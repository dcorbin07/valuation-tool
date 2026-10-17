"""THE §8 REAL-MONEY LIVE PATH, ON ALPACA, SHIPPING AT 0%.  [item 58 B]

WHAT THIS IS, AND WHAT DON ASKED FOR VERBATIM
---------------------------------------------
`PAPER_TRACK_CONTRACT.md` §8 (signed 2026-09-02, restored 2026-09-15) authorises a
percentage-of-equity real-money path. It was never built: refused twice, and the second refusal
measured the reason the vendor had to change — Tradier takes whole shares only, so at $5,000 of
book **51 of 68 Index names got zero shares** and the minimum whole book was **$128,562**.
Alpaca allows fractional shares, which is why Don moved.

Don's instruction, 2026-10-14, quoted because it IS the specification:

> *"I want it to be fully disciplined. Buy and hold and pilot at whatever percentage of the
> account is authorized and does that math per stock. Buying and selling only at quarterly
> rebalances and when that percentage changes. Otherwise no other restrictions because that's
> the whole point. If not, then we just have extra room for bugs, errors, and complications"*

THE WHOLE BEHAVIOUR
-------------------
Each stock's target value is `slot_pct × account_equity × weight_in_the_Index_book_in_force`.
The slot buys or sells fractional shares to reach that target, and acts on **exactly three
events**:

  1. a **new rebalance event** on the bound Index record;
  2. a **change in the slot's own percentage** — 0→X buys in, X→Y resizes, X→0 sells out;
  3. **nothing else.** No loss stops, no drawdown rule, no drift rebalancing, no trading
     between events. Dividends sit as cash until the next event.

**THE LOSS STOPS §8 REQUIRED ARE REMOVED BY DON'S INSTRUCTION**, and that removal is recorded in
the contract's §8a rather than inferred from this file. Nothing here halts, trims or freezes on
performance; there is no code path that reads a return and decides to trade.

WHY "FULLY DISCIPLINED" MAKES THE CODE SMALLER, WHICH IS HIS OWN ARGUMENT
-------------------------------------------------------------------------
Every extra rule is a branch that can fire when it should not. The only reads that can cause an
order here are: the book in force, its weights, the account's equity, and the slot's percentage.
A price is read to set a limit and to size the order, never to decide WHETHER to trade.

IF ANYTHING IS BROKEN, THE SLOT DOES NOT TRADE
----------------------------------------------
Before any order is sent, `preflight` checks the inputs and the arithmetic. If any check fails
the slot sends **no orders that cycle**, alerts Don with the reason, and checks again next
cycle. **An error never causes a sale and never changes holdings** — which is why every refusal
returns the same empty order list rather than a partial one. These checks are about the
software, never about performance.

SEPARATION, WHICH IS THE PART THAT MATTERS MOST
-----------------------------------------------
* The live client is a **different class** from the paper broker and accepts **only** the live
  host (`_LiveClient`). `alpaca_broker.AlpacaPaperBroker` accepts only the paper host. Neither
  can be pointed at the other's.
* **No live client is constructed at all** unless the slot's keys exist, `LIVE_PILOT_ENABLED=1`,
  its percentage is above 0, and — for any slot but 1 — the contract carries that holder's own
  signed authorization. At 0%, which is how every slot ships, the cycle computes the orders it
  *would* place, logs them, diffs them against the paper book, and **returns without
  constructing a client**.
* A lane never sets a percentage, never enters a key and never triggers a live order: the only
  trigger is the service's own scheduled cycle, and the keys exist only in Render's environment.

PAUSING IS NOT ZERO, AND CONFUSING THEM WOULD SELL DON'S BOOK
-------------------------------------------------------------
* `LIVE_PILOT_ENABLED=0` — **PAUSE.** Every slot stops acting. Nothing is sold, holdings stay
  exactly as they are, and no target is computed. It is the global kill switch §8 requires.
* `ALPACA_ACCOUNT_<n>_LIVE_PCT=0` — **A TARGET OF ZERO.** That is an instruction to hold
  nothing, so the slot SELLS what it bought, at the next cycle.

They are opposite in effect and one character apart in an environment panel, so `status()`
states the difference in words on every read.
"""
from __future__ import annotations

import datetime as _dt
import os
import re
from typing import Optional
from urllib.parse import urlparse

#: The LIVE host. This module is the only one permitted to name it as a target.
LIVE_BASE = "https://api.alpaca.markets"
LIVE_HOST = "api.alpaca.markets"

#: The paper host, named ONLY to refuse it: a live slot pointed at paper would silently do
#: nothing real while reporting success, which is the same class of error as the reverse.
PAPER_HOST = "paper-api.alpaca.markets"

#: The global kill switch, §8's requirement. Anything other than exactly "1" is a pause --
#: `MA6`'s rule, err toward the state that refuses, so a typo pauses rather than arms.
ENABLED_VAR = "LIVE_PILOT_ENABLED"

#: Retired by item 58. `ALPACA_LIVE_PCT` was an earlier draft's single-account name and is
#: READ NOWHERE: a slot's percentage comes only from `ALPACA_ACCOUNT_<n>_LIVE_PCT`. Honouring
#: it as an alias would mean an old variable silently arming slot 1.
RETIRED_VARS = ("ALPACA_LIVE_PCT",)

_SLOT_RX = re.compile(r"^ALPACA_ACCOUNT_(\d+)_KEY_ID$")

