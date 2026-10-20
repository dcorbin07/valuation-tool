# -*- coding: utf-8 -*-
"""Settlement-aware rebalancing: what an account can spend WITHOUT BORROWING, and how long a
wait for cash is allowed to last before it stops being normal.

**WHY THIS IS A MODULE AND NOT A FEW LINES INSIDE `run_slot`.** Two properties decide whether
the live path can ever create a margin debit, and both are arithmetic on the broker's own
reply: which field bounds a buy, and when a wait becomes a fault. A test should be able to
drive each against a recorded account without constructing a cycle -- and the AST guard that
proves no other line in the live path reads a buying-power field needs one place to point at.

---------------------------------------------------------------------------------------------
WHICH FIELD, AND WHY -- from Alpaca's own documentation, quoted (item 67)
---------------------------------------------------------------------------------------------

`GET /v2/account` publishes several buying-power fields and they do not mean the same thing:

  * **`non_marginable_buying_power`** -- *"Current available non-margin dollar buying power"*.
    This is the figure that answers the question actually being asked, in Alpaca's own words.
    **It is the primary.**
  * **`buying_power`** -- *"Current available $ buying power; If multiplier = 4, this is your
    daytrade buying power ...; If multiplier = 2, buying_power = max(equity - initial_margin,
    0) * 2; **If multiplier = 1, buying_power = cash**"*. So it equals cash ONLY at multiplier
    1 and is LEVERED above it. Usable only as `min(cash, buying_power)`, which is safe at every
    multiplier because the cash term bounds it.
  * **`regt_buying_power`** -- *"Your buying power under Regulation T"*. Reg T buying power is
    the levered figure by definition. **Never read here.**
  * **`cash`** -- *"Cash Balance"*.
  * **`multiplier`** -- *"valid values 1 (standard limited margin account with 1x buying
    power), 2 (reg T margin account ...), 4 (PDT account ...)"*.

`daytrading_buying_power` and `cash_withdrawable` are **not in that schema** and are not read.

**WHY AN IRA STILL GETS THIS TREATMENT THOUGH IT PROBABLY NEVER WAITS.** Alpaca's IRAs are
*"by default setup with limited margin (1x margin)"*, and limited margin *"allows you to avoid
certain Federal Reserve Board Regulation T settlement periods"* and *"permits the purchase of
securities with the use of unsettled funds"* -- while it *"does not allow for borrowing of
funds, creating a margin debit, short selling, or selling naked options"*, and *"Alpaca will
not extend any credit or margin in the Alpaca IRA"*. So a sell-then-buy rebalance may never
wait at all. **The budget is not a settlement model and does not try to be one**: it asks the
broker what is spendable without borrowing and sizes to that. An account that does not need to
wait does not wait, because the broker reports the proceeds as available immediately.

---------------------------------------------------------------------------------------------
HOW LONG A WAIT MAY LAST -- counted in TRADING DAYS, and counted by OBSERVATION
---------------------------------------------------------------------------------------------

US equities settle **T+1**: proceeds of a sale on trading day D are settled by D+1. A wait that
is still unresolved on **D+2** has outlasted T+1 by a full trading day, and that is the alert.

**THE COUNT IS OF DISTINCT DATES ON WHICH THE WAIT WAS SEEN, WHICH MAKES IT A TRADING-DAY
COUNT BY CONSTRUCTION AND NEEDS NO HOLIDAY CALENDAR.** A buy is only ever deferred inside the
orders window, and that window is only open on a trading day -- so every date in the list is a
day the market was open. A weekend or a holiday contributes nothing, because no cycle ran. The
alternative, counting calendar days against a hand-maintained holiday list, would be a second
definition of "trading day" that rots.

**AND THE SAME CORRECTION APPLIES TO THE NO-PROGRESS CEILING [item 64's family].** That
ceiling counted CYCLES. There are up to five scheduled cycles a day plus any manual ones, so a
rebalance working exactly as designed could spend a five-cycle ceiling inside a single morning
-- the false-alarm shape item 64 was built to remove, reintroduced by the schedule it added.
Counting distinct dates makes the ceiling mean what its own message says.
"""
from __future__ import annotations

import datetime as _dt
import os
from typing import Optional

