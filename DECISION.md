# Route lateness verdict — week of Mon 3 – Sun 9 Aug 2026

**For:** Priya (Ops Lead, Mumbai North) → Friday regional review
**Data:** `trips.csv` (5,292 rows, 40 routes), `schedule_v2.csv` (REC-114), `ops_log.txt`
**Every number below is reproduced by `python verify_decision.py`, and can be clicked into live via the `cityflo-otp` MCP server (see `README.md`).**

## The verdict

| | Route | Number that decides it | Consequence |
|---|---|---|---|
| **Worst #1** | **R-27** | median **6 min** late (post-REC-114 trips, n=103) | depot on-time incentive at risk |
| **Worst #2** | **R-33** | median **5 min** late (full week, n=104) | depot on-time incentive at risk |
| **Worst #3** | **R-26** | median **4 min** late (full week, n=103) | depot on-time incentive at risk |
| **Cleared** | **R-14** | median **0 min** late after REC-114 took effect (n=85) | not flagged |
| **Separate incident** | **R-35** | **Wed 5 Aug: all 19 trips 36–61 min late, median 52** | refund queue; not in the worst-three |

All other 35 routes: **not flagged**. R-37 and R-31 tie R-26 on median and lose only on the tie-break. They are named as runners-up because that's where the review will push (Call 4).

---

## How lateness is measured (applies to every call below)

A stranger can re-run this on next week's file and get the same answer.

1. **Lateness per trip** = `corrected_arrival − (scheduled_departure + runtime_used)`, in minutes.
2. **`runtime_used`** = `revised_runtime_min` from `schedule_v2.csv` **if** the route is listed there **and** the trip's departure date is on/after its `effective_date`; otherwise the trip's own `scheduled_runtime_min`. This is HANDOFF directive (b), REC-114. It touches 189 trips: R-14 and R-27 from **2026-08-05** onward, with revised runtimes of 53 and 45 min.
   - REC-114 says "4xx vehicle series", but `vehicle_series` is the last two digits only and maps 1:1 to route (R-NN ↔ NN, 0 exceptions). The file can't tell a 4xx vehicle from any other. So the revision is applied only where `schedule_v2.csv` gives a number. No vehicle mapping is invented.
3. **`corrected_arrival`**: when `tz_offset` ≠ `+05:30`, shift the arrival onto `+05:30`. This is one row, **T1-02864** (R-23, `+00:00`): raw 01:32 → 07:02, lateness −2 min (on time). Taken raw, it would read as arriving 4.7 h before it left.
4. **Excluded rows (42 of 5,292; 5,250 scored):**
   - **24 unparseable arrivals.** All have the literal `08:60` time, spread across 19 routes. The true time can't be recovered.
   - **18 negative-elapsed rows.** Each shows arrival exactly 5 min *before* scheduled departure, across 15 routes. That reads as lateness of −40 to −60 min, which is physically impossible for a trip.
5. **Route score** = **median** trip lateness. Ties go to **p90**, then **mean**, all descending.
6. **Scoring window** = all 7 days, except that **REC-114 routes are scored only on trips on/after the effective date**. The score should describe performance under the timetable now in force.
7. **Incident** = a route-day with **≥ 3 trips at lateness ≥ 30 min**. It is reported separately and never folded into the ranking.

Scope check: the review is "Friday", but the export runs Mon–Sun. Scoring **Mon–Fri only** gives the same worst-three (R-27 7, R-33 5, R-26 4) and R-14 still at 0. The weekend doesn't change any verdict.

---

## Call 1 — Rank by median, not mean

- **Rule:** route score = median trip lateness; tie-break p90 → mean.
- **The case it breaks on — R-35.** The naive mean ranks R-35 **#1** (7.58 min). That is entirely Wednesday: without 5 Aug, R-35's median is 1 min and its mean 0.78. The median ranks R-35 **#13** (median 2). Its worst day of the year then never shows up in the ranking at all. I keep the median anyway: one bad day shouldn't cost a depot head the week's incentive. That day is caught by Call 5 instead.
- **Cost and who pays:** if the median were wrong and R-35 *should* be flagged, the R-35 depot head escapes a penalty. But every one of those 19 trips still goes to the refund track (Call 5), so riders don't pay for it.
- **What would change my mind:** R-35, or any route, showing an incident-grade day in **two separate weeks**. Then it's a pattern, not a one-off, and it moves into the ranking.

## Call 2 — R-27 is #1 (median 6, scored on post-REC-114 trips only)

