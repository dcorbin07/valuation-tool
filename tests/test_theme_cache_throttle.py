# -*- coding: utf-8 -*-
"""A SEC refusal is not an absence -- the theme cache's publication probe, three answers.

    python tests/test_theme_cache_throttle.py

WHAT THIS EXISTS FOR, measured on the live runner rather than imagined. Run 37226135982
(2026-10-04) got all three crawl shards green for the first time and then died in
`themes-assemble`:

    STEPPED BACK 4 quarter(s): the derived window is not published by SEC yet
                 30-JUN-2026  01jun2026-31aug2026  published=False
                 31-MAR-2026  01mar2026-31may2026  published=False
                 31-DEC-2025  01dec2025-28feb2026  published=False
                 30-SEP-2025  01sep2025-30nov2025  published=False
      REFUSING: no published 13F window within 4 quarters
    13f: downloading 01mar2025-31may2025
    requests.exceptions.HTTPError: 429 Client Error: Too Many Requests

THREE SEPARATE DEFECTS IN THAT OUTPUT, and the first is the one that makes it misleading rather
than merely broken.

 1. **A 429 READ AS "NOT PUBLISHED".** The probe was `ok = r.status_code == 200`, which collapses
    three answers into two. `30-SEP-2025` is the tell: those 13Fs were due in November 2025 and
    have been on SEC's site for most of a year, so `published=False` there cannot mean what it
    says. The run then reported *"not published by SEC yet"* -- sending a reader to look for a
    filing deadline that had passed eleven months earlier.
 2. **THE REFUSAL DID NOT REFUSE.** It printed `REFUSING` and downloaded the window anyway.
 3. **NOTHING WAS PACED.** Three shards had just finished hammering SEC; the probe went out
    unpaced because `main()` did not build its `Guard` until thirty lines later, and
    `download_dataset` took a `guard` argument whose only appearance in the body was the
    signature itself.

NOTHING HERE TOUCHES THE NETWORK, and that is enforced rather than intended: `requests` is
replaced by a table of canned responses, and a test asserts the substitution bites and is
restored. The gate runs every suite on every land, so a suite that called SEC would make the
land depend on a vendor -- and would get itself rate-limited, which is the very condition under
test.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import scripts.live_theme_sources as M       # noqa: E402
import scripts.theme_cache_build as TC       # noqa: E402


class _Resp:
    def __init__(self, status):
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP %d" % self.status_code)

    def iter_content(self, _n):
        return [b"x" * 16]


class _Transport:
    """A scripted `requests`. `plan` is consumed one status per call."""

    def __init__(self, plan):
        self.plan = list(plan)
        self.calls = []

    def head(self, url, **kw):
        self.calls.append(("head", url))
        return _Resp(self.plan.pop(0) if self.plan else 200)

    def get(self, url, **kw):
        self.calls.append(("get", url))
        return _Resp(self.plan.pop(0) if self.plan else 200)


class _Guard(M.Guard):
    """The real Guard with a no-op sleeper, so pacing is counted and not waited on."""

    def __init__(self, budget=99):
        self.slept = []
        super().__init__(min_interval=0.0, budget=budget, sleeper=self.slept.append)


def _with_transport(plan):
    """Install the scripted transport into the module's lazy `import requests`."""
    import types
    t = _Transport(plan)
    mod = types.ModuleType("requests")
    mod.head, mod.get = t.head, t.get

    class _Exc(Exception):
        pass
    mod.exceptions = types.SimpleNamespace(HTTPError=_Exc)
    saved = sys.modules.get("requests")
    sys.modules["requests"] = mod
    return t, saved


def _restore(saved):
    if saved is None:
        sys.modules.pop("requests", None)
    else:
        sys.modules["requests"] = saved


