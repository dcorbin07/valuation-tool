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
from ..safe_error import redact
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

# Bumped whenever a metrics row gains fields that a cached row would be missing. A cache entry
# written under an older schema is DISCARDED rather than served, because a stale row silently
# lacking (say) `sector` looks identical to a name the feed genuinely has no sector for — and
# that is exactly how the blank-sector bug survived on the live site for weeks. Cost of a bump
# is one slow refetch cycle; cost of not bumping is a coverage number that lies.
#   1 -> USD normalization (the original `units` stamp)
#   2 -> broker fundamentals merged in (sector / beta / ev / book_to_price / roe now expected)
METRICS_SCHEMA = 2

# `net_debt` was MISSING from this tuple, so it alone was emitted in the provider's native
# units (millions) while market_cap, ev and total_debt beside it were scaled to dollars.
# fairvalue.py's EV bridge then computed `ev = market_cap + net_debt` as dollars + millions,
# which makes the net-debt term ~1e-6 of its true size and silently collapses the bridge to
# a bare re-rate. CHTR's real net debt / market cap is 4.68; the lens saw 96,644 against
# 20.6 billion. Same class as the P7 currency bug: every column present, every column
# populated, one of them in the wrong unit.
_ABSOLUTE_USD = ("market_cap", "revenue", "net_income", "operating_income", "fcf",
                 "ebitda", "ev", "gross_profit", "total_debt", "total_equity",
                 "interest_expense", "net_debt")


def _stamp_units(m: dict, scale: float = 1.0) -> dict:
    """Scale the absolute currency figures to USD dollars and record the convention."""
    if scale != 1.0:
        for k in _ABSOLUTE_USD:
            v = m.get(k)
            if v is not None:
                m[k] = v * scale
    m["units"] = METRICS_UNITS
    m["schema"] = METRICS_SCHEMA
    return m


#: The three momentum inputs. A cached row carrying NONE of them is not fit to serve -- see
#: `_usable_cache`. Named here rather than inline so the one list is shared.
_MOMENTUM_INPUTS = ("ret_12_1", "ret_6_1", "high_prox")


def _usable_cache(cached):
    """Drop cached fundamentals that are not fit to serve.

    Written before the USD normalization, on an older schema -- or, since item 54, carrying
    NONE of the three momentum inputs.

    **THE THIRD RULE IS WHY THE FIRST REPAIR DID NOT REACH ITS OWN NAMES.** Item 54 part 2 added
    a retry to the per-name free fetch, and the 2026-10-13 scan -- the first with it in place --
    still had `T`, `VZ`, `MGM`, `FDX` and `PFE` with no momentum at all: the very names item 53
    part 7 measured returning 400 sessions of history on demand. The retry was never reaching
    them, because `get_metrics` serves a cached row FIRST and the fundamentals cache runs to
    **30 days** -- so a row written by the broken scan was handed back unchanged, and would have
    been for a month.

    A row with no momentum is exactly the state the repair exists to end, so it is now a cache
    MISS and the name is fetched again. This is the same judgement the two rules above already
    make -- a cached row that is not fit for purpose is dropped rather than served -- applied to
    a third way of being unfit.

    **IT IS BOUNDED AND SELF-LIMITING.** Only the rows that lack momentum are re-fetched: 9 of
    the top 500 and ~30 of 1,456 on the scan measured. A name with genuinely too little history
    (`SUN`, 61 sessions) still returns `high_prox`, so it caches normally and is not re-fetched
    forever; a name that keeps failing is retried once per scan, which is the behaviour wanted.

    **NO SCORING RULE CHANGES** -- this decides whether a row is re-FETCHED, not how it is
    scored, which is the ruling's own line.
    """
    c = cached or {}
    if c.get("units") != METRICS_UNITS:
        return None
    if int(c.get("schema") or 1) < METRICS_SCHEMA:
        return None
    if not any(c.get(k) is not None for k in _MOMENTUM_INPUTS):
        return None
    return cached


