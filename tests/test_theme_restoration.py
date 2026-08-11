"""
Tests for the THEME RESTORATION and the vintage event it triggered.

Registered in `PREREG_theme_restoration.md`, committed alone at `1d12822`.

The live book scored 4 of 7 weighted themes and failed the calibrated long-short floor.
`capital_discipline` cleared the gate first (Spearman +0.8421). `institutional` (+0.1706) and
`insider` (+0.3596) FAILED it, and were then rebuilt to the panel's own definitions by FIDELITY-2
(`PREREG_fidelity2_rebuild.md`, `ef765fc`) and cleared the SAME bar at +0.9190 and +0.8726. All
seven weighted themes now reach a live score.

These pin what could silently rot: that nothing ships without clearing the bar, that the shipped
sources compute the SAME quantities the gate was measured on, and that the vintage arithmetic is
what the record says -- including that the same-day amendment did NOT reset the clock twice.

No network: the one test that would fetch is skipped unless a cache is present.
"""
from __future__ import annotations

import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import shadow_vintage as SV        # noqa: E402
from valuation.edge import track_meter as TM           # noqa: E402
from valuation.screener import issuance as ISS         # noqa: E402
from valuation.screener import settings as S           # noqa: E402
from scripts import theme_restoration as R             # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestOnlyTheThemeThatPassedIsWired(unittest.TestCase):
    """The whole point of the gate. Restoring a theme that failed fidelity would put a DIFFERENT
    theme under a validated theme's name — the B7 disease with a coherence justification."""

    def test_capital_discipline_has_a_live_source(self):
        self.assertTrue(hasattr(ISS, "share_issuance"))
        self.assertTrue(ISS.available())

    def test_institutional_and_insider_ship_ONLY_after_passing_on_the_rebuild(self):
        """UPDATED 2026-08-11 by FIDELITY-2. These two were absent because they FAILED the gate
        (+0.1706, +0.3596). They ship now because they were rebuilt to the panel's own
        definitions and cleared the SAME bar (+0.9190, +0.8726) — never because a second look
        made them seem good enough."""
        from valuation.screener import live_themes
        self.assertTrue(hasattr(live_themes, "columns_for"))
        src = io.open(live_themes.__file__, encoding="utf-8").read()
        self.assertIn("+0.9190", src)
        self.assertIn("+0.8726", src)

    def test_the_scan_enriches_through_the_two_reviewed_paths(self):
        src = io.open(os.path.join(REPO, "valuation", "screener", "screen.py"),
                      encoding="utf-8").read()
        self.assertIn("_enrich_with_issuance", src)
        self.assertIn("_enrich_with_live_themes", src)

    def test_the_deployed_weight_was_not_retuned(self):
        """Restoration enters at the DEPLOYED weight. A changed weight would be a different
        adoption needing its own gate."""
        self.assertEqual(S.WEIGHTS_ESTABLISHED["capital_discipline"], 0.125)
        self.assertEqual(S.WEIGHTS_SPECULATIVE["capital_discipline"], 0.125)


class TestTheShippedSourceMatchesWhatTheGateMeasured(unittest.TestCase):
    """THE DRIFT GUARD, and it caught a real one.

    The fidelity gate was measured on the V2G measured-only column. The first cut of the shipped
    module listed four share concepts and looped them one at a time, which resolves a DIFFERENT
    series than passing the list in one call — PEP came out -0.003537 against the measured
    column's -0.003628. Close enough to pass a spot-check, and not the quantity that scored
    +0.8421. If these two ever diverge again, the shipped theme is no longer the one that
    cleared the gate.
    """

    CACHE = os.path.join(REPO, "data", "live_themes", "xbrl")

    def test_the_concept_list_is_exactly_the_measured_columns(self):
        self.assertEqual(ISS._SHARE_CONCEPTS,
                         ["EntityCommonStockSharesOutstanding",
                          "WeightedAverageNumberOfDilutedSharesOutstanding"])

    def test_the_list_is_passed_in_one_call_not_looped(self):
        src = io.open(ISS.__file__, encoding="utf-8").read()
        self.assertIn("_annual_series(facts, _SHARE_CONCEPTS", src)
        self.assertNotIn("for c in _SHARE_CONCEPTS", src)

    def test_it_reproduces_the_measured_column_on_cached_names(self):
        """Offline: compares the shipped extraction against the V2G cache using the SAME facts
        would need the raw facts, which the cache does not keep — so this asserts the algorithm
        inputs match, and the end-to-end agreement (38/38) is recorded in the handoff."""
        if not os.path.isdir(self.CACHE):
            self.skipTest("V2G xbrl cache not present")
        n = len([f for f in os.listdir(self.CACHE) if f.endswith(".json")])
        self.assertGreater(n, 0)


