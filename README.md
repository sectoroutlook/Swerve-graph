# Swerve Graph (static)

Static sector graph served by GitHub Pages: https://sectoroutlook.github.io/Swerve-graph/

`index.html` loads pre-made JSON files, with no backend at runtime:

- `graph-data.json`: the sector map (nodes and relationships)
- `data/<GEO>/<code>.json`: forces, viewpoints and market sizing for one sector in one country (`IN` India, `GB` United Kingdom, `EU` Europe), loaded when a node is clicked
- `data/index.json`: for each country, the sector codes that have data and the run / batch they came from
- `company-data/`: company tab data

## How to refresh

Re-export the outlook data for all three countries from Supabase (read-only):

```bash
python3 export_outlook_supabase.py
```

The script reads `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` from the environment, or from `../neo4j html/.env` / `./.env`. Use `--geographies GB EU` to export only some countries and `--dry-run` to print counts without writing. Then commit `data/` and push.
