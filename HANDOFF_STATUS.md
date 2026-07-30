# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

**Session date:** 2026-07-29 (fourth session that day)
**Branch:** `worktree-bulk-tests` -> merged to `main`

> **Scope:** P2 (bulk.py tests) and P3 (speedup + **the full-universe run, which COMPLETED
> for the first time**) are done. P4-P7 not started.

---

## 0. THIS SESSION — the full 2,827-name run finally completed, and it deflates the 800-name result

The load phase and the scoring loop are both fixed, so the run that had never finished now
finishes. **The headline: PBO went from 13% to 53%.** The friendlier large-cap universe was
doing most of the work.

| metric | **FULL 2,710 names, 110 dates** | 800-name (prev session) | read |
|---|---|---|---|
| **PBO** (want <50%) | **53%** | 13% | **the 13% did NOT hold up** — at 53% the weight selection is likely overfit by the metric's own threshold |
| **Deflated Sharpe** (want >95%) | **73%** | 77% | broadly unchanged, still short of the bar |
| Top-decile alpha vs equal-weight | **+5.1%/yr** (sig-wtd +5.6%) | +4.1% | *better* on the full universe |
| Long-short D1-D10 | **+7.7%/yr, t 1.12**, hit 61% | +5.0%, t 0.78 | better, still not significant |
| Monotonicity | **-0.85** | -0.64 | notably better — deciles are well ordered |
| Walk-forward verdict | **KEEP DEFAULTS** (`ic-proportional` +0.051 vs +0.044 failed the haircut) | adopt `ic-ir` | reversed |
| CPCV verdict | adopt **`equal-weight`** (+0.058 vs +0.045, 100% of 15 paths) | adopt `ic-ir` | see below |
| 13F dependence | +5.1% -> **+3.9%**, t 1.12 -> 0.71 | +4.1% -> +2.2%, t 0.78 -> 0.06 | **much less dependent** |
| Regime (median IC) | large +0.039, small +0.038, mid +0.028 | large +0.081 | edge is flatter across caps than we thought |

**How to read this honestly — the raw edge and the tuning are two different things.**

The *portfolio* numbers all got BETTER on the full universe: higher top-decile alpha, higher
long-short t, much cleaner monotonicity (-0.85), and far less 13F dependence. What got worse is
the *weight selection*: PBO 53% says picking a weighting from this search is likely overfit,
and walk-forward now refuses to adopt anything at all.

**The two validators disagree, and the disagreement is informative.** Walk-forward says keep
defaults; CPCV adopts `equal-weight` — not a tuned scheme, but the least-tuned one available.
Taken together they are saying *don't tune the weights*, which is the opposite of the previous
session's "adopt ic-ir" and consistent with the project's long-standing finding that
weight-tuning is mostly noise-chasing.

**So the previous session's PBO 13% / "first genuine ADOPT verdict" should be treated as an
artifact of the 800-name large-cap subset.** The caveat flagged there turned out to be the
whole story. Deflated Sharpe ~73-77% is the stable number across both universes, and it is
still below 95%.

The weighting CPCV would adopt is essentially flat — every theme at 0.119 except sentiment
(0.048, which is empty anyway since grades are parked):
```
WEIGHTS_ESTABLISHED = {"value": 0.119, "quality": 0.119, "momentum": 0.119, "insider": 0.119,
                       "low_risk": 0.119, "capital_discipline": 0.119, "sentiment": 0.0476,
                       "size": 0.119, "institutional": 0.119}
```
That is equal-weight by another name. **NOT applied** — with PBO at 53% and walk-forward
refusing to adopt, applying anything from this search is exactly what PBO is warning against.
It also drops `institutional` from 34% (the 800-name recommendation) to 11.9%, so the two runs
disagree sharply about the one theme we know carries weight.

**Also worth noting:** the survivorship fix and PIT market cap from P1 are in these numbers, so
this is the cleanest run to date — 19,207 delisting dates masked, no fake flat post-delisting
returns, and market cap from Sharadar's own point-in-time field rather than shares x price.

### P3 speedup — the premise was wrong, and profiling paid for itself

