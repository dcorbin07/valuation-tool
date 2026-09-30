"""AUDIT 6 (2026-09-29) — two ignore files, two classes of file that went the wrong way.

`.dockerignore` excluded every `*.md`, and four of them are opened by DEPLOYED code at request
time, package-relative, so on valquo.co the trial count on /proof fell back to the stale
artifact (224 against a live 248), /work/research rendered "0 entries", and /api/index-track
reported the contract "not readable". `.gitignore` ignored `*.db` and not SQLite's sidecars,
so `git_push.bat`'s `git add -A` committed `.scan-cache/screener.db-shm` and `-wal` to the
public repository on 2026-09-28.

Both are probed the way `test_fleet_highwater.py` probes the image: by applying the file's own
patterns to a path, never by reading a comment.

Run: python tests/test_ignore_rules_audit6.py
"""
from __future__ import annotations

import fnmatch
import io
import os
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _patterns(name):
    out = []
    with io.open(os.path.join(REPO, name), encoding="utf-8") as fh:
        for line in fh:
            t = line.strip()
            if t and not t.startswith("#"):
                out.append(t)
    return out


def _excluded(patterns, rel):
    """Last matching pattern wins; a leading `!` re-includes. Same reading as the image test."""
    parts = rel.replace("\\", "/").split("/")
    out = False
    for pat in patterns:
        neg = pat.startswith("!")
        body = (pat[1:] if neg else pat).rstrip("/").lstrip("/")
        hit = any(fnmatch.fnmatch(c, body) for c in parts) or \
            fnmatch.fnmatch(rel.replace("\\", "/"), body)
        if hit:
            out = not neg
    return out


class TheImageShipsTheRecordItReads(unittest.TestCase):
    """Every markdown file a deployed module opens must survive `.dockerignore`."""

    READ_AT_REQUEST_TIME = (
        "RESEARCH_LOG.md",              # research_log.detail(): live N, HLZ hurdle, /work/research
        "PAPER_TRACK_CONTRACT.md",      # index_track.gate_state(): the operational gate
        "VALQUO_EXTENSIONS.md",         # research_record.registers()
        "PREREG_free_analysis.md",      # research_record.registers(): the PREREG_*.md glob
    )

    def setUp(self):
        self.pats = _patterns(".dockerignore")

    def test_the_four_record_files_are_re_included(self):
        for rel in self.READ_AT_REQUEST_TIME:
            self.assertFalse(_excluded(self.pats, rel), "%s is kept out of the image" % rel)

    def test_the_files_actually_exist_so_the_negation_is_not_decorative(self):
        for rel in self.READ_AT_REQUEST_TIME:
            self.assertTrue(os.path.exists(os.path.join(REPO, rel)), rel)

    def test_the_deployed_code_really_opens_them_package_relative(self):
        """The reason these four and not others: the code resolves them from __file__."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "research_log.py"),
                      encoding="utf-8").read()
        self.assertIn('"RESEARCH_LOG.md"', src)
        src = io.open(os.path.join(REPO, "valuation", "screener", "index_track.py"),
                      encoding="utf-8").read()
        self.assertIn("PAPER_TRACK_CONTRACT.md", src)
        src = io.open(os.path.join(REPO, "valuation", "web", "research_record.py"),
                      encoding="utf-8").read()
        self.assertIn('"PREREG_*.md"', src)
        self.assertIn('"VALQUO_EXTENSIONS.md"', src)

    def test_the_rest_of_the_markdown_still_stays_out(self):
        """The exclusion is narrow: handoffs, the brief and the audits do not ship."""
        for rel in ("CLAUDE.md", "HANDOFF_STATUS.md", "HANDOFF_edge_audit.md",
                    "VALQUO_MASTER_AUDIT_5.md", "RUN_RULES.md", "VALQUO_LEDGER.md"):
            self.assertTrue(_excluded(self.pats, rel), "%s would now ship" % rel)

    def test_data_stays_out_wholesale(self):
        """SECURITY_AUDIT L5 is untouched: the licensed exports never enter a build context."""
        self.assertIn("data/", self.pats)
        self.assertTrue(_excluded(self.pats, "data/backtest_freeze_2026-08/bulk/sep.csv"))


class TheRepoIgnoresSqliteSidecars(unittest.TestCase):
    def setUp(self):
        self.pats = _patterns(".gitignore")

    def test_every_sidecar_a_sqlite_database_can_leave_behind_is_ignored(self):
        for rel in (".scan-cache/screener.db-shm", ".scan-cache/screener.db-wal",
                    "data/app.db-journal", "anywhere/x.db"):
            self.assertTrue(_excluded(self.pats, rel), "%s would be committed by add -A" % rel)

    def test_the_mounts_ghost_files_are_ignored(self):
        self.assertTrue(_excluded(self.pats, ".scan-cache/.fuse_hidden0000001200000001"))

    def test_the_two_sidecars_are_no_longer_tracked(self):
        """The rule alone does not untrack a file git already holds (its own docstring says so
        of `valuation/data/`). Checked through git when git is available, so a checkout that
        re-added them fails here rather than on the public remote."""
        import subprocess
        try:
            out = subprocess.run(["git", "ls-files", ".scan-cache"], cwd=REPO,
                                 capture_output=True, text=True, timeout=30)
        except Exception:                                               # noqa: BLE001
            self.skipTest("git not available here")
        if out.returncode != 0:
            self.skipTest("not a git checkout: " + (out.stderr or "").strip()[:80])
        tracked = [ln for ln in out.stdout.splitlines() if ln.strip()]
        self.assertEqual(tracked, [], "SQLite sidecars are tracked: %r" % tracked)


if __name__ == "__main__":
    unittest.main(verbosity=1)
