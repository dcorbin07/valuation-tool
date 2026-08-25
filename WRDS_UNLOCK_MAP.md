# WRDS_UNLOCK_MAP.md — **v2, REDRAWN 2026-08-24 against the official subscription list**
## Frontier Scout. v1 (commit `1675a30`) was built on the commissioning brief's guesses;
## four of its seven seeds are void. v1 is superseded, not deleted — §1 is its death ledger.

**Census-conditional throughout:** every entry reads "IF `WRDS_CENSUS.md` confirms ⟨product,
fields, span⟩ THEN ⟨what reopens⟩". No outcome statistic was computed anywhere in this file.
`WRDS_CENSUS.md` does not exist on `origin/main` at this writing — nothing below is confirmed.

**THE LICENSING FENCE (inherited verbatim by every sketch):** research-only under the
institution's subscription. Never in the product, never on a public page, never feeding a live
score. **Raw rows never leave `D:\wrds`**; registers bank derived aggregates only. The repo is
PUBLIC — `D:\wrds` joins `.gitignore`'s licensed-data class **before** the first pull, not after
(`DATA-HISTORY`'s lesson, applied in advance).

**Counters:** equity ~242 (hurdle **3.3133**), options **307** (305 was a mid-session read,
corrected on landing), infra ~20 — re-read at run (`MA37`).

---

## 1. THE DEATH LEDGER — v1's entries against the real list (nothing silently dropped)

| v1 entry | product it rested on | status | what stays shut |
|---|---|---|---|
| **W-2** index options → `P6`/`O8`/`B-G1` | OptionMetrics IvyDB | **DEAD** | `P6` stays `NEEDS-DATA`; `O8` stays INCONCLUSIVE-on-proxies. **The B-G1 dispersion question returns to Don's desk as a real ~$150/mo purchase decision** — it did not become free |
| **W-4** intraday momentum → `MB41` | TAQ | **DEAD** | `MB41` stays `NOT-TESTABLE-HERE`. **CONCLUSION RIGHT, REASONING WRONG — see §7.2:** I called Intraday Indicators "daily per-name aggregates"; it also ships 5/15/30-minute bars. It still does not revive `MB41` (stock-specific, not the index series it needs) **and it is TAQ-gated on this grant anyway** — the row now stands on two sound legs instead of one wrong one |
| **W-8** clean options instruments | IvyDB | **DEAD** | No loss worth mourning: `I-1` is built and its parity check clears at **0.9858** against a 0.95 bar. `O-1`'s K2 stays on raw-chain Breeden–Litzenberger |
| **W-10** short interest pre-2018 → `S18` | US short interest | **DEAD** | `S18` stays partial-sample (32 of 69 dates, all late). The both-halves gate remains impossible |
| **W-11** surface features at 1996 scale | IvyDB | **DEAD** | `B-11` stays on the owned deep freeze (2016+) |
| **W-12** `MA31`/`MA32` reopen | Markit securities lending | **DEAD** (absent from the list) | The family **stays shut**, and this is now a plain tombstone: the 2026 JFE borrow-fee finding says the reopen needs a borrow control, and no borrow product is subscribed |
| **W-13** as-first-reported robustness | Compustat PIT/unrestated | **CENSUS-DEPENDENT** | Live only if the PIT product sits inside the 276 Compustat–CapIQ tables. Ask; expect no |
| — | **Audit Analytics** | **DEAD** | **The NT-filing route for `MA28`'s fourth flag is gone.** `MA28` stays a **three-flag** card, and `MA28-CARD`'s published thresholds stay as shipped |
| **W-1** PIT sector map | Compustat hist. GICS | **CONFIRMED — `S25` HAS RE-OPENED** | `comp.co_hgic` entitled and dated: 45,836 rows / 32,012 gvkeys, **94.9%** panel coverage, **30.2% carrying more than one dated row** — a history, not a snapshot wearing a date. Two caveats travel: the GICS 11 are not the panel's 11 (the crosswalk is a register's choice), and **GICS's own taxonomy changes (Real Estate 2016, Communication Services 2018) will read as a wave of simultaneous reclassifications** |
| **W-3** revisions | LSEG IBES | **LIVE — and larger than v1 knew** | see W-3 / W-3b |
| **W-5** institutional backfill | Thomson/Refinitiv s34 | **DEAD via this route** | All eight `tfn.*` tables genuinely denied, re-verified on eight fresh connections; `tfn` is a legacy shell. Any substitute is the census's to name, and until it does, `MB7`'s 49-of-69-date defect stands unrepaired |
| **W-6** delisting cross-check | CRSP | **LIVE** | see W-6 |
| **W-7** $ADV → `B13`/`S7` | CRSP volume | **LIVE — NO LONGER SUPERSEDED (§7.2)** | W-16 is dead, so CRSP `dsf` is the route rather than the fallback. Phase 2 measured **2,271 of 2,531 = 89.7%** against the current path's 19.8%; `B13` and `S7`'s fourth interaction unpark here |
| **W-9** Compustat twin | Compustat + CRSP | **LIVE** | see W-9 |

