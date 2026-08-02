"""
Simulated portfolio for the OPTIONS bot — the spread-level analogue of the
equity SimPortfolio used by the trend/momentum bots.

The options bot is shaped differently from the rebalance bots: it OPENS put
credit spreads that live for weeks, then CLOSES them on a profit target, stop,
or time exit. So its simulated book has to hold open spreads, mark each to
market over many days using real option quotes, and realize P&L on close.

Model (pure simulation, same philosophy as the equity sim):
  - Opening a spread: assume it fills at the quoted net credit. We receive that
    credit into cash and record the open spread.
  - Marking to market: each manage cycle, re-quote each open spread's legs and
    compute the cost to buy it back now → unrealized P&L vs the credit received.
  - Closing a spread: assume it fills at the current buy-to-close cost. Realize
    the P&L (credit received − cost to close, × contracts × 100).

State files (data/sim/options/):
  - portfolio.json        cash, realized P&L, list of open spreads
  - equity_curve.jsonl    ONE mark-to-market row per trading day (same format
                          and cadence as the trend/momentum/reversion curves)
  - equity_intraday.jsonl every intraday mark, append-only, for monitoring

The equity-curve format AND CADENCE are IDENTICAL to the trend/momentum sim
curves, so the correlation tracker and end-of-day summary work on it unchanged.

A note on why the curve is one row per day:
  The options bot's manage job runs every 30 minutes from 10:00-16:00 ET — 12
  times a day — while the other three bots run once. Appending on every manage
  cycle gave the options curve ~12x the rows of its siblings, all stamped with
  the same date. Any statistic computed by walking rows (daily returns, vol,
  Sharpe, and the cross-strategy correlation matrix that is the entire point of
  running four bots in parallel) would then be comparing 12 intraday steps
  against one daily step and calling both "a day". So record_equity_snapshot
  UPSERTS by date: the last write of the day wins and the curve keeps exactly
  one row per trading day. The intraday detail is not thrown away — it goes to
  equity_intraday.jsonl, which no cross-strategy statistic reads.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Union

logger = logging.getLogger(__name__)

CONTRACT_MULTIPLIER = 100  # one option contract = 100 shares of exposure

# Sibling of equity_curve.jsonl holding every intraday mark.
INTRADAY_CURVE_FILENAME = "equity_intraday.jsonl"


@dataclass
class SimSpread:
    """An open put credit spread in the simulated book.

    NOTE on units: credit_received_per_spread and all close costs are in
    PER-SPREAD DOLLARS (i.e. premium-per-share × 100). So a $0.72/share credit
    is stored as 72.0. Cash flows multiply only by `contracts` (the ×100 is
    already baked into the per-spread dollar figure).
    """
    spread_id: str                      # unique: f"{underlying}-{exp}-{short}-{long}"
    underlying: str
    expiration: str                     # ISO date
    short_strike: float
    long_strike: float
    contracts: int
    credit_received_per_spread: float   # net credit per spread when opened ($, per-spread)
    short_put_occ: str = ""
    long_put_occ: str = ""

    @property
    def total_credit(self) -> float:
        """Total credit received across all contracts (cash inflow at open)."""
        return self.credit_received_per_spread * self.contracts

    def unrealized_pnl(self, close_cost_per_spread: float) -> float:
        """
        P&L if marked at `close_cost_per_spread` (per-spread dollars to
        buy-to-close one spread now). Profit = credit received − cost to close.
        """
        return (self.credit_received_per_spread - close_cost_per_spread) * self.contracts


@dataclass
class OptionsSimPortfolio:
    cash: float
    starting_equity: float
    open_spreads: dict = field(default_factory=dict)   # spread_id -> SimSpread
    realized_pnl: float = 0.0

    # ─── Persistence ─────────────────────────────────────────────────────────

    @classmethod
    def load_or_init(
        cls,
        path: Path,
        initial_cash: Union[float, Callable[[], float]] = 100_000.0,
    ) -> "OptionsSimPortfolio":
        """
        Load the sim book, or start a fresh one seeded with `initial_cash`.

        `initial_cash` may be a callable, which is only invoked when we actually
        need to seed a new book. The caller's seed value is a live broker call
        (Jobs._sim_initial_cash -> tradier.get_account_value()), and the manage
        job runs 12x a day against an existing file — so evaluating it eagerly
        meant a dozen pointless round-trips a day whose result was discarded.
        """
        if path.exists():
            try:
                d = json.loads(path.read_text())
                spreads = {sid: SimSpread(**s) for sid, s in d.get("open_spreads", {}).items()}
                return cls(cash=float(d["cash"]), starting_equity=float(d["starting_equity"]),
                           open_spreads=spreads, realized_pnl=float(d.get("realized_pnl", 0.0)))
            except Exception as e:
                logger.warning("Could not parse options sim portfolio at %s: %s; fresh.", path, e)
        seed = float(initial_cash() if callable(initial_cash) else initial_cash)
        return cls(cash=seed, starting_equity=seed)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cash": self.cash,
            "starting_equity": self.starting_equity,
            "realized_pnl": self.realized_pnl,
            "open_spreads": {sid: asdict(s) for sid, s in self.open_spreads.items()},
        }
        path.write_text(json.dumps(payload, indent=2))

    # ─── Open / close (pure simulation) ────────────────────────────────────────

    def open_spread(self, spread: SimSpread) -> None:
        """Open a spread: receive its credit into cash, record it."""
        if spread.spread_id in self.open_spreads:
            logger.debug("Spread %s already open; skipping.", spread.spread_id)
            return
        self.cash += spread.total_credit          # credit received up front
        self.open_spreads[spread.spread_id] = spread

    def close_spread(self, spread_id: str, close_cost_per_spread: float) -> float:
        """
        Close a spread at `close_cost_per_spread` (buy-to-close cost per spread).
        Pay the cost from cash, realize P&L, remove it. Returns realized P&L.
        """
        spread = self.open_spreads.get(spread_id)
        if spread is None:
            return 0.0
        cost = close_cost_per_spread * spread.contracts
        self.cash -= cost                          # pay to buy it back
        pnl = spread.unrealized_pnl(close_cost_per_spread)
        self.realized_pnl += pnl
        del self.open_spreads[spread_id]
        return pnl

    # ─── Valuation ─────────────────────────────────────────────────────────────

    def total_equity(self, close_costs: dict[str, float]) -> float:
        """
        Cash + the liability of buying back all open spreads. close_costs maps
        spread_id -> current buy-to-close cost per spread. A spread we received
        credit for is a liability until closed (we'd pay to exit), so its
        marked value reduces equity by the current close cost × size.
        """
        liability = 0.0
        for sid, s in self.open_spreads.items():
            cost = close_costs.get(sid, s.credit_received_per_spread)  # fallback: flat
            liability += cost * s.contracts
        return self.cash - liability

    def unrealized_pnl(self, close_costs: dict[str, float]) -> float:
        return sum(s.unrealized_pnl(close_costs.get(sid, s.credit_received_per_spread))
                   for sid, s in self.open_spreads.items())

    # ─── Equity curve logging (same format as the equity sim) ──────────────────

    def record_equity_snapshot(self, curve_path: Path, close_costs: dict[str, float],
                               label: str = "", record_intraday: bool = True) -> dict:
        """
        Write today's mark to the equity curve, replacing any earlier row for
        the same date, and append the same mark to the intraday log.

        Last write of the day wins. That is the right rule for a curve that is
        meant to be a daily close: at 10:30 we have a provisional mark, by 15:30
        we have a better one, and only one of them should end up in the series
        the correlation tracker reads. See the module docstring for why one row
        per day matters.
        """
        equity = self.total_equity(close_costs)
        snapshot = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "date": date.today().isoformat(),
            "equity": round(equity, 2),
            "cash": round(self.cash, 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "unrealized_pnl": round(self.unrealized_pnl(close_costs), 2),
            "num_positions": len(self.open_spreads),
            "return_since_start": round((equity / self.starting_equity - 1.0), 6)
                                  if self.starting_equity > 0 else 0.0,
            "label": label,
        }
        curve_path.parent.mkdir(parents=True, exist_ok=True)

        if record_intraday:
            # Every mark, append-only. Nothing cross-strategy reads this file;
            # it exists so upserting the daily curve doesn't destroy history.
            intraday_path = curve_path.parent / INTRADAY_CURVE_FILENAME
            try:
                with intraday_path.open("a") as f:
                    f.write(json.dumps(snapshot) + "\n")
            except OSError as e:
                logger.warning("Could not append intraday mark to %s: %s", intraday_path, e)

        _upsert_daily_row(curve_path, snapshot)
        return snapshot


# ─── Equity-curve file helpers ──────────────────────────────────────────────


def _upsert_daily_row(curve_path: Path, snapshot: dict) -> None:
    """
    Replace any existing row for snapshot["date"] with `snapshot`, keeping the
    file to exactly one row per trading day and preserving date order.

    Written atomically (temp file + os.replace) so a crash mid-write cannot
    leave a truncated curve — this file is the only record of the simulated
    track record, and rewriting it in place on every manage cycle would
    otherwise be 12 daily chances to lose it.
    """
    today = snapshot["date"]
    rows: list[dict] = []
    if curve_path.exists():
        for line in curve_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # Keep unparseable lines out of the rewrite rather than
                # crashing; log so a corrupted curve is visible.
                logger.warning("Dropping unparseable equity-curve line in %s", curve_path)
                continue
            if row.get("date") == today:
                continue  # superseded by this snapshot
            rows.append(row)
    rows.append(snapshot)

    tmp_fd, tmp_name = tempfile.mkstemp(dir=str(curve_path.parent), suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        os.replace(tmp_name, curve_path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise
