"""
Universe builder.

Produces the daily list of tickers we'll consider for trading. The pipeline:

    1. Pull all stock listings from NASDAQ and NYSE via Nasdaq's screener API.
    2. Apply baseline filters: minimum price, minimum market cap, exchange.
    3. Add a hard-coded list of liquid major ETFs (SPY, QQQ, IWM, sector SPDRs).
    4. Enrich each ticker with current price and 30-day average daily volume
       from Tradier (batched in groups of 50).
    5. Apply the average-volume filter.
    6. Sort by market cap descending and persist to disk as JSON.

This module produces a *broad* candidate pool — typically 800–1000 names. The
downstream screener (V3) will narrow that to the ~50–150 actually-tradeable
candidates per day using IV rank, earnings calendar, bid-ask gates, etc.

The output JSON has a flat `tickers` list with per-symbol metadata so any
downstream consumer can filter or sort however it needs without reaching back
out to live APIs.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import requests

from .tradier import TradierClient

logger = logging.getLogger(__name__)


# ─── Nasdaq listing API ─────────────────────────────────────────────────────

NASDAQ_SCREENER_URL = "https://api.nasdaq.com/api/screener/stocks"

# Nasdaq's API requires a non-default User-Agent or it 403s.
_NASDAQ_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


# ─── Hard-coded liquid ETF whitelist ────────────────────────────────────────

# We include these regardless of whether they appear in the stock screener pull
# (ETFs are on a separate Nasdaq endpoint, and we don't want to maintain two
# fetchers). Every name here has deep options liquidity with weekly expirations
# and tight bid-ask. If you want to add or remove names, this is the place.
LIQUID_ETF_WHITELIST = [
    # Broad index ETFs
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "IWM",   # Russell 2000
    "DIA",   # Dow Jones
    "VTI",   # Total US market
    # Treasury ETFs
    "TLT",   # 20+ year treasury
    "IEF",   # 7-10 year treasury
    "SHY",   # 1-3 year treasury
    # Sector SPDRs
    "XLF",   # Financials
    "XLE",   # Energy
    "XLK",   # Technology
    "XLV",   # Healthcare
    "XLI",   # Industrials
    "XLU",   # Utilities
    "XLY",   # Consumer Discretionary
    "XLP",   # Consumer Staples
    "XLB",   # Materials
    "XLRE",  # Real Estate
    "XLC",   # Communication Services
    # Commodities
    "GLD",   # Gold
    "SLV",   # Silver
    "USO",   # Oil
    # International
    "EFA",   # Developed markets ex-US
    "EEM",   # Emerging markets
    # Credit
    "HYG",   # High yield corporate bonds
    "LQD",   # Investment grade corporate bonds
]


# ─── Data classes ───────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UniverseConfig:
    """Filtering and enrichment parameters for the universe builder."""

    # Baseline filters applied to the raw Nasdaq listing data.
    min_price: float = 20.0
    min_market_cap: float = 2_000_000_000.0  # $2B

    # Average daily volume filter applied after Tradier enrichment.
    min_avg_volume: int = 500_000

    # Which exchanges to include. NASDAQ + NYSE covers most US large/mid caps.
    exchanges: tuple[str, ...] = ("NASDAQ", "NYSE")

    # Whether to include the LIQUID_ETF_WHITELIST.
    include_etfs: bool = True

    # Batch size for Tradier quote enrichment. Tradier's quote endpoint accepts
    # up to ~50 symbols per call.
    quote_batch_size: int = 50


@dataclass
class UniverseTicker:
    symbol: str
    name: str
    exchange: str
    last_price: float
    market_cap: float
    avg_volume_30d: float | None
    is_etf: bool


@dataclass
class UniverseSnapshot:
    """A complete universe build result, suitable for JSON persistence."""

    build_timestamp_utc: str
    config: dict
    count: int
    tickers: list[UniverseTicker] = field(default_factory=list)


# ─── Parsing helpers ────────────────────────────────────────────────────────


def parse_price(s: object) -> float:
    """Parse a price string like '$1,234.56' or a raw number into a float."""
    if isinstance(s, (int, float)):
        return float(s)
    try:
        return float(str(s).replace("$", "").replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0.0


def parse_market_cap(c: object) -> float:
    """
    Parse a market cap value, which can be a raw number, a numeric string,
    or a string like '1.23B', '456M', '789K'.
    """
    if isinstance(c, (int, float)):
        return float(c)
    if not c:
        return 0.0
    s = str(c).replace(",", "").replace("$", "").strip()
    if not s:
        return 0.0
    try:
        unit = s[-1].upper()
        if unit == "B":
            return float(s[:-1]) * 1e9
        if unit == "M":
            return float(s[:-1]) * 1e6
        if unit == "K":
            return float(s[:-1]) * 1e3
        return float(s)
    except (ValueError, IndexError):
        return 0.0


# ─── Builder ────────────────────────────────────────────────────────────────


class UniverseBuilder:
    """
    Builds a tradeable ticker universe.

    Usage:
        builder = UniverseBuilder(config=UniverseConfig(), tradier=client)
        snapshot = builder.build()
        builder.save(snapshot, Path("data/cache/universe_2026-05-19.json"))
    """

    def __init__(
        self,
        config: UniverseConfig,
        tradier: TradierClient,
        session: Optional[requests.Session] = None,
    ):
        self.config = config
        self.tradier = tradier
        self._session = session or requests.Session()
        self._session.headers.update(_NASDAQ_HEADERS)

    # ─── Public API ──────────────────────────────────────────────────────────

    def build(self) -> UniverseSnapshot:
        """Run the full build pipeline and return the snapshot."""
        logger.info("Starting universe build")

        # 1. Fetch listings from Nasdaq for each exchange.
        raw_rows: list[dict] = []
        for exchange in self.config.exchanges:
            rows = self._fetch_listings(exchange)
            logger.info("Nasdaq screener: %s -> %d rows", exchange, len(rows))
            raw_rows.extend(rows)

        # 2. Apply baseline filters from the raw listing data.
        baseline_tickers = list(self._apply_baseline_filters(raw_rows))
        logger.info(
            "After baseline filters (price>=%s, cap>=%s): %d tickers",
            self.config.min_price,
            self.config.min_market_cap,
            len(baseline_tickers),
        )

        # 3. Add ETF whitelist.
        if self.config.include_etfs:
            existing_symbols = {t.symbol for t in baseline_tickers}
            etfs_to_add = [s for s in LIQUID_ETF_WHITELIST if s not in existing_symbols]
            logger.info("Adding %d ETFs from whitelist", len(etfs_to_add))
            for symbol in etfs_to_add:
                # Stub metadata for ETFs — will be enriched in the next step.
                baseline_tickers.append(
                    UniverseTicker(
                        symbol=symbol,
                        name=symbol,
                        exchange="NYSE",  # All whitelist ETFs trade on NYSE/ARCA
                        last_price=0.0,
                        market_cap=0.0,
                        avg_volume_30d=None,
                        is_etf=True,
                    )
                )

        # 4. Enrich with quote data from Tradier (batched).
        enriched = self._enrich_with_quotes(baseline_tickers)

        # 5. Apply volume filter.
        # ETFs from the whitelist bypass the market-cap filter (we trust them),
        # but they still need to pass the volume filter to ensure liquidity.
        passed = [
            t
            for t in enriched
            if (t.avg_volume_30d is not None and t.avg_volume_30d >= self.config.min_avg_volume)
            or (t.is_etf and (t.avg_volume_30d or 0) >= self.config.min_avg_volume)
        ]
        logger.info(
            "After volume filter (>=%s avg): %d tickers",
            self.config.min_avg_volume,
            len(passed),
        )

        # 6. Sort by market cap descending. ETFs sort to the top because we
        # treat them as having very high effective "cap" for sorting purposes.
        passed.sort(
            key=lambda t: (
                1 if t.is_etf else 0,
                t.market_cap,
                t.avg_volume_30d or 0,
            ),
            reverse=True,
        )

        snapshot = UniverseSnapshot(
            build_timestamp_utc=datetime.now(timezone.utc).isoformat(),
            config=asdict(self.config) if hasattr(self.config, "__dataclass_fields__") else {},
            count=len(passed),
            tickers=passed,
        )
        logger.info("Universe build complete: %d tickers", snapshot.count)
        return snapshot

    def save(self, snapshot: UniverseSnapshot, path: Path) -> None:
        """Persist a snapshot to disk as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "build_timestamp_utc": snapshot.build_timestamp_utc,
            "config": snapshot.config,
            "count": snapshot.count,
            "tickers": [asdict(t) for t in snapshot.tickers],
        }
        path.write_text(json.dumps(payload, indent=2))
        logger.info("Saved universe snapshot to %s", path)

    @staticmethod
    def load(path: Path) -> UniverseSnapshot:
        """Load a previously persisted snapshot."""
        payload = json.loads(path.read_text())
        tickers = [UniverseTicker(**t) for t in payload["tickers"]]
        return UniverseSnapshot(
            build_timestamp_utc=payload["build_timestamp_utc"],
            config=payload.get("config", {}),
            count=payload["count"],
            tickers=tickers,
        )

    # ─── Internal pipeline steps ─────────────────────────────────────────────

    def _fetch_listings(self, exchange: str) -> list[dict]:
        """Fetch all listings for a single exchange from Nasdaq's screener API."""
        params = {
            "tableonly": "true",
            "limit": "10000",
            "exchange": exchange,
        }
        try:
            response = self._session.get(
                NASDAQ_SCREENER_URL,
                params=params,
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error("Failed to fetch %s listings: %s", exchange, e)
            return []
        try:
            return response.json().get("data", {}).get("table", {}).get("rows", []) or []
        except (ValueError, AttributeError) as e:
            logger.error("Failed to parse Nasdaq response for %s: %s", exchange, e)
            return []

    def _apply_baseline_filters(self, rows: Iterable[dict]) -> Iterable[UniverseTicker]:
        """Apply price/market-cap filters and convert to UniverseTicker."""
        seen: set[str] = set()
        for row in rows:
            symbol = (row.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen:
                continue
            # Skip symbols with non-standard characters (warrants, units, rights,
            # preferreds — typically have '.', '/', '=', '^' in them).
            if any(ch in symbol for ch in (".", "/", "=", "^", " ")):
                continue

            price = parse_price(row.get("lastsale"))
            cap = parse_market_cap(row.get("marketCap"))

            if price < self.config.min_price:
                continue
            if cap < self.config.min_market_cap:
                continue

            seen.add(symbol)
            yield UniverseTicker(
                symbol=symbol,
                name=(row.get("name") or "").strip(),
                exchange=(row.get("exchange") or "").strip().upper(),
                last_price=price,
                market_cap=cap,
                avg_volume_30d=None,  # filled in by enrichment step
                is_etf=False,
            )

    def _enrich_with_quotes(
        self, tickers: list[UniverseTicker]
    ) -> list[UniverseTicker]:
        """
        Batch-fetch Tradier quotes for the candidate list and fill in
        last_price and avg_volume_30d. Tickers that don't return a quote
        (delisted, mistyped) are dropped.
        """
        by_symbol = {t.symbol: t for t in tickers}
        symbols = list(by_symbol.keys())
        logger.info("Fetching Tradier quotes for %d tickers", len(symbols))

        result: list[UniverseTicker] = []
        batch_size = self.config.quote_batch_size

        for i in range(0, len(symbols), batch_size):
            batch = symbols[i : i + batch_size]
            try:
                quotes = self.tradier.get_quotes(batch)
            except Exception as e:  # broker.TradierError + anything network-y
                logger.warning(
                    "Quote fetch failed for batch starting at %s: %s",
                    batch[0],
                    e,
                )
                continue

            for q in quotes:
                symbol = (q.get("symbol") or "").upper()
                if symbol not in by_symbol:
                    continue
                ticker = by_symbol[symbol]
                last = q.get("last") or q.get("close") or 0.0
                avg_vol = q.get("average_volume")
                # If the original baseline pass didn't set a price (ETFs from
                # the whitelist), pull it from the quote.
                if ticker.last_price == 0.0 and last:
                    ticker = UniverseTicker(
                        symbol=ticker.symbol,
                        name=q.get("description") or ticker.name,
                        exchange=ticker.exchange,
                        last_price=float(last),
                        market_cap=ticker.market_cap,
                        avg_volume_30d=float(avg_vol) if avg_vol else None,
                        is_etf=ticker.is_etf,
                    )
                else:
                    ticker = UniverseTicker(
                        symbol=ticker.symbol,
                        name=ticker.name or q.get("description") or "",
                        exchange=ticker.exchange,
                        last_price=ticker.last_price,
                        market_cap=ticker.market_cap,
                        avg_volume_30d=float(avg_vol) if avg_vol else None,
                        is_etf=ticker.is_etf,
                    )
                result.append(ticker)

        logger.info("Got quotes for %d/%d tickers", len(result), len(symbols))
        return result