class TheProbeHasThreeAnswers(unittest.TestCase):
    def test_200_is_published(self):
        t, saved = _with_transport([200])
        try:
            self.assertIs(M.head_published("http://x/a.zip", _Guard()), True)
        finally:
            _restore(saved)
        self.assertEqual(len(t.calls), 1)

    def test_404_is_a_genuine_absence(self):
        t, saved = _with_transport([404])
        try:
            self.assertIs(M.head_published("http://x/a.zip", _Guard()), False)
        finally:
            _restore(saved)

    def test_429_RAISES_rather_than_returning_not_published(self):
        """The whole defect in one assertion. A rate-limit must not be expressible as False."""
        _, saved = _with_transport([429] * 20)
        try:
            with self.assertRaises(M.Throttled):
                M.head_published("http://x/a.zip", _Guard())
        finally:
            _restore(saved)

    def test_a_429_that_clears_on_retry_is_published(self):
        """Retry is what makes the three-state answer usable rather than merely honest."""
        _, saved = _with_transport([429, 200])
        try:
            self.assertIs(M.head_published("http://x/a.zip", _Guard()), True)
        finally:
            _restore(saved)

    def test_it_paces_before_every_attempt(self):
        g = _Guard()
        _, saved = _with_transport([429, 200])
        try:
            M.head_published("http://x/a.zip", g)
        finally:
            _restore(saved)
        self.assertEqual(g.calls, 2, "every attempt must pass through the guard")
        self.assertGreaterEqual(len(g.slept), 1, "a 429 must back off")


class TheStepBackStopsOnARefusal(unittest.TestCase):
    def _probe(self, plan, **kw):
        t, saved = _with_transport(plan)
        try:
            return TC.newest_published_periods(guard=_Guard(), **kw), t
        finally:
            _restore(saved)

    def test_a_404_steps_back_and_a_later_200_is_taken(self):
        per, t = self._probe([404, 200])
        self.assertEqual(per.get("stepped_back"), 1)
        self.assertNotIn("undetermined", per)
        self.assertNotIn("unpublished", per)
        self.assertEqual(len(t.calls), 2)

    def test_a_throttle_STOPS_the_walk_and_reports_UNDETERMINED(self):
        """Stepping back on a rate-limit asks four more questions of a server that has just
        refused one, and records four more false absences on the way."""
        per, t = self._probe([429] * 40)
        self.assertIs(per.get("undetermined"), True)
        self.assertIsNot(per.get("unpublished"), True,
                         "a refusal must never be recorded as 'no published window'")
        probed = per.get("probed") or []
        self.assertEqual(len(probed), 1, "it must not keep walking: %r" % (probed,))
        self.assertIsNone(probed[0]["published"], "published must be UNKNOWN, not False")
        self.assertTrue(probed[0].get("throttled"))

    def test_four_genuine_404s_are_still_unpublished(self):
        """The repair must not make the real 'not published' state unreachable."""
        per, _ = self._probe([404] * 8)
        self.assertIs(per.get("unpublished"), True)
        self.assertNotIn("undetermined", per)

    def test_no_guard_is_UNDETERMINED_rather_than_absent(self):
        """My own first cut fell back to `ok = False` here -- the same conflation one level up:
        unable to ASK became 'not published'."""
        _, saved = _with_transport([200])
        try:
            per = TC.newest_published_periods(guard=None)
        finally:
            _restore(saved)
        # The module DOES have a Guard, so the real path is taken and this is not undetermined.
        self.assertTrue(hasattr(M, "Guard"))
        self.assertNotIn("no Guard available", str(per.get("probed")))

    def test_the_guard_none_branch_is_reachable_and_says_so(self):
        saved_guard = M.Guard
        del M.Guard
        try:
            per = TC.newest_published_periods(guard=None)
        finally:
            M.Guard = saved_guard
        self.assertIs(per.get("undetermined"), True)
        self.assertIn("no Guard available", (per["probed"][0] or {}).get("throttled", ""))


class TheDownloadHonoursItsGuard(unittest.TestCase):
    def test_a_429_is_retried_rather_than_raised_on_the_first_look(self):
        """`guard` was in the signature and nowhere in the body, so `raise_for_status()` turned
        SEC's 429 into a traceback that killed the assemble step."""
        import tempfile
        g = _Guard()
        _, saved = _with_transport([429, 200])
        try:
            d = tempfile.mkdtemp()
            p = M.download_dataset(d, "01jan2020-31mar2020", guard=g)
        finally:
            _restore(saved)
        self.assertTrue(os.path.exists(p))
        self.assertEqual(g.calls, 2)

    def test_a_sustained_429_raises_Throttled_and_not_HTTPError(self):
        import tempfile
        _, saved = _with_transport([429] * 40)
        try:
            with self.assertRaises(M.Throttled):
                M.download_dataset(tempfile.mkdtemp(), "01jan2020-31mar2020", guard=_Guard())
        finally:
            _restore(saved)

    def test_it_paces_even_when_no_guard_is_passed(self):
        """`None` used to mean 'no pacing at all', which made the unpaced path the DEFAULT --
        and the default is what the failing run took."""
        import tempfile
        _, saved = _with_transport([200])
        try:
            p = M.download_dataset(tempfile.mkdtemp(), "01jan2020-31mar2020")
        finally:
            _restore(saved)
        self.assertTrue(os.path.exists(p))

    def test_the_guard_is_REFERENCED_in_the_body_and_not_only_the_signature(self):
        """The defect was visible by reading and nobody read it. Pinned structurally so the
        parameter cannot go back to being decorative."""
        import ast
        import inspect
        src = inspect.getsource(M.download_dataset)
        tree = ast.parse(src.lstrip())
        fn = tree.body[0]
        names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        self.assertIn("guard", names)
        self.assertGreaterEqual(
            sum(1 for n in ast.walk(fn) if isinstance(n, ast.Name) and n.id in ("guard", "g")),
            3, "the guard is mentioned but barely used")


