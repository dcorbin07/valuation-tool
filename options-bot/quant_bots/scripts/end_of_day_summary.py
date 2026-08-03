#!/usr/bin/env python3
"""
Post the end-of-day summary to Discord (or log it if Discord isn't configured).

Run this once after market close — manually, or as a scheduled job on the same
box as the bots (e.g. a cron/Task Scheduler entry at 4:30pm ET). It reads each
bot's recorded equity curve and posts a single digest.

Usage:
    python scripts/end_of_day_summary.py
    python scripts/end_of_day_summary.py --bots trend momentum
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import DiscordNotifier, post_end_of_day


def main() -> int:
    p = argparse.ArgumentParser(description="Post end-of-day summary to Discord.")
    p.add_argument("--bots", nargs="+", default=["options", "trend", "momentum", "reversion"])
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
    mode = os.environ.get("BOT_MODE", "")
    sent = post_end_of_day(notifier, PROJECT_ROOT, bots=args.bots, mode=mode)
    print("Summary sent to Discord." if sent else "Summary logged (Discord not configured).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
