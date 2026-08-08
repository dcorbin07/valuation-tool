# PRE-REGISTRATION — Session 9, the selection rule on X8's cross-country data

**Written and committed BEFORE any arm return, correlation or count was computed.** This is an
addendum to `HANDOFF_edge_audit.md` SESSION 8 §2, which fixed the design; it settles the two
operational choices §2 left open, and nothing else. Where the two disagree, §2 wins.

## The question

Session 7's leave-one-out selection used a decide-half **argmax**, which picked `momentum` and
`capital_discipline` — both of which flip sign across halves — while `quality`, stable on both
halves, was never selected. Is a **stability-first** rule better than the incumbent argmax?
Session 8 proved this is not answerable on the Sharadar panel (one panel = one draw; a paired
sign test at n = 1 has a minimum achievable p of 0.50). It is answerable on 16 held-out
countries.

## Fixed by Session 8 §2, restated so this file stands alone

- **Decide set:** `usa` only. **Measure set:** 15 developed-European countries + `jpn` = **16**,
  none touched during selection.
- **Arms:** 5 leave-one-out arms — `value`, `quality`, `momentum`, `size`, `investment`. Only
  5 of Valquo's 7 themes map to JKP; `insider` and `institutional` have no analogue and are out
  of scope. Say so whenever this is quoted.
- **Arm definition:** `Δ_arm(t) = mean of the 4 remaining themes − mean of all 5`, per month.
- **Rule A (incumbent):** split `usa` in half by date; select `argmax` of the mean of the two
  half-means.
- **Rule B (stability):** among arms whose Δ has the **same sign in both `usa` halves**, select
  the largest. If none qualifies, Rule B **abstains** — recorded as an outcome, not a failure.
- **Statistic:** per country, the paired difference `Δ(arm chosen by B) − Δ(arm chosen by A)`
  over that country's full monthly history.
- **Verdict:** one-sided **sign test**. Ambiguous is a NULL (RUN_RULES A6).
- **Trial cost:** 5 arms → equity `N` 116 → 121. Logged to `RESEARCH_LOG.md` when run.

## THE TWO CHOICES THIS FILE COMMITS

### 1. Which correlation calibrates the bar — committed: the MAXIMUM over all ten arm-pairs

The 16 countries are not independent, so 12/16 (exact one-sided α 3.84%) is a floor.
`valuation/edge/cross_country.py` measures the co-movement `rho` and re-derives the critical
count by simulating the sign test's own null with that `rho` in it.

`rho` must be measured on an object that carries **no selection information**. There are
`C(5,2) = 10` ordered-irrelevant arm-pairs; the rules select exactly one of them. **Committed:
measure `rho` on all ten arm-pair difference panels and calibrate the bar from the LARGEST**,
reporting the median and the full range. The maximum is the conservative choice and is fixed in
advance precisely so that no post-hoc question — "was the selected pair unusually correlated?" —
can be answered after the fact in the result's favour.

- `critical_k` = smallest k with simulated `P(count ≥ k) ≤ 0.05` at that `rho`.
- **The bar may only move up.** If the calibration returns `critical_k < 12`, the threshold
  stays **12** — a measured lack of clustering cannot buy a weaker bar than the independent-
  countries arithmetic already implies.
- `clustering_measurable` is reported either way. If it is False, the design effect sits inside
  its own shuffled null and is quoted as a bound, never as a measurement (R3's standing rule).

### 2. If both rules select the same arm — committed: NO CONTRAST, and that is the result

Session 8 measured that on the Sharadar panel the two rules pick the same arm 90% of the time.
If they do so on `usa`, every paired difference is identically zero and the sign test is
vacuous. **Committed in advance: that outcome is reported as `NO CONTRAST` — not a NULL, not a
tie, and not an invitation to change either rule and re-run.** It is informative in its own
right: it would say the stability constraint does not bind on this data, which is the honest
answer to a differently-phrased question.

Ties in a country's paired difference (exactly 0.0) count **against** Rule B.

## The expectation, written down first (RUN_RULES A6)

**I expect a NULL, 65/35** — most likely because Rule B abstains or selects the same arm as
Rule A. Session 8's Monte Carlo found the rules reach different verdicts on only 5.1% of panels,
and there is no reason the JKP data should be kinder. Recorded because this project's
directional expectations have been wrong more often than right, and writing them down first is
the only thing that keeps that measurable.

## What this can and cannot answer — must travel with any quote

| | |
|---|---|
| **CAN** | whether a stability rule is **substantially** better: power **79.8%** against a rule better in 80% of countries, **63.0%** at 75% |
| **CANNOT** | whether it is **slightly** better: power **8.5%** at 55%. A NULL does **not** mean the rules are equivalent |
| **CANNOT** | say anything about `insider` or `institutional` — 2 of 7 themes do not map |
| **CANNOT** | corroborate Valquo's *magnitude*; X8 measured that gap at a factor of six |
| **CAVEAT** | JKP is **CC BY-NC 4.0, RESEARCH ONLY** — validates the model, can never ship |

The power figures above are computed at **independent** countries. If clustering is measurable
the true power is **lower** than these, and the CANNOT row gets stronger, never weaker.
