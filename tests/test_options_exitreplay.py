"""O1 / O23 — the frozen exit replay, and the audit-B2 regression that this study found.

A SEPARATE FILE ON PURPOSE. `tests/test_edge.py` is edited by every lane; keeping these here
means a parallel session cannot collide with them.

THE FIRST CLASS IS THE IMPORTANT ONE. `options_exitlab.capture_path` was left on the PRE-B2
quote filter when audit B2 moved `options_backtest.simulate_trade` to the loose exit tolerance,
so wide and thin quote days were deleted from every trade's exit path. It went unnoticed because
nothing replayed a POST-B2 book through the exit lab until O1 did. These tests fail on the old
line.
"""
import datetime as dt
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_exitlab as EL          # noqa: E402
from valuation.edge import options_exitreplay as XR       # noqa: E402
from valuation.edge import options_fill as F              # noqa: E402


def _bars(days, px=100.0):
    return {"date": list(days), "close": [px] * len(days), "raw_close": [px] * len(days)}


class _Provider:
    """Minimal `contract_history` provider over an explicit day list."""

    def __init__(self, days):
        self.days = days

    def contract_history(self, ticker, expiry, strike, right, start, end):
        import pandas as pd

        rows = [{"date": d, "bid": b, "ask": a} for d, b, a in self.days
                if start <= d <= end]
        return pd.DataFrame(rows) if rows else None


ENTRY = {"strike": 100.0, "right": "C", "expiration": "2024-03-15",
         "bid": 1.00, "ask": 1.10, "open_interest": 5000, "volume": 500}
E_DATE = dt.date(2024, 1, 15)
EXPIRY = dt.date(2024, 3, 15)


def _capture(days):
    return EL.capture_path(_Provider(days), "TEST", dict(ENTRY), E_DATE,
                           _bars(["2024-01-15", "2024-03-15"]))


class TheExitFilterIsTheOneProductionUses(unittest.TestCase):
    """AUDIT B2. A wide or thin quote is a BAD price, not an ABSENT one."""

    def test_a_wide_spread_day_survives_into_the_exit_path(self):
        # 0.25/0.35 -> mid 0.30, spread 33% > the 25% entry ceiling. The pre-B2 line dropped it,
        # which is precisely the price region where the -50% stop should fire.
        self.assertEqual(F.quote_reject_reason(F.Quote(bid=0.25, ask=0.35),
                                               check_liquidity=False), "wide_spread")
        self.assertIsNone(F.exit_reject_reason(F.Quote(bid=0.25, ask=0.35)))
        p = _capture([(dt.date(2024, 1, 22), 0.25, 0.35)])
        self.assertEqual(len(p["days"]), 1, "a wide-spread day must not vanish from the path")

    def test_a_thin_premium_day_survives_into_the_exit_path(self):
        self.assertEqual(F.quote_reject_reason(F.Quote(bid=0.04, ask=0.05),
                                               check_liquidity=False), "thin_premium")
        p = _capture([(dt.date(2024, 1, 22), 0.04, 0.05)])
        self.assertEqual(len(p["days"]), 1)

    def test_days_that_are_genuinely_unusable_are_still_dropped(self):
        p = _capture([(dt.date(2024, 1, 22), 0.0, 0.0),      # non_positive
                      (dt.date(2024, 1, 23), 0.90, 0.50),    # crossed
                      (dt.date(2024, 1, 24), None, None),    # no_quote
                      (dt.date(2024, 1, 25), 0.60, 0.70)])   # usable
        self.assertEqual([d[0] for d in p["days"]], ["2024-01-25"])

    def test_the_dropped_day_is_what_let_a_loser_ride_past_its_stop(self):
        """The regression in the shape it actually bit: a stop-triggering day on a wide quote.

        Entry fill is 1.10 (full-touch ask). A 0.25/0.35 day marks at 0.25 on the sell side,
        i.e. -77%, well through the -50% stop. Under the pre-B2 filter that day did not exist
        and the trade ran on to a LATER exit -- which is exactly the sign the O1 replay saw on
        the real book (held_days never shorter than the book's, never longer in the fix).
        """
        days = [(dt.date(2024, 1, 22), 0.25, 0.35),
                (dt.date(2024, 2, 20), 0.90, 1.00)]
        t = EL.apply_policy(_capture(days), dict(EL.SHIPPED))
        self.assertEqual(t["exit_reason"], "stop")
        self.assertEqual(t["exit_date"], "2024-01-22")


