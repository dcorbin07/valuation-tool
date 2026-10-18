# -*- coding: utf-8 -*-
"""ITEM 71 — THE TRANSITION TABLE. One declaration, every combination, four facts per row.

**WHY A TABLE INSTEAD OF A SEVENTH PATCH.** Six auditor reviews have each found a new state the
close or send logic mishandled, and each correct fix exposed the next — because the states are
nested and nobody had ever written down what the whole space is:

| review | the two states that shared one value |
|---|---|
| 1 | `place_limit` — two names for one call |
| 2 | `[]` — both "nothing there" and "the request failed" |
| 3 | truncated versus failed |
| 4 | three populations for one "which names does this cycle need" |
| 5 | "nothing left to plan" versus "nothing left to do" |
| 6 | "did not ask" versus "nothing working", and "0% flat" versus "0% holding" |

So this file declares the space and the expected outcome for every point in it, and asserts the
code agrees. **A row where the code differs from the declaration is a defect.**

**2,240 rows. 1,641 of them were wrong before item 71** -- measured by running this same
declaration against the pre-item-71 sources restored from git, which is the control that stops
the table being a mirror of the implementation. Reproduce with:

    python scripts/i71_table_before.py

and that script carries the breakdown by defect kind, plus the one artefact it excludes and why.

WHAT EACH ROW ASSERTS — the four facts the brief names
-----------------------------------------------------
1. **what is SENT** — nothing at all, sells only, or orders that may include buys;
2. **what is WRITTEN** — the slot's own record file, compared BYTE-FOR-BYTE before and after,
   which is the only way to assert "writes nothing" rather than "writes nothing important";
3. **whether the event stays OPEN or CLOSES** — `event_closed`, plus `open_event` and
   `processed` read off the record;
4. **whether Don is ALERTED.**

THE EXPECTATION IS DERIVED FROM THE REQUIREMENTS, NOT FROM THE IMPLEMENTATION
-----------------------------------------------------------------------------
`expected()` below is written from §8's three clauses, `DECISIONS.md`'s three authorised events
and the six reviews' rulings — each rule carrying its source. **It could still be a mirror of
the code's bugs, and the control for that is the pre-item-71 measurement**: the same table run
against the tree before this item disagrees on a large number of rows, which it could not do if
the declaration had been read off the implementation.

THE SIZE, AND WHAT IS PRUNED, STATED RATHER THAN IMPLIED
---------------------------------------------------------
The brief's axes cross to **7 × 5 × 4 × 3 × 3 × 4 × 2 = 10,080** rows, and one row costs ~27 ms
of real `run_cycle` with recorded HTTP — about 4.5 minutes. The three READ axes are therefore
crossed **marginally** (vary one, hold the others at `ok`): 4 + 3 + 3 − 2 = **8** read states
rather than 36. That is a real reduction and it carries a real assumption — that the three reads
do not interact — so the assumption is **measured rather than asserted**:
`TheThreeReadsAreCrossedFullyOnOneCell` runs all 36 on a representative cell.

Every HTTP reply here is a recorded fixture. Nothing touches a network and nothing places a real
order: the live client is injected through `live_client_factory` and its host is never contacted.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import io
import itertools
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

import tests.test_item63 as T63                        # noqa: E402
from valuation.edge import alpaca_broker as AB         # noqa: E402
from valuation.edge import live_cycle as LC            # noqa: E402
from valuation.edge import live_slots as LS            # noqa: E402

OPEN_NOW = _dt.datetime(2026, 11, 2, 13, 36)

#: The book in force. Two names, equal weight, formed on the rebalance date.
FORMED = "2026-11-01"
BOOK = {"ok": True, "formed_on": FORMED, "reason": "",
        "positions": [{"ticker": "AAPL", "status": "held", "weight": 0.5},
                      {"ticker": "BBB", "status": "held", "weight": 0.5}]}
#: The PREVIOUS book, for events that are not a rebalance.
BOOK_OLD = dict(BOOK, formed_on="2026-08-01")

ACCOUNT = {"id": "acct-live-1", "account_number": "L1", "equity": "10000", "cash": "10000",
           "buying_power": "10000", "non_marginable_buying_power": "10000",
           "status": "ACTIVE", "multiplier": "1"}
PAPER_ACCOUNT = dict(ACCOUNT, id="acct-paper-1", account_number="PA1")

#: 5% of $10,000 over two equal weights at a $100 mid = 2.5 shares each. Every fixture's
#: holdings are stated in these units so "the targets are met" is a declared fact rather than
#: arithmetic this file re-does.
ON_TARGET = 2.5


# --------------------------------------------------------------------------------------- #
# THE RECORDED BROKER
# --------------------------------------------------------------------------------------- #
class Rec:
    """One recorded Alpaca session, driving the real `AlpacaPaperBroker` and `_LiveClient`.

    `orders_read`, `positions_read` and `quotes_read` are the three READ axes, each reproducing
    a real failure rather than a stub that raises -- which is item 65's lesson: neither real
    client raises, so a stub that does tests nothing.
    """

    FULL_PAGE = 500          # what `reconcile` treats as "there may be more"

    def __init__(self, *, holdings, resting=(), account=None, slot="1",
                 orders_read="ok", positions_read="ok", quotes_read="ok"):
        self.holdings, self.resting = dict(holdings), list(resting)
        self.acct = dict(account or ACCOUNT)
        self.slot = slot
        self.orders_read = orders_read
        self.positions_read = positions_read
        self.quotes_read = quotes_read
        self.placed, self.cancelled, self.calls = [], [], []

    def _orders(self):
        out = []
        for t, q in sorted(self.holdings.items()):
            if float(q) <= 0:
                continue
            out.append({"id": "f-" + t, "client_order_id": LC.client_order_id(
                self.slot, "rebalance:2026-07-30", t), "symbol": t, "side": "buy",
                "qty": str(q), "filled_qty": str(q), "status": "filled",
                "limit_price": "100", "filled_avg_price": "100",
                "submitted_at": "2026-07-30T14:40:00Z"})
        for i, (t, side, qty, fq, ev) in enumerate(self.resting):
            out.append({"id": "r-%d" % i, "client_order_id": LC.client_order_id(
                self.slot, ev, t, attempt=1), "symbol": t, "side": side, "qty": str(qty),
                "filled_qty": str(fq), "status": "new", "limit_price": "100",
                "filled_avg_price": None, "submitted_at": "2026-11-02T14:30:00Z"})
        return out

    def request(self, method, url, headers=None, params=None, data=None, timeout=None):
        self.calls.append((method, url))
        if url.endswith("/v2/account"):
            return T63.Reply(dict(self.acct))
        if url.endswith("/v2/account/configurations"):
            return T63.Reply({"fractional_trading": True})
        if "/v2/assets" in url:
            return T63.Reply([{"symbol": s, "fractionable": True, "tradable": True,
                               "exchange": "NASDAQ", "status": "active",
                               "class": "us_equity"} for s in ("AAPL", "BBB")])
        if url.endswith("/v2/positions"):
            if self.positions_read == "unreadable":
                # A REAL FAILURE SHAPE: the broker answers with an error status, which is what
                # `positions_result` turns into `ok=False`. Not an exception -- the shipped
                # client does not raise (item 65).
                return T63.Reply({"message": "forbidden"}, status=403)
            if self.positions_read == "empty":
                return T63.Reply([])
            eff = dict(self.holdings)
            for t, side, qty, fq, ev in self.resting:
                if float(fq or 0):
                    eff[t] = eff.get(t, 0.0) + (float(fq) if side == "buy"
                                                else -float(fq))
            return T63.Reply([{"symbol": t, "qty": str(q), "avg_entry_price": "100",
                               "side": "long"} for t, q in sorted(eff.items())
                              if float(q) > 0])
        if "quotes/latest" in url:
            if self.quotes_read == "none":
                return T63.Reply({"quotes": {}})
            q = {s: {"bp": 99.0, "ap": 101.0, "t": "x"}
                 for s in ("AAPL", "BBB", "MSFT", "SPY")}
            if self.quotes_read == "one_missing":
                # ONE-SIDED, which is the real IEX failure: a bid and no ask gives no mid.
                q["BBB"] = {"bp": 99.0, "ap": 0.0, "t": "x"}
            return T63.Reply({"quotes": q})
        if url.endswith("/v2/orders") and method == "GET":
            if self.orders_read == "failed":
                return T63.Reply({"message": "server error"}, status=500)
            if self.orders_read == "truncated":
                rows = self._orders()
                pad = [dict(rows[0] if rows else {
                    "id": "p", "client_order_id": "other-x", "symbol": "ZZZ", "side": "buy",
                    "qty": "1", "filled_qty": "0", "status": "canceled",
                    "limit_price": "1", "filled_avg_price": None,
                    "submitted_at": "2026-01-01T00:00:00Z"},
                    id="pad-%d" % i, client_order_id="other-%d" % i)
                    for i in range(self.FULL_PAGE)]
                return T63.Reply(pad)
            return T63.Reply(self._orders())
        if url.endswith("/v2/orders") and method == "POST":
            body = json.loads(data or "{}")
            self.placed.append(body)
            return T63.Reply(dict(body, id="srv-%d" % len(self.placed), status="new",
                                  filled_qty="0"))
        if "/v2/orders/" in url and method == "DELETE":
            self.cancelled.append(url.rsplit("/", 1)[-1])
            return T63.Reply({}, status=204)
        return T63.Reply({}, status=404)


# --------------------------------------------------------------------------------------- #
# THE AXES
# --------------------------------------------------------------------------------------- #
#: SLOT STATE. `holds` is DECLARED by construction rather than computed, so
#: the expectation never re-does the arithmetic the code under test performs.
#:   record   -- the slot's own `holdings`
#:   resting  -- orders still working at the broker, as (ticker, side, qty, filled, event)
#:   open_ev  -- the event the record says is still open, if any
STATES = {
    "fresh":            dict(record={}, resting=(), open_ev=None, holds=False),
    "on_target":        dict(record={"AAPL": ON_TARGET, "BBB": ON_TARGET}, resting=(),
                             open_ev=None, holds=True),
    "off_target":       dict(record={"AAPL": 1.0}, resting=(), open_ev=None, holds=True),
    "resting_same":     dict(record={"AAPL": ON_TARGET}, open_ev="rebalance:" + FORMED,
                             resting=(("BBB", "buy", ON_TARGET, 0.0, "rebalance:" + FORMED),),
                             holds=True),
    "resting_opposite": dict(record={"AAPL": ON_TARGET, "BBB": ON_TARGET},
                             open_ev="rebalance:" + FORMED,
                             resting=(("BBB", "sell", 1.0, 0.0, "rebalance:" + FORMED),),
                             holds=True),
    "resting_partial":  dict(record={"AAPL": ON_TARGET, "BBB": 1.0},
                             open_ev="rebalance:" + FORMED,
                             resting=(("BBB", "buy", 1.5, 0.5, "rebalance:" + FORMED),),
                             holds=True),
    # THE BLOCKER-B SHAPE: a remainder open for a DIFFERENT event than the one arriving.
    "mid_event":        dict(record={}, open_ev="rebalance:" + FORMED,
                             resting=(("AAPL", "buy", ON_TARGET, 0.0, "rebalance:" + FORMED),
                                      ("BBB", "buy", ON_TARGET, 0.0, "rebalance:" + FORMED)),
                             holds=False),
}

#: EVENT. `last_*` is what the record says it last acted on; `pct` is the environment now.
EVENTS = {
    "rebalance": dict(last_pct=5.0, last_event="2026-08-01", pct=5.0, book=BOOK),
    "buy_in":    dict(last_pct=0.0, last_event=FORMED, pct=5.0, book=BOOK),
    "resize":    dict(last_pct=5.0, last_event=FORMED, pct=2.0, book=BOOK),
    "sell_out":  dict(last_pct=5.0, last_event=FORMED, pct=0.0, book=BOOK),
    #: TWO EVENTS IN ONE SESSION: a rebalance cycle, then a percentage change, same session.
    "overlap":   dict(last_pct=5.0, last_event="2026-08-01", pct=5.0, book=BOOK,
                      then_pct=0.0),
}

#: READ OUTCOMES, crossed MARGINALLY -- vary one, hold the others at `ok`. See the module
#: docstring for the arithmetic and for the cell where all 36 are crossed.
READS = [
    dict(orders="ok", positions="ok", quotes="ok"),
    dict(orders="truncated", positions="ok", quotes="ok"),
    dict(orders="failed", positions="ok", quotes="ok"),
    dict(orders="not_attempted", positions="ok", quotes="ok"),
    dict(orders="ok", positions="unreadable", quotes="ok"),
    dict(orders="ok", positions="empty", quotes="ok"),
    dict(orders="ok", positions="ok", quotes="one_missing"),
    dict(orders="ok", positions="ok", quotes="none"),
]

MODES = ("live", "paper", "dry", "GET")
PILOTS = ("1", "0")

#: **DOES THIS SLOT'S RECORD ALREADY MEET THIS EVENT'S TARGETS?** Declared per (state, event)
#: rather than computed, because computing it would re-do the arithmetic under test -- and
#: declared per EVENT rather than per state because it is NOT a property of the state: the
#: targets move with the percentage. `on_target` holds 2.5 shares of each name, which IS the
#: 5% target ($250 at a $100 mid) and is NOT the 2% one ($100). My first cut declared it on the
#: state alone and `mid_event` exposed it -- "met" for a sell-out whose target is nothing, then
#: read as "met" for a 5% buy-in as well.
#:
#: The deciding percentage for `overlap` is its SECOND cycle's, which is 0%.
MET = {
    ("fresh", "rebalance"): False, ("fresh", "buy_in"): False,
    ("fresh", "resize"): False, ("fresh", "sell_out"): True,
    ("fresh", "overlap"): True,
    ("on_target", "rebalance"): True, ("on_target", "buy_in"): True,
    ("on_target", "resize"): False, ("on_target", "sell_out"): False,
    ("on_target", "overlap"): False,
    ("off_target", "rebalance"): False, ("off_target", "buy_in"): False,
    ("off_target", "resize"): False, ("off_target", "sell_out"): False,
    ("off_target", "overlap"): False,
    ("resting_same", "rebalance"): False, ("resting_same", "buy_in"): False,
    ("resting_same", "resize"): False, ("resting_same", "sell_out"): False,
    ("resting_same", "overlap"): False,
    ("resting_opposite", "rebalance"): True, ("resting_opposite", "buy_in"): True,
    ("resting_opposite", "resize"): False, ("resting_opposite", "sell_out"): False,
    ("resting_opposite", "overlap"): False,
    ("resting_partial", "rebalance"): False, ("resting_partial", "buy_in"): False,
    ("resting_partial", "resize"): False, ("resting_partial", "sell_out"): False,
    ("resting_partial", "overlap"): False,
    ("mid_event", "rebalance"): False, ("mid_event", "buy_in"): False,
    ("mid_event", "resize"): False, ("mid_event", "sell_out"): True,
    ("mid_event", "overlap"): True,
}



# --------------------------------------------------------------------------------------- #
# THE DECLARATION — written from the requirements, with a source per rule
# --------------------------------------------------------------------------------------- #
def expected(state, event, read, mode, pilot):
    """What this row must and must not do.

    `{"sent", "may_write", "may_close", "armed", "wind_down", "clean"}`.

    **IT STATES THE SAFETY DIRECTION, PLUS ONE POSITIVE CONTROL.** Whether a PERMITTED write
    actually happens depends on which branch ran -- a preflight refusal legitimately persists
    nothing -- so predicting every write exactly would mean re-implementing the branch logic
    here, and a declaration that mirrors the implementation agrees with it on the bugs too.
    What the table asserts instead:

    * `sent` -- `"none"` means **literally nothing may be transmitted**; `"sells_only"` means
      no buy may be; `"any"` means the row is not constrained on direction.
    * `may_write` -- False means the record must be **byte-for-byte unchanged**.
    * `may_close` -- False means `event_closed` must be False.
    * `clean` -- the POSITIVE CONTROL. Without it, code that did nothing at all would satisfy
      every must-not row in the table.

    `sent` does not predict quantities: that is the arithmetic under test and it has its own
    suites.
    """
    st, ev = STATES[state], EVENTS[event]
    # **AN `overlap` ROW REPORTS ITS SECOND CYCLE**, so the deciding percentage is `then_pct`.
    # My first cut armed it on the first cycle's, which is why every overlap row disagreed.
    pct = ev.get("then_pct", ev["pct"]) if event == "overlap" else ev["pct"]
    # **THE PAUSE WINS FIRST, so a PAUSED slot is not winding down [item 71].**
    # `LIVE_PILOT_ENABLED=0` is documented as pausing WITHOUT selling, which is a
    # different instruction from 0%, and the order of `armed`'s conditions is what
    # keeps them different. My first cut left the pilot out of this and every paused
    # row disagreed -- in the SAFE direction, which is why it needed the table to find.
    wind_down = (pilot == "1" and pct <= 0 and st["holds"])

    # ---- WHAT IS WRITTEN -------------------------------------------------------------
    # W1. A GET persists nothing, for any slot. [item 71 blocker C; the door's own rule for
    #     sending, applied to writing]
    # W2. A cycle that did not successfully read its own orders persists nothing -- it does not
    #     know what is working at the broker. [item 71 blocker C]
    #     `not_attempted` is the mode-dependent one: no live client is built outside `live`.
    # A LIVE CLIENT EXISTS ONLY IN `live` MODE FOR AN ARMED SLOT, and the orders read is
    # `not_attempted` without one -- which is why `not_attempted` is the absence of a client
    # rather than a reply a broker can give.
    armed = (pilot == "1") and (pct > 0 or wind_down)
    client = (mode == "live") and armed and read["orders"] != "not_attempted"
    read_ok = bool(client and read["orders"] == "ok")
    may_write = bool(read_ok and mode != "GET")

    # ---- WHAT IS SENT ----------------------------------------------------------------
    # S1. Only `mode=live` may transmit. [§8; `live_sends = (mode == LIVE)`]
    # S2. `LIVE_PILOT_ENABLED` != 1 pauses every slot, without selling. [DECISIONS 2026-10-14]
    # S3. A slot must be ARMED: a positive percentage, or 0% with holdings (the wind-down).
    #     [item 71 blocker A]
    # S4. A wind-down transmits SELLS ONLY. [item 71 blocker A]
    # S5. Nothing transmits unless this slot's own orders were read. [items 65, 67]
    # S6. A missing two-sided quote for a name the cycle needs refuses the cycle. [item 69]
    # S7. An unreadable position list refuses the cycle. [item 63]
    sent = "none"
    if read_ok:
        if read["positions"] == "unreadable" or read["quotes"] in ("one_missing", "none"):
            sent = "none"                      # preflight refuses
        elif read["positions"] == "empty" and st["holds"]:
            sent = "none"                      # record-versus-broker disagreement refuses
        elif wind_down:
            sent = "sells_only"
        else:
            sent = "any"

    # ---- OPEN OR CLOSED --------------------------------------------------------------
    # C1. An event closes only on POSITIVE evidence that nothing is working: the orders read
    #     succeeded, the plan is empty with nothing skipped, no order of this slot's is resting
    #     FOR THIS EVENT, and the open remainder belongs to THIS event. [items 69, 70, 71]
    this_key = _key_for(state, event)
    resting_this_event = any(r[4] == this_key for r in st["resting"])
    open_is_mine = (st["open_ev"] in (None, this_key))
    met = MET[(state, event)]
    if event == "overlap":
        # **NOT ASSERTED, DELIBERATELY.** Whether the first cycle left a remainder open depends
        # on what the first cycle did, and declaring that would mean modelling the
        # implementation here -- which is the one thing this declaration must not do. The
        # safety direction is still asserted on every overlap row, and blocker B's own property
        # has a dedicated test where the sequence is explicit.
        may_close = None
    else:
        may_close = bool(may_write and met and not resting_this_event and open_is_mine
                         and not (read["positions"] == "empty" and st["holds"])
                         and read["quotes"] == "ok")

    # ---- ALERTED ---------------------------------------------------------------------
    # A1. Don is told whenever the cycle refuses for a reason he must act on, and is NOT told
    #     on an ordinary quiet cycle -- an alert that fires on healthy cycles is one nobody
    #     reads on the unhealthy one (`MA21`).
    alerted = None            # None = not asserted on this row (see the dedicated class)
    if read["orders"] in ("truncated", "failed") and client:
        alerted = True

    # ---- THE POSITIVE CONTROL --------------------------------------------------------
    # A CLEAN CYCLE MUST ACT. Without this, code that did nothing whatever would satisfy every
    # must-not row above -- which is the shape of vacuous pass this project keeps paying for.
    # The positive control is not applied to `overlap`, whose outcome depends on the first
    # cycle -- see `may_close` above.
    clean = bool(read_ok and read["positions"] == "ok" and read["quotes"] == "ok"
                 and not (read["positions"] == "empty" and st["holds"])
                 and event != "overlap")
    return {"sent": sent, "may_write": may_write, "may_close": may_close,
            "alerted": alerted, "wind_down": wind_down, "armed": armed, "clean": clean,
            "targets_met": met, "resting_this_event": resting_this_event,
            "open_is_mine": open_is_mine}


def _key_for(state, event):
    """The event key this cycle will act on, from the writer's own generator."""
    ev = EVENTS[event]
    if event == "overlap":
        # **THE SECOND CYCLE'S KEY, not the first's.** An overlap row is measured on its second
        # cycle, which acts on the percentage change -- cycle one wrote `last_pct` as the
        # first percentage, so the key is from that to `then_pct`. My first cut returned the
        # rebalance's key and the record then looked "closed" because CYCLE ONE had closed it.
        return "pct:%s->%s" % (ev["pct"], ev["then_pct"])
    if event == "rebalance":
        return "rebalance:%s" % ev["book"]["formed_on"]
    return "pct:%s->%s" % (ev["last_pct"], ev["pct"])


