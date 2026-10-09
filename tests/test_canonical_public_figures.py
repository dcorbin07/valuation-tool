# -*- coding: utf-8 -*-
"""`DECISION_canonical_move.md` steps 3 and 5 — a public figure may not be mislabelled by the move.

Two surfaces, one property: **a figure and the stamp saying which universe it describes must move
together.** The canonical move changes the panel under both, and each fails differently.

**1. `settings.measured()` — THE READ-THROUGH, AND THE LIVE DEFECT.** `MC11` removed the figure
literals from `BOOK_CONFIGS` because *"a second copy of a measured number is a copy that goes
stale"*, so the figures now come out of `BACKTEST_RESULTS.json` at request time and reach the
public landing page through `index_track.backtested`. **But their provenance was still typed** —
`n_dates = 69`, `n_names = 2531` — so the canonical re-run would have reported corrected figures
from a 9,645-name panel under a 2,531-name stamp. A wrong figure invites checking; a wrong label
makes a right figure unverifiable. **Both are now derived from the same blob the function already
opens**, with no fallback, per that module's own rule: *"An absent artifact returns nothing, not
the old literals."*

**2. `research_record` — THE COMMITTED PAIR.** The page compares a headline statistic against a
calibrated floor and renders only the COMPARISON (`MB38`). It cannot derive either at render time
— `data/` never ships — so both stay committed literals and **the DRIFT is what gets pinned**
(`MA13`'s idiom). The invariant is NOT *"the floor equals the corrected floor"*, which would be a
clock red for the whole interval between this register landing and the app lane updating the page.
It is the property `MA19` names as this record's recurring defect, *"a numerator at one `N` paired
with a floor at another"*:

    THE HEADLINE STATISTIC AND THE PLACEBO FLOOR MUST COME FROM THE SAME PANEL.

That passes before the hand-off and after it, and **fails only on a half-done update** — which is
the one failure a hand-off between two lanes produces and nothing else would catch.

Run as its own process and judged by exit code, per `RUN_RULES`.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETTINGS_SRC = os.path.join(ROOT, "valuation", "screener", "settings.py")
ARTIFACT = os.path.join(ROOT, "BACKTEST_RESULTS.json")

from valuation.screener import settings as S                                 # noqa: E402
from valuation.web import research_record as RR                              # noqa: E402

#: the 2,531-name panel's pair, as published. Committed literals, both, so a drift in either
#: shows up here as a diff (`MA13`).
PUBLISHED_HEADLINE = 2.6199121240414884
PUBLISHED_FLOOR = 2.2837

FLOOR_KEY = "long_short_tstat_nw"


def _fa():
    """The licensed data root, or None. RETURNS A STATE rather than raising — a helper that
    reports its own inability by raising turns every caller into a crash where the data is
    absent, which is the 'fails open in CI' family one level down."""
    try:
        from scripts.index_best import _data_root
        d = _data_root(required=False)
    except Exception:
        return None
    if not d:
        return None
    p = os.path.join(d, "free_analysis")
    return p if os.path.isdir(p) else None


def _corrected_pair():
    """(headline, floor) for the corrected universe, read from the two landed artifacts."""
    fa = _fa()
    if not fa:
        return None
    fp, dp = (os.path.join(fa, "CORRECTED_FLOORS.json"),
              os.path.join(fa, "CORRECTED_DEPLOYED.json"))
    if not (os.path.exists(fp) and os.path.exists(dp)):
        return None
    with io.open(fp, encoding="utf-8") as fh:
        floors = json.load(fh).get("floors") or []
    rec = next((f for f in floors if f.get("key") == FLOOR_KEY), None)
    with io.open(dp, encoding="utf-8") as fh:
        dep = json.load(fh).get("deployed") or {}
    if not rec or dep.get(FLOOR_KEY) is None:
        return None
    return (float(dep[FLOOR_KEY]), float(rec["corrected"]))


# =============================================================================================
class TheReadThroughCarriesTheArtifactsOwnUniverse(unittest.TestCase):
    """`settings.measured()` — the figures and their provenance come from ONE blob."""

    def test_the_universe_stamp_is_not_a_literal_in_the_source(self):
        """Read the SYNTAX TREE, not the text. A comment explaining why 2,531 was wrong quotes
        2,531, and a substring ban would fire on the explanation — this record's single most
        repeated guard defect."""
        tree = ast.parse(io.open(SETTINGS_SRC, encoding="utf-8").read())
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "measured"), None)
        self.assertIsNotNone(fn, "settings.measured() is gone; this guard has no subject")
        banned = {2531, 69}
        found = [n.value for n in ast.walk(fn)
                 if isinstance(n, ast.Constant) and isinstance(n.value, int)
                 and n.value in banned]
        self.assertFalse(found,
                         "measured() types a universe size or date count (%r). The figures are "
                         "read through from the artifact; their provenance must be too, or a "
                         "corrected figure ships under a stale stamp." % (found,))

    def test_the_stamp_matches_the_artifact_it_reads(self):
        got = S.measured("roth") or {}
        if got.get("unavailable"):
            print("SKIP: %s" % got["unavailable"])
            raise unittest.SkipTest("no canonical artifact on this host")
        with io.open(ARTIFACT, encoding="utf-8") as fh:
            uni = (json.load(fh).get("universe") or {})
        self.assertEqual(got.get("n_names"), uni.get("n_names"))
        self.assertEqual(got.get("n_dates"), uni.get("n_dates"))
        # MB21: gate the comparison rather than scoring an absence perfectly.
        self.assertIsNotNone(uni.get("n_names"),
                             "the artifact carries no universe.n_names, so this test compared "
                             "nothing")

    def test_an_absent_artifact_offers_no_figure_rather_than_a_stale_one(self):
        """The module's own rule, and the stamp must obey it too: no fallback to 2,531."""
        got = S.measured("roth", path=os.path.join(ROOT, "_no_such_artifact_.json")) or {}
        self.assertIn("unavailable", got)
        self.assertIsNone(got.get("n_names"),
                          "an absent artifact still produced a universe size, i.e. a literal "
                          "fallback survived")
        self.assertIsNone(got.get("net_alpha"))

    def test_the_figures_are_still_read_through_and_not_re_typed(self):
        """A positive control on `MC11`'s own change: if the literals came back, deriving the
        stamp would be pointless."""
        got = S.measured("roth") or {}
        if got.get("unavailable"):
            raise unittest.SkipTest("no canonical artifact on this host")
        with io.open(ARTIFACT, encoding="utf-8") as fh:
            bc = ((json.load(fh).get("book_configs") or {}).get("roth") or {})
        for k in ("net_alpha", "net_sharpe", "annual_turnover"):
            self.assertEqual(got.get(k), bc.get(k), "%s is not the artifact's value" % k)


