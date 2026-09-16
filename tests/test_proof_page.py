"""The /proof page — pins the properties that make it evidence rather than marketing.

The page's whole claim is that it does not type its numbers. That is a claim about the
SOURCE, so it is asserted against the source, and the guards below are checked for vacuity in
both directions — a guard that passes because it is looking at nothing is the failure mode
this repository has recorded more often than any other.

Run as its own process and judged by exit code, like every suite here.
"""

import os
import re
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.web import proof                                    # noqa: E402
from valuation.web.app import app as APP                           # noqa: E402

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "valuation", "web", "templates", "proof.html")

# Numbers a reader would take for a research result. Deliberately NOT "any digit": the
# template legitimately carries CSS lengths, list numbering, example years and the definition
# of a statistic's own scale (-1.0 is a perfectly ordered ladder). What it must never carry is
# a figure that could be read as a return, a t-statistic or a threshold this project measured.
_PERFORMANCE_SHAPED = re.compile(r"(?<![\w.-])\d{1,3}\.\d{1,4}(?![\w])")


def _template_prose():
    """The template with CSS, Jinja and comments removed — what a reader actually sees.

    Both the <style> block AND inline style="" attributes are stripped, because a padding
    value is not a claim and leaving them in would force the guard to be loosened until it
    caught nothing.
    """
    src = open(TEMPLATE, encoding="utf-8").read()
    src = re.sub(r"<style>.*?</style>", " ", src, flags=re.S)
    src = re.sub(r'style="[^"]*"', " ", src)
    src = re.sub(r"\{\{.*?\}\}", " ", src, flags=re.S)      # Jinja expressions — derived
    src = re.sub(r"\{%.*?%\}", " ", src, flags=re.S)
    src = re.sub(r"\{#.*?#\}", " ", src, flags=re.S)
    return src


def test_the_template_types_no_performance_figure():
    """THE LOAD-BEARING GUARD. Every number on the page must come from an artifact.

    A proof page carrying a hand-typed statistic is the claim and its refutation in one
    object: the moment the backtest is re-run, the page is asserting something the repository
    no longer says, and it is the one page on the site whose only job is to be checkable.
    """
    typed = _PERFORMANCE_SHAPED.findall(_template_prose())
    # -1.0 is the definition of the monotonicity scale, not a measurement of it.
    typed = [t for t in typed if t not in ("1.0",)]
    assert not typed, (
        f"proof.html types performance-shaped numbers {sorted(set(typed))} — every figure on "
        f"this page must be derived in proof.py and rendered through a Jinja expression")


def test_that_guard_can_actually_fail():
    """Positive control. The regex above must catch a typed figure when one is present —
    otherwise the test above passes by seeing nothing, which is how four earlier guards in
    this project stayed green over live defects."""
    assert _PERFORMANCE_SHAPED.findall("the composite returned 7.17 a year")
    assert _PERFORMANCE_SHAPED.findall("t 2.6199 against a floor")
    assert not _PERFORMANCE_SHAPED.findall("padding:26px"), "the guard would fire on CSS"
    assert not _PERFORMANCE_SHAPED.findall("in 2016 and 2022"), "the guard would fire on years"


def test_the_payload_refuses_rather_than_substituting():
    """A missing artifact must cost a section and be NAMED, never be filled in from memory.

    Pointed at a directory with no artifacts, `payload()` has to come back unavailable. The
    dangerous failure is the opposite one — a module that quietly falls back to a constant
    looks identical to a working page and is a lie.
    """
    real_backtest, real_draws, real_summary = (proof.BACKTEST_JSON, proof.PLACEBO_JSON,
                                               proof.PLACEBO_FALLBACK_JSON)
    try:
        proof.BACKTEST_JSON = os.path.join(os.path.sep, "nonexistent", "BACKTEST_RESULTS.json")
        p = proof.payload()
        assert p["available"] is False, "payload() invented a page with no artifact to read"
        assert p["missing"], "it refused without saying what was missing"
        assert "reason" in p
    finally:
        proof.BACKTEST_JSON, proof.PLACEBO_JSON, proof.PLACEBO_FALLBACK_JSON = (
            real_backtest, real_draws, real_summary)

    # And the refusal reaches the page rather than throwing a 500 at a visitor.
    assert proof.payload()["available"] is True, "the restore failed; later tests are void"


