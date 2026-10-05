# -*- coding: utf-8 -*-
"""`INDEX-CHOICE-ARM4` — arm 4's checks, and the two things that must not happen.

**ANOTHER ITEM'S VOID CONDITION IS AT STAKE HERE, which is unusual and is the reason most of
this file exists.** `INDEX-CHOICE`'s register §6 condition 2 reads *"No new arm. Arms 1, 2, 3
only; arm 4 (the ceiling) is not carried into this item."* The obvious way to give arm 4 the same
checks is to add it to `index_choice_split.CHOICE` — which would **breach that condition and
silently change a landed artifact**. So the arm set became a parameter whose default is the
original tuple, and these tests pin both halves: the default is unchanged, and arm 4 is not in it.

The second thing that must not happen is arm 4 being quietly promoted. Its own register §1
pre-commits that **no figure here makes it a fourth option for 2026-10-22**, and the decision
memo's three-option table is the observable form of that.
"""
import ast
import inspect
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

from scripts import index_choice_split as S                               # noqa: E402
from scripts import index_choice_factors as F                             # noqa: E402
from scripts import index_choice_arm4 as A4                               # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL_CHOICE = ("1_incumbent_10bn", "2_liquid_decile", "3_liquid_top25")


class IndexChoicesVoidConditionIsRespected(unittest.TestCase):
    def test_arm_4_is_NOT_in_index_choices_own_arm_set(self):
        """Its register §6.2 forbids it, and the artifact would change."""
        self.assertEqual(tuple(S.CHOICE), ORIGINAL_CHOICE)
        self.assertNotIn(A4.ARM4, S.CHOICE)
        self.assertNotIn(A4.ARM4, F.CHOICE)

    def test_the_parameter_DEFAULTS_are_the_original_arm_set(self):
        """This is what makes the refactor inert for every existing caller BY CONSTRUCTION. The
        behavioural proof is the re-run that reproduced INDEX_CHOICE_SPLIT.json leaf by leaf;
        this is the structural half."""
        for fn in (S._score_half, S._shares):
            d = inspect.signature(fn).parameters["choice"].default
            self.assertEqual(tuple(d), ORIGINAL_CHOICE, "%s's default moved" % fn.__name__)
        self.assertEqual(tuple(inspect.signature(F.main).parameters["choice"].default),
                         ORIGINAL_CHOICE)

    def test_index_choices_factor_main_still_defaults_to_its_OWN_output_path(self):
        """`out=None` must fall back to INDEX-CHOICE's own file, or a caller that omits it
        writes somewhere else and the landed artifact silently stops being refreshed."""
        self.assertIsNone(inspect.signature(F.main).parameters["out"].default)
        src = io.open(os.path.join(REPO, "scripts", "index_choice_factors.py"),
                      encoding="utf-8").read()
        self.assertIn("out = out or OUT", src)
        self.assertEqual(src.count("with open(out,"), 1)
        self.assertEqual(src.count("with open(OUT,"), 0,
                         "the write path must honour the parameter, or arm 4 clobbers "
                         "INDEX_CHOICE_FACTORS.json")

    def test_index_choices_item_label_still_defaults_to_INDEX_CHOICE(self):
        self.assertEqual(inspect.signature(F.main).parameters["item"].default, "INDEX-CHOICE")


class Arm4WritesItsOwnArtifacts(unittest.TestCase):
    def test_the_split_leg_writes_a_distinct_file(self):
        if not A4.OUT or not S.OUT:
            self.skipTest("LOUD SKIP: no data root on this machine")
        self.assertNotEqual(os.path.abspath(A4.OUT), os.path.abspath(S.OUT))
        self.assertIn("ARM4", os.path.basename(A4.OUT))

    def test_the_factor_leg_asserts_it_is_not_writing_index_choices_file(self):
        """Read the source: the guard must be present, because the two paths differ by one word
        and a copy-paste would land on the wrong one."""
        src = io.open(os.path.join(REPO, "scripts", "index_choice_arm4_factors.py"),
                      encoding="utf-8").read()
        self.assertIn("assert out != F.OUT", src)


class TheArmSetCarriesTheIncumbent(unittest.TestCase):
    def test_CHOICE4_includes_the_incumbent(self):
        """The SECOND registered statistic is 'positive vs the INCUMBENT on the same half'.
        Without the incumbent in the arm set it cannot be computed at all, and the item would
        silently report only the vs-SPY leg."""
        self.assertIn("1_incumbent_10bn", A4.CHOICE4)
        self.assertIn(A4.ARM4, A4.CHOICE4)
        self.assertEqual(len(A4.CHOICE4), 2)