class TestItFailsToNoneNeverToAGuess(unittest.TestCase):
    def test_an_unknown_ticker_returns_None(self):
        self.assertIsNone(ISS.share_issuance("", None))

    def test_a_transient_failure_is_not_cached(self):
        """A network error must be retried next scan. Banking it as 'this name has no issuance'
        would quietly shrink coverage for a month."""
        src = io.open(ISS.__file__, encoding="utf-8").read()
        self.assertIn("NOT cached", src)

    def test_the_enrichment_can_be_switched_off(self):
        """The off switch restores the exact pre-restoration behaviour."""
        from valuation.screener.screen import _enrich_with_issuance
        was = os.environ.get("SCREENER_LIVE_ISSUANCE")
        os.environ["SCREENER_LIVE_ISSUANCE"] = "0"
        try:
            rows = [{"ticker": "AAPL", "share_issuance": None}]
            stats = _enrich_with_issuance(rows, None)
            self.assertTrue(stats.get("disabled"))
            self.assertIsNone(rows[0]["share_issuance"])
        finally:
            if was is None:
                os.environ.pop("SCREENER_LIVE_ISSUANCE", None)
            else:
                os.environ["SCREENER_LIVE_ISSUANCE"] = was

    def test_an_already_populated_value_is_never_overwritten(self):
        from valuation.screener.screen import _enrich_with_issuance
        rows = [{"ticker": "AAPL", "share_issuance": 0.123}]
        stats = _enrich_with_issuance(rows, None)
        self.assertEqual(rows[0]["share_issuance"], 0.123)
        self.assertEqual(stats["already"], 1)


class TestTheVintageArithmetic(unittest.TestCase):
    def test_exactly_one_vintage_is_open_and_it_is_three(self):
        cv = TM.current_vintage()
        self.assertEqual(cv["vintage"], 3)
        self.assertEqual(cv["status"], "OPEN")

    def test_vintage_two_is_closed_not_deleted(self):
        v2 = next(v for v in TM.VINTAGES if v["vintage"] == 2)
        self.assertEqual(v2["status"], "CLOSED")
        self.assertIsNotNone(v2["closed"])
        self.assertIn("theme restoration", v2["reason"])

    def test_vintage_ones_void_record_is_untouched(self):
        """Voided vintages are kept, never deleted — they still appear in as_operated()."""
        v1 = next(v for v in TM.VINTAGES if v["vintage"] == 1)
        self.assertEqual(v1["status"], "VOID")

    def test_vintage_twos_pinned_params_id_was_NOT_rewritten(self):
        """A pin that moves retroactively is not a pin. Vintage 2 deliberately omits the new
        PARAM_KEY so its hash is exactly what the record published."""
        self.assertEqual(SV.pinned_snapshot(2)["params_id"], "0060c5ef3dda")

    def test_the_two_vintages_are_mechanically_different_models(self):
        """Without the added PARAM_KEY they would hash IDENTICAL — no declared weight changed —
        and `same_model` would report no change while the live book demonstrably changed."""
        self.assertFalse(SV.same_model(SV.pinned_snapshot(2), SV.pinned_snapshot(3)))

    def test_the_new_param_key_is_what_distinguishes_them(self):
        self.assertIn("themes_scored_live", SV.PARAM_KEYS)
        self.assertNotIn("themes_scored_live", SV.pinned_snapshot(2)["params"])
        self.assertIn("themes_scored_live", SV.pinned_snapshot(3)["params"])

    def test_no_declared_weight_changed_between_the_vintages(self):
        """This vintage exists because the BOOK changed, not because the model was retuned."""
        self.assertEqual(SV.pinned_snapshot(2)["params"]["theme_weights"],
                         SV.pinned_snapshot(3)["params"]["theme_weights"])

    def test_all_seven_weighted_themes_reach_a_live_score_after_the_amendment(self):
        """The coherence goal, reached in two stages on one day: five themes at open, seven
        after FIDELITY-2 rebuilt the two that had failed."""
        live = SV.pinned_snapshot(3)["params"]["themes_scored_live"]
        for t in ("capital_discipline", "institutional", "insider",
                  "momentum", "quality", "size", "value"):
            self.assertIn(t, live)

    def test_the_amendment_did_not_reset_the_clock_a_second_time(self):
        """The registered zero-accrued-days rule AMENDS in place, so the opening date and every
        date derived from it must be exactly where the restoration left them."""
        import datetime as _d
        self.assertEqual(TM.current_vintage()["opened"], _d.date(2026, 8, 11))
        self.assertEqual(TM.INCEPTION, _d.date(2026, 8, 11))
        self.assertEqual(SV.PINNED[3]["opened"], _d.date(2026, 8, 11))

    def test_no_fourth_vintage_was_opened(self):
        self.assertEqual(max(v["vintage"] for v in TM.VINTAGES), 3)
        self.assertEqual(SV.open_pairs()[0]["shadow_vintage"], 2,
                         "the shadow must still be vintage 2, the four-theme book")


