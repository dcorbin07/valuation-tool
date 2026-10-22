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

**5,632 rows** since item 72 added the four states and three events the auditor's seventh
review found unreachable. **1,641 of the original 2,240 were wrong before item 71** -- measured
by running this same
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

import ast
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
#: ITS formation date. A record whose `last_event_date` does not match the book it is handed
#: produces a REBALANCE, which preempts every percentage event -- so an item-77 case that wants
#: a pure percentage event must pair `BOOK_OLD` with this. (Caught by the second round trip
#: recording `rebalance:2026-08-01` instead of the percentage key it was asserting.)
OLD_FORMED = BOOK_OLD["formed_on"]

ACCOUNT = {"id": "acct-live-1", "account_number": "L1", "equity": "10000", "cash": "10000",
           "buying_power": "10000", "non_marginable_buying_power": "10000",
           "status": "ACTIVE", "multiplier": "1"}
PAPER_ACCOUNT = dict(ACCOUNT, id="acct-paper-1", account_number="PA1")

#: **THE TWO CASH ACCOUNTS ITEM 73 NEEDED, and their absence is why this table could not reach
#: a cash shortfall at all.** `non_marginable_buying_power` is the field the budget reads
#: (item 67), so it is the one that has to be short -- setting `cash` alone would leave the
#: budget full and the row inert, which is the shape of an axis that varies nothing.
BROKE_ACCOUNT = dict(ACCOUNT, cash="0", buying_power="0",
                     non_marginable_buying_power="0")
#: Forty dollars, against item 73's $250 default threshold.
TRICKLE_ACCOUNT = dict(ACCOUNT, cash="40", buying_power="40",
                       non_marginable_buying_power="40")

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
                 orders_read="ok", positions_read="ok", quotes_read="ok",
                 broker_extra=None, mark=100.0):
        self.holdings, self.resting = dict(holdings), list(resting)
        # **A POSITION IN THE ACCOUNT THAT THIS SLOT'S RECORD DOES NOT KNOW ABOUT [item 72].**
        # The auditor's own noted gap: this fixture otherwise DERIVES the broker's positions
        # from the record, so no foreign position appears in any row and `positions="empty"`
        # only ever tests the broker holding LESS. The dangerous direction -- the broker
        # holding MORE -- is item 63's blocker, and it is also what makes item 67's
        # fresh-record check fire.
        self.broker_extra = dict(broker_extra or {})
        self.acct = dict(account or ACCOUNT)
        self.slot = slot
        self.orders_read = orders_read
        self.positions_read = positions_read
        self.quotes_read = quotes_read
        # **THE PRICE, AS AN AXIS [item 77, blocker C].** Every quote in this fixture was
        # bid 99 / ask 101, so no row could vary the MARK -- and the auditor's blocker C is
        # entirely about what a price move does inside an open event. Defaulted to the old
        # pair so every existing row is byte-for-byte unchanged.
        self.mark = float(mark)
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
            for t, q in self.broker_extra.items():
                eff[t] = eff.get(t, 0.0) + float(q)
            return T63.Reply([{"symbol": t, "qty": str(q), "avg_entry_price": "100",
                               "side": "long"} for t, q in sorted(eff.items())
                              if float(q) > 0])
        if "quotes/latest" in url:
            if self.quotes_read == "none":
                return T63.Reply({"quotes": {}})
            q = {s: {"bp": self.mark - 1.0, "ap": self.mark + 1.0, "t": "x"}
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
    # ---- ADDED BY ITEM 72, the three slot states the auditor found missing -------------
    #
    # **BRAND NEW: no record at all.** Not the same as an empty one -- item 67's fresh-record
    # check refuses ONE cycle when the record is new and the account is not empty, and that
    # refusal was reachable in no row of the table.
    "brand_new":        dict(record={}, resting=(), open_ev=None, holds=False, fresh=True),
    # **AND THE SAME AGAINST AN ACCOUNT THAT IS NOT EMPTY [item 72].** Item 67's fresh-record
    # check refuses ONE cycle in exactly this state, and it was reachable in no row -- because
    # the fixture derives the broker's positions from the record, so a brand-new record always
    # had an empty account. `broker_extra` is a position the record does not know about, which
    # is also the direction the auditor could only check by hand.
    "brand_new_dirty":  dict(record={}, resting=(), open_ev=None, holds=False, fresh=True,
                             broker_extra={"AAPL": 2.5}),
    # **EXHAUSTED: the no-progress ceiling has already been spent.** Six trading days recorded
    # against this event with the holdings unchanged, which is the state the ceiling exists to
    # produce -- and the table crossed it with nothing.
    "exhausted":        dict(record={"AAPL": 1.0}, resting=(),
                             open_ev="rebalance:" + FORMED, holds=True,
                             attempt_days=("2026-10-26", "2026-10-27", "2026-10-28",
                                           "2026-10-29", "2026-10-30", "2026-11-02")),
    # **A STALE `open_event`: named, with NOTHING resting for it.** Item 72's own subject, and
    # the state every real event is in the morning after its `day` orders expired. Every other
    # `open_ev` state in this table pairs it with live resting orders.
    "stale_open":       dict(record={"AAPL": ON_TARGET, "BBB": ON_TARGET}, resting=(),
                             open_ev="rebalance:2026-08-01", holds=True),
    # ---- ADDED BY ITEM 73: the two CASH states, which this table could not reach ---------
    #
    # Every account in this fixture had ten thousand dollars of no-borrow buying power, so no
    # row could ever reach a cash shortfall -- and Don's rulings of 2026-10-18 are entirely
    # about what happens when it does.
    #
    # **BOTH SHARE `off_target`'s RECORD, DELIBERATELY.** `MET` is a statement about the record
    # against the book and has nothing to do with cash, so sharing the record means their
    # `MET` entries are derived from `off_target`'s rather than guessed afresh -- and a
    # declaration guessed afresh is the one way this table can start agreeing with the
    # implementation about a bug.
    #
    # `cash_short`: a real gap and NO money. Don: *"Waiting for cash is a normal state, not a
    # failure ... it alerts Don once. It does not re-alert every cycle and does not burn the
    # ceiling."* The sells still go -- a sell RAISES cash -- so the constraint is no BUY.
    "cash_short":       dict(record={"AAPL": 1.0}, resting=(), open_ev=None, holds=True,
                             account=BROKE_ACCOUNT, cash_short=True),
    # `cash_trickle`: a gap, and forty dollars against the $250 threshold. The event is already
    # in `processed`, so this is NOT the first fill -- which is the only state in which the
    # threshold may hold anything back.
    "cash_trickle":     dict(record={"AAPL": 1.0}, resting=(),
                             open_ev="rebalance:" + FORMED, holds=True,
                             processed_extra=("rebalance:" + FORMED,),
                             account=TRICKLE_ACCOUNT, cash_short=True),
}

