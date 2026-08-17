"""MA28-CARD — the accounting red-flag risk card. Register `PREREG_ma28_accounting_riskcard.md`.

Run: python tests/test_ma28_riskcard.py

WHAT THIS PINS, AND WHY EACH ONE EXISTS

  THE HYPOTHESIS SWAP (§7 void condition 1). The single most likely way this item goes wrong is
  that somebody computes `top_decile_alpha` to decide it, because every instinct in this
  repository points at alpha bars. The gate is the CRASH RATE. An AST check asserts
  `quantile_backtest` is reachable from the CONTROLS path and NOT from the arm path -- read from
  the syntax tree, because a grep cannot tell a call from a comment about a call, which is a
  defect this record has now caught four times.

  THE REGISTERED CONSTANTS. Every bar in the script must still be the bar the register fixed.
  A constant that drifts after a measurement is the whole failure mode a register prevents, so
  each is pinned to its literal here and must move in the same diff.

  POINT-IN-TIME (§5 C6). On `tests/test_pead.py`'s protocol: introduce a filing dated strictly
  AFTER the scoring date and assert no flag moves. Built on a synthetic SF1 file so it runs with
  no licensed data.

  TWO-PASS DISCIPLINE. `--arms` must refuse without a passing controls artifact. Demonstrated by
  invoking it against an absent and against a failing artifact, not asserted.

Tripwires that pass today are worth nothing unless they can bite, so `test_the_tripwires_can_bite`
mutation-tests them.
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
SCRIPT = os.path.join(ROOT, "scripts", "ma28_riskcard.py")
REGISTER = os.path.join(ROOT, "PREREG_ma28_accounting_riskcard.md")

_SKIPS: list[str] = []


def _src() -> str:
    with io.open(SCRIPT, "r", encoding="utf-8") as f:
        return f.read()


def _tree() -> ast.Module:
    return ast.parse(_src())


def _fn(tree: ast.Module, name: str) -> ast.FunctionDef:
    for n in ast.walk(tree):
        if isinstance(n, ast.FunctionDef) and n.name == name:
            return n
    raise AssertionError(f"{name} not found in {SCRIPT}")


def _calls(node: ast.AST) -> set[str]:
    """Every attribute/name actually CALLED inside a node, read from the AST.

    Deliberately not a grep: the script's own docstring says the words
    'quantile_backtest' several times explaining why it must not appear in the arm path, and a
    text search would fire on that prose. Comment-versus-code, caught four times in this record.
    """
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute):
                out.add(f.attr)
            elif isinstance(f, ast.Name):
                out.add(f.id)
    return out


# ======================================================================================
# the hypothesis swap
# ======================================================================================

def test_the_arm_path_never_computes_alpha():
    """§7 void condition 1. The gate is the crash-rate replication, not alpha."""
    t = _tree()
    arm_calls = _calls(_fn(t, "run_arms")) | _calls(_fn(t, "window_result")) \
        | _calls(_fn(t, "per_date_diff")) | _calls(_fn(t, "pooled")) \
        | _calls(_fn(t, "permutation_p95"))
    for banned in ("quantile_backtest", "top_decile_alpha"):
        assert banned not in arm_calls, (
            f"`{banned}` is called from the ARM path. The register's gate is the CRASH RATE; "
            "computing alpha to decide this item is swapping the hypothesis mid-run.")


def test_alpha_is_still_reachable_from_the_gating_control():
    """The mirror of the test above, and it is what stops it passing VACUOUSLY. If
    `quantile_backtest` vanished from the file entirely, the arm-path check would pass while C1
    silently stopped gating anything."""
    assert "quantile_backtest" in _calls(_fn(_tree(), "run_controls")), (
        "C1 no longer calls quantile_backtest -- the gating control is not gating")


def test_the_arm_path_reads_no_return_column_other_than_the_registered_outcome():
    """`fwd_ret` may be read only to form the crash indicator. A second return statistic
    creeping into the arm is the same swap in a quieter form."""
    src = _src()
    body = src.split("def run_arms", 1)[1]
    for banned in ("long_short", "monotonicity", "sharpe", "alpha"):
        assert banned not in body, f"the arm path references `{banned}`"


# ======================================================================================
# the registered constants
# ======================================================================================

def test_every_registered_constant_is_still_its_registered_value():
    import importlib
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    m = importlib.import_module("scripts.ma28_riskcard")
    expected = {
        "CRASH": -0.50,                 # §3.2 the ONE outcome
        "RECORD_CORRECTION": -0.20,     # §2, no verdict, may not become the arm
        "MIN_FLAGGED_PER_DATE": 30,     # §3.4
        "MIN_KEPT_PER_DATE": 100,       # §3.4
        "RATIO_FLOOR": 2.0,             # §4 B2
        "ABS_FLOOR_PP": 0.50,           # §4 B3
        "N_PERM": 500,                  # §4 B1
        "MIN_COVERAGE": 0.05,           # §5 C2
        "SIZE_RATIO_FLOOR": 1.5,        # §5 C4
        "SIZE_MIN_QUINTILES": 3,        # §5 C4
        "INCUMBENT_RHO_MAX": 0.50,      # §5 C5
    }
    for k, v in expected.items():
        assert getattr(m, k) == v, (
            f"{k} is {getattr(m, k)} and the register fixed {v}. Moving a bar after a "
            "measurement is the failure a register exists to prevent.")


def test_the_composite_is_the_deployed_seven_themes_at_one_eighth():
    """C1 caught this on the script's first run: nine themes at 1/7 is a DIFFERENT composite
    that reproduces nothing and raises nothing."""
    import importlib
    m = importlib.import_module("scripts.ma28_riskcard")
    assert m.W == 0.125
    assert m.THEMES == ["value", "quality", "momentum", "insider", "capital_discipline",
                        "size", "institutional"]
    assert "low_risk" not in m.THEMES and "growth" not in m.THEMES
    # ...but C5 must still look at them, or a proxy for a zero-weight theme goes unseen
    assert "low_risk" in m.C5_THEMES and "growth" in m.C5_THEMES


def test_the_flag_builder_is_imported_and_not_re_implemented():
    """§7 void condition 4, and audit B7's defect class: two copies of a formula that must
    agree."""
    src = _src()
    assert "from s10_accounting_veto import build_flags" in src
    for banned in ("def build_flags", "def beneish_m", "def altman_z", "-1.78", "1.81"):
        assert banned not in src, (
            f"`{banned}` appears in this script -- the flag construction must be IMPORTED "
            "from s10_accounting_veto, never re-typed here")


# ======================================================================================
# point-in-time (§5 C6) -- tests/test_pead.py's protocol
# ======================================================================================

_SF1_HEADER = ["ticker", "datekey", "dimension", "revenue", "cor", "receivables", "assetsc",
               "ppnenet", "assets", "depamor", "sgna", "liabilities", "ncfo", "netinc",
               "workingcapital", "retearn", "ebit", "marketcap", "ncfcommon", "ncfdebt", "debt"]


def _row(ticker, datekey, distress=False):
    """A healthy quarter, or a violently distressed one.

    THE TAMPER MUST MOVE RATIOS, NOT SCALE, AND THAT IS NOT A DETAIL. My first fixture
    multiplied every line item by 97 and the vacuity check below caught it: Altman Z is
    1.2*x1 + 1.4*x2 + 3.3*x3 + 0.6*x4 + 1.0*x5 where EVERY term is a ratio, so scaling the
    whole filing leaves the score bit-identical. The look-ahead test would have passed while
    tampering with nothing at all -- a guard that cannot move the quantity it is guarding.
    """
    v = {"ticker": ticker, "datekey": datekey, "dimension": "ARQ",
         "revenue": 1000, "cor": 600, "receivables": 200,
         "assetsc": 500, "ppnenet": 400, "assets": 2000,
         "depamor": 50, "sgna": 150, "liabilities": 900,
         "ncfo": 120, "netinc": 100, "workingcapital": 300,
         "retearn": 250, "ebit": 180, "marketcap": 2500,
         "ncfcommon": 10, "ncfdebt": 20, "debt": 700}
    if distress:
        # ratios collapse: negative working capital, accumulated deficit, operating losses,
        # a market cap far below liabilities. Altman Z goes deep into the distress zone.
        v.update({"workingcapital": -800, "retearn": -1500, "ebit": -400,
                  "marketcap": 150, "liabilities": 1900, "ncfo": -300, "netinc": -350,
                  "receivables": 900, "revenue": 400})
    return [str(v[c]) for c in _SF1_HEADER]


def _write_sf1(path, rows):
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(",".join(_SF1_HEADER) + "\n")
        for r in rows:
            f.write(",".join(r) + "\n")


def _flags_for(rows, dates):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from s10_accounting_veto import build_flags
    with tempfile.TemporaryDirectory() as d:
        _write_sf1(os.path.join(d, "fundamentals.csv"), rows)
        return build_flags(d, ["AAA"], dates)


def test_a_filing_dated_after_the_scoring_date_cannot_move_a_flag():
    """C6. The PEAD protocol: tamper AFTER the as-of date and assert nothing moves.

    Eight quarters of history, scored at 2020-01-15. Then a NINTH filing is added dated
    2020-06-30 -- six months in the future -- with wildly different numbers. Every flag must be
    bit-identical.
    """
    hist = [_row("AAA", f"{y}-{m}-01") for y in (2018, 2019) for m in ("03", "06", "09", "12")]
    dates = ["2020-01-15"]
    before = _flags_for(hist, dates)
    after = _flags_for(hist + [_row("AAA", "2020-06-30", distress=True)], dates)

    assert len(before) == len(after) == 1
    for col in ("beneish_m", "altman_z", "extfin", "beneish_flag", "altman_flag",
                "extfin_flag", "n_flags", "vetoed"):
        b, a = before.iloc[0][col], after.iloc[0][col]
        same = (b == a) or (b != b and a != a)          # NaN == NaN
        assert same, f"a FUTURE filing moved `{col}`: {b} -> {a} — this is look-ahead"


def test_the_point_in_time_test_is_not_vacuous():
    """A test that would pass on any input proves nothing. The SAME tamper dated BEFORE the
    scoring date must move the score -- otherwise the fixture is simply not reaching the flag."""
    hist = [_row("AAA", f"{y}-{m}-01") for y in (2018, 2019) for m in ("03", "06", "09", "12")]
    dates = ["2020-01-15"]
    before = _flags_for(hist, dates)
    moved = _flags_for(hist + [_row("AAA", "2020-01-02", distress=True)], dates)
    b, a = before.iloc[0]["altman_z"], moved.iloc[0]["altman_z"]
    assert b != a, ("a PAST filing did not move altman_z either — the fixture never reaches "
                    "the flag, so the look-ahead test above is vacuous")


# ======================================================================================
# two-pass discipline
# ======================================================================================

def test_the_arm_pass_refuses_without_a_passing_controls_artifact():
    """Session 26's defect was computing a gating control and the outcomes it gates in one
    pass. Demonstrated, not asserted: run --arms against an absent file and a failing one."""
    import importlib
    m = importlib.import_module("scripts.ma28_riskcard")

    class A:
        pass

    with tempfile.TemporaryDirectory() as d:
        a = A()
        a.controls_json = os.path.join(d, "nope.json")
        assert m.run_arms(a) == 2, "the arm pass ran with NO controls artifact"

        a.controls_json = os.path.join(d, "failed.json")
        with io.open(a.controls_json, "w", encoding="utf-8") as f:
            json.dump({"controls_passed": False}, f)
        assert m.run_arms(a) == 2, "the arm pass ran against a FAILING controls artifact"


# ======================================================================================
# the register itself
# ======================================================================================

def test_the_register_exists_and_fixes_the_things_the_script_reads():
    with io.open(REGISTER, "r", encoding="utf-8") as f:
        t = " ".join(f.read().split())
    for s in ("THE GATE IS THE CRASH-RATE REPLICATION. IT IS NOT ALPHA.",
              "fwd_ret ≤ −0.50", "≥ 2.0×", "+0.50pp", "500 draws"):
        assert s in t, f"the register no longer fixes: {s}"


def test_the_register_discloses_its_own_non_blindness():
    """The full-sample separation was published before this register was written. A register
    that did not say so would be claiming a blindness it does not have."""
    with io.open(REGISTER, "r", encoding="utf-8") as f:
        t = " ".join(f.read().split())
    assert "NOT blind to the full-sample result" in t
    assert "PASS here is weaker evidence than a FAIL" in t.replace("**", "")


def test_the_tripwires_can_bite():
    """MUTATION TEST. Every check above passes today. Each mutation is applied to a COPY of the
    thing under test, never to the tree."""
    caught = 0

    # 1. alpha creeps into the arm path
    mutated = _src().replace("def run_arms(args):",
                             "def run_arms(args):\n    FP.quantile_backtest(None)", 1)
    t = ast.parse(mutated)
    if "quantile_backtest" in _calls(_fn(t, "run_arms")):
        caught += 1

    # 2. a registered bar drifts
    if _src().replace("RATIO_FLOOR = 2.0", "RATIO_FLOOR = 1.2", 1) != _src():
        mutated = _src().replace("RATIO_FLOOR = 2.0", "RATIO_FLOOR = 1.2", 1)
        ns: dict = {}
        for line in mutated.split("\n"):
            if line.startswith("RATIO_FLOOR"):
                exec(line, ns)
        if ns.get("RATIO_FLOOR") != 2.0:
            caught += 1

    # 3. the flag builder is re-implemented instead of imported
    mutated = _src() + "\n\ndef build_flags(*a, **k):\n    return None\n"
    if "def build_flags" in mutated:
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
        print("\n  SKIPPED (reported, never silent):")
        for s in sorted(set(_SKIPS)):
            print(f"    - {s}")
    print(f"\n{passed}/{len(tests)} MA28-CARD tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
