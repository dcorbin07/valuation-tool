"""
ONE SOURCE OF TRUTH FOR THE DERIVED VALUATION SURFACES, AND AN AI LABEL THAT TELLS THE TRUTH.

Measured on valquo.co 2026-09-30, `POST /api/value {"ticker":"KNSL"}`: the regime was
`financial`, `fair_value_blend` used ONE lens (`pb_roe`, weight 1.0) at $291.03 against a
$323.25 price, and `score.drivers` nevertheless carried "Monte Carlo: 100% of trials value it
above the price" -- a statement about the unlevered FCFF model, which carried weight ZERO in
that fair value. That term is worth 0.30 of the valuation subscore, so the name read 73 "Buy"
while trading above its own fair value. The same payload reported the AI source as
`rule-based (no AI key configured) (AI call failed: Expecting value: line 1 column 1 (char 0))`
-- two mutually exclusive claims in one string, on an account where a key IS configured.

These tests pin the five properties that stop both recurring. Every one is asserted on BOTH a
financial and a growth-led fixture, because a gate that only fires on the case it was written
for is not a gate -- and because the non-financial path must come back bit-identical.

Run:  python -m pytest tests/test_valuation_consistency.py
      python tests/test_valuation_consistency.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tests.state_isolation  # noqa: F401  (must precede the valuation imports)

from valuation.config import CONFIG
from valuation.data.models import CompanyData
from valuation.engine.pipeline import lens_applicability, value_from_company
from valuation.engine.scoring import compute_score
from valuation.ai import analyst
from tests.fixtures import build_growth


# --------------------------------------------------------------------------- fixtures
def _financial() -> CompanyData:
    """A KNSL-shaped insurer: the live case, reproduced offline.

    `beta` is set so nothing reaches the network -- a fixture that silently falls back to a
    default beta is measuring the fallback, not the model.
    """
    cd = CompanyData(ticker="KNSL", name="Kinsale Capital Group", sector="Financial Services",
                     industry="Insurance - Property & Casualty", price=323.25,
                     shares_diluted=23.0, market_cap=323.25 * 23.0, beta=0.95)
    cd.revenue = 1_600.0
    cd.net_income = 380.0
    cd.total_equity = 2_000.0
    cd.total_debt = 185.0
    cd.cash = 120.0
    cd.revenue_history = [700.0, 900.0, 1_150.0, 1_400.0, 1_600.0]
    cd.net_income_history = [130.0, 180.0, 250.0, 310.0, 380.0]
    return cd


def _valued(cd):
    return value_from_company(cd, CONFIG)


# --------------------------------------------------------------------------- item 1
def test_lens_applicability_reads_the_weights_the_blend_actually_assigned():
    fin = _valued(_financial())
    grw = _valued(build_growth())

    a_fin = lens_applicability(fin.fair_value_blend)
    a_grw = lens_applicability(grw.fair_value_blend)

    # The financial's blend is the P/B-ROE lens alone, so the FCFF surfaces do not apply.
    assert "pb_roe" in a_fin["used"], a_fin
    assert a_fin["fcff_applies"] is False, a_fin
    assert "DO NOT apply" in a_fin["note"]

    # The growth-led name IS valued on discounted cash flow, so they do.
    assert "dcf" in a_grw["used"], a_grw
    assert a_grw["fcff_applies"] is True, a_grw


def test_an_absent_lens_reads_as_not_applicable_rather_than_unknown():
    """`dcf` missing from the blend must fail CLOSED.

    A gate that treats "no entry for this lens" as "cannot tell" fails open on exactly the case
    it exists for -- a financial's blend does not carry a zero-weight `dcf` entry, it carries no
    `dcf` entry at all.
    """
    class _Blend:
        lenses = {"pb_roe": {"value": 291.03, "weight": 1.0}}

    app = lens_applicability(_Blend())
    assert app["fcff_applies"] is False
    assert app["used"] == ["pb_roe"]

    class _Zero:
        lenses = {"pb_roe": {"value": 1.0, "weight": 1.0}, "dcf": {"value": 2.0, "weight": 0.0}}

    z = lens_applicability(_Zero())
    assert z["fcff_applies"] is False, "a weight of zero is not use"
    assert z["zero_weight"] == ["dcf"]


def test_the_financial_is_scored_on_its_own_distribution_and_the_fcff_one_is_labelled():
    r = _valued(_financial())

    # The scorer's Monte Carlo is the one belonging to the lens that produced the headline.
    assert r.montecarlo is not None
    assert r.montecarlo.model == "justified P/B from ROE"

    # The FCFF surfaces are KEPT -- deleting them would hide that the model ran -- and carry a
    # label saying they may not be used.
    ref = r.reference_only
    assert ref, "the FCFF surfaces were dropped rather than labelled"
    assert "NOT USED FOR THIS COMPANY TYPE" in ref["note"]
    assert "must not enter a score, a verdict or a recommendation" in ref["note"]
    assert ref["montecarlo"] is not None, "the FCFF Monte Carlo should still be visible"

    # And the reverse DCF is not computed at all for this company type.
    assert r.reverse is None
    assert r.to_dict()["reverse"] is None


def test_a_growth_led_name_keeps_the_fcff_surfaces_and_labels_nothing():
    r = _valued(build_growth())
    assert r.reverse is not None, "the reverse DCF applies to a growth-led name"
    assert not r.reference_only, "nothing is reference-only when every lens applies"
    assert not r.financial_surfaces, "P/B-ROE surfaces are not built for a non-financial"


def test_the_monte_carlo_driver_names_its_model():
    """An unattributed probability is what let an inapplicable distribution lift a score."""
    r = _valued(_financial())
    mc_drivers = [d for d in r.score.drivers if "Monte Carlo" in d]
    assert mc_drivers, r.score.drivers
    assert "justified P/B from ROE" in mc_drivers[0], mc_drivers

    # The non-financial path is untouched: the shipped MonteCarloResult carries no `model`, so
    # the driver reads exactly as it always did. This is the inertness half of the change.
    g = _valued(build_growth())
    g_drivers = [d for d in g.score.drivers if "Monte Carlo" in d]
    assert g_drivers, g.score.drivers
    assert g_drivers[0].startswith("Monte Carlo:"), g_drivers


def test_a_weight_zero_distribution_cannot_reach_the_score():
    """The measured consequence, at the live input.

    The live FCFF reading was 100%. Scored with it the composite reaches Hold; scored with the
    distribution belonging to the lens that produced the headline it reads Reduce -- on a name
    trading ABOVE its own fair value. The point is not the exact numbers but that the term can
    move the verdict, which is why an inapplicable one may not supply it.
    """
    cd = _financial()
    r = _valued(cd)
    w = r.wacc.wacc

    class _MC:
        def __init__(self, p):
            self.prob_undervalued = p
            self.model = None

    assert r.base_fair_value < cd.price, "the fixture must be trading above fair value"

    live = compute_score(cd, r.classification, w, base_fv=r.base_fair_value,
                         mc=_MC(1.00), comps=r.comps)
    shipped = r.score
    assert shipped.score < live.score, (shipped.score, live.score)
    assert live.recommendation != shipped.recommendation, (live.recommendation,
                                                           shipped.recommendation)


# --------------------------------------------------------------------------- item 2
def test_the_financial_surfaces_delegate_rather_than_re_deriving_the_multiple():
    """B7: one implementation of the justified-P/B arithmetic.

    `financial_fair_value` caps `g` below both Ke and ROE before applying the multiple and
    bounds the result to [0.2, 6.0]x book. A second copy of that arithmetic would drop the
    capping and produce a distribution the headline cannot reach.

    Delegation is proved by SUBSTITUTION rather than by a numeric identity. A tempting shortcut
    -- "the Monte Carlo's median must equal the point estimate" -- is mathematically false here:
    the justified multiple is non-linear and TWO variables are perturbed, so `median(f(X))` need
    not equal `f(median(X))`. That assertion passed on one fixture by luck and failed on this
    one, which is exactly the kind of check that would later be "fixed" by loosening it.
    """
    from valuation.engine import financials as fin
    cd = _financial()
    r = _valued(cd)
    ke, g = r.wacc.cost_of_equity, r.assumptions.terminal_growth

    point = fin.financial_fair_value(cd, ke, g)

    grid = fin.pb_roe_sensitivity(cd, ke, g)
    assert len(grid["grid"]) == 5 and len(grid["grid"][0]) == 5
    # The centre cell takes zero steps on both axes, so it IS the point estimate -- exactly.
    assert grid["grid"][2][2] == point, (grid["grid"][2][2], point)

    mc = fin.pb_roe_monte_carlo(cd, ke, g, trials=2000)
    assert mc["p10"] < mc["p50"] < mc["p90"]
    assert 0.0 <= mc["prob_undervalued"] <= 1.0

    # SUBSTITUTION: replace the one function and every surface must move with it. If any of the
    # three re-derived `pb * bvps` itself, its output would be unchanged here.
    real = fin.financial_fair_value
    fin.financial_fair_value = lambda *a, **k: 7.0
    try:
        assert fin.pb_roe_sensitivity(cd, ke, g)["grid"][2][2] == 7.0
        sub = fin.pb_roe_monte_carlo(cd, ke, g, trials=50)
        assert sub["p10"] == sub["p50"] == sub["p90"] == 7.0, sub
    finally:
        fin.financial_fair_value = real
    assert fin.financial_fair_value(cd, ke, g) == point, "the module was not restored"

    rev = fin.implied_roe(cd, ke, g)
    assert rev["implied_roe"] is not None
    # Solved, not algebraically inverted: feeding the answer back through the forward model has
    # to reproduce today's price, which a closed-form inverse ignoring the bounds would not.
    back = fin.financial_fair_value(cd, ke, g, roe_override=rev["implied_roe"])
    assert abs(back - cd.price) < 0.01, (back, cd.price)


def test_the_financial_narrative_speaks_book_value_roe_and_cost_of_equity():
    r = _valued(_financial())
    out = analyst._rule_based(r)
    blob = " ".join([out["business_summary"], out["bull_thesis"], out["bear_thesis"],
                     out["overall_take"]] + list(out["assumption_critique"])).lower()

    for term in ("book value", "return on equity", "cost of equity"):
        assert term in blob, "the narrative never mentions %r: %s" % (term, blob[:400])
    assert "price-to-book" in blob or "book" in blob


def test_the_narrative_never_claims_net_cash_or_buyback_capacity_for_a_financial():
    """Deposits, reserves and float are OPERATING liabilities.

    A financial's computed net debt can come back negative while the firm holds no
    distributable cash at all, and buybacks there are gated on regulatory capital this model
    does not read. So the claim is suppressed by regime, not by the sign of net debt.
    """
    cd = _financial()
    # `net_debt` is `total_debt - cash_sti`, NOT `total_debt - cash`; setting the wrong field
    # leaves the fixture looking net-DEBT and the test passing for no reason.
    cd.total_debt, cd.cash_sti = 100.0, 5_000.0
    r = _valued(cd)
    assert cd.net_debt is not None and cd.net_debt < 0, "the fixture must look net-cash"

    out = analyst._rule_based(r)
    blob = " ".join(out["catalysts"] + [out["bull_thesis"], out["bear_thesis"],
                                        out["overall_take"]]).lower()
    assert "buyback" not in blob, out["catalysts"]
    assert "net-cash" not in blob and "net cash" not in blob, out["catalysts"]

    # POSITIVE CONTROL: the same claim IS made for a non-financial with net cash, so the test
    # above is measuring the regime branch and not the absence of the sentence everywhere.
    g = build_growth()
    g.total_debt, g.cash = 0.0, 5_000.0
    gr = _valued(g)
    assert gr.company.net_debt < 0
    gout = analyst._rule_based(gr)
    assert any("buyback" in c.lower() for c in gout["catalysts"]), gout["catalysts"]


def test_the_reverse_dcf_risk_is_not_inherited_where_the_model_does_not_apply():
    """A risk bullet is part of a verdict-shaped narrative."""
    r = _valued(_financial())
    assert r.reverse is None
    out = analyst._rule_based(r)          # must not raise on the absent model
    assert not any("priced for optimism" in x.lower() for x in out["key_risks"])


# --------------------------------------------------------------------------- item 3
def test_comps_are_shown_beside_the_headline_with_their_gap_and_are_not_blended():
    """Whether comps SHOULD be blended for a financial is a measurement question, not this one.

    So the weights are untouched and the figure is published as an independent read. A
    cross-check that has been folded into the thing it checks is not a cross-check.
    """
    r = _valued(_financial())
    cc = r.comps_cross_check
    assert cc, "the comps figure is computed and then discarded"
    assert cc["blended"] is False
    assert cc["comps_fair_value"] and cc["headline_fair_value"]
    expected = (cc["comps_fair_value"] / cc["headline_fair_value"] - 1.0) * 100.0
    assert abs(cc["gap_vs_headline_pct"] - expected) < 1e-9
    assert "cross-check" in cc["note"]

    # The blend itself is unchanged -- no weight was added for comps.
    assert "comps" not in lens_applicability(r.fair_value_blend)["used"]


def test_the_payload_carries_applicability_so_a_consumer_can_tell():
    for cd in (_financial(), build_growth()):
        d = _valued(cd).to_dict()
        assert "lens_applicability" in d
        assert "reference_only" in d
        assert "financial_surfaces" in d
        assert "comps_cross_check" in d
        assert isinstance(d["lens_applicability"]["fcff_applies"], bool)


# --------------------------------------------------------------------------- item 4
def test_an_empty_reply_is_a_named_failure_with_a_reason():
    """`json.loads("")` produced the live message and explained nothing.

    Three conditions yield that identical string -- a budget consumed by thinking, a refusal,
    and prose instead of JSON -- and they want different fixes.
    """
    for text, stop in (("", "max_tokens"), ("   \n\t ", None)):
        try:
            analyst._parse_json(text, "probe", stop_reason=stop, blocks=1)
        except analyst.AIReplyError as e:
            assert "empty" in str(e)
            assert "stop_reason=" in str(e)
        else:
            raise AssertionError("an empty reply parsed")


def test_the_parser_recovers_json_from_fenced_and_prefixed_replies():
    good = [
        '{"moat": "Wide"}',
        '```json\n{"moat": "Wide"}\n```',
        '```\n{"moat": "Wide"}\n```',
        '```json\n{"moat": "Wide"}',                      # fence cut short by max_tokens
        'Here is the analysis:\n{"moat": "Wide"}\nHope that helps.',
        '{"moat": "use `x` here"}',                        # a backtick inside a value survives
    ]
    for text in good:
        out = analyst._parse_json(text, "probe")
        assert out["moat"].startswith(("Wide", "use")), (text, out)
        assert out["source"] == "probe"


def test_prose_and_malformed_json_are_refused_for_DIFFERENT_stated_reasons():
    """The reason has to name the condition, not merely that something went wrong.

    Asserting only the exception TYPE here was too weak, and mutation proved it: with the
    no-JSON-object branch disabled, prose falls through to the decode branch and still raises
    `AIReplyError` -- so the test passed against a tree with the guard removed. The two paths
    diagnose different problems (a model that answered in prose vs one whose JSON was cut off),
    so each is required to say which it found.
    """
    cases = [
        ("I cannot help with that.", "contained no JSON object"),
        ("[1, 2, 3]", "contained no JSON object"),        # no brace at all
        # An object opened and never closed has no closing brace, so it is the NO-OBJECT case,
        # not the decode case -- which is worth pinning, because the obvious guess is the other
        # way round and a truncated reply is the commonest real failure.
        ('{"moat": ', "contained no JSON object"),
        ('{"moat": }', "did not parse"),                   # braces present, contents invalid
        ('{"a":1} {"b":2}', "did not parse"),              # two objects inside one span
    ]
    for text, expected in cases:
        try:
            analyst._parse_json(text, "probe", stop_reason="end_turn")
        except analyst.AIReplyError as e:
            assert expected in str(e), (text, str(e))
            assert "stop_reason=end_turn" in str(e)
        else:
            raise AssertionError("%r parsed" % text)


def test_a_configured_key_that_fails_never_reports_no_key_configured():
    """The live payload made both claims at once; a reader would have hunted a missing env var.

    The failing call is forced through the real `analyze`, so this tests the entry point rather
    than the label helper -- blanking the helper alone must not leave this passing.
    """
    r = _valued(build_growth())

    class _Cfg:
        resolved_ai_provider = "anthropic"
        anthropic_api_key = "sk-ant-notarealkeyatall000000"
        openai_api_key = None
        ai_model_anthropic = "claude-sonnet-5"
        ai_model_openai = "gpt-x"
        montecarlo_trials = 100

    def _boom(prompt, cfg):
        raise analyst.AIReplyError("the reply was empty (stop_reason=max_tokens)")

    real = analyst._call_anthropic
    analyst._call_anthropic = _boom
    try:
        out = analyst.analyze(r, _Cfg())
    finally:
        analyst._call_anthropic = real

    src = out["source"]
    assert "no AI key configured" not in src, src
    assert "AIReplyError" in src, src               # the CLASS, not just the message
    assert "claude-sonnet-5" in src, src            # and which model was tried
    assert "Anthropic" in src, src


def test_the_no_key_label_is_still_used_when_there_is_genuinely_no_key():
    """The default must survive, or the fix has only moved the false statement."""
    r = _valued(build_growth())

    class _Cfg:
        resolved_ai_provider = "anthropic"
        anthropic_api_key = None
        openai_api_key = None
        ai_model_anthropic = "claude-sonnet-5"
        ai_model_openai = "gpt-x"

    assert analyst.analyze(r, _Cfg())["source"] == analyst._NO_KEY


def test_a_financial_whose_call_fails_also_gets_the_failure_label():
    """The financial narrative is a separate return path and must not reintroduce the defect."""
    r = _valued(_financial())
    out = analyst._rule_based(r, "rule-based (Anthropic claude-sonnet-5 call failed: X: y)")
    assert "no AI key configured" not in out["source"], out["source"]
    assert "call failed" in out["source"]


def test_a_key_is_never_carried_into_a_reason_or_a_log():
    key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz"
    assert key not in analyst._safe("auth failed for %s" % key)
    assert "sk-***" in analyst._safe("auth failed for %s" % key)
    # Non-key text is untouched, so the redaction is not simply blanking the reason.
    assert analyst._safe("stop_reason=max_tokens") == "stop_reason=max_tokens"


def test_the_configured_anthropic_model_is_a_live_model_id():
    """`claude-sonnet-5` is current. A stale default would 404 on every call.

    Pinned as a committed literal set rather than a substring rule, so a typo'd or retired id
    fails here instead of at the provider.
    """
    live = {"claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5", "claude-fable-5",
            "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6"}
    assert CONFIG.ai_model_anthropic in live, CONFIG.ai_model_anthropic


def test_the_output_budget_leaves_room_for_adaptive_thinking():
    """1600 was the live defect.

    `max_tokens` caps thinking AND text together, and adaptive thinking is on by default on the
    configured model, so a budget sized for the JSON alone can be spent entirely on reasoning --
    returning a thinking block, no text, and `json.loads("")`.
    """
    assert analyst._MAX_TOKENS >= 4000, analyst._MAX_TOKENS


# --------------------------------------------------------------------------- the live surface
def test_the_page_renders_a_null_surface_instead_of_throwing():
    """A page-level crash caused by a correctness fix two layers away.

    `montecarlo` and `reverse` are now `null` for a financial. `mcChart(null)` read
    `mc.hist_bins` and `reverseBox(null)` read `rv.growth_verdict` on the first line of each, so
    either would have thrown a TypeError and taken the WHOLE valuation page down for every bank
    and insurer. The guard must come BEFORE the first dereference, which is what is checked --
    asserting merely that the guard exists somewhere would pass with it placed after.
    """
    js = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "valuation", "web", "static", "app.js")
    with open(js, encoding="utf-8") as fh:
        src = fh.read()

    for fn, guard, deref in (("function mcChart(", "if (!mc)", "mc.hist_bins"),
                             ("function reverseBox(", "if (!rv)", "rv.growth_verdict")):
        start = src.index(fn)
        body = src[start:start + 3000]
        # Non-vacuity: both markers must be present, or the ordering check compares nothing.
        assert guard in body, "%s lost its null guard" % fn
        assert deref in body, "%s no longer dereferences; re-point this test" % fn
        assert body.index(guard) < body.index(deref), \
            "%s dereferences before guarding" % fn

    # And the call site has to hand over the financial's own surfaces, or the guard can only ever
    # render "not applied" and the replacement distribution is unreachable.
    assert "mcChart(d.montecarlo, d.financial_surfaces)" in src
    assert "reverseBox(d.reverse, d.financial_surfaces)" in src


if __name__ == "__main__":
    import traceback

    fails = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("  ok   %s" % name)
            except Exception:
                fails += 1
                print("  FAIL %s" % name)
                traceback.print_exc()
    print("\n%s" % ("all passed" if not fails else "%d failed" % fails))
    sys.exit(1 if fails else 0)
