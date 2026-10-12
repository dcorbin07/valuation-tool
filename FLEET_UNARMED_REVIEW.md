# FLEET REVIEW — the 14 books declared and never armed (item 46)

**A REVIEW, NOT A REGISTER. ZERO TRIALS.** Nothing is run, nothing is adopted, no fill is placed,
no declaration is edited. Every verdict below cites a **landed measurement** or a **standing ruling
of Don's**; where neither exists the book is kept and the reason is a horizon or an unmeasured
hurdle, said as such.

**THE SET IS DERIVED, NOT QUOTED, AND IT CORRECTS A LIST I HAD WRONG.** `fleet_books.RULES` holds
the armed books and it has **FOUR** entries — `f1_fill_ab`, `f3_bear_puts`,
`f8_csp_entry_financing`, **`f11_dip_reject_puts`** — against the three an earlier reading of
`HANDOFF_optionsbot.md` §74 implied. **18 declared streams minus those four is exactly 14**, and
`f11` is **armed** and therefore **not** reviewed here:

`f2_menu_gate` · `f4_eventfree_premium` · `f5_ivcheap` · `f6_collar_ledger` · `f10_clean_csp` ·
`f12_postevent_reversal` · `f13_second_event` · `f14_fda_nohump` · `f15_insider_cluster` ·
`f17_vrp_percentile_sells` · `f18_boring_book` · `f19_density_gate` · `f20_married_put_storm` ·
`testbook`

**THE STATE ON DISK, MEASURED** (`data_export/`, last synced **2026-10-03** — the live service has
moved since, and the final section corrects three claims against it): 18 record streams, **158 rows
— 109 `selfcheck`, 79 `fill`, 6 `close`.** **Sixteen of the eighteen contain nothing but
self-checks**, exactly 6 rows each. Only `f3_bear_puts` (72 fills) and `testbook` (7) ever recorded
one, and **not one of the 14 books below has ever recorded a fill** — which the live body of
2026-10-12 still confirms, every one of them at `state: ARMED_NO_ENTRY_RULE`.

---

## THE ONE MEASUREMENT THAT DECIDES THREE OF THEM, AND IT IS THE PAYOFF OF A REGISTER THAT "FAILED"

**`SELL-PREMIUM` (`9b6986c`) measured a fixed-0.90-moneyness short put at 8.900816 years of premium
against a 6.0-year crash bar, and the mechanism is the income**: that strike collects **0.7778% of
strike at a median 44 DTE = 4.4545%/yr** at `turns_per_year` 5.7273.

> **THREE OF THE FLEET'S FOUR UNARMED PREMIUM-SELLING BOOKS — F-4, F-10 AND F-17 — ARE ALL FIXED
> 0.90-MONEYNESS SHORT PUTS, AND NOT ONE OF THEIR DECLARATIONS EVER APPLIED A CRASH STRESS.**

And **every one of them fires the bar**, by arithmetic on their own declared tenors at the implied
vol backed out of `SELL-PREMIUM`'s own measured income (**IV 0.2864**), with annual income =
premium × `252/DTE`:

| book | DTE | turns/yr | prem / strike | income / yr | synthetic-row loss | **years of premium** |
|---|---|---|---|---|---|---|
| `SELL-PREMIUM` as run | 44 | 5.73 | 0.7780% | 4.456% | 39.61% | **8.90** |
| **`f4_eventfree_premium`** | 30 | 8.40 | 0.4081% | 3.428% | 39.61% | **11.57** |
| **`f17_vrp_percentile_sells`** | 30 | 8.40 | 0.4081% | 3.428% | 39.61% | **11.57** |
| **`f10_clean_csp`** | 52 | 4.85 | 0.9952% | 4.823% | 39.61% | **8.22** |

**THE INSTRUMENT CHECK FIRST (`MB15`): at 44 DTE this calibration returns 0.7780% of strike against
the register's MEASURED 0.7778%** — four significant figures, on a number it was fitted to at one
point and is being read away from here.

**A CORRECTION TO MY OWN FIRST CUT OF THIS TABLE, AND IT REVERSED THE ORDERING.** I first scaled
the premium by `sqrt(DTE/44)` and reported ~7.8 years for the 30-DTE books and ~10.7 for F-10 —
**the ranking backwards.** The error is that `sqrt(T)` scaling holds near the money and **fails for
a far-OTM put at low vol**, where the probability of a 10% move grows far faster than `sqrt(T)`. So
**annual income RISES with tenor here** (3.43%/yr at 30 DTE against 4.82% at 52), inverting the
usual premium-decay intuition, and **F-10's longer tenor makes it the BEST of the three rather than
the worst.**

