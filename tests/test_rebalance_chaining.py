"""REBALANCE CHAINING — the book turns over and inception never moves.

**THE BIND THIS RESOLVES.** `PAPER_TRACK_CONTRACT.md` §3 voids a window for *"a book that
silently stopped rebalancing"*, and §5a rule 2 says a rebalance is **NOT** a vintage event — so
the book must turn over and inception must not move. But `contract_row` priced every position
from inception, so a name entering at a rebalance was credited with the market's move from
BEFORE it was held. The disabled Cowork task resolved that by moving inception, which §5a
forbids outright.

**THE STANDARD ANSWER IS INDEX CHAINING**, and these tests pin its load-bearing properties:

  * **A NO-OP EVENT CHANGES NOTHING BY EXACTLY 0.0.** An event whose positions equal the book
    in force must leave every subsequent row bit-identical. Not "close" — 0.0. This is the test
    that would catch an anchor read from the wrong row, because a wrong anchor shifts every
    later row by a CONSTANT, which looks entirely plausible in isolation.

  * **A SWAPPED NAME IS PRICED FROM R, NOT FROM INCEPTION.** The defect itself, stated
    directly.

  * **AN EVENT ON AN UNMARKED DAY IS REFUSED.** The anchor has to be a day the track actually
    recorded, or the level being compounded onto is a guess that never surfaces again.

Run: python tests/test_rebalance_chaining.py
"""
from __future__ import annotations

import csv
import datetime as dt
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_mark as IM                          # noqa: E402

PASSED = FAILED = 0
INC = dt.date(2026, 7, 30)


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


