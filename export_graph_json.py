"""
export_graph_json.py

Exports a lightweight snapshot of the sector-note Neo4j graph as a single
graph-data.json file, shaped for the Cytoscape.js visualization in index.html.

graph-data.json itself stays lightweight: taxonomy identity + relationship
structure (+ BUYS_FROM notes) only. The dense force_*/vp_*/sizing_*
analytical properties that neo4j_populate.py writes onto SubIndustry/
IndustryGroup nodes are instead written out as one small JSON file per node
into a data/ folder (data/<id>.json), so the browser can lazy-fetch a
node's forces/viewpoints/market_sizing only when that node is actually
clicked, rather than bundling all of it into the single up-front page load.

Connection pattern mirrors neo4j_retrieval.py: reads NEO4J_URI, NEO4J_USER
(or NEO4J_USERNAME), NEO4J_PASSWORD, NEO4J_DATABASE from the environment
(.env file supported via python-dotenv).

Geography is hardcoded to a single constant below (GEOGRAPHY = "IN") since
all data inspected so far is India-only. Change that constant if/when the
graph expands to other geographies.

Usage:
    python export_graph_json.py
    python export_graph_json.py --output /path/to/graph-data.json
"""

from __future__ import annotations

import os
import json
import argparse
from datetime import datetime, timezone

try:
    from neo4j import GraphDatabase
except ImportError as exc:
    raise ImportError(
        "The 'neo4j' package is required. Install it with: pip install neo4j"
    ) from exc

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Reuses the exact same flattened-property reshape logic (force_N_*, vp_N_*,
# sizing_N_* -> structured lists, including the JSON-string decoding for
# sizing's demand_drivers/pnl_drivers/new_opportunities) that
# neo4j_retrieval.py already implements and tests via its own CLI, rather
# than duplicating that parsing here.
from neo4j_retrieval import reshape_node_properties, filter_reshaped_node


# ─── Config ────────────────────────────────────────────────────────────────

GEOGRAPHY = "IN"  # single hardcoded geography constant; change here if this expands later

DEFAULT_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graph-data.json")

# Forces / viewpoints / market sizing are lazy-fetched by the browser per
# node on click (data/<id>.json), rather than bundled into graph-data.json.
# That keeps the up-front page load lean regardless of how much sector
# intelligence text exists, at the cost of one small fetch per node click.
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Node labels included in the export. Scoped to taxonomy + value chain only —
# the full graph also has Commodity (279) and MacroIndicator (692) nodes
# connected via AFFECTS (2,270 edges), which would make a single force-directed
# view unreadable. Those can be added later as a toggle-able layer if wanted.
NODE_LABELS = ["Sector", "IndustryGroup", "SubIndustry"]

# Relationship types included in the export. AFFECTS is deliberately excluded
# for the same reason (see NODE_LABELS comment above).
REL_TYPES = ["BELONGS_TO", "BUYS_FROM"]

# BUYS_FROM relationship notes end with a trailing sentence like "The scope
# qualifier: ..." — internal taxonomy/methodology commentary (edge-type
# classifications, "distinct from row X", node-tagging caveats) written for
# whoever curated the dataset, not for a viewer reading the sidebar. This
# marker is stripped from the notes text exported to graph-data.json; the
# full raw text is untouched in Neo4j.
_SCOPE_QUALIFIER_MARKER = "The scope qualifier:"


def _strip_scope_qualifier(notes: str | None) -> str | None:
    if not notes:
        return notes
    idx = notes.find(_SCOPE_QUALIFIER_MARKER)
    if idx == -1:
        return notes
    return notes[:idx].rstrip()


# ─── Connection ────────────────────────────────────────────────────────────

def _get_driver():
    uri = os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME")
    password = os.environ.get("NEO4J_PASSWORD")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    if not uri or not user or not password:
        raise EnvironmentError(
            "Missing Neo4j connection details. Set NEO4J_URI, NEO4J_USER "
            "(or NEO4J_USERNAME), and NEO4J_PASSWORD in your environment or .env file."
        )

    driver = GraphDatabase.driver(uri, auth=(user, password))
    return driver, database


# ─── Cypher ────────────────────────────────────────────────────────────────

# Data-quality note: a handful of nodes share the same `code` across two
# different labels (e.g. IG0601 exists as both an IndustryGroup and a
# mislabeled SubIndustry). Rather than hardcoding those codes, this query
# detects them at runtime and the export logic below keeps the IndustryGroup
# (or Sector) copy and drops the SubIndustry duplicate, so the graph doesn't
# end up with two nodes sharing one id. This self-corrects automatically if
# the underlying Neo4j data is ever cleaned up.
_DUPLICATE_CODES_QUERY = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $labels)
WITH n.code AS code, count(n) AS cnt
WHERE code IS NOT NULL AND cnt > 1
RETURN collect(code) AS codes
"""

# Node id is the taxonomy `code` (e.g. "SE01", "IG0601", "IN010101") rather
# than elementId(), since that's what the rest of the pipeline (index.html's
# dropdowns, search, and sidebar data-id lookups) and the current
# graph-data.json already key on.
_NODES_QUERY = """
MATCH (n)
WHERE any(label IN labels(n) WHERE label IN $labels)
  AND NOT (n:SubIndustry AND n.code IN $duplicate_codes)
