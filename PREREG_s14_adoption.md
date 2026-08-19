# PREREG — S14 ADOPTION: the no-trade band at width 0.30 enters live construction

**Committed ALONE, before any wiring code exists.** One `.md`, zero `.py`. This register fixes the
construction-fidelity gate, the vintage interpretation and the honesty surfaces **before** the
implementation that must satisfy them.

This is **not** a research register — nothing here is being measured for a verdict. S14's evidence
is already banked (session 35, double-cleared; the grid-boundary caveat discharged by S14-WIDTH).
Don has adopted. What this register binds is **whether the thing that ships is the thing that was
measured**, which is the B7 failure mode and the only way this adoption can go wrong.

---

## 1 · DON'S DECISION, VERBATIM

> **DON HAS ADOPTED S14 - the no-trade band at width 0.30.**
>
> Adopted on S14's double-clear (sessions 35 + S14-WIDTH).

Recorded 2026-08-13. The decision is Don's; this lane executes it and does not re-litigate it.

**What the evidence says, quoted whole so the adoption is not oversold:**

* Session 35, sweeping the shipped width grid on a decide half and measuring the argmax on the
  held-out half, **both directions picked 0.30 and both cleared**: net alpha **+1.78pp** and
  **+1.77pp**, gross alpha **+1.02pp** and **+0.77pp**, measured cost saving **+0.76pp** and
  **+1.00pp**. Turnover roughly **halves** (2.6078 → 1.3514; 2.5800 → 1.4198).
* **Roughly half the gain is a SIGNAL effect, not a cost effect** — gross alpha improves, so the
  register's original "pure cost saving, makes no signal claim" framing was wrong and session 35
  corrected it against itself. Holding a name until it leaves the top 30% rather than the top 10%
  stops the book churning on rank noise.
* **S14-WIDTH discharged the grid-boundary caveat**: given 0.40 / 0.50 / 0.75 to choose from, both
  halves still picked **0.30**, so the optimum is interior and the knee is identified.
* **The caveat that travels with it:** the knee replicates in **location** but not in **sharpness**
  — decisive on the late half (0.30 → 0.75 costs 3.59pp), nearly flat on the early half (0.75 is
  second best, 0.14pp below the peak).

---

## 2 · THE CONSTRUCTION FIDELITY GATE — stated before the implementation exists

**THE BAR, fixed here, with zero free parameters** (Don specified it; there is nothing to tune):

> Apply the **LIVE** book-construction entry point to the panel's **most recent cross-section**
> and reproduce the **measured arm's** book **NAME-FOR-NAME**. Exact set equality. Not "mostly",
> not "within tolerance" — a single name of difference FAILS.

**Why exact and not approximate.** A band that differs from the measured band is a *different
construction wearing a validated construction's evidence* — precisely the B7 disease this project
has already paid for once. There is no tolerance at which a wrong band becomes acceptable, because
the number being borrowed (+1.78pp held out) describes the measured band and nothing else.

**The check must run the LIVE entry point, not the rule in isolation.** A test that calls the same
function with the same arguments passes by construction and proves nothing. The gate earns its keep
only if it exercises the path a real scan takes, so that it fails on **wiring** drift:

* the band silently not applied at all (**today's actual state** — see §3);
* the wrong width reaching the rule;
* the wrong denominator (book size vs universe size) behind the exit rank;
* the held-set not threaded through, which degrades the band to plain top-N **silently**.

**If the gate fails, the adoption does not ship.** The failure is reported with the diff, and the
live path is fixed until it reproduces — the measured arm is never adjusted to meet the live path.

---

## 3 · A FINDING RECORDED BEFORE IT CAN BE MISTAKEN FOR A DESIGN CHOICE

The S14 ledger row states: *"the band is ALREADY LIVE in the taxable configuration, so an adopt
would change the DEFAULT rather than introduce the band."*

**That is FALSE, and it was verified false before this register was written.** `exit_frac` is
consumed live in exactly three places and **none of them apply it**:

* `valquo_index.py:306` — writes it into the payload as metadata;
* `valquo_index.py:358` — prints it in the CLI banner;
* `web/app.py:331` — displays it.

The only code that has ever *applied* a band is `fundamental_panel.turnover_and_costs` (the
backtest) and the two S14 measurement scripts. `build_index` is a pure top-N selection with **no
band and no notion of a held name**, and `valquo_index.py:298-310` says so in a comment: the band
"requires the PREVIOUS book, so it is applied at rebalance time, not in this snapshot" — and it is
emitted as an *instruction for a human rebalancer* rather than executed.

**Consequence for this task, which is why it is registered rather than noted afterwards:** adopting
S14 is **wiring the band into live construction for the first time**, not flipping a default. It is
a larger change than the ledger implies, the fidelity gate is therefore load-bearing rather than
ceremonial, and the `taxable` config's declared 20% band has never affected a book anyone received.

---

## 4 · THE VINTAGE INTERPRETATION — derived from the register, not assumed

Per the **PT-GAPDUE** rule the current vintage is derived, never assumed. Derived at the time of
writing: `track_meter.current_vintage()` returns **vintage 3, opened 2026-08-11, status OPEN**;
today is **2026-08-13**, so vintage 3 has accrued **2 complete days**.

`PREREG_fidelity2_rebuild.md` §4 registered the only exception to Amendment 1, and it is explicitly
self-limiting:

> An adopted change made while the current vintage has accrued **ZERO complete days** AMENDS that
> vintage instead of opening the next. … **The moment vintage 3 has accrued one complete day, this
> clause stops applying and Amendment 1's ordinary rule resumes.**

Vintage 3 has accrued two complete days, so **the amendment clause does not apply** and Amendment
1's ordinary rule governs: **vintage 4 OPENS, dated 2026-08-13.** This agrees with Don's
instruction, and it is recorded as a derivation so that the agreement is checkable rather than
coincidental.

**Rule 6 is paid in full and is not hidden:** opening vintage 4 **resets the accrued forward clock
to zero** and buys nothing statistically. Vintage 3's two days are spent. That is the price of an
adoption, it was Don's to pay, and V1's shadow machinery is the only thing that recovers any of it.

---

## 5 · THE SHADOW — what is compared against what

Vintage 3 (**band-less**, seven live themes) becomes the shadow predecessor and keeps being scored
on the same dates, so the adoption is **forward-measured from day one** and the market risk that
dominates a vs-SPY test cancels in the pair.

**Pre-committed so it cannot be read as a disappointment later:** a shadow pair that has not crossed
is the **EXPECTED** outcome and is **NOT** evidence the adoption was worthless. `verdict()` already
carries that sentence in its own output. The band changes the book only where a held name sits
between rank 10% and rank 30%, so early divergence will be **small by construction**.

---

## 6 · WHAT SHIPS, AND WHAT DELIBERATELY DOES NOT

**Ships:** one constant in one module, imported by both the measured path and the live path, so the
rule cannot be re-derived in a second location and drift (the publication-consolidation lesson).

**Does NOT ship, stated now so its absence is not read as an oversight:**

* The **backtest headline is not re-run and not restated.** The published figures describe the
  validated composite; where the live book now differs, the surfaces must say so rather than
  quietly re-pointing the headline at a construction it did not measure.
* **No re-tuning of anything.** Width 0.30 is adopted as measured. No grid, no second look.
* **Equity `N` is unchanged.** An adoption searches nothing; S14 and S14-WIDTH were charged when
  they ran.

---

## 7 · EXPECTATIONS, written down first because they keep being wrong

1. The fidelity gate **passes on the first honest attempt** — 40/60. The book-size rule differs
   between paths (`int(round(...))` with a `MIN_NAMES` floor live vs `int(...)` in the panel), and
   that is exactly the kind of detail that fails a name-for-name check.
2. The live book on the current cross-section **changes by fewer than 20% of its names** when the
   band is applied to a real previous book — 70/30.
3. At least one **further defect** is found in the live path while wiring it — 60/40, on this
   project's record.
