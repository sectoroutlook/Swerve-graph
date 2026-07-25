"""
neo4j_retrieval.py

Pure retrieval module for the sector-note graph (Neo4j).

This module contains NO LLM calls. It only connects to Neo4j, reshapes raw
node properties into structured records, applies optional filters, and
assembles JSON. It is meant to be imported as a building block by a later
orchestration script that adds reasoning on top of the retrieved data.

Graph shape (as of last inspection):
    Labels:        Sector, IndustryGroup, SubIndustry, Commodity, MacroIndicator
    Relationships: BELONGS_TO   (SubIndustry -> IndustryGroup, IndustryGroup -> Sector, etc.)
                   BUYS_FROM     (SubIndustry -> SubIndustry, value-chain / supplier edges)
                   AFFECTS       (Commodity/MacroIndicator -> Sector/IndustryGroup/SubIndustry)
    Identity key:  all nodes are matched by their `name` property (case-sensitive,
                   exact match expected upstream).

Node property shape (SubIndustry / IndustryGroup):
    Properties are flattened, numbered groups rather than nested objects:
        force_{i}_title, force_{i}_description, force_{i}_type,
        force_{i}_impact_magnitude, force_{i}_time_horizon, force_{i}_as_of_date
            -> force_{i}_type is one of:
               tailwind, headwind, structural_change, cyclical_change,
               key_risk, upside_driver

        vp_{i}_title, vp_{i}_description, vp_{i}_stance,
        vp_{i}_source_firm, vp_{i}_source_date, vp_{i}_source_doc_id
            -> vp_{i}_stance is one of:
               positive, cautious_positive, neutral, cautious_negative, negative

        sizing_{i}_tam_value, sizing_{i}_tam_unit, sizing_{i}_sam_value,
        sizing_{i}_as_of_year, sizing_{i}_forecast_cagr, sizing_{i}_forecast_cagr_period,
        sizing_{i}_historical_cagr, sizing_{i}_historical_cagr_period,
        sizing_{i}_demand_drivers, sizing_{i}_pnl_drivers, sizing_{i}_new_opportunities
            -> these three are JSON-encoded strings, e.g. '[{"driver": ..., "description": ...}]'
        sizing_{i}_methodology, sizing_{i}_source_firm, sizing_{i}_source_date,
        sizing_{i}_data_confidence

This module reshapes these flattened groups into lists of records
(`forces`, `viewpoints`, `market_sizing`) and supports filtering that
reshaped data down to specific categories / force types / viewpoint
stances / sizing components.

By default, filters apply ONLY to the primary/root node being queried
(the SubIndustry itself, or the IndustryGroup itself). Value-chain
neighbors (BUYS_FROM) and, for an IndustryGroup, member SubIndustries,
come back with full, unfiltered, reshaped data. Pass
apply_filters_to_neighbors=True to cascade the same filters down to
neighbors / member subindustries (and their own value chains) too.

Public entry points:
    retrieve(name, node_type, categories=None, force_types=None,
             viewpoint_stances=None, sizing_components=None,
             apply_filters_to_neighbors=False) -> dict

    save_result_json(result, output_dir=None) -> str
        Saves a retrieve() result to '<outputs>/<name>__<type>__<timestamp>.json'
        (an 'outputs' folder next to this script, auto-created). Returns the
        path written. e.g. Oil_Gas_Upstream_EP__SubIndustry__20260723_154210.json

    run_cli()  -> interactive menu-driven wrapper around retrieve() that also
        prints and saves the result via save_result_json()

node_type must be one of: "SubIndustry", "IndustryGroup" (case-insensitive,
"IN" and "IG" shorthand also accepted per the original spec).

Output shape:
    {
        "query": {
            "name": ..., "type": ...,
            "filters": {"categories": [...], "force_types": [...],
                        "viewpoint_stances": [...], "sizing_components": [...]}
        },
        "data": {
            # for a SubIndustry query:
            "subindustry": {
                "raw_properties": {...all flat properties, minus force/vp/sizing keys...},
                "forces": [ {title, description, type, impact_magnitude, time_horizon, as_of_date}, ... ],
                "viewpoints": [ {title, description, stance, source_firm, source_date, source_doc_id}, ... ],
                "market_sizing": [ {tam_value, tam_unit, sam_value, demand_drivers, pnl_drivers,
                                     new_opportunities, methodology, source_firm, source_date,
                                     as_of_year, forecast_cagr, forecast_cagr_period,
                                     historical_cagr, historical_cagr_period, data_confidence}, ... ],
                "sources": [ "Bain & Company", "IBEF", ... ]   # deduplicated, RAW (not normalized)
                                                                 # source_firm values from whichever
                                                                 # viewpoints/market_sizing records
                                                                 # survived filtering. Forces carry no
                                                                 # source_firm in the underlying data.
            },
            "value_chain": [
                {
                    "name": ..., "relationship": "BUYS_FROM", "direction": "outgoing",
                    "labels": [...],
                    "relationship_properties": {   # properties of the BUYS_FROM edge itself
                        "notes": "...", "strength": "high|medium|low",
                        "nature": ["raw_material"|"service"|"component"|"energy"|"capital", ...],
                        "end_market": ["B2B"|"B2G"|...], "p2_id": "...", "last_reviewed": "..."
                        # not all edges have all fields; empty dict if relationship has no properties
                    },
                    "properties": {   # target node's data; filtered only if apply_filters_to_neighbors=True
                        "raw_properties": {...}, "forces": [...], "viewpoints": [...],
                        "market_sizing": [...], "sources": [...]
                    }
                },
                ...
            ]

            # for an IndustryGroup query:
            "industry_group": { ... same reshape as subindustry, filters DO apply here ... },
            "subindustries": [
                {
                    "subindustry": { ...ALWAYS full / unfiltered... },
                    "value_chain": [ ... ALWAYS full / unfiltered ... ]
                },
                ...
            ]
        },
        "source": [ {node_name, labels, matched_via, query}, ... ],
        "errors": [ "..." ]   # present and non-empty only if something was not found
    }
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

try:
    from neo4j import GraphDatabase
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "The 'neo4j' package is required. Install it with: pip install neo4j"
    ) from exc

try:
    from dotenv import load_dotenv
    load_dotenv()  # loads a .env file from the current working directory, if present
except ImportError:
    pass  # python-dotenv is optional; env vars can also be set directly


# ---------------------------------------------------------------------------
# Constants: category / type / stance vocabularies
# ---------------------------------------------------------------------------

ALL_CATEGORIES = ["forces", "viewpoints", "market_sizing"]

ALL_FORCE_TYPES = [
    "tailwind",
    "headwind",
    "structural_change",
    "cyclical_change",
    "key_risk",
    "upside_driver",
]

ALL_VIEWPOINT_STANCES = [
    "positive",
    "cautious_positive",
    "neutral",
    "cautious_negative",
    "negative",
]

ALL_SIZING_COMPONENTS = [
    "tam_sam",
    "demand_drivers",
    "pnl_drivers",
    "new_opportunities",
    "methodology_source",
    "cagr",
]

_TYPE_ALIASES = {
    "in": "SubIndustry",
    "subindustry": "SubIndustry",
    "sub_industry": "SubIndustry",
    "sub-industry": "SubIndustry",
    "ig": "IndustryGroup",
    "industrygroup": "IndustryGroup",
    "industry_group": "IndustryGroup",
    "industry-group": "IndustryGroup",
}


class Neo4jRetrievalError(Exception):
    """Raised for retrieval-time errors (not found, ambiguous, bad input)."""


def _normalize_type(node_type: str) -> str:
    key = node_type.strip().lower()
    if key not in _TYPE_ALIASES:
        raise Neo4jRetrievalError(
            f"Unknown node_type '{node_type}'. Expected one of: "
            f"SubIndustry / IN / IndustryGroup / IG."
        )
    return _TYPE_ALIASES[key]


def _normalize_subset(values: Optional[list[str]], allowed: list[str], label: str) -> Optional[list[str]]:
    """Validate a requested subset against an allowed vocabulary. None means 'all'."""
    if values is None:
        return None
    invalid = [v for v in values if v not in allowed]
    if invalid:
        raise Neo4jRetrievalError(
            f"Invalid {label} value(s) {invalid}. Allowed values: {allowed}."
        )
    return list(values)


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------

class Neo4jConnection:
    """Thin wrapper around the neo4j driver, usable as a context manager."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ):
        self.uri = uri or os.environ.get("NEO4J_URI")
        self.user = user or os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME")
        self.password = password or os.environ.get("NEO4J_PASSWORD")
        self.database = database or os.environ.get("NEO4J_DATABASE", "neo4j")

        if not self.uri or not self.user or not self.password:
            raise Neo4jRetrievalError(
                "Missing Neo4j connection details. Provide uri/user/password "
                "explicitly or set NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars."
            )

        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> "Neo4jConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def run(self, query: str, params: Optional[dict] = None) -> list[dict]:
        params = params or {}
        with self._driver.session(database=self.database) as session:
            result = session.run(query, params)
            return [record.data() for record in result]


