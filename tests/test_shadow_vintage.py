"""V1 shadow-vintage tests.

Run: python tests/test_shadow_vintage.py

Every frozen parameter is pinned to a LITERAL here, not recomputed from the module, so a silent
retune fails a test instead of quietly agreeing with itself. Same discipline as
tests/test_track_meter.py, and for the same reason: the register
(PREREG_v1_shadow_vintages.md) is only worth something if a later edit cannot move it.
"""
import ast
import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import shadow_vintage as SV       # noqa: E402
from valuation.edge import track_meter as TM          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ frozen parameters
def test_the_frozen_parameters_are_the_registered_ones():
    assert SV.CONTRACT_VERSION == "V1-shadow-vintages-2026-08-10"
    assert SV.RHO == 3.0
    assert SV.ALPHA == 0.05
    assert SV.VERDICT_MONTHS == 60
    assert SV.MIN_MONTHS_FOR_ANY_VERDICT == 6
    assert SV.MIN_WEIGHT_OVERLAP == 0.20
    assert abs(SV.DESIGN_EFFECT - 1.4660914) < 1e-6


def test_rho_and_alpha_are_the_contracts_and_not_a_second_copy():
    """A second declaration of the same constant is a second record free to drift from the
    document Don signed. These must BE the contract's, not merely equal to them today."""
    assert SV.RHO is TM.RHO and SV.ALPHA is TM.ALPHA
    src = open(os.path.join(ROOT, "valuation", "edge", "shadow_vintage.py"),
               encoding="utf-8").read()
    for bad in ("RHO = 3.0", "ALPHA = 0.05"):
        assert bad not in src, f"shadow_vintage re-declares {bad} instead of importing it"


def test_the_design_effect_inflation_is_load_bearing():
    """Without the AR(1) inflation the boundary is narrower and the guarantee breaks -- the
    vs-SPY meter measured 6.7% false crossings against a nominal 5% when it was removed. If a
    later edit drops it, sigma falls and this fails."""
    te = 6.0
    with_it = SV.sigma_monthly_pp(te)
    without = te / math.sqrt(12.0)
    assert with_it > without * 1.2, "the design-effect inflation has gone missing"
    assert abs(with_it / without - math.sqrt(1.4660914)) < 1e-6


def test_sigma_reproduces_the_contract_meter_at_the_contracts_own_tracking_error():
    """The control. Fed the vs-SPY meter's own TE of 11.40pp/yr, this machinery must reproduce
    the contract's published sigma 3.9847 and its published ~19pp/yr at 60 months -- because it
    is the same boundary function, imported. Disagreement means one meter has drifted."""
    s = SV.sigma_monthly_pp(11.40)
    assert abs(s - TM.SIGMA_MONTHLY_PP) < 1e-12, f"{s} != {TM.SIGMA_MONTHLY_PP}"
    assert abs(s - 3.9847) < 1e-3
    assert abs(SV.detectable_difference_pp_per_year(60, s) - 19.01) < 0.05
    assert abs(SV.boundary(60, s) - TM.boundary(60)) < 1e-12


def test_sigma_refuses_a_non_positive_tracking_error():
    """A zero-sigma meter crosses on the first observation, in both directions, forever."""
    for bad in (0.0, -1.0):
        try:
            SV.sigma_monthly_pp(bad)
            raise AssertionError(f"accepted TE {bad}")
        except ValueError:
            pass


def test_the_power_table_in_the_register_is_what_the_code_computes():
    """Pins the published table (PREREG §1) cell by cell, so the register cannot go stale."""
    for te, sig, d12, d36, d60 in ((2.0, 0.6991, 7.46, 4.26, 3.34),
                                   (4.0, 1.3981, 14.93, 8.51, 6.67),
                                   (6.0, 2.0972, 22.39, 12.77, 10.01),
                                   (11.40, 3.9847, 42.55, 24.26, 19.01)):
        s = SV.sigma_monthly_pp(te)
        assert abs(s - sig) < 5e-4, f"TE {te}: sigma {s} != {sig}"
        for n, want in ((12, d12), (36, d36), (60, d60)):
            got = SV.detectable_difference_pp_per_year(n, s)
            assert abs(got - want) < 0.02, f"TE {te} at {n}m: {got} != {want}"


def test_the_instrument_is_weaker_than_it_looks_and_the_module_says_so():
    """The register commits IN ADVANCE that a non-crossing pair is the expected outcome. That
    sentence must survive in the code's own output, not only in a markdown file nobody opens."""
    v = SV.verdict([0.05] * 12, SV.sigma_monthly_pp(4.0))
    assert v["verdict"] == "NULL"
    assert "EXPECTED outcome" in v["why"] and "NOT evidence" in v["why"]
    assert "detectable_pp_per_year" in v


