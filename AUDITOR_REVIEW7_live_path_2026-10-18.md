# AUDITOR — SEVENTH REVIEW OF THE §8 LIVE PATH — 2026-10-18 (after item 71)

**LIVE KEYS MAY BE ENTERED AT 0%.**

Blockers A, B and C are closed. I reproduced each end to end through `run_cycle` with the real
client classes and with `armed_state` derived by production rather than supplied, and I went
looking for a fourth. I found two defects and neither can move a position or send an order: a
false message with no escalation behind it, and a per-specification limit on the wind-down. Both
should be fixed; neither is a reason to withhold the gate.

This is the first time in seven reviews that I cannot construct a route by which this path loses
money, trades without authority, trades twice, or records a conclusion it has no evidence for.

Gate: item 71 is on `origin/main` at `2e7ae50` (merged into this branch). Reviewed read-only. No
network call to Alpaca, no credential read, no source file changed, `DECISIONS.md` untouched.

---

## 1. The three blockers

Every reproduction below runs through `run_cycle`. `armed_state` is computed inside it from the
environment and the slot's own record — never passed in. That distinction is the whole reason
item 70's suite could see only one of four gates, so this harness never does it either.

### Blocker A — the sell-out executes

```
pct 5 -> 0, record holds AAPL 0.25 + BBB 0.25
   armed=True  sell_only=True
   parity: ok=True measured=False        (vacuous, not passed)
   planned: [AAPL sell 0.25, BBB sell 0.25]
   PLACED on the LIVE host: [AAPL sell 0.25, BBB sell 0.25]
   SOLD: ['AAPL', 'BBB']    TSLA touched? False
```

Don's 999 TSLA, bought by hand with no `valquo-` order behind it, is in the same account and in
the broker's position list. It is not sold, not planned, and not quoted. The wind-down reads the
slot's own fill-derived record, so it can only ever sell what this path bought.

The four controls that matter, all correct:

| | |
|---|---|
| 0% and the record holds **nothing** | `armed=False`, nothing placed, and the reason no longer claims a falsehood: *"at 0% and its own record holds nothing, so there is nothing to sell and a 0% target licenses no buy"* |
| 0% holding, **`LIVE_PILOT_ENABLED=0`** | `armed=False`, nothing placed — *"every slot is PAUSED. Nothing is sold and holdings stay exactly as they are."* **The pause still wins**, which is what keeps Don's two instructions different |
| resize 5% → 2% | unchanged: arms, parity `ok=True`, places both sells |
| a **family slot** at 0% holding | `armed=False` on an unsigned contract, `armed=True, sell_only=True` on a signed row, and `armed=False` when it shares slot 1's credential |

That last row is mine rather than item 71's: the table configures slot 1 only, and slot 1 needs
no contract row, so §8's family-slot gate is never crossed with `sell_only`. It is honoured —
`holder_authorized` and `isolation` are both inside the wind-down branch, in the right order.

**The fourth gate item 71 found of its own accord is the part I would single out.** My sixth
review showed that fixing parity was insufficient and named `armed` as the first gate. Item 71
fixed both and then re-asked my question of its own fix, finding `parity_absent` — the paper slot
runs at `PAPER_PCT = 100`, so the comparison that branch waits for *cannot exist* for a
wind-down. A refusal with no condition that lifts it is the right thing to go looking for, and
nothing compelled it to look.

**A wind-down transmits no buy, enforced twice** — the plan is filtered and a buy is blocked
again at the sender, each with its own alert naming itself a planner defect. I could not make a
buy appear in a wind-down plan by any route (`targets(0, …)` is zero for every name, so no
positive delta exists), so both guards are defence in depth against a future change rather than
against anything reachable today. That is the correct place to be belt-and-braces: the thing
prevented is spending real money in an account its owner has just told to hold nothing.

### Blocker B — the overlapping-event close

The route from my sixth review: the buy-in is sent, nothing has filled, Don sets 0% in the same
session.

```
event pct_change pct:100.0->0.0      outcome=targets_met   event_closed=False
blocked_by_open_event: rebalance:2026-11-01
open_remainder: True      resting_this_event: []
PLACED: []
open_event AFTER: rebalance:2026-11-01     processed: ['rebalance:2026-11-01']
reason: "this event's plan is empty, but rebalance:2026-11-01 is still open with orders of this
         slot's working at the broker -- so the empty plan means that event's orders cover the
         gap rather than that THIS event is finished."
```

