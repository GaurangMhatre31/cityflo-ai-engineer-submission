# Lateness rule — verification + sensitivity (working notes, NOT the final DECISION.md)

## 1. Verified scheduled-arrival calculation

`scheduled_lateness_min` is 100% empty by design (DATA_GUIDE.md: "not a stored fact"). Computed instead as:

```
scheduled_arrival = scheduled_departure + runtime_to_use
corrected_arrival  = actual_arrival + (STANDARD_OFFSET(+05:30) - tz_offset)   [only when tz_offset != +05:30]
lateness_min       = corrected_arrival - scheduled_arrival   (minutes)
```

`runtime_to_use`:
- `revised_runtime_min` from `schedule_v2.csv` **only if** `route` is explicitly listed there (R-14 or R-27) **and** `scheduled_departure.date() >= effective_date` (2026-08-05).
- Otherwise `scheduled_runtime_min` from `trips.csv` (the per-trip value — confirmed NOT a fixed per-route number; every route has all of 35/40/45/50/55 min depending on time of day).

tz correction applied to 1 row (T1-02864, R-23, `+00:00`): raw arrival 01:32 -> corrected 07:02, lateness -2.0 (on time). Verified by hand against the scheduled arrival (~07:04).

## 2. REC-114 resolution

Resolved narrowly, not broadly:
- `vehicle_series` is a perfect 1:1 map to `route` (R-NN <-> "NN", 0 exceptions across 5,292 rows) and is documented as only "the last two digits of the vehicle class" — the file cannot distinguish a 4xx-class vehicle from any other hundred-series vehicle with the same last two digits.
- `schedule_v2.csv` only lists R-14 and R-27. Revised runtime applied **only** to those two, **only** from `effective_date` onward.

## 3. Exclusions + sensitivity

Primary metric excludes 24 unparseable `"HH:60"` rows and 18 negative-elapsed rows (post tz-correction) -> 5,250 of 5,292 rows (99.2%) remain.

Sensitivity tested: repairing the 24 rows instead of excluding changes **zero** route medians. Clamping the 18 negative rows to 0 instead of excluding shifts only 2 low-traffic routes by 0.5 min, no worst-three change under any ranking. Neither exclusion-treatment choice is load-bearing.

## 4. R-35 Wednesday 08-05 — kept in full, not deleted

All 19 of R-35's trips on Wed 08-05 ran 36-61 min late (day-median 52 min, trip range 36-61). Every other day that week R-35 averages 0-2 min.

**Correction (2026-10-13 verification pass):** HANDOFF.md explicitly calls `ops_log.txt` "last week's ops log," while `trips.csv` is "this week's GPS export"; ops_log only ever uses weekday labels, never dates. So its "Wed" may or may not be 2026-08-05, and the files can't tell which. The mismatch stands as an observation. The log describes a city-wide, AM-only slowdown. The data shows R-35 alone, all day, with other routes' Wed AM mean at 1.46 min (the "2.80" above included R-35, and the last R-35 departure was 20:21, not 21:51). Calling it a "conflict" is withdrawn: it may be two different weeks. DECISION.md shows the comparison with that caveat, and the R-35 incident rests on GPS evidence alone, with no claimed cause.

## 5. Incident-flag rule — defined and tested

**Rule:** a route-day is flagged as a severe incident if it has >= 3 trips with trip-level lateness >= 30 minutes.

**Why 30 minutes is operationally meaningful:** it is close to the longest scheduled runtime band itself (55 min) — at this point a rider isn't "running a bit late," they've lost most of a second trip's worth of time. It also happens to be the exact point where this dataset shows zero ambiguity: every trip at or above 30 min belongs to one single event; the next-highest trip-level lateness anywhere else in the entire week is 25 min — a clean 5-minute gap. The >=3 same-day cluster requirement exists so a single bad GPS ping (e.g., one of the 24 corrupted-timestamp rows, if it had parsed to a large number) can't trigger an "incident" alone — real incidents affect multiple riders on multiple trips.

**Result:** exactly one route-day triggers: **R-35, 2026-08-05, 19 qualifying trips** (every single trip that route ran that day). Zero other route-days have even 1 trip over the 30-min threshold — no near-misses, no ambiguity.

**Edge case tested (item 5, real data, not hypothetical):** R-27 on 2026-08-07 has 4 trips at 15-22 min late (15, 19, 22, 22) — a genuine same-day cluster of moderate delays. None cross 30 min, so the incident rule correctly does **not** fire on it. This is not a flaw here, because R-27's elevation that day is already captured by the persistent-lateness track (its day-median that day is 11 min, already contributing to its median/p90 ranking). **The actual risk the rule carries:** if a route with a similar moderate (15-25 min), same-day cluster did NOT otherwise qualify for the persistent-lateness worst-three, that day would go completely unflagged by both tracks — the rule only catches extremes, nothing in between. **What would change this call:** a future week showing a similar moderate same-day cluster recurring on a route that never surfaces in the persistent-lateness ranking — that would justify adding a second, lower-severity tier to the incident rule (e.g., >=3 trips >=20min as a "watch" flag, distinct from the >=30min "incident" flag).

## 6. REC-114 rechecked — a consequential finding during verification (item 3, item 6)

