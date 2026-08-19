"""MB1, pinned.  [the arms charge 2 options trials; these tests charge none]

What has to hold:

  * THE MENU IS THE ENGINE'S OWN. `build_menu` must be `pick_contract`'s prefilter verbatim, and
    the strongest form of that is behavioural: on a synthetic chain the menu must CONTAIN the
    shipped pick and the menu's own argmin must BE it. Pinned here on a fixture so it runs with
    no freeze mounted, and gated on the real data by C1.
  * the moneyness FALLBACK is kept. Removing it is a void condition of the register, and a
    "tidier" menu would silently be a different menu from the engine's.
  * the two passes may not run together and `--arms` REFUSES without a passing controls artifact.
  * the KILL CONDITION fires on the WEAKER half. `any(|gap| < 1.0)`, never `all` - softening it
    to "both halves" is a void condition and would invert the item's meaning.
  * a zero-leg arm RAISES rather than writing a plausible coverage null (MA31's failure mode).
  * resolution is LAZY (CI has no D: drive) and the mutable store is never opened.
  * paths are compared separator-insensitively (MB42).

Offline: the fixtures are synthetic frames, so every test here runs on Linux and Windows alike.
"""
from __future__ import annotations

import ast
import datetime as dt
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import pandas as pd  # noqa: E402

from valuation.edge import options_backtest as OB  # noqa: E402

import scripts.mb1_alternatives_menu as M  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb1_alternatives_menu.py")
REGISTER = os.path.join(REPO, "PREREG_mb1_alternatives_menu.md")


def _src():
    with open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def _chain(asof, spot=100.0, n=14):
    """A synthetic call chain: two expirations, a strike ladder, all quoted and fillable."""
    rows = []
    for dte in (30, 60):                       # 30 is OUTSIDE the 45-75 band, 60 inside
        exp = asof + dt.timedelta(days=dte)
        for i in range(n):
            k = 80.0 + 5.0 * i                 # 80 .. 145
            rows.append({"expiration": exp, "strike": k, "right": "C", "date": asof,
                         "bid": max(0.35, (spot - k) * 0.5 + 4.0),
                         "ask": max(0.45, (spot - k) * 0.5 + 4.3),
                         "volume": 500, "open_interest": 2000})
    return pd.DataFrame(rows)


# ------------------------------------------------------- the menu IS the engine's menu
def test_the_menu_contains_the_shipped_pick_and_its_argmin_is_that_pick():
    asof = dt.date(2019, 3, 4)
    ch = _chain(asof)
    menu = M.build_menu(ch, 100.0, asof)
    assert menu, "menu is empty on a fully quoted synthetic chain"
    pick = OB.pick_contract(ch, 100.0, asof, right="C")
    assert pick is not None
    key = lambda r: (float(r["strike"]), str(r["expiration"])[:10])   # noqa: E731
    assert key(pick) in {key(x) for x in menu}, "the shipped pick is not in the menu"
    assert key(M.menu_argmin(menu)) == key(pick), "the menu's argmin is not the shipped pick"


def test_the_menu_applies_the_dte_band():
    asof = dt.date(2019, 3, 4)
    menu = M.build_menu(_chain(asof), 100.0, asof)
    for r in menu:
        d = (pd.Timestamp(r["expiration"]).date() - asof).days
        assert OB.DTE_RANGE[0] <= d <= OB.DTE_RANGE[1], d


def test_the_menu_applies_the_moneyness_band():
    asof = dt.date(2019, 3, 4)
    menu = M.build_menu(_chain(asof), 100.0, asof)
    for r in menu:
        m = float(r["strike"]) / 100.0
        assert 0.90 <= m <= 1.20, m


def test_the_moneyness_fallback_is_kept_verbatim():
    """`if len(near) == 0: near = d`. Removing it is a void condition of the register.

    With a spot far from every strike the band is empty, and the SHIPPED behaviour is to fall
    back to the DTE-band set rather than return nothing.
    """
    asof = dt.date(2019, 3, 4)
    exp = asof + dt.timedelta(days=60)
    # Strikes JUST outside the 1.20 ceiling, priced as plausible OTM calls so IV actually solves.
    # An earlier version of this fixture moved the SPOT far away instead and priced the resulting
    # deep-ITM calls BELOW intrinsic, which is arbitrage-impossible: IV had no solution, delta came
    # back NaN, dropna emptied the menu and the test failed against correct code. The fixture was
    # the defect, and it is recorded here because a fixture that cannot price is indistinguishable
    # from a filter that rejects.
    rows = [{"expiration": exp, "strike": 100.0 * m, "right": "C", "date": asof,
             "bid": 1.40, "ask": 1.60, "volume": 500, "open_interest": 2000}
            for m in (1.21, 1.24, 1.27, 1.30)]
    ch = pd.DataFrame(rows)
    assert M.build_menu(ch, 100.0, asof),         "the fallback was removed; the menu is no longer the engine's"
    # and the source still carries it
    assert "near = d" in _src()


