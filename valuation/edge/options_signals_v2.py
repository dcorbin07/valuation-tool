"""
§2 — new ThetaData-derived option signals, judged ON THE FADE. PRE-SPECIFIED GATE, committed
results-free before any of them were computed.

--------------------------------------------------------------------------------------------
WHAT THIS IS ACTUALLY TESTING, AND WHY THE USUAL TEST WOULD BE THE WRONG ONE.

The scream-buy edge is not weak on average - it is DECAYING: +16.4%/trade over 2016-2020 and
+4.4% over 2021-2025, with 2022, 2023 and 2025 negative. A signal that lifts full-sample
expectancy is therefore close to worthless here: the full sample is dominated by the early
period that already works. Phase 3 made that concrete twice - the 65-75 DTE band gained +11.55pp
on the early half and +1.19pp on the late one, and was rejected.

So every signal below is judged on ONE question: **does it improve the 2021-2025 half?**

--------------------------------------------------------------------------------------------
HOW LOOK-AHEAD IS AVOIDED IN A TEST THAT TARGETS THE LATE PERIOD.

Aiming at the late half creates an obvious trap: tune a threshold until the late half looks
good, and the result is guaranteed and meaningless. So the split is strict and one-directional:

    THRESHOLD IS FITTED ON 2016-2020 ONLY.  It is the median of the signal among PROFITABLE
    early-half trades - a fixed, untuned recipe ("look like the early winners looked"), not a
    search over cutoffs.

    IT IS THEN APPLIED UNCHANGED TO 2021-2025, which never informed it.

No threshold is ever selected by looking at late-half outcomes. A signal that needed such tuning
is exactly what this design refuses to let through.

--------------------------------------------------------------------------------------------
THE SIGNALS - all computed from the CACHED chain, no new data pull.

  iv_rank        ATM IV percentile against that name's own trailing year. "Is vol rich or cheap
                 FOR THIS STOCK", which raw IV cannot say (a 40% IV is cheap for TSLA, rich for KO).
  vrp            ATM IV minus trailing 30-day realised vol. Positive = options priced above
                 what the stock has actually been doing, i.e. you are overpaying for the move.
                 For a LONG option buyer a NEGATIVE VRP should be the friendly state, so the
                 signal is negated to keep the "higher is better" convention.
  term_slope     ~60-DTE ATM IV minus front-expiry ATM IV. Backwardation (negative) marks stress
                 or a pending event; contango is the calm default.
  skew_25d       25-delta put IV minus 25-delta call IV. Rising put skew is the market paying up
                 for downside protection.
  gex_proxy      sum over strikes of open_interest * gamma, calls minus puts, scaled by spot.
                 A dealer-positioning proxy: large positive = pinning/mean-reverting, large
                 negative = moves get amplified. Gamma is computed from IV by Black-Scholes, as
                 the mandate specifies, because the vendor does not serve it cheaply.

NOT INCLUDED: tick-level flow (sweeps, blocks, aggressor side). It needs the tick trade feed,
which is not in the cached EOD history and would be a fresh multi-hour pull. Its absence is
recorded rather than quietly skipped, because "we tested the flow signals" would be false.

--------------------------------------------------------------------------------------------
PRE-COMMITTED GATE - a signal is adopted as a live filter only if ALL hold:

  1. LATE-HALF LIFT: filtered expectancy over 2021-2025 beats unfiltered by >= MIN_LATE_GAIN.
  2. IT KEEPS A BOOK: it retains at least MIN_RETAINED of late-half trades. A filter that keeps
     8% of signals has not fixed the strategy, it has replaced it with a much smaller one, and
     its apparent edge is a small-sample artefact.
  3. SAMPLE: at least MIN_TRADES filtered trades in the late half.
  4. NOT MERELY SELECTIVE: it must beat a random filter that keeps the SAME NUMBER of late-half
     trades. Reported alongside every result, because dropping trades at random from a
     heavy-tailed distribution moves expectancy on its own.
  5. NO CHERRY-PICKING ACROSS SIGNALS: with several signals tested at once, the best of them
     will look good by chance. Any winner must ALSO be positive in the early half - not because
     the early half matters for adoption, but because a signal that only ever helps the period
     it was aimed at is indistinguishable from noise that happened to land there.

Expect rejections. These are the most-watched derived quantities in options, and the fade may
simply be the strategy decaying rather than something a filter can rescue.
"""
from __future__ import annotations

from typing import Optional

# Pre-committed gate.
MIN_LATE_GAIN = 0.05        # +5pp of expectancy on the 2021-2025 half
MIN_RETAINED = 0.40         # must keep >=40% of late-half trades
MIN_TRADES = 60             # filtered late-half trades
LATE_START = "2021-01-01"

SIGNALS = ("iv_rank", "vrp", "term_slope", "skew_25d", "gex_proxy")


def _iv_at_delta(enr, target_delta: float, right: str) -> Optional[float]:
    """IV of the contract closest to a target delta on one expiry. None if nothing qualifies."""
    cand = [r for _, r in enr.iterrows()
            if str(r.get("right", ""))[:1].upper() == right[:1].upper()
            and r.get("delta") is not None and r.get("iv") is not None]
    if not cand:
        return None
    best = min(cand, key=lambda r: abs(abs(float(r["delta"])) - target_delta))
    return float(best["iv"])


