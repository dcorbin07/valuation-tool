"""Notification + advisory layer: Discord webhook + LLM advisory (flag-only)."""
from .advisor import (
    Advisory,
    AdvisorySignal,
    LLMAdvisor,
    build_advisory_fn,
)
from .discord import DiscordNotifier

__all__ = [
    "Advisory",
    "AdvisorySignal",
    "LLMAdvisor",
    "build_advisory_fn",
    "DiscordNotifier",
]
