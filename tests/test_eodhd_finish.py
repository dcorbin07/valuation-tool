# -*- coding: utf-8 -*-
"""Tests for the finish-out: replication feasibility, and `tracelead`'s `K1` settle.

**WHAT THESE PIN.**

1. **THE FEASIBILITY BARS ARE THE PRE-COMMITTED ONES.** They were committed ALONE and BEFORE the
   measurement; `W-28`'s rule is that a bar watched to fail may not then be relaxed, and a test is
   the only thing that makes that durable once the reading is known.
2. **BOTH COVERAGE RULES ARE STRICTLY POINT-IN-TIME.** A window that includes `t` itself, or a
   filing dated `t` counting as known at `t`, is look-ahead on the exact signal under test.
3. **THE ISSUER SET IS VALIDATED BEFORE ANYTHING IS PULLED.** A rebuild that silently produced a
   different set would make `K1` a measurement of a different population -- `O-1`'s family.
4. **TWO DEFECTS I ACTUALLY HIT**, pinned behaviourally rather than by substring: a calendar read
   with no header admitted the literal string "date" and sorted it LAST, which would have shifted
   every window; and an error capture kept the HEAD of an exception that embeds the whole query, so
   the database's message -- the only diagnostic part -- was truncated away.
"""
import ast
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEAS = os.path.join(ROOT, "scripts", "eodhd_replication_feasibility.py")
K1 = os.path.join(ROOT, "scripts", "tracelead_k1_settle.py")


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


class TheFeasibilityBarsArePreCommitted(unittest.TestCase):
    def test_the_three_bars_hold_their_committed_values(self):
        from scripts import eodhd_replication_feasibility as F
        self.assertEqual(F.R1_CELL_COVERAGE, 0.85)
        self.assertEqual(F.R2_PER_DATE_FLOOR, 0.70)
        self.assertEqual(F.R3_MAX_SURVIVORSHIP_SPLIT, 0.15)

    def test_all_three_are_required_so_one_pass_cannot_carry_it(self):
        src = _src(FEAS)
        self.assertIn('rep["R1_pass"] and rep["R2_pass"] and rep["R3_pass"]', src)

    def test_the_per_date_bar_is_every_date_and_not_a_mean(self):
        """A mean can hide an era hole entirely, which is the failure this bar exists to catch."""
        src = _src(FEAS)
        self.assertIn("(per_date >= R2_PER_DATE_FLOOR).all()", src)

    def test_the_survivorship_split_is_measured_not_merely_cautioned(self):
        src = _src(FEAS)
        for key in ("coverage_alive_at_end", "coverage_left_before_end",
                    "R3_survivorship_split", "rows_left_before_end"):
            self.assertIn(key, src)

    def test_an_absent_name_counts_as_uncovered_rather_than_being_dropped(self):
        """Excluding absent names would measure coverage on the names that have coverage."""
        from scripts import eodhd_replication_feasibility as F
        tree = ast.parse(_src(FEAS))
        fn = [n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "datekeys_by_ticker"][0]
        body = ast.unparse(fn)
        self.assertIn("out[t] = []", body)
        self.assertIs(F.R1_CELL_COVERAGE > 0, True)


class TheCoverageRulesArePointInTime(unittest.TestCase):
    def test_feasibility_counts_a_period_filed_on_or_before_the_rebalance_date(self):
        src = _src(FEAS)
        self.assertIn("bisect.bisect_right(dk[t], d)", src)

    def test_the_k1_window_excludes_the_rebalance_date_itself(self):
        """`[t-63, t)` -- a trade ON t must never count, or the kill reads the future."""
        from scripts import tracelead_k1_settle as K
        cal = ["2026-01-%02d" % d for d in range(1, 29)]
        cells = _frame([("2026-01-20", "AAA", "111111")])
        # a trade ON the rebalance date only
        pairs = _pairs([("111111", "2026-01-20")])
        got = K.score(pairs, cells, cal)
        self.assertEqual(got["2026-01-20"]["covered"], 0,
                         "a trade on t itself must not count as in-window")
        # a trade the session BEFORE must count -- positive control, so the rule is not "never"
        pairs2 = _pairs([("111111", "2026-01-19")])
        got2 = K.score(pairs2, cells, cal)
        self.assertEqual(got2["2026-01-20"]["covered"], 1)

    def test_a_trade_older_than_the_window_does_not_count(self):
        from scripts import tracelead_k1_settle as K
        cal = ["2026-%02d-%02d" % (m, d) for m in (1, 2, 3, 4) for d in range(1, 29)]
        cells = _frame([("2026-04-20", "AAA", "111111")])
        self.assertEqual(
            K.score(_pairs([("111111", "2026-01-02")]), cells, cal)["2026-04-20"]["covered"], 0)


