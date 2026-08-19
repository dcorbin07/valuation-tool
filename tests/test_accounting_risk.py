"""MA28-CARD's disclosure card. The arithmetic is four divisions; the risk is all in the copy.

Six ways this can be wrong while looking right, and each has a test that fails on it:

  * IT COULD QUOTE THE DIFFERENCE. The register's sharpest instruction is ratio-and-both-rates,
    never the percentage-point gap, because the base rate moves four-fold across the halves and
    the gap swings with it. Pinned twice — once against the module's SYNTAX TREE, so no
    subtraction of the two rates can be written at all, and once against the rendered text.
  * A FIGURE COULD DRIFT FROM THE ARTIFACT. Only the four counts per window are pinned; every
    rate and every ratio is derived from them, and the derived values are asserted against the
    published artifact's own figures to the last bit.
  * THE COPY COULD OUTRUN THE MEASUREMENT. The register gated this on the crash rate and
    explicitly NOT on alpha, and the same flag was REJECTED as a portfolio screen. `BANNED` is
    asserted against the RENDERED payload rather than this file, because rendering is where copy
    leaks — and it caught the module's own first draft.
  * "NOT SCORED" COULD RENDER AS "CLEAN". Failing open on a risk card is the worst available
    failure, and here it is not only a principle: the rows with no computable input crashed at
    about twice the base rate.
  * THE DISCLOSURE COULD BECOME A SCREEN. Pinned by asserting `block()` returns the same answer
    whatever the rows are and mutates none of them.
  * IT COULD GO ON SAYING "NOT SCORED" AFTER THAT STOPPED BEING TRUE. The live-input gate is
    measured per request, and the day a lane adds the balance-sheet fields this suite FAILS and
    demands the per-name half rather than letting a stale sentence ship.

Every fixture is synthetic; nothing here touches the network, the store or a real scan.

Run: python tests/test_accounting_risk.py
"""
from __future__ import annotations

import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.web import accounting_risk as AR  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "web", "accounting_risk.py")
APPJS = os.path.join(ROOT, "valuation", "web", "static", "app.js")
FORMULAS = os.path.join(ROOT, "scripts", "s10_accounting_veto.py")

#: The published artifact's own figures, quoted here ONCE so the derivations have something
#: external to be checked against. `data/` is gitignored, so these cannot be re-read from disk in
#: CI — they are transcribed from `data/free_analysis/MA28_CARD.json` and the whole point of the
#: assertions below is that the module does NOT contain a second copy of them.
ARTIFACT = {
    "full_sample": (0.026597370834607153, 0.008742772548252842, 3.0422123745999063),
    "early_half": (0.011674449633088725, 0.0034126936047333455, 3.4208900608295076),
    "late_half": (0.03986135181975736, 0.013594711001612933, 2.9321220447443164),
}


def _src(path=MODULE) -> str:
    return open(path, encoding="utf-8").read()


def _rendered(rows=None) -> str:
    return AR.rendered_text(AR.block(rows if rows is not None else [{"ticker": "AAA"}]))


# ============================ the arithmetic, and what may be said with it ================
def test_every_rate_and_ratio_derives_from_the_counts_and_matches_the_artifact():
    """Counts are pinned; rates and ratios are computed. The artifact says they agree exactly.

    This is what makes "one number, one meaning" checkable here: if a future edit types a rate
    beside its counts, the two copies can drift and this test is what notices.
    """
    for window, (rf, rk, ratio) in ARTIFACT.items():
        got = AR.rates(window)
        assert abs(got["flagged"] - rf) == 0.0, (window, got["flagged"], rf)
        assert abs(got["kept"] - rk) == 0.0, (window, got["kept"], rk)
        assert abs(got["ratio"] - ratio) == 0.0, (window, got["ratio"], ratio)


