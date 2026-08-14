"""
Fundamental point-in-time backtest — the "prove it on real history" engine.

Given a survivorship-free, point-in-time provider (Sharadar SF1+SEP, or a WRDS/CRSP
export), this builds a historical panel of our SAME nine themes at each rebalance date
(reusing the live factor engine, so the backtest scores stocks exactly like the site
does), then:
  • measures each candidate weighting's top-N portfolio return vs the S&P, and
  • runs the out-of-sample-gated optimizer to find the best STARTING weights.

Point-in-time = at each historical date we only use the fundamentals that were public
by then (SF1 `datekey`), and prices include delisted names — so no look-ahead and no
survivorship bias. That's the whole reason this needs a real data source, not free data.

v1 covers value / quality / momentum / low-risk / size (the meat). Growth, sentiment,
capital-discipline and sector-neutrality need extra history/metadata and stay neutral
here; they're additive later.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from ..screener import settings as S
from . import statistics as _stats      # AUDIT M2 — the ONE cross-date inference definition
from . import payload_schema as _schema  # AUDIT M6 — field-level results-file schema guard


def _f(d: dict, *keys):
    """First of `keys` present as a real number, else None.

    NaN counts as ABSENT. pandas reads a blank CSV cell as float('nan'), and returning that
    broke every `if x is not None` guard in this module in a way that raised no error:
      - `_f_score` treated a missing currentratio/debtnc (~18% of rows) as a test the company
        FAILED rather than one that couldn't be evaluated, both deflating the score and
        pushing the row past the ">=6 tests usable" guard on tests that weren't usable;
      - the roe/roic fallbacks below never fired, because a blank Sharadar column came back
        as NaN rather than None, so `if roe is None` was False.
    """
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if f == f:                       # NaN != NaN -> a blank cell is missing, not a value
            return f
    return None


# Which of the derived inputs below to populate. This exists so a change in the validation
# numbers can be attributed to ONE new signal rather than a bundle: flip an entry off and
# re-run to isolate it. All four ship on.
DERIVE = {"roe": True, "roic": True, "assetturnover": True, "beta": True}

# Statutory US federal rate, used only when a name's own effective rate can't be computed
# (pre-tax income <= 0, so taxexp/ebt is meaningless). Date-aware because a single constant
# across an 18-year window would be wrong for most of it: the TCJA cut 35% -> 21% for fiscal
# years beginning 2018.
_TCJA = "2018-01-01"


def _eff_tax_rate(sf1) -> float:
    """Effective tax rate from the row itself, else the statutory rate for that date.

    Clipped to [0, 0.60]: one-off items produce effective rates of -400% or +900% on small
    pre-tax numbers, and an unclipped rate turns a profitable name's NOPAT negative for
    accounting reasons that say nothing about its return on capital.
    """
    ebt, taxexp = _f(sf1, "ebt"), _f(sf1, "taxexp")
    if ebt is not None and ebt > 0 and taxexp is not None:
        return min(0.60, max(0.0, taxexp / ebt))
    dk = str(sf1.get("datekey") or sf1.get("date") or "")
    return 0.21 if dk >= _TCJA else 0.35


def _asset_turnover(row) -> Optional[float]:
    """revenue / assets — Sharadar's own `assetturnover` when present, else derived.

    Blank in 100% of ARQ rows, which is why F-Score test 9 (rising asset turnover) has
    never been evaluable in this project: it was one of only three tests that could be
    missing, and the >=6-usable guard was absorbing its absence silently.
    """
    if row is None:
        return None
    v = _f(row, "assetturnover")
    if v is not None:
        return v
    rev, a = _f(row, "revenue"), _f(row, "assets")
    return (rev / a) if (rev is not None and a and a > 0) else None


# A trailing-twelve-month window must not silently span a reporting gap. Four consecutive
# quarters cover ~365 days; 450 allows for late filings and 52/53-week fiscal calendars but
# rejects a company with a missing quarter, where summing "the last four rows" would quietly
# add up two or three years of earnings.
TTM_MAX_SPAN_DAYS = 450


def _ttm(rows, as_of, keys, n=4):
    """Sum the last `n` point-in-time quarterly rows for each key in `keys`.

    Returns None unless all n rows exist, are distinct quarters, and span a plausible year —
    a partial sum would silently understate a flow and read as a low-quality company.

    Motivation: the ARQ export gives one QUARTER's flow, so `roe = netinc/equity` is a
    quarterly rate whose level depends on which fiscal quarter a name happens to be in on a
    given rebalance date. Names sit at different fiscal quarters, so that seasonality enters
    the cross-section as noise. Summing four quarters removes it.
    """
    if not rows:
        return None
    picked = []
    for r in rows:                      # rows are pre-sorted by datekey
        dk = r.get("datekey") or r.get("date")
        if dk and dk <= as_of:
            picked.append((dk, r))
        elif dk and dk > as_of:
            break
    if len(picked) < n:
        return None
    # AUDIT D10-a — COLLAPSE RESTATEMENTS BEFORE TAKING THE LAST n. Verified against the live
    # Sharadar key on 2026-08-03: a restatement APPENDS a new ARQ row rather than rewriting the
    # existing one, and in the shipped export 3.15% of (ticker, reportperiod) groups carry more
    # than one datekey, across 1,818 of 2,827 tickers. The two rows describe the SAME fiscal
    # quarter, so a window taken over the last four rows could sum Q1, Q2, Q2', Q3 — one quarter
    # counted twice and one dropped. The guard below deduplicated on DATEKEY, which two filings
    # of one quarter never share, so it could not see this: exactly the "guard that cannot see"
    # pattern. Keep the LATEST filing of each reportperiod that is public by `as_of`, which is
    # both the correct point-in-time choice and one row per quarter.
    if any(r.get("reportperiod") for _, r in picked):
        by_period = {}
        for dk, r in picked:                       # datekey-ascending, so later wins
            by_period[r.get("reportperiod") or dk] = (dk, r)
        picked = sorted(by_period.values(), key=lambda x: x[0])
        if len(picked) < n:
            return None
    picked = picked[-n:]
    seen = {dk for dk, _ in picked}
    if len(seen) < n:                   # duplicate datekeys -> not n distinct quarters
        return None
    try:
        span = (pd.to_datetime(picked[-1][0]) - pd.to_datetime(picked[0][0])).days
    except (ValueError, TypeError):
        return None
    if span > TTM_MAX_SPAN_DAYS:
        return None
    out = {}
    for k in keys:
        vals = [_f(r, k) for _, r in picked]
        if any(v is None for v in vals):
            return None
        out[k] = float(sum(vals))
    return out


def _ttm_quality(m, rows, as_of) -> None:
    """TTM variants of the two strongest derived signals, measured alongside the quarterly
    ones so the comparison is head-to-head on identical rows rather than across runs.

    Denominators stay at the period-end stock (equity / invested capital), matching the
    quarterly versions — the ONLY difference is the flow window, so any IC difference is
    attributable to seasonality and nothing else. Averaging the denominator over the year is
    a further refinement, deliberately not bundled in here.
    """
    t = _ttm(rows, as_of, ("netinc", "ebit", "taxexp", "ebt"))
    if not t:
        return
    sf1 = _pit(rows, as_of) or {}
    equity, invcap = _f(sf1, "equity"), _f(sf1, "invcap")
    if equity and equity > 0:
        m["roe_ttm"] = t["netinc"] / equity
    if invcap and invcap > 0:
        # Effective rate from TTM tax over TTM pre-tax income — steadier than one quarter's,
        # which is where most one-off tax distortions live.
        ebt, tax = t["ebt"], t["taxexp"]
        rate = min(0.60, max(0.0, tax / ebt)) if ebt > 0 else _eff_tax_rate(sf1)
        m["roic_ttm"] = t["ebit"] * (1.0 - rate) / invcap


def _usd_divisor(sf1) -> float:
    """Local-currency units per USD, so `usd = local / divisor`.

    CAREFUL — Sharadar's `fxusd` is units of LOCAL currency per USD, not the multiplier:
    SKM 1514.2 (won/USD), TSM 31.64 (TWD/USD), IX 160 (JPY/USD), AAPL 1.0. Verified against
    the shipped USD columns: `equityusd/equity == revenueusd/revenue == ebitusd/ebit ==
    1/fxusd` exactly, for every foreign name checked. Using fxusd as a MULTIPLIER would square
    the currency error rather than fix it (~2.3 million x for SKM).

    Falls back to deriving the ratio from any local/USD pair, then to 1.0 (a USD reporter).
    """
    f = _f(sf1, "fxusd")
    if f is not None and f > 0:
        return f
    for u_key, l_key in (("equityusd", "equity"), ("revenueusd", "revenue"),
                         ("ebitusd", "ebit")):
        u, l = _f(sf1, u_key), _f(sf1, l_key)
        if u is not None and l is not None and u != 0 and l != 0:
            r = l / u
            if r > 0:
                return r
    return 1.0


def _to_usd(sf1, usd_key, local_value, divisor):
    """Sharadar's own USD column when present, else the local value converted."""
    v = _f(sf1, usd_key) if usd_key else None
    if v is not None:
        return v
    if local_value is None:
        return None
    return local_value / divisor if divisor else local_value


def _ev_point_in_time() -> bool:
    """Rebuild EV at the REBALANCE date instead of trusting the filing's own `ev`.

    Sharadar's `ev` is exactly `marketcap + debt - cashneq` (verified: median |diff|/mc = 0,
    96.4% inside 1% on 193,811 ARQ rows), and that `marketcap` is the one from the FILING
    date. The panel replaced the buggy shares x price market cap with a point-in-time figure
    from DAILY, but `ev` was left alone — so `ebit_ev`, `ev_sales` and `ev_ebitda` measured
    cheapness against a price roughly 111 days stale (the panel's effective fundamental lag),
    while `earnings_yield`, `fcf_yield` and `book_to_price` used the fresh one. The median
    one-quarter market-cap move is 10.5% and 18.6% of names move more than 25%, so this was a
    real handicap on the EV ratios rather than a rounding detail.

    It was STALE, not look-ahead: the price embedded in it is older than the rebalance, never
    newer, so the bias was conservative and no past result is invalidated upward.

    Default ON since 2026-08-03. It is a CORRECTNESS fix, not a performance one — measured
    full-universe it is a wash at book level (long-short t 3.396 -> 3.520, top-decile alpha
    +11.82% -> +11.88%, PBO unchanged) and the held-out gate reads not_replicated in both
    directions. The reason to ship it anyway is that there is no defensible version of the
    panel in which half the value ratios are priced at the rebalance date and half at a
    ~111-day-old quote. The flag remains so the old behaviour is one env var away.
    """
    from ..config import CONFIG
    return bool(getattr(CONFIG, "ev_point_in_time", True))


# How each row's enterprise value was arrived at. Ordered best -> worst; anything other than
# the first two means that row's EV ratios are still priced at the filing date.
EV_SRC_LINE_ITEMS = "pit_line_items"   # mc + (debt - cashneq)/fx   — preferred, 99.95% of rows
EV_SRC_IDENTITY = "pit_ev_identity"    # mc + (ev - marketcap)      — no fx needed, recovers 0.04%
EV_SRC_STALE_OFF = "stale_flag_off"    # rebuild disabled
EV_SRC_STALE_NO_MC = "stale_no_mc"     # no point-in-time market cap to re-price with
EV_SRC_STALE_NO_ND = "stale_no_netdebt"  # neither net-debt route available


def _pit_ev(sf1, ev_filing, mc, debt, cash, div, enabled):
    """-> (enterprise_value, source_tag). Re-prices the EQUITY leg of EV to `mc`.

    Net debt is only observable when a company files, so the debt leg is deliberately held at
    its last reported value — that IS the point-in-time answer, not an approximation of one.
    Only the equity leg is stale-able between filings, and that is the leg this refreshes.

    Two routes, because a single one leaves rows behind and a row left behind silently keeps
    the old stale value (this project's most-repeated bug class):

      A `mc + (debt - cashneq)/fx` — 99.95% of ARQ rows. `debt`/`cashneq` are REPORTING-currency
        line items and `mc` is USD, so net debt MUST be converted before it is added; adding raw
        won to a USD market cap is the P7 currency bug wearing a different hat.
      B `mc + (ev - marketcap)` — 98.29% of rows, and available on 82 rows where A is not. Both
        terms are already USD so it needs no fx at all, and it inherits whatever else Sharadar
        puts in EV (minority interest, preferred) instead of my simplification to debt - cash.

    Where both exist they agree to a p99 of 0.001% of market cap (193,811 rows), including on
    the 8,071 foreign-reporter rows where A converts and B does not — an independent check on
    the P7 fx handling, since a wrong `fxusd` would blow A apart from B on exactly those rows.
    A is preferred only because its coverage is higher.

    Both are in raw dollars: `mc` is DAILY's $mm figure scaled up, and the fact that A and B
    agree at all proves SF1's `ev`/`marketcap` are raw dollars too. Mixing scales here would
    corrupt a cross-section silently, so that agreement is load-bearing, not trivia.

    Falls back to the filing's stale `ev` rather than dropping the row, so a missing input
    costs accuracy instead of coverage — but every fallback is counted and surfaced by
    `ev_freshness()`, because a silent fallback is the bug this whole change is fixing.
    """
    if not enabled:
        return ev_filing, EV_SRC_STALE_OFF
    if not mc:
        return ev_filing, EV_SRC_STALE_NO_MC
    if debt is not None and cash is not None and div:
        return mc + (debt - cash) / div, EV_SRC_LINE_ITEMS
    mc_filing = _f(sf1, "marketcap")
    if ev_filing is not None and mc_filing:
        return mc + (ev_filing - mc_filing), EV_SRC_IDENTITY
    return ev_filing, EV_SRC_STALE_NO_ND


def _sf1_to_metrics(ticker, sf1, price, market_cap, ev_point_in_time=None) -> dict:
    """Map a Sharadar SF1 (ARQ) row → our metrics dict, valued at the as-of price.

    CURRENCY (P7): `marketcap` and `ev` are USD, but the raw line items are in the company's
    REPORTING currency. Every value ratio that divides a fundamental against market cap or EV
    therefore has to use the USD figure, or foreign reporters are handed a fake cheapness of
    up to ~1,500x (SK Telecom's book_to_price computed to 892 against a true 0.59) and sweep
    the top decile. 4.1% of panel rows report in a foreign currency and ALL of them were
    pushed the same direction.

    Same-currency ratios are deliberately left on the raw fields — roe, roic, op_margin,
    gross_margin, net_debt_to_ebitda all divide local by local and are already correct.
    Converting them would be a no-op at best and a new bug at worst.
    """
    rev, ni, ebit = _f(sf1, "revenue"), _f(sf1, "netinc"), _f(sf1, "ebit")
    ebitda, gp, fcf = _f(sf1, "ebitda"), _f(sf1, "gp"), _f(sf1, "fcf")
    equity, debt, cash = _f(sf1, "equity"), _f(sf1, "debt"), _f(sf1, "cashneq")
    ev, intexp = _f(sf1, "ev"), _f(sf1, "intexp")
    mc = market_cap
    ndte = ((debt or 0.0) - (cash or 0.0)) / ebitda if ebitda not in (None, 0) else None

    # ROE / ROIC. Sharadar populates these only in its averaged dimensions (ART/ARY); the
    # ARQ export this panel reads leaves them blank in EVERY row, so z_roe and z_roic have
    # been all-NaN in every backtest this project has run and `quality` was silently the mean
    # of 8 inputs rather than 10. Derived here from the raw line items, which ARE present.
    #
    # These are quarterly flows over a period-end stock, so the LEVEL is a quarterly rate,
    # not annualized. That is deliberate and harmless: every number here is z-scored
    # cross-sectionally before use, so only the ranking matters, and it matches how the
    # panel already treats earnings_yield / fcf_yield / op_margin. It does mean fiscal-quarter
    # seasonality enters the cross-section — a TTM version is the obvious follow-up.
    roe = _f(sf1, "roe")
    if roe is None and DERIVE["roe"] and ni is not None and equity and equity > 0:
        roe = ni / equity          # equity>0 only: a negative book value inverts the sign
    roic = _f(sf1, "roic")
    if roic is None and DERIVE["roic"] and ebit is not None:
        invcap = _f(sf1, "invcap")
        if invcap and invcap > 0:
            roic = ebit * (1.0 - _eff_tax_rate(sf1)) / invcap
    # --- USD figures for every ratio measured against market cap or EV (both USD) ---
    div = _usd_divisor(sf1)
    eq_usd = _to_usd(sf1, "equityusd", equity, div)
    rev_usd = _to_usd(sf1, "revenueusd", rev, div)
    ebit_usd = _to_usd(sf1, "ebitusd", ebit, div)
    # No `netincusd` column exists in this export; `netinccmnusd` (net income to COMMON, USD)
    # is the better numerator against market cap anyway, since market cap is common equity.
    #
    # AUDIT B20 — ONE definition, computed consistently. The fallback used to be `ni` (TOTAL net
    # income / fx), so `earnings_yield` silently switched numerator definition mid-cross-section:
    # net income to common where the USD column was populated, total net income where it was
    # not. For most names those are identical, but for preferred-heavy issuers — banks, REITs,
    # recently-recapitalised companies — they differ by the preferred dividend, and those names
    # cluster in one sector. The fallback is now `netinccmn`, the SAME quantity in local
    # currency, so only the currency conversion varies. `ni` remains the last resort for a row
    # carrying neither, and how often that happens is counted rather than assumed.
    _ni_cmn = _f(sf1, "netinccmn")
    ni_usd = _to_usd(sf1, "netinccmnusd", _ni_cmn if _ni_cmn is not None else ni, div)
    _ni_basis = ("netinccmnusd" if _f(sf1, "netinccmnusd") is not None else
                 "netinccmn_fx" if _ni_cmn is not None else
                 "netinc_fx_FALLBACK" if ni is not None else "none")
    fcf_usd = _to_usd(sf1, None, fcf, div)        # no fcfusd column — convert
    ebitda_usd = _to_usd(sf1, None, ebitda, div)  # no ebitdausd column — convert
    is_foreign = abs(div - 1.0) > 1e-9

    # EV at the REBALANCE date, not the filing date. See _pit_ev — the equity leg is re-priced
    # to the point-in-time market cap and the debt leg is held at its last reported value.
    if ev_point_in_time is None:
        ev_point_in_time = _ev_point_in_time()
    ev_filing = ev
    ev, ev_src = _pit_ev(sf1, ev, mc, debt, cash, div, ev_point_in_time)

    return {
        "ticker": ticker, "sector": "", "price": price, "market_cap": mc,
        "revenue": rev, "net_income": ni, "operating_income": ebit, "fcf": fcf,
        "gross_profit": gp, "total_debt": debt, "total_equity": equity, "interest_expense": intexp,
        # VALUE ratios — USD numerator/denominator on both sides (P7).
        "book_to_price": (eq_usd / mc) if (eq_usd is not None and mc) else None,
        "earnings_yield": (ni_usd / mc) if (ni_usd is not None and mc) else None,
        "fcf_yield": (fcf_usd / mc) if (fcf_usd is not None and mc) else None,
        # AUDIT B18 — ONE convention for negative enterprise value across all three EV ratios:
        # treat it as MISSING. A net-cash company used to read as the most expensive name in the
        # cross-section on `ebit_ev` and, once negated in build_frame, the cheapest of all on
        # `neg_ev_sales` — the same fact sorted to opposite ends of the same theme. A negative
        # multiple is not on the same scale as a positive one, so there is no ordering that is
        # right; the honest answer is no observation. ~0.70% of rows.
        "ebit_ev": (ebit_usd / ev) if (ebit_usd is not None and ev and ev > 0) else None,
        "ev_sales": (ev / rev_usd) if (ev and ev > 0 and rev_usd and rev_usd > 0) else None,
        # EV/EBITDA, POSITIVE EBITDA ONLY. A negative denominator flips the multiple negative,
        # which then sorts as "cheapest of all" — the loss-makers would lead the value ranking.
        # Leaving it None instead means the theme simply averages its other inputs for that
        # name (same convention build_frame already uses for a missing input).
        # AUDIT B18, completed. The first pass guarded `ebit_ev` and `ev_sales` on `ev > 0` and
        # left this one on the truthiness test alone, so 414 rows (0.36%) still carried a
        # negative EV/EBITDA — and the NEW sign check found them on the very next run, which is
        # what that check was added for. Same convention as its two siblings: missing.
        "ev_ebitda": (ev / ebitda_usd) if (ev and ev > 0 and ebitda_usd and ebitda_usd > 0)
        else None,
        # AUDIT B18, second half. The remaining negatives in `ev_sales` and `ps` are NOT negative
        # enterprise value — they are negative REVENUE: 538 rows, 0.273% of the export, and the
        # names are agency mortgage REITs and financial guarantors (DX, NLY, AGNC, MBI, RWT,
        # FNMA), where a quarter's net interest income after losses genuinely comes out below
        # zero. A negative sales multiple has exactly the same failure mode as a negative EV one:
        # negate it and the name sorts as the cheapest in the cross-section. Same answer — a
        # multiple on a negative denominator is not on the same scale as one on a positive
        # denominator, so it is no observation rather than an extreme.
        # (Verified: 746 rows have negative `ev` (0.378%), which is the population behind the
        # `ev_ebitda` flag; 538 have negative `revenueusd`, which is the `ev_sales`/`ps` one.)
        "ps": (mc / rev_usd) if (mc and rev_usd and rev_usd > 0) else None,
        # SAME-CURRENCY ratios — local/local, already correct, deliberately untouched.
        "op_margin": (ebit / rev) if (ebit is not None and rev) else _f(sf1, "ebitmargin"),
        "gross_margin": (gp / rev) if (gp is not None and rev) else _f(sf1, "grossmargin"),
        "roic": roic, "roe": roe, "net_debt_to_ebitda": ndte,
        # beta is filled in by _price_extras (regression vs the benchmark); None here so a
        # row whose window is too short simply has no beta rather than a stale one.
        "revenue_growth": None, "beta": None,
        # Diagnostics for the P8 sanity layer — not scored.
        "_is_foreign": is_foreign, "_fx_divisor": div,
        # Which EV route fired, and how far re-pricing moved it. `_ev_drift` is the whole point
        # of the fix expressed as a number: 0 means the filing's EV was already current.
        "_ev_src": ev_src,
        "_ev_drift": (abs(ev - ev_filing) / abs(ev_filing)
                      if (ev and ev_filing) else None),
    }


def _price_factors(closes, i) -> dict:
    """Momentum / trend / low-vol computed from prices up to index i (point-in-time)."""
    out = {}
    if i >= 252 and closes[i - 252] > 0:
        out["ret_12_1"] = closes[i - 21] / closes[i - 252] - 1.0
    if i >= 126 and closes[i - 126] > 0:
        out["ret_6_1"] = closes[i - 21] / closes[i - 126] - 1.0
    win = closes[max(0, i - 252):i + 1]
    hi = max(win) if win else None
    if hi and hi > 0:
        out["high_prox"] = closes[i] / hi
    vlook = closes[max(0, i - 120):i + 1]
    rets = [vlook[k] / vlook[k - 1] - 1.0 for k in range(1, len(vlook)) if vlook[k - 1] > 0]
    if len(rets) >= 20:
        mu = sum(rets) / len(rets)
        var = sum((x - mu) ** 2 for x in rets) / (len(rets) - 1)
        out["realized_vol"] = (var ** 0.5) * (252 ** 0.5)
    return out


def _price_extras(closes, i, bench=None) -> dict:
    """Short-horizon price anomalies, all strictly from data up to index i.

    Deliberately chosen to be orthogonal to the 12-1 momentum already in the panel —
    which skips the most recent month precisely because that month behaves the OPPOSITE
    way:

      neg_ret_1m   short-term reversal: last month's losers tend to bounce, so the signal
                   is the NEGATED 1-month return.
      neg_max_ret  the MAX / lottery effect: stocks with one huge up-day attract
                   speculative buying and subsequently underperform, so the largest daily
                   return of the past month is negated.
      neg_idio_vol idiosyncratic volatility: residual vol after regressing the stock's
                   daily returns on the benchmark's. Low idio-vol has historically
                   outperformed, hence negated. Being the stock-SPECIFIC part is what
                   makes it distinct from the total realized_vol already present.

    Also returns `beta` — the SLOPE of that same regression. It was already being computed
    and thrown away, while `low_risk = mean(z_neg_beta, z_neg_vol)` had no beta to work with
    (the panel hard-coded beta=None, so z_neg_beta was all-NaN and low_risk was purely
    realized volatility). Reported un-negated; factors.py negates it into neg_beta, so the
    orientation stays in one place.
    """
    out = {}
    if i >= 21 and closes[i - 21] > 0:
        out["neg_ret_1m"] = -(closes[i] / closes[i - 21] - 1.0)

    win = closes[max(0, i - 21):i + 1]
    drets = [win[k] / win[k - 1] - 1.0 for k in range(1, len(win)) if win[k - 1] > 0]
    if drets:
        out["neg_max_ret"] = -max(drets)

    if bench is not None and i >= 120:
        s = closes[max(0, i - 120):i + 1]
        b = bench[max(0, i - 120):i + 1]
        n = min(len(s), len(b))
        sr, br = [], []
        for k in range(1, n):
            if s[k - 1] > 0 and b[k - 1] > 0 and s[k] > 0 and b[k] > 0:
                sr.append(s[k] / s[k - 1] - 1.0)
                br.append(b[k] / b[k - 1] - 1.0)
        if len(sr) >= 40:
            mb, ms = sum(br) / len(br), sum(sr) / len(sr)
            varb = sum((x - mb) ** 2 for x in br)
            if varb > 0:
                beta = sum((br[k] - mb) * (sr[k] - ms) for k in range(len(br))) / varb
                if DERIVE["beta"]:
                    out["beta"] = beta          # -> neg_beta, the missing half of low_risk
                resid = [sr[k] - (ms + beta * (br[k] - mb)) for k in range(len(sr))]
                mr = sum(resid) / len(resid)
                var = sum((x - mr) ** 2 for x in resid) / (len(resid) - 1)
                out["neg_idio_vol"] = -((var ** 0.5) * (252 ** 0.5))
    return out


def _f_score(cur, prior) -> Optional[int]:
    """Piotroski F-Score (0-9) from two point-in-time SF1 rows.

    Nine binary accounting-health tests: profitability (4), leverage/liquidity (3),
    operating efficiency (2). Returns None unless at least six could be evaluated, so a
    thin row can't masquerade as a genuinely low score.
    """
    if not cur or not prior:
        return None
    assets, assets_p = _f(cur, "assets"), _f(prior, "assets")
    if not assets or not assets_p or assets <= 0 or assets_p <= 0:
        return None

    ni, ni_p = _f(cur, "netinc"), _f(prior, "netinc")
    cfo = _f(cur, "ncfo")
    roa = (ni / assets) if ni is not None else None
    roa_p = (ni_p / assets_p) if ni_p is not None else None

    tests = [
        roa > 0 if roa is not None else None,                                  # 1 profitable
        cfo > 0 if cfo is not None else None,                                  # 2 cash-generative
        roa > roa_p if (roa is not None and roa_p is not None) else None,      # 3 improving
        (cfo / assets) > roa if (cfo is not None and roa is not None) else None,  # 4 earnings quality
    ]
    ltd, ltd_p = _f(cur, "debtnc"), _f(prior, "debtnc")
    tests.append((ltd / assets) < (ltd_p / assets_p)
                 if (ltd is not None and ltd_p is not None) else None)          # 5 deleveraging
    cr, cr_p = _f(cur, "currentratio"), _f(prior, "currentratio")
    tests.append(cr > cr_p if (cr is not None and cr_p is not None) else None)  # 6 liquidity up
    sh, sh_p = _f(cur, "sharesbas", "shareswa"), _f(prior, "sharesbas", "shareswa")
    tests.append(sh <= sh_p * 1.001 if (sh and sh_p) else None)                 # 7 no dilution
    gm, gm_p = _f(cur, "grossmargin"), _f(prior, "grossmargin")
    tests.append(gm > gm_p if (gm is not None and gm_p is not None) else None)  # 8 margin up
    # 9 turnover up. `prior` is the point-in-time row from ~365 days earlier, i.e. roughly
    # the same fiscal quarter a year back, so comparing quarterly revenue/assets is
    # seasonally aligned rather than comparing a Q4 to a Q2.
    at = _asset_turnover(cur) if DERIVE["assetturnover"] else _f(cur, "assetturnover")
    at_p = _asset_turnover(prior) if DERIVE["assetturnover"] else _f(prior, "assetturnover")
    tests.append(at > at_p if (at is not None and at_p is not None) else None)

    usable = [t for t in tests if t is not None]
    if len(usable) < 6:
        return None
    return int(sum(1 for t in usable if t))


def _sf1_extras(m, sf1, rows, as_of, cut1=None) -> None:
    """F-Score, accruals quality, and cash-based operating profitability.

    All need a prior-year point-in-time row for the year-over-year changes, fetched the
    same way _yoy does it, so nothing is used that wasn't public by `as_of`.

    accruals_q   — the existing (previously never populated) hook: NEGATED total accruals,
                   (net income - operating cash flow) / assets, so earnings backed by real
                   cash score higher.
    cash_op_prof — Novy-Marx cash-based operating profitability: gross profit less SG&A and
                   R&D, adjusted for working-capital accruals, over assets. It beats plain
                   gross profitability in the literature precisely because it strips the
                   accrual component out.
    """
    if cut1 is None:
        cut1 = str((pd.to_datetime(as_of) - pd.Timedelta(days=365)).date())
    prior = _pit(rows, cut1)          # cut1 hoisted by the caller — see _yoy
    assets = _f(sf1, "assets")

    fs = _f_score(sf1, prior)
    if fs is not None:
        m["f_score"] = float(fs)

    ni, cfo = _f(sf1, "netinc"), _f(sf1, "ncfo")
    if assets and assets > 0 and ni is not None and cfo is not None:
        m["accruals_q"] = -((ni - cfo) / assets)

    if assets and assets > 0 and prior:
        rev, cor = _f(sf1, "revenue"), _f(sf1, "cor")
        sgna, rnd = _f(sf1, "sgna") or 0.0, _f(sf1, "rnd") or 0.0
        if rev is not None and cor is not None:
            op = rev - cor - sgna - rnd
            # Working-capital accruals: rising receivables/inventory and falling payables
            # all mean reported profit that hasn't become cash yet.
            d = 0.0
            for key, sign in (("receivables", -1.0), ("inventory", -1.0), ("payables", 1.0)):
                a, b = _f(sf1, key), _f(prior, key)
                if a is not None and b is not None:
                    d += sign * (a - b)
            m["cash_op_prof"] = (op + d) / assets


def _prep_holders(rows):
    """Sorted (dates, holder_count) from the 13F aggregate file.

    The bundled Sharadar institutional file is the AGGREGATE (one row per ticker-quarter);
    the per-manager SF3 detail is NOT in it, so true per-fund conviction can't be built
    from what's on disk. What it does carry and we've been ignoring is `shrholders` — how
    many institutions hold the shares — a breadth-of-ownership signal distinct from the
    dollar total that inst_accum already uses.
    """
    recs = []
    for r in rows:
        d = r.get("calendardate") or r.get("date")
        v = _f(r, "shrholders")
        if d and v is not None:
            recs.append((d, float(v)))
    if len(recs) < 2:
        return None
    dts = pd.to_datetime([x[0] for x in recs], errors="coerce")
    ok = ~pd.isna(dts)
    dd = dts[ok].values.astype("datetime64[D]")
    vv = np.array([recs[i][1] for i in range(len(recs)) if bool(ok[i])], dtype=float)
    if len(dd) < 2:
        return None
    order = np.argsort(dd)
    return dd[order], vv[order]


def _inst_breadth_at(prep, as_of, lag_days=45):
    """Quarter-over-quarter growth in the NUMBER of institutional holders as of `as_of`.

    Same filing-lag treatment as inst_accum: 13F data only becomes public well after the
    quarter it describes, so the cutoff is shifted back by `lag_days`.
    """
    if prep is None:
        return None
    dts, vals = prep
    cutoff = np.datetime64(as_of[:10], "D") - np.timedelta64(lag_days, "D")
    b = int(np.searchsorted(dts, cutoff, side="right"))
    if b < 2:
        return None
    cur, prev = float(vals[b - 1]), float(vals[b - 2])
    return (cur / prev - 1.0) if prev > 0 else None


def _daily_at(rows, as_of):
    """Latest DAILY month-end row on/before as_of -> (marketcap, pe, pb, ps, evebitda).

    Sharadar's own point-in-time values. Preferred over deriving market cap from
    shares x price: that derived path is what silently produced nothing when the `assets`
    column was missing from the loader allowlist, and it depends on getting sharefactor
    right for every split and share-class quirk.

    Rows are (date, mc, pe, pb, ps, evebitda) ascending, so a reverse walk finds the most
    recent qualifying row and can never see the future.
    """
    if not rows:
        return None
    for rec in reversed(rows):
        if rec[0] <= as_of:
            return rec[1], rec[2], rec[3], rec[4], rec[5]
    return None


