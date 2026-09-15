# PREREG_DRAFT_w19_trace_distress.md — bond-implied distress on `MA28`'s own validated verdict object
## Frontier Scout draft, 2026-08-28. **BLIND. Zero trials charged by this file. No outcome statistic computed.**
## For an executor to accept or reject. **Rejection costs nothing.**

---

## §0 · WHY THIS REGISTER EXISTS, AND WHAT MAKES IT DIFFERENT FROM EVERY OTHER TRACE PROPOSAL

TRACE is **VIRGIN** in this record and `WRDS_UNLOCK_MAP` W-19 already lists it. **What this draft
adds is the verdict object.** The obvious TRACE register — *"add a credit-spread column to the
composite"* — is an **addition**, and additions are **0-for-9**. This register is not that.

> **`MA28`'s accounting flags are a PROXY FOR DISTRESS. TRACE offers a better-measured instrument
> for the SAME construct. And this project has already validated exactly one verdict object for
> that construct: CRASH RATE.**

`MA28-CARD` **passed all three legs** on crash rate (**3.0422×**). `E-4` measured the full sample
at a pooled ratio of **3.1914**. `S10`'s A2 arm measured flagged names crashing more than 50% on **2.660%** of
occasions against **0.874%** for names kept — a ratio of **3.04×** — and `S10`'s own note calls it
*"the number the audit calls the one that matters most."*

**So this register is `SEARCH_DOCTRINE` search-line 1 (re-measurement before addition) and
search-line 2 (verdict objects matched to mechanisms) satisfied by a single arm** — the only entry
on the width map that does both. **And it is the register most likely on this map to die free**,
for the reason in §5.

---

## §1 · THE HYPOTHESIS

**Names whose bonds trade at distressed spreads crash more often than names their accounting
flags do not catch — and bond-implied distress ranks crash risk better than the accounting-flag
proxy does, on the same names and dates.**

**Two arms, both on crash rate:**

* **A1 · RE-MEASUREMENT (primary).** Among names `MA28` **flags**, does a bond-spread ranking
  separate the ones that crash from the ones that do not? *(Does the better instrument add
  resolution inside the flagged set?)*
* **A2 · COVERAGE-COMPLEMENT (secondary, reported, non-decisive).** Among names `MA28` does
  **not** flag but whose bonds trade distressed, is the crash rate elevated relative to the
  unflagged base rate? *(Does the accounting proxy MISS names the market catches?)*

**A2 is the interesting one and it is deliberately not the gate**, because its population is
defined by the instrument being tested — a selection this draft will not hide behind.

---

## §2 · WHY THIS IS NOT AN OPTIONS ENTRY SIGNAL, AND NOT AN ADDITION

* **`R2` stands.** The options entry question is closed (**−5.06pp** against random). **Nothing here
  is an entry signal**, and the register may not become one without arguing past `R2` on its own.
  *(`MB1`'s timing/selection split is deliberately NOT quoted as support: the record has since
  withdrawn that reading — the confound is **−2.5454pp** against a **−1.2762pp** residual, twice the
  size and the same direction, and `CLAUDE.md` states it **must not** be quoted as evidence that
  contract selection matters.)*
* **`MB12` stands** — four items in the R² 0.027–0.145 band, a fifth at 0.2926 / 0.2936, none
  clearing. This register does **not** claim orthogonal information. It claims a **better
  instrument for a construct the record has already validated.** If the bond measure turns out to
  be orthogonal to `MA28`'s flags, that is `A2`'s territory and `A2` is not the gate.
* **`X-SEED-1` / `E-8` are complements, not duplicates.** With IvyDB dead, **TRACE is the only
  market-implied distress instrument that reaches names without liquid options.**

---

## §3 · THE VERDICT OBJECT, AND THE BAR

**Object: crash rate** — the fraction of name-quarters with a drawdown worse than the threshold
`MA28-CARD` already used, **taken verbatim from the shipped card rather than re-chosen here.**
Re-choosing the threshold would make this a new question wearing a validated question's clothes.

**Bar:** the same three-leg structure `MA28-CARD` passed, **stated field-by-field in the
declaration before the arm**. **One statistic, one bar** — `E-5`'s lesson: its **UNRESOLVED**
verdict came from a **conjunctive** bar, and this register will not repeat it.

**Explicitly NOT the object:** composite alpha. A distress instrument that improves crash ranking
without improving alpha is a **success** here, exactly as `MA28-CARD` was.

---

## §4 · GRAVEYARD

| row | what it says | how this register argues past it, or does not |
|---|---|---|
| `S10-ACCT` A1 | the flag **veto** REJECTED: excludes 5.74% of rows, alpha +0.1970pp, LS t 2.6199 → 2.7080, but max drawdown −0.280933 → −0.282016 — a **−0.1082pp** move against a **+2.0pp** bar | **this register does not propose a veto or any portfolio action.** It measures a rate |
| `S10` drawdown leg | portfolio drawdown spans **exactly ONE 63-day period on every arm — COVID 2020Q1** | **n = 1 for portfolio drawdown.** This is why the object is **name-level crash rate**, where n is name-quarters, not portfolio drawdown, where n is one |
| `MB8` | flags nearly **disjoint** from the book | a **book** fact. This register measures on the **flagged population**, not on the book |
| `E-5` | UNRESOLVED on a **conjunctive** bar; hazard decayed monotonically 9 of 9 | **one statistic, one bar** — §3 |
| `MB12` | orthogonality is not a motivation | not claimed — §2 |
| `R2` / `MB1` | options entry closed | not an entry signal — §2 |

---

## §5 · THE KILL THAT IS THE WHOLE REGISTER — coverage on the arm's own population

