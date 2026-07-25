"""
neo4j_etl.py
=============
Loads normalised master JSON(s) into a local Neo4j graph database.

NODES (exactly 5):
  Company        — identity + all financials + ratios + market data +
                   governance + guidance + pnl_drivers + business description
  Segment        — all segment metrics, capacity, geographic breakdown
  Person         — role, compensation, shareholding, background
  ExternalEntity — entity identity, shared across companies
  Regulator      — regulator identity, shared across companies

PROPERTY STORAGE:
  Every label uses the EXACT label string from the JSON as the property key.
  No prefixes, no sanitisation, no transformation.
  Time-series data stored as JSON string per label:
    "Revenue from Operations" = '{"FY2017":{"value":22783,"unit":"INR Crores"},...}'
  This means one property per label — clean, readable, matches Excel exactly.

EDGES:
  (Company)  -[:HAS_SEGMENT]->   (Segment)         {ticker}
  (Person)   -[:WORKS_FOR]->     (Company)         {role, periods_seen}
  (Company)  -[:REGULATED_BY]->  (Regulator)       {periods_seen}
  (Company)  -[:RELATES_TO]->    (ExternalEntity)  {relationship_type, period,
                                                     + all properties from JSON}
  (Company)  -[:FINANCED_BY]->   (ExternalEntity)  {instrument_label, period,
                                                     + all debt fields from JSON}

USAGE:
  pip install neo4j

  # Single company:
  python neo4j_etl.py \\
    --master ADANIPOWER_normalised_master.json \\
    --uri bolt://127.0.0.1:7687 \\
    --user neo4j \\
    --password yourpassword

  # Multiple companies:
  python neo4j_etl.py \\
    --master ADANIPOWER_normalised_master.json TATASTEEL_normalised_master.json \\
    --uri bolt://127.0.0.1:7687 \\
    --user neo4j \\
    --password yourpassword

  # Entire folder:
  python neo4j_etl.py \\
    --master-dir ./normalised/ \\
    --uri bolt://127.0.0.1:7687 \\
    --user neo4j \\
    --password yourpassword
"""

import argparse
import json
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase


# ── Helpers ────────────────────────────────────────────────────────────────────

def as_json(data) -> str:
    """Serialise any value to a compact JSON string for Neo4j property storage."""
    return json.dumps(data, ensure_ascii=False)


def table_to_props(table: dict) -> dict:
    """
    Convert {label: {period: {value, unit}}} to {label: json_string}.
    Uses the exact label string as the property key.
    Each value is a JSON string: '{"FY2017":{"value":22783,"unit":"INR Crores"},...}'
    """
    props = {}
    for label, period_data in table.items():
        if isinstance(period_data, dict) and period_data:
            props[label] = as_json(period_data)
    return props


def table_to_props_scoped(table: dict, scope: str) -> dict:
    """
    Same as table_to_props, but suffixes each key with " (Consolidated)" or
    " (Standalone)". Used for pnl/balance_sheet/cash_flow, where a label like
    "Revenue from Operations" can legitimately appear in BOTH the
    consolidated and standalone sections with DIFFERENT values. Without this
    suffix, storing both under the same property key would mean the second
    props.update() call silently overwrites the first — which is exactly
    what this codebase used to do (see git history / neo4j html/export
    conversation), permanently losing the consolidated figures for every
    overlapping label. neo4j_company_retrieval.py's _split_scoped_dict()
    is the read-side counterpart that un-suffixes and re-nests these back
    into {"consolidated": {...}, "standalone": {...}}.
    """
    props = {}
    for label, period_data in table.items():
        if isinstance(period_data, dict) and period_data:
            props[f"{label} ({scope})"] = as_json(period_data)
    return props


def structured_to_props(table: dict) -> dict:
    """
    Convert {label: {period: dict_or_text}} to {label: json_string}.
    Used for guidance, pnl_drivers, capacity, governance, business_description.
    """
    props = {}
    for label, period_data in table.items():
        if isinstance(period_data, dict) and period_data:
            props[label] = as_json(period_data)
    return props


# ── ETL ────────────────────────────────────────────────────────────────────────

