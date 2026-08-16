"""V6-B's M1 statistic on a per-name row — the fidelity check V6's own register demanded.

The arithmetic here is trivial: look up one of two numbers. Everything worth testing is the
join, and there are four ways it can be wrong while looking right:

  * THE CLASSIFICATION COULD DRIFT FROM M1's. The floors are pinned against the measurement
    SCRIPT rather than retyped, so a register that moved its own boundary breaks this suite
    instead of silently re-pointing a published rate at a population nobody measured. The
    strict/inclusive asymmetry is pinned from both sides, because it is exactly the kind of
    detail a tidying edit removes.
  * A MISSING INPUT COULD BECOME A CLASS. Defaulting is how an absence turns into a confident
    number, and one of the two defaults is the flattering one.
  * THE RATE COULD ESCAPE ITS POPULATION. M1 measured names at least 20% down; the screen's
    control goes to 10%. At the default threshold that gate never fires, which is why it is
    tested at a threshold where it does.
  * THE DISCLOSURE COULD BECOME A SCREEN. Pinned by running the whole screen twice over
    fixtures that differ ONLY in class and asserting the row set and its order are identical.

Every fixture is synthetic; nothing here touches the network, the store or a real valuation.

Run: python tests/test_dip_risk.py
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.web import dip, dip_posture, dip_risk  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ============================== the classification ========================================
def test_the_floors_are_the_measurement_scripts_own_floors():
    """Pinned against source, not retyped. If V6-B's register ever moves a boundary, this
    fails rather than letting a published rate describe a different population."""
    src = open(os.path.join(ROOT, "scripts", "v6_dip_detector.py"), encoding="utf-8").read()
    q = re.search(r"^QUALITY_FLOOR\s*=\s*([0-9.]+)", src, re.M)
    h = re.search(r"^HEALTH_FLOOR\s*=\s*([0-9.]+)", src, re.M)
    assert q and h, "the measurement script no longer declares its floors where this looked"
    assert float(q.group(1)) == dip_risk.QUALITY_FLOOR, (q.group(1), dip_risk.QUALITY_FLOOR)
    assert float(h.group(1)) == dip_risk.HEALTH_FLOOR, (h.group(1), dip_risk.HEALTH_FLOOR)


def test_the_classification_expression_is_still_the_one_this_module_reproduces():
    """The floors matching is not enough — the COMBINATION could have changed (an `or`, a
    different column, a reversed comparison). This pins the expression itself."""
    src = open(os.path.join(ROOT, "scripts", "v6b_dip_survival.py"), encoding="utf-8").read()
    assert '_healthy' in src and 'QUALITY_FLOOR' in src and 'HEALTH_FLOOR' in src
    m = re.search(r'_healthy"\]\s*=\s*(.{0,220})', src, re.S)
    assert m, "v6b_dip_survival.py no longer assigns _healthy where this test looked"
    expr = " ".join(m.group(1).split())
    assert "> QUALITY_FLOOR" in expr, expr        # STRICT on quality
    assert ">= HEALTH_FLOOR" in expr, expr        # INCLUSIVE on health
    assert "&" in expr and "|" not in expr, ("M1's rule is a conjunction; this module would "
                                             "be reproducing the wrong one: " + expr)


def test_the_strict_and_inclusive_boundaries_are_preserved_exactly():
    """Exactly at the quality floor is UNHEALTHY (strict >); exactly at the health floor is
    HEALTHY (inclusive >=). Tidying either into the other moves a published boundary."""
    assert dip_risk.classify(0.0, 80.0) == dip_risk.UNHEALTHY     # q == floor -> excluded
    assert dip_risk.classify(0.0001, 80.0) == dip_risk.HEALTHY
    assert dip_risk.classify(1.0, 50.0) == dip_risk.HEALTHY       # h == floor -> included
    assert dip_risk.classify(1.0, 49.999) == dip_risk.UNHEALTHY


def test_both_clauses_are_required():
    assert dip_risk.classify(2.0, 90.0) == dip_risk.HEALTHY
    assert dip_risk.classify(-2.0, 90.0) == dip_risk.UNHEALTHY
    assert dip_risk.classify(2.0, 10.0) == dip_risk.UNHEALTHY


def test_a_missing_input_is_unclassified_and_never_defaulted_to_either_side():
    for bad in (None, "", "n/a", float("nan")):
        assert dip_risk.classify(bad, 80.0) is None, bad
        assert dip_risk.classify(1.0, bad) is None, bad


def test_an_unclassified_name_carries_no_rate_at_all():
    b = dip_risk.for_name(drawdown=0.35, z_quality=None, health_score=80.0)
    assert b["class"] is None and b["applies"] is False
    assert b["further_fall_rate"] is None and b["peer_rate"] is None and b["label"] is None
    assert b["why_not_code"] == "unclassified" and b["why_not"]


# ============================== the population gates ======================================
def test_a_name_shallower_than_the_measured_depth_gets_a_class_and_no_rate():
    """M1 measured names at least 20% down. The screen's control reaches 10%, so this fires
    for real whenever a reader widens it."""
    b = dip_risk.for_name(drawdown=0.15, z_quality=1.0, health_score=80.0)
    assert b["class"] == dip_risk.HEALTHY, "the class is still knowable and is still reported"
    assert b["applies"] is False and b["further_fall_rate"] is None
    assert b["why_not_code"] == "shallow"
    assert "20%" in b["why_not"], b["why_not"]


def test_the_depth_gate_is_inclusive_at_exactly_the_measured_depth():
    assert dip_risk.for_name(0.20, 1.0, 80.0)["applies"] is True
    assert dip_risk.for_name(0.19999, 1.0, 80.0)["applies"] is False


def test_a_cash_burning_name_is_excluded_because_no_measured_row_was_scored_that_way():
    """`_health_score`'s burner branch took ZERO rows in V6-B's build (its own C4 control), so
    a live burner's health score comes from a branch the rate never saw."""
    b = dip_risk.for_name(0.35, 1.0, 80.0, cash_burning=True)
    assert b["class"] == dip_risk.HEALTHY and b["applies"] is False
    assert b["why_not_code"] == "cash_burning"
    assert dip_risk.for_name(0.35, 1.0, 80.0, cash_burning=False)["applies"] is True
    assert dip_risk.for_name(0.35, 1.0, 80.0, cash_burning=None)["applies"] is True