#: US equities settle T+1. A wait still open on the SECOND trading day after it began has
#: outlasted settlement by a full trading day, which is `len(days_seen) > 2`: the day it began,
#: the day it should have cleared, and one more.
SETTLEMENT_TRADING_DAYS = 1
WAIT_ALERT_AFTER_TRADING_DAYS = SETTLEMENT_TRADING_DAYS + 1

#: Consecutive TRADING DAYS an event may fail to advance before the slot stops retrying it.
#: Deliberately the same number as the cycle ceiling it replaces -- what changed is the unit.
MAX_EVENT_TRADING_DAYS = 5

#: The broker's own name for the figure that bounds a buy. **The ONLY key this project sizes a
#: buy from.** A committed literal (`MA13`) so a future edit to the sizing rule shows up as a
#: change to this line rather than as a different string somewhere inside the cycle.
NO_BORROW_FIELD = "non_marginable_buying_power"

#: Levered figures, named so a reader can see they were considered and refused rather than
#: overlooked. Never read. A buy sized from either of these is a margin debit, in an account
#: that is not allowed to carry one.
LEVERED_FIELDS = ("regt_buying_power", "daytrading_buying_power")

#: What Alpaca says when an order is refused for want of funds. Matched to tell a SETTLEMENT
#: WAIT from a broker fault -- the one is normal and keeps the sells, the other means no orders
#: and an alert. Alpaca's code for it is 40310000.
INSUFFICIENT_CODES = (40310000,)
INSUFFICIENT_PHRASES = ("insufficient buying power", "insufficient day trading buying power",
                        "insufficient_buying_power", "buying power is insufficient")


def _f(x) -> Optional[float]:
    try:
        if x is None or isinstance(x, bool):
            return None
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def spendable(account) -> dict:
    """How much this account can spend on a buy **without borrowing**, and which field said so.

    Accepts either client's account shape -- `AlpacaPaperBroker.account()` returns a normalised
    dict and `_LiveClient.account()` returns `{"ok", "data"}` around Alpaca's raw body --
    because the two have diverged four times already and a budget reading only one of them
    would be the fifth.

    `ok` False means **the broker did not report a figure this code is willing to spend
    against**, which is a broken input: the caller sends no buys. It is NOT a settlement wait,
    because nothing here establishes that the funds are merely unsettled.
    """
    a = account
    if isinstance(a, dict) and isinstance(a.get("data"), dict):
        if a.get("ok") is False:
            return {"ok": False, "amount": None, "field": None,
                    "reason": "the account could not be read, so no buy can be sized"}
        a = a.get("data") or {}
    if not isinstance(a, dict):
        return {"ok": False, "amount": None, "field": None,
                "reason": "no account was supplied, so no buy can be sized"}

    nmbp = _f(a.get(NO_BORROW_FIELD))
    cash = _f(a.get("cash"))
    bp = _f(a.get("buying_power"))
    mult = _f(a.get("multiplier"))

    if nmbp is not None:
        amount, field = nmbp, NO_BORROW_FIELD
        why = ("the broker's own non-margin buying power, which is Alpaca's documented "
               "'current available non-margin dollar buying power'")
    elif cash is not None and bp is not None:
        # `buying_power` equals cash ONLY at multiplier 1 and is levered above it, so the cash
        # term is what makes this safe at any multiplier. Taking the min rather than branching
        # on `multiplier` means an unreported or wrong multiplier cannot widen the budget.
        amount, field = min(cash, bp), "min(cash, buying_power)"
        why = ("the broker did not report %s, so the budget is the smaller of cash and buying "
               "power -- buying power alone is levered whenever the multiplier is above 1"
               % NO_BORROW_FIELD)
    elif cash is not None:
        amount, field = cash, "cash"
        why = "the broker reported only a cash balance, which cannot include borrowed funds"
    else:
        return {"ok": False, "amount": None, "field": None, "multiplier": mult,
                "reason": ("the broker reported no spendable figure (%s, cash and buying_power "
                           "are all absent or unreadable), so no buy is sized and none is sent"
                           % NO_BORROW_FIELD)}

    amount = max(0.0, round(float(amount), 2))
    return {"ok": True, "amount": amount, "field": field, "why": why, "multiplier": mult,
            "levered_fields_not_read": list(LEVERED_FIELDS),
            "reason": "%.2f spendable without borrowing, from %s" % (amount, field)}