class Neo4jETL:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        with self.driver.session() as s:
            s.run("RETURN 1")
        print("Connected to Neo4j.")

    def close(self):
        self.driver.close()

    def run(self, cypher: str, **params):
        with self.driver.session() as session:
            return session.run(cypher, **params)

    # ── Constraints ────────────────────────────────────────────────────────────

    def create_constraints(self):
        for stmt in [
            "CREATE CONSTRAINT company_ticker IF NOT EXISTS FOR (c:Company)        REQUIRE c.ticker       IS UNIQUE",
            "CREATE CONSTRAINT segment_id     IF NOT EXISTS FOR (s:Segment)        REQUIRE s.segment_id   IS UNIQUE",
            "CREATE CONSTRAINT person_id      IF NOT EXISTS FOR (p:Person)         REQUIRE p.person_id    IS UNIQUE",
            "CREATE CONSTRAINT entity_name    IF NOT EXISTS FOR (e:ExternalEntity) REQUIRE e.name         IS UNIQUE",
            "CREATE CONSTRAINT regulator_name IF NOT EXISTS FOR (r:Regulator)      REQUIRE r.name         IS UNIQUE",
        ]:
            try:
                self.run(stmt)
            except Exception:
                pass

    # ── Company node ───────────────────────────────────────────────────────────

    def load_company(self, master: dict):
        ticker  = master.get("ticker", "UNKNOWN")
        company = master.get("company") or ticker

        props = {
            "ticker":            ticker,
            "company_name":      company,
            "annual_periods":    as_json(master.get("periods", {}).get("annual",    [])),
            "quarterly_periods": as_json(master.get("periods", {}).get("quarterly", [])),
        }

        # Identity fields — exact label as key, value as string
        for label, value in master.get("identity", {}).items():
            if value is not None:
                props[label] = str(value)

        # Financial tables — one JSON string per label, suffixed by scope
        # ("... (Consolidated)" / "... (Standalone)") since the same label
        # commonly appears in both scopes with different values — see
        # table_to_props_scoped() docstring for why this matters.
        fin = master.get("financials", {})
        props.update(table_to_props_scoped(fin.get("consolidated", {}).get("pnl",           {}), "Consolidated"))
        props.update(table_to_props_scoped(fin.get("consolidated", {}).get("balance_sheet",  {}), "Consolidated"))
        props.update(table_to_props_scoped(fin.get("consolidated", {}).get("cash_flow",      {}), "Consolidated"))
        props.update(table_to_props_scoped(fin.get("standalone",   {}).get("pnl",           {}), "Standalone"))
        props.update(table_to_props_scoped(fin.get("standalone",   {}).get("balance_sheet",  {}), "Standalone"))
        props.update(table_to_props_scoped(fin.get("standalone",   {}).get("cash_flow",      {}), "Standalone"))

        # Ratios
        props.update(table_to_props(master.get("ratios", {})))

        # Operational metrics and unit economics at company level
        props.update(table_to_props(master.get("operational_metrics", {})))
        props.update(table_to_props(master.get("unit_economics",      {})))

        # Market data
        props.update(table_to_props(master.get("market_data", {})))

        # Business description — text per label per period
        props.update(structured_to_props(master.get("business_description", {})))

        # Governance — text per label per period
        props.update(structured_to_props(master.get("governance", {})))

        # Guidance — full detail per topic per period
        props.update(structured_to_props(master.get("guidance", {})))

        # PnL drivers — full detail per driver per period
        props.update(structured_to_props(master.get("pnl_drivers", {})))

        # Clean up stale unscoped pnl/balance_sheet/cash_flow properties left
        # over from before table_to_props_scoped() existed. Those older loads
        # stored e.g. "Revenue from Operations" (unsuffixed) as a single key
        # shared by both scopes, where the standalone write silently
        # clobbered the consolidated one. Re-running this loader now writes
        # "Revenue from Operations (Consolidated)" / "... (Standalone)"
        # instead, but the old unsuffixed key would otherwise linger forever
        # as stale, ambiguous data sitting alongside the correct one.
        stale_unscoped_labels = set()
        for scope in ("consolidated", "standalone"):
            stale_unscoped_labels.update(fin.get(scope, {}).get("pnl", {}).keys())
            stale_unscoped_labels.update(fin.get(scope, {}).get("balance_sheet", {}).keys())
            stale_unscoped_labels.update(fin.get(scope, {}).get("cash_flow", {}).keys())
        if stale_unscoped_labels:
            remove_clause = ", ".join(f"c.`{label}`" for label in sorted(stale_unscoped_labels))
            self.run(f"""
                MATCH (c:Company {{ticker: $ticker}})
                REMOVE {remove_clause}
            """, ticker=ticker)

        self.run("""
            MERGE (c:Company {ticker: $ticker})
            SET c += $props
        """, ticker=ticker, props=props)

        print(f"    Company node: {len(props)} properties ({len(stale_unscoped_labels)} legacy unscoped keys cleaned up)")

    # ── Segment nodes ──────────────────────────────────────────────────────────

    def load_segments(self, master: dict):
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for seg_name, seg_data in master.get("segments", {}).items():
            seg_id = f"{ticker}__{seg_name}"

            props = {
                "segment_id":        seg_id,
                "segment_name":      seg_name,
                "ticker_ref":        ticker,
                "sub_industry_code": seg_data.get("sub_industry_code"),
                "segment_type":      seg_data.get("segment_type"),
            }
            props = {k: v for k, v in props.items() if v is not None}

            # All metric tables — exact label as key
            props.update(table_to_props(seg_data.get("financials",          {})))
            props.update(table_to_props(seg_data.get("operational_metrics", {})))
            props.update(table_to_props(seg_data.get("unit_economics",      {})))

            # Capacity — rich detail per label per period
            props.update(structured_to_props(seg_data.get("capacity",             {})))
            props.update(structured_to_props(seg_data.get("geographic_breakdown", {})))
            props.update(structured_to_props(seg_data.get("pnl_drivers",         {})))
            props.update(structured_to_props(seg_data.get("guidance",            {})))
            props.update(structured_to_props(seg_data.get("business_description",{})))

            self.run("""
                MERGE (s:Segment {segment_id: $segment_id})
                SET s += $props
            """, segment_id=seg_id, props=props)

            self.run("""
                MATCH (c:Company {ticker: $ticker})
                MATCH (s:Segment {segment_id: $segment_id})
                MERGE (c)-[:HAS_SEGMENT]->(s)
            """, ticker=ticker, segment_id=seg_id)

            count += 1

        print(f"    {count} Segment nodes")

    # ── Person nodes ───────────────────────────────────────────────────────────

    def load_people(self, master: dict):
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for person_name, person_data in master.get("people", {}).items():
            person_id = f"{ticker}__{person_name}"

            props = {
                "person_id":     person_id,
                "full_name":     person_name,
                "ticker_ref":    ticker,
                "date_of_birth": person_data.get("date_of_birth"),
                "nationality":   person_data.get("nationality"),
                "gender":        person_data.get("gender"),
            }
            props = {k: v for k, v in props.items() if v is not None}

            # Role, compensation, shareholding, background — exact labels
            props.update(structured_to_props(person_data.get("role",         {})))
            props.update(structured_to_props(person_data.get("background",   {})))
            props.update(table_to_props(     person_data.get("compensation", {})))
            props.update(table_to_props(     person_data.get("shareholding", {})))
            props.update(structured_to_props(person_data.get("track_record", {})))

            self.run("""
                MERGE (p:Person {person_id: $person_id})
                SET p += $props
            """, person_id=person_id, props=props)

            # WORKS_FOR edge — role and all periods seen
            periods_seen = sorted({
                period
                for label, period_data in person_data.get("role", {}).items()
                if isinstance(period_data, dict)
                for period in period_data.keys()
            })
            # Latest role text
            latest_role = None
            for label, period_data in person_data.get("role", {}).items():
                if isinstance(period_data, dict) and period_data:
                    latest_p = sorted(period_data.keys())[-1]
                    slot = period_data[latest_p]
                    val  = slot.get("value") if isinstance(slot, dict) else slot
                    if val:
                        latest_role = str(val)
                        break

            self.run("""
                MATCH (p:Person  {person_id: $person_id})
                MATCH (c:Company {ticker:    $ticker})
                MERGE (p)-[r:WORKS_FOR]->(c)
                SET r.role         = $role,
                    r.periods_seen = $periods_seen
            """, person_id=person_id, ticker=ticker,
                     role=latest_role or "Unknown",
                     periods_seen=periods_seen)

            count += 1

        print(f"    {count} Person nodes")

    # ── Regulator nodes ────────────────────────────────────────────────────────

    def load_regulators(self, master: dict):
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for reg_key, reg_data in master.get("regulators", {}).items():
            reg_name = reg_data.get("name") or reg_key

            props = {
                "name":             reg_name,
                "acronym":          reg_data.get("acronym"),
                "type":             reg_data.get("type"),
                "jurisdiction":     reg_data.get("jurisdiction"),
                "sector_regulated": reg_data.get("sector_regulated"),
            }
            props = {k: v for k, v in props.items() if v is not None}

            self.run("""
                MERGE (r:Regulator {name: $name})
                SET r += $props
            """, name=reg_name, props=props)

            self.run("""
                MATCH (c:Company  {ticker: $ticker})
                MATCH (r:Regulator {name:  $reg_name})
                MERGE (c)-[rel:REGULATED_BY]->(r)
                SET rel.periods_seen = $periods_seen
            """, ticker=ticker, reg_name=reg_name,
                     periods_seen=reg_data.get("periods_seen", []))

            count += 1

        print(f"    {count} Regulator nodes")

    # ── ExternalEntity nodes ───────────────────────────────────────────────────

    def load_external_entities(self, master: dict):
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for ent_key, ent_data in master.get("external_entities", {}).items():
            ent_name = ent_data.get("name") or ent_key

            props = {
                "name":              ent_name,
                "type":              ent_data.get("type"),
                "country":           ent_data.get("country"),
                "sector":            ent_data.get("sector"),
                "sub_industry_code": ent_data.get("sub_industry_code"),
                "listed":            ent_data.get("listed"),
                "ticker":            ent_data.get("ticker"),
                "periods_seen":      as_json(ent_data.get("periods_seen", [])),
            }
            props = {k: v for k, v in props.items() if v is not None}

            self.run("""
                MERGE (e:ExternalEntity {name: $name})
                SET e += $props
            """, name=ent_name, props=props)

            count += 1

        print(f"    {count} ExternalEntity nodes")

    # ── Relationships ──────────────────────────────────────────────────────────

    def load_relationships(self, master: dict):
        """
        RELATES_TO edges — one edge per relationship entry.
        Edge carries: relationship_type, period, + all property k/v from JSON.
        """
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for rel_key, rel_data in master.get("relationships", {}).items():
            from_node = rel_data.get("from_node")
            to_node   = rel_data.get("to_node")
            rel_type  = rel_data.get("relationship_type", "RELATES_TO")
            if not from_node or not to_node:
                continue

            # Ensure target entity exists
            self.run("MERGE (e:ExternalEntity {name: $name})", name=to_node)

            # Build edge properties — include everything from the JSON
            edge_props = {
                "relationship_type": rel_type,
                "from_node":         from_node,
                "to_node":           to_node,
                "from_type":         rel_data.get("from_type", ""),
                "to_type":           rel_data.get("to_type", ""),
            }

            # Add all period-keyed properties onto the edge
            properties = rel_data.get("properties", {})
            if isinstance(properties, dict):
                for period, prop_map in properties.items():
                    if isinstance(prop_map, dict):
                        for prop_label, prop_val in prop_map.items():
                            if prop_val is not None:
                                # Key: "{period}__{prop_label}"
                                key = f"{period}__{prop_label}"
                                edge_props[key] = str(prop_val)
                    elif prop_map is not None:
                        edge_props[period] = str(prop_map)

            # Store full properties as JSON too for easy retrieval
            edge_props["properties_json"] = as_json(properties)

            self.run("""
                MATCH (c:Company      {ticker: $ticker})
                MATCH (e:ExternalEntity {name: $to_node})
                MERGE (c)-[r:RELATES_TO {
                    relationship_type: $rel_type,
                    to_node: $to_node
                }]->(e)
                SET r += $edge_props
            """, ticker=ticker, to_node=to_node,
                     rel_type=rel_type, edge_props=edge_props)

            count += 1

        print(f"    {count} RELATES_TO edges")

    # ── Debt / FINANCED_BY edges ───────────────────────────────────────────────

    def load_debt(self, master: dict):
        """
        FINANCED_BY edges — one edge per instrument per period per lender.
        Edge carries all debt fields: rate, amount, security, rating, maturity etc.
        """
        ticker = master.get("ticker", "UNKNOWN")
        count  = 0

        for instr_label, period_data in master.get("debt_schedule", {}).items():
            if not isinstance(period_data, dict):
                continue

            for period, detail in period_data.items():
                if not isinstance(detail, dict):
                    continue

                lender = detail.get("lender")
                if not lender:
                    continue

                # Ensure lender entity exists
                self.run("MERGE (e:ExternalEntity {name: $name})", name=lender)

                # Edge properties — all debt fields exactly as in JSON
                edge_props = {
                    "instrument_label": instr_label,
                    "period":           period,
                }
                for field, value in detail.items():
                    if value is not None:
                        edge_props[field] = (
                            str(value) if isinstance(value, (dict, list))
                            else value
                        )

                self.run("""
                    MATCH (c:Company      {ticker: $ticker})
                    MATCH (e:ExternalEntity {name: $lender})
                    MERGE (c)-[r:FINANCED_BY {
                        instrument_label: $instr_label,
                        period:           $period
                    }]->(e)
                    SET r += $edge_props
                """, ticker=ticker, lender=lender,
                         instr_label=instr_label, period=period,
                         props=edge_props, edge_props=edge_props)

                count += 1

        print(f"    {count} FINANCED_BY edges")

    # ── Load one company ───────────────────────────────────────────────────────

    def load(self, master_path: str) -> str:
        print(f"\nLoading: {Path(master_path).name}")
        master  = json.loads(Path(master_path).read_text(encoding="utf-8"))
        ticker  = master.get("ticker", "UNKNOWN")
        company = master.get("company", ticker)
        annual  = master.get("periods", {}).get("annual",    [])
        qtr     = master.get("periods", {}).get("quarterly", [])
        print(f"  {company} ({ticker})")
        print(f"  {len(annual)} annual + {len(qtr)} quarterly periods")

        self.load_company(master)
        self.load_segments(master)
        self.load_people(master)
        self.load_regulators(master)
        self.load_external_entities(master)
        self.load_relationships(master)
        self.load_debt(master)

        print(f"  ✓ Done: {company} ({ticker})")
        return ticker


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Load normalised master JSON(s) into Neo4j."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--master", nargs="+",
        help="One or more normalised_master.json file paths"
    )
    group.add_argument(
        "--master-dir",
        help="Folder containing *_normalised_master.json files"
    )
    parser.add_argument("--uri",      default="bolt://127.0.0.1:7687")
    parser.add_argument("--user",     default="neo4j")
    parser.add_argument("--password", default=os.environ.get("NEO4J_PASSWORD"))
    args = parser.parse_args()

    if not args.password:
        print("ERROR: Provide --password or set NEO4J_PASSWORD env var")
        sys.exit(1)

    # Collect files
    files: list[Path] = []
    if args.master:
        for p in args.master:
            fp = Path(p)
            if not fp.exists():
                print(f"ERROR: Not found: {fp}")
                sys.exit(1)
            files.append(fp)
    else:
        d = Path(args.master_dir)
        files = sorted(d.glob("*_normalised_master.json"))
        if not files:
            print(f"ERROR: No *_normalised_master.json in {d}")
            sys.exit(1)
        print(f"Found {len(files)} files in {d}")

    etl = Neo4jETL(args.uri, args.user, args.password)
    try:
        etl.create_constraints()
        loaded, failed = [], []
        for fp in files:
            try:
                loaded.append(etl.load(str(fp)))
            except Exception as e:
                print(f"  ✗ Failed {fp.name}: {e}")
                failed.append(fp.name)

        print(f"\n{'='*60}")
        print(f"ETL COMPLETE — {len(loaded)} companies loaded")
        if loaded: print(f"  {loaded}")
        if failed: print(f"  Failed: {failed}")
        print()
        print("Verify in Neo4j Browser (http://localhost:7474):")
        print("  MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count ORDER BY count DESC")
        print("  MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS count ORDER BY count DESC")
        for t in loaded:
            print(f"  MATCH (c:Company {{ticker:'{t}'}})-[r]->(n) RETURN c,r,n LIMIT 100")
    finally:
        etl.close()


if __name__ == "__main__":
    main()