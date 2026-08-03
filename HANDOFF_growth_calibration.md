# HANDOFF — calibrating the growth/fair-value lens

Branch: `worktree-growth-valuation`. Date: 2026-08-02. Follows `HANDOFF_growth_valuation.md`,
which made the fair value method-correct for pre-profit names. This asks the next question:
is the resulting number worth anything as a SIGNAL?

Everything below is the full universe — 2,827 tickers in the export, 2,710 with usable
price history, **2,625 that produced at least one valuation** — over ~18 years and 110
rebalance dates, point-in-time throughout, using the LIVE valuation engine (not a
re-implementation). No subset: the methodology rule in CLAUDE.md forbids resting a verdict
on 400/800-name samples, and this verdict does not.

## The answer, up front

**Do not weight the fair-value gap as alpha.** It is a framing and communication tool.

There is a weak hint at a one-year horizon that does not clear this project's own bar, and
nothing at all at three months. Worse, the whole DCF/growth-lens/maturity-blend apparatus
ranks stocks LESS well than the plain ratios it is built on top of.

| | 63-day horizon | 252-day horizon |
|---|---|---|
| rows | 129,574 (2,625 names) | 127,625 (2,554 names) |
| median rank IC | +0.0092 | +0.0108 |
| IC t-stat | **+0.99** | +1.91 → **+0.52 .. +1.44** on independent windows |
| long-short | +7.85%/yr (t +1.27) | +8.82%/yr (t +1.82) → **t +0.67 .. +1.24** independent |
| top-decile alpha | +7.92%/yr (t +2.04) | +11.17%/yr (t +3.71) → **t +1.78 .. +1.93** independent |
| monotonicity | -0.297 | -0.406 (-1.0 = perfectly ordered) |

Two corrections had to be applied before those numbers meant anything, and both mattered.

## Correction 1 — the 63-day "significant" alpha is a size effect

The widest-discount decile has a median market cap of **$1.73B against the universe's
$4.60B**. Split each date into market-cap terciles and measure the gap INSIDE each:

| tier | median cap | median IC | IC t | long-short | top-quintile alpha |
|---|---|---|---|---|---|
| small | $1.05B | +0.0042 | -0.51 | -0.4% (t -0.06) | +3.6% (t +0.95) |
| mid | $4.66B | +0.0167 | +0.69 | -0.5% (t -0.12) | +0.4% (t +0.21) |
| large | $22.70B | +0.0108 | +0.87 | +1.0% (t +0.31) | +0.2% (t +0.16) |

Nothing clears t=2 anywhere. The aggregate +7.92% is the gap sorting on market cap and
collecting the small-cap premium, which the `size` theme already exists to capture.

## Correction 2 — the 252-day t-stats were inflated by overlapping windows

A 252-day forward return sampled every 63 days overlaps its next three observations, so
the IC series is autocorrelated by construction and the t-stat — which assumes independent
draws — is inflated by roughly sqrt(4) = 2x. That is enough to turn "nothing" into
"significant", so `nonoverlapping_check()` re-runs on every 4th date, at all four offsets:

| offset | dates | median IC | IC t | LS t | top-decile alpha |
|---|---|---|---|---|---|
| 0 | 27 | +0.0249 | +1.44 | +0.67 | +9.6% (t +1.82) |
| 1 | 27 | +0.0158 | +1.26 | +1.24 | +14.8% (t +1.93) |
| 2 | 27 | +0.0225 | +0.52 | +0.98 | +8.9% (t +1.93) |
| 3 | 26 | -0.0100 | +0.59 | +0.72 | +11.4% (t +1.78) |

**The honest reading:** the top-decile alpha is positive and remarkably consistent across
all four independent subsamples (+8.9% to +14.8%, t +1.78 to +1.93) — that consistency is
mild evidence it isn't pure noise. But it never clears t=2 in any of them, the IC and
long-short don't hold up at all, and the decile curve is U-shaped (D10 = +21.1%/yr, the
second-highest bucket), which is not a valuation ordering. Both tails outperform the
middle, consistent with the gap picking up high-uncertainty names at both ends.

This project's stated bar is t>2. It is not met. Reporting +11.17% (t +3.71) would have
been the easy and wrong thing to do.

## The measurement is not broken — a positive control says so

A null is worthless if the yardstick can't find anything. Two plain value factors,
measured on the SAME rows by the SAME code (same overlap treatment, so comparable):

| factor | 63d median IC | 63d IC t | 252d median IC | 252d IC t |
|---|---|---|---|---|
| `ebit_ev` | +0.0140 | +1.73 | **+0.0568** | **+3.15** |
| `neg_ev_sales` | +0.0259 | +1.92 | **+0.0317** | **+3.27** |
| **the blended fair-value gap** | **+0.0092** | **+0.99** | **+0.0108** | **+1.91** |

Both controls are consistent with the value theme's independently measured strength
(median IC +0.0211, t +1.461 in `BACKTEST_RESULTS.json`), so the harness detects real
signal in real data.

**For scale, against the nine live themes** (same file, same universe, same 63-day
horizon). The fair-value gap's +0.0092 would rank below every theme that carries a
positive weight — below even `size`:

