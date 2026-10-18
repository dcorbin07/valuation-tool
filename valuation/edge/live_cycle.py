"""THE ONE CYCLE THAT DRIVES EVERY SLOT — paper and live, identical code.  [item 58b]

WHY ONE RUNNER AND NOT TWO
--------------------------
The paper slot and every live slot run **the same function**. That is the whole point of step 3
of item 58b: the live path gets proven with real (paper) orders before any real money, and a
second implementation for paper would prove a different program. The only thing that differs
between a paper slot and a live one is **which client it is handed** — and the clients are
separate classes that each accept only their own host, so neither can be pointed at the other's.

WHAT A CYCLE DOES, IN ORDER
---------------------------
For each slot, independently (one slot's failure never stops another):

  1. resolve its percentage and whether it is armed (`live_slots.armed`);
  2. decide whether an event applies (`live_slots.event_for`) — a new rebalance on the bound
     record, a percentage change, or an unfilled remainder from the event it is already working;
  3. run **every** "is anything broken" check (`live_slots.preflight`). A failure means **no
     orders for that slot this cycle, plus an alert**, and it tries again next cycle;
  4. compute the per-stock targets and the order plan;
  5. **armed** → send `day` limit orders and record each attempt.
     **0%** → log the plan, diff it against the paper slot, send nothing, and **construct no
     client at all**;
  6. record what it processed, so a restart never repeats an order.

WHEN IT RUNS, AND WHY THAT TIME
-------------------------------
**14:40 UTC.** Fractional orders must be `day` limit orders (Alpaca permits no other
`time_in_force` for a fractional quantity), and a `day` order placed outside market hours is
not worked until the next session — so a cycle has to run **inside** the session or its orders
sit unexamined.

14:40 UTC is **10:40am ET in summer and 9:40am ET in winter**, i.e. inside the session in both,
which matters because this project has already been bitten by a fixed UTC cron drifting an hour
against the Eastern session twice a year (`app_saas`'s own note on 20:45 UTC being 4:45pm ET in
summer and 3:45pm ET in winter). It is also:

* **after the open has settled** — the first ten minutes carry the widest spreads of the day,
  and every order here is a limit at the mid;
* **well before the close**, so an unfilled order has most of a session to work and the
  re-send next cycle is the exception rather than the rule;
* **not on the hour**, where every other scheduled job in this repo clusters.

A cycle outside market hours is not an error. It computes, logs, alerts if something is broken,
and sends nothing — `session_state()` decides, and the reason travels in the result.

NOTHING HERE READS A RETURN
---------------------------
No loss stops, no drawdown rule, no drift rebalancing — removed by Don's instruction and
recorded in §8a. The only inputs that can cause an order are the book in force, its weights,
the account's equity and the slot's percentage. A price is read to set a limit and to size the order, never to decide WHETHER to trade.
A test walks this module's AST and asserts no such name exists.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

from . import live_slots as LS
from . import settlement as SETTLE

#: The scheduled minute, in UTC. See the module docstring for why.
CYCLE_UTC = "14:40"

#: The paper slot's name. A STRING, deliberately not a number: `discover_slots` returns ints
#: from `ALPACA_ACCOUNT_<n>_*`, so a string slot id cannot collide with a live slot however
#: many Don adds, and `str(slot) == "paper"` is the one test that tells them apart.
PAPER_SLOT = "paper"

#: The paper slot holds the whole paper account, because its job is to mirror the Index book
#: through the identical runner and be the thing live slots diff against. A fraction would make
#: the parity diff a comparison of two different books.
PAPER_PCT = 100.0

#: THE THREE SEND MODES, and the only three. [item 2b]
#:
#: `DRY` computes everything and transmits nothing, for every slot. `PAPER` transmits for the
#: paper slot on the paper client and leaves every live slot dry however it is configured.
#: `LIVE` additionally lets an ARMED live slot transmit, and remains reserved for after the
#: auditor review.
#:
#: **ONE MODE RATHER THAN TWO BOOLEANS.** `send` plus `send_paper` can disagree, and both
#: inconsistent combinations would have to mean something; a three-valued mode has no
#: inconsistent state to interpret.
DRY, PAPER, LIVE = "dry", "paper", "live"

#: The tokens that mean LIVE, matched EXACTLY. `1` is the brief's own; `live` is accepted
#: because a reader typing the word means it.
LIVE_TOKENS = ("1", "live")

#: The token that means PAPER-ONLY, matched exactly.
PAPER_TOKENS = ("paper",)


def send_mode(raw_value) -> dict:
    """`{mode, token, reason}` from a request parameter. **ANYTHING UNRECOGNISED IS DRY.**

    The first cut of the door used `bool(request.args.get("run"))`, which is TRUTHINESS: `?run=0`
    is a non-empty string and would therefore have placed LIVE orders, as would `?run=no` and
    `?run=false`. A caller typing the thing that means "no" got the thing that means "yes".

    So the match is exact, the unrecognised case is DRY, and the reason SAYS SO -- because a
    caller who believed they were sending needs to learn that they were not, and silence would
    read identically to a quiet market.
    """
    tok = ("" if raw_value is None else str(raw_value)).strip().lower()
    if tok in LIVE_TOKENS:
        return {"mode": LIVE, "token": tok,
                "reason": "live sending requested; every live slot is still gated by "
                          "LIVE_PILOT_ENABLED, a non-zero percentage, an authorized holder "
                          "and a key pair"}
    if tok in PAPER_TOKENS:
        return {"mode": PAPER, "token": tok,
                "reason": "paper-only: the paper slot transmits on the paper client and every "
                          "live slot stays a dry run whatever its settings"}
    if not tok:
        return {"mode": DRY, "token": "", "reason": "no run token: a dry run for every slot"}
    return {"mode": DRY, "token": tok,
            "reason": ("the run token %r is not one of %r, so this is a DRY RUN and NOTHING "
                       "was sent. It is not treated as a request to send: a truthiness test "
                       "would have read '0' and 'no' as yes."
                       % (tok, tuple(PAPER_TOKENS) + tuple(LIVE_TOKENS)))}


#: How far two order plans may differ, per name, as a share of the slot's value, before the
#: parity diff is reported as a MISMATCH. 0.5% absorbs the rounding of a fractional quantity at
#: two-decimal limit prices and nothing larger.
PARITY_TOLERANCE = 0.005

#: THE ID NAMESPACE THIS PATH OWNS. [item 63, auditor #9]
#:
#: Every order this module places carries `valquo-<slot>-<event>-<ticker>`, and `reconcile`
#: counts an order as this slot's only if it starts with `valquo-<slot>-`. The old prefix was
#: the bare `"<slot>-"`, which was safe against other slots (the hyphen separates `1-` from
#: `11-`) and against the paper slot (`PAPER_SLOT` is a word, not a number) and safe against a
#: MANUAL order only by accident -- Alpaca's own ids are UUID-shaped, so their second character
#: is never a hyphen. An order a human tagged `1-whatever` would have been absorbed into the
#: slot's holdings and could then have been sold by it.
#:
#: ONE DEFINITION, used by the writer and the reader (`B7`). Two copies of an id convention
#: drift, and the drift is silent: the reader simply stops recognising the writer's orders and
#: the slot reads as holding nothing.
COID_NAMESPACE = "valquo"

#: Alpaca's documented maximum page for `/v2/orders`. A FULL page is treated as TRUNCATED --
#: see `reconcile`, and the auditor's measurement of the old 100-order default.
ORDERS_PAGE_LIMIT = 500

#: HOW MANY CYCLES ONE EVENT MAY BE ATTEMPTED BEFORE THE SLOT STOPS TRYING. [item 63, #11]
#:
#: §8a re-prices and re-sends an unfilled order "each following cycle until that event's targets
#: are met", which is right for a settlement delay and wrong for a PERMANENT rejection -- an IRA
#: that cannot hold fractional shares, say. `live_notify` dedupes on
#: `(kind, slot, event, reason[:120])`, so a condition that fails identically every day is
#: announced ONCE and then silent. A slot failing the same way every day for a month without
#: saying so is a failure mode this project has already paid for, so the retry stops and
#: escalates instead.
MAX_EVENT_ATTEMPTS = 5


def coid_prefix(slot) -> str:
    """The prefix identifying one slot's own orders. The reader's half of `client_order_id`."""
    return "%s-%s-" % (COID_NAMESPACE, str(slot))


def client_order_id(slot, event_key_str, ticker, attempt=None) -> str:
    """The id stamped on every order this path places. The writer's half of `coid_prefix`.

    **IT CARRIES THE ATTEMPT NUMBER, AND WITHOUT THAT THE REMAINDER MECHANISM CANNOT WORK
    [item 64].** §8a re-prices an unfilled order and re-sends it on the following cycle, which
    means the same event and the same ticker -- so the id was byte-identical to one Alpaca had
    already accepted, and Alpaca rejects a duplicate `client_order_id`. The second real cycle
    sent 60 remainder orders and **Alpaca refused all 60**. Item 63 made this id a namespace
    and not unique per attempt, which went unnoticed because no second attempt had ever
    happened: blocker 1 meant the first attempt never reached the broker either.

    **ATTRIBUTION IS UNAFFECTED**: `reconcile` matches on the `valquo-<slot>-` PREFIX, so a
    suffix changes nothing about which orders a slot owns. `attempt=None` keeps the old form,
    for a caller reproducing a recorded id.

    **THE NUMBER PASSED HERE IS `send_seq`, NOT THE ATTEMPT CEILING'S COUNTER [item 64].** They
    were briefly the same value and they have opposite requirements: the ceiling RESETS when the
    book advances (or a healthy rebalance stops itself) and this must NEVER reset (or it
    reproduces an id Alpaca has already accepted). Sharing them sent 22 duplicate ids on one
    real cycle.
    """
    base = "%s%s-%s" % (coid_prefix(slot), event_key_str, str(ticker).upper())
    if attempt is None:
        return base
    return "%s-a%d" % (base, int(attempt))


def live_dir(root: str = None) -> str:
    """Where slot state lives. `data/` — gitignored, on the service's persistent disk."""
    from .fleet import repo_root
    return os.path.join(root or repo_root(), "data", "live_slots")


def state_path(slot, root: str = None) -> str:
    return os.path.join(live_dir(root), "slot_%s.json" % str(slot).replace(os.sep, "_"))


def read_state(slot, root: str = None) -> dict:
    """A slot's own record. Never raises; an unreadable state is an EMPTY one.

    **AN EMPTY STATE IS THE SAFE DEFAULT AND THAT IS NOT OBVIOUS.** It means "this slot has
    processed nothing", so the next cycle sees a rebalance event and buys in. The alternative
    — treating an unreadable state as "already processed" — would silently skip a real event
    and leave the slot holding nothing while reporting success. A slot that has genuinely
    bought something is caught anyway by `preflight`, which compares this record against the
    broker's own positions and refuses when they disagree.

    **CORRECTED 2026-10-15 (item 63): THAT LAST SENTENCE WAS FALSE WHEN IT WAS WRITTEN, AND IT
    IS THE DEFENCE THIS DEFAULT RESTED ON.** `preflight` iterated the slot's own record, so an
    EMPTY record yielded zero comparisons and passed however much the broker held -- the check
    fired on a wrong record and was blind to a missing one, which is the case this default
    produces. The auditor reproduced a second full buy-in through it. The sentence is true
    again only because `preflight` now also compares in the reverse direction, scoped to names
    this slot has itself ordered, and because the intended orders are written BEFORE they are
    sent. Neither existed when the defence was written.
    """
    try:
        with open(state_path(slot, root), encoding="utf-8") as fh:
            d = json.load(fh) or {}
    except (OSError, ValueError):
        return {"slot": str(slot), "last_event_date": None, "last_pct": None,
                "holdings": {}, "processed": [], "attempts": [], "fills_seen": 0}
    d.setdefault("holdings", {})
    d.setdefault("processed", [])
    d.setdefault("attempts", [])
    d.setdefault("fills_seen", 0)
    return d


def write_state(slot, state: dict, root: str = None) -> dict:
    """Atomic, and its failure is reported rather than raised."""
    try:
        d = live_dir(root)
        os.makedirs(d, exist_ok=True)
        p = state_path(slot, root)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(state, fh, indent=2, sort_keys=True, default=str)
            fh.write("\n")
        os.replace(tmp, p)
        return {"ok": True, "reason": ""}
    except OSError as e:
        return {"ok": False, "reason": "could not write slot state: %s" % e}


def event_key(event: dict, book: dict, pct) -> str:
    """A stable name for the event a cycle is acting on, so a restart cannot repeat it.

    The key carries **what makes the event that event**: a rebalance is identified by the
    book's formation date, a percentage change by the two percentages. So re-running the same
    cycle finds the key already in `processed` and does nothing, while a genuinely new event
    produces a new key.
    """
    kind = (event or {}).get("event") or "none"
    if kind == "rebalance":
        return "rebalance:%s" % ((book or {}).get("formed_on") or "?")
    if kind == "pct_change":
        return "pct:%s->%s" % ((event or {}).get("from_pct"), pct)
    return "none"


def parity(live_targets: dict, paper_targets: dict, *, live_value: float,
           paper_value: float, tolerance: float = PARITY_TOLERANCE) -> dict:
    """Diff a live slot's TARGET WEIGHTS against the paper slot's. [rewritten, item 63]

    §8 requires dry-run parity logged and diffed against the paper book before any real order.
    The two accounts have different equity, so the comparison is per name **as a share of the
    slot's own value** — comparing dollar amounts would report a mismatch on every name purely
    because the accounts differ in size, which is a diff that can never pass and therefore
    never means anything.

    **IT DIFFS TARGETS AND NOT ORDER DELTAS, AND THAT IS THE REPAIR.** The first cut compared
    order plans. A delta is a function of current holdings, and the paper slot (100% of the
    paper account) and a live slot (X% of Don's) are routinely in different fill states -- a
    name already filled on one side and not the other produces a mismatch with nothing wrong.
    Once that starts, every name mismatches for a legitimate reason, and a check that cries
    wolf on healthy cycles is a check nobody reads on the unhealthy one (`MA21`).
    **A TARGET is holdings-independent**: whatever each slot already owns, both should be
    aiming at the same proportions of their own value, and that is exactly the claim "the live
    orders reproduce the paper book's arithmetic" is making.
    """
    out = {"ok": False, "n_names": 0, "n_mismatch": 0, "worst": None, "mismatches": [],
           "tolerance": tolerance, "compares": "target weights", "reason": ""}
    lv, pv = LS._f(live_value), LS._f(paper_value)
    # **EVERY TARGET ZERO IS VACUOUS, NOT FAILED [item 71, proposed by item 70].** This
    # function compares each name's target as a SHARE of the slot's own value, and a wind-down
    # has a slot value of zero and a zero target for every name -- so there is no weight to
    # diff and nothing for a mismatch to mean. Refusing it blocked the X->0 sell-out at the
    # third of four gates, which `C5` running in the unusual direction: absent evidence was
    # being read as adverse evidence.
    #
    # **IT CANNOT WIDEN TO ANYTHING ELSE**, and that is structural rather than careful: a
    # positive percentage with a positive equity always yields a positive slot value, and
    # `targets` REFUSES a non-positive equity before this is ever called -- so "every target is
    # zero" is reachable only from a zero percentage. The `targets` dict must also be non-empty,
    # or a book that failed to load would read as a wind-down.
    _lt = [LS._f(v) or 0.0 for v in (live_targets or {}).values()]
    if _lt and all(abs(v) <= 0 for v in _lt) and (lv or 0.0) <= 0:
        out.update(ok=True, measured=False, n_names=len(_lt),
                   reason=("every target is zero, so there are no weights to diff: this is the "
                           "X->0 wind-down and parity is VACUOUS rather than passed. The sales "
                           "are of what this slot's own record holds, which no weight "
                           "comparison could check."))
        return out
    if not lv or not pv or lv <= 0 or pv <= 0:
        out["reason"] = ("parity needs a positive value on both sides; live=%r paper=%r"
                         % (live_value, paper_value))
        return out

    def _share(targets, total):
        by = {}
        for t, v in (targets or {}).items():
            by[str(t).upper()] = (LS._f(v) or 0.0) / total
        return by

    a, b = _share(live_targets, lv), _share(paper_targets, pv)
    names = sorted(set(a) | set(b))
    out["n_names"] = len(names)
    worst = 0.0
    for t in names:
        d = abs(a.get(t, 0.0) - b.get(t, 0.0))
        if d > worst:
            worst, out["worst"] = d, {"ticker": t, "diff_share": round(d, 6)}
        if d > tolerance:
            out["n_mismatch"] += 1
            out["mismatches"].append({"ticker": t,
                                      "live_target_share": round(a.get(t, 0.0), 6),
                                      "paper_target_share": round(b.get(t, 0.0), 6),
                                      "diff_share": round(d, 6)})
    out["ok"] = (out["n_mismatch"] == 0)
    out["reason"] = ("the live slot's target weights match the paper book's on all %d names "
                     "within %.3f%%" % (len(names), tolerance * 100.0) if out["ok"] else
                     "%d of %d target weights differ from the paper book's by more than %.3f%%"
                     % (out["n_mismatch"], len(names), tolerance * 100.0))
    return out


