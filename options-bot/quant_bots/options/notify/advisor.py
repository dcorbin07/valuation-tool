"""
LLM advisory layer (Phase 1: flag-and-log, NO veto authority).

This is the cautious first version of the AI review we discussed. For each
proposed opening order, it asks Claude to search recent news for the underlying
and assess whether there's a specific binary-event risk the screener can't see
(pending FDA decision, M&A, trading halt, fraud/SEC action, unannounced
earnings, etc.).

CRITICAL DESIGN CONSTRAINTS (these are the whole point):
  - The advisory has NO authority to block, resize, or change any order.
    It returns an advisory record that gets logged and (optionally) sent to
    Discord. The bot trades exactly as it would without this layer.
  - The advisory output is purely informational. You read the flags, learn
    what the model catches and what it cries wolf about, and decide LATER
    (after calibration) whether to promote it to veto authority.
  - A failure in the advisory layer NEVER affects trading. If the API call
    fails, times out, or returns garbage, the order proceeds and we log that
    the advisory was unavailable.

This module deliberately does not call the Anthropic API directly with a
hard-coded client — it takes an `advise_fn` callable so you can wire in
whatever LLM access you have (Anthropic SDK, a local proxy, etc.) and so the
whole thing is unit-testable with a stub. A reference implementation using the
Anthropic SDK is in build_advisory_fn() but it's optional.

When you eventually promote this to Phase 2 (actual veto on specific event
types), that's a deliberate, separate change — not something that happens by
accident.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class AdvisorySignal(Enum):
    NO_CONCERN = "no_concern"
    CONCERN = "concern"          # specific event flagged
    UNAVAILABLE = "unavailable"  # advisory couldn't run (API error etc.)


@dataclass
class Advisory:
    """An advisory record for a single proposed order. Informational only."""

    symbol: str
    signal: AdvisorySignal
    reasoning: str
    flagged_events: list[str] = field(default_factory=list)

    @property
    def is_concern(self) -> bool:
        return self.signal == AdvisorySignal.CONCERN


# The instruction we give the LLM. Deliberately narrow: only flag specific,
# checkable binary events — NOT general market sentiment or vibes.
ADVISORY_SYSTEM_PROMPT = """You are a risk-review assistant for a systematic \
options-selling bot. The bot sells put credit spreads (30-45 days to expiry) \
on liquid US stocks to collect premium. It already filters out names with \
scheduled earnings inside the trade window. Your ONLY job is to catch \
SPECIFIC, CHECKABLE binary-event risks the bot's data feeds cannot see.

You should raise a CONCERN only if you find concrete evidence of one of these \
within roughly the next 45 days for the given ticker:
- A pending FDA decision / PDUFA date / clinical trial readout
- An announced or strongly-rumored M&A / acquisition / merger
- A trading halt currently in effect
- An SEC investigation, Wells Notice, fraud allegation, or accounting \
restatement announced recently
- An unscheduled special event likely to cause a large gap (investor day with \
guidance, major product/legal decision)
- Evidence the company's earnings date is actually inside the next 45 days \
despite the bot thinking otherwise

Do NOT raise a concern for: general market sentiment, recent price moves, \
analyst opinions, "the stock seems volatile", broad macro risk, or vague \
unease. Those are not specific binary events and the bot already prices \
volatility.

