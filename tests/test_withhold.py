"""
When the model refuses to value a name, the whole page must refuse (offline, no network).

    python tests/test_withhold.py

THE BUG. KSPI, 2026-08-05, signed out. The headline read "Fair value: Not DCF-valuable,
Upside: n/a" with the guard's reason under it — and then FAIR VALUE & SCENARIOS printed
BEAR $620.31 (+573%) / BASE $1,289.68 (+1299%) / BULL $2,888.33 (+3033%): the exact number
the guard had just withheld, three inches below the notice withholding it, in green.

Six more cards did the same thing (Monte Carlo median and "100% of trials above the price",
the sensitivity grid, the comps implied values, the reverse-DCF verdict, the FCF projection,
and a 93/100 "Strong Buy" gauge). The fix is a rule, not seven patches: nothing computed
from a withheld fair value is published, and the numbers are stripped from the API response
rather than merely not drawn — so "it isn't on the page" is checkable here, offline, instead
of by squinting at a browser.

The fixture below is the REAL KSPI payload shape with the REAL figures that shipped, so a
regression reproduces the actual bug rather than a sanitised version of it.
"""
import json
import os
import re
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import withhold                      # noqa: E402

APP_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "valuation", "web", "static", "app.js")

PRICE = 92.19
REASON = ("Cannot value this name: the model's $1,289.60 is 14.0x the $92.19 price. That gap "
          "is a data problem (currency or share count), not an opportunity, so no fair value "
          "is published.")

#: Every figure that rendered on the live page for KSPI while the headline said the name
#: could not be valued. Each one must be gone after withholding.
LEAKED = [620.2688355663354, 1289.5983215433105, 2888.146436947473,   # scenario cards
          2293.6874204966884, 928.6315450198296, 5839.11241046628,    # raw DCF cone
          2335.725200478383, 872.8932813115293, 6340.114354833571,    # Monte Carlo
          2798.85, 3448.83, 4746.12, 8632.67,                         # sensitivity grid
          326.3166344204799, 360.1179, 292.8437,                      # comps implied
          987.2461624629182]                                          # growth lens


