# PREREG — "OWN THE EVENT" as its OWN strategy, not a filter on a dead one

**Committed ALONE, before any arm is scored.** One `.md`, zero `.py`; a strict git ancestor of
every measurement commit.

**Item:** `MA54-2` (`OPEN` in the ledger) / `O17`'s C4 arm. **Don's decision, made on purpose:**
C4's `NULL` rests on a **retention floor set for a product reason**, not on the effect. The
alert product is dead, so that constraint no longer applies to anything. This register does not
lower the bar — it **derives the bar a STANDALONE strategy should face, before scoring the arm
against it**, on the `TP-BAR` precedent.

**ADOPTS NOTHING.** No live code path changes. **Options `N` 292 → 294** (§6).

---

## 0. Premise — verified against the artifact, not quoted from the audit

`data/free_analysis/O6_O7_O17_EARNINGS.json`, arm `O17.arms.C4_own_the_event`, read directly:

| | n | all_mean | kept_mean | **gain** | null p95 | retention |
|---|---|---|---|---|---|---|
| **full** | 3,482 | 0.0373387 | 0.0841987 | **+0.0468600** | 0.0220829 | **0.5706491** |
| early | 1,646 | 0.0562120 | 0.1136933 | **+0.0574813** | 0.0324106 | 0.5710814 |
| late | 1,836 | 0.0204186 | 0.0577184 | **+0.0372998** | 0.0294068 | 0.5702614 |

**verdict: `NULL`.** Every figure the re-open rests on reproduces exactly: **+4.686pp/trade**,
positive in **both halves**, clearing its **own calibrated null in both halves** — and `NULL`
**solely** because retention 0.5706 fell under `RETENTION_FLOOR` = 0.70.

**THE RULE ITSELF IS ALREADY BUILT AND SHIPPED.** `valuation/studies/earnings_surface.py::
owns_the_event(entry, expiry, earnings)` returns True when the contract's expiry falls after the
next announcement following entry, and **`None` for UNKNOWN**. It is **called, never re-typed**.

**THE COVERAGE HOLE IS SYSTEMATIC AND IS INHERITED VERBATIM.** O17 measured that **29 of 186
names have ZERO earnings coverage (388 trades, 10.0%) and every one is a foreign private issuer**
filing 20-F/6-K. A filter reading "no date" as "no announcement" **fails open on a non-random
tenth of the book**. `owns_the_event` returns `None` there and those trades are **DROPPED**,
never scored as either arm.

---

## 1. WHY THIS IS A DIFFERENT EXPERIMENT, AND THE COMPARATOR IS THE WHOLE POINT

**As a FILTER, C4's comparator is the unfiltered alert book, and its null is a random-REMOVAL
null** — `perm_null_removal` asks *"does removing THESE trades beat removing a random subset of
the same size?"* That is the correct null for a filter and it is **not** a test of a strategy.

**As a STANDALONE strategy the comparator must be RANDOM ENTRY**, because `R2` is the standing
result that this project's alert **loses to random entry by −5.0640pp/trade** (split-clean, CI95
[−8.5957, −1.5325], paired name-year sign test z −4.9612 over 1,332 cells, p 7e-07). A "strategy"
built out of a losing book has to show it is not simply inheriting the loss.

**THE DECISIVE TEST HAS NEVER BEEN RUN AND IT IS RUNNABLE ON OWNED DATA.** The five-seed
split-clean random-entry control books exist (`control_r2_splitclean_seed0..4.pkl`) and carry
`alert_ts`, `expiry`, `ticker` and `pnl_pct` — every field `owns_the_event` needs. So the rule
can be applied to **random entries** exactly as it is applied to alert entries.

Three outcomes, all informative, distinguished **before** the run:

* **Random-spanning ≈ alert-spanning, both well above their non-spanning halves** → the effect
  is a property of **owning an earnings event**, independent of the dead alert. **That is a
  genuine standalone strategy and the largest un-harvested measured effect in the catalogue
  becomes real.**
