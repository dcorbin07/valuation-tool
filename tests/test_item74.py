# -*- coding: utf-8 -*-
"""ITEM 74 — send every breakage, and every rebalance that can't happen, to Don on Discord.

Don's rulings, 2026-10-18:

  * **two channels** — problems to `#valquo-alerts`, routine posts where they are today;
  * **an outside monitor** (healthchecks.io), because nothing inside GitHub can report that
    GitHub stopped running jobs, and it has happened once;
  * **the noise rule** — one post when a problem starts, one when it clears, one reminder per
    day while it stays broken;
  * **nothing private, ever** — no P&L, return or verdict; no key, token or webhook URL; no
    account number.

**THIS ITEM CHANGES WHERE MESSAGES GO AND NOTHING ELSE**, so the first class below pins that
every order plan is identical before and after. If that fails, nothing else here matters.

**THE REGISTRY TEST IS THE ONE THAT OUTLIVES THIS ITEM.** It walks the syntax tree of the whole
package and fails on any alert kind nobody has classified, so a future alert cannot default to
the wrong channel or to nowhere. The tempting alternative — "anything whose name contains fail,
error or crash is a problem" — is wrong in both directions on the kinds already here:
`account_changed` and `stale_open_event_never_completed` are the two most serious things the
live path can say and neither contains any of those words, while `live_order_sent` is the most
routine.
"""
from __future__ import annotations

import ast
import re
import datetime as _dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import state_isolation   # noqa: E402,F401

import tests.test_item63 as T63                         # noqa: E402
from valuation.edge import alpaca_broker as AB          # noqa: E402
from valuation.edge import fleet_notify as FN           # noqa: E402
from valuation.edge import live_cycle as LC             # noqa: E402
from valuation.edge import live_notify as LN            # noqa: E402
from valuation.saas import alert_routing as AR          # noqa: E402
from valuation.saas import notify as NOTIFY             # noqa: E402
from valuation.screener import rebalance_watch as RW    # noqa: E402

OPEN_NOW = _dt.datetime(2026, 10, 22, 13, 36)


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.sent = []          # [(channel, body)]

    def send(self, ok=True):
        def _s(cfg, body, channel=None):
            self.sent.append((channel, body))
            return ok
        return _s

    def kinds_on(self, channel):
        return [b for (c, b) in self.sent if c == channel]


# =============================================================================================
class TheORDERPLANSAreIdenticalBeforeAndAfter(_Tmp):
    """Item 74's own promise: *"This item changes where messages go, never what the system
    trades. A test must pin that every order plan is identical before and after."*

    Pinned by running the real cycle and comparing the plan against the one `0ffc014` produced
    — the figures below are COMMITTED LITERALS taken from that tree, not recomputed here, so a
    change in the planner cannot move the expectation with it (`MA13`'s idiom).
    """

    #: What the paper slot plans on item 63's own fixture, MEASURED on `71b0c2b` -- item 75's
    #: landing, before a line of item 74 existed. The sources were restored from git, the plan
    #: printed, and the sources put back; the figure is that output, not this tree's.
    #:
    #: **A LITERAL COPIED FROM TODAY'S RUN WOULD BE A TEST THAT CANNOT FAIL**, which is the
    #: whole reason to pin a plan at all. My first cut guessed `AAA/BBB` from a different
    #: fixture and went red, which is the guard working.
    EXPECTED = [("AAPL", "buy", 6.0), ("MSFT", "buy", 2.0)]

    def _plan(self):
        got = LC.run_slot(LC.PAPER_SLOT, pct=100.0, armed_state=T63.ARMED, book=T63.BOOK,
                          client=T63.broker(T63.RecordedAlpaca()), equity=1000.0,
                          marks=T63.MARKS, root=self.root, send=False,
                          account=T63.ACCOUNT)
        return [(str(o["ticker"]), str(o["side"]).lower(), round(float(o["qty"]), 6))
                for o in (got.get("orders") or [])]

    def test_the_plan_matches_the_pre_item_74_tree(self):
        got = self._plan()
        self.assertTrue(got, "the fixture planned nothing, so this test proves nothing")
        self.assertEqual(got, self.EXPECTED)

    def test_routing_is_not_reachable_from_the_PLANNER_at_all(self):
        """The structural half: `live_slots.order_plan` must not import or mention routing.
        A plan that could read a channel is a plan a notification change could move."""
        import inspect
        from valuation.edge import live_slots as LS
        src = inspect.getsource(LS.order_plan)
        for word in ("alert_routing", "channel", "discord", "webhook"):
            self.assertNotIn(word, src.lower(),
                             "the order planner mentions %r" % word)


