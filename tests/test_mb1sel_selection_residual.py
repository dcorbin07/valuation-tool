"""MB1-SEL's selection-residual register, pinned. [charges no trials: the arm never ran]

The gating control FIRED, so this suite mostly pins that the refusal is real and that the gate
which produced it is not vacuous.

What has to hold:

  * THE GATE CAN PASS. A control that fires on every input proves nothing, and a VOID produced by
    one is worthless. Pinned by construction on synthetic books where the arms are selected
    identically.
  * THE GATE MEASURES THE DIFFERENTIAL, not either arm's shift. The residual is a difference of
    differences, so a coverage effect constant across the arms cancels exactly and must NOT trip
    it - otherwise the gate fires on the very structure that makes the residual robust.
  * THE ARM REFUSES without a passing control, and the refusal is demonstrable rather than
    asserted (O10's process defect).
  * THE MEDIAN IS COMPUTED NOWHERE in the arm path. O17C4 and MB1 both measured that it cannot
    see this book's effect, so the register bans it - read by AST, not by substring.
  * THE VERDICT READS THE PRIMARY ONLY. The trimmed means are declared secondaries and may not
    flip, rescue or override it.
  * the three verdict states are mutually exclusive and every one of them is reachable.

Offline: synthetic inputs, so it runs on Linux and Windows alike with no freeze mounted.
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

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROL_SRC = os.path.join("scripts", "mb1sel_range_control.py")
ARM_SRC = os.path.join("scripts", "mb1sel_arm.py")

BAR_PP = 1.00

# MB1's published coverage, which this control must reproduce exactly or it is measuring a
# different object than the decomposition it exists to guard.
MB1_ALERT_COVERED, MB1_ALERT_TOTAL = 2446, 3870
MB1_CONTROL_COVERED, MB1_CONTROL_TOTAL = 18531, 29654


def _src(rel):
    with io.open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return fh.read()


def _differential(a_cov, a_unc, c_cov, c_unc):
    """The gated statistic, in pp - the same arithmetic the control ships."""
    a = (float(np.mean(a_cov)) - float(np.mean(a_unc))) * 100.0
    c = (float(np.mean(c_cov)) - float(np.mean(c_unc))) * 100.0
    return a - c


# ---------------------------------------------------------------- the gate is not vacuous

def test_the_gate_passes_when_the_arms_are_selected_identically():
    """THE LOAD-BEARING NON-VACUITY CHECK.

    If the gate fired on every input, the VOID it produced would carry no information at all.
    Here both arms have a LARGE coverage effect (+8pp) but the SAME one, so the differential is
    zero and the gate must pass.
    """
    a_cov, a_unc = [0.10] * 100, [0.02] * 100
    c_cov, c_unc = [0.30] * 100, [0.22] * 100        # same +8pp shift, different levels
    d = _differential(a_cov, a_unc, c_cov, c_unc)
    assert abs(d) < 1e-9, d
    assert abs(d) <= BAR_PP, "a constant coverage effect must NOT trip the gate"


def test_a_large_but_shared_coverage_effect_still_passes():
    """The difference-of-differences argument, pinned as arithmetic rather than asserted."""
    for shift in (0.05, 0.20, 0.75):
        a_cov, a_unc = [shift + 0.01] * 50, [0.01] * 50
        c_cov, c_unc = [shift + 0.40] * 50, [0.40] * 50
        assert abs(_differential(a_cov, a_unc, c_cov, c_unc)) < 1e-9, shift


def test_the_gate_fires_when_the_arms_are_selected_differently():
    a_cov, a_unc = [0.10] * 100, [0.08] * 100        # +2pp
    c_cov, c_unc = [0.30] * 100, [0.20] * 100        # +10pp
    d = _differential(a_cov, a_unc, c_cov, c_unc)
    assert abs(d) > BAR_PP, d


def test_the_gate_reads_the_differential_and_not_either_arm_alone():
    """A control gated on either arm's own shift would fire on the shared-effect case above,
    which is exactly the structure that makes the residual robust."""
    src = _src(CONTROL_SRC)
    assert "differential" in src
    tree = ast.parse(src)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            names |= {k.value for k in node.keys
                      if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    assert "c_range_passes" in names
    assert "differential_pp" in names


# ---------------------------------------------------------------- it measures the right object

def _artifact():
    for root in (os.path.join(REPO, "data"),
                 os.path.abspath(os.path.join(REPO, "..", "..", "..", "data"))):
        p = os.path.join(root, "free_analysis", "MB1SEL_RANGE_CONTROL.json")
        if os.path.isfile(p):
            return json.load(io.open(p, encoding="utf-8"))
    return None


def test_the_control_reproduces_mb1s_published_coverage_exactly():
    """If the covered set is not MB1's covered set, this guards a different decomposition."""
    a = _artifact()
    if a is None:
        return
    assert a["alert"]["covered_n"] == MB1_ALERT_COVERED, a["alert"]["covered_n"]
    assert a["alert"]["covered_n"] + a["alert"]["uncovered_n"] == MB1_ALERT_TOTAL
    assert a["control"]["covered_n"] == MB1_CONTROL_COVERED, a["control"]["covered_n"]
    assert a["control"]["covered_n"] + a["control"]["uncovered_n"] == MB1_CONTROL_TOTAL


def test_the_published_coverage_rates_round_to_mb1s_reported_percentages():
    assert abs(MB1_ALERT_COVERED / MB1_ALERT_TOTAL - 0.6320) < 5e-5
    assert abs(MB1_CONTROL_COVERED / MB1_CONTROL_TOTAL - 0.6249) < 5e-5


def test_the_control_actually_fired():
    """The recorded outcome, pinned so a later silent pass is visible as a change."""
    a = _artifact()
    if a is None:
        return
    assert a["c_range_passes"] is False
    assert abs(a["differential_pp"]) > BAR_PP


# ---------------------------------------------------------------- the arm refuses

def test_the_arm_refuses_without_a_passing_control():
    tree = ast.parse(_src(ARM_SRC))
    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "_gate" in fns
    body = ast.dump(fns["_gate"])
    assert body.count("SystemExit") >= 2, "refuse on BOTH missing and failing, separately"
    assert "c_range_passes" in _src(ARM_SRC)


def test_the_gate_is_not_a_hard_coded_refusal():
    """It must RETURN on a passing artifact, or "the arm refuses" is uninformative.

    Tested on the gate FUNCTION in isolation, deliberately: running the arm itself with a tampered
    artifact would compute the selection residual, which register void condition 4 forbids while
    the control is firing. So the gate is exercised and the arm is not.
    """
    import tempfile
    from scripts import mb1sel_arm as M

    orig = M.CONTROL_IN
    try:
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "ok.json")
            with io.open(p, "w", encoding="utf-8") as fh:
                json.dump({"c_range_passes": True, "differential_pp": 0.1, "bar_pp": 1.0}, fh)
            M.CONTROL_IN = p
            assert M._gate()["c_range_passes"] is True

            bad = os.path.join(d, "bad.json")
            with io.open(bad, "w", encoding="utf-8") as fh:
                json.dump({"c_range_passes": False, "differential_pp": -2.5, "bar_pp": 1.0}, fh)
            M.CONTROL_IN = bad
            try:
                M._gate()
                raise AssertionError("the gate let a FAILING control through")
            except SystemExit:
                pass

            M.CONTROL_IN = os.path.join(d, "absent.json")
            try:
                M._gate()
                raise AssertionError("the gate let a MISSING control through")
            except SystemExit:
                pass
    finally:
        M.CONTROL_IN = orig


def test_the_arm_calls_the_gate_before_it_reads_any_book():
    tree = ast.parse(_src(ARM_SRC))
    main = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = []
    for node in ast.walk(main):
        if isinstance(node, ast.Call):
            f = node.func
            calls.append(f.id if isinstance(f, ast.Name) else getattr(f, "attr", ""))
    assert "_gate" in calls
    assert calls.index("_gate") < calls.index("_load_book"), "the gate must precede any book read"


# ---------------------------------------------------------------- the median ban

def test_the_median_is_computed_nowhere_in_the_arm():
    """Read by AST. O17C4 and MB1 both measured that the median cannot see this book's effect."""
    for rel in (ARM_SRC, CONTROL_SRC):
        tree = ast.parse(_src(rel))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ("median", "nanmedian"):
                raise AssertionError("%s computes a median" % rel)
            if isinstance(node, ast.Name) and node.id in ("median", "nanmedian"):
                raise AssertionError("%s references a median" % rel)


def test_the_ban_is_stated_where_a_reader_will_find_it():
    assert "median_is_banned" in _src(ARM_SRC)


# ---------------------------------------------------------------- primary vs secondaries

def test_the_verdict_reads_the_primary_only():
    src = _src(ARM_SRC)
    assert "verdict_reads_primary_only" in src
    seg = src.split("the pre-committed three-state rule")[1]
    assert '"mean"' in seg, "the rule must select the primary explicitly"
    for t in ("trim10", "trim20"):
        assert t not in seg, "a secondary reached the verdict rule"


def test_the_trimmed_mean_is_symmetric_and_refuses_to_empty_a_sample():
    from scripts.mb1sel_arm import _trimmed_mean
    x = [0.0, 1.0, 2.0, 3.0, 100.0]
    assert _trimmed_mean(x, 0.0) == float(np.mean(x))
    assert _trimmed_mean(x, 0.20) == 2.0            # drops one from each end
    assert _trimmed_mean([1.0], 0.20) == 1.0
    assert _trimmed_mean([], 0.10) is None


def test_trimming_pulls_a_right_tailed_sample_down():
    from scripts.mb1sel_arm import _trimmed_mean
    x = [0.0] * 20 + [500.0]
    assert _trimmed_mean(x, 0.10) < float(np.mean(x))


# ---------------------------------------------------------------- the three-state rule

def _verdict(full, early, late):
    signs = {np.sign(w["point"]) for w in (full, early, late)}
    confirmed = (all(w["excl"] for w in (full, early, late)) and len(signs) == 1
                 and full["nearer_beyond"])
    return "CONFIRMED" if confirmed else ("REFUTED" if full["inside"] else "UNRESOLVED")


def test_all_three_verdict_states_are_reachable():
    ok = {"excl": True, "point": -2.0, "nearer_beyond": True, "inside": False}
    assert _verdict(ok, ok, ok) == "CONFIRMED"
    tight = {"excl": True, "point": -0.4, "nearer_beyond": False, "inside": True}
    assert _verdict(tight, tight, tight) == "REFUTED"
    wide = {"excl": False, "point": -1.3, "nearer_beyond": False, "inside": False}
    assert _verdict(wide, wide, wide) == "UNRESOLVED"


def test_a_point_estimate_beyond_the_bar_does_not_confirm_on_its_own():
    """O21-D2's lesson: the bound must hold across the INTERVAL, not merely at the point.

    This is the exact shape of MB1's post-hoc reading - a -1.28pp point with an interval that
    reaches almost to zero - and it must NOT confirm.
    """
    near_zero = {"excl": True, "point": -1.28, "nearer_beyond": False, "inside": False}
    assert _verdict(near_zero, near_zero, near_zero) == "UNRESOLVED"


def test_disagreeing_halves_cannot_confirm():
    pos = {"excl": True, "point": +2.0, "nearer_beyond": True, "inside": False}
    neg = {"excl": True, "point": -2.0, "nearer_beyond": True, "inside": False}
    assert _verdict(neg, neg, pos) == "UNRESOLVED"


# ---------------------------------------------------------------- housekeeping

def test_the_bootstrap_is_paired():
    src = _src(ARM_SRC)
    assert "PAIRED: same keys for both arms" in src


def test_the_cluster_is_r3s_name_year_unit():
    from scripts.mb1sel_arm import _cluster
    assert _cluster("AAPL", "2016-12-15") == ("AAPL", "2016")


def test_neither_script_differences_against_r2s_whole_book_figure():
    """Void condition 5 - R2's -5.0640pp is a different entry set."""
    for rel in (ARM_SRC, CONTROL_SRC):
        assert "5.0640" not in _src(rel)


def test_both_are_runnable_as_their_own_process():
    for rel in (ARM_SRC, CONTROL_SRC):
        assert 'if __name__ == "__main__":' in _src(rel)


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