def test_no_rate_is_typed_anywhere_in_the_module():
    """The three published rates must appear NOWHERE as literals — only the counts.

    Checked against code with docstrings stripped, so the prose may still quote "2.66%" for a
    reader while the arithmetic cannot.
    """
    code = _code_only(MODULE)
    for window, (rf, rk, _) in ARTIFACT.items():
        for lit in ("%.6f" % rf, "%.6f" % rk, repr(rf), repr(rk)):
            assert lit not in code, (window, lit)


def test_the_module_cannot_subtract_the_two_rates():
    """THE REGISTER'S SHARPEST RULE, pinned against the SYNTAX TREE and not by grep.

    The base rate moved 0.34% -> 1.36% between halves, so the pp gap swings 0.86 -> 2.39 while
    the ratio barely moves. A "so many points more likely" card quotes an era average that
    describes neither half. Reading the AST rather than the text means a subtraction cannot hide
    behind a helper name or whitespace, and means a comment ABOUT subtraction does not fire it —
    the comment-versus-code family this project has caught four times.
    """
    tree = ast.parse(_src())
    rate_names = {"flagged", "kept", "rate_flagged", "rate_kept"}
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            names = set()
            for side in (node.left, node.right):
                if isinstance(side, ast.Subscript) and isinstance(side.slice, ast.Constant):
                    names.add(str(side.slice.value))
                elif isinstance(side, ast.Name):
                    names.add(side.id)
                elif isinstance(side, ast.Attribute):
                    names.add(side.attr)
            assert not (names & rate_names), ("a rate difference is computed at line %d"
                                              % node.lineno)


def test_the_ast_subtraction_guard_is_not_vacuous():
    """A guard that would pass on a tree containing the very thing it forbids is worth nothing.

    Positive control: the same walk over a snippet that DOES subtract the rates must fire.
    """
    tree = ast.parse("gap = r['flagged'] - r['kept']\n")
    fired = False
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            names = set()
            for side in (node.left, node.right):
                if isinstance(side, ast.Subscript) and isinstance(side.slice, ast.Constant):
                    names.add(str(side.slice.value))
            if names & {"flagged", "kept"}:
                fired = True
    assert fired, "the walk cannot see a rate subtraction it is supposed to forbid"


def test_the_rendered_card_quotes_the_ratio_and_both_rates():
    """All three, in the text a reader gets. A ratio alone is unreadable; a rate alone is
    uninterpretable; and the pair without the ratio invites the subtraction."""
    t = _rendered()
    r = AR.rates("full_sample")
    assert "%.2f%%" % (100 * r["flagged"]) in t, "the flagged rate is not rendered"
    assert "%.2f%%" % (100 * r["kept"]) in t, "the base rate is not rendered"
    assert "%.2fx" % r["ratio"] in t, "the ratio is not rendered"
    assert "%.2fx" % AR.rates("early_half")["ratio"] in t, "the early half is not rendered"
    assert "%.2fx" % AR.rates("late_half")["ratio"] in t, "the late half is not rendered"


def test_the_headline_names_the_figure_it_quotes_as_a_ratio():
    """The number alone is not enough — the WORD has to be right.

    A mutation that left `_x(ratio)` in place and relabelled it "a gap of 3.04x" passed every
    other assertion here: the figure was present and correct and described as the wrong kind of
    quantity. That sentence is exactly the misreading the register's rule exists to stop.
    """
    h = AR.block([{"ticker": "A"}])["headline"]
    assert "a ratio of" in h, h
    for wrong in ("a gap of", "more likely", "points more"):
        assert wrong not in h, wrong


def test_the_threshold_travels_in_the_same_sentence_as_the_rates():
    """The audit's own error was pairing THESE rates with the -20% threshold, which produces a
    sentence that refutes itself. The headline names the outcome it measured."""
    h = AR.block([{"ticker": "A"}])["headline"]
    assert "more than half their value" in h, h
    assert "next quarter" in h, h


# ============================ coverage, and the "not scored" rule =========================
def test_coverage_is_stated_before_the_result_is_acted_on():
    """The standing coverage rule, on the surface rather than in a handoff."""
    t = _rendered()
    for k in ("beneish", "altman", "extfin"):
        assert "%.1f%%" % (100 * AR.COVERAGE[k]) in t, k
    assert "%.1f%%" % (100 * AR.unscoreable_share()) in t, "the unscoreable share is not shown"


