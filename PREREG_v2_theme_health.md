# PREREG — V2, the live theme-health meter

**Committed 2026-08-09, BEFORE `scripts/theme_health.py` existed and before a single live IC was
computed.** `VALQUO_EXTENSIONS.md` V2 requires the horizon, the IC definition, the band
construction and the DEGRADED rule to be fixed before the first computation. They are fixed here.

**WHY THIS PRE-REGISTRATION IS UNUSUALLY EASY TO BELIEVE, AND SAY SO WHEN QUOTING IT.** At this
commit the live record holds **zero closed 63-day windows** — the deepest usable snapshot history
on this machine is 7 calendar days, and every one of those days is synthetic test output (see §7).
There is no live number to tune a threshold against, *even in principle*. This is the same
argument `track_meter.py` makes about its own parameters, and it is the strongest form the
argument takes: not "I did not look", but "there was nothing to look at".

Only three things were measured before this file was written, all of them required by V2 to come
first and none of them an IC: **how many snapshot dates exist, what fraction of each theme is
non-null, and which provider wrote each file.**

---

## 1. The question

The backtest's theme ICs (`per_theme.themes` in `BACKTEST_RESULTS.json`: quality +0.0356,
capital_discipline +0.0297, low_risk +0.0247, …) are measured on ONE Sharadar panel of 69
rebalance dates. **They have never been checked against live forward returns.** V2 asks for a
meter that answers, as windows close, whether a theme is still doing live what the panel says it
did historically.

## 2. Horizon — FIXED

**63 trading days.** Chosen to match the panel's own horizon so the live figure and the backtest
figure are the same object measured on different data. No other horizon is reported.

## 3. IC definition — FIXED, and it is literally the panel's code

For a measurement date `d` and theme `T`: the **Spearman rank correlation across names** between
the theme score recorded at `d` and that name's realized forward return from `d` to `d + 63`
trading days.

* The correlation is computed by **`valuation.edge.fundamental_panel._spearman`, imported
  read-only** — not re-implemented. A re-implementation is a second definition free to drift from
  the first, which is the defect class this project has paid for repeatedly.