**THE VERDICT IS UNCHANGED BECAUSE ALL THREE STILL FIRE**: 11.57, 11.57 and 8.22 against 6.0, the
closest still **37% over**. **An estimate, not a measurement** — each book's own net income must be
measured before any re-declaration — **and it runs in the books' FAVOUR**, because F-4, F-10 and
F-17 are **not dip-conditioned**, so their implied vol is *lower* than the post-drop vol
`SELL-PREMIUM` measured, which means *less* premium and *more* years than the table shows.

**THE FIX IS MEASURED AND IT IS ONE FIELD.** At the same calibrated IV, a **25-delta** strike
(moneyness ≈ 0.925) collects **7.315%/yr** and reads **5.64 years** — because moving the strike
toward the money raises income **convexly** (+64% for +0.025 of moneyness) and raises the crash
loss only **linearly** (+1.63pp). Full table in `PREREG_DRAFT_sellpremium2.md` §2.

---

## THE TABLE

| book | verdict | the result that decides it |
|---|---|---|
| **F-4** `eventfree_premium` | **RE-DECLARE at ~25 delta, or RETIRE** | `SELL-PREMIUM` `K3`: its 0.90-moneyness strike fires a 6.0-year crash bar at **11.57 years** on its own tenor, and its declaration never applied one |
| **F-10** `clean_csp` | **RE-DECLARE at ~25 delta, or RETIRE** | same at **8.22 years** — the best of the three and still 37% over the bar |
| **F-17** `vrp_percentile_sells` | **RETIRE** | `SELL-PREMIUM` `K2` measured **its own conditioning variable** and the gradient runs **backwards**; plus the `K3` problem above. **Two independent reasons** |
| **F-5** `ivcheap` | **RETIRE** | the same `K2` measurement, read for a **buyer** — it buys in the band where the seller earns most |
| **F-12** `postevent_reversal` | **RETIRE** | `U7`: the live composite is useless as an options signal, and f12's **direction rule is the composite's sign** |
| **F-13** `second_event` | **RETIRE** | same `U7` citation — and its 0.88-year horizon is the fleet's shortest, which makes naming the real defect matter more |
| **F-15** `insider_cluster` | **KEEP THE SIGNAL, DROP THE CALL** | `MB20` leaves the opportunistic-insider axis **open**; `DIP-CALL-3`'s arithmetic forecloses the 60-DTE ATM **call** |
| **F-14** `fda_nohump` | **KEEP — cheapest unarmed book, lowest priority** | `O7` is hostile but is a **different event class**; 93 fills / 2.87 years is the fleet's shortest real horizon |
| **F-18** `boring_book` | **RETIRE** | `E-3`: its dullness input is a **repackaging** of the incumbents; and 1,202 fills / **20.0 years** |
| **F-6** `collar_ledger` | **RETIRE** | **`R1-VAR`, Don's own standing ruling** — risk bought with return, and the Sharpe is not bad |
| **F-20** `married_put_storm` | **RETIRE** | `R1-VAR` again, **plus** `DIP-CALL-3`'s power kill on its storm flag |
| **F-2** `menu_gate` | **MERGE — it is a FIELD, not a book** | its own H1 says *"fleet-wide convention, not a book"*; 4,563 fills / **47.5 years** |
| **F-19** `density_gate` | **MERGE — it is a FIELD, not a book** | same; *"a LABELING GATE, refuses nothing"*; 1,015 fills / 21.2 years |
| **`testbook`** | **RETIRE** | its own declaration: *"THROWAWAY TEST-BOOK, not a research book"* |

---

## THE REASONING, BOOK BY BOOK, WHERE IT IS NOT OBVIOUS

### F-17 and F-5 die on ONE measurement read in two directions

`A3`'s `iv_rank` **is** the own-history IV percentile — *"the fraction of the name's own trailing
252 ATM-IV observations that sit below today's"* — which is **exactly F-17's entry variable and
exactly F-5's, inverted.** `SELL-PREMIUM`'s `K2` re-priced `A3`'s own **881** era trades as **naked
puts held to expiry at the mid** (coverage **1.0000**, zero skipped) and measured, by `A3`'s own
bands:

| IV-rank band | n | mean % of strike | median % of strike |
|---|---|---|---|
| 0.50–0.65 | 313 | **+0.5700** | 0.9018 |
| 0.65–0.80 | 260 | **+0.4904** | 0.9196 |
| 0.80–1.01 | 308 | **+0.4229** | 1.0409 |