# =============================================================================================
class EveryAlertKindIsClassified(unittest.TestCase):
    """ONE REGISTRY, and a test that fails on anything unclassified."""

    @staticmethod
    def emitted_kinds():
        """Every alert kind emitted anywhere under `valuation/`, by AST not by grep.

        An alert is a dict carrying BOTH `kind` and `reason` — that pair is what distinguishes a
        notification from the several other dicts in this tree that happen to have a `kind` key
        (a headline classification, an audit-item collision). Dynamic values are returned as the
        marker `<dynamic>` so they cannot pass unnoticed.
        """
        found = {}
        for dp, _dn, fn in os.walk(os.path.join(REPO, "valuation")):
            if "__pycache__" in dp:
                continue
            for f in fn:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dp, f)
                try:
                    tree = ast.parse(io.open(p, encoding="utf-8").read())
                except (OSError, SyntaxError):
                    continue
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Dict):
                        continue
                    keys = [k.value for k in node.keys
                            if isinstance(k, ast.Constant) and isinstance(k.value, str)]
                    if "kind" not in keys or "reason" not in keys:
                        continue
                    for k, v in zip(node.keys, node.values):
                        if isinstance(k, ast.Constant) and k.value == "kind":
                            name = (v.value if isinstance(v, ast.Constant)
                                    and isinstance(v.value, str) else "<dynamic>")
                            found.setdefault(name, set()).add(os.path.relpath(p, REPO))
        return found

    def test_EVERY_EMITTED_KIND_IS_IN_THE_REGISTRY(self):
        found = self.emitted_kinds()
        self.assertTrue(found, "the AST walk found no alerts at all, so it proves nothing")
        missing = sorted(k for k in found
                         if k != "<dynamic>"
                         and k not in AR.KINDS
                         and k not in AR.NOT_ALERT_KINDS)
        self.assertEqual(missing, [],
                         "unclassified alert kind(s) %r -- add them to alert_routing.KINDS "
                         "with the reason beside each" % (missing,))

    def test_THE_DYNAMIC_KINDS_ARE_NAMED_rather_than_waved_through(self):
        """`run_slot` builds two kinds from an expression. A `<dynamic>` hit would otherwise be
        a hole in the test above, so the two names are asserted to exist in the registry AND to
        be the two the source actually builds."""
        import inspect
        src = inspect.getsource(LC.run_slot)
        for k in ("reconcile_truncated", "order_read_failed"):
            self.assertIn('"%s"' % k, src, "run_slot no longer builds %r" % k)
            self.assertIn(k, AR.KINDS, "%r is not classified" % k)

    def test_an_unknown_kind_RAISES_rather_than_guessing(self):
        with self.assertRaises(AR.UnclassifiedAlert):
            AR.channel_for("something_nobody_classified")

    def test_the_registry_is_not_a_NAME_RULE_in_disguise(self):
        """The measurement behind the design note, and it is one-directional in the DANGEROUS
        direction — which is sharper than what I first asserted.

        My first cut claimed the rule misclassifies `live_order_sent` too. It does not: nothing
        routine contains one of these words, so the rule gets every routine kind right by luck
        and gets two dozen PROBLEMS wrong. Every one of its mistakes therefore sends a real
        failure to the routine channel, which is exactly the failure a problems channel exists
        to prevent — and `account_changed` and `stale_open_event_never_completed`, the two most
        serious things the live path can say, are both among them.
        """
        words = ("fail", "error", "crash", "bad")
        wrong = []
        for kind, ch in AR.KINDS.items():
            guess = AR.ALERTS if any(w in kind for w in words) else AR.ROUTINE
            if guess != ch:
                wrong.append(kind)
        self.assertGreater(len(wrong), 10,
                           "a name rule nearly reproduces the registry, which would mean the "
                           "hand classification is not earning its keep")
        self.assertIn("account_changed", wrong)
        self.assertIn("stale_open_event_never_completed", wrong)
        for kind in wrong:
            self.assertEqual(AR.KINDS[kind], AR.ALERTS,
                             "the name rule's mistakes are supposed to be problems routed to "
                             "the routine channel; %r breaks that reading" % kind)

    def test_EVERY_registry_entry_is_a_real_channel(self):
        for kind, ch in AR.KINDS.items():
            self.assertIn(ch, AR.CHANNELS, "%r is routed to %r" % (kind, ch))

    def test_the_two_kinds_DECLARED_AHEAD_of_item_73_are_said_to_be_so(self):
        """`C5`'s direction applied to the registry: an entry with no emitter is declared as
        such, so a line nobody can reach shows up rather than looking like coverage."""
        found = self.emitted_kinds()
        for k in AR.DECLARED_AHEAD_OF_EMITTER:
            self.assertIn(k, AR.KINDS)
            self.assertNotIn(k, found,
                             "%r now HAS an emitter, so take it out of "
                             "DECLARED_AHEAD_OF_EMITTER" % k)


# =============================================================================================
class ProblemsAndRoutinePostsGoToDifferentPlaces(_Tmp):
    def test_an_order_is_ROUTINE_and_a_rejection_is_an_ALERT(self):
        alerts = [
            {"kind": "live_order_sent", "slot": "paper", "event": "e", "reason": "buy A 1 @ 2"},
            {"kind": "broker_error", "slot": "paper", "event": "e", "reason": "rejected"},
        ]
        got = LN.announce(alerts, root=self.root, send=self.send(), now=OPEN_NOW)
        self.assertTrue(got["sent"])
        self.assertEqual(len(self.sent), 2, self.sent)
        self.assertEqual(len(self.kinds_on(AR.ALERTS)), 1)
        self.assertEqual(len(self.kinds_on(AR.ROUTINE)), 1)
        self.assertIn("rejected", self.kinds_on(AR.ALERTS)[0])
        self.assertIn("buy A", self.kinds_on(AR.ROUTINE)[0])
        self.assertNotIn("buy A", self.kinds_on(AR.ALERTS)[0],
                         "an order line reached the problems channel")

    def test_a_routine_only_cycle_posts_NOTHING_to_the_alerts_channel(self):
        LN.announce([{"kind": "live_order_sent", "slot": "paper", "event": "e",
                      "reason": "buy A"}], root=self.root, send=self.send(), now=OPEN_NOW)
        self.assertEqual(self.kinds_on(AR.ALERTS), [])

    def test_a_quiet_cycle_stays_quiet_on_BOTH_channels(self):
        got = LN.announce([], root=self.root, send=self.send(), now=OPEN_NOW)
        self.assertFalse(got["sent"])
        self.assertEqual(self.sent, [])

    def test_the_FLEET_sends_fills_routine_and_refusals_to_alerts(self):
        d = os.path.join(self.root, "fleet")
        os.makedirs(d, exist_ok=True)
        fill = {"kind": "fill", "seq": "1", "symbol": "SPY", "occ": "SPY260101C00500000",
                "side": "buy", "qty": "1", "fill_price": "1.25", "arm": "B"}
        got = FN.announce({"f1": [fill]}, {"f2": "SELFCHECK_ABSENT"}, d, send=self.send())
        self.assertTrue(got["sent"], got.get("reason"))
        self.assertEqual(len(self.sent), 2, self.sent)
        self.assertIn("SPY", self.kinds_on(AR.ROUTINE)[0])
        self.assertIn("SELFCHECK_ABSENT", self.kinds_on(AR.ALERTS)[0])
        self.assertNotIn("SPY", self.kinds_on(AR.ALERTS)[0])


