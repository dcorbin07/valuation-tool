"""SC-4 — "the record this week": the denominator page made temporal. Offline, deterministic.

    python tests/test_record_this_week.py

WHAT IS ACTUALLY AT RISK HERE, and it is not the arithmetic.

1. **A CHANGELOG BECOMING A PROGRESS REPORT.** Every element on this block is a count, a date
   or a verdict word, and each one is individually harmless. Assembled and summarised they are
   one careless edit away from "the record is getting stronger", which is a performance claim
   wearing a process claim's clothes. `WEEK_BANNED` exists for that edit, and it is asserted
   against the RENDERED section because rendering is where copy leaks (`MA28-CARD-UI`).

2. **A DERIVED NUMBER GOING STALE AS A LITERAL.** The item's whole point is motion, so any
   count typed into the source or the template is wrong within days — the audit that proposed
   `MB38` quoted a trial count that was already stale when it was executed.

3. **THE GUARD'S EXEMPTION WIDENING.** `MB38` opened a one-string hole in the figure guard so
   the hurdle could be published. This block renders up to six. The hole must stay exactly as
   wide as the page and must shut completely when the register cannot be read — a property
   this item BROKE on its first cut and `MB38`'s own test caught.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

import ast                                            # noqa: E402
import datetime as dt                                 # noqa: E402
import html as _htmlmod                               # noqa: E402
import re                                             # noqa: E402

from valuation.config import CONFIG                   # noqa: E402

CONFIG.private_mode = False

from valuation.edge import research_log as RL         # noqa: E402
from valuation.edge.statistics import hlz_hurdle      # noqa: E402
from valuation.saas.app_saas import create_saas_app   # noqa: E402
from valuation.web import research_record as RR       # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True
URL = "/work/research"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE = os.path.join(ROOT, "valuation", "web", "research_record.py")
TEMPLATE = os.path.join(ROOT, "valuation", "web", "templates", "research.html")


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _page():
    with APP.test_client() as c:
        r = c.get(URL)
    assert r.status_code == 200, f"{URL} returned {r.status_code}"
    return _htmlmod.unescape(r.get_data(as_text=True))


def _section(page=None):
    """Just SC-4's own section of the rendered page.

    SCOPED, AND THE SCOPING IS LOAD-BEARING RATHER THAN TIDY. Measured: run against the whole
    page `week_violations` returns fifteen hits, every one of them in a log row or a paragraph
    belonging to another item. Policing another item's prose is not this guard's job and would
    be switched off inside a week.
    """
    p = page if page is not None else _page()
    i = p.index(RR.WEEK_HEADING)
    return p[i:p.index("</section>", i)]


def _text(html):
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]+>", " ", html))


# --------------------------------------------------------------------- it is on the page
def test_the_section_renders_and_every_sentence_comes_from_the_module():
    """Split into LEVEL copy and MOTION copy, which is the distinction the block is built on.

    The level sentences render on every week — a standing count is true whether or not
    anything happened. The verdict note is about verdicts, so it renders only when there were
    some. Asserting it unconditionally is what a quiet week caught.
    """
    sec = _section()
    for name in ("WEEK_HEADING", "WEEK_LEDE", "WEEK_HURDLE_NOTE", "WEEK_FLOOR_NOTE",
                 "WEEK_NOT_A_RESULT"):
        assert getattr(RR, name) in sec, f"{name} is not rendered verbatim on every week"
    if RR.weekly()["quiet"]:
        assert RR.WEEK_QUIET in sec, "a quiet week rendered no quiet sentence"
        assert RR.WEEK_VERDICT_NOTE not in sec, "a quiet week talked about verdicts"
    else:
        assert RR.WEEK_VERDICT_NOTE in sec, "WEEK_VERDICT_NOTE is not rendered verbatim"
        assert RR.WEEK_QUIET not in sec, "a busy week claimed to be quiet"


def test_the_template_holds_no_copy_of_its_own():
    """A sentence living in both places is two versions of the truth."""
    tmpl = _src(TEMPLATE)
    for name in ("WEEK_HEADING", "WEEK_LEDE", "WEEK_HURDLE_NOTE", "WEEK_VERDICT_NOTE",
                 "WEEK_FLOOR_NOTE", "WEEK_QUIET", "WEEK_NOT_A_RESULT"):
        text = getattr(RR, name)
        for chunk in (text[:40], text[-40:]):
            assert chunk not in tmpl, f"{name} is retyped in the template"


# --------------------------------------------------------------------- the posture line
def test_the_rendered_section_carries_no_banned_phrasing():
    bad = RR.week_violations(_section())
    assert not bad, f"banned phrasing reached the rendered section: {bad}"


def test_the_banned_check_is_not_vacuous():
    """It must fire on all three families and on a named statistic."""
    for planted in ("the record is on track",
                    "we expect the next quarter to confirm it",
                    "the book beat the market again",
                    "this proves the edge is real",
                    "a remarkable week for a world-class process",
                    "the t-statistic moved this week",
                    "alpha improved"):
        assert RR.week_violations(planted), f"the guard missed: {planted!r}"


def test_the_guard_does_not_forbid_the_honest_sentence():
    """THE GUARD MUST NOT DEFEAT THE ITEM IT GUARDS.

    The floor paragraph's job is to say that nothing has moved YET and that this is NOT proof
    it will hold. A tuple that banned "proof" or "will" would forbid the most careful sentence
    in the block and leave only the flattering half of it.
    """
    for allowed in ("Not proof that they will hold afterwards.",
                    "nothing has changed yet, which is a much weaker statement",
                    "three entries were rejected and five were null",
                    "the bar rose because more things were tried"):
        assert not RR.week_violations(allowed), (
            f"the guard forbids an honest sentence: {allowed!r} -> {RR.week_violations(allowed)}")


def test_the_rendered_section_contains_no_performance_figure():
    """The item's kill condition, asserted where it matters: the served HTML."""
    for line in _text(_section()).splitlines():
        assert not RR.contains_figure(line), f"a figure reached the page: {line.strip()!r}"