def test_the_unscoreable_share_is_derived_from_the_row_counts():
    """22.0% is 25,079 of 113,945, and the denominator is the two counts added. Typed, the two
    could drift; derived, they cannot."""
    assert AR.panel_rows() == 6542 + 107403
    assert abs(AR.unscoreable_share() - 0.22009741541972003) < 1e-15


def test_not_scored_is_never_clean_and_the_card_says_why_with_a_number():
    """The rule has a measurement behind it: the rows with NO computable input crashed at about
    twice the rate of the rows that were scored and came back unflagged. Absence of a flag is
    not absence of risk, and on the thinnest data it ran the wrong way."""
    assert abs(AR.no_input_vs_base_ratio() - 2.007298882740295) < 1e-12
    t = _rendered()
    assert '"not scored"' in t and '"clean"' in t, "the rule is not stated to a reader"
    assert "%.2fx" % AR.no_input_vs_base_ratio() in t, "the rule ships without its number"


def test_the_prose_only_names_fields_the_formulas_actually_read():
    """`not_scored_note` names five inputs by hand. Every one must be a required input, or the
    card is explaining its own gap with a field nothing reads."""
    note = AR.not_scored_note(10).lower()
    for phrase, field in (("total assets", "assets"), ("total liabilities", "liabilities"),
                          ("working capital", "workingcapital"),
                          ("retained earnings", "retearn")):
        assert phrase in note, phrase
        assert field in AR.REQUIRED_INPUTS, field


# ============================ the live-input gate =========================================
def test_the_required_inputs_are_the_shipped_formulas_own_fields():
    """Pinned against `s10_accounting_veto.py`'s SYNTAX TREE, not retyped from memory.

    That file is the ONE definition of these formulas — `scripts/ma28_riskcard.py` imports it
    rather than keeping a copy — so a change to what Beneish or Altman reads fails this card's
    suite instead of leaving `REQUIRED_INPUTS` describing an older formula.
    """
    tree = ast.parse(open(FORMULAS, encoding="utf-8").read())
    fields = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in ("beneish_m", "altman_z",
                                                               "build_flags"):
            for n in ast.walk(node):
                if isinstance(n, ast.Call):
                    f = n.func
                    if isinstance(f, ast.Attribute) and f.attr == "get":
                        args = n.args[:1]
                    elif isinstance(f, ast.Name) and f.id == "_req":
                        args = n.args[1:]
                    else:
                        continue
                    for a in args:
                        if isinstance(a, ast.Constant) and isinstance(a.value, str):
                            fields.add(a.value)
    fields.discard("_dk")
    assert fields, "the formula source no longer reads its fields where this looked"
    assert fields == set(AR.REQUIRED_INPUTS), (sorted(fields - set(AR.REQUIRED_INPUTS)),
                                               sorted(set(AR.REQUIRED_INPUTS) - fields))


def test_all_three_flags_need_the_one_universal_input():
    """`assets` is required by every one of the three, which is what makes the gate a single
    checkable fact rather than a seventeen-item list to eyeball."""
    assert AR.UNIVERSAL_INPUT in AR.REQUIRED_INPUTS
    src = open(FORMULAS, encoding="utf-8").read()
    for fn in ("def beneish_m", "def altman_z", "def build_flags"):
        body = src[src.index(fn):]
        body = body[:body.index("\ndef ", 1)] if "\ndef " in body[1:] else body
        assert '"assets"' in body or "'assets'" in body, fn


def test_no_live_row_can_be_scored_today_and_the_answer_is_measured():
    """Zero, computed from the live metrics contract rather than asserted in a comment."""
    from valuation.data.models import CompanyData
    from valuation.screener import providers
    row = providers.company_to_metrics(CompanyData(ticker="PROBE"))
    assert not AR.scoreable(row), "a live row now carries every input — see the test below"
    assert AR.UNIVERSAL_INPUT in AR.missing_inputs(row)