# --------------------------------------------------------------------------------------- #
# THE RUNNER
# --------------------------------------------------------------------------------------- #
def _digest(root, slot="1"):
    """A byte digest of the slot's own record. `None` when the file does not exist.

    **BYTES, NOT A FIELD COMPARISON.** "Writes nothing" has to mean the file did not change,
    and a comparison of the fields a test happens to name is how a write to an unnamed field
    goes unnoticed.
    """
    p = LC.state_path(str(slot), root)
    if not os.path.exists(p):
        return None
    return hashlib.sha256(io.open(p, "rb").read()).hexdigest()


def run_row(state, event, read, mode, pilot, *, root=None):
    """One row, through the real `run_cycle`. Returns what it did."""
    own = root is None
    root = root or tempfile.mkdtemp()
    try:
        st, ev = STATES[state], EVENTS[event]
        rec = {"slot": "1", "account_id": "acct-live-1", "processed": [],
               "holdings": dict(st["record"]), "last_pct": ev["last_pct"],
               "last_event_date": ev["last_event"]}
        if st["open_ev"]:
            rec["open_event"] = st["open_ev"]
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, sort_keys=True)

        live = Rec(holdings=st["record"], resting=st["resting"],
                   orders_read=read["orders"], positions_read=read["positions"])
        # **THE QUOTE AXIS VARIES THE *PAPER* SESSION, and that is a fact about the code rather
        # than a convenience.** `_marks_for(client, ...) if hasattr(client, "quotes")` --
        # and `_LiveClient` has NO `quotes`, correctly, because Alpaca's market data is on a
        # different host and that class is pinned to one. So a live slot is priced from the
        # PAPER client, and my first cut varied the live session's quotes and varied nothing:
        # a whole axis of this table was inert.
        paper = Rec(holdings={}, account=PAPER_ACCOUNT, slot="paper",
                    quotes_read=read["quotes"])
        env = {"LIVE_PILOT_ENABLED": pilot, "ALPACA_ACCOUNT_1_KEY_ID": "k",
               "ALPACA_ACCOUNT_1_SECRET_KEY": "s" * 24,
               "ALPACA_ACCOUNT_1_LIVE_PCT": str(ev["pct"])}
        before = _digest(root)

        # **`not_attempted` IS THE ABSENCE OF A CLIENT, NOT A REPLY [item 71].** My first cut
        # made it a session behaviour, so in `live` mode a client was still built, the read
        # still succeeded, and the row transmitted two buys against a declaration expecting
        # silence. In production it is what a paper, dry or unarmed cycle produces -- no client
        # is constructed -- so the row withholds the factory.
        factory = (None if read["orders"] == "not_attempted"
                   else (lambda n: LS._LiveClient(n, "k", "s" * 24, session=live)))

        def _cycle(pct_now):
            env2 = dict(env, ALPACA_ACCOUNT_1_LIVE_PCT=str(pct_now))
            return LC.run_cycle(
                env=env2,
                # A GET is a DRY cycle that may not write -- which is exactly how the door
                # calls it: `may_write=(request.method == "POST")`.
                mode=("dry" if mode == "GET" else mode),
                may_write=(mode != "GET"),
                now=OPEN_NOW, root=root, book=ev["book"],
                paper_client=AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24,
                                                  session=paper),
                live_client_factory=factory,
                notify_send=(lambda cfg, b: True))

        got = _cycle(ev["pct"])
        if event == "overlap":
            # **THE SECOND EVENT, SAME SESSION -- AND THE ROW MEASURES ONLY THAT CYCLE.** This
            # is the blocker-B route when the first event's orders are still resting. My first
            # cut measured both cycles against a declaration describing the second, so cycle
            # one's legitimate buy-in read as "transmitted when nothing may be sent".
            before = _digest(root)
            del live.placed[:]
            got = _cycle(ev["then_pct"])
        after = _digest(root)
        slot = next((x for x in (got.get("slots") or [])
                     if str(x.get("slot")) == "1"), {}) or {}
        final = LC.read_state("1", root)
        # **"CLOSED" IS READ FROM THE RECORD, NOT FROM THE CYCLE'S SELF-REPORT.** `processed`
        # carrying the key is what makes an event un-repeatable, so it is the property that
        # matters -- and it is the only one measurable on a tree that predates
        # `event_closed`, which is what made the first control run blind to this whole column.
        key = _key_for(state, event)
        # **"FINISHED" NEEDS BOTH HALVES, and my first cut used only the first.** The SEND path
        # also appends to `processed` -- that is what stops a restart re-firing the event from
        # scratch -- and it sets `open_event` to the same key to mark the remainder. So
        # `processed` alone says "acted on", not "complete"; the record says COMPLETE when the
        # key is processed AND no remainder for it is outstanding. Found by the self-report
        # disagreeing with the record on nine rows, which is that cross-check working.
        closed_in_record = (key in (final.get("processed") or [])
                            and final.get("open_event") != key)
        return {
            "closed_in_record": closed_in_record,
            "key": key,
            "placed": [(o["symbol"], o["side"]) for o in live.placed],
            "wrote": (before != after),
            "event_closed": bool(slot.get("event_closed")),
            "open_event": final.get("open_event"),
            "processed": list(final.get("processed") or []),
            "alerts": [a["kind"] for a in (slot.get("alerts") or [])],
            "armed": bool(slot.get("armed")),
            "sell_only": bool(slot.get("sell_only")),
            "writes_allowed": slot.get("writes_allowed"),
            "reason": slot.get("reason") or "",
            "withheld_buys": [o.get("ticker") for o in (slot.get("withheld_buys") or [])],
        }
    finally:
        if own:
            shutil.rmtree(root, True)