def _sf3_at(qs, as_of, lag_days=45, cut=None):
    """Point-in-time SF3 aggregates: (holders, value, conviction, holders_prev).

    Lagged like the other 13F data — a quarter's filings arrive over the following weeks,
    and the most recent quarter in the file is always partially reported (AAPL shows 2,551
    holders for 2026-06-30 against 6,060 for 2026-03-31), so using it unlagged would read a
    filing-completeness artifact as a collapse in ownership.
    """
    if not qs:
        return None
    cutoff = cut if cut is not None else         str((pd.to_datetime(as_of[:10]) - pd.Timedelta(days=int(lag_days))).date())
    keys = sorted(k for k in qs if k <= cutoff)
    if not keys:
        return None
    cur = qs[keys[-1]]
    prev = qs[keys[-2]] if len(keys) >= 2 else None
    return (cur.get("holders"), cur.get("value"), cur.get("conviction"),
            (prev or {}).get("holders"))


def _pit(rows, as_of):
    """Latest fundamentals row whose datekey is on/before as_of (no look-ahead)."""
    chosen = None
    for r in rows:
        dk = r.get("datekey") or r.get("date")
        if dk and dk <= as_of:
            chosen = r
        elif dk and dk > as_of:
            break
    return chosen


def _yoy(m, rows, as_of, shares_now, rev_now, assets_now, cut1=None, cut2=None):
    """Populate revenue_growth / asset_growth / share_issuance / growth_accel from prior-year
    point-in-time SF1 rows. These turn the GROWTH and CAPITAL-DISCIPLINE (investment) themes —
    currently empty 'hooks' in the backtest — into real, low-correlation signals, computed only
    from data public by `as_of` (no look-ahead)."""
    # cut1/cut2 are the as_of-365d and as_of-730d cutoffs. They depend only on as_of, not
    # on the ticker, so the caller computes them ONCE per rebalance date and passes them in.
    # Deriving them here cost 19k pd.to_datetime calls and 35% of total panel-build time.
    if cut1 is None:
        cut1 = str((pd.to_datetime(as_of) - pd.Timedelta(days=365)).date())
    if cut2 is None:
        cut2 = str((pd.to_datetime(as_of) - pd.Timedelta(days=730)).date())
    p1 = _pit(rows, cut1)
    if not p1:
        return
    rev0, a0 = _f(p1, "revenue"), _f(p1, "assets")
    s0 = _f(p1, "sharesbas", "shareswa", "shareswadil")
    if rev_now is not None and rev0 and rev0 != 0:
        m["revenue_growth"] = rev_now / rev0 - 1.0
    if assets_now is not None and a0 and a0 != 0:
        m["asset_growth"] = assets_now / a0 - 1.0                # investment factor (low = good)
    if shares_now and s0 and s0 != 0:
        m["share_issuance"] = shares_now / s0 - 1.0              # net issuance (low/negative = good)
    p2 = _pit(rows, cut2)                                        # 2-yr-ago → growth acceleration
    # Test the VALUE, not the key: _sf1_to_metrics pre-seeds revenue_growth=None, so
    # `"revenue_growth" in m` is always True and this reached `None - float` whenever the
    # prior-year revenue was missing.
    if p2 is not None and m.get("revenue_growth") is not None:
        rev2 = _f(p2, "revenue")
        if rev2 and rev0 and rev2 != 0:
            m["growth_accel"] = m["revenue_growth"] - (rev0 / rev2 - 1.0)


def _insider_formula(net, buys):
    """The shipped 0-100 insider score. ONE definition, called by both paths.

    S3 PREMISE CHECK (b): this expression used to be written out twice -- once in
    `_insider_score` (the row-iterating fallback) and once in `_insider_score_at` (the prepped
    fast path) -- and the B26 comment in each said the two paths must agree. Two copies of a
    formula that MUST agree is the B7 defect class, so there is now one copy and the duplicates
    delegate to it. Bit-identical to what both sites computed before; pinned by
    `test_s3_both_insider_paths_agree`.
    """
    import math
    return max(0.0, min(100.0, 50 + 40 * math.tanh(net / 5e6) + min(10, 2 * buys)))


def _insider_score(rows, as_of, lookback_days=90):
    """0-100 (50 = neutral) net insider buying over the trailing window, by FILING date
    (point-in-time). Mirrors the live insider factor so the two are comparable."""
    if not rows:
        return None
    import math
    hi = pd.to_datetime(as_of)
    lo = hi - pd.Timedelta(days=lookback_days)
    net, buys = 0.0, 0
    for r in rows:
        d = pd.to_datetime(r.get("filingdate") or r.get("date"), errors="coerce")
        # AUDIT B26 — `>= hi`, matching _insider_score_at: a Form 4 dated as_of is not
        # reliably public before that day's close. The two paths must agree or the
        # prepped fast path and the fallback score the same name differently.
        if d is pd.NaT or d >= hi or d < lo:
            continue
        sh, pr = _f(r, "transactionshares"), _f(r, "transactionpricepershare")
        val = (sh * pr) if (sh is not None and pr is not None) else _f(r, "transactionvalue")
        if val is None:
            continue
        net += val
        if val > 0:
            buys += 1
    if net == 0 and buys == 0:
        return None
    return _insider_formula(net, buys)


def _inst_accum(rows, as_of, lag_days=45):
    """Quarter-over-quarter change in 13F institutional holdings, using only quarters whose
    filing (calendardate + ~45d lag) was public by as_of — so no look-ahead from stale 13Fs."""
    if not rows:
        return None
    hi = pd.to_datetime(as_of)
    usable = []
    for r in rows:
        d = pd.to_datetime(r.get("calendardate") or r.get("date"), errors="coerce")
        if d is not pd.NaT and (d + pd.Timedelta(days=lag_days)) <= hi:
            usable.append((d, r))
    if len(usable) < 2:
        return None
    usable.sort(key=lambda x: x[0])
    cur = _f(usable[-1][1], "totalvalue", "value", "sharesheld", "shares")
    prev = _f(usable[-2][1], "totalvalue", "value", "sharesheld", "shares")
    if cur is None or not prev or prev <= 0:
        return None
    return cur / prev - 1.0


# --- fast versions: pre-index each ticker's dates ONCE, then O(log n) lookups per date ---
def _prep_insider(rows):
    """Sorted (dates[datetime64], signed_value[float]) for a ticker's Form-4 transactions."""
    recs = []
    for r in rows:
        d = r.get("filingdate") or r.get("date")
        if not d:
            continue
        sh, pr = _f(r, "transactionshares"), _f(r, "transactionpricepershare")
        val = (sh * pr) if (sh is not None and pr is not None) else _f(r, "transactionvalue")
        if val is not None:
            recs.append((d, float(val)))
    if not recs:
        return None
    dts = pd.to_datetime([x[0] for x in recs], errors="coerce")
    ok = ~pd.isna(dts)
    dd = dts[ok].values.astype("datetime64[D]")
    vv = np.array([recs[i][1] for i in range(len(recs)) if bool(ok[i])], dtype=float)
    order = np.argsort(dd)
    return dd[order], vv[order]


def _insider_score_at(prep, as_of, lookback_days=90):
    if prep is None:
        return None
    import math
    dts, vals = prep
    hi = np.datetime64(as_of[:10], "D")
    lo = hi - np.timedelta64(lookback_days, "D")
    # AUDIT B26 — SAME-DAY EXCLUSION. `side="right"` on the upper bound made a filing dated
    # `as_of` itself usable at that day's close. Form 4s and rating actions are routinely
    # filed after the bell, so a same-day row is not reliably public when the panel scores.
    # At most one day of optimism, and free to remove; `side="left"` stops at the day BEFORE.
    a = int(np.searchsorted(dts, lo, side="left"))
    b = int(np.searchsorted(dts, hi, side="left"))
    if b <= a:
        return None
    w = vals[a:b]
    net, buys = float(w.sum()), int((w > 0).sum())
    return _insider_formula(net, buys)


def _insider_raw_at(prep, as_of, lookback_days=90):
    """The `(net, buys)` pair `_insider_score_at` reduces to a score, exposed unreduced.

    S3 needs the two raw quantities to build its variants, and it must build them from the SAME
    window the shipped score uses or the arms differ in more than the formula. So this repeats
    the window arithmetic and nothing else; `_insider_score_at` remains the only scorer.
    Returns None on exactly the inputs that make the score None.
    """
    if prep is None:
        return None
    dts, vals = prep
    hi = np.datetime64(as_of[:10], "D")
    lo = hi - np.timedelta64(lookback_days, "D")
    a = int(np.searchsorted(dts, lo, side="left"))
    b = int(np.searchsorted(dts, hi, side="left"))
    if b <= a:
        return None
    w = vals[a:b]
    return float(w.sum()), int((w > 0).sum())


def _prep_inst(rows):
    """Sorted (dates[datetime64], totalvalue[float]) for a ticker's 13F quarterly totals."""
    recs = []
    for r in rows:
        d = r.get("calendardate") or r.get("date")
        v = _f(r, "totalvalue", "value", "sharesheld", "shares")
        if d and v is not None:
            recs.append((d, float(v)))
    if len(recs) < 2:
        return None
    dts = pd.to_datetime([x[0] for x in recs], errors="coerce")
    ok = ~pd.isna(dts)
    dd = dts[ok].values.astype("datetime64[D]")
    vv = np.array([recs[i][1] for i in range(len(recs)) if bool(ok[i])], dtype=float)
    order = np.argsort(dd)
    return dd[order], vv[order]


def _prep_grades(rows):
    """Sorted (dates[datetime64], direction[int]) for a ticker's analyst rating actions.

    direction: +1 upgrade, -1 downgrade, 0 maintain/initiate. Unlike 13F there is no
    filing lag to model — a rating action is published the day it happens, so the row's
    own date IS the moment it became public.
    """
    recs = []
    for r in rows:
        d = r.get("date")
        a = str(r.get("action") or "").strip().lower()
        if not d:
            continue
        if a in ("upgrade", "up"):
            v = 1
        elif a in ("downgrade", "down"):
            v = -1
        else:
            v = 0                      # maintain / initiate / reiterate
        recs.append((str(d)[:10], v))
    if not recs:
        return None
    dts = pd.to_datetime([x[0] for x in recs], errors="coerce")
    ok = ~pd.isna(dts)
    dd = dts[ok].values.astype("datetime64[D]")
    vv = np.array([recs[i][1] for i in range(len(recs)) if bool(ok[i])], dtype=float)
    if len(dd) == 0:
        return None
    order = np.argsort(dd)
    return dd[order], vv[order]


# Trailing window for the rating-revision signal. A quarter is long enough to accumulate
# a few actions on a typical large cap, short enough to still be "recent sentiment".
GRADES_WINDOW_DAYS = 90


def _grades_at(prep, as_of, window_days=GRADES_WINDOW_DAYS):
    """Point-in-time (net_revision, disagreement) from actions in (as_of-window, as_of].

    net_revision  = (upgrades - downgrades) / total actions   in [-1, 1]
    disagreement  = share of directional actions that go AGAINST the majority, in [0, 0.5]
                    — 0 when every move agrees, 0.5 when analysts are evenly split.

    Only rows dated on or before `as_of` are considered, so there is no look-ahead.
    Returns None when the window is empty (no opinion to read).
    """
    if prep is None:
        return None
    dts, vals = prep
    hi = np.datetime64(as_of[:10], "D")
    lo = hi - np.timedelta64(int(window_days), "D")
    # AUDIT B26 — SAME-DAY EXCLUSION. `side="right"` on the upper bound made a filing dated
    # `as_of` itself usable at that day's close. Form 4s and rating actions are routinely
    # filed after the bell, so a same-day row is not reliably public when the panel scores.
    # At most one day of optimism, and free to remove; `side="left"` stops at the day BEFORE.
    a = int(np.searchsorted(dts, lo, side="right"))
    b = int(np.searchsorted(dts, hi, side="left"))
    if b <= a:
        return None
    w = vals[a:b]
    n = len(w)
    ups = int((w > 0).sum())
    downs = int((w < 0).sum())
    net = (ups - downs) / float(n)
    directional = ups + downs
    if directional == 0:
        disagree = 0.0                     # only maintains: no disagreement expressed
    else:
        disagree = min(ups, downs) / float(directional)
    return net, disagree


def _inst_accum_at(prep, as_of, lag_days=45):
    if prep is None:
        return None
    dts, vals = prep
    cutoff = np.datetime64(as_of[:10], "D") - np.timedelta64(lag_days, "D")   # 13F filing lag
    b = int(np.searchsorted(dts, cutoff, side="right"))
    if b < 2:
        return None
    cur, prev = float(vals[b - 1]), float(vals[b - 2])
    return (cur / prev - 1.0) if prev > 0 else None


# S15 — the VALUE theme's raw inputs, and nothing else. `neg_ev_sales`, `neg_ps` and
# `neg_ev_ebitda` are DERIVED inside `build_frame` before the sector block runs, so they
# are available to be de-meaned by the time S15 needs them.
VALUE_INPUTS = ["earnings_yield", "fcf_yield", "ebit_ev", "book_to_price",
                "neg_ev_sales", "neg_ps", "neg_ev_ebitda"]


def _inst_age_at(prep, as_of, lag_days=45):
    """S8 — CALENDAR DAYS since the 13F quarter-end `_inst_accum_at` actually used.

    Repeats that function's window arithmetic and nothing else, so the age describes the SAME
    observation the signal is built from. Returns None on exactly the inputs that make the
    signal None.
    """
    if prep is None:
        return None
    dts, vals = prep
    cutoff = np.datetime64(as_of[:10], "D") - np.timedelta64(lag_days, "D")
    b = int(np.searchsorted(dts, cutoff, side="right"))
    if b < 2:
        return None
    return float((np.datetime64(as_of[:10], "D") - dts[b - 1]).astype("timedelta64[D]")
                 .astype(int))


def _forward_return(closes, i, h, n_cal):
    """S22 — delisting-aware forward return over `h` trading days from calendar index `i`.

    This is the shipped `fwd_ret` rule, factored out so that additional horizons are computed
    by the SAME code rather than by a second implementation that can drift from it.

    Delisting: if the horizon-end price is NaN because the survivorship mask cut the name
    mid-window, fall back to the last price it actually traded at, realizing the delisting
    outcome instead of discarding the name — dropping it would quietly re-introduce the
    survivorship bias the mask exists to remove.

    RIGHT-CENSORING IS NOT DELISTING (PREREG_s22_term_structure.md §2a). If `i + h` runs past
    the end of the shared calendar the return DOES NOT EXIST and this returns None. It must not
    fall through to the delisting branch: that branch returns the last traded price, which for a
    censored window would deliver a SHORTER realized return labelled as a long-horizon one, and
    would do so precisely for the most recent dates — flattering short horizons and penalising
    long ones. Pinned by test_s22_right_censoring_is_not_delisting.
    """
    if i + h >= n_cal:
        return None
    start = closes[i]
    if not (start > 0):
        return None
    end = closes[i + h]
    if end != end:                                      # NaN -> delisted mid-window
        seg = closes[i + 1:i + h + 1]
        valid = seg[~np.isnan(seg)] if len(seg) else seg
        end = float(valid[-1]) if len(valid) else np.nan
    return (end / start - 1.0) if end == end else None


