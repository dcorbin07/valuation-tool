# PRE-REGISTRATION — S5, S6, S13, S24, S27: five alternative weighting/combination schemes

**One register, five arms, committed before any arm has been scored.** Written after a premise
check against the code (§1), reported here in full because **three of the five propose behaviour
that is already shipped, in whole or in part**. No arm's alpha, *t* or gate result exists at this
commit.

All five are `src=auto` ledger rows — *"a lead, not a fact"*. S21 is the precedent: an `auto` row
proposed behaviour the code already shipped, and the register caught it only because the premise
was checked against the code rather than against the item text.

---

## 0. THE STANDING RESULT THAT FRAMES ALL FIVE

This is not a neutral prior and the register will not pretend otherwise. Three measured facts
from the record, stated before any arm runs:

1. **CPCV HAS DECLINED TO ADOPT ANY WEIGHTING, EVERY TIME IT HAS BEEN ASKED.** Eight schemes,
   several occasions, and `cpcv.adopt` reads **`false`** in the canonical artifact today.
2. **THE ML TREE COMBINER DID NOT MERELY FAIL — IT REVERSED OUT OF SAMPLE.** Monotonicity
   **+0.382** and **+0.842** on the two measure halves (negative is well-ordered), i.e. its top
   decile underperformed its bottom decile, while all 16 grid × direction cells had a *positive*
   decide-half CPCV out-of-sample IC. Selection on this panel can generalise **backwards**.
3. **WEIGHT TUNING HAS BEEN NOISE-CHASING EVERY TIME IT WAS TRIED:** the parameter search's
   **+8.43%/yr in-search → −0.04%/yr on the locked hold-out.**

**So the honest prior on all five arms is failure**, and §7 states that per arm before running.
The reason to run them anyway is that "we expect these to fail" is not a measurement, five
schemes have never been put through one common instrument, and three of the five turn out to be
partly shipped already — which is worth knowing regardless of the verdicts.

---

## 1. PREMISE CHECK — three of the five are already shipped, in whole or in part

**(a) S27 IS ALREADY SHIPPED, AT THE AUDIT'S OWN MIDDLE HALF-LIFE.** The item says *"Every IC is
a full-sample median. Every weight is fixed."* The first half is true only of the **reported
diagnostics**. The **weight-selection path already weights recent observations more**:
`_theme_ic_stats` (`fundamental_panel.py:2135-2145`) computes
`wts = 0.5 ** (days_ago / halflife_days)` — an exponentially-weighted IC — and
`halflife_days=1260` (**≈5 years**) is the default of `_weighted_optimize`, `walk_forward` **and
`cpcv_validate`**. The audit proposes half-lives of *"3, 5 and 10 years"*; **5 is the shipped
default.** So S27's remaining testable content is only whether a *different* half-life beats the
shipped one, and the arm is defined that way in §3.

**(b) S5's SHRINKAGE IS HALF-SHIPPED, AND THE SHIPPED HALF HAS ALREADY BEEN REJECTED.**
`_weight_schemes` contains **`ic-shrunk-50`** — `0.5 × ic_proportional + 0.5 × equal_weight` —
which is a shrinkage estimator toward the equal-weight prior with the intensity **fixed at 50%**.
It is one of the eight schemes CPCV has repeatedly declined to adopt. **S5's actual contribution
is therefore not "shrinkage" but "shrinkage whose intensity is determined by the data"**, which is
what the James–Stein arm in §3 tests.

**(c) S13's INVERSE-VOL IS SHIPPED AT THE WRONG LEVEL.** `_weight_schemes` contains
**`risk-parity` = `norm(1/vol)`** — inverse-volatility **across THEMES**, already CPCV-tested and
never adopted. S13 asks for inverse-volatility **across NAMES inside the book**, which is a
different object: position sizing, not signal weighting. The distinction is the whole item, and
conflating them would report a shipped rejection as a new one. Separately, the signal-weighted
book S13 mentions does exist — `sw_top_decile_alpha` is computed and published, not deployed.