def test_the_day_the_inputs_arrive_this_card_owes_a_scorer():
    """THE TRIPWIRE, and it is the point of building the gate rather than hardcoding False.

    Today `names_scored` is 0 on every request and the card says so in words. The day a lane
    adds total assets and the rest to the metrics contract, that sentence becomes false and
    nothing else in the product would notice. This fails then, and the message says what is
    owed: build the per-name half against the ONE formula definition, or drop the sentence.

    `track_meter`'s not-yet-due-versus-due-and-missing distinction, on a product surface.
    """
    from valuation.data.models import CompanyData
    from valuation.screener import providers
    row = providers.company_to_metrics(CompanyData(ticker="PROBE"))
    blk = AR.block([row])
    if blk.get("names_scored"):
        raise AssertionError(
            "live rows now carry the accounting inputs, so `not_scored_note` is FALSE. Build "
            "the per-name half — delegating to scripts/s10_accounting_veto.py, which is the one "
            "definition of these formulas — and remember external financing is a within-date "
            "top-decile rank, so it scores a LIST and never a single name.")
    assert blk["names_scored"] == 0


def test_the_gate_is_live_and_not_a_hardcoded_zero():
    """Positive control for the tripwire: a synthetic row carrying every required input MUST
    come back scoreable. Without this, the two tests above would pass on `return False`."""
    full = {k: 1.0 for k in AR.REQUIRED_INPUTS}
    assert AR.scoreable(full), "the gate cannot see a complete row"
    assert AR.missing_inputs(full) == []
    assert AR.block([full])["names_scored"] == 1


def test_a_present_but_empty_field_counts_as_missing():
    """Coverage is about VALUES, not schema keys. A field that is in the contract and None on
    every name is the failure the coverage rule exists for."""
    full = {k: 1.0 for k in AR.REQUIRED_INPUTS}
    full["assets"] = None
    assert not AR.scoreable(full)
    full["assets"] = float("nan")
    assert not AR.scoreable(full), "NaN is not a value"


# ============================ the copy, against what is rendered ==========================
def test_the_rendered_card_carries_no_banned_wording():
    """Asserted against the RENDERED payload, not this file — `dip_posture`'s design, and V4's
    lesson that a phrase can be assembled at render time from innocent parts.

    It caught the module's own first draft: `why_the_ratio` illustrated the forbidden form by
    quoting it, so the sentence explaining what may not be said was the first thing to fire.
    """
    for rows in ([], [{"ticker": "A"}], [{"ticker": "A"}, {"ticker": "B"}]):
        t = AR.rendered_text(AR.block(rows))
        assert AR.violations(t) == [], (rows, AR.violations(t))


def test_the_banned_check_is_not_vacuous():
    """It must fire on the sentences it exists to stop, or the test above proves nothing."""
    assert AR.violations("these names underperform, so avoid them")
    assert AR.violations("the accounts suggest fraud")
    assert AR.violations("this stock will crash")
    assert AR.violations("about 1.6 percentage points more likely")


def test_the_card_never_claims_a_return_effect():
    """The register gated this on the crash rate and NOT on alpha, and the same flag was
    rejected as a portfolio screen. The scope limit is on the surface, not only in the file."""
    t = _rendered()
    assert "says nothing about returns" in t, "the scope limit is not rendered"
    assert AR.violations(t) == []


def test_the_card_never_accuses_a_company():
    """Beneish is a manipulation index in the literature. A published statistic crossing a
    published threshold is not evidence that a named real company did anything wrong, and this
    is the copy edit most likely to be made by someone trying to sound punchier."""
    t = _rendered().lower()
    assert "not a finding about any company's conduct" in t
    for word in ("fraud", "manipulating earnings", "cooking the books"):
        assert word not in t, word