# =============================================================================================
class TheNoiseRule(_Tmp):
    """One post when it starts; one when it clears; one reminder per day while it stays broken."""

    COND = [{"kind": "preflight_failed", "slot": "1", "reason": "no usable price for AAA"}]

    def test_ONE_post_when_it_starts_and_NOTHING_on_the_same_day(self):
        d = _dt.datetime(2026, 10, 22, 9, 0)
        first = LN.announce(self.COND, root=self.root, send=self.send(), now=d)
        self.assertTrue(first["sent"])
        for hour in (10, 12, 14, 16):
            again = LN.announce(self.COND, root=self.root, send=self.send(),
                                now=d.replace(hour=hour))
            self.assertFalse(again["sent"],
                             "a second post on the same day, at %d:00" % hour)
        self.assertEqual(len(self.sent), 1, self.sent)

    def test_ONE_reminder_the_NEXT_day_and_no_more(self):
        LN.announce(self.COND, root=self.root, send=self.send(),
                    now=_dt.datetime(2026, 10, 22, 9, 0))
        d2 = _dt.datetime(2026, 10, 23, 9, 0)
        rem = LN.announce(self.COND, root=self.root, send=self.send(), now=d2)
        self.assertTrue(rem["sent"], "no reminder on the following day")
        self.assertEqual(rem["n_reminders"], 1)
        self.assertEqual(rem["n_conditions"], 0, "a reminder read as a NEW condition")
        self.assertIn("still", self.sent[-1][1],
                      "the reminder is indistinguishable from a new failure")
        for hour in (11, 15, 19):
            self.assertFalse(LN.announce(self.COND, root=self.root, send=self.send(),
                                         now=d2.replace(hour=hour))["sent"])
        self.assertEqual(len(self.sent), 2, self.sent)

    def test_ONE_post_when_it_clears(self):
        LN.announce(self.COND, root=self.root, send=self.send(),
                    now=_dt.datetime(2026, 10, 22, 9, 0))
        gone = LN.announce([], root=self.root, send=self.send(),
                           now=_dt.datetime(2026, 10, 22, 17, 0))
        self.assertTrue(gone["sent"])
        self.assertEqual(gone["n_cleared"], 1)
        self.assertIn("has cleared", self.sent[-1][1])
        self.assertEqual(self.sent[-1][0], AR.ALERTS,
                         "a clearing belongs where the problem was reported")
        quiet = LN.announce([], root=self.root, send=self.send(),
                            now=_dt.datetime(2026, 10, 23, 9, 0))
        self.assertFalse(quiet["sent"], "the clearing was announced twice")

    def test_a_reminder_is_a_DAY_and_not_24_hours(self):
        """A 24-hour rule drifts later every day until it lands in the middle of the night, and
        this path runs five times a day on a scheduler measured 3.45-7.48 hours late."""
        self.assertTrue(AR.needs_reminder("2026-10-22", "2026-10-23"))
        self.assertFalse(AR.needs_reminder("2026-10-23", "2026-10-23"))
        self.assertTrue(AR.needs_reminder("", "2026-10-23"),
                        "an unreadable stamp must read as DUE, which is the loud direction")


# =============================================================================================
class ThePerChannelWatermark(_Tmp):
    """A successful post on one channel must not discard the other channel's lines."""

    PAIR = [{"kind": "live_order_sent", "slot": "paper", "event": "e", "reason": "buy A 1"},
            {"kind": "broker_error", "slot": "paper", "event": "e", "reason": "rejected AAA"}]

    def test_a_failed_ALERTS_post_is_retried_while_the_routine_one_is_not(self):
        def half(cfg, body, channel=None):
            self.sent.append((channel, body))
            return channel != AR.ALERTS          # routine succeeds, alerts fails

        first = LN.announce(self.PAIR, root=self.root, send=half, now=OPEN_NOW)
        self.assertTrue(first["sent"], "the routine half should have gone")
        self.assertFalse(first["by_channel"][AR.ALERTS]["sent"])

        self.sent = []
        second = LN.announce(self.PAIR, root=self.root, send=self.send(), now=OPEN_NOW)
        chans = [c for (c, _b) in self.sent]
        self.assertIn(AR.ALERTS, chans, "the failed rejection was never retried")
        self.assertNotIn(AR.ROUTINE, chans,
                         "the order was announced twice after a successful first post")

    def test_a_failed_CLEARING_is_retried(self):
        cond = [{"kind": "parity_mismatch", "slot": "1", "reason": "BBB differs"}]
        LN.announce(cond, root=self.root, send=self.send(), now=OPEN_NOW)
        self.sent = []
        LN.announce([], root=self.root, send=self.send(ok=False), now=OPEN_NOW)
        self.sent = []
        again = LN.announce([], root=self.root, send=self.send(), now=OPEN_NOW)
        self.assertEqual(again["n_cleared"], 1, "the clearing was lost on a failed post")


