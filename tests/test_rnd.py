"""I-1 - the Breeden-Litzenberger RND builder. Run: python tests/test_rnd.py

WHAT THESE PIN, AND WHY IN THIS ORDER.

  1. THE BENCHMARK IS TESTED BEFORE THE ESTIMATOR IS TESTED AGAINST IT. `mixture_lognormal_*`
     are the ground truth every accuracy test leans on, so they are first verified independently
     - against numerical integration of the mixture itself, and against the Black-Scholes
     lognormal in the degenerate one-component case. A benchmark nobody checked is not a
     benchmark, and an estimator scored against a wrong one passes while being wrong.

  2. THE LOGNORMAL ALONE IS NOT A TEST. A flat smile must return N(-d2) exactly - but that is
     the case a BROKEN estimator still gets right, because a constant vol makes every
     smile-shape decision irrelevant. So the load-bearing accuracy test is Bahra's two-lognormal
     mixture (BoE WP 66, 1997), which is skewed and fat-tailed, and it ships WITH ITS CONTROL:
     a single lognormal at the ATM vol is measured to be badly wrong on the same number, so the
     test demonstrates the estimator is doing real work rather than reproducing an assumption.

  3. THE TAIL-MASS ARITHMETIC IS MUTATION-TESTED. Every sign, discount factor and stencil in the
     Breeden-Litzenberger chain is individually corrupted, and the suite asserts the corruption
     is CAUGHT. A green suite over code nobody perturbed says only that the code ran.

  4. THE INSTRUMENT'S NEUTRALITY IS ENFORCED AT SOURCE LEVEL. `rnd.py` may not read a forward
     return, and may not reach the mutable chain store. Both are source sweeps, and both carry
     their own non-vacuity check - a guard that would pass over an empty file is not a guard.
"""
import ast
import io
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tests.state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import blackscholes as BS  # noqa: E402
from valuation.studies import rnd as R  # noqa: E402

RND_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "valuation", "studies", "rnd.py")

# --------------------------------------------------------------------------------- fixtures
ASOF = pd.Timestamp("2018-03-01")
EXP = pd.Timestamp("2018-05-31")
T = (EXP - ASOF).days / 365.0
RATE = 0.02
FLAT_F, FLAT_SIG = 100.0, 0.30
FLAT_SPOT = FLAT_F * math.exp(-RATE * T)

# Bahra's two-lognormal mixture: a benign mode and a crash mode, so the density is genuinely
# left-skewed and a lognormal cannot represent it.
MIX_W = (0.75, 0.25)
MIX_F = (108.0, 76.0)
MIX_S = (0.22, 0.55)
MIX_FWD = sum(w * f for w, f in zip(MIX_W, MIX_F))
MIX_SPOT = MIX_FWD * math.exp(-RATE * T)
STRIKES = np.arange(50.0, 155.0, 2.5)


def _black76(k, right, sigma, fwd, t=T, r=RATE):
    vt = sigma * math.sqrt(t)
    d1 = (math.log(fwd / k) + 0.5 * vt * vt) / vt
    d2 = d1 - vt
    n = R._norm_cdf
    if right == "C":
        return math.exp(-r * t) * (fwd * n(d1) - k * n(d2))
    return math.exp(-r * t) * (k * n(-d2) - fwd * n(-d1))


def _flat_price(k, right):
    return _black76(k, right, FLAT_SIG, FLAT_F)


def _mix_price(k, right):
    c = R.mixture_lognormal_call(MIX_W, MIX_F, MIX_S, T, RATE, k)
    return c if right == "C" else c - math.exp(-RATE * T) * (MIX_FWD - k)


def chain(price_fn, strikes=STRIKES, spread_frac=0.01, expiry=EXP, asof=ASOF):
    """A two-sided chain from an EXACT pricer, so any error found is the estimator's own."""
    rows = []
    for k in strikes:
        for right in ("C", "P"):
            mid = price_fn(float(k), right)
            if mid <= 0:
                continue
            half = max(0.005, spread_frac * mid)
            rows.append({"strike": float(k), "right": right, "bid": mid - half,
                         "ask": mid + half, "expiration": expiry, "date": asof})
    return pd.DataFrame(rows)


