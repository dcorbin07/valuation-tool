# AUDITOR THIRD REVIEW — the §8 live path after items 64 and 65

# NOT YET.

**My last blocker is closed. A new one arrived with item 64's schedule, and it is the same
question I have been asking since the first review: can the software place an order it should
not.** It can — a remainder re-send stacks up to **five full orders** against a one-order target,
and item 64's five-cron schedule makes two or three in-window cycles a routine day rather than an
accident.

**And a correction against my own last review, which matters more than the finding.** I marked
question 7 **CLOSED** on 2026-10-16. **It was not closed, and my verification was the reason I
could not see it.** I reproduced "unreadable positions" with a stub that **raises**; both real
clients return `[]` on a 5xx. Item 65 found this. My own test method committed the exact defect I
had criticised the project's tests for two reviews running — a double that passes because the
double is not the real thing.

**Reviewer:** auditor lane · **Date:** 2026-10-17 · **Reviewing:** items 64 and 65
**Gate:** item 65 is on `origin/main` (`bc52c55`, `e53d355`, `252ebcc`, `213022d`, `41e26a8`) —
checked before starting, as instructed.
**Suites:** `test_item58` 71, `test_item58b` 77, `test_item58b_doors` 22, `test_item63` 68,
`test_item64` 59, `test_item65` 52 — **349 of 349 green.** The blocker below passes all 349.

Third in a series; `AUDITOR_REVIEW_live_path.md` and `AUDITOR_REREVIEW_live_path_2026-10-16.md`
are left unedited as the record of what was true then.

---

## The blocker: a remainder re-send stacks positions, and the new schedule makes it routine

**Reproduced end to end through `run_cycle`, with the real `AlpacaPaperBroker` class and recorded
HTTP.** Target 100 shares. Each cycle's order rests unfilled, as a day limit at the mid routinely
does:

```
cycle 1: planned=1 sent=1 resting_seen=0   holdings={}
cycle 2: planned=1 sent=1 resting_seen=1   holdings={}
cycle 3: planned=1 sent=1 resting_seen=2   holdings={}
cycle 4: planned=1 sent=1 resting_seen=3   holdings={}
cycle 5: planned=1 sent=1 resting_seen=4   holdings={}
cycle 6: planned=1 sent=0  -- the no-progress ceiling stops it

   valquo-paper-rebalance:2026-10-22-AAPL-a1   buy 100
   valquo-paper-rebalance:2026-10-22-AAPL-a2   buy 100
   valquo-paper-rebalance:2026-10-22-AAPL-a3   buy 100
   valquo-paper-rebalance:2026-10-22-AAPL-a4   buy 100
   valquo-paper-rebalance:2026-10-22-AAPL-a5   buy 100
   target 100 shares; total live BUY quantity = 500
```

**The mechanism, in three facts that are each individually correct.**

1. `reconcile` builds holdings from **fills only** — correct, and deliberately so: a record built
   from submissions would claim holdings the account does not have.
2. The wash-trade clearing cancels only the **opposite** side. Also correct, and
   `test_a_resting_SAME_side_order_is_NOT_cancelled` gives the right reason: *"cancelling a
   same-side order would throw away a working order for nothing."*
3. So a resting **same-side** order is neither counted as a holding nor cancelled — and
   `order_plan` computes `target − filled`, which is the whole remainder again.

**Each decision is right and the composition is not.** §8a's own wording is *"an order unfilled or
partly filled by the close is **re-priced** and re-sent each following cycle"*. Re-pricing an order
means replacing it. Within one session this re-sends **without** re-pricing the first one away, so
it is an addition rather than a replacement.

**Why this was safe until item 64 and is not now.** A `day` order expires at the close, so with
**one** cycle per session "re-send next cycle" really is a re-price: yesterday's order is gone.
The single `40 14 * * 1-5` cron gave exactly that. Item 64's pending workflow adds four more:

```
- cron: "30 11 * * 1-5"      - cron: "40 14 * * 1-5"
- cron: "0 12 * * 1-5"       - cron: "10 16 * * 1-5"
- cron: "30 12 * * 1-5"
```