def reconcile(client, state: dict) -> dict:
    """What this slot ACTUALLY holds, from its own filled orders. Returns a report.

    **THE SLOT'S RECORD IS BUILT FROM FILLS, NEVER FROM SUBMISSIONS.** A `day` limit order can
    fill in part or not at all, so a record built from what was SENT would claim holdings the
    account does not have -- and the next cycle would then plan no remainder, leaving the event
    half-done and looking complete. This is what the brief means by "the slot keeps its own
    record of what it bought".

    **IT IS SCOPED TO THIS SLOT'S OWN ORDERS**, matched on the `client_order_id` prefix this
    module stamps. Don's other holdings in the account are never read into the record and
    therefore can never be traded: the planner can only sell what this dict contains.

    **IT DOES NOT COPY THE BROKER'S POSITION LIST**, deliberately. Doing so would make
    `preflight`'s record-versus-broker check vacuous -- it would compare the broker against
    itself and could never fire. Two independent accounts of the same holdings is the point.
    """
    out = {"ok": False, "n_orders": 0, "n_filled": 0, "unfilled": 0, "fills": [],
           "holdings": dict(state.get("holdings") or {}), "symbols": [], "resting": [],
           "truncated": False, "open_remainder": False, "reason": "",
           # WHICH OF FOUR STATES THIS IS IN. [item 65, the auditor's last blocker]
           #
           #   not_attempted -- no client was supplied. A dry or paper-only cycle; it must
           #                    still compute a plan, and it cannot send anyway.
           #   failed        -- the broker was asked and would not answer.
           #   truncated     -- the broker answered with a full page, so the total is wrong.
           #   ok            -- the holdings are known.
           #
           # **`failed` AND `truncated` ARE THE SAME EPISTEMIC STATE** -- "I do not know what I
           # hold" -- and before this only `truncated` refused. `not_attempted` is a THIRD
           # thing: "I did not ask". Collapsing it into `failed` would refuse every dry run,
           # which is the positions sentinel's lesson one function over.
           "order_read": "not_attempted"}
    if client is None or not hasattr(client, "orders"):
        out["reason"] = "no client, or it cannot list orders; the record is left as it was"
        return out
    # THE SLOT MUST BE POPULATED OR THE PREFIX MATCHES NOTHING [item 63, auditor #6]. With no
    # `slot` key the old prefix was the bare `"-"`, which matches no id -- so `reconcile`
    # silently returned an EMPTY book and reported success. `run_slot` always sets it, but a
    # caller invoking this directly did not, and "reconciled an empty book" is indistinguishable
    # from "this slot holds nothing".
    if not str(state.get("slot") or "").strip():
        out["order_read"] = "failed"
        out["reason"] = ("the state carries no slot number, so no order could be attributed to "
                         "it; this is a refusal rather than an empty book")
        return out
    # **`orders_result` RATHER THAN `orders`, AND THIS IS WHERE THE AUDITOR'S BLOCKER REALLY
    # LIVED [item 65].** Both clients' `orders()` return `[]` when the request fails, so a 5xx
    # arrived as an EMPTY SUCCESS: `order_read` read "ok", the book read empty, the derived
    # scope read empty, every broker position was skipped, and a second full buy-in went out.
    # Refusing on a failed read -- the auditor's `if` -- was necessary and could never fire,
    # because nothing below this line could tell a failure from an empty account.
    #
    # `orders()` is kept for callers that want whatever arrived; this path needs the difference.
    try:
        if hasattr(client, "orders_result"):
            res = client.orders_result(limit=ORDERS_PAGE_LIMIT) or {}
            if not res.get("ok"):
                out["order_read"] = "failed"
                out["reason"] = (res.get("reason")
                                 or "the broker's orders could not be read")
                return out
            # **AND `truncated` IS A REFUSAL TOO [item 67 part 0].** The reader is paged now,
            # and it reports "I could not prove this is every order" separately from "I could
            # not read them". Reading only `ok` turned that into SUCCESS WITH A SHORT LIST --
            # and the length check below could not see it, because the pager had already
            # deduped the page down. A reader whose refusal the caller does not read is the
            # defect item 65 found underneath the auditor's own fix, one item later.
            if res.get("truncated"):
                out["truncated"] = True
                out["order_read"] = "truncated"
                out["reason"] = (res.get("reason")
                                 or "this slot's order history could not be read in full")
                return out
            out["pages_read"] = res.get("pages")
            orders = list(res.get("data") or [])
        else:
            # A client without the honest reader -- a stub, or something older. Its `[]` is
            # ambiguous and is treated as it reads, which is the pre-item-65 behaviour; the
            # derived interface test requires `orders_result` on both REAL clients, so this
            # branch cannot be the production path.
            try:
                orders = client.orders(limit=ORDERS_PAGE_LIMIT) or []
            except TypeError:
                orders = client.orders() or []
    except Exception as e:                                              # noqa: BLE001
        out["order_read"] = "failed"
        out["reason"] = "the broker's orders could not be read (%s)" % type(e).__name__
        return out
    # A FULL PAGE MEANS THERE MAY BE MORE, AND MORE MEANS THE FILL TOTALS ARE WRONG. Alpaca
    # returns newest first, so the orders that fall outside the window are the OLDEST -- i.e.
    # the earlier rebalance's fills, which is exactly the half that makes a holding look
    # half-sized. Under-counting holdings makes the planner buy the difference again, so this
    # is reported as a refusal rather than smoothed over.
    if len(orders) >= ORDERS_PAGE_LIMIT:
        out["truncated"] = True
        out["order_read"] = "truncated"
        out["reason"] = ("the broker returned a FULL page of %d orders, so older fills may be "
                         "outside the window and this slot's holdings cannot be totalled "
                         "reliably; it sends nothing this cycle" % len(orders))
        return out
    mine_prefix = coid_prefix(state.get("slot"))
    filled, open_left = {}, False
    for o in orders:
        coid = str((o or {}).get("client_order_id") or "")
        if not coid.startswith(mine_prefix):
            continue
        out["n_orders"] += 1
        sym = str((o or {}).get("symbol") or "").upper()
        # EVERY NAME THIS SLOT HAS ORDERED, filled or not. `preflight`'s reverse direction
        # needs it: a broker position in one of these names that the record does not know
        # about is the empty-record hole, and a position in any OTHER name is Don's own and
        # must never be refused on. [item 63]
        if sym and sym not in out["symbols"]:
            out["symbols"].append(sym)
        fq = LS._f((o or {}).get("filled_qty"))
        side = str((o or {}).get("side") or "").lower()
        status = str((o or {}).get("status") or "").lower()
        if status in ("new", "accepted", "partially_filled", "pending_new", "held"):
            open_left = True
            # WHICH ORDERS ARE STILL RESTING, AND ON WHICH SIDE. [item 65]
            # Alpaca refuses an order on one side of a name while one of ours rests on the
            # other, so the sender has to be able to find and clear it. Only THIS slot's own
            # orders are listed, because the prefix filter above has already run -- the path
            # never cancels anything it did not place.
            if sym:
                # **AND HOW MUCH OF IT IS STILL OPEN [item 67 part 0].** The quantity was not
                # recorded, so the planner could not subtract it -- which is the auditor's
                # third blocker: five cycles, five full orders, 500 shares against a 100-share
                # target. `qty - filled_qty` is the part still working; a partial fill is
                # already in `filled` below, so taking the whole `qty` would double-count it.
                oq = LS._f((o or {}).get("qty"))
                of = LS._f((o or {}).get("filled_qty")) or 0.0
                out["resting"].append({"id": str((o or {}).get("id") or coid),
                                       "ticker": sym, "side": side, "coid": coid,
                                       "qty_open": (max(0.0, oq - of)
                                                    if oq is not None else None)})
        if fq and fq > 0 and sym:
            out["n_filled"] += 1
            filled[sym] = filled.get(sym, 0.0) + (fq if side == "buy" else -fq)
            # STEP 7, RECORDED HERE because this is the only place a FILL PRICE exists. A
            # `day` limit order placed mid-cycle is usually still working when the cycle
            # ends, so a measurement taken at submission would have nothing to measure.
            lp = LS._f((o or {}).get("limit_price"))
            fp = LS._f((o or {}).get("filled_avg_price"))
            if lp and fp:
                out["fills"].append({"ticker": sym, "kind": "stock", "side": side,
                                     "mid": lp, "fill": fp, "order_id": coid})
        if (not fq or fq <= 0) and status in ("canceled", "expired", "rejected"):
            # AN ORDER THAT NEVER FILLED IS ALSO AN OBSERVATION, and on this path it is the
            # more informative half -- see `feed_gap_report`'s own note on censoring.
            out["unfilled"] += 1
    for sym, q in filled.items():
        # A SELL REDUCES AND NEVER GOES NEGATIVE: this slot cannot hold less than nothing, and
        # a negative would read as a short the §8 path is not authorised to take.
        out["holdings"][sym] = max(0.0, round(q, 9))
    out["holdings"] = {k: v for k, v in out["holdings"].items() if (v or 0) > 1e-9}
    out["open_remainder"] = open_left
    out["order_read"] = "ok"
    out["ok"] = True
    return out


def _marks_for(client, tickers) -> dict:
    """Quotes for the names a cycle would trade. Never raises; a gap becomes a preflight fail.

    **A CLIENT THAT CANNOT QUOTE IS A DIFFERENT FACT FROM A CLIENT THAT QUOTED NOTHING**, and
    the first cut returned `{}` for both [item 63]. `_LiveClient` genuinely has no `quotes` --
    correctly, because Alpaca's market data is on a different host and that class is pinned to
    exactly one -- so a caller handing it here got an empty map, and the slot then refused with
    "no usable price for 2 name(s)", which points a reader at the price feed rather than at the
    client. `run_cycle` guards the call with `hasattr` and prices live slots from the paper
    client; this makes the ungarded case say what actually happened.
    """
    if client is None or not hasattr(client, "quotes"):
        return {}
    try:
        return client.quotes(sorted(set(tickers))) or {}
    except AttributeError:
        # NOT swallowed into an empty map: the only way here is a `quotes` that exists and
        # then fails on an attribute of its own, which is a bug in the client rather than a
        # quiet feed. Re-raised so it reaches `run_slot`'s handler and is reported as a
        # crashed slot instead of as a missing price.
        raise
    except Exception:                                                   # noqa: BLE001
        return {}


def _rejection_reason(res) -> str:
    """WHY an order was refused, whichever client refused it. [item 64]

    **THE TWO CLIENTS DISAGREE ON THE SHAPE OF A FAILURE and nothing caught it**, because item
    63's interface test checked method NAMES and the suite's shape fixture models only SUCCESS
    replies. `_LiveClient._request` returns `{"ok": False, "status", "error"}` while
    `AlpacaPaperBroker.place_equity` returns `{"ok": False, "reason", "detail", "sent"}`.
    Reading `error` alone reported sixty real rejections as the string `None`, on the one path
    whose whole purpose is to say why it did not trade.

    Alpaca puts the actionable sentence in the response BODY, not the status, so the nested
    `detail.error` is unwrapped rather than printed as a dict -- a reader needs
    "potential wash trade detected" or "insufficient buying power", not `{'ok': False, ...}`.
    """
    if not isinstance(res, dict):
        return "the client returned %r rather than a reply" % (res,)
    def _flat(v):
        """Alpaca's message, not the envelope it arrived in. The live client's `error` IS the
        parsed body, so it is a dict; printing it gives `{'message': 'forbidden'}` where a
        reader needs `forbidden`."""
        if isinstance(v, dict):
            return str(v.get("message") or v.get("error") or v.get("reason") or v)
        return str(v)

    bits = []
    for k in ("error", "reason"):
        v = res.get(k)
        if v:
            bits.append(_flat(v))
    d = res.get("detail")
    if isinstance(d, dict):
        inner = d.get("error") or d.get("message") or d.get("reason")
        if isinstance(inner, dict):
            inner = inner.get("message") or inner.get("error") or inner
        if inner:
            bits.append(_flat(inner))
        if d.get("status"):
            bits.append("HTTP %s" % d.get("status"))
    elif d:
        bits.append(str(d))
    if res.get("status") and not any("HTTP" in b for b in bits):
        bits.append("HTTP %s" % res.get("status"))
    # DEDUPED, because the paper client often carries the same sentence in two places and a
    # doubled reason reads as two faults.
    seen, out = set(), []
    for b in bits:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return "; ".join(out)[:400] or ("the client refused it and said nothing; the reply keys "
                                    "were %s" % sorted(res))


def writes_allowed(rec: dict, *, may_write: bool) -> dict:
    """May this cycle persist anything about this slot? ONE definition. [item 71, blocker C]

    `{"ok", "reason"}`. Two conditions and both are evidence rather than intention:

    1. **THE ORDER READ MUST HAVE SUCCEEDED.** `order_read == "ok"` is the only state in which
       this slot knows what it holds and what is working. `truncated` and `failed` already
       refused the cycle outright; `not_attempted` did not, and that is the blocker -- a cycle
       with no client closed the event that a cycle with a client holds open, and WROTE it.
    2. **THE CALLER MUST PERMIT A WRITE.** A GET of `/admin/live-cycle` ran a dry cycle, and a
       dry cycle still wrote state. A side-effecting GET is reachable by a retry, a prefetch, a
       proxy or a pasted link -- the same reasoning `/admin/track-row` already applies to its
       own write, where a GET asking to write returns 405.

    **IT IS A PRECONDITION, NOT AN OPTION**, and the default is the permissive one only because
    every production caller passes it explicitly; the test suite pins both directions.
    """
    read = str((rec or {}).get("order_read") or "")
    if not may_write:
        return {"ok": False, "reason": ("this is a READ-ONLY cycle, so nothing about this slot "
                                        "is persisted -- the plan is computed and reported and "
                                        "the record is left exactly as it was")}
    if read != "ok":
        return {"ok": False, "reason": (
            "this slot's own orders were not read on this cycle (order_read=%r), so it does "
            "not know what is working at the broker and persists NOTHING. A cycle that could "
            "not look must not record a conclusion -- a paper or dry cycle builds no live "
            "client, and closing an event here would discard a remainder that a cycle which "
            "CAN look is holding open." % (read or "unknown"))}
    return {"ok": True, "reason": ""}


def _note_write(out: dict, res: dict, slot, what: str) -> bool:
    """EVERY `write_state` RESULT IS READ. [item 63, blocker 2]

    Its return was discarded at both call sites. A failed write produces an empty record, and an
    empty record is what makes the next cycle plan a full buy-in it has already made -- so the
    one function whose failure causes the duplicate was the one nobody checked. After a send
    there is nothing to undo, so this cannot refuse; it ALERTS, loudly, naming what could not be
    recorded. The refusal happens earlier, on the intent write, where it still can.
    """
    if (res or {}).get("ok"):
        return True
    if (res or {}).get("withheld"):
        # **NOT A FAILURE AND NOT AN ALERT [item 71].** A read-only cycle, or one that could
        # not read its own orders, is SUPPOSED to persist nothing -- alerting on it would fire
        # on five scheduled cycles a day and on every GET, which is how a real alert stops
        # being read (`MA21`).
        out["state_write_withheld"] = (res or {}).get("reason")
        return False
    out.setdefault("alerts", []).append({
        "kind": "state_write_failed", "slot": str(slot),
        "reason": ("this slot could not write its own record while %s: %s. Its next cycle may "
                   "not know what it already did." % (what, (res or {}).get("reason")))})
    out["state_write_failed"] = True
    return False


#: WHAT THE SLOT DOES TODAY WITH A NAME THAT IS NOT FRACTIONABLE. Measured from the shipped
#: path rather than asserted, and it is **not** "the whole slot refuses": `order_plan` sizes
#: every order as a fractional quantity (`abs(delta) / mark`, nine decimals), the send loop
#: transmits them one at a time, and a per-order rejection appends a `broker_error` and moves
#: on to the next name. So ONE non-fractionable name costs THAT NAME and nothing else --
#: for a while.
#:
#: **AND THEN IT COSTS THE WHOLE EVENT, WHICH IS THE PART THAT WANTS DECIDING.** The name's
#: target is never reached, so the event never closes, so it is retried -- and the no-progress
#: ceiling stops the event after `MAX_EVENT_TRADING_DAYS` trading days with no change in the
#: holdings. At that point the slot stops trying the event AT ALL, including the names that
#: would have traded, and raises `event_attempts_exhausted`. Under item 67's day counting that
#: is a week of trading rather than a single morning, which is a better failure than the one
#: before it and is still a failure.
#:
#: **THE CHOICE IS DON'S AND IS NOT MADE HERE.** The three options, priced:
#:   (a) leave it -- a non-fractionable name trades nothing, and after five trading days the
#:       event stops with a named alert. Costs nothing to build; costs a week of a rebalance.
#:   (b) round that name to whole shares -- it trades, at a weight that is wrong by up to one
#:       share's worth. A construction change: the slot would hold something the book does not
#:       describe.
#:   (c) skip that name -- the slot holds the rest at their own weights and the book's total is
#:       short by that name's share. Also a construction change, and it is silent unless
#:       reported.
#: Each needs its own register and none is a bug fix. **Reported, not decided.**
NON_FRACTIONABLE_TODAY = {
    "what_happens": ("the order is transmitted as a fractional quantity and Alpaca rejects "
                     "it; that ONE name does not trade and every other name in the book "
                     "does"),
    "and_then": ("the event's targets are never met, so it is retried, and the no-progress "
                 "ceiling stops the WHOLE event after %s trading days with an "
                 "`event_attempts_exhausted` alert -- including the names that would trade"),
    "the_choice_is_dons": ("leave it, round that name to whole shares, or skip that name. "
                           "The last two are construction changes, not bug fixes, and each "
                           "needs its own register."),
}


