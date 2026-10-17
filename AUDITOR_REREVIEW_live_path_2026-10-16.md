# AUDITOR RE-REVIEW — the §8 live path after item 63

# NOT YET.

**One blocker remains, and it is blocker 2 reached by a different route.** Nine of the eleven
things item 63 claims are genuinely closed, and I verified each by reproduction rather than from
the commit message. The residual is narrow, reproducible, and about one `if`.

**Reviewer:** auditor lane · **Date:** 2026-10-16 · **Reviewing:** item 63 (`2344529`, `502dc94`)
**Tree:** `worktree-auditor-live-path-review` at `origin/main` + this file
**Suites:** `test_item63` 66, `test_item58` 71, `test_item58b` 77, `test_item58b_doors` 22 —
**236 of 236 green.** The residual below passes all 236.

Companion to `AUDITOR_REVIEW_live_path.md` (2026-10-15), which is left unedited as the record of
what was true then.

---

## The one remaining blocker

**A duplicate full buy-in is still reachable: state record lost + `/v2/orders` unreadable +
`/v2/positions` readable.**

Item 63 closed the empty-record hole by making `preflight` compare **both** directions, and
scoped the reverse direction with `slot_symbols` so it cannot refuse on Don's own unrelated
holdings. Both of those are right, and I confirmed the scope behaves correctly in both
directions. But `slot_symbols` is itself derived, at `live_cycle.py:578`:

```python
slot_symbols = sorted(set(rec.get("symbols") or [])
                      | {str(t).upper() for t in (st.get("holdings") or {})}
                      | {str(o.get("ticker") or "").upper()
                         for o in ((st.get("intent") or {}).get("orders") or [])})
```

All three sources are empty at once when the state file is gone **and** `reconcile` failed. The
reverse check then runs with an empty scope, and its first line is
`if tkr in mine_names or tkr not in scope: continue` — so every broker position is skipped and
nothing is flagged. Reproduced, with parity satisfied exactly as `run_cycle` supplies it:

```
B. orders UNREADABLE, state lost, positions READABLE
   slot_symbols : []
   preflight    : ok=True  problems=[]
   parity       : True
   ORDERS SENT  : [('AAPL', 'buy', 100.0)]      <-- on top of the 100 the broker reports
   reason       : sent 1 order(s) for rebalance:2026-10-22
```

The same setup with `/v2/orders` readable refuses correctly (`reconcile` recovers the holdings
and the targets are already met). So the fix works wherever the scope can be derived, and the
gap is exactly where it cannot.

**Why the 236 tests pass through it.** `test_an_EMPTY_record_against_a_holding_broker_REFUSES`
passes `slot_symbols=["AAPL"]` **explicitly**, so it proves `preflight` refuses *given* a scope.
`test_END_TO_END_the_second_full_buy_in_does_not_transmit` supplies readable
`valquo-paper-`-prefixed orders, so `reconcile` succeeds and it refuses by the
targets-already-met path. **Neither exercises a failed `reconcile`**, which is the only state in
which the scope is empty. This is the same shape as the original blocker: the unit test supplies
by hand the thing the production path derives.

**Why both legs are realistic rather than contrived.** `data/` is gitignored and lives on
Render's disk; item 62 established that `valquo_track.json` has never shipped with any deploy, so
an empty `data/live_slots/` after a redeploy or disk reprovision is a demonstrated state in this
project, not a hypothetical. And one endpoint 5xx-ing or rate-limiting while another succeeds is
ordinary.

**The fix is one `if`, and the code already contains the pattern three lines away.** A
*truncated* order page is already a refusal:

```python
if rec.get("truncated"):
    ...
    return out
if rec.get("ok"):
    st["holdings"] = rec["holdings"]
```

There is no `else`. **Truncated and failed are the same epistemic state — "I do not know what I
hold" — and only one of them refuses.** Making a failed `reconcile` a refusal closes this, is
consistent with the module's own logic, and costs a skipped cycle. (Widening the scope to include
the book's held names would also work: a broker position in a name the slot is about to buy, with
no record explaining it, is precisely the ambiguity that must refuse. The refusal is the smaller
change.)

