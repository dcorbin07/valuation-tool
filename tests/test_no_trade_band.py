"""Tests for the NO-TRADE BAND adopted 2026-08-13 (S14, width 0.30).

Registered in `PREREG_s14_adoption.md`, committed alone at `793f777` before any wiring existed.

WHAT THESE PIN, and why each would otherwise rot silently:

* The band rule is ONE OBJECT shared by the backtest and the live book -- not two equivalent
  implementations. Equivalence maintained by hand is equivalence that drifts, and a drifted live
  band would be a different construction wearing S14's evidence (the B7 disease).
* The live path ACTUALLY APPLIES the band. Before this adoption `exit_frac` was declared in three
  places and applied in none, so "the config says 0.30" was never evidence that any book had one.
* The band does not apply without a previous book, and says so rather than looking like a book
  with the band off.
* A retained name is LABELLED. Don accepted the divergence; the product's side of that bargain is
  that the user can tell which names the ranking alone would not have selected.

The full construction-fidelity gate runs against the real 69-date panel
(`scripts/s14_construction_fidelity.py`). These are its hermetic counterpart: no panel, no data
directory, no network -- so they run on a fresh CI runner, per the LA15 isolation standard.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import fundamental_panel as FP       # noqa: E402
from valuation.edge import no_trade_band as NTB          # noqa: E402
from valuation.edge import valquo_index as VI            # noqa: E402
from valuation.screener import settings as S             # noqa: E402


def _rows(scores):
    """A synthetic cross-section in the shape a scan produces."""
    return [{"ticker": f"T{i:04d}", "hot_score": float(s), "price": 10.0,
             "market_cap": 5e10} for i, s in enumerate(scores)]


class TestTheRuleIsOneObject(unittest.TestCase):
    def test_the_backtest_and_the_shared_module_are_the_same_function(self):
        """Not 'equivalent' -- IDENTICAL. If someone re-implements the rule next to the live
        book, this fails, which is the whole reason the rule was moved out of the panel."""
        self.assertIs(FP._band_select, NTB.band_select)
        self.assertIs(FP._exit_rank_for, NTB.exit_rank_for)

    def test_nothing_else_defines_a_band_rule(self):
        """A second definition anywhere in `valuation/` is the failure mode this guards."""
        found = []
        for root, _dirs, files in os.walk("valuation"):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(root, fn)
                with open(p, encoding="utf-8") as fh:
                    src = fh.read()
                if "def band_select" in src or "def _band_select" in src:
                    found.append(p.replace("\\", "/"))
        self.assertEqual(found, ["valuation/edge/no_trade_band.py"], found)

    def test_the_adopted_width_is_not_restated_as_a_bare_literal(self):
        """The config's width must EQUAL the adopted constant. If one moves without the other,
        the live book and the constant disagree and this fails."""
        self.assertEqual(NTB.BAND_WIDTH, 0.30)
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["exit_frac"], NTB.BAND_WIDTH)


class TestTheExitRankDerivation(unittest.TestCase):
    def test_it_reproduces_the_inline_formula_it_replaced(self):
        """The panel used to compute this inline. Checked over a grid rather than asserted."""
        for n_uni in range(20, 2000, 37):
            for k in (1, 5, 10, max(1, int(n_uni * 0.10))):
                for w in (0.12, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75):
                    self.assertEqual(NTB.exit_rank_for(n_uni, k, w),
                                     max(k, int(n_uni * w)))

    def test_it_truncates_and_does_not_round(self):
        """Load-bearing: the gate compares books name-for-name, so rounding here would select a
        different book on any cross-section where the product is not integral."""
        # 105 * 0.30 = 31.5 -> 31, not 32.
        self.assertEqual(NTB.exit_rank_for(105, 10, 0.30), 31)

    def test_no_width_means_no_band(self):
        self.assertEqual(NTB.exit_rank_for(1000, 25, None), 25)

    def test_the_band_can_never_be_narrower_than_the_book(self):
        """Otherwise a held name could be 'outside the band' while still inside the book."""
        self.assertEqual(NTB.exit_rank_for(100, 50, 0.10), 50)


class TestTheRuleItself(unittest.TestCase):
    def test_with_no_band_it_reduces_exactly_to_plain_top_n(self):
        """This is what makes the no-band case a true baseline rather than a second code path."""
        comp = np.array([9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
        ticks = np.array([f"T{i}" for i in range(6)], dtype=object)
        got = NTB.band_select(comp, ticks, {"T4", "T5"}, 3, 3)
        self.assertEqual(set(got), {"T0", "T1", "T2"})

    def test_a_held_name_inside_the_band_is_retained_over_a_higher_challenger(self):
        comp = np.array([9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
        ticks = np.array([f"T{i}" for i in range(6)], dtype=object)
        # T3 is held and sits at rank 3, inside an exit_rank of 5 -> kept, so the book is
        # T0, T1, T3 and the challenger T2 is passed over.
        got = NTB.band_select(comp, ticks, {"T0", "T1", "T3"}, 3, 5)
        self.assertEqual(set(got), {"T0", "T1", "T3"})
        self.assertNotIn("T2", got)

    def test_book_size_is_held_constant(self):
        comp = np.arange(50, 0, -1).astype(float)
        ticks = np.array([f"T{i}" for i in range(50)], dtype=object)
        for held in ({}, {"T30"}, {f"T{i}" for i in range(20, 45)}):
            self.assertEqual(len(NTB.band_select(comp, ticks, set(held), 10, 25)), 10)

    def test_retained_names_are_exactly_the_ones_rank_alone_would_not_buy(self):
        comp = np.array([9.0, 8.0, 7.0, 6.0, 5.0, 4.0])
        ticks = np.array([f"T{i}" for i in range(6)], dtype=object)
        r = NTB.held_within_band(comp, ticks, {"T0", "T1", "T3"}, 3, 5)
        self.assertEqual(r, {"T3"})          # T0/T1 are top-3 on rank anyway

    def test_no_held_set_means_nothing_is_retained(self):
        comp = np.arange(20, 0, -1).astype(float)
        ticks = np.array([f"T{i}" for i in range(20)], dtype=object)
        self.assertEqual(NTB.held_within_band(comp, ticks, set(), 5, 10), set())


class TestTheLiveBookAppliesIt(unittest.TestCase):
    """The hermetic counterpart of the construction-fidelity gate.

    These call `build_index` -- the LIVE entry point -- and compare against the rule the
    BACKTEST applies. A test that called the rule directly would pass by construction.
    """

    def setUp(self):
        # Descending scores so rank == index, which makes the expected book readable.
        self.scores = list(range(200, 0, -1))
        self.rows = _rows(self.scores)
        self.ticks = np.array([r["ticker"] for r in self.rows], dtype=object)
        self.comp = np.array([r["hot_score"] for r in self.rows], dtype=float)

    def _live(self, held, width, n=20):
        return VI.build_index(self.rows, large_cap_min=0.0, top_n=n, weighting="equal",
                              held=held, exit_frac=width)

    def test_the_live_book_reproduces_the_backtest_rule_name_for_name(self):
        """THE GATE, in miniature. Held names deep in the band, so the two paths could differ."""
        held = {f"T{i:04d}" for i in range(15, 45)}
        n, width = 20, NTB.BAND_WIDTH
        expected = FP._band_select(self.comp, self.ticks, held, n,
                                   FP._exit_rank_for(len(self.rows), n, width))
        live = [p["ticker"] for p in self._live(held, width, n)["positions"]]
        self.assertEqual(set(live), set(expected))
        # Non-vacuity: it must differ from plain top-N, or this proves nothing.
        plain = {f"T{i:04d}" for i in range(n)}
        self.assertNotEqual(set(live), plain)

    def test_without_a_band_the_live_book_is_plain_top_n(self):
        live = [p["ticker"] for p in self._live({f"T{i:04d}" for i in range(15, 45)},
                                                None, 20)["positions"]]
        self.assertEqual(set(live), {f"T{i:04d}" for i in range(20)})

    def test_without_a_previous_book_the_band_cannot_apply_and_says_so(self):
        """The honest first-rebalance state. It must NOT read as 'the band is off'."""
        p = self._live(set(), NTB.BAND_WIDTH, 20)
        self.assertFalse(p["no_trade_band"]["applied"])
        self.assertEqual(p["no_trade_band"]["n_held_supplied"], 0)
        self.assertIn("no previous book", p["no_trade_band"]["note"])
        self.assertEqual({x["ticker"] for x in p["positions"]},
                         {f"T{i:04d}" for i in range(20)})

    def test_the_payload_records_that_the_band_bound(self):
        p = self._live({f"T{i:04d}" for i in range(15, 45)}, NTB.BAND_WIDTH, 20)
        b = p["no_trade_band"]
        self.assertTrue(b["applied"])
        self.assertEqual(b["width"], 0.30)
        self.assertEqual(b["exit_rank"], int(200 * 0.30))
        self.assertGreater(b["n_band_retained"], 0)
        self.assertEqual(set(b["band_retained"]),
                         NTB.held_within_band(self.comp, self.ticks,
                                              {f"T{i:04d}" for i in range(15, 45)}, 20,
                                              int(200 * 0.30)))


class TestDisplayHonesty(unittest.TestCase):
    def test_a_retained_name_is_labelled_and_an_ordinary_pick_is_not(self):
        rows = _rows(list(range(200, 0, -1)))
        held = {f"T{i:04d}" for i in range(15, 45)}
        p = VI.build_index(rows, large_cap_min=0.0, top_n=20, weighting="equal",
                           held=held, exit_frac=NTB.BAND_WIDTH)
        retained = [x for x in p["positions"] if x["band_retained"]]
        ordinary = [x for x in p["positions"] if not x["band_retained"]]
        self.assertTrue(retained, "the fixture must produce at least one retained name")
        self.assertTrue(ordinary)
        for x in retained:
            self.assertEqual(x["why_band"], NTB.BAND_HELD_NOTE)
            self.assertIn("challenger", x["why_band"])
        for x in ordinary:
            self.assertEqual(x["why_band"], "")

    def test_every_position_carries_the_field_even_with_no_band(self):
        """Absent-vs-false is the difference between 'no band' and 'field never written'."""
        p = VI.build_index(_rows(list(range(50, 0, -1))), large_cap_min=0.0, top_n=10,
                           weighting="equal")
        for x in p["positions"]:
            self.assertIn("band_retained", x)
            self.assertFalse(x["band_retained"])


class TestThePreviousBookRead(unittest.TestCase):
    def test_it_reads_the_tickers_of_a_real_payload(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"positions": [{"ticker": "AAA"}, {"ticker": "BBB"}]}, fh)
            self.assertEqual(sorted(VI._previous_book(p)), ["AAA", "BBB"])

    def test_it_fails_to_empty_rather_than_holding_the_wrong_names(self):
        """A band that silently held wrong names would still LOOK like a valid book."""
        with tempfile.TemporaryDirectory() as d:
            missing = os.path.join(d, "nope.json")
            self.assertEqual(VI._previous_book(missing), [])
            bad = os.path.join(d, "bad.json")
            with open(bad, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            self.assertEqual(VI._previous_book(bad), [])
            notdict = os.path.join(d, "list.json")
            with open(notdict, "w", encoding="utf-8") as fh:
                json.dump([1, 2, 3], fh)
            self.assertEqual(VI._previous_book(notdict), [])

    def test_rows_without_a_ticker_are_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.json")
            with open(p, "w", encoding="utf-8") as fh:
                json.dump({"positions": [{"ticker": "AAA"}, {"weight": 1}, "junk"]}, fh)
            self.assertEqual(VI._previous_book(p), ["AAA"])


class TestWhereTheBandAppliesAndWhereItDeliberatelyDoesNot(unittest.TestCase):
    def test_the_decile_config_carries_the_adopted_width(self):
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["exit_frac"], 0.30)
        self.assertEqual(S.BOOK_CONFIGS["taxable"]["top_frac"], 0.10)

    def test_the_fixed_n_book_stays_band_less_because_that_arm_was_never_measured(self):
        """S14 measured the DECILE book. `exit_frac` is a fraction of the ranked UNIVERSE, which
        on a 25-name book would hold nearly every name nearly forever. Shipping it there would
        be borrowing S14's evidence for a construction nobody measured."""
        self.assertIsNone(S.BOOK_CONFIGS["roth"]["exit_frac"])
        self.assertEqual(S.BOOK_CONFIGS["roth"]["top_n"], 25)

    def test_the_taxable_measured_figures_are_flagged_as_belonging_to_the_old_width(self):
        """The `measured` block was measured at 0.20 and no run has measured 0.30 for this
        config, so it must not be presented as describing the shipped width."""
        cfg = S.BOOK_CONFIGS["taxable"]
        self.assertEqual(cfg["measured_width"], 0.20)
        self.assertNotEqual(cfg["measured_width"], cfg["exit_frac"])


