"""
Daily + weekly Discord recap of the forward paper track (options book + Valquo Index vs SPY).

WHY IT ONLY READS. Every number here already exists somewhere that has been tested:
`options_tracker.record_outcome` computes each trade's P&L from the premiums it was logged
against, `options_tracker.scorecard` defines expectancy, and `paper_track.index_summary`
defines the index-vs-SPY record. This module re-derives NONE of them. A recap that computed
its own P&L would eventually disagree with the API and the Signals tab, and the version people
read in Discord is the one they would believe.

WHAT IT IS ALLOWED TO SAY. The paper track is days old. So:

  * Every post is stamped "paper (Tradier sandbox), since <date>" and carries the `thin`
    label straight from `paper_track._label` — the same string the API serves, so the recap
    cannot quietly grade the track more generously than the product does.
  * The backtested options expectancy is quoted as a REFERENCE next to the realized one,
    never as a target or a promise, and always with the fade caveat (the full-sample +10.4%
    a trade is +4.4% in the recent half).
  * Options are described as CONVEX — ~37% of trades win, most lose a little and a few win
    big. The word "win rate" never appears next to a confidence or a quality claim, because
    a 37% hit rate reads as failure to anyone who has not been told the shape of the payoff.
  * With no closed trades it says "no closed trades yet" and stops. Reporting a 0% hit rate
    and $0 expectancy on an empty book is not neutral — it looks like a measured result.

IDEMPOTENCY. `post()` marks the day in the same `alerts_sent` table the scream-buy de-dupe
uses, so the two DST-straddling crons (and any manual re-run) produce exactly one post per
kind per day. FAILS QUIET: no webhook configured is a normal state that returns
`posted: False` with a reason — never an exception, because this runs in the same cron family
as the paper track itself and a missing optional secret must not turn a healthy run red.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from ..edge import paper_track as PT
from ..edge.options_confidence import (FULL_SAMPLE_EXPECTANCY, HIT_RATE,
                                       LATE_HALF_EXPECTANCY)
from .notify import send_discord

KINDS = ("daily", "weekly")

# One de-dupe key per kind. `alerts_sent` is keyed by an upper-cased "ticker", so these
# sentinels look like the `__HOTDIGEST__` one the hot digest already uses and cannot collide
# with a real symbol.
_DEDUPE_KEY = {"daily": "__RECAP_DAILY__", "weekly": "__RECAP_WEEKLY__"}

# The weekly window, in calendar days back from the post date. 7 covers exactly one Mon-Fri
# when it runs on its Friday cron, and degrades sensibly if it ever runs a day late.
WEEK_DAYS = 7

# Discord hard-rejects over 2000 characters and `send_discord` truncates at 1900 — from the
# END, which is where the disclaimer and the convexity caveat live. A recap that loses
# "educational only" to a long list of trades is the one failure this file cannot allow, so
# the body is trimmed to fit BEFORE it is sent. See `_fit`.
MAX_CHARS = 1900

_FOOTER = ("_Educational only, not investment advice. Paper account — no real money and no "
           "real orders; sandbox fills on ~15-minute-delayed quotes._")

# Said in full on the weekly post and in short on the daily one. The hit rate is the number
# most likely to be misread, so it is never quoted without the shape of the payoff attached.
_CONVEXITY = (f"Options here are CONVEX, not high-probability: the backtest hits "
              f"{HIT_RATE:.0%} of the time — most trades lose a little and a few win big. "
              f"Hit rate alone says nothing about whether this works.")


# ------------------------------------------------------------------ formatting
def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _pct(x, nd: int = 1, signed: bool = True) -> str:
    """A fraction as a percent. Missing reads as an em dash, never as zero."""
    v = _f(x)
    if v is None:
        return "—"
    return f"{v * 100:+.{nd}f}%" if signed else f"{v * 100:.{nd}f}%"


def _pp(x, nd: int = 2) -> str:
    v = _f(x)
    return "—" if v is None else f"{v * 100:+.{nd}f} pp"


def _money(x) -> str:
    v = _f(x)
    return "—" if v is None else f"{'+' if v >= 0 else '-'}${abs(v):,.0f}"


def _d(x) -> Optional[_dt.date]:
    try:
        return _dt.date.fromisoformat(str(x)[:10])
    except (TypeError, ValueError):
        return None


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _fit(lines: list, keep_tail: int, limit: int = MAX_CHARS) -> str:
    """Join `lines`, dropping indented DETAIL lines until it fits inside Discord's limit.

    `keep_tail` is how many trailing lines are the caveats. They are never candidates for
    removal, and they are what a naive truncation would have eaten first: a post that loses
    "educational only, not investment advice" because six trades closed that day is exactly
    backwards. Detail lines (the per-trade rows) are dropped oldest-first and replaced with a
    count, so the reader is told the list was shortened rather than shown a silent subset.
    """
    body, tail = list(lines[:len(lines) - keep_tail]), list(lines[len(lines) - keep_tail:])
    mark = "    …detail trimmed to fit Discord's message limit"
    dropped, at = 0, None

    def size():
        return len("\n".join(body + ([mark] if dropped else []) + tail))

    while size() > limit:
        i = next((j for j, ln in enumerate(body) if ln.startswith("    ")), None)
        if i is None:
            break
        body.pop(i)
        at = i if at is None else min(at, i)
        dropped += 1
    if dropped:
        body.insert(min(at, len(body)), mark)
    text = "\n".join(body + tail)
    if len(text) > limit:                    # nothing left to drop; protect the caveats
        head = "\n".join(body)[:max(0, limit - len("\n".join(tail)) - 2)]
        text = head + "\n" + "\n".join(tail)
    return text


def _contract(row: dict) -> str:
    """A human contract id from what the paper row stores, degrading to the OCC symbol."""
    t = row.get("ticker") or "?"
    exp = str(row.get("expiry") or "")[:10]
    return f"{t} {exp}".strip() if exp else str(t)


# ------------------------------------------------------------------ reading the book
def _closed_paper_trades(store) -> list:
    """Closed PAPER options trades with the P&L the tracker already computed.

    LEFT JOIN, and a fallback to the stored premiums, because `record_outcome` declines to
    score a row that has no entry premium — such a trade is closed but unscoreable, and it
    should appear in the recap as closed-without-a-number rather than vanish from it.
    """
    PT.ensure_schema(store)
    sql = """SELECT p.alert_id, p.ticker, p.occ_symbol, p.expiry, p.contracts,
                    p.entry_premium, p.exit_premium, p.exit_ts, p.exit_reason,
                    a.pnl_pct AS pnl_pct, a.pnl_dollars AS pnl_dollars
             FROM paper_option_orders p
             LEFT JOIN option_alerts a ON a.id = p.alert_id
             WHERE p.state = 'closed'
             ORDER BY p.exit_ts"""
    with store._conn() as c:
        cur = c.execute(sql)
        keys = [k[0] for k in cur.description]
        rows = [dict(zip(keys, r)) for r in cur.fetchall()]
    for r in rows:
        if r.get("pnl_pct") is None:
            entry, ex = _f(r.get("entry_premium")), _f(r.get("exit_premium"))
            if entry and entry > 0 and ex is not None:
                r["pnl_pct"] = ex / entry - 1.0
                r["pnl_dollars"] = (ex - entry) * 100.0 * max(1, int(r.get("contracts") or 1))
    return rows


def _index_history(store) -> list:
    with store._conn() as c:
        cur = c.execute("SELECT as_of, index_ret, bench_ret, active_ret, n_positions, n_priced "
                        "FROM paper_index_track ORDER BY as_of")
        keys = [k[0] for k in cur.description]
        return [dict(zip(keys, r)) for r in cur.fetchall()]


def _holdings_added(store, since: str) -> list:
    with store._conn() as c:
        return [r[0] for r in c.execute(
            "SELECT ticker FROM paper_index_holdings WHERE entry_date >= ? ORDER BY ticker",
            (since,))]


def _delta(rows: list, back: int) -> Optional[dict]:
    """Change over the last `back` recorded points. None when there is no earlier point.

    Deliberately measured in RECORDED points rather than calendar days: if the cycle missed a
    session, "since the previous point" is the honest window and pretending it was one day
    would attribute two days of drift to one.
    """
    if len(rows) < back + 1:
        return None
    now, then = rows[-1], rows[-1 - back]
    out = {"from": then["as_of"], "to": now["as_of"], "points": back}
    for k in ("index_ret", "bench_ret"):
        a, b = _f(now.get(k)), _f(then.get(k))
        out[k] = (1.0 + a) / (1.0 + b) - 1.0 if (a is not None and b is not None) else None
    if out["index_ret"] is not None and out["bench_ret"] is not None:
        out["active_ret"] = out["index_ret"] - out["bench_ret"]
    else:
        out["active_ret"] = None
    return out


def collect(store, day=None, window_days: int = WEEK_DAYS) -> dict:
    """Everything both posts need, read from the tracked record. Computes no P&L of its own."""
    today = _d(day) or _dt.date.today()
    since = (today - _dt.timedelta(days=window_days)).isoformat()
    day_iso = today.isoformat()

    opt = PT.options_summary(store)
    idx = PT.index_summary(store)
    closed = _closed_paper_trades(store)
    hist = _index_history(store)

    opened_today = [r["ticker"] for r in PT.paper_orders(store, states=("open", "submitted"))
                    if str(r.get("entry_ts") or "")[:10] == day_iso]
    closed_today = [r for r in closed if str(r.get("exit_ts") or "")[:10] == day_iso]
    closed_week = [r for r in closed if str(r.get("exit_ts") or "")[:10] >= since]

    scored = [r for r in closed_week if _f(r.get("pnl_pct")) is not None]
    ranked = sorted(scored, key=lambda r: _f(r.get("pnl_pct")))
    return {
        "day": day_iso,
        "since": since,
        "options": {
            "summary": opt,
            "opened_today": opened_today,
            "closed_today": closed_today,
            "closed_week": closed_week,
            "week_pnl_dollars": sum(_f(r.get("pnl_dollars")) or 0.0 for r in closed_week),
            "best": ranked[-1] if ranked else None,
            "worst": ranked[0] if ranked else None,
        },
        "index": {
            "summary": idx,
            "day": _delta(hist, 1),
            "week": _delta(hist, min(5, len(hist) - 1)) if len(hist) > 1 else None,
            "added_since": _holdings_added(store, since),
            "added_today": _holdings_added(store, day_iso),
            "points_in_window": [r for r in hist if r["as_of"] >= since],
        },
    }


# ------------------------------------------------------------------ health
def health_note(data: dict, day=None) -> str:
    """One honest line: did the cycle actually run, and is anything stuck.

    The index book records exactly one point per session it ran, so counting points against
    the trading days in the window is a real liveness check rather than a restatement of the
    numbers above it. A gap here is the failure mode that matters most — a forward track that
    silently stops recording is indistinguishable from one that is doing fine.
    """
    from ..screener.market_session import is_trading_day

    idx = data["index"]["summary"]
    if not idx.get("started"):
        return ("Health: the index book has not recorded a session yet, so there is nothing to "
                "check for gaps.")

    today = _d(day) or _dt.date.today()
    expected = [today - _dt.timedelta(days=i) for i in range(WEEK_DAYS)]
    # Only sessions on or after inception count. Without this a track that started yesterday
    # reports "1/5 sessions" and cries about a hole every day of its first week — a watchdog
    # that is wrong at exactly the moment you are watching it teaches you to ignore it.
    born = _d(idx.get("inception"))
    expected = [d for d in expected if is_trading_day(d) and (born is None or d >= born)]
    got = {r["as_of"] for r in data["index"]["points_in_window"]}
    ran = sum(1 for d in expected if d.isoformat() in got)

    bits = [f"cycle recorded {ran}/{len(expected)} sessions since "
            f"{'inception' if born and born > today - _dt.timedelta(days=WEEK_DAYS) else f'{WEEK_DAYS} days ago'}"]
    by_state = (data["options"]["summary"].get("by_state") or {})
    stuck = by_state.get("claimed", 0) + by_state.get("closing", 0)
    if stuck:
        bits.append(f"{stuck} option order(s) mid-flight")
    if by_state.get("rejected"):
        bits.append(f"{by_state['rejected']} rejected by the broker")
    if ran < len(expected):
        bits.append("**a missed session means the track has a hole in it, not a flat day**")
    return "Health: " + "; ".join(bits) + "."


# ------------------------------------------------------------------ the posts
def _label(data: dict) -> str:
    """The honesty stamp, taken from whichever book has actually started."""
    opt, idx = data["options"]["summary"], data["index"]["summary"]
    return opt.get("label") if opt.get("started") else idx.get("label")


def _options_block(data: dict, weekly: bool = False) -> list:
    o = data["options"]
    s = o["summary"]
    sc = s.get("scorecard") or {}
    n_closed = sc.get("n_closed") or 0
    lines = ["**Options (scream-buy paper book)**"]

    if not s.get("started"):
        lines.append("• Not started — no alert has been submitted to the paper account yet.")
        return lines

    lines.append(f"• Live now: {s.get('n_live', 0)} · opened today: {len(o['opened_today'])}"
                 + (f" ({', '.join(o['opened_today'][:6])})" if o["opened_today"] else ""))

    shown = o["closed_week"] if weekly else o["closed_today"]
    if shown:
        lines.append(f"• Closed {'this week' if weekly else 'today'}: {len(shown)}")
        for r in shown[:6]:
            pnl = _f(r.get("pnl_pct"))
            amt = (f"{_pct(pnl)} ({_money(r.get('pnl_dollars'))})" if pnl is not None
                   else "closed without a scoreable entry premium")
            lines.append(f"    {_contract(r)} — {amt} · {r.get('exit_reason') or 'exit'}")
        if len(shown) > 6:
            lines.append(f"    …and {len(shown) - 6} more")
    else:
        lines.append(f"• Closed {'this week' if weekly else 'today'}: none")

    # Realized expectancy vs the backtest — the comparison this whole track exists to make.
    if not n_closed:
        lines.append("• **No closed trades yet** — nothing to score. Expectancy, hit rate and "
                     "P&L stay blank rather than being reported as zero.")
        return lines

    lines.append(f"• To date: {n_closed} closed · expectancy {_pct(sc.get('expectancy_pct'))}"
                 f"/trade · {_money(sc.get('cum_pnl_dollars'))} on a 1-contract basis")
    if weekly:
        # A RATE is only quoted once the sample can carry one. "hit rate 100%" off a single
        # winner is the most flattering and least true number this post could contain, so
        # below the floor it is stated as a raw count instead.
        hits = _f(sc.get("hit_rate"))
        won = int(round((hits or 0) * n_closed))
        rate = (_pct(hits, nd=0, signed=False) if sc.get("enough_to_tune")
                else f"{won} of {n_closed} won (too few to read as a rate)")
        lines.append(f"    hit rate {rate} · avg win {_pct(sc.get('avg_win_pct'))} "
                     f"· avg loss {_pct(sc.get('avg_loss_pct'))}")
    lines.append(f"• Backtest reference: {FULL_SAMPLE_EXPECTANCY:+.1%}/trade full-sample, "
                 f"{LATE_HALF_EXPECTANCY:+.1%} in the recent half. A reference point, not a "
                 f"target and not a promise.")
    if not sc.get("enough_to_tune"):
        lines.append(f"    {n_closed} closed is below the {sc.get('min_required')}-trade floor "
                     f"— too few to mean anything yet.")
    return lines


def _index_block(data: dict, weekly: bool = False) -> list:
    i = data["index"]
    s = i["summary"]
    lines = ["**Valquo Index vs SPY (paper)**"]
    if not s.get("started"):
        lines.append(f"• Not started — {s.get('n_holdings', 0)} holdings seeded, no marked "
                     f"session yet.")
        return lines

    day = i["day"]
    if day:
        lines.append(f"• Since the previous point ({day['from']} → {day['to']}): "
                     f"index {_pct(day['index_ret'], nd=2)}, SPY {_pct(day['bench_ret'], nd=2)} "
                     f"→ {_pp(day['active_ret'])}")
    else:
        lines.append("• First recorded session — no previous point to compare with yet.")

    # Suppressed when the week is only one point long: it would restate the line above it
    # under a wider-sounding label, which reads as more evidence than there is.
    if weekly and i["week"] and i["week"]["points"] > 1:
        w = i["week"]
        lines.append(f"• This week ({w['from']} → {w['to']}, {_plural(w['points'], 'session')}): "
                     f"index {_pct(w['index_ret'], nd=2)}, SPY {_pct(w['bench_ret'], nd=2)} "
                     f"→ {_pp(w['active_ret'])}")

    lines.append(f"• Since inception {s.get('inception')} "
                 f"({_plural(s.get('n_days') or 0, 'session')}): "
                 f"index {_pct(s.get('index_ret'), nd=2)}, SPY {_pct(s.get('bench_ret'), nd=2)} "
                 f"→ **{_pp(s.get('active_ret'))}**")
    lines.append(f"• {s.get('n_holdings')} holdings, {s.get('n_priced')} priced against SPY"
                 + (f" · added today: {', '.join(i['added_today'][:8])}"
                    if i["added_today"] else " · no holdings changes today"))
    if not s.get("meaningful"):
        lines.append(f"    {s.get('n_days')} sessions is far short of the "
                     f"{s.get('min_days_for_meaning')} needed before this means anything.")
    return lines


def daily_text(data: dict) -> str:
    lines = [f"📄 **Valquo paper track — {data['day']}**", f"_{_label(data)}_", ""]
    lines += _options_block(data, weekly=False) + [""]
    lines += _index_block(data, weekly=False) + [""]
    lines.append(f"_{_CONVEXITY}_")
    lines.append(_FOOTER)
    return _fit(lines, keep_tail=2)


def weekly_text(data: dict) -> str:
    o = data["options"]
    lines = [f"🗓️ **Valquo paper track — week to {data['day']}**", f"_{_label(data)}_", ""]
    lines += _options_block(data, weekly=True)
    best, worst = o["best"], o["worst"]
    if best is not None:
        # With one scored trade, "best" and "worst" are the same row. Naming it twice implies
        # a spread that does not exist.
        if worst is not None and worst is not best:
            lines.append(f"• Best this week: {_contract(best)} {_pct(best.get('pnl_pct'))}"
                         f" · worst: {_contract(worst)} {_pct(worst.get('pnl_pct'))}")
        else:
            lines.append(f"• Only scored trade this week: {_contract(best)} "
                         f"{_pct(best.get('pnl_pct'))}")
        lines.append(f"• Week P&L (closed trades, 1 contract each): "
                     f"{_money(o['week_pnl_dollars'])}")
    lines.append("")
    lines += _index_block(data, weekly=True) + [""]
    lines.append(health_note(data, day=data["day"]))
    lines.append(f"_{_CONVEXITY}_")
    lines.append(_FOOTER)
    return _fit(lines, keep_tail=3)


def build(store, kind: str = "daily", day=None) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown recap kind {kind!r}")
    data = collect(store, day=day)
    return weekly_text(data) if kind == "weekly" else daily_text(data)


def post(cfg, store, kind: str = "daily", day=None, force: bool = False) -> dict:
    """Build and post one recap. At most one per kind per day unless `force`.

    Returns a result dict in every path and raises only on a genuinely broken call (an unknown
    kind). A missing webhook, an already-posted day and a Discord outage are all normal states
    that must not fail the cron around them.
    """
    if kind not in KINDS:
        raise ValueError(f"unknown recap kind {kind!r}")
    day_iso = (_d(day) or _dt.date.today()).isoformat()
    key = _DEDUPE_KEY[kind]

    if not getattr(cfg, "discord_webhook_url", ""):
        return {"posted": False, "kind": kind, "day": day_iso,
                "reason": "no DISCORD_WEBHOOK_URL configured"}
    if not force and store.alerted_today(key, day=day_iso):
        return {"posted": False, "kind": kind, "day": day_iso, "duplicate": True,
                "reason": "already posted for this day"}

    text = build(store, kind=kind, day=day_iso)
    if not send_discord(cfg, text):
        # NOT marked: a failed post must be retryable by the backup cron, and marking it here
        # would burn the day's single slot on a message nobody received.
        return {"posted": False, "kind": kind, "day": day_iso, "chars": len(text),
                "reason": "Discord did not accept the post"}
    store.mark_alerted(key, day_iso, day=day_iso)
    return {"posted": True, "kind": kind, "day": day_iso, "chars": len(text)}
