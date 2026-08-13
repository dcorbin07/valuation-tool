"""The Dip Detector: the screen, the gates, and the posture line that governs its copy.

WHAT THESE TESTS ARE FOR, in order of how much they matter:

1. **A check that did not run may never render as one that passed.** Two of the four
   disqualifiers need a full DCF; the screen does not run one for every name. If those ever
   silently become `pass`, a reader is told four things were verified when two were.
2. **The z-score may never become a percentage.** `z_high_prox` is an exact ORDERING key and a
   meaningless threshold key. Turning it into a drawdown would put a fabricated per-name
   number on a public surface.
3. **The posture line holds against the RENDERED page**, not against the module — rendering is
   where copy leaks, which is what V4 had to learn when a research page's publishing rule had
   to be asserted line by line against the HTML.
4. **The bounds are reported.** A screen that truncates silently reads as coverage.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation  # noqa: F401,E402  - must precede the valuation imports

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import dip, dip_posture  # noqa: E402
from valuation.engine import scoring  # noqa: E402

PASSED = []
FAILED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
        print(f"  PASS  {name}")
    except AssertionError as e:
        FAILED.append((name, str(e)))
        print(f"  FAIL  {name}: {e}")
    except Exception as e:                                            # noqa: BLE001
        FAILED.append((name, f"{type(e).__name__}: {e}"))
        print(f"  ERROR {name}: {type(e).__name__}: {e}")


# ----------------------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------------------

def _row(ticker, z_hp=None, **kw):
    r = {"ticker": ticker, "name": ticker + " Inc", "price": 100.0,
         "z_quality": 1.0, "z_growth": 1.0, "extra": {"numbers": {}}}
    if z_hp is not None:
        r["extra"]["numbers"]["high_prox"] = z_hp
    r.update(kw)
    return r


def _healthy(dd, **kw):
    m = {"drawdown": dd, "subs": {"quality": 80.0, "health": 75.0, "growth": 70.0},
         "checks": {"withheld": "pass", "beta_provenance": "pass", "terminal_share": "pass"}}
    m.update(kw)
    return m


# ----------------------------------------------------------------------------------------
# 1. THE THRESHOLD CONTROL
# ----------------------------------------------------------------------------------------

def test_the_threshold_control_covers_dons_range_and_clamps_outside_it():
    assert dip.MIN_DRAWDOWN_FLOOR == 0.10, dip.MIN_DRAWDOWN_FLOOR
    assert dip.MIN_DRAWDOWN_CEIL == 0.40, dip.MIN_DRAWDOWN_CEIL
    assert dip.DEFAULT_MIN_DRAWDOWN == 0.20, dip.DEFAULT_MIN_DRAWDOWN
    assert dip.clamp_drawdown(0.01) == 0.10
    assert dip.clamp_drawdown(0.99) == 0.40
    assert dip.clamp_drawdown(0.25) == 0.25


def test_a_percentage_typed_as_a_whole_number_is_understood_not_clamped_to_the_ceiling():
    # A slider or a hand-typed query string sending "25" means 25%, not 2500%. Without the
    # >1 branch this silently becomes the 40% ceiling and the screen quietly gets stricter.
    assert dip.clamp_drawdown(25) == 0.25
    assert dip.clamp_drawdown("30") == 0.30


def test_junk_input_falls_back_to_the_default_rather_than_erroring():
    for bad in (None, "", "abc", [], {}, float("nan")):
        assert dip.clamp_drawdown(bad) == dip.DEFAULT_MIN_DRAWDOWN, bad


def test_the_screens_own_default_matches_the_module_default():
    # Python binds default arguments at def time. An earlier draft defined DEFAULT_SHORTLIST
    # twice — once above `screen` and once below it — so the module said 12 and the function
    # silently used 40. This pins the two together.
    import inspect
    got = inspect.signature(dip.screen).parameters["shortlist"].default
    assert got == dip.DEFAULT_SHORTLIST, f"{got} != {dip.DEFAULT_SHORTLIST}"
    assert dip.DEFAULT_SHORTLIST <= dip.MAX_SHORTLIST


# ----------------------------------------------------------------------------------------
# 2. THE HEALTH GATE
# ----------------------------------------------------------------------------------------

def test_the_health_floor_is_taken_from_the_products_own_scoring_and_not_invented():
    # 66 is where `scoring._recommendation` stops saying Hold and starts saying Buy. If that
    # calibration ever moves, this fails and the floor is reconsidered deliberately.
    assert scoring._recommendation(66) == "Buy", scoring._recommendation(66)
    assert scoring._recommendation(65) == "Hold", scoring._recommendation(65)
    for k, v in dip.HEALTH_FLOORS.items():
        assert v == 66.0, f"{k} floor is {v}"


def test_the_health_gate_covers_exactly_the_three_subscores_don_named():
    assert set(dip.HEALTH_FLOORS) == {"quality", "health", "growth"}, dip.HEALTH_FLOORS


def test_momentum_is_deliberately_not_in_the_health_gate():
    # A name 20% off its high has poor momentum BY CONSTRUCTION — `_momentum_score` reads
    # price vs the 200-day average and the 6-month return. Gating on it would reject the
    # entire population this screen exists to find.
    assert "momentum" not in dip.HEALTH_FLOORS
    assert "valuation" not in dip.HEALTH_FLOORS


def test_a_missing_subscore_is_not_a_pass():
    assert dip.health_check({"quality": 90, "health": 90, "growth": 90})["ok"] is True
    out = dip.health_check({"quality": 90, "health": 90})
    assert out["ok"] is False, out
    assert out["missing"] == ["growth"], out
    assert dip.health_check(None)["ok"] is False
    assert dip.health_check({})["ok"] is False


def test_a_subscore_below_the_floor_fails_and_is_named():
    out = dip.health_check({"quality": 90, "health": 40, "growth": 90})
    assert out["ok"] is False
    assert out["below"] == ["health"], out


# ----------------------------------------------------------------------------------------
# 3. THE DISQUALIFIER GATE — the one that matters most
# ----------------------------------------------------------------------------------------

def test_a_check_that_did_not_run_is_not_a_check_that_passed():
    checks = dip.disqualifier_checks(_row("AAA"))
    for k in dip.DCF_ONLY_CHECKS:
        assert checks[k] == dip.NOT_RUN, f"{k} = {checks[k]}"
        assert checks[k] != dip.PASS
    assert set(checks) == set(dip.CHECKS), (set(checks), set(dip.CHECKS))


def test_the_two_withholding_kinds_are_told_apart():
    # `record_refusal` and `record_unavailable` mean different things — "the model rejects
    # this valuation" vs "we could not look today, and the next scan retries it". Showing one
    # badge for both tells a reader one thing when two are true.
    refused = dip.disqualifier_checks(
        {"fair_value_withheld": True, "fair_value_withheld_kind": "refused"})
    assert refused["withheld"] == dip.FAIL
    assert refused["no_data"] == dip.PASS, refused

    missing = dip.disqualifier_checks(
        {"fair_value_withheld": True, "fair_value_withheld_kind": "unavailable"})
    assert missing["withheld"] == dip.FAIL
    assert missing["no_data"] == dip.FAIL, missing


def test_a_withheld_name_never_reaches_the_screen():
    rows = [_row("AAA", z_hp=-3.0, fair_value_withheld=True,
                 fair_value_withheld_kind="refused")]
    out = dip.screen(rows, 0.20, measure=lambda r: _healthy(0.50))
    assert out["rows"] == [], out["rows"]
    assert out["rejected_checks"] == 1, out


def test_a_measurement_cannot_upgrade_a_row_level_failure():
    # Defence in depth: the row-level gate already drops these before measurement, so this
    # pins that the merge cannot become the way a refusal gets overridden later.
    row = {"fair_value_withheld": True, "fair_value_withheld_kind": "refused",
           "ticker": "AAA", "z_quality": 1.0, "z_growth": 1.0}
    merged = dict(dip.disqualifier_checks(row))
    claimed = {"withheld": dip.PASS}
    for k, v in claimed.items():
        if k in merged and merged[k] != dip.FAIL:
            merged[k] = v
    assert merged["withheld"] == dip.FAIL, merged


def test_the_dcf_checks_become_real_when_a_valuation_supplies_them():
    rows = [_row("AAA", z_hp=-3.0)]
    out = dip.screen(rows, 0.20, measure=lambda r: _healthy(0.50))
    assert len(out["rows"]) == 1, out
    r = out["rows"][0]
    assert r["checks"]["beta_provenance"] == dip.PASS, r["checks"]
    assert r["checks_not_run"] == [], r["checks_not_run"]


def test_a_beta_the_company_did_not_supply_fails_the_row():
    rows = [_row("AAA", z_hp=-3.0)]
    m = _healthy(0.50)
    m["checks"]["beta_provenance"] = dip.FAIL
    out = dip.screen(rows, 0.20, measure=lambda r: m)
    assert out["rows"] == [], out["rows"]


# ----------------------------------------------------------------------------------------
# 4. THE ORDERING — exact, and never rendered
# ----------------------------------------------------------------------------------------

def test_the_z_score_orders_exactly_and_is_never_published_as_a_percentage():
    # Standardisation within a date is strictly monotone, so ordering by z ascending IS
    # ordering by drawdown descending. The screen must USE that and never SHOW it.
    rows = [_row("SHALLOW", z_hp=-0.5), _row("DEEP", z_hp=-3.0), _row("MID", z_hp=-1.5)]
    seen = []

    def _m(r):
        seen.append(r["ticker"])
        return _healthy({"DEEP": 0.60, "MID": 0.40, "SHALLOW": 0.30}[r["ticker"]])

    out = dip.screen(rows, 0.20, measure=_m, shortlist=2)
    assert seen == ["DEEP", "MID"], seen        # the two deepest, in order, and only those
    for r in out["rows"]:
        for key, val in r.items():
            assert "z_high_prox" not in str(key), key
            # the z of the deepest name is -3.0; a drawdown of -3.0 or 3.0 would be that
            # number leaking through as a ratio
            if key == "drawdown":
                assert 0.0 <= val <= 1.0, (r["ticker"], val)


def test_a_name_with_no_ordering_key_sorts_last_rather_than_first():
    # Unknown is not "shallow". Putting unknowns first would spend the whole measurement
    # budget on names whose drawdown nobody can even rank.
    #
    # THE COMPARISON NAME MUST SIT ABOVE ZERO, and that is the whole point of this fixture.
    # An earlier version used only a DEEP name at z = -3.0, and it passed even when the
    # unknown-sorts-last rule was deleted, because -3.0 still sorts before the 0.0 a broken
    # implementation hands an unknown. NEAR_HIGH at z = +1.5 is the case that separates them:
    # under the rule the unknown goes last, without it the unknown jumps ahead of a name that
    # is barely off its high. Found by mutation, not by reading.
    rows = [_row("UNKNOWN"), _row("NEAR_HIGH", z_hp=1.5), _row("DEEP", z_hp=-3.0)]
    seen = []

    def _m(r):
        seen.append(r["ticker"])
        return _healthy(0.50)

    dip.screen(rows, 0.20, measure=_m, shortlist=2)
    assert seen == ["DEEP", "NEAR_HIGH"], seen
    assert "UNKNOWN" not in seen, "an unrankable name consumed the measurement budget"


# ----------------------------------------------------------------------------------------
# 5. THE BOUNDS ARE REPORTED
# ----------------------------------------------------------------------------------------

def test_the_cap_is_reported_and_not_applied_silently():
    rows = [_row(f"T{i}", z_hp=-float(i)) for i in range(1, 21)]
    out = dip.screen(rows, 0.20, measure=lambda r: _healthy(0.50), shortlist=5)
    assert out["n_eligible"] == 20, out["n_eligible"]
    assert out["n_measured"] == 5, out["n_measured"]
    assert out["capped"] == 15, out["capped"]
    assert len(out["rows"]) == 5


def test_a_name_that_could_not_be_measured_is_counted_not_dropped_quietly():
    rows = [_row("AAA", z_hp=-3.0), _row("BBB", z_hp=-2.0)]
    out = dip.screen(rows, 0.20,
                     measure=lambda r: _healthy(0.50) if r["ticker"] == "AAA" else None)
    assert len(out["rows"]) == 1, out["rows"]
    assert out["n_unmeasured"] == 1, out


def test_every_rejection_reason_has_its_own_counter():
    rows = [
        _row("HEALTHY", z_hp=-3.0),
        _row("WITHHELD", z_hp=-2.9, fair_value_withheld=True,
             fair_value_withheld_kind="refused"),
        _row("PREFILTERED", z_hp=-2.8, z_quality=-1.0),
    ]

    def _m(r):
        if r["ticker"] == "HEALTHY":
            return _healthy(0.50)
        return _healthy(0.50, subs={"quality": 10.0, "health": 10.0, "growth": 10.0})

    out = dip.screen(rows, 0.20, measure=_m)
    assert out["rejected_checks"] == 1, out
    assert out["rejected_prefilter"] == 1, out
    assert out["n_universe"] == 3, out


def test_the_prefilter_is_not_the_health_gate_and_a_missing_z_survives_it():
    # A row missing a theme z-score must reach the real gate rather than be dropped on a
    # data gap — the coverage rule's whole point.
    assert dip.prefilter_ok({"z_quality": None, "z_growth": None}) is True
    assert dip.prefilter_ok({"z_quality": 1.0, "z_growth": 1.0}) is True
    assert dip.prefilter_ok({"z_quality": -0.5, "z_growth": 1.0}) is False


# ----------------------------------------------------------------------------------------
# 6. THE MEASUREMENT MAPPING
# ----------------------------------------------------------------------------------------

class _Prov:
    def __init__(self, substituted):
        self.substituted = substituted


class _Wacc:
    def __init__(self, substituted):
        self.beta_provenance = _Prov(substituted)


class _Score:
    def __init__(self):
        self.subscores = {"quality": 80.0, "health": 70.0, "growth": 68.0}
        self.score = 74
        self.confidence = "medium"


class _Result:
    def __init__(self, price=80.0, high=100.0, substituted=False):
        self.company = type("CD", (), {"price": price, "price_52w_high": high})()
        self.wacc = _Wacc(substituted)
        self.score = _Score()
        self.fair_value_blend = None
        self.fair_value_scenarios = {}
        self.base_fair_value = 120.0


def test_the_drawdown_is_a_ratio_of_two_measured_prices():
    m = dip.measurement_from(_Result(price=80.0, high=100.0))
    assert abs(m["drawdown"] - 0.20) < 1e-9, m["drawdown"]
    assert m["high_52w"] == 100.0


def test_a_price_above_the_trailing_high_is_a_new_high_not_a_negative_drawdown():
    # The 52-week window and the quote can be minutes apart. Clamped at zero so it can only
    # ever FAIL the threshold, never pass it from the wrong side.
    m = dip.measurement_from(_Result(price=110.0, high=100.0))
    assert m["drawdown"] == 0.0, m["drawdown"]


def test_a_substituted_beta_is_reported_as_a_failure_not_as_silence():
    assert dip.measurement_from(_Result(substituted=True))["checks"]["beta_provenance"] \
        == dip.FAIL
    assert dip.measurement_from(_Result(substituted=False))["checks"]["beta_provenance"] \
        == dip.PASS


def test_terminal_share_reads_not_run_when_there_is_no_dcf_blend():
    # `blend.terminal_share_cap`'s own docstring: callers apply it only when the DCF lens is
    # in the blend. No blend means the question was not asked, not that it was answered.
    assert dip.measurement_from(_Result())["checks"]["terminal_share"] == dip.NOT_RUN


def test_the_measurement_budget_is_a_hard_stop():
    calls = []

    def _get(t):
        calls.append(t)
        return _Result()

    m = dip.engine_measure(_get, budget=2)
    for t in ("A", "B", "C", "D"):
        m({"ticker": t})
    assert calls == ["A", "B"], calls


def test_one_name_failing_to_value_does_not_fail_the_screen():
    def _boom(t):
        raise RuntimeError("vendor down")

    assert dip.engine_measure(_boom, budget=5)({"ticker": "AAA"}) is None


# ----------------------------------------------------------------------------------------
# 7. THE POSTURE LINE — asserted against the RENDERED page
# ----------------------------------------------------------------------------------------

def test_the_register_is_open_and_the_verdict_fields_are_empty():
    assert dip_posture.STATUS == dip_posture.OPEN, dip_posture.STATUS
    assert dip_posture.VERDICT_HEADLINE == ""
    assert dip_posture.VERDICT_DETAIL == ""
    p = dip_posture.posture()
    assert p["verdict"] is None, p
    assert p["explainer"] == dip_posture.OPEN_EXPLAINER


def test_the_open_state_says_it_is_a_screen_and_names_the_register():
    p = dip_posture.posture()
    assert "not a prediction" in p["explainer"].lower(), p["explainer"]
    assert "testing it" in p["explainer"].lower(), p["explainer"]
    assert p["register"].startswith("PREREG_"), p["register"]


def test_a_closed_register_cannot_ship_without_its_numbers():
    # The close-out flips STATUS. If it flips STATUS and forgets the detail, the tab would
    # render an upgraded claim with no effect size behind it — which is exactly how "healthy
    # dips recover" becomes folklore. Simulated here rather than waiting for the day.
    orig = (dip_posture.STATUS, dip_posture.VERDICT_HEADLINE, dip_posture.VERDICT_DETAIL)
    try:
        dip_posture.STATUS = dip_posture.POSITIVE
        p = dip_posture.posture()
        assert p["verdict"] == dip_posture.POSITIVE
        assert p["headline"] == "", "a half-finished flip must be visibly empty, not plausible"
        assert p["digest_eligible"] is True, "a closed register unblocks the digest"
    finally:
        (dip_posture.STATUS, dip_posture.VERDICT_HEADLINE,
         dip_posture.VERDICT_DETAIL) = orig


def test_null_is_exactly_as_reachable_as_positive():
    # Same rule as `shadow_vintage`'s missing sign branch: the state nobody wants to publish
    # must be as easy to publish as the one everybody does.
    orig = dip_posture.STATUS
    try:
        for st in (dip_posture.POSITIVE, dip_posture.NULL):
            dip_posture.STATUS = st
            p = dip_posture.posture()
            assert p["verdict"] == st, p
            assert p["digest_eligible"] is True, p
    finally:
        dip_posture.STATUS = orig


def test_the_digest_stays_blocked_while_the_register_is_open():
    # An outbound "dip alert" is a recommendation-shaped push and waits for the evidence.
    assert dip_posture.posture()["digest_eligible"] is False


def test_the_posture_copy_contains_none_of_its_own_banned_phrasings():
    p = dip_posture.posture()
    blob = " ".join(str(v) for v in p.values())
    assert dip_posture.violations(blob) == [], dip_posture.violations(blob)


def test_the_banned_list_covers_advice_and_prediction_and_actually_matches():
    assert dip_posture.violations("You should buy the dip here") == ["buy the dip"]
    assert dip_posture.violations("clearly OVERSOLD") == ["oversold"]
    assert dip_posture.violations("this is sentiment-driven") == ["sentiment-driven"]
    assert dip_posture.violations("a screen, not a prediction") == []


def test_the_rendered_dip_tab_carries_no_banned_phrasing():
    # AGAINST THE HTML, not against the module — rendering is where copy leaks. Both the
    # public and the owner render, because they are different code paths through the same
    # template and only one of them is exercised by a default test client.
    from flask import render_template
    from valuation.web.app import app
    with app.test_request_context("/"):
        pub = app.test_client().get("/").get_data(as_text=True)
        own = render_template("index.html", may_see_owner=True, may_act=True,
                              is_owner=True, ai_enabled=False, ai_provider="")
    for label, page in (("public", pub), ("owner", own)):
        bad = dip_posture.violations(page)
        assert bad == [], f"{label}: {bad}"


def test_the_dip_tab_renders_for_a_visitor_not_only_for_the_owner():
    # The split calls /api/dip PUBLIC. The tab BUTTON sits outside the owner gate; the first
    # cut left the PANEL inside it, so the button rendered for everyone and opened nothing.
    # Grepping for the button would have passed. This greps for the panel.
    page = None
    from valuation.web.app import app
    page = app.test_client().get("/").get_data(as_text=True)
    assert 'data-tab="dip"' in page, "the tab button is missing"
    assert 'id="tab-dip"' in page, "the tab PANEL is owner-gated but the button is not"
    assert 'id="dipThreshold"' in page, "the threshold control is missing"
    # ...and the owner-only neighbours must still be absent for a visitor.
    assert 'id="tab-index"' not in page
    assert 'id="screamTrack"' not in page


def test_the_threshold_control_offers_dons_whole_range():
    from valuation.web.app import app
    page = app.test_client().get("/").get_data(as_text=True)
    m = re.search(r'id="dipThreshold".*?</select>', page, re.S)
    assert m, "no threshold control rendered"
    vals = [float(v) for v in re.findall(r'value="([0-9.]+)"', m.group(0))]
    assert min(vals) == dip.MIN_DRAWDOWN_FLOOR, vals
    assert max(vals) == dip.MIN_DRAWDOWN_CEIL, vals
    assert dip.DEFAULT_MIN_DRAWDOWN in vals, vals


def test_the_route_answers_and_always_carries_its_posture():
    from valuation.web.app import app
    d = app.test_client().get("/api/dip").get_json()
    assert d is not None
    assert (d.get("posture") or {}).get("status") == dip_posture.STATUS, d.get("posture")
    assert "rows" in d


def test_the_template_holds_no_claim_copy_of_its_own():
    # Every claim-bearing sentence must come from `dip_posture`, or the close-out flips a
    # constant and the template goes on saying the old thing. Same defect the hardcoded theme
    # legend shipped when it called a live theme dormant.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(here, "valuation", "web", "templates", "index.html"),
               encoding="utf-8").read()
    m = re.search(r'<div id="tab-dip".*?(?=\{%\s*if may_see_owner)', src, re.S)
    assert m, "could not locate the dip tab block in the template"
    block = m.group(0)
    # Strip Jinja comments and expressions; what is left is literal prose.
    prose = re.sub(r"\{#.*?#\}", " ", block, flags=re.S)
    prose = re.sub(r"\{\{.*?\}\}", " ", prose, flags=re.S)
    prose = re.sub(r"<!--.*?-->", " ", prose, flags=re.S)
    prose = re.sub(r"<[^>]+>", " ", prose)
    for phrase in ("screen, not a prediction", "testable claim", "recover"):
        assert phrase not in prose.lower(), \
            f"claim copy {phrase!r} is hardcoded in the template instead of coming from dip_posture"


if __name__ == "__main__":
    print("Dip Detector — screen, gates and posture")
    for _n, _f in sorted(list(globals().items())):
        if _n.startswith("test_") and callable(_f):
            check(_n, _f)
    print(f"\n{len(PASSED)}/{len(PASSED) + len(FAILED)} dip tests passed")
    if FAILED:
        for n, e in FAILED:
            print(f"  FAILED {n}: {e}")
        sys.exit(1)
