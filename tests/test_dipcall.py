"""DIP-CALL — what these tests pin, and why each one exists.

Register: `PREREG_dipcall.md`, committed ALONE at `c5e0b31`.

THE LOAD-BEARING ONES, in order of how much they would cost if they failed silently:

1. **THE LOOK-AHEAD, FROM BOTH SIDES.** The volatility scale is taken `shift(1)`, so perturbing
   the event day's OWN return must not move its own scale -- and the companion must hold too, or
   the guard is vacuous: perturbing a PRIOR day MUST move it. `V6`'s own vacuity companion caught
   exactly this shape, and `MA28`'s Altman-Z fixture was vacuous for the mirror-image reason (it
   scaled a whole filing, and a sum of RATIOS is invariant to that).

2. **THE SPLIT TRAP, FROM BOTH SIDES.** `V6`'s `C5`: on a RAW series a 2-for-1 split reads as a
   -50% drop, and since companies split AFTER they rise a raw basis flags the strongest names in
   the universe. The event basis must be the adjusted series. Pinned with a positive control so
   it cannot pass by detecting nothing.

3. **A1's NEWS WINDOW IS MEASURED IN SESSIONS, NOT CALENDAR DAYS.** A Friday-after-the-close
   announcement reacts on Monday: three CALENDAR days later and ONE SESSION later. A
   calendar-days implementation misclassifies it, and earnings reactions are the whole news arm.

4. **A1b: UNKNOWN IS A THIRD STATE AND NEVER READS AS "NO NEWS".** `O6`/`O7` measured 29 of 186
   names as foreign private issuers with ZERO earnings dates, so a filter folding UNKNOWN into
   "no announcement" fails OPEN on a non-random tenth of the book. Positive control included, or
   the test passes by returning UNKNOWN for everything.

5. **A12: THE TIER IS POINT-IN-TIME AND NEVER SEES A FUTURE CAP.** The census's 459 names are
   "ever in the tier", which counts a name's 2009 events because it reached $10B in 2019.

6. **THE ARM'S GATE REFUSES, AND THE TWO REFUSAL STATES ARE DISTINCT.** `E-1`'s lesson: a
   hard-coded refusal cannot tell "the control never ran" from "the control ran and fired". The
   gate is exercised by its own function and the arm is NEVER run -- `E-1`'s other lesson is that
   a test proving a refusal by REMOVING it is unsafe when the thing behind the refusal is
   forbidden.

7. **NO BAR IS RETYPED IN A SCRIPT.** `MA5` measured that a default is exactly how the
   Harvey-Liu-Zhu bar froze at 3.0, and these bars are PRE-COMMITTED, so a second copy would let
   a successor inherit this register's pre-registration without writing one. Read from the SYNTAX
   TREE, never grepped: `MA49` recorded a fixture that failed against the FIXED tree because the
   repair comment quoted the defect verbatim.

8. **THE REGISTER EXISTS AND IS MARKDOWN-ONLY AND IS AN ANCESTOR.** `S3-I1`'s
   declaration-before-fill check against real git, and `W-1`'s lesson that a citation to a file
   nobody checked is worth nothing.

    python tests/test_dipcall.py
"""
from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.studies import dipcall as D  # noqa: E402

_SKIPS = []


def _skip(t, why):
    _SKIPS.append(why)
    t.skipTest(why)


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _series(closes, start="2010-01-04"):
    """A synthetic ascending price frame with the module's own column names."""
    dates = pd.bdate_range(start, periods=len(closes)).strftime("%Y-%m-%d").tolist()
    return pd.DataFrame({"date": dates, "close": np.asarray(closes, dtype=float)})


def _vol_z(closes):
    """Reproduce the module's event arithmetic on a synthetic series."""
    s = _series(closes)
    r = s["close"].pct_change()
    vol = r.rolling(D.VOL_WIN, min_periods=D.MIN_VOL_OBS).std().shift(1)
    return r, vol, r / vol


