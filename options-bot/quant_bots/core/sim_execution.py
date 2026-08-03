"""
Sim-execution helper shared by the trend and momentum orchestrators.

When a bot runs in SIM mode, instead of sending orders to the broker we:
  1. Use the bot's own SimPortfolio as the source of "current positions"
     (so the rebalance diff is against the simulated book, not the broker).
  2. Apply each rebalance order as an assumed fill at the order's price.
  3. Mark the book to market with real quotes and append an equity snapshot.

This keeps each bot's simulated account fully independent — one shared sandbox
for quotes, but separate books per bot. The two orchestrators call these two
functions so the logic lives in one place.
"""
from __future__ import annotations

import logging
from pathlib import Path

from .sim_portfolio import SimPortfolio

logger = logging.getLogger(__name__)

# Map equity order sides to a signed share multiplier for the sim book.
_SIDE_SIGN = {
    "buy": +1,
    "buy_to_cover": +1,
    "sell": -1,
    "sell_short": -1,
}


def sim_paths(project_root: Path, bot_name: str) -> tuple[Path, Path]:
    """(portfolio.json, equity_curve.jsonl) paths for a given bot's sim book."""
    base = project_root / "data" / "sim" / bot_name
    return base / "portfolio.json", base / "equity_curve.jsonl"


def load_sim(project_root: Path, bot_name: str, initial_cash: float) -> SimPortfolio:
    pf_path, _ = sim_paths(project_root, bot_name)
    return SimPortfolio.load_or_init(pf_path, initial_cash=initial_cash)


def resolve_prices(
    tradier,
    base_prices: dict[str, float],
    required_symbols,
    batch_size: int = 50,
) -> tuple[dict[str, float], list[str]]:
    """
    Guarantee a price for every symbol in `required_symbols`.

    WHY THIS EXISTS: the signal layer only knows prices for names it scored
    this cycle. A position that has since dropped OUT of the selection has no
    price — and apply_orders_to_sim() silently skips any order it can't price.
    That meant EXIT orders never filled: positions accumulated forever and were
    marked at entry cost (frozen P&L), corrupting the equity curve. Any caller
    that applies orders to a sim book MUST route through here first.

    Returns (prices, unresolved). `prices` is a copy of base_prices topped up
    with live quotes; `unresolved` lists symbols we still couldn't price, which
    the caller must surface rather than swallow.
    """
    prices = dict(base_prices)
    missing = [s for s in dict.fromkeys(required_symbols)
               if prices.get(s, 0.0) <= 0]
    if not missing:
        return prices, []

    for i in range(0, len(missing), batch_size):
        batch = missing[i:i + batch_size]
        try:
            quotes = tradier.get_quotes(batch)
        except Exception as e:
            logger.warning("Quote backfill failed for %s: %s", batch, e)
            continue
        for q in quotes or []:
            sym = q.get("symbol")
            if not sym:
                continue
            for field in ("last", "close", "prevclose"):
                try:
                    px = float(q.get(field) or 0)
                except (TypeError, ValueError):
                    continue
                if px > 0:
                    prices[sym] = px
                    break

    unresolved = [s for s in missing if prices.get(s, 0.0) <= 0]
    if unresolved:
        logger.warning(
            "Could not price %d held symbol(s) after quote backfill: %s. "
            "Orders on these will NOT fill in the sim book.",
            len(unresolved), unresolved,
        )
    return prices, unresolved


def apply_orders_to_sim(
    sim: SimPortfolio,
    orders: list,
    last_prices: dict[str, float],
    slippage_per_share: float = 0.0,
) -> list[dict]:
    """
    Apply rebalance orders (objects with .symbol/.side/.quantity) to the sim
    book as assumed fills at the latest quoted price. Returns fill records.

    An order with no usable price is SKIPPED. That is a data problem, not a
    normal outcome — callers should pre-resolve prices with resolve_prices()
    so this never fires. It logs at WARNING because a silent skip on an exit
    order strands the position and freezes its P&L.
    """
    fills = []
    for o in orders:
        sign = _SIDE_SIGN.get(o.side.value, 0)
        price = last_prices.get(o.symbol, 0.0)
        if sign == 0 or price <= 0:
            logger.warning(
                "SKIPPING sim fill for %s %s %s — no usable price. If this is an "
                "exit, the position stays open and marks at cost.",
                getattr(o.side, "value", o.side), getattr(o, "quantity", "?"), o.symbol,
            )
            continue
        signed = sign * o.quantity
        sim.apply_fill(o.symbol, signed, price, slippage_per_share=slippage_per_share)
        fills.append({"symbol": o.symbol, "side": o.side.value,
                      "qty": o.quantity, "fill_price": price})
    return fills


def finalize_sim(
    sim: SimPortfolio, project_root: Path, bot_name: str,
    last_prices: dict[str, float], label: str = "",
) -> dict:
    """Persist the sim book and append an equity-curve snapshot. Returns it."""
    pf_path, curve_path = sim_paths(project_root, bot_name)
    sim.save(pf_path)
    return sim.record_equity_snapshot(curve_path, last_prices, label=label)
