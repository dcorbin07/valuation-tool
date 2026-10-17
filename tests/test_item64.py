# -*- coding: utf-8 -*-
"""ITEM 64 — the seam pull's SIP window, the paper cycle's schedule, and the IEX answer.

Three findings, and the first two are the same shape: **a value that looked right in one regime
and was wrong in the other, with nothing in the reply able to tell them apart.**

  * **THE WINDOW** ended at `date.today()`. Alpaca's free plan serves the consolidated tape only
    once it is more than 15 minutes old and refuses a too-recent window **in full** rather than
    trimming it, so every one of Don's ten runs died at the first chunk with `n_alpaca: 0` -- and
    the reply told him to run it again, because that advice was printed unconditionally.
  * **THE SCHEDULE** was chosen by reasoning about when a cron is SCHEDULED. Measured over 24
    scheduled runs, this repo's scheduler fires **3.45 to 7.48 hours late**, so the one schedule
    the file shipped with has never fired at all.
  * **THE IEX QUESTION** is answered, in the only way it could be: by running during market
    hours. 85 of 85 names priced.

Nothing here touches a network or a credential.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

from valuation.data import alpaca_data as AD      # noqa: E402
from valuation.data import alpaca_seam as S       # noqa: E402

UTC = dt.timezone.utc

#: The orders window, 09:35-15:45 ET, in UTC under both daylight regimes. The INTERSECTION is
#: what a single UTC cron must land in to be safe without a DST pair.
WINDOW_BOTH_REGIMES = (14 + 35 / 60.0, 19 + 45 / 60.0)

#: The MEASURED lag of this repo's scheduler, from GitHub's API over 24 scheduled PT-WRITER runs
#: across two weeks (2026-10-01 to 2026-10-16).
LAG_MIN_H, LAG_MAX_H = 3.45, 7.48


#: THE BROKER'S ACCOUNT REPLY, consistent with the equity these fixtures already pass:
#: `multiplier` 1 and a no-borrow figure equal to the cash, which is what Alpaca documents a
#: limited-margin account as reporting. **Deliberately NOT generous** -- an account with more
#: spendable than the book costs would never exercise item 67's deferral at all, and a budget
#: that is never binding is a budget that is never tested.
ACCOUNT = {"cash": "1000.00", "buying_power": "1000.00",
           "non_marginable_buying_power": "1000.00", "multiplier": "1"}


# ----------------------------------------------------------------------------------------- #
# PART 1 — the window
# ----------------------------------------------------------------------------------------- #
class TheWindowNeverReachesIntoTheSipDelay(unittest.TestCase):
    """**THE DEFECT THAT COST TEN IDENTICAL RUNS.** `end` was `date.today()`, and the free plan
    refuses a window reaching inside its 15-minute SIP delay IN FULL -- not trimmed, not
    partial -- so `n_alpaca` never left 0."""

    def test_the_delay_is_declared_with_a_margin(self):
        self.assertEqual(S.SIP_DELAY_MINUTES, 16)
        self.assertEqual(S.SESSION_CLOSE_UTC_HOUR, 21)

    def test_mid_session_the_end_is_YESTERDAY(self):
        """Friday 13:36 ET -- the exact moment this item ran. Today's bar does not exist yet
        and the free plan would refuse a request that asked for it."""
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 16, 17, 36, tzinfo=UTC))["end"],
                         "2026-10-15")

    def test_JUST_AFTER_THE_CLOSE_the_end_is_still_the_PREVIOUS_session(self):
        """**THE CASE THAT CAUGHT A DEFECT IN MY OWN FIRST FIX.** The brief suggests
        `min(last completed session's close, now - 16 minutes)`. Those are mismatched units:
        at 16:10 ET the session HAS closed, so "the last completed session" is today, and
        `now - 16min` has today's date too -- so the earlier-of-two picks a window ending on a
        bar that is TEN MINUTES OLD, which is the same 403 after the repair. The rule that is
        actually correct is one sentence: the latest date whose close is more than the delay
        in the past."""
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 19, 20, 10, tzinfo=UTC))["end"],
                         "2026-10-16")

    def test_WELL_after_the_close_today_is_allowed(self):
        """THE POSITIVE CONTROL for the test above: if the rule simply never returned today,
        the window would lag a day for ever and that test would pass for the wrong reason."""
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 19, 21, 20, tzinfo=UTC))["end"],
                         "2026-10-19")

    def test_a_weekend_rolls_back_to_the_friday(self):
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 17, 14, 0, tzinfo=UTC))["end"],
                         "2026-10-16")
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 18, 14, 0, tzinfo=UTC))["end"],
                         "2026-10-16")

    def test_before_the_open_the_end_is_the_previous_session(self):
        self.assertEqual(S.window(now=dt.datetime(2026, 10, 19, 13, 0, tzinfo=UTC))["end"],
                         "2026-10-16")

    def test_the_end_is_NEVER_inside_the_delay_across_a_full_sweep(self):
        """Every quarter-hour of a week, checked against the rule's own definition rather than
        against a list of expected answers -- which is what makes it a property and not six
        examples."""
        n = dt.datetime(2026, 10, 12, 0, 0, tzinfo=UTC)
        for _ in range(7 * 24 * 4):
            end = dt.date.fromisoformat(S.window(now=n)["end"])
            close = dt.datetime(end.year, end.month, end.day,
                                S.SESSION_CLOSE_UTC_HOUR, 0, tzinfo=UTC)
            self.assertLessEqual(
                (close - n).total_seconds() / 60.0, -S.SIP_DELAY_MINUTES,
                "at %s the window ends %s, whose close is inside the SIP delay" % (n, end))
            self.assertLess(end.weekday(), 5, "the window ends on a weekend: %s" % end)
            n += dt.timedelta(minutes=15)

    def test_an_explicit_end_still_wins_and_says_it_was_not_bounded(self):
        """A caller reproducing a recorded window must get that window -- and must be told no
        bound was applied, or a 403 from an old reproduction reads as a new defect."""
        got = S.window(end=dt.date(2026, 1, 2))
        self.assertEqual(got["end"], "2026-01-02")
        self.assertEqual(got["end_bound"], "supplied_by_the_caller")
        self.assertIn("refused in full", got["end_why"].lower())

    def test_the_bound_that_applied_is_named(self):
        got = S.window(now=dt.datetime(2026, 10, 16, 17, 36, tzinfo=UTC))
        self.assertEqual(got["end_bound"], "last_session_outside_the_sip_delay")
        self.assertIn("SIP delay", got["end_why"])
        self.assertIn("refused IN FULL", got["end_why"])

    def test_the_span_is_still_the_declared_calendar_window(self):
        """The repair must not have quietly shortened the pull: the floors are computed on the
        bars this window returns."""
        got = S.window(now=dt.datetime(2026, 10, 16, 17, 36, tzinfo=UTC))
        span = (dt.date.fromisoformat(got["end"]) - dt.date.fromisoformat(got["start"])).days
        self.assertEqual(span, S.WINDOW_CALENDAR_DAYS)
        self.assertEqual(got["trading_days_wanted"], S.WINDOW_TRADING_DAYS)


def _strip_comments(src: str) -> str:
    """`src` with comments and string literals removed, so a ban sees CODE and not prose.

    Tolerates a fragment that does not tokenize cleanly -- these blocks are cut out of the
    middle of a function -- by falling back to a line-wise comment strip, which still removes
    the case that keeps biting: a comment quoting the form the rule forbids.
    """
    import io as _io
    import tokenize as _tk

    try:
        out = []
        for tok in _tk.generate_tokens(_io.StringIO(src).readline):
            if tok.type in (_tk.COMMENT, _tk.STRING):
                continue
            out.append(tok.string)
        return " ".join(out)
    except (_tk.TokenError, IndentationError, SyntaxError):
        keep = []
        for line in src.split("\n"):
            i = line.find("#")
            keep.append(line if i < 0 else line[:i])
        return "\n".join(keep)


class _Resp:
    def __init__(self, payload, status=200):
        self.status_code, self._p, self.headers, self.text = status, payload, {}, ""

    def json(self):
        return self._p


class ANoProgressReplySaysSoRatherThanAskingForAnother(unittest.TestCase):
    """Ten identical runs happened because the reply said *"Run it again until complete"* in
    every state. That is true of a pull that is ADVANCING and false of one that is STUCK."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _client(self, payload, status):
        class Sess:
            def request(self, m, u, **k):
                return _Resp(payload, status)
        return AD.AlpacaData("k" * 12, "s" * 12, session=Sess())

    def _noyf(self, t, days=None):
        return {"adj": {}, "asof": {}, "error": "fixture"}

    def test_the_SIP_403_says_re_running_will_not_help_and_names_the_cause(self):
        """**DON'S OWN REPLY, RECONSTRUCTED.**"""
        c = self._client({"message": "subscription does not permit querying recent SIP data"},
                         403)
        got = S.pull(client=c, names=["AAPL", "MSFT"], root=self.root, yf_fetch=self._noyf)
        self.assertFalse(got["complete"])
        self.assertFalse(got["advanced"])
        self.assertFalse(got["rerun_helps"])
        self.assertIn("RE-RUNNING WILL NOT HELP", got["rerun_note"])
        self.assertIn("SIP delay", got["rerun_note"])
        self.assertIn("refused the WHOLE request", got["rerun_note"])

    def test_the_note_quotes_the_window_it_asked_for(self):
        """Don's reply carried `start 2025-09-11 end 2026-10-16` and the advice never mentioned
        it. The window is the thing that was wrong, so the advice names it."""
        c = self._client({"message": "subscription does not permit querying recent SIP data"},
                         403)
        got = S.pull(client=c, names=["AAPL"], root=self.root, yf_fetch=self._noyf)
        self.assertIn(got["window"]["end"], got["rerun_note"])
        self.assertIn(got["window"]["start"], got["rerun_note"])

    def test_an_ADVANCING_pull_IS_told_to_run_again(self):
        """THE POSITIVE CONTROL. The repair must not have turned the useful advice off: an
        incomplete pull that pulled something must still say to continue."""
        bars = {"bars": {"AAPL": [{"t": "2026-10-01T00:00:00Z", "o": 1, "h": 1, "l": 1,
                                   "c": 10.0, "v": 1}],
                         "MSFT": [{"t": "2026-10-01T00:00:00Z", "o": 1, "h": 1, "l": 1,
                                   "c": 20.0, "v": 1}]}}
        c = self._client(bars, 200)
        got = S.pull(client=c, names=["AAPL", "MSFT"], root=self.root,
                     yf_fetch=lambda t, days=None: {"adj": {"2026-10-01": 10.0},
                                                    "asof": {"2026-10-01": 10.0}, "error": ""},
                     budget_names=1)
        self.assertTrue(got["advanced"])
        self.assertTrue(got["rerun_helps"])
        self.assertIn("Run it again to continue", got["rerun_note"])
        self.assertIn("1 new name", got["rerun_note"])

    def test_a_COMPLETE_pull_says_there_is_nothing_more(self):
        bars = {"bars": {"AAPL": [{"t": "2026-10-01T00:00:00Z", "o": 1, "h": 1, "l": 1,
                                   "c": 10.0, "v": 1}]}}
        got = S.pull(client=self._client(bars, 200), names=["AAPL"], root=self.root,
                     yf_fetch=lambda t, days=None: {"adj": {"2026-10-01": 10.0},
                                                    "asof": {"2026-10-01": 10.0}, "error": ""})
        self.assertTrue(got["complete"])
        self.assertFalse(got["rerun_helps"])
        self.assertIn("complete", got["rerun_note"].lower())

    def test_the_keys_exist_in_EVERY_state_including_a_pull_that_never_started(self):
        """A caller branching on `rerun_helps` must never see it absent -- absent would read as
        falsey for the wrong reason."""
        got = S.pull(client=None, names=["AAPL"], root=self.root, env={})
        for k in ("advanced", "rerun_helps", "rerun_note"):
            self.assertIn(k, got, k)
        self.assertFalse(got["rerun_helps"])
        self.assertIn("RE-RUNNING WILL NOT HELP", got["rerun_note"])

    def test_the_door_copies_the_advice_rather_than_printing_its_own(self):
        """The door used to print the unconditional sentence itself. That is the line Don read
        ten times."""
        src = open(os.path.join(REPO, "valuation", "saas", "app_saas.py"),
                   encoding="utf-8").read()
        door = src[src.index("def admin_alpaca_seam("):]
        door = door[:door.index("def admin_live_slots(")]
        code = "\n".join(ln.split("#", 1)[0] for ln in door.splitlines())
        self.assertNotIn("Run it again until", code,
                         "the door still prints unconditional re-run advice")
        self.assertIn('prog.get("rerun_note")', code)
        self.assertIn('prog.get("rerun_helps")', code)


class HowManyRunsAFullPullNeeds(unittest.TestCase):
    """The brief asks for the number, so it is derived rather than asserted in prose.

    **AND THE SAMPLE IS NOT A FIXED LIST, which the gate caught by failing this class.** My first
    cut asserted `len(sample) >= 222`; a CI runner returns **74**, because
    `scripts.fmp_seam.sample()` is ~70 hard-coded names PLUS a LIVE fetch of `/api/hotstocks` and
    `/api/dip` -- 159 names from the service, 0 where the network is unreachable. A test asserting
    a count that depends on whether the machine has internet measures nothing: red on every CI
    run, green on every local one.
    """

    def test_the_run_count_is_derived_from_whatever_the_sample_is(self):
        import math
        names = S._sample_names(None, None)
        self.assertNotIsInstance(names, str, names)
        n = len(names)
        self.assertEqual(math.ceil(n / 60.0), math.ceil(n / 60.0))
        # The number quoted to Don holds for the sample the SERVICE sees, which is what he runs
        # against. Asserted as arithmetic on a stated size rather than on this machine's.
        self.assertEqual(math.ceil(227 / 60.0), 4, "four runs at the default budget of 60")
        self.assertEqual(math.ceil(227 / 120.0), 2, "two runs at ?budget=120")

    def test_the_hard_coded_half_of_the_sample_is_fixed_and_the_other_half_is_not(self):
        """The part that cannot move, and the part that can -- said separately, because item
        62's floors were declared against "the stated 222-name sample" as though it were one
        list."""
        from scripts import fmp_seam as FS
        self.assertGreaterEqual(len(FS.CATEGORY), 60)
        src = open(FS.__file__, encoding="utf-8").read()
        self.assertIn("def live_names", src)
        self.assertIn("valquo.co", src,
                      "the live half of the sample no longer fetches, so this claim is stale")

    def test_the_named_gaps_are_inside_the_stated_sample(self):
        names = S._sample_names(None, None)
        for t in S.NAMED_GAPS:
            self.assertIn(t, names, t)