def _derive_cash_met():
    """`MET` for item 73's cash states, from `off_target`'s — identical records, same answer.

    Asserted rather than assumed: both must actually carry `off_target`'s record, or the
    derivation is a guess wearing a derivation's clothes.
    """
    for name in ("cash_short", "cash_trickle"):
        assert STATES[name]["record"] == STATES["off_target"]["record"], \
            "%s no longer shares off_target's record, so its MET cannot be derived" % name
    for (st, ev), v in list(MET.items()):
        if st == "off_target":
            MET[("cash_short", ev)] = v
            MET[("cash_trickle", ev)] = v


#: EVENT. `last_*` is what the record says it last acted on; `pct` is the environment now.
EVENTS = {
    "rebalance": dict(last_pct=5.0, last_event="2026-08-01", pct=5.0, book=BOOK),
    "buy_in":    dict(last_pct=0.0, last_event=FORMED, pct=5.0, book=BOOK),
    "resize":    dict(last_pct=5.0, last_event=FORMED, pct=2.0, book=BOOK),
    "sell_out":  dict(last_pct=5.0, last_event=FORMED, pct=0.0, book=BOOK),
    #: TWO EVENTS IN ONE SESSION: a rebalance cycle, then a percentage change, same session.
    "overlap":   dict(last_pct=5.0, last_event="2026-08-01", pct=5.0, book=BOOK,
                      then_pct=0.0),
    # ---- ADDED BY ITEM 72 --------------------------------------------------------------
    #: **A QUIET CYCLE: no event at all.** The book has not moved and the percentage has not
    #: moved, which is the ordinary case and -- in `event_for`'s own words -- *"the whole
    #: point"*. The table had no row in which the slot was supposed to do NOTHING.
    "quiet":     dict(last_pct=5.0, last_event=FORMED, pct=5.0, book=BOOK),
    #: **AN UPWARD RESIZE.** Every resize in the table went DOWN (5% -> 2%), so every one
    #: planned sells; an upward move plans BUYS, which is the side that spends money and the
    #: side the budget bounds.
    "resize_up": dict(last_pct=2.0, last_event=FORMED, pct=5.0, book=BOOK),
    #: **A NEW BOOK SUPERSEDING AN OPEN PERCENTAGE EVENT.** `event_for` prefers the rebalance,
    #: so a pct event left open is overtaken -- and whether its remainder survives that is the
    #: blocker-B question from the other direction.
    "book_over_pct": dict(last_pct=2.0, last_event="2026-08-01", pct=5.0, book=BOOK,
                          open_pct_event="pct:2.0->5.0"),
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
#: **DOES THIS SLOT'S RECORD ALREADY MEET THIS EVENT'S TARGETS?** Declared per (state, event)
#: because it is NOT a property of the state: the targets move with the percentage. `on_target`
#: holds 2.5 shares of each name, which IS the 5% target ($250 at a $100 mid) and is NOT the 2%
#: one ($100).
#:
#: **THE RULE IS SECTION 8a's, NOT THE IMPLEMENTATION'S**: `target_i = pct/100 x equity x w_i`,
#: so at $10,000 equity with two names at weight 0.5 and a $100 mid the per-name target is 2.5
#: shares at 5%, 1.0 at 2% and nothing at 0%; "met" is the record EQUALLING that. The entries
#: are written out so a reader can check any one of them against the record in `STATES` without
#: running anything -- the generator exists only to keep 80 of them free of typos.
#:
#: The deciding percentage for `overlap` is its SECOND cycle's, which is 0%.
MET = {
    # brand_new         record {}
    ("brand_new", "book_over_pct"): False,
    ("brand_new", "buy_in"): False,
    ("brand_new", "overlap"): True,
    ("brand_new", "quiet"): False,
    ("brand_new", "rebalance"): False,
    ("brand_new", "resize"): False,
    ("brand_new", "resize_up"): False,
    ("brand_new", "sell_out"): True,
    # brand_new_dirty   record {} -- and a FOREIGN position in the account
    ("brand_new_dirty", "book_over_pct"): False,
    ("brand_new_dirty", "buy_in"): False,
    ("brand_new_dirty", "overlap"): True,
    ("brand_new_dirty", "quiet"): False,
    ("brand_new_dirty", "rebalance"): False,
    ("brand_new_dirty", "resize"): False,
    ("brand_new_dirty", "resize_up"): False,
    ("brand_new_dirty", "sell_out"): True,
    # exhausted         record {'AAPL': 1.0}
    ("exhausted", "book_over_pct"): False,
    ("exhausted", "buy_in"): False,
    ("exhausted", "overlap"): False,
    ("exhausted", "quiet"): False,
    ("exhausted", "rebalance"): False,
    ("exhausted", "resize"): False,
    ("exhausted", "resize_up"): False,
    ("exhausted", "sell_out"): False,
    # fresh             record {}
    ("fresh", "book_over_pct"): False,
    ("fresh", "buy_in"): False,
    ("fresh", "overlap"): True,
    ("fresh", "quiet"): False,
    ("fresh", "rebalance"): False,
    ("fresh", "resize"): False,
    ("fresh", "resize_up"): False,
    ("fresh", "sell_out"): True,
    # mid_event         record {}
    ("mid_event", "book_over_pct"): False,
    ("mid_event", "buy_in"): False,
    ("mid_event", "overlap"): True,
    ("mid_event", "quiet"): False,
    ("mid_event", "rebalance"): False,
    ("mid_event", "resize"): False,
    ("mid_event", "resize_up"): False,
    ("mid_event", "sell_out"): True,
    # off_target        record {'AAPL': 1.0}
    ("off_target", "book_over_pct"): False,
    ("off_target", "buy_in"): False,
    ("off_target", "overlap"): False,
    ("off_target", "quiet"): False,
    ("off_target", "rebalance"): False,
    ("off_target", "resize"): False,
    ("off_target", "resize_up"): False,
    ("off_target", "sell_out"): False,
    # ---- ITEM 73's TWO CASH STATES are DERIVED from `off_target` below the literal ---------
    #
    # `MET` is a statement about the RECORD against the book and has nothing to do with how much
    # cash the account holds, and both new states share `off_target`'s record exactly. Deriving
    # them means a change to that record's declaration moves all three together; retyping eight
    # booleans twice is how a table comes to disagree with itself. See `_derive_cash_met`.
    # on_target         record {'AAPL': 2.5, 'BBB': 2.5}
    ("on_target", "book_over_pct"): True,
    ("on_target", "buy_in"): True,
    ("on_target", "overlap"): False,
    ("on_target", "quiet"): True,
    ("on_target", "rebalance"): True,
    ("on_target", "resize"): False,
    ("on_target", "resize_up"): True,
    ("on_target", "sell_out"): False,
    # resting_opposite  record {'AAPL': 2.5, 'BBB': 2.5}
    ("resting_opposite", "book_over_pct"): True,
    ("resting_opposite", "buy_in"): True,
    ("resting_opposite", "overlap"): False,
    ("resting_opposite", "quiet"): True,
    ("resting_opposite", "rebalance"): True,
    ("resting_opposite", "resize"): False,
    ("resting_opposite", "resize_up"): True,
    ("resting_opposite", "sell_out"): False,
    # resting_partial   record {'AAPL': 2.5, 'BBB': 1.0}
    ("resting_partial", "book_over_pct"): False,
    ("resting_partial", "buy_in"): False,
    ("resting_partial", "overlap"): False,
    ("resting_partial", "quiet"): False,
    ("resting_partial", "rebalance"): False,
    ("resting_partial", "resize"): False,
    ("resting_partial", "resize_up"): False,
    ("resting_partial", "sell_out"): False,
    # resting_same      record {'AAPL': 2.5}
    ("resting_same", "book_over_pct"): False,
    ("resting_same", "buy_in"): False,
    ("resting_same", "overlap"): False,
    ("resting_same", "quiet"): False,
    ("resting_same", "rebalance"): False,
    ("resting_same", "resize"): False,
    ("resting_same", "resize_up"): False,
    ("resting_same", "sell_out"): False,
    # stale_open        record {'AAPL': 2.5, 'BBB': 2.5}
    ("stale_open", "book_over_pct"): True,
    ("stale_open", "buy_in"): True,
    ("stale_open", "overlap"): False,
    ("stale_open", "quiet"): True,
    ("stale_open", "rebalance"): True,
    ("stale_open", "resize"): False,
    ("stale_open", "resize_up"): True,
    ("stale_open", "sell_out"): False,
}

#: Item 73's two cash states, filled in from `off_target`'s — see `_derive_cash_met` above for
#: why by reference rather than by retyping. Called HERE because `MET` is the thing it reads.
_derive_cash_met()



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
    #     **AND ITEM 78 §3 NARROWED WHAT A 0% SLOT NEEDS, so this rule changed rather than its
    #     wording.** `one_missing` is a one-sided quote for **BBB**. A slot that may not buy
    #     needs prices only for what it HOLDS -- so a wind-down of a slot whose record is
    #     `{"AAPL": ...}` is no longer blocked by a book name it does not own, and it sells
    #     AAPL. Eight rows moved from `none` to `sells_only` on that reading and every one is
    #     a 0% slot holding AAPL alone.
    #
    #     **THE TABLE CARRIES ITS OWN CONTROL and that is what licenses the change**:
    #     `resting_opposite` holds BOTH names, so BBB is in its population, so it still
    #     refuses -- and `quotes=none` refuses everywhere, because then AAPL has no mid either
    #     and a limit order cannot be priced. The direction matters: blocking the exit would
    #     have stranded a position indefinitely over an unrelated name's one-sided quote, with
    #     a daily alert about it, which is the noise item 78 was written to stop.
    # S7. An unreadable position list refuses the cycle. [item 63]
    sent = "none"
    #: Is the missing name one THIS slot needs? Derived from the record rather than listed, so
    #: a new state's record cannot silently inherit the wrong answer.
    needs_the_unpriced_name = (not wind_down) or ("BBB" in st["record"])
    if read_ok:
        if (read["positions"] == "unreadable" or read["quotes"] == "none"
                or (read["quotes"] == "one_missing" and needs_the_unpriced_name)):
            sent = "none"                      # preflight refuses
        elif read["positions"] == "empty" and st["holds"]:
            sent = "none"                      # record-versus-broker disagreement refuses
        elif wind_down:
            sent = "sells_only"
        elif st.get("cash_short") and not _buys_possible(state, event):
            # S8. **NO MONEY MEANS NO BUY, AND THE SELLS STILL GO [item 73].** Don, 2026-10-18:
            #     the buys are scaled by `min(1, spendable / total buy cost)`, which is ZERO
            #     when the no-borrow figure is zero. A SELL is never bounded by cash, because a
            #     sell RAISES it, so the constraint on these rows is "no buy" -- the same
            #     constraint as a wind-down's, for a different reason.
            # S9. **AND THE TOP-UP THRESHOLD ONLY BINDS A LATER CYCLE.** Don: *"The first fill
            #     of a new event is not held back by the threshold."* So `cash_trickle`'s $40
            #     waits when the event is already open (a top-up under $250) and goes out
            #     scaled when the event is arriving now (a first fill). `_buys_possible` is
            #     that distinction, derived from the rule rather than from the code.
            sent = "sells_only"
        else:
            sent = "any"

    # ---- OPEN OR CLOSED --------------------------------------------------------------
    # C1. An event closes only on POSITIVE evidence that nothing is working: the orders read
    #     succeeded, the plan is empty with nothing skipped, no order of this slot's is resting
    #     FOR THIS EVENT, and the open remainder belongs to THIS event. [items 69, 70, 71]
    this_key = _key_for(state, event)
    resting_this_event = any(r[4] == this_key for r in st["resting"])
    # **A STALE `open_event` DOES NOT BLOCK [item 72].** The auditor: *"a stale `open_event`
    # with nothing resting is also a condition worth clearing rather than refusing on for
    # ever."* So a foreign open event blocks the close only while something of this slot's is
    # actually working for it -- which is the requirement, not a detail read off the code.
    _open_ev = st["open_ev"]
    _open_has_resting = any(r[4] == _open_ev for r in st["resting"]) if _open_ev else False
    open_is_mine = (_open_ev in (None, this_key)) or not _open_has_resting
    met = MET[(state, event)]
    if (event in ("overlap", "book_over_pct", "quiet")
            or state in ("brand_new", "brand_new_dirty", "exhausted")):
        # **NOT ASSERTED ON THESE [item 72], and each for its own reason.** `overlap` and
        # `book_over_pct` depend on what an earlier cycle or an overtaken event did;
        # `brand_new` may spend its one cycle on item 67's fresh-record refusal; and an
        # `exhausted` event's close depends on whether the ceiling fires first, which is the
        # thing under test rather than something to declare. The SAFETY direction is still
        # asserted on every one of these rows.
        # **NOT ASSERTED, DELIBERATELY.** Whether the first cycle left a remainder open depends
        # on what the first cycle did, and declaring that would mean modelling the
        # implementation here -- which is the one thing this declaration must not do. The
        # safety direction is still asserted on every overlap row, and blocker B's own property
        # has a dedicated test where the sequence is explicit.
        may_close = None
    elif st.get("cash_short") and not met:
        # C2. **A CASH GAP KEEPS ITS EVENT OPEN [item 73].** Don, 2026-10-18: *"The shortfall
        #     stays OPEN until it is filled or the next event replaces it."* So a row with a
        #     real gap and no money to close it may NOT close -- and that is the whole point of
        #     the ruling, because an event closed over an unfilled gap is a gap nothing will
        #     ever come back for. Where the targets ARE met there is no gap and cash is
        #     irrelevant, which the `not met` guard leaves to the ordinary rule below.
        may_close = False
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
    # **EXCLUDED FROM THE POSITIVE CONTROL [item 72]:** `overlap` and `book_over_pct` depend
    # on an earlier or overtaken event; a `quiet` cycle's correct behaviour is to do NOTHING,
    # which is `event_for`'s own "the whole point"; an `exhausted` event is stopped by the
    # ceiling, which is the machinery working; and a `brand_new` record may spend its one cycle
    # on item 67's fresh-record refusal.
    clean = bool(read_ok and read["positions"] == "ok" and read["quotes"] == "ok"
                 and not (read["positions"] == "empty" and st["holds"])
                 and event not in ("overlap", "book_over_pct", "quiet")
                 and state not in ("exhausted", "brand_new", "brand_new_dirty"))
    return {"sent": sent, "may_write": may_write, "may_close": may_close,
            "alerted": alerted, "wind_down": wind_down, "armed": armed, "clean": clean,
            "targets_met": met, "resting_this_event": resting_this_event,
            "open_is_mine": open_is_mine}


def _buys_possible(state, event) -> bool:
    """Can a CASH-SHORT row buy anything at all? [item 73]

    Two of Don's rules decide it, and neither is read off the implementation:

      * with ZERO no-borrow buying power the scaling fraction is zero, so nothing can be
        bought whatever else is true;
      * with SOME money, the $250 top-up threshold holds it back **only on a later cycle of an
        already-open event** -- *"the first fill of a new event is not held back by the
        threshold"*. A first fill goes out scaled.

    So a trickle buys when this row is the event's FIRST fill and waits when it is a top-up,
    and the record's own open event is what distinguishes them.
    """
    st = STATES[state]
    if not st.get("cash_short"):
        return True
    acct = st.get("account") or {}
    if float(acct.get("non_marginable_buying_power") or 0) <= 0:
        return False
    # Some money: a top-up waits, a first fill goes. A top-up is a later cycle of an event the
    # record still has open, which is exactly when `processed_extra` is seeded.
    ev = EVENTS[event]
    open_now = ev.get("open_pct_event") or st["open_ev"]
    is_top_up = bool(st.get("processed_extra") and open_now == _key_for(state, event))
    return not is_top_up


def _key_for(state, event):
    """The event key this cycle will act on, from the writer's own generator."""
    ev = EVENTS[event]
    if event == "quiet":
        # **NO EVENT OF ITS OWN [item 72].** `event_for` returns nothing, so the cycle acts on
        # whatever `open_event` holds -- the remainder path -- and with none there is no key.
        return STATES[state]["open_ev"] or "none"
    if event == "book_over_pct":
        # **IT IS A REBALANCE.** The book moved, and `event_for` prefers the rebalance over the
        # open percentage event, so the key is the rebalance's. Mine returned a `pct:` key.
        return "rebalance:%s" % ev["book"]["formed_on"]
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
        # **AN OPEN *PERCENTAGE* EVENT, for `book_over_pct` [item 72].** A rebalance arriving
        # while a pct event is open: `event_for` prefers the rebalance, so the pct event is
        # overtaken, and whether its remainder survives is blocker B from the other direction.
        if ev.get("open_pct_event"):
            rec["open_event"] = ev["open_pct_event"]
        # **AN EXHAUSTED EVENT, seeded with the days and the fingerprint the ceiling reads
        # [item 72].** Both are needed: the day list alone resets on the first cycle, because
        # `note_no_progress` treats an absent fingerprint as "a changed definition does not
        # inherit its old values" and starts the count again (item 64's rule).
        # **ITEM 73: AN EVENT ALREADY IN `processed` is what makes a cycle NOT the first
        # fill**, and the threshold may hold nothing back on a first fill. Only the SEND path
        # appends the key, so seeding it is how this fixture reaches a later top-up at all.
        #
        # **SEEDED ONLY WHERE THE RECORD'S OPEN EVENT IS THE ARRIVING ONE**, and that took two
        # goes. A hard-coded rebalance key left `processed` carrying the arriving key while
        # `book_over_pct` replaced `open_event` with its pct event, so 66 rows read as ALREADY
        # CLOSED before the cycle ran (`closed_in_record` is `key in processed and
        # open_event != key`). Using the arriving key unconditionally has the same effect for
        # the same reason. A top-up is by definition a later cycle of an event the record still
        # has OPEN, so that is the condition -- and where it does not hold the row is a FIRST
        # FILL, which `is_first_fill` in the declaration accounts for.
        if st.get("processed_extra") and rec.get("open_event") == _key_for(state, event):
            rec["processed"] = [_key_for(state, event)]
        if st.get("attempt_days"):
            fp = "|".join("%s:%.6f" % (t, float(st["record"].get(t) or 0))
                          for t in sorted(st["record"]))
            rec["event_attempt_days"] = {st["open_ev"]: list(st["attempt_days"])}
            rec["event_fingerprint"] = {st["open_ev"]: fp}
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        # **A BRAND-NEW RECORD IS NO FILE AT ALL [item 72], which is not the same as an empty
        # one.** Item 67's fresh-record check refuses ONE cycle when the record is new and the
        # account is not empty, and that refusal was reachable in no row of the table.
        if not st.get("fresh"):
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, sort_keys=True)

        live = Rec(holdings=st["record"], resting=st["resting"],
                   orders_read=read["orders"], positions_read=read["positions"],
                   broker_extra=st.get("broker_extra"),
                   # **ITEM 73: THE STATE CARRIES ITS OWN ACCOUNT.** Every account here had ten
                   # thousand dollars of no-borrow buying power, so no row could reach a cash
                   # shortfall -- and Don's rulings of 2026-10-18 are entirely about that case.
                   account=st.get("account"))
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
                notify_send=(lambda cfg, b, ch=None: True))

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
            # TWO REASONS REACH THIS, so the message names which. A wind-down may not buy at
            # all (item 71 blocker A); a cash-short slot has nothing to buy WITH (item 73).
            why = "a WIND-DOWN" if want["wind_down"] else "a CASH-SHORT slot"
            bad.append("%s transmitted buys: %r" % (why, buys))
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
        # **ITEM 72 ADDED FOUR STATES AND THREE EVENTS**, the shapes the auditor's seventh
        # review found the table could not reach: a brand-new record, a brand-new record
        # against a non-empty account, an exhausted event, a STALE `open_event`, a quiet cycle,
        # an UPWARD resize, and a new book superseding an open percentage event.
        # 7 x 5 -> 11 x 8, so 2,240 rows -> 5,632.
        #
        # **ITEM 73 ADDED THE TWO CASH STATES.** Every account in this fixture had ten thousand
        # dollars of no-borrow buying power, so no row could reach a cash shortfall at all --
        # and Don's rulings of 2026-10-18 are entirely about that case. 11 -> 13 states, so
        # 5,632 rows -> 6,656.
        self.assertEqual(len(STATES), 13)
        self.assertEqual(len(EVENTS), 8)
        self.assertEqual(len(READS), 8)
        self.assertEqual(len(MODES), 4)
        self.assertEqual(len(PILOTS), 2)
        self.assertEqual(len(all_rows()), 13 * 8 * 8 * 4 * 2)
        self.assertEqual(len(all_rows()), 6656)
        # AND THE CASH STATES ARE REACHABLE: a budget that was never short would make every one
        # of their 1,024 rows a restatement of `off_target`.
        for name in ("cash_short", "cash_trickle"):
            acct = STATES[name]["account"]
            self.assertLess(float(acct["non_marginable_buying_power"]),
                            float(ACCOUNT["non_marginable_buying_power"]),
                            "%s's account is not actually short, so its rows are inert" % name)


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
        wrong, acted = [], 0
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
            # **THE POSITIVE DIRECTION [item 72, the auditor's third request].** Without it
            # this control asserted only that forbidden things do not happen, so a tree that
            # did nothing at all would have satisfied all 36 rows -- the vacuous pass, in the
            # one test whose job is to measure an interaction.
            if w["clean"] and w["sent"] == "any":
                if not g["placed"]:
                    wrong.append("%s/%s/%s is CLEAN with work to do and sent NOTHING"
                                 % (o, p, q))
                else:
                    acted += 1
        self.assertEqual(wrong, [], "\n  ".join(wrong))
        # AND AT LEAST ONE COMBINATION MUST BE THE CLEAN ONE, or the line above never ran.
        self.assertEqual(acted, 1,
                         "exactly one of the 36 is all-ok and it must have traded: %d" % acted)