class TestTheHeadlineSaysWhereItDiffers(unittest.TestCase):
    def test_a_banded_book_declares_that_the_published_figures_exclude_the_band(self):
        """The two errors this prevents: quietly re-pointing the headline at a construction
        nobody measured, or letting a reader assume the published alpha describes this book."""
        rows = _rows(list(range(200, 0, -1)))
        p = VI.build_index(rows, large_cap_min=0.0, top_n=20, weighting="equal",
                           held={f"T{i:04d}" for i in range(15, 45)}, exit_frac=0.30)
        h = p["headline_scope"]
        self.assertTrue(h["differs"])
        self.assertTrue(h["live_book_applies_band"])
        self.assertIn("no no-trade band", h["headline_describes"])
        self.assertIn("WITHOUT a", h["note"])
        # The published `method` string is UNCHANGED -- posture language is not rewritten.
        self.assertIn("top decile", p["method"])

    def test_an_unbanded_book_does_not_claim_a_divergence(self):
        p = VI.build_index(_rows(list(range(50, 0, -1))), large_cap_min=0.0, top_n=10,
                           weighting="equal")
        self.assertFalse(p["headline_scope"]["differs"])


class TestTheConfigBlockIsBuiltInOnePlace(unittest.TestCase):
    """It used to be built separately by `export()` and by the `/api/valquo-index` route, each
    with its own `band_note`. When the band became real, one copy would have been corrected and
    the other left telling readers to apply it by hand -- after which it would run twice."""

    def test_a_banded_config_says_the_band_is_already_applied(self):
        cb = VI.config_block("taxable", S.BOOK_CONFIGS["taxable"])
        self.assertEqual(cb["exit_frac"], 0.30)
        self.assertIn("do NOT apply it again by hand", cb["band_note"])

    def test_an_unbanded_config_says_so_plainly(self):
        cb = VI.config_block("roth", S.BOOK_CONFIGS["roth"])
        self.assertIsNone(cb["exit_frac"])
        self.assertIn("no no-trade band", cb["band_note"])

    def test_measured_figures_are_published_with_the_width_they_were_measured_at(self):
        """`measured` was measured at 0.20 and the shipped width is 0.30. Publishing them side
        by side without saying so is how a stale figure travels."""
        cb = VI.config_block("taxable", S.BOOK_CONFIGS["taxable"])
        self.assertEqual(cb["measured_width"], 0.20)
        self.assertIn("not the 0.3 now shipped", cb["measured_width_note"])

    def test_no_config_means_an_empty_block_rather_than_a_stub(self):
        self.assertEqual(VI.config_block(None, None), {})


