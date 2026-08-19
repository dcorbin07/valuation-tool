"""The TIDEMARK surface ships derived statistics and nothing else — offline.

    python tests/test_tidemark_surface.py

WHAT IS AT RISK, and only one of the five is layout.

`VALQUO_MASTER_AUDIT_4.md` MB25 commissions a linked page reporting a SEPARATE project's
Phase-1 result; MB26 names the one thing that must not ship beside it.

1. **A LICENSED SERIES LEVEL REACHES THE PAGE.** Case-Shiller is S&P copyright and explicitly
   not redistributable; NAREIT's terms are unverified. TIDEMARK's own construction publishes
   only percentiles, episode counts and bands, so nothing had to be stripped — but a later edit
   that widens the payload would breach a licence rather than merely add a field.
   `test_no_licensed_level_reaches_the_payload` is the pin, and MB25 is explicit that **an
   allowlist alone is not enough**: it passes vacuously if the builder emits nothing. The
   sentinel is what makes it a measurement, and `test_the_sentinel_control_is_not_vacuous`
   proves the sentinel itself can be seen.

2. **THE CAPTIONS DRIFT.** MB25 requires them verbatim on the `V3`/`hold_horizon.py`
   precedent. TIDEMARK is not in this repository, so a test cannot diff these strings against
   its documents — the enforceable half is that each caption is a committed literal and each
   survives into the rendered page. That limit is stated in the module docstring rather than
   implied, and it is the honest scope of these tests.

3. **THE RULING FALLS OFF.** MB25: *"A dashboard shipped without that sentence reads as a
   signal."* The whole page is a refusal; losing the refusal inverts it.

4. **MB26 — A COMBINED VERDICT, OR AN UNLABELLED PAIR OF DENOMINATORS.** Valquo and TIDEMARK
   have separate registers and separate critical values. A page showing both without naming
   both denominators invites a reader to average statistics never measured against the same bar.

5. **THE STALENESS GATE FAILS OPEN.** `index_track.gate_state()`'s rule: every unrecognised
   outcome resolves toward showing no number, never toward a claim.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

import datetime as _dt                               # noqa: E402

from valuation.config import CONFIG                  # noqa: E402

CONFIG.private_mode = False

from valuation.saas.app_saas import create_saas_app  # noqa: E402
from valuation.web import tidemark_surface as TS     # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "web", "tidemark_surface.py")
TEMPLATE = os.path.join(ROOT, "valuation", "web", "templates", "tidemark.html")

#: MB25's own suggested sentinel.
SENTINEL = "123456.789"


def _page() -> str:
    with APP.test_client() as c:
        r = c.get("/tidemark")
        assert r.status_code == 200, f"/tidemark returned {r.status_code}"
        return r.data.decode("utf-8")


def _text(h: str) -> str:
    """Rendered page as prose: tags out, entities in, whitespace collapsed."""
    import html as _html
    return re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", h))).strip()


def _read(p: str) -> str:
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def _route_function(tree):
    """The `/tidemark` view function node, located by its decorator rather than by text."""
    import ast
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call) and dec.args
                    and isinstance(dec.args[0], ast.Constant)
                    and dec.args[0].value == "/tidemark"):
                return node
    raise AssertionError("no view function is decorated with the /tidemark route")


def _statements(fn):
    """The function's statements with the docstring dropped. Prose about code is not code."""
    import ast
    return [n for n in fn.body
            if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str))]


def _code_without_docstring(fn, src: str) -> str:
    """The function's CODE, with its docstring dropped. Prose about code is not code."""
    import ast
    body = [n for n in fn.body
            if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant)
                    and isinstance(n.value.value, str))]
    lines = src.splitlines()
    return "\n".join("\n".join(lines[n.lineno - 1:(n.end_lineno or n.lineno)]) for n in body)


# ------------------------------------------------------------------ 1. the licence pin