def fractional_report(client, tickers) -> dict:
    """Which of these names Alpaca says may be traded fractionally. READ-ONLY, no order.

    `fractionable` and `tradable` come from Alpaca's own asset master, one request for the
    whole active US equity list rather than one per name.

    **A NAME ABSENT FROM THE MASTER IS REPORTED ABSENT, NEVER AS `fractionable: False`.**
    Absent is not a measured False (`C5`) and the two have different fixes: one is a name
    Alpaca will not trade at all, the other is a name it will trade in whole shares.
    """
    want = sorted({str(t).strip().upper() for t in (tickers or []) if str(t).strip()})
    out = {"n_asked": len(want), "asked": want,
           "non_fractionable_today": dict(
               NON_FRACTIONABLE_TODAY,
               and_then=NON_FRACTIONABLE_TODAY["and_then"]
               % SETTLE.MAX_EVENT_TRADING_DAYS)}
    if client is None or not hasattr(client, "assets"):
        out["ok"] = False
        out["reason"] = ("no client able to read the asset master was supplied, so this is "
                         "UNMEASURED -- not a report that these names are whole-share only")
        return out
    try:
        got = client.assets(want) or {}
    except Exception as e:                                              # noqa: BLE001
        out["ok"] = False
        out["reason"] = "the asset master could not be read (%s: %s)" % (type(e).__name__, e)
        return out
    if not got.get("ok"):
        out["ok"] = False
        out["reason"] = got.get("reason") or "the asset master could not be read"
        return out

    rows = got.get("assets") or {}
    frac = sorted(k for k, v in rows.items() if v.get("fractionable"))
    whole = sorted(k for k, v in rows.items() if not v.get("fractionable"))
    untradable = sorted(k for k, v in rows.items() if not v.get("tradable"))
    out.update({
        "ok": True, "n_master": got.get("n_master"),
        "per_name": {k: {"fractionable": bool(v.get("fractionable")),
                         "tradable": bool(v.get("tradable"))}
                     for k, v in sorted(rows.items())},
        "n_fractionable": len(frac), "n_whole_share_only": len(whole),
        "whole_share_only": whole, "not_tradable": untradable,
        # NOT folded into either count. A name the master does not carry is unmeasured here.
        "missing_from_master": list(got.get("missing") or []),
        "reason": ("%d of %d names are fractionable; %d are whole-share only%s"
                   % (len(frac), len(want), len(whole),
                      ("; %d are not in Alpaca's active US equity master at all"
                       % len(got.get("missing") or []))
                      if got.get("missing") else "")),
    })
    return out


def account_settlement_report(client) -> dict:
    """What an account says about settlement and fractional trading. READ-ONLY, no order.

    Item 67 part 2's IRA question. Three reads, all GET: the account's own fields, its
    configuration, and the no-borrow figure a buy would actually be sized from.

    **"THE API DOES NOT REPORT IT" IS AN ANSWER AND IS GIVEN AS ONE.** Alpaca documents
    `fractional_trading` on `/v2/account/configurations`, and item 65 is a fresh demonstration
    that the documentation and the wire can disagree -- so absence is reported as absence
    rather than as disabled. The definitive test is a $1 buy placed by hand in Alpaca's own
    app, which is Don's to make or not; **no lane places it.**
    """
    out = {"ok": False, "reason": "no client was supplied", "constructs_an_order": False}
    if client is None:
        return out
    acct = None
    try:
        if hasattr(client, "account_report"):
            acct = client.account_report()
        elif hasattr(client, "account"):
            acct = client.account()
    except Exception as e:                                              # noqa: BLE001
        return dict(out, reason="the account could not be read (%s: %s)"
                    % (type(e).__name__, e))
    cfg = None
    try:
        if hasattr(client, "configurations"):
            cfg = client.configurations()
    except Exception as e:                                              # noqa: BLE001
        cfg = {"ok": False, "reason": "%s: %s" % (type(e).__name__, e)}

    budget = SETTLE.spendable(acct)
    frac = (cfg or {}).get("fractional_trading") if (cfg or {}).get("ok") else None
    reported = bool((cfg or {}).get("reported")) if (cfg or {}).get("ok") else False
    return {
        "ok": bool((acct or {}).get("ok")), "constructs_an_order": False,
        "account": {k: (acct or {}).get(k) for k in
                    ("status", "multiplier", "cash", "buying_power",
                     "non_marginable_buying_power", "regt_buying_power",
                     "trading_blocked", "account_blocked", "account_number_shape")},
        "spendable_without_borrowing": budget,
        "fractional_trading": ("enabled" if (reported and frac) else
                               "disabled" if reported else
                               "NOT REPORTED by the API"),
        "fractional_trading_note": (
            "Alpaca documents `fractional_trading` on /v2/account/configurations. Where it is "
            "absent this says so rather than guessing: the definitive test is a $1 buy placed "
            "by hand in Alpaca's own app, and no lane places one."),
        "max_options_trading_level": (cfg or {}).get("max_options_trading_level"),
        "configurations_read": bool((cfg or {}).get("ok")),
        "configurations_reason": (cfg or {}).get("reason"),
        "limited_margin_expected": (
            "Alpaca's IRAs are set up with limited margin (1x), so `multiplier` is expected to "
            "read 1 and `buying_power` to equal the cash. Limited margin permits spending "
            "UNSETTLED proceeds and does NOT permit borrowing or a margin debit -- which is "
            "why a rebalance here may never wait for settlement at all, and why the buy "
            "budget asks the broker rather than modelling it."),
    }


#: **THE SLOT STATE THAT BELONGS TO ONE EVENT AND MUST NOT OUTLIVE IT. [item 72]**
#:
#: Every one of these is keyed by event, so leaving an entry behind attributes one event's
#: residue to the next -- which is item 64's own subject: its fourth real cycle read 5 of 5
#: attempts while the book advanced 72 -> 77, one cycle from stopping a healthy rebalance on a
#: counter that meant something else when it was written.
#:
#: **ONE LIST, TWO SITES** (`B7`): the close branch and item 72's stale-event clearing. My first
#: cut of the second listed four of these, and item 64's own guard caught the divergence by
#: slicing the first `for bag in (` in the file -- which was the new one.
#:
#: `event_attempts` and `event_progress` are item 64's RETIRED counters, read nowhere. They stay
#: on the list because a bag that is cleared in one place and not the other is the drift this
#: constant exists to prevent, and clearing something nothing reads costs nothing.
EVENT_SCOPED_STATE = ("event_attempts", "event_progress", "send_seq",
                      "event_fingerprint", "event_attempt_days", "awaiting_settlement")


#: WHAT THE PLANNER CONCLUDED, AS A VALUE RATHER THAN AS AN EMPTY LIST.  [item 69]
#:
#: **ONLY `PLAN_TARGETS_MET` CLOSES AN EVENT.** The close branch used to test `not
#: plan["orders"]`, which is true of both *"nothing to do"* and *"I could not work out what to
#: do"* -- so an exit the feed could not price was recorded as a completed rebalance, with no
#: alert and a coverage line reporting perfect coverage. Third occurrence of that shape on this
#: path, and a boolean cannot carry three states.
PLAN_TARGETS_MET = "targets_met"          # nothing to do: no orders AND nothing skipped
PLAN_BLOCKED = "blocked"                  # something was skipped: the plan is INCOMPLETE
PLAN_WORK = "work"                        # there are orders to send

#: **AND A FOURTH: MY OWN ORDERS ARE STILL WORKING [item 70, the auditor's FIFTH blocker].**
#:
#: Item 67 subtracts this slot's own resting same-side quantity so a remainder cannot stack --
#: right, and it changed what an EMPTY PLAN MEANS. Before item 67 an empty plan meant "the
#: holdings match the targets"; since item 67 it can also mean "the gap is already covered by an
#: order that has not filled." The close branch read the first and got the second, so a resting
#: sell covering a whole exit CLOSED the event with no alert, and nothing retried once the `day`
#: order expired. **On a sell-out at 0% that leaves the slot fully invested at a declared 0%**,
#: and because `last_pct` is written to 0 the sell-out cannot re-fire.
#:
#: Fourth occurrence of ONE shape on this path, which is why it gets a value and not a boolean:
#: `place_limit` missing (two names, one call), `[]` meaning both empty and failed, truncated
#: versus failed, three populations for one fact -- and now "nothing left to PLAN" versus
#: "nothing left to DO".
PLAN_RESTING = "orders_working"           # nothing to send: my own orders are still unfilled

#: Every value. An outcome absent from this tuple is a programming error rather than a state,
#: and the guard that enumerates it would not see a fifth one added elsewhere.
PLAN_OUTCOMES = (PLAN_TARGETS_MET, PLAN_BLOCKED, PLAN_WORK, PLAN_RESTING)

#: The ONLY outcome that may close an event. Declared as a one-element tuple rather than a bare
#: equality so the test can assert the set and a future addition shows up as a change here.
PLAN_OUTCOMES_THAT_CLOSE_AN_EVENT = (PLAN_TARGETS_MET,)


def resting_for_event(resting, slot, key) -> list:
    """This slot's own resting orders THAT BELONG TO THIS EVENT. [item 70]

    **THE EVENT IS READ FROM THE `coid`, AND THE PREFIX IS DERIVED FROM THE WRITER RATHER THAN
    PARSED.** `client_order_id` builds `valquo-<slot>-<event>-<TICKER>-a<n>`; calling it with an
    EMPTY ticker returns exactly `valquo-<slot>-<event>-`, so "does this order belong to this
    event" is a `startswith` against the generator's own output. Splitting on `-` would be
    wrong on both sides: an event key carries dates (`rebalance:2026-10-22`) and a ticker can
    carry a dash (`BRK-B`), so a hand-rolled parse would mis-attribute both (`MA5`).

    **AND THE FILTER MATTERS RATHER THAN BEING TIDINESS.** `reconcile`'s list is scoped to the
    slot and NOT to the event, which is correct for item 67's subtraction -- a leftover order
    from the PREVIOUS event must still be subtracted so a remainder cannot stack. But a leftover
    from a previous event is no reason to hold THIS event open, and holding it open on one would
    stall every subsequent rebalance behind an order nobody is waiting for.
    """
    if not key or str(key) == "none":
        return []
    want = client_order_id(slot, str(key), "")
    out = []
    for r in (resting or []):
        if str((r or {}).get("coid") or "").startswith(want):
            out.append(r)
    return out


def plan_outcome(plan: dict, *, resting=None) -> str:
    """Which of `PLAN_OUTCOMES` this plan is.

    **`skipped` BEATS AN EMPTY `orders`.** A plan with nothing to send and something skipped is
    not a finished event -- it is an event whose work could not be worked out, and the two had
    the same truth value until this existed.

    **AND A RESTING ORDER FOR THIS EVENT BEATS AN EMPTY PLAN [item 70].** `resting` is this
    slot's own unfilled orders FOR THIS EVENT (see `resting_for_event`); when the plan is empty
    because they cover the gap, the event is not finished and must not close. It defaults to
    empty so a caller that does not supply it gets exactly the old behaviour -- which is why
    every call site is checked by test rather than assumed.
    """
    if (plan or {}).get("orders"):
        # **ORDERS BEAT A SKIP, and that is not a softening.** A skip alongside work is item
        # 67's per-name granularity, which the auditor checked and approved: an unreadable
        # resting quantity costs THAT NAME and the others still trade. Returning BLOCKED here
        # would refuse the whole cycle for one withheld name and revert it. The skip is alerted
        # either way; what differs is whether anything is sent.
        return PLAN_WORK
    if (plan or {}).get("skipped"):
        # **A SKIP BEATS A REST, and the order of these two is a judgement rather than an
        # accident.** Both keep the event open, so the only thing the precedence decides is
        # which one a reader is told about -- and "I could not work out what to do with this
        # name" needs a human, while "my order has not filled yet" does not. The resting fact
        # is reported alongside either way.
        return PLAN_BLOCKED
    return PLAN_RESTING if resting else PLAN_TARGETS_MET


def note_no_progress(st: dict, out: dict, key, *, counts_a_day: bool,
                     on_date: str = None) -> dict:
    """Record one attempt at `key` against the no-progress ceiling. ONE definition. [item 70]

    Returns `{"exhausted", "days", "reason"}` and MUTATES `st["event_fingerprint"]` and
    `st["event_attempt_days"]`; the caller decides what to do with an exhausted event.

    **PROGRESS IS A CHANGE IN THE HOLDINGS, NOT AN INCREASE**, and the holdings come from
    `reconcile`, which builds them from FILLS -- so the counter cannot be fooled by orders that
    are accepted and never fill, which is exactly what an unfillable limit or a permanent
    rejection produces. A fingerprint of the whole map also catches a sell and a buy that net to
    the same total. The old test was `held_now > baseline`, which a SELL can never satisfy, so
    the sell leg of a rebalance registered as no progress -- and under item 67 the sells go
    first.

    **`counts_a_day` IS THE CALLER'S, AND IT IS A PRECONDITION RATHER THAN AN OPTION.**
    `note_trading_day`'s own docstring reads *"Every date reaching this function is a date on
    which the orders window was open, so the returned list is a trading-day count with no
    holiday calendar anywhere near it."* A branch that can run outside the window (the resting
    and blocked branches both can) must pass False there, or a Saturday manual cycle would spend
    a trading day and the ceiling would stop meaning what its own alert says -- item 64's
    false-alarm family, which item 64 itself reintroduced by adding four more schedules.
    """
    held_map = st.get("holdings") or {}
    fp = "|".join("%s:%.6f" % (t, float(held_map.get(t) or 0))
                  for t in sorted(held_map))
    prints_seen = dict(st.get("event_fingerprint") or {})
    day_map = dict(st.get("event_attempt_days") or {})
    days = list(day_map.get(key) or [])
    if prints_seen.get(key) is None:
        # **A CHANGED DEFINITION DOES NOT INHERIT ITS OLD VALUES [item 64's rule, twice
        # over].** `event_attempts` counted cycles and `event_progress` stored a float total;
        # both were written under rules this one replaces, so neither is evidence about trading
        # days and neither is read. Item 64's fourth real cycle read 5 of 5 while the book
        # advanced 72 -> 77, one cycle from stopping a healthy rebalance on a number that meant
        # something else when it was written.
        days = []
    elif fp != prints_seen[key]:
        days = []                           # it advanced: the retry is working
    prints_seen[key] = fp
    st["event_fingerprint"] = prints_seen
    if counts_a_day:
        days = SETTLE.note_trading_day(days, on_date or _stamp())
    day_map[key] = days
    st["event_attempt_days"] = day_map
    out["attempts_without_progress"] = len(days)
    out["attempt_days"] = list(days)
    out["attempts_counted_in"] = "trading days"
    out["attempt_day_counted"] = bool(counts_a_day)
    done = len(days) > SETTLE.MAX_EVENT_TRADING_DAYS
    return {"exhausted": done, "days": list(days),
            "reason": (("this slot has attempted %s on %d separate TRADING DAYS (%s onward) "
                        "with NO change in what it holds, and stops trying; something is "
                        "rejecting these orders or leaving them unfillable, and a daily retry "
                        "would be deduped into silence" % (key, len(days), days[0]))
                       if done else "")}