* **Random-spanning > alert-spanning** → R2's anti-signal persists inside the earnings subset;
  the rule is real and the alert still subtracts value. The strategy is "buy calls spanning
  earnings", with **no alert in it at all**.
* **Random-spanning shows no gain while alert-spanning does** → the +4.686pp is **alert-specific
  and dies with the alert**, and MA54-2 closes.

---

## 2. THE ARMS

* **A1 — the strategy.** On the split-clean alert book: `owns_the_event == True` vs `False`,
  `None` dropped. Reproduces C4 and is the anchor.
* **A2 — the strategy on RANDOM ENTRY.** Identical rule, identical scorer, on the five pooled
  split-clean control seeds. **This is the arm the register exists for.**

**A1 and A2 use ONE scorer and one earnings map.** No arm may differ by fill, contract, exit or
calendar — only by which entry set it runs on.

**THE STOCK EXPRESSION, and it carries no verdict.** For every scored trade, the underlying's
return over the identical window. If buying the **stock** through earnings earns the same, the
option adds nothing but cost and leverage, and the "strategy" is an equity observation wearing
an options costume. Reported beside every arm.

---

## 3. THE BAR — DERIVED FIRST, CALIBRATED NOT ARGUED, AND BINDING WHATEVER IT RETURNS

`TP-BAR`'s lesson is quoted rather than paraphrased: *"what the memo pre-registers is a
PROCEDURE, NOT A NUMBER, deliberately — any level argued in prose would be one chosen after
seeing which arms pass."* So no retention number is asserted here.

**WHY 0.70 DOES NOT TRANSFER.** It exists because a **filter** must not starve an alert stream a
product depends on. A standalone strategy has no stream to starve; it **generates** its own
trades. Retention is not merely a different number for it — it is **not a defined quantity**.
What replaces it is **breadth and concurrency**: is this a book, or a handful of clustered
events?

**B1 — ABSOLUTE BREADTH, derived from a measured object.** On each of three axes — trades per
year, share of names traded, share of months with at least one entry — the strategy must be **no
narrower than the alert book it replaces**. The alert book is the object every published options
figure in this project is measured on; a strategy narrower than a book **already shown to fail
survivability at $50k** (`O11`) is not more tradeable than it. Derived from a measurement, not
chosen.

**B2 — CALIBRATED BREADTH.** 200 random entry sets of the **same size** drawn from the same
(name, date) grid and window; the bar is the **p5** of their breadth on each axis. This asks
whether the rule is concentrated **beyond what its own trade count forces**. Binding whatever it
returns.

**B3 — CONCURRENCY, AND IT IS THE ONE THAT CAN ACTUALLY FAIL.** Earnings arrive in four
reporting seasons, so a spans-earnings book clusters in **time** by construction. `O11` measured
that this is the failure mode that matters: alerts cluster, **51.5% of trades fall in weeks with
more than 10 alerts, expectancy is −4.51% in quiet weeks and +14.28% in the top decile of busy
weeks**, and a concurrency cap of 10 refused 1,677 of 3,870 trades and turned a **+3.27%
per-trade expectancy into −25.9% total return, $50,000 → $37,059**. Bar: **peak simultaneous
open positions, and the share of trades refused at O11's own caps of 10 and 50, must be no worse
than the alert book's.** If the strategy is *more* concurrent, O11's finding bites **harder**,
and a positive per-trade expectancy is then explicitly **not** evidence it is tradeable.

**ALL THREE ARE COMPUTED AND WRITTEN DOWN BEFORE ANY ARM IS SCORED**, in their own pass, and the
arms stage refuses to run without the artifact (the `O19` two-pass design).

---

## 4. CONTROLS

* **C-SEEDS.** Five seeds **pooled**, never one. `R2`'s standing rule — a single control seed
  ranges +6.46% to +15.34% on this payoff and can flip a verdict on its own.
* **C-SIGN.** The **paired name-year sign test** carries the verdict against random entry, not
  the mean. R2 established the paired *t* is the wrong statistic on a barbell payoff (it is never
  significant even pooled, −1.227, p 0.22) while the sign test reaches z −4.9612.
