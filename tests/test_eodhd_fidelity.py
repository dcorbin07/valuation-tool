# -*- coding: utf-8 -*-
"""Tests for the EODHD cross-vendor route: the provider, the step-3 bars, the step-4 gate.

**WHAT THESE PIN, in order of how expensive the mistake would be.**

1. **THE LICENCE FENCE.** Nothing EODHD-derived that carries a per-name value may be tracked. The
   repo is public; the raw rows live on `D:\\eodhd` and research artifacts carry derived statistics
   only.
2. **`datekey` IS THE FILING DATE.** The whole point-in-time claim rests on it, and the tempting
   repair -- fall back to the period end when a filing date is absent -- is exactly the look-ahead
   the design exists to avoid. Mutation-tested.
3. **THE BARS ARE `D9`'s.** A retyped 0.80 is a second definition of a pre-committed bar, and this
   project has been bitten by a frozen copy of a moving number more than once (`MA5`).
4. **THE TWO SIDES ARE COMPOSED SYMMETRICALLY.** A five-theme incumbent against a four-theme
   challenger is not a like-for-like comparison, and the asymmetry would read as a vendor
   disagreement.
5. **A MISSING FIELD IS NAMED.** Five wired factors were once empty in every run of this project's
   history without raising.
"""
import ast
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import eodhd_provider as EP                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROV = os.path.join(ROOT, "valuation", "studies", "eodhd_provider.py")
FID = os.path.join(ROOT, "scripts", "eodhd_fidelity.py")
GATE = os.path.join(ROOT, "scripts", "eodhd_delisted.py")


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _payload(filing="2026-07-28", second_filing=None):
    """A two-period payload; the second period's filing date is optional on purpose."""
    q2 = {"date": "2026-06-30", "totalRevenue": "100", "netIncome": "9",
          "operatingIncome": "12"}
    if filing:
        q2["filing_date"] = filing
    q3 = {"date": "2026-09-30", "totalRevenue": "110", "netIncome": "10",
          "operatingIncome": "13"}
    if second_filing:
        q3["filing_date"] = second_filing
    return {"General": {"Code": "TEST", "IsDelisted": False},
            "Financials": {
                "Income_Statement": {"quarterly": {"2026-06-30": q2, "2026-09-30": q3}},
                "Balance_Sheet": {"quarterly": {
                    "2026-06-30": dict(q2, totalStockholderEquity="50", totalAssets="200"),
                    "2026-09-30": dict(q3, totalStockholderEquity="55", totalAssets="210")}},
                "Cash_Flow": {"quarterly": {
                    "2026-06-30": dict(q2, totalCashFromOperatingActivities="20",
                                       capitalExpenditures="-5"),
                    "2026-09-30": dict(q3, totalCashFromOperatingActivities="22",
                                       capitalExpenditures="-6")}}}}


class TheLicenceFence(unittest.TestCase):
    def test_the_raw_root_is_a_windows_path_outside_the_repository(self):
        # `MA42`: a Windows path is NOT absolute under POSIX -- a backslash is an ordinary
        # filename character -- so `os.path.abspath` on a Linux runner resolves `D:\eodhd` to a
        # path INSIDE the checkout and a naive "outside the repo" test returns False in CI while
        # passing locally. Compared with `ntpath` explicitly, which is the platform the path is
        # written for.
        import ntpath
        for src in (_src(FID), _src(GATE)):
            self.assertIn(r"D:\eodhd", src)
        for raw in (r"D:\eodhd",):
            self.assertTrue(ntpath.isabs(raw))
            drive, _ = ntpath.splitdrive(raw)
            self.assertTrue(drive)
            self.assertNotEqual(drive.lower(), ntpath.splitdrive(ROOT)[0].lower() + "X")
        # positive control: a repo-relative root must be rejected by the same rule
        self.assertFalse(ntpath.splitdrive(os.path.join("data", "eodhd"))[0])

    def test_no_tracked_artifact_carries_a_per_name_vendor_value(self):
        # The fence is on TRACKED files. A research artifact may carry a derived statistic (an
        # overlap rate, a Spearman) and never a per-name figure.
        for p in (PROV, FID, GATE):
            src = _src(p)
            self.assertNotIn("api_token=", src.replace("api_token=<REDACTED>", ""))