| momentum | quality | institutional | capital_disc. | growth | value | size | **the gap** | low_risk | insider |
|---|---|---|---|---|---|---|---|---|---|
| +0.0517 | +0.0363 | +0.0297 | +0.0232 | +0.0221 | +0.0211 | +0.0126 | **+0.0092** | -0.0014 | -0.0034 |

**The uncomfortable part: a plain EV/Sales sort ranks stocks better than the full
valuation engine does, at both horizons and by a wide margin at one year.** Every
modelling choice in the blend — WACC, terminal margin, exit multiple, maturity weights —
is a place to add noise, and on this evidence that is the net effect for ranking purposes.
`tests/test_calibration.py` also plants a known signal in a synthetic panel and confirms
the machinery recovers it, and reports a null panel as null, so the harness is pinned from
both directions.

## Does the growth lens help, or does it just look reasonable?

This was the actual question behind the task. **It does not help.** The pre-profit tier has
a NEGATIVE information coefficient at both horizons — the only tier that does:

| tier (63d) | rows | median IC | IC t | long-short | top-quintile alpha |
|---|---|---|---|---|---|
| deep_growth (maturity <0.35) | 11,432 | **-0.0084** | **-1.26** | +3.9% (t +0.48) | **-1.5%** (t -0.29) |
| mixed (0.35–0.65) | 34,725 | +0.0038 | +0.68 | +7.7% (t +1.66) | +5.2% (t +1.85) |
| established (>0.65) | 83,417 | +0.0028 | +0.50 | +1.4% (t +0.53) | +1.8% (t +1.35) |
| growth-led (revenue lens >50% of blend) | 16,768 | +0.0276 | +0.85 | +0.7% (t +0.10) | +0.8% (t +0.17) |

At 252 days `deep_growth` is still negative on IC (-0.0186, t -0.88) though its long-short
turns positive (+18.3%, t +2.98 — before the overlap correction, and on the noisiest,
widest-dispersion tier in the panel; do not lean on it). `mixed` is the best cut at both
horizons and still doesn't clear the bar once corrected — and being the best of four cuts
is exactly the kind of finding that doesn't replicate.

So: the growth lens made the number DEFENSIBLE (it stopped publishing $2.63 for a $65
stock, and stopped printing three negative scenario cards under a positive headline). It
did not make it PREDICTIVE. Those are different claims and only the first is supported.

## Does the market-implied growth ever come true?

No — it is a "priced for perfection" flag, not a forecast. Realized revenue CAGR over the
following 3 years, same rows:

| group | n | median implied | median realized | realized >= implied | rank corr |
|---|---|---|---|---|---|
| growth-led names | 11,927 | **+49.4%** | **+11.8%** | **30.8%** | +0.143 |
| everything else | 87,064 | +13.3% | +5.9% | 39.7% | +0.189 |

A growth-led name's price implies ~49%/yr and the company delivers ~12%. Reality clears
the bar under a third of the time — and that comparison is **tilted in the company's
favour**: the implied figure averages over the DCF's whole 5-10 year forecast while the
realized figure covers only the first 3 years, which are the fastest years of a fading
growth path. 30.8% is a floor, not an exaggeration.

**But the rank correlation is positive** (+0.14 to +0.21): a higher implied growth does
weakly identify a company that subsequently grows faster. So the number is not noise — it
is just not a level anyone should treat as a forecast. The UI already says "the price
implies at least ~94%/yr; our base case is ~34% — judge this one on whether that gap is
achievable", which is the right framing for a statistic that behaves this way.
**No wording change needed.**

## What this does NOT say

- It does not say the valuation is wrong. A fair value can describe what a business is
  worth and still not predict a 3-month return; that is the normal case for intrinsic
  valuation.
- It does not say the 7b work was wasted. The failure it fixed — a mature-sector multiple
  pointed at a hypergrowth company, plus scenario cards from an excluded model — was a
  correctness bug, and correctness is not conditional on predictiveness.
- It does not license removing the fair value from the site. It is fine as a framing tool.
  It should not be a scoring input.

## Item 4 — the EV/EBITDA path

Checked and confirmed wired end-to-end, not merely present:

- `screener/providers.py` emits `ev_ebitda`; `screen._rows_from` carries it; `fairvalue.py`
  bridges it through net debt (`implied EV = EV x peer/own`, `equity = implied EV - net debt`).
- `comps.py` does the same on the deep page, and `growth.exit_sales_multiple` uses the
  EV/EBITDA benchmark against the company's own sustainable margin.
- Coverage on the real panel: **74.1% of rows** actually used an EV/EBITDA-implied value
  (86.6% used EV/Sales). Not a wired-but-empty column.
- New test `test_fair_value_uses_ev_ebitda_where_ebitda_is_positive` pins both halves: the
  net-debt bridge arithmetic, and that a NEGATIVE EBITDA is dropped rather than used.

## Item 5 — the blend across the whole spectrum

Real point-in-time rows from the run (`spot_checks` in the JSON):

