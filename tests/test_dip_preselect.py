# -*- coding: utf-8 -*-
"""ITEM 23b — the screen valued twelve names out of 242 and reported the result as coverage.

WHAT THE LIVE SERVICE RETURNED
------------------------------
After item 19 fixed the wiring, `/api/dip?min_drawdown=0.10`::

    n_universe 1490 | prefilter rejects 1245 | eligible 242
    n_measured 12   | n_unmeasured 0 | capped 230 | rows 1

So the screen was eligible to look at 242 names, looked at 12, and the page said what the
market was doing. The 12 were the DEEPEST 12 -- the sort is exact, because `high_prox`'s
within-date z-score is strictly monotone in the drawdown -- so the cap was not hiding anything
*deeper*. It was hiding everything BETWEEN the threshold and the twelfth name's depth, which at
a 20% threshold is most of the interesting range.

THE DIAGNOSTIC THAT DECIDED THE DESIGN, taken on the service at a 10% threshold: of the 12
measured, six were 51-66% down (PODD 61.98, TME 66.48, LIF 61.13, BSX 59.42, MBLY 52.25,
NKE 51.36) and **five of those six were rejected on health**, leaving one row. So the health
gate was doing the work among the names that were checked -- and 230 names between 20% and 51%
were never checked at all.

THE CAUSE, WHICH IS A NUMBER THAT WAS COMPUTED AND THROWN AWAY
--------------------------------------------------------------
`prices.py` and `broker_universe.py` both compute ``high_prox = price / 52-week high`` for every
name in every scan. `screen.py` persisted only its WITHIN-DATE Z-SCORE (`extra["numbers"]` is
keyed on `z_<name>`), and a z-score can ORDER names by drawdown but cannot state one. So the
screen could rank 242 names for free and had to spend a full valuation on each to learn its
depth -- which is why it valued twelve. ``1 - high_prox`` IS the drawdown.

WHAT THIS SUITE PINS
--------------------
The free drawdown, the two-stage selection, the SLACK that makes the preselector safe, the
loud degradation on an older snapshot, and the payload fields the page is now required to
state. It does not re-test the wiring: `tests/test_dip_wiring.py` owns that.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.web import dip                                      # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def row(ticker, high_prox=None, **kw):
    """A snapshot row that clears the prefilter and the row-level disqualifiers."""
    r = {"ticker": ticker, "name": ticker + " Inc", "sector": "Technology",
         "price": 100.0, "market_cap": 5e10, "hot_score": 60.0, "rank": 1,
         "z_quality": 0.5, "z_growth": 0.5,
         "fair_value": 120.0, "upside": 0.2,
         "extra": {"numbers": {}}}
    if high_prox is not None:
        r["extra"]["high_prox"] = high_prox
    r.update(kw)
    return r


def measurer(depths, subs=None):
    """A `measure` that answers from a dict of ticker -> drawdown. Counts its own calls."""
    calls = []
    # THE REAL FLOORS, read from the module rather than typed: `HEALTH_FLOORS` is
    # {quality, health, growth} at 66.0, and the first cut of this fixture used 60s with no
    # `health` key at all -- so every row was health-rejected and three tests failed for a
    # reason that had nothing to do with what they were testing. This project's own note on
    # the same trap: "dip fixture had no subscores so HEALTH_FLOORS filtered all rows".
    good = subs or dict({k: v + 10.0 for k, v in dip.HEALTH_FLOORS.items()},
                        value=70.0, momentum=70.0)

    def _m(r):
        t = r["ticker"]
        calls.append(t)
        dd = depths.get(t)
        if dd is None:
            return None
        return {"drawdown": dd, "price": 100.0, "high_52w": 100.0 / (1.0 - dd),
                "subs": dict(good), "checks": {}, "fair_value": 120.0, "upside": 0.2,
                "score": 60.0, "confidence": "medium", "days_since_high": 30}

    _m.calls = calls
    return _m


class TheFreeDrawdown(unittest.TestCase):
    """`1 - high_prox`, from the snapshot, with no valuation and no network."""

    def test_it_reads_the_raw_ratio(self):
        self.assertAlmostEqual(dip.cheap_drawdown(row("A", high_prox=0.4)), 0.6, places=9)

    def test_it_reads_a_flat_row_too(self):
        """Some callers hand `screen` rows with the number at the top level."""
        self.assertAlmostEqual(dip.cheap_drawdown({"high_prox": 0.75}), 0.25, places=9)

    def test_a_name_at_its_high_is_zero_and_not_negative(self):
        """Above its own 52-week high reads as a small negative, which is zero drawdown."""
        self.assertEqual(dip.cheap_drawdown({"high_prox": 1.02}), 0.0)
        self.assertEqual(dip.cheap_drawdown({"high_prox": 1.0}), 0.0)

    def test_an_absent_ratio_is_None_and_NEVER_zero(self):
        """THE LOAD-BEARING ONE. Treating unknown as "shallow" would delete the deepest names
        from the page the screen exists to fill -- `_z_high_prox`'s own note, one layer on."""
        self.assertIsNone(dip.cheap_drawdown(row("A")))
        self.assertIsNone(dip.cheap_drawdown({}))

    def test_junk_is_None_rather_than_an_exception(self):
        for bad in ("", "abc", None, float("nan"), 0.0, -1.0, {}):
            self.assertIsNone(dip.cheap_drawdown({"high_prox": bad}), repr(bad))

    def test_it_does_not_read_the_z_score_by_mistake(self):
        """`extra["numbers"]["high_prox"]` is the Z-SCORE and is a different number. Reading it
        as a ratio would produce a confident, plausible, wrong drawdown -- and a z-score of
        -1.4 would read as a 240% fall."""
        r = row("A")
        r["extra"]["numbers"]["high_prox"] = -1.4
        self.assertIsNone(dip.cheap_drawdown(r))


