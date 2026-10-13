# FLEET RETIREMENTS — books whose DECLARED EXPRESSION is closed

**A RETIREMENT CLOSES A DECLARATION, NEVER A HYPOTHESIS.** Every row below retires *this fleet's
version* of a trade because a **landed measurement** says it cannot pay, or because the book is
not a book. A successor with a different construction, its own blind register and its own trials
is foreclosed by nothing here. **No declaration is edited** — `declaration_commit`'s provenance
stays exactly as it was, and this file is the record that supersedes it.

**IT IS MECHANICAL, NOT DOCUMENTARY.** `fleet.retired_books()` reads this table and
`fleet_books.register_all()` **REFUSES to arm any book named in it**, so a retirement cannot be
undone by someone adding a line to `RULES` without first deleting a row here and saying why.

**ZERO TRIALS.** The harness charges at the first verdict read and nothing here reads a verdict.
Executed by the options-bot lane from `FLEET_UNARMED_REVIEW.md` (`2c7d967` + `01b234a`), whose
verdicts are adopted and whose reasoning is not restated.

| book | retired | the landed result that closed it |
|---|---|---|
| f17_vrp_percentile_sells | 2026-10-13 | `SELL-PREMIUM`'s `K2` measured **its own conditioning variable** and the seller earns MOST in the lowest IV-rank band and LEAST in the highest (+0.5700 / +0.4904 / +0.4229 % of strike). F-17 enters at percentile >= 90, the worst band for a seller, and its own `min_effect` is a per-trade MEAN, which is the falling statistic. **Plus** the `K3` problem below: two independent reasons. |
| f5_ivcheap | 2026-10-13 | The same `K2` table read for a **buyer**: it buys the band where the seller earns most and the buyer therefore loses most. One measurement, two books, both pointed the wrong way. |
| f12_postevent_reversal | 2026-10-13 | `U7` measured the live composite as an options signal and it carries no information — expectancy by decile is **U-shaped**, the bottom decile is the **third most profitable** at +10.64%, and real-minus-control is **−0.08pp [−1.02, +0.82]**. F-12's direction rule **is** the composite's sign. |
| f13_second_event | 2026-10-13 | The same `U7` citation, and naming the defect matters more here because **F-13's 0.88-year horizon is the fleet's shortest** — it is the most tempting book on the board, and arming it would buy a fast verdict on a direction rule already measured to carry nothing. |
| f18_boring_book | 2026-10-13 | `E-3` measured its dullness input as a **repackaging of the incumbents** (R² 0.347/0.413 on the seven weighted themes, where `U2` found a repackaged incumbent). 1,202 fills / **20.0 years**. |
| f6_collar_ledger | 2026-10-13 | **`R1-VAR`, Don's own standing ruling:** *"A SHARPE OR VOLATILITY GAIN BOUGHT WITH ALPHA IS NOT WORTH HAVING UNLESS THE SHARPE ITSELF IS BAD."* The book runs Sharpe **0.5866** at IR ~0.88/yr, so the antecedent does not fire, and a collar is exactly that trade. **The 2026-10-12 ruling does NOT exempt it**: that ruling frees a SEPARATE system, and a collar is an **overlay on the Index's own holdings**, so it is judged against the Index's own position by construction. |
| f20_married_put_storm | 2026-10-13 | `R1-VAR` again, same overlay reasoning — **plus** `DIP-CALL-3`'s power kill on its storm flag: the unit of independence is a DATE, and a +6.38%/yr effect needs **66.7 years at 50% power and 104.2 at 80%** against 27 years of daily data in total. |
| testbook | 2026-10-13 | Its own declaration: *"THROWAWAY TEST-BOOK, not a research book."* |
| f4_eventfree_premium | 2026-10-13 | **THE DECLARED 0.90-MONEYNESS EXPRESSION ONLY.** `SELL-PREMIUM`'s `K3` fires a 6.0-year crash bar at **11.57 years** on this book's own 30-DTE tenor, and its declaration never applied a crash stress at all. The estimate is **generous** to the book — it uses post-dip implied vol while F-4 is not dip-conditioned, so the true figure is worse. **The 25-delta re-declaration is NOT foreclosed; see below.** |
| f10_clean_csp | 2026-10-13 | **THE DECLARED 0.90-MONEYNESS EXPRESSION ONLY.** Same stress at **8.22 years** on its 52-DTE tenor — the best of the three and still **37% over** the bar. **The 25-delta re-declaration is NOT foreclosed; see below.** |

---

## WHY F-4 AND F-10 ARE RETIRED AS DECLARED RATHER THAN RE-DECLARED TODAY

The review offered *"RE-DECLARE at ~25 delta, or RETIRE"*, and **`SELL-PREMIUM-2` has since made
the 25-delta case evidentially strong**: on the same universe it clears the identical 6.0-year bar
at **4.6747 years**, because 25-delta contracts collect **9.0811%/yr of secured cash against the
0.90-moneyness rule's 4.4545%**.

**It does not transfer, and the reason is the one `MB8` names: a number may not travel across
populations.** `SELL-PREMIUM-2` measured **dip-conditioned** entries, where `V6-OPT` put post-dip
implied vol **+17.711%** above the name's own trailing median. **F-4 and F-10 are not
dip-conditioned**, so their 25-delta income is a different and smaller number, and `K3`'s
denominator is exactly that income. **Re-declaring them on `SELL-PREMIUM-2`'s figure would be
borrowing an income across populations to clear a crash gate.**

