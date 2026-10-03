# PREREG DRAFT — N8, SPIN-OFFS IN EVENT TIME

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Don's Addition 2 candidate.
**Not in the graveyard — no ledger row tests spin-offs.**

**SCOPE NOTE, AND IT SAVES A DRAFT: Addition 2 pairs spin-offs with "S&P 500 additions/deletions",
and THAT HALF IS ALREADY DRAFTED.** `PREREG_DRAFT_w17_spdji_index_events.md` (2026-08-28) designs
index add/delete **in event time**, declares itself a **CLOSURE PURCHASE** with a pre-committed
*"a null verdict CLOSES this thread permanently"*, and states its own prior as **LOW** because the
index-inclusion premium is *"the most-documented decayed anomaly in the equity literature"*.
**It has NO ledger row — it was never adjudicated.** The right action is to **adjudicate W-17 as it
stands, not to rewrite it**; this draft covers only the spin-off half, which W-17 does not.

---

## 1. MECHANISM

A spun-off subsidiary arrives in the market with no analyst following, forced selling from index
funds and parent-company holders who did not want it, and no natural shareholder base. The
documented consequence (Cusatis–Miles–Woolridge) is abnormal drift in **both** the child and the
parent over the following one to three years. **It is the purest form of the Roth thesis in Addition
2's list: the mispricing exists because institutions are structurally obliged to sell something
small, and a small book is under no such obligation.**

**ARM — ONE arm, in EVENT TIME.** Abnormal return of the **child** over a pre-committed window
after the distribution date, against a size-and-industry-matched control, on all spin-off events in
the owned window. One window, one matching rule, no sweep. **The parent leg is a declared secondary
and carries no verdict** — two legs would be two arms.

## 2. EVIDENCE *FOR*

* **THE EVENTS ARE IN OWNED DATA, DATED AND PAIRED, WITH NO PULL.** Censused read-only from the
  freeze's `bulk/actions.csv` (671,781 rows, 19 action types): **`spinoff` 565, `spunofffrom` 565,
  `spinoffdividend` 521.** The parent/child pairing is explicit in the two reciprocal codes, and
  `contraticker`/`contraname` carry the counterparty — so the event spine needs building but not
  buying.
* **It lives in the HIGH-POWER space.** `SEARCH_DOCTRINE` §1.4: the equity cross-section has an
  80%-power MDE of **0.4274–0.5071 SD** — about the largest effect the panel has ever held, i.e.
  nearly useless — while **event time** reaches **1.66pp at n_eff 400**, an order of magnitude
  better. A spin-off is **exogenous, dated and staggered**, which is exactly the shape event time
  needs. `SEARCH_DOCTRINE`'s own complaint is that **245 equity trials were spent in the weak
  space** while event time has one drafted register.
* **The mechanism is not a factor in disguise.** Unlike `N1`, `N5`, `N6` and `N7`, the return here
  is not a size, momentum or value tilt — it is a forced-seller event — so it is the one Part C arm
  whose result could not be restated as a factor loading.
* **The project already owns the machinery for event studies on this panel**: `E-5`'s hazard-curve
  library, `I-4`'s dated event spine, `EVOWN`'s `owns_the_event`, and `crsp_delist`'s terminal-value
  handling.

## 3. EVIDENCE *AGAINST* — AND THE FIRST POINT IS PROBABLY FATAL

* **565 EVENTS IS THE CEILING ACROSS THE ENTIRE FILE, AND THE USABLE COUNT WILL BE FAR SMALLER.**
  That 565 spans all of Sharadar's history and the whole universe. Restricting to the panel's own
  names, to the 2009–2026 window, and then to the small/mid-cap band leaves an **UNMEASURED** and
  certainly much smaller number — against event time's **n_eff 400** reference for a 1.66pp MDE.
  **This is the free kill in §5 and the honest prior is that it fires.**
