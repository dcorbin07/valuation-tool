"""
Overfitting statistics — the reputable, published guards against fooling yourself.

Implements the Probabilistic and Deflated Sharpe Ratio (Bailey & López de Prado,
2014), which correct a backtest's Sharpe for (a) how many strategy variants you
tried, (b) sample length, and (c) skew/kurtosis. When you search many weightings,
the *best* one looks good by luck; the Deflated Sharpe tells you the probability
the edge is real anyway. Also includes the Harvey-Liu-Zhu (2016) multiple-testing
hurdle for newly "discovered" factors — `hlz_hurdle(N) = sqrt(2 ln N)`, which is the
ONE definition of that bar in this project (audit MA5). It is written "t > 3" in the
literature because 3.0 is sqrt(2 ln N) at N = 90; this project passed N = 90 on
2026-08-06 and the two have diverged ever since, so the derived form is the one to
quote and the constant is not carried anywhere.

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
    """Per-period Sharpe (mean/std). Annualize separately if needed.

    AUDIT MA49(b). This used to filter `None` and NOT NaN, while `_clean` below has always
    dropped both. The asymmetry was not cosmetic: a single NaN return made `r.std()` NaN, so
    the `== 0` guard was False, and the function returned **NaN rather than None** — which
    `deflated_sharpe_ratio` then carried all the way to a published `deflated_sharpe` of NaN.
    A NaN is not a verdict, and it is the one value that compares False against every bar, so
    it fails a threshold check silently instead of loudly.

    NOW DELEGATES TO `_clean`, so there is ONE definition of "a usable observation" in this
    module rather than two that disagree. Verified inert on the shipped inputs: the banked
    long-short and top-decile series carry no NaN, so this returns the same float it always
    did (pinned by test). The change is to what the NEXT NaN costs.
    """
    r = _clean(returns)
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
        # AUDIT MA49(b). This read `trial_sharpes and len(trial_sharpes) > 1`, and `and` on a
        # numpy array evaluates the array's truth value — which RAISES for any array of length
        # > 1 ("The truth value of an array with more than one element is ambiguous"). So the
        # documented `trial_sharpes` argument worked for a list and crashed for the ndarray
        # every caller in this project actually has to hand. Tested by identity and length,
        # never by truthiness; `_clean` also drops a NaN trial rather than poisoning the
        # variance with it.
        ts = _clean(trial_sharpes) if trial_sharpes is not None else None
        var_trials = float(np.var(ts, ddof=1)) if (ts is not None and len(ts) > 1) else (sr * sr)
    sr_star = expected_max_sharpe(n_trials, var_trials)
    dsr = probabilistic_sharpe_ratio(sr, n, skew, kurt, sr_star)
    # AUDIT MA49(b), second half. Dropping a NaN is the right convention — it is what every
    # other statistic in this module already does via `_clean` — but a dropped observation the
    # caller never hears about is a subset wearing the full sample's name. `n_unusable` is that
    # count, and it reads 0 on every input this project has today.
    try:
        n_unusable = int(len(list(returns)) - len(_clean(returns)))
    except TypeError:                                   # a one-shot iterator: do not consume it
        n_unusable = None
    return {"sharpe_per_period": sr, "n_obs": n, "n_trials": n_trials,
            "n_unusable": n_unusable,
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


# =============================================================================
# AUDIT MA5 — the Harvey-Liu-Zhu bar. ONE definition, DERIVED, never a constant.
# =============================================================================
# Until this block the project carried the same idea FOUR times: this module's
# `hlz_significant(t) -> |t| > 3.0` (a CONSTANT), `fundamental_panel._trials_haircut`
# and the inline `hurdle` in its `multiple_testing` block (both derived, and only
# the first floored at the research log's `N`), plus `ablation.py`'s own copy. The
# 3.0 is not a different bar from sqrt(2 ln N) — it is sqrt(2 ln N) evaluated at
# N = 90 and then frozen, so the two agree only while `N` sits near 90 and diverge
# monotonically as trials accumulate. Audit B7's defect class (three composite
# functions, one repair) with a moving target instead of a static one.
#
# `hlz_hurdle` is now the one definition and every other site delegates to it.
#
# WHY `n_trials` IS REQUIRED AND HAS NO DEFAULT. A default is what turned this
# into a constant in the first place: the caller stops thinking about `N`, the
# number goes stale silently, and the staleness runs in the FLATTERING direction
# (the hurdle only ever RISES with trials, so a frozen bar is always too easy).
# Defaulting to the research log's live count would be worse still — it would make
# a pure-arithmetic primitive read a file from disk, so a unit test of the
# ARITHMETIC would depend on the project's trial history. The caller supplies `N`.

def hlz_hurdle(n_trials) -> float:
    """sqrt(2 ln N) — the expected maximum of N standard-normal draws.  [AUDIT MA5]

    THE ONE DEFINITION of the Harvey-Liu-Zhu multiple-testing hurdle. Trying `N`
    configurations inflates the best of them by luck, and the winner must clear this
    to be believed. It is a FUNCTION OF `N`, which is exactly why a hard-coded 3.0
    cannot stand in for it: 3.0 is this expression at N = 90.

    Floored at N = 2 so the log is defined; `hlz_hurdle(1)` would be 0.0 and
    `hlz_hurdle(0)` undefined, and a hurdle of zero passes everything.
    """
    return float(math.sqrt(2.0 * math.log(max(2, int(n_trials)))))


def hlz_significant(t_stat, n_trials) -> bool:
    """Does |t| clear the Harvey-Liu-Zhu hurdle for a search of `n_trials`?  [AUDIT MA5]

    `n_trials` is REQUIRED — see the block comment above. Pass the trial count for the
    family this statistic belongs to (`research_log.trial_count(domain=...)`), not the
    project-wide total: the Deflated Sharpe and this hurdle are both corrections for
    the size of the search that produced THIS claim.
    """
    return abs(t_stat) > hlz_hurdle(n_trials)


# =============================================================================
# AUDIT M2 — cross-date inference. ONE definition, CLUSTERED BY DEFAULT.
# =============================================================================
# Before this block the project had FOUR hand-rolled naive t-stats (two in
# `fundamental_panel`, one in `engine/calibration.py`, one in the EV study) and
# the clustered figure existed only where R9 had bolted it on by hand. The
# equity lane's per-signal and per-theme IC t-stats had no clustered variant at
# ALL — including the theme IC t that carries X7's calibrated 2.71 bar.
#
# `mean_inference` is now the one definition. Its unqualified `t` is the HAC
# (clustered) statistic; the i.i.d. figure is carried beside it, explicitly
# labelled a diagnostic; and `n_eff` travels with `n`, which is M2's third
# requirement and the one nothing in the equity lane did.
#
# WHAT THIS DELIBERATELY DOES NOT DO (PREREG_m2_m6.md §2): it does not redefine
# any existing key. `long_short_tstat` is read by `holdout_compare_panels`,
# whose +0.25 margin was committed against the NAIVE statistic, and the placebo
# floors (naive 2.1437 / HAC 2.2837) are specific to both the statistic AND the
# lag. Redefining in place would silently re-quote every verdict those gates
# ever produced. Clustered is the default here by being what this function
# returns as `t` — not by moving the record.

DEFAULT_HAC_LAG = 1


def _clean(series):
    """The usable observations, as a float array. None and NaN dropped."""
    import numpy as np
    return np.asarray([x for x in series if x is not None and x == x], dtype=float)


def naive_tstat(series):
    """i.i.d. t-statistic of a series' mean against zero. DIAGNOSTIC ONLY.

    Kept as a named, importable function precisely so that the assumption is
    visible at every call site rather than reimplemented inline for the fifth time.
    """
    import numpy as np
    s = _clean(series)
    if len(s) < 2:
        return None
    sd = float(np.std(s, ddof=1))
    return float(np.mean(s) / (sd / np.sqrt(len(s)))) if sd > 0 else None


def hac_tstat(series, lag=DEFAULT_HAC_LAG):
    """AUDIT R9 — Newey-West (Bartlett) HAC t-statistic of the mean against zero.

    The 63-day windows genuinely do not overlap, so the naive t is defensible on the
    OVERLAP dimension. It is not defensible on autocorrelation: factor spreads are
    serially correlated and regime-dependent. Same estimator `scripts/factor_alpha.py`
    uses for R1 on a mean-only design, so the two lanes report comparable inference.
    """
    import numpy as np
    s = _clean(series)
    n = len(s)
    if n < 3:
        return None
    e = s - s.mean()                       # residuals of a mean-only regression
    g0 = float(e @ e) / n
    S_hac = g0
    for L in range(1, min(int(lag), n - 1) + 1):
        gL = float(e[L:] @ e[:-L]) / n
        S_hac += 2.0 * (1.0 - L / (lag + 1.0)) * gL      # Bartlett kernel
    if S_hac <= 0:
        return None
    se = np.sqrt(S_hac / n)
    return float(s.mean() / se) if se > 0 else None


def chi2_sf(x, k):
    """Upper-tail chi-square probability. Series expansion for the regularised lower
    incomplete gamma P(k/2, x/2); adequate at the small dfs used here and avoids a
    scipy dependency this project does not otherwise carry."""
    if x <= 0 or k <= 0:
        return 1.0
    a, xx = k / 2.0, x / 2.0
    if xx > a + 40.0:                       # far tail — P ~ 1, report a floor rather than 0.0
        return 1e-12
    term = 1.0 / math.gamma(a + 1.0)
    total = term
    for i in range(1, 512):
        term *= xx / (a + i)
        total += term
        if term < total * 1e-15:
            break
    p_lower = total * math.exp(-xx + a * math.log(xx))
    return float(min(1.0, max(0.0, 1.0 - p_lower)))


def ljung_box(series, lags=4):
    """AUDIT R9 — Ljung-Box Q, so the independence assumption is VISIBLE.

    A small p means the series is serially correlated and the naive i.i.d. t
    overstates significance — which is the whole reason the HAC t is the default.
    """
    s = _clean(series)
    n = len(s)
    lags = int(min(lags, n - 2))
    if n < 8 or lags < 1:
        return None
    e = s - s.mean()
    denom = float(e @ e)
    if denom <= 0:
        return None
    acf, q = [], 0.0
    for L in range(1, lags + 1):
        r = float(e[L:] @ e[:-L]) / denom
        acf.append(r)
        q += (r * r) / (n - L)
    q *= n * (n + 2)
    return {"q": float(q), "df": lags, "acf": [float(x) for x in acf],
            "p_value": chi2_sf(float(q), lags),
            "lag1_autocorr": (float(acf[0]) if acf else None)}


# --------------------------------------------------------- S28: distribution, not just the mean
def distribution(values, dates=None) -> dict:
    """The SHAPE of a per-period series, beside the mean the payload already publishes.

    LEDGER S28. Every headline this project ships is a mean, or a t on a mean, and a mean is the
    one summary that cannot show a book being carried by three quarters out of sixty-nine. This
    adds quantiles and the DATED worst/best periods. It is REPORTING ONLY: no new claim, no
    threshold, no verdict, and nothing here gates anything.

    THE UNITS ARE PER-PERIOD AND THE BLOCK SAYS SO. These are 63-trading-day draws, not annual
    figures. `top_decile_alpha` is `ppy * mean(alpha)`; a QUANTILE may NOT be scaled that way,
    because annualising is a statement about a mean and not about an order statistic. The block
    carries a `units` string so a figure cannot be picked up without it.
    """
    s = _clean(values)
    if not len(s):
        return {"n": 0, "units": "per-period (not annualised)"}

    srt = sorted(float(x) for x in s)
    n = len(srt)

    def q(p):
        if n == 1:
            return srt[0]
        i = p * (n - 1)
        lo = int(i)
        hi = min(lo + 1, n - 1)
        return srt[lo] + (srt[hi] - srt[lo]) * (i - lo)

    mean = sum(srt) / n
    var = sum((x - mean) ** 2 for x in srt) / (n - 1) if n > 1 else 0.0
    neg = sum(1 for x in srt if x < 0)
    out = {
        "n": n,
        "units": ("per-period (not annualised) - a quantile is an order statistic and may not "
                  "be scaled by periods-per-year the way a mean is"),
        "mean": mean, "sd": var ** 0.5,
        "min": srt[0], "p05": q(0.05), "p25": q(0.25), "median": q(0.50),
        "p75": q(0.75), "p95": q(0.95), "max": srt[-1],
        "negative_periods": neg, "negative_fraction": neg / n,
    }

    # The DATED extremes. `_clean` may drop non-finite entries, so the dates are matched against
    # the ORIGINAL series rather than against the cleaned one - pairing a cleaned value with an
    # uncleaned date is exactly how an off-by-one mislabels the worst quarter in the record.
    if dates is not None:
        pairs = [(d, float(v)) for d, v in zip(dates, values)
                 if v is not None and v == v and abs(float(v)) != float("inf")]
        if pairs:
            w = min(pairs, key=lambda p: p[1])
            b = max(pairs, key=lambda p: p[1])
            out["worst"] = {"date": str(w[0]), "value": w[1]}
            out["best"] = {"date": str(b[0]), "value": b[1]}
            out["n_dated"] = len(pairs)
    return out


def auto_lag(n):
    """Schwert/Greene automatic HAC truncation lag: floor(4*(n/100)^(2/9)).

    M2 asks for the lag to come from the series rather than from convention. It is
    REPORTED here and deliberately NOT adopted as the shipped figure: at n = 69 this
    returns 3, and moving the published HAC t off lag 1 would both change the record
    and invalidate the placebo floor (2.2837) that was calibrated at lag 1.
    """
    n = int(n)
    if n < 3:
        return 0
    return max(1, int(math.floor(4.0 * (n / 100.0) ** (2.0 / 9.0))))


def effective_n(n, rho):
    """AR(1) effective sample size, n·(1−rho)/(1+rho), clipped to [1, n].

    An ESTIMATE off a single autocorrelation coefficient, not a measurement with a
    null behind it — R3's rule ("a raw design effect is not evidence of clustering")
    applies to it, which is why the rho it was built from is always reported beside
    it. Clipped at n because negative autocorrelation IMPROVES precision, and letting
    n_eff exceed n would turn a favourable property into a manufactured bonus.
    """
    if n is None or n < 1 or rho is None or rho != rho:
        return None
    r = max(-0.999, min(0.999, float(rho)))
    return float(max(1.0, min(float(n), n * (1.0 - r) / (1.0 + r))))


def mean_inference(series, lag=DEFAULT_HAC_LAG, ljung_lags=4) -> dict | None:
    """THE cross-date inference function. Clustered (HAC) by default.

    `t` is the HAC statistic. `t_naive` is the i.i.d. one, carried for continuity and
    diagnosis, never as the headline. `n_eff` travels with `n`. `auto_lag`/`t_auto_lag`
    report what a data-driven lag would give WITHOUT adopting it.
    """
    s = _clean(series)
    n = int(len(s))
    if n < 2:
        return None
    lb = ljung_box(s, lags=ljung_lags)
    rho = (lb or {}).get("lag1_autocorr")
    al = auto_lag(n)
    return {
        "t": hac_tstat(s, lag=lag),
        "method": "newey_west_hac",
        "lag": int(lag),
        "lag_source": "fixed",
        "n": n,
        "n_eff": effective_n(n, rho),
        "autocorr_lag1": rho,
        "t_naive": naive_tstat(s),
        "naive_note": ("DIAGNOSTIC ONLY — assumes i.i.d. periods. Quote `t`. "
                       "Existing *_tstat keys remain naive for record continuity "
                       "(PREREG_m2_m6.md §2)."),
        "ljung_box": lb,
        "auto_lag": al,
        "t_auto_lag": hac_tstat(s, lag=al),
        "auto_lag_note": ("REPORTED, NOT ADOPTED — adopting it would move the published "
                          "HAC t and invalidate the placebo floor calibrated at lag 1."),
    }


# ------------------------------------------------------------------------------------------
# AUDIT R4 — false-discovery control across a FAMILY of tests
# ------------------------------------------------------------------------------------------

def two_sided_p(t) -> float | None:
    """Two-sided p from a t statistic, normal approximation.

    A 69-date IC series has df in the sixties, where the normal and the exact t differ by
    <1e-3 — and BH decides on the ORDERING of p, which is invariant to any strictly monotone
    transform, so the approximation cannot change which hypotheses are rejected.
    """
    if t is None:
        return None
    t = float(t)
    if t != t or t in (float("inf"), float("-inf")):
        return None
    return float(math.erfc(abs(t) / math.sqrt(2.0)))


def benjamini_hochberg(pvals, q: float = 0.05) -> list:
    """Benjamini–Hochberg step-up, returning the reject vector in the INPUT order.

    AUDIT R4 asked for this "across the family of *equity* signal tests, as the options
    autopsy already does for its 126 features". It had never existed on the equity side: BH
    was implemented three separate times in the OPTIONS lane (`tickflow_signals`,
    `s17_event_codes`, `path_gate`) and nowhere else. This is the shared definition, so a
    fourth copy is not what closes R4 — that would be audit B7's defect class, three copies
    of a formula that must agree. **Consolidating the existing three is the options lane's
    to do; this does not touch them.**

    STEP-UP, NOT STEP-DOWN, and the distinction decides discoveries: rejections run to the
    LARGEST k with p(k) <= q·k/m, so every hypothesis ranked above a qualifying one is
    rejected even where it fails its own threshold. An implementation that stops at the first
    failure is the step-DOWN procedure and is strictly less powerful. Pinned against
    Benjamini and Hochberg's own 1995 worked example (m=15, q=0.05 → exactly 4 rejections).

    `None`/NaN entries never reject and never enter the denominator's ordering.
    """
    idx = [i for i, p in enumerate(pvals)
           if p is not None and isinstance(p, (int, float)) and p == p]
    rej = [False] * len(pvals)
    if not idx:
        return rej
    order = sorted(idx, key=lambda i: pvals[i])
    m = len(order)
    k_max = 0
    for rank, i in enumerate(order, start=1):
        if pvals[i] <= q * rank / m:
            k_max = rank
    for rank, i in enumerate(order, start=1):
        if rank <= k_max:
            rej[i] = True
    return rej