FLAT_CHAIN = chain(_flat_price)
MIX_CHAIN = chain(_mix_price)


def _flat_slice():
    return R.build_slice(FLAT_CHAIN, spot=FLAT_SPOT, asof=ASOF, expiry=EXP, symbol="FLAT",
                         r=RATE)


def _mix_slice():
    return R.build_slice(MIX_CHAIN, spot=MIX_SPOT, asof=ASOF, expiry=EXP, symbol="MIX", r=RATE)


# =========================================================================================
# 1. THE BENCHMARKS THEMSELVES, verified before anything is scored against them
# =========================================================================================
def test_mixture_tail_mass_matches_numerical_integration_of_its_own_density():
    """The analytic mixture CDF must equal a brute-force integral of the mixture PDF.

    Independent route: the CDF is a sum of N(-d2) terms while this integrates the lognormal
    density directly on a grid. If both were wrong the same way they would have to be wrong
    identically, which two different formulas do not do by accident.
    """
    lo, hi, n = 1e-4, 600.0, 400001
    s = np.linspace(lo, hi, n)
    pdf = np.zeros_like(s)
    for w, f, sg in zip(MIX_W, MIX_F, MIX_S):
        vol = sg * math.sqrt(T)
        mu = math.log(f) - 0.5 * vol * vol
        pdf += w * np.exp(-0.5 * ((np.log(s) - mu) / vol) ** 2) / (s * vol * math.sqrt(2 * math.pi))
    assert abs(float(np.trapezoid(pdf, s)) - 1.0) < 1e-4, "mixture pdf must integrate to 1"
    for strike in (40.0, 60.0, 76.0, 100.0, 130.0):
        m = s <= strike
        num = float(np.trapezoid(pdf[m], s[m]))
        ana = R.mixture_lognormal_tail_mass(MIX_W, MIX_F, MIX_S, T, strike)
        assert abs(num - ana) < 2e-4, "K=%s numerical %.8f vs analytic %.8f" % (strike, num, ana)


def test_a_one_component_mixture_is_exactly_the_black_scholes_lognormal():
    """Cross-check between the two independent analytic references at their common point."""
    for strike in (55.0, 80.0, 100.0, 140.0):
        mix = R.mixture_lognormal_tail_mass((1.0,), (FLAT_F,), (FLAT_SIG,), T, strike)
        ln = R.lognormal_tail_mass(FLAT_SPOT, strike, T, RATE, FLAT_SIG)
        assert abs(mix - ln) < 1e-12, "K=%s mixture %.12f vs lognormal %.12f" % (strike, mix, ln)


def test_mixture_call_price_matches_numerical_integration_of_the_payoff():
    lo, hi, n = 1e-4, 600.0, 400001
    s = np.linspace(lo, hi, n)
    pdf = np.zeros_like(s)
    for w, f, sg in zip(MIX_W, MIX_F, MIX_S):
        vol = sg * math.sqrt(T)
        mu = math.log(f) - 0.5 * vol * vol
        pdf += w * np.exp(-0.5 * ((np.log(s) - mu) / vol) ** 2) / (s * vol * math.sqrt(2 * math.pi))
    for strike in (70.0, 100.0, 125.0):
        num = math.exp(-RATE * T) * float(np.trapezoid(np.clip(s - strike, 0, None) * pdf, s))
        ana = R.mixture_lognormal_call(MIX_W, MIX_F, MIX_S, T, RATE, strike)
        assert abs(num - ana) < 5e-3, "K=%s numerical %.6f vs analytic %.6f" % (strike, num, ana)


def test_lognormal_tail_mass_is_N_minus_d2_and_not_N_minus_d1():
    """The classic confusion, pinned. At K = F they differ by a knowable amount."""
    sigma, t, r = 0.40, 1.0, 0.0
    spot = strike = 100.0                 # at the money, where the two differ most visibly
    got = R.lognormal_tail_mass(spot, strike, t, r, sigma)
    d1 = (math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)
    assert abs(got - R._norm_cdf(-d2)) < 1e-15
    assert abs(got - R._norm_cdf(-d1)) > 0.10, "N(-d1) and N(-d2) must not be confusable here"


