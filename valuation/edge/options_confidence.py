"""
Per-alert confidence for the live scream-buy engine.

--------------------------------------------------------------------------------------------
WHAT "CONFIDENCE" MEANS HERE, AND WHAT IT EMPHATICALLY DOES NOT MEAN.

It is **expectancy-confidence**: how much backtested evidence there is that alerts with this
fingerprint carry positive expected return per trade. It is **NOT a probability of winning.**

That distinction is not pedantry, it is the whole payoff shape of the strategy. The validated
single-leg book has a **37.4% hit rate** with **+120.4% average win** against **-55.3% average
loss**. Most trades lose. The edge is that the minority of winners more than double while the
losers roughly halve. So a "high" confidence alert is one where the *expected value* is best
supported - it is still, individually, more likely to lose than win.

`DISCLAIMER` below is returned on every single result and is meant to be rendered on the card.
If a UI shows the level without it, the UI is lying.

--------------------------------------------------------------------------------------------
THE THREE THINGS THAT MOVE THE NUMBER.

1. BUCKET EXPECTANCY. The backtest measured expectancy per trade across the fingerprint
   dimensions that are knowable at alert time: entry IV regime, DTE band, contract delta, and
   the term-structure read. Those tables are transcribed below as constants with their sample
   sizes, sourced line by line to OPTIONS_BACKTEST_RESULTS.md. They are committed rather than
   read from `data/` because the licensed panel is gitignored and the live app must not depend
   on it.

2. THE FADE, APPLIED AS A DISCOUNT. Every bucket table is a FULL-SAMPLE number, and the full
   sample is dominated by the early period that worked: +16.4% over 2016-2020 against +4.4%
   over 2021-2025. Quoting a full-sample bucket to a user today would advertise a regime that
   has not existed for five years. So each full-sample bucket is multiplied by `FADE_FACTOR`
   = late-half expectancy / full-sample expectancy = 0.044 / 0.104. This is a deliberate
   HAIRCUT, not a forecast: it assumes the recent regime persists rather than that the early
   one returns.

   The term-structure bucket is exempt because it was ALREADY measured on the late half only -
   applying the discount to it would double-count the fade.

3. THIN EVIDENCE, AS A CAP RATHER THAN A TERM. Thin evidence cannot produce a confident answer
   however good the point estimate looks, so it caps the level at "thin" outright rather than
   nudging it down. A cap is used because the failure mode being guarded against - a flattering
   subgroup of eleven trades - is not a small error, it is a different kind of claim.

   Two things trigger it, and they are NOT the same thing:

     a) TOO FEW DIMENSIONS KNOWN (`MIN_DIMENSIONS`). This is the one that actually fires in
        production, and it amounts to "no contract was resolved on the chain": DTE and delta are
        knowable only from a real contract, so the dimension count is a proxy for whether the
        trade being described can actually be placed. Every bucket here was measured on trades
        that had a 35-delta 45-75 DTE contract, so quoting one for an alert that has no contract
        borrows authority the number does not carry.

     b) A NARROW BUCKET (`MIN_BUCKET_N`). With the tables as committed this NEVER fires - the
        smallest bucket has 192 trades. It is a guard for the future, not an active mechanism,
        and saying so is the point: if anyone later adds a finer cut (per ticker, per sector,
        per year), it stops a confident-looking answer from shipping on eleven trades. The test
        exercises it through an injected table rather than pretending it fires today.

--------------------------------------------------------------------------------------------
THE BACKWARDATION NUMBER IS DERIVED, NOT MEASURED, AND IS LABELLED AS SUCH.

phase 3b reported the late half as: all 756 trades +4.76%, and the 307 contango trades
(40.6%) +12.88%. It never printed the backwardation complement, but that complement is pinned
by arithmetic:

    exp(back) = (0.0476 - 0.406 * 0.1288) / 0.594 = -0.0079

So backwardation alerts ran at roughly **-0.8%** per trade in the recent half. That is the
honest reason the term filter is a gate and not a garnish. It is stored as
`TERM_BUCKETS["backwardation"]` with `derived: True` so nobody later cites it as a measured
figure. `test_confidence_backwardation_is_the_arithmetic_complement` pins the derivation.

--------------------------------------------------------------------------------------------
WHAT THIS DOES NOT DO.

It does not combine the buckets with a fitted model. The dimensions are correlated (a 65-75 DTE
contract at 35 delta is not independent of its IV regime) and there is nowhere near enough data
to estimate that interaction without overfitting the same 1,540 trades yet again. It takes the
plain MEAN of the contributing bucket estimates and reports which ones contributed. That is a
transparent heuristic for RANKING alerts against each other, and it is described that way in
`method` on every result rather than dressed up as a per-trade expected return.
"""
from __future__ import annotations

from typing import Optional

# ---- headline reference, from OPTIONS_BACKTEST_RESULTS.md ---------------------------------
FULL_SAMPLE_EXPECTANCY = 0.104     # +10.4%/trade, 1,540 closed trades 2016-2025
LATE_HALF_EXPECTANCY = 0.044       # +4.4%/trade, 2020-12-09 .. 2025-11-03, n=770
EARLY_HALF_EXPECTANCY = 0.164      # +16.4%/trade, 2016-01-19 .. 2020-12-07, n=770
HIT_RATE = 0.374                   # 37.4% - the number a confidence level must NOT imply
AVG_WIN = 1.204
AVG_LOSS = -0.553

