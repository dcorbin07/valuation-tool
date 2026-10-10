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
        proved a withdrawn arm by removing its refusal and thereby RAN it.

        THIS TEST DELIBERATELY TOUCHES NO REAL PATH, so it runs everywhere including CI. Its
        first cut called `D.out_path(arm.KILLS)` just to prove the monkeypatch was undone, which
        reached `data_root()` and ABORTED on a runner with no `data/`. The restoration is proved
        by FUNCTION IDENTITY instead, which is the thing actually being checked.
        """
        import importlib
        import tempfile
        arm = importlib.import_module("scripts.dipcall_arm")
        before = D.out_path

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
                        arm.require_kills("DIPCALL")
                    msgs[label] = str(cm.exception)
                finally:
                    D.out_path = orig

        self.assertIn("ABSENT", msgs["absent"])
        self.assertIn("FIRED", msgs["fired"])
        self.assertIn("K1_event_count", msgs["fired"],
                      "the refusal does not name WHICH kill fired")
        self.assertNotEqual(msgs["absent"], msgs["fired"])
        # The monkeypatch is undone — proved by identity, which touches no path.
        self.assertIs(D.out_path, before)

    def test_the_gate_is_CONDITIONAL_in_the_syntax_tree_not_hard_coded(self):
        """A refusal that cannot fire is not a refusal. `all_kills_pass` must be READ, and the
        arm's `main` must CALL the gate -- read from the AST so a docstring cannot satisfy it."""
        tree = ast.parse(_src("scripts/dipcall_arm.py"))
        fn = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn("require_kills", fn)
        src = ast.dump(fn["require_kills"])
        self.assertIn("all_kills_pass", src)
        # ONE scoring path serves BOTH registers, so the artifact it gates on must be a
        # PARAMETER. A hard-coded name would make DIP-CALL-2 read DIP-CALL's kill artifact --
        # which FIRED -- or silently clobber a landed one.
        self.assertIn("prefix", [a.arg for a in fn["require_kills"].args.args],
                      "the gate is not parameterised on the artifact prefix")
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
        if not D.have_data():
            _skip(self, "no populated data root (data/ is gitignored, so CI has none)")
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
        if not D.have_data():
            _skip(self, "no populated data root (data/ is gitignored, so CI has none)")
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
        if not D.have_data():
            _skip(self, "no populated data root (data/ is gitignored, so CI has none)")
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