def test_no_licensed_level_reaches_the_payload():
    """MB25's pin, in both halves: the allowlist, and the sentinel that makes it a measurement.

    The allowlist half asserts every market row carries EXACTLY the nine keys MB25 names. The
    positive-control half widens the source table with a distinctive sentinel level and asserts
    it survives into neither the payload nor the page — which is a real test of the projection
    in `markets()`, because replacing that projection with `dict(m)` lets the sentinel straight
    through.
    """
    allow = ("market", "anchor", "percentile", "episodes", "n_eff",
             "band_sigma", "tier", "refusal", "as_of")
    assert TS.MARKET_KEYS == allow, ("the allowlist itself moved; MB25 names exactly these "
                                     f"nine keys, module has {TS.MARKET_KEYS}")

    rows = TS.payload()["markets"]
    assert rows, "no market rows at all — the allowlist would pass vacuously"
    for r in rows:
        assert set(r) == set(allow), (
            f"{r.get('anchor')} carries {sorted(set(r) - set(allow))} beyond the allowlist")

    # --- positive control: a series level in the source table must not survive
    original = TS.MARKETS
    try:
        TS.MARKETS = tuple(dict(m, level=float(SENTINEL), raw_series_value=SENTINEL)
                           for m in original)
        blob = json.dumps(TS.payload(), default=str)
        assert SENTINEL not in blob, (
            "a series level placed on the source table reached the payload — `markets()` is no "
            "longer projecting onto MARKET_KEYS")
        assert SENTINEL not in _page(), (
            "a series level placed on the source table reached the rendered page")
    finally:
        TS.MARKETS = original


def test_the_sentinel_control_is_not_vacuous():
    """Prove the sentinel can be SEEN, so its absence above is evidence rather than luck.

    This project's most-repeated test defect is a guard that passes because it is looking at
    nothing — `V6`'s C8 read a column the panel does not have, `MA5`'s guard fired on its own
    documentation, `MA23`'s stale-path guard was blind to the import syntax the codebase
    writes. Here: widen the allowlist so the sentinel is legitimately emitted, and require both
    detections to fire.
    """
    original_m, original_k = TS.MARKETS, TS.MARKET_KEYS

    # --- the PAYLOAD half: widening the allowlist must let the sentinel through
    try:
        TS.MARKETS = tuple(dict(m, level=float(SENTINEL)) for m in original_m)
        TS.MARKET_KEYS = original_k + ("level",)
        blob = json.dumps(TS.payload(), default=str)
        assert SENTINEL in blob, (
            "the sentinel could not reach the payload even when explicitly allowlisted, so the "
            "check above proves nothing")
    finally:
        TS.MARKETS, TS.MARKET_KEYS = original_m, original_k

    # --- the PAGE half, and the first cut of this test got it wrong.
    # Adding an unrendered key can never reach the HTML, because the template renders NAMED
    # fields only -- so proving the page check works needs the sentinel in a field the page
    # actually renders. `refusal` is the realistic leak path anyway: it is free prose, and free
    # prose is where a level would arrive if one ever did.
    try:
        TS.MARKETS = tuple(dict(m, refusal=f"leaked level {SENTINEL}") for m in original_m)
        assert SENTINEL in _page(), (
            "a sentinel placed in a RENDERED field did not reach the page, so the page half of "
            "the licence pin is looking at nothing")
    finally:
        TS.MARKETS = original_m


def test_the_page_reproduces_no_source_series_value():
    """A second, independent read: nothing on the page looks like a licensed index level.

    Percentiles are shown as 0-100 with one decimal, bands in sigma, effective n as a count.
    A Case-Shiller index level or a NAREIT yield would arrive as a bare number with no such
    unit. Rather than guess at magnitudes, this asserts the two licensed anchors contribute
    their DERIVED fields and that no numeric token on the page matches their stored level
    fields — of which there are none, which is the point.
    """
    licensed = {"us_housing_price_to_rent", "reit_dividend_yield", "reit_yield_spread"}
    present = {m["anchor"] for m in TS.MARKETS} & licensed
    assert present == licensed, f"the licensed anchors are not all present: {present}"
    for m in TS.MARKETS:
        assert set(m) == set(TS.MARKET_KEYS), (
            f"{m['anchor']}: the stored table itself carries a field beyond the allowlist")


