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
def test_both_classes_are_written_out_in_full_and_neither_quotes_the_other():
    """CHANGED 2026-08-16, and the change is the point rather than a relaxation.

    This test used to require that EACH label quote the other class's rate — the old
    `label_for` rendered "32.5% ... against 43.4% of the unhealthy group". `HANDOFF_v6b_health
    _gap.md` then measured that the live screen does not reproduce M1's comparison at all: its
    prefilter removes the unhealthy side upstream, so a per-row side-by-side "invites reading
    the screen as having done the separating when the prefilter did it upstream" (§6.1).

    So the requirement is INVERTED here and the contrast is pinned at screen level instead, by
    `test_the_contrast_is_stated_once_at_screen_level_and_says_it_cannot_be_made_here`. What is
    NOT relaxed is the rule the old test was really protecting — both classes stay equally
    sayable, in full, neither a stub — because an unhealthy row rendering nothing would make
    the unflattering class read as missing data."""
    hl, ul = dip_risk.label_for("healthy"), dip_risk.label_for("unhealthy")
    assert "32.5%" in hl and "43.4%" not in hl, (
        "the per-name label quotes the peer rate again; that is the comparison the live data "
        "cannot make: " + hl)
    assert "43.4%" in ul and "32.5%" not in ul, ul
    assert len(ul) > 60 and len(hl) > 60, "neither label may be a stub"
    for lbl in (hl, ul):
        assert "measured panel" in lbl, (
            "the rate must carry its own scope; a number and a nearby note get separated the "
            "moment anything is copied or truncated: " + lbl)


def test_the_contrast_is_stated_once_at_screen_level_and_says_it_cannot_be_made_here():
    """The replacement for the per-row comparison, pinned to the handoff's own findings.

    Three things must survive a copy edit: the panel share (so the reader knows the measured
    population really did contain both groups), the statement that this page cannot make the
    comparison, and the attribution of the separating to the screen's own filters rather than
    to the figure."""
    note = dip_risk.SCREEN_CONTRAST_NOTE
    low = note.lower()
    assert "cannot be made on this page" in low, note
    assert "filters remove the unhealthy side" in low, (
        "the mechanism r1 measured — an upstream filter — must be named: " + note)
    assert "the separating was done by those filters upstream" in low, note
    assert "73.2%" in note, "the panel's own unhealthy share must appear: " + note


def test_moving_the_comparison_off_the_rows_did_not_delete_it():
    """CAUGHT BY EXECUTING THE RENDERER, not by reading it — the first cut of this change took
    the peer rate off the row and put it nowhere, so 43.4% appeared on a normal all-healthy
    screen exactly zero times while `METHOD_NOTE` went on promising the unhealthy figure was
    "here so the healthy one has something to be read against".

    A rate with nothing on the other side of it is not interpretable. Both panel rates must
    therefore survive at SCREEN level even though neither may sit on a row."""
    note = dip_risk.SCREEN_CONTRAST_NOTE
    assert "43.4%" in note and "32.5%" in note, (
        "the peer rate is rendered nowhere; METHOD_NOTE promises it and the screen does not "
        "show it: " + note)
    assert "measured panel" in note and "cannot be made on this page" in note.lower()
    # ... and it must still be absent from the row.
    assert "43.4%" not in dip_risk.label_for("healthy")
    assert not dip_risk.violations(note), dip_risk.violations(note)


def test_the_copy_is_pinned_to_the_handoffs_own_findings():
    """V6B-PRODUCT's precedent, applied one surface over: that row pinned its sentence verbatim
    into the edge lane's handoff so a revision there fails this suite rather than drifting.

    The same thing is owed here, because `SCREEN_CONTRAST_NOTE` asserts things this lane did
    NOT measure — the panel's 73.19% split and the single-point reachable set are r1's, read
    out of `HANDOFF_v6b_health_gap.md`. If that pass is ever revised or retracted, the copy
    saying "essentially every name listed here is already in the healthy group" stops being
    supported, and it must break here rather than keep rendering.

    Whitespace is flattened first: the handoff is hard-wrapped, so the phrases straddle
    newlines and a naive substring search would report a false absence."""
    path = os.path.join(ROOT, "HANDOFF_v6b_health_gap.md")
    assert os.path.exists(path), (
        "the handoff this copy rests on is gone; SCREEN_CONTRAST_NOTE now asserts findings "
        "with no record behind them")
    flat = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())

    # The two panel facts the note quotes, and the counts the derived share comes from.
    assert "73.19%" in flat, "r1's panel split is no longer in the handoff"
    for n in ("9,924", "27,090", "37,014"):
        assert n in flat, "the row counts behind unhealthy_share() moved: " + n
    # The mechanism the note names — an upstream filter, not delisting, not a floor difference.
    assert "prefilter removes M1's entire unhealthy side" in flat, flat[:0]
    assert "not a discriminator between two groups on this surface" in flat
    # And §6.1's constraint, which is why the notes render with the rate rather than beside it.
    assert "invites reading the screen as having done the separating" in flat

    # The share this module derives must equal the one the handoff states.
    assert abs(dip_risk.unhealthy_share() - 0.7319) < 0.0002, dip_risk.unhealthy_share()