#: How a holder's authorization is recognised in the contract, read the way
#: `index_track.gate_state()` reads its own row: a table row, matched on the slot number, whose
#: verdict cell is an explicit YES. Anything unrecognised is NOT authorized.
_AUTH_RX_TMPL = (r"^\|\s*Slot\s+%d\s+live\s+authorization\s*\|\s*"
                 r"(YES[^|]*|yes[^|]*)\|")


class NotLiveError(RuntimeError):
    """Raised when anything about a live slot's configuration is not unambiguously correct."""


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def assert_live_host(base: str) -> str:
    """Fail unless `base` is exactly Alpaca's LIVE endpoint. Returns it normalised."""
    b = (base or "").strip().rstrip("/")
    u = urlparse(b)
    host = (u.hostname or "").lower()
    if u.scheme != "https" or host != LIVE_HOST:
        raise NotLiveError(
            "the live path refuses %r: it must be %r (host %s). A live slot pointed at the "
            "paper host would report success while doing nothing real." % (b, LIVE_BASE,
                                                                           LIVE_HOST))
    return b


def pilot_enabled(env=None) -> bool:
    """Is the global switch on? Anything but exactly "1" is a pause."""
    e = env if env is not None else os.environ
    return str(e.get(ENABLED_VAR, "") or "").strip() == "1"


def discover_slots(env=None) -> list:
    """Every slot `n` that has BOTH keys, in numeric order. Keys are never returned.

    Discovery is by the presence of a KEY PAIR rather than of a percentage, deliberately: a
    slot whose percentage variable is missing **defaults to 0** and must still be discovered,
    or a new account would be invisible rather than idle.
    """
    e = env if env is not None else os.environ
    out = []
    for name in e:
        m = _SLOT_RX.match(name or "")
        if not m:
            continue
        n = int(m.group(1))
        if not (e.get("ALPACA_ACCOUNT_%d_KEY_ID" % n, "") or "").strip():
            continue
        if not (e.get("ALPACA_ACCOUNT_%d_SECRET_KEY" % n, "") or "").strip():
            continue
        out.append(n)
    return sorted(set(out))


def slot_pct(n: int, env=None) -> dict:
    """The slot's percentage, 0-100, or a refusal. A missing value is 0, never a default-on."""
    e = env if env is not None else os.environ
    raw = (e.get("ALPACA_ACCOUNT_%d_LIVE_PCT" % n, "") or "").strip()
    if raw == "":
        return {"ok": True, "pct": 0.0, "stated": False,
                "reason": "no percentage is set, so this slot is at 0% and does nothing"}
    v = _f(raw)
    if v is None or v < 0.0 or v > 100.0:
        # A BAD VALUE IS NOT 0 AND IS NOT IGNORED. It is a broken input, so the slot refuses
        # to act -- treating it as 0 would SELL the book on a typo.
        return {"ok": False, "pct": None, "stated": True,
                "reason": ("ALPACA_ACCOUNT_%d_LIVE_PCT is %r, which is not a number between 0 "
                           "and 100. The slot sends no orders and alerts, because reading it "
                           "as 0 would sell the book on a typo." % (n, raw))}
    return {"ok": True, "pct": float(v), "stated": True, "reason": ""}


def holder(n: int, env=None) -> str:
    e = env if env is not None else os.environ
    return (e.get("ALPACA_ACCOUNT_%d_HOLDER" % n, "") or "").strip() or "unnamed"


def holder_authorized(n: int, contract_text: str = None) -> dict:
    """Is this slot's holder authorized by the contract? Slot 1 is Don's and needs no row.

    §8: *"Family slots remain at 0 until each account holder's own signed authorization"*. Read
    from `PAPER_TRACK_CONTRACT.md` the way `index_track.gate_state()` reads its gate row, so
    there is one way this project turns a signed document into a boolean.
    """
    if int(n) == 1:
        return {"ok": True, "authorized": True, "reason": "slot 1 is Don's own account",
                "row": "n/a"}
    txt = contract_text
    if txt is None:
        try:
            from ..screener import index_track as IT
            with open(IT.contract_path(), encoding="utf-8") as fh:
                txt = fh.read()
        except Exception as e:                                          # noqa: BLE001
            return {"ok": False, "authorized": False,
                    "reason": ("the contract could not be read (%s), so no holder "
                               "authorization can be confirmed" % type(e).__name__)}
    rx = re.compile(_AUTH_RX_TMPL % int(n), re.M)
    if rx.search(txt or ""):
        return {"ok": True, "authorized": True,
                "reason": "the contract carries a signed authorization for slot %d" % n,
                "row": "Slot %d live authorization" % n}
    # EVERY UNRECOGNISED OUTCOME IS NOT-AUTHORIZED: a missing file, a malformed table, a row
    # that says anything but YES. The failure direction is "stays at 0%".
    return {"ok": True, "authorized": False,
            "reason": ("the contract carries no signed authorization row for slot %d, so it "
                       "stays at 0%% whatever its percentage says" % n),
            "row": "Slot %d live authorization" % n}