By the workflow's **own** delay table, the first three all land inside the 14:35–19:45Z orders
window once GitHub's measured 3.45–7.48h delay is applied — roughly thirty minutes apart. So two
or three in-window cycles per session is the **designed** behaviour, and
`concurrency: cancel-in-progress: false` makes them queue and run sequentially, each seeing the
previous one's resting order. The stacking is deterministic, not a race.

**The workflow's justification is the sentence that is wrong:**

> *"**AND AN EXTRA RUN COSTS NOTHING**, which is what makes this the right instrument: the door is
> idempotent per event — an event whose targets are already met closes and sends nothing."*

The door is idempotent **when the targets are met**. The case that matters is the one where they
are not met *because the previous order has not filled* — and there an extra run costs a duplicate
order. The schedule was widened on an idempotency claim that does not hold in the state the
schedule exists to retry.

**What bounds it, and this is item 64's own work doing the containing.** The no-progress ceiling
stops the slot at **5** consecutive cycles without a holdings advance, so exposure is capped at
roughly 5× the authorised target and the slot then alerts. It is also self-correcting: if the
stacked orders fill, the next cycle sees the over-holding and sells down (`order_plan` caps a sell
at `have_qty`, so it cannot overshoot into a short). So this is not unbounded and not permanent.

**It is still a blocker, for a reason specific to what §8 authorises.** This is a
percentage-of-equity mandate. A slot authorised to hold X% of the account can, on an ordinary day
where the mid does not get hit, carry up to 5X% of live buy orders — and if the market moves
through them, 5X% of position until the next cycle unwinds it. That is a breach of the one number
the account holder actually authorised, produced by the scheduler rather than by any broken input.

**Why 349 tests miss it.** `test_a_resting_SAME_side_order_is_NOT_cancelled` exercises exactly
this state and asserts only `sess.cancelled == []`. It documents the decision not to cancel and
never asks the consequent question — *if the working order is kept, must it be subtracted from the
plan?* No test runs two in-window cycles with an unfilled same-side order and checks the **total
quantity sent**.

**Two fixes, either sufficient.** Subtract resting same-side quantity from the delta in
`order_plan` — the planner's `have` becomes filled **plus** this slot's own resting on that side —
which is the smaller change and keeps the working order. Or cancel-and-replace the same-side
resting order, which is literally what "re-priced" means and reuses the confirmed-cancel machinery
item 65 just built. I prefer the first: it keeps a working order working, which is the reason the
same-side cancel was rejected in the first place.

---

## The five questions

### 1. My residual route — **CLOSED**, and the fix is deeper than the one I proposed

State lost, `/v2/orders` unreadable, `/v2/positions` readable. Driven end to end through
`run_cycle` with the real client class and recorded HTTP, **with the market forced open** so the
session gate could not mask the result:

```
A. /v2/orders HTTP 500, positions hold the book, state lost, session OPEN
   order_read   : failed
   ORDERS SENT  : []
   reason       : the broker's orders could not be read (HTTP 500)
```

**And item 65 found that my proposed `if` could never have fired.** I recommended "make a failed
`reconcile` refuse". But both clients returned `[]` on a 5xx, so `reconcile` never reported
failure — it reported **success with an empty book**. My diagnosis of the state was right
("truncated and failed are the same epistemic state") and my fix was aimed one layer too high.
`orders_result()` / `positions_result()` on both clients, plus `reconcile`'s four-state
`order_read` (`not_attempted` / `failed` / `truncated` / `ok`), is the correct depth. Keeping
`not_attempted` as a **third** state is right: collapsing it would refuse every dry cycle.

**Other empty-scope routes the same derivation could reach.** I looked. One remains, and I am
recording it as a **noted risk rather than a blocker**: an order read that **succeeds and returns
empty** while positions are held. The slot then treats those positions as Don's own — which is the
documented, deliberate scope choice, and the right one, since refusing on unexplained positions
would brick a healthy account. It would take state loss *plus* a successful-but-empty order read
to produce a duplicate. A full page already refuses, so age-out cannot silently truncate; a
genuinely empty page means no orders exist. **A cheap hardening if wanted:** a slot whose record
is entirely fresh — no holdings, no processed events, no recorded `account_id` — meeting a
non-empty account is ambiguous, and refusing once there would cost one cycle and close the last
corner of this family.

