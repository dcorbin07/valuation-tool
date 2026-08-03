"""
OPTIONS_DEEP_RESEARCH thread #2 — the CROSS-SECTION of option returns.

PRE-SPECIFIED. Everything above the "RESULT" banner, including the SIGN of every hypothesis, was
written and committed BEFORE any sort was run. Directions matter more here than anywhere else in
this project: a cross-sectional sort has two ends, and a study that picks which end to go long
after seeing the numbers has a 50% hit rate by construction.

--------------------------------------------------------------------------------------------
WHY THIS THREAD, AND WHY IT IS DIFFERENT FROM EVERYTHING BEFORE IT.

Every options study this project has run asks the same question: is the scream-buy alert a good
time to buy a call? The answer is no — 22b showed the alert loses to a random entry day, 22c
showed that is stable and unfixable across fifteen corrections, and thread #1 showed the exit
cannot rescue it either.

This thread asks a question the project has never asked: **are some names' options systematically
cheap or rich relative to others, regardless of any timing signal?** That is the part of the
options literature with actual out-of-sample replication behind it, and none of it has been tested
on this cache. It needs no entry signal, so nothing it finds can be contaminated by the dead one.

--------------------------------------------------------------------------------------------
THE INSTRUMENT: A ONE-MONTH ATM STRADDLE, HELD TO EXPIRY.

At each month end, for each name, buy the call AND the put at the strike nearest spot on the
expiry closest to TARGET_DTE days out, and hold to expiry. Both legs are bought at the ASK. The
position settles at INTRINSIC against the underlying's as-traded close at expiry.

Three deliberate choices, each with its cost stated:

  1. A STRADDLE, NOT CAO-HAN'S DELTA-HEDGED CALL. Their instrument rebalances a delta hedge daily,
     which would need an implied-vol solve per position per day — roughly a million solves across
     this panel. A straddle is delta-neutral AT INCEPTION and is the canonical variance-risk-premium
     instrument, but it is NOT delta-neutral thereafter: it picks up gamma and drift as the
     underlying moves. So this is an approximation of Cao-Han, and a faithful replication of
     Goyal-Saretto, and it is labelled that way rather than sold as both.
  2. HELD TO EXPIRY, SETTLED AT INTRINSIC. Thread #1 found that this project's simulator marks a
     position that outlives its contract's last usable quote at THAT STALE QUOTE — a price from
     before the final decay, higher than the truth in 94.7% of cases. Holding to expiry and
     settling against the underlying sidesteps that entirely: there is no mark, only a payoff.
  3. BOUGHT AT THE ASK, BOTH LEGS. A straddle crosses two spreads at entry, so this is the most
     spread-punished instrument in the project. That is the honest way to run it — a cross-section
     that only exists at mid prices is not a finding.

--------------------------------------------------------------------------------------------
THE SIX CHARACTERISTICS, AND THE DIRECTION EACH IS PREDICTED TO GO. FIXED IN ADVANCE.

Every one is measured STRICTLY BEFORE the formation date. "Long Q1" always means the quintile the
literature says should earn the option BUYER more.

  iv_rv        log(ATM IV at the traded tenor / trailing 252-day realised vol).
               GOYAL-SARETTO (2009): options are rich where IV stands high above realised vol, and
               those names' option returns are LOWER. Long Q1 = the cheapest fifth.
  idio_vol     stdev of residuals from a 252-day regression of daily returns on the market proxy.
               CAO-HAN (2013): delta-hedged option returns FALL with idiosyncratic vol.
               Long Q1 = lowest idio-vol.
  idio_skew    skewness of those same residuals.
               BOYER-VORKINK: lottery-like, positively skewed names attract buyers and their
               options are overpriced. Long Q1 = least positively skewed.
  vol_of_vol   stdev of daily log changes in the name's own ATM IV over the past 63 sessions.
               Vol-of-vol is a priced risk; options on it carry a premium, so buyers earn LESS.
               Long Q1 = steadiest vol.
  smile_slope  25-delta put IV minus 25-delta call IV at the traded expiry.
               A steep put skew is the market paying up for protection. Long Q1 = flattest skew.
               A WEAKER PRIOR than the four above, and flagged as such.
  illiq        mean relative bid-ask spread of the two legs at formation.
               MECHANICAL, NOT A HYPOTHESIS. Returns here are measured net of the spread, so a
               wide-spread name must earn less by construction. It is included as a CONTROL — if
               it does not sort, the panel is not measuring what it thinks it is — and it is
               counted in the multiplicity like everything else. It is never a discovery.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE. A verdict is one of ADOPT / SUGGESTIVE / REJECT.

  S1  A CHARACTERISTIC IS ADOPTED only if ALL hold, net of spread, at aggression 1.0:
        (a) the LONG-ONLY excess return of Q1 over the equal-weighted all-names straddle is
            positive with t >= MIN_T. Long-only because the long-short leg is not investable —
            see S4;
        (b) it holds in BOTH held-out halves (2016-2020, 2021-2025);
        (c) the quintile spread is MONOTONE in the predicted direction, measured by a rank
            correlation across the five quintile means of at least MIN_MONOTONE in absolute value.
            A characteristic whose Q1 and Q5 differ while Q2-Q4 are noise has not sorted anything;
        (d) at least MIN_MONTHS formation dates and MIN_NAMES_PER_DATE names per date;
        (e) it survives BH-FDR at FDR_Q across all six characteristics.

  S2  DIRECTION IS FIXED IN ADVANCE. A characteristic that sorts strongly in the OPPOSITE
      direction to its published sign is reported as a CONTRADICTION of the literature, not
      quietly re-signed into a win. This is the single most important rule in the file.

  S3  MULTIPLICITY IS PAID FOR: Deflated Sharpe at n_trials = 6; BH-FDR across the six; and PBO by
      CSCV over the characteristic grid, which must come in under MAX_PBO.

  S4  THE LONG-SHORT IS A RESEARCH STATISTIC, NOT A STRATEGY, AND IS LABELLED SO EVERY TIME IT
      APPEARS. Its short leg is a naked short straddle — unlimited risk, not permitted in Don's
      account, and explicitly excluded by the mandate's guardrail ("no naked options in an IRA,
      defined risk only for anything short-vol"). The investable read is always the long-only one.

  S5  THE HEADLINE IS NET OF SPREAD at aggression 1.0, with both legs bought at the ask. A mid-fill
      version is computed as a diagnostic of how much of any result is spread, and never reported
      as the result.

Expect rejection. A one-month ATM straddle bought at the ask is a brutally expensive instrument —
the average straddle here pays two full spreads on entry — and the published cross-sectional
results are mostly gross of transaction costs or measured on delta-hedged positions with far
smaller effective costs. A finding of "the published sorts do not survive retail spreads on this
universe" is a completely valid outcome and is the one to expect.

--------------------------------------------------------------------------------------------
WHAT THIS CANNOT SEE.

  * NO SPY. The Sharadar equity export does not carry ETFs, so the market proxy for the
    idiosyncratic-vol and idiosyncratic-skew regressions is the EQUAL-WEIGHTED daily return of
    this universe itself. That is a universe-specific factor, not the market, and it will absorb
    slightly more common variation than a true market index would — which biases idio_vol and
    idio_skew toward being SMALLER and noisier, not larger. Recorded rather than papered over.
  * VOL-OF-VOL USES THE 60-DTE ATM IV SERIES built for 22c, while the traded instrument is ~30
    DTE. Vol-of-vol is a persistent, slow-moving property, so the tenor mismatch is second-order,
    but it is a mismatch.
  * DAILY DATA ONLY. Straddles are formed on month-end closes; no intramonth rebalancing, no
    early close, no early exercise (long options only, so exercise never binds against us).
  * THE UNIVERSE IS THE MINER'S CACHE: chosen by TODAY's liquidity and already screened for
    spread. Both biases run toward any edge surviving, and neither can be removed here.
  * NO SHORTING COSTS OR MARGIN. Another reason the long-short is a research statistic only.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from typing import Optional

from . import options_fill as F
from . import options_universe as U
from .options_autopsy import FDR_Q, bh_fdr, deflated_sharpe
from .options_exitlab import pbo_cscv_policies, MAX_PBO
from .options_signals_v2 import LATE_START

# ---- window ---------------------------------------------------------------------------------
FORMATION_START = "2016-02-01"
FORMATION_END = "2025-10-31"
CACHE_END = "2025-12-31"

# ---- the instrument -------------------------------------------------------------------------
TARGET_DTE = 30
DTE_BAND = (21, 45)
MONEYNESS_BAND = (0.90, 1.10)      # the ATM strike must genuinely be near the money

# ---- characteristic windows -------------------------------------------------------------------
RV_WINDOW = 252
IDIO_WINDOW = 252
VOV_WINDOW = 63
MIN_IDIO_OBS = 200

# ---- the gate ---------------------------------------------------------------------------------
N_QUINTILES = 5
MIN_NAMES_PER_DATE = 20
MIN_MONTHS = 60
MIN_T = 2.0
MIN_MONOTONE = 0.60                # |Spearman| of quintile index vs quintile mean return

# The published sign of each characteristic: +1 means "HIGH values predict LOWER option returns",
# which is the direction every one of these is claimed in. Q1 (lowest) is therefore always the
# quintile the buyer wants. Fixed here so no result can be re-signed after the fact (S2).
CHARACTERISTICS = {
    "iv_rv": {"sign": +1, "source": "Goyal-Saretto 2009", "hypothesis": True},
    "idio_vol": {"sign": +1, "source": "Cao-Han 2013", "hypothesis": True},
    "idio_skew": {"sign": +1, "source": "Boyer-Vorkink", "hypothesis": True},
    "vol_of_vol": {"sign": +1, "source": "vol-of-vol risk premium", "hypothesis": True},
    "smile_slope": {"sign": +1, "source": "put-skew richness (weak prior)", "hypothesis": True},
    "illiq": {"sign": +1, "source": "MECHANICAL control, never a discovery", "hypothesis": False},
}
CHAR_NAMES = tuple(CHARACTERISTICS)

OUT_DIR = os.path.join("data", "options_xsection")


def _log(m):
    print(f"[optxs] {m}", flush=True)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def _mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def _stdev(v):
    v = [x for x in v if x is not None]
    if len(v) < 2:
        return None
    m = sum(v) / len(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def _median(v):
    v = sorted(x for x in v if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def _spearman(xs, ys) -> Optional[float]:
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 3:
        return None

    def rank(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0.0] * len(vals)
        for pos, i in enumerate(order):
            r[i] = float(pos)
        return r

    rx, ry = rank([p[0] for p in pairs]), rank([p[1] for p in pairs])
    n = len(rx)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return (num / den) if den else None


# ================================ formation dates ==========================================
def month_end_dates(bars: dict, start: str = FORMATION_START,
                    end: str = FORMATION_END) -> list:
    """The last trading day of each month inside the window, from a name's own bar calendar."""
    out = {}
    for d in bars["date"]:
        if start <= d <= end:
            out[d[:7]] = d
    return [out[k] for k in sorted(out)]


