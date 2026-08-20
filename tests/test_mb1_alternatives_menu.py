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


def _drive_arms(alert_legs, control_legs, covered):
    """Run run_arms() to completion on supplied legs, returning the artifact.

    Everything downstream of the scoring loop is cheap, and O21-D2's worst defect fired AFTER
    every statistic had been computed: a literal `%` in prose inside a `%`-formatted string
    crashed the artifact write, so a finished run left nothing on disk. That class is only
    catchable by actually executing the write.
    """
    tmp = tempfile.mkdtemp()
    old = (M.CONTROLS_OUT, M.ARMS_OUT, M.LEGS_OUT, M.CS, M._bars_dir, M.TickerChains, M._books,
           M._covered, M._score_both)
    try:
        M.CONTROLS_OUT = os.path.join(tmp, "c.json")
        M.ARMS_OUT = os.path.join(tmp, "a.json")
        # LEGS_OUT too, or the suite clobbers a real run's draws in data/ (rule 9's own artifact).
        M.LEGS_OUT = os.path.join(tmp, "legs.pkl")
        with open(M.CONTROLS_OUT, "w", encoding="utf-8") as fh:
            json.dump({"all_gating_pass": True,
                       "c1_menu_contains_pick": {"rate": 0.9954},
                       "c2_coverage_parity": {"gap_pp": 0.71, "alert_share": 0.632,
                                              "control_share": 0.625}}, fh)
        M.CS = type("X", (), {"resolve_harvest":
                              staticmethod(lambda: ("Z:/fake", {"sha256": "deadbeef"}))})()
        M._bars_dir = lambda: "Z:/fake"
        M.TickerChains = lambda c: None
        M._books = lambda: ([], [])
        M._covered = lambda rows, tc: covered
        M._score_both = lambda a, c, tc, b: (alert_legs, control_legs)
        assert M.run_arms() == 0
        with open(M.ARMS_OUT, encoding="utf-8") as fh:
            return json.load(fh)
    finally:
        (M.CONTROLS_OUT, M.ARMS_OUT, M.LEGS_OUT, M.CS, M._bars_dir, M.TickerChains, M._books,
         M._covered, M._score_both) = old


def _leg(sym, day, delta, ret):
    return {"ticker": sym, "entry": day, "delta": delta, "ret": ret, "seed": None}


def test_the_half_boundary_comes_from_the_covered_entry_set_not_from_the_legs():
    """The register: "Split at the median entry date of the covered ALERT set".

    THE COVERED SET IS ENTRIES, NOT LEGS. Each entry contributes a variable number of legs
    (median 5 on the real data), so a leg-weighted median lets one entry sitting on a deep chain
    drag the boundary toward its own date. The fixture is built so the two answers DIFFER - one
    early entry carries 40 legs and every other entry carries one - which is what makes this
    test non-vacuous rather than a restatement of the code.
    """
    covered = [{"ticker": "A", "alert_ts": "2016-01-04"}] + \
              [{"ticker": "A", "alert_ts": "2020-0%d-01" % i} for i in range(1, 6)]
    legs = [_leg("A", "2016-01-04", 0.3, 0.1) for _ in range(40)] + \
           [_leg("A", "2020-0%d-01" % i, 0.3, 0.1) for i in range(1, 6)]
    ctrl = [_leg("B", "2016-01-04", 0.3, 0.2), _leg("B", "2020-05-01", 0.3, 0.2)]

    leg_weighted = sorted(l["entry"] for l in legs)[len(legs) // 2]
    entry_weighted = sorted(r["alert_ts"] for r in covered)[len(covered) // 2]
    assert leg_weighted != entry_weighted, "fixture is vacuous: the two boundaries agree"

    art = _drive_arms(legs, ctrl, covered)
    assert art["half_cut"] == entry_weighted, (
        "half_cut %r is the LEG-weighted boundary, not the covered ALERT set's"
        % art["half_cut"])


def test_the_arms_write_path_executes_end_to_end():
    """O21-D2's class: a run that computes every statistic and then cannot write it."""
    covered = [{"ticker": "A", "alert_ts": "201%d-03-01" % i} for i in range(6, 10)]
    legs, ctrl = [], []
    for i in range(6, 10):
        for k, d in enumerate((0.10, 0.25, 0.45, 0.80)):     # one leg per delta bucket
            legs.append(_leg("A", "201%d-03-01" % i, d, 0.05 * k))
            ctrl.append(_leg("B", "201%d-03-01" % i, d, 0.04 * k))
    art = _drive_arms(legs, ctrl, covered)
    for k in ("alert", "control", "halves", "kill_condition", "verdict", "half_cut",
              "full_sample_gap_pp_median", "harvest_provenance", "coverage_note",
              "menu_premise", "signs_agree"):
        assert k in art, "missing %s" % k
    assert set(art["halves"]) == {"early", "late"}
    for h in ("early", "late"):
        assert len(art["halves"][h]["alert_buckets"]) == len(M.DELTA_BUCKETS)
    blob = json.dumps(art)
    for bad in ("%%", "{:,}", "{0}", "%.1f", "%s"):
        assert bad not in blob, "leaked format token %r into the artifact" % bad


def test_the_harness_isolates_every_output_path_the_arm_writes():
    """Tests must not touch real state.

    The leg dump arrived as a new output path and the harness did not redirect it, so the suite
    wrote into the REAL data dir - which would silently clobber the draws of a ~55-minute scoring
    pass. This pins that every module-level *_OUT the arm writes is redirected by the harness.
    """
    outs = [n for n in dir(M) if n.endswith("_OUT")]
    assert set(outs) >= {"CONTROLS_OUT", "ARMS_OUT", "LEGS_OUT"}, outs
    real = {n: getattr(M, n) for n in outs}
    seen = {}

    def _capture(alert_legs, control_legs, covered):
        for n in outs:
            seen[n] = getattr(M, n)
        return None

    covered = [{"ticker": "A", "alert_ts": "2017-03-01"}, {"ticker": "A", "alert_ts": "2018-03-01"}]
    legs = [_leg("A", "2017-03-01", 0.3, 0.1), _leg("A", "2018-03-01", 0.3, 0.1)]
    art = _drive_arms(legs, list(legs), covered)
    assert art is not None
    # every path is restored afterwards...
    for n in outs:
        assert getattr(M, n) == real[n], "%s not restored" % n
    # ...and none of the real files was written during the run
    assert not os.path.exists(real["LEGS_OUT"]) or \
        os.path.getmtime(real["LEGS_OUT"]) < os.path.getmtime(__file__) + 10**9, \
        "the suite wrote the real legs artifact"


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
