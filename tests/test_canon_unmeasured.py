# -*- coding: utf-8 -*-
"""`CANON-UNMEASURED` — the five parameters this item added, and the generator it repaired.

Every one of the five defaults to the LANDED behaviour, so the point of most of these tests is
that the default did not move. The ones that matter are the two that prove a NEW path is not
inert and the one that proves the generator now REFUSES instead of silently shrinking.

Run:  python tests/test_canon_unmeasured.py
"""
from __future__ import annotations

import ast
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
if REPO not in sys.path:
    sys.path.insert(0, REPO)

import state_isolation  # noqa: F401,E402  — must precede any `valuation` import

import numpy as np                                                          # noqa: E402

from valuation.edge import fundamental_panel as FP                          # noqa: E402

PASS, FAIL = [], []


def check(name, fn):
    try:
        fn()
    except Exception as e:                                                  # noqa: BLE001
        FAIL.append((name, repr(e)))
        print("  FAIL  %s\n        %r" % (name, e))
    else:
        PASS.append(name)
        print("  PASS  %s" % name)


# ---------------------------------------------------------------------------------------------
# `_pbo(fixed=)` — one implementation of the rank arithmetic, two selection rules
# ---------------------------------------------------------------------------------------------
#: four candidates over three paths. Deliberately built so the IN-SAMPLE argmax and the fixed
#: scheme are DIFFERENT candidates with DIFFERENT out-of-sample ranks, or neither direction
#: below would be evidence of anything.
NAMES = ["a", "b", "c", "current-default"]
IS_MAT = [[9.0, 1.0, 2.0, 3.0],
          [8.0, 1.0, 2.0, 3.0],
          [7.0, 1.0, 2.0, 3.0]]
#: `a` wins in sample every path and lands TOP out of sample every path (rank 1.0 -> not an
#: overfit instance); `current-default` is WORST out of sample every path (rank 0.25 -> at or
#: below the median on all three).
OOS_MAT = [[4.0, 3.0, 2.0, 1.0],
           [4.0, 3.0, 2.0, 1.0],
           [4.0, 3.0, 2.0, 1.0]]


def test_pbo_default_is_the_argmax_rule_unchanged():
    assert FP._pbo(IS_MAT, OOS_MAT, NAMES) == 0.0


def test_pbo_default_equals_passing_fixed_none_explicitly():
    assert FP._pbo(IS_MAT, OOS_MAT, NAMES) == FP._pbo(IS_MAT, OOS_MAT, NAMES, fixed=None)


def test_pbo_fixed_reads_the_named_scheme_and_NOT_the_argmax():
    """The one test that proves the new path is not inert: same matrices, opposite answer."""
    argmax = FP._pbo(IS_MAT, OOS_MAT, NAMES)
    fixed = FP._pbo(IS_MAT, OOS_MAT, NAMES, fixed="current-default")
    assert argmax == 0.0, argmax
    assert fixed == 1.0, fixed
    assert argmax != fixed


def test_pbo_fixed_is_a_rank_statistic_monotone_in_oos_standing():
    """`a` best, `current-default` worst, so the fixed reading must be ordered the same way.

    This is the property that forbids publishing a `fixed=` value as a probability of
    overfitting: it is each candidate's out-of-sample rank and nothing else."""
    vals = [FP._pbo(IS_MAT, OOS_MAT, NAMES, fixed=n) for n in NAMES]
    assert vals[0] == 0.0, vals
    assert vals[-1] == 1.0, vals
    assert vals == sorted(vals), vals


def test_pbo_fixed_on_an_unknown_scheme_returns_None_rather_than_guessing():
    """A silent fall back to the argmax would answer a DIFFERENT question under the caller's
    name, which is this record's wrong-object family."""
    assert FP._pbo(IS_MAT, OOS_MAT, NAMES, fixed="no-such-scheme") is None


def test_pbo_fixed_still_skips_a_path_whose_oos_value_is_missing():
    oos = [list(OOS_MAT[0]), list(OOS_MAT[1]), list(OOS_MAT[2])]
    oos[0][3] = float("nan")
    # two usable paths remain and the fixed scheme is worst on both
    assert FP._pbo(IS_MAT, oos, NAMES, fixed="current-default") == 1.0


# ---------------------------------------------------------------------------------------------
# `cpcv_validate(deployed_readings=)` — OFF by default, and adds NO KEY when off
# ---------------------------------------------------------------------------------------------
def test_cpcv_validate_defaults_deployed_readings_off():
    import inspect
    sig = inspect.signature(FP.cpcv_validate)
    assert "deployed_readings" in sig.parameters
    assert sig.parameters["deployed_readings"].default is False