def isolation(env=None) -> dict:
    """Do any two slots share a credential? Returns the clashes; never the credentials."""
    e = env if env is not None else os.environ
    seen, clashes = {}, []
    for n in discover_slots(e):
        for which in ("KEY_ID", "SECRET_KEY"):
            v = (e.get("ALPACA_ACCOUNT_%d_%s" % (n, which), "") or "").strip()
            if not v:
                continue
            if v in seen and seen[v] != n:
                clashes.append({"slots": sorted([seen[v], n]), "field": which.lower()})
            else:
                seen[v] = n
    return {"ok": not clashes, "clashes": clashes,
            "reason": ("" if not clashes else
                       "two slots share a credential, so they are the same account under two "
                       "names: %s" % clashes)}


def armed(n: int, env=None, contract_text: str = None) -> dict:
    """Is this slot allowed to send a real order? Four conditions, all required.

    **THIS IS THE ONLY FUNCTION THAT MAY SAY YES**, and nothing constructs a live client without
    it. The conditions are evaluated in the order that reveals the most useful reason first.
    """
    e = env if env is not None else os.environ
    out = {"slot": int(n), "armed": False, "reason": "", "holder": holder(n, e),
           "pct": None, "pilot_enabled": pilot_enabled(e)}
    if int(n) not in discover_slots(e):
        out["reason"] = "slot %d has no key pair configured" % n
        return out
    if not out["pilot_enabled"]:
        out["reason"] = ("%s is not 1, so every slot is PAUSED. Nothing is sold and holdings "
                         "stay exactly as they are." % ENABLED_VAR)
        return out
    p = slot_pct(n, e)
    out["pct"] = p.get("pct")
    if not p["ok"]:
        out["reason"] = p["reason"]
        return out
    if (p["pct"] or 0.0) <= 0.0:
        out["reason"] = ("slot %d is at 0%%, so it holds nothing. At 0%% the cycle computes "
                         "and logs the orders it would place and sends none." % n)
        return out
    auth = holder_authorized(n, contract_text)
    if not auth["authorized"]:
        out["reason"] = auth["reason"]
        return out
    iso = isolation(e)
    if not iso["ok"]:
        out["reason"] = iso["reason"]
        return out
    out["armed"] = True
    out["reason"] = "slot %d is armed at %.4g%% for %s" % (n, p["pct"], out["holder"])
    return out


# --------------------------------------------------------------------------- #
# The per-stock arithmetic — the whole of what the slot decides
# --------------------------------------------------------------------------- #
def targets(pct: float, equity: float, positions) -> dict:
    """`{ticker: target_value}` for a slot. THE ONLY SIZING RULE IN THE LIVE PATH.

    `target_i = pct/100 × equity × w_i`, with the weights renormalised over the HELD names so
    a book carrying an exited position at zero weight still deploys the slot's full percentage.
    Returns a refusal rather than a partial map when the inputs cannot support it.
    """
    p, eq = _f(pct), _f(equity)
    if p is None or p < 0 or p > 100:
        return {"ok": False, "reason": "the percentage %r is not between 0 and 100" % (pct,)}
    if eq is None or eq <= 0:
        return {"ok": False, "reason": "account equity %r is not a positive number" % (equity,)}
    held = [q for q in (positions or [])
            if str((q or {}).get("ticker") or "").strip()
            and (_f((q or {}).get("weight")) or 0.0) > 0]
    tw = sum(_f(q.get("weight")) or 0.0 for q in held)
    if not held or tw <= 0:
        return {"ok": False, "reason": "the book carries no held position with a weight"}
    slot_value = (p / 100.0) * eq
    out = {}
    for q in held:
        w = (_f(q.get("weight")) or 0.0) / tw
        out[str(q["ticker"]).upper()] = slot_value * w
    return {"ok": True, "targets": out, "slot_value": slot_value, "n": len(out),
            "weights_renormalised_over": len(held)}


