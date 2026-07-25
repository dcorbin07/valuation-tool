"""
yfinance adapter — the primary (free, no-key) data source.

yfinance scrapes Yahoo Finance, whose row labels and availability vary by
ticker and change over time, so every field is looked up defensively with
multiple candidate labels and safe fallbacks. Nothing here raises on a missing
field; instead it records a data-quality note and moves on.

Fundamentals use the most recent reported fiscal year (like the Nike model's
FY2025 base year); market data (price, shares, beta) is live.
"""
from __future__ import annotations

from typing import Optional
import datetime as _dt

from .models import CompanyData, _safe


# ---------------------------------------------------------------------------
# DataFrame helpers (yfinance returns statements as row=line-item, col=date)
# ---------------------------------------------------------------------------
def _pick_row(df, candidates):
    """Return the first matching row (as a Series) or None.

    Match is case-insensitive: first try exact, then 'startswith', then
    'contains' so we tolerate Yahoo's label drift.
    """
    if df is None or getattr(df, "empty", True):
        return None
    index = {str(i).strip().lower(): i for i in df.index}
    keys = list(index.keys())
    for cand in candidates:
        c = cand.lower()
        if c in index:
            return df.loc[index[c]]
    for cand in candidates:
        c = cand.lower()
        for k in keys:
            if k.startswith(c):
                return df.loc[index[k]]
    for cand in candidates:
        c = cand.lower()
        for k in keys:
            if c in k:
                return df.loc[index[k]]
    return None


def _sorted_cols(df):
    """Columns (period ends) sorted most-recent-first."""
    if df is None or getattr(df, "empty", True):
        return []
    try:
        return list(sorted(df.columns, reverse=True))
    except Exception:
        return list(df.columns)


def _latest(row, cols):
    if row is None:
        return None
    for c in cols:
        try:
            v = _safe(row.get(c))
        except Exception:
            v = None
        if v is not None:
            return v
    return None


def _history(row, cols, n=6):
    out = []
    if row is None:
        return out
    for c in cols:
        try:
            out.append(_safe(row.get(c)))
        except Exception:
            out.append(None)
        if len(out) >= n:
            break
    return out


def _mm(x):
    """Absolute currency -> millions."""
    v = _safe(x)
    return None if v is None else v / 1e6


