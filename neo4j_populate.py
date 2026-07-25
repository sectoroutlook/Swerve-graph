"""
Neo4j Sector Outlook Population Script
────────────────────────────────────────
Reads sector intelligence from three Supabase tables and writes it
directly as properties onto the existing :Sector, :IndustryGroup,
or :SubIndustry nodes in Neo4j.

No intermediate :SectorOutlook node. No child nodes. No relationships created.
Outlook data lives as flat numbered properties on the taxonomy node itself.

Property naming convention:
  outlook_stance, outlook_date, outlook_updated_at, outlook_geography
  vp_1_source_firm, vp_1_stance, vp_1_title, vp_1_description, ...
  force_1_type, force_1_title, force_1_description, force_1_impact_magnitude, ...
  sizing_1_as_of_year, sizing_1_tam_value, sizing_1_tam_unit, ...
  sizing_1_demand_drivers (JSON string), sizing_1_pnl_drivers (JSON string), ...

On re-run: all existing outlook_* / vp_* / force_* / sizing_* properties
are removed before new ones are written — no stale data.

Usage:
    python neo4j_populate.py --sector SE02
    python neo4j_populate.py --sectors SE02 SE07 SE06
    python neo4j_populate.py                           # all sectors with data
    python neo4j_populate.py --cleanup-old-nodes       # delete legacy :SectorOutlook nodes
"""

import os
import json
import logging
import argparse
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

from supabase import create_client, Client
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

load_dotenv()

# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
_run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_DIR / f"neo4j_{_run_ts}.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neo4j.io").setLevel(logging.WARNING)
logging.getLogger("neo4j.pool").setLevel(logging.WARNING)
logging.getLogger("neo4j.bolt").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("neo4j_populate")

# ─── Environment ─────────────────────────────────────────────────────────────

SUPABASE_URL         = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
NEO4J_URI            = os.environ.get("NEO4J_URI")
NEO4J_USERNAME       = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD       = os.environ.get("NEO4J_PASSWORD")

# ─── Node Label Resolver ──────────────────────────────────────────────────────

def _node_label(code: str) -> str:
    """Resolve Neo4j node label from code prefix."""
    if code.startswith("SE"):
        return "Sector"
    elif code.startswith("IG"):
        return "IndustryGroup"
    elif code.startswith("IN"):
        return "SubIndustry"
    raise ValueError(f"Unknown code prefix: {code!r} — expected SE/IG/IN")


# ─── Stance Computation ──────────────────────────────────────────────────────

STANCE_ORDER = [
    "negative",
    "cautious_negative",
    "neutral",
    "cautious_positive",
    "positive",
]

def compute_overall_stance(viewpoints: list) -> str:
    """
    Derive overall stance from viewpoints by majority vote.
    Ties broken toward caution (the more negative option).
    Returns 'neutral' if no viewpoints.
    """
    if not viewpoints:
        return "neutral"
    stances = [vp.get("stance", "neutral") for vp in viewpoints if vp.get("stance")]
    if not stances:
        return "neutral"
    counter   = Counter(stances)
    max_count = max(counter.values())
    tied      = [s for s, c in counter.items() if c == max_count]
    if len(tied) == 1:
        return tied[0]
    for stance in STANCE_ORDER:
        if stance in tied:
            return stance
    return tied[0]


# ─── Supabase Readers ─────────────────────────────────────────────────────────

def _latest_run_id(table: str, sector_code: str, geography: str, sb: Client) -> str | None:
    """
    Return the lexicographically largest run_id for this node.
    run_id format is YYYYMMDD_HHMMSS, so max() == most recent run.
    Returns None if the column doesn't exist or no rows found.
    """
    try:
        result = (
            sb.table(table)
            .select("run_id")
            .eq("sector_code", sector_code)
            .eq("geography", geography)
            .not_.is_("run_id", "null")
            .execute()
        )
        rows = result.data or []
        ids  = [r["run_id"] for r in rows if r.get("run_id")]
        return max(ids) if ids else None
    except Exception:
        return None


def read_viewpoints(sector_code: str, geography: str, sb: Client) -> list:
    run_id = _latest_run_id("sector_viewpoints", sector_code, geography, sb)
    q = (
        sb.table("sector_viewpoints")
        .select("*")
        .eq("sector_code", sector_code)
        .eq("geography", geography)
    )
    if run_id:
        q = q.eq("run_id", run_id)
    return q.execute().data or []


def read_market_sizing(sector_code: str, geography: str, sb: Client) -> list:
    run_id = _latest_run_id("sector_market_sizing", sector_code, geography, sb)
    q = (
        sb.table("sector_market_sizing")
        .select("*")
        .eq("sector_code", sector_code)
        .eq("geography", geography)
    )
    if run_id:
        q = q.eq("run_id", run_id)
    return q.execute().data or []


def read_forces(sector_code: str, geography: str, sb: Client) -> list:
    run_id = _latest_run_id("sector_forces", sector_code, geography, sb)
    q = (
        sb.table("sector_forces")
        .select("*")
        .eq("sector_code", sector_code)
        .eq("geography", geography)
    )
    if run_id:
        q = q.eq("run_id", run_id)
    return q.execute().data or []


def discover_sector_codes(geography: str, sb: Client, page_size: int = 1000) -> list[str]:
    """
    Distinct sector_codes with outlook data in any Supabase outlook table.
    Includes nodes with only viewpoints, only market_sizing, or only forces.
    Paginates because PostgREST defaults to 1000 rows per request.
    """
    codes: set[str] = set()
    for table in ("sector_viewpoints", "sector_market_sizing", "sector_forces"):
        offset = 0
        while True:
            result = (
                sb.table(table)
                .select("sector_code")
                .eq("geography", geography)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = result.data or []
            for row in rows:
                code = row.get("sector_code")
                if code:
                    codes.add(code)
            if len(rows) < page_size:
                break
            offset += page_size
    return sorted(codes)


# ─── Neo4j Writer ─────────────────────────────────────────────────────────────

def _safe_str(val) -> str | None:
    """Serialise lists/dicts to JSON string for Neo4j property storage."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return str(val)


def write_to_neo4j(
    driver: Driver,
    sector_code: str,
    geography: str,
    extraction_date: str,
    overall_stance: str,
    viewpoints: list,
    market_sizing: list,
    forces: list,
    run_id: str | None = None,
    batch_id: str | None = None,
):
    label = _node_label(sector_code)

    with driver.session() as session:

        # ── 1. Verify node exists ─────────────────────────────────────────────
        result = session.run(
            f"MATCH (n:{label} {{code: $code}}) RETURN n.code AS found",
            code=sector_code,
        )
        if not result.single():
            log.warning(
                f"[{sector_code}] No :{label} node found with code={sector_code}. "
                f"Skipping. Ensure sector_master is loaded in Neo4j."
            )
            return False

        # ── 2. Remove all existing outlook properties ─────────────────────────
        # Read current property keys, filter to outlook-related ones, remove them
        result = session.run(
            f"MATCH (n:{label} {{code: $code}}) RETURN keys(n) AS k",
            code=sector_code,
        )
        record = result.single()
        if record:
            old_keys = [
                k for k in record["k"]
                if k.startswith(("outlook_", "vp_", "force_", "sizing_"))
            ]
            if old_keys:
                remove_clause = ", ".join(f"n.`{k}`" for k in old_keys)
                session.run(
                    f"MATCH (n:{label} {{code: $code}}) REMOVE {remove_clause}",
                    code=sector_code,
                )
                log.debug(
                    f"[{sector_code}] Removed {len(old_keys)} stale outlook properties"
                )

        # ── 3. Build flat properties dict ─────────────────────────────────────
        props: dict = {
            "outlook_stance":       overall_stance,
            "outlook_date":         extraction_date,
            "outlook_updated_at":   datetime.now(timezone.utc).isoformat(),
            "outlook_geography":    geography,
            "outlook_vp_count":     len(viewpoints),
            "outlook_force_count":  len(forces),
            "outlook_sizing_count": len(market_sizing),
            "outlook_run_id":       run_id,
            "outlook_batch_id":     batch_id,
        }

        # Viewpoints ── flat numbered properties
        for i, vp in enumerate(viewpoints, start=1):
            props[f"vp_{i}_source_firm"]   = vp.get("source_firm")
            props[f"vp_{i}_stance"]        = vp.get("stance")
            props[f"vp_{i}_title"]         = vp.get("viewpoint_title")
            props[f"vp_{i}_description"]   = vp.get("viewpoint_description")
            props[f"vp_{i}_source_date"]   = str(vp.get("source_date") or "")
            props[f"vp_{i}_source_doc_id"] = str(vp.get("source_doc_id") or "")

        # Forces ── flat numbered properties
        for i, f in enumerate(forces, start=1):
            props[f"force_{i}_type"]             = f.get("force_type")
            props[f"force_{i}_title"]            = f.get("title")
            props[f"force_{i}_description"]      = f.get("description")
            props[f"force_{i}_impact_magnitude"] = f.get("impact_magnitude")
            props[f"force_{i}_time_horizon"]     = f.get("time_horizon")
            props[f"force_{i}_as_of_date"]       = str(f.get("as_of_date") or "")

        # Market sizing ── scalars flat, nested arrays as JSON strings
        for i, ms in enumerate(market_sizing, start=1):
            props[f"sizing_{i}_as_of_year"]              = ms.get("as_of_year")
            props[f"sizing_{i}_tam_value"]               = float(ms["tam_value"]) if ms.get("tam_value") is not None else None
            props[f"sizing_{i}_tam_unit"]                = ms.get("tam_unit")
            props[f"sizing_{i}_sam_value"]               = float(ms["sam_value"]) if ms.get("sam_value") is not None else None
            props[f"sizing_{i}_forecast_cagr"]           = float(ms["forecast_cagr"]) if ms.get("forecast_cagr") is not None else None
            props[f"sizing_{i}_forecast_cagr_period"]    = ms.get("forecast_cagr_period")
            props[f"sizing_{i}_historical_cagr"]         = float(ms["historical_cagr"]) if ms.get("historical_cagr") is not None else None
            props[f"sizing_{i}_historical_cagr_period"]  = ms.get("historical_cagr_period")
            props[f"sizing_{i}_methodology"]             = ms.get("sizing_methodology")
            props[f"sizing_{i}_source_firm"]             = ms.get("source_firm")
            props[f"sizing_{i}_source_date"]             = str(ms.get("source_date") or "")
            props[f"sizing_{i}_data_confidence"]         = ms.get("data_confidence")
            props[f"sizing_{i}_demand_drivers"]          = _safe_str(ms.get("demand_drivers"))
            props[f"sizing_{i}_pnl_drivers"]             = _safe_str(ms.get("pnl_drivers"))
            props[f"sizing_{i}_new_opportunities"]       = _safe_str(ms.get("new_opportunities"))

        # Strip None values — Neo4j ignores missing properties cleanly
        props = {k: v for k, v in props.items() if v is not None}

        # ── 4. SET all properties on the existing node in one query ───────────
        # SET n += $props merges new properties without touching existing ones
        # (code, name, etc. are preserved)
        session.run(
            f"MATCH (n:{label} {{code: $code}}) SET n += $props",
            code  = sector_code,
            props = props,
        )
        log.debug(
            f"[{sector_code}] SET {len(props)} properties on :{label} {{code: {sector_code!r}}}"
        )
        return True


# ─── Legacy Cleanup ───────────────────────────────────────────────────────────

def cleanup_old_nodes(driver: Driver):
    """
    Delete all legacy :SectorOutlook nodes and their child nodes/relationships.
    Run once after migrating to the flat-property architecture.
    """
    with driver.session() as session:
        result = session.run(
            """
            MATCH (so:SectorOutlook)
            OPTIONAL MATCH (so)-[:HAS_VIEWPOINT|HAS_FORCE|HAS_SIZING]->(child)
            DETACH DELETE so, child
            RETURN count(so) AS deleted
            """
        )
        record  = result.single()
        deleted = record["deleted"] if record else 0
        log.info(f"Cleanup: deleted {deleted} legacy :SectorOutlook node(s) and all children")


# ─── Main ─────────────────────────────────────────────────────────────────────

def populate(sector_codes: list, geography: str = "IN"):
    missing = [
        k for k in ["SUPABASE_URL", "SUPABASE_SERVICE_KEY", "NEO4J_URI", "NEO4J_PASSWORD"]
        if not os.environ.get(k)
    ]
    if missing:
        raise EnvironmentError(
            f"Missing environment variables: {', '.join(missing)}\n"
            "Add NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD to your .env"
        )

    sb     = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

    log.info("=" * 60)
    log.info(f"  NEO4J OUTLOOK POPULATE  —  {_run_ts}")
    log.info(f"  Codes   : {', '.join(sector_codes)}")
    log.info(f"  Neo4j   : {NEO4J_URI}")
    log.info("=" * 60)

    results = {}

    for sector_code in sector_codes:
        log.info(f"── {sector_code} ──────────────────────────────────────────")
        try:
            # Read from Supabase (each function resolves latest run_id independently)
            viewpoints    = read_viewpoints(sector_code, geography, sb)
            market_sizing = read_market_sizing(sector_code, geography, sb)
            forces        = read_forces(sector_code, geography, sb)

            if not viewpoints and not forces and not market_sizing:
                log.warning(f"[{sector_code}] No data found in Supabase — skipping")
                results[sector_code] = "no_data"
                continue

            # Log which run_id was used per table (first row's run_id, or legacy null)
            vp_rid  = viewpoints[0].get("run_id")    if viewpoints    else None
            ms_rid  = market_sizing[0].get("run_id") if market_sizing else None
            f_rid   = forces[0].get("run_id")        if forces        else None
            run_ids = {r for r in (vp_rid, ms_rid, f_rid) if r}
            log.info(
                f"[{sector_code}] Read from Supabase — "
                f"{len(viewpoints)} viewpoints  "
                f"{len(market_sizing)} sizing  "
                f"{len(forces)} forces  "
                f"run_id(s)={run_ids or 'legacy/null'}"
            )

            # Compute overall stance — majority vote, no LLM
            overall_stance = compute_overall_stance(viewpoints)
            log.info(f"[{sector_code}] Overall stance: {overall_stance}")

            # Use most recent source_date as extraction_date
            all_dates = (
                [vp.get("source_date") for vp in viewpoints if vp.get("source_date")] +
                [f.get("as_of_date")   for f  in forces     if f.get("as_of_date")]
            )
            extraction_date = (
                max(str(d) for d in all_dates)
                if all_dates
                else datetime.now().date().isoformat()
            )

            # Write to Neo4j
            ok = write_to_neo4j(
                driver          = driver,
                sector_code     = sector_code,
                geography       = geography,
                extraction_date = extraction_date,
                overall_stance  = overall_stance,
                viewpoints      = viewpoints,
                market_sizing   = market_sizing,
                forces          = forces,
                run_id          = vp_rid or ms_rid or f_rid,
                batch_id        = (
                    (viewpoints[0].get("batch_id")    if viewpoints    else None) or
                    (market_sizing[0].get("batch_id") if market_sizing else None) or
                    (forces[0].get("batch_id")        if forces        else None)
                ),
            )

            if ok:
                log.info(f"[{sector_code}] ✓  Written to Neo4j")
                results[sector_code] = "success"
            else:
                results[sector_code] = "node_not_found"

        except Exception as e:
            log.exception(f"[{sector_code}] Failed: {type(e).__name__}: {e}")
            results[sector_code] = f"error: {e}"

    driver.close()

    log.info("=" * 60)
    log.info("  SUMMARY")
    log.info("=" * 60)
    for code, status in results.items():
        icon = "✓" if status == "success" else ("⚠" if status in ("no_data", "node_not_found") else "✗")
        log.info(f"  {icon} {code}  {status}")
    log.info("")
    return results


# ─── Entry Point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Populate Neo4j taxonomy nodes with outlook properties from Supabase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python neo4j_populate.py --sector SE02
  python neo4j_populate.py --sectors SE02 SE07 SE06
  python neo4j_populate.py                           # all codes with data
  python neo4j_populate.py --cleanup-old-nodes       # delete legacy :SectorOutlook nodes
        """,
    )
    parser.add_argument(
        "--sector", "--sectors", nargs="+", metavar="CODE",
        help="Codes to populate (SE02, IG0201, IN020301, etc.). "
             "If omitted, populates all codes that have data in Supabase.",
    )
    parser.add_argument(
        "--geography", default="IN",
        help="Geography code (default: IN)",
    )
    parser.add_argument(
        "--cleanup-old-nodes", action="store_true",
        help="Delete all legacy :SectorOutlook nodes and children before populating.",
    )
    args = parser.parse_args()

    # Connect Neo4j driver for cleanup if needed
    if args.cleanup_old_nodes:
        drv = GraphDatabase.driver(
            os.environ.get("NEO4J_URI"),
            auth=(os.environ.get("NEO4J_USERNAME", "neo4j"), os.environ.get("NEO4J_PASSWORD")),
        )
        cleanup_old_nodes(drv)
        drv.close()

    if args.sector:
        codes = args.sector
    else:
        sb    = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        codes = discover_sector_codes(args.geography, sb)
        if not codes:
            print(
                "No sector codes found with outlook data in Supabase "
                "(sector_viewpoints, sector_market_sizing, or sector_forces). "
                "Run the extraction pipeline first."
            )
            exit(0)
        log.info(
            f"Discovered {len(codes)} sector code(s) with data for geography={args.geography!r}"
        )

    populate(sector_codes=codes, geography=args.geography)
