# AUDITOR — TENTH REVIEW OF THE §8 LIVE PATH — 2026-10-27 (after item 83)

**SAFE TO RAISE ABOVE 0% WHEN DON CHOOSES.**

I said that in my ninth review and the paper slot then borrowed $4,760. So before anything else:
**my ninth review was wrong, and I can say exactly why.** My account fixture set `cash`,
`buying_power` and `non_marginable_buying_power` to one number, `multiplier` to `"1"` and `status`
to `ACTIVE` in every review I have written. No test of mine could distinguish those fields or
exercise a margin account, which is the whole of the defect. Worse, at review 6 I *credited* the
old rule's `min(cash, buying_power)` as protection "so a wrong multiplier cannot widen the
budget" — and that was the fallback branch for when `non_marginable_buying_power` is **absent**.
On the paper account the field was present, so the protection I credited could not fire. I
reported a guard whose precondition was the absence of the field that caused the loss.

Item 83's rule is right, and I have tested it with fixtures whose fields disagree. One
non-blocking finding, whose consequence I measured rather than assumed.

Gate: item 83 (`a7807d9`) is on `origin/main` and merged, along with items 79–82. Reviewed
read-only. No network call to Alpaca, no credential read, no source file changed, `DECISIONS.md`
untouched.

---

## 1. Can any buy spend more than cash, on any multiplier? — **No.**

### The rule in isolation, against bodies whose fields disagree

`NO_BORROW_FIELD` is now `"cash"`, which makes that constant's name true of what it holds, and
`non_marginable_buying_power` has joined `LEVERED_FIELDS` — named as refused rather than silently
unused.

| account body | budget | the old rule |
|---|---|---|
| **Alpaca's documented sample** — cash −23,140.20, nmbp +7,386.56, mult 4 | **0.00** | 7,386.56 |
| **the paper account at 17:46Z** — cash 7,843.80, nmbp 41,831.33, mult 4 | **7,843.80** | **41,831.33** |
| after it borrowed — cash −4,759.68, nmbp 36,000 | **0.00** | 36,000 |
| the IRA's limited margin — cash 5,000, mult 1 | 5,000.00 | 5,000 |
| mult 2, cash 1,000 below bp 2,000 | **1,000.00** | 2,000 |
| multiplier absent entirely, cash 1,000, nmbp 9,999 | **1,000.00** | 9,999 |
| cash exactly 0, nmbp 50,000 | **0.00** | 50,000 |

The multiplier is read and recorded and never branched on, which is the right shape: the cap is
cash at 1x and at 4x by the same arithmetic.

### A broken or incomplete read sizes nothing

Nine shapes, all `ok=False, amount=None`: the account read failed; no account; a bare string; an
empty body; `cash` absent; `cash` unparseable; `cash` None; **only `buying_power` present**; and
**only `non_marginable_buying_power` present**. The last two matter most — a body carrying a
levered field and no cash is refused rather than substituted, which is the exact substitution that
caused the loss.

### An open buy that cannot be valued refuses the whole reservation

| open orders | `open_buy_value` | budget on cash 2,000 |
|---|---|---|
| two valuable open buys (1,500) | ok, 1,500 | **500.00** |
| one carrying no `limit_price` | **ok=False** | **refused** |
| one carrying no `qty_open` | **ok=False** | **refused** |
| an open **sell** | ok, 0 | 2,000 — not reserved |
| nothing open | ok, 0 | 2,000 |

Refusing on an unvaluable open buy is the direction that does not borrow, and not reserving a sell
is what lets a rebalance reinvest its own proceeds.

### End to end, through `run_cycle` with the real client classes