def _redact(msg) -> str:
    """Strip API keys out of a message before it can be stored or served.

    `requests` puts the FULL request URL in its HTTPError text, query string included — so
    an unedited "FMP call failed" note carries the live apikey, and these notes are surfaced
    publicly in the scan's health block. Never widen what reaches that block without going
    through here.

    The implementation now lives in `valuation/safe_error.py` so every route, log line and
    provider shares ONE scrubber — this used to be a private helper called from four places
    in this file while 23 HTTP handlers returned raw exception text (SECURITY_AUDIT.md H2).
    Kept as a thin alias because it is the name the health-block call sites already use.
    """
    return redact(msg)


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
    name = "free (broker fundamentals + EDGAR/Yahoo/Stooq)"

    def __init__(self, cfg=CONFIG, store=None):
        self.cfg = cfg
        self.store = store
        self.universe_note = ""
        # Broker fundamentals, bulk-loaded once per scan by prefetch(). None means "never
        # attempted", an empty dict means "attempted and got nothing" — the two are reported
        # differently so a broken token is not mistaken for a feed with no coverage.
        self._broker_raw: Optional[dict] = None
        self._broker_note = ""
        self._broker_hits = 0
        #: ITEM 54 part 2: one tuple per free fetch -- (ticker, attempts, ok, recovered,
        #: degraded, why). Bounded in practice by the universe size, and read by
        #: `refetch_detail`.
        self._free_reports: list = []
        self._broker_only = 0
        # get_metrics runs on a thread pool (scan_workers, default 8) and these counters are
        # reported in the health block — an unsynchronized += drops updates and understates
        # the very coverage number this change exists to establish.
        self._lock = _threading.Lock()

    # ----------------------------------------------------------------- #
    # Bulk fundamentals prefetch (the free route — see broker_fundamentals.py)
    # ----------------------------------------------------------------- #
    def prefetch(self, tickers) -> dict:
        """Bulk-load broker fundamentals for the whole universe in ~3 calls per 100 names.

        Optional by contract: run_scan calls this only if the provider defines it, so a
        provider without it (or a run with no TRADIER_TOKEN) behaves exactly as before.
        """
        from . import broker_fundamentals as BF
        if not BF.available(self.cfg):
            self._broker_raw = {}
            self._broker_note = "no TRADIER_TOKEN — broker fundamentals unavailable"
            return {}
        try:
            self._broker_raw = BF.fetch_raw(list(tickers), self.cfg)
            got = len((self._broker_raw or {}).get("company") or {})
            self._broker_note = f"broker fundamentals loaded for {got} of {len(tickers)} names"
        except Exception as e:
            self._broker_raw = {}
            self._broker_note = f"broker fundamentals failed ({_redact(e)})"
        return self._broker_raw or {}

    def _broker_metrics(self, ticker: str):
        if not self._broker_raw:
            return None
        from . import broker_fundamentals as BF
        try:
            return BF.to_metrics(ticker, self._broker_raw)
        except Exception:
            return None

    @property
    def broker_stats(self) -> dict:
        # ITEM 44. THESE COUNT *THIS RUN'S* PREFETCH AND NOTHING ELSE, and saying so is the
        # whole point of the extra key. The live health block reads
        # `names_with_broker_data: 0` and `note: "broker fundamentals loaded for 0 of 1500
        # names"` directly beside `by_source: {"free+broker": 777}` -- which reads as a
        # contradiction and cost a lane an afternoon's wrong conclusion ("the broker half is
        # gone").
        #
        # Both are right and they count DIFFERENT POPULATIONS. `get_metrics` returns a CACHED
        # row before it ever consults the broker, and `merge` stamps `free+broker` only when
        # the broker actually filled a field -- so with an empty prefetch no row scored TODAY
        # can carry that label, and the 777 that do were stamped on an earlier run when the
        # prefetch worked. `O-1`'s family: a count measured on one population read as a fact
        # about another.
        return {"note": self._broker_note, "names_with_broker_data": self._broker_hits,
                "names_broker_only": self._broker_only,
                "scope": "this run's prefetch only; names already in the fundamentals cache "
                         "keep their earlier broker fields and still count under "
                         "by_source['free+broker']"}

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

    @property
    def _retry_budget(self):
        """One budget for the whole scan, created on first use.  [item 54 part 2]

        Per-provider rather than per-name, because the thing being bounded is the scan's wall
        clock and the far end's patience, neither of which is per-name.
        """
        with self._lock:
            b = getattr(self, "_rb", None)
            if b is None:
                from .refetch import RetryBudget
                b = self._rb = RetryBudget()
        return b

    def refetch_detail(self) -> dict:
        """What the retry did, for the scan's health block.  [item 54 part 2]

        **THE COUNTS ARE THE POINT.** A rescue nobody can see is indistinguishable from a scan
        that never needed one, and a degraded payload that was discarded has to be reported or
        the reader cannot tell it from a name that simply has no data.
        """
        b = getattr(self, "_rb", None)
        out = {"ran": b is not None}
        if b is None:
            return out
        out.update(b.detail())
        with self._lock:
            reps = list(getattr(self, "_free_reports", []))
        out["names_fetched"] = len(reps)
        out["names_retried"] = sum(1 for r in reps if r[1] > 1)
        out["names_recovered_by_retry"] = sum(1 for r in reps if r[3])
        out["names_degraded_discarded"] = sum(1 for r in reps if r[4])
        out["names_failed"] = sum(1 for r in reps if not r[2])
        # A bounded sample, so a reader can see WHY rather than only how many.
        out["failure_sample"] = [{"ticker": r[0], "why": r[5]}
                                 for r in reps if not r[2]][:5]
        out["recovered_sample"] = [r[0] for r in reps if r[3]][:10]
        return out

    def get_metrics(self, ticker: str) -> Optional[dict]:
        # cached?
        if self.store:
            cached = _usable_cache(
                self.store.get_cached_fundamentals(ticker, max_age_days=self.cfg_max_age()))
            if cached:
                return cached

        from . import broker_fundamentals as BF
        broker = self._broker_metrics(ticker)

        # The per-name free fetch (yfinance `.info` + EDGAR) is the ONLY free source for the
        # flow items the broker has no table for — operating income, gross profit, FCF,
        # interest expense, revenue growth. It is also slow and aggressively rate-limited from
        # a cloud IP, and when it fails it returns nothing at all. Before the broker prefill
        # that meant the name was DROPPED from the scan entirely ("no data"); now it survives
        # on the broker's half, so a throttled Yahoo costs the scan some quality per name
        # instead of costing it the name.
        # ITEM 54 PART 2 — IT GETS A SECOND ATTEMPT, AND A DEGRADED ANSWER IS NOT ACCEPTED.
        # The single attempt above is what left `T`, `VZ`, `MGM`, `RNR`, `NVDA` and `KO` with
        # no momentum in the live scan while all six return 400 sessions of history on demand.
        # The retry is PACED and drawn from a scan-wide budget, and a throttled payload is
        # DISCARDED rather than merged -- see `refetch.py` for the measured tells (price and
        # market cap both absent drives the WACC to the after-tax cost of debt exactly).
        #
        # A currency mismatch is still handled, and still not retried: it is a fact about the
        # filing, so a second attempt returns the same thing.
        free = None
        try:
            from ..data import fetcher
            from .refetch import fetch_free
            rep = fetch_free(ticker, self.cfg, get_company=fetcher.get_company,
                             get_quote=P.get_quote, budget=self._retry_budget)
            with self._lock:
                self._free_reports.append(
                    (rep["ticker"], rep["attempts"], rep["ok"], rep["recovered"],
                     rep["degraded"], rep["why"][:120]))
            if rep["ok"]:
                free = company_to_metrics(rep["cd"], rep["quote"])
        except Exception:
            free = None

        m = BF.merge(broker, free)
        if m is None:
            return None
        if broker is not None:
            with self._lock:
                self._broker_hits += 1
                if free is None:
                    self._broker_only += 1
        m.setdefault("ticker", ticker.upper())
        m["units"] = METRICS_UNITS
        m["schema"] = METRICS_SCHEMA
        if self.store:
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

    def prefetch(self, tickers) -> dict:
        """Delegate the bulk broker prefetch to the free stack behind this provider.

        On the current FMP subscription almost every per-symbol call 402s and the circuit
        breaker hands the whole universe to the free stack, so the fallback path is the hot
        path — it needs the broker prefill more than the FMP path does, not less.
        """
        return self._free_provider().prefetch(tickers)

    def _free_provider(self) -> "FreeProvider":
        if not self._free:
            self._free = FreeProvider(self.cfg, None)      # no store: we cache below
        return self._free

    @property
    def broker_stats(self) -> dict:
        return self._free.broker_stats if self._free else {}

    def _free_fallback(self, ticker: str) -> Optional[dict]:
        m = self._free_provider().get_metrics(ticker)
        if m is not None:
            with self._lock:
                self._served_free += 1
        return m