# ------------------------------------------------------------------ snapshots
def test_a_snapshot_is_order_independent_and_hashes_the_model():
    a = SV.snapshot({"theme_weights": {"b": 0.5, "a": 0.5}, "sector_neutral": False})
    b = SV.snapshot({"sector_neutral": False, "theme_weights": {"a": 0.5, "b": 0.5}})
    assert a["params_id"] == b["params_id"]
    assert SV.same_model(a, b)


def test_a_snapshot_ignores_keys_that_do_not_define_the_model():
    a = SV.snapshot({"theme_weights": {"a": 1.0}})
    b = SV.snapshot({"theme_weights": {"a": 1.0}, "run_id": "whatever", "as_of": "2026-08-10"})
    assert SV.same_model(a, b), "an incidental key changed the model's identity"


def test_a_real_parameter_change_changes_the_id():
    a = SV.snapshot({"theme_weights": {"quality": 0.125}, "sector_neutral": False})
    for changed in ({"theme_weights": {"quality": 0.126}, "sector_neutral": False},
                    {"theme_weights": {"quality": 0.125}, "sector_neutral": True}):
        assert not SV.same_model(a, SV.snapshot(changed))


def test_vintage_2s_parameters_are_pinned_now_while_nothing_can_be_compared():
    """The pre-registration's whole claim. Vintage 2's snapshot is in a tracked file BEFORE any
    successor exists, so it cannot be reconstructed later to suit a comparison."""
    snap = SV.pinned_snapshot(2)
    assert snap and snap["params_id"] == "0060c5ef3dda"
    assert SV.PINNED[2]["opened"] == dt.date(2026, 8, 10) == TM.INCEPTION
    weights = snap["params"]["theme_weights"]
    assert weights["low_risk"] == 0.0, "low_risk is zeroed in the deployed model"
    assert abs(sum(weights.values()) - 0.875) < 1e-9, "seven themes at a flat 1/8 each"
    assert snap["params"]["sector_neutral"] is False, "the intervention research rejected"


def test_param_keys_are_the_registered_set():
    """Widening this silently redefines what 'the same model' means, so it is pinned."""
    assert SV.PARAM_KEYS == ("theme_weights", "sector_neutral", "residual_momentum",
                             "ev_point_in_time", "large_cap_min", "top_decile", "max_weight",
                             "weighting", "top_n")


# ------------------------------------------------------------------ divergence
def test_identical_books_have_full_overlap_and_disjoint_books_have_none():
    same = [{"ticker": "A", "weight": 0.5}, {"ticker": "B", "weight": 0.5}]
    d = SV.divergence(same, list(same))
    assert abs(d["weight_overlap"] - 1.0) < 1e-9 and d["n_shared"] == 2 and d["comparable"]

    d2 = SV.divergence(same, [{"ticker": "C", "weight": 1.0}])
    assert abs(d2["weight_overlap"]) < 1e-9 and d2["n_shared"] == 0
    assert d2["comparable"] is False


def test_overlap_notices_a_reweighting_that_name_counts_cannot():
    """Two books can hold the SAME names and be different portfolios. A shared-name count says
    they are identical; the overlap measure is the one that notices."""
    a = [{"ticker": "A", "weight": 0.9}, {"ticker": "B", "weight": 0.1}]
    b = [{"ticker": "A", "weight": 0.1}, {"ticker": "B", "weight": 0.9}]
    d = SV.divergence(a, b)
    assert d["n_shared"] == 2 and d["n_only_live"] == 0
    assert abs(d["weight_overlap"] - 0.2) < 1e-9, d["weight_overlap"]


def test_divergence_survives_empty_books():
    d = SV.divergence([], [])
    assert d["n_live"] == 0 and d["comparable"] is False


# ------------------------------------------------------------------ the verdict
def _sig():
    return SV.sigma_monthly_pp(4.0)


def test_no_verdict_below_the_minimum_months():
    v = SV.verdict([5.0] * 5, _sig())
    assert v["verdict"] == "INSUFFICIENT" and v["n_months"] == 5
    assert "no verdict is available and none is implied" in v["why"]


def test_an_incomparable_pair_is_refused_before_anything_is_computed():
    """Checked FIRST, and it must beat even a hugely crossing series -- a paired difference
    between two unrelated books does not measure the adoption."""
    v = SV.verdict([50.0] * 60, _sig(), weight_overlap=0.05)
    assert v["verdict"] == "NOT-COMPARABLE"
    assert "does not measure the adoption" in v["why"]


def test_a_pair_at_the_overlap_floor_is_still_comparable():
    v = SV.verdict([0.0] * 12, _sig(), weight_overlap=SV.MIN_WEIGHT_OVERLAP)
    assert v["verdict"] == "NULL", "the floor is inclusive"