# ---------------------------------------------------------------------------
# Core Cypher operations
# ---------------------------------------------------------------------------

_GET_NODE_QUERY = """
MATCH (n:{label} {{name: $name}})
RETURN properties(n) AS props, labels(n) AS labels
"""

_GET_BUYS_FROM_QUERY = """
MATCH (a:SubIndustry {name: $name})-[r:BUYS_FROM]->(b)
RETURN properties(b) AS props, labels(b) AS labels, b.name AS name,
       type(r) AS rel_type, 'outgoing' AS direction, properties(r) AS rel_props
"""

_GET_SUBINDUSTRIES_OF_IG_QUERY = """
MATCH (s:SubIndustry)-[r:BELONGS_TO]->(ig:IndustryGroup {name: $name})
RETURN s.name AS name, type(r) AS rel_type
"""


def _fetch_node(conn: Neo4jConnection, name: str, label: str) -> Optional[dict]:
    query = _GET_NODE_QUERY.format(label=label)
    rows = conn.run(query, {"name": name})
    if not rows:
        return None
    return rows[0]


# ---------------------------------------------------------------------------
# Property reshaping: flat force_N_/vp_N_/sizing_N_ groups -> structured lists
# ---------------------------------------------------------------------------

def _safe_json_loads(value: Any) -> Any:
    """sizing_*_demand_drivers etc. are JSON-encoded strings; '[]' -> []."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def _extract_group(props: dict, prefix: str) -> dict[int, dict]:
    """
    Collects all keys matching '{prefix}_{i}_{field}' into {i: {field: value}}.
    e.g. prefix='force' picks up force_1_title, force_1_type, force_2_title, ...
    """
    groups: dict[int, dict] = {}
    marker = f"{prefix}_"
    for key, value in props.items():
        if not key.startswith(marker):
            continue
        rest = key[len(marker):]
        # rest looks like "<index>_<field...>"
        parts = rest.split("_", 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        idx, field = int(parts[0]), parts[1]
        groups.setdefault(idx, {})[field] = value
    return groups


def _reshape_forces(props: dict) -> list[dict]:
    groups = _extract_group(props, "force")
    forces = []
    for idx in sorted(groups):
        g = groups[idx]
        forces.append(
            {
                "index": idx,
                "title": g.get("title"),
                "description": g.get("description"),
                "type": g.get("type"),
                "impact_magnitude": g.get("impact_magnitude"),
                "time_horizon": g.get("time_horizon"),
                "as_of_date": g.get("as_of_date"),
            }
        )
    return forces


def _reshape_viewpoints(props: dict) -> list[dict]:
    groups = _extract_group(props, "vp")
    viewpoints = []
    for idx in sorted(groups):
        g = groups[idx]
        viewpoints.append(
            {
                "index": idx,
                "title": g.get("title"),
                "description": g.get("description"),
                "stance": g.get("stance"),
                "source_firm": g.get("source_firm"),
                "source_date": g.get("source_date"),
                "source_doc_id": g.get("source_doc_id"),
            }
        )
    return viewpoints


def _reshape_market_sizing(props: dict) -> list[dict]:
    groups = _extract_group(props, "sizing")
    sizing = []
    for idx in sorted(groups):
        g = groups[idx]
        sizing.append(
            {
                "index": idx,
                "tam_value": g.get("tam_value"),
                "tam_unit": g.get("tam_unit"),
                "sam_value": g.get("sam_value"),
                "as_of_year": g.get("as_of_year"),
                "forecast_cagr": g.get("forecast_cagr"),
                "forecast_cagr_period": g.get("forecast_cagr_period"),
                "historical_cagr": g.get("historical_cagr"),
                "historical_cagr_period": g.get("historical_cagr_period"),
                "demand_drivers": _safe_json_loads(g.get("demand_drivers", "[]")),
                "pnl_drivers": _safe_json_loads(g.get("pnl_drivers", "[]")),
                "new_opportunities": _safe_json_loads(g.get("new_opportunities", "[]")),
                "methodology": g.get("methodology"),
                "source_firm": g.get("source_firm"),
                "source_date": g.get("source_date"),
                "data_confidence": g.get("data_confidence"),
            }
        )
    return sizing


def _raw_properties_minus_groups(props: dict) -> dict:
    """Everything that isn't part of a force_/vp_/sizing_ numbered group."""
    result = {}
    for key, value in props.items():
        if (
            _is_grouped_key(key, "force")
            or _is_grouped_key(key, "vp")
            or _is_grouped_key(key, "sizing")
        ):
            continue
        result[key] = value
    return result


