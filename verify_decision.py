"""Re-derive every number DECISION.md cites from the raw CSVs, then drive the MCP
server over stdio. Exits non-zero on any mismatch.

    python verify_decision.py
"""
import asyncio
import copy
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

from cityflo_otp import lateness as L

HERE = Path(__file__).resolve().parent
failures = []


def check(name, got, want):
    ok = got == want
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got {got!r}" + ("" if ok else f", want {want!r}"))
    if not ok:
        failures.append(name)


def vs_export(t):
    return (t["corrected_arrival"] - (t["scheduled_departure"] + timedelta(minutes=t["scheduled_runtime_min"]))).total_seconds() / 60


def top(trips, n=5):
    return [r["route"] for r in L.ranking(trips)[:n]]


T = L.load_trips()
C = L.clean(T)
S = L.scored_trips(T)
dq = L.data_quality(T)
V = {v["route"]: v for v in L.verdicts(T)}

# --- base rule / data quality
check("rows total", dq["rows_total"], 5292)
check("rows scored", dq["rows_scored_clean"], 5250)
check("unparseable rows", dq["unparseable_arrival"]["count"], 24)
check("unparseable pattern", dq["unparseable_arrival"]["raw_values"], ["08:60"])
check("unparseable routes", len({t["route"] for t in T if t["status"] == "unparseable_arrival"}), 19)
check("negative-elapsed rows", dq["negative_elapsed_excluded"]["count"], 18)
neg = [t for t in T if t["status"] == "negative_elapsed"]
check("negative-elapsed all -5 min", {(t["corrected_arrival"] - t["scheduled_departure"]).total_seconds() / 60 for t in neg}, {-5.0})
check("negative-elapsed routes", len({t["route"] for t in neg}), 15)
tz = dq["tz_corrected"]
check("tz row", [(x["trip_id"], x["corrected_arrival"], x["lateness_min"]) for x in tz], [("T1-02864", "2026-08-03 07:02", -2.0)])
check("REC-114 rows", dq["rec114_rows_using_revised_runtime"], 189)
check("REC-114 effective dates", {k: v.isoformat() for k, v in L.rec114_effective_dates().items()}, {"R-14": "2026-08-05", "R-27": "2026-08-05"})
check("vehicle_series 1:1 with route", all(t["vehicle_series"] == t["route"][2:] for t in T), True)
check("REC-114 only applied on/after effective date",
      all(t["service_date"].isoformat() >= "2026-08-05" and t["route"] in ("R-14", "R-27") for t in T if t["uses_rec114"]), True)
check("post-fix scoring drops all pre-date R-14/R-27 trips",
      [t for t in S if t["route"] in ("R-14", "R-27") and t["service_date"].isoformat() < "2026-08-05"], [])

# --- verdict
def stat(r, *keys):
    return tuple(round(V[r][k], 2) for k in keys)

check("worst three", top(T, 3), ["R-27", "R-33", "R-26"])
check("R-27 median/p90/mean/n", stat("R-27", "median", "p90", "mean", "n"), (6.0, 14.0, 4.84, 103))
check("R-33 median/p90/mean/n", stat("R-33", "median", "p90", "mean", "n"), (5.0, 10.0, 5.36, 104))
check("R-26 median/p90/mean/n", stat("R-26", "median", "p90", "mean", "n"), (4.0, 9.0, 4.51, 103))
check("R-37 median/p90/mean", stat("R-37", "median", "p90", "mean"), (4.0, 9.0, 4.13))
check("R-14 post-fix median/mean/n", stat("R-14", "median", "mean", "n"), (0.0, 0.16, 85))
check("R-14 verdict", V["R-14"]["verdict"], "CLEARED - on time since REC-114 revision")
check("R-35 rank/median", (V["R-35"]["rank"], V["R-35"]["median"]), (13, 2.0))
check("runners-up", [r for r, v in V.items() if v["verdict"].startswith("RUNNER-UP")], ["R-37", "R-31"])
check("Mon-Fri worst three", top([t for t in T if t["service_date"].weekday() < 5], 3), ["R-27", "R-33", "R-26"])

# --- Call 1
nm = {}
for t in T:
    if t["status"] != "unparseable_arrival":
        nm.setdefault(t["route"], []).append(t["lateness_min"])
nm_rank = sorted(nm, key=lambda r: -sum(nm[r]) / len(nm[r]))
check("naive mean #1", (nm_rank[0], round(sum(nm["R-35"]) / len(nm["R-35"]), 2)), ("R-35", 7.58))
r35nw = L.summarize([t["lateness_min"] for t in C if t["route"] == "R-35" and t["service_date"].isoformat() != "2026-08-05"])
check("R-35 excl Wed median/mean", (r35nw["median"], r35nw["mean"]), (1.0, 0.78))

