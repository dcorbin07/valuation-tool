# PREREG_e5_hazard_curve.md — E-5 / INV-A: WHEN do flagged names crash?

**Item `E-5` (scout invention `INV-A`), `IDEAS_LEDGER.md` BATCH 1. Domain EQUITY, 1 trial.
Register written by the executing lane, ALONE and BLIND: no hazard, no rate beyond the
figures `MA28-CARD` already published in `CLAUDE.md`, and no quarter-2/3/4 quantity of any
kind has been computed at the time of this commit. Committed markdown-only, zero `.py`, as a
strict git ancestor of every measurement commit; the trial is booked in a separate commit
BEFORE the runner is invoked.**

**ADOPTS NOTHING. CHANGES NO PRODUCT COPY. LICENSES NO TRADE.** No file under
`valuation/screener`, `valuation/web` or `valuation/engine` is touched by this item, and a
test pins it.

---

## 0. PROVENANCE, AND THE THREE PLACES I DEPART FROM THE PROPOSAL

The scout proposed the object, the consumers, the survival machinery, the kill and the bar.
I accept all five and depart in three places, each declared here **before** anything is run
so the departure cannot be chosen on an outcome.

**(0a) THE PRIMARY STATISTIC IS THE HAZARD RATIO BY QUARTER, NOT THE EXCESS SHARE ALONE.**
The proposal states one claim: *"hazard is front-loaded (>=60% of excess crashes inside 2
quarters)"*. The excess share is a ratio of DIFFERENCES, and `I-3`'s standing rule — measured,
not stylistic — is that the absolute gap is era-dependent on this panel (`MA28` measured kept
0.3413% early against 1.3595% late, so the gap swings 0.86pp -> 2.39pp while the ratio moves
3.42 -> 2.93). A statistic built out of differences inherits that. So the excess share is
**kept, verbatim, at its 60% bar** as leg L3, and it is joined by a leg stated on the ratio
(L2). The verdict needs both. This makes the register harder to pass, not easier.

**(0b) THE FOUR-QUARTER WINDOW IS RIGHT-CENSORED, NEVER REQUIRED.** The obvious construction —
keep only rows with four quarters of forward prices — **selects on survival, and it selects
away exactly the names the question is about.** A name that halves in quarter 1 and delists in
quarter 2 has no price at quarter 4; excluding it would delete an early event and bias the
curve toward FLAT, i.e. against the hypothesis, silently. Every row is therefore entered at
k=1 and censored when its price series ends, and a test pins that a row which crashes at k=1
and then has no further prices is counted as an **EVENT at k=1** and not dropped.

**(0c) `MA28_CARD.json` IS NOT ON DISK, SO THE INSTRUMENT GATE COMPARES AGAINST THE PUBLISHED
FIGURES INSTEAD.** `scripts/i3_crash_gate_validate.py` names
`data/free_analysis/MA28_CARD.json` as its validation target; that file is absent from both
`data/free_analysis` directories on this machine and the validator **refuses** rather than
passing vacuously (correct direction, and reported outside this lane per `RUN_RULES` rule 3).
K3 below therefore recomputes `MA28`'s own quarter-1 window from the panel with `I-3` at
`MA28`'s own bars and compares it to the numbers `CLAUDE.md` publishes. That is a stronger
gate than reading a JSON, because it re-derives rather than re-reads.

---

## 1. THE QUESTION, AND WHY IT IS NOT `MA28` AGAIN

`MA28-CARD` established a RATE: names tripping 2 or more of Beneish M > -1.78, Altman Z < 1.81
and top-decile external financing lost more than half their value over the next 63 trading days
at **2.6597%** against **0.8743%**, ratio **3.0422x**, replicating in both halves.

It says nothing about **WHEN**. A card that says *"flagged names crash 3x more often"* and a
put bought on that basis both need to know whether that 3x is concentrated in the first
quarter after the flag or spread evenly over a year. Those two worlds imply different copy and
different tenors, and the record cannot currently distinguish them.

