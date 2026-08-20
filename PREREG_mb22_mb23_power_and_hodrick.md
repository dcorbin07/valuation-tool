# PREREG — MB22 (required-n power gate) + MB23 (Hodrick 1B cross-check)

**Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every measurement
commit.** Both items are INFRASTRUCTURE and charge **1 trial each to the `infra` domain**
(V1 / M2 / M6 / HACFLOOR / X7RECON precedent). **Infra `N` gates no published claim.**

Two items, one register, because they are the two halves of one question — *how much evidence
does a design actually carry?* — and because MB23's cross-check needs MB22's language to state
its own result.

**Live counters re-read from `research_log.detail()` after merging `origin/main`, not quoted
from `CLAUDE.md`:** equity **234**, options **304**, infra **15**. Infra goes **15 -> 17**.
Equity and options are **untouched**.

---

## 0. Blindness, stated exactly

**Neither item is blind, and pretending otherwise would be worse than saying so.**

* **MB22** is arithmetic. There is no outcome to be blind to: `((sqrt(2 ln N) + z)/effect)^2`
  returns what it returns. Its "result" is a set of positive controls, and I have READ the
  numbers those controls must reproduce (TIDEMARK's `POWER_GATE.md`, and this project's own
  recorded MDEs) before writing the code. That is the *point* of a positive control — you must
  know the right answer in advance — but it means MB22's controls are verification, never
  discovery.
* **MB23's estimator verification** is likewise against **published** numbers (Wei-Wright Table
  1), read before implementation, deliberately: `tests/test_hac.py` in TIDEMARK records that
  verifying an estimator against one's own expectation is exactly the failure mode that produced
  a wrong Hodrick implementation returning `t ~ 0.3` at every horizon.
* **MB23's cross-check IS blind in the only way that matters**, and this is the part the
  threshold below binds. The two shipped H=63 Newey-West statistics are already public
  (long-short **2.6199121240414884**, top-decile alpha **4.376230427940328**) and I have read
  them. **What is NOT known is what the Hodrick estimator returns on the same series**, because
  no Hodrick estimator exists in this repository. The bar is set below before that number is
  computed.

---

## 1. MB22 — the required-n / minimum-detectable-effect gate

### 1.1 What is being ported, and what Valquo already has

Valquo already has `statistics.effective_n(n, rho)` (an AR(1) closed form) and, in the options
lane, `options_stats.effective_n(rows, block)` (a design effect scored against a **shuffled
null** — R3's rule that a raw design effect is never quoted without its null is already learned
here). What Valquo does **not** have is the last step: the conversion from available
observations to a **required-n bar**, and its inverse, the **minimum detectable effect**.

Shipped as `valuation/edge/power_gate.py`:

```
crit                = statistics.hlz_hurdle(n_trials)          # DELEGATED, never re-derived
required_n(effect)  = ((crit + z_power) / effect) ** 2
mde(available_n)    = (crit + z_power) / sqrt(available_n)     # the same identity, inverted
mde_from_se(se)     = crit * se                                # this project's own form
mde_from_observed   = crit * effect / |t|                      # S19 / MA33's form
```

`hlz_hurdle` is **imported**, not re-implemented. MA5 found this project carrying four copies of
`sqrt(2 ln N)`, of which only one saw M1's floor, and shipped a test that fails if a second
appears anywhere under `valuation/`. **A fifth copy here would break that test and deserve to.**

### 1.2 Positive controls, all fixed before the code exists

**External — TIDEMARK, whose own gate reproduces its charter's printed power table:**

| control | expected |
|---|---|
| `required_n` at crit **1.96**, IR 0.20 | **196** (printed) |
| `required_n` at crit **1.96**, IR 0.30 | **87** (printed) |
| `required_n` at crit **1.96**, IR 0.15 | **348** (printed) |
| `hlz_hurdle(66)` | **2.8947** |
| `required_n` at N=66, IR 0.30 | **155.0** |
| `mde` at N=66, 82.3 available years | **0.41** |
| `mde` at N=66, 45.8 available years | **0.55** |
| `mde` at N=66, 25.2 available years | **0.74** |
| `mde` at N=66, 52.4 available years | **0.52** |

**Internal — this project's own hand-computed MDEs, which the ported function must reproduce
without being told the answer.** These matter more than the external ones, because they are the
evidence that the ported instrument measures the quantity Valquo already means by "MDE":

| register | inputs on record | expected MDE |
|---|---|---|
| `S19` A1 (via `MA33`) | incremental IC 0.012202150018043164, t 1.1876022080477582, crit 2.0 | **+0.020549** |
| `V2G` | paired HAC se 0.9354 pp, crit 2.0 | **1.8708 pp** |
| `V6` A1 | implied se 2.0885 pp, crit 2.0 | **+4.177 pp** |

**And the identity that makes the two routes one function:** `mde_from_se(effect/|t|, crit)`
must equal `mde_from_observed(effect, t, crit)` **exactly**, for every input. If they can
disagree, there are two definitions of MDE in this repository and MA5's whole finding applies
again.

