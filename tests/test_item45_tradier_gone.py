# -*- coding: utf-8 -*-
"""ITEM 45 - Tradier's account is gone, and a PRESENT token is not a WORKING token.

THE DEFECT WAS IN THREE PLACES AND IT IS ONE SENTENCE. `intraday/providers.get_provider`,
`screener/broker_universe.available` and `screener/broker_fundamentals.available` all answered
"have we got a broker?" with `bool(cfg.tradier_token)`. Don withdrew his funds, Tradier
deactivated the brokerage account, and the token stayed a non-empty string while every request
began answering `401 "Access Token not approved"`. So Tradier was still chosen; every
`TradierProvider` method swallows its exception into `None`; and the intraday run printed
`scored 0 of 150 names -- nothing scored -- not ingesting` and exited 1 (run 37853898863,
2026-10-08 22:31 UTC), with `/api/signals` frozen at 2026-10-08 00:20 and nothing alerting
because there is no `DISCORD_WEBHOOK_URL`.

TWO OF THIS ITEM'S OWN PREMISES WERE MEASURED FALSE AND THE TESTS RECORD IT:
  * the SANDBOX token is **ALIVE** (HTTP 200, returns bid/ask), so the fleet's paper fills and
    the options record's marking are NOT broken -- only the LIVE market-data token died;
  * so "stop the options record" has nothing to stop today. The stop is built anyway, because
    the sandbox hangs off the same login and a stop that first appears the day it is needed is
    a stop nobody has tested.

EVERY TEST HERE IS OFFLINE. `live_token_works` is driven by substituting its HTTP call, so the
suite asserts the DECISION rather than today's network weather -- a guard whose verdict depends
on whether a vendor is up is a guard that goes red for reasons unrelated to the code.
"""
from __future__ import annotations

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402

from valuation.data import tradier_health as TH                            # noqa: E402
from valuation.intraday import providers as P                              # noqa: E402
from tests.source_bounds import code_only                                  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Cfg:
    def __init__(self, token="t" * 28, env="live", paper=""):
        self.tradier_token = token
        self.tradier_env = env
        self.tradier_paper_token = paper


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._p = payload or {}

    def json(self):
        return self._p


def _fake_requests(status, payload=None, raises=None, seen=None):
    class _R:
        @staticmethod
        def get(url, **kw):
            if seen is not None:
                seen.append((url, kw))
            if raises:
                raise raises("boom")
            return _Resp(status, payload)
    return _R