def test_mixture_rejects_weights_that_do_not_sum_to_one():
    for bad in ((0.5, 0.4), (1.0, 0.2)):
        try:
            R.mixture_lognormal_tail_mass(bad, MIX_F, MIX_S, T, 80.0)
        except ValueError:
            continue
        raise AssertionError("weights %r must be refused" % (bad,))


# =========================================================================================
# 2. ACCURACY - the lognormal (easy), then the mixture (the real test) with its control
# =========================================================================================
def test_flat_smile_reproduces_the_black_scholes_lognormal_tail_mass():
    s = _flat_slice()
    assert s.usable, s.reasons
    for frac in R.TAIL_THRESHOLDS:
        est = s.tail_mass[frac]
        true = R.lognormal_tail_mass(FLAT_SPOT, frac * FLAT_SPOT, T, RATE, FLAT_SIG)
        assert abs(est - true) < 1e-3, "frac %.2f: %.8f vs analytic %.8f" % (frac, est, true)


def test_flat_smile_recovers_the_input_volatility():
    s = _flat_slice()
    assert abs(s.diagnostics["atm_vol"] - FLAT_SIG) < 1e-3, s.diagnostics["atm_vol"]


def test_the_skewed_mixture_is_recovered_where_it_is_observed():
    """The load-bearing accuracy test: a genuinely skewed, fat-tailed published benchmark."""
    s = _mix_slice()
    assert s.usable, s.reasons
    for frac in R.TAIL_THRESHOLDS:
        est = s.tail_mass[frac]
        true = R.mixture_lognormal_tail_mass(MIX_W, MIX_F, MIX_S, T, frac * MIX_SPOT)
        assert abs(est - true) < 2e-2, "frac %.2f: %.8f vs analytic %.8f" % (frac, est, true)


def test_the_mixture_test_is_not_vacuous_a_lognormal_would_fail_it():
    """CONTROL. If a lognormal at the ATM vol passed the test above, the test would prove
    nothing about the estimator's ability to see skew. It does not pass: measured, the true
    mass at 0.70 is ~0.107 while a lognormal says ~0.040."""
    s = _mix_slice()
    frac = 0.70
    true = R.mixture_lognormal_tail_mass(MIX_W, MIX_F, MIX_S, T, frac * MIX_SPOT)
    naive = R.lognormal_tail_mass(MIX_SPOT, frac * MIX_SPOT, T, RATE, s.diagnostics["atm_vol"])
    assert abs(naive - true) > 5e-2, "the lognormal control must be badly wrong; got %.6f" % naive
    assert abs(s.tail_mass[frac] - true) < abs(naive - true) / 3.0, \
        "the estimator must beat the lognormal control by a wide margin"


def test_the_forward_is_recovered_from_parity_on_both_fixtures():
    assert abs(_flat_slice().forward - FLAT_F) < 1e-6
    assert abs(_mix_slice().forward - MIX_FWD) < 1e-6


def test_the_density_integrates_to_one_and_carries_no_negative_mass():
    for s in (_flat_slice(), _mix_slice()):
        assert abs(s.diagnostics["integral"] - 1.0) <= R.INTEGRAL_TOL, s.diagnostics["integral"]
        assert s.diagnostics["negative_mass"] <= R.MAX_NEG_MASS, s.diagnostics["negative_mass"]
        assert s.diagnostics["cdf_monotone_read_region"]


def test_the_two_cdf_routes_agree():
    """Slope-of-price and integral-of-density are the same quantity; disagreement is error."""
    for s in (_flat_slice(), _mix_slice()):
        assert s.diagnostics["cdf_route_max_gap"] < 1e-3, s.diagnostics["cdf_route_max_gap"]


