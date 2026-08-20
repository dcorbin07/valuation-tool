"""I-1 - Breeden-Litzenberger risk-neutral densities from the PINNED frozen chains.

    from valuation.studies.rnd import build_slice, TAIL_THRESHOLDS
    res = build_slice(cross_section, spot=raw_close, asof=d, expiry=e, symbol="AAPL")
    res.tail_mass[0.50]          # Q(S_T <= 0.50 * spot), risk-neutral
    res.usable                   # the ONLY thing to branch on; res.reasons says why not

WHAT THIS IS. An INSTRUMENT. It turns one (name, date, expiry) option cross-section into an
estimated risk-neutral density over the terminal underlying price, and reads its left-tail mass
at pre-declared thresholds. It is infra: it charges ZERO trials and it decides nothing.

WHAT IT IS NOT, AND THIS IS ENFORCED RATHER THAN PROMISED. It computes NO relationship between
any RND quantity and any forward RETURN. Not a correlation, not an IC, not a bucketed mean - the
module never reads a realized outcome at all. The reason is that this instrument's neutrality is
its whole value: it is consumed by `PREREG_DRAFT_o1_flagged_puts.md` as a **stage-0 kill that
must fire before any arm exists**, so if the builder had already been pointed at returns, the
kill would be scored on a tool that had seen the answer. `tests/test_rnd.py` sweeps this module's
own source for the forbidden vocabulary and fails on a match. RND crash-content is
mixed-to-contested in the literature (J. Empirical Finance 2018); nothing here adjudicates that,
and a number this module returns is a statement about option PRICES, never about what happened.

-------------------------------------------------------------------------------------------
THE METHOD, AND THE TWO PLACES IT DEPARTS FROM SR-677 - BOTH MEASURED, NEITHER PREFERRED BLIND
-------------------------------------------------------------------------------------------
The skeleton is Malz, NY Fed Staff Report 677 (2014), "A Simple and Reliable Way to Compute
Option-Based Risk-Neutral Distributions", which the scout's citation names as the standard
stable implementation:

  1. Prices -> implied vols per strike, in FORWARD (Black-76) space, OTM side only.
  2. Fit a SMOOTH smile.
  3. Extrapolate the smile beyond the quoted range in a way that keeps the tails lognormal.
  4. Re-price on a fine strike grid; Breeden-Litzenberger (1978) by finite difference.

     f(K) = e^{rT} d2C/dK2        F(K) = 1 + e^{rT} dC/dK        F(K) = e^{rT} dP/dK

SR-677 does step 2 in DELTA space and step 3 by holding vol FLAT. Both were implemented
literally first, run on the frozen equity chains, and both broke. The two changes below were
adopted only after the literal version was measured to fail, and each is justified by a
measurement rather than by preference:

  * **DEPARTURE 1 - the abscissa is log-moneyness ln(K/F), not delta.** Delta is a fine
    coordinate for FX, where SR-677 is aimed: quotes arrive at five well-separated deltas. On a
    dense equity chain with a steep skew the delta->strike map is NOT INVERTIBLE - measured on
    AAPL 2025-07-07, 7 folding steps at delta 0.0059-0.0074 where K doubles back through
    265-270. Sorting by K and de-duplicating then silently discards the folded branch, leaving a
    jump in vol(K) that Breeden-Litzenberger turns into a density spike of -0.90 against a peak
    of +0.72. `ln(K/F)` is monotone in K by construction, so the fold cannot occur at all -
    the failure is removed structurally rather than detected and patched.

  * **DEPARTURE 2 - the wings are SMOOTH-PASTED, not clamped flat.** This is the more important
    one and the reason is arithmetic, not taste. The density depends on the smile's SECOND
    derivative through the vega term (d2C/dK2 carries `C_sigma * sigma''`). Clamping vol flat
    at the last quote puts a STEP in sigma' at each seam, and a step in sigma' is a DELTA
    FUNCTION in sigma'' - so flat extrapolation manufactures a negative density spike at both
    edges whenever the smile has any slope there, which an equity skew always does. Instead the
    edge slope decays exponentially,

        sigma(x) = sigma_e + slope_e * L * (1 - exp(-|x - x_e| / L))

    which is C1 at the seam (no delta function) and ASYMPTOTICALLY CONSTANT, so the far tails
    stay lognormal - the property flat extrapolation existed to provide, kept without the kink.

  * **The smile fit is a SPREAD-WEIGHTED smoothing spline, fitted to the quotes' own precision
    and no tighter.** Each point's vol uncertainty is measured by solving IV at the bid and at
    the ask; the spline is weighted by it with the standard chi-square target `s = n`. This is
    what lets one rule serve both a 31-quote AAPL chain and a 9-quote ABBV chain: interpolating
    every point exactly puts quote noise straight into sigma'' and rings, while a rigid
    polynomial cannot follow a real skew. Measured, the weighted spline beats a cubic polynomial
    on BOTH axes at once - see VERIFICATION.

-------------------------------------------------------------------------------------------
WHY THE FORWARD COMES FROM PARITY, AND THE TRAP THAT WOULD HAVE MADE ITS CHECK VACUOUS
-------------------------------------------------------------------------------------------
The parity forward embeds the market's own dividend and borrow assumptions, so it needs no
dividend estimate. It is a robust median over near-the-money matched strikes where BOTH legs
pass `usable_quote`.

`dividends.spot_from_parity` returns S = C - P + K*exp(-rT). Deriving the forward from parity
and then "checking" it against a spot derived from parity is TRUE BY CONSTRUCTION - MA31 named
that failure by name. The check here is against `raw_close` from the bars, an INDEPENDENT
series, and that is what makes it a check.

`raw_close`, NEVER `close`. Strikes are as-traded; `close` is split- and dividend-adjusted. NVDA
2012 reads 0.27 adjusted against a raw 11.97, a 43x ratio, and matching an as-traded strike to an
adjusted spot picks a contract nowhere near the money and FAILS SILENTLY - the option still
prices, it is simply mostly intrinsic (`U1-SPLIT`, `O6`). The parity-vs-raw_close diagnostic is
the tripwire: an adjustment mismatch throws it by tens of percent, far outside any spread band,
so the check's real job is catching a corporate action, not auditing dividends.

-------------------------------------------------------------------------------------------
SPARSE WINGS - THE INTERPOLATION AND ITS FAILURE MODE, STATED RATHER THAN DISCOVERED
-------------------------------------------------------------------------------------------
Beyond the outermost quote the smile is the smooth-pasted continuation above, which asymptotes
to a constant vol - so the estimated far tail is a LOGNORMAL tail. Consequences, both of which
travel with every number this module returns:

  * A tail mass whose threshold lies BELOW the lowest usable strike is an EXTRAPOLATION, not a
    measurement. Every slice reports `threshold_extrapolated` per threshold and `build_slice`
    will not hide it. On the frozen chains this is common at 0.50 and rare at 0.80.
  * The error is ONE-DIRECTIONAL. A real equity smile keeps steepening into the left wing; the
    pasted continuation flattens it, so an extrapolated left-tail mass is a LOWER BOUND on what
    a still-steepening smile would imply. For a consumer asking whether the market UNDER-prices
    a crash, that is the conservative direction: it biases toward "the market charges less than
    it really does", making an "already priced" verdict harder to reach, not easier.

QUOTE VALIDITY. `usable_quote` on BOTH legs, the ONE shipped definition (`MA45`), never a local
copy. A one-sided quote yields an IV from ask/2 - a number, never an error, and wrong. Rows are
dropped and COUNTED, never silently imputed.

SOURCE. The pinned freeze resolver only (`chain_store.resolve_chains` / `resolve_harvest`), which
RAISES rather than falling back. The mutable store is `O16`'s defect - 44.2% of its payload units
were rewritten after the books were banked - and may not serve a register.

-------------------------------------------------------------------------------------------
VERIFICATION - against closed forms, because that is the only honest test of an estimator
-------------------------------------------------------------------------------------------
`tests/test_rnd.py` scores this against densities whose tail mass is known ANALYTICALLY:

  * a flat smile must return the Black-Scholes lognormal, tail mass exactly N(-d2);
  * a two-lognormal MIXTURE - Bahra, Bank of England WP 66 (1997), the canonical published RND
    test case - must be recovered from analytically priced options, skew and all.

The mixture is the one that matters. A lognormal is the case a broken estimator still gets
right, so an estimator tested only against it has not been tested. The measured control: on the
mixture at the 0.70 threshold the true mass is 0.10715, a single lognormal at the ATM vol says
0.03386, and this estimator returns 0.10716 - it recovers a tail a lognormal understates
threefold.

Selection was made on those benchmarks plus real-chain stability, never on anything downstream:
spread-weighted spline vs cubic polynomial, max mixture error 7.0e-3 vs 1.6e-2 AND real-chain
clean-density share 0.913 vs 0.812. Better on both axes, so the choice needed no trade-off.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from scipy.interpolate import UnivariateSpline

from valuation.edge.blackscholes import bs_price, implied_vol, usable_quote

# ---------------------------------------------------------------------------------------------
# Pre-declared thresholds. FIXED HERE, BEFORE ANY SLICE IS BUILT, so a consumer cannot choose a
# threshold after seeing a density. 0.50 is the risk-neutral analogue of MA28's crash event
# (>50% quarterly fall) and is the one PREREG_DRAFT_o1_flagged_puts.md K2 reads; 0.70 is the
# moneyness its section 3 targets. The rest bracket them so a reader can see the shape.
# ---------------------------------------------------------------------------------------------
TAIL_THRESHOLDS: Tuple[float, ...] = (0.50, 0.60, 0.70, 0.80, 0.90)

METHOD = ("Breeden-Litzenberger on a spread-weighted smoothing smile in log-moneyness with "
          "C1 smooth-pasted wings (Malz FRBNY SR-677 skeleton; two measured departures)")
CITATIONS = (
    "Breeden & Litzenberger (1978), J. Business 51(4)",
    "Malz (2014), FRBNY Staff Report 677",
    "Bahra (1997), Bank of England Working Paper 66 (two-lognormal mixture benchmark)",
)

# --------------------------------------------------------------------------- fit-quality bars
# Pre-declared. A slice failing any of them is UNUSABLE and says which; nothing is clipped into
# looking healthy.
INTEGRAL_TOL = 0.02          # RND integrates to 1 +/- this (O-1's K1)
MAX_NEG_MASS = 0.01          # tolerated |negative density| mass before the slice is refused
MONOTONE_TOL = 1e-9          # the READ REGION is held to floating-point monotonicity
MIN_SMILE_POINTS = 5         # Malz's FX case runs on 5 quotes; below that there is no fit
MIN_DTE_DAYS = 7             # under a week, discretization noise dominates the density
MAX_DTE_DAYS = 400
GRID_N = 2001                # odd, so a central difference has a true centre
GRID_SIGMAS = 10.0           # grid half-width in units of sigma*sqrt(T) around the forward
ATM_BAND = 0.15              # |K/F - 1| <= this defines "near the money" for the parity forward

# --------------------------------------------------------------------------- smile-fit constants
# SMOOTH_S_MULT = 1.0 is the standard chi-square criterion s = n for a weighted smoothing spline:
# fit to within the quotes' own precision and no tighter. It was checked to sit on a PLATEAU
# rather than at a tuned edge - 1.0, 2.0 and 4.0 all return the same real-chain pass rates - so
# the instrument is not balanced on this number.
SMOOTH_S_MULT = 1.0
# PASTE_L is the decay length of the wing slope, in log-moneyness units: the edge slope has
# decayed by 1/e one factor exp(L) out in strike. 0.5 was taken because pass rates rise steeply
# from 0.10 to 0.50 and flatten after; smaller values leave a sharper seam.
PASTE_L = 0.50
# Vol is clipped to the range the shipped solver can invert, so a runaway wing cannot produce a
# price the pricer would refuse.
VOL_FLOOR, VOL_CEIL = 0.01, 5.0
# Fallback IV uncertainty when one side of a quote will not solve, as a fraction of the mid IV.
FALLBACK_IV_FRAC = 0.05


@dataclass
class RNDSlice:
    """One (name, date, expiry) density, its tail masses, and its own fit diagnostics.

    `usable` is the ONLY thing a consumer should branch on. It is False whenever any
    pre-declared fit bar failed, and `reasons` says which - so a refusal is always attributable
    and never reads as an absence of data.
    """
    symbol: str
    asof: Optional[pd.Timestamp] = None
    expiry: Optional[pd.Timestamp] = None
    spot: Optional[float] = None
    forward: Optional[float] = None
    t_years: Optional[float] = None
    rate: Optional[float] = None
    strikes: Optional[np.ndarray] = None
    density: Optional[np.ndarray] = None
    cdf: Optional[np.ndarray] = None
    tail_mass: Dict[float, float] = field(default_factory=dict)
    threshold_extrapolated: Dict[float, bool] = field(default_factory=dict)
    diagnostics: Dict[str, object] = field(default_factory=dict)
    reasons: Tuple[str, ...] = ()
    usable: bool = False

    def summary(self) -> dict:
        """A JSON-safe row. The diagnostics travel WITH the numbers, never in a separate file."""
        return {
            "symbol": self.symbol,
            "asof": None if self.asof is None else str(pd.Timestamp(self.asof).date()),
            "expiry": None if self.expiry is None else str(pd.Timestamp(self.expiry).date()),
            "spot": self.spot,
            "forward": self.forward,
            "t_years": self.t_years,
            "usable": self.usable,
            "reasons": list(self.reasons),
            "tail_mass": {str(k): v for k, v in sorted(self.tail_mass.items())},
            "threshold_extrapolated": {str(k): v for k, v
                                       in sorted(self.threshold_extrapolated.items())},
            "diagnostics": dict(self.diagnostics),
            "method": METHOD,
        }


# ---------------------------------------------------------------------------------------------
# Analytic references. These are the BENCHMARKS the estimator is tested against, and they live
# in the module (not the test file) for one reason: a benchmark written inside the test that
# consumes it can drift into agreeing with the implementation. These are closed forms from the
# literature and depend on nothing above them.
# ---------------------------------------------------------------------------------------------
def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(float(x) / math.sqrt(2.0)))


def lognormal_tail_mass(spot: float, strike: float, t: float, r: float, sigma: float,
                        q: float = 0.0) -> float:
    """Q(S_T <= K) under Black-Scholes. EXACTLY N(-d2) - the textbook closed form.

    This is the analytic truth a flat smile must reproduce. Note it is N(-d2) and NOT N(-d1):
    N(-d2) is the risk-neutral PROBABILITY of finishing below K, while N(-d1) is a
    delta-weighted quantity. Confusing them is the classic error, which is why this has its own
    name rather than being inlined at a call site.
    """
    if t <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        raise ValueError("lognormal_tail_mass needs positive spot, strike, t, sigma")
    d2 = (math.log(spot / strike) + (r - q - 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    return _norm_cdf(-d2)


def mixture_lognormal_tail_mass(weights: Sequence[float], forwards: Sequence[float],
                                sigmas: Sequence[float], t: float, strike: float) -> float:
    """Q(S_T <= K) for a weighted mixture of lognormals (Bahra 1997, BoE WP 66).

    Component i has E[S_T] = forwards[i] and log-volatility sigmas[i]*sqrt(t). A mixture's CDF is
    the weighted sum of component CDFs - the property that makes this the canonical published
    benchmark for an RND estimator, because the density is genuinely skewed and fat-tailed while
    its tail mass stays exact.
    """
    w = np.asarray(weights, dtype=float)
    f = np.asarray(forwards, dtype=float)
    s = np.asarray(sigmas, dtype=float)
    if w.shape != f.shape or w.shape != s.shape:
        raise ValueError("mixture parameters must be the same length")
    if abs(float(w.sum()) - 1.0) > 1e-12:
        raise ValueError("mixture weights must sum to 1")
    if strike <= 0 or t <= 0:
        raise ValueError("mixture_lognormal_tail_mass needs positive strike and t")
    tot = 0.0
    for wi, fi, si in zip(w, f, s):
        vol = si * math.sqrt(t)
        # component median is fi*exp(-vol^2/2) so that its mean is exactly fi
        d2 = (math.log(fi / strike) - 0.5 * vol * vol) / vol
        tot += float(wi) * _norm_cdf(-d2)
    return tot


def mixture_lognormal_call(weights: Sequence[float], forwards: Sequence[float],
                           sigmas: Sequence[float], t: float, r: float, strike: float) -> float:
    """Black-76 call under the same mixture, discounted at r.

    A mixture of lognormals prices as the weighted sum of Black-76 calls on each component - the
    other half of why Bahra's mixture is the right test case: the estimator can be fed EXACT
    prices with no simulation noise, so any error the test finds is the estimator's own.
    """
    w = np.asarray(weights, dtype=float)
    tot = 0.0
    for wi, fi, si in zip(w, np.asarray(forwards, float), np.asarray(sigmas, float)):
        vol = si * math.sqrt(t)
        d1 = (math.log(fi / strike) + 0.5 * vol * vol) / vol
        d2 = d1 - vol
        tot += float(wi) * (fi * _norm_cdf(d1) - strike * _norm_cdf(d2))
    return math.exp(-r * t) * tot


# ---------------------------------------------------------------------------------------------
# The forward, from put-call parity on matched strikes
# ---------------------------------------------------------------------------------------------
def forward_from_parity(xs: pd.DataFrame, t: float, r: float,
                        spot_hint: Optional[float] = None) -> Tuple[Optional[float], dict]:
    """Median parity forward over near-the-money matched strikes, plus its own diagnostics.

    C - P = e^{-rT}(F - K)  =>  F = K + e^{rT}(C - P), per matched strike.

    BOTH legs must pass `usable_quote`; a matched pair with one dead leg is not a pair. The
    median over the near-the-money band is used rather than a single strike because parity noise
    is worst where the legs are least liquid, and one ATM strike would put the whole forward on
    one quote.
    """
    need = ("strike", "right", "bid", "ask")
    for c in need:
        if c not in xs.columns:
            return None, {"error": "missing column %r" % c}
    d = xs.copy()
    d["right"] = d["right"].astype(str).str.upper().str[0]
    ok = [usable_quote(b, a) for b, a in zip(d["bid"], d["ask"])]
    d = d.loc[np.asarray(ok, dtype=bool)]
    if d.empty:
        return None, {"error": "no usable quotes", "n_pairs": 0}
    d["mid"] = (d["bid"].astype(float) + d["ask"].astype(float)) / 2.0
    d["half_spread"] = (d["ask"].astype(float) - d["bid"].astype(float)) / 2.0
    calls = d[d["right"] == "C"].drop_duplicates("strike").set_index("strike")
    puts = d[d["right"] == "P"].drop_duplicates("strike").set_index("strike")
    common = calls.index.intersection(puts.index)
    if len(common) == 0:
        return None, {"error": "no matched call/put strikes with two usable legs", "n_pairs": 0}
    k = np.asarray(common, dtype=float)
    cm = calls.loc[common, "mid"].to_numpy(dtype=float)
    pm = puts.loc[common, "mid"].to_numpy(dtype=float)
    band = calls.loc[common, "half_spread"].to_numpy(dtype=float) + \
        puts.loc[common, "half_spread"].to_numpy(dtype=float)
    fwd_all = k + math.exp(r * t) * (cm - pm)

    anchor = float(spot_hint) if spot_hint else float(np.median(fwd_all))
    sel = np.abs(k / anchor - 1.0) <= ATM_BAND
    if not sel.any():                       # nothing near the money; fall back to all pairs
        sel = np.ones_like(k, dtype=bool)
    fwd = float(np.median(fwd_all[sel]))
    diag = {
        "n_pairs": int(len(k)),
        "n_pairs_atm": int(sel.sum()),
        "forward": fwd,
        "forward_dispersion": float(np.std(fwd_all[sel])) if sel.sum() > 1 else 0.0,
        # The band the parity relation is entitled to: the summed half-spreads of the legs used.
        # DERIVED from the quotes, never an invented tolerance.
        "parity_band": float(np.median(band[sel])),
    }
    return fwd, diag


# ---------------------------------------------------------------------------------------------
# Step 1 - prices to implied vols, WITH each point's own uncertainty
# ---------------------------------------------------------------------------------------------
def smile_points(xs: pd.DataFrame, forward: float, t: float,
                 r: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    """Return (strikes, vols, vol_sigmas, diagnostics) for the OTM option at each usable strike.

    OTM ONLY, AND THAT IS THE STANDARD CHOICE RATHER THAN A PREFERENCE. An ITM option is mostly
    intrinsic, so its extrinsic value - the only part carrying vol information - is a small
    difference of two large numbers and its implied vol is correspondingly noisy. Every published
    implementation uses the OTM wing on each side; taking both rights at one strike would also
    double-count, since parity makes them redundant.

    THE UNCERTAINTY IS MEASURED, NOT ASSUMED. `vol_sigma` is half the IV bracket implied by the
    quote itself - solve at the bid, solve at the ask, halve the difference. That is what lets
    the fit be flexible where the market is tight and stiff where it is wide, without anybody
    choosing a smoothing constant per name.

    WORKING IN FORWARD (BLACK-76) SPACE, VIA THE SHIPPED PRICER. `bs_price(S=F*exp(-rT), ..., q=0)`
    is identically the Black-76 price: substituting S = F*exp(-rT) into d1 cancels the rT term and
    leaves d1 = [ln(F/K) + sigma^2 T/2]/(sigma sqrt(T)). So the shipped Black-Scholes solver is
    reused as-is rather than a second pricer being written beside it - audit B7's defect class.
    """
    s_eff = forward * math.exp(-r * t)          # Black-76 as BS-with-q=0; see docstring
    d = xs.copy()
    d["right"] = d["right"].astype(str).str.upper().str[0]
    n_raw = int(len(d))
    ok = np.asarray([usable_quote(b, a) for b, a in zip(d["bid"], d["ask"])], dtype=bool)
    n_unusable = int((~ok).sum())
    d = d.loc[ok]
    empty = (np.array([]), np.array([]), np.array([]))
    if d.empty:
        return (*empty, {"n_raw": n_raw, "n_unusable_quote": n_unusable, "n_smile": 0,
                         "n_iv_failed": 0, "k_min": None, "k_max": None,
                         "median_vol_sigma": None, "n_sigma_fallback": 0})
    strike_f = d["strike"].astype(float)
    otm = ((d["right"] == "C") & (strike_f >= forward)) | \
          ((d["right"] == "P") & (strike_f < forward))
    d = d.loc[otm]
    # One row per strike; if both rights somehow survive, keep the first deterministically.
    d = d.sort_values(["strike", "right"]).drop_duplicates(subset=["strike"], keep="first")

    ks, vols, sigs = [], [], []
    n_iv_failed, n_fallback = 0, 0
    for k, right, b, a in zip(d["strike"].astype(float), d["right"],
                              d["bid"].astype(float), d["ask"].astype(float)):
        mid = 0.5 * (float(b) + float(a))
        iv = implied_vol(mid, s_eff, float(k), t, r, right=str(right), q=0.0)
        if iv is None or not math.isfinite(iv) or iv <= 0:
            n_iv_failed += 1
            continue
        iv_b = implied_vol(float(b), s_eff, float(k), t, r, right=str(right), q=0.0)
        iv_a = implied_vol(float(a), s_eff, float(k), t, r, right=str(right), q=0.0)
        if iv_b and iv_a and iv_a > iv_b:
            sig = 0.5 * (iv_a - iv_b)
        else:
            # One side would not invert (typically a bid at or below intrinsic). Fall back to a
            # fixed fraction and COUNT it, so a chain fitted mostly on fallbacks is visible.
            sig = FALLBACK_IV_FRAC * float(iv)
            n_fallback += 1
        ks.append(float(k))
        vols.append(float(iv))
        sigs.append(max(float(sig), 1e-4))
    diag = {
        "n_raw": n_raw,
        "n_unusable_quote": n_unusable,
        "n_iv_failed": int(n_iv_failed),
        "n_smile": int(len(ks)),
        "k_min": float(min(ks)) if ks else None,
        "k_max": float(max(ks)) if ks else None,
        "median_vol_sigma": float(np.median(sigs)) if sigs else None,
        "n_sigma_fallback": int(n_fallback),
    }
    if not ks:
        return (*empty, diag)
    order = np.argsort(np.asarray(ks))
    return (np.asarray(ks)[order], np.asarray(vols)[order], np.asarray(sigs)[order], diag)


# ---------------------------------------------------------------------------------------------
# Step 2-3 - the smooth smile in log-moneyness, with C1 smooth-pasted wings
# ---------------------------------------------------------------------------------------------
def fit_smile(strikes: np.ndarray, vols: np.ndarray, vol_sigmas: np.ndarray, forward: float):
    """Return (vol_of_strike, (k_lo_observed, k_hi_observed)).

    The abscissa is ln(K/F) - monotone in K by construction, so the delta-space fold that breaks
    SR-677 on an equity skew cannot occur (module docstring, DEPARTURE 1).

    The wings are smooth-pasted rather than clamped flat, because a step in sigma' is a delta
    function in sigma'' and the density carries `C_sigma * sigma''` (DEPARTURE 2). The
    continuation is asymptotically constant, so the far tails remain lognormal.
    """
    k = np.asarray(strikes, dtype=float)
    v = np.asarray(vols, dtype=float)
    w = np.asarray(vol_sigmas, dtype=float)
    if k.size < 2:
        raise ValueError("need at least 2 smile points")
    x = np.log(k / float(forward))
    # A spline needs strictly increasing abscissae.
    keep = np.concatenate(([True], np.diff(x) > 0))
    x, v, w = x[keep], v[keep], w[keep]
    if x.size < 2:
        raise ValueError("smile collapsed to a single strike")
    lo_x, hi_x = float(x[0]), float(x[-1])

    if x.size < 4:
        # Too few knots for a cubic. A straight weighted line is honest; a cubic would not be.
        co = np.polyfit(x, v, 1)
        core = lambda z: np.polyval(co, z)                              # noqa: E731
        dcore = lambda z: np.full_like(np.asarray(z, float), float(co[0]))   # noqa: E731
    else:
        spl = UnivariateSpline(x, v, w=1.0 / w, k=3, s=SMOOTH_S_MULT * x.size, ext=3)
        d1 = spl.derivative(1)
        core = spl
        dcore = d1

    lo_v = float(np.asarray(core(np.array([lo_x])), float)[0])
    hi_v = float(np.asarray(core(np.array([hi_x])), float)[0])
    lo_s = float(np.asarray(dcore(np.array([lo_x])), float)[0])
    hi_s = float(np.asarray(dcore(np.array([hi_x])), float)[0])

    def vol_of_strike(kk):
        xa = np.log(np.atleast_1d(np.asarray(kk, dtype=float)) / float(forward))
        out = np.empty_like(xa)
        inside = (xa >= lo_x) & (xa <= hi_x)
        if inside.any():
            out[inside] = np.asarray(core(xa[inside]), dtype=float)
        left, right = xa < lo_x, xa > hi_x
        if left.any():
            u = lo_x - xa[left]                       # distance beyond the low-strike edge
            out[left] = lo_v - lo_s * PASTE_L * (1.0 - np.exp(-u / PASTE_L))
        if right.any():
            u = xa[right] - hi_x
            out[right] = hi_v + hi_s * PASTE_L * (1.0 - np.exp(-u / PASTE_L))
        return np.clip(out, VOL_FLOOR, VOL_CEIL)

    return vol_of_strike, (float(k[0]), float(k[-1]))


# ---------------------------------------------------------------------------------------------
# Step 4 - Breeden-Litzenberger on a uniform strike grid
# ---------------------------------------------------------------------------------------------
def density_from_smile(vol_of_strike, observed: Tuple[float, float], forward: float, t: float,
                       r: float, min_strike: Optional[float] = None,
                       read_hi: Optional[float] = None,
                       n_grid: int = GRID_N, n_sigmas: float = GRID_SIGMAS):
    """Return (K, density, cdf, diagnostics).

        f(K)  = e^{rT} * d2C/dK2          (Breeden-Litzenberger 1978)
        F(K)  = 1 + e^{rT} * dC/dK        (the same identity, one derivative up)

    BOTH the slope CDF and the integrated-density CDF are computed, and their disagreement is
    REPORTED rather than one being quietly preferred: they are the same quantity by construction,
    so a gap between them is discretization error made visible. A number with no second route to
    it cannot tell you when it has gone wrong.

    A NOTE ON THE `integral` DIAGNOSTIC, BECAUSE IT IS WEAKER THAN IT LOOKS. O-1's K1 asks that
    the density integrate to 1 +/- 0.02. Computed this way the integral TELESCOPES - it is a sum
    of second differences of the call curve - so it returns ~1 almost regardless of how badly the
    smile is behaved, and on a chain whose density was oscillating between -0.90 and +0.72 it
    still read 1.00000. It is retained because the register asks for it and because it genuinely
    catches one thing (a grid that truncates real mass), but `negative_mass` is the diagnostic
    that actually detects a broken density, and it is the one to read first.
    """
    k_obs_lo, k_obs_hi = observed
    s_atm = float(np.asarray(vol_of_strike(np.array([forward])), float)[0]) * math.sqrt(t)
    if not (math.isfinite(s_atm) and s_atm > 0):
        s_atm = 0.3 * math.sqrt(t)
    hi = forward * math.exp(n_sigmas * s_atm)
    lo = forward * math.exp(-n_sigmas * s_atm)
    # The grid MUST reach every threshold a caller will ask about, or the answer there would be
    # silently clipped rather than computed. A lognormal tail that far out is small, but "small
    # because we computed it" and "zero because the grid stopped" are different claims.
    if min_strike is not None and min_strike > 0:
        lo = min(lo, float(min_strike) * 0.8)
    lo = max(lo, 1e-6 * forward)
    k = np.linspace(lo, hi, int(n_grid))
    h = float(k[1] - k[0])
    s_eff = forward * math.exp(-r * t)
    vols = np.asarray(vol_of_strike(k), dtype=float)
    c = np.array([bs_price(s_eff, float(kk), t, r, float(vv), right="C", q=0.0) or 0.0
                  for kk, vv in zip(k, vols)], dtype=float)
    disc = math.exp(r * t)
    dens = np.full_like(c, np.nan)
    dens[1:-1] = disc * (c[2:] - 2.0 * c[1:-1] + c[:-2]) / (h * h)
    dens[0], dens[-1] = dens[1], dens[-2]
    cdf_slope = np.full_like(c, np.nan)
    cdf_slope[1:-1] = 1.0 + disc * (c[2:] - c[:-2]) / (2.0 * h)
    cdf_slope[0] = max(0.0, 2.0 * cdf_slope[1] - cdf_slope[2])
    cdf_slope[-1] = min(1.0, 2.0 * cdf_slope[-2] - cdf_slope[-3])

    integral = float(np.trapezoid(dens, k))                 # RAW, not clipped - see docstring
    neg = float(np.trapezoid(np.clip(-dens, 0.0, None), k))
    cdf_int = np.concatenate(([0.0], np.cumsum(
        0.5 * (np.clip(dens[1:], 0.0, None) + np.clip(dens[:-1], 0.0, None)) * np.diff(k))))
    tot = cdf_int[-1]
    if tot > 0:
        cdf_int = cdf_int / tot                       # normalise ONLY the integrated route
    cdf_slope_c = np.clip(cdf_slope, 0.0, 1.0)

    step = np.diff(cdf_slope_c)
    worst_i = int(np.argmin(step)) if step.size else 0
    # The region a threshold can actually read. Above it the density is wing decoration as far as
    # a left-tail consumer is concerned; it is diagnosed globally but not gated on.
    hi_read = float(read_hi) if read_hi else float(forward)
    in_read = k[:-1] <= hi_read
    read_step = step[in_read] if in_read.any() else step
    read_mask = k <= hi_read
    neg_read = (float(np.trapezoid(np.clip(-dens[read_mask], 0.0, None), k[read_mask]))
                if read_mask.sum() > 1 else 0.0)
    diag = {
        "integral": integral,
        "negative_mass": neg,
        "negative_mass_read_region": neg_read,
        "grid_lo": float(lo), "grid_hi": float(hi), "grid_h": h, "n_grid": int(n_grid),
        "k_observed_lo": float(k_obs_lo), "k_observed_hi": float(k_obs_hi),
        "read_region_hi": hi_read,
        "atm_vol": float(s_atm / math.sqrt(t)),
        # The two independent routes to the same CDF; their max gap is the honest error bar.
        "cdf_route_max_gap": float(np.nanmax(np.abs(cdf_slope_c - cdf_int))),
        "cdf_worst_step": float(step.min()) if step.size else 0.0,
        "cdf_worst_step_moneyness": float(k[worst_i] / forward) if step.size else None,
        "cdf_monotone_global": bool(np.all(step >= -MONOTONE_TOL)),
        "cdf_monotone_read_region": bool(np.all(read_step >= -MONOTONE_TOL)),
    }
    return k, dens, cdf_slope_c, diag


def tail_mass_from_cdf(k: np.ndarray, cdf: np.ndarray, strike: float) -> float:
    """Q(S_T <= strike), read off the CDF by linear interpolation between grid points.

    Clamped to [0, 1]: a probability outside the unit interval is a discretization artefact, and
    returning one would let a consumer print it.
    """
    v = float(np.interp(float(strike), k, cdf, left=float(cdf[0]), right=float(cdf[-1])))
    return min(1.0, max(0.0, v))


# ---------------------------------------------------------------------------------------------
# The slice builder - every gate pre-declared above, every refusal attributed
# ---------------------------------------------------------------------------------------------
def build_slice(xs: pd.DataFrame, spot: float, asof, expiry, symbol: str = "",
                r: Optional[float] = None,
                thresholds: Sequence[float] = TAIL_THRESHOLDS) -> RNDSlice:
    """One cross-section -> one RNDSlice. NEVER raises on bad data; refuses and says why.

    `spot` MUST be the as-traded `raw_close`. Passing an adjusted close is the `U1-SPLIT` defect
    and will not raise - it will quietly produce a density centred nowhere near the money. The
    parity diagnostic below is what catches it, which is why it runs on every slice rather than
    on request.
    """
    asof = pd.Timestamp(asof)
    expiry = pd.Timestamp(expiry)
    out = RNDSlice(symbol=str(symbol), asof=asof, expiry=expiry, spot=float(spot))
    reasons = []

    dte = int((expiry - asof).days)
    out.diagnostics["dte_days"] = dte
    if dte < MIN_DTE_DAYS or dte > MAX_DTE_DAYS:
        out.reasons = ("dte_out_of_band",)
        out.diagnostics["dte_band"] = [MIN_DTE_DAYS, MAX_DTE_DAYS]
        return out
    t = dte / 365.0
    out.t_years = t
    if r is None:
        from valuation.edge.blackscholes import risk_free_rate
        r = float(risk_free_rate(asof.date()))
    out.rate = float(r)

    if not (math.isfinite(float(spot)) and float(spot) > 0):
        out.reasons = ("bad_spot",)
        return out

    fwd, fdiag = forward_from_parity(xs, t, float(r), spot_hint=float(spot))
    out.diagnostics["parity"] = fdiag
    if fwd is None or not math.isfinite(fwd) or fwd <= 0:
        out.reasons = ("no_parity_forward",)
        return out
    out.forward = float(fwd)

    # THE INDEPENDENT CHECK (O-1's K1). The parity forward discounted back must land on the
    # as-traded spot within the band the quotes themselves justify. `raw_close` is an INDEPENDENT
    # series, which is what stops this being true by construction.
    implied_spot = float(fwd) * math.exp(-float(r) * t)
    band = float(fdiag.get("parity_band") or 0.0)
    dev = implied_spot - float(spot)
    out.diagnostics["parity_implied_spot"] = implied_spot
    out.diagnostics["parity_spot_dev"] = dev
    out.diagnostics["parity_spot_dev_frac"] = dev / float(spot)
    # A dividend-paying name sits legitimately BELOW spot by the PV of dividends over the option's
    # life, so a 2% allowance rides on top of the quoted band. An ADJUSTMENT mismatch throws this
    # by tens of percent and is caught either way - that is the failure this is really for.
    out.diagnostics["parity_within_band"] = bool(abs(dev) <= band + 0.02 * float(spot))

    ks, vols, sigs, sdiag = smile_points(xs, float(fwd), t, float(r))
    out.diagnostics["smile"] = sdiag
    if len(ks) < MIN_SMILE_POINTS:
        out.reasons = ("too_few_smile_points",)
        return out

    try:
        vol_of_strike, observed = fit_smile(ks, vols, sigs, float(fwd))
        k_grid, dens, cdf, ddiag = density_from_smile(
            vol_of_strike, observed, float(fwd), t, float(r),
            min_strike=min(float(x) for x in thresholds) * float(spot),
            read_hi=max(float(x) for x in thresholds) * float(spot))
    except (ValueError, FloatingPointError, np.linalg.LinAlgError) as e:      # noqa: BLE001
        out.reasons = ("fit_failed:%s" % type(e).__name__,)
        return out
    out.strikes, out.density, out.cdf = k_grid, dens, cdf
    out.diagnostics.update(ddiag)

    k_obs_lo = ddiag.get("k_observed_lo")
    for frac in thresholds:
        kt = float(frac) * float(spot)
        out.tail_mass[float(frac)] = tail_mass_from_cdf(k_grid, cdf, kt)
        # An honest flag, not a footnote: below the lowest strike a quote was seen at, the number
        # is the smooth-pasted lognormal EXTRAPOLATION described in the module docstring.
        out.threshold_extrapolated[float(frac)] = bool(
            k_obs_lo is not None and kt < float(k_obs_lo))

    # ------------------------------------------------------------------ the pre-declared gates
    if abs(ddiag["integral"] - 1.0) > INTEGRAL_TOL:
        reasons.append("integral_off:%.4f" % ddiag["integral"])
    if ddiag["negative_mass"] > MAX_NEG_MASS:
        reasons.append("negative_density:%.4f" % ddiag["negative_mass"])
    # Strict monotonicity is required exactly where a threshold is read. A residual dip out in
    # the right wing is recorded in `cdf_monotone_global` and does not refuse the slice, because
    # it cannot reach a left-tail number.
    if not ddiag["cdf_monotone_read_region"]:
        reasons.append("cdf_not_monotone_in_read_region")
    if not out.diagnostics["parity_within_band"]:
        reasons.append("parity_spot_mismatch:%.4f" % out.diagnostics["parity_spot_dev_frac"])
    out.reasons = tuple(reasons)
    out.usable = not reasons
    return out


def build_name_day(chain: pd.DataFrame, spot: float, asof, symbol: str = "",
                   r: Optional[float] = None,
                   thresholds: Sequence[float] = TAIL_THRESHOLDS) -> list:
    """Every expiry available for one (name, date). Returns a list of RNDSlice, usable or not.

    Unusable slices are RETURNED, not dropped. A caller wanting only good ones filters on
    `.usable`; a caller writing a coverage census needs the refusals and their reasons, and a
    function that silently returned the survivors would make that census impossible to write.
    """
    asof = pd.Timestamp(asof)
    d = chain.copy()
    d["expiration"] = pd.to_datetime(d["expiration"])
    if "date" in d.columns:
        d = d.loc[pd.to_datetime(d["date"]) == asof]
    out = []
    for e, xs in d.groupby("expiration"):
        out.append(build_slice(xs, spot=spot, asof=asof, expiry=e, symbol=symbol, r=r,
                               thresholds=thresholds))
    return out


def coverage_census(slices: Sequence[RNDSlice]) -> dict:
    """Counts and the reason breakdown. The number a write-up prints instead of 'it worked'."""
    n = len(slices)
    usable = [s for s in slices if s.usable]
    reasons: Dict[str, int] = {}
    for s in slices:
        for why in (s.reasons or ("(none)",)):
            head = why.split(":")[0]
            reasons[head] = reasons.get(head, 0) + 1
    extrap = {}
    for frac in TAIL_THRESHOLDS:
        flagged = [s.threshold_extrapolated.get(frac) for s in usable
                   if frac in s.threshold_extrapolated]
        extrap[str(frac)] = (float(np.mean(flagged)) if flagged else None)
    return {
        "n_slices": n,
        "n_usable": len(usable),
        "usable_share": (len(usable) / n) if n else None,
        "refusal_reasons": reasons,
        "extrapolated_share_by_threshold": extrap,
        "method": METHOD,
        "citations": list(CITATIONS),
    }
