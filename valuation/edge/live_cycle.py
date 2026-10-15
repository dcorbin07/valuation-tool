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
the account's equity and the slot's percentage. A price is read to set a limit, never to decide.
A test walks this module's AST and asserts no such name exists.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

from . import live_slots as LS

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


def parity(live_plan: list, paper_plan: list, *, live_value: float,
           paper_value: float, tolerance: float = PARITY_TOLERANCE) -> dict:
    """Diff a live slot's orders against the paper slot's, SCALED to the same equity.

    §8 requires dry-run parity logged and diffed against the paper book before any real order.
    The two accounts have different equity, so the comparison is per name **as a share of the
    slot's own value** — comparing dollar amounts would report a mismatch on every name purely
    because the accounts differ in size, which is a diff that can never pass and therefore
    never means anything.
    """
    out = {"ok": False, "n_names": 0, "n_mismatch": 0, "worst": None, "mismatches": [],
           "tolerance": tolerance, "reason": ""}
    lv, pv = LS._f(live_value), LS._f(paper_value)
    if not lv or not pv or lv <= 0 or pv <= 0:
        out["reason"] = ("parity needs a positive value on both sides; live=%r paper=%r"
                         % (live_value, paper_value))
        return out

    def _share(plan, total):
        by = {}
        for o in (plan or []):
            t = str(o.get("ticker") or "").upper()
            signed = (1.0 if str(o.get("side")) == "buy" else -1.0)
            val = (LS._f(o.get("qty")) or 0.0) * (LS._f(o.get("limit_price")) or 0.0)
            by[t] = by.get(t, 0.0) + signed * val / total
        return by

    a, b = _share(live_plan, lv), _share(paper_plan, pv)
    names = sorted(set(a) | set(b))
    out["n_names"] = len(names)
    worst = 0.0
    for t in names:
        d = abs(a.get(t, 0.0) - b.get(t, 0.0))
        if d > worst:
            worst, out["worst"] = d, {"ticker": t, "diff_share": round(d, 6)}
        if d > tolerance:
            out["n_mismatch"] += 1
            out["mismatches"].append({"ticker": t, "live_share": round(a.get(t, 0.0), 6),
                                      "paper_share": round(b.get(t, 0.0), 6),
                                      "diff_share": round(d, 6)})
    out["ok"] = (out["n_mismatch"] == 0)
    out["reason"] = ("the live plan matches the paper plan on all %d names within %.3f%%"
                     % (len(names), tolerance * 100.0) if out["ok"] else
                     "%d of %d names differ from the paper plan by more than %.3f%%"
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
           "holdings": dict(state.get("holdings") or {}),
           "open_remainder": False, "reason": ""}
    if client is None or not hasattr(client, "orders"):
        out["reason"] = "no client, or it cannot list orders; the record is left as it was"
        return out
    try:
        orders = client.orders() or []
    except Exception as e:                                              # noqa: BLE001
        out["reason"] = "the broker's orders could not be read (%s)" % type(e).__name__
        return out
    mine_prefix = "%s-" % str(state.get("slot") or "")
    filled, open_left = {}, False
    for o in orders:
        coid = str((o or {}).get("client_order_id") or "")
        if not coid.startswith(mine_prefix):
            continue
        out["n_orders"] += 1
        sym = str((o or {}).get("symbol") or "").upper()
        fq = LS._f((o or {}).get("filled_qty"))
        side = str((o or {}).get("side") or "").lower()
        status = str((o or {}).get("status") or "").lower()
        if status in ("new", "accepted", "partially_filled", "pending_new", "held"):
            open_left = True
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
    out["ok"] = True
    return out


def _marks_for(client, tickers) -> dict:
    """Quotes for the names a cycle would trade. Never raises; a gap becomes a preflight fail."""
    try:
        return client.quotes(sorted(set(tickers)))
    except Exception:                                                   # noqa: BLE001
        return {}


