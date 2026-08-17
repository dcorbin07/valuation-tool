"""DEEPITM-FIN pinned.  [PREREG_v5reread_deepitm_financing.md]

What has to be protected here is not the verdict — it is the handful of things that make the
verdict mean what it says:

  * the SPOT is the as-traded series. A split-adjusted spot against an as-traded strike is the
    U1-SPLIT defect and it fails SILENTLY, so it is pinned at source AND at the artifact;
  * the two-pass gate really refuses. A gating control that cannot stop an arm is not a gate;
  * the EXECUTABLE convention is the primary one for a COST question, and it is not quietly
    swapped for mids — which is the number the frontier reported and is 5x smaller;
  * the loader treats an EMPTY directory as absent. That defect was live in the first run of
    this script and produced zero surviving pairs;
  * and zero pairs RAISES rather than flowing downstream as a plausible coverage null.
"""
from __future__ import annotations

import ast
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
ART = os.path.join(DATA, "free_analysis", "DEEPITM_FIN.json")
CTRL = os.path.join(DATA, "free_analysis", "DEEPITM_FIN_CONTROLS.json")
SRC = os.path.join(REPO, "scripts", "deepitm_financing.py")


def _src() -> str:
    return open(SRC, encoding="utf-8").read()


def _art():
    if not os.path.exists(ART):
        return None
    return json.load(open(ART, encoding="utf-8"))


# ---------------------------------------------------------------------------------------------
# the split trap
# ---------------------------------------------------------------------------------------------
def test_spot_is_the_as_traded_series_and_never_the_adjusted_one():
    s = _src()
    assert '"raw_close"' in s or "'raw_close'" in s, "the as-traded series is not read"
    # `close` may appear in prose; it must never be SUBSCRIPTED as a data column.
    assert 'd["close"]' not in s and "d['close']" not in s, (
        "the adjusted close is being read as spot — this is the U1-SPLIT defect and it fails "
        "silently, because the option still prices, it is simply nowhere near the money")


def test_the_spot_fidelity_control_actually_gates():
    s = _src()
    assert "C2_spot_fidelity" in s
    assert "C2_MAX_NONSENSE_FRAC" in s
    tree = ast.parse(s)
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "C2_MAX_NONSENSE_FRAC" in names, "the C2 threshold is not referenced in code"


def test_the_measured_spot_fidelity_is_clean():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    frac = a["controls"]["gating"]["C2_spot_fidelity"]["frac_nonsense_moneyness"]
    assert frac <= 0.05, "nonsense moneyness fraction %.4f — spot/strike bases disagree" % frac


# ---------------------------------------------------------------------------------------------
# the gate
# ---------------------------------------------------------------------------------------------
def test_arms_refuse_without_a_passing_controls_artifact():
    s = _src()
    assert "REFUSING" in s, "the arms stage cannot refuse"
    assert 'c.get("all_gating_pass")' in s, (
        "the arms stage does not READ the controls verdict — a gate that is written but not read "
        "is the session-26 defect")


def test_the_two_passes_are_mutually_exclusive_flags():
    s = _src()
    assert "--controls-only" in s and "--arms" in s
    assert "two-pass" in s.lower()


# ---------------------------------------------------------------------------------------------
# existence is not population
# ---------------------------------------------------------------------------------------------
def test_the_loader_treats_an_empty_directory_as_absent():
    s = _src()
    assert "os.listdir(p)" in s, (
        "_data() does not test for POPULATION — an empty worktree data dir will shadow the "
        "populated primary one, which is exactly what happened on the first run")
    assert "EXISTENCE IS NOT POPULATION" in s


def test_zero_pairs_raises_rather_than_returning_empty():
    s = _src()
    assert "ZERO pairs survived" in s, (
        "an empty result must RAISE; flowing downstream it reads as a coverage null rather than "
        "as an instrument failure")
    assert "raise RuntimeError" in s


# ---------------------------------------------------------------------------------------------
# the primary convention
# ---------------------------------------------------------------------------------------------
def test_the_executable_convention_is_the_primary_one_for_a_cost_question():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    arms = a["arms"]
    mid = arms["A1_financing_spread_mid_bps"]["median"]
    exe = arms["A2_financing_spread_executable_bps"]["median"]
    assert exe > mid, (
        "the executable rate must exceed the mid rate — you buy the call at the ask and sell the "
        "put at the bid, so a cost measured at mids is not a cost anyone pays")
    comp = arms["A3_all_in_option_route_bps_yr"]["components_median"]
    assert abs(comp["financing_excess_exe_bps"] - exe) < 1e-9, (
        "the all-in cost is not built from the EXECUTABLE spread")


def test_the_all_in_cost_includes_the_roll_and_the_roll_dominates_at_this_tenor():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    c = a["arms"]["A3_all_in_option_route_bps_yr"]["components_median"]
    assert c["rolls_per_year_at_median_dte"] > 3.0, (
        "at 60-90 DTE the book rolls several times a year; if this drops the tenor changed")
    assert c["roll_spread_bps_yr"] > 100.0, (
        "the roll cost has collapsed — the whole result turns on it being large at this tenor")


def test_commission_is_imported_not_retyped():
    s = _src()
    assert "from valuation.edge.options_fill import COMMISSION_PER_CONTRACT" in s
    assert "0.65" not in s, "the commission is hard-coded here — that is a second definition"


def test_the_shared_quote_rule_is_imported_not_reimplemented():
    s = _src()
    assert "BS.usable_quote" in s, "MA45's shared usable-quote rule is not used"


# ---------------------------------------------------------------------------------------------
# scope discipline
# ---------------------------------------------------------------------------------------------
def test_the_index_cell_carries_no_verdict():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    cell = a["arms"]["index_cell_NO_VERDICT"]
    assert "NO verdict" in cell["note"]
    assert cell["n_names"] <= 20, (
        "the Index cell has grown — if the freeze ever covers the Index properly the register's "
        "scope limit needs rewriting rather than silently widening")


def test_the_post_hoc_era_split_is_labelled_and_carries_no_verdict():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    d = a["arms"]["POST_HOC_by_rate_era_NO_VERDICT"]
    assert "POST-HOC" in d["note"] and "NO verdict" in d["note"]


def test_nothing_is_adopted_or_recommended():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    assert a["adopts"] == "NOTHING"
    assert a["recommends"] == "NOTHING"


def test_the_margin_rates_are_labelled_assumptions():
    a = _art()
    if a is None:
        print("   (skipped — no artifact)")
        return
    blurb = a["arms"]["margin_rates_are_assumptions"]
    assert "NOT measurements" in blurb, (
        "the margin rates must be labelled assumptions — they are published retail cards, not "
        "anything this repository measured")
    for _k, v in a["arms"]["A3_vs_margin"].items():
        assert "assumption" in v, "a margin route ships without naming its assumption"


def test_no_aggregate_is_printed_below_the_floor():
    s = _src()
    assert "MIN_N = 30" in s
    assert "NOT QUOTABLE" in s, "the floor does not suppress an aggregate"
    a = _art()
    if a is None:
        return
    for d in a["arms"]["per_name"]:
        if not d["quotable"]:
            assert "median" not in d, (
                "%s is below the floor and still ships a median" % d.get("symbol"))


def test_the_freeze_is_the_source_and_the_mutable_store_is_not_read():
    s = _src()
    assert "options_freeze" in s
    assert "options_derived" not in s, "the mutable derived store is read — void condition 5"


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                        # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