# ================================ the straddle =============================================
def pick_straddle(chain, spot: float, as_of: dt.date, target_dte: int = TARGET_DTE):
    """The ATM call and put on the expiry nearest `target_dte`. None if nothing is tradable.

    Both legs must be at the SAME strike and the SAME expiry — otherwise it is not a straddle and
    its delta-neutrality at inception, which is the whole point of the instrument, is gone.
    """
    import pandas as pd

    if chain is None or len(chain) == 0 or not spot or spot <= 0:
        return None
    exp = pd.to_datetime(chain["expiration"]).dt.date
    future = sorted({e for e in exp if e > as_of
                     and DTE_BAND[0] <= (e - as_of).days <= DTE_BAND[1]})
    if not future:
        return None
    tgt = min(future, key=lambda e: abs((e - as_of).days - target_dte))
    f = chain[exp == tgt].copy()
    right = f["right"].astype(str).str[0].str.upper()
    calls, puts = f[right == "C"], f[right == "P"]
    if not len(calls) or not len(puts):
        return None
    strikes = sorted(set(calls["strike"].astype(float)) & set(puts["strike"].astype(float)))
    strikes = [k for k in strikes
               if MONEYNESS_BAND[0] <= k / spot <= MONEYNESS_BAND[1]]
    if not strikes:
        return None
    k = min(strikes, key=lambda s: abs(s - spot))
    c = calls[calls["strike"].astype(float) == k].iloc[0]
    p = puts[puts["strike"].astype(float) == k].iloc[0]
    cq = F.Quote(bid=c.get("bid"), ask=c.get("ask"), oi=c.get("open_interest"),
                 volume=c.get("volume"))
    pq = F.Quote(bid=p.get("bid"), ask=p.get("ask"), oi=p.get("open_interest"),
                 volume=p.get("volume"))
    if F.quote_reject_reason(cq) or F.quote_reject_reason(pq):
        return None
    return {"expiry": tgt, "strike": float(k), "dte": (tgt - as_of).days,
            "call": cq, "put": pq}


