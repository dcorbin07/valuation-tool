# AUDITOR — EIGHTH REVIEW OF THE §8 LIVE PATH — 2026-10-21 (after items 72–75)

**NOT YET.**

Three blockers. Item 73's cash arithmetic is correct — Don's worked example reproduces to the
cent — and none of the three is in that arithmetic. Two are in the wind-down item 71 built, which
I passed at the seventh review; one of those destroys a real position on a configuration
omission, and I did not find it then.

> **A. An ABSENT or MISTYPED percentage variable liquidates the whole book.** `slot_pct` reads a
> missing value as `0.0, stated=False`; `armed` reads the `0.0` and never reads `stated`, so a
> slot holding its book winds down and **transmits every sell**. Reproduced three ways: the
> variable removed, the variable empty, and the variable's NAME wrong. A *malformed* value
> correctly refuses — so the code refuses the typo that fails to parse and liquidates on the typo
> that does not.
>
> **B. A percentage that returns to a value it has held before is refused as already processed.**
> After one in-and-out round trip the slot can never buy in again via the percentage, and the
> second exit leaves it holding the book while the dashboard reads 0%. Proven against a control
> that differs only in `processed` membership. No alert.
>
> **C. A price move inside an open event makes the slot trade the difference.** Item 73 froze the
> targets, which closes the equity channel; the gap is still marked to market, so a rise during a
> cash wait transmits live **sells** of names the slot is in the middle of buying. Item 73's own
> commit names this hole as the one it set out to close.

Gate: items 72 (`0ffc014`), 73 (`a06272d`), 74 (`17428fe`) and 75 (`71b0c2b`) are on
`origin/main` and merged into this branch. Reviewed read-only. No network call to Alpaca, no
credential read, no source file changed, `DECISIONS.md` untouched.

---

## Blocker A — a missing percentage sells the book

Every row below is one `run_cycle` with the real `AlpacaPaperBroker` and real `_LiveClient` over
recorded HTTP, `armed_state` derived by production. The slot has been running at 10% and holds
5 shares each of a two-name book.

| environment | `pct` | `stated` | `armed` | `sell_only` | placed on the live host |
|---|---|---|---|---|---|
| `ALPACA_ACCOUNT_1_LIVE_PCT=10` | 10.0 | True | True | False | — (`event=none`) |
| **variable absent entirely** | 0.0 | **False** | True | True | **`AAA sell 5`, `BBB sell 5`** |
| **name wrong (`_PCT`, not `_LIVE_PCT`)** | 0.0 | **False** | True | True | **`AAA sell 5`, `BBB sell 5`** |
| **variable set to `""`** | 0.0 | **False** | True | True | **`AAA sell 5`, `BBB sell 5`** |
| deliberately `0` | 0.0 | True | True | True | `AAA sell 5`, `BBB sell 5` — correct |
| malformed (`abc`) | None | True | **False** | False | — refuses, correctly |

The reason it reports is *"sent 2 order(s) for pct:10.0->0.0"*, and the alerts are
`live_order_sent` and `parity_vacuous_wind_down` — **indistinguishable from an exit Don asked
for.** There is no confirmation step and no distinct alert.

**The argument against this is already written in the code, by the person who wrote the
function.** `slot_pct`'s own docstring:

> *"A BAD VALUE IS NOT 0 AND IS NOT IGNORED. It is a broken input, so the slot refuses to act —
> treating it as 0 would SELL THE BOOK ON A TYPO."*

That was true when it was written, because 0% could not sell. Item 71 made 0%-with-holdings a
wind-down and the **absent** branch was never revisited — it is exempted from the refusal on the
stated ground that *"an ABSENT value is the shipped state and it is not a typo."* True of a slot
that has never traded; false of one that holds a book. **Tenth message on this path to assert a
property the code does not have, and the first where the property it claims is the exact harm
that now occurs.**

`stated` is the fix and it already exists: `slot_pct` returns it on every path and `armed` never
reads it. A wind-down should require `stated=True` — an instruction to hold nothing, not the
absence of an instruction.

**Reachability, stated honestly.** It needs the variable to go from readable-and-positive to
unreadable while the slot holds something: a Render environment-group edit, a deploy from a
different configuration, a renamed variable, or deleting the variable to "turn it off" instead of
setting it to 0. A wrong name entered at the *start* is harmless, because the slot never buys. I
am not claiming this is likely — I am claiming it is a single omitted environment variable
between a funded IRA and a full liquidation, with no second gate and nothing in the alert to say
it was not asked for. **And the name is easy to get wrong: I got it wrong myself in my fifth
review**, writing `ALPACA_ACCOUNT_1_PCT`, which is also the shape `DECISIONS.md` uses when it
describes the slots as `ALPACA_ACCOUNT_<n>_*`.