# --- Calls 2 & 3: REC-114 yardstick
for route, pre_want, post_exp_want, post_rev_want in (("R-27", (40, 2.0), 2.0, 6.0), ("R-14", (33, 8.0), 8.0, 0.0)):
    pre = [t for t in C if t["route"] == route and t["service_date"].isoformat() < "2026-08-05"]
    post = [t for t in C if t["route"] == route and t["service_date"].isoformat() >= "2026-08-05"]
    p = L.summarize([t["lateness_min"] for t in pre])
    check(f"{route} pre-fix n/median", (p["n"], p["median"]), pre_want)
    check(f"{route} post-fix median vs export", L.summarize([vs_export(t) for t in post])["median"], post_exp_want)
    check(f"{route} post-fix median vs revised", L.summarize([t["lateness_min"] for t in post])["median"], post_rev_want)
r27 = [t for t in S if t["route"] == "R-27"]
check("R-27 trips >=5 / >=10 (revised)", (sum(t["lateness_min"] >= 5 for t in r27), sum(t["lateness_min"] >= 10 for t in r27)), (57, 34))
check("R-27 trips >=5 (export)", sum(vs_export(t) >= 5 for t in r27), 29)
check("R-27 daily medians Thu-Sun", [L.daily_medians(C, "R-27")[d] for d in ("2026-08-06", "2026-08-07", "2026-08-08", "2026-08-09")], [7.0, 11.0, 8.0, 4.0])
r14 = [t for t in S if t["route"] == "R-14"]
check("R-14 trips >=5 / >=10 (export)", (sum(vs_export(t) >= 5 for t in r14), sum(vs_export(t) >= 10 for t in r14)), (68, 31))
check("R-14 daily medians Wed-Sun", [L.daily_medians(C, "R-14")[d] for d in ("2026-08-05", "2026-08-06", "2026-08-07", "2026-08-08", "2026-08-09")], [-4.0, -2.0, 4.0, -1.0, 3.0])
blended = {}
for t in C:
    blended.setdefault(t["route"], []).append(t["lateness_min"])
bl = sorted(blended, key=lambda r: (-L.summarize(blended[r])["median"], -L.summarize(blended[r])["p90"], -L.summarize(blended[r])["mean"]))
check("R-14 blended-week median/rank", (L.summarize(blended["R-14"])["median"], bl.index("R-14") + 1), (4.0, 3))
T_no = copy.deepcopy(T)
for t in T_no:
    if t["uses_rec114"]:
        t["lateness_min"] = vs_export(t)
nb = {}
for t in L.clean(T_no):
    nb.setdefault(t["route"], []).append(t["lateness_min"])
no_rank = sorted(nb, key=lambda r: (-L.summarize(nb[r])["median"], -L.summarize(nb[r])["p90"], -L.summarize(nb[r])["mean"]))
check("without REC-114: #1 and R-27 position", (no_rank[0], L.summarize(nb["R-14"])["median"], no_rank.index("R-27") + 1), ("R-14", 8.0, 14))

# --- Call 4: R-26 vs R-37
check("R-26 excluded negative row", [(t["trip_id"], t["lateness_min"]) for t in neg if t["route"] == "R-26"], [("T1-03377", -55.0)])
check("R-37 has no excluded rows", [t["trip_id"] for t in T if t["route"] == "R-37" and t["status"] != "ok"], [])
T_keep = copy.deepcopy(T)
for t in T_keep:
    if t["status"] == "negative_elapsed":
        t["status"] = "ok"
check("keep negatives: R-26 mean", round(next(r for r in L.ranking(T_keep) if r["route"] == "R-26")["mean"], 2), 3.94)
check("keep negatives: top five", top(T_keep), ["R-27", "R-33", "R-37", "R-26", "R-31"])
T_clamp = copy.deepcopy(T)
for t in T_clamp:
    if t["status"] == "negative_elapsed":
        t["status"], t["lateness_min"] = "ok", 0.0
check("clamp negatives to 0: top five", top(T_clamp), ["R-27", "R-33", "R-26", "R-37", "R-31"])
T_rep = copy.deepcopy(T)
for t in T_rep:
    if t["status"] == "unparseable_arrival":
        a = datetime.strptime(t["actual_arrival_raw"][:10] + " 09:00", "%Y-%m-%d %H:%M")
        t["corrected_arrival"] = a
        t["lateness_min"] = (a - (t["scheduled_departure"] + timedelta(minutes=t["runtime_used"]))).total_seconds() / 60
        t["status"] = "ok" if a >= t["scheduled_departure"] else "negative_elapsed"
base_med = {r["route"]: r["median"] for r in L.ranking(T)}
check("repair 08:60: medians changed", [r["route"] for r in L.ranking(T_rep) if r["median"] != base_med[r["route"]]], [])
for r, want in (("R-26", (10, 51)), ("R-37", (7, 50))):
    v = [t["lateness_min"] for t in S if t["route"] == r]
    check(f"{r} trips >=10 / >=5", (sum(x >= 10 for x in v), sum(x >= 5 for x in v)), want)

