"""MA29 — the refusal count, and the four things the audit's own sentence got wrong.

The arithmetic is trivial: read three integers the scan already computed. Everything worth
testing is a CONSTRAINT, and each one is the kind that rots silently:

  * THE CLAIM IT MUST NOT MAKE. A refusal is about the MODEL, not the company. `BANNED` is
    asserted against the RENDERED payload rather than the source, because a phrase can be
    assembled at render time out of parts that are each innocent (`dip_posture.py`'s design,
    carried forward as `tenure.py` did for MA30).
  * THE TWO KINDS STAY APART. `refused` and `unavailable` are different claims and
    `engine/publication.py` exists partly to keep them apart; a surface that collapses them
    reports a feed outage as a verdict on companies.
  * THE DENOMINATOR IS "ASKED", NOT "SCORED". Production asks the top 500 of ~795 scored, so
    the audit's "N of M names it scored" understates the rate by 1.6x.
  * NO SECOND COUNT. Every figure is read from `publication_audit`; recounting from rows would
    be a second definition of "refused", free to drift from the first.

The live figures pinned below were measured against the PUBLIC payload on 2026-08-15 (scan of
2026-08-14): 800 universe, 795 scored, 500 asked, 2 refused, 0 unavailable.

Run: python tests/test_refusals.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede the valuation imports)

from valuation.web import refusals  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The shape `screen.publication_audit` emits, with the live 2026-08-14 numbers.
LIVE_AUDIT = {"band": 5.0, "rows_checked": 500, "withheld_refused": 2, "withheld_no_data": 0,
              "asked_but_silent_count": 0, "band_breach_count": 0, "unverified_count": 0}

_FAILED = []


def check(name, cond, detail=""):
    if cond:
        print("  ok   %s" % name)
    else:
        print("  FAIL %s %s" % (name, detail))
        _FAILED.append(name)


# ---------------------------------------------------------------- the copy rule
def test_the_wording_is_pinned_verbatim():
    """`V3`/`score_confidence.py`: one module owns the copy and a test pins it.

    Reworded copy is how a disclosure quietly becomes a recommendation, so this fails on any
    edit and the editor has to come and change the pin deliberately.
    """
    check("label pinned", refusals.LABEL == "Names the model would not value", refusals.LABEL)
    check("explainer states it is about the MODEL",
          "statement about the MODEL, not" in refusals.EXPLAINER)
    check("explainer says the ranking does not use it",
          "The ranking does not use a fair value" in refusals.EXPLAINER)


def test_the_banned_check_runs_against_the_rendered_payload_not_the_source():
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14", displayed=500, display_withheld=0)
    text = refusals.rendered_text(blk)
    check("rendered text is non-empty", len(text) > 200, repr(text[:60]))
    check("no banned phrase in the rendered payload", refusals.violations(text) == [],
          refusals.violations(text))
    # every user-visible string is actually in the rendered text
    for key in ("label", "explainer", "sentence"):
        check("rendered_text includes %s" % key, str(blk[key]) in text)


def test_the_banned_check_is_not_vacuous():
    """A guard no input can trip is indistinguishable from its own absence."""
    bad = dict(refusals.block(LIVE_AUDIT), sentence="These names are overvalued — avoid these.")
    v = refusals.violations(refusals.rendered_text(bad))
    check("a bad sentence trips the guard", "overvalued" in v and "avoid these" in v, v)
    check("every banned phrase is detectable",
          all(refusals.violations("... %s ..." % p) == [p] or p in refusals.violations(
              "... %s ..." % p) for p in refusals.BANNED))


def test_it_makes_no_claim_about_returns_or_the_company():
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14")
    text = refusals.rendered_text(blk).lower()
    for word in ("outperform", "underperform", "return", "beat the market", "risky"):
        check("no '%s' in the copy" % word, word not in text)


# ------------------------------------------------- the two kinds stay apart
def test_the_two_kinds_are_never_collapsed():
    """`publication.py`: collapsing them makes a transient feed problem read as a verdict."""
    audit = dict(LIVE_AUDIT, withheld_refused=0, withheld_no_data=7)
    blk = refusals.block(audit, scan_date="2026-08-14")
    check("refused reported as 0", blk["refused"] == 0, blk["refused"])
    check("unavailable reported as 7", blk["unavailable"] == 7, blk["unavailable"])
    check("the refusal sentence says none were declined",
          "declined none of them" in blk["sentence"], blk["sentence"])
    check("the unavailable sentence is separate and present",
          blk["unavailable_sentence"] and "could not be fetched" in blk["unavailable_sentence"])
    check("the unavailable sentence calls it temporary",
          "temporary" in blk["unavailable_sentence"])
    check("the unavailable names are NOT described as refused",
          "declined to publish" not in (blk["unavailable_sentence"] or ""))


def test_no_unavailable_means_no_unavailable_sentence():
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14")
    check("zero unavailable draws no sentence", blk["unavailable_sentence"] is None)
    check("but the zero is still reported", blk["unavailable"] == 0)


# ------------------------------------------------------------- the denominator
def test_the_denominator_is_asked_not_scored():
    """The audit says "N of M names it scored"; only `rows_checked` were ASKED.

    On the live scan that is 500 against 795 scored — quoting 795 understates the refusal rate
    by a factor of 1.59. Nothing in this block may carry the scored figure.
    """
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14")
    check("asked is rows_checked", blk["asked"] == 500, blk["asked"])
    check("the sentence quotes 500", "500" in blk["sentence"], blk["sentence"])
    check("the sentence never quotes the scored figure", "795" not in blk["sentence"])
    check("the sentence says 'asked'", "asked to value" in blk["sentence"])


def test_it_reads_the_audit_and_never_recounts():
    """Given an audit block, the answer is the audit's — there is no second count to drift."""
    weird = dict(LIVE_AUDIT, withheld_refused=41, rows_checked=123)
    blk = refusals.block(weird, scan_date="2026-08-14")
    check("refused taken from the audit", blk["refused"] == 41, blk["refused"])
    check("asked taken from the audit", blk["asked"] == 123, blk["asked"])


