"""SC-1 (was the record's own forecasting any good?) and S3-I7 (the declared-book shelf).

Two additions to `/research`, tested against the same two failure modes the page was already
built around, because they are the ones that actually happen here:

  * A NUMBER THAT GOES STALE. `MB38` derives the trial denominator at render because a count
    typed onto a public page is wrong the week after it ships. The calibration section carries
    a count of the same kind — how many predictions have been scored — and it is derived from
    a published card for exactly that reason. `test_the_count_moves_with_the_card` and
    `test_no_measured_calibration_value_is_typed_into_the_source` are the two halves of that.

  * A GUARD THAT OPENS INSTEAD OF CLOSING. Both figures the calibration section renders are
    bare decimals, so the page's own no-figures rule redacts them, and the fix is a second
    exemption on `MB38`'s exact terms: derived, whole matches only, and EMPTY when the source
    cannot be read. Every one of those three is pinned, and the last one is pinned in the
    direction that matters — `test_the_exemption_is_empty_when_the_card_cannot_be_read`
    asserts the figure comes BACK under the rule, not that the page still renders.

The shelf is tested mostly for what it REFUSES to infer. It never reads a status off the
calendar, never guesses a horizon out of a document's prose (`preregistrations()` records what
that costs: one register was given a registration date of 1998-01-01, from its own contents),
and never quietly rolls a closed window forward. And it is tested while EMPTY, because that is
the state it ships in and a shelf that only appeared once it had something to show would be
evidence of nothing.

Run: python tests/test_research_shelf_and_calibration.py
"""
from __future__ import annotations

import ast
import json
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.web import research_record as RR                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "web", "research_record.py")
TEMPLATE = os.path.join(ROOT, "valuation", "web", "templates", "research.html")


def _artifact_path() -> str:
    """Where `SC1B_CLUSTER_BY_ITEM.json` actually is, which is often not under this checkout.

    `data/` is gitignored, so a git WORKTREE carries none of it. A test that looked only under
    its own root would skip on every worktree even on the machine that has the artifact — the
    exact defect `tests/test_i3_crash_gate.py` shipped, where a helper resolved the data root
    and the test then read from the repo anyway, so the check was dead on any worktree while
    still reporting a pass. Same candidate order as
    `valuation.studies.optionable_universe._data_root`.
    """
    rel = os.path.join("free_analysis", "SC1B_CLUSTER_BY_ITEM.json")
    for root in (os.environ.get("VALQUO_DATA_ROOT"),
                 os.path.join(ROOT, "data"),
                 r"C:\Users\donni\Downloads\valuation-tool\data"):
        if root and os.path.exists(os.path.join(root, rel)):
            return os.path.join(root, rel)
    return ""


def _card(**over) -> dict:
    """A well-formed card. Overridable field by field so each test moves ONE thing."""
    base = {
        "item": "SC-1b",
        "register": "PREREG_sc1b_cluster_by_item.md",
        "register_commit": "329402d",
        "corpus_pinned_to": "8e2e9fe",
        "verdict": "CALIBRATED-IN-THE-LARGE",
        "n": 43,
        "n_clusters": 15,
        "gap": -0.05,
        "half_width": 0.1432030129124821,
        "bar": 0.15,
        "detection_threshold_50pct": 0.12044583109484722,
        "cluster_adjusted_detection_threshold_50pct": 0.14471665442688625,
        "may_not_be_quoted_as": ["validation of any individual prior"],
        "source": "data/free_analysis/SC1B_CLUSTER_BY_ITEM.json",
        "source_sha256": "0" * 64,
    }
    base.update(over)
    return base