### 1.3 The deviation ported from TIDEMARK, and it is a REFUSAL to port something

`POWER_GATE.md` 5.1 records that **the validation its own pre-registration asked for could not
be run**: it asked that the `n_overlapping / deff` bridge reproduce a charter column of
"independent n", and that column turns out to be exactly `n/h` — the count of **non-overlapping
windows** — a different quantity reached by an unrelated route, sitting in the adjacent column
of the same table.

**So the port ships both routes and forbids using either to validate the other.** They are
reported side by side; agreement between them is **corroboration**, never validation. A
docstring saying so is not enough, so the two routes are separate functions with separate names
and a caller has to choose one deliberately.

### 1.4 What MB22 does NOT ship, and why — MB30 / MA21 bind

**No repository-wide check that greps every `PREREG_*.md` for an MDE.** There are ~68 of them
and essentially none states one in the form this function computes, so such a check would fire
on ~68 legitimate historical registers on its first run and be switched off inside a week. That
is **MA21's** precedent exactly: it declined a blank-verdict warning that would have fired on 41
legitimate ledger rows, and this record already calls that failure mode *"the cry-wolf failure
`MA19` already refused once."*

What ships instead is the same substitution MA21 made: **a rule for what happens NEXT**
(`RUN_RULES.md` PART A rule 11) plus **a library the next register calls**, and tests that pin
the arithmetic rather than policing the corpus.

---

## 2. MB23 — Hodrick (1992) 1B as a cross-check

### 2.1 What is ported

`valuation/edge/hodrick.py`, written from the published formula:

```
r_{t+1} + ... + r_{t+h}  =  a  +  b * x_t  +  e_{t+h}

Var(a,b)' = (SUM xt xt')^-1 (SUM w_{t+1} w_{t+1}') (SUM xt xt')^-1
  where w_{t+1} = (r_{t+1} - rbar) * SUM_{i=0}^{h-1} x_{t-i}
```

**The residual is the ONE-PERIOD one at a single date; the REGRESSOR is summed over the h most
recent dates.** TIDEMARK's own first implementation had those the other way round — it summed
the regressors while keeping the h-period residual — and returned `t ~ 0.3` at every horizon
against a bootstrap `p ~ 0.018`, i.e. it silently produced "no evidence". That failure mode is
why the verification below is against printed numbers and an algebraic identity, never against
my own expectation.

**1B is valid ONLY under the null b = 0.** Wei-Wright's Table 1 measures the degradation
directly: coverage falls to 0.44 at h=48 when the true b is 0.1. So the ported function is
documented as a **test against zero** and must not be used to put an interval around a non-zero
coefficient.

### 2.2 The estimator verification bar, committed now

Against **Wei-Wright (2009), FEDS 2009-27, Table 1** under their fully specified DGP
(`T = 500`, nominal coverage 0.95, `h` in 12/24/36/48):

* **BAR: at `alpha = 0` — the only case 1B is valid for — the reproduced coverage must sit
  within 0.03 (absolute) of every printed cell**, at 400 draws per cell, seed fixed in the
  source. TIDEMARK reports max abs deviation 0.016 across 23 cells at higher rep counts; 0.03 is
  the allowance for Monte-Carlo error at 400 draws and is fixed here **before** the run.
* **Plus one exact algebraic identity, no tolerance and no simulation:** at `h = 1` the summed
  regressor window is a single term, so 1B collapses to the heteroskedasticity-robust (White)
  sandwich computed with residuals `(r - rbar)`. Checked to `rtol = 1e-12`.
* **Plus one leakage pin:** changing `r_t` alone must not move `y_t`. An off-by-one here makes
  the regression partly contemporaneous and every t-statistic built on it meaningless.

**One reading has to be established rather than assumed, and it is recorded because getting it
wrong produces a plausible-looking failure:** Table 1's column headings print "beta" but the
values are the DGP's **alpha**, the ONE-period slope. The implied long-horizon slope is
`beta = alpha (1 - phi^h)/(1 - phi)`. **That reading is settled by the DGP's own population R2
row, which uses no estimator at all**, so it is established independently of the thing being
tested.

### 2.3 THE CROSS-CHECK, and its pre-committed threshold

**The object.** Valquo's shipped H=63 statistics are `hac_tstat(series, lag=1)` — Newey-West
t-statistics of the **mean** of a 69-element series of non-overlapping 63-day period returns.
They are mean tests, not slope regressions. **This is stated here, before the measurement,
because it is the reason the audit predicts agreement:** at H=63 the horizon equals the
rebalance interval, so there is no overlap for a HAC correction to correct beyond the small
lag-1 autocorrelation the series carries.

So the cross-check runs Hodrick's construction **specialised to a constant regressor** — the
same sandwich, the same `w_{t+1} = (r_{t+1} - rbar) * SUM_{i=0}^{h-1} x_{t-i}` with `x == 1` —
against the shipped Newey-West statistic on the identical series. Both estimate the variance of
the same quantity. Anything else would be comparing two different regressions and calling the
difference an estimator disagreement.

