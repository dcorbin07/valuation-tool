"""
Live fundamentals from the BROKER (Tradier's Morningstar-backed `beta/markets/fundamentals`).

Why this exists: FMP is on the free Basic tier — 250 calls/day and no fundamentals — so the
live hot score cannot lean on it, and the per-name free stack (yfinance/EDGAR) is slow and
heavily rate-limited from a cloud IP. Tradier is already paid for and has no such limit:

  * `beta/markets/fundamentals/{company,ratios,financials,statistics}`
  * up to **100 symbols per call** (verified 2026-08-02; 200 returns a non-JSON error body),
    so the whole 800-name universe costs ~32 calls instead of FMP's ~2,400.

WHAT IS ACTUALLY IN THERE — measured on 200 liquid names, 2026-08-02, not assumed. Tradier
returns a large envelope in which MOST tables are null; the populated ones are:

    share_class_profile   market_cap 99%, enterprise_value 99%, shares_outstanding 99%
    valuation_ratios      book_value_per_share 99%, p_s 98.5%, p_b 91.5%, p_e 88%,
                          ev_to_ebitda 83.5%
    operation_ratios      r_o_a 95.5%, r_o_e 89.5%, total_debt_equity_ratio 87.5%
    alpha_beta            beta 99%
    ownership_summary     13F + insider tallies, 99%
    historical_asset_classification  morningstar_sector_code 99%

and these are null for EVERY symbol, on every plan tier we can reach:

    financial_statements_restate, segmentation, earning_reports_restate, historical_returns,
    operation_ratios_restate, earning_ratios_restate, trailing_returns, asset_classification

That second list is the important one: there is **no income statement and no balance sheet**
here — no revenue, no operating income, no gross profit, no FCF, no interest expense, and no
revenue growth. So the flow-derived factors (`op_margin`, `gross_margin`, `fcf_yield`,
`ebit_ev`, `roic`, `revenue_growth`, `interest_cov`, `f_score`) have NO free broker source and
still need the per-name free stack. See DERIVED below for what we can reconstruct anyway, and
HANDOFF_appfixes.md for the field-by-field verdict.

DERIVED, not reported. Morningstar gives ratios rather than line items, so several absolute
figures are reconstructed by inverting a ratio against market cap:

    revenue      = market_cap / p_s_ratio
    net_income   = market_cap / p_e_ratio        (positive earnings only — see below)
    total_equity = book_value_per_share * shares_outstanding
    ebitda       = enterprise_value / ev_to_ebitda
    net_debt     = enterprise_value - market_cap
    total_debt   = total_debt_equity_ratio * total_equity

These are arithmetic identities, not estimates, but they inherit the ratio's as-of date
(month-end) while market cap is same-day, so a fast-moving name's derived revenue can be a few
percent off the filed figure. They are used only where the free stack has nothing — a REPORTED
value always wins over a derived one (see `merge`).

**A loss-making company has no P/E**, so `net_income` comes back None rather than negative for
roughly 12% of the universe. That is deliberate and it degrades correctly: `classify_bucket`
reads a missing profit as "speculative", which is the right bucket for a loss-maker. Do NOT
"fix" this by treating a null P/E as zero earnings.

Units: every absolute figure here is already USD dollars, matching providers.METRICS_UNITS.
Tradier reports market cap in dollars (AAPL 4.537e12 = 14.687e9 shares x $308.91 — verified),
so nothing is scaled on the way out.
"""
from __future__ import annotations

from typing import Optional

from ..config import CONFIG

BASE = "https://api.tradier.com/beta"
CHUNK = 100               # symbols per call; 200 returns a non-JSON error body
TIMEOUT = 120

# The four endpoints worth calling. `statistics` is deliberately NOT among them: its only
# populated table is price_statistics (average volume, 52-week high/low), and the scan
# already gets all three from the free batched `markets/quotes` in broker_universe.
ENDPOINTS = ("company", "ratios", "financials")

