"""The hold-horizon copy is the sentence S22 registered — offline.

    python tests/test_hold_horizon.py

WHAT IS AT RISK, and it is not layout.

Extension S22 (`HANDOFF_edge_audit.md` session 18) found that the top decile's annualized
alpha is essentially FLAT from three months to two years. That is the most flattering shape a
term-structure study can return, which is precisely why its handoff did not leave the wording
to a page: §6 registers ONE sentence as the only claim derivable with no extrapolation, and
names the caveats "without which it may not be displayed".

Four ways that could silently become a bigger claim, and each has a test below:

1. **THE SENTENCE DRIFTS.** Every shipped sentence must appear VERBATIM in the handoff, with
   markdown normalised on the handoff's side. A surface that "tidies" a registered sentence is
   how a measured figure becomes a promise.

2. **THE CAVEATS FALL OFF.** §6 says the sentence may not be displayed without them. They are
   held as separate clauses and every one must survive into the rendered page — a caveat line
   that loses "gross of costs" while keeping the return figure is the failure mode.

3. **THE LONG-SHORT SPREAD GETS BLENDED IN.** It does NOT persist — HAC t falls 2.7167 at one
   quarter to 0.6846 at two years — and the handoff forbids quoting it beyond about a year.
   The persistence lives entirely in the long leg, which is fortunate because the product is a
   long-only list, but it means the research statistic and the product statistic diverge with
   horizon. No long-short figure may appear in the module or beside this copy on a page.

4. **IT BECOMES A PER-NAME PROMISE.** V3 already established that where a name sits inside the
   decile is not distinguishable from chance. S22's figures are the decile's as a group, so the
   only half that may reach a name row is the LIMIT, and it is an exact substring of the long
   form rather than a second editable sentence.

A fifth, from the handoff's own §7: the result is NOT a finding that the book should rebalance
less often, and §7 calls that "the most likely way this result gets misused". The product ships
that distinction rather than leaving it in a research file.
"""
import html as _html
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                  # noqa: E402

CONFIG.private_mode = False

from valuation.saas.app_saas import create_saas_app  # noqa: E402
from valuation.web import hold_horizon as HH         # noqa: E402
from valuation.web import score_confidence as SC     # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HANDOFF = os.path.join(ROOT, "HANDOFF_edge_audit.md")
APP_JS = os.path.join(ROOT, "valuation", "web", "static", "app.js")


def _norm(s: str) -> str:
    """Strip markdown decoration and collapse whitespace.

    Emphasis and blockquote markers are REMOVED rather than replaced by a space, because that
    is what a reader sees: the handoff writes `universe**; **gross`, which renders as
    `universe; gross`. Nothing here can turn a DIFFERENT sentence into a matching one —
    `test_the_pin_is_not_vacuous` proves it.
    """
    return re.sub(r"\s+", " ", re.sub(r"[*`>]", "", s)).strip()


def _handoff() -> str:
    with open(HANDOFF, encoding="utf-8") as fh:
        return _norm(fh.read())


def _page(url: str) -> str:
    with APP.test_client() as c:
        r = c.get(url)
    assert r.status_code == 200, f"{url} returned {r.status_code}"
    return r.get_data(as_text=True)


def _visible(url: str) -> str:
    """The page as a READER sees it — entities resolved.

    Jinja autoescapes, so `one quarter's selection` reaches the browser as `quarter&#39;s`.
    Asserting against the raw markup would make the pin depend on which punctuation a
    registered sentence happens to contain, and would quietly stop matching the day someone
    adds an apostrophe to the handoff. Escaping is correct output; it just is not the text.
    """
    return _html.unescape(_page(url))


# ------------------------------------------------------------------ 1. the pin to the handoff
def test_the_registered_sentence_ships_verbatim():
    """THE ONE THE TASK ASKED FOR. §6's sentence, not a paraphrase of it."""
    doc = _handoff()
    assert _norm(HH.DEFENSIBLE) in doc, (
        f"hold_horizon.DEFENSIBLE is not in {os.path.basename(HANDOFF)} verbatim.\n"
        f"  shipped: {_norm(HH.DEFENSIBLE)!r}\n"
        "The handoff is the register. Either the product copy was reworded (fix the product) "
        "or the handoff was (that is a research-record change, not a copy edit)."
    )


def test_every_mandatory_caveat_clause_is_quoted_from_the_handoff():
    doc = _handoff()
    for clause in HH.CAVEAT_CLAUSES:
        assert _norm(clause) in doc, f"caveat clause not in the handoff verbatim: {clause!r}"
    assert len(HH.CAVEAT_CLAUSES) == 3


def test_the_misuse_warning_opens_with_the_handoffs_own_words():
    """§7's sentence, so the product's version cannot soften the research one."""
    head = HH.NOT_A_HOLD_RULE.split(" — ")[0]
    assert _norm(head) in _handoff(), (
        "NOT_A_HOLD_RULE no longer opens with §7's registered sentence"
    )


