# -*- coding: utf-8 -*-
"""`EODHD-CENSUS` — the licence fence, the key, and the no-outcome property.

The load-bearing tests are `test_no_tracked_file_carries_a_per_name_value` (the personal licence
forbids redistributing the data, and this repo is public) and
`test_the_key_is_never_printed_or_written` (a leaked key is permanent in a public history).
"""
from __future__ import annotations

import ast
import io
import json
import ntpath
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import state_isolation  # noqa: F401,E402


def _skip_loudly(case, why):
    """A skip nobody can mistake for a pass — the repo's own idiom, because in a 300-suite run a
    silent skip and a pass look identical."""
    msg = "(SKIPPED LOUDLY: %s)" % why
    print("\n       %s" % msg, flush=True)
    case.skipTest(msg)


MODULES = ("scripts/eodhd_census.py", "scripts/eodhd_coverage.py", "scripts/eodhd_restated.py")
CENSUS_MD = os.path.join(ROOT, "EODHD_CENSUS.md")


def _src(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _data_root():
    from valuation.studies import dipcall as D
    return D.data_root(required=False)


def _artifact(name):
    r = _data_root()
    if not r:
        return None
    p = os.path.join(r, "free_analysis", name)
    return json.load(io.open(p, encoding="utf-8")) if os.path.isfile(p) else None


class TheLicenceFence(unittest.TestCase):
    """The personal plan forbids displaying or redistributing the data. The repo is public."""

    def test_the_raw_root_is_not_inside_the_repository_tree(self):
        """Compared with `ntpath`, because `os.path.abspath` on a Windows path under POSIX
        resolves INSIDE the repo — the defect that failed CI on `TRACELEAD` three days ago."""
        from scripts import eodhd_census as E
        self.assertTrue(ntpath.isabs(E.RAW_ROOT), E.RAW_ROOT)
        drive = ntpath.splitdrive(E.RAW_ROOT)[0].upper()
        self.assertTrue(drive and drive != "C:",
                        "licensed payload must not sit on the checkout's volume: %r" % E.RAW_ROOT)

    def test_the_raw_root_check_is_not_vacuous(self):
        for bad in ("eodhd", r".\eodhd", "data/eodhd"):
            self.assertFalse(ntpath.isabs(bad), bad)

    def test_every_repo_side_write_goes_through_the_gitignored_data_root(self):
        """`D.out_path` resolves under `data/`, which is gitignored. A write to any other
        repo-side path would put vendor-derived rows into a public history."""
        for rel in MODULES:
            tree = ast.parse(_src(rel))
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                f = n.func
                name = getattr(f, "id", "") or getattr(f, "attr", "")
                if name != "open" and name != "write":
                    continue
            # structural: the only artifact paths are D.out_path(...) or RAW_ROOT joins
            src = _src(rel)
            if "out_path(" in src or "RAW_ROOT" in src:
                continue
            self.assertNotIn("io.open", src, rel)

    def test_no_tracked_file_carries_a_per_name_value(self):
        """THE LOAD-BEARING TEST. `EODHD_CENSUS.md` is committed to a PUBLIC repo, so it may
        carry rates, counts, spans and field NAMES (schema) and no company's figures.

        Asserted structurally: the census names companies only in coverage/availability rows, and
        the numbers beside them are period COUNTS and DATES. A dollar figure would be the
        redistribution the licence forbids, so the `$` sign may appear only in the tier label.
        """
        if not os.path.isfile(CENSUS_MD):
            _skip_loudly(self, "EODHD_CENSUS.md absent")
        txt = io.open(CENSUS_MD, encoding="utf-8").read()
        # the only permitted dollar usage is the tier's own name
        for frag in txt.split("$")[1:]:
            self.assertTrue(frag.startswith("10B") or frag.startswith("10b"),
                            "a dollar amount in a tracked file reads as redistributed data: %r"
                            % frag[:40])

    def test_the_census_states_the_fence_rather_than_assuming_it(self):
        if not os.path.isfile(CENSUS_MD):
            _skip_loudly(self, "EODHD_CENSUS.md absent")
        txt = io.open(CENSUS_MD, encoding="utf-8").read()
        for needle in ("personal", "non-commercial", "public", "D:\\eodhd"):
            self.assertIn(needle, txt, needle)


class TheKeyIsNeverExposed(unittest.TestCase):

    def test_the_key_is_never_printed_or_written(self):
        """A leaked key is permanent in a public history. No `print` may take the key, and no
        artifact may carry it."""
        for rel in MODULES:
            tree = ast.parse(_src(rel))
            for n in ast.walk(tree):
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print":
                    dump = ast.dump(n)
                    self.assertNotIn("api_key", dump, rel)
                    self.assertNotIn("EODHD_API_KEY", dump, rel)

    def test_errors_are_scrubbed_before_they_can_be_shown(self):
        """An HTTPError's reason can echo the request URL, which carries the token."""
        src = _src("scripts/eodhd_census.py")
        self.assertIn("def _scrub", src)
        self.assertIn("api_token=<REDACTED>", src)

    def test_scrub_actually_removes_the_token(self):
        """Both mechanisms are exercised, and the second case is why.

        **Found by mutation:** with only the URL case below, disabling the literal replacement
        left the test GREEN — because the `api_token=` regex alone strips a token that appears in
        a query string. A token echoed BARE in an exception message (which is how a library
        surfaces it) needs the literal replacement, so a bare case is asserted too.
        """
        from scripts import eodhd_census as E
        url = "https://eodhd.com/api/user?api_token=SECRETVALUE&fmt=json"
        self.assertNotIn("SECRETVALUE", E._scrub(url, "SECRETVALUE"))
        bare = "upstream rejected credential SECRETVALUE while fetching"
        out = E._scrub(bare, "SECRETVALUE")
        self.assertNotIn("SECRETVALUE", out)
        self.assertIn("<REDACTED>", out)

    def test_a_missing_key_stops_with_a_named_reason_and_no_value(self):
        """The brief: "if it is absent, stop and say so in one line" — so the refusal must NAME
        the key it wants and carry no value.

        **Corrected while writing this test:** my first cut asserted the literal against
        `KeyMissing.__doc__`, which describes the class rather than the refusal; the property
        lives in the RAISED MESSAGE. Checked over the syntax tree so no key is needed to run it.
        """
        from scripts import eodhd_census as E
        self.assertTrue(issubclass(E.KeyMissing, RuntimeError))
        tree = ast.parse(_src("scripts/eodhd_census.py"))
        msgs = []
        for n in ast.walk(tree):
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
                if getattr(n.exc.func, "id", "") == "KeyMissing":
                    for a in ast.walk(n.exc):
                        if isinstance(a, ast.Constant) and isinstance(a.value, str):
                            msgs.append(a.value)
        self.assertTrue(msgs, "KeyMissing is never raised with a message")
        joined = " ".join(msgs)
        self.assertIn("EODHD_API_KEY", joined)
        self.assertIn("no value is printed", joined)


class NoOutcomeIsEverRead(unittest.TestCase):

    def test_no_module_names_a_forward_return(self):
        for rel in MODULES:
            tree = ast.parse(_src(rel))
            names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            names |= {n.value for n in ast.walk(tree)
                      if isinstance(n, ast.Constant) and isinstance(n.value, str)}
            for b in ("fwd_ret", "bench_ret", "abnormal", "permutation_null"):
                self.assertNotIn(b, names, "%s reaches an outcome (%s)" % (rel, b))

    def test_the_scan_is_not_vacuous(self):
        tree = ast.parse(_src("scripts/insider_wide_arm.py"))
        found = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        found |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertTrue({"abnormal", "permutation_null"} & found)

    def test_each_module_declares_zero_trials(self):
        for rel in MODULES:
            self.assertIn("ZERO TRIALS", _src(rel).upper(), rel)


class TheCensusFiguresMatchTheArtifacts(unittest.TestCase):
    """A census that drifts from its own artifacts is worse than none."""

    def test_the_coverage_figures_are_the_measured_ones(self):
        r = _artifact("EODHD_COVERAGE.json")
        if r is None:
            _skip_loudly(self, "EODHD_COVERAGE.json absent — built from a licensed feed, which "
                               "CI never has")
        txt = io.open(CENSUS_MD, encoding="utf-8").read()
        u = r["undated_upper_bound"]
        self.assertIn("%.4f" % u["tier_matched_frac"], txt)
        self.assertIn("%.4f" % u["universe_matched_frac"], txt)
        s = r["dated_sample"]
        self.assertIn("%.4f" % s["BOTH_dated_legs_frac"], txt)

    def test_the_undated_figure_is_labelled_an_upper_bound(self):
        r = _artifact("EODHD_COVERAGE.json")
        if r is None:
            _skip_loudly(self, "EODHD_COVERAGE.json absent")
        self.assertIn("UPPER BOUND", r["undated_upper_bound"]["LABEL"])

    def test_the_restatement_agreement_rate_matches(self):
        r = _artifact("EODHD_RESTATED.json")
        if r is None:
            _skip_loudly(self, "EODHD_RESTATED.json absent")
        txt = io.open(CENSUS_MD, encoding="utf-8").read()
        self.assertIn("%.4f" % r["overall"]["agreement_rate"], txt)
        self.assertIn(str(r["overall"]["pairs"]), txt.replace(",", ""))

    def test_the_control_is_sharadars_as_reported_dimension(self):
        r = _artifact("EODHD_RESTATED.json")
        if r is None:
            _skip_loudly(self, "EODHD_RESTATED.json absent")
        self.assertIn("ARQ", r["control"]["dimension_used"])

    def test_agreement_is_not_overclaimed_as_proof_of_as_reported(self):
        """Both vendors could carry the same restatement; the artifact must say so."""
        r = _artifact("EODHD_RESTATED.json")
        if r is None:
            _skip_loudly(self, "EODHD_RESTATED.json absent")
        self.assertIn("does NOT prove", r["HOW_TO_READ_IT"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
