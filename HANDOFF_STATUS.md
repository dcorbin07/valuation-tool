# Valquo — handoff status

Written at the end of every Claude Code session. Overwritten each time, so this is always
the current state, not a log. Plain text, no colour codes — the Cowork agent reads this
file directly.

**Session date:** 2026-07-29 (third session that day)
**Branch:** `worktree-wire-bulk` -> merged to `main`

> **Scope warning:** this session wired the bulk caches into the panel (new P1) and left
> **P2-P7 not started** — including the full-universe run, which is still the key outstanding
> validation. See section 3.

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

1. **The full 2,827-name backtest still has not completed.** The load phase is fixed
   (~6 min → seconds on re-runs) but the scoring loop is untouched, so the run time is still
   unknown. This remains the key outstanding validation.
2. **DAILY / SF3 / ACTIONS are prepared but NOT yet consumed by the panel.** The caches exist
   and are correct; `build_fundamental_panel` does not read them yet. So market cap is still
   derived from shares x price, returns are still not split/delisting-adjusted, and the SF3
   conviction figures are not in any factor. **Wiring the caches into the panel is the next
   concrete step.**
3. **P3 (SF3 smart-money conviction signal): not started.** Inputs are ready.
4. **P4 (re-check `low_risk` / `neg_asset_growth` / `capital_discipline`): not started.**
   Previous session's numbers stand: `neg_vol` median IC −0.078, `neg_asset_growth` −0.029,
   `low_risk` theme pooled IC −0.048, and CPCV independently zeroed `low_risk`.
   **No live scoring was changed.**
5. **P5 (winsorize / robust MAD z-scores / industry-relative ranking): not started.**
6. FMP/grades remain parked as instructed — no calls made.

---

## 4. Recommended next step

1. **Wire the prepared caches into `build_fundamental_panel`** (item 3.2). Highest value: it
   replaces the hand-computed market cap that hid the `assets` bug, and it's the prerequisite
   for P3.
2. **Add unit tests for `bulk.py`** before building on it (2e) — one test would have caught the
   `security_type` misbinding.
3. **Re-profile the panel scoring loop, then run the full universe unattended** with the new
   progress logging to see where the remaining time actually goes.
4. Then P3 (conviction signal), P4 (the two problem factors), P5 (robustness).
5. Fill in `bulk.EARNINGS_CODES` from Sharadar's EVENTS docs to activate earnings dates.

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