def _payload(valuable=False):
    """The /api/value payload for KSPI, as the engine produced it."""
    return {
        "company": {"ticker": "KSPI", "name": "Kaspi.kz", "price": PRICE,
                    "currency": "USD", "financial_currency": "KZT"},
        "classification": {"regime": "growth", "dcf_reliability": "low"},
        "wacc": {"wacc": 0.0503},
        "assumptions": {"start_growth": 0.3428, "notes": []},
        "scenarios": {
            "bear": {"per_share": 928.6315450198296, "equity_value": 1.7e8, "rows": [{"year": 1, "revenue": 11496.2}]},
            "base": {"per_share": 2293.6874204966884, "equity_value": 4.3e8, "rows": [{"year": 1, "revenue": 11496.2}]},
            "bull": {"per_share": 5839.11241046628, "equity_value": 1.1e9, "rows": [{"year": 1, "revenue": 11496.2}]},
            "bear_price": 928.6315450198296, "base_price": 2293.6874204966884,
            "bull_price": 5839.11241046628},
        "montecarlo": {"trials": 2000, "mean": 2400.1, "median": 2335.725200478383, "std": 900.0,
                       "p5": 700.0, "p10": 872.8932813115293, "p25": 1400.0, "p75": 4000.0,
                       "p90": 6340.114354833571, "p95": 7100.0, "prob_undervalued": 1.0,
                       "price": PRICE, "hist_bins": [400.0, 900.0], "hist_counts": [12, 44]},
        "reverse": {"implied_avg_growth": -0.09795, "base_avg_growth": 0.20205,
                    "growth_verdict": "Market prices in only ~-9.8% avg growth — below our "
                                      "base (20.2%). Expectations look cheap.",
                    "margin_verdict": "…or only a ~20.3% terminal margin vs our 40.3%."},
        "comps": {"subject": {"pe": 7.67998452136027, "ps": 2.046261889466831,
                              "ev_sales": 1.6520418341714658, "ev_ebitda": 5.054346999453748},
                  "benchmark": {"pe": 30, "ev_ebitda": 22, "ps": 6.5, "ev_sales": 6.5},
                  "benchmark_source": "Technology sector benchmark",
                  "implied": {"pe": 360.1179, "ps": 292.8437, "ev_sales": 310.6045,
                              "ev_ebitda": 341.7281},
                  "comps_fair_value": 326.3166344204799},
        "sensitivity": {"wacc_axis": [0.03, 0.04], "growth_axis": [0.02, 0.03],
                        "grid": [[2798.85, 3448.83, 4746.12, 8632.67, None]],
                        "base_wacc": 0.0503, "base_growth": 0.025},
        "score": {"score": 93, "recommendation": "Strong Buy", "confidence": "medium",
                  "subscores": {"valuation": 100.0, "quality": 90.5, "growth": 87.5,
                                "health": 100.0, "momentum": 78.0},
                  "weights": {"valuation": 0.3, "quality": 0.2, "growth": 0.2,
                              "health": 0.15, "momentum": 0.15},
                  "drivers": ["Monte Carlo: 100% of trials value it above the price.",
                              "Comps imply $326.32 (+254%).",
                              "ROIC 24% vs WACC 5% → +19% value-creation spread.",
                              "Forward revenue growth ~34%.",
                              "Net debt/EBITDA -0.5x, positive FCF."]},
        "ai": None,
        "fair_value_blend": {
            "value": None if not valuable else 1289.5983215433105,
            "valuable": valuable, "reason": "" if valuable else REASON,
            "method": "39% DCF · 32% multiples · 28% growth (revenue multiple)",
            "confidence": "low", "value_low": 620.2688355663354, "value_high": 2888.146436947473,
            "lenses": {"dcf": {"value": 2293.7359, "weight": 0.395},
                       "multiples": {"value": 326.3236, "weight": 0.323},
                       "growth": {"value": 987.2462, "weight": 0.282}},
            "notes": []},
        "growth_lens": {"value": 987.2461624629182, "applies": True,
                        "revenue_at_horizon": 19188.6, "exit_multiple": 11.026},
        "fair_value_scenarios": {"method": "39% DCF · 32% multiples · 28% growth",
                                 "bear": 620.2688355663354, "base": 1289.5983215433105,
                                 "bull": 2888.146436947473},
        "base_fair_value": None if not valuable else 1289.5983215433105,
        "dcf_per_share": 2293.6874204966884,
        "upside": None,
        "warnings": [REASON],
        "sources": ["FMP"],
    }


def _numbers(obj, path="", out=None):
    """Every numeric leaf in a structure, with the path it sits at."""
    out = [] if out is None else out
    if isinstance(obj, dict):
        for k, v in obj.items():
            _numbers(v, f"{path}.{k}", out)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            _numbers(v, f"{path}[{i}]", out)
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        out.append((path, float(obj)))
    return out


# --------------------------------------------------------------------------- #
# The rule itself
# --------------------------------------------------------------------------- #
def test_a_valuable_name_is_returned_completely_untouched():
    """The withholding must be invisible on every name that was not refused — otherwise the
    cure is worse than the bug."""
    ok = _payload(valuable=True)
    assert withhold.is_withheld(ok) is False
    out = withhold.withhold_derived_figures(ok)
    assert out is ok, "a publishable name must not be copied, altered or marked"
    assert json.dumps(out, sort_keys=True) == json.dumps(_payload(valuable=True), sort_keys=True)