# =============================================================================================
# 1. THE LOOK-AHEAD, BOTH DIRECTIONS
# =============================================================================================
class LookAhead(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(7)
        self.closes = 100.0 * np.cumprod(1.0 + rng.normal(0, 0.01, 200))

    def test_the_event_day_is_not_inside_its_own_volatility_scale(self):
        """`shift(1)`. Perturbing day i's return must leave day i's own scale untouched."""
        i = 150
        _, vol_a, _ = _vol_z(self.closes)
        c = self.closes.copy()
        c[i:] *= 0.80                      # a -20% shock ON day i, carried forward
        _, vol_b, _ = _vol_z(c)
        self.assertAlmostEqual(float(vol_a.iloc[i]), float(vol_b.iloc[i]), places=15,
                               msg="the event day's return reached its own volatility scale")

    def test_and_the_guard_is_NOT_vacuous_a_prior_day_DOES_move_it(self):
        """Without this companion the test above passes against a scale that reads nothing."""
        i = 150
        _, vol_a, _ = _vol_z(self.closes)
        c = self.closes.copy()
        c[i - 10:] *= 0.80                 # the same shock TEN SESSIONS EARLIER
        _, vol_b, _ = _vol_z(c)
        self.assertNotAlmostEqual(float(vol_a.iloc[i]), float(vol_b.iloc[i]), places=6,
                                  msg="a PRIOR day's return does not reach the scale either, so "
                                      "the look-ahead guard is measuring nothing")

    def test_a_perturbation_on_the_event_day_does_move_its_own_z(self):
        """The other half of non-vacuity: the event day's return must reach its own z, or the
        event could not be detected at all."""
        i = 150
        c = self.closes.copy()
        c[i:] *= 0.80
        _, _, z_b = _vol_z(c)
        _, _, z_a = _vol_z(self.closes)
        self.assertLess(float(z_b.iloc[i]), float(z_a.iloc[i]) - 1.0)
        self.assertLess(float(z_b.iloc[i]), -D.K_PRIMARY)


# =============================================================================================
# 2. THE SPLIT TRAP (V6's C5), BOTH DIRECTIONS
# =============================================================================================
class SplitTrap(unittest.TestCase):
    def test_a_2_for_1_split_on_a_RAW_series_reads_as_an_event(self):
        """The defect this register's basis choice exists to avoid. A raw series halves on the
        split, which is a -50% day, and companies split AFTER they rise -- so a raw basis flags
        the strongest names in the universe (`V6`'s C5). This is the POSITIVE control: it proves
        the detector can see the artefact, so the next test's silence is informative."""
        rng = np.random.default_rng(3)
        raw = 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.008, 200))
        raw[150:] /= 2.0                    # the split, unadjusted
        _, _, z = _vol_z(raw)
        self.assertLessEqual(float(z.iloc[150]), -D.K_PRIMARY,
                             msg="the raw-basis split artefact is not detectable, so the "
                                 "companion test below proves nothing")

    def test_and_the_ADJUSTED_series_the_register_uses_does_NOT(self):
        """`closeadj`: the split is already divided out, so there is no -50% day to flag."""
        rng = np.random.default_rng(3)
        adj = 100.0 * np.cumprod(1.0 + rng.normal(0.001, 0.008, 200))
        _, _, z = _vol_z(adj)               # no split applied: this IS the adjusted basis
        self.assertGreater(float(z.iloc[150]), -D.K_PRIMARY)

    def test_the_module_reads_the_adjusted_column_and_names_the_raw_rule(self):
        """`read_prices` must document that a STRIKE needs the raw close -- `O-1` paid the other
        half of this lesson when MNST's 3-for-1 booked a fake +1453%."""
        doc = (D.read_prices.__doc__ or "")
        self.assertIn("RAW", doc)
        self.assertIn("STRIKE", doc.upper())


# =============================================================================================
# 3 + 4. A1 / A1b — THE NEWS WINDOW IN SESSIONS, AND UNKNOWN AS A THIRD STATE
# =============================================================================================
class _Spine(object):
    """A stand-in with the shipped `dates_or_unknown` contract: `None` for an uncovered name."""

    def __init__(self, by):
        self.by = by

    def dates_or_unknown(self, t):
        return self.by.get(t)