def _is_grouped_key(key: str, prefix: str) -> bool:
    marker = f"{prefix}_"
    if not key.startswith(marker):
        return False
    rest = key[len(marker):]
    parts = rest.split("_", 1)
    return len(parts) == 2 and parts[0].isdigit()


def reshape_node_properties(props: dict) -> dict:
    """
    Full reshape of a node's raw properties into structured categories.
    Always computes all three categories; filtering happens separately so
    that neighbor nodes can reuse this same reshape without any filtering.
    """
    return {
        "raw_properties": _raw_properties_minus_groups(props),
        "forces": _reshape_forces(props),
        "viewpoints": _reshape_viewpoints(props),
        "market_sizing": _reshape_market_sizing(props),
    }


def _collect_sources(viewpoints: list[dict], sizing: list[dict]) -> list[str]:
    """
    Deduplicated (but NOT normalized) list of source_firm values found across
    a set of viewpoint and market-sizing records. Raw values are kept as-is
    (e.g. "BCG", "BCG Global", "bcg_global" all appear separately if present)
    since firm-name normalization was explicitly not requested.
    """
    seen: list[str] = []
    for record in viewpoints:
        firm = record.get("source_firm")
        if firm and firm not in seen:
            seen.append(firm)
    for record in sizing:
        firm = record.get("source_firm")
        if firm and firm not in seen:
            seen.append(firm)
    return seen