# --------------------------------------------------------------------------------------- #
# ITEM 77 — THE AUDITOR'S EIGHTH REVIEW, REPRODUCED
# --------------------------------------------------------------------------------------- #
#
# Every case below is one the auditor drove on the shipped code and watched do the wrong
# thing. They use the same recorded `Rec` session, the same real `_LiveClient` and
# `AlpacaPaperBroker`, and the same `run_cycle` as the table above; nothing touches a network.
#
# **EACH ONE FAILS ON THE PRE-ITEM-77 TREE**, which is measured rather than asserted:
# `scripts/i77_before.py` restores the three sources from git and runs exactly these cases.
def _run77(*, env, record, book, resting=(), account=None, mark=100.0, root=None,
           mode="live", pct=None, broker_extra=None):
    """One cycle, with the environment and the mark under the caller's control.

    `run_row` fixes both -- the percentage is always set and the mark is always 100 -- which
    is why neither of the two axes item 77 is about could be reached from the table.
    """
    own = root is None
    root = root or tempfile.mkdtemp()
    try:
        p = LC.state_path("1", root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with io.open(p, "w", encoding="utf-8") as fh:
            json.dump(record, fh, sort_keys=True)
        live = Rec(holdings=record.get("holdings") or {}, resting=resting,
                   account=account, mark=mark, broker_extra=broker_extra)
        paper = Rec(holdings={}, account=PAPER_ACCOUNT, slot="paper", mark=mark)
        got = LC.run_cycle(
            env=dict(env), mode=mode, may_write=True, now=OPEN_NOW, root=root, book=book,
            paper_client=AB.AlpacaPaperBroker(key_id="PKFIX", secret_key="s" * 24,
                                              session=paper),
            live_client_factory=(lambda n: LS._LiveClient(n, "k", "s" * 24, session=live)),
            notify_send=(lambda cfg, b, ch=None: True))
        slot = next((x for x in (got.get("slots") or [])
                     if str(x.get("slot")) == "1"), {}) or {}
        return {
            "placed": [(o["symbol"], o["side"], float(o.get("qty") or 0))
                       for o in live.placed],
            "sides": sorted({o["side"] for o in live.placed}),
            "alerts": [a["kind"] for a in (got.get("alerts") or [])],
            "slot_alerts": [a["kind"] for a in (slot.get("alerts") or [])],
            # EVERY ALERT'S WORDS, cycle-level and slot-level together: an alert raised by the
            # slot loop lands on the CYCLE's list, and a test reading only the slot's own
            # would pass on silence.
            "alert_text": " ".join((a.get("reason") or "")
                                   for a in list(got.get("alerts") or [])
                                   + list(slot.get("alerts") or [])),
            "armed": bool(slot.get("armed")),
            "sell_only": bool(slot.get("sell_only")),
            "reason": slot.get("reason") or "",
            "state": LC.read_state("1", root),
            "slot": slot,
        }
    finally:
        if own:
            shutil.rmtree(root, True)


#: A slot holding its whole book, at a declared 10%, with nothing outstanding.
def _holding_record(pct_recorded=10.0):
    return {"slot": "1", "account_id": "acct-live-1", "processed": [],
            "holdings": {"AAPL": 5.0, "BBB": 5.0},
            "last_pct": pct_recorded, "last_event_date": OLD_FORMED}


_KEYS = {"LIVE_PILOT_ENABLED": "1", "ALPACA_ACCOUNT_1_KEY_ID": "k",
         "ALPACA_ACCOUNT_1_SECRET_KEY": "s" * 24}


class BlockerAAnAbsentPercentageMustNotLiquidate(unittest.TestCase):
    """**A MISSING OR MISNAMED PERCENTAGE READ AS 0% AND SOLD THE BOOK.** [item 77]

    `slot_pct` returns `0.0, stated=False` for an absent value and `armed` read the 0.0 and
    never the `stated`, so on a slot holding its book each of these gave `armed=True,
    sell_only=True` and TRANSMITTED BOTH SELLS -- reported as *"sent 2 order(s) for
    pct:10.0->0.0"* and indistinguishable from an exit Don asked for.

    The argument against it was already written in the function it was in: *"treating it as 0
    would SELL THE BOOK ON A TYPO"*. That refusal was applied to the typo that fails to PARSE
    and not to the one that leaves the variable ABSENT.
    """

    THREE = (("removed", {}),
             ("empty", {"ALPACA_ACCOUNT_1_LIVE_PCT": ""}),
             ("misspelled", {"ALPACA_ACCOUNT_1_PCT": "0"}))

    def test_none_of_the_three_transmits_anything(self):
        for name, extra in self.THREE:
            got = _run77(env=dict(_KEYS, **extra), record=_holding_record(), book=BOOK_OLD)
            self.assertEqual(got["placed"], [],
                             "%s: TRANSMITTED %r" % (name, got["placed"]))
            self.assertFalse(got["armed"], name)
            self.assertFalse(got["sell_only"], name)

    def test_each_one_alerts_in_plain_words_naming_the_variable(self):
        # A slot that silently stops acting looks exactly like a slot with nothing to do, so
        # refusing is only half the fix.
        for name, extra in self.THREE:
            got = _run77(env=dict(_KEYS, **extra), record=_holding_record(), book=BOOK_OLD)
            self.assertIn("pct_unstated_while_holding", got["alerts"], name)
            self.assertIn("ALPACA_ACCOUNT_1_LIVE_PCT", got["alert_text"], name)

    def test_the_misspelling_is_NAMED_rather_than_silently_ignored(self):
        # The percentage IS set correctly here, so the slot is healthy -- the only finding is
        # the stray variable, which must still be reported by name.
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_PCT="0",
                              ALPACA_ACCOUNT_1_LIVE_PCT="10"),
                     record=_holding_record(), book=BOOK_OLD)
        self.assertIn("unknown_slot_variable", got["alerts"])
        self.assertIn("ALPACA_ACCOUNT_1_PCT", got["alert_text"])
        # AND NO VALUE IS CARRIED: one of these could be a mistyped secret.
        self.assertNotIn("s" * 24, got["alert_text"])

    def test_a_STATED_zero_still_winds_down(self):
        # THE POSITIVE CONTROL, and it is what stops the fix being "refuse everything". Don's
        # documented way out must still work: a typed 0 on a holding slot sells it out.
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="0"),
                     record=_holding_record(), book=BOOK_OLD)
        self.assertTrue(got["armed"])
        self.assertTrue(got["sell_only"])
        self.assertEqual(got["sides"], ["sell"], got["placed"])
        self.assertEqual(len(got["placed"]), 2, got["placed"])

    def test_a_slot_that_holds_NOTHING_stays_quiet_with_no_percentage(self):
        # The ordinary dormant state: a slot with keys and no percentage yet. It must not
        # alert, or every unconfigured slot alerts on every cycle.
        rec = dict(_holding_record(), holdings={})
        got = _run77(env=dict(_KEYS), record=rec, book=BOOK_OLD)
        self.assertEqual(got["placed"], [])
        self.assertNotIn("pct_unstated_while_holding", got["alerts"])


