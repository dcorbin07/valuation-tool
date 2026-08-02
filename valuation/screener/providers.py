"""
Data providers for the screener — a thin abstraction so the scan logic never
cares where the numbers come from.

  * FreeProvider  — default, no key. Universe from the BROKER (Tradier: ~7,100 listed
    names, liquidity-ranked), else SEC EDGAR's filer list, else the bundled list;
    per-name metrics from the existing yahoo/EDGAR fetch; prices from Stooq/yfinance.
    Works everywhere but slower at whole-market scale.
  * FMPProvider   — used automatically if FMP_API_KEY is set.

FMP's bulk endpoints (`company-screener`, `stock-list`, every `*-constituent` list) are
402 Restricted on the current subscription, and its per-symbol endpoints serve only an
allowlist — most of the liquid universe returns 402 "this value set for 'symbol' is not
available under your current subscription". So FMPProvider is NOT a whole-market provider
here: it takes the universe from the fallback chain and serves whichever individual names
its plan allows, delegating the rest to the free stack. Both paths emit the same normalized
`metrics` dict, and the per-source split is reported in the scan's health block so a book
built from two fundamentals feeds is never a silent fact.
"""
from __future__ import annotations

import threading as _threading
from typing import Optional

from ..config import CONFIG
from . import universe as U
from . import prices as P


# --------------------------------------------------------------------------- #
# UNIT CONVENTION (do not break): every absolute currency figure in a metrics
# dict is in USD DOLLARS.
#
# This used to be provider-dependent and it silently corrupted the product. The
# valuation CompanyData carries millions (see data/models.py), so the free path
# emitted market_cap in MILLIONS while FMP's profile emits DOLLARS — and the two
# meet in the same scan. Downstream everything assumes dollars: the Valquo Index
# keeps names above a 10e9 large-cap floor and the web UI renders market_cap/1e9,
# so a millions-denominated $276B Dell displayed as "$0.0B" and no name ever
# cleared the large-cap floor (the book quietly fell back to "largest half").
#
# Ratios are unit-free, so they are computed on the raw (millions) values and the
# absolute figures are scaled once, at the end. Every metrics dict is stamped with
# `units` so a cache entry written under the old convention is discarded instead
# of being mixed into a fresh scan.
# --------------------------------------------------------------------------- #
METRICS_UNITS = "usd"

_ABSOLUTE_USD = ("market_cap", "revenue", "net_income", "operating_income", "fcf",
                 "ebitda", "ev", "gross_profit", "total_debt", "total_equity",
                 "interest_expense")


def _stamp_units(m: dict, scale: float = 1.0) -> dict:
    """Scale the absolute currency figures to USD dollars and record the convention."""
    if scale != 1.0:
        for k in _ABSOLUTE_USD:
            v = m.get(k)
            if v is not None:
                m[k] = v * scale
    m["units"] = METRICS_UNITS
    return m


def _usable_cache(cached):
    """Drop cached fundamentals written before the USD normalization (they hold millions)."""
    return cached if (cached or {}).get("units") == METRICS_UNITS else None


