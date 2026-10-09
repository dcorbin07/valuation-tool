# -*- coding: utf-8 -*-
"""`DECISION_canonical_move.md` step 1 — the canonical headline describes the DEPLOYED book.

**THE GATE THE MEMO SPECIFIES FOR STEP 1**, written because the memo says step 1 is *"the only
one that touches behaviour"* and that *"if step 1 cannot be made to pass its gate, the move stops
there."*

**WHY IT IS NEEDED NOW AND WAS NOT BEFORE.** `cpcv.adopt` has been false on every run in this
project's history, so `rec is base` and the distinction was invisible. `CORRECTED-FLOORS` part 1b
measured that on the corrected universe CPCV **adopts `ic-proportional`**, and the adopted book's
top-decile alpha is **2.83%** against the deployed **6.07%** — so a canonical re-run would
otherwise re-point the headline at a book nobody runs. **It flatters DOWNWARD here, and the rule
is indifferent to the direction.**

Run as its own process and judged by exit code, per `RUN_RULES`.
"""
from __future__ import annotations

import ast
import io
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PANEL_SRC = os.path.join(ROOT, "valuation", "edge", "fundamental_panel.py")
MEMO = os.path.join(ROOT, "DECISION_canonical_move.md")

#: the half-open region of `run_backtests` that computes the headline blocks.
#:
#: **THE BOUNDARY MATTERS AND MY FIRST ONE WAS WRONG.** It ran to `recommended_weights_full`,
#: which sweeps in the `adopted_book` block -- and that block legitimately uses `rec`, because it
#: IS the adopted reading. The guard fired on two uses of `rec` and was RIGHT to: it told me the
#: region included a block where `rec` belongs. So the region ends where the adopted block
#: begins, and the adopted block has its own assertion that it DOES score `rec`.
HEAD_MARK = "            headline_w = base"
TAIL_MARK = '                    out["adopted_book"] = {'


def _src():
    return io.open(PANEL_SRC, encoding="utf-8").read()


def _headline_region():
    s = _src()
    i, j = s.index(HEAD_MARK), s.index(TAIL_MARK)
    assert i < j, "the headline region markers are out of order"
    return s[i:j]


# =============================================================================================
class TheHeadlineIsTheDeployedBook(unittest.TestCase):
    def test_the_headline_vector_is_the_base_weights(self):
        """`headline_w = base`, not `rec`. One line, and it is the whole ruling."""
        t = ast.parse(_src())
        found = []
        for n in ast.walk(t):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 \
                    and getattr(n.targets[0], "id", None) == "headline_w":
                found.append(getattr(n.value, "id", None))
        self.assertEqual(found, ["base"],
                         "headline_w must be assigned from `base` exactly once; got %r" % (found,))

    def test_no_bare_rec_survives_in_the_headline_region(self):
        """A COUNT of converted call sites can be satisfied by converting the wrong ones. This
        cannot: the enumeration showed ZERO other uses of `rec` in the region, so the absence of
        the name is exact rather than merely strict."""
        leftover = re.findall(r"\brec\b", _headline_region())
        self.assertFalse(leftover,
                         "a bare `rec` survives in the headline region, so a headline block is "
                         "still computed on CPCV's recommendation: %r" % (leftover,))

    def test_every_headline_block_is_computed_on_the_headline_vector(self):
        region = _headline_region()
        n = len(re.findall(r"panel, cols, headline_w\b", region))
        self.assertGreaterEqual(n, 14,
                                "expected at least 14 headline call sites on headline_w, found "
                                "%d -- adoption reaches construction, multiple_testing, regime, "
                                "benchmarks, institutional_dependence, four costs cells, six "
                                "book-config cells and two after_tax cells" % n)

    def test_construction_weighting_reports_the_headlines_own_weighting(self):
        """It used to report CPCV's choice, which blurred two facts: what the headline USED and
        what CPCV ADOPTED. They are now separate fields."""
        region = _headline_region()
        self.assertIn('out["construction_weighting"] = "default"', region)
        self.assertIn('out["headline_weighting_is_the_deployed_book"]', region)

    def test_the_guard_is_not_vacuous(self):
        """A positive control: the pattern it bans must be detectable when present."""
        probe = "x = quantile_backtest(panel, cols, rec, n_q=10)\n"
        self.assertTrue(re.findall(r"\brec\b", probe),
                        "the bare-`rec` detector cannot see the thing it bans")