def test_tail_mass_is_monotone_in_the_threshold():
    for s in (_flat_slice(), _mix_slice()):
        vals = [s.tail_mass[f] for f in sorted(R.TAIL_THRESHOLDS)]
        assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:])), vals


# =========================================================================================
# 3. MUTATION - every piece of the tail-mass arithmetic corrupted, one at a time
# =========================================================================================
def _accuracy_holds() -> bool:
    """The property the mutations must break: both fixtures reproduce their analytic truth."""
    try:
        f, m = _flat_slice(), _mix_slice()
        if not (f.usable and m.usable):
            return False
        for frac in R.TAIL_THRESHOLDS:
            if abs(f.tail_mass[frac] -
                   R.lognormal_tail_mass(FLAT_SPOT, frac * FLAT_SPOT, T, RATE, FLAT_SIG)) > 1e-3:
                return False
            if abs(m.tail_mass[frac] -
                   R.mixture_lognormal_tail_mass(MIX_W, MIX_F, MIX_S, T, frac * MIX_SPOT)) > 2e-2:
                return False
        return True
    except Exception:                                                # noqa: BLE001
        return False


def _mutate(attr, replacement):
    original = getattr(R, attr)
    setattr(R, attr, replacement)
    try:
        return _accuracy_holds()
    finally:
        setattr(R, attr, original)


def test_mutation_baseline_is_green_before_anything_is_corrupted():
    """Without this, every mutation below could 'pass' because the baseline was already red."""
    assert _accuracy_holds(), "baseline accuracy must hold before mutation testing means anything"


def test_mutation_survival_instead_of_cdf_is_caught():
    """Q(S<=K) vs Q(S>K) - the single most likely sign error in a tail-mass instrument."""
    orig = R.tail_mass_from_cdf
    assert not _mutate("tail_mass_from_cdf", lambda k, c, s: 1.0 - orig(k, c, s)), \
        "returning the survival function instead of the CDF was NOT caught"


def test_mutation_of_the_discount_factor_is_caught():
    """f = e^{+rT} C''; using e^{-rT} scales every density by e^{-2rT}."""
    orig = R.density_from_smile

    def bad(vol_of_strike, observed, forward, t, r, **kw):
        k, d, c, dg = orig(vol_of_strike, observed, forward, t, r, **kw)
        return k, d * math.exp(-2 * r * t), np.clip(1.0 - (1.0 - c) * math.exp(-2 * r * t),
                                                    0, 1), dg
    assert not _mutate("density_from_smile", bad), "a corrupted discount factor was NOT caught"


def test_mutation_of_the_breeden_litzenberger_cdf_sign_is_caught():
    orig = R.density_from_smile

    def bad(vol_of_strike, observed, forward, t, r, **kw):
        k, d, c, dg = orig(vol_of_strike, observed, forward, t, r, **kw)
        return k, d, np.clip(1.0 - c, 0.0, 1.0), dg      # F(K) -> 1 - F(K)
    assert not _mutate("density_from_smile", bad), "a flipped CDF sign was NOT caught"


def test_mutation_of_the_second_difference_stencil_is_caught():
    """Dropping the factor 2 in (c[+1] - 2c[0] + c[-1]) is a plausible typo, not an exotic one."""
    orig = R.density_from_smile

    def bad(vol_of_strike, observed, forward, t, r, **kw):
        k, d, c, dg = orig(vol_of_strike, observed, forward, t, r, **kw)
        return k, d * 0.5, np.clip(c * 0.5, 0.0, 1.0), dg
    assert not _mutate("density_from_smile", bad), "a corrupted stencil was NOT caught"


def test_mutation_of_the_threshold_scaling_is_caught():
    """Thresholds multiply SPOT. Multiplying the FORWARD instead is a silent, plausible slip."""
    orig = R.tail_mass_from_cdf
    assert not _mutate("tail_mass_from_cdf",
                       lambda k, c, s: orig(k, c, s * 1.05)), \
        "reading the tail mass at the wrong strike was NOT caught"