Item 71 went past the one-line guard I proposed. I asked that the close stop *discarding* the
other event's remainder; it also stops the close recording *itself* complete — `processed` does
not gain the pct key. The reasoning is right and worth keeping: *"Something else is on its way to
meeting my targets is not my targets are met."* The sequence self-heals — the resting buys fill,
and the next cycle at 0% places `AAPL sell 5, BBB sell 5`.

### Blocker C — the no-read close

Same state, four ways in, with the record's own bytes hashed before and after:

| in | `order_read` | `writes_allowed` | `event_closed` | state file |
|---|---|---|---|---|
| `POST ?run=1` | `ok` | True | False (held open) | legitimately written |
| `POST ?run=paper` | `not_attempted` | False | False | **sha and size identical** |
| `POST ?run=0` | `not_attempted` | False | False | **identical** |
| `GET` | `not_attempted` | False | False | **identical** |

`open_event` survives in all four. The two refusal reasons are distinct and each names its own
cause — the read for a paper or dry cycle, the verb for a GET. The paper slot on a GET also
writes nothing, so the gate is not live-slot-specific.

**A cycle that cannot record cannot send**, which closes the obvious corollary: in live mode with
the write withheld, the pre-send guard refuses and `PLACED` is empty, with *"an order sent without
a record of it is how a position gets bought twice."* That combination is unreachable from the
door — a GET carrying a run token returns 405, so a GET is always the dry mode — but the gate
holds on its own.

**One correction to my own method, since I reported it loosely in the middle of this work.** My
first check compared the parsed state dict and read "changed" on every row, including rows where
nothing was written. `read_state` seeds `attempts` and `fills_seen`, so a parsed comparison
against an in-memory fixture is always unequal. The byte comparison above is the right
instrument, and it is the one item 71 uses.

---

## 2. The transition table

**It is the strongest control in this series, and its own before-count is why.** A declaration
read off the implementation agrees with it everywhere, bugs included, so the table proves nothing
until it disagrees with a tree that has them. I ran `scripts/i71_table_before.py` against
`da2c07e` myself and reproduced the figures exactly:

```
rows 2240   wrong_any 1643   wrong_real 1641   artefact_only 2
  1524  WROTE the record when no write is permitted
   320  armed=False where the wind-down must arm
   320  sell_only=False
   275  event_closed=False but the record says True   (the artefact kind)
   271  CLOSED the event with no evidence that nothing is working
```

Sources restored byte-for-byte; `git status` clean afterwards. Excluding the `event_closed`
artefact from the headline rather than counting it is the right call — that field did not exist
on the old tree, and counting its absence would have inflated the number in the item's own
favour.

The pruning is stated rather than hidden: the three read axes are crossed marginally (8 of 36)
and the assumption that they do not interact is measured on `(off_target, rebalance, live, 1)` —
a well-chosen cell, since it is the one with real work in live mode. I verified the full 2,240
rows pass today (74s) and that `?run=paper` and `GET` map as the door maps them.

### Is it complete? No — here is what it omits

I checked the omissions rather than sampling the rows, taking them in order of how likely they
were to be wrong.

**Found a defect — `open_event` set with nothing resting.** Every `resting_*` state pairs
`open_ev` with live resting orders, and `mid_event` does too. No row has a **stale** `open_event`
— which is the state every real event is in the morning after its `day` orders expired unfilled.
Three consecutive cycles, record on target, nothing working at the broker:

```
event=rebalance  key=rebalance:2026-11-01   outcome=targets_met
open_remainder=False      resting_this_event=[]      alerts=[]
blocked_by_open_event='rebalance:2026-08-01'
reason: "...rebalance:2026-08-01 is still open with ORDERS OF THIS SLOT'S WORKING AT THE BROKER"
state after: open_event='rebalance:2026-08-01'   (unchanged, every cycle, for ever)
```

`open_remainder: False` sits in the same payload as a reason asserting that orders are working.
**That is the eighth message on this path to claim a property the code does not have**, written
by the item that was fixing the seventh. There is no alert, and the branch returns before the
no-progress ceiling — so it cannot escalate, which breaks item 70's own rule: *"A branch that
keeps an event open and cannot reach the ceiling has swapped a silent close for a SILENT HOLD,
which is not an improvement."*

**Why it is not a blocker, stated so the judgement can be checked.** The branch fires only when
the plan is empty, and with nothing resting an empty plan means the holdings already meet the
targets — so nothing needs doing while it refuses. The first event with real work sends, and the
send path overwrites `open_event`, so it self-heals. I could not construct a case where the stall
holds back a trade that was due. What it does cost is real but bounded: a false reason, no record
of the event, no escalation, and a permanently stale field that the next person to read it will
trust.