class NewsWindow(unittest.TestCase):
    def test_the_window_is_i_minus_j_in_zero_or_one_SESSIONS(self):
        self.assertEqual(D.NEWS_SESSION_WINDOW, (0, 1))
        for gap, want in ((0, D.NEWS), (1, D.NEWS), (2, D.NO_NEWS), (3, D.NO_NEWS)):
            got = D.news_class(None, "T", 100, [100 - gap])
            self.assertEqual(got, want, "session gap %d classified %s" % (gap, got))

    def test_an_announcement_AFTER_the_event_is_not_news_for_that_event(self):
        """A reaction cannot precede its cause. `i - j = -1` must not classify as news."""
        self.assertEqual(D.news_class(None, "T", 100, [101]), D.NO_NEWS)

    def test_a_friday_after_close_announcement_reacting_MONDAY_is_NEWS(self):
        """THE CALENDAR-VS-SESSION TRAP. Friday the 8th, reaction Monday the 11th: three CALENDAR
        days and ONE SESSION. A calendar-days window of {0,1} would call this NO-NEWS and throw
        away a real earnings reaction."""
        dates = ["2010-01-07", "2010-01-08", "2010-01-11", "2010-01-12"]
        d2i = {d: j for j, d in enumerate(dates)}
        spine = _Spine({"T": ["2010-01-08"]})
        ann = D.announce_sessions(spine, "T", d2i)
        self.assertEqual(ann, [1])
        self.assertEqual(D.news_class(spine, "T", d2i["2010-01-11"], ann), D.NEWS)
        # and the calendar gap really is three days, which is what makes the test meaningful
        import datetime as dt
        self.assertEqual((dt.date(2010, 1, 11) - dt.date(2010, 1, 8)).days, 3)

    def test_an_announcement_on_a_NON_trading_date_maps_FORWARD_to_the_next_session(self):
        """A holiday announcement reacts on the next session the name actually trades."""
        dates = ["2010-01-07", "2010-01-08", "2010-01-11"]
        d2i = {d: j for j, d in enumerate(dates)}
        spine = _Spine({"T": ["2010-01-09"]})          # a Saturday
        self.assertEqual(D.announce_sessions(spine, "T", d2i), [2])

    def test_A1b_an_uncovered_name_is_UNKNOWN_and_never_NO_NEWS(self):
        spine = _Spine({"COVERED": ["2010-01-08"]})
        self.assertIsNone(D.announce_sessions(spine, "FOREIGN", {"2010-01-11": 0}))
        self.assertEqual(D.news_class(spine, "FOREIGN", 0, None), D.UNKNOWN)

    def test_A1b_POSITIVE_CONTROL_a_covered_name_still_returns_NO_NEWS(self):
        """Without this the test above passes against a classifier that returns UNKNOWN always,
        which would empty both arms and read as a coverage problem rather than a bug."""
        d2i = {"2010-01-07": 0, "2010-01-08": 1, "2010-01-11": 2, "2010-02-01": 3}
        spine = _Spine({"T": ["2010-01-08"]})
        ann = D.announce_sessions(spine, "T", d2i)
        self.assertEqual(D.news_class(spine, "T", 3, ann), D.NO_NEWS)


# =============================================================================================
# 5. A12 — THE POINT-IN-TIME TIER NEVER SEES A FUTURE CAP
# =============================================================================================
class PointInTimeTier(unittest.TestCase):
    def test_a_future_cap_does_not_make_an_earlier_session_eligible(self):
        sched = [("2012-03-31", 5e8), ("2015-03-31", 5e10)]
        flags = D._tier_flags(["2011-01-03", "2013-01-03", "2016-01-04"], sched)
        self.assertEqual(list(flags), [False, False, True],
                         "A12: tier membership read a cap from the future")

    def test_a_session_before_the_first_observation_is_NOT_eligible(self):
        """Unknown is never read as eligible."""
        flags = D._tier_flags(["2008-01-02"], [("2012-03-31", 5e11)])
        self.assertEqual(list(flags), [False])

    def test_a_name_leaving_the_tier_stops_being_eligible(self):
        sched = [("2010-03-31", 5e10), ("2013-03-31", 1e8)]
        flags = D._tier_flags(["2011-01-03", "2014-01-03"], sched)
        self.assertEqual(list(flags), [True, False])

    def test_an_empty_schedule_is_never_eligible(self):
        self.assertEqual(list(D._tier_flags(["2011-01-03"], [])), [False])