def test_the_handoff_pin_is_not_vacuous():
    """It must be capable of failing — a flattened-whitespace search that matched anything, or
    a path that silently resolved to an empty string, would pass on nothing."""
    path = os.path.join(ROOT, "HANDOFF_v6b_health_gap.md")
    flat = re.sub(r"\s+", " ", open(path, encoding="utf-8").read())
    assert len(flat) > 3000, len(flat)
    assert "a phrase this handoff certainly does not contain" not in flat


def test_the_method_notes_promise_is_kept_by_what_is_actually_served():
    """`METHOD_NOTE` makes a promise about the unhealthy figure; this asserts the served text
    keeps it, rather than trusting that two constants written apart still agree."""
    assert "does not show" in dip_risk.METHOD_NOTE
    rows = [{"dip_risk": dip_risk.for_name(0.35, 2.0, 90.0)}]      # an all-healthy screen
    text = dip_risk.rendered_text(rows, dip_risk.summary(rows))
    assert "43.4%" in text, (
        "on an all-healthy screen — which r1 measured is every screen — the served text quotes "
        "no unhealthy figure at all, so METHOD_NOTE describes something absent")
    assert "32.5%" in text


def test_the_panel_share_is_derived_from_the_row_counts_and_not_typed():
    """A share and the counts it comes from are two statements of one fact, and this project
    has corrected four stale figures that drifted exactly that way."""
    assert dip_risk.N_ROWS["healthy"] + dip_risk.N_ROWS["unhealthy"] == dip_risk.N_ROWS_ALL
    expected = float(dip_risk.N_ROWS["unhealthy"]) / float(dip_risk.N_ROWS_ALL)
    assert abs(dip_risk.unhealthy_share() - expected) < 1e-12
    assert 0.73 < dip_risk.unhealthy_share() < 0.74, dip_risk.unhealthy_share()
    src = open(os.path.join(ROOT, "valuation", "web", "dip_risk.py"), encoding="utf-8").read()
    assert "73.2" not in src.replace("73.19", ""), (
        "the share is typed somewhere as a literal; it must only ever be derived")


def test_the_size_caveat_rides_only_on_the_rows_it_is_true_of():
    """The effect runs -3.79pp in the largest tier against -14.29pp in the smallest, and the
    live book is megacap-tilted — so on this surface the caveat applies to most of what a
    reader sees. It must not appear on a row whose tier is unknown."""
    big = dip_risk.for_name(0.35, 1.0, 80.0,
                            market_cap=dip_risk.TOP_QUINTILE_MEDIAN_MCAP * 2)
    unknown = dip_risk.for_name(0.35, 1.0, 80.0,
                                market_cap=dip_risk.TOP_QUINTILE_MEDIAN_MCAP * 0.5)
    assert big["weakest_size_tier"] is True and big["size_caveat"], big
    assert unknown["weakest_size_tier"] is None and unknown["size_caveat"] is None, unknown
    assert "-3.79" in big["size_caveat"] and "-14.29" in big["size_caveat"], big["size_caveat"]
    assert not dip_risk.violations(big["size_caveat"])


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


# ============================== it actually reaches a reader ==============================
#
# The gap `HANDOFF_v6b_health_gap.md` §5 found was not a wrong number — it was a correct number
# nobody could see. `rendered_text` existed so the banned-phrasing rule could be asserted
# against what is SERVED, and with no renderer it swept copy no reader received. These tests
# fail if the field goes back to being payload-only, which is the state it was already in once.
def _appjs() -> str:
    return open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
                encoding="utf-8").read()


#: The table cell that WIRES the helper in, as opposed to the line that defines it. Held as a
#: constant because two tests need to anchor on the call site and anchoring on the bare name
#: `_dipRate(r)` silently matches `function _dipRate(r) {` instead — which is how a deleted
#: `<td>` and an ungated notes block both slipped past an earlier cut of this suite.
_CALL_SITE = "${_dipRate(r)}"


def _render_dip_src() -> str:
    """`renderDip` plus its helper — the region a per-row string would have to appear in."""
    src = _appjs()
    start = src.index("function _dipRate(")
    end = src.index("/* ====================== SCREAM-BUY TRACK RECORD")
    return src[start:end]


