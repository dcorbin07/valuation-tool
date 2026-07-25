"""
Overfitting statistics — the reputable, published guards against fooling yourself.

Implements the Probabilistic and Deflated Sharpe Ratio (Bailey & López de Prado,
2014), which correct a backtest's Sharpe for (a) how many strategy variants you
tried, (b) sample length, and (c) skew/kurtosis. When you search many weightings,
the *best* one looks good by luck; the Deflated Sharpe tells you the probability
the edge is real anyway. Also includes the Harvey-Liu-Zhu (2016) t>3 significance
gate for newly "discovered" factors.

References:
  Bailey & López de Prado (2014), "The Deflated Sharpe Ratio."
  Harvey, Liu & Zhu (2016), "…and the Cross-Section of Expected Returns."
"""
from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()
_EULER = 0.5772156649015329


def sharpe(returns) -> float | None:
    """Per-period Sharpe (mean/std). Annualize separately if needed."""
    import numpy as np
    r = np.asarray([x for x in returns if x is not None], float)
    if len(r) < 3 or r.std(ddof=1) == 0:
        return None
    return float(r.mean() / r.std(ddof=1))


def _moments(returns):
    import numpy as np
    r = np.asarray([x for x in returns if x is not None], float)
    n = len(r)
    if n < 3:
        return n, 0.0, 3.0
    sd = r.std(ddof=1)
    if sd == 0:
        return n, 0.0, 3.0
    z = (r - r.mean()) / sd
    skew = float((z ** 3).mean())
    kurt = float((z ** 4).mean())      # normal = 3
    return n, skew, kurt


def probabilistic_sharpe_ratio(sr, n, skew=0.0, kurt=3.0, sr_benchmark=0.0):
    """P(true Sharpe > sr_benchmark) given the observed per-period Sharpe `sr`."""
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr * sr))
    if n < 2:
        return None
    z = (sr - sr_benchmark) * math.sqrt(n - 1) / denom
    return float(_N.cdf(z))


def expected_max_sharpe(n_trials, var_trials):
    """Expected maximum per-period Sharpe from N independent trials with Sharpe
    variance `var_trials` (López de Prado's estimate)."""
    if n_trials < 2 or var_trials <= 0:
        return 0.0
    a = _N.inv_cdf(1 - 1.0 / n_trials)
    b = _N.inv_cdf(1 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trials) * ((1 - _EULER) * a + _EULER * b)


def deflated_sharpe_ratio(returns, n_trials, var_trials=None, trial_sharpes=None):
    """Probability the strategy's true Sharpe > 0 after deflating for `n_trials`.
    Provide either `var_trials` (variance of the trials' Sharpes) or `trial_sharpes`."""
    sr = sharpe(returns)
    if sr is None:
        return {"deflated_sharpe": None, "note": "not enough returns"}
    n, skew, kurt = _moments(returns)
    if var_trials is None:
        import numpy as np
        var_trials = float(np.var(trial_sharpes, ddof=1)) if (trial_sharpes and len(trial_sharpes) > 1) else (sr * sr)
    sr_star = expected_max_sharpe(n_trials, var_trials)
    dsr = probabilistic_sharpe_ratio(sr, n, skew, kurt, sr_star)
    return {"sharpe_per_period": sr, "n_obs": n, "n_trials": n_trials,
            "sr_benchmark": sr_star, "deflated_sharpe": dsr,
            "real": bool(dsr is not None and dsr > 0.95),
            "note": ("Edge likely real (DSR > 0.95)" if (dsr or 0) > 0.95 else
                     "Not distinguishable from luck after multiple testing (DSR ≤ 0.95).")}


def min_track_record_length(sr, skew=0.0, kurt=3.0, sr_benchmark=0.0, prob=0.95):
    """How many periods you'd need for the Sharpe to be significant at `prob`."""
    if sr <= sr_benchmark:
        return None
    z = _N.inv_cdf(prob)
    denom = (sr - sr_benchmark) ** 2
    return 1 + (1 - skew * sr + (kurt - 1) / 4.0 * sr * sr) * (z / math.sqrt(denom)) ** 2 * denom / denom


def hlz_significant(t_stat) -> bool:
    """Harvey-Liu-Zhu: a genuinely new factor needs |t| > 3 (not 2) to survive
    multiple-testing across the 'factor zoo'."""
    return abs(t_stat) > 3.0