**THE OBJECT: the conditional hazard of a >=50% cumulative loss from the flag date, by quarter,
for the first four quarters, for flagged names against kept names.**

**NEAREST ROWS, AND WHY NONE OF THEM IS THIS.** `MA28-CARD` — the rate, one quarter, no
timing. `V6-B` — a survival question, but conditioned on a **drawdown**, not on an accounting
flag, and its outcome is a forward MINIMUM rather than a cumulative return at a horizon.
`S22` — a term structure, but of ALPHA, and its standing convention (quote the horizon, never
extrapolate a floor across configurations) travels here and is honoured in §7. `MB8` — the
same flag on the top-decile BOOK, a different population, and its result binds §10.

---

## 2. THE INSTRUMENT, STATED PRECISELY ENOUGH TO BE WRONG

For every panel row `(d, tk)`, flagged or kept:

* `c0` = the ticker's last close on or before `d`, from `data/backtest/prices/{TK}.csv`.
* For `k = 1..4`: `j_k` = the `63k`-th price row **strictly after** `d`. If it does not exist,
  the row is **not observable at k** and is censored from k onward.
* `r_k = close(j_k) / c0 - 1`.
* **EVENT at k** iff `r_k <= -0.50` and no event at any `k' < k`.
* **AT RISK at k** iff no event at any `k' < k` **and** observable at k.