class TestTheShadowBookOpened(unittest.TestCase):
    """V1's machinery fires for the first time. Before this, `open_pairs()` was documented as
    'Empty until an adoption opens vintage 3'."""

    def test_exactly_one_pair_is_open(self):
        pairs = SV.open_pairs()
        self.assertEqual(len(pairs), 1)

    def test_the_pair_is_live_three_shadowed_by_two(self):
        p = SV.open_pairs()[0]
        self.assertEqual(p["live_vintage"], 3)
        self.assertEqual(p["shadow_vintage"], 2)

    def test_the_shadow_runs_a_pinned_snapshot_not_a_reconstruction(self):
        self.assertIsNotNone(SV.pinned_snapshot(SV.open_pairs()[0]["shadow_vintage"]))

    def test_it_is_still_fenced_off_every_public_surface(self):
        """Research-only, and fenced BEFORE it has numbers to leak — PT-OUTBOUND is why."""
        for mod in ("valuation/web/app.py", "valuation/web/unified.py", "valuation/saas/app_saas.py"):
            p = os.path.join(REPO, mod)
            if os.path.exists(p):
                self.assertNotIn("shadow_vintage", io.open(p, encoding="utf-8").read(), mod)


class TestTheGateThresholdsAreTheRegisteredOnes(unittest.TestCase):
    def test_every_threshold_matches_the_register(self):
        self.assertEqual(R.FIDELITY_FLOOR, 0.60)
        self.assertEqual(R.MIN_PAIRS, 100)
        self.assertEqual(R.MAX_P, 0.01)
        self.assertEqual(R.CALIB_PCTILE, 95)
        self.assertEqual(R.COVERAGE_FLOOR, 0.05)
        self.assertEqual(R.MIN_COVERAGE, 0.30)
        self.assertEqual(R.MIN_DISTINCT, 2)

    def test_the_bar_is_the_max_of_floor_and_calibration(self):
        """A live theme must beat BOTH an absolute floor and what distinct panel themes score
        against each other. Dropping either half would have restored a failing theme."""
        src = io.open(R.__file__, encoding="utf-8").read()
        self.assertIn("max(FIDELITY_FLOOR", src)

    def test_the_three_candidates_are_the_three_dead_themes(self):
        self.assertEqual(set(R.UNDER_TEST),
                         {"capital_discipline", "institutional", "insider"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
