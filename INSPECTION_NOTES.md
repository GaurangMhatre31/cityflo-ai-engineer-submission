# Inspection notes — on-time performance domain

Factual record only. No verdict, no worst-three ranking, no DECISION.md yet (per instruction).

## Bundle source
Downloaded from https://careers.cityflo.com/takehomes/ai-engineer/ to
`D:\Profiles\gaurang.mhatre\Desktop\cluade\cityflo-ai-engineer-takehome\`:
BRIEF.md, DATA_GUIDE.md, HANDOFF.md, data/trips.csv, data/schedule_v2.csv, data/ops_log.txt.

## trips.csv — structure
- Columns: trip_id, route, vehicle_series, scheduled_departure, scheduled_runtime_min, actual_arrival, tz_offset, scheduled_lateness_min
- 5,292 rows, 40 routes (R-01..R-40), 7 calendar days (2026-08-03 Mon through 2026-08-09 Sun), exactly 756 trips/day.
- `scheduled_lateness_min` is 100% empty (as documented — intentional, not a defect).
- `route` <-> `vehicle_series` is a perfect 1:1 mapping (route R-NN always has vehicle_series "NN"); zero exceptions across 5,292 rows.

## Data-quality defects found
1. **24 rows (0.45%) have unparseable `actual_arrival`**: literal string pattern `"<same date as scheduled_departure> 08:60"` — invalid minute value (60), same sentinel pattern every time, spread across 21 different routes/vehicles/times of day. Not a single rogue device; looks like a uniform corrupted/missing-ping sentinel.
2. **1 row (T1-02864, R-23) has `tz_offset` = "+00:00"** instead of the fleet-standard "+05:30". Taken at face value this row shows actual_arrival 282 minutes *before* scheduled_departure (nonsensical). Correcting for the offset (+5:30) moves arrival to 07:02 local vs a scheduled arrival of ~07:04 — i.e. the trip was almost exactly on time once the bad offset is corrected. Strong candidate for "device misconfiguration," not real lateness.
3. **19 rows have `actual_arrival` before `scheduled_departure`** (excluding the tz row above) — all exactly -5 minutes, spread across 14 different routes. Systematic, not random: looks like a logging artifact (arrival ping registered slightly before the dispatch timestamp was finalized) rather than a real circumstance, but flagged, not resolved.
4. **No duplicate trip_id, no duplicate full rows.**
5. **`scheduled_runtime_min` is per-trip, not per-route** — every route has all five observed values (35/40/45/50/55 min) depending on time of day; there is no single "timetable runtime" per route in this file.

## REC-114 / schedule_v2.csv conflicts (important — read before building the tool)
- `schedule_v2.csv` only contains **two** rows: R-14 (revised_runtime_min=53) and R-27 (revised_runtime_min=45, note "no change"), effective_date 2026-08-05.
- HANDOFF directive (b) says "trips on the 4xx vehicle series are measured against schedule_v2.csv." But `vehicle_series` in trips.csv is documented as only "the last two digits of the vehicle class" — and since vehicle_series is 1:1 with route (01-40) across the whole fleet, there is **no column value that distinguishes a 4xx-class vehicle from any other hundred-series** in this export. Read literally, the whole fleet could be "4xx" (401-440) or none of it could be determinable — the file cannot prove which interpretation is correct. In practice REC-114 is only *actionable* for the two routes schedule_v2.csv actually lists (R-14, R-27); the other 38 routes have nothing to substitute regardless of how "4xx" is interpreted.
- `effective_date` is 2026-08-05 — the **middle** of the 7-day export (Mon-Sun). R-14 has 34 trips before that date and 85 on/after; R-27 has 42 before and 105 on/after. So even for R-14/R-27, REC-114 raises a second question the data doesn't answer on its own: does the revised runtime apply to the whole week being reviewed, or only to trips from Wed 08-05 onward?
- R-27's own scheduled_runtime_min values range 35-55 (not flat 45) both before and after 08-05, despite the note "no change" — meaning "no change" refers to the reconciliation benchmark, not to individual trip timetables, which already varied by time of day. `scheduled_runtime_min` (per-trip) and `revised_runtime_min` (flat per-route benchmark) are not obviously the same kind of quantity.

## Scope question
- trips.csv covers Mon 08-03 through **Sun 08-09** (7 days). HANDOFF/ops_log frame this as a **Friday review** of "this week," and ops_log.txt only has entries for Mon-Fri. Whether Sat/Sun trips belong in the verdict Priya is presenting Friday is an open scope question the data does not resolve.

## ops_log.txt cross-check (does not join on any key — narrative only)
- Wed 08-05 AM: log claims "waterlogged, western corridor diverted ~35min **all AM**."
  Actual data: only **route R-35** shows elevated lateness on Wed 08-05, and it is NOT limited to AM — all 19 of R-35's trips that day (6:35 through 21:51 scheduled departures) ran 36-61 min late. Every other route's Wed-AM average (2.80 min) is barely different from the week's baseline (~1.5-1.8 min). R-35 itself is normal on all six other days (means between -3.1 and +1.6 min).
  **This is a direct conflict between the ops narrative (citywide, AM-only, weather-caused) and the GPS data (single-route, all-day, isolated to R-35).** This is the single largest lateness signal in the dataset and will need a defended call on citywide-weather vs. route-isolated-failure.
- Fri 08-07 "all normal, good day" is consistent with the data: Friday's mean lateness (1.50 min, n=753) is the lowest of the week.
- Tue 21:40 no-show, Thu AC swap, Wed evening festival/citywide slowdown: no corroborating pattern found yet at the route level (not deeply investigated — logged as unresolved, not ruled out).

## What the data CAN support
- A per-trip elapsed time (`actual_arrival - scheduled_departure`) compared to that trip's own `scheduled_runtime_min`, for 5,267 of 5,292 rows (99.5%) with parseable timestamps and standard tz_offset.
- Detection of at least one severe, isolated, single-day/single-route event (R-35, Wed 08-05) that would dominate a naive weekly mean for that route.
- A rough week-wide lateness baseline: median +2 min, p95 +9 min, mean +1.73 min (excluding the 24 unparseable and 1 tz-bug rows).

## What the data CANNOT prove on its own
- Which vehicles are actually in the "4xx series" REC-114 refers to (column granularity destroys that distinction).
- Whether Priya's "this week" includes Saturday/Sunday.
- Causation for any single late trip (weather vs. mechanical vs. driver vs. traffic) — ops_log gives narrative color but doesn't join to trips.csv on any key, so any attributed cause is an inference, not a fact.
- Ground truth for the 24 corrupted-timestamp rows or the 19 negative-elapsed rows — their true arrival time is simply unknown, not recoverable from this file.
- A single universally "correct" definition of lateness (mean vs. median vs. peak-window vs. threshold-count) — the brief and DATA_GUIDE both say this is a choice to be made and defended, not a fact to look up.

## Errata — verification pass, 2026-10-13 (checked by `verify_decision.py`)

- Defect 1: the 24 `08:60` rows span **19** routes, not 21.
- Defect 3: **18** rows (not 19) have arrival before departure, excluding the tz row. They span **15** routes, not 14.
- ops_log cross-check: R-35's Wednesday scheduled departures run 06:35–**20:21** (not 21:51). The "2.80 min" Wed-AM figure included R-35; other routes' Wed AM mean is 1.46.
- "Friday's mean is the lowest of the week" holds only for the pre-REC-114 inspection computation. Under the final rule, Friday's mean is 1.68, mid-range among non-Wednesday days (1.57–1.86). It is still consistent with "all normal".
- HANDOFF calls `ops_log.txt` "**last week's** ops log", and the log names weekdays, not dates. Its "Wed" is not necessarily 2026-08-05.