class TheK1InstrumentIsValidatedBeforeItIsBelieved(unittest.TestCase):
    def test_the_bar_is_the_drafts_own(self):
        from scripts import tracelead_k1_settle as K
        self.assertEqual(K.K1_BAR, 0.70)
        self.assertEqual(K.WINDOW_SESSIONS, 63)

    def test_a_mismatched_issuer_set_refuses_rather_than_proceeding(self):
        from scripts import tracelead_k1_settle as K
        self.assertEqual(K.EXPECTED_TIER_CUSIP6, 428)
        src = _src(K1)
        self.assertIn("if len(c6) != EXPECTED_TIER_CUSIP6:", src)
        self.assertIn("a different population", src)

    def test_a_partial_era_refuses_rather_than_scoring(self):
        """A missing year would understate coverage and could fire the kill for the wrong reason."""
        src = _src(K1)
        self.assertIn("if errs:", src)
        self.assertIn("about the PULL rather than the data", src)

    def test_the_verdict_vocabulary_is_closed(self):
        src = _src(K1)
        self.assertIn('"K1 FIRES"', src)
        self.assertIn('"K1 DOES NOT FIRE"', src)


class TheTwoDefectsIActuallyHit(unittest.TestCase):
    def test_the_session_calendar_rejects_a_header_row(self):
        """BEHAVIOURAL. Read with no header, the literal string "date" entered the calendar and
        sorted LAST, which would have shifted every window boundary by one and produced a
        plausible coverage figure from a corrupted calendar."""
        from scripts import tracelead_k1_settle as K
        try:
            cal = K.sessions()
        except (FileNotFoundError, OSError) as exc:
            self.skipTest("SKIPPED LOUDLY: price store absent (%s)" % exc)
        self.assertTrue(cal, "the calendar must not be empty")
        self.assertNotIn("date", cal)
        for c in (cal[0], cal[-1]):
            self.assertEqual(len(c), 10)
            self.assertTrue(c[:4].isdigit())
            self.assertEqual(c[4], "-")
        self.assertEqual(cal, sorted(cal))

    def test_an_empty_calendar_raises_rather_than_scoring_nothing(self):
        src = _src(K1)
        self.assertIn("no trading sessions parsed", src)

    def test_the_query_error_capture_keeps_the_tail_of_the_exception(self):
        """The QUERY exception embeds the whole SQL, so keeping its HEAD keeps my own IN-list and
        discards the database's message -- the only part that diagnoses anything.

        **AND THE BAN IS NARROW ON PURPOSE.** A first version of this test forbade `str(exc)[:300]`
        anywhere in the file and FAILED AGAINST THE CORRECT SOURCE, because the **connect**
        handler legitimately keeps the head: a connection error does not embed a query, so its
        first characters are the message. The substring-ban family, which this record names
        repeatedly -- so the assertion is scoped to the per-year query handler.
        """
        # **READ THE SYNTAX TREE, NOT THE TEXT -- after three wrong attempts at this one guard.**
        # A plain ban fired on the connect handler (which legitimately keeps the head); scoping it
        # to the loop fired on the COMMENT documenting the repair; and `tokenize` spaces slice
        # tokens apart, so the needle stopped matching. The AST sees the slice itself.
        tree = ast.parse(_src(K1))
        found = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], ast.Subscript)
                    and isinstance(node.targets[0].value, ast.Name)
                    and node.targets[0].value.id == "errs"):
                found.append(ast.unparse(node.value))
        self.assertEqual(len(found), 1, "expected exactly one errs[...] assignment")
        self.assertIn("-400", found[0],
                      "the per-year query handler must keep the TAIL of the exception")
        # positive control: the connect handler legitimately keeps the head, and still does
        self.assertIn("REFUSED on the single attempt", _src(K1))


class NothingIsAdoptedAndNoRegisterIsCommitted(unittest.TestCase):
    def test_both_scripts_declare_zero_trials(self):
        for p in (FEAS, K1):
            src = _src(p)
            self.assertIn('"trials": 0', src)
            self.assertIn("FIXED", src)

    def test_neither_script_writes_a_register_file(self):
        """BEHAVIOURAL, not a substring ban.

        A first version forbade the string `PREREG_` in the body and FAILED AGAINST THE CORRECT
        SOURCE, because `tracelead_k1_settle.py` legitimately CITES `PREREG_DRAFT_tracelead.md` as
        the provenance of its 0.70 bar -- exactly the prose-documenting-the-rule case the
        substring-ban family keeps producing. What matters is that neither script WRITES one, so
        the output paths are checked instead.
        """
        import ast as _ast
        for p in (FEAS, K1):
            tree = _ast.parse(_src(p))
            for node in _ast.walk(tree):
                if isinstance(node, _ast.Constant) and isinstance(node.value, str):
                    if node.value.endswith(".md"):
                        self.fail("%s names a markdown output %r" % (p, node.value))
            # and the only writes are json/pickle artifacts
            self.assertNotIn('open(PREREG', _src(p))

    def test_both_run_standalone(self):
        for p in (FEAS, K1, __file__):
            self.assertIn('if __name__ == "__main__":', _src(p))


def _frame(rows):
    import pandas as pd
    return pd.DataFrame(rows, columns=["date", "ticker", "cusip6"])


def _pairs(rows):
    import pandas as pd
    return pd.DataFrame(rows, columns=["cusip6", "d"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