def _write(d: str, card: dict) -> str:
    p = os.path.join(d, "card.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(card, f)
    return p


def _at_card(path):
    """Point the module's default card at `path` and drop the memo. Returns a restorer."""
    was = RR.CALIBRATION_CARD
    RR.CALIBRATION_CARD = path
    RR.reset_calibration_cache()

    def restore():
        RR.CALIBRATION_CARD = was
        RR.reset_calibration_cache()
    return restore


# =======================================================================================
# SC-1 — derived, never typed
# =======================================================================================
def test_the_count_moves_with_the_card():
    """The whole reason it is not a literal: the scored count grows as the record grows."""
    with tempfile.TemporaryDirectory() as d:
        a = RR.calibration(card_path=_write(d, _card(n=43)))
        assert a["n"] == 43, a
        b = RR.calibration(card_path=_write(d, _card(n=61, n_clusters=22)))
        assert b["n"] == 61 and b["n_clusters"] == 22, b


def test_no_measured_calibration_value_is_typed_into_the_source():
    """No measured figure may appear as a literal in the module.

    Read from the SYNTAX TREE rather than grepped, because this module's own prose quotes the
    values the rule forbids — the comment-versus-code defect this repository has paid for
    repeatedly, most recently in `MA49`.
    """
    tree = ast.parse(open(MODULE, encoding="utf-8").read())
    banned = {0.1432030129124821, 0.1432, 0.15, 43.0, 15.0, 0.05,
              0.12044583109484722, 0.14471665442688625}
    # The two hurdle constants are DECLARED withheld operands and are MB38's, not this
    # item's; they have their own test and are exempted here by identity, not by value.
    allowed = {RR.HEADLINE_STATISTIC, RR.PLACEBO_FLOOR}
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
                and not isinstance(node.value, bool):
            v = float(node.value)
            if v in allowed:
                continue
            if v in banned:
                bad.append((node.lineno, node.value))
    assert not bad, ("a measured calibration value is typed into the module: "
                     + ", ".join("line %d: %r" % b for b in bad))


def test_the_verdict_is_a_word_this_page_owns_and_not_the_cards_raw_string():
    with tempfile.TemporaryDirectory() as d:
        c = RR.calibration(card_path=_write(d, _card()))
        assert c["verdict_phrase"] == RR.CALIBRATION_PHRASE["CALIBRATED-IN-THE-LARGE"]
        assert c["verdict_phrase"] != c["verdict"], c


def test_the_direction_is_derived_from_the_sign_of_the_gap():
    """A negative gap means the record predicted a thing LESS often than it happened."""
    with tempfile.TemporaryDirectory() as d:
        low = RR.calibration(card_path=_write(d, _card(gap=-0.05)))
        high = RR.calibration(card_path=_write(d, _card(gap=+0.05)))
        assert "LESS often" in low["direction"], low["direction"]
        assert "MORE often" in high["direction"], high["direction"]
        assert low["direction"] != high["direction"]
        # ...and neither reads as a market view. "Pessimistic" is the technical word and it
        # is deliberately not used two clicks from a performance card.
        for c in (low, high):
            assert "pessimist" not in c["direction"].lower(), c["direction"]


def test_a_gap_below_the_designs_own_resolution_is_hedged_and_one_above_it_is_not():
    with tempfile.TemporaryDirectory() as d:
        small = RR.calibration(card_path=_write(d, _card(gap=-0.05)))
        big = RR.calibration(card_path=_write(d, _card(gap=-0.90)))
        assert small["below_detection"] and small["direction"].startswith("mildly"), small
        assert not big["below_detection"] and not big["direction"].startswith("mildly"), big


# =======================================================================================
# SC-1 — fail closed, in every direction
# =======================================================================================
def test_it_fails_closed_when_the_card_is_missing():
    c = RR.calibration(card_path=os.path.join(tempfile.gettempdir(), "no_such_card.json"))
    assert not c["available"] and c["reason"], c
    assert "half_width_text" not in c, "a refusal leaked a figure"


def test_it_fails_closed_when_the_card_is_malformed():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bad.json")
        open(p, "w", encoding="utf-8").write("{ this is not json")
        c = RR.calibration(card_path=p)
        assert not c["available"] and c["reason"], c


def test_it_fails_closed_on_a_verdict_this_page_has_no_word_for():
    """An unrecognised verdict is a study this page has not been taught to describe."""
    with tempfile.TemporaryDirectory() as d:
        c = RR.calibration(card_path=_write(d, _card(verdict="SPECTACULARLY-VINDICATED")))
        assert not c["available"], c
        assert "vocabulary" in c["reason"], c["reason"]


def test_it_fails_closed_when_the_verdict_disagrees_with_its_own_interval():
    """The comparison is re-derived, so a card cannot publish a verdict its numbers refute."""
    with tempfile.TemporaryDirectory() as d:
        c = RR.calibration(card_path=_write(d, _card(half_width=0.99)))
        assert not c["available"], c
        assert "disagrees" in c["reason"], c["reason"]


def test_a_refusal_never_carries_a_number():
    with tempfile.TemporaryDirectory() as d:
        for bad in (_card(verdict="NOPE"), _card(half_width=0.99), _card(n=0)):
            c = RR.calibration(card_path=_write(d, bad))
            assert not c["available"], c
            for k in ("n", "half_width_text", "bar_text", "n_clusters"):
                assert k not in c, "a refusal leaked %s" % k
            assert not RR.contains_figure(c["reason"]), c["reason"]


# =======================================================================================
# SC-1 — the guard's second exemption, on MB38's exact terms
# =======================================================================================
def test_the_exemption_admits_the_two_rendered_strings_and_nothing_else():
    """The hole is exactly as wide as the section, and every near miss on it still fires."""
    with tempfile.TemporaryDirectory() as d:
        r = _at_card(_write(d, _card()))
        try:
            exempt = RR.derived_calibration_figures()
            assert exempt == frozenset({"0.1432", "0.15"}), sorted(exempt)
            for ok in ("0.1432", "0.15"):
                assert not RR.contains_figure(ok), ok
            # A percentage is a performance figure whatever its digits; naming it as a
            # statistic brings it straight back under the rule; and a different number is a
            # different number.
            for near in ("0.1432%", "t 0.1432", "10.1432", "0.15x", "0.150", "IC 0.15",
                         "$0.15", "0.1433"):
                assert RR.contains_figure(near), "the exemption let %r through" % near
        finally:
            r()


def test_the_exemption_is_empty_when_the_card_cannot_be_read():
    """FAIL CLOSED. The figure must come back UNDER the rule, not merely stop rendering."""
    r = _at_card(os.path.join("data_export", "no_such_calibration_card.json"))
    try:
        assert RR.derived_calibration_figures() == frozenset()
        assert RR.contains_figure("0.1432"), "the half-width stayed exempt with no card"
        assert RR.contains_figure("0.15"), "the ceiling stayed exempt with no card"
    finally:
        r()


def test_withhold_is_not_given_the_calibration_exemption():
    """`withhold()` redacts text this page does not own. It gets no exemption, ever."""
    with tempfile.TemporaryDirectory() as d:
        r = _at_card(_write(d, _card()))
        try:
            got = RR.withhold("a logged row that happens to say 0.1432 and 0.15")
            assert RR.WITHHELD in got, got
            assert "0.1432" not in got, got
        finally:
            r()


def test_the_two_exemptions_fail_closed_independently():
    """A card that goes missing must not withdraw MB38's hurdle, and vice versa."""
    r = _at_card(os.path.join("data_export", "no_such_calibration_card.json"))
    try:
        m = RR.multiplicity()
        if m.get("available") and m.get("hurdle_text"):
            assert not RR.contains_figure(m["hurdle_text"]), \
                "losing the calibration card withdrew the hurdle's exemption"
    finally:
        r()


# =======================================================================================
# SC-1 — the card is derived from the artifact, and cannot drift from it
# =======================================================================================
def test_the_committed_card_matches_the_artifact_when_the_artifact_is_present():
    """ONE AUTHORITY. Where the study's artifact is on disk, the committed card must be
    exactly what re-deriving it produces — so a card edited by hand, or left behind by an
    older run, fails here rather than quietly publishing a stale verdict.

    Skipped, loudly, where the artifact is absent: `data/` is gitignored and never ships, so
    CI and the service legitimately do not have it. The card is the published fact there.
    """
    from scripts import publish_calibration_card as P

    art = _artifact_path()
    card = os.path.join(ROOT, P.CARD)
    assert os.path.exists(card), "the calibration card is not committed"
    if not art:
        print("       (artifact absent -- drift check skipped, card is the published fact)")
        return
    fresh = P.text(P.build(art))
    on_disk = open(card, encoding="utf-8").read()
    assert fresh == on_disk, ("data_export/calibration_card.json has drifted from "
                              + P.ARTIFACT + " -- re-run scripts/publish_calibration_card.py")


def test_the_card_names_the_artifact_it_came_from():
    card = json.load(open(os.path.join(ROOT, "data_export", "calibration_card.json"),
                          encoding="utf-8"))
    assert card["source"].endswith("SC1B_CLUSTER_BY_ITEM.json"), card["source"]
    assert re.fullmatch(r"[0-9a-f]{64}", card["source_sha256"]), card["source_sha256"]


def test_the_publisher_copies_and_never_computes():
    """Every published value must be present in the artifact. Nothing is derived here."""
    from scripts import publish_calibration_card as P

    art = _artifact_path()
    if not art:
        print("       (artifact absent -- copy check skipped)")
        return
    raw = json.load(open(art, encoding="utf-8"))
    card = P.build(art)
    for key, path in P.FIELDS:
        cur = raw
        for k in path:
            cur = cur[k]
        assert card[key] == cur, (key, card[key], cur)


# =======================================================================================
# SC-1 — what reaches the page
# =======================================================================================
def _page(**over) -> str:
    from valuation.saas.app_saas import create_saas_app
    import valuation.saas.app_saas as A

    app = create_saas_app()
    with app.test_request_context():
        from flask import render_template
        rec = RR.record()
        rec.update(over)
        return render_template("research.html", work_url="/work", **rec)


def test_the_limits_travel_with_the_claim():
    """A calibration verdict published without its limits is the one claim here nobody could
    check: it is an AGGREGATE, the gap is below the design's own resolution, and the pairs are
    picked by a rule whose miss rate has never been measured."""
    c = RR.calibration()
    assert c["available"], c["reason"]
    limit = c["limit"]
    assert "AGGREGATE" in limit, limit
    assert "coin-flip" in limit or "coin flip" in limit, limit
    assert "miss rate" in limit, limit


def test_the_page_carries_the_studys_own_may_not_be_quoted_list():
    """Carried from the artifact rather than re-worded, so the caveat and the claim cannot
    drift apart on the one page where that would matter most."""
    c = RR.calibration()
    assert c["available"], c["reason"]
    assert c["may_not_be_quoted_as"], c
    html = _page()
    assert "What this may not be quoted as" in html, "the list is not rendered"
    for q in c["may_not_be_quoted_as"]:
        head = q.split("--")[0].strip()[:40]
        assert head in html, head


def test_the_section_disappears_when_the_card_cannot_be_read():
    """Fail closed on the PAGE, not just in the payload."""
    r = _at_card(os.path.join("data_export", "no_such_calibration_card.json"))
    try:
        html = _page(calibration=RR.calibration())
        assert RR.CALIBRATION_HEADING not in html, "the section rendered without a card"
    finally:
        r()
    html = _page()
    assert RR.CALIBRATION_HEADING in html, "the section vanished with a good card"


def test_the_section_renders_and_the_two_figures_are_the_derived_ones():
    c = RR.calibration()
    html = _page()
    assert c["half_width_text"] in html and c["bar_text"] in html, (c, len(html))
    assert c["verdict_phrase"] in html, c["verdict_phrase"]
    assert str(c["n"]) in html


def test_the_template_holds_no_copy_of_the_calibration_copy():
    """Every sentence is a constant in the module; the template renders and owns nothing."""
    tpl = open(TEMPLATE, encoding="utf-8").read()
    i = tpl.find("{% if calibration.available %}")
    j = tpl.find("{% endif %}", tpl.find("What this may not be quoted as"))
    assert i > 0 and j > i
    section = tpl[i:j]
    for sentence in (RR.CALIBRATION_LEDE[:40], RR.CALIBRATION_LIMIT[:40],
                     RR.CALIBRATION_METHOD[:40]):
        assert sentence not in section, "the template carries its own copy: %r" % sentence


# =======================================================================================
# S3-I7 — the declared-book shelf, against S3-I1's real format
# =======================================================================================
#
# A declaration is `DECL_<book>.md` carrying exactly ONE fenced ```json block, committed
# ALONE before the book's first fill (`valuation/edge/fleet.py`). These fixtures are built
# from the harness's own `declaration_template` shape rather than from a format this page
# invented, because a shelf that parses something the harness does not emit renders nothing
# forever and passes every test it wrote for itself.
DECL_BODY = """# DECL %(book)s

**Committed ALONE, before this book's first fill.**

```json
%(json)s
```
"""


def _decl(book: str, *, horizon=None, fills=None, blocks: int = 1) -> str:
    hz = {"expected_fills_per_month": 30, "min_effect": 0.1, "sigma": 1.0, "rho": 3.0,
          "alpha": 0.05, "fills_needed": fills if fills is not None else 60,
          "earliest_honest_read": horizon if horizon is not None else "TODO YYYY-MM-DD"}
    d = {"book": book, "domain": "options", "hypothesis_class": "cost",
         "entry_rule": "TODO", "structure": {}, "universe": "TODO", "sizing": "TODO",
         "concurrency_cap": 10, "side": "long", "records_schema": [],
         "verdict_horizon": hz, "verdict_grammar": ["A", "B"],
         "trial": {"domain": "options", "charged_at": "first_verdict_read"},
         "o11_sentence": "O11 binds this book."}
    body = DECL_BODY % {"book": book, "json": json.dumps(d, indent=2)}
    if blocks == 2:
        body += "\n```json\n" + json.dumps(d, indent=2) + "\n```\n"
    return body


def _fleet_dir(d: str, files: dict) -> str:
    for name, body in files.items():
        with open(os.path.join(d, name), "w", encoding="utf-8") as f:
            f.write(body)
    return d


def test_an_empty_fleet_renders_an_honest_sentence_rather_than_hiding():
    """A shelf that appeared only once it had something to show would be evidence of nothing.

    AMENDED AT THE DECLARATION CEREMONY, 2026-08-24. The second half used to assert that the
    LIVE page reads *"No books have been declared yet"* — true on the day it was written and
    made false by the ceremony, which declared seventeen books. **The behaviour is unchanged
    and correct; what was wrong was pinning a transient state to the live page.** The empty
    case is still tested, on a controlled root where it can be constructed rather than waited
    for, and the live page is now asserted to render the shelf and to be CONSISTENT with
    whatever the fleet actually holds — which is the property that does not expire.
    """
    with tempfile.TemporaryDirectory() as d:
        s = RR.declared_books(root=d)
        assert s["available"] and s["empty"] and s["n"] == 0, s
        assert "No books have been declared yet" in s["empty_note"], s["empty_note"]

    live = RR.declared_books()
    html = _page()
    assert RR.DECL_HEADING in html, "the shelf is hidden"
    # The empty sentence appears if and only if the fleet is empty. Both directions, so this
    # cannot rot again in either state.
    assert ("No books have been declared yet" in html) == live["empty"], live["n"]


def test_a_draft_is_not_a_declaration():
    """THE ONE THAT WOULD HAVE PUBLISHED A FALSE CLAIM.

    The scout lane carries twenty `DECL_DRAFT_*.md` files whose own text says they are *to be
    committed ALONE ... before any fleet order is placed* — i.e. awaiting the very commit that
    would make them declarations. A glob of `DECL_*.md` lists all twenty as declared books on
    a page whose entire claim is that these things were committed in advance.
    """
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {
            "DECL_f1_fill_ab.md": _decl("f1_fill_ab"),
            "DECL_DRAFT_f1_fill_ab.md": "# DECL DRAFT — F-1\n\nprose, no block\n",
            "DECL_DRAFT_f2_menu_gate.md": "# DECL DRAFT — F-2\n\nprose, no block\n",
        })
        s = RR.declared_books(root=d)
        assert s["n"] == 1, [b["file"] for b in s["books"]]
        assert s["books"][0]["file"] == "DECL_f1_fill_ab.md"
        assert s["drafts_excluded"] == 2, s["drafts_excluded"]
        assert RR.DECL_DRAFT_PREFIX == "DECL_DRAFT_"