def test_the_pin_is_not_vacuous():
    """Sentences the handoff never made must fail the same check."""
    doc = _handoff()
    for tampered in (
        HH.DEFENSIBLE.replace("about 5.1% annualized", "about 15.1% annualized"),
        HH.DEFENSIBLE.replace("beat the equal-weighted universe", "beat the S&P 500"),
        HH.NOT_A_HOLD_RULE.split(" — ")[0].replace("is not", "is"),
    ):
        assert _norm(tampered) not in doc, f"the pin matches a sentence never made: {tampered!r}"
    # And the normaliser must not be collapsing distinct sentences together.
    assert _norm("The top decile beat the universe at every horizon tested") not in doc


def test_the_verdict_and_provenance_are_the_handoffs():
    doc = _handoff()
    assert HH.VERDICT == "CONSTANT-RATE"
    assert "CONSTANT-RATE" in doc
    assert HH.HORIZON_QUARTERS == 8
    assert os.path.exists(HANDOFF)
    assert os.path.exists(os.path.join(ROOT, HH.REGISTER)), f"{HH.REGISTER} is missing"


def test_the_figures_in_the_sentence_match_the_constants():
    """The prose and the data must not be independently editable."""
    assert f"about {HH.ALPHA_ANN_FIRST_QUARTER}% annualized" in HH.DEFENSIBLE
    assert f"about {HH.ALPHA_ANN_TWO_YEARS}% annualized" in HH.DEFENSIBLE
    assert (HH.ALPHA_ANN_FIRST_QUARTER, HH.ALPHA_ANN_TWO_YEARS) == (6.6, 5.1)
    assert f"{HH.PANEL_NAMES:,}-name / {HH.PANEL_DATES}-date panel" in HH.caveat()
    assert (HH.PANEL_NAMES, HH.PANEL_DATES) == (2531, 69)
    # Rank IC rises with horizon — an independent route to the same finding. If this ever
    # inverts, the methodology paragraph is describing the opposite of the data.
    assert HH.RANK_IC_TWO_YEARS > HH.RANK_IC_FIRST_QUARTER


# ------------------------------------------------------------------ 2. one source, no rewrites
def test_the_per_name_line_is_a_substring_of_the_registered_sentence():
    assert HH.PER_NAME in HH.DEFENSIBLE, (
        "PER_NAME must be an exact substring of DEFENSIBLE — otherwise the name row and the "
        "legend are two independently-editable statements of one limit."
    )


def test_the_name_row_carries_the_limit_and_not_the_return_figures():
    """V3 forbids a per-name promise; the decile's returns are not this name's."""
    note = HH.per_name_note()
    assert HH.PER_NAME in note
    for figure in ("6.6%", "5.1%", "annualized", "beat the equal-weighted"):
        assert figure not in note, (
            f"the per-name note quotes {figure!r} — S22's figures are the top decile's as a "
            "group, and attaching one to a single name is the promise V3 ruled out"
        )


def test_the_static_javascript_holds_no_copy_of_the_wording():
    with open(APP_JS, encoding="utf-8") as fh:
        js = fh.read()
    for name in ("DEFENSIBLE", "PER_NAME", "BAND", "BAND_SCOPE", "NOT_A_HOLD_RULE"):
        assert getattr(HH, name) not in js, (
            f"app.js hard-codes {name}. It must read window.HOLD_HORIZON instead, or the name "
            "row and the legend become two editable statements of one finding."
        )
    assert "_HOLD_H" in js, "app.js no longer reads the injected hold-horizon copy at all"


def test_the_context_processor_supplies_it_site_wide():
    """index.html is rendered by BOTH web/app.py and saas/app_saas.py."""
    with APP.test_request_context("/"):
        from valuation.web.app import _site_context
        ctx = _site_context()
    assert "hold_horizon" in ctx
    assert ctx["hold_horizon"]["defensible"] == HH.DEFENSIBLE
    assert ctx["hold_horizon"]["per_name"] == HH.PER_NAME


# ------------------------------------------------------------------ 3. the rendered surfaces
def test_the_hot_list_states_the_horizon_with_its_caveats():
    html = _visible("/app")
    assert HH.DEFENSIBLE in html, "the ranking is rendered without the hold-horizon sentence"
    for clause in HH.CAVEAT_CLAUSES:
        assert clause in html, (
            f"the mandatory caveat clause {clause!r} is not on the page — §6 says the sentence "
            "may not be displayed without it"
        )
    assert HH.NOT_A_HOLD_RULE in html, "the page states the two-year figure without §7's warning"


def test_methodology_carries_the_finding_and_the_same_caveats():
    html = _visible("/methodology")
    assert HH.DEFENSIBLE in html, "/methodology lost the registered sentence"
    assert HH.NOT_A_HOLD_RULE in html, "/methodology states the figure without §7's warning"
    for clause in HH.CAVEAT_CLAUSES:
        assert clause in html, f"/methodology dropped the caveat clause {clause!r}"