class BlockerBEachPercentageEventWorksMoreThanOnce(unittest.TestCase):
    """**THE ON-SWITCH AND THE OFF-SWITCH EACH WORKED ONCE.** [item 77]

    `event_key` named a percentage event `pct:<from>-><to>` with nothing to tell two
    occurrences apart, while its docstring promised *"a genuinely new event produces a new
    key"*.
    """

    def test_the_second_round_trip_is_not_refused_for_ever(self):
        # THE AUDITOR'S CHAIN: 0 -> 5% buys in, 5 -> 0% sells out, and 5% AGAIN was refused
        # with "this slot has already processed pct:0.0->5.0", for ever, with `last_pct`
        # stuck at 0 so every later cycle refused identically.
        root = tempfile.mkdtemp()
        try:
            rec = {"slot": "1", "account_id": "acct-live-1",
                   "processed": ["pct:0.0->5.0", "pct:5.0->0.0"],
                   "holdings": {}, "last_pct": 0.0, "last_event_date": OLD_FORMED}
            got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="5"),
                         record=rec, book=BOOK_OLD, root=root)
            self.assertNotIn("already processed", got["reason"], got["reason"])
            self.assertEqual(got["sides"], ["buy"], got["placed"])
            self.assertEqual(len(got["placed"]), 2, got["placed"])
            # AND THE NEW OCCURRENCE IS RECORDED UNDER ITS OWN KEY, so the one after it is
            # new too rather than colliding with this one.
            self.assertIn("pct:0.0->5.0#2", got["state"].get("processed") or [])
        finally:
            shutil.rmtree(root, True)

    def test_setting_zero_again_after_a_rebalance_sells_out(self):
        # **THE DANGEROUS HALF.** With `pct:5.0->0.0` already processed and the position
        # re-established by a rebalance, Don setting 0% again gave `armed=True,
        # sell_only=True, key=None, nothing planned, nothing placed, NO ALERT` -- the slot
        # holding the book while the dashboard read 0%.
        rec = {"slot": "1", "account_id": "acct-live-1",
               "processed": ["pct:5.0->0.0"],
               "holdings": {"AAPL": 5.0, "BBB": 5.0},
               "last_pct": 0.0, "last_event_date": OLD_FORMED}
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="0"),
                     record=rec, book=BOOK_OLD)
        self.assertTrue(got["armed"])
        self.assertTrue(got["sell_only"])
        self.assertEqual(got["sides"], ["sell"], got["placed"])
        self.assertEqual(len(got["placed"]), 2, got["placed"])

    def test_or_it_refuses_and_alerts_but_never_silently_nothing(self):
        # THE RULE, as the brief states it: *"Setting 0% while this slot holds its own
        # positions must always sell them out, or refuse and alert. Never silently nothing."*
        # Asserted as the DISJUNCTION, so a future change that makes this state refuse for a
        # good reason still passes -- and silence still fails.
        rec = {"slot": "1", "account_id": "acct-live-1", "processed": ["pct:5.0->0.0"],
               "holdings": {"AAPL": 5.0, "BBB": 5.0},
               "last_pct": 0.0, "last_event_date": OLD_FORMED}
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="0"),
                     record=rec, book=BOOK_OLD)
        # **SCOPED TO THIS SLOT, and the first cut was not.** It read the CYCLE's alert list,
        # which carries the PAPER slot's two routine `live_order_sent` lines -- so on the
        # pre-item-77 tree it passed while slot 1 did nothing and said nothing, which is the
        # exact state it exists to forbid. Caught by running it against that tree.
        sold = bool(got["placed"]) and got["sides"] == ["sell"]
        refused_and_said_so = bool(got["slot_alerts"]) and not got["placed"]
        self.assertTrue(sold or refused_and_said_so,
                        "silently nothing: placed=%r slot_alerts=%r reason=%r"
                        % (got["placed"], got["slot_alerts"], got["reason"]))

    def test_a_restart_still_never_repeats_the_SAME_occurrence(self):
        # The other half of the requirement. An occurrence already recorded and finished --
        # `last_pct` written, nothing open -- must not fire again.
        rec = {"slot": "1", "account_id": "acct-live-1", "processed": ["pct:0.0->5.0"],
               "holdings": {"AAPL": ON_TARGET, "BBB": ON_TARGET},
               "last_pct": 5.0, "last_event_date": OLD_FORMED}
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="5"),
                     record=rec, book=BOOK_OLD)
        self.assertEqual(got["placed"], [], got["placed"])

    def test_the_occurrence_number_is_stable_while_the_event_is_unrecorded(self):
        # **A COUNTER BUMPED PER CYCLE WAS THE FIRST DESIGN AND IT WAS WRONG.** A cycle that
        # refuses BEFORE recording would bump it again next cycle, so the key would change
        # every cycle and `note_no_progress` could never accumulate a ceiling. Derived from
        # `processed`, it is stable for exactly as long as the occurrence is unrecorded.
        st = {"processed": ["pct:0.0->5.0"]}
        ev = {"act": True, "event": "pct_change", "from_pct": 0.0}
        seqs = {LC.next_pct_seq(st, ev, 5.0, remainder=False) for _ in range(5)}
        self.assertEqual(seqs, {2})
        self.assertEqual(LC.event_key(ev, BOOK_OLD, 5.0, seq=2), "pct:0.0->5.0#2")
        # OCCURRENCE 1 KEEPS THE OLD SPELLING, so nothing already recorded is orphaned.
        self.assertEqual(LC.event_key(ev, BOOK_OLD, 5.0, seq=1), "pct:0.0->5.0")


