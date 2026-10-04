# -*- coding: utf-8 -*-
"""INDEX-CHOICE -- tests for the name split, the buildability control and the decomposition.

The load-bearing ones:

 1. **X1's method is IMPORTED, not restated.** It is the blindness argument for the whole item:
    the key, the seed and the split count were fixed in August before arms 2 and 3 existed. A
    local copy would let a successor silently change one.
 2. **Each half is REBUILT within the half** -- universe trim and standardisation both. Scoring
    a half against full-universe z-scores would measure neither thing.
 3. **D9's 60% bar is reused verbatim and never relaxed**, and the control reproduces D9's own
    published figure, which is what makes the top-25 number D9's measurement extended rather
    than a lookalike.
 4. **No alpha verdict** may be taken from the factor regression, per the register.
 5. **Importing any of it must not require the licensed panel** -- the CI-only failure
    `INDEX-BEST` shipped once already.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import numpy as np                                                      # noqa: E402
import pandas as pd                                                     # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPLIT = os.path.join(REPO, "scripts", "index_choice_split.py")
BUILD = os.path.join(REPO, "scripts", "index_choice_buildable.py")
FACT = os.path.join(REPO, "scripts", "index_choice_factors.py")
REGISTER = os.path.join(REPO, "PREREG_index_choice.md")
MEMO = os.path.join(REPO, "DECISION_index_choice.md")


def _src(p):
    return io.open(p, encoding="utf-8").read()


class X1sMethodIsInheritedNotRestated(unittest.TestCase):
    """The blindness argument. If these are local copies, a successor can change one."""

    def test_the_key_the_seed_and_the_split_count_are_imported_from_X1(self):
        tree = ast.parse(_src(SPLIT))
        got = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and "r4_x1_accounting_universe" in (n.module or ""):
                for a in n.names:
                    got[a.asname or a.name] = True
        for must in ("stable_key_half", "SEED", "K_SPLITS", "_assert_split"):
            self.assertIn(must, got, "%s must be IMPORTED from X1, not restated" % must)

    def test_no_local_copy_of_the_seed_or_split_count_is_assigned(self):
        tree = ast.parse(_src(SPLIT))
        assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign)
                    for t in n.targets if isinstance(t, ast.Name)}
        for banned in ("SEED", "K_SPLITS"):
            self.assertNotIn(banned, assigned,
                             "%s is assigned locally, which lets it drift from X1" % banned)

    def test_the_imported_values_are_the_ones_X1_registered(self):
        from scripts.r4_x1_accounting_universe import K_SPLITS, SEED, stable_key_half
        self.assertEqual(SEED, 20260813)
        self.assertEqual(K_SPLITS, 100)
        # the key is seedless and order-free: the same ticker always lands in the same half
        self.assertEqual(stable_key_half("AAPL"), stable_key_half("AAPL"))
        self.assertIn(stable_key_half("AAPL"), (0, 1))

    def test_X1s_own_split_control_bites_and_is_called_not_reimplemented(self):
        """`_assert_split` is X1's C2. Exercised on a PERMUTATION split, where exact balance is
        guaranteed by construction -- see the next test for why a HASH split is different."""
        import numpy as _np
        from scripts.r4_x1_accounting_universe import _assert_split
        u = ["T%04d" % i for i in range(2000)]
        perm = list(_np.random.default_rng(0).permutation(u))
        a, b = sorted(perm[:1000]), sorted(perm[1000:])
        _assert_split(a, b, u)
        with self.assertRaises(AssertionError):
            _assert_split(a, b[:-5], u)             # positive control: it must bite
        with self.assertRaises(AssertionError):
            _assert_split(a, a, u)                  # and on overlap

    def test_X1s_balance_assertion_is_only_APPROXIMATELY_true_of_a_HASH_split(self):
        """REPORTED, NOT FIXED, and it is X1's lane (`RUN_RULES` rule 3).

        `_assert_split` asserts `abs(len(A) - len(B)) <= 1`. That is GUARANTEED for a random
        permutation split and is NOT guaranteed for a sha1 % 2 split, which is only
        approximately balanced. On the real 2,531-name universe the hash lands at 1266/1265 and
        passes -- BY LUCK OF THIS UNIVERSE. On synthetic universes of 500/1000/2000/5000 it
        differs by 36/22/22/16 and X1's own control would FAIL on a correct split. So if the
        panel's universe changes, X1's stable split can fail its own assertion for no
        substantive reason. This item's own run asserted it and PASSED, so nothing here rests
        on it."""
        from scripts.r4_x1_accounting_universe import stable_key_half
        u = ["T%04d" % i for i in range(2000)]
        a = sum(1 for t in u if stable_key_half(t) == 0)
        self.assertGreater(abs(2 * a - len(u)), 1,
                           "if a hash split were exactly balanced this report would be wrong")

    def test_arm4_the_ceiling_is_not_carried_into_this_item(self):
        from scripts.index_choice_split import CHOICE
        self.assertEqual(len(CHOICE), 3)
        self.assertNotIn("4_all_cap_ceiling", CHOICE,
                         "void condition 2: the ceiling arm is not carried in")


class EachHalfIsRebuiltWithinTheHalf(unittest.TestCase):
    def test_the_half_is_scored_on_a_subset_frame_not_the_full_panel(self):
        """The trim and the z-scores are properties of the POPULATION. Pinned by shape: the
        scorer must filter the panel to the half's names before scoring it."""
        tree = ast.parse(_src(SPLIT))
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "_score_half")
        src = ast.unparse(fn)
        self.assertIn("isin(names)", src,
                      "the half must be scored on its own rows")
        self.assertIn("sub", src)

    def test_a_half_below_the_name_floor_is_refused_rather_than_scored(self):
        from scripts.index_choice_split import MIN_NAMES_PER_HALF, _score_half
        self.assertGreaterEqual(MIN_NAMES_PER_HALF, 400)
        p = pd.DataFrame({"date": ["2010-01-15"] * 5, "ticker": list("ABCDE"),
                          "market_cap": [1e9] * 5, "fwd_ret": [0.01] * 5,
                          "bench_ret": [0.01] * 5})
        self.assertIsNone(_score_half(p, list("ABCDE"), [], {}),
                          "a half below the floor must return None, not a number")

    def test_the_incumbent_paired_against_itself_is_identically_zero(self):
        """The control that proves the pairing is PER HALF. If the incumbent were taken from
        the full universe, this would not be zero."""
        from scripts.index_choice_split import _shares
        halves = [{"spy_ann": 0.1, "arms": {"1_incumbent_10bn": {"roth_ann": 0.2},
                                            "2_liquid_decile": {"roth_ann": 0.3},
                                            "3_liquid_top25": {"roth_ann": 0.25}}},
                  {"spy_ann": 0.1, "arms": {"1_incumbent_10bn": {"roth_ann": 0.15},
                                            "2_liquid_decile": {"roth_ann": 0.1},
                                            "3_liquid_top25": {"roth_ann": 0.4}}}]
        s = _shares(halves)
        self.assertEqual(s["1_incumbent_10bn"]["vs_incumbent"]["median"], 0.0)
        self.assertTrue(s["control_incumbent_vs_itself_is_zero"])
        # and the shares are computed per half, not pooled
        self.assertAlmostEqual(s["2_liquid_decile"]["vs_incumbent"]["share_positive"], 0.5)
        self.assertAlmostEqual(s["3_liquid_top25"]["vs_incumbent"]["share_positive"], 1.0)


