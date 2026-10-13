"""Core lateness rules for the Cityflo on-time-performance review.

Every number in DECISION.md is produced by the functions in this file. The MCP
server (server.py) and the verification script (verify_decision.py) both call
into here, so the tool Priya clicks into and the written verdict cannot drift.

Rules (see DECISION.md for the defence of each):
  lateness_min      = corrected_arrival - (scheduled_departure + runtime_used)
  corrected_arrival = actual_arrival + (+05:30 - tz_offset)   when tz_offset != +05:30
  runtime_used      = schedule_v2.revised_runtime_min  if route listed in schedule_v2.csv
                                                        and departure date >= effective_date
                      else trips.scheduled_runtime_min
  excluded rows     = actual_arrival does not parse, or corrected arrival < scheduled departure
  route score       = median lateness (tie-break p90, then mean, all descending);
                      REC-114 routes are scored on post-effective-date trips only
  incident          = route-day with >= 3 trips at lateness >= 30 min
"""
from __future__ import annotations

import csv
import os
import statistics as st
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

STANDARD_OFFSET = timedelta(hours=5, minutes=30)
INCIDENT_TRIP_MIN = 30.0
INCIDENT_CLUSTER_MIN = 3
WORST_N = 3

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def data_dir(override: str | None = None) -> Path:
    return Path(override or os.environ.get("CITYFLO_DATA_DIR") or DEFAULT_DATA_DIR)


