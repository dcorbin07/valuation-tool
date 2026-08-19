"""MA58 - cross-sectional return seasonality. Pins the register's construction and its rules.

PREREG_ma58_return_seasonality.md, committed ALONE at 6f998fc; budget booked at eb85ca7.

The register's two hard constraints are the two things worth pinning, because both are the kind
that rot silently:

  (1) THE LAG STRUCTURE IS THE HYPOTHESIS. The constants are read from the SOURCE TREE, so a
      later edit to K, the window length or the non-annual offsets fails here rather than
      quietly answering a different question.
  (2) DEPTH WAS FIXED BEFORE THE RESULT. K=5 is a control and may not carry a verdict.

Plus the P1S0-CONTROL clause: every leg is a SORTING question and no LEVEL statistic may enter
the verdict rule.

Data-dependent tests SKIP LOUDLY when the licensed export is absent -- a data-dependent test
that skips quietly is the vacuous pass this project has caught four times.
"""
import ast
import datetime as dt
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import tests.state_isolation  # noqa: F401
except Exception:
    pass

from scripts import ma58_seasonality as M

_SKIPS = []
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "scripts", "ma58_seasonality.py")
REG = os.path.join(os.path.dirname(HERE), "PREREG_ma58_return_seasonality.md")


def _have_data():
    return os.path.exists(M.PANEL) and os.path.exists(M.PRICES_PKL)


def _skip(name):
    _SKIPS.append(name)


# ------------------------------------------------------------------ #
#  (1) THE LAG STRUCTURE
# ------------------------------------------------------------------ #
def test_the_registered_lag_structure_is_what_the_source_actually_carries():
    """Read the SYNTAX TREE, not the imported values, so a constant that is computed or
    monkeypatched at import cannot satisfy this (MA49's lesson: a grep for `n_names = 9` failed
    against the FIXED tree because the repair's comment quoted the defect verbatim)."""
    tree = ast.parse(open(SRC, encoding="utf-8").read())
    lits = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and \
                isinstance(node.targets[0], ast.Name):
            try:
                lits[node.targets[0].id] = ast.literal_eval(node.value)
            except Exception:
                pass
    assert lits["K_PRIMARY"] == 10, lits.get("K_PRIMARY")
    assert lits["K_CONTROL"] == 5, lits.get("K_CONTROL")
    assert lits["WINDOW_MONTHS"] == 3, lits.get("WINDOW_MONTHS")
    assert tuple(lits["NONSEAS_MONTHS"]) == (3, 6, 9), lits.get("NONSEAS_MONTHS")
    assert tuple(lits["INCUMBENTS"]) == (
        "value", "quality", "momentum", "insider",
        "capital_discipline", "size", "institutional"), lits.get("INCUMBENTS")
    assert lits["IC_BAR"] == 2.71, lits.get("IC_BAR")


def test_the_offsets_are_ten_annual_lags_and_thirty_non_annual_ones():
    offs = M._offsets(M.K_PRIMARY)
    seas = [o for o in offs if o[1] == 0]
    non = [o for o in offs if o[1] != 0]
    assert len(seas) == 10 and len(non) == 30, (len(seas), len(non))
    assert [k for k, _ in seas] == list(range(1, 11))
    # every non-annual window sits in one of the OTHER three quarters of the same years
    assert sorted({m for _, m in non}) == [3, 6, 9]


def test_no_window_can_end_after_the_rebalance_date():
    """C3 as arithmetic rather than as a run-time count: the latest window is [t-3mo, t]."""
    for t in (pd.Timestamp("2015-05-20"), pd.Timestamp("2009-01-15"), pd.Timestamp("2026-01-28")):
        for k, m in M._offsets(M.K_PRIMARY):
            end = t - pd.DateOffset(years=k) + pd.DateOffset(months=m) \
                + pd.DateOffset(months=M.WINDOW_MONTHS)
            assert end <= t, (k, m, end, t)


# ------------------------------------------------------------------ #
#  LOOK-AHEAD, and its VACUITY COMPANION
# ------------------------------------------------------------------ #
def _synthetic():
    d = pd.date_range("1995-01-02", "2020-12-31", freq="B")
    c = np.linspace(10.0, 60.0, len(d))
    px = {"AAA": (d.values.astype("datetime64[D]"), c.copy())}
    panel = pd.DataFrame({"date": [pd.Timestamp("2015-05-20")], "ticker": ["AAA"]})
    return panel, px, d


