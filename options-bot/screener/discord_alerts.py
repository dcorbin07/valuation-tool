"""
discord_alerts.py — post to the three Discord channels via webhooks.

Channel webhook URLs come from .env:
  DISCORD_WEBHOOK_DAILY, DISCORD_WEBHOOK_INSIDER, DISCORD_WEBHOOK_IMPROVE
In --dry-run mode the pipeline prints instead of posting.
"""

import os
import time
import requests

_WEBHOOKS = {
    "daily_list": "DISCORD_WEBHOOK_DAILY",
    "insider_flags": "DISCORD_WEBHOOK_INSIDER",
    "improvement_suggestions": "DISCORD_WEBHOOK_IMPROVE",
}
_COLORS = {"daily_list": 0x1F3864, "insider_flags": 0x2E7D32, "improvement_suggestions": 0x8E44AD}


def post(channel, title, body, dry_run=False):
    """Post an embed to a channel. Honors dry-run mode (print only)."""
    if dry_run:
        print(f"\n[DRY-RUN · #{channel}] {title}\n{body}\n")
        return True
    url = os.getenv(_WEBHOOKS.get(channel, ""))
    if not url:
        print(f"[warn] no webhook configured for #{channel}; skipping post")
        return False
    # Discord embed description cap is 4096 chars; chunk if needed
    chunks = [body[i:i + 3900] for i in range(0, max(len(body), 1), 3900)] or [""]
    ok = True
    for idx, chunk in enumerate(chunks):
        payload = {"embeds": [{
            "title": title if idx == 0 else f"{title} (cont.)",
            "description": chunk, "color": _COLORS.get(channel, 0x333333),
        }]}
        ok = ok and _post_with_retry(url, payload)
    return ok


def _post_with_retry(url, payload, tries=3):
    for _ in range(tries):
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 429:  # rate limited
                time.sleep(float(r.headers.get("Retry-After", 1)) + 0.5)
                continue
            r.raise_for_status()
            return True
        except Exception:
            time.sleep(1.0)
    return False
