# PREREG — MA36 + MA37: the live options record is censored at one end and blended at the other

**Lane:** options-bot. **Date:** 2026-08-14. **Register committed ALONE** (one `.md`, zero
`.py`), before any repair exists, and it is a strict git ancestor of every commit that changes
behaviour. **Items:** `MA36` and `MA37` of `VALQUO_MASTER_AUDIT_ULTIMATE.md` §3, both HIGH,
both filed under "record integrity".

**ADOPTS NOTHING AND TESTS NOTHING.** These are correctness repairs, not hypotheses. There is no
arm, no threshold and no verdict. **Trial cost ZERO**, logged `FIXED`, on the `PT-BUG12`
precedent (the previous paper-track repair, also registered first, also zero trials).

**SO WHY A REGISTER AT ALL, WHEN NOTHING IS BEING TESTED?** Because both repairs **move a number
the product publishes** — the live options expectancy — and one of them requires me to choose
*which era of the record users see*. Choosing an era after seeing which era flatters the number
is exactly the degree of freedom this project registers away. Everything below that could be
chosen is chosen **here**, before the repair exists and before any post-fix number is read.

---

## 0. Priors, and the two frames this deliberately does NOT inherit

* **`B5-lesser` is the direct parent of MA36 and it was RIGHT.** It stopped `paper_track` sending
  a market order when there was no bid, because a market fill is outside the ask-in / bid-out
  convention every validated options number in this repo is net of. **That repair is not being
  reversed.** MA36 is that repair stopping one line short: refusing an unmodelled *fill* is
  correct, and refusing to *settle a contract that no longer exists* is not the same act.
* **`PT-BUG12` (session 16) is the procedural parent.** It found the forward book running exit
  levels no backtest describes, and its lesson is quoted here because it applies verbatim: *"the
  repair runs in the flattering direction and that must travel with it."* MA36's runs the **other**
  way (see §5), which is the easier case — but the discipline is the same.
* **NOT INHERITED: the `R2` dead-entry frame.** R2 is about whether the alert picks a good *day*.
  Nothing here touches entry selection, and no number below is evidence for or against R2.
* **NOT INHERITED: `O11`'s survivability frame.** O11 says per-trade expectancy means nothing
  until it survives realistic sizing. True, and **irrelevant here**: this register does not claim
  the live book is good, it claims the live book is *mis-recorded*. Fixing a censored record is
  not a claim about the strategy.

## 1. Premise findings — measured before the design below was written

Each re-measured by me on the current tree, not quoted from the audit.

1. **`grep -c intrinsic valuation/edge/paper_track.py` → 0.** No path in the forward track
   settles an expired position at intrinsic, by any spelling.
2. **`_exit_decision` (`:563-565`) returns `"expiry"` forever once `(expiry - today).days <=
   CLOSE_BEFORE_EXPIRY_DAYS`**, and that condition never stops being true. So a past-expiry row
   is re-decided every cycle, and every cycle it takes the no-bid `continue` at `:619-625`.
3. **`_stats` and `paper_report` count `status='closed'` only.** A stranded row is neither a
   winner nor a loser; it is **absent**. Winners and quoted losers are scored; total losses are
   dropped. That is the censoring, and it is one-sided.
4. **`record_epoch` is WRITTEN AND NEVER READ AS A FILTER outside one module.** It appears
   **17** times in `scream_log.py`, **2** times in `options_tracker.py` (the `_FIELDS` entry and
   the stamp at `:96`), and **0** times in `options_paper.py`. `scorecard` runs
   `SELECT * FROM option_alerts WHERE status='closed'` with no epoch clause; `tuning_candidates`
   calls `scorecard`; `paper_report` takes `min(alert_ts)` over **every** row.