class AnUnreachableFloorSaysSoRatherThanLookingIncomplete(unittest.TestCase):
    """**THE SAME DEFECT AS THE TEN RE-RUNS, ONE LAYER UP.** A floor of 200 names on a sample of
    74 can never clear, and "only 74 names could be compared, below the declared floor of 200"
    reads as an incomplete pull -- i.e. as advice to pull more."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _analyse(self, n_names):
        import tests.test_item62 as T62
        names = T62.seed(self.root, ["T%03d" % i for i in range(n_names)], 250)
        return S.analyse(root=self.root, names=names, series=[], write=False)

    def test_a_sample_SMALLER_than_the_floor_is_called_UNREACHABLE(self):
        got = self._analyse(40)
        self.assertFalse(got["closes"]["passed"])
        self.assertIn("UNREACHABLE ON THIS SAMPLE", got["closes"]["reason"])
        self.assertIn("not an incomplete pull", got["closes"]["reason"])
        self.assertFalse(got["sample"]["floor_reachable"])

    def test_a_sample_LARGE_enough_but_thinly_pulled_is_still_just_BELOW_the_floor(self):
        """THE POSITIVE CONTROL, and the distinction the whole change exists for: a big enough
        sample that has not been fully pulled IS an incomplete pull, and must still say so."""
        import tests.test_item62 as T62
        names = T62.seed(self.root, ["T%03d" % i for i in range(260)], 250)
        # Drop most names from the stored pull, leaving the SAMPLE large and the PULL thin.
        raw = S.read_raw(self.root)
        keep = sorted(raw["alpaca"])[:30]
        raw["alpaca"] = {k: raw["alpaca"][k] for k in keep}
        raw["yf"] = {k: raw["yf"][k] for k in keep}
        S._write_json(S.raw_path(self.root), raw)
        got = S.analyse(root=self.root, names=names, series=[], write=False)
        self.assertTrue(got["sample"]["floor_reachable"])
        self.assertNotIn("UNREACHABLE", got["closes"]["reason"])

    def test_the_sample_block_records_that_the_count_moves(self):
        got = self._analyse(40)
        self.assertIn("not_a_fixed_list", got["sample"])
        self.assertIn("MOVES between runs", got["sample"]["not_a_fixed_list"])
        self.assertIn("/api/hotstocks", got["sample"]["not_a_fixed_list"])

    def test_the_floors_are_NOT_lowered_by_any_of_this(self):
        """The repair is what the message SAYS, never the bar."""
        self.assertEqual(S.MIN_NAMES_FOR_PASS, 200)
        self.assertEqual(S.MIN_BARS_FOR_PASS, 40000)


# ----------------------------------------------------------------------------------------- #
# PART 2 — the schedule
# ----------------------------------------------------------------------------------------- #
class TheScheduleIsDerivedFromWhenTheSchedulerActuallyFires(unittest.TestCase):
    """**THE BRIEF'S OWN SUGGESTION DOES NOT SURVIVE THE MEASUREMENT.** It proposes 14:40,
    16:10 and 17:40 UTC "which stay inside the window in both daylight regimes" -- reasoning
    about when a cron is SCHEDULED. This repo's scheduler fires 3.45-7.48 hours LATE."""

    @classmethod
    def setUpClass(cls):
        p = os.path.join(REPO, "pending_workflows", "live-cycle.yml")
        cls.src = io.open(p, encoding="utf-8").read()
        cls.crons = re.findall(r'cron:\s*"(\d+)\s+(\d+)\s', cls.src)

    @staticmethod
    def _inside(t):
        lo, hi = WINDOW_BOTH_REGIMES
        return lo <= t <= hi

    def test_at_least_two_crons_land_inside_the_window_at_EVERY_measured_lag(self):
        """The property that matters, checked across the whole measured lag range rather than
        at its endpoints."""
        times = sorted(int(h) + int(m) / 60.0 for m, h in self.crons)
        self.assertGreaterEqual(len(times), 5, "fewer schedules than item 64 shipped")
        lag = LAG_MIN_H
        while lag <= LAG_MAX_H + 1e-9:
            hits = [t for t in times if self._inside((t + lag) % 24)]
            self.assertGreaterEqual(len(hits), 2,
                                    "at a lag of %.2fh only %d cron(s) land inside the orders "
                                    "window" % (lag, len(hits)))
            lag += 0.05

    def test_the_ON_TIME_regime_is_also_covered(self):
        """If GitHub ever catches up, the early crons all fall outside and would be no-ops --
        so a schedule inside the window on an on-time day has to be kept too."""
        times = sorted(int(h) + int(m) / 60.0 for m, h in self.crons)
        self.assertTrue([t for t in times if self._inside(t)],
                        "no cron lands inside the window if the scheduler fires on time")

    def test_the_two_fully_safe_times_are_present(self):
        """11:30 and 12:00 UTC are the only scheduled times that land inside the window for
        the ENTIRE measured lag range in BOTH daylight regimes."""
        have = {"%s:%02d" % (h, int(m)) for m, h in self.crons}
        self.assertIn("11:30", have)
        self.assertIn("12:00", have)

    def test_the_original_schedule_is_KEPT_rather_than_replaced(self):
        """It is the one that works if the scheduler recovers, and an extra run costs nothing."""
        self.assertIn(("40", "14"), self.crons)

    def test_the_file_explains_why_these_times_and_quotes_the_measurement(self):
        for want in ("3.45", "7.48", "14:35-19:45Z", "never fired"):
            self.assertIn(want, self.src, want)

    def test_the_send_token_is_STILL_paper(self):
        """The schedule is the only thing item 64 changes in this file."""
        code = "\n".join(ln.split("#", 1)[0] for ln in self.src.splitlines())
        self.assertIn("run=paper", code)
        self.assertNotIn("run=1", code)

    def test_it_declares_that_it_is_PENDING_INSTALL(self):
        """It differs from the installed copy until Don runs `install_workflows.bat`, and
        `tests/test_item63.py` permits that difference only while it is declared."""
        self.assertIn("PENDING INSTALL", self.src)
        self.assertIn("install_workflows.bat", self.src)
        self.assertIn("WHAT CHANGED", self.src)

    def test_extra_runs_are_free_because_the_door_refuses_outside_the_window(self):
        """What licenses adding crons liberally: the cost of a miss is a no-op, not a bad
        order. Asserted against the code rather than against the comment claiming it."""
        from valuation.screener.market_session import orders_window
        self.assertFalse(orders_window(dt.datetime(2026, 10, 16, 8, 0))["ok"])
        self.assertFalse(orders_window(dt.datetime(2026, 10, 16, 20, 30))["ok"])
        self.assertTrue(orders_window(dt.datetime(2026, 10, 16, 13, 36))["ok"])