# The fade haircut. Full-sample buckets are scaled to the recent regime before being shown.
FADE_FACTOR = LATE_HALF_EXPECTANCY / FULL_SAMPLE_EXPECTANCY      # ~0.423

# Below this many closed trades in the narrowest contributing bucket, the level is capped at
# "thin" no matter how good the estimate looks. Same floor the tracker uses to allow tuning.
# A GUARD, not an active mechanism - see the docstring: no committed bucket is this small.
MIN_BUCKET_N = 30

# Fewer calibrated dimensions than this and the estimate is capped at "thin". This is the cap
# that fires in production, and 3 is not an arbitrary number: DTE and delta are knowable ONLY
# once a real contract has been resolved on the chain, so >=3 dimensions is precisely the
# condition "a tradable contract exists". Without one there are at most two (IV regime and term
# structure), and every bucket in these tables was measured on trades that DID have a 35-delta
# 45-75 DTE contract - quoting that expectancy for a trade nobody can place is the exact kind of
# borrowed authority this cap exists to stop.
MIN_DIMENSIONS = 3

DISCLAIMER = ("Expectancy-confidence, NOT probability of profit. The backtested hit rate is "
              "37% - most single-leg trades lose a little and a minority win big. A "
              "high-confidence alert is not a likely winner.")

# ---- bucket tables (full-sample; see module docstring for the fade discount) ---------------
# BY IV REGIME - ATM IV at entry, quartile cuts 18.1% / 33.1%.
IV_CUTS = (0.181, 0.331)
IV_BUCKETS = {
    "low (<18.1%)":      {"exp": 0.177, "n": 385},
    "mid (18.1-33.1%)":  {"exp": 0.063, "n": 770},
    "high (>=33.1%)":    {"exp": 0.115, "n": 385},
}

# BY DTE - the live band is 45-75.
DTE_BUCKETS = {
    "45-55": {"exp": 0.078, "n": 548},
    "55-65": {"exp": 0.072, "n": 519},
    "65-75": {"exp": 0.170, "n": 473},
}

# BY CONTRACT DELTA - the live target is 0.35, which lands in the best bucket. That is a
# confirmation of the existing choice, not a reason to re-open it (the 65-75 DTE refinement
# that looked equally good on this table was REJECTED on a held-out split).
DELTA_BUCKETS = {
    "<0.30":     {"exp": 0.044, "n": 192},
    "0.30-0.40": {"exp": 0.116, "n": 1125},
    ">=0.40":    {"exp": 0.096, "n": 223},
}

# BY TERM STRUCTURE - ALREADY late-half only, so exempt from the fade discount.
TERM_BUCKETS = {
    "contango":      {"exp": 0.1288, "n": 307, "derived": False},
    "backwardation": {"exp": -0.0079, "n": 449, "derived": True},
    "unknown":       {"exp": 0.0476, "n": 756, "derived": False},
}

# Level thresholds, read against the FADE-ADJUSTED estimate (i.e. a recent-regime figure).
#
# THESE CUTS ARE SET FROM THE ACHIEVABLE RANGE, and the reason is worth recording because the
# obvious choice is wrong. With the term gate ON, every alert that reaches a user is a contango
# alert, so the term bucket (+12.88%, a quarter of the mean) is effectively a CONSTANT and the
# estimate can only vary over what the other three dimensions contribute. The reachable span is
# narrow and does not start near zero:
#
#     contango       0.0511 .. 0.0812        <- what users actually see
#     backwardation  0.0170 .. 0.0470        <- suppressed by default
#
# A "high above +5%" rule - the intuitive one - would therefore label EVERY displayed alert
# "high", making the badge decorative. The cuts below split the contango span instead, so the
# scale distinguishes the alerts it is shown next to. `test_confidence_scale_actually_
# discriminates` pins that the best and worst contango fingerprints do not land on the same
# level, which is the property that keeps this honest if the tables are ever revised.
#
# This is a DISPLAY calibration, not a trading rule: it changes no alert (the term gate decides
# that) and only modulates suggested size within the capped 0.5-1.0 range in SIZE_SCALE.
LEVEL_CUTS = ((0.072, "high"), (0.058, "moderate"), (0.0, "low"))
LEVEL_AVOID = "avoid"
LEVEL_THIN = "thin"

# Sizing multiplier per level. Deliberately compressed: the spread between the best and worst
# fingerprint in the recent regime is a couple of percentage points of expectancy, which does
# not justify a 5x swing in position size on a strategy this noisy.
SIZE_SCALE = {"high": 1.0, "moderate": 0.75, "low": 0.5, "thin": 0.5, "avoid": 0.0}


