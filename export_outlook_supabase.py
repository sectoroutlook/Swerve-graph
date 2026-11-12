"""
export_outlook_supabase.py

Exports per-sector outlook data (forces / viewpoints / market sizing) from
Supabase into static JSON files for the GitHub Pages graph:

    data/<GEO>/<sector_code>.json   one file per sector with data, per geography
    data/index.json                 per geography: name, which sector codes have
                                    data, latest batch / run date and, per table,
                                    the run_id / batch_id used

Each data/<GEO>/<code>.json has the same shape export_graph_json.py used to
write into data/<code>.json (forces / viewpoints / market_sizing / sources),
plus:
    - "geography" at the top level
    - "documents": the source documents referenced by this sector's rows
    - on every row: source_doc_id, source_title, source_publisher,
      source_url (from the documents table, where available)
    - country_focus on every row, for geographies where at least one row
      has it set (today only EU: EU / IE / NO / ..., may be null)

Geographies are not hard-coded: every distinct `geography` value found in the
three outlook tables is exported, so a new country appears after its first
run. Names come from the countries table (iso2 -> name), falling back to the
code; NAME_OVERRIDES changes only how a name is displayed.

"Latest" rule (same as neo4j_populate.py's _latest_run_id): per table, per
sector_code + geography, only the rows with the newest run_id are used.

Supabase is only READ. Credentials come from env vars SUPABASE_URL and
SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY), falling back to a .env file
(--env-file, default ../neo4j html/.env, then ./.env). The key is never
written to any output.

Usage:
    python3 export_outlook_supabase.py                      # every geography found
    python3 export_outlook_supabase.py --geographies GB EU  # only these (index merged)
    python3 export_outlook_supabase.py --dry-run            # counts only
    python3 export_outlook_supabase.py --out-dir /tmp/x     # write somewhere else
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ENV_FILES = [os.path.join(HERE, "..", "neo4j html", ".env"), os.path.join(HERE, ".env")]
DATA_DIR = os.path.join(HERE, "data")
PAGE_SIZE = 1000

# Display names that differ from the countries table. EU is one Europe-wide
# outlook (Euronext), so it is shown as "Europe" rather than "European Union".
NAME_OVERRIDES = {"EU": "Europe"}
TABLES = ("sector_forces", "sector_viewpoints", "sector_market_sizing")


# ─── Supabase (PostgREST, read-only) ─────────────────────────────────────────

def _read_env_file(path: str) -> dict:
    values = {}
    if not os.path.isfile(path):
        return values
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def _credentials(env_file: str | None) -> tuple[str, str]:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
    for path in ([env_file] if env_file else DEFAULT_ENV_FILES):
        if url and key:
            break
        vals = _read_env_file(path)
        url = url or vals.get("SUPABASE_URL")
        key = key or vals.get("SUPABASE_SERVICE_ROLE_KEY") or vals.get("SUPABASE_KEY")
    if not (url and key):
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY not found in env or .env file")
    return url.rstrip("/") + "/rest/v1/", key


class Supabase:
    def __init__(self, base: str, key: str):
        self.base = base
        self.session = requests.Session()
        self.session.headers.update({"apikey": key, "Accept": "application/json"})

    def select_all(self, table: str, params: dict) -> list[dict]:
        rows, offset = [], 0
        while True:
            headers = {"Range-Unit": "items", "Range": f"{offset}-{offset + PAGE_SIZE - 1}"}
            r = self.session.get(self.base + table, params=params, headers=headers, timeout=60)
            if not r.ok:
                sys.exit(f"Supabase read of {table} failed: HTTP {r.status_code}")
            page = r.json()
            rows.extend(page)
            if len(page) < PAGE_SIZE:
                return rows
            offset += PAGE_SIZE


def latest_rows(sb: Supabase, table: str, geography: str) -> dict[str, list[dict]]:
    """sector_code -> rows from that sector's newest run_id (ordered by id)."""
    rows = sb.select_all(table, {"select": "*", "geography": f"eq.{geography}", "order": "id.asc"})
    by_code: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row.get("sector_code"):
            by_code[row["sector_code"]].append(row)
    result = {}
    for code, code_rows in by_code.items():
        run_ids = [r["run_id"] for r in code_rows if r.get("run_id")]
        latest = max(run_ids) if run_ids else None
        result[code] = [r for r in code_rows if r.get("run_id") == latest] if latest else code_rows
    return result


def discover_geographies(sb: Supabase) -> list[str]:
    """Distinct geography values across the three outlook tables."""
    geos: set[str] = set()
    for table in TABLES:
        geos.update(r["geography"] for r in sb.select_all(table, {"select": "geography"}) if r.get("geography"))
    return sorted(geos)


