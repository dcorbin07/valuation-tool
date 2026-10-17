# PRE-REGISTRATION — `F23-SECID`: does the cluster rule survive counting insiders by SEC ID?

**Committed ALONE, markdown only, zero `.py`, before any runner for this item exists.**
`DECISIONS.md` 2026-10-15: *"the rule is re-measured on the SEC's insider ID numbers on the
2009–2019 build data only, with stage 1's bar. F-23 moves to that rule only if it clears."*

**ONE EQUITY TRIAL, booked in the commit after this one and before any runner exists.**

**THE CHECK QUADRANT IS SPENT AND IS NOT READ AGAIN.** `INSIDER-WIDE` spent it on 2026-10-13.
This register reads the **BUILD quadrant only**, which `RESEARCH_CHARTER.md` §5 licenses reusing.

---

## 0. Why this exists, in one paragraph

`INSIDER-WIDE` confirmed the rule on the `cap >= $500M` tier using the **licensed SF2 export**,
where *"distinct insider"* means a distinct **`ownername` string**. F-23 cannot trade forward on
that file — it is a frozen snapshot — and the SEC's free feed, which is the only live replacement,
**counts insiders differently**: SF2 carries **no owner identifier at all** (24 columns, name only)
while the SEC supplies **`RPTOWNERCIK`**. Measured on the 2026-07-01..2026-09-30 overlap, the two
feeds agree on which names bought and when to **97.9%/99.2%** and fall to **88.5%/77.5%** the
moment the owner is added to the key. **The rule triggers on a COUNT OF DISTINCT INSIDERS, so that
disagreement is the trigger itself.** So the key is re-measured before the book is moved onto it.

---

## 1. THE ONE CHANGE — and the design decision that keeps it ONE change

**`distinct insider` means a distinct SEC reporting-owner ID (`RPTOWNERCIK`) rather than a distinct
`ownername` string.** Everything else is `PREREG_insider_cluster_wide.md`'s, unchanged.

**AND BOTH ARMS RUN ON THE SEC's OWN DATA, WHICH IS NOT WHAT A NAIVE READING WOULD DO.** Sourcing
the ID arm from the SEC while leaving the name arm on SF2 would change **two** things at once — the
**feed** and the **key** — and no difference between them could be attributed to either. So:

* **ARM A (NAME):** SEC data, clusters counted by distinct **`RPTOWNERNAME`** (normalised:
  upper-cased, punctuation dropped, whitespace collapsed — the key `INSIDER-LIVE-FEED` already
  uses, and **deliberately not a fuzzy match**, because a threshold would make the comparison a
  tunable parameter).
* **ARM B (ID):** SEC data, clusters counted by distinct **`RPTOWNERCIK`**.

**The ONLY difference between A and B is the identity key.** `A` is the **reference**, not a second
hypothesis, and carries **no verdict** — it exists so the ID rule's effect can be read against a
name rule measured on the same rows.

**AND THE COMPARISON TO THE REGISTERED FIGURE IS A THIRD, SEPARATELY LABELLED THING.**
`INSIDER-WIDE`'s build-quadrant `$500M+` reading is **SF2/name**: **+1.1319pp**, *t* **+2.01 /
+2.25**, `se` 0.5641 / 0.5025, cost 0.601pp, **net +0.5312pp**, on **1,378 events / 574 tickers**.
Any gap between that and ARM A carries the **feed** difference and may **not** be read as a
statement about the key.

### 1a. Unchanged, verbatim