def run_slot(slot, *, pct, armed_state: dict, book: dict, client, equity,
             marks: dict, root: str = None, session_ok: bool = True,
             paper_plan: list = None, paper_value: float = None,
             send: bool = True) -> dict:
    """One slot's cycle. Returns what it did and why. NEVER RAISES.

    `send=False` is what 0% and an out-of-session cycle use: everything is computed and logged
    and nothing is transmitted. It is not a "dry run flag" a caller could forget to set — the
    caller that would arm a slot has to pass `send=True` AND hold a live client, and `armed`
    is the only function that licenses either.
    """
    out = {"slot": str(slot), "pct": pct, "armed": bool(armed_state.get("armed")),
           "event": "none", "acted": False, "orders": [], "sent": [], "alerts": [],
           "preflight": None, "parity": None, "reason": "", "session_ok": bool(session_ok)}
    st = read_state(slot, root)
    st["slot"] = str(slot)
    try:
        held = [q for q in ((book or {}).get("positions") or [])
                if q.get("status") == "held"]

        # RECONCILE FIRST. What the slot holds is a fact about its FILLS, and the plan below
        # is the difference between the targets and that. Without this the plan is the full
        # buy-in on every cycle -- which is exactly what my own second-cycle test caught.
        rec = reconcile(client, st)
        out["reconcile"] = rec
        if rec.get("ok"):
            st["holdings"] = rec["holdings"]
            # STEP 7. Only the PAPER slot feeds the measurement: the brief asks for the first
            # thirty PAPER fills, and pooling a live fill into it would mix two accounts'
            # executions into one figure about the free feed.
            if str(slot) == PAPER_SLOT:
                out["feed_gap"] = record_feed_gap(rec.get("fills") or [], root,
                                                  unfilled=rec.get("unfilled") or 0)

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
        bpos = None
        if client is not None and hasattr(client, "positions"):
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
        out["broker_positions_read"] = (None if bpos is None else len(bpos))

        pf = LS.preflight(book=book, equity=equity, marks=marks,
                          slot_record=st.get("holdings") or {}, pct=pct,
                          broker_positions=bpos)
        out["preflight"] = pf
        if not pf["ok"]:
            # NO ORDERS, PLUS AN ALERT. An error never causes a sale and never changes
            # holdings, so nothing below this line runs.
            out["alerts"].append({"kind": "preflight_failed", "slot": str(slot),
                                  "reason": pf["reason"]})
            out["reason"] = pf["reason"]
            return out

        tg = LS.targets(pct, equity, held)
        if not tg["ok"]:
            out["alerts"].append({"kind": "targets_failed", "slot": str(slot),
                                  "reason": tg["reason"]})
            out["reason"] = tg["reason"]
            return out
        plan = LS.order_plan(tg["targets"], st.get("holdings") or {}, marks)
        out["orders"] = plan["orders"]
        out["skipped"] = plan["skipped"]
        out["slot_value"] = tg["slot_value"]

        # THE TARGETS ARE MET: nothing left to do for this event, so it CLOSES. Recorded here
        # rather than after sending, because "met" is a property of the reconciled holdings
        # and not of whether this particular cycle transmitted anything.
        if not plan["orders"]:
            if key and key != "none" and key not in st["processed"]:
                st["processed"].append(key)
            st["open_event"] = None
            st["last_event_date"] = (book or {}).get("formed_on")
            st["last_pct"] = pct
            write_state(slot, st, root)
            out["reason"] = ("this event's targets are already met, so there is nothing to "
                             "send and the event is closed")
            return out

        if paper_plan is not None:
            out["parity"] = parity(plan["orders"], paper_plan,
                                   live_value=tg["slot_value"], paper_value=paper_value)
            if not out["parity"]["ok"]:
                out["alerts"].append({"kind": "parity_mismatch", "slot": str(slot),
                                      "reason": out["parity"]["reason"]})

        if not (out["armed"] and send and session_ok and client is not None):
            out["reason"] = ("computed %d order(s) and sent none: %s"
                             % (len(plan["orders"]),
                                armed_state.get("reason") if not out["armed"] else
                                ("the session is closed" if not session_ok else
                                 "no client was supplied")))
            return out

        # ---- the only place an order is transmitted -------------------------------------
        for o in plan["orders"]:
            try:
                res = client.place_limit(o["ticker"], o["side"], o["qty"], o["limit_price"],
                                         client_order_id="%s-%s-%s" % (slot, key, o["ticker"]))
            except Exception as e:                                      # noqa: BLE001
                res = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
            rec = {"ticker": o["ticker"], "side": o["side"], "qty": o["qty"],
                   "limit_price": o["limit_price"], "ok": bool(res.get("ok")),
                   "detail": res.get("error") if not res.get("ok") else None}
            out["sent"].append(rec)
            st["attempts"].append(dict(rec, event=key, at=_stamp()))
            if not res.get("ok"):
                out["alerts"].append({"kind": "broker_error", "slot": str(slot),
                                      "reason": "order for %s was rejected: %s"
                                                % (o["ticker"], res.get("error"))})
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
        write_state(slot, st, root)
        out["reason"] = "sent %d order(s) for %s" % (len(out["sent"]), key)
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