def country_names(sb: Supabase, codes: list[str]) -> dict[str, str]:
    """iso2 -> display name: NAME_OVERRIDES, else countries.name, else the code."""
    names = {}
    if codes:
        for row in sb.select_all("countries", {"select": "iso2,name", "iso2": "in.(" + ",".join(codes) + ")"}):
            if row.get("name"):
                names[row["iso2"]] = row["name"]
    return {c: NAME_OVERRIDES.get(c) or names.get(c) or c for c in codes}


def fetch_documents(sb: Supabase, doc_ids: set[str]) -> dict[str, dict]:
    docs, ids = {}, sorted(doc_ids)
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        for d in sb.select_all("documents", {
            "select": "doc_id,title,source,date,url",
            "doc_id": "in.(" + ",".join(chunk) + ")",
        }):
            docs[d["doc_id"]] = d
    return docs


# ─── Reshape (mirrors neo4j_populate.write_to_neo4j + neo4j_retrieval reshape) ─

def _str_or_none(v):
    return None if v is None or v == "" else str(v)


def _float_or_none(v):
    return float(v) if v is not None else None


def _with_source(entry: dict, row: dict, docs: dict, with_focus: bool) -> dict:
    doc = docs.get(row.get("source_doc_id") or "") or {}
    entry["source_doc_id"] = _str_or_none(row.get("source_doc_id"))
    entry["source_title"] = doc.get("title")
    entry["source_publisher"] = doc.get("source")
    entry["source_url"] = doc.get("url")
    if "source_date" not in entry:
        entry["source_date"] = _str_or_none(doc.get("date"))
    if with_focus:
        entry["country_focus"] = row.get("country_focus")
    return entry


def reshape_force(i: int, f: dict, docs: dict, with_focus: bool) -> dict:
    return _with_source({
        "index": i,
        "title": f.get("title"),
        "description": f.get("description"),
        "type": f.get("force_type"),
        "impact_magnitude": f.get("impact_magnitude"),
        "time_horizon": f.get("time_horizon"),
        "as_of_date": _str_or_none(f.get("as_of_date")),
    }, f, docs, with_focus)


def reshape_viewpoint(i: int, v: dict, docs: dict, with_focus: bool) -> dict:
    return _with_source({
        "index": i,
        "title": v.get("viewpoint_title"),
        "description": v.get("viewpoint_description"),
        "stance": v.get("stance"),
        "source_firm": v.get("source_firm"),
        "source_date": _str_or_none(v.get("source_date")),
    }, v, docs, with_focus)


def reshape_sizing(i: int, m: dict, docs: dict, with_focus: bool) -> dict:
    return _with_source({
        "index": i,
        "tam_value": _float_or_none(m.get("tam_value")),
        "tam_unit": m.get("tam_unit"),
        "sam_value": _float_or_none(m.get("sam_value")),
        "as_of_year": m.get("as_of_year"),
        "forecast_cagr": _float_or_none(m.get("forecast_cagr")),
        "forecast_cagr_period": m.get("forecast_cagr_period"),
        "historical_cagr": _float_or_none(m.get("historical_cagr")),
        "historical_cagr_period": m.get("historical_cagr_period"),
        "demand_drivers": m.get("demand_drivers") or [],
        "pnl_drivers": m.get("pnl_drivers") or [],
        "new_opportunities": m.get("new_opportunities") or [],
        "methodology": m.get("sizing_methodology"),
        "source_firm": m.get("source_firm"),
        "source_date": _str_or_none(m.get("source_date")),
        "data_confidence": m.get("data_confidence"),
    }, m, docs, with_focus)


def collect_sources(viewpoints: list[dict], sizing: list[dict]) -> list[str]:
    """Same as neo4j_retrieval._collect_sources: deduped source_firm values."""
    seen: list[str] = []
    for rec in viewpoints + sizing:
        firm = rec.get("source_firm")
        if firm and firm not in seen:
            seen.append(firm)
    return seen


# ─── Export ──────────────────────────────────────────────────────────────────

