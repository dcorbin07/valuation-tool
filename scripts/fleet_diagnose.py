# -*- coding: utf-8 -*-
"""ITEM 46 - why the fleet has never recorded a filled order. READ-ONLY, repeatable.

Item 45 measured the symptom: across all 18 record streams, 16 books hold nothing but
self-checks, and `f3_bear_puts` -- the only declared book with order rows -- has 72 of them,
every one `fate=working` with `fill_price` and `venue` empty. This answers WHY, from the code,
the records and the broker, and it is read-only: `positions()` and `orders()` are GETs, and
nothing here can place, amend or cancel.

THE THREE ANSWERS IT PRODUCES, and they are three different causes rather than one:

1. **13 of the 16 have no entry rule implemented at all.** `fleet_books.RULES` registers FOUR
   books; the other fourteen (including `testbook`) are declared and un-armed, and `cycle()`
   has been saying so on every run. **Not a defect** -- it is the declared-but-not-armed state
   working as designed.
2. **`f1_fill_ab` is a RIDER.** Its own declaration says it never sends an order
   (`places_orders=False`). **Not a defect either.**
3. **EVERY BOOK, INCLUDING THE THREE ARMED ONES, IS BLOCKED AT THE GATE.** The live cycle
   returns `not_breathing_reason: ALL_BOOKS_BLOCKED_AT_GATE:SELFCHECK_STALE` with `armed: 0`,
   `blocked: 18` and every book reading *"the harness changed since the last self-check; re-run
   it"*. `harness_fingerprint()` covers eight modules, so any change to one invalidates all 18
   day-1 certificates, and re-certifying places a real sandbox order -- which is why it is a
   deliberate POST and not something the cron can do. **Nothing automatically re-certifies, so
   the fleet has been gated shut since the last harness change.**

AND THE FOURTH ANSWER IS THE ONE THAT MATTERS MOST: **f3's orders DID fill.** `orders()` returns
ZERO open orders while `positions()` returns 43 open positions with real cost bases, and 37 of
the 44 distinct contracts f3 ordered have one. The 72 rows say `working` because **a fill row is
written ONCE, at submission, from a status read moments later -- and nothing ever polls the
order again.** `submit()` even obtains the broker's order id (`_PB.order_id(res)`) and discards
it, because `RECORD_COLUMNS` has no column to put it in.

WHY THE RECONCILIATION THIS DIAGNOSIS RECOMMENDS CANNOT CLAIM AN ORDER-LEVEL FILL. Without the
order id the only join is the OCC symbol, and **the sandbox account is SHARED with the forward
options paper track** (`paper_track` marks through the same `PaperBroker`), which is visible in
the position list: it holds CALLS, and `f3_bear_puts` is a puts book. So a position in contract
X is evidence that someone's order in X filled, not that THIS row's did. The quantities confirm
the ambiguity rather than hiding it: 84 contracts held against 65 matched record rows.
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Where the service's streams are backed up to. `/data/` is gitignored and a worktree carries
#: it EMPTY, so the committed export is the only copy a lane can read -- and its own commit
#: date bounds every claim made from it.
BACKUP_DIR = os.path.join(REPO, "data_export", "fleet_records")


def streams(root: str = None) -> dict:
    """`{book: [rows]}` from the backup, with each row's `kind`."""
    out = {}
    for p in sorted(glob.glob(os.path.join(root or BACKUP_DIR, "*.csv"))):
        book = os.path.basename(p)[:-4]
        with io.open(p, newline="", encoding="utf-8") as fh:
            out[book] = list(csv.DictReader(fh))
    return out


def why_no_orders(root: str = None) -> dict:
    """Per book: is it armed, can it order, and did it ever try?

    The three states are DIFFERENT and the point of this function is that they are not lumped:
    a book with no rule is not a broken book, a rider is not a silent book, and an armed book
    with no orders is the only one of the three that is a question.
    """
    from valuation.edge.fleet_books import RULES
    st = streams(root)
    rows = []
    for book in sorted(st):
        kinds = collections.Counter(r.get("kind") for r in st[book])
        rule = RULES.get(book)
        if rule is None:
            state, why = "NO_ENTRY_RULE", ("declared but un-armed: no entry rule is "
                                           "implemented in fleet_books.RULES")
        elif not rule[1]:
            state, why = "RIDER", ("its own declaration says it never sends an order "
                                   "(places_orders=False)")
        elif not kinds.get("fill"):
            state, why = "ARMED_NO_ORDERS", ("armed and able to order, and has never written "
                                             "an order row -- the entry rule found no "
                                             "candidate, or the gate refused before it ran")
        else:
            state, why = "ARMED_WITH_ORDERS", "has order rows"
        rows.append({"book": book, "state": state, "why": why,
                     "records": len(st[book]), "kinds": dict(kinds)})
    census = collections.Counter(r["state"] for r in rows)
    return {"books": rows, "census": dict(census),
            "implemented": sorted(RULES),
            "can_order": sorted(k for k, (f, p) in RULES.items() if p)}


