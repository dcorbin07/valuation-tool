# -*- coding: utf-8 -*-
"""PKG-MB20 — routine vs opportunistic insider trades.

TRIPWIRES on the properties that decided the item, plus a real unit test of the classifier. Each
pins a defect this register hit or a rule it would otherwise break silently:

* the classifier is POINT-IN-TIME BY CONSTRUCTION — it may look only at years strictly before the
  trade's own, and `K5` reads zero because of that, not because of a filter;
* `UNCLASSIFIABLE` is a NAMED state and is KEPT, never folded into `OPPORTUNISTIC` — folding it
  would turn a behavioural screen into a data-availability screen (`S10`'s failure mode);
* the `insider_filter` hook is a PRODUCTION change, so its default must be provably inert and the
  panel must not acquire a dependency on `valuation/studies/` (`MA23`'s one-way boundary);
* `MB16`: ONE log row, verdict edited in place. `M1-PARSE`: no raw pipe in the prose.
"""
from __future__ import annotations

import ast
import io
import os
import unittest

import pandas as pd

import state_isolation  # noqa: F401  (must precede any `valuation` import)

from valuation.studies import insider_routine as IR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with io.open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


def _tree(*parts):
    return ast.parse(_read(*parts))


def _rows(spec):
    """spec: list of (ticker, owner, 'YYYY-MM-DD')."""
    return pd.DataFrame([{"ticker": t, "ownername": o, "transactiondate": d}
                         for t, o, d in spec])


class TestTheRuleIsCohenMalloyPomorskis(unittest.TestCase):

    def test_three_consecutive_years_same_month_is_routine(self):
        d = _rows([("AAA", "SMITH", "2015-03-04"),
                   ("AAA", "SMITH", "2016-03-09"),
                   ("AAA", "SMITH", "2017-03-02")])
        lab = list(IR.classify(d))
        # Only the THIRD trade can be routine: it is the first with two prior same-month years.
        self.assertEqual(lab, [IR.OPPORTUNISTIC, IR.OPPORTUNISTIC, IR.ROUTINE])

    def test_two_consecutive_years_is_not_enough(self):
        d = _rows([("AAA", "SMITH", "2016-03-09"), ("AAA", "SMITH", "2017-03-02")])
        self.assertNotIn(IR.ROUTINE, list(IR.classify(d)))

    def test_a_gap_year_breaks_the_run(self):
        d = _rows([("AAA", "SMITH", "2015-03-04"),
                   ("AAA", "SMITH", "2017-03-02"),
                   ("AAA", "SMITH", "2018-03-05")])
        self.assertNotIn(IR.ROUTINE, list(IR.classify(d)))

    def test_a_different_month_is_a_different_pattern(self):
        d = _rows([("AAA", "SMITH", "2015-03-04"),
                   ("AAA", "SMITH", "2016-04-09"),
                   ("AAA", "SMITH", "2017-03-02")])
        self.assertNotIn(IR.ROUTINE, list(IR.classify(d)))

    def test_the_pair_is_ticker_AND_owner(self):
        """Two people trading the same month for years are not one routine trader, and one
        person trading two tickers does not pool them."""
        d = _rows([("AAA", "SMITH", "2015-03-04"),
                   ("AAA", "JONES", "2016-03-09"),
                   ("AAA", "SMITH", "2017-03-02")])
        self.assertNotIn(IR.ROUTINE, list(IR.classify(d)))
        d2 = _rows([("AAA", "SMITH", "2015-03-04"),
                    ("BBB", "SMITH", "2016-03-09"),
                    ("AAA", "SMITH", "2017-03-02")])
        self.assertNotIn(IR.ROUTINE, list(IR.classify(d2)))


class TestItIsPointInTimeByConstruction(unittest.TestCase):

    def test_a_later_repeat_cannot_relabel_an_earlier_trade(self):
        """THE LOAD-BEARING PROPERTY. Adding trades in 2018 and 2019 must not change how the
        2017 trade was labelled — otherwise the label leaks the future into the panel."""
        early = _rows([("AAA", "SMITH", "2015-03-04"),
                       ("AAA", "SMITH", "2016-03-09"),
                       ("AAA", "SMITH", "2017-03-02")])
        lab_early = list(IR.classify(early))
        late = _rows(list(map(tuple, early.values)) +
                     [("AAA", "SMITH", "2018-03-05"), ("AAA", "SMITH", "2019-03-06")])
        lab_late = list(IR.classify(late))
        self.assertEqual(lab_early, lab_late[:len(lab_early)],
                         "a future trade changed a past label — that is look-ahead")

    def test_the_first_two_of_a_long_routine_run_are_opportunistic(self):
        """The positive control for the test above: if everything were labelled ROUTINE the
        invariance check would pass vacuously."""
        d = _rows([("AAA", "SMITH", "%d-03-04" % y) for y in range(2010, 2020)])
        lab = list(IR.classify(d))
        self.assertEqual(lab[:2], [IR.OPPORTUNISTIC, IR.OPPORTUNISTIC])
        self.assertEqual(lab[2], IR.ROUTINE)
        self.assertIn(IR.ROUTINE, lab)


