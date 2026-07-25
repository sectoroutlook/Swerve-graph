"""
neo4j_company_retrieval.py

Pure retrieval module for the company ETL graph (Neo4j) written by
neo4j_etl.py, e.g. Adani_power.json loaded via `python neo4j_etl.py --master ...`.

This module contains NO LLM calls. It only connects to Neo4j, reshapes raw
node/edge properties into structured records, applies optional category
filters, and assembles JSON. It mirrors the design of neo4j_retrieval.py
(the sector-taxonomy retrieval module) but targets the company graph schema.

Graph shape (per neo4j_etl.py):
    Labels:        Company, Segment, Person, ExternalEntity, Regulator
    Relationships: (Company)-[:HAS_SEGMENT]->(Segment)                {no properties}
                   (Person)-[:WORKS_FOR]->(Company)                   {role, periods_seen}
                   (Company)-[:REGULATED_BY]->(Regulator)             {periods_seen}
                   (Company)-[:RELATES_TO]->(ExternalEntity)          {relationship_type,
                                                                        from_node, to_node,
                                                                        from_type, to_type,
                                                                        properties_json,
                                                                        "{period}__{label}" flattened fields}
                   (Company)-[:FINANCED_BY]->(ExternalEntity)         {instrument_label, period,
                                                                        lender, amount, unit,
                                                                        interest_rate, rate_type,
                                                                        security, currency,
                                                                        instrument_type,
                                                                        outstanding_amount, tenor_years}
    Identity key:  Company matched by `ticker` (unique constraint); Segment by
                   `segment_id` ("{ticker}__{segment_name}"); Person by
                   `person_id` ("{ticker}__{person_name}"); ExternalEntity and
                   Regulator by `name`.

Company/Segment/Person node property shape:
    Every property key is the EXACT label string from the source JSON
    (no prefix/sanitisation), and its value is a JSON-encoded string holding
    a period-keyed dict, e.g.:
        company["Revenue from Operations"] = '{"FY2017": {"value": 22783.82,
                                                            "unit": "INR Crores"},
                                                 "FY2018": {...}, ...}'
    A small number of scalar identity fields are plain strings (e.g. Company
    Name, CIN, ticker, segment_id, person_id, full_name, date_of_birth).

    This module classifies every property into one of two buckets and
    reshapes accordingly:
      - "table" properties: JSON-parseable period-keyed dicts -> parsed dict
      - "scalar" properties: plain strings/identity fields -> left as-is

Category grouping (for filtering):
    Company-level categories mirror the ETL's own source sections:
      "pnl", "balance_sheet", "cash_flow"   (each split consolidated/standalone)
      "ratios", "operational_metrics", "unit_economics", "market_data"
      "business_description", "governance", "guidance", "pnl_drivers"
    Since the graph itself doesn't tag which section each property came
    from (properties are flattened onto the node), retrieve_company()
    AUTOMATICALLY locates and loads the matching source "normalised
    master" JSON (e.g. Adani_power.json) the first time it sees a given
    ticker, by scanning SOURCE_JSON_SEARCH_DIRS (default: this script's own
    directory) for a *.json file whose "ticker" field matches. No manual
    setup call is required. If no matching source file is found on disk,
    categorization silently falls back to putting everything in an "other"
    bucket — retrieval still works, just without the category split.

    Relationship-style categories are separate and are always returned as
    their own top-level keys (not affected by the company-property
    categories filter): "segments", "people", "regulators",
    "relationships" (RELATES_TO / ExternalEntity), "debt" (FINANCED_BY).

Public entry points:
    retrieve_company(name, categories=None) -> dict
        `name` is matched case-insensitively against Company.company_name
        (substring match) and resolved to a ticker internally. Raises
        Neo4jRetrievalError if zero or more than one company matches.

    save_result_json(result, output_dir=None) -> str
        Same convention as neo4j_retrieval.py:
        outputs/<company_slug>__Company__<timestamp>.json

    run_cli() -> interactive menu-driven wrapper around retrieve_company()

Output shape:
    {
        "query": {"name": ..., "resolved_ticker": ..., "resolved_company_name": ...,
                   "filters": {"categories": [...]}},
        "data": {
            "company": {
                "identity": {...scalar fields...},
                "pnl": {"consolidated": {...}, "standalone": {...}},          # if requested
                "balance_sheet": {"consolidated": {...}, "standalone": {...}},# if requested
                "cash_flow": {"consolidated": {...}, "standalone": {...}},    # if requested
                "ratios": {...},                # if requested
                "operational_metrics": {...},   # if requested
                "unit_economics": {...},        # if requested
                "market_data": {...},           # if requested
                "business_description": {...},  # if requested
                "governance": {...},            # if requested
                "guidance": {...},              # if requested
                "pnl_drivers": {...},           # if requested
                "other": {...}                  # any property not in the category map
            },
            "segments": [ {segment_id, segment_name, sub_industry_code, segment_type,
                            properties: {...reshaped like company...}}, ... ],
            "people": [ {person_id, full_name, role, periods_seen,
                         properties: {...reshaped...}}, ... ],
            "regulators": [ {name, periods_seen, ...}, ... ],
            "relationships": [ {to_node, relationship_type, from_type, to_type,
                                 properties: {...parsed from properties_json...}}, ... ],
            "debt": [ {instrument_label, period, lender, amount, unit, interest_rate,
                        rate_type, security, currency, instrument_type,
                        outstanding_amount, tenor_years}, ... ]
        },
        "source": [ {node_name/ticker, labels, matched_via, query}, ... ],
        "errors": [ "..." ]
    }
"""