def book_vs_record(book: dict, held_by_slot: dict, plan: dict, resting=None,
                   marks: dict = None) -> dict:
    """Which of the book's HELD names this slot does not hold, and why. [item 72]

    Read-only, and it answers the auditor's question -- *"why does the paper slot hold 82 names
    and not the book's full count?"* -- on every cycle instead of once.

    **THE RECORD IS A FILL COUNT.** `reconcile` builds `holdings` from this slot's own FILLED
    orders, deliberately: a record built from submissions is what made the duplicate buy-in
    reachable (item 63). So "the book holds it and the record does not" has five possible
    causes, and before this two of them were reported nowhere.

    Each name gets EXACTLY ONE reason, tested most-specific first:

      planned_this_cycle   an order for it is in this cycle's plan
      resting              one of this slot's orders for it is working at the broker
      skipped              the planner could not plan it (no usable mark; unknown resting qty)
      dust                 the gap is under `min_order_value`, so no order is worth sending
      unfilled_or_rejected ordered before and never filled, OR never accepted by the account

    **THE LAST CLASS IS TWO THINGS AND SAYS SO.** An order the broker rejected outright leaves
    nothing in the orders list, so this cycle cannot tell it from a limit that never filled.
    Naming one of them would be a guess; `fractional_report` and the `attempts` log are where a
    reader separates them.
    """
    held = [str((q or {}).get("ticker") or "").strip().upper()
            for q in ((book or {}).get("positions") or [])
            if (q or {}).get("status") == "held"
            and (LS._f((q or {}).get("weight")) or 0.0) > 0]
    held = [t for t in held if t]
    have = {str(k).upper() for k, v in (held_by_slot or {}).items()
            if (LS._f(v) or 0.0) > 0}
    planned = {str(o.get("ticker") or "").upper() for o in ((plan or {}).get("orders") or [])}
    skipped = {str(x.get("ticker") or "").upper(): str(x.get("reason") or "")
               for x in ((plan or {}).get("skipped") or [])}
    dusty = {str(x.get("ticker") or "").upper(): x
             for x in ((plan or {}).get("dust") or [])}
    rest = {str((r or {}).get("ticker") or "").upper() for r in (resting or [])}
    rows = []
    for t in sorted(set(held) - have):
        if t in planned:
            rows.append({"ticker": t, "why": "planned_this_cycle"})
        elif t in rest:
            rows.append({"ticker": t, "why": "resting",
                         "detail": "an order of this slot's is working at the broker"})
        elif t in skipped:
            rows.append({"ticker": t, "why": "skipped", "detail": skipped[t]})
        elif t in dusty:
            rows.append({"ticker": t, "why": "dust",
                         "detail": ("the gap is %.4f, under the %.2f minimum order value, so "
                                    "no order is worth sending"
                                    % (dusty[t].get("gap_value") or 0.0,
                                       dusty[t].get("min_order_value") or 0.0))})
        else:
            rows.append({"ticker": t, "why": "unfilled_or_rejected",
                         "detail": ("this slot ordered it on an earlier cycle and the order "
                                    "never filled, OR the broker never accepted it -- a "
                                    "rejected order leaves nothing in the orders list, so this "
                                    "cycle cannot tell the two apart. `fractional_report` and "
                                    "the `attempts` log separate them.")})
    from collections import Counter
    return {
        "n_book_held": len(set(held)),
        "n_recorded": len(have),
        "n_not_held": len(rows),
        "not_held": rows[:60],
        "by_reason": dict(Counter(r["why"] for r in rows)),
        "note": ("the record is a FILL count, not a selection count: `reconcile` builds it "
                 "from this slot's own FILLED orders, so a name whose limit never filled is "
                 "simply absent. This names every held book name the record does not have, "
                 "with the reason this cycle actually has."),
    }


