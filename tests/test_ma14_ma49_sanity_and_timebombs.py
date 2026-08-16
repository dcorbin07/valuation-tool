"""AUDIT MA14 + MA49 — the live sanity port, and the five latent time-bombs.

Run: python tests/test_ma14_ma49_sanity_and_timebombs.py

MA14: `sanity_check` guards the BACKTEST, whose input is a static licensed export that does not
drift. The LIVE path reads vendor feeds that do, and had coverage checks only — which answer
PRESENCE. `OOB2` is what the gap costs: Yahoo dropped one beta field, `wacc.py` substituted
1.10, and MRK went from "cannot value" to a 91 Strong Buy with nothing empty and nothing raised.

MA49: five defects that change no shipped number TODAY, which is exactly why they are worth
pinning — each is a trap set for a future run, and four of the five fail in the direction that
looks like a healthy result.

EVERY FIXTURE HERE IS WRITTEN TO FAIL AGAINST THE PRE-FIX TREE (M3's standard). Where one
cannot — because the pre-fix behaviour is a hard-coded literal that a test cannot un-write —
the test reconstructs the old behaviour inline and asserts on that, rather than pretending.
"""
from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# =========================================================================== MA14
def _frame(**over):
    d = {"book_to_price": [0.5, 0.6, 0.4, 0.7],
         "earnings_yield": [0.05, 0.06, 0.04, 0.03],
         "fcf_yield": [0.03] * 4, "ebit_ev": [0.08] * 4,
         "ev_sales": [2.0] * 4, "ev_ebitda": [9.0] * 4, "ps": [3.0] * 4,
         "is_foreign": [False, False, True, True]}
    d.update(over)
    return pd.DataFrame(d)


def test_ma14_the_bands_are_one_definition_shared_with_the_backtest():
    """The live check must judge against the SAME numbers the backtest does, by IDENTITY.

    Two copies of a threshold is the MA39 defect (`RESULT_BLOCKS` drifted, and a later change
    added `benchmarks` to one copy only, leaving seven payload blocks unwatched). Object
    identity — not equality — because equal-today is how a drift starts.
    """
    from valuation.edge import fundamental_panel as FP
    from valuation.edge import sanity_spec as SS
    assert FP.SANE_RANGES is SS.SANE_RANGES
    assert FP.SANE_RANGE_EXEMPT is SS.SANE_RANGE_EXEMPT
    assert FP.SUBGROUP_PEG_PCTILE == SS.SUBGROUP_PEG_PCTILE
    assert FP.SANE_VIOLATION_SHARE == SS.SANE_VIOLATION_SHARE


