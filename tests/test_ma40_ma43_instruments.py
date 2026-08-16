"""MA40 + MA41 + MA42 + MA43 + MA47 — five inference/reporting instruments, pinned.

Run: python tests/test_ma40_ma43_instruments.py

WHAT THESE FIVE HAVE IN COMMON. Each is a defect that produces a PLAUSIBLE NUMBER rather than
an error, which is why every one of them survived in the tree with a passing suite:

  * MA40 — two whole result blocks computed every run and dropped on the way to the file. The
    only symptom was their absence from a 1,200-leaf JSON nobody diffs by hand.
  * MA41 — an out-of-sample IC inflated by fold-adjacent leakage. It is a perfectly ordinary
    number; it is just too high.
  * MA42 — a status frozen at "0 complete paired month(s)" forever. It reads exactly like a
    pair that has not accrued yet.
  * MA43 — a paired difference computed against the wrong quarters. With equal-length series
    there is NO symptom at all.
  * MA47 — a panel cache that reuses a DIFFERENT universe's panel because the key stored a
    ticker COUNT rather than a ticker identity. The panel loads fine.

EVERY FIXTURE HERE FAILS AGAINST THE PRE-FIX TREE. That is the M3 standard, and it is not a
claim made from reading the diff: the pre-fix behaviour is RECONSTRUCTED in the test itself
(positional pairing, `embargo=0`, a projection with the fields removed) and asserted to give a
different, wrong answer. A fixture that cannot demonstrate the defect proves nothing about the
fix.
"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import ablation as AB                    # noqa: E402
from valuation.edge import payload_schema as PS              # noqa: E402
from valuation.edge import results_file as RF                # noqa: E402
from valuation.edge import shadow_vintage as SV              # noqa: E402
from valuation.edge import walkforward as WF                 # noqa: E402
from valuation.studies import param_search as PSRCH          # noqa: E402


# ---------------------------------------------------------------------------
# MA43 — paired_diff must key on dates, not positions
# ---------------------------------------------------------------------------

def _series(n=24, seed=0):
    rng = np.random.default_rng(seed)
    dates = ["2010-%02d-15" % (i + 1) if i < 12 else "2011-%02d-15" % (i - 11)
             for i in range(n)]
    return dates, list(rng.normal(0.02, 0.05, n)), list(rng.normal(0.01, 0.05, n))


class TestMA43PairedDiffAlignment(unittest.TestCase):

    def test_equal_length_different_dates_is_the_no_symptom_case(self):
        """THE DEFECT. Both arms 23 long, each missing a DIFFERENT date. Positional pairing
        truncates nothing, raises nothing, and pairs most elements against the wrong quarter."""
        dates, a, b = _series(24, seed=0)
        da = dates[:5] + dates[6:]          # 23, missing index 5
        db = dates[:15] + dates[16:]        # 23, missing index 15
        aa, bb = a[:23], b[:23]
        self.assertEqual(len(da), len(db))
        self.assertEqual(len(aa), len(bb))

        positional = AB.paired_diff(aa, bb, draws=400)                       # pre-fix behaviour
        keyed = AB.paired_diff(aa, bb, draws=400, dates_a=da, dates_b=db)    # post-fix

        self.assertTrue(positional["ok"] and keyed["ok"])
        self.assertEqual(positional["alignment"], "positional-equal-length")
        self.assertEqual(keyed["alignment"], "dates")
        # The whole point: the two answers differ, and only one of them is the paired
        # difference the docstring promises.
        self.assertNotAlmostEqual(positional["mean_diff_ann"], keyed["mean_diff_ann"], places=6)
        self.assertEqual(keyed["n_shared"], 22)
        self.assertEqual(keyed["n_dropped_a"], 1)
        self.assertEqual(keyed["n_dropped_b"], 1)

    def test_unequal_lengths_now_refuse_instead_of_truncating(self):
        """Pre-fix this SILENTLY truncated to the shorter series. Refusing is the safe
        direction: which periods correspond is exactly what this function cannot guess."""
        dates, a, b = _series(24, seed=1)
        r = AB.paired_diff(a, b[:18], draws=50)
        self.assertFalse(r["ok"])
        self.assertIn("refusing to truncate", r["reason"])

    def test_duplicate_dates_are_refused(self):
        """A repeat would silently keep the LAST occurrence — the same quiet guess again.
        Found while writing the first fixture above, whose dates repeated by accident."""
        dates, a, b = _series(24, seed=2)
        r = AB.paired_diff(a, b, draws=50, dates_a=["2010-01-15"] * 24, dates_b=dates)
        self.assertFalse(r["ok"])
        self.assertIn("duplicate dates", r["reason"])

    def test_identical_dates_reproduce_the_positional_answer_exactly(self):
        """The fix must be INERT when the inputs were already aligned, or it silently restates
        every result the function has ever produced."""
        dates, a, b = _series(24, seed=3)
        pos = AB.paired_diff(a, b, draws=600, seed=7)
        keyed = AB.paired_diff(a, b, draws=600, seed=7, dates_a=dates, dates_b=dates)
        self.assertAlmostEqual(pos["mean_diff_ann"], keyed["mean_diff_ann"], places=12)
        self.assertEqual(pos["n_periods"], keyed["n_periods"])


# ---------------------------------------------------------------------------
# MA41 — walk_forward must embargo the fold boundary
# ---------------------------------------------------------------------------

class TestMA41WalkForwardEmbargo(unittest.TestCase):

    def _panel(self, n_dates=48, n_names=60, seed=5):
        rng = np.random.default_rng(seed)
        rows = []
        for di in range(n_dates):
            for ni in range(n_names):
                f1 = rng.normal()
                rows.append({"date": "d%03d" % di, "ticker": "T%03d" % ni,
                             "f1": f1, "f2": rng.normal(), "f3": rng.normal(),
                             "fwd_ret": 0.02 * f1 + rng.normal(0, 0.05)})
        import pandas as pd
        return pd.DataFrame(rows)

    def test_the_training_set_no_longer_touches_the_test_fold(self):
        """THE STRUCTURAL ASSERTION, and it fails against the pre-fix tree by construction.

        Pinned by capturing the dates `_ic_for` is actually handed, rather than by comparing
        two ICs — an IC comparison depends on the fixture's noise and can pass by luck, while
        "the last training date is adjacent to the first test date" is exactly the defect.
        """
        seen = []
        real = WF._ic_for

        def spy(df, w, cols, ret_col, date_col):
            seen.append(sorted(df[date_col].unique()))
            return real(df, w, cols, ret_col, date_col)

        panel = self._panel()
        n_all = panel["date"].nunique()

        WF._ic_for = spy
        try:
            WF.walk_forward(panel, ["f1", "f2", "f3"], n_folds=3, step_grid=0.5, embargo=1)
            embargoed = [s for s in seen]
            seen.clear()
            WF.walk_forward(panel, ["f1", "f2", "f3"], n_folds=3, step_grid=0.5, embargo=0)
            plain = [s for s in seen]
        finally:
            WF._ic_for = real

        # `_ic_for` is called on TEST folds and on the final "refit on ALL data" pass too, so
        # the captures must be filtered before anything is asserted — found by this test
        # failing twice, first on the full-panel refit (the max in both arms) and then on a
        # test fold that ends at the calendar's end. Training sets are ANCHORED: every one is
        # `folds[:k]`, so it starts at the first date and is shorter than the whole panel.
        all_dates = sorted(panel["date"].unique())
        first = all_dates[0]

        def trains(seq):
            return [s for s in seq if len(s) < n_all and s and s[0] == first]

        e_tr, p_tr = trains(embargoed), trains(plain)
        self.assertTrue(e_tr and p_tr, "no training sets captured — the spy is not working")
        self.assertEqual(max(len(s) for s in p_tr) - max(len(s) for s in e_tr), 1,
                         "embargo=1 must drop exactly one training date")

        # AND THE DEFECT ITSELF. Pre-fix, every training set ran right up to the date before
        # its test fold. Post-fix there is a one-date gap, so the date immediately after the
        # last training date is NOT the first test date.
        for s in e_tr:
            gap_date = all_dates[all_dates.index(s[-1]) + 1]
            self.assertNotIn(gap_date, s, "the embargoed date must not be in the training set")
        for s in p_tr:
            # the un-embargoed arm is the pre-fix behaviour: training runs to the boundary
            self.assertEqual(len(s), all_dates.index(s[-1]) + 1)

    def test_the_embargo_is_reported_and_defaults_on(self):
        r = WF.walk_forward(self._panel(), ["f1", "f2", "f3"], n_folds=3, step_grid=0.5)
        self.assertEqual(r["embargo"], 1, "the embargo must be ON by default")
        self.assertGreater(r["embargoed_train_dates"], 0)
        self.assertIn("margin_se", r)
        self.assertIn("REPORTED ONLY", r["verdict"])

    def test_the_margin_is_reported_and_carries_no_calibrated_floor(self):
        """The adopt boolean is deliberately unchanged; inventing a threshold here would be
        an uncalibrated bar, which is the error this project's record warns about most."""
        r = WF.walk_forward(self._panel(), ["f1", "f2", "f3"], n_folds=3, step_grid=0.5)
        self.assertIn("no calibrated floor", r["margin_note"])
        self.assertEqual(r["adopt"],
                         bool(r["walk_oos_ic_optimized"] == r["walk_oos_ic_optimized"]
                              and r["walk_oos_ic_optimized"] > 0
                              and r["walk_oos_ic_optimized"] > r["walk_oos_ic_baseline"]))

    def test_walkforward_is_no_longer_the_only_splitter_without_an_embargo(self):
        """The audit's own measurement was `grep -c embargo` -> 0. It must never read 0 again."""
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "valuation", "edge", "walkforward.py"),
                   encoding="utf-8").read()
        self.assertGreater(src.count("embargo"), 5)


