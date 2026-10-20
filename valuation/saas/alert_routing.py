"""WHICH CHANNEL DOES A MESSAGE GO TO — one registry, and a test fails on anything unclassified.

Don's ruling, 2026-10-18: problems go to a separate `#valquo-alerts` channel; the routine posts
— the daily recap, order sent and filled lines — stay where they are. The two must not be mixed,
because the whole value of a problems channel is that an unread message in it is a problem.

**WHY A REGISTRY AND NOT A CONVENTION.** The tempting rule is *"anything whose kind contains
`fail`, `error` or `crash` is an alert"*, and it is wrong in both directions on the kinds this
project already emits: `account_changed` and `stale_open_event_never_completed` are the two most
serious things the live path can say and neither contains any of those words, while
`live_order_sent` is the most routine. Worse, a substring rule is the family this record has
repointed five times — a guard keyed on a name rather than on the property. So each kind is
classified by hand, with the reason beside it, and `tests/test_item74.py` walks the syntax tree
of the whole package and **fails on any kind nobody has classified**. A future alert therefore
cannot default to the wrong channel, and cannot default to nowhere.

**THE DEFAULT DIRECTION IS LOUD.** `channel_for` raises on an unknown kind rather than guessing.
A kind that reached production unclassified is a bug, and the two ways of absorbing it are both
worse than a refusal: routing it to `#valquo-alerts` trains Don to ignore that channel, and
routing it to the routine one hides the thing he asked to be told about. `MA6`'s direction.

**NOTHING PRIVATE EVER LEAVES, AND IT IS ENFORCED ON THE FINISHED TEXT.** `scrub` runs on the
composed message, not on its inputs — V4's lesson, which `post_dip_digest` already applies one
level up: a publishing rule has to be asserted against what actually sends. It redacts by VALUE
rather than by name, so a webhook URL or a token is removed because the message contains that
exact string and never because a variable happened to be called `TOKEN`. That also means this
module never has to know, print or store any of them.
"""
from __future__ import annotations

import datetime as _dt
import os
import re

#: The two channels. `ALERTS` is `#valquo-alerts`; `ROUTINE` is the channel that exists today.
ALERTS = "alerts"
ROUTINE = "routine"
CHANNELS = (ALERTS, ROUTINE)

#: Don creates both himself. A lane never sees, prints or stores either.
ALERT_WEBHOOK_VAR = "DISCORD_ALERT_WEBHOOK_URL"
ROUTINE_WEBHOOK_VAR = "DISCORD_WEBHOOK_URL"

#: Prefixed to an alert that had to fall back to the routine webhook, so nothing goes silent
#: during setup AND nobody mistakes the fallback for the finished configuration.
FALLBACK_PREFIX = "(alerts channel not set)"

#: healthchecks.io. Only ever read as `os.environ`-present-or-absent by the workflows; the value
#: is never read into a message. Named here so one file holds every name Don has to create.
PING_KEY_VAR = "HC_PING_KEY"


class UnclassifiedAlert(KeyError):
    """A kind nobody has put in `KINDS`. Deliberately fatal — see the module docstring."""


# =============================================================================================
# THE REGISTRY
# =============================================================================================
#
# One entry per kind, the channel, and why. Grouped by where the kind is emitted so a reader
# adding an alert can see which group theirs belongs to.