def fetch(ticker: str) -> Optional[CompanyData]:
    """Fetch and normalize a company from Yahoo Finance. Returns None on hard failure."""
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance is not installed. Run: pip install -r requirements.txt")

    t = yf.Ticker(ticker)
    cd = CompanyData(ticker=ticker.upper(), as_of=_dt.date.today().isoformat())
    cd.sources.append("Yahoo Finance (yfinance)")

    # ---- info dict (rich but occasionally flaky/slow) ----
    info = {}
    try:
        info = t.info or {}
    except Exception:
        cd.quality_notes.append("Yahoo `info` unavailable; used fast_info + statements only.")

    fast = {}
    try:
        fast = dict(t.fast_info)
    except Exception:
        fast = {}

    cd.name = info.get("longName") or info.get("shortName") or ticker.upper()
    cd.sector = info.get("sector") or ""
    cd.industry = info.get("industry") or ""
    cd.currency = info.get("currency") or fast.get("currency") or "USD"
    cd.quote_type = (info.get("quoteType") or "").upper()

    # ---- price / shares / market cap / beta ----
    cd.price = _safe(info.get("currentPrice") or info.get("regularMarketPrice") or fast.get("lastPrice"))
    shares = _safe(info.get("sharesOutstanding") or fast.get("shares"))
    cd.shares_diluted = None if shares is None else shares / 1e6
    cd.market_cap = _mm(info.get("marketCap") or fast.get("marketCap"))
    cd.beta = _safe(info.get("beta"))
    cd.analyst_target_price = _safe(info.get("targetMeanPrice"))

    # ---- statements ----
    inc = bal = cf = None
    try:
        inc = t.income_stmt
    except Exception:
        pass
    try:
        bal = t.balance_sheet
    except Exception:
        pass
    try:
        cf = t.cashflow
    except Exception:
        pass

    ic = _sorted_cols(inc)
    bc = _sorted_cols(bal)
    fc = _sorted_cols(cf)

    # Fiscal-year labels from income statement columns
    cd.fiscal_years = [getattr(c, "year", str(c)) for c in ic[:6]]

    # Revenue
    rev_row = _pick_row(inc, ["Total Revenue", "Operating Revenue", "Revenue"])
    cd.revenue = _mm(_latest(rev_row, ic))
    cd.revenue_history = [_mm(v) for v in _history(rev_row, ic)]

    # EBIT / Operating income
    ebit_row = _pick_row(inc, ["EBIT", "Operating Income", "Total Operating Income As Reported"])
    cd.ebit = _mm(_latest(ebit_row, ic))
    cd.ebit_history = [_mm(v) for v in _history(ebit_row, ic)]

    # Gross profit
    gp_row = _pick_row(inc, ["Gross Profit"])
    cd.gross_profit = _mm(_latest(gp_row, ic))
    if cd.gross_profit is None:
        cogs_row = _pick_row(inc, ["Cost Of Revenue", "Cost Of Goods Sold", "Reconciled Cost Of Revenue"])
        cogs = _mm(_latest(cogs_row, ic))
        if cd.revenue is not None and cogs is not None:
            cd.gross_profit = cd.revenue - cogs

    # Net income
    ni_row = _pick_row(inc, ["Net Income", "Net Income Common Stockholders",
                             "Net Income Continuous Operations"])
    cd.net_income = _mm(_latest(ni_row, ic))
    cd.net_income_history = [_mm(v) for v in _history(ni_row, ic)]

    # Effective tax rate = Tax Provision / Pretax Income
    tax_row = _pick_row(inc, ["Tax Provision", "Income Tax Expense"])
    pretax_row = _pick_row(inc, ["Pretax Income", "Income Before Tax"])
    tax = _latest(tax_row, ic)
    pretax = _latest(pretax_row, ic)
    if tax is not None and pretax not in (None, 0) and pretax > 0:
        cd.effective_tax_rate = max(0.0, min(0.45, tax / pretax))

    # Interest expense
    int_row = _pick_row(inc, ["Interest Expense", "Interest Expense Non Operating", "Net Interest Income"])
    ie = _latest(int_row, ic)
    cd.interest_expense = None if ie is None else abs(_mm(ie))

    # EBIT margin history
    cd.ebit_margin_history = []
    for e, r in zip(cd.ebit_history, cd.revenue_history):
        if e is not None and r not in (None, 0):
            cd.ebit_margin_history.append(e / r)
        else:
            cd.ebit_margin_history.append(None)

    # ---- balance sheet ----
    debt_row = _pick_row(bal, ["Total Debt"])
    cd.total_debt = _mm(_latest(debt_row, bc))
    if cd.total_debt is None:
        ltd = _mm(_latest(_pick_row(bal, ["Long Term Debt"]), bc)) or 0.0
        cur = _mm(_latest(_pick_row(bal, ["Current Debt", "Current Debt And Capital Lease Obligation"]), bc)) or 0.0
        if ltd or cur:
            cd.total_debt = ltd + cur

    cash_row = _pick_row(bal, ["Cash Cash Equivalents And Short Term Investments",
                               "Cash And Cash Equivalents"])
    cd.cash_sti = _mm(_latest(cash_row, bc))

    eq_row = _pick_row(bal, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"])
    cd.total_equity = _mm(_latest(eq_row, bc))

    ic_row = _pick_row(bal, ["Invested Capital"])
    cd.invested_capital = _mm(_latest(ic_row, bc))
    if cd.invested_capital is None:
        # Approx: total debt + book equity - cash (a standard proxy)
        parts = [cd.total_debt, cd.total_equity]
        if all(p is not None for p in parts):
            cd.invested_capital = cd.total_debt + cd.total_equity - (cd.cash_sti or 0.0)

    # ---- cash flow ----
    da_row = _pick_row(cf, ["Depreciation And Amortization", "Depreciation Amortization Depletion",
                            "Depreciation"])
    cd.da = _mm(_latest(da_row, fc))
    if cd.da is None:
        cd.da = _mm(_latest(_pick_row(inc, ["Reconciled Depreciation"]), ic))

    capex_row = _pick_row(cf, ["Capital Expenditure", "Purchase Of PPE"])
    cx = _latest(capex_row, fc)
    cd.capex = None if cx is None else abs(_mm(cx))

    fcf_row = _pick_row(cf, ["Free Cash Flow"])
    cd.fcf = _mm(_latest(fcf_row, fc))
    if cd.fcf is None:
        ocf = _mm(_latest(_pick_row(cf, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"]), fc))
        if ocf is not None and cd.capex is not None:
            cd.fcf = ocf - cd.capex
    cd.fcf_history = []
    if fcf_row is not None:
        cd.fcf_history = [_mm(v) for v in _history(fcf_row, fc)]

    # ---- analyst estimates (best-effort) ----
    try:
        ge = t.growth_estimates
        if ge is not None and not ge.empty:
            # look for next-year revenue/eps growth
            for label in ["+1y", "1y", "next year"]:
                if label in [str(i).lower() for i in ge.index]:
                    idx = [i for i in ge.index if str(i).lower() == label][0]
                    val = _safe(ge.loc[idx].iloc[0])
                    if val is not None:
                        cd.analyst_rev_growth_next = val
                        break
    except Exception:
        pass
    if cd.analyst_rev_growth_next is None:
        rg = _safe(info.get("revenueGrowth"))
        if rg is not None:
            cd.analyst_rev_growth_next = rg

    # ---- price history / momentum (best-effort) ----
    try:
        hist = t.history(period="1y", interval="1d")
        if hist is not None and not hist.empty:
            closes = hist["Close"].dropna()
            if len(closes) > 0:
                last = float(closes.iloc[-1])
                if cd.price is None:
                    cd.price = last
                cd.price_52w_high = float(closes.max())
                cd.price_52w_low = float(closes.min())
                if len(closes) >= 200:
                    cd.ma_200 = float(closes.iloc[-200:].mean())
                else:
                    cd.ma_200 = float(closes.mean())
                if len(closes) >= 126:
                    cd.ret_6m = last / float(closes.iloc[-126]) - 1.0
                if len(closes) >= 21:
                    cd.ret_1m = last / float(closes.iloc[-21]) - 1.0
    except Exception:
        pass

    # ---- final sanity flags ----
    if cd.price is None:
        cd.quality_notes.append("No live price found — valuation upside/score may be unreliable.")
    if cd.revenue is None:
        cd.quality_notes.append("No revenue found on Yahoo — try SEC EDGAR or another ticker format.")
    if cd.shares_diluted is None and cd.market_cap and cd.price:
        cd.shares_diluted = cd.market_cap / cd.price  # implied

    return cd
