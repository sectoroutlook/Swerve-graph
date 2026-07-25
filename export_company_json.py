"""
export_company_json.py

Exports the company ETL graph (Company/Segment nodes written by
neo4j_etl.py, e.g. Adani_power.json) into a folder of small JSON files for
the "Company" tab in index.html's sidebar.

Companies aren't connected to any node on the taxonomy graph canvas (see
the "adding Adani to the graph" conversation this followed from — the
Company/Segment subgraph and the Sector/IndustryGroup/SubIndustry subgraph
are two disconnected islands in the same Neo4j database), so the Company
tab gets its own independent selector rather than being driven by canvas
clicks. That means, unlike graph-data.json's lazy per-node fetch, the
browser needs an up-front index of which companies exist at all:

    company-data/index.json          -> [{ticker, company_name}, ...]
    company-data/<ticker>.json       -> one company's scoped data

Reuses neo4j_company_retrieval.py's retrieve_company() for all the actual
Neo4j reads and property reshaping/categorization (including the
consolidated/standalone split for pnl/balance_sheet/cash_flow — see that
module's _split_scoped_dict, and neo4j_etl.py's table_to_props_scoped for
why that split exists), rather than duplicating any of that logic here.
This script's own job is just: pick the categories that matter for a first
version of the Company tab (financials + ratios + segments; people and
relationships/debt are deliberately left out for now, though
retrieve_company() already supports pulling them with zero new Cypher if
that scope grows later), reshape each metric's period-keyed dict into a
sorted series with a precomputed "latest" headline value, and write it out.

Connection pattern mirrors export_graph_json.py / neo4j_retrieval.py: reads
NEO4J_URI, NEO4J_USER (or NEO4J_USERNAME), NEO4J_PASSWORD, NEO4J_DATABASE
from the environment (.env file supported via python-dotenv).

Usage:
    python export_company_json.py
    python export_company_json.py --data-dir /path/to/company-data
"""

from __future__ import annotations

import os
import re
import json
import argparse
from typing import Any, Optional

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

from neo4j_company_retrieval import (
    Neo4jConnection,
    retrieve_company,
)


# ─── Config ────────────────────────────────────────────────────────────────

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "company-data")

# Full scope for the Company tab: core financials + ratios/metrics +
# segments + an Overview tab (identity/business description/governance/
# guidance) + People (executives/directors) + Debt & Relationships
# (lenders via FINANCED_BY, other external entities via RELATES_TO).
CATEGORIES = [
    "pnl", "balance_sheet", "cash_flow",
    "ratios", "operational_metrics", "unit_economics", "market_data", "pnl_drivers",
    "business_description", "governance", "guidance",
    "segments", "people", "regulators", "relationships", "debt",
]

_STATEMENT_CATEGORIES = ["pnl", "balance_sheet", "cash_flow"]
_FLAT_CATEGORIES = ["ratios", "operational_metrics", "unit_economics", "market_data"]
# Overview categories are qualitative/text period data (a statement or
# nested {statement, type, tone, ...} per period) rather than numeric
# {value, unit} series, so they go through _build_note_list instead of
# _build_metric_list. pnl_drivers lives here too even though it's
# P&L-adjacent, since its shape is a per-period narrative
# ({driver_type, direction, segment, description}), not a numeric series.
_OVERVIEW_CATEGORIES = ["business_description", "governance", "guidance", "pnl_drivers"]


# ─── Period parsing / sorting ───────────────────────────────────────────────

# "FY2026" (annual) or "Q1_FY2027" (quarterly). Annual periods sort AFTER
# Q4 of the same fiscal year (quarter rank 5), since an annual figure is
# reported once the full year, including Q4, is complete.
_ANNUAL_RE = re.compile(r"^FY(\d{4})$")
_QUARTER_RE = re.compile(r"^Q([1-4])_FY(\d{4})$")


def _period_sort_key(period: str) -> tuple[int, int]:
    m = _QUARTER_RE.match(period)
    if m:
        quarter, year = int(m.group(1)), int(m.group(2))
        return (year, quarter)
    m = _ANNUAL_RE.match(period)
    if m:
        year = int(m.group(1))
        return (year, 5)
    return (0, 0)  # unrecognized format sorts first, lowest priority


