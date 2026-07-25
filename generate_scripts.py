"""
Generalized parser: sector_value_chain_phase2_map.md -> SQL + Cypher
Reads the Row Summary Table and detail sections dynamically.
No hardcoded row counts, P2 IDs, or sector codes.
Strict: errors out if any row is missing notes or last_reviewed.
"""
import re
import sys

MAP_FILE = 'sector_value_chain_phase2_map.md'
SQL_OUT = 'phase2_supabase_insert.sql'
CYPHER_OUT = 'phase2_neo4j_merge.cypher'

with open(MAP_FILE, 'r') as f:
    content = f.read()

# ---------------------------------------------------------------------------
# 1. Parse Row Summary Table — only lines whose 2nd field matches P2-<num><letter?>
# ---------------------------------------------------------------------------
P2ID_RE = re.compile(r'^P2-\d+[a-z]?$')

summary_rows = {}
for line in content.split('\n'):
    line = line.strip()
    if not line.startswith('|'):
        continue
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 13:
        continue
    p2id = parts[1]
    if not P2ID_RE.match(p2id):
        continue
    summary_rows[p2id] = {
        'p2id': p2id,
        'from_in': parts[2],
        'to_in': parts[4],
        'from_sector': parts[6],
        'to_sector': parts[7],
        'strength': parts[8],
        'nature_raw': parts[9],
        'end_market_raw': parts[10],
    }

print(f"Found {len(summary_rows)} rows in Row Summary Table")

# ---------------------------------------------------------------------------
# 2. Find detail sections dynamically
# ---------------------------------------------------------------------------
lines = content.split('\n')
header_indices = []
for i, line in enumerate(lines):
    m = re.match(r'^####\s+(P2-\w+)', line.strip())
    if m and P2ID_RE.match(m.group(1)):
        header_indices.append((i, m.group(1)))

detail_blocks = {}
for idx, (line_idx, p2id) in enumerate(header_indices):
    start = line_idx
    end = header_indices[idx+1][0] if idx+1 < len(header_indices) else len(lines)
    detail_blocks[p2id] = '\n'.join(lines[start:end])

print(f"Found {len(detail_blocks)} detail sections")

# ---------------------------------------------------------------------------
# 3. Extract notes + last_reviewed (STRICT — error if missing)
# ---------------------------------------------------------------------------
def extract_notes(block):
    m = re.search(r'\*\*Notes:\*\*\s*(.*?)(?=\n\n\*\*(?:Strength rationale|Sources|Evidence sources|Flag status|Flag)|\n---|\Z)', block, re.DOTALL)
    if m:
        return ' '.join(m.group(1).split())
    return None

def extract_last_reviewed(block):
    m = re.search(r'\|\s*last_reviewed\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|', block)
    if m:
        return m.group(1)
    table_lines = re.findall(r'^\|.+\|\s*$', block, re.MULTILINE)
    for i, hline in enumerate(table_lines):
        cols = [c.strip() for c in hline.strip().strip('|').split('|')]
        if 'last_reviewed' in cols:
            col_idx = cols.index('last_reviewed')
            if i + 2 < len(table_lines):
                data_cols = [c.strip() for c in table_lines[i+2].strip().strip('|').split('|')]
                if col_idx < len(data_cols) and re.match(r'^\d{4}-\d{2}-\d{2}$', data_cols[col_idx]):
                    return data_cols[col_idx]
    return None

errors = []
rows = []
for p2id, summary in summary_rows.items():
    block = detail_blocks.get(p2id)
    if block is None:
        errors.append(f"{p2id}: no detail section found")
        continue
    notes = extract_notes(block)
    last_reviewed = extract_last_reviewed(block)
    if notes is None:
        errors.append(f"{p2id}: missing **Notes:** block")
    if last_reviewed is None:
        errors.append(f"{p2id}: missing last_reviewed date")
    if notes is None or last_reviewed is None:
        continue
    rows.append({**summary, 'notes': notes, 'last_reviewed': last_reviewed})

if errors:
    print(f"\n*** {len(errors)} ERRORS — fix these in the markdown before proceeding ***")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"\nAll {len(rows)} rows passed validation (notes + last_reviewed present)")

# ---------------------------------------------------------------------------
# 4. Field transformation helpers
# ---------------------------------------------------------------------------
def parse_nature(raw):
    """'capital, service' -> ['capital', 'service']"""
    items = [x.strip() for x in raw.split(',') if x.strip()]
    return items

def parse_end_market(raw):
    """'null' -> None ; 'B2B' -> ['B2B'] ; 'B2B/B2G' -> ['B2B','B2G'] ; 'B2B, B2G' -> ['B2B','B2G']"""
    raw = raw.strip()
    if raw.lower() == 'null' or raw == '':
        return None
    items = re.split(r'[,/]', raw)
    return [x.strip() for x in items if x.strip()]