# =============================================================================================
class NothingPrivateEverLeaves(_Tmp):
    """Don: no P&L, return or verdict; no key, token or webhook URL; no account number."""

    ENV = {"DISCORD_ALERT_WEBHOOK_URL": "https://discord.test/api/webhooks/42/sEcReTaLeRt",
           "DISCORD_WEBHOOK_URL": "https://discord.test/api/webhooks/43/sEcReTrOuTiNe",
           "ADMIN_TOKEN": "tok-abcdefghijklmnop",
           "HC_PING_KEY": "hcp-abcdefghijklmnop",
           "ALPACA_ACCOUNT_1_SECRET_KEY": "sk-abcdefghijklmnopqrst"}

    def test_a_webhook_url_a_token_and_a_key_are_all_REMOVED_from_a_body(self):
        body = ("posting to %s with %s and %s and key %s"
                % (self.ENV["DISCORD_ALERT_WEBHOOK_URL"], self.ENV["ADMIN_TOKEN"],
                   self.ENV["HC_PING_KEY"], self.ENV["ALPACA_ACCOUNT_1_SECRET_KEY"]))
        safe = AR.safe_body(body, env=self.ENV)
        self.assertFalse(safe["blocked"], safe["why"])
        for v in self.ENV.values():
            self.assertNotIn(v, safe["text"], "a configured secret survived the scrub")
        self.assertIn(AR.REDACTED, safe["text"])

    def test_AN_ACCOUNT_ID_IS_REMOVED_TOO__and_the_live_path_embeds_one(self):
        """`account_changed`'s own reason text carries the Alpaca account id, which is why
        `extra` exists: this module cannot know an identifier the slot reads from its record,
        so the caller supplies it and nothing is guessed at."""
        acct = "PA3XYZ9QWERTY"
        body = "this slot's keys now resolve to account %s" % acct
        safe = AR.safe_body(body, env=self.ENV, extra=[acct])
        self.assertNotIn(acct, safe["text"])

    def test_a_RETURN_SHAPED_WORD_is_refused_on_the_ALERTS_channel(self):
        safe = AR.safe_body("the book is up 12% in excess return", env=self.ENV,
                            check_returns=True)
        self.assertTrue(safe["blocked"])
        self.assertEqual(safe["text"], AR.BLOCKED_LINE)

    def test_a_BLOCKED_body_is_REPLACED_and_not_DROPPED(self):
        """A leak must not be indistinguishable from a quiet day, and the body must not go out
        either. So the pointer survives and the text does not."""
        safe = AR.safe_body("alpha was 7%", env=self.ENV, check_returns=True)
        self.assertTrue(safe["text"])
        self.assertIn("NOT posted", safe["text"])

    def test_the_PRODUCT_CARDS_are_NOT_return_gated__and_that_line_is_deliberate(self):
        """The scream-buy caveat contains the word "profit". Gating the routine channel on
        return-words would have silently stopped a card this project ships today, and that copy
        already has its own authority (`web.dip_posture`). Pinned so the line is a decision
        rather than an accident."""
        card = NOTIFY._CONF_CAVEAT
        self.assertIn("profit", card.lower(), "the caveat changed; re-read this test")
        self.assertFalse(AR.safe_body(card, env={})["blocked"])
        self.assertTrue(AR.safe_body(card, env={}, check_returns=True)["blocked"])

    def test_NO_LIVE_CYCLE_BODY_carries_a_secret_or_a_return_word(self):
        """End to end through the real cycle, with the secrets actually set in the env."""
        bodies = []

        def cap(cfg, body, channel=None):
            bodies.append(body)
            return True

        r = LC.run_cycle(env={}, root=self.root, book=T63.BOOK, send=True, now=OPEN_NOW,
                         paper_client=T63.broker(T63.RecordedAlpaca()), notify_send=cap)
        self.assertTrue(r["ok"])
        self.assertTrue(bodies, "the cycle announced nothing, so this proves nothing")
        for b in bodies:
            self.assertEqual(AR.secret_violations(b, env=self.ENV), [], b[:200])
            self.assertEqual(AR.return_violations(b), [], b[:200])


# =============================================================================================
class TheWebhookFallback(unittest.TestCase):
    def test_the_alerts_channel_falls_back_LOUDLY_to_the_routine_one(self):
        h = AR.webhook(None, AR.ALERTS, {"DISCORD_WEBHOOK_URL": "https://r"})
        self.assertTrue(h["ok"])
        self.assertEqual(h["channel_used"], AR.ROUTINE)
        self.assertEqual(h["prefix"], AR.FALLBACK_PREFIX + " ")

    def test_with_neither_set_it_refuses_and_the_reason_names_the_VARIABLES(self):
        h = AR.webhook(None, AR.ALERTS, {})
        self.assertFalse(h["ok"])
        self.assertIn(AR.ALERT_WEBHOOK_VAR, h["reason"])
        self.assertIn(AR.ROUTINE_WEBHOOK_VAR, h["reason"])

    def test_cfg_IS_THE_AUTHORITY_so_item_74_changes_no_existing_behaviour(self):
        """`send_discord` read `cfg.discord_webhook_url` and nothing else before item 74. An
        env-first rule would make a caller that deliberately passes an empty cfg start posting
        because the process happened to have the variable set — a behaviour change smuggled in
        by a routing change, which is the one thing this item promised not to do."""
        class _Cfg:
            discord_webhook_url = ""
            discord_alert_webhook_url = ""
        h = AR.webhook(_Cfg(), AR.ROUTINE, {"DISCORD_WEBHOOK_URL": "https://leak"})
        self.assertFalse(h["ok"])
        self.assertEqual(h["url"], "")

    def test_the_watchdog_SCRIPT_agrees_with_the_registry(self):
        """`scripts/check_staleness.py` cannot import the registry — it runs on a bare runner,
        deliberately, because a watchdog that needs the app to import cannot report that the app
        will not import. So the two copies are asserted to agree about the only thing that could
        drift: the variable names and the prefix.

        **AND THE ENVIRONMENT IS CLEARED FIRST, WHICH THIS TEST TAUGHT ME THE HARD WAY.** My
        first cut called `_alert_webhook()` against the real process environment. A developer
        machine has `DISCORD_WEBHOOK_URL` set, so the test failed — and its failure message
        PRINTED most of the real webhook URL. A test that reads live secrets can both fail for
        no reason and publish the thing it is checking is handled carefully.
        """
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        import check_staleness as CS
        self.assertEqual(CS.ALERT_WEBHOOK_VAR, AR.ALERT_WEBHOOK_VAR)
        self.assertEqual(CS.ROUTINE_WEBHOOK_VAR, AR.ROUTINE_WEBHOOK_VAR)
        self.assertEqual(CS.FALLBACK_PREFIX, AR.FALLBACK_PREFIX)
        saved = {k: os.environ.pop(k, None)
                 for k in (AR.ALERT_WEBHOOK_VAR, AR.ROUTINE_WEBHOOK_VAR)}
        try:
            self.assertEqual(CS._alert_webhook(), ("", ""))
            os.environ[AR.ROUTINE_WEBHOOK_VAR] = "https://example.invalid/routing-test"
            url, prefix = CS._alert_webhook()
            self.assertEqual(prefix, AR.FALLBACK_PREFIX + " ")
            self.assertEqual(url, "https://example.invalid/routing-test")
            os.environ[AR.ALERT_WEBHOOK_VAR] = "https://example.invalid/alerts-test"
            url, prefix = CS._alert_webhook()
            self.assertEqual(prefix, "")
            self.assertEqual(url, "https://example.invalid/alerts-test")
        finally:
            for k, v in saved.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


