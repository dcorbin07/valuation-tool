# PRE-REGISTRATION — V2G: what the three dead live themes cost in return

Committed **alone, before `scripts/live_theme_cost.py` existed and before any arm was scored.**
Edge lane, 2026-08-10. Ledger row `V2G`.

## 1. The question, and who asked it

The greeks lane measured (`HANDOFF_live_data_bugs.md` Part 12.7, 500 served rows) that three of the
seven weighted themes reach **no live score**:

| theme | live state | deployed weight |
|---|---|---|
| `insider` | 500/500 non-null but **one distinct value** — constant, so `zscore` → all-NaN | 0.125 |
| `capital_discipline` | **0/500 non-null** — absent | 0.125 |
| `institutional` | **0/500 non-null** — absent | 0.125 |

`WEIGHTS_ESTABLISHED` has seven non-zero themes at 0.125 (sum 0.875), so **0.375 of 0.875 — 42.9%
of the weight mass — reaches no live score**, and the live hot list is a **four-theme** book
(`value`, `quality`, `momentum`, `size`) wearing the weights of a seven-theme one.

That lane explicitly declined to price it: *"No claim is made here about how much this costs in
return. That is a backtest question (score the panel with those three themes removed) and it is
not this lane's, and not this run's."* This register is that backtest question.

**The decision it feeds:** whether building live sources for the dead themes is the project's
highest-value work or a nice-to-have.

## 2. The two arms — fixed now, and there is nothing to select

| arm | themes | weights |
|---|---|---|
| **A7** — deployed | value, quality, momentum, insider, capital_discipline, size, institutional | 0.125 each |
| **B4** — the live book | value, quality, momentum, size | 0.125 each |

Both are scored by the **shipped** `quantile_backtest` → `composite_from_frame` → `composite`, at
`n_q=10`, `horizon=63`, on the corrected panel `data/free_analysis/panel_corrected_69d.pkl`
(**2,531 names, 69 dates, 2009-01-15 → 2026-01-28, 113,945 rows** — verified before this file was
written, and the `institutional` 71.72% / `insider` 83.08% coverages match CLAUDE.md's corrected
figures).

**There is no selection step anywhere in this design.** Two pre-specified arms, one comparison. So
no decide/measure split is required to make the comparison honest, and none is performed. "Both
split directions" below is a **stability check**, not a selection gate.

## 3. Why B4 *is* the live book, not merely a model of it — and the control that proves it

`fundamental_panel.composite` and `cross_sectional.composite_score` are the same arithmetic:
renormalise by the **present-weight mass** (`denom = (present * w).sum(axis=1)`). Since B7 landed
there is one composite in the tree. Therefore a theme that is **absent** (all-NaN) or **constant**
(z-scores to all-NaN) drops out of both numerator and denominator identically — which is exactly
what dropping it from `weights` does.

So the restriction needs **no new scoring code**, and that claim is checkable rather than asserted:

* **C1 — ABSENCE EQUIVALENCE.** Scoring the **A7** weight vector on a panel whose three dead theme
  columns are set to NaN must equal the **B4** arm's composite **to 1e-12, name for name**.
* **C2 — CONSTANCY EQUIVALENCE (the live case exactly).** Scoring the **A7** weight vector on a
  panel where `insider` is set to a **constant** and the other two are NaN must equal **B4**
  likewise. This is the live product's actual condition, and it is the one that would break if
  `zscore` did not return all-NaN on a zero-variance column.

If C1 or C2 fails, the arms are not what this register says they are and **no verdict is
reported** — the run becomes a defect report.

**A consequence I commit to reporting whichever way it falls:** A7 can rank a name that has only
`institutional`; B4 cannot. The two arms may therefore score **different numbers of names**, and a
date could in principle be dropped by one arm and not the other. Per-arm scored-name counts and
the per-date alignment are reported, and all paired statistics are computed on the **intersection
of dates**, stated as a count.

## 4. Statistics and bars — committed before any arm runs

**Primary object: `top_decile_alpha`** (the number on the front of the product) and the
**long-short HAC t** (per R9, HAC is the statistic this project quotes; the naive t is a
diagnostic only).

**(a) The cost.** `Δalpha = alpha(B4) − alpha(A7)`. Negative = the live book is worse.
Bar: X7's **calibrated top-decile alpha margin of 1.95pp**.

**(b) Paired significance.** Because both arms are scored on the same dates and largely the same
names, the per-period difference `d_t = alpha_series(B4)[t] − alpha_series(A7)[t]` cancels the
market move that dominates each level. HAC(lag 1) t on `d_t` is the significance statistic.

> **Stated plainly: no calibrated floor exists for a paired within-panel difference.** X7 and
> session 10 calibrated *level* statistics (LS t, alpha t) against a shuffled-signal null; neither
> calibrates a difference between two overlapping arms. I therefore use the **conventional |t| ≥
> 2.0** here and **label it uncalibrated every time it is quoted**. I do not invent a floor, and I
> do not silently reuse a level floor for a difference — that is precisely the naive-vs-HAC
> mismatch session 10 had to close.

