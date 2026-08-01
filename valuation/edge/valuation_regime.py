"""
Valuation-regime "risk-off" overlay — PRE-SPECIFIED RULE. Committed BEFORE it was ever run.

Companion to regime.py (the 200-day trend filter, which was REJECTED because its entire benefit
came from the 2008 half). Same discipline, different premise: instead of asking "is the market
falling?", ask "is the market EXPENSIVE?" and stand down when it is.

Committed in its own results-free commit so the git history proves the rule and threshold were
fixed before any number came back.

--------------------------------------------------------------------------------------------
THE PRIMARY RULE — one rule, pre-committed. Not three.

    At each rebalance date, compute the market-wide AGGREGATE EARNINGS YIELD from the panel:

        agg_ey = sum(net income) / sum(market cap)     over every scored name that date

    which is the market-cap-weighted earnings yield (equivalently 1 / aggregate P/E). It is
    computed by SUMMING numerator and denominator rather than averaging per-name ratios, so a
    single tiny-cap name with a freak yield cannot move it, and loss-makers net off correctly
    instead of producing an undefined P/E.

    Risk-off when the market is expensive RELATIVE TO ITS OWN HISTORY:

        agg_ey <= Pth percentile of agg_ey over all PRIOR rebalance dates   ->  risk-off
        otherwise                                                          ->  fully invested

    An expanding trailing window (every prior date, never the current or future ones) with a
    minimum history of MIN_HISTORY dates. An absolute P/E threshold would be hindsight: "over
    20x is expensive" is a fact about the last 20 years that nobody knew in 1998.

PRE-COMMITTED PARAMETERS — not to be changed after seeing results:

    VALUATION_PCTILE   = 20         risk-off in the cheapest-yield (= most expensive) quintile
    MIN_HISTORY        = 20         rebalances of history before the rule may fire at all
    RISK_OFF_EXPOSURE  = 0.0, 0.5   both reported
    CASH_ANNUAL_RATE   = 0.0        cash earns nothing (harsh on the overlay, same as regime.py)

SECONDARY METRICS ARE DIAGNOSTICS, NOT CANDIDATES. median P/E and a crude aggregate PEG are
computed and reported because they are informative about what the market looked like, but they
are NOT alternative decision rules. Testing three rules would be three chances to get lucky on
one crash, which is the exact error this file exists to avoid. If the primary rule fails, the
answer is "rejected", not "let me try the other two".

--------------------------------------------------------------------------------------------
ADOPTION BAR — stricter than regime.py's, and also pre-committed:

    1. Max drawdown must improve by >= MIN_DD_IMPROVEMENT on the full sample.
    2. Return give-up at most MAX_RETURN_GIVEUP.
    3. Must improve BOTH max drawdown AND Sharpe in BOTH held-out halves. regime.py passed
       every full-sample test and died here; a valuation rule is MORE exposed to this failure,
       because "expensive" is dominated by two episodes (1999-2000 and 2021) in 18 years.
    4. Whipsaw and OPPORTUNITY COST reported: how long it sits out, and what the book did while
       it was out. A valuation rule's characteristic failure is not a crash — it is sitting in
       cash through an expensive market that keeps rising for years.

Rejecting is the expected outcome.

================================ RESULT (run after the above was committed) =================
REJECTED on every criterion, and more decisively than the trend filter.

    config                      net ann   Sharpe    maxDD   flips   invested
    no overlay                  +30.69%     1.13   -57.0%       -          -
    valuation overlay off=0%    +26.58%     1.05   -57.0%       8        94%
    valuation overlay off=50%   +28.75%     1.11   -57.0%       8        94%

MAX DRAWDOWN DOES NOT MOVE AT ALL -- identical to three decimals in every configuration. The
rule fires on only 10 of 165 rebalances and never during the actual crash.

    half    base DD / Sharpe    off=0%            off=50%
    early   -57.0% / 1.09       DD +0.0% Sh -0.07  DD +0.0% Sh -0.01
    late    -34.8% / 1.16       DD +0.0% Sh -0.10  DD +0.0% Sh -0.04

Worse Sharpe in BOTH halves. And the mechanism is exactly the failure this file pre-specified:
WHILE RISK-OFF THE BOOK RETURNED +10.02% PER PERIOD (+77.3% annualized). It sat out the BEST
periods, not the worst. "Expensive" and "about to fall" are different things, and an aggregate
valuation percentile picks up the former with no information about the latter.

Kept as a toggle (settings.VALUATION_REGIME_OVERLAY), OFF by default. Unlike the trend filter
there is not even a tempting full-sample story here to argue about.

TWO CAVEATS ON THE REPORTED LEVELS (they do not affect the rule, which is a percentile of a
quantity against its own history, so any constant basis cancels):
  * The aggregate earnings yield is computed from the panel's QUARTERLY (ARQ) net income, so
    the implied "P/E ~96x" is a quarterly-flow artifact. Multiply the yield by ~4 for an
    annualized figure: ~24x, which is a plausible market P/E. The printed multiple should not
    be quoted as a market P/E.
  * The aggregate PEG came back NaN because revenue growth is not persisted on panel rows
    (only the value-ratio raws are). It is reported as unavailable rather than approximated.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

VALUATION_PCTILE = 20
MIN_HISTORY = 20
RISK_OFF_EXPOSURE = (0.0, 0.5)
CASH_ANNUAL_RATE = 0.0

MIN_DD_IMPROVEMENT = 0.05
MAX_RETURN_GIVEUP = 0.03


def aggregate_valuation(panel) -> pd.DataFrame:
    """Per-rebalance market-wide valuation, strictly from that date's cross-section.

    Returns a frame indexed by date with:
        agg_ey     sum(net income) / sum(market cap)   -- the primary metric
        median_pe  median of per-name P/E over PROFITABLE names only (diagnostic)
        agg_peg    aggregate P/E divided by median revenue growth, in percent (diagnostic)

    `earnings_yield` on the panel is net income / market cap per name, so net income is
    recovered as earnings_yield * market_cap — no extra column needed, and it stays consistent
    with whatever the scorer actually used (including the P7 currency fix).
    """
    need = {"date", "market_cap"}
    if panel is None or panel.empty or not need <= set(panel.columns):
        return pd.DataFrame()
    ey_col = "raw_earnings_yield" if "raw_earnings_yield" in panel.columns else None
    rows = []
    for d, sub in panel.groupby("date"):
        mc = pd.to_numeric(sub["market_cap"], errors="coerce")
        ey = pd.to_numeric(sub[ey_col], errors="coerce") if ey_col else None
        rec = {"date": d, "n": int(len(sub))}
        if ey is not None:
            ok = mc.notna() & ey.notna() & (mc > 0)
            tot_mc = float(mc[ok].sum())
            tot_ni = float((ey[ok] * mc[ok]).sum())
            rec["agg_ey"] = (tot_ni / tot_mc) if tot_mc > 0 else np.nan
            pos = ok & (ey > 0)
            rec["median_pe"] = float((1.0 / ey[pos]).median()) if pos.any() else np.nan
            g = (pd.to_numeric(sub.get("raw_revenue_growth"), errors="coerce")
                 if "raw_revenue_growth" in sub.columns else None)
            gm = float(g.median()) if g is not None and g.notna().any() else np.nan
            agg_pe = (1.0 / rec["agg_ey"]) if rec.get("agg_ey") else np.nan
            rec["agg_peg"] = (agg_pe / (gm * 100.0)) if (gm and gm > 0 and agg_pe == agg_pe) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def valuation_signal(val_frame, pctile: int = VALUATION_PCTILE,
                     min_history: int = MIN_HISTORY) -> dict:
    """{date: True if invested} — risk-off when agg_ey sits in its cheapest-yield tail.

    The percentile is computed over PRIOR dates only (expanding window), so the decision at
    each date uses nothing that was not already observable.
    """
    out = {}
    if val_frame is None or len(val_frame) == 0 or "agg_ey" not in val_frame.columns:
        return out
    dates = list(val_frame["date"])
    vals = list(pd.to_numeric(val_frame["agg_ey"], errors="coerce"))
    hist = []
    for d, v in zip(dates, vals):
        if v != v or len(hist) < min_history:
            out[d] = True                       # not enough history -> stay invested
        else:
            thr = float(np.percentile(hist, pctile))
            out[d] = bool(v > thr)              # yield ABOVE the low tail = not expensive
        if v == v:
            hist.append(v)                      # append AFTER deciding: never sees itself
    return out