* **A spin-off child is, by construction, a name the panel may not carry.** It is newly listed, has
  no fundamental history, and the composite's own eligibility rules — the 70% non-null rule, the
  two-year history conventions — will exclude exactly the names the hypothesis is about.
  **So the arm may be measuring the subset of spin-offs that are already seasoned**, which is the
  opposite of the population the literature describes.
* **`B6`'s lesson applies to a newly-listed population more than to any other.** A cohort of names
  that have just appeared is the shape most vulnerable to survivorship in either direction, and the
  register must use a **matched** forward window (`MC12` failed 13 of 14 years for want of one).
* **The matched control is the hard part and it is where the result will be decided.** A
  size-and-industry-matched control needs the industry classification `N6` documents — `co_hgic`
  from 1999, CRSP `siccd` before — and **`S25` measured 11.37% of covered names disagreeing with
  the panel's own sector today**, so the match is itself uncertain.
* **The literature's window is ONE TO THREE YEARS**, which is far longer than the 63-day forward
  return the panel carries. `S22` measured that the panel's alpha is still accruing at two years
  (+6.59% → +5.10% annualised), so long windows are measurable here — but they **overlap heavily**,
  and `MB21` established that overlapping windows need a persistence-preserving null
  (`valuation/studies/persistence_null.py`) rather than `placebo_panel`, which *"has no memory"*.

## 4. BAR AND MDE

**Two questions, two designs, per charter clause 4b.**

**(1) IS THE EFFECT REAL — event time, the primary.** Abnormal return of the child against the
matched control over the pre-committed window, with the **event** as the unit of independence and
within-episode residual correlation measured rather than assumed. Reference MDE **1.66pp at n_eff
400** (`DC-1` §7). **The register must state its realised n_eff before reading the effect.**

**(2) IS IT WORTH HOLDING — charter clause 1.** Only if (1) clears: a long-only book of recent
spin-off children inside the band, net of cost, vs the benchmark, built on **2009–2019 × half the
tickers** and checked **once** on **2020–2026 × the other half**.

Equity `N` **252**, hurdle **3.3254862** (derived). Every critical value on an event-time statistic
is **UNCALIBRATED** on this panel — `X7` calibrates cross-sectional LEVELS — and must be labelled
so, which is `V2G`'s and `R1-VAR`'s rule applied to a new space.

## 5. THE FREE PRE-OUTCOME KILL — READ FIRST, AND EXPECTED TO FIRE

**K1 (FREE, zero trials). The event census.** From `bulk/actions.csv`, with no returns joined:
how many `spinoff` / `spunofffrom` events fall inside the panel's window, on panel names, inside
the small/mid-cap band, with the child carrying enough post-event history for the declared window?

* **Usable events < 100** → the design cannot approach event time's power reference and the arm
  **closes at zero trials**.
* **Usable events < 400** → it is **UNDERPOWERED BY CONSTRUCTION** and must say so in advance,
  which is `O-1`'s pre-committed branch (*"if it lands below, the honest outcome is UNDERPOWERED and
  the trial still charges"*).
* **The ceiling is 565 across all of history**, so the register should price this as likely before
  running it rather than discovering it.

**K2 (FREE). Panel membership of the children.** The share of spin-off children that ever appear in
the panel at all. If most do not, the arm is about seasoned spin-offs and the register must rename
its own hypothesis.

**K3 (FREE). The `spinoffdividend` code is a THIRD object** (521 rows) and must be classified, not
pooled — `S25`'s rule that a transition needs **both** conditions, and `I-4`'s that an event code
decoded by name is not an event census.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT only if a book is adopted**; the event-time leg adopts nothing. Derive
the vintage; derived today **vintage 4, OPEN since 2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed
to Don.

**Owned data: YES for the event spine and the modern window** — ACTIONS is in the freeze and needs
no pull. **The matched control needs the industry route of `N6`**, and the pre-2009 eras would need
`crsp.dsf`/`msf` plus CRSP's own distribution codes, since Sharadar's ACTIONS history before 1998
is not the panel's price source.