def filter_reshaped_node(
    reshaped: dict,
    categories: Optional[list[str]] = None,
    force_types: Optional[list[str]] = None,
    viewpoint_stances: Optional[list[str]] = None,
    sizing_components: Optional[list[str]] = None,
) -> dict:
    """
    Applies category/type/stance/component filters to an already-reshaped
    node dict (as produced by reshape_node_properties). Only used for the
    PRIMARY node; neighbor nodes should be passed through unfiltered.

    categories=None means all three categories are included, each still
    subject to their own sub-filters if given.

    A top-level "sources" field is always included: the deduplicated list of
    source_firm values (e.g. "Bain & Company", "IBEF", "BCG") drawn from
    whichever viewpoints/market_sizing records survive filtering. Forces
    carry no source_firm in the underlying data, so they don't contribute.
    """
    cats = categories if categories is not None else ALL_CATEGORIES
    result: dict[str, Any] = {"raw_properties": reshaped["raw_properties"]}

    filtered_forces: list[dict] = []
    filtered_viewpoints: list[dict] = []
    filtered_sizing_full: list[dict] = []  # unprojected, used only for source collection

    if "forces" in cats:
        filtered_forces = reshaped["forces"]
        if force_types is not None:
            filtered_forces = [f for f in filtered_forces if f.get("type") in force_types]
        result["forces"] = filtered_forces

    if "viewpoints" in cats:
        filtered_viewpoints = reshaped["viewpoints"]
        if viewpoint_stances is not None:
            filtered_viewpoints = [v for v in filtered_viewpoints if v.get("stance") in viewpoint_stances]
        result["viewpoints"] = filtered_viewpoints

    if "market_sizing" in cats:
        filtered_sizing_full = reshaped["market_sizing"]
        if sizing_components is not None:
            sizing_components_full = filtered_sizing_full
            result["market_sizing"] = [
                _project_sizing_component(s, sizing_components) for s in sizing_components_full
            ]
        else:
            result["market_sizing"] = filtered_sizing_full

    result["sources"] = _collect_sources(filtered_viewpoints, filtered_sizing_full)

    return result


