# S25 — THE GICS → PANEL SECTOR CROSSWALK, DECLARED BEFORE IT IS BUILT

**Dated 2026-08-25, options-live lane. ZERO TRIALS.** This document is committed **BEFORE** any
crosswalk code exists and before any figure it produces is read. It is not a hypothesis and it
carries no bar: it is an INSTRUMENT declaration, on the `I-2`/`I-3` precedent.

**WHY IT IS WRITTEN FIRST.** A crosswalk chosen after seeing which mapping flatters a result is
the failure this project names more often than any other. Eleven GICS sectors and eleven
panel sectors admit many mappings; the one below is fixed now, in the open, with a reason per
cell, so that no later number can have chosen it.

**NO RANKING ARM RUNS IN THIS PASS.** `SECTOR-NEUTRAL-B6` was REJECTED TWICE on measurement,
and `S25` was only one of its two named routes back. **A dated map removes the DATA objection
and does not touch the REJECTION.** Re-opening it needs its own blind register and its own
trials, and is not proposed here.

---

## 1. What is being mapped, and onto what

**SOURCE: `comp.co_hgic`.** 45,836 dated rows over 32,012 gvkeys, `indfrom` / `indthru`,
`indfrom` spanning 1999-06-30 → 2026-08-24. Coverage of our universe **2,403 of 2,531 = 94.9%**,
with **1,007 of 2,403 (41.9%) reclassified at least once**. Eleven `gsector` codes.

**TARGET: the eleven strings the ENGINE is keyed on** — and the target is chosen by the
consumer rather than by taste. `assumptions.SECTOR_TARGET_MARGIN` and `comps.SECTOR_MULTIPLES`
are both dicts whose keys are exactly:

    Basic Materials · Communication Services · Consumer Cyclical · Consumer Defensive ·
    Energy · Financial Services · Healthcare · Industrials · Real Estate · Technology ·
    Utilities

**A mapping onto anything else would not be usable by the thing it exists to repair.** Measured
from the source: `SECTOR_TARGET_MARGIN` runs **0.10 (Consumer Cyclical) → 0.27 (Technology)**,
a **2.70× spread**, and `SECTOR_MULTIPLES` runs PE 12 → 30 and EV/Sales 0 → 8.0.

**BOTH DICTS FAIL OPEN, and that is measured rather than assumed:**
`SECTOR_TARGET_MARGIN.get(cd.sector, 0.12)` and `SECTOR_MULTIPLES.get(cd.sector, _DEFAULT)`. An
unmapped or empty sector is **silently given 0.12 and a default multiple** — so a crosswalk
that returns nothing is not neutral, it is a vote for the middle. The instrument therefore
reports UNMAPPED as its own state and never as a blank.

## 2. THE CROSSWALK — eleven cells, each with its reason

| GICS | name | → panel | why this cell |
|---|---|---|---|
| 10 | Energy | **Energy** | Same concept and near-identical constituent definition; no boundary dispute. |
| 15 | Materials | **Basic Materials** | Same concept under two vendors' names. Yahoo prefixes "Basic"; the constituent definition (chemicals, metals, mining, paper) is the same. |
| 20 | Industrials | **Industrials** | Same name, same concept — capital goods, transport, commercial services. |
| 25 | Consumer Discretionary | **Consumer Cyclical** | Yahoo's "Cyclical" IS the discretionary bucket; the names differ, the intent does not. **This is the cell where MEMBERSHIP diverges most** — see §3. |
| 30 | Consumer Staples | **Consumer Defensive** | Yahoo's "Defensive" IS the staples bucket. Same caveat as 25: the pair is right, the boundary between them is drawn differently. |
| 35 | Health Care | **Healthcare** | Same concept; the only difference is a space. |
| 40 | Financials | **Financial Services** | Same concept. Note the interaction with 60 below: before 2016 GICS 40 CONTAINED real estate. |
| 45 | Information Technology | **Technology** | Same concept. **GICS 45 is NARROWER than Yahoo's Technology** — see §3. |
| 50 | Communication Services | **Communication Services** | Same name and, post-2018, the same concept. Before 2018 GICS 50 was "Telecommunication Services", a much narrower bucket — see §4. |
| 55 | Utilities | **Utilities** | Same concept; no dispute. |
| 60 | Real Estate | **Real Estate** | Same concept. **Did not exist before 2016** — see §4. |

**IT IS 1:1 AT THE LABEL LEVEL AND THAT IS THE EASY HALF.** Every GICS sector has exactly one
natural panel counterpart and vice versa; no cell requires a judgement call about WHICH bucket,
only about whether the buckets contain the same firms. They do not.

## 3. WHAT THE CROSSWALK COSTS, AND IT IS DECLARED AS A COST RATHER THAN DISCOVERED AS A FINDING

**The labels map 1:1; the MEMBERSHIP does not.** Yahoo files Alphabet and Meta under
Communication Services and Amazon under Consumer Cyclical, and GICS agrees today — but Yahoo
has historically filed several large names under Technology that GICS 45 excludes, and the
Discretionary/Staples line is drawn differently by the two vendors.

