"""
A3 portfolio layer — combined-book sizing, and THE KEY NUMBER: correlation with the long arm.

--------------------------------------------------------------------------------------------
WHY A PORTFOLIO LAYER IS NOT OPTIONAL FOR THIS ARM.

The options-bot's own backtest engine says it plainly in its limitations section, and it is the
most important sentence in that file: "The live bot holds up to 10 spreads across 10 DIFFERENT
tickers, and those 10 are all short puts — they are all the same trade wearing different hats.
In a market-wide selloff their correlation goes to ~1 and all 10 stops trigger on the same
morning."

Per-trade expectancy cannot see that. Ten independent-looking positions with an average pairwise
correlation of 0.4 in calm and 0.9 in a crash do not diversify; they concentrate, and they do it
precisely on the day it hurts. So the book is sized off an estimated PORTFOLIO volatility, not
off ten separate per-trade risk budgets, and the correlation estimate is SHRUNK.

--------------------------------------------------------------------------------------------
THE SHRINKAGE IS PORTED FROM `quant_bots/trend/risk.py`, NOT REWRITTEN.

`shrinkage_lambda`, `sample_correlation`, `shrink_correlation`, `portfolio_vol` and
`naive_weighted_vol` below are the same functions with the same defaults. The reasoning, in that
module's words: Sigma is estimated from ~63 daily observations across up to ~10 names, the sample
correlation matrix has far more free parameters than independent draws, and vol targeting DIVIDES
by the estimate — so an under-estimated portfolio vol becomes over-sized positions. The remedy
is the Ledoit-Wolf move: blend toward a constant-correlation target,

    R_shrunk = (1 - lambda) * R_sample + lambda * R_const

where R_const puts the average sample off-diagonal everywhere and therefore has exactly one
parameter. Volatilities are estimated well and are NOT shrunk; only correlations are.

lambda = 1 / (1 + n_obs/n_names), clamped to [0.20, 0.90]. With 63 observations and 10 names that
is 0.14 -> clamped to 0.20: the floor says we never fully trust a two-month correlation matrix
even when the cross-section is small.

WHAT IS DIFFERENT HERE, and why. The trend bot's weights are directional equity exposures. A put
credit spread's risk is NOT its notional — it is the defined max loss, and its P&L is driven by
the underlying with a delta that is small at entry and grows as the short strike is approached.
So each open spread enters Sigma as its UNDERLYING's return series, weighted by the spread's max
loss, i.e. we treat a spread as "this much money exposed to this name going down". That
over-states risk in calm periods (a 20-delta spread does not lose its full width on a 2% dip)
and is roughly right in the selloffs that actually set the drawdown. Wrong in the conservative
direction, which is the direction to be wrong in.

--------------------------------------------------------------------------------------------
THE CORRELATION WITH THE SINGLE-LEG ARM — what is being computed, and on what footing.

Both arms are put on the SAME risk footing before anything is compared, because otherwise the
correlation would partly measure position sizing rather than co-movement:

    single-leg arm   risk per trade = the premium paid       (max loss on a long option)
    VRP arm          risk per trade = (width - credit) * 100 (max loss on a defined-risk spread)

Every trade in both arms is re-expressed as P&L per $1,000 of risk (options_sizing.RISK_PER_TRADE,
the convention already adopted for the long arm), booked in the month the trade CLOSED, since
that is when the cash is realised. Months in which an arm did not trade contribute 0, not a gap —
dropping them would compute the correlation only over months both arms happened to be active,
which is exactly the wrong subsample.

Reported: monthly correlation, per-year P&L for both arms side by side (2022 / 2023 / 2025 are
the long arm's losing years and are the point of the exercise), the combined book's Sharpe and
max drawdown against the single-leg arm's alone, and the correlation measured only in the long
arm's DOWN months — because an arm that is uncorrelated on average but correlated in the bad
months is worse than useless.

A caveat that will not be dropped: the two arms trade the same 55 large-cap names over the same
2016-2025 window. Whatever correlation comes out is a property of that window, and one shared
sample cannot tell you what happens in a regime neither arm has seen.
"""
from __future__ import annotations