def test_cpcv_validate_adds_no_key_when_the_flag_is_off():
    """`payload_schema.BLOCK_SPEC` guards the `cpcv` block FIELD BY FIELD: a computed field that
    reaches the source and not the projection FAILS the run (`M6`). So the new reading must be
    absent from the dict entirely when off, not present-and-None.

    Read off the SYNTAX TREE rather than by running a 70-second CPCV: the guarantee is that the
    key is emitted inside a conditional on the flag."""
    src = io.open(os.path.join(REPO, "valuation", "edge", "fundamental_panel.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "cpcv_validate")
    # the key appears exactly once, and inside a `**({...} if _dep is not None else {})`
    lits = [n for n in ast.walk(fn)
            if isinstance(n, ast.Constant) and n.value == "deployed_readings"]
    assert len(lits) == 1, len(lits)
    ifexps = [n for n in ast.walk(fn) if isinstance(n, ast.IfExp)
              and any(isinstance(c, ast.Constant) and c.value == "deployed_readings"
                      for c in ast.walk(n))]
    assert ifexps, "the key is not emitted conditionally"


# ---------------------------------------------------------------------------------------------
# `_assert_split(balance_tol=)` — 1 by default, DERIVED for a hash partition
# ---------------------------------------------------------------------------------------------
def test_assert_split_default_tolerance_is_one_and_still_bites():
    from scripts.r4_x1_accounting_universe import _assert_split
    uni = ["t%d" % i for i in range(10)]
    a, b = uni[:7], uni[7:]
    try:
        _assert_split(a, b, uni)
    except AssertionError as e:
        assert "differ by 4" in str(e), str(e)
    else:
        raise AssertionError("an imbalance of 4 must fail the DEFAULT tolerance")


def test_assert_split_accepts_a_balanced_random_split_at_the_default():
    from scripts.r4_x1_accounting_universe import _assert_split
    uni = ["t%d" % i for i in range(10)]
    _assert_split(uni[:5], uni[5:], uni)


def test_assert_split_with_a_derived_tolerance_accepts_the_real_hash_imbalance():
    """4798 / 4847 on 9,645 names is z = 0.50 under a fair hash. The DEFAULT bar of 1 fired on
    it; the derived 4-sigma bar must not."""
    from scripts.r4_x1_accounting_universe import _assert_split
    n = 9645
    uni = ["t%d" % i for i in range(n)]
    a, b = uni[:4798], uni[4798:]
    assert len(b) == 4847
    tol = int(round(2.0 * n ** 0.5))
    assert tol == 196, tol
    try:
        _assert_split(a, b, uni)
    except AssertionError:
        pass
    else:
        raise AssertionError("the default must still reject an imbalance of 49")
    _assert_split(a, b, uni, balance_tol=tol)


def test_assert_split_still_requires_disjoint_and_exhaustive_at_any_tolerance():
    """The tolerance must relax the BALANCE leg only. A loose tolerance that also let an
    overlapping or non-exhaustive split through would be a silenced check."""
    from scripts.r4_x1_accounting_universe import _assert_split
    uni = ["t%d" % i for i in range(10)]
    for a, b in ((uni[:6], uni[4:]), (uni[:4], uni[5:])):
        try:
            _assert_split(a, b, uni, balance_tol=10_000)
        except AssertionError:
            continue
        raise AssertionError("an overlapping / non-exhaustive split passed at a loose tolerance")


# ---------------------------------------------------------------------------------------------
# `strategy_series(legacy_composite=)` — the LANDED convention by default
# ---------------------------------------------------------------------------------------------
def _toy_panel():
    import pandas as pd
    rng = np.random.default_rng(11)
    rows = []
    for d in ("2020-01-01", "2020-04-01", "2020-07-01"):
        for i in range(60):
            rows.append({
                "date": d, "ticker": "T%02d" % i,
                "value": rng.normal(), "quality": rng.normal(),
                # a MISSING theme on some rows is the whole difference between the two
                # composites: the legacy one reads it as exactly average, the shipped one
                # renormalises by the present-weight mass.
                "momentum": (np.nan if i % 3 == 0 else rng.normal()),
                "fwd_ret": rng.normal() * 0.05,
                "market_cap": 1e9 * (i + 1), "bench_ret": 0.01,
            })
    return pd.DataFrame(rows)


def test_strategy_series_defaults_to_the_legacy_composite():
    import inspect
    from scripts.etf_benchmark import strategy_series
    assert inspect.signature(strategy_series).parameters[
        "legacy_composite"].default is True


def test_strategy_series_two_composites_are_NOT_the_same_book():
    """Non-vacuity. If the two branches agreed on a frame with missing themes, the parameter
    would be decoration and the primary/sensitivity split in R1's reading would mean nothing."""
    from scripts.etf_benchmark import strategy_series
    p = _toy_panel()
    w = {"value": 0.125, "quality": 0.125, "momentum": 0.125}
    leg = strategy_series(p, w, legacy_composite=True)
    shp = strategy_series(p, w, legacy_composite=False)
    assert len(leg) == len(shp) == 3
    assert max(abs(leg["top"].values - shp["top"].values)) > 0.0


# ---------------------------------------------------------------------------------------------
# `v6b --expect-record` — the gate's LITERALS move, its RULE does not
# ---------------------------------------------------------------------------------------------
def test_v6b_expect_record_defaults_to_the_published_literals():
    src = io.open(os.path.join(REPO, "scripts", "v6b_dip_survival.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    adds = [n for n in ast.walk(tree)
            if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument"
            and n.args and isinstance(n.args[0], ast.Constant)
            and n.args[0].value == "--expect-record"]
    assert len(adds) == 1, len(adds)
    kw = {k.arg: k.value for k in adds[0].keywords}
    assert isinstance(kw["default"], ast.Constant) and kw["default"].value is None


def test_v6b_c1_still_aborts_when_the_expectation_is_not_met():
    """The RULE is kept. A re-pointable gate that stopped gating would be a silenced check."""
    src = io.open(os.path.join(REPO, "scripts", "v6b_dip_survival.py"),
                  encoding="utf-8").read()
    assert "C1 FAILED" in src
    i = src.index("ok1 = all(")
    assert "return 2" in src[i:i + 900], "C1 no longer aborts"


# ---------------------------------------------------------------------------------------------
# `canon_figure_table` — the generator must REFUSE, not shrink
# ---------------------------------------------------------------------------------------------
GEN = os.path.join(REPO, "scripts", "canon_figure_table.py")


def test_the_generator_carries_no_absolute_path_literal():
    """All three of its original paths were dead and the failure was SILENT ROW LOSS. A literal
    absolute path is how that happens, so there must not be one."""
    src = io.open(GEN, encoding="utf-8").read()
    tree = ast.parse(src)
    bad = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            v = n.value
            if v[1:3] == ":\\" or v[1:3] == ":/" or v.startswith("/Users") or v.startswith("/home"):
                bad.append(v)
    assert not bad, bad


def test_the_generator_refuses_rather_than_dropping_the_published_column():
    src = io.open(GEN, encoding="utf-8").read()
    assert "REFUSING" in src
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "load_published_artifact")
    raises = [n for n in ast.walk(fn)
              if isinstance(n, ast.Raise) or (isinstance(n, ast.Call)
                                              and getattr(n.func, "id", "") == "SystemExit")]
    assert raises, "load_published_artifact can still return quietly"
    # and the corrected column too
    assert "no tracked BACKTEST_RESULTS.json" in src


def test_the_successor_rows_never_DROP_an_absent_artifact():
    """A missing artifact must become an UNMEASURED row WITH ITS REASON. Dropping it is the
    generator defect one level up."""
    src = io.open(os.path.join(REPO, "scripts", "canon_unmeasured.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, ast.FunctionDef) and n.name == "table_rows")
    # every `if not d` branch must append rather than `continue`/`pass`
    conts = [n for n in ast.walk(fn) if isinstance(n, (ast.Continue, ast.Pass))]
    assert not conts, "table_rows has a skip branch; an absent artifact must become a row"
    assert src.count('"UNMEASURED"') >= 4


def test_the_successor_rows_are_wired_into_the_generator():
    src = io.open(GEN, encoding="utf-8").read()
    assert "table_rows" in src, "the successor rows are not unioned in"
    assert "rows += " in src



def test_every_superseded_pointer_resolves_to_a_real_row():
    """A pointer that can rot is the defect one level up. The generator's SUPERSEDED_BY pairs
    are explicit strings, so each target must actually name a row the generator emits."""
    import json
    import scripts.canon_figure_table as G  # running it regenerates; that is the point
    doc = json.load(io.open(G.OUT_JSON, encoding="utf-8"))
    figs = {str(r.get("figure")) for r in doc["rows"]}
    bad = []
    for grp, fig, targets in G.SUPERSEDED_BY:
        src = [r for r in doc["rows"]
               if str(r.get("figure")) == fig and r.get("group") == grp]
        if not src:
            # A SOURCE that does not exist is always a rotted pointer -- the row it names is
            # gone, so the pair is stale and must be removed or corrected.
            bad.append(("source row does not exist", grp, fig))
            continue
        if any(t in figs for t in targets):
            continue
        # A TARGET that has not landed is NOT a rotted pointer: an item whose successor sweep
        # is still running, or which turns out to be unmeasurable, is an honest state. What
        # must hold is that the row SAYS SO rather than claiming an answer it cannot point at.
        note = (src[0].get("note") or "")
        if "no successor row has landed yet" not in note:
            bad.append(("target absent and the row does not say so", grp, fig))
    assert not bad, bad


def test_the_supersession_reaches_the_MARKDOWN_not_only_the_json():
    """The markdown is the file handed to the app fixer. A bare UNMEASURED on a figure this
    table answers three groups further down is the misreading the annotation removes."""
    md = io.open(os.path.join(REPO, "CANONICAL_FIGURE_TABLE.md"), encoding="utf-8").read()
    assert "UNMEASURED -> SUPERSEDED" in md
    assert "ANSWERED BELOW at:" in md


def main():
    print("CANON-UNMEASURED — the added parameters and the repaired generator\n")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d/%d canon-unmeasured tests passed" % (len(PASS), len(PASS) + len(FAIL)))
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