def order_plan(targets_map: dict, held_by_slot: dict, marks: dict, *,
               min_order_value: float = 1.0, resting=None) -> dict:
    """The orders that move the slot's own holdings to `targets_map`. Limit orders only.

    `held_by_slot` is **the slot's OWN record** of what it bought, never the broker's whole
    position list — Don's other holdings in the account are never touched, and that is enforced
    by what this function is given rather than by a filter it could forget to apply.

    **A NAME ABSENT FROM `targets_map` IS NOT IN THE PLAN AT ALL, and that is load-bearing
    rather than incidental.** It is what makes the paragraph above true by construction. An
    EXIT is expressed as an explicit target of ZERO, which this function sells in full -- and
    building those zero targets is `run_slot`'s job, because deciding that a held name should
    no longer be held is a statement about the BOOK and not about a price.

    I briefly made this iterate the holdings as well, to sell a name the book had dropped. Item
    58's `test_a_name_the_slot_did_not_buy_is_not_in_the_plan_at_all` caught it by planning a
    sale of `DONS_OWN` -- a defensive contract catching a change that would have sold a holding
    the slot never bought.

    **`resting` IS THIS SLOT'S OWN UNFILLED ORDERS, AND SUBTRACTING THEM IS WHAT STOPS A
    REMAINDER STACKING [item 67 part 0].** `have` is otherwise FILLED quantity alone, so a
    cycle that finds last cycle's order still working re-plans the whole remainder on top of it
    -- five cycles, five full orders, five times the authorised target. The auditor reproduced
    exactly that, and item 64's five-cron schedule makes two or three in-window cycles routine.

    **ONLY THE SAME SIDE IS SUBTRACTED.** An opposite-side resting order is CANCELLED just
    before the send (item 65's confirmed-cancel machinery), so subtracting it as well would
    over-size this order by exactly the quantity about to be cancelled -- a stacking fix that
    stacks. My first cut netted the two and did that: held 6, resting sell 6, target 6 planned
    a buy of 6, the cancel removed the sell, and the account ended at 12.

    A SELL is still capped at what is actually HELD, so this can never plan a short. One
    residual, bounded and stated: if a target SHRINKS while a buy rests, the resting buy still
    fills and overshoots -- by at most the target authorised when that order was placed, and
    the next cycle sells it down. One previously-authorised order, not five, and
    self-correcting.
    """
    orders, skipped = [], []
    # **PER TICKER AND PER SIDE, from this slot's own orders only.** `reconcile` has already
    # filtered by the `valquo-<slot>-` prefix; an entry whose open quantity could not be read
    # is counted as ZERO rather than skipped silently, and reported, because a resting order of
    # unknown size is the one case this cannot subtract.
    pend_buy, pend_sell, unknown = {}, {}, []
    for r in (resting or []):
        tk = str((r or {}).get("ticker") or "").strip().upper()
        if not tk:
            continue
        q = _f((r or {}).get("qty_open"))
        if q is None:
            # **AND THAT NAME DOES NOT TRADE, which my first cut got backwards.** It reported
            # the unknown and planned the full remainder anyway -- failing OPEN in the one
            # state the subtraction exists for. An unreadable open quantity means the
            # committed quantity is unknown, and planning against an unknown is how the
            # stacking happened.
            unknown.append(tk)
            continue
        if str((r or {}).get("side") or "").lower() == "sell":
            pend_sell[tk] = pend_sell.get(tk, 0.0) + max(0.0, q)
        else:
            pend_buy[tk] = pend_buy.get(tk, 0.0) + max(0.0, q)
    held_now = {str(k).upper(): v for k, v in (held_by_slot or {}).items()
                if (_f(v) or 0.0) > 0}
    plan_for = {str(k).upper(): v for k, v in (targets_map or {}).items()}
    unknown_set = set(unknown)
    for tkr, tgt in sorted(plan_for.items()):
        if tkr in unknown_set:
            skipped.append({"ticker": tkr,
                            "reason": ("this slot has an order resting on %s whose open "
                                       "quantity the broker did not report, so what it is "
                                       "already committed to is unknown and nothing more is "
                                       "planned for it this cycle" % tkr)})
            continue
        mark = _f((marks or {}).get(tkr, {}).get("mid") if isinstance(
            (marks or {}).get(tkr), dict) else (marks or {}).get(tkr))
        if mark is None or mark <= 0:
            # A MISSING PRICE IS A BROKEN INPUT, not a reason to trade at any price. The caller
            # turns this into "no orders this cycle" -- see `preflight`.
            skipped.append({"ticker": tkr, "reason": "no usable mark"})
            continue
        have_qty = _f((held_by_slot or {}).get(tkr)) or 0.0
        have_val = have_qty * mark
        # **THE SIDE COMES FROM FILLED HOLDINGS** -- which way does this slot need to move --
        # and the SAME-SIDE resting quantity is then taken off the amount. Only the same side:
        # an opposite-side order is CANCELLED immediately before the send (item 65), so
        # subtracting it would over-size this order by exactly the quantity that is about to be
        # cancelled. My first cut netted the two and did precisely that.
        delta = tgt - have_val
        side = "buy" if delta > 0 else "sell"
        qty = abs(delta) / mark
        already = (pend_buy if side == "buy" else pend_sell).get(tkr, 0.0)
        committed_qty = have_qty + (already if side == "buy" else -already)
        committed_val = committed_qty * mark
        # **WHAT IS ALREADY WORKING ON THIS SIDE IS NOT RE-SENT.** Without this the planner
        # re-plans the whole remainder every cycle and the orders STACK -- five cycles, five
        # full orders, five times the authorised target, which is what the auditor reproduced.
        qty = qty - already
        if qty * mark < float(min_order_value):
            # Already committed to within a dollar, or a move too small to be worth an order.
            continue
        if side == "sell":
            qty = min(qty, have_qty)      # NEVER sell more than this slot bought
            if qty <= 0:
                continue
        orders.append({"ticker": tkr, "side": side, "qty": round(qty, 9),
                       "limit_price": round(mark, 2), "target_value": round(tgt, 2),
                       "current_value": round(have_val, 2),
                       # BOTH, because they answer different questions: what is held, and what
                       # is held plus what is already working. The second is what was planned
                       # against, so it is the one a reader needs to check the arithmetic.
                       "committed_value": round(committed_val, 2),
                       "resting_qty_subtracted": round(already, 9)})
    # **SELLS FIRST, ALWAYS. [item 67]** A rebalance's buys are funded by its sells, so the
    # transmission order decides whether the cash is there when the buy arrives. Alpaca's IRAs
    # run limited margin and let unsettled proceeds be spent, so this may never bind -- but the
    # order costs nothing and the alternative is a buy refused for want of money the same cycle
    # was about to raise. Ticker is the tie-break so the plan is deterministic.
    orders.sort(key=lambda o: (0 if str(o["side"]).lower() == "sell" else 1, o["ticker"]))
    return {"orders": orders, "skipped": skipped,
            "sells_first": True,
            # Named so a reader can see the exits were planned rather than inferring it from a
            # count. A held name whose whole value is under `min_order_value` is dust and is
            # deliberately left alone -- an order that small is refused by the broker anyway.
            "exiting": sorted(t for t in held_now if float(plan_for.get(t) or 0.0) <= 0),
            "resting_considered": sum(len(x) for x in (pend_buy, pend_sell)),
            # **NOT FOLDED INTO A COUNT AND NOT SILENT.** A resting order whose open quantity
            # the broker did not report cannot be subtracted, so the name it is on could still
            # stack. It has never happened -- Alpaca sends `qty` on every order -- and if it
            # does, this is what says so.
            "resting_qty_unknown": sorted(set(unknown)),
            "n_sell": sum(1 for o in orders if str(o["side"]).lower() == "sell"),
            "n_buy": sum(1 for o in orders if str(o["side"]).lower() == "buy")}