def export_geography(sb: Supabase, geo: str, dry_run: bool, data_dir: str) -> dict:
    tables = {t: latest_rows(sb, t, geo) for t in TABLES}
    codes = sorted(set().union(*[set(v) for v in tables.values()]))
    used_rows = [r for t in tables.values() for rows in t.values() for r in rows]
    # country_focus only where this geography actually uses it (EU today).
    with_focus = any(r.get("country_focus") for r in used_rows)

    doc_ids = {r["source_doc_id"] for t in tables.values() for rows in t.values()
               for r in rows if r.get("source_doc_id")}
    docs = fetch_documents(sb, doc_ids) if doc_ids else {}

    counts = {"sectors": len(codes), "forces": 0, "viewpoints": 0, "market_sizing": 0,
              "documents_referenced": len(doc_ids), "documents_found": len(docs)}
    index_entries = {}
    out_dir = os.path.join(data_dir, geo)

    if not dry_run:
        os.makedirs(out_dir, exist_ok=True)
        for stale in glob.glob(os.path.join(out_dir, "*.json")):
            os.remove(stale)

    for code in codes:
        f_rows = tables["sector_forces"].get(code, [])
        v_rows = tables["sector_viewpoints"].get(code, [])
        m_rows = tables["sector_market_sizing"].get(code, [])
        forces = [reshape_force(i, r, docs, with_focus) for i, r in enumerate(f_rows, 1)]
        viewpoints = [reshape_viewpoint(i, r, docs, with_focus) for i, r in enumerate(v_rows, 1)]
        sizing = [reshape_sizing(i, r, docs, with_focus) for i, r in enumerate(m_rows, 1)]
        counts["forces"] += len(forces)
        counts["viewpoints"] += len(viewpoints)
        counts["market_sizing"] += len(sizing)

        # Each table falls back to its own newest run, so a sector's sections
        # can come from different batches — record run/batch per table.
        index_entries[code] = {
            key: {
                "count": len(rows),
                "run_id": rows[0].get("run_id") if rows else None,
                "batch_id": rows[0].get("batch_id") if rows else None,
            }
            for key, rows in (("forces", f_rows), ("viewpoints", v_rows), ("market_sizing", m_rows))
        }

        if dry_run:
            continue
        doc_list = []
        for rec in viewpoints + forces + sizing:
            d = docs.get(rec.get("source_doc_id") or "")
            if d and all(x["doc_id"] != d["doc_id"] for x in doc_list):
                doc_list.append({"doc_id": d["doc_id"], "title": d.get("title"),
                                 "publisher": d.get("source"), "date": _str_or_none(d.get("date")),
                                 "url": d.get("url")})
        payload = {
            "geography": geo,
            "forces": forces,
            "viewpoints": viewpoints,
            "market_sizing": sizing,
            "sources": collect_sources(viewpoints, sizing),
            "documents": doc_list,
        }
        with open(os.path.join(out_dir, f"{code}.json"), "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)

    run_ids = [r["run_id"] for r in used_rows if r.get("run_id")]
    batch_ids = [r["batch_id"] for r in used_rows if r.get("batch_id")]
    latest_run = max(run_ids) if run_ids else None
    return {
        "counts": counts,
        "sectors": index_entries,
        "latest_batch_id": max(batch_ids) if batch_ids else None,
        # run_id is YYYYMMDD_HHMMSS
        "latest_run_date": f"{latest_run[:4]}-{latest_run[4:6]}-{latest_run[6:8]}" if latest_run else None,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--geographies", nargs="+", metavar="CODE",
                    help="only these geography codes (default: every geography found in the outlook tables)")
    ap.add_argument("--dry-run", action="store_true", help="read and count only; write nothing")
    ap.add_argument("--out-dir", default=DATA_DIR, help="output folder (default: data/ next to this script)")
    ap.add_argument("--env-file", help="path to a .env with SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
    args = ap.parse_args()

    sb = Supabase(*_credentials(args.env_file))
    found = discover_geographies(sb)
    geos = [g.upper() for g in args.geographies] if args.geographies else found
    missing = [g for g in geos if g not in found]
    if missing:
        print(f"no outlook rows for: {' '.join(missing)} (found: {' '.join(found)})")
        geos = [g for g in geos if g in found]
    names = country_names(sb, geos)

    # A full export rebuilds the index (countries no longer in Supabase drop
    # out); a --geographies export merges into the existing one.
    index_path = os.path.join(args.out_dir, "index.json")
    index = {"geographies": {}}
    if args.geographies and os.path.isfile(index_path):
        with open(index_path, encoding="utf-8") as fh:
            index = json.load(fh)

    for geo in geos:
        result = export_geography(sb, geo, args.dry_run, args.out_dir)
        c = result["counts"]
        print(f"{geo:3} {names[geo]:22} sectors={c['sectors']:4}  viewpoints={c['viewpoints']:5}  "
              f"forces={c['forces']:5}  sizing={c['market_sizing']:5}  "
              f"docs={c['documents_found']}/{c['documents_referenced']}")
        batches = sorted({t["batch_id"] for e in result["sectors"].values() for t in e.values() if t["batch_id"]})
        index["geographies"][geo] = {
            "code": geo,
            "name": names[geo],
            "label": names[geo],
            "sector_count": len(result["sectors"]),
            "latest_batch_id": result["latest_batch_id"],
            "latest_run_date": result["latest_run_date"],
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "batch_ids": batches,
            "codes": sorted(result["sectors"]),
            "sectors": result["sectors"],
        }

    if args.dry_run:
        print("dry run: nothing written")
        return
    index["generated_at"] = datetime.now(timezone.utc).isoformat()
    os.makedirs(args.out_dir, exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)
    print(f"wrote {index_path}")


if __name__ == "__main__":
    main()
