# AUDITOR — FIFTH REVIEW OF THE §8 LIVE PATH — 2026-10-17 (after item 69)

**NOT YET.**

One blocker, and it is a new one:

> **An event is recorded COMPLETE while this slot's own orders are still resting unfilled at the
> broker.** The planner subtracts the resting quantity (item 67, correctly), the plan comes back
> empty, and the close branch reads an empty plan as *"this event's targets are already met"*.
> When the `day` limit order then expires unfilled, nothing retries: the event is closed, the
> slot's record is wrong, and no alert was ever raised. On a **sell-out at 0%** this is the
> mechanism Don would be relying on to get out.

Item 69's blocker — my fourth — is **CLOSED**, and closed more thoroughly than I asked for.
Everything else I checked today holds. The five-cron `live-cycle.yml` and the replacement
`fleet-cycle.yml` are safe to install in one run, with one instruction about where the installer
reads from.

Gate: item 69 is on `origin/main` at `74b68fe` (merged into this branch). Reviewed read-only. No
network call to Alpaca, no credential read, no source file changed.

---

## The blocker: a resting order closes the event

### What I ran

End to end through `run_cycle`, with the real `AlpacaPaperBroker` over a recorded HTTP session —
`_request`, `orders_result`, `positions_result`, `quotes` and `place_equity` are the shipped
methods, not stubs. That discipline is here because of my own error on 2026-10-16: I marked
question 7 closed on the strength of a stub that *raised*, and item 65 found that neither real
client ever raises.

**Case A — an exit.** The book drops MSFT; the slot holds 5 shares; cycle 1 sent the sell; the
`day` order is still working when cycle 2 runs 30 minutes later.

```
exits_planned            : ['MSFT']
reconcile.open_remainder : True
reconcile.resting        : [{'ticker': 'MSFT', 'side': 'sell', 'qty_open': 5.0}]
plan_outcome             : targets_met
orders                   : []        skipped: []
PLACED                   : []
alerts                   : []
EVENT CLOSED?            : True      processed: ['rebalance:2026-11-01']
reason                   : "this event's targets are already met, so there is nothing to send
                            and the event is closed"
holdings still           : {'AAPL': 10.0, 'MSFT': 5.0}
```

The order then expires unfilled. Next cycle:

```
event  : none
reason : "no rebalance since 2026-11-01 and no percentage change, so the slot does nothing --
          which is the whole point"
STILL HOLDS MSFT? 5.0
```

**Case B — a buy, which is what the first live event is.** AAPL filled, BBB's buy still resting:
`plan_outcome: targets_met`, event closed, no alert. BBB's order expires; the slot holds nothing
of BBB against a target of 500 and never buys it. Same with a **partial** fill: 3 of 5 filled, 2
resting, `targets_met`, closed, and the 2 are never completed.

**Case C — the sell-out, and this is the one that decides the severity.** Don sets the slot to
0%:

```
cycle 1   event: pct_change  pct:100.0->0.0   PLACED: [AAPL sell 5, BBB sell 5]
cycle 2   plan_outcome: targets_met   alerts: []   open_event: None   last_pct: 0.0
          reason: "this event's targets are already met ... the event is closed"
cycle 3   event: none    PLACED: []    STILL HOLDS: {'AAPL': 5.0, 'BBB': 5.0}  at 0%
```

`last_pct` is now 0.0, so `event_for` sees no percentage change again. The sell-out cannot
re-fire without Don moving the percentage up and back down. **The slot stays fully invested at a
declared 0%, silently.**

Case C used the real `client_order_id` generator for the resting orders, not hand-written ids, so
the fixture is the shape the sender actually produces.

### Why it happens

Three facts, two of them correct on their own:

1. **Item 67** subtracts this slot's own same-side resting quantity so a remainder does not
   stack. That fix is right and I verified it again today.
2. **Item 69** taught the close branch to tell *"nothing to do"* from *"I could not work out what
   to do"*, via `PLAN_TARGETS_MET` / `PLAN_BLOCKED` / `PLAN_WORK`. Also right.
3. `PLAN_TARGETS_MET` is defined as **no orders and nothing skipped**. After (1), an empty plan
   no longer means the holdings match the targets — it can also mean *"the gap is already
   covered by an order that has not filled."*

So item 67 changed what an empty plan means, and the close branch's claim about itself was not
revisited. Its own comment, still in the tree, says:

> *"Recorded here rather than after sending, because 'met' is a property of the reconciled
> holdings and not of whether this particular cycle transmitted anything."*

That sentence is false as of item 67. In case B the reconciled holdings are `BBB: 0` against a
target of 500 and the branch reports the targets as met. **This is the sixth time on this path
that a docstring asserted the property the code had lost**, which is why the original brief told
me to read the code and not the docstrings.

`reconcile` already computes the missing fact. `out["open_remainder"] = open_left` is set on
every cycle and **read nowhere in the module** — I grepped it. The resting list even carries the
event in each `coid` (`valquo-<slot>-<event>-<ticker>-a<n>`), so *"does this slot have an order
still working for THIS event"* is answerable from data already in hand.

### Why I am blocking on it rather than noting it

- **It is the normal path, not an edge case.** Five crons exist precisely so that two or three
  in-session cycles per day are, in the pending file's own words, *"the DESIGNED behaviour"*.
  Cycle 1 sends; cycle 2 closes the event. Any name that has not filled by the second cycle is
  abandoned for the quarter.
- **The rate is measured, by this project, on this book.** `DECISIONS.md` 2026-10-16: *"the
  paper slot placed and filled real paper orders (81 of 85 names held after five cycles)."* Four
  names of 85 did not fill. Under today's code the event closes at cycle 2 and those four are
  never retried.
- **It is silent in all three of §8's clauses.** No trade, no alert, no retry — and unlike my
  fourth blocker the log does not merely look healthy, it states the opposite of the truth:
  *"targets are already met."*
- **It defeats the exit.** Case C is the one action Don would take in a hurry, and it is the one
  the defect leaves half-done with `last_pct` already written to 0.
- **It re-opens what items 67 and 69 were built to close.** Item 67's own commit records that *"a
  name leaving the book had never been sold"* as a defect. A sell that rests and expires while
  the event closes produces exactly that outcome again, by a different route.

### It is a small fix, and the escalation machinery already exists

The event must not close while this slot has an order resting for it. The natural form —
`PLAN_TARGETS_MET` requires `not plan["orders"] and not plan["skipped"] and not rec["resting"]`
for this event, or equivalently a fourth declared outcome — cannot reintroduce stacking, because
the subtraction still applies and the next cycle plans nothing while the order works.

I checked that leaving the event open does not brick the slot. The no-progress ceiling
(`MAX_EVENT_TRADING_DAYS = 5`, keyed on a fingerprint of the holdings) resets whenever the
holdings change and raises `event_attempts_exhausted` otherwise. So: the order fills → the
fingerprint moves → the counter resets and the event closes legitimately; the order never fills →
the next cycle sees no resting order and re-prices; it keeps failing → Don is alerted after five
trading days. That is §8's "doesn't trade, alerts, tries again" exactly. **Today the closing
cycle returns before reaching that code** (the close is at `live_cycle.py:1171`, the ceiling at
`:1268`), so the fix routes the case through machinery that is already written and tested.

---

## A second instance of the same family, latent

The `PLAN_BLOCKED` branch alerts and says, in its own text, *"The event stays OPEN and the next
cycle tries again."* It then writes:

```python
st["last_event_date"] = (book or {}).get("formed_on")
st["last_pct"] = pct
```

`last_event_date` is the field `event_for` keys on. It does **not** set `open_event` and does not
append to `processed`. So the next cycle finds `formed == last_event_date` (no event) and
`open_event` empty (no remainder), and returns early. Reproduced:

```
cycle 1  plan_outcome: blocked   alerts: ['plan_incomplete']
         STATE AFTER: last_event_date='2026-11-01'  open_event=None  processed=[]
cycle 2  event: none
         reason: "no rebalance since 2026-11-01 and no percentage change, so the slot does
                  nothing -- which is the whole point"
         holdings: {'AAPL': 5.0}   <- target was 1000 (10 shares)
```

One alert, then silence, and the rebalance is abandoned at half the target. The branch's comment
says the write exists *"so a persistent block escalates through the ceiling"* — but the ceiling
is 100 lines further down and this branch returns before it, and the thing the ceiling counts is
`event_attempt_days`, not `last_event_date`.

**I am recording this as latent rather than as a second blocker, and the reason is in item 67's
own code.** `PLAN_BLOCKED` is now reachable by exactly one route: a resting order whose open
quantity the broker did not report. (An unpriced name can no longer get there — item 69 made
`preflight`'s population a superset of the planner's targets, so preflight refuses first. I
checked that containment rather than taking it on trust: `tradable_names` = book held ∪ slot
holdings>0, and the planner's targets = book held ∪ exits ⊆ slot holdings>0.) The code says
Alpaca sends `qty` on every order and I have no reason to doubt it. My fixture reaches the state
through a leftover order from the **previous** event, because `reconcile`'s resting list is
filtered by slot prefix and not by event — which is correct for the subtraction and makes this
branch reachable on a cycle where `open_event` is legitimately empty.

Both instances are one sentence apart in the same `if`, so I would fix them together.

---

## Item 69 — my fourth blocker is closed

I re-ran my own reproduction. Before (recorded in review 4) and after:

| | 10-17 review 4 | **today** |
|---|---|---|
| `exits_planned` | `['MSFT']` | `['MSFT']` |
| alerts | `[]` | `preflight_failed`, naming MSFT as an **exit** |
| event closed | **yes**, `processed: ['rebalance:2026-11-01']` | **no**, `processed: []` |
| `marks_coverage` | `1 of 1 priced, missing: []` | `2 needed, 1 priced, missing: ['MSFT'], missing_exits: ['MSFT']` |
| reason | *"targets are already met"* | *"no usable price … 1 of them the slot must SELL because the book no longer holds it"* |
| retries? | no | **yes** — next cycle with a two-sided quote planned and placed `MSFT sell 5` |

Four for four, and two things better than I asked for:

- **It refuses at `preflight`, not at the alert.** I had proposed teaching the close branch to
  read `plan["skipped"]`; item 69 did that *as well*, but the unpriced exit now never reaches a
  plan at all, because the refusal's population was the real defect. That is the stronger fix.
- **The refusal names it as an exit** — *"this is an EXIT that cannot be priced rather than a buy
  that can wait"* — which is the distinction that decides whether a reader can ignore it.

**One definition instead of three.** `LS.tradable_names(book, slot_holdings)` is read by the quote
list, the refusal and the coverage report, with a test that no second definition exists. That is
the right shape: my diagnosis was *"one population widened and two not"*, and the answer is to
stop having three.

**I checked the widening cannot reach Don's own holdings**, because that is the risk a wider
population creates. With 999 TSLA held by hand in the same account and no `valquo-` order behind
it: `tradable_names` → `['AAPL']`, `priced_names.n` → 1, `slot_symbols` → `['AAPL']`,
`exits_planned` → `[]`, targets → `{'AAPL': 1000.0}`, nothing placed, and preflight passes
because TSLA is outside the slot's scope. A zero holding is also dropped, so a name the slot has
already sold out of cannot refuse the cycle for ever.

**Also correct, and worth saying because it closes a silence one branch over:** any skip is now
alerted even when other names *do* trade. A cycle that traded four names and withheld a fifth
previously said nothing about the fifth. And `exits_planned` is derived before `preflight`, so
the diagnostic survives on the refusing cycle — which is the cycle a reader most needs it on.

**Why item 69's suite could not have found today's blocker, fairly stated.** Its
`PLAN_OUTCOMES`/`PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT` enumeration is sound *within its own
vocabulary*: it proves exactly one of three outcomes closes an event, and it proves all three are
reachable. The vocabulary is one input short — the outcome space is built from `orders` and
`skipped`, and `resting` is a third input to the same question. Its control,
`test_a_CLEAN_cycle_still_closes_its_event`, uses a fixture with no resting orders, which is the
right control for the change it was making.

---

## The eight questions, as of today

| # | question | 10-15 | 10-16 | 10-17 (3rd) | 10-17 (4th) | **today** |
|---|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | pass | pass | **pass** |
| 2 | per-stock math matches the paper book | FAIL | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | pass | pass | pass | **pass** |
| 6 | a restart, retry or dispatch cannot repeat an order | FAIL | FAIL | FAIL | PASS | **pass** |
| 7 | **no check is vacuous** | FAIL | *pass (wrongly)* | pass | FAIL | **FAIL** |
| 8 | installing the workflow cannot place an order | pass | pass | pass | pass | **pass** |

**Question 6 holds for a second review.** Today's blocker runs the other way — it under-sends.
Nothing in item 69 widens what can be sent: `tradable_names` makes `preflight` refuse on *more*
names, not fewer, and I could not reach a duplicate by any route I tried.

**Question 7 fails again, on a third population.** Three instances today:

- the close decision measures the **plan** and reports a conclusion about the **holdings**, with
  its own comment claiming the property it lost;
- `reconcile.open_remainder` is computed every cycle and read nowhere;
- item 67's `test_ACROSS_A_DAY_BOUNDARY_a_resting_buy_is_still_not_re_sent` asserts that nothing
  was re-sent, and I ran its own fixture: after cycle 2 the state is `open_event=None`,
  `processed=['rebalance:2026-10-22']` — **the event is closed with both orders still resting**.
  Its assertion is satisfied by the slot having stopped acting, which is not the property it
  names. The subtraction *is* tested elsewhere in that suite, so the test is not vacuous for the
  change it was written for; it cannot see the close.

Re-checked rather than assumed, since item 69 touched shared code:

- **Q3** `assert_paper("https://api.alpaca.markets")` → `NotPaperError`;
  `assert_live_host("https://paper-api.alpaca.markets")` → `NotLiveError`; `_LiveClient` takes a
  `base` and the one construction site in `live_cycle.py` passes none.
- **Q4/Q8** `/admin/live-slots` is `GET` only; `/admin/live-cycle` is `GET|POST` and a GET
  carrying a run token returns 405. The installed workflow POSTs `?run=paper`.
- **Q5** `ALPACA_ACCOUNT_1_PCT` of `""`, `abc`, `-5`, `nan`, `1e9`, `0` and `100.5` all resolve
  to `pct=0.0, stated=False`; `LIVE_PILOT_ENABLED` unset → paused.
- **0% is still inert**, which is the premise of the whole question: `armed()` returns False at
  `pct <= 0` with *"at 0% the cycle computes and logs the orders it would place and sends none"*,
  and no live client is built unless a slot is armed.

---

## Is a single `install_workflows.bat` run safe now? — **YES, after one `git pull`.**

**Safe.** Both pending files replace an installed file **by name** —
`pending_workflows/live-cycle.yml` → `.github/workflows/live-cycle.yml`, and
`pending_workflows/fleet-cycle.yml` → `.github/workflows/fleet-cycle.yml`, which today carries
one cron at `19 22`. The old `pending_workflows/fleet-cycle-in-hours.yml`, which would have
*added* a second fleet schedule, is deleted. Afterwards: one `live-cycle` schedule (5 crons) and
one `fleet-cycle` schedule (1 cron at `0 12`). I counted the crons in every installed workflow;
there is no second fleet schedule anywhere. `data\pending_workflows\` holds no stale `.yml`
(only `installed\` and `cancelled\`), and the installer globs that directory non-recursively.

Neither can place a real order. The live workflow POSTs `?run=paper`. The fleet's broker
(`AlpacaPaperOptions`) validates its host with `assert_paper` and refuses a credential that
matches any live slot, even pointed at the paper host.

**The one instruction, and it is not hypothetical — it already happened.** The installer fetches
`origin/main` for the *destination* but copies the *sources* from the local working tree. The
`live-cycle.yml` installed at `80fe056` (today 13:20) is **byte-for-byte the item-65 version of
the pending file**, not item 67's — I compared the installed file against every historical
revision of `pending_workflows/live-cycle.yml` and it matches `e53d355` at 13,732 bytes while
item 67's is 18,779. So a local checkout that was behind main silently installed a four-hour-old
workflow on top of the newest main, and the commit message read *"Install workflow(s):
live-cycle.yml"* like any success.

What that cost is small and worth knowing: the five crons and `?run=paper` are present and
correct, so **nothing unsafe is running**. What is missing is item 67's read-only
fractional-and-settlement census step (a GET of `/admin/live-slots?check=fractional`, guarded by
`|| true`, places nothing). So that census is **not running today** despite item 67 and
`DECISIONS.md` describing it as shipped. Running the installer again — from a checkout that has
pulled — installs it and the fleet replacement together.

So: **`git pull` first, then double-click it once.** Not blocking on live keys either way.

One readability hazard while I am here, no action implied: `/admin/fleet-cycle?run=1` means
*send on paper*, and `/admin/live-cycle?run=1` means *permit live*. The same token string, two
doors, opposite stakes. Anyone moving a `curl` line between them should read the door first. Also
both files carry a `0 12` cron, so they are scheduled to fire together; with GitHub's measured
3.45–7.48h delay they will rarely actually coincide, and neither is time-critical.

---

## What I would require before a percentage above 0

**Blocking.**

1. **An event must not close while this slot has an order resting for it.** `PLAN_TARGETS_MET`
   should require an empty `rec["resting"]` for this event as well as an empty `orders` and
   `skipped` — or a fourth declared outcome, which fits the set item 69 built. `open_remainder`
   and the event key inside each `coid` already carry the fact.
2. **The `PLAN_BLOCKED` branch must stop writing `last_event_date`,** or must set `open_event`
   alongside it, so its own promise that the event stays open is true.
3. **Tests driven through `run_cycle`** for: a resting sell covering a whole exit; a resting buy
   covering a whole target; a partial fill; and the 0% sell-out. Each must assert the event is
   still open *and* that the next cycle re-sends once the order is gone. Item 67's day-boundary
   test should additionally assert `open_event` is still set, or it will keep passing through
   this.

**Not blocking.**

4. Fix the close branch's comment, or the next reader will trust it as I nearly did.
5. `reconcile.open_remainder` should either be read or removed.
6. Re-run `install_workflows.bat` after a pull so item 67's census step is actually installed.
7. Still carried from earlier reviews: `orders_window(now)` treats a caller-supplied `now` as ET
   regardless of its tzinfo (production passes `None`, so it is correct there);
   `wait_state(on_date=_stamp())` reads the wall clock; `HOLDERS` is hard-coded rather than
   derived.

---

## On the verdict

**Entering keys at 0% is itself inert, and I verified that again today** — `armed()` refuses
below 0.0001% and nothing constructs a live client for an unarmed slot. So the risk in entering
keys today is not exposure; it is that this review is the only gate, and nothing reviews the
step where Don raises the percentage. That is why I am answering the question the gate actually
asks, as in all four previous reviews, and the answer is **NOT YET**.

I want to be clear about what this is not. Item 69 is good work. It fixed my blocker at the
right level rather than at the level I proposed, replaced three copies of a fact with one,
reported two defects in its own first cut and a vacuous pass in its own fixture, and its
`PLAN_OUTCOMES` set is the first time this path has had a named state space instead of a boolean
— which is what let me ask "what else is in that space" and get an answer. Today's blocker is
not a regression from item 69; it is a consequence of item 67 that item 69's vocabulary did not
yet cover, and it has been reachable since item 67 landed.

The pattern across five reviews is now unmistakable and worth naming for whoever fixes this:
**every blocker on this path has been two distinct epistemic states sharing one value.**
`place_limit` missing (two names for one call). `[]` meaning both empty and failed (item 65).
Truncated versus failed (item 67). Three populations for one fact (item 69). And now *"nothing
left to plan"* versus *"nothing left to do"*. Each fix was correct and each exposed the next,
because the states are nested. I expect this to be the last layer — the close decision is now
one short expression away from reading the holdings, which is what it claims to read — but I
would not say so with confidence, and I said something close to that last time.

---

## What I checked

- Item 69's two source diffs (`live_slots.py`, `live_cycle.py`) line by line, against its commit
  message, and `DECISIONS.md` 2026-10-14 → 2026-10-17.
- Eight reproductions driven through `run_cycle` with the real `AlpacaPaperBroker` over a
  recorded HTTP session: the unpriced exit and its retry; a resting sell on an exit; a resting
  buy; a partial fill; the 0% sell-out (twice, the second time with real `client_order_id`s); a
  `PLAN_BLOCKED` cycle and the cycle after it; and Don's own 999 TSLA against the widened
  population.
- Item 67's own `test_ACROSS_A_DAY_BOUNDARY` fixture, driven directly to read the state it leaves.
- `order_plan`'s two bare `continue` paths; every write to `processed` and `last_event_date`;
  every read of `open_event` and `open_remainder`.
- `install_workflows.bat` in full; the installed `live-cycle.yml` against all five historical
  revisions of the pending file; cron counts in all eleven installed workflows;
  `data\pending_workflows\`; `AlpacaPaperOptions`'s host guards.
- All nine live-path suites: 71 + 78 + 10 + 22 + 70 + 60 + 65 + 85 + 26 = **487 tests, all
  green**. The blocker passes every one of them.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
