# CODE_AUDIT.md — end-to-end foundation audit (2026-07-31)

> ## STATUS (updated 2026-07-31, after P7/P8/P9b/P10)
> | finding | status |
> |---|---|
> | **C1** currency mismatch | **FIXED & re-validated.** PBO 13.3%→6.7%, value theme t +1.34→+1.46 (all six inputs improved), foreign top-decile over-representation 1.35x→0.56x. **The audit missed `neg_ps`** (it computes `market_cap/revenue` in the panel, not Sharadar's column) — also fixed. **And `fxusd` is a DIVISOR, not a multiplier**; the suggested `fcf × fx` would have squared the error. |
> | **H1** no correctness layer | **SHIPPED** as `sanity_check` (range / subgroup-pegging / market-cap divergence). Verified it *would* have caught C1: foreign names sat at the 86th percentile of book_to_price and earnings_yield pre-fix. |
> | **M2** SanDisk/WDC market cap | **DOES NOT REPRODUCE — unresolved, not fixed.** DAILY cap and shares×price agree to 1.6x, the 148M share count is plausible, and the price ran 29.6x over 17 months with ZERO discontinuities (WDC 10.3x, MU 8.5x — the whole storage complex). If wrong, the error is upstream in the PRICE, which both estimates share and no cross-check between them can detect. The divergence check *does* catch genuine cases (AIV 71x, EQC 53x). |
> | **M3** `sector_neutral` inert | **UNBLOCKED, then REJECTED on merit.** TICKERS downloaded (48,925 tickers, sector coverage **100.0%** of the panel universe), `sector_neutral` now functional — and industry-relative ranking **fails the pre-committed held-out margin in both directions** (early +0.41 t but −0.16% alpha; late −0.22 t, −0.62% alpha). Kept off. |
> | **L1** two "gross alpha" conventions | documented in both places; unchanged. |
> | **L2** autolearn unreviewed | unchanged; still inactive. |
>
> **P9b** (headless book) shipped: `python -m valuation.edge.valquo_index --full-universe`.
>
> **Research backlog status (2026-07-31):** ML tree combiner **TESTED AND REJECTED** (median OOS
> IC +0.0531 linear vs +0.0393 GBM; net alpha −8.2pp roth / −4.0pp taxable; fails in both
> halves). P13 in the roadmap below is therefore **closed, not pending** — re-open only with
> materially more data, not a different model.
>
> **P12 PEAD data blocker CLEARED (2026-08-01):** the EVENTS earnings code is **22**,
> decoded empirically (median 3 days before the SF1 filing; the only code with an abnormal
> price move, 1.64x baseline vs 0.84-1.15x for all others). `bulk.EARNINGS_CODES` is
> populated and `earnings_dates()` returns real dates. Coverage is PARTIAL (~2.83/ticker/yr
> vs ~4 expected) — a missing date means unknown, not 'no announcement'. The PEAD SIGNAL
> itself was then BUILT AND REJECTED (pead_car t +2.21 standalone but fails the held-out
> margin both ways; the drift variant has NO signal at t -0.47, which is backwards for PEAD,
> and pead_car is +0.286 correlated with ret_6_1 which already scores t +3.40). P12 is
> CLOSED. Elite-manager 13F was then also BUILT AND REJECTED (t +1.32 vs a 2.0 bar, below
> both sm_breadth +1.73 and inst_accum +1.88 already in the theme; weighting by manager
> track record moved conviction ~1.26 -> 1.32, noise).
>
> **THE RESEARCH BACKLOG IS NOW EMPTY AND ALL THREE ITEMS REJECTED.** The shipped model is
> unchanged. The consistent reading: the signal set is SATURATED for this dataset — more
> model capacity and more re-cuts of the same data do not add. The remaining levers are
> genuinely different data (VALQUO_NEXT_EDGE Tier 2: FINRA short interest, EDGAR 13D/8-K,
> congressional trades, IBES estimate revisions).


Static audit of the quant foundation (panel → factors → data path) prompted by finding the
second currency bug. Goal: account for every bug / mistake / skipped improvement before building
further, and re-order the roadmap around what's real. Read `HANDOFF_STATUS.md` for prior context.

Scope of this pass: the code the EDGE rests on — `fundamental_panel.py`, `factors.py`,
`data_providers.py`, `cross_sectional.py`, `valquo_index.py`, `settings.py`, and the Sharadar
export itself. The peripheral systems (intraday/options engine, SaaS/web app) were NOT deeply
audited — they are downstream products, not the foundation; a lighter pass on them is listed as a
later item.

---

## THE META-FINDING — one bug class has now shipped FOUR times

Every foundation bug this project has hit shares a signature: **the run completes, raises no
error, and the numbers look plausible — but a factor is silently wrong.**

1. `assets` dropped from the loader allowlist → `capital_discipline` half-empty for months.
2. `roic`/`roe`/`assetturnover`/`beta`/`growth_accel` blank in the ARQ export → `quality` scored
   on 8 of 10 inputs, `low_risk` on 1 of 2 (P5).
3. `_f()` returned NaN instead of None → F-Score counted MISSING tests as FAILED (P5).
4. **Currency mismatch → the entire `value` theme is garbage for foreign names (this audit).**

The `signal_coverage()` guard added in P5 catches class (1)/(2) — EMPTY columns. It does **not**
catch (3) or (4), because those columns are fully populated and just **wrong**. The single
highest-leverage fix coming out of this audit is a **correctness/sanity layer** (H1 below) that
checks values are *sane*, not merely *present*. That turns "we find these one at a time, after
they bite" into "the pipeline flags them on the first run."

---

## FINDINGS

### CRITICAL

**C1 — Currency mismatch corrupts the entire `value` theme for foreign names.**
Every value input that divides a fundamental against a USD market cap or EV uses the **raw
(local-currency)** fundamental:

| factor | formula | file:line | currency | verdict |
|---|---|---|---|---|
| `book_to_price` | `total_equity / market_cap` | factors.py:111 | local ÷ USD | BROKEN |
| `earnings_yield` | `netinc / market_cap` | fundamental_panel.py:198 | local ÷ USD | BROKEN |
| `fcf_yield` | `fcf / market_cap` | fundamental_panel.py:199 | local ÷ USD | BROKEN |
| `ebit_ev` | `ebit / ev` | fundamental_panel.py:200 | local ÷ USD (ev is USD) | BROKEN |
| `ev_sales` | `ev / revenue` | fundamental_panel.py:201 | USD ÷ local | BROKEN |
| `neg_ps` | `-ps` (Sharadar ratio) | factors.py:88 | consistent | ok |

- Verified in the data: `equity`, `netinc`, `ebit`, `revenue`, `debt`, `cashneq` are in the
  company's **reporting currency**; `marketcap` and `ev` are **USD** (TSM: `ev` 2030.84 =
  marketcap 2097.15 + debtusd 29.63 − cashusd 95.94, exactly). Sharadar ships USD variants
  (`equityusd`, `netincusd`, `revenueusd`, `ebitusd`) that the code does not use.
