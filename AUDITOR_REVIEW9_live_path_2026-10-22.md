# AUDITOR — NINTH REVIEW OF THE §8 LIVE PATH — 2026-10-22 (items 77 and 78)

**SAFE TO RAISE ABOVE 0% WHEN DON CHOOSES.**

All three of review 8's blockers are closed. I reproduced each against the before-state recorded
in that review, re-ran every check after item 78 landed on top, and went looking for what the two
items had opened between them. What I found is one false sentence on a dashboard and one dated
wall some weeks out. Neither can move a share or withhold a trade.

Gate: items 77 (`b3afe64`) and 78 (`67f66e3`) are on `origin/main` and merged into this branch.
Review 8 landed at `f2af6c1` after item 76 repointed the guard that had held it. Reviewed
read-only. No network call to Alpaca, no credential read, no source file changed, `DECISIONS.md`
untouched.

---

## The three blockers

Every reproduction runs through `run_cycle` with the real `AlpacaPaperBroker` and real
`_LiveClient` over a recorded HTTP session, with `armed_state` derived inside `run_cycle` from the
environment and the slot's own record. All of it re-run after item 78.

| | review 8 | today |
|---|---|---|
| **A** `LIVE_PCT` absent, on a slot holding its book | **transmitted `AAA sell 5, BBB sell 5`** | `armed=False`, nothing placed |
| **A** the variable's name wrong (`_PCT`) | **transmitted both sells** | `armed=False`, nothing placed |
| **A** the variable set to `""` | **transmitted both sells** | `armed=False`, nothing placed |
| **A** control: a *stated* `0` | sold out (correct) | **still sells out** |
| **A** control: `0%` holding nothing | — | silent, no alert |
| **A** malformed `abc` | refused | still refuses |
| **B** switch flips 3 and 5 (`0→5→0→5→0→5`) | **refused for ever, `last_pct` stuck** | `#2` and `#3` each buy in and sell out |
| **B** the second exit after a rebalance | **held the book, no alert** | sells out |
| **C** price 130 inside an open event | **`AAA sell 0.153846` ×2** | `buy 1.0` |
| **C** price 300 inside an open event | **`AAA sell 2.333333` ×2** | `buy 1.0` |
| **C** prices 70 / 100 / 130 / 300 | quantity moved with price | **identical at every price, no sell anywhere** |
| non-blocking: resting order + cash gap | no ceiling day, ever | spends one; a *pure* cash gap still spends none |
| non-blocking: `frozen_targets` | accumulated for ever | pruned to the event in hand |

**On A, the refusal says which state it is in** — *"slot 1 has keys but no
ALPACA_ACCOUNT_1_LIVE_PCT, so the slot is at an ASSUMED 0% while its own record still holds
position(s). An absent percentage is not an instruction to sell"* — and two cycle alerts fire,
`pct_unstated_while_holding` and, where the misspelling is present,
`unknown_slot_variable` naming `ALPACA_ACCOUNT_1_PCT`. `unknown_slot_vars` carries **no value**,
which I checked by planting a fake secret in an unknown suffix: nothing leaked.

**On B, the replacement for the guard item 77 made unreachable holds, and it is stronger than
what it replaced.** Item 77 says plainly that `processed` becomes unreachable for percentage keys
and that restart protection is now `last_pct` + `open_event`. I hammered that: three identical
cycles from one record place nothing, and a record **rolled back** one cycle — what a crash
between the send and the state write looks like — produces a *new* occurrence key (`#4`) that the
old guard would also have missed, and still places nothing, because the shares are already there.
So duplicate protection for percentage events now rests on the **reconciled holdings** rather than
on a bookkeeping list. That is a reality check instead of a record of intent.

**On C, I used the stronger assertion rather than the obvious one.** "No sell is produced" passes
whenever nothing is planned at all — which is the trap item 77 reports catching in its own fix,
where parity blocked the send on every price move. So I asserted the quantity is *identical* at
every price: `buy 1.0` at 70, 100, 130 and 300. And I checked the property the whole fix rests
on, which neither item 77 nor I had tested — **does the freeze survive the new pruning across
cycles?** Three consecutive cycles of one open event through a +60% and a −40% swing, driven from
the record each cycle left: `frozen_target_qty` stays `{AAA: 5.0, BBB: 5.0}`, the plan stays
`buy 3.0`, and the first cycle created the freeze itself.

---

## Item 78, and why it mattered that these two were reviewed together

Item 78's headline is operational — the paper slot was refusing an order history it had read in
full, which would have stopped Monday's rebalance. Two of its parts land in my scope.

