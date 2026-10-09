# -*- coding: utf-8 -*-
"""The proposed `themes` / `themes-assemble` jobs: every job must name its own schedule.

WHY A TEST FOR TEXT NOBODY HAS PASTED YET. The auto-land policy REFUSES any branch touching
`.github/`, so an agent cannot ship a workflow change — Don pastes it by hand. That makes the
proposed YAML a deliverable that reaches production without ever passing through CI, which is
the one kind of deliverable this repo cannot otherwise check. So the text is tracked in
`PROPOSAL_auto_scan_themes.md` and parsed here.

THE DEFECT THIS EXISTS FOR, and it is why the rule is worth enforcing mechanically rather than
by review. Session 70's `themes-assemble` read:

    if: ${{ always() && (github.event_name == 'schedule' || github.event.inputs.kind == 'themes') }}

`github.event_name == 'schedule'` is true for EVERY cron in the file — 76 scheduled events a
week once the themes cron is added — and `always()` makes the job run even when `themes` is
skipped. It would have re-crawled SEC for 1,500 names 75 times a week, timing out each time.
Every other job in that file already names its own schedule, 5 of 5; this is that house rule,
written down.

THE RULE IS ENFORCED ON BOTH FILES. On the proposal, so the text is right before it is pasted;
on the committed workflow, so it stays right afterwards and a future job cannot quietly
reintroduce the shape.
"""
from __future__ import annotations

import io
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROPOSAL = os.path.join(REPO, "PROPOSAL_auto_scan_themes.md")
WORKFLOW = os.path.join(REPO, ".github", "workflows", "auto-scan.yml")

sys.path.insert(0, REPO)
from scripts import workflow_source as WS  # noqa: E402


def _authoritative(name: str = "auto-scan.yml") -> str:
    """The workflow text as the ref that RUNS it has it -- not this checkout's copy.

    ITEM 44. Item 42 reported `auto-scan.yml` had no `53 17-19` cron; it had carried it since
    `d66155e`, and the lane was reading its own worktree, branched before that commit. **The
    land gate refuses any branch touching `.github/`, so a workflow can only change on main,
    which makes a lane's copy stale BY CONSTRUCTION rather than by accident** -- and a guard
    asserting a house rule against a stale copy passes while main's copy breaks it.

    On a CI runner `origin/main` is often not fetched, and there the local file is correct: the
    gate tests the MERGE of the branch into main, so the checkout already is main's copy plus
    the branch. `workflow_source.read` reports which one it gave us either way, and the test
    below pins that it never claims authority it does not have.
    """
    return WS.read(name)["text"]

#: The cron the proposal adds, and the dispatch kind that goes with it.
THEMES_CRON = "17 7 * * 0"
THEMES_KIND = "themes"


def _read(path: str) -> str:
    return io.open(path, encoding="utf-8").read()


def _fenced_yaml(md: str) -> list:
    """Every ```yaml block in the proposal, in order."""
    return re.findall(r"```yaml\n(.*?)```", md, re.S)


def _jobs_block(md: str) -> str:
    """The fenced block that defines jobs — the one carrying `themes:` at two-space indent."""
    for b in _fenced_yaml(md):
        if re.search(r"^  themes:\s*$", b, re.M):
            return b
    raise AssertionError("the proposal has no fenced yaml block defining a `themes:` job")


def _job_ifs(block: str) -> dict:
    """`{job name: its raw `if:` expression}` for a jobs fragment.

    Hand-parsed rather than fed to yaml.safe_load, and ON PURPOSE: the proposal's block is a
    FRAGMENT meant to be appended under an existing `jobs:` key, so it is not a valid document
    on its own, and `${{ ... }}` is not YAML either. The shapes checked here are the two things
    that matter — which jobs exist, and what each one's `if` says.
    """
    out = {}
    cur = None
    for line in block.splitlines():
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", line)
        if m:
            cur = m.group(1)
            out.setdefault(cur, None)
            continue
        m = re.match(r"^    if:\s*(.+?)\s*$", line)
        if m and cur:
            out[cur] = m.group(1)
    return out