def test_the_band_comes_from_the_scan_not_a_literal():
    blk = refusals.block(dict(LIVE_AUDIT, band=7.0), scan_date="2026-08-14")
    check("band echoed", blk["band"] == 7.0, blk["band"])
    check("the sentence quotes the scan's band", "7x" in blk["sentence"], blk["sentence"])


# ------------------------------------------------------------------- fail-soft
def test_a_missing_audit_reports_unavailable_and_never_zero_refused():
    """A missing count and a zero count are different statements. Only one is true."""
    for bad in (None, {}, "nope", 17, {"band": 5.0}, {"rows_checked": 500}):
        blk = refusals.block(bad)
        check("available False for %r" % (bad,), blk["available"] is False)
        check("no sentence for %r" % (bad,), blk["sentence"] is None)
        check("refused is None, not 0, for %r" % (bad,), blk["refused"] is None)


def test_a_zero_or_negative_denominator_is_refused():
    for n in (0, -1, "x", None):
        blk = refusals.block(dict(LIVE_AUDIT, rows_checked=n))
        check("rows_checked=%r is not usable" % (n,), blk["available"] is False)


def test_a_non_finite_band_is_refused_not_rendered():
    """MA53's finding: `float()` accepts nan/inf where `int()` raises.

    A NaN band would render "past nanx the market price" — a broken sentence in front of a
    reader rather than an honest silence.
    """
    for bad in (float("nan"), float("inf"), float("-inf"), "nan", "inf"):
        blk = refusals.block(dict(LIVE_AUDIT, band=bad))
        check("band=%r is refused" % (bad,), blk["available"] is False, blk["sentence"])


def test_a_bool_is_not_a_count():
    """`bool` is an `int` subclass, so a flag would silently pass an int() check."""
    blk = refusals.block(dict(LIVE_AUDIT, withheld_refused=True))
    check("True is rejected as a count", blk["available"] is False)


# -------------------------------------------------- the third state (serve time)
def test_the_serve_time_band_withhold_is_reported_apart_with_its_own_denominator():
    """It has NO `kind` on the row and is about the peer estimator, not the model's DCF."""
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14", displayed=50,
                         display_withheld=5, display_peer_only=3)
    check("total counted", blk["display_withheld"] == 5, blk["display_withheld"])
    check("third state counted", blk["display_peer_only"] == 3, blk["display_peer_only"])
    check("its own denominator is the served slice", blk["displayed"] == 50, blk["displayed"])
    check("its sentence quotes 50 and not 500", "50 names" in blk["display_sentence"],
          blk["display_sentence"])
    check("the sentence uses the PEER-ONLY count, not the total",
          " 3 names also had" in blk["display_sentence"], blk["display_sentence"])
    check("it is named as a limit on the shortcut, not on the model",
          "not on the model" in blk["display_sentence"])
    check("it is NOT added to the scan-time refusals", blk["refused"] == 2, blk["refused"])


def test_a_model_refusal_in_the_served_slice_is_not_called_a_peer_withhold():
    """THE DEFECT THIS TEST EXISTS FOR, found in this module's own first cut.

    `withhold_implausible_fair_values` increments its counter for rows that were ALREADY marked
    withheld at scan time, so its return value is the TOTAL withheld in the slice. On the live
    scan that total is 2 and BOTH are model refusals — feeding it to the third-state sentence
    would have told a reader that the model's own refusals were peer-estimate withholds.
    """
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14", displayed=500,
                         display_withheld=2, display_peer_only=0)
    check("the total is still reported", blk["display_withheld"] == 2)
    check("but no peer sentence is drawn", blk["display_sentence"] is None,
          blk["display_sentence"])