class BlockerCAPriceMoveInsideAnOpenEventDoesNotTrade(unittest.TestCase):
    """**THE AUDITOR'S FOUR-PRICE TEST: 100 / 130 / 70 / 300.** [item 77]

    Item 73 froze the dollar TARGETS, which closed the equity channel. The gap was still
    `frozen_target - have_qty x CURRENT mark`, so the MARK channel stayed open: the same slot
    with the event OPEN transmitted `[AAA sell 0.153846, BBB sell 0.153846]` at 130 and
    2.333333 each at 300, against nothing at all when the event was closed.
    """

    PRICES = (100.0, 130.0, 70.0, 300.0)

    #: **THE TOP-UP THRESHOLD IS LOWERED FOR THESE CASES, AND THE REASON IS THAT IT HID THEM.**
    #: The remainder here is $50 against item 73's $250 default, so every price produced NO
    #: ORDERS AT ALL -- and "no sells" passed on a cycle that planned nothing, which is the
    #: vacuous pass this file exists to catch. It was caught by the positive half below, which
    #: is why that half is there. `LIVE_MIN_TOPUP` still gates buys and is tested where it
    #: belongs (item 73's own suite); this isolates the property item 77 is about.
    ENV = dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="5", LIVE_MIN_TOPUP="1")

    def _open_event_record(self):
        # 90% filled on a rebalance whose remainder is waiting, so the event is OPEN and the
        # frozen quantities are the ones it was authorised with.
        key = "rebalance:" + FORMED
        return {"slot": "1", "account_id": "acct-live-1", "processed": [key],
                "open_event": key,
                "holdings": {"AAPL": 2.25, "BBB": 2.25},
                "last_pct": 5.0, "last_event_date": OLD_FORMED,
                "frozen_targets": {key: {"AAPL": 250.0, "BBB": 250.0}},
                "frozen_target_qty": {key: {"AAPL": 2.5, "BBB": 2.5}}}

    def test_no_price_creates_a_sell(self):
        for mk in self.PRICES:
            got = _run77(env=self.ENV, record=self._open_event_record(),
                         book=BOOK, mark=mk)
            sells = [o for o in got["placed"] if o[1] == "sell"]
            self.assertEqual(sells, [],
                             "mark %.0f planned SELLS inside an open event: %r"
                             % (mk, got["placed"]))

    def test_the_quantity_is_the_same_at_every_price(self):
        # **THE POSITIVE HALF, and it is what makes the test above non-vacuous**: a tree that
        # simply stopped trading would pass "no sells" and fail this.
        qtys = {}
        for mk in self.PRICES:
            got = _run77(env=self.ENV, record=self._open_event_record(),
                         book=BOOK, mark=mk)
            buys = sorted((t, round(q, 6)) for t, s, q in got["placed"] if s == "buy")
            qtys[mk] = buys
        first = qtys[self.PRICES[0]]
        self.assertTrue(first, "no buy was planned at any price: %r" % (qtys,))
        for mk in self.PRICES[1:]:
            self.assertEqual(qtys[mk], first,
                             "the planned quantity moved with the price: %r" % (qtys,))

    def test_the_mark_cancels_in_the_planner_itself(self):
        # THE MECHANISM, asserted directly on the shipped planner so the property is pinned
        # where it lives rather than only through a cycle: with the SHARE COUNT frozen, the
        # order quantity is `|qty_frozen - have_qty|` and the mark cancels.
        held, frozen_qty = {"AAA": 9.0}, {"AAA": 10.0}
        seen = set()
        for mk in (100.0, 130.0, 70.0, 300.0):
            tgt = {t: q * mk for t, q in frozen_qty.items()}
            plan = LS.order_plan(tgt, dict(held), {t: {"mid": mk} for t in frozen_qty})
            seen.add(tuple(sorted((o["ticker"], o["side"], round(o["qty"], 9))
                                  for o in plan["orders"])))
        self.assertEqual(len(seen), 1, "the plan varied with the mark: %r" % (seen,))
        self.assertEqual(seen.pop(), (("AAA", "buy", 1.0),))

    def test_the_OLD_dollar_freeze_really_did_sell_which_is_the_control(self):
        # **THE CONTROL.** Without it the three tests above would pass on a tree that never
        # traded at all. This reproduces the pre-item-77 arithmetic from the same shipped
        # planner -- a frozen DOLLAR target against `have_qty x current mark` -- and requires
        # it to do the wrong thing, which is what the fix changed.
        held, frozen_dollars = {"AAA": 9.0}, {"AAA": 1000.0}
        sells = {}
        for mk in (130.0, 300.0):
            plan = LS.order_plan(dict(frozen_dollars), dict(held), {"AAA": {"mid": mk}})
            sells[mk] = [(o["side"], round(o["qty"], 6)) for o in plan["orders"]]
        self.assertEqual(sells[130.0][0][0], "sell", sells)
        self.assertEqual(sells[300.0][0][0], "sell", sells)