def _project_sizing_component(sizing_record: dict, components: list[str]) -> dict:
    """Projects a single market-sizing record down to the requested components."""
    projected: dict[str, Any] = {"index": sizing_record.get("index")}
    if "tam_sam" in components:
        projected["tam_value"] = sizing_record.get("tam_value")
        projected["tam_unit"] = sizing_record.get("tam_unit")
        projected["sam_value"] = sizing_record.get("sam_value")
        projected["as_of_year"] = sizing_record.get("as_of_year")
    if "demand_drivers" in components:
        projected["demand_drivers"] = sizing_record.get("demand_drivers")
    if "pnl_drivers" in components:
        projected["pnl_drivers"] = sizing_record.get("pnl_drivers")
    if "new_opportunities" in components:
        projected["new_opportunities"] = sizing_record.get("new_opportunities")
    if "methodology_source" in components:
        projected["methodology"] = sizing_record.get("methodology")
        projected["source_firm"] = sizing_record.get("source_firm")
        projected["source_date"] = sizing_record.get("source_date")
        projected["data_confidence"] = sizing_record.get("data_confidence")
    if "cagr" in components:
        projected["forecast_cagr"] = sizing_record.get("forecast_cagr")
        projected["forecast_cagr_period"] = sizing_record.get("forecast_cagr_period")
        projected["historical_cagr"] = sizing_record.get("historical_cagr")
        projected["historical_cagr_period"] = sizing_record.get("historical_cagr_period")
    return projected


# ---------------------------------------------------------------------------
# Value chain (full/unfiltered by default; filterable via apply_filters_to_neighbors)
# ---------------------------------------------------------------------------

def _fetch_value_chain(
    conn: Neo4jConnection,
    subindustry_name: str,
    apply_filters: bool = False,
    categories: Optional[list[str]] = None,
    force_types: Optional[list[str]] = None,
    viewpoint_stances: Optional[list[str]] = None,
    sizing_components: Optional[list[str]] = None,
) -> tuple[list[dict], list[dict]]:
    """
    Returns (value_chain_data, source_entries) for the one-hop BUYS_FROM
    neighbors of the given SubIndustry. Fully reshaped and unfiltered unless
    apply_filters=True, in which case the same category/type/stance/component
    filters used for the primary node are cascaded to each neighbor too.
    """
    rows = conn.run(_GET_BUYS_FROM_QUERY, {"name": subindustry_name})

    value_chain_data = []
    source_entries = []
    for row in rows:
        reshaped = reshape_node_properties(row["props"])
        if apply_filters:
            properties = filter_reshaped_node(
                reshaped, categories, force_types, viewpoint_stances, sizing_components
            )
        else:
            properties = filter_reshaped_node(reshaped)

        value_chain_data.append(
            {
                "name": row["name"],
                "relationship": row["rel_type"],
                "direction": row["direction"],
                "labels": row["labels"],
                "relationship_properties": row.get("rel_props") or {},
                "properties": properties,
            }
        )
        source_entries.append(
            {
                "node_name": row["name"],
                "labels": row["labels"],
                "matched_via": {
                    "relationship": row["rel_type"],
                    "direction": row["direction"],
                    "from": subindustry_name,
                    "to": row["name"],
                },
                "relationship_properties": row.get("rel_props") or {},
                "query": _GET_BUYS_FROM_QUERY.strip(),
            }
        )
    return value_chain_data, source_entries


# ---------------------------------------------------------------------------
# Retrieval logic
# ---------------------------------------------------------------------------