- **Rule:** REC-114 routes are scored on trips on/after `effective_date` (2026-08-05) against the revised runtime (45 min for R-27).
- **Evidence it's persistent, not a spike:** daily medians Thu 7, Fri 11, Sat 8, Sun 4. Of 103 scored trips, 57 were ≥ 5 min late and 34 were ≥ 10.
- **The case it breaks on — R-27 itself.** This is the call I'd most expect to be attacked, so here it is plainly:

  | R-27 | vs export timetable (`scheduled_runtime_min`) | vs REC-114 timetable (flat 45) |
  |---|---|---|
  | before 5 Aug (n=40) | median **2** | — |
  | from 5 Aug (n=103) | median **2** | median **6** |

  Measured on the export timetable, the buses ran **the same** before and after 5 Aug. The jump from 2 to 6 comes entirely from REC-114 swapping the export's time-of-day runtimes (35–55 min) for a flat 45. `schedule_v2.csv` itself labels R-27 "no change". Without REC-114, R-27 ranks **#14**. I keep the call because REC-114 is a signed-off directive, and it exists so the numbers match what the review already holds. It is applied exactly as written, to the date it names.
- **Cost and who pays:** the R-27 depot head loses the on-time incentive. If REC-114's flat 45 isn't the timetable R-27 is fairly held to, that loss is wrong. It rests on the benchmark, not on any change in how the buses ran. Against the export timetable, R-27 had only 29 trips ≥ 5 min late (vs 57).
- **What would change my mind:** confirmation that R-27's vehicles are **not** on the 4xx series, or that REC-114's 45 min isn't the yardstick ops holds R-27 to. Then R-27 drops to #14 and **R-14 becomes #1 at median 8**.

## Call 3 — R-14 is cleared (median 0 post-REC-114)