def straddle_return(strad: dict, settle_underlying: Optional[float],
                    aggression: float = 1.0) -> Optional[dict]:
    """Buy both legs at the ask, hold to expiry, settle at intrinsic. Net of spread + commission.

    Uses `options_fill.round_trip` per leg so the cost model is the project's, not a private one.
    """
    if settle_underlying is None:
        return None
    legs = {}
    cost = 0.0
    pnl = 0.0
    for name, q, right in (("call", strad["call"], "C"), ("put", strad["put"], "P")):
        t = F.round_trip(q, None, right=right, strike=strad["strike"],
                         exit_underlying=settle_underlying, aggression=aggression,
                         expired=True)
        if not t.get("ok"):
            return None
        legs[name] = t
        cost += t["entry_fill"] * F.CONTRACT_MULTIPLIER
        pnl += t["net_pnl"]
    if cost <= 0:
        return None
    return {"entry_cost": cost, "net_pnl": pnl, "return_pct": pnl / cost,
            "strike": strad["strike"], "dte": strad["dte"],
            "expiry": strad["expiry"].isoformat(),
            "call_entry": legs["call"]["entry_fill"], "put_entry": legs["put"]["entry_fill"],
            "spread_pct": _mean([strad["call"].spread_pct, strad["put"].spread_pct])}


