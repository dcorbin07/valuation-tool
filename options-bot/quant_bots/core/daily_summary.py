"""
End-of-day summary for Discord — a daily heartbeat across all bots.

Reads each bot's sim equity curve (and journal, if present) and posts a single
digest to Discord: where each strategy stands, what it did today, and the
combined picture. Works for sim, paper, and live — it just reads whatever each
bot recorded that day.

This is what makes running unattended on Oracle comfortable: instead of silence,
you get one message a day confirming the bots ran and how they're doing. If
Discord isn't configured, it logs the same summary instead.

Designed to run as its own small scheduled job (after the market closes) on the
same box as the bots, so it sees their files directly. No data leaves the box
except the human-readable summary.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_COLOR_GREEN = 0x2ECC71
_COLOR_RED = 0xE74C3C
_COLOR_BLUE = 0x3498DB


@dataclass
class BotDaySummary:
    bot: str
    has_data: bool
    equity: float = 0.0
    day_return: float = 0.0          # today vs prior snapshot
    total_return: float = 0.0        # since start
    num_positions: int = 0
    realized_pnl: float = 0.0
    note: str = ""


def _read_curve(project_root: Path, bot: str) -> list[dict]:
    path = project_root / "data" / "sim" / bot / "equity_curve.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summarize_bot(project_root: Path, bot: str) -> BotDaySummary:
    curve = _read_curve(project_root, bot)
    if not curve:
        return BotDaySummary(bot=bot, has_data=False, note="no data yet")

    latest = curve[-1]
    prior = curve[-2] if len(curve) >= 2 else None
    day_return = 0.0
    if prior and prior.get("equity", 0) > 0:
        day_return = latest["equity"] / prior["equity"] - 1.0

    return BotDaySummary(
        bot=bot,
        has_data=True,
        equity=latest.get("equity", 0.0),
        day_return=day_return,
        total_return=latest.get("return_since_start", 0.0),
        num_positions=latest.get("num_positions", 0),
        realized_pnl=latest.get("realized_pnl", 0.0),
    )


def build_summaries(project_root: Path, bots: list[str]) -> list[BotDaySummary]:
    return [summarize_bot(project_root, b) for b in bots]


def post_end_of_day(notifier, project_root: Path,
                    bots: Optional[list[str]] = None, mode: str = "") -> bool:
    """
    Build and send the end-of-day digest. `notifier` is a DiscordNotifier (or
    anything with send_embed/send). Returns True if a message was sent.
    """
    bots = bots or ["options", "trend", "momentum", "reversion"]
    summaries = build_summaries(project_root, bots)
    active = [s for s in summaries if s.has_data]

    today = date.today().isoformat()
    if not active:
        return notifier.send(f"📊 End-of-day {today}: no bot data recorded yet.")

    # Combined equity + a simple equal-weight combined day-return view
    total_equity = sum(s.equity for s in active)
    combined_day = (sum(s.day_return for s in active) / len(active)) if active else 0.0
    up = combined_day >= 0
    color = _COLOR_GREEN if up else _COLOR_RED

    fields = []
    for s in active:
        arrow = "▲" if s.day_return >= 0 else "▼"
        fields.append({
            "name": s.bot,
            "value": (f"Equity ${s.equity:,.0f}\n"
                      f"{arrow} {s.day_return*100:+.2f}% today\n"
                      f"{s.total_return*100:+.2f}% total\n"
                      f"{s.num_positions} positions"),
            "inline": True,
        })

    mode_tag = f" [{mode}]" if mode else ""
    title = f"📊 End-of-Day Summary — {today}{mode_tag}"
    description = (f"Combined equity ${total_equity:,.0f} · "
                  f"avg day move {combined_day*100:+.2f}%\n"
                  f"{len(active)} of {len(bots)} strategies active.")

    return notifier.send_embed(title, description, color=color, fields=fields)
