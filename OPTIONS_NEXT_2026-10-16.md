# OPTIONS — WHAT IS STILL WORTH TESTING — 2026-10-16

**A MEMO, NOT A REGISTER. ZERO TRIALS.** Nothing is run, nothing is adopted. Two censuses are
reported — one already banked, one measured here and declared as a census — and **no forward
return is read anywhere.** Every figure is landed or is arithmetic on landed figures shown in full.

Companion drafts committed alongside: **`PREREG_DRAFT_earnings_csp.md`** and
**`PREREG_DRAFT_f21b_stress_gate.md`**.

**THE HURDLE IS DERIVED, NEVER QUOTED: options `N` = 323, `sqrt(2 ln N)` = 3.3993094 today.**
**`SEASON3_MAP.md` §7's whole options cost curve is computed on basis 307 and `IDEAS_LEDGER.md`'s
header reads 305** — **both are stale and every hurdle in them must be re-derived.**

---

# PART 1 — O-1's DATA QUESTION. **IT IS ALREADY ANSWERED, AND THE ANSWER IS NO**

The prompt asks for a census. **One has already been run and shipped, and re-running it would be
the duplication this memo exists to prevent.**

> **`O1-PULL`** (`VALQUO_LEDGER.md`): *"**DONE — SHIPPED 2026-08-25; STAGE 1 COMPLETE, STAGE 2 NOT
> RUN AND NAMED.** FACTS — zero trials; **flagged coverage 74 names to 2,969 cells, which is 0.82x
> O-1's own 3,600 floor, so the floor is unreachable at the primary tenor even from a complete
> pull.**"*

**SO THE THREE QUESTIONS HAVE ANSWERS:**

**(a) How many flagged name-dates have listed options?** The targeted pull took O-1's usable set
from **74 flagged trades to 2,969 cells**. Against `MA28`'s **6,542** flagged panel cells that is
45%, and against the floor it is **0.82×**.

**(b) How much put-chain history does a test need?** `O-1`'s own floor is **3,600 trades**
(1,200 per half), and `MB22`'s `required_n` independently returns **3,643** at 0.07 SD and
`N` = 308. **A complete pull reaches 0.82× of it. The design cannot be powered.**

**(c) What would the pull cost?** **NOT IN THE RECORD as a dollar figure** — there is no $/GB,
per-unit or per-symbol-year price anywhere, and `HANDOFF_optionsbot.md` contains no `$` amounts at
all. What exists: ThetaData **subscription tiers — $40 / $80 / $160 individual, from $250/mo
commercial** (`HANDOFF_data_spend.md`, verified against the pricing page, with the individual tier
*"personal use only"*), and the **physical** census — `D:\thetadata\HARVEST_CENSUS.json`: **2,850
banked symbol-years, 353,685,737 rows, 17.692 GB**, i.e. **≈6.2 MB and ≈124,100 rows per
symbol-year**. **The cost question is MOOT**: a complete pull does not reach the floor, so there is
nothing to buy.

**AND THE REASON IS STRUCTURAL, WHICH IS WHY NO PULL FIXES IT — I MEASURED THE MECHANISM
INDEPENDENTLY AND IT AGREES.** `MA28`'s flag fires on names with a **median market cap of
$2.69bn**. Chain-file coverage of the corrected panel's options-era cells (41 of 69 dates are
≥ 2016-01-04), by market cap:

| market cap | era cells | with a chain file | **coverage** |
|---|---|---|---|
| < $1bn | 8,036 | 100 | **1.24%** |
| **$1–2.69bn** | 12,972 | 479 | **3.69%** |
| $2.69–5bn | 10,324 | 709 | **6.87%** |
| $5–10bn | 11,996 | 2,371 | 19.76% |
| $10–50bn | 20,092 | 9,680 | 48.18% |
| > $50bn | 7,328 | 5,864 | 80.02% |
| **all** | **70,748** | **19,203** | **27.14%** |

**And the ceiling is not the cache, it is listing itself.** The fleet's own `optionable` gate holds
**487 names** (471 in the panel, **18.61%** of its names, **25.17%** of era cells) at a **median
cap of $30.28bn and a p05 of $4.31bn** — and **only 2.41% of era cells at or below the flagged
median of $2.69bn are optionable at all.**