That is the whole of what stands between this and a key.

---

## The six questions

### 1. Blocker 1 — **CLOSED.**

**`run_slot` places an order through the real paper broker.** I drove the actual
`AlpacaPaperBroker` class with only its HTTP layer stubbed, so `place_equity`'s own validation
ran:

```
orders planned : 2     orders accepted: 2     broker_errors: []
body: {'symbol':'AAPL','side':'buy','qty':'500','limit_price':'10.00',
       'type':'limit','time_in_force':'day',
       'client_order_id':'valquo-paper-rebalance:2026-10-22-AAPL'}
```

`place_limit` is a true **delegation** to `place_equity`, not a copy, so the limit-only,
positive-quantity and fractional-`time_in_force` rules apply unchanged — and a mutation that makes
it reimplement instead goes red. Choosing a second name over renaming `place_equity` is right:
`place_equity` is the paper books' shipped interface.

**Would the derived test catch the next divergence? Mostly yes — I mutation-tested it.** The rule
is two-part (an unguarded call must exist on both clients; a method missing from either must be
`hasattr`-guarded at every site), derived from `live_cycle`'s own AST, and it carries a positive
control asserting `place_limit` is in the derived set. Five of six mutations caught:

| mutation | caught |
|---|---|
| paper broker loses `place_limit` (blocker 1 itself) | **RED** |
| a new **unguarded** `client.brand_new_method()` call | **RED** |
| `_LiveClient` grows a `quotes` method | **RED** |
| `place_limit` reimplements instead of delegating | **RED** |
| unguarded call + a **comment** containing its `hasattr` text | survived |
| call through a holder name not in `HOLDERS` (e.g. `broker`) | survived |

Sources restored byte-for-byte; baseline green before and after.

The two survivors are **latent derivation gaps, not live defects** — I censused every attribute
call in `live_cycle` and today every client-shaped call goes through `client` or `pc`, both in
`HOLDERS`. Worth noting rather than fixing now: `guarded` is detected by a **substring** match on
`hasattr(client, "x")`, which is the family this repository has hit seven times. Its failure
direction is mostly safe (single quotes would misclassify as *required* and go red), but a comment
carrying that text makes an unguarded call read as guarded. `HOLDERS` is also a hand-typed list —
the defect the derivation exists to avoid, one level further up.

**The `_LiveClient` has-no-`quotes` handling is correct and is the right call.** The asymmetry is
real and must stay: Alpaca's market data is on `data.alpaca.markets` and `_LiveClient` is pinned
to exactly `api.alpaca.markets`, which is the single-host guarantee I credited as its strongest
property. `run_cycle` guards the call with `hasattr` and prices live slots from the paper client;
`_marks_for` now distinguishes "cannot quote" from "quoted nothing", and re-raises an
`AttributeError` from inside a real `quotes` instead of flattening it into a missing price. That
was a misattribution I did not name and item 63 found by applying its own new rule — credit where
it is due.

### 2. Blocker 2 — **NOT CLOSED.** Narrowed correctly; one route remains.

What *is* closed, each reproduced:

| my original case | now |
|---|---|
| empty record, broker holds, orders readable | **refuses** (reconcile recovers; targets met) |
| positions unreadable | **refuses** — "cannot know what it already holds" |
| positions **and** orders unreadable | **refuses** on the position list |
| failed state write | **refuses before transmitting** — the intent is written first |

**The scope is correct in both directions**, which the prompt asks specifically. It does **not**
refuse on Don's unrelated holdings — broker holding 500 TSLA that the slot never ordered gives
`ok: True, problems: []`, which is right, because refusing there would brick a healthy account.
And it does **not** miss the slot's own positions whenever the scope can be derived from fills,
recorded holdings, or recorded intent.

