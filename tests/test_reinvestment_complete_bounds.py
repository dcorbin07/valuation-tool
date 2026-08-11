"""
Tests for Item C — reinvestment Arm B against the COMPLETE bound set.

Registered in `PREREG_C_reinvestment_complete_bounds.md`, committed alone at `abeb4f7`.

These pin the VERDICT MACHINERY, not the verdict: that a bound set with a registered threshold
cannot be quietly re-scored on different fields, that the pre-registered escape hatches (VOID,
C5-INDECISIVE) behave as written, and that a finding discovered mid-run cannot leak into the
scorecard. The measured numbers live in `HANDOFF_parked_positives.md` — the artifact itself is
under `data/`, which is never committed.

No network: every fixture is synthetic.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from scripts import reinvestment_complete_bounds as R   # noqa: E402


def _name(fv=100.0, dcf=100.0, ev=1000.0, tv=800.0, ri=50.0, nc=50.0,
          rev1=1000.0, revlast=1000.0, wacc=0.08, score=50.0, conf="medium"):
    return {"fair_value": fv, "dcf": dcf, "ev": ev, "tv": tv, "reinvest_y1": ri,
            "net_capex": nc, "rev1": rev1, "revlast": revlast, "wacc": wacc,
            "score": score, "published": fv is not None, "confidence": conf}


def _rows(n_clean=100, **treated):
    """A population that passes everything, plus whatever the caller perturbs."""
    rows = {}
    for i in range(n_clean):
        # untreated: net capex <= 0, so the gate is never entered
        rows[f"CLEAN{i}"] = {"control": _name(nc=-1.0), "treated": _name(nc=-1.0),
                             "financial": False}
    for t, (c, a) in treated.items():
        rows[t] = {"control": c, "treated": a, "financial": False}
    return rows


class TestTheVerdictIsMechanical(unittest.TestCase):
    def test_a_clean_population_ships(self):
        """The control: if nothing violates, the arm ships. A scorer that can only reject is
        not scoring anything."""
        treated = {}
        for i in range(90):
            # undercharged under control (nc 200 vs reinvest 10 on revenue 1000 = 19%),
            # fully charged under treatment, flat revenue, value falls, terminal falls
            c = _name(nc=200.0, ri=10.0, fv=100.0, tv=800.0, dcf=100.0)
            a = _name(nc=200.0, ri=200.0, fv=90.0, tv=700.0, dcf=90.0)
            treated[f"T{i}"] = (c, a)
        p = R.evaluate(_rows(**treated), 190)
        self.assertEqual(p["verdict"], "SHIPS", p["failed_bounds"])

    def test_one_violated_bound_rejects(self):
        treated = {}
        for i in range(90):
            c = _name(nc=200.0, ri=10.0, tv=800.0)
            a = _name(nc=200.0, ri=200.0, fv=90.0, tv=700.0, dcf=90.0)
            treated[f"T{i}"] = (c, a)
        # one name's terminal value goes non-positive -> C2
        treated["T0"] = (_name(nc=200.0, ri=10.0, tv=800.0),
                         _name(nc=200.0, ri=200.0, fv=90.0, tv=-5.0, dcf=90.0))
        p = R.evaluate(_rows(**treated), 190)
        self.assertEqual(p["verdict"], "REJECTED-COMPLETE")
        self.assertIn("C2", p["failed_bounds"])

    def test_an_empty_treated_population_is_VOID_not_a_pass(self):
        """The hazard the VOID preconditions exist for: every output-validity bound passes
        trivially on an empty population, so a throttled fetch would otherwise SHIP the arm."""
        p = R.evaluate(_rows(n_clean=100), 130)
        self.assertEqual(p["verdict"], "VOID")
        self.assertIn("V2_treated", p["void_failures"])
        self.assertIn("V3_decisive", p["void_failures"])

    def test_a_thin_fetch_is_VOID(self):
        treated = {f"T{i}": (_name(nc=200.0, ri=10.0), _name(nc=200.0, ri=200.0, fv=90.0))
                   for i in range(90)}
        p = R.evaluate(_rows(**treated), 600)      # scored 190 of a 600-name universe
        self.assertEqual(p["verdict"], "VOID")
        self.assertIn("V1_fetch_rate", p["void_failures"])


class TestH1IsScoredOnTheRegisteredFieldsOnly(unittest.TestCase):
    """THE CORRECTION. The first cut of the scorer also compared ev/tv/dcf, which made H1 read
    VIOLATED on one control name. That is STRICTER than the registered bound, and re-scoring a
    bound on fields the register does not name — after seeing the result — is the exact error
    this task exists to correct."""

    FIELDS = ("fair_value", "wacc", "score", "confidence", "published")

    def test_the_field_list_is_exactly_what_the_register_names(self):
        p = R.evaluate(_rows(n_clean=100), 100)
        self.assertEqual(tuple(p["bounds"]["H1"]["fields"]), self.FIELDS)

    def test_an_untreated_name_whose_EV_moves_does_not_break_H1(self):
        rows = _rows(n_clean=100)
        rows["CLEAN0"]["treated"] = _name(nc=-1.0, ev=999.0)     # EV moved, nothing else
        p = R.evaluate(rows, 100)
        self.assertTrue(p["bounds"]["H1"]["held"])

    def test_an_untreated_name_whose_FAIR_VALUE_moves_DOES_break_H1(self):
        """The bound still has teeth on the fields it names."""
        rows = _rows(n_clean=100)
        rows["CLEAN0"]["treated"] = _name(nc=-1.0, fv=101.0)
        p = R.evaluate(rows, 100)
        self.assertFalse(p["bounds"]["H1"]["held"])
        self.assertIn("CLEAN0", p["bounds"]["H1"]["names"])

    def test_confidence_is_one_of_them(self):
        rows = _rows(n_clean=100)
        rows["CLEAN0"]["treated"] = _name(nc=-1.0, conf="low")
        p = R.evaluate(rows, 100)
        self.assertFalse(p["bounds"]["H1"]["held"])


class TestTheFindingCannotLeakIntoTheVerdict(unittest.TestCase):
    """PREREG §5: a thirteenth thing worth bounding is recorded for whoever re-opens it, NOT
    folded into this verdict. Adding a bound after seeing the run is the original sin."""

    def _rows_with_touched_financial(self):
        treated = {f"T{i}": (_name(nc=200.0, ri=10.0, tv=800.0),
                             _name(nc=200.0, ri=200.0, fv=90.0, tv=700.0, dcf=90.0))
                   for i in range(90)}
        rows = _rows(**treated)
        rows["FIN"] = {"control": _name(nc=100.0, ev=1000.0, ri=50.0),
                       "treated": _name(nc=100.0, ev=900.0, ri=120.0),
                       "financial": True}
        return rows

    def test_the_finding_is_reported(self):
        p = R.evaluate(self._rows_with_touched_financial(), 192)
        f = p["finding_not_a_bound"]
        self.assertEqual(f["n_touched"], 1)
        self.assertFalse(f["any_fair_value_moved"])

    def test_it_carries_no_verdict_weight(self):
        p = R.evaluate(self._rows_with_touched_financial(), 192)
        self.assertFalse(p["finding_not_a_bound"]["carries_verdict_weight"])
        self.assertEqual(p["verdict"], "SHIPS",
                         "a finding must not reject an arm that cleared every bound")

    def test_a_touched_financial_is_not_counted_as_treated(self):
        """Financials are out of the treated population by the register's own census, which is
        why the gate reaching them is a finding rather than a bound violation."""
        p = R.evaluate(self._rows_with_touched_financial(), 192)
        self.assertNotIn("FIN", p["populations"]["decisive_names"])


class TestC5IndecisiveClause(unittest.TestCase):
    """PREREG §4: if the multiplier decides the answer, C5 is INDECISIVE and carries no weight.
    A bound whose verdict rests on a number I chose is not a bound."""

    def _rows_at_ratio(self, changed_extra):
        treated = {}
        for i in range(90):
            treated[f"T{i}"] = (_name(nc=200.0, ri=10.0, tv=800.0),
                                _name(nc=200.0, ri=200.0, fv=90.0, tv=700.0, dcf=90.0))
        rows = _rows(**treated)
        # untreated names whose fair value nonetheless differs, inflating the blast radius
        for i in range(changed_extra):
            rows[f"CLEAN{i}"]["treated"] = _name(nc=-1.0, fv=99.0)
        return rows

    def test_a_ratio_inside_the_stated_band_is_indecisive_and_excluded(self):
        p = R.evaluate(self._rows_at_ratio(100), 190)   # 90 + 100 = 190 changed vs 90 decisive
        c5 = p["bounds"]["C5"]
        self.assertFalse(c5["held"])
        self.assertTrue(c5["indecisive"])
        self.assertNotIn("C5", p["failed_bounds"])

    def test_a_blast_radius_inside_the_ceiling_simply_holds(self):
        p = R.evaluate(self._rows_at_ratio(0), 190)
        self.assertTrue(p["bounds"]["C5"]["held"])
        self.assertFalse(p["bounds"]["C5"]["indecisive"])


class TestTheThresholdsAreTheRegisteredOnes(unittest.TestCase):
    """A register is only binding if the code uses its numbers. Each is a literal here, so a
    silent edit fails a test rather than moving a verdict."""

    def test_every_threshold_matches_the_register(self):
        self.assertEqual(R.V1_FETCH_RATE, 0.95)
        self.assertEqual(R.V2_MIN_TREATED, 80)
        self.assertEqual(R.V3_MIN_DECISIVE, 20)
        self.assertEqual(R.F1_TOL, 0.25)
        self.assertEqual(R.F2_MAX_UNDERCHARGED, 5)
        self.assertEqual(R.F4_TERMINAL_DROP, -0.05)
        self.assertEqual(R.UNDERCHARGE_FRAC, 0.05)
        self.assertEqual(R.FLAT_REVENUE_TOL, 0.05)
        self.assertEqual(R.C1_EV_POSITIVE_RATE, 0.99)
        self.assertEqual(R.C4_RISE_TOL, 0.01)
        self.assertEqual(R.C5_BLAST_MULTIPLE, 1.5)
        self.assertEqual(R.P2_REINVEST_RISE, 0.10)

    def test_the_universe_rule_has_no_discretionary_names(self):
        """191 bundled + exactly the seven foreign filers the record names."""
        self.assertEqual(R.RECORD_FOREIGN, ["BHP", "E", "PBR", "TTE", "RIO", "NVO", "CNI"])
        u = R.universe()
        self.assertEqual(len(u), len(set(u)), "the universe must not contain duplicates")
        for t in R.RECORD_FOREIGN:
            self.assertIn(t, u)

    def test_the_shipped_default_is_still_off(self):
        """Nothing in this task may change what the product runs. Arm B was REJECTED."""
        from valuation.engine import dcf as D
        self.assertEqual(D.REINVESTMENT_FLOOR_MODE, "off")


class TestScoringDoesNotMutateTheSnapshot(unittest.TestCase):
    def test_value_deep_copies_so_the_two_arms_cannot_contaminate_each_other(self):
        """`value_from_company` appends to `cd.quality_notes`; valuing the same object twice
        would carry the control's notes into the treated arm."""
        import io
        src = io.open(R.__file__, encoding="utf-8").read()
        self.assertIn("copy.deepcopy(cd)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