`_price_extras`' regression was NOT the bottleneck. `pd.to_datetime` was: 18,968 calls, 10.9s
of a 31.4s build (35%), because `_yoy` and `_sf1_extras` re-derived the same as_of-365d/-730d
cutoff for *every ticker at every date*. Hoisting those to once per rebalance date gave
**31.4s -> 11.2s (2.8x) with byte-identical output** (4,512 rows before and after). No numpy
rewrite needed; vectorizing the regression would have bought far less.

Full-run load time: **75s for 2,710 usable tickers** (was ~6 minutes of loading alone before).

### P2 — bulk.py now has 8 unit tests

Including `test_sf3_keyword_binding_regression`, which calls `prepare_sf3` by keyword and with
`rebuild` third-positional and asserts both agree — the exact check that would have caught the
zero-rows bug. SF3 conviction arithmetic is verified by hand (a small fund's whole-book
position must outweigh a giant's token stake), DAILY's tuple order is pinned because
`_daily_at()` unpacks positionally, and `earnings_dates()` staying inert is now enforced by a
test rather than a comment. **They found a real bug:** an empty/header-less CSV raised
StopIteration out of the loader; it now degrades to "no data".

**Tests: 98 passing across six suites** (bulk 8, edge 27, engine 19, intraday 13, screener 13,
SaaS 18).

---

## 0. THIS SESSION (bulk caches wired into the panel)

The caches are now actually consumed by `build_fundamental_panel`, which they were not before.

**Market cap + ratios from DAILY.** `_daily_at()` walks the month-end rows backwards to the
last one on/before `as_of`, so it cannot see the future. Market cap now comes from Sharadar's
own point-in-time figure, with shares x price kept only as a fallback (each row records which
was used in `_mc_src`). Spot-check: AAPL at 2015-06-30 -> market cap **$722.6B, PE 15.1,
PB 5.6, PS 3.4, EV/EBITDA 10.1** — historically accurate. A 1990 lookup correctly returns None.

**Survivorship fix from ACTIONS — and a trap avoided.** The panel forward-fills prices onto a
shared calendar, so a delisted name's last close was being carried forward *forever*: Merrill
Lynch, delisted 2008-12-31 at $11.64, contributed a fake flat 0% forward return to every
rebalance date for the following 18 years. All 19,207 delisting dates are now applied as a
mask, and a name that delists mid-window realizes its **last actual traded price** rather than
being dropped (dropping it would re-introduce the very bias the mask removes).

The trap: **Sharadar SEP closes are ALREADY split-adjusted** — AAPL is $0.098 in 1997 and shows
no discontinuity across the 2020 4:1 split. So the ACTIONS split ratios are deliberately NOT
applied; doing so would double-correct every split in the history. This is commented in the
code so it doesn't get "fixed" later.

**SF3 conviction exposed as factor inputs:** `sm_conviction` (sum of position / that manager's
own AUM), `sm_holders`, `sm_breadth` (growth in number of holders), `sm_avg_position`. Lagged
45 days like the other 13F data — necessary because the most recent quarter is always
partially filed (AAPL: 2,551 holders at 2026-06-30 vs 6,060 at 2026-03-31). They are
**inputs only, not yet in NUMBER_THEME** — whether any earns a place is P4's job for CPCV.
Spot-check: AAPL at 2015-06-30 -> 2,325 holders (2,284 prior), conviction 84.7.

**Effect on coverage:** `institutional` rose **70.5% -> 81.7%**. On a 232-name / 110-date panel
the build is now 32s to load + ~20s to score, with per-phase progress visible throughout.

**Tests: 90 passing, 0 failing** (edge 27, engine 19, intraday 13, screener 13, SaaS 18).

---

## 1. What I did this session

1. **P1 — safety + wired the four bulk tables.** `*.zip` (plus `*.csv.gz`, `*.parquet`) added
   to `.gitignore`; all four zips extracted and reduced to compact caches by a new streaming
   loader.
2. **P2 — diagnosed and largely fixed the full-run performance blocker.** Root cause measured,
   not guessed. Progress logging added so a slow run is never again indistinguishable from a
   hung one.
3. Found and fixed **two bugs in my own new code** before shipping.
4. **P3/P4/P5: not started.** Ran out of session.

---

## 2. Concrete results

### 2a. P2 ROOT CAUSE — measured

Profiled `WRDSProvider._indexed()`, which materializes a whole CSV as a dict of per-row dicts:

| table | size | load time | Python heap peak | rows |
|---|---|---|---|---|
| `fundamentals.csv` | 158 MB | **71 s** | 593 MB | 197,265 |
| `institutional.csv` | 16 MB | 8 s | — | 111,104 |
| **`insiders.csv`** | **580 MB** | **289 s** | **2,230 MB** | **5,636,964** |

~6 minutes and >2GB of heap **before the panel scores a single date**. That is why the
2,827-name run produced no output and had to be killed. It was not "needs longer".

**Fixes shipped:**
- `bulk.prepare_insiders()` — streams the 580MB file once and keeps only
  `(filing_date, signed_value)` per ticker (two floats, not a dict of eight strings), cached
  to a pickle. Re-runs load in under a second.
- **Progress logging in `build_fundamental_panel`** — reports every 250 tickers during load
  and every 10 rebalance dates during scoring, to stderr with elapsed seconds.

**Not yet done on P2:** the panel's per-ticker/per-date inner loop is still pure Python
(`_price_extras` runs a 120-point regression per ticker per date ≈ 75M operations on the full
universe). The load phase is fixed; the scoring phase has not been re-profiled or vectorized,
and **the full 2,827-name run has still not been completed end-to-end.**

### 2b. P1 — bulk tables wired (new `valuation/edge/bulk.py`)

Nothing loads a whole file. Each table is streamed once with `csv.reader`, column-pruned,
reduced, and cached. **5.5GB of raw CSV → 214MB of caches:**

| table | raw | rows | cache | prep time | contents |
|---|---|---|---|---|---|
| **SF3** | 2,898 MB | **79,359,661** (75% `SHR`) | **14.8 MB** | 258 s | per (ticker, quarter): holder count, total value, AUM-relative conviction |
| **DAILY** | 2,488 MB | ~34 M | 116.4 MB | 94 s | per ticker: month-end `marketcap / pe / pb / ps / evebitda` |
| **EVENTS** | 53 MB | — | 68.2 MB | 10 s | per ticker: raw `(date, codes)` — **uninterpreted, see 2d** |
| **ACTIONS** | 47 MB | — | 14.5 MB | 2 s | per ticker: splits, dividends, delistings |

Spot-checks that give confidence the parse is right:
- ACTIONS: AAPL splits = 2:1 (2005-02-28), 7:1 (2014-06-09), 4:1 (2020-08-31) — all correct.
  **19,207 tickers carry a delisting date** — the raw material for survivorship-free returns.
- SF3: AAPL 2026-03-31 = **6,060 holders**, conviction 546.9; KO = 1,405 holders, conviction
  12.6. The ordering is sensible (mega-cap held by nearly everyone).
- DAILY: AAPL 2026-07-29 marketcap $4.97T, PE 40.5, PB 46.6 — plausible, and now available
  directly instead of being derived from shares x price.

**SF3 is genuinely per-manager** (`investorname` column), so the P3 conviction signal is
buildable — a change from last session's finding, which was based only on the aggregate
`institutional.csv` in the older bundle.

### 2c. Two bugs I introduced and caught before merge

1. **`prepare_sf3` silently produced zero rows.** `main()` passed `rebuild` positionally into
   the third parameter, which was `security_type`, so the filter compared `securitytype` to
   `True` and discarded all 59.5M matching rows — while reporting success. Fixed by reordering
   the signature *and* switching every call site to keyword arguments so a future signature
   change cannot misbind the same way. Caught only because the row count printed 0.
2. **EVENTS earnings-code guess was wrong** — see 2d.

### 2d. EVENTS: earnings dates NOT extracted, deliberately

I initially assumed codes 11–17 were the earnings family. That is wrong: AAPL's recent rows
carry codes 22 / 52 / 57 / 91, and the frequencies don't fit a quarterly cadence (code `11`
appears ~18x per ticker over ~24 years, far too few; `91` ~95x, closer but unverified). The
download contains no legend.