# ---------------------------------------------------------------------------
# MA42 — shadow_vintage.detail() must not read a key nothing writes
# ---------------------------------------------------------------------------

class TestMA42ShadowMonths(unittest.TestCase):

    def test_months_paired_is_computed_not_read_from_an_unset_key(self):
        d = SV.detail()
        if not d.get("active"):
            self.skipTest("no vintage pair open")
        for k in ("months_elapsed", "months_paired", "paired_months_owed",
                  "paired_series_source"):
            self.assertIn(k, d, "%s must be reported" % k)

    def test_the_month_counter_actually_advances(self):
        """PRE-FIX THIS WAS THE DEFECT: 0 forever, so the verdict branch was unreachable.
        A counter that cannot move is what made the status vacuously stuck."""
        import datetime as dt
        o = dt.date(2026, 8, 13)
        self.assertEqual(SV._complete_months_since(o, dt.date(2026, 8, 15)), 0)
        self.assertEqual(SV._complete_months_since(o, dt.date(2026, 9, 12)), 0)
        self.assertEqual(SV._complete_months_since(o, dt.date(2026, 9, 13)), 1)
        self.assertEqual(SV._complete_months_since(o, dt.date(2027, 2, 13)), 6)
        self.assertEqual(SV._complete_months_since(o, dt.date(2031, 8, 13)), 60)

    def test_a_partial_month_is_not_counted(self):
        """Counting a part-month would inflate the denominator of a five-year clock."""
        import datetime as dt
        o = dt.date(2026, 1, 31)
        self.assertEqual(SV._complete_months_since(o, dt.date(2026, 2, 28)), 0)

    def test_the_zero_is_attributable_rather_than_bare(self):
        """`months_paired` is still 0 today, and for a stated reason: nothing writes a shadow
        series. A bare 0 is indistinguishable from the bug this item fixed."""
        d = SV.detail()
        if not d.get("active"):
            self.skipTest("no vintage pair open")
        self.assertEqual(d["months_paired"], 0)
        self.assertIn("no module in this repository writes", d["paired_series_source"])


