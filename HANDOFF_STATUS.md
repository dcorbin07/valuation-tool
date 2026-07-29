# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

**Session date:** 2026-07-29
**Branch merged to:** `main` (see "What shipped" for commits)

---

## 1. What I did this session

1. **Parked the FMP/grades path** on instruction. No FMP calls, no second key, no
   `export_grades` runs. `run_grades_backtest.bat` is left ready for WRDS/IBES or a paid key.
2. **Added Sharadar-only signals** and measured every one of them point-in-time.
3. **Fixed a data bug that had silently disabled existing factors** (details below — this is
   the most important item here).
4. **Started a live data archive** so we accumulate our own point-in-time options history.
5. **Made Valquo free and open** behind a single reversible flag.
6. **Added this file** plus a standing convention in CLAUDE.md.

---

## 2. Concrete results

### 2a. THE IMPORTANT FINDING — `assets` was missing from the column allowlist

`WRDSProvider._KEEP["fundamentals"]` is an allowlist applied when the Sharadar CSVs are
loaded. A column absent from it is silently dropped, and any factor needing it reads as
"no data" rather than raising. **`assets` was not in the list.**

Consequence: **`asset_growth` — half of the `capital_discipline` theme, which CLAUDE.md
records as "switched on" — has been empty in every backtest run to date.** The theme showed
~98% coverage only because `neg_issuance` carried it. Any past conclusion about
capital-discipline contribution was measuring one input, not two.

`shrholders` was likewise missing from the institutional allowlist.

Fixed, with a comment marking the allowlist as load-bearing. **Prior backtest numbers
involving `capital_discipline` should be treated as unreliable.**

### 2b. Per-signal predictive power (Sharadar, 400 names, 12y, 110 rebalances, 63d fwd)

Median per-date Spearman IC, and a t-stat on the IC series:

| number | median IC | IC t | coverage | verdict |
|---|---|---|---|---|
| `f_score` (Piotroski, new) | +0.0606 | **+5.66** | 97.4% | **KEEP — strongest number in the panel** |
| `inst_accum` (existing 13F) | +0.0436 | +3.41 | 66.7% | keep |
| `ret_12_1` (existing momentum) | +0.0933 | +3.09 | 92.8% | keep |
| `accruals_q` (was a dead hook, now populated) | +0.0262 | +3.08 | 73.0% | **KEEP** |
| `inst_breadth` (13F holder count, new) | +0.0235 | +2.71 | 71.6% | **KEEP** |
| `cash_op_prof` (Novy-Marx, new) | −0.0101 | +0.22 | 96.3% | rejected — no signal |
| `neg_ret_1m` (short-term reversal, new) | −0.0143 | −0.44 | 99.6% | rejected — wrong sign |
| `neg_idio_vol` (new) | −0.0251 | −0.64 | 79.2% | rejected — wrong sign |
| `neg_max_ret` (MAX effect, new) | −0.0719 | −1.52 | 100.0% | rejected — wrong sign |
| `neg_asset_growth` (existing, now actually populated) | −0.0290 | −1.60 | 97.4% | **wrong sign — see below** |
| `neg_vol` (existing low-vol) | −0.0779 | −1.22 | 99.6% | **wrong sign — see below** |

**Kept and wired:** `f_score` → quality, `accruals_q` → quality, `inst_breadth` →
institutional.
**Rejected and deliberately unwired** (code retained so re-testing is one line):
`cash_op_prof`, `neg_ret_1m`, `neg_max_ret`, `neg_idio_vol`.

**Selection-bias caveat, stated plainly:** those three were kept *because* they scored well
on this same panel. That is in-sample selection. The CPCV/PBO run is what prices it in, and
that run has not finished yet (see Blocked).

### 2c. Two EXISTING factors carry the wrong sign

Now that the data actually reaches them:

- `neg_asset_growth`: median IC −0.029 (t −1.60)
- `neg_vol`: median IC −0.078 (t −1.22)