---

## 2. TIER 1 — REOPENS A PERMANENTLY CLOSED DOOR

### W-1 · The PIT sector map — `S25`'s "unobtainable", now with BOTH routes it named
**Tags: [`S25` CLOSED-UNOBTAINABLE · `S15` "sector-neutral in every form is finished" ·
`SECTOR-NEUTRAL-B6` rejected on the panel that counts]**
`S25` named exactly two routes back: the **EDGAR assigned-SIC build** and a **historical GICS
snapshot "not sold as history."** The real list carries **both** — Compustat–CapIQ's historical
GICS (validity-windowed assignments) *and* **SEC Analytics Suite** (EDGAR filing headers, the
assigned-SIC route). Two independent instruments for one closed door, and **their disagreement
rate is itself a free quality check** neither route could provide alone.
**IF confirmed THEN** `S25` flips OBTAINED and `S15`'s finality meets its own re-open condition.
The re-run still argues past `SECTOR-NEUTRAL-B6` on instrument, not hope: that rejection applied
**today's** map backward, whose historical misclassification is attenuating noise.
**CENSUS:** Compustat–CapIQ → historical GICS table → gvkey, gsector, ggroup, indfrom, indthru
→ 2009-01→present **including delisted names** (a survivor-only map is today's map in costume
and the register dies free on it) · SEC Analytics Suite → filing-header SIC → same span · CCM
link. **Sketch:** v1's W-1 sketch survives the correction **intact** — use it as written
(2 equity trials; same-instrument kill at <10% disagreement).

### W-14 · Cboe open-close volume — **REJECTED AT THE CENSUS GATE 2026-08-26 · see §7.1**
*Left UNEDITED below as the record of what was proposed and why it was wrong (`MA18`'s
precedent). **Its central claim — that this dissolves `D4`'s purchase — measures FALSE.
`D4` is UNDISSOLVED.***
**Tags: [`D4` DON'T BUY (priced from SEC-filed schedules: **$500/mo EOD, $400 per
request-month**, and this project's own window is **94 purchasable months**) · `MB15` (venue
proxy VOID) · `MB16`/`O14` (six flow features NULL) · `R2` (the alert entry)]**
**Every flow feature this project has ever tested was computed from its own alert-day tick
cache** — 3,884 units, 186 symbols, conditioned on the alert screen itself. `MB15` died on the
venue axis, the condition+size successor is parked unpowered, and `O14`/`MB16`'s six features
are NULL *on that cache*. Cboe open-close is **exogenous and full-market**: customer-vs-firm
buy/sell **opening** volume at instrument level, not conditioned on our screen, and it is the
dataset the retail-flow literature is built on. **That conditioning difference is the whole
argument past the flow graveyard** — and it must be argued in the register, because the
mechanism (retail flow is uninformed on average) is the same one `MB15` was chasing when it
died on identification rather than on mechanism.
**IF confirmed THEN** the first exogenous signal class in the options book's history, and
`D4`'s buy-decision closes as OBTAINED-WITHOUT-PURCHASE. **Sketch:**
`PREREG_DRAFT_w14_cboe_openclose.md`.
**CENSUS:** Cboe Options (WRDS) → open-close volume summary → customer/firm × buy/sell ×
open/close, by underlying and ideally by strike/expiry → span (2016+ minimum to overlap the
owned book; earlier is upside) → symbol↔permno/ticker link.