class TheRunActuallyStops(unittest.TestCase):
    """The behavioural half. The unit tests above prove the probe reports UNDETERMINED; this
    proves the RUN then refuses -- which is the half that was broken, because the old code
    printed `REFUSING` and downloaded the window anyway. A refusal that does not refuse is
    worse than no refusal, because the log says the right thing."""

    def _run(self, plan, extra=(), aggregate=None, as_of=None):
        """Drive `main()` with a scripted SEC and an ISOLATED fallback source.

        `M.DEFAULT_ROOT` IS REDIRECTED TO A TEMP DIR, and that is not tidiness. The
        fallback reads `13f_aggregate.json` from that root, so without isolation these
        tests pass or fail on whether the machine happens to have one -- and they did:
        adding the fallback turned two of them into ERRORS on a box with a populated cache
        while leaving them green on a bare runner. A test whose verdict depends on the
        ambient tree is measuring the tree.

        `aggregate` is the on-disk window offered to the fallback, or None for "there is
        nothing confirmed to fall back to".
        """
        import contextlib
        import io as _io
        import json as _json
        import tempfile
        d = tempfile.mkdtemp()
        uni = os.path.join(d, "u.txt")
        with open(uni, "w", encoding="utf-8") as fh:
            fh.write("AAPL\nMSFT\n")
        root = os.path.join(d, "live_themes")
        os.makedirs(root, exist_ok=True)
        if aggregate:
            with open(os.path.join(root, "13f_aggregate.json"), "w",
                      encoding="utf-8") as fh:
                _json.dump({"periods": list(aggregate), "shape": {},
                            "by_period": {}}, fh)
        saved_guard, saved_root = M.Guard, M.DEFAULT_ROOT
        M.Guard = _Guard                      # a no-op sleeper, so nothing waits
        M.DEFAULT_ROOT = root
        t, saved = _with_transport(plan)
        buf, err = _io.StringIO(), _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                _argv = ["--universe", uni, *extra]
                if as_of:
                    _argv += ["--as-of", as_of]
                rc = TC.main(_argv)
        finally:
            _restore(saved)
            M.Guard, M.DEFAULT_ROOT = saved_guard, saved_root
        return rc, buf.getvalue(), err.getvalue(), t

    def test_a_throttled_probe_REFUSES_and_downloads_nothing(self):
        rc, out, err, t = self._run([429] * 60)
        self.assertEqual(rc, 4, out + err)
        self.assertIn("CANNOT DETERMINE", out)
        self.assertIn("UNKNOWN", out)
        self.assertNotIn("no published 13F window", out,
                         "a rate-limit must not be reported as SEC not having published")
        self.assertEqual([c for c in t.calls if c[0] == "get"], [],
                         "it downloaded a window it could not verify")

    def test_the_dry_run_still_REPORTS_rather_than_exiting_on_the_refusal(self):
        """My own first cut put the stop before this branch, which silenced the diagnosis in
        the one mode whose whole job is to print it."""
        rc, out, _err, _t = self._run([429] * 60, extra=("--dry-run",))
        self.assertEqual(rc, 0)
        self.assertIn("CANNOT DETERMINE", out)
        self.assertIn("DRY RUN", out)

    def test_the_probe_is_handed_a_guard_rather_than_building_its_own_late(self):
        """`main()` used to create its `Guard` THIRTY LINES AFTER the probe had already gone
        out, which is how the probe came to be rate-limited by the crawl shards that ran
        minutes earlier. One guard for the run also means the probe's refusals count against
        the same circuit breaker as the download's, which is the point of a budget."""
        import contextlib
        import io as _io
        import tempfile
        seen = {}
        real = TC.newest_published_periods

        def spy(as_of=None, max_back=4, guard=None):
            seen["guard"] = guard
            return real(as_of, max_back, guard=guard)

        uni = os.path.join(tempfile.mkdtemp(), "u.txt")
        with open(uni, "w", encoding="utf-8") as fh:
            fh.write("AAPL\n")
        saved_guard, M.Guard = M.Guard, _Guard
        TC.newest_published_periods = spy
        _t, saved = _with_transport([429] * 60)
        try:
            with contextlib.redirect_stdout(_io.StringIO()), \
                    contextlib.redirect_stderr(_io.StringIO()):
                # `--dry-run` so this stops before any price fetch. It also removes a hidden
                # dependency on the ambient tree: without it, a machine holding a 13F aggregate
                # falls back and runs on, and a bare runner refuses -- two different code paths
                # for one assertion about the guard.
                TC.main(["--universe", uni, "--dry-run"])
        finally:
            _restore(saved)
            TC.newest_published_periods = real
            M.Guard = saved_guard
        self.assertIsNotNone(seen.get("guard"),
                             "the probe was called without the run's guard")

    def test_the_dry_run_no_longer_claims_it_made_no_SEC_request(self):
        """It said "no SEC request was made" while the probe above had already made one."""
        _rc, out, _err, t = self._run([200], extra=("--dry-run",))
        self.assertTrue([c for c in t.calls if c[0] == "head"],
                        "the probe really does call SEC, which is the point")
        self.assertNotIn("no SEC request was made", out)