import math
from typing import Optional

from . import options_vrp as V

TRADING_DAYS = 252
MONTHS = 12
RISK_PER_TRADE = 1000.0          # options_sizing.RISK_PER_TRADE — the adopted convention
VOL_LOOKBACK = 63                # trading days of underlying returns for Sigma
TARGET_ANNUAL_VOL = 0.10         # trend/risk.RiskConfig.target_annual_vol
MAX_VOL_SCALE = 2.0              # trend/risk.RiskConfig.max_vol_scale
MIN_RETURN_OBSERVATIONS = 20
MIN_NAMES_FOR_CORRELATION = 2

VOL_METHOD_CORRELATION = "correlation"
VOL_METHOD_NAIVE = "naive_weighted_avg"


# ============================ shrinkage (ported from trend/risk.py) ========================
def shrinkage_lambda(n_observations: int, n_names: int) -> float:
    """lambda = 1/(1 + n_obs/n_names), clamped to [0.20, 0.90]. Port of trend/risk.py."""
    if n_names <= 0 or n_observations <= 0:
        return 0.9
    ratio = n_observations / n_names
    return max(0.20, min(0.90, 1.0 / (1.0 + ratio)))


def sample_correlation(series) -> list:
    """Pearson correlation matrix of equal-length return series. Port of trend/risk.py."""
    n = len(series)
    length = len(series[0]) if n else 0
    if length < 2:
        return [[1.0] * n for _ in range(n)]
    means = [sum(s) / length for s in series]
    devs = [[x - m for x in s] for s, m in zip(series, means)]
    sds = [math.sqrt(sum(d * d for d in dev) / (length - 1)) for dev in devs]
    corr = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if sds[i] <= 0 or sds[j] <= 0:
                rho = 0.0
            else:
                cov = sum(a * b for a, b in zip(devs[i], devs[j])) / (length - 1)
                rho = cov / (sds[i] * sds[j])
            corr[i][j] = corr[j][i] = max(-1.0, min(1.0, rho))
    return corr


