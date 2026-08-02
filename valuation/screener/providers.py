"""
Data providers for the screener — a thin abstraction so the scan logic never
cares where the numbers come from.

  * FreeProvider  — default, no key. Universe from the bundled list or SEC EDGAR's
    full filer list; per-name metrics from the existing yahoo/EDGAR fetch; prices
    from Stooq/yfinance. Works everywhere but slower at whole-market scale.
  * FMPProvider   — used automatically if FMP_API_KEY is set. One screener call
    returns the whole market with metrics; fast enough for ~5,000+ names.

Both emit the same normalized `metrics` dict that the factor engine consumes.
"""
from __future__ import annotations

from typing import Optional

from ..config import CONFIG
from . import universe as U
from . import prices as P


# --------------------------------------------------------------------------- #
# Pure mapping: CompanyData -> screener metrics (unit-testable offline)
# --------------------------------------------------------------------------- #
def company_to_metrics(cd, quote: Optional[dict] = None) -> dict:
    """Turn a valuation CompanyData (+ optional price quote) into factor inputs."""
    def sd(x):
        return x if (x is not None) else None

    mc = cd.market_cap
    nd = cd.net_debt if cd.net_debt is not None else 0.0
    ev = (mc + nd) if mc is not None else None
    ebitda = (cd.ebit + cd.da) if (cd.ebit is not None and cd.da is not None) else None

    # revenue growth + prior (acceleration)
    rg = cd.rev_growth_ttm
    rg_prior = None
    h = [v for v in (cd.revenue_history or []) if v is not None]
    if len(h) >= 3 and h[2]:
        rg_prior = h[1] / h[2] - 1.0

    roe = None
    if cd.net_income is not None and cd.total_equity not in (None, 0) and cd.total_equity > 0:
        roe = cd.net_income / cd.total_equity

    m = {
        "ticker": cd.ticker, "name": cd.name, "sector": cd.sector, "industry": cd.industry,
        "price": sd(cd.price if cd.price is not None else (quote or {}).get("price")),
        "market_cap": mc, "revenue": cd.revenue, "net_income": cd.net_income,
        "operating_income": cd.ebit, "fcf": cd.fcf, "ebitda": ebitda, "ev": ev,
        # Carried per row so the hot-list fair value can bridge an ENTERPRISE multiple
        # (EV/Sales, EV/EBITDA) back to a per-share EQUITY value. Without it those
        # multiples had to be skipped, which left every pre-profit name with nothing to
        # value on but a (negative, unusable) earnings yield.
        "net_debt": cd.net_debt,
        "earnings_yield": (cd.net_income / mc) if (cd.net_income is not None and mc) else None,
        "fcf_yield": (cd.fcf / mc) if (cd.fcf is not None and mc) else None,
        "ebit_ev": (cd.ebit / ev) if (cd.ebit is not None and ev) else None,
        "ev_ebitda": (ev / ebitda) if (ev and ebitda and ebitda > 0) else None,
        "ev_sales": (ev / cd.revenue) if (ev and cd.revenue) else None,
        "pe": (mc / cd.net_income) if (mc and cd.net_income and cd.net_income > 0) else None,
        "ps": (mc / cd.revenue) if (mc and cd.revenue) else None,
        "op_margin": cd.ebit_margin, "gross_margin": cd.gross_margin, "roic": cd.roic, "roe": roe,
        "net_debt_to_ebitda": cd.net_debt_to_ebitda,
        "revenue_growth": rg, "revenue_growth_prior": rg_prior,
        "ret_12_1": (quote or {}).get("ret_12_1") if quote else cd.ret_6m,
        "ret_6_1": (quote or {}).get("ret_6_1") if quote else None,
        "high_prox": (quote or {}).get("high_prox") if quote else None,
        "realized_vol": (quote or {}).get("realized_vol") if quote else None,
        "avg_dollar_volume": (quote or {}).get("avg_dollar_volume") if quote else None,
        "beta": cd.beta,
        # Raw inputs for the quality theme (profitability + safety).
        "gross_profit": cd.gross_profit, "total_debt": cd.total_debt, "total_equity": cd.total_equity,
        "interest_expense": cd.interest_expense,
        # Hooks — populated when the data source supports them; None → neutral factor.
        "earnings_revision": None,      # sentiment: estimate revisions (needs an estimates feed)
        "share_issuance": None,         # capital discipline: YoY change in shares (needs share history)
        "asset_growth": None,           # capital discipline: YoY change in total assets (needs balance-sheet history)
        "quote_type": (getattr(cd, "quote_type", "") or ""),
        "is_fund": (getattr(cd, "quote_type", "") or "").upper() in
                   {"ETF", "MUTUALFUND", "MONEYMARKET", "CURRENCY", "INDEX", "FUND"},
    }
    return m


class ScreenerProvider:
    name = "base"

    def get_universe(self, scope: str) -> list:
        raise NotImplementedError

    def get_metrics(self, ticker: str) -> Optional[dict]:
        raise NotImplementedError

    def price_history(self, ticker: str, days: int = 1500):
        return P.close_series(ticker, days)


