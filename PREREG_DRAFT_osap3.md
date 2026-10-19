# PREREG_DRAFT_osap3.md — three published signals, not 209 — 2026-10-18

**A DRAFT, NOT A REGISTER. ZERO TRIALS.** No arm has run and the firm-level OSAP file is **not
pulled**. A register exists only once this file is committed **ALONE**, markdown only, zero `.py`, as
a strict ancestor of every measurement commit.

**Ranked #3 in `EDGE_DATA_MAP.md`, and it is the one draft whose honest headline is a refusal: the
brief asks for a 209-signal batch and the arithmetic says three.**

---

## 1. WHAT THE BRIEF ASKS FOR, AND WHY THE NUMBER CHANGES

The brief asks to pull the Open Source Asset Pricing firm-level signals and *"propose ONE batch
register for the survivors: one trial per signal, booked first; BH across the batch … State its
power at today's `N`."*

**STATING ITS POWER IS THE ANSWER.** Two independent screens cut 212 predictors to three, and the
multiple-testing arithmetic says a 209-trial batch would cost more than it could possibly buy.

### SCREEN 1 — THE LARGE-CAP TEST, FREE, FROM A FILE ALREADY ON DISK

`data/factors/raw/osap_signal_docs.csv` (331 rows, 29 columns) carries each original paper's own
long-short result **and its `Stock Weight`**:

| screen | survivors |
|---|---|
| all rows | 331 |
| `Cat.Signal == Predictor` | **212** |
| …and **`Stock Weight == VW`** | **28** |
| …and holding period **≥ 3 months** | **12** |
| …and not already an input / already rejected / already run as a close sibling | **5** |
| …and **live-rebuildable from Sharadar or EDGAR** | **3** |

> **184 OF 212 PUBLISHED PREDICTORS HAVE ONLY EQUAL-WEIGHTED EVIDENCE.** Hou-Xue-Zhang measure
> microcaps — below the 20th NYSE percentile — at about **3% of market capitalisation and 60% of the
> stock count**, typically **more than 60% of the extreme deciles** a long/short sort holds, and
> conclude anomalies there are **more apparent than real.** **So for a $10B-floor book, an
> equal-weighted published result is close to no evidence at all**, and one free column removes 87%
> of the catalogue before a byte is pulled.

### SCREEN 2 — WHAT THIS PROJECT HAS ALREADY DONE TO THE REMAINING TWELVE

| acronym | VW %/mo | *t* | status |
|---|---|---|---|
| `GP` | 0.310 | 2.49 | **SHIPPED** (`gp_on_capital`); survives `R4`'s BH |
| `CBOperProf` | 0.470 | 3.17 | **TESTED → NULL** (`S2`, IC *t* +0.84 against a 2.71 bar) |
| `OperProfRD` | 0.290 | 1.84 | sibling of the above; **fails \|t\| 2 in its own paper** |
| `Investment` | 0.168 | 2.86 | **REJECTED** (`P5-3`, `neg_asset_growth` *t* −0.70, wrong sign) |
| `IdioVolAHT` | — | 2.70 | **NULL** (`R5`, *t* +1.21) |
| `RDcap` | 0.690 | 2.64 | **SIBLING FAILED** — `STAGE1-BATCH3` `C3` R&D-to-market **NOT_REPLICATED**, below its own MDE |
| `OrgCap` | 0.386 | 2.85 | **SIBLING KILLED** — `STAGE1-BATCH1` `A1` killed at 0.6087 coverage; `W-28` closed at `K1` |
| `PatentsRD` | 0.410 | 4.13 | new, **NOT live-rebuildable** (USPTO/NBER patents) |
| `CitationsRD` | 0.260 | 2.60 | new, **NOT live-rebuildable** |
| **`EquityDuration`** | **0.500** | **4.37** | **THE ARM** |
| **`BetaLiquidityPS`** | **0.533** | **2.54** | **THE ARM** |
| **`realestate`** | 0.244 | 1.80 | **THE ARM — and it fails \|t\| 2 in its OWN paper** |

**THE INTANGIBLES FAMILY HAS NOW BEEN ATTEMPTED THREE TIMES AND THE BINDING CONSTRAINT WAS THE SAME
EACH TIME.** `W-28` closed at `K1` (dated Compustat coverage 81.54% of cells, **57 of 69 dates below
its own 90% bar and the best date not reaching it**); `A1` killed pre-outcome at 0.6087; `C3`
NOT_REPLICATED. **`W-28`'s portable finding — a 90% DATED Compustat-linkage bar is not reachable on
this account — is why `RDcap` and `OrgCap` are excluded rather than retried.**

---

## 2. THE ARITHMETIC THAT FORBIDS THE BIG BATCH