def shrink_correlation(corr: list, lam: float) -> list:
    """Blend toward the constant-correlation target. Diagonal stays exactly 1.0."""
    n = len(corr)
    if n < 2:
        return [row[:] for row in corr]
    off = [corr[i][j] for i in range(n) for j in range(i + 1, n)]
    rho_bar = sum(off) / len(off)
    out = [[1.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            out[i][j] = out[j][i] = (1.0 - lam) * corr[i][j] + lam * rho_bar
    return out


def portfolio_vol(weights, vols, corr) -> float:
    """sigma_p = sqrt(sum_i sum_j w_i w_j s_i s_j rho_ij). Port of trend/risk.py."""
    n = len(weights)
    var = 0.0
    for i in range(n):
        wi = weights[i] * vols[i]
        if wi == 0.0:
            continue
        for j in range(n):
            var += wi * weights[j] * vols[j] * corr[i][j]
    return math.sqrt(max(0.0, var))


def naive_weighted_vol(weights, vols) -> float:
    """sum |w_i| s_i — the no-diversification estimate, kept as the explicit fallback path."""
    return sum(abs(w) * v for w, v in zip(weights, vols))


def estimate_book_vol(exposures: dict, returns_panel: dict, as_of: str) -> dict:
    """Annualized sigma of a book of short-put exposures {ticker: dollars_at_risk}.

    Weights are each name's max-loss share of the book. Names with no usable trailing history are
    added back LINEARLY (as if perfectly correlated with everything else), which over-states risk
    and therefore under-sizes — the safe direction when co-movement is unknown. Every fallback is
    labelled in `method` so the sizing path that ran is always attributable after the fact.
    """
    names = list(exposures)
    total = sum(abs(v) for v in exposures.values())
    if not names or total <= 0:
        return {"vol": 0.0, "method": VOL_METHOD_NAIVE, "names": 0, "observations": 0,
                "lam": 0.0}
    weights = {t: exposures[t] / total for t in names}

    series, vols, used = [], [], []
    for t in names:
        hist = _trailing_returns(returns_panel.get(t), as_of, VOL_LOOKBACK)
        if hist is None:
            continue
        mean = sum(hist) / len(hist)
        var = sum((x - mean) ** 2 for x in hist) / (len(hist) - 1)
        if var <= 0:
            continue
        used.append(t)
        series.append(hist)
        vols.append(math.sqrt(var) * math.sqrt(TRADING_DAYS))
    if len(used) < MIN_NAMES_FOR_CORRELATION:
        naive = naive_weighted_vol([weights[t] for t in names],
                                   [0.30] * len(names))     # 30% as a stand-in when unknown
        return {"vol": naive, "method": VOL_METHOD_NAIVE, "names": len(used),
                "observations": 0, "lam": 0.0}

    length = min(len(s) for s in series)
    series = [s[-length:] for s in series]
    lam = shrinkage_lambda(length, len(used))
    corr = shrink_correlation(sample_correlation(series), lam)
    w = [weights[t] for t in used]
    vol_covered = portfolio_vol(w, vols, corr)
    missing = [t for t in names if t not in set(used)]
    vol_uncovered = sum(abs(weights[t]) * 0.30 for t in missing)
    off = [corr[i][j] for i in range(len(used)) for j in range(i + 1, len(used))]
    return {"vol": vol_covered + vol_uncovered, "method": VOL_METHOD_CORRELATION,
            "names": len(used), "observations": length, "lam": lam,
            "avg_pairwise_corr": (sum(off) / len(off)) if off else None}


def _trailing_returns(series: Optional[dict], as_of: str, n: int):
    """Last `n` daily returns strictly BEFORE `as_of`. None when there are too few."""
    if not series:
        return None
    got = [v for d, v in series if d < as_of]
    if len(got) < MIN_RETURN_OBSERVATIONS:
        return None
    return got[-n:]


def build_returns_panel(bars_by: dict) -> dict:
    """{ticker: [(date, daily_return), ...]} from adjusted closes. Sorted, PIT by construction."""
    panel = {}
    for t, b in (bars_by or {}).items():
        ds, cs = b.get("date") or [], b.get("close") or []
        out = []
        for i in range(1, min(len(ds), len(cs))):
            p0, p1 = cs[i - 1], cs[i]
            if p0 and p0 > 0 and p1 and p1 > 0:
                out.append((ds[i], p1 / p0 - 1.0))
        panel[t] = out
    return panel


# ============================ the book simulation ==========================================
def simulate_book(trades, returns_panel: dict, initial_capital: float = V.INITIAL_CAPITAL,
                  vol_target: bool = False) -> dict:
    """Run the generated trades as ONE book under the ported caps, marked to market daily.

    Trades arrive already filtered to one-open-position-per-ticker by the generator (the bot's
    max_positions_per_ticker = 1). This layer applies what only a book can apply: the concurrency
    cap, the deployed-buying-power cap, whole-contract sizing against evolving equity, and — when
    `vol_target` is on — the correlation-aware scaling that says ten short-put spreads are not
    ten independent bets.

    Whole contracts, and a spread whose single-contract max loss exceeds the budget is SKIPPED,
    not taken oversized. `contracts_for` in options_sizing returns 0 for the same reason: a risk
    rule that quietly exceeds itself is decorative.

    Equity is cash minus the marked liability of every open spread, so the drawdown is the real
    mark-to-market one and not the realised-P&L curve (which would hide every open loss).
    """
    ordered = sorted((t for t in trades if t.get("ok") is not False),
                     key=lambda t: (t["alert_ts"], t["ticker"]))
    if not ordered:
        return {"error": "no trades"}

    # Mark path per trade, so equity can be struck on every calendar day the book is open.
    open_book, closed = [], []
    cash = initial_capital
    curve, skipped = [], {"too_expensive": 0, "concurrency": 0, "buying_power": 0}

    all_days = sorted({d for t in ordered for d, _ in (t.get("marks") or [])}
                      | {t["alert_ts"] for t in ordered})
    by_entry = {}
    for t in ordered:
        by_entry.setdefault(t["alert_ts"], []).append(t)

    for day in all_days:
        # --- close anything whose exit is today ---
        still = []
        for pos in open_book:
            if pos["trade"]["exit_date"] <= day:
                tr = pos["trade"]
                cash += tr["pnl_dollars"] * pos["contracts"]
                closed.append({**tr, "contracts": pos["contracts"],
                               "book_pnl": tr["pnl_dollars"] * pos["contracts"]})
            else:
                still.append(pos)
        open_book = still

        # --- mark equity: cash plus the unrealised P&L of everything still open ---
        unreal = 0.0
        for pos in open_book:
            m = pos["mark_by_day"].get(day, pos["last_cost"])
            pos["last_cost"] = m
            unreal += (pos["trade"]["credit_ps"] - m) * V.CONTRACT_MULTIPLIER * pos["contracts"]
        equity = cash + unreal
        deployed = sum(p["max_loss_total"] for p in open_book)
        curve.append({"date": day, "equity": equity, "deployed": deployed,
                      "n_open": len(open_book)})

        # --- attempt today's entries ---
        for tr in by_entry.get(day, []):
            if len(open_book) >= V.MAX_CONCURRENT:
                skipped["concurrency"] += 1
                continue
            max_loss_pc = tr["max_risk_dollars"]
            if max_loss_pc <= 0:
                continue
            scale = V.vol_scale_factor(tr.get("atm_iv"))
            budget = equity * V.RISK_PCT_PER_TRADE * scale
            if vol_target:
                exposures = {p["trade"]["ticker"]: p["max_loss_total"] for p in open_book}
                exposures[tr["ticker"]] = exposures.get(tr["ticker"], 0.0) + max_loss_pc
                est = estimate_book_vol(exposures, returns_panel, day)
                if est["vol"] > 0:
                    budget *= min(MAX_VOL_SCALE, TARGET_ANNUAL_VOL / est["vol"])
            contracts = int(budget // max_loss_pc)
            if contracts < 1:
                skipped["too_expensive"] += 1
                continue
            contracts = min(contracts, V.MAX_CONTRACTS_PER_SPREAD)
            order_risk = max_loss_pc * contracts
            if deployed + order_risk > equity * V.MAX_TOTAL_DEPLOYED_PCT:
                skipped["buying_power"] += 1
                continue
            open_book.append({
                "trade": tr, "contracts": contracts, "max_loss_total": order_risk,
                "mark_by_day": {d: c for d, c in (tr.get("marks") or [])},
                # Before the first usable mark a position is worth what we sold it for, i.e.
                # zero P&L. Starting at 0.0 would book the entire credit as instant profit on
                # every quiet day and quietly flatter the equity curve.
                "last_cost": tr["credit_ps"],
            })
            deployed += order_risk

    eq = [c["equity"] for c in curve]
    peak, mdd = eq[0] if eq else initial_capital, 0.0
    for e in eq:
        peak = max(peak, e)
        if peak > 0:
            mdd = min(mdd, e / peak - 1.0)
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq)) if eq[i - 1] > 0]
    mean = sum(rets) / len(rets) if rets else 0.0
    sd = (math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1))
          if len(rets) > 1 else 0.0)
    years = len(curve) / TRADING_DAYS if curve else 0.0
    final = eq[-1] if eq else initial_capital
    return {
        "n_taken": len(closed), "n_generated": len(ordered), "skipped": skipped,
        "initial_capital": initial_capital, "final_equity": final,
        "total_return": final / initial_capital - 1.0,
        "cagr": (final / initial_capital) ** (1 / years) - 1.0 if years > 0.5 and final > 0
        else None,
        "annual_vol": sd * math.sqrt(TRADING_DAYS),
        "sharpe": (mean * TRADING_DAYS) / (sd * math.sqrt(TRADING_DAYS)) if sd > 0 else None,
        "max_drawdown": mdd,
        "vol_targeted": vol_target,
        "curve": [{"date": c["date"], "equity": round(c["equity"], 2)} for c in curve[::5]],
        "avg_concurrent": (sum(c["n_open"] for c in curve) / len(curve)) if curve else 0.0,
    }


