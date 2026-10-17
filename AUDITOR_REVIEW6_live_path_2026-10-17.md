# AUDITOR — SIXTH REVIEW OF THE §8 LIVE PATH — 2026-10-17 (after item 70)

**NOT YET.**

Three blockers. My fifth is closed — all four cases verified end to end — and the search item 70
asked me to run found the next two populations, both in the branch it just rewrote.

> **A. The X→0 sell-out cannot execute on a live slot at all.** Item 70 reports this and
> attributes it to parity. Parity is the *third* gate; `armed()` refuses at `pct ≤ 0` and no live
> client is built, so **item 70's own proposed fix would not make the sell-out work** — I applied
> it and nothing transmitted. One of the three authorised events is structurally unreachable on
> the live path.
>
> **B. `PLAN_TARGETS_MET` clears `open_event` unconditionally**, so a second event with nothing
> to do discards the first event's remainder. Demonstrated leaving a slot invested at a declared
> 0% with both events recorded complete. One-line guard.
>
> **C. The close fires on an order read that was never attempted.** `?run=paper` — the installed
> schedule, five times a day — builds no live client, so `order_read` is `not_attempted` and the
> resting list is empty. Same state, same cycle: `mode=live` holds the event open, `mode=paper`
> and `mode=dry` **close it**.

Gate: item 70 is on `origin/main` at `05b6bbc` (merged into this branch). Reviewed read-only. No
network call to Alpaca, no credential read, no source file changed, `DECISIONS.md` untouched.

---

## 1. My fifth blocker — CLOSED, all four cases

Driven through `run_cycle` with the real `AlpacaPaperBroker` and the real `_LiveClient` over a
recorded HTTP session; `_request`, `orders_result`, `positions_result`, `quotes`, `place_equity`
and `place_limit` are the shipped methods.

| case | cycle with the order resting | after it expires |
|---|---|---|
| **A** resting SELL covers a whole exit | `orders_working`, nothing sent, `open_event` kept, `last_event_date` unmoved at `2026-08-01` | re-plans and **places `MSFT sell 5`** |
| **B** resting BUY covers a whole target | `orders_working`, `open_event` kept | **places `BBB buy 5`** |
| **C** partial fill, 3 of 5 | `orders_working`, holdings `BBB: 3` | **places `BBB buy 2`** — exactly the remainder |

`resting_this_event` reports `[('MSFT','sell',5.0)]` and the reason is explicit: *"this slot has
1 order(s) still working at the broker for rebalance:2026-11-01 (MSFT), so there is nothing to
send this cycle and the event is NOT recorded as complete."*

**The 0% sell-out across a `day`-order expiry, on the paper slot:**

```
cycle 1   event pct_change pct:100.0->0.0   PLACED [AAPL sell 5, BBB sell 5]   open_event set
cycle 2   orders_working   resting_this_event [AAPL sell, BBB sell]   open_event kept, last_pct 0.0
cycle 3   work             PLACED [AAPL sell 5, BBB sell 5]           <- the sell-out RESUMES
```

**`PLAN_BLOCKED` really does keep the event open.** My review-5 reproduction had it writing
`last_event_date` with `open_event` unset, so the next cycle found neither an event nor a
remainder. It now sets `open_event = key`, and the next cycle acts.

**And "stays open" can end, which is the property that makes it safe.** I drove nine cycles with
an order that never fills and never expires, overriding the day the ceiling reads:

```
11-03 days=1 … 11-06 days=4 | 11-07 days=4  11-08 days=4  (the weekend does NOT count)
11-09 days=5 | 11-10 days=6  exhausted=True  alert event_attempts_exhausted  open_event -> None
11-11 event=none
```

Six **trading** days, weekend correctly skipped, Don alerted, event closed, no stall and no
loop. `counts_a_day` being a precondition rather than an option is doing real work there.

`note_no_progress` as one definition with three callers is the right call: two of the three
branches could not reach the ceiling before, and the blocked branch's comment claimed an
escalation that was 100 lines below its own `return`.

---

## 2. Blocker A — the sell-out is unreachable on a live slot, and the proposed fix is insufficient

Item 70 found this, reported it rather than burying it, and declined to repair it on the sound
ground that parity is a §8 precondition. The finding is right. **The attribution is incomplete,
and that matters because the fix it proposes does not work.**

