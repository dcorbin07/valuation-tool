"""
OCC option symbol construction and parsing.

The OCC (Options Clearing Corporation) symbol is the standard option identifier
used by US brokerages, including Tradier. Format:

    <UNDERLYING><YYMMDD><C|P><STRIKE_x1000_8DIGITS>

Examples:
    AAPL251017C00255000  -> AAPL, 2025-10-17, Call, $255.00 strike
    SPY250620P00565000   -> SPY,  2025-06-20, Put,  $565.00 strike
    SPY250620P00565500   -> SPY,  2025-06-20, Put,  $565.50 strike (fractional)

The previous bot built up trades by passing strike, expiry, and option_type as
separate fields to the order endpoint. That is not how Tradier's API works —
options are identified by the OCC symbol string. Getting this wrong means every
order is rejected.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class OptionType(Enum):
    CALL = "C"
    PUT = "P"


@dataclass(frozen=True)
class OptionContract:
    """Parsed components of an OCC option symbol."""
    underlying: str
    expiration: date
    option_type: OptionType
    strike: float


def build_occ_symbol(
    underlying: str,
    expiration: date,
    option_type: OptionType,
    strike: float,
) -> str:
    """
    Construct an OCC-format option symbol string.

    Args:
        underlying: Stock ticker (e.g. "AAPL"). Case-insensitive; will be uppercased.
        expiration: Expiration date.
        option_type: OptionType.CALL or OptionType.PUT.
        strike: Strike price in dollars (e.g. 255.0 or 255.50).

    Returns:
        OCC symbol like "AAPL251017C00255000".

    Raises:
        ValueError: If inputs are invalid (empty underlying, non-positive strike,
                    strike too high, etc.).
    """
    if not underlying:
        raise ValueError("Underlying must not be empty")

    if strike <= 0:
        raise ValueError(f"Strike must be positive, got {strike}")

    if expiration < date(2000, 1, 1):
        raise ValueError(
            f"Expiration before year 2000 cannot be encoded in YYMMDD: {expiration}"
        )
    if expiration > date(2099, 12, 31):
        raise ValueError(
            f"Expiration after 2099 cannot be encoded in YYMMDD: {expiration}"
        )

    yymmdd = expiration.strftime("%y%m%d")
    type_char = option_type.value

    # Strike is encoded as price * 1000 in 8 zero-padded digits.
    # We round to nearest tenth of a cent (1e-4) before scaling, since OCC strikes
    # are at most 3 decimal places in practice.
    strike_int = round(strike * 1000)
    if strike_int <= 0:
        raise ValueError(f"Strike rounds to zero or below: {strike}")
    if strike_int >= 10**8:
        raise ValueError(
            f"Strike too high to encode in 8 digits (>=$100,000): {strike}"
        )

    strike_str = f"{strike_int:08d}"
    return f"{underlying.upper()}{yymmdd}{type_char}{strike_str}"


def parse_occ_symbol(symbol: str) -> OptionContract:
    """
    Parse an OCC-format option symbol back into its components.

    The fixed-width suffix (15 chars: 6 date + 1 type + 8 strike) is stripped
    from the right, and whatever remains is the underlying. This handles
    underlyings of any length (1 char like "F" up to longer adjusted symbols).

    Args:
        symbol: OCC symbol like "AAPL251017C00255000".

    Returns:
        OptionContract with underlying, expiration, option_type, strike fields.

    Raises:
        ValueError: If the symbol is malformed.
    """
    # Minimum length: 1 char underlying + 6 date + 1 type + 8 strike = 16
    if len(symbol) < 16:
        raise ValueError(f"OCC symbol too short ({len(symbol)} < 16): {symbol!r}")

    strike_str = symbol[-8:]
    type_char = symbol[-9]
    yymmdd = symbol[-15:-9]
    underlying = symbol[:-15]

    if not underlying:
        raise ValueError(f"OCC symbol has empty underlying: {symbol!r}")

    if type_char == "C":
        option_type = OptionType.CALL
    elif type_char == "P":
        option_type = OptionType.PUT
    else:
        raise ValueError(f"Invalid option type char {type_char!r} in {symbol!r}")

    try:
        year = 2000 + int(yymmdd[:2])
        month = int(yymmdd[2:4])
        day = int(yymmdd[4:6])
        expiration = date(year, month, day)
    except ValueError as e:
        raise ValueError(f"Invalid expiration {yymmdd!r} in {symbol!r}: {e}") from e

    try:
        strike_int = int(strike_str)
    except ValueError as e:
        raise ValueError(f"Invalid strike {strike_str!r} in {symbol!r}: {e}") from e

    if strike_int <= 0:
        raise ValueError(f"Strike must be positive in {symbol!r}, got {strike_int}")

    strike = strike_int / 1000

    return OptionContract(
        underlying=underlying,
        expiration=expiration,
        option_type=option_type,
        strike=strike,
    )
