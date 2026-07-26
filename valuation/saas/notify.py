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


def screaming_buys(rows, min_score) -> list:
    out = []
    for r in rows or []:
        s = r.get("score")
        labels = r.get("labels") or []
        if s is not None and s >= min_score and any(any(b in l for b in _BULL) for l in labels):
            out.append(r)
    out.sort(key=lambda r: r.get("score", 0), reverse=True)
    return out


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


def alert_discord_text(run_time, rows) -> str:
    lines = [f"🚨 **Valquo — Screaming buys** — {run_time}"]
    for r in rows[:10]:
        labs = ", ".join((r.get("labels") or [])[:3])
        idea = _idea(r)
        lines.append(f"• **{r['ticker']}**  score {r.get('score', 0):.0f} — {labs}" + (f"  · {idea}" if idea else ""))
    lines.append("_Educational only, not investment advice._")
    return "\n".join(lines)


def alert_email_html(run_time, rows, unsub_url) -> str:
    trs = "".join(
        f"<tr><td><b>{r['ticker']}</b></td><td style='text-align:right'>{r.get('score', 0):.0f}</td>"
        f"<td>{', '.join((r.get('labels') or [])[:3])}</td><td>{_idea(r)}</td></tr>" for r in rows[:10])
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1f3864">🚨 Screaming buys</h2>
      <p style="color:#555">Intraday scan {run_time}. High-conviction bullish setups.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr style="color:#888;text-align:left"><th>Ticker</th><th style="text-align:right">Score</th>
          <th>Signals</th><th>Contract idea</th></tr>
        {trs}
      </table>
      <p style="color:#999;font-size:12px;margin-top:16px">Educational only, not investment advice — technical/options
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
    picks = [r for r in screaming_buys(rows, cfg.alert_min_score) if not store.alerted_today(r["ticker"])]
    if not picks:
        return {"new": 0, "emails": 0, "tickers": []}
    send_discord(cfg, alert_discord_text(run_time, picks))
    sent = 0
    for u in users.alert_subscribers():
        unsub = f"{cfg.public_base_url}/alerts/unsubscribe/{unsub_token(cfg, u['id'])}"
        if send_email(cfg, u["email"], "🚨 Screaming buys", alert_email_html(run_time, picks, unsub)):
            sent += 1
    for r in picks:
        store.mark_alerted(r["ticker"], run_time)
    return {"new": len(picks), "emails": sent, "tickers": [r["ticker"] for r in picks]}