def test_an_unfillable_chain_yields_no_menu():
    """The fillability filter is load-bearing: it removes nearly half the in-band contracts."""
    asof = dt.date(2019, 3, 4)
    ch = _chain(asof)
    ch["volume"] = 0
    ch["open_interest"] = 0
    ch["bid"] = 0.0
    assert M.build_menu(ch, 100.0, asof) is None


# ------------------------------------------------------------------ the kill condition
def test_the_kill_condition_fires_on_the_weaker_half_not_on_both():
    """`any`, never `all`. Softening it to "both halves" inverts the item's meaning."""
    tree = ast.parse(_src())
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_arms"][0]
    srcseg = ast.get_source_segment(_src(), fn)
    assert "kill = any(" in srcseg, "the kill condition must be any(), not all()"
    assert "kill = all(" not in srcseg


def test_the_kill_bar_is_the_registered_one():
    assert M.KILL_PP == 1.0
    assert M.C1_FLOOR == 0.99
    assert M.C2_COVERAGE_TOL_PP == 2.0


def test_the_delta_buckets_are_the_registered_grid():
    assert M.DELTA_BUCKETS == ((0.00, 0.15), (0.15, 0.35), (0.35, 0.60), (0.60, 1.01))


# --------------------------------------------------------------------- the two passes
def test_the_two_passes_may_not_run_in_one_invocation():
    for argv in ([], ["--controls", "--arms"]):
        try:
            M.main(argv)
        except SystemExit as e:
            assert e.code != 0
        else:
            raise AssertionError("should have exited on %r" % (argv,))


def test_arms_refuses_without_a_passing_controls_artifact():
    old = M.CONTROLS_OUT
    try:
        M.CONTROLS_OUT = os.path.join(tempfile.mkdtemp(), "absent.json")
        assert M.run_arms() == 2
        p = os.path.join(tempfile.mkdtemp(), "c.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump({"all_gating_pass": False}, fh)
        M.CONTROLS_OUT = p
        assert M.run_arms() == 2
    finally:
        M.CONTROLS_OUT = old


# ------------------------------------------------------------------------- hygiene
def test_the_arm_never_opens_the_mutable_store():
    s = _src()
    assert 'join(DATA, "options")' not in s
    assert "resolve_harvest" in s
    assert "allow_mutable" not in s


def test_resolution_is_lazy_because_ci_has_no_d_drive():
    for node in ast.parse(_src()).body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                if sub.func.attr == "resolve_harvest" and isinstance(node, (ast.Assign, ast.Expr)):
                    raise AssertionError("resolve_harvest is called at module level")


def test_a_zero_leg_arm_raises_rather_than_writing_a_null():
    s = _src()
    assert "ZERO legs in an arm" in s
    fn = [n for n in ast.parse(s).body
          if isinstance(n, ast.FunctionDef) and n.name == "run_arms"][0]
    assert any(isinstance(x, ast.Raise) for x in ast.walk(fn))


def test_the_settlement_path_never_reaches_the_network():
    """S23's defect: a banked reproduction that silently fetches."""
    assert "OB.load_bars(" not in _src()
    assert "NEVER fetches" in _src()


def test_the_register_exists_and_is_cited():
    assert os.path.isfile(REGISTER)
    assert "PREREG_mb1_alternatives_menu.md" in _src()


def test_the_comparator_is_r2s_own_books_not_a_new_control():
    """Constructing a new random-entry control is a void condition."""
    assert "control_r2_splitclean_seed%d.pkl" in _src()


if __name__ == "__main__":
    # RUN_RULES line 25 runs each suite as its own process. WITHOUT THIS BLOCK THE FILE WOULD
    # EXIT 0 HAVING RUN NOTHING - the vacuous pass MB42's sibling defect was, caught last session.
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
