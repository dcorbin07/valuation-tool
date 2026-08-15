#!/usr/bin/env python3
"""The documentation a stranger lands on says true things — master audits MA17 and MA22.

MA17 (the bus test) measured that the CODE survives a stranger and the CLAIMS do not: every
suite passes from a clean clone with no `data/` at all, and not one headline number can be
reproduced without a licence that forbids publishing what you derive from it. README named
neither `VALQUO_LEDGER.md` nor `RUN_RULES.md` nor `CLAUDE.md` — zero matches — and told the
reader the point-in-time backtest had not been run, months after it had.

MA22 found the mechanism behind that class of rot: operating instructions had been buried in a
4,100-line findings record prepended to every session, where they aged out of sight. The file
carried THREE different counts of its own test suites — "24", "62", and (measured) 83 — and its
task list self-described as "the least trustworthy section in the file".

So the tests here are about entry points and self-consistency, not prose style. The sharpest one
is `test_no_document_instructs_from_a_hard_coded_suite_count`: a literal that must be
hand-maintained is precisely what produced MA22, and the repair is to derive the number.
"""
import io
import json
import os
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name: str) -> str:
    return io.open(ROOT / name, encoding="utf-8", errors="replace").read()


def flat(text: str) -> str:
    """Collapse whitespace so a phrase can be asserted regardless of where it line-wraps.

    Written after the first cut failed on `"or any\\n> derivation"` -- the doc was correct and
    the assertion was brittle. A prose test that depends on line-wrapping teaches people to
    reflow paragraphs to make the suite green.

    Blockquote markers are stripped too: collapsing whitespace alone left `or any > derivation`,
    so the fix for the wrap introduced a second, subtler version of the same brittleness."""
    unquoted = re.sub(r"(?m)^\s*>+\s?", "", text.lower())
    return re.sub(r"\s+", " ", unquoted)


SUITE_CLAIM = re.compile(r"runs (?:all |every )?(\d+) suites", re.I)


def stale_suite_claims(text: str, actual: int) -> list:
    """Present-tense claims of a specific suite count that disagree with reality.

    QUOTED occurrences are skipped, and that exemption is load-bearing rather than a
    convenience: this project's house style is to correct a stale claim IN PLACE by quoting
    what it used to say, so the record legitimately contains `"runs all 24 suites"` forever.
    A checker without this exemption fires on the correction itself -- it did, on the very
    text written to explain the fix -- and the only way to green it would have been to delete
    the historical record. `test_the_quote_exemption_does_not_blind_the_check` proves the
    exemption is narrow.
    """
    out = []
    for m in SUITE_CLAIM.finditer(text):
        if int(m.group(1)) == actual:
            continue
        line_start = text.rfind("\n", 0, m.start()) + 1
        line_end = text.find("\n", m.end())
        line = text[line_start:line_end if line_end != -1 else len(text)]
        pos = m.start() - line_start
        quotes = [i for i, ch in enumerate(line) if ch in '"“”']
        if quotes and quotes[0] < pos < quotes[-1]:
            continue  # inside a quotation: the record quoting its own stale claim
        out.append(f"claims {m.group(1)} suites, there are {actual}")
    return out


class BusTest(unittest.TestCase):
    """MA17 — can a stranger get from clone to knowing what is true?"""

    def test_start_here_exists_and_is_reachable_from_the_readme(self):
        """A landing page nothing links to is a landing page nobody lands on."""
        self.assertTrue((ROOT / "START_HERE.md").exists(), "START_HERE.md missing")
        readme = read("README.md")
        self.assertIn("START_HERE.md", readme)
        self.assertIn("VALQUO_LEDGER.md", readme,
                      "README must name the contractual answer to 'where do we stand'")

    def test_start_here_takes_the_reader_from_clone_to_green_suites(self):
        body = read("START_HERE.md")
        self.assertIn("git clone", body)
        self.assertIn("tests/test_*.py", body, "it must show how to run the whole gate")
        self.assertIn("requirements.txt", body)

    def test_start_here_states_the_licence_wall_rather_than_implying_reproducibility(self):
        """The honest core of MA17: the numbers are NOT reproducible by a stranger, and the
        reason is a licence, not a missing document. A quick-start that omits this reads as an
        invitation to reproduce and publish figures that may not be published."""
        body = flat(read("START_HERE.md"))
        self.assertIn("sharadar", body)
        self.assertIn("personal-use only", body)
        self.assertIn("any derivation", body)

    def test_start_here_quotes_the_evidence_with_its_own_counter_evidence(self):
        """This project's cardinal rule is not overselling. The headline may appear only
        alongside the bar it FAILS, or the page becomes marketing."""
        body = read("START_HERE.md")
        self.assertIn("+7.17%/yr", body)
        for caveat in ("gross of costs", "one panel"):
            self.assertIn(caveat, body.lower(), f"missing caveat: {caveat}")
        self.assertIn("Harvey", body, "the hurdle the long-short t FAILS must travel with it")

    def test_the_directional_claims_still_match_the_results_artifact(self):
        """Pinned as DIRECTIONS, not decimals, and deliberately so.

        The record already decided this once (`MA19`, declining to source an expectation from
        `BACKTEST_RESULTS.json`): that artifact is refreshed by a 20-40 minute backtest while
        the trial count moves the moment a register lands, so an exact-value pin would be red
        for the ordinary interval between the two -- and "a gate that cries wolf is one you
        learn to ignore". These two booleans flip only when something real changes, and when
        they flip START_HERE.md is genuinely wrong and must be edited."""
        art = ROOT / "BACKTEST_RESULTS.json"
        if not art.exists():
            self.skipTest("BACKTEST_RESULTS.json not present in this tree")
        hlz = json.load(io.open(art, encoding="utf-8")).get("multiple_testing", {}).get("hlz")
        if not hlz:
            self.skipTest("no multiple_testing.hlz block in this artifact")
        self.assertTrue(hlz["clears_x7_calibrated_floor"],
                        "START_HERE.md says the long-short t CLEARS the calibrated floor")
        self.assertFalse(hlz["clears_hlz_hurdle"],
                         "START_HERE.md says it FAILS the Harvey-Liu-Zhu hurdle")

    def test_the_readme_no_longer_says_the_backtest_has_not_been_run(self):
        """It said so for months after the Edge Lab existed -- the single most misleading
        sentence a stranger could read in this repository."""
        readme = read("README.md")
        self.assertNotIn("I have *not* yet run a point-in-time backtest", readme)
        self.assertNotIn("That backtest is the top item on the roadmap", readme)