def test_the_horizon_comes_from_the_declared_block_and_never_from_the_prose():
    """`preregistrations()` records what scraping costs: a register was given a registration
    date of 1998-01-01 out of its own contents."""
    with tempfile.TemporaryDirectory() as d:
        body = _decl("a", horizon="2027-08-20")
        body = body.replace("**Committed ALONE",
                            "We began drafting this on 1998-01-01.\n\n**Committed ALONE")
        _fleet_dir(d, {"DECL_a.md": body})
        b = RR.declared_books(root=d)["books"][0]
        assert b["horizon"] == "2027-08-20", b
        assert "1998" not in str(b["horizon"]), b


def test_a_placeholder_horizon_is_not_published_as_a_date():
    """The harness's own template ships `earliest_honest_read` as the literal string
    `TODO YYYY-MM-DD`. Rendering it publishes a to-do on a public page."""
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": _decl("a")})           # template default placeholder
        b = RR.declared_books(root=d)["books"][0]
        assert b["horizon"] is None and b["horizon_labelled"] is False, b
        # ...and the honest answer for a book whose horizon is an event count still shows.
        assert b["fills_needed"] == 60, b


def test_two_json_blocks_are_refused_rather_than_merged():
    """The harness refuses two blocks because picking one chooses the rules after the fact.
    A page that merged them would be doing exactly that on the reader's behalf."""
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": _decl("a", horizon="2027-08-20", blocks=2)})
        b = RR.declared_books(root=d)["books"][0]
        assert b["horizon"] is None, b
        assert b["fills_needed"] is None, b