Shipping a plausible-looking earnings calendar built on a guess would silently corrupt any
earnings-aware factor, so `prepare_events()` stores the **raw codes** and
`bulk.earnings_dates()` returns `[]` until `bulk.EARNINGS_CODES` is populated from Sharadar's
EVENTS documentation. The table is wired and queryable; only the interpretation is pending.

### 2e. Tests

**90 passing, 0 failing** — edge 27, engine 19, intraday 13, screener 13, SaaS 18. No new
tests this session: `bulk.py` is exercised end-to-end against the real 5.5GB files (results in
2b) but has no unit tests yet. **That is a gap** — the `security_type` bug in 2c would have
been caught instantly by one.

---

## 3. What's blocked / not done

1. ~~Full 2,827-name run~~ **DONE — see section 0.** It completes in minutes now, not never.
2. ~~Caches not consumed by the panel~~ **DONE last session** (PIT market cap, survivorship
   mask, SF3 inputs). SF3 conviction is exposed as inputs but deliberately not yet in
   NUMBER_THEME — that's P4's decision to make under CPCV.
3. **P3 (SF3 smart-money conviction signal): not started.** Inputs are ready.
4. **P4 (re-check `low_risk` / `neg_asset_growth` / `capital_discipline`): not started.**
   Previous session's numbers stand: `neg_vol` median IC −0.078, `neg_asset_growth` −0.029,
   `low_risk` theme pooled IC −0.048, and CPCV independently zeroed `low_risk`.
   **No live scoring was changed.**