Respond in this exact format:
SIGNAL: NO_CONCERN  (or CONCERN)
EVENTS: comma-separated list of specific events, or NONE
REASONING: one or two sentences."""


class LLMAdvisor:
    """
    Runs the advisory pass over a list of orders. Flag-and-log only.

    advise_fn signature: (symbol: str) -> str
      It should return the LLM's raw text response. The advisor parses it.
      If advise_fn raises or returns empty, the advisory is UNAVAILABLE and
      the order proceeds untouched.
    """

    def __init__(self, advise_fn: Optional[Callable[[str], str]] = None):
        self.advise_fn = advise_fn
        self.enabled = advise_fn is not None
        if not self.enabled:
            logger.info("LLMAdvisor: no advise_fn provided — advisory disabled.")

    def review_symbol(self, symbol: str) -> Advisory:
        """Run the advisory for one symbol. Never raises."""
        if not self.enabled:
            return Advisory(symbol, AdvisorySignal.UNAVAILABLE, "Advisory disabled.")
        try:
            raw = self.advise_fn(symbol)
        except Exception as e:
            logger.warning("Advisory failed for %s: %s", symbol, e)
            return Advisory(symbol, AdvisorySignal.UNAVAILABLE, f"Advisory error: {e}")
        if not raw or not raw.strip():
            return Advisory(symbol, AdvisorySignal.UNAVAILABLE, "Empty advisory response.")
        return self._parse(symbol, raw)

    def review_orders(self, symbols: list[str]) -> dict[str, Advisory]:
        """Run advisory for a list of symbols. Returns {symbol: Advisory}."""
        results: dict[str, Advisory] = {}
        for symbol in symbols:
            results[symbol] = self.review_symbol(symbol)
        n_concern = sum(1 for a in results.values() if a.is_concern)
        logger.info(
            "Advisory reviewed %d symbols: %d concerns flagged (advisory is "
            "informational — no orders blocked).",
            len(symbols), n_concern,
        )
        return results

    @staticmethod
    def _parse(symbol: str, raw: str) -> Advisory:
        """Parse the LLM's structured response. Lenient — defaults to NO_CONCERN."""
        signal = AdvisorySignal.NO_CONCERN
        events: list[str] = []
        reasoning = ""

        for line in raw.splitlines():
            line = line.strip()
            upper = line.upper()
            if upper.startswith("SIGNAL:"):
                val = line.split(":", 1)[1].strip().upper()
                if "CONCERN" in val and "NO_CONCERN" not in val and "NO CONCERN" not in val:
                    signal = AdvisorySignal.CONCERN
            elif upper.startswith("EVENTS:"):
                val = line.split(":", 1)[1].strip()
                if val and val.upper() != "NONE":
                    events = [e.strip() for e in val.split(",") if e.strip()]
            elif upper.startswith("REASONING:"):
                reasoning = line.split(":", 1)[1].strip()

        # Safety: if events were listed, treat as a concern even if SIGNAL line
        # was ambiguous.
        if events and signal == AdvisorySignal.NO_CONCERN:
            signal = AdvisorySignal.CONCERN

        return Advisory(symbol, signal, reasoning or raw.strip()[:300], events)


def build_advisory_fn() -> Optional[Callable[[str], str]]:
    """
    Reference implementation of advise_fn using the Anthropic SDK with web
    search. Optional — returns None if the SDK or API key isn't available, in
    which case the advisor stays disabled and the bot runs normally.

    Requires: pip install anthropic, and ANTHROPIC_API_KEY in the environment.
    """
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("No ANTHROPIC_API_KEY — LLM advisory will be disabled.")
        return None

    try:
        from anthropic import Anthropic
    except ImportError:
        logger.info("anthropic SDK not installed — LLM advisory disabled. "
                     "(pip install anthropic to enable.)")
        return None

    client = Anthropic(api_key=api_key)
    # Versioned model string (never an alias) so behavior is stable in
    # production. Override via ADVISORY_MODEL in .env to bump versions without
    # a code change.
    model = os.environ.get("ADVISORY_MODEL", "claude-sonnet-4-6")

    def advise(symbol: str) -> str:
        message = client.messages.create(
            model=model,
            max_tokens=400,
            system=ADVISORY_SYSTEM_PROMPT,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{
                "role": "user",
                "content": (
                    f"Review ticker {symbol} for any specific binary-event "
                    f"risk in the next ~45 days. Search recent news if needed."
                ),
            }],
        )
        # Concatenate text blocks from the response
        parts = []
        for block in message.content:
            if getattr(block, "type", None) == "text":
                parts.append(block.text)
        return "\n".join(parts)

    logger.info("LLM advisory enabled (Anthropic SDK + web search).")
    return advise