def test_the_withheld_constants_never_reach_the_page():
    """The operands of every comparison this page makes stay off it."""
    page = _page()
    for const in (RR.HEADLINE_STATISTIC, RR.PLACEBO_FLOOR, RR.FLOOR_FLIP_MARGIN_OVER_SE):
        for form in (repr(const), "%.4f" % const, "%.6f" % const):
            assert form not in page, f"{form} reached the page"


def test_the_section_names_no_statistic():
    """It may say a verdict LANDED and give the WORD. Naming the quantity is how a comparison
    gets onto the page without a number attached to it."""
    low = _text(_section()).lower()
    for stat in RR.WEEK_BANNED_STATISTICS:
        assert stat not in low, f"the section names a statistic: {stat}"


def test_it_says_it_is_not_a_result():
    """The S28 / MA29 reporting-infrastructure class, said on the surface rather than only in
    the handoff: no hypothesis, no threshold, no verdict of its own."""
    low = _text(_section()).lower()
    assert "none of this is a result" in low, "the section does not disclaim being a result"
    assert "no hypothesis" in low and "no threshold" in low, low[-400:]


# --------------------------------------------------------------------- the numbers
def test_every_count_renders_beside_its_own_domain_and_hurdle():
    """MB26's two-denominators rule. A week containing entries from both books must never
    show one pooled count or one pooled bar."""
    w = RR.weekly()
    assert w["available"], w["reason"]
    sec = _text(_section())

    # THE RULE ITSELF FIRST. Ordered ahead of the shape checks below deliberately: a mutation
    # that appended a pooled book was caught only by the key-ordering assertion raising, which
    # left the assertion that actually encodes MB26's rule unexercised. A guard that fires for
    # an incidental reason is a guard nobody has tested.
    # Computed from the REGISTER, not from `w["domains"]`. A mutation that appends a pooled
    # book to that list would otherwise move the very total this assertion is looking for, and
    # the check would sail past the thing it exists to catch.
    live = RL.detail()["by_domain"]
    pooled = "%.4f" % hlz_hurdle(sum(int(v) for v in live.values()))
    assert pooled not in {d["hurdle_after"] for d in w["domains"]}, (
        "the pooled bar coincides with a per-book one, so this check is vacuous today")
    assert pooled not in sec, "a POOLED bar reached the page"

    keys = [d["key"] for d in w["domains"]]
    assert set(keys) <= {"equity", "options", "infra"}, keys
    assert set(keys) >= {"equity", "options"}, keys
    assert keys == sorted(keys, key=["equity", "options", "infra"].index)
    for d in w["domains"]:
        assert d["label"] in sec, f"{d['key']} has no row of its own"
        assert d["hurdle_after"] in sec, f"{d['key']} renders no bar of its own"


