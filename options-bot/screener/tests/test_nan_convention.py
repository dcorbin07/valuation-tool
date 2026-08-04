"""
C1 — pandas turns None into NaN, and the live scorer's whole missing-data
convention tests `is None`.

`pit_data` correctly returns None for a missing input. The moment those values
pass through a DataFrame, pandas stores them as float NaN, and
`to_dict("records")` hands NaN back. Every branch in `scoring.py` asks
`is None`, so a NaN sails through as PRESENT and poisons whatever it touches.

This is the same defect class the project has now hit five times — the loader
allowlist, the SF3 positional arg, the five empty factors, `invcap`/`taxexp`/
`ebt`, and `_f()` returning NaN instead of None so `_f_score` counted MISSING
tests as FAILED ones. It is silent every time.

    cd screener && python -m unittest tests.test_nan_convention -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

import scoring as S
import run_backtest as R

NAN = float("nan")


class NaNPoisonsTheScorer(unittest.TestCase):
    """Characterisation: what NaN does if it reaches `scoring.py` unconverted."""

    def test_nan_input_makes_a_whole_subscore_nan(self):
        good = S.quality_score(0.20, 0.15, 1.0)
        self.assertIsNotNone(good)
        poisoned = S.quality_score(NAN, 0.15, 1.0)
        self.assertTrue(poisoned != poisoned,
                        "a NaN op_margin should poison quality_score — if this "
                        "ever stops being true, _denan may no longer be needed")

    def test_none_input_renormalizes_instead(self):
        """The behaviour NaN was stealing: drop the input, reweight the rest."""
        v = S.quality_score(None, 0.15, 1.0)
        self.assertIsNotNone(v)
        self.assertFalse(v != v)

    def test_nan_profitability_is_silently_bucketed_speculative(self):
        """
        The nastiest consequence. `classify_bucket` returns None for genuinely
        unknown profitability — its docstring says mapping a parser gap to
        "speculative" turns a data problem into a strategy decision. NaN defeats
        that: `nan is not None` is True and `nan > 0` is False, so the name is
        scored against loss-making growth companies on a different factor set.
        """
        self.assertIsNone(S.classify_bucket({"operating_income": None,
                                             "net_income": None}))
        self.assertEqual(S.classify_bucket({"operating_income": NAN,
                                            "net_income": NAN}), "speculative")


class DenanRestoresTheConvention(unittest.TestCase):
    def test_nan_becomes_none(self):
        out = R._denan({"a": NAN, "b": 1.5, "c": None, "d": "text"})
        self.assertIsNone(out["a"])
        self.assertEqual(out["b"], 1.5)
        self.assertIsNone(out["c"])
        self.assertEqual(out["d"], "text")

    def test_numpy_nan_too(self):
        self.assertIsNone(R._denan({"a": np.float64("nan")})["a"])

    def test_zero_and_false_survive(self):
        """0.0 is a real observation. Anything that collapses it to None would
        silently delete every genuinely-zero input."""
        out = R._denan({"z": 0.0, "f": False, "n": 0})
        self.assertEqual(out["z"], 0.0)
        self.assertIs(out["f"], False)
        self.assertEqual(out["n"], 0)

    # A one-row frame with a bare None keeps dtype=object and the None survives.
    # The coercion needs the column to infer NUMERIC, i.e. at least one real
    # float alongside the None — which is exactly what a real panel looks like:
    # most names have an op_margin, some do not. Hence two rows.
    _MIXED = [{"op_margin": 0.11, "roe": 0.20, "net_debt_to_ebitda": 2.0},
              {"op_margin": None, "roe": 0.15, "net_debt_to_ebitda": 1.0}]

    def test_a_dataframe_round_trip_is_repaired(self):
        """The actual path: None -> DataFrame -> to_dict -> NaN -> _denan."""
        raw = pd.DataFrame(self._MIXED).to_dict("records")[1]
        self.assertTrue(raw["op_margin"] != raw["op_margin"],
                        "precondition: pandas turned the None into NaN")
        self.assertIsNone(R._denan(raw)["op_margin"])

    def test_the_repaired_row_scores_where_the_raw_one_does_not(self):
        raw = pd.DataFrame(self._MIXED).to_dict("records")[1]
        poisoned = S.quality_score(raw["op_margin"], raw["roe"],
                                   raw["net_debt_to_ebitda"])
        self.assertTrue(poisoned != poisoned)
        fixed_row = R._denan(raw)
        fixed = S.quality_score(fixed_row["op_margin"], fixed_row["roe"],
                                fixed_row["net_debt_to_ebitda"])
        self.assertIsNotNone(fixed)
        self.assertFalse(fixed != fixed)


class EveryUnscoredRowIsAccountedFor(unittest.TestCase):
    """
    The property that made the bug findable, and the one worth keeping: the
    number of rows the live model does not score must equal the number of skips
    it REPORTS. Before the fix, a 60-name slice left 89 rows unscored while the
    tally saw 19 — the other 70 vanished into NaN with no reason recorded.
    """

    def _panel(self):
        rows = []
        for i in range(40):
            rows.append({
                "date": pd.Timestamp("2023-01-03"), "ticker": f"T{i:02d}",
                "sector": "Widgets", "price": 25.0,
                "avg_dollar_volume": 5e6, "market_cap": 1e9,
                "revenue": 1000.0 + i,
                "net_income": (None if i % 7 == 0 else 50.0 + i),
                "operating_income": (None if i % 5 == 0 else 80.0 + i),
                "total_debt": 100.0, "cash": 40.0,
                "op_margin": (None if i % 3 == 0 else 0.08 + i / 1000),
                "roe": 0.10 + i / 500, "net_debt_to_ebitda": 1.5,
                "latest_rev_growth": 0.12, "prior_rev_growth": 0.09,
                "ret_12_1": 0.05 + i / 200, "is_common_equity": True,
                "fwd_ret": 0.01, "bench_ret": 0.005,
            })
        return pd.DataFrame(rows)

    def test_unscored_count_equals_reported_skip_count(self):
        panel = self._panel()
        scored, skips = R.score_live(panel, with_insider=False)
        unscored = int(scored["composite_live"].isna().sum())
        self.assertEqual(unscored, sum(skips.values()),
                         f"{unscored} rows unscored but only "
                         f"{sum(skips.values())} skips reported — rows are "
                         f"disappearing without a recorded reason")

    def test_missing_one_input_does_not_delete_the_name(self):
        """A name missing only op_margin must still score, renormalized."""
        panel = self._panel()
        scored, _ = R.score_live(panel, with_insider=False)
        row = scored[scored["ticker"] == "T03"]        # i=3: op_margin is None
        self.assertEqual(len(row), 1)
        self.assertFalse(pd.isna(row["composite_live"].iloc[0]),
                         "a single missing input deleted the name instead of "
                         "renormalizing the remaining weights")


if __name__ == "__main__":
    unittest.main()