---

## Blocker B — the second round trip is refused

`event_key` builds a percentage event's name as `pct:<from>-><to>` and nothing distinguishes one
occurrence from another, while its own docstring says *"a genuinely new event produces a new
key."*

Driven as a chain, each event allowed to complete before the next change, as five cycles a day
would:

```
STEP 1  Don sets 5%   cycle 1  key=pct:0.0->5.0  PLACED [AAA buy 2.5, BBB buy 2.5]
                      cycle 2  remainder, event closes, record holdings {AAA 2.5, BBB 2.5}
STEP 2  Don sets 0%   cycle 1  key=pct:5.0->0.0  PLACED [AAA sell 2.5, BBB sell 2.5]
                      cycle 2  remainder, event closes, broker holds nothing
STEP 3  Don sets 5%   cycle 1  key=None          PLACED []
                      >>> "this slot has already processed pct:0.0->5.0, so it does nothing;
                           a restart never repeats an order"
                      last_pct stays 0.0, so every later cycle is refused identically
STEP 4  Don sets 0%   event=none
```

**The on-switch works once.** After one round trip the slot holds nothing, Don's setting says 5%,
and every cycle refuses with a sentence that reads like restart protection working.

**The off-switch also works once, and that is the dangerous half.** Reached via a rebalance
re-establishing the position after an exit — `pct:5.0->0.0` already in `processed`, the January
book bought back at 5%, Don sets 0% again:

```
armed=True  sell_only=True        <- it IS armed to sell
event=pct_change   key=None       planned []   PLACED []   alerts []
reason: "this slot has already processed pct:5.0->0.0, so it does nothing"
record after: holdings {AAA 2.5, BBB 2.5}   last_pct 5.0
```

**The control makes it unambiguous.** The identical state with that one key removed from
`processed`: `PLACED [AAA sell 2.5, BBB sell 2.5]`, *"sent 2 order(s) for pct:5.0->0.0"*. The
only difference between selling out and holding the book is a string in a list.

Bounded, and I want the bound on the record: the next quarterly rebalance has a different key, so
it fires, and at 0% that rebalance sells the book out. So the exposure is up to one quarter of
holding a position Don has instructed the slot to leave, with no alert, while
`/admin/live-slots` reports 0%.

---

## Blocker C — a price move inside an open event

The cleanest form is the same slot at four prices, differing only in whether the event is open:

```
event CLOSED (nothing outstanding)
   price 100 / 130 / 70 / 300   ->  event=none, PLACED [] every time
                                    "no rebalance since 2026-11-01 and no percentage change,
                                     so the slot does nothing -- which is the whole point"

event OPEN (held by a cash wait), 80% filled, frozen targets $500 a name
   price 100  ->  waiting_for_cash, $200 gap, nothing sent
   price 130  ->  PLACED [AAA sell 0.153846, BBB sell 0.153846]
   price  70  ->  waiting_for_cash, the gap grows to $440
   price 300  ->  PLACED [AAA sell 2.333333, BBB sell 2.333333]
```

So the answer to question 4 is precise: **between events, no — inside an open event, yes.** And
the realistic version is small moves, not large ones: at 95% filled and waiting on $50, a **6%**
rise on one name transmits `AAA sell 0.033` while the buy of the other is still deferred for
cash. The closer the slot is to its target, the smaller the move that triggers a sell.

Three things make this worth blocking on rather than noting:

- **Item 73's own commit identifies this hole as its subject** — *"a price move between two cycles
  of ONE rebalance changed the target and the slot traded the difference — drift trading arriving
  through the back door of a remainder cycle, which is exactly what Don's three-events rule
  forbids and which nothing was watching for."* Freezing the targets closed the equity channel.
  The gap is still `frozen_target − have_qty × CURRENT mark`, so the mark channel is open, and
  item 73's own test (double the marks, require the targets not to move) passes straight through
  it: the targets do not move and the gap does.
- **Item 73 makes the window long-lived by design.** Don's ruling blesses "waiting for cash" as a
  normal state waiting on an outside deposit. Before, an open event was exceptional; now it can
  be open for weeks, with five cycles a day inside it.
- **The top-up threshold does not gate sells.** `LIVE_MIN_TOPUP` is applied to the allocated
  buys only, so a sell goes out at anything above the $1 order minimum. And the proceeds become
  cash the next cycle spends, so it is self-funding churn: trim whatever rose, buy whatever fell.

Don's ruling 3 is honoured — it only ever sells what it bought. His three-events rule is not.

---

## What item 73 got right

- **Don's worked example reproduces to the cent.** `$800` against a `$2,002` gap: `f = 0.3996004`,
  two orders of `3.996003996` shares at `$399.60`, and the `$2` name skipped because its 40%
  share is `$0.7992` — *"it stays in the gap and catches up on a later top-up"*, which is Don's
  accepted consequence in his own words.
