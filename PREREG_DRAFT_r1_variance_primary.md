# PREREG DRAFT — R-1: THE VARIANCE-PRIMARY REGISTER
## Does inverse-vol construction reduce the book's volatility, at no material cost in alpha?
## The first register in this project's history whose primary metric is not a return.

**DRAFT, Frontier Scout lane, 2026-08-24.** Commit ALONE, markdown only, a strict ancestor of
every measurement commit; counters re-read first. **Trials: 1, equity** (~242 → 243 at this
writing; hurdle 3.3133 → 3.3145). Companion: `RISK_PRIMARY_MAP.md`, whose §1 arithmetic is the
reason this register exists in this shape and not as a Sharpe gate.

## 0. Why this is not `S13` re-run — the distinction the register lives or dies on

**Tags: [`S13` REJECTED-ON-ALPHA · `S5`/`S6`/`S24`/`S27` the weighting family · `MB8`
(non-inferiority's registered shape) · `S14` (net-of-cost gating, the record's one adoption)]**

`S13` ran an inverse-vol construction, **improved Sharpe 0.5866 → 0.6261 with drawdown flat**,
and was rejected for losing 1.76pp of alpha — against a gate its own row says it could not move
(*"the decile MEMBERSHIP is unchanged and the long-short leg is unchanged BY CONSTRUCTION. Its
t margin is therefore recorded N/A"*). **This register does not re-run that arm to get a nicer
answer.** It asks a **different primary question on a different statistic with a different
verdict rule**, and it pre-commits that the alpha result may not improve — alpha appears here
only as a **non-inferiority** leg that can *veto*, never as the thing being chased.

The distinction from the weighting graveyard is equally explicit: every corpse there
re-weighted to chase **return** and was gated on return. This targets **variance**, gates on
variance, and reports Sharpe as a derived quantity that decides nothing.

## 1. Arms (fixed; no sweep, no grid)

* **Base:** the shipped top-decile book under deployed weights — imported, never re-derived.
* **Arm A:** inverse-volatility weights within the top decile (each name's weight ∝ 1/σ, σ =
  trailing 252-session realised vol at the rebalance, PIT), **normalised to full investment**.
* **Arm B (declared secondary, same trial):** equal-risk-contribution ("risk parity") weights
  on the same names using the same σ and a shrunk correlation matrix (Ledoit–Wolf, shrinkage
  fixed at the published default and **never tuned**).
* **Membership is identical across all three by construction** — this register cannot move the
  decile, and it may never report a long-short figure (`S13`'s standing prohibition travels).

## 2. Primary statistic, bar, and the null — and why `X7` is not used

**Primary: the paired log variance ratio** `ln(σ²_arm / σ²_base)` on the 69 quarterly book
returns, declared sign **NEGATIVE** (the construction exists to reduce variance).

**Test: Pitman–Morgan** (paired variance equality via `corr(x+y, x−y)`), with a **date-block
bootstrap CI** (`R3`'s shipped machinery, block length as R3 uses) so the panel's
autocorrelation is carried rather than assumed away.

**Bar:** the arm must clear **|t| > 3.3133** (the honest hurdle at run-time `N`, re-read) **and
agree in sign across both halves**. Ambiguous against its own threshold is NULL (`RUN_RULES` A-6).

**`X7`'s placebo machinery is deliberately NOT used, and the register states why in advance**
(the reasoning is `RISK_PRIMARY_MAP.md` §2): `placebo_panel` permutes the signal away, so under
that null both arms collapse to the same random book and the contrast under test does not exist
in the null being generated; and `MB21` measured the placebo at **zero persistence** against a
real composite at **0.5677**, so a variance statistic computed on it mis-states the volatility
of a persistent book. **Variance has an analytic null; alpha did not. That is the whole reason
`X7` exists and the whole reason it does not apply here.**

**Declared secondary, no verdict:** a **weight-scramble null** — random weight vectors within
the decile preserving Arm A's concentration profile — reported as a sanity distribution to show
the measured reduction is not what any arbitrary re-weighting achieves. If the lane prefers, it
ships as its own instrument first; it is not required for the primary.

## 3. The alpha non-inferiority leg (gating, `MB8`'s shape)

Top-decile alpha must not fall by more than **`X7`'s calibrated margin 1.8629pp**
(`MA19`'s figure at `N` = 224 — **re-derive or re-confirm at run-time `N` per `MB31`, and
state which**). **A variance reduction bought with more alpha than that is a trade, not a free
lunch, and this register may not make that trade** — the arm is REJECTED regardless of the
variance result. `S13` lost 1.76pp, which sits *inside* that margin: the register notes this
in advance so the leg is understood as genuinely binding rather than decorative.

## 4. Power, both vocabularies, printed BEFORE the verdict is read (`RUN_RULES` A-11)

`SE(ln σ²-ratio) ≈ √(4(1−ρ²)/n)`, `n` = 69, ρ = the **measured** base-vs-arm return correlation
(a descriptive input, computed and printed in the controls pass, never assumed):

| ρ | SE | detectable vol reduction @ 3.3133 — 50% / 80% power |
|---|---|---|
| 0.95 | 0.0752 | 11.7% / **14.5%** |
| 0.97 | 0.0585 | 9.2% / **11.4%** |
| 0.99 | 0.0340 | 5.5% / **6.8%** |

The executor prints the exact line from `power_gate.state()` on the measured ρ. **If the
realised 80%-power MDE exceeds a 20% vol reduction, the design is UNPOWERED-BY-CONSTRUCTION and
the register stops before scoring** — a pre-outcome kill, `MB15`'s pattern.

**And the sentence that must travel with any null:** *this design can see a ~10% volatility
change and cannot see a Sharpe change; a NULL here means "no variance reduction of that size",
never "no risk benefit".*

## 5. Controls (own pass, read before the arm — `O10`'s process defect, not repeated)

**C1** membership identity: the arm's holdings reproduce the base's on 69 of 69 dates, count-gated
(`MB21`'s C1 idiom). **C2** ρ measured and printed (the power input). **C3** weights sum to 1 and
no name exceeds the contract's 8% cap. **C4** PIT: σ uses only trailing data; an AST test asserts
no forward column is loadable (`MB18`'s pin). **C5** Sharpe and max-drawdown computed and
reported **with CIs, carrying the words "reported, not gating"** — the register fails its own
review if either appears in a verdict sentence.

## 6. Void conditions

1. Any verdict resting on Sharpe, drawdown, or the long-short leg.
2. Sweeping the vol lookback, the shrinkage constant, or the weighting exponent (that is a grid
   and a different price — `MA58-SEAS`'s C-DEPTH lesson).
3. Using `X7`'s placebo as the primary null (§2).
4. Adopting anything: this register measures. Adoption is a vintage event and Don's decision.
5. Reading the arm before C1–C5 are banked and green.

## 7. Prior and expectations, written before the run

Prior: **~35% CONFIRMED** — deliberately the highest prior this lane has written, because the
mechanism is arithmetic rather than behavioural (inverse-vol weighting reduces portfolio
variance unless the vol estimate is pure noise) and because `S13`'s Sharpe-up/alpha-down
pattern is only possible if vol fell. **The genuine uncertainty is the alpha leg, not the
variance leg.** Expectations: (1) the variance leg clears — 70/30; (2) the alpha
non-inferiority leg is what decides the register — 65/35; (3) Arm B (risk parity) reduces
variance more than Arm A but costs more alpha — 55/45; (4) measured ρ lands ≥ 0.95 — 75/25;
(5) at least one number here contradicts this list — 60/40.

## 8. What this register does NOT do

It does not adopt, does not touch the composite, does not move the shipped book, does not
license a Sharpe claim anywhere in the product (`V3` still forbids per-name precision and
`MB38`'s vocabulary still governs any public sentence), and does not re-open `S13`, whose
alpha verdict stands on its own terms.