**The 510-order refusal is fixed without opening the refusal it had to keep.** `len(orders) >= 500`
was written for a reader that saw one page; item 67 made the reader paged and `orders` became the
total, so it fired on any slot whose whole history exceeded 500 however completely it had been
read. The check now applies only to the unpaged branch. Verified: 510 distinct orders →
`order_read=ok`, `pages=2`, `n_orders=510`.

**I tested the composition risk I named when item 77 landed, because item 77 had just made the
holdings read load-bearing.** If paging ever turned an incomplete read into a false `ok` with a
short history, the gap would read large and the slot would re-buy. Every incomplete shape still
refuses, end to end, with item 71's write gate holding:

```
a full page, ALL one stamp        order_read=truncated  writes_allowed=False  PLACED=[]  record unchanged
more pages than MAX_ORDER_PAGES   order_read=truncated  writes_allowed=False  PLACED=[]  record unchanged
the second page fails / None      ok=False              refuses
the cursor never advances         truncated             refuses
a full page with no timestamps    truncated             refuses
```

**And item 78 found a silent under-count that had been live since item 67 — which is the same
hole from the other side.** `paged_orders` refused a tie on the last timestamp *within* a page and
skipped it on the *next* page, because `after` is exclusive. Measured on 501 orders whose last two
share a stamp: 500 returned, `ok=True`, `truncated=False`. A dropped fill under-counts a holding,
and an under-counted holding makes the planner buy the difference again. Verified fixed: all 501
read, deduped, the tied order present. So item 77 moved duplicate protection onto the holdings
read in the same week item 78 closed a hole in it. Reviewing them apart would have passed a path
whose new protection rested on a reader that silently lost orders.

**The eighth substring-ban instance, and this one withheld a broken-slot warning.**
`return_violations` banned the substring `return` and the sentence Don needed contains
*"returned"*. Verified with the real banned vocabulary: *"the broker **returned** a FULL page of
510 orders"*, *"read 510 order(s) over 2 page(s)"* and *"**returning** the slot to 0% sells the
book"* all post, while *"the Index **return** was 12.4%"*, *"**alpha**"*, *"**outperformed**"* and
*"**profit**"* are all still blocked. The control held: narrowing the filter did not open it.

**`tradable_names` now takes the percentage, and it does not re-open item 69.** A 0% slot holding
nothing asked for 31 prices; it now asks for none, and a 0% slot that holds asks only for what it
owns. The property item 69 exists for survives: an unpriced **exit** still refuses, at 10% and at
0%, with `missing_exits=['MSFT']` and the refusal naming it as a sell. And this partly closes my
own review-8 non-blocking note — a wind-down is no longer blocked by a quote for a book name the
slot does not own. It is still blocked by an unpriced name it *does* own, which is correct:
§8 says an error never sells.

**Both before-controls reproduce, and I validated their rollback bases rather than trusting
them.** Item 77: **11 of 16** fail pre-fix. Its script rolls back to `89a96a4`, which is *not*
item 77's parent (`dd0bdcb`) — so I compared the three live-path module blobs at both and they are
byte-identical, because item 76 did not touch them. That check is only possible because the script
prints the commit it resolved, which is exactly the hazard its own docstring names. Item 78:
**23 of 30** fail pre-fix, split into behaviour failures and missing symbols so nobody reads an
`AttributeError` as a measured defect, and the six that pass on both each say why they are
controls. The two bases there are identical in all the code under test.

---

## Two findings, neither blocking

### 1. `/admin/live-slots` asserts a falsehood about exactly the state item 77 built

The dashboard, on the slot whose record holds `AAA 5.0, BBB 5.0` with no stated percentage:

```
pct=0.0  pct_stated=False  armed=False
reason: "slot 1 is at 0% and its own record holds nothing, so there is nothing to sell
         and a 0% target licenses no buy."
```

The record holds a full book. `status` calls `armed(n, e, contract_text)` with no `holds=`, which
defaults to the refusing `False`, and `live_slots` deliberately never reads state — so the surface
cannot tell the two 0% states apart. The **refusal is right**; the **reason is false**, and it is
false in the one place Don would look immediately after getting the
`pct_unstated_while_holding` alert, where it reads as a false alarm. `armed` has a correct
unstated-branch reason, but it is reachable only when `holds=True`, which `status` never passes.

That is the eleventh message on this path to assert a property the code has not established, and
the first since item 71 made the two 0% states mean different things. Not blocking: nothing trades
on it, and the alert that matters does fire with the right words.