# =============================================================================================
class TheRebalanceWatch(unittest.TestCase):
    """Don: overdue, refused, and a 14-day heads-up. The dates are DERIVED, never written down."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bp = os.path.join(self.tmp, "book.json")
        self._write([{"date": "2026-07-31", "scan_date": "2026-07-24",
                      "positions": [{"ticker": "AAA", "weight": 1.0}]}])

    def _write(self, rebalances):
        with io.open(self.bp, "w", encoding="utf-8") as fh:
            json.dump({"inception_date": "2026-07-30", "day_n": 1,
                       "scan_date": "2026-07-24",
                       "positions": [{"ticker": "AAA", "weight": 1.0}],
                       "rebalances": rebalances}, fh)

    def kinds(self, as_of, **kw):
        return [a["kind"] for a in RW.status(as_of=as_of, meta_path=self.bp, **kw)["alerts"]]

    def test_THE_DUE_DATE_IS_DERIVED_from_the_in_force_scan_date(self):
        """63 trading days from 2026-07-24 is 2026-10-22, which is the runbook's own figure.
        A hard-coded date would be right for one quarter and wrong for every one after."""
        from valuation.screener import index_in_force as IIF
        self.assertEqual(IIF.next_rebalance("2026-07-24"), "2026-10-22")
        self.assertEqual(RW.status(as_of="2026-10-20", meta_path=self.bp)["next_rebalance"],
                         "2026-10-22")

    def test_the_heads_up_fires_FOURTEEN_CALENDAR_DAYS_out_and_not_before(self):
        self.assertNotIn("rebalance_due_soon", self.kinds("2026-10-07"))
        self.assertIn("rebalance_due_soon", self.kinds("2026-10-08"))
        self.assertIn("rebalance_due_soon", self.kinds("2026-10-22"))

    def test_the_heads_up_says_the_SENTENCE_DON_ASKED_FOR(self):
        got = RW.status(as_of="2026-10-08", meta_path=self.bp)
        line = next(a["reason"] for a in got["alerts"]
                    if a["kind"] == "rebalance_due_soon")
        self.assertEqual(line, RW.HEADS_UP_SENTENCE.format(date="2026-10-22"))
        self.assertIn("Sharadar", line)

    def test_OVERDUE_FIRES_ON_THE_MORNING_OF_10_26__which_is_Don_s_own_figure(self):
        """His words: "more than one trading day past ... For 10-22 that means an alert from the
        morning of 10-26." 10-23 is one trading day past and inside the grace; 10-26 is two."""
        self.assertNotIn("rebalance_overdue", self.kinds("2026-10-22"))
        self.assertNotIn("rebalance_overdue", self.kinds("2026-10-23"))
        self.assertIn("rebalance_overdue", self.kinds("2026-10-26"))

    def test_a_NEWER_BOOK_silences_the_overdue_alert(self):
        self._write([{"date": "2026-07-31", "scan_date": "2026-07-24",
                      "positions": [{"ticker": "AAA", "weight": 1.0}]},
                     {"date": "2026-10-22", "scan_date": "2026-10-22",
                      "positions": [{"ticker": "BBB", "weight": 1.0}]}])
        got = RW.status(as_of="2026-10-26", meta_path=self.bp)
        self.assertFalse(got["overdue"], got["reason"])
        self.assertEqual(got["in_force"], "2026-10-22")
        self.assertEqual(got["next_rebalance"], "2027-01-25")

    def test_a_REFUSED_book_alerts_independently_of_the_dates(self):
        ks = self.kinds("2026-10-20",
                        refusal={"when": "2026-10-20T19:00", "reason": "conformance: 25 names"})
        self.assertIn("rebalance_refused", ks)

    def test_an_UNREADABLE_book_alerts_rather_than_passing(self):
        """`C5`: absent is not on time. A book nobody can read cannot be shown to be current."""
        got = RW.status(as_of="2026-10-20", meta_path=os.path.join(self.tmp, "nope.json"))
        self.assertFalse(got["ok"])
        self.assertIn("rebalance_overdue", [a["kind"] for a in got["alerts"]])

    def test_NO_FIGURE_reaches_a_rebalance_alert(self):
        for d in ("2026-10-08", "2026-10-26"):
            for a in RW.status(as_of=d, meta_path=self.bp)["alerts"]:
                self.assertEqual(AR.return_violations(a["reason"]), [], a["reason"])

    def test_every_rebalance_kind_is_in_the_registry(self):
        for d in ("2026-10-08", "2026-10-26"):
            for a in RW.status(as_of=d, meta_path=self.bp,
                               refusal={"reason": "x"})["alerts"]:
                self.assertEqual(AR.channel_for(a["kind"]), AR.ALERTS)