class TheValuationBudgetGoesToQualifiers(unittest.TestCase):
    """The defect, and the repair, on a population shaped like the live one."""

    def setUp(self):
        # 20 names. The five deepest are 60%+; ten sit between 25% and 35%; five are flat.
        self.rows = []
        self.depths = {}
        for i in range(5):
            t = "DEEP%d" % i
            self.rows.append(row(t, high_prox=0.40 - i * 0.02))
            self.depths[t] = 0.60 + i * 0.02
        for i in range(10):
            t = "MID%d" % i
            self.rows.append(row(t, high_prox=0.70 - i * 0.01))
            self.depths[t] = 0.30 + i * 0.01
        for i in range(5):
            t = "FLAT%d" % i
            self.rows.append(row(t, high_prox=0.99))
            self.depths[t] = 0.01

    def test_a_budget_smaller_than_the_qualifying_set_SPANS_it(self):
        """REPOINTED BY ITEM 33(b), and this test's own docstring predicted the repoint: it read
        "that is still true -- what changed is WHICH names compete for it", and item 33 changed
        it again.

        It used to assert `all(t.startswith("DEEP"))` -- the budget spent entirely on the
        deepest names. That was the honest description of the behaviour and it was the DEFECT
        measured on the live service: at `min_drawdown=0.10`, 204 names qualified, the 12
        deepest were valued, and the page showed two names about 60% down. A user asking for
        "down 10%" saw only the most extreme crashes.

        The budget is unchanged -- a valuation is a real cost -- so what it buys changed: a
        sample ACROSS the qualifying range. The deepest name is still always valued; so is the
        shallowest qualifier. And the thing item 23 won is untouched: a FLAT name still never
        buys a valuation."""
        m = measurer(self.depths)
        out = dip.screen(self.rows, min_drawdown=0.25, measure=m, shortlist=5)
        self.assertEqual(len(m.calls), 5)
        self.assertFalse([t for t in m.calls if t.startswith("FLAT")],
                         "item 23's win was lost: a flat name bought a valuation")
        self.assertTrue(m.calls[0].startswith("DEEP"), m.calls)
        # The property is simply that the budget is NOT the deepest-N prefix. My first cut of
        # this wrote a self-referential assertNotEqual that could not fail the way it read;
        # one clear assertion is better than two clever ones.
        self.assertTrue(any(not t.startswith("DEEP") for t in m.calls),
                        "every valued name came from the deep end: %r" % (m.calls,))

    def test_the_flat_names_never_buy_a_valuation(self):
        """THE REPAIR. Fifteen names qualify at 25%; five do not. With a budget of 20 the old
        code would have valued all 20 -- five of them names it already knew were 1% down."""
        m = measurer(self.depths)
        out = dip.screen(self.rows, min_drawdown=0.25, measure=m, shortlist=20)
        self.assertEqual(len(m.calls), 15, m.calls)
        self.assertFalse([t for t in m.calls if t.startswith("FLAT")],
                         "a valuation was spent on a name the scan already said was flat")
        self.assertEqual(len(out["rows"]), 15)

    def test_it_reports_qualified_against_checked(self):
        out = dip.screen(self.rows, min_drawdown=0.25,
                         measure=measurer(self.depths), shortlist=20)
        self.assertEqual(out["n_checked_for_depth"], 20)
        self.assertEqual(out["n_qualified_on_depth"], 15)
        self.assertIs(out["preselect_available"], True)
        # REPOINTED BY ITEM 33(b). This asserted the phrase "deep enough", which belonged to a
        # note that also reported "the %d-of-%d eligible names" using two DIFFERENT
        # denominators -- `n_qualified` (which counts names kept because their depth is unknown)
        # over `n_with_cheap` (which counts only names a depth could be read for). On the live
        # service that rendered as "the 204-of-163 eligible names", which is impossible on its
        # face. The wording is replaced; what is asserted now is the PROPERTY the wording got
        # wrong -- that the counts nest and the ratio is possible.
        self.assertEqual(out["n_qualified_on_depth"],
                         out["n_depth_pass"] + out["n_depth_unknown_kept"])
        self.assertLessEqual(out["n_qualified_on_depth"], out["n_eligible"])
        self.assertIn("of the %d eligible" % out["n_eligible"], out["preselect_note"])

    def test_the_cap_now_applies_to_the_qualifiers(self):
        out = dip.screen(self.rows, min_drawdown=0.25,
                         measure=measurer(self.depths), shortlist=5)
        self.assertEqual(out["n_measured"], 5)
        self.assertEqual(out["capped"], 10, "the cap should be 15 qualifiers minus 5 measured")

    def test_a_higher_threshold_narrows_what_is_valued(self):
        """At the control's CEILING, which is what a user can actually ask for.

        The first cut of this test passed 0.55 and asserted that only the five deep names were
        valued. `clamp_drawdown` silently clamps to `MIN_DRAWDOWN_CEIL` (0.40), so the real
        floor was 0.35 and the five shallowest MIDs qualified -- the test was asserting against
        a threshold the screen cannot be given. Pinned at the ceiling, read from the module.
        """
        m = measurer(self.depths)
        dip.screen(self.rows, min_drawdown=dip.MIN_DRAWDOWN_CEIL, measure=m, shortlist=20)
        # floor = 0.40 - 0.05 = 0.35, so MID5..MID9 (0.35..0.39 on the snapshot) qualify too.
        self.assertEqual(sorted(m.calls),
                         sorted(["DEEP%d" % i for i in range(5)]
                                + ["MID%d" % i for i in range(5, 10)]))
        self.assertNotIn("FLAT0", m.calls)

    def test_a_threshold_above_the_ceiling_is_clamped_and_not_honoured(self):
        """Stated rather than discovered, because it cost this suite a false failure: the
        control's range is [{floor}, {ceil}] and anything outside it is clamped, so a caller
        asking for 55% is asking for {ceil}."""
        out = dip.screen(self.rows, min_drawdown=0.55,
                         measure=measurer(self.depths), shortlist=20)
        self.assertEqual(out["min_drawdown"], dip.MIN_DRAWDOWN_CEIL)

    def test_the_rendered_drawdown_is_still_the_MEASURED_one(self):
        """The preselector is a necessary condition, never the authority.

        A name whose snapshot says 30% and whose valuation says 5% must not appear: the free
        number is yesterday's and the measured one is now.
        """
        depths = dict(self.depths)
        depths["MID0"] = 0.05
        out = dip.screen(self.rows, min_drawdown=0.25,
                         measure=measurer(depths), shortlist=20)
        self.assertNotIn("MID0", [r["ticker"] for r in out["rows"]])