def test_the_size_control_is_reported_with_its_direction():
    """C4 was registered as the likely killer and passed 5 of 5 with the gradient INVERTED. A
    card that omitted it would be omitting the finding, and a reader's own first objection."""
    t = _rendered()
    assert "%.2fx" % AR.SIZE_QUINTILE_RATIOS[4] in t
    assert "%.2fx" % AR.SIZE_QUINTILE_RATIOS[0] in t
    assert "STRONGEST among the very largest" in t


# ============================ it is a disclosure, not a screen ============================
def test_the_block_does_not_touch_the_rows():
    """Additive by contract. It may read the rows; it may not annotate, reorder or drop one."""
    rows = [{"ticker": "A", "score": 1}, {"ticker": "B", "score": 2}]
    before = [dict(r) for r in rows]
    AR.block(rows)
    assert rows == before, "block() mutated the rows it was given"
    assert [r["ticker"] for r in rows] == ["A", "B"], "block() reordered the rows"


def test_the_figures_do_not_depend_on_the_rows():
    """A disclosure describes a measurement, not the list it sits under. If the numbers moved
    with the rows they would be a statement about the screen, which is not what was measured."""
    a = AR.block([{"ticker": "A"}])
    b = AR.block([{"ticker": "X"}, {"ticker": "Y"}, {"ticker": "Z"}])
    for k in ("headline", "why_the_ratio", "ratio", "rate_flagged", "rate_kept",
              "coverage_note", "size_note"):
        assert a[k] == b[k], k


def test_it_is_fail_soft_and_never_breaks_the_hot_list():
    """It is a note under a public list. Malformed input renders nothing; it does not raise."""
    for bad in (None, [], "not a list", [None, 3, "x"], [{"ticker": "A"}, None]):
        blk = AR.block(bad)
        assert isinstance(blk, dict) and "label" in blk


# ============================ the register gate ===========================================
def test_a_withdrawal_is_exactly_as_sayable_as_the_result():
    """`dip_posture`'s rule about a NULL, applied to a retraction: flipping STATUS must withdraw
    the figures and say so, not fall silent — a surface that quietly stops updating is how a
    retracted number goes on being believed."""
    original = AR.STATUS
    try:
        AR.STATUS = AR.WITHDRAWN
        blk = AR.block([{"ticker": "A"}])
        assert blk["available"] is False
        assert blk["withdrawn_note"], "a withdrawal renders nothing at all"
        assert "headline" not in blk and "ratio" not in blk, "figures survived the withdrawal"
        assert AR.violations(AR.rendered_text(blk)) == []
    finally:
        AR.STATUS = original
    assert AR.block([{"ticker": "A"}])["available"] is True, "the fixture leaked"


# ============================ the renderer ================================================
_CALL_SITE = "d.accounting_risk"


def _render_hot_src() -> str:
    """The body of `renderHot`, so an assertion about the hot list cannot pass on a match
    somewhere else in a 2,000-line file."""
    src = open(APPJS, encoding="utf-8").read()
    i = src.index("function renderHot")
    j = src.index("\nfunction ", i + 1)
    return src[i:j]


#: The line that actually puts the card into the page. READING the block is not RENDERING it,
#: and this constant is the difference.
_EMIT = '<b>${esc(ar.label)}.</b> ${body}'
_EMIT_WITHDRAWN = '<b>${esc(ar.label)}.</b> ${esc(ar.withdrawn_note)}'


def test_the_renderer_reads_the_block_at_all():
    """The failure mode one lane over was a payload served to nobody: `/api/dip` carried
    `dip_risk` for days while `renderDip` never read it."""
    body = _render_hot_src()
    assert _CALL_SITE in body, "renderHot does not read the accounting_risk block"
    assert "ar.headline" in body and "ar.not_scored_note" in body