def compute_signals(chain, underlying: float, as_of, iv_history=None,
                    realized_vol: Optional[float] = None) -> dict:
    """All five signals for one name on one date, from the cached chain. Missing -> absent.

    Absent rather than defaulted: a fabricated zero would be indistinguishable from a real
    neutral reading, and would flow into every downstream average.
    """
    import datetime as dt

    import pandas as pd

    from . import blackscholes as BS

    if chain is None or len(chain) == 0:
        return {}
    asof = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    exp = pd.to_datetime(chain["expiration"]).dt.date
    future = sorted({e for e in exp if e > asof})
    if not future:
        return {}
    out = {}

    front = future[0]
    enr_front = BS.enrich_chain(chain[exp == front], underlying, asof)
    atm_front = None
    if enr_front is not None and len(enr_front):
        near = enr_front.dropna(subset=["iv"]).copy()
        if len(near):
            near["_d"] = (near["strike"].astype(float) - underlying).abs()
            atm_front = float(near.sort_values("_d")["iv"].iloc[0])

    # ~60-DTE expiry for term structure and skew (the band we actually trade).
    mid_exp = min(future, key=lambda e: abs((e - asof).days - 60))
    enr_mid = BS.enrich_chain(chain[exp == mid_exp], underlying, asof)
    atm_mid = None
    if enr_mid is not None and len(enr_mid):
        near = enr_mid.dropna(subset=["iv"]).copy()
        if len(near):
            near["_d"] = (near["strike"].astype(float) - underlying).abs()
            atm_mid = float(near.sort_values("_d")["iv"].iloc[0])

    if atm_front is not None and atm_mid is not None:
        out["term_slope"] = atm_mid - atm_front

    if enr_mid is not None and len(enr_mid):
        pv = _iv_at_delta(enr_mid, 0.25, "P")
        cv = _iv_at_delta(enr_mid, 0.25, "C")
        if pv is not None and cv is not None:
            out["skew_25d"] = pv - cv

    if atm_mid is not None:
        if realized_vol is not None and realized_vol > 0:
            # Negated: a long buyer wants IV BELOW realised, so cheaper = higher score.
            out["vrp"] = -(atm_mid - realized_vol)
        if iv_history:
            hist = [v for v in iv_history if v is not None]
            if len(hist) >= 60:
                out["iv_rank"] = sum(1 for v in hist if v < atm_mid) / len(hist)

    # GEX proxy: net dealer gamma across the near expiries we can price.
    if enr_mid is not None and len(enr_mid):
        g = enr_mid.dropna(subset=["gamma"])
        tot = 0.0
        for _, r in g.iterrows():
            oi = r.get("open_interest")
            if oi is None or oi < 0:
                continue
            sign = 1.0 if str(r.get("right", ""))[:1].upper() == "C" else -1.0
            tot += sign * float(oi) * float(r["gamma"])
        if tot:
            out["gex_proxy"] = tot * underlying / 1e6
    return out


def fit_threshold(early_rows, signal: str) -> Optional[float]:
    """Median of the signal among PROFITABLE early-half trades. Untuned by construction."""
    import statistics as st

    vals = [r.get(signal) for r in early_rows
            if r.get(signal) is not None and (r.get("pnl_pct") or 0) > 0]
    if len(vals) < 30:
        return None
    return st.median(vals)


def evaluate(rows, signal: str, seed: int = 0) -> dict:
    """Fit on 2016-2020, judge on 2021-2025, against the pre-committed gate."""
    import random

    from .options_tracker import _stats

    early = [r for r in rows if r["alert_ts"] < LATE_START]
    late = [r for r in rows if r["alert_ts"] >= LATE_START]
    thr = fit_threshold(early, signal)
    if thr is None:
        return {"signal": signal, "ok": False, "reason": "too few early-half values"}

    late_has = [r for r in late if r.get(signal) is not None]
    keep = [r for r in late_has if r[signal] >= thr]
    if not keep or not late_has:
        return {"signal": signal, "ok": False, "reason": "no late-half coverage", "threshold": thr}

    base, filt = _stats(late_has), _stats(keep)
    gain = (filt["expectancy_pct"] or 0) - (base["expectancy_pct"] or 0)
    retained = len(keep) / len(late_has)

    rnd = random.Random(seed)
    ctrl = []
    for _ in range(300):
        s = rnd.sample(late_has, min(len(keep), len(late_has)))
        ctrl.append(_stats(s)["expectancy_pct"] or 0)
    ctrl_mean = sum(ctrl) / len(ctrl)

    early_has = [r for r in early if r.get(signal) is not None]
    early_keep = [r for r in early_has if r[signal] >= thr]
    early_gain = ((_stats(early_keep)["expectancy_pct"] or 0)
                  - (_stats(early_has)["expectancy_pct"] or 0)) if early_keep else None

    passed = (gain >= MIN_LATE_GAIN and retained >= MIN_RETAINED
              and filt["n_closed"] >= MIN_TRADES
              and (filt["expectancy_pct"] or 0) > ctrl_mean
              and early_gain is not None and early_gain > 0)
    return {"signal": signal, "ok": True, "threshold": thr,
            "late_n_all": base["n_closed"], "late_n_kept": filt["n_closed"],
            "retained": retained,
            "late_exp_all": base["expectancy_pct"], "late_exp_filtered": filt["expectancy_pct"],
            "late_gain": gain, "random_control_exp": ctrl_mean,
            "early_gain": early_gain, "passed": passed}
