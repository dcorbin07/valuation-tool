"""The public research record (VALQUO_EXTENSIONS.md V4) — offline, deterministic.

    python tests/test_research_page.py

WHAT IS ACTUALLY AT RISK HERE, and it is not layout.

1. **A NUMBER ESCAPING.** The V4 spec allows no performance figures beyond what the public
   posture already carries, and `RESEARCH_LOG.md` is dense with them — result effect sizes in
   the source notes, pre-committed thresholds in the metric cells. The log is append-only and
   grows without anyone consulting this page, so "we checked the current rows" is not a
   safeguard. The rule is therefore absolute (NO performance figure at all, ever) and asserted
   against the RENDERED HTML rather than against the rows, because rendering is where a new
   column or a stray cell would leak.

2. **A SECOND COPY OF THE RECORD.** The page's whole claim is that it shows the log, not a
   curated version of it. If it ever stops being sourced — a hand-typed count, a filtered
   table — the claim silently becomes false while the page still looks right. So the tests
   feed it a SUBSTITUTE log and assert the page changes to match.

3. **A FLATTERING FILTER.** The record is mostly rejections and nulls. A page that quietly
   dropped them would be the exact dishonesty it exists to disprove.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.config import CONFIG                  # noqa: E402

# The page is a child of /work and inherits its gate, so the flag must be on for this suite.
CONFIG.private_mode = False
CONFIG.portfolio_path = "/work"

from valuation.edge import research_log as RL        # noqa: E402
from valuation.saas.app_saas import create_saas_app  # noqa: E402
from valuation.web import research_record as RR      # noqa: E402

APP = create_saas_app(CONFIG)
APP.config["TESTING"] = True
URL = "/work/research"


def _get(url=URL):
    with APP.test_client() as c:
        return c.get(url)


def _html():
    r = _get()
    assert r.status_code == 200, f"{URL} returned {r.status_code}"
    return r.get_data(as_text=True)


# --------------------------------------------------------------------- the publishing rule
def test_the_rendered_page_contains_no_performance_figure():
    """THE ONE THAT MATTERS. Asserted on the HTML, not on the rows.

    Every percentage, basis point, t-statistic, Sharpe, dollar amount and bare decimal in
    `RESEARCH_LOG.md` must be gone by the time it reaches a reader. Checked line by line so a
    failure names the offending line instead of just saying "somewhere".
    """
    offenders = []
    for i, line in enumerate(_html().splitlines(), 1):
        # The page's own CSS is full of decimals (font-size:13.5px). Style is not content.
        s = line.strip()
        if not s or s.startswith(("--", ".", "#", "@", "{", "}")) or ":" in s.split(">")[0]:
            continue
        if RR.contains_figure(s):
            offenders.append(f"  line {i}: {s[:110]}")
    assert not offenders, ("a performance figure reached the public research page:\n"
                           + "\n".join(offenders[:12]))


def test_the_withholder_actually_withholds_and_is_not_vacuous():
    """The guard must fire on real figures and NOT on the record's own identifiers and dates.

    `P4`, `P10-b` and `P6-1` are row IDs. An earlier version of the pattern read them as
    "statistic p, value 4" and the page's own guard fired on its own identifiers.
    """
    for figure in ("+7.17%", "134 bps", "-2.85 pp", "t 2.62", "$4.9M", "0.8556",
                   "261%", "1.17x", "IC +0.03"):
        assert RR.contains_figure(figure), f"a real figure passed the guard: {figure!r}"
        assert RR.WITHHELD in RR.withhold(f"result was {figure} overall")

    for safe in ("P4", "P10-b", "P6-1", "2026-08-09", "83 entries", "32 rejected",
                 "X7RECON", "PT-REGISTER"):
        assert not RR.contains_figure(safe), f"the guard fired on non-figure text: {safe!r}"
        assert RR.withhold(safe) == safe, f"withhold() mangled {safe!r}"


def test_a_date_survives_but_a_decimal_beside_it_does_not():
    got = RR.withhold("On 2026-08-09 the margin was 0.336 pp")
    assert "2026-08-09" in got, got
    assert "0.336" not in got, got


# --------------------------------------------------------------------- sourced, not retyped
def _fake_log(tmpdir):
    p = os.path.join(tmpdir, "FAKE_LOG.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(
            "| id | date | domain | pre | hypothesis | metric | verdict | n | source |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            "| ZZ1 | 2030-01-01 | equity | yes | A unicorn signal predicts returns |"
            " held-out alpha | REJECTED | n=1 | HANDOFF_fake.md |\n"
            "| ZZ2 | 2030-01-02 | equity | yes | A second unicorn signal |"
            " held-out alpha | ADOPTED | n=1 | HANDOFF_fake.md (gain +9.99pp) |\n")
    return p


def test_the_page_is_read_from_the_log_and_not_hand_maintained():
    """Point it at a substitute log; the record must change to match it.

    A hand-typed table would sail through every other test in this file and fail only this
    one — which is why it exists.
    """
    with tempfile.TemporaryDirectory() as d:
        rec = RR.record(log_path=_fake_log(d), root=d)
    ids = [i["id"] for i in rec["items"]]
    assert ids == ["ZZ2", "ZZ1"], ids                 # newest first
    assert rec["counts"]["rejected"] == 1 and rec["counts"]["adopted"] == 1
    assert rec["total"] == 2
    # ...and the substitute log's own planted figure must not survive into the record.
    assert all("9.99" not in i["source"] for i in rec["items"]), rec["items"]


def test_the_counts_are_the_logs_counts_not_a_typed_summary():
    """Every tally on the page is re-derivable from the same parse that sets the trial `N`."""
    rec = RR.record()
    rows = RL.rows()
    assert rec["total"] == len(rows)
    assert sum(rec["counts"].values()) == rec["total"]
    assert rec["searches"] == sum(1 for r in rows if RR.bucket(r["verdict"]) != "fixed")
    html = _html()
    for key in ("rejected", "adopted", "null"):
        assert str(rec["counts"][key]) in html, f"the {key} count is not on the page"


def test_extending_the_parser_did_not_move_the_trial_denominator():
    """`rows()` shares `_parse` with the counter, so a mistake there changes `N` — which feeds
    the Deflated Sharpe.

    PINNED ON A FIXTURE, NOT ON TODAY'S COUNT. The first version of this test asserted
    `n_used == 130`, the live value. That is the wrong pin twice over: it says nothing about
    the parser (any log with 130 equity trials passes it), and it would have failed the shared
    land gate for ANY OTHER LANE that legitimately appended a row — making one lane's correct
    work look like another's regression. The fixture below pins the parsing RULES instead, and
    the live log is checked only for internal consistency.

    The `notes` column is the point. An early cut of `_header_map` resolved columns by
    `startswith`, so in a table with no `n` column a `notes` cell would have been read as the
    grid multiplier — charging row A1 fifty trials because of a phrase in its prose.
    """
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "FIXTURE_LOG.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(
                "| id | date | domain | hypothesis | universe | metric |"
                " threshold (pre-committed) | verdict | source | notes |\n"
                "|---|---|---|---|---|---|---|---|---|---|\n"
                "| A1 | 2030-01-01 | equity | first | full | m | thr | REJECTED | S.md |"
                " grid n=50 in the appendix |\n"
                "| A2 | 2030-01-02 | options | second | full | m | thr | FIXED | S.md | none |\n"
                "\n"
                "| id | date | domain | pre | hypothesis | metric | verdict | n | source |\n"
                "|---|---|---|---|---|---|---|---|---|\n"
                "| B1 | 2030-01-03 | equity | yes | third | m | ADOPTED | n=20 | S.md |\n")
        det = RL.detail(path=p, use_cache=False)
        rws = RL.rows(path=p)

    # A1 contributes ONE trial despite the `n=50` in its notes; B1's own `n` cell gives 20.
    assert det["by_domain"]["equity"] == 21, det["by_domain"]
    assert det["by_domain"]["options"] == 0, "a FIXED row was charged as a trial"
    assert det["n_used"] == 21, det["n_used"]
    assert det["rows_counted"] == 2 and det["rows_fixed_not_counted"] == 1
    assert not det["rows_malformed"], det["rows_malformed"]

    # Both table layouts resolve their own columns: verdict sits at index 7 in the first table
    # and 6 in the second, so a hard-coded index would be wrong on one of them.
    by_id = {r["id"]: r for r in rws}
    assert by_id["A1"]["verdict"] == "REJECTED" and by_id["A1"]["hypothesis"] == "first"
    assert by_id["B1"]["verdict"] == "ADOPTED" and by_id["B1"]["pre"] == "yes"
    assert by_id["B1"]["n_trials"] == 20 and by_id["A1"]["n_trials"] == 1
    assert by_id["A2"]["n_trials"] == 0

    # The LIVE log: internal consistency only, so an unrelated lane appending a row cannot
    # fail this suite.
    live = RL.detail(use_cache=False)
    assert live["rows_counted"] + live["rows_fixed_not_counted"] == len(RL.rows())
    assert not live["rows_malformed"], live["rows_malformed"]
    assert live["n_used"] == max(RL.WEIGHT_SCHEME_TRIALS, live["by_domain"]["equity"])


def test_fixed_rows_are_in_the_record_but_count_zero_trials():
    """Two different questions: 'is this part of the record' and 'was this a search'."""
    rows = RL.rows()
    fixed = [r for r in rows if RR.bucket(r["verdict"]) == "fixed"]
    assert fixed, "no FIXED rows parsed at all — the record is incomplete"
    assert all(r["n_trials"] == 0 for r in fixed)
    assert all(r["n_trials"] >= 1 for r in rows if RR.bucket(r["verdict"]) != "fixed")


# --------------------------------------------------------------------- the record, unfiltered
def test_the_rejections_and_nulls_are_shown_and_outnumber_the_adoptions():
    """A page that quietly dropped the negative verdicts would be the dishonesty it exists to
    disprove. This asserts the SHAPE of the record, not a specific count."""
    rec = RR.record()
    assert rec["negative"] > rec["counts"]["adopted"], rec["counts"]
    html = _html()
    for word in ("Rejected", "Null", "Inconclusive"):
        assert word in html, f"{word} is not rendered"
    # Every row in the record reaches the page.
    for item in rec["items"][:25]:
        assert item["id"] in html, f"row {item['id']} was filtered out of the page"


def test_one_lay_reader_sentence_explains_preregistration():
    """The V4 spec asks for exactly one. More than one is a lecture; none is jargon."""
    html = _html()
    assert RR.PREREGISTRATION_SENTENCE in html
    assert html.count(RR.PREREGISTRATION_SENTENCE) == 1
    assert RR.PREREGISTRATION_SENTENCE.count(".") == 1, "the lay sentence grew a second sentence"


def test_the_registers_are_listed_by_reading_the_repository():
    rec = RR.record()
    files = [p["file"] for p in rec["preregistrations"]]
    assert any(f.startswith("PREREG_") for f in files), files
    assert "PAPER_TRACK_CONTRACT.md" in files, files
    html = _html()
    for f in files[:6]:
        assert f in html, f"{f} is missing from the page"


def test_no_registration_date_is_invented():
    """Scraping the first ISO date out of a register gave PREREG_free_analysis.md a
    registration date of 1998-01-01 — from its contents. A wrong date here would undermine the
    only claim the page makes, so no date is shown at all."""
    for p in RR.record()["preregistrations"]:
        assert "date" not in p, p
    assert "1998" not in _html()


# --------------------------------------------------------------------- posture
def test_the_page_carries_no_vendor_data_and_calls_no_api():
    """Same posture as /work: nothing fetched, nothing from a vendor, and stable across
    requests so it cannot be quietly made dynamic."""
    html = _html()
    assert "/api/" not in html, "the research page calls an API"
    assert "fetch(" not in html and "XMLHttpRequest" not in html
    assert html == _html(), "the page is not byte-identical across requests"


def test_the_page_is_noindex_and_gated_with_the_portfolio_page():
    r = _get()
    assert "noindex" in (r.headers.get("X-Robots-Tag") or "")
    assert 'name="robots"' in r.get_data(as_text=True)

    # TWO TRAPS HERE, both of which made an earlier draft of this test pass vacuously.
    #
    # (1) `portfolio_page` is the gate; the PATH is not. An empty PORTFOLIO_PATH merely falls
    #     back to "/work" (`config.resolved_portfolio_path`) — a sensible failure for a typo,
    #     and a useless one for a test.
    # (2) `create_saas_app` is IDEMPOTENT: it wraps one module-level Flask app once and
    #     returns that same app for every later call, whatever config is passed. So building a
    #     "second app with the flag off" silently re-tests the FIRST app, with the flag on, and
    #     asserts nothing at all. The flag has to be flipped on the config object the live app
    #     closed over — the routes read it per request, which is what makes this work.
    keep = CONFIG.portfolio_page
    try:
        CONFIG.portfolio_page = False
        assert _get().status_code == 404, "the record outlived its own gate"
        with APP.test_client() as c:
            assert c.get("/work").status_code == 404, "control: /work ignored the same gate"
    finally:
        CONFIG.portfolio_page = keep
    assert _get().status_code == 200, "the gate did not restore"


def test_work_links_to_the_record():
    """V4's deliverable is not just the page — it is the page being reachable from /work."""
    with APP.test_client() as c:
        work = c.get("/work").get_data(as_text=True)
    assert URL in work, "/work does not link to the research record"