def test_the_card_actually_reaches_the_page_and_not_just_a_variable():
    """READING IS NOT RENDERING, and this test exists because the first version of this suite
    did not distinguish them — the second time in two sessions.

    Deleting the one `html +=` that emits the card leaves `const ar = d.accounting_risk` and
    `const body = [ar.headline, ...]` standing, so every assertion about the block being read
    still passed while nothing reached a reader. That is precisely the defect `V6B-RENDER`
    shipped a rule about — anchor on the call site, not on a name the declaration also contains
    — and the rule was not sharp enough: `d.accounting_risk` IS the call site of the read, and
    the read is not the render. **Anchor on the thing that puts text into the output.**
    """
    body = _render_hot_src()
    assert _EMIT in body, "the card is computed and never emitted into the page"


def test_the_withdrawal_reaches_the_page_too():
    """A retraction that renders nothing is indistinguishable from a card that was never built,
    and a surface that quietly stops updating is how a withdrawn number goes on being believed.
    Verified by executing the renderer with `STATUS = withdrawn`; pinned here so it stays true."""
    assert _EMIT_WITHDRAWN in _render_hot_src(), "the withdrawal branch renders nothing"


def _strip_js_comments(js: str) -> str:
    """`//` lines and `/* */` blocks removed, so a paraphrase sweep reads CODE.

    IT CAUGHT ITS OWN COMMENT ON THE FIRST RUN. The block comment above the renderer opens
    "MA28-CARD — accounting stress and the risk of a very bad quarter", so the test asserting
    that app.js does not retype served copy failed against a tree that retypes nothing. That is
    the comment-versus-code family this project has now caught four times — `MA5`'s source
    sweep, `MA49(c)`'s fixture, last session's boundary test, and this. **A guard that cannot
    tell code from prose about code is not measuring the tree**, and the fix is always to read
    the tree rather than to soften the guard.
    """
    js = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in js.splitlines())


#: How much contiguous served copy may appear in the renderer. A hand-typed phrase list was the
#: first cut and it was wrong twice over: "ratio of" fired on a PRE-EXISTING sentence about
#: currency mismatch forty lines away, and a typed list only ever covers the copy that existed
#: when it was typed. This window is DERIVED from what the module actually serves, so it covers
#: every sentence added later, and it is long enough that ordinary English overlap cannot trip it.
_COPY_WINDOW = 30


def test_the_renderer_quotes_the_module_and_does_not_paraphrase_it():
    """One copy authority. The JS may lay out; it may not write.

    Derived rather than enumerated: no `_COPY_WINDOW`-character stretch of any served sentence
    may appear in the renderer's code. A paraphrase long enough to matter cannot avoid it, and a
    four-word English fragment cannot trigger it.
    """
    body = _strip_js_comments(_render_hot_src())
    blk = AR.block([{"ticker": "A"}])
    served = [str(blk.get(k) or "") for k in
              ("label", "headline", "why_the_ratio", "what_is_measured", "not_a_return_claim",
               "size_note", "coverage_note", "not_scored_note", "always")]
    for s in served:
        for i in range(0, max(1, len(s) - _COPY_WINDOW)):
            chunk = s[i:i + _COPY_WINDOW]
            assert chunk not in body, ("app.js is retyping served copy: ..." + chunk + "...")


def test_the_comment_stripper_keeps_the_code_it_is_asked_to_search():
    """Over-stripping would make the paraphrase sweep pass on an empty string, which is the
    same vacuity the sweep exists to avoid. It must remove the prose and keep every read."""
    raw = _render_hot_src()
    body = _strip_js_comments(raw)
    assert _CALL_SITE in body and "ar.headline" in body and "ar.coverage_note" in body
    assert "accounting stress" in raw, "the fixture no longer contains the prose it strips"
    assert "cooking the books" not in body, "the comment survived stripping"


def test_the_paraphrase_sweep_is_not_vacuous():
    """Positive control: a renderer that DID retype a served sentence must be caught. Without
    this the sweep could pass because the window is too long or the strip too aggressive."""
    blk = AR.block([{"ticker": "A"}])
    fake = "html += `<div>" + blk["what_is_measured"] + "</div>`;"
    hit = False
    s = blk["what_is_measured"]
    for i in range(0, max(1, len(s) - _COPY_WINDOW)):
        if s[i:i + _COPY_WINDOW] in _strip_js_comments(fake):
            hit = True
            break
    assert hit, "the sweep cannot see copy that was pasted into the renderer verbatim"


