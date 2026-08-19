"""
MB23 — Hodrick (1992) "1B" standard errors, as a CROSS-CHECK on this project's Newey-West
statistics. Ported from TIDEMARK's verified `tidemark/stats/hac.py`; register
`PREREG_mb22_mb23_power_and_hodrick.md`. **No TIDEMARK data crosses — only the method**, and the
method is re-derived from the published source below rather than trusted.

THE ESTIMATOR, as published. For the long-horizon predictive regression

    r_{t+1} + ... + r_{t+h}  =  a  +  b * x_t  +  e_{t+h}                         (1)

Hodrick's 1B estimates the variance of (a, b)' in (1) as

    ( SUM_t xt xt' )^-1  ( SUM_t w_{t+1} w_{t+1}' )  ( SUM_t xt xt' )^-1

    where  w_{t+1} = ( r_{t+1} - rbar ) * SUM_{i=0}^{h-1} x_{t-i},   xt = (1, x_t)'

Read the two halves against each other, because the difference between them IS the known bug:

  * the RESIDUAL is the ONE-PERIOD one, `(r_{t+1} - rbar)` — a scalar, at a single date;
  * the REGRESSOR is SUMMED over the h most recent dates, INCLUDING t.

TIDEMARK's own first implementation had these the other way round — it summed the regressors
while keeping the h-period residual — and the result was neither Hodrick nor anything else: it
returned `t ~ 0.3` at every horizon while a bootstrap against the same null returned `p ~ 0.018`.
It looked like "no evidence" and was accepted for long enough to reach a charter. Summing the
regressors is the eye-catching half of the formula and it is easy to implement that half alone.
`tests/test_mb23_hodrick.py` reconstructs the defect and pins what it does, so the failure is
recorded rather than remembered.

WHAT 1B IS AND IS NOT VALID FOR — this is not a footnote
--------------------------------------------------------
It is valid **only under the null b = 0**. Wei and Wright are explicit: it is in that case alone
that the sample variance of w consistently estimates the zero-frequency spectral density of
`x_t e_{t+h}`. So 1B answers *"can no predictability be rejected?"* and does NOT give a
trustworthy interval for a non-zero b. Their Table 1 measures the degradation: coverage falls to
**0.44 at h=48 when the true b is 0.1**, against a 0.95 nominal. The verification suite
reproduces that collapse deliberately, because an estimator that merely returned ~0.95
everywhere would pass a null-only check and be conservative-but-wrong.

VERIFICATION IS AGAINST PRINTED NUMBERS, NEVER AGAINST MY OWN EXPECTATION
-------------------------------------------------------------------------
  Min Wei and Jonathan Wright, "Confidence Intervals for Long-Horizon Predictive Regressions
  via Reverse Regressions", FEDS 2009-27, Board of Governors of the Federal Reserve System
  (published as Wei and Wright (2013), Journal of Applied Econometrics).
  Formula: section 2, p.3.  Coverage: Table 1, p.21.

Verifying an estimator against what you expect it to say is exactly the failure mode this port
exists downstream of, so it is not done that way here.

**One reading had to be established rather than assumed:** Table 1's column headings print
"beta", but the values are the DGP's `alpha` — the ONE-period slope, not the long-horizon one.
The implied long-horizon slope is `beta = alpha (1 - phi^h) / (1 - phi)`. That reading is
settled by the table's own population-R2 row, which uses only the DGP and no estimator at all,
so it is established independently of the thing being tested.

NEWEY-WEST IS NOT REIMPLEMENTED HERE
------------------------------------
`cross_check` calls the SHIPPED `statistics.hac_tstat`. A second Newey-West would make this a
comparison of two of my own functions rather than a check on the published number — audit B7's
defect class, which this record has now paid for several times. The slope-form `newey_west`
below exists only for the estimator-verification harness, where a regression with a genuine
regressor is required and no shipped Valquo function computes one.
"""

from __future__ import annotations

import numpy as np

from . import statistics as ST

__all__ = [
    "overlapping_sums", "ols", "hodrick_1b", "hodrick_1b_mean", "newey_west", "ols_se",
    "long_horizon_regression", "cross_check", "horizon_sweep", "null_calibration",
    "AGREEMENT_TOL",
]

#: `PREREG_mb22_mb23_power_and_hodrick.md` 2.3, fixed before any Hodrick number existed.
AGREEMENT_TOL = 0.10

#: `POWER_GATE.md` 5.2's CORRECTED criterion: a correctly sized estimator rejects at its
#: nominal rate. The rate, not a quantile of |t|. See `null_calibration`.
REJECTION_NOMINAL = 0.05
REJECTION_TOL = 0.015
VAR_T_TOL = 0.15


