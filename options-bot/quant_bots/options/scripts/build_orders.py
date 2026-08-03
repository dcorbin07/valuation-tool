#!/usr/bin/env python3
"""
Build, risk-check, and preview orders from today's candidates.

Pipeline:
    candidates JSON  -> Strategy        -> raw orders
    raw orders + account state -> Risk  -> sized orders
    sized orders -> Tradier preview     -> preview responses (no real trades)

Every order is previewed only. Hard-coded preview=True. Use a separate
orchestrator (V8) for real placement.

Usage:
    python scripts/build_orders.py
    python scripts/build_orders.py --top 10
    python scripts/build_orders.py --account-value-override 25000
    python scripts/build_orders.py --no-preview-api
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from broker import (  # noqa: E402
    OptionLeg,
    OrderSide,
    OrderType,
    TradierClient,
    TradierConfig,
    TradierError,
    parse_occ_symbol,
)
from risk import (  # noqa: E402
    AccountState,
    RiskConfig,
    RiskManager,
)
from screener import ScreenedCandidate  # noqa: E402
from strategy import (  # noqa: E402
    PutCreditSpreadStrategy,
    StrategyConfig,
    make_fingerprint,
)


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


def _load_candidates(path: Path) -> list[ScreenedCandidate]:
    payload = json.loads(path.read_text())
    candidates = []
    for d in payload["candidates"]:
        candidates.append(ScreenedCandidate(
            symbol=d["symbol"], last_price=d["last_price"], is_etf=d["is_etf"],
            target_expiration=date.fromisoformat(d["target_expiration"]),
            dte=d["dte"],
            short_put_strike=d["short_put_strike"],
            short_put_delta=d["short_put_delta"],
            short_put_bid=d["short_put_bid"], short_put_ask=d["short_put_ask"],
            short_put_mid=d["short_put_mid"], short_put_iv=d["short_put_iv"],
            short_put_open_interest=d["short_put_open_interest"],
            long_put_strike=d["long_put_strike"],
            long_put_bid=d["long_put_bid"], long_put_ask=d["long_put_ask"],
            long_put_mid=d["long_put_mid"],
            spread_credit_mid=d["spread_credit_mid"],
            spread_max_loss=d["spread_max_loss"],
            spread_return_on_risk=d["spread_return_on_risk"],
            atm_iv=d["atm_iv"],
            next_earnings=(
                date.fromisoformat(d["next_earnings"]) if d.get("next_earnings") else None
            ),
        ))
    return candidates


def _fingerprints_from_positions(positions: list[dict]) -> set[str]:
    fingerprints = set()
    for pos in positions:
        symbol = pos.get("symbol", "")
        if len(symbol) < 16:
            continue
        try:
            opt = parse_occ_symbol(symbol)
        except Exception:
            continue
        for width in (5.0, 10.0):
            fingerprints.add(
                make_fingerprint(opt.underlying, opt.expiration, opt.strike, opt.strike - width)
            )
            fingerprints.add(
                make_fingerprint(opt.underlying, opt.expiration, opt.strike + width, opt.strike)
            )
    return fingerprints


def main() -> int:
    parser = argparse.ArgumentParser(description="Build, risk-check, and preview orders.")
    parser.add_argument("--top", type=int, default=None)
    parser.add_argument("--candidates", type=Path, default=None)
    parser.add_argument("--no-preview-api", action="store_true")
    parser.add_argument("--account-value-override", type=float, default=None,
                          help="Override account value for testing risk math.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("build_orders")

    # ─── Load candidates ─────────────────────────────────────────────────────
    candidates_path = args.candidates or (
        PROJECT_ROOT / "data" / "cache" / f"candidates_{date.today().isoformat()}.json"
    )
    if not candidates_path.exists():
        sys.exit(f"Candidates file not found: {candidates_path}\nRun screen.py first.")
    candidates = _load_candidates(candidates_path)
    if args.top:
        candidates = candidates[: args.top]
    logger.info("Loaded %d candidates from %s", len(candidates), candidates_path)

    # ─── Fetch account state ─────────────────────────────────────────────────
    tradier = None
    if args.no_preview_api:
        account_value = args.account_value_override or 100_000.0
        positions = []
    else:
        token, account_id, sandbox = _load_env()
        tradier_config = TradierConfig(access_token=token, account_id=account_id, sandbox=sandbox)
        tradier = TradierClient(tradier_config)
        try:
            account_value = tradier.get_account_value()
            positions = tradier.get_positions()
            if args.account_value_override:
                account_value = args.account_value_override
                logger.info("Account value overridden to $%.2f", account_value)
        except TradierError as e:
            logger.error("Could not fetch account state: %s", e)
            tradier.close()
            return 1

    logger.info("Account value: $%.2f, open positions: %d", account_value, len(positions))

    # ─── Daily state for kill switch ─────────────────────────────────────────
    state_path = PROJECT_ROOT / "data" / "state" / "account_state.json"
    account_state = AccountState.load_or_init(state_path, current_equity=account_value)
    logger.info(
        "Account state: starting_equity=$%.2f, day P&L=%.2f%%",
        account_state.starting_equity, account_state.day_pnl_pct() * 100,
    )

    # ─── Strategy ────────────────────────────────────────────────────────────
    strategy = PutCreditSpreadStrategy(StrategyConfig())
    open_fingerprints = _fingerprints_from_positions(positions)
    if open_fingerprints:
        logger.info("Found %d position fingerprints to skip", len(open_fingerprints))
    strategy_result = strategy.build_orders(candidates, already_open_fingerprints=open_fingerprints)
    logger.info("Strategy produced %d raw orders", len(strategy_result.orders))

    # ─── Risk ────────────────────────────────────────────────────────────────
    risk_manager = RiskManager(RiskConfig())
    risk_result = risk_manager.filter_orders(
        orders=strategy_result.orders,
        account_value=account_value,
        current_positions=positions,
        today_pnl_pct=account_state.day_pnl_pct(),
    )
    logger.info(
        "Risk: %d accepted, %d rejected, kill_switch=%s",
        len(risk_result.accepted), len(risk_result.rejected), risk_result.kill_switch_active,
    )

    # ─── Preview ─────────────────────────────────────────────────────────────
    preview_responses: list[dict] = []
    if tradier is not None and risk_result.accepted:
        for i, sized in enumerate(risk_result.accepted, start=1):
            order = sized.order
            legs = [
                OptionLeg(order.short_put_occ, OrderSide.SELL_TO_OPEN, sized.contracts),
                OptionLeg(order.long_put_occ, OrderSide.BUY_TO_OPEN, sized.contracts),
            ]
            logger.info(
                "Previewing %d/%d: %s %s/%s × %d @ $%.2f",
                i, len(risk_result.accepted),
                order.symbol, order.short_strike, order.long_strike,
                sized.contracts, order.target_credit_per_contract,
            )
            try:
                response = tradier.place_multileg_order(
                    underlying=order.symbol, legs=legs,
                    order_type=OrderType.CREDIT,
                    price=order.target_credit_per_contract,
                    preview=True, tag=order.tag,
                )
                preview_responses.append({
                    "fingerprint": order.fingerprint, "symbol": order.symbol,
                    "contracts": sized.contracts,
                    "ok": response.get("status") == "ok",
                    "preview_status": response.get("status"),
                    "estimated_margin_change": response.get("margin_change"),
                    "raw": response,
                })
            except TradierError as e:
                logger.warning("Preview failed for %s: %s", order.symbol, e)
                preview_responses.append({
                    "fingerprint": order.fingerprint, "symbol": order.symbol,
                    "contracts": sized.contracts, "ok": False, "error": str(e),
                })

    if tradier is not None:
        tradier.close()

    # ─── Persist ─────────────────────────────────────────────────────────────
    out_path = PROJECT_ROOT / "data" / "cache" / f"orders_{date.today().isoformat()}.json"
    payload = {
        "run_timestamp_utc": strategy_result.run_timestamp_utc,
        "account_value": account_value,
        "account_state": {
            "date": account_state.date,
            "starting_equity": account_state.starting_equity,
            "last_seen_equity": account_state.last_seen_equity,
            "day_pnl_pct": account_state.day_pnl_pct(),
        },
        "risk": {
            "kill_switch_active": risk_result.kill_switch_active,
            "kill_switch_reason": risk_result.kill_switch_reason,
            "accepted_count": len(risk_result.accepted),
            "rejected_count": len(risk_result.rejected),
            "rejected": [
                {"symbol": r.symbol, "reason": r.reason, "detail": r.detail}
                for r in risk_result.rejected
            ],
        },
        "accepted_orders": [
            {
                "symbol": s.order.symbol,
                "expiration": s.order.expiration.isoformat(),
                "short_strike": s.order.short_strike,
                "long_strike": s.order.long_strike,
                "contracts": s.contracts,
                "short_put_occ": s.order.short_put_occ,
                "long_put_occ": s.order.long_put_occ,
                "target_credit_per_contract": s.order.target_credit_per_contract,
                "target_credit_total": s.order.target_credit_per_contract * s.contracts * 100,
                "max_loss_dollars": s.max_loss_dollars,
                "atm_iv": s.order.atm_iv,
                "fingerprint": s.order.fingerprint,
            }
            for s in risk_result.accepted
        ],
        "preview_responses": preview_responses,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str))
    logger.info("Saved to %s", out_path)

    # ─── Summary ─────────────────────────────────────────────────────────────
    print()
    print("=" * 78)
    print(f"  Account value:  ${account_value:,.2f}")
    print(f"  Day P&L:        {account_state.day_pnl_pct()*100:+.2f}%")
    print(f"  Open positions: {len(positions)}")
    print("=" * 78)
    print()

    if risk_result.kill_switch_active:
        print(f"  🛑 KILL SWITCH ACTIVE")
        print(f"     {risk_result.kill_switch_reason}")
        print()
        return 0

    print(f"  Strategy:    {len(strategy_result.orders)} raw orders from {len(candidates)} candidates")
    if strategy_result.skipped_existing:
        print(f"               (skipped {strategy_result.skipped_existing} as already-open)")
    print(f"  Risk:        {len(risk_result.accepted)} accepted, {len(risk_result.rejected)} rejected")
    print(f"  Risk budget: ${risk_result.risk_budget_per_trade:,.2f}/trade")
    print()

    if risk_result.rejected:
        reasons = Counter(r.reason for r in risk_result.rejected)
        print("  Rejections by reason:")
        for reason, count in reasons.most_common():
            print(f"    {reason}: {count}")
        print()
        print("  First few rejections (with detail):")
        for r in risk_result.rejected[:3]:
            print(f"    [{r.symbol}] {r.detail}")
        print()

    if not risk_result.accepted:
        print("  No orders accepted by risk layer.")
        return 0

    print("Accepted orders:")
    print(
        f"  {'Symbol':<7} {'Ctrs':>4} {'Short':>7} {'Long':>7} "
        f"{'Credit':>8} {'MaxLoss':>9} {'PreviewStatus':>14}"
    )
    print("  " + "-" * 64)
    by_fp = {r["fingerprint"]: r for r in preview_responses}
    total_max_loss = 0.0
    total_credit = 0.0
    for s in risk_result.accepted:
        resp = by_fp.get(s.order.fingerprint, {})
        if args.no_preview_api:
            status = "(offline)"
        elif resp.get("ok"):
            status = "ok"
        else:
            status = "ERROR"
        credit_total = s.order.target_credit_per_contract * s.contracts * 100
        print(
            f"  {s.order.symbol:<7} {s.contracts:>4} "
            f"{s.order.short_strike:>7.1f} {s.order.long_strike:>7.1f} "
            f"${credit_total:>6.0f} ${s.max_loss_dollars:>7.0f} "
            f"{status:>14}"
        )
        total_max_loss += s.max_loss_dollars
        total_credit += credit_total

    print("  " + "-" * 64)
    print(
        f"  {'TOTAL':<7} {sum(s.contracts for s in risk_result.accepted):>4} "
        f"{'':<7} {'':<7} ${total_credit:>6.0f} ${total_max_loss:>7.0f} "
        f"({total_max_loss/account_value*100:.1f}% of acct)"
    )
    print()
    print("NOTE: All orders were previewed only. No real positions were opened.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
