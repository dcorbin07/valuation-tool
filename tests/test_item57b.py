"""ITEM 57 PART B -- the Index record, before the 2026-10-22 rebalance.

B1 an unpriced holding becomes visible; B2 the contract's corporate-action rule, from the next
segment; B3 exited names on their own line; B4 the rebalance door.
"""
import csv
import datetime as _dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  must precede any `valuation` import

from valuation.screener import index_mark as IM                       # noqa: E402

ROW_COLS = ["date", "day_n", "valquo_pct", "spy_pct", "excess_pp", "n_priced"]


def _history(rows):
    """A recorded history CSV, in the shape `_read_history` expects."""
    d = tempfile.mkdtemp()
    p = os.path.join(d, "hist.csv")
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(ROW_COLS)
        for r in rows:
            w.writerow([r.get(c, "") for c in ROW_COLS])
    return p


def _book(positions, *, inception="2026-07-30", rebalances=None):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "book.json")
    meta = {"inception_date": inception, "benchmark": "SPY", "scan_date": inception,
            "positions": positions}
    if rebalances is not None:
        meta["rebalances"] = rebalances
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return p


class B1_AnUnpricedHoldingIsVisible(unittest.TestCase):
    """ET was absent from the daily row for four sessions and nothing said so."""

    def test_a_complete_record_says_so_rather_than_going_quiet(self):
        hp = _history([{"date": "2026-10-12", "n_priced": 85}])
        got = IM.unpriced_run(hp, n_positions=85)
        self.assertTrue(got["ok"])
        self.assertEqual(got["n_unpriced"], 0)
        self.assertFalse(got["alert"])
        self.assertIn("every holding priced", got["message"])

    def test_a_run_reports_its_length_and_its_first_day(self):
        hp = _history([{"date": "2026-10-06", "n_priced": 85},
                       {"date": "2026-10-07", "n_priced": 85},
                       {"date": "2026-10-08", "n_priced": 84},
                       {"date": "2026-10-09", "n_priced": 84},
                       {"date": "2026-10-12", "n_priced": 84}])
        got = IM.unpriced_run(hp, n_positions=85)
        self.assertEqual(got["n_unpriced"], 1)
        self.assertEqual(got["since"], "2026-10-08")
        self.assertEqual(got["n_days"], 3)
        self.assertIn("1 holding unpriced since 2026-10-08", got["message"])

    def test_ONE_day_does_not_alert_and_more_than_one_does(self):
        """One missed day is an ordinary vendor hiccup; a run is something to look at."""
        one = _history([{"date": "2026-10-08", "n_priced": 85},
                        {"date": "2026-10-09", "n_priced": 84}])
        self.assertFalse(IM.unpriced_run(one, n_positions=85)["alert"])
        two = _history([{"date": "2026-10-08", "n_priced": 84},
                        {"date": "2026-10-09", "n_priced": 84}])
        self.assertTrue(IM.unpriced_run(two, n_positions=85)["alert"])

    def test_the_run_is_the_CURRENT_one_not_the_first_time_it_ever_happened(self):
        hp = _history([{"date": "2026-09-01", "n_priced": 84},   # an older, healed run
                       {"date": "2026-09-02", "n_priced": 85},
                       {"date": "2026-10-09", "n_priced": 84}])
        got = IM.unpriced_run(hp, n_positions=85)
        self.assertEqual(got["since"], "2026-10-09")
        self.assertEqual(got["n_days"], 1)

    def test_an_empty_record_reports_a_reason_rather_than_a_clean_bill(self):
        """`V6`'s rule: an unmeasured nothing and a measured nothing must differ."""
        got = IM.unpriced_run(_history([]), n_positions=85)
        self.assertFalse(got["ok"])
        self.assertTrue(got["reason"])
        self.assertFalse(got["alert"])

    def test_it_contacts_no_vendor(self):
        """The Index tab must not price 85 names on a page load, and the question is
        HISTORICAL -- only the record can answer 'for how long'."""
        import inspect
        src = inspect.getsource(IM.unpriced_run)
        for banned in ("get_history_df", "_closes", "close_series", "prices"):
            self.assertNotIn(banned, src, banned)

    def test_the_expected_count_is_the_BOOKS_not_the_best_row_ever_recorded(self):
        """Taking the max `n_priced` would make a book short since its FIRST row look
        complete -- the shortfall would define its own baseline."""
        hp = _history([{"date": "2026-10-08", "n_priced": 84},
                       {"date": "2026-10-09", "n_priced": 84}])
        self.assertEqual(IM.unpriced_run(hp, n_positions=85)["n_unpriced"], 1)

    def test_the_index_payload_carries_it(self):
        import inspect
        from valuation.web import app as A
        src = inspect.getsource(A.api_index) if hasattr(A, "api_index") else ""
        if not src:
            with open(A.__file__, encoding="utf-8") as fh:
                src = fh.read()
        self.assertIn("unpriced_run", src)

    def test_the_page_renders_the_line_and_says_a_live_name_is_not_a_sale(self):
        import valuation
        p = os.path.join(os.path.dirname(os.path.abspath(valuation.__file__)),
                         "web", "static", "app.js")
        with open(p, encoding="utf-8") as fh:
            js = fh.read()
        self.assertIn("unpriced", js)
        self.assertIn("never a sale", js)


