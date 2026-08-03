"""
The instrument basket for the trend-following bot.

Unlike the options bot — which screened ~1,150 stocks dynamically — a
trend-following / managed-futures strategy trades a SMALL, CURATED, FIXED basket
of liquid instruments spanning multiple asset classes. The diversification
across asset classes is the whole point: when one class trends hard (including
crashing), the bot rides it, and the classes don't all move together. That
cross-asset spread is what produces "crisis alpha" — the property that this bot
tends to do well exactly when a short-volatility strategy (your options bot)
does badly.

We use liquid US-listed ETFs as proxies for what a real managed-futures fund
would trade as futures. ETFs are accessible in a normal brokerage/paper account,
have no expiration to roll, and are simple to short. The tradeoff vs. real
futures is no leverage and slightly higher cost — fine for paper validation.

Why these four buckets:
  - EQUITY indices: the core risk asset. Trends strongly in both directions.
  - BONDS / rates: often move opposite equities; trend well around rate cycles.
  - COMMODITIES: low correlation to financial assets; strong secular trends.
  - CURRENCIES (via USD proxies): another low-correlation trend source.

Each instrument is tagged with its asset class so the strategy/risk layers can
later cap exposure per class if desired (e.g. "no more than 40% net in equity").

This is intentionally a hand-maintained list, not a dynamic screen. ~25-35
liquid instruments is the sweet spot for trend-following — enough to diversify,
few enough that each gets meaningful capital and the signals stay clean.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AssetClass(Enum):
    EQUITY = "equity"
    BOND = "bond"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    REAL_ESTATE = "real_estate"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    asset_class: AssetClass
    # Can this be shorted in a typical account? A few (e.g. some commodity
    # ETFs) are awkward to short; we can still go long/flat on those.
    shortable: bool = True


# ─── The basket ─────────────────────────────────────────────────────────────
# Curated for liquidity (all trade millions of shares/day) and cross-asset
# coverage. Update deliberately, not dynamically.

TREND_BASKET: list[Instrument] = [
    # ── Equity indices (US + international) ──
    Instrument("SPY", "S&P 500", AssetClass.EQUITY),
    Instrument("QQQ", "Nasdaq 100", AssetClass.EQUITY),
    Instrument("IWM", "Russell 2000 small-cap", AssetClass.EQUITY),
    Instrument("EFA", "Developed ex-US equity", AssetClass.EQUITY),
    Instrument("EEM", "Emerging markets equity", AssetClass.EQUITY),
    Instrument("VGK", "Europe equity", AssetClass.EQUITY),
    Instrument("EWJ", "Japan equity", AssetClass.EQUITY),

    # ── Bonds / rates ──
    Instrument("TLT", "20+yr US Treasuries", AssetClass.BOND),
    Instrument("IEF", "7-10yr US Treasuries", AssetClass.BOND),
    Instrument("SHY", "1-3yr US Treasuries", AssetClass.BOND),
    Instrument("LQD", "Investment-grade corp bonds", AssetClass.BOND),
    Instrument("HYG", "High-yield corp bonds", AssetClass.BOND),
    Instrument("TIP", "TIPS (inflation-protected)", AssetClass.BOND),

    # ── Commodities ──
    Instrument("GLD", "Gold", AssetClass.COMMODITY),
    Instrument("SLV", "Silver", AssetClass.COMMODITY),
    Instrument("USO", "Crude oil", AssetClass.COMMODITY),
    Instrument("UNG", "Natural gas", AssetClass.COMMODITY),
    Instrument("DBC", "Broad commodity basket", AssetClass.COMMODITY),
    Instrument("DBA", "Agriculture", AssetClass.COMMODITY),
    Instrument("CPER", "Copper", AssetClass.COMMODITY),

    # ── Currencies (USD strength/weakness + majors) ──
    Instrument("UUP", "US Dollar bullish", AssetClass.CURRENCY),
    Instrument("FXE", "Euro", AssetClass.CURRENCY),
    Instrument("FXY", "Japanese yen", AssetClass.CURRENCY),
    Instrument("FXB", "British pound", AssetClass.CURRENCY),

    # ── Real estate (distinct trend behavior, rate-sensitive) ──
    Instrument("VNQ", "US REITs", AssetClass.REAL_ESTATE),
]


def get_basket() -> list[Instrument]:
    """Return the trend-following instrument basket."""
    return list(TREND_BASKET)


def get_symbols() -> list[str]:
    """Just the tickers — convenient for batch quote/history calls."""
    return [i.symbol for i in TREND_BASKET]


def by_asset_class() -> dict[AssetClass, list[Instrument]]:
    """Group the basket by asset class (for per-class exposure caps later)."""
    out: dict[AssetClass, list[Instrument]] = {}
    for inst in TREND_BASKET:
        out.setdefault(inst.asset_class, []).append(inst)
    return out


def lookup(symbol: str) -> Instrument | None:
    """Find an instrument by ticker (case-insensitive)."""
    s = symbol.upper()
    for inst in TREND_BASKET:
        if inst.symbol == s:
            return inst
    return None