def all_rows():
    """Every row in the table, as (state, event, read, mode, pilot)."""
    return list(itertools.product(sorted(STATES), sorted(EVENTS), range(len(READS)),
                                  MODES, PILOTS))


def check_row(row):
    """`None` if the code agrees with the declaration, else a string saying how it differs."""
    state, event, ri, mode, pilot = row
    read = READS[ri]
    want = expected(state, event, read, mode, pilot)
    got = run_row(state, event, read, mode, pilot)
    bad = []
    # ---- the SAFETY direction: what must never happen -------------------------------
    if want["sent"] == "none" and got["placed"]:
        bad.append("TRANSMITTED %r when nothing may be sent" % (got["placed"],))
    if want["sent"] == "sells_only":
        buys = [t for t, side in got["placed"] if side != "sell"]
        if buys:
            bad.append("a WIND-DOWN transmitted buys: %r" % (buys,))
    if not want["may_write"] and got["wrote"]:
        bad.append("WROTE the record when no write is permitted")
    if want["may_close"] is False and got["closed_in_record"]:
        bad.append("CLOSED the event with no evidence that nothing is working")
    if got["event_closed"] != got["closed_in_record"]:
        # THE SELF-REPORT MUST AGREE WITH THE RECORD. A cycle saying it closed an event whose
        # key is not in `processed` -- or the reverse -- is two accounts of one fact, which is
        # the shape every blocker on this path has had.
        bad.append("event_closed=%r but the record says %r"
                   % (got["event_closed"], got["closed_in_record"]))
    if bool(got["armed"]) != bool(want["armed"]):
        bad.append("armed=%r, declared %r" % (got["armed"], want["armed"]))
    if bool(got["sell_only"]) != bool(want["wind_down"]):
        bad.append("sell_only=%r, declared %r" % (got["sell_only"], want["wind_down"]))
    if want["alerted"] is True and not got["alerts"]:
        bad.append("no alert, and one is required")
    # ---- the POSITIVE control: a clean cycle must act -------------------------------
    if want["clean"] and want["may_close"] is True and not got["closed_in_record"]:
        bad.append("a CLEAN cycle whose targets are met did NOT close the event")
    if (want["clean"] and want["sent"] == "any" and not want["targets_met"]
            and not want["resting_this_event"] and want["open_is_mine"]
            and not got["placed"]):
        # **EXCLUDING ROWS WHOSE OWN ORDERS ARE RESTING**, because transmitting there
        # would stack the remainder -- item 70's `PLAN_RESTING`, and the one place this
        # control must not fire.
        # EXCLUDED: rows whose own orders are resting (transmitting would stack the
        # remainder -- item 70's `PLAN_RESTING`), and rows where ANOTHER event is open with
        # this slot's orders working (item 71's fifth fix -- that event resolves first).
        bad.append("a CLEAN cycle with work to do transmitted NOTHING")
    if not bad:
        return None
    return "%s | %s | orders=%s positions=%s quotes=%s | %s | pilot=%s :: %s" % (
        state, event, read["orders"], read["positions"], read["quotes"], mode, pilot,
        "; ".join(bad))


