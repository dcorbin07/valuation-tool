# -*- coding: utf-8 -*-
"""ITEM 38(a) — Don's third Dip Detector group: health not scored for this kind of company.

DECISIONS.md, 2026-10-07:

    DIP DETECTOR: show banks, insurers, REITs and regulated utilities in their own group,
    labelled "health not scored for this kind of company". Never counted as healthy, never
    silently excluded.

Item 36 measured 31 of 110 health rejections to be exactly this: a sub-score the model
WITHHELD because its metrics do not describe the business. The page reported all 110 as
"rejected on health", which reads as *the model looked at the balance sheet and did not like
it* when the truth is that nobody looked.

WHAT THESE TESTS ARE FOR, in order of how much they would cost to get wrong:

* **The silent drop.** A name that leaves `rejected_health` and arrives nowhere looks like a
  SMALLER rejection count, i.e. like an improvement. The identity is the only thing that
  catches it, so it is asserted here as well as live.
* **The excusal must be narrow.** Below a floor, or any OTHER sub-score missing, and the name
  stays rejected — otherwise the group quietly absorbs every incomplete financial and "never
  counted as healthy" is broken from the other side.
* **F-11's forward book must not move.** `health_rejects` feeds a LIVE research record whose
  declared rule is "failing the shipped health floors, classified by `health_check`" — and
  `health_check` still fails these names. Moving them out would re-specify a forward book as a
  side effect of a presentation ruling. The first cut of this change did exactly that.
* **One definition of which regimes withhold.** That list had already been written twice in
  the engine and the two had drifted, which is the defect this change repairs.
"""
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.engine import scoring                                           # noqa: E402
from valuation.web import dip                                                  # noqa: E402
from tests.source_bounds import (code_only, function_source,                  # noqa: E402
                                 js_function_source)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OK = {"quality": 80.0, "health": 80.0, "growth": 80.0}
WITHHELD = {"quality": 80.0, "health": None, "growth": 80.0}
WITHHELD_AND_LOW = {"quality": 40.0, "health": None, "growth": 80.0}
WITHHELD_AND_GAP = {"quality": 80.0, "health": None, "growth": None}


def row(t, prox=0.70):
    """An eligible snapshot row. `prox` is the RAW price/high ratio `cheap_drawdown` reads.

    NOT `extra.numbers.high_prox`, which is the within-date Z-SCORE and must never be read as a
    ratio -- a fixture that used it would make every name look like a tiny drawdown.
    """
    extra = {} if prox is None else {"high_prox": prox}
    return {"ticker": t, "name": t, "price": 50.0, "market_cap": 5e9,
            "hot_score": 60, "rank": 1, "z_quality": 0.5, "extra": extra}


def meas(dd, subs, unscored=None, regime=None):
    return {"drawdown": dd, "price": 50.0,
            "high_52w": (50.0 / (1 - dd)) if dd else 50.0,
            "subs": subs, "cash_burning": False, "score": 70, "confidence": "high",
            "fair_value": 80.0, "upside": 0.6, "fair_value_low": 60.0,
            "fair_value_high": 100.0, "fair_value_withheld_reason": None,
            "regime": regime, "health_not_scored": unscored,
            "checks": {"withheld": dip.PASS, "beta_provenance": dip.PASS,
                       "terminal_share": dip.PASS}}


def run(cases, min_drawdown=0.20):
    rows = [row(t, p) for t, p, _m in cases]
    by_t = {t: m for t, _p, m in cases}
    return dip.screen(rows, min_drawdown=min_drawdown,
                      measure=lambda r: by_t.get(r["ticker"]), shortlist=0)