RETURN
    n.code AS id,
    CASE
        WHEN n:Sector THEN 'Sector'
        WHEN n:IndustryGroup THEN 'IndustryGroup'
        WHEN n:SubIndustry THEN 'SubIndustry'
        ELSE labels(n)[0]
    END AS label,
    coalesce(n.name, n.code) AS name,
    n.code AS code,
    properties(n) AS props
"""

_RELS_QUERY = """
MATCH (a)-[r]->(b)
WHERE type(r) IN $rel_types
  AND any(label IN labels(a) WHERE label IN $labels)
  AND any(label IN labels(b) WHERE label IN $labels)
  AND NOT (a:SubIndustry AND a.code IN $duplicate_codes)
  AND NOT (b:SubIndustry AND b.code IN $duplicate_codes)
RETURN
    a.code AS source,
    b.code AS target,
    type(r) AS type,
    r.strength AS strength,
    r.nature AS nature,
    r.end_market AS end_market,
    r.notes AS notes
"""


# ─── Export ────────────────────────────────────────────────────────────────

def _write_node_data_files(node_rows: list[dict], data_dir: str) -> int:
    """
    Writes one data/<id>.json per node that has at least one of
    forces/viewpoints/market_sizing, containing that node's full, unfiltered
    reshaped data (all categories, all entries — the sidebar's tab UI does
    its own display-side selection). Nodes with none of the three are
    skipped entirely, so a missing file just means "nothing to show" and the
    browser doesn't need a 404 to figure that out... except fetch still has
    to try, so the caller should treat a failed fetch as "no data" quietly.
    """
    os.makedirs(data_dir, exist_ok=True)
    written = 0
    for row in node_rows:
        reshaped = reshape_node_properties(row["props"])
        filtered = filter_reshaped_node(reshaped)  # no filters = everything, plus computed "sources"
        if not (filtered["forces"] or filtered["viewpoints"] or filtered["market_sizing"]):
            continue
        payload = {
            "forces": filtered["forces"],
            "viewpoints": filtered["viewpoints"],
            "market_sizing": filtered["market_sizing"],
            "sources": filtered["sources"],
        }
        path = os.path.join(data_dir, f"{row['id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        written += 1
    return written


def export_graph(output_path: str = DEFAULT_OUTPUT_PATH, data_dir: str = DEFAULT_DATA_DIR) -> str:
    driver, database = _get_driver()

    try:
        with driver.session(database=database) as session:
            dup_result = session.run(_DUPLICATE_CODES_QUERY, labels=NODE_LABELS).single()
            duplicate_codes = (dup_result["codes"] if dup_result else []) or []
            if duplicate_codes:
                print(f"Note: {len(duplicate_codes)} code(s) shared across multiple labeled "
                      f"nodes, keeping the higher-level (Sector/IndustryGroup) copy and "
                      f"dropping the SubIndustry duplicate: {duplicate_codes}")

            node_rows = session.run(
                _NODES_QUERY, labels=NODE_LABELS, duplicate_codes=duplicate_codes
            ).data()
            rel_rows = session.run(
                _RELS_QUERY, rel_types=REL_TYPES, labels=NODE_LABELS, duplicate_codes=duplicate_codes
            ).data()
    finally:
        driver.close()

    nodes = [
        {
            "id": row["id"],
            "label": row["name"] or row["id"],
            "group": row["label"],
            "code": row["code"],
        }
        for row in node_rows
    ]

    relationships = [
        {
            "source": row["source"],
            "target": row["target"],
            "type": row["type"],
            "strength": row.get("strength"),
            "nature": row.get("nature"),
            "end_market": row.get("end_market"),
            "notes": _strip_scope_qualifier(row.get("notes")),
        }
        for row in rel_rows
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "geography": GEOGRAPHY,
        "nodes": nodes,
        "relationships": relationships,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(nodes)} nodes and {len(relationships)} relationships -> {output_path}")

    written = _write_node_data_files(node_rows, data_dir)
    print(f"Wrote {written} per-node data file(s) (forces/viewpoints/market_sizing) -> {data_dir}")

    return output_path


# ─── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export the Neo4j sector graph to graph-data.json")
    parser.add_argument(
        "--output", default=DEFAULT_OUTPUT_PATH,
        help="Path to write the JSON file (default: graph-data.json next to this script)",
    )
    parser.add_argument(
        "--data-dir", default=DEFAULT_DATA_DIR,
        help="Directory to write per-node forces/viewpoints/market_sizing JSON files (default: data/ next to this script)",
    )
    args = parser.parse_args()
    export_graph(output_path=args.output, data_dir=args.data_dir)
