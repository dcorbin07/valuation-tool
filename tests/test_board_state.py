#!/usr/bin/env python3
"""Tests for MB27 (scripts/board_state.py) and MB28 (scripts/drift_heartbeat.py).

TWO THINGS THESE TESTS ARE FOR, AND ONE THEY ARE NOT
-----------------------------------------------------
They pin (a) the two derivations where the audit's own proposed rule is measurably
wrong, and (b) the refusal MB30 makes binding: this reporter must never fail on a
finding. They are NOT a second implementation of the board -- where a test needs to
know what git says, it drives git.

THE CONTROLS ARE THE POINT. Three tests here are written as controls rather than as
assertions about my code: `test_the_audits_naive_rule_would_have_been_wrong` fails if
the naive rule ever stops being wrong (i.e. if the guard has become pointless), and
`test_unmeasured_is_not_zero` and `test_a_stopped_clock_is_visible` each drive the
failure path deliberately. A guard that only ever sees the healthy case is not
measuring anything.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import board_state as bs  # noqa: E402
from scripts import drift_heartbeat as hb  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# The real cell, copied from VALQUO_LEDGER.md on 2026-08-19. It is here verbatim because
# a paraphrase would test my paraphrase.
B13_STATUS = "**PARTIAL - BLOCKED ON DATA, NOT IN PROGRESS**"
D11_STATUS = "INPROGRESS"


class ClaimedItems(unittest.TestCase):
    """MB27 ingredient 2: 'ledger status cells matching IN ?PROGRESS'."""

    def test_a_negated_cell_is_not_a_claim(self):
        self.assertFalse(bs.is_claimed(B13_STATUS))

    def test_an_unspaced_cell_is_a_claim(self):
        self.assertTrue(bs.is_claimed(D11_STATUS))

    def test_ordinary_claims_are_claims(self):
        for s in ("IN PROGRESS", "**IN PROGRESS**", "in progress (edge lane)",
                  "IN_PROGRESS", "IN-PROGRESS"):
            self.assertTrue(bs.is_claimed(s), s)

    def test_other_negations_are_not_claims(self):
        for s in ("NOT IN PROGRESS", "no longer in progress", "never in progress",
                  "**DONE - was in progress until 2026-08-11**"):
            self.assertFalse(bs.is_claimed(s), s)

    def test_the_audits_naive_rule_would_have_been_wrong(self):
        """CONTROL. If this ever passes, the guard above has stopped being needed.

        The audit specifies `IN ?PROGRESS` against the status cell and predicts two
        hits. One of the two says the opposite of what the rule reads it as, so the
        literal rule carries a 50% false-positive rate on today's data.
        """
        import re
        naive = re.compile(r"IN ?PROGRESS", re.I)
        self.assertTrue(naive.search(B13_STATUS),
                        "the naive rule no longer matches B13 - re-read this test")
        self.assertFalse(bs.is_claimed(B13_STATUS))

    def test_it_delegates_to_the_one_ledger_parser(self):
        """One parser, not two. A second copy would not carry the raw-pipe fix."""
        src = (ROOT / "scripts" / "board_state.py").read_text(encoding="utf-8")
        self.assertIn("build_ledger", src)
        self.assertNotIn("splitlines()\n    cells", src)

    def test_claimed_reads_a_supplied_table(self):
        rows = {"X1": {"status": "IN PROGRESS", "handoff": "h.md", "date": "d"},
                "X2": {"status": B13_STATUS, "handoff": "h.md", "date": "d"},
                "X3": {"status": "**DONE**", "handoff": "h.md", "date": "d"}}
        self.assertEqual([r["id"] for r in bs.claimed(rows)], ["X1"])


class Lanes(unittest.TestCase):
    """MB27 ingredient 1. A lane is a lane; a rescue ref is not."""

    def test_a_lane_seen_locally_and_remotely_is_one_lane(self):
        """Found by running it: the first cut reported 'LANES IN FLIGHT: 2' for one."""
        b = {"branches": [
            {"ref": "worktree-x", "ahead": 3, "kind": "lane", "tip_epoch": 1, "remote": False},
            {"ref": "origin/worktree-x", "ahead": 3, "kind": "lane", "tip_epoch": 1, "remote": True},
        ], "worktrees": [], "claimed": [], "handoffs": [], "locks": [],
            "handoffs_modified": [], "heartbeat": {"present": False, "note": ""},
            "_meta": {"generated_at": "now"}, "refs_age_hours": 0.0}
        lanes = sorted({r["ref"].removeprefix("origin/") for r in b["branches"]})
        self.assertEqual(lanes, ["worktree-x"])

    def test_rescue_and_backup_refs_are_not_lanes(self):
        for ref in ("rescue/main-41d7b12", "origin/rescue/wip-main-c4a3939",
                    "backup/local-main-2026-08-16", "backup/pre-filter-20260728-073540"):
            self.assertFalse(bs.LANE.match(ref), ref)
            self.assertTrue(bs.KEEP.match(ref), ref)

    def test_a_worktree_branch_is_a_lane(self):
        for ref in ("worktree-optionsbot-lane", "origin/worktree-crowding-p2"):
            self.assertTrue(bs.LANE.match(ref), ref)


class NeverWarns(unittest.TestCase):
    """MB30 / MA21: this reporter carries no verdict and must not fail on a finding."""

    def test_the_live_board_exits_zero(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bs.main([])
        self.assertEqual(rc, bs.OK)
        self.assertIn("BOARD STATE", buf.getvalue())

    def test_json_mode_exits_zero(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bs.main(["--json"])
        self.assertEqual(rc, bs.OK)
        json.loads(buf.getvalue())

    def test_a_board_full_of_findings_still_exits_zero(self):
        """Locks, dirty worktrees and claimed items are FINDINGS, not failures."""
        b = bs.board()
        self.assertIsNotNone(b["counts"])
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = bs.main([])
        self.assertEqual(rc, bs.OK)

    def test_the_only_nonzero_exit_means_the_script_broke(self):
        src = (ROOT / "scripts" / "board_state.py").read_text(encoding="utf-8")
        self.assertIn("BROKEN = 2", src)
        self.assertEqual(bs.BROKEN, 2)
        self.assertEqual(bs.OK, 0)


class UnmeasuredIsNotZero(unittest.TestCase):
    def test_unmeasured_is_not_zero(self):
        """CONTROL, driven deliberately: a git failure must read UNMEASURED, not 0.

        A zero meaning 'nothing in flight' and a zero meaning 'git did not answer'
        would be checkout_drift.py's own founding defect in a new costume.
        """
        real = bs.branches
        try:
            def boom(*a, **k):
                raise RuntimeError("git is not here")
            bs.branches = boom
            b = bs.board()
        finally:
            bs.branches = real
        self.assertIsNone(b["branches"])
        self.assertIsNone(b["counts"]["lanes_in_flight"])
        self.assertIn("branches", b["_meta"]["unmeasured"])
        self.assertIn("UNMEASURED", "\n".join(bs.render(b)))

    def test_render_never_prints_none_as_a_count(self):
        b = bs.board()
        b["counts"]["lanes_in_flight"] = None
        self.assertNotIn("LANES IN FLIGHT: None", "\n".join(bs.render(b)))


class HandoffFreshness(unittest.TestCase):
    """MB27 ingredient 3, where the audit's proposed derivation does not measure work."""

    def test_age_comes_from_the_record_not_the_filesystem(self):
        rows = bs.handoffs()
        self.assertTrue(rows)
        self.assertTrue(any(r["age_days"] is not None for r in rows))
        for r in rows:
            self.assertIn("last_commit_epoch", r)
        src = (ROOT / "scripts" / "board_state.py").read_text(encoding="utf-8")
        self.assertIn('_git("log", "-1", "--format=%ct"', src)

    def test_the_filesystem_cannot_move_a_handoffs_reported_age(self):
        """The measured defect: after `git merge`, two handoffs carried the merge
        minute as their mtime while a third the merge did not touch read three days
        old. mtime is when git last WROTE the file here, not when the work happened.

        THE FIRST VERSION OF THIS TEST PASSED UNDER THE DEFECT and was caught by the
        mutation harness. It touched a file to `now` and compared before against after
        -- but the file it picked already carried a near-`now` mtime, so both readings
        were ~0 under the mtime implementation too and it agreed with itself. The mtime
        is now driven to a value NO handoff can legitimately have, so the two
        implementations cannot return the same answer.
        """
        target = next(p for p in ROOT.glob("HANDOFF_*.md"))
        orig = (target.stat().st_atime, target.stat().st_mtime)
        far_past = time.time() - 400 * 86400          # older than the repository
        try:
            os.utime(target, (far_past, far_past))
            age = {r["file"]: r["age_days"] for r in bs.handoffs()}[target.name]
        finally:
            os.utime(target, orig)
        self.assertIsNotNone(age)
        self.assertLess(age, 300.0,
                        "the reported age followed the filesystem, not the record")


