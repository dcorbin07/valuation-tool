"""
Transactional + digest email over SMTP (SendGrid, Postmark, SES, Gmail — anything
with SMTP). No-ops safely if SMTP isn't configured, so it never breaks a request.
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# send_status() outcomes. The distinction matters for security, not just for logging:
# "not_configured" means we are almost certainly on a dev box, while "failed" is the
# normal way a PRODUCTION mail server misbehaves. Collapsing the two into one False
# is what let /forgot hand reset links to anonymous callers whenever SMTP hiccuped.
SENT = "sent"
NOT_CONFIGURED = "not_configured"
FAILED = "failed"


def send_status(cfg, to_addr: str, subject: str, html: str) -> str:
    """Send one email and report WHICH of the three outcomes happened."""
    if not (cfg.smtp_host and cfg.smtp_user):
        return NOT_CONFIGURED
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.email_from
    msg["To"] = to_addr
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as s:
            s.starttls()
            s.login(cfg.smtp_user, cfg.smtp_password)
            s.sendmail(cfg.email_from, [to_addr], msg.as_string())
        return SENT
    except Exception:
        return FAILED


def send_email(cfg, to_addr: str, subject: str, html: str) -> bool:
    """Bool wrapper for the digest/alert callers that only care 'did it go out'."""
    return send_status(cfg, to_addr, subject, html) == SENT


def _fmt_weights(prev: dict, cur: dict) -> str:
    """One line per factor: 'value 0.28 → 0.30' with changed ones bolded."""
    keys = list(cur or prev or {})
    parts = []
    for k in keys:
        pv, cv = (prev or {}).get(k), (cur or {}).get(k)
        label = k.replace("_", " ")
        if pv is not None and cv is not None and abs(float(pv) - float(cv)) >= 0.005:
            parts.append(f"<b>{label} {float(pv):.2f} → {float(cv):.2f}</b>")
        else:
            parts.append(f"{label} {float(cv if cv is not None else pv):.2f}")
    return " · ".join(parts)


def learning_digest_html(report: dict) -> str:
    """Owner-only monthly note: did the out-of-sample learner change anything?"""
    import datetime as _dt
    status = report.get("status", "")
    buckets = report.get("buckets", {})
    any_change = any(b.get("adopted") for b in buckets.values())
    if status != "ok":
        headline = f"No changes — not enough history yet ({report.get('dates', 0)} scan dates). Current weights held."
    elif any_change:
        changed = ", ".join(b for b, v in buckets.items() if v.get("adopted"))
        headline = f"Updated the <b>{changed}</b> bucket weight(s) — the change beat the current weights out-of-sample."
    else:
        headline = "No changes this month — the current weights still won out-of-sample. Nothing was overfit into the model."

    blocks = ""
    for name, b in buckets.items():
        adopted = b.get("adopted")
        tag = ("✅ UPDATED" if adopted else "— held (no change)")
        ic = b.get("out_sample_ic")
        ic_line = f"<div style='color:#888;font-size:12px'>Out-of-sample IC: {ic:.3f}</div>" if isinstance(ic, (int, float)) else ""
        weights = _fmt_weights(b.get("previous"), b.get("weights")) if adopted else _fmt_weights(None, b.get("weights"))
        blocks += (
            f"<div style='margin:12px 0;padding:12px;border:1px solid #eee;border-radius:8px'>"
            f"<div><b style='text-transform:capitalize'>{name}</b> &nbsp; <span style='color:#666'>{tag}</span></div>"
            f"<div style='font-size:13px;color:#333;margin:6px 0'>{weights}</div>"
            f"{ic_line}"
            f"<div style='color:#999;font-size:12px;margin-top:4px'>{b.get('note', '')}</div></div>")

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1f3864">🧠 Valquo — monthly self-learning update</h2>
      <p style="color:#333">{headline}</p>
      <p style="color:#888;font-size:12px">Learned from {report.get('panel_rows', 0)} data points across
      {report.get('dates', 0)} scan dates. A change is adopted only if it beats the current weights on data it
      wasn't fit to — otherwise the current weights are kept.</p>
      {blocks}
      <p style="color:#999;font-size:12px;margin-top:16px">Private owner note. Educational tool, not investment advice.</p>
    </div>"""


def weekly_digest_html(scan_date: str, rows: list, sectors: list) -> str:
    top = rows[:15]
    trs = "".join(
        f"<tr><td>{r['rank']}</td><td><b>{r['ticker']}</b></td><td>{(r.get('sector') or '')[:18]}</td>"
        f"<td style='text-align:right'>{r.get('hot_score', 0):.0f}</td></tr>"
        for r in top)
    secs = ", ".join(f"{s['sector']}" for s in sectors[:4])
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1f3864">🔥 Valquo — Hot Stocks of the Day</h2>
      <p style="color:#555">Scan {scan_date}. Most attractive sectors: <b>{secs}</b>.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr style="color:#888;text-align:left"><th>#</th><th>Ticker</th><th>Sector</th><th style="text-align:right">Score</th></tr>
        {trs}
      </table>
      <p style="color:#999;font-size:12px;margin-top:16px">Educational only, not investment advice. The score is a
      heuristic, not a proven signal — verify before acting. Manage your subscription or unsubscribe in your account.</p>
    </div>"""