KINDS = {
    # ---- the live path: `valuation/edge/live_cycle.py` ---------------------------------------
    # ORDERS ARE ROUTINE. Don's ruling in his own words: "Orders sent or filled stay routine."
    "live_order_sent": ROUTINE,

    # Everything below stops, or could stop, the Index being traded as declared.
    "account_changed": ALERTS,            # the keys now resolve to a different account
    "broker_error": ALERTS,               # a rejection from Alpaca
    "buy_blocked_at_the_broker_door": ALERTS,
    "buy_withheld_in_wind_down": ALERTS,  # its own reason calls it "a defect in the planner"
    "cancel_unconfirmed": ALERTS,         # an order we tried to cancel may still be working
    "cycle_crashed": ALERTS,
    "event_attempts_exhausted": ALERTS,   # the no-progress ceiling ran out
    "live_slot_is_the_paper_account": ALERTS,
    "order_read_failed": ALERTS,          # built dynamically in `run_slot`
    "paper_account_unreadable": ALERTS,
    "paper_client_absent": ALERTS,
    "paper_targets_unavailable": ALERTS,
    "parity_absent": ALERTS,
    "parity_mismatch": ALERTS,
    # **ALERTS, AND THE CHOICE IS DELIBERATE RATHER THAN OBVIOUS.** A vacuous parity on a 0%
    # wind-down is expected behaviour, not a breakage, so "routine" is arguable. It goes to
    # alerts because it is the one state in which a live slot transmits with NO paper
    # cross-check, and that is worth one line per wind-down. The cost of being wrong this way
    # is a line Don reads and dismisses; the other way it is a silent uncrosschecked send.
    "parity_vacuous_wind_down": ALERTS,
    "preflight_failed": ALERTS,
    "reconcile_truncated": ALERTS,        # built dynamically in `run_slot`
    "settlement_wait_overdue": ALERTS,
    "slot_crashed": ALERTS,
    "stale_open_event_never_completed": ALERTS,
    "state_write_failed": ALERTS,
    "targets_failed": ALERTS,
    # ---- item 73: the cash gap ---------------------------------------------------------------
    # **ALERTS, AND ONCE PER EVENT RATHER THAN ONCE A DAY.** Don, 2026-10-18: *"Waiting for cash
    # is a normal state, not a failure ... it alerts Don once. It does not re-alert every cycle
    # and does not burn the ceiling."* So it is a problem in the sense that Don has to act (move
    # money, or decide not to) and NOT in the sense that anything is broken — which is why its
    # once-per-event record lives in the slot's own state rather than in `live_notify`'s daily
    # reminder. Pre-classified by item 74 before this emitter existed; see
    # `DECLARED_AHEAD_OF_EMITTER` below for how that was kept honest.
    "waiting_for_cash": ALERTS,
    # A malformed `LIVE_MIN_TOPUP` refuses the cycle, as a malformed percentage does, so this is
    # a broken input and the slot sends nothing.
    "min_topup_invalid": ALERTS,

    # ---- the daily record: `track_meter` / `/admin/track-row` --------------------------------
    "record_row_missing": ALERTS,
    "recording_not_ok": ALERTS,

    # ---- the rebalance: `valuation/screener/rebalance_watch.py` ------------------------------
    # Don: "any rebalance that can't happen or is late."
    "rebalance_overdue": ALERTS,
    "rebalance_refused": ALERTS,
    # THE HEADS-UP IS AN ALERT AND NOT A RECAP LINE. Its whole job is to arrive while there is
    # still time to renew a data subscription, and a recap is the post Don skims.
    "rebalance_due_soon": ALERTS,

    # ---- the fleet: `valuation/edge/fleet_notify.py` -----------------------------------------
    "fleet_fill": ROUTINE,                # "Fills stay routine."
    "fleet_book_refused": ALERTS,
    "fleet_book_unblocked": ALERTS,       # the good half of the same fact, same channel
    "fleet_selfcheck_failed": ALERTS,
    "fleet_cycle_crashed": ALERTS,

    # ---- the site: `scripts/check_staleness.py`, `auto-scan` ---------------------------------
    "site_data_stale": ALERTS,            # moved off the routine webhook by item 74
    "scan_failed": ALERTS,
    "daily_recap": ROUTINE,               # "The recap stays routine."
    "weekly_recap": ROUTINE,
    "hot_digest": ROUTINE,
    "dip_digest": ROUTINE,
    "scream_buys": ROUTINE,

    # ---- GitHub's own side -------------------------------------------------------------------
    # A scheduled workflow failing cannot be reported by the service, because the service is
    # often the thing that failed. Posted by an `if: failure()` step in the workflow itself.
    "workflow_failed": ALERTS,
    # The manual test button.
    "alert_test": ALERTS,
    "routine_test": ROUTINE,
}

#: **ITEM 73'S TWO KINDS, NOW EMITTED — and this list is empty because its guard said so.**
#:
#: Item 74 classified `waiting_for_cash` and `min_topup_invalid` before item 73 existed, so that
#: its routing would be right on the day it landed rather than a week later, and listed them
#: here as declared-but-unreachable: the `C5` direction (absent is not a measured zero) applied
#: to the registry itself. `tests/test_item74.py` asserts each entry here is still *unemitted* —
#: so the moment item 73 landed its emitters, that test went red and named the two kinds and the
#: remedy. **A forward declaration that cannot tell you when it stopped being one is a comment.**
#:
#: Both are now in `KINDS` proper, above, beside the other live-path kinds. The list stays
#: rather than being deleted: it is the mechanism, and the next item to pre-classify a kind will
#: want it.
DECLARED_AHEAD_OF_EMITTER = ()
for _k in DECLARED_AHEAD_OF_EMITTER:
    KINDS.setdefault(_k, ALERTS)