def _retrieve_subindustry(
    conn: Neo4jConnection,
    name: str,
    apply_filters: bool,
    categories: Optional[list[str]],
    force_types: Optional[list[str]],
    viewpoint_stances: Optional[list[str]],
    sizing_components: Optional[list[str]],
    apply_filters_to_neighbors: bool = False,
) -> tuple[dict, list[dict], list[str]]:
    """
    Core logic for a single SubIndustry: its own node (filtered only if
    apply_filters=True, i.e. this is the primary/root node of the query, or
    if this SubIndustry is itself being treated as a "neighbor"/"member" and
    apply_filters_to_neighbors=True was requested) + one-hop BUYS_FROM
    neighbors (filtered too if apply_filters_to_neighbors=True, else always
    full/unfiltered).
    """
    data: dict[str, Any] = {}
    source: list[dict] = []
    errors: list[str] = []

    node = _fetch_node(conn, name, "SubIndustry")
    if node is None:
        errors.append(f"SubIndustry '{name}' not found.")
        return data, source, errors

    reshaped = reshape_node_properties(node["props"])
    if apply_filters:
        data["subindustry"] = filter_reshaped_node(
            reshaped, categories, force_types, viewpoint_stances, sizing_components
        )
    else:
        # neighbor / member context: full and unfiltered, unless cascading is on
        data["subindustry"] = filter_reshaped_node(reshaped)

    source.append(
        {
            "node_name": name,
            "labels": node["labels"],
            "matched_via": None,
            "query": _GET_NODE_QUERY.format(label="SubIndustry").strip(),
        }
    )

    value_chain_data, value_chain_source = _fetch_value_chain(
        conn, name,
        apply_filters=apply_filters and apply_filters_to_neighbors,
        categories=categories, force_types=force_types,
        viewpoint_stances=viewpoint_stances, sizing_components=sizing_components,
    )
    data["value_chain"] = value_chain_data
    source.extend(value_chain_source)

    return data, source, errors


