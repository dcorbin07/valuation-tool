"""
Orchestrator configuration, including the trading-mode switch.

THE MOST IMPORTANT SAFETY BOUNDARY IN THE WHOLE BOT LIVES HERE.

TradingMode has three values:
  - PREVIEW_ONLY: every order is validated against Tradier but never placed.
    This is the default and the only mode that's safe to run unattended while
    you still trust nothing.
  - PAPER: orders are actually placed, but only against Tradier's sandbox
    (paper) environment. Requires sandbox=True on the broker. No real money.
  - LIVE: orders are placed against the real account with real money.

Hard guardrails enforced in code (not just convention):
  1. LIVE mode requires an explicit, separate environment variable
     (BOT_ALLOW_LIVE=YES_I_UNDERSTAND) in addition to setting mode=LIVE.
     Two independent switches must agree. This prevents a single typo or
     stray config from trading real money.
  2. LIVE mode requires the broker to be in production (sandbox=False).
     PAPER mode requires the broker to be in sandbox (sandbox=True).
     A mismatch raises immediately rather than doing something surprising.
  3. PREVIEW_ONLY never places orders regardless of any other setting.

You should run PREVIEW_ONLY for weeks, then PAPER for the agreed 2-3 months,
and only consider LIVE after the strategy has proven itself on paper AND your
account has grown past the threshold where the strategy is viable (~$25k).
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TradingMode(Enum):
    PREVIEW_ONLY = "preview_only"
    SIM = "sim"          # pure simulation; tracked in OptionsSimPortfolio
    PAPER = "paper"
    LIVE = "live"


# The magic phrase that must be set in BOT_ALLOW_LIVE to permit live trading.
_LIVE_CONFIRMATION_PHRASE = "YES_I_UNDERSTAND"


class LiveTradingNotAuthorizedError(Exception):
    """Raised when LIVE mode is requested without the confirmation env var."""


class BrokerEnvironmentMismatchError(Exception):
    """Raised when the trading mode and broker sandbox flag disagree."""


@dataclass
class OrchestratorConfig:
    """Top-level orchestrator settings."""

    mode: TradingMode = TradingMode.PREVIEW_ONLY

    # Schedule (times are Eastern). Prep builds the universe + candidates
    # pre-market; the open job reads them after the open settles; the manage
    # job runs periodically through the session.
    prep_job_hour: int = 9            # 09:00 ET — pre-market, before open job
    prep_job_minute: int = 0
    open_job_hour: int = 10           # 10:00 ET — let the open settle
    open_job_minute: int = 0
    manage_job_interval_minutes: int = 30  # check positions every 30 min

    # Whether to run each job. Prep must run (or have run) before open, since
    # open reads the candidates file prep produces.
    enable_prep_job: bool = True
    enable_open_job: bool = True
    enable_manage_job: bool = True

    # How many top candidates to consider each morning (passed to strategy)
    max_candidates_to_consider: int = 30

    # Safety: even in PAPER/LIVE, never place more than this many opening
    # orders in a single morning run. Backstop against a screener bug.
    max_opens_per_run: int = 10

    # Fill confirmation: after placing an opening order, poll its status to
    # confirm it filled (vs. silently assuming it did). Set wait to 0 to skip
    # polling entirely (fire-and-forget; manage job reconciles later).
    confirm_fills: bool = True
    fill_wait_secs: float = 30.0
    fill_poll_interval_secs: float = 3.0
    # Cancel an opening order that's still unfilled after the wait window.
    # Keeps the book clean — no stale working orders lingering past our window.
    cancel_unfilled_opens: bool = True

    def validate_against_broker(self, broker_is_sandbox: bool) -> None:
        """
        Enforce the hard guardrails. Call this once at orchestrator startup,
        BEFORE any jobs run. Raises if the configuration is unsafe.
        """
        if self.mode == TradingMode.LIVE:
            confirmation = os.environ.get("BOT_ALLOW_LIVE", "")
            if confirmation != _LIVE_CONFIRMATION_PHRASE:
                raise LiveTradingNotAuthorizedError(
                    "LIVE mode requested but BOT_ALLOW_LIVE is not set to "
                    f"'{_LIVE_CONFIRMATION_PHRASE}'. Live trading is blocked. "
                    "This is a deliberate two-key safety mechanism."
                )
            if broker_is_sandbox:
                raise BrokerEnvironmentMismatchError(
                    "LIVE mode requires the broker in PRODUCTION (sandbox=False), "
                    "but the broker is in sandbox. Set TRADIER_SANDBOX=false and "
                    "use production credentials — or switch mode to PAPER."
                )
            logger.warning(
                "⚠ LIVE TRADING MODE ACTIVE — orders will use REAL MONEY."
            )

        elif self.mode == TradingMode.PAPER:
            if not broker_is_sandbox:
                raise BrokerEnvironmentMismatchError(
                    "PAPER mode requires the broker in SANDBOX (sandbox=True), "
                    "but the broker is in production. Set TRADIER_SANDBOX=true "
                    "(default) — or switch mode to LIVE if you really mean it."
                )
            logger.info("PAPER mode — orders placed against Tradier sandbox.")

        elif self.mode == TradingMode.SIM:
            logger.info("SIM mode — pure simulation; spreads tracked in the "
                        "options bot's own SimPortfolio. No broker orders.")

        else:  # PREVIEW_ONLY
            logger.info("PREVIEW_ONLY mode — orders validated but never placed.")

    @property
    def is_sim(self) -> bool:
        """True if running in pure-simulation mode."""
        return self.mode == TradingMode.SIM

    @property
    def places_real_orders(self) -> bool:
        """True if this mode actually submits orders (PAPER or LIVE)."""
        return self.mode in (TradingMode.PAPER, TradingMode.LIVE)

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        """
        Build config from environment variables, defaulting to the safest mode.

        BOT_MODE = preview_only | paper | live   (default: preview_only)
        """
        mode_str = os.environ.get("BOT_MODE", "preview_only").lower()
        try:
            mode = TradingMode(mode_str)
        except ValueError:
            logger.warning(
                "Unknown BOT_MODE '%s'; defaulting to preview_only.", mode_str
            )
            mode = TradingMode.PREVIEW_ONLY
        return cls(mode=mode)