def test_the_renderer_reads_the_risk_block_at_all():
    """The whole finding routed by the handoff: the field was served and displayed to nobody."""
    src = _appjs()
    assert "dip_risk" in src, (
        "app.js no longer reads dip_risk; the rate is back to being computed on every request "
        "and rendered to no reader, which is the exact state HANDOFF_v6b_health_gap.md found")
    body = _render_dip_src()
    for field in ("further_fall_rate", "why_not", "not_a_probability", "screen_contrast_note",
                  "method_note"):
        assert field in body, "renderDip drops the served `%s`" % field
    # THE CALL SITE, not the definition. `_dipRate(r)` occurs twice — once as
    # `function _dipRate(r) {` and once as the interpolation in the table row — so an assertion
    # on the bare name passes on a helper that is defined and NEVER CALLED. A mutation deleting
    # the `<td>` was missed for exactly that reason; the `${...}` is the wiring.
    assert _CALL_SITE in body, "the per-row cell is not wired into the table"


def test_the_renderer_never_puts_the_peer_rate_on_a_row():
    """The user-facing half of the copy change, enforced where it can actually be violated.

    `peer_rate` is deliberately still in the payload — the digest and any other consumer may
    legitimately want it — so the guard has to sit on the RENDERER, which is the surface where
    the comparison would mislead."""
    body = _render_dip_src()
    assert "peer_rate" not in body, (
        "renderDip renders the peer rate on a row. r1 measured that this screen's prefilter "
        "removes the unhealthy side upstream, so a row-level 'X% against Y%' claims a "
        "separation this page did not do")
    for literal in ("43.4", "32.5", "0.4335", "0.3251"):
        assert literal not in body, (
            "a measured rate is typed into the renderer as a literal (%r); every number here "
            "must come from the payload" % literal)


def test_the_rate_never_renders_without_the_notes_that_scope_it():
    """§6.1: a bare percentage beside a list of names is "the one presentation §3 and §4 do not
    support". Both notes must be emitted by the same branch the rate is, so a copy edit cannot
    keep the number and drop the scope."""
    body = _render_dip_src()
    # From the CALL SITE, not the definition — see `_CALL_SITE`. Anchoring on the bare name put
    # the whole helper inside `tail`, so a generic "applies" search matched `_dipRate`'s own
    # `if (!b.applies)` guard and an ungated notes block was missed.
    tail = body[body.index(_CALL_SITE):]
    assert "screen_contrast_note" in tail and "method_note" in tail, (
        "the notes do not render after the rate; the rate can now appear alone")
    assert "(r.dip_risk || {}).applies" in tail, (
        "the notes are not gated on a rate actually being shown, so they will render on a "
        "screen that has no rate to qualify")


def test_the_renderer_quotes_the_module_and_does_not_paraphrase_it():
    """V3's pinned-copy rule. Every claim-bearing sentence is the server's; app.js does layout.
    Checked by requiring that no substantial phrase of the served copy is retyped there."""
    body = _render_dip_src()
    for sentence in (dip_risk.METHOD_NOTE, dip_risk.SCREEN_CONTRAST_NOTE,
                     dip_risk.NOT_A_PROBABILITY, dip_risk.SIZE_CAVEAT):
        for chunk in re.findall(r"[A-Za-z][A-Za-z ']{24,}", sentence):
            assert chunk.strip() not in body, (
                "app.js retypes served copy (%r); it must render it, not paraphrase or "
                "duplicate it" % chunk.strip()[:48])


def test_the_source_scan_is_not_vacuous():
    """Every test above greps a region; if the region were empty or mislocated they would all
    pass on nothing."""
    body = _render_dip_src()
    assert len(body) > 1500, len(body)
    assert "renderDip" in body and "<table>" in body
    # And the peer-rate guard must be capable of firing.
    assert "peer_rate" in open(os.path.join(ROOT, "valuation", "web", "dip_risk.py"),
                               encoding="utf-8").read(), (
        "peer_rate has left the payload entirely, so the renderer guard proves nothing")


def _code_only(path: str) -> str:
    """A module reduced to CODE — docstrings stripped — so a prose sweep cannot fire on this
    project's own habit of writing about the thing it is asserting the absence of."""
    import ast
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                and body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_zero_trials_this_row_measures_no_hypothesis():
    """A display change. It reads pinned constants, compares nothing against a bar and returns
    no verdict, so it charges no trial and equity `N` is untouched at 224."""
    code = _code_only(os.path.join(ROOT, "valuation", "web", "dip_risk.py"))
    for token in ("research_log", "n_trials", "trial_count", "hlz", "deflated_sharpe"):
        assert token not in code, (
            "this module reaches the trial counter (%r); a display of an already-measured rate "
            "charges no trial" % token)
    assert len(code) > 2000, "the code-only reduction is empty, so the sweep proves nothing"


def test_the_code_only_reduction_is_not_vacuous():
    """It must strip docstrings and keep code, or the sweep above passes on an empty string."""
    code = _code_only(os.path.join(ROOT, "valuation", "web", "dip_risk.py"))
    assert "def label_for" in code and "SCREEN_CONTRAST_NOTE" in code
    assert "rendering is where copy leaks" not in code, "docstrings were not stripped"


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