from __future__ import annotations

import json
import os
import re
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
# Category vocabulary
# ---------------------------------------------------------------------------

# Company-level property categories (subset of these can be requested).
# "segments", "people", "regulators", "relationships", "debt" are always
# returned as their own top-level keys, independent of this filter.
ALL_CATEGORIES = [
    "pnl",
    "balance_sheet",
    "cash_flow",
    "ratios",
    "operational_metrics",
    "unit_economics",
    "market_data",
    "business_description",
    "governance",
    "guidance",
    "pnl_drivers",
    "segments",
    "people",
    "regulators",
    "relationships",
    "debt",
]

# Company-node-property categories only (excludes the relationship-style
# categories, which are handled separately and always included/excluded
# as a whole based on whether they appear in `categories`).
_COMPANY_PROPERTY_CATEGORIES = [
    "pnl", "balance_sheet", "cash_flow", "ratios", "operational_metrics",
    "unit_economics", "market_data", "business_description", "governance",
    "guidance", "pnl_drivers",
]

_RELATIONSHIP_CATEGORIES = ["segments", "people", "regulators", "relationships", "debt"]

# Identity fields are always included on the company node regardless of filters.
_IDENTITY_LABELS = {
    "Company Name", "CIN", "Registered Office", "Scrip Code", "BSE Scrip Code",
    "NSE Scrip Code", "NSE Scrip Symbol", "Website",
    "Corporate Identity Number (CIN)", "Registered Office Address",
    "Scrip Code (BSE)", "Scrip Code (NSE)",
}


class Neo4jRetrievalError(Exception):
    """Raised for retrieval-time errors (not found, ambiguous, bad input)."""


def _normalize_categories(categories: Optional[list[str]]) -> Optional[list[str]]:
    if categories is None:
        return None
    invalid = [c for c in categories if c not in ALL_CATEGORIES]
    if invalid:
        raise Neo4jRetrievalError(
            f"Invalid categories {invalid}. Allowed values: {ALL_CATEGORIES}."
        )
    return list(categories)


# ---------------------------------------------------------------------------
# Connection handling (same pattern as neo4j_retrieval.py)
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
# Name -> ticker resolution
# ---------------------------------------------------------------------------