Its docstring states the mechanism as *"both doors are shut"* — a parity mismatch and
`parity_absent` — and proposes: *"when every target is zero there are no weights to diff, so
parity is VACUOUS rather than FAILED."* I applied exactly that, by replacing `parity` with one
that returns `{"ok": True, "measured": False}`:

```
as shipped                       armed=False  client_built=False  PLACED live: []
   reason: "...parity needs a positive value on both sides; live=0.0 paper=1000.0"

with parity VACUOUS-AND-PASSING  armed=False  client_built=False  PLACED live: []
   reason: "computed 2 order(s) and sent none: slot 1 is at 0%, so it holds nothing.
            At 0% the cycle computes and logs the orders it would place and sends none."
```

**Still nothing.** In production there are four gates at 0% and parity is the third:

1. `armed()` returns False at `pct <= 0.0` — and it is *"the only function that may say yes"*;
2. a live client is built only `if a["armed"] and live_sends`, so `client is None`;
3. parity refuses a non-positive side (the one item 70 found);
4. the send gate `out["armed"] and send and session_ok and client is not None`.

**Why item 70's suite could only see the third,** and this is the useful part:
`test_and_a_live_slot_therefore_sends_NOTHING_at_zero` calls `run_slot` directly with
`armed_state={"armed": True, "reason": "fixture"}` and a real `client`. `run_slot` takes both
from its caller — `out["armed"] = bool(armed_state.get("armed"))` — and production passes
`LS.armed(n, e)`. So **the fixture hands the slot the two things production withholds at 0%**,
which is why parity is the only obstacle it can observe. That is item 65's own lesson one level
up, in its own words: *"all 236 tests passed through it, because each supplied by hand the scope
the production path derives."* Here the hand-supplied thing is `armed_state`.

**The control that makes this a property of the code and not of my harness.** The same live slot,
same harness, same recorded session, resized rather than sold out:

```
pct 5 -> 2   armed=True   parity ok=True ("target weights match the paper book's on all")
             planned [AAPL sell 0.15, BBB sell 0.15]
             PLACED on the LIVE host: [AAPL sell 0.15, BBB sell 0.15]   alerts live_order_sent x2
pct 5 -> 0   armed=False  parity ok=False
             planned [AAPL sell 0.25, BBB sell 0.25]
             PLACED on the LIVE host: []                                 alerts parity_mismatch
```

So buy-in works, resize works, and **the sell-out is the only one of the three authorised events
that cannot transmit.** `DECISIONS.md` 2026-10-14 is explicit: *"0 to X buys in, and X to 0 sells
out"*, and `LIVE_PILOT_ENABLED=0` *"pauses every slot without selling"* — so pausing is not an
exit either. Don's documented way out of a live slot does not exist.

**And the refusal asserts the thing that is false.** `armed`'s own text reads *"slot 1 is at 0%,
so it holds nothing"* — true of a new slot, false of the only slot that needs a sell-out.
**Seventh time on this path that a message claims a property the code does not have**, and the
one a reader would most reasonably trust, because it appears in the cycle's `reason`.

The cleanest statement of the defect is the one this path keeps producing: **two states share one
value.** `pct == 0` means both *"never traded, hold nothing"* and *"still holding, must get
out"*, and `armed` cannot tell them apart. A fix needs a wind-down state — armed to **sell only**
when `pct == 0` and the slot's own record is non-empty — which is a change to the one function
that may say yes, so it wants doing deliberately and before keys go in, not after.

---

## 3. Blocker B — a second event closes the first event's remainder

`resting_for_event` holds **this** event open and ignores a leftover from another event. Both
halves are right, and item 70's reason for the filter is sound: holding this event open on
somebody else's order would stall every later rebalance. `test_a_PREVIOUS_events_order_does_NOT`
pins it.

But the close branch then runs `st["open_event"] = None` **unconditionally**, and `open_event`
may belong to a different event than the one being closed.

The route, and it is not contrived: the first buy-in is sent, nothing has filled yet, and Don
sets the slot to 0% in the same session.