**The intent-before-send inversion is the strongest single change in item 63.** Writing the
intended orders first and refusing on an unwritable disk means a failed write can no longer
produce the empty record *after* the orders have gone. It converts the worst ordering into the
safe one.

The residual is the empty-scope case above.

### 3. Question 2 (parity) — **CLOSED, all four parts.**

- **Blocks on mismatch.** A live slot returns before the send; the alert is kept.
- **Blocks on absence.** `parity_absent` is a refusal with `measured: False` — "absent is not a
  pass", which is the `C5` rule applied correctly. I hit this repeatedly in my own harness, which
  is how I know it fires.
- **Diffs target weights**, not order deltas, normalised per slot by its own value. This is the
  repair that matters: a delta depends on current holdings, so two slots in different fill states
  mismatched on every name for a legitimate reason, and a check that cries wolf on healthy cycles
  is one nobody reads on the unhealthy one.
- **Cannot brick a live slot that arms after the paper slot closes an event.** `paper_targets`
  comes from `LS.targets(PAPER_PCT, eq, held)`, computed **before** and **independently of**
  `run_slot(PAPER_SLOT, …)` and of the paper slot's event state. So paper closing its event on day
  1 leaves the comparison available on day 2. Had the blocking rule been built on the paper slot's
  *plan*, it would have been a permanent brick — item 63 saw that and avoided it.

**Both exemptions are correctly placed:** the paper slot is exempt from parity blocking, because
gating it would stop the mechanism that produces the comparison.

### 4. Question 7 — **CLOSED.**

`broker_positions=None` is a refusal. The sentinel is the thing that makes it safe, and it is
real:

```
argument omitted -> ok=True   positions_checked=False   (no broker consulted)
None             -> ok=False  positions_checked=False   ("could not be read ... sends nothing")
```

"No broker was consulted" and "the broker would not answer" are different facts and `None` cannot
carry both. Item 63 records building the sentinel and then throwing it away at the call site, with
item 58b's own positive control catching it — the kind of self-report that makes the rest of the
account more credible, not less.

### 5. The new pieces — **none of them can send an order a broken input should have stopped.**

| piece | verified | can it cause a send? |
|---|---|---|
| **account-id pin** | recorded on first armed cycle, refuses on change; a live id equal to the paper id refuses | no — refusal only |
| **5-cycle retry ceiling** | stops and escalates at 5; sits **after** preflight, so a transient data outage cannot burn the budget | no |
| **`valquo-<slot>-` namespace** | one definition shared by writer (`client_order_id`) and reader (`coid_prefix`) | no |
| **full-page refusal** | `ORDERS_PAGE_LIMIT = 500`; a full page sets `truncated` and refuses | no |

Three notes, none blocking:

- **The retry ceiling's placement is a real piece of care.** Had it incremented before preflight,
  five days of a thin IEX feed would have permanently exhausted a healthy event's budget.
- **The namespace migration is free only while no fill exists under the old `"<slot>-"` prefix.**
  Verified mechanically: an order tagged `1-rebalance:…` now reconciles to `n_orders=0,
  holdings={}`. It is genuinely free today — the first real cycle refused on prices and reported
  `broker_positions_read: 0`, so nothing was ever placed. **That window closes with the first
  fill**, and any later change to the prefix is a migration rather than an edit.
- **The account-id pin silently does not engage if the broker returns no `id`.** `if acct_id:`
  skips the whole block. It cannot cause a send on its own (an unreadable account also costs the
  equity, which preflight refuses on), but a 200 carrying an equity and no id would leave the slot
  unpinned with nothing saying so. Reporting `account_id_recorded: false` for live slots, as is
  already done for paper, would close it.

**A dated future issue, not a blocker:** the 500-order page refuses rather than paginating, which
item 63 declares as not-done. At 86 names and four rebalances a year that page fills in roughly 18
months, after which the slot refuses every cycle until real cursor pagination exists. It fails
safe; it should be fixed before mid-2028 rather than discovered then.