# =============================================================================================
class TheRecordGap(unittest.TestCase):
    def test_a_MISSING_ROW_and_a_FALSE_GATE_are_two_alerts(self):
        detail = {"recording_ok": False,
                  "per_vintage_recording": [
                      {"vintage": 4, "status": "OPEN",
                       "missing_dates": ["2026-10-19", "2026-10-20"]}]}
        got = RW.record_status(detail=detail)
        ks = [a["kind"] for a in got["alerts"]]
        self.assertIn("record_row_missing", ks)
        self.assertIn("recording_not_ok", ks)
        self.assertIn("2026-10-19", got["alerts"][0]["reason"])

    def test_ONLY_THE_OPEN_VINTAGE_S_MISSES_ARE_OWED(self):
        """A closed vintage's misses are history the contract already recorded and nobody can
        act on. Reporting them would alert every day for ever."""
        detail = {"recording_ok": True,
                  "per_vintage_recording": [
                      {"vintage": 1, "status": "VOID", "missing_dates": ["2026-07-31"]},
                      {"vintage": 3, "status": "CLOSED", "missing_dates": ["2026-08-12"]},
                      {"vintage": 4, "status": "OPEN", "missing_dates": []}]}
        got = RW.record_status(detail=detail)
        self.assertEqual(got["missing"], [])
        self.assertEqual(got["alerts"], [])

    def test_recording_ok_NONE_is_not_a_failure(self):
        """The meter returns None before the vintage's first row is due — the contract's own
        not-vacuously-green rule. Alerting on it would fire whenever a vintage opens."""
        got = RW.record_status(detail={"recording_ok": None,
                                       "per_vintage_recording": [
                                           {"status": "OPEN", "missing_dates": []}]})
        self.assertTrue(got["ok"])
        self.assertEqual(got["alerts"], [])

    def test_the_key_it_reads_IS_THE_ONE_THE_METER_EMITS(self):
        """My first cut read `detail()["gaps"]["missing"]`, and `detail()` has no `gaps` key —
        so `missing` was always empty and the row-missing alert could never fire, while
        `recording_ok` independently made the function look like it worked. Pinned against the
        real meter so the wrong-object version cannot come back."""
        from valuation.edge import track_meter as TM
        d = TM.detail()
        self.assertIn("per_vintage_recording", d)
        self.assertNotIn("gaps", d)
        for v in (d.get("per_vintage_recording") or []):
            self.assertIn("missing_dates", v)
            self.assertIn("status", v)


# =============================================================================================
def _read_wf(path):
    return io.open(path, encoding="utf-8").read().replace("\r\n", "\n")


def wf_jobs(src):
    """`{job: [(step name, its `if:` or "")]}`, parsed AS TEXT.

    **PyYAML IS NOT IN THE CI ENVIRONMENT, AND MY FIRST CUT IMPORTED IT ANYWAY.** Five tests
    below would have errored on the runner while passing here — `test_item65` carries that
    lesson in its own docstring ("my first cut imported `yaml` and the gate returned
    ModuleNotFoundError") and I wrote a new one instead of reading the neighbouring suite. It is
    not in `requirements.txt`, which is the check I should have run first.

    Parsed on the layout these files actually use and nothing looser: jobs at two spaces, steps
    at `      - name:`, keys at eight. `wf_jobs` returning an EMPTY dict for a file with jobs
    would make every assertion below vacuous, so each caller asserts it found something.
    """
    out, job, step = {}, None, None
    body = src[src.index("\njobs:") + 1:]
    for ln in body.split("\n"):
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*$", ln)
        if m:
            job, step = m.group(1), None
            out[job] = []
            continue
        if job is None:
            continue
        if ln and not ln.startswith(" ") and ln.rstrip() != "jobs:":
            job = None
            continue
        m = re.match(r"^      - name:\s*(.+?)\s*$", ln)
        if m:
            step = [m.group(1).strip('"\''), ""]
            out[job].append(step)
            continue
        m = re.match(r"^        if:\s*(.+?)\s*$", ln)
        if m and step is not None:
            step[1] = m.group(1).strip()
    return {k: [tuple(s) for s in v] for k, v in out.items()}


def wf_crons(src):
    return re.findall(r'^\s*- cron:\s*"([^"]+)"', src, re.M)


def wf_on_keys(src):
    """The keys under `on:`, parsed as text. `on:` is a YAML gotcha (it parses as True),
    which is a second reason not to reach for a YAML library here."""
    head = src[src.index("\non:") + 1:]
    out = []
    for ln in head.split("\n")[1:]:
        if ln and not ln.startswith(" "):
            break
        m = re.match(r"^  ([A-Za-z_]+):", ln)
        if m:
            out.append(m.group(1))
    return out


