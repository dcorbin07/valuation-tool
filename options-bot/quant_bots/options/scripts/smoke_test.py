#!/usr/bin/env python3
"""
Smoke test for the Tradier broker layer.

What this does:
  1. Verifies your API token authenticates (calls /user/profile)
  2. Fetches account balances
  3. Gets a SPY quote
  4. Lists upcoming SPY option expirations
  5. Pulls the option chain for ~30-45 DTE
  6. PREVIEWS (does not place) a put credit spread order

Nothing here places a real order. The order placement step uses preview=True,
which asks Tradier to validate the order and return the estimated cost without
executing it.

Run from the project root:
    python scripts/smoke_test.py

Required environment variables (set in .env or your shell):
    TRADIER_TOKEN              - Sandbox or production token
    TRADIER_ACCOUNT_ID         - The account number (e.g. VA1234567)
    TRADIER_SANDBOX            - "true" (default) or "false"
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta

# Ensure we can import from the project root regardless of where this is run.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from broker import (  # noqa: E402
    OptionLeg,
    OptionType,
    OrderSide,
    OrderType,
    TradierClient,
    TradierConfig,
    TradierError,
    build_occ_symbol,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("smoke_test")


def _load_env() -> tuple[str, str, bool]:
    """Load credentials from environment, with .env file support if available."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    token = os.environ.get("TRADIER_TOKEN")
    account_id = os.environ.get("TRADIER_ACCOUNT_ID")
    sandbox_flag = os.environ.get("TRADIER_SANDBOX", "true").lower() != "false"

    if not token:
        sys.exit("ERROR: TRADIER_TOKEN environment variable is not set.")
    if not account_id:
        sys.exit("ERROR: TRADIER_ACCOUNT_ID environment variable is not set.")

    return token, account_id, sandbox_flag


def _section(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> int:
    token, account_id, sandbox = _load_env()
    config = TradierConfig(
        access_token=token,
        account_id=account_id,
        sandbox=sandbox,
    )

    _section(f"Tradier smoke test ({config.env_name})")
    print(f"Account: {account_id}")
    print(f"Base URL: {config.base_url}")

    with TradierClient(config) as client:
        # ─── 1. Auth check ────────────────────────────────────────────────
        _section("1. Verify authentication")
        try:
            profile = client.get_user_profile()
        except TradierError as e:
            print(f"FAILED: {e}")
            print("Check that your token is valid and the account is active.")
            return 1
        profile_data = profile.get("profile", {})
        name = profile_data.get("name", "<unknown>")
        print(f"OK — authenticated as {name}")

        # ─── 2. Balances ──────────────────────────────────────────────────
        _section("2. Account balances")
        try:
            balances = client.get_balances()
            equity = balances.get("total_equity", "?")
            cash = balances.get("total_cash", "?")
            buying_power = balances.get(
                "option_buying_power", balances.get("stock_buying_power", "?")
            )
            print(f"Total equity:        ${equity}")
            print(f"Total cash:          ${cash}")
            print(f"Buying power:        ${buying_power}")
        except TradierError as e:
            print(f"FAILED: {e}")
            return 1

        # ─── 3. SPY quote ─────────────────────────────────────────────────
        _section("3. SPY quote")
        try:
            spy = client.get_quote("SPY")
            print(
                f"SPY  last={spy.get('last')}  bid={spy.get('bid')}  "
                f"ask={spy.get('ask')}  vol={spy.get('volume')}"
            )
            spy_price = float(spy.get("last") or spy.get("close") or 0)
            if spy_price <= 0:
                print("ERROR: could not get SPY price; aborting later steps.")
                return 1
        except TradierError as e:
            print(f"FAILED: {e}")
            return 1

        # ─── 4. SPY expirations ───────────────────────────────────────────
        _section("4. SPY option expirations")
        try:
            expirations = client.get_option_expirations("SPY")
        except TradierError as e:
            print(f"FAILED: {e}")
            return 1

        # Pick an expiration in the 30-45 DTE window for our strategy.
        today = date.today()
        target_window = [
            e
            for e in expirations
            if 25 <= (e - today).days <= 50
        ]
        if not target_window:
            print(
                f"No SPY expirations in the 25-50 DTE window — got {len(expirations)} "
                f"total. Falling back to the nearest one >= 25 DTE."
            )
            target_window = [e for e in expirations if (e - today).days >= 25]

        if not target_window:
            print("ERROR: no usable expirations found.")
            return 1

        target_exp = target_window[0]
        print(
            f"Picked expiration {target_exp} "
            f"({(target_exp - today).days} DTE)"
        )

        # ─── 5. Option chain ──────────────────────────────────────────────
        _section("5. SPY option chain")
        try:
            chain = client.get_option_chain("SPY", target_exp, with_greeks=True)
        except TradierError as e:
            print(f"FAILED: {e}")
            return 1

        puts = [o for o in chain if o.get("option_type") == "put"]
        print(f"Got {len(chain)} contracts ({len(puts)} puts)")

        # Find a put roughly at 20 delta. Greeks come back inside a "greeks" sub-dict;
        # delta on a put is negative, so we work with the absolute value.
        target_delta = 0.20
        candidates = []
        for opt in puts:
            greeks = opt.get("greeks") or {}
            delta = greeks.get("delta")
            if delta is None:
                continue
            candidates.append((abs(abs(float(delta)) - target_delta), opt))
        if not candidates:
            print(
                "WARNING: no greeks in chain response. Sandbox occasionally "
                "omits greeks. Skipping order preview."
            )
            return 0

        candidates.sort(key=lambda t: t[0])
        short_put_opt = candidates[0][1]
        short_put_strike = float(short_put_opt["strike"])
        # Long leg: 5 strikes below for a $5-wide spread (SPY uses $1 strike intervals
        # near the money, so 5 indices = $5 width).
        long_put_strike = short_put_strike - 5.0

        print(
            f"Short put strike: {short_put_strike}  "
            f"(delta ~{short_put_opt.get('greeks', {}).get('delta')})"
        )
        print(f"Long put strike:  {long_put_strike}")

        # ─── 6. Preview a put credit spread order ─────────────────────────
        _section("6. PREVIEW put credit spread order (no actual placement)")
        short_put = build_occ_symbol("SPY", target_exp, OptionType.PUT, short_put_strike)
        long_put = build_occ_symbol("SPY", target_exp, OptionType.PUT, long_put_strike)
        print(f"Short put OCC: {short_put}")
        print(f"Long put OCC:  {long_put}")

        legs = [
            OptionLeg(short_put, OrderSide.SELL_TO_OPEN, 1),
            OptionLeg(long_put, OrderSide.BUY_TO_OPEN, 1),
        ]

        # Estimate a target net credit at the mid of the chain bids/asks.
        # For a real spread we'd compute this properly; here we use a stub
        # of $0.50 for the preview — Tradier will tell us if it's unrealistic.
        target_credit = 0.50

        try:
            preview = client.place_multileg_order(
                underlying="SPY",
                legs=legs,
                order_type=OrderType.CREDIT,
                price=target_credit,
                preview=True,
                tag="smoke-test",
            )
        except TradierError as e:
            print(f"FAILED: {e}")
            return 1

        print("Preview response:")
        for k, v in preview.items():
            print(f"  {k}: {v}")

        _section("ALL CHECKS PASSED")
        print("Auth, balances, quotes, chain, and order preview all working.")
        print("No real orders were placed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