class TheHealthCheckIsTheOneDefinition(unittest.TestCase):

    def setUp(self):
        TH.reset_cache()
        self.addCleanup(TH.reset_cache)

    def _with(self, fake):
        real = sys.modules.get("requests")
        sys.modules["requests"] = fake
        self.addCleanup(lambda: sys.modules.__setitem__("requests", real)
                        if real is not None else sys.modules.pop("requests", None))

    def test_no_token_is_answered_without_a_request(self):
        seen = []
        self._with(_fake_requests(200, seen=seen))
        ok, detail = TH.live_token_works(_Cfg(token=""))
        self.assertFalse(ok)
        self.assertIn("no TRADIER_TOKEN", detail)
        self.assertEqual(seen, [], "an absent token needs no network call")

    def test_a_working_token_passes_and_says_nothing(self):
        self._with(_fake_requests(200, {"quotes": {"quote": {"symbol": "AAPL"}}}))
        ok, detail = TH.live_token_works(_Cfg())
        self.assertTrue(ok)
        self.assertEqual(detail, "")

    def test_the_REAL_failure_401_is_a_dead_account_and_names_it(self):
        self._with(_fake_requests(
            401, {"fault": {"faultstring": "Access Token not approved"}}))
        ok, detail = TH.live_token_works(_Cfg())
        self.assertFalse(ok)
        self.assertIn("401", detail)
        self.assertIn("Access Token not approved", detail)

    def test_the_token_is_never_in_the_detail_even_if_the_vendor_echoes_it(self):
        """A vendor that quoted the key back would otherwise put it in a log line."""
        tok = "s" * 28
        self._with(_fake_requests(401, {"fault": {"faultstring": "bad key " + tok}}))
        ok, detail = TH.live_token_works(_Cfg(token=tok))
        self.assertFalse(ok)
        self.assertNotIn(tok, detail)
        self.assertIn("<REDACTED>", detail)

    def test_an_unreachable_host_is_reported_AS_UNREACHABLE_not_as_a_dead_token(self):
        """A network outage written down as a dead account would send Don to Tradier's
        website to fix something that is not broken."""
        self._with(_fake_requests(0, raises=ConnectionError))
        ok, detail = TH.live_token_works(_Cfg())
        self.assertFalse(ok, "uncertainty degrades to the free route -- the safe direction")
        self.assertIn("unreachable", detail)
        self.assertNotIn("401", detail)

    def test_a_non_auth_error_is_not_called_an_auth_error(self):
        self._with(_fake_requests(503))
        ok, detail = TH.live_token_works(_Cfg())
        self.assertFalse(ok)
        self.assertEqual(detail, "HTTP 503")

    def test_it_asks_ONCE_per_process_and_refresh_re_asks(self):
        seen = []
        self._with(_fake_requests(200, seen=seen))
        cfg = _Cfg()
        TH.live_token_works(cfg)
        TH.live_token_works(cfg)
        TH.live_token_works(cfg)
        self.assertEqual(len(seen), 1, "the hot scan asks twice; it must cost one request")
        TH.live_token_works(cfg, refresh=True)
        self.assertEqual(len(seen), 2)

    def test_the_cache_key_is_a_digest_and_not_the_token(self):
        """A module-level dict holding a live credential is one repr() from a log line."""
        tok = "k" * 28
        k = TH._key(tok, TH.LIVE_BASE)
        self.assertNotIn(tok, k)
        self.assertNotEqual(k, TH._key("k" * 27 + "x", TH.LIVE_BASE),
                            "two different tokens must not share a cache entry")
        self.assertNotEqual(k, TH._key(tok, TH.SANDBOX_BASE),
                            "the same token against a different host is a different question")

    def test_it_probes_the_endpoint_the_scan_actually_READS(self):
        """Passing on some other endpoint would mean 'something answered', not 'this works'."""
        seen = []
        self._with(_fake_requests(200, seen=seen))
        TH.live_token_works(_Cfg())
        url, kw = seen[0]
        self.assertTrue(url.endswith("/markets/quotes"), url)
        self.assertEqual(kw["params"]["symbols"], TH.PROBE_SYMBOL)
        self.assertIn("Authorization", kw["headers"])

    def test_live_and_sandbox_bases_are_chosen_by_env(self):
        self.assertEqual(TH.base_for(_Cfg(env="live")), TH.LIVE_BASE)
        self.assertEqual(TH.base_for(_Cfg(env="sandbox")), TH.SANDBOX_BASE)
        self.assertEqual(TH.base_for(_Cfg(env="")), TH.SANDBOX_BASE,
                         "the default is sandbox (config.py), and omitting the env is how "
                         "auto-scan.yml once sent a live token to the sandbox host")


