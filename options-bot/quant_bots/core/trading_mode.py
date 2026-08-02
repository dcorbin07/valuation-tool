"""
Trading-mode switch and safety guardrails — shared by every bot.

This is the single most important safety boundary in any of the bots, so it
lives in core and is identical across strategies. Three modes:

  - PREVIEW_ONLY (default): every order validated against the broker but never
    placed. The only mode safe to run unattended while you still trust nothing.
  - PAPER: orders placed, but only against the broker's sandbox. No real money.
  - LIVE: real money. Requires THREE independent settings to agree
    (mode=live + BOT_ALLOW_LIVE=YES_I_UNDERSTAND + broker in production).

Each strategy bot wraps this with its own scheduling config (rebalance times,
etc.), but the mode logic and guardrails are shared and never duplicated.
"""
from __future__ import annotations

import logging
import os
from enum import Enum

logger = logging.getLogger(__name__)

_LIVE_CONFIRMATION_PHRASE = "YES_I_UNDERSTAND"


class TradingMode(Enum):
    PREVIEW_ONLY = "preview_only"
    SIM = "sim"          # pure simulation: fills assumed, tracked in SimPortfolio
    PAPER = "paper"
    LIVE = "live"


class LiveTradingNotAuthorizedError(Exception):
    """Raised when LIVE mode is requested without the confirmation env var."""


class BrokerEnvironmentMismatchError(Exception):
    """Raised when the trading mode and broker sandbox flag disagree."""


def mode_from_env(env_var: str = "BOT_MODE") -> TradingMode:
    """Read the trading mode from the environment, defaulting to the safest."""
    val = os.environ.get(env_var, "preview_only").lower()
    try:
        return TradingMode(val)
    except ValueError:
        logger.warning("Unknown %s '%s'; defaulting to preview_only.", env_var, val)
        return TradingMode.PREVIEW_ONLY


def places_real_orders(mode: TradingMode) -> bool:
    """True if this mode actually submits orders (PAPER or LIVE)."""
    return mode in (TradingMode.PAPER, TradingMode.LIVE)


def validate_mode_against_broker(mode: TradingMode, broker_is_sandbox: bool) -> None:
    """
    Enforce the hard guardrails. Call once at startup, before any job runs.
    Raises if the mode/broker combination is unsafe.
    """
    if mode == TradingMode.LIVE:
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
        logger.warning("⚠ LIVE TRADING MODE ACTIVE — orders will use REAL MONEY.")
    elif mode == TradingMode.PAPER:
        if not broker_is_sandbox:
            raise BrokerEnvironmentMismatchError(
                "PAPER mode requires the broker in SANDBOX (sandbox=True), but "
                "the broker is in production. Set TRADIER_SANDBOX=true (default) "
                "— or switch mode to LIVE if you really mean it."
            )
        logger.info("PAPER mode — orders placed against broker sandbox.")
    elif mode == TradingMode.SIM:
        logger.info("SIM mode — pure simulation; fills assumed at quoted prices, "
                    "tracked in the bot's own SimPortfolio. No broker orders.")
    else:
        logger.info("PREVIEW_ONLY mode — orders validated but never placed.")


def is_sim(mode: TradingMode) -> bool:
    """True if running in pure-simulation mode (tracked in SimPortfolio)."""
    return mode == TradingMode.SIM