class TheFrozenProviderServesTheStoreAndNothingElse(unittest.TestCase):
    def setUp(self):
        import pandas as pd
        self.df = pd.DataFrame({
            "symbol": ["TEST"] * 4 + ["OTHR"],
            "expiration": ["2024-03-15"] * 4 + ["2024-03-15"],
            "strike": pd.array([100.0, 100.0, 100.0, 105.0, 100.0], dtype="float32"),
            "right": ["C", "C", "C", "C", "C"],
            "date": ["2024-01-15", "2024-01-16", "2024-01-17", "2024-01-16", "2024-01-16"],
            "bid": [1.0, 1.1, 1.2, 2.0, 3.0], "ask": [1.1, 1.2, 1.3, 2.1, 3.1],
            "volume": [10] * 5, "open_interest": [100] * 5})
        self.ch = XR.FrozenChains(self.df)

    def test_contract_history_is_inclusive_of_both_endpoints(self):
        h = self.ch.contract_history("TEST", "2024-03-15", 100.0, "C",
                                     "2024-01-15", "2024-01-16")
        self.assertEqual(len(h), 2)

    def test_it_does_not_leak_another_symbol_or_another_strike(self):
        h = self.ch.contract_history("TEST", "2024-03-15", 100.0, "C",
                                     "2024-01-01", "2024-12-31")
        self.assertEqual(len(h), 3)

    def test_a_contract_absent_from_the_freeze_returns_none_rather_than_falling_back(self):
        """No live-store fallback, deliberately: a fallback would make the freeze unfalsifiable
        because every replay would succeed whether or not the copy was sufficient."""
        self.assertIsNone(self.ch.contract_history("NOPE", "2024-03-15", 100.0, "C",
                                                   "2024-01-01", "2024-12-31"))

    def test_float32_strike_noise_does_not_lose_a_contract(self):
        """The store keeps `strike` as float32; 100.0 can read back as 100.00000762939453.
        Keying on the raw float64 cast silently dropped 14 of 3,885 contracts before this."""
        import pandas as pd
        d = self.df.copy()
        d["strike"] = pd.array([100.00000762939453] * 3 + [105.0, 100.0], dtype="float64")
        ch = XR.FrozenChains(d)
        self.assertIsNotNone(ch.contract_history("TEST", "2024-03-15", 100.0, "C",
                                                 "2024-01-01", "2024-12-31"))

    def test_quote_on_returns_the_alert_day_quote(self):
        q = self.ch.quote_on("TEST", "2024-03-15", 100.0, "C", "2024-01-16")
        self.assertAlmostEqual(q["bid"], 1.1, places=5)
        self.assertIsNone(self.ch.quote_on("TEST", "2024-03-15", 100.0, "C", "2024-01-18"))


class TheFourWayPatternLabelIsTheRegistersOwn(unittest.TestCase):
    """The brief required which pattern counts as which to be fixed before the run."""

    @staticmethod
    def _res(sig, rnd, bar=True):
        return {"gate": {"p": {"beats_shipped_on_signal_by_bar": sig,
                               "beats_shipped_on_random": rnd,
                               "X1_adopt": bool(sig and rnd and bar)}}}

    def test_both_sets_is_an_exit_effect(self):
        self.assertEqual(XR.pattern_labels(self._res(True, True))["p"]["label"], "EXIT EFFECT")

    def test_signal_only_is_entry_information_leaking_through_the_exit(self):
        self.assertEqual(XR.pattern_labels(self._res(True, False))["p"]["label"], "SIGNAL-ONLY")

    def test_random_only_is_control_only_and_is_never_adopt_eligible(self):
        got = XR.pattern_labels(self._res(False, True))["p"]
        self.assertEqual(got["label"], "CONTROL-ONLY")
        self.assertFalse(got["adopt_eligible"])

    def test_neither_is_reject(self):
        self.assertEqual(XR.pattern_labels(self._res(False, False))["p"]["label"], "REJECT")