def test_a_large_sustained_difference_crosses_in_the_right_direction():
    s = _sig()
    n = 24
    per_month = SV.boundary(n, s) / n * 1.5          # comfortably over the boundary
    v = SV.verdict([per_month] * n, s, weight_overlap=0.9)
    assert v["crossed"] and v["verdict"] == "CONFIRMED-LIVE"
    v2 = SV.verdict([-per_month] * n, s, weight_overlap=0.9)
    assert v2["crossed"] and v2["verdict"] == "HARMED"


def test_the_verdict_has_no_sign_branch():
    """Flipping the sign of an ENTIRE series must flip the verdict and move nothing else. This
    is what makes HARMED as reachable as CONFIRMED-LIVE, which is the property that stops this
    becoming an instrument that can only deliver good news."""
    s = _sig()
    series = [0.9, -0.2, 1.4, 0.7, -0.1, 1.1, 0.8, 1.9, 0.4, 1.2, 0.6, 1.5]
    a = SV.verdict(series, s, weight_overlap=0.8)
    b = SV.verdict([-x for x in series], s, weight_overlap=0.8)
    assert abs(a["cumulative_diff_pp"] + b["cumulative_diff_pp"]) < 1e-9
    assert a["boundary_pp"] == b["boundary_pp"]
    assert a["crossed"] == b["crossed"]
    assert {a["verdict"], b["verdict"]} in ({"NULL"}, {"CONFIRMED-LIVE", "HARMED"})

    src = open(os.path.join(ROOT, "valuation", "edge", "shadow_vintage.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "verdict")
    # exactly ONE sign test in the whole function: the one that names the crossing direction
    signs = [n for n in ast.walk(fn) if isinstance(n, ast.Compare)
             and any(isinstance(o, (ast.Gt, ast.Lt)) for o in n.ops)
             and any(isinstance(c, ast.Constant) and c.value == 0 for c in n.comparators)]
    assert len(signs) == 1, f"{len(signs)} sign branches in verdict(); expected exactly 1"


def test_a_null_always_carries_what_it_could_have_detected():
    v = SV.verdict([0.01] * 30, _sig(), weight_overlap=0.9)
    assert v["verdict"] == "NULL"
    assert v["detectable_pp_per_year"] > 0
    assert f"{v['detectable_pp_per_year']:.2f}" in v["why"]


# ------------------------------------------------------------------ status and scope
def test_detail_is_not_vacuously_green_before_a_pair_exists():
    """The failure track_meter had to fix: a healthy-looking object full of zeros, reported
    before the thing it describes had started."""
    d = SV.detail()
    assert d["active"] is False and d["n_pairs"] == 0 and d["pairs"] == []
    assert "no vintage pair exists yet" in d["status"]
    assert "no verdict of any kind is available" in d["status"]
    assert d["current_vintage"] == 2


def test_detail_names_its_own_scope():
    assert "never" in SV.detail()["public_surface"]


def test_frozen_parameters_expose_the_sigma_estimator_in_words():
    fp = SV.frozen_parameters()
    assert "never revised downward" in fp["sigma_estimator"]
    assert fp["pinned"][2]["params_id"] == "0060c5ef3dda"
    assert fp["pinned"][2]["opened"] == "2026-08-10"


def test_the_shadow_never_reaches_an_outbound_surface():
    """Fenced BEFORE it has any numbers to leak. PT-OUTBOUND is why: a research object reached
    Discord and published +0.18pp while the bound recorder read -2.85pp."""
    outbound = []
    for sub in ("valuation/saas", "valuation/web"):
        base = os.path.join(ROOT, *sub.split("/"))
        for dirpath, _dirs, files in os.walk(base):
            outbound += [os.path.join(dirpath, f) for f in files if f.endswith(".py")]
    offenders = []
    for path in outbound:
        try:
            src = open(path, encoding="utf-8").read()
        except OSError:
            continue
        if "shadow_vintage" in src:
            offenders.append(os.path.relpath(path, ROOT))
    assert not offenders, ("shadow vintages reached an outbound surface: " + ", ".join(offenders))


def test_no_public_template_mentions_a_shadow_vintage():
    tpl = os.path.join(ROOT, "valuation", "web", "templates")
    hits = []
    if os.path.isdir(tpl):
        for dirpath, _d, files in os.walk(tpl):
            for f in files:
                try:
                    s = open(os.path.join(dirpath, f), encoding="utf-8").read().lower()
                except OSError:
                    continue
                if "shadow vintage" in s or "shadow_vintage" in s:
                    hits.append(f)
    assert not hits, f"a template renders the shadow: {hits}"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} shadow-vintage tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