# ============================ THE KEY NUMBER: arm correlation ==============================
def _exit_date_single_leg(row) -> Optional[str]:
    """The long arm stores alert_ts + held_days rather than an exit date. Reconstruct it."""
    import datetime as dt

    try:
        d = dt.date.fromisoformat(str(row["alert_ts"])[:10])
    except (KeyError, TypeError, ValueError):
        return None
    h = row.get("held_days")
    if h is None:
        return None
    return (d + dt.timedelta(days=int(h))).isoformat()


def monthly_pnl_per_risk(rows, exit_date_fn, risk: float = RISK_PER_TRADE) -> dict:
    """{'YYYY-MM': dollars} at a common $`risk` per trade, booked in the CLOSING month.

    Sizing-invariant by construction: pnl_pct is a return on the trade's own max loss, so
    multiplying by a fixed risk budget puts both arms on the same footing without either arm's
    contract-count convention leaking into the comparison.
    """
    out = {}
    for r in rows:
        p = r.get("pnl_pct")
        if p is None:
            continue
        ed = exit_date_fn(r)
        if not ed:
            continue
        out[ed[:7]] = out.get(ed[:7], 0.0) + p * risk
    return out


def _corr(a, b) -> Optional[float]:
    n = len(a)
    if n < 3:
        return None
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    return cov / math.sqrt(va * vb)