### 2. Item 64's changes — **three sound, one introduces the blocker**

**The per-attempt order-id suffix: sound.** `valquo-<slot>-<event>-<ticker>-a<send_seq>`. Verified
distinct across cycles and across a ceiling reset.

**The two counters: sound, and the separation is the right diagnosis.** One counter was serving
two purposes with opposite requirements — the ceiling must reset on progress or a healthy
rebalance stops itself; the suffix must never reset or it reproduces an id Alpaca has accepted.
`send_seq` is monotone while the event is open; the ceiling keeps its own and resets on a holdings
advance; both are cleared when the event closes (`live_cycle.py:804`). **Progress is measured on
holdings rather than order count**, which is the correct choice — an order accepted and never
filled is exactly what a permanent rejection produces, so counting orders would hide the thing the
ceiling exists to catch. The no-baseline rule (a counter written under the old meaning is not
evidence) is the right call and would otherwise have stopped a healthy rebalance one cycle later.

**`_rejection_reason`: sound.** Reads both clients' incompatible failure shapes and unwraps
Alpaca's nested body:

```
live  {'error': {'message': 'potential wash trade detected'}}  -> potential wash trade detected
paper {'reason': ..., 'detail': {'error': {'message': ...}}}   -> the broker rejected the order;
                                                                  client_order_id must be unique
neither shape                                                  -> "the client refused it and said
                                                                  nothing; the reply keys were ['ok']"
```

That last line is the right behaviour: it reports that nothing was said, rather than printing
`None` as though `None` were the reason.

**The new schedule: this is the blocker.** See above. The schedule reasoning about GitHub's
measured delay is careful and well-evidenced; what was not revisited is whether the cycle is safe
to run more than once per session.

**Could any of them send an order a broken input should have stopped?** No — none of the four
converts a refusal into a send. **Could a remainder re-send double a position? Yes**, and that is
the blocker. It is not a broken input; it is a correct input re-planned.

### 3. Item 65's wash-trade handling — **CLOSED**

Verified end to end with a cancel that succeeds and one that returns 500:

```
cancel CONFIRMED -> placed=[('AAPL','buy'), ('MSFT','buy')]   blocked=[]
cancel FAILS     -> placed=[('MSFT','buy')]                   blocked=['AAPL']
```

The cancel is confirmed **before** the opposite side is sent (`if res.get("ok")` → proceed, else
`blocked = True; continue`), an unconfirmed cancel means that **name** does not trade, and the
other names still trade — §8's rule applied at the right granularity. Only this slot's own orders
are ever cancelled, because `reconcile` filtered by the `valquo-<slot>-` prefix before recording
them. Treating a 404 as cancelled (not-resting is the property needed) and a 422 as not cancelled
(already filled is a holdings fact) is the correct asymmetry. `_LiveClient` gaining a `cancel` was
the fourth divergence between the two clients on this path and is now covered by item 63's derived
interface test.

### 4. My three notes

| note | status |
|---|---|
| **id pin when the broker returns no id** | **taken** — `account_id_recorded` is now reported for live slots, so an unpinned slot is visible rather than silent |
| **the `HOLDERS` list** | **not taken** — still a hand-typed `("client", "pc", "paper_client")`. Latent, not live: I re-censused every attribute call in `live_cycle` and every client-shaped call still goes through a covered name. It remains the hand-typed list inside the derivation that exists to avoid hand-typed lists |
| **pagination** | **not taken, and correctly declared not-done.** `ORDERS_PAGE_LIMIT = 500`, no cursor; a full page refuses rather than under-counting. Fails safe. At 86 names and four rebalances a year that page fills in roughly 18 months — and item 64's own figure of 239 orders for one event makes that sooner than my last estimate: ~2.8 orders per name per event means the 500-page fills in about **two events**. This should be fixed before the second or third quarterly rebalance, not in 2028 |

That pagination revision is a correction to my own last review, prompted by item 64's measured
order count. I previously reasoned one order per name per event; the real ratio is nearly three.

### 5. My eight questions, as of today

