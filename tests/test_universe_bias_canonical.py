# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 3/4 -- the canonical re-run, the books, and the things that would make
any of it meaningless.

The central risk in this item is **not** getting a wrong number. It is **writing one over the
project's memory**. `BACKTEST_RESULTS.json` is the tracked canonical artifact every public
figure on `/proof` reads at request time, and the shipped runner wrote to the repo root
unconditionally. So most of this file pins the containment:

  * the runner takes `--results-root`, defaulting to `None` i.e. the repo root, so
    `run_backtest.bat`, `RUN_RULES` PART 0's documented command and CI are all unchanged;
  * when it is given, the run SAYS the pair is not the canonical one;
  * `served_index_book` and `n1_band_book` take `panel_path`/`out`, likewise defaulting to the
    objects they already measured;
  * and `INDEX-BOOK`'s pre-committed `C1` fidelity gate is NOT weakened to let a new panel
    through -- a gate repointed so it stops comparing against the banked figure is not a gate.
"""
import ast
import inspect
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _fa():
    for c in (os.environ.get("VALQUO_DATA_ROOT"), os.path.join(REPO, "data"),
              r"C:\Users\donni\Downloads\valuation-tool\data"):
        if c and os.path.isdir(os.path.join(c, "free_analysis")):
            return os.path.join(c, "free_analysis")
    return None


def _src(rel):
    return io.open(os.path.join(REPO, rel), encoding="utf-8").read()


def _module_constant(rel, name):
    """Read a module-level constant WITHOUT importing the module.

    `served_index_book` builds `OUT` from the licensed data root at import time, so importing it
    raises on a CI runner. Parsing is not a workaround here, it is the better check: it runs
    everywhere, and a guard that silently skips where the data is absent is the
    `guards-that-fail-open-in-CI` family.
    """
    tree = ast.parse(_src(rel))
    for n in tree.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if getattr(t, "id", None) == name:
                    return ast.literal_eval(n.value)
    raise AssertionError("%s has no module-level %s" % (rel, name))


def _signature_defaults(rel, func):
    """(param names, whether every one defaults to None) for a top-level function, from source."""
    tree = ast.parse(_src(rel))
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == func:
            args = [a.arg for a in n.args.args]
            defaults = {}
            offset = len(args) - len(n.args.defaults)
            for i, d in enumerate(n.args.defaults):
                defaults[args[offset + i]] = (isinstance(d, ast.Constant) and d.value is None)
            return args, defaults
    raise AssertionError("%s has no def %s" % (rel, func))


class TheCanonicalArtifactCannotBeWrittenByAccident(unittest.TestCase):
    def test_the_runner_takes_a_results_root_that_defaults_to_the_repo_root(self):
        s = _src("valuation/edge/fundamental_panel.py")
        self.assertIn('ap.add_argument("--results-root", default=None', s)

    def test_the_default_still_resolves_to_the_repo_root(self):
        """`None` must reach `results_file.write` as `None`, because that is what makes it call
        `repo_root()` -- the behaviour every existing caller already has."""
        s = _src("valuation/edge/fundamental_panel.py")
        self.assertIn("root=args.results_root or None", s)

    def test_a_non_canonical_run_SAYS_it_is_not_canonical(self):
        """A run whose pair is not the tracked one must not print the same line as one whose
        pair is. A print that names the wrong object is how a reader comes to act on a file
        they have not looked at -- which cost a correct artifact earlier in this item."""
        s = _src("valuation/edge/fundamental_panel.py")
        self.assertIn("NOT the tracked canonical pair", s)

    def test_the_writer_still_honours_an_explicit_root(self):
        from valuation.edge import results_file
        sig = inspect.signature(results_file.write)
        self.assertIn("root", sig.parameters)
        self.assertIsNone(sig.parameters["root"].default)
        self.assertIn("root = root or repo_root()", inspect.getsource(results_file.write))

    def test_nothing_in_this_item_WRITES_the_canonical_artifact(self):
        """No `UNIVERSE-BIAS` script may open the canonical artifact for WRITING.

        **The first cut of this guard banned the NAME, and it fired against a correct tree** --
        part 4's whole job is to READ `BACKTEST_RESULTS.json` and table it against the corrected
        runs. That is the substring-ban family this record names repeatedly: a guard that bans a
        token trips on the legitimate use. The property is about the write MODE, so it is read
        off the AST of each `open`/`io.open` call and its path expression.
        """
        checked = 0
        for f in sorted(os.listdir(os.path.join(REPO, "scripts"))):
            if not f.startswith("universe_bias"):
                continue
            src = _src("scripts/" + f)
            tree = ast.parse(src)
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                fn = n.func
                name = getattr(fn, "id", None) or getattr(fn, "attr", None)
                if name != "open":
                    continue
                mode = ""
                if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                    mode = str(n.args[1].value)
                for kw in n.keywords or []:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = str(kw.value.value)
                if "w" not in mode and "a" not in mode:
                    continue
                checked += 1
                seg = ast.get_source_segment(src, n.args[0]) if n.args else ""
                self.assertNotIn("BACKTEST_RESULTS", seg or "",
                                 "%s opens the canonical artifact for writing" % f)
        self.assertGreater(checked, 0,
                           "no write-mode open was examined, so this guard proved nothing")

    def test_that_guard_would_catch_a_real_write(self):
        """Non-vacuity, in the one direction that matters."""
        bad = "import io\n" + 'io.open("BACKTEST_RESULTS.json", "w")' + "\n"
        tree = ast.parse(bad)
        hits = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and getattr(n.func, "attr", None) == "open":
                mode = n.args[1].value if len(n.args) > 1 else ""
                if "w" in str(mode):
                    hits.append(ast.get_source_segment(bad, n.args[0]))
        self.assertTrue(any("BACKTEST_RESULTS" in (h or "") for h in hits))

    def test_part_four_DOES_read_the_canonical_artifact(self):
        """And it must: the published column is the only one the public pages actually show."""
        self.assertIn("BACKTEST_RESULTS.json", _src("scripts/universe_bias_public.py"))

    def test_this_item_imports_nothing_that_needs_the_licensed_data_at_IMPORT_time(self):
        """THE DEFECT THIS PINS, and it is mine: `served_index_book` computes
        `DATA = _data_root()` at module level with `required` defaulting to True, so importing
        it RAISES wherever `data/` is absent -- every CI runner. A module-level import of it
        made `universe_bias_books` unimportable in CI and three tests ERRORED rather than
        running. `guards-that-fail-open-in-CI`: a check whose input is licensed does not run
        where the data lives, so it must not need the data to be imported at all.
        """
        risky = ("served_index_book", "n1_band_book")
        for f in sorted(os.listdir(os.path.join(REPO, "scripts"))):
            if not f.startswith("universe_bias"):
                continue
            tree = ast.parse(_src("scripts/" + f))
            for n in tree.body:            # MODULE level only -- a deferred import is fine
                mods = []
                if isinstance(n, ast.Import):
                    mods = [a.name for a in n.names]
                elif isinstance(n, ast.ImportFrom):
                    mods = [n.module or ""]
                for m in mods:
                    for r in risky:
                        self.assertNotIn(r, m,
                                         "%s imports %s at module level; it raises in CI" % (f, r))

    def test_the_unguarded_data_root_is_recorded_rather_than_edited(self):
        """`served_index_book`'s unguarded `_data_root()` is `INDEX-BOOK`'s, not this item's.
        Changing it could move a landed figure, so it is worked around and NAMED."""
        self.assertIn("DATA = _data_root()", _src("scripts/served_index_book.py"))
        self.assertIn("required` defaulting to True", _src("scripts/universe_bias_books.py"))


class TheFidelityGateIsNotWeakened(unittest.TestCase):
    def test_index_book_still_aborts_when_C1_fails(self):
        s = _src("scripts/served_index_book.py")
        self.assertIn("if not c1[\"pass\"]:", s)
        self.assertIn("C1 FAILED", s)

    def test_the_published_reference_is_still_the_banked_figure(self):
        s = _src("scripts/served_index_book.py")
        self.assertIn("0.07174142332098163", s)

    def test_the_books_runner_records_a_refusal_rather_than_dying_on_it(self):
        """`SystemExit` is not an `Exception`, so catching only `Exception` let the first
        refusal kill the whole runner -- which is how three of four readings went missing."""
        s = _src("scripts/universe_bias_books.py")
        self.assertIn("except SystemExit", s)
        self.assertIn('"refused"', s)
        tree = ast.parse(s)
        handlers = [h for n in ast.walk(tree) if isinstance(n, ast.Try) for h in n.handlers]
        names = {getattr(h.type, "id", None) for h in handlers}
        self.assertIn("SystemExit", names)
        self.assertIn("Exception", names)

    def test_the_runner_quotes_the_published_reference_from_the_record(self):
        self.assertEqual(
            _module_constant("scripts/universe_bias_books.py", "PUBLISHED_TOP_DECILE_ALPHA"),
            0.07174142332098163)

    def test_that_reference_matches_the_landed_artifact(self):
        fa = _fa()
        p = os.path.join(fa or "", "INDEX_BOOK.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: INDEX_BOOK.json is not on this machine")

        class B:
            PUBLISHED_TOP_DECILE_ALPHA = _module_constant(
                "scripts/universe_bias_books.py", "PUBLISHED_TOP_DECILE_ALPHA")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertEqual(float(d["C1_fidelity"]["published"]), B.PUBLISHED_TOP_DECILE_ALPHA)


class TheADVHazardIsMeasuredAtTheRealShapes(unittest.TestCase):
    def test_the_probe_reads_the_dict_and_the_frame_differently(self):
        """`MC9_SEP_ADV.pkl` is a `{"census", "by_ticker"}` DICT and `B13_ADV_PANEL.pkl` is a
        long FRAME. A probe assuming a frame for both returned a confident 0.0000 on BOTH
        sides -- a check that could not answer the question, answering it anyway."""
        s = _src("scripts/universe_bias_books.py")
        self.assertIn("isinstance(d, dict)", s)
        self.assertIn('d.get("by_ticker")', s)
        self.assertIn("isinstance(a, pd.DataFrame)", s)

    def test_coverage_is_reported_at_BOTH_name_and_cell_level(self):
        from scripts.universe_bias_books import coverage
        import pandas as pd
        panel = pd.DataFrame({"date": ["2009-01-15", "2009-01-15", "2009-04-15"],
                              "ticker": ["AAA", "BBB", "AAA"]})
        c = coverage(panel, {"AAA"}, {("2009-01-15", "AAA")})
        self.assertEqual(c["panel_names"], 2)
        self.assertEqual(c["names_with_adv_input"], 1)
        self.assertAlmostEqual(c["name_share"], 0.5)
        self.assertEqual(c["panel_cells"], 3)
        self.assertEqual(c["cells_in_crsp_adv"], 1)

    def test_the_caveat_travels_in_the_artifact_not_only_in_prose(self):
        s = _src("scripts/universe_bias_books.py")
        self.assertIn('"adv_caveat"', s)
        self.assertIn("NOT like-for-like", s)


class TheParameterisationsAreProvedInertRatherThanArgued(unittest.TestCase):
    def test_both_books_default_to_the_object_they_already_measured(self):
        """Read from SOURCE, not by importing: `served_index_book` builds `OUT` from the
        licensed data root at import time, so importing it RAISES on a CI runner -- and a check
        that skips exactly where the data lives is the `guards-that-fail-open-in-CI` family."""
        for rel in ("scripts/served_index_book.py", "scripts/n1_band_book.py"):
            args, defaults = _signature_defaults(rel, "main")
            for want in ("panel_path", "out", "label"):
                self.assertIn(want, args, "%s main lacks %s" % (rel, want))
                self.assertTrue(defaults.get(want),
                                "%s's %s must default to None so the original path is "
                                "unchanged" % (rel, want))
            src = _src(rel)
            self.assertIn('panel_path or os.path.join(FA, "panel_corrected_69d.pkl")', src)
            self.assertIn("out or OUT", src)

    def test_the_label_is_LOAD_BEARING_and_not_a_decorative_parameter(self):
        """An unused parameter is worse than none: it reads as a guarantee the artifact says
        which universe it describes, while the artifact says nothing."""
        for rel in ("scripts/served_index_book.py", "scripts/n1_band_book.py"):
            s = _src(rel)
            self.assertIn('res["universe_label"] = label or', s)
            self.assertIn('res["panel"] = os.path.basename(panel_path or', s)

    def test_the_inertness_diff_refuses_an_empty_comparison(self):
        """`MB21`: a perfect 0.000e+00 on nothing compared is not a pass."""
        from scripts.universe_bias_inert import diff, EXPECTED_NEW
        import tempfile
        d = tempfile.mkdtemp()
        a, b = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        json.dump({}, io.open(a, "w", encoding="utf-8"))
        json.dump({}, io.open(b, "w", encoding="utf-8"))
        self.assertFalse(diff(a, b)["ok"], "an empty-vs-empty diff must not read as INERT")
        self.assertEqual(tuple(EXPECTED_NEW), ("panel", "universe_label"))

    def test_the_inertness_diff_catches_a_moved_leaf_and_an_unexpected_key(self):
        from scripts.universe_bias_inert import diff
        import tempfile
        d = tempfile.mkdtemp()
        a, b = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        json.dump({"x": 1.0, "y": {"z": 2.0}}, io.open(a, "w", encoding="utf-8"))
        json.dump({"x": 1.0, "y": {"z": 2.5}}, io.open(b, "w", encoding="utf-8"))
        r = diff(a, b)
        self.assertFalse(r["ok"])
        self.assertEqual(r["n_moved"], 1)
        self.assertAlmostEqual(r["max_abs_dev"], 0.5)
        json.dump({"x": 1.0, "y": {"z": 2.0}, "surprise": 9}, io.open(b, "w", encoding="utf-8"))
        r = diff(a, b)
        self.assertFalse(r["ok"], "an unexpected new key must not pass as inert")
        self.assertIn("surprise", r["unexpected_added"])

    def test_the_two_expected_keys_ARE_tolerated(self):
        from scripts.universe_bias_inert import diff
        import tempfile
        d = tempfile.mkdtemp()
        a, b = os.path.join(d, "a.json"), os.path.join(d, "b.json")
        json.dump({"x": 1.0}, io.open(a, "w", encoding="utf-8"))
        json.dump({"x": 1.0, "panel": "p.pkl", "universe_label": "u"},
                  io.open(b, "w", encoding="utf-8"))
        self.assertTrue(diff(a, b)["ok"])

    def test_the_landed_inertness_artifact_records_a_non_vacuous_pass(self):
        fa = _fa()
        p = os.path.join(fa or "", "UNIVERSE_BIAS_INERT.json")
        if not fa or not os.path.exists(p):
            self.skipTest("LOUD SKIP: inertness artifact absent")
        d = json.load(io.open(p, encoding="utf-8"))
        self.assertTrue(d["all_inert"])
        for name, r in d["pairs"].items():
            self.assertFalse(r.get("skipped"), "%s was skipped, so it proves nothing" % name)
            self.assertGreater(r["shared"], 0, "%s compared nothing" % name)
            self.assertEqual(r["n_moved"], 0)


class ItChargesNothingAndClaimsNoAlpha(unittest.TestCase):
    def test_every_script_declares_zero_trials(self):
        for f in ("universe_bias_books.py", "universe_bias_inert.py"):
            self.assertIn("ZERO TRIALS", _src("scripts/" + f).upper())

    def test_no_calibrated_floor_is_quoted(self):
        for f in ("universe_bias_books.py", "universe_bias_inert.py"):
            s = _src("scripts/" + f)
            for fl in ("2.2837", "2.0540", "2.7072", "19.667", "1.8629", "0.6637"):
                self.assertNotIn(fl, s, "%s quotes the X7 floor %s" % (f, fl))


if __name__ == "__main__":
    unittest.main(verbosity=2)