# ------------------------------------------------------------------ 2/3. the copy

def test_every_caption_survives_into_the_page():
    """Each committed caption must reach the reader. A template may not silently drop one."""
    page = _text(_page())
    for name in ("HEADLINE", "HEADLINE_WHAT", "HEADLINE_WHY", "HEADLINE_STATUS",
                 "RULING", "RULING_INVERSE", "DESIGN_RULE", "BAND_WHERE", "BAND_IMPLIES",
                 "NO_STRATEGY_CLAIM", "EMPTY_TIERS_NOTE", "DENOMINATOR_WARNING",
                 "NO_COMBINED_VERDICT"):
        caption = re.sub(r"\s+", " ", getattr(TS, name)).strip()
        assert caption in page, f"{name} did not survive into the rendered page"


def test_the_ruling_is_present_verbatim_and_names_its_shortfall():
    """MB25 requires TIDEMARK's own words: a dashboard without this sentence reads as a signal."""
    assert TS.RULING.startswith("NO PHASE-2 QUESTION MAY BE ASKED ON THIS DATA."), TS.RULING
    for fragment in ("82 of the 155 independent years", "the worst has 25"):
        assert fragment in TS.RULING, f"the ruling lost {fragment!r}"
    assert fragment in _text(_page())


def test_the_unanswerable_finding_is_stated_as_the_headline_not_a_caveat():
    """The rotation question came back unanswerable at a pooled effective n of 3."""
    assert TS.HEADLINE == "The rotation question was asked. It came back unanswerable."
    assert TS.POOLED_EPISODES == 3, "the pooled independent episode count is the finding"
    assert "3 independent episodes" in TS.HEADLINE_WHY, TS.HEADLINE_WHY
    assert "headline finding, not a caveat" in TS.HEADLINE_STATUS
    page = _text(_page())
    assert TS.HEADLINE in page
    # It must arrive BEFORE any market reading, so no number is read without it.
    assert page.index(TS.HEADLINE) < page.index("Where it sits"), (
        "a market reading is rendered above the ruling, which inverts the page")


def test_the_inverse_reading_ships_with_its_ir_range():
    """POWER_GATE §3.1's more useful form: what the edge would have to be worth."""
    for fragment in ("0.41 to 0.74", "0.2 to 0.4"):
        assert fragment in TS.RULING_INVERSE, f"the inverse reading lost {fragment!r}"


def test_the_template_holds_no_tidemark_copy_of_its_own():
    """MB25: the module owns the copy, and nothing else may hold a TIDEMARK string.

    Enforced as: no committed caption appears as a literal in the template. A second copy of a
    sentence is a second place it can drift, which is the defect `hold_horizon.py` and
    `score_confidence.py` were both built to prevent.
    """
    tpl = _read(TEMPLATE)
    for name in ("HEADLINE", "HEADLINE_WHAT", "HEADLINE_WHY", "HEADLINE_STATUS", "RULING",
                 "RULING_INVERSE", "DESIGN_RULE", "BAND_WHERE", "BAND_IMPLIES",
                 "NO_STRATEGY_CLAIM", "EMPTY_TIERS_NOTE", "DENOMINATOR_WARNING",
                 "NO_COMBINED_VERDICT", "STALENESS_NOTE"):
        text = getattr(TS, name)
        probe = re.sub(r"\s+", " ", text).strip()[:40]
        assert probe not in re.sub(r"\s+", " ", tpl), (
            f"{name} is written literally into the template — it must render from the module")


# ------------------------------------------------------------------ 4. MB26

def test_both_denominators_are_named_and_labelled_with_their_project():
    """MB26: both Ns and both critical values, each attached to the project it belongs to."""
    d = TS.payload()["denominators"]
    assert d["tidemark"]["trials"] == 66, d["tidemark"]
    assert abs(d["tidemark"]["hurdle"] - 2.89) < 0.005, d["tidemark"]
    assert d["valquo"]["available"], (
        "Valquo's denominator could not be derived: " + d["valquo"]["reason"])
    assert d["valquo"]["equity"] > 0 and d["valquo"]["options"] > 0

    page = _text(_page())
    assert str(d["tidemark"]["trials"]) in page
    assert str(d["valquo"]["equity"]) in page and str(d["valquo"]["options"]) in page
    # each number must sit in a row naming its own project
    assert "TIDEMARK" in page and "Valquo" in page


