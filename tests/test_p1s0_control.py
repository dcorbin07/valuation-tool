"""P1S0-CONTROL — was P1S0's dead early half a PERIOD or a UNIVERSE?

Run: python tests/test_p1s0_control.py

Register: `PREREG_p1s0control_period_or_universe.md`, committed ALONE at `dc618c4`.

WHAT THIS PINS

  IT IS NOT A RE-RUN (§0, §7 void condition 1). The single most likely way this item goes wrong
  is that it quietly re-scores P1S0 and publishes a second set of numbers for one question. The
  script must READ `P1S0_GATE.json` and never write it, must never call P1S0's own `arms()` or
  `placebo_floors()`, and must use `restrict()` for exactly one thing -- deriving a DATE LIST.
  Checked through the AST, because a grep cannot tell a call from prose about a call.

  THE FLOOR IS THE RIGHT FLOOR (§7 void condition 3). P1S0's placebo was calibrated on 619
  names; this statistic is on 2,531. Comparing them is the extrapolation `U2` avoided by
  declining. The verdict path must read its floor from the CONTROL's own placebo artifact.

  THE RULE IS THE REGISTERED RULE (§4). Three branches, and NULL when the legs disagree -- the
  branch most likely to be quietly dropped, because it is the one that returns no headline.

  THE CONSTRUCTION IS THE SAME OBJECT. The full-panel `full` cells must reproduce P1S0's shipped
  `reference_full_panel_same_dates` bit-for-bit. That is the strongest available evidence that
  the dates and the code really are P1S0's, and it is data-dependent, so it SKIPS loudly rather
  than passing vacuously when the artifacts are absent.

Tripwires are mutation-tested by `test_the_tripwires_can_bite`.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "p1s0_control_period_or_universe.py")
REGISTER = os.path.join(ROOT, "PREREG_p1s0control_period_or_universe.md")

_SKIPS: list[str] = []


def _src() -> str:
    with io.open(SCRIPT, "r", encoding="utf-8") as f:
        return f.read()


def _fn(name: str, src: str | None = None) -> ast.FunctionDef:
    for n in ast.walk(ast.parse(src if src is not None else _src())):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} not found")


def _calls(node: ast.AST) -> set[str]:
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                out.add(f.attr)
            elif isinstance(f, ast.Name):
                out.add(f.id)
    return out


def _find(rel: str) -> str | None:
    here = ROOT
    roots = [os.path.join(here, "data")]
    for _ in range(4):
        here = os.path.dirname(here)
        roots.append(os.path.join(here, "data"))
    for r in roots:
        p = os.path.join(r, rel)
        if os.path.exists(p):
            return p
    return None


# ======================================================================================
# it is not a re-run
# ======================================================================================

def test_p1s0s_artifact_is_read_and_never_written():
    """§7 void condition 1. `_w` is the only writer in this file; P1S0_GATE must never reach it."""
    src = _src()
    tree = ast.parse(src)
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_w":
            first = n.args[0] if n.args else None
            seg = ast.get_source_segment(src, first) or ""
            assert "P1S0_GATE" not in seg, f"_w() writes to P1S0's own artifact: {seg}"
    # ...and it IS read, or the comparison has no optionable side at all
    assert "_r(P1S0_GATE)" in src, "P1S0's artifact is not read — the optionable side is missing"


def test_no_p1s0_arm_or_placebo_is_recomputed():
    """Calling P1S0's own `arms()` or `placebo_floors()` would re-score the landed item."""
    calls = set()
    for f in ("run_arms", "run_placebo", "run_verdict", "windows", "_cells"):
        calls |= _calls(_fn(f))
    for banned in ("arms", "placebo_floors", "verdict", "score"):
        assert banned not in calls, (
            f"`{banned}` is called — that is P1S0's own machinery and re-running it publishes a "
            "second set of numbers for one question")


def test_restrict_is_used_only_to_derive_dates():
    """§3. `restrict()` gives the DATE LIST so the comparison is same-dates. If a restricted
    frame ever reached `arm()`, this would silently become a re-run of P1S0's arms."""
    src = _src()
    w = _fn("windows", src)
    assert "restrict" in _calls(w), "windows() no longer derives the dates from the partition"
    assert "arm" not in _calls(w), "windows() scores an arm — a restricted frame is being scored"
    # restrict must appear in NO other function
    for f in ("run_arms", "run_placebo", "run_verdict", "_cells"):
        assert "restrict" not in _calls(_fn(f, src)), f"{f} calls restrict()"


def test_the_family_is_not_reopened_by_this_item():
    src = _src()
    assert '"changed_by_this_item": False' in src, (
        "the artifact no longer records that P1S0's family verdict is unchanged")
    assert "NOT reopened" in src


# ======================================================================================
# the floor is the right floor
# ======================================================================================

def test_the_verdict_reads_the_controls_own_floor_not_p1s0s():
    """§7 void condition 3: 619 names vs 2,531. Using P1S0's floors here is the extrapolation
    U2 avoided by declining."""
    src = _src()
    body = src.split("def run_verdict", 1)[1]
    assert 'plac["floors"]' in body, "the floor does not come from the control's own placebo"
    # the P1S0 artifact may be read in the verdict pass, but never for a floor
    for bad in ('p1s0["placebo"]', "p1s0['placebo']"):
        assert bad not in body, "the verdict reads P1S0's restricted-universe floors"


def test_the_placebo_is_computed_on_the_full_panel():
    src = _src()
    p = _fn("run_placebo", src)
    seg = ast.get_source_segment(src, p) or ""
    assert "placebo_panel(panel" in seg, "the placebo is not built from the FULL panel"
    assert "leaked" in seg and "fwd_ret" in seg, "no forward-return leak check on the placebo"