| scenario | budget | placed | net cash spent |
|---|---|---|---|
| **2026-10-26's shape** — margin account, resting buys worth 20,000, a remaining gap, cash 7,843.80 | **0.00** | **none** | 0 |
| the same, already overdrawn at −4,759.68 | 0.00 | none | 0 |
| Alpaca's documented sample | 0.00 | none | 0 |
| the IRA at 1x with the same cash | 0.00 | none | 0 |
| **partial fills** — 20 ordered, 8 filled, 12 open each | **8,000** (20,000 − 12,000 reserved) | 10 | **exactly 8,000** |
| **buys and sells in one cycle** — five over target, five under, cash 1,000 | 1,000 | 10 | **−19,000** (cash raised) |
| cash drops to 0 mid-event | 0.00 | none | 0 |
| a 50,000 deposit mid-event | 50,000 | 10 | 40,000 — the frozen gap |
| a 1,000,000 deposit mid-event | 1,000,000 | 10 | **40,000** — still the gap |

The partial-fill row is the one that would have prevented 2026-10-26 on its own: the **open part**
is reserved at its own limit price, not the whole order and not nothing. And the deposit rows show
item 73's frozen targets still capping the other side — a huge deposit buys the gap, not the
budget.

---

## 2. Does capping at cash stall a rebalance in the IRA? — **No. It serialises it.**

Five names over target, five under, cash 0:

```
cycle 1  nothing resting      budget 0     placed 5 SELLS, 0 buys   cash raised 20,000
cycle 2  the sells resting    budget 0     placed nothing           outcome waiting_for_cash
cycle 3  still resting        budget 0     placed nothing           outcome waiting_for_cash
cycle 4  sells filled, cash 20,000         placed 0 sells, 5 BUYS   spent exactly 20,000
```

That is item 67's sells-first design and item 83's cap composing as intended: the sells are never
reserved, so they go; the buys wait for the cash they raise; and when it lands they spend exactly
it. The rebalance completes — in two steps rather than one.

**A sell that never fills escalates rather than stalling.** Chained from its own record over
trading days, skipping the weekend: days 1 → 6, then `event_attempts_exhausted` and `open_event`
cleared. That is item 77's fix doing its work — a cash wait *with something resting* spends a
ceiling day.

**And a pure cash wait never exhausts, which is correct by ruling.** Nothing resting, no cash: one
`waiting_for_cash` alert on the first cycle and then silence, `attempt_day_counted=None` for ever.
That is Don's own instruction — *"Waiting for cash is a normal state: one plain alert, and no
ceiling burn"* — and the distinction from the escalating case is exactly the two halves of it. I
went looking for an exhausted cash wait still reporting *"this is not a failure"*; it cannot
happen, because a pure cash wait does not reach the ceiling at all.

---

## 3. The self-heal trim — **it cannot sell what the slot did not buy, and cannot loop**

Simulated from 2026-10-26's end state: holdings 104,750 against equity 100,000, cash −4,759.68,
with Don's 999 TSLA held by hand in the same account.

```
cycle 1  budget 0.00   10 sells, 0 buys   cash RAISED 4,750   TSLA touched: False
cycle 2  nothing to do                     cash −9.68   holdings exactly 100,000
```

Converged in one cycle, which matches item 83's prediction of "about $4,760 of sells and cash back
to roughly zero". Three properties verified rather than argued:

- **No buy while overdrawn.** The budget is 0.00 on cycle 1 because cash is negative, so the trim
  is sells only. There is no debit loop available: a sell raises cash, and the cap stops the
  proceeds being over-spent on the way back.
- **Nothing it did not buy.** TSLA is never quoted, planned or sold.
- **The sharpest form — a book name Don *also* holds by hand — is protected twice.** With the slot
  holding 10.475 of N0 and Don holding 500 more, `preflight` refuses the whole cycle and names it:
  *"this slot's record holds 10.475000 of N0 and the broker reports 510.475000"*. And if it ever
  got past that, `order_plan` caps a sell at the slot's own record — target $100 → `sell 9.475`,
  a full exit → `sell 10.475`, never 510.475.

Same on a live slot with production's own arming: 10 sells, 0 buys, cash raised, TSLA untouched,
event closed on the next cycle.