def build_fundamental_panel(provider, tickers, benchmark="SPY", rebalance_days=63,
                            lookback_years=6, horizon=63, inst_lag_days=45,
                            keep_numbers=False, sector_neutral=False,
                            grid_offset=None, extra_horizons=None,
                            sector_neutral_pair=False, standardizer_arms=None,
                            with_insider_raw=False, with_issuance_raw=False,
                            with_vol_raw=False, with_freshness=False,
                            bucket_relative_arms=None, sector_value_arm=False) -> pd.DataFrame:
    """Point-in-time panel of the theme columns per (date, ticker).

    keep_numbers=True additionally persists each individual standardized number (z_*), so
    a diagnostic can measure one signal's standalone predictive power instead of only the
    theme it was folded into. Off by default — it widens the frame considerably.

    S22 — `extra_horizons` adds a `fwd_ret_h{H}` column per requested horizon, computed inside
    the SAME loop from the SAME price array as the shipped `fwd_ret`. Off by default; with no
    extra horizons the frame is column-for-column identical to before.

    Why it exists: the horizon is baked into this function, and the grid end is
    `len(cal) - horizon`, so building one panel per horizon would vary the horizon AND the date
    set AND the scored cross-sections together — no difference between two such runs could be
    attributed to the horizon. One build keeps the scores, dates, names and composite identical
    across every arm, so the forward window is the only thing that varies (and any run-to-run
    nondeterminism in the panel is common to all arms and cancels).

    The extra columns are defined on exactly the rows this panel already emits — a row still
    requires the BASE `fwd_ret` to be present — so the row set does not change either. Longer
    horizons are simply NaN on the most recent dates, which is the censoring above.

    SECTOR-NEUTRAL-B6 — `sector_neutral_pair` additionally scores each cross-section with the
    OPPOSITE `sector_neutral` setting and emits it as `sn_{theme}` columns on the SAME rows. Off
    by default; with it off the frame is column-for-column identical to before.

    Why it exists: both prior sector-neutral rejections built the two arms as two separate runs,
    and a full backtest is NOT reproducible run to run (the `insider` theme moved median IC
    -0.0034 / +0.0155 / -0.0034 across three identical-data runs). Scoring both arms from the one
    `metrics` list makes that nondeterminism common-mode, so it cancels out of the difference
    being measured, and makes the identical row set a property of the code rather than a claim.
    Same argument as `extra_horizons` above.

    LEDGER S20/S21 — `standardizer_arms` is the same device generalised: a {prefix: callable}
    mapping, where each callable replaces the PER-NUMBER standardizer for one extra scoring of the
    SAME `metrics` list, emitted as `{prefix}_{theme}` columns on the SAME rows. Off by default;
    with it unset the frame is column-for-column identical to before. The study passes
    `{"rk": rank_score, "nw": zscore_nowinsor}` — see PREREG_s20_s21_construction.md §4.

    AUDIT X2 — `grid_offset` shifts the rebalance grid by N trading days. The grid has
    always started at exactly TD = 252 and every number this project has ever reported was
    measured on that ONE grid, which is an arbitrary choice: with rebalance_days = 63 there
    are 63 equally valid grids and nobody has ever looked at the other 62. A signal whose
    headline moves a lot between them is one draw from a wide distribution, and the honest
    statement is a range rather than a figure. Defaults to 0 (the historical grid) and can
    be set per run with EDGE_GRID_OFFSET so a sweep needs no call-site changes.
    """
    TD = 252
    if grid_offset is None:
        import os as _os_grid
        try:
            grid_offset = int(_os_grid.environ.get("EDGE_GRID_OFFSET", "0") or 0)
        except ValueError:
            grid_offset = 0
    grid_offset = int(grid_offset)
    if grid_offset < 0:
        raise ValueError(f"grid_offset must be >= 0, got {grid_offset}")
    # S22 — the additional forward windows, deduplicated and ordered. The BASE horizon is
    # allowed here and is the study's C0 control: `fwd_ret_h63` must equal `fwd_ret` exactly.
    _extra_h = sorted({int(h) for h in (extra_horizons or [])})
    if any(h <= 0 for h in _extra_h):
        raise ValueError(f"extra_horizons must all be > 0, got {sorted(extra_horizons or [])}")
    _GRID_START = TD + grid_offset
    from ..screener.factors import prefilter as _prefilter   # AUDIT B13

    # AUDIT B6 — TRUNCATE THE CALENDAR, NOT EACH TICKER'S SERIES.
    #
    # `price_history(days=N)` used to end in `df.sort_values("date").tail(N)`, so every ticker
    # kept its OWN last N rows and the panel calendar became the UNION of those windows. The
    # consequence was severe and non-random: at a 2001 cross-section, the only names present
    # were ones that STOPPED TRADING by about 2019, because a name still trading in 2026 had
    # its first decade truncated away. That is the inverse of classic survivorship bias — the
    # early sample contained eventual-delisters and nothing else — and it made roughly the
    # first 37 of 110 rebalance dates uninterpretable. Those same 37 dates had no benchmark
    # either (SPY was fetched under the same per-ticker cap), which is why the results file
    # reported `construction.n_periods = 110` next to `portfolio.n_periods = 73` over two
    # undisclosed and different windows.
    #
    # `days=None` asks the provider for the WHOLE series; the shared calendar is then cut once,
    # below, after the frame is built — so every ticker is cut at the same DATE by construction
    # and no ticker can lose its own early history. The full series are already on disk (7,184
    # rows, 1997-12-31 -> 2026-07-24), so this costs a slightly longer load and no extra frame
    # memory: the frame was ALWAYS the union calendar, this only stops it being mostly holes.
    _CAL_DAYS = TD * lookback_years + horizon + 60

    # ATTRIBUTION TOGGLES (default OFF — the shipped behaviour is the corrected one).
    # B6, B7 and B13 all landed in the same commit and all three move the panel, which
    # breaks the one-change-per-run rule. These exist so each can be reverted ALONE and
    # its own contribution to the headline measured. They are diagnostics, not options.
    import os as _os_attr
    _B6_LEGACY = _os_attr.environ.get("EDGE_AUDIT_B6_LEGACY_TRUNCATION", "").lower() == "true"
    _B13_OFF = _os_attr.environ.get("EDGE_AUDIT_B13_PREFILTER", "").lower() == "off"

    def series(t):
        d, c = provider.price_history(t, days=(_CAL_DAYS if _B6_LEGACY else None))
        return pd.Series(c, index=pd.to_datetime(d)) if (d and c and len(c) > TD) else None

    bench = series(benchmark)
    if bench is None or len(bench) < TD + horizon:
        # The benchmark (SPY) is an ETF, so a stocks-only point-in-time source won't carry it.
        # Pull the index line from free prices — it doesn't need to be survivorship-free.
        try:
            from ..screener.prices import close_series
            d, c = close_series(benchmark, days=TD * lookback_years + horizon + 200)
            if d and c and len(c) > TD:
                bench = pd.Series(c, index=pd.to_datetime(d))
        except Exception:
            pass
    if bench is None or len(bench) < TD + horizon:
        import sys
        print(f"[panel] benchmark '{benchmark}' unavailable ({0 if bench is None else len(bench)} days) from the "
              f"data source or free prices — cannot build the panel.", file=sys.stderr)
        return pd.DataFrame()

    # Progress logging. The full-universe run previously printed NOTHING for 90+ minutes,
    # which made a slow run indistinguishable from a hung one and got it killed. Every
    # phase now reports, so the next long run is diagnosable while it happens.
    import sys as _sys
    import time as _time
    _t0 = _time.time()

    def _prog(msg):
        print(f"[panel] {_time.time()-_t0:6.0f}s  {msg}", file=_sys.stderr, flush=True)

    _prog(f"loading per-ticker history for {len(tickers)} tickers "
          f"(price + fundamentals + insider + 13F)")
    px, hist, insh, inst, grd, hold = {}, {}, {}, {}, {}, {}
    dly, sf3 = {}, {}          # BULK: DAILY month-end ratios, SF3 per-manager 13F
    meta = {}                  # TICKERS: sector / country / exchange (NOT point-in-time)
    earn = {}                  # EVENTS: earnings announcement dates (code 22)
    elite = {}                 # SF3: manager-quality-weighted conviction
    shorts = {}                # FINRA short interest (publication-dated)
    e13d = {}                  # SEC 13D/13G activist stakes (filing-dated)
    usasp = {}                 # USAspending federal awards (quarter-end + lag)
    cong = {}                  # Congressional trades (PTR filing-dated)
    for _i, t in enumerate(tickers):
        if _i and _i % 250 == 0:
            _prog(f"  loaded {_i}/{len(tickers)} tickers, {len(px)} usable")
        s = series(t)
        if s is not None and len(s) > TD + horizon:
            px[t] = s
            hist[t] = sorted(provider.fundamentals_history(t) or [],
                             key=lambda r: (r.get("datekey") or r.get("date") or ""))
            insh[t] = _prep_insider(provider.insider_history(t) or [])       # pre-indexed once
            _ih = provider.institutional_history(t) or []
            inst[t] = _prep_inst(_ih)                                        # pre-indexed once
            hold[t] = _prep_holders(_ih)                                     # holder-count breadth
            # Analyst rating actions -> the sentiment theme. Absent from providers that
            # don't carry them, in which case the theme simply stays neutral as before.
            grd[t] = _prep_grades(provider.grades_history(t) or []) \
                if hasattr(provider, "grades_history") else None
            # Sharadar BULK: point-in-time market cap / ratios, and per-manager 13F detail.
            dly[t] = provider.daily_history(t) if hasattr(provider, "daily_history") else []
            sf3[t] = provider.sf3_for(t) if hasattr(provider, "sf3_for") else {}
            shorts[t] = (provider.short_interest_for(t)
                         if hasattr(provider, "short_interest_for") else [])
            e13d[t] = (provider.edgar_13d_for(t)
                       if hasattr(provider, "edgar_13d_for") else [])
            usasp[t] = (provider.usaspending_for(t)
                        if hasattr(provider, "usaspending_for") else [])
            cong[t] = (provider.congress_for(t)
                       if hasattr(provider, "congress_for") else [])
            elite[t] = (provider.elite_conviction_for(t)
                        if hasattr(provider, "elite_conviction_for") else {})
            meta[t] = provider.ticker_meta(t) if hasattr(provider, "ticker_meta") else {}
            earn[t] = (provider.earnings_dates(t)
                       if hasattr(provider, "earnings_dates") else [])
    if not px:
        import sys
        print("[panel] no usable price series for any ticker in the export.", file=sys.stderr)
        return pd.DataFrame()

    frame = pd.DataFrame(px).sort_index()
    # AUDIT B6 — the ONE calendar cut, applied to every ticker at the same date. Taken BEFORE
    # the ffill below so a name that genuinely had no data in the retained window cannot be
    # forward-filled into it from outside. `_cal_full` records what was available so the
    # discarded span is a reported number rather than an invisible default.
    _cal_full = (str(frame.index[0].date()), str(frame.index[-1].date()), int(len(frame.index)))
    if _B6_LEGACY:
        pass                      # legacy: each ticker already truncated itself, union calendar
    elif _CAL_DAYS and len(frame.index) > _CAL_DAYS:
        frame = frame.iloc[-_CAL_DAYS:]
    frame = frame.ffill()
    # Survivorship correction. The ffill() above carries each name's last close to the END
    # of the shared calendar, so a delisted company keeps "trading" flat forever — Merrill
    # Lynch, delisted 2008-12-31 at $11.64, otherwise contributes a fake 0% forward return
    # to every rebalance date for the next 18 years. Blank everything after the delisting so
    # the name simply isn't investable then.
    #
    # NOTE: we deliberately do NOT apply the ACTIONS split ratios. Sharadar's SEP closes are
    # ALREADY split-adjusted (AAPL is $0.098 in 1997 and shows no discontinuity across the
    # 2020 4:1 split), so re-applying them would double-correct every split in the history.
    _delisted = {}
    try:
        if hasattr(provider, "delisted_map"):
            _delisted = provider.delisted_map() or {}
    except Exception:
        _delisted = {}
    _pf_rejects = {}          # AUDIT B13: why names were dropped by the live screen
    _masked = 0
    if _delisted:
        for t in frame.columns:
            dd = _delisted.get(str(t).upper())
            if dd:
                m = frame.index > pd.to_datetime(dd)
                if m.any():
                    frame.loc[m, t] = np.nan
                    _masked += 1
    # AUDIT B14 — SHIP the mask's coverage instead of counting it and throwing it away. The
    # results file only ever carried `cleanups.survivorship_mask` as a boolean meaning "the
    # ACTIONS map is non-empty", which cannot distinguish a working mask from one that matched
    # nothing. The failure it exists to prevent is silent: if ACTIONS misses a delisting, that
    # name's last close is forward-filled to the panel end and it contributes a fake flat 0%
    # forward return to EVERY subsequent rebalance date. `ended_early_unmasked` counts exactly
    # that population — names whose price series stops well before the panel end with no
    # corresponding ACTIONS row — so a mask that quietly stops working becomes loud, the same
    # way `ev_freshness` was built to make a silent revert loud.
    _last_ok, _panel_end = {}, frame.index[-1] if len(frame.index) else None
    _ended_early = 0
    if _panel_end is not None:
        _cut = _panel_end - pd.Timedelta(days=STALE_TAIL_DAYS)
        for t in frame.columns:
            s = frame[t]
            idx = s.last_valid_index()
            if idx is None:
                continue
            _last_ok[str(t)] = str(idx.date())
            if idx < _cut and not _delisted.get(str(t).upper()):
                _ended_early += 1
    _mask_coverage = {
        "delisting_map_names": len(_delisted or {}),
        "series_masked": _masked,
        "tickers_in_frame": int(len(frame.columns)),
        "masked_share": (_masked / float(len(frame.columns))) if len(frame.columns) else None,
        "ended_early_unmasked": _ended_early,
        "ended_early_unmasked_share": (_ended_early / float(len(frame.columns))
                                       if len(frame.columns) else None),
        "stale_tail_days": STALE_TAIL_DAYS,
        "panel_end": str(_panel_end.date()) if _panel_end is not None else None,
    }
    cal = frame.index
    _n_cal = len(cal)                  # S22 — the censoring boundary for every forward window
    _cal64 = cal.values.astype("datetime64[D]")
    benchf = bench.reindex(cal).ffill()
    benchv = benchf.values.tolist()        # for the idiosyncratic-vol regression, computed once

    _n_dates = len(range(_GRID_START, len(cal) - horizon, rebalance_days))
    _prog(f"history loaded: {len(px)} usable tickers, {len(cal)} calendar days "
          f"-> scoring {_n_dates} rebalance dates")

    rows = []
    for _di, i in enumerate(range(_GRID_START, len(cal) - horizon, rebalance_days)):
        as_of = str(cal[i].date())
        _asof_ts = cal[i]
        _cut1 = str((_asof_ts - pd.Timedelta(days=365)).date())
        _cut2 = str((_asof_ts - pd.Timedelta(days=730)).date())
        _cut3 = str((_asof_ts - pd.Timedelta(days=int(inst_lag_days))).date())
        if _di and _di % 10 == 0:
            _prog(f"  rebalance {_di}/{_n_dates} ({as_of}), {len(rows):,} panel rows so far")
        b0, b1 = benchf.iloc[i], benchf.iloc[i + horizon]
        bret = (b1 / b0 - 1.0) if (b0 and b0 > 0) else np.nan
        metrics, fwd, mktcap = [], {}, {}
        fwd_x = {h: {} for h in _extra_h}        # S22 — one dict per extra horizon
        for t in px:
            closes = frame[t].values
            if np.isnan(closes[i]) or closes[i] <= 0:
                continue
            sf1 = _pit(hist.get(t, []), as_of)
            if not sf1:
                continue
            shares = _f(sf1, "sharesbas", "shareswa", "shareswadil")
            if not shares:
                continue
            # Market cap: prefer Sharadar's own point-in-time figure from DAILY; fall back
            # to shares x price only when the bulk cache has no row for this date.
            _d = _daily_at(dly.get(t), as_of)
            if _d and _d[0]:
                mc = float(_d[0]) * 1e6                       # DAILY marketcap is in $mm
                mc_src = "daily"
            else:
                mc = float(closes[i]) * shares * (_f(sf1, "sharefactor") or 1.0)
                mc_src = "derived"
            if mc < S.MIN_MARKET_CAP_MM * 1e6:                # point-in-time floor: match the live
                continue                                       # screener's investable universe ($50M+)
            m = _sf1_to_metrics(t, sf1, float(closes[i]), mc)
            _md = meta.get(t) or {}
            m["sector"] = _md.get("sector") or ""
            m["_country"] = _md.get("country") or ""
            m["_category"] = _md.get("category") or ""
            # AUDIT B13 — RUN THE LIVE INVESTABILITY SCREEN IN THE BACKTEST TOO. The only
            # universe test here used to be the $50M point-in-time cap floor above. `prefilter`
            # — which drops warrant/unit/right suffixes, ETFs and funds, and sub-$1.00 names —
            # is called in `score_universe_now` and was NEVER called on this path, so the
            # validated deciles could contain penny stocks and warrant tickers the live book
            # will not buy. `size` is one-seventh of the composite and points straight at them,
            # and the 236 bps breakeven was computed on that book.
            _cat = str(m.get("_category") or "")
            m["is_fund"] = bool("ETF" in _cat.upper() or "FUND" in _cat.upper())
            _keep, _why = (True, "") if _B13_OFF else _prefilter(m)
            if not _keep:
                _pf_rejects[_why] = _pf_rejects.get(_why, 0) + 1
                continue
            cl = closes.tolist()
            m.update(_price_factors(cl, i))
            m.update(_price_extras(cl, i, bench=benchv))       # reversal / MAX / idio-vol
            _yoy(m, hist.get(t, []), as_of, shares, _f(sf1, "revenue"), _f(sf1, "assets"),
                 cut1=_cut1, cut2=_cut2)                       # growth + investment
            _sf1_extras(m, sf1, hist.get(t, []), as_of, cut1=_cut1)   # F-Score / accruals / cash OP
            _ttm_quality(m, hist.get(t, []), as_of)            # roe_ttm / roic_ttm (P6.2)
            _ed = earn.get(t)
            if _ed:
                from .pead import pead_signals
                m.update(pead_signals(cl, _cal64, benchv, _ed, as_of))
            isc = _insider_score_at(insh.get(t), as_of)
            if isc is not None:
                m["insider_score"] = isc                          # → insider theme (now backtestable)
            if with_insider_raw:
                # S3 — the unreduced (net, buys) the score is built from, so the register's
                # variants are functions of the SAME window rather than a re-mined one. Opt-in,
                # so the default panel's column set is untouched.
                _raw = _insider_raw_at(insh.get(t), as_of)
                if _raw is not None:
                    m["ins_net"], m["ins_buys"] = _raw
            if with_freshness:
                # S9 — days since the SF1 filing this row's fundamentals came from. The panel
                # already picks that row point-in-time; only its AGE was never carried.
                _dk = str((sf1 or {}).get("datekey") or (sf1 or {}).get("date") or "")
                if _dk:
                    m["days_since_filing"] = float(
                        (pd.Timestamp(as_of[:10]) - pd.Timestamp(_dk[:10])).days)
                _ia_age = _inst_age_at(inst.get(t), as_of, lag_days=inst_lag_days)
                if _ia_age is not None:
                    m["days_since_13f"] = float(_ia_age)
            ia = _inst_accum_at(inst.get(t), as_of, lag_days=inst_lag_days)
            if ia is not None:
                m["inst_accum"] = ia                              # → institutional theme
            ib = _inst_breadth_at(hold.get(t), as_of, lag_days=inst_lag_days)
            if ib is not None:
                m["inst_breadth"] = ib                            # → institutional (holder breadth)
            # SF3 per-manager detail. Exposed as factor INPUTS here; whether any of them
            # earns a place in the composite is for CPCV to decide (P4), so they are not
            # yet registered in NUMBER_THEME.
            _cg = cong.get(t)
            if _cg:
                from .congress import signals_at as _cg_at
                m.update(_cg_at(_cg, as_of))
            _ua = usasp.get(t)
            if _ua:
                from .usaspending import signals_at as _ua_at
                m.update(_ua_at(_ua, as_of))
            _e = e13d.get(t)
            if _e:
                from .edgar13d import signals_at as _e13_at
                m.update(_e13_at(_e, as_of))
            _si = shorts.get(t)
            if _si:
                from .short_interest import signals_at
                m.update(signals_at(_si, as_of))
            # Elite-manager conviction, lagged exactly like every other 13F input.
            _eq = elite.get(t) or {}
            if _eq:
                _ks = sorted(k for k in _eq if k <= _cut3)
                if _ks:
                    m["sm_elite_conviction"] = float(_eq[_ks[-1]])
            s3 = _sf3_at(sf3.get(t), as_of, lag_days=inst_lag_days, cut=_cut3)
            if s3 is not None:
                holders, val, conv, holders_prev = s3
                if conv is not None:
                    m["sm_conviction"] = conv                     # sum of position/manager AUM
                if holders:
                    m["sm_holders"] = float(holders)
                    if holders_prev:
                        # Breadth of buying: growth in the number of managers holding it.
                        m["sm_breadth"] = holders / float(holders_prev) - 1.0
                    if val:
                        # Average commitment per holder — a few big believers vs many
                        # index-tracking token positions.
                        m["sm_avg_position"] = float(val) / float(holders)
            # Diagnostic only: which market-cap source this row used, and how far the DAILY
            # market cap sits from shares x price. A recycled/spun-off ticker (SanDisk out of
            # Western Digital in 2025) inherits the parent's DAILY history and shows ~10x its
            # true cap, which pollutes `size` and the cost model. Ratio, not a hard reject —
            # a legitimate multi-share-class name diverges too, so this is a flag for P8.
            m["_mc_src"] = mc_src
            _derived_mc = float(closes[i]) * shares * (_f(sf1, "sharefactor") or 1.0)
            m["_mc_ratio"] = (mc / _derived_mc) if _derived_mc > 0 else None
            gr = _grades_at(grd.get(t), as_of)
            if gr is not None:
                m["rating_rev"] = gr[0]                           # → sentiment theme
                m["neg_rating_disp"] = -gr[1]                     # dispersion: less is better
            metrics.append(m)
            mktcap[t] = float(mc)                                  # for the market-cap regime split
            # Forward return, delisting-aware. If the name stops trading inside the holding
            # window the horizon-end price is now NaN (masked above), so use the LAST price it
            # actually traded at. That realizes the delisting outcome instead of discarding
            # the name — dropping it would quietly re-introduce the survivorship bias the
            # mask exists to remove.
            fwd[t] = _forward_return(closes, i, horizon, _n_cal)
            for _h in _extra_h:                                 # S22 — same rule, same array
                fwd_x[_h][t] = _forward_return(closes, i, _h, _n_cal)
        if len(metrics) < 10:
            continue
        from ..screener.factors import build_frame
        _by_ticker = {m["ticker"]: m for m in metrics}
        # S12 — the CAP TIER, computed WITHIN this date's cross-section (terciles, pre-committed;
        # not quintiles, so the smallest group stays large). Written onto the metrics dicts
        # before `build_frame` sees them, so the bucket-relative arm can group on it exactly the
        # way sector_neutral groups on `sector`.
        if bucket_relative_arms:
            _mc = [(m.get("ticker"), m.get("market_cap")) for m in metrics]
            _ok = sorted([x for x in _mc if x[1] is not None and x[1] == x[1]],
                         key=lambda x: x[1])
            _n = len(_ok)
            _tier = {}
            for _i, (_tk, _v) in enumerate(_ok):
                _tier[_tk] = "small" if _i < _n / 3 else ("mid" if _i < 2 * _n / 3 else "large")
            for m in metrics:
                m["cap_tier"] = _tier.get(m.get("ticker"), "?")
        fr = build_frame(metrics, sector_neutral=sector_neutral, residual_momentum=False)
        # S12 — one extra scoring per bucket-relative arm, from the SAME `metrics` list in the
        # SAME pass, so the arms are provably scored on one identical row set and the known
        # `insider` nondeterminism is common-mode and cancels out of every difference.
        fr_br = {p: build_frame(metrics, sector_neutral=sector_neutral, residual_momentum=False,
                                bucket_relative=col)
                 for p, col in (bucket_relative_arms or {}).items()}
        # S15 — sector-relative on the VALUE theme's inputs ALONE, the narrow variant the three
        # broad sector-neutral rejections left explicitly open. Same pass, same `metrics` list,
        # so the arms are provably scored on one identical row set.
        fr_sv = (build_frame(metrics, sector_neutral=sector_neutral, residual_momentum=False,
                             sector_relative_cols=VALUE_INPUTS)
                 if sector_value_arm else None)
        # SECTOR-NEUTRAL-B6 — the OTHER arm, scored from the SAME `metrics` list in the SAME
        # pass. `build_frame` copies its input (`pd.DataFrame(metrics)`) and never mutates the
        # caller's list, so the two calls differ by the flag and by nothing else.
        fr_sn = (build_frame(metrics, sector_neutral=(not sector_neutral),
                             residual_momentum=False) if sector_neutral_pair else None)
        # S20/S21 — one extra scoring per standardizer arm, same `metrics`, same pass, so the
        # known run-to-run nondeterminism is common-mode and cancels out of every difference.
        fr_std = {p: build_frame(metrics, sector_neutral=sector_neutral,
                                 residual_momentum=False, standardizer=fn)
                  for p, fn in (standardizer_arms or {}).items()}
        for t, r in fr.iterrows():
            fr_ret = fwd.get(t)
            if fr_ret is None or fr_ret != fr_ret:
                continue
            row = {"date": as_of, "ticker": t, "fwd_ret": float(fr_ret),
                   "bench_ret": (float(bret) if bret == bret else np.nan),
                   "market_cap": mktcap.get(t),
                   # Sector (TICKERS overlay, not point-in-time) — needed for the
                   # concentration RISK cap, which is a different thing from the
                   # sector-NEUTRAL ranking rejected in P10.
                   "sector": (_by_ticker.get(t) or {}).get("sector") or ""}
            # S22 — longer forward windows on the SAME row. NaN where the calendar ends before
            # the window does; see `_forward_return` on why that may not be a last-price fallback.
            for _h in _extra_h:
                _v = fwd_x[_h].get(t)
                row[f"fwd_ret_h{_h}"] = None if (_v is None or _v != _v) else float(_v)
            for theme in S.FACTORS_ALL:
                v = r.get(theme) if theme in fr.columns else None
                row[theme] = None if (v is None or pd.isna(v)) else float(v)
            # SECTOR-NEUTRAL-B6 — the paired arm's themes on the SAME row, so the two arms are
            # provably scored on one identical row set and any run-to-run nondeterminism in the
            # panel (the known `insider` one) is common-mode and cancels out of the difference.
            if fr_sn is not None:
                _rs = fr_sn.loc[t] if t in fr_sn.index else None
                for theme in S.FACTORS_ALL:
                    v = (_rs.get(theme) if (_rs is not None and theme in fr_sn.columns)
                         else None)
                    row["sn_" + theme] = None if (v is None or pd.isna(v)) else float(v)
            # S3 — the unreduced insider inputs on this same row, so the register's variants are
            # rebuilt from the SAME window the shipped score used. `insider_score` travels too,
            # so the incumbent arm can be reproduced from the panel rather than trusted.
            if with_insider_raw:
                _src3 = _by_ticker.get(t) or {}
                for _k in ("ins_net", "ins_buys", "insider_score"):
                    _v3 = _src3.get(_k)
                    row[_k] = None if (_v3 is None or pd.isna(_v3)) else float(_v3)
            # S16 — the RAW net share change `capital_discipline` reduces to a single z-score.
            # The decomposition into buyback / dilution / M&A is a function of this one number
            # plus a dated ACTIONS join, so emitting it is enough and the panel stays the
            # authority for the window. Opt-in, so the default column set is untouched.
            if with_issuance_raw:
                _src16 = _by_ticker.get(t) or {}
                _v16 = _src16.get("share_issuance")
                row["share_issuance"] = (None if (_v16 is None or pd.isna(_v16))
                                         else float(_v16))
            # S13 — the RAW trailing volatility, in levels. An inverse-volatility book needs
            # magnitudes, and the panel otherwise carries only `z_neg_vol`, from which a level
            # cannot be recovered. Opt-in, so the default column set is untouched.
            if with_vol_raw:
                _src13 = _by_ticker.get(t) or {}
                _v13 = _src13.get("realized_vol")
                row["realized_vol"] = (None if (_v13 is None or pd.isna(_v13))
                                       else float(_v13))
            # S8/S9 — HOW OLD each row's inputs are at this rebalance. `days_since_filing` is
            # what S9 asks to be ported from the options autopsy; `days_since_13f` is the age
            # of the quarter-end the institutional signal actually used. Opt-in, so the default
            # column set is untouched.
            if with_freshness:
                _srcf = _by_ticker.get(t) or {}
                for _k in ("days_since_filing", "days_since_13f"):
                    _vf = _srcf.get(_k)
                    row[_k] = None if (_vf is None or pd.isna(_vf)) else float(_vf)
            # S12 — the bucket-relative arms' themes, on this same row, plus the group labels
            # so control C7 can report group sizes and C8 the book's size exposure.
            if fr_br:
                _srcb = _by_ticker.get(t) or {}
                row["cap_tier"] = _srcb.get("cap_tier")
                row["bucket"] = _srcb.get("bucket")
                for _p, _fb in fr_br.items():
                    _rb = _fb.loc[t] if t in _fb.index else None
                    for theme in S.FACTORS_ALL:
                        v = (_rb.get(theme) if (_rb is not None and theme in _fb.columns)
                             else None)
                        row[f"{_p}_{theme}"] = None if (v is None or pd.isna(v)) else float(v)
            # S15 — the sector-relative-VALUE arm's themes, on this same row. Control C4 checks
            # that every NON-value theme comes back bit-identical to the deployed one, which is
            # what makes this the narrow experiment it claims to be.
            if fr_sv is not None:
                _rv = fr_sv.loc[t] if t in fr_sv.index else None
                for theme in S.FACTORS_ALL:
                    v = (_rv.get(theme) if (_rv is not None and theme in fr_sv.columns)
                         else None)
                    row["sv_" + theme] = None if (v is None or pd.isna(v)) else float(v)
            # S20/S21 — the standardizer arms' themes, on this same row.
            for _p, _fr in fr_std.items():
                _rr = _fr.loc[t] if t in _fr.index else None
                for theme in S.FACTORS_ALL:
                    v = (_rr.get(theme) if (_rr is not None and theme in _fr.columns) else None)
                    row[f"{_p}_{theme}"] = None if (v is None or pd.isna(v)) else float(v)
            if keep_numbers:
                for num in S.NUMBERS_ALL:
                    zc = "z_" + num
                    v = r.get(zc) if zc in fr.columns else None
                    row[zc] = None if (v is None or pd.isna(v)) else float(v)
                # Diagnostics for sanity_check: the subgroup label, the market-cap divergence,
                # and the RAW value ratios (the z-scores alone can't reveal an implausible
                # LEVEL, which is exactly what the currency bug produced).
                _src = _by_ticker.get(t) or {}
                # Which side of the value split this name fell on. `value` means different
                # things either side of it, so any value diagnostic that ignores the bucket is
                # averaging two different factors together.
                _bk = r.get("bucket") if "bucket" in fr.columns else None
                row["bucket"] = None if (_bk is None or pd.isna(_bk)) else str(_bk)
                row["is_foreign"] = bool(_src.get("_is_foreign"))
                row["fx_divisor"] = _src.get("_fx_divisor")
                row["mc_ratio"] = _src.get("_mc_ratio")
                row["ev_src"] = _src.get("_ev_src")
                row["ev_drift"] = _src.get("_ev_drift")
                for _rr in tuple(SANE_RANGES) + SANE_RANGE_EXEMPT:
                    v = _src.get(_rr)
                    row["raw_" + _rr] = None if v is None else float(v)
            rows.append(row)
    _out = pd.DataFrame(rows)
    _out.attrs["survivorship_mask_coverage"] = _mask_coverage   # AUDIT B14
    LAST_PANEL_DIAGNOSTICS["survivorship_mask_coverage"] = _mask_coverage
    # AUDIT B6 / B22 / M6 — stamp the window this panel actually covers, and the SIZE of
    # each cross-section. Two headline blocks in the results file used to disagree about
    # their window with no marker, and a thin 1999 cross-section counted as one observation
    # of equal weight to a full 2024 one. Both are now visible per run.
    _cs = {}
    if len(_out) and "date" in _out.columns:
        _cs = {str(k): int(v) for k, v in _out.groupby("date").size().items()}
    _sizes = sorted(_cs.values())
    _win = {
        "available_start": _cal_full[0], "available_end": _cal_full[1],
        "available_trading_days": _cal_full[2],
        "retained_start": str(cal[0].date()) if len(cal) else None,
        "retained_end": str(cal[-1].date()) if len(cal) else None,
        "retained_trading_days": int(len(cal)),
        "calendar_cut_days": int(_CAL_DAYS),
        "truncation": "shared_calendar",     # AUDIT B6: never per-ticker
        "horizon": int(horizon), "rebalance_days": int(rebalance_days),
        "extra_horizons": list(_extra_h),        # S22 — provenance for the term-structure run
        # AUDIT X2 — which of the `rebalance_days` possible grids this run used. 0 is the
        # historical grid every prior number in the project was measured on.
        "grid_offset": int(grid_offset),
        "n_rebalance_dates": len(_cs),
        "cross_section_min": (_sizes[0] if _sizes else None),
        "cross_section_median": (_sizes[len(_sizes) // 2] if _sizes else None),
        "cross_section_max": (_sizes[-1] if _sizes else None),
        "cross_section_by_date": _cs,
        # AUDIT B13 — what the live investability screen removed, and the one test in
        # it that STILL cannot bind here.
        "prefilter_rejects": dict(sorted(_pf_rejects.items(), key=lambda kv: -kv[1])),
        "prefilter_adv_wired": False,
        "prefilter_note": ("MIN_AVG_DOLLAR_VOLUME has never bound on this path and "
                           "still does not: the price export on disk carries date+close "
                           "only, so avg_dollar_volume cannot be computed here. Wiring "
                           "it needs SEP volume in the panel loader (audit B13)."),
    }
    _out.attrs["panel_window"] = _win
    LAST_PANEL_DIAGNOSTICS["panel_window"] = _win
    return _out


# AUDIT B14 — a price series that stops this far short of the panel end, with no ACTIONS
# delisting row to explain it, is the signature of a delisting the mask MISSED. Two quarters
# is well past any ordinary data gap and well inside the horizon over which a forward-filled
# last close would start contributing fake flat returns.
STALE_TAIL_DAYS = 180

# AUDIT B14 — diagnostics from the most recent panel build, for the results writer. The
# panel returns a bare DataFrame and DataFrame.attrs does not survive every pandas
# operation, so the writer reads this instead of re-deriving anything.
LAST_PANEL_DIAGNOSTICS = {}

STALE_PRICE_MAX_DAYS = 10          # trading days a name may be quiet before it's not investable


def score_universe_now(provider, tickers, benchmark="SPY", lookback_years=3,
                       as_of=None, stale_days=STALE_PRICE_MAX_DAYS):
    """Score the WHOLE universe as of the latest available date -> live scan-style rows.

    build_fundamental_panel deliberately drops the final `horizon` days, because every row it
    emits needs a forward return to score against. A live book is exactly the rows it throws
    away: the most recent cross-section, with no future to measure. This reproduces the panel's
    metric construction for that one date and scores it with the LIVE weights, so the tracked
    book is built by the same code path the backtest validated.

    Returns rows shaped like a screener scan (ticker / price / market_cap / hot_score /
    composite / rank / bucket), consumable directly by valquo_index.build_index.

    `sector` is empty: the Sharadar export carries no sector column (see CLAUDE.md). That is a
    known gap, not an oversight — it means the exported book has no sector breakdown.
    """
    import sys as _sys
    import time as _time
    TD = 252
    _t0 = _time.time()

    def _prog(msg):
        print(f"[book] {_time.time()-_t0:5.0f}s  {msg}", file=_sys.stderr, flush=True)

    def series(t):
        d, c = provider.price_history(t, days=TD * lookback_years + 60)
        return pd.Series(c, index=pd.to_datetime(d)) if (d and c and len(c) > TD) else None

    _prog(f"loading {len(tickers)} tickers")
    px, hist, insh, inst, grd, hold, dly, sf3 = {}, {}, {}, {}, {}, {}, {}, {}
    last_seen = {}
    for _i, t in enumerate(tickers):
        if _i and _i % 500 == 0:
            _prog(f"  {_i}/{len(tickers)}, {len(px)} usable")
        s = series(t)
        if s is None or len(s) <= TD:
            continue
        px[t] = s
        last_seen[t] = s.index[-1]
        hist[t] = sorted(provider.fundamentals_history(t) or [],
                         key=lambda r: (r.get("datekey") or r.get("date") or ""))
        insh[t] = _prep_insider(provider.insider_history(t) or [])
        _ih = provider.institutional_history(t) or []
        inst[t] = _prep_inst(_ih)
        hold[t] = _prep_holders(_ih)
        grd[t] = _prep_grades(provider.grades_history(t) or []) \
            if hasattr(provider, "grades_history") else None
        dly[t] = provider.daily_history(t) if hasattr(provider, "daily_history") else []
        sf3[t] = provider.sf3_for(t) if hasattr(provider, "sf3_for") else {}
    if not px:
        return []

    frame = pd.DataFrame(px).sort_index().ffill()
    _delisted = {}
    try:
        if hasattr(provider, "delisted_map"):
            _delisted = provider.delisted_map() or {}
    except Exception:
        _delisted = {}
    for t in frame.columns:
        dd = _delisted.get(str(t).upper())
        if dd:
            m = frame.index > pd.to_datetime(dd)
            if m.any():
                frame.loc[m, t] = np.nan
    cal = frame.index
    i = len(cal) - 1 if as_of is None else int(np.searchsorted(cal.values,
                                                              np.datetime64(str(as_of)[:10]), "right") - 1)
    if i < TD:
        return []
    asof = str(cal[i].date())
    # ffill carries a dead name's last print forward forever, which would put stale quotes in
    # a live book. Require a real recent observation, not a carried-forward one.
    cutoff = cal[max(0, i - stale_days)]
    fresh = {t for t, d in last_seen.items() if d >= cutoff}
    _prog(f"scoring {len(px)} names as of {asof} ({len(fresh)} with fresh prices)")

    bench = series(benchmark)
    benchv = (bench.reindex(cal).ffill().values.tolist() if bench is not None else None)

    _cut1 = str((cal[i] - pd.Timedelta(days=365)).date())
    _cut2 = str((cal[i] - pd.Timedelta(days=730)).date())
    _cut3 = str((cal[i] - pd.Timedelta(days=45)).date())
    metrics, dropped_mc = [], []
    for t in px:
        if t not in fresh or t == benchmark:
            continue
        closes = frame[t].values
        if np.isnan(closes[i]) or closes[i] <= 0:
            continue
        sf1 = _pit(hist.get(t, []), asof)
        if not sf1:
            continue
        shares = _f(sf1, "sharesbas", "shareswa", "shareswadil")
        if not shares:
            continue
        _d = _daily_at(dly.get(t), asof)
        _derived_mc = float(closes[i]) * shares * (_f(sf1, "sharefactor") or 1.0)
        mc = (float(_d[0]) * 1e6 if (_d and _d[0]) else _derived_mc)
        if mc < S.MIN_MARKET_CAP_MM * 1e6:
            continue
        # Recycled / spun-off tickers can inherit a parent's DAILY history, so DAILY market cap
        # and shares x price disagree wildly (AIV 71x, EQC 53x on the panel). A book is meant to
        # be traded, and a name whose SIZE cannot be established has no business in it — market
        # cap drives large-cap eligibility, position sizing and the cost model. When the two
        # independent estimates disagree by more than MC_DIVERGENCE_FACTOR we cannot tell which
        # is right, so the name is dropped rather than shown at a number nobody should trust.
        #
        # NOTE — this does NOT catch the SanDisk/WDC case the code audit attributed to it, and
        # investigation says that case is not this bug: SNDK's DAILY cap ($336.7B) and its
        # shares x price ($212.7B) agree to 1.6x, its 148M share count is plausible, and its
        # price ran 48.60 -> 1436.56 over 17 months with ZERO day-over-day discontinuities
        # (WDC 10.3x, MU 8.5x — the whole storage complex moved together). The figure is
        # internally consistent; if it is still wrong, the error is upstream in the PRICE, which
        # both estimates share and no cross-check between them can see.
        #
        # The BACKTEST deliberately keeps these rows and only flags them (sanity_check), so the
        # validated history is never silently re-cut by a guard added later.
        if _derived_mc > 0:
            _ratio = mc / _derived_mc
            if _ratio > MC_DIVERGENCE_FACTOR or _ratio < 1.0 / MC_DIVERGENCE_FACTOR:
                dropped_mc.append({"ticker": t, "daily_mc": mc, "derived_mc": _derived_mc,
                                   "ratio": _ratio})
                continue
        m = _sf1_to_metrics(t, sf1, float(closes[i]), mc)
        cl = closes.tolist()
        m.update(_price_factors(cl, i))
        m.update(_price_extras(cl, i, bench=benchv))
        _yoy(m, hist.get(t, []), asof, shares, _f(sf1, "revenue"), _f(sf1, "assets"),
             cut1=_cut1, cut2=_cut2)
        _sf1_extras(m, sf1, hist.get(t, []), asof, cut1=_cut1)
        _ttm_quality(m, hist.get(t, []), asof)
        isc = _insider_score_at(insh.get(t), asof)
        if isc is not None:
            m["insider_score"] = isc
        ia = _inst_accum_at(inst.get(t), asof, lag_days=45)
        if ia is not None:
            m["inst_accum"] = ia
        ib = _inst_breadth_at(hold.get(t), asof, lag_days=45)
        if ib is not None:
            m["inst_breadth"] = ib
        s3 = _sf3_at(sf3.get(t), asof, lag_days=45, cut=_cut3)
        if s3 is not None:
            holders, val, conv, holders_prev = s3
            if conv is not None:
                m["sm_conviction"] = conv
            if holders:
                m["sm_holders"] = float(holders)
                if holders_prev:
                    m["sm_breadth"] = holders / float(holders_prev) - 1.0
                if val:
                    m["sm_avg_position"] = float(val) / float(holders)
        gr = _grades_at(grd.get(t), asof)
        if gr is not None:
            m["rating_rev"], m["neg_rating_disp"] = gr[0], -gr[1]
        metrics.append(m)

    if not metrics:
        return []
    # Same prefilter the live scan applies (warrants/units/penny/nano-cap).
    from ..screener.factors import build_frame, prefilter
    kept = [m for m in metrics if prefilter(m)[0]]
    _prog(f"{len(kept)} names pass the live prefilter (from {len(metrics)} scored)")
    if not kept:
        return []

    from ..screener.screen import _composites
    fr = build_frame(kept, sector_neutral=False, residual_momentum=False)
    fr["composite"] = _composites(fr, S.WEIGHTS_ESTABLISHED, S.WEIGHTS_SPECULATIVE)
    fr = fr[fr["composite"].notna()].copy()
    if fr.empty:
        return []
    fr["hot_score"] = fr["composite"].rank(pct=True) * 99 + 1
    fr = fr.sort_values("composite", ascending=False)
    fr["rank"] = range(1, len(fr) + 1)
    by_ticker = {m["ticker"]: m for m in kept}
    rows = []
    for tkr, r in fr.iterrows():
        src = by_ticker.get(tkr, {})
        rows.append({"ticker": tkr, "name": "", "sector": "",
                     "bucket": r.get("bucket"),
                     "price": src.get("price"), "market_cap": src.get("market_cap"),
                     "hot_score": float(r["hot_score"]), "composite": float(r["composite"]),
                     "rank": int(r["rank"])})
    rows.sort(key=lambda x: x["rank"])
    if dropped_mc:
        _prog(f"dropped {len(dropped_mc)} name(s) on market-cap divergence: "
              + ", ".join(f"{d['ticker']} ({d['ratio']:.0f}x)" for d in dropped_mc[:6]))
    return {"as_of": asof, "rows": rows, "dropped_mc_divergence": dropped_mc}


# =============================================================================================
# AUDIT B7 — THE COMPOSITE. One definition, used by selection, measurement and live.
# =============================================================================================
def composite(Z, wv):
    """Weighted mean of the present z-scores, RENORMALISED by the weight actually present.

    There used to be three of these in the tree and they did not agree.

      * SELECTION (`_weighted_optimize`, `walk_forward`, `cpcv_validate`) renormalised by the
        present-weight mass — a name missing a theme was scored on what it HAS.
      * MEASUREMENT (`quantile_backtest`, `_strategy_returns`, `_backtest`, `_backtest_hold`,
        `regime_split`, `turnover_and_costs`, `after_tax_backtest`) did NOT: a missing theme
        contributed a hard zero, which after z-scoring is exactly the cross-sectional AVERAGE,
        so an incomplete name was dragged toward the middle of the ranking.
      * LIVE (`screen.py` -> `factors.build_frame` -> `cross_sectional.composite_score`)
        renormalised AND applied sector-neutral ranking and residual momentum.

    That mattered because the missing data is not random. `institutional` is absent on 38.6% of
    rows and `insider` on 15%, and both absences track size and coverage — so under the
    measurement composite the extreme deciles were systematically biased toward data-complete
    names (larger, better covered, institutionally held). **The top-decile alpha and long-short
    t were computed under one composite while the weights that produced them were chosen under
    another, and the live product used a third.** No shipped code path reproduced the
    backtested composite exactly.

    Renormalisation is the convention kept, for two reasons: it is what the SELECTION step
    already used, so the deployed weights were chosen under it; and scoring a name on the
    themes it actually has is the defensible answer to missing data, where "treat it as exactly
    average" quietly rewards coverage instead of merit.

    `Z` is (n_names, n_cols) z-scores with NaN for missing; `wv` is the matching weight vector.
    A row with no present weight at all returns NaN rather than 0.0 — it has no opinion, and
    0.0 would place it mid-pack.
    """
    present = ~np.isnan(Z)
    denom = (present * wv).sum(axis=1)
    denom = np.where(denom == 0, np.nan, denom)
    return np.nansum(np.where(present, Z, 0.0) * wv, axis=1) / denom


def composite_from_frame(sub, cols, weights, zscore):
    """`composite` over a per-date slice whose columns still need standardising.

    ATTRIBUTION TOGGLE (default OFF): `EDGE_AUDIT_B7_LEGACY_COMPOSITE=true` restores the old
    MEASUREMENT convention — a plain weighted sum with missing themes read as 0.0, i.e. as
    exactly average. Selection (`composite` called directly) always renormalised and is left
    alone, which is precisely the disagreement B7 removed. This exists to measure B7's own
    contribution to the headline, not as a supported mode.
    """
    import os as _os_b7
    Z = np.column_stack([zscore(sub[c]).values for c in cols])
    wv = np.array([float(weights.get(c, 0.0)) for c in cols], dtype=float)
    if _os_b7.environ.get("EDGE_AUDIT_B7_LEGACY_COMPOSITE", "").lower() == "true":
        return np.nansum(np.where(~np.isnan(Z), Z, 0.0) * wv, axis=1)
    return composite(Z, wv)


def placebo_signal_cols(panel) -> list:
    """The columns a placebo must destroy: every scored theme, plus the standardized
    per-number `z_*` columns the per-signal diagnostics read. Everything else — `date`,
    `ticker`, `fwd_ret`, `marketcap`, `sector` — is deliberately left ALONE, so the
    cost model, the regime split and the benchmark keep operating on real data and only
    the signal→return link is broken."""
    themes = set()
    for _v in S.BUCKET_FACTORS.values():
        themes.update(_v)
    return [c for c in panel.columns if c in themes or str(c).startswith("z_")]


def placebo_panel(panel, seed, cols=None):
    """AUDIT X7 — the same panel with a definitionally worthless signal in it.

    The options bot has a no-edge self-test; the equity pipeline has never had one. Without
    it, every threshold in this project — the IC *t* > 2.0 bar, the PBO < 50% bar, the 0.25
    t-gain margin on a held-out split — is a convention rather than a measurement, because
    nobody has ever asked what those statistics do when the signal is known to be nothing.

    METHOD. Within each rebalance date, permute the signal columns AS A BLOCK across the
    names present. This is the strongest available null:

      * every theme keeps its exact per-date distribution (it is the same numbers);
      * the missingness PATTERN is preserved exactly — it travels with the row, so the
        per-date count of each missing-theme combination is identical;
      * the cross-theme correlation matrix is preserved exactly, because whole rows move
        together — so the weight schemes that read Sigma still see a real Sigma;
      * `fwd_ret`, `marketcap` and `sector` do not move, so the ONLY thing destroyed is
        the association between the signal and the return.

    Permuting whole rows rather than the final composite matters: it propagates through
    weight SELECTION as well as measurement, so CPCV, PBO and the Deflated Sharpe are
    exercised end to end rather than being handed a pre-shuffled score. And because the
    composite of a permuted row-block IS the permuted composite, it satisfies the
    catalogue's "shuffled composite" specification as a special case.

    Deterministic in `seed` — a placebo whose own numbers cannot be reproduced would be a
    poor instrument for calibrating reproducibility thresholds.
    """
    cols = placebo_signal_cols(panel) if cols is None else list(cols)
    if not cols:
        raise ValueError("placebo_panel: no signal columns found to permute")
    rng = np.random.default_rng(int(seed))
    out = panel.copy()
    vals = {c: panel[c].to_numpy(copy=True) for c in cols}
    for _d, idx in panel.groupby("date", sort=False).indices.items():
        if len(idx) < 2:
            continue
        perm = idx[rng.permutation(len(idx))]
        for c in cols:
            vals[c][idx] = vals[c][perm]      # RHS fancy-indexes to a copy first — safe
    for c in cols:
        out[c] = vals[c]
    return out


def _backtest(panel, cols, weights, top_n=20, horizon=252):
    """Top-N-by-composite portfolio vs the benchmark. The panel dates are non-overlapping
    holding periods (rebalance == horizon), so compounding is valid; we report an annualized
    CAGR (interpretable) alongside the total."""
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    strat, bench, ew = [], [], []
    for d in dates:
        sub = panel[panel["date"] == d]
        if len(sub) < top_n:
            continue
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        order = np.argsort(-comp)[:top_n]
        s = sub["fwd_ret"].values[order]
        b = sub["bench_ret"].values[order]
        allret = sub["fwd_ret"].values                    # every name this date → equal-weight bar
        sm = float(np.nanmean(s)) if np.isfinite(s).any() else float("nan")
        bm = float(np.nanmean(b)) if np.isfinite(b).any() else float("nan")
        em = float(np.nanmean(allret)) if np.isfinite(allret).any() else float("nan")
        if sm != sm or bm != bm:            # need BOTH to compare vs the benchmark → keep aligned
            continue
        strat.append(sm)
        bench.append(bm)
        ew.append(em if em == em else bm)   # equal-weight-of-universe: the fair, cap-neutral bar
    if not strat:
        return None
    tot = float(np.prod([1 + x for x in strat]) - 1)
    btot = float(np.prod([1 + x for x in bench]) - 1)
    etot = float(np.prod([1 + x for x in ew]) - 1)
    years = max(1e-6, len(strat) * horizon / 252.0)
    cagr = float((1 + tot) ** (1.0 / years) - 1) if tot > -1 else None
    bcagr = float((1 + btot) ** (1.0 / years) - 1) if btot > -1 else None
    ecagr = float((1 + etot) ** (1.0 / years) - 1) if etot > -1 else None
    hit = float(np.mean([1.0 if strat[k] > bench[k] else 0.0 for k in range(len(strat))]))
    return {"total_return": tot, "bench_return": btot, "cagr": cagr, "bench_cagr": bcagr,
            "ew_cagr": ecagr, "ew_alpha": (None if (cagr is None or ecagr is None) else cagr - ecagr),
            "n_periods": len(strat), "years": round(years, 1),
            "avg_period_alpha": float(np.mean([strat[k] - bench[k] for k in range(len(strat))])),
            "hit_rate": hit}


def _backtest_hold(panel, cols, weights, top_n=20, exit_rank=None, min_hold=2, horizon=63,
                   trailing_stop=None, take_profit=None, stop_loss=None, fv_at_or_above=None,
                   disable_rank_exit=False, cost_bps_one_way=None, return_series=False):
    """Event-driven backtest that mirrors the LIVE sell logic: BUY the top-N by composite,
    then HOLD each name until it falls out of the top `exit_rank` (a hysteresis band, so a
    still-good name that merely slips isn't churned) — subject to a minimum hold. Optional
    `trailing_stop` (e.g. 0.3) also sells if a name falls that far from its own peak since
    entry (a profit-lock / reversal catch). Holding periods are variable: a strong name
    compounds for years. 'Hold the gems, sell what's no longer worth holding', not churn.

    S23 — the alternative exits are ADDITIONAL and opt-in, so with every new argument at its
    default this function is bit-identical to what it was (pinned by
    test_s23_the_new_exits_are_opt_in_and_change_nothing). One implementation, not a second
    copy that can drift from the shipped one.

      * `take_profit` / `stop_loss` — cumulative return since entry, e.g. 0.25 / 0.08. These
        are evaluated at REBALANCE MARKS ONLY, because the panel carries no intra-quarter path,
        so they trigger LESS often than a true path-dependent rule would. That biases the
        result in FAVOUR of a TP/SL arm, which is stated in PREREG_s23_exit_rule.md §5a and is
        why a NEGATIVE result on these arms is the trustworthy direction.
      * `fv_at_or_above` — a set of (date, ticker) pairs at which the price has reached the
        point-in-time fair value. Precomputed by the caller through the LIVE engine, never
        re-derived here.
      * `disable_rank_exit` — the never-sell control. Its book grows without bound, so its
        size is NOT comparable to the others; that is the control's whole point.
      * `cost_bps_one_way` — charge turnover. On an equal-weighted book each traded name pays
        its own weight's worth, so the period drag is exactly
        `bps/1e4 * (n_bought + n_sold) / n_held`. Off by default, which is the historical
        (B17-flagged) behaviour: this function has always charged nothing.

    `return_series=True` adds the per-period draws and the per-period book/trade counts, which
    a PAIRED comparison of two arms needs and a summary cannot reconstruct (RUN_RULES A9).
    """
    from ..screener.cross_sectional import zscore
    exit_rank = exit_rank or (top_n * 2)
    dates = sorted(panel["date"].unique())
    by_date = {d: panel[panel["date"] == d] for d in dates}
    held, port, bench, ew, hold_lens = {}, [], [], [], []   # held[t] = [entry_i, cum_factor, peak_factor]
    held_counts = []                                       # AUDIT B17: realised book size
    exit_reasons, used_dates = {}, []                      # S23
    gross_series, drag_series, bought_series, sold_series = [], [], [], []
    for i, d in enumerate(dates):
        sub = by_date[d]
        tickers = sub["ticker"].values
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        order = np.argsort(-comp)
        rank = {tickers[order[r]]: r + 1 for r in range(len(order))}
        # PERFORMANCE (S23) — hoist the column out of the comprehension. `sub["fwd_ret"]` inside
        # it was re-evaluated once per NAME, so a 1,650-name cross-section extracted the column
        # 1,650 times and each extraction deep-copied the panel's `.attrs` through pandas'
        # `__finalize__`. Measured: 114,774 column extractions and 61 of 70 seconds per call, on
        # a function `run_backtests` and `sweep_hold_params` both drive. Identical results.
        _fwd_vals = sub["fwd_ret"].values
        fwd = {tickers[j]: _fwd_vals[j] for j in range(len(tickers))}
        n_sold_i = 0
        for t in list(held):                              # SELL: band drop-out (past min-hold) or stop
            entry_i, cum, peak = held[t]
            dd = (cum / peak - 1.0) if peak > 0 else 0.0
            aged = (i - entry_i) >= min_hold
            stop_hit = (trailing_stop is not None) and (dd <= -trailing_stop)
            rank_out = (not disable_rank_exit) and (t not in rank or rank[t] > exit_rank) and aged
            # S23 — cumulative return since entry, at this rebalance mark. `cum` is the running
            # product of realised period returns, so `cum - 1` IS that cumulative return.
            ret_cum = cum - 1.0
            tp_hit = (take_profit is not None) and aged and (ret_cum >= take_profit)
            sl_hit = (stop_loss is not None) and aged and (ret_cum <= -stop_loss)
            fv_hit = (fv_at_or_above is not None) and aged and ((d, t) in fv_at_or_above)
            if stop_hit or rank_out or tp_hit or sl_hit or fv_hit:
                # one reason per exit, in a fixed precedence so the counts sum to the exits
                reason = ("stop" if stop_hit else "take_profit" if tp_hit else
                          "stop_loss" if sl_hit else "fair_value" if fv_hit else "rank")
                exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
                hold_lens.append(i - entry_i)
                del held[t]
                n_sold_i += 1
        n_before = len(held)
        for r in range(min(top_n, len(order))):           # BUY: new top-N
            held.setdefault(tickers[order[r]], [i, 1.0, 1.0])
        n_bought_i = len(held) - n_before
        rets = []
        for t in held:                                    # this period's return + update each name's path
            fr = fwd.get(t)
            if fr is not None and fr == fr:               # exclude both None (dropped out) and NaN
                rets.append(fr)
                held[t][1] *= (1.0 + fr)
                held[t][2] = max(held[t][2], held[t][1])
        br = sub["bench_ret"].values
        allr = sub["fwd_ret"].values                      # equal-weight-of-universe bar (rebalanced)
        pr = float(np.mean(rets)) if rets else float("nan")
        bm = float(np.nanmean(br)) if np.isfinite(br).any() else float("nan")
        em = float(np.nanmean(allr)) if np.isfinite(allr).any() else float("nan")
        if pr == pr and bm == bm:
            # S23 — turnover drag. Equal-weighted book, so each traded name costs its own
            # weight's worth: bps * (bought + sold) / held. Zero when costs are off.
            drag = 0.0
            if cost_bps_one_way and len(held):
                drag = (float(cost_bps_one_way) / 1e4) * (n_bought_i + n_sold_i) / float(len(held))
            gross_series.append(pr)
            drag_series.append(drag)
            bought_series.append(n_bought_i)
            sold_series.append(n_sold_i)
            port.append(pr - drag)
            bench.append(bm)
            ew.append(em if em == em else bm)
            held_counts.append(len(held))      # AUDIT B17
            used_dates.append(str(d)[:10])
    if not port:
        return None
    tot = float(np.prod([1 + x for x in port]) - 1)
    btot = float(np.prod([1 + x for x in bench]) - 1)
    etot = float(np.prod([1 + x for x in ew]) - 1)
    years = max(1e-6, len(port) * horizon / 252.0)
    cagr = float((1 + tot) ** (1.0 / years) - 1) if tot > -1 else None
    bcagr = float((1 + btot) ** (1.0 / years) - 1) if btot > -1 else None
    ecagr = float((1 + etot) ** (1.0 / years) - 1) if etot > -1 else None
    hit = float(np.mean([1.0 if port[k] > bench[k] else 0.0 for k in range(len(port))]))
    avg_hold = (float(np.mean(hold_lens)) * horizon / 252.0) if hold_lens else None
    return {"cagr": cagr, "bench_cagr": bcagr, "ew_cagr": ecagr,
            "ew_alpha": (None if (cagr is None or ecagr is None) else cagr - ecagr),
            "total_return": tot, "bench_return": btot,
            "n_periods": len(port), "years": round(years, 1), "hit_rate": hit,
            "avg_hold_years": round(avg_hold, 1) if avg_hold else None, "exit_rank": exit_rank,
            # AUDIT B17 — THE REALISED BOOK SIZE, because this is NOT a top-N book. A name is
            # sold only when it falls below `exit_rank`, which defaults to `top_n * 2`, so with
            # top_n = 25 the held set converges toward roughly FIFTY positions. The results file
            # presented the resulting CAGR as the top-25 hold strategy. It also charges NO costs
            # and NO taxes, unlike every other book in the file — so it is not merely the
            # noisiest number, it describes a different portfolio measured without the frictions
            # every other book pays. Both facts now travel with the number.
            "target_n": int(top_n),
            "held_median": (int(np.median(held_counts)) if held_counts else None),
            "held_min": (int(min(held_counts)) if held_counts else None),
            "held_max": (int(max(held_counts)) if held_counts else None),
            "charges_costs": bool(cost_bps_one_way), "charges_taxes": False,
            # S23 — opt-in diagnostics. `exit_reasons` sums to the number of completed spells,
            # so "which rule actually fired" is measurable rather than inferred.
            **({"cost_bps_one_way": float(cost_bps_one_way)} if cost_bps_one_way else {}),
            **({"exit_reasons": dict(exit_reasons),
                "avg_bought_per_period": float(np.mean(bought_series)) if bought_series else None,
                "avg_sold_per_period": float(np.mean(sold_series)) if sold_series else None,
                "avg_drag_per_period": float(np.mean(drag_series)) if drag_series else None,
                "series": {"dates": used_dates, "net": list(port), "gross": gross_series,
                           "drag": drag_series, "bench": list(bench), "ew": list(ew),
                           "held": [int(x) for x in held_counts],
                           "bought": bought_series, "sold": sold_series}}
               if return_series else {}),
            # S28 — the shape of the hold book's own per-period returns, and of its EXCESS over
            # the equal-weight benchmark. Reporting only. The excess is the object `alpha_vs_
            # equal_weight` is a mean of, so its distribution is the honest companion to that
            # number; B17's label_warning below applies to every figure in this block, the
            # distribution included.
            **_hold_distribution(used_dates, port, ew),
            "label_warning": ("realised book size is ~exit_rank, NOT top_n; gross of costs and "
                              "taxes unlike every other book in this file (audit B17)")}


def _hold_distribution(dates, port, ew):
    """S28 — per-period shape for the hold book. Never raises: a reporting block must not be
    able to fail a completed backtest, and an empty series degrades to an empty dict."""
    try:
        from .statistics import distribution as _dist
        p, e = list(port), list(ew)
        if not p:
            return {}
        out = {"return_distribution": _dist(p, dates)}
        if len(e) == len(p):
            out["excess_vs_equal_weight_distribution"] = _dist(
                [a - b for a, b in zip(p, e)], dates)
        return out
    except Exception:                                       # noqa: BLE001
        return {}


def sweep_hold_params(panel, cols, weights, top_n=25, horizon=63):
    """Sweep each adjustable parameter of the hold-until-exit strategy and report its alpha
    in the FIRST half vs the SECOND half of history separately. Anti-overfit rule: trust a
    value only where BOTH halves agree — a spike in one half is noise, not signal. Shows the
    whole curve; does NOT auto-pick the max (that's how backtests fool you)."""
    dates = sorted(panel["date"].unique())
    if len(dates) < 8:
        return {"status": "insufficient history for a split sweep"}
    mid = dates[len(dates) // 2]
    first, second = panel[panel["date"] < mid], panel[panel["date"] >= mid]

    def alpha(sub, **kw):
        r = _backtest_hold(sub, cols, weights, horizon=horizon, **kw)
        return None if not r else round((r.get("cagr") or 0.0) - (r.get("bench_cagr") or 0.0), 4)

    def sweep(values, kwfn):
        return [{"value": v, "first_half_alpha": alpha(first, **kwfn(v)),
                 "second_half_alpha": alpha(second, **kwfn(v))} for v in values]

    return {
        "note": "alpha/yr vs S&P, first half vs second half. Trust values where BOTH agree; "
                "ignore a spike in only one half (that's overfitting).",
        "default": {"exit_band_xN": 2.0, "min_hold_periods": 2, "top_n": top_n, "trailing_stop_pct": None},
        "exit_band_xN": sweep([1.5, 2.0, 2.5, 3.0, 4.0, 5.0],
                              lambda m: {"top_n": top_n, "exit_rank": int(top_n * m)}),
        "min_hold_periods": sweep([1, 2, 3, 4], lambda mh: {"top_n": top_n, "min_hold": mh}),
        "top_n": sweep([10, 15, 20, 25, 30], lambda n: {"top_n": n}),
        "trailing_stop_pct": sweep([None, 0.20, 0.30, 0.40],
                                   lambda s: {"top_n": top_n, "trailing_stop": s}),
    }


def _rankdata(x):
    order = x.argsort()
    ranks = np.empty(len(x), dtype=float)
    ranks[order] = np.arange(len(x), dtype=float)
    return ranks


def _spearman(a, b):
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    m = ~(np.isnan(a) | np.isnan(b))
    if int(m.sum()) < 5:
        return np.nan
    ar = _rankdata(a[m]); br = _rankdata(b[m])
    ar -= ar.mean(); br -= br.mean()
    denom = np.sqrt((ar * ar).sum() * (br * br).sum())
    return float((ar * br).sum() / denom) if denom > 0 else np.nan


# AUDIT M2 — these four are now thin delegations to `edge/statistics.py`, which holds the ONE
# cross-date inference definition. They keep their names and their exact semantics because the
# published record and every pre-committed gate read the keys they feed; what changed is that
# there is no longer a second copy of the arithmetic here to drift from the first.
def _tstat(series):
    """Naive i.i.d. t-statistic of a series' mean against zero. DIAGNOSTIC ONLY (audit M2)."""
    return _stats.naive_tstat(series)


def _nw_tstat(series, lag=1):
    """AUDIT R9 — Newey-West (Bartlett) HAC t-statistic of the mean against zero."""
    return _stats.hac_tstat(series, lag=lag)


def _ljung_box(series, lags=4):
    """AUDIT R9 — Ljung-Box Q on a series, so the independence assumption is VISIBLE."""
    return _stats.ljung_box(series, lags=lags)


def _chi2_sf(x, k):
    """Upper-tail chi-square probability (audit M2: one definition, in `statistics.py`)."""
    return _stats.chi2_sf(x, k)


def _inference(series, lag=1, ljung_lags=4):
    """AUDIT M2 — the clustered-by-default inference block for a cross-date series.

    Additive: it sits BESIDE the existing `*_tstat` / `*_tstat_nw` keys rather than
    replacing them, because those keys are what the published record and the
    pre-committed gates read (PREREG_m2_m6.md §2). `t` here is the HAC statistic and
    equals `*_tstat_nw` by construction; `t_naive` equals `*_tstat`.
    """
    return _stats.mean_inference(series, lag=lag, ljung_lags=ljung_lags)


def _base_weights(cols, bucket):
    src = S.WEIGHTS_ESTABLISHED if bucket == "established" else S.WEIGHTS_SPECULATIVE
    base = {c: src.get(c, 0.0) for c in cols}
    tot = sum(base.values()) or 1.0
    return {c: v / tot for c, v in base.items()}


def _full_weights(rec, bucket):
    """Expand the optimizer's weights (over the factors that had data) back to the FULL
    theme set, filling absent themes with their small defaults and renormalizing — so the
    adopted/pasted weights always carry every theme, not a subset."""
    src = S.WEIGHTS_ESTABLISHED if bucket == "established" else S.WEIGHTS_SPECULATIVE
    full = {k: (rec.get(k) if rec.get(k) is not None else src.get(k, 0.0)) for k in src}
    tot = sum(full.values()) or 1.0
    return {k: round(v / tot, 4) for k, v in full.items()}


def _theme_ic_stats(by_date, cols, dates, halflife_days):
    """Per-theme information-coefficient statistics used to build weighting schemes:
    recency-weighted mean IC (mu), IC volatility (vol), and the IC COVARIANCE across themes
    (Sigma). Sigma is what lets us de-correlate redundant themes — value/quality/low-risk
    overlap heavily, so naive IC-proportional weighting triple-counts the same bet."""
    ref = max(dates)
    rows, wts = [], []
    for d in dates:
        sub = by_date[d]
        rows.append([_spearman(sub["z_" + c].values, sub["fwd_ret"].values) for c in cols])
        wts.append(0.5 ** ((pd.to_datetime(ref) - pd.to_datetime(d)).days / max(1.0, halflife_days)))
    n = len(cols)
    M = np.array(rows, dtype=float)                          # [dates x themes] per-date IC
    if M.size == 0:
        return np.zeros(n), np.ones(n), np.eye(n)
    w = np.array(wts, dtype=float)
    w = w / (w.sum() or 1.0)
    mu = np.zeros(n)
    for j in range(n):
        col = M[:, j]
        ok = ~np.isnan(col)
        mu[j] = float(np.sum(w[ok] * col[ok]) / (w[ok].sum() or 1.0)) if ok.any() else 0.0
    X = np.where(np.isnan(M), mu[None, :], M)                # fill gaps with the theme's own mean
    Xc = X - mu[None, :]
    vol = np.sqrt(np.maximum((w[:, None] * Xc * Xc).sum(axis=0), 1e-12))
    Sigma = (Xc * w[:, None]).T @ Xc                         # recency-weighted IC covariance
    return np.nan_to_num(mu), vol, Sigma


def _weight_schemes(mu, vol, Sigma, cols, eq, base):
    """Eight principled theme-sizing schemes from the IC stats. All are non-negative and sum to
    1, so any winner is directly adoptable as live weights (no coarse grid, nothing forced to 0)."""
    n = len(cols)

    def norm(v):
        v = np.clip(np.array(v, dtype=float), 0.0, None)
        s = float(v.sum())
        return {cols[i]: float(v[i] / s) for i in range(n)} if s > 0 else dict(eq)

    icprop = norm(mu)
    schemes = {
        "ic-proportional": icprop,                           # weight ∝ predictive power
        "ic-shrunk-50": {c: 0.5 * icprop[c] + 0.5 * eq[c] for c in cols},
        "risk-parity": norm(1.0 / vol),                      # equal RISK per theme (inverse-vol)
        "ic-ir": norm(np.where(vol > 0, mu / vol, 0.0)),     # reward RELIABLE themes (IC ÷ IC-vol)
        "positive-equal": (norm((mu > 0).astype(float)) if np.any(mu > 0) else dict(eq)),
        "equal-weight": dict(eq),
        "current-default": dict(base),
    }
    try:                                                     # de-correlated max information ratio:
        D = np.diag(np.diag(Sigma))                          #   w ∝ Σ⁻¹·μ, with Σ shrunk toward its
        Ss = 0.5 * Sigma + 0.5 * D + 1e-6 * np.eye(n)        #   diagonal (Ledoit-Wolf style) so the
        schemes["max-ir-decorr"] = norm(np.linalg.solve(Ss, mu))   # inverse can't blow up on noise
    except np.linalg.LinAlgError:
        schemes["max-ir-decorr"] = dict(icprop)
    return schemes


def _weighted_optimize(panel, cols, base, halflife_days=1260, min_oos_fraction=0.5):
    """Weight themes by their actual predictive power (information coefficient), not a coarse
    grid — so EVERY theme gets weight proportional to how well it forecasts returns, with
    shrinkage toward equal-weight to tame noise. Recent dates count more (half-life). The
    winner is then validated on a held-out recent half and only adopted if it beats the
    current defaults out-of-sample."""
    from ..screener.cross_sectional import zscore
    std = panel.copy()
    for c in cols:
        std["z_" + c] = std.groupby("date")[c].transform(lambda s: zscore(s))
    dates = sorted(std["date"].unique())
    if len(dates) < 6:
        return {"accepted": False, "recommended_weights": base, "verdict": "Too few rebalance dates."}
    mid = dates[len(dates) // 2]
    is_dates = [d for d in dates if d < mid]
    oos_dates = [d for d in dates if d >= mid]
    last_is = max(is_dates)
    wdate = {d: 0.5 ** ((pd.to_datetime(last_is) - pd.to_datetime(d)).days / halflife_days) for d in is_dates}
    by_date = {d: std[std["date"] == d] for d in dates}

    def comp(sub, w):
        Z = np.column_stack([sub["z_" + c].values for c in cols])
        wv = np.array([w[c] for c in cols], dtype=float)
        return composite(Z, wv)                                   # AUDIT B7

    def score(dates_, w, recency):
        num = den = 0.0
        for d in dates_:
            sub = by_date[d]
            ic = _spearman(comp(sub, w), sub["fwd_ret"].values)
            if ic == ic:
                wt = wdate[d] if recency else 1.0
                num += wt * ic
                den += wt
        return num / den if den > 0 else np.nan

    # Eight principled theme-sizing schemes from the IC stats (incl. de-correlated max-IR and
    # risk-parity), not a coarse grid — the SAME menu the walk-forward uses, so the two agree.
    eq = {c: 1.0 / len(cols) for c in cols}
    mu, vol, Sigma = _theme_ic_stats(by_date, cols, is_dates, halflife_days)
    candidates = _weight_schemes(mu, vol, Sigma, cols, eq, base)
    scored = [(n, w, score(is_dates, w, True)) for n, w in candidates.items()]
    scored = [(n, w, ic) for n, w, ic in scored if ic == ic]
    if not scored:
        return {"accepted": False, "recommended_weights": base, "candidates": len(candidates),
                "best_in_sample_weights": base, "in_sample_ic": None, "out_sample_ic": None,
                "verdict": "Could not compute in-sample IC."}
    scored.sort(key=lambda x: x[2], reverse=True)
    best_name, best_w, is_ic = scored[0]
    oos_ic = score(oos_dates, best_w, False)
    _avg = float(np.mean([len(by_date[d]) for d in oos_dates])) if oos_dates else 0.0
    _std_null = (1.0 / ((max(1.0, _avg - 1.0) * max(1, len(oos_dates))) ** 0.5)) if oos_dates else 1.0
    accepted = bool(best_name != "current-default" and is_ic > 0 and oos_ic == oos_ic and oos_ic > 0
                    and oos_ic >= min_oos_fraction * is_ic and oos_ic >= 1.64 * _std_null)
    verdict = (f"Adopted '{best_name}' — held out-of-sample (IS {is_ic:.3f} → OOS {oos_ic:.3f})."
               if accepted else "No candidate beat the defaults out-of-sample — kept current weights.")
    return {"accepted": accepted, "recommended_weights": best_w if accepted else base,
            "best_in_sample_weights": best_w, "candidates": len(candidates),
            "in_sample_ic": float(is_ic), "out_sample_ic": float(oos_ic) if oos_ic == oos_ic else None,
            "verdict": verdict}


def _wf_folds(dates, n_folds=5, min_train=None, embargo=1):
    """Anchored (expanding-window) walk-forward splits with a purge/embargo gap.
    Train is always the past up to a cut; test is the NEXT unseen block; roll forward.
    `embargo` drops the train period adjacent to the test block so a forward-return label
    can't overlap the test window (leakage guard). Returns [(train_dates, test_dates), ...]."""
    n = len(dates)
    if min_train is None:
        min_train = max(6, int(n * 0.35))                 # anchor: first ~35% is always training
    if n - min_train < 2:
        return []
    n_folds = max(1, min(n_folds, n - min_train))
    test_len = max(1, (n - min_train) // n_folds)
    folds, start = [], min_train
    while start < n:
        train = dates[:max(1, start - embargo)]
        test = dates[start:start + test_len]
        if not test or len(train) < 4:
            break
        folds.append((list(train), list(test)))
        start += test_len
    return folds


def _trial_N(domain="equity"):
    """AUDIT M1 — the project's real trial count, from the append-only research log.

    Returns the weight-scheme floor (8) if the log cannot be read, so a missing or unreadable
    log degrades to the OLD behaviour rather than to an unpenalised one.
    """
    try:
        from .research_log import trial_count
        return int(trial_count(domain=domain))
    except Exception:
        return 8


def _trials_haircut(n_trials):
    """Multiple-testing penalty. Trying N configs inflates the best one by luck; the expected
    max of N standard-normal draws is ≈ sqrt(2·ln N). The winner must clear this × its standard
    error to be believed — this is what stops us cherry-picking a lucky fold.

    AUDIT M1 — `n_trials` is now floored at the RESEARCH LOG's count, not just the number of
    candidates in the immediate comparison. Selecting the best of 8 folds after the project has
    already run ~84 equity trials is not an 8-trial search, and charging it as one is the same
    denominator error the Deflated Sharpe had.
    """
    return float(np.sqrt(2.0 * np.log(max(2, int(n_trials), _trial_N()))))


def walk_forward(panel, cols, base, top_n=25, horizon=63, halflife_days=1260, n_folds=5):
    """Honest, overfit-resistant selection of BOTH the theme weights and the trade parameters
    via anchored, purged walk-forward. For every fold we FIT on the past and score on the
    untouched next block; we aggregate the OUT-OF-SAMPLE result across folds (median, plus the
    fraction of folds where it was positive), and only recommend a non-default choice when it
    clears a multiple-testing haircut AND is stable across folds. Benchmarked against the
    equal-weight universe (the fair, cap-neutral bar)."""
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    folds = _wf_folds(dates, n_folds=n_folds)
    if not folds:
        return {"status": "insufficient dates for walk-forward"}

    # ---- theme weighting (IC-based, no coarse grid) ----------------------------------------
    std = panel.copy()
    for c in cols:
        std["z_" + c] = std.groupby("date")[c].transform(lambda s: zscore(s))
    by_date = {d: std[std["date"] == d] for d in dates}

    def comp(sub, w):
        Z = np.column_stack([sub["z_" + c].values for c in cols])
        wv = np.array([w[c] for c in cols], dtype=float)
        return composite(Z, wv)                                   # AUDIT B7

    def ic_score(ds, w, recency):
        num = den = 0.0
        ref = max(ds) if ds else None
        for d in ds:
            sub = by_date[d]
            ic = _spearman(comp(sub, w), sub["fwd_ret"].values)
            if ic == ic:
                wt = (0.5 ** ((pd.to_datetime(ref) - pd.to_datetime(d)).days / halflife_days)) if recency else 1.0
                num += wt * ic
                den += wt
        return num / den if den > 0 else np.nan

    eq = {c: 1.0 / len(cols) for c in cols}
    names = ["ic-proportional", "ic-shrunk-50", "risk-parity", "ic-ir", "max-ir-decorr",
             "positive-equal", "equal-weight", "current-default"]
    oos = {nm: [] for nm in names}
    picks, adaptive = [], []
    for train, test in folds:
        mu, vol, Sigma = _theme_ic_stats(by_date, cols, train, halflife_days)     # fit on TRAIN only
        cands = _weight_schemes(mu, vol, Sigma, cols, eq, base)
        tr = {nm: ic_score(train, cands[nm], True) for nm in names}
        valid = [nm for nm in names if tr[nm] == tr[nm]]
        pick = max(valid, key=lambda nm: tr[nm]) if valid else "current-default"
        te = {nm: ic_score(test, cands[nm], False) for nm in names}
        for nm in names:
            if te[nm] == te[nm]:
                oos[nm].append(te[nm])
        picks.append(pick)
        if te.get(pick) == te.get(pick):
            adaptive.append(te[pick])

    def _med(x):
        return float(np.median(x)) if x else None

    def _posfrac(x):
        return float(np.mean([1.0 if v > 0 else 0.0 for v in x])) if x else None

    wsumm = {nm: {"median_oos_ic": _med(oos[nm]), "folds_positive": _posfrac(oos[nm]),
                  "selected": picks.count(nm), "n": len(oos[nm])} for nm in names}
    challengers = [nm for nm in names if nm != "current-default" and wsumm[nm]["median_oos_ic"] is not None]
    wbest = max(challengers, key=lambda nm: wsumm[nm]["median_oos_ic"], default=None)
    wdflt = wsumm["current-default"]["median_oos_ic"]
    wadopt, wverdict = False, "kept the current default weights"
    if wbest is not None and wdflt is not None:
        arr = oos[wbest]
        se = (float(np.std(arr)) / (len(arr) ** 0.5)) if len(arr) > 1 else None
        edge = wsumm[wbest]["median_oos_ic"] - wdflt
        stable = (wsumm[wbest]["folds_positive"] or 0.0) >= 0.6
        if se and se > 0 and edge > _trials_haircut(len(names)) * se and stable and wsumm[wbest]["median_oos_ic"] > 0:
            wadopt = True
            wverdict = (f"adopt '{wbest}': median OOS IC {wsumm[wbest]['median_oos_ic']:+.3f} vs default "
                        f"{wdflt:+.3f}, positive in {wsumm[wbest]['folds_positive']:.0%} of folds, clears the "
                        f"{len(names)}-way trials haircut")
        else:
            wverdict = (f"keep defaults: best challenger '{wbest}' (median OOS IC "
                        f"{wsumm[wbest]['median_oos_ic']:+.3f} vs default {wdflt:+.3f}) did not clear the "
                        f"trials-adjusted, cross-fold-stable bar")

    # ---- trade parameters (hold-until-exit), benchmarked vs equal-weight --------------------
    def alpha_on(ds, **kw):
        sub = panel[panel["date"].isin(ds)]
        r = _backtest_hold(sub, cols, base, horizon=horizon, **kw)
        if not r:
            return None
        fair = r.get("ew_cagr")
        if fair is None:
            fair = r.get("bench_cagr")
        return (r.get("cagr") or 0.0) - (fair or 0.0)

    grids = {
        "exit_band_xN": ([1.5, 2.0, 2.5, 3.0, 4.0], 2.0, lambda m: {"top_n": top_n, "exit_rank": int(top_n * m)}),
        "min_hold_periods": ([1, 2, 3], 2, lambda mh: {"top_n": top_n, "min_hold": mh}),
        "top_n": ([10, 15, 20, 25, 30], top_n, lambda n: {"top_n": n}),
        "trailing_stop_pct": ([None, 0.3], None, lambda s: {"top_n": top_n, "trailing_stop": s}),
    }
    pfolds = folds if len(folds) <= 4 else _wf_folds(dates, n_folds=4)   # cap param folds for runtime
    params = {}
    for pname, (values, default_v, kwfn) in grids.items():
        per_val = {repr(v): [] for v in values}
        p_picks, p_adaptive = [], []
        for train, test in pfolds:
            tr = {v: alpha_on(train, **kwfn(v)) for v in values}
            valid = [v for v in values if tr[v] is not None]
            pick = max(valid, key=lambda v: tr[v]) if valid else default_v
            te = {v: alpha_on(test, **kwfn(v)) for v in values}
            for v in values:
                if te[v] is not None:
                    per_val[repr(v)].append(te[v])
            p_picks.append(pick)
            if te.get(pick) is not None:
                p_adaptive.append(te[pick])
        rows = [{"value": v, "median_oos_alpha": _med(per_val[repr(v)]),
                 "folds_positive": _posfrac(per_val[repr(v)]), "selected": p_picks.count(v),
                 "n": len(per_val[repr(v)])} for v in values]
        cand = [r for r in rows if r["median_oos_alpha"] is not None and r["value"] != default_v]
        drow = next((r for r in rows if r["value"] == default_v), None)
        best = max(cand, key=lambda r: r["median_oos_alpha"], default=None)
        adopt, verdict = False, f"keep default {default_v}"
        if best and drow and drow["median_oos_alpha"] is not None:
            arr = per_val[repr(best["value"])]
            se = (float(np.std(arr)) / (len(arr) ** 0.5)) if len(arr) > 1 else None
            edge = best["median_oos_alpha"] - drow["median_oos_alpha"]
            stable = (best["folds_positive"] or 0.0) >= 0.6
            if se and se > 0 and edge > _trials_haircut(len(values)) * se and stable and best["median_oos_alpha"] > 0:
                adopt = True
                verdict = (f"adopt {pname}={best['value']} (median OOS alpha {best['median_oos_alpha']:+.1%} vs "
                           f"default {drow['median_oos_alpha']:+.1%}, positive in {best['folds_positive']:.0%} of folds)")
            else:
                verdict = (f"keep default {default_v}: best value {best['value']} "
                           f"({best['median_oos_alpha']:+.1%}) did not clear the trials-adjusted, stable bar")
        params[pname] = {"default": default_v, "values": rows, "adaptive_oos_alpha": _med(p_adaptive),
                         "recommend": (best["value"] if adopt else default_v), "adopt": adopt, "verdict": verdict}

    if wadopt:                                              # refit the WINNING scheme on ALL dates →
        mu_a, vol_a, Sig_a = _theme_ic_stats(by_date, cols, dates, halflife_days)   # deployable weights
        rec_cols = _weight_schemes(mu_a, vol_a, Sig_a, cols, eq, base)[wbest]
    else:
        rec_cols = dict(base)
    return {"n_folds": len(folds), "param_folds": len(pfolds),
            "weights": {"candidates": wsumm, "adaptive_oos_ic": _med(adaptive),
                        "recommend": (wbest if wadopt else "current-default"),
                        "adopt": wadopt, "verdict": wverdict, "recommended_weights_cols": rec_cols},
            "params": params}


def quantile_backtest(panel, cols, weights, n_q=10, horizon=63, return_series=False,
                      ret_col="fwd_ret", standardizer=None):
    """The 'is the edge real and harvestable?' test. Each date, sort EVERY name by composite and
    split into n_q equal buckets; measure each bucket's forward return. A genuine signal shows
    (a) higher-composite buckets earning more (monotonic), and (b) a positive, statistically
    significant LONG-SHORT spread (top bucket − bottom bucket) — a market-neutral edge that
    doesn't depend on beating a bull market. Also reports a signal-weighted top-decile long book
    vs the equal-weight universe: the practical way to monetize a positive IC without a short.

    SIGN OF `monotonicity` — read this before interpreting it. Buckets are ordered by
    argsort(-comp), so bucket 0 is the HIGHEST composite, and `monotonicity` is the Spearman
    correlation between bucket INDEX and bucket return. A working signal therefore makes it
    NEGATIVE:

        -1.0 = returns fall perfectly from D1 to D10  → perfectly ordered, the best case
         0.0 = no ordering at all
        +1.0 = returns RISE from D1 to D10            → the composite is exactly backwards

    This project's notes repeatedly read it the other way round ("monotonicity is negative at
    every lag - the deciles aren't cleanly ordered", and a -0.782 -> -0.855 move logged as
    "slightly worse"). Both are inverted: those were well-ordered results getting better.
    Guarded by test_monotonicity_sign_convention.

    S22 — `ret_col` selects which forward-return column is scored. It defaults to the shipped
    `fwd_ret`, so every existing caller is unchanged; the term-structure study points it at the
    `fwd_ret_h{H}` columns `build_fundamental_panel(extra_horizons=...)` adds. Rows whose chosen
    column is NaN are skipped by the same finite-mask the composite already uses, which is how a
    long horizon silently loses its right-censored dates rather than scoring them short. Pass
    `horizon=H` alongside it, or the annualization will be wrong."""
    from ..screener.cross_sectional import zscore
    # S20/S21 — the PER-THEME standardizer (layer 3, the actual "z-sum"). Defaults to the
    # shipped winsorized z-score, so every existing caller is unchanged; the study passes the
    # arm's own standardizer so an arm is swapped at BOTH layers rather than half of one.
    _std = zscore if standardizer is None else standardizer
    if ret_col not in panel.columns:
        raise KeyError(f"quantile_backtest: no forward-return column {ret_col!r} in the panel "
                       f"(build it with build_fundamental_panel(extra_horizons=[...]))")
    dates = sorted(panel["date"].unique())
    q_rets = [[] for _ in range(n_q)]
    ls, sw_long, ewb = [], [], []
    alpha_series = []          # AUDIT R9 — per-period top-decile MINUS equal-weight
    used_dates, n_scored = [], []       # V2G — see `return_series`
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, _std)   # AUDIT B7; S20/S21 standardizer
        fwd = pd.to_numeric(sub[ret_col], errors="coerce").to_numpy(dtype=float)   # S22
        ok = np.isfinite(comp) & np.isfinite(fwd)
        comp, fwd = comp[ok], fwd[ok]
        if len(fwd) < n_q * 3:                              # need enough names for clean buckets
            continue
        used_dates.append(str(d)[:10])
        n_scored.append(int(len(fwd)))
        order = np.argsort(-comp)                           # highest composite first
        buckets = np.array_split(order, n_q)
        for qi, b in enumerate(buckets):
            if len(b):
                q_rets[qi].append(float(np.mean(fwd[b])))
        ls.append(float(np.mean(fwd[buckets[0]]) - np.mean(fwd[buckets[-1]])))
        ewb.append(float(np.mean(fwd)))
        # R9 — the headline's OWN series. `top_decile_alpha` is exactly ppy * mean of this,
        # and until now it shipped with no significance statistic of any kind.
        alpha_series.append(float(np.mean(fwd[buckets[0]]) - np.mean(fwd)))
        top = buckets[0]
        wp = np.clip(comp[top], 0.0, None)                  # signal-weighted (∝ positive composite)
        sw_long.append(float(np.sum(wp * fwd[top]) / wp.sum()) if wp.sum() > 0 else float(np.mean(fwd[top])))
    if len(ls) < 4:
        return {"status": "insufficient history for quantile construction"}
    ppy = 252.0 / horizon                                   # periods per year → annualize

    def annmean(s):
        return float(np.mean(s) * ppy) if s else None

    def tstat(s):
        s = np.asarray(s, dtype=float)
        sd = float(np.std(s, ddof=1)) if len(s) > 1 else 0.0
        return float(np.mean(s) / (sd / np.sqrt(len(s)))) if sd > 0 else None

    decile = [annmean(q) for q in q_rets]
    ew_ann = annmean(ewb)
    sw_ann = annmean(sw_long)
    mono = _spearman(np.arange(n_q, dtype=float), np.array([np.mean(q) if q else np.nan for q in q_rets]))
    # V2G — the per-period draws, opt-in so no existing caller's payload changes.
    # `top_decile_alpha` is exactly `ppy * mean(alpha)`, but a PAIRED comparison of two arms
    # needs the series itself: two arms scored on the same dates share the market move that
    # dominates each level, and differencing them cancels it. Summaries cannot be paired after
    # the fact, which is RUN_RULES A9 — store the draws, not just the summary.
    # `dates`/`n_scored` are returned because two arms need NOT score the same dates or the same
    # names: an arm can rank a name the other cannot (the other's themes are all absent on it),
    # so alignment has to be checkable rather than assumed.
    # U3 — `equal_weight` joins the opt-in dict for the same reason `alpha` did. The top-decile
    # book's own per-period RETURN is `alpha[i] + equal_weight[i]` by construction (see the two
    # appends above), and a combined equity/options curve needs the LEVEL, not the excess: you
    # cannot compound an alpha. Purely additive and inside the existing `return_series` gate, so
    # every current caller's payload stays bit-identical. The identity is pinned by test.
    series = {"dates": used_dates, "n_scored": n_scored,
              "long_short": [float(x) for x in ls],
              "alpha": [float(x) for x in alpha_series],
              "equal_weight": [float(x) for x in ewb]}
    # S28 — the SHAPE of the two series the headlines are means of. Computed ALWAYS (it is a
    # handful of order statistics, not the series) and deliberately NOT gated on
    # `return_series`, because the point of the item is that the distribution should be as
    # available as the mean. Reporting only: no threshold reads it and no verdict depends on it.
    from .statistics import distribution as _dist
    _alpha_dist = _dist(alpha_series, used_dates)
    _ls_dist = _dist(ls, used_dates)
    return {"n_periods": len(ls), "n_quantiles": n_q, "horizon": horizon,
            **({"series": series} if return_series else {}),
            "top_decile_alpha_distribution": _alpha_dist,
            "long_short_distribution": _ls_dist,
            "decile_ann_return": decile, "equal_weight_ann": ew_ann,
            "long_short_ann": annmean(ls), "long_short_tstat": tstat(ls),
            # AUDIT R9 — HAC inference and a visible serial-correlation diagnostic. The naive
            # t above assumes i.i.d. periods; these say whether that assumption holds. If
            # `long_short_ljung_box.p_value` < 0.05 the series is autocorrelated and
            # `long_short_tstat_nw` is the number to quote.
            "long_short_tstat_nw": _nw_tstat(ls, lag=1),
            "long_short_ljung_box": _ljung_box(ls, lags=4),
            # AUDIT M2 — clustered-by-default inference, ADDITIVE. `t` is the HAC statistic
            # (== long_short_tstat_nw); `t_naive` is the i.i.d. one (== long_short_tstat),
            # labelled a diagnostic. Carries n_eff beside n, which nothing here did before.
            "long_short_inference": _inference(ls),
            "long_short_hit": float(np.mean([1.0 if x > 0 else 0.0 for x in ls])),
            "top_decile_alpha": (None if decile[0] is None or ew_ann is None else decile[0] - ew_ann),
            # AUDIT R9 — the number on the front of the product finally has a significance
            # statistic. `top_decile_alpha` == ppy * mean(alpha_series) by construction.
            "top_decile_alpha_tstat": _tstat(alpha_series),
            "top_decile_alpha_tstat_nw": _nw_tstat(alpha_series, lag=1),
            "top_decile_alpha_ljung_box": _ljung_box(alpha_series, lags=4),
            "top_decile_alpha_inference": _inference(alpha_series),      # AUDIT M2
            "top_decile_alpha_hit": (float(np.mean([1.0 if x > 0 else 0.0 for x in alpha_series]))
                                     if alpha_series else None),
            "sw_top_decile_ann": sw_ann,
            "sw_top_decile_alpha": (None if sw_ann is None or ew_ann is None else sw_ann - ew_ann),
            "monotonicity": (None if mono != mono else float(mono))}


def benchmark_panel(panel, cols, weights, n_q=10, horizon=63, ew_turnover=1.0):
    """AUDIT R10 — the top decile against benchmarks a person could actually hold.

    Every alpha figure in this project is measured against the equal-weighted mean forward
    return of EVERY name in the panel that date — roughly 1,500 names including sub-dollar
    stocks, re-equal-weighted quarterly, and **charged zero trading cost while the strategy
    pays**. Nobody can hold that. It is a fine statistical control and a poor benchmark, and
    the project has only ever published the one number.

    Three benchmarks, side by side, published together whatever they say:

      a. `equal_weight` — the incumbent, unchanged, so nothing silently moves.
      b. `equal_weight_costed` — the SAME benchmark charged the same market-cap cost table
         the strategy is charged. Re-equal-weighting a ~1,500-name universe every quarter is
         not free; assuming it is, is a real thumb on the scale in the strategy's FAVOUR being
         removed here. Alpha against this should be HIGHER.
      c. `cap_weighted` — the panel's own cap-weighted average return, the closest investable
         analogue to "just buy the market" that can be built from the panel itself.
      d. `spy` — the benchmark's own realised 63d return from `bench_ret`, i.e. what a user
         would have got in the obvious index fund. Alpha against this should be LOWER.

    `ew_turnover` is the assumed one-way turnover per rebalance of the equal-weight book, used
    only for (b). 1.0 is deliberately conservative-in-the-strategy's-favour-removing direction:
    a quarterly re-equal-weight of a changing universe turns over a large fraction of itself.
    """
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    top, ew, capw, spy, ew_cost = [], [], [], [], []
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        fwd = sub["fwd_ret"].values
        mc = (sub["market_cap"].values if "market_cap" in sub.columns
              else np.full(len(sub), np.nan))
        ok = np.isfinite(comp) & np.isfinite(fwd)
        if int(ok.sum()) < n_q * 3:
            continue
        c_, f_, m_ = comp[ok], fwd[ok], mc[ok]
        order = np.argsort(-c_)
        b0 = np.array_split(order, n_q)[0]
        top.append(float(np.mean(f_[b0])))
        ew.append(float(np.mean(f_)))
        # (b) the equal-weight book charged the strategy's own cost table, name by name
        bps = np.array([one_way_cost_bps(x) for x in m_], dtype=float)
        ew_cost.append(float(np.mean(f_) - float(np.mean(bps)) * 1e-4 * 2.0 * ew_turnover))
        # (c) cap-weighted — the investable analogue
        w = np.where(np.isfinite(m_) & (m_ > 0), m_, 0.0)
        capw.append(float(np.sum(w * f_) / w.sum()) if w.sum() > 0 else float(np.mean(f_)))
        # (d) SPY over the identical window
        b = sub["bench_ret"].iloc[0] if "bench_ret" in sub.columns else np.nan
        spy.append(float(b) if b == b else np.nan)
    if len(top) < 4:
        return {"status": "insufficient history for benchmark comparison"}
    ppy = 252.0 / horizon

    def blk(bench, label, note):
        pairs = [(t, b) for t, b in zip(top, bench) if b == b]
        if len(pairs) < 4:
            return {"status": "no overlapping periods", "label": label}
        exc = [t - b for t, b in pairs]
        return {"label": label, "note": note, "n_periods": len(pairs),
                "benchmark_ann": float(np.mean([b for _, b in pairs]) * ppy),
                "top_decile_ann": float(np.mean([t for t, _ in pairs]) * ppy),
                "excess_ann": float(np.mean(exc) * ppy),
                "excess_tstat": _tstat(exc), "excess_tstat_nw": _nw_tstat(exc, lag=1),
                "excess_inference": _inference(exc),                     # AUDIT M2
                "hit_rate": float(np.mean([1.0 if x > 0 else 0.0 for x in exc]))}

    return {
        "n_periods": len(top), "horizon": horizon, "ew_turnover_assumed": float(ew_turnover),
        "equal_weight": blk(ew, "equal-weight universe (incumbent)",
                            "every name in the panel, cost-free — uninvestable, the number "
                            "every historical alpha figure in this project used"),
        "equal_weight_costed": blk(ew_cost, "equal-weight universe, charged the strategy's costs",
                                   "same benchmark, same market-cap cost table the strategy "
                                   "pays; removes a thumb on the scale in the strategy's favour"),
        "cap_weighted": blk(capw, "cap-weighted panel average",
                            "closest investable analogue buildable from the panel itself"),
        "spy": blk(spy, "SPY total return over the same windows",
                   "what the user's obvious alternative actually returned"),
    }


def regime_split(panel, cols, weights, n_tiers=3, horizon=63):
    """Where does the edge actually live? Split each date's names into market-cap tiers and measure
    the ranking's IC and top-minus-bottom-decile spread INSIDE each tier. Factor edges are usually
    strongest in smaller, less-efficient names — this tells us which universe to focus the live
    book on (and whether the large-cap tier, where an S&P-like benchmark lives, has any edge left)."""
    from ..screener.cross_sectional import zscore
    if "market_cap" not in panel.columns:
        return {"status": "no market_cap in panel"}
    dates = sorted(panel["date"].unique())
    labels = ["small", "mid", "large"] if n_tiers == 3 else [f"tier{i + 1}" for i in range(n_tiers)]
    ic = {lb: [] for lb in labels}
    spread = {lb: [] for lb in labels}
    for d in dates:
        sub = panel[panel["date"] == d]
        mc = sub["market_cap"].values.astype(float)
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        fwd = sub["fwd_ret"].values
        okmc = np.isfinite(mc)
        if okmc.sum() < n_tiers * 10:
            continue
        order = np.argsort(mc[okmc])                        # ascending market cap → tiers small→large
        idx_all = np.where(okmc)[0][order]
        for ti, chunk in enumerate(np.array_split(idx_all, n_tiers)):
            lb = labels[ti]
            cc, ff = comp[chunk], fwd[chunk]
            m2 = np.isfinite(cc) & np.isfinite(ff)
            if m2.sum() < 10:
                continue
            cc, ff = cc[m2], ff[m2]
            ic[lb].append(_spearman(cc, ff))
            o = np.argsort(-cc)
            k = max(1, len(o) // 10)
            spread[lb].append(float(np.mean(ff[o[:k]]) - np.mean(ff[o[-k:]])))
    ppy = 252.0 / horizon
    out = {}
    for lb in labels:
        icv = [x for x in ic[lb] if x == x]
        sv = spread[lb]
        out[lb] = {"median_ic": (float(np.median(icv)) if icv else None),
                   "long_short_ann": (float(np.mean(sv) * ppy) if sv else None),
                   "n_periods": len(sv)}
    return {"tiers": out, "n_tiers": n_tiers}


def _ncdf(x):
    import math
    return 0.5 * (1.0 + math.erf(x / (2.0 ** 0.5)))


def _nppf(p):
    """Inverse normal CDF (Acklam's approximation) — no scipy needed."""
    import math
    if p <= 0.0:
        return -1e9
    if p >= 1.0:
        return 1e9
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def _deflated_sharpe(strategy_rets, all_trial_sr):
    """Deflated Sharpe Ratio (Bailey & Lopez de Prado): probability the strategy's Sharpe is really >0
    after correcting for (a) how many variants we tried and (b) non-normal returns. >~0.95 = credible.

    AUDIT B9 — READ THIS BEFORE QUOTING THE NUMBER. As invoked in this project the statistic is
    very close to an UNDEFLATED Probabilistic Sharpe Ratio, and the ~100% figure in the record is
    not evidence of a 100% probability of anything.

    Two reasons, both structural:

      1. `all_trial_sr` is the eight weight schemes. Bailey-Lopez de Prado's benchmark `sr0`
         scales with the CROSS-TRIAL VARIANCE of Sharpe ratios, and eight near-identical
         weightings of the same eight themes have out-of-sample median ICs spanning +0.061 to
         +0.062 — so `var_sr` is ~0, `sr0` collapses to ~0, and the expression degenerates to
         phi(sr * sqrt(n-1)). Nothing is being deflated.
      2. N = 8 is not the number of trials the project has run. The research ledger records of
         the order of 100+ pre-registered tests. At N = 100+, sqrt(2 ln N) ~ 3.0 — which is,
         coincidentally, about the Harvey-Liu-Zhu multiple-testing hurdle.

    `sr0`, `var_sr` and `N` now ship alongside the probability (see `_deflated_sharpe_detail`)
    so a reader can see the degeneracy rather than infer it. Feeding a real trial count is item
    M1 (the append-only research log) and is NOT done here.

    The bar that IS meaningful on this evidence is the long-short t-statistic against the
    Harvey-Liu-Zhu hurdle of 3.0. Lead with that one.
    """
    d = _deflated_sharpe_detail(strategy_rets, all_trial_sr)
    return None if d is None else d["probability"]


def _deflated_sharpe_detail(strategy_rets, all_trial_sr):
    """The same computation, with the inputs that determine whether it deflated anything."""
    r = np.asarray(strategy_rets, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 8 or r.std(ddof=1) == 0:
        return None
    sr = float(r.mean() / r.std(ddof=1))                     # per-period Sharpe
    m = r - r.mean()
    # AUDIT B25 — ddof=1, matching the Sharpe above. This used to be ddof=0 while `sr` used
    # ddof=1, so the skew/kurtosis correction was computed on a different scale from the
    # quantity it corrects. It is the entire residual difference between this implementation
    # and `options_autopsy.deflated_sharpe`: with the same trial vector the two now agree to
    # floating-point, having previously differed in the fifth decimal for no stated reason.
    s = r.std(ddof=1)
    skew = float((m ** 3).mean() / s ** 3)
    kurt = float((m ** 4).mean() / s ** 4)                   # non-excess kurtosis
    trials = [x for x in all_trial_sr if x is not None]
    # AUDIT B25 — an EMPTY or single-element trial set does not license a deflation. It used to
    # fall through to N = 2 and var_sr = 1/n, fabricating a benchmark out of a variance the data
    # never supplied — a third convention for this statistic inside one module. With no trial
    # set the honest answer is sr0 = 0, i.e. a plain probabilistic Sharpe ratio, labelled.
    if len(trials) < 2:
        sr0 = 0.0
        denom0 = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2)
        if denom0 <= 0:
            return None
        z0 = (sr - sr0) * ((n - 1) ** 0.5) / (denom0 ** 0.5)
        return {"probability": float(_ncdf(z0)), "sharpe_per_period": sr,
                "sr0_benchmark": 0.0, "n_trials": len(trials),
                "var_sr_across_trials": None, "n_periods": int(n),
                "is_effectively_undeflated": True,
                "metric": "probabilistic_sharpe_ratio_UNDEFLATED"}
    # AUDIT M1 — N IS THE NUMBER OF TRIALS THE PROJECT HAS RUN, not the number of weight
    # schemes this one call was handed. `len(trials)` is 8; the research log counts the real
    # equity family. Bailey-Lopez de Prado's `sr0` grows with N, so a bigger honest N raises
    # the benchmark the Sharpe must beat and the probability falls. That is the intended
    # direction: the statistic has been flattering itself by a denominator of 8.
    #
    # `var_sr` still comes from the observed trial Sharpes — it is the only cross-trial
    # variance actually measured — while N comes from the log. Mixing them is what the
    # formula requires: the variance describes how much trials differ, N describes how many
    # there were, and only the second was ever wrong.
    _n_logged = _trial_N()
    N = max(2, len(trials), _n_logged)
    var_sr = float(np.var(trials, ddof=1))
    emc = 0.5772156649015329                                 # Euler-Mascheroni
    sr0 = (var_sr ** 0.5) * ((1 - emc) * _nppf(1 - 1.0 / N) + emc * _nppf(1 - 1.0 / (N * np.e)))
    denom = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2)
    if denom <= 0:
        return None
    z = (sr - sr0) * ((n - 1) ** 0.5) / (denom ** 0.5)
    return {"probability": float(_ncdf(z)), "sharpe_per_period": sr, "sr0_benchmark": float(sr0),
            "n_trials": int(N), "var_sr_across_trials": var_sr, "n_periods": int(n),
            # AUDIT M1 — where N came from, so a reader can see whether it was 8 or measured.
            "n_trials_from_weight_schemes": int(len(trials)),
            "n_trials_from_research_log": int(_n_logged),
            "n_trials_source": ("RESEARCH_LOG.md (audit M1)" if _n_logged > len(trials)
                                else "weight schemes only"),
            # AUDIT B9: when sr0 is ~0 the statistic is an UNDEFLATED PSR, not a DSR.
            "is_effectively_undeflated": bool(abs(sr0) < 0.05 * abs(sr) if sr else True),
            "metric": ("probabilistic_sharpe_ratio_UNDEFLATED"
                       if (abs(sr0) < 0.05 * abs(sr) if sr else True) else "deflated_sharpe_ratio")}


def _pbo(is_mat, oos_mat, names):
    """Probability of Backtest Overfitting (Bailey/Lopez de Prado): across CPCV paths, how often does
    the scheme that looked best IN-sample land BELOW the median OUT-of-sample? High = we're fooling
    ourselves; low = the selection generalizes."""
    import math
    below = tot = 0
    for isr, osr in zip(is_mat, oos_mat):
        valid = [(i, v) for i, v in enumerate(isr) if v == v]
        oos_vals = [v for v in osr if v == v]
        if not valid or len(oos_vals) < 2:
            continue
        best_i = max(valid, key=lambda x: x[1])[0]
        best_oos = osr[best_i]
        if best_oos != best_oos:
            continue
        rank = sum(1 for v in oos_vals if v <= best_oos) / len(oos_vals)   # (0,1], higher = better
        rank = min(max(rank, 1e-6), 1 - 1e-6)
        tot += 1
        if math.log(rank / (1 - rank)) <= 0:                 # at/below OOS median → an overfit instance
            below += 1
    return (below / tot) if tot > 0 else None


def _cpcv_paths(dates, n_groups=6, k_test=2, embargo=1):
    """Combinatorial Purged CV splits: chop the timeline into n_groups blocks, hold out every
    combination of k_test blocks as the test set (C(n_groups, k_test) paths), and purge/embargo the
    training rows adjacent to any test block. Every period gets tested many times, not once."""
    import itertools
    n = len(dates)
    if n < 12:
        return []
    n_groups = max(3, min(n_groups, n // 3))
    if k_test >= n_groups:
        k_test = max(1, n_groups - 1)
    groups = [list(g) for g in np.array_split(range(n), n_groups)]
    paths = []
    for combo in itertools.combinations(range(n_groups), k_test):
        test_idx = set()
        for gi in combo:
            test_idx.update(groups[gi])
        train = [i for i in range(n) if i not in test_idx and not any(abs(i - j) <= embargo for j in test_idx)]
        tr = [dates[i] for i in train]
        te = [dates[i] for i in sorted(test_idx)]
        if len(tr) >= 8 and len(te) >= 4:
            paths.append((tr, te))
    return paths


def _strategy_returns(panel, cols, weights, top_frac=0.1):
    """Per-period 'alpha' series of a weighting: top-decile mean forward return minus the equal-weight
    universe. Used to compute a Sharpe for the Deflated Sharpe Ratio."""
    from ..screener.cross_sectional import zscore
    out = []
    for d in sorted(panel["date"].unique()):
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        fwd = sub["fwd_ret"].values
        ok = np.isfinite(comp) & np.isfinite(fwd)
        comp, fwd = comp[ok], fwd[ok]
        if len(fwd) < 20:
            continue
        k = max(1, int(len(fwd) * top_frac))
        o = np.argsort(-comp)
        out.append(float(np.mean(fwd[o[:k]]) - np.mean(fwd)))
    return out


def cpcv_validate(panel, cols, base, halflife_days=1260, horizon=63, n_groups=6, k_test=2):
    """The strongest honesty test we have: pick the theme weighting via Combinatorial Purged CV
    (many train/test paths), and report the Probability of Backtest Overfitting + the Deflated Sharpe
    Ratio of the chosen weighting. Adopt only if it beats the default across paths AND clears the bar."""
    from ..screener.cross_sectional import zscore
    std = panel.copy()
    for c in cols:
        std["z_" + c] = std.groupby("date")[c].transform(lambda s: zscore(s))
    dates = sorted(std["date"].unique())
    by_date = {d: std[std["date"] == d] for d in dates}

    def comp(sub, w):
        Z = np.column_stack([sub["z_" + c].values for c in cols])
        wv = np.array([w[c] for c in cols], dtype=float)
        present = ~np.isnan(Z)
        den = (present * wv).sum(axis=1)
        den[den == 0] = np.nan
        return np.nansum(np.where(present, Z, 0.0) * wv, axis=1) / den

    def ic_score(ds, w):
        num = den = 0.0
        for d in ds:
            sub = by_date[d]
            ic = _spearman(comp(sub, w), sub["fwd_ret"].values)
            if ic == ic:
                num += ic
                den += 1
        return num / den if den > 0 else np.nan

    eq = {c: 1.0 / len(cols) for c in cols}
    names = ["ic-proportional", "ic-shrunk-50", "risk-parity", "ic-ir", "max-ir-decorr",
             "positive-equal", "equal-weight", "current-default"]
    paths = _cpcv_paths(dates, n_groups, k_test)
    if not paths:
        return {"status": "insufficient dates for CPCV"}
    is_mat, oos_mat, oos = [], [], {nm: [] for nm in names}
    for tr, te in paths:
        mu, vol, Sig = _theme_ic_stats(by_date, cols, tr, halflife_days)
        cands = _weight_schemes(mu, vol, Sig, cols, eq, base)
        isr = {nm: ic_score(tr, cands[nm]) for nm in names}
        osr = {nm: ic_score(te, cands[nm]) for nm in names}
        is_mat.append([isr[nm] for nm in names])
        oos_mat.append([osr[nm] for nm in names])
        for nm in names:
            if osr[nm] == osr[nm]:
                oos[nm].append(osr[nm])
    med = {nm: (float(np.median(oos[nm])) if oos[nm] else None) for nm in names}
    posf = {nm: (float(np.mean([1.0 if v > 0 else 0.0 for v in oos[nm]])) if oos[nm] else None) for nm in names}
    pbo = _pbo(is_mat, oos_mat, names)
    chall = [nm for nm in names if nm != "current-default" and med[nm] is not None]
    best = max(chall, key=lambda nm: med[nm], default=None)
    dflt = med["current-default"]
    adopt, verdict = False, "kept the current default weights"
    _adopt_detail = None
    if best is not None and dflt is not None:
        arr = oos[best]
        se = (float(np.std(arr)) / len(arr) ** 0.5) if len(arr) > 1 else None
        # SESSION 12 — BANK THE MARGIN, NOT JUST THE DECISION. The adopt gate multiplies `se` by
        # `_trials_haircut`, which is FLOORED AT THE RESEARCH LOG'S `N` (audit M1). So the same
        # draw can adopt at one project-wide trial count and not at another, and the adopted
        # weights then feed `quantile_backtest` — meaning `N` silently moves the long-short t of
        # any run that sits near this bar. X7's placebo recorded only the boolean, which is why
        # its 8%-vs-7% `ls_t >= 2.0` discrepancy cost two sessions and a 100-draw re-run to chase.
        # With (margin, se) banked, the decision at any other `N` is arithmetic.
        _adopt_detail = {
            "best": best, "median_oos_ic_best": med[best], "median_oos_ic_default": dflt,
            "margin": (None if (med[best] is None or dflt is None) else float(med[best] - dflt)),
            "se": se, "folds_positive": posf[best],
            "haircut": float(_trials_haircut(len(names))),
            "n_trials_used": int(max(2, len(names), _trial_N())),
            "bar": (None if not se else float(_trials_haircut(len(names)) * se)),
        }
        if se and se > 0 and (med[best] - dflt) > _trials_haircut(len(names)) * se and (posf[best] or 0) >= 0.6 and med[best] > 0:
            adopt = True
            verdict = (f"adopt '{best}': median OOS IC {med[best]:+.3f} vs default {dflt:+.3f} across "
                       f"{len(paths)} CPCV paths, positive in {posf[best]:.0%}")
        else:
            verdict = (f"keep defaults: best '{best}' ({med[best]:+.3f} vs {dflt:+.3f}) did not clear the "
                       f"CPCV trials-adjusted bar")
    mu, vol, Sig = _theme_ic_stats(by_date, cols, dates, halflife_days)     # refit on ALL data
    all_w = _weight_schemes(mu, vol, Sig, cols, eq, base)
    recname = best if adopt else "current-default"
    trial_sr = []
    for nm in names:
        s = _strategy_returns(panel, cols, all_w[nm])
        rr = np.asarray(s, dtype=float)
        trial_sr.append(float(rr.mean() / rr.std(ddof=1)) if len(rr) > 2 and rr.std(ddof=1) > 0 else None)
    _dsr_detail = _deflated_sharpe_detail(_strategy_returns(panel, cols, all_w[recname]), trial_sr)
    dsr = None if _dsr_detail is None else _dsr_detail["probability"]
    return {"n_paths": len(paths), "pbo": pbo, "deflated_sharpe": dsr,
            # AUDIT B9 — what the two headline statistics actually measure. `pbo` scores the
            # WEIGHT-SCHEME SELECTION STEP only: "the best of eight nearly-identical weightings
            # generalises". It says nothing about the signal-inclusion, theme-membership,
            # universe, standardisation and construction decisions in the project ledger — and
            # the shipped strategy keeps `current-default` anyway, so the selection being scored
            # is one the model never makes.
            "pbo_scope": "weight_scheme_selection_only",
            "deflated_sharpe_detail": _dsr_detail,
            "recommend": recname, "adopt": adopt,
            "adopt_detail": _adopt_detail,
            # SESSION 12 — the challenger's weights, exposed WHETHER OR NOT it was adopted. The
            # shipped path must keep returning `base` on a reject (that is the rule X7 measured),
            # so this is a separate key: it is what makes "what would this run have scored had the
            # bar been one haircut lower" answerable without re-running the sweep.
            "challenger_weights_cols": (dict(all_w[best]) if best in all_w else None),
            "verdict": verdict, "recommended_weights_cols": (all_w[recname] if adopt else dict(base)),
            "candidates": {nm: {"median_oos_ic": med[nm], "folds_positive": posf[nm]} for nm in names}}


def institutional_dependence(panel, cols, weights, horizon=63):
    """How much of the edge leans on the institutional (13F) theme? Rebuild the construction test with
    institutional REMOVED (weights renormalized) and compare. If the edge collapses without it, the
    whole thing rests on lagged quarterly 13F data — fragile."""
    if "institutional" not in cols:
        return {"status": "institutional not in factor set"}
    full = quantile_backtest(panel, cols, weights, horizon=horizon) or {}
    cols_wo = [c for c in cols if c != "institutional"]
    w2 = {c: weights.get(c, 0.0) for c in cols_wo}
    tot = sum(w2.values()) or 1.0
    w2 = {c: v / tot for c, v in w2.items()}
    wo = quantile_backtest(panel, cols_wo, w2, horizon=horizon) or {}

    def g(r, k):
        return r.get(k)
    return {"institutional_weight": round(float(weights.get("institutional", 0.0)), 3),
            "with": {"top_decile_alpha": g(full, "top_decile_alpha"), "long_short_tstat": g(full, "long_short_tstat"),
                     "monotonicity": g(full, "monotonicity")},
            "without": {"top_decile_alpha": g(wo, "top_decile_alpha"), "long_short_tstat": g(wo, "long_short_tstat"),
                        "monotonicity": g(wo, "monotonicity")}}


#: Filing-lag assumptions for the 13F due-diligence run.
#:
#: These MUST be chosen to cross a 13F quarter boundary, or the test measures nothing.
#: Both grids are quarterly: 13F rows are stamped with the quarter-END (`calendardate`),
#: and the rebalance dates (every 63 trading days) land 11-21 days PAST a quarter start.
#: So for an as-of of 2025-04-21 the previous quarter-end is 2025-03-31, and lags of
#: 45 / 60 / 90 days all resolve back to the SAME 2024-12-31 filing — identical panels,
#: identical stats, zero information. The old (45, 60, 90) default was structurally
#: incapable of showing a difference; it needs >111 days to select a different quarter.
#:
#:   15d  -> the most recent quarter-end, which is NOT yet filed  (deliberate look-ahead)
#:   45d  -> the last filed quarter, Q-1                          (what the backtest uses)
#:  135d  -> one quarter staler, Q-2
#:  225d  -> two quarters staler, Q-3
INST_LAG_GRID = (15, 45, 135, 225)


def validate_institutional(provider, tickers, lags=INST_LAG_GRID, lookback_years=18, horizon=63):
    """Standalone due-diligence on the institutional (13F) signal — the one theme carrying the edge.
    Rebuild the panel under several 13F filing-lag assumptions and measure the signal ALONE (100%
    weight): its IC, top-decile alpha, long-short spread + t-stat, monotonicity.

    Read it as an information-decay curve (see INST_LAG_GRID for why these lags):
      * STRONGER at 15d than at 45d => the edge leans on filings that weren't public yet,
        i.e. a look-ahead artifact rather than a tradeable signal.
      * peaks at 45d and decays through 135d -> 225d => a genuine, slowly-decaying signal.
      * flat across all four => no information at any horizon; it's noise.
    A Deflated Sharpe > ~95% at a realistic (>=45d) lag is the bar for "real"."""
    from ..screener.cross_sectional import zscore
    out = {"lags": {}}
    for lag in lags:
        panel = build_fundamental_panel(provider, tickers, rebalance_days=63,
                                        lookback_years=lookback_years, horizon=horizon, inst_lag_days=lag)
        if panel.empty or "institutional" not in panel.columns or not panel["institutional"].notna().any():
            out["lags"][str(lag)] = {"status": "no institutional data"}
            continue
        cols, w = ["institutional"], {"institutional": 1.0}
        q = quantile_backtest(panel, cols, w, horizon=horizon) or {}
        ics = []
        for d in sorted(panel["date"].unique()):
            sub = panel[panel["date"] == d]
            ics.append(_spearman(zscore(sub["institutional"]).values, sub["fwd_ret"].values))
        ics = [x for x in ics if x == x]
        strat = _strategy_returns(panel, cols, w)
        rr = np.asarray(strat, dtype=float)
        # AUDIT B25 — this used to call `_deflated_sharpe(strat, [single_sharpe])`, i.e. a ONE-
        # element trial vector. That path takes `N = max(2, 1) = 2` and `var_sr = 1/n`, which is
        # a THIRD convention for the same statistic inside the same module, and one that
        # deflates against a benchmark built from a variance the data never supplied. There is
        # no meaningful cross-trial Sharpe vector here — the lags are not competing strategies —
        # so the honest report is the UNDEFLATED probabilistic Sharpe, labelled as such, rather
        # than a deflation against a fabricated trial set.
        _psr_d = _deflated_sharpe_detail(strat, [])
        psr = None if _psr_d is None else _psr_d["probability"]
        out["lags"][str(lag)] = {
            "psr_metric": "probabilistic_sharpe_ratio_UNDEFLATED (no trial set; audit B25)",
            "dates": int(panel["date"].nunique()), "names": int(panel["ticker"].nunique()),
            "median_ic": (float(np.median(ics)) if ics else None),
            "top_decile_alpha": q.get("top_decile_alpha"), "long_short_ann": q.get("long_short_ann"),
            "long_short_tstat": q.get("long_short_tstat"), "monotonicity": q.get("monotonicity"),
            "deflated_sharpe": psr}
    return out


def multiple_testing_accounting(per_signal: dict, headline_ls_hac) -> dict:
    """AUDIT R4 — the two method bullets M1 did not deliver.

    M1 built the append-only log and fed the real `N` into the Deflated Sharpe. It did NOT do
    either of R4's other two:

      3. "Apply Benjamini–Hochberg across the family of *equity* signal tests, as the options
         autopsy already does for its 126 features."  BH existed only in the options lane.
         The equity analogue of "126 features" is the PER-SIGNAL IC TABLE — not the research
         log, which records verdicts and has NO p-value column, so BH across it is not
         computable and never was. That is R4's permanent residual.

      4. "Report the Harvey–Liu–Zhu adjusted hurdle for the number of trials actually run."
         `_trials_haircut` computed it and the CPCV adopt gate USED it, but nothing ever
         compared it to the HEADLINE, and no `harvey`/`hlz`/`hurdle` string existed anywhere
         in the canonical file. This block is that comparison, shipped so it cannot go unread
         a second time.

    THE ANSWER IS A TENSION AND BOTH SIDES SHIP. The headline HAC *t* clears X7's empirically
    CALIBRATED floor (2.2837) and FAILS the theoretical HLZ hurdle √(2·ln N) at the honest
    denominator. The counter-argument travels in the payload rather than being left to a
    reader: HLZ prices the BEST OF N draws, and the deployed composite is not the best of
    anything — flat 1/7, never tuned, `cpcv.adopt` false on every run — so the logged trials
    are overwhelmingly REJECTED ALTERNATIVES to it rather than candidates it beat.

    R4's own prediction was that the long-short *t* "probably clears a properly-computed
    hurdle". It does not, and both movements ran against it: that 3.52 was the pre-B6 void
    panel, while `N` went 8 → 200+, so the statistic fell as the hurdle rose.
    """
    from . import research_log as _rl
    sig = (per_signal or {})
    names = sorted(sig)
    rows = []
    for n in names:
        r = sig[n] or {}
        t_plain = r.get("ic_tstat")
        t_hac = (r.get("ic_inference") or {}).get("t")
        rows.append({"signal": n, "median_ic": r.get("median_ic"),
                     "coverage": r.get("coverage"), "n_dates": r.get("n_dates"),
                     "ic_tstat": t_plain, "ic_t_hac": t_hac,
                     "p_plain": _stats.two_sided_p(t_plain),
                     "p_hac": _stats.two_sided_p(t_hac)})
    for key, pk in (("bh_reject_plain", "p_plain"), ("bh_reject_hac", "p_hac")):
        for x, v in zip(rows, _stats.benjamini_hochberg([x[pk] for x in rows], 0.05)):
            x[key] = bool(v)

    det = {}
    try:
        det = _rl.detail() or {}
    except Exception:
        det = {}
    by = det.get("by_domain") or {}
    n_eq = int(by.get("equity") or 0)
    hurdle = float(np.sqrt(2.0 * np.log(max(2, n_eq)))) if n_eq else None
    t = (float(headline_ls_hac)
         if headline_ls_hac is not None and headline_ls_hac == headline_ls_hac else None)

    return {
        "bh": {
            "family": ("per-signal IC table — the equity analogue of the options autopsy's "
                       "126 features"),
            "q": 0.05, "n_signals": len(rows),
            "n_discoveries_plain": sum(x["bh_reject_plain"] for x in rows),
            "n_discoveries_hac": sum(x["bh_reject_hac"] for x in rows),
            "discoveries_plain": sorted(x["signal"] for x in rows if x["bh_reject_plain"]),
            "discoveries_hac": sorted(x["signal"] for x in rows if x["bh_reject_hac"]),
            "signals": rows,
            "not_computable_across_the_log": (
                "RESEARCH_LOG.md records verdicts and has no p-value column; reconstructing "
                "one for heterogeneous rows measured against different statistics on "
                "different universes would be invention. R4's permanent residual."),
        },
        "hlz": {
            "statistic": "construction.long_short_tstat_nw",
            "value": t,
            "n_trials_equity": n_eq,
            "hurdle_sqrt_2_ln_N": hurdle,
            "clears_hlz_hurdle": (None if (t is None or hurdle is None) else bool(t > hurdle)),
            "shortfall": (None if (t is None or hurdle is None) else float(hurdle - t)),
            "x7_calibrated_floor": 2.2837,
            "clears_x7_calibrated_floor": (None if t is None else bool(t > 2.2837)),
            "the_tension": (
                "CLEARS the bar measured against the project's own placebo and FAILS the bar "
                "derived from counting its own trials. Neither is 'the' answer. HLZ prices "
                "the best of N draws; the deployed composite is flat 1/7, never tuned, and "
                "cpcv.adopt is false on every run, so the logged trials are overwhelmingly "
                "REJECTED ALTERNATIVES to it rather than candidates it beat."),
        },
        "by_domain": by,
        "unified_domain_declared_but_zero": bool("unified" in (_rl.DOMAINS or ())
                                                 and (by.get("unified") or 0) == 0),
        "unified_note": (
            "research_log.DOMAINS declares `unified` and it reads zero: every U-series item "
            "testing unified equity+options hypotheses was charged to equity or options. "
            "Three parallel single-lane families and one dead bucket. Measured and ROUTED — "
            "deciding whether cross-lane claims need their own denominator would move every "
            "published N and is not made here."),
        "trials_logged_all_domains": det.get("trials_logged"),
        "audit_estimate": det.get("audit_estimate"),
        "gap_to_audit_estimate": det.get("gap_to_audit_estimate"),
    }


def per_signal_ic(panel, horizon_col="fwd_ret", min_names=20, min_dates=8) -> dict:
    """{signal: {median_ic, ic_tstat, coverage, n_dates}} for EVERY wired number.

    Needs a panel built with keep_numbers=True. Per-date Spearman IC of each standardized
    number against the forward return, then the median across dates and a t-stat on the IC
    series — the same measurement used to accept or reject a signal, so the results file
    reports exactly what the decisions were made on rather than a hand-curated subset.
    """
    out = {}
    if panel is None or panel.empty:
        return out
    for num in S.NUMBERS_ALL:
        zc = "z_" + num
        if zc not in panel.columns:
            continue
        ics = []
        for _d, sub in panel.groupby("date"):
            ss = sub.dropna(subset=[zc, horizon_col])
            if len(ss) >= min_names:
                ic = _spearman(ss[zc].values, ss[horizon_col].values)
                if ic == ic:
                    ics.append(ic)
        cov = float(panel[zc].notna().mean())
        if len(ics) >= min_dates:
            a = np.asarray(ics, dtype=float)
            sd = float(a.std(ddof=1))
            t = float(a.mean() / (sd / (len(a) ** 0.5))) if sd > 0 else 0.0
            out[num] = {"median_ic": float(np.median(a)), "ic_tstat": t,
                        # AUDIT M2 — an IC series indexed by rebalance date is exactly the
                        # object R9 showed is serially correlated for the long-short spread,
                        # and it had NO clustered figure at all. `ic_tstat` above is untouched.
                        "ic_inference": _inference(a),
                        "coverage": cov, "n_dates": len(a)}
        else:
            out[num] = {"median_ic": None, "ic_tstat": None, "coverage": cov,
                        "n_dates": len(ics)}
    return out


def theme_ic(panel, horizon_col="fwd_ret", min_names=20, min_dates=8) -> dict:
    """{theme: {median_ic, ic_tstat, coverage, n_dates}} for each composite THEME column.

    per_signal_ic measures individual numbers; this measures the blend each one feeds, which
    is the level the keep/drop decisions actually operate at. A theme can be worth carrying
    while an input is worthless (or the reverse), and without this the only evidence for
    "theme X is hurting" was a pooled figure from a small universe.

    Works on any panel — theme columns are always persisted, keep_numbers or not.
    """
    out = {}
    if panel is None or panel.empty:
        return out
    n = float(len(panel))
    for theme in S.FACTORS_ALL:
        if theme not in panel.columns:
            continue
        ics = []
        for _d, sub in panel.groupby("date"):
            ss = sub.dropna(subset=[theme, horizon_col])
            if len(ss) >= min_names:
                ic = _spearman(ss[theme].values, ss[horizon_col].values)
                if ic == ic:
                    ics.append(ic)
        cov = float(panel[theme].notna().sum() / n)
        if len(ics) >= min_dates:
            a = np.asarray(ics, dtype=float)
            sd = float(a.std(ddof=1))
            t = float(a.mean() / (sd / (len(a) ** 0.5))) if sd > 0 else 0.0
            out[theme] = {"median_ic": float(np.median(a)), "ic_tstat": t,
                          # AUDIT M2 — `ic_tstat` is the statistic carrying X7's calibrated
                          # 2.71 bar and it had no clustered variant. This is a NEW statistic
                          # with NO calibrated floor: nobody may compare `ic_inference.t`
                          # to 2.71. `ic_tstat` itself is untouched, so the bar still applies
                          # to exactly the number it was calibrated on.
                          "ic_inference": _inference(a),
                          "coverage": cov, "n_dates": len(a)}
        else:
            out[theme] = {"median_ic": None, "ic_tstat": None, "coverage": cov,
                          "n_dates": len(ics)}
    return out


# Minimum improvement for holdout_theme_validate to call a change real. PRE-SPECIFIED and
# committed BEFORE the P6 runs, because a threshold chosen after seeing results is not a
# threshold. Both must be met, in BOTH split directions.
#
#   alpha: 100bps/yr. Rationale is economic, not statistical — realistic one-way trading
#          costs on this universe are of that order (see turnover_and_costs), so an
#          "improvement" smaller than the cost of implementing it cannot be harvested and
#          should not be called an improvement.
#   t:     0.25. A noise floor. Half-sample long-short t-stats here run ~0.5-2.6, and the
#          previous rule admitted a +0.01 move, which is indistinguishable from zero.
#
# Disclosed honestly: I already knew the P5 numbers when picking these, so this is a
# principled tightening, not a blind pre-registration. Its one consequence on existing
# results is that `capital_discipline` drops from "confirmed" (it passed on dLS t +0.01) to
# "not_replicated", which is the outcome the old rule was already flagged as getting wrong.
# The clean use of these constants is the NEXT theme tested, not the ones already measured.
MIN_HOLDOUT_ALPHA_GAIN = 0.01      # +100 bps/yr top-decile alpha
MIN_HOLDOUT_TSTAT_GAIN = 0.25      # +0.25 long-short t


# One-way transaction cost (half-spread + market impact) in basis points, by point-in-time
# market cap. Every headline number in this project is GROSS of costs, and P5 tilted the book
# smaller-cap by zeroing low_risk — which is exactly where costs bite hardest — so the gross
# figures cannot be read as achievable without this.
#
# Deliberately round, conservative-side numbers rather than a fitted microstructure model:
# the honest output of this analysis is the BREAKEVEN cost (see cost_breakeven_bps), which
# needs no calibration to interpret. Treat the table as one plausible point on that curve.
COST_BPS_BY_MKTCAP = (
    (200e9, 4.0),        # mega cap
    (50e9, 6.0),
    (10e9, 10.0),
    (2e9, 20.0),
    (500e6, 40.0),
    (100e6, 80.0),
)
COST_BPS_MICRO = 150.0   # below $100M — often untradeable in size at all


def one_way_cost_bps(mktcap) -> float:
    """Cost in bps of buying OR selling $1 of a name with this market cap."""
    if mktcap is None or mktcap != mktcap or mktcap <= 0:
        return COST_BPS_MICRO
    for floor, bps in COST_BPS_BY_MKTCAP:
        if mktcap >= floor:
            return bps
    return COST_BPS_MICRO


def risk_stats(rets, per_year, rf=0.0):
    """Sharpe and max drawdown from a period-return series.

    Raw return is the wrong yardstick for choosing CONCENTRATION: a tighter book almost always
    shows a higher mean and a much higher variance, so ranking widths on alpha alone reliably
    picks the noisiest one. These are the per-unit-risk numbers that make the choice honest.

    Sharpe is annualized from the period returns (mean/sd * sqrt(periods per year)); max
    drawdown is the worst peak-to-trough on the compounded equity curve, which is what a human
    actually has to sit through.
    """
    a = np.asarray([r for r in rets if r == r], dtype=float)
    if len(a) < 3:
        return {"sharpe": None, "max_drawdown": None, "vol_ann": None, "n": int(len(a)),
                "rf_annual": float(rf), "metric": _risk_metric_name(rf)}
    sd = float(a.std(ddof=1))
    mu = float(a.mean()) - rf / per_year
    sharpe = (mu / sd) * (per_year ** 0.5) if sd > 0 else None
    eq = np.cumprod(1.0 + a)
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1.0).min())
    # AUDIT B19 — every caller passes rf = 0, so the figure labelled "sharpe" throughout the
    # results file is a return-to-VOLATILITY ratio, i.e. an information ratio against zero. Over
    # 1998-2026, with the risk-free rate averaging roughly 2%, that overstates a true Sharpe by
    # about 0.05-0.10. The direction is consistent across every book so relative comparisons are
    # unaffected, but the label is wrong and the figure reaches product-facing material — and
    # the options engine in this same repository subtracts a real rate, so two subsystems used
    # different definitions of the same word. The rate and the metric name now ship with the
    # number, so a reader can never take one for the other.
    return {"sharpe": sharpe, "max_drawdown": dd,
            "vol_ann": sd * (per_year ** 0.5), "n": int(len(a)),
            "rf_annual": float(rf), "metric": _risk_metric_name(rf)}


def _risk_metric_name(rf) -> str:
    return "sharpe_ratio" if rf else "information_ratio_vs_zero_rf"


def _sector_capped(order, tickers, sectors, n_target, max_sector_w):
    """Pick n_target names best-first, but never let one sector exceed `max_sector_w`.

    A CONCENTRATION RISK control, not a ranking change: names keep their exact composite order
    and nothing is re-scored. The only thing that happens is that once a sector has filled its
    allowance, the next name from it is skipped and the slot goes to the best name outside it.
    (P10 rejected sector-NEUTRAL ranking, which is a different intervention entirely — that
    re-scored every name against its sector peers.)

    Unknown sector ("" / None) is exempt: with no sector data the cap would otherwise silently
    bind on one giant bucket and quietly reshape the book.
    """
    cap_n = max(1, int(n_target * max_sector_w))
    picked, per = [], {}
    for i in order:
        t = tickers[i]
        sec = (sectors.get(t) or "").strip()
        if sec:
            if per.get(sec, 0) >= cap_n:
                continue
            per[sec] = per.get(sec, 0) + 1
        picked.append(i)
        if len(picked) >= n_target:
            break
    # If the cap is so tight the book cannot be filled, top up in rank order rather than
    # returning a short book — a smaller book is a different experiment, not a capped one.
    if len(picked) < n_target:
        have = set(picked)
        for i in order:
            if i not in have:
                picked.append(i)
                if len(picked) >= n_target:
                    break
    return picked


# MOVED 2026-08-13 by the S14 ADOPTION. The band rule used to be defined here, and here only,
# because only the backtest applied it. Adopting it into the live book meant a second caller, and
# writing the rule again next to `build_index` would have created two definitions of one
# construction. So the body moved to `no_trade_band.py` and BOTH callers import it.
#
# This is an ALIAS, not a re-implementation: `_band_select is no_trade_band.band_select` is true,
# and a test pins that identity. The measured path and the live path therefore cannot drift apart
# by any amount, which is what the construction-fidelity gate needs in order to mean something.
# Call sites below are unchanged.
from .no_trade_band import band_select as _band_select        # noqa: E402  (kept at its old site)
from .no_trade_band import exit_rank_for as _exit_rank_for    # noqa: E402


def turnover_and_costs(panel, cols, weights, top_frac=0.1, top_n=None, horizon=63,
                       flat_bps=None, exit_frac=None, exit_mult=None,
                       max_sector_w=None) -> dict:
    """Turnover and NET-of-cost performance of the long book, vs the equal-weight universe.

    Weights drift with returns between rebalances, so the trade at each date is the full
    |target - drifted| vector, not just entries and exits. Counting only names entering and
    leaving would understate turnover and flatter the net return.

    `flat_bps` overrides the market-cap cost table with a single number, which is what
    cost_breakeven_bps sweeps — the breakeven is the robust answer here, because it does not
    depend on believing any particular cost calibration.

    Only the strategy is charged; the equal-weight benchmark is left gross. That is
    deliberately unfavourable to the strategy rather than the reverse.

    NOTE ON ANNUALIZATION — these figures will not tie exactly to `construction.*`.
    quantile_backtest annualizes ARITHMETICALLY (mean x periods-per-year); this function
    COMPOUNDS, because a net-of-cost figure is meant to describe what an account actually
    ends up with. On the current panel that is a gross top-decile alpha of +13.7% here vs
    +11.8% there — same data, different convention, neither wrong. Compare cost numbers to
    cost numbers.
    """
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    prev_w, prev_cost = {}, {}
    gross, net, ew, traded_hist = [], [], [], []
    # AUDIT B11 — turnover-weighted realised cost, in one-element lists so the inner loop can
    # accumulate without a nonlocal declaration.
    _bps_num, _bps_den = [0.0], [0.0]
    for d in dates:
        sub = panel[panel["date"] == d]
        if len(sub) < 20:
            continue
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        k = int(top_n) if top_n else max(1, int(len(sub) * top_frac))
        _all_t = sub["ticker"].values
        # Band as a universe FRACTION (exit_frac) or as a multiple of the book size
        # (exit_mult) — the latter is the only one meaningful for a fixed-N book.
        _xr = k
        if exit_mult is not None:
            _xr = max(k, int(round(k * exit_mult)))
        elif exit_frac is not None:
            # S14 ADOPTION 2026-08-13: the FRACTION derivation now lives in one place and the
            # live path imports the same function. Exactly equivalent to the inline
            # `max(k, int(len(sub) * exit_frac))` this replaces -- the truncation is preserved
            # deliberately, and a test pins the equivalence over a grid rather than asserting it.
            _xr = _exit_rank_for(len(sub), k, exit_frac)
        _sel = _band_select(comp, _all_t, set(prev_w), k, _xr)
        if max_sector_w:
            _secmap = dict(zip(_all_t, sub["sector"].values)) if "sector" in sub.columns else {}
            _byname = {t: j for j, t in enumerate(_all_t)}
            _ord = [_byname[t] for t in _sel] + [j for j in np.argsort(-comp)
                                                 if _all_t[j] not in set(_sel)]
            _sel = [_all_t[j] for j in _sector_capped(_ord, _all_t, _secmap, k, max_sector_w)]
        _pos = {t: i for i, t in enumerate(_all_t)}
        order = np.array([_pos[t] for t in _sel], dtype=int)
        tick = sub["ticker"].values[order]
        rets = sub["fwd_ret"].values[order]
        mcap = (sub["market_cap"].values[order] if "market_cap" in sub.columns
                else np.full(len(order), np.nan))
        ok = np.isfinite(rets)
        if not ok.any():
            continue
        tick, rets, mcap = tick[ok], rets[ok], mcap[ok]
        w = 1.0 / len(tick)
        cur_w = {t: w for t in tick}
        cur_cost = {t: (flat_bps if flat_bps is not None else one_way_cost_bps(m))
                    for t, m in zip(tick, mcap)}

        # Trade = |target - drifted-from-last-period|, over the union of both books.
        turn = cost = 0.0
        for t in set(prev_w) | set(cur_w):
            dw = abs(cur_w.get(t, 0.0) - prev_w.get(t, 0.0))
            if dw <= 0:
                continue
            bps = cur_cost.get(t, prev_cost.get(t, COST_BPS_MICRO))
            turn += dw
            cost += dw * bps * 1e-4
            # AUDIT B11 — accumulate the TURNOVER-WEIGHTED bps actually charged. The project's
            # most quotable tradeability claim is "236 bps breakeven against a 37 bps actual
            # cost profile — a 6.4x margin". The breakeven side is computed, gridded and
            # shipped; the 37 bps side appeared exactly once, in a handoff, and was never
            # computed anywhere in the code or regression-tested. Both halves of the ratio are
            # now under test.
            _bps_num[0] += dw * bps
            _bps_den[0] += dw
        g = float(np.mean(rets))
        gross.append(g)
        net.append(g - cost)
        traded_hist.append(turn)
        allr = sub["fwd_ret"].values
        ew.append(float(np.nanmean(allr)) if np.isfinite(allr).any() else np.nan)

        # Carry DRIFTED weights into the next rebalance.
        grown = {t: w * (1.0 + r) for t, r in zip(tick, rets)}
        tot = sum(grown.values()) or 1.0
        prev_w = {t: v / tot for t, v in grown.items()}
        prev_cost = cur_cost

    if not gross:
        return {"status": "no periods"}
    per_year = 252.0 / float(horizon)
    ann = lambda xs: float(np.prod([1 + x for x in xs]) ** (per_year / len(xs)) - 1)
    ew_ok = [x for x in ew if x == x]
    ann_ew = ann(ew_ok) if ew_ok else None
    g_ann, n_ann = ann(gross), ann(net)
    # Sum|dw| counts both sides of each trade; one-way turnover is half of it.
    ann_turn = float(np.mean(traded_hist)) / 2.0 * per_year
    _rg, _rn = risk_stats(gross, per_year), risk_stats(net, per_year)
    _re = risk_stats(ew_ok, per_year) if ew_ok else {}
    return {"n_periods": len(gross), "n_names": (int(top_n) if top_n else None),
            "top_frac": (None if top_n else top_frac),
            "gross_sharpe": _rg["sharpe"], "net_sharpe": _rn["sharpe"],
            "net_max_drawdown": _rn["max_drawdown"], "net_vol_ann": _rn["vol_ann"],
            "equal_weight_sharpe": _re.get("sharpe"),
            "annual_turnover": ann_turn,
            "gross_ann": g_ann, "net_ann": n_ann,
            "cost_drag_ann": g_ann - n_ann,
            "equal_weight_ann": ann_ew,
            "gross_alpha": (None if ann_ew is None else g_ann - ann_ew),
            "net_alpha": (None if ann_ew is None else n_ann - ann_ew),
            # AUDIT B11 — the OTHER half of "236 bps breakeven vs a 37 bps actual cost profile".
            # The 37 was never computed anywhere; this is the realised turnover-weighted average
            # one-way cost the book actually paid, so the 6.4x margin has both of its numbers
            # under test instead of one.
            "realised_one_way_bps": ((_bps_num[0] / _bps_den[0]) if _bps_den[0] else None),
            "realised_cost_basis": ("flat_bps override" if flat_bps is not None
                                    else "market-cap cost table"),
            # AUDIT B11, stated rather than left implicit: two limitations of this cost model.
            "cost_model_limitations": [
                "keyed on point-in-time market cap ONLY — no spread, no average daily volume, "
                "no price level, no participation rate",
                "the equal-weight benchmark is charged ZERO cost while the strategy pays, so "
                "every 'alpha versus equal-weight' figure compares a book that trades against "
                "one that does not",
            ],
            "flat_bps": flat_bps}


# Top-bracket US taxable account, federal only. Short-term gains are ordinary income
# (37% top bracket + 3.8% NIIT); long-term is 20% + 3.8% NIIT. STATE tax is NOT included and
# is far from negligible — CA adds ~13.3% on both, NY ~10.9% — so a California investor should
# read the short-term figure as ~54%, not 40.8%. Defaults are federal so the number is not
# quietly tied to one state.
TAX_SHORT_TERM = 0.408
TAX_LONG_TERM = 0.238
LONG_TERM_DAYS = 366        # a US holding period must EXCEED one year


def after_tax_backtest(panel, cols, weights, top_frac=0.1, top_n=None, horizon=63,
                       short_rate=TAX_SHORT_TERM, long_rate=TAX_LONG_TERM,
                       flat_bps=None, lot_method="fifo", exit_frac=None,
                       exit_mult=None, max_sector_w=None) -> dict:
    """Net-of-COST and net-of-TAX performance of the long book, with real lot accounting.

    The book turns over ~250%/yr on a ~quarterly rebalance, so in a TAXABLE account almost
    every gain is realized inside a year and taxed as ordinary income. That is not a haircut
    you can wave at with an average rate: tax depends on WHEN each lot was bought, so this
    tracks individual lots, ages them against the actual calendar, and taxes each realized
    slice at the rate its own holding period earns.

    Method and its limits, stated because they move the answer:
      * FIFO lot selection (the US default absent a specific-lot election). A taxable
        investor electing HIFO/specific-lot would realize LESS gain, so this is the
        conservative end. `lot_method` is here to make that explicit, not to hide it.
      * Tax is paid FROM the portfolio at each rebalance, which is what makes the compounding
        after-tax rather than a cosmetic subtraction.
      * Unrealized gains at the end are NOT taxed — the book is not liquidated. That deferred
        liability is reported separately (`unrealized_gain_end`) so it is not mistaken for
        free money.
      * NO dividends anywhere. The panel's forward returns are price-only, so dividend income
        is absent from the gross figure and dividend tax is absent from this one. Consistent,
        but it means a high-yield book's real after-tax drag is understated.
      * No wash-sale disallowance and no loss carry-forward beyond the book itself: realized
        losses offset realized gains within the same rebalance and any excess carries forward,
        which is the ordinary treatment for an investor with other gains.
    """
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    if len(dates) < 3:
        return {"status": "not enough dates"}
    dts = {d: pd.to_datetime(d) for d in dates}

    lots = {}                       # ticker -> [[entry_date, basis, value], ...] FIFO order
    # Last-known cost for every ticker ever held. An EXIT is by definition not in the new
    # book, so looking its cost up in this period's table alone would miss and fall back to
    # the micro-cap rate — charging ~150bps to sell a mega-cap and inventing a drag that is
    # not there.
    cost_hist = {}
    value = 1.0                     # portfolio value, after tax and costs
    gross_v = 1.0                   # same book, no costs, no tax
    ew, gross_r, net_r, tax_r = [], [], [], []
    tax_short, tax_long, gain_short, gain_long, carry_loss = 0.0, 0.0, 0.0, 0.0, 0.0

    for di, d in enumerate(dates):
        sub = panel[panel["date"] == d]
        if len(sub) < 20:
            continue
        comp = composite_from_frame(sub, cols, weights, zscore)   # AUDIT B7
        k = int(top_n) if top_n else max(1, int(len(sub) * top_frac))
        _all_t = sub["ticker"].values
        # Band as a universe FRACTION (exit_frac) or as a multiple of the book size
        # (exit_mult) — the latter is the only one meaningful for a fixed-N book.
        _xr = k
        if exit_mult is not None:
            _xr = max(k, int(round(k * exit_mult)))
        elif exit_frac is not None:
            # S14 ADOPTION 2026-08-13: the FRACTION derivation now lives in one place and the
            # live path imports the same function. Exactly equivalent to the inline
            # `max(k, int(len(sub) * exit_frac))` this replaces -- the truncation is preserved
            # deliberately, and a test pins the equivalence over a grid rather than asserting it.
            _xr = _exit_rank_for(len(sub), k, exit_frac)
        _sel = _band_select(comp, _all_t, set(lots), k, _xr)
        if max_sector_w:
            _secmap = dict(zip(_all_t, sub["sector"].values)) if "sector" in sub.columns else {}
            _byname = {t: j for j, t in enumerate(_all_t)}
            _ord = [_byname[t] for t in _sel] + [j for j in np.argsort(-comp)
                                                 if _all_t[j] not in set(_sel)]
            _sel = [_all_t[j] for j in _sector_capped(_ord, _all_t, _secmap, k, max_sector_w)]
        _pos = {t: i for i, t in enumerate(_all_t)}
        order = np.array([_pos[t] for t in _sel], dtype=int)
        tick = sub["ticker"].values[order]
        rets = sub["fwd_ret"].values[order]
        mcap = (sub["market_cap"].values[order] if "market_cap" in sub.columns
                else np.full(len(order), np.nan))
        ok = np.isfinite(rets)
        if not ok.any():
            continue
        tick, rets, mcap = tick[ok], rets[ok], mcap[ok]
        cost_of = {t: (flat_bps if flat_bps is not None else one_way_cost_bps(m))
                   for t, m in zip(tick, mcap)}
        cost_hist.update(cost_of)

        total = sum(l[2] for ls in lots.values() for l in ls) or value
        target = {t: total / len(tick) for t in tick}
        traded_cost, realized_s, realized_l = 0.0, 0.0, 0.0

        # ---- SELL: trim anything above target (and exit anything not in the new book) ----
        for t in list(lots):
            held = sum(l[2] for l in lots[t])
            want = target.get(t, 0.0)
            if held <= want + 1e-12:
                continue
            to_sell = held - want
            traded_cost += to_sell * cost_hist.get(t, COST_BPS_MICRO) * 1e-4
            remaining = to_sell
            keep = []
            for lot in lots[t]:                      # FIFO: oldest lot first
                if remaining <= 1e-15:
                    keep.append(lot)
                    continue
                entry, basis, val = lot
                take = min(val, remaining)
                frac = take / val if val > 0 else 0.0
                gain = take - basis * frac
                # The holding period is measured on the real calendar, so a lot that survives
                # four ~quarterly rebalances correctly becomes long-term.
                if (dts[d] - dts[entry]).days > LONG_TERM_DAYS:
                    realized_l += gain
                else:
                    realized_s += gain
                remaining -= take
                if val - take > 1e-15:
                    keep.append([entry, basis * (1 - frac), val - take])
            lots[t] = keep
            if not lots[t]:
                del lots[t]

        # ---- BUY: top up to target, each purchase its own lot with its own clock ----
        for t in tick:
            held = sum(l[2] for l in lots.get(t, []))
            want = target[t]
            if want > held + 1e-12:
                buy = want - held
                traded_cost += buy * cost_hist.get(t, COST_BPS_MICRO) * 1e-4
                lots.setdefault(t, []).append([d, buy, buy])

        # ---- tax on what was realized this rebalance ----
        net_short = realized_s
        net_long = realized_l
        pool = net_short + net_long + carry_loss
        carry_loss = 0.0
        if pool < 0:                                  # net loss -> no tax, carry it forward
            carry_loss = pool
            tax_due = 0.0
        else:
            # Losses offset the highest-taxed gains first, which is what a taxable investor
            # would do and keeps this from overstating the drag.
            s = max(0.0, net_short + min(0.0, net_long))
            l = max(0.0, pool - s)
            tax_due = s * short_rate + l * long_rate
            tax_short += s * short_rate
            tax_long += l * long_rate
            gain_short += s
            gain_long += l

        drag = traded_cost + tax_due
        # Paying costs and tax out of the book is what makes the compounding after-tax.
        scale = (total - drag) / total if total > 0 else 1.0
        for t in lots:
            for lot in lots[t]:
                lot[2] *= scale

        # ---- hold the period ----
        r_by_t = {t: r for t, r in zip(tick, rets)}
        start = sum(l[2] for ls in lots.values() for l in ls)
        for t in list(lots):
            r = r_by_t.get(t)
            if r is None or r != r:
                continue
            for lot in lots[t]:
                lot[2] *= (1.0 + r)
        end = sum(l[2] for ls in lots.values() for l in ls)

        g = float(np.mean(rets))
        gross_v *= (1.0 + g)
        gross_r.append(g)
        net_r.append((end - value) / value if value > 0 else 0.0)
        tax_r.append(tax_due / total if total > 0 else 0.0)
        value = end
        allr = sub["fwd_ret"].values
        ew.append(float(np.nanmean(allr)) if np.isfinite(allr).any() else np.nan)

    if not gross_r:
        return {"status": "no periods"}
    per_year = 252.0 / float(horizon)
    n = len(gross_r)
    ann = lambda xs: float(np.prod([1 + x for x in xs]) ** (per_year / len(xs)) - 1)
    ew_ok = [x for x in ew if x == x]
    ann_ew = ann(ew_ok) if ew_ok else None
    g_ann = ann(gross_r)
    at_ann = float(value ** (per_year / n) - 1)
    basis_end = sum(l[1] for ls in lots.values() for l in ls)
    value_end = sum(l[2] for ls in lots.values() for l in ls)
    _rt = risk_stats(net_r, per_year)
    return {
        "n_periods": n, "years": round(n / per_year, 1),
        "short_rate": short_rate, "long_rate": long_rate, "lot_method": lot_method,
        "after_tax_sharpe": _rt["sharpe"], "after_tax_max_drawdown": _rt["max_drawdown"],
        "after_tax_vol_ann": _rt["vol_ann"],
        "gross_ann": g_ann, "after_tax_ann": at_ann,
        "equal_weight_ann": ann_ew,
        "gross_alpha": (None if ann_ew is None else g_ann - ann_ew),
        "after_tax_alpha": (None if ann_ew is None else at_ann - ann_ew),
        "total_drag_ann": g_ann - at_ann,
        "tax_paid_short": tax_short, "tax_paid_long": tax_long,
        "gains_short": gain_short, "gains_long": gain_long,
        "short_term_share_of_gains": (gain_short / (gain_short + gain_long)
                                      if (gain_short + gain_long) > 0 else None),
        "unrealized_gain_end": value_end - basis_end,
        "note": ("after_tax_alpha is for a TAXABLE account; a tax-advantaged account (IRA/401k) "
                 "pays no drag and earns the net-of-cost figure instead"),
    }


def cost_breakeven_bps(panel, cols, weights, top_frac=0.1, top_n=None, horizon=63,
                       grid=(0, 5, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200)) -> dict:
    """The one-way cost (bps) at which net alpha vs equal-weight reaches zero.

    This is the number to quote. It converts "is the edge tradeable?" from an argument about
    cost assumptions into a single figure you can compare against what execution actually
    costs: if breakeven is 80bps and the book is large caps, it is comfortable; if breakeven
    is 12bps on a small-cap book, it is not.
    """
    curve = []
    for bps in grid:
        r = turnover_and_costs(panel, cols, weights, top_frac=top_frac, top_n=top_n,
                               horizon=horizon, flat_bps=float(bps))
        if r.get("net_alpha") is None:
            continue
        curve.append({"bps": float(bps), "net_alpha": r["net_alpha"], "net_ann": r["net_ann"]})
    be = None
    for a, b in zip(curve, curve[1:]):
        if a["net_alpha"] >= 0 > b["net_alpha"]:
            span = a["net_alpha"] - b["net_alpha"]
            be = a["bps"] + (b["bps"] - a["bps"]) * (a["net_alpha"] / span if span else 0.0)
            break
    if be is None and curve and curve[-1]["net_alpha"] >= 0:
        be = float("inf")                      # survives the whole grid
    return {"breakeven_one_way_bps": be, "curve": curve}


def holdout_compare_panels(panel_a, panel_b, cols, label_a="A", label_b="B", n_q=10,
                           horizon=63, base_weight=0.125, min_dates=16,
                           min_alpha_gain=MIN_HOLDOUT_ALPHA_GAIN,
                           min_tstat_gain=MIN_HOLDOUT_TSTAT_GAIN,
                           standardizer_a=None, standardizer_b=None) -> dict:
    """Held-out comparison of two PANEL CONSTRUCTIONS (not two weightings).

    holdout_theme_validate answers "should this theme carry weight". Some changes are not a
    weight at all — sector-neutral scoring rebuilds every z-score — so they need the same
    discipline in a different shape: split by time, embargo the boundary, and require B to
    beat A by the SAME pre-committed margin (MIN_HOLDOUT_*) in BOTH split directions.

    Both panels must cover the same dates; only the construction differs.

    LEDGER S20/S21 — `standardizer_a` / `standardizer_b` let the two arms be scored by DIFFERENT
    standardizers, which is what makes a standardization change testable through this gate at all:
    the incumbent keeps the shipped winsorized z-score while the challenger uses its own. Both
    default to None (= the shipped `zscore`), so every existing caller is unchanged.
    """
    out = {"label_a": label_a, "label_b": label_b, "splits": {},
           "min_alpha_gain": min_alpha_gain, "min_tstat_gain": min_tstat_gain}
    if panel_a is None or panel_b is None or panel_a.empty or panel_b.empty:
        return {**out, "verdict": "no panel"}
    dates = sorted(set(panel_a["date"].unique()) & set(panel_b["date"].unique()))
    if len(dates) < min_dates:
        return {**out, "verdict": f"only {len(dates)} shared dates"}
    mid = len(dates) // 2
    out["boundary_date_embargoed"] = str(dates[mid])
    w = {c: base_weight for c in cols}
    halves = {"early_half": dates[:mid], "late_half": dates[mid + 1:]}
    improves = []
    for name, ds in halves.items():
        ra = quantile_backtest(panel_a[panel_a["date"].isin(ds)], cols, w,
                               n_q=n_q, horizon=horizon, standardizer=standardizer_a) or {}
        rb = quantile_backtest(panel_b[panel_b["date"].isin(ds)], cols, w,
                               n_q=n_q, horizon=horizon, standardizer=standardizer_b) or {}
        dt = (None if ra.get("long_short_tstat") is None or rb.get("long_short_tstat") is None
              else rb["long_short_tstat"] - ra["long_short_tstat"])
        da = (None if ra.get("top_decile_alpha") is None or rb.get("top_decile_alpha") is None
              else rb["top_decile_alpha"] - ra["top_decile_alpha"])
        ok = bool(dt is not None and da is not None
                  and dt >= min_tstat_gain and da >= min_alpha_gain)
        improves.append(ok)
        out["splits"][name] = {
            "n_dates": len(ds),
            "a_long_short_tstat": ra.get("long_short_tstat"),
            "b_long_short_tstat": rb.get("long_short_tstat"),
            "a_top_decile_alpha": ra.get("top_decile_alpha"),
            "b_top_decile_alpha": rb.get("top_decile_alpha"),
            "delta_long_short_tstat": dt, "delta_top_decile_alpha": da, "improves": ok}
    out["verdict"] = ("adopt" if all(improves)
                      else "reject" if not any(improves) else "not_replicated")
    return out


def holdout_theme_validate(panel, cols, n_q=10, horizon=63, base_weight=0.125,
                           min_dates=16, min_alpha_gain=MIN_HOLDOUT_ALPHA_GAIN,
                           min_tstat_gain=MIN_HOLDOUT_TSTAT_GAIN) -> dict:
    """Time-split checks that ZEROING a theme helps on data not used to decide it.

    CPCV and the Deflated Sharpe correct for the trials inside the *weight search*. Neither
    corrects for a human looking at a theme's IC on the whole panel, deciding to drop it, and
    then measuring the improvement on that same panel — which is how `low_risk` was zeroed.
    This is the missing test, and it is permanent rather than a one-off script so the claim
    keeps being re-checked on every run.

    THIS FUNCTION SHIPS TWO DIFFERENT VERDICTS AND THEY ANSWER DIFFERENT QUESTIONS.
    [AUDIT B8 — RESOLVED 2026-08-06, session 7.] It used to ship one, `verdicts`, whose
    docstring described the protocol below while the code ignored step 2 entirely: `rule_fired`
    was computed and never read, so a theme could read `confirmed` in a direction where the
    decide half never flagged it. That is a BOTH-HALVES STABILITY CHECK, not an out-of-sample
    confirmation, and the project called it the latter for months.

    Both are now computed and named for what they are:

    * **`verdicts` (unchanged semantics, honest name `stability_verdicts`)** — "does zeroing
      this theme improve the measure half, in both split directions?" The decide half is NOT
      consulted. It is a demanding and legitimate test, it is what every shipped decision in
      this project actually rested on, and X7's measured ~6% false-positive rate was calibrated
      against THIS object. Its meaning is deliberately frozen so that figure keeps applying.
    * **`oos_verdicts` (new — the protocol the docstring always described)** — step 2 is
      enforced: a theme is a CANDIDATE in a direction only if the pre-specified rule fires on
      that direction's decide half. Directions where it did not fire are `not_flagged` and
      contribute no evidence, because nothing selected the theme there.

    Protocol, fixed in advance:
      1. Split the rebalance dates in half BY TIME, and EMBARGO the boundary date — with
         rebalance == horizon, its forward window is the only one that can straddle the split.
      2. DECIDE on one half with a pre-specified rule: a theme is flagged if its MEDIAN IC on
         the decide half is <= 0. Stated as a rule so it can't be reverse-engineered per theme.
      3. MEASURE on the other half ONLY: the composite's long-short t and top-decile alpha
         with that theme at `base_weight` vs at 0. The measure half never informs the decision.
      4. Run BOTH directions, so no result rests on one arbitrary split.

    A theme is `confirmed` only if zeroing it improves BOTH metrics by at least the
    pre-specified MINIMUM MARGIN (see MIN_HOLDOUT_*), in BOTH directions. `not_replicated`
    means it worked one way and not the other, or cleared the sign but not the margin — the
    usual fate of noise. Requiring a margin rather than just the right sign is deliberate: the
    sign-only version admitted a +0.01 t-stat move as a confirmation.

    `oos_verdicts` applies the identical margin, but only over directions that flagged the
    theme: `confirmed_oos` if every flagged direction improves, `rejected_oos` if none does,
    `not_replicated_oos` if they disagree, and `not_flagged` if the rule never fired — in which
    case NO out-of-sample test of this theme was run and the stability verdict must not be
    quoted as though one had been. `oos_directions_tested` reports how many of the two
    directions carried evidence, because a one-direction confirmation is weaker than a
    two-direction one and the single word "confirmed" hides that.

    Weights are equal across `cols` rather than read from settings, so the comparison is
    "this theme in vs out", not "current live config vs something else".
    """
    out = {"rule": "median IC <= 0 on the decide half",
           "metric": "long_short_tstat and top_decile_alpha, measured on the held-out half",
           "min_alpha_gain": min_alpha_gain, "min_tstat_gain": min_tstat_gain,
           "verdicts_scope": "both_halves_stability — the decide-half rule is NOT applied "
                             "(audit B8); see oos_verdicts for the rule-gated protocol",
           "oos_verdicts_scope": "rule-gated out-of-sample — only directions whose decide half "
                                 "flagged the theme carry evidence (audit B8)",
           "splits": {}, "verdicts": {}, "oos_verdicts": {}, "oos_directions_tested": {}}
    if panel is None or panel.empty or not cols:
        return {**out, "status": "no panel"}
    dates = sorted(panel["date"].unique())
    if len(dates) < min_dates:
        return {**out, "status": f"only {len(dates)} dates, need {min_dates}"}
    mid = len(dates) // 2
    halves = {"decide_early_measure_late": (dates[:mid], dates[mid + 1:]),
              "decide_late_measure_early": (dates[mid + 1:], dates[:mid])}
    out["boundary_date_embargoed"] = str(dates[mid])

    def _w(zeroed):
        return {c: (0.0 if c == zeroed else base_weight) for c in cols}

    for name, (dec, mea) in halves.items():
        p_dec, p_mea = panel[panel["date"].isin(dec)], panel[panel["date"].isin(mea)]
        ic_d, ic_m = theme_ic(p_dec), theme_ic(p_mea)
        base = quantile_backtest(p_mea, cols, _w(None), n_q=n_q, horizon=horizon) or {}
        blk = {"decide_dates": len(dec), "measure_dates": len(mea),
               "baseline": {"long_short_tstat": base.get("long_short_tstat"),
                            "top_decile_alpha": base.get("top_decile_alpha"),
                            "long_short_ann": base.get("long_short_ann"),
                            "monotonicity": base.get("monotonicity")},
               "themes": {}}
        for c in cols:
            d, m = ic_d.get(c) or {}, ic_m.get(c) or {}
            d_ic = d.get("median_ic")
            r = quantile_backtest(p_mea, cols, _w(c), n_q=n_q, horizon=horizon) or {}
            dt = (None if r.get("long_short_tstat") is None or base.get("long_short_tstat") is None
                  else r["long_short_tstat"] - base["long_short_tstat"])
            da = (None if r.get("top_decile_alpha") is None or base.get("top_decile_alpha") is None
                  else r["top_decile_alpha"] - base["top_decile_alpha"])
            blk["themes"][c] = {
                "decide_median_ic": d_ic, "decide_ic_tstat": d.get("ic_tstat"),
                "measure_median_ic": m.get("median_ic"), "measure_ic_tstat": m.get("ic_tstat"),
                "rule_fired": (d_ic is not None and d_ic <= 0),
                "zeroed_long_short_tstat": r.get("long_short_tstat"),
                "zeroed_top_decile_alpha": r.get("top_decile_alpha"),
                "delta_long_short_tstat": dt, "delta_top_decile_alpha": da,
                "improves": bool(dt is not None and da is not None
                                 and dt >= min_tstat_gain and da >= min_alpha_gain)}
        out["splits"][name] = blk

    for c in cols:
        got = [out["splits"][s]["themes"][c]["improves"] for s in out["splits"]]
        out["verdicts"][c] = ("confirmed" if all(got)
                              else "rejected" if not any(got) else "not_replicated")
        # AUDIT B8 — the rule-gated protocol the docstring describes. A direction where the
        # decide half never flagged the theme is dropped rather than counted as evidence: the
        # measure-half number is real, but nothing SELECTED the theme in that direction, so it
        # confirms no decision anybody made. This is the whole difference between the two
        # verdicts, and it is why `rule_fired` had to stop being decorative.
        flagged = [out["splits"][s]["themes"][c]["improves"] for s in out["splits"]
                   if out["splits"][s]["themes"][c]["rule_fired"]]
        out["oos_directions_tested"][c] = len(flagged)
        out["oos_verdicts"][c] = ("not_flagged" if not flagged
                                  else "confirmed_oos" if all(flagged)
                                  else "rejected_oos" if not any(flagged)
                                  else "not_replicated_oos")
    out["stability_verdicts"] = out["verdicts"]      # the honest name for the frozen object
    return out


# A wired signal present in fewer than this fraction of panel rows is almost certainly a
# PLUMBING bug, not a thin signal. Every data bug this project has hit looked identical from
# the outside — the factor was wired, the run completed, no error was raised, and the column
# was silently empty (`assets` missing from the loader allowlist emptied capital_discipline;
# Sharadar leaves roe/roic/assetturnover blank in the ARQ dimension, so quality ran on 8 of
# its 10 inputs and low_risk on 1 of its 2, for every run in this project's history).
# 5% is deliberately far below any plausible real coverage: even the institutional theme,
# whose source data does not start until 2013, sits above 80%.
# --------------------------------------------------------------------------------------- #
# P8 — CORRECTNESS layer. signal_coverage() checks a factor is PRESENT; this checks it is
# SANE. Four foundation bugs have now shipped with the same signature — the run completes,
# raises nothing, and a factor is silently wrong — and coverage caught only the two that left
# a column EMPTY. The currency bug (P7) filled every column and was simply incorrect.
#
# Plausible cross-sectional bounds for each ratio factor. Generous on purpose: the job is to
# catch a 1,500x error, not to police a fat tail. A quarterly earnings yield of 5 means the
# company earned five times its market cap in three months.
# CALIBRATED against the known-broken (pre-P7) and known-good (post-P7) values on the same
# rows, so each band demonstrably separates them instead of being a guess. Bands are two-sided
# and generous: NEGATIVE book equity and negative EV (net cash above market cap) are both
# legitimate, and an early band of [0, 25] on book_to_price flagged 6.1% of perfectly good
# rows. A guard that always fires trains you to ignore it.
#
#   factor           band          flagged on FIXED   on BROKEN
#   book_to_price    [-50, 50]           0.005%         0.285%    <- separates well
#   fcf_yield        [-10, 10]           0.022%         0.028%
#   ebit_ev          [-25, 25]           0.033%         0.039%
#   earnings_yield   [-10, 10]           ~0%            ~0%       <- range can't see it
#
# `ev_sales`, `ev_ebitda` and `ps` are deliberately NOT range-checked: their tails are driven by
# near-zero-denominator companies (a real |max| of 2.9M on good data), negative EV is legitimate,
# and the band flagged identical shares before and after the fix — a pure no-op. The SUBGROUP
# check below is what covers them. `ev_ebitda` is already restricted to POSITIVE EBITDA at
# construction, so its remaining tail is genuinely "barely profitable", not a sign error.
SANE_RANGES = {
    "book_to_price": (-50.0, 50.0),
    "earnings_yield": (-10.0, 10.0),   # quarterly earnings / market cap
    "fcf_yield": (-10.0, 10.0),
    "ebit_ev": (-25.0, 25.0),
}
# Ratios measured but intentionally exempt from the range check (see above).
SANE_RANGE_EXEMPT = ("ev_sales", "ev_ebitda", "ps")
SANE_VIOLATION_SHARE = 0.01        # >1% of rows outside the band = systematic, not a fat tail
# A subgroup whose MEDIAN percentile sits this high/low is pegged. 0.70 verified against the
# pre-P7 values: it catches 4 of the 6 corrupted value ratios (book_to_price and
# earnings_yield reached 0.86 alone) with ZERO false positives on the corrected data, where
# every factor lands in 0.49-0.61. This is a detector threshold tuned on known-bad vs
# known-good data — it affects no return and no weight, so it is not the kind of
# after-the-fact tuning holdout_theme_validate exists to prevent.
SUBGROUP_PEG_PCTILE = 0.70
MC_DIVERGENCE_FACTOR = 3.0         # DAILY market cap vs shares x price
MC_DIVERGENCE_SHARE = 0.01


def sanity_check(panel, ranges=None, warn=True) -> dict:
    """Post-panel correctness pass: are the factor VALUES believable?

    Three checks, each aimed at a bug class that has actually shipped here:

      range      — every ratio factor inside a plausible cross-sectional band. Catches the
                   currency bug directly (SKM's book_to_price was 892).
      subgroup   — does an identifiable subgroup systematically PEG a factor? Foreign
                   reporters are free to identify (fxusd != 1), and "every foreign name is in
                   the top 2% of book_to_price" is precisely the currency signature. This is
                   the check that would have caught P7 on its first run.
      market_cap — DAILY market cap vs shares x price. Catches recycled/spun-off tickers
                   inheriting a parent's history (SanDisk showing $337B, ~10x reality).

    Needs a panel built with keep_numbers=True. Returns flags, never raises: a backtest that
    dies on a data quirk gets the check deleted, one that reports loudly gets it fixed.
    """
    ranges = ranges or SANE_RANGES
    out = {"available": False, "checks": {}, "flags": []}
    if panel is None or panel.empty:
        return out
    n = float(len(panel))
    out["available"] = True

    # ---- 1. sane ranges on the raw ratio levels ----
    rng = {}
    for name, (lo, hi) in ranges.items():
        col = "raw_" + name
        if col not in panel.columns:
            continue
        s = pd.to_numeric(panel[col], errors="coerce").dropna()
        if s.empty:
            continue
        bad = int(((s < lo) | (s > hi)).sum())
        share = bad / float(len(s))
        rng[name] = {"n": int(len(s)), "outside": bad, "share": share,
                     "lo": lo, "hi": hi,
                     "p01": float(s.quantile(0.01)), "median": float(s.median()),
                     "p99": float(s.quantile(0.99)), "max_abs": float(s.abs().max())}
        if share > SANE_VIOLATION_SHARE:
            out["flags"].append({
                "check": "range", "factor": name, "share_outside": share,
                "band": [lo, hi], "p99": rng[name]["p99"], "max_abs": rng[name]["max_abs"],
                "detail": f"{share:.2%} of rows outside [{lo}, {hi}] — systematic, not a fat tail"})
    out["checks"]["range"] = rng

    # ---- 1b. SIGN check on the range-exempt ratios ----
    # AUDIT B18. `ev_sales`, `ev_ebitda` and `ps` are exempt from the range band because they
    # legitimately take a wide range — which meant the one place a sign error could hide was the
    # one place nothing checked. A sign check is cheap and needs no band: after the negative-EV
    # convention was unified these should be empty, and a non-zero count means the guard has
    # something to say.
    sign = {}
    for name in SANE_RANGE_EXEMPT:
        col = "raw_" + name
        if col not in panel.columns:
            continue
        s = pd.to_numeric(panel[col], errors="coerce").dropna()
        if s.empty:
            continue
        neg = int((s < 0).sum())
        sign[name] = {"n": int(len(s)), "negative": neg, "share": neg / float(len(s))}
        if neg:
            out["flags"].append({
                "check": "sign", "factor": name, "negative": neg,
                "share_negative": neg / float(len(s)),
                "detail": (f"{neg} rows ({neg/float(len(s)):.2%}) of {name} are NEGATIVE — a "
                           f"negative multiple sorts to the wrong end of the value theme once "
                           f"negated; the convention is to treat it as missing")})
    out["checks"]["sign"] = sign

    # ---- 2. subgroup pegging ----
    sub = {}
    if "is_foreign" in panel.columns:
        flag = panel["is_foreign"].fillna(False).astype(bool)
        n_for = int(flag.sum())
        sub["foreign"] = {"n_rows": n_for, "share_of_rows": n_for / n}
        if n_for and n_for < len(panel):
            per_factor = {}
            # AUDIT B24 — de-duplicate the scan list. SANE_RANGES keys and SANE_RANGE_EXEMPT
            # names also appear as z_ columns, so factors were evaluated more than once, and the
            # raw-versus-z preference below meant the same factor could be measured on a raw
            # level in one pass and a standardised value in another. Worse, a factor and its
            # own negated twin were both reported — the shipped output showed `ev_ebitda` at a
            # foreign median percentile of 0.362 next to `neg_ev_ebitda` at 0.640, which is one
            # fact printed twice with the sign flipped. Cosmetic on its own, but an inflated
            # flag count trains readers to ignore the guard, and this guard is the one that
            # would have caught the currency bug.
            _seen, _scan = set(), []
            for name in (list(ranges) + list(SANE_RANGE_EXEMPT)
                         + [c[2:] for c in panel.columns if c.startswith("z_")]):
                if name not in _seen:
                    _seen.add(name)
                    _scan.append(name)
            _scan = [nm for nm in _scan
                     if not (nm.startswith("neg_") and nm[4:] in _seen)]
            for name in _scan:
                col = "raw_" + name if "raw_" + name in panel.columns else "z_" + name
                if col not in panel.columns:
                    continue
                s = pd.to_numeric(panel[col], errors="coerce")
                if s.notna().sum() < 100:
                    continue
                # Percentile rank WITHIN each date, so a subgroup tilt can't be a time effect.
                pct = s.groupby(panel["date"]).rank(pct=True)
                med = float(pct[flag].median()) if pct[flag].notna().any() else float("nan")
                if med != med:
                    continue
                per_factor[name] = med
                if med >= SUBGROUP_PEG_PCTILE or med <= (1.0 - SUBGROUP_PEG_PCTILE):
                    out["flags"].append({
                        "check": "subgroup", "factor": name, "subgroup": "foreign_reporters",
                        "median_percentile": med, "n_rows": n_for,
                        "detail": (f"foreign reporters sit at the {med:.0%} percentile of "
                                   f"{name} — a subgroup should not systematically peg a factor")})
            sub["foreign_median_percentile"] = dict(
                sorted(per_factor.items(), key=lambda kv: -abs(kv[1] - 0.5)))
    out["checks"]["subgroup"] = sub

    # ---- 3. market-cap divergence ----
    mc = {}
    if "mc_ratio" in panel.columns:
        s = pd.to_numeric(panel["mc_ratio"], errors="coerce").dropna()
        s = s[s > 0]
        if not s.empty:
            bad = ((s > MC_DIVERGENCE_FACTOR) | (s < 1.0 / MC_DIVERGENCE_FACTOR))
            share = float(bad.mean())
            worst = panel.loc[s[bad].sort_values(ascending=False).index[:10], ["ticker", "mc_ratio"]] \
                if bad.any() else None
            mc = {"n": int(len(s)), "median_ratio": float(s.median()),
                  "share_diverging": share, "factor": MC_DIVERGENCE_FACTOR,
                  "worst": ([{"ticker": str(t), "ratio": float(r)}
                             for t, r in worst.drop_duplicates("ticker").values[:10]]
                            if worst is not None else [])}
            if share > MC_DIVERGENCE_SHARE:
                out["flags"].append({
                    "check": "market_cap", "share_diverging": share,
                    "detail": (f"{share:.2%} of rows have DAILY market cap more than "
                               f"{MC_DIVERGENCE_FACTOR}x from shares x price — recycled or "
                               f"spun-off tickers inheriting a parent's history")})
    out["checks"]["market_cap"] = mc

    if warn and out["flags"]:
        import sys as _s
        print(f"[sanity] WARNING: {len(out['flags'])} correctness flag(s) — a factor is "
              f"POPULATED but implausible. Coverage cannot see this class of bug:",
              file=_s.stderr, flush=True)
        for f in out["flags"][:20]:
            print(f"[sanity]   {f['check']:10s} {f.get('factor', ''):18s} {f['detail']}",
                  file=_s.stderr, flush=True)
    return out


COVERAGE_FLOOR = 0.05

# Themes exempt from the coverage warning because they are DECLARED hooks: wired in advance
# of a data source that does not exist yet, so empty is their correct state and warning about
# them would train the reader to ignore this block.
#
# Deliberately an explicit list rather than "any theme with zero weight". A theme can be
# zero-weighted because it was MEASURED and found not to earn its place (low_risk), and that
# is completely different from having no data: its inputs still exist, the weight is
# reversible, and a plumbing bug in one must still be reported. Only add a theme here when
# there is genuinely no point-in-time source for it.
COVERAGE_EXEMPT_THEMES = frozenset({"sentiment"})   # no point-in-time estimates feed (parked)


def signal_coverage(panel, floor=COVERAGE_FLOOR, warn=True) -> dict:
    """{signal: coverage} for every wired number and theme, plus who is under `floor`.

    Coverage is measured on the STANDARDIZED column (`z_<num>`), not the raw input, because
    that is what actually reaches the composite: `zscore()` returns all-NaN for a column with
    zero cross-sectional variation, so a constant column is correctly reported as unusable
    rather than fully covered.

    Needs a panel built with keep_numbers=True for the per-number figures; theme coverage
    works on any panel. Warns to stderr for anything under the floor — the whole point is
    that a silently-empty factor becomes impossible to miss.
    """
    out = {"floor": float(floor), "numbers": {}, "themes": {}, "below_floor": []}
    if panel is None or panel.empty:
        return out
    n = float(len(panel))
    for num in S.NUMBERS_ALL:
        zc = "z_" + num
        if zc in panel.columns:
            out["numbers"][num] = float(panel[zc].notna().sum() / n)
    for theme in S.FACTORS_ALL:
        if theme in panel.columns:
            out["themes"][theme] = float(panel[theme].notna().sum() / n)
    _dead = set(COVERAGE_EXEMPT_THEMES)
    out["exempt_themes"] = sorted(_dead)
    for kind, vals in (("number", out["numbers"]), ("theme", out["themes"])):
        for name, cov in vals.items():
            theme = name if kind == "theme" else S.NUMBER_THEME.get(name)
            if cov < floor and theme not in _dead:
                out["below_floor"].append({"kind": kind, "name": name, "coverage": cov,
                                           "theme": theme})
    out["below_floor"].sort(key=lambda r: r["coverage"])
    if warn and out["below_floor"]:
        import sys as _s
        print(f"[coverage] WARNING: {len(out['below_floor'])} wired signal(s) below "
              f"{floor:.0%} coverage on {int(n):,} panel rows — these contribute nothing and "
              f"are probably a data/plumbing bug, not a weak signal:", file=_s.stderr, flush=True)
        for r in out["below_floor"]:
            print(f"[coverage]   {r['kind']:6s} {r['name']:20s} {r['coverage']:7.2%}",
                  file=_s.stderr, flush=True)
    return out


# A stale EV is not an error, so nothing raises when the rebuild silently stops working — the
# ratios just quietly go back to being priced ~111 days late. This is the floor at which that
# becomes a reportable problem rather than the handful of rows with no net-debt data at all.
EV_FRESH_FLOOR = 0.95


def ev_freshness(panel, floor=EV_FRESH_FLOOR, warn=True) -> dict:
    """How many rows got an EV priced at the REBALANCE date, and how far that moved it.

    Coverage says `ev_sales` is PRESENT; this says it is CURRENT. They are different questions
    and only the second one catches a rebuild that has quietly reverted to the filing's value —
    which is exactly the failure this fix exists to prevent, and which no test of a single row
    can notice once the fallback path is doing the work.

    `drift` is the fix's own effect size: the relative gap between the filing's EV and the
    re-priced one. Near-zero drift on a full panel would mean the rebuild is running but not
    actually changing anything, which is its own kind of broken.
    """
    out = {"floor": float(floor), "rows": 0, "by_source": {}, "fresh": None,
           "stale": None, "drift": {}, "ok": True, "warnings": []}
    if panel is None or panel.empty or "ev_src" not in panel.columns:
        out["warnings"].append("no ev_src column — panel built without keep_numbers?")
        out["ok"] = False
        return out
    n = float(len(panel))
    out["rows"] = int(n)
    vc = panel["ev_src"].value_counts(dropna=False)
    out["by_source"] = {("none" if pd.isna(k) else str(k)): int(v) for k, v in vc.items()}
    fresh_tags = {EV_SRC_LINE_ITEMS, EV_SRC_IDENTITY}
    fresh = float(panel["ev_src"].isin(fresh_tags).sum() / n)
    out["fresh"] = fresh
    out["stale"] = 1.0 - fresh
    if "ev_drift" in panel.columns:
        d = pd.to_numeric(panel["ev_drift"], errors="coerce").dropna()
        if len(d):
            out["drift"] = {"median": float(d.median()), "mean": float(d.mean()),
                            "p90": float(d.quantile(0.90)),
                            "frac_over_10pct": float((d > 0.10).mean()),
                            "frac_over_25pct": float((d > 0.25).mean())}
    # Flag-off is a deliberate choice, not a malfunction; say so instead of crying wolf.
    if out["by_source"].get(EV_SRC_STALE_OFF):
        out["warnings"].append(
            f"ev_point_in_time is OFF for {out['by_source'][EV_SRC_STALE_OFF]:,} rows — "
            "EV ratios are priced at the filing date, not the rebalance date")
        out["ok"] = False
    elif fresh < floor:
        out["warnings"].append(
            f"only {fresh:.2%} of rows have a rebalance-date EV (floor {floor:.0%})")
        out["ok"] = False
    if warn and out["warnings"]:
        import sys as _s
        for w in out["warnings"]:
            print(f"[ev_freshness] WARNING: {w}", file=_s.stderr, flush=True)
    return out


def run_backtest(provider, tickers, top_n=25, rebalance_days=63, horizon=63, lookback_years=18,
                 recency_halflife_days=1260, bucket="established") -> dict:
    ok, msg = provider.ready()
    if not ok:
        return {"ready": False, "provider": provider.name, "message": msg}
    panel = build_fundamental_panel(provider, tickers, rebalance_days=rebalance_days,
                                    lookback_years=lookback_years, horizon=horizon)
    if panel.empty or panel["date"].nunique() < 6:
        return {"ready": True, "provider": provider.name, "status": "insufficient history",
                "dates": 0 if panel.empty else int(panel["date"].nunique())}
    cols = [c for c in S.BUCKET_FACTORS[bucket] if c in panel.columns and panel[c].notna().any()]
    base = _base_weights(cols, bucket)
    opt = _weighted_optimize(panel, cols, base, halflife_days=recency_halflife_days)
    rec = opt.get("recommended_weights") or base
    return {"ready": True, "provider": provider.name, "survivorship_free": provider.survivorship_free,
            "dates": int(panel["date"].nunique()), "rows": int(len(panel)), "names": int(panel["ticker"].nunique()),
            "factors": cols, "default_weights": base, "optimized_weights": _full_weights(rec, bucket),
            "best_in_sample_weights": opt.get("best_in_sample_weights"), "candidates": opt.get("candidates"),
            "accepted": bool(opt.get("accepted")), "in_sample_ic": opt.get("in_sample_ic"),
            "out_sample_ic": opt.get("out_sample_ic"), "verdict": opt.get("verdict"),
            "backtest_default": _backtest(panel, cols, base, top_n, horizon),
            "backtest_optimized": _backtest(panel, cols, rec, top_n, horizon)}


def main(argv=None):
    """Local runner: point-in-time backtest → prints results vs the S&P and the
    paste-ready optimized starting weights.  Examples:
        python -m valuation.edge.fundamental_panel                 # uses EDGE_DATA_PROVIDER
        python -m valuation.edge.fundamental_panel --data-dir ./data/backtest   # offline local files
    """
    import argparse
    import json
    import sys
    from ..config import CONFIG
    from .data_providers import get_historical_provider, WRDSProvider
    from ..screener import universe as U

    # A Windows console negotiates UTF-8, but a REDIRECTED stdout (`> log.txt`, a pipe, a
    # scheduled task) falls back to cp1252 and the arrows/em-dashes we print raise
    # UnicodeEncodeError — killing a 40-minute run over pure cosmetics, and making the
    # .bat wrappers report "failed" on a run that actually succeeded.
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:                      # not a reconfigurable stream — fine
            pass

    ap = argparse.ArgumentParser(description="Fundamental point-in-time backtest (local).")
    ap.add_argument("--limit", type=int, default=CONFIG.backtest_universe_limit)
    ap.add_argument("--data-dir", default=None, help="use local exported files (WRDS layout) instead of the API")
    ap.add_argument("--json", default=None, help="also write the full result JSON here")
    ap.add_argument("--validate-institutional", action="store_true",
                    help="due-diligence the 13F signal alone across filing lags "
                         f"({'/'.join(str(x) for x in INST_LAG_GRID)}d)")
    args = ap.parse_args(argv)

    if args.data_dir:
        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
    else:
        prov = get_historical_provider(CONFIG)
    ok, msg = prov.ready()
    if not ok:
        print(f"Provider not ready: {msg}")
        return 1
    if hasattr(prov, "check"):                    # live key/subscription probe → clear error
        ok, msg = prov.check()
        print(msg)
        if not ok:
            return 1

    if args.validate_institutional:                         # standalone 13F due-diligence run
        lim = min(args.limit, 800)                           # the 13F edge lives in large caps
        tickers = prov.universe(limit=lim) or list(U.bundled_tickers())[:lim]
        _lags = INST_LAG_GRID
        print(f"Validating the institutional (13F) signal ALONE on the {len(tickers)} largest names, "
              f"lags {'/'.join(str(x) for x in _lags)}d ...", flush=True)
        vi = validate_institutional(prov, tickers, lags=_lags, lookback_years=CONFIG.backtest_lookback_years)
        _note = {15: "not yet filed - look-ahead", 45: "last filed quarter (Q-1)",
                 135: "one quarter staler (Q-2)", 225: "two quarters staler (Q-3)"}
        print("\n=== Standalone 13F signal, by assumed filing lag ===")
        print("    lag   dates   medIC    topDecile/yr   long-short/yr   LS t   monotonicity   DeflatedSharpe")
        _vf = (lambda x, p="+.1%": "n/a" if x is None else format(x, p))
        for lag in _lags:
            r = (vi.get("lags") or {}).get(str(lag)) or {}
            if r.get("status"):
                print(f"   {lag:>4}d  {r['status']}")
                continue
            print(f"   {lag:>4}d  {r.get('dates', 0):>5}   {_vf(r.get('median_ic'), '+.3f')}   "
                  f"{_vf(r.get('top_decile_alpha')):>10}   {_vf(r.get('long_short_ann')):>12}   "
                  f"{_vf(r.get('long_short_tstat'), '.2f'):>5}   {_vf(r.get('monotonicity'), '+.2f'):>10}   "
                  f"{_vf(r.get('deflated_sharpe'), '.0%')}   {_note.get(lag, '')}")
        print("\n   Read: STRONGER at 15d than 45d = the edge leans on filings that weren't public yet")
        print("   (look-ahead artifact). Peaks at 45d then decays through 135d -> 225d = a real,")
        print("   slowly-decaying signal. Flat across all four = noise. Deflated Sharpe > ~95% at")
        print("   a realistic (>=45d) lag is the bar for tradeable.")
        if args.json:
            with open(args.json, "w") as f:
                json.dump(vi, f, indent=2)
            print(f"\nFull results → {args.json}")
        return 0

    tickers = prov.universe(limit=args.limit) or list(U.bundled_tickers())[:args.limit]
    horizons = [int(x) for x in str(CONFIG.backtest_horizons).split(",") if x.strip()]
    print(f"Backtesting {len(tickers)} names via {prov.name} — horizons {horizons} …", flush=True)
    res = run_backtests(prov, tickers, horizons=horizons, rebalance_days=CONFIG.backtest_rebalance_days,
                        top_n=CONFIG.backtest_top_n, lookback_years=CONFIG.backtest_lookback_years,
                        recency_halflife_days=int(CONFIG.backtest_recency_halflife_years * 252))
    if not res.get("ready"):
        print(res.get("message"))
        return 1

    for H, r in sorted((res.get("horizons") or {}).items(), key=lambda kv: int(kv[0])):
        if r.get("status"):
            print(f"[{H}d] {r['status']}")
            continue
        bd, bo = r.get("backtest_default") or {}, r.get("backtest_optimized") or {}
        print(f"\n[{H}d] {r['names']} names · {r['dates']} dates")
        biw = r.get("best_in_sample_weights") or {}
        topw = ", ".join(f"{k} {v:.2f}" for k, v in sorted(biw.items(), key=lambda kv: -kv[1]) if v > 0)
        _fmt = (lambda x: "n/a" if x is None else f"{x:+.3f}")
        print(f"   optimizer searched {r.get('candidates', '?')} weightings; best in-sample = {topw or '(defaults)'}")
        print(f"     in-sample IC {_fmt(r.get('in_sample_ic'))} -> out-of-sample IC {_fmt(r.get('out_sample_ic'))}"
              f"  =>  {'ADOPTED (beat defaults OOS)' if r['accepted'] else 'REJECTED, kept defaults'}")

        def _line(lab, b):
            s = (f"   {lab}: {(b.get('cagr') or 0):+.1%}/yr  vs S&P {(b.get('bench_cagr') or 0):+.1%}"
                 f" (alpha {((b.get('cagr') or 0) - (b.get('bench_cagr') or 0)):+.1%}/yr, {b.get('years', '?')}y)")
            if b.get("ew_cagr") is not None:                 # fair, cap-neutral bar
                s += f"  ·  vs equal-wt {(b.get('ew_cagr') or 0):+.1%} (alpha {(b.get('ew_alpha') or 0):+.1%}/yr)"
            return s
        print(_line("default  ", bd))
        print(_line("optimized", bo))

    hu = res.get("hold_until_exit") or {}
    if hu.get("cagr") is not None:
        a = (hu.get("cagr") or 0) - (hu.get("bench_cagr") or 0)
        print(f"\n[HOLD until it drops out of favor]  (avg hold {hu.get('avg_hold_years', '?')}y, {hu.get('years', '?')}y span)")
        line = f"   strategy: {hu['cagr']:+.1%}/yr  vs S&P {(hu.get('bench_cagr') or 0):+.1%} (alpha {a:+.1%}/yr)"
        if hu.get("ew_cagr") is not None:
            line += f"  ·  vs equal-wt {(hu.get('ew_cagr') or 0):+.1%} (alpha {(hu.get('ew_alpha') or 0):+.1%}/yr)"
        print(line)
    elif hu.get("status"):
        print(f"\n[HOLD until it drops out of favor] {hu['status']}")

    cn = res.get("construction") or {}
    if cn and not cn.get("status"):
        nq = cn.get("n_quantiles", 10)
        wname = res.get("construction_weighting", "default")
        print(f"\n=== Portfolio construction — is the edge real & harvestable? ({nq} buckets, {cn.get('n_periods')} periods, {wname} weights) ===")
        dec = cn.get("decile_ann_return") or []
        cells = "  ".join(f"D{i + 1} {('n/a' if v is None else format(v, '+.0%'))}" for i, v in enumerate(dec))
        print(f"   Bucket return/yr (D1 = highest composite -> D{nq} = lowest):\n     {cells}")
        lt = cn.get("long_short_tstat")
        sig = "   <-- SIGNIFICANT market-neutral edge" if (lt is not None and abs(lt) >= 2) else "   (not significant)"
        print(f"   Long-short (D1 - D{nq}): {(cn.get('long_short_ann') or 0):+.1%}/yr   "
              f"t-stat {('n/a' if lt is None else f'{lt:.2f}')}   hit {cn.get('long_short_hit', 0):.0%}{sig}")
        print(f"   Long top-decile vs equal-weight: alpha {(cn.get('top_decile_alpha') or 0):+.1%}/yr   ·   "
              f"signal-weighted: {(cn.get('sw_top_decile_alpha') or 0):+.1%}/yr")
        mono = cn.get("monotonicity")
        print(f"   Monotonicity (bucket-rank -> return corr): {('n/a' if mono is None else f'{mono:+.2f}')}"
              f"   (want strongly NEGATIVE: better rank -> higher return)")
        cd = res.get("construction_default") or {}
        if cd and not cd.get("status"):                      # show the lift from the adopted weighting
            _t = (lambda x: "n/a" if x is None else f"{x:.2f}")
            print(f"   [lift vs default weights]  top-decile alpha {(cd.get('top_decile_alpha') or 0):+.1%} -> "
                  f"{(cn.get('top_decile_alpha') or 0):+.1%}/yr   ·   long-short t {_t(cd.get('long_short_tstat'))} -> "
                  f"{_t(cn.get('long_short_tstat'))}")
    elif cn.get("status"):
        print(f"\n=== Portfolio construction === {cn['status']}")

    rg = res.get("regime") or {}
    if rg and not rg.get("status"):
        print("\n=== Where the edge lives (by market-cap tier) ===")
        for lb, s in (rg.get("tiers") or {}).items():
            ic_v, ls_v = s.get("median_ic"), s.get("long_short_ann")
            print(f"   {lb:<6}: median IC {('n/a' if ic_v is None else f'{ic_v:+.3f}')}   "
                  f"long-short {('n/a' if ls_v is None else f'{ls_v:+.1%}/yr')}   ({s.get('n_periods', 0)} periods)")
    fu = res.get("factors_used")
    if fu:
        print(f"\n   themes with live data this run ({len(fu)}): {', '.join(fu)}")

    wf = res.get("walk_forward") or {}
    if wf and not wf.get("status"):
        print(f"\n=== Walk-forward validation (anchored + purged, {wf.get('n_folds', '?')} folds) ===")
        print("    Train on the past, test on the untouched NEXT block, roll forward. Every number below")
        print("    is OUT-OF-SAMPLE (median across folds). A multiple-testing haircut is applied so we")
        print("    can't be fooled by trying many configs. 'picked' = times it won on the train side.")
        w = wf.get("weights") or {}
        cs = w.get("candidates") or {}
        if cs:
            print("\n  Theme weighting  —  median OOS IC   [% folds positive]   picked:")
            for nm, s in sorted(cs.items(), key=lambda kv: (kv[1].get("median_oos_ic")
                                if kv[1].get("median_oos_ic") is not None else -9.0), reverse=True):
                mi, pf = s.get("median_oos_ic"), s.get("folds_positive")
                print(f"     {nm:<16} {('n/a' if mi is None else f'{mi:+.3f}'):>7}    "
                      f"[{('n/a' if pf is None else f'{pf:.0%}')}]     {s.get('selected', 0)}x")
            print(f"     -> {w.get('verdict')}")
        pr = wf.get("params") or {}
        if pr:
            print("\n  Trade parameters  —  median OOS alpha vs equal-weight   [% folds positive]   picked:")
            for pname, pdd in pr.items():
                print(f"   {pname}  (default {pdd.get('default')}):")
                for row in pdd.get("values", []):
                    ma, pf = row.get("median_oos_alpha"), row.get("folds_positive")
                    tag = "   <= recommend" if (pdd.get("adopt") and row["value"] == pdd.get("recommend")) else ""
                    print(f"      {str(row['value']):>6} : {('n/a' if ma is None else f'{ma:+.1%}'):>7}   "
                          f"[{('n/a' if pf is None else f'{pf:.0%}')}]   {row.get('selected', 0)}x{tag}")
                print(f"       -> {pdd.get('verdict')}")
    elif wf.get("status"):
        print(f"\n=== Walk-forward validation === {wf['status']}")

    cp = res.get("cpcv") or {}
    if cp and not cp.get("status"):
        pbo, dsr = cp.get("pbo"), cp.get("deflated_sharpe")
        print(f"\n=== Validation — Combinatorial Purged CV ({cp.get('n_paths')} paths) ===")
        print(f"   Probability of Backtest Overfitting (PBO): {('n/a' if pbo is None else f'{pbo:.0%}')}"
              f"   (lower is better; >50% = the selection is likely overfit)")
        print(f"   Deflated Sharpe Ratio: {('n/a' if dsr is None else f'{dsr:.0%}')}"
              f"   (prob the edge is real after correcting for #trials + non-normality; want >95%)")
        print(f"   -> {cp.get('verdict')}")
    elif cp.get("status"):
        print(f"\n=== Validation — CPCV === {cp['status']}")

    idp = res.get("institutional_dependence") or {}
    if idp and not idp.get("status"):
        wv, wi, wo = idp.get("institutional_weight"), (idp.get("with") or {}), (idp.get("without") or {})
        _p = (lambda x: "n/a" if x is None else f"{x:+.1%}")
        _t = (lambda x: "n/a" if x is None else f"{x:.2f}")
        print(f"\n=== Institutional (13F) dependence — weight {('n/a' if wv is None else f'{wv:.0%}')} ===")
        print(f"   with it   : top-decile alpha {_p(wi.get('top_decile_alpha'))}, long-short t {_t(wi.get('long_short_tstat'))}")
        print(f"   WITHOUT it: top-decile alpha {_p(wo.get('top_decile_alpha'))}, long-short t {_t(wo.get('long_short_tstat'))}"
              f"   (if the edge collapses here, it rests on lagged 13F data)")

    rwf = res.get("recommended_weights_full")
    ph = res.get("primary_horizon")
    h = (res.get("horizons") or {}).get(str(ph)) if ph else None
    if rwf:                                                  # the robust walk-forward adopted a weighting
        nm = res.get("recommended_weighting_name", "validation")
        print("\n=== Validation adopted a better weighting — paste into valuation/screener/settings.py, then git_push.bat ===")
        print(f"# '{nm}' beat the defaults out-of-sample and cleared the overfitting checks (CPCV / walk-forward verdicts above).")
        print("WEIGHTS_ESTABLISHED = " + json.dumps(rwf))
    elif h and h.get("accepted"):
        print("\n=== Paste into valuation/screener/settings.py, then commit + push ===")
        print("WEIGHTS_ESTABLISHED = " + json.dumps(h["optimized_weights"]))
    else:
        print("\nNo weighting beat the defaults out-of-sample (walk-forward or single-split) — keep the current weights.")
    # Canonical results files at the repo root, written on EVERY run and git-tracked, so the
    # current numbers travel out of a worktree to main for another agent to read. Derived
    # metrics only, never raw licensed rows. Never allowed to fail a completed backtest —
    # EXCEPT a schema failure (audit M6), which gets its own `except` below and exits
    # non-zero WITHOUT discarding any artifact the run already produced.
    _schema_failed = None
    try:
        import os as _os
        from .results_file import write as _write_results
        _cleanups = {
            "survivorship_mask": bool(getattr(prov, "delisted_map", None) and prov.delisted_map()),
            # AUDIT B14 — the boolean above only says the ACTIONS map is non-empty. This is
            # the mask's actual measured coverage, plus the count of names whose price
            # series ends early with NO delisting row to explain it.
            "survivorship_mask_coverage":
                LAST_PANEL_DIAGNOSTICS.get("survivorship_mask_coverage"),
            # AUDIT B6 / B22 / M6 — the window every block in this file was measured
            # over, plus the per-date cross-section sizes, so no two blocks can disagree
            # about their date range without it being visible.
            "panel_window": LAST_PANEL_DIAGNOSTICS.get("panel_window"),
            "pit_market_cap_from_daily": bool(getattr(prov, "daily_history", None)
                                              and prov.daily_history("AAPL")),
            "sf3_per_manager_inputs": bool(getattr(prov, "sf3_for", None) and prov.sf3_for("AAPL")),
        }
        # Per-signal IC for EVERY wired number, measured on the validated horizon so the
        # results file reports the same numbers the keep/reject decisions were made on.
        # run_backtests now measures it on the panel it already built, so there is nothing
        # to rebuild here; the fallback covers a caller that predates that.
        _psig = res.get("per_signal")
        if not _psig:
            try:
                _h = str((res.get("construction") or {}).get("horizon") or res.get("primary_horizon") or "")
                _hz = int(_h) if _h else 63
                _pan = build_fundamental_panel(prov, tickers, rebalance_days=63,
                                               lookback_years=CONFIG.backtest_lookback_years,
                                               horizon=_hz, keep_numbers=True)
                _psig = per_signal_ic(_pan)
            except Exception as _pe:
                print(f"[results] per-signal IC unavailable: {_pe}")
        # AUDIT B22 — check the schema BEFORE writing, and record any absence in the file
        # itself. A block that is missing must never look the same as a block that ran.
        _missing = missing_result_blocks(res)
        if _missing:
            res.setdefault("errors", []).append(
                "INCOMPLETE RUN — these required blocks are absent or empty: "
                + ", ".join(_missing) + " (audit B22)")
            print(f"[results] WARNING: {len(_missing)} required block(s) missing: "
                  f"{', '.join(_missing)}")
        _w = _write_results(res, universe_label=("full" if (args.limit or 0) >= 2000 else "subset"),
                            cleanups=_cleanups, per_signal=_psig)
        print(f"Canonical results  -> {_os.path.basename(_w['json'])} + "
              f"{_os.path.basename(_w['md'])} (repo root, tracked)")
    except _schema.PayloadSchemaError as _se:
        # AUDIT M6 — this blanket `except Exception` exists so a serialisation hiccup cannot
        # discard a completed 40-minute backtest, and that intent is right. But it would also
        # have SWALLOWED the schema guard, printing it as a warning nobody reads — a check
        # that cannot fail anything is not a check, which is the exact pattern M6 is about.
        # So the schema failure is caught SEPARATELY: the run keeps every artifact it has
        # already produced (both canonical files are on disk, and the --json dump below still
        # happens), and then main() exits NON-ZERO.
        _schema_failed = str(_se)
        print(f"[results] SCHEMA FAILURE (audit M6): {_se}")
    except Exception as _e:
        print(f"[results] could not write the canonical results files: {_e}")


    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"\nFull results → {args.json}")
    if _schema_failed:
        print("\nRUN FAILED: a computed field was dropped from the canonical results file.\n"
              "Nothing was lost — every artifact above was written. Carry the field in\n"
              "results_file.build_payload, or declare it in payload_schema.BLOCK_SPEC with\n"
              "a reason, then re-run.")
        return 2
    return 0


# AUDIT B22 / M6 — the blocks a COMPLETE run must contain. A missing block is now an error
# recorded in the results file rather than an absence nobody can distinguish from "not run".
RESULT_BLOCKS = (
    "construction", "regime", "institutional_dependence", "factors_used", "walk_forward",
    "cpcv", "hold_until_exit", "holdout_validation", "costs", "book_configs",
    "no_trade_band", "after_tax",
    "benchmarks",          # AUDIT R10 — a silently absent benchmark block would leave the
                           # uninvestable equal-weight figure standing alone again
)


def missing_result_blocks(res: dict) -> list:
    """Which required blocks are absent or empty. Used to fail a run LOUDLY (audit B22)."""
    out = []
    for k in RESULT_BLOCKS:
        v = res.get(k)
        if v is None or (isinstance(v, (dict, list)) and len(v) == 0):
            out.append(k)
    return out


def run_backtests(provider, tickers, horizons=(63, 252), rebalance_days=63, top_n=25,
                  lookback_years=18, recency_halflife_days=1260, bucket="established") -> dict:
    """Run the backtest at several holding horizons; the primary (adopted) one is the
    longest, matching a long-hold philosophy. Stable weights across horizons = trust."""
    ok, msg = provider.ready()
    if not ok:
        return {"ready": False, "provider": provider.name, "message": msg}
    out = {"ready": True, "provider": provider.name, "survivorship_free": provider.survivorship_free,
           "recency_halflife_years": round(recency_halflife_days / 252.0, 1), "horizons": {}}
    for H in horizons:
        rb = max(rebalance_days, int(H))          # rebalance ≥ horizon → NON-overlapping periods
        r = run_backtest(provider, tickers, top_n=top_n, rebalance_days=rb, horizon=int(H),
                         lookback_years=lookback_years, recency_halflife_days=recency_halflife_days, bucket=bucket)
        out["horizons"][str(int(H))] = r
    done = [h for h, r in out["horizons"].items() if r.get("optimized_weights")]
    out["primary_horizon"] = max(done, key=lambda x: int(x)) if done else None

    # Realistic 'hold until it drops out of favor' simulation (mirrors the live sell logic),
    # rather than fixed-calendar churn — winners compound, losers get sold when they fade.
    try:
        # keep_numbers=True: the per-signal IC and coverage diagnostics both need the
        # standardized per-number columns, and this is the SAME panel (63d, validated
        # horizon) they used to be rebuilt from — building it once instead of twice removes
        # a full duplicate panel build from every run.
        panel = build_fundamental_panel(provider, tickers, rebalance_days=63,
                                        lookback_years=lookback_years, horizon=63,
                                        keep_numbers=True)
        # Optional dump of the scored panel. Building it is the expensive part of a run
        # (~12 min); a follow-up study that only re-reads the stored z-columns should not
        # have to pay for it twice. Diagnostic only — nothing in the run reads it back.
        import os as _os
        import sys as _sy
        _pp = _os.environ.get("EDGE_PANEL_PICKLE")
        if _pp:
            try:
                panel.to_pickle(_pp)
                print(f"[panel] dumped {len(panel)} rows -> {_pp}", file=_sy.stderr, flush=True)
            except Exception as e:                       # a failed dump must not kill the run
                print(f"[panel] dump FAILED: {e}", file=_sy.stderr, flush=True)
        # Coverage guard runs BEFORE any validation, so an empty factor is reported even if
        # something downstream fails.
        # AUDIT B22 / X2 — the window and the rebalance grid this run used, carried in the
        # result dict itself. It reached the canonical file through `cleanups` but NOT the
        # --json dump, so a sweep that writes one JSON per configuration had no record of
        # which configuration produced it.
        out["panel_window"] = LAST_PANEL_DIAGNOSTICS.get("panel_window")
        out["signal_coverage"] = signal_coverage(panel)
        # Coverage says a factor is PRESENT; this says it is SANE. The currency bug filled
        # every column and was simply wrong, so coverage was blind to it.
        out["sanity_check"] = sanity_check(panel)
        # ...and this says the EV ratios are CURRENT. A rebuild that reverts to the filing's
        # stale value raises nothing and leaves coverage and sanity both perfectly happy.
        out["ev_freshness"] = ev_freshness(panel)
        out["per_signal"] = per_signal_ic(panel)
        # AUDIT R4 — the two bullets M1 did not deliver. See `multiple_testing_accounting`.
        out["multiple_testing"] = multiple_testing_accounting(
            out["per_signal"], (out.get("construction") or {}).get("long_short_tstat_nw"))
        out["per_theme"] = theme_ic(panel)      # the level keep/drop decisions operate at
        if not panel.empty and panel["date"].nunique() >= 6:
            cols = [c for c in S.BUCKET_FACTORS[bucket] if c in panel.columns and panel[c].notna().any()]
            base = _base_weights(cols, bucket)
            out["hold_until_exit"] = _backtest_hold(panel, cols, base, top_n=top_n, horizon=63)
            wf = walk_forward(panel, cols, base, top_n=top_n, horizon=63,
                              halflife_days=recency_halflife_days)   # walk-forward: trade params + weights
            out["walk_forward"] = wf
            cpcv = cpcv_validate(panel, cols, base, halflife_days=recency_halflife_days, horizon=63)
            out["cpcv"] = cpcv                               # CPCV + PBO + Deflated Sharpe (strongest test)
            # CPCV is the AUTHORITY for the weights. If it ran, respect its verdict (do NOT let the
            # weaker single-path walk-forward override a CPCV rejection). Only fall back to the
            # walk-forward when CPCV couldn't run at all.
            if not cpcv.get("status"):
                if cpcv.get("adopt"):
                    rec, adopted_w, rec_name = (cpcv.get("recommended_weights_cols") or base), True, cpcv.get("recommend")
                else:
                    rec, adopted_w, rec_name = base, False, "default"      # CPCV rejected → keep defaults
            elif (wf.get("weights") or {}).get("adopt"):
                rec, adopted_w, rec_name = ((wf.get("weights") or {}).get("recommended_weights_cols") or base), True, (wf.get("weights") or {}).get("recommend")
            else:
                rec, adopted_w, rec_name = base, False, "default"
            out["construction_weighting"] = (rec_name if adopted_w else "default")
            out["construction"] = quantile_backtest(panel, cols, rec, n_q=10, horizon=63)
            out["regime"] = regime_split(panel, cols, rec, n_tiers=3, horizon=63)           # where the edge lives
            out["benchmarks"] = benchmark_panel(panel, cols, rec, n_q=10, horizon=63)       # AUDIT R10
            out["institutional_dependence"] = institutional_dependence(panel, cols, rec, horizon=63)
            out["factors_used"] = cols                                                       # which themes had data
            # Held-out time split: does zeroing a theme still help on data that did NOT
            # inform the decision? The one check CPCV/DSR cannot provide.
            out["holdout_validation"] = holdout_theme_validate(panel, cols, horizon=63)
            # Tradeability. Every other number in this file is gross of costs; this is the
            # only block that says whether the edge survives being implemented.
            _cg = (0, 10, 25, 50, 100, 150, 200, 300, 500)
            out["costs"] = {
                "cost_model": "one-way bps by point-in-time market cap; see COST_BPS_BY_MKTCAP",
                "top_decile": {**(turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63) or {}),
                               **cost_breakeven_bps(panel, cols, rec, top_frac=0.1,
                                                    horizon=63, grid=_cg)},
                "top_25": {**(turnover_and_costs(panel, cols, rec, top_n=top_n, horizon=63) or {}),
                           **cost_breakeven_bps(panel, cols, rec, top_n=top_n,
                                                horizon=63, grid=_cg)}}
            # The two shipped book configs, measured on this run so settings.py's numbers
            # are never stale relative to the data.
            out["book_configs"] = {}
            for _nm, _cfg in (S.BOOK_CONFIGS or {}).items():
                _kw = {k: v for k, v in (("top_n", _cfg.get("top_n")),
                                         ("top_frac", _cfg.get("top_frac")),
                                         ("exit_frac", _cfg.get("exit_frac")),
                                         ("exit_mult", _cfg.get("exit_mult"))) if v}
                # Both are scored on THIS panel's horizon; the roth config's own 42d cadence
                # needs its own panel, so its numbers here are the 63d approximation and the
                # authoritative figures live in settings.BOOK_CONFIGS["roth"]["measured"].
                _c = turnover_and_costs(panel, cols, rec, horizon=63, **_kw) or {}
                _t = after_tax_backtest(panel, cols, rec, horizon=63, **_kw) or {}
                out["book_configs"][_nm] = {
                    "label": _cfg.get("label"),
                    "rebalance_days": _cfg.get("rebalance_days"),
                    "scored_at_horizon": 63,
                    "net_alpha": _c.get("net_alpha"), "net_sharpe": _c.get("net_sharpe"),
                    "net_max_drawdown": _c.get("net_max_drawdown"),
                    "annual_turnover": _c.get("annual_turnover"),
                    "after_tax_alpha": _t.get("after_tax_alpha"),
                    "after_tax_sharpe": _t.get("after_tax_sharpe")}

            # No-trade band sweep. Reported every run so the turnover/alpha tradeoff is a
            # standing number rather than a one-off study. exit_frac=None is the shipped
            # behaviour (sell the moment a name leaves the book).
            out["no_trade_band"] = {"enter_frac": 0.10, "widths": {}}
            for _xf in (None, 0.12, 0.15, 0.20, 0.25, 0.30):
                _c = turnover_and_costs(panel, cols, rec, top_frac=0.10, horizon=63,
                                        exit_frac=_xf) or {}
                _t = after_tax_backtest(panel, cols, rec, top_frac=0.10, horizon=63,
                                        exit_frac=_xf) or {}
                out["no_trade_band"]["widths"]["none" if _xf is None else f"{_xf:.2f}"] = {
                    "annual_turnover": _c.get("annual_turnover"),
                    "gross_alpha": _c.get("gross_alpha"),
                    "net_alpha": _c.get("net_alpha"),
                    "after_tax_alpha": _t.get("after_tax_alpha"),
                    "cost_drag_ann": _c.get("cost_drag_ann")}

            # AUDIT B21 — SECTOR CONCENTRATION CAPS, measured for the first time. `_sector_capped`
            # is fully implemented and `run_backtests` never passed `max_sector_w`, so it had
            # never once run. This is NOT the sector-neutral intervention that was tested and
            # rejected twice: neutralising SCORES by sector destroys cross-sector selection,
            # which is why it sold top-decile alpha. Capping WEIGHTS leaves the selection intact
            # and only bounds concentration.
            #
            # PRE-REGISTERED as a RISK intervention, on the same asymmetric logic as S10: adopt
            # only if drawdown improves materially for a small alpha give-up. It is NOT adopted
            # by anything here — this block measures it and ships the numbers.
            out["sector_caps"] = {"note": "measured, NOT adopted; risk intervention (audit B21)",
                                  "caps": {}}
            for _cap in (None, 0.25, 0.30, 0.40):
                _sc = turnover_and_costs(panel, cols, rec, top_frac=0.10, horizon=63,
                                         max_sector_w=_cap) or {}
                out["sector_caps"]["caps"]["none" if _cap is None else f"{_cap:.2f}"] = {
                    "gross_alpha": _sc.get("gross_alpha"),
                    "net_alpha": _sc.get("net_alpha"),
                    "net_max_drawdown": _sc.get("net_max_drawdown"),
                    "net_sharpe": _sc.get("net_sharpe"),
                    "annual_turnover": _sc.get("annual_turnover"),
                    "realised_one_way_bps": _sc.get("realised_one_way_bps")}

            # After-tax. ~250%/yr turnover means almost every gain is short-term in a TAXABLE
            # account, and that drag is several times the trading cost.
            out["after_tax"] = {
                "top_decile": after_tax_backtest(panel, cols, rec, top_frac=0.1, horizon=63),
                "top_25": after_tax_backtest(panel, cols, rec, top_n=top_n, horizon=63),
                "tax_advantaged_note": ("an IRA/401k pays NO drag and earns the net-of-cost "
                                        "figure in `costs` instead")}
            if adopted_w:
                out["construction_default"] = quantile_backtest(panel, cols, base, n_q=10, horizon=63)
                out["recommended_weights_full"] = _full_weights(rec, bucket)                # paste-ready weights
                out["recommended_weighting_name"] = rec_name
        else:
            out["hold_until_exit"] = {"status": "insufficient history"}
            out["construction"] = {"status": "insufficient history"}
            out["walk_forward"] = {"status": "insufficient history"}
            out["cpcv"] = {"status": "insufficient history"}
            out["regime"] = {"status": "insufficient history"}
    except Exception as e:
        # AUDIT B22 — this used to stamp FIVE keys. The same `try` also produces `costs`,
        # `holdout_validation`, `book_configs`, `no_trade_band`, `after_tax` and
        # `institutional_dependence`, so a failure partway through — inside `costs`, say —
        # discarded the four blocks after it WITH NO STATUS MARKER AT ALL. They were simply
        # absent from the JSON while `errors` stayed empty, and a reader (human or agent) saw a
        # clean file with four blocks missing and no signal that anything had gone wrong. Given
        # that this project's memory IS these files, that is a silent-corruption path into the
        # record. Every expected block is now stamped, and only if it is not already present.
        for _k in RESULT_BLOCKS:
            out.setdefault(_k, {"status": f"error: {e}"})
        out.setdefault("errors", []).append(f"diagnostics block failed: {type(e).__name__}: {e}")
    return out


if __name__ == "__main__":
    raise SystemExit(main())