class OperatingInstructionsAreWhereTheyAreRead(unittest.TestCase):
    """MA22 — the instructions live in the short file that is read first."""

    def test_run_rules_carries_the_operating_instructions(self):
        rr = read("RUN_RULES.md")
        self.assertIn("PART 0", rr)
        for token in ("data/", ".env", "Robinhood", "worktree-", "merge-base"):
            self.assertIn(token, rr, f"PART 0 must carry the hard rule / handoff mentioning {token}")

    def test_run_rules_is_still_short_enough_to_be_read(self):
        """Its own first line is 'Short on purpose. A long checklist gets ignored.' Moving the
        operating sections in must not turn it into the thing it warns about."""
        n = len(read("RUN_RULES.md").splitlines())
        self.assertLess(n, 320, f"RUN_RULES.md is {n} lines; it is supposed to be short")

    def test_claude_md_points_at_the_ledger_instead_of_carrying_a_task_list(self):
        """The deleted section's own header called it 'the least trustworthy section in the
        file', and two of the three OPEN items checked against the tree were already closed."""
        brief = read("CLAUDE.md")
        self.assertNotIn("## IMMEDIATE NEXT TASKS", brief)
        self.assertIn("VALQUO_LEDGER.md", brief)
        self.assertIn("RUN_RULES.md", brief)

    def test_claude_md_keeps_the_findings_record(self):
        """MA22 is explicitly NOT a rewrite: 'the findings record is load-bearing and should not
        be trimmed'. If this ever fails, someone has trimmed the wrong half."""
        brief = read("CLAUDE.md")
        self.assertIn("## CURRENT STATE", brief)
        self.assertGreater(len(brief), 250_000,
                           "the findings record appears to have been trimmed, not the task list")

    def test_no_document_instructs_from_a_hard_coded_suite_count(self):
        """THE ANTI-ROT PIN, and the direct repair of MA22's finding.

        Three different suite counts lived in one file because each was typed by hand and none
        was checked. So the instruction must DERIVE the number. Historical corrections may of
        course still quote the stale figures -- that is the record doing its job -- which is why
        this checks the imperative form ('runs all N suites'), not any occurrence of a number."""
        actual = len(list((ROOT / "tests").glob("test_*.py")))
        self.assertGreater(actual, 50, "sanity: the suite glob found almost nothing")

        offenders = []
        for name in ("CLAUDE.md", "RUN_RULES.md", "START_HERE.md", "README.md"):
            offenders += [f"{name}: {c}" for c in stale_suite_claims(read(name), actual)]
        self.assertEqual(offenders, [], "; ".join(offenders))

        rr = read("RUN_RULES.md")
        self.assertIn("ls tests/test_*.py | wc -l", rr,
                      "PART 0 must show how to COUNT the suites rather than quoting a number")

    def test_the_quote_exemption_does_not_blind_the_check(self):
        """Positive control, and it is the one that matters -- the exemption above is exactly
        the kind of carve-out that quietly turns a check off.

        The stale sentence that really was in CLAUDE.md must still be caught when written as
        an INSTRUCTION, and skipped only when the record is quoting it."""
        instruction = "The Action installs deps and runs all 24 suites, so allow time."
        quoting_it = 'the git-handoff text said the Action "runs all 24 suites" while line 26'

        self.assertEqual(stale_suite_claims(instruction, 86),
                         ["claims 24 suites, there are 86"],
                         "an unquoted stale instruction must still be caught")
        self.assertEqual(stale_suite_claims(quoting_it, 86), [],
                         "the record quoting its own stale claim is not an offence")
        self.assertEqual(stale_suite_claims(instruction, 24), [],
                         "a claim that matches reality is not an offence")


if __name__ == "__main__":
    unittest.main(verbosity=2)
