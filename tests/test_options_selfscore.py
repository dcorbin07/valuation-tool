# -*- coding: utf-8 -*-
"""ITEM 24 — the options record could only close a trade the paper broker had bought.

THE DEFECT, MEASURED ON THE LIVE SERVICE 2026-10-03
---------------------------------------------------
`/api/options-scorecard`: **26 open, 7 closed**, and the open ones could not close for two
separate reasons.

**EIGHT HAVE NO CONTRACT.** Alert ids 9, 10, 12, 13, 16, 18, 24, 25 (JNJ, MET, JNJ, DELL, ELV,
ELV, ETN, KMI) carry `contract_source: "descriptor (no chain)"` and no expiry: nothing to mark,
nothing to settle, no date on which they could mature. They sat in "26 open" forever.

**AND OF THE 18 WITH A CONTRACT, ONLY THE ONES THE BROKER BOUGHT WERE SCORED.**
`options_tracker`'s own docstring says why: *"an external scheduled process (Cowork) writes
`exit_*` back via `record_outcome`"*. That process no longer exists, and the only in-repo caller
of `record_outcome` is `paper_track`, which closes a position the PAPER BROKER holds.

    ELV alert 14 — 420C 2026-11-20, entry 27.80, last 7.00, −75%
    HCA alert  7 — 430C 2026-10-16, entry 22.40, last 8.60, −62%

both well past their own pre-registered **−50% stop**, neither held, neither scored. One
contract cost **$2,780** and **$2,240** against a **$1,000** budget — so the exclusion is the
sizing veto, which is a fact about this account's SIZE and not about the alert.

**THE CENSORING IS THEREFORE ONE-SIDED AND CORRELATES WITH PREMIUM.** `MA36` found the same
shape one layer down, with expiry rather than affordability as the filter: *"winners and quoted
losers are scored and the −100% tail is dropped, which is the opposite of the backtest this book
exists to validate."*

WHAT THIS SUITE PINS
--------------------
That an alert is scored against ITS OWN logged policy; that the two live examples fire their own
stop; that a no-contract alert leaves "open" without entering the closed set; that the shared
exit rule is ONE rule; and that the paper book is untouched.
"""
import datetime as dt
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.edge import options_selfscore as SS                 # noqa: E402
from valuation.edge import options_tracker as OT                   # noqa: E402
from valuation.edge import paper_track as PT                       # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TODAY = dt.date(2026, 10, 3)

#: The two live rows, as the service reports them. Reproduced as fixtures so the assertions are
#: about THOSE trades rather than about hypothetical ones.
ELV14 = {"id": 14, "ticker": "ELV", "opt_right": "call", "strike": 420.0,
         "expiry": "2026-11-20", "occ_symbol": "ELV261120C00420000",
         "entry_premium": 27.80, "alert_ts": "2026-09-15T20:30:00", "dte": 66,
         "features": "{}"}
HCA7 = {"id": 7, "ticker": "HCA", "opt_right": "call", "strike": 430.0,
        "expiry": "2026-10-16", "occ_symbol": "HCA261016C00430000",
        "entry_premium": 22.40, "alert_ts": "2026-09-02T20:30:00", "dte": 44,
        "features": "{}"}
#: One of the eight. No strike, no expiry, no OCC symbol.
KMI25 = {"id": 25, "ticker": "KMI", "opt_right": "call", "strike": None,
         "expiry": None, "occ_symbol": None, "entry_premium": None,
         "alert_ts": "2026-09-29T20:30:00", "dte": None,
         "features": '{"contract": {"source": "descriptor (no chain)"}}'}


def _store():
    """THE REAL `Store`, on a temp DB.

    The `option_alerts` DDL lives in `screener/store.py`, not in `options_tracker` -- the
    tracker only has `ensure_pnl_schema`, which ADDS columns to a table it assumes exists. A
    hand-rolled stand-in would therefore have had to reproduce that DDL, which is the
    wrong-object family: the suite would be testing the fixture's idea of the schema rather
    than the schema. `tests/test_scream_log.py` uses exactly this fixture for the same reason.
    """
    from valuation.screener.store import Store
    return Store(os.path.join(tempfile.mkdtemp(prefix="valquo_selfscore_"), "s.db"))


