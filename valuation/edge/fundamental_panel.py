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


def _sf1_to_metrics(ticker, sf1, price, market_cap) -> dict:
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
    ni_usd = _to_usd(sf1, "netinccmnusd", ni, div)
    fcf_usd = _to_usd(sf1, None, fcf, div)        # no fcfusd column — convert
    is_foreign = abs(div - 1.0) > 1e-9

    return {
        "ticker": ticker, "sector": "", "price": price, "market_cap": mc,
        "revenue": rev, "net_income": ni, "operating_income": ebit, "fcf": fcf,
        "gross_profit": gp, "total_debt": debt, "total_equity": equity, "interest_expense": intexp,
        # VALUE ratios — USD numerator/denominator on both sides (P7).
        "book_to_price": (eq_usd / mc) if (eq_usd is not None and mc) else None,
        "earnings_yield": (ni_usd / mc) if (ni_usd is not None and mc) else None,
        "fcf_yield": (fcf_usd / mc) if (fcf_usd is not None and mc) else None,
        "ebit_ev": (ebit_usd / ev) if (ebit_usd is not None and ev) else None,
        "ev_sales": (ev / rev_usd) if (ev and rev_usd) else None,
        "ps": (mc / rev_usd) if (mc and rev_usd) else None,
        # SAME-CURRENCY ratios — local/local, already correct, deliberately untouched.
        "op_margin": (ebit / rev) if (ebit is not None and rev) else _f(sf1, "ebitmargin"),
        "gross_margin": (gp / rev) if (gp is not None and rev) else _f(sf1, "grossmargin"),
        "roic": roic, "roe": roe, "net_debt_to_ebitda": ndte,
        # beta is filled in by _price_extras (regression vs the benchmark); None here so a
        # row whose window is too short simply has no beta rather than a stale one.
        "revenue_growth": None, "beta": None,
        # Diagnostics for the P8 sanity layer — not scored.
        "_is_foreign": is_foreign, "_fx_divisor": div,
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
        if d is pd.NaT or d > hi or d < lo:
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
    return max(0.0, min(100.0, 50 + 40 * math.tanh(net / 5e6) + min(10, 2 * buys)))


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
    a = int(np.searchsorted(dts, lo, side="left"))
    b = int(np.searchsorted(dts, hi, side="right"))
    if b <= a:
        return None
    w = vals[a:b]
    net, buys = float(w.sum()), int((w > 0).sum())
    return max(0.0, min(100.0, 50 + 40 * math.tanh(net / 5e6) + min(10, 2 * buys)))


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
    a = int(np.searchsorted(dts, lo, side="right"))
    b = int(np.searchsorted(dts, hi, side="right"))
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


def build_fundamental_panel(provider, tickers, benchmark="SPY", rebalance_days=63,
                            lookback_years=6, horizon=63, inst_lag_days=45,
                            keep_numbers=False, sector_neutral=False) -> pd.DataFrame:
    """Point-in-time panel of the theme columns per (date, ticker).

    keep_numbers=True additionally persists each individual standardized number (z_*), so
    a diagnostic can measure one signal's standalone predictive power instead of only the
    theme it was folded into. Off by default — it widens the frame considerably.
    """
    TD = 252

    def series(t):
        d, c = provider.price_history(t, days=TD * lookback_years + horizon + 60)
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
            meta[t] = provider.ticker_meta(t) if hasattr(provider, "ticker_meta") else {}
    if not px:
        import sys
        print("[panel] no usable price series for any ticker in the export.", file=sys.stderr)
        return pd.DataFrame()

    frame = pd.DataFrame(px).sort_index().ffill()
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
    _masked = 0
    if _delisted:
        for t in frame.columns:
            dd = _delisted.get(str(t).upper())
            if dd:
                m = frame.index > pd.to_datetime(dd)
                if m.any():
                    frame.loc[m, t] = np.nan
                    _masked += 1
    cal = frame.index
    benchf = bench.reindex(cal).ffill()
    benchv = benchf.values.tolist()        # for the idiosyncratic-vol regression, computed once

    _n_dates = len(range(TD, len(cal) - horizon, rebalance_days))
    _prog(f"history loaded: {len(px)} usable tickers, {len(cal)} calendar days "
          f"-> scoring {_n_dates} rebalance dates")

    rows = []
    for _di, i in enumerate(range(TD, len(cal) - horizon, rebalance_days)):
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
            cl = closes.tolist()
            m.update(_price_factors(cl, i))
            m.update(_price_extras(cl, i, bench=benchv))       # reversal / MAX / idio-vol
            _yoy(m, hist.get(t, []), as_of, shares, _f(sf1, "revenue"), _f(sf1, "assets"),
                 cut1=_cut1, cut2=_cut2)                       # growth + investment
            _sf1_extras(m, sf1, hist.get(t, []), as_of, cut1=_cut1)   # F-Score / accruals / cash OP
            _ttm_quality(m, hist.get(t, []), as_of)            # roe_ttm / roic_ttm (P6.2)
            isc = _insider_score_at(insh.get(t), as_of)
            if isc is not None:
                m["insider_score"] = isc                          # → insider theme (now backtestable)
            ia = _inst_accum_at(inst.get(t), as_of, lag_days=inst_lag_days)
            if ia is not None:
                m["inst_accum"] = ia                              # → institutional theme
            ib = _inst_breadth_at(hold.get(t), as_of, lag_days=inst_lag_days)
            if ib is not None:
                m["inst_breadth"] = ib                            # → institutional (holder breadth)
            # SF3 per-manager detail. Exposed as factor INPUTS here; whether any of them
            # earns a place in the composite is for CPCV to decide (P4), so they are not
            # yet registered in NUMBER_THEME.
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
            if closes[i] > 0:
                end = closes[i + horizon]
                if end != end:                                  # NaN -> delisted mid-window
                    seg = closes[i + 1:i + horizon + 1]
                    valid = seg[~np.isnan(seg)] if len(seg) else seg
                    end = float(valid[-1]) if len(valid) else np.nan
                fwd[t] = (end / closes[i] - 1.0) if end == end else None
            else:
                fwd[t] = None
        if len(metrics) < 10:
            continue
        from ..screener.factors import build_frame
        _by_ticker = {m["ticker"]: m for m in metrics}
        fr = build_frame(metrics, sector_neutral=sector_neutral, residual_momentum=False)
        for t, r in fr.iterrows():
            fr_ret = fwd.get(t)
            if fr_ret is None or fr_ret != fr_ret:
                continue
            row = {"date": as_of, "ticker": t, "fwd_ret": float(fr_ret),
                   "bench_ret": (float(bret) if bret == bret else np.nan),
                   "market_cap": mktcap.get(t)}
            for theme in S.FACTORS_ALL:
                v = r.get(theme) if theme in fr.columns else None
                row[theme] = None if (v is None or pd.isna(v)) else float(v)
            if keep_numbers:
                for num in S.NUMBERS_ALL:
                    zc = "z_" + num
                    v = r.get(zc) if zc in fr.columns else None
                    row[zc] = None if (v is None or pd.isna(v)) else float(v)
                # Diagnostics for sanity_check: the subgroup label, the market-cap divergence,
                # and the RAW value ratios (the z-scores alone can't reveal an implausible
                # LEVEL, which is exactly what the currency bug produced).
                _src = _by_ticker.get(t) or {}
                row["is_foreign"] = bool(_src.get("_is_foreign"))
                row["fx_divisor"] = _src.get("_fx_divisor")
                row["mc_ratio"] = _src.get("_mc_ratio")
                for _rr in tuple(SANE_RANGES) + SANE_RANGE_EXEMPT:
                    v = _src.get(_rr)
                    row["raw_" + _rr] = None if v is None else float(v)
            rows.append(row)
    return pd.DataFrame(rows)


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
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
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
                   trailing_stop=None):
    """Event-driven backtest that mirrors the LIVE sell logic: BUY the top-N by composite,
    then HOLD each name until it falls out of the top `exit_rank` (a hysteresis band, so a
    still-good name that merely slips isn't churned) — subject to a minimum hold. Optional
    `trailing_stop` (e.g. 0.3) also sells if a name falls that far from its own peak since
    entry (a profit-lock / reversal catch). Holding periods are variable: a strong name
    compounds for years. 'Hold the gems, sell what's no longer worth holding', not churn."""
    from ..screener.cross_sectional import zscore
    exit_rank = exit_rank or (top_n * 2)
    dates = sorted(panel["date"].unique())
    by_date = {d: panel[panel["date"] == d] for d in dates}
    held, port, bench, ew, hold_lens = {}, [], [], [], []   # held[t] = [entry_i, cum_factor, peak_factor]
    for i, d in enumerate(dates):
        sub = by_date[d]
        tickers = sub["ticker"].values
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
        order = np.argsort(-comp)
        rank = {tickers[order[r]]: r + 1 for r in range(len(order))}
        fwd = {tickers[j]: sub["fwd_ret"].values[j] for j in range(len(tickers))}
        for t in list(held):                              # SELL: band drop-out (past min-hold) or stop
            entry_i, cum, peak = held[t]
            dd = (cum / peak - 1.0) if peak > 0 else 0.0
            stop_hit = (trailing_stop is not None) and (dd <= -trailing_stop)
            rank_out = (t not in rank or rank[t] > exit_rank) and (i - entry_i) >= min_hold
            if stop_hit or rank_out:
                hold_lens.append(i - entry_i)
                del held[t]
        for r in range(min(top_n, len(order))):           # BUY: new top-N
            held.setdefault(tickers[order[r]], [i, 1.0, 1.0])
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
            port.append(pr)
            bench.append(bm)
            ew.append(em if em == em else bm)
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
            "avg_hold_years": round(avg_hold, 1) if avg_hold else None, "exit_rank": exit_rank}


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
        present = ~np.isnan(Z)
        denom = (present * wv).sum(axis=1)
        denom[denom == 0] = np.nan
        return np.nansum(np.where(present, Z, 0.0) * wv, axis=1) / denom

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