class TheWorkflowsAreHandedOverCorrectly(unittest.TestCase):
    """`.github` is refused by the land gate, so these go through `pending_workflows/`."""

    PENDING = os.path.join(REPO, "pending_workflows")
    INSTALLED = os.path.join(REPO, ".github", "workflows")

    #: Every scheduled workflow. `land-agent-branch` is out by Don's own instruction.
    EXPECTED = ("auto-scan", "daily-doors", "fleet-backup", "fleet-cycle", "fleet-selfcheck",
                "live-check", "live-cycle", "track-backup", "track-row", "valreads-record",
                "alert-test", "rebalance-watch")

    def test_every_workflow_is_waiting_as_a_SAME_NAME_replacement(self):
        for n in self.EXPECTED:
            self.assertTrue(os.path.exists(os.path.join(self.PENDING, n + ".yml")),
                            "pending_workflows/%s.yml is missing" % n)

    def test_land_agent_branch_is_NOT_among_them(self):
        """Don: "Leave land-agent-branch out -- a lane branch failing the gate is normal."
        Alerting on it would post several times a day for something working as designed."""
        self.assertFalse(os.path.exists(os.path.join(self.PENDING, "land-agent-branch.yml")))

    def test_ONE_INSTALL_LEAVES_EXACTLY_ONE_COPY_OF_EACH(self):
        """`install_workflows.bat` copies from `data/pending_workflows` and THEN from the
        tracked `pending_workflows`, into one directory, so a name present in both ends up as a
        single file with the TRACKED content. Asserted against the installer's own source,
        because the ordering is the whole guarantee."""
        src = io.open(os.path.join(REPO, "install_workflows.bat"),
                      encoding="utf-8", errors="replace").read()
        legacy = src.index('for %%F in ("%SRC%\\*.yml")')
        tracked = src.index('for %%F in ("%SRC2%\\*.yml")')
        self.assertLess(legacy, tracked,
                        "the tracked directory must be copied LAST so it wins a name clash")
        self.assertIn('copy /y', src)

    def test_every_JOB_has_a_failure_alert(self):
        for n in self.EXPECTED:
            if n == "alert-test":
                continue            # manual-only; its whole body is the test
            jobs = wf_jobs(_read_wf(os.path.join(self.PENDING, n + ".yml")))
            self.assertTrue(jobs, "%s: no jobs parsed, so this proves nothing" % n)
            for job, steps in jobs.items():
                self.assertTrue(steps, "%s/%s: no steps parsed" % (n, job))
                self.assertTrue(any("tell Don this failed" in x for x, _c in steps),
                                "%s/%s has no failure alert" % (n, job))

    def test_the_failure_step_runs_ONLY_on_failure(self):
        seen = 0
        for n in self.EXPECTED:
            for job, steps in wf_jobs(_read_wf(
                    os.path.join(self.PENDING, n + ".yml"))).items():
                for name, cond in steps:
                    if "tell Don this failed" in name:
                        seen += 1
                        self.assertEqual(cond, "failure()",
                                         "%s/%s posts on success too (if: %r)"
                                         % (n, job, cond))
        self.assertGreaterEqual(seen, 16, "only %d failure steps found" % seen)

    def test_the_PINGED_jobs_start_and_end_with_a_ping(self):
        """Don's list: track-row, live-cycle, fleet-cycle, the auto-scan watchdog,
        track-backup, and the rebalance-overdue check."""
        want = {"track-row": "track-row", "live-cycle": "live-cycle",
                "fleet-cycle": "fleet-cycle", "track-backup": "track-backup",
                "rebalance-watch": "rebalance-watch", "auto-scan": "auto-scan-watchdog"}
        for n, slug in want.items():
            hit = False
            for job, steps in wf_jobs(_read_wf(
                    os.path.join(self.PENDING, n + ".yml"))).items():
                names = [x for x, _c in steps]
                if not any(("healthchecks start (%s)" % slug) in x for x in names):
                    continue
                hit = True
                self.assertIn("healthchecks start (%s)" % slug, names[0],
                              "%s/%s: the start ping is not the FIRST step -- one that runs "
                              "after the work has begun cannot report a job that died on its "
                              "first step" % (n, job))
                self.assertTrue(any(("healthchecks end (%s)" % slug) in x for x in names),
                                "%s/%s has a start ping and no end ping, so the monitor would "
                                "report every run as still running" % (n, job))
            self.assertTrue(hit, "%s has no %s ping at all" % (n, slug))

    def test_live_cycle_STILL_SENDS_run_paper(self):
        """Item 74's hard rule. The only `run=1` strings in that file are the comments telling
        Don what to change AFTER the auditor review."""
        s = io.open(os.path.join(self.PENDING, "live-cycle.yml"), encoding="utf-8").read()
        self.assertIn("admin/live-cycle?run=paper", s)
        for line in s.splitlines():
            if "run=1" in line:
                self.assertTrue(line.lstrip().startswith("#"),
                                "a non-comment line carries run=1: %r" % line)

    def test_NO_WORKFLOW_ECHOES_A_SECRET(self):
        """A workflow log is readable by anyone with repo access and persists for months."""
        import re
        for n in self.EXPECTED:
            s = io.open(os.path.join(self.PENDING, n + ".yml"), encoding="utf-8").read()
            for m in re.finditer(r"^\s*echo\s+.*$", s, re.M):
                line = m.group(0)
                for bad in ("$HOOK", "${HOOK}", "$ADMIN_TOKEN", "${ADMIN_TOKEN}",
                            "$HC_PING_KEY", "${HC_PING_KEY}", "$ALERT_HOOK",
                            "${ALERT_HOOK}", "$ROUTINE_HOOK", "${ROUTINE_HOOK}"):
                    self.assertNotIn(bad, line, "%s echoes a secret: %r" % (n, line.strip()))

    def test_alert_test_is_MANUAL_ONLY(self):
        keys = wf_on_keys(_read_wf(os.path.join(self.PENDING, "alert-test.yml")))
        self.assertEqual(keys, ["workflow_dispatch"],
                         "a scheduled test is a recurring message saying nothing is wrong, "
                         "which is the fastest way to teach a reader to ignore the channel it "
                         "arrives in; got %r" % (keys,))

    def test_the_rebalance_watch_runs_at_least_DAILY_on_trading_days(self):
        src = _read_wf(os.path.join(self.PENDING, "rebalance-watch.yml"))
        crons = wf_crons(src)
        self.assertTrue(crons, "the overdue check has no schedule")
        for c in crons:
            self.assertTrue(c.endswith("1-5"), "%r is not a weekday schedule" % c)
        self.assertIn("workflow_dispatch", wf_on_keys(src),
                      "Don cannot run the check by hand")

    def test_THIS_ITEM_INSTALLED_NOTHING_ITSELF(self):
        """The land gate refuses any change under `.github/`, and `pending_workflows/` is the
        whole handover — Don installs it.

        **ASSERTED ON THE FILES, NOT ON A DIFF AGAINST `origin/main`.** My first cut ran
        `git diff --name-only origin/main -- .github`, which `test_ma60_conventions` forbids
        outright and went red: such a check "measures whatever is checked out rather than the
        lane that wrote them, and becomes a permanent tripwire for every later lane." It is
        right, and the property is directly checkable anyway — if this item had written into
        `.github/`, the installed files would carry its marker.
        """
        wf = os.path.join(REPO, ".github", "workflows")
        for n in self.EXPECTED:
            p = os.path.join(wf, n + ".yml")
            if not os.path.exists(p):
                continue            # alert-test and rebalance-watch are new; nothing to check
            src = io.open(p, encoding="utf-8").read()
            self.assertNotIn("item 74:", src,
                             ".github/workflows/%s.yml carries item 74's steps, so this lane "
                             "wrote into .github/ -- which the land gate refuses by design, "
                             "and the handover is `install_workflows.bat`" % n)

    def test_and_the_PENDING_file_DOES_carry_them__the_positive_control(self):
        """Without this, the test above would pass on a lane that did nothing at all."""
        for n in self.EXPECTED:
            if n == "alert-test":
                continue            # its whole body is the test; it has no failure step
            src = io.open(os.path.join(self.PENDING, n + ".yml"), encoding="utf-8").read()
            self.assertIn("item 74:", src,
                          "pending_workflows/%s.yml does not carry item 74's steps" % n)