- **Rule:** same as Call 2. R-14 is scored from 2026-08-05 against the revised 53 min. A REC-114 route whose post-effective median is ≤ 0 is **cleared**.
- **Evidence:** 85 trips; daily medians Wed −4, Thu −2, Fri 4, Sat −1, Sun 3. Blending in the 33 pre-revision trips (median 8) would put R-14 at a full-week median of 4. That would be **#3 on the blended table**, describing a timetable no longer in force.
- **The case it breaks on — R-14 itself, mirror image of R-27.** Against the export timetable, R-14 ran a median **8 min** late before 5 Aug *and* **8 min** late after (68 of 85 post-revision trips ≥ 5 min late, 31 ≥ 10). The buses did not get faster. R-14 is "on time" because REC-114 gives every trip 53 min where the export gave 35–55. **The earlier working notes called this "the schedule fix worked". That is not what the data shows, and that claim is withdrawn.** I keep the clearance because the directive defines R-14's yardstick from 5 Aug, and against that yardstick R-14 is on time.
- **Cost and who pays:** the R-14 depot head keeps the incentive. The exposure is on the rider side. If riders see the export timetable (the data doesn't say which one the app shows), those 68 trips are the R-14 complaints and refund requests this verdict doesn't anticipate.
- **What would change my mind:** evidence that riders are sold the export timetable rather than the REC-114 one. Then R-14 is a rider-facing late route at median 8, and it goes to #1.

## Call 4 — R-26 takes #3 over R-37 (the borderline call; the one I'm least sure of)

- **Rule:** median, then p90, then mean.
- **The case it breaks on — trip T1-03377.** R-26 and R-37 tie on median (4) **and** p90 (9). Only the mean separates them: **4.51 vs 4.13**. R-26's mean depends on excluding one negative-elapsed row, **T1-03377** (lateness −55 min). Keep that row and R-26's mean falls to 3.94, so **R-37 takes #3**. That is the brief's warning — one bad row swinging a mean — showing up in the tertiary tie-break. I keep the rule because the excluded row is a device artifact under a rule applied to all 18 such rows, not just this one. The comparison also holds up on measures that row can't touch: R-26 had **10 trips ≥ 10 min late vs R-37's 7**, and 51 vs 50 trips ≥ 5 min.
- **Other exclusion treatments, re-run under the final rule:**
  - Repairing the 24 `08:60` rows to 09:00 changes no route median.
  - Clamping the 18 negative rows to lateness 0 changes no top-five position.
  - Keeping the 18 rows as-is changes only the R-26/R-37 order above.
- **Cost and who pays:** one depot head loses the incentive and the other keeps it, on a 0.38-min mean difference. If I'm wrong, R-26's depot head pays for R-37's lateness.
- **What would change my mind:** evidence that T1-03377 is a real reading and not an artifact. Or next week's data with R-37 ahead on trips ≥ 10 min.

## Call 5 — R-35 is a separate incident, not a worst-three route

- **Rule:** a route-day with ≥ 3 trips at lateness ≥ 30 min is an incident. It is reported on its own and not ranked.
- **Result:** fires exactly once. **R-35, Wed 2026-08-05: all 19 trips** that day scored, departures 06:35–20:21. Lateness was **36–61 min, median 52**, with 16 trips ≥ 45 min and 975 trip-minutes late in total. No other trip in the week reaches 30. The next highest anywhere is 25 min, and lowering the threshold to 20 or 25 still flags only this day. R-35's other six daily medians are 0, 1, 0.5, 2, 1, 0.
- **Why 30 min:** it sits in a clean gap in this week's data (25 → 36). The ≥ 3-trip requirement means one corrupt GPS row can't create an incident.
- **The case it breaks on — moderate same-day clusters:**
  - **R-27 on Fri 7 Aug:** T1-03477 22, T1-03487 22, T1-03493 19, T1-03474 15 min.
  - **R-14 on Mon 3 Aug:** T1-01678 17, T1-01676 15, T1-01668 16 min.

  Neither fires the rule. R-27's day is still counted in its #1 ranking (day median 11). **R-14's day is invisible to both tracks.** It falls before REC-114's effective date, so it's excluded from scoring, and it's below the incident bar. I keep the 30-min rule because lowering it to 15 would turn routine bad days into "incidents" and dilute the one event that matters. I accept that a moderate cluster on an unflagged route goes unreported this week.
- **Cost and who pays:**
  - **Riders:** every rider on R-35's 19 Wednesday trips is a refund-queue candidate. The data has no ridership or fare, so this can't be sized in riders or rupees.
  - **R-35 depot head:** keeps the on-time incentive. The cause isn't in the data (see ops log below), so nothing shows the depot was at fault.
- **What would change my mind:** a cause attributable to R-35's depot (vehicle, crew, dispatch) moves the incident onto the depot's record. A second incident day on R-35 moves it into the ranking (Call 1). A moderate cluster recurring next week on a route outside the top three adds a "watch" tier (≥ 3 trips ≥ 15 min).

---

## The ops log doesn't match the GPS data — stated, not explained

| `ops_log.txt` says | Trip data shows |
|---|---|
| Wed 06:40 "SV Road waterlogged, western corridor diverted ~35min all AM" | **One** route, R-35, is late, and **all day** (8 AM + 11 PM trips, 36–61 min). Other routes' Wed AM (before 12:00) mean is **1.46 min**, inside the 1.50–2.15 range of Mon/Tue/Thu/Fri mornings. |
| Wed 18:20 "crowd surge, festival, everything slow city-wide" | Wed evening (18:00+, R-35 excluded) mean **1.39 min**, *lower* than Mon (2.15) and Tue (2.09). No city-wide slowdown is visible. |
| Fri 07:30 "all normal, good day" | Consistent with no elevated route-day on Friday; fleet mean 1.68, within the 1.57–1.86 range of every non-Wednesday day. |
| Mon yard swap, Tue no-show, Thu AC swap | No route-level signature found; nothing to confirm or rule out. |

**What the record does not claim.** It doesn't say *why* R-35 was late. The data has no geography, so it can't say whether R-35 runs on SV Road or the western corridor. The log doesn't join to trips on any key.

**What it can say.** HANDOFF describes the log as "**last week's** ops log", while `trips.csv` is this week's. The log names weekdays, not dates. So its "Wed" may not be 5 Aug. That could explain the mismatch, or the two could both be true. The data can't tell which. The R-35 verdict rests on the GPS rows alone.

## What the costs are — and are not — sized from

| Sized from the data | Not in the data, so not claimed |
|---|---|
| trips and trip-minutes late per route; R-35's 19 trips / 975 trip-minutes | rupee value of any depot incentive, or the incentive formula |
| R-14's 68 export-timetable-late trips (Call 3) | rider counts per trip, refund amounts, refund-queue volume |
| R-27's 57 vs 29 trips ≥ 5 min under the two yardsticks (Call 2) | which timetable the rider app displays |

Directive (a): no rider phone numbers or complaint text appear in the data, the tool output, or this record. Everything is referenced by trip id and route.

## Full verdict table (generated by `route_verdicts`)

Median / p90 / mean in minutes; n = scored trips; "from" = scoring window.

| Rank | Route | Median | p90 | Mean | n | From | Verdict |
|---|---|---|---|---|---|---|---|
| 1 | R-27 | 6 | 14 | 4.84 | 103 | 2026-08-05 | LATE - worst-three #1 |
| 2 | R-33 | 5 | 10 | 5.36 | 104 | full week | LATE - worst-three #2 |
| 3 | R-26 | 4 | 9 | 4.51 | 103 | full week | LATE - worst-three #3 |
| 4 | R-37 | 4 | 9 | 4.13 | 105 | full week | RUNNER-UP - same median as #3, lost on tie-break |
| 5 | R-31 | 4 | 8 | 3.59 | 112 | full week | RUNNER-UP - same median as #3, lost on tie-break |
| 6 | R-17 | 3 | 8 | 2.98 | 147 | full week | NOT FLAGGED |
| 7 | R-15 | 3 | 8 | 2.67 | 119 | full week | NOT FLAGGED |
| 8 | R-34 | 3 | 8 | 2.51 | 124 | full week | NOT FLAGGED |
| 9 | R-07 | 3 | 7.4 | 2.73 | 147 | full week | NOT FLAGGED |
| 10 | R-40 | 3 | 7 | 2.61 | 152 | full week | NOT FLAGGED |
| 11 | R-08 | 3 | 7 | 2.36 | 126 | full week | NOT FLAGGED |
| 12 | R-19 | 3 | 7 | 2.33 | 125 | full week | NOT FLAGGED |
| 13 | R-35 | 2 | 49.8 | 8.05 | 132 | full week | NOT FLAGGED; SEPARATE INCIDENT 2026-08-05 |
| 14 | R-09 | 2 | 7.5 | 2.31 | 146 | full week | NOT FLAGGED |
| 15 | R-11 | 2 | 7.4 | 2.26 | 137 | full week | NOT FLAGGED |
| 16 | R-05 | 2 | 7 | 2.34 | 105 | full week | NOT FLAGGED |
| 17 | R-18 | 2 | 7 | 2.03 | 154 | full week | NOT FLAGGED |
| 18 | R-21 | 2 | 7 | 1.82 | 124 | full week | NOT FLAGGED |
| 19 | R-03 | 2 | 7 | 1.7 | 103 | full week | NOT FLAGGED |
| 20 | R-20 | 2 | 6.6 | 1.97 | 145 | full week | NOT FLAGGED |
| 21 | R-22 | 2 | 6 | 1.82 | 112 | full week | NOT FLAGGED |
| 22 | R-39 | 2 | 6 | 1.81 | 154 | full week | NOT FLAGGED |
| 23 | R-12 | 2 | 6 | 1.79 | 112 | full week | NOT FLAGGED |
| 24 | R-02 | 2 | 6 | 1.34 | 105 | full week | NOT FLAGGED |
| 25 | R-38 | 1 | 7 | 1.49 | 146 | full week | NOT FLAGGED |
| 26 | R-25 | 1 | 7 | 1.45 | 139 | full week | NOT FLAGGED |
| 27 | R-32 | 1 | 7 | 1.17 | 133 | full week | NOT FLAGGED |
| 28 | R-10 | 1 | 6.5 | 1.07 | 126 | full week | NOT FLAGGED |
| 29 | R-24 | 1 | 6 | 0.84 | 146 | full week | NOT FLAGGED |
| 30 | R-01 | 1 | 5 | 0.82 | 153 | full week | NOT FLAGGED |
| 31 | R-28 | 1 | 5 | 0.62 | 151 | full week | NOT FLAGGED |
| 32 | R-36 | 1 | 5 | 0.22 | 132 | full week | NOT FLAGGED |
| 33 | R-14 | 0 | 12 | 0.16 | 85 | 2026-08-05 | CLEARED - on time since REC-114 revision |
| 34 | R-04 | 0 | 5 | 0.17 | 144 | full week | NOT FLAGGED |
| 35 | R-23 | 0 | 5 | 0.11 | 132 | full week | NOT FLAGGED |
| 36 | R-16 | 0 | 4 | -0.19 | 146 | full week | NOT FLAGGED |
| 37 | R-30 | -1 | 5 | -0.38 | 147 | full week | NOT FLAGGED |
| 38 | R-13 | -1 | 4.8 | -0.93 | 133 | full week | NOT FLAGGED |
| 39 | R-29 | -1 | 4 | -0.93 | 151 | full week | NOT FLAGGED |
| 40 | R-06 | -2 | 3.4 | -1.45 | 117 | full week | NOT FLAGGED |