- Magnitude: SK Telecom's book equity is 13.3 **trillion** won, so `book_to_price` computes to
  **≈892** vs a correct **≈0.59** — a ~1,500× fake cheapness. On correct ratios these names are
  *expensive* (TSM pe 34.8, SKM pe 61.5), yet they dominate the value-tilted book (top 6 of the
  86-name inception book are all foreign ADRs).
- Blast radius: **167 of 2,827 names (5.9%)** report in a foreign currency (`equity ≠ equityusd`).
  All are pushed systematically toward "ultra-cheap," and the damage concentrates in the **top
  decile**, exactly where portfolio selection happens.
- **This was in the backtest too** — foreign names were mis-valued across all 18 years. The
  validated edge (+11.77% top-decile) must be re-measured. It could move either way: if the
  forced-cheap foreign names under-performed, fixing this *improves* the edge; `value` is also the
  weakest theme (t +1.34), and part of that weakness may be this contamination.

Fix (in `_sf1_to_metrics`, fundamental_panel.py ~156–204; root cause is the `_KEEP` allowlist in
`data_providers.py:252` which never loads the `*usd` columns):
- `book_to_price` → `equityusd / market_cap`
- `earnings_yield` → `netincusd / market_cap`
- `ebit_ev` → `ebitusd / ev`  (ev already USD)
- `ev_sales` → `ev / revenueusd`
- `fcf_yield` → `(fcf × fx) / market_cap`, where `fx = equityusd / equity` (no `fcfusd` column
  exists — derive the FX factor from any local/usd pair)
- Add `equityusd, netincusd, revenueusd, ebitusd` to `WRDSProvider._KEEP`.
- **Do NOT touch** roe/roic/margins/growth/momentum/size/institutional — they use same-currency
  ratios or price returns and are correct as-is.
- Then re-run the full 2,710-name backtest and report: does top-decile alpha / long-short t / PBO /
  DSR move, and what is the foreign-name share of the top decile before vs after.

### HIGH

