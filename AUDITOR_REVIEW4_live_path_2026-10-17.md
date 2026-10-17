# AUDITOR FOURTH REVIEW — the §8 live path after item 67

# NOT YET.

**One blocker, and it is the first one in four reviews that is not about buying something
twice.** An exit the free feed cannot price is silently dropped: the slot keeps a name the Index
no longer holds, records the rebalance as **complete**, raises **no alert**, and its own price-
coverage line reports **1 of 1 priced, missing: none**.

**My third blocker is closed, and closed well.** Item 67 reproduced it at my exact ratio before
fixing it, took the option I preferred for the reason I gave, and then found and fixed two
defects in its own first cut. I verified the fix against the real client class, not a stub.

**And the answer Don is waiting on, stated separately because it differs from the verdict:
YES — the pending five-cron `live-cycle.yml` is safe to install.** See question 6.

**Reviewer:** auditor lane · **Date:** 2026-10-17 · **Reviewing:** item 67 (`05f50d4`)
**Suites:** `test_item58` 71, `test_item58b` 78, `test_item58b_doors` 22, `test_item63` 70,
`test_item64` 60, `test_item65` 65, `test_item67` 85 — **451 of 451 green.** The blocker passes
all 451.

Fourth in a series; the three earlier reviews are left unedited as the record of what was true
then.

---

## The blocker: an unpriced exit is dropped silently and the event is closed

Reproduced end to end through `run_cycle` with the real `AlpacaPaperBroker`. The slot holds AAPL
and MSFT; the book now holds AAPL only, so MSFT must be sold; IEX returns a one-sided quote for
MSFT, which yields no mid — the documented common case, and 26 of 86 names on the first real
cycle.

```
exits_planned : ['MSFT']                                   <- it KNOWS MSFT must go
planned       : []
skipped       : [{'ticker': 'MSFT', 'reason': 'no usable mark'}]
PLACED        : []
alerts        : []                                         <- NO ALERT
event closed? : True   processed: ['rebalance:2026-11-01']  <- recorded COMPLETE
marks_coverage: {'n_needed': 1, 'n_priced': 1, 'missing': []}
reason        : "this event's targets are already met, so there is nothing to send and the
                 event is closed"
```

That last line is false: the targets are not met. MSFT sits at 50 shares against a target of
zero, and `event_for` will not fire again until the next rebalance or a percentage change — so
the slot holds a name the Index dropped for a quarter.

**The mechanism is one population widened and two not.** Item 67 correctly found that an exited
name was never quoted, and widened the quote list:

> *"This was the book's held names alone — and an EXITED name is by definition not among them, so
> no quote was requested for it, so `order_plan` skipped it for want of a mark and the exit never
> happened. … the test I wrote for them passed because it supplied the price by hand."*

That is the right fix and a good self-catch. But **three** places compute "the names this cycle
cares about" from the book's held positions, and only one was widened:

| population | what it governs | widened by item 67? |
|---|---|---|
| `tickers` in `run_cycle` | which names get a quote | **yes** |
| `need` in `preflight` | whether a missing price **refuses** | **no** |
| `need` in `marks_coverage` | what the run log **reports** | **no** |

So the exit is now *asked for* but a failure to price it neither refuses nor shows. And the
third row is what makes it silent rather than merely wrong: the workflow's own summary prints
`priced: %s of %s` from `marks_coverage`, so the daily log reads

```
priced        : 1 of 1
sent          : 0
refusal       : this event's targets are already met ...
```

**which is indistinguishable from a healthy quiet day.** The only trace is `skipped` and
`exits_planned` inside the ~35KB body that item 65 part 3 moved to an artifact precisely because
nobody parses it.

**And the event-close branch cannot tell two states apart.** `if not plan["orders"]:` closes the
event, clears `open_event`, appends to `processed` and wipes the counters — without consulting
`plan["skipped"]`. "There is nothing to do" and "I could not work out what to do" are the same
value. **That is the third time on this path that two epistemic states have been collapsed into
one** — after `[]`-means-both-empty-and-failed (item 65) and truncated-versus-failed (item 67's
own part 0) — and it is the same shape each time.

The same branch swallows the other skip reason too: an unknown resting quantity correctly
withholds its name, the plan empties, and the event closes as "targets met". Verified.

**§8's own rule is violated in two of three clauses.** The contract says a broken input means the
slot *"doesn't trade that cycle, alerts Don, and tries again next cycle."* Here it does not trade
(correct), does **not** alert, and does **not** try again — the event is closed.

**Direction, stated plainly because it bears on severity.** This cannot place a wrong order. It
fails to place a required one, leaving the slot *under*-exposed by one name's weight while
holding a stale name. That is materially less dangerous than the 5× stacking I reported last
time, and I would not have blocked on the exposure alone. **I block on the silence**: a false
"targets are already met", no alert, and a coverage line that reports perfect coverage, on a path
whose entire discipline is refuse-visibly-and-retry. The 2026-10-22 rebalance is the first book
change in this path's life, so the first exit it will ever attempt is imminent.

**The fix is small and in the module's own idiom.** Do not close the event when `plan["skipped"]`
is non-empty — alert and leave it open, which is what every other broken input already does. And
compute both `need` lists from the same set as `tickers` (book held ∪ slot-held), so an unpriced
exit refuses and shows. Then a test that drives an unpriced exit through `run_cycle` and asserts
the event stays open.

---

## The seven questions

### 1. My third blocker — **CLOSED**, verified at the exact ratio, with two self-caught defects

`order_plan` now takes `resting=` and subtracts this slot's own **same-side** open quantity;
`reconcile` records `qty_open` as `qty − filled_qty`, so a partial fill is not double-counted.
All three cases the prompt names, through `run_cycle` with the real client:

| case | result |
|---|---|
| **five cycles in one session** | one order of 100 against a 100-share target. Cycles 2–5 plan nothing |
| **resting order of unknown size** | that name is withheld — `skipped: ['AAPL']`, nothing sent |
| **opposite-side order cancelled before the send** | cancelled `rest-sell`, then bought **100**, not 106 |

The third is the one worth dwelling on, because item 67 got it wrong first and says so: netting
*both* sides double-subtracts the quantity about to be cancelled, and its own first cut *"held 6,
resting sell 6, target 6 planned a buy of 6, the cancel removed the sell, and the account ended
at 12."* A stacking fix that stacks. Only the same side is subtracted now, and I confirmed the
cancel-then-buy path does not over-size.

The second was also wrong first — it reported the unknown and planned the full remainder anyway,
*"failing OPEN in the one state the subtraction exists for."* It withholds now.

**Any other way a working order can be planned twice?** I looked at seven routes and found none:
an order from an earlier event is still committed quantity and is correctly subtracted; a name
absent from `targets_map` is not planned at all; a sell is still capped at `have_qty` so no short
is reachable; `qty − already` going negative falls under `min_order_value` and is skipped;
case-folding is applied on both sides; a failed order read refuses before planning; and an
exit's target of zero takes the sell path where a resting buy is cancelled rather than
subtracted.

**One residual the docstring declares rather than hides**, and I agree with both the analysis and
the choice: if a target *shrinks* while a buy rests, that buy still fills and overshoots — by at
most the target authorised when it was placed, with the next cycle selling it down. One
previously-authorised order, not five, and self-correcting.

### 2. Pagination — **CLOSED**

`settlement.paged_orders` walks `after=` ascending and dedupes the exclusive-cursor overlap. All
four cases:

```
(a) full, full, short            -> ok=True  truncated=False  7 orders over 3 pages
(b) full page, LAST timestamp shared by 2 -> truncated=True
      "asking for everything after it would SKIP the ones not yet read"
(c) second page HTTP 500         -> ok=False  (reconcile turns this into a refusal)
(d) full page, no timestamps     -> truncated=True
```

Plus a non-advancing cursor and a 20-page cap, both `truncated`. Every case that cannot be proved
complete refuses, and `reconcile` reads the pager's refusal — which item 67 notes it did **not**
at first: *"truncated arrived as success with a short list, which is the defect item 65 found
underneath the auditor's own fix, one item later."* Living in `settlement.py` rather than either
client is right, and the separation test caught the first placement.

### 3. Settlement waits — **CLOSED, all four parts**

**Buys sized off non-marginable buying power, never margin:**

```
nmbp 500, buying_power 2000, multiplier 2  -> 500  from non_marginable_buying_power
nmbp absent, cash 500, bp 2000, mult 2     -> 500  from min(cash, buying_power)
cash only                                   -> 500  from cash
nothing reported                            -> REFUSE, no buy sized
live-client {"ok","data"} shape             -> 750  (both shapes read)
account unreadable                          -> REFUSE
```

`min(cash, buying_power)` rather than branching on `multiplier` is the right construction — an
unreported or wrong multiplier cannot widen the budget. `regt_buying_power` and
`daytrading_buying_power` are read nowhere.

**A funds refusal becomes `awaiting_settlement` and cannot become a re-buy on top of itself.**
Tested with a budget covering half the plan, across two in-window crons a day and a day boundary:

