# PREREG DRAFT — N6, INDUSTRY MOMENTUM

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Don's Addition 2 candidate.
**Not in the graveyard — no ledger row tests industry or sector momentum. But it sits next to the
most comprehensively closed thread in the record, and that proximity is the whole problem.**

---

## 1. MECHANISM

Industries, not just stocks, exhibit return continuation: an industry that has outperformed tends
to keep outperforming over the following months, and a large part of individual-stock momentum is
industry momentum in disguise (Moskowitz–Grinblatt). The tradeable form is to tilt toward names in
industries with strong trailing returns.

**ARM — ONE arm.** A long-only book inside the N1 small/mid-cap band, selected on the **trailing
industry return of the name's own industry**, at the served construction's weighting, 8% cap, 0.30
band, quarterly rebalance. One pre-committed lookback, one pre-committed industry definition, no
sweep over either.

## 2. EVIDENCE *FOR*

* **A POINT-IN-TIME INDUSTRY CLASSIFICATION NOW EXISTS, AND IT DID NOT WHEN SECTOR WORK WAS CLOSED.**
  `S25` closed **UNOBTAINABLE-WITHOUT-NEW-DATA** in session 29 — *"no point-in-time sector map is
  buildable from anything in this repository"* — and then **re-opened on its own named exit
  criterion** when `comp.co_hgic` turned out to be entitled and **dated**: 45,836 rows over 32,012
  gvkeys with `indfrom`/`indthru` ranges, **94.8% of panel tickers**, 3,853 dated spans, and
  **992 names (42.9%) reclassified at least once**. `valuation/edge/sector_map.py` ships it with a
  look-ahead refusal and 34 tests.
* **AND FOR THE PRE-2009 ERAS THERE IS A SECOND, FREE, GENUINELY POINT-IN-TIME ROUTE THE RECORD HAS
  NEVER USED: CRSP's own `siccd`, carried IN the dated name history.** `crsp.stocknames` and
  `dsenames` both carry **`siccd` inside `namedt`/`nameenddt` intervals** — so the industry as of a
  historical date is readable directly, with no crosswalk and no vendor snapshot. **`co_hgic` starts
  1999-06-30 and cannot date 1972–1998; CRSP's `siccd` can.** That is the single most useful thing
  in this draft.
* **Momentum is an incumbent theme that WORKS on this panel**, so the industry version is not a
  speculative axis: `momentum` carries theme IC *t* **+1.31** with three z-columns, and `R1`'s
  corrected re-run found **UMD loading at +0.205, *t* +3.65** — one of only two factors the book
  genuinely loads on.

## 3. EVIDENCE *AGAINST* — AND IT IS THE HEAVIEST OBJECTION IN ADDITION 2's LIST

* **SECTOR-NEUTRAL IS THE MOST THOROUGHLY CLOSED THREAD IN THE RECORD, AND IT WAS CLOSED THREE
  TIMES.** `SECTOR-NEUTRAL-B6` rejected it twice on measurement in both held-out directions, named
  **exactly two routes back** — `S25` (a dated map) and `S15` (sector-relative on the value theme
  alone) — and `S15` was then **rejected** while `W-1` closed the `S25` route by *meeting its own
  re-open condition and finding the answer unchanged*: Δalpha **−1.01pp** on the point-in-time map
  against **−1.09pp** on today's sectors, i.e. **the look-ahead was never what was killing it.**
  **So a dated industry classification has ALREADY been built and ALREADY failed to rescue a
  sector-based intervention on this book.**
* **The material difference must be stated precisely or this arm should not run.** Sector-NEUTRAL
  *removes* industry exposure by demeaning within group; industry MOMENTUM *takes* industry
  exposure deliberately. They are opposite interventions on the same classification, and `W-1`
  tested the removal, not the taking. **That is a real distinction — and a reader is entitled to
  note that the only thing the record has measured about this classification is that using it did
  not help.**
* **It is probably momentum twice.** Moskowitz–Grinblatt's own point is that individual momentum
  *is largely* industry momentum, and `momentum` is already a weighted theme with `ret_12_1`,
  `ret_6_1` and `high_prox`. **`S7`/`S18` ran six interaction arms and rejected all six**, and
  `E-1` withdrew on a **costume** kill at 0.6114 against `size` without running its arm. A
  pre-committed costume bar against the incumbent `momentum` theme is mandatory (§5, K2).
* **`co_hgic` does not reach the first era**, and SIC-vs-GICS is **not the same taxonomy** — `S25`
  measured **11.37% of covered names disagreeing with the panel's own sector TODAY**, and warns that
  a SIC-derived map *"changes point-in-timeness AND taxonomy at once"*. **So the 1972–1989 era and
  the modern period would be scored on different industry definitions**, which the register must
  declare as a limitation rather than discover.
* **GICS itself changed inside the window** — Real Estate separated in 2016, Communication Services
  created in 2018 — and `S25` measured **1,403 firm reclassifications against 74 and 62 taxonomy
  ones**. An industry-return series computed naively across those dates has a discontinuity that
  looks like a return.

## 4. BAR AND MDE

**Bar: charter clause 1**, built on **2009–2019 × half the tickers**, checked **once** on
**2020–2026 × the other half**, against the served book's **+1.9488pp/yr** and recent-half
**+0.2702pp**.

**MDE.** Industry momentum has a natural event-time form only weakly (industries do not announce),
so this is a **cross-sectional** arm in the weak space: `SEARCH_DOCTRINE` §1.4's **0.4274–0.5071 SD**
applies to any incremental leg and the register must say that leg is near-useless. The book leg
derives its MDE from realised tracking error. Equity `N` **252**, hurdle **3.3254862** (derived).

## 5. THE FREE PRE-OUTCOME KILLS

**K1 (FREE). The classification must be point-in-time and it must be provably so.** Reuse
`sector_map.py`'s existing look-ahead refusal — a date predating a name's first classification
returns `NOT_COVERED` and **never** the first span — and for the pre-1999 eras, build from CRSP
`siccd` **inside** the dated name interval, with the same refusal and a **positive control** so the
guard cannot pass by refusing everything (`S25`'s own design).

**K2 (FREE, and the one most likely to fire). The momentum costume.** Mean per-date |rho| between
the industry-momentum score and the incumbent **`momentum` theme**, against **`E-1`'s own 0.60 bar
reused verbatim**. Above it the arm **withdraws without running**, which is exactly what `E-1` did
at 0.6114.

**K3 (FREE). Taxonomy revisions must be separated from firm reclassifications** before any industry
return is computed, using `sector_map.classify_transition`, which `S25` built and which requires
**both** the date window **and** the destination code — because `S25` measured that *"either alone
over-claims"*.

**K4 (FREE). Group sizes.** Minimum names per industry per date, against a pre-committed floor.
`W-1` measured its own minimum sector group at 21 names with 11 sectors; a small-cap band split into
industries will be thinner, and an industry return computed on three names is noise with a label.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption.** Derive it; derived today **vintage 4, OPEN since
2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES for the modern period** — `sector_map.py` plus `co_hgic` (already pulled to
`D:\wrds` per `S25`, raw rows staying there). **YES for the pre-2009 eras too, via CRSP `siccd` in
the banked `stocknames`/`dsenames`** — which is free, already on disk, and needs no new pull.
**NO single taxonomy spans both**, and that is the limitation to declare.
