"""
Screaming-buy alerts.

Finds the highest-conviction bullish intraday setups and pushes them out:
  * Discord — an owner-level webhook that posts to your channel (opt-in = you set
    DISCORD_WEBHOOK_URL).
  * Email  — per-user, DEFAULT OFF. Users must opt in, and every email carries a
    one-click unsubscribe.
De-duped to at most one alert per ticker per day so you're not pinged every scan.
In-app notifications will hang off the same run_alerts() once the desktop app ships.
"""
from __future__ import annotations

from itsdangerous import URLSafeSerializer, BadSignature

from .emailer import send_email

_UNSUB_SALT = "alerts-unsub"

# A high score alone isn't "screaming" — require a genuinely bullish tag too.
_BULL = ("Call-heavy", "Unusual call volume", "Breakout", "Golden cross", "Uptrend", "MACD bullish")


def unsub_token(cfg, user_id) -> str:
    return URLSafeSerializer(cfg.secret_key, salt=_UNSUB_SALT).dumps(user_id)


def unsub_user_id(cfg, token):
    try:
        return URLSafeSerializer(cfg.secret_key, salt=_UNSUB_SALT).loads(token)
    except BadSignature:
        return None


def screaming_buys(rows, min_score, term_mode=None) -> list:
    """Scream-buy alerts, gated by the phase-3b term-structure read."""
    return screaming_buys_with_stats(rows, min_score, term_mode)[0]


def screaming_buys_with_stats(rows, min_score, term_mode=None):
    """`screaming_buys`, plus what the term gate did. Returns (picks, term_stats).

    `term_mode` defaults to the config flag, now "suppress": the filter removes ~60% of signals
    and is the single thing arresting the fade, so leaving it as an annotation meant the live
    alerts carried the full fade. "flag" is still one env var away. Missing term data is never
    suppressed - a quote outage must not read as backwardation.

    The stats exist so the live discard rate can be compared against the backtested 40.6%
    retention. A live retention nowhere near it means the threshold did not transfer between IV
    estimators, which is invisible if nobody counts.
    """
    from ..intraday import term_filter as TF

    out = []
    for r in rows or []:
        s = r.get("score")
        labels = r.get("labels") or []
        if s is not None and s >= min_score and any(any(b in l for b in _BULL) for l in labels):
            out.append(r)
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    if term_mode is None:
        try:
            from ..config import CONFIG
            term_mode = getattr(CONFIG, "options_term_filter", TF.DEFAULT_MODE)
        except Exception:                                            # noqa: BLE001
            term_mode = TF.DEFAULT_MODE
    return TF.apply_with_stats(out, mode=term_mode)


def send_discord(cfg, content: str) -> bool:
    url = getattr(cfg, "discord_webhook_url", "")
    if not url:
        return False
    try:
        import requests
        r = requests.post(url, json={"content": content[:1900]}, timeout=10)
        return r.status_code < 300
    except Exception:
        return False


def _idea(r) -> str:
    c = ((r.get("detail") or {}).get("contracts") or {}).get("swing") or {}
    return c.get("directional", "")


# Shown on every alert that carries a confidence level. The backtested hit rate is 37%, so a
# level must never be read as a chance of winning - see edge/options_confidence.py.
_CONF_CAVEAT = ("Confidence = strength of backtested EXPECTANCY, not chance of profit "
                "(hit rate ~37%: most trades lose a little, a few win big).")


def _live_line(a) -> str:
    """The concrete trade, when a real contract was resolved. Empty string when not."""
    if not a:
        return ""
    c, s, conf = a.get("contract"), a.get("sizing") or {}, a.get("confidence") or {}
    if not c:
        return ""
    bits = [f"${c['strike']:g} call {c['expiry']} ({c['dte']}d, "
            f"{abs(c.get('delta') or 0):.2f}Δ) @ ~${c['entry_premium']:.2f}"]
    if not s.get("skip"):
        bits.append(f"{s['contracts']}x = ${s['dollar_risk']:,.0f} at risk")
    elif s.get("reason"):
        bits.append(f"no size: {s['reason']}")
    if conf.get("level"):
        bits.append(f"confidence {conf['level']}")
    return "  ·  ".join(bits)


def _by_ticker(live_alerts):
    return {a.get("ticker"): a for a in (live_alerts or []) if a.get("ticker")}