#: Kinds that live in the tree under the key `kind` and are NOT alerts of any sort. Declared so
#: the registry test can tell "an alert nobody classified" from "a dict that happens to have a
#: `kind` key". Each is a parsing or mapping label, nowhere near a notification.
NOT_ALERT_KINDS = (
    # `valuation/data/headline_rules.py` — how a press-release headline was classified.
    "empty", "filed_by_the_company", "promotional", "salutation", "unattributed",
    # `scripts/ma_dependency_map.py` — how two audit items collide.
    "explicit", "logical",
)


def channel_for(kind: str) -> str:
    """Which channel `kind` goes to. Raises `UnclassifiedAlert` on anything unknown."""
    k = str(kind or "")
    try:
        return KINDS[k]
    except KeyError:
        raise UnclassifiedAlert(
            "alert kind %r is in no channel. Add it to `alert_routing.KINDS` with the reason "
            "beside it. It is not guessed from the name: `account_changed` is one of the most "
            "serious things this path can say and contains no word a rule could key on." % k)


def is_alert(kind: str) -> bool:
    return channel_for(kind) == ALERTS


def split(alerts) -> dict:
    """Partition a list of alert dicts by channel. Unknown kinds are collected, never routed.

    Returning them rather than raising is the one place a refusal would be wrong: a single
    unclassified kind must not cost the cycle every OTHER line it was about to send. The caller
    reports them, and the registry test is what stops one existing in the first place.
    """
    out = {ALERTS: [], ROUTINE: [], "unclassified": []}
    for a in (alerts or []):
        k = str((a or {}).get("kind") or "")
        try:
            out[channel_for(k)].append(dict(a))
        except UnclassifiedAlert:
            out["unclassified"].append(dict(a))
    return out


# =============================================================================================
# WHERE A CHANNEL POSTS, AND THE FALLBACK
# =============================================================================================

def webhook(cfg=None, channel: str = ROUTINE, env=None) -> dict:
    """Resolve a channel to a webhook. Never returns a value in any other field.

    `{"ok", "url", "channel_asked", "channel_used", "prefix", "reason"}` — and `url` is the one
    field carrying a secret, so no caller may log the whole dict. `reason` is written to be safe
    to print and says present/absent only.
    """
    e = os.environ if env is None else env
    ch = str(channel or ROUTINE)
    if ch not in CHANNELS:
        return {"ok": False, "url": "", "channel_asked": ch, "channel_used": None,
                "prefix": "", "reason": "%r is not a channel; expected one of %s"
                                        % (ch, ", ".join(CHANNELS))}

    def _v(name):
        return str(e.get(name) or "").strip()

    # **`cfg` IS THE AUTHORITY WHEN THERE IS ONE, AND THAT KEEPS THE OLD BEHAVIOUR EXACTLY.**
    # `send_discord` read `cfg.discord_webhook_url` and nothing else before item 74, so an
    # env-first rule would make a caller that deliberately passes a cfg with no webhook start
    # posting because the process happened to have the variable set -- a behaviour change
    # smuggled in by a routing change, which is the one thing this item promised not to do.
    # `cfg` is itself built from the environment in production, so this is a no-op there, and
    # the environment is read only when there is no cfg at all (the GitHub-side callers).
    if cfg is not None:
        routine = str(getattr(cfg, "discord_webhook_url", "") or "").strip()
        alert = str(getattr(cfg, "discord_alert_webhook_url", "") or "").strip()
    else:
        routine, alert = _v(ROUTINE_WEBHOOK_VAR), _v(ALERT_WEBHOOK_VAR)

    if ch == ROUTINE:
        return {"ok": bool(routine), "url": routine, "channel_asked": ch,
                "channel_used": (ROUTINE if routine else None), "prefix": "",
                "reason": ("" if routine else "%s is not set" % ROUTINE_WEBHOOK_VAR)}
    if alert:
        return {"ok": True, "url": alert, "channel_asked": ch, "channel_used": ALERTS,
                "prefix": "", "reason": ""}
    if routine:
        # **FALL BACK LOUDLY, NOT SILENTLY.** Don asked for this so nothing goes quiet during
        # setup; the prefix is what stops the fallback becoming the permanent arrangement
        # because it looked like it was working.
        return {"ok": True, "url": routine, "channel_asked": ch, "channel_used": ROUTINE,
                "prefix": FALLBACK_PREFIX + " ",
                "reason": "%s is not set, so this went to the routine channel"
                          % ALERT_WEBHOOK_VAR}
    return {"ok": False, "url": "", "channel_asked": ch, "channel_used": None, "prefix": "",
            "reason": "neither %s nor %s is set, so no alert can be posted at all"
                      % (ALERT_WEBHOOK_VAR, ROUTINE_WEBHOOK_VAR)}


# =============================================================================================
# NOTHING PRIVATE, EVER
# =============================================================================================

#: Environment names whose VALUE must never appear in a message. Used only to look values up and
#: redact them; the names are safe to print and the values are never stored or returned.
SECRET_VARS = (
    ALERT_WEBHOOK_VAR, ROUTINE_WEBHOOK_VAR, PING_KEY_VAR,
    "ADMIN_TOKEN", "ADMIN_WRITE_TOKEN", "SECRET_KEY",
    "ANTHROPIC_API_KEY", "FMP_API_KEY", "TRADIER_TOKEN", "SHARADAR_API_KEY",
    "NASDAQ_DATA_LINK_API_KEY", "ALPACA_API_KEY_ID", "ALPACA_SECRET_KEY",
    "APCA_API_KEY_ID", "APCA_API_SECRET_KEY",
)

#: And every per-slot key pair, whatever the slot number. Matched by SHAPE of the NAME, which is
#: safe — a name pattern decides which values to look up, and the values do the redacting.
SECRET_NAME_RE = re.compile(
    r"(?:^|_)(?:SECRET|TOKEN|PASSWORD|WEBHOOK|KEY_ID|SECRET_KEY|PING_KEY|API_KEY)(?:$|_)|"
    r"ALPACA_ACCOUNT_\d+_", re.I)

REDACTED = "[redacted]"

#: The figures that have a pre-committed horizon and may not be read early off a Discord line.
#: `fleet_notify`'s and `live_notify`'s prohibition, in one place now, with Don's own list added:
#: "no P&L, return or verdict."
RETURN_WORDS = (
    "p&l", "pnl", "p and l", "profit", "unrealized", "unrealised",
    "return", "excess", "alpha", "outperform", "underperform", "beat spy", "vs spy",
    "gain", "loss", "drawdown", "sharpe", "cagr", "verdict", "track record",
)

#: Minimum length for a value to be worth redacting. A one- or two-character environment value
#: would otherwise blank out half the message, and nothing that short is a secret.
MIN_SECRET_LEN = 8


def secret_values(env=None, extra=()) -> list:
    """Every value that must not appear in a message, longest first.

    Longest first matters: a webhook URL contains its own host, so redacting the short value
    first would leave the long one partly intact and unrecognisable to the check.
    """
    e = os.environ if env is None else env
    vals = set()
    for name in SECRET_VARS:
        vals.add(str(e.get(name) or "").strip())
    for name in list(e.keys()):
        if SECRET_NAME_RE.search(str(name)):
            vals.add(str(e.get(name) or "").strip())
    for x in (extra or []):
        vals.add(str(x or "").strip())
    return sorted((v for v in vals if len(v) >= MIN_SECRET_LEN), key=len, reverse=True)


def scrub(text: str, *, env=None, extra=()) -> str:
    """Remove every secret value from a finished message. Redacts by VALUE, never by name.

    `extra` is for identifiers this module cannot know — an Alpaca account id, say, which the
    live path reads from its own record and whose reason text embeds it. The caller supplies the
    strings; this decides nothing about where they came from.
    """
    s = str(text or "")
    for v in secret_values(env, extra):
        if v and v in s:
            s = s.replace(v, REDACTED)
    return s


def secret_violations(text: str, *, env=None, extra=()) -> list:
    """Any configured secret VALUE that appears in this message.

    Reported as REASONS, never as the offending value — a check that prints the secret it found
    has published it to wherever the test output goes.

    **THIS HALF APPLIES TO EVERY MESSAGE ON EVERY CHANNEL.** Nothing legitimate contains a
    webhook URL, an API key or an account identifier, so there is no copy this can refuse that
    anyone wanted sent.
    """
    s = str(text or "")
    return ["a configured secret value appears in the body (%d characters)" % len(v)
            for v in secret_values(env, extra) if v and v in s]


