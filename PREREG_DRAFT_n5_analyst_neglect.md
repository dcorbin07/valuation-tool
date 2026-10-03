# PREREG DRAFT — N5, ANALYST NEGLECT / LOW COVERAGE

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Don's Addition 2 candidate.
**Not in the graveyard — checked: no ledger row mentions neglect, coverage-as-a-signal, or
`numest`, and `D6`/`D6-REG` used IBES for REVISIONS, never for COVERAGE COUNT.**

---

## 1. MECHANISM

The number of analysts following a firm is a measure of how much attention the market pays it.
Neglected firms are plausibly mispriced for longer because fewer people are looking, and the
premium for holding them is compensation for bearing an information cost that a patient
long-horizon holder does not actually pay. It is the classic neglected-firm effect, and it is the
**purest statement of the Roth book's structural advantage**: the edge exists *because*
institutions cannot be bothered, and a small book can be.

**ARM — ONE arm.** A long-only book inside the N1 small/mid-cap band, selected on **low analyst
coverage** — `numest` from IBES `statsum_epsus` at the most recent summary date strictly before the
rebalance — at the served construction's weighting, 8% cap, 0.30 band, quarterly rebalance. One
pre-committed coverage threshold, no sweep.

## 2. EVIDENCE *FOR*

* **The data is banked, deep, and free of a pull.** `ibes_statsum_epsus` holds **15,029,492** rows
  spanning **1976–2026**, which is both the summary file `numest` lives in and a span that reaches
  **both pre-2009 eras**. `ibes_id` (308,801) carries the identifier spine.
* **It is a genuinely NEW axis on this panel.** Every IBES item the project has run — `D6`,
  `D6-REG`, `W-3b` — used **estimates and actuals**. **Nobody has used the COUNT.** The graveyard's
  closure of the revision family (§3) therefore does not reach it.
* **It is a cleaner statement of the capacity thesis than anything else in Part C.**
  `INDEX-BOOK` measured that **−4.1785pp/yr** of the tier gap is *"the small-cap premium the tier
  declines to hold"*, and `P2` put the crowding point at a **$5.1B cohort** — not binding at Roth
  size. Low coverage is the *mechanism* behind that premium rather than a proxy for it.
* **`U7` measured the compression that neglect escapes**: inside 187 megacaps *"the other themes
  are compressed and `size` dominates"*. Coverage is the variable that distinguishes a crowded
  cross-section from an uncrowded one.

## 3. EVIDENCE *AGAINST*

* **It is probably a size proxy, and `size` is already the load-bearing theme.** Coverage
  correlates strongly and mechanically with market cap. `X3` measured that `size` has the **worst**
  theme IC (**−0.30**) and carries the composite's **entire** statistical significance — so a
  coverage signal risks being `size` under a new name. **`R6`, `U7` and `S10` were each decided by
  exactly this failure mode**, and `R6`'s own **0.60** bar on mean per-date |rho| against `size` is
  reused verbatim as this arm's kill (§5, K2).
* **The revision family is closed and the closure is nearby.** `D6-REG` was rejected on both bases
  at **0.0867 SD against an MDE80 of 0.4274** — *"0.2× detection on the best-covered incremental
  register ever run"*. Coverage count is a different variable, but it is the same file and the same
  panel, and the honest prior from that result is poor.
* **Five structurally-orthogonal candidates have now been confirmed orthogonal and predicted
  nothing** (`U2`, `MA31`/`MA32`, `MA58`, `MB18`, `D6`), with R² between 0.027 and 0.145.
  `CLAUDE.md` names that motivation as one *"nobody should run again"*. **If this arm's case rests
  on "coverage is new information", it is the sixth member of that family and should be declined.**
  Its case must rest on the capacity mechanism instead.
* **The cross-section is the weak space.** Per `SEARCH_DOCTRINE` §1.4 the 80%-power MDE there is
  **0.4274–0.5071 SD**, approximately the largest effect the panel has ever held. A coverage tilt is
  a cross-sectional signal with no natural event, so **it cannot be moved into the high-power
  event-time space**, unlike `N3` or `N8`. That is the strongest structural reason to rank it below
  the event-time arms.

## 4. BAR AND MDE

**Bar: charter clause 1** — net-of-cost return vs SPY, long-only, Roth, built on **2009–2019 × half
the tickers** and checked **once** on **2020–2026 × the other half** per Addition 2, measured
against the served book's **+1.9488pp/yr** and recent-half **+0.2702pp**.

**MDE.** Row set changes, so no paired SE. Derive from the arm's own realised tracking error against
the benchmark. The cross-sectional MDE of **0.4274 SD** applies to any *incremental-IC* leg and the
register should state that such a leg is **near-useless here by construction**. Equity `N` **252**,
hurdle **3.3254862** (derived).

## 5. THE FREE PRE-OUTCOME KILLS

**K1 (FREE). Coverage of the coverage variable, inside the band.** Per date, the share of band names
with a `numest` reading on a summary date strictly before the rebalance. Below the 70% rule → no
book, closes at zero trials. **And the IBES↔CRSP/Sharadar identifier link must be censused here**,
not assumed: `ibes_id` is the spine and the link is the same `ncusip`-based problem Part B §2
documents.

**K2 (FREE, and the one most likely to fire). The size costume.** Mean per-date |rho| between
`numest` and the `size` theme, against **`R6`'s own 0.60 bar reused verbatim**. Above it, the arm
**withdraws** rather than being scored — `R6` withdrew on exactly this test at 0.6114 and did not
run its arm.

**K3 (FREE). Zero-coverage names must be counted and classified, never read as "maximally
neglected".** A name with no IBES record may be uncovered or may simply be unlinked, and treating
an identifier failure as an economic signal is `W-28`'s wrong-object family. `MC12`'s rule: a
missing row is a fact about the export, not about the firm.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption.** Derive it; derived today **vintage 4, OPEN since
2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES, entirely** — `ibes_statsum_epsus` and `ibes_id` are banked, spanning 1976–2026.
No pull, no purchase. **And because IBES reaches 1976, a survivor is testable in BOTH pre-2009
eras**, which is a real advantage over `pead_car`-based designs.