class TheO23VerdictRuleIsMechanical(unittest.TestCase):
    def test_high_r2_with_a_high_lower_bound_is_underlying_driven(self):
        v = XR.o23_verdict({"r2": 0.72}, {"lo": 0.61, "hi": 0.80})
        self.assertEqual(v["label"], "UNDERLYING-DRIVEN")

    def test_low_r2_with_a_low_upper_bound_is_option_driven(self):
        v = XR.o23_verdict({"r2": 0.10}, {"lo": 0.04, "hi": 0.19})
        self.assertEqual(v["label"], "OPTION-DRIVEN")

    def test_a_point_estimate_that_clears_on_a_straddling_interval_is_a_null(self):
        """A near-miss is a NULL, not a 'nearly'."""
        self.assertEqual(XR.o23_verdict({"r2": 0.55}, {"lo": 0.41, "hi": 0.68})["label"], "NULL")
        self.assertEqual(XR.o23_verdict({"r2": 0.24}, {"lo": 0.11, "hi": 0.33})["label"], "NULL")

    def test_a_missing_fit_is_a_null_rather_than_an_exception(self):
        self.assertEqual(XR.o23_verdict(None, None)["label"], "NULL")


class TheDecompositionArithmeticIsRight(unittest.TestCase):
    def test_ols_recovers_a_known_line_exactly(self):
        xs = [0.0, 1.0, 2.0, 3.0]
        fit = XR._ols_r2(xs, [1.0 + 2.0 * x for x in xs])
        self.assertAlmostEqual(fit["slope"], 2.0, places=9)
        self.assertAlmostEqual(fit["intercept"], 1.0, places=9)
        self.assertAlmostEqual(fit["r2"], 1.0, places=9)

    def test_a_constant_series_has_no_r2_rather_than_a_divide_by_zero(self):
        self.assertIsNone(XR._ols_r2([1.0, 1.0, 1.0], [2.0, 3.0, 4.0]))
        self.assertIsNone(XR._ols_r2([1.0, 2.0, 3.0], [5.0, 5.0, 5.0]))

    def test_the_underlying_close_is_as_traded_and_never_looks_forward(self):
        b = {"date": ["2024-01-15", "2024-01-16", "2024-01-17"],
             "close": [1.0, 2.0, 3.0], "raw_close": [10.0, 20.0, 30.0]}
        self.assertEqual(XR._und_close(b, "2024-01-16"), 20.0)
        self.assertEqual(XR._und_close(b, "2024-01-16"), 20.0)
        self.assertEqual(XR._und_close(b, "2024-01-14"), None)
        self.assertEqual(XR._und_close(b, "2024-06-01"), 30.0)


class TheBarsStampRecordsTheGapItCannotClose(unittest.TestCase):
    """The options freeze does NOT cover the underlying bars cache and O23 depends on it."""

    def test_a_missing_bars_file_is_recorded_as_absent_not_skipped(self):
        got = XR.stamp_bars(["__DEFINITELY_NOT_A_TICKER__"])
        self.assertEqual(got["__DEFINITELY_NOT_A_TICKER__"], {"present": False})

    def test_a_present_file_carries_a_digest(self):
        import pickle
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "XYZ.pkl"), "wb") as f:
                pickle.dump({"date": [], "close": []}, f)
            got = XR.stamp_bars(["xyz"], root=d)["XYZ"]
        self.assertTrue(got["present"])
        self.assertEqual(len(got["sha256"]), 64)


if __name__ == "__main__":
    unittest.main(verbosity=2)
