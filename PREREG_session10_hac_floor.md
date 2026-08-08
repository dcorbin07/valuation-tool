# PRE-COMMITMENT — Session 10, item 1: re-derive X7's long-short floor on the HAC statistic

**Written and committed BEFORE the sweep was launched.** This is a **calibration**, so what is
pre-committed is the *procedure* — seeds, draw count, panel, statistic, and what will be reported —
not a threshold. There is no hypothesis here and no pass/fail to game; the failure mode this file
guards against is choosing the seed count or the percentile after seeing which answer they give.

## The defect being closed

X7 calibrated the long-short floor at **2.14** by pushing 100 block-permuted placebo draws through
the real pipeline and taking the p95 of the **naive i.i.d.** *t*. R9 then measured Ljung–Box on the
long-short series, **rejected independence at p = 0.036** (lag-1 autocorrelation +0.189), and the
project's standing rule became "the Newey–West *t* is the number this project quotes." The shipped
statistic is therefore **HAC t 2.620**, and it has been compared against **2.14**, a bar derived for
a different estimator. `CLAUDE.md` has carried that as a known defect —
*"Comparing 2.620 to X7's calibrated floor of 2.14 is apples-to-oranges … Re-deriving it on the HAC
statistic is open."* This closes it.

## Procedure, fixed in advance

- **Panel:** `data/free_analysis/panel_corrected_69d.pkl` — the corrected 69-date panel,
  2009-01-15 → 2026-01-28, 113,945 rows, 8 themes.
- **Reproduction check, run BEFORE any draw and reported either way.** The unpermuted panel must
  reproduce the shipped run through the identical code path. **Already run:** `long_short_tstat`
  **2.8360640685** (record 2.83606), `long_short_tstat_nw` **2.6199121240** (R9's 2.620),
  `top_decile_alpha` **0.0717414233** (record 0.071741), `top_decile_alpha_tstat_nw` **4.3762304**
  (R9's 4.376), `pbo` **0.7333333** (record 0.73333), `adopt` **False**, 69 periods. **All match.**
- **Draws:** `n = 100`, **seeds 1000–1099** — X7's own seed block, unchanged.
- **Instrument:** `fundamental_panel.placebo_panel`, unchanged — within-date block permutation of
  the theme/`z_*` columns; `fwd_ret`, `marketcap`, `sector` untouched.
- **Costs:** measured (no `--no-costs`), so the sweep is a superset of X7's method rather than a
  cheaper variant.
- **The only change:** the recorder now also stores `long_short_tstat_nw`,
  `long_short_ljung_box_p`, `top_decile_alpha_tstat` and `top_decile_alpha_tstat_nw`. **These were
  computed by `quantile_backtest` on every draw of the original sweep and silently dropped by the
  writer** — no scoring logic is touched, which is why the naive floor must come back at 2.14.
- **The floor is the p95 of the null distribution**, the same estimator X7 used for every other
  calibrated bar. No other percentile will be substituted.

## What will be reported, whatever it says

1. The re-derived **HAC floor** (p95), with the null's median, max and the Monte Carlo error.
2. **The naive floor from the same sweep as a control.** If it does not come back at ≈2.14 the
   sweep is not comparable to X7's and the HAC floor will be reported as **not established**,
   with the discrepancy, rather than published over a broken control.
3. **Whether the shipped HAC t of 2.620 clears the re-derived floor.** *If it does not, that is the
   finding and it will be stated in one plain sentence with no softening* — the record has earned
   that treatment elsewhere and this bar gets no exception.
4. The rate at which pure noise clears **2.14 on the HAC statistic**, which measures the size of
   the apples-to-oranges error rather than establishing any new bar.
5. A calibrated floor for the **top-decile alpha HAC t** as a by-product, labelled as a by-product;
   it has never had one, and the sweep produces it for free.

## Trial cost

**Zero.** A calibration of an existing statistic on an existing panel searches nothing and
proposes no strategy. Equity `N` stays at **121**. `RESEARCH_LOG.md` gets one `infra` row for the
recorder change, consistent with how `SELRULE-GATE` was logged in session 9.
