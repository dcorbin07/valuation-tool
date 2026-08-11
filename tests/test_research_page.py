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
