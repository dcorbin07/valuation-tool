#!/usr/bin/env python3
"""
Run the trend-following bot (Bot #2).

Autonomous entry point. Runs a daily rebalance during market hours until you
stop it with Ctrl-C.

MODES (BOT_MODE env var, default preview_only):
    preview_only  - validate orders, place nothing (SAFE)
    paper         - place orders against Tradier sandbox (no real money)
    live          - REAL MONEY (requires BOT_ALLOW_LIVE + production broker)

Examples:
    python scripts/run_trend_bot.py                  # scheduler, preview mode
    python scripts/run_trend_bot.py --once           # one rebalance, then exit
    $env:BOT_MODE="paper"; python scripts/run_trend_bot.py --once   # paper, one run

Uses its OWN paper account — set TREND_TRADIER_TOKEN / TREND_TRADIER_ACCOUNT_ID
in .env if you want it separate from the options bot, else falls back to the
shared TRADIER_TOKEN / TRADIER_ACCOUNT_ID.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core import DiscordNotifier, TradierClient, TradierConfig, mode_from_env
from trend import TrendConfig, TrendOrchestrator


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    # Prefer trend-specific creds, fall back to shared ones.
    # Hard separation: the trend bot ONLY uses its own credentials. No shared
    # fallback — each bot trades its own account so their track records stay
    # completely independent.
    token = os.environ.get("TREND_TRADIER_TOKEN")
    account_id = os.environ.get("TREND_TRADIER_ACCOUNT_ID")
    sandbox = os.environ.get("TREND_TRADIER_SANDBOX", "true").lower() != "false"
    if not token or not account_id:
        print("Trend bot not configured (no TREND_TRADIER_TOKEN / "
              "TREND_TRADIER_ACCOUNT_ID in .env) — skipping. Set its own "
              "credentials to enable it.")
        sys.exit(0)
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the trend-following bot.")
    parser.add_argument("--once", action="store_true",
                        help="Run a single rebalance and exit, instead of the scheduler.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(PROJECT_ROOT / "trend_bot.log")],
    )
    logger = logging.getLogger("run_trend_bot")

    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)
    config = TrendConfig(mode=mode_from_env())

    # Ensure data dirs exist on a fresh box.
    for sub in ("cache", "state", "journal"):
        (PROJECT_ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)

    logger.info("Starting trend bot: mode=%s, broker=%s",
                config.mode.value, "sandbox" if sandbox else "PRODUCTION")

    with TradierClient(tradier_config) as tradier:
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
        orchestrator = TrendOrchestrator(config, tradier, PROJECT_ROOT, notifier=notifier)

        # Quick startup credential check
        try:
            equity = tradier.get_account_value()
            logger.info("Startup: Tradier OK, account equity $%.2f", equity)
        except Exception as e:
            sys.exit(f"Startup failed — could not reach Tradier: {e}")

        notifier.send(f"Trend bot started: mode={config.mode.value}, "
                      f"broker={'sandbox' if sandbox else 'PRODUCTION'}")

        if args.once:
            result = orchestrator.run_rebalance_guarded()
            print(f"\n[{result.job_name}] {result.summary}")
            if result.error:
                print(f"ERROR: {result.error}")
            return 0 if result.success else 1
        else:
            orchestrator.start()
    return 0


if __name__ == "__main__":
    sys.exit(main())