def test_mutation_of_the_analytic_lognormal_reference_is_caught():
    """The BENCHMARK is mutation-tested too: if N(-d2) became N(-d1) the estimator would be
    scored against the wrong truth and would 'fail' for the benchmark's reason, not its own."""
    orig = R.lognormal_tail_mass

    def bad(spot, strike, t, r, sigma, q=0.0):
        d1 = (math.log(spot / strike) + (r - q + 0.5 * sigma * sigma) * t) / (sigma * math.sqrt(t))
        return R._norm_cdf(-d1)
    assert not _mutate("lognormal_tail_mass", bad), "a corrupted analytic reference was NOT caught"


def test_mutation_of_the_parity_forward_is_caught():
    orig = R.forward_from_parity

    def bad(xs, t, r, spot_hint=None):
        f, d = orig(xs, t, r, spot_hint=spot_hint)
        return (None if f is None else f * 1.03), d
    assert not _mutate("forward_from_parity", bad), "a corrupted forward was NOT caught"


# =========================================================================================
# 4. THE INSTRUMENT'S NEUTRALITY AND ITS SOURCE, enforced rather than promised
# =========================================================================================
FORBIDDEN_RETURN_TOKENS = ("fwd_ret", "forward_return", "forward_ret", "realized_return",
                           "future_return", "ret_fwd", "information_coefficient")


def _module_source() -> str:
    with io.open(RND_SRC, encoding="utf-8") as fh:
        return fh.read()


def _code_only(src: str) -> str:
    """Strip docstrings and comments, so prose ABOUT a hazard is not read as the hazard.

    A guard that cannot tell code from prose about code is not measuring the tree - this
    module's docstring necessarily discusses forward returns in order to forbid them.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(tree))


def test_the_module_never_reads_a_forward_return():
    """I-1 is an INSTRUMENT. Any relationship between an RND quantity and a realized return
    voids its neutrality, because it is consumed as a kill that runs BEFORE any arm."""
    code = _code_only(_module_source())
    hits = [t for t in FORBIDDEN_RETURN_TOKENS if t in code]
    assert not hits, "rnd.py references forward-return vocabulary in CODE: %s" % hits


def test_the_forward_return_sweep_is_not_vacuous():
    """Positive control: the sweep must fire on a source that really does read a return."""
    code = _code_only("def f(panel):\n    return panel['fwd_ret'].mean()\n")
    hits = [t for t in FORBIDDEN_RETURN_TOKENS if t in code]
    assert hits, "the sweep failed to fire on a deliberate violation"


def test_the_sweep_strips_docstrings_so_prose_is_not_a_false_positive():
    src = 'def f():\n    """This must never read fwd_ret."""\n    return 1\n'
    assert "fwd_ret" in src
    assert "fwd_ret" not in _code_only(src), "docstring prose must not read as code"


MUTABLE_ESCAPES = ("allow_mutable", "VALQUO_CHAINS")


def test_the_module_cannot_reach_the_mutable_chain_store():
    """The freeze resolver is the only sanctioned door and it RAISES rather than falling back.
    This module must not carry its own escape hatch.

    Banned BY ROLE, not by path substring. `allow_mutable` and `VALQUO_CHAINS` are the two names
    that exist solely to opt out of the pin, so they identify the hazard exactly; banning a path
    fragment like "options" would fire on correct code that merely mentions a directory.
    """
    code = _code_only(_module_source())
    hits = [t for t in MUTABLE_ESCAPES if t in code]
    assert not hits, "rnd.py carries a mutable-store escape: %s" % hits


def test_the_mutable_store_sweep_is_not_vacuous():
    """Positive control, as every loosened guard needs one."""
    code = _code_only("def f(root):\n    return resolve_chains(root, allow_mutable=True)\n")
    assert [t for t in MUTABLE_ESCAPES if t in code], "the sweep failed to fire on a real escape"


def test_the_pinned_freeze_resolvers_exist_and_refuse_a_missing_freeze():
    from valuation.edge import chain_store as CS
    assert hasattr(CS, "resolve_chains") and hasattr(CS, "resolve_harvest")
    try:
        CS.resolve_harvest(root=os.path.join(os.path.dirname(RND_SRC), "_no_such_freeze_"))
    except CS.ChainStoreError:
        return
    raise AssertionError("resolve_harvest must RAISE on a missing freeze, never fall back")


def test_usable_quote_is_the_shipped_definition_not_a_local_copy():
    """Audit B7's class: one definition, delegated to."""
    assert R.usable_quote is BS.usable_quote
    code = _code_only(_module_source())
    assert "def usable_quote" not in code, "rnd.py must not define its own usable_quote"