def run_slot(slot, *, pct, armed_state: dict, book: dict, client, equity,
             marks: dict, root: str = None, session_ok: bool = True,
             paper_targets: dict = None, paper_value: float = None,
             account_id=None, account=None, settlement_report=None,
             fractional=None, send: bool = True, sess_reason: str = "",
             may_write: bool = True, sell_only: bool = False) -> dict:
    """One slot's cycle. Returns what it did and why. NEVER RAISES.

    `account` is the broker's whole account reply, not only its equity: item 67 sizes buys
    from what the broker reports as spendable WITHOUT BORROWING, and that figure
    (`non_marginable_buying_power`) lives in the same reply the equity came from. Absent, no
    buy is sized and none is sent -- the refusing direction.

    `send=False` is what 0% and an out-of-session cycle use: everything is computed and logged
    and nothing is transmitted. It is not a "dry run flag" a caller could forget to set — the
    caller that would arm a slot has to pass `send=True` AND hold a live client, and `armed`
    is the only function that licenses either.

    `may_write=False` is what a GET uses: the plan is computed and reported and **the record is
    left exactly as it was** [item 71, blocker C]. Separate from `send` because they are
    separate permissions -- a dry POST may write what it learned and must transmit nothing.

    `sell_only=True` is the X->0 WIND-DOWN [item 71, blocker A]. Every buy is withheld and
    reported; the sales are of what this slot's own record holds, which is the only thing a 0%
    target can license. It comes from `armed`, which is the only function that may say yes.
    """
    out = {"slot": str(slot), "pct": pct, "armed": bool(armed_state.get("armed")),
           "event": "none", "acted": False, "orders": [], "sent": [], "alerts": [],
           "preflight": None, "parity": None, "reason": "",
           # DECLARED ON EVERY CYCLE [item 71], so a reader never has to tell `False`
           # from "the key is absent" -- the distinction this path has paid for six times.
           "event_closed": False, "sell_only": bool(sell_only), "writes_allowed": None,
           "session_ok": bool(session_ok)}
    st = read_state(slot, root)
    st["slot"] = str(slot)
    # **MEASURED ON THE RECORD AS READ, BEFORE ANYTHING IS WRITTEN TO IT [item 67].** My first
    # cut computed this further down, AFTER the account-id pin had stamped `st["account_id"]`
    # -- so the id written by THIS cycle made a brand-new record look as though it had acted
    # before, and the check could never fire on a real first cycle. Caught by its own test
    # transmitting a full buy-in on top of a held account.
    record_is_fresh = not ((st.get("holdings") or {}) or (st.get("processed") or [])
                           or str(st.get("account_id") or "").strip()
                           or (st.get("intent") or {})
                           # **AND "I ALREADY ASKED" COUNTS AS HAVING ACTED**, or the refusal
                           # below repeats for ever and bricks a slot whose record was lost --
                           # which also blocks the self-healing route `reconcile` provides.
                           # The auditor's wording is "refusing ONCE".
                           or (st.get("fresh_record_refusal") or {}))
    try:
        # WHICH ACCOUNT DID THESE KEYS RESOLVE TO? [item 63, auditor's strengthening to Q3]
        #
        # The host check is strong -- `assert_live_host` requires exactly
        # `api.alpaca.markets`, it is a module constant, and no caller can supply a host -- but
        # it structurally cannot see the real residual risk: THE WRONG KEYS BEHIND THE RIGHT
        # HOST. Paper credentials pasted into `ALPACA_ACCOUNT_1_*`, or slot 2's keys into slot
        # 1, authenticate perfectly well. Alpaca then happily reports a different account under
        # slot 1's record, and slot 1's record is what decides what to sell.
        #
        # So the id is recorded on the first armed cycle and PINNED thereafter. A swapped key
        # pair becomes a refusal instead of a slot trading an account it has no record of.
        acct_id = (str(account_id).strip() or None) if account_id is not None else None
        if acct_id:
            known = str(st.get("account_id") or "").strip()
            if known and known != acct_id:
                out["alerts"].append({
                    "kind": "account_changed", "slot": str(slot),
                    "reason": ("this slot's keys now resolve to account %s and its record was "
                               "built on account %s; the keys have been swapped or re-pointed, "
                               "so it sends nothing and nothing is overwritten"
                               % (acct_id, known))})
                out["reason"] = out["alerts"][-1]["reason"]
                out["account_id"] = acct_id
                out["account_id_of_record"] = known
                return out
            if not known:
                st["account_id"] = acct_id
            out["account_id"] = acct_id
        # **WHETHER THE PIN ENGAGED, REPORTED EITHER WAY [item 65, the auditor's note 2].**
        # `if acct_id:` skips the whole block, so a 200 carrying an equity and no `id` left the
        # slot unpinned with NOTHING SAYING SO. It cannot cause a send by itself -- an
        # unreadable account also costs the equity, which preflight refuses on -- but an
        # unpinned slot is exactly the state the pin exists to prevent, and silence is how it
        # would be discovered later rather than now.
        out["account_id_recorded"] = bool(acct_id)
        if not acct_id:
            out["account_id_note"] = (
                "this cycle recorded no account id, so the slot is NOT pinned to an account: "
                "the broker's reply carried no `id`, or no id was supplied to this call. A "
                "swapped key pair would not be caught while that is true.")
        # **THE ACCOUNT'S OWN SETTLEMENT AND FRACTIONAL REPORT, RECORDED [item 67 part 2].**
        # Written here because `run_slot` is what writes this slot's record, and read by
        # `/admin/live-slots` -- which must not construct a live client of its own, because
        # item 58 pins that there is exactly one construction site and it is gated.
        if settlement_report:
            st["settlement_report"] = dict(settlement_report, read_at=_stamp())
            out["settlement_report"] = st["settlement_report"]
        # **AND THE BOOK'S FRACTIONABLE CENSUS, on whichever slot read it.** Recorded for the
        # same reason: `/admin/live-slots` must construct no client, so what it shows has to
        # have been written by something that legitimately holds one.
        if fractional:
            st["fractional_report"] = dict(fractional, read_at=_stamp())
            out["fractional_report"] = st["fractional_report"]

        held = [q for q in ((book or {}).get("positions") or [])
                if q.get("status") == "held"]

        # RECONCILE FIRST. What the slot holds is a fact about its FILLS, and the plan below
        # is the difference between the targets and that. Without this the plan is the full
        # buy-in on every cycle -- which is exactly what my own second-cycle test caught.
        rec = reconcile(client, st)
        out["reconcile"] = rec
        # **ONE GATE, READ ONCE, REPORTED ON EVERY CYCLE [item 71, blocker C].** Eight write
        # sites follow; a condition per branch would be eight chances to miss one.
        _w = writes_allowed(rec, may_write=may_write)
        out["writes_allowed"] = bool(_w["ok"])
        if not _w["ok"]:
            out["writes_withheld_reason"] = _w["reason"]

        def _write():
            """THE ONLY PATH FROM `run_slot` TO `write_state` [item 71, blocker C].

            A gate per branch would be one chance per branch to miss it, and there are eight.
            A `withheld` result is NOT a failure: `_note_write` reports it and does not alert,
            because a read-only cycle persisting nothing is the correct behaviour rather than a
            fault. A test asserts no second path to `write_state` exists in this function.
            """
            if not _w["ok"]:
                return {"ok": False, "withheld": True, "reason": _w["reason"]}
            return write_state(slot, st, root)
        if rec.get("order_read") in ("truncated", "failed"):
            # **"I DO NOT KNOW WHAT I HOLD" IS ONE STATE WITH TWO CAUSES, AND BOTH REFUSE.**
            # [item 65 -- the auditor's last blocker; item 63 refused only the truncated half]
            #
            # A full order page means the holdings TOTAL is wrong, and an under-counted holding
            # makes the planner buy the difference a second time. **A FAILED read is worse, not
            # milder**: `slot_symbols` is derived from this call's symbols, the recorded
            # holdings and the recorded intent, so when the state file is also gone all three
            # are empty, `preflight`'s reverse check runs with an EMPTY SCOPE, every broker
            # position is skipped, and a full buy-in transmits on top of a book the account
            # already holds. The auditor reproduced exactly that and all 236 tests passed
            # through it, because each supplied by hand the scope the production path derives.
            #
            # `not_attempted` is deliberately NOT here: that is a dry or paper-only cycle with
            # no client, which must still compute a plan and cannot send in any case.
            kind = ("reconcile_truncated" if rec.get("order_read") == "truncated"
                    else "order_read_failed")
            why = (rec.get("reason")
                   or "the broker's own orders could not be read, so this slot does not know "
                      "what it already holds")
            out["alerts"].append({"kind": kind, "slot": str(slot), "reason": why})
            out["reason"] = why
            return out
        if rec.get("ok"):
            st["holdings"] = rec["holdings"]
            # STEP 7. Only the PAPER slot feeds the measurement: the brief asks for the first
            # thirty PAPER fills, and pooling a live fill into it would mix two accounts'
            # executions into one figure about the free feed.
            if str(slot) == PAPER_SLOT:
                out["feed_gap"] = record_feed_gap(rec.get("fills") or [], root,
                                                  unfilled=rec.get("unfilled") or 0,
                                                  attempts=rec.get("n_orders") or 0)

        ev = LS.event_for(st, book, pct)
        ev["from_pct"] = st.get("last_pct")
        key = event_key(ev, book, pct)

        # AN UNFILLED REMAINDER IS ITSELF A REASON TO ACT, and it is the third of the three
        # events rather than a fourth thing: §8a says an order unfilled by the close is
        # re-priced and re-sent each following cycle until that event's targets are met.
        #
        # IT CARRIES THE OPEN EVENT'S OWN KEY. The first cut keyed it `"none"`, which is never
        # recorded as processed -- so a remainder cycle could never recognise itself as done
        # and re-sent the whole plan every time.
        open_key = st.get("open_event") or ""
        remainder = bool(open_key)
        if not ev.get("act") and not remainder:
            out["reason"] = ev["reason"]
            return out
        if ev.get("act") and key in (st.get("processed") or []) and not remainder:
            # ALREADY DONE AND NOTHING LEFT OPEN. A restart, a retry or a manual dispatch must
            # not repeat an order.
            out["event"] = ev["event"]
            out["reason"] = ("this slot has already processed %s, so it does nothing; a "
                             "restart never repeats an order" % key)
            return out
        if not ev.get("act"):
            key = open_key
        out["event"] = ev["event"] if ev.get("act") else "remainder"
        out["event_key"] = key

        # THE BROKER'S OWN POSITIONS, so the record-versus-broker check is NOT VACUOUS. The
        # first cut passed `None` here, which made that check pass by having nothing to
        # compare -- and it is the check standing between a stale record and a sale of
        # something the slot does not hold. `MA21`'s converse: a guard that cannot fire.
        #
        # ABSENT IS NOT AGREEMENT. If the list cannot be read, `None` travels on and
        # `preflight` says so rather than reading silence as a match.
        # NO CLIENT IS NOT AN UNREADABLE LIST [item 63]. A dry or paper-only cycle builds no
        # live client, so there is nothing to read and the check is NOT SUPPLIED -- the slot is
        # computing a plan, not sending one, and without a client the send gate refuses anyway.
        # A client that EXISTS and whose positions cannot be read is the case that must refuse,
        # and `None` carries that. Collapsing the two is what made item 58b's own positive
        # control go red: an armed live slot in a PAPER cycle stopped computing a plan at all.
        # **`positions_result` WHERE IT EXISTS, AND THE SAME DEFECT WAS UNDER THIS LEG TOO
        # [item 65].** Item 63 made an unreadable position list refuse and detected
        # "unreadable" by the call RAISING -- which `AlpacaPaperBroker.positions()` never does,
        # because it returns `[]` on a failed request. So that refusal could not fire through
        # the real client either, and "the account holds nothing" and "the broker would not
        # tell me" were one value on the one input that says what the slot already owns.
        bpos = LS.POSITIONS_NOT_SUPPLIED
        if client is not None and hasattr(client, "positions_result"):
            try:
                res = client.positions_result() or {}
                if not res.get("ok"):
                    bpos = None
                else:
                    bpos = [{"ticker": str((p or {}).get("ticker")
                                           or (p or {}).get("symbol") or "").upper(),
                             "qty": LS._f((p or {}).get("qty"))}
                            for p in (res.get("data") or [])
                            if str((p or {}).get("ticker") or (p or {}).get("symbol") or "")]
            except Exception:                                           # noqa: BLE001
                bpos = None
        elif client is not None and hasattr(client, "positions"):
            try:
                raw = client.positions()
                rows = raw if isinstance(raw, list) else ((raw or {}).get("data") or [])
                bpos = []
                for p in rows or []:
                    sym = str((p or {}).get("ticker") or (p or {}).get("symbol") or "").upper()
                    if sym:
                        bpos.append({"ticker": sym, "qty": LS._f((p or {}).get("qty"))})
            except Exception:                                           # noqa: BLE001
                bpos = None
        out["broker_positions_read"] = (
            None if bpos is None else
            ("not_supplied" if bpos is LS.POSITIONS_NOT_SUPPLIED else len(bpos)))

        # THE NAMES THIS SLOT HAS ITSELF TOUCHED, for `preflight`'s reverse direction: its own
        # filled-or-not orders, plus whatever it RECORDED AN INTENT to order and may have sent
        # before a failed state write. Any broker position in one of these that the record does
        # not know about is the empty-record hole; a position in any other name is Don's own
        # and must never be refused on. [item 63]
        slot_symbols = sorted(set(rec.get("symbols") or [])
                              | {str(t).upper() for t in (st.get("holdings") or {})}
                              | {str(o.get("ticker") or "").upper()
                                 for o in ((st.get("intent") or {}).get("orders") or [])})
        out["slot_symbols"] = slot_symbols
        # HOW MANY OF THE NAMES IT WOULD TRADE COULD BE PRICED, AND WHETHER THE MARKET WAS
        # OPEN WHEN IT ASKED [item 63]. The first real paper cycle refused with "no usable
        # price for 26 name(s)" at 22:54 ET, and that message is identical at 10:40 ET while
        # meaning something entirely different: after hours it is the free IEX feed having no
        # resting two-sided quote for a mid-cap, and in-session it would be a finding about the
        # vendor's coverage of this book. A refusal a reader cannot attribute is a refusal
        # somebody eventually overrides.
        # **THE SAME POPULATION AS THE REFUSAL AND THE QUOTE LIST [item 69].** This read
        # `held` alone, so a cycle that could not price an exit reported "1 of 1 priced,
        # missing: none" -- a reassuring number measured on a set that excludes the case it
        # exists to catch, which is the definition of a vacuous check. It is also the line the
        # workflow's own summary prints, so the daily log read as a healthy quiet day.
        need = LS.tradable_names(book, st.get("holdings") or {})
        priced = [t for t in need
                  if LS._f((marks.get(t) or {}).get("mid")
                           if isinstance(marks.get(t), dict) else marks.get(t))]
        out["marks_coverage"] = {
            "n_needed": len(need), "n_priced": len(priced),
            "missing": sorted(set(need) - set(priced))[:40],
            # WHICH of the unpriced ones are EXITS, named separately: an unpriced buy waits
            # harmlessly, an unpriced exit leaves the slot holding a name the Index dropped.
            "missing_exits": sorted(
                set(need) - set(priced)
                - {str(q.get("ticker") or "").upper()
                   for q in ((book or {}).get("positions") or [])
                   if q.get("status") == "held"})[:40],
            "population": ("the book's held names PLUS this slot's own recorded holdings -- the "
                           "same set as the quote list and the refusal, because an EXIT is by "
                           "definition not in the book"),
            "session_open_when_asked": bool(session_ok),
            "note": ("the market was CLOSED when these quotes were requested, so a thin "
                     "two-sided quote feed is EXPECTED here and this is not evidence about "
                     "the vendor's coverage. Alpaca's free feed is IEX only and a resting "
                     "bid and ask is what a mid needs." if not session_ok else
                     "the market was OPEN when these quotes were requested, so any missing "
                     "name IS a finding about the free IEX feed's coverage of this book"),
        }

        # ---- EXITS: A HELD NAME THE BOOK NO LONGER WANTS GETS A TARGET OF ZERO --------
        #
        # **NOTHING SOLD AN EXITED NAME BEFORE THIS [item 67], and it has never fired because
        # the live path has run exactly ONE event.** `held` above filters the book to
        # `status == "held"` and `LS.targets` drops a zero weight, so an exited name reached
        # the planner in neither shape and was held for ever -- the event closing as "targets
        # met" while the slot still held it. The first book change in the live path's life is
        # the 2026-10-22 rebalance.
        #
        # **TWO SHAPES, because `book_in_force` produces two.** A mid-event exit stays in
        # `positions` as `status: "exited"` with weight 0; a name dropped at a REBALANCE
        # belongs to a different event's book and is absent from `positions` entirely. Both are
        # exits and only the first is visible in the book's own rows.
        #
        # The second shape reads this slot's OWN recorded holdings, which `reconcile` builds
        # from `valquo-<slot>-` prefixed orders and nothing else -- so it can never name a
        # position the slot did not buy. `order_plan` is deliberately NOT given this power:
        # item 58 pins that a name absent from its targets is not in its plan at all.
        exits, book_names = {}, set()
        for q in ((book or {}).get("positions") or []):
            nm = str((q or {}).get("ticker") or "").strip().upper()
            if not nm:
                continue
            book_names.add(nm)
            if q.get("status") != "held" or (LS._f(q.get("weight")) or 0.0) <= 0:
                exits[nm] = 0.0
        for nm, qty in (st.get("holdings") or {}).items():
            nm = str(nm).strip().upper()
            if nm and nm not in book_names and (LS._f(qty) or 0.0) > 0:
                exits[nm] = 0.0
        exits = {nm: 0.0 for nm in exits
                 if (LS._f((st.get("holdings") or {}).get(nm)) or 0.0) > 0}
        out["exits_planned"] = sorted(exits)

        # **BRAND NEW MEANS ALL FOUR MARKERS ABSENT [item 67, the auditor's recommendation
        # 2]**, and it was measured at the top of this function from the record as READ. Any
        # one marker present means this slot has acted before, so the ambiguity the check
        # exists for cannot be the explanation and it never fires again.
        out["record_is_fresh"] = bool(record_is_fresh)
        pf = LS.preflight(book=book, equity=equity, marks=marks,
                          slot_record=st.get("holdings") or {}, pct=pct,
                          broker_positions=bpos, slot_symbols=slot_symbols,
                          record_is_fresh=record_is_fresh)
        out["preflight"] = pf
        if not pf["ok"]:
            # NO ORDERS, PLUS AN ALERT. An error never causes a sale and never changes
            # holdings, so nothing below this line runs.
            out["alerts"].append({"kind": "preflight_failed", "slot": str(slot),
                                  "reason": pf["reason"]})
            out["reason"] = pf["reason"]
            # **A FRESH-RECORD REFUSAL IS RECORDED SO IT HAPPENS ONCE [item 67].** Writing
            # nothing left the record brand new, so the next cycle refused identically and the
            # slot was bricked -- and the route that heals a lost record, `reconcile` rebuilding
            # holdings from this slot's own fills, was blocked along with it. The marker says
            # "I asked", NOT "those positions are mine": the ambiguity is recorded rather than
            # resolved, and the next cycle runs the machinery that was already correct.
            if record_is_fresh and "brand new" in (pf.get("reason") or ""):
                st["fresh_record_refusal"] = {
                    "at": _stamp(),
                    "reason": pf["reason"],
                    "what_it_means": ("this slot refused ONE cycle because its record was "
                                      "brand new and the account was not empty. It does not "
                                      "claim those positions; it records that the question "
                                      "was asked, so the next cycle proceeds normally."),
                }
                _note_write(out, _write(), slot,
                            "recording the one-off fresh-record refusal")
                out["fresh_record_refusal_recorded"] = True
            return out

        tg = LS.targets(pct, equity, held)
        if not tg["ok"]:
            out["alerts"].append({"kind": "targets_failed", "slot": str(slot),
                                  "reason": tg["reason"]})
            out["reason"] = tg["reason"]
            return out
        # **THIS SLOT'S OWN RESTING ORDERS ARE PASSED IN [item 67 part 0].** Without them
        # the planner re-plans the whole remainder every cycle and the orders STACK -- the
        # auditor's third blocker. `rec["resting"]` is already filtered to this slot's own
        # `valquo-<slot>-` prefix by `reconcile`, so nothing here can reach Don's own orders.
        # The zero targets are attached where `tg` exists; the exits themselves were derived
        # above, before preflight, so `exits_planned` is reported even on a refusing cycle.
        tg["targets"] = dict(tg["targets"])
        for nm in exits:
            tg["targets"].setdefault(nm, 0.0)

        plan = LS.order_plan(tg["targets"], st.get("holdings") or {}, marks,
                             resting=(rec.get("resting") or []))
        out["orders"] = plan["orders"]
        out["skipped"] = plan["skipped"]
        out["deferred"] = []
        out["slot_value"] = tg["slot_value"]
        out["targets"] = tg["targets"]

        # THE TARGETS ARE MET: nothing left to do for this event, so it CLOSES.
        #
        # **AND IT TESTS FOR THAT OUTCOME BY NAME [item 69].** `not plan["orders"]` was true of
        # "nothing to do" AND of "something was skipped, so I could not work out what to do" --
        # so an exit the feed could not price closed the event with no alert, and
        # `marks_coverage` reported perfect coverage while it happened.
        #
        # **AND THE OUTCOME IS NOW COMPUTED WITH THIS EVENT'S RESTING ORDERS [item 70].** The
        # comment that used to sit here read: *"Recorded here rather than after sending, because
        # 'met' is a property of the reconciled holdings and not of whether this particular
        # cycle transmitted anything."* **That sentence was true when it was written and item 67
        # made it false** -- since the planner subtracts this slot's own resting same-side
        # quantity, an empty plan can mean "the gap is already covered by an order that has not
        # filled", and the reconciled holdings can be BBB: 0 against a target of 500 while this
        # branch reports the targets as met. It is deleted rather than softened, because the
        # auditor records nearly trusting it, and because six blockers on this path have been a
        # docstring asserting a property the code had lost.
        # **THE CENSUS THAT ANSWERS "WHY 82 OF 86" [item 72], computed where the plan and the
        # resting list both exist. Read-only: it decides nothing.
        try:
            out["book_vs_record"] = book_vs_record(
                book, st.get("holdings") or {}, plan,
                resting=(rec.get("resting") or []), marks=marks)
        except Exception as _ex:                                        # noqa: BLE001
            # A DIAGNOSTIC MUST NEVER COST THE CYCLE ITS ORDERS [item 67's rule for the
            # fractional report, applied again].
            out["book_vs_record"] = {"error": "%s: %s" % (type(_ex).__name__, _ex)}
        rest_mine = resting_for_event(rec.get("resting") or [], slot, key)
        out["resting_this_event"] = [dict(r) for r in rest_mine]
        # **`open_remainder` IS NOW READ [item 70, the auditor's non-blocking item 5].** It was
        # computed on every cycle and read nowhere. Both facts ship, because they are different:
        # `open_remainder` is "this slot has SOME order working" and `resting_this_event` is
        # "...for THIS event". An order left over from a previous event is a reason to subtract
        # (item 67) and NOT a reason to hold this event open, or every later rebalance would
        # stall behind an order nobody is waiting for.
        out["open_remainder"] = bool(rec.get("open_remainder"))
        outcome = plan_outcome(plan, resting=rest_mine)
        out["plan_outcome"] = outcome
        # **ANY SKIP IS ALERTED, WHATEVER THE OUTCOME [item 69].** The auditor's blocker is a
        # skip in the empty-plan branch going unannounced; a skip in the branch that DOES trade
        # went unannounced too -- `skipped` reached the ~35KB body and nothing else. One alert
        # here covers both, and the outcome below decides only whether anything is sent.
        if plan.get("skipped"):
            why = "; ".join("%s: %s" % (str(x.get("ticker")), str(x.get("reason")))
                            for x in (plan.get("skipped") or [])[:6])
            exits = sorted(set(out.get("exits_planned") or [])
                           & {str(x.get("ticker") or "").upper()
                              for x in (plan.get("skipped") or [])})
            out["skipped_alerted"] = True
            out["alerts"].append({
                "kind": ("exit_unpriced" if exits else "plan_incomplete"),
                "slot": str(slot),
                "reason": ("%d name(s) in %s could not be planned and are NOT traded this "
                           "cycle: %s.%s The event stays OPEN and the next cycle tries again."
                           % (len(plan.get("skipped") or []), key, why,
                              (" %s must be SOLD because the book no longer holds it, so the "
                               "slot is still holding a name the Index has dropped."
                               % ", ".join(exits)) if exits else ""))})
        if outcome == PLAN_BLOCKED:
            # **NO TRADE, AN ALERT, AND THE EVENT STAYS OPEN** -- §8's three clauses, of
            # which only the first used to happen. Every other broken input on this path
            # already behaves exactly this way; this one branch did not. The alert was raised
            # above, for any skip; this branch adds that nothing is being sent at all.
            out["reason"] = ("nothing could be planned for %s, so this slot sends NOTHING and "
                             "the event is NOT recorded as complete -- a plan with something "
                             "skipped is not a finished rebalance. %s"
                             % (key, out["alerts"][-1]["reason"]))
            out["skipped"] = plan["skipped"]
            # **AND THE EVENT NOW ACTUALLY STAYS OPEN [item 70, the auditor's second
            # instance].** This branch has always SAID *"The event stays OPEN and the next cycle
            # tries again"* and then written `last_event_date` -- the one field `event_for` keys
            # on -- without setting `open_event`, which is the one field the remainder path
            # reads. So the next cycle found no event and no remainder and returned early: one
            # alert, then silence, with the rebalance abandoned at half the target.
            #
            # The old comment claimed the write existed *"so a persistent block escalates
            # through the ceiling"*. It could not: the ceiling is 100 lines further down, this
            # branch returns before it, and what the ceiling counts is `event_attempt_days` and
            # not `last_event_date`. **So the escalation is now called rather than asserted**,
            # and WITHOUT counting a trading day, because this branch can run outside the orders
            # window and `note_trading_day`'s precondition is that every date reaching it is one
            # the window was open on.
            st["open_event"] = key
            st["last_event_date"] = (book or {}).get("formed_on")
            st["last_pct"] = pct
            blk = note_no_progress(st, out, key, counts_a_day=bool(session_ok))
            if blk["exhausted"]:
                out["alerts"].append({"kind": "event_attempts_exhausted", "slot": str(slot),
                                      "reason": blk["reason"]})
                out["attempts_exhausted"] = True
                # **AND AN EXHAUSTED EVENT CLOSES, or "stays open" becomes "stalls for ever".**
                # Keeping it open was the fix; keeping it open past the ceiling would replace a
                # silent close with a silent hold, and every later rebalance would queue behind
                # it. Don is told, which is the point of the ceiling.
                st["open_event"] = None
            _note_write(out, _write(), slot,
                        "recording an incomplete plan")
            return out
        if outcome == PLAN_RESTING:
            # **MY OWN ORDERS ARE STILL WORKING, SO THERE IS NOTHING TO SEND AND NOTHING IS
            # FINISHED [item 70].** The event stays open, so the next cycle re-prices whatever
            # is left once the `day` order has expired -- which is §8a's own rule, and the one
            # the close branch was skipping past.
            #
            # **IT CANNOT RE-STACK**, which is the thing that makes leaving it open safe: item
            # 67's subtraction still applies, so while the order works the plan stays empty and
            # this branch simply repeats. The moment it expires unfilled, `reconcile` stops
            # listing it, the planner sees the whole remainder again, and it is re-sent with a
            # fresh `coid` suffix.
            st["open_event"] = key
            # NOT `last_event_date`, and NOT `processed`: both are how an event is recorded as
            # DONE, and this one is not.
            rst = note_no_progress(st, out, key, counts_a_day=bool(session_ok))
            names = ", ".join(sorted({str(r.get("ticker")) for r in rest_mine}))
            out["reason"] = ("this slot has %d order(s) still working at the broker for %s "
                             "(%s), so there is nothing to send this cycle and the event is "
                             "NOT recorded as complete -- it stays open and the next cycle "
                             "re-prices whatever has not filled"
                             % (len(rest_mine), key, names))
            if rst["exhausted"]:
                # **NO ALERT WHILE THEY ARE FRESH, AN ALERT WHEN THEY NEVER FILL.** A `day`
                # limit at the mid routinely takes several cycles to work through 85 names --
                # the real book filled 81 of 85 after five cycles -- so alerting on a resting
                # order would alert on the designed behaviour, and an alert that fires on
                # healthy cycles is one nobody reads on the unhealthy one (`MA21`).
                out["alerts"].append({"kind": "event_attempts_exhausted", "slot": str(slot),
                                      "reason": rst["reason"]})
                out["attempts_exhausted"] = True
                out["reason"] = rst["reason"]
                st["open_event"] = None
            _note_write(out, _write(), slot,
                        "recording that this slot's own orders are still working")
            return out
        if outcome == PLAN_TARGETS_MET:
            # **THE CLOSE IS A DECISION AND IT NOW HAS A NAME [item 71].** `plan_outcome` is a
            # property of the PLAN; whether the event CLOSED is a property of the cycle, and a
            # reader -- or a table -- asking "did this close?" had to infer it from the state
            # file. It is also the honest answer in the one case blocker C created: a paper or
            # dry cycle for a live slot computes TARGETS_MET, persists nothing, and the event
            # stays open.
            # **AND THE OPEN REMAINDER MUST BE THIS EVENT'S [item 71, found by the
            # transition table].** The auditor's third condition in full. Blocker B stopped the
            # close from DISCARDING another event's remainder; it left the close free to record
            # ITSELF complete while that remainder was outstanding -- and the plan it read as
            # "targets met" was empty only because the OTHER event's resting orders had been
            # subtracted from it. "Something else is on its way to meeting my targets" is not
            # "my targets are met".
            # **AND "ANOTHER EVENT IS OPEN" IS TWO STATES, WHICH IS MY OWN DEFECT FROM ITEM
            # 71 [item 72, the auditor's seventh review].** That item wrote one reason for
            # both: *"...is still open with orders of this slot's working at the broker"*. It
            # is true when something IS resting for that event and false when nothing is --
            # which is the state every real event is in the morning after its `day` orders
            # expired. `open_remainder: False` sat in the same payload as that sentence, and
            # the branch returned before the ceiling so it could not escalate. The paper slot
            # is in this state today.
            _open = str(st.get("open_event") or "")
            _other = _open not in ("", key)
            _other_resting = (resting_for_event(rec.get("resting") or [], slot, _open)
                              if _other else [])
            _stale = bool(_other and not _other_resting)
            out["open_event_of_record"] = _open or None
            out["open_event_is_stale"] = _stale
            out["event_closed"] = bool(_w["ok"] and not (_other and not _stale))
            if _w["ok"] and _other and not _stale:
                # GENUINELY OUTSTANDING: orders of this slot's really are working for that
                # event, so the empty plan means they cover the gap. The sentence is true here.
                out["reason"] = (
                    "this event's plan is empty, but %s is still open with %d order(s) of this "
                    "slot's working at the broker -- so the empty plan means that event's "
                    "orders cover the gap rather than that THIS event is finished. Nothing is "
                    "sent and nothing is recorded as complete; the open event resolves first."
                    % (_open, len(_other_resting)))
                out["blocked_by_open_event"] = _open
                # **AND IT REACHES THE CEILING NOW**, like the resting and blocked branches.
                # A branch that holds an event open and cannot escalate is item 70's own
                # silent hold. A day is counted only in session, because
                # `note_trading_day`'s precondition is that every date reaching it is one the
                # orders window was open on.
                _blk = note_no_progress(st, out, key, counts_a_day=bool(session_ok))
                if _blk["exhausted"]:
                    out["alerts"].append({"kind": "event_attempts_exhausted",
                                          "slot": str(slot), "reason": _blk["reason"]})
                    out["attempts_exhausted"] = True
                    st["open_event"] = None
                _note_write(out, _write(), slot, "recording a blocked event")
                return out
            if _w["ok"] and _stale:
                # **STALE: CLEARED RATHER THAN REFUSED ON FOR EVER.** Nothing of this slot's is
                # working for that event, and this event's plan is empty -- the holdings already
                # meet its targets -- so the old key is moot and the next reader would trust it.
                #
                # **AND WHETHER IT WAS EVER COMPLETED IS A DIFFERENT FACT.** Only the SEND path
                # appends to `processed` before setting `open_event`, so a stale key IN
                # `processed` is residue from orders that expired, and one NOT in `processed`
                # was left by `PLAN_BLOCKED` or `PLAN_RESTING` and never completed at all. The
                # second is worth telling Don about; the first is bookkeeping.
                _was_processed = _open in (st.get("processed") or [])
                st["open_event"] = None
                for bag in EVENT_SCOPED_STATE:
                    if isinstance(st.get(bag), dict):
                        st[bag] = {k: v for k, v in st[bag].items() if k != _open}
                if (st.get("intent") or {}).get("event") == _open:
                    st["intent"] = None
                out["cleared_stale_open_event"] = {
                    "event": _open, "was_recorded_complete": _was_processed}
                if not _was_processed:
                    out["alerts"].append({
                        "kind": "stale_open_event_never_completed", "slot": str(slot),
                        "reason": ("%s was left open and has NO order of this slot's working "
                                   "at the broker, and it was never recorded complete -- so it "
                                   "was planned and never finished. It is cleared, because this "
                                   "slot's holdings now meet %s's targets and the old key would "
                                   "otherwise be refused on for ever." % (_open, key))})
            if not _w["ok"]:
                # The branch reached here and changed nothing. Saying so is the whole point:
                # the old text read "the event is closed", which would have been the EIGHTH
                # message on this path claiming a property the code does not have -- written by
                # the item fixing the other seven.
                out["reason"] = ("this event's targets are met in this slot's record and "
                                 "NOTHING is recorded: %s" % _w["reason"])
                return out
            if key and key != "none" and key not in st["processed"]:
                st["processed"].append(key)
            # **ONLY IF IT IS THIS EVENT'S [item 71, the auditor's blocker B].** This ran
            # unconditionally, and `open_event` can belong to a DIFFERENT event: the buy-in is
            # sent and unfilled, Don sets 0% in the same session, and the sell-out's targets
            # genuinely ARE met at that instant -- the record holds nothing yet -- so it closed
            # and took the REBALANCE's remainder with it. The resting buys then filled and the
            # account was fully invested at a declared 0%, both events recorded complete, no
            # alert, and the slot's own record wrong as well as its position.
            #
            # It fires on a live slot too, because this branch sits BEFORE the parity gate --
            # and before item 71's wind-down that slot could then never sell.
            if st.get("open_event") == key:
                st["open_event"] = None
            # **`intent` IS CLEARED BY ITS OWN EVENT KEY [item 72], which is a different
            # condition from `open_event`'s and item 71 made them one.** Before item 71 both
            # were unconditional; item 71 put both behind `open_event == key`, which is right
            # for the remainder marker and wrong for `intent` -- `intent` carries the event it
            # belongs to, and a close with `open_event` already cleared (reachable via the
            # stale-event path) left it behind. Residue rather than a hazard, since its tickers
            # only ever widen `slot_symbols` and so make preflight check MORE names.
            if (st.get("intent") or {}).get("event") == key:
                st["intent"] = None      # the event is finished; nothing is outstanding
            # AND ITS COUNTERS GO WITH IT [item 64]. A closed event's attempt count is not
            # evidence about the next one, and leaving it behind means a slot that needed four
            # cycles once starts the following rebalance with four attempts already spent.
            # `event_fingerprint`, `event_attempt_days` and `awaiting_settlement` are item
            # 67's and belong on this list for the same reason as the rest: a finished event's
            # wait is not evidence about the next one, and a stale wait record would alert.
            for bag in EVENT_SCOPED_STATE:
                if isinstance(st.get(bag), dict):
                    st[bag] = {k: v for k, v in st[bag].items() if k != key}
            st["last_event_date"] = (book or {}).get("formed_on")
            st["last_pct"] = pct
            _note_write(out, _write(), slot, "closing the event")
            out["reason"] = ("this event's targets are already met, so there is nothing to "
                             "send and the event is closed")
            return out
        # Every other outcome leaves it open, stated once rather than per branch so a new
        # outcome cannot default to "closed" by omission.

        # ---- PARITY, AND FOR A LIVE SLOT IT BLOCKS [item 63, auditor question 2] ---------
        #
        # §8 requires the dry run diffed against the paper book BEFORE that slot's first real
        # order. The first cut alerted and sent anyway, and could skip the comparison entirely
        # whenever the paper side was down -- so the one cycle with no comparison was the cycle
        # most likely to need one. Both are refusals now, for a LIVE slot only: the paper slot
        # has nothing to be compared against and gating it would stop the very mechanism that
        # produces the comparison.
        is_live_slot = (str(slot) != PAPER_SLOT)
        if paper_targets is not None:
            out["parity"] = parity(tg["targets"], paper_targets,
                                   live_value=tg["slot_value"], paper_value=paper_value)
            if not out["parity"]["ok"]:
                out["alerts"].append({"kind": "parity_mismatch", "slot": str(slot),
                                      "reason": out["parity"]["reason"]})
                if is_live_slot:
                    out["reason"] = ("this slot's target weights do not match the paper "
                                     "book's, so it sends NOTHING this cycle: %s"
                                     % out["parity"]["reason"])
                    return out
        elif is_live_slot and sell_only:
            # **THE WIND-DOWN NEEDS NO COMPARISON, SO AN ABSENT ONE CANNOT BLOCK IT [item 71].**
            # This is the FOURTH gate on the sell-out and nobody had named it: fixing `armed`
            # and parity's zero-target case still left a live slot unable to get out on any day
            # the paper book was unavailable.
            #
            # It is not a weakening of `C5`. The comparison exists to show that a live slot's
            # TARGET WEIGHTS reproduce the paper book's, and a wind-down has no weights -- every
            # target is zero and the orders are sales of what this slot's own record holds.
            # **The paper slot runs at `PAPER_PCT = 100`, so its targets are never zero**: the
            # evidence this branch waits for cannot exist for this event, and waiting for
            # evidence that cannot exist is a refusal with no condition that lifts it.
            out["parity"] = {"ok": True, "measured": False,
                             "reason": ("this slot is winding down at 0%, so there are no "
                                        "target weights to diff against the paper book and "
                                        "parity is VACUOUS. The sales are of what this slot's "
                                        "own record holds, which no comparison could check.")}
            out["alerts"].append({"kind": "parity_vacuous_wind_down", "slot": str(slot),
                                  "reason": out["parity"]["reason"]})
        elif is_live_slot:
            # ABSENT IS NOT A PASS (`C5`). A live slot with no paper comparison available does
            # not send -- it is §8's precondition, not a nice-to-have. **Unchanged for every
            # event that HAS weights**, which is every event but the wind-down above.
            out["parity"] = {"ok": False, "measured": False,
                             "reason": ("no paper book was available to diff against this "
                                        "cycle, so parity is UNMEASURED")}
            out["alerts"].append({"kind": "parity_absent", "slot": str(slot),
                                  "reason": out["parity"]["reason"]})
            out["reason"] = ("parity against the paper book could not be computed, so this "
                             "slot sends NOTHING this cycle")
            return out

        if not (out["armed"] and send and session_ok and client is not None):
            out["reason"] = ("computed %d order(s) and sent none: %s"
                             % (len(plan["orders"]),
                                armed_state.get("reason") if not out["armed"] else
                                ((sess_reason or "the market is not open for orders")
                                 if not session_ok else "no client was supplied")))
            return out

        # ---- THE CEILING COUNTS ATTEMPTS THAT MADE NO PROGRESS [item 63 #11, fixed item 64]
        #
        # **ITEM 63 COUNTED CYCLES THAT ACTED, WHICH IS A DIFFERENT QUANTITY AND WOULD HAVE
        # MISFIRED ON THE REAL REBALANCE.** Measured on the live paper book: cycle 1 bought in,
        # cycle 2 hit the duplicate-id failure, cycle 3 sent 69 and holdings went 59 -> 72
        # filled. That event had used three of five attempts while FILLING NORMALLY -- a `day`
        # limit at the mid genuinely takes several cycles to work through 85 names -- so a
        # rebalance behaving exactly as §8a designs it would have stopped and alerted. A false
        # alarm on Don's first real rebalance is the cheapest possible way to teach him to
        # ignore this alert, which is the outcome the ceiling exists to prevent.
        #
        # The auditor's condition is a PERMANENTLY-rejecting one, so the counter resets on
        # progress and the ceiling means what it says: this event has not advanced in N
        # consecutive cycles. **PROGRESS IS MEASURED ON THE HOLDINGS, NOT THE ORDER COUNT**,
        # because `reconcile` builds holdings from FILLS -- so it cannot be fooled by orders
        # that are accepted and never fill, which is exactly what an unfillable limit or a
        # permanent rejection produces.
        # **THE CEILING COUNTS TRADING DAYS, NOT CYCLES [item 67, and it is item 64's own
        # false-alarm family one turn later].** Item 64 fixed this counter to mean "consecutive
        # cycles with no advance" -- and then added four backup schedules, so there are now up
        # to five scheduled cycles a day plus any manual ones. A five-CYCLE ceiling can be spent
        # inside a single morning by a rebalance behaving exactly as designed, which is the
        # false alarm item 64 existed to remove, reintroduced by item 64. Counting DISTINCT
        # DATES makes the ceiling mean what its own message says, and every date here is a
        # trading day by construction because a cycle only transmits inside the orders window.
        #
        # **AND PROGRESS IS A CHANGE IN THE HOLDINGS, NOT AN INCREASE.** The old test was
        # `held_now > baseline`, which a SELL can never satisfy -- so the sell leg of a
        # rebalance registered as no progress, and under item 67 the sells go first. A
        # fingerprint of the whole holdings map also catches a sell and a buy that happen to
        # net to the same total.
        # **ONE DEFINITION, THREE CALLERS [item 70].** The send path, the resting branch and
        # the blocked branch all need this, and the two new ones used to be unable to reach it
        # at all -- the blocked branch's own comment claimed it escalated through the ceiling
        # from 100 lines above it. A second copy of a counter whose reset rules took two items
        # to get right would be a second set of reset rules (`B7`).
        ceil = note_no_progress(st, out, key, counts_a_day=True)
        if ceil["exhausted"]:
            out["alerts"].append({"kind": "event_attempts_exhausted", "slot": str(slot),
                                  "reason": ceil["reason"]})
            out["reason"] = ceil["reason"]
            out["attempts_exhausted"] = True
            # The day is recorded even on the refusing branch, or the count would stop rising
            # and the alert would re-fire identically for ever instead of once. `note_no_progress`
            # has already written it into `st`.
            _note_write(out, _write(), slot, "recording the stopped event")
            return out

        # **A SEPARATE, MONOTONE COUNTER FOR THE ORDER ID [item 64].** The attempt counter was
        # doing both jobs and they have OPPOSITE requirements: the ceiling must RESET when the
        # book advances, or a healthy rebalance stops itself; the id suffix must NEVER reset, or
        # it reproduces an id Alpaca has already accepted. The fifth real cycle sent 22 orders
        # that came back "client_order_id must be unique" because the ceiling's reset had taken
        # the suffix back to `a1`. This one only ever increases while the event is open.
        seqs = dict(st.get("send_seq") or {})
        seqs[key] = int(seqs.get(key) or 0) + 1
        st["send_seq"] = seqs
        send_seq = seqs[key]
        out["send_seq"] = send_seq

        # ---- SIZE THE BUYS TO WHAT CAN BE SPENT WITHOUT BORROWING [item 67 part 1] -------
        #
        # The orders arrive sells-first from `order_plan`. Buys are then taken in that order
        # until the broker's own no-borrow figure is used up, and the rest are DEFERRED -- not
        # cancelled, not retried harder. A deferred buy is a SETTLEMENT WAIT: the sells stand,
        # the event stays OPEN, and the next trading day's cycles send the remainder once the
        # proceeds are spendable.
        #
        # **`to_send` IS A DIFFERENT LIST FROM `plan["orders"]`, AND THAT IS THE WHOLE POINT.**
        # `plan["orders"]` is what the event still needs and is what decides whether the
        # targets are met; this is what this cycle may transmit. My first cut filtered the plan
        # itself, and a fully-deferred rebalance then recorded itself as FINISHED.
        #
        # **IT IS NOT A SETTLEMENT MODEL AND MUST NOT BECOME ONE.** It asks the broker what is
        # available and sizes to that, so an account whose proceeds are immediately spendable --
        # which Alpaca says a limited-margin IRA's are -- never waits at all.
        budget = SETTLE.spendable(account) if account is not None else {
            "ok": False, "amount": None, "field": None,
            "reason": ("no account reply was supplied to this cycle, so nothing bounds a buy "
                       "and none is sized")}
        out["budget"] = budget
        to_send, deferred, spent = [], [], 0.0
        # **A WIND-DOWN TRANSMITS NO BUY [item 71, blocker A].** `sell_only` comes from
        # `armed`, the only function that may say yes, and it is set only when the percentage
        # is zero AND this slot's own record still holds something. Every target is therefore
        # zero and `order_plan` should produce sales alone -- "should" is not a safety property
        # when the thing being prevented is spending real money in an account its owner has
        # just told to hold nothing.
        withheld_buys = []
        if sell_only:
            keep = []
            for o in plan["orders"]:
                if str(o["side"]).lower() == "buy":
                    withheld_buys.append(dict(o, why=("this slot is winding down at 0%, so no "
                                                      "buy is transmitted")))
                else:
                    keep.append(o)
            plan = dict(plan, orders=keep)
            out["orders"] = keep
            if withheld_buys:
                # It should be unreachable, so if it fires a reader needs to know rather than
                # find a quiet list in a 35KB body.
                out["alerts"].append({
                    "kind": "buy_withheld_in_wind_down", "slot": str(slot),
                    "reason": ("%d buy order(s) were planned for a slot at 0%% and are NOT "
                               "transmitted: %s. A 0%% target licenses sales only, so this is "
                               "a defect in the planner rather than a decision."
                               % (len(withheld_buys),
                                  ", ".join(str(o.get("ticker")) for o in withheld_buys)))})
        out["withheld_buys"] = withheld_buys
        out["sell_only"] = bool(sell_only)
        for o in plan["orders"]:
            if str(o["side"]).lower() == "sell":
                to_send.append(o)               # a sell RAISES cash; no budget binds it
                continue
            cost = float(o["qty"]) * float(o["limit_price"])
            if not budget.get("ok"):
                deferred.append(dict(o, why="no spendable figure was reported"))
            elif spent + cost > float(budget["amount"]) + 1e-9:
                deferred.append(dict(o, why=("would spend %.2f of the %.2f available without "
                                             "borrowing" % (spent + cost, budget["amount"]))))
            else:
                spent += cost
                to_send.append(o)
        out["deferred"] = deferred
        out["buy_cost_planned"] = round(spent, 2)
        out["will_send"] = [dict(o) for o in to_send]

        if not to_send:
            # **NOTHING IS SPENDABLE, SO NOTHING IS TRANSMITTED AND THE EVENT STAYS OPEN.**
            # The intent is deliberately NOT overwritten: it is one of the three sources
            # `preflight` derives its scope from, and replacing a real intent with an empty one
            # narrows that scope -- the unsafe direction, and the shape of item 63's blocker 2.
            waits = dict(st.get("awaiting_settlement") or {})
            w = SETTLE.wait_state(list((waits.get(key) or {}).get("days") or []),
                                  on_date=_stamp())
            waits[key] = {"days": w["days"], "since": w["since"],
                          "n_orders": len(deferred)}
            st["awaiting_settlement"] = waits
            out["awaiting_settlement"] = dict(w, n_orders=len(deferred))
            if w["alert"]:
                out["alerts"].append({"kind": "settlement_wait_overdue", "slot": str(slot),
                                      "reason": w["reason"]})
            _note_write(out, _write(), slot, "recording the wait")
            out["reason"] = ("%d buy(s) for %s await cash that can be spent without "
                             "borrowing (%s); the event stays open and the next trading day's "
                             "cycles re-send them" % (len(deferred), key,
                                                      budget.get("reason")))
            return out

        # ---- THE INTENT IS WRITTEN BEFORE ANYTHING IS SENT [item 63, blocker 2] ----------
        #
        # The third fact in the auditor's duplicate buy-in: `write_state`'s result was
        # DISCARDED at both call sites, so a failed write after the orders had gone produced
        # exactly the empty record that makes the next cycle plan the whole buy-in again.
        # Writing first inverts the failure: if the disk is unwritable the slot refuses BEFORE
        # transmitting, and if it is writable then evidence of the attempt survives the send
        # whatever happens next.
        st["intent"] = {"event": key, "at": _stamp(),
                        "orders": [{"ticker": o["ticker"], "side": o["side"], "qty": o["qty"],
                                    "limit_price": o["limit_price"]} for o in to_send]}
        w = _write()
        if not w.get("ok"):
            out["alerts"].append({
                "kind": "state_write_failed", "slot": str(slot),
                "reason": ("the slot's own record could not be written, so it sends NOTHING: "
                           "%s. An order sent without a record of it is how a position gets "
                           "bought twice." % w.get("reason"))})
            out["reason"] = out["alerts"][-1]["reason"]
            return out

        # ---- the only place an order is transmitted -------------------------------------
        resting = list((rec.get("resting") or []))
        out["cancelled"], out["blocked_by_cancel"] = [], []
        for o in to_send:
            # **CLEAR A RESTING ORDER ON THE OPPOSITE SIDE FIRST, OR ALPACA REFUSES THIS ONE.**
            # [item 65] *"Potential wash trade detected. Use complex orders."* -- and complex
            # orders are forbidden here, so the obstruction is cleared instead. Only this slot's
            # own orders are ever cancelled: `reconcile` filtered by the `valquo-<slot>-` prefix
            # before recording them.
            blocked = False
            for rst in [r for r in resting
                        if r["ticker"] == o["ticker"] and r["side"] != str(o["side"]).lower()]:
                res = {"ok": False, "detail": "no cancel method on this client"}
                if hasattr(client, "cancel"):
                    try:
                        res = client.cancel(rst["id"]) or {}
                    except Exception as e:                              # noqa: BLE001
                        res = {"ok": False, "detail": "%s: %s" % (type(e).__name__, e)}
                if res.get("ok"):
                    out["cancelled"].append(dict(rst, why="opposite side of a planned order"))
                    resting = [r for r in resting if r["id"] != rst["id"]]
                else:
                    # **AN UNCONFIRMED CANCEL MEANS THIS NAME DOES NOT TRADE.** A cancel that
                    # silently failed leaves the opposite order resting, so the new order is
                    # refused anyway -- and the slot would believe it had cleared the way. §8's
                    # rule: a broken input stops THAT trade and alerts. The other names are not
                    # broken and still trade.
                    blocked = True
                    out["blocked_by_cancel"].append({"ticker": o["ticker"],
                                                     "order_id": rst["id"]})
                    out["alerts"].append({
                        "kind": "cancel_unconfirmed", "slot": str(slot),
                        "reason": ("%s has an order resting on the %s side that could not be "
                                   "cancelled (%s), so %s does not trade this cycle; Alpaca "
                                   "refuses a new order on the opposite side as a potential "
                                   "wash trade" % (o["ticker"], rst["side"],
                                                   _rejection_reason(res), o["ticker"]))})
            if blocked:
                continue
            if sell_only and str(o["side"]).lower() != "sell":
                # **UNREACHABLE, AND CHECKED AT THE DOOR ANYWAY [item 71].** The filter above
                # removed every buy; this is the same property asserted at the last line before
                # a real order leaves, because the two places a reader would look for "can a
                # wind-down buy?" are the planner and the sender, and only one of them is the
                # one that matters.
                out["alerts"].append({
                    "kind": "buy_blocked_at_the_broker_door", "slot": str(slot),
                    "reason": ("a BUY for %s reached the sender on a slot winding down at 0%% "
                               "and was blocked. The plan filter should have removed it, so "
                               "this is a defect." % o["ticker"])})
                continue
            try:
                res = client.place_limit(
                    o["ticker"], o["side"], o["qty"], o["limit_price"],
                    client_order_id=client_order_id(slot, key, o["ticker"],
                                                    attempt=send_seq))
            except Exception as e:                                      # noqa: BLE001
                res = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
            # **BOTH CLIENTS' FAILURE SHAPES, because they differ [item 64].**
            # `_LiveClient._request` says `error`; `AlpacaPaperBroker.place_equity` says
            # `reason` and carries the broker's own body under `detail`. Reading only `error`
            # reported sixty real rejections as `None` -- blocker 1's family one level down,
            # and the reason the second real cycle could not be diagnosed from its own log.
            why = _rejection_reason(res)
            rec = {"ticker": o["ticker"], "side": o["side"], "qty": o["qty"],
                   "limit_price": o["limit_price"], "ok": bool(res.get("ok")),
                   "detail": why if not res.get("ok") else None}
            out["sent"].append(rec)
            st["attempts"].append(dict(rec, event=key, at=_stamp()))
            if not res.get("ok") and SETTLE.is_settlement_wait(why, res.get("detail")):
                # **REFUSED FOR WANT OF SETTLED CASH IS NOT A BROKER FAULT [item 67].** The
                # broker's spendable figure can be stale by the time the order lands, so the
                # budget above is necessary and not sufficient. Recorded as a deferral so the
                # sells stand and the next trading day re-sends; a `broker_error` here would
                # read as a fault and, under the dedupe, drown the real ones.
                out["deferred"].append(dict(o, why="the broker refused it: %s" % why))
                out["sent"][-1]["awaiting_settlement"] = True
            elif not res.get("ok"):
                out["alerts"].append({"kind": "broker_error", "slot": str(slot),
                                      "reason": "order for %s was rejected: %s"
                                                % (o["ticker"], why)})
            else:
                out["alerts"].append({"kind": "live_order_sent", "slot": str(slot),
                                      "reason": "%s %s %.6f @ %.2f"
                                                % (o["side"], o["ticker"], o["qty"],
                                                   o["limit_price"])})
        out["acted"] = True
        # THE EVENT STAYS OPEN UNTIL ITS TARGETS ARE MET. `processed` records that the event
        # was SEEN and acted on, so a brand-new cycle does not treat it as new again;
        # `open_event` records that it is not FINISHED, so the next cycle re-prices whatever
        # did not fill. Both are needed: `processed` alone would stop the remainder, and
        # `open_event` alone would let a restart re-send the first order.
        if key and key != "none" and key not in st["processed"]:
            st["processed"].append(key)
        st["open_event"] = key
        st["last_event_date"] = (book or {}).get("formed_on")
        st["last_pct"] = pct

        # ---- THE SETTLEMENT WAIT, ON THE EVENT [item 67 part 1] --------------------------
        #
        # A deferral is NORMAL on a rebalance whose buys are funded by its own sells, so it is
        # recorded rather than alerted. The alert waits until the wait has been seen on more
        # trading days than T+1 can explain -- `wait_state`'s arithmetic, counted on the dates
        # cycles actually ran, which are trading days by construction.
        waits = dict(st.get("awaiting_settlement") or {})
        if out["deferred"]:
            w = SETTLE.wait_state(list((waits.get(key) or {}).get("days") or []),
                                  on_date=_stamp())
            waits[key] = {"days": w["days"], "since": w["since"],
                          "n_orders": len(out["deferred"])}
            out["awaiting_settlement"] = dict(w, n_orders=len(out["deferred"]))
            if w["alert"]:
                out["alerts"].append({"kind": "settlement_wait_overdue", "slot": str(slot),
                                      "reason": w["reason"]})
        elif key in waits:
            # It cleared. Removed so a later wait on the same event starts its own count, and
            # reported so a reader can see the wait ended rather than inferring it from silence.
            out["settlement_wait_cleared"] = dict(waits.pop(key), event=key)
        st["awaiting_settlement"] = waits

        _note_write(out, _write(), slot, "recording what was sent")
        out["reason"] = ("sent %d order(s) for %s%s"
                         % (len(out["sent"]), key,
                            ("; %d buy(s) await settled cash" % len(out["deferred"]))
                            if out["deferred"] else ""))
        return out
    except Exception as e:                                              # noqa: BLE001
        # A SLOT'S FAILURE IS ITS OWN. The caller continues with the others.
        out["alerts"].append({"kind": "slot_crashed", "slot": str(slot),
                              "reason": "%s: %s" % (type(e).__name__, e)})
        out["reason"] = "this slot failed and sent nothing (%s)" % type(e).__name__
        return out