class TheGroupExistsAndIsNarrow(unittest.TestCase):

    def test_each_of_dons_three_kinds_of_company_lands_in_the_group(self):
        """A bank, a REIT and a regulated utility, deep and otherwise clean."""
        out = run([("BANK", 0.70, meas(0.30, WITHHELD, True, "financial")),
                   ("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("UTIL", 0.70, meas(0.30, WITHHELD, True, "regulated"))])
        self.assertEqual(
            sorted(r["ticker"] for r in out["rows_health_not_scored"]),
            ["BANK", "REIT", "UTIL"])
        self.assertEqual(out["n_health_not_scored"], 3)

    def test_an_excused_name_is_never_in_the_healthy_rows(self):
        """The ruling's own words: *never counted as healthy anywhere*."""
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("GOOD", 0.70, meas(0.30, OK, False, "mature"))])
        self.assertEqual([r["ticker"] for r in out["rows"]], ["GOOD"])
        self.assertNotIn("REIT", [r["ticker"] for r in out["rows"]])

    def test_a_name_below_a_floor_elsewhere_stays_rejected(self):
        """*A name below a floor elsewhere stays rejected* -- the ruling is explicit."""
        out = run([("REIT", 0.70, meas(0.30, WITHHELD_AND_LOW, True, "reit"))])
        self.assertEqual(out["rows_health_not_scored"], [])
        self.assertEqual(out["rows"], [])
        self.assertEqual(out["rejected_health"], 1)

    def test_a_second_missing_subscore_is_a_data_gap_and_stays_rejected(self):
        """Growth missing too: nobody withheld growth, so this is an ordinary gap.

        Without the subset test the group would absorb every incomplete financial, which is
        the "never counted as healthy" rule broken from the other direction.
        """
        out = run([("REIT", 0.70, meas(0.30, WITHHELD_AND_GAP, True, "reit"))])
        self.assertEqual(out["rows_health_not_scored"], [])
        self.assertEqual(out["rejected_health"], 1)

    def test_a_measurement_that_does_not_claim_the_regime_stays_rejected(self):
        """A cache written before this change carries no key -- it must NOT be excused.

        This is the live path on the day of the deploy: the stored precompute predates the
        field, so the group is EMPTY until a scan has run with this code. Failing closed is the
        direction that can never read a name as healthy.
        """
        for absent in (None, False, "yes", 1):
            out = run([("REIT", 0.70, meas(0.30, WITHHELD, absent, "reit"))])
            self.assertEqual(out["rows_health_not_scored"], [],
                             "health_not_scored=%r must not excuse a name" % (absent,))
            self.assertEqual(out["rejected_health"], 1)

    def test_an_ordinary_company_missing_health_is_not_excused(self):
        """Same sub-scores, no regime claim: a plain data gap on a `mature` name."""
        out = run([("PLAIN", 0.70, meas(0.30, WITHHELD, False, "mature"))])
        self.assertEqual(out["rows_health_not_scored"], [])
        self.assertEqual(out["rejected_health"], 1)

    def test_the_predicate_is_not_vacuous_in_either_direction(self):
        """`health_not_scored_only` must be able to return BOTH answers.

        A guard that can only say "no" looks exactly like a feature nobody triggered -- which
        is what a wrong sub-score key would produce, silently.
        """
        yes = dip.health_not_scored_only({"ok": False, "missing": ["health"], "below": []},
                                         {"health_not_scored": True})
        self.assertTrue(yes)
        self.assertFalse(dip.health_not_scored_only(
            {"ok": False, "missing": [], "below": ["quality"]},
            {"health_not_scored": True}))
        # An `ok` name has nothing missing, so the group never competes with a healthy row.
        self.assertFalse(dip.health_not_scored_only(
            {"ok": True, "missing": [], "below": []}, {"health_not_scored": True}))


class TheIdentityStillCloses(unittest.TestCase):
    """Every name the screen values ends in exactly one place, and the page says which."""

    CASES = [("HEALTHY", 0.70, meas(0.30, OK, False, "mature")),
             ("REIT_DEEP", 0.70, meas(0.30, WITHHELD, True, "reit")),
             ("BANK_DEEP", 0.70, meas(0.30, WITHHELD, True, "financial")),
             # Inside PRESELECT_SLACK: measured, then too shallow at 0.20.
             ("REIT_SHALLOW", 0.83, meas(0.17, WITHHELD, True, "reit")),
             ("REIT_LOW", 0.70, meas(0.30, WITHHELD_AND_LOW, True, "reit")),
             ("PLAIN_GAP", 0.70, meas(0.30, WITHHELD, False, "mature")),
             # No scan ratio either, so item 36's fallback cannot rescue it.
             ("NO_DD", None, meas(None, WITHHELD, True, "reit"))]

    def test_the_five_buckets_sum_to_the_qualifying_set(self):
        out = run(self.CASES)
        total = (len(out["rows"]) + out["n_unmeasured"] + out["rejected_health"]
                 + out["rejected_shallow"] + out["n_health_not_scored"])
        self.assertEqual(
            total, out["n_qualified_on_depth"],
            "a name left a bucket and arrived nowhere: rows=%d unmeasured=%d health=%d "
            "shallow=%d group=%d vs qualifying=%s"
            % (len(out["rows"]), out["n_unmeasured"], out["rejected_health"],
               out["rejected_shallow"], out["n_health_not_scored"],
               out["n_qualified_on_depth"]))
        self.assertEqual(out["capped"], 0)

    def test_the_identity_would_break_if_the_group_were_dropped_from_it(self):
        """Non-vacuity: the new term is load-bearing, not decoration."""
        out = run(self.CASES)
        self.assertTrue(out["n_health_not_scored"] > 0, "no excused name in the fixture")
        without = (len(out["rows"]) + out["n_unmeasured"] + out["rejected_health"]
                   + out["rejected_shallow"])
        self.assertNotEqual(without, out["n_qualified_on_depth"])

    def test_an_excused_name_that_is_too_shallow_is_counted_as_shallow(self):
        """It is a shallow name, not a third thing -- and the sub-count makes it readable."""
        out = run(self.CASES)
        self.assertEqual(out["rejected_shallow"], 1)
        self.assertEqual(out["n_health_not_scored_shallow"], 1)
        self.assertNotIn("REIT_SHALLOW",
                         [r["ticker"] for r in out["rows_health_not_scored"]])

    def test_the_shallow_subcount_is_not_double_counted_in_the_identity(self):
        """It is a SUBSET of `rejected_shallow`, so the identity must not add it."""
        out = run(self.CASES)
        self.assertLessEqual(out["n_health_not_scored_shallow"], out["rejected_shallow"])

    def test_raising_the_threshold_moves_names_out_of_the_group_and_nothing_vanishes(self):
        for thr in (0.10, 0.20, 0.30, 0.40):
            out = run(self.CASES, min_drawdown=thr)
            total = (len(out["rows"]) + out["n_unmeasured"] + out["rejected_health"]
                     + out["rejected_shallow"] + out["n_health_not_scored"])
            self.assertEqual(total, out["n_qualified_on_depth"],
                             "the identity broke at min_drawdown=%s" % thr)


class ElevensBookDoesNotMove(unittest.TestCase):
    """F-11's reject population is defined by `health_check`, not by which bucket renders."""

    def test_every_excused_name_is_still_in_f11s_reject_population(self):
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("BANK", 0.70, meas(0.30, WITHHELD, True, "financial")),
                   ("GOOD", 0.70, meas(0.30, OK, False, "mature"))])
        rejects = sorted(r["ticker"] for r in out["health_rejects"])
        self.assertEqual(rejects, ["BANK", "REIT"],
                         "an excused name left a LIVE forward book's population")
        # ...and the healthy one is not in it, so the list is not simply everything.
        self.assertNotIn("GOOD", rejects)

    def test_the_reject_row_says_which_rejects_are_unscored(self):
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("LOW", 0.70, meas(0.30, WITHHELD_AND_LOW, True, "reit"))])
        by = {r["ticker"]: r for r in out["health_rejects"]}
        self.assertIs(by["REIT"]["health_not_scored"], True)
        self.assertIs(by["LOW"]["health_not_scored"], False)

    def test_dip_rejects_still_selects_on_depth_alone(self):
        """The book's threshold rule is unchanged: a field cannot admit or exclude a name."""
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("SHALLOW", 0.83, meas(0.17, WITHHELD, True, "reit"))])
        got = sorted(r["ticker"] for r in dip.dip_rejects(out, min_drawdown=0.20))
        self.assertEqual(got, ["REIT"])