```
CONTROL  percentage unchanged      outcome=orders_working  resting_this_event [AAPL buy, BBB buy]
                                   open_event stays 'rebalance:2026-11-01'

THE CASE  pct -> 0 mid-session     event pct_change pct:100.0->0.0
                                   exits_planned []        (the record holds nothing yet)
                                   resting_this_event []   (those orders are the rebalance's)
                                   open_remainder True     <- computed, reported, not read
                                   cancelled None          (the cancel loop is `for o in to_send`)
                                   outcome=targets_met
                                   open_event 'rebalance:2026-11-01' -> None
                                   processed ['rebalance:2026-11-01', 'pct:100.0->0.0']
                                   reason "this event's targets are already met …"

  -> the resting BUYS then fill:
     event none    reconciled from the broker's own fills: {'AAPL': 5.0, 'BBB': 5.0}
     the slot's own state file still says holdings {}        at a declared 0%
```

The sell-out's targets genuinely *were* met at that instant — the slot held nothing. What is
wrong is that closing it discarded the **rebalance's** remainder, and the rebalance's orders then
filled. The account ends fully invested at a declared 0%, both events recorded complete, no
alert, and the slot's own record wrong as well as its position.

It fires on a live slot too, because the close branch sits **before** the parity gate: slot 1 at
5% with its buy-in resting, taken to 0%, closes with `open_event 'rebalance:2026-11-01' -> None`
and `processed ['rebalance:2026-11-01', 'pct:5.0->0.0']` — and per blocker A that slot can then
never sell.

**The fix is one line:** clear `open_event` only when it is the event being closed
(`if st.get("open_event") == key`). With that, the next cycle resolves `key` to the open
rebalance, `resting_for_event` finds the buys, and the event stays open until they resolve — I
traced that path and it self-heals.

---

## 4. Blocker C — the close fires on a read that was never attempted

`reconcile` has four states precisely so *"I did not ask"* is distinguishable from *"nothing is
there"* (item 65). `run_slot` refuses on `truncated` and `failed`, and exempts `not_attempted`
with an explicit and correct reason:

> *"`not_attempted` is deliberately NOT here: that is a dry or paper-only cycle with no client,
> which must still compute a plan and cannot send in any case."*

Both clauses are true. Neither covers the third thing that branch does, which is **write**. Same
state — targets met in the record, one of this slot's orders still working at the broker — three
modes:

```
mode=live    outcome=orders_working  order_read=ok             open_event kept     <- correct
mode=paper   outcome=targets_met     order_read=not_attempted  open_event -> None  <- CLOSED
mode=dry     outcome=targets_met     order_read=not_attempted  open_event -> None  <- CLOSED
```

**The installed workflow POSTs `?run=paper`, five times a day.** So for every live slot, every
scheduled cycle today is a no-client cycle, and a GET of `/admin/live-cycle` is too. A cycle that
could not look closes the event that the cycle which can look holds open — and it **writes state
for a live slot** while doing it.

`open_remainder` is the other half: item 70 wired it to the payload (my non-blocking item 5) and
the branch still does not read it. In blocker B's reproduction it reports `True` on the very
cycle that closes the event. Reporting a fact is not the same as acting on it.

The three findings share one repair: **the close must require positive evidence that nothing is
working** — `order_read == "ok"`, no resting order for this event, and `open_event == key` —
rather than inferring it from an empty plan.

---

## 5. What else I looked for, and what I found nothing on

Question 2 asked for the next population before a real rebalance finds it. Beyond B and C:

- **Dust is the one remaining way `TARGETS_MET` can fire off-target, and it is bounded and
  intended.** `order_plan`'s `min_order_value` defaults to `1.0` and `run_slot` does not override
  it, so a gap under one dollar produces no order and no skip. At 5% of a $100k IRA across ~85
  names that is about 1.7% of a position. The `exiting` list documents the same for a held exit
  worth under a dollar. Not a finding; worth knowing it is the residual.
- **An opposite-side resting order** is not subtracted and is cancelled before the send, so it
  produces `PLAN_WORK` rather than a close. Correct.
- **A rebalance arriving while a pct event is open**, across a session boundary: the previous
  event's `day` orders have expired, so there is nothing resting and nothing to lose.
- **`resting_for_event`'s prefix** is derived from `client_order_id(slot, key, "")` rather than
  parsed. I checked the two cases a hand-rolled parse gets wrong — `pct:100.0->0.0` is a string
  prefix of `pct:100.0->0.05`, and `BRK-B` carries a dash — and item 70 pins both.