# ================================ characteristics ==========================================
def atm_iv_at(chain, spot: float, as_of: dt.date, expiry: dt.date) -> Optional[float]:
    """ATM call IV on the TRADED expiry — the tenor whose richness the sort is about."""
    import pandas as pd

    from . import blackscholes as BS

    exp = pd.to_datetime(chain["expiration"]).dt.date
    f = chain[(exp == expiry) & (chain["right"].astype(str).str[0].str.upper() == "C")].copy()
    if not len(f):
        return None
    f["_d"] = (f["strike"].astype(float) - float(spot)).abs()
    T = (expiry - as_of).days / 365.0
    if T <= 0:
        return None
    r = BS.risk_free_rate(as_of)
    for _, row in f.sort_values("_d").head(4).iterrows():
        bid, ask = _f(row.get("bid")), _f(row.get("ask"))
        if bid is None or ask is None or ask <= 0 or ask < bid:
            continue
        v = BS.implied_vol((bid + ask) / 2.0, float(spot), float(row["strike"]), T, r, "C")
        if v and 0.01 < float(v) < 5.0:
            return float(v)
    return None


def smile_slope_at(chain, spot: float, as_of: dt.date, expiry: dt.date) -> Optional[float]:
    """25-delta put IV minus 25-delta call IV on the traded expiry."""
    import pandas as pd

    from . import blackscholes as BS
    from .options_signals_v2 import _iv_at_delta

    exp = pd.to_datetime(chain["expiration"]).dt.date
    sub = chain[exp == expiry]
    if not len(sub):
        return None
    enr = BS.enrich_chain(sub, spot, as_of)
    if enr is None or len(enr) == 0:
        return None
    pv = _iv_at_delta(enr, 0.25, "P")
    cv = _iv_at_delta(enr, 0.25, "C")
    if pv is None or cv is None:
        return None
    return float(pv) - float(cv)


def realized_vol(closes, window: int = RV_WINDOW) -> Optional[float]:
    px = [c for c in closes[-(window + 1):] if c and c > 0]
    if len(px) < window // 2:
        return None
    rets = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    sd = _stdev(rets)
    return sd * math.sqrt(252.0) if sd else None