def _path_lists(block: str) -> list:
    """Every `path:` value in a jobs fragment, as a list of the paths it names.

    Handles both forms: `path: data/foo` inline, and `path: |` followed by indented lines.
    PARSED RATHER THAN GREPPED, because `form4_live` and the 13F zips are DISCUSSED at length
    in the comments that explain why they must never travel -- so a substring ban on either
    fires against the correct text. This project has paid for that shape repeatedly; the rule
    here is about what the paths ARE, not about which words appear.
    """
    out, cur, indent = [], None, None
    for line in block.splitlines():
        m = re.match(r"^(\s*)path:\s*(.*?)\s*$", line)
        if m:
            if cur is not None:
                out.append(cur)
            lead, val = m.group(1), m.group(2)
            if val in ("|", "|-", ">", ">-"):
                cur, indent = [], len(lead)
            else:
                out.append([val])
                cur, indent = None, None
            continue
        if cur is not None:
            # A block scalar ends at the first line indented no further than its own key.
            if line.strip() and (len(line) - len(line.lstrip())) <= indent:
                out.append(cur)
                cur, indent = None, None
            elif line.strip():
                cur.append(line.strip())
    if cur is not None:
        out.append(cur)
    return out


def _strip_comments(block: str) -> str:
    """The jobs fragment with YAML comments removed.

    WHY EVERY TEXT ASSERTION BELOW READS THIS AND NOT THE RAW BLOCK. The proposal explains each
    rule in a comment beside the thing it governs, so those comments necessarily QUOTE what they
    require -- `if: always()`, `merge-multiple`, `restore-keys: live-themes-crawl-`. A substring
    check on the raw text then passes against a MUTATED file because the prose still mentions it:
    measured, deleting `if: always()` from the shard's cache-save step was MISSED for exactly
    that reason. Comments are prose ABOUT the rule; the rule is the key.

    A YAML comment runs from an unquoted `#` to end of line. Nothing in these blocks puts a `#`
    inside a quoted scalar, and the stripper is pinned both ways below, so the simple form is
    the honest one here.
    """
    out = []
    for line in block.splitlines():
        i = line.find("#")
        if i == 0 or (i > 0 and line[i - 1].isspace()):
            line = line[:i].rstrip()
        if line.strip():
            out.append(line)
    return "\n".join(out)