**THE SELLER EARNS MOST IN THE LOWEST BAND AND LEAST IN THE HIGHEST.** F-17 enters at percentile
**≥ 90**, i.e. the worst band for a seller. F-5 buys the **lowest** percentile, i.e. the band where
the seller earns most and therefore the buyer loses most. **One table, two books, both pointed the
wrong way.**

**THE HONEST OTHER HALF, WHICH SHIPS WITH IT: the MEDIANS rise with IV rank while the MEANS fall,
and the sd widens from 1.758 to 2.858.** That is the short-vol signature. **F-17's own `min_effect`
is a per-trade MEAN of 0.75pp, so it is judged on the falling statistic** — but a successor that
declared a median bar in advance would not be refuted by this table, and that is not a successor
anyone has proposed. **And the whole gradient is −0.1471pp, 21.8× flatter than `A3`'s banked spread
gradient of −3.21pp**, so the correct statement is that **the percentile carries almost nothing in
either direction**, not that it is strongly adverse.

### F-12 and F-13 die on their direction rule, not their event

Both read *"the live composite's sign"* to choose call or put. **`U7` measured the composite as an
options signal and it carries no information**: expectancy by composite decile is **U-shaped, not
monotone** — the bottom decile, the one a veto exists to remove, is the **third most profitable at
+10.64%** — the bottom-decile veto lift is **−0.57pp [−1.49, +0.32]**, and real-minus-control is
**−0.08pp [−1.02, +0.82]** on five-seed random entry. The mechanism is measured: inside the
megacap options universe the composite is **mostly a size sort** (median market cap rising
monotonically $62.7B → $133.5B across deciles). **`U7`'s own conclusion was that the easier bar
failed with a mechanism, and that `U1` should not be run as written.** F-12 and F-13 are `U1` as
written, inside a fleet book.

**F-13's horizon is the fleet's shortest at 0.88 years**, so it is the most tempting book on the
board to arm. **That is why naming the defect matters: arming it would buy a fast verdict on a
direction rule already measured to carry nothing.**

### F-15 keeps its signal and loses its expression

**The signal is open.** `MB20` re-ranked the insider theme wholesale — the routine filter moves the
score on **54.83%** of scored cells — and the composite did not care, **but its own closing
sentence is that this "is not a finding that the classification is worthless"**, and the
opportunistic/clustering axis (Cohen-Malloy-Pomorski) is **not closed**: `MB20` measured a routine
share of **37.95%** of scoreable insider rows and left the rule sweep as **a void condition, not a
verdict**.

**The expression is foreclosed.** F-15 buys a **1.00-moneyness call at 60 DTE**. `DIP-CALL-3`
established the general arithmetic: an ATM call's implied move is `sigma·sqrt(h/252)`, which at IV
0.30 and 60 sessions is **±14.6%**, and no insider-cluster drift anywhere in this record approaches
a tenth of that. **So F-15's hypothesis should be tested in SHARES**, which takes it out of the
fleet entirely — or, if it is to stay an options book, **the implied-move hurdle must be computed
first and it is free.** Either way the declaration as written should not be armed.

### F-14 survives, and the reason is that O7 is about a different event

`O7` measured earnings options **RICH** on this universe — implied move **5.4512%** against
realised **4.7773%**, a difference of **−0.6739pp with a CI95 of [−0.8475, −0.5070] excluding
zero**, realised exceeding implied on only **35.07%** of 6,013 events — and its straddle backtest
at **−10.340% net of four crossings**, negative in both halves with both CIs excluding zero.

**That is hostile and it does not close F-14, for two stated reasons.** (a) **It is a different
event class**: `O7` is earnings on a 186-name megacap book; F-14 is **PDUFA/FDA decision dates**.
(b) **F-14's entire selection is the cases where the option is NOT priced for the event** — it
enters only when event-month ATM IV is **≤ 1.10×** the adjacent month, i.e. **no hump** — which is
the one condition under which `O7`'s "rich" finding should not apply. **`O7` belongs on F-14's face
as its hostile prior and not as its verdict.**

**And it is the cheapest book on the board: `fills_needed` 93, the fleet's lowest, at 2.87 years.**
Keep, lowest priority, and **only after F-21/F-22** — because a long straddle paying four crossings
is the structure `O7` measured as dominated by its own costs.

### F-6 and F-20 die on Don's own ruling, and the 2026-10-12 ruling does not rescue them

**`R1-VAR`, Don's standing ruling:** *"A SHARPE OR VOLATILITY GAIN BOUGHT WITH ALPHA IS NOT WORTH
HAVING UNLESS THE SHARPE ITSELF IS BAD."* The book runs **Sharpe 0.5866** at an IR of **~0.88/yr**
vs SPY, **so the antecedent does not fire.** A collar gives up upside to cut drawdown; a married
put pays premium to cut drawdown. **Both are exactly that trade.**