# Morningstar sector codes -> the sector NAMES the rest of the app already uses. Verified
# against engine/comps.SECTOR_MULTIPLES: all eleven match exactly, so a broker-sourced sector
# lands straight in the peer-median lookup and the fair-value comps rather than falling to the
# generic default. Spot-checked 2026-08-02: AAPL/MSFT/NVDA 311, XOM/CVX 309, JPM 103, UNH 206,
# WMT/KO 205, NEE 207, BA 310, GOOGL 308, LIN 101, F 102.
SECTOR_CODES = {
    101: "Basic Materials", 102: "Consumer Cyclical", 103: "Financial Services",
    104: "Real Estate", 205: "Consumer Defensive", 206: "Healthcare",
    207: "Utilities", 308: "Communication Services", 309: "Energy",
    310: "Industrials", 311: "Technology",
}

# Beta lookback preference. Morningstar publishes 36/48/60-month betas; 60m is the most
# stable and is what the low-risk theme was measured on.
BETA_PERIODS = ("period_60m", "period_48m", "period_36m")


def available(cfg=CONFIG) -> bool:
    return bool(getattr(cfg, "tradier_token", ""))


def _headers(cfg) -> dict:
    return {"Authorization": f"Bearer {cfg.tradier_token}", "Accept": "application/json"}