| batch | equity `N` | hurdle (derived) | BH's smallest *p* | 80%-power MDE, 44 dates |
|---|---|---|---|---|
| today | 307 | **3.3843309** | — | — |
| **+3** | **310** | **3.3872** | **0.0166667** | **0.6374 SD** |
| +7 | 314 | 3.3910 | 0.0142857 | 0.6378 SD |
| +28 | 335 | 3.4100 | 0.0035714 | 0.6407 SD |
| **+209** | **516** | **3.5344** | **0.0004785** | **0.6595 SD** |

**TWO THINGS A 209-SIGNAL BATCH WOULD DO, AND BOTH ARE PERMANENT:**

1. **It raises the hurdle for every future AND existing equity claim by +0.1501**, from 3.3843 to
   3.5344. **The direction is safe (`MA6`) and the cost is real** — it is paid by every item that
   comes after, forever.
2. **It demands that its best signal beat *p* = 0.00048.** At 44 dates with a correlated signal set,
   nothing in this project's history has ever come close to that.

**AND EVERY BATCH SIZE IS UNDERPOWERED ANYWAY — WHICH IS THE FINDING AND NOT A CAVEAT.** The
80%-power MDE on the build quadrant is **0.637–0.660 SD**, while **the strongest RAW anchor this
panel has ever carried is `z_fcf_margin` at 0.4346 SD** (`MB18`). **The batch cannot detect anything
as large as the best thing the panel has ever held**, so a null means *"nothing bigger than our
biggest"* — `MB18`'s and `V6`'s sentence — and the register pre-commits to reporting it that way.

**AND THE TEMPLATE IS WORSE STILL IF RESIDUALISED ON THE SEVEN THEMES:** `STAGE1-BATCH1` records
complete-case residualisation leaving **25 of 44 dates with a FIVE-DATE early half** against a
16-date floor, so its three scored arms came back **BOTH-HALVES NOT ASSESSABLE.** **This register
uses the deployed composite as a single control** (charter §1a) and has no choice about it.

---

## 3. THE PRIOR, STATED BEFORE THE DESIGN, BECAUSE IT IS THE MOST IMPORTANT NUMBER HERE

**TWENTY-THREE LITERATURE CANDIDATES HAVE ALREADY BEEN RUN THROUGH THIS EXACT DESIGN AND THE SCORE
IS 0-FOR-23:**

| batch | candidates | outcome |
|---|---|---|
| `STAGE1-BATCH1` | 12 | **0 survive**; 5 of 10 free kills fired |
| `STAGE1-BATCH2` | 5 | **0 survive**; every kill passed, every arm scored |
| `STAGE1-BATCH3` | 8 drafted, 6 scored | **0 clear the governing $10B tier**; three *"REAL BUT NOT INVESTABLE HERE"* |

**AND THE ONE EQUITY SIGNAL IN THE RECORD THAT DOES CLEAR DOES NOT CLEAR IN THIS TIER.**
`INSIDER-WIDE` CONFIRMED clustered opportunistic insider buying on **cap > $500M** at +3.4888pp
(BH *p* 3.2e-04) — and **cap > $10bn reads *t* 0.732**, with the late half netting negative in every
cell. **That is Hou-Xue-Zhang's and Green-Hand-Zhang's large-cap result reproduced inside this
project's own data, on its own best signal.**

> **SO THE PRIOR ON THIS BATCH IS LOW FOR A MEASURED REASON, AND THE REGISTER SAYS SO IN ADVANCE.
> THE QUESTION IT ANSWERS IS NOT "DOES ONE OF THESE WORK" BUT "ARE THE THREE REMAINING
> VALUE-WEIGHTED, LIVE-REBUILDABLE, UNTESTED PUBLISHED SIGNALS WORTH CLOSING?"** Three trials buys a
> closed question. That is the whole value proposition and it is stated as such.

---

## 4. THE FREE KILLS — before any arm, in their own pass, zero trials under `MB1-SEL`

| kill | measures | bar |
|---|---|---|
| **`K1` REBUILDABILITY** | each signal's inputs present in **Sharadar** at the tier, per date | **≥ 0.70 of cells each, or that signal drops from the batch** |
| **`K2` TIER COVERAGE** | OSAP signal values joined to the tier through the **DATED** `crsp.stocknames` route | **≥ 0.70 of cells**; measured on the arm's own population, never inherited |
| **`K3` COSTUME** | mean per-date \|Spearman\| of each signal against each of the seven themes **and** against `size` | **< 0.60 each, or that signal drops** |
| **`K4` AMBIGUITY** | tier cells resolving to more than one permno | **reported and DROPPED, never resolved by a guess** |
| **`K5` REPRODUCTION** | the composite control reproduces the landed record, gated on a non-zero cell count | **max \|Δ\| 0.000e+00** |

**`K2`'s JOIN IS THE DATED ROUTE AND THAT IS NOT NEGOTIABLE.** Measured 2026-10-18: **31,467 of
38,540 tier cells = 81.65% resolve, with 208 ambiguous.** CCM is **DENIED**, and `W-28` measured that
an **undated** route assigned one gvkey's dates to a **different company on 54 names** — so an
undated join is contamination, and the 81.65% is the cell-level figure, not `WRDS_CENSUS.md`'s
name-level 89.7%.