class TestTheVintageAndTheShadow(unittest.TestCase):
    def test_the_open_vintage_is_the_band_vintage(self):
        from valuation.edge import track_meter as TM
        cur = TM.current_vintage()
        self.assertEqual(cur["vintage"], 4)
        self.assertEqual(cur["opened"].isoformat(), "2026-08-13")
        self.assertIn("0.30", cur["label"])

    def test_the_label_is_derived_so_a_surface_cannot_drift_from_the_register(self):
        from valuation.edge import track_meter as TM
        lab = TM.vintage_label()
        self.assertEqual(lab["vintage"], TM.current_vintage()["vintage"])
        self.assertEqual(lab["shadow_vintage"], 3)
        self.assertIn("vintage 4 since 2026-08-13", lab["phrase"])
        self.assertIn("vintage 3 runs in shadow", lab["phrase"])

    def test_the_first_shadow_pair_is_open(self):
        """V1 shipped with no pair to measure. The band adoption opens the first one."""
        from valuation.edge import shadow_vintage as SV
        d = SV.detail()
        self.assertTrue(d["active"])
        self.assertEqual(d["n_pairs"], 1)
        self.assertEqual(d["pairs"][0]["live_vintage"], 4)
        self.assertEqual(d["pairs"][0]["shadow_vintage"], 3)

    def test_the_comparator_can_actually_see_the_band(self):
        """Without `no_trade_band` in PARAM_KEYS these two hash identically and the machinery
        reports 'no change' while the book demonstrably changed."""
        from valuation.edge import shadow_vintage as SV
        self.assertIn("no_trade_band", SV.PARAM_KEYS)
        self.assertFalse(SV.same_model(SV.PINNED[3]["snapshot"], SV.PINNED[4]["snapshot"]))

    def test_earlier_pins_are_not_retroactively_rewritten(self):
        """Adding a PARAM_KEY must not change a published params_id."""
        from valuation.edge import shadow_vintage as SV
        self.assertEqual(SV.PINNED[2]["snapshot"]["params_id"], "0060c5ef3dda")
        self.assertEqual(SV.PINNED[3]["snapshot"]["params_id"], "24878e43a1e3")
        self.assertNotIn("no_trade_band", SV.PINNED[3]["snapshot"]["params"])

    def test_the_pin_is_a_literal_but_must_match_the_adopted_width_today(self):
        """The pin is a LITERAL so a future width change cannot rewrite vintage 4's history.
        This asserts it is nonetheless correct NOW -- so changing the width without opening a
        vintage is loud rather than silent."""
        from valuation.edge import shadow_vintage as SV
        self.assertEqual(SV.PINNED[4]["snapshot"]["params"]["no_trade_band"], NTB.BAND_WIDTH)

    def test_only_one_key_separates_the_shadowed_pair(self):
        """The honest description of this adoption: it changes selection, not scoring."""
        from valuation.edge import shadow_vintage as SV
        a = SV.PINNED[3]["snapshot"]["params"]
        b = SV.PINNED[4]["snapshot"]["params"]
        diff = {k for k in set(a) | set(b) if a.get(k) != b.get(k)}
        self.assertEqual(diff, {"no_trade_band"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