def test_ma14_exactly_one_literal_assignment_of_the_bands_exists_in_the_tree():
    """A re-export is only one definition while nobody re-types it. Counted over the package."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, "valuation")):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for f in filenames:
            if not f.endswith(".py"):
                continue
            p = os.path.join(dirpath, f)
            try:
                tree = ast.parse(open(p, encoding="utf-8", errors="ignore").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id == "SANE_RANGES":
                            hits.append(os.path.relpath(p, ROOT).replace(os.sep, "/"))
    assert hits == ["valuation/edge/sanity_spec.py"], (
        f"SANE_RANGES is assigned in {hits}; it must be defined once and re-exported")


def test_ma14_the_live_check_catches_the_p7_currency_signature():
    """The bug that motivated the whole sanity layer, on a LIVE-shaped frame.

    P7: `marketcap` is USD while the raw line items are in the reporting currency, so SK
    Telecom's `book_to_price` computed to 892 against a true 0.589. Both the range band AND the
    subgroup peg must fire — the peg is the one that needs no band at all and is why the check
    would have caught P7 on its FIRST run.
    """
    from valuation.screener.live_sanity import live_sanity
    bad = _frame()
    bad.loc[2, "book_to_price"] = 892.0
    bad.loc[3, "book_to_price"] = 750.0
    out = live_sanity(bad)
    kinds = {f["check"] for f in out["flags"] if f["factor"] == "book_to_price"}
    assert "range" in kinds, "the range band did not fire on a 892 book_to_price"
    assert "subgroup" in kinds, "foreign reporters pegging book_to_price did not fire"
    assert not out["vacuous"]


def test_ma14_a_healthy_live_frame_is_clean():
    """A detector that fires on good data is one people switch off."""
    from valuation.screener.live_sanity import live_sanity
    out = live_sanity(_frame())
    assert out["flags"] == [], f"clean frame produced flags: {out['flags']}"
    assert out["checked"] > 5, "too few checks ran for the clean result to mean anything"


def test_ma14_absence_is_reported_and_never_reads_as_healthy():
    """THE VACUITY CASE, and the reason this is not just a copy of `sanity_check`.

    The backtest version does `if col not in panel.columns: continue`, which is right for a
    panel built to a known schema. On a live frame a renamed or dropped column would then
    produce ZERO checks and an empty `flags` — a clean bill of health from a guard that looked
    at nothing. That is the exact shape of every silent-data-rot bug in this project's record.
    """
    from valuation.screener.live_sanity import live_sanity
    out = live_sanity(pd.DataFrame({"ticker": ["A", "B"]}))
    assert out["flags"] == []
    assert out["vacuous"] is True, "a frame with no factor columns must self-report as vacuous"
    assert out["checked"] == 0
    assert len(out["columns_absent"]) >= 7, "absent columns must be named, not skipped"
    assert "means nothing" in out["note"]


def test_ma14_the_live_check_is_reporting_only_and_changes_no_score():
    """It must never withhold a row or move a number — a gate that can kill a scan gets
    deleted the first time it misfires. Pinned at source: the module may not import the
    scoring or store layer, and `screen.py` may only ever read its result into `health`."""
    src = open(os.path.join(ROOT, "valuation", "screener", "live_sanity.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = getattr(node, "module", "") or ""
            names = [a.name for a in node.names]
            assert "store" not in mod and "store" not in names, "live_sanity must not touch the store"
            assert "composite" not in mod, "live_sanity must not reach the scoring path"
    scr = open(os.path.join(ROOT, "valuation", "screener", "screen.py"), encoding="utf-8").read()
    assert '"value_sanity": live_sanity(scored)' in scr, "the live check is not wired"
    # it is read into the health dict and nowhere else
    assert scr.count("live_sanity(") == 1, "live_sanity is called more than once — one is a report"


# =========================================================================== MA49(b)
def test_ma49b_a_nan_return_no_longer_renders_the_dsr_as_a_nan_verdict():
    """PRE-FIX BEHAVIOUR RECONSTRUCTED INLINE, because the fix is a one-line delegation.

    `sharpe` filtered `None` and not NaN while `_clean` (same module) dropped both. One NaN
    made `r.std()` NaN, so the `== 0` guard was False and the function returned NaN — which
    `deflated_sharpe_ratio` carried to a published `deflated_sharpe` of NaN. NaN compares False
    against every bar, so it fails a threshold silently instead of loudly.
    """
    from valuation.edge import statistics as ST
    r = [0.01, 0.02, float("nan"), 0.03, -0.01, 0.02, 0.01, 0.0]

    old_arr = np.asarray([x for x in r if x is not None], float)      # the pre-fix filter
    old = None if (len(old_arr) < 3 or old_arr.std(ddof=1) == 0) else float(
        old_arr.mean() / old_arr.std(ddof=1))
    assert old != old, "the pre-fix reconstruction should produce NaN, or this test is inert"

    new = ST.sharpe(r)
    assert new == new and new is not None, "sharpe still returns NaN on a NaN input"
    d = ST.deflated_sharpe_ratio(r, n_trials=224, var_trials=0.03)
    assert d["deflated_sharpe"] == d["deflated_sharpe"], "DSR is still a NaN verdict"
    assert d["n_unusable"] == 1, "the dropped observation must be counted, not silently removed"


def test_ma49b_the_nan_fix_is_inert_on_nan_free_input():
    """It may not move a published number. 500 random NaN-free series, bit-for-bit."""
    from valuation.edge import statistics as ST
    rng = np.random.default_rng(11)
    worst = 0.0
    for _ in range(500):
        r = list(rng.normal(0.01, 0.05, size=int(rng.integers(4, 90))))
        a = np.asarray([x for x in r if x is not None], float)
        old = float(a.mean() / a.std(ddof=1))
        worst = max(worst, abs(old - ST.sharpe(r)))
    assert worst == 0.0, f"the fix moved a NaN-free Sharpe by {worst:.3e}"


def test_ma49b_ndarray_trial_sharpes_no_longer_raises():
    """`trial_sharpes and len(...) > 1` evaluated an ndarray's truth value, which RAISES for
    any array longer than 1 — so the documented argument worked for a list and crashed for the
    ndarray every caller in this project actually holds."""
    from valuation.edge import statistics as ST
    r = list(np.random.default_rng(5).normal(0.02, 0.04, 40))

    try:                                                    # pre-fix expression, reconstructed
        bool(np.array([0.5, 0.6, 0.7]) and True)
        raised = False
    except ValueError:
        raised = True
    assert raised, "the pre-fix expression no longer raises — this test would be inert"

    got = ST.deflated_sharpe_ratio(r, n_trials=8, trial_sharpes=np.array([0.5, 0.6, 0.7]))
    want = ST.deflated_sharpe_ratio(r, n_trials=8, trial_sharpes=[0.5, 0.6, 0.7])
    assert got["deflated_sharpe"] == want["deflated_sharpe"], "list and ndarray disagree"


# =========================================================================== MA49(c)
def test_ma49c_the_scheme_count_is_derived_and_equals_eight():
    """`x7_reconcile` hard-coded `n_names = 9  # 8 schemes + current-default`, and the comment
    states its own error: `current-default` IS one of the eight. The n=8 curve point was
    therefore scored at sqrt(2 ln 9) rather than sqrt(2 ln 8)."""
    from valuation.edge import fundamental_panel as FP
    n = len(FP._weight_schemes(np.zeros(1), np.ones(1), np.eye(1), ["_"],
                               {"_": 1.0}, {"_": 1.0}))
    assert n == 8, f"_weight_schemes returns {n}; the reconciliation's count must follow it"
    # READ THROUGH THE AST, NOT BY GREP — and this test's first cut is why. It grepped for
    # "n_names = 9" and failed against the FIXED tree, because the explanatory comment above
    # the repair quotes the defect verbatim. A guard that cannot tell code from prose about
    # code is not measuring the tree: the identical defect the studies-boundary suite hit, in
    # a new file, one session later. The AST sees assignments and never comments.
    src = open(os.path.join(ROOT, "scripts", "x7_reconcile.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    literals = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "n_names":
                    if isinstance(node.value, ast.Constant):
                        literals.append(node.value.value)
    assert not literals, f"n_names is assigned a literal {literals}; it must be DERIVED"
    assert "_weight_schemes" in src, "n_names must be derived from the scheme list itself"


# =========================================================================== MA49(d)
def test_ma49d_the_b6_cut_is_conditional_on_the_corrected_panel_flag():
    """On the corrected panel B6 already removed the first 37 dates, so the cut lands on 37
    HEALTHY rebalances and ships them under a name saying they were contaminated. The q-model
    block reasons this out and branches; the subperiod block computed it unconditionally."""
    src = open(os.path.join(ROOT, "scripts", "factor_alpha.py"), encoding="utf-8").read()
    # The `subs = { ... }` literal itself, delimited by its own braces rather than by a later
    # marker — the first cut of this test sliced on the block NAME and picked up the wrong
    # span entirely, so it failed against the fixed tree.
    i = src.index("subs = {")
    lit = src[i:src.index("}", i) + 1]
    assert "ex_b6_first_" not in lit, (
        "the B6 cut is still built unconditionally inside the `subs` literal")
    assert "if not args.corrected_panel:" in src, "the cut is no longer guarded by the flag"
    # and it must still be REACHABLE on the void-panel arm, or the cut was simply deleted
    assert "subs[f\"ex_b6_first_{B6_CONTAMINATED}\"]" in src, (
        "the B6 cut was removed rather than made conditional; the void-panel arm still needs it")


# =========================================================================== MA49(e)
def test_ma49e_a_starved_cap_tier_contributes_nothing_rather_than_everything():
    """It returned `np.ones(...)` — the FULL universe, wider even than the finite-cap names —
    when a tier could not be formed, so a date labelled `megacap` silently contributed every
    name. Mixing two universes under one label is B12's defect in a different column, and it
    fails in the direction that looks like more data."""
    from valuation.studies import param_search as PS
    starved = np.full(50, np.nan)
    starved[:5] = [1e9, 2e9, 3e9, 4e9, 5e9]                 # 5 finite, below the 30 floor
    m = PS._cap_mask(starved, "top10")
    assert m.sum() == 0, f"a starved tier still contributes {int(m.sum())} names"
    assert len(m) == 50 and m.dtype == bool

    healthy = np.linspace(1e8, 1e12, 200)
    h = PS._cap_mask(healthy, "top10")
    assert 0 < h.sum() < 200, "a healthy tier must still select a proper subset"
    assert PS._cap_mask(starved, "all").all(), "'all' must remain the full universe"


def test_ma49e_the_consumer_drops_a_starved_date_instead_of_crashing():
    """A fix that trades a silent wrong answer for a crash is not a fix. `rank_dates` already
    skips a cross-section under 25 names, so an empty mask drops the date cleanly."""
    src = open(os.path.join(ROOT, "valuation", "studies", "param_search.py"),
               encoding="utf-8").read()
    assert "if len(ids) < 25:" in src and "continue" in src, (
        "rank_dates no longer guards a thin cross-section; an empty cap mask would now "
        "reach the ranking arithmetic")


# =========================================================================== MA49(a)
def test_ma49a_the_frozen_coverage_bar_now_reports_its_own_staleness():
    """The bar is PRE-REGISTERED at 2025-12-31 and is deliberately NOT moved — a registered bar
    that follows the clock is not the bar that was registered. But a frozen bar only ever gets
    EASIER, so the repair is to make staleness a reported number instead."""
    src = open(os.path.join(ROOT, "scripts", "fetch_factors.py"), encoding="utf-8").read()
    assert '"covers_through_2025"' in src, "the pre-registered check was renamed or removed"
    assert "stale_days" in src and "bar_is_frozen" in src, "staleness is not disclosed"
    assert 'pd.Timestamp("2025-12-31" if daily else "2025-12-01")' in src, (
        "the pre-registered bar itself was changed; MA49(a) asks for disclosure, not a new bar")


def test_ma49a_dropped_factor_windows_are_counted_rather_than_vanishing():
    """`factor_windows` skipped an empty window with a bare `continue`, so a factor file that
    ends before the panel does silently shortens every regression in the file."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    src = open(os.path.join(ROOT, "scripts", "factor_alpha.py"), encoding="utf-8").read()
    assert "windows_dropped_no_factor_days" in src, "dropped windows are still uncounted"
    assert "def windows_report" in src, "no reader for the drop count"
    # the report must distinguish 'covered' from 'dropped', not just return a number
    blk = src.split("def windows_report", 1)[1][:1400]
    for k in ("windows_requested", "windows_scored", "n_dropped"):
        assert k in blk, f"windows_report does not ship {k}"


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
    print(f"\n{passed}/{len(tests)} MA14+MA49 tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