**AND THE 2026-10-12 RULING DOES NOT EXEMPT THEM, WHICH IS WORTH SPELLING OUT BECAUSE IT EXEMPTS
F-21.** That ruling says *"options trading is a separate system, shown separately and paper-traded
separately from the Index record"*, and so removes the shares comparison **for a separate system**.
**F-6 and F-20 are not separate systems — they are overlays on the Index's own holdings**, read
from `data_export/paper_track_holdings.csv`, modifying what the Index book owns. **A rule that
changes the Index's own position is judged against the Index's own position by construction**, so
`R1-VAR` still binds. F-21 sells puts on names the Index does not hold and is genuinely separate.

**F-20 carries a third, independent kill: its storm flag is a market-timing rule, and
`DIP-CALL-3` closed market timing on power** — the unit of independence is a **DATE**, and a
+6.38%/yr effect needs **66.7 years at 50% power and 104.2 at 80%** on market volatility, against
**27 years of daily data in total**, i.e. short by 2.0× to 3.9× of everything that exists.

### F-2 and F-19 are not books and should stop being counted as books

Both say so themselves — *"fleet-wide convention, not a book"*, *"A LABELING GATE, refuses nothing"*
— and both hold no positions. Their `fills_needed` figures (**4,563 / 47.5 years** and **1,015 /
21.2 years**) are the arithmetic of applying a per-trade meter to an object that has no trades.

**MERGE: the menu depth and the density percentile become RECORDED FIELDS on every other book's
fills**, which costs nothing, needs no horizon, and is what `MB1-SEL` says such an object can ever
be — *"a control can only ever BLOCK a finding, never produce one."* **Two caveats on the merge:**
`records_schema` entries must not collide with the 30 base `RECORD_COLUMNS` or the declaration
refuses; and **no declaration currently opts into any gate** — `tests/test_fleet_triage.py` asserts
exactly that — so adding a `gates` key to an existing book turns that test red and is the
options-bot lane's change to make deliberately, not a side effect.

---

## WHAT MUST BE IMPLEMENTED FOR THE TWO WORTH ARMING

**F-14 `fda_nohump` — the entry rule needs three things, and one of them does not exist yet.**
1. **The S3-I2 catalyst spine**, filtered to the PDUFA/decision class, with a date **inside 90
   days**. *The declaration names `S3-I2`; whether that spine is built and populated is **not
   established here** and is the first thing to check — a catalyst list that is empty would make
   this book starve silently rather than refuse.*
2. **The hump check at entry**: event-month ATM IV against the **adjacent later** month, enter only
   if the ratio is **≤ 1.10**. Both legs read the **RAW** chain layer, never `options_derived` —
   `SELL-PREMIUM` recorded that the derived layer is two-sided on **1.0000** of its rows **by
   construction**, so a quote check measured there reads 1.000 having checked nothing (`MB21`'s
   `C1`).
3. **The straddle leg selection**: nearest-ATM call and put at the **same** strike where both are
   listed, else the strangle minimising `|call strike − put strike|`, each requiring a **two-sided
   quote** on the as-traded spot.

**F-15 `insider_cluster` — the entry rule is implementable today and should not be implemented as
declared.**
1. **The cluster detector**: `>= 3` distinct `ownername` values on one ticker filing open-market
   purchases (`transactioncode` **P**) inside any rolling 5-session window, **on the `filingdate`
   clock and never `transactiondate`** — the declaration is already right about this and `B26`'s
   same-day-filing fix is what makes it safe.
2. **`MB20`'s own correction must be carried**: `ownername` is missing on **0 of 5,636,964** rows,
   so the cluster rule is computable on every row the score can value — **but `transactioncode` is
   absent on 27.40% of rows**, and a blank code can be classified neither way. **Those rows must be
   counted and skipped, never read as "not a purchase."**
3. **And then the expression must change.** Per the section above, the free pre-outcome step is the
   **implied-move hurdle**, not the entry rule: compute what a 60-DTE ATM call already prices and
   compare it to any insider-cluster drift the record carries. **If the drift is a small fraction
   of the implied move — as it was for `DIP-CALL` at 5.6–9.3% — the book is foreclosed before a
   line of entry code is written.**

---

## THE THING THAT BLOCKS ALL OF THIS — CORRECTED AGAINST THE LIVE SERVICE, AND IT IS NOT WHAT I FIRST WROTE