class TheProviderFallsBackInsteadOfScoringNothing(unittest.TestCase):

    def setUp(self):
        TH.reset_cache()
        self.addCleanup(TH.reset_cache)

    def _health(self, ok, detail=""):
        real = TH.live_token_works
        TH.live_token_works = lambda *a, **k: (ok, detail)
        self.addCleanup(setattr, TH, "live_token_works", real)

    def test_a_DEAD_token_selects_the_free_provider_and_says_why(self):
        self._health(False, "HTTP 401: Access Token not approved")
        p = P.get_provider(_Cfg())
        self.assertIsInstance(p, P.FreeProvider)
        self.assertIn("401", p.degraded_reason)
        self.assertEqual(p.feed_delay, P.FREE_FEED_DELAY)

    def test_a_LIVE_token_still_selects_Tradier(self):
        """The positive control. Without it the fallback could be unconditional, which would
        silently downgrade the feed the day the account is restored."""
        self._health(True)
        p = P.get_provider(_Cfg())
        self.assertIsInstance(p, P.TradierProvider)
        self.assertEqual(p.degraded_reason, "")
        self.assertEqual(p.feed_delay, P.TRADIER_FEED_DELAY)

    def test_an_ABSENT_token_needs_no_probe_at_all(self):
        called = []
        real = TH.live_token_works
        TH.live_token_works = lambda *a, **k: (called.append(1), (False, "x"))[1]
        self.addCleanup(setattr, TH, "live_token_works", real)
        p = P.get_provider(_Cfg(token=""))
        self.assertIsInstance(p, P.FreeProvider)
        self.assertEqual(called, [])
        self.assertIn("no TRADIER_TOKEN", p.degraded_reason)

    def test_verify_False_reproduces_the_OLD_behaviour_exactly(self):
        """Offered so a caller that must not pay a probe can opt out -- and pinned, because an
        'additive' flag that quietly changed the default would be the opposite of additive."""
        called = []
        real = TH.live_token_works
        TH.live_token_works = lambda *a, **k: (called.append(1), (False, "x"))[1]
        self.addCleanup(setattr, TH, "live_token_works", real)
        p = P.get_provider(_Cfg(), verify=False)
        self.assertIsInstance(p, P.TradierProvider)
        self.assertEqual(called, [], "verify=False must not probe")

    def test_auth_ok_DELEGATES_rather_than_probing_twice(self):
        """B7. Two probes would be two answers to one question, and the second one drifts."""
        self._health(False, "HTTP 403")
        t = P.TradierProvider(_Cfg())
        self.assertEqual(t.auth_ok(), (False, "HTTP 403"))
        src = io.open(os.path.join(REPO, "valuation", "intraday", "providers.py"),
                      encoding="utf-8").read()
        # SLICED FORWARD FROM `auth_ok`, because `def get_bars` is defined on the BASE class
        # ABOVE it -- the first cut used `src.index("def get_bars")` and got an EMPTY slice,
        # so the assertion passed against nothing. A guard reading a zero-length region is a
        # guard that cannot fail.
        start = src.index("def auth_ok")
        body = src[start:src.index("def get_bars", start)]
        self.assertTrue(len(body) > 80, "the slice is empty, so this guard reads nothing")
        self.assertIn("tradier_health", body)
        self.assertNotIn("requests.get", code_only(body),
                         "auth_ok must not make its own request")

    def test_the_delay_is_recoverable_from_a_RECORDED_label(self):
        """`/api/signals` describes a run it did not make, so the delay has to come from the
        stored label -- not from whichever provider is selected now, or a page served after
        the token died would relabel yesterday's real-time rows as delayed."""
        self.assertEqual(P.delay_for_label("Tradier"), P.TRADIER_FEED_DELAY)
        self.assertEqual(P.delay_for_label("free (yfinance, delayed)"), P.FREE_FEED_DELAY)
        self.assertEqual(P.delay_for_label(""), "unknown")
        self.assertEqual(P.delay_for_label("Alpaca"), "unknown",
                         "an unknown vendor is unknown, not assumed real-time")