def _stamp() -> str:
    # TIMEZONE-AWARE. `utcnow()` is deprecated and, more to the point, returns a NAIVE
    # datetime that reads as local time to anything that parses it -- on a record whose
    # timestamps are the only evidence of when an order was attempted.
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


#: STEP 8. Alpaca paper pays NO dividends (its own docs), so a paper book or the paper slot
#: holding through an ex-date earns nothing a real holder would have.
#:
#: **THE OMISSION IS STATED RATHER THAN FILLED IN, AND THAT IS A CHOICE WITH A REASON.** The
#: free routes this project owns carry a dividend series (`yfinance` ships `actions`), so
#: crediting them is buildable -- but the paper slot's job is to prove the ORDER PATH, and a
#: credited dividend is a number this code invented sitting in an account the broker says is
#: smaller. The next cycle reads `equity` from the broker, so an invented credit would be
#: overwritten and the two records would disagree about the same account. Quoting the shortfall
#: is the honest version and it costs nothing: the Index's own published figures are total
#: return, so the gap is measurable against them whenever Don wants it.
DIVIDEND_STATEMENT = {
    "paid_by_paper": False,
    "statement": ("Alpaca paper does not pay dividends, so any paper book or the paper slot "
                  "holding shares through an ex-date receives nothing and its return "
                  "understates a real holding's by the dividend."),
    "why_not_credited": ("the broker is the authority on this account's equity and the next "
                        "cycle reads it from there, so a dividend this code credited would be "
                        "overwritten and the two records would disagree about one account. "
                        "The shortfall is stated instead."),
    "measurable_against": ("the Index's own published figures are total-return, so the gap is "
                           "measurable whenever it is wanted"),
}

