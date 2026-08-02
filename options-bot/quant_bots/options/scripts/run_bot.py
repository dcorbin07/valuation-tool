#!/usr/bin/env python3
"""
Run the trading bot.

This is the autonomous entry point. It starts the scheduler, which runs the
morning open job and periodic management jobs during market hours, until you
stop it with Ctrl-C.

MODES (set via BOT_MODE env var, default preview_only):
    preview_only  - validate orders against Tradier, never place them (SAFE)
    paper         - place orders against Tradier sandbox (no real money)
    live          - place orders with REAL MONEY (requires BOT_ALLOW_LIVE)

Examples:
    # Safest — just watch what it would do, place nothing
    python scripts/run_bot.py

    # Paper trading (requires TRADIER_SANDBOX=true)
    BOT_MODE=paper python scripts/run_bot.py        # mac/linux
    $env:BOT_MODE="paper"; python scripts/run_bot.py # windows powershell

    # Run a single job once and exit (for testing) — see --once
    python scripts/run_bot.py --once open
    python scripts/run_bot.py --once manage

LIVE trading requires BOTH:
    BOT_MODE=live
    BOT_ALLOW_LIVE=YES_I_UNDERSTAND
    TRADIER_SANDBOX=false  (with production credentials)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from broker import TradierClient, TradierConfig  # noqa: E402
from notify import DiscordNotifier, LLMAdvisor, build_advisory_fn  # noqa: E402
from orchestrator import Orchestrator, OrchestratorConfig  # noqa: E402


def _load_env() -> tuple[str, str, bool]:
    try:
        from dotenv import load_dotenv
        # Load this bot's own .env if present, then also the parent
        # quant_bots/.env (the combined file shared by all three bots).
        # Own-folder values win if both define the same key.
        parent_env = Path(__file__).resolve().parent.parent.parent / ".env"
        if parent_env.exists():
            load_dotenv(parent_env)
        load_dotenv()  # options/.env (if any) overrides parent
    except ImportError:
        pass
    token = os.environ.get("TRADIER_TOKEN")
    account_id = os.environ.get("TRADIER_ACCOUNT_ID")
    sandbox = os.environ.get("TRADIER_SANDBOX", "true").lower() != "false"
    if not token:
        sys.exit("ERROR: TRADIER_TOKEN not set.")
    if not account_id:
        sys.exit("ERROR: TRADIER_ACCOUNT_ID not set.")
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the options trading bot.")
    parser.add_argument(
        "--once", choices=["prep", "open", "manage"], default=None,
        help="Run a single job once and exit, instead of starting the scheduler.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(PROJECT_ROOT / "bot.log"),
        ],
    )
    logger = logging.getLogger("run_bot")

    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)
    orch_config = OrchestratorConfig.from_env()

    logger.info(
        "Starting bot: mode=%s, broker=%s",
        orch_config.mode.value, "sandbox" if sandbox else "PRODUCTION",
    )

    with TradierClient(tradier_config) as tradier:
        # ── Notifier (Discord) — degrades to log-only if no webhook ──────────
        notifier = DiscordNotifier(webhook_url=os.environ.get("DISCORD_WEBHOOK_URL"))

        # ── LLM advisor (flag-and-log only) — disabled if no ANTHROPIC_API_KEY
        advisor = LLMAdvisor(advise_fn=build_advisory_fn())

        def on_job_complete(result):
            # Send each job result to Discord (or log if not configured).
            notifier.notify_job_result(result)
            # Surface any advisory concerns as a separate, clearly-labeled note.
            advisories = (result.details or {}).get("advisories", {})
            concerns = {
                sym: a for sym, a in advisories.items()
                if a.get("signal") == "concern"
            }
            if concerns:
                lines = [
                    f"⚠ {sym}: {a['reasoning']} (events: {', '.join(a['events'])})"
                    for sym, a in concerns.items()
                ]
                notifier.send(
                    "ADVISORY CONCERNS (informational — these trades were NOT "
                    "blocked):\n" + "\n".join(lines)
                )

        # Orchestrator constructor validates the safety guardrails and will
        # raise immediately if the mode/broker combination is unsafe.
        orchestrator = Orchestrator(
            orch_config, tradier, PROJECT_ROOT,
            on_job_complete=on_job_complete,
            advisor=advisor,
        )

        # Startup self-check: create data dirs, verify Tradier, report config.
        from orchestrator.startup import run_startup_checks
        check = run_startup_checks(
            PROJECT_ROOT, tradier,
            discord_configured=notifier.enabled,
            advisor_enabled=advisor.enabled,
        )
        for w in check.warnings:
            logger.info("Startup note: %s", w)
        if not check.ok:
            for m in check.messages:
                logger.error(m)
            sys.exit("Startup checks failed — see errors above. Not starting.")

        notifier.send(
            f"Bot started: mode={orch_config.mode.value}, "
            f"broker={'sandbox' if sandbox else 'PRODUCTION'}"
        )

        if args.once == "prep":
            result = orchestrator.run_prep_job()
            print(f"\n[{result.job_name}] {result.summary}")
            if result.error:
                print(f"ERROR: {result.error}")
            return 0 if result.success else 1
        elif args.once == "open":
            result = orchestrator.run_open_job()
            print(f"\n[{result.job_name}] {result.summary}")
            if result.error:
                print(f"ERROR: {result.error}")
            return 0 if result.success else 1
        elif args.once == "manage":
            result = orchestrator.run_manage_job()
            print(f"\n[{result.job_name}] {result.summary}")
            if result.error:
                print(f"ERROR: {result.error}")
            return 0 if result.success else 1
        else:
            # Start the blocking scheduler (runs until Ctrl-C)
            orchestrator.start()

    return 0


if __name__ == "__main__":
    sys.exit(main())