**`K1` IS THE KILL MOST LIKELY TO SHRINK THE BATCH BELOW THREE.** `realestate` needs PP&E components
whose Sharadar mapping is **unverified**; and `BetaLiquidityPS` needs the Pástor-Stambaugh liquidity
factor, which is published free and monthly but **is not in this repo** — so it is a free download
plus a schedule, not an existing column.

---

## 5. THE ARM

**Three signals, one arm each, no grid, no variants.** Charter §1a (incremental against the deployed
composite as a single control), build quadrant 2009-2019 × `sha1(ticker) % 2 == 0`, both halves
agreeing in sign, scored on both populations with the **$10B tier governing** (§1b).

**Declared signs, fixed here from each paper and not from this panel:**
`EquityDuration` **negative** (short duration outperforms), `BetaLiquidityPS` **positive**,
`realestate` **positive**.

**BH at q = 0.10 across the batch, membership fixed in the register**, so dropping a signal at `K1`
or `K3` **shrinks the batch and tightens BH** — and the register pre-commits that this is the correct
behaviour rather than a reason to keep a failing signal in to loosen the threshold.

**Every critical value LABELLED UNCALIBRATED.** `UNIVERSE-BIAS-2` moved the headline to HAC *t*
1.0780 and `STAGE1-BATCH1` states that **no bar measured on the 2,531-name panel transfers and no X7
floor may be quoted.** The hurdle is **derived** at the booked `N`, never typed from this file
(`MB32`).

---

## 6. TRIALS

**3 equity trials** (one per signal), booked **before any runner exists**. **Equity `N` 307 → 310**,
hurdle **derived** at booking. **If `K1` or `K3` drops a signal, the trial for it is still charged**
— `MA6`'s safe direction, and `E-1` kept its trial for exactly this reason even though its arm never
ran. All five kills charge zero under `MB1-SEL`.

---

## 7. VOID CONDITIONS

1. **Adding a signal after reading any kill or any arm.** Membership is fixed at the register.
2. **Pulling all 209 firm-level signals "while we are there."** The pull is **3–5 columns.** A wider
   pull invites a wider batch, and the wider batch is what §2 forbids.
3. **An undated join.** `W-28`.
4. **Resolving an ambiguous cell by picking a permno.** `K4` drops it.
5. **Quoting a bar measured on the 2,531-name panel.**
6. **Reading the check quadrant.**
7. **Reporting a null without its MDE.** `MB22`/`V6`/`S19`: quote the MDE with the verdict or do not
   quote the verdict.

---

## 8. THE LIVE ROUTE

**All three survivors are live-rebuildable and that is why they, and not `PatentsRD`/`CitationsRD`,
are the arm** — `EquityDuration` from book equity, ROE and growth (all mapped in Sharadar, already
rented); `BetaLiquidityPS` from the free monthly Pástor-Stambaugh factor; `realestate` from PP&E
components, **pending `K1`'s column check.**

**OSAP itself is free and its research use is unrestricted.** But **OSAP is a research file, not a
live feed** — the live score must rebuild each signal from Sharadar, so
`COVERAGE-IS-NOT-FIDELITY` applies: **an adoption would need a fidelity gate comparing the
Sharadar-rebuilt signal against the OSAP-provided one on an overlap**, and that gate is **not** in
this register.

---

## 9. EXPECTATIONS

| # | expectation | odds |
|---|---|---|
| 1 | **`K1` drops at least one of the three** | **60/40** |
| 2 | `K3` passes for `EquityDuration` (not a value costume) | 50/50 |
| 3 | **no signal clears on the governing $10B tier** | **85/15** |
| 4 | at least one clears on the wide universe and not the tier (*"REAL BUT NOT INVESTABLE HERE"*) | 35/65 |
| 5 | `realestate` is the weakest of the three | 75/25 |
| 6 | the batch's verdict is reported **with** its MDE and read as *"nothing bigger than our biggest"* | 90/10 |

**EXPECTATION 3 AT 85/15 IS THE HONEST HEADLINE.** Three trials to **close** the last
value-weighted, live-rebuildable, untested corner of the published catalogue is the trade being
proposed — not three trials for a discovery.

---

## 10. WHAT THIS DRAFT DOES NOT CLAIM

It does **not** claim any of the three works — no arm has run and the file is not pulled. It does
**not** claim the other 209 signals are worthless: **it claims 184 of them carry no large-cap
evidence and that the rest are tested, shipped, or sibling-failed here.** It does **not** reopen
`S2`, `P5-3`, `R5`, `W-28`, `A1` or `C3`. It does **not** propose adopting anything. And it does
**not** recommend the brief's own 209-trial design — **it declines it, with the hurdle arithmetic and
the MDE shown in full, and offers the three-trial version instead.**