`k` >= 2 distinct insiders filing an **OPPORTUNISTIC** open-market purchase (`TRANS_CODE == "P"`;
a missing code **COUNTED AND SKIPPED**) on one ticker inside a **30-calendar-day** window, dated at
the **LAST** filing, **one event per cluster** under a full-window cooldown, with the **STRICT**
condition that each insider of the pair traded in **each of the two prior calendar years**. The
**MARKET-ADJUSTED leg only** — the own-normal leg stays out for the reason this lane measured (its
own null is centred at **+1.17pp**, not zero). The **within-date permutation null**, 500 draws.
**Both halves**, boundary **2015-01-01** (stage 1's midpoint of 2009-2019, embargoed), each against
**its own** null, same sign. **Both clusterings** — event **date** and **ticker**. **Size-tiered
costs** per event from the shipped `fundamental_panel.one_way_cost_bps`, round trip = 2x one-way.
**Terminal vs censored** per `E-5`. Population: `cap >= $500M` at the most recent **PRIOR**
point-in-time market cap. Horizon **`h` = 63**.

### 1b. The feasibility facts, measured BEFORE this register was written

* **`RPTOWNERCIK` is 100.00% non-null** in 2007Q1, 2009Q1 and 2019Q4 — so the key exists across the
  whole build era and the two prior years it needs. A register resting on an absent field is void.
* The SEC publishes the quarters under **two path prefixes** — `structureddata` for older quarters
  and `datastandardsinnovation` for recent ones. Both are tried; a quarter reachable under neither
  is a **refusal**, never a silently empty quarter.
* The build era plus its two prior years is **2007Q1..2019Q4 = 52 quarterly ZIPs**, ~8-17 MB each.

---

## 2. THE BAR — stage 1's own clauses, fixed here, before anything runs

ARM B must clear **all four**. Any other outcome is a **DOES NOT CLEAR**.

* **A1 — SIGN.** The market-adjusted mean is **POSITIVE**.
* **A2 — ITS OWN NULL, BOTH HALVES.** Above its own within-date permutation p95 on the full build
  sample **and** both halves carry the **same sign**.
* **A3 — *t*.** Cluster-robust *t* > **2.0** on the event **DATE** and on the **TICKER**, clearing
  under **both**. **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`): no X7 or `CORRECTED-FLOORS` figure
  transfers to a clustered event-time mean, and the HLZ hurdle is **reported beside and not gated**
  (`R4`'s reason: HLZ prices the best of N draws and this is one pre-registered re-measurement).
* **A4 — ECONOMIC.** The mean exceeds the cell's **own event-weighted size-tiered round-trip cost**.
* **A5 — BH at q = 0.10 with `k` = 1, AND WHAT THAT IS WORTH IS STATED RATHER THAN IMPLIED.** There
  is **one** verdict arm, so BH at `k` = 1 reduces to `p <= 0.10` and **does no correcting work**.
  It is carried for continuity with stage 1's clause list and is **not** evidence of multiplicity
  control. ARM A is excluded because it carries no verdict, and that exclusion is declared here
  rather than after the fact.

---

## 3. POWER — stated before the run, and the honest reading is uncomfortable

From the name rule's **own realised** build-cell `se` (`MB8`: this construction's own, never
borrowed), worst clustering **0.5641pp** on `n` = 1,378:

| quantity | value |
|---|---|
| MDE80 at crit 2.0 | **1.6030pp** |
| power against the name rule's own gross effect (+1.1319pp) | **50.3%** (expected *t* +2.01) |
| power against its own **net** effect (+0.5312pp) | **14.7%** (expected *t* +0.94) |

**THE BUILD CELL AT `$500M+` IS A COIN FLIP ON THE GROSS LEG AND BLIND ON THE NET LEG.** The name
rule itself clears A3 at **+2.01 / +2.25** — *just* over the bar — so this is a knife-edge cell and
was before the ID key was considered.

**WHAT FOLLOWS, AND IT IS DECLARED NOW SO IT CANNOT BE CHOSEN LATER.** `DECISIONS.md` makes the
consequence binary — F-23 moves only if the ID rule clears — so the **verdict vocabulary is
`CLEARS` / `DOES NOT CLEAR`** and F-23's fate follows it either way. **But a `DOES NOT CLEAR` at
~50% power is NOT evidence that counting by ID is wrong**; it is a cell that cannot resolve a
difference of the size the name rule itself shows. That sentence travels with the verdict, and the
MDE travels with it (`RUN_RULES` PART A rule 11). **The one thing it is NOT is a licence to look
elsewhere** — see §5.

---

## 4. REQUIRED REPORT — produced whatever the verdict, and it is the point of the item

1. **Event counts:** ARM A and ARM B, with tickers, on the same cell.
2. **Shared events:** `|A ∩ B|`, the Jaccard, and the events unique to each.
3. **Gross and net effect for each arm**, with both clusterings and both halves.
4. **WHAT THE ID RULE SHOWS ABOUT THE NAME RULE**, decomposed rather than asserted:
   * **names MERGING two people** — one `ownername` string carrying **more than one**
     `RPTOWNERCIK`. If this dominates, the name rule **UNDER-counted** distinct insiders and
     **missed** clusters.
   * **names SPLITTING one person** — one `RPTOWNERCIK` appearing under **more than one**
     normalised name. If this dominates, the name rule **OVER-counted** and fired clusters that
     were **one insider filing twice**, which would be a **false-trigger** and the more serious
     direction for a book.
   * the share of ARM A's events that **survive** under the ID key, and the share that do not.
5. **The 83% figure is NOT this number and may not be conflated with it.** That was
   `INSIDER-LIVE-FEED`'s **SEC-versus-SF2** event overlap on a 2026 window — a **feed** comparison.
   This is a **key** comparison on one feed.

---

## 5. Void conditions

1. **The check quadrant read again**, in any form.
2. **The key definition changed after any figure is seen** — including switching between
   `RPTOWNERCIK` and a CIK-plus-name composite.
3. **A variant searched for after a `DOES NOT CLEAR`.** `DECISIONS.md` says F-23 stays declared and
   unfilled; a second key, a second `k`, a second tier or a second horizon is a **new register with
   its own trial**, and none is proposed here.
4. **ARM A quoted as a verdict**, or the SF2 figure quoted as if it were ARM A.
5. **A `CLEARS` read as confirming the registered result.** The registered result is **SF2/name on
   the check quadrant**; this is **SEC/ID on the build quadrant**, and the build quadrant is where
   designs are chosen rather than confirmed.
6. **The late-half caveat dropped** from anything F-23 says afterwards.
7. **A bar lowered** after being watched (`W-28`).
8. **Any real order, any broker, any percentage set by a lane.**

---

## 6. Expectations, stated now

1. **ARM B gives MORE events than ARM A**, at 65/35 — a name string can only merge distinct people,
   and merging reduces the distinct count below the true one.
2. **The dominant identity defect is MERGING rather than splitting**, at 60/40, because the SEC's
   own 2007Q1 quarter already shows **43,154 distinct CIKs against 43,102 distinct names**.
3. **ARM B CLEARS**, at 45/55 — a genuine coin flip, and the cell's own 50.3% power is most of why.
4. **The two arms share more than 90% of their events**, at 55/45.
5. **ARM A does not reproduce the SF2 figure**, at 80/20 — the feed difference is already measured
   at ~83% event agreement on a recent window.

---

## 7. Not done

* **No app file is touched.** The app fixer owns items 59-61 and the live path.
* **No purchase.** The 1999-2008 rung is closed as unobtainable in a separate, zero-trial row.
* **No broker code edited**, and the fleet self-check block is reported rather than repaired.
* **Nothing adopted.** F-23 remains paper-only and unfilled until its feed validation passes.