# --------------------------------------------------------------------- MB38: the denominator
#
# WHAT IS AT RISK IN THIS SECTION, and it is not the paragraph.
#
# MB38 publishes three things on a page whose absolute rule is "no performance figures": a
# trial count, the multiplicity bar that count implies, and the verdict word for the headline
# against it. Making that possible required ONE exemption in the guard. Everything below
# exists to keep that hole exactly one string wide, derived rather than typed, and closed
# whenever the register cannot be read.
#
# THE KILL CONDITION IS A TEST, NOT A NOTE. The item said: if the guard cannot be made to pass
# a count and a derived hurdle WITHOUT also passing a performance figure, do not ship. That
# was measured before any copy existed, and it is asserted here permanently so a later change
# to `_FIGURE` cannot quietly re-break it in either direction.
import ast as _ast
import html as _htmlmod

MODULE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "valuation", "web", "research_record.py")
TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "valuation", "web", "templates", "research.html")


def _src(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _module_code_without_docstrings():
    """The module's CODE. Docstrings stripped, because this file's own prose quotes the very
    numbers the tests below forbid in code — MA5's guard fired on its own documentation, and
    MA49(c)'s fixture failed against a fixed tree for the same reason."""
    tree = _ast.parse(_src(MODULE))
    out = []
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Constant) and isinstance(node.value, str):
            continue
        if isinstance(node, (_ast.Constant,)):
            out.append(repr(node.value))
    return "\n".join(out)