def served_by(health: dict, configured: str) -> dict:
    """What actually served this scan's fundamentals, derived from the census.

    E8 -- THE HEADER NAMED THE CONFIGURED VENDOR AND THE CENSUS SAID IT SERVED NOTHING,
    AND BOTH WERE IN THE SAME PAYLOAD, ONE KEY APART. `screen.run` returned
    `provider: provider.name` -- a fact about CONFIGURATION -- while the `health` dict beside
    it recorded `api_budget.served_by_fmp: 0`, `fmp_disabled_mid_scan: true` and a 402 Payment
    Required in `fmp_error_sample`. So the hot list's meta line read "Financial Modeling Prep"
    for a scan in which Financial Modeling Prep served zero names, and the evidence for that
    was already on the page's own API response.

    This is the family this project keeps meeting: a label a surface can state without
    consulting the measurement beside it. `hero.py` records the sharpest version -- a payload
    that honestly set `source: "paper-sandbox"` while the template never rendered it, and the
    lesson drawn there was that "a label that a surface can decline to show is not a
    safeguard". The inverse is this one: a label that is never asked to agree with the census
    is not a measurement, however honest the census is.

    SO THE LABEL IS DERIVED AND THE CONFIGURED NAME TRAVELS BESIDE IT RATHER THAN BEING
    REPLACED. A reader who wants to know what was MEANT to serve the scan is asking a real
    question, and the two answers differing is exactly the thing worth seeing.

    DEGRADES TO THE CONFIGURED NAME, LABELLED AS SUCH. With no census -- an old snapshot, a
    provider that keeps no counters -- this cannot know what served, and saying so is better
    than either inventing a source or showing nothing. `measured` is False in that state, so a
    surface can tell a measurement from a default.
    """
    out = {"label": configured, "configured": configured, "measured": False,
           "degraded": False, "counts": {}, "reason": None}
    # `isinstance` on BOTH levels, not just the outer one. A snapshot's `params` blob is
    # whatever was written months ago, so `api_budget` can legitimately be absent, None, or --
    # as a malformed-input test found -- a string. A label must not take down the hot list.
    b = (health or {}).get("api_budget") if isinstance(health, dict) else None
    if not isinstance(b, dict) or not b:
        out["reason"] = "this scan kept no source census, so the configured provider is named"
        return out

    fmp = int(b.get("served_by_fmp") or 0)
    free = int(b.get("served_by_free_fallback") or 0)
    off = bool(b.get("fmp_disabled_mid_scan"))
    fund = (health or {}).get("fundamentals")
    broker = fund.get("broker") if isinstance(fund, dict) else None
    bro = int((broker or {}).get("names_with_broker_data") or 0) \
        if isinstance(broker, dict) else 0

    out["measured"] = True
    out["counts"] = {"fmp": fmp, "free_fallback": free, "names_with_broker_data": bro,
                     "fmp_disabled_mid_scan": off, "fmp_errors": int(b.get("fmp_errors") or 0)}

    # A cache hit is served by NEITHER counter, so the counts need not sum to the scan size and
    # this must not try to make them: `get_metrics` returns a cached row before it touches
    # either path. What the counts do establish is which LIVE routes ran.
    if fmp and free:
        out["label"] = "%s + %s" % (configured, FreeProvider.name)
        out["degraded"] = True
        out["reason"] = ("%d name(s) served by %s and %d by the free stack"
                         % (fmp, configured, free))
    elif fmp:
        out["label"] = configured
        out["reason"] = "%d name(s) served by %s" % (fmp, configured)
    elif free or bro:
        # The case that was on the live site. Naming the configured vendor here is the defect.
        out["label"] = FreeProvider.name
        out["degraded"] = True
        why = "served no names"
        if off:
            why = "was disabled mid-scan"
        out["reason"] = ("%s %s, so every live name came from the free stack" % (configured, why))
    else:
        out["label"] = "cache"
        out["reason"] = ("no live fundamentals call was served this scan; every name came "
                         "from cache")
    return out


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