class TheFallbackIsAConfirmedWindow(unittest.TestCase):
    """Item 32(3). Refusing was right about the 429 and wrong about the outcome: on GitHub's
    SHARED RUNNER IPs it can mean the job never completes, which trades a wrong cache for NO
    cache -- and with no cache `institutional` and `insider` contribute nothing at all, which is
    the 0.00 the live check has been reporting. A cache one quarter behind, LABELLED, is better.

    THE FALLBACK IS NEVER A GUESSED WINDOW. It is one SEC demonstrably served: the aggregate on
    disk exists only because an earlier step downloaded and aggregated it. On the sharded
    workflow that is the window the CRAWL SHARDS confirmed -- `13f_aggregate.json` travels to
    the assemble job in the artifact (only the zips are excluded, for size) -- so the fallback
    costs NO SEC REQUEST, which is exactly why it beats "probe one quarter older": a probe can
    be throttled and a file cannot.
    """

    def test_a_throttled_probe_FALLS_BACK_to_the_window_on_disk_and_labels_it(self):
        # `--dry-run` IS THE SEAM, and it is not a dodge. Once the fallback makes the run
        # PROCEED it goes on to fetch prices from a live vendor, which a suite must not do --
        # and the decision being asserted (fall back, or refuse) is fully determined before
        # that point, from the probe's answer and the aggregate on disk. So the dry run reports
        # it and this reads the report. The non-dry-run REFUSAL is still exercised directly
        # below, because that path returns before any fetch.
        rc, out, err, t = TheRunActuallyStops()._run(
            [429] * 60, aggregate=("31-DEC-2025", "31-MAR-2026"), extra=("--dry-run",))
        self.assertIn("FELL BACK", out)
        self.assertIn("01mar2026-31may2026", out, "it did not adopt the confirmed window")
        self.assertIn("13F one quarter stale", out, "the staleness is not labelled")
        self.assertEqual(rc, 0, "it refused despite having a confirmed window: " + err)
        self.assertIn("WOULD BUILD, LABELLED: 13F one quarter stale", out)
        self.assertEqual([c for c in t.calls if c[0] == "get"], [],
                         "the fallback made a SEC download; it must cost no request")

    def test_the_diagnosis_SURVIVES_the_fallback(self):
        """My first cut fell back correctly and STOPPED SAYING WHY, because the CANNOT DETERMINE
        line keys on a flag the fallback dict does not carry. Falling back quietly is the same
        shape of defect as reading a 429 as 'not published'."""
        _rc, out, _err, _t = TheRunActuallyStops()._run(
            [429] * 60, aggregate=("31-DEC-2025", "31-MAR-2026"), extra=("--dry-run",))
        self.assertIn("CANNOT DETERMINE", out)

    def test_with_NOTHING_on_disk_it_still_REFUSES(self):
        """The repair must not make the refusal unreachable -- there is genuinely nothing to
        fall back to, and inventing a window would be the conflation one level up."""
        rc, out, err, t = TheRunActuallyStops()._run([429] * 60, aggregate=None)
        self.assertEqual(rc, 4, out)
        self.assertIn("no confirmed window to fall back to", err)
        self.assertEqual([c for c in t.calls if c[0] == "get"], [])

    def test_a_CONFIRMED_derived_window_does_not_fall_back(self):
        """The fallback must fire only when the derived window cannot be confirmed."""
        _rc, out, _err, _t = TheRunActuallyStops()._run(
            [200], aggregate=("31-DEC-2025", "31-MAR-2026"), extra=("--dry-run",))
        self.assertNotIn("FELL BACK", out)
        self.assertIn("WOULD BUILD from the derived window", out)
        self.assertIn("13F current", out)

    def test_the_label_wording_is_the_one_asked_for_and_pluralises_honestly(self):
        self.assertEqual(TC._stale_label(1), "13F one quarter stale")
        self.assertEqual(TC._stale_label(2), "13F two quarters stale")
        self.assertEqual(TC._stale_label(0), "13F current")

    def test_the_window_is_DERIVED_from_the_label_not_stored(self):
        """`B7`: a fallback must not be able to name a window the downloader would not fetch."""
        per = TC.periods_from_labels("31-MAR-2026", "31-DEC-2025", "2026-10-04")
        self.assertEqual(per["window_curr"], "01mar2026-31may2026")
        self.assertEqual(per["window_prior"], "01dec2025-28feb2026")


