"""WHY THIRTEEN DECLARED BOOKS COULD NOT BE ARMED — the blockers, pinned as MEASUREMENTS.

A refusal written only in prose rots: the tree moves, the reason stops being true, and nobody
finds out because nothing was checking. These pin the three findings the arming pass turned
up, so that if any of them is ever fixed the corresponding refusal FAILS and gets re-read
instead of quietly outliving its own cause.

  * **F-13's spine cannot answer a forward question** — proved on a SYNTHETIC spine, so the
    claim is structural and does not depend on today's copy of a licensed file.
  * **F-2's "verbatim" prefilter is not what it says it is** — the real constants are read
    from the source and compared against COMMITTED LITERALS (`MA13`'s idiom).
  * **NO LICENSED EXPORT REACHES THE DEPLOYED IMAGE**, which is the blocker behind six books
    at once and is a property of `.dockerignore`, not of any book.

    python tests/test_fleet_triage.py
"""
from __future__ import annotations

import ast
import datetime as dt
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge import event_spine as ES     # noqa: E402


class F13TheSpineIsBackwardOnly(unittest.TestCase):
    """F-13 needs event #2 — a FUTURE earnings date — *"KNOWN from the I-4 spine"*.

    Proved on a spine built by hand rather than on the licensed export, deliberately: a test
    that read `data/bulk/events.csv` would SKIP in the worktree and on CI (the file is
    gitignored and lives only in the primary root), and a refusal resting on a skipped test is
    a refusal resting on nothing.
    """

    def _spine(self):
        return ES.EventSpine({"AAA": ["2026-01-15", "2026-04-16", "2026-07-29"]})

    def test_the_spine_holds_only_dates_it_was_given(self):
        s = self._spine()
        self.assertEqual(s.by_ticker["AAA"][-1], "2026-07-29")

    def test_next_after_the_last_recorded_filing_is_None_not_a_projection(self):
        """THE WHOLE REFUSAL, in one assertion. Asked for the next event after its own last
        record, the spine says it does not know -- correctly. It cannot say anything else,
        because a filing history contains no scheduled dates."""
        s = self._spine()
        self.assertIsNone(s.next_after("AAA", dt.date(2026, 8, 24)))
        self.assertIsNone(s.next_after("AAA", "2026-07-30"))

    def test_it_answers_a_PAST_query_perfectly_well_which_is_what_hid_the_gap(self):
        """`is_known` is True and `next_after` works INSIDE the recorded range. The spine
        answers a different question truthfully, and that is what made the gap invisible to
        every machine check the ceremony could run against a declaration."""
        s = self._spine()
        self.assertTrue(s.is_known("AAA"))
        self.assertEqual(s.next_after("AAA", dt.date(2026, 2, 1)), "2026-04-16")

    def test_f13_is_still_declared_and_its_file_is_unedited(self):
        """The refusal is of the ENTRY RULE. Renaming the declaration back to a draft would
        destroy the `--diff-filter=A` evidence that it predates every line of fleet code."""
        self.assertTrue(os.path.exists(os.path.join(REPO, "DECL_f13_second_event.md")))
        self.assertFalse(os.path.exists(os.path.join(REPO, "DECL_DRAFT_f13_second_event.md")))


