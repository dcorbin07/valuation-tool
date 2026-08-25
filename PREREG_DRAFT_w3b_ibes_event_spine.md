# PREREG DRAFT (SKETCH) — W-3b: THE EARNINGS-DATE SPINE, REPAIRED
## `I-4` v2 — an INSTRUMENT, zero trials, and the largest blast radius in the WRDS map.
## Tags: [`I-4` (built on Sharadar code-22) · `S17`/`SC-2` (the legend, 1.65 events/ticker-yr)
## · `O6`/`O7`/`O17`/`O24`/`EVOWN` · `F-4`/`F-12`/`F-13` (fleet books that skip unknown events)]

**DRAFT, Frontier Scout lane, 2026-08-24.** Census-gated. **Trials: 0 — FIXED-class**
(an instrument with no hypothesis and no bar, on the `I-1`/`I-4`/`MB22` precedent). Commit ALONE.

## 1. The defect, stated precisely

`I-4` is the project's single earnings-date table and it rests on Sharadar EVENTS **code 22**,
which `SC-2`'s legend work measured at **~1.65 events per ticker-year against the ~4 a
quarterly calendar implies**, with the relayed census figure that **29 of 186 optionable names
carry ZERO coverage**. The analyses built on it are honest — every one treats a missing date as
**unknown** and counts it (`F-4`/`F-12`/`F-13` skip-and-count by declaration). **So this is a
hole in the instrument, not an error in the results** — and it silently shrinks every
event-conditioned universe, which is exactly the failure `RUN_RULES` A-10 exists to surface.

## 2. What is built

A second, independent, announcement-dated source from **IBES actuals** (`anndats`, and
`anntims` where present), joined to the panel through `ibcrsphist`, and **merged into `I-4`
under an explicit precedence rule fixed here: IBES `anndats` where present; Sharadar code-22
where IBES is absent; every row stamped with its source.** Never a silent union — `MB15`'s
vacuous-vs-passing rule travels: a date that came from neither source stays **unknown** and is
counted, never imputed from cadence (`S3-I6`'s guidance table may CONFIRM a date, never supply
one — `F-13`'s declaration already forbids it).

## 3. Validation before any consumer (the `MB15`/`MB16` order)

* **V1 — agreement:** on names covered by BOTH sources, the two dates agree within ±1 session
  on ≥95% of pairs. **The disagreement set is the deliverable either way** (`W-6`'s shape):
  ours wrong → a correction with its blast radius named (every study that used those dates);
  agreement → the first external validation `I-4` has ever had.
* **V2 — coverage:** the before/after coverage table, per name and per year, **including the
  29**. If IBES does not materially cover them, that is the finding and the spine stays as-is.
* **V3 — reproduction:** `I-4`'s existing consumers (`O6`/`O7`'s banked earnings joins — which
  `I-4` already reproduces exactly) must reproduce **bit-identical on the unchanged rows**, so
  the repair is provably additive. Count-gated (`MB21` C1).
* **V4 — PIT:** `anndats` is the announcement date; any use of `anntims`/pre-announcement
  fields that could leak is AST-pinned out (`MB18`'s idiom).

## 4. What it unblocks (the reason it is recommended first)

Every event-conditioned options study's "unknown" partition shrinks; `F-4`'s event-free
screen stops discarding tradeable names for want of a date; `F-12`/`F-13` gain eligible
population (`F-13`'s both-dates-known constraint is its declared starvation risk and this is
the only thing that relieves it); and `EVOWN`'s ambient finding gains a cleaner denominator if
anyone re-reads it. **No verdict moves and none may** — this register ships an instrument.

## 5. Void conditions and fence

Void: imputing any date; silent union without source stamps; changing any published verdict on
the strength of the repair (a re-read is a new register with its own charge); shipping IBES
values in the product. **Fence:** research-only, aggregates and dates banked as derived rows,
raw IBES never leaves `D:\wrds`, and the dates themselves are treated as licensed content —
they inform internal joins, they do not render publicly.

## 6. Expectations

(1) V1 agreement ≥95% — 70/30. (2) IBES covers ≥20 of the 29 zero-coverage names — 65/35.
(3) The disagreement set contains at least one date our studies used and IBES contradicts —
55/45. (4) No published verdict needs revision as a result — 75/25.