def test_the_figures_never_render_without_the_notes_that_scope_them():
    """The headline is the number; `not_scored_note` is the reason it is not about these names.
    A build that rendered one without the other would put a crash statistic directly above a
    list of companies with nothing between them."""
    body = _render_hot_src()
    i, j = body.index("ar.headline"), body.index("ar.not_scored_note")
    assert abs(i - j) < 400, "the headline and the not-scored note are not rendered together"
    for key in ("ar.coverage_note", "ar.not_a_return_claim", "ar.always"):
        assert key in body, key


def test_the_source_scan_is_not_vacuous():
    """`_render_hot_src` must return renderHot's body and not the whole file or an empty one."""
    body = _render_hot_src()
    assert 500 < len(body) < len(open(APPJS, encoding="utf-8").read())
    assert "function renderDip" not in body, "the slice ran past renderHot"


# ============================ bookkeeping =================================================
def _code_only(path: str) -> str:
    """The module with every docstring removed.

    A prose sweep that reads the docstrings fires on the module's own writing ABOUT the thing it
    forbids — which is exactly how `MA5`'s source sweep fired on its own documentation twice.
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(tree))


def test_the_code_only_reduction_is_not_vacuous():
    """It must strip docstrings and keep code, or the literal sweep passes on nothing."""
    code = _code_only(MODULE)
    assert "def headline" in code and "COUNTS" in code
    assert "rendering is where copy leaks" not in code, "docstrings were not stripped"


def test_zero_trials_this_card_measures_no_hypothesis():
    """It renders an already-measured statistic. No threshold is compared, no verdict reached,
    so it charges no trial and equity `N` does not move — the `S25` / `PT-WRITER` precedent."""
    code = _code_only(MODULE)
    for token in ("p_value", "pvalue", "significant", "adopt", "verdict", "threshold_clear"):
        assert token not in code, token


def test_the_provenance_files_exist():
    """The register is cited so a reader can check it exists rather than taking it on trust —
    `dip_posture`'s corrected REGISTER constant, which pointed at a file that never existed."""
    assert os.path.isfile(os.path.join(ROOT, AR.REGISTER)), AR.REGISTER
    assert os.path.isfile(os.path.join(ROOT, AR.SCRIPT)), AR.SCRIPT
    assert os.path.isfile(os.path.join(ROOT, AR.FORMULA_SOURCE)), AR.FORMULA_SOURCE


def test_the_published_thresholds_are_the_formula_sources_own():
    """-1.78, 1.81 and the top decile are Beneish's and Altman's published values and this panel
    fitted none of them — the rare genuine strength here, so it must not silently drift."""
    src = open(FORMULAS, encoding="utf-8").read()
    for const, attr in (("BENEISH_FLAG_ABOVE", AR.BENEISH_FLAG_ABOVE),
                        ("ALTMAN_FLAG_BELOW", AR.ALTMAN_FLAG_BELOW),
                        ("EXTFIN_TOP_DECILE", AR.EXTFIN_TOP_DECILE),
                        ("MIN_FLAGS_TO_VETO", AR.MIN_FLAGS)):
        m = re.search(r"^%s\s*=\s*(-?[0-9.]+)" % const, src, re.M)
        assert m, const
        assert float(m.group(1)) == float(attr), (const, m.group(1), attr)


def test_the_rule_is_two_of_three_and_says_so():
    """The audit's version is 2-of-FOUR including NT late-filing notices, which are not
    buildable from anything this project owns. The measured rule is narrower and a pass on it
    does not license the wider one."""
    assert AR.MIN_FLAGS == 2
    assert "two of three" in _rendered().lower()


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
    print("\n" + str(passed) + "/" + str(len(tests)) + " MA28-CARD disclosure tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