def overlapping_sums(r, h: int) -> np.ndarray:
    """`y_t = r_{t+1} + ... + r_{t+h}`, for every t at which the whole window exists.

    Given `r` of length T, returns length T-h. Element t is `r[t+1] + ... + r[t+h]` in 0-based
    terms: the h returns realised STRICTLY AFTER the date whose regressor is used, so nothing at
    or before t leaks into the dependent variable. An off-by-one here makes the regression
    partly contemporaneous and every t-statistic built on it meaningless, which is why it is
    pinned by an exact test rather than trusted.
    """
    r = np.asarray(r, dtype=float).reshape(-1)
    h = int(h)
    if h < 1:
        raise ValueError(f"h must be >= 1, got {h}")
    if len(r) <= h:
        raise ValueError(f"need more than h={h} observations, have {len(r)}")
    T = len(r)
    c = np.concatenate([[0.0], np.cumsum(r)])
    return c[h + 1:] - c[1:T - h + 1]


def _design(x) -> np.ndarray:
    """`(1, x_t)` rows."""
    x = np.asarray(x, dtype=float).reshape(-1)
    return np.column_stack([np.ones(len(x)), x])


def ols(y, X):
    """Coefficients and `(X'X)^-1`. Kept explicit so the sandwich below stays readable."""
    XtX_inv = np.linalg.inv(X.T @ X)
    return XtX_inv @ (X.T @ y), XtX_inv


def _sandwich(r: np.ndarray, X: np.ndarray, h: int):
    """THE one implementation of 1B. Both public entry points route through this.

    `X` is the full (T, k) design; the h-period sums and the alignment are done here so the
    slope form and the mean form cannot drift apart. Returns `(beta, V, n_overlapping)`.
    """
    T = len(r)
    if T <= 2 * h:
        raise ValueError(f"need more than 2h={2 * h} observations, have {T}")
    y = overlapping_sums(r, h)
    Xf = X[:T - h]
    beta, XtX_inv = ols(y, Xf)

    # w_{t+1} = (r_{t+1} - rbar) * SUM_{i=0}^{h-1} x_{t-i}
    # Rolling sum of the h most recent design rows, INCLUDING the current one.
    cum = np.vstack([np.zeros((1, X.shape[1])), np.cumsum(X, axis=0)])
    Xsum = cum[h:] - cum[:-h]              # row k = sum of X[k : k+h], i.e. window ENDING at k+h-1
    rbar = r.mean()
    t_end = np.arange(h - 1, T - 1)        # t = h-1 .. T-2, paired with the return at t+1
    eps = r[t_end + 1] - rbar
    W = Xsum[t_end - (h - 1)] * eps[:, None]
    V = XtX_inv @ (W.T @ W) @ XtX_inv
    return beta, V, int(len(y))