class C1GatesAndCannotPassVacuously(unittest.TestCase):
    def _fa(self, payload):
        d = tempfile.mkdtemp()
        if payload is not None:
            json.dump(payload, io.open(os.path.join(d, "INDEX_BEST.json"), "w",
                                       encoding="utf-8"))
        return d

    def test_an_absent_artifact_REFUSES_and_compares_nothing(self):
        g = A4.c1_reproduces_index_best(self._fa(None))
        self.assertFalse(g["ok"])
        self.assertEqual(g["compared"], 0)

    def test_an_artifact_without_arm_4_REFUSES(self):
        g = A4.c1_reproduces_index_best(self._fa({"arms": {"1_incumbent_10bn": {}}}))
        self.assertFalse(g["ok"])
        self.assertEqual(g["compared"], 0)

    def test_a_MOVED_banked_figure_REFUSES(self):
        """The whole point of the gate: arm 4's figures must be the ones INDEX-BEST banked."""
        g = A4.c1_reproduces_index_best(
            self._fa({"arms": {A4.ARM4: {"roth_net_ann": 0.2495}}}))
        self.assertFalse(g["ok"], "a changed banked figure must not pass")

    def test_the_exact_banked_figure_passes_and_compares_SOMETHING(self):
        g = A4.c1_reproduces_index_best(
            self._fa({"arms": {A4.ARM4: {"roth_net_ann": A4.BANKED_ROTH_NET_ANN}}}))
        self.assertTrue(g["ok"])
        self.assertGreater(g["compared"], 0,
                           "MB21's C1 once scored a perfect zero by comparing nothing")
        self.assertEqual(g["max_abs_dev"], 0.0)

    def test_the_quoted_figure_matches_the_real_banked_artifact(self):
        """A quoted constant that has drifted from the artifact is worse than no constant."""
        for c in (os.environ.get("VALQUO_DATA_ROOT"),
                  os.path.join(REPO, "data"),
                  r"C:\Users\donni\Downloads\valuation-tool\data"):
            if not c:
                continue
            p = os.path.join(c, "free_analysis", "INDEX_BEST.json")
            if os.path.exists(p):
                arm = json.load(io.open(p, encoding="utf-8"))["arms"][A4.ARM4]
                self.assertEqual(float(arm["roth_net_ann"]), A4.BANKED_ROTH_NET_ANN)
                return
        self.skipTest("LOUD SKIP: INDEX_BEST.json is not on this machine")


class Arm4StaysACeiling(unittest.TestCase):
    def test_the_runner_says_so_in_its_own_artifact_payload(self):
        src = io.open(os.path.join(REPO, "scripts", "index_choice_arm4.py"),
                      encoding="utf-8").read()
        self.assertIn('"arm_is_a_ceiling_not_an_option": True', src)

    def test_the_decision_memo_still_offers_THREE_options_not_four(self):
        """§1's void condition in its observable form. If arm 4 ever appears as a fourth
        OPTION in Don's table, this item has been misused."""
        p = os.path.join(REPO, "DECISION_index_choice.md")
        if not os.path.exists(p):
            self.skipTest("LOUD SKIP: the memo is not in this tree")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("The three options, side by side", src)
        self.assertNotIn("4_all_cap_ceiling", src)

    def test_the_register_exists_and_pre_commits_the_ceiling_label(self):
        p = os.path.join(REPO, "PREREG_index_choice_arm4.md")
        self.assertTrue(os.path.exists(p), "the register must be on disk to be checkable")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("REMAINS A CEILING", src)
        self.assertIn("ONE EQUITY TRIAL", src)