def _trials_haircut(n_trials):
    """Multiple-testing penalty. Trying N configs inflates the best one by luck; the expected
    max of N standard-normal draws is ≈ sqrt(2·ln N). The winner must clear this × its standard
    error to be believed — this is what stops us cherry-picking a lucky fold."""
    return float(np.sqrt(2.0 * np.log(max(2, n_trials))))


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
        present = ~np.isnan(Z)
        denom = (present * wv).sum(axis=1)
        denom[denom == 0] = np.nan
        return np.nansum(np.where(present, Z, 0.0) * wv, axis=1) / denom

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


def quantile_backtest(panel, cols, weights, n_q=10, horizon=63):
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
    Guarded by test_monotonicity_sign_convention."""
    from ..screener.cross_sectional import zscore
    dates = sorted(panel["date"].unique())
    q_rets = [[] for _ in range(n_q)]
    ls, sw_long, ewb = [], [], []
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
        fwd = sub["fwd_ret"].values
        ok = np.isfinite(comp) & np.isfinite(fwd)
        comp, fwd = comp[ok], fwd[ok]
        if len(fwd) < n_q * 3:                              # need enough names for clean buckets
            continue
        order = np.argsort(-comp)                           # highest composite first
        buckets = np.array_split(order, n_q)
        for qi, b in enumerate(buckets):
            if len(b):
                q_rets[qi].append(float(np.mean(fwd[b])))
        ls.append(float(np.mean(fwd[buckets[0]]) - np.mean(fwd[buckets[-1]])))
        ewb.append(float(np.mean(fwd)))
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
    return {"n_periods": len(ls), "n_quantiles": n_q, "horizon": horizon,
            "decile_ann_return": decile, "equal_weight_ann": ew_ann,
            "long_short_ann": annmean(ls), "long_short_tstat": tstat(ls),
            "long_short_hit": float(np.mean([1.0 if x > 0 else 0.0 for x in ls])),
            "top_decile_alpha": (None if decile[0] is None or ew_ann is None else decile[0] - ew_ann),
            "sw_top_decile_ann": sw_ann,
            "sw_top_decile_alpha": (None if sw_ann is None or ew_ann is None else sw_ann - ew_ann),
            "monotonicity": (None if mono != mono else float(mono))}


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
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
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
    after correcting for (a) how many variants we tried and (b) non-normal returns. >~0.95 = credible."""
    r = np.asarray(strategy_rets, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 8 or r.std(ddof=1) == 0:
        return None
    sr = float(r.mean() / r.std(ddof=1))                     # per-period Sharpe
    m = r - r.mean()
    s = r.std(ddof=0)
    skew = float((m ** 3).mean() / s ** 3)
    kurt = float((m ** 4).mean() / s ** 4)                   # non-excess kurtosis
    trials = [x for x in all_trial_sr if x is not None]
    N = max(2, len(trials))
    var_sr = float(np.var(trials, ddof=1)) if len(trials) > 1 else 1.0 / n
    emc = 0.5772156649015329                                 # Euler-Mascheroni
    sr0 = (var_sr ** 0.5) * ((1 - emc) * _nppf(1 - 1.0 / N) + emc * _nppf(1 - 1.0 / (N * np.e)))
    denom = (1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2)
    if denom <= 0:
        return None
    z = (sr - sr0) * ((n - 1) ** 0.5) / (denom ** 0.5)
    return float(_ncdf(z))


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
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
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
    if best is not None and dflt is not None:
        arr = oos[best]
        se = (float(np.std(arr)) / len(arr) ** 0.5) if len(arr) > 1 else None
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
    dsr = _deflated_sharpe(_strategy_returns(panel, cols, all_w[recname]), trial_sr)
    return {"n_paths": len(paths), "pbo": pbo, "deflated_sharpe": dsr, "recommend": recname, "adopt": adopt,
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
        psr = _deflated_sharpe(strat, [float(rr.mean() / rr.std(ddof=1)) if len(rr) > 2 and rr.std(ddof=1) > 0 else None])
        out["lags"][str(lag)] = {
            "dates": int(panel["date"].nunique()), "names": int(panel["ticker"].nunique()),
            "median_ic": (float(np.median(ics)) if ics else None),
            "top_decile_alpha": q.get("top_decile_alpha"), "long_short_ann": q.get("long_short_ann"),
            "long_short_tstat": q.get("long_short_tstat"), "monotonicity": q.get("monotonicity"),
            "deflated_sharpe": psr}
    return out


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
        return {"sharpe": None, "max_drawdown": None, "vol_ann": None, "n": int(len(a))}
    sd = float(a.std(ddof=1))
    mu = float(a.mean()) - rf / per_year
    sharpe = (mu / sd) * (per_year ** 0.5) if sd > 0 else None
    eq = np.cumprod(1.0 + a)
    peak = np.maximum.accumulate(eq)
    dd = float((eq / peak - 1.0).min())
    return {"sharpe": sharpe, "max_drawdown": dd,
            "vol_ann": sd * (per_year ** 0.5), "n": int(len(a))}


def _band_select(comp, tickers, held, n_target, exit_rank):
    """Which names to hold, given a NO-TRADE BAND (hysteresis).

    Enter on the top `n_target`; keep an existing holding until it falls past `exit_rank`.
    Without a band a name is sold the instant it slips one place out of the book, and the
    round-trip costs and — far more expensively — realizes a short-term gain. The band lets a
    still-good name drift instead of churning.

    Book SIZE is held at `n_target` so the comparison across widths is like-for-like: survivors
    are kept best-first, then the remaining slots go to the highest-ranked names not held. With
    `exit_rank == n_target` this reduces exactly to plain top-N, which is what makes the
    no-band case a true baseline rather than a different code path.
    """
    order = np.argsort(-comp)
    rank = {tickers[order[r]]: r for r in range(len(order))}
    keep = sorted((t for t in held if rank.get(t, 1 << 30) < exit_rank), key=lambda t: rank[t])
    out = keep[:n_target]
    if len(out) < n_target:
        chosen = set(out)
        for r in range(len(order)):
            t = tickers[order[r]]
            if t not in chosen:
                out.append(t)
                chosen.add(t)
                if len(out) >= n_target:
                    break
    return out


def turnover_and_costs(panel, cols, weights, top_frac=0.1, top_n=None, horizon=63,
                       flat_bps=None, exit_frac=None, exit_mult=None) -> dict:
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
    for d in dates:
        sub = panel[panel["date"] == d]
        if len(sub) < 20:
            continue
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
        k = int(top_n) if top_n else max(1, int(len(sub) * top_frac))
        _all_t = sub["ticker"].values
        # Band as a universe FRACTION (exit_frac) or as a multiple of the book size
        # (exit_mult) — the latter is the only one meaningful for a fixed-N book.
        _xr = k
        if exit_mult is not None:
            _xr = max(k, int(round(k * exit_mult)))
        elif exit_frac is not None:
            _xr = max(k, int(len(sub) * exit_frac))
        _sel = _band_select(comp, _all_t, set(prev_w), k, _xr)
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
                       exit_mult=None) -> dict:
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
        comp = np.zeros(len(sub))
        for c in cols:
            z = zscore(sub[c]).values
            comp = comp + np.where(np.isnan(z), 0.0, z) * weights.get(c, 0.0)
        k = int(top_n) if top_n else max(1, int(len(sub) * top_frac))
        _all_t = sub["ticker"].values
        # Band as a universe FRACTION (exit_frac) or as a multiple of the book size
        # (exit_mult) — the latter is the only one meaningful for a fixed-N book.
        _xr = k
        if exit_mult is not None:
            _xr = max(k, int(round(k * exit_mult)))
        elif exit_frac is not None:
            _xr = max(k, int(len(sub) * exit_frac))
        _sel = _band_select(comp, _all_t, set(lots), k, _xr)
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
                           min_tstat_gain=MIN_HOLDOUT_TSTAT_GAIN) -> dict:
    """Held-out comparison of two PANEL CONSTRUCTIONS (not two weightings).

    holdout_theme_validate answers "should this theme carry weight". Some changes are not a
    weight at all — sector-neutral scoring rebuilds every z-score — so they need the same
    discipline in a different shape: split by time, embargo the boundary, and require B to
    beat A by the SAME pre-committed margin (MIN_HOLDOUT_*) in BOTH split directions.

    Both panels must cover the same dates; only the construction differs.
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
                               n_q=n_q, horizon=horizon) or {}
        rb = quantile_backtest(panel_b[panel_b["date"].isin(ds)], cols, w,
                               n_q=n_q, horizon=horizon) or {}
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
    """Time-split confirmation that ZEROING a theme helps on data not used to decide it.

    CPCV and the Deflated Sharpe correct for the trials inside the *weight search*. Neither
    corrects for a human looking at a theme's IC on the whole panel, deciding to drop it, and
    then measuring the improvement on that same panel — which is how `low_risk` was zeroed.
    This is the missing test, and it is permanent rather than a one-off script so the claim
    keeps being re-checked on every run.

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

    Weights are equal across `cols` rather than read from settings, so the comparison is
    "this theme in vs out", not "current live config vs something else".
    """
    out = {"rule": "median IC <= 0 on the decide half",
           "metric": "long_short_tstat and top_decile_alpha, measured on the held-out half",
           "min_alpha_gain": min_alpha_gain, "min_tstat_gain": min_tstat_gain,
           "splits": {}, "verdicts": {}}
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
# `ev_sales` and `ps` are deliberately NOT range-checked: their tails are driven by
# near-zero-revenue companies (a real |max| of 2.9M on good data), negative EV is legitimate,
# and the band flagged identical shares before and after the fix — a pure no-op. The SUBGROUP
# check below is what covers them.
SANE_RANGES = {
    "book_to_price": (-50.0, 50.0),
    "earnings_yield": (-10.0, 10.0),   # quarterly earnings / market cap
    "fcf_yield": (-10.0, 10.0),
    "ebit_ev": (-25.0, 25.0),
}
# Ratios measured but intentionally exempt from the range check (see above).
SANE_RANGE_EXEMPT = ("ev_sales", "ps")
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

    # ---- 2. subgroup pegging ----
    sub = {}
    if "is_foreign" in panel.columns:
        flag = panel["is_foreign"].fillna(False).astype(bool)
        n_for = int(flag.sum())
        sub["foreign"] = {"n_rows": n_for, "share_of_rows": n_for / n}
        if n_for and n_for < len(panel):
            per_factor = {}
            for name in (list(ranges) + list(SANE_RANGE_EXEMPT)
                         + [c[2:] for c in panel.columns if c.startswith("z_")]):
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
    # metrics only, never raw licensed rows. Never allowed to fail a completed backtest.
    try:
        import os as _os
        from .results_file import write as _write_results
        _cleanups = {
            "survivorship_mask": bool(getattr(prov, "delisted_map", None) and prov.delisted_map()),
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
        _w = _write_results(res, universe_label=("full" if (args.limit or 0) >= 2000 else "subset"),
                            cleanups=_cleanups, per_signal=_psig)
        print(f"Canonical results  -> {_os.path.basename(_w['json'])} + "
              f"{_os.path.basename(_w['md'])} (repo root, tracked)")
    except Exception as _e:
        print(f"[results] could not write the canonical results files: {_e}")


    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"\nFull results → {args.json}")
    return 0


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
        # Coverage guard runs BEFORE any validation, so an empty factor is reported even if
        # something downstream fails.
        out["signal_coverage"] = signal_coverage(panel)
        # Coverage says a factor is PRESENT; this says it is SANE. The currency bug filled
        # every column and was simply wrong, so coverage was blind to it.
        out["sanity_check"] = sanity_check(panel)
        out["per_signal"] = per_signal_ic(panel)
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
        out["hold_until_exit"] = {"status": f"error: {e}"}
        out["construction"] = {"status": f"error: {e}"}
        out["walk_forward"] = {"status": f"error: {e}"}
        out["cpcv"] = {"status": f"error: {e}"}
        out["regime"] = {"status": f"error: {e}"}
    return out


if __name__ == "__main__":
    raise SystemExit(main())