5. **P5 (winsorize / robust MAD z-scores / industry-relative ranking): not started.**
6. FMP/grades remain parked as instructed — no calls made.

---

## 4. Recommended next step

1. **P4 — SF3 smart-money conviction.** Now the most valuable open item: the full run shows
   13F dependence is *lower* than feared (+5.1% -> +3.9% without it, vs a halving on the
   800-name run), and the SF3 inputs (`sm_conviction`, `sm_breadth`, `sm_holders`,
   `sm_avg_position`) are already computed point-in-time and waiting. Test on large caps, then
   validate under CPCV before registering anything in NUMBER_THEME.
2. **P5 — the hurting factors.** `low_risk` (negative pooled IC, zeroed by the 800-name CPCV),
   `neg_asset_growth` (wrong sign), and re-check `capital_discipline` now `assets` is
   populated. Report ICs; don't change live scoring without sign-off.
3. **P6 — robustness** (winsorize/clip, median-MAD z-scores, industry-relative ranking). Given
   PBO 53%, robustness work is now more valuable than any further weight search.
4. **Do NOT apply any weighting from the full run.** PBO 53% and a walk-forward refusal are the
   signal to stop tuning, not to pick the least-bad candidate.
5. **P7 — social preview** (og:image etc). Independent, still untouched.
6. Fill in `bulk.EARNINGS_CODES` from Sharadar's EVENTS docs to activate earnings dates.

---

## 5. Standing notes

- `data/` is gitignored, and `*.zip` / `*.csv.gz` / `*.parquet` are now ignored
  path-independently. The raw bulk downloads and every derived cache stay local. Nothing
  licensed was committed.
- Bulk layout: raw zips in `data/raw/`, extracted CSVs in `data/bulk/`, caches in
  `data/bulk/prepared/`. Rebuild with
  `python -m valuation.edge.bulk --bulk-dir data/bulk --cache-dir data/bulk/prepared [--only sf3] [--rebuild]`.
- **The most recent SF3 quarter is incomplete** (2026-06-30 shows 2,551 AAPL holders vs 6,060
  the prior quarter) because 13F filings arrive over the following weeks. Any point-in-time use
  must lag it — the existing 45-day `inst_lag_days` convention applies.
- The live hot-list scan runs at 22:23 UTC and uses the FMP key.
- Archive writes to `data/archive/` every scan (append-only, never read by the live app).