def daily_returns(bars: dict, as_of: str, window: int) -> list:
    """(date, simple return) strictly up to and including `as_of`, from ADJUSTED closes."""
    ds, cs = bars["date"], bars["close"]
    hi = -1
    for i, d in enumerate(ds):
        if d <= as_of:
            hi = i
        else:
            break
    if hi < 2:
        return []
    lo = max(1, hi - window + 1)
    out = []
    for i in range(lo, hi + 1):
        a, b = cs[i - 1], cs[i]
        if a and b and a > 0:
            out.append((ds[i], b / a - 1.0))
    return out


def idio_moments(rets: list, market: dict) -> dict:
    """Residual vol and skew from a one-factor regression on the market proxy.

    The proxy is the equal-weighted return of this universe, because the Sharadar equity export
    carries no ETFs. It absorbs slightly MORE common variation than a true index would, so these
    residual moments are if anything smaller and noisier than the published versions.
    """
    pairs = [(r, market[d]) for d, r in rets if d in market]
    if len(pairs) < MIN_IDIO_OBS:
        return {}
    ys = [p[0] for p in pairs]
    xs = [p[1] for p in pairs]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    var = sum((x - mx) ** 2 for x in xs)
    if var <= 0:
        return {}
    beta = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / var
    alpha = my - beta * mx
    res = [y - (alpha + beta * x) for x, y in zip(xs, ys)]
    sd = _stdev(res)
    if not sd or sd <= 0:
        return {}
    m3 = sum((r - _mean(res)) ** 3 for r in res) / n
    return {"idio_vol": sd * math.sqrt(252.0), "idio_skew": m3 / (sd ** 3), "beta": beta}


def vol_of_vol(iv_series: dict, dates: list, as_of: str,
               window: int = VOV_WINDOW) -> Optional[float]:
    """Stdev of daily LOG CHANGES in the name's own ATM IV, strictly before `as_of`."""
    prior = [(d, iv_series[d]) for d in dates if d < as_of and d in iv_series][-(window + 1):]
    ch = [math.log(prior[i][1] / prior[i - 1][1])
          for i in range(1, len(prior))
          if prior[i][1] and prior[i - 1][1] and prior[i][1] > 0 and prior[i - 1][1] > 0]
    if len(ch) < window // 2:
        return None
    return _stdev(ch)


# ================================ the panel ================================================
def build_market(all_bars: dict, start: str = FORMATION_START) -> dict:
    """{date: equal-weighted simple return across the universe}. The factor for idio moments."""
    acc = {}
    for bars in all_bars.values():
        ds, cs = bars["date"], bars["close"]
        for i in range(1, len(ds)):
            a, b = cs[i - 1], cs[i]
            if a and b and a > 0:
                acc.setdefault(ds[i], []).append(b / a - 1.0)
    return {d: sum(v) / len(v) for d, v in acc.items() if len(v) >= 20}


