"""The path study — the invariants that must not drift (audit: options bot, 2026-08-10).

    python tests/test_path_study.py

The study's headline numbers are reproduced by the scripts against a 22 MB frozen chain file
that CI does not have, so this suite pins the parts that can be pinned without it: the algebra,
the arm set against its own pre-registration, the exit logic on synthetic paths, and the bar.

THE MOST IMPORTANT TEST HERE IS `TheBarIsO1sNotANewOne`. The whole verdict is "the largest gain
is +3.60pp against a 10pp bar"; if someone later lowers the bar, that sentence silently becomes
an adoption.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts import path_arms as PA          # noqa: E402
from scripts import path_gate as PG          # noqa: E402
from valuation.edge import options_exitlab as XL   # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _day(d, ret, entry_fill=1.0, S=None, delta=None, iv=None, gap=None, iv_drop=None,
         extr=None):
    """One synthetic day-state. `ret` is what the arm reads; bid/ask are made consistent."""
    mark = entry_fill * (1.0 + ret)
    return {"d": d, "bid": mark, "ask": mark * 1.02, "mark": mark, "ret": ret,
            "S": S, "extr_frac": extr, "iv": iv, "delta": delta, "gap": gap,
            "iv_drop": iv_drop}


def _row(dte0=60, entry="2023-01-02", premium=1.0):
    import datetime as dt
    exp = (dt.date.fromisoformat(entry) + dt.timedelta(days=dte0)).isoformat()
    return {"ticker": "TEST", "alert_ts": entry, "expiry": exp, "strike": 100.0,
            "opt_right": "call", "entry_premium": premium, "entry_spread_pct": 0.02,
            "_entry_oi": 5000, "_entry_volume": 500, "pnl_pct": None, "exit_reason": None,
            "held_days": 0}


class TheEntryQuoteReconstructionIsAlgebraNotAnApproximation(unittest.TestCase):
    """The book stores the fill and the spread, never both sides. Checked in the study against
    the 1,099 trades that also carry a true `entry_bid`: max abs error 0.000000000."""

    def test_it_inverts_the_spread_definition_exactly(self):
        for ask in (0.35, 1.0, 5.1, 42.75):
            for s in (0.005, 0.02, 0.0985, 0.25):
                r = {"entry_premium": ask, "entry_spread_pct": s}
                q = PA.entry_quote(r)
                mid = (q.bid + q.ask) / 2.0
                self.assertAlmostEqual((q.ask - q.bid) / mid, s, places=12)
                self.assertAlmostEqual(q.ask, ask, places=12)

    def test_a_zero_spread_gives_bid_equal_ask(self):
        q = PA.entry_quote({"entry_premium": 2.0, "entry_spread_pct": 0.0})
        self.assertAlmostEqual(q.bid, q.ask, places=12)

    def test_liquidity_is_read_not_invented(self):
        """`round_trip` screens the entry quote, so a fabricated oi/volume would decide which
        trades are scoreable at all."""
        q = PA.entry_quote({"entry_premium": 2.0, "entry_spread_pct": 0.02,
                            "_entry_oi": 1234, "_entry_volume": 99})
        self.assertEqual(q.oi, 1234)
        self.assertEqual(q.volume, 99)


class TheArmSetIsExactlyThePreRegisteredOne(unittest.TestCase):

    def test_thirteen_arms_plus_the_baseline(self):
        self.assertEqual(len(PA.ARMS) - 1, 13, sorted(PA.ARMS))
        self.assertIn("shipped", PA.ARMS)

    def test_the_shipped_arm_is_the_inherited_policy(self):
        self.assertEqual(PA.ARMS["shipped"], {"tp": 1.0, "sl": -0.5, "time_frac": 0.5})

    def test_no_arm_re_runs_a_policy_O1_already_rejected(self):
        """The register's own promise. O1's grid is imported rather than retyped, so this
        cannot pass by someone copying a stale list into the test."""
        o1 = dict(XL.POLICIES)               # a tuple of (name, params) pairs
        self.assertGreaterEqual(len(o1), 20, "O1's grid shrank; the diff would be vacuous")
        for name, arm in PA.ARMS.items():
            if name == "shipped":
                continue
            for oname, op in o1.items():
                self.assertNotEqual({k: v for k, v in arm.items() if v is not None},
                                    {k: v for k, v in op.items() if v is not None},
                                    "%s duplicates O1's %s" % (name, oname))

    def test_every_arm_has_a_family(self):
        for name in PA.ARMS:
            if name != "shipped":
                self.assertIn(name, PA.FAMILY, name)
        self.assertEqual(set(PA.FAMILY.values()), set("ABCDEF"))


class TheShippedArmFiresTheInheritedLevels(unittest.TestCase):

    def test_the_target_fires_at_plus_one_hundred(self):
        r = _row()
        days = [_day("2023-01-03", 0.4), _day("2023-01-04", 1.05)]
        got = PA.apply_arm(r, days, PA.ARMS["shipped"])
        self.assertEqual(got["exit_reason"], "target")
        self.assertEqual(got["exit_date"], "2023-01-04")

    def test_the_stop_fires_at_minus_fifty(self):
        r = _row()
        days = [_day("2023-01-03", -0.2), _day("2023-01-04", -0.55)]
        self.assertEqual(PA.apply_arm(r, days, PA.ARMS["shipped"])["exit_reason"], "stop")

    def test_the_time_stop_fires_at_half_dte(self):
        r = _row(dte0=60)
        days = [_day("2023-01-10", 0.1), _day("2023-02-05", 0.2)]   # 2023-02-01 is half
        got = PA.apply_arm(r, days, PA.ARMS["shipped"])
        self.assertEqual(got["exit_reason"], "time_stop")

    def test_a_target_beats_a_stop_on_the_same_day(self):
        """Ordering is inherited from `options_exitlab.apply_policy` and must not drift."""
        r = _row()
        days = [_day("2023-01-03", 1.2)]
        self.assertEqual(PA.apply_arm(r, days, PA.ARMS["shipped"])["exit_reason"], "target")


class TheTwoRatchetArmsAreTheSameArm(unittest.TestCase):
    """A finding, pinned: with a +50% step the first ratchet lands exactly at breakeven and the
    +100% target closes the trade before a second step can arm, so `be50` and `step50` are one
    arm. They were still charged as two, because two were pre-registered."""

    def test_they_exit_identically_on_a_path_that_peaks_between_50_and_100(self):
        r = _row()
        days = [_day("2023-01-03", 0.6), _day("2023-01-04", 0.7), _day("2023-01-05", -0.05)]
        a = PA.apply_arm(r, days, PA.ARMS["be50"])
        b = PA.apply_arm(r, days, PA.ARMS["step50"])
        self.assertEqual(a["exit_reason"], b["exit_reason"])
        self.assertEqual(a["exit_date"], b["exit_date"])
        self.assertAlmostEqual(a["pnl_pct"], b["pnl_pct"], places=12)

    def test_the_ratchet_actually_fires_rather_than_the_arm_being_inert(self):
        r = _row()
        days = [_day("2023-01-03", 0.6), _day("2023-01-05", -0.05)]
        self.assertEqual(PA.apply_arm(r, days, PA.ARMS["be50"])["exit_reason"], "ratchet")


class TheConditionalTimeStopHoldsAWinnerAndClosesALaggard(unittest.TestCase):

    def test_it_closes_below_the_threshold(self):
        r = _row(dte0=60)
        days = [_day("2023-02-05", 0.10)]
        self.assertEqual(PA.apply_arm(r, days, PA.ARMS["time_cond25"])["exit_reason"],
                         "time_stop")

    def test_it_holds_above_the_threshold(self):
        r = _row(dte0=60)
        days = [_day("2023-02-05", 0.40), _day("2023-02-20", 1.1)]
        got = PA.apply_arm(r, days, PA.ARMS["time_cond25"])
        self.assertEqual(got["exit_reason"], "target",
                         "the conditional time stop closed a trade it was meant to hold")


class TheBarIsO1sNotANewOne(unittest.TestCase):
    """If this ever fails, the study's verdict sentence has silently changed meaning."""

    def test_the_gate_uses_o1s_pre_committed_expectancy_bar(self):
        self.assertEqual(PG.MIN_EXPECTANCY_GAIN, XL.MIN_EXPECTANCY_GAIN)
        self.assertEqual(PG.MIN_EXPECTANCY_GAIN, 0.10)

    def test_the_bar_is_a_ten_point_gain_not_a_ten_percent_one(self):
        """3.60pp is the study's best arm. It must not accidentally clear a 0.1% bar."""
        self.assertGreater(PG.MIN_EXPECTANCY_GAIN, 0.036)