def _parse_ts(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _parse_offset(s: str) -> timedelta:
    sign = -1 if s.startswith("-") else 1
    h, m = s.lstrip("+-").split(":")
    return sign * timedelta(hours=int(h), minutes=int(m))


def percentile(sorted_vals: list[float], p: float) -> float | None:
    """Linear-interpolation percentile (same as numpy's default)."""
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * p
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def load_schedule_v2(ddir: Path) -> dict[str, dict]:
    out = {}
    with open(ddir / "schedule_v2.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["route"]] = {
                "revised_runtime_min": float(r["revised_runtime_min"]),
                "effective_date": datetime.strptime(r["effective_date"], "%Y-%m-%d").date(),
                "note": r["note"],
            }
    return out


def load_trips(override_dir: str | None = None) -> list[dict]:
    """Every row of trips.csv, with lateness computed and a `status` of
    'ok', 'unparseable_arrival' or 'negative_elapsed'."""
    ddir = data_dir(override_dir)
    sched = load_schedule_v2(ddir)
    trips = []
    with open(ddir / "trips.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dep = _parse_ts(r["scheduled_departure"])
            arr = _parse_ts(r["actual_arrival"])
            t = {
                "trip_id": r["trip_id"],
                "route": r["route"],
                "vehicle_series": r["vehicle_series"],
                "scheduled_departure": dep,
                "service_date": dep.date() if dep else None,
                "scheduled_runtime_min": float(r["scheduled_runtime_min"]),
                "actual_arrival_raw": r["actual_arrival"],
                "tz_offset": r["tz_offset"],
                "tz_corrected": False,
                "uses_rec114": False,
                "runtime_used": float(r["scheduled_runtime_min"]),
                "lateness_min": None,
                "status": "ok",
            }
            if arr is None:
                t["status"] = "unparseable_arrival"
                trips.append(t)
                continue
            off = _parse_offset(r["tz_offset"])
            if off != STANDARD_OFFSET:
                arr = arr + (STANDARD_OFFSET - off)
                t["tz_corrected"] = True
            t["corrected_arrival"] = arr
            rev = sched.get(t["route"])
            if rev and dep.date() >= rev["effective_date"]:
                t["runtime_used"] = rev["revised_runtime_min"]
                t["uses_rec114"] = True
            t["lateness_min"] = (arr - (dep + timedelta(minutes=t["runtime_used"]))).total_seconds() / 60.0
            if arr < dep:
                t["status"] = "negative_elapsed"
            trips.append(t)
    return trips


def clean(trips: list[dict]) -> list[dict]:
    return [t for t in trips if t["status"] == "ok"]


def rec114_effective_dates(override_dir: str | None = None) -> dict[str, date]:
    return {r: v["effective_date"] for r, v in load_schedule_v2(data_dir(override_dir)).items()}


def scored_trips(trips: list[dict], override_dir: str | None = None) -> list[dict]:
    """Clean trips used for route scoring: REC-114 routes keep only trips on/after
    their effective date (current performance under the schedule in force)."""
    eff = rec114_effective_dates(override_dir)
    return [t for t in clean(trips) if t["route"] not in eff or t["service_date"] >= eff[t["route"]]]


def summarize(vals: list[float]) -> dict:
    v = sorted(vals)
    if not v:
        return {"n": 0}
    return {
        "n": len(v),
        "median": st.median(v),
        "p90": percentile(v, 0.90),
        "mean": round(st.mean(v), 2),
        "min": v[0],
        "max": v[-1],
    }


def daily_medians(trips: list[dict], route: str) -> dict[str, float]:
    by_day = defaultdict(list)
    for t in trips:
        if t["route"] == route:
            by_day[t["service_date"]].append(t["lateness_min"])
    return {d.isoformat(): st.median(v) for d, v in sorted(by_day.items())}


def incidents(trips: list[dict], trip_min: float = INCIDENT_TRIP_MIN,
              cluster_min: int = INCIDENT_CLUSTER_MIN) -> list[dict]:
    """Route-days with >= cluster_min clean trips at lateness >= trip_min."""
    hits = defaultdict(list)
    for t in clean(trips):
        if t["lateness_min"] >= trip_min:
            hits[(t["route"], t["service_date"])].append(t)
    out = []
    for (route, d), ts in sorted(hits.items()):
        if len(ts) < cluster_min:
            continue
        day_all = [t["lateness_min"] for t in clean(trips) if t["route"] == route and t["service_date"] == d]
        out.append({
            "route": route,
            "date": d.isoformat(),
            "qualifying_trips": len(ts),
            "trips_that_day": len(day_all),
            "day_summary": summarize(day_all),
            "trip_ids": [t["trip_id"] for t in sorted(ts, key=lambda t: -t["lateness_min"])],
        })
    return out


def ranking(trips: list[dict], override_dir: str | None = None) -> list[dict]:
    """All routes, worst first: median desc, then p90 desc, then mean desc."""
    by_route = defaultdict(list)
    for t in scored_trips(trips, override_dir):
        by_route[t["route"]].append(t["lateness_min"])
    rows = [{"route": r, **summarize(v)} for r, v in by_route.items()]
    rows.sort(key=lambda s: (-s["median"], -s["p90"], -s["mean"], s["route"]))
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows


def verdicts(trips: list[dict], override_dir: str | None = None) -> list[dict]:
    """One verdict per route. See DECISION.md section 1 for the rule."""
    eff = rec114_effective_dates(override_dir)
    inc = {i["route"]: i for i in incidents(trips)}
    rank = ranking(trips, override_dir)
    cutoff_median = rank[WORST_N - 1]["median"]
    out = []
    for row in rank:
        r = row["route"]
        if row["rank"] <= WORST_N:
            v = f"LATE - worst-three #{row['rank']}"
        elif row["median"] == cutoff_median:
            v = "RUNNER-UP - same median as #3, lost on tie-break"
        elif r in eff and row["median"] <= 0:
            v = "CLEARED - on time since REC-114 revision"
        else:
            v = "NOT FLAGGED"
        if r in inc:
            v += f"; SEPARATE INCIDENT {inc[r]['date']}"
        out.append({**row, "verdict": v,
                    "scored_from": eff[r].isoformat() if r in eff else "full week"})
    return out


def data_quality(trips: list[dict]) -> dict:
    unparse = [t for t in trips if t["status"] == "unparseable_arrival"]
    neg = [t for t in trips if t["status"] == "negative_elapsed"]
    tz = [t for t in trips if t["tz_corrected"]]
    return {
        "rows_total": len(trips),
        "rows_scored_clean": len(clean(trips)),
        "unparseable_arrival": {"count": len(unparse), "trip_ids": [t["trip_id"] for t in unparse],
                                "raw_values": sorted({t["actual_arrival_raw"][-5:] for t in unparse})},
        "negative_elapsed_excluded": {"count": len(neg), "trip_ids": [t["trip_id"] for t in neg],
                                      "lateness_values": sorted({round(t["lateness_min"], 1) for t in neg})},
        "tz_corrected": [{"trip_id": t["trip_id"], "route": t["route"], "tz_offset": t["tz_offset"],
                          "raw_arrival": t["actual_arrival_raw"],
                          "corrected_arrival": t["corrected_arrival"].strftime("%Y-%m-%d %H:%M"),
                          "lateness_min": t["lateness_min"]} for t in tz],
        "rec114_rows_using_revised_runtime": sum(t["uses_rec114"] for t in trips),
    }
