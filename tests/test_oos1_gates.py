"""OOS1 -- pins for the Compustat provider and the two preparation gates.

The two defects this file exists for are the two that **would not raise**:

  * the MILLIONS -> UNITS conversion. Omit it and every RATIO stays correct while every LEVEL is
    1e6 out, so only `size` and the EV columns move and nothing anywhere errors.
  * the YEAR-TO-DATE conversion. Omit it and Q4 is roughly 4x its true flow, which corrupts
    `fcf`, `fcf_margin`, `accruals` and `neg_issuance` and still produces a clean, plausible
    panel -- `MA31`'s failure mode.

Plus the one property the charter makes binding: **nothing here reads the 1972-1998 holdout.**
"""
import ast
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)

import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.edge import compustat_provider as CP  # noqa: E402

PASS, FAIL = [], []


def ck(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (("  -- " + detail) if detail else ""))


# ----------------------------------------------------------------- the YTD trap
def _ytd_fixture():
    """Two fiscal years for one gvkey, so a conversion that crosses the boundary is visible."""
    return pd.DataFrame({
        "gvkey": ["001"] * 8,
        "fyearq": [2000] * 4 + [2001] * 4,
        "fqtr": [1, 2, 3, 4, 1, 2, 3, 4],
        # YTD cash flow: 10, 25, 45, 70 then it RESETS to 5, 11, 18, 26.
        "oancfy": [10.0, 25.0, 45.0, 70.0, 5.0, 11.0, 18.0, 26.0],
        "capxy": [1.0, 3.0, 6.0, 10.0, 2.0, 5.0, 9.0, 14.0],
        "dvy": [0.0] * 8, "sstky": [0.0] * 8, "prstkcy": [0.0] * 8,
    })


def test_ytd():
    out = CP._ytd_to_quarterly(_ytd_fixture()).sort_values(["fyearq", "fqtr"])
    got = [round(float(x), 6) for x in out["oancfy_q"]]
    want = [10.0, 15.0, 20.0, 25.0, 5.0, 6.0, 7.0, 8.0]
    ck("YTD -> quarterly is YTD_t - YTD_{t-1} within a fiscal year",
       got == want, "got %s want %s" % (got, want))
    # THE DECISIVE CELL: 2001 Q1. A conversion that differenced against the PRIOR fiscal year's
    # Q4 would read 5 - 70 = -65, a large NEGATIVE operating cash flow out of nothing.
    q1_2001 = float(out[(out["fyearq"] == 2001) & (out["fqtr"] == 1)]["oancfy_q"].iloc[0])
    ck("the fiscal-year boundary does not leak (2001 Q1 is 5.0, not -65.0)",
       abs(q1_2001 - 5.0) < 1e-9, "got %.4f" % q1_2001)
    ck("the quarterly flows sum back to the year's YTD total",
       abs(sum(got[:4]) - 70.0) < 1e-9 and abs(sum(got[4:]) - 26.0) < 1e-9)
    # NON-VACUITY: the RAW column is NOT already the quarterly flow, so the test has something
    # to catch. Without this, a no-op conversion would pass whenever the fixture was degenerate.
    raw = [round(float(x), 6) for x in out["oancfy"]]
    ck("the fixture is non-vacuous -- the raw YTD column differs from the quarterly flow",
       raw != want)


# --------------------------------------------------------------- the units trap
def test_units():
    prov = CP.CompustatCrspProvider.__new__(CP.CompustatCrspProvider)
    row = {"datekey": "2001-02-14", "datadate": "2000-12-31", "datekey_source": "rdq",
           "atq": 1234.5, "revtq": 900.0, "cogsq": 400.0, "oiadpq": 200.0,
           "ceqq": 500.0, "niq": 50.0, "ibcomq": 48.0, "cshoq": 10.0,
           "dlttq": 100.0, "dlcq": 20.0, "oancfy_q": 60.0, "capxy_q": 25.0}
    r = prov._sf1_row(row)
    ck("assets is Compustat millions x 1e6", abs(r["assets"] - 1234.5e6) < 1.0,
       "got %r" % r["assets"])
    ck("revenue is millions x 1e6", abs(r["revenue"] - 900e6) < 1.0)
    ck("debt is (dlttq + dlcq) x 1e6", abs(r["debt"] - 120e6) < 1.0, "got %r" % r["debt"])
    ck("gp falls back to revenue - cor when gpq is absent",
       abs(r["gp"] - 500e6) < 1.0, "got %r" % r["gp"])
    ck("fcf is (ncfo - capx) x 1e6", abs(r["fcf"] - 35e6) < 1.0, "got %r" % r["fcf"])
    # RATIOS must be dimensionless -- the half of the units trap that is invisible in a ratio.
    ck("grossmargin is a ratio, not a level", abs(r["grossmargin"] - (500.0 / 900.0)) < 1e-9,
       "got %r" % r["grossmargin"])
    ck("ebitmargin is a ratio", abs(r["ebitmargin"] - (200.0 / 900.0)) < 1e-9)
    ck("sharesbas is millions x 1e6", abs(r["sharesbas"] - 10e6) < 1.0)
    ck("fxusd is exactly 1.0 under the USD-only filter", r["fxusd"] == 1.0)
    # The four DERIVED signals must be ABSENT, or the holdout arm and the training arm would use
    # two different definitions of the same signal -- a `B7` split inside the comparison meant
    # to detect one.
    for k in ("roe", "roic", "assetturnover", "beta"):
        ck("%s is left ABSENT for the builder to derive" % k, r.get(k) is None)


