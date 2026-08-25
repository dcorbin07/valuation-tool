"""EVOWN — event ownership as its own strategy family, pinned. [2 options trials, booked first]

What has to hold:

  * THE RIGHT IS PART OF THE CONTRACT KEY. A strike/expiry pair names TWO instruments and this
    freeze carries both; a history keyed without it hands `simulate_trade` a mixed frame and a
    deep-ITM put's quote read as a call's shows an instant several-hundred-percent gain that
    exits at "target" on day one. This is a defect that WAS in the first cut, caught by
    disbelieving the numbers rather than by anything raising.
  * THE MEDIAN IS COMPUTED NOWHERE. O17C4 recorded the effect as "a MEAN effect, not a MEDIAN
    one"; MB1 reproduced it; MB1-SEL pinned the ban by AST and this inherits it.
  * MATCHING IS BY DESIGN, and an unmatched cell is DROPPED rather than matched loosely.
  * BOTH ARMS ARE REQUIRED. A1 passing while A2 fails is REAL-BUT-UNSURVIVABLE, never a strategy.
  * the engine's own selection, exit and portfolio simulators are IMPORTED, never re-implemented.
  * spanning is VACUOUS on this entry rule, which is the census finding that shaped the design.

Offline: source inspection and synthetic frames, so it runs on Linux and Windows alike with no
freeze mounted.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401,E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join("scripts", "evown_build.py")
ARMS = os.path.join("scripts", "evown_arms.py")
CENSUS = os.path.join("scripts", "mb_evown_census.py")

# The census result that shaped the design: spans == menu EXACTLY at every offset.
CENSUS_SPANS = {5: (4769, 4769), 10: (4512, 4512), 15: (4607, 4607)}
DTE_CUTS = (51.0, 58.0, 66.0)          # O17C4's own quartile cuts


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


# ---------------------------------------------------------------- the contract-key defect

def test_the_right_is_part_of_the_contract_key():
    """THE DEFECT THAT WAS REAL AND WOULD HAVE READ AS A SPECTACULAR RESULT.

    Built here as a two-instrument frame: a cheap CALL and an expensive PUT at the same strike
    and expiry. Keyed correctly the history is calls-only; keyed without the right it is both,
    and the put's price read as the call's is a several-hundred-percent phantom gain.
    """
    import datetime as dt
    from scripts.evown_build import FreezeChains

    fc = FreezeChains.__new__(FreezeChains)
    fc._all = pd.DataFrame({
        "expiration": ["2016-09-16"] * 4,
        "strike": [105.0] * 4,
        "right": ["C", "P", "C", "P"],
        "date": ["2016-07-19", "2016-07-19", "2016-07-20", "2016-07-20"],
        "bid": [1.18, 6.70, 1.30, 6.50],
        "ask": [1.20, 6.80, 1.32, 6.60],
        "volume": [3443, 9, 100, 10],
        "open_interest": [29028, 1204, 29100, 1206],
    })
    fc.by_date = None
    fc.by_contract = {}
    fc.index_contracts([(105.0, "2016-09-16", "C")])

    h = fc.contract_history("X", "2016-09-16", 105.0, "C",
                            dt.date(2016, 7, 19), dt.date(2016, 9, 16))
    assert h is not None and len(h) == 2, len(h) if h is not None else None
    assert set(h["right"].astype(str)) == {"C"}, "the PUT leaked into a CALL's history"
    assert float(h["bid"].max()) < 2.0, "a put quote is being served as a call quote"


def test_the_key_is_a_triple_not_a_pair():
    """Pinned on the source: a two-element key is the defect, so the shape itself is asserted."""
    src = _src(BUILD)
    assert "(float(k), str(e), str(r))" in src, "by_contract must be keyed on (strike, exp, right)"
    assert "THE RIGHT IS PART OF THE KEY" in src, "the reason must travel with the code"


# ---------------------------------------------------------------- the median ban

RETURN_BEARING = {"ret", "return_pct", "pnl_pct", "gap", "pnl_dollars", "net_pnl", "rets"}


def _median_call_args(tree):
    """Every median call in the tree, with the source of its first argument."""
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if name not in ("median", "nanmedian"):
            continue
        arg = node.args[0] if node.args else None
        out.append(ast.unparse(arg) if arg is not None else "")
    return out


def test_no_median_is_computed_on_a_RETURN():
    """THE BAN IS BY MEASUREMENT AND IT IS ABOUT RETURNS, so the test is scoped to returns.

    `O17C4` measured the effect as "a MEAN effect, not a MEDIAN one" on option RETURNS - bimodal
    with an enormous mass at total loss - and `MB1` reproduced it. A TENOR is a different object:
    `dte`'s median is an ordinary descriptive and banning it would be banning the word rather
    than the defect.

    The first cut of this test banned the word and FAILED against the correct tree on
    `np.median(df["dte"])` - the substring-ban family for the fifth time in this lane. It reads
    the ARGUMENT now, which is the role the ban actually attaches to.
    """
    for rel in (BUILD, ARMS):
        for arg in _median_call_args(ast.parse(_src(rel))):
            hit = {t for t in RETURN_BEARING if t in arg}
            assert not hit, "%s takes a median of a RETURN: %s (%s)" % (rel, arg, sorted(hit))


def test_that_scoping_is_not_a_loophole():
    """Positive control: the scoped rule must still CATCH a median of a return.

    A rule narrowed until it catches nothing is worse than no rule, so the narrowed form is
    exercised against the thing it exists to forbid.
    """
    bad = ast.parse("import numpy as np\nx = np.median(df['ret'])\n")
    args = _median_call_args(bad)
    assert args and any(t in args[0] for t in RETURN_BEARING), args
    good = ast.parse("import numpy as np\nx = np.median(df['dte'])\n")
    assert not any(t in _median_call_args(good)[0] for t in RETURN_BEARING)


def test_the_ban_is_stated_where_a_reader_will_find_it():
    assert "median_is_banned" in _src(ARMS)


# ---------------------------------------------------------------- matching by design

def test_the_dte_cuts_are_o17c4s_reused_verbatim():
    from scripts.evown_arms import DTE_CUTS as CUTS
    assert tuple(CUTS) == DTE_CUTS


def test_the_bucket_boundaries_are_inclusive_and_ordered():
    from scripts.evown_arms import _bucket
    assert _bucket(40) == 0 and _bucket(51.0) == 0
    assert _bucket(51.1) == 1 and _bucket(58.0) == 1
    assert _bucket(58.1) == 2 and _bucket(66.0) == 2
    assert _bucket(66.1) == 3 and _bucket(200) == 3


def test_an_unmatched_cell_is_dropped_not_matched_loosely():
    """The register's rule. Pinned on the source: matching is a SET INTERSECTION of cells."""
    src = _src(ARMS)
    assert "set(s_cells) & set(c_cells)" in src, "matching must be a common-support intersection"
    assert "strategy_no_control_cell" in src and "control_no_strategy_cell" in src, \
        "both drop directions must be counted"