def unfilled(book: str = "f3_bear_puts", root: str = None) -> dict:
    """The order rows that never acquired an outcome, and what the record itself can say."""
    st = streams(root).get(book) or []
    orders = [r for r in st if r.get("kind") == "fill"]
    stuck = [r for r in orders
             if not (r.get("fill_price") or "").strip()
             and (r.get("fate") or "").strip() in ("working", "unknown", "")]
    return {
        "book": book, "order_rows": len(orders), "without_an_outcome": len(stuck),
        "order_type": dict(collections.Counter(r.get("order_type") for r in orders)),
        "fate": dict(collections.Counter(r.get("fate") for r in orders)),
        "distinct_contracts": len({r.get("occ") for r in orders}),
        "first": (orders[0].get("ts") if orders else None),
        "last": (orders[-1].get("ts") if orders else None),
        # The record keeps no broker order id, which is the whole reason an outcome could
        # never be written back: there is nothing to ask the broker about.
        "has_order_id_column": any("order_id" in (c or "")
                                   for c in (orders[0].keys() if orders else [])),
    }


def against_the_broker(book: str = "f3_bear_puts", root: str = None) -> dict:
    """What the sandbox says. READ-ONLY: `orders()` and `positions()` are both GETs."""
    from valuation.edge.paper_broker import PaperBroker
    st = streams(root).get(book) or []
    want = collections.Counter(r["occ"] for r in st
                               if r.get("kind") == "fill" and r.get("occ"))
    b = PaperBroker()
    try:
        open_orders = b.orders() or []
    except Exception as e:                                            # noqa: BLE001
        return {"ok": False, "reason": "orders() failed: %s" % type(e).__name__}
    try:
        pos = {p.get("symbol"): p for p in (b.positions() or [])}
    except Exception as e:                                            # noqa: BLE001
        return {"ok": False, "reason": "positions() failed: %s" % type(e).__name__}

    matched = sorted(o for o in want if o in pos)
    missing = sorted(o for o in want if o not in pos)
    held_qty = sum(float((pos.get(o) or {}).get("quantity") or 0) for o in matched)
    return {
        "ok": True, "base": b.base,
        "open_orders_at_the_broker": len(open_orders),
        "open_positions_at_the_broker": len(pos),
        "contracts_ordered": len(want),
        "contracts_with_a_position": len(matched),
        "contracts_without_a_position": len(missing),
        "without_a_position": missing,
        # NAMED, NOT HIDDEN: these do not tie, and the reason is that the account is shared.
        "held_quantity_on_matched": held_qty,
        "record_rows_on_matched": sum(want[o] for o in matched),
        "positions_not_in_this_book": len([s for s in pos if s not in want]),
        "attribution_limit": (
            "the join is the OCC symbol, because the record keeps no broker order id, and this "
            "sandbox account is SHARED with the forward options paper track (paper_track marks "
            "through the same PaperBroker -- the position list holds CALLS, and this is a puts "
            "book). So a position in a contract is evidence that SOMEONE's order in it filled, "
            "never that a particular row's did."),
        "verdict": ("THE ORDERS FILLED: zero open orders at the broker and a position in "
                    "%d of %d contracts, while every record row still reads `working`."
                    % (len(matched), len(want))) if (not open_orders and matched) else
                   ("no position matches, so the record's `working` may be literal"),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Why has the fleet never recorded a fill?")
    ap.add_argument("--book", default="f3_bear_puts")
    ap.add_argument("--root", default=None)
    ap.add_argument("--no-broker", action="store_true",
                    help="skip the read-only broker calls (offline)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)

    got = {"why_no_orders": why_no_orders(a.root), "unfilled": unfilled(a.book, a.root)}
    if not a.no_broker:
        got["broker"] = against_the_broker(a.book, a.root)

    if a.json:
        print(json.dumps(got, indent=1))
    else:
        w = got["why_no_orders"]
        print("")
        print("  WHY THE BOOKS PLACED NOTHING          %s" % w["census"])
        print("  entry rules implemented: %s" % ", ".join(w["implemented"]))
        print("  of those, able to order: %s" % ", ".join(w["can_order"]))
        print("")
        for r in w["books"]:
            print("   %-26s %-18s %s" % (r["book"], r["state"], r["kinds"]))
        u = got["unfilled"]
        print("")
        print("  %s: %d order rows, %d with no outcome, types %s, fates %s"
              % (u["book"], u["order_rows"], u["without_an_outcome"], u["order_type"],
                 u["fate"]))
        print("  a broker order id is stored: %s" % u["has_order_id_column"])
        if "broker" in got:
            b = got["broker"]
            print("")
            if not b.get("ok"):
                print("  THE BROKER: %s" % b.get("reason"))
            else:
                print("  THE BROKER (%s)" % b["base"])
                print("   open orders   : %d" % b["open_orders_at_the_broker"])
                print("   open positions: %d" % b["open_positions_at_the_broker"])
                print("   contracts ordered %d, with a position %d, without %d"
                      % (b["contracts_ordered"], b["contracts_with_a_position"],
                         b["contracts_without_a_position"]))
                print("   held qty on matched %s against %s record rows (they do NOT tie)"
                      % (b["held_quantity_on_matched"], b["record_rows_on_matched"]))
                print("   -> %s" % b["verdict"])
        print("")
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump(got, fh, indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