_FIND_COMPANY_QUERY = """
MATCH (c:Company)
WHERE toLower(c.company_name) CONTAINS toLower($name)
   OR toLower(c.ticker) CONTAINS toLower($name)
RETURN c.ticker AS ticker, c.company_name AS company_name
"""


def resolve_company(conn: Neo4jConnection, name: str) -> tuple[str, str]:
    """
    Resolves a (partial, case-insensitive) company name or ticker to an
    exact (ticker, company_name) pair. Raises Neo4jRetrievalError if zero
    or more than one company matches.
    """
    rows = conn.run(_FIND_COMPANY_QUERY, {"name": name})
    if not rows:
        raise Neo4jRetrievalError(f"No company found matching '{name}'.")
    if len(rows) > 1:
        candidates = [f"{r['company_name']} ({r['ticker']})" for r in rows]
        raise Neo4jRetrievalError(
            f"Ambiguous company name '{name}'. Matches: {candidates}. "
            f"Provide a more specific name or the exact ticker."
        )
    return rows[0]["ticker"], rows[0]["company_name"]


# ---------------------------------------------------------------------------
# Property reshaping
# ---------------------------------------------------------------------------

def _try_parse_json(value: Any) -> tuple[bool, Any]:
    """Returns (was_json, parsed_or_original)."""
    if not isinstance(value, str):
        return False, value
    stripped = value.strip()
    if not stripped or stripped[0] not in "{[":
        return False, value
    try:
        return True, json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return False, value


def reshape_flat_properties(props: dict, identity_labels: set[str] = frozenset()) -> dict:
    """
    Splits a node's flat properties into:
      - "identity": scalar identity fields (never JSON-encoded)
      - "tables": every other property, JSON-parsed where possible
                   (falls back to the raw string if not valid JSON)
    """
    identity: dict[str, Any] = {}
    tables: dict[str, Any] = {}

    for label, value in props.items():
        if label in identity_labels:
            identity[label] = value
            continue
        was_json, parsed = _try_parse_json(value)
        tables[label] = parsed if was_json else value

    return {"identity": identity, "tables": tables}


def categorize_company_tables(tables: dict) -> dict:
    """
    Buckets a company's reshaped "tables" dict into the ALL_CATEGORIES
    groups, based on CATEGORY_LABEL_MAP. Labels not found in the map land
    in "other" so nothing is silently dropped.
    """
    result: dict[str, Any] = {cat: {} for cat in _COMPANY_PROPERTY_CATEGORIES}
    result["other"] = {}

    for label, value in tables.items():
        category = CATEGORY_LABEL_MAP.get(label)
        if category is None:
            result["other"][label] = value
        else:
            result[category][label] = value

    return result


# Static label->category map. Built from the same section structure
# neo4j_etl.py reads from the source JSON (financials.consolidated/standalone
# .pnl/.balance_sheet/.cash_flow, ratios, operational_metrics, unit_economics,
# market_data, business_description, governance, guidance, pnl_drivers).
# The ETL flattens all of these onto the Company node without tagging which
# section each label came from, so this map is populated automatically at
# retrieval time by scanning for a matching source master JSON on disk (see
# _autoload_category_map_for_ticker / SOURCE_JSON_SEARCH_DIRS below). If no
# matching file is found, categorization falls back to leaving everything
# in "other" — retrieval still works, just without the category split.
CATEGORY_LABEL_MAP: dict[str, str] = {}

# Tickers for which we've already attempted an auto-load (successful or not),
# so repeated retrieve_company() calls don't re-scan the filesystem every time.
_AUTOLOADED_TICKERS: set[str] = set()

# Directories to search for source master JSON files, in order. Defaults to
# just this script's own directory (where Adani_power.json etc. live).
# Override by appending/replacing entries, e.g.:
#   neo4j_company_retrieval.SOURCE_JSON_SEARCH_DIRS.append("/path/to/masters")
SOURCE_JSON_SEARCH_DIRS: list[str] = [os.path.dirname(os.path.abspath(__file__))]