class TheTwoNonBlockingRepairs(unittest.TestCase):
    """An unfilled order alongside a cash gap, and the frozen maps not growing for ever."""

    def test_an_order_that_never_fills_beside_a_cash_gap_still_spends_a_ceiling_day(self):
        # Don's ruling has two halves and only the first was implemented: *"Waiting for cash
        # ... does not burn the ceiling. The ceiling still applies to orders that are sent and
        # never fill."* The cash-wait branch returned above the ceiling, so a resting order on
        # one name alongside a cash gap on another never escalated.
        key = "rebalance:" + FORMED
        rec = {"slot": "1", "account_id": "acct-live-1", "processed": [key],
               "open_event": key, "holdings": {"AAPL": 1.0},
               "last_pct": 5.0, "last_event_date": OLD_FORMED}
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="5"),
                     record=rec, book=BOOK, account=BROKE_ACCOUNT,
                     resting=(("BBB", "buy", 2.5, 0.0, key),))
        slot = got["slot"]
        if slot.get("send_outcome") in LC.SEND_OUTCOMES_THAT_DO_NOT_SPEND_A_CEILING_DAY:
            self.assertTrue(slot.get("ceiling_day_spent_on_resting_order"),
                            "a resting order alongside a cash gap spent no ceiling day: %r"
                            % (slot.get("reason"),))

    def test_the_frozen_maps_are_pruned_to_the_event_in_hand(self):
        # They carry one entry per name per event -- about 86 numbers for the Index book --
        # and the close paths only delete the key they are closing, so an event ABANDONED
        # rather than closed left its map behind for ever.
        stale = {"rebalance:2026-01-01": {"OLD": 1.0},
                 "pct:0.0->5.0": {"OLDER": 2.0}}
        rec = {"slot": "1", "account_id": "acct-live-1", "processed": [],
               "holdings": {}, "last_pct": 5.0, "last_event_date": "2026-08-01",
               "frozen_targets": dict(stale), "frozen_target_qty": dict(stale)}
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="5"),
                     record=rec, book=BOOK)
        for bag in ("frozen_targets", "frozen_target_qty"):
            keys = sorted((got["state"].get(bag) or {}))
            self.assertLessEqual(len(keys), 1, "%s kept %r" % (bag, keys))
            for k in keys:
                self.assertNotIn(k, stale, "%s kept a stale event: %r" % (bag, k))