def test_a_declaration_with_no_block_at_all_is_listed_without_inventing_fields():
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": "# DECL a\n\nprose only, no fenced block\n"})
        s = RR.declared_books(root=d)
        assert s["n"] == 1
        b = s["books"][0]
        assert b["horizon"] is None and b["fills_needed"] is None, b
        assert b["status"] == RR.DECLARED


def test_a_status_is_taken_from_the_harness_and_never_inferred_from_the_calendar():
    """Reaching a horizon is not reading a verdict. Only the second one charges a trial."""
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": _decl("a", horizon="2020-01-01")})
        b = RR.declared_books(root=d, today="2026-08-23")["books"][0]
        assert b["status"] == RR.DECLARED, b
        assert b["status"] != RR.VERDICT_READ, "a passed horizon was read as a verdict"


def test_a_closed_window_with_no_verdict_is_flagged_and_not_rolled_forward():
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": _decl("a", horizon="2020-01-01"),
                       "DECL_b.md": _decl("b", horizon="2099-01-01")})
        by = {b["file"]: b for b in RR.declared_books(root=d, today="2026-08-23")["books"]}
        assert by["DECL_a.md"]["overdue"] is True, by["DECL_a.md"]
        assert by["DECL_b.md"]["overdue"] is False, by["DECL_b.md"]


