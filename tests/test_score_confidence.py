"""The hot score's confidence language is the one V3's calibration registered — offline.

    python tests/test_score_confidence.py

WHAT IS AT RISK, and it is not layout.

Extension V3 measured the product's own score against a permutation null and the PER-NAME
result failed its pre-registered bar (rank 10, empirical p 0.116 — roughly one
chance-assembled universe in nine reaches the real value at that rank). The pre-registration
accepted, in writing and before the run, that this would require the product's confidence
language to weaken. `valuation/web/score_confidence.py` is that weakening.

Three ways it could silently un-weaken, all of which these tests are pointed at:

1. **THE WORDING DRIFTS.** The handoff's sentences were written to survive scrutiny; a
   surface that "tidies" one is how a calibrated hedge becomes a claim again. So every
   shipped sentence is asserted to appear VERBATIM in `HANDOFF_extensions_v3.md`, with the
   markdown normalised on the handoff's side only. If either side is reworded, this fails.

2. **THE GROUP HALF TRAVELS WITHOUT ITS CAVEAT.** V3's flattering finding — the top decile
   beats a chance book AS A GROUP — holds on only 21 of 69 dates. Quoting it as a standing
   property is the single most tempting misreading available here, so no rendered page may
   carry the group claim without the recency caveat in the same block.

3. **A SECOND COPY APPEARS IN JAVASCRIPT.** `app.js` renders the per-name panel. If it ever
   hard-codes its own softer version of the limit, a reader gets one story over the table and
   another on the name row. It must read `window.SCORE_CONFIDENCE` instead, so the tests
   assert the sentences are ABSENT from the static file.

Scope note, deliberately asserted rather than left to a comment: V3 settles the SCORE's
precision and explicitly not the backtested return spread. A test below fails if the
calibration copy ever attaches itself to a return figure.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG                  # noqa: E402

CONFIG.private_mode = False

from valuation.saas.app_saas import create_saas_app  # noqa: E402
from valuation.web import score_confidence as SC     # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(ROOT, "HANDOFF_extensions_v3.md")
APP_JS = os.path.join(ROOT, "valuation", "web", "static", "app.js")


def _norm(s: str) -> str:
    """Collapse markdown decoration and whitespace so a wrapped quote still matches.

    Only blockquote markers, emphasis and runs of whitespace are removed — nothing that could
    turn a DIFFERENT sentence into a matching one. `test_the_pin_is_not_vacuous` proves that.
    """
    return re.sub(r"\s+", " ", re.sub(r"[*_`>]", " ", s)).strip()


def _handoff() -> str:
    with open(HANDOFF, encoding="utf-8") as fh:
        return _norm(fh.read())


def _page(url: str) -> str:
    with APP.test_client() as c:
        r = c.get(url)
    assert r.status_code == 200, f"{url} returned {r.status_code}"
    return r.get_data(as_text=True)


def _app_page() -> str:
    return _page("/app")


def _methodology() -> str:
    return _page("/methodology")


# ------------------------------------------------------------------ 1. the pin to the handoff
def test_every_shipped_sentence_appears_verbatim_in_the_handoff():
    """THE ONE THE TASK ASKED FOR. The legend text must match the registered sentence."""
    doc = _handoff()
    for name in ("DEFENSIBLE", "PER_NAME", "THIN_DATA", "NO_LONGER_SAYABLE"):
        sentence = _norm(getattr(SC, name))
        assert sentence in doc, (
            f"score_confidence.{name} is not in {os.path.basename(HANDOFF)} verbatim.\n"
            f"  shipped:  {sentence!r}\n"
            "The handoff is the register. Either the product copy was reworded (fix the "
            "product) or the handoff was (that is a research-record change, not a copy edit)."
        )


def test_the_pin_is_not_vacuous():
    """A sentence that is NOT in the handoff must fail the same check.

    Without this, a normaliser that stripped too much — or a substring test against a huge
    document — would pass everything and the pin above would be decoration.
    """
    doc = _handoff()
    tampered = SC.DEFENSIBLE.replace("not distinguishable from chance",
                                     "clearly distinguishable from chance")
    assert _norm(tampered) not in doc, "the pin matches a sentence the handoff never made"

    softened = SC.PER_NAME.replace("is not distinguishable", "is broadly distinguishable")
    assert _norm(softened) not in doc

    # And the normaliser must not be collapsing distinct sentences together.
    assert _norm("Where an individual name sits inside that decile is fine") not in doc


def test_the_per_name_line_is_a_substring_of_the_legend_not_a_rewrite():
    """One source. The short form on a name row is literally part of the long form."""
    assert SC.PER_NAME in SC.DEFENSIBLE, (
        "PER_NAME must be an exact substring of DEFENSIBLE — otherwise the name row and the "
        "legend are two independently-editable statements of the same limit."
    )


def test_the_robustness_count_inside_the_sentence_matches_the_constant():
    """`45 of 69` is written into the sentence AND held as data; they must agree."""
    held, total = SC.PER_NAME_DATES
    assert f"{held} of {total} dates" in SC.DEFENSIBLE
    assert (held, total) == (45, 69)
    assert SC.GROUP_DATES == (21, 69)
    # The group result is the WEAKER of the two. If this ever inverts, the caveat below is
    # attached to the wrong half of the finding.
    assert SC.GROUP_DATES[0] < SC.PER_NAME_DATES[0]


def test_the_verdict_recorded_is_the_one_the_handoff_reached():
    doc = _handoff()
    assert SC.VERDICT == "NOT DISTINGUISHABLE"
    assert "VERDICT" in doc and "NOT DISTINGUISHABLE" in doc
    assert SC.PRIMARY_RANK == 10, "the registered primary statistic is the composite at rank 10"
    # Nobody may quote rank 5 (p 0.002) as the result; the handoff says so explicitly.
    assert "Nobody may quote rank 5" in doc


# ------------------------------------------------------------------ 2. the rendered surfaces
def test_the_hot_list_legend_carries_the_calibrated_sentence():
    html = _app_page()
    assert SC.DEFENSIBLE in html, "the ranking is rendered without its calibrated legend"
    assert SC.THIN_DATA in html, "the missing-data finding is not on the page"


def test_the_per_name_copy_no_longer_implies_per_name_precision():
    html = _app_page()
    assert SC.PER_NAME in html
    assert "coarse ordering, not a precise one" in html, (
        "the hot-list blurb still presents the rank without its precision limit"
    )


def test_the_group_claim_never_appears_without_its_recency_caveat():
    """The flattering half holds on 21 of 69 dates and may not stand alone."""
    caveat = SC.group_caveat()
    assert f"{SC.GROUP_DATES[0]} of {SC.GROUP_DATES[1]} dates" in caveat
    for url in ("/app", "/methodology"):
        html = _page(url)
        if "top decile as a group scores better" not in html:
            continue
        assert caveat in html, (
            f"{url} states the group-level result without the recency caveat — V3 measured it "
            f"on only {SC.GROUP_DATES[0]} of {SC.GROUP_DATES[1]} dates and it is not a "
            "standing property."
        )


def test_methodology_carries_the_finding_in_its_weaknesses_section():
    html = _methodology()
    assert SC.DEFENSIBLE in html
    assert SC.NO_LONGER_SAYABLE in html
    assert "Where it is weak" in html


def test_the_calibration_is_injected_for_javascript_from_the_same_constants():
    html = _app_page()
    assert "window.SCORE_CONFIDENCE" in html, (
        "app.js has no source for the calibrated wording, so the per-name panel would either "
        "render nothing or grow its own copy"
    )
    # The injected blob must actually carry the sentence, not an empty object.
    assert SC.PER_NAME.replace("—", "\\u2014") in html or SC.PER_NAME in html


# ------------------------------------------------------------------ 3. no second copy anywhere
def test_the_static_javascript_holds_no_copy_of_the_calibrated_wording():
    with open(APP_JS, encoding="utf-8") as fh:
        js = fh.read()
    for name in ("DEFENSIBLE", "PER_NAME", "THIN_DATA"):
        assert getattr(SC, name) not in js, (
            f"app.js hard-codes {name}. It must read window.SCORE_CONFIDENCE instead, or the "
            "name row and the legend become two editable statements of one limit."
        )
    assert "_SCORE_CONF" in js, "app.js no longer reads the injected calibration at all"


def test_the_context_processor_supplies_it_site_wide():
    """Registered on the shared app object, so BOTH render paths get it.

    index.html is rendered by valuation/web/app.py AND valuation/saas/app_saas.py. A per-route
    context variable would have to be added twice, and this project's recurring defect is the
    second place being forgotten.
    """
    with APP.test_request_context("/"):
        from valuation.web.app import _site_context
        ctx = _site_context()
    assert "score_confidence" in ctx
    assert ctx["score_confidence"]["defensible"] == SC.DEFENSIBLE
    assert ctx["score_confidence"]["per_name"] == SC.PER_NAME


# ------------------------------------------------------------------ 4. scope
def test_the_calibration_copy_is_not_attached_to_a_return_claim():
    """V3 settles the SCORE's precision, explicitly not the backtested return spread.

    Its handoff: "A composite can rank names in an order that is indistinguishable from chance
    at a given rank and still have a real top-minus-bottom return spread." Attaching this
    caveat to an alpha figure would understate the edge research as badly as dropping it from
    the score would oversell the ranking.
    """
    html = _methodology()
    i = html.find(SC.DEFENSIBLE)
    assert i >= 0
    block = html[i:i + 1400]
    assert "not about the backtested return spread" in block, (
        "the calibration paragraph no longer states its own scope"
    )
    # The paragraph must not silently become a returns caveat.
    for figure in ("%/yr", "alpha of", "breakeven"):
        assert figure not in block, f"the score-calibration block now quotes {figure!r}"


def test_the_source_files_it_quotes_are_tracked_and_present():
    """A pin against a file that is not in the repo pins nothing on anyone else's checkout."""
    assert os.path.exists(HANDOFF), f"{SC.SOURCE} is missing"
    assert os.path.exists(os.path.join(ROOT, SC.REGISTER)), f"{SC.REGISTER} is missing"


if __name__ == "__main__":
    fns = [(k, v) for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}\n      {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