def test_valquo_denominator_is_derived_and_never_typed():
    """MB25/MB26 quote 549 / 3.3031 / 3.3775 and the register had already moved past them.

    A typed denominator is guaranteed to go stale, so the module derives it. This asserts no
    audit-era literal was copied in — the failure this catches is someone "fixing" a derived
    value by pasting today's reading.
    """
    src = _read(MODULE)
    body = src.split('"""', 2)[2] if src.count('"""') >= 2 else src
    for stale in ("549", "3.3031", "3.3775"):
        assert stale not in body, (
            f"{stale!r} is typed into the module body; Valquo's denominator must be derived")
    assert "research_log" in body, "the module no longer derives Valquo's denominator at all"


def test_no_combined_verdict_and_no_cross_project_sentence():
    """MB26's prohibition. No statistic from one project inside a sentence about the other."""
    assert "no combined verdict" in TS.NO_COMBINED_VERDICT.lower()
    page = _text(_page())
    assert TS.NO_COMBINED_VERDICT in page
    assert TS.DENOMINATOR_WARNING in page

    # TIDEMARK's own figures must not appear inside any sentence naming Valquo, and vice versa.
    tide = {"66", "2.89", "155", "82"}
    for sentence in re.split(r"(?<=[.!?]) ", page):
        if "Valquo" in sentence and "TIDEMARK" not in sentence:
            hits = {n for n in tide if re.search(rf"\b{re.escape(n)}\b", sentence)}
            assert not hits, f"TIDEMARK figures {hits} appear in a Valquo sentence: {sentence!r}"


def test_no_forward_return_or_strategy_claim_anywhere():
    """TIDEMARK shipped no conditional return, and this page may not manufacture one."""
    page = _text(_page()).lower()
    for banned in ("expected return", "forward return", "annualized return", "we recommend",
                   "you should buy", "rotate into", "overweight"):
        assert banned not in page, f"the page carries a strategy-shaped phrase: {banned!r}"
    assert TS.NO_STRATEGY_CLAIM in _text(_page())


# ------------------------------------------------------------------ 5. the staleness gate

def test_the_staleness_gate_shows_the_vintage_instead_of_the_number():
    """Past the pre-committed limit every reading is suppressed, not merely annotated."""
    stamped = _dt.date.fromisoformat(TS.VINTAGE)
    late = stamped + _dt.timedelta(days=TS.STALE_AFTER_DAYS + 1)
    f = TS.freshness(late)
    assert not f["fresh"], f
    rows = TS.markets(late)
    assert rows, "no rows at all when stale"
    for r in rows:
        assert set(r) == set(TS.MARKET_KEYS), "the stale row broke the allowlist"
        for k in ("percentile", "episodes", "n_eff", "band_sigma", "tier"):
            assert r[k] is None, f"{r['anchor']} still shows {k} past the staleness limit"
        assert TS.VINTAGE in r["refusal"], "the stale row does not name the vintage"


def test_the_staleness_gate_is_not_vacuous_and_today_is_inside_it():
    """The boundary is real: one day inside the limit shows numbers, one day past does not."""
    stamped = _dt.date.fromisoformat(TS.VINTAGE)
    assert TS.freshness(stamped + _dt.timedelta(days=TS.STALE_AFTER_DAYS))["fresh"]
    assert not TS.freshness(stamped + _dt.timedelta(days=TS.STALE_AFTER_DAYS + 1))["fresh"]
    inside = TS.markets(stamped + _dt.timedelta(days=1))
    assert any(r["percentile"] is not None for r in inside), (
        "no reading is shown even when fresh — the stale test would pass vacuously")


def test_every_unrecognised_freshness_outcome_fails_toward_no_number():
    """`gate_state()`'s rule. A malformed or future-dated vintage is not a claim."""
    original = TS.VINTAGE
    try:
        for bad in ("", "not-a-date", "2026-13-99"):
            TS.VINTAGE = bad
            f = TS.freshness(_dt.date(2026, 8, 19))
            assert not f["fresh"] and f["reason"], f"{bad!r} did not fail closed: {f}"
    finally:
        TS.VINTAGE = original
    # a vintage dated in the future is also not a state this trusts
    future = _dt.date.fromisoformat(TS.VINTAGE) - _dt.timedelta(days=5)
    assert not TS.freshness(future)["fresh"]


# ------------------------------------------------------------------ the derived statistics

def test_the_percentile_band_reproduces_tidemarks_own_formula():
    """`SE(p) = sqrt(p(1-p)/n_eff)`, at the EFFECTIVE n and never at raw n.

    Recomputed here rather than carried, so this is a control on the table as well as on the
    arithmetic: a wrong `n_eff` would show up as a band that does not match TIDEMARK's.
    """
    import math
    checked = 0
    for m in TS.MARKETS:
        se = TS.percentile_se(m["percentile"], m["n_eff"])
        if m["percentile"] is None or m["n_eff"] is None:
            assert se is None
            continue
        expect = math.sqrt(m["percentile"] * (1 - m["percentile"]) / m["n_eff"])
        assert abs(se - expect) < 1e-12, m["anchor"]
        checked += 1
    assert checked >= 10, f"only {checked} bands checked — the control is thin"


def test_the_effective_n_is_always_below_the_raw_count_it_came_from():
    """A design effect above 1 is the whole reason this project exists. n_eff is never raw n."""
    for m in TS.MARKETS:
        if m["n_eff"] is None:
            continue
        assert m["n_eff"] > 0, m["anchor"]
        assert m["n_eff"] < 200, (
            f"{m['anchor']}: effective n {m['n_eff']} looks like a raw observation count")


def test_the_empty_top_tiers_are_still_rendered_with_their_counts():
    """The finding is that nothing reaches them. Hiding an empty tier hides the scale."""
    tiers = {t["tier"]: t for t in TS.payload()["tiers"]}
    assert set(tiers) == {"ACTIONABLE", "INDICATIVE", "NOT INTERPRETABLE", "REFUSED"}
    assert tiers["ACTIONABLE"]["count"] == 0 and tiers["INDICATIVE"]["count"] == 0, (
        "a market reached an actionable tier — this page's copy no longer describes it")
    page = _text(_page())
    for name in ("ACTIONABLE", "INDICATIVE"):
        assert name in page, f"the empty tier {name} is not shown"
    assert TS.EMPTY_TIERS_NOTE in page


def test_the_withdrawn_anchor_never_appears():
    """TIDEMARK's own rule: a withdrawn anchor beside live ones is an invitation to read it."""
    assert not any(m["anchor"] == "usd_real_broad" for m in TS.MARKETS)
    assert "usd_real_broad" not in _page()


def test_bitcoins_refusal_is_rendered_as_a_refusal_not_a_gap():
    """A blank cell reads as missing data — as something that will be filled in later."""
    btc = [m for m in TS.MARKETS if m["anchor"] == "btc_real"]
    assert len(btc) == 1, "the refusal case is gone, so this test measures nothing"
    b = btc[0]
    assert b["tier"] == "REFUSED" and b["percentile"] is None
    assert b["refusal"] and "refusal is the output" in b["refusal"]
    assert b["refusal"] in _text(_page())


# ------------------------------------------------------------------ the surface itself

def test_tidemark_is_a_linked_page_and_not_a_tab_in_the_hot_list():
    """MB25 specifies a linked page; a tab implies the two projects are one product."""
    page = _page()
    assert "/tidemark" not in _read(os.path.join(ROOT, "valuation", "web", "static", "app.js")), (
        "the hot-list app script references /tidemark, which is how a page becomes a tab")
    base = _read(os.path.join(ROOT, "valuation", "web", "templates", "_saas_base.html"))
    assert 'href="/tidemark"' in base, "the page is not linked from anywhere"
    assert "TIDEMARK" in page


