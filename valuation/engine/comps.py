"""
Relative valuation (comps) cross-check.

A DCF is only one lens. Here we compute the subject's own trading multiples and
imply a value from sector-typical multiples. This is a fast reality check: if the
DCF says $200 but every multiple says $120, the DCF assumptions deserve scrutiny.

By default we compare against sector-benchmark multiples (works for any ticker
with no extra fetching). If explicit peer tickers are supplied, their fetched
median multiples are used instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import median
from typing import Optional

from ..data.models import CompanyData

# Rough sector-typical multiples (large-cap norms). Deliberately conservative and
# clearly a benchmark, not a precise peer set.
SECTOR_MULTIPLES = {
    "Technology":            {"pe": 30, "ev_ebitda": 22, "ps": 6.5, "ev_sales": 6.5},
    "Communication Services":{"pe": 20, "ev_ebitda": 9,  "ps": 3.5, "ev_sales": 3.5},
    "Consumer Cyclical":     {"pe": 20, "ev_ebitda": 12, "ps": 1.5, "ev_sales": 1.7},
    "Consumer Defensive":    {"pe": 22, "ev_ebitda": 14, "ps": 1.6, "ev_sales": 1.8},
    "Healthcare":            {"pe": 24, "ev_ebitda": 15, "ps": 3.5, "ev_sales": 3.8},
    "Industrials":           {"pe": 22, "ev_ebitda": 14, "ps": 1.8, "ev_sales": 2.0},
    "Energy":                {"pe": 12, "ev_ebitda": 6,  "ps": 1.2, "ev_sales": 1.3},
    "Basic Materials":       {"pe": 15, "ev_ebitda": 8,  "ps": 1.5, "ev_sales": 1.6},
    "Utilities":             {"pe": 18, "ev_ebitda": 11, "ps": 2.2, "ev_sales": 3.0},
    "Real Estate":           {"pe": 30, "ev_ebitda": 18, "ps": 5.0, "ev_sales": 8.0},
    "Financial Services":    {"pe": 13, "ev_ebitda": 0,  "ps": 3.0, "ev_sales": 0},
}
_DEFAULT = {"pe": 20, "ev_ebitda": 12, "ps": 2.5, "ev_sales": 2.8}


@dataclass
class CompsResult:
    subject: dict = field(default_factory=dict)     # subject's own multiples
    benchmark: dict = field(default_factory=dict)   # multiples applied
    benchmark_source: str = "sector"
    implied: dict = field(default_factory=dict)      # implied value/share per method
    comps_fair_value: Optional[float] = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _subject_multiples(cd: CompanyData) -> dict:
    m = {}
    ev = None
    if cd.market_cap is not None:
        nd = cd.net_debt if cd.net_debt is not None else 0.0
        ev = cd.market_cap + nd
    ebitda = (cd.ebit + cd.da) if (cd.ebit is not None and cd.da is not None) else None
    if cd.market_cap and cd.net_income and cd.net_income > 0:
        m["pe"] = cd.market_cap / cd.net_income
    if cd.market_cap and cd.revenue and cd.revenue > 0:
        m["ps"] = cd.market_cap / cd.revenue
    if ev and cd.revenue and cd.revenue > 0:
        m["ev_sales"] = ev / cd.revenue
    if ev and ebitda and ebitda > 0:
        m["ev_ebitda"] = ev / ebitda
    return m


def compute_comps(cd: CompanyData, peers: Optional[list] = None,
                  fetch_fn=None) -> CompsResult:
    subj = _subject_multiples(cd)
    res = CompsResult(subject=subj)

    bench = dict(SECTOR_MULTIPLES.get(cd.sector, _DEFAULT))
    res.benchmark_source = f"{cd.sector or 'default'} sector benchmark"

    # Optional: use real peer medians if peers + a fetch function are provided.
    if peers and fetch_fn:
        peer_mults = {"pe": [], "ev_ebitda": [], "ps": [], "ev_sales": []}
        used = []
        for p in peers:
            try:
                pc = fetch_fn(p)
                pm = _subject_multiples(pc)
                for k in peer_mults:
                    if pm.get(k) and pm[k] > 0:
                        peer_mults[k].append(pm[k])
                used.append(p.upper())
            except Exception:
                continue
        bench2 = {k: median(v) for k, v in peer_mults.items() if v}
        if bench2:
            bench = bench2
            res.benchmark_source = "peer median (" + ", ".join(used) + ")"
    res.benchmark = bench

    shares = cd.shares_diluted
    nd = cd.net_debt if cd.net_debt is not None else 0.0
    implied = {}
    if shares and shares > 0:
        if bench.get("pe") and cd.net_income and cd.net_income > 0:
            implied["pe"] = bench["pe"] * (cd.net_income / shares)
        if bench.get("ps") and cd.revenue:
            implied["ps"] = bench["ps"] * (cd.revenue / shares)
        if bench.get("ev_sales") and cd.revenue:
            implied_ev = bench["ev_sales"] * cd.revenue
            implied["ev_sales"] = (implied_ev - nd) / shares
        ebitda = (cd.ebit + cd.da) if (cd.ebit is not None and cd.da is not None) else None
        if bench.get("ev_ebitda") and ebitda and ebitda > 0:
            implied_ev = bench["ev_ebitda"] * ebitda
            implied["ev_ebitda"] = (implied_ev - nd) / shares
    res.implied = implied
    vals = [v for v in implied.values() if v is not None and v > 0]
    res.comps_fair_value = (sum(vals) / len(vals)) if vals else None
    return res