* **C-HALVES.** Both halves, on the same split O17 used, for both A1 and A2.
* **C-UNKNOWN.** The 388 zero-coverage trades are dropped and **counted**, and the count is
  required to be non-zero — a zero would mean the earnings map never reached the data.
* **C-DTE.** `O13` measured expectancy climbing monotonically with tenor (−0.35% → +7.63%), and
  a contract that spans the next announcement is **mechanically longer-dated**. So the confound
  is structural, not hypothetical. O17 already refuted it *within the alert book* (the gain stays
  positive in **every DTE quartile**: +6.416, +6.310, +2.138, +2.711pp) — this re-runs that
  stratification on **both** arms, and additionally reports a **DTE-matched** comparison.
  **If the gain vanishes DTE-matched, the strategy is a tenor filter wearing an earnings filter's
  name** — `U7`'s and `S10`'s failure mode, and `MA54-4`'s explicit warning about `O6`.
* **C-SPLIT.** The split-clean books only. `U1-SPLIT` removed a +31,921% artefact from these
  exact corpora; the pre-split books may not be used.
* **C-FILL.** The shipped fill engine at `DEFAULT_AGGRESSION = 1.0`, unchanged.

---

## 5. VERDICT

**CANDIDATE** requires **all** of:

1. A1's gain positive and clearing its own calibrated null in **both halves** (reproducing C4);
2. **A2 shows the same effect on random entry** — the rule is not alert-specific;
3. **B1, B2 and B3 all pass**;
4. C-DTE: the gain survives DTE-matching.

Anything else is **REJECTED** or **NULL**. **Ambiguous against a pre-committed threshold is a
NULL** (`RUN_RULES` A6).

**CANDIDATE IS NOT ADOPT.** Adoption is a construction change and Don's call. And **O11 governs
everything downstream**: a positive per-trade expectancy on this corpus has already been shown
compatible with losing money at realistic size, so no outcome here licenses trading it.

---

## 6. TRIALS, EXPECTATIONS, VOID CONDITIONS

**TRIALS: 2** — A1 and A2, each of which could independently be reported as a positive finding.
**Options `N` 292 → 294.** The three bars are calibrations and charge **zero** (the `X7` /
`HACFLOOR` / `TP-BAR` precedent: a calibration searches nothing). The stock expression and the
DTE stratification are reported diagnostics and charge zero.

**EXPECTATIONS, written before any arm is scored:**

1. **A1 reproduces C4 to the digit — 95/5.** Same book, same rule, same scorer.
2. **A2 shows a POSITIVE spanning-vs-not gain on random entry — 70/30.** Earnings are a real
   volatility event and a longer-dated contract owns it whoever bought it.
3. **The gain is SMALLER on random entry than on the alert book — 55/45**, with no strong view;
   R2 says the alert subtracts value, which argues the other way.
4. **B1 and B2 pass comfortably — 85/15.** Earnings fire ~4×/yr on nearly every covered name, so
   breadth is not the binding constraint. **Stated in advance so that passing them is not later
   presented as a discovery.**
5. **B3 is the bar that binds, and the strategy is MORE concurrent than the alert book — 65/35.**
6. **The DTE-matched gain is materially smaller than the raw gain — 60/40**, because a
   spans-earnings contract is mechanically longer-dated and O13 says tenor pays.
7. **This does NOT end with something Don should trade — 85/15**, on O11.

**VOID CONDITIONS.**

1. This file is not a strict ancestor of every measurement commit.
2. Any bar, arm, comparator or verdict rule above is edited after a number is read.
3. **A retention threshold is asserted in prose instead of derived by §3.** That is the exact
   move `TP-BAR` exists to refuse.
4. A third arm, a second event definition, or a swept DTE/window is scored. The grid is A1 and
   A2 and nothing else.
5. The pre-split books are used, or a single control seed is quoted.
6. `owns_the_event`'s `None` is folded into either arm.
7. The result is reported as evidence the strategy is **tradeable** rather than that the effect
   is **real**. O11 is the standing reason those are different claims.
