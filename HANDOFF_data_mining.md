# HANDOFF — the ThetaData Pro harvest. Deadline 2026-09-01.

**Lane:** data miner. **Status:** RUNNING. **Zero trials — collection is not a test.**
No analysis was run and none may be quoted from this data beyond the integrity checks below.

New files, all mine: `mine_deep_chains.py`, `DEEP_HARVEST_SUMMARY.json`, this handoff.
Nothing under `valuation/edge/options_*.py` was touched. Nothing under `.github/` was touched.
**The existing freeze is untouched** — this writes to a new root, `D:\thetadata`.

---

## Day one: volumes, job, projected total

| | |
|---|---|
| **C:** (laptop) | 231 GB free of 476 GB |
| **D:** (raw root) | **436 GB free** of 466 GB |
| raw root | `D:\thetadata` (parameter `--raw-root`, this is the default) |
| **WHICH JOB THIS IS** | **EOD chains, deepened in TENOR — not tick, and not a re-pull of dates** |
| projected raw total | **31.8 GB** (Tier A 7.7 GB + Tier B 24.1 GB) |
| projected wall-clock | **~31.5 h serial** |
| headroom after | ~405 GB free on D: |

The projection is built from the existing cache's own footprint for exactly the 1,361 symbol-years
in scope (10.16 GB), scaled by the row multiple measured on three full symbol-years pulled at
depth (2.34×–3.13×). The high end is quoted so the projection cannot flatter itself.

**31.5 hours against a 15-day deadline.** There is enough headroom to finish Tiers A–D and still
consider the tick job (see *The fork left for Don*).

---

## THE FINDING THAT REDIRECTED THE QUEUE — read this before anything else

**Tier A and Tier B as written were already done, and pulling them would have spent the Pro window
re-fetching bytes that are on disk.**

The brief's premise is a measured fact — *3,869 of 3,884 full-chain days, 99.6%, are entry dates* —
but it is a fact about the **freeze**, and the freeze is not the only chain store:

* `data/options_freeze/R2_CORRECTED_2026-08-08/` is a **replay artifact**: the banked contracts'
  own histories. Entry-anchored by construction, which is exactly what it was built for.
* `data/options/<SYM>/<SYM>-<YEAR>.pkl` is the **breadth cache**, mined **one call per
  symbol-YEAR with `expiration="*"`**, so it already holds the whole chain for **every session**
  of the year.

Measured across every alert's entry..exit span, before anything was pulled:

| | |
|---|---|
| trading chain-days needed | **42,650** |
| **PRESENT in the existing EOD cache** | **42,608 — 99.90%** |
| absent | **42** (39 of them one contiguous MA gap, 2019-08-26 → 2019-09-20) |
| symbol-years with no file at all | **0** |

The raw calendar-day figure is 70.73%, and the difference is entirely weekends and holidays, which
have no chain by construction. Restricting to genuine sessions — the trading calendar harvested
from the cache itself, 2,515 sessions — gives the 99.90%.

### What is actually missing, and why it is the thing the blocked items need

| | |
|---|---|
| alert symbol-years capped at **90 DTE** | **850 of 1,361** (max observed DTE 88, **zero** rows above) |
| capped at **200 DTE** | **511 of 1,361** (max observed DTE 200, **zero** rows above) |
| holding a contract **beyond 200 DTE** | **ZERO, anywhere in the cache** |

**And that ceiling was a mining choice, not a subscription limit.** Probed on the live account
before committing to anything:

| AAPL 2024-03-04..05 | rows | max DTE | rows > 200 DTE |
|---|---|---|---|
| `max_dte=200` | 2,476 | 200 | 0 |
| `max_dte=400` | 3,680 | 382 | 1,204 |
| `max_dte=800` | 4,472 | 683 | 1,996 |
| `max_dte=1200` | 4,676 | 836 | 2,200 |

…in the same wall-clock (0.8 s → 1.6 s). 2016–2018 is served today and carries LEAPS too (AAPL
2016-03-01: 4,544 rows, 976 beyond 200 DTE).

**A roll moves OUT in tenor.** A 90-DTE ceiling makes "roll to a later expiry" unanswerable no
matter how many dates you hold, so the depth axis — not the date axis — is what unblocks O10, O18,
U6, O3 and O21. The harvest was redirected accordingly: **same tiers, same order, same alert
symbol-years, pulled at `max_dte=1200` instead of re-pulling dates.**

`max_dte` is **1200, not 800**, deliberately: 800 → 4,472 rows (max DTE 683) and 1200 → 4,676
(max 836), so the extra tenor costs ~4.6% of rows for no measurable time. There is no second
attempt after Sep 1, so the ceiling is set above anything the feed actually returns rather than at
a round number that might clip a January LEAP.

---

## The overlap comparison — brief rule 3

Pulling 0–1200 DTE re-covers the 0–90 or 0–200 band the existing cache already holds, so **every
unit carries its own control** and overlap is free rather than wasted.

**Result on the first units, and it is exact.** AAPL-2018:

| | |
|---|---|
| cached rows | 203,778 |
| new rows | 384,590 |
| **shared keys** | **203,778 — every cached key is present in the new pull** |
| bid mismatches | **0** (max abs diff 0.000) |
| ask mismatches | **0** (max abs diff 0.000) |
| volume mismatches | **0** (max abs diff 0.000) |
| agreement | **1.000000** |