def test_the_commit_and_the_status_read_as_unrecorded_without_the_harness():
    """A file cannot contain its own commit hash, and the harness's records live under the
    gitignored `data/`, so both come from `valuation.edge.fleet` or not at all. Until `S3-I1`
    lands there is nothing to import, and the shelf says so instead of guessing."""
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_a.md": _decl("a", horizon="2099-01-01")})
        s = RR.declared_books(root=d)
        assert s["harness_available"] is (RR._fleet() is not None)
        b = s["books"][0]
        if not s["harness_available"]:
            assert b["commit"] == "" and b["commit_known"] is False, b
            assert b["status"] == RR.DECLARED and b["recorded"] is False, b
            assert s["record_available"] is False, s


def test_the_harness_import_never_raises():
    """`_fleet()` is a probe, not a dependency: the page must render before `S3-I1` lands."""
    assert RR._fleet() is None or hasattr(RR._fleet(), "parse_declaration")


def test_the_shelf_publishes_no_performance_figure():
    """MB38's gate governs here exactly as it governs the rest of the page."""
    with tempfile.TemporaryDirectory() as d:
        _fleet_dir(d, {"DECL_f1_fill_ab.md": _decl("f1_fill_ab", horizon="2027-08-20")})
        s = RR.declared_books(root=d)
        flat = []
        for b in s["books"]:
            flat.extend(str(v) for v in b.values())
        flat.extend(str(v) for v in s.values() if isinstance(v, str))
        for t in flat:
            assert not RR.contains_figure(t), "the shelf published a figure: %r" % t