def test_the_hurdles_are_arithmetic_on_the_counts():
    w = RR.weekly()
    live = RL.detail()["by_domain"]
    for d in w["domains"]:
        assert d["now"] == int(live[d["key"]]), d
        assert d["before"] == d["now"] - d["charged"], d
        assert d["hurdle_after"] == "%.4f" % hlz_hurdle(d["now"]), d
        if d["hurdle_before_defined"]:
            assert d["hurdle_before"] == "%.4f" % hlz_hurdle(d["before"]), d


def test_the_before_count_is_the_sum_of_the_windows_own_rows():
    """The diff is not an estimate: N before the window is N now minus exactly the trials the
    window's own rows charge, so the two ends cannot drift."""
    w = RR.weekly(today=dt.date(2026, 8, 19))
    start = dt.date.fromisoformat(w["start"])
    end = dt.date.fromisoformat(w["end"])
    charged = {}
    for r in RL.rows():
        try:
            d = dt.date.fromisoformat((r.get("date") or "").strip())
        except Exception:                              # noqa: BLE001
            continue
        if start <= d <= end:
            k = (r.get("domain") or "").strip().lower()
            charged[k] = charged.get(k, 0) + int(r.get("n_trials") or 0)
    for d in w["domains"]:
        assert d["charged"] == charged.get(d["key"], 0), d


def test_a_below_floor_before_count_is_stated_rather_than_floored_silently():
    """`hlz_hurdle` floors at 2, so a "before" of 0 or 1 would render a bar that never
    existed. It must be reported as undefined instead."""
    w = RR.weekly(today=dt.date(2026, 8, 19), days=3650)
    below = [d for d in w["domains"] if d["before"] < 2]
    assert below, "the fixture failed to drive a count below the floor"
    for d in below:
        assert not d["hurdle_before_defined"], d
        assert d["hurdle_before"] is None, d


def test_the_floor_flip_count_is_derived_and_reproduces_the_recorded_one():
    """MB31 reports 247 from the banked draws. It is DERIVED here from the draw's own recorded
    margin ratio through the ONE hurdle definition, so the two agree by construction rather
    than by transcription — and `data/` is gitignored, so re-reading MB31's artifact at render
    time is not available in any case."""
    n = RR.floor_flip_n()
    assert n == 247, n
    assert hlz_hurdle(n) > RR.FLOOR_FLIP_MARGIN_OVER_SE
    assert hlz_hurdle(n - 1) <= RR.FLOOR_FLIP_MARGIN_OVER_SE
    assert str(n) not in _module_code_without_docstrings(), "the flip count is typed"


def test_the_floor_headroom_is_arithmetic_and_the_due_word_follows_it():
    w = RR.weekly()
    f = w["floor"]
    assert f["n"] == int(RL.detail()["by_domain"]["equity"])
    assert f["headroom"] == max(0, f["flip_n"] - f["n"])
    assert f["due"] is (f["n"] >= f["flip_n"])


def _sc4_section_of_template():
    """Just SC-4's own markup.

    SCOPED, AND THE FIRST CUT WAS NOT — it scanned the whole template and failed against a
    correct tree because the stylesheet carries `margin:0 0 18px` and the infrastructure count
    had reached 18. Third time this family has been met in three sessions: the guard has to
    look at the thing the item owns, or it reports on its neighbours.
    """
    t = _src(TEMPLATE)
    i = t.index("---- SC-4")
    return t[i:t.index("{% endif %}", t.index("{% if weekly.available %}", i))]


def _module_code_without_docstrings():
    tree = ast.parse(_src(MODULE))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(ast.fix_missing_locations(tree))


def test_no_count_from_this_block_is_typed_into_the_source_or_the_template():
    w = RR.weekly()
    code = _module_code_without_docstrings()
    tmpl = _sc4_section_of_template()
    live = {str(w["rows"]), str(w["charged"])}
    for d in w["domains"]:
        live |= {str(d["now"]), str(d["before"]), d["hurdle_after"]}
        if d["hurdle_before"]:
            live.add(d["hurdle_before"])
    # DECLARED DISPLAY PARAMETERS ARE NOT DERIVED COUNTS, and excluding them by identity is
    # the whole point. Found by the clock rolling past midnight mid-session: the
    # infrastructure book's "before" count reached 12, which is also the row cap, and the
    # check failed against a correct tree. A stated limit follows — a genuine typed count that
    # happens to equal one of these two is not caught — and it is the right trade, because the
    # alternative is a guard that fails on ordinary days and gets switched off.
    display_parameters = {str(RR.WEEK_MAX_ROWS), str(RR.WEEK_DAYS)}
    # ...and 0 and 1, which on a quiet week are legitimate derived counts and are also what
    # every `max(0, ...)` and slice bound in the module is written with. A typed 0 is not a
    # count that can go stale, which is the only thing this check exists to catch.
    live -= display_parameters | {"0", "1"}
    assert live, "every live count coincided with a display parameter; this check is vacuous"
    for v in live:
        # Standalone-number match, not substring — see `_typed` in test_research_page.py for
        # why: a two-digit count is a substring of half the decimals in the tree.
        pat = r"(?<![\d.\-+])" + re.escape(v) + r"(?![\d.])"
        assert not re.search(pat, code), f"{v} is typed into research_record.py"
        assert not re.search(pat, tmpl), f"{v} is typed into the template"


# --------------------------------------------------------------------- behaviour
def test_the_window_moves_with_the_clock():
    a = RR.weekly(today=dt.date(2026, 8, 19))
    b = RR.weekly(today=dt.date(2026, 8, 12))
    assert a["start"] == "2026-08-13" and a["end"] == "2026-08-19", a
    assert b["start"] == "2026-08-06" and b["end"] == "2026-08-12", b
    assert a["rows"] != b["rows"], "the window did not actually select different rows"


def test_a_quiet_week_says_so_rather_than_rendering_nothing():
    """A changelog that renders nothing on a quiet week is indistinguishable from one that has
    stopped working, so the quiet case is a sentence rather than an absence."""
    w = RR.weekly(today=dt.date(2030, 1, 1))
    assert w["available"] and w["quiet"], w
    assert w["rows"] == 0 and w["charged"] == 0
    # ...and the bars are still shown, because they are a level and a level is always true.
    assert w["domains"], "a quiet week hid the standing counts"
    assert all(not d["moved"] for d in w["domains"])

    real = RR.weekly
    try:
        RR.weekly = lambda *a, **k: w
        sec = _text(_section())
    finally:
        RR.weekly = real
    assert RR.WEEK_QUIET[:50] in sec, "the quiet week rendered no sentence"

    # A LEVEL IS ALWAYS TRUE, AND THIS IS THE ASSERTION THE TEMPLATE DEFECT BROKE. The first
    # cut nested the per-book bars and the headroom inside the busy-week branch, so a quiet
    # week dropped the options and infrastructure bars off the page entirely — and dropped the
    # headroom, which is most worth reading when nothing is happening. The payload was right
    # and the render was not, which is why this has to be asserted HERE and not on `w`.
    for d in w["domains"]:
        assert d["label"] in sec, f"a quiet week hid the {d['key']} book"
        assert d["hurdle_after"] in sec, f"a quiet week hid the {d['key']} bar"
    assert str(w["floor"]["flip_n"]) in sec, "a quiet week hid the headroom"


def test_the_cap_is_never_silent():
    """A trimmed list that says nothing about the trimming reads as the whole of it.

    RENDERED FROM THE SAME PAYLOAD IT ASSERTS ON. The first cut built the payload at a fixed
    date and rendered the page from the LIVE clock, so the two described different windows and
    it failed the moment the date rolled — a date-fragile test on a page whose entire subject
    is the passage of time.
    """
    w = RR.weekly(today=dt.date(2026, 8, 19))
    assert w["hidden"] > 0, "the fixture failed to produce a trimmed list"
    assert w["shown"] + w["hidden"] == w["rows"]
    assert w["shown"] == RR.WEEK_MAX_ROWS

    real = RR.weekly
    try:
        RR.weekly = lambda *a, **k: w
        sec = _text(_section())
    finally:
        RR.weekly = real
    assert str(w["hidden"]) in sec, "the number of trimmed entries is not on the page"
    assert str(w["rows"]) in sec, "the untrimmed total is not on the page"


def test_no_assertion_here_depends_on_todays_date():
    """THE FIFTH DEFECT OF THIS SESSION, AND THE MOST ON-POINT ONE.

    Two tests broke when the clock rolled past midnight mid-session — on a page whose whole
    subject is the record moving. Every test that renders now either drives the payload from
    the live clock on BOTH sides or patches `weekly` so payload and render are the same
    object; no test compares a fixed-date payload against a live render.
    """
    src = _src(os.path.abspath(__file__))
    tree = ast.parse(src)
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("test_")):
            continue
        body = ast.unparse(node)
        fixed = "dt.date(" in body
        renders = "_section(" in body or "_page(" in body
        patched = "RR.weekly = " in body
        assert not (fixed and renders and not patched), (
            f"{node.name} compares a fixed-date payload against a live render")


def test_it_fails_closed_when_the_register_raises():
    real = RL.rows
    RR.reset_hurdle_cache()
    try:
        def _boom(*a, **k):
            raise RuntimeError("the register is unreadable")
        RL.rows = _boom
        w = RR.weekly()
        assert w["available"] is False, "a raising parse produced a published diff"
        for k in ("start", "end", "floor"):
            assert w[k] is None, f"{k} survived a failed parse"
        assert w["domains"] == [] and w["entries"] == [] and w["hurdle_texts"] == []
    finally:
        RL.rows = real
        RR.reset_hurdle_cache()
    assert RR.weekly()["available"], "the module did not recover"


def test_the_exemption_shuts_when_the_level_is_unreadable():
    """SC-4 BROKE THIS AND MB38's OWN TEST CAUGHT IT — recorded here so it stays caught.

    Adding a second contributor to the exemption re-opened the hole whenever the first one was
    unavailable, because the second still read the register on its own. Both read the same
    file, so the set closes on the WEAKER of the two.
    """
    real = RR.multiplicity
    RR.reset_hurdle_cache()
    try:
        RR.multiplicity = lambda *a, **k: {"available": False, "hurdle_text": None}
        assert RR.derived_hurdles() == frozenset(), "the motion block re-opened the hole"
    finally:
        RR.multiplicity = real
        RR.reset_hurdle_cache()
    assert RR.derived_hurdles(), "the cache did not restore"


def test_vintage_labels_go_through_the_withholder():
    """Prose owned by another module. It carries a construction parameter, which the rule
    redacts — over-withholding by design, and left visible as a redaction rather than
    special-cased around."""
    w = RR.weekly(today=dt.date(2026, 8, 19))
    assert w["vintages"], "the fixture week contains no vintage event"
    for v in w["vintages"]:
        assert not RR.contains_figure(v["label"]), v
    assert any(RR.WITHHELD in v["label"] for v in w["vintages"]), (
        "no vintage label was redacted — the withholder may have stopped being applied")


# --------------------------------------------------------------------- the parse it rests on
def test_the_domain_is_emitted_by_the_one_parse():
    """THE DEFECT SC-4 FOUND. `record()` has always read a `domain` off each row and `_emit`
    never wrote one, so the public record rendered an empty column on every row. Fixed inside
    the single parse — a second reader of the same fact is the bug this module's own docstring
    says the project has shipped twice."""
    rows = RL.rows()
    assert rows, "no rows"
    blank = [r["id"] for r in rows if not (r.get("domain") or "").strip()]
    assert not blank, f"{len(blank)} rows still carry no domain, e.g. {blank[:5]}"
    assert set(r["domain"] for r in rows) <= set(RL.DOMAINS)


def test_emitting_the_domain_moved_no_count():
    """The counts are pinned to a committed literal elsewhere; this pins that the same values
    are what the emitted rows add up to, so the two views cannot drift."""
    d = RL.detail()
    per = {}
    for r in RL.rows():
        per[r["domain"]] = per.get(r["domain"], 0) + int(r.get("n_trials") or 0)
    for dom, n in d["by_domain"].items():
        assert per.get(dom, 0) == n, (dom, per.get(dom, 0), n)
    assert sum(per.values()) == d["trials_logged"] - d["trials_domain_unresolved"]


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    tree = ast.parse(_src(os.path.abspath(__file__)))
    names = [n.name for n in tree.body
             if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
    assert len(names) == len(set(names)), (
        f"shadowed: {sorted(n for n in names if names.count(n) > 1)}")
    reachable = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(reachable) == len(names), (len(reachable), len(names))


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:                                   # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} record-this-week tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