# ---------------------------------------------------------------------------
# MA40 — sector_caps and the walk_forward param sweep must reach the file
# ---------------------------------------------------------------------------

_WF_RES = {
    "walk_forward": {
        "n_folds": 5, "param_folds": 4,
        "weights": {"candidates": [], "adaptive_oos_ic": 0.05,
                    "recommend": "current-default", "adopt": False,
                    "verdict": "keep", "recommended_weights_cols": {}},
        "params": {"top_n": {"adopt": False, "oos_median": 0.011}},
    },
    "sector_caps": {"note": "measured, NOT adopted; risk intervention (audit B21)",
                    "caps": {"none": {"net_alpha": 0.061}, "0.30": {"net_alpha": 0.058}}},
}


class TestMA40BlocksReachTheFile(unittest.TestCase):

    def test_both_blocks_are_projected(self):
        p = RF.build_payload(_WF_RES)
        self.assertEqual(p["sector_caps"], _WF_RES["sector_caps"])
        self.assertEqual(p["walk_forward"]["params"], _WF_RES["walk_forward"]["params"])
        self.assertEqual(p["walk_forward"]["param_folds"], 4)

    def test_the_guard_catches_the_pre_fix_projection(self):
        """KNOWN-BAD FIXTURE. Reconstruct exactly what `build_payload` used to emit and assert
        the field-level guard reports all four dropped fields. If this ever returns empty, the
        guard has stopped watching these blocks and MA40 has silently regressed."""
        p = RF.build_payload(_WF_RES)
        pre = dict(p)
        wf = dict(pre["walk_forward"])
        wf.pop("params"); wf.pop("param_folds")
        pre["walk_forward"] = wf
        pre.pop("sector_caps")
        found = {(f["block"], f["field"]) for f in PS.check_payload(_WF_RES, pre)}
        self.assertEqual(found, {("walk_forward", "params"),
                                 ("walk_forward", "param_folds"),
                                 ("sector_caps", "caps"),
                                 ("sector_caps", "note")})

    def test_the_post_fix_projection_is_clean(self):
        """REPORTED AS PASSING PRE-FIX, DELIBERATELY — and the reason is MA40's own finding.

        Measured by restoring the sources to HEAD: 22 of the 23 fixtures in this file fail
        against the pre-fix tree, and this is the one that does not. It passes VACUOUSLY,
        because pre-fix neither block was in `BLOCK_SPEC`, so `check_payload` had nothing to
        look at and returned `[]` — a clean bill of health from a guard that was not watching.
        That is precisely the structural blindness MA40 exists to close, demonstrated on this
        test rather than argued. Claiming 23 of 23 would have been the more flattering number
        and the wrong one.
        """
        self.assertEqual(PS.check_payload(_WF_RES, RF.build_payload(_WF_RES)), [])

    def test_both_blocks_are_registered_in_BLOCK_SPEC(self):
        self.assertIn("walk_forward", PS.BLOCK_SPEC)
        self.assertIn("sector_caps", PS.BLOCK_SPEC)

    def test_the_schema_version_was_bumped(self):
        """The payload gained blocks; a reader comparing two artifacts must be able to tell."""
        self.assertGreaterEqual(RF.SCHEMA_VERSION, 7)