# pnl/balance_sheet/cash_flow labels are stored on the Neo4j Company node
# suffixed with " (Consolidated)" / " (Standalone)" (see neo4j_etl.py's
# table_to_props_scoped()), since the same label can legitimately appear in
# both scopes with different values. This regex recovers (label, scope) from
# a suffixed key so the values can be split back into
# {"consolidated": {...}, "standalone": {...}} on the way out — matching the
# shape documented at the top of this module.
_SCOPE_SUFFIX_RE = re.compile(r"^(.*) \((Consolidated|Standalone)\)$")

_SCOPED_CATEGORIES = ("pnl", "balance_sheet", "cash_flow")


def _split_scoped_dict(d: dict) -> dict:
    """
    Splits a flat {key: value} dict where some/all keys carry a
    " (Consolidated)"/" (Standalone)" suffix into
    {"consolidated": {label: value, ...}, "standalone": {label: value, ...}}.
    Keys without a recognized suffix are dropped (only expected from stale
    pre-fix data that hasn't been reloaded yet).
    """
    result: dict[str, dict] = {"consolidated": {}, "standalone": {}}
    for key, value in d.items():
        m = _SCOPE_SUFFIX_RE.match(key)
        if not m:
            continue
        label, scope = m.group(1), m.group(2).lower()
        result[scope][label] = value
    return result


def load_category_map_from_master(master_json_path: str) -> None:
    """
    Populates CATEGORY_LABEL_MAP by reading a source "normalised master"
    JSON (the same format neo4j_etl.py consumes, e.g. Adani_power.json) and
    recording which section each property label belongs to.

    You normally don't need to call this yourself — retrieve_company()
    calls it automatically the first time it sees a given ticker, by
    scanning SOURCE_JSON_SEARCH_DIRS for a JSON file whose own "ticker"
    field matches. This function remains available for explicit/manual use
    (e.g. pointing at a master file that isn't in the default search path).
    """
    with open(master_json_path, "r", encoding="utf-8") as f:
        master = json.load(f)

    def record(labels_dict: dict, category: str) -> None:
        for label in labels_dict:
            CATEGORY_LABEL_MAP[label] = category

    def record_scoped(labels_dict: dict, category: str, scope_suffix: str) -> None:
        # Must mirror neo4j_etl.py's table_to_props_scoped() suffix exactly,
        # since this is registering the key as it actually appears on the
        # Neo4j node, not the raw label from the source JSON.
        for label in labels_dict:
            CATEGORY_LABEL_MAP[f"{label} ({scope_suffix})"] = category

    fin = master.get("financials", {})
    for scope, scope_suffix in (("consolidated", "Consolidated"), ("standalone", "Standalone")):
        record_scoped(fin.get(scope, {}).get("pnl", {}), "pnl", scope_suffix)
        record_scoped(fin.get(scope, {}).get("balance_sheet", {}), "balance_sheet", scope_suffix)
        record_scoped(fin.get(scope, {}).get("cash_flow", {}), "cash_flow", scope_suffix)

    record(master.get("ratios", {}), "ratios")
    record(master.get("operational_metrics", {}), "operational_metrics")
    record(master.get("unit_economics", {}), "unit_economics")
    record(master.get("market_data", {}), "market_data")
    record(master.get("business_description", {}), "business_description")
    record(master.get("governance", {}), "governance")
    record(master.get("guidance", {}), "guidance")
    record(master.get("pnl_drivers", {}), "pnl_drivers")