Neither is significant, but both point the wrong way in this universe, and both are live in
the scoring today. The whole `low_risk` theme has a **negative** pooled IC (−0.048).
I have **not** changed them — that alters live scoring and is Don's call.
**Recommendation: consider dropping or inverting `neg_vol`, and re-check
`capital_discipline` now that `asset_growth` is real.**

### 2d. SF3 (per-manager 13F) — NOT in the bundle

`institutional.csv` is the aggregate: one row per ticker-quarter, no manager dimension
(columns: `calendardate, ticker, totalvalue, shrholders, shrunits, putholders, …`). Per-fund
conviction / position-vs-AUM cannot be built from what's on disk. **Skipped, nothing bought,
per instruction.** The closest available stand-in — `shrholders` breadth — was built instead
and it works (t +2.71).

### 2e. Tests

**87 passing, 0 failing** across five suites: edge 27, engine 19, intraday 10, screener 13,
SaaS 18 (+2 new open-access tests). The previously flaky
`test_fundamental_backtest_synthetic` is fixed and stable (10 consecutive clean runs).

### 2f. Free and open

`OPEN_ACCESS` (default **true**). Verified: anonymous visitors resolve to the `premium`
tier; all nine formerly-gated API routes return allow with no user; no daily valuation cap;
`billing_enabled` forced false so no Stripe checkout renders; `/app` returns 200 anonymously
with the full UI; `/pricing` shows "Valquo is free" instead of plans. `OPEN_ACCESS=false`
restores the paid product exactly — plan grid, checkout markup, 401s — verified in both
directions. Nothing deleted.

The Edge Lab (`/api/edge/*`) remains owner-only. It is a private research bench, not a
withheld product feature.

---

## 3. What's blocked, and why

1. **Full-universe CPCV / Deflated Sharpe / PBO run: INCOMPLETE.** Launched on the real
   2,827-name / 18-year panel with the new factor set (stale panel cache cleared, since the
   factor set changed). It had not finished when this session ended. **So there is no
   adopt-or-reject verdict, no PBO and no Deflated Sharpe for the new signals yet** — only
   the per-signal ICs in 2b, which are in-sample. Re-run:
   `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json`
   (or `run_backtest.bat`). Expect hours, not minutes, on the full universe.
2. **Estimate revisions (real ones): parked deliberately.** FMP's `analyst-estimates` is not
   point-in-time (fiscal-period dates, no as-of field, one row per target → no revision
   history at any tier). The FMP key is also account-wide rate-limited and did NOT reset at
   00:00 UTC as documentation implies. Waiting for WRDS/IBES or a paid key. `sentiment`
   coverage is therefore **0%** and the theme stays neutral.
3. **Options-exit backtesting on real option prices:** still not possible. The archive
   started this session (2f/4) is what unblocks it, but it needs months of accumulation.

---

## 4. Recommended next step

**In priority order:**

1. **Re-run the full backtest to completion and read the CPCV verdict.** Everything in 2b is
   in-sample until PBO and Deflated Sharpe say otherwise. `f_score` at t +5.66 is the most
   promising single result this project has produced — it deserves the strong test, not the
   weak one.
2. **Decide on `neg_vol` and `neg_asset_growth`** (2c). Two live factors point the wrong way.
   This is a scoring change, so it needs Don's sign-off.
3. **Re-examine every past `capital_discipline` conclusion** given 2a.
4. Leave FMP/grades parked until WRDS (IBES) is available.

---

## 5. Standing notes

- `data/` is gitignored and holds licensed Sharadar exports — never commit it.
- The live hot-list scan runs at 22:23 UTC (23:41 backup) and uses the FMP key.
- The archive writes to `data/archive/` (gitignored): `intraday/<date>/<HHMM>.json.gz` and
  `scans/<date>.json.gz`. Append-only, never read by the live app, failures swallowed.