5. **`record_outcome` accepts a zero exit premium and produces exactly −100%.** Its guard is
   `ex = _f(exit_premium); if ex is None` — `0.0` passes — and `pnl_pct = ex/entry - 1.0` is
   `-1.0` exactly. So settling at zero needs no new arithmetic and cannot silently no-op.
6. **A date-keyed historical underlying close is NOT available through the shipped provider
   interface.** `TradierProvider.get_bars` returns `close/high/low/volume` lists and **drops the
   dates**, so there is no way to ask it for "the close on the expiry date" without inventing a
   calendar alignment. This is the fact that decides §2's settlement basis, and it is recorded
   here rather than discovered later.

## 2. MA36 — the settlement rule, fixed before it is written

A position is settled by this rule **only** when all four hold:

* its state is `open`; and
* `_exit_decision` returns `"expiry"`; and
* there is no bid (`not (bid and bid > 0)`) — the existing B5-lesser condition, unchanged; and
* **`today > expiry`, STRICTLY.** Not `>=`, and never inside `CLOSE_BEFORE_EXPIRY_DAYS`. A no-bid
  position *before* expiry still holds time value and settling it at intrinsic would book a loss
  the market never charged. The B5-lesser defer is the correct behaviour there and is preserved.

Then, and only then, the contract's own `opt_right` and `strike` are read **from the alert row**
(`_alert_row`, the same route `_policy_for` already uses — the OCC string is not re-parsed, so
there is no second implementation of a field the store already holds), and:

* **`expiry_settled_worthless`** — the contract is out of the money on the underlying's current
  quote (call: `u <= strike`; put: `u >= strike`). **Settle at exactly `0.0`**, through the
  existing `_record` → `record_outcome` path, with a reason naming the basis. The row closes and
  posts **−100%**, which is precisely what `options_backtest.py:29` says the backtest does with
  the same event: *"expire worthless settle at intrinsic and post −100%. They are not dropped."*
* **`settlement_blocked`** — the underlying quote is unavailable, **or** the contract looks
  in-the-money on it. **Nothing is settled, nothing is scored**, and the row is reported by name
  in the returned dict with its reason. A human decides.

**WHY ZERO AND NEVER A RECONSTRUCTED INTRINSIC — this is the load-bearing choice.** Computing a
non-zero intrinsic requires the underlying **at expiry**, which premise 6 says this tree cannot
supply. Using *today's* underlying instead would book a fake gain on a dead call whenever the
stock rallied after expiry — the settlement trap `V6-OPT` caught in the backtest, in a new
costume, **and its error runs in the flattering direction.** Zero is the conservative bound for a
long option, it is the value the market itself is quoting by declining to bid, and it is the
backtest's own convention. **The ITM guard is what stops zero being applied blindly:** the only
thing it can ever do is *prevent* an automatic −100%, so it cannot manufacture a loss, and it
converts a silent strand into a named, visible anomaly.

**This is not a general fix for the stranded-row class.** A row stranded for a reason other than
expiry (a permanently rejected exit with no mark) is untouched and stays open. Saying so here
stops the next reader believing the class is closed.

## 3. MA37 — the epoch rule, fixed before it is written

* `scorecard`, `paper_report` and therefore `tuning_candidates` take an `epoch` argument whose
  **default is the store's CURRENT epoch** (`scream_log.current_epoch`), exactly as
  `scream_log.records()` already does. One convention, already shipped, extended to the three
  consumers that never adopted it.
* **WHICH ERA USERS SEE, CHOSEN NOW: the current epoch, and only the current epoch.** The
  archived era was retired by its own register for a stated reason — it *"predates the corrected
  alert stack (B1 price basis, C-series fixes)"* — and a number computed on rows the project has
  formally retired is not the live number, whichever way it points.
* **THE ARCHIVED ERA IS NOT HIDDEN AND NOT DELETED.** Every payload carries the epoch it was
  computed on and the count of rows in every other epoch, so a reader can see that an older
  record exists and is excluded. `scream_log`'s first principle — *"the reset is an archive,
  never a delete"* — is the whole reason this is a filter and not a purge.