def _mb38_section_of_template():
    t = _src(TEMPLATE)
    i = t.index("MB38: the denominator")
    j = t.index("{% endif %}", i)
    return t[i:j]


def _rendered_mb38_section(plain_page):
    """Just MB38's own section of the rendered page. The rest of the page is other items'
    copy and the log's own prose, and neither is this item's to police."""
    i = plain_page.index(RR.MULTIPLICITY_HEADING)
    return plain_page[i:plain_page.index("</section>", i)]


def _plain(html_text):
    """The page as a reader sees it: entities resolved, so `&#39;` matches an apostrophe."""
    return _htmlmod.unescape(html_text)


def test_mb38_kill_condition_the_guard_passes_a_count_and_a_derived_hurdle():
    """THE ITEM'S OWN KILL CONDITION, run before any copy was written and pinned here.

    Measured against the shipped guard first: counts passed, the verdict word passed, and
    `3.3031` came back `[figure withheld]` at every precision. The item's wording is "cannot
    be MADE to", so the exemption below is the answer to it — and this test is the standing
    proof that both halves still hold.
    """
    m = RR.multiplicity()
    assert m["available"], m["reason"]

    for count in (m["equity"], m["options"], m["infra"], m["trials"]):
        assert not RR.contains_figure(str(count)), f"a trial count is being withheld: {count}"

    assert not RR.contains_figure(m["hurdle_text"]), "the derived hurdle is being withheld"
    for word in (m["verdict"], m["placebo_verdict"]):
        assert not RR.contains_figure(word), f"a verdict word reads as a figure: {word!r}"


