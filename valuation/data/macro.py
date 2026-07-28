"""
Macro inputs — the live risk-free rate (10-Year US Treasury).

Free, no key: reads the ^TNX index from Yahoo (10Y yield x10). Falls back to the
configured default if the network/lookup fails so valuation never blocks on it.
"""
from __future__ import annotations

import time

from .models import _safe

# The 10Y yield barely moves intraday, but get_company() is called once per name —
# so in a 1,500-name scan this was 1,500 identical ^TNX lookups. Cache it process-wide
# for a few minutes so a full scan hits the network once, not once per ticker.
_CACHE = {"rate": None, "note": "", "ts": 0.0}
_TTL_SECONDS = 600


def risk_free_rate(cfg) -> tuple[float, str]:
    """Return (rate_decimal, source_note). Cached ~10 min to avoid per-name refetches."""
    now = time.time()
    if _CACHE["rate"] is not None and (now - _CACHE["ts"]) < _TTL_SECONDS:
        return _CACHE["rate"], _CACHE["note"]
    try:
        import yfinance as yf
        v = _safe(yf.Ticker("^TNX").fast_info.get("lastPrice"))
        if v is not None and 0 < v < 100:
            _CACHE.update(rate=v / 100.0, note=f"Live 10Y UST via ^TNX ({v/100.0:.2%})", ts=now)
            return _CACHE["rate"], _CACHE["note"]
    except Exception:
        pass
    # cache the fallback too (short TTL) so a network outage doesn't retry 1,500×
    _CACHE.update(rate=cfg.default_risk_free,
                  note=f"Default risk-free {cfg.default_risk_free:.2%} (live lookup failed)", ts=now)
    return _CACHE["rate"], _CACHE["note"]