**(d) S27's STATED DEPENDENCY IS SATISFIED, AND IT CUTS AGAINST S27.** The item says *"Run this
after X6, not before — if the structural-break test says these are breaks rather than drift, the
correct response is a regime split."* **X6 is `DONE` and returned `NULL`**: *"Structural-break
test null under Holm-Bonferroni; the 2012 story is NOT confirmed."* So there is no confirmed
break to respond to, and the drift S27 exists to track is itself not established.

**(e) S6 AND S24 ARE GENUINELY UNTESTED.** No factor-momentum overlay and no bootstrap ensemble
exists anywhere in the tree.

---

## 2. THE COMMON INSTRUMENT

**One panel build. Six scorings — the deployed arm plus five. Every arm a column set on ONE
frame**, so the arms differ in the weighting/combination rule and in nothing else. Identical
`(date, ticker)` key sets, asserted.

**The deployed comparator is the flat 1/7 composite** every published figure is measured on.

**BOOK-LEVEL VERDICTS ONLY.** No arm is judged by per-signal or per-theme IC, and no arm may be
promoted on one. This is not a stylistic choice: P6.3, X3, S20/S21, S3 and S16 have now
demonstrated **five** times that theme IC does not judge a construction change, and S16 added the
sharper version — a construction can be **rank-identical** to the incumbent and still look
different by other measures. Per-arm IC is recorded as a diagnostic and carries no verdict.

---

## 3. THE FIVE ARMS, exactly

* **S5 — HIERARCHICAL SHRINKAGE (James–Stein).** Estimate each theme's IC mean `mu_i` and its
  standard error across the 69 periods. Shrink toward the grand mean with the **data-determined**
  James–Stein intensity `c = 1 - (k-3)*sigma2 / sum((mu_i - mubar)^2)`, clipped to `[0, 1]`,
  `k` = number of themes. Weights ∝ `clip(shrunk_mu, 0, None)`, renormalised. **This differs from
  the shipped `ic-shrunk-50` in exactly one way: the 50% is replaced by an estimate.**
* **S6 — FACTOR MOMENTUM ON THEMES.** For each theme, its own long-short return over the trailing
  **4 periods** (~12 months), computed point-in-time from dates strictly before the scoring date.
  Weight ∝ `equal * (1 + trailing_return_rank_centred)`, then **capped at 2× the equal weight and
  floored at 0** — the audit's own pre-committed bounds, fixed here before running. Time-varying
  by date.
* **S13 — VOLATILITY-TARGETED BOOK.** The composite is **unchanged**; only the weighting of names
  **inside the top decile** changes, from equal to **inverse trailing 63-day volatility**, and a
  second variant **capped at 2× the equal weight**. Both variants are reported; the **capped one
  is the registered primary**, because an uncapped inverse-vol book can concentrate.
* **S24 — ENSEMBLE ACROSS DRAWS.** `B = 200` bootstrap resamples **of the themes** (sampling the
  signal set with replacement, not the names), recomputing the composite each draw and averaging
  the **within-date ranks**. Seeded and recorded. Per-name rank dispersion across draws is emitted
  as a by-product, which is the item's stated secondary value.
* **S27 — RECENCY WEIGHTING.** EWMA-IC theme weights at half-lives of **3 years (756d)** and
  **10 years (2520d)**, **against the shipped 5-year (1260d) default**, which is the incumbent for
  this arm and not a third challenger. Two half-lives, no sweep.

