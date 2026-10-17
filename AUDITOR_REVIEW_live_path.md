# AUDITOR REVIEW — the §8 real-money live path on Alpaca

**Reviewer:** auditor lane · **Date:** 2026-10-15 · **Reviewing:** item 58 (safety core) + item 58b (the caller)
**Tree:** `bd8ea25` · **Suites run:** `test_item58.py` **69 pass / 1 FAIL**, `test_item58b.py` 75 pass,
`test_item58b_doors.py` 22 pass — **166 of 167, and the gate is RED on the installed tree.**
(On the pre-install tree `0966e92` all 167 pass. Installing the workflow turned it red — see
question 8; the failure is a defective guard, not a real credential leak.)

> **WHERE THIS FILE LIVES.** The brief asks for it in the main folder. A lane working in a git
> worktree cannot write there, so it is committed at the repository root and reaches the main
> folder with the next `git merge --ff-only origin/main` — the same route the prompt itself took.

---

## VERDICT: DO NOT ENTER A LIVE KEY YET.

Two things block, and **neither is a weakness in the real-money rails**, which are the strongest
part of this build. The blockers are elsewhere:

1. **The paper proof §8 requires cannot run at all.** `run_slot` transmits by calling
   `client.place_limit(...)`. `AlpacaPaperBroker` **has no `place_limit`** — it has
   `place_equity`. Every paper order raises `AttributeError`, is swallowed into a `broker_error`
   alert, and nothing is sent. The paper slot is the entire mechanism by which this path is
   proven before real money, and it has never placed an order and cannot.
2. **A duplicate buy-in is reachable.** When the slot's own state record is empty — an absent,
   corrupt or unwritten state file — `preflight`'s record-versus-broker check **compares nothing
   and passes**, because it iterates the slot's record. A slot that already holds the full book
   will plan and transmit a second full buy-in. I reproduced this.

Both are fixable without redesign, and neither is in the separation, arming or environment
machinery. §8's structural guarantees I find **sound**, and I say so explicitly below so the
repairs are scoped to what is actually broken rather than to the whole path.

---

## The eight questions

### 1. Does a slot trade only on the three events? — **YES, with one honest qualification**

`live_slots.event_for` reads exactly four things: the book's `formed_on`, the slot's
`last_event_date`, its `last_pct`, and the current `pct`. No return, no price history, no
drawdown, no other date. I enumerated every environment read in both modules — they are exactly
the five documented variables and nothing else. `tests/test_item58b.py:428` walks the AST for a
banned-name set and **carries a positive control** (line 450), so it is not a guard that passes
by seeing nothing.

**The qualification, because the docstrings do not quite say it.** `run_slot` acts on
`ev.act OR remainder`, where `remainder` is `state["open_event"]`. That is a trigger
`event_for` does not know about. It is authorised — §8a's execution mechanics make an unfilled
order re-priced and re-sent "each following cycle until that event's targets are met" — and it
**cannot invent a new target**, only re-plan against the open event's existing one. So the
behaviour is correct and the description "the third of the three events rather than a fourth
thing" is defensible. But it is gated by *state*, not by the book, which matters for question 6.

**A second, smaller overstatement.** `live_slots.py` and `live_cycle.py` both say *"A price is
read to set a limit, never to decide."* Not quite: in `order_plan` the mark sets
`have_val = have_qty × mark`, so it determines the trade **delta and quantity**, not only the
limit. A wrong mark produces a wrong order size.

**Why that is nevertheless safe, and it is a real structural protection worth crediting:** the
same mark sets the limit. A mark that is too low under-states current value *and* prices the buy
limit below the market, so the order does not fill. A mark too high over-states value *and*
prices the sell above the market. **A badly wrong mark produces an unfillable order, not a bad
fill.** Only a slightly wrong mark fills, and then the error is proportionate. The sentence
should be corrected; the behaviour should not.

### 2. Does the per-stock math match the paper book's? — **NO. This is the weakest part and it does not hold.**

The brief told me to treat this sceptically. It does not survive.

**The tolerance is stated.** `PARITY_TOLERANCE = 0.005` (0.5%), compared per name as a share of
each slot's own value, which correctly neutralises the two accounts having different equity.
That part is right.

**The failure direction is NOT "no orders".** In `run_slot`:

```python
if paper_plan is not None:
    out["parity"] = parity(...)
    if not out["parity"]["ok"]:
        out["alerts"].append({"kind": "parity_mismatch", ...})
# ... execution continues and the orders are sent
```

A parity mismatch **alerts and sends anyway.** The brief requires no orders plus an alert, and
§8 as signed requires "dry-run parity logged and diffed against the paper book **before that
slot's first real order**". Neither is enforced in code.

**Worse: parity can be skipped entirely and the slot still sends.** `paper_plan` is `None`
whenever the paper client could not be built or its account could not be read. `run_cycle`
handles that gracefully and continues to the live slots — so a live slot reaches
`if paper_plan is not None:` with `None`, computes **no parity at all**, and proceeds to
transmit. The one cycle where the paper side is down is the cycle with no comparison.

**And the comparison is structurally weak even when it runs.** `parity` diffs **order plans** —
deltas — not target portfolios. Deltas are a function of current holdings, and the paper slot
(100% of the paper account) and a live slot (X% of Don's) will routinely be in different fill
states. Once they diverge, every name mismatches for an entirely legitimate reason. Combined
with a mismatch that does not block, this trains the reader to ignore the one check standing
between a live order and an arithmetic divergence.

**So: would a divergence actually be caught? No — it would be reported, into a channel that will
already be full of false mismatches, and the order would go anyway.**

Three repairs, in order of importance:

- **a mismatch must return before the send**, exactly as a failed preflight does;
- **absent parity must block a live slot's first real order**, not be skipped as `None`;
- **diff target weights, not order deltas** — `targets_map` normalised by `slot_value` is
  holdings-independent and compares the thing the brief actually means ("the live orders
  reproduce the paper book's arithmetic").

### 3. Can a paper book ever reach the live client? — **NO. This holds, and it is well built.**

- `_LiveClient.__init__` calls `assert_live_host`, which requires `https` and exactly
  `api.alpaca.markets`. `AlpacaPaperBroker.__init__` calls `assert_paper`, requiring exactly
  `paper-api.alpaca.markets`. Each refuses the other's host by name.
- **Separate classes, not a flag** — pinned by `test_item58.py:234`, including that neither is a
  subclass of the other.
- **No host can be threaded through from a caller.** The single construction site
  (`live_cycle.py:764`) passes only `(n, key_id, secret)` and never `base`. There is no base-URL
  or host variable anywhere in the live path's environment reads, so there is nothing to
  override.
- **`AlpacaPaperBroker` additionally refuses a paper key that is also configured as a live slot
  credential** (`_clashes_with_a_live_slot`) — a check I did not expect, and it closes the
  reverse direction.
- **The AST import guard was repointed honestly.** At item 58 it asserted `offenders == []`;
  item 58b built a caller, so the free guarantee was spent. It now carries a two-entry allowlist
  (`edge/live_cycle.py`, `saas/app_saas.py`) with a reason each, **in the same commit as the
  change that fired it**, and keeps the absolute half — no `fleet*`, `paper_*`, `options_*`,
  `paper_track.py` or `alpaca_broker.py` may import the live path. That is the right way to
  retire a guard that has been outgrown, and the replacement — counting *constructions* rather
  than imports — is stronger than what it replaced.

### 4. Can a lane trigger a live order? — **NO.**

- **One construction site**, asserted by count across `valuation/`, `scripts/` and `tests/`, and
  asserted to sit inside an `if` whose test names both `armed` and `send`.
- **`config.py` holds the paper keys and not the live ones**, with the reason in a comment.
  Verified: the only `ALPACA` fields in the dataclass are `alpaca_paper_key_id` and
  `alpaca_paper_secret_key`. Nothing holding a config object can obtain a live credential.
- Live keys are read only from `os.environ`, per slot, on demand, inside `live_cycle`.
- Both doors require `_admin_ok()`. A **GET** carrying any run token returns **405** and touches
  nothing — the `/admin/track-row` lesson applied. `send_mode` matches tokens **exactly**, so
  `?run=0`, `?run=no` and `?run=false` are DRY and say so; the earlier
  `bool(request.args.get("run"))` truthiness defect is genuinely fixed.
- `live_client_factory` is a test seam the production door never passes.

### 5. Does a missing or bad environment value ever result in an order? — **NO. Every path fails toward refusal.**

| input | behaviour | correct? |
|---|---|---|
| percentage missing | `0.0`, slot idle, still **discovered** | yes — discovery is by key pair, so a new account is idle rather than invisible |
| percentage non-numeric or out of range | **refuse + alert, not 0** | yes — and the comment says why: reading a typo as 0 would **sell** the book |
| key pair missing | slot not discovered; no client constructed | yes |
| `LIVE_PILOT_ENABLED` anything but exactly `"1"` | pause, nothing sold | yes |
| slot > 1 with no signed authorization row | not armed | yes — **and every unrecognised outcome** (missing file, malformed table, non-YES row) is not-authorized |
| two slots sharing a credential | not armed, clash reported, **credentials never returned** | yes |
| `ALPACA_LIVE_PCT` (retired) | read nowhere; reported as retired if set | yes — no alias is honoured |

The pause-versus-zero distinction is real, opposite in effect, one character apart in an
environment panel, and `status()` states it in words on every read. That is the right call.

### 6. Can a restart, a retry or a manual dispatch repeat an order? — **YES, on one path. The two named defects are genuinely repaired; a third remains.**

**The repair is real, and I checked it rather than the account of it.** `processed` and
`open_event` do different jobs and both are needed: `processed` records seen-and-acted so a
restart does not treat the event as new; `open_event` records not-yet-finished so the next cycle
re-prices the remainder. The unfilled-remainder path now carries the **open event's own key**
rather than `"none"` (`if not ev.get("act"): key = open_key`), and `"none"` is explicitly never
appended to `processed`. An event closes only when `plan["orders"]` is empty — i.e. when the
**reconciled** holdings meet the targets — and that close is recorded before any send precisely
because "met" is a property of holdings and not of whether this cycle transmitted. That is
correct.

**The remaining path, reproduced.** Three facts compose:

- `read_state` returns an **empty** record for an absent or corrupt state file. Its docstring
  defends this: *"A slot that has genuinely bought something is caught anyway by `preflight`,
  which compares this record against the broker's own positions and refuses when they
  disagree."*
- **That claim is false.** `preflight` iterates `slot_record.items()`. An **empty** record yields
  zero iterations and therefore zero problems, however much the broker holds. Measured:

  ```
  slot_record={}            vs broker AAPL=100 -> ok: True   problems: []
  slot_record={AAPL: 50.0}  vs broker AAPL=100 -> ok: False  problems: [record/broker disagree]
  ```

  The check fires on a *wrong* record and is blind to a *missing* one — and missing is the case
  that produces a duplicate buy-in.
- `write_state`'s return value is **discarded** at both call sites in `run_slot`. A failed write
  (unmounted or full Render disk, bad path) produces exactly the empty record above, after the
  orders have already gone.

End to end, with the broker holding the full book and the state file absent:

```
broker_positions_read : 1          (positions readable)
preflight ok          : True       problems: []
ORDERS TRANSMITTED    : [('AAPL', 'buy', 100.0)]   <-- a second full buy-in
```

It also fires with positions unreadable (see question 7). **Fix: `preflight` must refuse when the
broker reports a position the slot's record does not know about**, and `write_state`'s failure
must raise an alert rather than be dropped.

**A second, lower-severity issue on the same function.** `reconcile` calls `client.orders()`,
which defaults to **`limit=100`** on both clients. The Index book is **86 names**. From the
second rebalance onward there are more than 100 orders and Alpaca returns the newest first, so
older fills fall outside the window. Measured on a synthetic two-rebalance history:

```
orders at broker: 172 ; orders reconcile SAW: 100
holding quantities seen: {1.0: 72, 2.0: 14}   (the true value is 2.0 for all 86)
```

72 of 86 names under-counted by half. This one **fails safe** — the record is non-empty, so
`preflight` catches the disagreement and the slot refuses — but it refuses *every cycle
thereafter*, so the slot bricks rather than trades. Paginate, or scope the query to the open
event.

**The sharp sub-question — is the `client_order_id` prefix a sound identity?** Mostly yes, and
for reasons worth recording:

- **Against another slot: safe.** Slot 1's prefix is `"1-"`; slot 11 writes `"11-…"`, whose
  second character is `1`, not `-`, so it does not match. The hyphen does the work.
- **Against the paper slot: safe.** `PAPER_SLOT` is the string `"paper"`, deliberately not a
  number, so it cannot collide with any `ALPACA_ACCOUNT_<n>` slot.
- **Against a manual order: safe in practice, not by construction.** Alpaca auto-generates a
  UUID-shaped `client_order_id` whose second character is a hex digit, never `-`, so a
  hand-placed order will not match. But that is a property of Alpaca's id format, not a
  namespace this code owns. A manual order deliberately tagged `1-anything` **would** be
  absorbed into the slot's holdings and could then be sold by it. **A prefix like `valquo-1-`
  would make it structural rather than fortunate**, and it costs one line.
- **One edge case:** `mine_prefix` is `"%s-" % str(state.get("slot") or "")`. `run_slot` sets
  `st["slot"] = str(slot)` immediately after reading, so it is always populated on that path —
  but a caller invoking `reconcile` with a state dict lacking `slot` gets the prefix `"-"`,
  which matches nothing and silently reconciles an empty book. Worth asserting.

### 7. Is any check vacuous? — **One still is, and it is the one that matters.**

**`preflight`'s positions check is no longer vacuous in the normal path.** `run_slot` reads
`client.positions()`, normalises both shapes, and passes a real list; `None` genuinely travels
on when the list cannot be read rather than being treated as agreement; and
`out["broker_positions_read"]` records which happened. That is a real repair of the first cut.

**But it is vacuous for an empty record**, as shown in question 6 — and that is the exact case
the check exists to catch, because an empty record is what produces a duplicate buy-in rather
than a refusal.

**Should a failure to READ the positions refuse rather than proceed? Yes — and it currently
proceeds.** `preflight` skips the block entirely when `broker_positions is None`, and nothing
downstream consults `out["broker_positions_read"]`. Reproduced with both read paths down and the
broker already holding the position:

```
broker_positions_read : None
reconcile ok          : False  (the broker's orders could not be read)
preflight ok          : True   problems: []
ORDERS TRANSMITTED    : [('AAPL', 'buy', 100.0)]
```

This is the project's own stated rule — an error never trades — not being applied to the one
input that tells the slot what it already owns. **An unreadable position list must be a preflight
failure.** The cost is one skipped cycle; the alternative is a duplicate position.

**Sweeping the other checks for the same shape**, the rest are sound: the book check reads
`ok`/`held`/`formed_on` and fails on each; equity and percentage are range-checked; the marks
check enumerates the names it would actually trade and names the missing ones. The feed-gap
report states `measured: False` rather than reporting zero when nothing is recorded — absent is
not zero, correctly. `holder_authorized` treats every unrecognised outcome as not-authorized.

### 8. Could installing the scheduled workflow place an order? — **No live order. But the brief's description of the file is out of date, and the file is now installed.**

**Two corrections to the brief, both found by reading rather than by taking the description.**

**First: it does not ship with "no `?run=1`" — it ships with `?run=paper`** (amended by item 2b),
and `?run=paper` **transmits**: the paper slot sends on the Alpaca paper client at 100% of the
paper account. The brief's sentence *"it computes … and transmits nothing"* is wrong. The file's
own header says so plainly; the brief predates the amendment.

**Second: it is no longer pending. It is installed.** At the tree the brief was written against
it sat only in `pending_workflows/`; at `bd8ea25` ("Install workflow(s): live-cycle.yml") it is
also at `.github/workflows/live-cycle.yml`, and I verified the two copies are **byte-identical**.
Don installed it before this review landed, exactly as the brief predicted he would.

So, precisely:

- **It cannot place a real-money order as installed.** `send_mode("paper")` → `PAPER`;
  `live_sends = (mode == LIVE)` is `False`; the live-client construction sits behind
  `if a["armed"] and live_sends:`. **No live client is constructed even for a fully armed slot.**
  The §8 property the brief cares about holds, and installing it was not the decision to go live.
- **It is not a dry run.** It is a paper-sending run, deliberately — the first version *was*
  fully dry, and the header records that this was wrong, because the paper slot would then never
  have placed a paper order and Don could not watch the rebalance go through.
- **Turning it on is the single visible edit the header claims** — `run=paper` → `run=1` — and
  that edit is necessary but **not sufficient**: a live order additionally needs
  `LIVE_PILOT_ENABLED=1`, a percentage above 0, a key pair, and (for slots above 1) a signed
  authorization row. Four more conditions, none of them in this file. That is the right
  arrangement and it runs in the safe direction.
- **Caveat, given blocking finding 1:** `?run=paper` currently transmits *nothing*, because
  `place_limit` does not exist on the paper client. The workflow is installed, scheduled, and
  its whole purpose is unmet until that is fixed. It will run at 14:40 UTC on the next weekday
  and post a page of `AttributeError` rejections.

**AND INSTALLING IT TURNED THE §8 GATE RED — the substring-ban family, again.**
`test_item58.py::test_no_workflow_carries_an_alpaca_credential` walks `.github/workflows/` and
fails `if "ALPACA" in body.upper()`. It now fires on `live-cycle.yml`. **No credential is
present:** the only secrets the file references are `SITE_BASE_URL` and `ADMIN_TOKEN`, which is
exactly the architecture §8 wants. The two matches are **prose in comments** — *"the Alpaca
PAPER client"* and *"Alpaca permits no other time_in_force"*. A guard tripped by a comment
documenting the very rule it enforces.

This repository has paid for that lesson repeatedly, and **the fix is already present two tests
earlier in the same file**: `test_no_paper_book_imports_the_live_module` carries a docstring
explaining that it reads the **AST** precisely because its first cut grepped a substring and
flagged `config.py`'s comment. The workflow guard did not get the same treatment. It should
match a credential's *shape* — `secrets.ALPACA…`, or an `env:` key beginning `ALPACA_` — rather
than the vendor's name anywhere in the file.

Two things follow, and the second matters more than the first:

- **The gate is red on `main` right now.** Whoever installed the workflow either did not run this
  suite or has not noticed. The red is a false positive, but a false positive on the one suite
  guarding the live path is the kind that gets suppressed rather than fixed.
- **It is red for a reason that is good news.** The check is asking the right question — no live
  key on GitHub — and the answer is genuinely *no*. Fix the guard; do not weaken the rule.

**On the tracked location:** `pending_workflows/live-cycle.yml` **is tracked** (confirmed via
`git ls-files`), and the reasoning is right. A file that POSTs an admin door on a schedule is
precisely where an unnoticed `?run=1` would live, and the old gitignored
`data/pending_workflows/` route made that unreviewable and unpinnable. Keep it tracked. I would
add one thing: **a test that reads both copies and asserts the token is not `1`**, so the review
gate is enforced by CI rather than by the reviewer's attention — and now that an installed copy
exists, the test should cover the installed path too, or the two can drift.

---

## The blocking defect, in full

`run_slot` is one runner for both clients — the right design, and the explicit point of item 58b
step 3. But the two clients do not implement the same interface at the one line that transmits:

| | `place_limit` | `place_equity` |
|---|---|---|
| `live_slots._LiveClient` | **yes** | no |
| `alpaca_broker.AlpacaPaperBroker` | **no** | yes |

`live_cycle.py:457` calls `client.place_limit(...)`. Run against the real paper broker's
interface:

```
orders planned : 2
orders accepted: 0
acted flag     : True
ALERT: broker_error - order for AAPL was rejected: AttributeError: 'AlpacaPaperBroker'
                      object has no attribute 'place_limit'
processed      : ['rebalance:2026-10-22']
open_event     : rebalance:2026-10-22
holdings       : {}
```

Three consequences:

1. **The paper slot has never placed an order and cannot.** §8's premise — prove the path with
   real paper orders before real money — is unmet, and the installed workflow cannot meet it.
2. **The failure is loud once, then silent.** `broker_error` is an `EVENT_KIND` in
   `live_notify`, deduped on `(kind, slot, event, reason[:120])`. Because holdings never advance,
   the next cycle produces an identical plan and an identical reason, so it is suppressed. Don
   gets one page of rejections and nothing thereafter.
3. **The asymmetry runs the wrong way.** The *live* client implements the method; the *paper*
   client does not. So the only client that would work through this line is the one spending real
   money, and the docstring claim that paper and live "run the same function" is true of the
   function and false at the call it makes.

**Why 167 tests miss it:** every suite uses a `Stub` that *defines* `place_limit`
(`test_item58b.py:74`). The suite is alert to client divergence — `LiveShaped` exists precisely
to pin that the two clients' *reply shapes* differ — but it models the reply shape and not the
method name. **No test ever hands `run_slot` an object carrying the real paper broker's
interface.** That is the gap to close along with the fix: a test asserting that every method
`run_slot` calls exists on **both real client classes**.

The fix is small — add `place_limit` to `AlpacaPaperBroker` delegating to `place_equity`, or have
`run_slot` resolve one name — but **do not widen the call site with a `getattr` fallback**: that
reintroduces the silent-divergence class. One named method on both clients, pinned by a test.

---

## The three open facts — my view on each

### 1. Is the host check sufficient on its own? — **Yes, and it should not be the only thing recorded.**

`GET /v2/account` genuinely carries no `is_paper`, no `account_type` and no environment field; I
accept the finding. The host therefore carries the guarantee, and **it is strong enough to carry
it**, for a reason stronger than the check itself: there is **no path by which a caller can
supply a host.** `_LiveClient` defaults `base` to `LIVE_BASE` and the one construction site never
passes it; no environment variable anywhere in the live path names a host or base URL; `_request`
rebuilds every path from the validated `self.base`. The guarantee is not "we check the host" but
"the host is a module constant with no override", which is a different and better property.
Keeping the account-number prefix as corroboration only is right — the brief forbade relying on
`PALPACA_`, and a prefix in a docs example is not an API contract.

**One cheap strengthening I would take, and it is not a host check.** The real residual risk is
not the host — it is **the wrong keys behind the right host**: paper credentials pasted into
`ALPACA_ACCOUNT_1_*`, or slot 2's keys into slot 1. Alpaca will authenticate those happily
against whichever host the key belongs to, and the host check cannot see it. So:

- on a slot's first armed cycle, **record the account id** returned by `/v2/account` into the
  slot's state, and **refuse on any later cycle if it changes**. A swapped key pair then becomes
  a refusal instead of a slot trading a different account under slot 1's record;
- assert the live account id is **not** the paper account's id.

Both are reads, both fail toward refusal, and together they close the one gap the host check
structurally cannot cover.

### 2. IRA fractional shares and settlement — **the handling is right; watch the first rebalance; add a retry ceiling.**

Treating a buying-power rejection as a broker error → no orders for that slot that cycle → alert
→ retry next cycle is the correct design, and it is the only one available: Alpaca does not
document whether fractional shares work in an IRA, nor what settlement means for a sell-then-buy
rebalance, and **assuming either way would be inventing a fact.** The re-send-next-cycle
behaviour resolves a settlement delay naturally, which is the right shape for an unknown of this
kind.

**Yes, Don's first real rebalance should be watched for this specifically** — a rebalance is the
only event that sells and buys in the same cycle, so it is the only one that can hit unsettled
cash, and the first one is the cheapest chance to observe it.

**One gap to close first: the retry loop has no ceiling.** A permanently-rejecting condition — an
IRA that simply cannot hold fractional shares, say — retries every cycle forever, and after the
first announcement `live_notify` dedupes it into silence. Add an attempt count per event and
escalate after a small number. A slot failing the same way every day for a month without saying
so is a failure mode this project has already paid for.

**A measurement worth taking before the first real rebalance, on paper, for free:** once
`place_limit` is fixed, run the paper slot through one full rebalance and count how many names
fill. That is the cheapest available evidence about both fractional support and the mid-limit
fill rate, and it costs one cycle.

### 3. The feed-gap pair — **an honest substitute, and it should be reported as not-measured in the costly direction.**

The censoring argument is correct and correctly stated in the code: every order is a limit at the
mid, a limit never fills worse than its limit, so the measured price gap **can only read
favourable or zero**. `feed_gap_report` says so in its own `censoring` block rather than hiding
it, which is the right behaviour and deserves saying.

**Is the unfilled count an honest companion? Yes, and it is genuinely uncensored** — an order
resting at the free feed's mid that expires is that mid not being a traded price, which is the
same question asked where the limit cannot hide the answer.

**But the pair is not yet a measurement, for a reason the code does not state:** `n_unfilled` is
a **monotone counter with no denominator**. "Fourteen unfilled" means nothing without the number
of orders placed. Record attempts alongside it so the figure is a **rate**; then the pair is
informative.

**My ruling on the framing:** report the price gap as **measured but one-sided by construction**,
and report the underlying question — *is the free IEX feed wrong in the costly direction* — as
**NOT MEASURED**, with the unfill rate as the uncensored evidence bearing on it. That is stronger
than either "measured" or "not measured" alone, and it matches how this project has handled
censored measurements before.

**And nothing on this path should place a market order to close the gap.** The information is not
worth a market order on real money in an account with no loss stops, and the unfill rate answers
the decision-relevant half — whether orders at the mid actually execute — without one.

---

## What I would require before a live key goes in

**Blocking:**

1. `place_limit` exists on both clients, with a test asserting the interface `run_slot` requires
   is satisfied by **both real client classes** (not by a stub).
2. `preflight` refuses when the broker reports a position the slot's record does not know about —
   closing the empty-record hole.
3. `preflight` refuses when the broker's positions **cannot be read**, rather than skipping.
4. A parity mismatch **returns before the send**, and an **absent** parity blocks a live slot's
   first real order.
5. The paper slot completes **one full rebalance on paper**, with the fills inspected. That is
   §8's own precondition and it has never been met.
6. **The §8 gate is green again.** `test_no_workflow_carries_an_alpaca_credential` is currently
   failing on the installed workflow over a comment. Repoint it at a credential's shape, not the
   vendor's name. A red gate on the live path is not a state in which to enter a key, even when
   the red is a false positive — especially then.

**Strongly recommended, not blocking:**

7. `write_state` failure raises an alert instead of being discarded.
8. `reconcile` paginates `client.orders()` or scopes it to the open event — 86 names exceeds the
   100-order default from the second rebalance on.
9. `client_order_id` gets an owned namespace (`valquo-<slot>-…`).
10. Record and pin the live account id per slot; assert it is not the paper account's.
11. An attempt ceiling per event, so a permanently-rejecting condition escalates rather than
    retrying into a deduped silence.
12. A CI test asserting neither copy of `live-cycle.yml` carries `run=1`, now that an installed
    copy exists alongside the pending one and the two can drift.
13. Correct the two docstring overstatements: the mark sets the order size as well as the limit,
    and `read_state`'s defence of the empty-record default is currently false.
14. Normalise the unfilled count into a rate.

**Once 1–6 are done, I have no objection to slot 1's keys going in at 0%.** The separation,
arming and environment discipline are genuinely strong — stronger than most of what I have
reviewed in this repository — and the two refusals in `LIVE_PILOT_BLOCKED.md` were right to hold
out for fractional shares. What is missing is not a rail. It is the proof that the rails carry a
train, plus two holes in the record-keeping that a cautious reading of the docstrings would have
said were already closed.

---

## What I checked, so a later reader can disbelieve me efficiently

- **Read in full:** `valuation/edge/live_slots.py` (528), `valuation/edge/live_cycle.py` (863),
  `valuation/edge/live_notify.py` (189), `pending_workflows/live-cycle.yml` (108); the two doors
  in `valuation/saas/app_saas.py` (1309–1437); `alpaca_broker.py`'s interface and host handling;
  `PAPER_TRACK_CONTRACT.md` §8 and §8a; the 2026-10-14/15 `DECISIONS.md` entries.
- **Ran all three suites on the installed tree `bd8ea25`: 166 pass, 1 fail** — the fail being
  the defective workflow guard in question 8. **Every other defect above survives all 167**,
  which is the point: they are not caught by the suite in either tree. On the pre-install tree
  `0966e92` the same three suites are 167 green, and the live-path source files are
  byte-identical between the two (verified by `diff`), so nothing in this review turns on which
  tree it was read in.
- **Reproduced, with scripts, against the real classes:** the `place_limit` gap end to end; the
  empty-record preflight hole; the duplicate buy-in with positions readable *and* unreadable; the
  100-order reconcile window on an 86-name book.
- **Verified by grep/AST:** one `_LiveClient` construction site; every environment read in the
  live path; no host or base variable anywhere; `config.py` carries paper keys only;
  `live-cycle.yml` tracked, **and installed** at `bd8ea25`, byte-identical to the pending copy and
  still `?run=paper`.
- **Not checked:** anything against a live or paper Alpaca account. No network call was made and
  no credential was read. Every finding is from source and from local reproduction.