def test_the_guard_firing_is_what_triggers_withholding():
    """Both halves of the renderer's own test (app.js: `base_fair_value == null &&
    valuable === false`). A missing fair value alone is a data gap, not a refusal."""
    assert withhold.is_withheld(_payload()) is True
    gap = _payload(valuable=True)
    gap["base_fair_value"] = None                      # no blend refusal — just no number
    gap["fair_value_blend"]["value"] = None
    assert withhold.is_withheld(gap) is False
    assert withhold.is_withheld({}) is False
    assert withhold.is_withheld(None) is False


def test_the_scenario_cone_the_bug_was_reported_for_is_gone():
    out = withhold.withhold_derived_figures(_payload())
    fvs = out["fair_value_scenarios"]
    assert fvs["bear"] is None and fvs["base"] is None and fvs["bull"] is None
    assert fvs["withheld"] is True
    # the method label is not a number and stays, so the card can still say what it WOULD
    # have been valued as
    assert "DCF" in fvs["method"]
    for k in ("bear_price", "base_price", "bull_price"):
        assert out["scenarios"][k] is None
    for case in ("bear", "base", "bull"):
        assert out["scenarios"][case]["per_share"] is None
        assert out["scenarios"][case]["rows"] == []
    assert out["dcf_per_share"] is None
    assert out["fair_value_blend"]["value_low"] is None
    assert out["fair_value_blend"]["value_high"] is None
    assert out["fair_value_blend"]["lenses"] == {}
    assert out["growth_lens"] is None


def test_the_same_valuation_in_its_other_costumes_is_gone_too():
    """Monte Carlo, the sensitivity grid and the reverse-DCF read are all the withheld
    number wearing something else. `prob_undervalued` matters most: it is the share of
    trials of the withheld DCF that beat the price, and it printed as "100% of trials value
    it above today's price"."""
    out = withhold.withhold_derived_figures(_payload())
    mc = out["montecarlo"]
    for k in ("mean", "median", "p5", "p10", "p25", "p75", "p90", "p95",
              "prob_undervalued", "hist_bins", "hist_counts"):
        assert mc[k] is None, f"montecarlo.{k} survived"
    assert mc["withheld"] is True and mc["price"] == PRICE   # the price is not our output
    assert out["sensitivity"]["grid"] == []
    assert out["sensitivity"]["withheld"] is True
    assert out["reverse"]["growth_verdict"] is None
    assert out["reverse"]["implied_avg_growth"] is None


def test_comps_keep_the_ratios_and_lose_the_implied_dollars():
    """A multiple is currency-neutral; the per-share value implied by it is not, which is
    how a $92 stock showed a $326 implied value. The distinction is the point of the card."""
    out = withhold.withhold_derived_figures(_payload())
    assert out["comps"]["subject"]["pe"] == 7.67998452136027
    assert out["comps"]["benchmark"]["pe"] == 30
    assert out["comps"]["implied"] == {}
    assert out["comps"]["comps_fair_value"] is None
    assert out["comps"]["withheld"] is True


def test_no_withheld_figure_survives_anywhere_in_the_valuation_blocks():
    """The catch-all. Rather than listing the seven cards known to have leaked, walk every
    number in every valuation block and require it to be plausible against the price — the
    guard's own >5x band. A new card that starts republishing the DCF fails here without
    anyone remembering to add it to a list."""
    out = withhold.withhold_derived_figures(_payload())
    blocks = ("scenarios", "montecarlo", "sensitivity", "comps", "reverse",
              "fair_value_blend", "growth_lens", "fair_value_scenarios", "score")
    counts = (".trials",)          # a trial COUNT is not a value figure
    for b in blocks:
        for path, v in _numbers(out.get(b), b):
            if path.endswith(counts):
                continue
            assert abs(v) <= PRICE * 5, f"{path} = {v} survived on a {PRICE} stock"
    for key in ("base_fair_value", "dcf_per_share", "upside"):
        assert out[key] is None
    # and none of the exact figures that shipped are anywhere in the response body, except
    # the guard's reason, which quotes one on purpose (see below)
    scrubbed = {k: v for k, v in out.items() if k not in ("warnings", "withheld")}
    scrubbed["fair_value_blend"] = {k: v for k, v in out["fair_value_blend"].items()
                                    if k != "reason"}
    body = json.dumps(scrubbed)
    for v in LEAKED:
        assert f"{v}" not in body, f"{v} is still on the wire"
        assert f"{v:,.2f}" not in body