# --------------------------------------------------------------------------------------- #
# THE TABLE
# --------------------------------------------------------------------------------------- #
class TheWholeTable(unittest.TestCase):
    """**EVERY ROW, AND THE COUNT IS REPORTED RATHER THAN ASSERTED.**"""

    def test_every_row_matches_the_declaration(self):
        rows = all_rows()
        wrong = [w for w in (check_row(r) for r in rows) if w]
        if wrong:
            self.fail("%d of %d rows disagree with the declaration:\n  %s"
                      % (len(wrong), len(rows), "\n  ".join(wrong[:40])))
        print("\n    TABLE: %d rows, all matching the declaration" % len(rows))

    def test_the_MET_table_covers_every_state_and_event(self):
        """A missing entry would raise; a SPURIOUS one would silently describe a row that does
        not exist. Both directions, because only one of them fails loudly on its own."""
        want = {(a, b) for a in STATES for b in EVENTS}
        self.assertEqual(set(MET), want,
                         "missing %r / spurious %r" % (sorted(want - set(MET)),
                                                       sorted(set(MET) - want)))

    def test_the_table_is_the_declared_size(self):
        """`MA13`'s committed-literal idiom on the row count: an axis quietly losing a value
        would shrink the table and nothing else would notice."""
        self.assertEqual(len(STATES), 7)
        self.assertEqual(len(EVENTS), 5)
        self.assertEqual(len(READS), 8)
        self.assertEqual(len(MODES), 4)
        self.assertEqual(len(PILOTS), 2)
        self.assertEqual(len(all_rows()), 7 * 5 * 8 * 4 * 2)
        self.assertEqual(len(all_rows()), 2240)