def _sharpe_monthly(series) -> Optional[float]:
    n = len(series)
    if n < 3:
        return None
    m = sum(series) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in series) / (n - 1))
    if sd <= 0:
        return None
    return (m / sd) * math.sqrt(MONTHS)


def _max_dd(series) -> float:
    cum, peak, mdd = 0.0, 0.0, 0.0
    for x in series:
        cum += x
        peak = max(peak, cum)
        mdd = min(mdd, cum - peak)
    return mdd


def arm_correlation(vrp_rows, single_rows, risk: float = RISK_PER_TRADE) -> dict:
    """Correlation of the two arms' monthly P&L, and what the combined book looks like.

    Months where an arm did not trade count as ZERO, not as missing. Restricting to months both
    arms were active would measure co-movement on a subsample chosen by activity, and activity is
    itself regime-dependent — precisely the bias this number exists to avoid.
    """
    vrp = monthly_pnl_per_risk(vrp_rows, lambda r: r.get("exit_date"), risk)
    sgl = monthly_pnl_per_risk(single_rows, _exit_date_single_leg, risk)
    if not vrp or not sgl:
        return {"error": "one arm has no monthly P&L"}
    lo = max(min(vrp), min(sgl))
    hi = min(max(vrp), max(sgl))
    months = sorted(m for m in set(vrp) | set(sgl) if lo <= m <= hi)
    v = [vrp.get(m, 0.0) for m in months]
    s = [sgl.get(m, 0.0) for m in months]
    c = [x + y for x, y in zip(v, s)]

    down = [i for i, x in enumerate(s) if x < 0]
    corr_down = (_corr([v[i] for i in down], [s[i] for i in down])
                 if len(down) >= 3 else None)

    years = sorted({m[:4] for m in months})
    per_year = {}
    for y in years:
        idx = [i for i, m in enumerate(months) if m[:4] == y]
        per_year[y] = {
            "vrp": sum(v[i] for i in idx),
            "single_leg": sum(s[i] for i in idx),
            "combined": sum(c[i] for i in idx),
        }
    return {
        "months": len(months), "window": [months[0], months[-1]] if months else None,
        "risk_per_trade": risk,
        "monthly_correlation": _corr(v, s),
        "correlation_in_single_leg_down_months": corr_down,
        "n_single_leg_down_months": len(down),
        "vrp_sharpe": _sharpe_monthly(v),
        "single_leg_sharpe": _sharpe_monthly(s),
        "combined_sharpe": _sharpe_monthly(c),
        "vrp_max_drawdown_dollars": _max_dd(v),
        "single_leg_max_drawdown_dollars": _max_dd(s),
        "combined_max_drawdown_dollars": _max_dd(c),
        "vrp_total": sum(v), "single_leg_total": sum(s), "combined_total": sum(c),
        "vrp_worst_month": min(v), "single_leg_worst_month": min(s),
        "combined_worst_month": min(c),
        "per_year": per_year,
        "smooths_the_book": bool(_sharpe_monthly(c) is not None
                                 and _sharpe_monthly(s) is not None
                                 and _sharpe_monthly(c) > _sharpe_monthly(s)),
        "caveat": ("both arms trade the same 55 large caps over the same 2016-2025 window; this "
                   "correlation is a property of that window, not a law"),
    }