- **Could B or C produce a duplicate order?** No. Both close an event early, so the failure is
  always an under-send: after the close, `processed` carries the key and `last_event_date` equals
  `formed_on`, so the event cannot re-fire. Question 6 survives.

---

## 6. The installed workflows match the pending ones

Confirmed after Don's pull and reinstall (`2dc5496`, *"Install workflow(s): fleet-cycle.yml
live-cycle.yml"*):

```
live-cycle.yml    pending=18778  installed=18778  IDENTICAL=True
fleet-cycle.yml   pending=6974   installed=6974   IDENTICAL=True
```

Byte-for-byte on LF-normalised content. One `live-cycle` schedule with 5 crons and one
`fleet-cycle` with 1; no second fleet schedule anywhere; no stale `.yml` in the gitignored
handover directory. The stale-source hazard I reported last time is resolved — the installed
`live-cycle.yml` is now item 67's version, so **its read-only fractional/settlement census step
is actually installed** (`GET /admin/live-slots?check=fractional`, guarded by `|| true`).

The only send token in the file's live path is `?run=paper`; `?run=1` appears solely in the
comment explaining what to change later. Neither workflow can place a real order: the fleet's
`AlpacaPaperOptions` validates its host with `assert_paper` and refuses a credential matching any
live slot.

Also still true and still worth one sentence: `/admin/fleet-cycle?run=1` means *send on paper*
while `/admin/live-cycle?run=1` means *permit live*. Same token, two doors, opposite stakes.

---

## 7. The eight questions, as of today

| # | question | 10-15 | 10-16 | 10-17 ③ | 10-17 ④ | 10-17 ⑤ | **today** |
|---|---|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | pass | pass | pass | **pass** ¹ |
| 2 | per-stock math matches the paper book | FAIL | pass | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | pass | pass | pass | *unsound* | **pass** ² |
| 6 | a restart, retry or dispatch cannot repeat an order | FAIL | FAIL | FAIL | PASS | pass | **pass** |
| 7 | **no check is vacuous** | FAIL | *pass (wrongly)* | pass | FAIL | FAIL | **FAIL** |
| 8 | installing the workflow cannot place an order | pass | pass | pass | pass | pass | **pass** |

¹ Nothing trades outside the three events, so this passes as phrased. The inverse now fails: one
of the three cannot trade at all (blocker A).

² **An error in my own fifth review, and I am correcting it rather than restating the
conclusion.** That review's question-5 line read *"`ALPACA_ACCOUNT_1_PCT` of `""`, `abc`, `-5`,
`nan`, `1e9`, `0` and `100.5` all resolve to `pct=0.0, stated=False`"*. **The variable is
`ALPACA_ACCOUNT_<n>_LIVE_PCT`.** Every value I passed hit the "no percentage is set" branch, so
the measurement supported nothing — a vacuous check of my own, in a review whose failing question
is vacuous checks. It is also how I noticed blocker A's first gate: a control of mine came back
`pct=0.0` when I had set it to 2.

Re-measured on the real name, the conclusion holds and is stronger than I had it:

```
LIVE_PCT=''      ok=True  pct=0.0   stated=False  armed=False
LIVE_PCT='abc'   ok=False pct=None  stated=True   armed=False
LIVE_PCT='-5'    ok=False pct=None  stated=True   armed=False
LIVE_PCT='nan'   ok=False pct=None  stated=True   armed=False
LIVE_PCT='1e9'   ok=False pct=None  stated=True   armed=False
LIVE_PCT='100.5' ok=False pct=None  stated=True   armed=False
LIVE_PCT='inf'   ok=False pct=None  stated=True   armed=False
LIVE_PCT='5'     ok=True  pct=5.0   stated=True   armed=True
LIVE_PCT='100'   ok=True  pct=100.0 stated=True   armed=True
```

A malformed value returns `ok=False, pct=None` and refuses with a reason I would quote back at
anyone tempted to simplify it: *"reading it as 0 would sell the book on a typo."* That design note
is exactly right, and it is the same distinction blocker A needs and does not have.

**Question 7's three instances today** are blockers B and C plus `armed`'s false refusal text.

Re-checked rather than assumed: `assert_paper(LIVE)` → `NotPaperError`,
`assert_live_host(PAPER)` → `NotLiveError`, options `assert_paper(LIVE)` → `NotPaperError`; one
`_LiveClient` construction site and it passes no `base`; `/admin/live-slots` is GET-only and
`/admin/live-cycle` is `GET|POST` with a GET carrying a run token returning 405.