> **`MA28`'s FLAG FIRES ON NAMES TOO SMALL TO HAVE LISTED OPTIONS. THE PUT THAT WOULD BUY THE
> CRASH DOES NOT EXIST, AND THAT IS NOT A DATA PURCHASE — IT IS A FACT ABOUT WHAT IS LISTED.**

**ONE SECONDARY ROUTE EXISTS AND CARRIES NO VERDICT:** `O-1` ran at **150–210 DTE** (`target_dte`
180) and the harvest reaches past 200 DTE **for 2016–2018 only** — which is most of why its
coverage was 5.89%. **A SHORT-TENOR version of O-1 would have far better coverage** (§3's funnels
show 49% at short tenor against 17% at 25–45 DTE), and `O-1`'s declared **secondary 330–400 DTE
tenor was NOT RUN and carries no verdict.** **But a tenor change is a different register**, and
`O-1`'s left-tail finding — risk-neutral **1.5299** [1.1902, 1.9201] against `MA28`'s physical
**3.0422** — was measured at 150–210 DTE and may not be assumed to transfer. **Recorded as the one
non-closed thread, not recommended.**

---

# PART 2 — THE DTE QUESTION, IN PLAIN WORDS. **AND THE PROMPT'S OWN PREMISE IS WRONG**

Don asked: *"Maybe not use the same DTE for every trade?"* Here is what the record actually says.

## 2a. THE CORRECTION FIRST, BECAUSE TWO FILES STATE IT WRONGLY

The prompt — following `HANDOFF_optionsbot.md:3936` and `CLAUDE.md`, which both say *"the alert's
own expectancy climbs monotonically with tenor"* — describes `O13` as finding expectancy rising
with tenor **on both the alert and the random-day book.** **Measured from `O13_ANTISIGNAL.json`,
neither half of that is right:**

| `dte` quintile | **alert** | **control** | gap | n alert |
|---|---|---|---|---|
| q1 (shortest) | **−0.3513%** | 6.2902% | −6.6415pp | 907 |
| q2 | +0.3584% | **11.2002%** | **−10.8418pp** | 845 |
| q3 | **+6.3516%** | 8.0254% | −1.6738pp | 644 |
| q4 | **+4.1747%** | 7.8787% | −3.7040pp | 771 |
| q5 (longest) | **+7.6276%** | 8.0535% | −0.4259pp | 703 |

* **THE ALERT BOOK IS NOT MONOTONE: q3 (+6.35%) EXCEEDS q4 (+4.17%).** The endpoints rise
  (−0.35% → +7.63%) and the word "monotonically" is wrong in both files.
* **THE CONTROL IS NOT RISING EITHER — AND IT IS NOT FLAT.** Its best cell is **q2 at +11.20%**,
  and q1 ≈ q3 ≈ q4 ≈ q5 ≈ 8%. **So on the one genuine random-entry book in the record, tenor shows
  no trend at all.**
* **AND `O13`'s OWN VERDICT IS THAT IT FAILS: `S_worst` 0.4718 against its own calibrated p95
  0.4974**, clearing the **early half only**, with `features_clearing_both_halves` an **empty list
  for all 32 arms.** Its own wording: *"suggestive and not distinguishable from noise by the
  pre-registered bar."*
* **THE DECOMPOSITION CLOSES "TRADE LONGER-DATED" AS A REPAIR**: `dte`'s rate component is
  **−5.0176pp** and its mix component **+0.0141pp** of a −5.0640pp total. **The alert's loss is
  within-bin, not composition — so changing which tenor it buys cannot fix it.**