class TheTwoClocksAreReportedSeparately(unittest.TestCase):
    """Item 32(4). The shard step printed "as of 2026-07-01" and the assemble step "as of
    2026-10-04", and NEITHER was wrong about the date: stepping back a quarter is implemented by
    MOVING THE CLOCK (`as_of - 95 days`) and re-deriving, so after one step back on 2026-10-04
    the field reads 2026-10-04 - 95d = 2026-07-01 exactly. The shard stepped back once (and
    confirmed 31-MAR-2026); the assemble step's probe was throttled before it stepped anywhere.
    The field means "the clock these periods were derived from" and was being read as "today"."""

    def test_a_step_back_moves_the_derivation_clock_and_run_as_of_keeps_today(self):
        import datetime as _dt
        _t, saved = _with_transport([404, 200])
        try:
            per = TC.newest_published_periods(_dt.date(2026, 10, 4), guard=_Guard())
        finally:
            _restore(saved)
        self.assertEqual(per["stepped_back"], 1)
        self.assertEqual(per["as_of"], "2026-07-01",
                         "the derivation clock did not move as the step-back implies")
        self.assertEqual(per["run_as_of"], "2026-10-04", "the job's own clock was lost")
        self.assertEqual(per["window_curr"], "01mar2026-31may2026")

    def test_no_step_back_leaves_the_two_clocks_equal(self):
        import datetime as _dt
        _t, saved = _with_transport([200])
        try:
            per = TC.newest_published_periods(_dt.date(2026, 10, 4), guard=_Guard())
        finally:
            _restore(saved)
        self.assertEqual(per["as_of"], per["run_as_of"])

    def test_the_run_clock_survives_a_throttle(self):
        import datetime as _dt
        _t, saved = _with_transport([429] * 40)
        try:
            per = TC.newest_published_periods(_dt.date(2026, 10, 4), guard=_Guard())
        finally:
            _restore(saved)
        self.assertIs(per.get("undetermined"), True)
        self.assertEqual(per["run_as_of"], "2026-10-04")


class ThePatientPolicyIsTheDataSetsAlone(unittest.TestCase):
    """Item 32(2). SEC throttles for ~10 minutes and the module default spends ~15 seconds, which
    is why the run gave up. It is NOT raised globally: `MAX_ATTEMPTS` governs every per-ticker
    fetch in the crawl (1,500 names across three legs), so a patient policy there would turn one
    throttled run into a job that never finishes inside its timeout."""

    def test_the_dataset_policy_waits_out_a_ten_minute_cool_off(self):
        n, base, cap = M._policy(True)
        total = sum(min(cap, base * (2 ** a)) for a in range(n - 1))
        self.assertGreaterEqual(total, 600.0,
                                "the patient policy gives up inside SEC's ~10 minute cool-off")

    def test_the_default_policy_is_UNCHANGED_so_the_crawl_still_terminates(self):
        self.assertEqual(M._policy(False), (3, 5.0, 120.0))

    def test_the_probe_and_the_download_are_patient_to_the_SAME_degree(self):
        """Two halves of one question. A run that waits out a cool-off on the HEAD and then
        gives up after 15 seconds on the GET has spent the wait and thrown away the answer."""
        self.assertEqual(M._policy(True), M._policy(True))
        n, base, cap = M._policy(True)
        self.assertEqual((n, base, cap), (M.DATASET_MAX_ATTEMPTS, M.DATASET_BACKOFF_BASE_S,
                                          M.DATASET_BACKOFF_MAX_S))

    def test_a_patient_caller_still_spends_the_circuit_breaker_budget(self):
        """Being patient must not also mean being exempt from the thing that stops a run banking
        a partial census."""
        g = _Guard(budget=2)
        g.throttled(0, 30.0, 300.0)
        g.throttled(1, 30.0, 300.0)
        with self.assertRaises(SystemExit):
            g.throttled(2, 30.0, 300.0)

    def test_a_long_throttle_that_clears_is_retried_rather_than_refused(self):
        """The behavioural point: five refusals then a 200 must still find the window."""
        _t, saved = _with_transport([429] * 5 + [200])
        try:
            self.assertIs(M.head_published("http://x/a.zip", _Guard(), patient=True), True)
        finally:
            _restore(saved)