**SO THE INSTRUMENT MUST MEASURE ITS OWN DISAGREEMENT AND REPORT IT BEFORE ANY CONSUMER USES
IT.** On TODAY's date both labels are observable for every covered name, so the disagreement
rate is directly measurable and is **pre-committed here as a required output**:

    taxonomy_disagreement = share of covered names where crosswalk(GICS today) != panel sector

**THIS NUMBER IS NOT A DEFECT AND MUST NOT BE READ AS ONE.** It is the price of expressing one
vendor's opinion in another's vocabulary. It is required because **without it, a repair that
changes a name's sector cannot be attributed** — the change could be look-ahead being fixed, or
it could be the taxonomy switch, and those are different things.

### THE DECOMPOSITION, FIXED NOW SO IT CANNOT BE CHOSEN LATER

Two separable effects, and the repair is only the second:

* **TAXONOMY EFFECT** — `crosswalk(GICS today)` vs `panel sector today`. Pure vendor
  disagreement. **Contains no point-in-time information at all.**
* **POINT-IN-TIME EFFECT** — `crosswalk(GICS at as_of)` vs `crosswalk(GICS today)`. **This is
  the look-ahead**, measured within ONE taxonomy so the crosswalk cancels exactly.

**TWO REPAIR VARIANTS WILL BE BUILT AND BOTH REPORTED, LABELLED:**

* **REPAIR-A (CHANGE-ONLY), the primary.** Override the sector **only where GICS records a
  reclassification** between `as_of` and today; otherwise keep the panel's own sector. **The
  crosswalk's disagreement cancels by construction**, so what moves is look-ahead and nothing
  else. This is the honest repair.
* **REPAIR-B (FULL), reported as a sensitivity and carrying NO verdict.** Use
  `crosswalk(GICS at as_of)` for every covered name. It fixes look-ahead **and** switches
  taxonomy in one step, so its total is confounded by construction and is quoted only beside
  the taxonomy disagreement that explains most of it.

## 4. GICS CHANGED INSIDE THE WINDOW — TAXONOMY REVISIONS ARE NOT CORPORATE EVENTS

**Two revisions move every firm in a group on ONE date and would read, in a naive event study,
as a wave of simultaneous reclassifications:**

* **REAL ESTATE (60) separated from Financials (40), 2016.** Every real-estate name's `indfrom`
  moves on essentially one date, and none of them did anything.
* **COMMUNICATION SERVICES (50) created, 2018**, by moving names out of Information Technology
  (45) and Consumer Discretionary (25). Before this, 50 was "Telecommunication Services".

**THE INSTRUMENT FLAGS THESE AND NEVER SILENTLY ABSORBS THEM.** Every dated transition carries
a `revision` field — `TAXONOMY_REVISION` or `FIRM_RECLASSIFICATION` — decided by whether the
transition's date falls in a known revision window AND matches that revision's code pattern.
**A consumer treating `indfrom` as an event date without reading that field is measuring an
index provider's paperwork.** This is `I-4`'s codes-34/35 sunset lesson in a new table: a
vendor-side definitional change that looks like data.

**THE FLAG IS DECLARED AS DIAGNOSTIC, NOT AS A FILTER.** The instrument does not delete
revision transitions — for the VALUATION repair a revision is a real change in which margin a
name is scored against, whatever caused it. It labels them so an event study cannot count them
and so the repair can report how much of its own movement is revision-driven.

## 5. THE JOIN IS DATE-SCOPED, AND TICKER REUSE IS THE KNOWN HAZARD

`crsp.ccmxpf_lnkhist` is **DENIED** on this account, so the link runs `ticker → gvkey` through
`comp.security.tic`. **A ticker is reused across companies over time** — the data-miner lane
measured 1,053 matched tickers mapping to more than one permno on the CRSP side, which is
`S3-I5`'s reuse problem in a different table.

**PRE-COMMITTED HANDLING:** where one ticker maps to more than one gvkey, the instrument
**REFUSES the name rather than picking one**, records it as `AMBIGUOUS_TICKER` with the
candidate gvkeys, and reports the count. **A silently-picked gvkey is a wrong company's sector
history wearing the right ticker**, and on a 2009 row nothing downstream could detect it. The
refusal is the safe direction and its cost is reported as reduced coverage.

## 6. WHAT THIS PASS WILL AND WILL NOT DO

**WILL:** build the dated map; report coverage, taxonomy disagreement, revision-vs-firm
transition counts, and ambiguous-ticker refusals; measure what REPAIR-A and REPAIR-B move on
the **banked** valuation panel; ship tests.

**WILL NOT:** run any ranking arm; re-open `SECTOR-NEUTRAL-B6`; change any live scoring path;
charge any trial; or quote any figure before 1999-06-30, **because GICS did not exist** and
`co_hgic` cannot date a sector there. Our 69-date panel starts 2009-01-15 and is inside the
covered span; `S23`'s valuation path reaches 1998 and **is not repairable for its earliest
rows**, which is a limit of the source and is reported rather than papered over.

**VOID CONDITIONS.** Changing the crosswalk after reading any repair figure; quoting REPAIR-B's
total without the taxonomy disagreement beside it; reading `indfrom` as an event date without
the `revision` field; or presenting any of this as evidence about sector-neutral ranking.