def _f(x) -> Optional[float]:
    """A usable FINITE float, else None. NaN and +/-inf are missing, not values."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def _pos(x) -> Optional[float]:
    """A strictly positive float, else None — for values used as a DIVISOR."""
    v = _f(x)
    return v if (v is not None and v > 0) else None


def fetch_raw(tickers, cfg=CONFIG, session=None) -> dict:
    """{endpoint: {TICKER: [result blocks]}} for every requested endpoint, batched.

    A failed chunk is skipped rather than aborting the sweep: partial fundamentals for most
    of the universe beats none for all of it, and the caller reports coverage either way.
    """
    import requests
    s = session or requests.Session()
    tickers = [t for t in tickers if t]
    out: dict = {ep: {} for ep in ENDPOINTS}
    for ep in ENDPOINTS:
        for i in range(0, len(tickers), CHUNK):
            chunk = tickers[i:i + CHUNK]
            try:
                r = s.get(f"{BASE}/markets/fundamentals/{ep}",
                          params={"symbols": ",".join(chunk)},
                          headers=_headers(cfg), timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for entry in data:
                sym = (entry.get("request") or "").upper()
                if sym:
                    out[ep].setdefault(sym, []).extend(entry.get("results") or [])
    return out


def _tables(results, name):
    """Every non-null instance of table `name` across a symbol's result blocks.

    Tradier returns several result blocks per symbol (Company, and one Stock block per share
    class), and the same table can appear in more than one with different content — AAPL
    carries two betas under two share-class ids. Yielding all of them lets the callers below
    take the first usable value in a defined order instead of depending on block ordering.
    """
    for res in results or []:
        t = (res.get("tables") or {}).get(name)
        if t is not None:
            yield t


def _first(results, table, *path):
    """First non-null value at `path` inside any instance of `table`."""
    for t in _tables(results, table):
        blocks = t if isinstance(t, list) else [t]
        for blk in blocks:
            cur = blk
            for key in path:
                if not isinstance(cur, dict):
                    cur = None
                    break
                cur = cur.get(key)
            if cur is not None:
                return cur
    return None


def _beta(results) -> Optional[float]:
    for period in BETA_PERIODS:
        v = _f(_first(results, "alpha_beta", period, "beta"))
        if v is not None:
            return v
    return None


def _roe(results) -> Optional[float]:
    """Trailing-twelve-month ROE.

    Morningstar publishes the same ratio over 3M / 9M / 1Y windows in one table, and the 3M
    figure is a QUARTERLY return on equity — about a quarter of the annual one (AAPL 0.278 vs
    1.488). Mixing the two across a cross-section would make ROE a coin flip on which window a
    given name happened to report, so only the 1Y/TTM window is accepted.
    """
    for t in _tables(results, "operation_ratios_a_o_r"):
        blocks = t if isinstance(t, list) else [t]
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            for period in ("period_1y", "period_12m"):
                p = blk.get(period)
                if isinstance(p, dict) and p.get("r_o_e") is not None:
                    return _f(p["r_o_e"])
    return None


def _debt_to_equity(results) -> Optional[float]:
    for t in _tables(results, "operation_ratios_a_o_r"):
        blocks = t if isinstance(t, list) else [t]
        for blk in blocks:
            if not isinstance(blk, dict):
                continue
            for period in ("period_1y", "period_3m", "period_9m", "period_12m"):
                p = blk.get(period)
                if isinstance(p, dict) and p.get("total_debt_equity_ratio") is not None:
                    return _f(p["total_debt_equity_ratio"])
    return None


def to_metrics(ticker: str, raw: dict) -> Optional[dict]:
    """Map one symbol's raw broker payload to the screener metrics contract.

    Returns None when the symbol has no market cap — without it nothing downstream works
    (the size theme, the large-cap floor and every derived absolute all need it), so a row
    that thin is better handled by the free stack.
    """
    tkr = (ticker or "").upper()
    comp = (raw.get("company") or {}).get(tkr) or []
    rat = (raw.get("ratios") or {}).get(tkr) or []

    mc = _pos(_first(comp, "share_class_profile", "market_cap"))
    if mc is None:
        return None
    # Enterprise value is reported as exactly 0 for banks — a "not applicable" sentinel, not a
    # measurement. Verified 2026-08-02: of 200 liquid names, 11 carry ev == 0 and ALL ELEVEN are
    # Financial Services (JPM, BAC, WFC, GS, MS, C, SCHW, AXP, COF, NU, SOFI); no other sector
    # has one and none is negative. Taken literally it would set net_debt = -market_cap and
    # ev_sales = 0, i.e. hand every large bank the cheapest possible EV/Sales in the universe
    # and peg the whole sector to the top of the value theme. Treat it as MISSING: the EV-based
    # ratios then drop out for banks and they are ranked on earnings yield / book / sales, which
    # is how a bank should be valued anyway (engine.comps already zeroes their EV multiples).
    ev = _pos(_first(comp, "share_class_profile", "enterprise_value"))
    shares = _pos(_first(comp, "share_class_profile", "shares_outstanding")) \
        or _pos(_first(comp, "ownership_summary", "shares_outstanding"))

    pe = _pos(_first(rat, "valuation_ratios", "p_e_ratio"))
    ps = _pos(_first(rat, "valuation_ratios", "p_s_ratio"))
    pb = _pos(_first(rat, "valuation_ratios", "p_b_ratio"))
    ev_ebitda = _pos(_first(rat, "valuation_ratios", "e_v_to_e_b_i_t_d_a"))
    bvps = _f(_first(rat, "valuation_ratios", "book_value_per_share"))

    # --- derived absolutes (see module docstring) ---
    revenue = (mc / ps) if ps else None
    net_income = (mc / pe) if pe else None          # None for loss-makers: no P/E is published
    # Book equity: prefer bvps x shares (99% / 99% coverage) over market_cap / p_b (91.5%),
    # and keep the sign — a negative book value is real information, not a missing one.
    total_equity = (bvps * shares) if (bvps is not None and shares) else \
                   ((mc / pb) if pb else None)
    ebitda = (ev / ev_ebitda) if (ev is not None and ev_ebitda) else None
    net_debt = (ev - mc) if ev is not None else None
    d_to_e = _debt_to_equity(rat)
    total_debt = (d_to_e * total_equity) if (d_to_e is not None and total_equity is not None
                                             and total_equity > 0) else None
    ev_sales = (ev / revenue) if (ev is not None and revenue) else None

    m = {
        "ticker": tkr,
        "name": "",            # the broker universe listing carries the company name
        "sector": SECTOR_CODES.get(
            _first(comp, "historical_asset_classification", "morningstar_sector_code"), ""),
        "industry": "",
        "price": None,         # from the quote feed, not fundamentals
        "market_cap": mc, "ev": ev, "net_debt": net_debt,
        "revenue": revenue, "net_income": net_income, "ebitda": ebitda,
        "total_equity": total_equity, "total_debt": total_debt,
        "earnings_yield": (1.0 / pe) if pe else None,
        "pe": pe, "ps": ps,
        "ev_ebitda": ev_ebitda, "ev_sales": ev_sales,
        "book_to_price": (total_equity / mc) if (total_equity is not None) else None,
        "roe": _roe(rat),
        "net_debt_to_ebitda": (net_debt / ebitda) if (net_debt is not None and ebitda) else None,
        "beta": _beta(rat),
        "shares_outstanding": shares,
        # NOT AVAILABLE from this feed at any tier — listed explicitly so a reader can tell
        # "the broker has no source" apart from "the call failed". The free stack fills these.
        "operating_income": None, "fcf": None, "gross_profit": None, "interest_expense": None,
        "op_margin": None, "gross_margin": None, "fcf_yield": None, "ebit_ev": None,
        "roic": None, "revenue_growth": None, "revenue_growth_prior": None,
        "quote_type": "EQUITY", "is_fund": False,
        "units": "usd",
        "source": "broker",
    }
    return m


# Fields the broker genuinely reports or can derive. Anything outside this set is the free
# stack's job, and the coverage report keys off it — so adding a mapping above without adding
# it here would quietly understate what the broker now covers.
BROKER_FIELDS = ("market_cap", "ev", "net_debt", "revenue", "net_income", "ebitda",
                 "total_equity", "total_debt", "earnings_yield", "pe", "ps", "ev_ebitda",
                 "ev_sales", "book_to_price", "roe", "net_debt_to_ebitda", "beta", "sector")

# Fields with NO free broker source — the honest "would need paid fundamentals" list.
GAP_FIELDS = ("operating_income", "fcf", "gross_profit", "interest_expense", "op_margin",
              "gross_margin", "fcf_yield", "ebit_ev", "roic", "revenue_growth")


def merge(broker: Optional[dict], free: Optional[dict]) -> Optional[dict]:
    """Combine a broker row with a free-stack row. A REPORTED value always beats a derived one.

    The free stack (yfinance/EDGAR) reads actual filings, so where it has a real income
    statement its revenue / net income / equity are the filed figures and the broker's
    ratio-inverted reconstructions should not overwrite them. The broker wins only where the
    free stack came back empty — which, from a cloud IP under yfinance rate limiting, is most
    of the time.

    Either side may be None: a broker-only row is a partial but usable name, and a free-only
    row is exactly what the scan produced before this module existed.
    """
    if broker is None and free is None:
        return None
    if broker is None:
        out = dict(free)
        out.setdefault("source", "free")     # stamped even here, so `by_source` never says "unknown"
        return out
    if free is None:
        return dict(broker)

    out = dict(free)
    filled = []
    for k, v in broker.items():
        if k in ("source", "units", "ticker"):
            continue
        cur = out.get(k)
        # Treat "" as missing for the text fields and None as missing for the numerics.
        missing = cur is None or (isinstance(cur, str) and not cur.strip())
        if missing and v is not None and not (isinstance(v, str) and not v.strip()):
            out[k] = v
            filled.append(k)
    out["units"] = "usd"
    out["source"] = "free+broker" if filled else "free"
    out["broker_filled"] = filled
    return out


def coverage(rows) -> dict:
    """Per-field fill rate across a list of metrics dicts — the honest coverage report.

    Reported as three groups so the answer to "do we need to pay for fundamentals?" is
    legible: what the broker covers, what only the slow free stack can cover, and the fields
    nothing free supplies at all.
    """
    rows = [r for r in rows if r]
    n = len(rows) or 1

    def rate(field):
        return round(sum(1 for r in rows if r.get(field) is not None) / n, 3)

    by_source: dict = {}
    for r in rows:
        by_source[r.get("source") or "unknown"] = by_source.get(r.get("source") or "unknown", 0) + 1
    return {
        "names": len(rows),
        "by_source": by_source,
        "broker_fields": {f: rate(f) for f in BROKER_FIELDS},
        "gap_fields": {f: rate(f) for f in GAP_FIELDS},
    }
