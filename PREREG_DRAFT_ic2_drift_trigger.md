# PREREG DRAFT — IC2, THE DRIFT-TRIGGERED REBALANCE

**DRAFT. Frontier Scout. No measurement, no arm, ZERO trials.**

**WITHDRAWN FROM THE RANKED SIX, and the withdrawal is the recommendation.** Two reasons, both
stated rather than hedged. **(a)** Its honest prior is that it **closes at zero trials** on the
free census in §5 — `S22`'s tenure numbers make the interesting middle band unlikely — so it is
not a candidate for a trial so much as a cheap closure, which `MB15`, `W-14`, `DC-1` and `W-28`
all establish as the best outcome an item can have. **(b)** It is a **cadence** question and may
already be r1's. **The free kill is drafted in full below so that whoever owns the boundary can
run it for nothing**; what is withdrawn is the claim on a trial, not the work.

**BOUNDARY WITH r1.** `REBAL-CADENCE` tests FIXED-calendar cadences (quarterly / semi-annual /
annual / staggered). This is a **STATE-CONTINGENT** cadence: the calendar never fires it, the
book's own drift does. If r1's item admits a state-contingent arm, **this draft is withdrawn
outright rather than run beside it** — two lanes measuring one cadence question is how two numbers
come to exist for one decision.

---

## 1. MECHANISM

Rebalance only when the held book has drifted: compute the mean current rank of the names held,
and rebalance when it falls past **ONE** pre-committed threshold. The claim is that a calendar
rebalance on a book that has not drifted pays turnover for nothing, while a book that has drifted
badly should not wait for the next quarter.

**ARM: one threshold, pre-committed, no grid.** The threshold is derived from the shipped band's
own geometry — the book already holds a name until it leaves the top 30% (`BAND_WIDTH = 0.30`,
wired live at vintage 4) — so the natural single threshold is the mean held rank crossing that
same 30% line. **Deriving it from a shipped constant rather than choosing it is the only thing
that keeps this a one-arm item.**

## 2. THE RECORD'S EVIDENCE *FOR*

* **`S14` proved that cutting turnover on this book can be worth real money.** Width 0.30 took
  turnover **2.6078 → 1.3514** (early) and **2.5800 → 1.4198** (late) for net alpha **+1.78pp /
  +1.77pp**, double-clearing in both directions. So turnover reduction is not free money but it is
  not nothing either.
* **`S14`'s gain was about HALF a signal effect, not purely a cost saving** — gross alpha improved
  too (**+1.02pp / +0.77pp**). That is the record's own evidence that *hysteresis* in this book
  carries information, which is the family this arm belongs to.
* **The book is expensive to turn.** Measured **261%/yr** turnover at **33.4 bps** one-way, against
  a breakeven of **134.1 bps**. The cost curve is banked (**6.57% @25 bps, 5.04% @50, 2.02% @100,
  −0.94% @150**), so any turnover change can be priced without re-measuring cost.

## 3. THE RECORD'S EVIDENCE *AGAINST* — AND IT IS NEARLY DISPOSITIVE

* **`S22`'s tenure measurement says the trigger cannot have an interesting middle.** The top decile
  turns over almost completely every quarter: Kaplan–Meier median spell **ONE rebalance**,
  **70.6% of spells last exactly one**, one-period retention **36.6%**. A book whose membership
  more than half replaces itself each quarter has a mean held rank that drifts past any sane
  threshold essentially every quarter. **So the trigger is either inert (fires quarterly, i.e. the
  incumbent) or it is wide enough to skip quarters — in which case it IS the hold-longer family.**
* **The hold-longer family is measured and it is bad.** `S23`'s `C-NEVER` control cost **−10.89pp/yr
  at HAC *t* −3.801**, the book grew to **417 names**, and alpha against the equal-weighted universe
  collapsed **15.48% → 3.37%** — by **dilution**, since it never traded. And `S22` §7 states
  directly that **cohort persistence is NOT "hold longer"**: its +6.6%→+5.1% two-year figures are
  the buy-and-hold return of a cohort selected on ONE date, while a quarterly book re-selects and
  compounds fresh selections. **Quoting `S22`'s persistence as support for skipping rebalances is
  the misreading `S22` wrote a paragraph to forbid.**
* **`S23` found nothing beats the incumbent exit.** Four challengers, all inside 0.4pp/yr in either
  direction on 69 paired periods, **three of four flipping sign between halves**. The exit-rule
  family has already been swept and came back flat.
* **`S14-WIDTH` forbids a third extension of the band**, and a drift trigger is a band on a
  different object. The register must argue it is not a fourth bite at the same apple.

## 4. BAR AND MDE

Gate: the shipped `holdout_compare_panels`, verbatim, both halves, both weightings — as above.

**MDE.** Paired within-panel, so **no calibrated floor exists** (`V2G`, `R1-VAR`) and the arm must
measure its **own** paired HAC SE (`MB8`). Equity N **248**, hurdle **3.3206712** (derived). The
bracket from `MB8` 0.1106pp to `V2G` 0.9354pp applies; because a drift trigger changes only WHICH
quarters rebalance and not the ranking, the honest prior is the **lower** end, so this arm may
actually be *resolvable* where `IC1` is not. That is the one respect in which it is attractive.

## 5. KILLS — THE FIRST IS FREE AND IS THE WHOLE POINT

* **K1 (FREE, zero trials, read FIRST and reported whatever it says). The firing-rate census.**
  From banked decile membership across the 69 dates, compute how many of the 68 transitions the
  trigger would have fired on, at the single pre-committed threshold.
  * **Fires on ≥ 64 of 68** → the trigger is the incumbent wearing a condition. **STOP, zero
    trials.**
  * **Fires on ≤ 34 of 68** → the arm skips at least half the rebalances and is the hold-longer
    family, whose nearest measured point is `S23`'s −10.89pp/yr. **STOP, zero trials**, and report
    the implied holding period beside `S23`'s figure.
  * **Between** → the arm is interesting and may proceed to one trial.
  **On `S22`'s tenure numbers the middle band is unlikely, and the register should price it as
  unlikely in advance rather than discover it.**
* **K2 (free).** The trigger must not be a disguised calendar: if its firing dates correlate above
  a pre-committed bar with quarter-ends, it is a cadence item and belongs to r1.
* **K3.** Turnover must actually fall; if it does not, the stated mechanism is absent.

## 6. VINTAGE CONSEQUENCE

**On adoption: a VINTAGE EVENT**, and a conspicuous one — it changes *when the live book trades*,
which is visible to anyone reading the rebalance history. Derive the vintage from
`track_meter.VINTAGES`, never quote it; derived today, **vintage 4 OPEN since 2026-08-13** (S14
band 0.30), ~48 days accrued. Rule 6: the reset buys nothing statistically. **ELIGIBLE, NOT
ADOPTED**, routed to Don.

## 7. CAN OWNED DATA TEST IT?

**Yes, and K1 needs no new computation at all** — the banked panel plus the shipped
`_band_select` membership reproduce the held book on all 69 dates, which is exactly what vintage
4's own construction-fidelity check already did name-for-name. So the free kill is hours, not
days, and it is the reason this draft is ranked second.