def test_the_call_site_derives_the_third_state_from_the_absent_kind():
    """It must not pass the return value as the peer-only count. Source-level, because the
    distinction is invisible in the output whenever the two happen to be equal."""
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    check("a peer-only count is computed", "_peer_only" in src)
    check("it is derived from the missing kind", "not r.get(_RWK)" in src, )
    check("and it is what is passed", "display_peer_only=_peer_only" in src)
    check("the return value is passed as the TOTAL",
          "display_withheld=_band_withheld" in src)


def test_zero_display_withholds_draw_nothing():
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14", displayed=500,
                         display_withheld=0, display_peer_only=0)
    check("no sentence at zero", blk["display_sentence"] is None)


# ------------------------------------------------------- wording / correctness
def test_the_cause_is_not_asserted_because_a_currency_refusal_has_no_ratio():
    """`decide()` refuses on the band OR on an unresolved currency mismatch.

    The currency branch returns `ratio=None`, so "because its estimate was more than X× the
    price" — the audit's wording — is false for it. Verified against the real `decide` here,
    not assumed, so this fails if that branch ever starts carrying a ratio.
    """
    from valuation.engine.publication import decide

    class CD:
        financial_currency, currency, fx_rate, fx_unresolved = "KZT", "USD", None, True

    v = decide(100.0, 92.19, cd=CD())
    check("a currency refusal really does refuse", v.publish is False)
    check("and carries no ratio", v.ratio is None, v.ratio)
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14")
    check("so the copy hedges the cause", "usually because" in blk["sentence"],
          blk["sentence"])
    check("and names the other cause too", "currency or share-count" in blk["sentence"])


def test_the_scan_date_is_named_rather_than_called_today():
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14")
    check("dates the scan", "On the 2026-08-14 scan" in blk["sentence"], blk["sentence"])
    check("never says today", "today" not in blk["sentence"].lower())
    bare = refusals.block(LIVE_AUDIT)
    check("degrades to 'this scan' with no date", bare["sentence"].startswith("On this scan"))


def test_singular_and_plural():
    one = refusals.block(dict(LIVE_AUDIT, withheld_refused=1), scan_date="d")["sentence"]
    check("singular name", "for 1 of them" in one and "The name is still ranked" in one, one)
    many = refusals.block(dict(LIVE_AUDIT, withheld_refused=2), scan_date="d")["sentence"]
    check("plural names", "The names are still ranked" in many, many)


def test_the_live_numbers_render_the_expected_sentence():
    """The one reading taken from production, pinned end to end."""
    blk = refusals.block(LIVE_AUDIT, scan_date="2026-08-14", displayed=500, display_withheld=0)
    s = blk["sentence"]
    check("live sentence", s == (
        "On the 2026-08-14 scan the model was asked to value the top 500 names and declined "
        "to publish a fair value for 2 of them. In each case the model produced a number and "
        "its own guard rejected them — usually because the estimate came out past 5x the "
        "market price, which is almost always a currency or share-count problem rather than "
        "an opportunity. The names are still ranked normally: the ranking never uses a fair "
        "value."), s)


# ------------------------------------------------------------- the wiring
def test_the_endpoint_serves_the_block():
    """End to end through the real store and the real route."""
    from valuation.screener.store import Store
    from valuation.web import app as webapp

    path = os.path.join(tempfile.mkdtemp(prefix="ma29_"), "s.db")
    st = Store(path)
    rows = [{"ticker": "AAA", "price": 10.0, "rank": 1, "fair_value": 12.0},
            {"ticker": "BBB", "price": 10.0, "rank": 2, "fair_value": None}]
    st.save_snapshot("2026-08-14", rows, provider="test",
                     params={"universe_size": 800, "health": {"publication_audit": LIVE_AUDIT}})

    orig = webapp._store
    webapp._store = lambda: st
    try:
        with webapp.app.test_client() as c:
            d = c.get("/api/hotstocks?top=50").get_json()
    finally:
        webapp._store = orig

    blk = (d or {}).get("refusals")
    check("payload carries a refusals block", isinstance(blk, dict), type(blk))
    check("it is available", blk and blk.get("available") is True, blk)
    check("it carries the live numbers", blk and blk.get("refused") == 2
          and blk.get("asked") == 500, blk)
    check("no banned phrase in the served payload",
          refusals.violations(refusals.rendered_text(blk)) == [])
    check("the served slice is its display denominator", blk.get("displayed") == 2,
          blk.get("displayed"))
    check("the third state is counted, not inferred from the total",
          blk.get("display_peer_only") == 0, blk.get("display_peer_only"))