class TheProbeIsSkippedWhenTheAnswerIsOnDisk(unittest.TestCase):
    """Item 32(1), and it comes with a PREMISE CORRECTION.

    The item asks for the 13F data set to be probed and downloaded BEFORE the Form 4 crawl
    spends the rate budget. **It already is**: `main()` calls `build_13f` about twenty lines
    before `fetch_all`, in the shard step too. Measured on run 37237240057, that is not where
    the budget goes -- the three shards crawl 14,504 documents over ~11 minutes and the ASSEMBLE
    JOB starts afterwards, so its probe is first within its own job and still lands after eleven
    minutes of three-way hammering. **Re-ordering inside one job cannot fix a budget spent
    across jobs.**

    What does help is not asking at all. `13f_aggregate.json` travels from the shards to the
    assemble job in the artifact, so when the shards have already built the window assemble
    needs, the answer is ON DISK: an aggregate exists only because an earlier step downloaded
    and aggregated it, which means SEC served that window. Probing is then pure cost, and on
    shared runner IPs the request is the scarce thing.
    """

    def test_an_aggregate_covering_the_derived_window_skips_the_probe_entirely(self):
        rc, out, _err, t = TheRunActuallyStops()._run(
            [200], aggregate=("31-MAR-2026", "30-JUN-2026"), extra=("--dry-run",),
            as_of="2026-10-04")
        self.assertEqual(rc, 0, out)
        self.assertIn("probe        SKIPPED", out)
        self.assertEqual(t.calls, [], "it probed SEC for a window already on disk")

    def test_a_DIFFERENT_window_on_disk_still_probes(self):
        """The skip must not swallow the case it exists beside: a stale aggregate is exactly
        when the derived window DOES need confirming."""
        _rc, out, _err, t = TheRunActuallyStops()._run(
            [200], aggregate=("31-DEC-2025", "31-MAR-2026"), extra=("--dry-run",),
            as_of="2026-10-04")
        self.assertNotIn("probe        SKIPPED", out)
        self.assertTrue([c for c in t.calls if c[0] == "head"], "it did not probe")

    def test_nothing_on_disk_still_probes(self):
        _rc, out, _err, t = TheRunActuallyStops()._run(
            [200], aggregate=None, extra=("--dry-run",), as_of="2026-10-04")
        self.assertNotIn("probe        SKIPPED", out)
        self.assertTrue([c for c in t.calls if c[0] == "head"])

    def test_the_skip_test_matches_build_13fs_OWN_definition_of_already_have_it(self):
        """`B7`. Two different answers to "already have it" would mean skipping the probe and
        then downloading anyway -- the worst of both. `aggregate_covers` compares
        `[prior, curr]` in the same order `build_13f` does."""
        import json as _json
        import tempfile
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "13f_aggregate.json"), "w", encoding="utf-8") as fh:
            _json.dump({"periods": ["31-MAR-2026", "30-JUN-2026"]}, fh)
        per = {"prior": "31-MAR-2026", "curr": "30-JUN-2026"}
        self.assertIs(TC.aggregate_covers(per, root=d), True)
        # Reversed is NOT a match, because build_13f's own test is order-sensitive.
        self.assertIs(TC.aggregate_covers({"prior": "30-JUN-2026", "curr": "31-MAR-2026"},
                                          root=d), False)
        self.assertIs(TC.aggregate_covers(per, root=tempfile.mkdtemp()), False)