def test_mb38_the_exemption_admits_the_hurdle_and_nothing_else():
    """The hole is one string wide, and every near miss on it still fires.

    `13.3031` is a different number. `3.3031%` is a percentage whatever its digits. `t 3.3031`
    is a named statistic, and naming it brings it straight back under the rule.
    """
    m = RR.multiplicity()
    h = m["hurdle_text"]
    assert RR.derived_hurdles() == frozenset({h}), RR.derived_hurdles()

    for a in ("+7.17%", "134 bps", "-2.85 pp", "t 2.62", "$4.9M", "0.8556", "261%", "1.17x",
              "IC +0.03", "2.6199", "2.2837", f"alpha {h}", f"t {h}", f"IC {h}", f"Sharpe {h}",
              f"{h}%", f"{h} pp", f"{h}x", f"1{h}", f"{h}1", f"${h}M", f"-{h}", "13.3031"):
        assert RR.contains_figure(a), f"the exemption let a real figure through: {a!r}"


def test_mb38_the_exemption_is_derived_from_the_register_and_moves_with_it():
    """Not a literal. Point the derivation at a different register and the hurdle must move.

    A frozen hurdle would be wrong within a week: the audit that proposed this item quoted a
    count that was already stale when it was executed.
    """
    from valuation.edge.statistics import hlz_hurdle
    live = RR.multiplicity()
    with tempfile.TemporaryDirectory() as d:
        alt = RR.multiplicity(log_path=_fake_log(d))
    assert alt["available"], alt["reason"]
    assert alt["equity"] != live["equity"], "the fixture failed to move N"
    assert alt["hurdle"] == hlz_hurdle(alt["equity"]), "the hurdle is not a function of N"
    assert live["hurdle"] == hlz_hurdle(live["equity"])
    assert alt["hurdle_text"] != live["hurdle_text"], "the hurdle did not follow N"


def test_mb38_the_exemption_is_empty_when_the_register_cannot_be_read():
    """FAILS CLOSED. A broken parse must CLOSE the guard, not open it."""
    real = RR.multiplicity
    RR.reset_hurdle_cache()
    try:
        RR.multiplicity = lambda *a, **k: {"available": False, "hurdle_text": None}
        assert RR.derived_hurdles() == frozenset(), "an unreadable register left a hole open"
        assert RR.contains_figure("3.3031"), "the hurdle stayed exempt with no register"
    finally:
        RR.multiplicity = real
        RR.reset_hurdle_cache()
    assert RR.derived_hurdles(), "the cache did not restore"


def test_mb38_multiplicity_fails_closed_when_the_parse_itself_raises():
    """FOUND BY MUTATION. Every other fail-closed test here replaces `multiplicity` wholesale,
    so none of them ever entered its own `except` branch — a mutation that made that branch
    return `available: True` with a typed hurdle survived the whole suite.

    A register that raises must produce no numbers and no exemption, exactly as a register
    that reads empty does.
    """
    real = RL.detail
    RR.reset_hurdle_cache()
    try:
        def _boom(*a, **k):
            raise RuntimeError("the register is unreadable")
        RL.detail = _boom
        m = RR.multiplicity()
        assert m["available"] is False, "a raising parse produced a published denominator"
        for k in ("equity", "options", "infra", "trials", "hurdle", "hurdle_text", "verdict"):
            assert m[k] is None, f"{k} survived a raising parse: {m[k]!r}"
        assert RR.derived_hurdles() == frozenset(), "a raising parse left the guard open"
    finally:
        RL.detail = real
        RR.reset_hurdle_cache()
    assert RR.multiplicity()["available"], "the register did not restore"


def test_mb38_withhold_is_not_given_the_exemption():
    """The redactor handles text this page does not own and stays maximally conservative.

    The exemption belongs to the question "would this publish a figure", asked of the page's
    own output — not to the sweep that cleans up log rows.
    """
    h = RR.multiplicity()["hurdle_text"]
    assert RR.withhold(h) == RR.WITHHELD, "withhold() acquired the exemption"
    assert RR.WITHHELD in RR.withhold(f"the margin was {h} overall")