class TheSlackIsWhatMakesItSafe(unittest.TestCase):
    """The free number is the snapshot's and the rendered number is today's, so a tight
    preselector would silently drop a name that qualifies now because it did not yesterday."""

    def test_a_name_just_under_the_threshold_still_buys_a_valuation(self):
        rows = [row("EDGE", high_prox=1.0 - (0.20 - 0.03))]       # 17% down on the snapshot
        m = measurer({"EDGE": 0.22})                              # 22% down when valued
        out = dip.screen(rows, min_drawdown=0.20, measure=m, shortlist=10)
        self.assertEqual(m.calls, ["EDGE"],
                         "a name three points under the threshold was refused a valuation, so "
                         "a day's move would silently drop it")
        self.assertEqual([r["ticker"] for r in out["rows"]], ["EDGE"])

    def test_a_name_far_under_the_threshold_does_not(self):
        """The positive control: slack is a tolerance, not an escape hatch."""
        rows = [row("FAR", high_prox=0.95)]                       # 5% down
        m = measurer({"FAR": 0.05})
        dip.screen(rows, min_drawdown=0.20, measure=m, shortlist=10)
        self.assertEqual(m.calls, [])

    def test_the_slack_is_published_so_it_cannot_be_a_hidden_constant(self):
        out = dip.screen([row("A", high_prox=0.5)], min_drawdown=0.20,
                         measure=measurer({"A": 0.5}), shortlist=10)
        self.assertEqual(out["preselect_slack"], dip.PRESELECT_SLACK)

    def test_the_slack_is_wider_than_any_row_this_screen_has_rendered(self):
        """A rule about magnitude, stated as one. The shallowest row the live screen has ever
        shown is 51% down; the slack has to cover a day's move, not a quarter's."""
        self.assertGreaterEqual(dip.PRESELECT_SLACK, 0.02)
        self.assertLessEqual(dip.PRESELECT_SLACK, 0.10)