def alert_discord_text(run_time, rows, live_alerts=None) -> str:
    by = _by_ticker(live_alerts)
    lines = [f"🚨 **Valquo — Screaming buys** — {run_time}"]
    for r in rows[:10]:
        labs = ", ".join((r.get("labels") or [])[:3])
        lines.append(f"• **{r['ticker']}**  score {r.get('score', 0):.0f} — {labs}")
        live = _live_line(by.get(r["ticker"]))
        # Fall back to the descriptor only when no real contract could be resolved, so a
        # chain outage reads as a vaguer alert rather than silently as a different one.
        lines.append(f"    {live}" if live else f"    {_idea(r)}")
    if any(_live_line(by.get(r["ticker"])) for r in rows[:10]):
        lines.append(f"_{_CONF_CAVEAT} Suggestion only — Valquo never places trades._")
    lines.append("_Educational only, not investment advice._")
    return "\n".join(lines)


def alert_email_html(run_time, rows, unsub_url, live_alerts=None) -> str:
    by = _by_ticker(live_alerts)
    trs = "".join(
        f"<tr><td><b>{r['ticker']}</b></td><td style='text-align:right'>{r.get('score', 0):.0f}</td>"
        f"<td>{', '.join((r.get('labels') or [])[:3])}</td>"
        f"<td>{_live_line(by.get(r['ticker'])) or _idea(r)}</td></tr>" for r in rows[:10])
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1f3864">🚨 Screaming buys</h2>
      <p style="color:#555">Intraday scan {run_time}. High-conviction bullish setups.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr style="color:#888;text-align:left"><th>Ticker</th><th style="text-align:right">Score</th>
          <th>Signals</th><th>Contract &amp; size</th></tr>
        {trs}
      </table>
      <p style="color:#999;font-size:12px;margin-top:16px">{_CONF_CAVEAT} Position sizes are a
      SUGGESTION against a fixed dollar risk budget — Valquo never places trades.<br>
      Educational only, not investment advice — technical/options
      signals are not a proven edge and this is not an autotrader. Verify on the live chain.<br>
      You opted in to these alerts. <a href="{unsub_url}">Unsubscribe</a> anytime.</p>
    </div>"""


def hot_digest_text(scan_date, rows, sectors=None) -> str:
    """A monospaced, at-a-glance top-10 for Discord."""
    top = rows[:10]
    lines = [f"🔥 **Valquo — Hot Stocks of the Day** — {scan_date}", "```",
             f"{'#':<3}{'Ticker':<8}{'Score':<7}{'Sector':<16}{'Price':>9}"]
    for r in top:
        price = r.get("price")
        lines.append(f"{str(r.get('rank', '')):<3}{(r.get('ticker') or ''):<8}"
                     f"{(r.get('hot_score') or 0):<7.0f}{(r.get('sector') or '')[:15]:<16}"
                     f"{('$' + format(price, ',.2f')) if price else '—':>9}")
    lines.append("```")
    if sectors:
        lines.append("Hottest sectors: **" + ", ".join(s["sector"] for s in sectors[:4]) + "**")
    lines.append("_Educational only, not investment advice._")
    return "\n".join(lines)


def post_hot_digest(cfg, store, scan_date, rows, sectors=None) -> bool:
    """Post the daily top-10 to Discord, at most once per day."""
    if not getattr(cfg, "discord_webhook_url", "") or store.alerted_today("__HOTDIGEST__"):
        return False
    if send_discord(cfg, hot_digest_text(scan_date, rows, sectors)):
        store.mark_alerted("__HOTDIGEST__", scan_date)
        return True
    return False


def run_alerts(cfg, store, users) -> dict:
    """New screaming buys from the latest intraday snapshot → Discord + opt-in email.
    De-dupes per ticker per day. Safe to call after every intraday scan."""
    run_time = store.latest_intraday_time()
    rows = store.load_intraday()
    picks, term_stats = screaming_buys_with_stats(rows, cfg.alert_min_score)
    picks = [r for r in picks if not store.alerted_today(r["ticker"])]
    if not picks:
        return {"new": 0, "emails": 0, "tickers": [], "term_filter": term_stats}
    # Resolve each alert to a REAL contract on the live chain, so the paper book records a
    # priceable trade rather than a descriptor. Never allowed to break the alert path.
    live = []
    try:
        live = build_live_alerts(cfg, picks)
    except Exception as e:                                  # pragma: no cover - defensive
        import sys
        print(f"[alerts] live contract resolution failed (alerts still sent): {e}",
              file=sys.stderr)
    send_discord(cfg, alert_discord_text(run_time, picks, live_alerts=live))
    sent = 0
    for u in users.alert_subscribers():
        unsub = f"{cfg.public_base_url}/alerts/unsubscribe/{unsub_token(cfg, u['id'])}"
        if send_email(cfg, u["email"], "🚨 Screaming buys",
                      alert_email_html(run_time, picks, unsub, live_alerts=live)):
            sent += 1
    # Log every alert with its CONTRACT and fingerprint, so expectancy can be scored later.
    # Never allowed to break the alert path: a logging failure must not stop a notification.
    logged = 0
    try:
        logged = log_scream_buys(store, run_time, picks, live_alerts=live)
    except Exception as e:                                  # pragma: no cover - defensive
        import sys
        print(f"[alerts] contract logging failed (alerts still sent): {e}", file=sys.stderr)
    for r in picks:
        store.mark_alerted(r["ticker"], run_time)
    return {"new": len(picks), "emails": sent, "logged": logged,
            "tickers": [r["ticker"] for r in picks], "term_filter": term_stats,
            "with_contract": sum(1 for a in live if a.get("contract"))}


def build_live_alerts(cfg, picks) -> list:
    """Resolve scan rows to real contracts + confidence + sizing on the LIVE chain.

    Kept here rather than in the scan because the chain fetch is several calls per name: it runs
    only for names that already cleared the alert bar, never for the whole universe.
    """
    from ..edge.options_live import build_alerts
    from ..intraday.providers import get_provider

    budget = getattr(cfg, "options_risk_per_trade", None) or 1000.0
    alerts, _ = build_alerts(picks, provider=get_provider(cfg), risk_budget=float(budget))
    return alerts


def log_scream_buys(store, run_time, picks, live_alerts=None) -> int:
    """Persist each scream-buy alert + its contract, for the forward paper book.

    UPGRADED (roadmap #21): when `live_alerts` carries a contract resolved from the real broker
    chain, the strike/expiry/premium are the actual ones and the row is SCOREABLE - which is the
    whole point of the paper book, since a row with no entry premium can never produce a P&L.

    It still degrades to the old descriptor behaviour when the chain is unavailable, because an
    alert with a fingerprint and no strike is worth more than no record at all. `contract_source`
    records which of the two happened, so "the paper book is empty" and "the chain has been down
    for a week" cannot be confused.
    """
    from ..edge.options_tracker import log_alert
    by_ticker = {a.get("ticker"): a for a in (live_alerts or []) if a.get("ticker")}
    n = 0
    for r in picks or []:
        d = r.get("detail") or {}
        cs = (d.get("contracts") or {})
        horizon = "swing" if "swing" in cs else (sorted(cs)[0] if cs else None)
        c = (cs.get(horizon) or {}) if horizon else {}
        a = by_ticker.get(r.get("ticker")) or {}
        lc = a.get("contract") or {}
        conf, sizing = a.get("confidence") or {}, a.get("sizing") or {}
        n += 1 if log_alert(store, {
            "alert_ts": run_time, "ticker": r.get("ticker"),
            "opt_right": lc.get("right") or (
                "put" if str(c.get("directional", "")).find("put") >= 0 else "call"),
            "strike": lc.get("strike") if lc else c.get("strike"),
            "expiry": lc.get("expiry") if lc else c.get("expiry"),
            "entry_premium": lc.get("entry_premium") if lc else (c.get("mid") or c.get("premium")),
            "underlying_price": r.get("price"),
            "score": r.get("score"),
            "momentum_score": d.get("momentum_score") or r.get("momentum_score"),
            "technical_score": d.get("technical_score") or r.get("technical_score"),
            "iv": lc.get("iv") or c.get("iv") or d.get("iv"), "iv_rank": d.get("iv_rank"),
            "horizon": horizon,
            "target_delta": lc.get("delta") if lc else c.get("delta"),
            "dte": lc.get("dte") if lc else c.get("dte"),
            "flow_read": next((l for l in (r.get("labels") or [])
                               if "call" in l.lower() or "put" in l.lower()), None),
            "labels": r.get("labels") or [],
            "features": {
                "exit_policy": lc.get("exit_policy") or {"target_pct": 1.00, "stop_pct": -0.50,
                                                         "time_stop_frac": 0.50},
                "contract_source": "live chain" if lc else "descriptor (no chain)",
                "term": {k: a.get("term", {}).get(k) for k in ("term_slope", "term_ok", "source")}
                        if a.get("term") else None,
                "confidence": {k: conf.get(k) for k in
                               ("level", "expectancy_estimate", "min_bucket_n")} or None,
                "sizing": {k: sizing.get(k) for k in
                           ("contracts", "dollar_risk", "skip", "reason")} or None,
            },
        }) else 0
    return n