**`O-1` died because a chain-coverage figure measured on the ALERT BOOK (~75%) was applied to the
PANEL (5.89% actual, ~17×).** This register is exposed to precisely that error, in a place where
the two populations have **opposite** selection pressures:

* **Bond issuance skews LARGE-CAP** — bigger firms issue public debt.
* **`MA28` flags skew DISTRESSED** — and distress skews small.

**Nobody knows whether those overlap, and this draft does not guess.**

> **K1 · COVERAGE (FREE, fires before anything is scored).** Among **name-dates that `MA28`
> flags**, what fraction have **at least one TRACE-reported bond trade within the 63 sessions
> before the flag date**? **If that fraction is below 30%, the register STOPS, zero trials.**

**The figure must be computed on flagged name-dates, stated in the declaration, and never
substituted with a panel-wide or universe-wide coverage number.** A universe-wide figure would be
`O-1`'s mistake in a new costume.

**Three further free kills:**

| kill | fires when | cost | consequence |
|---|---|---|---|
| **K2 · STALENESS** | the median gap between the last bond trade and the flag date exceeds **21 sessions** on the covered set | FREE | the "market-implied" measure is not measuring the market at the flag date; STOP |
| **K3 · CROSSWALK** | CUSIP-9 → our names coverage on the covered set falls below **90%**, or `ticker_identity`'s `firstpricedate` audit finds an unresolvable collision | FREE | STOP — same instrument-zero risk as W-28's `K1` |
| **K4 · EFFECTIVE n** | after clustering by **name** (not name-quarter), the effective number of independent flagged episodes falls below the n the §6 MDE assumes | FREE | STOP and restate; `R3`'s measured design effect **2.2121** (**2.1837** split-clean, against a null p95 of 1.1898) is the precedent that clustering is not optional here |

**All four are free and all fire before a crash rate is read.**

---

## §6 · POWER — MB22, at both vocabularies

**The object is a RATE, so the vocabulary is a proportion, not an SD.** The declaration states
both of the following **before the arm**, using the census's own coverage counts:

* `MDE_50% = crit × se_p` and `MDE_80% = (crit + 0.84) × se_p`, with `crit = √(2·ln N)` and
  **N = 245 at the time of reading if run third this season** → `crit = 3.317004`, on the
  ledger-confirmed base of 242 (`WIDTH_AUDIT` §0.4). The declaration re-reads the counter and
  substitutes; **the Δ per trial is +0.0012 and does not depend on the base.**
* `se_p = √( p̄(1−p̄) · (1/n₁ + 1/n₂) ) × √deff`, where `p̄` is the pooled crash rate, `n₁`/`n₂`
  are the **covered flagged** counts in the two bond-spread groups, and **`deff` is measured by
  name-level clustering, not assumed** (`R3` measured **2.2121** on the options book, **2.1837** split-clean against a null p95 of 1.1898; the equity panel's
  own deff is 1.177 on dates).
* `required_n = ((crit + z_power)/effect)²`, with `effect` the **pre-declared** rate difference the
  register would call material.

**The anchor the declaration must beat, and it is demanding:** `S10`'s measured separation is
**2.660% against 0.874%** — a **3.04×** ratio on a **base rate under 1%**. **Rare-event rates need
large n, and the coverage kill decides whether n exists.** If the powered `required_n` exceeds the
covered flagged count, **the register states that and does not run** — `RUN_RULES` A-11.

> **Stated plainly: it is entirely possible that the honest arithmetic here says this register
> cannot be powered on the flagged names that have bonds. If so, that is the deliverable, it costs
> zero trials, and it is a better outcome than an underpowered arm.**

---

## §7 · DATA

**Tables the census must probe:**

| table | what it must return |
|---|---|
| `trace.trace_enhanced` | the enhanced file — **uncapped trade sizes, with a publication delay**; `cusip_id`, `trd_exctn_dt`, `rptd_pr`, `entrd_vol_qt`, and the **span** |
| `trace.trace_standard` | the standard file — capped sizes, shorter delay; same fields |
| a reference/master table | bond → issuer mapping, **coupon, maturity, seniority** — a spread needs a benchmark curve and a maturity |
| `crsp.stocknames` | `ncusip` ↔ `permno` for the equity leg |

**Two construction decisions frozen at declaration:**
1. **enhanced vs standard** — the enhanced file's publication delay must be checked against the
   flag date, or the measure is **not point-in-time**. *(`F-13`'s lesson: name the field and its
   direction in time.)*
2. **spread against what** — a stated benchmark curve, named in the declaration, not chosen after
   seeing dispersion.

**And one that cannot be frozen and so becomes a kill:** issuers with **many** bonds need an
aggregation rule (nearest-maturity? volume-weighted?). **The rule is declared before the arm; if
the census shows the choice materially changes the ranking, the register withdraws** rather than
picking the ranking it likes.

**Licensing fence:** WRDS is **research-only, never public**; raw rows never leave `D:\wrds`.

---

## §8 · TRIAL ACCOUNTING

**Zero trials by this draft.** **1 equity trial** if a crash-rate verdict is read.
If run after `W-28` and `W-1`: N **245 → 246**, hurdle **3.317004 → 3.318232** (Δ **+0.001228**).
**Four free kills fire first**, so the most likely outcome of this register is **zero trials and a
dated coverage refusal.**

---

## §9 · WHAT A KILL WOULD BUY

**`K1` firing is not a wasted session.** It would establish, with a number, that **market-implied
distress is unreachable for the names this project's distress flags actually catch** — which
closes the entire "external distress instrument" thread that `MA28`, `E-4`, `E-5`, `E-8` and
`X-SEED-1` all point at, **permanently and for free**, and removes the last reason to want IvyDB
back for this purpose.

**A dated, powered refusal is the second-best outcome available here, and it costs nothing.**
