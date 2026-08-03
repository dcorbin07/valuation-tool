#!/usr/bin/env python3
"""
Run the cross-sectional momentum bot (Bot #3).

Autonomous entry point. Each day during market hours it builds a stock universe,
ranks names by 12-1 momentum, holds the top winners long and bottom losers
short, and rebalances toward that target. Runs until Ctrl-C.

MODES (BOT_MODE env var, default preview_only):
    preview_only  - validate orders, place nothing (SAFE)
    paper         - place against Tradier sandbox (no real money)
    live          - REAL MONEY (requires BOT_ALLOW_LIVE + production broker)

Examples:
    python scripts/run_momentum_bot.py                 # scheduler, preview
    python scripts/run_momentum_bot.py --once          # one rebalance, exit
    $env:BOT_MODE="paper"; python scripts/run_momentum_bot.py --once

Uses its OWN paper account if MOMENTUM_TRADIER_TOKEN / MOMENTUM_TRADIER_ACCOUNT_ID
are set, else falls back to the shared TRADIER_* vars. A separate account per bot
keeps the three strategies' track records cleanly independent.
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
from momentum import MomentumBotConfig, MomentumOrchestrator


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    # Hard separation: the momentum bot ONLY uses its own credentials. No
    # shared fallback — each bot trades its own account so their track records
    # stay completely independent.
    token = os.environ.get("MOMENTUM_TRADIER_TOKEN")
    account_id = os.environ.get("MOMENTUM_TRADIER_ACCOUNT_ID")
    sandbox = os.environ.get("MOMENTUM_TRADIER_SANDBOX", "true").lower() != "false"
    if not token or not account_id:
        print("Momentum bot not configured (no MOMENTUM_TRADIER_TOKEN / "
              "MOMENTUM_TRADIER_ACCOUNT_ID in .env) — skipping. Set its own "
              "credentials to enable it.")
        sys.exit(0)
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the cross-sectional momentum bot.")
    parser.add_argument("--once", action="store_true",
                        help="Run a single rebalance and exit.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(PROJECT_ROOT / "momentum_bot.log")],
    )
    logger = logging.getLogger("run_momentum_bot")

    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)
    config = MomentumBotConfig(mode=mode_from_env())

    for sub in ("cache", "state", "journal"):
        (PROJECT_ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)

    logger.info("Starting momentum bot: mode=%s, broker=%s",
                config.mode.value, "sandbox" if sandbox else "PRODUCTION")

    with TradierClient(tradier_config) as tradier:
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
        orchestrator = MomentumOrchestrator(config, tradier, PROJECT_ROOT, notifier=notifier)

        try:
            equity = tradier.get_account_value()
            logger.info("Startup: Tradier OK, account equity $%.2f", equity)
        except Exception as e:
            sys.exit(f"Startup failed — could not reach Tradier: {e}")

        notifier.send(f"Momentum bot started: mode={config.mode.value}, "
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