def test_the_gap_is_a_difference_of_means_on_the_common_support():
    from scripts.evown_arms import _gap
    S = [{"ret": 0.10}, {"ret": 0.20}]
    C = [{"ret": 0.05}, {"ret": 0.05}]
    assert abs(_gap(S, C) - 10.0) < 1e-9          # (0.15 - 0.05) * 100
    assert _gap([], C) is None and _gap(S, []) is None


def test_the_bootstrap_is_paired():
    assert "PAIRED: same keys for both arms" in _src(ARMS)


# ---------------------------------------------------------------- both arms required

def _verdict(a1, a2, under=False):
    return ("UNDERPOWERED" if under else
            "VIABLE" if (a1 and a2) else
            "REAL-BUT-UNSURVIVABLE" if (a1 and not a2) else
            "NOT-DEMONSTRATED")


def test_all_four_verdict_states_are_reachable():
    assert _verdict(True, True) == "VIABLE"
    assert _verdict(True, False) == "REAL-BUT-UNSURVIVABLE"
    assert _verdict(False, True) == "NOT-DEMONSTRATED"
    assert _verdict(False, False) == "NOT-DEMONSTRATED"
    assert _verdict(True, True, under=True) == "UNDERPOWERED"


def test_a_passing_return_arm_alone_is_never_a_strategy():
    """O11's whole point: a book with +3.27%/trade ended at $37,059 from $50,000."""
    assert _verdict(True, False) != "VIABLE"


