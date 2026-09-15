# ⛔ VOID — 2026-08-26. **THE PRODUCT IS NOT ON THIS WRDS GRANT.**
> Cboe open-close returned **zero candidates across 221 libraries**. This sketch never becomes a
> register: `D4`'s purchase question is **UNDISSOLVED** and costs what `D4` said it costs.
> Left unedited below as the record of the design. **Note for whoever reads it next:** the kill
> that would have caught this was never in this file — access is the census's gate, not a
> register's. See `WRDS_UNLOCK_MAP.md` §7.1.

# PREREG DRAFT (SKETCH) — W-14: CBOE OPEN-CLOSE — the options book's first exogenous signal
## Tags: [`D4` DON'T-BUY (dissolved by entitlement) · `MB15` VOID (venue axis) · `O14`/`MB16`
## (six flow features NULL) · `R2` (the alert entry) · `MB12` (orthogonality is not a motivation)]

**DRAFT, Frontier Scout lane, 2026-08-24.** Census-gated: nothing below runs until
`WRDS_CENSUS.md` confirms the product, fields and span. **Trials: 2, options** (305 → 307;
hurdle 3.3824 → 3.3843 — re-read at run). Commit ALONE.

## 1. The argument past the flow graveyard — conditioning, not novelty

Six flow features have been measured NULL on this book (`O14`'s five, `MB16`'s VPIN), and the
venue-based retail proxy died pre-arm (`MB15`). **Every one of them was computed from our own
alert-day tick cache** — 3,884 units, 186 symbols, selected by the alert screen itself, which
`MB15`'s own scope note calls *"selected toward the retail-heavy tail... does not generalise to
ordinary days."* Cboe open-close is **full-market and unconditioned by us**: customer-vs-firm
**opening** buy/sell volume, published daily, the dataset behind the retail-flow literature.

**The register must argue this explicitly and not lean on novelty** (`MB12` binds: "structurally
orthogonal" has failed five times as a motivation). The mechanism claim is the literature's,
not ours: **retail opening flow is uninformed on average**, so heavy retail *opening call
buying* marks names where the option is being bought by the least informed cohort — and
`MB15` died on *identification*, never on that mechanism being refuted.

## 2. The object and the arm (one hypothesis, two counters' worth of care)

* **Signal (per underlying, per week):** retail-share of **opening** option volume =
  customer-opening volume ÷ total opening volume, and its **call−put opening imbalance**. Both
  are exogenous, published, and computed from vendor rows only.
* **Universe:** the optionable panel names, full market — **not** alert days. This is the
  point; the register states it as the departure from every prior flow test.
* **Arm:** monthly quintile sort on the signal, forward returns of the **underlying**
  (charged to options per the `U2`/`MA31` precedent on which counter predicts what — **the
  executor confirms the counter at commit**; if the arm predicts the underlying it is EQUITY by
  that precedent, and the register must pick one and say so before running).
* **Statistic:** `O14`'s `score_arm` imported verbatim (monthly-quintile long-short, month-block
  t, within-month permutation null) so the comparison to the six NULLs is like-for-like.

## 3. Pre-outcome kills (own pass, read first)

* **K1 — the renaming kill (`MB16`'s pattern, and its lesson):** if the signal correlates
  within-month above **0.90** with any of `O14`'s five features or VPIN, it is those renamed
  and the arm is WITHDRAWN. **`MB16` found its own registered kill statistic structurally blind
  to magnitude-renaming; this register tests correlation on both the signed and absolute forms.**
* **K2 — the span kill:** if the confirmed span does not cover **both halves** of the intended
  window with ≥16 months per half (`S18`'s floor), the design cannot return a both-halves
  verdict and the register stops.
* **K3 — the identification kill:** if the product does not separate **customer** from
  **firm/market-maker** opening volume, there is no retail identifier and this is `MB15` again
  on a new axis — VOID before scoring. *This is the one most likely to fire; it is written
  first for that reason.*

## 4. Power (`RUN_RULES` A-11, both vocabularies)

Printed at commit from `power_gate.state()` on the realised month count. The reference number
the register must beat: **`MB16`'s banked SE 0.04817 → a 50%-power MDE of +9.64pp against an
observed 8.35pp** — the design that could not see the effect it saw. A full-market monthly
panel has more cross-section per month than the alert cache's *median of 2 names per date*, so
the SE should fall materially; **if it does not, this register inherits `MB16`'s verdict shape
and should not be run.**

## 5. Verdict grammar, void conditions, fence

WORKS / NULL / WITHDRAWN(K1) / VOID(K2,K3). Void: using alert days anywhere; conditioning on our
own screen; quoting a result as evidence about the alert entry (`R2` stands). **Fence:** WRDS
research-only; aggregates banked, raw rows never leave `D:\wrds`; nothing renders publicly.

## 6. Prior

**~12%.** Higher than the flow graveyard's base rate because the conditioning defect that
plausibly explains six NULLs is removed; still low because five of those six were measured on
the very cohort this signal claims to identify, and because `D4`'s own analysis of this dataset
found no consumer worth $500/mo when the question was asked commercially.