class AnOlderSnapshotDegradesLOUDLY(unittest.TestCase):
    """The live snapshot on the day this was written carries no raw ratio, because the scan
    that writes it had not run since the change. The screen must behave exactly as before and
    SAY so -- a silent fallback to 'the deepest twelve' is the thing being fixed."""

    def setUp(self):
        self.rows = [row("A"), row("B"), row("C")]                # no `high_prox` anywhere
        self.m = measurer({"A": 0.5, "B": 0.4, "C": 0.01})
        self.out = dip.screen(self.rows, min_drawdown=0.20, measure=self.m, shortlist=2)

    def test_it_measures_the_shortlist_exactly_as_before(self):
        self.assertEqual(len(self.m.calls), 2)
        self.assertEqual(self.out["n_measured"], 2)
        self.assertEqual(self.out["capped"], 1)

    def test_it_says_the_preselector_was_unavailable(self):
        self.assertIs(self.out["preselect_available"], False)
        self.assertEqual(self.out["n_checked_for_depth"], 0)
        self.assertIsNone(self.out["n_qualified_on_depth"])

    def test_the_note_names_the_cause_and_the_remedy(self):
        note = self.out["preselect_note"]
        self.assertIn("no 52-week-high ratio", note)
        self.assertIn("deepest-ranked", note)
        self.assertIn("A scan run after this change will carry it", note)

    def test_a_PARTLY_populated_snapshot_keeps_the_unknown_names(self):
        """The dangerous middle case. Mid-migration some rows have the ratio and some do not,
        and a strict rule would delete exactly the ones nobody can rank."""
        rows = [row("HAS", high_prox=0.5), row("HASNT")]
        m = measurer({"HAS": 0.5, "HASNT": 0.45})
        out = dip.screen(rows, min_drawdown=0.20, measure=m, shortlist=10)
        self.assertEqual(sorted(m.calls), ["HAS", "HASNT"])
        self.assertEqual(sorted(r["ticker"] for r in out["rows"]), ["HAS", "HASNT"])
        self.assertEqual(out["n_checked_for_depth"], 1,
                         "only one row carried a free drawdown")