# =============================================================================================
# 12. DIP-CALL-2 — the logic that actually produced the verdict
# =============================================================================================
class Dipcall2(unittest.TestCase):
    """`PREREG_dipcall2.md`. The load-bearing one is `test_BOTH_definitions_must_pass...`: the
    h21 arm met every condition on the own-normal definition and failed the economic floor on
    the market-adjusted one, so the conjunction over BOTH definitions is the rule that produced
    FAILS. If that ever silently became an OR, this register would read as a pass."""

    def test_the_register_exists_and_was_committed_ALONE(self):
        reg = "PREREG_dipcall2.md"
        self.assertTrue(os.path.isfile(os.path.join(REPO, reg)))

        def git(*a):
            return subprocess.run(("git",) + a, cwd=REPO, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL).stdout.decode("utf-8", "replace")
        sha = ""
        for line in git("log", "--format=%H", "--", reg).splitlines():
            sha = line.strip()
        if not sha:
            _skip(self, "no git history for %s in this checkout" % reg)
        files = [x for x in git("show", "--name-only", "--format=", sha).split() if x]
        self.assertEqual(files, [reg],
                         "the successor register was NOT committed alone: %s" % files)

    def test_the_register_records_the_news_arm_as_STRUCTURALLY_UNREACHABLE(self):
        """C2. The arm must be RECORDED, not silently dropped -- an absent arm reads as a design
        that never had one."""
        txt = _src("PREREG_dipcall2.md")
        self.assertIn("STRUCTURALLY UNREACHABLE", txt)
        self.assertIn("UNTESTED, NOT NULL", txt)
        self.assertIn("2.97%", txt, "the measurement behind the claim is not stated")

    def test_the_register_keeps_BH_k_at_10_and_says_why(self):
        """C4. The true batch is 8; shrinking k would make every threshold easier (W-28)."""
        self.assertIn("`k` = 10", _src("PREREG_dipcall2.md"))
        self.assertEqual(D.BH_K, 10)

    def test_BOTH_definitions_must_pass_and_an_OR_would_have_flipped_the_verdict(self):
        """THE RULE THAT PRODUCED THE VERDICT, reproduced on the arm's own banked numbers: the
        h21 cell PASSES on `own` and FAILS the economic floor on `mkt`, so an any-definition
        rule would report a PASS where the register reports FAILS."""
        p = D.out_path("DIPCALL2_ARM.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL2_ARM.json absent (data/ is gitignored, so CI has none)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        v = a["verdicts_section_2f"]["h21|no_news"]
        self.assertTrue(all(v["checks"]["own"].values()),
                        "the banked h21 own-normal cell no longer meets every condition")
        self.assertFalse(all(v["checks"]["mkt"].values()),
                         "the banked h21 market-adjusted cell no longer fails")
        self.assertEqual(v["verdict"], "FAILS")
        self.assertFalse(a["step1_pass"])
        self.assertEqual(a["step1_passing_arms"], [])
        # The condition that fails is the ECONOMIC FLOOR, not significance -- which is what
        # makes the result "real but sub-cost" rather than "not detected".
        self.assertFalse(v["checks"]["mkt"]["economic_floor"])
        self.assertTrue(v["checks"]["mkt"]["date_clustered_t"],
                        "the market-adjusted h21 cell was significant; if that changes the "
                        "real-but-sub-cost reading no longer holds")

    def test_the_two_kill_artifacts_are_DISTINCT_objects(self):
        """DIP-CALL's kill artifact FIRED and DIP-CALL-2's PASSED. ONE scoring path serves both,
        so if the prefix were ignored the successor would read the predecessor's fired gate --
        or clobber a landed artifact."""
        if not D.have_data():
            _skip(self, "no populated data root (data/ is gitignored, so CI has none)")
        got = {}
        for pref in ("DIPCALL", "DIPCALL2"):
            q = D.out_path("%s_KILLS.json" % pref)
            if not os.path.isfile(q):
                _skip(self, "%s absent" % q)
            with io.open(q, encoding="utf-8") as fh:
                got[pref] = json.load(fh)
        self.assertFalse(got["DIPCALL"]["all_kills_pass"])
        self.assertTrue(got["DIPCALL2"]["all_kills_pass"])
        self.assertEqual(sorted(got["DIPCALL"]["gated_arms"]), sorted([D.NEWS, D.NO_NEWS]))
        self.assertEqual(got["DIPCALL2"]["gated_arms"], [D.NO_NEWS])
        # Every cell is still REPORTED in both, never absent.
        for pref in ("DIPCALL", "DIPCALL2"):
            cells = got[pref]["K1_event_count"]["cells"]
            self.assertIn("tier|h21|news|early", cells)
            self.assertIn("tier|h21|no_news|early", cells)

    def test_the_clustered_se_behaves_in_BOTH_directions(self):
        """A2. A clustered se that always equals the iid one absorbs nothing; one that is always
        huge is not measuring the data. Both directions, on synthetic data."""
        from scripts import dipcall_arm as ARM
        rng = np.random.default_rng(5)
        n, g = 2000, 100
        groups = np.repeat(np.arange(g), n // g)
        y = rng.normal(0, 1, n)                      # NO within-cluster structure
        _, se_c, _, _ = ARM.clustered(y, groups)
        se_iid = float(np.std(y, ddof=1) / np.sqrt(n))
        self.assertLess(abs(se_c / se_iid - 1.0), 0.35)
        shock = rng.normal(0, 1, g)                  # PERFECT within-cluster correlation
        y2 = shock[groups]
        _, se_c2, _, _ = ARM.clustered(y2, groups)
        self.assertGreater(se_c2 / (float(np.std(y2, ddof=1)) / np.sqrt(n)), 3.0)

    def test_the_permutation_sampler_is_exact_where_it_must_be(self):
        """Two degenerate cases with KNOWN answers, so the sampler cannot be plausibly wrong."""
        from scripts import dipcall_arm as ARM
        # (a) every pool value on a date identical -> every draw returns that value exactly
        pool_v = np.array([3.0] * 10 + [7.0] * 10, dtype=float)
        pool_d = np.array([1] * 10 + [2] * 10, dtype=np.int32)
        arm_d = np.array([1, 1, 2], dtype=np.int32)
        r = ARM.permutation_null(pool_v, pool_d, arm_d, 50, 0)
        self.assertAlmostEqual(r["p95"], (3.0 + 3.0 + 7.0) / 3.0, places=12)
        self.assertAlmostEqual(r["p05"], (3.0 + 3.0 + 7.0) / 3.0, places=12)
        # (b) sampling the WHOLE pool of a date returns that date's exact mean
        r2 = ARM.permutation_null(np.array([1.0, 2.0, 3.0, 4.0]),
                                  np.array([5, 5, 5, 5], dtype=np.int32),
                                  np.array([5, 5, 5, 5], dtype=np.int32), 20, 0)
        self.assertAlmostEqual(r2["null_mean"], 2.5, places=12)

    def test_the_own_minus_market_IDENTITY_holds(self):
        """C4's identity is what explains the verdict: own - mkt = r_market - h * mu_prior."""
        p = D.out_path("DIPCALL2_CONTROLS.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL2_CONTROLS.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            c = json.load(fh)["C4_why_the_definitions_disagree"]
        self.assertTrue(c["pass"])
        for h in ("h5", "h21"):
            self.assertLess(c[h]["identity_abs_dev_pp"], c["tolerance_pp"])
        # the MARKET leg is the larger term, which is the whole finding
        self.assertGreater(c["h21"]["mean_market_window_return_pp"],
                           c["h21"]["mean_h_times_own_trailing_mean_pp"])

    def test_no_survivor_filtering_occurred(self):
        """Section 2e / A11. Every name whose series ends inside a horizon must be TERMINAL, so
        the administrative-censor count is ZERO on this panel."""
        p = D.out_path("DIPCALL2_ARM.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL2_ARM.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        self.assertEqual(a["censoring"]["administrative_dropped"], 0)
        self.assertGreater(a["censoring"]["terminal_used"], 0)


# =============================================================================================
# 13. DIP-CALL-3 — THE 1999-2008 ERA
# =============================================================================================
class Dipcall3(unittest.TestCase):
    """`PREREG_dipcall3.md`. The load-bearing ones are `test_the_era_gate_is_NON_VACUOUS...`
    (without `B1` every pre-2004 event reads NO-NEWS because the SOURCE is silent, which would
    have fired on 34.62% of this era's tier events) and `test_a_REFUSED_cell_is_NOT_RUN...`
    (`K1` refused both no-news cells, so an arm that scored them anyway would be reporting a
    measurement the register forbids)."""

    REG = "PREREG_dipcall3.md"

    def test_the_register_exists_and_was_committed_ALONE_and_is_an_ANCESTOR(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, self.REG)))

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
        self.assertEqual(anc.returncode, 0, "the register commit is not an ancestor of HEAD")

    def test_the_register_declares_the_eleven_amendments_and_the_void_conditions(self):
        txt = _src(self.REG)
        for a in ["### B%d" % i for i in range(1, 12)]:
            self.assertIn(a, txt, "the register is missing amendment %s" % a)
        self.assertIn("VOID CONDITIONS", txt)
        self.assertIn("LABELLED UNCALIBRATED", txt)
        # B10: the hypothesis is admittedly post-hoc, so a pass could only ever be FIRST evidence
        self.assertIn("FIRST EVIDENCE", txt.upper())

    def test_the_register_records_that_POOL_SIZE_already_read_this_era(self):
        """The prompt's own disclosure requirement: this era is not virgin, `POOL-SIZE` read it
        once for pool WIDTH. Recording it is what stops a successor calling this a first look."""
        self.assertIn("POOL-SIZE", _src(self.REG))

    # ------------------------------------------------------------------ B1, the era news gate
    def test_the_era_gate_is_INERT_when_the_source_covers_the_era(self):
        """`news_lo = None` is the build era's case, so the landed DIP-CALL-2 classification is
        bit-identical and this register cannot have moved a published number."""
        dates = ["1999-03-01", "2006-01-04", "2008-12-30"]
        code = np.array([D.NEWS, D.NO_NEWS, D.NEWS], dtype=object)
        out, n = D.apply_news_era_gate(dates, code, None, D.NEWS, D.UNKNOWN)
        self.assertEqual(n, 0)
        self.assertEqual(list(out), list(code))
        self.assertIsNone(D.era(D.ERA_BUILD)["news_lo"],
                          "the build era must keep news_lo = None or DIP-CALL-2 moves")

    def test_the_era_gate_is_NON_VACUOUS_and_has_a_POSITIVE_CONTROL(self):
        """Both directions. A gate that relabelled everything would pass the first half alone."""
        dates = ["1999-03-01", "2004-08-22", "2004-08-23", "2007-06-01"]
        code = np.array([D.NEWS, D.NO_NEWS, D.NO_NEWS, D.NEWS], dtype=object)
        out, n = D.apply_news_era_gate(dates, code, D.CODE22_FIRST, D.NEWS, D.UNKNOWN)
        self.assertEqual(n, 2, "the two rows before the source's first date must be gated")
        self.assertEqual(out[0], D.UNKNOWN)
        self.assertEqual(out[1], D.UNKNOWN)
        # POSITIVE CONTROL: a row ON the first date and a row after it SURVIVE their class
        self.assertEqual(out[2], D.NO_NEWS, "a row ON news_lo must not be gated")
        self.assertEqual(out[3], D.NEWS, "a row after news_lo must keep its class")

    def test_an_already_UNKNOWN_row_is_not_double_counted(self):
        """`A1b`'s third state survives the era gate rather than being re-gated."""
        out, n = D.apply_news_era_gate(["1999-03-01"], np.array([D.UNKNOWN], dtype=object),
                                       D.CODE22_FIRST, D.NEWS, D.UNKNOWN)
        self.assertEqual(n, 0)
        self.assertEqual(out[0], D.UNKNOWN)

    def test_CODE22_FIRST_is_the_measured_date_and_is_stated_in_the_register(self):
        self.assertEqual(D.CODE22_FIRST, "2004-08-23")
        self.assertIn(D.CODE22_FIRST, _src(self.REG))

    # --------------------------------------------------------------------- the era definitions
    def test_era_REFUSES_an_unknown_name(self):
        with self.assertRaises(SystemExit):
            D.era("no-such-era")

    def test_the_era_carries_NO_ticker_half_split(self):
        """`B5`. The charter treats a pre-2009 era as a THIRD separate look, not a half of the
        2×2 budget, so halving the tickers here would discard half the era for nothing."""
        self.assertIsNone(D.era(D.ERA_OOS9908)["ticker_half"])
        self.assertEqual(D.era(D.ERA_BUILD)["ticker_half"], 0)
        self.assertIn("### B5", _src(self.REG))

    def test_the_eras_do_not_share_a_tier_panel(self):
        self.assertNotEqual(D.era(D.ERA_BUILD)["tier_panel"],
                            D.era(D.ERA_OOS9908)["tier_panel"])

    # ---------------------------------------------------- K1 is a PER-CELL refusal, enforced
    def test_the_arm_READS_the_cleared_cell_list_rather_than_its_own_judgement(self):
        """Source-level, because this is the one guard between a refused cell and a reported
        number. Read the AST rather than grepping, per `MA49`."""
        tree = ast.parse(_src("scripts/dipcall3_arm.py"))
        lits = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertIn("cells_cleared_for_the_arm", lits,
                      "the arm does not read the kill pass's cleared-cell list")

    def test_a_REFUSED_cell_is_NOT_RUN_and_carries_no_mean(self):
        p = D.out_path("DIPCALL3_ARM.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL3_ARM.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        refused = a["cells_refused_by_K1_and_NOT_RUN"]
        self.assertTrue(refused, "K1 refused nothing, so this guard is vacuous here")
        for label in refused:
            self.assertNotIn(label, a["cells_cleared"])
            v = a["verdicts"].get(label)
            self.assertIsNotNone(v, "a refused cell must still be RECORDED, not dropped")
            self.assertIn("NOT RUN", v["verdict"])
            self.assertNotIn("checks", v, "a refused cell must carry no scored checks")
            self.assertNotIn(label, a["passing_cells"])

    def test_the_no_news_cells_are_the_refused_ones_so_the_replication_did_NOT_run(self):
        """The sentence a reader most needs: the faithful out-of-sample replication of
        DIP-CALL-2's NO-NEWS arm is the thing `K1` refused, so the POOLED cells are a declared
        different object (section 5 void condition 3)."""
        p = D.out_path("DIPCALL3_ARM.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL3_ARM.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        self.assertEqual(sorted(a["cells_refused_by_K1_and_NOT_RUN"]),
                         ["no_news|h126", "no_news|h63"])
        self.assertEqual(sorted(a["cells_cleared"]), ["pooled|h126", "pooled|h63"])

    def test_BH_k_stays_4_even_though_only_two_cells_RAN(self):
        """`W-28`. A cell that cannot be built does not shrink `k`; shrinking it would make
        every surviving threshold easier after the fact."""
        p = D.out_path("DIPCALL3_ARM.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL3_ARM.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            a = json.load(fh)
        self.assertEqual(a["bh"]["k"], 4)
        self.assertEqual(len(a["bh"]["rows"]), 2)
        self.assertEqual(a["bh"]["q"], D.BH_Q)

    def test_the_power_floor_was_RAISED_by_the_eras_own_dispersion_never_lowered(self):
        """`B3` committed `max(1865, required_n from THIS era's own measured sd)`, so the
        correction to the draft's arithmetic can only ever make the bar harder."""
        p = D.out_path("DIPCALL3_KILLS.json") if D.have_data() else ""
        if not p or not os.path.isfile(p):
            _skip(self, "DIPCALL3_KILLS.json absent (data/ is gitignored)")
        with io.open(p, encoding="utf-8") as fh:
            k = json.load(fh)
        for cell in k["K1_design_effect"]["by_cell"].values():
            self.assertGreaterEqual(cell["bar"], 1865.0)

    # -------------------------------------------------------------- no option arm, no options N
    def test_there_is_NO_option_arm_and_no_options_trial(self):
        """`B9`. The draft's own arithmetic shows a call cannot capture a ~1pp drift against a
        12-20pp implied move, so this register is SHARES only and charges equity alone."""
        txt = _src(self.REG)
        self.assertIn("### B9", txt)
        src = _src("scripts/dipcall3_arm.py") + _src("scripts/dipcall3_kills.py")
        for banned in ("resolve_chains", "pick_contract", "options_fill", "simulate_trade"):
            self.assertNotIn(banned, src,
                             "an options primitive reached a shares-only register: %s" % banned)

    def test_the_arm_refuses_without_a_passing_kill_artifact(self):
        """Two refusal states must be DISTINCT -- a hard-coded refusal cannot tell 'never ran'
        from 'ran and fired' (`E-1`)."""
        src = _src("scripts/dipcall3_arm.py")
        self.assertIn("is ABSENT", src)
        self.assertIn("cleared NO cell", src)


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    if _SKIPS:
        print("\nSKIPPED LOUDLY (%d) - these are NOT passes:" % len(_SKIPS))
        for s in sorted(set(_SKIPS)):
            print("  - %s" % s)
    raise SystemExit(0 if r.wasSuccessful() else 1)