def _scripts_reading_workflows(sdir: str) -> list:
    """Filenames in `sdir` that OPEN a file under `.github/workflows/`.

    Takes the directory as a parameter so the guard can be pointed at a planted offender -- a
    guard that has only ever been run against a clean tree has not been shown to fire.
    """
    import ast
    READERS = ("open", "read_text", "read_bytes")
    offenders = []
    for fn in sorted(os.listdir(sdir)):
        if not fn.endswith(".py") or fn == "workflow_source.py":
            continue
        try:
            tree = ast.parse(io.open(os.path.join(sdir, fn), encoding="utf-8",
                                     errors="replace").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            f = node.func
            nm = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nm not in READERS:
                continue
            lits = [n.value for n in ast.walk(node)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            joined = "/".join(lits)
            if "workflows" in joined and "pending_workflows" not in joined:
                offenders.append(fn)
                break
    return offenders


def _workflow_job_ifs() -> dict:
    src = _authoritative()
    body = src.split("\njobs:", 1)[1]
    return _job_ifs(body)


class EveryJobNamesItsOwnSchedule(unittest.TestCase):
    """The house rule, on the proposal and on the committed workflow alike."""

    def _assert_named(self, where, job, expr):
        self.assertIsNotNone(expr, "%s: job `%s` has no `if:` at all, so it runs on every "
                                   "event the workflow accepts" % (where, job))
        # (a) NO `always()`. It defeats `needs:` and makes a job run when its dependency was
        # skipped -- which is half of how session 70's assemble job came to fire 76x a week.
        self.assertNotIn("always()", expr,
                         "%s: job `%s` uses always(), so it runs even when its `needs:` was "
                         "skipped or failed" % (where, job))
        # (b) IF IT MENTIONS THE SCHEDULE EVENT AT ALL, IT MUST NAME A CRON. This is the exact
        # defect: `github.event_name == 'schedule'` alone is true for every cron in the file.
        if "event_name == 'schedule'" in expr.replace('"', "'"):
            self.assertIn("github.event.schedule ==", expr,
                          "%s: job `%s` fires on the SCHEDULE EVENT without naming a cron, so "
                          "it runs on every cron in this workflow" % (where, job))
        # (c) IF IT MENTIONS DISPATCH INPUTS, IT MUST GUARD ON THE DISPATCH EVENT. Reading
        # `inputs.kind` on a schedule event yields an empty string, which compares unequal and
        # so happens to be harmless -- but it is harmless by accident, and the existing five
        # jobs all pair the two.
        if "inputs.kind" in expr:
            self.assertIn("github.event_name == 'workflow_dispatch'", expr.replace('"', "'"),
                          "%s: job `%s` reads inputs.kind without guarding on the dispatch "
                          "event" % (where, job))
        # (d) IT MUST NAME SOMETHING. A condition with neither a cron nor a dispatch kind is
        # not a scoped condition.
        self.assertTrue("github.event.schedule ==" in expr or "inputs.kind" in expr,
                        "%s: job `%s` names neither a cron nor a dispatch kind" % (where, job))

    def test_the_PROPOSAL_jobs_each_name_their_own_schedule(self):
        ifs = _job_ifs(_jobs_block(_read(PROPOSAL)))
        self.assertEqual(sorted(ifs), ["themes", "themes-assemble"], ifs)
        for job, expr in ifs.items():
            self._assert_named("PROPOSAL", job, expr)

    def test_both_proposal_jobs_name_the_THEMES_cron_and_nothing_else(self):
        """Not merely 'a' cron — the one this proposal adds. A job naming the hot cron would
        satisfy a looser rule and still be wrong."""
        ifs = _job_ifs(_jobs_block(_read(PROPOSAL)))
        for job, expr in ifs.items():
            crons = re.findall(r"github\.event\.schedule == '([^']+)'", expr)
            self.assertEqual(crons, [THEMES_CRON],
                             "job `%s` names %r, not just the themes cron" % (job, crons))
            kinds = re.findall(r"inputs\.kind == '([^']+)'", expr)
            self.assertEqual(kinds, [THEMES_KIND],
                             "job `%s` names dispatch kinds %r" % (job, kinds))

    def test_the_cron_the_proposal_ADDS_is_the_cron_its_jobs_NAME(self):
        """The two halves of the change have to agree, or the job never fires at all — the
        silent-opposite of the defect being fixed."""
        md = _read(PROPOSAL)
        added = re.findall(r'^\s*- cron: "([^"]+)"', md, re.M)
        self.assertIn(THEMES_CRON, added,
                      "the proposal's schedule block does not add %r" % THEMES_CRON)
        ifs = _job_ifs(_jobs_block(md))
        for job, expr in ifs.items():
            self.assertIn("'%s'" % THEMES_CRON, expr, job)

    def test_the_dispatch_kind_is_in_the_OPTIONS_list(self):
        """A kind the dropdown does not offer cannot be dispatched."""
        md = _read(PROPOSAL)
        opts = re.search(r"options:\s*\[([^\]]+)\]", md)
        self.assertIsNotNone(opts, "the proposal does not show the dispatch options list")
        got = [x.strip() for x in opts.group(1).split(",")]
        self.assertIn(THEMES_KIND, got, got)

    def test_the_COMMITTED_workflow_obeys_the_same_rule(self):
        """So the rule survives the paste. Five jobs today, all five already compliant — which
        is what makes this a house rule rather than a new invention."""
        ifs = _workflow_job_ifs()
        self.assertGreaterEqual(len(ifs), 5, ifs)
        for job, expr in ifs.items():
            self._assert_named("auto-scan.yml", job, expr)

    def test_the_rule_would_CATCH_session_70s_text(self):
        """THE POSITIVE CONTROL. Without this the assertions above are consistent with a rule
        that cannot fail, and the whole point is that it catches the shape that shipped."""
        bad = ("${{ always() && (github.event_name == 'schedule' || "
               "github.event.inputs.kind == 'themes') }}")
        with self.assertRaises(AssertionError):
            self._assert_named("fixture", "themes-assemble", bad)
        # And it must catch each half on its own, not only the two together.
        with self.assertRaises(AssertionError):
            self._assert_named("fixture", "j",
                               "${{ github.event_name == 'schedule' }}")
        with self.assertRaises(AssertionError):
            self._assert_named("fixture", "j", "${{ always() }}")
        with self.assertRaises(AssertionError):
            self._assert_named("fixture", "j", None)
        # ...while PASSING the corrected shape, or it is just a ban on everything.
        self._assert_named("fixture", "themes-assemble",
                           "${{ (github.event_name == 'schedule' && github.event.schedule == "
                           "'17 7 * * 0') || (github.event_name == 'workflow_dispatch' && "
                           "github.event.inputs.kind == 'themes') }}")


class TheShardsWorkReachesTheAssembleJob(unittest.TestCase):
    """Defect 2: `restore-keys` returns ONE cache, so the assemble job saw one shard of three."""

    def setUp(self):
        self.md = _read(PROPOSAL)
        self.raw = _jobs_block(self.md)
        # CODE, not prose -- see `_strip_comments`.
        self.jobs = _strip_comments(self.raw)

    def test_the_transfer_is_an_ARTIFACT_merge_and_not_a_cache_prefix(self):
        self.assertIn("actions/upload-artifact@v4", self.jobs)
        self.assertIn("actions/download-artifact@v4", self.jobs)
        self.assertIn("merge-multiple: true", self.jobs,
                      "without merge-multiple each artifact lands in its own subdirectory and "
                      "the crawl root stays empty")
        self.assertIn("pattern: live-themes-crawl-*", self.jobs)

    def test_the_assemble_job_does_NOT_restore_the_crawl_from_a_cache_prefix(self):
        """The precise defect. A `restore-keys: live-themes-crawl-` in the ASSEMBLE job returns
        the single most recent shard — measured, that is 3,010 new SEC fetches instead of 39,
        and 1,000 names whose `submissions/` index is missing get a DURABLE empty Form 4
        payload that is never retried."""
        assemble = self.jobs.split("  themes-assemble:", 1)[1]
        self.assertNotIn("restore-keys: live-themes-crawl-", assemble,
                         "the assemble job restores the crawl from a cache prefix, which "
                         "returns ONE shard")

    def test_each_shards_warm_start_is_scoped_to_ITS_OWN_shard(self):
        """The same prefix bug in the restore direction: without the shard number a shard warms
        up from whichever shard finished last."""
        shard = self.jobs.split("  themes:", 1)[1].split("  themes-assemble:", 1)[0]
        self.assertIn("restore-keys: live-themes-crawl-${{ matrix.shard }}-", shard)

    def test_form4_live_can_NEVER_travel_between_runs(self):
        """Its window is `today - 90d .. today` and moves every day, while `fetch4` skips any
        name whose payload already exists — so a carried-over payload freezes the insider window
        and serves a stale score with nothing looking wrong. An ALLOWLIST is what makes that
        structurally impossible rather than remembered.

        CHECKED ON THE PARSED `path:` LISTS, not on the text. `form4_live` is named repeatedly
        in the comments that explain this very rule, so a substring ban would fire against the
        correct file -- the family this repo keeps paying for.
        """
        lists = _path_lists(self.jobs)
        self.assertTrue(lists, "no path: lists were parsed, so this checks nothing")
        for paths in lists:
            for p in paths:
                self.assertNotIn("form4_live", p,
                                 "a path list carries form4_live: %r" % (paths,))

    def test_the_allowlist_names_exactly_the_six_things_that_may_travel(self):
        """And it is an allowlist: every crawl path list is a subset of these six, so nothing
        new can travel by being forgotten."""
        allowed = {"data/live_themes/cusip", "data/live_themes/xbrl",
                   "data/live_themes/insider", "data/live_themes/submissions",
                   "data/live_themes/cik_map.json",
                   "data/live_themes/13f_aggregate.json"}
        crawl = [p for p in _path_lists(self.jobs)
                 if any(x.startswith("data/live_themes/") for x in p)]
        self.assertEqual(len(crawl), 3,
                         "expected three crawl path lists (warm restore, cache save, artifact "
                         "upload); got %d: %r" % (len(crawl), crawl))
        for paths in crawl:
            self.assertEqual(set(paths), allowed,
                             "a crawl path list is not the allowlist: %r" % (paths,))

    def test_submissions_travels_because_the_FORM_4_LEG_READS_IT(self):
        """Not an optimisation. `fetch4` builds its document list from
        `submissions/<ticker>.json`, which the CUSIP leg populates per shard, and writes a
        DURABLE `n_filings: 0` for a name whose index it cannot see."""
        self.assertIn("data/live_themes/submissions", self.jobs)

    def test_a_silently_empty_artifact_is_REFUSED(self):
        self.assertIn("if-no-files-found: error", self.jobs)

    def test_partial_progress_survives_a_failed_shard(self):
        """`actions/cache` does not save on failure, so a timed-out shard threw away every name
        it HAD fetched and met the same wall the following week."""
        shard = self.jobs.split("  themes:", 1)[1].split("  themes-assemble:", 1)[0]
        self.assertIn("actions/cache/save@v4", shard)
        self.assertIn("if: always()", shard,
                      "the shard's cache save is not unconditional, so a failed shard loses "
                      "its partial crawl")

    def test_the_13f_zips_do_not_travel(self):
        """190MB for the pair, and `build_13f` short-circuits on the 4.6MB aggregate whenever
        the periods match. Checked on the parsed paths for the same reason as above."""
        for paths in _path_lists(self.jobs):
            for p in paths:
                self.assertFalse(p.endswith(".zip") or p.endswith("*"),
                                 "a path list could carry the 13F zips: %r" % (paths,))

    def test_what_arrived_is_PRINTED(self):
        """"The merge worked" and "one shard arrived" look identical in a log that does not
        count. ~1500 per leg is right; ~500 is the defect returning."""
        assemble = self.jobs.split("  themes-assemble:", 1)[1]
        self.assertIn("Show what arrived", assemble)
        for leg in ("cusip", "xbrl", "insider", "submissions"):
            self.assertIn(leg, assemble)


class TheStripperIsNotVacuous(unittest.TestCase):
    """A comment stripper has to be pinned in BOTH directions, or a ban passes by seeing
    nothing. This is the lesson `MB15` wrote down after the same guard failed the same way."""

    def test_it_keeps_a_real_key_and_drops_the_same_words_from_a_comment(self):
        kept = _strip_comments("    steps:\n      - name: x\n        if: always()\n")
        self.assertIn("if: always()", kept, "the stripper removed the code as well")
        dropped = _strip_comments("      # an explicit save with `if: always()` keeps it\n")
        self.assertNotIn("always()", dropped, "the stripper left a comment behind")

    def test_the_real_block_survives_stripping(self):
        jobs = _strip_comments(_jobs_block(_read(PROPOSAL)))
        self.assertIn("  themes:", jobs)
        self.assertIn("  themes-assemble:", jobs)
        self.assertIn("actions/upload-artifact@v4", jobs)
        self.assertGreater(len(jobs.splitlines()), 40,
                           "the stripper ate the block, so every check on it is vacuous")


class TheHotJobCanActuallySeeTheCache(unittest.TestCase):
    """Item 4 is the step that makes the whole feature reach a user, and NOTHING ELSE CHECKS IT.

    `tests/test_theme_cache_build.py::test_the_hot_job_sets_LIVE_THEMES_CACHE` skips loudly
    today and is described as becoming "a hard failure once it lands". It will not: it greps the
    WHOLE workflow for `LIVE_THEMES_CACHE`, and the ASSEMBLE job sets that variable — so after
    this paste it flips to PASSING even if item 4 were left out entirely, which is the one
    omission that would leave every live score without the three themes. Its name says `hot job`
    and its body says `txt`. Not this lane's file; covered here instead.
    """

    def setUp(self):
        self.md = _read(PROPOSAL)

    def _item4(self) -> str:
        for b in _fenced_yaml(self.md):
            if "Restore the live theme cache" in b:
                return _strip_comments(b)
        raise AssertionError("the proposal has no hot-job restore step")

    def test_the_hot_job_restores_the_cache_file_the_reader_reads(self):
        """`live_themes.py` reads `data/live_cache/theme_columns.json` — `DEFAULT_CACHE`. The
        restore must land it THERE, or the scan looks in the right place at nothing."""
        from scripts import theme_cache_build as B
        b = self._item4()
        self.assertIn("path: data/live_cache/theme_columns.json", b)
        self.assertEqual(B.DEFAULT_CACHE.replace(os.sep, "/"),
                         "data/live_cache/theme_columns.json",
                         "the reader's default path moved; item 4 now restores the wrong file")

    def test_the_hot_job_only_RESTORES_and_never_saves(self):
        """`themes-assemble` is the only writer. A hot scan that could save under this key would
        publish a partial cache 40 times a week from the intraday cron alone."""
        b = self._item4()
        self.assertIn("actions/cache/restore@v4", b)
        self.assertNotIn("cache/save", b)
        self.assertNotIn("actions/cache@v4", b,
                         "the combined cache action SAVES on post-job, so the hot job would "
                         "publish whatever it happened to hold")

    def test_the_restore_reaches_the_LATEST_published_cache(self):
        """The key is deliberately unmatchable so `restore-keys` does the work — otherwise a
        hot run would only ever match its own run id and never find last Sunday's cache."""
        b = self._item4()
        self.assertIn("restore-keys: live-themes-cache-", b)
        self.assertIn("never-matches", b,
                      "the exact key is matchable, so the restore may bind to the wrong run")


class TheProposalStatesWhatItCosts(unittest.TestCase):
    """A workflow proposal without its Actions bill is not reviewable."""

    def test_it_states_the_weekly_minutes_and_the_public_private_difference(self):
        md = _read(PROPOSAL)
        self.assertIn("ACTIONS MINUTES PER WEEK", md)
        self.assertIn("2,000", md, "the private-repo allowance is not stated")
        self.assertRegex(md, r"PUBLIC today", "it does not say the repo is public today")
        self.assertIn("6,750", md, "the cost of the defect is not quantified")

    def test_it_names_the_measured_fetch_counts_both_ways(self):
        md = _read(PROPOSAL)
        self.assertIn("3,010", md)
        self.assertIn("39", md)

    def test_it_says_plainly_whether_the_text_is_safe_to_paste(self):
        md = _read(PROPOSAL)
        self.assertIn("SAFE TO PASTE", md)


class EveryCronReachesAJob(unittest.TestCase):
    """THE COMPLEMENT OF `EveryJobNamesItsOwnSchedule`, AND I ALMOST SHIPPED THE DEFECT IT CATCHES.

    That class pins one direction: no job may fire on a bare `schedule` event without naming a
    cron. This pins the other: **no cron may exist that no job's condition matches.** Such a cron
    fires a real run in which every job SKIPS -- it consumes a scheduled slot, appears in the run
    list as a success, and does nothing. Nothing in the run looks wrong.

    ITEM 37 WROTE A BACKUP INTRADAY CRON (`53 17-19 * * 1-5`) into
    `data/pending_workflows/auto-scan.yml` and the intraday job is gated on the EXACT string
    `github.event.schedule == '23 13-20 * * 1-5'`. Adding the cron without extending that
    condition would have delivered runs that did nothing, which is the opposite of the point --
    and on a workflow whose scheduler already drops 72% of intraday slots, a silent no-op would
    have been indistinguishable from another drop.

    COMMENTS STRIPPED FIRST, AND THAT DISTINCTION COST A CUT OF ITS OWN: a regex over
    `- cron: "..."` matches the comment documenting the cron the master audit REMOVED
    (`# REMOVED by the master audit (MA1): - cron: "0 12 1 * *"`), so the first version of this
    audit reported a dead cron that does not exist. `_strip_comments` is this file's own answer
    to that family and every other text assertion here already reads through it.

    **IT USED `yaml.safe_load` AND THAT FAILED IN CI, WHICH IS THE WORSE DEFECT OF THE TWO.**
    PyYAML is installed locally and is NOT on the runner, so both committed-workflow guards
    raised `ModuleNotFoundError` and the suite reported `errors=2` -- a guard that cannot run
    where it matters, after a session spent removing exactly that shape from other people's
    checks. It took the land red, which is the good outcome: an `unittest.skipUnless` on the
    import would have left the two checks silently absent in CI forever.

    SO THIS READS TWO LINE SHAPES, not a document: `- cron: "..."` inside the `schedule:`
    block, and `github.event.schedule == '...'` anywhere in a job condition. It depends on
    nothing outside the standard library, which is the property that matters for a guard whose
    whole job is to be green or red on a runner.
    """

    def _crons_and_gates(self, path, text=None):
        import re
        body = _strip_comments(text if text is not None else _read(path))
        # The `schedule:` block ends at the next key no more indented than itself, which for
        # these workflows is `workflow_dispatch:` or `jobs:`. Bounded that way rather than by a
        # line count so a comment or an added cron cannot push the end past it.
        crons = []
        in_sched = False
        for line in body.splitlines():
            st = line.strip()
            if st.startswith("schedule:"):
                in_sched = True
                continue
            if in_sched:
                m = re.match(r"-\s*cron:\s*[\"\']([^\"\']+)[\"\']", st)
                if m:
                    crons.append(m.group(1))
                    continue
                if st and not st.startswith("-"):
                    in_sched = False
        gates = set(re.findall(r"github\.event\.schedule\s*==\s*\'([^\']+)\'", body))
        return crons, gates

    def test_the_committed_workflow_has_no_dead_cron(self):
        crons, gates = self._crons_and_gates(WORKFLOW, _authoritative())
        self.assertTrue(crons, "no crons were parsed, so this guard is looking at nothing")
        dead = [c for c in crons if c not in gates]
        self.assertEqual(dead, [], "these crons match no job's `if`, so every run they fire "
                                   "does nothing: %s" % dead)

    def test_no_job_is_gated_on_a_cron_that_does_not_exist(self):
        """The mirror failure: a job that can never fire on a schedule. Harmless to run and
        silently fatal to whatever it was supposed to do."""
        crons, gates = self._crons_and_gates(WORKFLOW, _authoritative())
        orphan = sorted(g for g in gates if g not in crons)
        self.assertEqual(orphan, [], "these job conditions name a cron the schedule does not "
                                     "contain, so the job never fires: %s" % orphan)

    def test_a_pending_workflow_is_held_to_the_same_rule(self):
        """`data/pending_workflows/` is how a lane proposes a `.github/` change it cannot make,
        so it is exactly where an unpaired cron would slip through unreviewed. SKIPPED LOUDLY
        when there is no pending file -- the normal state -- rather than passing vacuously."""
        pending = os.path.join(REPO, "data", "pending_workflows", "auto-scan.yml")
        if not os.path.exists(pending):
            self.skipTest("no pending auto-scan.yml to check (this is the normal state)")
        crons, gates = self._crons_and_gates(pending)
        self.assertTrue(crons)
        self.assertEqual([c for c in crons if c not in gates], [])
        self.assertEqual(sorted(g for g in gates if g not in crons), [])


class AWorkflowClaimReadsTheCopyThatRUNS(unittest.TestCase):
    """ITEM 44. The measured defect: item 42 reported `auto-scan.yml` had no `53 17-19` cron.

    It had carried it since `d66155e` (installed 2026-10-08 08:15 ET). The lane read the file in
    its own worktree, branched before that commit -- and **that is guaranteed, not unlucky: the
    land gate refuses any branch touching `.github/`, so a workflow can only ever change on
    main, by Don running `install_workflows.bat`. A lane's copy of a `.github/` file is stale by
    construction.**
    """

    def test_the_reader_never_claims_authority_it_does_not_have(self):
        got = WS.read("auto-scan.yml")
        self.assertIn(got["source"], ("origin/main", "local"))
        self.assertEqual(got["authoritative"], got["source"] == "origin/main")
        if not got["authoritative"]:
            # The fallback must SAY so. A helper that silently substituted the local copy would
            # reproduce item 42's defect with an extra layer of indirection, because the caller
            # would believe it held the authoritative text.
            self.assertTrue(got["reason"], "the fallback must explain itself")
        self.assertTrue(got["text"], "it returned no text at all, so every caller is vacuous")

    def test_a_missing_workflow_is_reported_and_not_invented(self):
        got = WS.read("no-such-workflow-%s.yml" % os.getpid())
        self.assertFalse(got["authoritative"])
        self.assertIsNone(got["text"])
        self.assertIn("never authoritative", got["reason"])

    def test_the_reader_CAN_SEE_a_stale_local_copy(self):
        """NON-VACUITY, against the real commit that caused the wrong report.

        Without this the helper could be hard-coded to say `differs: False` and every test
        above would still pass. Reading the parent of the install commit must produce a text
        that LACKS the backup cron and a `differs` that is True.
        """
        old = WS.read("auto-scan.yml", ref="d66155e^")
        if not old["authoritative"]:
            self.skipTest("d66155e^ is not reachable in this checkout (shallow clone)")
        self.assertNotIn("53 17-19 * * 1-5", WS.crons(old["text"]),
                         "d66155e^ should PREDATE the backup cron")
        self.assertTrue(old["differs"],
                        "the local copy carries the cron and the old ref does not, so this "
                        "must read as a difference -- otherwise `differs` is decoration")

    def test_scripts_do_not_read_a_github_workflow_behind_the_readers_back(self):
        """ONE authoritative reader (B7). The alternative is what already happened once.

        READ THROUGH THE AST, AND THE FIRST CUT OF THIS GUARD IS WHY. It collected every string
        literal naming `workflows` and flagged the file if it also called `open` anywhere --
        and **it fired on five correct scripts, every one of them a DOCSTRING or a comment
        describing which workflow installs a package.** `MA49`/`MB1`/`MB15`'s family, in the
        guard written to enforce one authoritative reader, on its first run.

        The property is not "this file mentions a workflow"; it is "this file OPENS one". So
        the literal has to be tied to the call: a `Call` to `open`/`io.open`/`read_text` with
        `workflows` named anywhere inside ITS OWN argument subtree. `workflow_source.py` is
        excluded because it is the reader, and `pending_workflows/` because a pending file is a
        PROPOSAL -- reading it locally is the only way to read it at all.
        """
        offenders = _scripts_reading_workflows(os.path.join(REPO, "scripts"))
        self.assertEqual(offenders, [],
                         "these scripts read a .github/workflows file directly; route them "
                         "through scripts/workflow_source.py, whose whole job is that a claim "
                         "about the live scheduler is not made from a lane's stale copy: %s"
                         % offenders)

    def test_that_guard_actually_FIRES_on_a_planted_offender(self):
        """The positive control, with the three cases that separate the rule from a grep.

        A guard only ever run against a clean tree has not been shown to fire -- and the first
        cut of the one above fired on five CORRECT files, so both directions need pinning.
        """
        import shutil
        import tempfile
        d = tempfile.mkdtemp(prefix="wfguard-")
        self.addCleanup(shutil.rmtree, d, True)

        def put(name, body):
            with io.open(os.path.join(d, name), "w", encoding="utf-8") as fh:
                fh.write(body)

        # (1) THE OFFENDER: reads the live workflow directly.
        put("offender.py", 'import os\n'
                           'open(os.path.join("x", ".github", "workflows", "auto-scan.yml"))\n')
        # (2) PROSE ONLY -- a docstring naming the workflow, plus an unrelated open(). This is
        #     exactly what the first cut flagged, five times.
        put("innocent_prose.py", '"""Installed by .github/workflows/auto-scan.yml."""\n'
                                 'open("requirements.txt")\n')
        # (3) THE PENDING DIRECTORY is a PROPOSAL, and reading it locally is the only way.
        put("innocent_pending.py",
            'open("data/pending_workflows/tradier-seam.yml")\n')

        found = _scripts_reading_workflows(d)
        self.assertEqual(found, ["offender.py"],
                         "the guard must flag the real read and neither innocent file; got %s"
                         % found)


if __name__ == "__main__":
    unittest.main(verbosity=2)