def test_a_commit_hash_cannot_trip_the_figure_guard():
    """Hex has no `.`, no `$` and no `x`, so a hash cannot look like a figure. Asserted rather
    than assumed, because the shelf renders one per row."""
    for h in ("329402d", "8e2e9fe", "0000000", "1234567", "9876543", "deadbee", "1e2e3e4"):
        assert not RR.contains_figure(h), h
        assert RR.withhold(h) == h, h


def test_a_title_from_a_declaration_is_withheld_like_any_other_borrowed_text():
    """The documents are not this page's copy, so their headings go through `withhold()`."""
    with tempfile.TemporaryDirectory() as d:
        body = _decl("a").replace("# DECL a", "# The book that returned +7.17%/yr")
        _fleet_dir(d, {"DECL_a.md": body})
        b = RR.declared_books(root=d)["books"][0]
        assert RR.WITHHELD in b["title"], b["title"]
        assert "7.17" not in b["title"], b["title"]


def test_the_status_vocabulary_is_closed_and_every_status_has_a_blurb():
    """CLOSED added 2026-08-24 at the declaration ceremony, and this literal is why it had to
    be a deliberate act: the vocabulary is pinned here, so widening it fails until the same
    commit widens both. `MA13`'s idiom.

    THE DEFECT IT CLOSES WAS LIVE AND PUBLIC. The harness has always been able to write a
    `close` record — line 603 below already admitted `"close"` as a valid harness kind — and
    the vocabulary had no word for it, so a book closed on the record rendered as **FILLING**:
    *"the record it will be judged on is still filling"*, said of a book that will never fill
    again. The day-1 test-book, closed with a zero-charge row, is exactly that case.
    """
    assert set(RR.DECL_STATUSES) == {RR.DECLARED, RR.FILLING, RR.VERDICT_READ, RR.CLOSED}
    for st in RR.DECL_STATUSES:
        assert RR.DECL_STATUS_BLURB.get(st), st
    # The kinds the status is derived from are the harness's, not invented here.
    kinds = {k for names, _ in RR._DECL_KIND_STATUS for k in names}
    assert kinds <= {"selfcheck", "fill", "refusal", "meter_read", "close"}, kinds


