# Cityflo on-time performance — MCP server + decision

- `DECISION.md` — the verdict for Priya (worst-three, cleared, incident, each call defended).
- `decisions.jsonl` — steering ledger; anchors are line numbers in the raw session transcript.
- `cityflo_otp/` — the MCP server (`server.py`) and the lateness rules it serves (`lateness.py`).
- `verify_decision.py` — re-derives every number in `DECISION.md` from the CSVs and drives the server over stdio.
- `INSPECTION_NOTES.md`, `LATENESS_RULE_NOTES.md` — working notes from the session (see their errata sections).

## Run

Requires Python 3.10+ and `pip install "mcp>=1.2"`.

```bash
python -m cityflo_otp.server          # stdio MCP server
python verify_decision.py             # all checks should print PASS
```

Data defaults to `data/` (the bundle's files, unmodified). Point it elsewhere, e.g. at a fresh week, with
`CITYFLO_DATA_DIR=/path/to/data`, or pass `data_dir` to any tool.

**Claude Code:** `.mcp.json` in this folder registers the server as `cityflo-otp`; open Claude Code here and
approve it. Or run `claude mcp add cityflo-otp -- python -m cityflo_otp.server` from this folder.

## Tools

| tool | answers |
|---|---|
| `route_verdicts` | one verdict per route, with median / p90 / mean / n |
| `rank_routes(top_n)` | worst-first ranking |
| `route_detail(route)` | daily medians, excluded rows, and for REC-114 routes the before/after on both timetables |
| `incident_flags(trip_threshold_min=30, cluster_min=3)` | incident route-days; lower the threshold to find moderate clusters |
| `trip_lookup(trip_id)` | one trip as scored |
| `data_quality_report` | every excluded or corrected row, by trip id |