### W-3 · LSEG IBES — `D6` unparks and `D7` dissolves by their own text
**Tags: [`D6` STAY PARKED — *"Path is IBES via WRDS, so D6 and D7 are ONE decision"* · `D7`
NOT PURCHASABLE (affiliation — **the thing that changed**) · PEAD's local rejection]**
The one signal class the record priced as unobtainable at any retail price. **Sketch:** v1's
W-2 sketch (revision *breadth*, not level; PEAD faced by name; coverage kill at <60%) survives
intact. **CENSUS:** IBES → det_epsus + statsum_epsus → estimate, statpers, anndats, revision
timestamps, analyst counts → 2009→present → ibcrsphist link → **small-cap coverage rate against
our panel** (that rate is the register's own kill input).

---

## 3. TIER 2 — REPAIRS A KNOWN DEFECT

*Ranked by the commission's rule. **Stated plainly against that rule: W-3b has the largest
blast radius in this entire map and I recommend it FIRST in execution order** — it repairs an
instrument that 20 fleet books and every event-conditioned options study stand on.*

### W-3b · IBES **actuals with announcement dates** — the earnings-date spine repaired
**Tags: [`I-4` (the spine, built on Sharadar code-22) · `S17`/`SC-2` (the legend; code 22 runs
**1.65 events/ticker-year** against ~4 implied) · `O6`/`O7`/`O17`/`O24`/`EVOWN` (every
event-conditioned options study) · `F-4`/`F-12`/`F-13` (fleet books whose entry rules *skip*
unknown-event names and count the skips)]**
The relayed census figure — **29 of 186 names with ZERO earnings coverage** — is a hole in the
input, not in the analyses: the honest studies all treat a missing date as *unknown* and count
it. **IF IBES actuals confirm THEN** the spine gains a second, independent, announcement-dated
source; coverage rises; and every downstream study's "unknown" partition shrinks. Zero trials —
this is `I-4` v2, an instrument. **The cross-source disagreement rate is a finding either way**
(`W-6`'s shape: ours wrong = a correction with named blast radius; agreement = external
validation). **Sketch:** `PREREG_DRAFT_w3b_ibes_event_spine.md`.
**CENSUS:** IBES → actuals (act_epsus) → anndats, anntims, pends → 2009→present → coverage of
the 186 optionable names **and specifically the 29** → ibcrsphist link.

### W-5 · Thomson/Refinitiv s34 — the panel's most consequential coverage hole
**Tags: [`MB7`'s 49-of-69-date complete-case defect · `RUN_RULES` A-10 (exists because of it) ·
`MA58-SEAS` UNINTERPRETABLE partly on it · `THEME-RESTORE`/`FIDELITY-2` (the splice precedent)]**
`institutional` is empty before ~2013-06 — the root cause of every basis-seven residualisation
losing 20 of 69 dates. **PROVISIONALLY LIVE** pending the re-probe. Priced honestly as **a
panel-change register, not a data drop**: fidelity gate on the overlap (`FIDELITY-2`'s 0.60 bar,
imported), a declared splice date, a new panel object (never overwrite `panel_corrected_69d.pkl`
— the `M4`/`B23` lesson), and **the named consequence that `X7`'s floors are calibrated on the
old panel**, so any register *scoring* on the extended panel owes a floor re-derivation first.
**Sketch:** v1's W-3 sketch survives intact. **CENSUS:** confirm the correct library name first
(the DENIED was ours), then s34 → mgrno, cusip, shares, fdate, rdate → gap window 2009→2014 +
overlap 2013-06→present → **rdate−fdate lag distribution** (PIT honesty is the lag) → cusip↔permno.

### W-16 · Intraday Indicators by WRDS — **DEAD 2026-08-26 (TAQ-gated) · see §7.2**
*Left unedited below. The `B13`/`S7` half survives via **W-7** (CRSP `dsf`, 89.7% coverage);
the spread / price-impact half and the `S14` cost-model refinement are gone.*
**Tags: [`B13` PARTIAL-BLOCKED (*"MIN_AVG_DOLLAR_VOLUME structurally cannot bind — the price
export carries date and close ONLY"*) · `S7` (*"size × liquidity IS NOT BUILDABLE"*) · `MA25`
(the record correction: the project has a liquidity measure, on a different path) · `O18`
(ρ = 0.6743) · `S14`/`S14-WIDTH` (the cost-inclusive gate that produced the record's ONE
adoption) · `V5` (slippage)]**
TAQ-derived **daily spreads, depth and price impact without TAQ**. Three defects dissolve at
once: `B13`'s prefilter becomes bindable (FIXED-class), `S7`'s one un-buildable interaction
becomes buildable (1 equity trial, arguing past its three *rejected* siblings on the closure's
own "not buildable" language — the fourth was never rejected, only impossible), and **the
cost model behind `S14`'s band gets per-name price impact instead of a flat assumption** —
which is the single member of the risk/cost family with a winning precedent (see
`RISK_PRIMARY_MAP.md` §4). **CENSUS:** Intraday Indicators → effective/quoted spread, depth,
price impact (Amihud/Kyle-style) → daily → 2009→present → panel-name coverage rate → permno link.

### W-6 · CRSP delisting returns — the survivorship mask cross-checked
**Tags: [`B14` (the ACTIONS mask, "complete") · `E-5`'s terminal-value rule · `C5`'s 32.1%-invisible]**
Zero-trial record-integrity class; a disagreement is a finding either way. **CENSUS:** CRSP →
dse/dsf → dlret, dlstcd, dlstdt → 2009→present → permno↔ticker.

### W-21 · Blockholders — the `34`/`35` sunset repaired
**Tags: [`SC-2` (the finding: EVENTS codes 34/35 — Schedule 13G/13D — **stop 2024-12-17 and
2025-05-16**, a dying input under `S17`'s strongest arm) · `S17` (all ten arms NULL, era-concentrated)]**
**IF confirmed THEN** the 13D/G channel gains a live source past the sunset, which is the one
mechanism `SC-2` could name for `S17`'s era-concentration. Note the honest limit `SC-2` already
recorded: the lead touches **at most one of five arms**. **CENSUS:** Blockholders → holder,
percent, date → span past 2025 → link.

### W-23 · Financial Ratios Suite — the second-vendor cross-check
**Tags: [`OOB2` (a vendor field vanished and rewrote a headline — single-vendor fragility, the
project's own scar) · `B10` (`accruals_q` silent overwrite)]** Not a signal: an independent
recomputation of ratios we compute ourselves, as a fragility audit. Cheap, zero trials.

---

## 4. TIER 3 — MERELY EXTENDS (real, priced, behind everything above)

* **W-9 · The Compustat/CRSP twin** — [`X8` (replicates in other countries) · `OOB2` · `MB13`]
  The same market from independent pipes; and Compustat's depth makes a ~60-year twin panel
  constructible. **The honest `MB13` statement, unchanged from v1:** its NOT-PERMITTED is *"on
  this panel"* arithmetic and stands as written; a 60-year object changes that gate's **inputs
  on a different object**, and `MB22` re-runs there rather than being waived. Largest build in
  the map — a season, not a session; its first register is the cheap headline replication.
* **W-17 · Historical SPDJI** — PIT index membership → index-add/drop catalysts
  (`OPTIONS_BRAINSTORM` #11/#41, previously blocked on reconstitution history). [VIRGIN]
* **W-19 · TRACE** — corporate bonds, genuinely virgin here. The natural question is
  bond-implied distress against `MA28`'s accounting flags — **and with IvyDB dead, TRACE is the
  only market-implied distress instrument that reaches names without liquid options**, which
  makes it `X-SEED-1`/`E-8`'s complement rather than a duplicate. [VIRGIN · `MA28-CARD` · `E-8`]
* **W-22 · Beta Suite + Pastor–Stambaugh factors** — feeds Part 2's factor-neutralisation
  candidate and gives `R1`/`X4` a liquidity-risk factor. [`X4` t 1.10 · `S15` (the
  neutralisation family's record)]
* **W-25 · SEC Order Execution (Rule 605/606)** — an **external anchor for `O18`'s ρ = 0.6743**
  and for the fleet's `F-1` fill A/B: published effective/quoted spread statistics by market
  centre. Cheap, and it makes a cost claim checkable against something we did not compute.
* **W-18 · Insiders Data by WRDS** — **DEMOTED against the brief.** `MA57` already **refuted**
  the data blocker on owned data (24 columns, `ownername` *and* `transactioncode` present,
  5,636,964 rows, zero missing on 124,181 open-market purchase rows) and `MB20`/`B-1` is
  unblocked without WRDS. This is a **second-source cross-check**, not an unlock. [`MA57`·`MB20`]
* **W-24 · US Patents** — a new signal class (Kogan et al. patent value) that walks straight
  into **the five-body orthogonality wall** (`U2`, `MA31`/`MA32`, `MA58-SEAS`, `MB18` — R² 0.027
  to 0.145, not one clearing). Listed because nothing is discarded; ranked low **because the
  record says new orthogonal signals do not work here**, and this file will not pretend
  otherwise. [`MB12` (the pattern that constrains every such register)]
* **W-27 · Event Study tool / W-26 · Bank Regulatory** — a canned validation convenience, and a
  product whose universe barely intersects ours. Lowest, listed for completeness.

### W-20 · **INSTRUMENT ZERO — Linking Queries / CCM. Price this FIRST.**
Every entry above is a join. `gvkey↔permno↔cusip↔ticker↔ibes-ticker` coverage over **our**
names, with share-class and ticker-reuse handling, is the gate on the whole map — and this
project has been bitten by identity before (the harvest's **45 units over 26 symbols** carrying
another company's history; `B12`'s alphabetical universe). **The census's first deliverable
should be the link-coverage table**, because a 90%-coverage link silently truncates every
downstream study and looks like a result.

---

## 5. THE ANTI-SEED — what WRDS does NOT touch (quote this list, not "we bought data")

* **Mechanism closures stay closed:** short vol as richness-selling (`O9`/`A3`/`V6-OPT` — the
  strike spends the edge), the alert entry (`R2`), `U1`, exit tuning (`S23`/`O1`/`PATHSTUDY`),
  `O13`, `U7`, `MB8` (flags disjoint from the book is a *book* fact), weight/scheme tuning
  (`MLCOMB` reversed out of sample), `MB9`-as-stated, and "structurally orthogonal" as a
  motivation (five bodies — see W-24, which is held to it).
* **Time-bound arithmetic stays time-bound:** `S19`/`MA33`'s decay clock needs future months;
  `V1`'s shadow pairing needs an adoption event; every fleet verdict horizon needs **fills**.
* **N-bound machinery is untouched:** placebo floors, HLZ hurdles, the DSR — they move on
  trials, not entitlements. `MB13` stands as written.
* **The alert-cache power walls stand:** `MB15-SLIM` and every rubric bucket-3 item are bounded
  by alert-days, and WRDS sells no alert days. **The one real exception is W-14**, which is
  exogenous by construction — and it must still argue past the flow graveyard on mechanism.
* **NEW, from Part 2:** *no vendor sells statistical power for a Sharpe gate.* The
  risk-primary kill in `RISK_PRIMARY_MAP.md` is a property of 69 quarterly periods and survives
  every entitlement on this list.
* **And the four dead products above** — nobody should re-propose an IvyDB, TAQ, short-interest
  or Audit-Analytics-dependent design without a new subscription, not merely a new argument.

---

## 6. THE CENSUS INTERLOCK — one block, ticked one-for-one

1. **CCM / Linking Queries (W-20, FIRST):** link coverage over our 2,531 names, share classes,
   reuse handling. 2. **Compustat–CapIQ:** historical GICS incl. delisted (W-1); PIT/unrestated
   present? (W-13); the seven themes' input fields for the twin (W-9). 3. **SEC Analytics:**
   filing-header SIC span (W-1); full-text availability and unit (W-15/lazy-prices class).
4. **IBES:** detail+summary revisions and small-cap coverage (W-3); **actuals with anndats,
   and specifically the 29 zero-coverage names** (W-3b). 5. **Thomson/Refinitiv:** correct
   library name, s34 gap-window coverage, rdate lag (W-5). 6. **Cboe Options:** fields, strike
   granularity, span (W-14). 7. **Intraday Indicators:** spread/depth/impact fields, panel-name
   coverage (W-16). 8. **CRSP:** dlret/dlstcd (W-6); dsf volume as W-7 fallback. 9. **Blockholders**
   span past the 2024-12/2025-05 sunset (W-21). 10. **Historical SPDJI**, **TRACE**, **Beta
   Suite**, **Pastor–Stambaugh**, **Financial Ratios**, **SEC Order Execution**, **Patents**,
   **Bank Regulatory**, **Event Study** — entitled, span, key (Tier 3).

*Zero trials charged by this file. Every reopen argues past its tag inside its own register,
and the census gates all of it. — Scout*

---

## 7. CORRECTIONS LOG — 2026-08-26 (append-and-amend; §2–§4 left unedited above)

*Three corrections owed, and a fourth thing this lane got structurally wrong. Entries above are
NOT rewritten — their headings carry a pointer and the bodies stand as the record of what was
proposed. `MA18`'s precedent: a deliverable is a record of what was found, including by whom.*

### 7.1 · **W-14 IS REJECTED. The claim measured FALSE and `D4` is UNDISSOLVED.**

**Measured: Cboe open-close is NOT on this WRDS grant under any name — zero candidates across
221 libraries.** W-14's headline claim — that it "dissolves `D4`'s declined $500/mo purchase" —
**is false**, and the consequences are recorded rather than softened:

* **`D4` stays `REJECTED / DON'T BUY`, and its purchase question is UNDISSOLVED.** The SEC-filed
  prices stand as `D4` measured them ($500/mo EOD; $400 per request-month; 94 purchasable months
  for this project's window). If the retail-flow question is ever wanted, **it costs what `D4`
  said it costs** — this map bought nothing there.
* **The options book still has no exogenous signal**, and every flow feature in the record stays
  alert-day-conditioned. Nothing about the *argument* for exogenous flow was refuted; the
  **product** is absent. Those are different, and only the second is now known.

**On whose kill fired — and I want to be exact rather than flattering.** My W-14 sketch named
**K3 (identification)** as "the one most likely to fire", and the family of risk was right. But
**K3 did not fire and could not have**: it tests whether an obtained product separates customer
from firm volume, and no product was obtained. **The gate that rejected W-14 was the CENSUS,
upstream of every kill in the register.** The distinction is the lesson:

> **A register's kill conditions can only protect against properties of data you have. They are
> structurally blind to a product that is not there. Only the census guards that door — which is
> why §7.4 matters more than this paragraph does.**

Recorded so no future reader concludes that well-written kill conditions catch access failures.
They do not, and mine did not.

### 7.2 · **W-16 IS DEAD: WRDS Intraday Indicators requires TAQ, and this grant has none.**

The product page states it plainly and I quoted it a session ago while marking the entry only
"verify first" — **that was too soft and it is now DEAD**, not qualified. What survives and what
does not:

* **DEAD:** the spread / depth / price-impact half, the external anchor for `O18`'s ρ, and the
  `S14` cost-model refinement (per-name price impact). The `MB41` non-revival stands.
* **SURVIVES, via W-7 instead:** `B13`'s unbindable `MIN_AVG_DOLLAR_VOLUME` and `S7`'s fourth
  interaction unpark on **CRSP `dsf`** — phase 2 measured **89.7%** panel coverage against the
  current path's 19.8%. W-7 is promoted from fallback to route.
* **The constructive substitute, and it costs nothing:** effective spreads are estimable **from
  daily OHLC alone** — Ardia–Guidotti–Kroencke (*JFE* 2024), with Corwin–Schultz and Holden
  (2009) as the older members of that family. CRSP daily carries OHLC. **A cost model is
  therefore still buildable without TAQ**, at lower resolution and with its estimator named.
* **And a correction to my own correction:** the death-ledger's W-4 row said Intraday Indicators
  is "daily per-name aggregates". It also ships **5/15/30-minute** bars. The row's conclusion
  (`MB41` stays dead) was right for the wrong reason and now stands on two better ones.

### 7.3 · **The O-1 design lesson, and it is the most expensive thing on this page**

**`O-1`'s arm returned UNDERPOWERED because a chain-coverage figure measured on the ALERT BOOK
was applied to the PANEL: ~75% assumed against 5.89% actual — a factor of ~17.** That number
came from my draft. I wrote *"every panel rebalance date with chain coverage (expected ≈40 of 69,
the `V6-OPT` window)"* — importing a coverage rate from a population (dipped names with options
activity) that is not the population the arm would test (all MA28-flagged panel names). The
register then ran and could not have cleared.

**Adopted as a standing drafting rule for every future draft this lane writes:**

> **COVERAGE IS MEASURED ON THE POPULATION THE ARM WILL TEST, AND STATED BEFORE THE ARM.** A
> coverage rate borrowed from any other population — an earlier study, an adjacent screen, a
> book with different selection — is an assumption wearing a measurement's clothes. It goes in
> the pre-outcome control pass, and the arm refuses without it.

This joins two rules the same way, and together they are now this lane's checklist:

1. **Name the FIELD and its DIRECTION IN TIME**, never just the source (`F-13`, `2ef8e5d`).
2. **Measure coverage on the arm's own population, before the arm** (`O-1`, this entry).
3. **Price a margin for what is economically acceptable, not only for what is statistically
   resolvable** (`R-1`, `RISK_PRIMARY_MAP.md` §amended).

Three drafts, three different ways to be confidently wrong about something checkable in advance.
All three are cheap to check and none was checked.

### 7.4 · **What the census could NOT have answered — and the convention that follows**

**`WRDS_CENSUS.md` probed the OptionMetrics-replacement shape and never probed open-close.** Its
denial of six `optprice`-shaped tables was **never a measurement of this product**, and reading
it as one would have been a second error on top of the first. The decisive evidence is the
separate **221-library sweep returning zero candidates** — a different instrument answering a
different question, and it is the one that settles W-14.

> **CONVENTION, binding on every future entry in this map: a `CENSUS:` line must name the EXACT
> LIBRARY AND TABLES to probe — `library.table`, not a product's marketing name — plus the fields
> and span. A product name is a thing to search for; a table name is a thing to test.**

**Existing entries whose `CENSUS:` lines are under this standard and must be sharpened before
anyone acts on them:** W-3/W-3b (IBES — name `ibes.det_epsus`, `ibes.statsum_epsus`,
`ibes.act_epsus`, `wrdsapps.ibcrsphist`), W-17 (SPDJI), W-19 (TRACE), W-21 (Blockholders),
W-22 (Beta Suite / Pastor–Stambaugh), W-25 (SEC Order Execution), W-23 (Financial Ratios).
W-1 and W-7 are already confirmed by probe and need nothing. **Until an entry's tables are named,
its "IF the census confirms" is not a testable condition — it is a wish with a colon after it.**

### 7.5 · Net effect on the map

**Tier 1 is now one entry, not three:** W-1 (**CONFIRMED — `S25` re-opened**, the first
permanently-closed row to meet its own exit criterion) and W-3 (IBES, live but tables unnamed).
**W-14 is rejected; W-5 is dead via `tfn`; W-16 is dead.** The map's honest score after contact
with the census: **one confirmed unlock, one live, two dead on entitlement, one dead on gating,
one rejected outright.** That is a normal hit rate for a speculative map and it is why every
entry was written conditional — but the conditionality only worked where the condition named
something testable, which is §7.4's whole point.
