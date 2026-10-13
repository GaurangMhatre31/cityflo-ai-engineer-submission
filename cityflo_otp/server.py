"""Cityflo on-time-performance MCP server (stdio).

Run:  python -m cityflo_otp.server        (from the submission folder)
Data: defaults to ./data; override with CITYFLO_DATA_DIR
      (e.g. to point it at the debrief's fresh data slice).

Directive (a): trips.csv carries no rider phone numbers or complaint text, and no
tool here emits any rider-level field — outputs are trip ids, routes and minutes.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from mcp.server.fastmcp import FastMCP

from cityflo_otp import lateness as L

mcp = FastMCP("cityflo-otp")


def _jsonable(obj):
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.strftime("%Y-%m-%d %H:%M")
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, float):
        return round(obj, 2)
    return obj


@mcp.tool()
def data_quality_report(data_dir: str | None = None) -> dict:
    """Rows excluded or repaired before scoring: unparseable arrivals, negative
    elapsed time, tz_offset corrections, and how many rows REC-114 re-benchmarks."""
    return _jsonable(L.data_quality(L.load_trips(data_dir)))


@mcp.tool()
def rank_routes(top_n: int = 10, data_dir: str | None = None) -> list[dict]:
    """Routes ranked worst-first by median lateness (tie-break p90, then mean).
    REC-114 routes are scored on trips on/after their effective date only."""
    return _jsonable(L.ranking(L.load_trips(data_dir), data_dir)[:top_n])


@mcp.tool()
def route_verdicts(data_dir: str | None = None) -> list[dict]:
    """One verdict per route (LATE worst-three / RUNNER-UP / CLEARED / NOT FLAGGED,
    plus any SEPARATE INCIDENT day), with the stats behind it."""
    return _jsonable(L.verdicts(L.load_trips(data_dir), data_dir))


@mcp.tool()
def incident_flags(trip_threshold_min: float = L.INCIDENT_TRIP_MIN,
                   cluster_min: int = L.INCIDENT_CLUSTER_MIN,
                   data_dir: str | None = None) -> list[dict]:
    """Route-days with >= cluster_min trips at lateness >= trip_threshold_min.
    Defaults are the committed incident rule (3 trips at >= 30 min); lower the
    threshold to look for moderate same-day clusters."""
    return _jsonable(L.incidents(L.load_trips(data_dir), trip_threshold_min, cluster_min))


@mcp.tool()
def route_detail(route: str, data_dir: str | None = None) -> dict:
    """Everything behind one route's verdict: scored stats, daily medians, and —
    for REC-114 routes — before/after the effective date against BOTH the revised
    and the export timetable, so the effect of the benchmark swap is visible."""
    trips = L.load_trips(data_dir)
    clean = [t for t in L.clean(trips) if t["route"] == route]
    if not clean:
        return {"error": f"no clean trips for route {route!r}"}
    verdict = next(v for v in L.verdicts(trips, data_dir) if v["route"] == route)
    out = {
        "verdict": verdict,
        "full_week": L.summarize([t["lateness_min"] for t in clean]),
        "daily_medians": L.daily_medians(clean, route),
        "excluded_rows": [{"trip_id": t["trip_id"], "status": t["status"]}
                          for t in trips if t["route"] == route and t["status"] != "ok"],
    }
    eff = L.rec114_effective_dates(data_dir).get(route)
    if eff:
        def vs_export(t):
            sched = t["scheduled_departure"] + timedelta(minutes=t["scheduled_runtime_min"])
            return (t["corrected_arrival"] - sched).total_seconds() / 60.0
        pre = [t for t in clean if t["service_date"] < eff]
        post = [t for t in clean if t["service_date"] >= eff]
        out["rec114"] = {
            "effective_date": eff,
            "pre_effective_vs_export_timetable": L.summarize([t["lateness_min"] for t in pre]),
            "post_effective_vs_revised_timetable": L.summarize([t["lateness_min"] for t in post]),
            "post_effective_vs_export_timetable": L.summarize([vs_export(t) for t in post]),
        }
    return _jsonable(out)


@mcp.tool()
def trip_lookup(trip_id: str, data_dir: str | None = None) -> dict:
    """One trip as scored: raw and corrected arrival, runtime used, lateness, status."""
    for t in L.load_trips(data_dir):
        if t["trip_id"] == trip_id:
            return _jsonable(t)
    return {"error": f"trip {trip_id!r} not found"}


def main():
    mcp.run()


if __name__ == "__main__":
    main()