### 6. My eight original questions, as of today

| # | question | 2026-10-15 | **today** |
|---|---|---|---|
| 1 | trades only on the three events | pass (with two docstring overstatements) | **pass** — both overstatements corrected |
| 2 | per-stock math matches the paper book | **FAIL** | **pass** — blocks on mismatch and absence, diffs targets |
| 3 | a paper book cannot reach the live client | pass | **pass** — unchanged, and `_LiveClient` still has no `quotes` |
| 4 | a lane cannot trigger a live order | pass | **pass** — one construction site, still behind armed-and-send |
| 5 | a bad environment value never yields an order | pass | **pass** |
| 6 | a restart, retry or dispatch cannot repeat an order | **FAIL** | **FAIL** — narrowed to one route (empty scope) |
| 7 | no check is vacuous | **FAIL** | **pass** — unreadable positions refuse; the sentinel is real |
| 8 | installing the workflow cannot place an order | pass, with two corrections to the brief | **pass** — still `?run=paper`; the credential guard red I reported is fixed by item 62 |

**Seven of eight pass. Question 6 is the one that does not, and it is the verdict.**

---

## What I would require

**Blocking — one item:**

1. **A failed `reconcile` must refuse**, as a truncated one already does. Equivalently, include
   the book's held names in `slot_symbols`. Plus a test that exercises the **derivation** — a
   failed `/v2/orders` with a readable `/v2/positions` and no state file — rather than supplying
   `slot_symbols` by hand.

**Recommended, not blocking:**

2. Report `account_id_recorded` for live slots, so a broker reply with no `id` is visible rather
   than silently unpinned.
3. Tighten the derived guard's `guarded` detection to read tokenized code rather than a substring,
   and derive `HOLDERS` (or assert that no attribute call on any other local name resolves to a
   client) — the two mutations that survived.
4. Real cursor pagination of `orders()` before the 500-order page fills, ~mid-2028.

**On the one blocker: entering keys at 0% sends nothing, and I considered whether that makes this
a pass.** It does not, and the reason is the honest one rather than the cautious one: a slot at 0%
never reaches the code in question, so keys at 0% are genuinely safe — but the only thing between
0% and the duplicate is Don typing a percentage, and that is the step this review exists to be
finished before. The fix is one `if` and a test. I would rather name it now than have the next
review be about a double position in a real account.

Everything else item 63 claims, it did. The two blockers I reported were real, both were taken
seriously, and the fixes are better than the minimum — the intent-before-send inversion, the
target-weight parity, the sentinel, and a derived interface test that catches four of the four
divergences that matter are all stronger than what I asked for. One route through one derived set
was missed.

---

## What I checked

- **Reproduced against the real classes**, not fixtures: `run_slot` placing orders through the
  actual `AlpacaPaperBroker` with its HTTP layer stubbed; all four of my original duplicate-buy-in
  cases; the empty-scope case with parity satisfied as `run_cycle` supplies it; the
  Don's-unrelated-holdings control; the sentinel's two states; the no-slot-number refusal; the
  full-page refusal; the old-prefix invisibility.
- **Mutation-tested the derived interface guard** — six mutations, five caught, sources restored
  byte-for-byte and the baseline green before and after.
- **Censused** every attribute call in `live_cycle` against the `HOLDERS` list.
- **Read** the diffs of `live_slots.py`, `live_cycle.py` and `alpaca_broker.py`, item 63's 66
  tests, and both commit messages — the messages last, and against the code rather than for it.
- **Ran** all four suites: 236 green. The residual blocker passes every one of them, which is the
  point.
- **Not checked:** anything against a live or paper Alpaca account. No network call, no credential
  read. The service-side evidence in `502dc94` (paper keys authenticate, the book is readable,
  `broker_positions_read: 0`, the refusal on 26 unpriced names) I take as reported and did not
  independently verify; it is consistent with everything I could check locally.