def is_settlement_wait(reason, detail=None) -> bool:
    """Is this refusal 'there is not enough settled cash yet' rather than a broker fault?

    **THE DISTINCTION DECIDES WHETHER THE SELLS STAND.** A settlement wait keeps the sells,
    defers the buys and re-sends them on the next trading day; every other broker error means
    no orders that cycle and an alert. Getting it backwards in one direction cancels a correct
    rebalance, and in the other hides a real fault behind a daily retry.

    Matched on a declared vocabulary rather than a loose substring: "buying power" on its own
    appears in refusals that are not about settlement at all.
    """
    blob = " ".join(str(x) for x in (reason, detail) if x).lower()
    if any(p in blob for p in INSUFFICIENT_PHRASES):
        return True
    return any(str(c) in blob for c in INSUFFICIENT_CODES)


def _date_of(x) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, _dt.datetime):
        return x.date().isoformat()
    if isinstance(x, _dt.date):
        return x.isoformat()
    s = str(x).strip()
    return s[:10] if len(s) >= 10 else None


def note_trading_day(days, on_date) -> list:
    """Record that something was observed on `on_date`, once per date, in order.

    Every date reaching this function is a date on which the orders window was open, so the
    returned list is a trading-day count with no holiday calendar anywhere near it.
    """
    out = [str(x)[:10] for x in (days or []) if str(x).strip()]
    d = _date_of(on_date)
    if d and d not in out:
        out.append(d)
    return out


def wait_state(days, *, on_date=None) -> dict:
    """How long a settlement wait has lasted, and whether that is still normal.

    `alert` is True once the wait has been seen on more than `WAIT_ALERT_AFTER_TRADING_DAYS`
    distinct trading days -- the day it began, the day T+1 should have cleared it, and one more.
    """
    seen = (note_trading_day(days, on_date) if on_date
            else [str(x)[:10] for x in (days or []) if str(x).strip()])
    n = len(seen)
    over = n > WAIT_ALERT_AFTER_TRADING_DAYS
    return {
        "days": seen, "trading_days": n, "since": (seen[0] if seen else None),
        "alert": bool(over),
        "reason": (("cash from this event's sells has not been spendable on %d trading days "
                    "(%s onward); US equities settle T+1, so a wait this long is no longer "
                    "settlement and wants looking at" % (n, seen[0]))
                   if over else
                   ("waiting for sale proceeds to become spendable; seen on %d trading day(s), "
                    "which is within T+1 and is not a fault" % n)),
    }

# -------------------------------------------------------------------------------------------
# EVERY ORDER, PAGED -- shared by BOTH clients, and living in NEITHER of them
# -------------------------------------------------------------------------------------------
#
# **IT IS HERE BECAUSE IT MAY NOT BE IN EITHER CLIENT'S MODULE.** Both need it, so one would
# have had to import the other -- and item 58's `B_Separation` requires that no paper-side
# module imports the live path, which is what keeps a paper book from reaching live machinery.
# This module imports nothing project-local and is neither path, so the two share one
# definition (`B7`) with no boundary crossed. I tried `live_slots` first and the test caught it.
#: How many pages of orders to walk before refusing. 20 x 500 is 10,000 orders -- about forty
#: events at item 64's measured 239 per event, i.e. ten years of quarterly rebalances. A cap
#: rather than an unbounded loop, because a bug in the advance condition would otherwise spin
#: against a live broker.
MAX_ORDER_PAGES = 20