---

## 8. What I would require

**Blocking.**

1. **A live slot must be able to sell out.** `armed` needs to distinguish *"0% and flat"* from
   *"0% and still holding"*, and the message *"slot N is at 0%, so it holds nothing"* must stop
   asserting the false half. Parity's zero-target case needs the vacuous treatment item 70
   proposes **as well** — it is necessary and, demonstrably, not sufficient.
2. **Clear `open_event` only when it is the event being closed.**
3. **Close only on positive evidence that nothing is working:** `order_read == "ok"`, no resting
   order for this event, `open_event == key`. `open_remainder` should be read or dropped.
4. **Tests driven through `run_cycle` with `armed_state` derived rather than supplied**, for: a
   live slot taken X→0; a second event arriving while the first event's orders rest; and the same
   state under `mode=live`, `mode=paper` and `mode=dry` asserting the same close decision. The
   third is the one that would have caught C, because C is invisible to any single mode.

**Not blocking.**

5. `_stamp()` rather than the cycle's `now` in `note_no_progress` — item 70 names this as my own
   item 7 and works around it in its suite; it means the ceiling reads the wall clock.
6. `HOLDERS` is hard-coded rather than derived.
7. `orders_window(now)` treats a caller-supplied `now` as ET regardless of its tzinfo;
   production passes `None`, so it is correct there.

---

## 9. On the verdict

Entering keys at 0% remains inert in itself — `armed()` refuses below 0.0001% and no live client
is built for an unarmed slot — so the risk today is not exposure but that this review is the only
gate, and nothing reviews the step where Don raises the percentage, or the step where he lowers
it again. That second step is blocker A.

Item 70 is the best item in this series. It fixed my blocker with a declared fourth outcome
rather than another boolean, made the ceiling one definition after finding two branches could not
reach it, deleted the false comment instead of softening it, reported four defects in its own
first cut and a vacuous pass in its own Amendment 3 fixture, and — the thing I want to single out
— **found and reported a defect that makes its own change look worse**, the live sell-out, when
nothing compelled it to go looking. Its three test repoints onto `inspect.getsource` are a real
improvement on guards keyed to a location.

What it could not see, it could not see for one reason: its fixture asserted `armed_state` rather
than deriving it. That is the shape worth carrying forward more than any individual fix. Six
reviews in, **every blocker on this path has been two states sharing one value** — `place_limit`
as two names for one call, `[]` as both empty and failed, truncated versus failed, three
populations for one fact, nothing-to-plan versus nothing-to-do, and now *did-not-ask* versus
*nothing-working* and *0%-flat* versus *0%-holding*. The states are nested, so each correct fix
exposes the next. I said last time I expected that to be the last layer and that I would not say
so with confidence; I was right to hedge, and I will not predict it again. What I will say is
that B and C are each one line and A is one function, and that the remaining surface is now small
enough that the next review should be short.

---

## What I checked

- Item 70's `live_cycle.py` diff line by line against its commit message; `DECISIONS.md`
  2026-10-14 → 2026-10-17; my five previous reviews.
- Eleven reproductions through `run_cycle` with the real `AlpacaPaperBroker` and real
  `_LiveClient` over recorded HTTP: cases A, B and C with their retries; the 0% sell-out across a
  `day`-order expiry on paper; the same on a live slot, and with parity neutralised; a live slot
  resized 5%→2% as the arming control; nine cycles driving the no-progress ceiling through a
  weekend; a second event closing the first, on paper and on a live slot; and one state read under
  all three modes.
- `armed` / `slot_pct` on twelve environment values, on the correct variable name.
- Every write to `open_event`, `processed` and `last_event_date`; every read of `order_read` and
  `open_remainder`; `order_plan`'s two bare `continue` paths; the cancel loop's scope.
- Item 70's own fixtures for the live-slot-at-zero tests, to establish why its diagnosis stopped
  where it did.
- Installed versus pending for both workflows; cron counts across all installed workflows; the
  gitignored handover directory; `AlpacaPaperOptions`'s host guards.
- All ten live-path suites: 71 + 78 + 10 + 22 + 70 + 60 + 65 + 85 + 26 + 46 = **533 tests, all
  green.** All three blockers pass every one of them.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