def build_name(prov, ticker: str, bars: dict, market: dict, iv_series: dict,
               aggression: float = 1.0) -> dict:
    """Every month-end straddle for one name, with its characteristics as of formation."""
    rows, skips = [], {}
    px_raw = bars.get("raw_close") or bars["close"]
    iv_dates = sorted(iv_series)
    for d in month_end_dates(bars):
        i = bars["date"].index(d)
        spot = _f(px_raw[i])
        if spot is None or spot <= 0:
            skips["no_spot"] = skips.get("no_spot", 0) + 1
            continue
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(ticker, day)
        if chain is None or len(chain) == 0:
            skips["no_chain"] = skips.get("no_chain", 0) + 1
            continue
        strad = pick_straddle(chain, spot, day)
        if strad is None:
            skips["no_straddle"] = skips.get("no_straddle", 0) + 1
            continue
        if strad["expiry"].isoformat() > CACHE_END:
            skips["expiry_past_cache"] = skips.get("expiry_past_cache", 0) + 1
            continue
        # settle against the as-traded close at or before expiry
        settle, settle_d = None, None
        for j, ds_ in enumerate(bars["date"]):
            if ds_ <= strad["expiry"].isoformat():
                settle, settle_d = px_raw[j], ds_
        if settle is None or settle_d < d:
            skips["no_settle_bar"] = skips.get("no_settle_bar", 0) + 1
            continue
        res = straddle_return(strad, settle, aggression=aggression)
        if res is None:
            skips["unpriceable"] = skips.get("unpriceable", 0) + 1
            continue

        iv = atm_iv_at(chain, spot, day, strad["expiry"])
        rv = realized_vol(bars["close"][:i + 1])
        rets = daily_returns(bars, d, IDIO_WINDOW)
        mom = idio_moments(rets, market)
        row = {
            "date": d, "ticker": ticker, "return_pct": res["return_pct"],
            "entry_cost": res["entry_cost"], "spread_pct": res["spread_pct"],
            "dte": res["dte"], "strike": res["strike"], "expiry": res["expiry"],
            "spot": spot, "settle": settle,
            # characteristics, all measured strictly at or before formation
            "iv_rv": (math.log(iv / rv) if (iv and rv and iv > 0 and rv > 0) else None),
            "atm_iv": iv, "rv252": rv,
            "idio_vol": mom.get("idio_vol"), "idio_skew": mom.get("idio_skew"),
            "vol_of_vol": vol_of_vol(iv_series, iv_dates, d),
            "smile_slope": smile_slope_at(chain, spot, day, strad["expiry"]),
            "illiq": res["spread_pct"],
        }
        rows.append(row)
    return {"ticker": ticker, "rows": rows, "skips": skips}


# ================================ sorts ====================================================
def quintile_sort(panel: list, char: str, n_q: int = N_QUINTILES,
                  min_names: int = MIN_NAMES_PER_DATE) -> dict:
    """Monthly equal-weighted quintile portfolios, sorted ASCENDING on `char`.

    Q1 is always the LOW end. Because every published sign in CHARACTERISTICS is +1 ("high
    predicts lower option returns"), Q1 is always the quintile the buyer is predicted to want, and
    the long-short is always Q1 minus Q5. Nothing is re-signed after the fact (S2).
    """
    by_date = {}
    for r in panel:
        v = _f(r.get(char))
        if v is not None and _f(r.get("return_pct")) is not None:
            by_date.setdefault(r["date"], []).append((v, r))
    months, dropped = {}, 0
    for d, items in sorted(by_date.items()):
        if len(items) < min_names:
            dropped += 1
            continue
        items.sort(key=lambda t: t[0])
        n = len(items)
        qs = []
        for q in range(n_q):
            lo, hi = int(n * q / n_q), int(n * (q + 1) / n_q)
            grp = items[lo:hi]
            qs.append({"n": len(grp),
                       "ret": _mean([g[1]["return_pct"] for g in grp]),
                       "char": _mean([g[0] for g in grp])})
        months[d] = {"quintiles": qs, "n_names": n,
                     "all_ret": _mean([g[1]["return_pct"] for g in items]),
                     "ls": (qs[0]["ret"] - qs[-1]["ret"])
                     if (qs[0]["ret"] is not None and qs[-1]["ret"] is not None) else None,
                     "q1_excess": (qs[0]["ret"] - _mean([g[1]["return_pct"] for g in items]))
                     if qs[0]["ret"] is not None else None}
    return {"char": char, "months": months, "n_months": len(months),
            "n_dates_dropped_thin": dropped}


def series_stats(vals) -> dict:
    v = [x for x in vals if x is not None]
    n = len(v)
    if n < 3:
        return {"n": n}
    m = sum(v) / n
    sd = _stdev(v)
    return {"n": n, "mean": m, "stdev": sd,
            "t": (m / (sd / math.sqrt(n))) if sd and sd > 0 else None,
            "sharpe": (m / sd) if sd and sd > 0 else None,
            "share_positive": sum(1 for x in v if x > 0) / n}


