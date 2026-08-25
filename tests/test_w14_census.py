"""W-14 - the Cboe open-close census gate, and the executor's rejection of the scout's draft.

Run as its own process and judged by EXIT CODE (`RUN_RULES` PART 0), never by grepping output.

CI-SAFE BY CONSTRUCTION, and that is `O-1`'s lesson applied at the start rather than after a
failed land: CI has no WRDS credentials and no `data/`, so every guard about the SOURCE and the
VERDICT runs everywhere, and only the checks that need a live grant or a written artifact skip -
LOUDLY, with a reason. `MB42`: a guard whose only real execution is skipped IS the defect.
"""
import ast
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402  MUST precede any valuation import

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

DRAFT = os.path.join(REPO, "PREREG_DRAFT_w14_cboe_openclose.md")
VERDICT = os.path.join(REPO, "W14_EXECUTOR_VERDICT.md")
SRC = os.path.join(REPO, "scripts", "w14_census.py")


def _src(p):
    with io.open(p, encoding="utf-8") as fh:
        return fh.read()


def _tree(p):
    return ast.parse(_src(p))


def _artifact(name):
    """The census artifacts live under the licensed data root, which CI does not have."""
    for cand in (os.path.join(REPO, "data"),
                 os.path.abspath(os.path.join(REPO, "..", "..", "..", "data"))):
        p = os.path.join(cand, "free_analysis", name)
        if os.path.isfile(p):
            return p
    return None


class TestTheDraftAndTheVerdict(unittest.TestCase):
    def test_both_documents_exist(self):
        """A citation a reader cannot check is not a citation - `V6`'s own defect."""
        self.assertTrue(os.path.isfile(DRAFT), "the scout's draft is missing")
        self.assertTrue(os.path.isfile(VERDICT), "the executor's verdict is missing")

    def test_the_verdict_rejects_and_names_the_kill_that_fired(self):
        s = _src(VERDICT)
        self.assertIn("REJECTED", s)
        self.assertIn("K3", s)
        self.assertIn("ZERO TRIALS", s.upper())

    def test_the_draft_is_not_edited_into_agreement(self):
        """An executor rejects a draft; it does not rewrite it into one that would have passed.
        `MB1`'s discipline - run the rule AS WRITTEN and report the defect."""
        s = _src(DRAFT)
        self.assertIn("K3", s)
        self.assertIn("DRAFT", s.upper())
        # the draft must still carry the premise this verdict refutes, or the refutation is moot
        self.assertIn("census", s.lower())

    def test_the_verdict_states_power_at_both_vocabularies(self):
        """`RUN_RULES` A-11 and the brief's explicit requirement: power BEFORE any floor."""
        s = _src(VERDICT)
        self.assertIn("80%-power", s)
        self.assertIn("50%-power", s)
        for token in ("3.3853", "3.3133", "4.2253", "4.1533"):
            self.assertIn(token, s, "the verdict omits a hurdle/multiplier it claims to derive")

    def test_the_verdict_argues_each_graveyard_tag_by_name(self):
        s = _src(VERDICT)
        for tag in ("MB15", "MB16", "O14", "R2", "MB12", "D4", "S25"):
            self.assertIn(tag, s, "graveyard tag %s not argued" % tag)


class TestThePowerArithmetic(unittest.TestCase):
    """Derived, never transcribed. `MB32`: a hand-typed figure goes stale the moment N moves."""

    def test_the_hurdles_and_multipliers_reproduce(self):
        from valuation.edge import statistics as st

        co, ce = st.hlz_hurdle(308), st.hlz_hurdle(242)
        self.assertAlmostEqual(co, 3.3853, places=3)
        self.assertAlmostEqual(ce, 3.3133, places=3)
        self.assertAlmostEqual(co + 0.84, 4.2253, places=3)
        self.assertAlmostEqual(ce + 0.84, 4.1533, places=3)

    def test_the_drafts_reference_figure_is_at_the_retired_bar(self):
        """The draft fixes the number to beat as MB16's SE 0.04817 -> a 50%-power MDE of
        +9.64pp. That is 2.0 x SE - the RETIRED 2.0 convention - and at this project's own
        hurdle the same SE gives +16.31pp. A successor inheriting it would set its floor at
        roughly half the required size. `MB22`'s vocabulary correction, landing on a live draft."""
        from valuation.edge import statistics as st

        se = 0.04817
        self.assertAlmostEqual(2.0 * se * 100, 9.634, places=2)          # the draft's figure
        crit = st.hlz_hurdle(308)
        self.assertAlmostEqual(crit * se * 100, 16.3069, places=3)       # the honest one
        self.assertGreater(crit * se, 1.6 * (2.0 * se))                  # ~1.7x, not a rounding

    def test_power_against_mb16s_own_observed_effect_is_tiny(self):
        from valuation.edge import power_gate as pg

        self.assertLess(pg.power_at(0.0835, 0.04817, n_trials=308), 0.10)