#: `broker_positions` was not supplied at all -- a caller doing pure arithmetic. DISTINCT from
#: `None`, which means the caller TRIED to read the broker's positions and could not. [item 63]
POSITIONS_NOT_SUPPLIED = object()


def preflight(*, book: dict, equity, marks: dict, slot_record: dict, pct,
              broker_positions=POSITIONS_NOT_SUPPLIED, slot_symbols=None,
              record_is_fresh: bool = False, tolerance: float = 0.01) -> dict:
    """Every "is anything broken" check, in one place. `ok: False` means NO ORDERS this cycle.

    The list is the brief's, and each entry exists because the alternative is an order placed
    on a number nobody checked. **None of these is about performance.**

    **THE RECORD-VERSUS-BROKER CHECK RUNS IN BOTH DIRECTIONS [item 63], and the reverse one is
    what closes a duplicate buy-in.** The first cut iterated `slot_record` only, so it fired on
    a WRONG record and was blind to a MISSING one -- and an empty record is precisely what
    produces a second full buy-in, because the planner then sees nothing held and plans
    everything. The auditor reproduced it: an empty record against a broker holding the whole
    book passed with zero problems and transmitted.

    `slot_symbols` scopes the reverse direction, and the scope is necessary rather than
    cautious: Don's account may hold names this path never touches, and `reconcile` promises
    those are never read into the record and therefore can never be traded. Refusing on them
    would brick the slot on a healthy account. So the reverse check asks the narrower, correct
    question -- *does the broker hold a position in a name THIS SLOT has itself ordered that
    the record does not know about?* -- and `live_cycle` supplies that set from the slot's own
    `client_order_id`-matched orders plus its recorded intent.

    `broker_positions=None` means the list could NOT BE READ and is a refusal; omitting the
    argument means no broker was consulted and the check is skipped and reported as skipped.
    `None` cannot carry both facts, which is why the sentinel exists.

    **`record_is_fresh` CLOSES THE LAST CORNER OF THAT FAMILY [item 67, the auditor's
    recommendation 2].** The reverse check above is scoped to names this slot has itself
    ordered, which is right -- but the scope is derived from the order read, so state loss PLUS
    an order read that SUCCEEDS AND RETURNS EMPTY leaves an empty scope, every held position
    reads as Don's own, and the whole book is bought a second time. A record with no holdings,
    no processed events and no pinned account id meeting an account that already holds
    something is ambiguous, so it refuses once. **It can fire at most once in a slot's life**,
    on its very first cycle, which is what stops it crying wolf.
    """
    problems = []
    if not isinstance(book, dict) or not book.get("ok"):
        problems.append("the Index book in force could not be read: %s"
                        % ((book or {}).get("reason") or "no reason given"))
    else:
        held = [q for q in (book.get("positions") or []) if q.get("status") == "held"]
        if not held:
            problems.append("the book in force carries no held positions")
        if not book.get("formed_on"):
            problems.append("the book carries no formation date, so it cannot be checked "
                            "for staleness against its own rebalance")
    if _f(equity) is None or (_f(equity) or 0) <= 0:
        problems.append("account equity could not be read as a positive number")
    p = _f(pct)
    if p is None or p < 0 or p > 100:
        problems.append("the slot's percentage is not a number between 0 and 100")
    if not isinstance(marks, dict):
        problems.append("no price map was supplied")
    elif isinstance(book, dict) and book.get("ok"):
        need = [str(q.get("ticker") or "").upper()
                for q in (book.get("positions") or []) if q.get("status") == "held"]
        missing = [t for t in need
                   if not _f((marks.get(t) or {}).get("mid")
                             if isinstance(marks.get(t), dict) else marks.get(t))]
        if missing:
            problems.append("no usable price for %d name(s) the cycle would trade: %s"
                            % (len(missing), ", ".join(missing[:8])))
    positions_checked = False
    if broker_positions is None:
        # AN UNREADABLE POSITION LIST IS A REFUSAL, NOT A SKIP [item 63, auditor question 7].
        # The slot would otherwise transmit without knowing what it already owns -- and the
        # auditor reproduced exactly that: positions unreadable, preflight ok, a second full
        # buy-in sent. The cost of refusing is one skipped cycle; the cost of proceeding is a
        # duplicate position in a real account.
        problems.append("the broker's position list could not be read, so this slot cannot "
                        "know what it already holds and sends nothing this cycle")
    elif broker_positions is not POSITIONS_NOT_SUPPLIED:
        positions_checked = True
        # THE SLOT'S OWN RECORD MUST AGREE WITH THE BROKER on the names it believes it holds.
        # A disagreement means one of the two is wrong, and trading on either would be a guess.
        # EITHER SHAPE. A list of `{ticker, qty}` is what `AlpacaPaperBroker.positions`
        # returns and what this function documents; a `{SYM: qty}` mapping is the obvious
        # thing for a caller to build, and iterating one yields its KEYS -- so the strict
        # version raised `AttributeError` on a string, which a caller's own `except` would
        # report as "this slot failed" and NOT as "the shapes disagree". Accepting both is
        # two lines and removes a whole class of silent misreport.
        if hasattr(broker_positions, "items"):
            by_broker = {str(k).upper(): _f(v) for k, v in broker_positions.items()}
        else:
            by_broker = {str((q or {}).get("ticker") or "").upper(): _f((q or {}).get("qty"))
                         for q in broker_positions}
        for tkr, qty in (slot_record or {}).items():
            theirs = by_broker.get(str(tkr).upper())
            mine = _f(qty) or 0.0
            if theirs is None:
                problems.append("this slot's record holds %s and the broker reports no such "
                                "position" % tkr)
            elif abs((theirs or 0.0) - mine) > max(float(tolerance), abs(mine) * 0.001):
                problems.append("this slot's record holds %.6f of %s and the broker reports "
                                "%.6f" % (mine, tkr, theirs or 0.0))
        # ---- THE REVERSE DIRECTION [item 63] ------------------------------------------
        # A position the broker holds in a name THIS SLOT has ordered, which the record does
        # not know about. That is the empty-record hole, and it is the one that produces a
        # duplicate buy-in rather than a refusal.
        mine_names = {str(t).upper() for t in (slot_record or {})}
        scope = {str(t).upper() for t in (slot_symbols or [])}
        # **AN ENTIRELY FRESH RECORD AGAINST A NON-EMPTY ACCOUNT IS AMBIGUOUS.** Either this is
        # a genuinely new slot in an account holding Don's own names -- fine, and clearing this
        # once costs a cycle -- or the record was lost and these are the slot's own positions,
        # in which case proceeding buys the book twice. The reverse check above cannot tell
        # them apart, because the scope it needs comes from the order read that is missing.
        held_names = sorted(t for t, q in by_broker.items() if (_f(q) or 0.0) > 0)
        if record_is_fresh and held_names:
            problems.append(
                "this slot's record is brand new -- no holdings, no processed event, no "
                "account id -- and the account already holds %d position(s) (%s). That is "
                "either Don's own holdings or this slot's record having been lost, and this "
                "cycle cannot tell which, so it sends nothing. If they are Don's, the next "
                "cycle after this slot records anything at all will not ask again"
                % (len(held_names), ", ".join(held_names[:8])))
        for tkr, qty in sorted(by_broker.items()):
            if tkr in mine_names or tkr not in scope:
                continue
            if (_f(qty) or 0.0) <= 0:
                continue
            problems.append(
                "the broker reports %.6f of %s, which this slot has itself ordered, and this "
                "slot's record does not know about it -- the record is missing or stale, so "
                "acting on it could buy the position a second time" % (_f(qty) or 0.0, tkr))
    return {"ok": not problems, "problems": problems,
            "positions_checked": positions_checked,
            "reason": ("" if not problems else
                       "the slot sends NO orders this cycle and alerts Don: %s"
                       % "; ".join(problems))}


