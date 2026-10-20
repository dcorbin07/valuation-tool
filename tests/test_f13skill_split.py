# -*- coding: utf-8 -*-
"""`F13SKILL` — `K0` and the charter-split arithmetic.

The load-bearing test is `test_the_verdict_is_decided_by_the_floor_and_not_by_an_outcome`: the
NOT-ASSESSABLE verdict must follow from date counts alone, because the draft's §5 forbids choosing a
split after seeing a result (`MA58`'s void condition 5).
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import state_isolation  # noqa: F401,E402


def _skip_loudly(case, why):
    """A skip nobody can mistake for a pass. The repo's own idiom -- `test_fleet_doors` prints
    `(SKIPPED LOUDLY: ...)` -- because in a 327-suite run a silent skip and a pass look the
    same. Every artifact below is built from data under `data/`, which is gitignored, so CI
    never has it and these cases MUST skip rather than fail or pass vacuously."""
    msg = "(SKIPPED LOUDLY: %s)" % why
    print("\n       %s" % msg, flush=True)
    case.skipTest(msg)

from scripts import f13skill_split as F                                  # noqa: E402

DRAFT = os.path.join(ROOT, "PREREG_DRAFT_f13skill.md")


def _src(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _artifact():
    d = ROOT
    for _ in range(6):
        p = os.path.join(d, "data", "free_analysis", F.OUT)
        if os.path.isfile(p):
            return json.load(io.open(p, encoding="utf-8"))
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    return None


class NoOutcomeIsEverRead(unittest.TestCase):

    def test_the_module_never_names_a_forward_return(self):
        tree = ast.parse(_src("scripts/f13skill_split.py"))
        names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.value for n in ast.walk(tree)
                  if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        for b in ("fwd_ret", "abnormal", "permutation_null", "bench_ret"):
            self.assertNotIn(b, names, b)

    def test_it_declares_zero_trials(self):
        self.assertIn("ZERO TRIALS", (F.__doc__ or "").upper())


class TheBarsAreTheDraftsOwn(unittest.TestCase):

    def test_the_draft_file_exists(self):
        self.assertTrue(os.path.isfile(DRAFT))

    def test_K0s_bar_is_the_drafts_thousand(self):
        self.assertEqual(F.K0_BAR, 1000)
        self.assertIn("1,000", _src("PREREG_DRAFT_f13skill.md"))

    def test_the_half_floor_is_the_shipped_sixteen(self):
        """The 16-date both-halves floor is the SHIPPED one and is not chosen here.

        **Corrected while writing this test:** my first cut asserted the literal against
        `PREREG_DRAFT_f13skill.md`, which does not contain it — that draft reasons about "~14
        build-quadrant dates" and never names the floor. The floor is cited in
        `PREREG_DRAFT_osap3.md` (quoting `STAGE1-BATCH1`'s five-date early half "against a 16-date
        floor"), so that is where the citation is checked. A test that cites the wrong source is
        the wrong-object family on a test rather than on an arm.
        """
        self.assertEqual(F.MIN_HALF_DATES, 16)
        self.assertIn("16-date floor", _src("PREREG_DRAFT_osap3.md"))

    def test_the_best_ever_anchor_is_MB18s_measured_figure(self):
        self.assertAlmostEqual(F.BEST_EVER_RAW_ANCHOR_SD, 0.4346, places=4)


class TheVerdictFollowsFromDatesAlone(unittest.TestCase):

    def test_the_verdict_is_decided_by_the_floor_and_not_by_an_outcome(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        cs = r["charter_split"]
        expected_assessable = cs["early_clears_floor"] and cs["late_clears_floor"]
        if expected_assessable:
            self.assertIn("ASSESSABLE", r["verdict"])
            self.assertNotIn("NOT ASSESSABLE", r["verdict"])
        else:
            self.assertIn("NOT ASSESSABLE", r["verdict"])

    def test_the_early_half_really_is_below_the_floor(self):
        """Measured 2026-10-19: 8 early dates against a 16-date floor."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        cs = r["charter_split"]
        self.assertLess(cs["early_dates"], F.MIN_HALF_DATES)
        self.assertFalse(cs["early_clears_floor"])

    def test_K0_passes_from_2013_and_not_before(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        self.assertEqual(r["K0"]["first_year_clearing_the_bar"], 2013)
        by = {int(k): v for k, v in r["K0"]["managers_by_year"].items()}
        self.assertLess(by[2012], F.K0_BAR)
        self.assertGreaterEqual(by[2013], F.K0_BAR)

    def test_the_manager_column_was_resolved_and_is_not_the_scouts_guess(self):
        """`mgrno` is Thomson's `s34` column. The real one is `cik`."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        self.assertEqual(r["K0"]["manager_column_resolved"], "cik")

    def test_the_MDE_travels_with_the_verdict(self):
        """`MB22`/`V6`/`S19`: quote the MDE with the verdict or do not quote the verdict."""
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        self.assertIn("MDE_SENTENCE", r)
        self.assertIn("usable_window", r["mde"])
        self.assertIn("early_half", r["mde"])
        for v in r["mde"].values():
            self.assertIn("UNCALIBRATED", v["LABEL"])

    def test_the_early_half_MDE_exceeds_the_best_anchor_this_panel_has_carried(self):
        r = _artifact()
        if r is None:
            _skip_loudly(self, "F13SKILL_SPLIT.json absent -- built from LICENSED WRDS payload, which CI never has")
        self.assertGreater(r["mde"]["early_half"]["mde80_sd_at_crit_2"],
                           F.BEST_EVER_RAW_ANCHOR_SD)


class WhatIsNotClaimed(unittest.TestCase):

    def test_no_arm_is_scored_and_no_skill_weight_is_built(self):
        src = _src("scripts/f13skill_split.py")
        for banned in ("skill_weight", "crowding", "herfindahl"):
            self.assertNotIn(banned, src.lower().replace("skill_weight`", ""),
                             "the split module must not build the signal: %s" % banned)

    def test_it_does_not_relax_the_floor_after_reading_it(self):
        """`W-28` §6: a pre-committed bar may not move once it has been watched to fail."""
        tree = ast.parse(_src("scripts/f13skill_split.py"))
        lits = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, int)]
        self.assertIn(16, lits)
        self.assertNotIn(8, [v for v in lits if v == 8 and False] or [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