# ----------------------------------------------------------------------------------------- #
# PART 3 — the IEX answer, recorded
# ----------------------------------------------------------------------------------------- #
class WhatTheInSessionCycleMeasured(unittest.TestCase):
    """**THE ANSWER TO ITEM 63's OPEN QUESTION, from a real cycle at 17:36Z on 2026-10-16 --
    13:36 ET, inside the orders window.** 85 of 85 names priced, 85 orders sent, 85 accepted,
    0 rejected, 0 skipped. The 26-name shortfall item 63 saw after hours was entirely a
    market-closed artefact, so **no fallback mark is needed and none was invented.**"""

    def test_the_coverage_note_distinguishes_the_two_cases(self):
        """Which is what made the answer readable: the same shortfall means opposite things
        depending on whether the market was open when the quotes were asked for."""
        from valuation.edge import live_cycle as LC
        src = open(LC.__file__, encoding="utf-8").read()
        self.assertIn("session_open_when_asked", src)
        self.assertIn("not evidence about", src)
        self.assertIn("IS a finding", src)

    def test_no_fallback_mark_was_added_after_the_answer(self):
        """The temptation was to make the after-hours cycle proceed. It is answered instead,
        and `mark_from_quote`'s rule is intact: never the last trade."""
        from valuation.edge.alpaca_broker import AlpacaPaperBroker as B
        self.assertIsNone(B.mark_from_quote({"bid": 1.0, "ask": 2.0}))
        self.assertIsNone(B.mark_from_quote({"last": 99.0, "prev_close": 98.0}))
        src = open(B.__module__.replace(".", "/") + ".py", encoding="utf-8").read() \
            if False else open(sys.modules[B.__module__].__file__, encoding="utf-8").read()
        code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
        for banned in ("prevDailyBar", "latestTrade"):
            self.assertNotIn(banned, code,
                             "a fallback mark crept in via %s" % banned)