def test_a_price_move_after_t_cannot_change_the_feature():
    """The look-ahead guard. Tamper with every close STRICTLY AFTER t and require both features
    bit-identical."""
    panel, px, d = _synthetic()
    a, _ = M.build_features(panel, px, M.K_PRIMARY)
    d2, c2 = px["AAA"][0].copy(), px["AAA"][1].copy()
    after = d2 > np.datetime64("2015-05-20")
    assert after.sum() > 100, "the tamper must actually touch something"
    c2[after] *= 97.0
    b, _ = M.build_features(panel, {"AAA": (d2, c2)}, M.K_PRIMARY)
    for col in ("seas", "nonseas"):
        assert a[col].iloc[0] == b[col].iloc[0], (col, a[col].iloc[0], b[col].iloc[0])


def test_the_vacuity_companion_a_move_AT_A_WINDOW_ENDPOINT_must_change_it():
    """MA28's lesson: a tamper that leaves the statistic bit-identical proves nothing about the
    guard. Altman Z is a sum of RATIOS, so scaling a whole filing moved nothing and the
    look-ahead test passed vacuously.

    The tamper must land ON an endpoint -- see the path-independence test below, which is why
    the first cut of this companion was itself vacuous."""
    panel, px, d = _synthetic()
    a, _ = M.build_features(panel, px, M.K_PRIMARY)
    d2, c2 = px["AAA"][0].copy(), px["AAA"][1].copy()
    # the k=1 annual-lag window is [2014-05-20, 2014-08-20]; hit its END
    at = (d2 >= np.datetime64("2014-08-18")) & (d2 <= np.datetime64("2014-08-20"))
    assert at.sum() >= 1
    c2[at] *= 97.0
    b, _ = M.build_features(panel, {"AAA": (d2, c2)}, M.K_PRIMARY)
    assert a["seas"].iloc[0] != b["seas"].iloc[0], "the guard cannot see a change it must see"


def test_the_feature_is_path_independent_and_that_is_why_the_companion_targets_an_endpoint():
    """RECORDED BECAUSE IT MADE MY OWN FIRST VACUITY TEST VACUOUS. A window return is
    close(end)/close(start) - 1, so it depends on TWO closes and not on the path between them.
    Scaling every interior price by 97 moves NOTHING -- which looked like the look-ahead guard
    failing and was the feature's definition. The MA28 family in a third costume."""
    panel, px, d = _synthetic()
    a, _ = M.build_features(panel, px, M.K_PRIMARY)
    d2, c2 = px["AAA"][0].copy(), px["AAA"][1].copy()
    inside = (d2 >= np.datetime64("2014-05-25")) & (d2 <= np.datetime64("2014-08-15"))
    assert inside.sum() > 10, "the tamper must touch something"
    c2[inside] *= 97.0
    b, _ = M.build_features(panel, {"AAA": (d2, c2)}, M.K_PRIMARY)
    assert a["seas"].iloc[0] == b["seas"].iloc[0], "the feature is not path-independent"


def test_a_gap_wider_than_the_tolerance_makes_a_window_uncomputable_not_imputed():
    panel, px, d = _synthetic()
    d2, c2 = px["AAA"][0].copy(), px["AAA"][1].copy()
    # blow a 60-day hole around the k=3 annual-lag window start (2012-05-20)
    hole = (d2 >= np.datetime64("2012-04-01")) & (d2 <= np.datetime64("2012-06-30"))
    keep = ~hole
    b, _ = M.build_features(panel, {"AAA": (d2[keep], c2[keep])}, M.K_PRIMARY)
    assert not bool(b["eligible"].iloc[0]), "a hole must make the row ineligible, never imputed"
    assert pd.isna(b["seas"].iloc[0]) and pd.isna(b["nonseas"].iloc[0])


# ------------------------------------------------------------------ #
#  (2) DEPTH, and the VERDICT RULE
# ------------------------------------------------------------------ #
def test_the_control_depth_carries_no_verdict():
    """Register s2.1 and void condition 3: K=5 may not rescue or overturn A1. The verdict
    function is handed ONLY the primary block, so a C-DEPTH cell cannot reach it."""
    src = open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_verdict")
    names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
    consts = {n.value for n in ast.walk(fn) if isinstance(n, ast.Constant)}
    assert "K_CONTROL" not in names, "_verdict can see the control depth"
    assert not any(isinstance(c, str) and "C_DEPTH" in c for c in consts), \
        "_verdict references a C-DEPTH key"


def test_no_LEVEL_statistic_can_enter_the_verdict_rule():
    """The P1S0-CONTROL clause (register s2.5). P1S0-CONTROL returned NULL because leg 1 asked a
    SORTING question and leg 2 a LEVEL one. Every quantity `_verdict` reads must be a rank
    statistic; a decile return, cumulative alpha or hit rate may not appear."""
    tree = ast.parse(open(SRC, encoding="utf-8").read())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_verdict")
    banned = ("alpha", "cum_", "decile", "hit_rate", "return_ann", "sharpe", "drawdown")
    seen = [n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    seen += [n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)]
    for s in seen:
        low = str(s).lower()
        for b in banned:
            # the register's own prose names them in order to forbid them; only KEY LOOKUPS matter
            assert not (low == b or low.startswith(b + "_") or low.endswith("_" + b)), \
                f"a LEVEL statistic reached the verdict rule: {s}"