class TheScanPersistsTheRatio(unittest.TestCase):
    """The one-line change that makes any of the above reachable on real data."""

    def test_high_prox_is_in_the_raw_number_allowlist(self):
        """In THE ALLOWLIST, not merely somewhere in the file.

        A DEFECT IN THIS TEST'S FIRST CUT, found by mutation. It walked the whole module for a
        `"high_prox"` constant and passed with the allowlist entry deleted, because
        `screen.py` line 210 carries an unrelated one -- a loop that fills `high_prox` from the
        broker universe where the fundamentals feed left a hole. A positive assertion satisfied
        by an unrelated occurrence: the same family as a ban tripped by a comment, and the
        third time this session.

        So the allowlist is located structurally -- the `for k in [...]` of the dict
        comprehension that builds `extra` -- and the entry is required to be in THAT list.
        """
        import ast
        p = os.path.join(REPO, "valuation", "screener", "screen.py")
        with open(p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        lists = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.DictComp):
                continue
            for gen in node.generators:
                it = gen.iter
                if isinstance(it, (ast.List, ast.Tuple)):
                    vals = [e.value for e in it.elts if isinstance(e, ast.Constant)]
                    # The raw-number allowlist is the one carrying the fundamentals.
                    if "earnings_yield" in vals and "fcf_yield" in vals:
                        lists.append(vals)
        self.assertEqual(len(lists), 1,
                         "expected exactly one raw-number allowlist in screen.py, found %d"
                         % len(lists))
        self.assertIn("high_prox", lists[0],
                      "`high_prox` is not in the raw-number allowlist, so the free drawdown "
                      "can never reach a snapshot and every preselect test above is about a "
                      "code path real data cannot enter")

    def test_the_allowlist_locator_is_not_vacuous(self):
        """It must find a real list with real contents, or the assertion above sees nothing."""
        import ast
        p = os.path.join(REPO, "valuation", "screener", "screen.py")
        with open(p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.DictComp):
                for gen in node.generators:
                    if isinstance(gen.iter, (ast.List, ast.Tuple)):
                        vals = [e.value for e in gen.iter.elts
                                if isinstance(e, ast.Constant)]
                        if "earnings_yield" in vals:
                            self.assertGreater(len(vals), 8)
                            self.assertIn("roe", vals)
                            return
        self.fail("the locator found no raw-number allowlist at all")

    def test_the_raw_ratio_and_the_z_score_are_different_keys(self):
        """They are both called `high_prox`, in two different dicts, and one is a ratio while
        the other is a standard deviation. If the screen ever read the wrong one it would
        produce a confident wrong number rather than fail."""
        import ast
        p = os.path.join(REPO, "valuation", "screener", "screen.py")
        with open(p, encoding="utf-8") as f:
            src = f.read()
        self.assertIn('"z_" + n', src, "the z-score dict no longer prefixes its keys, so the "
                                       "raw ratio and the z-score may now collide")