class AnAbsoluteRankTrimIsInvisibleOnAHalfUniverse(unittest.TestCase):
    """THE FINDING THIS ITEM ACTUALLY PRODUCED, and it is a correction to a LANDED item.

    Arm 2 and arm 4 differ by exactly one keyword: `universe_rank=1500` against `None`. On the
    FULL panel that trim binds on 66 of 69 dates (median 1,557 names per date). On a HALF
    universe there are only ~785 names per date, so **it binds on 0 of 69** and arm 2 collapses
    into arm 4.

    Measured consequence: every one of arm 4's 200 half-book statistics came back **bit-identical**
    to arm 2's, and the two stable-split levels agree to 16 significant figures. So
    `INDEX-CHOICE`'s headline *"arm 2 beats the incumbent on 200 of 200 half-books"* is evidence
    about **a wider-pool decile**, not about the 1,500-name liquidity trim that defines arm 2.

    THE PORTABLE RULE: **a universe filter expressed as an ABSOLUTE RANK is not invariant to
    subsampling the universe**, so `X1`'s name-split method cannot evaluate one. A RELATIVE
    filter (a top decile) scales with the population and can be. Any future arm whose universe
    is defined by an absolute count inherits this and must say so.
    """

    def test_the_two_arms_differ_by_exactly_one_keyword(self):
        from scripts.index_best import ARMS
        kw = {n: k for n, k, _l, _b in ARMS}
        a2, a4 = dict(kw["2_liquid_decile"]), dict(kw[A4.ARM4])
        diff = {k for k in set(a2) | set(a4) if a2.get(k) != a4.get(k)}
        self.assertEqual(diff, {"universe_rank"})
        self.assertEqual(a2["universe_rank"], 1500)
        self.assertIsNone(a4["universe_rank"])

    def test_the_trim_binds_on_the_full_panel_and_NOT_on_a_half(self):
        """The measurement, re-derived rather than quoted. Skips loudly without the panel."""
        import pandas as pd
        from scripts.r4_x1_accounting_universe import stable_key_half
        if not A4.FA or not os.path.exists(os.path.join(A4.FA, "panel_corrected_69d.pkl")):
            self.skipTest("LOUD SKIP: the licensed panel is not on this machine")
        p = pd.read_pickle(os.path.join(A4.FA, "panel_corrected_69d.pkl"))
        full = p.groupby("date")["ticker"].nunique()
        half_names = [t for t in sorted(p["ticker"].unique()) if stable_key_half(t) == 0]
        half = p[p["ticker"].isin(half_names)].groupby("date")["ticker"].nunique()
        self.assertGreater(int((full > 1500).sum()), 60,
                           "the trim must bind on most FULL dates or arm 2 is not a trim")
        self.assertEqual(int((half > 1500).sum()), 0,
                         "if the trim ever binds on a half, this finding needs re-deriving")

    def test_the_two_arms_half_book_statistics_are_IDENTICAL(self):
        """The consequence, read off the two artifacts. This is what makes it a finding rather
        than a worry: they are not merely close, they are equal."""
        if not A4.FA:
            self.skipTest("LOUD SKIP: no data root")
        pa = os.path.join(A4.FA, "INDEX_CHOICE_ARM4.json")
        pi = os.path.join(A4.FA, "INDEX_CHOICE_SPLIT.json")
        if not (os.path.exists(pa) and os.path.exists(pi)):
            self.skipTest("LOUD SKIP: an artifact is absent")
        a = json.load(io.open(pa, encoding="utf-8"))
        i = json.load(io.open(pi, encoding="utf-8"))
        s4 = a["random_splits"]["shares"][A4.ARM4]
        s2 = i["random_splits"]["shares"]["2_liquid_decile"]
        self.assertEqual(s4, s2,
                         "arm 2 and arm 4 no longer agree on halves -- the mechanism changed "
                         "and the write-up needs re-deriving")
        self.assertEqual([h["arms"][A4.ARM4] for h in a["stable_split"]["per_half"]],
                         [h["arms"]["2_liquid_decile"] for h in i["stable_split"]["per_half"]])

    def test_the_decision_memo_carries_the_correction(self):
        """Don reads that memo on 2026-10-22. A finding that invalidates how one of its rows
        should be read has to be IN it, not only in a handoff."""
        p = os.path.join(REPO, "DECISION_index_choice.md")
        if not os.path.exists(p):
            self.skipTest("LOUD SKIP: the memo is not in this tree")
        src = io.open(p, encoding="utf-8").read()
        self.assertIn("absolute rank", src.lower())
        self.assertIn("0 of 69", src)


class TheMethodIsImportedNotRetyped(unittest.TestCase):
    @staticmethod
    def _imported(path):
        tree = ast.parse(io.open(path, encoding="utf-8").read())
        names = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom):
                if n.module:
                    names.add(n.module)
                names.update(a.name for a in n.names)       # `from x import y` puts y HERE
            elif isinstance(n, ast.Import):
                names.update(a.name for a in n.names)
        return names

    def test_arm4_imports_X1s_keys_and_index_choices_scorers(self):
        got = self._imported(os.path.join(REPO, "scripts", "index_choice_arm4.py"))
        for want in ("stable_key_half", "SEED", "K_SPLITS", "_assert_split",
                     "_score_half", "_shares", "_spy_ann"):
            self.assertIn(want, got, "%s must be IMPORTED, not retyped (B7, MA5)" % want)

    def test_arm4_does_not_restate_X1s_seed_or_split_count_as_literals(self):
        tree = ast.parse(io.open(os.path.join(REPO, "scripts", "index_choice_arm4.py"),
                                 encoding="utf-8").read())
        lits = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, int)
                and not isinstance(n.value, bool)}
        from scripts.r4_x1_accounting_universe import K_SPLITS, SEED
        self.assertNotIn(SEED, lits, "X1's seed is restated as a literal")
        # K_SPLITS is 100; a bare 100 would be ambiguous, so only the seed is banned by value
        self.assertIsInstance(K_SPLITS, int)


if __name__ == "__main__":
    unittest.main(verbosity=2)