def test_the_reason_keeps_the_number_because_that_is_the_evidence():
    """The one permitted place. "the model's $1,289.60 is 14.0x the $92.19 price" is the
    argument for withholding, not a valuation — deleting it would leave a refusal with no
    stated cause, which is worse."""
    out = withhold.withhold_derived_figures(_payload())
    assert out["fair_value_blend"]["reason"] == REASON
    assert "$1,289.60" in out["withheld"]["reason"]
    assert out["withheld"]["cards"]["scenarios"]
    assert out["withheld"]["score_note"]


# --------------------------------------------------------------------------- #
# The score — the second costume, and the more serious one
# --------------------------------------------------------------------------- #
def test_the_score_is_withheld_and_the_page_is_told_why():
    """MEASURED, not assumed. `compute_score` is called with base_fv=None
    (engine/pipeline.py:280) so the margin-of-safety term does drop — and then
    `_valuation_score` rebuilds the number from `mc.prob_undervalued` (scoring.py:83, weight
    0.30 of the sub-score, = 1.00 on KSPI) and `comps.comps_fair_value` (scoring.py:86,
    weight 0.15). Both are the withheld valuation. The valuation sub-score printed 100.0/100
    on a name the model had just declined to value, and the >5x cap that would have held the
    composite to 50 is written `if base_fv and ...` (scoring.py:228) so it cannot fire once
    the guard has set base_fv to None. Publishing the bad number capped KSPI at 50;
    withholding it let KSPI print 93 "Strong Buy"."""
    out = withhold.withhold_derived_figures(_payload())
    s = out["score"]
    assert s["score"] is None and s["recommendation"] is None
    assert s["subscores"]["valuation"] is None
    # the components with no fair value in them survive — that is the whole reason the score
    # can be withheld without the page going blank
    assert s["subscores"]["quality"] == 90.5 and s["subscores"]["momentum"] == 78.0
    drivers = " ".join(s["drivers"]).lower()
    assert "monte carlo" not in drivers and "comps imply" not in drivers
    assert "roic" in drivers, "drivers with no valuation in them must survive"
    assert "valuation" in out["withheld"]["score_note"].lower()


def test_the_score_note_states_the_defect_rather_than_hiding_it():
    """This lane must not silently redefine what the score means to fix a display problem.
    The wording has to say the composite is not shown and why."""
    note = withhold.SCORE_NOTE.lower()
    assert "not shown" in note
    assert "declined to publish" in note or "withheld" in note
    assert "quality" in note and "momentum" in note


# --------------------------------------------------------------------------- #
# The renderer, checked at the source
# --------------------------------------------------------------------------- #
def _render_body():
    src = open(APP_JS, encoding="utf-8").read()
    i = src.index("function render(d)")
    return src[i:src.index("\nfunction metric(", i)], src


def test_the_renderer_draws_nothing_derived_from_a_withheld_value():
    """The server strips the figures, but the browser is the surface the reader sees, so it
    refuses independently: every call that draws a DCF-derived figure sits in the ELSE branch
    of `notValuable`. Two locks, because this bug was one lock failing."""
    body, _ = _render_body()
    assert "if (notValuable) {" in body and "withheldCards(d);" in body
    guarded = body.index("if (notValuable) {")
    els = body.index("} else {", guarded)
    for call in ("rangebar(", "scenarioCards(", "fcfChart(", "mcChart(", "sensBox(",
                 "reverseBox("):
        at = body.index(call)
        assert at > els, f"{call} is called outside the notValuable else-branch"
        assert body.count(call) == 1, f"{call} is called more than once in render()"