def store_with(alerts):
    st = _store()
    OT.ensure_pnl_schema(st)
    for a in alerts:
        OT.log_alert(st, a)
    return st


def row_for(st, ticker):
    """One alert row, BY TICKER.

    `log_alert` assigns its own autoincrement id, so the `"id"` in these fixtures -- which are
    the live service's ids, kept because they are what the brief names -- is NOT the id in a
    temp store. Looking a row up by the fixture's id silently returned `None` and five tests
    failed on `NoneType is not subscriptable` rather than on anything they were about.
    """
    with st._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts WHERE ticker=?", (ticker,))
        r = cur.fetchone()
        return dict(zip([d[0] for d in cur.description], r)) if r else {}


def quoter(marks):
    """`quotes(occs) -> {occ: {"bid": ..}}`, from a dict. Counts its calls."""
    calls = []

    def _q(occs):
        calls.append(list(occs))
        return {o: ({"bid": marks[o]} if marks.get(o) is not None else {}) for o in occs}

    _q.calls = calls
    return _q


# ==========================================================================================
# THE RULE IS ONE RULE
# ==========================================================================================
class TheExitRuleIsShared(unittest.TestCase):
    """`B7`: a second implementation for the alert path is how a scorer and a broker come to
    disagree about the same trade."""

    def test_the_rule_lives_in_options_tracker(self):
        self.assertTrue(callable(getattr(OT, "exit_decision", None)))

    def test_paper_track_delegates_rather_than_reimplementing(self):
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "paper_track.py"),
                  encoding="utf-8") as f:
            tree = ast.parse(f.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_exit_decision")
        body = ast.unparse(fn)
        self.assertIn("OT.exit_decision", body,
                      "`paper_track._exit_decision` no longer delegates, so the alert path and "
                      "the broker path can drift on what 'the stop fired' means")
        self.assertNotIn('"stop"', body, "the rule has been re-inlined: " + body[:300])
        self.assertNotIn("'stop'", body, "the rule has been re-inlined: " + body[:300])

    def test_the_selfscorer_delegates_too(self):
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "options_selfscore.py"),
                  encoding="utf-8") as f:
            tree = ast.parse(f.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "decide")
        body = ast.unparse(fn)
        self.assertIn("OT.exit_decision", body)

    def test_the_close_before_expiry_constant_has_exactly_one_definition(self):
        """`MA5`: the Harvey-Liu-Zhu bar froze at 3.0 because its definition sat inside one of
        its consumers. This constant now governs two callers."""
        import ast
        n = 0
        for rel in ("options_tracker.py", "paper_track.py", "options_selfscore.py"):
            with open(os.path.join(REPO, "valuation", "edge", rel), encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if (isinstance(node, ast.Assign) and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == "CLOSE_BEFORE_EXPIRY_DAYS"):
                    if isinstance(node.value, ast.Constant):
                        n += 1
        self.assertEqual(n, 1, "CLOSE_BEFORE_EXPIRY_DAYS is defined as a literal %d times" % n)

    def test_the_two_modules_agree_on_its_value(self):
        self.assertEqual(PT.CLOSE_BEFORE_EXPIRY_DAYS, OT.CLOSE_BEFORE_EXPIRY_DAYS)

    def test_the_rule_order_is_preserved(self):
        """A hard stop beats a target beats expiry beats a soft time stop, and the order IS the
        behaviour: a mark simultaneously below the stop and past the time stop must read
        'stop', because that is what a real account would have done first."""
        d = OT.exit_decision(0.4, 2.0, 0.5, "2026-10-04", "2026-09-01", TODAY)
        self.assertEqual(d, "stop")
        d = OT.exit_decision(2.5, 2.0, 0.5, "2026-10-04", "2026-09-01", TODAY)
        self.assertEqual(d, "target")
        d = OT.exit_decision(1.0, 2.0, 0.5, "2026-10-04", "2026-09-01", TODAY)
        self.assertEqual(d, "expiry")
        d = OT.exit_decision(1.0, 2.0, 0.5, "2026-12-18", "2026-09-01", TODAY)
        self.assertEqual(d, "time_stop")


# ==========================================================================================
# THE TWO LIVE TRADES
# ==========================================================================================
class TheTwoLiveStopsFire(unittest.TestCase):
    """The whole item in two assertions."""

    def test_ELV_alert_14_fires_its_own_stop(self):
        self.assertEqual(SS.decide(ELV14, 7.00, TODAY), "stop")

    def test_HCA_alert_7_fires_its_own_stop(self):
        self.assertEqual(SS.decide(HCA7, 8.60, TODAY), "stop")

    def test_the_stop_is_the_alerts_OWN_level_and_not_a_default_typed_here(self):
        """`PT._exit_policy` reads the alert's logged policy; these rows predate one, so the
        default applies -- and the default is read from the module, never retyped."""
        lv = SS.levels(ELV14)
        self.assertAlmostEqual(lv["stop_pct"], OT.DEFAULT_STOP_PCT, places=9)
        self.assertAlmostEqual(lv["stop_premium"], 27.80 * (1.0 + OT.DEFAULT_STOP_PCT),
                               places=9)
        self.assertAlmostEqual(lv["target_premium"], 27.80 * (1.0 + OT.DEFAULT_TARGET_PCT),
                               places=9)

    def test_an_alert_with_its_OWN_policy_is_honoured(self):
        """The whole reason the policy is read rather than assumed: session 16 found the resume
        path silently collapsing to the defaults for any alert whose policy differed."""
        a = dict(ELV14, features='{"exit_policy": {"stop_pct": -0.80, "target_pct": 3.0}}')
        lv = SS.levels(a)
        self.assertAlmostEqual(lv["stop_premium"], 27.80 * 0.20, places=9)
        # 7.00 is above a -80% stop of 5.56, so this alert would NOT have stopped out.
        self.assertIsNone(SS.decide(a, 7.00, TODAY))

    def test_a_healthy_mark_fires_nothing(self):
        self.assertIsNone(SS.decide(ELV14, 20.0, TODAY))

    def test_the_time_stop_is_anchored_on_the_ALERTS_OWN_clock(self):
        """Half the ORIGINAL tenor. Computing it from today's date-to-expiry would re-arm the
        clock every run and the stop would never fire."""
        lv = SS.levels(ELV14)
        self.assertEqual(lv["time_stop_date"], "2026-10-18")      # 2026-09-15 + 33 days
        self.assertEqual(SS.decide(ELV14, 20.0, dt.date(2026, 10, 19)), "time_stop")


# ==========================================================================================
# THE EIGHT THAT ARE NOT TRADES
# ==========================================================================================
class TheNoContractAlerts(unittest.TestCase):
    def test_one_is_not_scoreable(self):
        self.assertFalse(SS.is_scoreable(KMI25))

    def test_a_complete_one_is(self):
        self.assertTrue(SS.is_scoreable(ELV14))

    def test_half_a_contract_is_not_scoreable_either(self):
        """An expiry with no OCC symbol cannot be quoted; an OCC symbol with no expiry cannot
        be settled or time-stopped. Either way it would sit in 'open' forever."""
        self.assertFalse(SS.is_scoreable(dict(ELV14, occ_symbol=None)))
        self.assertFalse(SS.is_scoreable(dict(ELV14, expiry=None)))
        self.assertFalse(SS.is_scoreable(dict(ELV14, expiry="")))

    def test_it_leaves_open_without_entering_the_closed_set(self):
        """NOT `closed`: `_stats` would then put it in the denominator of a hit rate it cannot
        belong to, since it has no return at all."""
        st = store_with([ELV14, KMI25])
        res = SS.score_open_alerts(st, quoter({"ELV261120C00420000": 20.0}), today=TODAY)
        self.assertEqual(res["no_contract"], 1)
        sc = OT.scorecard(st)
        self.assertEqual(sc["n_no_contract"], 1)
        self.assertEqual(sc["n_open"], 1)
        self.assertEqual((sc["overall"] or {}).get("n_closed") or 0, 0)

    def test_the_scorecard_says_what_the_third_count_means(self):
        st = store_with([KMI25])
        SS.score_open_alerts(st, quoter({}), today=TODAY)
        sc = OT.scorecard(st)
        self.assertIn("no option chain", sc["no_contract_note"])
        self.assertIn("not positions awaiting an outcome", sc["no_contract_note"])

    def test_the_note_is_empty_when_there_are_none(self):
        """A note about a state that does not apply is noise on every other book."""
        st = store_with([ELV14])
        self.assertEqual(OT.scorecard(st)["no_contract_note"], "")

    def test_the_reason_travels_on_the_row(self):
        st = store_with([KMI25])
        SS.score_open_alerts(st, quoter({}), today=TODAY)
        r = row_for(st, "KMI")
        self.assertEqual(r.get("status"), SS.NO_CONTRACT)
        self.assertIn("not scoreable", r.get("exit_reason") or "")


# ==========================================================================================
# SCORING THE BOOK
# ==========================================================================================
class ScoringTheOpenBook(unittest.TestCase):
    def setUp(self):
        self.st = store_with([ELV14, HCA7, KMI25])

    def test_both_losers_are_closed_at_their_own_stop(self):
        q = quoter({"ELV261120C00420000": 7.00, "HCA261016C00430000": 8.60})
        res = SS.score_open_alerts(self.st, q, today=TODAY)
        self.assertEqual(res["closed"], 2, res)
        self.assertEqual(res["no_contract"], 1)
        reasons = {e["ticker"]: e["reason"] for e in res["exits"] if e.get("reason")}
        self.assertEqual(reasons.get("ELV"), "stop")
        self.assertEqual(reasons.get("HCA"), "stop")

    def test_the_pnl_is_computed_by_record_outcome_and_not_here(self):
        """`MA46`'s gross-and-net decision and `MA36`'s -100% convention both live there; a
        second P&L path would be able to disagree with the stored premiums."""
        q = quoter({"ELV261120C00420000": 7.00, "HCA261016C00430000": 8.60})
        SS.score_open_alerts(self.st, q, today=TODAY)
        with self.st._conn() as c:
            rows = dict(c.execute("SELECT ticker, pnl_pct FROM option_alerts "
                                  "WHERE status=?", ("closed",)).fetchall())
        self.assertAlmostEqual(rows["ELV"], 7.00 / 27.80 - 1.0, places=9)
        self.assertAlmostEqual(rows["HCA"], 8.60 / 22.40 - 1.0, places=9)

    def test_the_scorecard_now_counts_them(self):
        q = quoter({"ELV261120C00420000": 7.00, "HCA261016C00430000": 8.60})
        SS.score_open_alerts(self.st, q, today=TODAY)
        o = OT.scorecard(self.st)["overall"]
        self.assertEqual(o["n_closed"], 2)
        self.assertEqual(o["hit_rate"], 0.0, "two stop-outs are not wins")
        self.assertLess(o["expectancy_pct"], 0.0)

    def test_quotes_are_fetched_in_ONE_call(self):
        """A per-name fetch on a 26-row book is 26 round trips, and the chunking that stops a
        wide book silently truncating lives in the broker."""
        q = quoter({"ELV261120C00420000": 20.0, "HCA261016C00430000": 20.0})
        SS.score_open_alerts(self.st, q, today=TODAY)
        self.assertEqual(len(q.calls), 1, q.calls)
        self.assertEqual(sorted(q.calls[0]),
                         ["ELV261120C00420000", "HCA261016C00430000"])

    def test_a_healthy_MARK_still_closes_HCA_on_its_TIME_STOP(self):
        """A FINDING, not a fixture error, and it sharpens the item.

        At a mark of 20.0 neither alert's stop or target fires -- but HCA alert 7's own time
        stop fell on **2026-09-24** (alerted 2026-09-02 at 44 DTE, half the tenor = 22 days) and
        today is 2026-10-03. So HCA was overdue for closure on its own policy EVEN IF THE TRADE
        HAD BEEN FINE. The brief reports it at -62% past its stop; it was also nine days past
        its time stop, and the record showed neither.
        """
        q = quoter({"ELV261120C00420000": 20.0, "HCA261016C00430000": 20.0})
        res = SS.score_open_alerts(self.st, q, today=TODAY)
        self.assertEqual(res["closed"], 1, res)
        self.assertEqual(res["unchanged"], 1)
        # The KMI row is in `exits` too -- with a STATUS and the no-contract reason, not an
        # exit reason -- so filter on the exit itself rather than on "has a reason".
        closes = [e for e in res["exits"] if e.get("status") != SS.NO_CONTRACT]
        self.assertEqual([e["ticker"] for e in closes], ["HCA"])
        self.assertEqual(closes[0]["reason"], "time_stop")

    def test_a_book_inside_every_rule_closes_nothing(self):
        """The real quiet case: a date before any time stop, with healthy marks."""
        q = quoter({"ELV261120C00420000": 20.0, "HCA261016C00430000": 20.0})
        res = SS.score_open_alerts(self.st, q, today=dt.date(2026, 9, 20))
        self.assertEqual(res["closed"], 0, res)
        self.assertEqual(res["unchanged"], 2)

    def test_apply_false_writes_nothing(self):
        """How this is exercised against the live record before it restates a figure."""
        q = quoter({"ELV261120C00420000": 7.00, "HCA261016C00430000": 8.60})
        res = SS.score_open_alerts(self.st, q, today=TODAY, apply=False)
        self.assertEqual(res["closed"], 2, "it must still REPORT what would happen")
        self.assertIs(res["applied"], False)
        self.assertEqual(OT.scorecard(self.st)["n_open"], 3,
                         "a dry run changed the record")
        self.assertEqual(OT.scorecard(self.st)["n_no_contract"], 0)

    def test_the_restatement_is_dated_both_ways(self):
        """`MA36`: a restatement that keeps no record of the figure it replaced is
        indistinguishable from the figure having always been that."""
        q = quoter({"ELV261120C00420000": 7.00, "HCA261016C00430000": 8.60})
        res = SS.score_open_alerts(self.st, q, today=TODAY)
        self.assertIsNotNone(res["expectancy_before"])
        self.assertIsNotNone(res["expectancy_after"])
        self.assertEqual(res["expectancy_before"]["n_closed"], 0)
        self.assertEqual(res["expectancy_after"]["n_closed"], 2)

    def test_a_quiet_run_snapshots_nothing(self):
        """Only paid for when there is something to settle -- so the date has to be one on
        which nothing fires, which (see above) 2026-10-03 is not."""
        q = quoter({"ELV261120C00420000": 20.0, "HCA261016C00430000": 20.0})
        res = SS.score_open_alerts(self.st, q, today=dt.date(2026, 9, 20))
        self.assertEqual(res["closed"], 0)
        self.assertIsNone(res["expectancy_before"])
        self.assertIsNone(res["expectancy_after"])


class TheMissingBidRules(unittest.TestCase):
    """B5-lesser for a LIVE contract, MA36 for a DEAD one. The two are opposite and the
    distinction is STRICTLY `day > expiry`."""

    def test_a_live_contract_with_no_bid_DEFERS(self):
        st = store_with([ELV14])
        res = SS.score_open_alerts(st, quoter({"ELV261120C00420000": None}), today=TODAY)
        self.assertEqual(res["deferred_no_bid"], 1)
        self.assertEqual(res["closed"], 0)
        self.assertEqual(OT.scorecard(st)["n_open"], 1)

    def test_a_contract_PAST_expiry_with_no_bid_SETTLES_AT_ZERO(self):
        """MA36's whole point: a long option that decays to no bid IS the total loss, and
        deferring forever drops the -100% tail while keeping the winners."""
        st = store_with([HCA7])
        res = SS.score_open_alerts(st, quoter({"HCA261016C00430000": None}),
                                   today=dt.date(2026, 10, 20))
        self.assertEqual(res["settled_expired"], 1)
        self.assertEqual(res["closed"], 1)
        self.assertAlmostEqual(row_for(st, "HCA").get("pnl_pct"), -1.0, places=9,
                               msg="a worthless expiry must read exactly -100% (MA36)")

    def test_INSIDE_the_close_window_it_still_defers(self):
        """`_exit_decision` returns 'expiry' from CLOSE_BEFORE_EXPIRY_DAYS out, and the
        contract is ALIVE there -- a missing bid is a thin market, not a settlement."""
        st = store_with([HCA7])
        res = SS.score_open_alerts(st, quoter({"HCA261016C00430000": None}),
                                   today=dt.date(2026, 10, 15))
        self.assertEqual(res["deferred_no_bid"], 1)
        self.assertEqual(res["settled_expired"], 0)

    def test_the_settlement_price_is_never_reconstructed(self):
        """V6-OPT's trap: using today's underlying would book a fake gain on a dead call
        whenever the stock rallied after expiry, and the error runs in the FLATTERING
        direction. Asserted on the source, because the absence of a call is the property."""
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "options_selfscore.py"),
                  encoding="utf-8") as f:
            tree = ast.parse(f.read())
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for banned in ("get_bars", "intrinsic", "underlying_price_now"):
            self.assertNotIn(banned, names,
                             "the self-scorer reaches for %r, which would reconstruct a "
                             "settlement price" % banned)