def paged_orders(fetch, *, page_limit: int = 500, status: str = "all",
                 max_pages: int = None) -> dict:
    """Every order, walked page by page. `{"ok", "data", "truncated", "reason", "pages"}`.

    `fetch(params)` performs one request and returns `{"ok", "data"}` -- the shape BOTH clients'
    `_request` already produces, which is what lets the two share one pager (`B7`).

    **TRUNCATED IS A REFUSAL, NOT A PARTIAL ANSWER.** The caller cannot total fills from a
    partial order list without under-counting a holding, and an under-counted holding makes the
    planner buy the difference again. So every case this cannot prove complete comes back
    `truncated` and the caller refuses.
    """
    cap = int(max_pages or MAX_ORDER_PAGES)
    out, seen, after, pages = [], set(), None, 0
    while pages < cap:
        params = {"status": status, "limit": int(page_limit), "direction": "asc"}
        if after:
            params["after"] = after
        got = fetch(params) or {}
        pages += 1
        if not got.get("ok"):
            return {"ok": False, "data": [], "truncated": False, "pages": pages,
                    "reason": "the broker's orders could not be read (HTTP %s)"
                              % got.get("status")}
        rows = [r for r in (got.get("data") or []) if isinstance(r, dict)]
        fresh = 0
        for r in rows:
            oid = str(r.get("id") or r.get("client_order_id") or "")
            if oid and oid in seen:
                continue            # `after` is exclusive, so an overlap is expected
            if oid:
                seen.add(oid)
            out.append(r)
            fresh += 1
        if len(rows) < int(page_limit):
            return {"ok": True, "data": out, "truncated": False, "pages": pages,
                    "reason": "read %d order(s) over %d page(s)" % (len(out), pages)}
        # A FULL PAGE: there is more. The advance is only safe if the page's last timestamp
        # belongs to exactly one order, because `after` is exclusive on the timestamp.
        stamps = [str(r.get("submitted_at") or "") for r in rows]
        last = stamps[-1] if stamps else ""
        if not last:
            return {"ok": True, "data": out, "truncated": True, "pages": pages,
                    "reason": ("a full page of %d orders carried no submission timestamp, so "
                               "there is no safe way to ask for the next page" % len(rows))}
        if stamps.count(last) > 1:
            return {"ok": True, "data": out, "truncated": True, "pages": pages,
                    "reason": ("%d orders share this page's last submission timestamp (%s), so "
                               "asking for everything after it would SKIP the ones not yet "
                               "read -- and a skipped fill under-counts a holding"
                               % (stamps.count(last), last))}
        if fresh == 0:
            return {"ok": True, "data": out, "truncated": True, "pages": pages,
                    "reason": ("a full page of orders contained nothing new, so the page "
                               "cursor is not advancing and the read cannot be completed")}
        after = last
    return {"ok": True, "data": out, "truncated": True, "pages": pages,
            "reason": ("the order history did not end within %d pages of %d, so this slot's "
                       "fill totals cannot be read reliably" % (cap, page_limit))}

# ---------------------------------------------------------------------------------------------
# ITEM 73 -- PARTIAL CASH: spread the buys, keep the shortfall open, top up in useful amounts
# ---------------------------------------------------------------------------------------------

#: **ONE UNIVERSAL VARIABLE, which is Don's explicit choice of 2026-10-18**: *"There is no
#: per-account variable; Don chose one universal setting."* It applies to every live slot AND to
#: the paper slot, so parity still compares like with like -- a per-slot threshold would make the
#: two books diverge for a reason that has nothing to do with the Index.
MIN_TOPUP_VAR = "LIVE_MIN_TOPUP"

#: Dollars. Below this, a top-up waits rather than firing 86 tiny orders for a small deposit.
DEFAULT_MIN_TOPUP = 250.0


def min_topup(env=None) -> dict:
    """The smallest top-up worth sending. `{"ok", "amount", "stated", "reason"}`.

    **A MALFORMED VALUE REFUSES, EXACTLY AS `LIVE_PCT` DOES**, and for a sharper reason than
    that one has: reading a typo as **0** would top up on every cent that lands in the account,
    and reading it as the DEFAULT would silently ignore a figure Don had deliberately set. So a
    value that is not a non-negative number is a broken input and the slot sends nothing.

    An ABSENT value is the default rather than a refusal -- that is the shipped state and it is
    not a typo.
    """
    e = env if env is not None else os.environ
    raw = (e.get(MIN_TOPUP_VAR, "") or "").strip()
    if raw == "":
        return {"ok": True, "amount": DEFAULT_MIN_TOPUP, "stated": False,
                "reason": ("%s is not set, so the default of $%.2f applies to every slot"
                           % (MIN_TOPUP_VAR, DEFAULT_MIN_TOPUP))}
    try:
        v = float(raw)
    except (TypeError, ValueError):
        v = None
    if v is None or v != v or v in (float("inf"), float("-inf")) or v < 0:
        return {"ok": False, "amount": None, "stated": True,
                "reason": ("%s is %r, which is not a non-negative number of dollars. The slot "
                           "sends no orders and alerts, because reading it as 0 would fire a "
                           "top-up on every cent that lands in the account and reading it as "
                           "the default would ignore a figure that was set deliberately."
                           % (MIN_TOPUP_VAR, raw))}
    return {"ok": True, "amount": float(v), "stated": True, "reason": ""}


