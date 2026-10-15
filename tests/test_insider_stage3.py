# -*- coding: utf-8 -*-
"""`INSIDER-STAGE3` — the older-data rung's feasibility, the live feed, and F-23's declaration.

Nothing here needs the licensed export or a banked panel, so none of it fails open on a CI runner
(`guards-that-fail-open-in-ci`) — and nothing here is allowed to take the suite down either, which
is the inverse failure this lane shipped one item ago (`except Exception` not catching a refusing
resolver's `SystemExit`).
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.edge import fleet as FL                                      # noqa: E402
from valuation.edge import track_meter as TM                                # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK = "f23_insider_cluster_shares"
DECL = os.path.join(REPO, "DECL_%s.md" % BOOK)


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


def _tree(rel):
    return ast.parse(_src(rel))


def _decl():
    p = FL.parse_declaration(_src("DECL_%s.md" % BOOK))
    assert p["ok"], p.get("reason")
    return p["declaration"]


class TheDeclarationIsValidAndCameAlone(unittest.TestCase):
    def test_the_file_exists(self):
        self.assertTrue(os.path.isfile(DECL), DECL)

    def test_it_parses_and_validates_with_zero_refusals(self):
        r = FL.validate_declaration(_decl(), book=BOOK)
        self.assertTrue(r["ok"], "refusals: %s" % r["refusals"])
        self.assertEqual(r["refusals"], [])

    def test_it_was_committed_alone(self):
        """The harness's own declaration-before-fill rule: the introducing commit must exist, be
        an ancestor of HEAD, and have touched EXACTLY ONE file."""
        try:
            out = subprocess.run(["git", "log", "--format=%H", "-n", "40", "--", DECL],
                                 cwd=REPO, capture_output=True).stdout.decode("utf-8")
        except Exception as e:                                              # noqa: BLE001
            self.skipTest("git unavailable: %r" % (e,))
        shas = [x for x in out.split() if x]
        if not shas:
            self.skipTest("declaration not in this checkout's history")
        files = subprocess.run(["git", "show", "--name-only", "--format=", shas[-1]],
                               cwd=REPO, capture_output=True).stdout.decode("utf-8").split()
        self.assertEqual([f for f in files if f.strip()], ["DECL_%s.md" % BOOK])

    def test_the_o11_sentence_is_verbatim(self):
        self.assertEqual(_decl()["o11_sentence"], FL.O11_SENTENCE)

    def test_it_is_a_long_equity_shares_book_that_sells_no_premium(self):
        d = _decl()
        self.assertEqual(d["domain"], "equity")
        self.assertEqual(d["side"], "long")
        self.assertIs(d["sells_premium"], False)
        self.assertIn("shares", d["structure"]["instrument"])

    def test_it_is_the_fleets_first_equity_book_and_says_why_strike_selection_is_fixed(self):
        """Reported rather than edited: `validate_declaration` REQUIRES an option-shaped
        `strike_selection`, and a shares book has no strike. The field carries the reason."""
        d = _decl()
        self.assertEqual(d["structure"]["strike_selection"], "fixed")
        self.assertIn("NO STRIKE", d["structure"]["strike_selection_note"])

    def test_the_trial_is_charged_at_the_first_verdict_read_and_not_now(self):
        d = _decl()
        self.assertEqual(d["trial"]["charged_at"], "first_verdict_read")
        self.assertEqual(d["trial"]["domain"], "equity")


class TheHorizonIsDerivedAndNotRound(unittest.TestCase):
    def test_fills_needed_is_the_boundary_crossing_and_not_a_round_number(self):
        h = _decl()["verdict_horizon"]
        n, sg, rho, al = int(h["fills_needed"]), float(h["sigma"]), float(h["rho"]), \
            float(h["alpha"])
        mei = float(h["min_effect"])
        self.assertLessEqual(TM.boundary(n, sigma=sg, rho=rho, alpha=al) / n, mei)
        self.assertGreater(TM.boundary(n - 1, sigma=sg, rho=rho, alpha=al) / (n - 1), mei,
                           "n-1 must NOT already clear, or fills_needed is not the crossing")
        self.assertNotEqual(n % 10, 0, "a multiple of ten is the round number this forbids")

    def test_the_min_effect_is_NET_of_cost_and_not_gross(self):
        """A gross bar would let the book pass while losing money."""
        h = _decl()["verdict_horizon"]
        self.assertAlmostEqual(float(h["min_effect"]), 2.9122, places=4)
        self.assertIn("NET", h["min_effect_basis"])

    def test_sigma_is_measured_and_may_only_be_raised(self):
        h = _decl()["verdict_horizon"]
        self.assertIn("MEASURED", h["sigma_provenance"])
        self.assertTrue(h["sigma_may_only_be_raised"])
        self.assertGreater(float(h["sigma"]), 0)

    def test_the_concurrency_cap_does_not_bind_the_construction(self):
        """A 63-session hold on the declared event rate implies ~77.5 expected concurrent
        positions. A cap below that REFUSES events, and the register's result is measured on ALL
        events — so a binding cap would make this book a different construction."""
        d = _decl()
        h = d["verdict_horizon"]
        per_year = float(h["expected_fills_per_month"]) * 12.0
        hold_years = float(d["structure"]["horizon_sessions"]) / 252.0
        expected_concurrent = per_year * hold_years
        self.assertGreaterEqual(int(d["concurrency_cap"]), expected_concurrent,
                                "cap %s binds against %.1f expected concurrent"
                                % (d["concurrency_cap"], expected_concurrent))

    def test_the_horizon_carries_the_eras_own_optimism_warning(self):
        self.assertIn("1.41x", _decl()["verdict_horizon"]["power_gate_note"])


class TheCaveatsAreInTheDeclarationNotInAHandoff(unittest.TestCase):
    def test_the_late_half_nets_about_zero_and_the_declaration_says_so(self):
        t = _src("DECL_%s.md" % BOOK)
        self.assertIn("2023-2026", t)
        self.assertIn("0.045pp net", t)
        self.assertIn("BLEEDS", t)

    def test_it_refuses_to_narrow_to_the_band_the_diagnostic_favours(self):
        t = _src("DECL_%s.md" % BOOK)
        self.assertIn("does NOT narrow", t)

    def test_the_void_conditions_include_backfill_and_a_real_order(self):
        t = _src("DECL_%s.md" % BOOK)
        self.assertIn("Backfill", t)
        self.assertIn("real order at a broker", t)


class TheFeedIsNotValidatedSoTheBookCannotFill(unittest.TestCase):
    def test_the_bars_are_declared_in_the_module_before_any_comparison(self):
        from scripts import insider_live_feed as LF
        self.assertEqual(LF.ROW_RECALL_BAR, 0.95)
        self.assertEqual(LF.EVENT_JACCARD_BAR, 0.90)

    def test_the_declaration_cites_those_same_bars(self):
        t = _src("DECL_%s.md" % BOOK)
        self.assertIn("0.95", t)
        self.assertIn("0.90", t)
        self.assertIn("NO FILL UNTIL THE FEED PASSES", t)

    def test_the_feed_module_places_no_order_and_has_no_other_mode(self):
        tree = _tree("scripts/insider_live_feed.py")
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("place_equity_order", "place_option_order", "submit_order", "record"):
            self.assertNotIn(banned, names, "the feed module must not %s" % banned)

    def test_the_name_key_is_not_a_tunable_fuzzy_match(self):
        """A threshold-based name matcher would turn a feed disagreement into a parameter, and
        the bar is declared before the run."""
        from scripts import insider_live_feed as LF
        self.assertEqual(LF._norm_name("Smith, John A."), "SMITH JOHN A")
        self.assertEqual(LF._norm_name("  smith   john  a  "), "SMITH JOHN A")
        tree = _tree("scripts/insider_live_feed.py")
        names = {n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        for banned in ("ratio", "partial_ratio", "token_sort_ratio", "get_close_matches"):
            self.assertNotIn(banned, names)

    def test_the_harness_itself_also_refuses_the_fill(self):
        """A SECOND, independent block: Don's ruling that no book fills until the harness passes
        its own day-1 self-check. Belt and braces, and it is the harness's refusal rather than
        this lane's."""
        r = FL.may_fill(BOOK)
        self.assertFalse(r["ok"])
        self.assertTrue(str(r.get("code") or "").strip())


