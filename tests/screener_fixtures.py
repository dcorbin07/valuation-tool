"""Synthetic screener provider for offline testing (no network).

Generates a universe with a *known embedded signal*: a hidden 'edge' per name
drives both its factors and (later) its forward return, so the scan should rank
high-edge names near the top and the backtest should detect real predictive power.
"""
from __future__ import annotations

import numpy as np

from valuation.screener.providers import ScreenerProvider
from valuation.screener.universe import BUNDLED_UNIVERSE

SECTORS = list(BUNDLED_UNIVERSE.keys())


def _rng(ticker):
    return np.random.default_rng(abs(hash(ticker)) % (2**32))


def synth_metrics(ticker, sector, edge=None):
    r = _rng(ticker)
    if edge is None:
        edge = float(r.normal(0, 1))            # hidden quality of the name
    # Absolute currency figures are USD DOLLARS, matching providers.METRICS_UNITS — the
    # contract every real provider now emits. ($0.5B–$300B caps, $50M–$3B operating income.)
    profitable = r.random() > 0.35
    op = (r.uniform(50, 3000) if profitable else -r.uniform(20, 800)) * 1e6
    mc = float(r.uniform(500, 300000)) * 1e6
    ey = 0.02 + 0.05 * edge + r.normal(0, 0.01) if profitable else r.normal(-0.02, 0.02)
    return {
        "ticker": ticker, "name": f"{ticker} Corp", "sector": sector, "industry": "",
        "price": float(r.uniform(8, 400)), "market_cap": mc,
        "operating_income": op, "net_income": op * 0.8,
        "revenue": float(r.uniform(200, 50000)) * 1e6,
        "fcf": op * r.uniform(0.5, 1.2), "ebitda": abs(op) + r.uniform(50, 500) * 1e6,
        "earnings_yield": ey, "fcf_yield": ey * r.uniform(0.7, 1.3),
        "ebit_ev": 0.03 + 0.05 * edge + r.normal(0, 0.01),
        "ev_ebitda": float(max(3, 18 - 4 * edge + r.normal(0, 2))),
        "ev_sales": float(max(0.3, 4 - 1.2 * edge + r.normal(0, 0.6))),
        "pe": float(max(4, 22 - 5 * edge + r.normal(0, 3))),
        "ps": float(max(0.3, 4 - 1.0 * edge + r.normal(0, 0.6))),
        "op_margin": float(np.clip(0.10 + 0.06 * edge + r.normal(0, 0.02), -0.2, 0.5)),
        "gross_margin": float(np.clip(0.35 + 0.08 * edge + r.normal(0, 0.05), 0.1, 0.9)),
        "roic": float(np.clip(0.08 + 0.06 * edge + r.normal(0, 0.02), -0.1, 0.4)),
        "roe": float(np.clip(0.10 + 0.06 * edge, -0.2, 0.5)),
        "net_debt_to_ebitda": float(np.clip(2.0 - 0.8 * edge + r.normal(0, 0.5), -1, 6)),
        "revenue_growth": float(np.clip(0.08 + 0.05 * edge + r.normal(0, 0.03), -0.3, 0.8)),
        "revenue_growth_prior": float(np.clip(0.07 + 0.03 * edge, -0.3, 0.7)),
        "ret_12_1": float(np.clip(0.05 + 0.10 * edge + r.normal(0, 0.15), -0.7, 1.5)),
        "avg_dollar_volume": float(r.uniform(2e6, 5e8)), "beta": float(r.uniform(0.6, 1.8)),
        "units": "usd",
        "_edge": edge,
    }


class SyntheticProvider(ScreenerProvider):
    name = "synthetic (offline test)"

    def __init__(self, per_sector=14):
        self.per_sector = per_sector
        self._edges = {}

    def get_universe(self, scope="bundled"):
        out = []
        for si, sector in enumerate(SECTORS):
            for j in range(self.per_sector):
                t = f"SYN{si:02d}{j:02d}"
                out.append({"ticker": t, "name": f"{t} Corp", "sector": sector,
                            "industry": "", "market_cap": None})
        return out

    def get_metrics(self, ticker):
        # find sector from ticker prefix
        si = int(ticker[3:5])
        sector = SECTORS[si]
        m = synth_metrics(ticker, sector)
        self._edges[ticker] = m["_edge"]
        return m