class ThePaperBookIsASeparateObject(unittest.TestCase):
    """It answers what a $1,000-budget account actually got, fills and sizing included, and is
    the only measurement this project has of real execution."""

    def test_the_selfscorer_writes_to_no_paper_table(self):
        import ast
        with open(os.path.join(REPO, "valuation", "edge", "options_selfscore.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("paper_option_orders", src)
        self.assertNotIn("UPDATE paper", src)
        self.assertNotIn("INSERT INTO paper", src)

    def test_the_only_table_it_updates_is_option_alerts(self):
        import re
        with open(os.path.join(REPO, "valuation", "edge", "options_selfscore.py"),
                  encoding="utf-8") as f:
            src = f.read()
        tables = set(re.findall(r"UPDATE\s+(\w+)", src))
        self.assertEqual(tables, {"option_alerts"}, tables)

    def test_it_calls_no_broker(self):
        """The quote source is INJECTED, so the logic is testable and the live caller chooses."""
        with open(os.path.join(REPO, "valuation", "edge", "options_selfscore.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("PaperBroker(", src)


class TheRetiredReference(unittest.TestCase):
    """`/api/options-paper` headlined +12.88% -- the term filter's figure -- and R7 rejected
    that filter on corrected data."""

    def setUp(self):
        from valuation.edge import options_paper as OP
        self.OP = OP

    def test_the_primary_reference_is_the_corrected_alert_book(self):
        st = store_with([])
        r = self.OP.paper_report(st)
        self.assertAlmostEqual(r["primary_reference"]["value"],
                               self.OP.CORRECTED_ALERT_BOOK_EXPECTANCY, places=9)
        self.assertNotAlmostEqual(r["primary_reference"]["value"],
                                  self.OP.GATED_LATE_HALF_EXPECTANCY, places=4)

    def test_the_rejected_figure_is_KEPT_with_its_verdict(self):
        """Deleted it would be unfindable by a reader who saw it; kept unlabelled it would be
        quoted again. `scream_log`'s principle: nothing removed, everything dated."""
        st = store_with([])
        r = self.OP.paper_report(st)
        rets = {x["value"]: x for x in r["retired_references"]}
        self.assertIn(self.OP.GATED_LATE_HALF_EXPECTANCY, rets)
        row = rets[self.OP.GATED_LATE_HALF_EXPECTANCY]
        self.assertEqual(row["retired_by"], "R7")
        self.assertIn("REJECTED", row["why"])
        self.assertIn("-1.12pp", row["why"])

    def test_the_reference_carries_R2s_negative_result(self):
        """The honest reference carries a negative result, which is why it is the right one."""
        st = store_with([])
        r = self.OP.paper_report(st)
        note = r["primary_reference"]["and_the_part_that_matters"]
        self.assertIn("5.06", note)
        self.assertIn("random entry", note)
        self.assertIn("O11", note)

    def test_the_caveat_no_longer_credits_the_dead_job(self):
        st = store_with([])
        r = self.OP.paper_report(st)
        self.assertNotIn("Robinhood job", r["caveat"])
        self.assertNotIn("external Robinhood", r["caveat"])
        self.assertIn("OWN exit rules", r["caveat"])
        self.assertIn("no_contract", r["caveat"])

    def test_it_says_where_outcomes_come_from_now(self):
        st = store_with([])
        r = self.OP.paper_report(st)
        self.assertIn("self-scored", r["outcome_source"])
        self.assertIn("no longer exists", r["outcome_source"])

    def test_the_headline_is_the_corrected_basis_when_thin(self):
        st = store_with([])
        r = self.OP.paper_report(st)
        self.assertTrue(r["thin"])
        self.assertAlmostEqual(r["headline_expectancy"],
                               self.OP.CORRECTED_ALERT_BOOK_EXPECTANCY, places=9)
        self.assertIn("corrected basis", r["headline_source"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