def _build_metric_list(label_to_periods: dict) -> list[dict]:
    """
    Converts {label: {period: {value, unit}}} into a list of
    [{label, unit, latest_period, latest_value, series: [{period, value}, ...]}],
    sorted chronologically (oldest first) within each series, with a
    precomputed "latest" headline so the client doesn't need to parse
    period strings at all.
    """
    metrics = []
    for label, period_data in label_to_periods.items():
        if not isinstance(period_data, dict) or not period_data:
            continue
        entries = []
        for period, detail in period_data.items():
            if not isinstance(detail, dict):
                continue
            value = detail.get("value")
            if value is None:
                continue
            entries.append({
                "period": period,
                "value": value,
                "unit": detail.get("unit"),
            })
        if not entries:
            continue
        entries.sort(key=lambda e: _period_sort_key(e["period"]))
        latest = entries[-1]
        metrics.append({
            "label": label,
            "unit": latest.get("unit"),
            "latest_period": latest["period"],
            "latest_value": latest["value"],
            "series": entries,
        })
    metrics.sort(key=lambda m: m["label"])
    return metrics


def _build_note_list(label_to_periods: dict) -> list[dict]:
    """
    For qualitative/text categories (business_description, governance,
    guidance, pnl_drivers): converts {label: {period: text_or_dict}} into
    [{label, latest_period, entries: [{period, text, detail}, ...]}],
    sorted newest-first within each entry list (most recent commentary is
    what a reader wants on top, unlike numeric series which read
    chronologically). "text" is always a display-ready string (either the
    raw string value, or, for nested dicts like guidance's
    {statement, type, tone} / pnl_drivers' {driver_type, direction,
    segment, description}, the most descriptive sub-field found). "detail"
    keeps the full original value for callers that want the structured
    fields (type/tone/driver_type/direction/etc.) rather than just the text.
    """
    _TEXT_KEYS = ("statement", "description", "text", "value", "summary")
    notes = []
    for label, period_data in label_to_periods.items():
        if not isinstance(period_data, dict) or not period_data:
            continue
        entries = []
        for period, detail in period_data.items():
            if isinstance(detail, str):
                text = detail
            elif isinstance(detail, dict):
                text = next((detail[k] for k in _TEXT_KEYS if isinstance(detail.get(k), str)), None)
                if text is None:
                    text = json.dumps(detail, ensure_ascii=False)
            else:
                continue
            if not text:
                continue
            entries.append({"period": period, "text": text, "detail": detail})
        if not entries:
            continue
        entries.sort(key=lambda e: _period_sort_key(e["period"]), reverse=True)
        notes.append({
            "label": label,
            "latest_period": entries[0]["period"],
            "entries": entries,
        })
    notes.sort(key=lambda n: n["label"])
    return notes


def _build_statement_section(scoped: dict) -> dict:
    """For pnl/balance_sheet/cash_flow: {"consolidated": [...], "standalone": [...]}."""
    return {
        "consolidated": _build_metric_list(scoped.get("consolidated", {})),
        "standalone": _build_metric_list(scoped.get("standalone", {})),
    }


def _build_segment(segment: dict) -> dict:
    props = segment.get("properties", {}) or {}
    return {
        "segment_id": segment.get("segment_id"),
        "segment_name": segment.get("segment_name"),
        "segment_type": segment.get("segment_type"),
        "sub_industry_code": segment.get("sub_industry_code"),
        "metrics": _build_metric_list(props),
    }


def _build_person(person: dict) -> dict:
    """
    neo4j_company_retrieval._fetch_people() returns
    {person_id, full_name, role, periods_seen, properties: {label: {period: value}}}
    where `role` is the value of r.role from the single WORKS_FOR edge Neo4j
    returned for this (person, company) pair, and `properties` holds
    whatever other flat fields (background, other role-history variants,
    etc.) were on the Person node — reshaped into notes the same way as the
    Overview categories, since these are text/period fields too.
    """
    props = person.get("properties", {}) or {}
    return {
        "person_id": person.get("person_id"),
        "full_name": person.get("full_name"),
        "role": person.get("role"),
        "periods_seen": person.get("periods_seen"),
        "notes": _build_note_list(props),
    }


