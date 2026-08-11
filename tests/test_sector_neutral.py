"""
Sector-neutral ranking: the wiring, not the verdict. Run:
    python tests/test_sector_neutral.py

Background. `sector_neutral` is a config toggle that has existed since Batch 2, but
`build_fundamental_panel` hard-coded `"sector": ""` for every row, so `build_frame`
grouped on a CONSTANT and the sector-neutral path subtracted a median computed over the
whole universe from itself — an exact no-op. It was silently INERT in every backtest this
project ever ran (CODE_AUDIT M3), and nothing failed, warned, or looked different: turning
the toggle on produced byte-identical numbers.

That is the same failure class as the five empty factors and the dropped `assets` column —
a wired thing quietly doing nothing. So these tests pin the WIRING:

  * the panel populates `sector` from the provider's TICKERS overlay,
  * the panel emits a `sector` column,
  * with real sectors the toggle CHANGES the numbers,
  * with blank sectors it is a provable no-op (the exact bug's signature).

They deliberately do NOT pin whether sector-neutral is better. It was tested on the full
2,827-name universe (P10, re-confirmed 2026-08-02) and REJECTED in both held-out split
directions; `HANDOFF_sector_neutral.md` has the numbers. The verdict is a research finding
that may change; the wiring must not silently revert either way.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from valuation.screener.factors import build_frame


# --------------------------------------------------------------------------- #
#  fixtures
# --------------------------------------------------------------------------- #
def _metrics(sectors):
    """One name per entry in `sectors`, with a strong SECTOR-LEVEL offset baked in.

    Utilities are given systematically fat earnings yields and Technology systematically
    thin ones — exactly the accidental sector bet that sector-neutral scoring is supposed
    to remove. Within a sector the names still fan out, so a sector-relative ranking is
    well defined.
    """
    out = []
    offs = {"Utilities": 0.10, "Technology": 0.0, "Healthcare": 0.05}
    n_in = {s: sectors.count(s) for s in set(sectors)}
    seen = {}
    for i, sec in enumerate(sectors):
        base = offs.get(sec, 0.0)
        # Rank WITHIN the sector, so the only cross-sector difference is `base` and the
        # sector effect is cleanly separable from the within-sector fan-out.
        k = seen[sec] = seen.get(sec, -1) + 1
        rank = k / max(1, n_in[sec] - 1)
        out.append({
            "ticker": f"T{i:03d}", "sector": sec,
            "price": 10.0 + i, "market_cap": 1e9 * (i + 1),
            "revenue": 1e9, "net_income": 1e8, "operating_income": 1.2e8,
            "earnings_yield": base + 0.01 * rank,
            "fcf_yield": base + 0.008 * rank,
            "ebit_ev": base + 0.012 * rank,
            "book_to_price": 0.5 + base + 0.1 * rank,
            # These must also fan out WITHIN a sector: a column that is constant inside
            # each group demedians to exactly zero, and zscore() of a constant column is
            # all-NaN, which would make the test vacuous rather than failing loudly.
            "op_margin": 0.10 + base + 0.02 * rank,
            "gross_margin": 0.35 + base + 0.03 * rank,
            "roe": 0.10 + base + 0.02 * rank,
            "roic": 0.08 + base + 0.02 * rank,
            "ret_12_1": 0.05 + base + 0.04 * rank,
            "ret_6_1": 0.03 + base + 0.03 * rank,
        })
    return out


_SECTORS = (["Utilities"] * 8 + ["Technology"] * 8 + ["Healthcare"] * 8)


# --------------------------------------------------------------------------- #
#  the wiring
# --------------------------------------------------------------------------- #
def test_sector_neutral_changes_the_numbers_when_sectors_are_real():
    """THE regression test. With a real sector column the toggle must move the composite.

    Before the TICKERS overlay was wired in, this assertion would have FAILED — ON and OFF
    were identical to the last bit, which is precisely why the inertness went unnoticed
    for the project's entire history.
    """
    m = _metrics(_SECTORS)
    off = build_frame(m, sector_neutral=False, residual_momentum=False)
    on = build_frame(m, sector_neutral=True, residual_momentum=False)
    moved = []
    for col in ("value", "quality", "momentum"):
        a, b = off[col], on[col]
        mask = a.notna() & b.notna()
        assert mask.any(), f"{col} is entirely NaN in the fixture — test is not measuring anything"
        moved.append(float((a[mask] - b[mask]).abs().mean()))
    assert max(moved) > 0.05, f"sector_neutral did not change any theme: {moved}"


def test_sector_neutral_is_a_provable_noop_when_every_sector_is_blank():
    """The exact signature of the shipped bug: a constant sector column.

    `x - median(x)` over one group is a pure shift, and the z-score that follows is
    shift-invariant, so ON and OFF must agree EXACTLY. Keeping this pinned means that if
    the sector overlay ever silently stops populating, the test above flips to failing
    rather than the whole feature going quiet again.
    """
    m = _metrics([""] * 24)
    off = build_frame(m, sector_neutral=False, residual_momentum=False)
    on = build_frame(m, sector_neutral=True, residual_momentum=False)
    for col in ("value", "quality", "momentum"):
        a, b = off[col], on[col]
        mask = a.notna() & b.notna()
        assert mask.any(), col
        worst = float((a[mask] - b[mask]).abs().max())
        assert worst < 1e-9, f"{col}: blank sectors must be a no-op, max delta {worst}"


def test_sector_neutral_removes_the_sector_level_offset():
    """The economic point: a whole cheap sector should stop sweeping the top of the book.

    The fixture hands Utilities a +10pp earnings-yield offset over Technology. Ranked
    against the whole universe, Utilities owns the top of `value`; ranked against sector
    peers, the sector's mean value score must collapse toward the others.
    """
    m = _metrics(_SECTORS)
    off = build_frame(m, sector_neutral=False, residual_momentum=False)
    on = build_frame(m, sector_neutral=True, residual_momentum=False)
    secs = np.array([x["sector"] for x in m])

    def spread(fr):
        means = [float(np.nanmean(fr["value"].values[secs == s])) for s in ("Utilities", "Technology")]
        return abs(means[0] - means[1])

    assert spread(on) < spread(off), (
        f"sector-neutral must SHRINK the cross-sector value spread "
        f"(off {spread(off):.3f} -> on {spread(on):.3f})")
    assert spread(on) < 0.35, f"residual cross-sector spread still large: {spread(on):.3f}"


def test_sector_median_is_used_not_the_global_median():
    """Pin the construction itself: subtract the SECTOR median, then z-score globally.

    A plausible-looking wrong implementation (subtract the global median, or z-score
    within sector and then again globally) would still 'change the numbers' and pass the
    first test. This checks the actual arithmetic on a single granular input.
    """
    m = _metrics(_SECTORS)
    fr = build_frame(m, sector_neutral=True, residual_momentum=False)
    raw = np.array([x["earnings_yield"] for x in m], dtype=float)
    secs = np.array([x["sector"] for x in m])
    expect = raw.copy()
    for s in set(secs):
        sel = secs == s
        expect[sel] = raw[sel] - np.median(raw[sel])
    got = fr["earnings_yield"].values.astype(float)
    assert np.nanmax(np.abs(got - expect)) < 1e-12, (
        f"earnings_yield is not sector-demedianed: max delta {np.nanmax(np.abs(got - expect))}")


# --------------------------------------------------------------------------- #
#  the source of the sector column
# --------------------------------------------------------------------------- #
def test_provider_ticker_meta_serves_the_tickers_overlay():
    """`ticker_meta` is what feeds `metrics["sector"]`; it must be case-insensitive and
    must degrade to {} rather than raise when the TICKERS cache was never built."""
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = "."

    prov = WRDSProvider(_C())
    prov._bulk_cache = getattr(prov, "_bulk_cache", {})
    # Inject a fake TICKERS cache through whatever memo `_bulk` uses, without touching disk.
    fake = {"AAPL": {"sector": "Technology", "industry": "Consumer Electronics",
                     "country": "USA", "exchange": "NASDAQ", "category": "", "scale": ""}}
    prov._bulk = lambda name, _f=fake: (_f if name == "tickers" else {})
    assert prov.ticker_meta("aapl").get("sector") == "Technology"
    assert prov.ticker_meta("AAPL").get("sector") == "Technology"
    assert prov.ticker_meta("NOSUCH") == {}, "unknown ticker must be {} not a raise"


def test_panel_no_longer_hardcodes_an_empty_sector():
    """Belt-and-braces: the literal `"sector": ""` that made this inert is gone from the
    scoring path, and the panel row carries a sector field sourced from the metrics."""
    import inspect
    from valuation.edge import fundamental_panel as F

    src = inspect.getsource(F.build_fundamental_panel)
    assert 'm["sector"] = ' in src, "panel must assign sector from the TICKERS overlay"
    assert '"sector": (' in src or '"sector": _' in src, "panel row must carry a sector value"
    # The only remaining `"sector": ""` may be the _sf1_to_metrics default, not the scorer.
    assert '"sector": "",' not in src, (
        'build_fundamental_panel still hard-codes an empty sector — sector_neutral is inert again')


# --------------------------------------------------------------------------- #
#  SECTOR-NEUTRAL-B6 — splitting one paired panel into two arms
# --------------------------------------------------------------------------- #
def test_b6_split_arms_maps_sn_columns_onto_the_theme_names():
    """`split_arms` must hand `holdout_compare_panels` two frames with the SAME column names.

    The gate scores both panels with one `cols` list, so the sector-neutral arm has to arrive
    with its values under the plain theme names. A silent failure here would compare the flat
    arm against ITSELF and report a difference of exactly zero — which reads like a clean null
    rather than like a broken harness, so it is pinned.
    """
    import pandas as pd

    from scripts.sector_neutral_rerun import split_arms

    df = pd.DataFrame({
        "date": ["2020-01-01"] * 3, "ticker": ["A", "B", "C"], "fwd_ret": [0.1, 0.2, 0.3],
        "sector": ["Tech", "Tech", "Utilities"],
        "value": [1.0, 2.0, 3.0], "sn_value": [-1.0, -2.0, -3.0],
        "quality": [4.0, 5.0, 6.0], "sn_quality": [-4.0, -5.0, -6.0],
    })
    flat, sn = split_arms(df)
    assert list(flat["value"]) == [1.0, 2.0, 3.0]
    assert list(sn["value"]) == [-1.0, -2.0, -3.0], "sn_ values must land under the theme name"
    assert list(sn["quality"]) == [-4.0, -5.0, -6.0]
    for frame, who in ((flat, "flat"), (sn, "sn")):
        assert not [c for c in frame.columns if str(c).startswith("sn_")], \
            f"{who} arm still carries sn_ columns, which would double-count the pair"
    assert len(flat) == len(sn) == 3, "splitting must not drop rows"
    assert list(flat["ticker"]) == list(sn["ticker"]), "the arms must keep one row order"


def test_b6_the_two_arms_are_not_accidentally_the_same_object():
    """Mutating one arm must not touch the other — `split_arms` copies rather than views."""
    import pandas as pd

    from scripts.sector_neutral_rerun import split_arms

    df = pd.DataFrame({
        "date": ["2020-01-01"] * 2, "ticker": ["A", "B"], "fwd_ret": [0.1, 0.2],
        "sector": ["Tech", "Utilities"],
        "value": [1.0, 2.0], "sn_value": [9.0, 8.0],
    })
    flat, sn = split_arms(df)
    sn.loc[0, "value"] = -99.0
    assert flat.loc[0, "value"] == 1.0, "the arms share memory — one write corrupted both"
    assert df.loc[0, "value"] == 1.0, "split_arms mutated the caller's panel"


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
    print(f"\n{passed}/{len(tests)} sector-neutral tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