| tier | example | price | fair value | method |
|---|---|---|---|---|
| financial | MS 2012-10-08 | $12.55 | $4.77 | justified P/B from ROE |
| financial | KMPR 2019-10-14 | $63.79 | $34.11 | justified P/B from ROE |
| established | GRMN 2020-01-14 | $84.41 | $72.74 | 65% DCF · 22% multiples · 13% growth |
| established | TRI 2013-04-12 | $23.56 | $22.52 | 49% DCF · 40% multiples · 10% growth |
| deep growth | XPO 2014-04-11 | $9.73 | $46.41 | 87% growth · 10% multiples · 3% DCF |
| deep growth | ATHM1 1998-12-31 | $37.12 | $0.69 | 88% growth · 7% DCF · 5% multiples |

Banks never touch the FCFF DCF, established names sit close to price on a DCF-led blend,
and pre-profit names are revenue-led and very wide (ATHM1 — a 1998 dot-com — at 2% of its
price, XPO at 4.8x). The width is the honest output for that archetype, and it is why
those rows are marked low confidence and led with the implied-growth read.

## Method notes (what would make this wrong)

- **The engine is the LIVE engine.** `lean_fair_value` calls classify -> WACC ->
  assumptions -> DCF -> comps -> growth lens -> blend, the same functions the website uses.
  Monte Carlo, sensitivity and scoring are skipped only because none can change
  `blend.value`, and `test_lean_path_matches_the_full_pipeline` fails if that ever changes.
- **Point-in-time.** Same calendar, delisting mask and forward-return convention as
  `build_fundamental_panel`. Only filings with `datekey <= as_of` are read.
- **TTM, not quarterly.** The export is ARQ. Feeding a single quarter's revenue into a DCF
  would make every fair value ~4x too low, silently. Pinned by a test; AAPL reproduces
  $182.8B (FY14) and $383.3B (FY23) exactly.
- **Currency (P7).** Market cap is USD, line items are in the reporting currency; all
  monetary lines are divided by `_usd_divisor` before reaching `CompanyData`. The sanity
  layer tests for the P7 signature directly — ADRs are 1.26x represented in the widest-
  discount decile, well under the 2x flag.
- **The share count cancels.** Shares are derived as market cap / price, so
  `fair_value/price == fair_equity/market_cap`. The measurement is immune to ADR ratios,
  share classes and split adjustments. Pinned by a test.
- **Failures are counted, not swallowed.** The panel loop reports how many (date, ticker)
  pairs produced no usable company and how many valuations raised, with the first few
  errors — a silently skipped subgroup is how this project has lost signals before.
- **Constant risk-free rate — TESTED, not just caveated.** No historical yield series is
  on disk, so one rate covers all 18 years, and a higher rate hurts long-duration growth
  names more than short-duration ones, so it is not perfectly neutral cross-sectionally.
  The whole panel was therefore rebuilt at **rf = 2.0%** (vs the 4.3% default — more than
  halved, and roughly the 2012-2021 regime). The conclusion does not move:

  | | rf 4.3% | rf 2.0% |
  |---|---|---|
  | median IC | +0.0092 | +0.0095 |
  | IC t | +0.99 | +0.98 |
  | top-decile alpha | +7.92% (t +2.04) | +7.46% (t +2.01) |
  | small / mid / large topQ alpha t | +0.95 / +0.21 / +0.16 | +1.01 / +0.14 / +0.00 |

  Re-run any rate with `--risk-free`.
- **Today's sector classification** is applied to historical rows (the TICKERS overlay is
  not point-in-time) — the same mild look-ahead the factor panel already accepts.
- **This is a gross-of-costs measurement.** Since the conclusion is "no usable edge",
  costs would only make it worse, so they were not modelled.

## Files

- `valuation/engine/calibration.py` — new. Point-in-time company construction, the lean
  engine path, the panel build, and the measurement (coverage, sanity, IC, deciles,
  non-overlapping re-run, positive controls, size and maturity cuts, half split,
  implied-vs-realized growth, spot checks).
  `python -m valuation.engine.calibration --data-dir data/backtest --json CALIBRATION_RESULTS.json`
  — ~9 minutes for the full universe; `--from-panel-csv` re-measures a dump in seconds.
- `tests/test_calibration.py` — new, 23 tests.
- `tests/test_screener.py` — +1 test (the EV/EBITDA bridge). 23/23.
- `CALIBRATION_RESULTS.json` — the full 63-day run, machine-readable.

**Nothing in the live valuation path was changed by this work.** It is measurement only.

## Recommended next step

Leave the fair value out of the score and keep it as the explanatory number it already is.
If anyone wants a valuation-derived SIGNAL, the evidence points at the raw ratios
(`ebit_ev`, `neg_ev_sales`) already in the `value` theme, not at the blended output.

The one thread worth pulling, if any: the 252-day top-decile alpha was positive in all four
independent subsamples (+8.9% to +14.8%). That is not significance, but it is not nothing
either. The way to settle it is more data, not more slicing of this one — which is the same
answer as task #12 in CLAUDE.md, the forward paper-track. Do not re-cut this panel looking
for a threshold it passes.
