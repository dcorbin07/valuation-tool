"""MB1's decomposition, pinned. [charges no trials: it computes no verdict]

  * THE IDENTITY IS EXACT: pick_gap = menu_gap + selection_residual, to floating point.
  * IT CARRIES NO VERDICT. The register's kill fires on the pooled median in the arms pass; this
    reports the split beside it and may never decide anything.
  * THE RESIDUAL IS A DIFFERENCE OF DIFFERENCES, so an instrument bias constant across the two
    arms CANCELS. Pinned by measurement: shifting both picks by the same amount must not move the
    residual by one bit. That is the entire argument for mixing a banked series with a
    re-simulated one, so it has to be demonstrated rather than asserted.
  * R2's published whole-book gap is never differenced against a covered-subset figure.
  * an empty join RAISES rather than writing a decomposition from nothing (MA31's failure mode).
"""
from __future__ import annotations

import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

import scripts.mb1_decomposition as DEC  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "mb1_decomposition.py")


def _src():
    with open(SCRIPT, encoding="utf-8") as fh:
        return fh.read()


def test_the_identity_is_exact():
    d = DEC.decompose(0.0398, 0.1002, 0.0330, 0.0805)
    assert abs(d["menu_gap_pp"] + d["selection_residual_pp"] - d["pick_gap_pp"]) < 1e-9
    assert abs(d["day_share"] + d["selection_share"] - 1.0) < 1e-12


def test_a_constant_instrument_bias_cancels_from_the_residual():
    """The whole justification for mixing a banked series with a re-simulated one.

    If the banked pick series carried a constant bias b relative to the re-simulated menu, both
    arms' picks shift by b and the residual - a difference of differences - must not move.
    """
    base = DEC.decompose(0.0398, 0.1002, 0.0330, 0.0805)
    for b in (0.01, -0.05, 0.25):
        shifted = DEC.decompose(0.0398 + b, 0.1002 + b, 0.0330, 0.0805)
        assert abs(shifted["selection_residual_pp"] - base["selection_residual_pp"]) < 1e-9, b
        assert abs(shifted["menu_gap_pp"] - base["menu_gap_pp"]) < 1e-12, b


def test_a_differential_bias_does_NOT_cancel_and_the_test_says_so():
    """The exposure that survives, stated honestly: a bias differing BETWEEN the arms moves it."""
    base = DEC.decompose(0.0398, 0.1002, 0.0330, 0.0805)
    skew = DEC.decompose(0.0398 + 0.02, 0.1002, 0.0330, 0.0805)
    assert abs(skew["selection_residual_pp"] - base["selection_residual_pp"]) > 1.0


def test_it_emits_no_verdict():
    tree = ast.parse(_src())
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name):
                assert t.id.lower() not in ("kill", "verdict", "fires", "adopt", "decision"), t.id
        if isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    if k.value.lower() in ("verdict", "kill", "fires", "adopt"):
                        is_bool = isinstance(v, ast.Constant) and isinstance(v.value, bool)
                        assert not is_bool, k.value
    assert "DESCRIPTIVE - CARRIES NO VERDICT" in _src()


def test_r2s_published_figure_is_never_differenced():
    """It is a different entry set. Quoting it for orientation is fine; subtracting it is not."""
    s = _src()
    tree = ast.parse(s)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            for side in (node.left, node.right):
                if isinstance(side, ast.Name) and "R2_PUBLISHED" in side.id:
                    raise AssertionError("differences R2's whole-book figure")
    assert "never differenced against anything here" in s


def test_an_empty_join_raises():
    s = _src()
    assert "ZERO banked trades matched" in s
    fn = [n for n in ast.parse(s).body if isinstance(n, ast.FunctionDef) and n.name == "main"][0]
    assert any(isinstance(x, ast.Raise) for x in ast.walk(fn))


def test_it_refuses_without_the_arms_artifacts():
    old = DEC.LEGS_IN
    try:
        DEC.LEGS_IN = os.path.join(REPO, "no", "such", "legs.pkl")
        assert DEC.main([]) == 2
    finally:
        DEC.LEGS_IN = old


def test_decompose_returns_none_on_a_missing_component():
    assert DEC.decompose(None, 0.1, 0.03, 0.08) is None


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
