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

## ops_log.txt cross-check — conclusion withdrawn (verification pass, 2026-10-13)
HANDOFF.md calls `ops_log.txt` **"last week's ops log"**, while `trips.csv` is **"this week's GPS export"**. `ops_log.txt` uses weekday labels only, never dates. So the log's "Wed" may or may not be 2026-08-05, and these files can't tell which.

The mismatch itself is real and stays on record. The log describes a city-wide, AM-only slowdown. The GPS shows one route, R-35, late all day, and other routes' Wed AM mean of 1.46 min (corrected from the 2.80 originally reported, which included R-35). What is withdrawn is the earlier framing that this is a "direct conflict" needing a call on weather vs. route failure. It could be a contradiction, or two different weeks. DECISION.md shows the comparison with that caveat. The R-35 incident rests on GPS evidence alone: 19/19 trips on 2026-08-05 ran 36–61 min late (departures 06:35–20:21), day-median 52, every other day 0–2. No cause is claimed.

Numeric corrections to this file are listed under **Errata** at the end.

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
- ops_log cross-check: R-35's Wednesday scheduled departures run 06:35–**20:21**. The last trip, T1-04513, departed 20:21 and arrived 22:00. "21:51" matches no R-35 Wednesday row, and where it came from isn't known. The "2.80 min" Wed-AM figure included R-35; other routes' Wed AM mean is 1.46.
- "What the data CANNOT prove" below still says "19 negative-elapsed rows". The correct count is 18.
- "Friday's mean is the lowest of the week" holds only for the pre-REC-114 inspection computation. Under the final rule, Friday's mean is 1.68, mid-range among non-Wednesday days (1.57–1.86). It is still consistent with "all normal".
- HANDOFF calls `ops_log.txt` "**last week's** ops log", and the log names weekdays, not dates. Its "Wed" is not necessarily 2026-08-05.