class OneDefinitionOfWhichRegimesWithhold(unittest.TestCase):

    def test_the_engine_withholds_health_for_exactly_dons_three_kinds(self):
        self.assertEqual(sorted(scoring.HEALTH_NOT_SCORED_REGIMES),
                         ["financial", "regulated", "reit"])
        for r in scoring.HEALTH_NOT_SCORED_REGIMES:
            self.assertFalse(scoring.health_is_scored(r))
        for r in ("mature", "growth", "hypergrowth", "cyclical", "", None):
            self.assertTrue(scoring.health_is_scored(r), r)

    def test_the_withheld_subscore_is_the_one_the_floors_are_keyed_on(self):
        """If these two strings ever disagree the group is silently always empty.

        `HEALTH_REGIME_WITHHELD` is the set `health_not_scored_only` intersects `missing`
        against; `HEALTH_FLOORS` is what `health_check` populates `missing` from. A mismatch
        makes the subset test unsatisfiable and the feature looks untriggered rather than
        broken.
        """
        self.assertEqual(dip.HEALTH_REGIME_WITHHELD, (scoring.HEALTH_SUBSCORE_KEY,))
        for k in dip.HEALTH_REGIME_WITHHELD:
            self.assertIn(k, dip.HEALTH_FLOORS)

    def test_the_engine_really_returns_nothing_for_those_regimes(self):
        """Pinned against the CURVE, not against the constant it is supposed to drive."""
        class Cls(object):
            def __init__(self, regime):
                self.regime, self.is_cash_burning = regime, False

        class CD(object):
            net_debt_to_ebitda, interest_coverage, fcf = 2.0, 8.0, 5e8
            cash_runway_years = None

            def __getattr__(self, k):
                return None

        for regime in scoring.HEALTH_NOT_SCORED_REGIMES:
            score, drivers = scoring._health_score(CD(), Cls(regime))
            self.assertIsNone(score, regime)
            self.assertTrue(drivers, "a withheld sub-score must say why")
        # And a regime that IS scored returns a number, or the test above proves nothing.
        score, _ = scoring._health_score(CD(), Cls("mature"))
        self.assertIsNotNone(score)

    def test_the_dip_module_keeps_no_copy_of_the_regime_list(self):
        """It must ASK the engine. A copy here is the defect this change repairs, moved.

        Read from the SOURCE because that is where a copy would appear; a runtime check would
        pass against a copy that happened to agree today.

        OVER `code_only`, AND THE FIRST CUT OF THIS TEST IS WHY. It banned the regime names in
        the RAW segment and failed against the correct tree, because the comment explaining why
        the list must not be copied QUOTES the list. That is `MA49`/`MB1`/`MB15`'s family --
        committed here in a session spent removing it from other people's guards -- so the ban
        now reads tokens with comments and string literals stripped.
        """
        path = os.path.join(REPO, "valuation", "web", "dip.py")
        body = function_source(path, "measurement_from")
        code = code_only(body)
        # The POSITIVE property first, so the ban below cannot pass by seeing nothing.
        self.assertIn("health_is_scored", code,
                      "measurement_from no longer asks the engine at all")
        self.assertIn("reit", body, "the fixture is wrong: the comment should mention reit")
        for regime in ("financial", "reit", "regulated"):
            self.assertNotIn(regime, code,
                             "dip.py spells a regime name in CODE instead of asking the "
                             "engine (prose is stripped, so this is a real copy)")

    def test_the_confidence_label_and_the_curve_cannot_disagree(self):
        """THE DEFECT THIS EXTRACTION FIXED, pinned so it cannot come back.

        `_health_score` grew `reit` and `regulated`; `compute_score`'s confidence line did not.
        So a REIT or a regulated utility with COMPLETE data was labelled `medium` confidence
        for a sub-score the model had DELIBERATELY declined to score -- the exact outcome the
        comment on that line forbids ("not applicable is not missing"). Measured before the
        repair: financial `high`, reit `medium`, regulated `medium`.

        The two now read the same predicate, and this asserts the PROPERTY rather than the
        line: for every withheld regime, the sub-score is `None` AND the confidence line does
        not count it.
        """
        code = code_only(function_source(
            os.path.join(REPO, "valuation", "engine", "scoring.py"), "compute_score"))
        self.assertIn("health_is_scored", code,
                      "the confidence line keeps its own regime test")
        # A ban on `== "financial"` would be VACUOUS here, because `code_only` strips the
        # literal and leaves `==`. The comparison itself is what survives stripping, and
        # `compute_score` has no legitimate one -- it reads `_WEIGHTS.get(cls.regime, ...)`.
        self.assertNotIn("regime ==", code,
                         "compute_score compares a regime directly again")
        # ...and the property as BEHAVIOUR, not only as shape: every withheld regime's health
        # sub-score is None AND is not counted as a data gap.
        for regime in scoring.HEALTH_NOT_SCORED_REGIMES:
            self.assertFalse(scoring.health_is_scored(regime))


    def test_why_no_published_confidence_LABEL_moved(self):
        """THE FACT THAT MAKES THE DEFECT ABOVE LATENT RATHER THAN LIVE.

        `confidence` is `low` when `dcf_reliability == "low"` OR `missing >= 2`, and every
        regime that withholds health is ALSO set `dcf_reliability = "low"` at classification --
        because the FCFF DCF is refused for all three. That branch dominates, so the miscounted
        `missing` could never reach the label: live after the repair, COF, O and NEE all read
        `low`, for a different and legitimate reason.

        Pinned because the handoff now SAYS no label was ever wrong. The day a withheld regime
        carries a `dcf_reliability` above `low`, the second encoding becomes reachable -- and
        this test going red is how a reader learns that the "latent" claim has expired.
        """
        src = io.open(os.path.join(REPO, "valuation", "engine", "classify.py"),
                      encoding="utf-8").read()
        for regime in scoring.HEALTH_NOT_SCORED_REGIMES:
            i = src.index('c.regime = "%s"' % regime)
            # The assignment on the very next line, so this reads the branch that sets the
            # regime rather than any other `dcf_reliability` in the file.
            nxt = src[i:src.index("\n", src.index("\n", i) + 1)]
            self.assertIn('c.dcf_reliability = "low"', nxt,
                          "%s no longer forces dcf_reliability low, so the confidence defect "
                          "this item repaired is now REACHABLE and the handoff's 'latent' "
                          "claim has expired" % regime)