def test_num_treats_nan_as_absent():
    ck("_num(nan) is None -- the builder's `_f` convention", CP._num(float("nan")) is None)
    ck("_num(None) is None", CP._num(None) is None)
    ck("_num('x') is None", CP._num("x") is None)
    ck("_num(0.0) is 0.0 and NOT None", CP._num(0.0) == 0.0)
    r = CP.CompustatCrspProvider.__new__(CP.CompustatCrspProvider)._sf1_row(
        {"datekey": "d", "datadate": "d", "datekey_source": "rdq", "atq": float("nan")})
    ck("a NaN Compustat cell maps to None, not to NaN x 1e6", r["assets"] is None)


# ------------------------------------------------------- the five-theme freeze
def test_frozen_model():
    import scripts.oos1_gates as G
    ck("the frozen model is exactly five themes",
       tuple(G.FIVE) == ("value", "quality", "momentum", "capital_discipline", "size"),
       repr(G.FIVE))
    ck("each weight is 0.2 and they sum to 1.0",
       all(v == 0.2 for v in G.FIVE_W.values()) and abs(sum(G.FIVE_W.values()) - 1.0) < 1e-12)
    for dead in ("insider", "institutional", "low_risk", "sentiment", "growth"):
        ck("%s carries no weight in the holdout model" % dead, dead not in G.FIVE_W)
    ck("Gate B's bar is 0.90", G.GATE_B_BAR == 0.90)
    ck("the holdout era is 1972-1998 (r1 took 1999-2008)", tuple(G.HOLDOUT) == (1972, 1998))


def test_dead_themes_are_empty_not_fabricated():
    p = CP.CompustatCrspProvider.__new__(CP.CompustatCrspProvider)
    for m in ("insider_history", "institutional_history", "grades_history"):
        ck("%s returns an EMPTY list, not a neutral value" % m, getattr(p, m)("X") == [])
    ck("delisted_map is empty rather than absent", p.delisted_map() == {})