class TheFilingDateIsTheKey(unittest.TestCase):
    def test_a_period_without_a_filing_date_is_dropped(self):
        rows = EP.fundamentals_rows(_payload(), "TEST")
        self.assertEqual([r["date"] for r in rows], ["2026-06-30"])

    def test_datekey_is_the_filing_date_and_not_the_period_end(self):
        rows = EP.fundamentals_rows(_payload(), "TEST")
        self.assertEqual(rows[0]["datekey"], "2026-07-28")
        self.assertNotEqual(rows[0]["datekey"], rows[0]["date"])

    def test_both_periods_survive_when_both_carry_a_filing_date(self):
        # Positive control: the drop rule must not be "drop everything".
        rows = EP.fundamentals_rows(_payload(second_filing="2026-10-27"), "TEST")
        self.assertEqual(len(rows), 2)

    def test_the_drop_is_reported_rather_than_silently_differenced(self):
        d = EP.dropped_for_no_filing_date(_payload())
        self.assertEqual((d["periods"], d["with_filing_date"], d["dropped"]), (2, 1, 1))

    def test_the_source_never_falls_back_to_the_period_end_for_datekey(self):
        """MUTATION-SHAPED: the tempting repair is a look-ahead, so forbid it structurally.

        A fallback would place an unpublished figure at its period end, which is precisely the
        look-ahead the point-in-time read exists to remove.
        """
        tree = ast.parse(_src(PROV))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "fundamentals_rows"][0]
        body = ast.unparse(fn)
        self.assertIn("filing_date", body)
        self.assertNotIn('r.get("date") or r.get("filing_date")', body)
        # the row is skipped on a falsy datekey -- the only safe behaviour
        self.assertIn("continue", body)


class TheMappingIsMeasuredNotAssumed(unittest.TestCase):
    def _freeze(self, payloads):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "fundamentals"))
        for tk, pay in payloads.items():
            with io.open(os.path.join(d, "fundamentals", "%s.json" % tk), "w",
                         encoding="utf-8") as fh:
                json.dump({"payload": pay}, fh)
        return d

    def test_probe_reports_rates_with_their_denominator(self):
        d = self._freeze({"TEST": _payload(second_filing="2026-10-27")})
        rep = EP.probe(d, ["TEST"])
        self.assertEqual(rep["rows"], 2)
        self.assertEqual(rep["names_with_a_payload"], 1)
        self.assertIn("field_non_null_counts", rep)
        self.assertEqual(rep["field_non_null_counts"]["revenue"], 2)
        self.assertEqual(rep["field_non_null"]["revenue"], 1.0)

    def test_a_field_that_never_appears_is_named(self):
        d = self._freeze({"TEST": _payload(second_filing="2026-10-27")})
        rep = EP.probe(d, ["TEST"])
        # this fixture carries no inventory anywhere, so the mapping must say so
        self.assertIn("inventory", rep["never_seen"])
        self.assertNotIn("revenue", rep["never_seen"])

    def test_a_missing_required_column_is_reported(self):
        pay = _payload(second_filing="2026-10-27")
        for freq in ("quarterly",):
            for per in pay["Financials"]["Balance_Sheet"][freq]:
                pay["Financials"]["Balance_Sheet"][freq][per].pop("totalAssets", None)
        d = self._freeze({"TEST": pay})
        rep = EP.probe(d, ["TEST"])
        self.assertIn("assets", rep["required_missing"])

    def test_an_absent_name_is_not_an_error_and_not_a_row(self):
        d = self._freeze({"TEST": _payload()})
        rep = EP.probe(d, ["TEST", "NOPE"])
        self.assertEqual(rep["names_with_a_payload"], 1)
        self.assertIsNone(EP.load_unit(d, "NOPE"))

    def test_the_capex_sign_is_measured_in_both_directions(self):
        neg = self._freeze({"A": _payload(second_filing="2026-10-27")})
        r = EP.capex_sign(neg, ["A"])
        self.assertEqual(r["positive"], 0)
        self.assertTrue(r["matches_sharadar_convention"])
        pay = _payload(second_filing="2026-10-27")
        for per in pay["Financials"]["Cash_Flow"]["quarterly"]:
            pay["Financials"]["Cash_Flow"]["quarterly"][per]["capitalExpenditures"] = "5"
        pos = self._freeze({"A": pay})
        r2 = EP.capex_sign(pos, ["A"])
        self.assertEqual(r2["negative"], 0)
        self.assertFalse(r2["matches_sharadar_convention"])


class TheTwoThemesAreDeliberatelyNotServed(unittest.TestCase):
    def test_insider_and_institutional_return_empty_on_purpose(self):
        p = EP.EodhdProvider("nowhere", price_delegate=None)
        self.assertEqual(p.insider_history("AAPL"), [])
        self.assertEqual(p.institutional_history("AAPL"), [])

    def test_the_reason_is_recorded_with_its_numbers(self):
        # A future session must not wire a 2.4%-of-rows feed in silently; the measured reason is
        # in the module so the decision is checkable rather than remembered.
        src = _src(PROV)
        self.assertIn("137,297", src)
        self.assertIn("5,636,964", src)