def test_the_rendered_page_still_carries_no_performance_figure():
    """The page's own rule, re-run with both new sections on it. Not a duplicate of the
    research-page suite's version: that one runs against whatever state the repo is in, and
    this one is the reason to re-run it after adding two sections that render figures."""
    offenders = []
    for i, line in enumerate(_page().splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("--", ".", "#", "@", "{", "}")) or ":" in s.split(">")[0]:
            continue
        if RR.contains_figure(s):
            offenders.append("  line %d: %s" % (i, s[:110]))
    assert not offenders, "\n".join(offenders[:10])


def test_the_deliberately_not_here_section_counts_the_exemptions_correctly():
    """The page states which numbers are not exceptions to its own rule. Adding two more
    made the old singular sentence false, and a page that contradicts itself about its
    publishing rule is worse than one that never stated it."""
    html = _page()
    assert "One number above is not an exception" not in html, \
        "the page still claims a single exemption while rendering three figures"
    assert "not exceptions to that" in html, "the replacement sentence is gone"


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    names = re.findall(r"^def (test_\w+)", src, re.M)
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, ", ".join(dupes)
    live = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(live) == len(names), (len(names), len(live))


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
    print("\n" + str(passed) + "/" + str(len(tests))
          + " SC-1 calibration + S3-I7 shelf tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