def sql_array(items):
    escaped = [i.replace("'", "''") for i in items]
    return "ARRAY[" + ", ".join(f"'{i}'" for i in escaped) + "]::text[]"

def sql_string(s):
    return "'" + s.replace("'", "''") + "'"

def parse_type_c(from_in, to_in, from_sector, to_sector):
    """Detect Type C (one side is 'null (SEXX)') -> returns (from_node, to_node, edge_type)
    where node is ('SubIndustry', code) or ('Sector', sector_code)
    """
    null_pattern = re.compile(r'^null\s*\(([A-Z0-9]+)\)$')
    fm = null_pattern.match(from_in)
    tm = null_pattern.match(to_in)
    if fm:
        from_node = ('Sector', from_sector)
    else:
        from_node = ('SubIndustry', from_in)
    if tm:
        to_node = ('Sector', to_sector)
    else:
        to_node = ('SubIndustry', to_in)
    return from_node, to_node

# ---------------------------------------------------------------------------
# 5. Generate SQL
# ---------------------------------------------------------------------------
sql_lines = []
sql_lines.append("-- Phase 2 sector_value_chain inserts")
sql_lines.append(f"-- Generated from sector_value_chain_phase2_map.md — {len(rows)} rows")
sql_lines.append("")

for r in rows:
    from_in_raw = r['from_in']
    to_in_raw = r['to_in']
    null_pattern = re.compile(r'^null\s*\(([A-Z0-9]+)\)$')

    from_sub = 'NULL' if null_pattern.match(from_in_raw) else sql_string(from_in_raw)
    to_sub = 'NULL' if null_pattern.match(to_in_raw) else sql_string(to_in_raw)

    nature_list = parse_nature(r['nature_raw'])
    end_market_list = parse_end_market(r['end_market_raw'])

    nature_sql = sql_array(nature_list)
    end_market_sql = 'NULL' if end_market_list is None else sql_array(end_market_list)

    sql = f"""INSERT INTO sector_value_chain
  (from_sector_code, to_sector_code, from_sub_industry_code, to_sub_industry_code,
   relationship, strength, nature, end_market, notes, last_reviewed)
VALUES
  ({sql_string(r['from_sector'])}, {sql_string(r['to_sector'])}, {from_sub}, {to_sub},
   'BUYS_FROM', {sql_string(r['strength'])}, {nature_sql}, {end_market_sql},
   {sql_string(r['notes'])}, '{r['last_reviewed']}')
ON CONFLICT ON CONSTRAINT sector_value_chain_unique_edge DO NOTHING;
-- {r['p2id']}
"""
    sql_lines.append(sql)

with open(SQL_OUT, 'w') as f:
    f.write('\n'.join(sql_lines))

print(f"\nWrote {SQL_OUT} ({len(rows)} INSERT statements)")

# ---------------------------------------------------------------------------
# 6. Generate Cypher
# ---------------------------------------------------------------------------
cypher_lines = []
cypher_lines.append("// Phase 2 sector_value_chain MERGE statements")
cypher_lines.append(f"// Generated from sector_value_chain_phase2_map.md — {len(rows)} rows")
cypher_lines.append("")

type_c_count = 0
for r in rows:
    from_node, to_node = parse_type_c(r['from_in'], r['to_in'], r['from_sector'], r['to_sector'])
    if from_node[0] == 'Sector' or to_node[0] == 'Sector':
        type_c_count += 1

    nature_list = parse_nature(r['nature_raw'])
    end_market_list = parse_end_market(r['end_market_raw'])

    def cy_str(s):
        return '"' + s.replace('"', '\\"').replace('\\', '\\\\') + '"'

    nature_cy = "[" + ", ".join(cy_str(n) for n in nature_list) + "]"
    end_market_cy = "null" if end_market_list is None else "[" + ", ".join(cy_str(e) for e in end_market_list) + "]"

    cypher = f"""MATCH (a:{from_node[0]} {{code: '{from_node[1]}'}}), (b:{to_node[0]} {{code: '{to_node[1]}'}})
MERGE (a)-[r:BUYS_FROM]->(b)
SET r.strength = '{r['strength']}',
    r.nature = {nature_cy},
    r.end_market = {end_market_cy},
    r.notes = {cy_str(r['notes'])},
    r.last_reviewed = date('{r['last_reviewed']}'),
    r.p2_id = '{r['p2id']}';
"""
    cypher_lines.append(cypher)

with open(CYPHER_OUT, 'w') as f:
    f.write('\n'.join(cypher_lines))

print(f"Wrote {CYPHER_OUT} ({len(rows)} MERGE statements, {type_c_count} Type C mixed-node edges)")