def evaluate_char(sort: dict, char: str) -> dict:
    """S1 applied to one characteristic."""
    months = sort["months"]
    if not months:
        return {"char": char, "ok": False, "reason": "no usable months"}
    dates = sorted(months)
    ls = [months[d]["ls"] for d in dates]
    q1x = [months[d]["q1_excess"] for d in dates]
    allr = [months[d]["all_ret"] for d in dates]

    qmeans = []
    for q in range(N_QUINTILES):
        qmeans.append(_mean([months[d]["quintiles"][q]["ret"] for d in dates]))
    mono = _spearman(list(range(N_QUINTILES)), qmeans)

    def half(vals, which):
        return [v for d, v in zip(dates, vals)
                if (d < LATE_START) == (which == "early")]

    st_ls, st_q1 = series_stats(ls), series_stats(q1x)
    e, l = series_stats(half(q1x, "early")), series_stats(half(q1x, "late"))
    both = bool((e.get("mean") or -1) > 0 and (l.get("mean") or -1) > 0
                and e.get("n", 0) >= 12 and l.get("n", 0) >= 12)
    meta = CHARACTERISTICS[char]
    return {
        "char": char, "ok": True, "source": meta["source"],
        "is_hypothesis": meta["hypothesis"], "published_sign": meta["sign"],
        "n_months": len(dates), "n_dates_dropped_thin": sort["n_dates_dropped_thin"],
        "quintile_mean_returns": qmeans,
        "quintile_mean_char": [_mean([months[d]["quintiles"][q]["char"] for d in dates])
                               for q in range(N_QUINTILES)],
        "monotonicity": mono,
        "all_names": series_stats(allr),
        # THE INVESTABLE READ (S4): buy the cheap quintile instead of buying everything.
        "long_only_q1_excess": st_q1,
        "held_out_q1_excess": {"early": e, "late": l, "both_positive": both},
        # RESEARCH STATISTIC ONLY: its short leg is a naked short straddle (S4).
        "long_short_NOT_INVESTABLE": st_ls,
        "monthly_q1_excess": {d: months[d]["q1_excess"] for d in dates},
    }


def gate(ev: dict, fdr_discovery: Optional[bool] = None) -> dict:
    """S1, applied mechanically."""
    if not ev.get("ok"):
        return {"passed": False, "reason": ev.get("reason")}
    q1 = ev["long_only_q1_excess"]
    mono = ev.get("monotonicity")
    meta = CHARACTERISTICS[ev["char"]]
    t_ok = bool((q1.get("t") or 0) >= MIN_T and (q1.get("mean") or 0) > 0)
    mono_ok = bool(mono is not None and abs(mono) >= MIN_MONOTONE)
    # Monotone in the PREDICTED direction: quintile means should DECREASE with the characteristic
    # when the published sign is +1, i.e. a negative rank correlation.
    mono_right_way = bool(mono is not None and (mono * -meta["sign"]) > 0)
    enough = bool(ev["n_months"] >= MIN_MONTHS)
    halves = bool(ev["held_out_q1_excess"]["both_positive"])
    disc = bool(fdr_discovery) if fdr_discovery is not None else None
    passed = bool(t_ok and mono_ok and mono_right_way and enough and halves
                  and meta["hypothesis"] and (disc is not False))
    contradiction = bool(mono is not None and abs(mono) >= MIN_MONOTONE
                         and not mono_right_way)
    return {"passed": passed, "t_ok": t_ok, "t": q1.get("t"), "mean": q1.get("mean"),
            "monotonicity": mono, "monotone_enough": mono_ok,
            "monotone_in_predicted_direction": mono_right_way,
            "contradicts_published_sign": contradiction,
            "enough_months": enough, "both_halves_positive": halves,
            "survives_fdr": disc, "is_hypothesis": meta["hypothesis"]}