# =============================================================================================
class TheTwoOperandsDescribeOnePanel(unittest.TestCase):
    """`research_record` — the committed pair must not be half-updated."""

    def test_the_module_still_renders_neither_operand(self):
        """`MB38`'s rule, and the premise of everything else here: the page compares, it does not
        publish. If that changes, these constants stop being internal and this test's framing is
        wrong — so it is asserted rather than assumed."""
        self.assertFalse(hasattr(RR, "RENDER_OPERANDS"),
                         "a switch to render the operands appeared; MB38's rule is that the "
                         "SITE must not publish them")

    def test_the_pair_is_internally_consistent(self):
        h, f = float(RR.HEADLINE_STATISTIC), float(RR.PLACEBO_FLOOR)
        published = (abs(h - PUBLISHED_HEADLINE) < 1e-12 and abs(f - PUBLISHED_FLOOR) < 1e-12)

        pair = _corrected_pair()
        if pair is None:
            # SKIP LOUDLY, and only after asserting the published side — a test that passes
            # BECAUSE the data is absent is the vacuous pass this record keeps finding.
            self.assertTrue(published,
                            "the pair is not the published 2,531-name panel's (headline %r, "
                            "floor %r) and the corrected artifacts are absent, so it cannot be "
                            "checked against the corrected universe either" % (h, f))
            print("SKIP: corrected artifacts absent; published pair verified")
            raise unittest.SkipTest("no licensed data root")

        ch, cf = pair
        corrected = (abs(h - ch) < 1e-9 and abs(f - cf) < 1e-9)
        self.assertTrue(
            published or corrected,
            "THE PAGE'S TWO OPERANDS DO NOT DESCRIBE ONE PANEL.\n"
            "  module    : headline %r vs floor %r\n"
            "  published : %r vs %r\n"
            "  corrected : %r vs %r\n"
            "A half-done update pairs a numerator from one universe with a floor from another, "
            "which is MA19's own recurring defect. Move BOTH or neither."
            % (h, f, PUBLISHED_HEADLINE, PUBLISHED_FLOOR, ch, cf))

    def test_a_mixed_pair_is_REJECTED(self):
        """The positive control. Without it the test above could be passing because its matcher
        is too loose rather than because the pair is consistent."""
        pair = _corrected_pair()
        if pair is None:
            raise unittest.SkipTest("no licensed data root")
        ch, cf = pair

        def consistent(h, f):
            return ((abs(h - PUBLISHED_HEADLINE) < 1e-12 and abs(f - PUBLISHED_FLOOR) < 1e-12)
                    or (abs(h - ch) < 1e-9 and abs(f - cf) < 1e-9))

        self.assertTrue(consistent(PUBLISHED_HEADLINE, PUBLISHED_FLOOR))
        self.assertTrue(consistent(ch, cf))
        self.assertFalse(consistent(PUBLISHED_HEADLINE, cf),
                         "an old headline with a corrected floor is accepted; the detector is "
                         "not seeing the thing it exists to catch")
        self.assertFalse(consistent(ch, PUBLISHED_FLOOR),
                         "a corrected headline with the old floor is accepted")

    def test_the_corrected_pair_is_not_degenerate(self):
        """`MB21`: if the corrected pair equalled the published one, the mixed-pair control
        would be checking that a number equals itself."""
        pair = _corrected_pair()
        if pair is None:
            raise unittest.SkipTest("no licensed data root")
        ch, cf = pair
        self.assertGreater(abs(ch - PUBLISHED_HEADLINE), 1e-6)
        self.assertGreater(abs(cf - PUBLISHED_FLOOR), 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