def _retrieve_industry_group(
    conn: Neo4jConnection,
    name: str,
    categories: Optional[list[str]],
    force_types: Optional[list[str]],
    viewpoint_stances: Optional[list[str]],
    sizing_components: Optional[list[str]],
    apply_filters_to_neighbors: bool = False,
) -> tuple[dict, list[dict], list[str]]:
    """
    Core logic for an IndustryGroup: its own node (filters apply here, since
    the IndustryGroup is the primary/root node) + all member SubIndustries,
    each expanded with the SubIndustry logic above. Member subindustries
    (and their own value chains) are UNFILTERED by default; if
    apply_filters_to_neighbors=True, the same filters requested for the
    IndustryGroup are cascaded down to every member SubIndustry and its
    value chain as well.
    """
    data: dict[str, Any] = {}
    source: list[dict] = []
    errors: list[str] = []

    node = _fetch_node(conn, name, "IndustryGroup")
    if node is None:
        errors.append(f"IndustryGroup '{name}' not found.")
        return data, source, errors

    reshaped = reshape_node_properties(node["props"])
    data["industry_group"] = filter_reshaped_node(
        reshaped, categories, force_types, viewpoint_stances, sizing_components
    )
    source.append(
        {
            "node_name": name,
            "labels": node["labels"],
            "matched_via": None,
            "query": _GET_NODE_QUERY.format(label="IndustryGroup").strip(),
        }
    )

    member_rows = conn.run(_GET_SUBINDUSTRIES_OF_IG_QUERY, {"name": name})
    subindustries = []
    for row in member_rows:
        sub_name = row["name"]
        source.append(
            {
                "node_name": sub_name,
                "labels": ["SubIndustry"],
                "matched_via": {
                    "relationship": row["rel_type"],
                    "direction": "outgoing",
                    "from": sub_name,
                    "to": name,
                },
                "query": _GET_SUBINDUSTRIES_OF_IG_QUERY.strip(),
            }
        )
        # apply_filters mirrors apply_filters_to_neighbors here: member
        # subindustries are treated like "neighbors" of the IndustryGroup.
        sub_data, sub_source, sub_errors = _retrieve_subindustry(
            conn, sub_name,
            apply_filters=apply_filters_to_neighbors,
            categories=categories, force_types=force_types,
            viewpoint_stances=viewpoint_stances, sizing_components=sizing_components,
            apply_filters_to_neighbors=apply_filters_to_neighbors,
        )
        subindustries.append(sub_data)
        source.extend(sub_source)
        errors.extend(sub_errors)

    data["subindustries"] = subindustries
    return data, source, errors


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def retrieve(
    name: str,
    node_type: str,
    categories: Optional[list[str]] = None,
    force_types: Optional[list[str]] = None,
    viewpoint_stances: Optional[list[str]] = None,
    sizing_components: Optional[list[str]] = None,
    apply_filters_to_neighbors: bool = False,
    connection: Optional[Neo4jConnection] = None,
) -> dict:
    """
    Retrieve structured graph data for a SubIndustry or IndustryGroup. No LLM calls.

    By default, filters apply ONLY to the primary/root node (the SubIndustry
    or IndustryGroup passed in). Value-chain neighbors, and (for an
    IndustryGroup) member SubIndustries and their value chains, come back
    fully reshaped and unfiltered.

    Set apply_filters_to_neighbors=True to cascade the same categories /
    force_types / viewpoint_stances / sizing_components filters down to
    BUYS_FROM value-chain neighbors, and (for an IndustryGroup) to every
    member SubIndustry and its own value chain as well.

    Args:
        name: exact `name` property value of the node to retrieve.
        node_type: "SubIndustry" / "IN" or "IndustryGroup" / "IG" (case-insensitive).
        categories: subset of ["forces", "viewpoints", "market_sizing"].
            None = all three.
        force_types: subset of ALL_FORCE_TYPES. None = all. Ignored if
            "forces" not in categories.
        viewpoint_stances: subset of ALL_VIEWPOINT_STANCES. None = all.
            Ignored if "viewpoints" not in categories.
        sizing_components: subset of ALL_SIZING_COMPONENTS. None = all.
            Ignored if "market_sizing" not in categories.
        apply_filters_to_neighbors: if True, cascade the above filters to
            value-chain neighbors / member subindustries too. Default False
            (neighbors/members always full/unfiltered, the original behavior).
        connection: optional pre-built Neo4jConnection to reuse (e.g. across
            many calls in a batch). If omitted, a new connection is opened
            and closed using environment variables.

    Returns:
        dict with "query", "data", "source", and optionally "errors" keys.
    """
    resolved_type = _normalize_type(node_type)
    categories = _normalize_subset(categories, ALL_CATEGORIES, "categories")
    force_types = _normalize_subset(force_types, ALL_FORCE_TYPES, "force_types")
    viewpoint_stances = _normalize_subset(viewpoint_stances, ALL_VIEWPOINT_STANCES, "viewpoint_stances")
    sizing_components = _normalize_subset(sizing_components, ALL_SIZING_COMPONENTS, "sizing_components")

    owns_connection = connection is None
    conn = connection or Neo4jConnection()

    try:
        if resolved_type == "SubIndustry":
            data, source, errors = _retrieve_subindustry(
                conn, name,
                apply_filters=True,
                categories=categories, force_types=force_types,
                viewpoint_stances=viewpoint_stances, sizing_components=sizing_components,
                apply_filters_to_neighbors=apply_filters_to_neighbors,
            )
        else:
            data, source, errors = _retrieve_industry_group(
                conn, name,
                categories=categories, force_types=force_types,
                viewpoint_stances=viewpoint_stances, sizing_components=sizing_components,
                apply_filters_to_neighbors=apply_filters_to_neighbors,
            )
    finally:
        if owns_connection:
            conn.close()

    result: dict[str, Any] = {
        "query": {
            "name": name,
            "type": resolved_type,
            "filters": {
                "categories": categories if categories is not None else ALL_CATEGORIES,
                "force_types": force_types if force_types is not None else ALL_FORCE_TYPES,
                "viewpoint_stances": viewpoint_stances if viewpoint_stances is not None else ALL_VIEWPOINT_STANCES,
                "sizing_components": sizing_components if sizing_components is not None else ALL_SIZING_COMPONENTS,
                "apply_filters_to_neighbors": apply_filters_to_neighbors,
            },
        },
        "data": data,
        "source": source,
    }
    if errors:
        result["errors"] = errors

    return result


# ---------------------------------------------------------------------------
# Saving results to JSON
# ---------------------------------------------------------------------------

_OUTPUT_DIR_NAME = "outputs"


def _slugify(text: str) -> str:
    """Turns a node name into a filesystem-safe slug, e.g.
    'Oil & Gas Upstream (E&P)' -> 'Oil_Gas_Upstream_EP'."""
    keep = []
    for ch in text:
        if ch.isalnum():
            keep.append(ch)
        elif ch in (" ", "-", "_"):
            keep.append("_")
        # anything else (&, (), /, etc.) is dropped
    slug = "".join(keep)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_")


