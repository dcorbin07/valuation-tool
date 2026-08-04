"""
pit_data.py — build a POINT-IN-TIME panel for the edge backtest.

For each (ticker, rebalance date) it reconstructs the factors *as they were known
on that date* — using only SEC filings filed on/before the date, with the values as
reported then — and pairs them with the realized FORWARD return. This is the step
that removes fundamental look-ahead; getting it wrong is how most screener backtests
secretly cheat by using today's (restated, future) numbers to "predict" the past.

  raw_factors (oriented higher = better):
    ey       earnings yield  = net income / market cap        (value, cheaper = higher)
    roe      net income / shareholders' equity                (quality)
    opm      operating income / revenue                       (quality)
    neg_lev  -(net debt / EBITDA)                             (quality, less leverage = higher)
    growth   latest-vs-prior annual revenue growth            (growth)
    mom      12-1 month price return                          (momentum)

The cross-sectional standardization + weighting happens in run_backtest.py.

SURVIVORSHIP CAVEAT: forward returns come from a free price feed that only carries
names still listed today. Delisted losers are absent, so any edge will look better
than reality. This is a screen, not proof — confirm on survivorship-free data.
"""
import numpy as np
import pandas as pd
from datetime import date as _date

# us-gaap / dei concept tags (self-contained so this doesn't depend on edgar internals)
REV = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
       "RevenueFromContractWithCustomerIncludingAssessedTax", "SalesRevenueNet"]
NI = ["NetIncomeLoss", "ProfitLoss"]
OPINC = ["OperatingIncomeLoss"]
EQUITY = ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]
CASH = ["CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"]
LTD = ["LongTermDebtNoncurrent", "LongTermDebt"]
LTD_CUR = ["LongTermDebtCurrent"]
STD = ["ShortTermBorrowings", "DebtCurrent"]
DA = ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
      "DepreciationAndAmortization"]
SHARES = ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"]


def _units(facts, concept):
    f = facts.get("facts", {})
    for tax in ("us-gaap", "dei"):
        node = f.get(tax, {}).get(concept)
        if node:
            u = node.get("units", {})
            for k in ("USD", "shares", "USD/shares"):
                if k in u:
                    return u[k]
    return []


def _duration_days(e):
    """Length of the period this datapoint covers; None for instant facts."""
    start, end = e.get("start"), e.get("end")
    if not start or not end:
        return None
    try:
        return (_date.fromisoformat(end) - _date.fromisoformat(start)).days
    except (TypeError, ValueError):
        return None


def _pit_point(facts, concepts, as_of, kind="instant"):
    """
    Most recent value with filed <= as_of.

    THE BUG THIS FIXES — and it corrupted half the backtest.

    The original selected purely by (end, filed) and NEVER filtered on period
    duration. Flow concepts (net income, operating income) appear in
    companyfacts at 3, 6, 9 and 12-month durations, so after a 10-Q lands the
    "most recent" value is a QUARTERLY figure. Meanwhile `revenue` came from
    _pit_annual, which correctly restricts to FY. The code was therefore
    dividing a quarterly numerator by an annual denominator.

    Measured on a synthetic filer:

        as_of 2024-03-01 (only the FY2023 10-K known)   opm = 0.100
        as_of 2024-06-01 (Q1-2024 10-Q now known)       opm = 0.025

    A 4x drop with no change in the business. And because filers have
    staggered fiscal calendars, on any given rebalance date SOME names carry
    annual figures while others carry quarterly ones — a 4x scale difference
    WITHIN the same cross-section, which cross_sectional.zscore then dutifully
    standardizes as if it were signal. `ey`, `roe` and `opm` are three of the
    six factors and 50% of the backtest weight, so any IC measured on them was
    measuring fiscal-calendar timing.

    kind="instant" — balance-sheet items (equity, cash, debt). Point values,
                     no duration, take the latest.
    kind="ttm"     — flow items (income). Sums the last four QUARTERS when
                     they are available, else falls back to the latest annual
                     figure. Either way the window is twelve months for every
                     name on every date, which is what makes the ratios
                     comparable across the cross-section.

    (Sharadar's ART dimension gives this for free, which is one more reason to
    move the screener onto it — but the EDGAR path has to be correct until
    then, and the backtest reads this module today.)
    """
    as_of = str(as_of)
    if kind == "ttm":
        return _pit_ttm(facts, concepts, as_of)

    best = None  # (end, filed, val)
    for c in concepts:
        for e in _units(facts, c):
            filed, end = e.get("filed"), e.get("end")
            if not filed or not end or filed > as_of:
                continue
            if _duration_days(e) is not None:
                continue                      # a duration fact is not an instant
            key = (end, filed)
            if best is None or key > (best[0], best[1]):
                best = (end, filed, e.get("val"))
        if best:
            break
    return best[2] if best else None


def _pit_ttm(facts, concepts, as_of):
    """
    Trailing-twelve-month value for a FLOW concept, as known on `as_of`.

    Preference order:
      1. Four consecutive non-overlapping quarters ending at the latest known
         quarter — a true TTM, and the most current view available.
      2. The latest ANNUAL (~365-day) figure. Staler, but still a twelve-month
         window, so it stays comparable with every other name.

    Never mixes the two, and never returns a bare quarter.
    """
    for c in concepts:
        pts = []
        for e in _units(facts, c):
            filed, end, dur = e.get("filed"), e.get("end"), _duration_days(e)
            if not filed or not end or filed > as_of or dur is None:
                continue
            if e.get("val") is None:
                continue
            pts.append({"start": e["start"], "end": end, "dur": dur,
                        "filed": filed, "val": e["val"]})
        if not pts:
            continue

        quarters = [p for p in pts if 60 <= p["dur"] <= 120]
        annuals = [p for p in pts if 330 <= p["dur"] <= 400]

        # De-duplicate each period by latest filing (restatements win).
        def dedup(rows):
            out = {}
            for r in rows:
                k = (r["start"], r["end"])
                if k not in out or r["filed"] > out[k]["filed"]:
                    out[k] = r
            return sorted(out.values(), key=lambda r: r["end"], reverse=True)

        quarters, annuals = dedup(quarters), dedup(annuals)

        if len(quarters) >= 4:
            window, cursor = [], None
            for q in quarters:                    # newest first, walk backwards
                if cursor is None or q["end"] < cursor:
                    window.append(q)
                    cursor = q["start"]
                if len(window) == 4:
                    break
            if len(window) == 4:
                span = (_date.fromisoformat(window[0]["end"])
                        - _date.fromisoformat(window[-1]["start"])).days
                if 330 <= span <= 400:            # genuinely contiguous
                    return sum(q["val"] for q in window)

        if annuals:
            return annuals[0]["val"]
    return None


def _pit_annual(facts, concepts, as_of, n=2):
    """Latest `n` fiscal-year values known by as_of (uses latest filing for each year end)."""
    as_of = str(as_of)
    by_end = {}  # end -> (filed, val), keep latest filed
    for c in concepts:
        for e in _units(facts, c):
            filed, end, fp, form = e.get("filed"), e.get("end"), e.get("fp"), e.get("form", "")
            if not filed or not end or filed > as_of:
                continue
            if fp != "FY" or not (form.startswith("10-K") or form.startswith("20-F")):
                continue
            if end not in by_end or filed > by_end[end][0]:
                by_end[end] = (filed, e.get("val"))
        if by_end:
            break
    return [v for _, (_, v) in sorted(by_end.items(), reverse=True)[:n]]


def _pit_sum(facts, concept_lists, as_of):
    total, found = 0.0, False
    for cl in concept_lists:
        v = _pit_point(facts, cl, as_of)
        if v is not None:
            total += v; found = True
    return total if found else None