**Found a limit, not a defect — the wind-down is all-or-nothing on pricing.** The table has no
exit state at all (no row holds a name the book has dropped, which was items 67's and 69's whole
subject) and never crosses `one_missing` with a wind-down. Measured:

```
0%, both names priced       -> PLACED [AAPL sell 0.25, BBB sell 0.25]
0%, BBB bid-only (no mid)   -> preflight ok=False, planned [], PLACED [], alert preflight_failed
```

One unquotable name refuses the **whole** exit, including the name that *is* priced. That is
§8's own rule — *"that slot doesn't trade that cycle, alerts Don, and tries again next cycle"*,
and *"an error never sells"* — and it alerts rather than going quiet, so I am not blocking on it.
Don should know the shape: the exit works in session (item 64 measured IEX pricing 85 of 85) and
will refuse after hours (item 63's first real cycle refused on 26 names). It is the one place
where refusing everything is arguably the wrong trade-off, and changing it would mean inventing a
fallback mark, which Don has ruled out.

**Checked and clean.** Three omissions I expected to bite did not:

- **A broker position the record does not know about.** The table's fixture *derives* the broker's
  positions from the slot's own holdings, so no foreign position appears in any of the 2,240 rows
  and `positions="empty"` only tests the broker holding *less*. The dangerous direction — the
  broker holding *more* — is item 63's blocker. Tested with 999 TSLA: untouched.
- **A family slot (n ≠ 1).** Clean, above.
- **Out of session.** `now` is fixed at one in-session time, and three of the five installed crons
  are scheduled pre-market. All five, plus four edges:

```
06:30 / 07:00 / 07:30 ET  window_ok=False  PLACED []  processed []  attempt_day_counted None
09:40 / 11:10 ET          window_ok=True   PLACED [AAPL buy, BBB buy]   attempt_day_counted True
09:29 ET  "the session is not open for orders yet ... the window opens at 09:35 ET"
15:55 ET  "too late in the session to place a day order ... the window closes at 15:45 ET"
16:30 ET  same;   Saturday  "weekend - the market is closed"
```

Plans, sends nothing, **writes nothing**, spends no ceiling day, and the reason names the actual
clock and the window. `counts_a_day` being a precondition rather than an option is doing exactly
the work item 70 claimed for it.

**Omitted and not yet checked by anyone**, in descending order of what I would add first: an
exhausted event (at the ceiling) crossed with modes and reads, since the two exhaustion closes are
writes; a quiet cycle with no event at all, which is the commonest cycle there is; an **upward**
resize, so that `rebalance` and `buy_in` are not the only buy-producing events; a brand-new record
(item 67's one-off fresh refusal never fires, because every row's record carries `last_pct` and
`last_event_date`); and a new book superseding an open pct event, which is `overlap` in the other
order.

**One smaller thing about the 36-way control.** It asserts the three safety directions only, so a
tree that did nothing whatever would satisfy it. The main table has a positive control and this
sub-control does not — worth one line given that item 71 makes precisely this argument about its
own declaration.

---

## 3. The eight questions

| # | question | 10-15 | 10-16 | ③ | ④ | ⑤ | ⑥ | **today** |
|---|---|---|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | pass | pass | pass | pass ¹ | **pass** |
| 2 | per-stock math matches the paper book | FAIL | pass | pass | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | pass | pass | pass | *unsound* | pass | **pass** |
| 6 | a restart, retry or dispatch cannot repeat an order | FAIL | FAIL | FAIL | PASS | pass | pass | **pass** |
| 7 | **no check is vacuous** | FAIL | *pass (wrongly)* | pass | FAIL | FAIL | FAIL | **pass** |
| 8 | installing the workflow cannot place an order | pass | pass | pass | pass | pass | pass | **pass** |

¹ My sixth review passed question 1 as phrased while noting the inverse failed: one of the three
authorised events could not trade at all. That is now fixed, so the note comes off.

**Question 7 passes for the first time since 10-16, and that pass was mistaken.** The three
instances I raised last time are all closed: the close decision now reads the holdings' own
evidence (`order_read == "ok"`, nothing resting for this event, `open_event == key`);
`open_remainder` is read rather than merely reported; and `armed`'s false refusal text is gone.
Against that I am recording one false *message* — the stale-`open_event` reason — and I have
deliberately not stretched question 7 to cover it: the branch's **condition** is right and its
**sentence** is wrong, which is a different fault from a check that cannot fire. If it is still
there at the next review I will count it.

Re-verified rather than assumed: `assert_paper(LIVE)` → `NotPaperError`,
`assert_live_host(PAPER)` → `NotLiveError`, options `assert_paper(LIVE)` → `NotPaperError`; one
`_LiveClient` construction site passing no `base`; `/admin/live-slots` GET-only and
`/admin/live-cycle` `GET|POST` with a GET carrying a run token returning 405; exactly **one**
production caller of `run_cycle`, and it passes `may_write` explicitly, so the permissive default
has no implicit user.

**All ten live-path suites plus the table: 71 + 78 + 10 + 22 + 70 + 60 + 65 + 85 + 26 + 52 + 23 +
8 = 570 tests, all green.** Item 71 also repointed item 70's suite (52 tests now, up from 46),
which is the right response to a guard keyed to a location.

---

## 4. What I would require, and what I would not

**Nothing blocking.**

**Fix before the first real event:**

1. The stale-`open_event` reason must stop asserting that orders are working when
   `open_remainder` says none are, and that branch should reach the no-progress ceiling like the
   other two. A stale `open_event` with nothing resting is also a condition worth clearing rather
   than refusing on for ever.

**Fix when convenient:**

2. Add the five omitted table rows above, starting with the exhausted event.
3. Give the 36-way read control a positive direction.
4. Carried from earlier reviews and still open, all three acknowledged by item 71:
   `note_no_progress` records `_stamp()` rather than the cycle's `now`, so the ceiling reads the
   wall clock; `HOLDERS` is hard-coded; `orders_window` treats a caller-supplied `now` as ET
   regardless of its tzinfo. The first changes what every dated record on this path means and
   should not be rushed.

**Operational, for Don rather than for a lane:** the wind-down refuses entirely while any one
name in the book has no two-sided quote, so plan to set 0% during market hours. The sell-out then
works in one cycle.

---

## 5. On the verdict

I am saying that the gate is met: live keys may go in at 0%. I am not saying this path is free of
defects — I found two today, and six of the seven reviews before this one found something that
could have cost money.

What changed my answer is not that the list of findings is empty but that its character has
changed. Every blocker in this series was a case where the slot acted, or failed to act, **without
evidence**: an order sent on a name it could not price, a second buy-in on a record it could not
read, an event closed on a plan it had subtracted, a conclusion written by a cycle that could not
look. Today the path refuses in all of those, and it refuses in the direction that costs nothing —
no trade, an alert, a retry, and an end to the retry. Today's two findings are a sentence that is
wrong and a refusal that is too broad. Neither can move a share.

The one thing I want on the record about my own confidence. Six times I have found the next layer
after the previous one was fixed, and each layer was two states sharing one value: two names for
one call, `[]` as both empty and failed, truncated versus failed, three populations for one fact,
nothing-to-plan versus nothing-to-do, did-not-ask versus nothing-working, and 0%-flat versus
0%-holding. I said at the fifth review that I expected the next layer to be the last and that I
would not say so with confidence; I said at the sixth that I would not predict it again, and I
will not. What I will say is that the 2,240-row table is the first instrument on this path that
searches the state space instead of testing the cases someone thought of, and that it found two
defects its own author's fixes had missed. That is why the character of the findings changed, and
it is the reason I am answering yes rather than finding a seventh layer.

Going above 0% remains Don's decision and is not gated by this review. On the first real event I
would read three fields before anything else: `writes_allowed`, `plan_outcome`, and
`marks_coverage.missing` — in that order, because the first says whether the cycle could know
anything, the second says what it concluded, and the third says whether the free feed could price
the book.

---

## What I checked

- Item 71's three source diffs (`live_slots.py`, `live_cycle.py`, `app_saas.py`) line by line
  against its commit message; `DECISIONS.md` 2026-10-14 → 2026-10-17; my six previous reviews.
- Nine reproductions through `run_cycle` with the real `AlpacaPaperBroker` and real `_LiveClient`
  over recorded HTTP, `armed_state` derived throughout: the live sell-out at 0% with 999 TSLA
  present; 0% with an empty record; 0% paused; the 5%→2% resize control; the overlapping-event
  close and its self-heal; the no-read close in live, paper, dry and GET with the state file
  hashed; a stale `open_event` over three cycles; a wind-down with one name unpriceable; a family
  slot's authorization and isolation gates; a withheld write against a live send; and all five
  installed crons plus four session edges.
- `armed` / `slot_pct` on the correct variable; the four gates at 0% individually.
- `scripts/i71_table_before.py` run against `da2c07e`, figures reproduced exactly, sources
  restored byte-for-byte and verified.
- The table's axes, fixtures and row runner, to establish what it omits rather than taking the
  count on trust; the 36-way read control's cell and its assertions.
- Every production caller of `run_cycle`; the door's verb-to-permission mapping.
- 570 tests across twelve suites, all green.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