def test_a_rate_is_never_present_beside_a_does_not_apply_flag():
    """A number gets read; a flag next to it does not. So the number must be absent."""
    for kw in ({"drawdown": 0.05}, {"z_quality": None}, {"cash_burning": True}):
        args = {"drawdown": 0.35, "z_quality": 1.0, "health_score": 80.0}
        args.update(kw)
        b = dip_risk.for_name(**args)
        assert b["applies"] is False
        assert b["further_fall_rate"] is None and b["peer_rate"] is None


# ============================== the numbers ===============================================
def test_the_rates_are_the_artifacts_own_rates():
    """Skips rather than passes when the licensed artifact is absent (it is gitignored, so CI
    has no copy). A skip that announces itself is honest; a silent pass is not."""
    import json
    for base in (ROOT, os.path.join(ROOT, "..", "..", "..")):
        p = os.path.join(base, "data", "free_analysis", "V6B_DIP_SURVIVAL.json")
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))["diagnostics"]["D1_base_rates"]
            assert abs(d["P_further20_healthy"] - dip_risk.RATE["healthy"]) < 1e-9
            assert abs(d["P_further20_unhealthy"] - dip_risk.RATE["unhealthy"]) < 1e-9
            assert d["n_healthy"] == dip_risk.N_ROWS["healthy"]
            assert d["n_unhealthy"] == dip_risk.N_ROWS["unhealthy"]
            return
    print("      (artifact absent - rate pin skipped, floors still pinned against source)")


def test_the_healthy_rate_is_below_both_comparisons_it_is_shown_against():
    assert dip_risk.RATE["healthy"] < dip_risk.RATE["unhealthy"]
    assert dip_risk.RATE["healthy"] < dip_risk.RATE_ALL_DIPS, (
        "the healthy rate must beat the UNCONDITIONED rate too, or the screen is only "
        "beating its own worst half")


def test_the_size_flag_is_one_directional_and_never_says_the_effect_is_stronger():
    big = dip_risk.TOP_QUINTILE_MEDIAN_MCAP
    assert dip_risk.in_weakest_size_tier(big * 2) is True
    assert dip_risk.in_weakest_size_tier(big * 0.5) is None, (
        "below the top quintile's median the tier is UNKNOWN, not 'stronger'")
    assert dip_risk.in_weakest_size_tier(big) is None       # at the median: still unknown
    for bad in (None, "x", 0, -1, float("nan")):
        assert dip_risk.in_weakest_size_tier(bad) is None, bad