class TheOtherTwoCallSitesAskTheSameQuestion(unittest.TestCase):

    def setUp(self):
        TH.reset_cache()
        self.addCleanup(TH.reset_cache)

    def _health(self, ok, detail=""):
        real = TH.live_token_works
        TH.live_token_works = lambda *a, **k: (ok, detail)
        self.addCleanup(setattr, TH, "live_token_works", real)

    def test_broker_universe_available_follows_the_health_check(self):
        from valuation.screener import broker_universe as BU
        self._health(False, "HTTP 401")
        self.assertFalse(BU.available(_Cfg()))
        self._health(True)
        self.assertTrue(BU.available(_Cfg()))

    def test_broker_fundamentals_available_follows_the_health_check(self):
        from valuation.screener import broker_fundamentals as BF
        self._health(False, "HTTP 401")
        self.assertFalse(BF.available(_Cfg()))
        self._health(True)
        self.assertTrue(BF.available(_Cfg()))

    def test_a_PRESENT_token_with_a_FAILING_check_returns_False(self):
        """THE decisive case, and the one sentence that broke three paths.

        A substring ban cannot express this. The first cut banned
        `bool(getattr(cfg, "tradier_token"` as text and fired on the DOCSTRING that quotes it
        to explain the change; stripping strings does not help either, because the needle
        itself contains a string literal, so with strings gone it can never match. **The
        property is behavioural: a token that is PRESENT and does not WORK must answer no.**
        """
        from valuation.screener import broker_universe as BU
        from valuation.screener import broker_fundamentals as BF
        cfg = _Cfg(token="x" * 28)
        self.assertTrue(cfg.tradier_token, "the premise is a NON-EMPTY token")
        self._health(False, "HTTP 401: Access Token not approved")
        self.assertFalse(BU.available(cfg), "a dead token must not read as available")
        self.assertFalse(BF.available(cfg), "a dead token must not read as available")
        # And the positive control, so the functions are not simply returning False always.
        self._health(True)
        self.assertTrue(BU.available(cfg))
        self.assertTrue(BF.available(cfg))

    def test_both_DELEGATE_to_the_one_definition(self):
        """B7, as a positive property of the source rather than a ban on the old text."""
        for rel in ("valuation/screener/broker_universe.py",
                    "valuation/screener/broker_fundamentals.py"):
            src = io.open(os.path.join(REPO, rel), encoding="utf-8").read()
            body = src[src.index("def available"):]
            nxt = body.find("\ndef ")
            body = body[:nxt] if nxt > 0 else body
            self.assertIn("live_token_works", code_only(body, keep_strings=True), rel)