| # | question | 10-15 | 10-16 | **today** |
|---|---|---|---|---|
| 1 | trades only on the three events | pass | pass | **pass** |
| 2 | per-stock math matches the paper book | FAIL | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | pass | **pass** |
| 6 | **a restart, retry or dispatch cannot repeat an order** | FAIL | FAIL | **FAIL** |
| 7 | no check is vacuous | FAIL | *pass (wrongly)* | **pass** — genuinely, now |
| 8 | installing the workflow cannot place an order | pass | pass | **pass**, with a caveat |

**Question 6 has failed three times for three different reasons** — the empty record, the empty
scope, and now the un-subtracted resting order. Each previous fix was correct and each exposed the
next layer. That is a path converging, not a path in trouble; but the question is not yet answered
yes.

**Question 7 is marked pass with an asterisk in the middle column deliberately.** I called it
closed when it was not. The refusal existed and could not fire through a real broker. It fires
now — I verified it against the real class with a recorded 500, not against a raising stub.

**Question 8's caveat:** the *installed* workflow still carries the single 14:40Z cron and
`?run=paper`, so nothing changes until Don installs the pending copy. The pending copy cannot send
live either — the token is still `?run=paper` and the one construction site is behind the live
gate. But **installing it is what makes the blocker above routine**, so it should not be installed
before the planner change.

---

## What I would require

**Blocking — one item:**

1. **A remainder must not add to a resting same-side order.** Either subtract this slot's own
   resting same-side quantity in `order_plan`, or cancel-and-replace using item 65's
   confirmed-cancel machinery. Plus a test that runs **two in-window cycles** with an unfilled
   same-side order and asserts the **total quantity sent** does not exceed the target —
   `test_a_resting_SAME_side_order_is_NOT_cancelled` reaches this exact state and asserts only
   that nothing was cancelled.

**Sequencing, which matters as much as the fix:** do not install the five-cron workflow until that
lands. The current single-cron copy is safe because a day order expires between cycles.

**Recommended, not blocking:**

2. Refuse once when a slot with an entirely fresh record meets a non-empty account — the last
   corner of the empty-scope family.
3. Real cursor pagination, now on a ~two-event horizon rather than an 18-month one.
4. Derive `HOLDERS`, or assert no attribute call on any other local name resolves to a client.

---

## On the verdict, and on my own last review

Entering keys at 0% sends nothing, and a slot at 0% never reaches the planner. I considered
calling this a pass on that basis and did not, for the same reason as last time: the only thing
between 0% and a 5× position is Don typing a percentage, and the sequencing risk here is real
rather than theoretical — the workflow that makes it routine is sitting in `pending_workflows/`
waiting for a double-click, and nothing in that file warns against installing it first.

Items 64 and 65 are good work. Item 65 in particular found a defect **underneath** my own
recommended fix and said so plainly, including that it sat under a repair I had marked closed —
which is the second time this path's authors have caught something my verification missed. The
honest summary of three reviews is that the real-money rails have been sound throughout and the
execution layer has taken four rounds to get right, with each round exposing the next layer rather
than repeating the last.

---

## What I checked

- **Reproduced end to end through `run_cycle`, with the real `AlpacaPaperBroker` class and
  recorded HTTP** (not raising stubs — the mistake that cost me question 7 last time): my residual
  route with a real 500, with the market both shut and forced open; the remainder stacking over
  seven cycles; the wash-trade cancel in both the confirmed and unconfirmed directions;
  `_rejection_reason` on both clients' failure shapes.
- **Read** the diffs for items 64 and 65 across `live_cycle.py`, `live_slots.py`,
  `alpaca_broker.py`, both workflow copies, and the new `test_item64` and `test_item65` suites —
  and read the commit messages **last**, against the code rather than for it.
- **Re-censused** every attribute call in `live_cycle` against the `HOLDERS` list.
- **Ran** all six suites: 349 green. The blocker passes every one of them.
- **Not checked:** anything against a live or paper Alpaca account. No network call, no credential
  read. The service-side evidence in items 64 and 65 — six real cycles, 239 orders, 161 filled, 81
  of 85 names held, two confirmed wash-trade rejections — I take as reported. **I could not
  determine from here whether any of those 239 orders stacked**, because I cannot see whether two
  orders for one remainder both filled; the figures are consistent with it and do not establish
  it.
