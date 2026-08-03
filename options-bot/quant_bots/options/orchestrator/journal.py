"""
Trade journal — a durable, append-only record of everything the bot does.

This is the missing audit trail. Every meaningful action — an opening order
placed, a closing order placed, a fill observed, a kill-switch trip, a job run
— gets appended as one JSON line to a daily file:

    data/journal/journal_<YYYY-MM>.jsonl

Why JSONL (one JSON object per line) instead of one big JSON file:
  - Append-only: we never rewrite the file, so a crash mid-write can at worst
    lose the last line, never corrupt history.
  - Streamable: you can tail it, grep it, or load it incrementally.
  - Monthly rollover keeps individual files manageable over years of trading.

Why this matters:
  - Without it, "how did the bot do last month?" is unanswerable — the
    data/cache JSONs get overwritten every run.
  - For the 2-3 month paper-trading evaluation, this IS the performance record.
  - For eventual live trading, it's the audit trail for every dollar.

Each record has at minimum: timestamp_utc, event_type, and event-specific
fields. The schema is intentionally loose (just a dict) so we can add event
types without migrations.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradeJournal:
    """Append-only JSONL journal with monthly file rollover."""

    def __init__(self, journal_dir: Path):
        self.journal_dir = journal_dir
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    def _current_path(self) -> Path:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.journal_dir / f"journal_{month}.jsonl"

    def record(self, event_type: str, **fields: Any) -> None:
        """
        Append one event. Never raises — a journaling failure must not crash a
        trading job (it's logged instead).
        """
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            **fields,
        }
        try:
            with self._current_path().open("a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.warning("Failed to write journal entry (%s): %s", event_type, e)

    # ─── Convenience recorders for the common events ──────────────────────────

    def record_open(self, symbol: str, short_strike: float, long_strike: float,
                    contracts: int, credit: float, mode: str,
                    order_id: Any = None, status: str = None) -> None:
        self.record(
            "order_open", symbol=symbol, short_strike=short_strike,
            long_strike=long_strike, contracts=contracts, credit=credit,
            mode=mode, order_id=order_id, status=status,
        )

    def record_close(self, symbol: str, short_strike: float, long_strike: float,
                     contracts: int, decision: str, realized_pnl: float,
                     mode: str, order_id: Any = None, status: str = None) -> None:
        self.record(
            "order_close", symbol=symbol, short_strike=short_strike,
            long_strike=long_strike, contracts=contracts, decision=decision,
            realized_pnl=realized_pnl, mode=mode, order_id=order_id, status=status,
        )

    def record_job(self, job_name: str, mode: str, success: bool,
                   summary: str) -> None:
        self.record("job_run", job_name=job_name, mode=mode,
                    success=success, summary=summary)

    def record_kill_switch(self, reason: str, mode: str) -> None:
        self.record("kill_switch", reason=reason, mode=mode)

    def record_fill(self, symbol: str, order_id: Any, status: str,
                    fill_price: float = None) -> None:
        self.record("fill_observed", symbol=symbol, order_id=order_id,
                    status=status, fill_price=fill_price)

    # ─── Reading back ─────────────────────────────────────────────────────────

    def read_all(self) -> list[dict]:
        """Read every journal entry across all monthly files, oldest first."""
        entries: list[dict] = []
        for path in sorted(self.journal_dir.glob("journal_*.jsonl")):
            try:
                for line in path.read_text().splitlines():
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            except Exception as e:
                logger.warning("Could not read journal %s: %s", path, e)
        return entries

    def summarize_realized_pnl(self) -> dict:
        """
        Quick performance summary from the journal: count of opens/closes and
        total realized P&L. Useful for the 'how did the bot do' question.
        """
        entries = self.read_all()
        opens = [e for e in entries if e.get("event_type") == "order_open"]
        closes = [e for e in entries if e.get("event_type") == "order_close"]
        realized = sum(float(e.get("realized_pnl") or 0) for e in closes)
        wins = sum(1 for e in closes if float(e.get("realized_pnl") or 0) > 0)
        losses = sum(1 for e in closes if float(e.get("realized_pnl") or 0) < 0)
        return {
            "total_opens": len(opens),
            "total_closes": len(closes),
            "realized_pnl": realized,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(closes)) if closes else 0.0,
        }