# =============================================================================================
# 6. THE ARM'S GATE REFUSES, AND THE TWO STATES ARE DISTINCT
# =============================================================================================
class ArmGate(unittest.TestCase):
    def test_the_two_refusal_states_have_DISTINCT_messages(self):
        """`E-1`: a hard-coded refusal cannot tell 'never ran' from 'ran and fired'. Exercised
        through the gate's own function; THE ARM IS NEVER RUN, because `E-1`'s own mutation test
        proved a withdrawn arm by removing its refusal and thereby RAN it."""
        import importlib
        arm = importlib.import_module("scripts.dipcall_arm")
        real = D.out_path(arm.KILLS)
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            absent = os.path.join(tmp, "nope.json")
            fired = os.path.join(tmp, "fired.json")
            with io.open(fired, "w", encoding="utf-8") as fh:
                json.dump({"all_kills_pass": False,
                           "gates": {"K1_event_count": False, "K2": True}}, fh)

            msgs = {}
            for label, path in (("absent", absent), ("fired", fired)):
                orig = D.out_path
                D.out_path = lambda n, _p=path: _p          # noqa: E731
                try:
                    with self.assertRaises(SystemExit) as cm:
                        arm.require_kills()
                    msgs[label] = str(cm.exception)
                finally:
                    D.out_path = orig

        self.assertIn("ABSENT", msgs["absent"])
        self.assertIn("FIRED", msgs["fired"])
        self.assertIn("K1_event_count", msgs["fired"],
                      "the refusal does not name WHICH kill fired")
        self.assertNotEqual(msgs["absent"], msgs["fired"])
        # And the real artifact on disk is what it was.
        self.assertEqual(real, D.out_path(arm.KILLS))

    def test_the_gate_is_CONDITIONAL_in_the_syntax_tree_not_hard_coded(self):
        """A refusal that cannot fire is not a refusal. `all_kills_pass` must be READ, and the
        arm's `main` must CALL the gate -- read from the AST so a docstring cannot satisfy it."""
        tree = ast.parse(_src("scripts/dipcall_arm.py"))
        fn = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn("require_kills", fn)
        src = ast.dump(fn["require_kills"])
        self.assertIn("all_kills_pass", src)
        self.assertGreaterEqual(sum(1 for n in ast.walk(fn["require_kills"])
                                    if isinstance(n, ast.Raise)) +
                                sum(1 for n in ast.walk(fn["require_kills"])
                                    if isinstance(n, ast.Call)
                                    and getattr(n.func, "id", "") == "SystemExit"), 1)
        called = [n for n in ast.walk(fn["main"]) if isinstance(n, ast.Call)
                  and getattr(n.func, "id", "") == "require_kills"]
        self.assertEqual(len(called), 1, "main() does not call the gate exactly once")