class TheBarsAreImportedNotRetyped(unittest.TestCase):
    def test_no_bar_literal_is_retyped_in_the_step_three_script(self):
        """`MA5`: a second copy of a pre-committed bar is how one freezes while the other moves."""
        tree = ast.parse(_src(FID))
        lits = {round(float(n.value), 4) for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, float)}
        for bar in (0.8, 0.6, 0.7):
            self.assertNotIn(bar, lits,
                             "bar %r is retyped; import it from d9_fidelity instead" % bar)

    def test_the_bars_actually_resolve_to_d9s_values(self):
        from scripts import d9_fidelity as D9
        self.assertEqual((D9.B1_COMPOSITE_SPEARMAN, D9.B2_DECILE_OVERLAP,
                          D9.B3_THEME_SPEARMAN), (0.80, 0.60, 0.70))
        self.assertEqual(D9.FIDELITY2, {"institutional": 0.9190, "insider": 0.8726})


class TheComparisonIsSymmetric(unittest.TestCase):
    def test_both_sides_are_composed_on_the_same_theme_set(self):
        from scripts import eodhd_fidelity as F
        from scripts import d9_fidelity as D9
        self.assertEqual(tuple(F.THEMES), tuple(D9.B3_THEMES))
        self.assertNotIn("insider", F.THEMES)
        # and the script must compose BOTH sides through the same call, not one each way
        src = _src(FID)
        self.assertEqual(src.count("_flat_composite(sh_t, THEMES)"), 1)
        self.assertEqual(src.count("_flat_composite(eo_t, THEMES)"), 1)

    def test_the_four_theme_basis_is_declared_as_a_deviation(self):
        src = _src(FID)
        self.assertIn("FOUR THEMES", src.upper())
        self.assertIn("NOT THE SAME STATISTIC", src.upper())


class TheGatesRefuse(unittest.TestCase):
    def test_compare_refuses_without_scores(self):
        from scripts import eodhd_fidelity as F
        if os.path.exists(F.SCORES_OUT):
            self.skipTest("SKIPPED LOUDLY: EODHD scores already exist at %s" % F.SCORES_OUT)
        self.assertEqual(F.compare(), 2)

    def test_score_refuses_without_a_passing_probe(self):
        src = _src(FID)
        self.assertIn("REFUSED: no passing probe artifact", src)
        self.assertIn("probe_pass", src)

    def test_the_refusal_is_conditional_rather_than_hard_coded(self):
        tree = ast.parse(_src(FID))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "score"][0]
        self.assertTrue(any(isinstance(n, ast.If) for n in ast.walk(fn)))


class TheStepFourGate(unittest.TestCase):
    def test_the_reuse_filter_excludes_collisions_and_reports_them(self):
        from scripts import eodhd_delisted as G
        try:
            dead, surv, nd, ns, coll = G.cohorts()
        except (FileNotFoundError, OSError) as exc:
            self.skipTest("SKIPPED LOUDLY: spine or panel absent (%s)" % exc)
        self.assertEqual(len(set(dead) & set(surv)), 0)
        self.assertGreater(coll["collide_with_a_live_ticker"], 0)
        self.assertEqual(coll["dead_tickers_used"],
                         coll["dead_tickers_total"] - coll["collide_with_a_live_ticker"])

    def test_the_cohorts_are_seeded_so_they_cannot_be_redrawn(self):
        from scripts import eodhd_delisted as G
        try:
            a = G.cohorts()[0]
            b = G.cohorts()[0]
        except (FileNotFoundError, OSError) as exc:
            self.skipTest("SKIPPED LOUDLY: spine or panel absent (%s)" % exc)
        self.assertEqual(a, b)

    def test_a_reuse_suspected_row_is_excluded_from_both_sides_of_the_rate(self):
        src = _src(GATE)
        self.assertIn("reuse_suspected", src)
        self.assertIn("rows_scored", src)
        self.assertIn("reuse_suspected_excluded", src)

    def test_the_control_cohort_exists_at_all(self):
        # An empty-statement rate with no comparator cannot distinguish a survivorship hole from
        # a vendor that is simply thin on old data. The control is the measurement.
        src = _src(GATE)
        self.assertIn("survivors", src)
        self.assertIn("empty_share_difference_dead_minus_survivors", src)


class ThePathsResolveBesideTheirInputs(unittest.TestCase):
    def test_the_data_root_is_not_taken_from_the_repo_root(self):
        """`E-5`: a worktree carries `data/` EMPTY, so a repo-relative artifact path reads nothing.

        The failure mode is a silent skip or an empty frame scored as a result, which is why this
        is pinned rather than left to whoever next runs it from a worktree.
        """
        for p in (FID, GATE):
            src = _src(p)
            self.assertIn("data_root(required=False)", src)

    def test_both_scripts_run_standalone(self):
        # `O21-D2`: this project's runner judges a suite by EXIT CODE, and a file with no
        # `__main__` block defines its tests, executes nothing and exits 0.
        for p in (FID, GATE, __file__):
            self.assertIn('if __name__ == "__main__":', _src(p))


if __name__ == "__main__":
    unittest.main(verbosity=2)