> **SO WHAT CLIMBS WITH TENOR IS THE ALERT BOOK'S EXPECTANCY, I.E. THE ALERT'S DAMAGE SHRINKS AT
> LONG TENOR (the gap narrows −6.64 → −0.43pp). THAT IS A STATEMENT ABOUT THE ALERT, AND THE ALERT
> IS CLOSED** (`DECISIONS.md` 2026-10-16: *"it loses to random days in every score band and at
> every threshold"*).

## 2b. AND EVERY ALERT-FAMILY DTE CONCLUSION LIVES INSIDE A 30-DAY WINDOW

`O13`, `O17`, `O17C4`, `EVOWN`, `R2`, `MB1`, `O10`, `O18`, `O12` and `O21` all run on the engine's
fixed **`DTE_RANGE = (45, 75)`** (`options_backtest.py:122`). **So "expectancy rises with tenor"
in that family means "rises between 45 and 75 days", measured on a book that loses to random
entry.** `O17`'s own quartile edges make it explicit: **45–50, 51–57, 58–65, 66–74.**

`O17`'s unfiltered expectancy by that quartile — **+0.376, −0.877, +6.736, +8.584pp** — does rise,
and it is **the same alert book**, so it is the same statement.

## 2c. `EVOWN` — AT 45–75 DTE, TENOR REMOVES A CHOICE RATHER THAN OFFERING ONE

`MB_EVOWN_CENSUS_B.json`: at K = 5 the engine's menu is non-empty on **4,769** events and
**4,769** of those span the announcement — `menu_rate == spans_rate` to **sixteen digits** at
every K. And the DTE-matched control spans anyway on **16,943 of 27,350 = 61.95%**.

> **AT 45–75 DTE A CONTRACT CANNOT AVOID AN EARNINGS ANNOUNCEMENT. "OWNING THE EVENT" IS NOT A
> DESIGN CHOICE THERE — IT IS WHAT THE TENOR DOES TO YOU. THE ONLY WAY TO MAKE IT A CHOICE IS TO
> LEAVE THAT BAND**, which is exactly what `F-4`'s tag says (*"only < 40 DTE can avoid events"*)
> and what `PREREG_DRAFT_earnings_csp.md` does at ~15 DTE.

## 2d. ON THE LONG SIDE, LONGER TENOR IS PRICED AND IT IS DEARER

`SC-3`'s four pre-declared strata, all-in bps/yr: **915.4 → 798.0 → 676.5 → 757.9** at
200–300 / 300–450 / 450–650 / 650–858 DTE. **NOT MONOTONE — it bottoms at 450–650 and rises
again**, because the call leg's absolute half-spread runs **$0.95 → $1.55 → $1.70 → $2.05** while
the MID financing excess rises monotonically **112.8 → 162.4 bps.** Every interval sits above
Robinhood Gold's `rf + 420`, and `DEEPITM-FIN`'s 60–90 DTE all-in is **701.87 bps/yr** (median DTE
73, **5.0 rolls/yr**) — so the best long tenor only **ties** the short one, its interval
[641.8, 713.7] **containing 701.87**.

> **ON THE LONG SIDE THE TENOR QUESTION IS ANSWERED AND THE ANSWER IS THAT TENOR BUYS NOTHING:
> financing costs 6.8–9.2%/yr at every tenor owned, against drifts the record measures in single
> percents.**

## 2e. ON THE SHORT SIDE TENOR MATTERS A GREAT DEAL — AND IT IS ARITHMETIC, NOT A SIGNAL

**`K3`'s income is `premium_fraction × 252 / dte`, so the tenor is half the denominator.**
§89 recorded what getting that wrong costs: quoting a 37-DTE figure as `F-10`'s *"would have
claimed 0.89 years of headroom where the truth is 0.14 — a six-fold overstatement, in the
flattering direction"*, **and the shortcut that looks equivalent is also wrong — holding the
premium fraction fixed and changing only the turns INVENTS income, because a longer-dated put
collects more premium.** (I made the matching error once in `FLEET_UNARMED_REVIEW.md`, caught it
by recomputing with the pricer, and §89 confirms the correction independently.)

**THE CLEAN TENOR COMPARISON NOBODY HAS QUOTED AS ONE** — `FLEET_RETIREMENTS.md`, same universe,
same 25-delta strike rule, each book at its own declared tenor, zero trials:

| | build 2016–2019 | check 2020–2025 |
|---|---|---|
| **30 DTE** (`F-4`'s) | **4.7539 yr** on **9.0474%/yr** (n 5,974) | **3.5185 yr** on **12.0122%/yr** (n 10,426) |
| **52 DTE** (`F-10`'s) | **5.8598 yr** on **7.2076%/yr** (n 3,046) | **4.4281 yr** on **9.3600%/yr** (n 5,408) |

> **ON THE SHORT-PREMIUM SIDE, SHORTER TENOR IS BETTER ON BOTH AXES — MORE INCOME PER YEAR AND MORE
> CRASH-BAR HEADROOM — IN BOTH QUADRANTS. AND THE STRIKE RULE DOMINATES THE TENOR: at 0.90
> moneyness and 30 DTE `K3` fires at 11.57 years; at 25 delta on the same tenor it is 4.7539, a
> 2.43× improvement from the strike alone.**

Caveat travelling with those figures (`MB8`): the population is `SELL-PREMIUM-2`'s universe entered
on **random days** — the best available non-dip proxy, **not** either book's own names.

## 2f. SO: IS ANY DTE DESIGN UNTESTED AND WORTH A REGISTER?

**NO LANDED OPTIONS ITEM HAS EVER VARIED DTE AS A PER-TRADE RULE.** Every one used a fixed band or
pre-declared strata. **The single exception is `O7`'s straddle, whose expiry is event-anchored**
(first expiry strictly after the announcement, ≤ 45 days) — and that is a richness measurement,
not a return strategy. **So Don's instinct is correct that it is untried.**

**TWO CANDIDATES EXIST AND BOTH ARE ALREADY ON THE BOOKS:**

* **`MB2` — the 4 × 4 DTE × delta grid — is PARKED BY DON (2026-08-19), not closed.** Sixteen
  cells, **sixteen trials booked before the run**, and the audit's own prior is **~7%** that any
  cell is actionable. **It should stay parked**: three corners are already measured
  (`DEEPITM-FIN`, the banked book with `R2` standing, and `P1S0`'s closure of the vehicle), and
  **its own RETURN CONDITION is NOT MET** — it required *"a confirmed selection-matters finding"*
  and `MB1-SEL` is **`VOID BEFORE THE ARM — the gating control fired.`**
* **`MB2`'s OWN ONE-CELL VERSION IS THE ONLY TENOR REGISTER I WOULD RUN**, and it is named in its
  own text: *"**60–90 DTE × 0.85–0.95 delta ALONE, 1 trial**, framed as `DEEPITM-FIN`'s return-side
  companion, pre-committing that its failure closes the tenor question permanently rather than
  prompting a fifth tenor."* **One trial, a pre-committed permanent closure, and a corner nobody
  has read on the return side.** `SEASON3_MAP.md`'s own open question #4 for Don asks exactly
  this — *"Unpark the single 60–90 cell into `B-14`, or keep parked?"* — **and is unanswered.**

**AND THE HONEST VERDICT ON THE PER-TRADE DTE IDEA ITSELF: a per-trade tenor rule needs something
to condition on, and the record has no measured conditioner.** `O13`'s own `dte` arm is the closest
thing and it fails its calibrated bar with an empty both-halves list. **A rule that varies DTE on
nothing is a grid, and a grid is `MB2`.** **What IS worth doing is choosing a FIXED tenor on the
arithmetic of §2e rather than inheriting 45–75 from the engine — which is what
`PREREG_DRAFT_earnings_csp.md` does at ~15 DTE, for a measured reason** (shorter tenor turns
capital faster and is the only band where event ownership is a choice).

---

# PART 3 — THE RANKING

**ONE MEASUREMENT I MADE WHILE RANKING CHANGED THE ORDER, SO IT GOES FIRST.**

> **`SELL-PREMIUM-2`'s AFFORDABILITY WALL IS A SIZING RULE, NOT A STRATEGY PROBLEM.** §84 reports
> that at $25k the book *"skips 2,060 of 2,610 trades because ONE contract ties up more than
> $2,500"* — and **$2,500 is `account ÷ cap` at cap 10.** The surviving trades are therefore only
> those on **sub-$25 stocks**. Reconstructed from the banked picks: **7.43% of events have
> `strike × 100 ≤ $2,500`** against the measured **5.98% taken** (the gap is the concurrency cap),
> so the wall is reproduced. **At cap 3 the slot is $8,333 and 60.31% of events become
> affordable — an 8.1× increase in the tradeable event set, with no change to the strategy, no
> spread, and no new broker.**
>
> | account | cap | per slot | affordable share of events |
> |---|---|---|---|
> | $25k | **10** | $2,500 | **7.43%** |
> | $25k | **3** | $8,333 | **60.31%** |
> | $50k | 10 | $5,000 | 34.56% |
> | $10k | 3 | $3,333 | 13.83% |
>
> **The cost is diversification — one assignment is a third of the book rather than a tenth — and
> that is the trade to measure. It is an `O11` sizing question, it charges at most one trial, and
> it is the cheapest thing on this list by a wide margin.**

| # | candidate | what it costs | why here |
|---|---|---|---|
| **1** | **Re-size, don't re-design: `SELL-PREMIUM-2`'s cap at a real account** | **≤1 options trial**, no new data, no broker | The strategy already **passed every clause** on the build quadrant. The thing that made it earn 1–2%/yr is `account ÷ cap`, and the fix is a constant. **Highest EV per trial on the board, and it is not a new hypothesis** |
| **2** | **`EARNINGS-CSP`** (drafted) | **3 options trials**, Level-2 clean, no new data for stages 1–2 | `O7` measured the richness over **6,013 events**; the **selling side has never been tested at any tenor**; the entry **cannot load the book into a crash**, which is the single defect that killed `SELL-PREMIUM-2`'s check read. **Gated on a free kill that can stop it for nothing** |
| **3** | **`MB2`'s ONE CELL — 60–90 DTE × 0.85–0.95 delta** | **1 options trial** | The only genuinely untested tenor corner, **pre-committed to close the tenor question permanently either way**. Needs Don to unpark it; `SEASON3_MAP`'s question #4 |
| **4** | **`F-21b` stress gate** (drafted) | **≤1 trial, no new book, no new fills** | Costs almost nothing to freeze and **cannot resolve in under ~17 years** (§3 of its draft). Worth starting *because* it is slow, not despite it. Judgement, not a verdict |
| **5** | **`B-14` liquidity × tenor 2×2** | **2 options trials**; `S3-I5` is DONE so it is runnable | Carries the tenor axis honestly as a 2×2 rather than a 16-cell grid, and `MB2`'s single cell could fold into it |
| **6** | **`B-13` alert-density regime** · **`B-0c` menu breadth** | 1 trial each, no dependency | Cheap and unblocked, but both attach to books the record has closed |
| — | **`O-1` at short tenor** | 2+ trials | **Not recommended.** §1's ceiling is listing, not data; only the tenor thread is non-closed and its left-tail finding was measured at 150–210 DTE |
| — | **`B-G1` index-chain** · **`B-G2` FDA** · **`B-G3` borrow** | 1–2 trials **plus a purchase** | Gated on money (`B-G1` ~$150/mo pre-authorised pending Don) or on data that does not exist (`F-14`'s catalyst spine is **built and empty**) |

## CLOSED — one line each, so nobody re-runs it

| item | closed because |
|---|---|
| **The alert-driven long-call entry (`R2`)** | loses to random entry by **−5.0640pp/trade**, z −4.9612; `DECISIONS.md` 2026-10-16 will not re-open it |
| **`O9` — IV rank as sell-timing** | effect **flips sign across SPY/QQQ/IWM**; closed by its own pre-registration. **Index vol-timing only — it did not close single-name premium selling, and `SELL-PREMIUM-2` later passed stage 1** |
| **`O-SEED-5` — calendar spreads at earnings** | two legs pay `D9`'s costs **twice** on a **0.67%-of-spot** differential. **The cost half still binds; its "`O9` closed the family" half is contradicted by `SELL-PREMIUM-2`** |
| **`A3` — alert-day credit spreads** | **−7.99%/trade** of max risk, and **+0.13% at a fill nobody can achieve** — *"there is no premium"*. (**Its ledger row is NOT IN THE RECORD**, and the id collides with `O6`'s A3 arm — worth fixing) |
| **`DIP-CALL` 1/2/3** | the bounce is real, **smaller than the cost**, and ±12.5–20pp of implied move swamps a 1.12pp drift |
| **`F-15` insider-cluster calls** | the 60-DTE ATM call needs **4.85%** at IV 0.30 against a published **1.64%** drift — **short by 3.0×**. Signal moved to shares (`DECISIONS.md` 2026-10-13) |
| **`U7` composite-as-options-veto / `U1`** | bottom decile is the **third most profitable**; the composite is mostly a size sort inside the options universe |
| **`P1S0`** | the options-expression family closed at its power anchor |
| **`SELL-PREMIUM` (0.90 moneyness)** | `K3` at **8.90 years** against 6.0 — the strike surrendered the income |
| **`SELL-PREMIUM-3` (spreads)** | **NOT CONFIRMED and UNDERPOWERED** on stage 1 (halves **+4.5871%** / **−1.2132%**, no cell above 0.77× its MDE) — **and Level 2 forbids it on Don's account anyway.** Check read NOT spent |
| **Ten fleet books** | retired 2026-10-13 with the result that closed each, mechanically enforced |
| **`MB15-SLIM`, `INV-C`** | unpowered by construction / killed at the author's desk |

**AND TWO RECORD DEFECTS FOUND WHILE RANKING, REPORTED NOT FIXED** (`RUN_RULES` rule 3):
**(a)** `HANDOFF_optionsbot.md:3936` and `CLAUDE.md` both say `O13`'s alert expectancy *"climbs
monotonically with tenor"* and **q3 (+6.3516%) exceeds q4 (+4.1747%)** — the endpoints rise and the
word is wrong. **(b)** `DECL_f4_eventfree_premium.md` states *"code-22 runs 1.65 events/ticker-yr"*
and **that figure matches none of the three measured densities** (`bulk.py`'s repo-wide **2.83**,
or the megacap book's **median 3.96 / mean 4.14**); **its provenance is not in the record.** Both
are the owning lanes' to correct.

---

# FOR DON — PLAIN WORDS

**The ranked list, shortest first.**

1. **Change one number before testing anything new.** The put-selling strategy that passed every
   one of your tests earns 1–2% a year at $25k for a reason that has nothing to do with the
   strategy: the book divides your account into **ten** slots, so each slot gets $2,500 and only
   stocks under $25 fit. **Three slots instead of ten would make 60% of the trades affordable
   instead of 7%.** That is a one-line change, costs at most one trial, and it is the cheapest
   thing on this list. The price is that one bad assignment hurts three times as much — which is
   exactly what should be measured.
2. **Sell the earnings premium instead of buying it.** We measured years ago that earnings options
   are expensive — the implied move is 5.45% against a realised 4.78%, and the move only beat the
   implied 35% of the time — **and nobody has ever tested selling it.** It is cash-secured puts
   only, so it works on your Alpaca account with no spread and no new broker. **And it fixes the
   thing that broke the last one: an earnings date is set by a company's calendar, so the rule
   cannot load you up right before a crash** — which is exactly what the dip rule did in 2020.
3. **One tenor test, one trial, and it closes the question for good.** You asked about not using
   the same DTE every time. The honest answer is in Part 2: on the buying side longer tenor just
   costs more financing; on the selling side **shorter is better on both axes**, measured. There is
   one corner nobody has read, you parked it yourself in August, and its own design says that if it
   fails, the tenor question is closed permanently. That is worth one trial.

**The one thing I would test first: number 1.** It is not a new idea, it costs almost nothing, and
it is the difference between a strategy that works on paper and one you could actually run.

**What it costs.** Number 1: **≤1 trial, $0.** Number 2: **3 trials, $0** for the historical part —
but the **forward paper book needs an earnings calendar we do not have**, which is a free-data
problem to solve before it can ever go live. Number 3: **1 trial, $0**, and your word to unpark it.

**And three things to know before any of it.** The crash test that passed and then let the book
lose its worst year is the record's sharpest warning — **`SELL-PREMIUM-2`'s crash arithmetic
cleared at 3.42 years against a 6.0 bar and 2020 was still the worst year in the book** — so I have
deliberately **not** written a crash bar into the earnings draft; it reports two measured
disclosures instead. **The spread version is dead on your account**: Level 2 does not allow
spreads, and it failed its own first stage anyway. And **nothing can reach a forward verdict until
the paper fleet is actually trading** — it has never placed an order, which is why you put that
first.