Verifying the R-33/R-27/R-14 ordering surfaced a real problem: R-14's blended full-week median (4.0 min, rank 3) mixes two very different regimes:
- **Pre-revision** (Aug 3-4, old schedule, 33 trips): median **8.0 min**, mean 8.42 — genuinely, consistently late. This is presumably *why* REC-114 was issued for this route.
- **Post-revision** (Aug 5-9, new schedule live, 85 trips — the majority of the week): median **0.0 min**, mean 0.16 — essentially on time, roughly symmetric from -18 to +19.

Averaging these together makes R-14 look like a persistent, ongoing problem (median 4.0) when the post-fix data says it has already been resolved. **Refined rule applied:** for the two REC-114 routes only, score persistent lateness using **post-effective-date trips only** (since the metric is meant to describe current performance under the schedule currently in force) — full week still used for all 38 unaffected routes, since nothing changed for them.

Re-checked R-27 the same way for consistency: pre-revision median 2.0 (clean) -> post-revision median **6.0** (worse). R-27's problem is real, current, and got worse under the new schedule — not a stale artifact.

**Net effect: R-14 drops out of the worst-three (cleared — the schedule fix worked), and R-27 moves to #1 (its true current severity was being understated by the blended-week number).**

## 7. Verified final ranking (median -> p90 -> mean tie-break; REC-114 routes scored post-effective-date only)

| Rank | Route | Median | p90 | Mean | n | Persistence check (daily medians) |
|---|---|---|---|---|---|---|
| 1 | **R-27** | 6.00 | 14.00 | 4.84 | 103 (post-fix only) | Elevated Thu/Fri/Sat (7/11/8), not a single day |
| 2 | **R-33** | 5.00 | 10.00 | 5.36 | 104 | Elevated every day, 4-8 min, no single spike |
| 3 | **R-26** | 4.00 | 9.00 | 4.51 | 103 | Elevated every day, 3-6 min, no single spike |
| 4 | R-37 | 4.00 | 9.00 | 4.13 | 105 | (runner-up, close tie) |
| 5 | R-31 | 4.00 | 8.00 | 3.59 | 112 | (runner-up, close tie) |
| cleared | R-14 | 0.00 (post-fix) | - | 0.16 | 85 (post-fix) | Pre-fix: median 8.0 (genuinely late). Resolved by REC-114. |
| **flagged incident** | **R-35** | 2.00 (unremarkable) | 49.80 | 8.05 | 132 | 6 normal days (0-2 min) + 1 catastrophic day (52 min median, 19/19 trips 36-61min) |

Tie-break rule used throughout: median (primary) -> p90 (secondary, rewards consistency over occasional severity) -> mean (tertiary). Necessary because minute-resolution GPS data produces many whole-number median ties; this is disclosed, not hidden.

## 8. Cost quantification (item 4) — only where the evidence supports it

**Supported by data:**
- R-27, R-33, R-26 show *sustained, multi-day* elevation (verified day-by-day, no route hiding a single bad day behind its average) — flagging these three as worst-three is defensible under Priya's own framing ("if I flag a route that wasn't really late, the depot head loses his on-time incentive"): the data shows real, repeated lateness, not a one-off.
- R-35's incident is a concrete, countable rider-impact event: 19 trips, every rider on that route that day, delayed 36-61 minutes — a specific, dateable, quantifiable candidate for the refund queue, separate from the depot-incentive conversation.
- R-14 would have been a **wrongly-flagged** route under the naive blended-week median — exactly the failure mode Priya said costs her the depot head's trust. Verification caught this before it reached DECISION.md.

**NOT supported by data (not claimed):** exact rupee/dollar cost of any incentive or refund, the incentive payout formula, refund-queue volume or cost-per-minute. None of that exists in `trips.csv`, `ops_log.txt`, or `schedule_v2.csv` — stating a number here would be invented, not evidenced.

## Errata — verification pass, 2026-10-13 (checked by `verify_decision.py`; DECISION.md supersedes)

Statements above that the recomputation from raw data does not support:

- **§6 "the schedule fix worked" / "R-27 got worse under the new schedule" — withdrawn.** Against the export's own `scheduled_runtime_min`, R-14 ran median 8 min late both before *and* after 08-05, and R-27 median 2 both before and after. The 8→0 and 2→6 shifts come entirely from REC-114 swapping the benchmark to a flat 53 / 45 min, not from any change in how the buses ran. The verdict numbers (R-27 6, R-14 0) stand under the directive. The causal story does not.
- **§3 "no worst-three change under any ranking" — not true under the final (post-fix) rule.** Keeping the 18 negative-elapsed rows as-is swaps #3/#4: R-26's mean falls from 4.51 to 3.94 because of one row, T1-03377 (−55 min), and R-37 (4.13) takes #3. Repairing `08:60` and clamping negatives to 0 still change nothing.
- **§4 "every other route's Wed-AM average is 2.80 min" — that figure includes R-35.** Excluding R-35, the Wed AM (before 12:00) mean is 1.46 min.
- **§4 "6:35am–9:51pm"** — R-35's Wednesday scheduled departures run 06:35–20:21. The last arrival was 22:00.
- **§5 "next-highest trip-level lateness 25 min"** — confirmed. Note a second moderate cluster beyond R-27 08-07: **R-14 on 08-03** (T1-01678 17, T1-01668 16, T1-01676 15). It falls before REC-114's effective date, so it is invisible to both the ranking and the incident rule.
