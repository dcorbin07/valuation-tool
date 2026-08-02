"""
Tradier brokerage API client.

Supports both sandbox (paper trading) and production environments. Defaults to
sandbox; you must explicitly opt into production with `sandbox=False`.

This client is intentionally thin — it wraps Tradier's REST endpoints with proper
error handling, rate limiting, and Pythonic argument types. Strategy logic,
position sizing, and risk management live in higher-level modules that consume
this client.

Reference: https://documentation.tradier.com/brokerage-api
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Optional

import requests

from .occ_symbol import OptionType, build_occ_symbol, parse_occ_symbol

logger = logging.getLogger(__name__)


# ─── Exceptions ─────────────────────────────────────────────────────────────


class TradierError(Exception):
    """Base exception for all Tradier client errors."""


class TradierAuthError(TradierError):
    """Authentication failed (401 from Tradier)."""


class TradierRateLimitError(TradierError):
    """Rate limit exceeded (429 from Tradier)."""


class TradierAPIError(TradierError):
    """Generic API error (4xx/5xx other than 401/429)."""

    def __init__(self, status_code: int, message: str, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"Tradier API error {status_code}: {message}")


# ─── Enums ──────────────────────────────────────────────────────────────────


class OrderSide(Enum):
    """Tradier order sides for options."""

    BUY_TO_OPEN = "buy_to_open"
    SELL_TO_OPEN = "sell_to_open"
    BUY_TO_CLOSE = "buy_to_close"
    SELL_TO_CLOSE = "sell_to_close"


class EquitySide(Enum):
    """Tradier order sides for equities/ETFs (single-leg, directional)."""

    BUY = "buy"               # open or add to a long
    SELL = "sell"             # close or reduce a long
    SELL_SHORT = "sell_short"  # open or add to a short (needs margin account)
    BUY_TO_COVER = "buy_to_cover"  # close or reduce a short


class OrderType(Enum):
    """Tradier order types. For multi-leg, prefer CREDIT/DEBIT/EVEN over MARKET."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    DEBIT = "debit"
    CREDIT = "credit"
    EVEN = "even"


class OrderDuration(Enum):
    DAY = "day"
    GTC = "gtc"
    PRE = "pre"
    POST = "post"


# ─── Data classes ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class OptionLeg:
    """
    A single leg of a multi-leg options order.

    `option_symbol` is the OCC symbol (e.g. "SPY251017P00565000"). Use
    `OptionLeg.from_components()` if you have strike/expiry/type and want to
    construct it without manually building the symbol.
    """

    option_symbol: str
    side: OrderSide
    quantity: int

    @classmethod
    def from_components(
        cls,
        underlying: str,
        expiration: date,
        option_type: OptionType,
        strike: float,
        side: OrderSide,
        quantity: int,
    ) -> "OptionLeg":
        return cls(
            option_symbol=build_occ_symbol(underlying, expiration, option_type, strike),
            side=side,
            quantity=quantity,
        )


@dataclass
class TradierConfig:
    """
    Configuration for a Tradier API client.

    Sandbox is the default and recommended setting during development. Switching
    to production (sandbox=False) means orders go to a real funded account and
    move real money. Do not flip this lightly.
    """

    access_token: str
    account_id: str
    sandbox: bool = True

    @property
    def base_url(self) -> str:
        return (
            "https://sandbox.tradier.com/v1"
            if self.sandbox
            else "https://api.tradier.com/v1"
        )

    @property
    def env_name(self) -> str:
        return "sandbox" if self.sandbox else "production"


# ─── Client ─────────────────────────────────────────────────────────────────


def _normalize_list(payload: Any, key: str) -> list[dict]:
    """
    Tradier responses are inconsistent: collections come back as `null` (string),
    a single dict, or a list. This helper normalizes to always-a-list.
    """
    if not payload or payload == "null":
        return []
    inner = payload.get(key) if isinstance(payload, dict) else None
    if not inner or inner == "null":
        return []
    if isinstance(inner, dict):
        return [inner]
    if isinstance(inner, list):
        return inner
    return []