- **A deposit cannot buy past the frozen targets.** `$600` gap, `$100,000` cash → `$600` bought,
  `fraction 1.0`, `shortfall 0`. The frozen map is read, not re-derived (`targets_are_frozen:
  true`), and a new rebalance or a percentage change computes a fresh one.
- **A split is caught by an existing guard.** Record 2 shares, broker 4, mark halved: preflight
  refuses — *"this slot's record holds 2.000000 of AAA and the broker reports 4.000000"* — so the
  mark-and-share mismatch that would otherwise have bought the "shortfall" never reaches a plan.
- **Don's own holdings are untouched** with a cash shortfall in play: 999 TSLA held by hand is
  never quoted, planned, sold or counted, at `$0` cash and at `$100,000`.
- **A malformed threshold refuses.** `LIVE_MIN_TOPUP` of `abc`, `-5`, `nan`, `inf` → `ok=False`,
  `min_topup_invalid`, `send_outcome=withheld`, nothing placed. Absent → `$250`, `stated=False`.
  *(The same `stated`/absent distinction that blocker A needs is computed here too.)*
- **A non-cash refusal is not swallowed by the cash machinery.** `is_settlement_wait` is True for
  *insufficient buying power* and False for *not authorized to trade*, *potential wash trade*,
  *not fractionable*, *not active* and the empty string — so those reach `broker_error` rather
  than a quiet deferral. Question 3's second case is clean.
- **The ordering is right and asserted on the source:** the budget sits above the ceiling, so a
  gap waiting on a deposit does not spend a trading day before anything else happens.
- **`_cash_wait` requires `not _has_sells`**, which keeps item 67's settlement escalation alive
  for a cycle that has sells of its own to wait on. The distinction between "waiting on my own
  proceeds" and "waiting on outside money" is the right one.

---

## Non-blocking

1. **The ceiling exemption also covers a co-occurring unfilled order.** A resting order that
   never fills, alongside a cash gap, gives `waiting_for_cash` with
   `attempts_without_progress=None` — so no escalation ever fires, and the alert attributes the
   delay to cash. The resting order *is* reported in `resting_this_event`, so nothing is hidden,
   and the exemption is Don's explicit ruling. Narrow it: exempt the day only when the wait is
   purely a cash shortfall, i.e. nothing of this slot's is resting for this event.
2. **`frozen_targets` accumulates and is never pruned.** The clear-list drops only the closed
   key, so a record gains one full target map per event for ever. Harmless today (the lookup is
   by the current key) and it is also the mechanism that would make blocker B's repeated key read
   a stale freeze, were the `processed` check not refusing first.
3. **Carried and still open:** `note_no_progress` records `_stamp()` rather than the cycle's
   `now`; `HOLDERS` is hard-coded; `orders_window` treats a caller-supplied `now` as ET.

**Reported outside this lane.** `tests/test_item74.py::test_THIS_ITEM_INSTALLED_NOTHING_ITSELF`
is **red on main**, and it is red because the handover succeeded: it asserts that
`.github/workflows/*.yml` do not carry item 74's marker, and `798bca0` installed them, so the
guard fires on its own success. Installed and pending are identical for all four files I
checked, so the install was correct and the guard is wrong. This is the same shape as `da2c07e`'s
own subject from four days ago — *"the guard it tripped asserted that the handover had not
happened yet"* — reintroduced one item later.

---

## The eight questions

| # | question | ④ | ⑤ | ⑥ | ⑦ | **today** |
|---|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | pass | pass | **FAIL** ¹ |
| 2 | per-stock math matches the paper book | pass | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | *unsound* | pass | pass | **FAIL** ² |
| 6 | a restart, retry or dispatch cannot repeat an order | PASS | pass | pass | pass | **pass** ³ |
| 7 | **no check is vacuous** | FAIL | FAIL | FAIL | pass | **pass** |
| 8 | installing the workflow cannot place an order | pass | pass | pass | pass | **pass** |

¹ Blocker C: a price move inside an open event is not one of the three events, and it transmits.
² Blocker A: an absent or mistyped `ALPACA_ACCOUNT_<n>_LIVE_PCT` yields live sell orders. A
malformed one still refuses, which is why this is a new failure rather than an old one.
³ Blocker B is the opposite failure — an event refused *because* it was processed before — so
question 6 still passes as phrased. Worth noting that the mechanism protecting question 6 is the
mechanism causing blocker B.