def find_source_master_for_ticker(ticker: str) -> Optional[str]:
    """
    Scans SOURCE_JSON_SEARCH_DIRS for a *.json file whose own "ticker" field
    (top-level, as written by the same pipeline that produces Adani_power.json)
    matches the given ticker. Filenames are NOT trusted for matching, since
    they aren't guaranteed to encode the ticker (e.g. "Adani_power.json" for
    ticker "ADANIPOWER") — every candidate file's contents are checked instead.

    Returns the file path if found, else None. Skips files that aren't valid
    JSON or don't look like a normalised master (no "ticker" key) rather
    than raising.
    """
    for directory in SOURCE_JSON_SEARCH_DIRS:
        if not os.path.isdir(directory):
            continue
        for entry in os.listdir(directory):
            if not entry.lower().endswith(".json"):
                continue
            path = os.path.join(directory, entry)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    # Peek at just enough to check the ticker cheaply would
                    # require a streaming parser; these files are small
                    # enough (~1-2 MB) that a full load is fine here.
                    candidate = json.load(f)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue
            if isinstance(candidate, dict) and candidate.get("ticker") == ticker:
                return path
    return None


def _autoload_category_map_for_ticker(ticker: str) -> None:
    """
    Ensures CATEGORY_LABEL_MAP has entries for this ticker's source file,
    loading it on first use. Safe to call repeatedly (no-op after the first
    successful or unsuccessful attempt for a given ticker).
    """
    if ticker in _AUTOLOADED_TICKERS:
        return
    _AUTOLOADED_TICKERS.add(ticker)

    master_path = find_source_master_for_ticker(ticker)
    if master_path is None:
        return  # no source file found; categorization will fall back to "other"

    try:
        load_category_map_from_master(master_path)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass  # malformed source file; categorization falls back to "other"


# ---------------------------------------------------------------------------
# Core Cypher operations
# ---------------------------------------------------------------------------

_GET_COMPANY_QUERY = """
MATCH (c:Company {ticker: $ticker})
RETURN properties(c) AS props, labels(c) AS labels
"""

_GET_SEGMENTS_QUERY = """
MATCH (c:Company {ticker: $ticker})-[:HAS_SEGMENT]->(s:Segment)
RETURN properties(s) AS props, labels(s) AS labels
"""

_GET_PEOPLE_QUERY = """
MATCH (p:Person)-[r:WORKS_FOR]->(c:Company {ticker: $ticker})
RETURN properties(p) AS props, labels(p) AS labels,
       r.role AS role, r.periods_seen AS periods_seen
"""

_GET_REGULATORS_QUERY = """
MATCH (c:Company {ticker: $ticker})-[r:REGULATED_BY]->(reg:Regulator)
RETURN properties(reg) AS props, labels(reg) AS labels, r.periods_seen AS periods_seen
"""

_GET_RELATIONSHIPS_QUERY = """
MATCH (c:Company {ticker: $ticker})-[r:RELATES_TO]->(e:ExternalEntity)
RETURN properties(e) AS entity_props, e.name AS entity_name,
       properties(r) AS rel_props
"""

_GET_DEBT_QUERY = """
MATCH (c:Company {ticker: $ticker})-[r:FINANCED_BY]->(e:ExternalEntity)
RETURN properties(r) AS rel_props, e.name AS lender_name
"""


def _fetch_company(conn: Neo4jConnection, ticker: str) -> Optional[dict]:
    rows = conn.run(_GET_COMPANY_QUERY, {"ticker": ticker})
    return rows[0] if rows else None


def _fetch_segments(conn: Neo4jConnection, ticker: str) -> list[dict]:
    rows = conn.run(_GET_SEGMENTS_QUERY, {"ticker": ticker})
    segments = []
    for row in rows:
        reshaped = reshape_flat_properties(row["props"])
        segments.append(
            {
                "segment_id": row["props"].get("segment_id"),
                "segment_name": row["props"].get("segment_name"),
                "sub_industry_code": row["props"].get("sub_industry_code"),
                "segment_type": row["props"].get("segment_type"),
                "properties": reshaped["tables"],
            }
        )
    return segments