def allocate_buys(buys, spendable, *, min_order_value: float = 1.0) -> dict:
    """Spread `spendable` across `buys` PROPORTIONALLY. Pure arithmetic; sends nothing.

    `{"orders", "skipped", "fraction", "total_cost", "fillable_cost", "shortfall"}`.

    **EVERY NAME IS SCALED BY THE SAME FRACTION** -- `f = min(1, spendable / total cost)` --
    which is Don's ruling of 2026-10-18. The alternative, and what shipped until now, is to take
    the buys in plan order until the budget runs out: that leaves the first names at full size
    and the rest at zero, so with $2,000 against a $5,000 target the alphabetical tail is simply
    not bought.

    **A SCALED ORDER UNDER `min_order_value` IS SKIPPED AND STAYS IN THE GAP**, rather than
    being rounded up (which would spend more than the fraction allows) or down (which the broker
    refuses anyway). Don accepted the consequence in writing: *"Smaller names lagging behind,
    because their share of a top-up is under `min_order_value`, is accepted. They stay in the gap
    and catch up on a later top-up."*

    **`fillable_cost` IS WHAT WOULD ACTUALLY BE SENT**, which is what the top-up threshold is
    measured against -- not the nominal scaled total, because the names dropped for being too
    small would make a $250 threshold pass on $40 of real orders.
    """
    rows = [dict(o) for o in (buys or [])]
    total = 0.0
    for o in rows:
        try:
            total += float(o["qty"]) * float(o["limit_price"])
        except (TypeError, ValueError, KeyError):
            return {"orders": [], "skipped": [], "fraction": 0.0, "total_cost": None,
                    "fillable_cost": 0.0, "shortfall": None,
                    "reason": "a planned buy carried no usable quantity or price"}
    amt = None
    try:
        amt = float(spendable)
    except (TypeError, ValueError):
        amt = None
    if amt is None or amt != amt or amt < 0:
        return {"orders": [], "skipped": [dict(o, why="no spendable figure was reported")
                                          for o in rows],
                "fraction": 0.0, "total_cost": round(total, 2), "fillable_cost": 0.0,
                "shortfall": round(total, 2),
                "reason": "no spendable figure was reported, so nothing is sized"}
    if total <= 0:
        return {"orders": [], "skipped": [], "fraction": 1.0, "total_cost": 0.0,
                "fillable_cost": 0.0, "shortfall": 0.0, "reason": "there is nothing to buy"}
    f = min(1.0, amt / total)
    out_orders, skipped, fill = [], [], 0.0
    for o in rows:
        cost = float(o["qty"]) * float(o["limit_price"])
        scaled_cost = cost * f
        if scaled_cost < float(min_order_value):
            skipped.append(dict(o, why=("its %.1f%% share of the available cash is $%.4f, "
                                        "under the $%.2f minimum order value, so it stays in "
                                        "the gap and catches up on a later top-up"
                                        % (f * 100.0, scaled_cost, min_order_value))))
            continue
        q = float(o["qty"]) * f
        out_orders.append(dict(o, qty=round(q, 9), full_qty=float(o["qty"]),
                               scaled_by=round(f, 9),
                               scaled_cost=round(scaled_cost, 2)))
        fill += scaled_cost
    return {"orders": out_orders, "skipped": skipped, "fraction": round(f, 9),
            "total_cost": round(total, 2), "fillable_cost": round(fill, 2),
            "shortfall": round(max(0.0, total - fill), 2),
            "reason": ("every buy is scaled to %.4f of its gap, which is $%.2f of the $%.2f "
                       "needed" % (f, fill, total))}