def test_the_stale_chart_path_is_closed():
    """Skipping a chart draw is not enough: Chart.js keeps the previous ticker's canvas, so
    a withheld name would have shown the LAST name's cone. `withheldCards` destroys both."""
    _, src = _render_body()
    i = src.index("function withheldCards(")
    fn = src[i:src.index("\n}", i)]
    assert 'killChart("fcf")' in fn and 'killChart("mc")' in fn
    for el in ("rangebar", "scenarioCards", "mcNote", "sensBox", "reverseBox", "fcfNote"):
        assert el in fn, f"withheldCards leaves #{el} holding whatever was there"


def test_the_refusal_says_why_rather_than_going_blank():
    """A blank card reads as "still loading" or "no data for this one". The reader is owed
    the same sentence the headline gave them, on every card that disappeared."""
    _, src = _render_body()
    assert "function withheldBox(" in src
    assert "Not published for this name." in src
    assert "Not rated." in src, "the gauge must say it is not rated, not just vanish"
    for key in ("scenarios", "montecarlo", "sensitivity", "fcf", "comps", "reverse", "score"):
        assert key in withhold.CARD_REASONS
        # the client carries the same copy as a fallback, so a card cannot render an empty
        # explanation if the server block is ever missing
        assert re.search(rf"\b{key}:\s*\"", src), f"no client fallback reason for {key}"


def test_the_gauge_cannot_print_a_recommendation_on_a_withheld_name():
    _, src = _render_body()
    i = src.index("function gauge(")
    fn = src[i:src.index("\n}", src.index("stroke-dashoffset", i))]
    assert "if (notValuable || s == null) {" in fn
    assert fn.index("if (notValuable") < fn.index("scoreColor(s)"), \
        "the refusal must come before any score styling"


# --------------------------------------------------------------------------- #
# End to end, through the actual route
# --------------------------------------------------------------------------- #
def _stub_result(payload):
    blend = types.SimpleNamespace(valuable=payload["fair_value_blend"]["valuable"],
                                  reason=payload["fair_value_blend"]["reason"])
    return types.SimpleNamespace(to_dict=lambda: payload,
                                 base_fair_value=payload["base_fair_value"],
                                 fair_value_blend=blend, ai=None)


def _client_with_stub(payload):
    from valuation.web import app as webapp
    orig = webapp.value_ticker
    webapp.value_ticker = lambda *a, **k: _stub_result(payload)
    webapp.app.config["TESTING"] = True
    return webapp, orig


def test_the_api_response_itself_carries_no_withheld_figure():
    """The end the reader can actually inspect: view-source and the network tab. Anything
    still in this response is one console line away from being republished."""
    payload = _payload()
    webapp, orig = _client_with_stub(payload)
    try:
        with webapp.app.test_client() as c:
            body = c.post("/api/value", json={"ticker": "KSPI"}).get_data(as_text=True)
    finally:
        webapp.value_ticker = orig
    for v in LEAKED:
        assert str(v) not in body, f"{v} reached the browser"
    assert "1289.5983215433105" not in body
    assert "$1,289.60" in body, "the reason, which quotes it deliberately, must survive"
    compact = re.sub(r"\s+", "", body)
    assert '"score":null' in compact and '"recommendation":null' in compact
    # the misleading data-gap message must not be attached to a deliberate refusal
    assert "Check the ticker symbol" not in body


def test_a_publishable_name_still_gets_its_numbers_through_the_route():
    payload = _payload(valuable=True)
    webapp, orig = _client_with_stub(payload)
    try:
        with webapp.app.test_client() as c:
            body = c.post("/api/value", json={"ticker": "NKE"}).get_data(as_text=True)
    finally:
        webapp.value_ticker = orig
    assert "1289.5983215433105" in body and "2293.6874204966884" in body