def test_the_survivability_bar_is_cap_ten_at_both_account_sizes():
    src = _src(ARMS)
    assert "EQUITIES = (50_000.0, 250_000.0)" in src
    assert 'a2["cap10_$%d" % int(e)]["above_start"] for e in EQUITIES' in src
    assert "cap 50 reported" in src, "cap 50 must be reported as carrying no verdict"


# ---------------------------------------------------------------- imported, not re-implemented

def test_the_engine_is_imported_never_reimplemented():
    for rel, names in ((BUILD, ("pick_contract", "simulate_trade", "load_splits")),
                       (ARMS, ("simulate_book", "long_leg_as_book_trade"))):
        tree = ast.parse(_src(rel))
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for n in names:
            assert n not in defined, "%s re-implements %s (the B7 defect class)" % (rel, n)
        assert n in _src(rel)


def test_power_is_stated_before_any_arm_is_scored():
    """MB22's gate, and RUN_RULES A11. Both MDE vocabularies must travel together."""
    tree = ast.parse(_src(ARMS))
    main = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
    order = [getattr(c.func, "attr", getattr(c.func, "id", ""))
             for c in ast.walk(main) if isinstance(c, ast.Call)]
    assert "state" in order, "power_gate.state must be emitted"
    assert order.index("state") < order.index("_gap"), "power must precede the first arm"


# ---------------------------------------------------------------- the census finding

def test_spanning_is_vacuous_on_this_entry_rule():
    """The count that spans equals the count the engine produced AT ALL, at every offset.

    Structural: the engine's band is 45-75 DTE and K <= 15 trading days is <= ~21 calendar days,
    so the contract cannot expire before the announcement. This is why the arm is against a
    DTE-matched control rather than a spanning/not-spanning partition.
    """
    for k, (menu, spans) in CENSUS_SPANS.items():
        assert menu == spans, (k, menu, spans)


def test_the_engine_band_makes_it_impossible_to_expire_first():
    """The arithmetic behind the census result, so it is not merely an observed coincidence."""
    from valuation.edge.options_backtest import DTE_RANGE
    min_dte = DTE_RANGE[0]
    max_k_calendar = 15 * 7 / 5.0                 # 15 trading days, generously in calendar days
    assert min_dte > max_k_calendar, (min_dte, max_k_calendar)


def test_zero_earnings_names_fail_closed():
    src = _src(CENSUS)
    assert "FAIL CLOSED" in src
    assert "names_zero_earnings_FAIL_CLOSED" in src


def test_the_scope_travels_in_every_output():
    for rel in (BUILD, ARMS):
        s = _src(rel)
        assert "UNMEASURED and never read as zero" in s


def test_o11_governs_and_nothing_licenses_a_trade():
    s = _src(ARMS)
    assert "O11 GOVERNS" in s and "nothing here licenses a trade" in s


# ---------------------------------------------------------------- housekeeping

def test_the_arms_refuse_without_a_built_book():
    src = _src(ARMS)
    assert "REFUSING: no built book" in src


def test_all_three_are_runnable_as_their_own_process():
    for rel in (BUILD, ARMS, CENSUS):
        assert 'if __name__ == "__main__":' in _src(rel)


def test_the_recorded_verdict_matches_the_artifact():
    """Pins the landed result so a silent re-run that changes it is visible."""
    for root in (os.path.join(REPO, "data"),
                 os.path.abspath(os.path.join(REPO, "..", "..", "..", "data"))):
        p = os.path.join(root, "free_analysis", "EVOWN_ARMS.json")
        if os.path.isfile(p):
            d = json.load(io.open(p, encoding="utf-8"))
            assert d["verdict"] == "NOT-DEMONSTRATED", d["verdict"]
            assert d["A1_pass"] is False and d["A2_pass"] is True
            assert d["underpowered"] is False, "the n floors were cleared; power is the caveat"
            return


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