* **`epoch=None` means ALL epochs**, so the blended figure remains computable on demand. Nothing
  is destroyed; what changes is the default.
* **THE TUNING LOOP IS THE POINT, not the display.** `tuning_candidates` proposes which alert
  fingerprints to favour. Learning from a record the project retired is the defect that matters
  most here, and it is fixed by the same one-line default.

**PRE-COMMITTED, BEFORE ANY POST-FIX NUMBER IS READ: the current-epoch record is expected to be
THIN — plausibly zero closed trades — and "thin" is the honest state, to be rendered as thin.**
It may not be worked around by widening the filter, by falling back to the blend when the
current epoch is small, or by reporting a zero as a result. If the honest answer is *"no live
alerts logged in this era yet"*, that is the answer that ships.

## 4. Controls — all six run, and C1/C2 gate

* **C1 (GATES).** No row that was already `closed` changes its `pnl_pct`, `exit_premium` or
  `status`. The MA36 path may only ever touch rows that were `open`. If a closed row moves, the
  change is void.
* **C2 (GATES).** The archive is read-only: the count of rows per `record_epoch` is identical
  before and after, and no row's `record_epoch` changes. MA37 is a filter, never a purge.
* **C3.** A no-bid position **before** expiry still defers, with the B5-lesser reason unchanged.
* **C4.** A past-expiry position that looks in-the-money is **not** settled, is not scored, and
  is reported by name.
* **C5.** `scorecard(store, epoch=None)` reproduces the pre-fix blended numbers exactly, which
  is the proof that the old figure was filtered rather than lost.
* **C6.** `record_outcome` on a `0.0` exit premium yields `pnl_pct == -1.0` exactly, pinned with
  a real entry premium — the arithmetic the whole MA36 repair rests on.

## 5. Expectations, written down first, scored in the handoff

1. **The live expectancy FALLS, or is unchanged, and CANNOT rise** on MA36 alone — the repair
   adds only −100% trades. **90/10.** *If it rises, the fix is wrong and ships nowhere.*
2. **MA37 leaves the current-epoch record thin — under `MIN_CLOSED_PER_BUCKET` (30) closed
   trades, and quite possibly zero.** 85/15.
3. **The blended figure and the current-epoch figure differ materially** (more than 1pp of
   expectancy), i.e. MA37 is not cosmetic. 70/30.
4. **No closed row moves** (C1 passes first time). 95/5.
5. **The ITM guard never fires on the local database**, because the local store is dev/test
   output and holds no real stranded position. 80/20.
6. **`tuning_candidates` is the consumer whose output changes most**, because it is the one that
   thresholds on `MIN_CLOSED_PER_BUCKET` per bucket. 60/40.

## 6. Trial cost and scope

**ZERO trials. `N` does not move** — options stays at 292, equity at 218, infra at 11. Neither
item has a pre-committed bar or returns a verdict against one, which is the `FIXED`-class test
`O21` had to have corrected *upward* the one time it got this wrong; both of these are genuine
repairs of a defect, so `FIXED` is right and the log row will say so.

**No research claim moves.** `GATED_LATE_HALF_EXPECTANCY = 0.1288` and every backtested options
figure are untouched: this changes what the **live forward record** reports about itself.

## 7. Void conditions

1. Any closed row changes (C1) → void.
2. Any row's `record_epoch` changes, or any row is deleted (C2) → void.
3. The live expectancy **rises** as a result of MA36 → stop, report, ship nothing.
4. A non-zero settlement price is computed from a reconstructed underlying → void, §2 forbids it.
5. The epoch default is set to anything other than the current epoch, or widened when the
   current epoch is thin → void, §3 forbids it.
6. Any third item is fixed inside this register. MA38–MA49 are named in the same audit section
   and are **not** in scope; they get their own row and their own register.