class TheFleetRecordIsLabelledNotDeleted(unittest.TestCase):
    """ITEM 23's second half, and the two mutations that exposed it was untested.

    I wrote `fleet_history.invalidate_unmeasured_dip_span` and shipped it with no test at all,
    which the harness found by inferring the span from disk and by removing the `through`
    validation -- both passed. A function whose whole job is to write into the evidence record
    is the last place to leave untested.
    """

    def setUp(self):
        import shutil
        import tempfile
        from valuation.edge import fleet_history as FH
        self.FH = FH
        self.root = tempfile.mkdtemp(prefix="f11span-")
        self.addCleanup(shutil.rmtree, self.root, True)
        # A series with three fabricated days inside the span and two REAL days after it.
        for d, n in (("2026-08-10", 0), ("2026-09-01", 0), ("2026-10-02", 0),
                     ("2026-10-04", 3), ("2026-10-05", 2)):
            FH.record("dip_rejects", d, {"n": n, "rows": []}, count=n, root=self.root)

    def _spans(self):
        return [x for x in self.FH.invalid_spans(self.root)
                if (x.get("reason") or "").startswith("ITEM 19")]

    def test_it_invalidates_only_the_bounded_span(self):
        """THE MUTATION THAT WALKED THROUGH: inferring the span from everything on disk would
        swallow the real rows that are already sitting after the repair."""
        out = self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                                     date="2026-10-06")
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(out["applied"]), 1, out)
        a = out["applied"][0]
        self.assertEqual(a["from"], "2026-08-10")
        self.assertEqual(a["to"], "2026-10-02")
        self.assertEqual(a["n_days"], 3)

    def test_the_real_rows_after_the_span_are_NOT_invalidated(self):
        self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                               date="2026-10-06")
        spans = self._spans()
        self.assertEqual(len(spans), 1)
        self.assertLess(spans[0]["to"], "2026-10-04")

    def test_the_rows_themselves_are_untouched(self):
        """APPEND ONLY. A recorder that could erase its own bad days could erase its good
        ones, which is why the rule exists."""
        before = self.FH.read("dip_rejects", self.root, honour_invalidations=False)
        self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                               date="2026-10-06")
        after = self.FH.read("dip_rejects", self.root, honour_invalidations=False)
        self.assertEqual([r["date"] for r in before["rows"]],
                         [r["date"] for r in after["rows"]])
        self.assertEqual(len(after["rows"]), 5)

    def test_a_reader_that_honours_invalidations_FLAGS_the_span(self):
        """KEPT AND FLAGGED, not dropped -- and that is `read`'s stated contract, which this
        test's first cut got wrong.

        It asserted the rows vanished. They do not: `read`'s own docstring says "the rows are
        still returned -- they are kept, not erased -- but a consumer that reads `n` and
        ignores `invalid` is counting fabricated days", and `n_valid` ships beside `n`. That is
        the right design for an append-only record, and asserting deletion would have been
        asserting against the rule this whole mechanism exists to honour.
        """
        self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                               date="2026-10-06")
        r = self.FH.read("dip_rejects", self.root)
        by = {x["date"]: x for x in (r.get("rows") or [])}
        self.assertEqual(r["n"], 5, "a row was erased")
        self.assertEqual(r["n_valid"], 2)
        self.assertEqual(r["n_invalid"], 3)
        for bad in ("2026-08-10", "2026-09-01", "2026-10-02"):
            self.assertIs(by[bad]["invalid"], True, bad)
        for good in ("2026-10-04", "2026-10-05"):
            self.assertIs(by[good]["invalid"], False, good)

    def test_the_path_the_books_use_honours_it(self):
        """`read` is the raw door; `history_for` is what a book calls, and it filters."""
        self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                               date="2026-10-06")
        import inspect
        src = inspect.getsource(self.FH.history_for)
        self.assertIn("invalid", src,
                      "`history_for` does not consult the invalidation, so every consumer "
                      "would still read the fabricated days")

    def test_it_is_idempotent(self):
        self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                               date="2026-10-06")
        again = self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-10-03",
                                                       date="2026-10-07")
        self.assertEqual(again["applied"], [])
        self.assertIn("dip_rejects", again["already_done"])
        self.assertEqual(len(self._spans()), 1)

    def test_a_missing_through_is_REFUSED(self):
        """THE OTHER MUTATION. Without this an empty `through` would invalidate nothing and
        report success, or worse, be read as a date."""
        for bad in ("", None, "nope", "2026-10", "2026-08-05"):
            out = self.FH.invalidate_unmeasured_dip_span(self.root, through=bad)
            self.assertFalse(out["ok"], repr(bad))
            self.assertIn("YYYY-MM-DD", out["reason"])
            self.assertEqual(self._spans(), [], "a refused call still wrote a span")

    def test_a_through_before_the_span_start_is_refused(self):
        """2026-08-06 is the day the Entry wrapper landed; nothing before it is in scope."""
        out = self.FH.invalidate_unmeasured_dip_span(self.root, through="2026-08-05")
        self.assertFalse(out["ok"])

    def test_a_series_with_no_rows_in_span_is_nothing_to_do_not_an_error(self):
        import shutil
        import tempfile
        root = tempfile.mkdtemp(prefix="f11empty-")
        self.addCleanup(shutil.rmtree, root, True)
        self.FH.record("dip_rejects", "2026-10-04", {"n": 1, "rows": []}, count=1, root=root)
        out = self.FH.invalidate_unmeasured_dip_span(root, through="2026-10-03",
                                                     date="2026-10-06")
        self.assertTrue(out["ok"])
        self.assertEqual(out["applied"], [])
        self.assertIn("dip_rejects", out["nothing_to_do"])

    def test_the_reason_names_item_19_and_distinguishes_itself_from_H2(self):
        """Audit #5's `H2` reason describes a screen that does not exist in this repository.
        This screen existed, ran every cycle and measured nothing. Conflating the two would
        make the record claim H2 had covered this."""
        r = self.FH.UNMEASURED_DIP_REASON
        self.assertIn("ITEM 19", r)
        self.assertIn("resultcache.Entry", r)
        self.assertIn("42597e2", r)
        self.assertIn("DIFFERENT CAUSE FROM AUDIT #5", r)
        self.assertNotEqual(r, self.FH.FABRICATED_REASON)

    def test_it_is_a_separate_function_from_the_H2_one(self):
        """One function with two meanings is how the record comes to claim the wrong cause."""
        self.assertIsNot(self.FH.invalidate_unmeasured_dip_span,
                         self.FH.invalidate_fabricated_span)


class TheOldBehaviourIsNotSilentlyKept(unittest.TestCase):
    """Guard against the repair being reverted to a no-op."""

    def test_screen_calls_the_free_drawdown(self):
        import ast
        p = os.path.join(REPO, "valuation", "web", "dip.py")
        with open(p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "screen")
        called = {n.func.id for n in ast.walk(fn)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn("cheap_drawdown", called,
                      "`screen` no longer consults the free drawdown, so the budget is back "
                      "to being spent on the first N eligible names")

    def test_the_measured_set_is_taken_from_the_qualifiers(self):
        import ast
        p = os.path.join(REPO, "valuation", "web", "dip.py")
        with open(p, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "screen")
        for node in ast.walk(fn):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id == "measured_set"):
                txt = ast.unparse(node)
                self.assertIn("qualified", txt,
                              "the measured set is not sliced from the qualifiers: " + txt)
                self.assertNotIn("survivors", txt)
                return
        self.fail("no `measured_set = ...` assignment found in `screen`")


if __name__ == "__main__":
    unittest.main(verbosity=2)