# --------------------------------------------------------------------------- #
# The exports — a download is a publication
# --------------------------------------------------------------------------- #
# A REAL withheld result, built offline from a synthetic company through the real pipeline,
# so the guard itself decides — no hand-made "withheld" object that could drift from what
# the engine actually produces. NKE's inputs against a $2.00 price come out at 37.5x, which
# is exactly the shape the guard exists for.
def _withheld_result(mc_trials=300):
    from valuation.config import CONFIG
    from valuation.engine.pipeline import value_from_company
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fixtures import build_nike
    cd = build_nike()
    cd.price = 2.0
    cd.market_cap = 2.0 * cd.shares_diluted
    r = value_from_company(cd, CONFIG, mc_trials=mc_trials)
    assert withhold.is_withheld_result(r), "the fixture stopped tripping the guard"
    return r


def _publishable_result(mc_trials=300):
    from valuation.config import CONFIG
    from valuation.engine.pipeline import value_from_company
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fixtures import build_nike
    r = value_from_company(build_nike(), CONFIG, mc_trials=mc_trials)
    assert not withhold.is_withheld_result(r)
    return r


def _tmp(suffix):
    import tempfile
    f = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    f.close()
    return f.name


#: Numbers a refusal document may legitimately contain: the price itself, a year, and the
#: figure quoted INSIDE the guard's sentence as the evidence for withholding.
def _implausible_numbers(text, price, reason):
    # collapse whitespace first: a PDF wraps the reason across lines, and an un-normalised
    # comparison would "find" the withheld figure it is allowed to quote
    text = re.sub(r"\s+", " ", str(text))
    text = text.replace(re.sub(r"\s+", " ", reason), " ")   # the one permitted quotation
    out = []
    for tok in re.findall(r"-?\d[\d,]*\.?\d*", text):
        try:
            v = float(tok.replace(",", ""))
        except ValueError:
            continue
        if 1900 < v < 2200 and "." not in tok:            # a year, not money
            continue
        if v > price * 5:
            out.append(tok)
    return out


def test_the_pdf_renders_the_refusal_instead_of_erroring():
    """A user asking for a tearsheet of a name the model cannot value should get a tearsheet
    that says so, with the reason. An error would claim the export is broken; the export is
    fine and the valuation is withheld, and those are different claims."""
    r = _withheld_result()
    from valuation.report import pdf as pdf_report
    path = _tmp(".pdf")
    pdf_report.build_pdf(r, path)
    assert os.path.getsize(path) > 800, "no document was produced"

    lines = pdf_report.withheld_pdf_lines(r)
    flat = " ".join(str(t[1] if k == "kv" else t) if k != "kv" else f"{t[0]} {t[1]}"
                    for k, t in lines)
    reason = withhold.refusal_reason(r)
    assert reason in flat, "the document must state the reason"
    for phrase in ("not published", "n/a", "not rated"):
        assert phrase in flat, f"the document never says {phrase!r}"
    assert not _implausible_numbers(flat, r.company.price, reason)

    try:
        from pypdf import PdfReader                       # in requirements.txt for this check
    except ImportError:                                   # pragma: no cover
        print("      (pypdf missing — checked the lines, not the rendered file)")
        return
    text = "\n".join((p.extract_text() or "") for p in PdfReader(path).pages)
    assert reason.split(".")[0] in text.replace("\n", " ")
    assert not _implausible_numbers(text, r.company.price, reason), \
        "a figure derived from the withheld valuation is IN THE RENDERED PDF"
    # No SECTION of the normal tearsheet survives. Matched on its headings and table
    # headers, case-sensitively — the refusal's own prose names the withheld cards in
    # lower case ("the bear/base/bull cases ... the Monte Carlo distribution") on purpose,
    # since telling the reader what is missing is the job of the document.
    for banned in ("Score Breakdown", "Reverse DCF", "vs Price", "Base Fair Value",
                   "Comps fair value", "Scenarios"):
        assert banned not in text, f"the refusal tearsheet still has a {banned} section"