# ================================ orchestration ============================================
def analyse(panel: list, seed: int = 0) -> dict:
    sorts = {c: quintile_sort(panel, c) for c in CHAR_NAMES}
    evs = {c: evaluate_char(sorts[c], c) for c in CHAR_NAMES}

    pvals, order = [], []
    for c in CHAR_NAMES:
        ev = evs[c]
        if not ev.get("ok"):
            continue
        t = (ev["long_only_q1_excess"].get("t"))
        if t is None:
            continue
        # One-sided: only a POSITIVE long-only excess in the predicted direction can be a
        # discovery. A characteristic that sorts backwards is a contradiction, not a find (S2).
        p = math.erfc(abs(t) / math.sqrt(2.0)) if t > 0 else 1.0
        pvals.append(p)
        order.append(c)
    flags = bh_fdr(pvals, FDR_Q) if pvals else []
    fdr = {c: {"p": pvals[i], "discovery": bool(flags[i]) if i < len(flags) else False}
           for i, c in enumerate(order)}

    gates = {c: gate(evs[c], (fdr.get(c) or {}).get("discovery")) for c in CHAR_NAMES}

    # PBO over the characteristic grid, reusing the tested CSCV helper: each characteristic is a
    # "policy" whose monthly long-only excess return series is its performance.
    rows_by_char = {}
    for c in CHAR_NAMES:
        ev = evs[c]
        if ev.get("ok"):
            rows_by_char[c] = [{"ticker": "Q1", "alert_ts": d, "alert_date": d, "pnl_pct": v}
                               for d, v in ev["monthly_q1_excess"].items() if v is not None]
    pbo = pbo_cscv_policies(rows_by_char, n_blocks=8) if len(rows_by_char) >= 3 else \
        {"ok": False, "reason": "too few characteristics"}

    dsr = {}
    for c in CHAR_NAMES:
        ev = evs[c]
        if ev.get("ok"):
            v = [x for x in ev["monthly_q1_excess"].values() if x is not None]
            if len(v) >= 30:
                dsr[c] = deflated_sharpe(v, n_trials=len(CHAR_NAMES))

    return {
        "panel": panel_summary(panel),
        "characteristics": evs,
        "fdr": fdr,
        "gate": gates,
        "pbo": pbo,
        "deflated_sharpe": dsr,
        "verdict": verdict(evs, gates),
        "params": {"TARGET_DTE": TARGET_DTE, "DTE_BAND": list(DTE_BAND),
                   "N_QUINTILES": N_QUINTILES, "MIN_NAMES_PER_DATE": MIN_NAMES_PER_DATE,
                   "MIN_MONTHS": MIN_MONTHS, "MIN_T": MIN_T, "MIN_MONOTONE": MIN_MONOTONE,
                   "FDR_Q": FDR_Q, "MAX_PBO": MAX_PBO,
                   "characteristics": CHARACTERISTICS,
                   "window": [FORMATION_START, FORMATION_END]},
    }


def panel_summary(panel: list) -> dict:
    rets = [_f(r.get("return_pct")) for r in panel]
    rets = [v for v in rets if v is not None]
    cov = {c: sum(1 for r in panel if _f(r.get(c)) is not None) / len(panel)
           for c in CHAR_NAMES} if panel else {}
    return {"n_straddles": len(panel),
            "n_names": len({r["ticker"] for r in panel}),
            "n_months": len({r["date"] for r in panel}),
            "mean_return": _mean(rets), "median_return": _median(rets),
            "share_total_loss": (sum(1 for v in rets if v <= -0.99) / len(rets))
            if rets else None,
            "mean_entry_cost": _mean([_f(r.get("entry_cost")) for r in panel]),
            "median_spread_pct": _median([_f(r.get("spread_pct")) for r in panel]),
            "median_dte": _median([_f(r.get("dte")) for r in panel]),
            # THE COVERAGE RULE: never judge a characteristic without checking this first.
            "coverage": cov}


def verdict(evs: dict, gates: dict) -> dict:
    adopted = sorted(c for c, g in gates.items() if g.get("passed"))
    contradictions = sorted(c for c, g in gates.items()
                            if g.get("contradicts_published_sign"))
    suggestive = sorted(c for c, g in gates.items()
                        if not g.get("passed") and (g.get("t") or 0) >= 1.0
                        and g.get("monotone_in_predicted_direction"))
    if adopted:
        label = "ADOPT"
    elif suggestive:
        label = "SUGGESTIVE — nothing clears the gate"
    else:
        label = "REJECT — the published cross-sections do not survive here"
    return {"label": label, "adopted": adopted, "suggestive": suggestive,
            "contradicts_published_sign": contradictions,
            "note": "the long-short is never the basis of a verdict — its short leg is a naked "
                    "short straddle and is not investable in this account."}


def save(res: dict, out_dir: str = OUT_DIR, name: str = "XSECTION_RESULTS.json") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return path