def _fetch_people(conn: Neo4jConnection, ticker: str) -> list[dict]:
    rows = conn.run(_GET_PEOPLE_QUERY, {"ticker": ticker})
    people = []
    for row in rows:
        reshaped = reshape_flat_properties(row["props"])
        people.append(
            {
                "person_id": row["props"].get("person_id"),
                "full_name": row["props"].get("full_name"),
                "role": row.get("role"),
                "periods_seen": row.get("periods_seen"),
                "properties": reshaped["tables"],
            }
        )
    return people


def _fetch_regulators(conn: Neo4jConnection, ticker: str) -> list[dict]:
    rows = conn.run(_GET_REGULATORS_QUERY, {"ticker": ticker})
    regulators = []
    for row in rows:
        props = dict(row["props"])
        props["periods_seen"] = row.get("periods_seen")
        regulators.append(props)
    return regulators


def _fetch_relationships(conn: Neo4jConnection, ticker: str) -> list[dict]:
    rows = conn.run(_GET_RELATIONSHIPS_QUERY, {"ticker": ticker})
    relationships = []
    for row in rows:
        rel_props = row["rel_props"] or {}
        # Prefer the structured properties_json over the flattened
        # "{period}__{label}" edge keys, since it's already nested.
        was_json, parsed_properties = _try_parse_json(rel_props.get("properties_json"))
        relationships.append(
            {
                "to_node": row.get("entity_name"),
                "relationship_type": rel_props.get("relationship_type"),
                "from_node": rel_props.get("from_node"),
                "from_type": rel_props.get("from_type"),
                "to_type": rel_props.get("to_type"),
                "entity_properties": row["entity_props"],
                "properties": parsed_properties if was_json else {},
            }
        )
    return relationships


def _fetch_debt(conn: Neo4jConnection, ticker: str) -> list[dict]:
    rows = conn.run(_GET_DEBT_QUERY, {"ticker": ticker})
    debt = []
    for row in rows:
        rel_props = dict(row["rel_props"] or {})
        rel_props.setdefault("lender", row.get("lender_name"))
        debt.append(rel_props)
    return debt


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def retrieve_company(
    name: str,
    categories: Optional[list[str]] = None,
    connection: Optional[Neo4jConnection] = None,
) -> dict:
    """
    Retrieve structured company-graph data. No LLM calls.

    Args:
        name: company name or ticker (case-insensitive substring match
            against Company.company_name / Company.ticker). Must resolve
            to exactly one company.
        categories: subset of ALL_CATEGORIES. None = everything.
            Company-property categories (pnl, balance_sheet, cash_flow,
            ratios, operational_metrics, unit_economics, market_data,
            business_description, governance, guidance, pnl_drivers)
            control what's included under data.company.
            Relationship categories (segments, people, regulators,
            relationships, debt) control which top-level data.* keys
            are populated at all.
        connection: optional pre-built Neo4jConnection to reuse.

    Returns:
        dict with "query", "data", "source", and optionally "errors" keys.
    """
    categories = _normalize_categories(categories)
    cats = categories if categories is not None else ALL_CATEGORIES

    owns_connection = connection is None
    conn = connection or Neo4jConnection()

    data: dict[str, Any] = {}
    source: list[dict] = []
    errors: list[str] = []

    try:
        ticker, company_name = resolve_company(conn, name)
        _autoload_category_map_for_ticker(ticker)

        company_row = _fetch_company(conn, ticker)
        if company_row is None:
            errors.append(f"Company with ticker '{ticker}' not found (resolved but missing).")
        else:
            reshaped = reshape_flat_properties(company_row["props"], _IDENTITY_LABELS)
            categorized = categorize_company_tables(reshaped["tables"])
            company_data: dict[str, Any] = {"identity": reshaped["identity"]}
            for cat in _COMPANY_PROPERTY_CATEGORIES:
                if cat in cats:
                    # pnl/balance_sheet/cash_flow keys are suffixed by scope
                    # on the node (see _SCOPE_SUFFIX_RE); split them back
                    # into {"consolidated": {...}, "standalone": {...}} here
                    # so callers get the shape documented at the top of this
                    # module instead of raw suffixed keys.
                    company_data[cat] = (
                        _split_scoped_dict(categorized[cat])
                        if cat in _SCOPED_CATEGORIES
                        else categorized[cat]
                    )
            company_data["other"] = categorized["other"]
            data["company"] = company_data
            source.append(
                {
                    "node_name": ticker,
                    "labels": company_row["labels"],
                    "matched_via": None,
                    "query": _GET_COMPANY_QUERY.strip(),
                }
            )

        if "segments" in cats:
            data["segments"] = _fetch_segments(conn, ticker)
            source.append({"node_name": f"{ticker} segments", "labels": ["Segment"],
                            "matched_via": {"relationship": "HAS_SEGMENT"}, "query": _GET_SEGMENTS_QUERY.strip()})

        if "people" in cats:
            data["people"] = _fetch_people(conn, ticker)
            source.append({"node_name": f"{ticker} people", "labels": ["Person"],
                            "matched_via": {"relationship": "WORKS_FOR"}, "query": _GET_PEOPLE_QUERY.strip()})

        if "regulators" in cats:
            data["regulators"] = _fetch_regulators(conn, ticker)
            source.append({"node_name": f"{ticker} regulators", "labels": ["Regulator"],
                            "matched_via": {"relationship": "REGULATED_BY"}, "query": _GET_REGULATORS_QUERY.strip()})

        if "relationships" in cats:
            data["relationships"] = _fetch_relationships(conn, ticker)
            source.append({"node_name": f"{ticker} relationships", "labels": ["ExternalEntity"],
                            "matched_via": {"relationship": "RELATES_TO"}, "query": _GET_RELATIONSHIPS_QUERY.strip()})

        if "debt" in cats:
            data["debt"] = _fetch_debt(conn, ticker)
            source.append({"node_name": f"{ticker} debt", "labels": ["ExternalEntity"],
                            "matched_via": {"relationship": "FINANCED_BY"}, "query": _GET_DEBT_QUERY.strip()})

    except Neo4jRetrievalError as e:
        errors.append(str(e))
        ticker, company_name = None, None
    finally:
        if owns_connection:
            conn.close()

    result: dict[str, Any] = {
        "query": {
            "name": name,
            "resolved_ticker": ticker,
            "resolved_company_name": company_name,
            "filters": {"categories": cats},
        },
        "data": data,
        "source": source,
    }
    if errors:
        result["errors"] = errors

    return result