# ============================== the copy rule =============================================
def test_both_classes_are_written_out_in_full_and_each_quotes_the_other():
    hl, ul = dip_risk.label_for("healthy"), dip_risk.label_for("unhealthy")
    assert "32.5%" in hl and "43.4%" in hl, hl
    assert "43.4%" in ul and "32.5%" in ul, ul
    assert len(ul) > 60, "the unflattering label must not be a stub"


def test_the_rendered_payload_carries_no_banned_phrasing():
    """Asserted against what is SERVED. `dip_posture`'s DISTRESS family is the live risk here:
    a further-fall statistic sits one paraphrase away from a bankruptcy claim whose own arm is
    VOID on power."""
    rows = [{"dip_risk": dip_risk.for_name(0.35, 1.0, 80.0, market_cap=5e10)},
            {"dip_risk": dip_risk.for_name(0.35, -1.0, 80.0)},
            {"dip_risk": dip_risk.for_name(0.12, 1.0, 80.0)},
            {"dip_risk": dip_risk.for_name(0.35, None, None)},
            {"dip_risk": dip_risk.for_name(0.35, 1.0, 80.0, cash_burning=True)}]
    text = dip_risk.rendered_text(rows, dip_risk.summary(rows))
    assert not dip_risk.violations(text), dip_risk.violations(text)
    assert len(text) > 400, "the sweep must actually have text to sweep"


def test_the_banned_list_is_shared_with_the_posture_module_and_not_copied():
    assert dip_risk.violations("this one will recover") == ["will recover"]
    assert dip_risk.violations("it went bust") == ["went bust"]
    src = open(os.path.join(ROOT, "valuation", "web", "dip_risk.py"), encoding="utf-8").read()
    assert "BANNED = (" not in src, "the banned list is duplicated; one list on this surface"


def test_v3s_rule_travels_with_every_number():
    b = dip_risk.for_name(0.35, 1.0, 80.0)
    assert "not a probability for this one" in b["not_a_probability"].lower()
    assert "of these names" in b["label"], (
        "the label must attribute the rate to a GROUP, not to this company: " + b["label"])
    for banned_name in ("probability", "odds", "risk_score", "chance"):
        assert banned_name not in b, "the field name itself must not read as a per-name odds"


def test_the_method_note_says_the_measured_health_bar_is_lower_than_the_screens():
    """A reader who knows the screen lists at 66/66/66 would otherwise assume the rate's
    'healthy' means the same thing. It does not, and it is the looser of the two.

    It must ALSO not imply the field discriminates: the sweep below measures that a listed name
    can essentially never be unhealthy, so a note promising a listed name 'can land in either
    group' would be technically true at one boundary and misleading everywhere else."""
    note = dip_risk.METHOD_NOTE.lower()
    assert "lower bar" in note and "50" in note, dip_risk.METHOD_NOTE
    assert "already cleared it" in note, dip_risk.METHOD_NOTE
    assert "either group" not in note, (
        "the note implies a discrimination the surface does not have: " + dip_risk.METHOD_NOTE)
    assert "does not show" in note, ("the unhealthy rate must be framed as a comparison "
                                     "baseline: " + dip_risk.METHOD_NOTE)


# ============================== display, not screen =======================================
def _row(t, z_quality, dd_price, mc=1e9):
    """A snapshot row whose measured drawdown is `1 - dd_price`."""
    return {"ticker": t, "name": t, "z_quality": z_quality, "z_growth": 1.0,
            "market_cap": mc, "extra": {"numbers": {"high_prox": -1.0}}}


def _measure(dd, health=80.0, burning=False):
    return lambda r: {"drawdown": dd, "subs": {"quality": 90.0, "health": health,
                                               "growth": 90.0},
                      "cash_burning": burning, "checks": {}}


#: The only `z_quality` at which a LISTED row classifies unhealthy — see the module docstring.
#: Not a curiosity: it is the sole fixture that can exercise the unhealthy branch end to end.
_UNHEALTHY_Z = 0.0