class TestUnclassifiableIsNamedAndKept(unittest.TestCase):

    def test_a_missing_owner_or_date_is_unclassifiable_not_opportunistic(self):
        d = _rows([("AAA", None, "2015-03-04"), ("AAA", "SMITH", None)])
        self.assertEqual(list(IR.classify(d)), [IR.UNCLASSIFIABLE, IR.UNCLASSIFIABLE])

    def test_the_mask_KEEPS_unclassifiable_rows(self):
        """Dropping them would make the variant differ wherever the DATA is missing as well as
        wherever the BEHAVIOUR differs, so a verdict could not be attributed to the hypothesis."""
        d = _rows([("AAA", None, "2015-03-04")])
        self.assertTrue(bool(IR.opportunistic_mask(IR.classify(d))[0]))

    def test_coverage_quotes_the_routine_share_over_CLASSIFIABLE_rows(self):
        """A share over all rows silently mixes 'not routine' with 'cannot tell'."""
        d = _rows([("AAA", "SMITH", "%d-03-04" % y) for y in (2015, 2016, 2017)] +
                  [("AAA", None, "2015-03-04")])
        c = IR.coverage(IR.classify(d))
        self.assertEqual(c["counts"][IR.UNCLASSIFIABLE], 1)
        self.assertAlmostEqual(c["frac_classifiable"], 0.75, places=12)
        self.assertAlmostEqual(c["routine_share_of_classifiable"], 1.0 / 3.0, places=12)


class TestTheHookIsInertByDefault(unittest.TestCase):

    def test_insider_filter_exists_and_defaults_to_none(self):
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        fn = next(n for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and n.name == "build_fundamental_panel")
        args = [a.arg for a in fn.args.args]
        self.assertIn("insider_filter", args)
        i = args.index("insider_filter")
        j = i - (len(fn.args.args) - len(fn.args.defaults))
        self.assertGreaterEqual(j, 0, "insider_filter has no default")
        default = fn.args.defaults[j]
        self.assertIsInstance(default, ast.Constant)
        self.assertIsNone(default.value, "insider_filter must default to None")

    def test_EVERY_use_is_guarded_on_exactly_is_not_none(self):
        """The node SHAPE, and EVERY site, not merely one.

        TWO EARLIER FORMS OF THIS TEST WERE TOO WEAK AND MUTATION FOUND BOTH. `W-1`'s asked only
        that the name and `is not None` both appeared in the unparsed test, so widening a guard
        to `... or True` walked straight through. This one's first cut then asked for AT LEAST
        ONE correctly-shaped guard -- and the hook has TWO sites, so mutating either left the
        other to satisfy it. The property that actually protects the default is that NO guard
        mentioning `insider_filter` may be anything but the exact comparison.
        """
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        mentions = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            if "insider_filter" not in ast.unparse(node.test):
                continue
            mentions += 1
            t = node.test

            def _is_the_comparison(x):
                return (isinstance(x, ast.Compare)
                        and isinstance(x.left, ast.Name) and x.left.id == "insider_filter"
                        and len(x.ops) == 1 and isinstance(x.ops[0], ast.IsNot)
                        and isinstance(x.comparators[0], ast.Constant)
                        and x.comparators[0].value is None)

            # THE PROPERTY IS THAT THE COMPARISON IS A REQUIRED CONJUNCT, not that it stands
            # alone. `insider_filter is not None AND isc is not None` is legitimate -- the emit
            # site needs the incumbent score to exist before it can fall back to it. An `Or`
            # is NOT: `... or True` makes the override reachable with the default in place,
            # which is the exact mutation that walked through the earlier form of this test.
            if _is_the_comparison(t):
                ok = True
            elif isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And):
                ok = any(_is_the_comparison(v) for v in t.values)
            else:
                ok = False
            if not ok:
                self.fail("an `insider_filter` guard does not REQUIRE "
                          "`insider_filter is not None`: %s" % ast.unparse(t))
        self.assertGreaterEqual(mentions, 2,
                                "expected both hook sites to guard on insider_filter; found "
                                "%d -- fewer means a use has become unguarded or vanished"
                                % mentions)

    def test_the_panel_does_not_import_the_classifier(self):
        """`MA23`'s one-way boundary. The filter is DUCK-TYPED in; the panel must learn nothing
        about how a trade is classified."""
        tree = _tree("valuation", "edge", "fundamental_panel.py")
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotIn("studies", node.module,
                                 "the panel imported a study — MA23's boundary")
            elif isinstance(node, ast.Import):
                for a in node.names:
                    self.assertNotIn("valuation.studies", a.name)


class TestTheResearchLogRow(unittest.TestCase):

    def _row(self):
        rows = [l for l in _read("RESEARCH_LOG.md").split("\n")
                if l.startswith("| PKG-MB20 |")]
        self.assertEqual(len(rows), 1,
                         "a second row double-charges the trial (MB16 — no dedup by id)")
        return rows[0]

    def test_the_row_has_the_nine_cells_the_parser_expects(self):
        self.assertEqual(self._row().count("|") - 1, 9,
                         "a raw pipe in the prose shifts every column after it (M1-PARSE)")

    def test_the_verdict_replaced_the_placeholder_and_charges_one_equity_trial(self):
        c = self._row().split("|")
        self.assertFalse(c[7].strip().startswith("PRE-REGISTERED"))
        self.assertIn("REJECT", c[7].upper())
        self.assertEqual(c[3].strip(), "equity")
        self.assertEqual(c[8].strip(), "n=1")


class TestTheRegisterIsOnDisk(unittest.TestCase):

    def test_it_names_the_three_year_rule_and_the_MA57_correction(self):
        t = _read("PREREG_mb20_insider_routine.md")
        self.assertIn("48.72", t, "MA57's four-year figure, the premise being corrected")
        self.assertIn("60.47", t, "the three-year figure on the identical population")
        self.assertIn("42,537", t, "the reproduction that makes it the same object")

    def test_the_rule_constant_matches_the_register(self):
        self.assertEqual(IR.CONSECUTIVE_YEARS, 3,
                         "the register commits to THREE consecutive years; a sweep is a void "
                         "condition")


if __name__ == "__main__":
    unittest.main(verbosity=2)