class TestTheCensusIsReadOnly(unittest.TestCase):
    """The draft's fence: WRDS research-only, raw rows never leave `D:\\wrds`. The strongest
    way to honour it is never to materialise a row - checked on the syntax tree, not by grep."""

    def test_no_write_statement_appears_anywhere(self):
        s = _src(SRC).lower()
        for banned in ("insert into", "update ", "delete from", "drop ", "create table",
                       "copy ", "to_csv", "to_pickle", "to_parquet"):
            self.assertNotIn(banned, s, "the census can write: %r" % banned)

    def test_every_query_is_a_select(self):
        """Parsed, not grepped: every string literal handed to raw_sql must begin with select."""
        bad = []
        for node in ast.walk(_tree(SRC)):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            if name not in ("raw_sql", "sql"):
                continue
            for a in node.args:
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    if not a.value.strip().lower().startswith("select"):
                        bad.append(a.value[:60])
        self.assertEqual(bad, [], "non-SELECT handed to the driver: %r" % bad)

    def test_it_refuses_without_credentials_rather_than_guessing(self):
        t = _tree(SRC)
        fn = [n for n in ast.walk(t)
              if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
        raises = [n for n in ast.walk(fn) if isinstance(n, ast.Raise)]
        self.assertGreaterEqual(len(raises), 1, "no refusal on absent credentials")

    def test_the_k3_vocabulary_is_declared_and_not_a_single_guessed_name(self):
        """`WRDS_CENSUS.md`'s own lesson: a census that probes the names in a brief measures the
        brief. K3 needs a customer-vs-firm split on OPENING volume, so all three families are
        enumerated rather than one name guessed."""
        import w14_census as W

        self.assertGreaterEqual(len(W.K3_CUSTOMER), 3)
        self.assertGreaterEqual(len(W.K3_FIRM), 3)
        self.assertTrue(any("open" in x for x in W.K3_OPEN))
        self.assertGreaterEqual(len(W.NEEDLES), 5)


class TestTheMeasuredFindings(unittest.TestCase):
    """Skips LOUDLY where the artifact is absent - CI has no `data/`."""

    def _load(self, name):
        p = _artifact(name)
        if p is None:
            self.skipTest("no %s on this machine (data/ is gitignored; CI has none of it). "
                          "The SOURCE and VERDICT guards in this file still run." % name)
        with io.open(p, encoding="utf-8") as fh:
            return json.load(fh)

    def test_no_openclose_product_exists_on_this_grant(self):
        d = self._load("W14_CENSUS.json")
        self.assertEqual(d["openclose_candidates_account_wide"], [])
        self.assertEqual(d["gate"], "NO_PRODUCT")
        self.assertGreaterEqual(d["n_libraries"], 200)

    def test_the_cboe_library_is_the_ivydb_shape_and_not_a_volume_product(self):
        d = self._load("W14_CENSUS.json")
        names = d["cboe_table_names"]["cboe"]
        self.assertIn("optprice_2020", names)
        self.assertIn("ivlisted_2020", names)
        self.assertFalse([n for n in names if "opencl" in n.lower()])

    def test_no_table_anywhere_splits_customer_from_firm_on_options_volume(self):
        d = self._load("W14_CENSUS_COLUMNS.json")
        both = d["tables_with_customer_AND_firm_columns"]
        # the only hits are Bureau van Dijk registries - false positives on the substring 'firm'
        for b in both:
            self.assertTrue(b["table"].startswith("bvd"),
                            "an unexpected customer/firm table: %r" % b["table"])

    def test_the_retail_identifier_exists_and_is_denied(self):
        """Corrects `WRDS_CENSUS.md`, which searched LIBRARY names for a product living in
        TABLE names and reported it ABSENT-ON-THIS-LOGIN."""
        d = self._load("W14_RETAIL_IDENTIFIER.json")
        self.assertGreater(d["n_tables_with_retail_columns"], 50)
        self.assertFalse(d["any_readable"], "a retail table now reads - the verdict needs re-run")


if __name__ == "__main__":
    unittest.main(verbosity=2)