def test_the_class_does_not_decide_membership_or_ordering():
    """The pin that matters most. Two screens differing ONLY in the field that drives the
    class must return the same rows in the same order."""
    healthy = [_row("AAA", 2.0, 0.0), _row("BBB", 2.0, 0.0)]
    unhealthy = [_row("AAA", _UNHEALTHY_Z, 0.0), _row("BBB", _UNHEALTHY_Z, 0.0)]
    a = dip.screen(healthy, min_drawdown=0.20, measure=_measure(0.35))
    b = dip.screen(unhealthy, min_drawdown=0.20, measure=_measure(0.35))
    assert [r["ticker"] for r in a["rows"]] == [r["ticker"] for r in b["rows"]] == \
        ["AAA", "BBB"], (a["rows"], b["rows"])
    assert a["rows"][0]["dip_risk"]["class"] == "healthy"
    assert b["rows"][0]["dip_risk"]["class"] == "unhealthy"
    assert a["n_eligible"] == b["n_eligible"] and a["rejected_health"] == b["rejected_health"]


def test_the_membership_pin_is_not_vacuous():
    """It only means something if the two fixtures really do classify differently, and if the
    screen really would have been capable of dropping one of them."""
    a = dip.screen([_row("AAA", 2.0, 0.0)], min_drawdown=0.20, measure=_measure(0.35))
    b = dip.screen([_row("AAA", _UNHEALTHY_Z, 0.0)], min_drawdown=0.20,
                   measure=_measure(0.35))
    assert a["rows"][0]["dip_risk"]["class"] != b["rows"][0]["dip_risk"]["class"]
    dropped = dip.screen([_row("AAA", 2.0, 0.0)], min_drawdown=0.20,
                         measure=_measure(0.05))
    assert dropped["rows"] == [], "the screen cannot drop anything, so the pin proves nothing"


def test_a_listed_name_can_essentially_never_be_classified_unhealthy():
    """THE STRUCTURAL FINDING, pinned so a loosened gate re-opens the question instead of
    quietly falsifying the module's own docstring.

    The screen's prefilter drops `z_quality < 0` and it lists on `health >= 66`, while M1's
    clauses are `z_quality > 0` and `health >= 50`. So every listed name clears M1's health
    clause with room to spare, and can fail its quality clause only at exactly zero. The field
    is therefore a VERIFICATION that a row is in the measured group, not a discriminator
    between two groups — which is what licenses attaching the rate at all."""
    assert dip.PREFILTER_Z_FLOOR >= dip_risk.QUALITY_FLOOR, (
        "the prefilter no longer implies M1's quality clause; a listed name can now be "
        "unhealthy on quality and the docstring's finding must be re-measured")
    assert dip.HEALTH_FLOORS["health"] >= dip_risk.HEALTH_FLOOR, (
        "the screen's health gate has dropped below M1's floor; a listed name can now be "
        "unhealthy on health")
    assert "z_quality" in dip.PREFILTER_THEMES

    found = []
    for z in (None, -2.0, -0.5, -1e-9, 0.0, 1e-9, 0.5, 2.0):
        for h in (None, 0.0, 49.9, 50.0, 65.9, 66.0, 80.0, 100.0):
            out = dip.screen([_row("T", z, 0.0)], min_drawdown=0.20,
                             measure=_measure(0.35, health=h))
            if out["rows"] and out["rows"][0]["dip_risk"]["class"] == "unhealthy":
                found.append((z, h))
    assert {z for z, _ in found} == {0.0}, (
        "the unhealthy class is reachable somewhere other than exactly zero quality: %r"
        % (found,))
    assert found, "the sweep found no unhealthy cell at all, so it proves nothing"


def test_the_comparison_rate_is_labelled_as_describing_names_the_screen_does_not_show():
    """Because it does. Quoting 43.4% beside every row without that framing invites reading it
    as a label the screen is about to apply to one of them."""
    src = open(os.path.join(ROOT, "valuation", "web", "dip_risk.py"), encoding="utf-8").read()
    assert "comparison baseline describing names this screen does not show" in src