class TheBuildabilityBarIsD9sAndIsNotRelaxed(unittest.TestCase):
    def test_the_bar_is_sixty_percent_and_is_attributed_to_D9(self):
        from scripts.index_choice_buildable import D9_BAR
        self.assertEqual(D9_BAR, 0.60)
        self.assertIn("reused verbatim", _src(BUILD))

    def test_the_control_compares_against_D9s_published_figure(self):
        from scripts.index_choice_buildable import (D9_PUBLISHED_DECILE_OVERLAP,
                                                    D9_PUBLISHED_LL_SPEARMAN)
        # the literals must be D9's, to the digit, or the control proves nothing
        self.assertEqual(D9_PUBLISHED_DECILE_OVERLAP, 0.23255813953488372)
        self.assertEqual(D9_PUBLISHED_LL_SPEARMAN, 0.43211493611995416)

    def test_the_overlap_arithmetic_is_right_and_denominated_on_k(self):
        from scripts.index_choice_buildable import _overlap
        a = ["A", "B", "C", "D"]
        b = ["C", "D", "E", "F"]
        self.assertEqual(_overlap(a, b, 2), 0.0)
        self.assertEqual(_overlap(a, b, 4), 0.5)
        self.assertEqual(_overlap(a, a, 4), 1.0)

    def test_arm3s_book_size_is_the_one_INDEX_BEST_measured(self):
        from scripts.index_choice_buildable import ARM3_BOOK
        from scripts.index_best import CONCENTRATED_N
        self.assertEqual(ARM3_BOOK, CONCENTRATED_N,
                         "the top-25 cut must be the same 25 INDEX-BEST scored")

    def test_the_verdict_is_a_refusal_not_a_preference(self):
        src = _src(BUILD)
        self.assertIn("arm3_buildable_by_path_A", src)
        self.assertIn(">= D9_BAR", src)
        self.assertNotIn("0.5", src.split("D9_BAR = ")[1][:40],
                         "the bar must not be softened near its definition")