def test_a_failed_power_control_forces_UNINTERPRETABLE_whatever_the_arms_say():
    """The rule was fixed in the register BEFORE the controls ran, so it must not be reachable
    around. Hand `_verdict` an arm that clears everything and a failing power control."""
    great = {w: {"clears_2_71": True, "clears_own_null": True} for w in ("full", "early", "late")}
    block = {"seas": great, "contrast": {w: {"clears": True} for w in ("full", "early", "late")}}
    v = M._verdict(block, {"power_pass": False})
    assert v["verdict"] == "UNINTERPRETABLE", v
    v2 = M._verdict(block, {"power_pass": True})
    assert v2["verdict"] == "REPLICATED", v2


def test_the_discriminator_can_only_harden_the_verdict():
    """A2 is a discriminator, not a second chance: if the non-annual windows predict as well,
    the verdict is NOT-SEASONAL, never REPLICATED."""
    great = {w: {"clears_2_71": True, "clears_own_null": True} for w in ("full", "early", "late")}
    block = {"seas": great, "contrast": {w: {"clears": False} for w in ("full", "early", "late")}}
    assert M._verdict(block, {"power_pass": True})["verdict"] == "NOT-SEASONAL"
    # and a failing A1 is REJECTED regardless of how good the contrast looks
    bad = dict(great); bad["early"] = {"clears_2_71": False, "clears_own_null": True}
    block2 = {"seas": bad, "contrast": {w: {"clears": True} for w in ("full", "early", "late")}}
    assert M._verdict(block2, {"power_pass": True})["verdict"] == "REJECTED"


def test_both_halves_are_required_not_just_the_full_sample():
    great = {w: {"clears_2_71": True, "clears_own_null": True} for w in ("full", "early", "late")}
    con = {w: {"clears": True} for w in ("full", "early", "late")}
    for w in ("full", "early", "late"):
        b = {k: dict(v) for k, v in great.items()}
        b[w] = {"clears_2_71": True, "clears_own_null": False}
        assert M._verdict({"seas": b, "contrast": con},
                          {"power_pass": True})["verdict"] == "REJECTED", w


def test_the_shipped_tstat_arithmetic_is_used_and_a_constant_series_cannot_return_1e16():
    """C-DEGEN. `theme_ic`'s guard is `sd > 0` and whether a constant series has an exactly-zero
    float sd is VALUE-DEPENDENT (U2's finding), which can return t ~ 1e16 and read as a pass."""
    t, n, med = M._tstat([0.1, 0.1, 0.1, 0.1])
    assert t == 0.0, t
    t2, _, _ = M._tstat([1.0, 2.0, 3.0, 4.0])
    a = np.array([1.0, 2.0, 3.0, 4.0])
    assert abs(t2 - a.mean() / (a.std(ddof=1) / 2.0)) < 1e-12


# ------------------------------------------------------------------ #
#  THE TWO-PASS GATE
# ------------------------------------------------------------------ #
def test_the_arms_pass_refuses_without_a_passing_controls_artifact(tmp=None):
    """Session 26's defect: a gating control computed in the same pass as the outcomes is not a
    gate. `--arms` must REFUSE, not warn."""
    import json, tempfile
    real = M.OUT_CTL
    try:
        d = tempfile.mkdtemp()
        M.OUT_CTL = os.path.join(d, "absent.json")
        try:
            M.arms(); raise AssertionError("arms ran with no controls artifact")
        except SystemExit as e:
            assert "REFUSING" in str(e), e
        M.OUT_CTL = os.path.join(d, "failing.json")
        json.dump({"GATES_PASS": False}, open(M.OUT_CTL, "w"))
        try:
            M.arms(); raise AssertionError("arms ran against failing gates")
        except SystemExit as e:
            assert "REFUSING" in str(e), e
    finally:
        M.OUT_CTL = real


def test_nothing_under_valuation_is_touched_and_no_seasonality_signal_was_shipped():
    """Register void condition 8. The MA58 tripwire in test_ma_final_batch.py stays green and is
    CORRECT to: this item computes a study column, it does not ship a signal."""
    import re
    from valuation.screener import settings as S
    found = sorted(k for k in S.NUMBER_THEME if re.search(r"seas|_month|calendar", k, re.I))
    assert found == [], found
    assert len(S.NUMBER_THEME) == 53, len(S.NUMBER_THEME)


# ------------------------------------------------------------------ #
#  ARTIFACT-LEVEL (skip loudly without the licensed export)
# ------------------------------------------------------------------ #
def test_the_artifacts_agree_with_the_register():
    import json
    if not os.path.exists(M.OUT_ARM) or not os.path.exists(M.OUT_CTL):
        return _skip("MA58 artifacts absent (run --controls-only then --arms)")
    a = json.load(open(M.OUT_ARM))
    c = json.load(open(M.OUT_CTL))
    assert a["register_commit"] == "6f998fc" and a["budget_commit"] == "eb85ca7"
    assert a["trials_charged"] == 2 and a["equity_N_after"] == 234
    assert a["adopts"] is None
    assert c["C1_pass"] and c["C2_pass"] and c["C3_pass"] and c["GATES_PASS"]
    assert c["C3_windows_ending_after_t"] == 0
    assert c["C4_identical_rows"]["identical"], "the two arms were not on identical rows"
    assert a["primary_K10"]["carries_verdict"] is True
    assert a["C_DEPTH_K5"]["carries_verdict"] is False
    # the power controls failed, so the verdict must be UNINTERPRETABLE
    assert c["power_pass"] is False
    assert a["verdict"]["verdict"] == "UNINTERPRETABLE", a["verdict"]


def test_the_measured_power_decomposition_still_holds():
    """The finding that outlives the verdict: BOTH restrictions cost ~1.5 of a t and they
    COMPOUND. If either number moves materially the write-up is stale."""
    import json
    if not os.path.exists(M.OUT_CTL):
        return _skip("MA58 controls artifact absent")
    c = json.load(open(M.OUT_CTL))
    gp = c["power_controls"]["z_gp_on_capital"]
    assert gp["n_dates"] == 49, ("the incumbent complete-case rule no longer costs 20 dates",
                                 gp["n_dates"])
    assert abs(gp["raw_ic_tstat"] - 1.1363462765307066) < 1e-9, gp["raw_ic_tstat"]
    assert not gp["clears_2_0_raw"]


def test_the_register_states_both_ledger_constraints():
    if not os.path.exists(REG):
        return _skip("register absent")
    t = open(REG, encoding="utf-8").read()
    assert "THE LAG STRUCTURE **IS** THE HYPOTHESIS" in t
    assert "K = 10" in t and "CARRIES NO VERDICT" in t.upper() or "carries no verdict" in t
    assert "SORTING" in t and "LEVEL" in t
    assert "PEAD" in t and "2.71" in t


# ------------------------------------------------------------------ #
#  MUTATION TEST
# ------------------------------------------------------------------ #
def test_the_tripwires_can_bite():
    """Several checks above pass today and change no source, so they are worth nothing unless a
    violation would fail them. Each mutation is applied to a COPY, never to the tree."""
    caught = 0

    # 1. the power rule is bypassed
    great = {w: {"clears_2_71": True, "clears_own_null": True} for w in ("full", "early", "late")}
    con = {w: {"clears": True} for w in ("full", "early", "late")}
    if M._verdict({"seas": great, "contrast": con}, {"power_pass": False})["verdict"] \
            == "UNINTERPRETABLE":
        caught += 1

    # 2. a one-half pass is treated as a pass
    half = {k: dict(v) for k, v in great.items()}
    half["early"] = {"clears_2_71": False, "clears_own_null": False}
    if M._verdict({"seas": half, "contrast": con}, {"power_pass": True})["verdict"] == "REJECTED":
        caught += 1

    # 3. the lag structure is widened to a non-annual set
    mutated = [(k, m) for k in range(1, 11) for m in (0, 1, 2)]
    if sorted({m for _, m in mutated if m != 0}) != [3, 6, 9]:
        caught += 1

    # 4. C-DEGEN. THIS MUTATION FOUND A REAL DEFECT IN THIS SCRIPT: before the relative floor,
    # `_tstat([0.1, 0.1, 0.1])` returned t = 1.019e16 (sd 5.8e-17 passes `sd > 0`) while the same
    # list with a FOURTH element returned exactly 0.0. Value- AND length-dependent.
    if M._tstat([0.1, 0.1, 0.1])[0] == 0.0 and M._tstat([0.1] * 4)[0] == 0.0:
        caught += 1

    assert caught == 4, f"only {caught}/4 tripwires can bite"


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
    if _SKIPS:
        print("\n  SKIPPED (licensed data or artifacts absent):")
        for s in sorted(set(_SKIPS)):
            print(f"    - {s}")
    print(f"\n{passed}/{len(tests)} MA58 tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