#: STEP 7. The first N paper fills, recorded mid against fill price. Thirty, per the brief.
FEED_GAP_N = 30


def feed_gap_path(root: str = None) -> str:
    return os.path.join(live_dir(root), "feed_gap.json")


def record_feed_gap(rows, root: str = None, *, unfilled: int = 0, attempts: int = 0) -> dict:
    """Append fill observations until `FEED_GAP_N` are held. Never raises.

    `rows` are `{ticker, kind, mid, fill, side}`. **STOCK AND OPTION ARE KEPT APART**, per the
    brief, because they are different feeds -- the free plan is IEX for stocks and an
    INDICATIVE feed for options, so pooling them would average a measured gap with a gap
    against a feed that is explicitly not the market.
    """
    out = {"ok": False, "n": 0, "reason": ""}
    try:
        try:
            with open(feed_gap_path(root), encoding="utf-8") as fh:
                held = json.load(fh) or {}
        except (OSError, ValueError):
            held = {}
        fills = list(held.get("fills") or [])
        seen = {str(f.get("order_id") or "") for f in fills if f.get("order_id")}
        # UNFILLED ORDERS ARE COUNTED, NOT PRICED. A monotone counter, because an order that
        # expired is a fact about the feed's mid that the price gap below cannot express.
        n_unfilled = max(int(held.get("n_unfilled") or 0), int(unfilled or 0))
        # THE DENOMINATOR [item 63, auditor #14]. An unfilled COUNT is not a measurement:
        # fourteen unfilled means nothing without the number of orders placed. `reconcile`
        # re-reads the same orders every cycle, so this is a MAXIMUM rather than a running
        # total -- the same monotone treatment the unfilled count already gets, for the same
        # reason.
        n_attempts = max(int(held.get("n_attempts") or 0), int(attempts or 0))
        for r in (rows or []):
            # IDEMPOTENT PER ORDER. `reconcile` re-reads the same filled orders on every
            # cycle, so without this the same fill would be counted until the window filled
            # up with one execution.
            oid = str((r or {}).get("order_id") or "")
            if oid and oid in seen:
                continue
            if oid:
                seen.add(oid)
            if len(fills) >= FEED_GAP_N:
                break
            mid, fill = LS._f((r or {}).get("mid")), LS._f((r or {}).get("fill"))
            if mid is None or fill is None or mid <= 0:
                continue
            fills.append({"ticker": str(r.get("ticker") or "").upper(),
                          "kind": ("option" if str(r.get("kind")) == "option" else "stock"),
                          "side": str(r.get("side") or ""), "mid": mid, "fill": fill,
                          "gap": fill - mid, "gap_frac": (fill - mid) / mid,
                          "order_id": oid, "at": _stamp()})
        os.makedirs(live_dir(root), exist_ok=True)
        p = feed_gap_path(root)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"fills": fills, "n_unfilled": n_unfilled,
                       "n_attempts": n_attempts}, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, p)
        out.update(ok=True, n=len(fills), n_unfilled=n_unfilled, n_attempts=n_attempts)
        return out
    except OSError as e:
        out["reason"] = "could not record the feed gap: %s" % e
        return out