class B2_TheCorporateActionRule(unittest.TestCase):
    """§5a's rule, from the next segment, with the current one left reproducible."""

    def test_the_cutover_is_the_next_rebalance(self):
        self.assertEqual(IM.CORPORATE_ACTION_FROM, "2026-10-22")

    def test_the_current_segment_is_UNCHANGED_so_recorded_rows_stay_reproducible(self):
        """Append-only: changing the arithmetic for a published segment is a back-fill, and
        §3 treats a back-fill as voiding the whole run."""
        # 0.98 / 0.02: ONE NAME DROPPING OUT MUST NOT BREACH THE 95% COVERAGE FLOOR, or
        # the row refuses and the test measures the floor instead of the rule. A real exit is
        # a ~0.8% position (WBS 0.78%, ET 0.79%), so this is also the right shape.
        bp = _book([{"ticker": "AAA", "weight": 0.98}, {"ticker": "BBB", "weight": 0.02}])
        hp = _history([{"date": "2026-08-03", "n_priced": 2}])
        base, mark = "2026-07-30", "2026-08-03"

        def fetch(t, **kw):
            # BBB has a base price and then stops -- the exact shape the rule is about.
            if t == "SPY":
                return _df({INCEPTION: 100.0, base: 100.0, mark: 101.0})
            if t == "AAA":
                return _df({base: 10.0, mark: 11.0})
            return _df({base: 20.0})
        got = IM.contract_row(mark, meta_path=bp, fetch=fetch, history_path=hp,
                              refuse_before_close=False)
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertFalse(got["corporate_action_applies"])
        # Renormalised over AAA alone: +10%, i.e. the OLD behaviour, bit for bit.
        self.assertAlmostEqual(got["row"]["valquo_pct"], 10.0, places=4)
        self.assertEqual(got["unpriced"], ["BBB"])
        self.assertEqual(got["exited"], [])

    def test_a_stopped_name_is_SOLD_AT_ITS_LAST_CLOSE_from_the_cutover(self):
        base, mark = "2026-10-22", "2026-11-20"
        bp = _book([{"ticker": "AAA", "weight": 0.98}, {"ticker": "BBB", "weight": 0.02}],
                   rebalances=[{"date": base, "scan_date": base, "positions": [
                       {"ticker": "AAA", "weight": 0.98},
                       {"ticker": "BBB", "weight": 0.02}]}])
        hp = _history([{"date": base, "n_priced": 2, "valquo_pct": 0.0},
                       {"date": mark, "n_priced": 2}])

        def fetch(t, **kw):
            if t == "SPY":
                return _spy(base, mark)
            if t == "AAA":
                return _df({base: 10.0, mark: 12.0})            # +20%
            return _df({base: 20.0, "2026-10-23": 22.0})        # +10%, then gone
        got = IM.contract_row(mark, meta_path=bp, fetch=fetch, history_path=hp,
                              refuse_before_close=False)
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertTrue(got["corporate_action_applies"])
        # THE WEIGHT STAYS IN, so BBB's realised +10% is KEPT rather than erased:
        # 0.98*20 + 0.02*10 = 19.8. Under the old rule BBB is renormalised away and the row
        # reads 20.0 -- which is the whole difference the contract's rule makes.
        self.assertAlmostEqual(got["row"]["valquo_pct"], 19.8, places=4)
        self.assertEqual(got["unpriced"], [])
        self.assertEqual(len(got["exited"]), 1)
        self.assertEqual(got["exited"][0]["ticker"], "BBB")

    def test_the_last_close_is_STORED_which_is_the_contracts_own_stated_limit(self):
        base, mark = "2026-10-22", "2026-11-20"
        bp = _book([{"ticker": "AAA", "weight": 0.98}, {"ticker": "BBB", "weight": 0.02}],
                   rebalances=[{"date": base, "scan_date": base, "positions": [
                       {"ticker": "AAA", "weight": 0.98},
                       {"ticker": "BBB", "weight": 0.02}]}])
        hp = _history([{"date": base, "n_priced": 2, "valquo_pct": 0.0},
                       {"date": mark, "n_priced": 2}])

        def fetch(t, **kw):
            if t == "SPY":
                return _spy(base, mark)
            if t == "AAA":
                return _df({base: 10.0, mark: 12.0})
            return _df({base: 20.0, "2026-10-23": 22.0})
        got = IM.contract_row(mark, meta_path=bp, fetch=fetch, history_path=hp,
                              refuse_before_close=False)
        ex = got["exited"][0]
        self.assertEqual(ex["last_date"], "2026-10-23")
        self.assertAlmostEqual(ex["last_close"], 22.0)
        self.assertAlmostEqual(ex["weight"], 0.02)

    def test_A_NAME_THAT_STILL_TRADES_IS_NEVER_SOLD(self):
        """ET's case, and the one error this rule must never make. ET's free route went
        silent for three sessions after its listing moved and then priced again."""
        base, mark = "2026-10-22", "2026-11-20"
        bp = _book([{"ticker": "AAA", "weight": 0.98}, {"ticker": "BBB", "weight": 0.02}],
                   rebalances=[{"date": base, "scan_date": base, "positions": [
                       {"ticker": "AAA", "weight": 0.98},
                       {"ticker": "BBB", "weight": 0.02}]}])
        hp = _history([{"date": base, "n_priced": 2, "valquo_pct": 0.0},
                       {"date": mark, "n_priced": 2}])
        # BBB's last price is only TWO trading days before the mark: a vendor gap.
        near = "2026-11-18"

        def fetch(t, **kw):
            if t == "SPY":
                return _spy(base, mark)
            if t == "AAA":
                return _df({base: 10.0, mark: 12.0})
            return _df({base: 20.0, near: 22.0})
        got = IM.contract_row(mark, meta_path=bp, fetch=fetch, history_path=hp,
                              refuse_before_close=False)
        self.assertTrue(got.get("ok"), got.get("reason"))
        self.assertEqual(got["exited"], [], "a two-day vendor gap was treated as a SALE")
        self.assertEqual(got["unpriced"], ["BBB"])

    def test_the_bound_errs_toward_still_trading(self):
        """`MA6`: err toward the state that refuses. Writing a false realised return into an
        append-only record is unrecoverable; leaving a name out for a few days is visible."""
        self.assertGreaterEqual(IM.STOPPED_TRADING_AFTER_DAYS, 5)

    def test_NO_SEGMENT_BASE_is_not_a_corporate_action(self):
        """WBS's case: its only close is AFTER the segment opened, so there is no purchase
        price to realise a return against and it stays unpriced under both rules."""
        base, mark = "2026-10-22", "2026-11-20"
        bp = _book([{"ticker": "AAA", "weight": 0.98}, {"ticker": "BBB", "weight": 0.02}],
                   rebalances=[{"date": base, "scan_date": base, "positions": [
                       {"ticker": "AAA", "weight": 0.98},
                       {"ticker": "BBB", "weight": 0.02}]}])
        hp = _history([{"date": base, "n_priced": 2, "valquo_pct": 0.0},
                       {"date": mark, "n_priced": 2}])

        def fetch(t, **kw):
            if t == "SPY":
                return _spy(base, mark)
            if t == "AAA":
                return _df({base: 10.0, mark: 12.0})
            return _df({"2026-10-24": 20.0})          # no base price at all
        got = IM.contract_row(mark, meta_path=bp, fetch=fetch, history_path=hp,
                              refuse_before_close=False)
        self.assertEqual(got["unpriced"], ["BBB"])
        self.assertEqual(got["exited"], [])

    def test_the_contract_carries_the_dated_correction_and_its_measured_size(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "PAPER_TRACK_CONTRACT.md"), encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("CORRECTION, 2026-10-14", txt)
        self.assertIn("2026-10-22", txt)
        for needle in ("WBS", "ET", "never a sale", "NEVER A SALE"):
            if needle.lower() in txt.lower():
                break
        else:
            self.fail("the correction names neither name")
        self.assertIn("DATA\nPROBLEM TO FIX, NEVER A SALE".replace("\n", " "),
                      txt.replace("\n", " "))


