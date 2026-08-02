#!/usr/bin/env python3
"""
Run the mean-reversion bot (Bot #4).

Uses its OWN paper account if REVERSION_TRADIER_TOKEN / REVERSION_TRADIER_ACCOUNT_ID
are set; otherwise falls back to the shared TRADIER_TOKEN (fine for SIM, which
only needs quotes). Mode comes from BOT_MODE (preview_only/sim/paper/live).

    BOT_MODE=sim python scripts/run_reversion_bot.py --once
    $env:BOT_MODE="sim"; python scripts/run_reversion_bot.py   # windows
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
from reversion import ReversionBotConfig, ReversionOrchestrator


def _load_env() -> tuple[str, str, bool]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    # Prefer the bot's own creds; fall back to the shared token (SIM-safe).
    token = os.environ.get("REVERSION_TRADIER_TOKEN") or os.environ.get("TRADIER_TOKEN")
    account_id = (os.environ.get("REVERSION_TRADIER_ACCOUNT_ID")
                  or os.environ.get("TRADIER_ACCOUNT_ID"))
    sandbox_raw = (os.environ.get("REVERSION_TRADIER_SANDBOX")
                   or os.environ.get("TRADIER_SANDBOX", "true"))
    sandbox = sandbox_raw.lower() != "false"
    if not token or not account_id:
        print("Reversion bot not configured (no REVERSION_TRADIER_TOKEN/ACCOUNT_ID "
              "or shared TRADIER_TOKEN/ACCOUNT_ID in .env) — skipping.")
        sys.exit(0)
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the mean-reversion bot.")
    parser.add_argument("--once", action="store_true",
                        help="Run a single rebalance and exit.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(PROJECT_ROOT / "reversion_bot.log")],
    )
    logger = logging.getLogger("run_reversion_bot")

    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)
    config = ReversionBotConfig(mode=mode_from_env())

    for sub in ("cache", "state", "journal"):
        (PROJECT_ROOT / "data" / sub).mkdir(parents=True, exist_ok=True)

    logger.info("Starting reversion bot: mode=%s, broker=%s",
                config.mode.value, "sandbox" if sandbox else "PRODUCTION")

    with TradierClient(tradier_config) as tradier:
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))
        orchestrator = ReversionOrchestrator(config, tradier, PROJECT_ROOT, notifier=notifier)

        try:
            equity = tradier.get_account_value()
            logger.info("Startup: Tradier OK, account equity $%.2f", equity)
        except Exception as e:
            sys.exit(f"Startup failed — could not reach Tradier: {e}")

        notifier.send(f"Reversion bot started: mode={config.mode.value}, "
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