def feed_gap_report(root: str = None) -> dict:
    """The measurement, or how far off it is. STOCK AND OPTION SEPARATELY."""
    out = {"target_n": FEED_GAP_N, "n": 0, "complete": False, "stock": None, "option": None,
           "reason": ""}
    try:
        with open(feed_gap_path(root), encoding="utf-8") as fh:
            held = json.load(fh) or {}
        fills = held.get("fills") or []
    except (OSError, ValueError):
        out["reason"] = "no paper fill has been recorded yet"
        return out
    out["n_unfilled"] = int(held.get("n_unfilled") or 0)
    out["n_attempts"] = int(held.get("n_attempts") or 0)
    # THE RATE, OR AN HONEST ABSENCE [item 63]. With no attempts recorded there is no
    # denominator, and a rate of `None` is the only truthful answer -- reporting 0.0 would
    # say "nothing fails to fill" on the strength of nothing having been tried.
    out["unfilled_rate"] = (
        (out["n_unfilled"] / float(out["n_attempts"])) if out["n_attempts"] > 0 else None)
    out["unfilled_rate_note"] = (
        "unfilled orders as a share of orders placed. `None` means no denominator has been "
        "recorded yet, which is NOT a rate of zero." if out["unfilled_rate"] is None else
        "%d of %d orders placed at the free feed's mid did not fill"
        % (out["n_unfilled"], out["n_attempts"]))
    out["n"] = len(fills)
    out["complete"] = len(fills) >= FEED_GAP_N
    for kind in ("stock", "option"):
        xs = [f for f in fills if f.get("kind") == kind]
        if not xs:
            # ABSENT IS NOT ZERO. `V6`'s rule: a measurement not yet taken and a measured gap
            # of nothing must not read the same.
            out[kind] = {"n": 0, "measured": False,
                         "reason": "no %s fill recorded yet" % kind}
            continue
        gaps = sorted(LS._f(f.get("gap_frac")) or 0.0 for f in xs)
        n = len(gaps)
        out[kind] = {
            "n": n, "measured": True,
            "median_gap_frac": gaps[n // 2],
            "mean_gap_frac": sum(gaps) / n,
            "worst_gap_frac": max(gaps, key=abs),
            "note": ("fill minus the recorded mid, as a share of the mid. Positive means the "
                     "fill was WORSE than the mid for a buy."),
        }
    # THE BINDING LIMITATION, STATED WITH THE MEASUREMENT RATHER THAN LEFT TO BE NOTICED.
    # Every order on this path is a LIMIT at the mid, and a limit order cannot fill worse than
    # its limit -- so the price gap is CENSORED ON ONE SIDE BY CONSTRUCTION and can only ever
    # read favourable or zero. It therefore measures how much BETTER than the free feed's mid
    # an execution came, and it CANNOT measure the feed being wrong in the costly direction.
    #
    # The uncensored half is the FILL RATE: an order resting at the IEX mid that expires
    # unfilled is the feed's mid not being a price that traded, which is the same question
    # asked where the limit does not hide the answer. Both ship, and neither is the whole
    # measurement alone.
    out["censoring"] = {
        "price_gap_is_one_sided": True,
        "why": ("every order is a limit at the mid, and a limit order never fills worse than "
                "its limit, so this gap can only read favourable or zero"),
        "uncensored_companion": ("the unfilled RATE -- an order resting at the free feed's "
                                 "mid that expired is that mid not being a traded price, and "
                                 "it is reported as a share of orders placed because a count "
                                 "with no denominator is not a measurement"),
        "underlying_question": ("is the free IEX feed wrong in the COSTLY direction? NOT "
                                "MEASURED, and not measurable on this path: the price gap is "
                                "one-sided by construction and the unfill rate is the "
                                "uncensored evidence bearing on it."),
        "would_need": ("a market order to measure the costly direction, which this path does "
                       "not place"),
    }
    if not out["complete"]:
        out["reason"] = ("%d of %d fills recorded; the measurement is reported as incomplete "
                         "rather than quoted early" % (out["n"], FEED_GAP_N))
    return out


def run_cycle(*, env=None, mode: str = DRY, only: str = None, root: str = None,
              book=None, now=None, paper_client=None, live_client_factory=None,
              notify_send=None, send=None, may_write: bool = True) -> dict:
    """ONE CYCLE over the paper slot and every live slot. Never raises.

    THE PAPER SLOT RUNS FIRST AND DELIBERATELY SO: its order plan is what every live slot's
    dry run is diffed against (§8's parity requirement), so it has to exist before they run.

    `send=False` is the default, which makes a GET of the door a dry run for every slot.
    """
    e = env if env is not None else os.environ

    # `send=` IS KEPT AS A COMPATIBILITY SHIM AND IT RESOLVES THE SAFE WAY. A caller passing
    # `send=True` means LIVE, which is what it meant before; anything falsey means DRY. It is
    # not removed outright because a caller left on the old keyword would otherwise silently
    # get the DEFAULT -- and the default is dry, so that direction is safe, but a caller
    # believing it was sending and transmitting nothing is the failure that looks like a quiet
    # market. `mode=` wins if both are given.
    if mode == DRY and send is not None:
        mode = LIVE if send else DRY
    if mode not in (DRY, PAPER, LIVE):
        mode = DRY
    paper_sends = mode in (PAPER, LIVE)
    live_sends = (mode == LIVE)

    out = {"ok": True, "at": _stamp(), "mode": mode,
           "send_requested": live_sends, "paper_send_requested": paper_sends,
           "slots": [], "alerts": [], "paper": None, "session": None, "reason": ""}
    try:
        from ..screener import index_in_force as IF
        from ..screener.market_session import orders_window, session_state

        # THE ORDERS WINDOW, NOT THE CLOSE. `session_state` answers "has today's session
        # closed" and is true only from 16:15 ET, because it exists to decide when the Index
        # may be MARKED. Gating orders on it meant the cycle scheduled at 10:40 ET -- chosen
        # precisely BECAUSE a `day` limit order must be placed inside the session -- could
        # never transmit anything, for ever, while reporting "the session is closed" as a
        # sensible-looking reason. Found when this module's own suite changed verdict at
        # midnight.
        sess = orders_window(now)
        out["session"] = sess
        # The close is still REPORTED, because a reader comparing this against the Index mark
        # needs both and they are now visibly different questions.
        out["session_closed_state"] = session_state(now)
        session_ok = bool(sess.get("ok"))

        bk = book if book is not None else IF.attach_returns(IF.book_in_force())
        held = [q for q in ((bk or {}).get("positions") or [])
                if q.get("status") == "held"]
        # **EVERY NAME THAT MIGHT BE TRADED, WHICH IS THE BOOK'S PLUS WHAT THE SLOTS HOLD
        # [item 67].** This was the book's held names alone -- and an EXITED name is by
        # definition not among them, so no quote was requested for it, so `order_plan` skipped
        # it for want of a mark and the exit never happened. The exit targets added in this
        # same item would have been silently skipped on every cycle, and the test I wrote for
        # them passed because it supplied the price by hand.
        #
        # A name is read from a slot's OWN record (`reconcile` builds those from
        # `valquo-<slot>-` prefixed orders and nothing else), so this can only ever ask for a
        # quote on something a slot bought. Asking for a quote trades nothing.
        tickers = [str(q.get("ticker") or "").upper() for q in held]
        _slots_to_price = [PAPER_SLOT] + [str(n) for n in LS.discover_slots(e)]
        for _s in _slots_to_price:
            for _nm in (read_state(_s, root).get("holdings") or {}):
                _nm = str(_nm).strip().upper()
                if _nm and _nm not in tickers:
                    tickers.append(_nm)
        out["priced_names"] = {
            "n": len(tickers), "book_held": len(held),
            "held_by_a_slot_and_not_in_the_book": sorted(
                set(tickers) - {str(q.get("ticker") or "").upper() for q in held}),
            "why": ("an exited name must be priced or it cannot be sold -- `order_plan` skips a "
                    "name with no usable mark, which is right, and would have skipped every "
                    "exit"),
        }

        # ---- the paper slot, on the paper client ----------------------------------------
        #
        # **THE PAPER TARGETS ARE COMPUTED HERE RATHER THAN TAKEN FROM THE PAPER SLOT'S RUN,
        # AND THAT IS NOT TIDYING [item 63].** Parity now diffs TARGET WEIGHTS, and a target is
        # a pure function of (percentage, equity, book) -- it does not depend on what the paper
        # slot happens to be doing this cycle. Reading it out of the paper slot's plan would
        # make the comparison unavailable exactly when the paper slot has nothing to do: paper
        # processes the rebalance on day 1 and closes the event, Don arms a live slot on day 2,
        # the paper slot returns early with no plan, and the live slot would then refuse for
        # ever on a missing comparison. Computing it directly removes that coupling.
        paper_targets, paper_value, paper_account_id = None, None, None
        pc = paper_client
        if pc is None:
            try:
                from .alpaca_broker import AlpacaPaperBroker
                pc = AlpacaPaperBroker()
            except Exception as ex:                                     # noqa: BLE001
                out["paper"] = {"slot": PAPER_SLOT, "armed": False, "orders": [],
                                "reason": ("the Alpaca paper client could not be built: %s. "
                                           "Every slot still runs; the paper slot is the one "
                                           "that cannot." % ex),
                                "alerts": [{"kind": "paper_client_absent",
                                            "slot": PAPER_SLOT, "reason": str(ex)}]}
                out["alerts"].extend(out["paper"]["alerts"])
                pc = None
        if pc is not None:
            marks = _marks_for(pc, tickers)
            # GUARDED. An unguarded read here raised into the outer handler, which returns
            # having run NOTHING -- so a blip in the paper account would have cost every live
            # slot its dry run and its parity diff, in an account they do not use. The module
            # docstring promises "one slot's failure never stops another"; this is the line
            # that broke it.
            try:
                acct = pc.account() if hasattr(pc, "account") else {}
            except Exception as ex:                                     # noqa: BLE001
                acct = {}
                out["alerts"].append({"kind": "paper_account_unreadable",
                                      "slot": PAPER_SLOT,
                                      "reason": "the paper account could not be read (%s); "
                                                "the paper slot sends nothing this cycle and "
                                                "every live slot still runs" % ex})
            eq = (acct or {}).get("equity")
            paper_account_id = (acct or {}).get("account_id")
            ptg = LS.targets(PAPER_PCT, eq, held)
            if ptg.get("ok"):
                paper_targets, paper_value = ptg["targets"], ptg["slot_value"]
            else:
                out["alerts"].append({
                    "kind": "paper_targets_unavailable", "slot": PAPER_SLOT,
                    "reason": ("the paper book's own target weights could not be computed "
                               "(%s), so no live slot has a comparison this cycle and none "
                               "will send" % ptg.get("reason"))})
            # THE PAPER SLOT IS ARMED BY CONSTRUCTION -- it is paper money on a host that
            # cannot be anything else, which is the whole point of proving the path here.
            # **THE FRACTIONABLE CENSUS, READ WHERE A CLIENT ALREADY EXISTS [item 67
            # part 2].** One GET of Alpaca's asset master, which is ACCOUNT-INDEPENDENT -- so
            # the paper keys answer the question for the live slots too. Guarded: a census is a
            # report, and a report must never cost the cycle its orders.
            try:
                frac = fractional_report(pc, tickers)
            except Exception:                                           # noqa: BLE001
                frac = None
            res = run_slot(PAPER_SLOT, pct=PAPER_PCT, fractional=frac,
                           may_write=bool(may_write),
                           armed_state={"armed": True,
                                        "reason": "the paper slot is always armed: it is "
                                                  "paper money on the paper host"},
                           book=bk, client=pc, equity=eq, account=acct,
                           marks=marks, root=root,
                           session_ok=session_ok, send=paper_sends,
                           account_id=paper_account_id,
                           sess_reason=sess.get("reason") or "")
            out["paper"] = res
            out["alerts"].extend(res.get("alerts") or [])
        out["paper_account_id_recorded"] = bool(paper_account_id)

        # ---- every live slot -------------------------------------------------------------
        for n in LS.discover_slots(e):
            if only is not None and str(only) != str(n):
                continue
            # **`holds` IS DERIVED FROM THE SLOT'S OWN RECORD, BEFORE ARMING [item 71,
            # blocker A].** This is what lets `armed` tell "0% and flat" from "0% and still
            # holding" -- the two states that shared one value and made the X->0 sell-out
            # unreachable. The record is this slot's own holdings, built by `reconcile` from
            # this slot's own fills, so a wind-down can only ever sell what this path bought;
            # Don's other positions in the same account are not in it and cannot be.
            _rec_st = read_state(n, root)
            _holds = any((LS._f(q) or 0.0) > 0
                         for q in (_rec_st.get("holdings") or {}).values())
            a = LS.armed(n, e, holds=_holds)
            p = LS.slot_pct(n, e)
            pct = p.get("pct")
            client, eq, marks, live_account_id = None, None, {}, None
            slot_report = None
            # **PER ITERATION, BESIDE `client`, OR A FAILED SLOT INHERITS THE LAST ONE'S
            # ACCOUNT [item 67].** Every path that clears `client` clears this too.
            slot_account = None
            # THE ONLY PLACE A LIVE CLIENT IS BUILT, AND `live_sends` IS THE WHOLE GATE ON
            # TOP OF `armed`. In PAPER mode this is False, so `run=paper` cannot construct a
            # live client even for a fully armed slot -- which is the property 2b asks to be
            # pinned, and it is pinned structurally rather than by intention.
            if a["armed"] and live_sends:
                # THE ONLY PLACE A LIVE CLIENT IS EVER CONSTRUCTED, and all four conditions
                # have already been checked by `armed`.
                try:
                    if live_client_factory is not None:
                        client = live_client_factory(n)
                    else:
                        client = LS._LiveClient(
                            n, (e.get("ALPACA_ACCOUNT_%d_KEY_ID" % n) or ""),
                            (e.get("ALPACA_ACCOUNT_%d_SECRET_KEY" % n) or ""))
                    acct = client.account()
                    eq = ((acct or {}).get("data") or {}).get("equity")
                    # **THE BUY BUDGET COMES OUT OF THIS SAME REPLY [item 67].** Sizing a buy
                    # from one read and the equity from another is the wrong-object family, and
                    # on a live account the object is money.
                    slot_account = acct
                    # **READ HERE, AT THE ONE PLACE A LIVE CLIENT EXISTS [item 67 part 2].**
                    # Three GETs, no order constructed on any path. It answers Don's question
                    # about the IRA -- limited margin, what is spendable without borrowing, and
                    # whether Alpaca reports fractional trading as enabled.
                    try:
                        slot_report = account_settlement_report(client)
                    except Exception:                                   # noqa: BLE001
                        slot_report = None
                    live_account_id = str(((acct or {}).get("data")
                                           or {}).get("id") or "") or None
                    # THE LIVE SLOT MUST NOT BE THE PAPER ACCOUNT. The host check cannot see
                    # this: paper credentials pasted into `ALPACA_ACCOUNT_1_*` authenticate
                    # against the paper host and `_LiveClient` would refuse that host -- but a
                    # future client, or a paper key that Alpaca also honours on the live host,
                    # would not be caught. Comparing the resolved ids costs one read.
                    # [item 63]
                    if (live_account_id and paper_account_id
                            and live_account_id == paper_account_id):
                        out["alerts"].append({
                            "kind": "live_slot_is_the_paper_account", "slot": str(n),
                            "reason": ("slot %s's keys resolve to the SAME account as the "
                                       "paper broker (%s); it sends nothing and is treated as "
                                       "having no client" % (n, live_account_id))})
                        client, eq, live_account_id = None, None, None
                        slot_account = None
                except Exception as ex:                                 # noqa: BLE001
                    out["alerts"].append({"kind": "broker_error", "slot": str(n),
                                          "reason": "the live client failed: %s" % ex})
                    client, eq, live_account_id = None, None, None
                    slot_account = None
            if client is None:
                # AT 0%, PAUSED, OR UNAUTHORIZED: price from the PAPER client so the dry run
                # has marks, and read equity from the live account ONLY if one was built.
                marks = _marks_for(pc, tickers) if pc is not None else {}
                # The dry run needs an equity to size against. Without a live client there is
                # none, so it uses the PAPER account's -- and says so, because a dry run
                # sized on another account's equity is a shape check, not a dollar check.
                try:
                    # A DRY RUN HAS NO LIVE ACCOUNT, so no buy is sized from one --
                    # `slot_account` is already None from the initialisation above and is
                    # deliberately NOT set to the paper account's reply. It transmits nothing
                    # either way (`send=False`), and the budget it reports then says plainly
                    # that nothing bounded it rather than quoting another account's figure.
                    eq = ((pc.account() or {}).get("equity") if pc is not None else None)
                except Exception:                                       # noqa: BLE001
                    eq = None   # the dry run then refuses at preflight, which is correct
            else:
                marks = _marks_for(client, tickers) if hasattr(client, "quotes") else (
                    _marks_for(pc, tickers) if pc is not None else {})
            res = run_slot(n, pct=pct, armed_state=a, book=bk, client=client, equity=eq,
                           account=slot_account, settlement_report=slot_report,
                           marks=marks, root=root, session_ok=session_ok,
                           paper_targets=paper_targets, paper_value=paper_value,
                           account_id=live_account_id,
                           send=bool(live_sends and a["armed"]),
                           may_write=bool(may_write),
                           sell_only=bool(a.get("sell_only")),
                           sess_reason=sess.get("reason") or "")
            res["mode"] = mode
            if mode == PAPER:
                res["paper_mode_note"] = ("this is a PAPER-ONLY cycle, so this live slot "
                                          "computed its plan and sent nothing whatever its "
                                          "percentage, arming or keys")
            res["sized_on"] = ("the live account's equity" if client is not None
                               else "the PAPER account's equity, because this slot has no "
                                    "live client -- so the diff is a shape check rather than "
                                    "a dollar check")
            if res.get("parity") is not None and res.get("writes_allowed"):
                # **GATED ON THE SLOT'S OWN ANSWER [item 71], and my first cut of this gated it
                # on `may_write` alone.** The transition table found that on its first run: a
                # PAPER cycle, a DRY cycle and a PAUSED slot all still wrote here, because this
                # write sits outside `run_slot` where the gate lives -- the same blocker C in
                # the one place the gate could not see it. Blocker C was reported against the
                # close branch; the property is about EVERY write.
                #
                # It reads `writes_allowed` off the slot's result rather than recomputing the
                # condition, so there is one definition of "may this cycle persist anything"
                # (`B7`). A slot result without the key is treated as NO.
                st = read_state(n, root)
                st["last_parity"] = res["parity"]
                write_state(n, st, root)
            out["slots"].append(res)
            out["alerts"].extend(res.get("alerts") or [])

        if not LS.discover_slots(e):
            out["reason"] = ("no live slot has a key pair configured, so only the paper slot "
                             "ran. This is the expected state until Don adds slot 1's keys "
                             "after the auditor review.")

        # STEP 6. ANNOUNCED LAST, AND OUTSIDE EVERY SLOT. Two reasons: one message per cycle
        # rather than one per slot, and a notifier failure that happened mid-loop could not
        # then stop a later slot from running. `live_notify` never raises, and this is
        # belt-and-braces on top of that.
        try:
            from . import live_notify as LN
            out["announced"] = LN.announce(out["alerts"], root=root, send=notify_send)
        except Exception as ex:                                         # noqa: BLE001
            out["announced"] = {"sent": False,
                                "reason": "the notifier failed and the cycle did not: %s" % ex}
        return out
    except Exception as ex:                                             # noqa: BLE001
        out["ok"] = False
        out["reason"] = "the cycle failed before any slot ran (%s)" % type(ex).__name__
        out["alerts"].append({"kind": "cycle_crashed", "slot": "-", "reason": str(ex)})
        return out


def key_presence(env=None) -> dict:
    """Are the variables PRESENT? Booleans and names only — never a value.  [item 58b step 1]

    **THIS IS THE ANSWER TO "DID DON SET THE KEYS", AND IT IS OWNER-ONLY.** A lane cannot read
    it: the door that serves it needs the admin token, which no lane ever sees. So a lane
    reports presence as UNKNOWN rather than assuming it, and Don reads this.
    """
    e = env if env is not None else os.environ

    def present(name):
        return bool((e.get(name, "") or "").strip())

    slots = []
    for n in LS.discover_slots(e):
        slots.append({"slot": n, "holder": LS.holder(n, e),
                      "key_id_present": present("ALPACA_ACCOUNT_%d_KEY_ID" % n),
                      "secret_present": present("ALPACA_ACCOUNT_%d_SECRET_KEY" % n),
                      "pct_present": present("ALPACA_ACCOUNT_%d_LIVE_PCT" % n)})
    return {
        "paper": {"key_id_present": present("ALPACA_PAPER_KEY_ID"),
                  "secret_present": present("ALPACA_PAPER_SECRET_KEY"),
                  "both_present": present("ALPACA_PAPER_KEY_ID")
                  and present("ALPACA_PAPER_SECRET_KEY")},
        "pilot_enabled_present": present(LS.ENABLED_VAR),
        "pilot_enabled": LS.pilot_enabled(e),
        "live_slots": slots,
        "n_live_slots": len(slots),
        "retired_set": [v for v in LS.RETIRED_VARS if present(v)],
        "note": ("Presence only. No value appears in this payload, and none ever will -- the "
                 "question is whether the variable is set, and the answer to that is a "
                 "boolean."),
        "as_of": _stamp(),
    }