# =========================================================================================
# 5. QUOTE VALIDITY, THE SPLIT TRAP, AND REFUSAL ATTRIBUTION
# =========================================================================================
def test_one_sided_quotes_are_excluded_and_counted():
    """The victims must be rows the smile ACTUALLY USES, or the test passes vacuously.

    Zeroing the bid on a deep-ITM call proves nothing: it is not on the OTM side, so it was
    never going to enter the smile and `n_smile` cannot move. The rows are therefore chosen by
    the same OTM rule `smile_points` applies, and the fixture asserts it selected some.
    """
    ch = FLAT_CHAIN.copy()
    right = ch["right"].astype(str).str.upper().str[0]
    strike = ch["strike"].astype(float)
    otm = ((right == "C") & (strike >= FLAT_F)) | ((right == "P") & (strike < FLAT_F))
    # ALREADY-usable only. The fixture's own cheapest wings carry a bid at or below zero (a
    # penny-wide market on a sub-cent option), so corrupting those would move `n_unusable_quote`
    # by less than the number of rows touched and the test would read as a partial failure of
    # the module rather than as an overlapping fixture.
    live = np.asarray([R.usable_quote(b, a) for b, a in zip(ch["bid"], ch["ask"])], dtype=bool)
    victims = ch.index[otm & pd.Series(live, index=ch.index)][:8]
    assert len(victims) == 8, "fixture must find 8 usable OTM rows to corrupt"
    base = _flat_slice()
    ch.loc[victims, "bid"] = 0.0                     # a one-sided quote is not a price
    s = R.build_slice(ch, spot=FLAT_SPOT, asof=ASOF, expiry=EXP, r=RATE)
    assert (s.diagnostics["smile"]["n_unusable_quote"]
            == base.diagnostics["smile"]["n_unusable_quote"] + 8), \
        (s.diagnostics["smile"], base.diagnostics["smile"])
    assert s.diagnostics["smile"]["n_smile"] == base.diagnostics["smile"]["n_smile"] - 8, \
        (s.diagnostics["smile"], base.diagnostics["smile"])


def test_a_crossed_quote_is_refused():
    ch = FLAT_CHAIN.copy()
    ch.loc[ch.index[:6], "ask"] = ch.loc[ch.index[:6], "bid"] - 0.01
    s = R.build_slice(ch, spot=FLAT_SPOT, asof=ASOF, expiry=EXP, r=RATE)
    assert s.diagnostics["smile"]["n_unusable_quote"] >= 6


def test_an_adjusted_spot_trips_the_parity_tripwire():
    """U1-SPLIT. As-traded strikes against a split-adjusted close produce a plausible number,
    never an error. The parity-vs-raw_close check is what catches it, so it is pinned from
    both sides: the correct spot passes, a 4-for-1 'adjusted' spot fails and SAYS SO."""
    good = _flat_slice()
    assert good.diagnostics["parity_within_band"]
    bad = R.build_slice(FLAT_CHAIN, spot=FLAT_SPOT / 4.0, asof=ASOF, expiry=EXP, r=RATE)
    assert not bad.diagnostics["parity_within_band"]
    assert not bad.usable
    assert any(x.startswith("parity_spot_mismatch") for x in bad.reasons), bad.reasons


def test_a_refusal_always_names_its_reason():
    bad = R.build_slice(FLAT_CHAIN, spot=FLAT_SPOT / 4.0, asof=ASOF, expiry=EXP, r=RATE)
    assert not bad.usable and bad.reasons, "an unusable slice must carry an attributable reason"
    ok = _flat_slice()
    assert ok.usable and ok.reasons == (), ok.reasons