def test_the_workbook_has_no_model_in_it():
    """The harder case. A spreadsheet of scenario rows is exactly the shape that leaks, and
    every cell in the normal workbook is a FORMULA — so blanking a summary cell would leave
    the file recomputing the withheld figure the moment it opened. The refusal workbook is
    not the model with holes in it: the model sheets are never built. Checked cell by cell."""
    r = _withheld_result()
    from valuation.report import excel as excel_report
    from openpyxl import load_workbook
    path = _tmp(".xlsx")
    excel_report.build_workbook(r, path)
    wb = load_workbook(path)          # formulas as written, not cached values
    assert wb.sheetnames == ["Not valued"], f"model sheets were built: {wb.sheetnames}"

    reason = withhold.refusal_reason(r)
    cells, formulas = [], 0
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if c.value is None:
                    continue
                cells.append((f"{ws.title}!{c.coordinate}", c.value))
                if isinstance(c.value, str) and c.value.startswith("="):
                    formulas += 1
    assert formulas == 0, "a refusal workbook must not carry a single live formula"
    assert any(reason in str(v) for _, v in cells), "the reason is not in the workbook"
    for ref, v in cells:
        if isinstance(v, (int, float)):
            assert abs(v) <= r.company.price * 5, f"{ref} = {v} survived"
        else:
            assert not _implausible_numbers(str(v), r.company.price, reason), \
                f"{ref} carries a withheld figure"


def test_a_publishable_name_still_exports_the_whole_model():
    """The refusal must not cost everyone else their workbook."""
    r = _publishable_result()
    from valuation.report import excel as excel_report
    from valuation.report import pdf as pdf_report
    from openpyxl import load_workbook
    xp, pp = _tmp(".xlsx"), _tmp(".pdf")
    excel_report.build_workbook(r, xp)
    pdf_report.build_pdf(r, pp)
    wb = load_workbook(xp)
    assert set(wb.sheetnames) == {"DCF Model", "WACC", "Sensitivity"}
    formulas = sum(1 for ws in wb.worksheets for row in ws.iter_rows() for c in row
                   if isinstance(c.value, str) and c.value.startswith("="))
    assert formulas > 50, "the live model lost its formulas"
    assert os.path.getsize(pp) > 2000


def test_the_export_routes_serve_the_refusal_document():
    """End to end: 200 and a real file, not a 409. The bytes that reach the browser are
    re-opened and walked, because that is the artefact the user actually gets."""
    from valuation.web import app as webapp
    from openpyxl import load_workbook
    r = _withheld_result()
    reason = withhold.refusal_reason(r)
    webapp._LAST["NKE"] = r
    webapp.app.config["TESTING"] = True
    try:
        with webapp.app.test_client() as c:
            pdf = c.get("/api/export/pdf?ticker=NKE")
            assert pdf.status_code == 200, f"pdf returned {pdf.status_code}"
            assert pdf.mimetype == "application/pdf"
            assert pdf.get_data()[:5] == b"%PDF-"

            xls = c.get("/api/export/excel?ticker=NKE")
            assert xls.status_code == 200, f"excel returned {xls.status_code}"
            path = _tmp(".xlsx")
            with open(path, "wb") as fh:
                fh.write(xls.get_data())
            wb = load_workbook(path)
            assert wb.sheetnames == ["Not valued"]
            for ws in wb.worksheets:
                for row in ws.iter_rows():
                    for cell in row:
                        if cell.value is None:
                            continue
                        assert not str(cell.value).startswith("="), "live formula shipped"
                        assert not _implausible_numbers(str(cell.value),
                                                        r.company.price, reason)
    finally:
        webapp._LAST.pop("NKE", None)


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
    print(f"\n{passed}/{len(tests)} withholding tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
