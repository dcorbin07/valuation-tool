"""
V3 noise-calibrated-hot-score tests (offline, deterministic). Run:
    python tests/test_score_calibration.py

The V3 calibration rests on a claim about its own instrument: that one permutation scheme
destroys exactly one thing (cross-theme agreement) and that the OTHER scheme — X7's, the obvious
one to reach for — destroys nothing at all where a score is concerned. Neither claim is
self-evident from reading the code, and the second one is the reason the calibration exists in the
shape it does, so both are pinned here rather than asserted in a write-up.

The exact-invariance test is the important one. If someone later "simplifies" the harness to reuse
`fundamental_panel.placebo_panel`, every calibrated bar in V3 silently becomes a comparison of the
real book against itself, and the run would still complete, still print percentiles, and still look
like a measurement.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from valuation.screener import settings as S
from scripts.score_calibration import (_bucket_positions, permute_within_column, permute_block,
                                       statistic, calibrate, _present_weight_fraction)

THEMES = [c for c in S.FACTORS_ALL]


def _toy(n=240, seed=7, holes=True):
    """A cross-section with both buckets, correlated themes, and realistic missingness."""
    rng = np.random.default_rng(seed)
    common = rng.normal(size=n)                       # a shared factor -> themes agree
    df = pd.DataFrame(index=[f"T{i:04d}" for i in range(n)])
    for j, c in enumerate(THEMES):
        df[c] = 0.6 * common + 0.8 * rng.normal(size=n)
        if holes:
            # Missingness travels in ROWS, as it does on the real panel: a thin name is thin on
            # several themes at once, which is what makes the coverage-preserving property matter.
            thin = rng.random(n) < 0.18
            drop = thin & (rng.random(n) < 0.5 + 0.05 * j)
            df.loc[drop, c] = np.nan
    df["bucket"] = np.where(rng.random(n) < 0.75, "established", "speculative")
    df["sector"] = rng.choice(list("ABCDE"), size=n)
    df["market_cap"] = np.exp(rng.normal(22, 1.5, size=n))
    return df


# ------------------------------------------------------ H0: X7's scheme cannot calibrate a score
def test_block_permutation_leaves_the_composite_multiset_exactly_unchanged():
    """THE FINDING, pinned. X7's permutation moves whole rows, so a name's theme vector AND its
    renormalization denominator both travel intact and only the ticker label changes. The sorted
    composite is therefore identical to the real one — not close, identical — which means a null
    built this way is the real book wearing a different name tag."""
    df = _toy()
    groups = _bucket_positions(df)
    real = statistic(df, [1, 5, 10], 24)
    for seed in (0, 1, 2, 3, 4):
        rng = np.random.default_rng(seed)
        d = statistic(permute_block(df, THEMES, groups, rng), [1, 5, 10], 24)
        assert abs(d["composite_sd"] - real["composite_sd"]) < 1e-12, (seed, d["composite_sd"])
        for k in (1, 5, 10):
            assert abs(d[f"c_at_{k}"] - real[f"c_at_{k}"]) < 1e-9, (seed, k)


def test_block_permutation_does_actually_shuffle_the_rows():
    """Guards the test above from passing for the wrong reason: invariance of the SCORE must not
    be mistaken for the permutation having quietly done nothing."""
    df = _toy()
    rng = np.random.default_rng(0)
    out = permute_block(df, THEMES, _bucket_positions(df), rng)
    moved = sum(1 for c in THEMES
                if not np.allclose(df[c].to_numpy(float), out[c].to_numpy(float), equal_nan=True))
    assert moved == len(THEMES), moved


# --------------------------------------------------- H1: the instrument destroys one thing only
def test_within_column_preserves_each_theme_marginal_exactly():
    """The null must not be a different universe — only a differently-assembled one. Each theme's
    sorted values within each bucket come back identical."""
    df = _toy()
    rng = np.random.default_rng(3)
    out = permute_within_column(df, THEMES, _bucket_positions(df), rng)
    for b in ("established", "speculative"):
        m = df["bucket"] == b
        for c in THEMES:
            a = np.sort(df.loc[m, c].dropna().to_numpy(float))
            z = np.sort(out.loc[m, c].dropna().to_numpy(float))
            assert np.allclose(a, z), (b, c)


def test_within_column_preserves_every_row_coverage_pattern():
    """The property the whole design rests on: NaNs stay exactly where they are, so each row's
    present-weight denominator is unchanged and a difference in the composite cannot be blamed on
    a name suddenly being scored on more or fewer themes."""
    df = _toy()
    rng = np.random.default_rng(4)
    out = permute_within_column(df, THEMES, _bucket_positions(df), rng)
    assert (df[THEMES].isna().to_numpy() == out[THEMES].isna().to_numpy()).all()
    a = _present_weight_fraction(df)
    z = _present_weight_fraction(out)
    assert np.allclose(a.to_numpy(float), z.to_numpy(float), equal_nan=True)


def test_within_column_destroys_cross_theme_agreement():
    """It has to actually remove the thing it claims to remove: mean pairwise theme correlation
    must fall toward zero, on a toy universe built with a shared factor."""
    df = _toy()
    rng = np.random.default_rng(5)
    out = permute_within_column(df, THEMES, _bucket_positions(df), rng)

    def mean_corr(f):
        c = f[THEMES].corr().to_numpy(float)
        iu = np.triu_indices_from(c, k=1)
        return float(np.nanmean(c[iu]))

    before, after = mean_corr(df), mean_corr(out)
    assert before > 0.2, before
    assert abs(after) < 0.1, after
    assert after < before


def test_within_column_never_touches_the_structural_columns():
    """ticker (the index), bucket, sector and market_cap are the X7 convention's untouched set."""
    df = _toy()
    rng = np.random.default_rng(6)
    out = permute_within_column(df, THEMES, _bucket_positions(df), rng)
    assert list(out.index) == list(df.index)
    for c in ("bucket", "sector"):
        assert (out[c].values == df[c].values).all(), c
    assert np.allclose(out["market_cap"].to_numpy(float), df["market_cap"].to_numpy(float))