def point_in_time_factors(facts, price_asof, as_of):
    """
    Fundamental factors as known on as_of, given the price that day.

    Emits TWO overlapping views of the same numbers, deliberately:

      * the six oriented `raw_factors` (`ey`/`roe`/`opm`/`neg_lev`/`growth`/`mom`)
        that the panel's own cross-sectional composite consumes; and
      * the RAW line items under the names `scoring.score_stock` reads
        (`net_income`, `operating_income`, `total_debt`, `cash`, `revenue`,
        `op_margin`, `net_debt_to_ebitda`, `latest_rev_growth`,
        `prior_rev_growth`).

    The second group is what makes C1 possible: the LIVE scorer could not be
    replayed historically because nothing point-in-time ever produced its
    inputs. They are the same underlying values, so the two models are compared
    on identical data and any difference between them is the MODEL, not the
    feed. `op_margin` is `opm` and `net_debt_to_ebitda` is `-neg_lev` by
    construction, on purpose — do not "fix" one without the other.

    One definitional note, left alone on purpose: `opm` divides a TTM operating
    income by the latest ANNUAL revenue. Both are twelve-month windows so the
    scale is right (which is what the quarterly/annual bug was about), but they
    are not the SAME twelve months. Changing it would move the legacy model's
    factor and destroy the apples-to-apples C1 comparison, so it stays.
    """
    ni = _pit_point(facts, NI, as_of, kind="ttm")     # FLOW -> twelve months
    op = _pit_point(facts, OPINC, as_of, kind="ttm")  # FLOW -> twelve months
    eq = _pit_point(facts, EQUITY, as_of)
    cash = _pit_point(facts, CASH, as_of)
    shares = _pit_point(facts, SHARES, as_of)
    debt = _pit_sum(facts, [LTD, LTD_CUR, STD], as_of)
    da = _pit_point(facts, DA, as_of, kind="ttm")     # FLOW -> twelve months
    # THREE years, not two: the live `growth_score` takes a level AND an
    # acceleration, and acceleration needs the PRIOR year's growth, which needs
    # a third revenue observation. With only two the live model silently scored
    # every name on level alone.
    rev_hist = _pit_annual(facts, REV, as_of, 3)
    rev = rev_hist[0] if rev_hist else None

    mc = (shares * price_asof) if (shares and price_asof) else None
    ebitda = (op + da) if (op is not None and da is not None) else op
    net_debt = (debt or 0) - (cash or 0)

    def _yoy(a, b):
        return (a / b - 1) if (a is not None and b) else None

    opm = (op / rev) if (op is not None and rev and rev > 0) else None
    nd_ebitda = (net_debt / ebitda) if (ebitda and ebitda > 0) else None
    roe = (ni / eq) if (ni is not None and eq and eq > 0) else None
    latest_g = _yoy(rev_hist[0], rev_hist[1]) if len(rev_hist) >= 2 else None
    prior_g = _yoy(rev_hist[1], rev_hist[2]) if len(rev_hist) >= 3 else None

    return {
        # ── oriented factors for the panel composite (higher = better) ──
        "shares": shares, "market_cap": mc, "revenue": rev,
        "ey": (ni / mc) if (ni is not None and mc and mc > 0) else None,
        "roe": roe,
        "opm": opm,
        "neg_lev": (-nd_ebitda) if nd_ebitda is not None else None,
        "growth": latest_g,
        # ── raw line items under the names scoring.score_stock() reads ──
        "net_income": ni, "operating_income": op, "equity": eq,
        "cash": cash, "total_debt": debt, "da": da, "ebitda": ebitda,
        "net_debt": net_debt,
        "op_margin": opm,
        "net_debt_to_ebitda": nd_ebitda,
        "latest_rev_growth": latest_g,
        "prior_rev_growth": prior_g,
        "rev_hist": rev_hist,
    }