**(c) The question that matters most, reported separately: does B4 stand on its own?**
Against the calibrated absolute floors for **this** panel:

| statistic | calibrated floor | source |
|---|---|---|
| long-short HAC t | **2.2837** | session 10 placebo p95 |
| top-decile alpha HAC t | **2.2913** | session 10 placebo p95 |
| long-short naive t (diagnostic) | 2.1437 | X7 / session 10 |

B4 is the book **users actually receive**. If it clears, the live product has a demonstrable edge
without the three themes. If it does not, the live product is shipping a book whose edge is not
demonstrable on its own panel — a materially worse finding than a mere alpha gap, and it is
reported as such.

**C3 — ARE THE FLOORS STILL THE FLOORS AT `N` = 131?** The published floors were measured at
`N` = 121 and re-verified at `N` = 129 (20 adopters at both). `N` moves individual draws through
the CPCV adopt gate (session 12). My arms never call CPCV, so the coupling cannot touch them — but
it can move the floor I compare against. `data/free_analysis/X7_RECONCILE.json` banks every draw's
`(margin, se)`, so adoption at any `N` is arithmetic: I recompute the adopter count at 131 and
report whether the floors still stand. **Zero trials — a calibration searches nothing.**

## 5. Decision rule — fixed now

| condition | verdict |
|---|---|
| `Δalpha ≤ −1.95pp` **AND** paired HAC \|t\| ≥ 2.0 | **MATERIAL** — building the live sources is high-value |
| `Δalpha > −1.95pp` **AND** paired HAC \|t\| < 2.0 | **IMMATERIAL** — a nice-to-have |
| anything else (the two disagree) | **NULL — ambiguous**, both halves reported, no recommendation |

Per RUN_RULES A6, **ambiguous is a NULL** and is reported as one. A near miss is a null.

## 6. Both split directions — a stability check, not a gate

The same two arms are re-scored on the **early half** and the **late half** of the 69 dates
(dates sorted; first 34 / last 35, the split stated before it is run). Both directions are
reported whatever they say. **No arm is selected on one half and measured on the other, because
nothing is being selected.** A sign flip between halves does not overturn the full-sample verdict
but is reported prominently — session 7 found four of seven LOO arms change sign between halves,
so a stable full-sample ablation figure is not to be assumed.

## 7. Exploratory decomposition — NO VERDICT, and I commit to that now

To make the answer actionable ("which source do we build first?") I additionally score three
six-theme arms, each dropping exactly one dead theme from A7:

* A7 − `insider` &nbsp; A7 − `capital_discipline` &nbsp; A7 − `institutional`

**These carry NO verdict and may not be quoted as findings.** Session 7 established the rule on
this exact panel: *"Do not quote a full-sample ablation arm as a finding"* — four of seven LOO arms
changed sign between halves. They are reported with both halves beside them so their instability is
visible, and they exist to rank build priority, not to decide anything.

## 8. What I expect — written first, because this project's expectations keep being wrong

| prediction | confidence |
|---|---|
| **MATERIAL** (the restriction costs ≥ 1.95pp and is significant) | **55 / 45** — genuinely uncertain |
| B4 still clears the calibrated LS HAC floor of 2.2837 | 50 / 50 |
| `institutional` is the single most costly of the three to lose | 55 / 45 |
| dropping `insider` alone **helps or is neutral** (its panel IC is −0.24) | 70 / 30 |
| at least one of the three decomposition arms flips sign between halves | 65 / 35 |

**The two considerations that pull opposite ways, recorded so the prediction cannot be
retro-fitted.** Against a large cost: B4 retains `size` — which X3 found carries the composite's
*entire* statistical significance despite the worst theme IC — and `quality`, the strongest theme,
and LOO found `size` the worst arm to drop in both halves independently. For a large cost:
`capital_discipline` has the second-strongest IC (+2.76) and is one of only two themes clearing
X7's 2.71 bar. **X3's actual lesson is that theme IC does not predict marginal contribution at
all**, so neither argument is worth much, which is why this is 55/45 and not 80/20.

## 9. Trial cost — paid as registered

**Four new arms** (B4, and the three exploratory six-theme arms), charged to the **equity** domain:
**`N` 131 → 135.** A7 is the incumbent and is already counted. The halves are the **same arms on
subsets, not new hypotheses**, and are not charged — the precedent is session 7's LOO, which
charged 7 for 7 arms while measuring every one in both directions.

`BACKTEST_RESULTS.json` is re-run from a clean tree afterwards so the artifact's `n_trials` and
Deflated Sharpe match the register rather than going stale on the denominator.

## 10. What voids this pre-registration

Changing an arm's definition, a bar, the decision rule (§5) or the split point (§6) after seeing a
number. Adding an arm after seeing a result — the decomposition set is **fixed at three** here and
now. Tightening is permitted and must be recorded with its reason; loosening is not. Re-running the
report is free and is not a new trial.

**What would make this register a failure rather than a result:** reporting a verdict when C1 or C2
failed; quoting an exploratory decomposition arm as a finding; comparing the paired difference
against a level floor; or letting `Δalpha` be reported without the two halves beside it.