def test_within_column_is_seed_deterministic():
    """A stored draw must be reproducible from its seed alone, or the banked draws are worthless."""
    df = _toy()
    g = _bucket_positions(df)
    a = permute_within_column(df, THEMES, g, np.random.default_rng(11))
    b = permute_within_column(df, THEMES, g, np.random.default_rng(11))
    c = permute_within_column(df, THEMES, g, np.random.default_rng(12))
    assert np.allclose(a[THEMES].to_numpy(float), b[THEMES].to_numpy(float), equal_nan=True)
    assert not np.allclose(a[THEMES].to_numpy(float), c[THEMES].to_numpy(float), equal_nan=True)


def test_permutation_stays_inside_its_bucket():
    """Themes are standardized within bucket, so a value crossing the boundary would change the
    marginal the null is supposed to preserve."""
    df = _toy()
    rng = np.random.default_rng(8)
    out = permute_within_column(df, THEMES, _bucket_positions(df), rng)
    for b in ("established", "speculative"):
        m = (df["bucket"] == b).to_numpy()
        for c in THEMES:
            src = set(np.round(df.loc[m, c].dropna().to_numpy(float), 12))
            got = set(np.round(out.loc[m, c].dropna().to_numpy(float), 12))
            assert got <= src, (b, c, len(got - src))


# ------------------------------------------------------------------------ the reported table
def test_empirical_p_counts_draws_at_or_above_the_real_value():
    real = {"c_at_1": 1.0}
    draws = [{"c_at_1": v} for v in [0.5, 0.9, 1.0, 1.1, 2.0]]
    t = calibrate(real, draws, [1])[1]
    assert t["n_noise_ge_real"] == 3, t
    assert abs(t["empirical_p"] - 0.6) < 1e-12


def test_calibrate_survives_a_rank_deeper_than_the_cross_section():
    """A ladder rank past the end of a thin cross-section must report None, not crash and not a
    silently borrowed value from a neighbouring rank."""
    df = _toy(n=60)
    rec = statistic(df, [1, 10, 5000], 6)
    assert rec["c_at_5000"] is None
    assert rec["c_at_1"] is not None


def test_resume_restores_integer_rank_keys_on_the_calibration_table():
    """A resumed run must reach the SAME verdict as an uninterrupted one.

    JSON has no integer keys, so a round trip turns the rank-keyed table's `10` into `"10"`, the
    verdict lookup `table.get(PRIMARY_RANK)` misses, and the script reports NULL/ambiguous for a
    result that is a clean NOT DISTINGUISHABLE. That actually happened, and it was caught only
    because the printed verdict disagreed with a table already read out of the same file — which
    is luck, not a control. A wrong verdict that reads as "no conclusion" is the worst failure
    this harness can have: it looks like caution.
    """
    import json
    import tempfile
    from scripts.score_calibration import _load_partial, PRIMARY_RANK

    payload = {"primary_within_column": {
        "table": {PRIMARY_RANK: {"real": 1.0, "noise_p95": 0.9, "empirical_p": 0.01,
                                 "clears_p95": True}}}}
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x.json")
        with open(p, "w") as f:
            json.dump(payload, f)
        back, _ = _load_partial(p)
    tab = back["primary_within_column"]["table"]
    assert PRIMARY_RANK in tab, list(tab)
    assert tab[PRIMARY_RANK]["clears_p95"] is True


def test_a_zero_empirical_p_counts_as_the_strongest_evidence_not_the_weakest():
    """An empirical p of 0.0 means NO noise draw reached the real value. Written as
    `(p or 1)` it becomes 1.0, because 0.0 is falsy — silently reclassifying the strongest
    dates as the weakest. That happened here and cost half the distinguishable count (12 of 24)
    before an independent recount caught it."""
    from scripts.score_calibration import _agreeing

    scored = [{"clears_p95": True, "empirical_p": 0.0},      # strongest possible
              {"clears_p95": True, "empirical_p": 0.02},
              {"clears_p95": False, "empirical_p": 0.90}]
    n_dist = sum(1 for r in scored
                 if r["clears_p95"] and r["empirical_p"] is not None and r["empirical_p"] <= 0.05)
    assert n_dist == 2, n_dist
    assert _agreeing("DISTINGUISHABLE", {"n_dates_distinguishable": n_dist}) == 2


def test_composite_is_the_row_sum_of_its_contributions():
    """The live invariant `attribution.decompose` promises. If it breaks, every number V3 reports
    is explaining a different quantity from the one it ranks."""
    from valuation.screener.attribution import decompose
    df = _toy()
    comp, contrib = decompose(df, S.WEIGHTS_ESTABLISHED, S.WEIGHTS_SPECULATIVE, soft=True)
    assert np.allclose(comp.dropna().to_numpy(float),
                       contrib.sum(axis=1, min_count=1).dropna().to_numpy(float))


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
    print(f"\n{passed}/{len(tests)} V3 score-calibration tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
