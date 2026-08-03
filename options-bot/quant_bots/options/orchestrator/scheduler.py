"""
The scheduler — the top-level autonomous loop.

Uses APScheduler's BlockingScheduler to run two recurring jobs:
  - open_job  at config.open_job_hour:open_job_minute Eastern, weekdays
  - manage_job every config.manage_job_interval_minutes during market hours

Both jobs are guarded: they check the market is actually open (via the local
calendar AND Tradier's clock) before doing anything. On a holiday or weekend,
they no-op and log.

This module is the only place that imports APScheduler, so the rest of the bot
stays free of that dependency and remains unit-testable. The job logic in
jobs.py is fully testable without a scheduler.

Run it with:  python scripts/run_bot.py
Stop it with: Ctrl-C (graceful shutdown).
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from broker import TradierClient

from .calendar import EASTERN, describe_market_state, is_trading_day, now_eastern
from .config import OrchestratorConfig
from .jobs import JobResult, Jobs

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Wires config + broker + jobs together and runs them on a schedule.

    on_job_complete is an optional callback (JobResult -> None) that the
    notifier (V9) will hook into. Default is no-op.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        tradier: TradierClient,
        project_root: Path,
        on_job_complete: Optional[Callable[[JobResult], None]] = None,
        advisor=None,
    ):
        self.config = config
        self.tradier = tradier
        self.project_root = project_root
        self.jobs = Jobs(config, tradier, project_root, advisor=advisor)
        self.on_job_complete = on_job_complete or (lambda result: None)

        # Enforce the safety guardrails before anything can run.
        self.config.validate_against_broker(tradier.config.sandbox)

    # ─── Guarded job wrappers ──────────────────────────────────────────────────

    def _market_is_tradeable(self) -> bool:
        """Check both the local calendar and Tradier's clock."""
        now = now_eastern()
        if not is_trading_day(now.date()):
            logger.info("Skipping job: %s", describe_market_state(now))
            return False
        try:
            clock = self.tradier.get_clock()
            state = clock.get("state", "")
            if state not in ("open", "premarket"):
                logger.info("Skipping job: Tradier clock state is '%s'", state)
                return False
        except Exception as e:
            # If we can't reach the clock, fall back to the local calendar
            # judgment, which already passed is_trading_day.
            logger.warning("Could not fetch Tradier clock (%s); using local calendar.", e)
        return True

    def run_prep_job(self) -> JobResult:
        # Prep runs PRE-market (builds universe + candidates), so it only needs
        # to be a trading day — not market-open. We don't gate it on the clock.
        from datetime import datetime, timezone
        from .calendar import is_trading_day, now_eastern, describe_market_state
        if not is_trading_day(now_eastern().date()):
            logger.info("Skipping prep: %s", describe_market_state())
            return JobResult(
                "prep_job", datetime.now(timezone.utc).isoformat(),
                self.config.mode.value, True, "Skipped — not a trading day",
            )
        result = self.jobs.prep_job()
        self.on_job_complete(result)
        return result

    def run_open_job(self) -> JobResult:
        if not self._market_is_tradeable():
            from datetime import datetime, timezone
            return JobResult(
                "open_job", datetime.now(timezone.utc).isoformat(),
                self.config.mode.value, True, "Skipped — market not tradeable",
            )
        result = self.jobs.open_job()
        self.on_job_complete(result)
        return result

    def run_manage_job(self) -> JobResult:
        if not self._market_is_tradeable():
            from datetime import datetime, timezone
            return JobResult(
                "manage_job", datetime.now(timezone.utc).isoformat(),
                self.config.mode.value, True, "Skipped — market not tradeable",
            )
        result = self.jobs.manage_job()
        self.on_job_complete(result)
        return result

    # ─── Scheduling ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the blocking scheduler. Runs until Ctrl-C."""
        try:
            from apscheduler.schedulers.blocking import BlockingScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            raise SystemExit(
                "apscheduler is not installed. Run: pip install apscheduler"
            )

        scheduler = BlockingScheduler(timezone=EASTERN)

        if self.config.enable_prep_job:
            scheduler.add_job(
                self.run_prep_job,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour=self.config.prep_job_hour,
                    minute=self.config.prep_job_minute,
                    timezone=EASTERN,
                ),
                id="prep_job",
                name="Pre-market prep job (universe + screen)",
                misfire_grace_time=3600,
            )
            logger.info(
                "Scheduled prep_job at %02d:%02d ET, Mon-Fri",
                self.config.prep_job_hour, self.config.prep_job_minute,
            )

        if self.config.enable_open_job:
            scheduler.add_job(
                self.run_open_job,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour=self.config.open_job_hour,
                    minute=self.config.open_job_minute,
                    timezone=EASTERN,
                ),
                id="open_job",
                name="Morning open job",
                misfire_grace_time=3600,  # tolerate up to 1h late (e.g. box just booted)
            )
            logger.info(
                "Scheduled open_job at %02d:%02d ET, Mon-Fri",
                self.config.open_job_hour, self.config.open_job_minute,
            )

        if self.config.enable_manage_job:
            scheduler.add_job(
                self.run_manage_job,
                CronTrigger(
                    day_of_week="mon-fri",
                    hour="10-15",  # 10:00-15:59 ET — through the session
                    minute=f"*/{self.config.manage_job_interval_minutes}",
                    timezone=EASTERN,
                ),
                id="manage_job",
                name="Position management job",
                misfire_grace_time=600,
            )
            logger.info(
                "Scheduled manage_job every %d min, 10:00-16:00 ET, Mon-Fri",
                self.config.manage_job_interval_minutes,
            )

        logger.info("Orchestrator starting in %s mode. %s",
                    self.config.mode.value.upper(), describe_market_state())
        logger.info("Press Ctrl-C to stop.")
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Orchestrator shutting down gracefully.")
            scheduler.shutdown(wait=False)