* Minimum **20 names** on a date for that date to produce an IC (`theme_ic`'s own `min_names=20`).
* Per theme the reported statistics are the **median IC across dates** (the panel's headline
  statistic) plus the mean, the count of dates, and the per-date rows themselves.
* Forward returns are simple price returns computed from **prices the store already recorded**.
  No vendor call is made by this script, ever — it is offline, reproducible, and cannot exhaust a
  quota. (A live-measurement lane has already lost two full runs to silent Yahoo throttling.)

## 4. Cadence and the overlap — FIXED

**Monthly.** One measurement date per calendar month: the last scan on or before that month's
final trading day.

63 trading days is ~3 calendar months, so **consecutive monthly windows overlap 3:1 by
construction.** That is not hidden and it is not corrected away by dropping observations; it is
priced into the band (§5). Treating overlapping windows as independent is the single easiest way
to manufacture significance here, and it is pre-emptively refused.

## 5. The band — FIXED

An **anytime-valid Robbins normal-mixture confidence sequence**, so the meter may be read every
month with no multiplicity correction invented after the fact. The boundary function is
**`valuation.edge.track_meter.boundary`, imported read-only** — the project gets one boundary
implementation, not two.

* **Observation.** For month `i`, `z_i = IC_i * sqrt(n_i - 1)`, where `n_i` is that month's usable
  cross-section. Under the null of no predictability this has unit variance whatever `n_i` is,
  which is how a varying cross-section is handled exactly rather than approximately.
* **`sigma = sqrt(3) = 1.7320508`.** The overlap design effect: for statistics on `m`-fold
  overlapping windows the lag-`j` autocorrelation is ~`1 - j/m`, so the variance of the running
  sum inflates by `1 + 2*sum_{j=1}^{m-1}(1 - j/m)`, which at `m = 3` is exactly **3**.
* **`rho = 3`**, the value `track_meter` froze — chosen there to minimise the detectable effect
  over the 12-to-60-month range, which is the same range that applies here.
* **`alpha = 0.05 FAMILY-WISE across the 10 themes, i.e. 0.005 two-sided per theme**
  (Bonferroni). **This is not caution, it is a measured correction:** X7 measured that when eight
  themes are tested and the bar is applied to whichever looks best, **39% of pure-noise draws
  produce at least one theme clearing it.** V2 tests ten. The uncorrected per-theme alpha is
  reported alongside as a diagnostic and **carries no verdict**.
* **`sigma` MAY NEVER BE REVISED DOWNWARD** — inherited verbatim from `track_meter`'s rule 1. A
  narrower band makes crossing easier, so a downward revision is indistinguishable from buying a
  result. If the realized sd of `z_i` exceeds `sqrt(3)` the bound is anti-conservative and sigma
  must be RAISED; the script reports **`sigma_breach`** on every call so this cannot pass quietly.

## 6. Verdicts — FIXED

`reference_sign` is the sign of that theme's backtest `median_ic`, taken from
`BACKTEST_RESULTS.json` at run time (with the file's own provenance recorded in the output, so a
stale artifact is visible rather than assumed), and **only when `|median_ic| >= 0.01`**
(`REF_MIN_IC`). Below that the backtest itself is not claiming a direction and no directional
verdict is defined. On today's artifact that gives a reference to 7 themes and withholds it from
`insider` (−0.0052), `sentiment` (empty) and nothing else.

| verdict | condition |
|---|---|
| **DEGRADED** | the running sum crosses the boundary on the side OPPOSITE `reference_sign` |
| **CONFIRMED-LIVE** | the running sum crosses on the SAME side as `reference_sign` |
| **INSUFFICIENT** | no crossing |
| **NO-REFERENCE** | `reference_sign` undefined; crossings still reported as UP-CROSS / DOWN-CROSS, without the degraded/confirmed labels, because "degraded relative to what?" has no answer |
| **NOT-QUOTABLE** | a §7 minimum is unmet; **no IC is printed at all** |

**INSUFFICIENT IS NOT EVIDENCE OF ANYTHING, AND ANY READING OF IT AS REASSURANCE OR AS DOUBT IS AN
ERROR.** `track_meter` makes the same point about its own non-crossing state and it matters more
here: this meter will sit at INSUFFICIENT for years.

## 7. The coverage rule — FIXED, and it is the part most likely to fire

V2 requires snapshot depth per theme to be reported before any IC is quoted, and requires the
output to say for itself when it is too thin. Every floor below is a **refusal to print a number**,
not a footnote attached to one.

| gate | value | why |
|---|---|---|
| `MIN_NAMES_PER_DATE` | 20 | the panel's own `theme_ic` floor |
| `MIN_MONTHS` | 6 | six CLOSED windows before any IC is quoted for a theme |
| `MIN_THEME_COVERAGE` | 0.30 | the project's existing 30% coverage floor (the bar `pead_drift` failed) |
| `MAX_ATTRITION` | 0.20 | a date whose names are >20% unmeasurable forward is VOIDED, not measured on its survivors |
| `MAX_VOIDED_FRACTION` | 0.10 | `track_meter`'s constant: above this the series cannot carry a verdict |
| `PRICE_STALENESS_TD` | 3 | the forward mark must land within ±3 trading days of `d + 63` (`track_meter.MARK_STALENESS_LIMIT_TD`) |
| `SYNTHETIC_PROVIDERS` | excluded | see below |

**SYNTHETIC SOURCES ARE EXCLUDED FROM MEASUREMENT AND NAMED IN THE OUTPUT.** Every scan archive on
this machine — all 7 days of it — was written by provider `"synthetic (offline test)"` with tickers
like `SYN0802`. Measuring an IC on those rows would produce a real-looking number about nothing,
which is precisely the failure mode `CLAUDE.md` records for roadmap #12 ("45/45 tests pass, 0
rows"). The filter is pre-committed here so that it cannot later be described as a convenient
exclusion of inconvenient data.

## 8. Expectation, written down first

Per the project's standing rule that expectations are recorded before results *because they keep
being wrong* (four wrong directional calls in a row, then one right):

**I expect the meter to return NOT-QUOTABLE on every theme, at 0 closed windows, and to stay
NOT-QUOTABLE for at least 9 months** — 3 months for the first window to close plus 6 monthly
observations. **Confidence 95%**, which is high only because this is a statement about arithmetic
and data depth, not about a market. The forecast that could be wrong is the one after it: **I
expect the first quotable verdicts, whenever they arrive, to be INSUFFICIENT for all 10 themes,
60/40** — the same arithmetic that gives `track_meter` 13.3% power at 60 months applies to a
weaker signal here.

## 9. Scope — what this run may and may not touch

* **NEW FILES ONLY**, plus read-only imports. `scripts/theme_health.py` and its test.
* `valuation/edge/**` is **imported and never edited** (`_spearman`, `track_meter.boundary`).
* Nothing reaches a public surface. This is owner-side Edge Lab instrumentation.
* Per RUN_RULES rule 9 the artifact stores **per-date, per-theme rows**, not only the summary.

## 10. What would make this pre-registration void

Any of: changing the horizon; lowering `sigma`; loosening a §7 floor; dropping the Bonferroni
correction; measuring on synthetic rows; or re-defining the IC away from the panel's `_spearman`.
Each of those makes crossing easier or the comparison less like-for-like. **Tightening any of them
is permitted and must be recorded** — a stricter rule cannot reach the harmful error, which here
is telling Don a theme is fine, or broken, on evidence that cannot support either.