# ---------------------------------------------------------------------------
# MA47 — the panel cache key must carry ticker IDENTITY, not a count
# ---------------------------------------------------------------------------

class _NoDirProvider:
    dir = None


class TestMA47CacheKey(unittest.TestCase):

    def _prov(self, tickers):
        return PSRCH._panel_provenance(_NoDirProvider(), tickers, 63, 18, 63, 45)

    def test_two_different_universes_of_the_same_size_no_longer_collide(self):
        """THE B12 COLLISION, RE-ENCODED. The old key was
        `f"{len(tickers)}_{rebalance_days}_..."`, so the alphabetical A-C 800 and the largest
        800 hashed identically and the second silently read the first's panel."""
        a = PSRCH._provenance_key(self._prov(["AAPL", "MSFT", "IBM"]))
        b = PSRCH._provenance_key(self._prov(["TSLA", "NVDA", "AMZN"]))
        self.assertNotEqual(a, b, "same-length different universes must not share a key")

    def test_ticker_order_does_not_change_the_key(self):
        """A universe is a SET. Order-sensitivity would cause pointless 40-minute rebuilds."""
        a = PSRCH._provenance_key(self._prov(["AAPL", "MSFT", "IBM"]))
        b = PSRCH._provenance_key(self._prov(["IBM", "AAPL", "MSFT"]))
        self.assertEqual(a, b)

    def test_the_panel_shaping_env_toggles_are_in_the_key(self):
        """Each verified live in the tree, not taken from the audit's list: config.py:187,
        fundamental_panel.py:1056 and :1095."""
        base = PSRCH._provenance_key(self._prov(["AAPL", "MSFT"]))
        for var, val in (("EDGE_EV_POINT_IN_TIME", "false"),
                         ("EDGE_GRID_OFFSET", "20"),
                         ("EDGE_AUDIT_B6_LEGACY_TRUNCATION", "true")):
            old = os.environ.get(var)
            os.environ[var] = val
            try:
                self.assertNotEqual(PSRCH._provenance_key(self._prov(["AAPL", "MSFT"])), base,
                                    "%s must change the cache key" % var)
            finally:
                if old is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = old

    def test_the_parameters_are_still_in_the_key(self):
        """The four the old key DID cover must not have been lost in the rewrite."""
        base = PSRCH._provenance_key(self._prov(["AAPL", "MSFT"]))
        for kwargs in ({"rebalance_days": 21}, {"lookback_years": 6},
                       {"horizon": 252}, {"inst_lag_days": 15}):
            args = {"rebalance_days": 63, "lookback_years": 18, "horizon": 63,
                    "inst_lag_days": 45}
            args.update(kwargs)
            p = PSRCH._panel_provenance(_NoDirProvider(), ["AAPL", "MSFT"], **args)
            self.assertNotEqual(PSRCH._provenance_key(p), base, "%s must change the key" % kwargs)

    def test_an_unavailable_vintage_is_declared_not_faked(self):
        """The fingerprint records what it could not measure rather than pretending to cover it."""
        p = self._prov(["AAPL"])
        self.assertEqual(p["data"]["vintage"], "unavailable")
        self.assertIn("why", p["data"])

    def test_a_legacy_cache_file_without_a_sidecar_is_refused(self):
        """The failure direction is REBUILD, never reuse-what-we-cannot-vouch-for."""
        import tempfile

        import pandas as pd
        with tempfile.TemporaryDirectory() as d:
            prov = self._prov(["AAPL", "MSFT"])
            key = PSRCH._provenance_key(prov)
            path = os.path.join(d, "panel_cache_%s.pkl" % key)
            pd.DataFrame({"date": ["2020-01-01"], "x": [1]}).to_pickle(path)
            # No sidecar written -> must NOT be reused.
            msgs = []
            built = {"n": 0}

            def fake_build(*a, **k):
                built["n"] += 1
                return pd.DataFrame()

            real = PSRCH.FP.build_fundamental_panel
            PSRCH.FP.build_fundamental_panel = fake_build
            try:
                PSRCH.cached_panel(_NoDirProvider(), ["AAPL", "MSFT"], d,
                                   progress=lambda m: msgs.append(m))
            finally:
                PSRCH.FP.build_fundamental_panel = real
            self.assertEqual(built["n"], 1, "a sidecar-less cache file must be rebuilt")
            self.assertTrue(any("no provenance sidecar" in m for m in msgs),
                            "the refusal must say why: %s" % msgs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