class TheFeasibilityPassReadsNoOutcome(unittest.TestCase):
    def test_no_forward_return_is_loaded_anywhere_in_the_feasibility_scripts(self):
        for rel in ("scripts/insider_stage3_feasibility.py",
                    "scripts/insider_stage3_sec_size.py",
                    "scripts/insider_live_feed.py"):
            tree = _tree(rel)
            bad = [n for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)
                   and n.value in ("fwd_ret", "fwd_ret_h63")]
            self.assertEqual(bad, [], "%s names a forward-return column" % rel)

    def test_that_check_is_not_vacuous(self):
        probe = ast.parse('X = frame["fwd_ret"]')
        bad = [n for n in ast.walk(probe)
               if isinstance(n, ast.Constant) and n.value == "fwd_ret"]
        self.assertTrue(bad)

    def test_the_first_emittable_year_is_derived_from_two_columns_not_one(self):
        """An event is dated at the LAST FILING while `prior_year_presence` keys on TRANSACTION
        years, so the answer is `max(first_filing_year, first_transaction_year + 2)` and reading
        only one column gets it wrong."""
        from scripts import insider_stage3_feasibility as FS
        got = FS.first_emittable({"filing_year_counts": {"2008": 1},
                                  "transaction_year_counts": {"1988": 1}})
        self.assertEqual(got["first_emittable_year"], 2008)
        self.assertIn("FILING floor", got["which_constraint_binds"])
        got2 = FS.first_emittable({"filing_year_counts": {"2006": 1},
                                   "transaction_year_counts": {"2006": 1}})
        self.assertEqual(got2["first_emittable_year"], 2008)
        self.assertIn("two-prior-TRANSACTION-year", got2["which_constraint_binds"])

    def test_the_sec_size_counter_refuses_a_zero_rather_than_reporting_it(self):
        """Its first cut counted ZERO Form 4s across four years and said so, because `form.idx`
        is fixed-width and it split on pipes. A control form's count of zero is a PARSER failure."""
        from scripts import insider_stage3_sec_size as SZ
        self.assertEqual(SZ._CONTROL_FORMS, ("8-K", "10-Q"))
        self.assertIn("master.zip", SZ.BASE)
        self.assertNotIn("form.zip", SZ.BASE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