class F2ThePrefilterIsNotWhatTheDeclarationSaysItIs(unittest.TestCase):
    """F-2 claims MB1's prefilter *"verbatim"* and then describes a different function.

    The constants are READ FROM THE SOURCE and compared with committed literals. If `build_menu`
    is ever changed to match F-2's parenthetical, these fail and the refusal is re-read --
    which is the point. Nothing here is substring-banned.
    """

    MB1 = os.path.join(REPO, "scripts", "mb1_alternatives_menu.py")

    def _src(self):
        with io.open(self.MB1, encoding="utf-8") as fh:
            return fh.read()

    def test_the_moneyness_bands_are_side_dependent_and_are_not_0_85_to_1_15(self):
        src = self._src()
        # The real line, quoted: `lo, hi = (0.90, 1.20) if right.upper().startswith("C")
        # else (0.80, 1.10)`. Read as a tuple-of-tuples so a reformat does not break it.
        found = set()
        for n in ast.walk(ast.parse(src)):
            if isinstance(n, ast.Tuple) and len(n.elts) == 2:
                vals = [e.value for e in n.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, float)]
                if len(vals) == 2:
                    found.add(tuple(vals))
        self.assertIn((0.90, 1.20), found, "the CALL band")
        self.assertIn((0.80, 1.10), found, "the PUT band")
        self.assertNotIn((0.85, 1.15), found,
                         "F-2's declared band does not appear in the prefilter it cites")

    def test_the_moneyness_filter_carries_a_FALLBACK_so_it_is_not_binding(self):
        """`if len(near) == 0: near = d`. F-2 presents moneyness as a filter; in the shipped
        prefilter it yields entirely rather than empty the set."""
        self.assertIn("near = d", self._src())

    def test_the_dte_band_is_a_FIXED_constant_not_a_band_around_the_hosts_target(self):
        from valuation.edge import options_backtest as OB
        self.assertEqual(OB.DTE_RANGE, (45, 75))
        # It equals +/-25% of 60 by arithmetic, which is presumably where F-2's phrasing came
        # from -- and it is NOT relative to anything. F-11 declares 91 DTE, and 91 is outside
        # this band, so the gate would judge F-11's entry against a menu that cannot contain it.
        self.assertLess(OB.DTE_RANGE[1], 91,
                        "if this ever changes, F-2's tenor objection needs re-reading")

    def test_the_prefilter_requires_a_SOLVABLE_DELTA_which_the_declaration_never_mentions(self):
        """In tension with the books it would host: F-3 and F-11 are moneyness-fixed and F-3's
        void condition is delta-targeted strikes."""
        self.assertIn('dropna(subset=["delta"])', self._src())

    def test_no_book_has_opted_into_any_gate_so_both_gates_are_inert_today(self):
        """The reason F-2's defect is harmless RIGHT NOW, and the reason it was still fixed:
        the opt-in is a one-line amendment somebody will make without re-reading the refusal."""
        import glob
        from valuation.edge import fleet as F
        opted = []
        for fn in glob.glob(os.path.join(REPO, "DECL_*.md")):
            with io.open(fn, encoding="utf-8") as fh:
                p = F.parse_declaration(fh.read())
            if p["ok"] and (p["declaration"].get("gates") or []):
                opted.append(os.path.basename(fn))
        self.assertEqual(opted, [], "a host opted in -- F-2 and F-19 are no longer inert")


class TheLicensedExportsNeverReachTheDeployedImage(unittest.TestCase):
    """THE BLOCKER BEHIND SIX BOOKS AT ONCE, and it belongs to none of them.

    The fleet cycle runs on the Render service -- `PT-WRITER`'s architecture, because only
    that process holds the sandbox token, the network and the records store together. The
    image is built by `COPY . .` under a `.dockerignore` that excludes `data/` WHOLESALE. So
    any entry rule reading a licensed export cannot run where the runner runs, ever, as things
    stand -- and it fails there, not here, which is the worst place to find out.
    """

    def test_dockerignore_excludes_the_whole_data_directory(self):
        with io.open(os.path.join(REPO, ".dockerignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
        self.assertIn("data/", lines)
        self.assertNotIn("!data/", lines, "a negation would reopen the licensed-data rule")

    def test_gitignore_keeps_the_licensed_exports_out_of_the_repo_too(self):
        with io.open(os.path.join(REPO, ".gitignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
        self.assertIn("/data/", lines)

    def test_data_export_IS_shipped_which_is_why_three_books_are_not_blocked_on_this(self):
        """F-6, F-8 and F-20 read `data_export/paper_track_holdings.csv` -- a PUBLISHED
        artifact, tracked in git and not excluded from the image. Their blocker is S3-I3 and
        the paper index book, never this one. The distinction decides which lane fixes what."""
        with io.open(os.path.join(REPO, ".dockerignore"), encoding="utf-8") as fh:
            lines = [ln.strip() for ln in fh if ln.strip() and not ln.strip().startswith("#")]
        self.assertNotIn("data_export/", lines)
        self.assertTrue(os.path.exists(
            os.path.join(REPO, "data_export", "paper_track_holdings.csv")))


if __name__ == "__main__":
    r = unittest.main(exit=False, verbosity=2).result
    raise SystemExit(0 if r.wasSuccessful() else 1)