**WHAT A RE-DECLARATION NEEDS, AND IT IS CHEAP AND NAMED.** Each book's own measured net income at
25 delta on its **own** entry population. **`SELL-PREMIUM-2`'s `A2` control is already that
object** — a 25-delta put entered on **random days** in the same names, which is precisely the
non-dip population — and it measured **+0.2957%/trade** across five seeds. **It did not bank the
premium fraction**, only the return, so `K3`'s denominator cannot be read out of it today. Banking
that one column on a re-run of the existing control would settle both books **without a new
register and without a trial**, because a control can only ever BLOCK (`MB1-SEL`).

**So the hypotheses stay open and the declarations close.** That is the distinction the review
itself drew: *"It does not retire any hypothesis — only expressions and declarations."*

---

## F-2 AND F-19 ARE NOT RETIRED — THEY ARE FIELDS, AND THEY HAVE BEEN FOLDED IN

Both say so of themselves (*"fleet-wide convention, not a book"*; *"A LABELING GATE, refuses
nothing"*), both hold no positions, and their `fills_needed` figures — **4,563 / 47.5 years** and
**1,015 / 21.2 years** — are the arithmetic of applying a per-trade meter to an object that has no
trades. **`menu_depth` and `density_percentile` are now `records_schema` fields on
`DECL_f21_v6opt_dip_csp.md` and `DECL_f22_dip_csp_random_twin.md`**, which is what `MB1-SEL` says
such an object can ever be. Neither collides with the 30 base `RECORD_COLUMNS`, pinned by test.

**They keep their declarations and are NOT armed**, because a field is not a book and retiring
them would imply their content was wrong rather than mis-housed.

---

## F-14 AND F-15 — WHAT THEY NEED, AND WHETHER THE INPUTS EXIST. MEASURED TODAY.

**F-14 `fda_nohump` — THE SPINE IS BUILT AND EMPTY, SO THE BOOK WOULD STARVE SILENTLY.**
`valuation/edge/catalyst_calendar.py` (`S3-I2`) exists with `add_snapshot`, `coverage`,
`forward_rows`, `latest`, `load`, `save`, `usable_date`, and `scripts/s3i2_catalyst_scrape.py` is
its only caller. **Measured: there is NO catalyst data anywhere under `data/`** — no
`catalysts/`, no `catalyst_calendar.json`, nothing matching `*catalyst*` — **and nothing schedules
the scraper.** The module's own docstring warns against *"'no catalysts' on the day a scraper
silently breaks"*, and an empty spine is that failure in its permanent form. **So the review's
*"KEEP — cheapest unarmed book"* is right about the economics and the book cannot be armed today
for a reason the review flagged as unestablished and this measurement settles.** Its other two
needs are buildable now: the hump check (event-month ATM IV against the adjacent later month,
enter only at <= 1.10) and the straddle leg selection, **both reading the RAW chain layer** —
never `options_derived`, which `SELL-PREMIUM` measured as two-sided on **1.0000** of its rows by
construction.

**F-15 `insider_cluster` — THE SIGNAL'S INPUTS EXIST TODAY AND ARE MEASURED; THE EXPRESSION IS THE
PROBLEM.** On the shipped `data/backtest/insiders.csv` (691 MB) as of 2026-10-13:
**6,688,777 rows**, `ownername` missing on **0**, `filingdate` present on **all** of them,
**163,653** open-market purchase (`transactioncode` **P**) rows, and `transactioncode` **missing
on 28.52%** — which must be **counted and skipped, never read as "not a purchase"** (`MB20`'s own
correction; that file has grown since `MB20` measured 5,636,964 rows at 27.40%). **So the cluster
detector — `>= 3` distinct `ownername` values on one ticker filing P inside a rolling 5-session
window, on the `filingdate` clock and never `transactiondate` — is implementable today.**
**The expression is not.** F-15 buys a **1.00-moneyness call at 60 DTE**, and `DIP-CALL-3`
established the arithmetic: an ATM call's implied move is `sigma * sqrt(h/252)`, about **±14.6%**
at IV 0.30 over 60 sessions, and no insider-cluster drift in this record approaches a tenth of it.
**The free pre-outcome step is the implied-move hurdle, not the entry rule** — and if the drift is
a small fraction of the implied move, as it was for `DIP-CALL` at 5.6–9.3%, the book is foreclosed
before a line of entry code is written. **Tested in SHARES it leaves the fleet entirely.**

**THIS INVERTS THE REVIEW'S PRIORITY ORDERING, AND THAT IS THE USEFUL PART: F-14 is the cheaper
book and its input does not exist, while F-15's input exists and its expression is the thing that
is probably dead.**

---

## WHAT THIS FILE DOES NOT DO

It retires **no hypothesis** — F-17's percentile, F-5's cheap vol, F-12/F-13's post-event windows,
F-6/F-20's protection and F-4/F-10's premium selling are each testable constructions that *this
fleet's version of them* is measured against. It **edits no declaration**. It books **no trial**.
It arms **nothing**. And it makes **no claim that the surviving books will pass** — `O11` binds
every one of them, and the fleet's own record remains **79 fills and zero recorded outcomes**.