**THREE CLAIMS IN MY OWN FIRST CUT OF THIS SECTION WERE STALE, AND THE CORRECTION MATTERS BECAUSE IT
MOVES THE BLOCKER.** They rested on `data_export/`, last synced **2026-10-03**, and on
`scripts/fleet_diagnose.py`'s diagnosis of that state. The **`FLEET SELF-CHECK (re-certify)`
Action succeeded at 2026-10-12 22:54Z** — run `38319241292`, 36 minutes before this file was first
committed — and its response body settles all three.

| what I wrote | what the live body says |
|---|---|
| *"ALL 18 BOOKS ARE CURRENTLY BLOCKED AT `SELFCHECK_STALE` … `armed: 0, blocked: 18`"* | **`armed: 18, blocked: 0, breathing: true, not_breathing_reason: ""`** — and **17 real books `certified`** |
| *"F-3's 72 orders … all 72 rows still read `working`"* | **the `reconcile` fix has LANDED**: `reconciled: {f3_bear_puts: {candidates 75, wrote 37}, testbook: {wrote 1}}, wrote: 38` |
| *"a prerequisite for F-21 being worth anything"* | that prerequisite is **met**; F-3 also wrote **3 new fills** this cycle, `records: 79` |

**AND THE LIVE BODY INDEPENDENTLY CONFIRMS THIS REVIEW'S SET.** Its own
`books_with_no_entry_rule` is a list of **exactly the 14** derived at the top of this file, and
`entry_rules_registered` is **`[f11_dip_reject_puts, f1_fill_ab, f3_bear_puts,
f8_csp_entry_financing]`** — so the four-armed correction is the service's own and not just
`fleet_books.RULES`'s.

### THE REAL BLOCKER IS THE OPPOSITE OF ARMING, AND IT IS A NEW FINDING

> **THREE OF THE FOUR ARMED BOOKS ARE `RULE_ARMED_NEVER_FIRES`.** `f1_fill_ab` has **30
> observations and zero fills**; `f8_csp_entry_financing` **26 and zero**; `f11_dip_reject_puts`
> **26 and zero**. Only `f3_bear_puts` fires. The harness's own message is the right one: *"A rule
> that cannot qualify anybody is indistinguishable in the records from a quiet market, and this is
> the difference. Check the rule before reading the emptiness as a finding."*

**SO "WORTH ARMING" IS THE WRONG QUESTION TO END ON.** Arming is not the binding constraint —
**qualifying is**, and the base rate is 1 in 4. Every "KEEP" above should be read as *worth arming
and then watched for `RULE_ARMED_NEVER_FIRES`*, which is a cheaper failure than a wrong verdict and
is reported loudly by the harness rather than looking like a quiet market.

### AND IT LANDS DIRECTLY ON F-21, WHICH IS THE MOST USEFUL THING IN THIS SECTION

**F-21 enters on the dip detector's HEALTHY list, and its sibling source is the one the live cycle
reports as not consulted.** The body's `history` block gives `dip_rejects`: **`n_days: 6`, of which
`n_days_invalid: 2`, `n_days_valid: 4`**, against `alert_count` and `iv60_atm` at **24 days each**.
`history_not_consulted: ["dip_rejects"]`, with the harness refusing to fabricate a row rather than
writing a zero:

> *"SOURCE NOT CONSULTED, SO NO ROW WAS WRITTEN: dip_rejects. This is a GAP, deliberately, and a
> gap is recoverable. The alternative — a row saying zero when nothing ran — is a positive
> assertion of ABSENCE that a first-appearance study cannot tell from a real one."*

**That is the correct behaviour and it is also a warning about F-21's own feasibility: the one
armed book reading the dip family (`f11`) has 26 observations and zero fills, and the dip source is
not consulted on every cycle.** F-21's declared **2.0 fills/month is a prior, and this is the
measurement that most threatens it.** **The first thing to do before arming F-21 is not to write
its entry rule — it is to confirm the healthy-dip list is consulted on every cycle and actually
supplies names**, because a book that cannot qualify anybody accrues nothing for thirty-nine years
and looks exactly like a quiet market while doing it.

---

## WHAT THIS REVIEW DOES NOT SAY

It does **not** retire any hypothesis — only expressions and declarations. F-17's percentile, F-5's
cheap-vol, F-12/F-13's post-event windows and F-6/F-20's protection are each **testable
constructions that this fleet's version of them is measured against**, and a successor with a
different construction, its own blind register and its own trials is not foreclosed by anything
here. It does **not** edit a single declaration — the files are the options-bot lane's and
acceptance is theirs. It books **no trial**: the harness charges at the first verdict read and this
file reads nothing. And it makes **no claim that arming the two survivors will produce a pass** —
`O11` binds every one of them, and the fleet's own record is **79 fills, zero recorded outcomes.**