# =============================================================================================
# 7. NO BAR IS RETYPED IN A SCRIPT (MA5), READ FROM THE SYNTAX TREE (MA49)
# =============================================================================================
class BarsAreNotRetyped(unittest.TestCase):
    BARS = (1500, 0.70, 0.30, 3.0, 0.67, 2.5, 10e9, 0.10)

    def test_the_register_constants_live_in_the_module(self):
        for name, want in (("MIN_EVENTS_PER_CELL", 1500),
                           ("EARNINGS_COVERAGE_FLOOR", 0.70),
                           ("VOL_RHO_BAR", 0.30),
                           ("VOL_QUINTILE_RATIO_BAR", 3.0),
                           ("ECONOMIC_FLOOR_PP", 0.67),
                           ("K_PRIMARY", 2.5),
                           ("TIER_FLOOR", 10e9),
                           ("BH_Q", 0.10),
                           ("BH_K", 10),
                           ("CONTRACT_MIN_POSITIONS", 50)):
            self.assertEqual(getattr(D, name), want, name)

    def test_no_script_retypes_a_bar_as_a_literal(self):
        """`MA5`. Read from the AST, so the docstrings that DISCUSS these numbers -- and they all
        do, deliberately -- cannot trip the check. `MA49` recorded a fixture failing against the
        FIXED tree for exactly that reason."""
        for rel in ("scripts/dipcall_kills.py", "scripts/dipcall_arm.py",
                    "scripts/dipcall_k_census.py"):
            tree = ast.parse(_src(rel))
            lits = [n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                    and not isinstance(n.value, bool)]
            for bar in (1500, 0.67, 0.30, 10e9):
                self.assertNotIn(bar, lits,
                                 "%s retypes the pre-committed bar %r instead of importing it "
                                 "from valuation.studies.dipcall" % (rel, bar))

    def test_the_k_census_is_declared_to_carry_no_verdict(self):
        """It runs AFTER the kill fired, so its own artifact must say so in machine-readable
        form -- a reader of the JSON alone must not be able to mistake it for a result."""
        p = D.out_path("DIPCALL_K_CENSUS.json")
        if not os.path.isfile(p):
            _skip(self, "DIPCALL_K_CENSUS.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        self.assertEqual(a["trials"], 0)
        self.assertFalse(a["forward_return_touched"])
        self.assertFalse(a["is_a_verdict"])
        self.assertFalse(a["advances_the_program"])


# =============================================================================================
# 8. THE REGISTER: MARKDOWN ONLY, AND A STRICT ANCESTOR
# =============================================================================================
class Register(unittest.TestCase):
    REG = "PREREG_dipcall.md"

    def test_the_register_file_exists(self):
        """`W-1`: a citation to a file nobody checked is worth nothing."""
        self.assertTrue(os.path.isfile(os.path.join(REPO, self.REG)))

    def test_the_register_commit_touched_markdown_ONLY_and_is_an_ANCESTOR(self):
        """`S3-I1`'s declaration-before-fill check, against REAL git rather than a stub --
        checking a commit rule against a stub checks the stub."""
        def git(*a):
            return subprocess.run(("git",) + a, cwd=REPO, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")

        sha = ""
        for line in git("log", "--format=%H", "--", self.REG).splitlines():
            sha = line.strip()                      # the OLDEST commit touching it
        if not sha:
            _skip(self, "no git history for %s in this checkout" % self.REG)
        files = [x for x in git("show", "--name-only", "--format=", sha).split() if x]
        self.assertEqual(files, [self.REG],
                         "the register was NOT committed alone: %s" % files)
        self.assertTrue(all(f.endswith(".md") for f in files))
        anc = subprocess.run(("git", "merge-base", "--is-ancestor", sha, "HEAD"), cwd=REPO,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertEqual(anc.returncode, 0,
                         "the register commit is not an ancestor of HEAD")

    def test_the_register_declares_the_twelve_amendments_and_the_void_conditions(self):
        txt = _src(self.REG)
        for a in ["### A%d" % i for i in range(1, 13)]:
            self.assertIn(a, txt, "the register is missing amendment %s" % a)
        self.assertIn("VOID CONDITIONS", txt)
        self.assertIn("LABELLED UNCALIBRATED", txt)


# =============================================================================================
# 9. X1's SPLIT IS ONE DEFINITION (B7), AND THE CENSUS CONTROLS REPRODUCE
# =============================================================================================
class TickerSplit(unittest.TestCase):
    def test_it_agrees_with_X1s_OWN_published_definition(self):
        """`B7`. The duplication pre-dates this item -- `scripts/dipcall_census.py` and
        `scripts/r4_x1_accounting_universe.py` each carry a copy -- so this is a THIRD, and this
        test is what stops the three diverging. Reported as a bug in the handoff."""
        import importlib
        r4 = importlib.import_module("scripts.r4_x1_accounting_universe")
        for t in ("AAPL", "MSFT", "AMZN", "ABBV", "BRK.B", "ZZZZ", "A", "aapl"):
            self.assertEqual(D.stable_key_half(t), r4.stable_key_half(t), t)

    def test_the_published_1266_1265_shape_is_a_roughly_even_split(self):
        ts = ["T%04d" % i for i in range(4000)]
        h = [D.stable_key_half(t) for t in ts]
        self.assertAlmostEqual(sum(h) / len(h), 0.5, delta=0.03)

    def test_the_census_controls_reproduce_on_the_real_panel(self):
        """3,545 build-quadrant half-0 names and 459 names ever in the tier -- the two counts
        `DIPCALL_CENSUS.json` published. Two independent controls that this item's tier logic is
        the census's object."""
        if not os.path.isfile(D.panel_path()):
            _skip(self, "UNIVERSE_BIAS_PANEL_full.pkl absent (data/ is gitignored)")
        p = pd.read_pickle(D.panel_path())
        p["date"] = p["date"].astype(str)
        p["ticker"] = p["ticker"].astype(str)
        bq = p[(p["date"] >= "2009") & (p["date"] <= D.BUILD_HI)]
        h0 = set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"])
        self.assertEqual(len(h0), 3545)
        sched = D.tier_schedule()
        ever = 0
        for t, v in sched.items():
            if t not in h0:
                continue
            caps = [c for d, c in v if "2009" <= d <= D.BUILD_HI]
            if caps and max(caps) >= D.TIER_FLOOR:
                ever += 1
        self.assertEqual(ever, 459)


# =============================================================================================
# 10. THE EMBARGO AND THE HORIZON-INSIDE-THE-BUILD-YEARS RULE
# =============================================================================================
class HalvesAndEmbargo(unittest.TestCase):
    def test_the_half_boundary_is_the_registered_one(self):
        self.assertEqual(D.HALF_BOUNDARY, "2015-01-01")
        self.assertEqual(D.half_of("2014-12-31"), "early")
        self.assertEqual(D.half_of("2015-01-02"), "late")

    def test_an_event_whose_horizon_CROSSES_the_boundary_is_detected(self):
        dates = ["2014-12-29", "2014-12-30", "2014-12-31", "2015-01-02", "2015-01-05"]
        self.assertTrue(D.crosses_boundary(dates, 0, 3))
        self.assertFalse(D.crosses_boundary(dates, 3, 1))
        self.assertFalse(D.crosses_boundary(dates, 0, 1),
                         "an event and horizon wholly inside the early half must NOT be dropped")

    def test_the_whole_horizon_must_lie_inside_the_build_years(self):
        self.assertTrue(D.horizon_ok(100, 50, 21, 90))
        self.assertFalse(D.horizon_ok(100, 80, 21, 90),
                         "a horizon reaching past the build quadrant was accepted")
        self.assertFalse(D.horizon_ok(100, 95, 21, 999),
                         "a horizon reaching past the END OF THE SERIES was accepted")


# =============================================================================================
# 11. THE KILL ARTIFACT'S OWN CLAIMS
# =============================================================================================
class KillArtifact(unittest.TestCase):
    def _art(self):
        p = D.out_path("DIPCALL_KILLS.json")
        if not os.path.isfile(p):
            _skip(self, "DIPCALL_KILLS.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)

    def test_the_kill_pass_touched_no_outcome(self):
        a = self._art()
        self.assertFalse(a["forward_return_touched"])
        self.assertFalse(a["abnormal_return_touched"])
        self.assertEqual(a["trials_this_pass"], 0)

    def test_K1_fired_and_the_floor_is_the_REGISTERED_one(self):
        """The result this item reports. If a successor silently lowers the floor, this goes red."""
        a = self._art()
        self.assertEqual(a["K1_event_count"]["floor"], D.MIN_EVENTS_PER_CELL)
        self.assertFalse(a["K1_event_count"]["pass"])
        self.assertFalse(a["all_kills_pass"])

    def test_the_TIER_cells_decide_K1_and_the_full_universe_does_not(self):
        """Charter Stage 1b: the tier governs advancement. The full-universe cells all CLEAR the
        floor, so if the kill were read off them it would not have fired -- which is exactly why
        the artifact must record which population decided it."""
        a = self._art()
        cells = a["K1_event_count"]["cells"]
        tier = {k: v for k, v in cells.items() if k.startswith("tier|")}
        full = {k: v for k, v in cells.items() if k.startswith("full|")}
        self.assertLess(min(tier.values()), D.MIN_EVENTS_PER_CELL)
        self.assertGreaterEqual(min(full.values()), D.MIN_EVENTS_PER_CELL)
        self.assertIn("tier", a["K1_event_count"]["note"])

    def test_the_tier_clears_the_50_position_floor_so_the_kill_is_not_a_size_artefact(self):
        a = self._art()
        self.assertEqual(a["tier_size_per_date"]["dates_below_floor"], 0)
        self.assertGreaterEqual(a["tier_size_per_date"]["per_date_min"],
                                D.CONTRACT_MIN_POSITIONS)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