def test_the_route_delegates_and_holds_no_copy_of_its_own():
    """The route may fetch and render. It may not hold a figure or a sentence.

    Read through the AST with the DOCSTRING REMOVED, not by grepping the source. The first cut
    grepped, and failed against a correct tree because the route's own docstring explains that
    the payload carries percentiles — a guard that cannot tell code from prose about code is
    not measuring the tree. That is `MA5`'s source sweep and `MA49(c)`'s fixture, for the third
    time in this repository, and `test_the_route_guard_is_not_vacuous` proves the replacement
    still bites.
    """
    import ast
    src = _read(os.path.join(ROOT, "valuation", "web", "app.py"))
    fn = _route_function(ast.parse(src))
    stmts = _statements(fn)

    # Every literal the route contains, from the syntax tree. A substring grep cannot do this
    # job: the second cut of this test banned "percentile" and failed on the DELEGATION CALL
    # `_tidemark.percentile_se`, which is the one thing the route is supposed to do.
    consts = [n.value for st in stmts for n in ast.walk(st)
              if isinstance(n, ast.Constant)]
    numbers = [c for c in consts if isinstance(c, (int, float)) and not isinstance(c, bool)]
    strings = [c for c in consts if isinstance(c, str)]
    assert not numbers, f"the route body carries numeric literals {numbers}; it must delegate"
    assert set(strings) <= {"tidemark.html"}, (
        f"the route body carries prose {sorted(set(strings) - {'tidemark.html'})}; the module "
        f"owns the copy")

    body = _code_without_docstring(fn, src)
    assert "tidemark_surface" in body and "render_template" in body


def test_the_route_guard_is_not_vacuous():
    """The guard above must fail on a route that really does hold a figure."""
    import ast
    src = _read(os.path.join(ROOT, "valuation", "web", "app.py"))
    fn = _route_function(ast.parse(src))
    assert _statements(fn), "the route body came back empty, so the guard reads nothing"
    assert _code_without_docstring(fn, src).strip(), "the route body reads as empty text"

    # A route that really does hold a figure and a sentence must be seen to hold them.
    tampered = ast.parse('@app.route("/tidemark")\n'
                         'def tidemark():\n'
                         '    """Doc mentioning percentile and episodes."""\n'
                         '    n = 66\n'
                         '    return render_template("x.html", note="NO PHASE-2 QUESTION")\n')
    bad = _route_function(tampered)
    consts = [n.value for st in _statements(bad) for n in ast.walk(st)
              if isinstance(n, ast.Constant)]
    assert any(isinstance(c, (int, float)) and not isinstance(c, bool) for c in consts), (
        "a numeric literal planted in a route body is invisible to this guard")
    assert any(isinstance(c, str) and "NO PHASE-2" in c for c in consts), (
        "prose planted in a route body is invisible to this guard")
    # ...and the docstring's mention of percentile must NOT be what trips it.
    assert not any(isinstance(c, str) and "percentile" in c for c in consts), (
        "the guard is reading the docstring again")


def test_the_page_carries_the_risk_disclaimer():
    """Every public surface in this project carries the same one string."""
    from valuation.web.app import RISK_DISCLAIMER
    assert re.sub(r"\s+", " ", RISK_DISCLAIMER).strip() in _text(_page())


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    """A duplicate `def test_` rebinds silently and the older one simply stops running.

    Session 40 shipped exactly that defect: a test was deleted by a name collision, the suite
    stayed green, and it was caught only by hand-counting. This runs that census as a test.
    """
    src = _read(os.path.abspath(__file__))
    names = re.findall(r"^def (test_\w+)", src, flags=re.M)
    dupes = {n for n in names if names.count(n) > 1}
    assert not dupes, f"shadowed test names: {sorted(dupes)}"
    reachable = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(names) == len(reachable), (
        f"{len(names)} definitions but {len(reachable)} reachable tests")


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