Related and smaller: `unknown_slot_vars` is raised as a cycle alert but is **not** in the `status`
payload, which carries `retired_variables_set` but not the new report. The door that lists slot
configuration does not list the misspelling it now detects.

### 2. The order-page wall has moved, not gone — and it is weeks away, not years

`MAX_ORDER_PAGES × ORDERS_PAGE_LIMIT` is `20 × 500 = 10,000` orders, and the history is read with
`status="all"`, so it never shrinks. Item 78 reports the re-send pattern and deliberately does not
change it, noting that neither cancel-and-replace nor a PATCH would reduce the count because both
still write a row. From item 78's own measurement — 510 orders accumulated 10-16 to 10-21:

| rate | the 10,000-order cap arrives in |
|---|---|
| the measured ~102/day | **≈ 93 days** (~3 months) |
| 86 names once a day | ≈ 110 days |
| 86 names × 5 cycles (a rebalance week) | **≈ 22 days** |

When it arrives, `reconcile` returns `truncated` and the slot refuses every cycle — the same
failure Don hit on 10-21, one order of magnitude further out, and it will reach the live slot too
once it trades. There is no warning before the wall: the first sign is a refusing slot.

Not blocking, because the failure direction is refusal rather than a wrong trade, and because
three weeks is enough notice. But it is a dated fact and this project's own standard is to date
such things rather than discover them. What I would want: a warning when the read crosses some
fraction of the cap, and a decision on bounding the window (item 78's brief asked about `until`
as well as `after`; only `after` is used).

---

## Carried, and the one residual on C

- `note_no_progress` records `_stamp()` rather than the cycle's `now`, so the ceiling reads the
  wall clock; `HOLDERS` is hard-coded; `orders_window` treats a caller-supplied `now` as ET.
  All three acknowledged by item 77 and not taken; the first changes what every dated record on
  this path means and should not be rushed.
- **C's residual, stated because it will look like drift to anyone watching:** a price move can
  still decide *whether* a top-up fires, because `LIVE_MIN_TOPUP` is a dollar threshold by Don's
  own ruling. At 4 of 5 shares held, the same `buy 1.0` is sent at a mark of 130 and withheld as
  `topup_below_threshold` at 100. The **quantity never changes**, which is the property that
  matters, and item 77 states this limit itself.
- `test_insider_cluster` is red on main (pandas 3 turning a `ValueError` into a `TypeError`). It
  imports only `valuation.studies.*` and touches nothing on this path.

---

## The eight questions

| # | question | ⑤ | ⑥ | ⑦ | ⑧ | **today** |
|---|---|---|---|---|---|---|
| 1 | trades only on the three events | pass | FAIL | pass | **FAIL** | **pass** |
| 2 | per-stock math matches the paper book | pass | pass | pass | pass | **pass** |
| 3 | a paper book cannot reach the live client | pass | pass | pass | pass | **pass** |
| 4 | a lane cannot trigger a live order | pass | pass | pass | pass | **pass** |
| 5 | a bad environment value never yields an order | *unsound* | pass | pass | **FAIL** | **pass** |
| 6 | a restart, retry or dispatch cannot repeat an order | pass | pass | pass | pass | **pass** |
| 7 | **no check is vacuous** | FAIL | FAIL | pass | pass | **pass** ¹ |
| 8 | installing the workflow cannot place an order | pass | pass | pass | pass | **pass** |

¹ I am not stretching question 7 to cover finding 1. The `status` reason is a false **sentence**
attached to a **correct** decision, which is a different fault from a check that cannot fire —
the same line I drew at review 7 and declined to cross at review 8. If it is still there next
time I will count it.

Q5's matrix, which is now the clean one: absent and empty → `stated=False`, not armed; `abc`,
`-5`, `nan`, `100.5`, `inf` → `ok=False`, not armed; a stated `0` → armed **sell-only**; `5` →
armed. Q3: `assert_paper(LIVE)`, `assert_live_host(PAPER)` and the options `assert_paper(LIVE)`
all raise; one `_LiveClient` site, passing no `base`. Q4/Q8: `/admin/live-slots` GET-only,
`/admin/live-cycle` `GET|POST`, and the installed workflow still POSTs `?run=paper` on five crons.

**All eighteen live-path suites: 806 tests, 0 failing.** Both findings pass every one of them.

---

## Six corrections to my own work, and the pattern in them

I got six things wrong in this review before reporting any of them, and every one was caught by
disbelieving a result rather than by reading:

1. My blocker-B chain reported step 5 placing nothing. My day counter had reached **2026-11-07, a
   Saturday**. The code was right.
