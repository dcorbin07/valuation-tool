"""
Discord webhook notifier.

Free, fast, no account-level API — just a webhook URL you create in any Discord
channel (Server Settings → Integrations → Webhooks → New Webhook → Copy URL).
Set it in your .env as DISCORD_WEBHOOK_URL.

This replaces the Twilio SMS idea from the original ChatGPT bot: free instead
of ~$1/mo + per-message, richer formatting, searchable history, and no phone
number juggling.

Design:
  - Notifier is a thin wrapper with one job: post messages to Discord.
  - If no webhook URL is configured, it degrades to logging only (so the bot
    runs fine without Discord set up — notifications just go to the log).
  - It never raises on a failed send; a notification failure must never crash
    a trading job. Failures are logged.
  - notify_job_result() formats a JobResult (from the orchestrator) into a
    readable Discord message with color coding.
"""
from __future__ import annotations

import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)


# Discord embed colors (decimal RGB)
_COLOR_GREEN = 3066993    # success / profit
_COLOR_RED = 15158332     # error / loss
_COLOR_BLUE = 3447003     # informational
_COLOR_YELLOW = 16776960  # warning / advisory


class DiscordNotifier:
    """
    Posts messages to a Discord channel via webhook.

    Usage:
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
        notifier.send("Bot started in PAPER mode")
        notifier.notify_job_result(job_result)
    """

    def __init__(self, webhook_url: Optional[str] = None, timeout_secs: float = 10.0):
        self.webhook_url = webhook_url
        self.timeout_secs = timeout_secs
        self.enabled = bool(webhook_url)
        if not self.enabled:
            logger.info(
                "DiscordNotifier: no webhook URL configured — notifications "
                "will be logged only."
            )

    def send(self, content: str) -> bool:
        """Send a plain-text message. Returns True if sent, False otherwise."""
        if not self.enabled:
            logger.info("[notify] %s", content)
            return False
        try:
            resp = requests.post(
                self.webhook_url,
                json={"content": content[:2000]},  # Discord 2000-char limit
                timeout=self.timeout_secs,
            )
            if resp.status_code in (200, 204):
                return True
            logger.warning("Discord send returned %d: %s", resp.status_code, resp.text[:200])
            return False
        except requests.RequestException as e:
            logger.warning("Discord send failed: %s", e)
            return False

    def send_embed(
        self, title: str, description: str, color: int = _COLOR_BLUE,
        fields: Optional[list[dict]] = None,
    ) -> bool:
        """Send a rich embed message."""
        if not self.enabled:
            logger.info("[notify] %s — %s", title, description)
            return False
        embed: dict = {
            "title": title[:256],
            "description": description[:4096],
            "color": color,
        }
        if fields:
            embed["fields"] = fields[:25]
        try:
            resp = requests.post(
                self.webhook_url,
                json={"embeds": [embed]},
                timeout=self.timeout_secs,
            )
            if resp.status_code in (200, 204):
                return True
            logger.warning("Discord embed returned %d: %s", resp.status_code, resp.text[:200])
            return False
        except requests.RequestException as e:
            logger.warning("Discord embed failed: %s", e)
            return False

    def notify_job_result(self, result) -> bool:
        """
        Format and send a JobResult (from orchestrator.jobs). Imported lazily
        so this module doesn't hard-depend on the orchestrator package.
        """
        color = _COLOR_GREEN if result.success else _COLOR_RED
        if result.error:
            color = _COLOR_RED

        title = f"{result.job_name} ({result.mode})"
        description = result.summary

        fields = []
        details = result.details or {}

        # Open-job details
        if "placed" in details:
            placed = details.get("placed", [])
            failed = details.get("failed", [])
            if placed:
                lines = [
                    f"• {p['symbol']} ×{p.get('contracts','?')} @ ${p.get('credit','?')}"
                    for p in placed[:10]
                ]
                fields.append({"name": "Placed/Previewed", "value": "\n".join(lines)[:1024], "inline": False})
            if failed:
                fields.append({"name": "Failed", "value": str(len(failed)), "inline": True})
            if "account_value" in details:
                fields.append({"name": "Account", "value": f"${details['account_value']:,.0f}", "inline": True})

        # Manage-job details
        if "open_spreads" in details:
            fields.append({"name": "Open spreads", "value": str(details["open_spreads"]), "inline": True})
            if "total_pnl" in details:
                pnl = details["total_pnl"]
                fields.append({"name": "Unrealized P&L", "value": f"${pnl:,.0f}", "inline": True})
            closed = details.get("closed", [])
            if closed:
                lines = [
                    f"• {c['symbol']} {c.get('decision','')} (P&L ${c.get('pnl',0):,.0f})"
                    for c in closed[:10]
                ]
                fields.append({"name": "Closed", "value": "\n".join(lines)[:1024], "inline": False})

        if details.get("kill_switch"):
            color = _COLOR_RED
            title = "🛑 " + title

        return self.send_embed(title, description, color=color, fields=fields or None)