class TheScanReportsWhichFeedServedIt(unittest.TestCase):

    def test_the_payload_names_the_feed_its_delay_and_why(self):
        src = io.open(os.path.join(REPO, "valuation", "intraday", "scan.py"),
                      encoding="utf-8").read()
        for key in ('"feed_source"', '"feed_delay"', '"feed_degraded_reason"'):
            self.assertIn(key, src)

    def test_the_run_records_the_feed_that_SERVED_it(self):
        """DRIVEN. `intraday_runs.provider` read "Tradier" on runs Tradier served none of.

        The first cut asserted the expression appeared in `scan.py` -- and it appears TWICE
        (the save call and the returned payload), so mutating the save call left the other
        occurrence satisfying the test. **An `assertIn` over a whole file cannot pin WHICH
        call site uses the value.** So the store is stubbed and asked what it was handed.
        """
        from valuation.intraday import scan as SCAN

        saved = {}

        class _Store:
            def save_intraday(self, run_time, rows, provider=""):
                saved["provider"] = provider

        class _Prov:
            name = "Tradier"
            source_label = "free (yfinance, delayed)"
            feed_delay = "delayed about 15 minutes"
            degraded_reason = "Tradier rejected the token (HTTP 401)"

            def get_universe(self):
                return ["AAA"]

            def get_bars(self, t):
                return None          # nothing scores; the SAVE is what is under test

            def get_option_summary(self, t):
                return None

        res = SCAN.run_intraday(store=_Store(), provider=_Prov(), with_options=False,
                                save=True)
        self.assertEqual(saved.get("provider"), "free (yfinance, delayed)",
                         "the run must record the feed that served it, not the class name")
        # And the payload describes the same feed, so the log and the record cannot disagree.
        self.assertEqual(res["feed_source"], "free (yfinance, delayed)")
        self.assertEqual(res["provider"], "Tradier")
        self.assertIn("401", res["feed_degraded_reason"])

    def test_the_store_can_READ_the_column_it_has_always_written(self):
        from valuation.screener.store import Store
        self.assertTrue(hasattr(Store, "intraday_run"),
                        "the provider column existed and nothing read it")

    def test_nothing_scored_names_WHICH_source_failed(self):
        """DRIVEN WITH BOTH INPUTS, because mutation proved the grep version worthless.

        The first cut asserted the string `BOTH SOURCES PRODUCED NOTHING` appeared in
        `ci_scan.py`, and flipping the condition to a constant left it green -- the string sits
        there whether or not it can be reached. The decision is now a function, so it can be
        called with each input.
        """
        from scripts.ci_scan import nothing_scored_message
        free = nothing_scored_message("free (yfinance, delayed)")
        paid = nothing_scored_message("Tradier")
        self.assertIn("BOTH SOURCES PRODUCED NOTHING", free)
        self.assertNotIn("BOTH SOURCES", paid)
        self.assertIn("no fallback was used", paid)
        self.assertNotEqual(free, paid, "one message for both faults is the old defect")
        # An unrecorded source is not the free feed, so it must not claim both sources died.
        self.assertNotIn("BOTH SOURCES", nothing_scored_message(None))
        src = io.open(os.path.join(REPO, "scripts", "ci_scan.py"), encoding="utf-8").read()
        self.assertIn("feed_degraded_reason", src)
        # And the banner must no longer infer the feed from the token's presence -- checked on
        # CODE, because the comment above the fix quotes the expression it replaced.
        self.assertNotIn("'Tradier' if CONFIG.tradier_token else",
                         code_only(src, keep_strings=True))

    def test_the_page_has_somewhere_to_say_it(self):
        html = io.open(os.path.join(REPO, "valuation", "web", "templates", "index.html"),
                       encoding="utf-8").read()
        self.assertIn('id="sigFeed"', html)
        js = io.open(os.path.join(REPO, "valuation", "web", "static", "app.js"),
                     encoding="utf-8").read()
        self.assertIn('setHtml("sigFeed"', js)
        self.assertIn("not recorded for this run", js,
                      "a run with no recorded source must say so rather than be described "
                      "as real-time")


class TheOptionsRecordSTOPSRatherThanRecordingZeros(unittest.TestCase):

    def test_a_dead_quote_feed_is_a_declared_stop(self):
        """DRIVEN, not grepped. Mutation deleted the assignment and the grep version stayed
        green, because the message string was still sitting in the source."""
        from valuation.edge import paper_track as PT

        class _Store:
            pass

        class _Broker:
            def quotes(self, syms):
                return {}                      # the feed is dead: nothing comes back

            def order(self, *a, **k):
                return {}

        live = [{"alert_id": "a1", "occ_symbol": "AAPL261120C00250000",
                 "ticker": "AAPL", "state": "open"}]
        real_orders, real_ensure = PT.paper_orders, PT.ensure_schema
        self.addCleanup(setattr, PT, "paper_orders", real_orders)
        self.addCleanup(setattr, PT, "ensure_schema", real_ensure)
        PT.ensure_schema = lambda *a, **k: None
        PT.paper_orders = lambda store, **k: (live if k.get("states") else [])

        out = PT.mark_open(_Store(), _Broker())
        self.assertTrue(out["quote_feed_stopped"],
                        "a feed that quoted none of the live positions is a STOP")
        self.assertIn("STOPPED, not zero", out["stopped_reason"])
        self.assertEqual(out["marked"], 0, "and it must not invent a mark")

        # THE POSITIVE CONTROL: a feed that answers must NOT report a stop, or the flag could
        # be hard-coded True and the test above would still pass.
        class _Alive(_Broker):
            def quotes(self, syms):
                return {s: {"bid": 1.0, "ask": 1.2} for s in syms}

        real_update = PT._update
        self.addCleanup(setattr, PT, "_update", real_update)
        PT._update = lambda *a, **k: None
        out2 = PT.mark_open(_Store(), _Alive())
        self.assertFalse(out2["quote_feed_stopped"])
        self.assertEqual(out2["stopped_reason"], "")

    def test_it_still_refuses_to_invent_a_mark(self):
        """The pre-existing guarantee, pinned so the new reporting cannot replace it."""
        src = io.open(os.path.join(REPO, "valuation", "edge", "paper_track.py"),
                      encoding="utf-8").read()
        self.assertIn("if mark is not None:", src)