```
10-22 14:40  sent=1 deferred=1   "1 buy(s) await settled cash"
10-22 15:00  sent=1 deferred=0
10-23 14:40  "targets are already met ... closed"
TOTAL PER NAME: AAPL 50.0, MSFT 50.0   (target 50 each) -- no name exceeded its target
```

`to_send` being a different list from `plan["orders"]` is the load-bearing part: a fully-deferred
rebalance does not record itself as finished, the event stays open, and the intent is
deliberately not overwritten because it is one of `preflight`'s three scope sources. Item 67's
first cut filtered the plan itself and closed the event — the same collapse as the blocker above,
caught there and not here.

**The ceiling counts trading days.** `MAX_EVENT_TRADING_DAYS = 5`, dated once per date. I first
tested `note_trading_day` directly with a weekend and it recorded Saturday — then checked the
call site: the session gate at line 1125 returns before the counter at line 1182, so only
in-session cycles reach it and the docstring's claim holds. **My test was unfair, not the code.**
Progress is a *change* in the holdings fingerprint rather than an increase, so a sell can satisfy
it — the old rule could not.

**The alert fires only after T+1 plus a trading day.** `SETTLEMENT_TRADING_DAYS = 1`; 1 day → no
alert, 2 days → no alert, 3 days → alert. Correct.

`is_settlement_wait` matches *"insufficient buying power"* and correctly declines *"potential
wash trade detected"*, *"not allowed to short"* and *"cost basis must be >= 1"* — a funds wait is
not every rejection.

### 4. The exit fix — **PARTLY. Two of three hold; the third is the blocker.**

| requirement | result |
|---|---|
| a name that leaves the book is sold | **yes** — `exits_planned: ['MSFT']`, sold 50 |
| only to the slot's own recorded quantity, never Don's other holdings | **yes** — with Don holding 999 TSLA the slot never bought, only MSFT was planned. `order_plan` iterates `targets_map`, so Don's holdings are unreachable by construction, and item 58's `test_a_name_the_slot_did_not_buy_is_not_in_the_plan_at_all` caught item 67's first attempt planning a sale of `DONS_OWN` |
| an unpriced exit must not fail open | **NO** — see the blocker |

Putting the exit in `run_slot` rather than `order_plan` is the right placement, for the reason
given: a name absent from the planner's targets must not be in its plan at all, and that
invariant is what makes "Don's other holdings are never touched" true by construction rather
than by a filter.

### 5. Fractional reads — **they cannot change what is sent, by refusing or otherwise**

`/v2/assets` (line 645) is inside `fractional_report`; `/v2/account/configurations` (line 704) is
inside `account_settlement_report`. Verified by AST:

- `run_slot` — the only function that transmits — calls **neither**, nor either reporter;
- neither reporter contains `place_limit`, `place_equity`, `order_plan` or `cancel(`;
- both are called from `run_cycle` as diagnostics, and both carry `constructs_an_order: False`.

So they are strictly reporting. They do not even gate — which is the safest arrangement and also
means a non-fractionable name is *not* caught pre-emptively; it is rejected by the broker and
handled as a `broker_error`, with the ceiling stopping the event after five trading days. Item 67
states that outcome and leaves the remedy to Don as a construction change, which is correct.
Reporting `NOT REPORTED` rather than guessing when Alpaca omits `fractional_trading` is the right
call.

### 6. Is the pending five-cron `live-cycle.yml` safe to install? — **YES.**

Don is holding this on my word, so plainly: **install it.**

My third review's objection was that five crons make two or three in-window cycles routine, and
that the remainder stacked on each. **That cause is gone**, and the file states the condition to
check rather than a date:

> *"`order_plan` in valuation/edge/live_slots.py subtracts this slot's own resting SAME-SIDE
> quantity, and `reconcile` records `qty_open` on each resting order."*

**I verified both independently of the commit message** — the subtraction by reproducing five
in-session cycles and getting one order, and `qty_open` by reading its derivation. The condition
is met on `origin/main`.

Three further points:

- The file now opens with **DO NOT INSTALL YET — unless the planner fix below is on
  `origin/main`**, which is the right way to ship a conditional instruction.
- It still sends `?run=paper`, so no live order is reachable from it, and the installed copy's
  single cron is safe in the meantime.
- **The blocker above is not made worse by installing it.** The exit is lost on the first cycle
  whose plan empties, whether that takes hours with five crons or days with one. Installing
  reaches it sooner; it does not create it.

The one thing I would change is cosmetic but worth doing: the paragraph justifying the extra
crons still reads *"AND AN EXTRA RUN COSTS NOTHING … the door is idempotent per event"*. That
sentence was the premise my third review refuted, and it is now true again **because of the
subtraction**, not because it was true when written. A reader who installs on the strength of
that sentence is relying on reasoning that was wrong for a day.

