#!/usr/bin/env python3
"""
Sync the portfolio: pull open positions, compute P&L, decide exits, and
preview any closing orders.

Reads:   live positions from Tradier
Writes:  data/cache/portfolio_<YYYY-MM-DD>.json

Every closing order is previewed only (preview=True hard-coded). No real
trades placed.

Usage:
    python scripts/sync_portfolio.py
    python scripts/sync_portfolio.py --no-preview-api    # just print decisions
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from broker import OrderType, TradierClient, TradierConfig, TradierError  # noqa: E402
from portfolio import ExitDecision, PortfolioConfig, PortfolioManager  # noqa: E402


def _load_env() -> tuple[str, str, bool]:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    token = os.environ.get("TRADIER_TOKEN")
    account_id = os.environ.get("TRADIER_ACCOUNT_ID")
    sandbox = os.environ.get("TRADIER_SANDBOX", "true").lower() != "false"
    if not token:
        sys.exit("ERROR: TRADIER_TOKEN not set.")
    if not account_id:
        sys.exit("ERROR: TRADIER_ACCOUNT_ID not set.")
    return token, account_id, sandbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync portfolio and preview exits.")
    parser.add_argument("--no-preview-api", action="store_true",
                          help="Skip Tradier closing-order previews.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("sync_portfolio")

    token, account_id, sandbox = _load_env()
    tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)

    with TradierClient(tradier_config) as tradier:
        manager = PortfolioManager(PortfolioConfig(), tradier)
        snapshot = manager.sync()

        # Preview closing orders for anything not HOLD
        preview_responses = []
        to_close = snapshot.positions_to_close()
        if not args.no_preview_api and to_close:
            for i, spread in enumerate(to_close, start=1):
                logger.info(
                    "Previewing close %d/%d: %s %s/%s (%s)",
                    i, len(to_close),
                    spread.underlying, spread.short_strike, spread.long_strike,
                    spread.decision.value,
                )
                # To close a credit spread we pay a debit (buy back short,
                # sell long). Price at the current close cost per share.
                close_price = spread.current_close_cost_per_spread / 100.0
                try:
                    response = tradier.place_multileg_order(
                        underlying=spread.underlying,
                        legs=spread.to_closing_legs(),
                        order_type=OrderType.DEBIT,
                        price=round(max(close_price, 0.01), 2),
                        preview=True,
                        tag=f"close-{spread.underlying}",
                    )
                    preview_responses.append({
                        "underlying": spread.underlying,
                        "decision": spread.decision.value,
                        "ok": response.get("status") == "ok",
                        "raw": response,
                    })
                except TradierError as e:
                    logger.warning("Close preview failed for %s: %s", spread.underlying, e)
                    preview_responses.append({
                        "underlying": spread.underlying,
                        "decision": spread.decision.value,
                        "ok": False,
                        "error": str(e),
                    })

    # ─── Persist ─────────────────────────────────────────────────────────────
    out_path = PROJECT_ROOT / "data" / "cache" / f"portfolio_{date.today().isoformat()}.json"
    payload = {
        "synced_at": date.today().isoformat(),
        "total_unrealized_pnl": snapshot.total_unrealized_pnl,
        "spread_count": len(snapshot.spreads),
        "unpaired_leg_count": len(snapshot.unpaired_legs),
        "spreads": [
            {
                "underlying": s.underlying,
                "expiration": s.expiration.isoformat(),
                "short_strike": s.short_strike,
                "long_strike": s.long_strike,
                "contracts": s.contracts,
                "credit_received_per_spread": s.credit_received_per_spread,
                "current_close_cost_per_spread": s.current_close_cost_per_spread,
                "unrealized_pnl_dollars": s.unrealized_pnl_dollars,
                "pnl_pct_of_credit": s.pnl_pct_of_credit,
                "dte": s.dte,
                "decision": s.decision.value,
                "decision_reason": s.decision_reason,
            }
            for s in snapshot.spreads
        ],
        "preview_responses": preview_responses,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    logger.info("Saved to %s", out_path)

    # ─── Summary ─────────────────────────────────────────────────────────────
    print()
    print("=" * 80)
    print(f"  Portfolio: {len(snapshot.spreads)} open spreads, "
          f"total unrealized P&L ${snapshot.total_unrealized_pnl:,.2f}")
    if snapshot.unpaired_legs:
        print(f"  ⚠ {len(snapshot.unpaired_legs)} unpaired legs (couldn't form spreads)")
    print("=" * 80)
    print()

    if not snapshot.spreads:
        print("  No open spreads. Nothing to manage.")
        print("  (Expected — sandbox starts with no positions. Open some via")
        print("   build_orders.py with preview=False once you trust the bot,")
        print("   or manually in the Tradier sandbox UI, then re-run this.)")
        return 0

    print(f"  {'Symbol':<7} {'Short':>7} {'Long':>6} {'Ctrs':>4} "
          f"{'Credit':>7} {'Close':>7} {'P&L':>8} {'%Cred':>7} {'DTE':>4} {'Decision':>14}")
    print("  " + "-" * 84)
    for s in snapshot.spreads:
        print(
            f"  {s.underlying:<7} {s.short_strike:>7.1f} {s.long_strike:>6.1f} "
            f"{s.contracts:>4} ${s.credit_received_per_spread:>5.0f} "
            f"${s.current_close_cost_per_spread:>5.0f} "
            f"${s.unrealized_pnl_dollars:>6.0f} {s.pnl_pct_of_credit*100:>6.0f}% "
            f"{s.dte:>4} {s.decision.value:>14}"
        )
    print()

    closing = snapshot.positions_to_close()
    if closing:
        print(f"  {len(closing)} spread(s) flagged to close:")
        for s in closing:
            print(f"    [{s.underlying}] {s.decision_reason}")
        print()
        print("  NOTE: Closing orders previewed only. No real trades placed.")
    else:
        print("  All spreads HOLD — none meet exit criteria.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