**H1 — No correctness layer; the coverage guard checks presence, not validity.**
See the meta-finding. Add a post-panel sanity pass that (a) asserts each ratio factor sits in a
sane cross-sectional range, and (b) flags when an identifiable subgroup systematically pegs a
factor — the foreign-currency reporters are detectable for free (`equity ≠ equityusd`), and
"every foreign name is in the top 2% of book_to_price" is exactly the signature this would catch.
Ship it as a `sanity_check` block in BACKTEST_RESULTS.json next to `signal_coverage`. Highest
preventive value in this list; do it alongside C1 so the re-run is itself validated by it.

### MEDIUM

**M2 — DAILY market cap is wrong for recycled / spun-off tickers.** The inception book lists
SanDisk (SNDK) at $337B and Western Digital (WDC) at $220B, both ~10× reality (SanDisk spun out of
WDC in 2025). Pollutes the `size` theme and the market-cap-scaled cost model for those names, and
undermines trust in the displayed book. Add a divergence check (DAILY marketcap vs shares×price)
and/or a recycled-ticker guard. Low portfolio impact (few names, weak theme) but visible.

**M3 — `sector_neutral` has been inert in every backtest.** No sector column exists on disk;
the panel hard-codes `"sector": ""` (fundamental_panel.py:195), so the sector-neutral path groups
on a constant. Known from P6.3b. Unblock with one Sharadar TICKERS download → ticker→sector map →
populate `metrics["sector"]`. Bonus: the same download carries country/exchange, which
independently settles the ADR question from C1. Caveat: TICKERS gives *today's* classification, a
mild look-ahead on historical rows (usually benign; state it, don't hide it).

### LOW / footguns (not bugs)

**L1 — Two "gross alpha" numbers coexist** (+11.77% arithmetic from `quantile_backtest` vs +13.71%
compounded from the cost model). Documented in P6, but a footgun — always label which convention,
or standardize on one.

**L2 — Self-learning autolearn loop not audited here.** It is OOS-gated and currently inactive
(weights are hard-coded in `settings.py`), so it is low risk today, but review it before ever
enabling gated auto-apply of weights.

---

## AUDITED AND CLEAN (no issue found)

- **Point-in-time integrity.** `_pit` selects the latest row with `datekey ≤ as_of` (filing date,
  not fiscal period — no look-ahead); `_daily_at(as_of)` for market cap; all fundamental/13F/YoY
  cutoffs are `as_of − lag`; forward returns are delisting-aware (use last traded price when a name
  delists mid-window); `ffill` only carries a *past* close forward, never a future value back.
  This is the most carefully built part of the codebase.
- **Z-score / winsorization** (`cross_sectional.py`). Winsorize at 2/98; both `zscore` and
  `robust_zscore` guard `sd == 0` and all-NaN (return NaN, no div-by-zero); robust falls back to
  classic when MAD == 0. Correct.
- **Sign / orientation.** Every theme is oriented higher = better before z-scoring; `neg_*` inputs
  negated once; monotonicity sign is fixed and pinned by `test_monotonicity_sign_convention`.
- **Composite assembly** (`factors.py`). Only `value` is exposed to C1; growth, momentum (incl.
  residual-momentum), low_risk, capital_discipline, size, institutional, insider all use
  same-currency ratios or price returns.
- **Live weights** (`settings.py`): value/quality/momentum/insider/capital_discipline/size/
  institutional = 0.125 each; low_risk = 0 (P5); sentiment = 0 (grades empty). Matches intent.

---

## RE-ORDERED P# ROADMAP (new findings merged with what was outstanding)

**P7 — Currency correctness fix + backtest re-validation (C1). CRITICAL, blocks everything.**
Nothing downstream should be trusted until this is fixed and the edge re-measured. Includes
regenerating a clean inception `valquo_index.json`.

**P8 — Data-correctness / sanity layer (H1 + M2).** The subgroup/range guard and the recycled-
ticker cap check. Do it with P7 so the re-run is validated by it. This is the fix that stops the
recurring class.

**P9 — Forward Valquo-vs-SPY tracker on the corrected book (Cowork).** Was in flight; correctly
gated behind P7/P8. Once the book is clean and the edge re-confirmed, stand up the live track.

**P10 — TICKERS download → sector data (M3).** Unblocks industry-relative ranking (test it through
`holdout_theme_validate`) and independently verifies the ADR country/exchange from C1.

**P11 — Social preview / og:image** (the long-deferred item).

**P12 — PEAD from EVENTS** (needs the earnings-code legend first).

**P13 — ML tree combiner** (worthwhile now that several real, currency-correct signals exist).

**P14 — Gated auto-apply of weights** (after the L2 autolearn review).

**Parked:** WRDS/IBES estimate-revisions sentiment (data-gated).

## FINRA short interest (P24.1, 2026-08-01)
`valuation/edge/short_interest.py` — committed results-free, then the verdict appended.
REJECTED: t +1.04 / +0.42 vs a 2.0 bar. Not low power — controls on the same 34-date window
score +3.53 (ret_6_1) and +3.27 (inst_accum). Genuinely orthogonal (+0.048 vs ret_6_1), just not
predictive; -0.311 vs size.

The one thing to not break: FINRA gives only `settlementDate`, which is ~2 weeks BEFORE the data
is public. `fetch_short_interest` stamps every row with settlement + 15 days and deliberately
never returns the settlement date, so a future caller cannot reintroduce the look-ahead.
Pinned by `test_short_interest_uses_publication_date_not_settlement`.

Cache: `data/bulk/prepared/short_interest.pkl` (167MB, gitignored with the rest of data/).

## SEC EDGAR 13D/13G (P24.2, 2026-08-01)
`valuation/edge/edgar13d.py` - committed results-free, verdict appended. REJECTED: activist_13d
t -0.69 (wrong sign), and the pre-committed passive 13G placebo beat it by 2.35 t.

Two things not to re-break, both pinned by `test_edgar13d_dating_and_form_rename`:
- BOTH form spellings are required. The SEC renamed "SC 13D" -> "SCHEDULE 13D" during 2024;
  matching only the old one silently empties 2025 onward (~30 vs ~15,000 filings/quarter).
- form.idx must be parsed by STRUCTURE, not fixed width - the column offsets moved over EDGAR's
  history and a fixed-width parse returns nothing for whole eras.

Only `Date Filed` is ever read (the public disclosure date); the 5%-crossing event date is not
parsed at all. Caches: `data/bulk/prepared/edgar13d.pkl`, `cik_ticker.json` (gitignored).

## USAspending + congressional trades (P24.3/P24.4, 2026-08-01)
`valuation/edge/usaspending.py`, `valuation/edge/congress.py` - both committed results-free,
verdicts appended. USAspending REJECTED (t +0.70, subset had power). Congress INCONCLUSIVE
(t +0.97, best control only +1.87 - no verdict claimed).

Things not to re-break:
- **congress.py must never store `transaction_date`.** 21.9% of filings are late; the 90th
  percentile trade-to-filing gap is 210 days and the max is 4,049. Using the transaction date
  injects up to seven months of look-ahead. The loader discards the field rather than merely
  declining to filter on it. Pinned by `test_congress_never_stores_transaction_date`.
- **usaspending.py stamps quarter_end + 60 days** and never returns the raw quarter end. FPDS has
  a reporting delay and DoD actions were historically withheld 90 days.
- Federal award momentum is 4-quarters-over-4-quarters on purpose: obligations spike hugely in
  the September fiscal year-end, so a shorter window measures the calendar, not the company.
- The USAspending recipient->ticker map is exact-normalized-name only, never fuzzy: a false match
  silently credits another company's contracts to a stock. Subsidiaries (Electric Boat -> GD) are
  therefore missed; no parent-rollup endpoint exists (all three candidate paths 404).

Caches (gitignored): `data/bulk/prepared/usaspending.pkl`, `congress.pkl`, `sec_names.json`.

## Options track (2026-08-02)
See `OPTIONS_BACKTEST_RESULTS.md`. Scream-buy: +10.4%/trade over 1,540 trades net of spread,
positive in both held-out halves, but 15 trades are 98% of the dollar profit.

Things not to re-break:
- **Two price series.** `closeadj` for technicals, `closeunadj` for ALL option maths. Option
  strikes are never split-adjusted; mixing them made ATM IV solve to None on every pre-split
  date and picked contracts from the wrong end of the ladder, silently. Pinned by
  `test_options_split_adjustment_two_series`.
- **Fill defaults to buying the ask and selling the bid.** Mid fills are a diagnostic, never a
  headline. Pinned by `test_options_fill_engine_charges_the_spread_both_ways`.
- **Expired-worthless contracts must post -100%**, not vanish - that is the survivorship bias
  that flatters options backtests. Pinned by `test_options_expired_worthless_is_recorded_not_dropped`.
- **Year gaps are recorded and the name excluded**, never silently under-sampled.
- **The runner takes a PID lock**: two runners sharing one bank silently corrupted each other
  (a zombie run overwrote a 197-trade result with 5 trades).
Caches (gitignored): `data/options/<SYM>/<SYM>-<YEAR>.pkl`, `optbt_state.pkl`.
