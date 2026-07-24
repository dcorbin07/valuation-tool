"""
Macro inputs — the live risk-free rate (10-Year US Treasury).

Free, no key: reads the ^TNX index from Yahoo (10Y yield x10). Falls back to the
configured default if the network/lookup fails so valuation never blocks on it.
"""
from __future__ import annotations

from .models import _safe


def risk_free_rate(cfg) -> tuple[float, str]:
    """Return (rate_decimal, source_note)."""
    try:
        import yfinance as yf
        v = _safe(yf.Ticker("^TNX").fast_info.get("lastPrice"))
        if v is not None and 0 < v < 100:
            return v / 100.0, f"Live 10Y UST via ^TNX ({v/100.0:.2%})"
    except Exception:
        pass
    return cfg.default_risk_free, f"Default risk-free {cfg.default_risk_free:.2%} (live lookup failed)"