# --- Call 5: incident
inc = L.incidents(T)
check("incident route-days", [(i["route"], i["date"], i["qualifying_trips"], i["trips_that_day"]) for i in inc], [("R-35", "2026-08-05", 19, 19)])
d = inc[0]["day_summary"]
check("R-35 Wed min/max/median", (d["min"], d["max"], d["median"]), (36.0, 61.0, 52.0))
w = sorted([t for t in C if t["route"] == "R-35" and t["service_date"].isoformat() == "2026-08-05"], key=lambda t: t["scheduled_departure"])
check("R-35 Wed departures", (w[0]["scheduled_departure"].strftime("%H:%M"), w[-1]["scheduled_departure"].strftime("%H:%M")), ("06:35", "20:21"))
check("R-35 Wed AM/PM trips", (sum(t["scheduled_departure"].hour < 12 for t in w), sum(t["scheduled_departure"].hour >= 12 for t in w)), (8, 11))
check("R-35 Wed trips >=45 / trip-minutes", (sum(t["lateness_min"] >= 45 for t in w), sum(t["lateness_min"] for t in w)), (16, 975.0))
outside = max(t["lateness_min"] for t in C if not (t["route"] == "R-35" and t["service_date"].isoformat() == "2026-08-05"))
check("max lateness outside incident", outside, 25.0)
check("incident at 20/25 min thresholds", [[(i["route"], i["date"]) for i in L.incidents(T, th)] for th in (20, 25)], [[("R-35", "2026-08-05")]] * 2)
check("R-35 other-day medians", [m for dd, m in L.daily_medians(C, "R-35").items() if dd != "2026-08-05"], [0.0, 1.0, 0.5, 2.0, 1.0, 0.0])
check("moderate clusters (>=3 trips >=15 min)", [(i["route"], i["date"], i["trip_ids"]) for i in L.incidents(T, 15)], [
    ("R-14", "2026-08-03", ["T1-01678", "T1-01668", "T1-01676"]),
    ("R-27", "2026-08-07", ["T1-03477", "T1-03487", "T1-03493", "T1-03474"]),
    ("R-35", "2026-08-05", inc[0]["trip_ids"])])

# --- ops log cross-check
def mean(xs):
    return round(sum(xs) / len(xs), 2)

def window(day, pred):
    return mean([t["lateness_min"] for t in C if t["route"] != "R-35" and t["service_date"].isoformat() == day and pred(t["scheduled_departure"].hour)])

check("Wed AM mean excl R-35", window("2026-08-05", lambda h: h < 12), 1.46)
check("Mon/Tue/Thu/Fri AM range", (min(window(x, lambda h: h < 12) for x in ("2026-08-03", "2026-08-04", "2026-08-06", "2026-08-07")),
                                   max(window(x, lambda h: h < 12) for x in ("2026-08-03", "2026-08-04", "2026-08-06", "2026-08-07"))), (1.5, 2.15))
check("evening means Wed/Mon/Tue", tuple(window(x, lambda h: h >= 18) for x in ("2026-08-05", "2026-08-03", "2026-08-04")), (1.39, 2.15, 2.09))
day_means = {dd: mean([t["lateness_min"] for t in C if t["service_date"].isoformat() == dd]) for dd in sorted({t["service_date"].isoformat() for t in C})}
check("Friday mean", day_means["2026-08-07"], 1.68)
check("non-Wed day-mean range", (min(v for k, v in day_means.items() if k != "2026-08-05"), max(v for k, v in day_means.items() if k != "2026-08-05")), (1.57, 1.86))


# --- MCP server, driven over stdio
async def drive_server():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "cityflo_otp.server"], cwd=str(HERE))
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = sorted(t.name for t in (await s.list_tools()).tools)
            check("MCP tools", tools, ["data_quality_report", "incident_flags", "rank_routes", "route_detail", "route_verdicts", "trip_lookup"])

            async def call(name, **args):
                res = await s.call_tool(name, args)
                if res.isError:
                    return {"error": res.content[0].text}
                return res.structuredContent.get("result", res.structuredContent) if res.structuredContent else json.loads(res.content[0].text)

            check("MCP rank_routes top3", [x["route"] for x in await call("rank_routes", top_n=3)], ["R-27", "R-33", "R-26"])
            check("MCP incident_flags", [(x["route"], x["date"]) for x in await call("incident_flags")], [("R-35", "2026-08-05")])
            det = await call("route_detail", route="R-14")
            check("MCP route_detail R-14 post vs export median", det["rec114"]["post_effective_vs_export_timetable"]["median"], 8.0)
            check("MCP trip_lookup T1-02864", (await call("trip_lookup", trip_id="T1-02864"))["lateness_min"], -2.0)
            check("MCP data_quality_report rows", (await call("data_quality_report"))["rows_scored_clean"], 5250)
            check("MCP route_verdicts count", len(await call("route_verdicts")), 40)


asyncio.run(drive_server())

print(f"\n{'ALL CHECKS PASSED' if not failures else f'{len(failures)} FAILED: ' + ', '.join(failures)}")
sys.exit(1 if failures else 0)
