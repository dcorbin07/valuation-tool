# PREREG — DIP-CALL-3 — the slow drift, in SHARES, on 1999–2008

**THIS IS THE REGISTER. It is committed ALONE (markdown only, zero `.py`) and is a strict git
ancestor of every commit that computes an outcome** — `RESEARCH_CHARTER.md` §3. Nothing below is
edited after an outcome exists; corrections are reported beside it (`MB1`'s discipline).

**Authorised by Don, `DECISIONS.md` 2026-10-08:** *"calls after a sharp drop in a strong, liquid
company is authorised as a research program — stock-level bounce first, the option expression only
if the bounce survives, then a forward paper book."*

**THE PROGRAM'S NAME IS NOW MISLEADING AND THE REGISTER SAYS SO IN ITS TITLE. THERE IS NO OPTION
ARM AND NO OPTIONS TRIAL.** §8 shows a call cannot capture a 1.1–1.6pp drift against a ±12–28pp
implied move at any strike or tenor on the grid. **Don's authorisation makes the option expression
conditional on the stock bounce; the arithmetic makes it impossible. What survives of his idea is
the same insight in SHARES, and that is what this register tests.**

**PREDECESSORS: `PREREG_dipcall.md` (ALONE at `c5e0b31`, step 1 at `48afffb`) and
`PREREG_dipcall2.md` (ALONE at `23be924`, step 1 at `2ae3a1d`). Both carry over in full — every
amendment `A1`–`A12`, the event definition, the statistic, the no-survivor-filtering rule, the
pass conjunction and the void conditions — EXCEPT where §0 states a change and why.** Carrying
them by reference rather than restating is deliberate: a restated register is a second copy that
drifts (`MA5`), and both are on `origin/main` where any reader can check them.

**EXECUTOR PASS ON `PREREG_DRAFT_dipcall3.md` (scout, commit `7cb4657`). THE DRAFT IS ACCEPTED IN
SUBSTANCE — its charter analysis, its closure of lead 2, and its options arithmetic are adopted
as written — AND AMENDED IN ELEVEN PLACES, every one before any outcome exists.** Two of the
amendments change the design, and one of them runs in the permissive direction and is flagged as
such.

**NOTHING IS ADOPTED. NO REAL TRADE IS PLACED, EVER.**

---

## 0. THE ELEVEN EXECUTOR AMENDMENTS

### B1 — **THE NEWS SPLIT DOES NOT EXIST BEFORE 2004-08-23, SO IT CANNOT BE A PRIMARY AXIS ON THIS ERA**
**This is the amendment that changes the design, and it is a measurement rather than a judgement.**
Measured on the shipped `data/bulk/events.csv`: code 22 carries **385,426 rows, the FIRST dated
2004-08-23**, and **ZERO rows in 1998, 1999, 2000, 2001, 2002 and 2003** (2004 carries 5,766, then
~20,000/yr). `event_spine.EARNINGS_CODE_LEGEND` says the same thing in the tree —
`"first": "2004-08-23"` — so this was knowable without a query and the draft's §3a did not check it.

**The draft's §3a crosses 63 and 126 sessions with the news split to make four primary cells, and
its early half is 1999–2003 — a window with NO earnings coverage whatsoever.**

**AND `A1b`'s GUARD DOES NOT CATCH THIS, WHICH IS THE DANGEROUS PART.** `A1b` fails closed on a
name with no coverage ANYWHERE: `dates_or_unknown` returns `None` and the name is excluded. But a
name with 2005–2008 announcements HAS coverage, so under the inherited rule its **1999 events
would be classified NO-NEWS** — because no announcement falls in their window, for the sole reason
that the source has no announcements then. **That is precisely the fail-open defect `A1b` exists to
prevent, at the ERA level rather than the NAME level, and it would fire on 100% of pre-2004
events** — labelling every dot-com-era earnings crash as "no news".

**FIXED: the news classification additionally requires the EVENT DATE to lie inside code 22's own
coverage window.** An event before **2004-08-23** is **UNKNOWN BY ERA** and may enter neither news
arm. The covered subset is **2004-08-23 → 2008-12-31**.

### B2 — THE FOUR PRIMARY CELLS ARE RESTRUCTURED, KEEPING THE COUNT AND `k`
`B1` makes the draft's 2 × 2 unbuildable. The four cells become:

| # | cell | era | halves |
|---|---|---|---|
| 1 | **POOLED** (news-agnostic), 63 sessions | **full 1999–2008** | 1999–2003 / 2004–2008 |
| 2 | **POOLED**, 126 sessions | full 1999–2008 | 1999–2003 / 2004–2008 |
| 3 | **NO-NEWS**, 63 sessions | **covered subset 2004-08-23 → 2008-12-31** | split at 2006-12-31 |
| 4 | **NO-NEWS**, 126 sessions | covered subset | split at 2006-12-31 |

**Cells 3–4 are the FAITHFUL out-of-sample replication** — `DIP-CALL-2`'s arm was the no-news tier
arm and its banked effects are no-news effects. **Cells 1–2 are a DECLARED DIFFERENT OBJECT**: they
include earnings reactions, and they exist because they are the only way to read the dot-com decade
at all. **Neither reading may be quoted as the other** (void condition 3). **4 cells, 4 equity
trials, `k` = 4 — exactly the count the prompt fixes.**

**The NEWS (earnings-dated) arm on the covered subset is a declared SENSITIVITY carrying NO
verdict.** `DIP-CALL-2` measured news events at **1,669 of 8,074 classified** on eleven years; on
4.4 years it will be thin, and `DIP-CALL`'s whole death was that this arm is structurally
unreachable on a $10B tier.

### B3 — **THE POWER REQUIREMENT IS RE-DERIVED, AND IT RUNS IN THE PERMISSIVE DIRECTION**
The draft's `K1` refuses below **5,274** events. That number pairs the **market-adjusted EFFECT**
(+1.6367pp) with an **inherited own-normal ANCHOR dispersion** (28.28pp) — two different objects —
and the draft's own §5 says that anchor *"is not a measurement"*. `DIP-CALL-2` MEASURED the
realised tier dispersion per definition, and each effect must be paired with ITS OWN:

| horizon | definition | effect | measured sd | required n |
|---|---|---|---|---|
| 63 | own-normal | +2.6574pp | 19.352pp | 942 |
| 63 | **market** | **+1.1176pp** | **11.453pp** | **1,865** |
| 126 | own-normal | +5.0117pp | 33.986pp | 817 |
| 126 | market | +1.6367pp | 16.737pp | 1,857 |

**The binding requirement is 1,865**, not 5,274, because both definitions must clear and the
market-adjusted pair is the demanding one.

**THIS LOWERS A FEASIBILITY BAR BEFORE THE RUN AND THEREFORE NEEDS THE STRICTER SCRUTINY, SO THREE
THINGS BOUND IT.** (a) 5,274 was in a **DRAFT, never a committed register** — the executor pass is
where a draft's arithmetic is corrected, and this draft explicitly invites it. (b) The error is not
a matter of taste: it crosses one definition's effect with another's dispersion. (c) **The bar
actually committed is NOT 1,865 — it is the LARGER of 1,865 and the requirement re-derived from
THIS ERA's OWN measured dispersion** (`K1`, §4). **1999–2008 contains the dot-com crash and 2008,
so its dispersion will be LARGER and the real bar HIGHER** — the correction can only raise the
committed bar above the correctly-paired reference, never lower it.

### B4 — THE ERA, THE TIER SOURCE, AND A 23% COVERAGE HOLE THAT IS COUNTED
* **Era:** 1999-01-01 → 2008-12-31, daily.
* **Tier source:** `data/free_analysis/POOL_SIZE_OOS_PANEL.pkl` — `POOL-SIZE`'s own 1999–2008
  panel, built from the freeze's **full raw** SEP/SF1/SFP. Measured: **1998-12-31 → 2008-07-10,
  39 quarterly dates, 8,474 names, `market_cap` 100% non-null**, and the **$10B tier runs 171 to
  423 names per date, median 272** — so it clears `CONTRACT_MIN_POSITIONS` = 50 by 3.4× at its
  thinnest. **This is the era's OWN universe, not a 2026 selection**, which is why it is used
  rather than `data/backtest` (`PANEL-EXT-RECHECK`: *"the names that are biggest in 2026"*).
* **THE HOLE, MEASURED AND REPORTED RATHER THAN DISCOVERED: 673 names are ever in the era's $10B
  tier and only 518 have a daily price file — 76.97%.** The 155 missing names are **counted and
  listed, never read as zero**. On a 150-name sample of those that do have files, 126 reach back
  to 1999-04 or earlier and 145 span 2004-08 → 2008-06, at a median of 2,579 in-era sessions.
* **Tier membership is POINT-IN-TIME** — the most recent PRIOR quarterly observation (`A12`) —
  **never survival to today.**
* **DISCLOSED, AND IT IS MATERIAL: the tier source ENDS 2008-07-10**, so an event in H2 2008
  carries the **July 2008** cap. That is point-in-time correct (nothing later was knowable) and it
  is stale by up to six months in the one window where caps collapsed fastest. **Every H2-2008
  event is flagged in the artifact** so a reader can see how much of any result rests on them.

### B5 — THE UNIVERSE IS NOT SPLIT BY TICKER HALF, AND THAT IS THE CHARTER'S OWN STRUCTURE
`X1`'s `sha1(ticker) % 2` split exists to keep the **2009–2019 build** cell disjoint from the
**2020–2026 check** cell. `RESEARCH_CHARTER.md` §4(b) treats the pre-2009 eras as a **third and
separate** look and does not halve them, and `POOL-SIZE` read the era whole (11,052 names). **So
DIP-CALL-3 reads the era's full universe.** Declared, because it is more power than a half and the
reason must be the charter's structure rather than the power.

### B6 — THE WHOLE HORIZON MUST LIE INSIDE THE ERA
Carried from `DIP-CALL-2`'s implementation decision 1 and taken on a **global session calendar**,
so the arm rows and the permutation pool obey ONE rule. A 126-session horizon from late 2008 would
otherwise read 2009 prices — the build cell this program has already spent. **An event qualifies
for horizon `h` only if session `t + h` is still inside 1999–2008.**

### B7 — `A3`'s SECOND VOLATILITY-SORT FORM IS CARRIED FORWARD
The draft's `K3` uses only the registered mean per-date |ρ| < 0.30. `DIP-CALL`'s `A3` established
that this form is **small by construction** — at k = 2.5 the flag is 1 on roughly 1.5% of a date's
rows — and added the discriminating form. **Both apply and the kill fires if EITHER exceeds**:
|ρ| ≥ 0.30, or the event rate in the top trailing-volatility quintile ≥ **3.0×** the bottom's.
`DIP-CALL-2` measured 0.0713 and **0.478** (the gradient runs the OTHER way), so this is a
tightening that cost the predecessor nothing.

### B8 — THE MARKET LEG IS THE ERA'S OWN CAP-WEIGHTED RETURN
`A8`'s construction with the era's universe: the **cap-weighted daily return of era panel names
with price files, 1999–2008 only**, weights from the most recent PRIOR quarterly `market_cap`.
Ken French is used **nowhere**. **It is validated against an EXTERNAL yardstick before any arm is
read** — SPY's own daily series over the same sessions, as `DIP-CALL-2`'s `C1` did (0.9782
correlation there). A market leg that is wrong makes every market-adjusted figure wrong in a way
nothing else in the arm would notice.

### B9 — NO OPTION ARM, NO OPTIONS TRIAL, AND THE REASON IS ARITHMETIC NOT POWER
Adopted from the draft's §2 unchanged; restated in §8. **Options `N` is untouched at its live
value.**

### B10 — A PASS IS **FIRST EVIDENCE**, NEVER CONFIRMATION
`DC-1`'s provenance rule, and it binds harder here than there. **The hypothesis is admittedly
POST-HOC**: 63 and 126 sessions were declared NO-VERDICT in `PREREG_dipcall2.md` *before any
outcome existed*, and they are being promoted **because they came back larger**. The draft's own
§1a says that is *"choosing the design on the outcome whether or not the cell was named in
advance"* — and it is right. **What makes this legitimate is that 1999–2008 is genuinely fresh
data, which is what an out-of-sample test IS**; what it does not do is convert a post-hoc cell
into a confirmed one. **A pass is a reason to run a forward paper book, never a reason to
believe**, and it is quoted at **half** its size (McLean-Pontiff) if it ever reaches Don.

### B11 — THE ECONOMIC CASE IS STATED AT THE SIZE DON WOULD ACTUALLY SEE
The draft's +1.79 / +1.93pp/yr are **gross of the McLean-Pontiff halving** the charter's adoption
clause requires. At half size: **+0.90 / +0.97pp/yr**. And they are **ALPHA against the market**,
not total return. §9 states both, because the number that reaches a decision must be the one the
decision would be made on.

---

## 1. WHAT CARRIES OVER UNCHANGED
The event (`r_t ≤ −2.5 σ_{t−1}`, 60-session **strictly prior** scale, 40-observation minimum, on
the **split- and dividend-adjusted** basis — `V6`'s `C5`); entry at the **close of session t** with
the horizon over *t*+1 … *t*+*h* (`A9`); **BOTH** abnormal-return definitions reported and quoting
one alone **FORBIDDEN** (`DC-1`, and `DIP-CALL-2` is the proof it was needed — own-normal met every
pass condition and **was the market**, an identity measured to 0.0062pp); standard errors
**clustered on event date AND on ticker**, clearing required under **BOTH** (`A2`); the arm's own
**within-date permutation p95**, 500 draws; **no survivor filtering**, with `A11`/`E-5`'s
terminal-versus-administrative split counted both ways; the **+0.67pp** round-trip economic floor
(`A4`, **LABELLED AN EXTRAPOLATION** from `B11`'s measured 33.4bps one-way on a different book);
**TWO-SIDED** *p* (`A6`); **every critical value LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`) with no
X7 or `CORRECTED-FLOORS` floor quoted for a daily event study; and the hurdle **DERIVED at run
time**, never typed here (`MA5`, `MA37`, `MB32`).

---

## 2. THE PASS CONDITION
A cell passes iff **all** of: the point estimate is **POSITIVE**; it is **≥ +0.67pp per window**;
it clears its **own within-date permutation p95** and |*t*| > the derived hurdle under **BOTH**
clustering readings; in **BOTH** halves with the same sign; under **BOTH** abnormal-return
definitions; and its two-sided *p* survives **BH at q = 0.10, `k` = 4**.

**Ambiguous against any of these is a NULL, not a judgement call** (`RUN_RULES` PART A rule 6).

---

## 3. THE FREE PRE-OUTCOME KILLS — run and READ in their OWN pass
`O10`'s process defect is not repeated: the kill pass is a separate invocation, its artifact is
written first, and **the arm REFUSES to run without it**.

* **`K0` COVERAGE AND TIER SIZE.** The 155 price-file-less tier names counted and listed; the
  per-date tier name count shipped (charter Stage 1b); **every date must clear
  `CONTRACT_MIN_POSITIONS` = 50** or the arm is NOT ASSESSABLE on the governing population.
* **`K1` THE DESIGN EFFECT AGAINST ITS OWN SHUFFLED NULL, AND THE REQUIRED-n REFUSAL.** `R3` is
  why the null is mandatory: **600 independent draws in 12 blocks returned a design effect near 1.8
  from sampling error alone**, so a raw design effect is not evidence of clustering and applying one
  as a haircut would manufacture a correction out of noise. The effective-n **bracket** is reported,
  never either end alone. **THE ARM REFUSES on any cell whose effective n falls below
  `max(1865, required_n(effect, THIS ERA's own measured pre-outcome dispersion))`** — per `B3`, and
  the era's own figure is expected to be the larger.
* **`K2` NEWS COVERAGE ≥ 0.70** of tier names **on the covered subset only**, UNKNOWN names counted
  and excluded by name (`A1b`) and pre-2004-08-23 events excluded by era (`B1`). It gates cells 3–4
  and is **meaningless on the full era**, where coverage is zero by construction.
* **`K3` THE EVENT MUST NOT BE A VOLATILITY SORT** — `B7`'s two forms, fires if EITHER exceeds.
* **`K4` THE DISPERSION IS MEASURED** on this era's own rows and the power table re-derived from it
  (`A10`), with the direction of its error labelled: a trailing pre-outcome estimate understates
  post-event dispersion, which **overstates power**, and the MDE that travels with any verdict
  comes from the arm's **own realised clustered se** (`MB8`).

**A kill firing stops the program at zero further trials and is the cheapest good outcome
available to it** (`DC-1`).

---

## 4. TRIALS AND BENJAMINI-HOCHBERG
**4 EQUITY trials**, booked **before any runner exists**, re-read from `research_log.detail()`
after merging `origin/main`. **`k` = 4, q = 0.10** — thresholds .02500 / .05000 / .07500 / .10000.
**A cell that cannot be built is NOT RUN and `k` STAYS 4**, because shrinking it makes every
surviving threshold easier (`W-28`). **ZERO options trials and no option arm** (`B9`).

**SENSITIVITIES CARRYING NO VERDICT, fixed now:** 5 and 21 sessions (the mirror image of
`DIP-CALL-2`, and declared as such); the NEWS arm on the covered subset; k ∈ {2.0, 3.0}; the
quality/health overlay; `V6-B`'s health floors.

---

## 5. VOID CONDITIONS
1. Quoting a 5- or 21-session reading as a verdict.
2. Quoting one abnormal-return definition without the other.
3. **Quoting the POOLED cells as a statement about the no-news drift, or the reverse** — they are
   different objects on different eras (`B2`).
4. Relaxing any bar in §2 or §3 after seeing it fail (`W-28`).
5. Promoting a sensitivity without its own later register.
6. **Reading this era a second time for this program.** It is ONE read and after it the era is
   spent for DIP-CALL.
7. Touching the **check quadrant** (2020–2026 × half 1) anywhere — not read, and not censused.
8. Quoting a pass as confirmation rather than first evidence (`B10`).
9. Conditioning the headline on the quality/health score (`P1S0`, `V6-OPT`).

---

## 6. PROVENANCE AND THE DISCLOSURES THE CHARTER REQUIRES
* **`POOL-SIZE` HAS ALREADY READ 1999–2008 ONCE**, for pool width — labelled in its own memo
  *"A LABELLED PROXY FOR POOL WIDTH, NOT A TEST OF THE SHIPPED COMPOSITE"*, five themes, 11,052
  names, 39 quarterly dates, 1998-12-31 → 2008-07-10. **This is a different question on the same
  data** — a daily price event study against a quarterly pool ladder — **and that is a real cost,
  not a technicality.**
* **THE FIVE-THEME LIMITATION DOES NOT BIND THIS ARM, and the reason is specific.** Charter §5
  Stage 3 restricts the 1999–2008 proxy because `institutional` has no pre-2009 source (SF3 starts
  2013-06-30) and `insider` reaches only 0.307 by 2008. **Those are statements about THEME
  COVERAGE. This arm reads prices and nothing else** — no theme, no composite, no 13F, no Form 4 —
  **so it inherits the data boundary (satisfied: SEP reaches 1997-12-31) and none of the theme
  restriction.**
* **`DC-1`'s TWO COMMITMENTS, CARRIED.** Its mechanism *"was generated from two names Don holds,
  both of which recovered — selection on the outcome three times over"*: if the panel is ever
  extended past 2026-01-28, **`NOW` and `CRM` are EXCLUDED BY NAME**; and a positive result is
  **FIRST evidence, never confirmation** (`B10`).
* **AND THE SAME HAZARD IN THIS PROGRAM'S OWN FRAMING:** *"such companies recover"* is an
  observation about companies that **did**. `A12` defines the tier at the event date and `A11`
  keeps the ones that did not recover in the sample.

---

## 7. LEAD 2 IS CLOSED AT ZERO TRIALS, AND NOT BY THIS REGISTER'S CHOICE
Adopted from the draft's §1c unchanged, because its third reason is decisive on arithmetic: the
unit of observation is a **DATE**, so an effect of **+0.5317pp per 21-session window** against a
21-day market SD of **4.47pp** needs **~1,251 independent non-overlapping windows ≈ 104 years**,
and at the forward contract's own frozen σ it needs **53 years**. **This project holds 27 years of
daily data in total.** The claim is also partly mechanical on a rising window: 2009–2019 is the
longest bull market on record, so **any** rule buying after down days earns above-average forward
returns **by construction**. **A successor may not spend the check quadrant on it.**

---

## 8. WHY THERE IS NO OPTION ARM — adopted from the draft's §2
A 63-session ATM call's implied move is `σ·√(63/252)`:

| implied vol | 63-session move | the drift | drift as a share |
|---|---|---|---|
| 25% | ±12.50pp | +1.1176pp | **8.9%** |
| 30% | ±15.00pp | +1.1176pp | **7.5%** |
| 40% | ±20.00pp | +1.1176pp | **5.6%** |

At 126 sessions the shares are **9.3% / 7.7% / 5.8%**. **The drift is 5.6%–9.3% of the move the
option already prices, and implied volatility is ELEVATED exactly when this strategy buys** — by a
measured **+17.71%** over the name's own trailing 252-day median (`V6-OPT` stage 1), decaying only
**−16.56%** by t+30. **So DIP-CALL is foreclosed as an options program on arithmetic alone,
whatever this register returns. This is not a power statement and no amount of data changes it.**

---

## 9. WHAT A PASS WOULD BE WORTH, AFTER COSTS — the number for Don
The round trip is paid **per trade**, so a longer hold pays it fewer times. On `DIP-CALL-2`'s own
banked market-adjusted effects and its own **+0.67pp** floor:

| horizon | effect/window | round trips/yr | gross/yr | cost/yr | **net/yr** | **at HALF size** |
|---|---|---|---|---|---|---|
| 5 | +0.0534pp | 50.4 | +2.69pp | 33.77pp | **−31.08pp** | — |
| 21 | +0.5277pp | 12.0 | +6.33pp | 8.04pp | **−1.71pp** | — |
| **63** | +1.1176pp | 4.0 | +4.47pp | 2.68pp | **+1.79pp** | **+0.90pp** |
| **126** | +1.6367pp | 2.0 | +3.27pp | 1.34pp | **+1.93pp** | **+0.97pp** |

**The 21-session cell fails on cost — which is exactly what `DIP-CALL-2` measured — and 63 and 126
clear it at about +1.8 to +1.9pp/yr, or +0.9 to +1.0pp/yr at the size the charter would quote.**

**STATED AGAINST ITSELF, because this is the whole economic case:** it is **ALPHA against the
market and not a total return**; it is **small**; it is gross of slippage beyond the modelled
floor; it assumes **continuous reinvestment the event rate may not supply** (and the capital-
weighted question is `O11`'s, unanswered here — `O11` measured a **+3.27%/trade** book ending
**−25.9%** at cap 10); and it is measured **in the window where it was discovered**. **It is a
reason to test, not a reason to believe.**

---

## 10. EXPECTATIONS, registered before any outcome exists
Adopting the draft's priors: **the drift surviving 1999–2008 at 20–25%**, and surviving in a form
worth trading at **10–15%**.

1. **`K1` REFUSES at least one cell** — 60/40, and the no-news covered-subset cells are the ones at
   risk: a labelled estimate puts them near **3,200 raw events** against ~1,865 required, which at
   `DIP-CALL-2`'s measured design effect of **2.1009** is ~1,520 effective — **below the bar**. The
   pooled full-era cells estimate near **9,400 raw**.
2. **This era's measured dispersion EXCEEDS 2009–2019's** — 85/15. Dot-com and 2008.
3. **The two abnormal-return definitions disagree by more than 2×** — 70/30, on `DIP-CALL-2`'s
   measured 3.11× at 21 sessions and the identity behind it.
4. **At least one cell flips sign between halves** — 70/30. 1999–2003 and 2004–2008 are different
   regimes, and this is the record's most repeated pattern.
5. **No cell passes §2** — 75/25, the modal outcome, and the binding constraint is expected to be
   the **both-halves** rule rather than significance or the cost floor.
6. **The POOLED and NO-NEWS readings disagree** — 55/45; a disagreement is a reported finding.

---

## 11. WHAT THIS REGISTER DOES NOT DO
* **It adopts nothing and places no trade, ever.**
* **It registers NO option arm and books NO options trial** (`B9`, §8).
* **It does not touch the check quadrant** — not read, not censused — so **2020 and 2022 remain
  unspent**.
* **It does not re-open or overwrite `DIP-CALL-2`.** Its step-1 failure stands as measured, and
  this register adds no verdict to its no-verdict cells — it tests them **elsewhere**.
* **It does not re-open lead 2** (§7), nor `V6`, `V6-B`, `V6-OPT`, `DC-1`, `O17C4` or `R2`.
* **It does not open the 1972–1998 WRDS era** — `OOS1`'s Gate B reads **0.837303** against **0.90**.
* **It re-derives no landed figure** — `B11`'s 33.4bps, `V6-OPT`'s IV elevation, `O11`'s caps and
  `DIP-CALL-2`'s banked effects are **charged as inputs**.
* **It quotes no hard-coded trial count, hurdle or vintage** — all three are derived at run time.