### 7. My eight questions, as of today

| # | question | 10-15 | 10-16 | 10-17 (3rd) | **today** |
|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | pass | **pass** |
| 2 | per-stock math matches the paper book | FAIL | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | pass | pass | **pass** |
| 6 | **a restart, retry or dispatch cannot repeat an order** | FAIL | FAIL | FAIL | **PASS** |
| 7 | **no check is vacuous** | FAIL | *pass (wrongly)* | pass | **FAIL** |
| 8 | installing the workflow cannot place an order | pass | pass | pass | **pass** |

**Question 6 passes for the first time in four reviews.** It failed on the empty record, then the
empty scope, then the un-subtracted resting order. Each fix was correct and each exposed the
next; this is the first review where I cannot produce a duplicate order by any route I can think
of.

**Question 7 fails on a new population.** `marks_coverage` reporting `1 of 1 priced, missing: []`
while a name went unpriced is a measurement taken on the wrong set — the same family as the
`place_limit` name, the `[]`-on-failure replies, and truncated-versus-failed. A check whose
population excludes the case it exists to catch is the definition of vacuous, and this one also
reports a reassuring number while doing it.

---

## What I would require

**Blocking — one item, three lines plus a test:**

1. `if not plan["orders"]` must not close the event when `plan["skipped"]` is non-empty: alert
   and leave the event open, as every other broken input does.
2. Compute `preflight`'s `need` and `marks_coverage`'s `need` from the same set as `tickers`
   (the book's held names **∪** every name a slot holds), so an unpriced exit both refuses and
   shows.
3. A test driving an unpriced exit through `run_cycle` that asserts the event stays **open** and
   an alert is raised — the existing exit tests supply a price, which is the same gap item 67
   found in its own first attempt.

**Not blocking:**

4. `orders_window(now)` uses a caller-supplied `now` **as-is** and compares it against ET clock
   times while labelling them "ET". Production passes `None` and is correct, so this is a test
   seam rather than a defect — but it silently measured a different time in my own harness (16:10
   UTC was judged as 16:10 ET), and a future test could assert a window behaviour that does not
   match production. Convert, or require tz-aware input.
5. `wait_state(on_date=_stamp())` reads the wall clock rather than the cycle's `now`, so the
   trading-day count cannot be exercised across simulated days.
6. Derive `HOLDERS` in the interface test, still outstanding from the second review and still
   latent.

---

## On the verdict

Entering keys at 0% sends nothing, and this blocker cannot place a wrong order in any case — so
I considered passing, more seriously than in the previous three reviews, because the direction of
the defect has changed. What decided it is that the first exit this path will ever attempt is the
2026-10-22 rebalance, days away; that an exit is by construction a name the Index has just
dropped, which is disproportionately the kind IEX will not quote; and that every surface Don
reads would show a healthy cycle while it happened.

Item 67 is the strongest of the four. It reproduced my blocker at my own ratio before touching
it, chose the option I preferred and cited my reason for it, found two defects in its own first
cut and reported both, and corrected §8a's open question 2 against itself in the contract rather
than quietly. Three of its four parts I can find nothing wrong with. The fourth fixed the half of
the exit problem that was visible — the name was never quoted — and left the half that only
appears when the quote fails.

---

## What I checked

- **Reproduced end to end through `run_cycle` with the real `AlpacaPaperBroker` and recorded
  HTTP** — not raising stubs, which is the lesson from my third review: five in-session cycles;
  a resting order of unknown size; an opposite-side cancel followed by a buy; a priced exit; an
  unpriced exit; an exit beside Don's own 999-share holding; a half-budget deferral across two
  crons a day and three days.
- **Exercised `settlement.paged_orders` directly** on four page shapes, and `spendable` on six
  account shapes including both clients' reply envelopes.
- **Verified by AST** that `run_slot` reaches neither fractional read, and that neither reporter
  can place or plan.
- **Checked the call site** before believing my own weekend-counter result, and found my test at
  fault rather than the code.
- **Read** item 67's diff across `live_slots.py`, `live_cycle.py`, `alpaca_broker.py`, the new
  `settlement.py`, both workflow copies, and `test_item67`'s 85 tests — commit message last, and
  against the code rather than for it.
- **Ran** all seven suites: 451 green. The blocker passes every one of them.
- **Not checked:** anything against a live or paper Alpaca account. No network call, no
  credential read. Item 67's service-side claims I take as reported; the paper slot has run one
  event, so the exit path has never fired in production and the 2026-10-22 rebalance is its first
  occasion.