class FreeProvider(ScreenerProvider):
    name = "free (EDGAR + Yahoo + Stooq)"

    def __init__(self, cfg=CONFIG, store=None):
        self.cfg = cfg
        self.store = store

    def get_universe(self, scope: str = "bundled") -> list:
        if scope in ("whole_market", "edgar"):
            edgar_list = self._edgar_universe()
            if edgar_list:
                return edgar_list
        # default / fallback: bundled sector-labeled list
        smap = U.bundled_sector_map()
        return [{"ticker": t, "name": t, "sector": smap.get(t, ""), "industry": "",
                 "market_cap": None} for t in U.bundled_tickers()]

    def _edgar_universe(self) -> list:
        try:
            import requests
            r = requests.get("https://www.sec.gov/files/company_tickers.json",
                             headers={"User-Agent": self.cfg.sec_user_agent}, timeout=25)
            r.raise_for_status()
            rows = []
            for v in r.json().values():
                rows.append({"ticker": v["ticker"].upper(), "name": v.get("title", ""),
                             "sector": "", "industry": "", "market_cap": None})
            return rows
        except Exception:
            return []

    def get_metrics(self, ticker: str) -> Optional[dict]:
        # cached?
        if self.store:
            cached = self.store.get_cached_fundamentals(ticker, max_age_days=self.cfg_max_age())
            if cached:
                return cached
        try:
            from ..data import fetcher
            cd = fetcher.get_company(ticker, self.cfg)
            if getattr(cd, "fx_unresolved", False):
                return None   # statement/price currency mismatch we couldn't resolve — skip vs. rank garbage
            quote = P.get_quote(ticker)
            m = company_to_metrics(cd, quote)
        except Exception:
            return None
        if self.store and m:
            self.store.cache_fundamentals(ticker, m)
        return m

    def cfg_max_age(self):
        return 30  # refresh cached fundamentals monthly by default


class FMPProvider(ScreenerProvider):
    name = "Financial Modeling Prep"
    BASE = "https://financialmodelingprep.com/stable"

    def __init__(self, cfg=CONFIG, store=None):
        self.cfg = cfg
        self.store = store
        self.key = cfg.fmp_api_key

    def _get(self, path, **params):
        import requests
        params["apikey"] = self.key
        r = requests.get(f"{self.BASE}/{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def get_universe(self, scope: str = "whole_market") -> list:
        # One call returns the market with sector + market cap already attached.
        try:
            data = self._get("company-screener", exchange="NASDAQ,NYSE",
                             isActivelyTrading="true", country="US", limit=6000)
            out = []
            for d in data:
                out.append({"ticker": (d.get("symbol") or "").upper(),
                            "name": d.get("companyName", ""), "sector": d.get("sector", ""),
                            "industry": d.get("industry", ""), "market_cap": d.get("marketCap")})
            return [x for x in out if x["ticker"]]
        except Exception:
            # fall back to the free universe if the key/endpoint isn't working
            return FreeProvider(self.cfg, self.store).get_universe("bundled")

    def get_metrics(self, ticker: str) -> Optional[dict]:
        if self.store:
            cached = self.store.get_cached_fundamentals(ticker, max_age_days=30)
            if cached:
                return cached
        try:
            km = (self._get("key-metrics-ttm", symbol=ticker) or [{}])[0]
            ratios = (self._get("ratios-ttm", symbol=ticker) or [{}])[0]
            profile = (self._get("profile", symbol=ticker) or [{}])[0]
            m = _fmp_to_metrics(ticker, km, ratios, profile)
        except Exception:
            return None
        if self.store and m:
            self.store.cache_fundamentals(ticker, m)
        return m


def _fmp_to_metrics(ticker, km, ratios, profile) -> dict:
    """Map FMP TTM key-metrics/ratios/profile to our metrics dict (best-effort;
    verify field names against your FMP plan's live payload on first run)."""
    g = lambda d, *ks: next((d[k] for k in ks if d.get(k) is not None), None)
    mc = g(profile, "marketCap", "mktCap")
    return {
        "ticker": ticker.upper(), "name": g(profile, "companyName") or ticker,
        "sector": g(profile, "sector") or "", "industry": g(profile, "industry") or "",
        "price": g(profile, "price"), "market_cap": mc,
        "earnings_yield": g(km, "earningsYieldTTM", "earningsYield"),
        "fcf_yield": g(km, "freeCashFlowYieldTTM", "freeCashFlowYield"),
        "ev_ebitda": g(ratios, "enterpriseValueMultipleTTM", "evToEbitdaTTM"),
        "ev_sales": g(km, "evToSalesTTM"),
        "pe": g(ratios, "priceToEarningsRatioTTM", "peRatioTTM"),
        "ps": g(ratios, "priceToSalesRatioTTM"),
        "op_margin": g(ratios, "operatingProfitMarginTTM"),
        "gross_margin": g(ratios, "grossProfitMarginTTM"),
        "roic": g(km, "returnOnInvestedCapitalTTM", "roicTTM"),
        "roe": g(ratios, "returnOnEquityTTM"),
        "net_debt_to_ebitda": g(km, "netDebtToEBITDATTM"),
        "revenue_growth": g(profile, "revenueGrowth"),
        "revenue_growth_prior": None,
        "operating_income": None, "fcf": None, "revenue": None, "net_income": None,
        "gross_profit": g(km, "grossProfitTTM"), "total_debt": g(km, "totalDebtTTM"),
        "total_equity": g(km, "totalStockholdersEquityTTM"),
        "earnings_revision": None,
        "ret_12_1": None, "avg_dollar_volume": g(profile, "volAvg"), "beta": g(profile, "beta"),
        "is_fund": bool(g(profile, "isEtf") or g(profile, "isFund")),
        "quote_type": "ETF" if (g(profile, "isEtf") or g(profile, "isFund")) else "EQUITY",
    }


def get_provider(cfg=CONFIG, store=None) -> ScreenerProvider:
    if cfg.fmp_api_key:
        return FMPProvider(cfg, store)
    return FreeProvider(cfg, store)