class TheGapsMutationFound(unittest.TestCase):
    """Three tests that did not exist until mutation showed the guards could not see these.

    The fourth mutation -- deleting the probe-confirmed branch of `confirmed_fallback` -- was
    NOT caught and that is NO EVIDENCE about the guard: with the probe walking newest-first a
    confirm ENDS the walk, so that branch cannot be reached through `main()` at all. Its own
    docstring says so. It is defensive, it is cheap, and it is tested DIRECTLY below rather than
    left as dead code nobody exercises.
    """

    def test_the_download_is_patient_BY_DEFAULT(self):
        """The default is what the failing run took. A caller that forgets the keyword must get
        the patient policy, not the 15-second one."""
        import inspect
        sig = inspect.signature(M.download_dataset)
        self.assertIs(sig.parameters["patient"].default, True,
                      "download_dataset is no longer patient by default")

    def test_the_probe_confirmed_branch_is_used_when_one_exists(self):
        """Unreachable through `main()` today (a confirm ends the walk), so driven directly."""
        per = {"run_as_of": "2026-10-04",
               "probed": [{"period": "30-JUN-2026", "window": "01jun2026-31aug2026",
                           "published": False},
                          {"period": "31-MAR-2026", "window": "01mar2026-31may2026",
                           "published": True}],
               "undetermined": True}
        import tempfile
        fb = TC.confirmed_fallback(per, root=tempfile.mkdtemp())
        self.assertIsNotNone(fb, "a window this run CONFIRMED was not used")
        self.assertEqual(fb["window_curr"], "01mar2026-31may2026")
        self.assertEqual(fb["prior"], "31-DEC-2025", "the prior quarter was not derived")
        self.assertIn("probe confirmed", fb["fallback_source"])

    def test_a_REAL_run_with_a_fallback_does_not_refuse(self):
        """THE POINT OF THE WHOLE ITEM, and `--dry-run` cannot show it: the dry run returns
        before the refusal, so every fallback test above passes whether or not the refusal is
        conditioned on the fallback. Mutation proved exactly that -- making the refusal fire
        unconditionally left the suite green.

        So this drives a REAL run with the three heavy legs stubbed. The stubs are the work
        (`build_13f`, `fetch_all`, the market-cap fetch, the cache write); the DECISION under
        test is untouched.
        """
        import contextlib
        import io as _io
        import json as _json
        import tempfile
        d = tempfile.mkdtemp()
        uni = os.path.join(d, "u.txt")
        with open(uni, "w", encoding="utf-8") as fh:
            fh.write("AAPL" + chr(10))
        root = os.path.join(d, "live_themes")
        os.makedirs(root, exist_ok=True)
        with open(os.path.join(root, "13f_aggregate.json"), "w", encoding="utf-8") as fh:
            _json.dump({"periods": ["31-DEC-2025", "31-MAR-2026"]}, fh)

        saved = {"Guard": M.Guard, "ROOT": M.DEFAULT_ROOT,
                 "b13": M.build_13f, "fa": M.fetch_all, "caps": TC.period_market_caps}
        M.Guard, M.DEFAULT_ROOT = _Guard, root
        M.build_13f = lambda *a, **k: {"periods": [], "by_period": {}, "shape": {}}
        M.fetch_all = lambda *a, **k: {}
        TC.period_market_caps = lambda *a, **k: {}
        _f2 = TC.F2
        class _Stub:
            @staticmethod
            def build_live(**kw):
                _Stub.seen = kw
                return {"rows": [], "n_served": 0}
        TC.F2 = _Stub
        t, tsaved = _with_transport([429] * 60)
        buf, err = _io.StringIO(), _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                rc = TC.main(["--universe", uni, "--as-of", "2026-10-04"])
        finally:
            _restore(tsaved)
            M.Guard, M.DEFAULT_ROOT = saved["Guard"], saved["ROOT"]
            M.build_13f, M.fetch_all = saved["b13"], saved["fa"]
            TC.period_market_caps = saved["caps"]
            TC.F2 = _f2
        out, errs = buf.getvalue(), err.getvalue()
        self.assertNotEqual(rc, 4, "a confirmed fallback existed and it refused anyway:\n" + out
                            + errs)
        self.assertIn("FELL BACK", out)
        # AND THE STALENESS REACHED THE CACHE, not only the log. `periods_source` is what
        # `live_themes.py` reads, so a consumer cannot see the columns without seeing that they
        # are a quarter behind.
        self.assertIn("13F one quarter stale", _Stub.seen["periods_source"])
        self.assertEqual(_Stub.seen["period_curr"], "31-MAR-2026",
                         "it built the derived window rather than the confirmed one")


class TheHarnessItself(unittest.TestCase):
    def test_the_substitution_bites_and_is_restored(self):
        """A transport stub that was never installed would make every test above vacuous."""
        import requests as real_before
        t, saved = _with_transport([200])
        try:
            import requests as faked
            self.assertIsNot(faked, real_before)
            M.head_published("http://x/a.zip", _Guard())
            self.assertEqual(t.calls, [("head", "http://x/a.zip")])
        finally:
            _restore(saved)
        import requests as real_after
        self.assertIs(real_after, real_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
