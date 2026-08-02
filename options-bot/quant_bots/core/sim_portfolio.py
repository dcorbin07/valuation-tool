"""
Simulated portfolio accounting — the per-bot "paper account in software."

This lets all three bots run against ONE shared data source while each keeps its
OWN independent simulated book and P&L track record. That's how multi-strategy
shops actually measure pods: not in separate brokerage accounts, but as
separate accounting books in software. It means you never need more than one
Tradier sandbox login, and each strategy's return/correlation can be measured
cleanly.

Model: PURE SIMULATION for fills, REAL quotes for marking.
  - When the bot "places" an order, we assume it fills immediately at the
    provided price (the current quoted mid). No broker round-trip, so the
    sandbox's flaky fill engine never corrupts the experiment.
  - Each day we mark all holdings to market using real quotes (the same quotes
    the strategy already fetches), compute total equity, and append a snapshot
    to the equity curve. That curve is the strategy's track record and the
    input to the later correlation analysis.

Optional slippage knob (default 0): apply a per-share cost to each fill to
approximate crossing the bid-ask spread, for absolute-return realism later.
For comparing strategies against each other it can stay off — the optimism of
mid-fills applies about equally to all three.

State files (per bot, under its data/sim/):
  - portfolio.json      current cash + holdings (signed share counts + avg cost)
  - equity_curve.jsonl  one daily mark-to-market snapshot per line

These are LOCAL files — fast, always-available, and surviving zip re-extraction
(the packaging excludes data/sim/). They are never written to Google Drive or
any network store; the bots need instant, reliable read/write every run.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SimHolding:
    symbol: str
    shares: int            # signed: + long, − short
    avg_cost: float        # average entry price per share (absolute)

    def market_value(self, price: float) -> float:
        """Signed market value of the position at `price`."""
        return self.shares * price

    def unrealized_pnl(self, price: float) -> float:
        """
        Unrealized P&L. For a long: (price − cost) × shares. For a short, shares
        is negative, so the same formula gives the correct sign (you profit when
        price falls below your short entry).
        """
        return (price - self.avg_cost) * self.shares


@dataclass
class SimPortfolio:
    """A bot's simulated account: cash + holdings, with realized P&L tracking."""

    cash: float
    starting_equity: float
    holdings: dict = field(default_factory=dict)   # symbol -> SimHolding
    realized_pnl: float = 0.0

    # ─── Persistence ─────────────────────────────────────────────────────────

    @classmethod
    def load_or_init(cls, path: Path, initial_cash: float = 100_000.0) -> "SimPortfolio":
        if path.exists():
            try:
                d = json.loads(path.read_text())
                holdings = {
                    s: SimHolding(**h) for s, h in d.get("holdings", {}).items()
                }
                return cls(
                    cash=float(d["cash"]),
                    starting_equity=float(d["starting_equity"]),
                    holdings=holdings,
                    realized_pnl=float(d.get("realized_pnl", 0.0)),
                )
            except Exception as e:
                logger.warning("Could not parse sim portfolio at %s: %s; "
                               "starting fresh.", path, e)
        return cls(cash=initial_cash, starting_equity=initial_cash)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cash": self.cash,
            "starting_equity": self.starting_equity,
            "realized_pnl": self.realized_pnl,
            "holdings": {s: asdict(h) for s, h in self.holdings.items()},
        }
        path.write_text(json.dumps(payload, indent=2))

    # ─── Fills (pure simulation) ───────────────────────────────────────────────

    def apply_fill(self, symbol: str, signed_shares: int, price: float,
                   slippage_per_share: float = 0.0) -> None:
        """
        Apply a simulated fill of `signed_shares` (+ buy/long, − sell/short) at
        `price`. Updates cash, holdings, average cost, and realized P&L.

        Slippage (optional): worsens the effective price by this much per share
        (you pay a bit more buying, receive a bit less selling). Default 0.
        """
        if signed_shares == 0 or price <= 0:
            return

        # Effective price including slippage (always works against you)
        eff_price = price + slippage_per_share if signed_shares > 0 else price - slippage_per_share

        # Cash impact: buying shares costs cash (negative), selling adds cash.
        self.cash -= signed_shares * eff_price

        existing = self.holdings.get(symbol)
        if existing is None:
            self.holdings[symbol] = SimHolding(symbol, signed_shares, eff_price)
            return

        old_shares = existing.shares
        new_shares = old_shares + signed_shares

        # Case 1: adding to the same side (or from zero) — update avg cost.
        if old_shares == 0 or (old_shares > 0) == (signed_shares > 0):
            total_cost = existing.avg_cost * abs(old_shares) + eff_price * abs(signed_shares)
            existing.avg_cost = total_cost / abs(new_shares) if new_shares != 0 else 0.0
            existing.shares = new_shares

        # Case 2: reducing or closing/flipping the position — realize P&L.
        else:
            closing = min(abs(signed_shares), abs(old_shares))
            # Realized P&L on the closed portion (sign handled by direction)
            direction = 1 if old_shares > 0 else -1
            self.realized_pnl += direction * (eff_price - existing.avg_cost) * closing

            if abs(signed_shares) <= abs(old_shares):
                existing.shares = new_shares
                if existing.shares == 0:
                    del self.holdings[symbol]
            else:
                # Flipped through zero to the other side; remaining opens new pos
                remaining = abs(signed_shares) - abs(old_shares)
                existing.shares = int(direction * -1 * remaining)
                existing.avg_cost = eff_price

    # ─── Valuation ─────────────────────────────────────────────────────────────

    def total_equity(self, prices: dict[str, float]) -> float:
        """Cash + market value of all holdings (using provided prices)."""
        mv = 0.0
        for sym, h in self.holdings.items():
            p = prices.get(sym, h.avg_cost)  # fall back to cost if no quote
            mv += h.market_value(p)
        return self.cash + mv

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(h.unrealized_pnl(prices.get(s, h.avg_cost))
                   for s, h in self.holdings.items())

    def signed_shares(self) -> dict[str, int]:
        """Current holdings as {symbol: signed_shares} — for rebalance diffing."""
        return {s: h.shares for s, h in self.holdings.items() if h.shares != 0}

    # ─── Equity curve logging ──────────────────────────────────────────────────

    def record_equity_snapshot(self, curve_path: Path, prices: dict[str, float],
                               label: str = "") -> dict:
        """Append a daily mark-to-market snapshot to the equity curve JSONL."""
        equity = self.total_equity(prices)
        snapshot = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "date": date.today().isoformat(),
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl(prices), 2),
            "num_positions": len(self.holdings),
            "return_since_start": round((equity / self.starting_equity - 1.0), 6)
                                  if self.starting_equity > 0 else 0.0,
            "label": label,
        }
        curve_path.parent.mkdir(parents=True, exist_ok=True)
        with curve_path.open("a") as f:
            f.write(json.dumps(snapshot) + "\n")
        return snapshot