A name with no computable value in any arm is **dropped, never imputed** — imputing a neutral
score converts an availability gap into a signal (S10's failure mode).

---

## 4. THE GATE

Primary, for the four arms that change the composite (S5, S6, S24, S27): **held out in BOTH split
directions, boundary embargoed** — the arm must beat the deployed composite by
**≥ +100 bps top-decile alpha AND ≥ +0.25 long-short *t*, in BOTH halves**, the same margins used
by `SECTOR-NEUTRAL-B6`, `S20`, `S21`, `S3` and `S16`.

**CPCV is the authority for weight adoption** and is reported for every arm that produces a weight
vector (S5, S6, S27): an arm CPCV declines is not adopted whatever the held-out split says. This
is the existing rule — *"if CPCV runs and rejects, keep the defaults"* — and it binds here.

**S13 IS JUDGED DIFFERENTLY, AND THE DIFFERENCE IS FIXED NOW RATHER THAN DISCOVERED LATER.** It
changes position sizing inside the long book, so **the long-short leg is unchanged BY
CONSTRUCTION**. Its *t* margin is therefore recorded **`N/A — unchanged by construction`** and
may **never** be reported as a pass. S13 is judged on the alpha margin, plus the three quantities
the audit actually asks for — **Sharpe, maximum drawdown and turnover** — which are reported
whatever the alpha does. **X7 calibrates no floor for Sharpe, drawdown or turnover**, so those
three are reported as measurements and carry no verdict.

**Verdict per arm: ADOPT-ELIGIBLE** iff it clears every applicable margin in both directions;
otherwise **REJECTED**. Ambiguous is a **NULL** (`RUN_RULES` A6).

### 4.1 THE FAMILY-WISE CLAUSE — five siblings, fixed before any result

**Five arms are tested against one bar, so the chance that at least one clears by luck is far
above the per-arm rate.** Under independence, five arms each at a nominal 5% gives
**≈23%** for at least one. The arms are positively correlated (all are functions of the same theme
IC series), so 23% is an **upper bound** — but it is the right order of magnitude and X7 has
measured this exact structure once already: testing eight themes makes *"at least one theme at
IC t ≥ 2.0"* a **39%** event under pure noise.

Therefore, fixed in advance:

* **A single clearing arm is recorded `ELIGIBLE — UNREPLICATED, 1 OF 5 SIBLING ARMS`, never
  "adopted"**, and that label must travel with the figure wherever it is quoted.
* It gets **the full skeptical treatment**: both split directions reported explicitly, its CPCV
  verdict reported beside it, and its per-half deltas shown rather than summarised.
* **Two or more arms clearing would be the more interesting outcome** and is *not* treated as
  stronger evidence per arm — the arms are correlated, so co-clearing is close to what a common
  underlying effect *or* a common noise draw would both produce.

---

## 5. CONTROLS — all read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record.** The deployed arm must return
  `top_decile_alpha` 0.07174142332098163, `long_short_tstat` 2.8360640685320595, HAC
  2.6199121240414884, `monotonicity` −0.8909090909090909. **The run ABORTS before any arm is read
  if it does not.**
* **C2 — identical rows** across all six scorings.
* **C3 — no arm is inert.** Within-date rank correlation against the deployed composite, per arm.
  **An arm at ~1.000 changes no ordering and its verdict is meaningless** — S16's identity result
  is why this control now exists.
* **C4 — every weight vector is a valid weighting**: non-negative, sums to 1, and S6's bounds
  (≤ 2× equal, ≥ 0) actually bind where claimed.
* **C5 — S5's shrinkage is not degenerate.** The James–Stein intensity is reported. **If it clips
  to 1.0 the arm IS equal weight** and must be reported as such rather than as an independent
  scheme; if it clips to 0.0 it is raw IC-proportional, which is already a shipped scheme.
* **C6 — S24's ensemble is seeded and reproducible**, and its draw count is reported. A bagging
  result that changes between runs is not a result.
* **C7 — S13 does not change the composite.** The top-decile MEMBERSHIP must be identical to the
  deployed arm's on every date; only the weights inside it move. Asserted, not assumed.
* **C8 — COVERAGE FIRST, per the COVERAGE RULE.** Each arm's non-null coverage is reported before
  its verdict. S13 additionally needs a trailing volatility per name; **rows lacking it fall back
  to equal weight and the fallback RATE is reported**, because a silent fallback would make the
  arm quietly identical to the incumbent.

---

## 6. WHAT ADOPTION WOULD COST

Adoption of any arm is a **VINTAGE EVENT**. The current vintage is **DERIVED, never assumed**
(`PT-GAPDUE`) at the time of running and recorded in the write-up. Per Rule 6 a vintage change
resets the whole five-year forward clock and buys nothing statistically.

**Therefore no arm is adopted by this register.** An eligible arm is recorded **ELIGIBLE**, with
the §4.1 label, and the decision is Don's on the evidence. Nothing in `settings.py` or the live
scoring path changes on this register's result.

---

## 7. EXPECTATIONS, per arm, written before any arm was scored

Framed by §0. **The register expects all five to fail**, and says so per arm with a confidence and
a reason, because the value of writing them down is that this project's directional calls keep
being wrong.

1. **S5 fails — 80/20.** The audit itself predicts shrinkage lands near equal weight, *"which is
   the point"*. And the fixed-intensity version (`ic-shrunk-50`) has already been offered to CPCV
   repeatedly and never adopted. **If S5's James–Stein intensity comes back near 1.0, the arm is
   equal weight and the finding is that the data asks for the weighting already deployed** — a
   genuine, if unexciting, result.
2. **S6 fails — 85/15.** The highest-confidence rejection here, and the audit agrees: it records
   Asness's critique that most apparent factor timing is value-timing in disguise, and notes that
   *"Valquo's own CPCV has consistently declined to time anything."*
3. **S13 fails the ALPHA gate while improving the thing it exists to improve — 60/40**, and this
   is the arm most likely to show something real. Inverse-vol sizing is one of the few results the
   audit says *"replicates almost everywhere"*, and the standard shape is **Sharpe up, drawdown
   better, return slightly down** — which fails an alpha-margin gate **by construction**. **The
   gate is the wrong instrument for a risk-management change, and this is registered as a known
   mismatch rather than discovered afterwards.** Both are reported.
4. **S24 fails — 80/20.** Bagging over a signal set of seven shrinks every draw toward the same
   mean composite; there is very little to bag, and the ensemble's rank correlation with the
   incumbent is expected **above 0.98**.
5. **S27 fails — 85/15**, and it is the arm whose premise is weakest: recency weighting is
   already shipped at the middle half-life (§1a), and X6 found no confirmed structural break to
   justify a shorter one (§1d).
6. **Family-wise: at least one of the five clears in at least one half — 55/45.** That is not a
   prediction of a real effect; it is a prediction about **noise across five correlated arms**,
   and §4.1 is the rule that keeps it from being read as one.

---

## 8. TRIAL COST

**Five arms, one weighting each, no grids: equity `N` 165 → 170.** Charged whatever the verdicts
are. S13's two variants count as **one** arm (the capped one is the registered primary and the
uncapped one is reported beside it, not selected between); S27's two half-lives likewise count as
**one** arm, because both are the same hypothesis at two settings of one parameter and neither is
chosen on the result.

**The §1 premise checks charge nothing** — they measure what the code already is.
`BACKTEST_RESULTS.json` is re-run **from a clean tree** so the artifact carries the honest
denominator.

---

## 9. WHAT THIS REGISTER DOES NOT DO

* It does **not** re-test the eight shipped `_weight_schemes`. CPCV has answered that question
  repeatedly and this register does not re-buy the answer.
* It does **not** implement the full Bayesian (MCMC) version of S5. The audit calls that a stretch
  goal and says the empirical-Bayes estimator *"captures most of the benefit"*; a `numpyro`
  version is a different item.
* It does **not** touch `low_risk`, whose removal S13 is described as complementing. That theme's
  status was decided by `holdout_theme_validate` and is not re-opened here.
* It does **not** change `halflife_days` anywhere in the live path, whatever S27 returns.
* It does **not** produce a per-name confidence display from S24's dispersion. The dispersion is
  emitted and recorded; putting a number on the product's surface is the web lane's and needs its
  own decision.