`63` is the panel's own forward window and is not chosen here; `-0.50` is `MA28`'s registered
threshold, reused **verbatim** rather than re-picked with its consequences already published
(`MB1SEL`'s discipline). Four quarters is the proposal's own horizon.

**ONE INSTRUMENT THROUGHOUT.** Quarter 1 is computed by the same price-path code as quarters
2-4. It would be easier to take quarter 1 from the panel's shipped `fwd_ret` and quarters 2-4
from prices; that would put a seam exactly where the hypothesis lives and could manufacture
front-loading out of two instruments disagreeing. K3 gates the single instrument against the
shipped one at the one point where they must agree.

**HAZARD AND RATIO.** For each date `d` and quarter `k`:
`h_f(d,k) = events_flagged / at_risk_flagged`, `h_p(d,k)` likewise for kept.
Pooled across dates, `HR(k) = h_f(k) / h_p(k)`. Every rate ships with its **event count**;
`crash_gate.quotable` is the only path by which a figure reaches a write-up, and
`min_events = 10` is declared here (`MB8` measured one crash in a bucket of 407 — one crash is
not a rate).

---

## 3. DATA, AND WHAT IS NOT TOUCHED

`data/free_analysis/panel_r5r6.pkl` (69 dates, 2009-01-15 -> 2026-01-28, 2,531 names — the
panel `MA28` itself ran on), `data/backtest/prices/*.csv`, `data/backtest/fundamentals.csv`
via `scripts/s10_accounting_veto.build_flags` — the **ONE** flag definition, imported and never
re-implemented (`B7`/`MA5`). `data/backtest/actions.csv` for the censoring census only.

**No option chain, no tick cache, no live quote, no network call.** Pinned by an AST test over
the shipped runner: the arm path may not name any options or live-data module.

---

## 4. PRE-OUTCOME GATES — COMPUTED AND READ IN THEIR OWN PASS, BEFORE ANY ARM

`--controls` writes `data/free_analysis/E5_CONTROLS.json`; `--arms` **REFUSES** to run without
it and without `all_gating_pass`. Computing a gating control and the outcomes it gates in one
pass is session 26's process defect and `O10`'s, and is not repeated.

**K1 — COVERAGE (pre-outcome; observability bounds the risk set from above).**
Rows observable at k=4 must be **>= 70%** of flagged panel rows, and **>= 55 of 69 dates** must
carry >= `MIN_FLAGGED_PER_DATE` = 30 flagged and >= `MIN_KEPT_PER_DATE` = 100 kept rows
observable at k=4. Both floors are `MA28`'s own per-date qualification counts, reused verbatim.
Failing K1 -> **UNPOWERED-BY-CONSTRUCTION**, and the arm does not run.

**K2 — REQUIRED-n (rule 11, pre-outcome).** Using `crash_gate.required_rows` at `MA28`'s
published kept rate (0.008743), a target ratio of 2.0, the measured flagged share and
`crit = hlz_hurdle(equity N)`, the required row count at 80% power must be **<= the observable
rows at every k**. The figure is printed **before** the arm and ships in the artifact whatever
it says. Failing K2 -> **UNPOWERED-BY-CONSTRUCTION**.

**K3 — INSTRUMENT (the strongest gate here).** Two comparisons, both required:
* my reconstructed `r_1 <= -0.50` must agree with the panel's shipped
  `fwd_ret <= -0.50` on **>= 99.0%** of rows where both are observable;
* `crash_gate.window_result` at `MA28`'s bars over quarter 1 on the full panel must reproduce
  `MA28`'s published **2.6597% / 0.8743% / 3.0422x** with each rate within **0.02pp** and the
  ratio within **0.05x**.

Failing K3 is a **VOID**, not a null: it means the object measured is not the object `MA28`
measured. A control failure discovered pre-arm may be diagnosed and repaired (`MA28`'s own C1
caught a nine-theme error that way); a control may **never** be adjusted after an arm is read,
and the two-pass design is what makes that checkable.

---

## 5. THE ARM — ONE HYPOTHESIS, THREE LEGS, ALL REQUIRED

**H: the flag's excess crash hazard is FRONT-LOADED — it is concentrated in the quarters
immediately after the flag fires and decays thereafter.**

* **L1 — ELEVATION AT ENTRY.** `HR(1) >= 2.0`, `MA28`'s own B2 ratio floor reused verbatim.
  This is a **gate, not a claim**: quarter 1 is `MA28`'s object and it published 3.0422x. What
  L1 actually tests is whether entering every row and censoring (§0b) leaves the same object;
  a large move here is a selection finding and is reported as one.
* **L2 — DECAY, ON THE RATIO.** `HR` pooled over quarters 1-2 must **exceed** `HR` pooled over
  quarters 3-4, **in the full sample and in BOTH halves** (early/late, middle date embargoed,
  `crash_gate.halves`), **and** the decay statistic must clear its own **within-date
  permutation p95** — the flag shuffled within each date, `X7`'s scheme and `MA28`'s B1, which
  preserves each date's flagged count and every crash outcome exactly and destroys only which
  names carry the flag.
* **L3 — MAGNITUDE, THE PROPOSAL'S OWN BAR.** The share of the four-quarter excess crash count
  falling in quarters 1-2 must be **>= 0.60**. Reported per half beside the full sample.

**Why 0.60 is not a free pass, computed before running:** under a FLAT hazard ratio the risk
set barely declines (quarterly crash rates are of order 3%), so the excess is roughly flat
across k and the quarter-1-2 share is ~50%. 0.60 requires a genuine decline. A decay from
HR ~ 3.0 to ~ 1.5 produces ~62%. The bar sits where it discriminates.

---

## 6. VERDICT GRAMMAR — FIVE STATES, ALL REACHABLE

| verdict | condition |
|---|---|
| **FRONT-LOADED** | L1 and L2 and L3 |
| **FLAT** | L1 holds; L2 and L3 both fail; no reversal (see below) |
| **BACK-LOADED** | L1 holds; `HR(3-4) > HR(1-2)` in the full sample **and both halves** |
| **UNPOWERED** | K1 or K2 fails, or fewer than 3 qualifying dates at any k |
| **UNRESOLVED** | any other combination, including legs that disagree across halves |

Ambiguous against a pre-committed threshold is a NULL, never a judgement (`RUN_RULES` A6).
A tie on L2 (`HR(1-2) == HR(3-4)` to the printed precision) is **FLAT**, not FRONT-LOADED.

---

## 7. POWER — RULE 11, BOTH VOCABULARIES, STATED BEFORE THE RUN

`MB22` established that every MDE this project has published is `crit x se`, a **50%-power
detection threshold**, and that the 80%-power figure is `(crit + 0.84) x se`, 1.42x larger at
crit 2.0. Both are reported here and each is labelled.

* **Pre-outcome (K2):** `crash_gate.required_rows` at the published kept rate, ratio 2.0, the
  measured flagged share, and `crit = hlz_hurdle(equity N)` — at 80% power, with the
  equal-allocation figure printed beside it for contrast and never as the answer.
* **Post-hoc, quoted WITH the verdict or not at all** (`V6`/`S19`/`MB16`'s rule): the decay
  statistic's minimum detectable effect from **its own realised standard error**, in both
  vocabularies. A NULL here means *"no decay at least this large"*, never *"no decay"*.

`X7`'s calibrated floors are **not** quoted anywhere in this item. They were calibrated on a
decile-book long-short *t* and a top-decile alpha margin at 69 dates; this is a crash-rate
hazard and neither object. Quoting one would be `S22`'s void condition and `P1S0-CONTROL`'s
floor-extrapolation error.

---

## 8. CONTROLS — NONE CARRIES A VERDICT EXCEPT AS STATED

* **C1** point-in-time: the forward window starts **strictly after** `d`; pinned by a synthetic
  fixture in which a crash dated on or before `d` must not register.
* **C2** the anchor: `c0` is the panel's own price basis, evidenced by K3's agreement rate.
* **C3** the censoring census — **the control most likely to bite.** Rows censored before k=4
  split into ADMINISTRATIVE (the panel's last dates against a price file ending 2026-07-24) and
  DELISTING. Delisting censoring is potentially **informative** and runs against the
  hypothesis' direction: a flagged name that dies without first printing a -50% quarter is
  removed from the risk set rather than counted. Reported by flag status, with the ratio, and
  the direction of the resulting bias stated in the write-up.
* **C4** — the **sensitivity that bounds C3**: re-score with distress delisting
  (`bankruptcyliquidation`, `regulatorydelisting` — `V6-B`'s definitions, and **never** the
  acquisition umbrella, since 82.63% of delistings on this universe are takeovers) counted as
  an EVENT in the quarter it occurs. Same hypothesis, stated sensitivity, **no extra trial**;
  if the verdict differs between primary and sensitivity the item is **UNRESOLVED**.
* **C5** flag persistence, **diagnostic, no verdict, and required for interpretation**: of the
  names flagged at `d`, what share are still flagged at `d+k`? This separates *"the flag's
  information decays"* from *"the flag goes away"*, and the two mean different things to O-1's
  tenor choice. It is not a leg because no bar for it was derivable before the run.
* **C6** null non-vacuity: the permutation draws must be non-degenerate (a strictly positive
  spread and >= 100 distinct values), because a null that returns a constant scores everything
  perfectly. `MB21`'s C1 failed vacuously at a perfect 0.000e+00 on an empty frame; a null is
  checked for having compared something.
* **C7** the shuffle is `I-3`'s shuffle: the decay null's permutation scheme must reproduce
  `crash_gate.permutation_null` **exactly** on a single-quarter degenerate case at the same
  seed. This is `B7` protection obtained by measurement rather than by asserting that two loops
  are the same.
* **C8** size, **diagnostic, no verdict**: Altman Z contains market cap directly, so the flag is
  mechanically size-linked and `MA28`'s C4 found the effect strongest in megacaps. Median
  market cap by flag status and the per-quintile quarter-1 ratio are reported so a reader can
  see whether the timing question inherits the size gradient. It is not a leg: `MA28` already
  adjudicated the size question for the RATE, and re-adjudicating it for the TIMING would be a
  second hypothesis on one trial.

---

## 9. VOID CONDITIONS

1. Reading any quarter-2/3/4 quantity before this file is committed. (It has not been.)
2. Changing `CRASH`, `63`, `K_MAX`, the 30/100 per-date floors, the 2.0 ratio floor, the 0.60
   share floor, `N_PERM` or the seed after any arm value is read.
3. Choosing the half boundary, the quarter grouping (1-2 vs 3-4) or the censoring rule after
   seeing an arm.
4. Adding a fifth quarter, a second crash threshold, or a second flag definition — each is a
   new hypothesis and charges its own trial. `-0.20` is `MA28`'s **record correction** and may
   not become an arm here.
5. Quoting any `X7` floor, or comparing the decay statistic to a bar calibrated on another
   object.
6. Reporting the primary verdict when it disagrees with C4's sensitivity as anything other than
   **UNRESOLVED**.
7. Quoting the excess-crash DIFFERENCE as a headline figure without both rates and the ratio
   beside it (`I-3`'s rule, `MA28-CARD`'s measurement).

---

## 10. WHAT THIS MAY NEVER BE QUOTED AS

* **NOT a screen and NOT a trade.** `S10` established that a name-level exclusion cannot move
  this book's drawdown, whose worst quarter is one market-wide event (COVID 2020Q1, trough
  index 44 of 69). Nothing here licenses excluding a name.
* **NOT a book result.** This is the **PANEL**. `MB8` measured `MA28`'s flag firing on 3.56% of
  the top-decile book and catching one crash of eighty-four, and measured a haircut on it making
  exposure WORSE. **A hazard curve on the panel does not transfer to the book, and O-1 may not
  read it as if it did.**
* **NOT evidence about alpha, in any direction.** The verdict object is a crash RATE.
* **NOT a claim that the flag causes anything.** It is a conditional frequency.
* A **FLAT** verdict is not evidence that timing is absent — it is evidence that no decay at
  least as large as §7's MDE is detectable on 69 quarterly dates.

---

## 11. EXPECTATIONS — WRITTEN NOW, SCORED IN THE WRITE-UP

1. **L1 clears** (HR(1) >= 2.0) — **90/10**.
2. **Entering-and-censoring leaves `MA28`'s headline nearly intact**: |HR(1) - 3.0422| < 0.5 —
   **70/30**.
3. **L2 clears** (decay on the ratio, both halves, clears its permutation p95) — **45/55**.
4. **L3 clears** (>=60% of excess in quarters 1-2) — **35/65**.
5. **Overall verdict is FRONT-LOADED** — **35/65**. (The proposal said ~40%; I am marginally
   more pessimistic because the cumulative-from-anchor construction gives later quarters more
   time to reach -50%, which works against front-loading mechanically.)
6. **C5: fewer than half the names flagged at `d` are still flagged at `d+4`** — **55/45**.
7. **C3 bites: flagged rows are censored by delisting at >=2x the kept rate** — **65/35**.
8. **The verdict is not UNPOWERED** — **85/15**.

---

## 12. TRIAL ACCOUNTING

**1 trial, EQUITY** — the arm predicts a forward outcome of the UNDERLYING (`U2`/`MA31`'s
precedent, and `MA28-CARD`'s own charge). Booked in its own commit **before** the runner is
invoked, and `EXPECTED_BY_DOMAIN` in `tests/test_research_log_integrity.py` moves in that same
commit (`MA13`'s tamper-evidence).

Equity **N** was re-read from `research_log.detail()` **after** merging `origin/main`, never
quoted from a prompt or a handoff (`MA37`'s rule, three times on the record): the live count is
**236**, and this item takes it to **237**. Options 305 and infra 19 are untouched.

The controls pass, C4's sensitivity, C5, C8 and the census charge **nothing**: a control can
only ever block a finding, never produce one, and adds no degree of freedom to any published
claim (`MB1SEL`'s reasoning, and its correction direction).