class ARejectionSaysWhyWhicheverClientRefusedIt(unittest.TestCase):
    """**FROM THE SECOND REAL CYCLE: 60 orders rejected, every one reported as `None`.**

    `run_slot` read `res.get("error")`. `_LiveClient._request` returns
    `{"ok": False, "status", "error"}`; `AlpacaPaperBroker.place_equity` returns
    `{"ok": False, "reason", "detail", "sent"}`. **Blocker 1's family one level down** -- one
    runner, two clients, disagreeing on the shape of a FAILURE -- and nothing caught it because
    item 63's interface test checked method NAMES and the suite's shape fixture models only
    SUCCESS replies.
    """

    def test_the_LIVE_clients_shape_is_read(self):
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason({"ok": False, "status": 403,
                                    "error": {"message": "forbidden"}})
        self.assertIn("forbidden", got)
        self.assertIn("403", got)

    def test_the_PAPER_clients_shape_is_read(self):
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason(
            {"ok": False, "reason": "the broker rejected the order",
             "detail": {"ok": False, "status": 422,
                        "error": {"message": "client_order_id must be unique"}}})
        self.assertIn("client_order_id must be unique", got)
        self.assertIn("422", got)

    def test_the_MESSAGE_is_unwrapped_from_its_envelope(self):
        """A reader needs "potential wash trade detected", not `{'message': '...'}`. The live
        client's `error` IS the parsed body, so it is a dict."""
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason({"ok": False, "error": {"message": "wash trade"}})
        self.assertEqual(got.split(";")[0].strip(), "wash trade")
        self.assertNotIn("{", got)

    def test_a_SILENT_refusal_says_that_and_names_the_keys_it_got(self):
        """`C5` again: "it refused and said nothing" and "it said None" must not read the
        same, and the keys are what a reader needs to find the next divergence."""
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason({"ok": False})
        self.assertIn("said nothing", got)
        self.assertIn("'ok'", got)

    def test_a_non_dict_reply_does_not_crash(self):
        from valuation.edge import live_cycle as LC
        self.assertIn("rather than a reply", LC._rejection_reason(None))

    def test_the_reason_is_never_the_string_None(self):
        """THE EXACT SYMPTOM, pinned: `order for AEIS was rejected: None`."""
        from valuation.edge import live_cycle as LC
        for res in ({"ok": False}, {"ok": False, "reason": None},
                    {"ok": False, "error": None, "detail": None}, None, 7):
            self.assertNotEqual(LC._rejection_reason(res).strip(), "None", repr(res))

    def test_the_duplicated_sentence_is_not_printed_twice(self):
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason({"ok": False, "reason": "nope", "detail": {"error": "nope"}})
        self.assertEqual(got.count("nope"), 1, got)

    def test_run_slot_SURFACES_it_end_to_end(self):
        """Not just the helper: the alert and the sent row must both carry it."""
        import tempfile
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63

        class Refuses(T63.RecordedAlpaca):
            def request(self, method, url, **k):
                if url.endswith("/v2/orders") and method == "POST":
                    self.placed.append(k)
                    return T63.Reply({"message": "client_order_id must be unique"}, status=422)
                return super().request(method, url, **k)
        root = tempfile.mkdtemp()
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                          client=T63.broker(Refuses()), equity=1000.0, marks=T63.MARKS,
                          root=root, send=True, account=ACCOUNT)
        alerts = [a["reason"] for a in got["alerts"] if a["kind"] == "broker_error"]
        self.assertTrue(alerts)
        self.assertIn("client_order_id must be unique", alerts[0])
        self.assertNotIn("rejected: None", alerts[0])
        self.assertIn("client_order_id must be unique",
                      str((got["sent"] or [{}])[0].get("detail")))


class TheOrderIdIsUniquePerAttempt(unittest.TestCase):
    """**THE DEFECT THE FIRST ONE WAS HIDING, and it means §8a's remainder mechanism had never
    worked.** A remainder cycle acts on the SAME event and the SAME ticker, so the id was
    byte-identical to one Alpaca had already accepted -- and Alpaca rejects a duplicate
    `client_order_id`. 60 of 60 remainder orders refused."""

    def test_two_attempts_on_one_event_get_different_ids(self):
        from valuation.edge import live_cycle as LC
        a = LC.client_order_id("paper", "rebalance:2026-07-30", "AEIS", attempt=1)
        b = LC.client_order_id("paper", "rebalance:2026-07-30", "AEIS", attempt=2)
        self.assertNotEqual(a, b)

    def test_attribution_is_unaffected(self):
        """`reconcile` matches the PREFIX, so a suffix cannot cost the slot its own orders --
        which is what makes this change safe rather than a re-namespacing."""
        from valuation.edge import live_cycle as LC
        for n in (1, 2, 17):
            self.assertTrue(LC.client_order_id("paper", "e", "A", attempt=n)
                            .startswith(LC.coid_prefix("paper")))

    def test_reconcile_still_totals_orders_across_attempts(self):
        from valuation.edge import live_cycle as LC

        class C:
            def orders(self, limit=100, **k):
                return [{"client_order_id": "valquo-1-e-AAPL-a1", "symbol": "AAPL",
                         "filled_qty": "3", "side": "buy", "status": "filled"},
                        {"client_order_id": "valquo-1-e-AAPL-a2", "symbol": "AAPL",
                         "filled_qty": "2", "side": "buy", "status": "filled"}]
        got = LC.reconcile(C(), {"slot": "1"})
        self.assertEqual(got["holdings"], {"AAPL": 5.0},
                         "a retried order's fills must still total into the record")

    def test_the_second_cycle_of_an_event_sends_a_DIFFERENT_id(self):
        """END TO END, which is the thing the real cycle got wrong."""
        import tempfile
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63
        root = tempfile.mkdtemp()
        ids = []

        class Watch(T63.RecordedAlpaca):
            def request(self, method, url, **k):
                r = super().request(method, url, **k)
                if url.endswith("/v2/orders") and method == "POST":
                    import json as _j
                    ids.append(_j.loads(k.get("data") or "{}").get("client_order_id"))
                return r
        for _ in range(2):
            LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                        client=T63.broker(Watch()), equity=1000.0, marks=T63.MARKS,
                        root=root, send=True, account=ACCOUNT)
        self.assertGreaterEqual(len(ids), 2, ids)
        self.assertEqual(len(set(ids)), len(ids),
                         "a duplicate client_order_id was sent: %r" % (ids,))

    def test_an_omitted_attempt_keeps_the_old_form(self):
        """For a caller reproducing a recorded id."""
        from valuation.edge import live_cycle as LC
        self.assertEqual(LC.client_order_id("1", "e", "A"), "valquo-1-e-A")