def test_a_slice_outside_the_dte_band_is_refused_at_both_ends():
    for exp in (ASOF + pd.Timedelta(days=R.MIN_DTE_DAYS - 1),
                ASOF + pd.Timedelta(days=R.MAX_DTE_DAYS + 1)):
        ch = chain(_flat_price, expiry=exp)
        s = R.build_slice(ch, spot=FLAT_SPOT, asof=ASOF, expiry=exp, r=RATE)
        assert not s.usable and s.reasons == ("dte_out_of_band",), s.reasons


def test_too_few_smile_points_is_refused_rather_than_fitted():
    ch = chain(_flat_price, strikes=np.array([95.0, 100.0, 105.0]))
    s = R.build_slice(ch, spot=FLAT_SPOT, asof=ASOF, expiry=EXP, r=RATE)
    assert not s.usable and "too_few_smile_points" in s.reasons, s.reasons


def test_an_empty_cross_section_refuses_instead_of_raising():
    empty = pd.DataFrame(columns=["strike", "right", "bid", "ask", "expiration", "date"])
    s = R.build_slice(empty, spot=FLAT_SPOT, asof=ASOF, expiry=EXP, r=RATE)
    assert not s.usable and s.reasons, s.reasons


# =========================================================================================
# 6. THE SPARSE-WING CONTRACT: extrapolation is FLAGGED, and the wings stay smooth
# =========================================================================================
def test_a_threshold_below_the_lowest_quoted_strike_is_flagged_extrapolated():
    """The honest half of the sparse-wing story, and the one a consumer must be able to read."""
    s = _flat_slice()
    k_lo = s.diagnostics["k_observed_lo"]
    for frac in R.TAIL_THRESHOLDS:
        expected = (frac * FLAT_SPOT) < k_lo
        assert s.threshold_extrapolated[frac] is expected, \
            "frac %.2f: flag %s but K=%.3f vs lowest quote %.3f" % (
                frac, s.threshold_extrapolated[frac], frac * FLAT_SPOT, k_lo)
    assert any(s.threshold_extrapolated.values()), "fixture must exercise the True branch"
    assert not all(s.threshold_extrapolated.values()), "fixture must exercise the False branch"


def test_the_smile_is_C1_at_the_seam_where_the_wing_is_pasted_on():
    """DEPARTURE 2, pinned numerically. A STEP in sigma' at the seam is a delta function in
    sigma'', and the density carries C_sigma * sigma'' - so a kink here manufactures a negative
    density spike. The one-sided slopes must match."""
    ks, vols, sigs, _ = R.smile_points(MIX_CHAIN, MIX_FWD, T, RATE)
    vol_of_strike, (k_lo, k_hi) = R.fit_smile(ks, vols, sigs, MIX_FWD)
    for edge in (k_lo, k_hi):
        h = edge * 1e-4
        inside = float(vol_of_strike(np.array([edge + h if edge == k_lo else edge - h]))[0])
        at = float(vol_of_strike(np.array([edge]))[0])
        outside = float(vol_of_strike(np.array([edge - h if edge == k_lo else edge + h]))[0])
        slope_in = abs(inside - at) / h
        slope_out = abs(at - outside) / h
        assert abs(slope_in - slope_out) < 0.05 * max(1.0, slope_in), \
            "seam at K=%.3f is not C1: inside %.6f vs outside %.6f" % (edge, slope_in, slope_out)


def test_the_pasted_wing_is_asymptotically_constant_so_the_tails_stay_lognormal():
    ks, vols, sigs, _ = R.smile_points(MIX_CHAIN, MIX_FWD, T, RATE)
    vol_of_strike, (k_lo, _) = R.fit_smile(ks, vols, sigs, MIX_FWD)
    far = np.array([k_lo * 0.5, k_lo * 0.25, k_lo * 0.10])
    v = np.asarray(vol_of_strike(far), dtype=float)
    assert abs(v[-1] - v[-2]) < abs(v[1] - v[0]) + 1e-12, "the wing must flatten, not run away"
    assert np.all(np.isfinite(v)) and np.all(v > 0)