def return_violations(text: str) -> list:
    """Return-shaped words — the figures with a pre-committed horizon.

    **THIS HALF DOES NOT APPLY TO THE PRODUCT CARDS, AND THAT IS A LINE RATHER THAN AN
    OVERSIGHT.** The prohibition comes from `live_notify` and `fleet_notify` — *"§8's horizon is
    pre-committed and a Discord line is not where a figure gets read early"* — and it is about
    the OPERATIONAL posts. The routine product cards are a different, long-settled surface with
    their own copy authority (`web.dip_posture.violations`, asserted against the rendered
    payload), and the hot digest and the scream-buy card legitimately carry scores and the
    confidence caveat, which itself contains the word "profit". Re-gating them here would be a
    second copy authority over text that already has one — the `B7` family — and it would have
    silently stopped a card this project ships today.

    So: operational bodies are gated, product cards are not, and each is gated in exactly one
    place. `live_notify` and `fleet_notify` keep their own tests on their own composers, which is
    where the words would be introduced.
    """
    low = str(text or "").lower()
    return ["the body carries the return-shaped word %r" % w for w in RETURN_WORDS if w in low]


def violations(text: str, *, env=None, extra=(), check_returns: bool = True) -> list:
    """Everything that must not be in this message and is. Empty is the only acceptable answer."""
    out = secret_violations(text, env=env, extra=extra)
    if check_returns:
        out.extend(return_violations(text))
    return out


# =============================================================================================
# THE NOISE RULE
# =============================================================================================
#
# Don, 2026-10-18, verbatim: "one post when a problem starts; one when it clears; one reminder
# per day while it stays broken."

#: One reminder per DAY, keyed on the calendar date rather than on an elapsed-hours count. A
#: 24-hour rule and a daily rule differ by exactly the amount that makes a reminder drift later
#: every day until it lands in the middle of the night, and this path already runs five times a
#: day on a scheduler measured 3.45-7.48 hours late.
def needs_reminder(last_reminded, today=None) -> bool:
    """Is a still-broken condition due its daily reminder?

    `last_reminded` is an ISO date (or datetime prefix) or empty. Unreadable reads as DUE, which
    is the loud direction: a reminder nobody needed is noise, a reminder nobody got is silence.
    """
    d = _as_date(today) or _dt.date.today()
    prev = _as_date(last_reminded)
    if prev is None:
        return True
    return prev < d


def _as_date(x):
    if x is None or x == "":
        return None
    if isinstance(x, _dt.datetime):
        return x.date()
    if isinstance(x, _dt.date):
        return x
    s = str(x).strip()[:10]
    try:
        return _dt.date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None


def today_stamp(now=None) -> str:
    d = _as_date(now) or _dt.date.today()
    return d.isoformat()


# =============================================================================================
# THE MESSAGE SHAPE
# =============================================================================================

def compose_alert(what_broke: str, what_it_means: str, what_to_do: str) -> str:
    """Don's three short lines, in his order: what broke, what it means, what to do.

    A shared composer rather than a convention, because the third line is the one that gets
    dropped when a message is written in a hurry, and a problem report with no action is the
    thing the fleet's own note records eighteen books sitting behind for weeks.
    """
    return "\n".join([
        "**%s**" % str(what_broke or "").strip(),
        str(what_it_means or "").strip(),
        str(what_to_do or "").strip(),
    ])


#: What goes out INSTEAD of a message that failed the privacy gate. Blocking and sending nothing
#: would make a leak indistinguishable from a quiet day, which is the worse of the two failures;
#: sending the body anyway publishes the thing Don said must never be published. So the body is
#: replaced and the pointer survives.
BLOCKED_LINE = ("A Valquo alert was composed and NOT posted: its text failed the "
                "nothing-private check. Open the latest workflow run to read it.")


def safe_body(text: str, *, env=None, extra=(), check_returns: bool = False) -> dict:
    """The body as it may actually be sent. `{"text", "scrubbed", "blocked", "why"}`.

    Two steps, in this order and for different reasons. `scrub` removes a configured secret by
    VALUE and is lossless for every legitimate word, so it always runs and then the secret check
    should find nothing -- it runs anyway, because a scrubber that silently failed to match would
    otherwise be indistinguishable from a message that was clean. If anything survives, the body
    is REPLACED rather than dropped: see `BLOCKED_LINE`.

    `check_returns` defaults to **False** so that adding this gate to `send_discord` cannot
    refuse a product card that ships today. See `return_violations` for why that line is drawn
    where it is.
    """
    raw = str(text or "")
    clean = scrub(raw, env=env, extra=extra)
    bad = violations(clean, env=env, extra=extra, check_returns=check_returns)
    if bad:
        return {"text": BLOCKED_LINE, "scrubbed": clean != raw, "blocked": True, "why": bad}
    return {"text": clean, "scrubbed": clean != raw, "blocked": False, "why": []}