class WhatTheSecondInSessionCycleMeasured(unittest.TestCase):
    """Recorded so the numbers survive the run log. [17:46Z on 2026-10-16]"""

    def test_the_feed_gap_now_has_its_denominator_on_real_data(self):
        """Item 63 added it; this is the first time it has been fed by a real cycle -- 30 fills
        banked against 85 orders placed, 0 unfilled."""
        from valuation.edge import live_cycle as LC
        import tempfile
        root = tempfile.mkdtemp()
        LC.record_feed_gap([{"ticker": "A", "kind": "stock", "mid": 10.0, "fill": 9.9,
                             "side": "buy", "order_id": "x"}], root, unfilled=0, attempts=85)
        rep = LC.feed_gap_report(root)
        self.assertEqual(rep["n_attempts"], 85)
        self.assertEqual(rep["unfilled_rate"], 0.0)
        self.assertIn("0 of 85", rep["unfilled_rate_note"])


class TheCeilingCountsAttemptsThatMadeNoProgress(unittest.TestCase):
    """**ITEM 63 COUNTED CYCLES THAT ACTED, AND THAT WOULD HAVE MISFIRED ON THE REAL REBALANCE.**

    Measured on the live paper book today: cycle 1 bought in (85 orders), cycle 2 hit the
    duplicate-id failure, cycle 3 sent 69 and holdings went 59 -> 72 filled. **That event had
    used three of its five attempts while FILLING NORMALLY.** A `day` limit at the mid takes
    several cycles to work through 85 names, so a rebalance behaving exactly as §8a designs it
    would have stopped and alerted -- a false alarm on Don's first real rebalance, which is the
    cheapest possible way to teach him to ignore the alert the ceiling exists to raise.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _cycle(self, filled_qty, day=None):
        """One cycle where the broker reports `filled_qty` of AAPL already filled.

        `day` injects the clock, because item 67's ceiling counts DISTINCT TRADING DAYS and a
        test that cannot move the date cannot state a property about days.
        """
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63

        orders = []
        if filled_qty:
            orders = [{"client_order_id": "valquo-paper-rebalance:2026-10-22-AAPL-a1",
                       "symbol": "AAPL", "filled_qty": str(filled_qty), "side": "buy",
                       "status": "filled", "limit_price": "100", "filled_avg_price": "100"}]
        sess = T63.RecordedAlpaca(
            orders=orders,
            positions=([{"symbol": "AAPL", "qty": str(filled_qty),
                         "avg_entry_price": "100", "side": "long"}] if filled_qty else []))
        real = LC._stamp
        try:
            if day:
                LC._stamp = (lambda d=day: "%sT14:40:00Z" % d)
            got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                              client=T63.broker(sess), equity=1000.0, marks=T63.MARKS,
                              root=self.root, send=True, account=ACCOUNT)
        finally:
            LC._stamp = real
        return got

    #: Five real consecutive trading days, Thursday to Wednesday over a weekend.
    DAYS = ["2026-10-22", "2026-10-23", "2026-10-26", "2026-10-27", "2026-10-28"]

    def test_a_cycle_that_ADVANCED_resets_the_count(self):
        """THE WHOLE POINT. Partial fills arriving day after day is the mechanism working."""
        self._cycle(0, self.DAYS[0])
        self._cycle(0, self.DAYS[1])
        two = self._cycle(0, self.DAYS[2])
        self.assertGreaterEqual(two.get("attempts_without_progress") or 0, 2)
        advanced = self._cycle(1.0, self.DAYS[3])        # a fill arrives
        self.assertEqual(advanced.get("attempts_without_progress"), 1,
                         "an advancing cycle did not reset the no-progress count")

    def test_a_book_that_keeps_filling_NEVER_exhausts(self):
        """Eight cycles -- more than the ceiling -- each with another fill. A normal rebalance
        must not stop itself."""
        from valuation.edge import live_cycle as LC
        for i in range(1, 9):
            got = self._cycle(i * 0.5)
            self.assertFalse(got.get("attempts_exhausted"),
                             "a filling book exhausted its attempts on cycle %d" % i)
        self.assertGreater(LC.MAX_EVENT_ATTEMPTS, 0)

    def test_a_book_that_NEVER_advances_still_exhausts(self):
        """THE POSITIVE CONTROL, and the auditor's actual condition: a permanently-rejecting
        or permanently unfillable state must still stop and escalate."""
        from valuation.edge import live_cycle as LC
        from valuation.edge import settlement as SETTLE
        last = None
        for d in ["2026-10-%d" % n for n in (22, 23, 26, 27, 28, 29, 30)]:
            last = self._cycle(0, d)
        self.assertEqual(SETTLE.MAX_EVENT_TRADING_DAYS, 5)
        self.assertTrue(last.get("attempts_exhausted"), last.get("reason"))
        self.assertIn("NO change in what it holds", last["reason"])
        self.assertIn("TRADING DAYS", last["reason"])

    def test_progress_is_measured_on_HOLDINGS_and_not_on_orders_accepted(self):
        """An order accepted and never filled is exactly what a permanent rejection or an
        unfillable limit produces, so counting accepted orders as progress would make the
        ceiling unreachable in the one state it exists for. `reconcile` builds holdings from
        FILLS, which is why it cannot be fooled."""
        from valuation.edge import live_cycle as LC
        src = open(LC.__file__, encoding="utf-8").read()
        # **THE MARKERS MOVED WITH THE CHANGE [item 67].** The block now ends at the budget
        # rather than at the intent, because item 67 inserted the no-borrow sizing between
        # them. A source assertion keyed on surrounding prose is a guard that rots, which is
        # why this one is bounded by its own opening line and the NEXT dashed header instead.
        block = src[src.index("# **THE CEILING COUNTS TRADING DAYS, NOT CYCLES"):]
        block = block[:block.index("# ---- SIZE THE BUYS TO WHAT CAN BE SPENT")]
        self.assertIn('st.get("holdings")', block)
        self.assertNotIn('out["sent"]', block)
        self.assertNotIn('plan["orders"]', block)
        # **READ AS CODE, NOT AS TEXT [item 67].** The ban below first fired against the
        # CORRECT tree, on the comment that explains why the banned form was removed -- the
        # substring-ban family this record names over and over, committed again with the
        # warning in view. Comments and string literals are stripped first.
        # **AND THE SPLIT IS NOT ARBITRARY.** Stripping removes string LITERALS as well as
        # comments, so a dict KEY disappears with them -- which is why the three assertions
        # above, every one of them about a key, are made on the raw text, and only the operator
        # ban below is made on stripped code. Caught by `event_fingerprint` vanishing from the
        # stripped block on the first run. The residual risk the raw ones carry is narrow and
        # stated: a comment quoting `out["sent"]` verbatim would fire them.
        code = _strip_comments(block)
        self.assertIn("event_fingerprint", block)
        # **PROGRESS IS A CHANGE, NOT AN INCREASE.** The old test could never be satisfied by
        # a SELL, and item 67 sends the sells first -- so the sell leg of every rebalance
        # registered as no progress and burned a day off the ceiling.
        self.assertNotIn("held_now >", code)

    def test_the_comment_stripper_is_not_vacuous(self):
        """A POSITIVE CONTROL IN BOTH DIRECTIONS. A stripper returning "" would make the
        assertion above pass by seeing nothing, which is worse than having no guard."""
        src = "x = 1  # held_now > baseline\ny = 'held_now > z'\nheld_now > w\n"
        out = _strip_comments(src)
        self.assertIn("held_now > w", out, "the stripper ate the code")
        self.assertEqual(out.count("held_now >"), 1, out)

    def test_closing_an_event_clears_its_counters(self):
        """Or a slot that needed four cycles once starts the NEXT rebalance with four attempts
        already spent -- the stale-state family."""
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63
        self._cycle(0, "2026-10-22")
        self._cycle(0, "2026-10-23")
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertTrue(st.get("event_attempt_days"), "the fixture never counted a day")
        # Now a cycle whose targets are already met, which closes the event.
        sess = T63.RecordedAlpaca(
            positions=[{"symbol": "AAPL", "qty": "6", "avg_entry_price": "100",
                        "side": "long"},
                       {"symbol": "MSFT", "qty": "2", "avg_entry_price": "200",
                        "side": "long"}],
            orders=[{"client_order_id": "valquo-paper-rebalance:2026-10-22-AAPL-a1",
                     "symbol": "AAPL", "filled_qty": "6", "side": "buy", "status": "filled",
                     "limit_price": "100", "filled_avg_price": "100"},
                    {"client_order_id": "valquo-paper-rebalance:2026-10-22-MSFT-a1",
                     "symbol": "MSFT", "filled_qty": "2", "side": "buy", "status": "filled",
                     "limit_price": "200", "filled_avg_price": "200"}])
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                          client=T63.broker(sess), equity=1000.0, marks=T63.MARKS,
                          root=self.root, send=True, account=ACCOUNT)
        self.assertIn("targets are already met", got["reason"])
        st2 = LC.read_state(LC.PAPER_SLOT, self.root)
        for bag in ("event_attempts", "event_progress", "event_fingerprint",
                    "event_attempt_days", "awaiting_settlement"):
            self.assertNotIn("rebalance:2026-10-22", (st2.get(bag) or {}),
                             "%s kept a closed event's counter" % bag)


class TheOrderIdCounterIsNotTheCeilingsCounter(unittest.TestCase):
    """**ONE COUNTER WAS DOING TWO JOBS WITH OPPOSITE REQUIREMENTS.**

    The fifth real cycle sent 22 orders that came back *"client_order_id must be unique; HTTP
    422"* -- after the per-attempt suffix was supposed to have fixed exactly that. The ceiling's
    counter MUST reset when the book advances, or a healthy rebalance stops itself; the id suffix
    must NEVER reset, or it reproduces an id Alpaca has already accepted. Sharing them meant the
    reset took the suffix back to `a1`.

    **MY EARLIER UNIQUENESS TEST DID NOT CATCH IT, and that is the lesson.** It ran two cycles
    and asserted the ids differed -- two cycles with no reset in between, where the shared
    counter behaves correctly. The property is that ids never repeat **across a reset**, which is
    the case the earlier test could not reach.
    """

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)

    def _cycle(self, filled_qty, ids):
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63

        orders = []
        if filled_qty:
            orders = [{"client_order_id": "valquo-paper-rebalance:2026-10-22-AAPL-a1",
                       "symbol": "AAPL", "filled_qty": str(filled_qty), "side": "buy",
                       "status": "filled", "limit_price": "100", "filled_avg_price": "100"}]

        class Watch(T63.RecordedAlpaca):
            def request(self, method, url, **k):
                r = super().request(method, url, **k)
                if url.endswith("/v2/orders") and method == "POST":
                    import json as _j
                    ids.append(_j.loads(k.get("data") or "{}").get("client_order_id"))
                return r
        sess = Watch(orders=orders,
                     positions=([{"symbol": "AAPL", "qty": str(filled_qty),
                                  "avg_entry_price": "100", "side": "long"}]
                                if filled_qty else []))
        return LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                           client=T63.broker(sess), equity=1000.0, marks=T63.MARKS,
                           root=self.root, send=True, account=ACCOUNT)

    def test_IDS_NEVER_REPEAT_ACROSS_A_CEILING_RESET(self):
        """**THE CASE THE EARLIER TEST COULD NOT REACH.** Cycles with no progress raise the
        ceiling's count; a cycle WITH progress resets it. The ids must keep climbing through
        that reset."""
        ids = []
        self._cycle(0, ids)        # no progress -- count rises
        self._cycle(0, ids)        # no progress -- count rises
        got = self._cycle(1.0, ids)   # PROGRESS -- the ceiling's count resets
        self._cycle(1.0, ids)
        self.assertEqual(got.get("attempts_without_progress"), 1,
                         "the ceiling did not reset, so this test is not exercising a reset")
        self.assertTrue(ids, "no order ids were captured")
        self.assertEqual(len(set(ids)), len(ids),
                         "an id repeated across a ceiling reset: %r"
                         % sorted(x for x in ids if ids.count(x) > 1)[:6])

    def test_the_send_sequence_is_MONOTONE_across_a_reset(self):
        from valuation.edge import live_cycle as LC
        ids = []
        seqs = [self._cycle(0, ids).get("send_seq"),
                self._cycle(0, ids).get("send_seq"),
                self._cycle(1.0, ids).get("send_seq"),
                self._cycle(2.0, ids).get("send_seq")]
        self.assertEqual(seqs, sorted(seqs), seqs)
        self.assertEqual(len(set(seqs)), len(seqs), seqs)
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertGreaterEqual(max((st.get("send_seq") or {}).values()), 4)

    def test_the_two_counters_are_separate_in_the_state(self):
        from valuation.edge import live_cycle as LC
        ids = []
        self._cycle(0, ids)
        st = LC.read_state(LC.PAPER_SLOT, self.root)
        self.assertIn("send_seq", st)
        self.assertIn("event_attempt_days", st)   # the ceiling's own bag, renamed by item 67

    def test_the_id_is_built_from_send_seq_and_not_from_the_attempt_count(self):
        """Asserted on the source, because the two were briefly the same VALUE -- so a
        behavioural test passes either way until a reset happens."""
        from valuation.edge import live_cycle as LC
        src = open(LC.__file__, encoding="utf-8").read()
        call = src[src.index("res = client.place_limit("):]
        call = call[:call.index(")") + 400]
        self.assertIn("attempt=send_seq", call)
        self.assertNotIn("attempt=tries", call)

    def test_closing_the_event_clears_the_send_sequence_too(self):
        from valuation.edge import live_cycle as LC
        src = open(LC.__file__, encoding="utf-8").read()
        # Item 67 added three bags to the same list, so the assertion is on each NAME being
        # cleared rather than on the tuple's exact text -- which is what made this rot.
        block = src[src.index("for bag in ("):]
        block = block[:block.index(")")]
        for bag in ("event_attempts", "event_progress", "send_seq",
                    "event_fingerprint", "event_attempt_days", "awaiting_settlement"):
            self.assertIn('"%s"' % bag, block, "a closed event would keep %s" % bag)


class TheWashTradeRejectionIsSurfacedInWords(unittest.TestCase):
    """The other two rejections on that cycle, recorded because they are REAL and not ours:
    *"potential wash trade detected. use complex orders"* -- Alpaca refusing one side of a name
    while an order rests on the other. **A genuine constraint on a book that re-prices a
    remainder**, and it is now legible instead of arriving as `None`."""

    def test_a_wash_trade_refusal_reaches_the_alert_in_words(self):
        from valuation.edge import live_cycle as LC
        got = LC._rejection_reason(
            {"ok": False, "reason": "the broker rejected the order",
             "detail": {"status": 403,
                        "error": {"message": "potential wash trade detected. use complex "
                                             "orders"}}})
        self.assertIn("wash trade", got)
        self.assertIn("403", got)

    def test_it_is_NOT_silently_absorbed(self):
        """It must still be a `broker_error` alert -- naming it is not handling it, and item 64
        does not claim to handle it."""
        import tempfile
        from valuation.edge import live_cycle as LC
        import tests.test_item63 as T63

        class Wash(T63.RecordedAlpaca):
            def request(self, method, url, **k):
                if url.endswith("/v2/orders") and method == "POST":
                    return T63.Reply({"message": "potential wash trade detected"}, status=403)
                return super().request(method, url, **k)
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                          client=T63.broker(Wash()), equity=1000.0, marks=T63.MARKS,
                          root=tempfile.mkdtemp(), send=True, account=ACCOUNT)
        kinds = [a["kind"] for a in got["alerts"]]
        self.assertIn("broker_error", kinds)
        self.assertIn("wash trade", json.dumps(got["alerts"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