def record_feed_gap(rows, root: str = None, *, unfilled: int = 0) -> dict:
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
            json.dump({"fills": fills, "n_unfilled": n_unfilled}, fh, indent=2,
                      sort_keys=True)
            fh.write("\n")
        os.replace(tmp, p)
        out.update(ok=True, n=len(fills), n_unfilled=n_unfilled)
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
        "uncensored_companion": ("the unfilled count -- an order resting at the free feed's "
                                 "mid that expired is that mid not being a traded price"),
        "would_need": ("a market order to measure the costly direction, which this path does "
                       "not place"),
    }
    if not out["complete"]:
        out["reason"] = ("%d of %d fills recorded; the measurement is reported as incomplete "
                         "rather than quoted early" % (out["n"], FEED_GAP_N))
    return out


def run_cycle(*, env=None, mode: str = DRY, only: str = None, root: str = None,
              book=None, now=None, paper_client=None, live_client_factory=None,
              notify_send=None, send=None) -> dict:
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
        from ..screener.market_session import session_state

        sess = session_state(now)
        out["session"] = sess
        session_ok = bool(sess.get("ok"))

        bk = book if book is not None else IF.attach_returns(IF.book_in_force())
        held = [q for q in ((bk or {}).get("positions") or [])
                if q.get("status") == "held"]
        tickers = [str(q.get("ticker") or "").upper() for q in held]

        # ---- the paper slot, on the paper client ----------------------------------------
        paper_plan, paper_value = None, None
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
            # THE PAPER SLOT IS ARMED BY CONSTRUCTION -- it is paper money on a host that
            # cannot be anything else, which is the whole point of proving the path here.
            res = run_slot(PAPER_SLOT, pct=PAPER_PCT,
                           armed_state={"armed": True,
                                        "reason": "the paper slot is always armed: it is "
                                                  "paper money on the paper host"},
                           book=bk, client=pc, equity=eq, marks=marks, root=root,
                           session_ok=session_ok, send=paper_sends)
            out["paper"] = res
            out["alerts"].extend(res.get("alerts") or [])
            paper_plan = res.get("orders")
            paper_value = res.get("slot_value")

        # ---- every live slot -------------------------------------------------------------
        for n in LS.discover_slots(e):
            if only is not None and str(only) != str(n):
                continue
            a = LS.armed(n, e)
            p = LS.slot_pct(n, e)
            pct = p.get("pct")
            client, eq, marks = None, None, {}
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
                except Exception as ex:                                 # noqa: BLE001
                    out["alerts"].append({"kind": "broker_error", "slot": str(n),
                                          "reason": "the live client failed: %s" % ex})
                    client, eq = None, None
            if client is None:
                # AT 0%, PAUSED, OR UNAUTHORIZED: price from the PAPER client so the dry run
                # has marks, and read equity from the live account ONLY if one was built.
                marks = _marks_for(pc, tickers) if pc is not None else {}
                # The dry run needs an equity to size against. Without a live client there is
                # none, so it uses the PAPER account's -- and says so, because a dry run
                # sized on another account's equity is a shape check, not a dollar check.
                try:
                    eq = ((pc.account() or {}).get("equity") if pc is not None else None)
                except Exception:                                       # noqa: BLE001
                    eq = None   # the dry run then refuses at preflight, which is correct
            else:
                marks = _marks_for(client, tickers) if hasattr(client, "quotes") else (
                    _marks_for(pc, tickers) if pc is not None else {})
            res = run_slot(n, pct=pct, armed_state=a, book=bk, client=client, equity=eq,
                           marks=marks, root=root, session_ok=session_ok,
                           paper_plan=paper_plan, paper_value=paper_value,
                           send=bool(live_sends and a["armed"]))
            res["mode"] = mode
            if mode == PAPER:
                res["paper_mode_note"] = ("this is a PAPER-ONLY cycle, so this live slot "
                                          "computed its plan and sent nothing whatever its "
                                          "percentage, arming or keys")
            res["sized_on"] = ("the live account's equity" if client is not None
                               else "the PAPER account's equity, because this slot has no "
                                    "live client -- so the diff is a shape check rather than "
                                    "a dollar check")
            if res.get("parity") is not None:
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