**No disagreement has been seen.** Verdict counts are carried in `DEEP_HARVEST_SUMMARY.json` under
`overlap_verdicts`; **a single `DISAGREE` stops the run**, is logged in full with up to five
example rows per column, and is reported here.

Two things the comparison deliberately does **not** count as disagreement, both by construction:
the cached frame is slim-filtered (`mine_options_cache.slim_filter` drops rows with no two-sided
quote *and* no OI *and* no volume, plus quotes wider than 300%) so it legitimately holds **fewer**
keys — only the intersection is compared; and the cached frame is float32 where the raw arrives
float64, so floats are compared at 1e-3.

---

## The resume test I actually ran

Not an assumption — a real hard kill, with the invariants checked on both sides.

1. **Before:** manifest 6 lines, 4 payloads, 0 stray `.tmp`.
2. Launched the harvester on 6 units, `--workers 1`, and let it run **50 seconds** — well inside a
   unit, since a symbol-year takes 30–140 s.
3. **`taskkill /PID <pid> /T /F`** — no signal, no cleanup, whole process tree.
4. **After the kill:** manifest still 6 lines (**no torn line**), payloads still 4 (**no
   half-written file**), **0 stray `.tmp`**, process gone. The atomic write (`tmp` + `os.replace`)
   meant the in-flight unit left nothing behind at all.
5. **Restarted.** Scope line was **identical** before and after — `done {'A': 4}, to pull 6` — so
   the killed unit was correctly **not** counted as done and the four completed ones were skipped.
   The restart then completed all 6.
6. **`--verify --full-hash`: 10 of 10 records re-hashed to their recorded sha256**, zero missing,
   zero wrong-size, zero wrong-hash.

The ordering that makes this safe is deliberate: **the payload is written and `os.replace`d BEFORE
its manifest line is appended**, and the manifest line is `fsync`ed. So a kill can lose a unit's
*record* (it re-pulls, costing one unit) but can never record a unit as complete when its bytes
are absent or partial. The manifest is JSON-lines and a torn final line is skipped on load, which
re-pulls that unit rather than failing to start.

---

## Queue and per-tier completion

| tier | scope | symbol-years | status |
|---|---|---|---|
| **A** | alert symbol-years **2016–2018** (outside Standard's window — least recoverable) | **400** | RUNNING |
| **B** | alert symbol-years **2019–2025** | **961** | queued behind A |
| **C** | 2016–2018 backfill for the P1S0 optionable universe | TBD | not started |
| **D** | 60–90 DTE × delta band for the Index's 86 names | TBD | not started |

Tier A is pulled **entirely before** Tier B — the unit list is sorted by tier — so if the clock
runs out, what got done is what mattered most.

### Daily progress

| date | tier | units done / total | GB | projected finish |
|---|---|---|---|---|
| 2026-08-16 | A | harvest launched; 10 units banked in testing | 0.07 | ~31.5 h from launch |

---

## BUGS FOUND

**1. `theta_bulk` concurrency is unsafe for deep pulls — reported, not fixed (lane rule).**
At `--workers 2`, two of the first three symbol-years lost whole quarters to gRPC
`_MultiThreadedRendezvous` (AAPL-2016 lost Q1+Q4, AAPL-2017 lost Q2). Serially, all three
succeeded first try. This matches a measurement from the O14 tick lane: ThetaData **serialises the
account**, so per-call latency scales with workers while throughput stays flat, and extra workers
buy nothing but failures. `mine_options_cache.py` uses `WORKERS = 4` because Standard *permits* 4
concurrent requests — permitted is not useful. **This harvester runs `--workers 1`.** The bug is in
another lane's file and was not touched.

**2. A failed quarter is silently a short year.** `_fetch_span` returns what it has, so a
symbol-year assembled from three good quarters and one failure looks like a complete year on disk.
This harvester treats **any** failed quarter as a failed **unit** (no payload written, `status:
failed`, re-pulled next run) rather than banking a partial year. Flagged because the same shape
exists in the breadth miner.

---

## What was NOT pulled, and why

*After 2026-09-01 this section is the permanent record of what is unreachable.*

* **Tick-resolution data across holding periods.** ~190 GB, would not fit on the laptop, and fits
  D: only at the cost of everything else. The existing tick cache (`data/options_ticks/`, 4.72 GB)
  is **entry-days only** — 3,884 alert-days, 70.3 M prints. See the fork below; this is a decision
  with a deadline attached.
* **The 42 absent holding-period chain-days**, of which 39 are one contiguous MA gap
  (2019-08-26 → 2019-09-20). Being picked up incidentally: MA-2019 is a Tier B unit and the deep
  pull re-fetches the whole year, so if the gap was a mining failure it closes, and if it is a
  vendor gap it will show as a short year. Recorded either way.
* **Anything beyond ~836 DTE.** The feed itself stops there — `max_dte=1200` returns a max observed
  DTE of 836 on AAPL — so this is a source limit, not a choice.

### The fork left for Don, and it has a deadline

The depth harvest needs ~31.5 h of a 15-day window. **The remaining capacity is real and it
expires.** The one genuinely unreachable-after-Sep-1 dataset not covered above is **tick data
across holding periods** — every print on every day a position was open, rather than only on entry
days. It is what a passive-limit fill model (O10) and a spread-conditional cost model (O18) would
want, and at ~190 GB it fits D:'s 436 GB but nothing else would.

I have not started it, because it is a large irreversible commitment of the remaining window and
the depth harvest is the higher-confidence unblock. **If it is wanted, it should start once Tier B
is done and before ~Aug 26** to land inside the window.
