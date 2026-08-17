# PRE-REGISTRATION — the accounting red-flag risk card (`MA26-A` + `MA28` + `MA54-1`, one register)

**Committed ALONE, markdown only, before any measurement code exists.** A strict git ancestor of
every measurement commit. `MA60`'s convention check enforces this, and this register is written to
satisfy it rather than to be grandfathered past it.

**Item:** the first post-audit research item. Audit #3 closed at `cbeb658` with zero `OPEN`.
**Domain:** equity. **Trial cost: 1**, booked in `RESEARCH_LOG.md` in this same markdown-only
commit, before the run. **Equity `N` 230 → 231**; the HLZ hurdle moves 3.29790 → 3.29922, which is
0.0013 of a *t* and changes no verdict anywhere.

**Three audit ids, one hypothesis.** `MA26`-A frames this as a disclosure, `MA28` as a product
card, `MA54`-1 as a re-examination on `V6-B` M1's instrument. The batch that closed audit #3
measured them to be the same object and folded them into one register rather than three, because
building three would triple-charge one hypothesis. This is that register. **All three rows resolve
on it.**

---

## 0. What is being tested, and what is NOT

**THE GATE IS THE CRASH-RATE REPLICATION. IT IS NOT ALPHA.**

The claim is a **disclosure**: *names carrying flag X went on to suffer outcome Y at rate Z,
against a base rate of W*. It is not a screen, not a ranking, and not a return claim.

**Top-decile alpha is not computed in any arm of this register, and a `quantile_backtest` call
appearing in the arm path is a void condition (§7).** The only place alpha appears is control C1,
which reproduces the published headline to prove the panel is the right object and then aborts if
it does not — it is a gate on the instrument, never an input to the verdict.

**Why the gate is not alpha, measured rather than asserted.** `S10-ACCT` already ran the veto as a
screen and it was **REJECTED**: it failed the portfolio-drawdown leg at −0.1082pp against a +2.0pp
bar. And `S10` had already measured *why* that leg could never pass — this book's maximum drawdown
spans **exactly one 63-day period on every arm, at the same trough index 44 of 69, COVID 2020Q1** —
a market-wide quarter no name-level flag can move. Re-registering on a portfolio leg would fail for
the same reason a third time.

**The opposite-sign warning that governs the copy.** `S10`'s valuation half found the **reverse**:
a valuation-band screen deleted names that crashed at **half** the rate of the names it kept. So
this project has one accounting-flag result pointing one way and one valuation-band result pointing
the other, and the product may state a **base rate in a specific named bad outcome** and may never
say *"avoid these names"*.

---

## 1. Non-blindness, disclosed here rather than discovered later

**This register is NOT blind to the full-sample result, and it cannot be** — the pilot is published
in `data/free_analysis/S10_ACCOUNTING.json` and quoted in `CLAUDE.md`. Known before writing this:

| known figure | value |
|---|---|
| crash rate, flagged | 2.6597% (174 of 6,542) |
| crash rate, kept | 0.8743% (939 of 107,403) |
| pooled ratio | **3.0422×** |
| flagged share of rows | 5.7414% |
| coverage: Beneish / Altman / ext-fin computable | 68.59% / 76.67% / 94.51% |

**What is genuinely blind, and it is the whole substance of this register:** the pilot is a
**single full-sample number with no halves, no null, no size control and no incumbent control** —
its own artifact says so in words, `"MEASUREMENT - no calibrated floor exists for this"`. Nothing
is known about the half-level rates, the permutation distribution, the within-size behaviour, or
the correlation against incumbent themes. **Every bar in §4 is set against quantities that have
never been computed.**

**The asymmetry this creates, committed in advance:** because the full-sample separation is known
to be large, a **PASS here is weaker evidence than a FAIL**. A fail would be genuinely surprising;
a pass largely confirms something already visible. The verdict is reported with that label attached
either way.

---

## 2. A defect in the audit's own product sentence, found before measuring and corrected here

`VALQUO_MASTER_AUDIT.md:950` proposes the exact sentence the card should display:

> *"names tripping 2 of 3 fell **20%+** in a quarter **2.66%** of the time against **0.87%** for
> names that did not, over 69 quarters."*

**The rates are right and the threshold is wrong.** `S10_ACCOUNTING.json` records
`"threshold": -0.5` — those two rates were measured at a **50%** fall, not 20%.

**It is wrong in the direction that makes the card implausible on its face.** A 20%+ quarterly
fall is an ordinary event; a base rate of 0.87% for it would be obviously too low, and a careful
reader would rightly disbelieve the whole card. **Shipping the audit's sentence verbatim would
have published a number that discredits itself.**

**How this register handles it, fixed now so it cannot become a choice later.** The arm is
registered at **−50%**, because that is the threshold the pilot measured and the one the 3.04×
refers to. The **−20% rate will also be reported, as a RECORD CORRECTION with no verdict attached**,
solely to establish what the audit's sentence should have said. **It may not become the arm, and
substituting it after seeing either number is a void condition (§7).**

---

## 3. Construction — fixed before any measurement

### 3.1 The flag

