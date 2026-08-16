"""
MA59: the archived studies stay out of the live product, and the modules that
LOOK dead but are load-bearing stay in it. Run:

    python tests/test_ma59_quarantine.py

The audit's instruction was "archive, do not delete", and it named two lists:
modules whose only importer is a closed study's own script, and modules that
look dead and are not. Both lists were verified against a derived import graph
before this file was written, and the audit was right about every entry -- all
17 archive candidates are unreachable from a real entry point, all 6
load-bearing ones are reachable.

WHY THIS IS PINNED IN BOTH DIRECTIONS. A quarantine test that only checks the
dead list catches the harmless mistake (someone wires a closed study into the
live app) and misses the expensive one (someone reads "looks dead", deletes a
module the panel depends on, and changes what `BACKTEST_RESULTS.json`
reproduces). The audit says both passes agree on the second list, so it is
the one carrying the loud name.

WHAT THIS FILE DOES NOT CLAIM. Unreachable is not unused: every archived module
is still imported by its own study script and its own pin test, and those still
run. It means no code path starting at the web app can reach it, which is the
property "archived" is supposed to denote.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import import_graph  # noqa: E402


# Closed studies. Each is archived in place with a banner, per the B16 pattern:
# the file stays, the study stays reproducible, and nothing live may reach it.
ARCHIVED = (
    "valuation/edge/options_tail.py",
    "valuation/edge/options_exitreplay.py",
    "valuation/edge/options_xsection.py",
    "valuation/edge/tickflow.py",
    "valuation/edge/tickflow_signals.py",
    "valuation/edge/surface_xsec.py",
    "valuation/edge/kelly.py",
    "valuation/edge/dividends.py",
    "valuation/edge/convex_overlay.py",
    "valuation/edge/bucket_floor.py",
    "valuation/edge/antisignal.py",
    "valuation/edge/earnings_surface.py",
    "valuation/edge/surface_stock.py",
    "valuation/edge/options_vrp.py",
    "valuation/edge/options_vrp_portfolio.py",
    "valuation/edge/ev_multiples_study.py",
    # B16's quarantined exit rule. Unreachable IS its contract, not a finding.
    "valuation/edge/deprecated_options_exit.py",
)

# Looks dead by eye, is load-bearing. Deleting any of these changes what the
# live product computes or what a past backtest reproduces.
LOAD_BEARING = {
    "valuation/data/yahoo.py":
        "the free-stack price provider the CI scan depends on",
    "valuation/edge/congress.py":
        "D-series alt-data, inert by default but wired into the panel",
    "valuation/edge/usaspending.py":
        "D-series alt-data, inert by default but wired into the panel",
    "valuation/edge/edgar13d.py":
        "D-series alt-data, inert by default but wired into the panel",
    "valuation/edge/short_interest.py":
        "D-series alt-data, inert by default but wired into the panel",
    "valuation/edge/autolearn.py":
        "MA1's live-weight path -- retire it deliberately, never by deletion",
}


class Quarantine(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.reachable = import_graph.reachable()
        cls.all_modules = set(import_graph.graph())

    def test_every_named_module_still_exists(self):
        """A renamed file must not silently empty either list.

        Without this, deleting a module makes its quarantine test pass -- the
        strongest possible false all-clear, and the exact shape of the bug
        MA59 exists to prevent.
        """
        for rel in list(ARCHIVED) + list(LOAD_BEARING):
            with self.subTest(rel):
                self.assertIn(rel, self.all_modules,
                              f"{rel} is named by MA59 but is not in the tree. "
                              "If it was deliberately removed, remove it here "
                              "in the same commit so the diff shows it.")

    def test_archived_studies_are_unreachable_from_the_live_product(self):
        leaked = sorted(r for r in ARCHIVED if r in self.reachable)
        self.assertEqual(
            leaked, [],
            "A closed study is now reachable from a production entry point. "
            "These modules are archived: their verdicts are recorded and their "
            "code is kept only so the study reproduces. Reaching one from the "
            "live app means the product is running an experiment.")

    def test_load_bearing_modules_are_still_reachable(self):
        for rel, why in sorted(LOAD_BEARING.items()):
            with self.subTest(rel):
                self.assertIn(
                    rel, self.reachable,
                    f"{rel} is no longer reachable from any entry point. It "
                    f"looks dead and is not: {why}. If this is deliberate, it "
                    "is a construction change and needs a register, not a "
                    "deletion.")

    def test_the_reachability_probe_is_not_vacuous(self):
        """The pins above are worthless if reachability returns everything.

        Two ways this test could pass while measuring nothing: the entry points
        could resolve to nothing (empty reachable set, so no archived module is
        ever 'leaked'), or the graph could be complete (everything reachable,
        so no load-bearing module is ever missing). Both are checked.
        """
        self.assertTrue(
            any((import_graph.ROOT / e).exists()
                for e in import_graph.ENTRY_POINTS),
            "No entry point exists, so nothing is reachable and the archive "
            "half of this suite passes vacuously.")
        self.assertGreater(len(self.reachable), 50,
                           "Reachable set implausibly small -- the graph "
                           "resolver has probably stopped resolving imports.")
        self.assertLess(len(self.reachable), len(self.all_modules),
                        "Everything is reachable, so the archive pin cannot "
                        "fail and proves nothing.")

    def test_deadness_is_measured_transitively_not_by_direct_importers(self):
        """The distinction this whole item turns on, pinned as a live example.

        `surface_xsec` IS imported by a file under `valuation/`, so a
        direct-importer count calls it production code. That importer is
        `tickflow_signals`, which nothing live reaches. If someone rewrites
        the analysis to count direct importers, this fails.
        """
        importers = import_graph.importers("valuation/edge/surface_xsec.py")
        self.assertIn("valuation/edge/tickflow_signals.py", importers,
                      "surface_xsec's in-package importer has moved; "
                      "re-derive the example before trusting the comment.")
        self.assertNotIn("valuation/edge/surface_xsec.py", self.reachable,
                         "surface_xsec is reachable, so the transitive "
                         "example no longer demonstrates anything.")


class Banners(unittest.TestCase):
    """Archived modules say so in their own docstring.

    A reader who opens the file, rather than the ledger, has to be told. The
    banner is what makes 'archived' visible at the point of use -- the B16
    pattern, which this project has already used for the deprecated exit rule.
    """

    def test_each_archived_module_carries_the_banner(self):
        missing = []
        for rel in ARCHIVED:
            head = (import_graph.ROOT / rel).read_text(
                encoding="utf-8", errors="replace")[:2000]
            if "ARCHIVED" not in head:
                missing.append(rel)
        self.assertEqual(
            missing, [],
            "Archived modules must open with an ARCHIVED banner naming the "
            "study that closed and what may still import them.")

    def test_the_banner_check_can_actually_fail(self):
        """Positive control: a live module must NOT carry the banner.

        Otherwise the assertion above could be satisfied by the word appearing
        everywhere, and would stop distinguishing anything.
        """
        live = (import_graph.ROOT / "valuation/edge/autolearn.py").read_text(
            encoding="utf-8", errors="replace")[:2000]
        self.assertNotIn("ARCHIVED", live)


class RejectedOverrides(unittest.TestCase):
    """The one-env-var paths back to a twice-rejected intervention.

    MA59: `SCREENER_SECTOR_NEUTRAL`, `SCREENER_RESIDUAL_MOMENTUM` and
    `VALQUO_ROBUST_Z` each re-enable something the research eliminated, and a
    run with one set reports its results under the ordinary headline with
    nothing anywhere saying the model changed. The audit offered "delete the
    override or make it warn"; deleting removes the ability to A/B the rejected
    arm, so it warns.
    """

    def test_the_rejected_flags_default_to_off(self):
        from valuation.config import Config
        for var in ("SCREENER_SECTOR_NEUTRAL", "SCREENER_RESIDUAL_MOMENTUM"):
            self.assertNotIn(
                var, os.environ,
                f"{var} is set in this environment, so the run below would "
                "not be measuring the default.")
        cfg = Config()
        self.assertFalse(cfg.sector_neutral)
        self.assertFalse(cfg.residual_momentum)
        self.assertEqual(cfg.rejected_overrides_active(), {})

    def test_the_default_path_warns_about_nothing(self):
        """A warning on every ordinary run is noise, and noise gets muted."""
        import warnings
        from valuation.config import Config
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            Config()
        self.assertEqual(
            [w for w in caught if issubclass(w.category, RuntimeWarning)], [],
            "Constructing a default Config warned. The rejected-override "
            "warning must fire only for someone who opted in.")

    def test_enabling_a_rejected_intervention_warns(self):
        import warnings
        from valuation.config import Config
        os.environ["SCREENER_SECTOR_NEUTRAL"] = "true"
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                cfg = Config()
            self.assertTrue(cfg.sector_neutral)
            self.assertIn("sector_neutral", cfg.rejected_overrides_active())
            msgs = [str(w.message) for w in caught
                    if issubclass(w.category, RuntimeWarning)]
            self.assertTrue(
                any("REJECTED INTERVENTION ENABLED" in m for m in msgs),
                f"no warning raised; got {msgs}")
        finally:
            os.environ.pop("SCREENER_SECTOR_NEUTRAL", None)

    def test_the_robust_z_flag_still_carries_its_warning(self):
        """Pinned by source, because the module-level branch runs at import.

        Re-importing under a patched environment would either be a no-op (the
        module is cached) or would re-run a module other tests hold references
        into, so this reads the source instead and says so.
        """
        import inspect
        from valuation.screener import cross_sectional
        src = inspect.getsource(cross_sectional)
        self.assertIn("VALQUO_ROBUST_Z", src)
        self.assertIn("REJECTED INTERVENTION ENABLED", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