def _bucket_for(value: Optional[float], table: dict, edges) -> Optional[str]:
    """Pick a bucket key by ordered numeric edges. None when the input is missing/NaN."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v != v:                       # NaN is not None and would otherwise compare False forever
        return None
    keys = list(table.keys())
    for i, edge in enumerate(edges):
        if v < edge:
            return keys[i]
    return keys[len(edges)]


def iv_bucket(atm_iv: Optional[float]) -> Optional[str]:
    return _bucket_for(atm_iv, IV_BUCKETS, IV_CUTS)


def dte_bucket(dte: Optional[float]) -> Optional[str]:
    """None outside the traded 45-75 band - an out-of-band contract has no calibration."""
    if dte is None:
        return None
    try:
        d = float(dte)
    except (TypeError, ValueError):
        return None
    if d != d or d < 45 or d > 75:
        return None
    return "45-55" if d < 55 else ("55-65" if d < 65 else "65-75")


def delta_bucket(delta: Optional[float]) -> Optional[str]:
    if delta is None:
        return None
    try:
        d = abs(float(delta))
    except (TypeError, ValueError):
        return None
    if d != d:
        return None
    return "<0.30" if d < 0.30 else ("0.30-0.40" if d < 0.40 else ">=0.40")


def term_bucket(term_ok: Optional[bool]) -> str:
    """Unknown is its own bucket, never silently treated as backwardation."""
    if term_ok is None:
        return "unknown"
    return "contango" if term_ok else "backwardation"


def cap_level(level: str, n_min: int, n_dims: int):
    """Apply the thin-evidence caps. Returns (level, reason-or-None).

    Split out from `confidence` so the narrow-bucket guard can be exercised directly: with the
    committed tables it cannot fire, and a test that quietly never reaches its assertion is
    worse than no test.
    """
    if level == LEVEL_AVOID:
        return level, None                 # a negative estimate is not made safer by thin data
    if n_dims < MIN_DIMENSIONS:
        return LEVEL_THIN, (f"only {n_dims} calibrated dimension(s) known (need "
                            f"{MIN_DIMENSIONS}) - typically means no live chain, so no "
                            f"contract, so no DTE or delta")
    if n_min < MIN_BUCKET_N:
        return LEVEL_THIN, (f"narrowest bucket has {n_min} closed trades "
                            f"(need {MIN_BUCKET_N})")
    return level, None


def confidence(atm_iv: Optional[float] = None, dte: Optional[float] = None,
               delta: Optional[float] = None, term_ok: Optional[bool] = None) -> dict:
    """Expectancy-confidence for one live alert. Never a win probability - see DISCLAIMER.

    Returns the level, the fade-adjusted estimate behind it, every contributing bucket, and the
    reason the level was capped when it was. All of it is returned so the card can show the
    working rather than an unexplained badge.
    """
    contributions = []

    ib = iv_bucket(atm_iv)
    if ib:
        contributions.append({"dim": "iv_regime", "bucket": ib,
                              "full_sample_exp": IV_BUCKETS[ib]["exp"],
                              "estimate": IV_BUCKETS[ib]["exp"] * FADE_FACTOR,
                              "n": IV_BUCKETS[ib]["n"], "fade_applied": True})
    db = dte_bucket(dte)
    if db:
        contributions.append({"dim": "dte", "bucket": db,
                              "full_sample_exp": DTE_BUCKETS[db]["exp"],
                              "estimate": DTE_BUCKETS[db]["exp"] * FADE_FACTOR,
                              "n": DTE_BUCKETS[db]["n"], "fade_applied": True})
    xb = delta_bucket(delta)
    if xb:
        contributions.append({"dim": "delta", "bucket": xb,
                              "full_sample_exp": DELTA_BUCKETS[xb]["exp"],
                              "estimate": DELTA_BUCKETS[xb]["exp"] * FADE_FACTOR,
                              "n": DELTA_BUCKETS[xb]["n"], "fade_applied": True})
    tb = term_bucket(term_ok)
    contributions.append({"dim": "term_structure", "bucket": tb,
                          "full_sample_exp": None,
                          "estimate": TERM_BUCKETS[tb]["exp"],
                          "n": TERM_BUCKETS[tb]["n"], "fade_applied": False,
                          "derived": TERM_BUCKETS[tb].get("derived", False)})

    est = sum(c["estimate"] for c in contributions) / len(contributions)
    n_min = min(c["n"] for c in contributions)

    level = LEVEL_AVOID
    for cut, name in LEVEL_CUTS:
        if est >= cut:
            level = name
            break

    level, capped = cap_level(level, n_min, len(contributions))

    return {
        "level": level,
        "expectancy_estimate": round(est, 4),
        "basis": "recent-regime (2021-2025) estimate; full-sample buckets discounted by "
                 f"{FADE_FACTOR:.3f} for the fade",
        "fade_factor": round(FADE_FACTOR, 4),
        "min_bucket_n": n_min,
        "capped_reason": capped,
        "size_scale": SIZE_SCALE[level],
        "contributions": contributions,
        "hit_rate_reference": HIT_RATE,
        "is_win_probability": False,
        "disclaimer": DISCLAIMER,
        "method": "mean of matched backtest bucket expectancies, fade-discounted; a ranking "
                  "heuristic, not a fitted per-trade expected return",
    }