# ---------------------------------------------------------------------------
# Saving results to JSON (same convention as neo4j_retrieval.py)
# ---------------------------------------------------------------------------

_OUTPUT_DIR_NAME = "outputs"


def _slugify(text: str) -> str:
    keep = []
    for ch in text or "unknown":
        if ch.isalnum():
            keep.append(ch)
        elif ch in (" ", "-", "_"):
            keep.append("_")
    slug = "".join(keep)
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug.strip("_") or "unknown"


def build_output_filename(result: dict) -> str:
    import datetime

    query = result.get("query", {})
    name_slug = _slugify(query.get("resolved_company_name") or query.get("name", "unknown"))
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{name_slug}__Company__{timestamp}.json"


def save_result_json(result: dict, output_dir: Optional[str] = None) -> str:
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

def _prompt_multi(prompt: str, options: list[str]) -> Optional[list[str]]:
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


def run_cli() -> None:
    """Interactive menu-driven wrapper around retrieve_company()."""
    print("=== Neo4j Company Graph Retrieval ===\n")

    name = input("Enter the company name (or ticker): ").strip()

    print()
    categories = _prompt_multi("Which categories do you want?", ALL_CATEGORIES)

    print("\nRunning retrieval...\n")
    result = retrieve_company(name=name, categories=categories)
    print(json.dumps(result, indent=2, default=str))

    if not result.get("errors"):
        filepath = save_result_json(result)
        print(f"\nSaved to: {filepath}")
    else:
        print(f"\nErrors: {result['errors']}")


if __name__ == "__main__":
    run_cli()
