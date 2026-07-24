"""
Transactional + digest email over SMTP (SendGrid, Postmark, SES, Gmail — anything
with SMTP). No-ops safely if SMTP isn't configured, so it never breaks a request.
"""
from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(cfg, to_addr: str, subject: str, html: str) -> bool:
    if not (cfg.smtp_host and cfg.smtp_user):
        return False
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
        return True
    except Exception:
        return False


def weekly_digest_html(scan_date: str, rows: list, sectors: list) -> str:
    top = rows[:15]
    trs = "".join(
        f"<tr><td>{r['rank']}</td><td><b>{r['ticker']}</b></td><td>{(r.get('sector') or '')[:18]}</td>"
        f"<td style='text-align:right'>{r.get('hot_score', 0):.0f}</td></tr>"
        for r in top)
    secs = ", ".join(f"{s['sector']}" for s in sectors[:4])
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:auto">
      <h2 style="color:#1f3864">🔥 Hot Stocks of the Week</h2>
      <p style="color:#555">Scan {scan_date}. Most attractive sectors: <b>{secs}</b>.</p>
      <table style="width:100%;border-collapse:collapse;font-size:14px">
        <tr style="color:#888;text-align:left"><th>#</th><th>Ticker</th><th>Sector</th><th style="text-align:right">Score</th></tr>
        {trs}
      </table>
      <p style="color:#999;font-size:12px;margin-top:16px">Educational only, not investment advice. The score is a
      heuristic, not a proven signal — verify before acting. Manage your subscription or unsubscribe in your account.</p>
    </div>"""
