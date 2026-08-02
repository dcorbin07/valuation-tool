"""
Point-in-time universe construction — the actual survivorship-bias fix.

WHAT WAS WRONG WITH THE OLD ONE
───────────────────────────────
`core/universe_builder.py` calls a live Nasdaq screener endpoint and has no
as-of concept at all — `build()` takes no arguments. A backtest of 2021-2024
therefore traded, on every single day of that window:

    the 150 largest companies AS OF TODAY,
    filtered on TODAY's price >= $20 and TODAY's market cap >= $2B,
    sorted by TODAY's market cap.

Three biases stack, and the third is the killer:

  1. SURVIVORSHIP — anything delisted, acquired or bankrupted over the window
     is structurally absent. The losers were deleted from history.
  2. QUOTE-DROP — `_enrich_with_quotes` silently drops any ticker that fails to
     return a quote, which correlates with being troubled.
  3. LOOK-AHEAD SELECTION — you pre-selected the winners of the very period you
     are measuring. For a momentum strategy this is close to fatal; the result
     is not a mild overstatement, it is an artefact.

This module replaces all three. It reconstructs the universe as it ACTUALLY
was on a historical date, delisted names included.

THE FIELDS YOU MUST NOT FILTER ON
─────────────────────────────────
`TICKERS.scalemarketcap` and `scalerevenue` are tempting — buckets 1-6 from
Nano to Mega, already computed. They are based on the MAXIMUM OBSERVED value
over the issuer's entire life. Filtering on them leaks look-ahead into a
universe you believe is clean: a company that became a mega-cap in 2024 is
labelled mega-cap in 2005. Use `DAILY.marketcap` as of the date instead. This
module does, and refuses to offer the other.

WHY `isdelisted` IS NOT FILTERED
────────────────────────────────
Keeping the delisted rows is the entire point. A ticker is in the universe on
date D if D falls inside its [firstpricedate, lastpricedate] window — which
naturally includes companies that were alive then and are dead now, and
naturally excludes companies that had not yet listed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .sharadar import SharadarStore

logger = logging.getLogger(__name__)

# Categories that are ordinary US common equity. Anything else — preferred,
# warrants, units, SPACs ("Blank Checks"), ADRs, Canadian issuers — is excluded
# by default because the strategies assume ordinary common stock.
#
# NOTE: this list is best-effort from published documentation. Sharadar has
# never published an exhaustive enumeration. scripts/verify_sharadar.py runs a
# SELECT DISTINCT against your actual data and reports anything unrecognised,
# so an unexpected value shows up as a warning rather than silently shrinking
# your universe.
DOMESTIC_COMMON = (
    "Domestic Common Stock",
    "Domestic Common Stock Primary Class",
    "Domestic Common Stock Secondary Class",
)

ADR_COMMON = (
    "ADR Common Stock",
    "ADR Common Stock Primary Class",
    "ADR Common Stock Secondary Class",
)


@dataclass(frozen=True)
class PITUniverseConfig:
    min_price: float = 20.0            # matches the live UniverseConfig
    min_market_cap: float = 2_000_000_000.0
    min_avg_dollar_volume: float = 0.0     # 0 disables; see min_avg_volume
    min_avg_volume: float = 500_000.0
    volume_lookback_days: int = 30
    exchanges: tuple = ("NASDAQ", "NYSE", "NYSEARCA", "BATS", "NYSEMKT")
    include_adrs: bool = False
    max_names: Optional[int] = None    # cap AFTER filtering, by market cap desc
    # Deliberately absent: any filter on scalemarketcap / scalerevenue.
    # See the module docstring — those leak look-ahead.


@dataclass
class PITTicker:
    symbol: str
    permaticker: Optional[str]
    name: Optional[str]
    exchange: Optional[str]
    sector: Optional[str]
    market_cap: Optional[float]
    price: Optional[float]
    avg_volume: Optional[float]
    is_delisted: bool
    last_price_date: Optional[str]


@dataclass
class PITSnapshot:
    as_of: date
    tickers: list[PITTicker] = field(default_factory=list)
    # Diagnostics. Every count here is a name that did NOT make the universe.
    # A silent universe is how you end up debugging a strategy when the real
    # problem is that the filter ate 90% of the candidates.
    rejected: dict = field(default_factory=dict)
    delisted_included: int = 0

    @property
    def count(self) -> int:
        return len(self.tickers)

    def symbols(self) -> list[str]:
        return [t.symbol for t in self.tickers]


class PITUniverseBuilder:
    """
    Reconstruct the tradable universe as of a historical date.

    All data comes from the local Sharadar mirror — no network, so a backtest
    over 750 rebalance dates does 750 index seeks rather than 750 HTTP calls.
    """

    def __init__(self, store: SharadarStore, config: Optional[PITUniverseConfig] = None):
        self.store = store
        self.config = config or PITUniverseConfig()

    def build(self, as_of: date) -> PITSnapshot:
        cfg = self.config
        snap = PITSnapshot(as_of=as_of)
        rejected = {"not_listed": 0, "category": 0, "exchange": 0,
                    "no_price": 0, "price": 0, "no_cap": 0, "cap": 0, "volume": 0}

        allowed = list(DOMESTIC_COMMON) + (list(ADR_COMMON) if cfg.include_adrs else [])
        iso = as_of.isoformat()

        # Listed-on-that-date window. This single predicate is what makes the
        # result survivorship-free: a company delisted in 2019 IS in a 2017
        # universe, and a company that IPO'd in 2021 is NOT.
        rows = self.store.db.execute(
            "SELECT ticker, permaticker, name, exchange, sector, category, "
            "       isdelisted, firstpricedate, lastpricedate "
            "FROM tickers WHERE tbl='SEP' "
            "  AND firstpricedate IS NOT NULL AND firstpricedate <= ? "
            "  AND (lastpricedate IS NULL OR lastpricedate = '' OR lastpricedate >= ?)",
            (iso, iso)).fetchall()

        unknown_categories: set[str] = set()
        candidates = []
        for r in rows:
            cat = (r["category"] or "").strip()
            if cat and cat not in DOMESTIC_COMMON and cat not in ADR_COMMON:
                unknown_categories.add(cat)
            if cat not in allowed:
                rejected["category"] += 1
                continue
            if cfg.exchanges and (r["exchange"] or "") not in cfg.exchanges:
                rejected["exchange"] += 1
                continue
            candidates.append(r)

        if unknown_categories:
            logger.info(
                "PIT universe: %d category value(s) not in the known list and "
                "therefore excluded — verify these are genuinely not common "
                "equity: %s", len(unknown_categories), sorted(unknown_categories)[:12])

        for r in candidates:
            sym = r["ticker"]

            # Price LEVEL must be unadjusted. closeadj is back-adjusted, so a
            # stock that later split 4:1 would look like it traded at a quarter
            # of its real price and would fail a $20 screen it actually passed.
            px = self.store.price_on(sym, as_of, adjusted=False)
            if px is None:
                rejected["no_price"] += 1
                continue
            if px < cfg.min_price:
                rejected["price"] += 1
                continue

            cap = self.store.marketcap_on(sym, as_of)
            if cap is None:
                rejected["no_cap"] += 1
                continue
            if cap < cfg.min_market_cap:
                rejected["cap"] += 1
                continue

            avg_vol = self._avg_volume(sym, as_of, cfg.volume_lookback_days)
            if cfg.min_avg_volume and (avg_vol is None or avg_vol < cfg.min_avg_volume):
                rejected["volume"] += 1
                continue
            if cfg.min_avg_dollar_volume:
                if avg_vol is None or avg_vol * px < cfg.min_avg_dollar_volume:
                    rejected["volume"] += 1
                    continue

            delisted = (r["isdelisted"] or "N").upper() == "Y"
            if delisted:
                snap.delisted_included += 1

            snap.tickers.append(PITTicker(
                symbol=sym, permaticker=r["permaticker"], name=r["name"],
                exchange=r["exchange"], sector=r["sector"], market_cap=cap,
                price=px, avg_volume=avg_vol, is_delisted=delisted,
                last_price_date=r["lastpricedate"],
            ))

        snap.tickers.sort(key=lambda t: (t.market_cap or 0), reverse=True)
        if cfg.max_names:
            dropped = max(0, len(snap.tickers) - cfg.max_names)
            if dropped:
                logger.info("PIT universe: capped at %d names, dropped %d smaller",
                            cfg.max_names, dropped)
            snap.tickers = snap.tickers[: cfg.max_names]

        snap.rejected = rejected
        logger.info(
            "PIT universe @ %s: %d names (%d already-delisted-by-today, i.e. "
            "exactly the names a live screener would have hidden from you). "
            "Rejected: %s", as_of, snap.count, snap.delisted_included,
            ", ".join(f"{k}={v}" for k, v in rejected.items() if v))
        return snap

    def _avg_volume(self, ticker: str, as_of: date, lookback: int) -> Optional[float]:
        row = self.store.db.execute(
            "SELECT AVG(volume) v FROM (SELECT volume FROM sep WHERE ticker=? "
            "AND date<=? AND volume IS NOT NULL ORDER BY date DESC LIMIT ?)",
            (ticker, as_of.isoformat(), lookback)).fetchone()
        return row["v"] if row and row["v"] else None

    # ── diagnostics ────────────────────────────────────────────────────────

    def survivorship_report(self, as_of: date) -> dict:
        """
        Quantify the bias the OLD builder carried.

        Of the names in the universe on `as_of`, how many are dead today? Those
        are precisely the names a live screener cannot show you — and their
        absence is what made every prior backtest optimistic. Run this on a few
        historical dates before trusting any older result.
        """
        snap = self.build(as_of)
        dead = [t for t in snap.tickers if t.is_delisted]
        return {
            "as_of": as_of.isoformat(),
            "universe_size": snap.count,
            "delisted_since": len(dead),
            "pct_invisible_to_a_live_screener": (
                round(100.0 * len(dead) / snap.count, 1) if snap.count else 0.0),
            "examples": [t.symbol for t in dead[:15]],
        }