def test_nothing_sorts_or_filters_on_the_risk_field_without_a_register():
    """Same standing condition MA30's tenure disclosure carries. Displaying a measured rate is
    free; ranking or selecting on it is an adoption and needs the both-halves gate."""
    bad = []
    for rel in ("valuation/web/dip.py", "valuation/web/dip_risk.py",
                "valuation/web/app.py", "valuation/saas/notify.py"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        for i, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or not ("dip_risk" in s or "further_fall_rate" in s):
                continue
            for verb in ("sort(", "sorted(", "key=", "filter(", "ORDER BY", "order_by"):
                if verb in s:
                    bad.append(rel + ":" + str(i) + ": " + s)
    assert not bad, ("the risk statistic is being used to order or select names, which is an "
                     "adoption and needs its own register: " + "; ".join(bad))


def test_the_register_sweep_would_catch_a_real_violation():
    line = 'rows = sorted(rows, key=lambda r: r["dip_risk"]["further_fall_rate"])'
    assert "dip_risk" in line and any(v in line for v in ("sorted(", "key="))


def test_the_screen_reports_coverage_for_the_field():
    rows = [_row("AAA", 2.0, 0.0), _row("BBB", _UNHEALTHY_Z, 0.0)]
    out = dip.screen(rows, min_drawdown=0.20, measure=_measure(0.35))
    s = out["dip_risk"]
    assert s["rows"] == 2 and s["classified"] == 2 and s["rate_shown"] == 2
    assert s["healthy"] == 1 and s["unhealthy"] == 1 and s["coverage"] == 1.0
    assert s["register"] == "PREREG_v6b_dip_survival.md"


def test_coverage_names_the_reason_each_row_was_withheld():
    rows = [_row("AAA", 2.0, 0.0), _row("BBB", None, 0.0)]
    out = dip.screen(rows, min_drawdown=0.10, measure=_measure(0.15))
    s = out["dip_risk"]
    assert s["rate_shown"] == 0 and s["withheld_by_reason"].get("shallow") == 1
    assert s["withheld_by_reason"].get("unclassified") == 1, s["withheld_by_reason"]
    assert s["coverage"] == 0.0


def test_an_empty_screen_reports_no_coverage_rather_than_perfect_coverage():
    s = dip.screen([], min_drawdown=0.20, measure=_measure(0.35))["dip_risk"]
    assert s["rows"] == 0 and s["coverage"] is None, (
        "zero rows must not read as 1.0 coverage")


def test_the_posture_paragraph_and_the_per_name_rates_do_not_disagree():
    """Two surfaces quoting one measurement. If either is edited alone they diverge silently,
    and the paragraph is the one a reader trusts."""
    for frag in ("32.5%", "43.4%"):
        assert frag in dip_posture.RISK_HEADLINE, dip_posture.RISK_HEADLINE
    assert "32.5%" == "%.1f%%" % (100 * dip_risk.RATE["healthy"])
    assert "43.4%" == "%.1f%%" % (100 * dip_risk.RATE["unhealthy"])


def test_the_risk_field_is_absent_when_the_risk_register_is_not_positive():
    """Guard against the obvious future edit: if V6-B were ever revised to NULL, the per-name
    rate must not outlive the paragraph that licenses it."""
    assert dip_posture.RISK_STATUS == dip_posture.POSITIVE, (
        "V6-B is no longer POSITIVE; dip_risk must be gated or removed, not left shipping a "
        "rate whose register was withdrawn")
    assert dip_risk.register_is_live() is True


def test_withdrawing_the_register_withdraws_every_rate_at_RUNTIME():
    """Not merely pinned by the test above — enforced in the code, so it survives an edit that
    deletes the test. The withdrawal takes the CLASS with it: 'healthy' rendered beside a
    withdrawn measurement still invites the lookup the withdrawal exists to stop."""
    real = dip_posture.RISK_STATUS
    try:
        dip_posture.RISK_STATUS = dip_posture.NULL
        b = dip_risk.for_name(0.35, 2.0, 90.0, market_cap=9e10)
        assert b["applies"] is False and b["why_not_code"] == "register_withdrawn"
        assert b["class"] is None and b["further_fall_rate"] is None
        assert b["peer_rate"] is None and b["label"] is None
        assert b["weakest_size_tier"] is None
        rows = [{"dip_risk": b}]
        assert dip_risk.summary(rows)["rate_shown"] == 0
    finally:
        dip_posture.RISK_STATUS = real
    assert dip_risk.for_name(0.35, 2.0, 90.0)["applies"] is True, "the fixture did not restore"


def test_the_runtime_gate_is_not_vacuous():
    """It only means something if the same inputs DO produce a rate while the register is
    live — otherwise the test above would pass on a permanently dead field."""
    assert dip_risk.for_name(0.35, 2.0, 90.0)["further_fall_rate"] == dip_risk.RATE["healthy"]


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print("  PASS  " + t.__name__); passed += 1
        except AssertionError as e:
            print("  FAIL  " + t.__name__ + ": " + str(e))
        except Exception as e:
            print("  ERROR " + t.__name__ + ": " + type(e).__name__ + ": " + str(e))
    print("\n" + str(passed) + "/" + str(len(tests)) + " V6-B per-name risk tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