def test_the_injected_blob_reaches_javascript():
    html = _page("/app")
    assert "window.HOLD_HORIZON" in html, (
        "app.js has no source for the hold-horizon wording, so the name panel and the "
        "valuation band would either render nothing or grow their own copy"
    )
    assert HH.PER_NAME.replace("—", "\\u2014") in html or HH.PER_NAME in html


# ------------------------------------------------------------------ 4. scope — the long-short
def test_no_long_short_figure_appears_in_the_module():
    """It decays to insignificance by two years; the handoff forbids quoting it alongside."""
    src = open(os.path.join(ROOT, "valuation", "web", "hold_horizon.py"), encoding="utf-8").read()
    shipped = "\n".join(str(v) for k, v in sorted(vars(HH).items())
                        if k.isupper() and isinstance(v, (str, tuple, int, float)))
    shipped += HH.caveat() + HH.per_name_note()
    for token in ("long-short", "long/short", "short leg", "spread of"):
        assert token not in shipped.lower(), (
            # Assertion messages stay inside cp1252: these suites are run offline with
            # `python tests/test_x.py` on a Windows console, and a message carrying a character
            # the console cannot encode crashes the RUNNER — the suite exits non-zero while
            # printing nothing about why. Found by the mutation harness, not by reasoning.
            f"a shipped hold-horizon string mentions {token!r} — the long-short spread does not "
            "persist (HAC t falls 2.72 to 0.68) and may not travel with this copy"
        )
    # The module may DISCUSS it in prose, and should: the exclusion is deliberate, not an
    # oversight, and a future editor needs to know why. This asserts the reason is recorded.
    assert "long-short" in src.lower(), (
        "the module no longer explains why the long-short spread is excluded, so the omission "
        "reads as an accident and the next editor will 'complete' the picture"
    )


def test_the_long_short_spread_is_not_quoted_beside_the_horizon_copy():
    """On a rendered page, not just in the module."""
    for url in ("/app", "/methodology"):
        html = _visible(url)
        i = html.find(HH.DEFENSIBLE)
        assert i >= 0, f"{url} lost the hold-horizon sentence"
        block = html[max(0, i - 1200):i + 2500]
        for token in ("long-short", "long/short"):
            assert token not in block.lower(), (
                f"{url} quotes a long-short figure beside the hold-horizon claim; the spread "
                "decays to insignificance by two years and the handoff forbids it"
            )


def test_the_horizon_copy_is_not_attached_to_a_score_precision_claim():
    """S22 settles how long RETURNS persisted; V3 settles the SCORE's precision.

    They are different objects with different evidence. Merging them would either import V3's
    'not distinguishable from chance' into a return finding it does not describe, or lend S22's
    persistence to a ranking precision it never measured.
    """
    html = _visible("/app")
    i = html.find(HH.DEFENSIBLE)
    block = html[i:i + 1500]
    assert SC.DEFENSIBLE not in block, (
        "the score-calibration sentence now sits inside the hold-horizon block; those are "
        "different findings about different objects"
    )


# ------------------------------------------------------------------ 5. the valuation band
def test_the_band_is_framed_as_a_zone_and_never_as_a_target():
    assert "zone the model considers full value" in HH.BAND
    assert "not a target" in HH.BAND
    for banned in ("price target", "will reach", "expect the price", "should trade at"):
        assert banned not in HH.BAND.lower(), f"the band copy promises: {banned!r}"


def test_the_band_does_not_borrow_the_backtests_evidence():
    """Different object: the valuation engine on one company's filings, not the composite."""
    for token in ("6.6%", "5.1%", "top decile", "backtest,"):
        assert token not in HH.BAND, f"the band copy quotes an S22 figure: {token!r}"
    assert "do not check each other" in HH.BAND_SCOPE, (
        "BAND_SCOPE no longer says the two measurements are independent, which is the whole "
        "reason it exists"
    )


def test_the_band_copy_is_absent_when_the_valuation_is_withheld():
    """A withheld fair value has no zone to describe.

    LA10 established that a refusal clears every derived field; the band is the same class of
    object. `app.js` blanks `scenarioNote` on the withheld path — this pins that the band
    wording is not rendered unconditionally somewhere upstream of it.
    """
    with open(APP_JS, encoding="utf-8") as fh:
        js = fh.read()
    i = js.find('setHtml("scenarioCards", withheldBox')
    assert i >= 0, "the withheld branch for the scenario cards has moved or gone"
    tail = js[i:i + 400]
    assert 'setHtml("scenarioNote", "")' in tail, (
        "the withheld branch no longer clears scenarioNote, so the band framing could describe "
        "a valuation the product refused to publish"
    )


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