# ======================================================================================
# the rule is the registered rule
# ======================================================================================

def test_the_decision_rule_has_all_three_branches_including_null():
    """The NULL branch returns no headline and is the one most likely to be quietly dropped."""
    src = _src()
    body = src.split("def run_verdict", 1)[1]
    for s in ('reading = "UNIVERSE"', 'reading = "PERIOD"', 'reading = "NULL"'):
        assert s in body, f"the decision rule lost its `{s}` branch"
    assert "leg1_clears and leg2_positive" in body
    assert "(not leg1_clears) and (not leg2_positive)" in body


def test_the_registered_constants_are_unchanged():
    import importlib
    m = importlib.import_module("scripts.p1s0_control_period_or_universe")
    assert m.ANCHOR == 63, m.ANCHOR
    assert m.LEG2_H == 252, m.LEG2_H
    assert m.HORIZONS == [63, 252, 504]
    assert m.PLACEBO_DRAWS == 200 and m.PLACEBO_SEED0 == 7100, "the placebo no longer matches P1S0"
    assert m.MODE == "pit_liquid", "P1S0's PRIMARY mode is pit_liquid"


def test_h504_cannot_decide():
    """§7 void condition 5: 504 is a diagnostic and may not be promoted."""
    body = _src().split("def run_verdict", 1)[1]
    assert "504" not in body, "H=504 appears in the verdict path — it is a diagnostic only"


def test_the_verdict_pass_refuses_without_both_artifacts():
    """The bar must exist before the statistic it judges is known."""
    import importlib
    m = importlib.import_module("scripts.p1s0_control_period_or_universe")

    class A:
        pass

    with tempfile.TemporaryDirectory() as d:
        a = A()
        a.arms_json = os.path.join(d, "no_arms.json")
        a.placebo_json = os.path.join(d, "no_placebo.json")
        a.out_json = os.path.join(d, "out.json")
        assert m.run_verdict(a) == 2, "the verdict ran with NO artifacts"
        with io.open(a.arms_json, "w", encoding="utf-8") as f:
            json.dump({}, f)
        assert m.run_verdict(a) == 2, "the verdict ran with no PLACEBO artifact"


# ======================================================================================
# the construction is the same object
# ======================================================================================

def test_the_full_panel_cells_reproduce_p1s0s_shipped_reference():
    """The strongest available evidence that the dates and the code really are P1S0's."""
    mine_p = _find(os.path.join("free_analysis", "P1S0_CONTROL_ARMS.json"))
    gate_p = _find(os.path.join("free_analysis", "P1S0_GATE.json"))
    if not mine_p or not gate_p:
        _SKIPS.append("test_the_full_panel_cells_reproduce_p1s0s_shipped_reference")
        return
    with io.open(mine_p, encoding="utf-8") as f:
        mine = json.load(f)
    with io.open(gate_p, encoding="utf-8") as f:
        ref = json.load(f)["modes"]["pit_liquid"]["reference_full_panel_same_dates"]
    for h in ("63", "252", "504"):
        a = mine["horizons"][h]["full_panel"]["full"]["cum_alpha"]
        b = ref[h]["full"]["cum_alpha"]
        assert mine["horizons"][h]["n_dates"] == ref[h]["n_dates"], h
        assert a == b, (
            f"H={h}: my full-panel cum_alpha {a!r} does not reproduce P1S0's shipped "
            f"reference {b!r} — this is not the same object")


def test_the_register_fixes_the_rule_and_the_windows():
    with io.open(REGISTER, encoding="utf-8") as f:
        t = " ".join(f.read().split())
    for s in ("THIS IS NOT A RE-RUN OF P1S0",
              "2016-01-20 → 2020-10-20",
              "the two legs disagree",
              "200 draws, seeds 7100–7299",
              "may not be compared with P1S0's restricted-universe floors".lower()):
        assert s in t or s in t.lower(), f"the register no longer fixes: {s}"


def test_the_register_states_a_prior_that_disagrees_with_the_brief():
    with io.open(REGISTER, encoding="utf-8") as f:
        t = " ".join(f.read().split()).replace("**", "")
    assert "I lean PERIOD, at roughly 55/45" in t
    assert "NULL is a live outcome" in t


def test_the_tripwires_can_bite():
    """MUTATION TEST, on COPIES only."""
    caught = 0
    src = _src()

    # 1. the script starts writing to P1S0's own artifact
    mutated = src.replace("_w(a.arms_json, out)", "_w(P1S0_GATE, out)", 1)
    bad = False
    for n in ast.walk(ast.parse(mutated)):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "_w":
            seg = ast.get_source_segment(mutated, n.args[0]) if n.args else ""
            if "P1S0_GATE" in (seg or ""):
                bad = True
    if bad:
        caught += 1

    # 2. a restricted frame reaches arm()
    mutated = src.replace("        ds = P.scorable_dates(r, h)",
                          "        ds = P.scorable_dates(r, h); arm(r, h)", 1)
    if "arm" in _calls(_fn("windows", mutated)):
        caught += 1

    # 3. the NULL branch is dropped
    mutated = src.replace('reading = "NULL"', 'reading = "PERIOD"', 1)
    if 'reading = "NULL"' not in mutated.split("def run_verdict", 1)[1]:
        caught += 1

    assert caught == 3, f"only {caught}/3 tripwires can bite"


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
        print("\n  SKIPPED (artifacts absent — reported, never silent):")
        for s in sorted(set(_SKIPS)):
            print(f"    - {s}")
    print(f"\n{passed}/{len(tests)} P1S0-CONTROL tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