# =============================================================================================
class TheServiceDoors(unittest.TestCase):
    """**THE TOKEN IS SET ON `CONFIG` BEFORE THE APP IS BUILT**, which is how every other admin
    suite here does it — `_admin_ok` closes over `cfg`, so setting `os.environ` after
    `create_saas_app` changes nothing and the test skips for a reason that is about the fixture
    rather than about the door. My first cut did exactly that and skipped."""

    TOKEN = "item74-admin-token-for-tests"

    def setUp(self):
        from valuation.config import CONFIG
        from valuation.saas.app_saas import create_saas_app
        self._prev = CONFIG.admin_token
        self._prev_alert = getattr(CONFIG, "discord_alert_webhook_url", "")
        self._prev_routine = CONFIG.discord_webhook_url
        CONFIG.admin_token = self.TOKEN
        # NEITHER WEBHOOK IS SET, so the door cannot reach the network from a test run.
        CONFIG.discord_alert_webhook_url = ""
        CONFIG.discord_webhook_url = ""
        self.cfg = CONFIG
        self.app = create_saas_app(CONFIG)
        self.app.config["TESTING"] = False
        self.app.config["PROPAGATE_EXCEPTIONS"] = False
        self.client = self.app.test_client()
        self.hdr = {"X-Admin-Token": self.TOKEN}

    def tearDown(self):
        self.cfg.admin_token = self._prev
        self.cfg.discord_alert_webhook_url = self._prev_alert
        self.cfg.discord_webhook_url = self._prev_routine

    def test_the_alert_test_door_reports_PRESENT_OR_ABSENT_and_never_a_value(self):
        r = self.client.post("/admin/alert-test", headers=self.hdr)
        body = r.get_data(as_text=True)
        self.assertEqual(r.status_code, 200, body[:300])
        d = json.loads(body)
        self.assertTrue(d.get("configured"), "the door reported no names at all")
        for name, val in (d["configured"] or {}).items():
            self.assertIn(val, (True, False), "%s reported %r rather than present/absent"
                          % (name, val))
        # **NOT ONE CHARACTER OF A URL, A TOKEN OR A KEY IN THE WHOLE REPLY.** The reply travels
        # through a workflow log, which is readable by anyone with repo access and persists for
        # months, so this is asserted over the ENTIRE body rather than over one field.
        whole = json.dumps(d).lower()
        for bad in ("http://", "https://", self.TOKEN.lower()):
            self.assertNotIn(bad, whole, "the reply carries %r" % bad)

    def test_the_alert_test_door_SAYS_WHICH_NAMES_rather_than_a_bare_boolean(self):
        from valuation.saas import alert_routing as _AR
        d = json.loads(self.client.post("/admin/alert-test",
                                        headers=self.hdr).get_data(as_text=True))
        self.assertIn(_AR.ALERT_WEBHOOK_VAR, d["configured"])
        self.assertIn(_AR.ROUTINE_WEBHOOK_VAR, d["configured"])
        self.assertIs(d["configured"][_AR.ALERT_WEBHOOK_VAR], False)
        # With neither set, the reason must NAME the variables -- that is the whole content of
        # a setup-time reply.
        self.assertIn(_AR.ALERT_WEBHOOK_VAR, d["channels"][_AR.ALERTS]["reason"])

    def test_a_GET_of_the_rebalance_watch_reports_and_posts_nothing(self):
        r = self.client.get("/admin/rebalance-watch", headers=self.hdr)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        d = json.loads(r.get_data(as_text=True))
        self.assertFalse(d["posted"])
        self.assertIn("would_alert", d)
        self.assertIn("posts nothing", d.get("note") or "")

    def test_the_doors_refuse_without_a_token(self):
        for path in ("/admin/alert-test", "/admin/rebalance-watch"):
            self.assertEqual(self.client.post(path).status_code, 401, path)

    def test_a_GET_of_the_rebalance_watch_POSTS_NOTHING(self):
        """A side-effecting GET is reachable by a retry, a prefetch, a proxy or a pasted link,
        and none of those is a decision to tell Don something is wrong."""
        import inspect
        from valuation.saas import app_saas
        tree = ast.parse(inspect.getsource(app_saas))
        fn = next((n for n in ast.walk(tree)
                   if isinstance(n, ast.FunctionDef) and n.name == "admin_rebalance_watch"),
                  None)
        self.assertIsNotNone(fn, "the door is gone")
        body = ast.unparse(fn)
        self.assertIn('request.method == \'POST\'', body)
        i = body.index("LN.announce")
        self.assertIn("request.method == 'POST'", body[:i],
                      "the announce is not behind a POST check")


if __name__ == "__main__":
    import sys as _s
    _s.exit(0 if unittest.main(exit=False, verbosity=2).result.wasSuccessful() else 1)