def _redact(msg) -> str:
    """Strip API keys out of a message before it can be stored or served.

    `requests` puts the FULL request URL in its HTTPError text, query string included — so
    an unedited "FMP call failed" note carries the live apikey, and these notes are surfaced
    publicly in the scan's health block. Never widen what reaches that block without going
    through here.
    """
    import re
    s = str(msg)
    s = re.sub(r"(?i)([?&](?:apikey|api_key|token|access_token)=)[^&\s]+", r"\1<redacted>", s)
    return re.sub(r"(?i)(bearer\s+)\S+", r"\1<redacted>", s)


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
    # CompanyData carries millions; the metrics contract is dollars. Ratios above are
    # unit-free and unaffected — only the absolute figures move.
    return _stamp_units(m, scale=1e6)


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
        self.universe_note = ""

    def get_universe(self, scope: str = "bundled") -> list:
        # Broker first for a whole-market scope. Tradier enumerates ~7,100 listed common
        # stocks in 26 calls and prices them in batches, so it returns a LIQUIDITY-RANKED
        # universe with company names and prices already attached. SEC EDGAR returns every
        # filer that ever existed — ~10,000 rows with no price and no way to tell a mega-cap
        # from a shell — so it is the second choice, not the first.
        if scope in ("whole_market", "broker", "liquid"):
            rows = self._broker_universe()
            if rows:
                self.universe_note = ""
                return rows
        if scope in ("whole_market", "edgar"):
            edgar_list = self._edgar_universe()
            if edgar_list:
                return edgar_list
        if scope == "sp500":
            smap = U.bundled_sector_map()
            return [{"ticker": t, "name": "", "sector": smap.get(t, ""), "industry": "",
                     "market_cap": None} for t in U.sp500_tickers(self.cfg)]
        # default / fallback: bundled sector-labeled list
        smap = U.bundled_sector_map()
        return [{"ticker": t, "name": t, "sector": smap.get(t, ""), "industry": "",
                 "market_cap": None} for t in U.bundled_tickers()]

    def _broker_universe(self) -> list:
        try:
            from . import broker_universe as BU
            if not BU.available(self.cfg):
                self.universe_note = ("no TRADIER_TOKEN — cannot source the broker universe; "
                                      "falling back")
                return []
            rows = BU.build(self.cfg, limit=int(getattr(self.cfg, "universe_limit", 0)
                                                or BU.DEFAULT_LIMIT))
            if not rows:
                self.universe_note = "broker universe came back empty — falling back"
            return rows
        except Exception as e:
            self.universe_note = f"broker universe failed ({_redact(e)}) — falling back"
            return []

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
            cached = _usable_cache(
                self.store.get_cached_fundamentals(ticker, max_age_days=self.cfg_max_age()))
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
    CALLS_PER_NAME = 3          # key-metrics-ttm + ratios-ttm + profile
    FAIL_STREAK_OFF = 12        # consecutive failures before we stop asking FMP

    def __init__(self, cfg=CONFIG, store=None):
        self.cfg = cfg
        self.store = store
        self.key = cfg.fmp_api_key
        # Why a universe call fell back, recorded rather than swallowed. The live site spent
        # weeks scanning 191 bundled names instead of the market because this exception was
        # caught silently and the fallback looks identical to success from the outside.
        self.universe_note = ""
        # Per-scan call budget. With no bulk endpoint every uncached name costs
        # CALLS_PER_NAME requests, so an 800-name universe is ~2,400 — enough to exhaust a
        # day's quota in one scan. 0 = unlimited (the default; set FMP_MAX_CALLS to bound
        # it). This caps what we SPEND, not what we rank: a name past the budget is served
        # by the free stack instead, and the split is reported in the scan's health block.
        self.max_calls = int(getattr(cfg, "fmp_max_calls", 0) or 0)
        self._calls = 0
        self._skipped = 0
        self._served_fmp = 0
        self._served_free = 0
        self._fmp_errors: list = []
        self._fail_streak = 0
        self._fmp_off = False
        self._free = None
        self._lock = _threading.Lock()

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
            out = [x for x in out if x["ticker"]]
            if not out:
                return self._fallback_universe(scope, "FMP company-screener returned no rows")
            return out
        except Exception as e:
            return self._fallback_universe(scope, f"FMP company-screener failed ({_redact(e)})")

    def _fallback_universe(self, scope: str, why: str) -> list:
        """Fall back for the SCOPE THAT WAS ASKED FOR.

        This used to hardcode "bundled" no matter what the caller wanted, which is why a
        `whole_market` scan silently became a 191-name scan: FMP's `company-screener` is a
        402 Restricted Endpoint on this subscription (so is `stock-list`, every
        `*-constituent` list and `batch-quote-short` — verified 2026-08-02 against the live
        key), the exception was swallowed, and the bundled list looked like success.
        """
        free = FreeProvider(self.cfg, self.store)
        rows = free.get_universe(scope)
        detail = free.universe_note
        self.universe_note = (f"{_redact(why)} — this subscription has no bulk endpoint; sourced "
                              f"{len(rows)} names from the fallback chain instead"
                              + (f" ({detail})" if detail else ""))
        return rows

    def _take_budget(self, n: int = None) -> bool:
        n = self.CALLS_PER_NAME if n is None else n
        if not self.max_calls:
            return True
        with self._lock:
            if self._calls + n > self.max_calls:
                self._skipped += 1
                return False
            self._calls += n
            return True

    @property
    def budget(self) -> dict:
        seen = []
        for e in self._fmp_errors:                      # de-duped, bounded sample
            k = e[:70]
            if k not in seen:
                seen.append(k)
        return {"calls_per_name": self.CALLS_PER_NAME, "max_calls": self.max_calls or None,
                "calls_used": self._calls, "names_skipped_over_budget": self._skipped,
                "served_by_fmp": self._served_fmp, "served_by_free_fallback": self._served_free,
                "fmp_errors": len(self._fmp_errors), "fmp_error_sample": seen[:3],
                "fmp_disabled_mid_scan": self._fmp_off}

    def get_metrics(self, ticker: str) -> Optional[dict]:
        if self.store:
            cached = _usable_cache(self.store.get_cached_fundamentals(ticker, max_age_days=30))
            if cached:
                return cached                       # cache hits cost no quota
        # Over budget or circuit-broken: serve the name from the free stack rather than drop
        # it. The budget bounds what we SPEND at FMP, not how many names the product ranks.
        if self._fmp_off or not self._take_budget():
            return self._free_fallback(ticker)
        try:
            km = (self._get("key-metrics-ttm", symbol=ticker) or [{}])[0]
            ratios = (self._get("ratios-ttm", symbol=ticker) or [{}])[0]
            profile = (self._get("profile", symbol=ticker) or [{}])[0]
            m = _fmp_to_metrics(ticker, km, ratios, profile)
            with self._lock:
                self._served_fmp += 1
                self._fail_streak = 0
        except Exception as e:
            # This subscription serves only an allowlist of symbols: most names come back
            # 402 "This value set for 'symbol' is not available under your current
            # subscription" (verified 2026-08-02 — FCX, NSC, MU and most of the liquid
            # universe). Returning None there would leave the product ranking a handful of
            # mega-caps, so fall back to the free stack for that one name rather than
            # dropping it. The split is reported in the scan's health block, because a book
            # built from two fundamentals sources is a fact the reader should see.
            with self._lock:
                self._fmp_errors.append(_redact(e)[:120])
                self._fail_streak += 1
                # Circuit breaker. When the subscription is symbol-restricted essentially
                # every name fails, and paying 3 requests each to discover that would burn
                # the daily quota and the wall clock on nothing. After a run of consecutive
                # failures, stop asking and serve the rest from the free stack.
                if self._fail_streak >= self.FAIL_STREAK_OFF and not self._fmp_off:
                    self._fmp_off = True
            m = self._free_fallback(ticker)
            if m is None:
                return None
        if self.store and m:
            self.store.cache_fundamentals(ticker, m)
        return m

    def _free_fallback(self, ticker: str) -> Optional[dict]:
        if not self._free:
            self._free = FreeProvider(self.cfg, None)      # no store: we cache below
        m = self._free.get_metrics(ticker)
        if m is not None:
            with self._lock:
                self._served_free += 1
        return m


def _fmp_to_metrics(ticker, km, ratios, profile) -> dict:
    """Map FMP TTM key-metrics/ratios/profile to our metrics dict (best-effort;
    verify field names against your FMP plan's live payload on first run)."""
    g = lambda d, *ks: next((d[k] for k in ks if d.get(k) is not None), None)
    mc = g(profile, "marketCap", "mktCap")
    m = {
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
    # FMP already reports absolute figures in dollars — stamp, don't scale.
    return _stamp_units(m)


def get_provider(cfg=CONFIG, store=None) -> ScreenerProvider:
    if cfg.fmp_api_key:
        return FMPProvider(cfg, store)
    return FreeProvider(cfg, store)
