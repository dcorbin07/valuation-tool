"""
MA60: the register conventions, enforced instead of hand-verified. Run:

    python tests/test_ma60_conventions.py

The audit's charge is that the factory's rules are prose -- "handoff before
done", "thresholds before the run", "a ledger row per landing", "the canonical
artifact must not go stale" -- and that CI enforces none of them, so each one
holds exactly as long as every agent chooses to be honest. The phrase "strict
git ancestor" appears in the corpus dozens of times as HAND-VERIFIED evidence,
and `git merge-base --is-ancestor` is one line.

Three of the four are encoded here. Each was MEASURED before it was pinned,
because a check written from the prose rather than from the tree would have
failed on arrival and been switched off the same day.

WHAT IS DELIBERATELY NOT PINNED, and why it matters more than what is: exact
equality between the canonical artifact and the research log. The artifact is
refreshed by a 20-40 minute backtest while the log's N rises the moment a
register lands, so the two are legitimately unequal for the ordinary interval
between them -- MA19 declined the same check for the same reason, and this file
follows that precedent rather than re-litigating it. The DIRECTIONAL check
below has no such window: the artifact may lag the log, but it must never lead
it, because leading means rows left the log after the artifact counted them.
"""
import json
import os
import ast as _ast
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def git(*args):
    """Run git in the repo; return stdout, or None if git cannot answer."""
    try:
        p = subprocess.run(("git",) + args, cwd=ROOT, capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


HAVE_GIT = git("rev-parse", "--git-dir") is not None


class CanonicalArtifactIsNotStale(unittest.TestCase):
    """`BACKTEST_RESULTS.json`'s trial count vs `RESEARCH_LOG.md`'s.

    The trial count is the denominator of the Deflated Sharpe and of the
    Harvey-Liu-Zhu hurdle, so an artifact counting FEWER trials than the log
    holds is quoting an easier bar than the project has earned. That is the
    tolerable direction only because it is transient. The other direction is
    not transient and is what this pins.
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "BACKTEST_RESULTS.json"),
                  encoding="utf-8") as fh:
            cls.art = json.load(fh)
        from valuation.edge import research_log
        cls.log = research_log.detail()

    def test_the_artifact_never_counts_more_equity_trials_than_the_log_holds(self):
        art_n = self.art["cpcv"]["deflated_sharpe_detail"]["n_trials"]
        log_n = self.log["n_used"]
        self.assertLessEqual(
            art_n, log_n,
            f"BACKTEST_RESULTS.json counts {art_n} equity trials but "
            f"RESEARCH_LOG.md now yields only {log_n}. The artifact may lag "
            "the log (a backtest takes 20-40 minutes); it may never lead it. "
            "Leading means rows left the log after the artifact counted them "
            "-- either a row was edited or removed, or the parser regressed. "
            "Both LOWER N, and lowering N RAISES every DSR- and HLZ-gated "
            "claim, so this fails in the flattering direction.")

    def test_the_artifact_never_counts_more_total_trials_than_the_log_holds(self):
        art_total = self.art["multiple_testing"]["trials_logged_all_domains"]
        log_total = self.log["trials_logged"]
        self.assertLessEqual(
            art_total, log_total,
            f"artifact all-domain trials {art_total} exceeds the log's "
            f"{log_total}. See the equity check for why this direction alone "
            "is a defect.")

    def test_the_comparison_is_reading_real_numbers(self):
        """Vacuity control: both sides must be plausible positive integers.

        A missing key defaulting to 0 would make `<=` pass forever.
        """
        art_n = self.art["cpcv"]["deflated_sharpe_detail"]["n_trials"]
        self.assertIsInstance(art_n, int)
        self.assertGreater(art_n, 50, "artifact trial count implausibly small")
        self.assertGreater(self.log["n_used"], 50, "log N implausibly small")
        self.assertTrue(self.log["available"],
                        "RESEARCH_LOG.md did not parse, so the log side of "
                        "this comparison is a default and proves nothing.")


class LedgerRowsNameRealCommits(unittest.TestCase):
    """A ledger row's commit column is its evidence. Evidence must exist.

    A row reading DONE against a commit that is not in history is
    indistinguishable from a row reading DONE against nothing -- and the ledger
    is, by its own contract rule, the answer to "where do we stand".
    """

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(ROOT, "VALQUO_LEDGER.md"), encoding="utf-8") as fh:
            cls.text = fh.read()
        cls.all_shas = None
        if HAVE_GIT:
            out = git("rev-list", "--all")
            cls.all_shas = set(out.split("\n")) if out else set()

    def _referenced(self):
        """(id, sha-token) for every commit-column entry that looks like a sha."""
        out = []
        for line in self.text.splitlines():
            if not line.startswith("| ") or line.startswith("|---"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 6 or cells[0] in ("id", "ID"):
                continue
            for tok in re.findall(r"\b[0-9a-f]{7,40}\b", cells[5]):
                out.append((cells[0], tok))
        return out

    def test_every_commit_named_by_a_ledger_row_exists(self):
        if not HAVE_GIT:
            self.skipTest("git unavailable — cannot verify commit references")
        refs = self._referenced()
        self.assertGreater(len(refs), 40,
                           "Found almost no commit references; the ledger's "
                           "column layout has probably moved and this check "
                           "is now reading the wrong cell.")
        missing = [(i, s) for i, s in refs
                   if not any(f.startswith(s) for f in self.all_shas)]
        self.assertEqual(
            missing, [],
            "Ledger rows cite commits that are not in this repository's "
            f"history: {missing[:8]}. Either the sha is wrong, or the work "
            "was never pushed — the second is the stranded-work failure "
            "RUN_RULES exists to prevent.")

    def test_the_commit_check_can_actually_fail(self):
        """Positive control: an invented sha must not resolve."""
        if not HAVE_GIT:
            self.skipTest("git unavailable")
        self.assertFalse(any(f.startswith("dead1234beef") for f in self.all_shas))


class NoSuiteAssertsOnAWorkingTreeDiff(unittest.TestCase):
    """A lane-scope check must read its own COMMITS, never the checked-out tree.  [SC-4]

    MEASURED, NOT ANTICIPATED. Two suites shipped the same construction within two days --
    `test_mb18_expectations_gap.py` and `test_mb8_sizing_haircut.py`, each with a
    `test_this_lane_touched_no_live_scoring_path` running `git diff --name-only origin/main --
    <live paths>` and requiring the output to be EMPTY. That compares `origin/main` against
    WHATEVER IS CHECKED OUT, so it does not measure the lane that wrote it at all: it becomes a
    permanent tripwire on whole directories, owned by an item that has already landed, and it
    fires on the next lane to touch one of them. It failed a land gate for an app-fixer change
    to the public research page, which had no relationship to either item.

    TWO COPIES IS A TEMPLATE, NOT AN ACCIDENT, which is why this is a convention rather than
    two repairs.

    IT READS THE SYNTAX TREE, AND THE FIRST CUT DID NOT -- IT GREPPED, AND FAILED AGAINST A
    CORRECT TREE ON ITS OWN POSITIVE CONTROL, whose planted example necessarily contains the
    forbidden text. That is `MA5`'s hurdle sweep firing on its own documentation and
    `MA49(c)`'s fixture firing on the comment describing its repair, met a third time. Stripping
    strings the way `MA5` did is not available here, because the thing being forbidden IS a list
    of string constants -- so the distinction has to be a CALL versus a string that merely
    contains those words, which only the AST can draw.

    THE RULE IS NARROW ON PURPOSE: it forbids a call passing both `diff` and `origin/main`.
    `git show`, `git log`, and a diff between two named commits are all untouched, because
    those read history rather than the working copy.
    """

    @staticmethod
    def _offending_calls(src):
        """Calls that pass both `diff` and `origin/main` as literal arguments."""
        try:
            tree = _ast.parse(src)
        except SyntaxError:                            # pragma: no cover - not a python suite
            return []
        out = []
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.Call):
                continue
            consts = set()
            for sub in _ast.walk(node):
                if isinstance(sub, _ast.Constant) and isinstance(sub.value, str):
                    consts.add(sub.value)
            if "diff" in consts and "origin/main" in consts:
                out.append(getattr(node, "lineno", 0))
        return out

    def _suites(self):
        d = os.path.join(ROOT, "tests")
        return [os.path.join(d, f) for f in sorted(os.listdir(d))
                if f.startswith("test_") and f.endswith(".py")]

    def test_no_suite_diffs_the_working_tree_against_origin_main(self):
        bad = []
        for path in self._suites():
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            if self._offending_calls(src):
                bad.append(os.path.basename(path))
        self.assertEqual(
            bad, [],
            "these suites assert on a working-tree diff against origin/main, which measures "
            "whatever is checked out rather than the lane that wrote them, and becomes a "
            "permanent tripwire for every later lane: %s. Read the commits carrying the "
            "lane's own files instead." % bad)

    def test_the_working_tree_diff_check_can_actually_fail(self):
        """Positive control. The check above passes by finding NOTHING across every suite,
        which is exactly what a broken matcher also returns.

        The example is PARSED rather than searched, which is the whole difference: as a string
        in this file it is prose about the defect, and only parsing it makes it the call the
        rule forbids.
        """
        planted = ('import subprocess\n'
                   'r = subprocess.run(["git", "diff", "--name-only", "origin/main", "--",\n'
                   '                    "valuation/web"], capture_output=True)\n')
        self.assertTrue(self._offending_calls(planted),
                        "the matcher no longer sees the construction it exists to forbid")

    def test_the_check_does_not_fire_on_a_commit_to_commit_diff(self):
        """Reading history is fine; only the working tree is forbidden."""
        ok = ('import subprocess\n'
              'subprocess.run(["git", "diff", "--name-only", "a1b2c3d", "e4f5a6b"])\n')
        self.assertFalse(self._offending_calls(ok),
                         "the rule fires on a legitimate commit-to-commit diff")


class RegistersAreCommittedBlind(unittest.TestCase):
    """A pre-registration committed alongside its own measurement code is not blind.

    MEASURED BEFORE PINNING: 53 of 59 registers on disk were added in a
    markdown-only commit. Six were not, and they are grandfathered BY NAME
    below rather than exempted by a pattern -- grandfathering is not
    exoneration, it is a record that these six cannot support the "strict
    ancestor, committed alone" claim the others can. Several are defensible
    (a calibration re-run using machinery that already existed, a paper-track
    repair that is not a measurement register at all); this test takes no view
    on which, it only stops the list growing silently.
    """

    GRANDFATHERED = {
        "PREREG_free_analysis.md",
        "PREREG_session10_hac_floor.md",
        "PREREG_session11_execution_protocol.md",
        "PREREG_session16_paper_track_repair.md",
        "PREREG_session9_selection_rule.md",
        "PREREG_v1_shadow_vintages.md",
    }

    def test_new_registers_are_added_in_a_markdown_only_commit(self):
        if not HAVE_GIT:
            self.skipTest("git unavailable — cannot inspect commit contents")
        offenders = []
        names = [n for n in sorted(os.listdir(ROOT))
                 if n.startswith("PREREG_") and n.endswith(".md")]
        self.assertGreater(len(names), 20, "registers not found — has the "
                                           "naming convention changed?")
        for name in names:
            if name in self.GRANDFATHERED:
                continue
            sha = (git("log", "--diff-filter=A", "--format=%H", "--", name) or "")
            sha = sha.split("\n")[0]
            if not sha:
                continue        # not yet committed; nothing to judge
            files = [f for f in (git("show", "--pretty=", "--name-only", sha)
                                 or "").split("\n") if f]
            non_md = [f for f in files if not f.endswith(".md")]
            if non_md:
                offenders.append((name, sha[:8], non_md[:3]))
        self.assertEqual(
            offenders, [],
            "A register was committed together with non-markdown files: "
            f"{offenders}. The register must be a strict git ancestor of every "
            "measurement commit, and committing it with code means the "
            "thresholds and the instrument landed together — so nobody can "
            "check the thresholds were fixed first.")

    def test_the_grandfather_list_does_not_name_absent_files(self):
        """A stale exemption silently widens as files are renamed."""
        for name in sorted(self.GRANDFATHERED):
            with self.subTest(name):
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, name)),
                    f"{name} is grandfathered but no longer exists; remove it "
                    "from the list so the exemption cannot outlive the file.")


class SuiteManifest(unittest.TestCase):
    """MA60's second bullet: split product suites from register-pin suites.

    The split itself is derived in `scripts/suite_manifest.py`. The WORKFLOW
    change that would consume it is not in this branch, and deliberately so:
    MA11's land policy refuses any branch touching `.github/`, so this item
    cannot auto-land its own last step, and weakening that policy to let it
    through would be silencing a check to make a run green. What is shipped is
    the judgement -- which suite is which -- so applying it is mechanical.

    MEASURED, AND IT CORRECTS THE AUDIT: 14 of 94 suites are pure register
    pins, not the large tail the item implies. Most closed studies' pin tests
    import a LIVE module too (`fundamental_panel`, `options_tracker`), so they
    really do exercise production code and belong on the land gate.
    """

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        import suite_manifest
        cls.manifest = suite_manifest.classify()

    def test_every_suite_is_classified(self):
        on_disk = {p for p in os.listdir(os.path.join(ROOT, "tests"))
                   if p.startswith("test_") and p.endswith(".py")}
        self.assertEqual(
            on_disk - set(self.manifest), set(),
            "A suite exists that the manifest does not classify, so a gate "
            "split driven by it would silently skip that suite.")

    def test_unclassifiable_suites_default_to_product(self):
        """The safe direction, pinned as a property rather than asserted.

        Running a pin test on a land costs time. NOT running a product test
        costs a broken deploy. So anything ambiguous must land in 'product'.
        """
        self.assertIn("product", set(self.manifest.values()))
        self.assertGreater(
            sum(1 for v in self.manifest.values() if v == "product"),
            sum(1 for v in self.manifest.values() if v == "register-pin"),
            "More suites are classified register-pin than product; the rule "
            "has probably inverted, which would move live coverage off the "
            "land gate.")

    def test_suites_covering_live_code_are_never_register_pinned(self):
        """Spot-check the direction that would actually hurt.

        These three exercise modules the live product reaches. If the rule ever
        classifies one as a nightly pin, the land gate stops covering them.
        """
        for name in ("test_edge.py", "test_screener.py", "test_land_policy.py"):
            with self.subTest(name):
                if name in self.manifest:
                    self.assertEqual(self.manifest[name], "product")


if __name__ == "__main__":
    unittest.main(verbosity=2)