class TradierClient:
    """
    Thin client for Tradier REST API.

    Usage:
        cfg = TradierConfig(
            access_token=os.environ["TRADIER_TOKEN"],
            account_id=os.environ["TRADIER_ACCOUNT_ID"],
            sandbox=True,
        )
        client = TradierClient(cfg)
        account_value = client.get_account_value()

    Safety: order placement defaults to `preview=True`, which validates the
    order with Tradier (returning estimated cost, margin impact, and warnings)
    without actually placing it. You must explicitly pass `preview=False` to
    place a live order.
    """

    # Tradier's documented rate limits are ~60-120 requests/minute depending on
    # endpoint type. We keep a small inter-request floor as a courtesy.
    _MIN_REQUEST_INTERVAL_SECS = 0.1

    def __init__(self, config: TradierConfig, timeout_secs: float = 10.0):
        self.config = config
        self.timeout_secs = timeout_secs
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {config.access_token}",
                "Accept": "application/json",
            }
        )
        self._last_request_monotonic: float = 0.0
        logger.info(
            "TradierClient initialized for account=%s env=%s",
            config.account_id,
            config.env_name,
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "TradierClient":
        return self

    def __exit__(self, *_args: Any) -> None:
        self.close()

    # ─── Internal request handling ───────────────────────────────────────────

    def _rate_limit_pause(self) -> None:
        elapsed = time.monotonic() - self._last_request_monotonic
        if elapsed < self._MIN_REQUEST_INTERVAL_SECS:
            time.sleep(self._MIN_REQUEST_INTERVAL_SECS - elapsed)
        self._last_request_monotonic = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> dict:
        self._rate_limit_pause()
        url = f"{self.config.base_url}{path}"
        logger.debug("Tradier %s %s params=%s data=%s", method, path, params, data)

        try:
            response = self._session.request(
                method,
                url,
                params=params,
                data=data,
                timeout=self.timeout_secs,
            )
        except requests.RequestException as e:
            raise TradierError(f"Network error calling {method} {path}: {e}") from e

        if response.status_code == 401:
            raise TradierAuthError(
                "Authentication failed — check TRADIER_TOKEN is valid and active."
            )
        if response.status_code == 429:
            raise TradierRateLimitError(
                "Rate limit exceeded. Slow down request rate or wait."
            )
        if response.status_code >= 400:
            body = response.text[:500] if response.text else ""
            raise TradierAPIError(response.status_code, response.reason, body)

        try:
            return response.json()
        except ValueError as e:
            raise TradierAPIError(
                response.status_code,
                "Response was not valid JSON",
                response.text[:500],
            ) from e

    # ─── Account & profile ───────────────────────────────────────────────────

    def get_user_profile(self) -> dict:
        """Return user profile and the list of accounts attached to this token."""
        return self._request("GET", "/user/profile")

    def get_balances(self) -> dict:
        """
        Return the balances dict for the configured account.

        Key fields: total_equity, total_cash, option_buying_power,
        stock_buying_power, market_value, account_number.
        """
        result = self._request(
            "GET", f"/accounts/{self.config.account_id}/balances"
        )
        return result.get("balances", {}) or {}

    def get_account_value(self) -> float:
        """Total account equity as a float. Uses get_balances() under the hood."""
        balances = self.get_balances()
        # total_equity is the canonical "everything" value
        value = balances.get("total_equity")
        if value is None:
            raise TradierAPIError(
                0, "balances response did not include total_equity", str(balances)
            )
        return float(value)

    # ─── Positions ───────────────────────────────────────────────────────────

    def get_positions(self) -> list[dict]:
        """Return current open positions for the configured account."""
        result = self._request(
            "GET", f"/accounts/{self.config.account_id}/positions"
        )
        return _normalize_list(result.get("positions"), "position")

    # ─── Orders ──────────────────────────────────────────────────────────────

    def get_orders(self, include_tags: bool = False) -> list[dict]:
        """Return the order history (open + recent closed) for the account."""
        params = {"includeTags": "true"} if include_tags else None
        result = self._request(
            "GET",
            f"/accounts/{self.config.account_id}/orders",
            params=params,
        )
        return _normalize_list(result.get("orders"), "order")

    def get_order(self, order_id: int) -> dict:
        """Get a single order by ID."""
        result = self._request(
            "GET",
            f"/accounts/{self.config.account_id}/orders/{order_id}",
        )
        return result.get("order", {}) or {}

    # Terminal order states — once an order reaches one of these it won't change.
    TERMINAL_ORDER_STATES = frozenset({
        "filled", "canceled", "cancelled", "rejected", "expired", "error",
    })

    def wait_for_fill(
        self,
        order_id: int,
        max_wait_secs: float = 30.0,
        poll_interval_secs: float = 3.0,
    ) -> dict:
        """
        Poll an order until it reaches a terminal state or the timeout elapses.

        Returns the final order dict. Check the 'status' field:
          - 'filled'   -> fully filled
          - 'partially_filled' (non-terminal; may still be working at timeout)
          - 'open' / 'pending' -> still working when we gave up waiting
          - 'canceled' / 'rejected' / 'expired' -> didn't fill

        This never raises on a still-working order; it just returns whatever
        state the order is in at timeout. The caller decides what to do
        (the manage job will reconcile against actual positions regardless).
        """
        import time as _time
        deadline = _time.monotonic() + max_wait_secs
        order: dict = {}
        while _time.monotonic() < deadline:
            try:
                order = self.get_order(order_id)
            except TradierError as e:
                logger.warning("wait_for_fill: get_order(%s) failed: %s", order_id, e)
                return {"id": order_id, "status": "unknown", "error": str(e)}
            status = (order.get("status") or "").lower()
            if status in self.TERMINAL_ORDER_STATES:
                return order
            _time.sleep(poll_interval_secs)
        # Timed out still non-terminal
        return order or {"id": order_id, "status": "timeout"}

    def cancel_order(self, order_id: int) -> dict:
        """Cancel an open order by ID."""
        return self._request(
            "DELETE",
            f"/accounts/{self.config.account_id}/orders/{order_id}",
        )

    # ─── Multi-leg order placement ───────────────────────────────────────────

    def place_equity_order(
        self,
        symbol: str,
        side: "EquitySide",
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        price: Optional[float] = None,
        duration: OrderDuration = OrderDuration.DAY,
        preview: bool = True,
        tag: Optional[str] = None,
    ) -> dict:
        """
        Place a single-leg equity/ETF order. This is the path the trend-following
        and momentum bots use — they trade instruments directly, not options.

        For a long entry:
            client.place_equity_order("SPY", EquitySide.BUY, 100,
                                       order_type=OrderType.MARKET, preview=True)

        For a short entry (requires a margin account):
            client.place_equity_order("TLT", EquitySide.SELL_SHORT, 50,
                                       order_type=OrderType.MARKET, preview=True)

        Args:
            symbol: Equity/ETF ticker (e.g. "SPY").
            side: BUY / SELL / SELL_SHORT / BUY_TO_COVER.
            quantity: Number of shares (whole shares; Tradier doesn't do
                fractional via this endpoint).
            order_type: MARKET or LIMIT. MARKET is acceptable for liquid ETFs
                (unlike options, where we always avoid it). LIMIT requires price.
            price: Limit price; required for LIMIT orders.
            duration: DAY (default) or GTC.
            preview: If True (default), validate without placing.
            tag: Optional client-side identifier (alphanumeric, max 255 chars).

        Returns:
            Order response dict. Preview includes cost/commission/margin/warnings;
            live includes the order id and status.
        """
        if quantity <= 0:
            raise ValueError(f"quantity must be positive, got {quantity}")
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("LIMIT order requires a price")
        if price is not None and price < 0:
            raise ValueError(f"price must be non-negative, got {price}")

        data: dict[str, str] = {
            "class": "equity",
            "symbol": symbol.upper(),
            "side": side.value,
            "quantity": str(int(quantity)),
            "type": order_type.value,
            "duration": duration.value,
        }
        if price is not None:
            data["price"] = f"{price:.2f}"
        if tag:
            data["tag"] = tag
        if preview:
            data["preview"] = "true"

        logger.info(
            "Placing equity order: %s %s %d @ %s (preview=%s, env=%s)",
            side.value, symbol.upper(), int(quantity),
            f"{price:.2f}" if price is not None else "market",
            preview, self.config.env_name,
        )

        result = self._request(
            "POST",
            f"/accounts/{self.config.account_id}/orders",
            data=data,
        )
        return result.get("order", {}) or {}

    def place_multileg_order(
        self,
        underlying: str,
        legs: list[OptionLeg],
        order_type: OrderType,
        price: Optional[float] = None,
        duration: OrderDuration = OrderDuration.DAY,
        preview: bool = True,
        tag: Optional[str] = None,
    ) -> dict:
        """
        Place a multi-leg options order (2-4 legs). This is the path we use for
        put credit spreads, iron condors, and any other defined-risk strategy.

        For a put credit spread you would:
            legs = [
                OptionLeg(short_put_occ, OrderSide.SELL_TO_OPEN, qty),
                OptionLeg(long_put_occ,  OrderSide.BUY_TO_OPEN,  qty),
            ]
            client.place_multileg_order(
                "SPY", legs,
                order_type=OrderType.CREDIT,
                price=0.85,            # the net credit you want to receive
                preview=True,          # validate without placing
            )

        Args:
            underlying: Underlying symbol (e.g. "SPY"). Tradier requires this
                even though leg OCC symbols already encode it.
            legs: Between 2 and 4 OptionLeg objects.
            order_type: For credit spreads use CREDIT; for debit spreads use
                DEBIT. EVEN for zero-cost. Avoid MARKET for multi-leg — slippage
                across legs will eat any edge.
            price: Net price for the spread. Required for CREDIT/DEBIT/LIMIT.
                For CREDIT this is the minimum credit you'll accept; Tradier
                fills only at this price or better.
            duration: DAY, GTC, etc.
            preview: If True (default), Tradier validates the order and returns
                cost/margin/warnings WITHOUT placing it. Always preview first.
            tag: Optional client-side identifier (alphanumeric, max 255 chars).

        Returns:
            Order response dict. In preview mode includes estimated cost,
            commission, margin_change, and any warnings. In live mode includes
            the order id and initial status.
        """
        if not 2 <= len(legs) <= 4:
            raise ValueError(
                f"Multi-leg order requires 2-4 legs, got {len(legs)}"
            )

        if order_type in (OrderType.CREDIT, OrderType.DEBIT, OrderType.LIMIT):
            if price is None:
                raise ValueError(f"{order_type.value} order requires a price")
            if price < 0:
                raise ValueError(f"price must be non-negative, got {price}")

        # Sanity check that all legs share the same underlying and expiration.
        # Tradier enforces this server-side too, but failing locally gives a
        # clearer error and avoids a wasted API call.
        contracts = [parse_occ_symbol(leg.option_symbol) for leg in legs]
        underlyings = {c.underlying for c in contracts}
        if len(underlyings) > 1:
            raise ValueError(
                f"All legs must share the same underlying, got {underlyings}"
            )
        if contracts[0].underlying.upper() != underlying.upper():
            raise ValueError(
                f"Legs reference {contracts[0].underlying} but `underlying` "
                f"argument is {underlying}"
            )

        data: dict[str, str] = {
            "class": "multileg",
            "symbol": underlying.upper(),
            "type": order_type.value,
            "duration": duration.value,
        }
        if price is not None:
            data["price"] = f"{price:.2f}"
        if tag:
            data["tag"] = tag
        if preview:
            data["preview"] = "true"

        for i, leg in enumerate(legs):
            data[f"option_symbol[{i}]"] = leg.option_symbol
            data[f"side[{i}]"] = leg.side.value
            data[f"quantity[{i}]"] = str(leg.quantity)

        logger.info(
            "Placing multi-leg order: %s %d legs %s @ %s (preview=%s, env=%s)",
            underlying.upper(),
            len(legs),
            order_type.value,
            f"{price:.2f}" if price is not None else "—",
            preview,
            self.config.env_name,
        )

        result = self._request(
            "POST",
            f"/accounts/{self.config.account_id}/orders",
            data=data,
        )
        return result.get("order", {}) or {}

    # ─── Market data ─────────────────────────────────────────────────────────

    def get_quote(self, symbol: str) -> dict:
        """Get a single quote. Returns last, bid, ask, volume, etc."""
        quotes = self.get_quotes([symbol])
        return quotes[0] if quotes else {}

    def get_quotes(self, symbols: list[str]) -> list[dict]:
        """Batch-fetch quotes. Tradier supports up to ~50 symbols per call."""
        if not symbols:
            return []
        params = {"symbols": ",".join(symbols), "greeks": "false"}
        result = self._request("GET", "/markets/quotes", params=params)
        return _normalize_list(result.get("quotes"), "quote")

    def get_option_expirations(
        self,
        symbol: str,
        include_all_roots: bool = True,
    ) -> list[date]:
        """
        Get list of available option expiration dates for a symbol.
        """
        params = {"symbol": symbol}
        if include_all_roots:
            params["includeAllRoots"] = "true"
        result = self._request("GET", "/markets/options/expirations", params=params)
        expirations = result.get("expirations")
        if not expirations or expirations == "null":
            return []
        date_strs = expirations.get("date", [])
        if isinstance(date_strs, str):
            date_strs = [date_strs]
        return [date.fromisoformat(d) for d in date_strs]

    def get_option_chain(
        self,
        symbol: str,
        expiration: date,
        with_greeks: bool = True,
    ) -> list[dict]:
        """
        Get the full option chain for a symbol/expiration.

        Each option dict contains: symbol (OCC), strike, bid, ask, last, volume,
        open_interest, option_type, expiration_date, and (if with_greeks) a
        greeks sub-dict with delta, gamma, theta, vega, mid_iv, etc.

        For our strategy, delta is what we use to pick strikes.
        """
        params = {
            "symbol": symbol,
            "expiration": expiration.isoformat(),
            "greeks": "true" if with_greeks else "false",
        }
        result = self._request("GET", "/markets/options/chains", params=params)
        return _normalize_list(result.get("options"), "option")

    def get_history(
        self,
        symbol: str,
        start: date,
        end: date,
        interval: str = "daily",
    ) -> list[dict]:
        """
        Historical OHLC bars for a symbol.

        interval: 'daily' | 'weekly' | 'monthly'. (Intraday intervals exist but
        require a different endpoint; not exposed here.)
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        result = self._request("GET", "/markets/history", params=params)
        history = result.get("history")
        if not history or history == "null":
            return []
        days = history.get("day", [])
        if isinstance(days, dict):
            return [days]
        return days

    def get_clock(self) -> dict:
        """
        Current market clock: state ('open' | 'closed' | 'premarket' |
        'postmarket'), description, next_change, next_state.
        """
        result = self._request("GET", "/markets/clock")
        return result.get("clock", {}) or {}