Re-verified rather than assumed: `assert_paper(LIVE)` → `NotPaperError`,
`assert_live_host(PAPER)` → `NotLiveError`, options `assert_paper(LIVE)` → `NotPaperError`; one
`_LiveClient` site passing no `base`; `/admin/live-slots` GET-only and `/admin/live-cycle`
`GET|POST`; all four installed workflows byte-identical to their pending copies, `live-cycle.yml`
still POSTing `?run=paper` on five crons.

**All sixteen live-path suites: 715 tests, one failing — `test_item74`, above, outside the live
path.** The three blockers pass every one of the other 714.

---

## What I would require

**Blocking.**

1. **A wind-down must require a *stated* percentage.** `armed` should read `slot_pct`'s `stated`
   as well as its `pct`: an instruction to hold nothing is not the same as the absence of an
   instruction. The malformed branch already does the right thing; this is the same reasoning one
   branch over. I would also want the wind-down's alert to say which it was.
2. **An event key must distinguish one occurrence from another** — a sequence number, or
   `processed` keyed per occurrence. Until then the on- and off-switches each work once. Whatever
   the fix, `event_key`'s docstring claim that "a genuinely new event produces a new key" has to
   become true or go.
3. **A remainder cycle must not sell a name the event is buying.** The simplest form is to clamp
   each name's gap at or above zero while an event's fill phase is open, so a price move can only
   ever reduce the buy, never reverse it. Whatever the shape, I would want a test that moves the
   marks between two cycles of one event and asserts **no sell is produced** — item 73's existing
   test asserts the targets do not move, which this behaviour satisfies.

**Not blocking:** the three items above, plus the `test_item74` guard, which is somebody else's
lane but is red on main now.

---

## On the verdict

I passed this path at the seventh review, and two of today's three blockers are in code I
examined then. I should say plainly what I missed and why.

**Blocker A I could have found and did not.** I tested `LIVE_PCT` with twelve values at the
seventh review and every one of them was a *present* value. The absent case is the one I had
already got wrong once — my fifth review's question-5 line used the wrong variable name — so I
had the clue in my own hands and tested around it rather than through it. The rule I would take
from this: when a function distinguishes *absent* from *set*, test both, because the branch that
exists for the shipped state is the branch nobody revisits when the meaning of its value changes.

**Blocker B is not new either**, and it is not item 73's: `event_key` has had this shape since
item 58b. It became reachable the moment the sell-out worked, which was item 71 — so it has been
live for exactly as long as my pass has.

**Blocker C is the one item 73 introduced the exposure for** rather than the defect: the
behaviour predates it, and item 73 both named the hole and made the window in which it fires a
normal, long-lived state.

Item 73 itself is good work. The arithmetic is right to the cent against Don's own example, the
two new declared vocabularies follow the pattern that has served this path well, it reported
three defects of its own and two fixture defects the table caught, and its decision to put the
budget above the ceiling is exactly the kind of ordering question that is invisible until
something waits for weeks. The findings here are not criticisms of its sizing logic; the sizing
logic is the part I could not break.

What has changed about my confidence is the shape of where the defects now are. For seven reviews
they were in the machinery of deciding and recording. These three are in the **boundary between
Don's instructions and the machinery** — what a missing instruction means, what a repeated
instruction means, and what an instruction authorises for how long. That is a smaller surface and
a more checkable one, and I would expect a table over `(variable present/absent/malformed) ×
(holds/flat) × (event repeated/new)` to settle it the way item 71's table settled the state
machine.

Raising above 0% remains Don's decision. On this evidence I would not raise it yet, and I would
not set the percentage back to 0 by deleting the variable at any point.

---

## What I checked

- Items 72, 73, 74 and 75's commits and diffs; `DECISIONS.md` 2026-10-17 → 2026-10-21, including
  Don's six cash rulings; my seventh review.
- Ten reproductions through `run_cycle` with the real `AlpacaPaperBroker` and real `_LiveClient`
  over recorded HTTP, `armed_state` derived throughout: a deposit against frozen targets; a price
  fall; a price rise at four levels; a 2-for-1 split; a new rebalance and a percentage change
  replacing the gap; the 0→5→0→5 chain, twice, once with each event allowed to complete; the
  second exit with its control; Don's 999 TSLA under a cash shortfall; a resting order plus a cash
  gap; a malformed and a zero threshold; the four environment states against a held book; and the
  open-versus-closed price sweep.
- `allocate_buys` against Don's worked example; `min_topup` on seven values;
  `is_settlement_wait` on six refusal strings; `slot_pct` and `armed` on nine values.
- `event_key`'s construction; every write to `processed`, `open_event`, `frozen_targets` and
  `cash_wait`; the budget-versus-ceiling ordering; which side of the plan `LIVE_MIN_TOPUP` gates.
- All four installed workflows against their pending copies; the live workflow's send token.
- 715 tests across sixteen suites; the one failure identified and attributed.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