def hodrick_1b(r, x, h: int) -> dict:
    """1B standard errors for the h-period overlapping regression of returns on `x`.

    **The t-statistic this returns is a test of b = 0 and nothing else.** Away from that null the
    implied interval is not reliable (Wei-Wright Table 1: coverage 0.44 at h=48 when b=0.1). Do
    not put a confidence interval around a non-zero coefficient with it.

    `r[t]` is the one-period return realised over period t; `x[t]` is the predictor known at the
    END of period t. Computed WITHOUT ever forming an h-period residual — see the module
    docstring for why that sentence is the whole point.
    """
    r = np.asarray(r, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float).reshape(-1)
    if len(r) != len(x):
        raise ValueError(f"r and x must be the same length, got {len(r)} and {len(x)}")
    beta, V, n_ov = _sandwich(r, _design(x), int(h))
    se = float(np.sqrt(V[1, 1]))
    b = float(beta[1])
    return {"beta": b, "se": se, "t": (b / se) if se > 0 else float("nan"),
            "n_overlapping": n_ov, "n_independent_windows": int(n_ov // int(h)),
            "h": int(h), "estimator": "hodrick_1992_1B", "valid_only_under": "beta == 0"}


def hodrick_1b_mean(r, h: int = 1) -> dict:
    """1B specialised to a CONSTANT regressor — the form that matches Valquo's shipped tests.

    This project's H=63 headline statistics are `hac_tstat(series, lag=1)`: Newey-West t-values
    of the **mean** of a series of period returns. They are mean tests, not slope regressions.
    So the like-for-like cross-check is Hodrick's own sandwich with `x == 1`, which is what this
    computes — the same `_sandwich`, not a second implementation.

    **It scores T-h of the T observations**, because the construction pairs a window ending at t
    with the return at t+1 and there is no return after the last date. That is inherited from the
    predictive-regression setting and is reported (`n_overlapping`) rather than papered over;
    `cross_check` holds the sample fixed so the comparison isolates the estimator.
    """
    r = np.asarray(r, dtype=float).reshape(-1)
    h = int(h)
    X = np.ones((len(r), 1))
    beta, V, n_ov = _sandwich(r, X, h)
    se = float(np.sqrt(V[0, 0]))
    b = float(beta[0])
    return {"beta": b, "se": se, "t": (b / se) if se > 0 else float("nan"),
            "n_overlapping": n_ov, "h": h, "estimator": "hodrick_1992_1B_constant_regressor",
            "valid_only_under": "mean == 0"}


def ols_se(r, x, h: int) -> dict:
    """Plain OLS standard errors on the overlapping regression. The naive number."""
    r = np.asarray(r, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float).reshape(-1)
    T = len(r)
    h = int(h)
    X = _design(x)[:T - h]
    y = overlapping_sums(r, h)
    beta, XtX_inv = ols(y, X)
    e = y - X @ beta
    s2 = (e @ e) / (len(y) - X.shape[1])
    se = float(np.sqrt(s2 * XtX_inv[1, 1]))
    b = float(beta[1])
    return {"beta": b, "se": se, "t": (b / se) if se > 0 else float("nan"),
            "r2": float(1.0 - (e @ e) / ((y - y.mean()) @ (y - y.mean()))),
            "n_overlapping": int(len(y)), "estimator": "ols"}


def newey_west(r, x, h: int, lags=None) -> dict:
    """Newey-West for the SLOPE regression, lag truncation h by default.

    Here only so the verification harness can put the two estimators side by side on a regression
    with a genuine regressor. **For a MEAN test use the shipped `statistics.hac_tstat`** — that
    is the number this project publishes, and comparing against a second copy of it would be
    checking my arithmetic rather than the record's.

    Wei-Wright's Table 1 puts this estimator's coverage at 71-86% against a 95% nominal, and it
    gets WORSE as the horizon grows, which is the opposite of what a correction should do.
    """
    r = np.asarray(r, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float).reshape(-1)
    T = len(r)
    h = int(h)
    L = h if lags is None else int(lags)
    X = _design(x)[:T - h]
    y = overlapping_sums(r, h)
    beta, XtX_inv = ols(y, X)
    e = y - X @ beta
    u = X * e[:, None]
    S = u.T @ u
    for l in range(1, L + 1):
        G = u[l:].T @ u[:-l]
        S += (1.0 - l / (L + 1.0)) * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = float(np.sqrt(V[1, 1]))
    b = float(beta[1])
    return {"beta": b, "se": se, "t": (b / se) if se > 0 else float("nan"),
            "n_overlapping": int(len(y)), "lags": int(L), "estimator": "newey_west"}


def long_horizon_regression(r, x, h: int) -> dict:
    """All three side by side. Reporting only one of them is how this goes wrong."""
    o, nw, hd = ols_se(r, x, h), newey_west(r, x, h), hodrick_1b(r, x, h)
    return {"h": int(h), "beta": o["beta"], "r2": o["r2"],
            "n_overlapping": o["n_overlapping"],
            "n_independent_windows": hd["n_independent_windows"],
            "t_ols": o["t"], "t_newey_west": nw["t"], "t_hodrick_1b": hd["t"],
            "se_ols": o["se"], "se_newey_west": nw["se"], "se_hodrick_1b": hd["se"]}


def cross_check(series, lag: int = ST.DEFAULT_HAC_LAG, h: int = 1,
                tol: float = AGREEMENT_TOL) -> dict:
    """MB23's cross-check: Hodrick 1B against the SHIPPED Newey-West, on one return series.

    Reports the Newey-West statistic TWICE and requires agreement with BOTH — which is stricter
    than the register's own bar and cannot be accused of picking the flattering comparator:

      * `t_newey_west_shipped` — `hac_tstat` on every observation, i.e. the published headline;
      * `t_newey_west_same_rows` — `hac_tstat` on the T-h rows Hodrick actually scores, which
        isolates the ESTIMATOR from the one-observation sample trim the construction imposes.

    `agrees` is True only when both relative gaps sit at or under `tol`.
    """
    r = np.asarray([v for v in np.asarray(series, dtype=float).reshape(-1)
                    if v == v], dtype=float)
    h = int(h)
    hod = hodrick_1b_mean(r, h)
    t_ship = ST.hac_tstat(r, lag=lag)
    t_same = ST.hac_tstat(r[h:], lag=lag)
    out = {
        "h": h, "lag": int(lag), "n": int(len(r)), "n_hodrick_rows": hod["n_overlapping"],
        "t_hodrick_1b": hod["t"], "se_hodrick_1b": hod["se"],
        "t_newey_west_shipped": t_ship, "t_newey_west_same_rows": t_same,
        "t_naive": ST.naive_tstat(r),
        "tol": float(tol),
    }
    for key, ref in (("shipped", t_ship), ("same_rows", t_same)):
        gap = abs(hod["t"] - ref) / abs(ref) if ref else None
        out[f"relative_gap_vs_{key}"] = gap
        out[f"agrees_vs_{key}"] = (gap is not None and gap <= tol)
    out["agrees"] = bool(out["agrees_vs_shipped"] and out["agrees_vs_same_rows"])
    return out


def horizon_sweep(series, horizons=(1, 2, 3, 4, 5, 6, 7, 8),
                  lag_equals_h: bool = True) -> list:
    """DIAGNOSTIC ONLY, NO VERDICT. The two estimators across cumulative horizons.

    At `h = 1` the horizon equals the rebalance interval and the windows do not overlap; beyond
    it they do, which is `S22`'s territory. **A cell with h > 1 may NOT be quoted as a verdict
    about `S22`** — `PREREG_mb22_mb23_power_and_hodrick.md` 2.4 makes that a void condition, and
    the reason is `MB21`: `S22`'s null is separately mis-specified in a way that compounds with
    horizon, so re-scoring one half of that comparison while leaving the other alone would be
    worse than leaving both.
    """
    r = np.asarray([v for v in np.asarray(series, dtype=float).reshape(-1)
                    if v == v], dtype=float)
    rows = []
    for h in horizons:
        h = int(h)
        if len(r) <= 2 * h:
            rows.append({"h": h, "insufficient_sample": True, "n": int(len(r))})
            continue
        hod = hodrick_1b_mean(r, h)
        y = overlapping_sums(r, h)
        lag = h if lag_equals_h else ST.DEFAULT_HAC_LAG
        t_nw = ST.hac_tstat(y, lag=lag)
        rows.append({
            "h": h, "n_overlapping": hod["n_overlapping"], "hac_lag": int(lag),
            "t_hodrick_1b": hod["t"], "t_newey_west": t_nw,
            "relative_gap": (abs(hod["t"] - t_nw) / abs(t_nw)) if t_nw else None,
            "verdict": None,
            "note": "DIAGNOSTIC - carries no verdict about S22 (PREREG 2.4, MB21).",
        })
    return rows


def null_calibration(phi: float, sd: float, n: int, h: int, reps: int, seed: int) -> dict:
    """Is the estimator correctly SIZED on a simulated no-predictability null?

    Returns are iid BY CONSTRUCTION; only the regressor carries persistence. Under a
    correctly-sized estimator the Hodrick t has unit variance, so `var_t` is a direct check that
    the machinery is what it claims to be.

    **TWO criteria are returned and only one of them is the decision rule.** `POWER_GATE.md` 5.2
    records that TIDEMARK's pre-registered criterion — the 97.5th percentile of `|t|` within 10%
    of 1.96 — compares the WRONG QUANTILE: 1.96 is the 97.5th percentile of the SIGNED t, i.e.
    the 95th of `|t|`, so a correctly sized estimator gives ~2.24 and the rule flags it. Run
    against the Wei-Wright cell whose coverage is published, that criterion **fails on the
    verified case**. `agrees` therefore reflects the CORRECTED statistic — the rejection rate
    against its nominal 0.05 — and `agrees_criterion_as_committed` is carried beside it, marked,
    so the error is visible rather than quietly fixed.
    """
    rng = np.random.default_rng(int(seed))
    t_h = np.empty(int(reps))
    for i in range(int(reps)):
        e = rng.standard_normal(int(n)) * float(sd)
        if abs(phi) < 1:
            e[0] = rng.standard_normal() * float(sd) / np.sqrt(1.0 - float(phi) ** 2)
        x = np.empty(int(n))
        acc = 0.0
        for k in range(int(n)):
            acc = float(phi) * acc + e[k] if k else e[k]
            x[k] = acc
        r = rng.standard_normal(int(n))
        t_h[i] = hodrick_1b(r, x, int(h))["t"]
    var_t = float(np.var(t_h, ddof=1))
    q975 = float(np.quantile(np.abs(t_h), 0.975))
    rej = float((np.abs(t_h) > 1.96).mean())
    return {
        "phi": float(phi), "n": int(n), "h": int(h), "reps": int(reps), "seed": int(seed),
        "var_t_hodrick": var_t, "q975_abs_t_hodrick": q975, "rejection_rate_at_1_96": rej,
        "agrees": bool(abs(var_t - 1.0) <= VAR_T_TOL
                       and abs(rej - REJECTION_NOMINAL) <= REJECTION_TOL),
        "agrees_criterion_as_committed": bool(abs(var_t - 1.0) <= VAR_T_TOL
                                              and abs(q975 - 1.96) / 1.96 <= 0.10),
        "criterion": "rejection rate vs nominal 0.05 (POWER_GATE.md 5.2's CORRECTION)",
        "criterion_as_committed_note": ("q97.5 of |t| within 10% of 1.96 - MISSPECIFIED, "
                                        "fails on the verified cell, reported not used."),
    }