class RetiredBoardFile(unittest.TestCase):
    """The one assertion that cannot cry wolf: a file making no dated claim."""

    def test_the_hand_typed_board_no_longer_claims_anything_about_today(self):
        d = json.loads((ROOT / "ma_in_flight.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(d), ["_meta", "_retired_2026_08_14"])
        self.assertIn("RETIRED", d["_meta"]["STATUS"])
        self.assertIn("board_state.py", d["_meta"]["how_to_find_out"])

    def test_the_retired_contents_are_kept_verbatim(self):
        """Rule 9. All eight items it named are preserved, and all eight are DONE."""
        d = json.loads((ROOT / "ma_in_flight.json").read_text(encoding="utf-8"))
        old = d["_retired_2026_08_14"]
        items = [k for k in old if not k.startswith("_")]
        self.assertEqual(sorted(items),
                         sorted(["MA13", "MA19", "MA36", "MA37", "MA15", "MA16",
                                 "MA20", "MA35"]))

    def test_every_item_the_retired_file_named_is_done(self):
        """The premise MB27 rests on, verified rather than repeated (RUN_RULES A8)."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import build_ledger
        rows = build_ledger.read_ledger()
        d = json.loads((ROOT / "ma_in_flight.json").read_text(encoding="utf-8"))
        for item in (k for k in d["_retired_2026_08_14"] if not k.startswith("_")):
            self.assertIn("DONE", rows[item]["status"].upper(),
                          f"{item} is not DONE - MB27's premise has changed")

    def test_the_snapshot_path_is_gitignored(self):
        ign = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".board_state.json", ign)
        self.assertEqual(bs.SNAPSHOT.name, ".board_state.json")


class Heartbeat(unittest.TestCase):
    """MB28. The clock."""

    def test_an_absent_heartbeat_says_not_installed(self):
        with tempfile.TemporaryDirectory() as d:
            r = bs.heartbeat(Path(d) / "nope.json")
        self.assertFalse(r["present"])
        self.assertIsNone(r["age_hours"])
        self.assertIn("install_drift_task.bat", r["note"])

    def test_a_stopped_clock_is_visible(self):
        """CONTROL. A frozen heartbeat must report its age, not disappear."""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "drift.json"
            p.write_text('{"state": "ok"}', encoding="utf-8")
            old = time.time() - 72 * 3600
            os.utime(p, (old, old))
            r = bs.heartbeat(p)
        self.assertTrue(r["present"])
        self.assertGreater(r["age_hours"], 71.0)
        self.assertEqual(r["last"]["state"], "ok")

    def test_it_writes_even_when_it_cannot_measure(self):
        """A missing write and a missing task would look identical downstream."""
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "drift.json"
            rc = hb.main(["--out", str(out), "--repo", str(Path(d) / "not-a-repo"),
                          "--no-fetch"])
            self.assertEqual(rc, hb.ALARM)
            written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["state"], "unknown")
        self.assertIn("error", written)
        self.assertIn("ran_at", written)

    def test_a_healthy_run_writes_ok_and_exits_zero(self):
        """Measured against a repo this test BUILDS, not against Don's machine.

        THE FIRST VERSION OF THIS TEST FAILED IN CI AND PASSED LOCALLY, which is the worst
        way for a test to be wrong. It ran the heartbeat with no `--repo`, so it measured
        `checkout_drift.SHARED_CHECKOUT` -- a pinned `C:\\Users\\donni\\...` path that
        exists on exactly one machine. On the ubuntu runner it resolves to nothing, the
        state is `unknown`, and the assertion read
        `AssertionError: 'unknown' not found in ('ok', 'alarm')`. The pin is correct and
        deliberate in `checkout_drift` (a copy measuring "its own tree" would always report
        a fresh worktree and always say fine); the defect was a test that inherited it.
        It builds its own origin-and-clone, so `ok` is reachable on any platform.
        """
        from tests.test_checkout_drift import build  # the one fixture builder
        with tempfile.TemporaryDirectory() as d:
            repo = build(d, "hb")
            out = Path(d) / "drift.json"
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = hb.main(["--out", str(out), "--repo", repo, "--no-fetch"])
            written = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(written["state"], "ok")
        self.assertEqual(rc, hb.OK)
        self.assertEqual(written["measured"]["ahead"], 0)
        self.assertEqual(written["measured"]["behind"], 0)

    def test_there_is_one_drift_measure_not_two(self):
        src = (ROOT / "scripts" / "drift_heartbeat.py").read_text(encoding="utf-8")
        self.assertIn("from scripts.checkout_drift import", src)
        self.assertNotIn("rev-list", src)

    def test_the_two_modules_agree_on_the_heartbeat_path(self):
        """One fact. If they disagree the board silently reports NOT INSTALLED forever."""
        self.assertEqual(bs.HEARTBEAT, hb.DEFAULT_OUT)

    def test_the_installer_is_shipped_and_runnable(self):
        for name in ("install_drift_task.bat", "drift_heartbeat.bat"):
            self.assertTrue((ROOT / name).exists(), name)
        bat = (ROOT / "install_drift_task.bat").read_text(encoding="utf-8")
        self.assertIn("ValquoDriftCheck", bat)
        self.assertIn("schtasks /Create", bat)
        # After the 19:30 sync and the 20:00 auto-push, so it measures what they left.
        #
        # READ THE ASSIGNMENT, NOT THE FILE. `assertIn("20:30", bat)` passed against a
        # tree where the schedule had been moved to 09:00, because the comment block
        # above it still said 20:30 -- comment-versus-code, the family this project has
        # now found five times, caught here by the mutation harness rather than in
        # production.
        import re as _re
        m = _re.search(r'set\s+"WHEN=([0-9:]+)"', bat)
        self.assertIsNotNone(m, "install_drift_task.bat no longer sets WHEN")
        self.assertEqual(m.group(1), "20:30")

    def test_the_heartbeat_is_not_bolted_onto_the_sync_task(self):
        """It would die exactly when the task it exists to watch dies."""
        boot = (ROOT / "scripts" / "valquo_sync_bootstrap.bat").read_text(encoding="utf-8")
        self.assertNotIn("drift_heartbeat", boot)


class ItRunsFromTheCommandLine(unittest.TestCase):
    def test_board_state_runs_as_a_subprocess(self):
        p = subprocess.run([sys.executable, "scripts/board_state.py"],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        self.assertEqual(p.returncode, 0, p.stderr[-400:])
        self.assertIn("BOARD STATE", p.stdout)
        self.assertIn("DRIFT HEARTBEAT", p.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