def meta(rebalances=None):
    m = {"inception_date": INC.isoformat(), "benchmark": "SPY",
         "positions": [{"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}]}
    if rebalances is not None:
        m["rebalances"] = rebalances
    return m


def events(rebalances=None):
    m = meta(rebalances)
    return IM.rebalance_events(m, INC, m["positions"])


def test_an_absent_rebalance_list_is_exactly_event_zero():
    """An old book must be bit-identical under the new code."""
    ev = events()
    assert len(ev) == 1, ev
    assert ev[0]["date"] == INC and ev[0]["is_inception"] is True
    assert [p["ticker"] for p in ev[0]["positions"]] == ["AAA", "BBB"]


def test_the_event_in_force_is_the_latest_on_or_before_the_mark():
    ev = events([{"date": "2026-10-22", "positions": [{"ticker": "CCC", "weight": 1.0}]}])
    assert IM.event_in_force(ev, dt.date(2026, 10, 21))["is_inception"] is True
    # ON the day itself the NEW book is in force: a rebalance executes at that day's close and
    # its row is the anchor the next segment compounds onto.
    assert IM.event_in_force(ev, dt.date(2026, 10, 22))["is_inception"] is False
    assert IM.event_in_force(ev, dt.date(2026, 11, 2))["date"] == dt.date(2026, 10, 22)


def test_an_event_dated_on_or_before_inception_is_dropped():
    """It would shadow event zero and silently reorder the record."""
    for d in ("2026-07-30", "2026-07-01"):
        ev = events([{"date": d, "positions": [{"ticker": "CCC", "weight": 1.0}]}])
        assert len(ev) == 1, "%s was not dropped: %r" % (d, ev)


def test_events_are_ordered_oldest_first_however_they_were_written():
    ev = events([{"date": "2026-11-20", "positions": [{"ticker": "C", "weight": 1.0}]},
                 {"date": "2026-10-22", "positions": [{"ticker": "D", "weight": 1.0}]}])
    assert [e["date"].isoformat() for e in ev] == ["2026-07-30", "2026-10-22", "2026-11-20"], ev


def test_a_malformed_event_is_dropped_rather_than_guessed_at():
    for bad in ({"positions": [{"ticker": "C", "weight": 1.0}]},          # no date
                {"date": "not-a-date", "positions": [{"ticker": "C", "weight": 1.0}]},
                {"date": "2026-10-22", "positions": []},                  # no positions
                {"date": "2026-10-22"}):
        assert len(events([bad])) == 1, "a malformed event survived: %r" % bad


def test_the_recorded_level_reads_the_row_rather_than_recomputing_it():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "h.csv")
        with open(p, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(IM.ROW_COLUMNS), lineterminator="\r\n")
            w.writeheader()
            w.writerow({"date": "2026-10-22", "day_n": 60, "valquo_pct": 4.8831,
                        "spy_pct": 4.2572, "excess_pp": 0.6259, "n_priced": 85})
        lvl = IM._recorded_level("2026-10-22", p)
        assert lvl is not None and abs(lvl - 1.048831) < 1e-12, lvl
        assert IM._recorded_level("2026-10-21", p) is None, "an unmarked day returned a level"


# =======================================================================================
# END TO END — through contract_row, against a real book file and a real history file
# =======================================================================================
PRICES = {
    # inception, the rebalance day, and the mark. AAA/BBB are the original book; CCC enters
    # at the rebalance and MOVES SHARPLY BEFORE IT, which is what makes the from-inception
    # defect visible rather than a rounding difference.
    "SPY": {"2026-07-30": 100.0, "2026-10-22": 110.0, "2026-11-02": 121.0},
    "AAA": {"2026-07-30": 100.0, "2026-10-22": 120.0, "2026-11-02": 132.0},
    "BBB": {"2026-07-30": 100.0, "2026-10-22": 120.0, "2026-11-02": 132.0},
    "CCC": {"2026-07-30": 100.0, "2026-10-22": 200.0, "2026-11-02": 220.0},
}


def fake_fetch(ticker, days=400, as_of=None):
    import pandas as pd
    d = PRICES.get(str(ticker).upper())
    if not d:
        return None
    f = pd.DataFrame({"Date": pd.to_datetime(sorted(d)),
                      "Close": [d[k] for k in sorted(d)]})
    f.attrs["valquo_src"] = "test"
    return f


def _book_and_history(tmp, rebalances=None, rows=(("2026-10-22", 20.0, 10.0),)):
    """A book file and a history file on disk, as the shipped code reads them."""
    import json
    bp = os.path.join(tmp, "book.json")
    m = meta(rebalances)
    with open(bp, "w", encoding="utf-8") as f:
        json.dump(m, f)
    hp = os.path.join(tmp, "h.csv")
    with open(hp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(IM.ROW_COLUMNS), lineterminator="\r\n")
        w.writeheader()
        for (d, vq, sp) in rows:
            w.writerow({"date": d, "day_n": 60, "valquo_pct": vq, "spy_pct": sp,
                        "excess_pp": round(vq - sp, 4), "n_priced": 2})
    return bp, hp


def _row(tmp, rebalances, mark="2026-11-02", rows=(("2026-10-22", 20.0, 10.0),)):
    bp, hp = _book_and_history(tmp, rebalances, rows)
    return IM.contract_row(mark, meta_path=bp, fetch=fake_fetch,
                           refuse_before_close=False, history_path=hp)


def test_a_noop_event_changes_every_subsequent_row_by_EXACTLY_zero():
    """THE pin. An event whose positions equal the book in force must move nothing at all.

    A wrong anchor shifts every later row by a CONSTANT, which is entirely plausible-looking
    in isolation and would never be noticed. Exactly 0.0 is the only assertion that catches it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = _row(tmp, None)
        assert base["ok"], base
        # The recorded 2026-10-22 level must equal what the un-chained arithmetic produces on
        # that day, or the no-op is not a no-op for a reason that has nothing to do with
        # chaining. AAA and BBB are both +20% there, so the level is 20.0%.
        noop = _row(tmp, [{"date": "2026-10-22",
                           "positions": [{"ticker": "AAA", "weight": 0.5},
                                         {"ticker": "BBB", "weight": 0.5}]}])
        assert noop["ok"], noop
        d = abs(noop["row"]["valquo_pct"] - base["row"]["valquo_pct"])
        assert d == 0.0, ("a no-op rebalance moved the row by %r (chained %r vs unchained %r)"
                          % (d, noop["row"]["valquo_pct"], base["row"]["valquo_pct"]))


def test_a_swapped_name_is_priced_from_R_and_not_from_inception():
    """The defect itself. CCC doubles BEFORE the rebalance; chaining must not credit that."""
    with tempfile.TemporaryDirectory() as tmp:
        got = _row(tmp, [{"date": "2026-10-22",
                          "positions": [{"ticker": "CCC", "weight": 1.0}]}])
        assert got["ok"], got
        # CCC runs 200 -> 220 over the segment, i.e. +10%, compounded onto the recorded 20.0%:
        #   1.20 x 1.10 = 1.32  ->  32.0%
        assert abs(got["row"]["valquo_pct"] - 32.0) < 1e-9, got["row"]

        # ...and the from-inception answer would have been 100 -> 220 = +120%, which is the
        # number this whole change exists to stop being recorded.
        assert abs(got["row"]["valquo_pct"] - 120.0) > 1.0, (
            "the row was priced from inception, not from the rebalance")


def test_an_event_on_a_day_the_track_never_marked_is_REFUSED():
    """The anchor must be a day that was actually recorded, never a neighbouring row."""
    with tempfile.TemporaryDirectory() as tmp:
        got = _row(tmp, [{"date": "2026-10-21",          # not in the history file
                          "positions": [{"ticker": "CCC", "weight": 1.0}]}],
                   rows=(("2026-10-22", 20.0, 10.0),))
        assert got["ok"] is False, got
        assert "no recorded row" in (got.get("reason") or ""), got["reason"]
        assert got["row"] is None


def test_the_benchmark_stays_cumulative_from_inception_across_a_rebalance():
    """SPY never rebalances with us; chaining it would change what the excess measures."""
    with tempfile.TemporaryDirectory() as tmp:
        got = _row(tmp, [{"date": "2026-10-22",
                          "positions": [{"ticker": "CCC", "weight": 1.0}]}])
        assert got["ok"], got
        # SPY 100 -> 121 from INCEPTION is +21%, not the +10% of the segment alone.
        assert abs(got["row"]["spy_pct"] - 21.0) < 1e-9, got["row"]


def test_inception_and_day_n_are_untouched_by_a_rebalance():
    """Section 5a rule 2: a rebalance is not a vintage event, so the clock must not move."""
    with tempfile.TemporaryDirectory() as tmp:
        a = _row(tmp, None)
        b = _row(tmp, [{"date": "2026-10-22",
                        "positions": [{"ticker": "CCC", "weight": 1.0}]}])
        assert a["ok"] and b["ok"]
        assert a["row"]["day_n"] == b["row"]["day_n"], (a["row"]["day_n"], b["row"]["day_n"])
        import json
        bp = os.path.join(tmp, "book.json")
        assert json.load(open(bp, encoding="utf-8"))["inception_date"] == INC.isoformat()


# =======================================================================================
# THE APPEND DOOR'S REFUSALS — append-only, ordered, anchored, and the Index
# =======================================================================================
def _ok_conformance(n, w, n_eligible=None):
    return {"ok": True, "reason": ""}


def _no_conformance(n, w, n_eligible=None):
    return {"ok": False, "reason": "only %d names" % n}


def _event(date="2026-11-20", ticker="CCC"):
    return {"date": date, "scan_date": "2026-11-18",
            "positions": [{"ticker": ticker, "weight": 1.0}]}


def _fresh(tmp, rebalances=None, rows=(("2026-10-22", 20.0, 10.0),
                                       ("2026-11-20", 25.0, 12.0))):
    return _book_and_history(tmp, rebalances, rows)


def test_a_legal_event_is_appended_and_inception_is_untouched():
    import json
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        before = json.load(open(bp, encoding="utf-8"))["inception_date"]
        r = IM.append_rebalance(_event(), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert r["ok"] and r["wrote"], r
        after = json.load(open(bp, encoding="utf-8"))
        assert after["inception_date"] == before, "INCEPTION MOVED"
        assert len(after["rebalances"]) == 1, after["rebalances"]


def test_re_sending_the_identical_event_is_a_no_op_not_an_error():
    """A retried request must not corrupt anything, and must not read as a failure."""
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        a = IM.append_rebalance(_event(), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        b = IM.append_rebalance(_event(), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert a["wrote"] is True and b["wrote"] is False, (a, b)
        assert b["ok"] is True, b
        assert b["n_events"] == 1, b


def test_a_DIFFERENT_event_on_a_recorded_date_is_REFUSED_as_a_rewrite():
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        IM.append_rebalance(_event(ticker="CCC"), meta_path=bp, history_path=hp,
                            conformance=_ok_conformance)
        r = IM.append_rebalance(_event(ticker="DDD"), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert r["ok"] is False and r["wrote"] is False, r
        assert "append-only" in r["reason"], r["reason"]


def test_an_event_dated_BEFORE_the_last_one_is_REFUSED():
    """Events are an ordered history; one landing out of order silently changes which book
    was in force for every day after it."""
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        IM.append_rebalance(_event("2026-11-20"), meta_path=bp, history_path=hp,
                            conformance=_ok_conformance)
        r = IM.append_rebalance(_event("2026-10-22"), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert r["ok"] is False, r
        assert "ordered history" in r["reason"], r["reason"]


def test_an_event_on_an_unmarked_day_is_REFUSED_by_the_door_too():
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        r = IM.append_rebalance(_event("2026-11-19"), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert r["ok"] is False, r
        assert "no recorded row" in r["reason"], r["reason"]


def test_a_book_that_is_not_the_Index_is_REFUSED():
    """The seed door's own lesson one step later: a truncated scan must not be installed
    under the Index's name."""
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        r = IM.append_rebalance(_event(), meta_path=bp, history_path=hp,
                                conformance=_no_conformance)
        assert r["ok"] is False, r
        assert "not the contract-bound Index" in r["reason"], r["reason"]


def test_an_event_on_or_before_inception_is_REFUSED():
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp, rows=(("2026-07-30", 0.0, 0.0),))
        r = IM.append_rebalance(_event("2026-07-30"), meta_path=bp, history_path=hp,
                                conformance=_ok_conformance)
        assert r["ok"] is False, r
        assert "event zero" in r["reason"], r["reason"]


def test_a_malformed_event_is_refused_rather_than_written():
    with tempfile.TemporaryDirectory() as tmp:
        bp, hp = _fresh(tmp)
        for bad in ({"positions": [{"ticker": "C", "weight": 1.0}]},
                    {"date": "2026-11-20", "positions": []},
                    "not a dict"):
            r = IM.append_rebalance(bad, meta_path=bp, history_path=hp,
                                    conformance=_ok_conformance)
            assert r["ok"] is False and r["wrote"] is False, (bad, r)


def run():
    global PASSED, FAILED
    print("REBALANCE CHAINING")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