def _build_regulator(reg: dict) -> dict:
    """neo4j_company_retrieval._fetch_regulators() returns the Regulator node's
    flat properties plus periods_seen merged into one dict."""
    return {
        "name": reg.get("name"),
        "acronym": reg.get("acronym"),
        "type": reg.get("type"),
        "jurisdiction": reg.get("jurisdiction"),
        "sector_regulated": reg.get("sector_regulated"),
        "periods_seen": reg.get("periods_seen"),
    }


def _build_relationship(rel: dict) -> dict:
    """neo4j_company_retrieval._fetch_relationships() (RELATES_TO edges to
    ExternalEntity nodes, e.g. subsidiaries/JVs): properties is already a
    parsed {period: {field: value}} dict from properties_json."""
    props = rel.get("properties", {}) or {}
    periods = sorted(props.keys(), key=_period_sort_key, reverse=True)
    return {
        "to_node": rel.get("to_node"),
        "relationship_type": rel.get("relationship_type"),
        "from_type": rel.get("from_type"),
        "to_type": rel.get("to_type"),
        "latest_period": periods[0] if periods else None,
        "latest_detail": props.get(periods[0]) if periods else None,
        "periods": [{"period": p, "detail": props[p]} for p in periods],
    }


def _build_debt(debt: dict) -> dict:
    """neo4j_company_retrieval._fetch_debt() (FINANCED_BY edges): one row
    per financing instrument, already flat (no period-keyed nesting)."""
    return {
        "lender": debt.get("lender"),
        "instrument_label": debt.get("instrument_label"),
        "instrument_type": debt.get("instrument_type"),
        "period": debt.get("period"),
        "amount": debt.get("amount"),
        "unit": debt.get("unit"),
        "outstanding_amount": debt.get("outstanding_amount"),
        "interest_rate": debt.get("interest_rate"),
        "rate_type": debt.get("rate_type"),
        "tenor_years": debt.get("tenor_years"),
        "security": debt.get("security"),
        "currency": debt.get("currency"),
    }


def _build_company_graph(
    ticker: str,
    company_name: str,
    segments: list[dict],
    people: list[dict],
    regulators: list[dict],
    relationships: list[dict],
    debt: list[dict],
) -> dict:
    """
    Standalone graph for canvas rendering: one Company node in the center,
    with a node per real connected entity from every relationship type the
    Company subgraph actually has in Neo4j (HAS_SEGMENT, WORKS_FOR,
    REGULATED_BY, RELATES_TO, FINANCED_BY), shaped the same way
    graph-data.json shapes the taxonomy graph (id/label/group on nodes,
    source/target/type on edges) so index.html's Cytoscape rendering code
    can share as much logic as possible between the two graphs.

    Debt and RELATES_TO rows are per-period (e.g. 60 debt rows / 217
    relationship rows for Adani Power), so lenders and related entities are
    deduplicated by name into one node each here — one row per period would
    make the canvas unreadable and doesn't add anything a single node with a
    "latest period" edge label doesn't already convey (the full period
    history is still in the sidebar's Debt & Relationships tab).
    """
    nodes = [{"id": ticker, "label": company_name, "group": "Company"}]
    edges = []

    for seg in segments:
        seg_id = seg.get("segment_id") or f"{ticker}__{seg.get('segment_name')}"
        nodes.append({"id": seg_id, "label": seg.get("segment_name") or seg_id, "group": "Segment"})
        edges.append({"source": seg_id, "target": ticker, "type": "HAS_SEGMENT"})

    for person in people:
        person_id = person.get("person_id") or f"{ticker}__{person.get('full_name')}"
        nodes.append({"id": person_id, "label": person.get("full_name") or person_id, "group": "Person"})
        edges.append({
            "source": person_id, "target": ticker, "type": "WORKS_FOR",
            "label": person.get("role") or None,
        })

    for reg in regulators:
        reg_id = f"reg__{reg.get('name')}"
        nodes.append({"id": reg_id, "label": reg.get("acronym") or reg.get("name") or reg_id, "group": "Regulator"})
        edges.append({"source": ticker, "target": reg_id, "type": "REGULATED_BY"})

    # Dedupe lenders by name — same lender often appears across many periods.
    seen_lenders: dict[str, str] = {}
    for d in debt:
        lender_name = d.get("lender")
        if not lender_name:
            continue
        lender_id = seen_lenders.get(lender_name)
        if lender_id is None:
            lender_id = f"lender__{lender_name}"
            seen_lenders[lender_name] = lender_id
            nodes.append({"id": lender_id, "label": lender_name, "group": "Lender"})
            edges.append({
                "source": ticker, "target": lender_id, "type": "FINANCED_BY",
                "label": d.get("instrument_type") or None,
            })

    # Dedupe related entities (subsidiaries/JVs/etc.) by to_node name — same
    # entity typically recurs once per reporting period.
    seen_entities: dict[str, str] = {}
    for rel in relationships:
        entity_name = rel.get("to_node")
        if not entity_name:
            continue
        entity_id = seen_entities.get(entity_name)
        if entity_id is None:
            entity_id = f"entity__{entity_name}"
            seen_entities[entity_name] = entity_id
            nodes.append({"id": entity_id, "label": entity_name, "group": "RelatedEntity"})
            edges.append({
                "source": ticker, "target": entity_id, "type": "RELATES_TO",
                "label": rel.get("relationship_type") or None,
            })

    return {"nodes": nodes, "relationships": edges}