**One definition, and it is the shipped one.** `scripts/s10_accounting_veto.py::build_flags` is
**imported, not re-implemented** — re-typing it would be audit `B7`'s defect class, and the
register's own claim is that this is the same object `S10-ACCT` measured.

* **Beneish M-score** > **−1.78** (published threshold, eight-variable published coefficients).
  A missing component makes the score `None`; it is never defaulted to a neutral value.
* **Altman Z** < **1.81** (published distress zone, manufacturing five-variable form).
* **External financing** in the **top decile within the date** (`(ncfcommon + ncfdebt) / assets`),
  a cross-sectional rule computed per date, never on a pooled threshold.
* **FLAGGED** = **2 or more of the 3**.

**The registered deviation, restated because it bounds what a null can close.** The audit's rule is
two-or-more of **FOUR**, the fourth being NT late-filing notices, which are **unbuildable from any
data this project owns**. This is two-of-**three**, which makes the flag **NARROWER**: a name
flagged by NT plus one other is not flagged here. **A null on 2-of-3 does not close the 4-flag
rule.**

### 3.2 The named bad outcome — ONE definition

**`fwd_ret ≤ −0.50` over the panel's 63-trading-day forward window** — a fall of more than half in
roughly one quarter. Fixed here. Not a family.

### 3.3 The base rate

**The rate among NOT-flagged rows on the same universe and the same dates**, computed identically.
Both the pooled unconditional rate and the kept rate are reported; the bar is stated against the
**kept** rate, because that is the comparison a card's reader makes.

### 3.4 Panel and windows

`data/free_analysis/panel_r5r6.pkl` — the corrected 69-date, 2,531-name panel, 113,945 rows,
2009-01-15 → 2026-01-28, the same object `S10-ACCT` used. Halves: **first 34 dates / last 34
dates, with the 35th (boundary) date EMBARGOED**, the protocol this project already uses.

A date enters the statistic only if it carries **≥ 30 flagged rows and ≥ 100 kept rows**. Fixed
now, so a thin date cannot be dropped after its value is seen.

---

## 4. The statistic, the bar, and the kill condition

**Primary statistic.** For each qualifying date *t*:

```
d_t = P(fwd_ret <= -0.50 | flagged, t) - P(fwd_ret <= -0.50 | kept, t)
```

reported as **mean(d_t)** with a **Newey–West(1)** *t*, plus the **pooled ratio**
`rate_flagged / rate_kept` over the window.

**THE BAR — all three legs, in BOTH halves.** There is no calibrated floor for a crash-rate
separation anywhere in this project, so one is **built**, on `X7`'s and `V6-B`'s method rather than
invented:

| leg | requirement | why this and not something else |
|---|---|---|
| **B1 — statistical** | `mean(d_t)` exceeds the **p95** of its own **within-date permutation null** (500 draws; the flag is shuffled *within each date*, preserving that date's flagged count and its crash outcomes exactly) | the only calibrated bar available; it holds the cross-sectional and time-series structure fixed and destroys only the flag's identity |
| **B2 — economic, relative** | pooled ratio **≥ 2.0×** | a card that says *"1.1× more likely"* is not worth displaying. A doubling of a catastrophe rate is the smallest difference a reader can act on |
| **B3 — economic, absolute** | `mean(d_t)` **≥ +0.50pp** | B2 alone would pass on a doubling of a trivially small base rate. Both must hold |

**KILL CONDITION.** Failing **any** of B1/B2/B3 in **either** half is a **NULL**. Ambiguous against
any threshold is a **NULL**, never a judgement call (`RUN_RULES` A6).

**B2's floor is set BELOW the known full-sample 3.04×, and that is disclosed rather than hidden.**
2.0× is chosen as a **product** criterion — the point at which a disclosure is worth a reader's
attention — and not fitted to the pilot. It is nevertheless the permissive direction, which is the
second reason a PASS here is weak evidence and a FAIL is strong.

---

## 5. Controls — every one fixed now, and two of them GATING

| # | control | pre-committed rule |
|---|---|---|
| **C1** | **GATING.** Reproduce the published headline on this panel: `top_decile_alpha` 0.07174142332098163, `long_short_tstat` 2.8360640685320595, NW 2.6199121240414884, monotonicity −0.8909090909090909 | **exact** equality. On failure the run **ABORTS before any arm is scored** and writes `ABORTED`. It runs in its **own pass** — session 26's defect is not repeated |
| **C2** | **GATING. COVERAGE FIRST.** Per-input computable share reported **before any rate is read** | any input below the **5%** COVERAGE-RULE floor ⇒ the arm is **VOID — UNDERPOWERED BY CONSTRUCTION**, and nothing built on it may be quoted |
| **C3** | **not inert** | flagged share must lie in **(0.5%, 25%)**. Outside that the flag is degenerate and the arm is flagged, not reported as a failure |
| **C4** | **SIZE — the failure mode that has killed three items here** | pooled ratio computed **within each of 5 within-date market-cap quintiles**. If the ratio is **≥ 1.5× in fewer than 3 of 5 quintiles**, the finding is labelled a **SIZE SORT** and **may not be displayed**, whatever the arm says |
| **C5** | **not a repackaged incumbent** | mean per-date Spearman of `flagged` (0/1) against each of the **9** theme z-scores. **max &#124;ρ&#124; > 0.50** ⇒ repackaged incumbent, may not be displayed |
| **C6** | **point-in-time** | a filing whose `datekey` is **strictly after** the scoring date must not change any flag. Pinned by a test on `tests/test_pead.py`'s protocol — tamper after the as-of date, assert nothing moves |
| **C7** | **the coverage asymmetry, reported not assumed** | Beneish is computable on ~69% of rows and Altman on ~77%, so a row missing Beneish can reach 2 flags only via Altman + ext-fin. The flagged rate is reported **split by how many flags were COMPUTABLE**, so a coverage artefact cannot masquerade as a signal |

**C4 is why this register expects to be decided by a control rather than by the arm.** `U7` turned
out to be a market-cap sort wearing a composite's name; `S10` the same; `V6-B` M1 survived only
after a within-size stratification was added. **Altman Z contains market capitalisation directly**
(`X4 = marketcap / liabilities`), so this flag is **mechanically** size-linked by construction, not
incidentally. That is the single most likely way this item fails.

---

## 6. My prior, stated before measuring — and it disagrees with the brief

The brief says *expect NULL*, on the record's base rate of ~250 tested and one adopted. **I am
going to disagree with it, and say so now rather than after.**

* **The half-level replication of the separation: I expect it to HOLD, ~80/20.** Altman Z is
  literally a bankruptcy predictor with published coefficients; a distress score separating
  catastrophic outcomes is close to mechanical, and the pilot's 174 vs 939 crashes on 113,945 rows
  is not a thin sample.
* **The size control C4: ~50/50, and this is where I expect it to be decided.** Market cap enters
  Altman Z directly.
* **Overall PASS on all three legs and all controls: ~45%.**

**Stating a favourable prior raises the bar on me, not lowers it** — if it passes, I have predicted
success and found it, which this record explicitly values less than predicting failure and being
surprised. It is recorded so the expectation can be scored against the outcome either way.

**One prediction that is not about the verdict:** I expect the **per-flag** breakdown to show Altman
carrying nearly all of the separation and external financing almost none, ~70/30.

---

## 7. Void conditions

The item is **VOID** — no verdict may be quoted from it — if any of these occurs:

1. **`quantile_backtest` or `top_decile_alpha` appears anywhere in the arm path.** The gate is the
   crash rate. Computing alpha to decide this item is swapping the hypothesis mid-run.
2. **The crash threshold changes from −0.50**, or the −20% figure is promoted from a record
   correction to the arm, after any half-level number has been read.
3. **Any bar in §4 is moved after a measurement.** The floors are 2.0× and +0.50pp and p95, fixed
   here.
4. **The flag construction is re-implemented** rather than imported from
   `scripts/s10_accounting_veto.py`, or any threshold in it is changed.
5. **A second outcome definition is added** — a distress/delisting arm, another horizon, another
   drawdown depth. `V6-B` M2 already established that the ACTIONS distress route is
   **underpowered by construction** at 42 events against a floor of 60; it is declined here by
   name rather than tried and discarded.
6. **A gating control and an arm are computed in one pass**, or C1/C2 are read after an arm.

---

## 8. What the product would be permitted to say

**If and only if** the arm passes all three legs in both halves **and** C4 and C5 both pass, one
sentence becomes displayable — with its base rate in it, subject to `V3` (no per-name precision)
and the withholding rules:

> *"Companies whose accounts tripped at least two of three published stress tests went on to lose
> more than half their value over the following quarter about **Z%** of the time, against **W%**
> for companies that did not — measured across 69 quarterly observations from 2009 to 2026. This
> is a base rate for a group, not a forecast about any one company, and this project has **not**
> shown that these companies underperform."*

**Banned in every state, asserted against the RENDERED payload and not the source** — because
rendering is where copy leaks, which is `dip_posture.py`'s design and the record says to carry it
forward: *"avoid these names"*, *"overvalued"*, *"will fall"*, *"red flag"* used as a verdict,
and any per-name probability.

**If the arm fails, the deliverable is the sentence's absence and the reason**, and the card is not
built. A NULL must be exactly as reachable as a pass.

---

## 9. Trial accounting

**1 trial, equity.** One hypothesis, one outcome definition, one statistic, one bar. Charged to
**equity** on the `U2`/`MA31`/`P1S0` precedent — the arm predicts the **underlying's** forward
return path.

The controls charge **nothing**: C1 reproduces a published figure, C2/C3/C7 are coverage censuses,
C4/C5 are diagnostics with pre-committed interpretation rules and no independent verdict, C6 is a
correctness pin. The per-flag breakdown and the −20% record correction charge nothing and **carry
no verdict**.

**Equity `N` 230 → 231.** Options 294 and infra 15 are untouched. `BACKTEST_RESULTS.json` needs no
re-run: `N` enters the Deflated Sharpe and the HLZ hurdle, and at 231 the hurdle is **3.2992174**
against **3.2979022** — 0.0013 of a *t*, which moves no published comparison.