def _price_arrays(price_df):
    d = price_df.copy()
    # Robust to mixed-timezone sources (yfinance can return -05:00 / -04:00 across DST)
    # AND to plain date strings (Stooq): coerce everything to UTC, drop tz, keep the date.
    d["Date"] = pd.to_datetime(d["Date"], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    d = d.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return d["Date"].values, d["Close"].astype(float).values


def _volume_array(price_df):
    """Share volume aligned with _price_arrays, or None when the feed has none."""
    if "Volume" not in price_df:
        return None
    d = price_df.copy()
    d["Date"] = pd.to_datetime(d["Date"], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    d = d.dropna(subset=["Date"]).sort_values("Date").reset_index(drop=True)
    return d["Volume"].astype(float).values


def avg_dollar_volume(dates, closes, volumes, as_of, lookback=30):
    """
    Average daily dollar volume over the `lookback` sessions ENDING at as_of.

    This is the input to the live model's liquidity gate. `prices.get_quote`
    computes the same thing off the tail of the series, i.e. as of TODAY — which
    is fine for a daily screener and completely wrong for a backtest, where
    today's liquidity is a decade of look-ahead. Measured as of the rebalance
    date instead.
    """
    if volumes is None:
        return None
    i = _idx_asof(dates, as_of)
    if i is None:
        return None
    lo = max(0, i - lookback + 1)
    px, vol = closes[lo:i + 1], volumes[lo:i + 1]
    if len(px) == 0:
        return None
    dv = px * vol
    dv = dv[np.isfinite(dv)]
    return float(dv.mean()) if len(dv) else None


def _idx_asof(dates, as_of):
    pos = np.searchsorted(dates, np.datetime64(pd.Timestamp(as_of)), side="right") - 1
    return pos if pos >= 0 else None


def momentum_12_1(dates, closes, as_of):
    i = _idx_asof(dates, as_of)
    if i is None or i < 252:
        return None
    return float(closes[i - 21] / closes[i - 252] - 1)


def forward_return(dates, closes, as_of, horizon_td=63):
    i = _idx_asof(dates, as_of)
    if i is None or i + horizon_td >= len(closes):
        return None
    return float(closes[i + horizon_td] / closes[i] - 1)


def price_asof(dates, closes, as_of):
    i = _idx_asof(dates, as_of)
    return float(closes[i]) if i is not None else None


def build_panel(tickers, rebalance_dates, get_facts, get_prices, bench_prices,
                horizon_td=63, sectors=None, get_insider=None,
                is_common_equity=None):
    """
    tickers: list. rebalance_dates: list of dates. get_facts(t)->companyfacts dict.
    get_prices(t)->DataFrame[Date,Close(,Volume)]. bench_prices: DataFrame[Date,Close].
    sectors: optional {ticker: sector}. Returns the point-in-time panel DataFrame.

    get_insider: optional callable (ticker, as_of_date) -> list of Form 4
        transaction dicts filed ON OR BEFORE as_of, or None for "not fetched".
        `scoring.insider_score` distinguishes those two: [] means "we looked and
        there was no qualifying activity" (a real, neutral observation) while
        None means "not fetched" and renormalizes away. Passing None here
        therefore produces the live model MINUS its insider component, which is
        a legitimate thing to measure but must be labelled as such.
    is_common_equity: optional {ticker: bool} for the live model's first gate.

    The panel now carries BOTH the six oriented factors and the raw line items
    the live scorer reads, so one panel can be scored by either model. That is
    the whole point of C1: two models, one point-in-time feed, no excuse for
    them to disagree about the data.
    """
    bdates, bcloses = _price_arrays(bench_prices)
    rows = []
    for t in tickers:
        facts = get_facts(t)
        pdf = get_prices(t)
        if not facts or pdf is None or len(pdf) == 0:
            continue
        dates, closes = _price_arrays(pdf)
        volumes = _volume_array(pdf)
        for asof in rebalance_dates:
            p = price_asof(dates, closes, asof)
            if p is None:
                continue
            fwd = forward_return(dates, closes, asof, horizon_td)
            if fwd is None:
                continue  # no forward window yet (recent dates) -> excluded
            f = point_in_time_factors(facts, p, asof)
            row = {
                "date": pd.Timestamp(asof), "ticker": t,
                "sector": (sectors or {}).get(t, "?"),
                "ey": f["ey"], "roe": f["roe"], "opm": f["opm"],
                "neg_lev": f["neg_lev"], "growth": f["growth"],
                "mom": momentum_12_1(dates, closes, asof),
                "fwd_ret": fwd,
                "bench_ret": forward_return(bdates, bcloses, asof, horizon_td),
                # ── raw inputs for the LIVE scorer ──
                "price": p,
                "avg_dollar_volume": avg_dollar_volume(dates, closes, volumes, asof),
                "market_cap": f["market_cap"], "shares": f["shares"],
                "revenue": f["revenue"], "net_income": f["net_income"],
                "operating_income": f["operating_income"],
                "total_debt": f["total_debt"], "cash": f["cash"],
                "op_margin": f["op_margin"],
                "net_debt_to_ebitda": f["net_debt_to_ebitda"],
                "latest_rev_growth": f["latest_rev_growth"],
                "prior_rev_growth": f["prior_rev_growth"],
                "is_common_equity": (is_common_equity or {}).get(t, True),
            }
            # ret_12_1 is the live scorer's name for the same number `mom` holds.
            row["ret_12_1"] = row["mom"]
            if get_insider is not None:
                row["insider_transactions"] = get_insider(t, asof)
            rows.append(row)
    return pd.DataFrame(rows)
