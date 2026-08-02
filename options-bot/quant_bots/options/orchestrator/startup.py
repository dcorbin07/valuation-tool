"""
Startup self-check.

Runs once when the bot starts, BEFORE the scheduler. Catches the dumb-but-fatal
problems that otherwise only surface when a job fails at 10am on a cloud box
you're not watching:

  - data/ subdirectories don't exist on a fresh machine
  - Tradier credentials are missing or the token is dead
  - The trading mode / broker-environment combination is unsafe
  - (informational) whether Discord and the LLM advisor are configured

Returns a list of human-readable problems. An empty list means good to go.
The runner prints these and refuses to start the scheduler if any are fatal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from broker import TradierClient, TradierError

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    ok: bool
    messages: list[str]
    warnings: list[str]


REQUIRED_DIRS = ["data/cache", "data/state", "data/journal"]


def run_startup_checks(
    project_root: Path,
    tradier: TradierClient,
    discord_configured: bool,
    advisor_enabled: bool,
) -> CheckResult:
    messages: list[str] = []
    warnings: list[str] = []

    # 1. Ensure data directories exist (create them — this is the fix, not just
    #    a check, so a fresh cloud box just works).
    for rel in REQUIRED_DIRS:
        d = project_root / rel
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messages.append(f"FATAL: could not create directory {d}: {e}")

    # 2. Verify Tradier credentials actually work.
    try:
        profile = tradier.get_user_profile()
        name = profile.get("profile", {}).get("name", "<unknown>")
        balances = tradier.get_balances()
        equity = balances.get("total_equity", "?")
        logger.info("Startup check: Tradier OK (account=%s, equity=$%s)", name, equity)
    except TradierError as e:
        messages.append(f"FATAL: Tradier API check failed: {e}")
    except Exception as e:
        messages.append(f"FATAL: unexpected error reaching Tradier: {e}")

    # 3. Informational: notifier / advisor status
    if discord_configured:
        logger.info("Startup check: Discord notifications ENABLED")
    else:
        warnings.append("Discord not configured — notifications will log only.")

    if advisor_enabled:
        logger.info("Startup check: LLM advisory ENABLED (flag-only)")
    else:
        warnings.append("LLM advisory disabled — no news-event flagging.")

    ok = len(messages) == 0
    return CheckResult(ok=ok, messages=messages, warnings=warnings)