# =============================================================================================
class TheAdoptedBookIsReportedBesideItAndNeverInstead(unittest.TestCase):
    def test_the_adopted_block_exists_in_both_states(self):
        """A block of nulls and an absent block must not read the same (`O21-D2`'s VACUOUS rule),
        so a reader can tell *"CPCV rejected"* from *"nobody looked"*."""
        s = _src()
        self.assertEqual(s.count('out["adopted_book"]'), 2,
                         "the adopted block must be written in BOTH the adopted and the rejected "
                         "state, so an absent block and a rejection do not read the same")
        self.assertIn("CPCV REJECTED", s)

    def test_the_adopted_block_carries_its_own_construction(self):
        """Reported, never substituted. If it carried no figures it would be a label rather than
        a reading, and nobody could check what adoption would have said."""
        s = _src()
        i = s.index('out["adopted_book"]')
        blk = s[i:i + 1400]
        self.assertIn("quantile_backtest(panel, cols, rec", blk,
                      "the adopted block must score the ADOPTED weights -- that is the one place "
                      "`rec` still belongs")

    def test_it_says_why_it_is_not_the_headline(self):
        """X7 measured that adoption manufactures about +1.4 of long-short *t* out of nothing on
        27% of PURE-NOISE draws, because CPCV selects among its own schemes ON THE SAME PANEL the
        headline is then measured on. The artifact must carry that reason."""
        s = _src()
        self.assertIn("why_it_is_not_the_headline", s)
        self.assertIn("PURE-NOISE", s)

    def test_the_paste_ready_recommendation_is_deliberately_unchanged(self):
        """`recommended_weights_full` always was the RECOMMENDATION, so it still reads `rec`.
        Changing it would be a different decision from the one the memo records."""
        self.assertIn("_full_weights(rec, bucket)", _src())


# =============================================================================================
class TheChangeIsInertWhereverCPCVRejects(unittest.TestCase):
    """The safety argument, and it is why this lands as a correctness change with no figure
    attached: when `adopted_w` is false the code sets `rec = base`, so substituting `base` into
    the headline cannot move a value. CPCV has rejected on every run to date."""

    def test_both_rejection_branches_set_rec_to_base(self):
        s = _src()
        self.assertGreaterEqual(
            s.count('rec, adopted_w, rec_name = base, False, "default"'), 2,
            "the rejection branches must bind `rec` to `base`; if they ever diverge, the "
            "inertness argument for this change stops holding")

    def test_cpcv_is_still_the_authority_for_the_recommendation(self):
        """The change does NOT weaken CPCV. It still decides what is RECOMMENDED; it no longer
        decides what the headline MEASURES."""
        s = _src()
        self.assertIn("CPCV is the AUTHORITY for the weights", s)
        self.assertIn('out["cpcv"] = cpcv', s)


# =============================================================================================
class TheMemoLandsFirstAndSaysWhatMayNotMove(unittest.TestCase):
    def test_the_memo_exists_and_records_the_ruling(self):
        """WHITESPACE-NORMALISED, because the memo is hard-wrapped at ~96 chars and the phrase
        this looks for straddles a line break. A substring assertion on wrapped prose breaks on
        the wrap -- the text was right and the matcher was naive, which is a cousin of the
        substring-ban family."""
        self.assertTrue(os.path.exists(MEMO), "the decision memo must land before the move")
        m = " ".join(io.open(MEMO, encoding="utf-8").read().split())
        self.assertIn("a book nobody runs is the defect", m)
        self.assertIn("whichever way it flatters", m)

    def test_the_memo_names_what_must_not_move(self):
        m = " ".join(io.open(MEMO, encoding="utf-8").read().split())
        for frag in ("PAPER_TRACK_CONTRACT", "forward record", "deployed weights"):
            self.assertIn(frag, m, "the memo does not name %r among what must not move" % frag)

    def test_the_memo_names_the_dot_env_hazard(self):
        """The obvious route is the wrong one: `WRDS_DATA_DIR` also feeds the LIVE screener's
        provider, so pointing it at the corrected export would move the product's data source."""
        m = io.open(MEMO, encoding="utf-8").read()
        self.assertIn("WRDS_DATA_DIR", m)
        self.assertIn("--data-dir", m)

    def test_the_frozen_meter_parameters_are_untouched(self):
        """The memo's first `must not move`, checked against the code rather than the prose."""
        # READ OFF THE MODULE, NOT GUESSED. The constant is `SIGMA_MONTHLY_PP` and `RHO` is
        # 3.0 rather than 3 -- and the whole point of this test is to check the frozen
        # parameters against the CODE rather than against the memo's prose, so guessing their
        # names would have defeated it.
        from valuation.edge import track_meter as TM
        self.assertAlmostEqual(TM.SIGMA_MONTHLY_PP, 3.9847, places=4)
        self.assertAlmostEqual(TM.RHO, 3.0, places=10)
        self.assertAlmostEqual(TM.ALPHA, 0.05, places=10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