**One operational consequence Don should know**, and it is pre-existing rather than item 83's: that
record-versus-broker refusal means holding a **book name** by hand in a live slot's account blocks
that slot entirely until the hand position is gone. It is the safe direction and it is loud, but it
is a constraint on the account rather than a bug.

---

## 4. Did anything in my ninth review rest on the old sizing rule?

**Yes — the verdict, and one credit from review 6. Both are withdrawn.**

- **Review 9's verdict is withdrawn.** It said safe to raise above 0%, and there was a route by
  which the path could overspend: the buy budget could exceed cash on a margin account. The paper
  slot then took it.
- **Review 6's credit for `min(cash, buying_power)` is withdrawn.** I described it as protection
  against a wrong or unreported multiplier. It is the `elif` for when
  `non_marginable_buying_power` is absent, so it could not fire on an account that reports the
  field — which is every Alpaca account.

**What does *not* need withdrawing, checked rather than assumed:** reviews 8 and 9's blocker
findings are independent of the budget. Blocker A is arming, B is event keys, C is frozen shares,
and item 83 changes none of them — I re-ran nothing of them here because item 83 touches
`spendable`, `open_buy_value` and `reconcile`'s `limit_price`, and the three suites that pin those
blockers are green. The frozen-gap cap I credited in review 8 ("$100,000 against a $600 gap buys
exactly $600") is also independent, and the deposit rows above re-confirm it.

### The generalisable form of my miss, and what else it concealed

The defect was invisible to me because of a fixture, not a reasoning error — so the useful question
is what *else* that fixture pinned. Five things: the three cash-ish fields equal, `multiplier` 1,
and `status` ACTIVE. Two of the five concealed real behaviour: item 83's, and this —

**A blocked or closed account still gets a full budget and still transmits.** `account_blocked`,
`trading_blocked` and `status` are all read by the settlement census and **gate nothing**:

```
ACTIVE (the fixture I always used)    budget 20,000   placed 2 buys
account_blocked True                  budget 20,000   placed 2 buys
trading_blocked True                  budget 20,000   placed 2 buys
status ACCOUNT_CLOSED                 budget 20,000   placed 2 buys
```

**Non-blocking, because I measured the consequence rather than assuming it.** Driving a rejecting
broker over seven cycles: `broker_error` twice per cycle carrying the broker's own words — *"the
broker rejected the order; account is not authorized to trade; HTTP 403"* — holdings unchanged
every cycle, nothing spent, and `event_attempts_exhausted` on the 6th trading day. The
classification is right too: *"account is not authorized to trade"*, *"account is blocked"* and
*"trading is blocked"* are all **not** settlement waits, so none is swallowed as a quiet deferral.

So the slot sends into a wall, is refused, and Don is told twice. It is the same family as item
83's defect — a field read, reported and not acted on — which is why it belongs in this section
rather than in a list of its own.

---

## The eight questions

| # | question | ⑦ | ⑧ | ⑨ | **today** |
|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | FAIL | pass | **pass** |
| 2 | per-stock math matches the paper book | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | pass | FAIL | pass | **pass** |
| 6 | a restart, retry or dispatch cannot repeat an order | pass | pass | pass | **pass** |
| 7 | **no check is vacuous** | pass | FAIL | pass | **pass** ¹ |
| 8 | installing the workflow cannot place an order | pass | pass | pass | **pass** |

¹ The blocked-account fields are read and gate nothing, which is adjacent to question 7 but is not
a vacuous *check* — nothing claims to gate on them. The old `min(cash, buying_power)` branch
**was** a vacuous guard on every real account, and it is gone.

A ninth question is now worth carrying, because it is the one this review exists for:
**does any figure the path spends against mean what its field name says?** Item 83 answered it for
the budget by making `NO_BORROW_FIELD` literally `"cash"` and shipping `account_figures` so the
provenance is checkable after the fact.

Re-verified: `assert_paper(LIVE)` → `NotPaperError`, `assert_live_host(PAPER)` → `NotLiveError`,
options `assert_paper(LIVE)` → `NotPaperError`; one `_LiveClient` site passing no `base`;
`LIVE_PCT` absent/empty/`abc` → not armed, `0` → armed sell-only, `5` → armed.

**All twenty-four live-path suites: 964 tests, 0 failing.**

**Item 83's before-control reproduces, in both directions.** 15 of 17 item-83 tests fail against
the pinned baseline, **and 4 of item 67's 87 fail too** — the four that assert the new rule by
name. That second direction is the strong part: it shows the repointed guards tracked a change of
rule rather than being loosened until they passed. Sources restored byte-for-byte; the tree is
clean.

---

## What I would require

**Nothing blocking.**

1. **Gate on `trading_blocked` / `account_blocked` / `status`** where they are already read, or say
   in one line why sending into the rejection is preferred. The consequence is bounded either way;
   the reason to fix it is that five days of rejections burn the no-progress ceiling for an event
   that was never going to trade.
2. **Carried and still open:** `note_no_progress` records `_stamp()` rather than the cycle's `now`;
   `HOLDERS` is hard-coded; `orders_window` treats a caller-supplied `now` as ET; and from review 9,
   `/admin/live-slots` reports *"its own record holds nothing"* about a holding slot at an unstated
   percentage, and the 10,000-order page cap is still ahead of the paper slot.

**For Don, on the first live cycle.** Read `budget.account_figures` before anything else. It now
ships `cash`, the multiplier, and every levered field **named as refused**, so "was the budget
bigger than the cash" is answerable from the record rather than by derivation — which is the
second finding in item 83 and the reason the first one took arithmetic to establish.

---

## On the verdict, and on my own record

I have now passed this path twice and been wrong once. That is the fact that should set how much
my pass is worth, and I would rather state it than let the verdict line carry more weight than it
has earned: **the measurements in this review are worth more than the verdict on it.** What I can
say precisely is that the rule is now narrow enough to test exhaustively — cash minus open buys,
negative reads as zero, no buying-power field consulted at any multiplier, the multiplier not
branched on — and that I have tested it against the body that actually caused the loss, against
Alpaca's own documented sample, against nine broken reads, five reservation shapes and nine
end-to-end cycles including partial fills and mixed buys and sells.

What I got wrong in nine reviews was not a chain of reasoning. It was one fixture, repeated. Every
account I built had its three cash-ish fields equal and its multiplier at 1, so the single most
consequential question on this path — *does the number we spend against mean cash?* — was
unanswerable by construction in every test I wrote. Item 83 made Alpaca's own contradictory sample
a permanent fixture, which is the right repair, and I have varied five account fields here rather
than one.

The lesson I would carry further than this path: **when a value comes from outside, vary the fields
against each other, not just the value.** A fixture where every field agrees cannot test a rule
that picks between them — and "pick the right field" was the whole of the rule.

---

## What I checked

- Item 83's commit and full diff on `settlement.py` and `live_cycle.py`; the **old** `spendable` at
  `a7807d9^` to establish what my review-6 credit had actually described; `DECISIONS.md`; my ninth
  review.
- Items 79–82's scope, to confirm none of them touches the trading decision.
- `spendable` on 7 disagreeing-field bodies, 9 broken or partial reads, and 5 reservation shapes;
  `open_buy_value` on each; `is_settlement_wait` on four blocked-account strings.
- Fourteen cycles through `run_cycle` with the real `AlpacaPaperBroker` and real `_LiveClient` over
  recorded HTTP, `armed_state` derived: 2026-10-26's shape at four account states; partial fills;
  buys and sells together; three mid-event cash levels; a four-cycle sells-then-buys sequence; an
  eight-cycle never-filling sell; a seven-cycle pure cash wait; the trim on the paper slot and on a
  live slot; a book name held by hand; and seven cycles against a rejecting broker.
- Which account fields the path reads at all, and which of them gate anything.
- Item 83's before-control run in both directions, with the restore verified.
- 964 tests across twenty-four suites.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