def event_for(slot_state: dict, book: dict, pct) -> dict:
    """Which of the three events, if any, applies this cycle.

    `slot_state` is the slot's own last-acted record: `{last_event_date, last_pct}`.
    """
    last_ev = str((slot_state or {}).get("last_event_date") or "")
    last_pct = _f((slot_state or {}).get("last_pct"))
    formed = str((book or {}).get("formed_on") or "")
    now_pct = _f(pct)
    if formed and formed != last_ev:
        return {"act": True, "event": "rebalance",
                "reason": "the Index book in force was formed %s and this slot last acted on "
                          "%s" % (formed, last_ev or "nothing")}
    if now_pct is not None and (last_pct is None or abs(now_pct - last_pct) > 1e-9):
        kind = ("buy-in" if (last_pct or 0) == 0 and now_pct > 0 else
                ("sell-out" if now_pct == 0 else "resize"))
        return {"act": True, "event": "pct_change", "kind": kind,
                "reason": "the slot's percentage moved from %s to %s (%s)"
                          % ("unset" if last_pct is None else last_pct, now_pct, kind)}
    return {"act": False, "event": "none",
            "reason": ("no rebalance since %s and no percentage change, so the slot does "
                       "nothing -- which is the whole point" % (last_ev or "inception"))}


def status(env=None, contract_text: str = None) -> dict:
    """Every slot: holder, percentage, armed or not, and what pausing means. Owner-only.

    **NO CREDENTIAL APPEARS IN THIS PAYLOAD**, and no live client is constructed to build it.
    """
    e = env if env is not None else os.environ
    slots = []
    for n in discover_slots(e):
        a = armed(n, e, contract_text)
        p = slot_pct(n, e)
        slots.append({"slot": n, "holder": holder(n, e),
                      "pct": p.get("pct"), "pct_stated": p.get("stated"),
                      "armed": a["armed"], "reason": a["reason"],
                      "authorized": holder_authorized(n, contract_text)["authorized"]})
    retired = [v for v in RETIRED_VARS if (e.get(v, "") or "").strip() != ""]
    return {
        "slots": slots,
        "n_slots": len(slots),
        "pilot_enabled": pilot_enabled(e),
        "isolation": isolation(e),
        # THE DIFFERENCE, IN WORDS, ON EVERY READ. These two are opposite in effect and one
        # character apart in an environment panel.
        "pause_vs_zero": {
            "pause": ("%s=0 PAUSES every slot. Nothing is sold, holdings stay exactly as they "
                      "are, and no target is computed." % ENABLED_VAR),
            "zero_pct": ("ALPACA_ACCOUNT_<n>_LIVE_PCT=0 is a TARGET OF ZERO: an instruction to "
                         "hold nothing, so the slot SELLS what it bought at the next cycle."),
        },
        "retired_variables_set": retired,
        "retired_note": ("%s is retired and is read NOWHERE. If it is set, delete it and use "
                         "ALPACA_ACCOUNT_1_LIVE_PCT -- honouring an alias would let an old "
                         "variable arm a slot." % ", ".join(RETIRED_VARS)),
        "loss_stops": ("REMOVED by Don's instruction of 2026-10-14 (contract section 8a). "
                       "Nothing here halts, trims or freezes on performance."),
        "as_of": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


class _LiveClient:
    """The LIVE Alpaca client. Constructed only by `arm_and_trade`, only when `armed` says so.

    A separate class from `AlpacaPaperBroker` rather than a flag on it: a boolean that chooses
    between paper and real money is one typo from a real order, and a flag would also let a
    paper book reach this code by passing it.
    """

    def __init__(self, slot: int, key_id: str, secret_key: str, base: str = LIVE_BASE,
                 timeout: int = 25, session=None):
        self.base = assert_live_host(base)
        if not (key_id or "").strip() or not (secret_key or "").strip():
            raise NotLiveError("slot %s has no key pair; no live client is constructed" % slot)
        self.slot = int(slot)
        self._key_id, self._secret = key_id.strip(), secret_key.strip()
        self.timeout, self._session = int(timeout), session

    def _headers(self) -> dict:
        return {"APCA-API-KEY-ID": self._key_id,
                "APCA-API-SECRET-KEY": self._secret,
                "Content-Type": "application/json"}

    def _request(self, method: str, path: str, body: dict = None, params: dict = None):
        import json as _j

        import requests
        sess = self._session or requests
        r = sess.request(method, "%s/%s" % (self.base, str(path).lstrip("/")),
                         headers=self._headers(), params=params or None,
                         data=(_j.dumps(body) if body is not None else None),
                         timeout=self.timeout)
        code = getattr(r, "status_code", 0)
        try:
            payload = r.json()
        except Exception:                                               # noqa: BLE001
            payload = {"raw": getattr(r, "text", "")[:400]}
        if code >= 400:
            return {"ok": False, "status": code, "error": payload}
        return {"ok": True, "status": code, "data": payload}

    def account(self) -> dict:
        return self._request("GET", "/v2/account")

    def positions(self) -> dict:
        return self._request("GET", "/v2/positions")

    def configurations(self) -> dict:
        """`GET /v2/account/configurations`. READ-ONLY -- GET, and nothing is constructed.

        Item 67 part 2: whether the IRA may place a fractional order. Alpaca documents
        `fractional_trading` here -- *"If true, account is able to participate in fractional
        trading"* -- and the same reply carries the options level. **Absence is reported as
        absence**, never as disabled: item 65 is a fresh demonstration that the documentation
        and the wire can disagree, and "the API does not say" is the honest answer when they do.
        """
        got = self._request("GET", "/v2/account/configurations")
        if not got.get("ok"):
            return {"ok": False, "reason": "the account configuration could not be read",
                    "detail": got}
        d = got.get("data") or {}
        has = "fractional_trading" in d
        return {"ok": True, "reported": bool(has),
                "fractional_trading": (bool(d.get("fractional_trading")) if has else None),
                "max_options_trading_level": d.get("max_options_trading_level"),
                "max_margin_multiplier": d.get("max_margin_multiplier"),
                "no_shorting": d.get("no_shorting"),
                "reason": ("fractional trading: %s"
                           % ("enabled" if (has and d.get("fractional_trading"))
                              else "disabled" if has
                              else "NOT REPORTED by this endpoint"))}

    def account_report(self) -> dict:
        """What this account says about itself, in the fields a rebalance depends on.

        READ-ONLY and deliberately NARROW: the settlement fields, the multiplier, and the
        SHAPE of the account number rather than the number. An account number is an identifier
        Don did not ask to see printed, and its shape is the only part any check here uses.
        """
        got = self._request("GET", "/v2/account")
        if not got.get("ok"):
            return {"ok": False, "reason": "the account could not be read", "detail": got}
        d = got.get("data") or {}
        num = str(d.get("account_number") or "")
        return {
            "ok": True, "status": d.get("status"),
            "multiplier": _f(d.get("multiplier")),
            "cash": _f(d.get("cash")),
            "buying_power": _f(d.get("buying_power")),
            "non_marginable_buying_power": _f(d.get("non_marginable_buying_power")),
            "regt_buying_power": _f(d.get("regt_buying_power")),
            "trading_blocked": bool(d.get("trading_blocked")),
            "account_blocked": bool(d.get("account_blocked")),
            # THE SHAPE, NOT THE NUMBER.
            "account_number_shape": ("%d characters, starts with %s"
                                     % (len(num), (num[:1] or "(nothing)"))),
        }

    def assets(self, symbols=None) -> dict:
        """`fractionable` and `tradable` per symbol from Alpaca's asset master. READ-ONLY.

        One request for the whole active US equity master rather than one per name, and a
        symbol MISSING from it is reported missing rather than as `fractionable: False` --
        absent is not a measured False (`C5`), and the two have different fixes.
        """
        got = self._request("GET", "/v2/assets",
                            params={"status": "active", "asset_class": "us_equity"})
        if not got.get("ok"):
            return {"ok": False, "reason": "the asset master could not be read",
                    "detail": got, "assets": {}, "n_master": 0}
        by = {}
        for r in (got.get("data") or []):
            if not isinstance(r, dict):
                continue
            sym = str(r.get("symbol") or "").strip().upper()
            if sym:
                by[sym] = {"fractionable": bool(r.get("fractionable")),
                           "tradable": bool(r.get("tradable")),
                           "exchange": r.get("exchange"), "status": r.get("status")}
        want = ([str(x).strip().upper() for x in symbols if str(x).strip()]
                if symbols is not None else sorted(by))
        return {"ok": True, "n_master": len(by),
                "assets": {k: by[k] for k in want if k in by},
                "missing": [k for k in want if k not in by],
                "reason": "read %d active US equities from the asset master" % len(by)}

    def positions_result(self) -> dict:
        """`{"ok", "data", "reason"}`, matching `AlpacaPaperBroker.positions_result` exactly.
        [item 65]

        This client's `positions()` already returns the `_request` envelope, so a failure is
        visible here -- but the paper client's was not, and `run_slot` runs on both. One shape
        on both clients is the point: a divergence at a read is how the auditor's blocker
        reached a second buy-in, and a divergence at a WRITE is how blocker 1 stopped the paper
        slot trading at all.
        """
        got = self._request("GET", "/v2/positions")
        if not got.get("ok"):
            return {"ok": False, "data": [],
                    "reason": "the broker's positions could not be read (HTTP %s)"
                              % got.get("status")}
        rows = got.get("data") or []
        return {"ok": True,
                "data": [{"ticker": str((p or {}).get("symbol") or "").upper(),
                          "qty": _f((p or {}).get("qty"))} for p in rows],
                "reason": ""}

    def orders_result(self, status: str = "all", limit: int = 100) -> dict:
        """`{"ok", "data", "reason", "truncated"}` -- see `positions_result`. [item 65]

        **PAGED [item 67 part 0].** One event produced 239 orders, so a single 500-order page
        fills in about two events. `truncated` is a refusal the caller honours, not a partial
        answer -- see `paged_orders`.
        """
        from .settlement import paged_orders

        res = paged_orders(
            lambda p: self._request("GET", "/v2/orders", params=p),
            page_limit=int(limit), status=status)
        return {"ok": bool(res.get("ok")), "data": list(res.get("data") or []),
                "truncated": bool(res.get("truncated")), "pages": res.get("pages"),
                "reason": ("" if (res.get("ok") and not res.get("truncated"))
                           else res.get("reason") or "")}

    def orders(self, status: str = "all", limit: int = 100) -> list:
        """THIS SLOT'S ORDERS, raw, for `live_cycle.reconcile` to total the fills from.

        Returns a LIST and never raises, matching `AlpacaPaperBroker.orders` exactly -- because
        `reconcile` runs on both and a shape difference between the two clients would make the
        paper slot prove a program the live slot does not run.

        Without this a live slot's holdings record would never advance past empty, and every
        cycle would plan the full buy-in again: the defect that was just repaired, surviving on
        the one path where repeating an order costs real money.
        """
        got = self._request("GET", "/v2/orders",
                            params={"status": status, "limit": int(limit)})
        return list(got.get("data") or []) if got.get("ok") else []

    def cancel(self, order_id) -> dict:
        """Cancel one resting order. `{"ok", "detail"}`, matching the paper client. [item 65]

        **IT EXISTS BECAUSE `run_slot` NOW NEEDS IT AND ONLY ONE CLIENT HAD IT** -- the fourth
        divergence between these two classes on this path, after the `place_limit` NAME, the two
        failure-reply KEYS and the two READ paths. Alpaca refuses one side of a name while an
        order rests on the other (*"potential wash trade detected"*), and the answer is to clear
        the obstruction rather than to place a complex order.

        A 404 counts as cancelled: the order is not resting, which is the property the caller
        needs. A 422 does NOT -- Alpaca returns it when an order is already filled, and a filled
        order is a holdings fact the caller must not paper over.
        """
        got = self._request("DELETE", "/v2/orders/%s" % order_id)
        ok = bool(got.get("ok")) or int(got.get("status") or 0) == 404
        return {"ok": ok, "detail": got}

    def place_limit(self, ticker: str, side: str, qty: float, limit_price: float,
                    client_order_id: str = None) -> dict:
        """A LIMIT order, `time_in_force=day`, per §8 and Alpaca's fractional constraint."""
        body = {"symbol": str(ticker).upper(), "side": str(side).lower(), "type": "limit",
                "qty": ("%.9f" % float(qty)).rstrip("0").rstrip("."),
                "limit_price": "%.2f" % float(limit_price), "time_in_force": "day"}
        if client_order_id:
            body["client_order_id"] = str(client_order_id)
        return self._request("POST", "/v2/orders", body=body)