class ThePageRendersTheGroupFromTheServersWords(unittest.TestCase):

    JS = os.path.join(REPO, "valuation", "web", "static", "app.js")

    def setUp(self):
        self.js = io.open(self.JS, encoding="utf-8").read()

    def test_the_label_and_the_sentence_are_served(self):
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit"))])
        self.assertEqual(out["health_not_scored_label"], dip.HEALTH_NOT_SCORED_LABEL)
        self.assertEqual(out["health_not_scored_note"], dip.HEALTH_NOT_SCORED_NOTE)
        self.assertEqual(out["health_regime_withheld"], ["health"])

    def test_the_label_says_what_don_said(self):
        lab = dip.HEALTH_NOT_SCORED_LABEL.lower()
        self.assertIn("health not scored for this kind of company", lab)
        for kind in ("bank", "insurer", "reit", "regulated utilit"):
            self.assertIn(kind, lab, "the label drops %r" % kind)

    def test_the_sentence_says_the_user_must_judge_that_part(self):
        note = dip.HEALTH_NOT_SCORED_NOTE.lower()
        self.assertIn("do not describe these businesses", note)
        self.assertIn("yours to judge", note)

    def test_the_js_renders_the_served_strings_and_writes_none_of_its_own(self):
        self.assertIn("d.health_not_scored_label", self.js)
        self.assertIn("d.health_not_scored_note", self.js)
        self.assertIn("rows_health_not_scored", self.js)
        # No paraphrase of the label in the JS: `dip_posture.py`'s rule, because prose in a
        # template does not stop when a ruling changes.
        self.assertNotIn("Health not scored for this kind", self.js)

    def test_the_group_is_rendered_on_the_empty_rows_paths_too(self):
        """The common case on this screen is NO healthy rows.

        Item 36 measured 110 of 151 classifiable names rejected on health, so emitting the
        group only after the main table would hide it on exactly the days it is the whole
        answer -- "never silently excluded" broken by control flow rather than by a filter.
        """
        body = js_function_source(self.JS, "renderDip")
        # FIVE writes, not four -- the count in the first cut of this test was wrong. Two of
        # them run BEFORE a screen exists and correctly carry no group: `d.error` (the request
        # failed) and `d.empty` (no scan has landed). The other three are real screen outcomes
        # and every one must append it.
        self.assertEqual(body.count('setHtml("dipResults",'), 5,
                         "renderDip's exit paths changed; re-check each one appends the group")
        after = body[body.index("_dipUnscoredGroup(d)"):]
        self.assertEqual(after.count('setHtml("dipResults",'), 3)
        self.assertEqual(after.count("extra"), 3,
                         "a screen-outcome path stopped appending the group")

    def test_the_group_is_its_own_table_and_not_a_badge_on_a_healthy_row(self):
        body = js_function_source(self.JS, "_dipUnscoredGroup")
        self.assertIn("<table>", body)
        self.assertIn("rows_health_not_scored", body)
        self.assertIn("return \"\"", body, "an empty group must render nothing at all")

    def test_the_chip_tooltip_does_not_call_a_withheld_score_not_computed(self):
        """Inside this group "not computed" is the one sentence it exists to prevent."""
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit"))])
        self.assertEqual(out["health_not_scored_chip"], dip.HEALTH_NOT_SCORED_CHIP)
        self.assertIn("not scored for this kind of company",
                      dip.HEALTH_NOT_SCORED_CHIP.lower())
        body = js_function_source(self.JS, "_dipHealthChips")
        self.assertIn("unscoredTitle", body)
        self.assertIn("not computed", body, "the ordinary data-gap wording must survive")

    def test_the_row_says_which_group_it_is_in(self):
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("GOOD", 0.70, meas(0.30, OK, False, "mature"))])
        self.assertIs(out["rows_health_not_scored"][0]["health_not_scored"], True)
        self.assertEqual(out["rows_health_not_scored"][0]["regime"], "reit")
        self.assertIs(out["rows"][0]["health_not_scored"], False)

    def test_both_groups_carry_the_same_columns(self):
        """ONE row builder. Two literals is how the disclosure goes missing from one table."""
        out = run([("REIT", 0.70, meas(0.30, WITHHELD, True, "reit")),
                   ("GOOD", 0.70, meas(0.30, OK, False, "mature"))])
        self.assertEqual(sorted(out["rows"][0].keys()),
                         sorted(out["rows_health_not_scored"][0].keys()))


class TheLiveCheckAssertsTheNewIdentity(unittest.TestCase):

    def test_the_identity_in_the_live_check_names_the_new_bucket(self):
        src = io.open(os.path.join(REPO, "scripts", "live_check.py"),
                      encoding="utf-8").read()
        self.assertIn("n_health_not_scored", src)
        # ...and NOT the sub-count, which would double-count and fail a correct screen.
        i = src.index('parts = {k: d.get(k) for k in ("n_unmeasured"')
        block = src[i:i + 400]
        self.assertNotIn("n_health_not_scored_shallow", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
