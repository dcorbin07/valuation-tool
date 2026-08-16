"""
The public-facing documents must stay true. Run:

    python tests/test_public_docs.py

The repository went public on 2026-08-16. Before that, a stale README cost a
reader some confusion; after it, a stale README is a false public claim about a
financial product. The accuracy pass that day found the README describing a
project three months and three audits out of date -- it stated "I have not yet
run a point-in-time backtest" months after 224 pre-registered equity trials,
was silent on four of the five product surfaces, and linked to a sibling
repository that does not exist.

THE NUMBERS BELOW ARE DERIVED FROM THE ARTIFACT, NOT HARD-CODED. A test that
pinned literals would have to be edited every time the panel is re-run, and
would then be edited to whatever the new number was -- which is not a check.
These read `BACKTEST_RESULTS.json` and assert the README agrees with it, so the
README cannot drift away from the record without failing.
"""
import io
import json
import os
import re
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def read(name):
    with io.open(os.path.join(ROOT, name), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def flat(text):
    """Collapse wrapping so a claim split across lines is still findable."""
    return re.sub(r"\s+", " ", re.sub(r"(?m)^\s*>+\s?", "", text))


class HeadlineNumbersMatchTheArtifact(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.readme = flat(read("README.md"))
        cls.start = flat(read("START_HERE.md"))
        with io.open(os.path.join(ROOT, "BACKTEST_RESULTS.json"),
                     encoding="utf-8") as fh:
            cls.art = json.load(fh)

    def test_top_decile_alpha_matches(self):
        alpha = self.art["construction"]["top_decile_alpha"]
        want = "+%.2f%%/yr" % (alpha * 100)
        self.assertIn(want, self.readme,
                      f"README must quote the artifact's top-decile alpha ({want})")

    def test_the_long_short_t_and_both_bars_match(self):
        hlz = self.art["multiple_testing"]["hlz"]
        for label, value, places in (
                ("long-short HAC t", hlz["value"], 2),
                ("HLZ hurdle", hlz["hurdle_sqrt_2_ln_N"], 2),
                ("X7 calibrated floor", hlz["x7_calibrated_floor"], 4)):
            with self.subTest(label):
                self.assertIn(f"{value:.{places}f}", self.readme,
                              f"README must quote {label} = {value:.{places}f}")

    def test_the_readme_states_both_sides_of_the_tension(self):
        """Clearing one bar and failing the other must travel together.

        Quoting only the cleared bar overstates the result; quoting only the
        failed one understates it. The artifact ships both and so must the
        README.
        """
        hlz = self.art["multiple_testing"]["hlz"]
        self.assertTrue(hlz["clears_x7_calibrated_floor"])
        self.assertFalse(hlz["clears_hlz_hurdle"])
        low = self.readme.lower()
        self.assertIn("harvey", low, "the failed bar must be named")
        self.assertTrue(
            "calibrated floor" in low or "calibrated" in low,
            "the cleared bar must be named")

    def test_trial_count_matches_the_research_log(self):
        n = self.art["multiple_testing"]["hlz"]["n_trials_equity"]
        self.assertIn(str(n), self.readme,
                      f"README must quote the equity trial count ({n})")

    def test_universe_shape_matches(self):
        u = self.art["universe"]
        self.assertIn(f"{u['n_names']:,}", self.readme)
        self.assertIn(str(u["n_dates"]), self.readme)

    def test_the_artifact_side_is_real(self):
        """Vacuity control: these assertions are worthless on a stub artifact."""
        self.assertEqual(self.art["universe"]["label"], "full")
        self.assertGreater(self.art["multiple_testing"]["hlz"]["n_trials_equity"], 50)


class NothingPrivateOrBrokenIsPublished(unittest.TestCase):

    PUBLIC = ("README.md", "START_HERE.md", "DATA_AND_METHODS.md")

    def test_no_public_doc_names_the_separate_business_or_its_owner_details(self):
        """The launch checklists were untracked on 2026-08-16.

        They carried a separate LLC, entity structuring and a securities-law
        posture -- private business planning, not project documentation. This
        stops the same material reappearing in a doc a visitor reads first.
        """
        banned = ("on the steps", "mason school", "william & mary")
        for name in self.PUBLIC:
            low = read(name).lower()
            for phrase in banned:
                with self.subTest(f"{name}:{phrase}"):
                    self.assertNotIn(phrase, low)

    def test_the_banned_phrase_check_can_actually_fail(self):
        """Positive control -- otherwise an empty banned list would pass."""
        self.assertIn("valquo", read("README.md").lower())

    def test_launch_checklists_are_not_tracked(self):
        try:
            out = subprocess.run(("git", "ls-files"), cwd=ROOT,
                                 capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            self.skipTest("git unavailable")
        if out.returncode != 0:
            self.skipTest("git ls-files failed")
        tracked = set(out.stdout.split())
        for name in ("LAUNCH_CHECKLIST.md", "GO_LIVE.md"):
            with self.subTest(name):
                self.assertNotIn(name, tracked,
                                 f"{name} is internal business planning and was "
                                 "untracked when the repo went public.")

    def test_no_broken_sibling_directory_links(self):
        """`../screener` named a repository that does not exist.

        Relative links out of the repo root do not resolve for a visitor on
        GitHub. Sibling projects must be absolute URLs.
        """
        for name in self.PUBLIC:
            text = read(name)
            for bad in re.findall(r"\]\(\.\./[^)]*\)", text):
                self.fail(f"{name} contains a relative sibling link {bad}; "
                          "use an absolute URL")


class TheLicenceLimitIsStated(unittest.TestCase):
    """A stranger must learn they cannot publish what they derive.

    Sharadar's terms are personal-use only and forbid commercial use of the
    data "or any derivation" (ledger row D1). A public repo quoting headline
    figures without that sentence invites exactly the misuse it forbids.
    """

    def test_readme_states_the_sharadar_limit(self):
        low = flat(read("README.md")).lower()
        self.assertIn("sharadar", low)
        self.assertIn("any derivation", low,
                      "the README must quote the licence's own words")

    def test_readme_says_the_research_data_is_not_published(self):
        low = flat(read("README.md")).lower()
        self.assertTrue(
            "gitignored" in low or "never published" in low,
            "the README must say the licensed exports are not in the repo")

    def test_start_here_still_carries_it_too(self):
        low = flat(read("START_HERE.md")).lower()
        self.assertIn("any derivation", low)


class EveryProductSurfaceIsDescribed(unittest.TestCase):
    """MA17's bus test, applied to the product rather than the code.

    A visitor must be able to learn what Valquo is now -- and, more
    importantly, which surfaces carry a measured claim and which are screens.
    """

    SURFACES = ("valuation engine", "screener", "valquo index",
                "dip detector", "options")

    def test_all_five_surfaces_appear(self):
        low = flat(read("README.md")).lower()
        for s in self.SURFACES:
            with self.subTest(s):
                self.assertIn(s, low)

    def test_the_readme_says_the_options_entry_signal_does_not_work(self):
        """The single most misleadable surface, so it is pinned explicitly."""
        low = flat(read("README.md")).lower()
        self.assertTrue(
            "does not work" in low or "loses" in low or "subtracts value" in low,
            "the README must state plainly that the options entry signal is "
            "measured and negative -- R2 found it loses to random entry.")

    def test_the_paper_track_is_labelled_paper_and_undecided(self):
        low = flat(read("README.md")).lower()
        self.assertIn("paper", low)
        self.assertIn("2031", low,
                      "the verdict date must be stated so no earlier reading "
                      "is mistaken for a verdict")

    def test_the_forward_track_dates_match_the_derived_vintage(self):
        """Never quote a vintage date -- derive it. It moves on ordinary work days.

        The record shows the gate date wrong in three separate documents at
        once because each had quoted a literal.
        """
        try:
            from valuation.edge import track_meter
        except Exception:                       # pragma: no cover
            self.skipTest("track_meter unavailable")
        d = track_meter.detail()
        readme = flat(read("README.md"))
        for key in ("operational_gate_date", "verdict_date"):
            val = d.get(key)
            if val:
                with self.subTest(key):
                    self.assertIn(str(val), readme,
                                  f"README must quote the DERIVED {key} "
                                  f"({val}), not a literal that will rot.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