def test_mb38_the_withheld_statistic_never_reaches_the_page_or_the_payload():
    """THE ONE THAT MATTERS HERE. The comparison ships; its operands do not.

    Both constants are real and are used for a real comparison — a verdict word derived from
    invented operands would be worthless. They must not appear in the payload or the HTML.
    """
    page = _plain(_html())
    for bad in (repr(RR.HEADLINE_STATISTIC), repr(RR.PLACEBO_FLOOR),
                "2.6199", "2.2837", "2.62", "2.28"):
        assert bad not in page, f"a withheld operand reached the page: {bad}"

    def leaves(o):
        if isinstance(o, dict):
            for v in o.values():
                yield from leaves(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                yield from leaves(v)
        else:
            yield o

    vals = list(leaves(RR.record()["multiplicity"]))
    assert RR.HEADLINE_STATISTIC not in vals, "the statistic is in the payload"
    assert RR.PLACEBO_FLOOR not in vals, "the calibrated floor is in the payload"


def test_mb38_both_verdict_words_are_derived_from_a_real_comparison():
    """Flip the statistic and both words must flip. A typed word would not move.

    This also pins the direction the PROSE asserts: the paragraph says the two bars can
    disagree about the same number, and today they do.
    """
    m = RR.multiplicity()
    assert m["verdict"] == RR.VERDICT_FAIL, m["verdict"]
    assert m["placebo_verdict"] == RR.VERDICT_PASS, m["placebo_verdict"]

    keep = RR.HEADLINE_STATISTIC
    try:
        RR.HEADLINE_STATISTIC = keep + 10.0
        assert RR.multiplicity()["verdict"] == RR.VERDICT_PASS, "the verdict word is typed"
        RR.HEADLINE_STATISTIC = 0.0
        assert RR.multiplicity()["placebo_verdict"] == RR.VERDICT_FAIL
    finally:
        RR.HEADLINE_STATISTIC = keep
    assert RR.multiplicity()["verdict"] == RR.VERDICT_FAIL, "the comparison did not restore"


def test_mb38_no_count_and_no_hurdle_is_typed_into_the_source():
    """DERIVED AT RENDER, per the item. A typed count goes stale within a week.

    Docstrings are stripped from the module before the check, because this suite's own prose
    and the module's own docstrings legitimately quote these numbers.
    """
    m = RR.multiplicity()
    live = {str(m["equity"]), str(m["options"]), str(m["infra"]), str(m["trials"]),
            m["hurdle_text"]}
    code = _module_code_without_docstrings()
    for v in live:
        assert v not in code, f"{v} is typed into research_record.py"
    section = _mb38_section_of_template()
    for v in live:
        assert v not in section, f"{v} is typed into the template"


def test_mb38_the_hurdle_is_not_computed_in_this_module():
    """MA5's rule: sqrt(2 * ln N) is written exactly ONCE, in `statistics.hlz_hurdle`.

    The first cut of `multiplicity()` computed it inline and the project-wide MA5 guard named
    this file — the check MA5 built catching a fifth copy from a lane that had the warning in
    view.
    """
    code = _src(MODULE)
    assert "hlz_hurdle" in code, "the module does not delegate to the one definition"
    tree = _ast.parse(code)
    for node in _ast.walk(tree):
        if isinstance(node, _ast.Attribute) and node.attr == "log":
            raise AssertionError("research_record.py computes a logarithm of its own")
        if isinstance(node, _ast.Attribute) and node.attr == "sqrt":
            raise AssertionError("research_record.py computes a square root of its own")


def test_mb38_the_rendered_copy_is_pinned_verbatim():
    """V3 / dip_posture pattern: the sentences the page shows are owned in one place and
    asserted against the RENDERED output, because rendering is where copy leaks."""
    page = _plain(_html())
    for name in ("MULTIPLICITY_HEADING", "MULTIPLICITY_LEDE", "MULTIPLICITY_PARAGRAPH",
                 "MULTIPLICITY_BOTH_SIDES", "MULTIPLICITY_CAVEAT",
                 "MULTIPLICITY_WHY_PUBLISHABLE"):
        text = getattr(RR, name)
        assert text in page, f"{name} is not on the page verbatim"


def test_mb38_the_template_holds_no_copy_of_its_own():
    """Every sentence comes from the module. A second copy in the template is a second
    version of the truth, which is the defect this whole page exists to avoid."""
    section = _mb38_section_of_template()
    for name in ("MULTIPLICITY_LEDE", "MULTIPLICITY_PARAGRAPH", "MULTIPLICITY_CAVEAT"):
        text = getattr(RR, name)
        for chunk in (text[:40], text[-40:]):
            assert chunk not in section, f"{name} is retyped in the template"


def test_mb38_the_section_disappears_when_the_register_cannot_be_read():
    """Fail closed on the SURFACE too: show nothing rather than something wrong."""
    real = RR.multiplicity
    RR.reset_hurdle_cache()
    try:
        RR.multiplicity = lambda *a, **k: {"available": False, "reason": "x", "equity": None,
                                           "options": None, "infra": None, "trials": None,
                                           "hurdle": None, "hurdle_text": None,
                                           "hurdle_n": None, "verdict": None,
                                           "placebo_verdict": None}
        r = _get()
        assert r.status_code == 200, "the page died instead of hiding the section"
        page = r.get_data(as_text=True)
        assert RR.MULTIPLICITY_HEADING not in page, "the section rendered with no numbers"
    finally:
        RR.multiplicity = real
        RR.reset_hurdle_cache()
    assert RR.MULTIPLICITY_HEADING in _html(), "the section did not come back"


def test_mb38_the_page_states_the_registered_caveat_and_claims_no_success():
    """Both sides of the record's own tension, and no chest-thumping.

    The caveat is R4's registered argument against the strict reading. It is stated once; the
    page does not argue it, and it does not use it to retract the verdict word.
    """
    page = _plain(_html())
    assert RR.VERDICT_FAIL in page, "the failing verdict is not on the page"

    # R4's caveat has THREE load-bearing parts and all three must survive: what the hurdle
    # prices, why the deployed model is not that thing, and what the counted trials therefore
    # are. Checking one phrase let a mutation gut the other two.
    caveat = RR.MULTIPLICITY_CAVEAT
    assert caveat in page, "the registered caveat is not on the page"
    assert "best of N attempts" in caveat, "the caveat does not say what the hurdle prices"
    assert "not the best of anything" in caveat, "the caveat does not say why that matters"
    assert "never tuned" in caveat, "the caveat does not say the weights were never tuned"
    assert "rejected" in caveat, "the caveat does not say what the counted trials were"

    # SCOPED TO THE COPY THIS ITEM OWNS, and word-boundaried — both corrections to my own
    # first cut, which searched the WHOLE page for the substring "proven" and failed against
    # a correct tree on the word "provenance" in a log row forty rows away. That is
    # MA28-CARD-UI's defect exactly: a hand-typed phrase list firing on innocent pre-existing
    # text. The log's own prose is not this item's to police, and a substring is not a word.
    owned = " ".join(getattr(RR, n) for n in (
        "MULTIPLICITY_HEADING", "MULTIPLICITY_LEDE", "MULTIPLICITY_PARAGRAPH",
        "MULTIPLICITY_BOTH_SIDES", "MULTIPLICITY_CAVEAT", "MULTIPLICITY_WHY_PUBLISHABLE",
        "VERDICT_FAIL", "VERDICT_PASS")) + " " + _rendered_mb38_section(page)
    import re as _re
    for boast in ("proven", "beats the market", "outperforms", "outperformed", "guaranteed",
                  "risk[- ]free", "significant", "edge"):
        assert not _re.search(rf"\b{boast}\b", owned, _re.I), \
            f"MB38's own copy claims too much: {boast!r}"

    # ...and the check must be able to fail: a planted boast in the same scope must trip it.
    assert _re.search(r"\bproven\b", owned + " proven", _re.I), "the boast check is vacuous"


def test_mb38_the_denominator_is_the_same_parse_that_sets_the_deflated_sharpe():
    """The page's claim is that its count cannot drift from the model's own correction.

    Asserted against `research_log` directly: if these ever diverge the page is publishing a
    denominator the model does not use, which is worse than publishing none.
    """
    m = RR.multiplicity()
    det = RL.detail()
    assert m["equity"] == det["by_domain"]["equity"], (m["equity"], det["by_domain"])
    assert m["options"] == det["by_domain"]["options"]
    assert m["infra"] == det["by_domain"]["infra"]
    assert m["trials"] == det["trials_logged"]
    assert m["hurdle_n"] == RL.trial_count(domain="equity"), "the hurdle uses a different N"


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
    print(f"\n{passed}/{len(tests)} research-page tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