def test_vol_of_strike_is_single_valued_where_a_delta_abscissa_would_fold():
    """DEPARTURE 1. On a steep skew the delta->strike map doubles back; ln(K/F) cannot. Pinned
    by feeding a deliberately steep smile and asserting the vol curve stays a function of K."""
    steep = []
    for k in STRIKES:
        sig = 0.20 + 0.9 * max(0.0, (100.0 - float(k)) / 100.0) ** 1.5
        for right in ("C", "P"):
            mid = _black76(float(k), right, sig, 100.0)
            if mid <= 0:
                continue
            half = max(0.005, 0.01 * mid)
            steep.append({"strike": float(k), "right": right, "bid": mid - half,
                          "ask": mid + half, "expiration": EXP, "date": ASOF})
    ch = pd.DataFrame(steep)
    ks, vols, sigs, _ = R.smile_points(ch, 100.0, T, RATE)
    vol_of_strike, _ = R.fit_smile(ks, vols, sigs, 100.0)
    grid = np.linspace(40.0, 160.0, 500)
    v = np.asarray(vol_of_strike(grid), dtype=float)
    assert v.shape == grid.shape and np.all(np.isfinite(v)), "vol(K) must be single-valued"
    assert np.all(v > 0)


# =========================================================================================
# 7. THE CENSUS AND THE CONSUMER CONTRACT
# =========================================================================================
def test_build_name_day_returns_unusable_slices_rather_than_dropping_them():
    """A caller writing a coverage census needs the refusals; silently returning survivors
    would make an honest census impossible to write."""
    near = ASOF + pd.Timedelta(days=3)               # deliberately inside the DTE floor
    ch = pd.concat([chain(_flat_price), chain(_flat_price, expiry=near)], ignore_index=True)
    out = R.build_name_day(ch, spot=FLAT_SPOT, asof=ASOF, symbol="X", r=RATE)
    assert len(out) == 2, [s.expiry for s in out]
    assert sum(s.usable for s in out) == 1
    assert any(s.reasons == ("dte_out_of_band",) for s in out)


def test_coverage_census_counts_and_attributes():
    near = ASOF + pd.Timedelta(days=3)
    ch = pd.concat([chain(_flat_price), chain(_flat_price, expiry=near)], ignore_index=True)
    cen = R.coverage_census(R.build_name_day(ch, spot=FLAT_SPOT, asof=ASOF, r=RATE))
    assert cen["n_slices"] == 2 and cen["n_usable"] == 1
    assert cen["refusal_reasons"].get("dte_out_of_band") == 1
    assert cen["method"] == R.METHOD and cen["citations"]


def test_summary_is_json_safe_and_carries_its_diagnostics():
    import json
    payload = json.dumps(_mix_slice().summary())
    back = json.loads(payload)
    assert back["usable"] is True
    assert set(back["tail_mass"]) == {str(f) for f in R.TAIL_THRESHOLDS}
    assert "negative_mass" in back["diagnostics"] and "integral" in back["diagnostics"]
    assert back["method"] == R.METHOD


def test_thresholds_are_pre_declared_and_include_the_consumers_own():
    """O-1's K2 reads Q(S_T <= 0.5 S_0); its section 3 targets 0.70 moneyness. Both must be
    fixed in the module rather than chosen by a caller after seeing a density."""
    assert 0.50 in R.TAIL_THRESHOLDS and 0.70 in R.TAIL_THRESHOLDS
    assert tuple(sorted(R.TAIL_THRESHOLDS)) == R.TAIL_THRESHOLDS


def test_the_builder_is_deterministic():
    a, b = _mix_slice(), _mix_slice()
    for frac in R.TAIL_THRESHOLDS:
        assert a.tail_mass[frac] == b.tail_mass[frac], frac


def test_tail_masses_are_probabilities():
    for s in (_flat_slice(), _mix_slice()):
        for frac, v in s.tail_mass.items():
            assert 0.0 <= v <= 1.0, (frac, v)


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                       # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