**THE BAR, fixed before any Hodrick number exists:**

> **Agreement is `|t_hodrick - t_newey_west| / |t_newey_west| <= 0.10`, required on BOTH shipped
> H=63 statistics — the long-short spread AND the top-decile alpha. If both agree, the port is
> recorded VALIDATED and NO CLAIM MOVES. If either exceeds 0.10, the port is recorded DISAGREES
> and the disagreement is reported; it still moves no claim in this session, because moving one
> would require MB21's persistence-preserving null, which is not built here.**

Both branches move nothing. That is deliberate and is the honest shape of a cross-check: this
register can *validate* an instrument or *flag* one, and cannot re-score a result either way.

**The corrected criterion is ported, NOT the committed one.** `POWER_GATE.md` 5.2 records that
TIDEMARK's own pre-registered cross-check criterion was misspecified — it asked for the 97.5th
percentile of `|t_Hodrick|` to sit within 10% of 1.96, which is the wrong quantile (1.96 is the
97.5th of the **signed** t, the 95th of `|t|`), and **the rule fails on the verified case**:
`Var(t_H) = 0.96` and rejection 0.046 against a nominal 0.05, both correct, while
`q97.5|t_H| = 2.20`. **A port that copies the criterion instead of the correction ships a rule
that flags known-good cases.** The corrected statistic — rejection rate against its nominal 0.05
— is what ships, and the misspecified one is computed and printed beside it, marked, with the
positive control that exposes it.

### 2.4 The h-sweep is a DIAGNOSTIC and carries NO verdict

Beyond `h = 1` the two estimators are expected to diverge, and where they diverge is exactly
`S22`'s territory (H = 126 ... 504, HAC lag running to 7, overlap severe). The sweep is run and
reported **because refusing to look would be worse**, and it is labelled with no verdict, for a
reason fixed here in advance: **`MB21` measures that `S22`'s null is mis-specified in a way that
compounds with horizon**, and re-scoring `S22` against a better SE while leaving its null
unfixed would change one half of a comparison. `MB23` says so and stops.

**Void condition: quoting any h > 1 cell of this sweep as a verdict about `S22` voids this
register.**

---

## 3. Void conditions

1. Re-implementing `sqrt(2 ln N)` anywhere rather than calling `statistics.hlz_hurdle` (MA5).
2. Validating either `available_independent_n` route against the other (POWER_GATE 5.1).
3. Shipping the misspecified `q97.5` criterion as the cross-check's decision rule (POWER_GATE 5.2).
4. Moving, re-scoring or re-opening ANY landed claim on the strength of either item.
5. Quoting an `h > 1` cell of MB23's sweep as a verdict about `S22` (see 2.4).
6. Adding a repo-wide check that fires on existing registers (MB30 / MA21).
7. Charging these to `equity` or `options`. Both are `infra`.

## 4. Trial charge

**infra 15 -> 17.** One per item. Equity stays **234**, options stays **304**.
`BACKTEST_RESULTS.json` needs no re-run: infra `N` enters no published bar, and per `MA21` the
artifact may legitimately LAG the log.

## 5. Expectations, written before the run, to be scored afterwards

1. **The H=63 cross-check AGREES on both statistics** — 85/15. The audit predicts it, and the
   mechanism (no overlap at H=63) is structural rather than empirical.
2. **The Hodrick t will land very close to the NAIVE t rather than between naive and HAC** —
   70/30. At `h = 1` with a constant regressor the sandwich has almost nothing to correct.
3. **The long-short statistic will be the LOOSER of the two comparisons** — 60/40. Its lag-1
   autocorrelation is 0.189 against the alpha series' 0.081, so the HAC correction is larger
   there and a Hodrick estimator that ignores it should sit further away.
4. **The h-sweep diverges monotonically with h** — 75/25.
5. **All three internal MDE controls reproduce** — 90/10. If one does not, this project has two
   definitions of MDE and that is a finding.
6. **At least one of the ported gate's numbers will contradict something I expected** — 60/40,
   on this record's own base rate.

## 6. What this register does NOT do, named so it is not mistaken for done

* **It does not run `MB21`.** No persistence-preserving null is built, `S22`'s null is not
  replaced, and `S22`'s verdict does not move. MB23 is `MB21`'s companion instrument and the
  audit says so; shipping the instrument is not running the item.
* **It does not re-score any horizon result.** Not `S22`, not `R1`, not the headline.
* **It does not import any TIDEMARK data.** `MB24` marks data flow out of scope; only the
  *method* crosses, re-derived from the published sources named above.
* **It does not add an MDE to any existing register.** Rule 11 binds future ones.
* **It does not build a required-n gate for the OPTIONS lane's clustered statistics.** The
  design-effect route exists there (`options_stats.effective_n`); wiring it into the required-n
  arithmetic is a further item.