2. I first reported blocker A's refusal as raising no alert. The alerts are at **cycle** level, not
   slot level; item 77's claim was accurate and I was reading the wrong list.
3. My pager fixture used `fetch(**kw)` where `paged_orders` passes a params **dict positionally**.
4. My recorded session ignored `limit`, so the page cap could not be exercised at all and read as
   passing.
5. I asserted `ok=False` on an incomplete read. The pager returns `ok=True, truncated=True` and
   its own docstring says *"TRUNCATED IS A REFUSAL, NOT A PARTIAL ANSWER … the caller refuses"* —
   I was testing a field in isolation instead of the contract the caller reads.
6. My alert-filter fixtures put *"returned"* in the must-**block** set, which is the very word the
   fix exists to unblock.

Every one of those is **mis-specifying the contract I was testing**, which is the same family as
the defects this path keeps producing — a check measuring the wrong object. I note it because an
auditor whose instrument fails in the same way as the code under review has to say so, and because
four of the six would have produced a *false finding* rather than a missed one.

Item 78's own figures understate its control by one, in its own disfavour: it reports 29 tests, 22
failing, 10 on behaviour; I measure **30, 23 and 11**, with the extra test added after the message
was written.

---

## On the verdict

I passed this path at review 7 and had to withdraw that at review 8, so I want to be explicit
about why I am passing it again and what would make me wrong.

Review 8's three blockers were all about the **boundary between Don's instructions and the
machinery** — what a missing instruction means, what a repeated one means, what one authorises for
how long. I said then that this was a smaller and more checkable surface than the state machine,
and that a table over `(variable present/absent/malformed) × (holds/flat) × (event repeated/new)`
would settle it. Item 77 did substantially that: it added `stated` to the one decision that can
sell, numbered the occurrences, made 0%-while-holding a standing instruction rather than a
one-off, and extended the 6,656-row table — where eight rows legitimately moved from "nothing may
be sent" to "sells only", each a 0% slot holding one name, with the table's own controls
(`resting_opposite` still refuses, `quotes=none` refuses everywhere) unmoved.

What makes me more confident than at review 7 is not the absence of findings — I have two — but
that **both of today's findings are in reporting rather than in deciding**, and that the one place
a decision changed hands (duplicate protection moving from `processed` to the holdings read) was
immediately hardened from the other side by item 78. The two items compose correctly, and I
checked the composition rather than each in isolation.

What would make me wrong, in the order I would bet on it: the order-page wall arriving sooner than
three weeks and being met with a quick relaxation of the `truncated` refusal rather than a bounded
window; a dashboard that keeps telling Don a holding slot holds nothing until he stops believing
it; and the `_stamp()`-versus-`now` item, which is the last place on this path where a dated record
means something other than what it says.

Raising above 0% remains Don's decision and is not gated by this review. On the first real event I
would read four fields in this order: `writes_allowed`, then `plan_outcome`, then `send_outcome`,
then `marks_coverage.missing` — the first says whether the cycle could know anything, the second
what it concluded, the third whether money was the reason it did nothing, and the fourth whether
the free feed could price the book.

---

## What I checked

- Items 77 and 78's commits and full diffs on `live_slots.py`, `live_cycle.py`, `settlement.py`,
  `alert_routing.py` and `app_saas.py`; `DECISIONS.md` 2026-10-18 → 2026-10-21; review 8.
- Item 76's `index_in_force.py` change, to confirm its no-live-trading claim: the additions sit in
  `attach_labels` and the live path calls `attach_returns(book_in_force())`, never `attach_labels`.
- Twenty-one reproductions through `run_cycle` with the real client classes over recorded HTTP:
  blocker A's six environment states plus the flat-slot control and the value-leak probe; blocker
  B's five-step chain twice, three identical repeats and a rolled-back record; blocker C's
  four-price sweep open and closed, with and without cash, plus three consecutive cycles through a
  ±60% swing; both non-blocking items; the 510-order and 501-order-with-a-tie reads; five
  incomplete-read shapes end to end; `tradable_names` at six (pct, holdings) combinations with
  item 69's unpriced-exit property at 10% and 0%; and the alert filter on thirteen strings.
- An environment sweep of every `e.get` on this path: after item 77, no variable's absence
  authorises an action.
- Both before-controls run, their rollback bases validated by comparing module blobs, and the
  trees confirmed restored.
- 806 tests across eighteen suites; the one red suite on main identified and attributed.
- Nothing changed: `git diff --name-only origin/main` lists this file only.