def test_a_missing_placebo_costs_a_section_and_not_the_page():
    """Partial failure is the common case and must degrade honestly: the other sections still
    render, and the hole is named in `missing` rather than being invisible."""
    real_draws, real_summary = proof.PLACEBO_JSON, proof.PLACEBO_FALLBACK_JSON
    try:
        proof.PLACEBO_JSON = os.path.join(os.path.sep, "nonexistent", "a.json")
        proof.PLACEBO_FALLBACK_JSON = os.path.join(os.path.sep, "nonexistent", "b.json")
        p = proof.payload()
        assert p["available"] is True, "losing the placebo took down the whole page"
        assert p["placebo"] is None
        assert p["missing"], "the missing placebo was not named"
        assert p["benchmarks"], "an unrelated section was lost with it"
    finally:
        proof.PLACEBO_JSON, proof.PLACEBO_FALLBACK_JSON = real_draws, real_summary


def test_the_placebo_counts_are_counted_from_the_draws():
    """`N of 100 noise runs beat it` is the most quotable sentence on the page, so it is
    recomputed here from the raw file rather than trusted.

    A tie must count AGAINST the strategy. That is not pedantry: on the decile-ordering
    statistic — which is a rank correlation over ten buckets and therefore coarse — a noise
    draw EXACTLY equals the real value, so the difference between `>` and `>=` is the
    difference between claiming a clean sweep and reporting 1 of 100.
    """
    p = proof.payload()
    pl = p["placebo"]
    assert pl and pl["counted_from_draws"], "the page fell back to percentiles"

    raw = json.load(open(proof.PLACEBO_JSON, encoding="utf-8"))["draws"]
    for row in pl["rows"]:
        vals = [d[row["key"]] for d in raw if isinstance(d.get(row["key"]), (int, float))]
        if row["direction"] == "high":
            expected = sum(1 for v in vals if v >= row["real"])
        else:
            expected = sum(1 for v in vals if v <= row["real"])
        assert row["n_beaten"] == expected, (
            f"{row['key']}: page says {row['n_beaten']} of {row['n_draws']}, the draws say "
            f"{expected}")
        assert row["beats_every_draw"] == (expected == 0)

        # AND THE BAR ITSELF, which the count above does not cover. Found by mutation: halving
        # `noise_bar` left every other assertion green while making the real result look like
        # it cleared a threshold twice as easy as the one actually measured. The floor is the
        # claim, so the floor is recomputed — and the error runs in the flattering direction,
        # which is the direction nothing else here was checking.
        s = sorted(vals)
        q = 0.95 if row["direction"] == "high" else 0.05
        pos = q * (len(s) - 1)
        lo_i = int(pos)
        want = s[lo_i] * (1 - (pos - lo_i)) + s[min(lo_i + 1, len(s) - 1)] * (pos - lo_i)
        assert abs(row["noise_bar"] - want) < 1e-9, (
            f"{row['key']}: page shows a noise floor of {row['noise_bar']}, the draws give "
            f"{want} — the bar the result is judged against does not match the draws")
        assert abs(row["noise_median"] - sorted(vals)[len(vals) // 2]) < 0.05, \
            f"{row['key']}: the 'typical noise run' figure is not the draws' median"
        assert row["noise_min"] == min(vals) and row["noise_max"] == max(vals)

    # Non-vacuous: at least one row must be a clean sweep and at least one must not be, or
    # this test is agreeing with a constant.
    swept = [r["beats_every_draw"] for r in pl["rows"]]
    assert any(swept) and not all(swept), (
        "every placebo row has the same verdict — the comparison is not discriminating and "
        "the page is not reporting an honest mix")


def test_no_licensed_international_figure_ships():
    """Global Factor Data is CC BY-NC 4.0 and `CLAUDE.md` records the rule without
    qualification: the X8 replication validates the model and can NEVER ship in the product.

    The page is allowed to say the replication exists and to say why its numbers are absent.
    It is not allowed to print them. Checked against the rendered page, because the licence
    binds what reaches a reader and not what the source looks like.
    """
    body = APP.test_client().get("/proof").get_data(as_text=True)
    for banned in ("3.85", "4.30", "2.35", "2.05%", "3.36%"):
        assert banned not in body, f"the proof page prints a licensed X8 figure: {banned!r}"
    assert "jkp" not in body.lower()
    # It must still DISCLOSE the omission — silence would be the dishonest way to comply.
    low = body.lower()
    assert "licen" in low and ("non-commercial" in low or "cannot be published" in low), \
        "the page drops the strongest evidence without telling the reader why"


def test_the_failing_bars_are_on_the_page():
    """The reason this page exists. Three of the four standard thresholds are FAILED and a
    version that quietly showed only the passing one would be advertising.

    Pinned against the payload rather than the prose so a copy edit cannot remove a failure
    without this going red.
    """
    bars = proof.payload()["bars"]
    assert bars, "no thresholds rendered at all"
    failed = [b for b in bars if not b["passes"]]
    passed = [b for b in bars if b["passes"]]
    assert failed, "the page shows no failing threshold — check it is not filtering them out"
    assert passed, "the page shows no passing threshold either; the section is broken"
    names = " ".join(b["name"].lower() for b in failed)
    assert "harvey" in names or "hurdle" in names, \
        "the multiple-testing hurdle — the headline's clearest failure — is not shown failing"

    body = APP.test_client().get("/proof").get_data(as_text=True).lower()
    assert "fails" in body, "no failure is visible to a reader"


def test_the_page_is_static_by_construction():
    """Byte-identical across requests and making no API call — the same property the portfolio
    page pins, and for the same reason: it makes 'this page reads no vendor data' a fact about
    the code rather than a promise in a docstring."""
    c = APP.test_client()
    a = c.get("/proof")
    b = c.get("/proof")
    assert a.status_code == 200 and len(a.data) > 5000
    assert a.data == b.data, "the proof page is not deterministic across requests"
    body = a.get_data(as_text=True)
    assert "/api/" not in body, "the proof page fetches from the API"
    assert "fetch(" not in body


def test_the_page_says_when_it_was_generated():
    """A proof page that will not date itself is not one. The stamp is the reader's only way
    to know the numbers are current, and a stale artifact must show as a stale date rather
    than being silently relabelled."""
    p = proof.payload()
    assert p["generated_at"], "no generation timestamp"
    body = APP.test_client().get("/proof").get_data(as_text=True)
    assert p["generated_at"][:10] in body, "the run date is computed but never rendered"


def test_the_trial_count_is_read_live_and_not_from_the_stale_artifact():
    """The count of tests run is the denominator that makes the multiple-testing hurdle
    honest, and it rises whenever any lane books a trial while the backtest artifact is only
    rebuilt on a full run. Reading it live is what stops the page understating how many shots
    were taken — and understating it would flatter the result."""
    p = proof.payload()
    assert p["trials"] and p["trials"].get("equity"), "no trial count on the page"
    assert p["trials_source"], "the trial count does not say where it came from"
    artifact = json.load(open(proof.BACKTEST_JSON, encoding="utf-8"))
    frozen = artifact.get("multiple_testing", {}).get("by_domain", {}).get("equity")
    if frozen and "RESEARCH_LOG" in (p["trials_source"] or ""):
        assert p["trials"]["equity"] >= frozen, (
            "the live trial count is BELOW the artifact's — the denominator moved backwards, "
            "which would overstate significance")


def _run():
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {fn.__name__}: {e}")
        except Exception as e:                                   # noqa: BLE001
            failed += 1
            print(f"  ERR  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(_run())