# ─── Company listing ─────────────────────────────────────────────────────────

_LIST_COMPANIES_QUERY = """
MATCH (c:Company)
RETURN c.ticker AS ticker, c.company_name AS company_name
ORDER BY c.company_name
"""


def _list_companies(conn: Neo4jConnection) -> list[dict]:
    rows = conn.run(_LIST_COMPANIES_QUERY)
    return [{"ticker": r["ticker"], "company_name": r["company_name"]} for r in rows]


# ─── Export ────────────────────────────────────────────────────────────────

def export_companies(data_dir: str = DEFAULT_DATA_DIR) -> str:
    os.makedirs(data_dir, exist_ok=True)

    conn = Neo4jConnection()
    try:
        companies = _list_companies(conn)

        index_path = os.path.join(data_dir, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump({"companies": companies}, f, indent=2, ensure_ascii=False)
        print(f"Wrote company index ({len(companies)} companies) -> {index_path}")

        for entry in companies:
            ticker = entry["ticker"]
            result = retrieve_company(ticker, categories=CATEGORIES, connection=conn)

            if result.get("errors"):
                print(f"  ✗ Skipped {ticker}: {result['errors']}")
                continue

            data = result.get("data", {})
            company = data.get("company", {})
            ticker_resolved = result["query"]["resolved_ticker"]
            company_name_resolved = result["query"]["resolved_company_name"]
            segments_built = [_build_segment(s) for s in data.get("segments", [])]
            people_built = [_build_person(p) for p in data.get("people", [])]
            regulators_built = [_build_regulator(r) for r in data.get("regulators", [])]
            relationships_built = [_build_relationship(r) for r in data.get("relationships", [])]
            debt_built = [_build_debt(d) for d in data.get("debt", [])]

            payload = {
                "ticker": ticker_resolved,
                "company_name": company_name_resolved,
                "identity": company.get("identity", {}),
                "financials": {
                    cat: _build_statement_section(company.get(cat, {}))
                    for cat in _STATEMENT_CATEGORIES
                },
                **{
                    cat: _build_metric_list(company.get(cat, {}))
                    for cat in _FLAT_CATEGORIES
                },
                "overview": {
                    cat: _build_note_list(company.get(cat, {}))
                    for cat in _OVERVIEW_CATEGORIES
                },
                "segments": segments_built,
                "people": people_built,
                "regulators": regulators_built,
                "relationships": relationships_built,
                "debt": debt_built,
                "graph": _build_company_graph(
                    ticker_resolved, company_name_resolved,
                    segments_built, people_built, regulators_built,
                    relationships_built, debt_built,
                ),
            }

            out_path = os.path.join(data_dir, f"{ticker}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            print(f"  ✓ {entry['company_name']} ({ticker}) -> {out_path}")
    finally:
        conn.close()

    return data_dir


# ─── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export the Neo4j company ETL graph to per-company JSON files for index.html's Company tab."
    )
    parser.add_argument(
        "--data-dir", default=DEFAULT_DATA_DIR,
        help="Directory to write index.json and per-company JSON files (default: company-data/ next to this script)",
    )
    args = parser.parse_args()
    export_companies(data_dir=args.data_dir)