class B3_ExitedNamesAreNotHoldings(unittest.TestCase):

    def _js(self):
        import valuation
        p = os.path.join(os.path.dirname(os.path.abspath(valuation.__file__)),
                         "web", "static", "app.js")
        with open(p, encoding="utf-8") as fh:
            return fh.read()

    def test_the_holdings_table_excludes_exited_names(self):
        """WBS sat at row 58 among the held names with 0.00% weight and a blank company."""
        js = self._js()
        self.assertIn('.filter(p => (p || {}).status !== "exited")', js)

    def test_they_get_their_own_line_with_a_date_and_a_reason(self):
        js = self._js()
        i = js.index("Left the book")
        window = js[i:i + 900]
        self.assertIn("e.date", window)
        self.assertIn("e.reason", window)
        self.assertIn("not holdings", window)

    def test_the_exit_note_no_longer_says_the_amendment_is_outstanding(self):
        """Amendment 2 recorded the rule on 2026-10-04; the note said otherwise for ten
        days afterwards."""
        from valuation.screener.index_in_force import EXITS
        for e in EXITS:
            self.assertNotIn("outstanding", (e.get("ruling") or "").lower())
            self.assertIn("Amendment 2", e.get("ruling") or "")


class B4_TheRebalanceDoor(unittest.TestCase):

    def _setup(self, *, rows, event_date="2026-10-22"):
        positions = [{"ticker": "T%02d" % i, "weight": 1.0 / 60} for i in range(60)]
        bp = _book(positions, rebalances=[{"date": "2026-07-30", "scan_date": "2026-07-30",
                                           "positions": positions, "is_inception": True}])
        hp = _history(rows)
        ev = {"date": event_date, "scan_date": event_date, "positions": positions}
        return bp, hp, ev

    def test_an_event_dated_BEFORE_an_already_recorded_row_is_REFUSED(self):
        """THE DATED HAZARD. The 2026-10-22 event is appended on the evening of 10-23. If it
        slips past PT-WRITER's 03:07 UTC run, the 10-23 row has already been marked on the OLD
        book -- and recording the event then moves the segment base underneath it, leaving a
        row no code path can reproduce and append-only can never correct."""
        bp, hp, ev = self._setup(rows=[{"date": "2026-10-22", "n_priced": 60,
                                        "valquo_pct": 1.0},
                                       {"date": "2026-10-23", "n_priced": 60,
                                        "valquo_pct": 1.1}])
        got = IM.append_rebalance(ev, meta_path=bp, history_path=hp,
                                  conformance=lambda n, w: {"ok": True})
        self.assertFalse(got["ok"], got)
        self.assertFalse(got["wrote"])
        self.assertIn("2026-10-23", got["reason"])
        self.assertIn("AFTER", got["reason"])
        self.assertEqual(got.get("latest_recorded_row"), "2026-10-23")

    def test_the_same_event_is_ACCEPTED_when_no_later_row_exists(self):
        bp, hp, ev = self._setup(rows=[{"date": "2026-10-22", "n_priced": 60,
                                        "valquo_pct": 1.0}])
        got = IM.append_rebalance(ev, meta_path=bp, history_path=hp,
                                  conformance=lambda n, w: {"ok": True})
        self.assertTrue(got["ok"], got)
        self.assertTrue(got["wrote"])

    def test_a_row_ON_the_event_date_is_still_required(self):
        """The anchor rule is unweakened: the new refusal is about LATER rows."""
        bp, hp, ev = self._setup(rows=[{"date": "2026-10-21", "n_priced": 60,
                                        "valquo_pct": 1.0}])
        got = IM.append_rebalance(ev, meta_path=bp, history_path=hp,
                                  conformance=lambda n, w: {"ok": True})
        self.assertFalse(got["ok"])
        self.assertIn("no recorded row", got["reason"])

    def test_the_dry_run_names_what_cannot_be_priced(self):
        got = IM.unpriceable_on(
            [{"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}],
            "2026-10-22",
            fetch=lambda t, **kw: (_df({"2026-10-22": 10.0}) if t == "AAA" else _df({})))
        self.assertTrue(got["ok"])
        self.assertEqual(got["unpriceable"], ["BBB"])
        self.assertEqual(got["priced"], 1)
        self.assertAlmostEqual(got["weight_share"], 0.5)

    def test_the_dry_run_reports_a_clean_book_as_clean(self):
        got = IM.unpriceable_on([{"ticker": "AAA", "weight": 1.0}], "2026-10-22",
                                fetch=lambda t, **kw: _df({"2026-10-22": 10.0}))
        self.assertEqual(got["unpriceable"], [])
        self.assertEqual(got["priced"], 1)

    def test_the_cli_dry_run_calls_it(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(root, "scripts", "seed_track.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("unpriceable_on", src)
        self.assertIn("PRICE CHECK", src)
        # A dry run that cannot run its own check must SAY so rather than printing a clean line.
        self.assertIn("COULD NOT RUN", src)


def _df(by_date):
    """A minimal price frame in the shape `_closes` reads.

    A **"Date" COLUMN**, not a DatetimeIndex: `_closes` checks
    `"Date" not in df.columns` and returns `{}` otherwise -- so an index-shaped fixture reads
    as every name being unpriced, which is how my first cut of these tests "proved" a clean
    book was entirely unpriceable.
    """
    import pandas as pd
    keys = sorted(by_date or {})
    return pd.DataFrame({"Date": keys, "Close": [by_date[k] for k in keys]})


#: Inception, which the BENCHMARK leg is always priced from -- `contract_row` chains the book
#: by segment and deliberately leaves SPY cumulative from inception, so a fixture that prices
#: SPY only on the segment base makes the whole row refuse.
INCEPTION = "2026-07-30"


def _spy(base, mark):
    return _df({INCEPTION: 100.0, base: 100.0, mark: 100.0})


if __name__ == "__main__":
    unittest.main(verbosity=2)