class TheDeclarationIsNotAMirrorOfTheCode(unittest.TestCase):
    """**THE CONTROL.** A declaration read off the implementation would agree with it
    everywhere, including on the bugs -- so the table proves nothing until it is shown to
    DISAGREE with a tree that has them. `scripts/i71_table_before.py` runs this same
    declaration against the pre-item-71 sources restored from git: **1,641 of 2,240 rows.**

    It is a script rather than a test because it rewrites tracked source files to run, and a
    suite that does that during a gate is a suite that can leave the tree altered -- which is
    a cost item `W-1` already paid once."""

    #: MEASURED, and a committed literal so a silent change shows in a diff (`MA13`).
    WRONG_BEFORE_ITEM_71 = 1641
    ROWS = 2240

    def test_the_control_script_exists_and_says_what_it_measured(self):
        p = os.path.join(REPO, "scripts", "i71_table_before.py")
        self.assertTrue(os.path.exists(p), "the control is not reproducible")
        txt = io.open(p, encoding="utf-8").read()
        self.assertIn(str(self.WRONG_BEFORE_ITEM_71), txt)
        self.assertIn(str(self.ROWS), txt)
        # And it must restore what it rewrites.
        self.assertIn("restored byte-for-byte", txt)
        self.assertIn("RESTORE FAILED", txt)

    def test_the_before_count_is_most_of_the_table(self):
        """Stated as a property rather than left to a reader: if the declaration had been read
        off the implementation this number would be near zero."""
        self.assertGreater(self.WRONG_BEFORE_ITEM_71, self.ROWS // 2)

    def test_each_rule_has_a_source_in_the_declaration(self):
        import inspect
        src = inspect.getsource(expected)
        for needle in ("blocker A", "blocker C", "DECISIONS 2026-10-14", "item 69",
                       "items 69, 70, 71", "MA21"):
            self.assertIn(needle, src, "a rule with no source: %r" % needle)

    def test_the_declaration_does_not_import_the_implementation_s_decisions(self):
        """It may use `client_order_id` (the writer's own id format, which is a fact about the
        data) and must not call the close logic, the planner or `armed`."""
        import inspect
        src = inspect.getsource(expected) + inspect.getsource(_key_for)
        for banned in ("plan_outcome", "writes_allowed", "LS.armed", "order_plan",
                       "resting_for_event"):
            self.assertNotIn(banned, src, "the declaration consults %r" % banned)


class TheThreeReadsAreCrossedFullyOnOneCell(unittest.TestCase):
    """**THE MARGINAL CROSS CARRIES AN ASSUMPTION, SO IT IS MEASURED.** The table varies one
    read at a time; this runs all 4 x 3 x 3 = 36 on a representative cell, so "the three reads
    do not interact" is a measurement on at least one point rather than a hope."""

    def test_all_36_read_combinations_on_a_representative_cell(self):
        combos = list(itertools.product(("ok", "truncated", "failed", "not_attempted"),
                                        ("ok", "unreadable", "empty"),
                                        ("ok", "one_missing", "none")))
        self.assertEqual(len(combos), 36)
        wrong = []
        for o, p, q in combos:
            read = dict(orders=o, positions=p, quotes=q)
            w = expected("off_target", "rebalance", read, "live", "1")
            g = run_row("off_target", "rebalance", read, "live", "1")
            if w["sent"] == "none" and g["placed"]:
                wrong.append("%s/%s/%s sent %r" % (o, p, q, g["placed"]))
            if not w["may_write"] and g["wrote"]:
                wrong.append("%s/%s/%s WROTE with no write permitted" % (o, p, q))
            if w["may_close"] is False and g["closed_in_record"]:
                wrong.append("%s/%s/%s CLOSED with no evidence" % (o, p, q))
        self.assertEqual(wrong, [], "\n  ".join(wrong))


if __name__ == "__main__":
    unittest.main(verbosity=2)