# -------------------------------------------- the holdout is not read by a gate
def test_no_gate_reads_the_holdout():
    src = open(os.path.join(REPO, "scripts", "oos1_gates.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    ck("gate_b exists", "gate_b" in fn)
    # Gate B's floor must sit ABOVE the holdout ceiling, so no holdout year can be loaded by it,
    # and BELOW the 2009 grid start by enough to give the momentum columns their 252 trading
    # days -- otherwise momentum is computed on a truncated window and the Spearman falls for a
    # reason that is NOT vendor translation.
    import scripts.oos1_gates as G
    ck("Gate B's burn-in floor is strictly above the holdout ceiling",
       G.GATE_B_BURNIN_YEAR > G.HOLDOUT[1],
       "floor %d vs holdout ceiling %d" % (G.GATE_B_BURNIN_YEAR, G.HOLDOUT[1]))
    ck("Gate B's burn-in floor leaves at least a year before the 2009 grid start",
       G.GATE_B_BURNIN_YEAR <= 2008, "floor %d" % G.GATE_B_BURNIN_YEAR)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "gate_b"]
    ck("gate_b is invoked with the declared burn-in constant, not a literal",
       any(any(isinstance(a, ast.Name) and a.id == "GATE_B_BURNIN_YEAR" for a in c.args)
           for c in calls), "calls: %d" % len(calls))
    # And no gate computes a forward return at all: the holdout cannot be scored by accident.
    bodies = "\n".join(ast.dump(fn[k]) for k in fn if k.startswith("gate_"))
    for banned in ("fwd_ret", "alpha", "long_short", "top_decile"):
        ck("no gate body references %r" % banned, banned not in bodies)


def test_french_units_are_checked_not_converted():
    """The defect that actually happened: a DOUBLE /100 on an already-decimal file.

    Uncorrected it made the 1995 market return 0.03%/yr against a true ~37%, and Gate A read
    correlation 0.999998 beside a 2.86pp mean absolute difference -- which would have been
    reported as a level failure of a CRSP build that is correct.
    """
    import scripts.oos1_gates as G
    ck("there is a decimal ceiling constant", hasattr(G, "DECIMAL_CEILING"))
    ck("the ceiling is 0.05", G.DECIMAL_CEILING == 0.05)
    src = open(os.path.join(REPO, "scripts", "oos1_gates.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    fn = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_french"]
    ck("_french exists", len(fn) == 1)
    dump = ast.dump(fn[0])
    # The loader must REFUSE, not convert. A /100 anywhere inside it is the defect returning.
    div_by_100 = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)
                     and isinstance(n.right, ast.Constant) and n.right.value == 100.0
                     for n in ast.walk(fn[0]))
    ck("_french does NOT divide by 100 -- it refuses instead", not div_by_100)
    ck("_french raises on out-of-range units", "SystemExit" in dump or "raise" in dump)

    # NON-VACUITY, both directions: the real decimal file must be ACCEPTED, and a
    # percent-scaled copy of it must be REFUSED. A guard that only ever passes is not a guard.
    import tempfile
    import shutil
    root = None
    for cand in ("../../../data", "../../data", "data"):
        p = os.path.join(REPO, cand, "factors", "parsed", "ff5_monthly.csv")
        if os.path.isfile(p):
            root = os.path.join(REPO, cand)
            break
    if root is None:
        ck("SKIPPED LOUDLY: the parsed factor file is absent (data/ is empty in a worktree)",
           True)
        return
    try:
        G._french(root)
        ck("the real decimal factor file is ACCEPTED", True)
    except SystemExit as exc:
        ck("the real decimal factor file is ACCEPTED", False, str(exc)[:120])
    tmp = tempfile.mkdtemp()
    try:
        dst = os.path.join(tmp, "factors", "parsed")
        os.makedirs(dst)
        f = pd.read_csv(os.path.join(root, "factors", "parsed", "ff5_monthly.csv"))
        for c in ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"):
            if c in f.columns:
                f[c] = f[c].astype(float) * 100.0
        f.to_csv(os.path.join(dst, "ff5_monthly.csv"), index=False)
        refused = False
        try:
            G._french(tmp)
        except SystemExit:
            refused = True
        ck("a PERCENT-scaled factor file is REFUSED", refused)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_benchmark_is_labelled_not_load_bearing():
    src = open(os.path.join(REPO, "valuation", "edge", "compustat_provider.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    mi = [n for n in ast.walk(tree)
          if isinstance(n, ast.FunctionDef) and n.name == "market_index"]
    ck("market_index exists", len(mi) == 1)
    doc = ast.get_docstring(mi[0]) or ""
    ck("market_index names crsp_a_stock.dsi as the real benchmark source still to pull",
       "dsi" in doc and "NOT banked" in doc)
    ck("market_index states that no gate statistic reads it",
       "no gate statistic reads it" in doc)


def test_price_history_uses_absolute_price_and_adjusts():
    src = open(os.path.join(REPO, "valuation", "edge", "compustat_provider.py"),
               encoding="utf-8").read()
    tree = ast.parse(src)
    # `prc` must be read through .abs(): CRSP marks a bid/ask average with a NEGATIVE price, and
    # taking the sign at face value flips every ratio built on it. Checked on the AST so a
    # comment mentioning `abs` cannot satisfy it (the substring-ban family, `MB1`).
    found = False
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) \
                and n.func.attr == "abs":
            found = True
    ck("the daily price is taken as |prc|", found)
    ck("the price series is divided by cfacpr (split-adjusted, V6's C5)", "cfacpr" in src)


def test_universe_subset_is_by_size_not_alphabetical():
    src = open(os.path.join(REPO, "valuation", "edge", "compustat_provider.py"),
               encoding="utf-8").read()
    ck("a capped universe is the LARGEST by market cap, citing B12",
       "sort_values(ascending=False)" in src and "B12" in src)


if __name__ == "__main__":
    for t in (test_ytd, test_units, test_num_treats_nan_as_absent, test_frozen_model,
              test_dead_themes_are_empty_not_fabricated, test_no_gate_reads_the_holdout,
              test_french_units_are_checked_not_converted,
              test_benchmark_is_labelled_not_load_bearing,
              test_price_history_uses_absolute_price_and_adjusts,
              test_universe_subset_is_by_size_not_alphabetical):
        print(t.__name__)
        t()
    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        for f in FAIL:
            print("  FAILED: " + f)
        sys.exit(1)