class ThePaperSlotIsUnaffectedExceptWhereTheseRulesBind(unittest.TestCase):
    """The brief's own requirement, and the answer differs per blocker. [item 77]

    **A AND B DO NOT REACH THE PAPER SLOT AT ALL. C DOES, AND SHOULD.** Saying "the paper slot
    is unaffected" as a blanket claim would be false of C and would hide the thing a reader
    most needs to know -- so each is stated separately with its reason.
    """

    def test_blocker_A_cannot_reach_the_paper_slot_because_it_is_never_ARMED(self):
        # The paper slot is handed a literal `armed_state` -- *"the paper slot is always armed:
        # it is paper money on the paper host"* -- so `armed()` is never consulted for it and
        # the `stated` gate item 77 added to that function cannot apply. Asserted on the
        # source, because this is a statement about which code runs.
        src = io.open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "valuation", "edge", "live_cycle.py"),
            encoding="utf-8").read()
        tree = ast.parse(src)
        armed_calls = [n for n in ast.walk(tree)
                       if isinstance(n, ast.Call)
                       and getattr(n.func, "attr", None) == "armed"]
        self.assertEqual(len(armed_calls), 1,
                         "`armed` is called %d times; the paper slot must not be one of them"
                         % len(armed_calls))
        # ... and behaviourally: with NO percentage variable at all, the paper slot still runs.
        got = _run77(env={"LIVE_PILOT_ENABLED": "1"}, record=_holding_record(),
                     book=BOOK, mode="paper")
        self.assertNotIn("pct_unstated_while_holding", got["alerts"])

    def test_blocker_B_cannot_reach_the_paper_slot_because_it_is_not_at_zero(self):
        # The standing wind-down fires only at 0% while holding. The paper slot runs at 100%,
        # so `event_for` returns exactly what it returned before item 77 for it.
        st = {"last_event_date": OLD_FORMED, "last_pct": 100.0,
              "holdings": {"AAPL": 1.0}, "processed": []}
        ev = LS.event_for(st, BOOK_OLD, 100.0)
        self.assertFalse(ev["act"])
        self.assertEqual(ev["event"], "none")
        # AND THE ONE STATE THAT WOULD FIRE IS ONE THE PAPER SLOT IS NEVER IN.
        ev0 = LS.event_for(dict(st, last_pct=0.0), BOOK_OLD, 0.0)
        self.assertTrue(ev0["act"])
        self.assertTrue(ev0.get("standing"))

    def test_blocker_C_DOES_bind_on_the_paper_slot_and_that_is_correct(self):
        # The freeze is applied in `run_slot`, which both slots share, so the paper slot's
        # targets are frozen as quantities too. That is the intended answer rather than an
        # accident: drift trading on a price move is wrong on the paper book as well, and the
        # paper book is the one the live slot's parity is measured against -- freezing one and
        # not the other would make the two disagree on every price move by construction.
        src = io.open(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "valuation", "edge", "live_cycle.py"),
            encoding="utf-8").read()
        self.assertIn("frozen_target_qty", src)
        # ONE freeze site, shared, rather than a live-only branch.
        self.assertEqual(src.count('st["frozen_target_qty"] = _frozen_qty'), 1)

    def test_the_paper_slot_still_trades_normally_through_all_of_it(self):
        # THE POSITIVE CONTROL for this whole class: a tree where the paper slot had stopped
        # working would satisfy every assertion above.
        got = _run77(env=dict(_KEYS, ALPACA_ACCOUNT_1_LIVE_PCT="0"),
                     record=dict(_holding_record(), holdings={}), book=BOOK, mode="paper")
        self.assertTrue(any(a == "live_order_sent" for a in got["alerts"]),
                        "the paper slot transmitted nothing: %r" % (got["alerts"],))


if __name__ == "__main__":
    unittest.main(verbosity=2)
