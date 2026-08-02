"""
The live scanning universe, sourced from the BROKER (Tradier).

Why this exists: FMP's bulk endpoints — `company-screener`, `stock-list`, every
`*-constituent` list, `available-exchanges`, `batch-quote-short` — all return
**402 Restricted Endpoint** on the current subscription. Verified against the live key
on 2026-08-02; per-symbol endpoints (`profile`, `quote`, `key-metrics-ttm`, `ratios-ttm`)
work fine, so the key is valid and it is specifically the *list* endpoints that are paid.
That left the scan falling back to the 191-name bundled list, so the "top decile" of the
large-cap tier was a decile of 154 names.

Tradier has no such restriction and is already paid for:

  * `markets/lookup` — 26 calls (one per letter) enumerate ~7,100 distinct NYSE/Nasdaq
    common stocks with their company names, in about ten seconds.
  * `markets/quotes` — batched, hundreds of symbols per call, returning last price,
    average volume and the 52-week high.

So the whole universe costs ~50 free calls. Names are ranked by **average dollar volume**
rather than market cap: the broker does not publish market cap, and liquidity is both the
thing that actually decides whether a name is tradeable and an extremely tight proxy for
size. The market cap that gates the large-cap tier still comes from the fundamentals feed
per name, exactly as before — this module only decides *which* names are worth spending a
fundamentals call on.

Deliberately NOT Sharadar: that export is point-in-time backtest data and has no business
in the live path.
"""
from __future__ import annotations

import string
from typing import Optional

from ..config import CONFIG
from . import settings as S

LOOKUP_EXCHANGES = "N,Q"          # NYSE + Nasdaq
QUOTE_CHUNK = 200                 # symbols per batched quote call
DEFAULT_LIMIT = 1500              # names kept after the liquidity ranking


def _base(cfg) -> str:
    return ("https://api.tradier.com/v1" if getattr(cfg, "tradier_env", "live") == "live"
            else "https://sandbox.tradier.com/v1")


def _headers(cfg) -> dict:
    return {"Authorization": f"Bearer {cfg.tradier_token}", "Accept": "application/json"}


def _as_list(x) -> list:
    """Tradier collapses a one-element array to a bare object. Normalize."""
    if not x:
        return []
    return x if isinstance(x, list) else [x]


def normalize(symbol: str) -> str:
    """Tradier writes class shares with a slash (BRK/B, BF/B); the fundamentals feeds and
    yfinance both want a dash (BRK-B). Left unconverted these names fail every downstream
    lookup, which quietly drops some of the largest companies in the market."""
    return (symbol or "").upper().replace("/", "-").strip()


def available(cfg=CONFIG) -> bool:
    return bool(getattr(cfg, "tradier_token", ""))


def list_symbols(cfg=CONFIG, session=None) -> dict:
    """{TICKER: company name} for every common stock listed on NYSE/Nasdaq.

    One `markets/lookup` per letter. A letter that fails is skipped rather than aborting the
    sweep — a partial universe is still enormously better than the 191-name bundled list,
    and the caller reports how many names it got.
    """
    import requests
    s = session or requests.Session()
    out: dict = {}
    for ch in string.ascii_uppercase:
        try:
            r = s.get(f"{_base(cfg)}/markets/lookup",
                      params={"q": ch, "exchanges": LOOKUP_EXCHANGES, "types": "stock"},
                      headers=_headers(cfg), timeout=30)
            r.raise_for_status()
            for sec in _as_list((r.json().get("securities") or {}).get("security")):
                t = (sec.get("symbol") or "").upper()
                if t and (sec.get("type") or "stock") == "stock":
                    out[t] = sec.get("description") or ""
        except Exception:
            continue
    return out


def quote_batch(tickers, cfg=CONFIG, session=None) -> dict:
    """{TICKER: quote fields} from batched `markets/quotes`. Free and unmetered."""
    import requests
    s = session or requests.Session()
    tickers = [t for t in tickers if t]
    out: dict = {}
    for i in range(0, len(tickers), QUOTE_CHUNK):
        chunk = tickers[i:i + QUOTE_CHUNK]
        try:
            r = s.get(f"{_base(cfg)}/markets/quotes", params={"symbols": ",".join(chunk)},
                      headers=_headers(cfg), timeout=45)
            r.raise_for_status()
            for q in _as_list((r.json().get("quotes") or {}).get("quote")):
                t = (q.get("symbol") or "").upper()
                if t:
                    out[t] = q
        except Exception:
            continue
    return out


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def build(cfg=CONFIG, limit: int = DEFAULT_LIMIT, min_price: float = None,
          min_adv: float = None, session=None) -> list:
    """The liquid US common-stock universe, most liquid first.

    Returns universe rows in the shape `run_scan` expects, carrying the display/eligibility
    fields the broker gives us for free: company name, price and average dollar volume.
    `market_cap` stays None — the broker does not publish it, and the fundamentals feed
    supplies it per name.
    """
    min_price = S.PRICE_FLOOR if min_price is None else min_price
    min_adv = S.MIN_AVG_DOLLAR_VOLUME if min_adv is None else min_adv

    names = list_symbols(cfg, session=session)
    if not names:
        return []
    quotes = quote_batch(sorted(names), cfg, session=session)

    rows, seen = [], set()
    for t, nm in names.items():
        q = quotes.get(t)
        if not q or (q.get("type") or "stock") != "stock":
            continue
        price = _f(q.get("last")) or _f(q.get("prevclose"))
        avg_vol = _f(q.get("average_volume")) or _f(q.get("volume"))
        if price is None or price < min_price or not avg_vol:
            continue
        adv = price * avg_vol
        if adv < min_adv:
            continue
        hi = _f(q.get("week_52_high"))
        tick = normalize(t)                      # BRK/B -> BRK-B for the downstream feeds
        if tick in seen:
            continue
        seen.add(tick)
        rows.append({
            "ticker": tick,
            "name": nm or (q.get("description") or ""),
            "sector": "", "industry": "", "market_cap": None,
            "price": price,
            "avg_dollar_volume": adv,
            # Nearness to the 52-week high — a momentum input the FMP path never had.
            "high_prox": (price / hi) if (hi and hi > 0) else None,
        })

    rows.sort(key=lambda r: -r["avg_dollar_volume"])
    return rows[:limit] if limit else rows