def stress_correlation(returns_panel: dict, tickers, iv_by_date: Optional[dict] = None,
                       worst_n: int = 20, high_vol_pct: float = 0.10) -> dict:
    """Does cross-name correlation really go to ~1 in a selloff? Measured, not assumed.

    THE OBVIOUS TEST IS BIASED, so it is reported but not believed. Taking the worst N days of
    the equal-weight basket and correlating within them conditions the sample on its own
    cross-sectional mean: every selected day already has a large common component, and the
    correlation is then estimated from the DEVIATIONS around that (already extreme) mean.
    Selection on the aggregate compresses the estimate, and it can easily come out LOWER than
    the full sample even when co-movement genuinely rose. A number that moves the wrong way for
    a known statistical reason is not evidence of anything, so it is labelled rather than quoted.

    The primary split is therefore on an EXOGENOUS marker: the cross-sectional average ATM IV
    (A2's daily series). High-vol days are the top `high_vol_pct` of that distribution. Selecting
    on the level of implied vol does not condition on the realised cross-sectional mean return,
    so the comparison is much closer to honest. It is still not perfect — vol and correlation are
    themselves related — but it is not the artifact above.
    """
    names = [t for t in tickers if returns_panel.get(t)]
    if len(names) < 3:
        return {"error": "too few names"}
    by_date = {}
    for t in names:
        for d, r in returns_panel[t]:
            by_date.setdefault(d, {})[t] = r
    days = sorted(d for d, row in by_date.items() if len(row) >= max(3, len(names) // 2))
    if len(days) < 100:
        return {"error": "too few aligned days"}

    def avg_corr(subset):
        subset = sorted(subset)
        if len(subset) < 10:
            return None
        common = [t for t in names
                  if sum(1 for d in subset if t in by_date[d]) == len(subset)]
        if len(common) < 3:
            return None
        series = [[by_date[d][t] for d in subset] for t in common]
        corr = sample_correlation(series)
        off = [corr[i][j] for i in range(len(common)) for j in range(i + 1, len(common))]
        return sum(off) / len(off) if off else None

    out = {"n_names": len(names), "n_days": len(days),
           "avg_pairwise_corr_full_sample": avg_corr(days)}

    if iv_by_date:
        marked = [d for d in days if iv_by_date.get(d) is not None]
        if len(marked) >= 100:
            ranked = sorted(marked, key=lambda d: iv_by_date[d], reverse=True)
            k = max(20, int(len(ranked) * high_vol_pct))
            hi, lo = ranked[:k], ranked[k:]
            out.update({
                "primary_split": "cross-sectional average ATM IV (exogenous to returns)",
                "n_high_vol_days": len(hi), "high_vol_pct": high_vol_pct,
                "avg_pairwise_corr_high_vol": avg_corr(hi),
                "avg_pairwise_corr_rest": avg_corr(lo),
                "high_vol_window_examples": sorted(hi)[:5],
            })
    basket = {d: sum(by_date[d].values()) / len(by_date[d]) for d in days}
    worst = sorted(days, key=lambda d: basket[d])[:worst_n]
    out.update({
        "worst_n": worst_n,
        "avg_pairwise_corr_worst_days_BIASED": avg_corr(worst),
        "worst_days": sorted(worst)[:10],
        "worst_days_caveat": ("selected on their own basket return, so this is conditioned on "
                              "the common component and is biased DOWNWARD; do not read it as "
                              "evidence that correlation falls in a selloff"),
        "note": ("short puts across names are the same trade in a selloff; if the high-vol "
                 "figure is above the rest, diversification is not available when it is needed "
                 "and the book must be sized off the stressed number"),
    })
    return out