def build_output_filename(result: dict) -> str:
    """Builds a 'name__type__timestamp.json' filename from a retrieve() result."""
    import datetime

    query = result.get("query", {})
    name_slug = _slugify(query.get("name", "unknown"))
    type_slug = query.get("type", "unknown")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name_slug}__{type_slug}__{timestamp}.json"


def save_result_json(result: dict, output_dir: Optional[str] = None) -> str:
    """
    Saves a retrieve() result dict to a JSON file named
    '<name>__<type>__<timestamp>.json' inside an 'outputs' subfolder next
    to this script (created if missing, unless output_dir is given).

    Returns the full path of the file written.
    """
    if output_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(script_dir, _OUTPUT_DIR_NAME)

    os.makedirs(output_dir, exist_ok=True)

    filename = build_output_filename(result)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str, ensure_ascii=False)

    return filepath


# ---------------------------------------------------------------------------
# Interactive CLI menu
# ---------------------------------------------------------------------------

def _prompt_single(prompt: str, options: list[str]) -> str:
    while True:
        print(prompt)
        for i, opt in enumerate(options, start=1):
            print(f"  {i}) {opt}")
        choice = input("> ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print("Invalid choice, try again.\n")


def _prompt_multi(prompt: str, options: list[str]) -> Optional[list[str]]:
    """Returns None for 'all', else the selected subset."""
    while True:
        print(prompt)
        print("  0) All")
        for i, opt in enumerate(options, start=1):
            print(f"  {i}) {opt}")
        raw = input("Enter comma-separated numbers (e.g. 1,3) or 0 for all: ").strip()
        if raw == "0" or raw == "":
            return None
        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            if any(i < 1 or i > len(options) for i in indices):
                raise ValueError
            return [options[i - 1] for i in indices]
        except ValueError:
            print("Invalid input, try again.\n")


def _prompt_yes_no(prompt: str, default_no: bool = True) -> bool:
    suffix = " [y/N]: " if default_no else " [Y/n]: "
    raw = input(prompt + suffix).strip().lower()
    if raw == "":
        return not default_no
    return raw in ("y", "yes")


def run_cli() -> None:
    """Interactive menu-driven wrapper around retrieve()."""
    print("=== Neo4j Sector Graph Retrieval ===\n")

    node_type = _prompt_single("Node type?", ["SubIndustry (IN)", "IndustryGroup (IG)"])
    node_type = "SubIndustry" if node_type.startswith("SubIndustry") else "IndustryGroup"

    name = input(f"\nEnter the exact {node_type} name: ").strip()

    print()
    categories = _prompt_multi(
        "Which categories do you want for the primary node?",
        ALL_CATEGORIES,
    )
    cats = categories if categories is not None else ALL_CATEGORIES

    force_types = None
    if "forces" in cats:
        print()
        force_types = _prompt_multi("Which force types?", ALL_FORCE_TYPES)

    viewpoint_stances = None
    if "viewpoints" in cats:
        print()
        viewpoint_stances = _prompt_multi("Which viewpoint stances?", ALL_VIEWPOINT_STANCES)

    sizing_components = None
    if "market_sizing" in cats:
        print()
        sizing_components = _prompt_multi("Which market sizing components?", ALL_SIZING_COMPONENTS)

    print()
    neighbor_label = (
        "value-chain neighbors (BUYS_FROM)"
        if node_type == "SubIndustry"
        else "member subindustries (and their value chains)"
    )
    apply_filters_to_neighbors = _prompt_yes_no(
        f"Apply the same filters to {neighbor_label} too? "
        "(No = they always return full, unfiltered data)"
    )

    print("\nRunning retrieval...\n")
    result = retrieve(
        name=name,
        node_type=node_type,
        categories=categories,
        force_types=force_types,
        viewpoint_stances=viewpoint_stances,
        sizing_components=sizing_components,
        apply_filters_to_neighbors=apply_filters_to_neighbors,
    )
    print(json.dumps(result, indent=2, default=str))

    filepath = save_result_json(result)
    print(f"\nSaved to: {filepath}")


if __name__ == "__main__":
    run_cli()
