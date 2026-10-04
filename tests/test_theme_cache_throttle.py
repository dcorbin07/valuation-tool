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

    def _run(self, plan, extra=()):
        import contextlib
        import io as _io
        import tempfile
        uni = os.path.join(tempfile.mkdtemp(), "u.txt")
        with open(uni, "w", encoding="utf-8") as fh:
            fh.write("AAPL\nMSFT\n")
        saved_guard = M.Guard
        M.Guard = _Guard                      # a no-op sleeper, so nothing waits
        t, saved = _with_transport(plan)
        buf, err = _io.StringIO(), _io.StringIO()
        try:
            with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
                rc = TC.main(["--universe", uni, *extra])
        finally:
            _restore(saved)
            M.Guard = saved_guard
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
                TC.main(["--universe", uni])
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