def test_a_snapshot_with_no_health_block_does_not_break_the_list():
    """Every snapshot saved before `publication_audit` existed must still render."""
    from valuation.screener.store import Store
    from valuation.web import app as webapp

    path = os.path.join(tempfile.mkdtemp(prefix="ma29b_"), "s.db")
    st = Store(path)
    st.save_snapshot("2026-08-14", [{"ticker": "AAA", "price": 10.0, "rank": 1}],
                     provider="test", params={"universe_size": 800})
    orig = webapp._store
    webapp._store = lambda: st
    try:
        with webapp.app.test_client() as c:
            r = c.get("/api/hotstocks?top=50")
            d = r.get_json()
    finally:
        webapp._store = orig
    check("still 200", r.status_code == 200, r.status_code)
    check("block present but unavailable", (d.get("refusals") or {}).get("available") is False,
          d.get("refusals"))
    check("and says nothing", (d.get("refusals") or {}).get("sentence") is None)


def test_the_renderer_quotes_the_module_and_does_not_paraphrase_it():
    """Copy in a template drifts silently — that is why one module owns it.

    The renderer must read every string from the block. A literal copy of the explainer in the
    JS would be a second owner of the wording, which is exactly what `V3` forbids.
    """
    js = open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    check("renderer reads the block's sentence", "rf.sentence" in js)
    check("renderer reads the block's explainer", "rf.explainer" in js)
    check("renderer reads the block's label", "rf.label" in js)
    check("renderer draws the two kinds separately", "rf.unavailable_sentence" in js)
    check("renderer gates on available", "rf.available" in js)
    # no paraphrase: a distinctive clause of the explainer must not be typed into the JS
    check("the explainer is not duplicated in the renderer",
          "statement about the MODEL" not in js)


def test_the_count_is_no_longer_discarded_at_the_call_site():
    """`withhold_implausible_fair_values` returns a count that used to be thrown away."""
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    m = re.search(r"^(\s*)(_?\w+\s*=\s*)?withhold\.withhold_implausible_fair_values\(rows\)",
                  src, re.M)
    check("the call site exists", m is not None)
    check("its return value is captured", bool(m and m.group(2)),
          m.group(0) if m else "")


def test_refusals_are_never_used_to_sort_or_filter_the_list():
    """A disclosure that reorders the book is a screen, and a screen needs a register."""
    src = open(os.path.join(ROOT, "valuation", "web", "app.py"), encoding="utf-8").read()
    for bad in ("sort(key=lambda r: r.get(\"fair_value_withheld\")",
                "if r.get(\"fair_value_withheld\")] ",
                "refusals_block[\"refused\"] >"):
        check("no %r" % bad[:34], bad not in src)
    js = open(os.path.join(ROOT, "valuation", "web", "static", "app.js"),
              encoding="utf-8").read()
    check("the renderer does not filter rows on the refusal flag",
          ".filter(r => r.fair_value_withheld" not in js)


def _code_only(path: str) -> str:
    """The module's CODE, with docstrings and comments removed.

    A line grep cannot tell code from the same words in prose. This module's own docstring says
    it "clears no threshold" — an assertion that the thing is absent — and a grep read that as
    the thing being present. Rather than add a file exemption (which is what stops a sweep
    finding the next real case), the text is reduced to code first: `ast.unparse` drops comments
    outright, and the docstring nodes are removed before unparsing.
    """
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
    """MA29 reports a count. It has no threshold, so it may not touch the research log."""
    code = _code_only(os.path.join(ROOT, "valuation", "web", "refusals.py"))
    for forbidden in ("research_log", "RESEARCH_LOG", "t_stat", "threshold", "p95", "verdict"):
        check("refusals.py CODE does not reference %s" % forbidden, forbidden not in code)


def test_the_code_only_reduction_is_not_vacuous():
    """If `_code_only` returned nothing, the sweep above would pass by seeing nothing."""
    path = os.path.join(ROOT, "valuation", "web", "refusals.py")
    code = _code_only(path)
    check("code survives the reduction", len(code) > 1000, len(code))
    check("real identifiers survive", "def block" in code and "BANNED" in code)
    check("the docstring prose is gone", "clears no threshold" not in code)
    check("prose really was in the raw file",
          "clears no threshold" in open(path, encoding="utf-8").read())


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        print(fn.__name__)
        fn()
    print("\n%d/%d checks failed" % (len(_FAILED), len(fns)))
    if _FAILED:
        for n in _FAILED:
            print("  FAILED:", n)
        sys.exit(1)
    print("MA29 refusals: all %d tests pass" % len(fns))