class TheWallMeasuresOnTheHalfItDidNotSelectOn(unittest.TestCase):

    def test_paired_gain_matches_only_shared_trades(self):
        arm = [{"i": 1, "pnl_pct": 0.5, "alert_ts": "2020-01-01"},
               {"i": 2, "pnl_pct": 0.1, "alert_ts": "2022-01-01"}]
        base = [{"i": 1, "pnl_pct": 0.2, "alert_ts": "2020-01-01"}]
        g, n = PG.paired_gain(arm, base)
        self.assertEqual(n, 1)
        self.assertAlmostEqual(g, 0.3, places=12)

    def test_the_halves_are_disjoint_and_exhaustive(self):
        rows = [{"alert_ts": "20%02d-01-01" % i, "i": i, "pnl_pct": 0.0} for i in range(10, 20)]
        cut = PG.split_date(rows)
        early = PG.half(rows, cut, "early")
        late = PG.half(rows, cut, "late")
        self.assertEqual(len(early) + len(late), len(rows))
        self.assertEqual(set(r["i"] for r in early) & set(r["i"] for r in late), set())

    def test_benjamini_hochberg_is_monotone_and_rejects_nothing_when_all_are_null(self):
        self.assertEqual(set(PG.bh({"a": 0.5, "b": 0.6, "c": 0.9}, 0.1).values()), {False})
        got = PG.bh({"a": 0.001, "b": 0.5, "c": 0.9}, 0.1)
        self.assertTrue(got["a"])
        self.assertFalse(got["b"])


class TheStudySaysWhatItIsNot(unittest.TestCase):
    """The dead-entry caveat is load-bearing and lives in the code, not only the write-up."""

    def test_the_modules_carry_the_dead_entry_caveat(self):
        for mod in (PA, PG):
            src = open(mod.__file__, encoding="utf-8").read()
            self.assertIn("R2", src, mod.__name__)
        self.assertIn("entry", PA.__doc__.lower())
        self.assertIn("dead", PA.__doc__.lower())

    def test_the_pre_registration_exists_and_fixes_the_arms_before_the_tables(self):
        p = os.path.join(REPO, "PREREG_path_study.md")
        self.assertTrue(os.path.exists(p))
        txt = open(p, encoding="utf-8").read()
        for name in PA.ARMS:
            if name != "shipped":
                self.assertIn(name, txt, "%s is not in the pre-registration" % name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
