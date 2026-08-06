"""
R1 fragility tests (offline, deterministic). Run:
    python tests/test_factor_alpha_fragility.py

The fragility verdict rests on four criteria pre-committed in HANDOFF_r1.md section 6. These
tests pin the machinery each criterion depends on -- above all the per-period alpha
decomposition, whose defining property (the contributions sum to n * alpha) is what makes the
"share from the best k periods" number mean anything at all -- and pin the constants, so the
thresholds cannot drift away from what was committed.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from scripts.factor_alpha import FF_MODEL, PPY
from scripts.factor_alpha_fragility import (concentration, overlap_check, rolling_alpha,
                                            MODELS, STABLE_FROM, CONCENTRATION_LIMIT, T_BAR)


def _frame(n=80, seed=0, alpha=0.02):
    """A synthetic top/ew series with a known intercept over known factors."""
    rng = np.random.default_rng(seed)
    F = rng.normal(scale=0.04, size=(n, len(FF_MODEL)))
    beta = np.array([0.1, 0.4, 0.1, 0.3, 0.1, 0.2])
    y = alpha + F @ beta + rng.normal(scale=0.02, size=n)
    idx = pd.bdate_range("2000-01-07", periods=n, freq="63B")
    d = pd.DataFrame(F, columns=FF_MODEL, index=idx)
    d["ew"] = 0.0
    d["top"] = y
    return d


# ------------------------------------------------------------ the pre-committed constants
def test_constants_match_the_precommitment():
    """HANDOFF_r1.md 6a fixed these before any cut ran; they must not drift."""
    assert STABLE_FROM == "2008-01-01"
    assert CONCENTRATION_LIMIT == 0.50
    assert T_BAR == 2.0


def test_model_set_is_the_one_that_was_committed():
    assert set(MODELS) == {"CAPM", "FF3", "FF5 (no momentum)", "FF5+MOM", "q4", "q5"}
    assert MODELS["CAPM"][0] == ["MKT"]
    assert MODELS["FF3"][0] == ["MKT", "SMB", "HML"]
    assert "UMD" not in MODELS["FF5 (no momentum)"][0]
    assert "UMD" in MODELS["FF5+MOM"][0]


# ------------------------------------------------------------ concentration
def test_alpha_contributions_sum_to_n_times_alpha():
    """The defining identity. Without it, 'share of alpha from the best k' is meaningless."""
    d = _frame()
    c = concentration(d, FF_MODEL)
    # total_alpha_sum == n * alpha_63d == n * alpha_ann / PPY
    expected = c["n_full"] * c["alpha_ann_full"] / PPY
    assert abs(c["total_alpha_sum"] - expected) < 1e-9, (c["total_alpha_sum"], expected)


def test_shares_are_ordered_and_bounded():
    c = concentration(_frame(), FF_MODEL)
    s1 = c["share_from_best"]["best_1"]
    s3 = c["share_from_best"]["best_3"]
    s5 = c["share_from_best"]["best_5"]
    assert 0 < s1 < s3 < s5, (s1, s3, s5)
    assert s5 < 1.0


def test_dropping_the_best_lowers_alpha_and_dropping_the_worst_raises_it():
    c = concentration(_frame(), FF_MODEL)
    base = c["alpha_ann_full"]
    assert c["drop_best"]["drop_best_1"]["alpha_ann"] < base
    assert c["drop_best"]["drop_best_5"]["alpha_ann"] < c["drop_best"]["drop_best_1"]["alpha_ann"]
    assert c["drop_worst_5"]["alpha_ann"] > base


def test_drop_best_k_removes_exactly_k_periods():
    c = concentration(_frame(n=60), FF_MODEL)
    assert c["n_full"] == 60
    for k in (1, 3, 5):
        assert c["drop_best"][f"drop_best_{k}"]["n"] == 60 - k


def test_a_single_dominant_period_is_detected_as_concentration():
    """A planted outlier must push the best-1 share up, or the criterion cannot fire."""
    d = _frame(seed=3)
    clean = concentration(d, FF_MODEL)["share_from_best"]["best_1"]
    d = d.copy()
    d.iloc[10, d.columns.get_loc("top")] += 8.0        # one enormous period
    spiked = concentration(d, FF_MODEL)["share_from_best"]["best_1"]
    assert spiked > clean * 3, (clean, spiked)
    # the criterion in HANDOFF_r1.md 6a trips above 50%; a period this dominant must trip it
    assert spiked > CONCENTRATION_LIMIT, spiked


# ------------------------------------------------------------ overlap
def _ff_for_overlap(starts, ends, days=63):
    ff = pd.DataFrame({"end": pd.DatetimeIndex(ends),
                       "n_days": [days] * len(ends)},
                      index=pd.DatetimeIndex(starts))
    return ff


def test_overlap_check_passes_on_adjacent_windows():
    """Window i is (d_i, d_i+1]: end_i == start_i+1 is adjacency, NOT overlap."""
    g = pd.bdate_range("2000-01-07", periods=6, freq="63B")
    ff = _ff_for_overlap(g[:-1], g[1:])
    strat = pd.DataFrame(index=g)
    o = overlap_check(strat, ff)
    assert o["windows_are_non_overlapping"] is True
    assert o["consecutive_windows_sharing_a_day"] == 0
    assert o["end_equals_next_start"] is True
    assert o["all_windows_exactly_63_days"] is True


def test_overlap_check_detects_a_real_overlap():
    """If a window ended AFTER the next one started, inference would need correcting."""
    g = pd.bdate_range("2000-01-07", periods=6, freq="63B")
    ends = list(g[1:])
    ends[0] = g[2]                                     # window 0 now runs past window 1's start
    ff = _ff_for_overlap(g[:-1], ends)
    o = overlap_check(pd.DataFrame(index=g), ff)
    assert o["windows_are_non_overlapping"] is False
    assert o["consecutive_windows_sharing_a_day"] >= 1


def test_overlap_check_flags_a_wrong_length_window():
    g = pd.bdate_range("2000-01-07", periods=4, freq="63B")
    ff = _ff_for_overlap(g[:-1], g[1:])
    ff.loc[ff.index[1], "n_days"] = 61
    o = overlap_check(pd.DataFrame(index=g), ff)
    assert o["all_windows_exactly_63_days"] is False
    assert o["window_days_min"] == 61


# ------------------------------------------------------------ rolling
def test_rolling_window_count_and_bounds():
    d = _frame(n=80)
    r = rolling_alpha(d, FF_MODEL, window=40)
    assert r["n_windows"] == 80 - 40 + 1
    assert len(r["series"]) == r["n_windows"]
    assert r["alpha_min"] <= r["alpha_median"] <= r["alpha_max"]
    assert 0.0 <= r["share_positive"] <= 1.0


def test_rolling_recovers_a_planted_constant_alpha():
    """With a constant true alpha, every rolling window should find roughly it."""
    d = _frame(n=90, seed=11, alpha=0.03)
    r = rolling_alpha(d, FF_MODEL, window=40)
    assert r["share_positive"] == 1.0
    assert abs(r["alpha_median"] - 0.03 * PPY) < 0.03, r["alpha_median"]


def test_rolling_sees_a_regime_that_the_full_sample_average_hides():
    """The point of the test: a dead second half must show up as weak windows."""
    d = _frame(n=90, seed=5, alpha=0.03)
    d = d.copy()
    d.iloc[45:, d.columns.get_loc("top")] -= 0.03      # second half has no alpha
    r = rolling_alpha(d, FF_MODEL, window=30)
    assert r["alpha_min"] < 0.5 * r["alpha_max"], (r["alpha_min"], r["alpha_max"])


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
    print(f"\n{passed}/{len(tests)} R1 fragility tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