class TheFactorPassTakesNoAlphaVerdict(unittest.TestCase):
    def test_R1s_machinery_is_called_not_reimplemented(self):
        tree = ast.parse(_src(FACT))
        # `from scripts import factor_alpha as FAC` puts the module in `names`, not in
        # `n.module` -- the first cut of this guard looked only at `n.module` and FAILED
        # against a correct tree. The wrong-object family.
        seen = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                seen.add(n.module or "")
                seen |= {a.name for a in n.names}
            elif isinstance(n, ast.Import):
                seen |= {a.name for a in n.names}
        self.assertTrue(any("factor_alpha" in x for x in seen),
                        "the estimator and factor windows must come from R1 (B7)")
        src = _src(FACT)
        for name in ("ols_nw", "regress", "factor_windows", "FF_MODEL"):
            self.assertIn(name, src)

    def test_no_local_ols_or_newey_west_is_defined(self):
        tree = ast.parse(_src(FACT))
        defs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for banned in ("ols_nw", "ols", "newey_west", "regress"):
            self.assertNotIn(banned, defs,
                             "%s is defined locally; R1's one definition must be called" % banned)

    def test_the_source_says_the_intercept_is_not_alpha(self):
        src = _src(FACT)
        self.assertIn("no_alpha_verdict", src)
        self.assertIn("DECOMPOSITION", src.upper())

    def test_the_alignment_control_exists_and_is_R1s(self):
        src = _src(FACT)
        self.assertIn("alignment_control", src)
        self.assertIn("spy_on_mkt_beta", src)

    def test_the_lag_is_R1s_choice_of_one(self):
        from scripts.index_choice_factors import LAG
        self.assertEqual(LAG, 1)


class TheRegisterAndMemoAreHonoured(unittest.TestCase):
    def test_the_register_is_on_disk_and_forbids_a_re_pick(self):
        self.assertTrue(os.path.exists(REGISTER))
        s = _src(REGISTER)
        self.assertIn("No re-pick", s)
        self.assertIn("UNCALIBRATED", s.upper())

    def test_the_memo_quotes_the_fixed_sentence_and_the_derived_vintage(self):
        # NORMALISED: the memo is hard-wrapped, so a phrase can straddle a newline. A raw
        # substring search fails against a correct document -- found by this guard doing it.
        s = " ".join(_src(MEMO).split())
        for must in ("in-sample", "net of modelled trading costs",
                     "not statistically separable", "vintage 5",
                     "CONTRACT_MIN_POSITIONS"):
            self.assertIn(must, s, "the memo must carry %r" % must)

    def test_the_memo_states_which_case_the_recommendation_is(self):
        """The register requires the memo to say whether a recommendation is made."""
        s = _src(MEMO).upper()
        self.assertIn("THE EVIDENCE IS CLEAR", s)
        self.assertIn("DOES NOT DECIDE", s)

    def test_the_memo_names_the_period_caveat_rather_than_burying_it(self):
        s = _src(MEMO)
        self.assertIn("late half", s)
        self.assertIn("possibly still a period artifact", s)

    def test_the_trial_charge_matches_the_register(self):
        from scripts.index_choice_split import main as _m  # noqa: F401
        self.assertIn('"trials": 2', _src(SPLIT))
        self.assertIn('"trials": 0', _src(BUILD))
        self.assertIn('"trials": 1', _src(FACT))


class ImportingDoesNotRequireLicensedData(unittest.TestCase):
    """The CI-only failure INDEX-BEST shipped once. Pinned for all three scripts."""

    def test_every_module_level_data_root_uses_the_non_raising_form(self):
        for p in (SPLIT, BUILD, FACT):
            tree = ast.parse(_src(p))
            found = False
            for n in tree.body:
                if not isinstance(n, ast.Assign):
                    continue
                if not any(isinstance(t, ast.Name) and t.id == "DATA" for t in n.targets):
                    continue
                found = True
                self.assertIsInstance(n.value, ast.Call)
                kw = {k.arg: getattr(k.value, "value", None) for k in n.value.keywords}
                self.assertIs(kw.get("required"), False,
                              "%s resolves the data root in the RAISING form at import time"
                              % os.path.basename(p))
            self.assertTrue(found, "no module-level DATA assignment in %s" % p)

    def test_each_main_refuses_loudly_when_the_panel_is_absent(self):
        for p in (SPLIT, BUILD, FACT):
            s = _src(p)
            self.assertIn("if not FA:", s, os.path.basename(p))
            self.assertIn("the licensed panel is absent", s, os.path.basename(p))


if __name__ == "__main__":
    unittest.main(verbosity=2)
