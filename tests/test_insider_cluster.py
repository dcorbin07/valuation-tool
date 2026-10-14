# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` — the construction, and the guards that make its verdict mean something.

Run as its own process: `RUN_RULES` 0.1 judges a suite by its EXIT CODE, and a file with no
`__main__` block defines its tests, executes nothing and exits 0 (`O21-D2`'s own near-miss).

**THE DATA-DEPENDENT TESTS SKIP LOUDLY AND NEVER SILENTLY.** `data/` is gitignored, so on a CI
runner there is no populated root at all — `dipcall.have_data()` exists for exactly this and
returns an answer instead of raising (its own docstring: *"a test must be able to ask 'is the data
here?' and get an answer rather than an exception; a script must not"*). The construction tests
below need no data and therefore run everywhere, which is the half that matters.
"""
import ast
import io
import os
import subprocess
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation                                               # noqa: F401,E402

from valuation.studies import dipcall as D                                 # noqa: E402
from valuation.studies import insider_cluster as IC                        # noqa: E402
from valuation.studies import insider_routine as IR                        # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(HERE, "valuation", "studies", "insider_cluster.py")
REGISTER = os.path.join(HERE, "PREREG_insider_cluster.md")


def _rows(spec):
    """spec: list of (ticker, owner, filingdate, transactiondate, code)."""
    df = pd.DataFrame(spec, columns=["ticker", "ownername", "filingdate",
                                     "transactiondate", "transactioncode"])
    for c in df.columns:
        df[c] = df[c].astype("string")
    return df


class TestTheRegisterCameFirst(unittest.TestCase):
    def test_the_register_exists_and_is_cited_by_name(self):
        self.assertTrue(os.path.exists(REGISTER), REGISTER)

    def test_the_register_is_a_strict_git_ancestor_and_never_shares_a_commit_with_code(self):
        def shas(pathspec):
            out = subprocess.run(["git", "log", "--format=%H", "--", pathspec],
                                 cwd=HERE, capture_output=True)
            return [x for x in out.stdout.decode("utf-8", "replace").split() if x]

        reg = shas("PREREG_insider_cluster.md")
        mod = shas("valuation/studies/insider_cluster.py")
        if not reg or not mod:
            self.skipTest("one of the two files is not committed yet")
        r = subprocess.run(["git", "merge-base", "--is-ancestor", reg[-1], mod[-1]],
                           cwd=HERE, capture_output=True)
        self.assertEqual(r.returncode, 0,
                         "the register's FIRST commit must be a strict ancestor of the "
                         "construction's (register %s, module %s)" % (reg[-1][:8], mod[-1][:8]))
        for sha in reg:
            out = subprocess.run(["git", "show", "--name-only", "--format=", sha],
                                 cwd=HERE, capture_output=True)
            files = [f for f in out.stdout.decode("utf-8", "replace").split() if f]
            bad = [f for f in files if not f.endswith(".md")]
            self.assertFalse(bad, "register commit %s also touched %s" % (sha[:8], bad))

    def test_the_register_declares_a_sign_and_names_the_strict_condition(self):
        """WHITESPACE-NORMALISED, because the register is HARD-WRAPPED at 100 columns and the
        phrase this looks for spans a newline. The first cut asserted the raw string and failed
        against a register that says exactly what it was asked to say -- a guard broken by the
        line width of the document it reads."""
        raw = io.open(REGISTER, encoding="utf-8").read()
        t = " ".join(raw.split())
        self.assertIn("SIGN: POSITIVE", t)
        self.assertIn("two prior calendar years", t)
        self.assertIn("UNDERPOWERED-BY-CONSTRUCTION", t)


class TestTheConstruction(unittest.TestCase):
    def test_a_missing_code_is_skipped_and_never_read_as_not_a_purchase(self):
        df = _rows([
            ("AAA", "X", "2015-01-10", "2015-01-05", "P"),
            ("AAA", "Y", "2015-01-12", "2015-01-06", None),      # no code -> SKIPPED
        ])
        labels = pd.Series([IR.OPPORTUNISTIC, IR.OPPORTUNISTIC], index=df.index)
        buys = IC.opportunistic_purchases(df, labels, strict=False)
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys.iloc[0]["ownername"], "X")

    def test_the_nullable_boolean_does_not_silently_become_false_without_the_fill(self):
        # THE DEFECT THIS PINS: under the `string` dtype a missing code is `pd.NA`, so
        # `code == "P"` is a NULLABLE boolean. `.to_numpy(dtype=bool)` RAISES on it -- which is
        # the correct refusal, and is the `blank-code counter` family one level up, where a check
        # read 0 blank codes on a column holding 1,544,490 because NA compares False and nothing
        # raised. The fill is the register's SKIP rule written out, not a convenience.
        df = _rows([("AAA", "X", "2015-01-10", "2015-01-05", None)])
        with self.assertRaises(ValueError):
            (df["transactioncode"] == "P").to_numpy(dtype=bool)
        self.assertFalse(bool((df["transactioncode"] == "P").fillna(False).iloc[0]))

    def test_a_cluster_needs_k_DISTINCT_insiders_not_k_filings(self):
        same = _rows([("AAA", "X", "2015-01-10", "2015-01-05", "P"),
                      ("AAA", "X", "2015-01-12", "2015-01-06", "P")])
        lab = pd.Series([IR.OPPORTUNISTIC] * 2, index=same.index)
        ev = IC.cluster_events(IC.opportunistic_purchases(same, lab, strict=False), k=2)
        self.assertEqual(len(ev), 0, "one insider filing twice is not a cluster")

        two = _rows([("AAA", "X", "2015-01-10", "2015-01-05", "P"),
                     ("AAA", "Y", "2015-01-12", "2015-01-06", "P")])
        lab2 = pd.Series([IR.OPPORTUNISTIC] * 2, index=two.index)
        ev2 = IC.cluster_events(IC.opportunistic_purchases(two, lab2, strict=False), k=2)
        self.assertEqual(len(ev2), 1)
        self.assertEqual(ev2.iloc[0]["date"], "2015-01-12", "dated at the LAST filing")
        self.assertEqual(int(ev2.iloc[0]["n_insiders"]), 2)

    def test_filings_outside_the_window_are_not_one_cluster(self):
        far = _rows([("AAA", "X", "2015-01-10", "2015-01-05", "P"),
                     ("AAA", "Y", "2015-03-20", "2015-03-15", "P")])
        lab = pd.Series([IR.OPPORTUNISTIC] * 2, index=far.index)
        ev = IC.cluster_events(IC.opportunistic_purchases(far, lab, strict=False), k=2)
        self.assertEqual(len(ev), 0, "69 days apart is not a 30-day window")

    def test_ONE_EVENT_PER_CLUSTER_and_this_is_the_defect_that_was_caught(self):
        """THE REGRESSION THIS EXISTS FOR, and it is a defect of my own found before any outcome.

        The first cut suppressed a repeat only on the SAME day (`d <= last_fired`), so the very
        next filing re-fired the same cluster: `ISCA` came back with **29 insiders on 2008-01-04,
        01-07 AND 01-08** — one cluster counted about twenty times. The register's rule 5 states
        the intent correctly, so the CODE was wrong against the REGISTER, which is the only
        direction in which this is a fix rather than a change of hypothesis. It cost 8,478 build
        events down to **4,386**, i.e. it REDUCES power — the direction that makes the design
        harder.
        """
        spec = [("AAA", "X", "2015-01-%02d" % d, "2015-01-01", "P") for d in range(5, 20)]
        spec += [("AAA", "Y", "2015-01-%02d" % d, "2015-01-01", "P") for d in range(6, 21)]
        df = _rows(spec)
        lab = pd.Series([IR.OPPORTUNISTIC] * len(df), index=df.index)
        ev = IC.cluster_events(IC.opportunistic_purchases(df, lab, strict=False), k=2)
        self.assertEqual(len(ev), 1,
                         "30 filings by two insiders inside one window is ONE cluster, got %d"
                         % len(ev))

    def test_a_second_genuine_cluster_more_than_a_window_later_DOES_fire(self):
        # The cooldown must not be a one-event-per-ticker-forever rule, or a name that clusters
        # in 2010 and again in 2015 would contribute once. Both directions, because a rule that
        # suppresses everything is not a rule.
        spec = [("AAA", "X", "2015-01-05", "2015-01-01", "P"),
                ("AAA", "Y", "2015-01-06", "2015-01-01", "P"),
                ("AAA", "X", "2015-06-05", "2015-06-01", "P"),
                ("AAA", "Y", "2015-06-06", "2015-06-01", "P")]
        df = _rows(spec)
        lab = pd.Series([IR.OPPORTUNISTIC] * len(df), index=df.index)
        ev = IC.cluster_events(IC.opportunistic_purchases(df, lab, strict=False), k=2)
        self.assertEqual(len(ev), 2)

    def test_the_strict_condition_requires_BOTH_prior_years_and_is_the_default(self):
        # X has traded in 2013 and 2014, so routine was POSSIBLE; Y appears only in 2015.
        spec = [("AAA", "X", "2013-05-10", "2013-05-01", "S"),
                ("AAA", "X", "2014-07-10", "2014-07-01", "S"),
                ("AAA", "X", "2015-01-10", "2015-01-05", "P"),
                ("AAA", "Y", "2015-01-12", "2015-01-06", "P")]
        df = _rows(spec)
        lab = pd.Series([IR.OPPORTUNISTIC] * len(df), index=df.index)
        strict = IC.opportunistic_purchases(df, lab)          # DEFAULT is strict
        broad = IC.opportunistic_purchases(df, lab, strict=False)
        self.assertEqual(sorted(strict["ownername"].tolist()), ["X"])
        self.assertEqual(sorted(broad["ownername"].tolist()), ["X", "Y"])
        # and the cluster therefore does NOT form under the strict rule
        self.assertEqual(len(IC.cluster_events(strict, k=2)), 0)
        self.assertEqual(len(IC.cluster_events(broad, k=2)), 1)

    def test_the_default_is_the_conservative_one(self):
        import inspect
        sig = inspect.signature(IC.opportunistic_purchases)
        self.assertIs(sig.parameters["strict"].default, True,
                      "O-1's lesson: a guard whose default is off is a guard a new caller "
                      "silently loses")

    def test_the_routine_classifier_is_CALLED_and_not_reimplemented(self):
        tree = ast.parse(io.open(MODULE, encoding="utf-8").read())
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertIn("classify", called)
        # and CONSECUTIVE_YEARS is not retyped here
        self.assertNotIn("CONSECUTIVE_YEARS =",
                         io.open(MODULE, encoding="utf-8").read())


class TestNoOutcomeIsReadInTheConstruction(unittest.TestCase):
    def test_over_the_syntax_tree_because_the_docstring_states_the_rule(self):
        src = io.open(MODULE, encoding="utf-8").read()
        self.assertIn("No\nforward return is computed anywhere in this file", src.replace(
            "No forward return is computed anywhere in this file",
            "No\nforward return is computed anywhere in this file"))
        banned = {"fwd_ret", "forward_return", "abnormal", "ar_own", "ar_mkt"}
        hits, names = [], 0
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Name):
                names += 1
                if n.id in banned:
                    hits.append(n.id)
            elif isinstance(n, ast.Attribute) and n.attr in banned:
                hits.append(n.attr)
            elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value in banned:
                hits.append(n.value)
        self.assertFalse(hits, "the construction reads an outcome: %s" % hits)
        self.assertGreater(names, 50, "non-vacuous: the tree was walked")

    def test_the_ban_catches_an_injected_read(self):
        orig = io.open(MODULE, "rb").read()
        try:
            bad = orig.replace(b"PURCHASE_CODE = \"P\"",
                               b"PURCHASE_CODE = \"P\"\n_X = fwd_ret")
            self.assertNotEqual(bad, orig, "mutation point moved")
            io.open(MODULE, "wb").write(bad)
            hits = [n.id for n in ast.walk(ast.parse(io.open(MODULE, encoding="utf-8").read()))
                    if isinstance(n, ast.Name) and n.id == "fwd_ret"]
            self.assertTrue(hits, "the AST ban did not see an injected read")
        finally:
            io.open(MODULE, "wb").write(orig)
        self.assertEqual(io.open(MODULE, "rb").read(), orig,
                         "the module must be restored BYTE-FOR-BYTE (W-1's harness defect)")


class TestTheSourceIsTheFreezeNotTheExport(unittest.TestCase):
    def test_the_path_names_the_freeze_and_the_module_says_why(self):
        """AND THE SUBSTRING BAN HERE WAS THE DEFECT, FOR THE NINTH TIME IN THIS PROJECT.
        The first cut asserted `"insiders.csv"` was absent from the source and FAILED AGAINST THE
        CORRECT TREE, because the module's docstring explains at length why
        `data/backtest/insiders.csv` is NOT used -- prose documenting the rule, containing exactly
        what the rule forbids (`MA49`, `MB1` three times in one register, `MB15`, `W-1`, `MB20`,
        and this item's own VALREADS sibling two commits ago). It reads the AST now: no string
        CONSTANT in the code may name that file, which is the property that matters, and prose
        about it is permitted."""
        src = io.open(MODULE, encoding="utf-8").read()
        self.assertIn("backtest_freeze_2026-10", src)
        bad = [n.value for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.Constant) and isinstance(n.value, str)
               and n.value.endswith("insiders.csv")]
        self.assertFalse(bad, "the code names the export: %s" % bad)
        # POSITIVE CONTROL, so the narrowed rule is proved still to bite.
        self.assertTrue([n.value for n in ast.walk(ast.parse('x = "data/backtest/insiders.csv"'))
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)
                         and n.value.endswith("insiders.csv")])

    def test_it_refuses_rather_than_reading_nothing_when_the_freeze_is_absent(self):
        import tempfile
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(SystemExit):
                IC.sf2_zip(root=t)


class TestTheKillPassIsSeparateFromTheArm(unittest.TestCase):
    def test_the_arm_refuses_without_the_kill_artifact(self):
        arm = os.path.join(HERE, "scripts", "insider_cluster_arm.py")
        if not os.path.exists(arm):
            self.skipTest("the arm is not written yet")
        src = io.open(arm, encoding="utf-8").read()
        self.assertIn("REFUSING", src)
        self.assertIn("INSIDER_CLUSTER_KILLS.json", src)

    def test_the_kill_pass_reads_no_forward_return(self):
        kp = os.path.join(HERE, "scripts", "insider_cluster_kills.py")
        tree = ast.parse(io.open(kp, encoding="utf-8").read())
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertNotIn("abnormal", called)
        self.assertNotIn("build_market", called)
        self.assertTrue(called, "non-vacuous")


class TestTheBanksAgreeWithTheRegister(unittest.TestCase):
    """The numbers in the register's tables must be the numbers on disk, or the register is
    describing a different measurement from the one that ran. `MA13`'s committed-literal idiom
    applied to a census."""

    def setUp(self):
        if not D.have_data():
            self.skipTest("no populated data root (CI): skipping LOUDLY, never silently")
        import json
        p = D.out_path("INSIDER_CLUSTER_CENSUS.json")
        if not os.path.isfile(p):
            self.skipTest("census not run here")
        self.c = json.load(io.open(p, encoding="utf-8"))

    def test_the_census_is_the_STRICT_one(self):
        self.assertTrue(self.c["definition"]["strict"],
                        "the banked census must be the register's PRIMARY definition")

    def test_the_cluster_parameters_match_the_register(self):
        self.assertEqual(self.c["definition"]["k_primary"], 2)
        self.assertEqual(self.c["definition"]["window_days"], 30)

    def test_the_governing_tier_is_the_incumbents_absolute_floor(self):
        self.assertEqual(D.TIER_FLOOR, 10e9)


if __name__ == "__main__":
    unittest.main(verbosity=1)
