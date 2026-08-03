"""
Account state persistence.

The risk layer needs to know "what was the account worth at the start of today"
so it can compute today's drawdown and trigger the daily loss kill switch.
This module persists that snapshot in a tiny JSON file.

Pattern:
    state = AccountState.load_or_init(path, current_equity=tradier.get_account_value())
    # state.starting_equity is the equity at first run of the day
    # state.last_seen_equity gets updated on each run

The file rolls over at calendar-day boundaries. If you run the bot for the
first time today, it snapshots current equity as today's starting equity.
Subsequent runs the same day use the same starting equity. Tomorrow's first
run rolls forward.

This is intentionally simple — no SQL, no schema migration. If the file gets
corrupted or deleted, the worst that happens is the kill switch resets for
the day, which fails open. We'll add audit logging in V9.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AccountState:
    """One-day-rolling snapshot of account equity."""

    date: str                  # ISO date "YYYY-MM-DD" — today's date
    starting_equity: float     # equity at first run of the day
    last_seen_equity: float    # equity at most recent run

    @classmethod
    def load_or_init(
        cls,
        path: Path,
        current_equity: float,
        today: Optional[date] = None,
    ) -> "AccountState":
        """
        Load state from `path` if it exists and is for today; otherwise create
        fresh state with `current_equity` as today's starting equity.

        Always writes the (possibly-updated) state back to `path` before
        returning so subsequent runs see consistent data.
        """
        today = today or date.today()
        today_iso = today.isoformat()

        existing: Optional[AccountState] = None
        if path.exists():
            try:
                payload = json.loads(path.read_text())
                existing = AccountState(
                    date=payload["date"],
                    starting_equity=float(payload["starting_equity"]),
                    last_seen_equity=float(payload["last_seen_equity"]),
                )
            except (ValueError, KeyError, TypeError) as e:
                logger.warning(
                    "Could not parse account state at %s: %s; rebuilding fresh",
                    path, e,
                )
                existing = None

        if existing is not None and existing.date == today_iso:
            # Same day — update last_seen_equity but keep starting_equity
            state = AccountState(
                date=today_iso,
                starting_equity=existing.starting_equity,
                last_seen_equity=current_equity,
            )
        else:
            # New day (or first run ever) — snapshot fresh
            if existing is not None:
                logger.info(
                    "Account state rolled from %s to %s (starting_equity reset)",
                    existing.date, today_iso,
                )
            state = AccountState(
                date=today_iso,
                starting_equity=current_equity,
                last_seen_equity=current_equity,
            )

        state.save(path)
        return state

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2))

    def day_pnl_pct(self) -> float:
        """Today's P&L as a fraction of starting equity. Negative = down."""
        if self.starting_equity <= 0:
            return 0.0
        return (self.last_seen_equity - self.starting_equity) / self.starting_equity