class TheAppendOnlyWriterSurvivesATransientRename(unittest.TestCase):
    """Owed from item 43's outside-lane report, and measured: 1 run in 10 of
    `tests/test_fleet_highwater.py` failed with WinError 32 on `os.replace`."""

    def test_a_transient_winerror_32_is_retried_and_then_succeeds(self):
        from valuation.edge import append_only as AO
        calls = []
        real = os.replace

        def flaky(a, b):
            calls.append(1)
            if len(calls) < 3:
                e = PermissionError("busy")
                e.winerror = 32
                raise e
            return real(a, b)

        os.replace = flaky
        self.addCleanup(setattr, os, "replace", real)
        import tempfile
        d = tempfile.mkdtemp(prefix="ao45-")
        import shutil
        self.addCleanup(shutil.rmtree, d, True)
        p = os.path.join(d, "x.csv")
        r = AO.append({"seq": "1", "v": "a"}, p, key="seq", columns=["seq", "v"])
        self.assertTrue(r.get("wrote"), r)
        self.assertEqual(len(calls), 3, "it must retry, not give up on the first failure")

    def test_a_REAL_permission_error_still_refuses(self):
        """The retry must not turn a genuine refusal into a half-second pause and the same
        failure. Only winerror 32 is transient; everything else raises at once."""
        from valuation.edge import append_only as AO
        calls = []
        real = os.replace

        def denied(a, b):
            calls.append(1)
            e = PermissionError("access denied")
            e.winerror = 5
            raise e

        os.replace = denied
        self.addCleanup(setattr, os, "replace", real)
        import tempfile
        import shutil
        d = tempfile.mkdtemp(prefix="ao45-")
        self.addCleanup(shutil.rmtree, d, True)
        r = AO.append({"seq": "1", "v": "a"}, os.path.join(d, "y.csv"),
                      key="seq", columns=["seq", "v"])
        self.assertFalse(r.get("wrote"))
        self.assertEqual(len(calls), 1, "a non-transient error must not be slept over")

    def test_the_retry_is_bounded(self):
        from valuation.edge import append_only as AO
        self.assertLessEqual(AO._REPLACE_TRIES, 8)
        self.assertLessEqual(AO._REPLACE_TRIES * AO._REPLACE_SLEEP_S, 1.0,
                             "a long retry turns a permission problem into a hang")


class TheCancelledTradierProposalIsNotInstallable(unittest.TestCase):
    """Don will not fund Tradier again (2026-10-08), so the seam measurement is cancelled."""

    def test_it_is_not_offered_for_installation(self):
        from scripts import propose_workflow as PW
        self.assertNotIn("tradier-seam.yml", PW.available(),
                         "a cancelled proposal must not be stageable for install_workflows")

    def test_the_tracked_copy_is_KEPT_and_marked_cancelled(self):
        """Nothing is discarded: the text stays readable, in a directory whose name says it
        must not be installed."""
        p = os.path.join(REPO, "scripts", "workflows", "cancelled", "tradier-seam.yml")
        self.assertTrue(os.path.exists(p), "the record of the proposal must survive")
        self.assertIn("workflow_dispatch", io.open(p, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
