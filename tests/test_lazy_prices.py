"""
Lazy-prices dataset tests (offline — no network, tiny fixtures). Run:
    python tests/test_lazy_prices.py

Deliberately NOT appended to test_edge.py: this module is research-only and must not be able
to break the suite the live panel depends on.

The tests that matter most are the point-in-time ones. A textual-similarity dataset is very
easy to contaminate — fit a TF-IDF vectorizer on the whole corpus and every historical row
silently knows what words became common in 2025 — and the contamination shows up as a better
backtest, not as an error. test_idf_is_point_in_time and test_no_future_leak_into_past_rows
pin that shut.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.research import lazy_prices as lp


def _tmp():
    return tempfile.mkdtemp()


def _doc(ticker, form, filing_date, report_date, words, acc=None, sections=True):
    """A cached-document record shaped exactly like fetch_document() returns."""
    from collections import Counter
    toks = words.split() if isinstance(words, str) else words
    rec = {"form": form, "accession": acc or f"{ticker}-{filing_date}",
           "filing_date": filing_date, "report_date": report_date,
           "primary_doc": "x.htm", "doc_source": "primary", "error": None,
           "n_words": len(toks), "n_chars": 10 * len(toks),
           "counts": dict(Counter(toks))}
    for name in ("mdna", "risk"):
        rec[f"{name}_words"] = len(toks) if sections else 0
        rec[f"{name}_counts"] = dict(Counter(toks)) if sections else None
    return rec


# --------------------------------------------------------------------------- #
#  text handling
# --------------------------------------------------------------------------- #
def test_html_to_text_strips_tags_scripts_and_entities():
    raw = ("<html><head><style>p{color:red}</style><script>var x=1;</script></head>"
           "<body><p>Total&nbsp;revenue &amp; profit</p><div>grew</div></body></html>")
    got = lp.html_to_text(raw)
    assert "color:red" not in got and "var x" not in got, got
    assert "revenue" in got and "&" in got and "grew" in got, got
    assert "<" not in got and ">" not in got, got


def test_tokenize_drops_numbers_punctuation_and_stopwords():
    got = lp.tokenize("Revenue of $1,234.5 million in 2025 was up 12% -- and the margin grew.")
    assert "revenue" in got and "million" in got and "margin" in got, got
    for bad in ("1", "2025", "12", "of", "the", "and", "in", "was"):
        assert bad not in got, (bad, got)
    # single characters are noise (list bullets, "a", "s" from possessives)
    assert all(len(t) >= 2 for t in got), got


def test_sections_prefer_the_body_over_the_table_of_contents():
    """Every 10-K names its items twice: once in the TOC, once as the real heading. Taking
    the FIRST match gives you a one-line TOC entry, which is why the longest span wins."""
    text = ("Table of contents Item 1A. Risk Factors 12 Item 1B. Unresolved 20 "
            "Item 7. Management Discussion 30 Item 8. Financial Statements 40 "
            "Item 1A. Risk Factors " + "competition supply chain risk " * 40 +
            "Item 1B. Unresolved Staff Comments none "
            "Item 7. Management Discussion " + "revenue grew margin expanded " * 40 +
            "Item 8. Financial Statements see notes")
    secs = lp.extract_sections(text, "10-K")
    assert secs["mdna"] and "revenue grew" in secs["mdna"], secs["mdna"]
    assert "Table of contents" not in (secs["mdna"] or ""), secs["mdna"]
    assert secs["risk"] and "competition supply" in secs["risk"], secs["risk"]
    # 10-Q uses different item numbers; the 10-K spec must not be applied to it.
    q = ("Item 2. Management Discussion " + "revenue grew margin expanded " * 40 +
         "Item 3. Quantitative disclosures")
    assert lp.extract_sections(q, "10-Q")["mdna"], "10-Q MD&A (Item 2) not isolated"


def test_cross_reference_is_not_a_section_heading():
    """REGRESSION — this shipped broken and was caught by eyeballing a real filing.

    AAPL's 10-Q says, inside MD&A, "...factors discussed in Part I, Item 1A of the 2025 Form
    10-K and Part II, Item 1A of this Form 10-Q ... under the heading 'Risk Factors.'" The
    first version read that as the start of Risk Factors, so the "risk" section began
    mid-MD&A and ran to the end of it: mdna and risk came back as near-duplicates (identical
    top terms on the real document). A heading now has to be followed by the section title
    AND not be preceded by a reference cue.
    """
    text = ("Item 2. Management's Discussion and Analysis of Financial Condition "
            + "revenue grew margin expanded " * 60 +
            "differences include those discussed in Part I, Item 1A of the 2025 Form 10-K "
            "and Part II, Item 1A of this Form 10-Q, in each case under the heading "
            "\"Risk Factors.\" " + "gross margin guidance " * 60 +
            "Item 3. Quantitative and Qualitative Disclosures About Market Risk none "
            "Item 4. Controls and Procedures effective "
            "Item 1A. Risk Factors " + "supply concentration litigation " * 60 +
            "Item 2. Unregistered Sales of Equity Securities none")
    secs = lp.extract_sections(text, "10-Q")
    assert secs["risk"] and secs["risk"].strip().startswith(". Risk Factors"), secs["risk"][:80]
    assert "revenue grew" not in secs["risk"], "MD&A text leaked into the risk section"
    assert "supply concentration" in secs["risk"], secs["risk"][:120]
    assert secs["mdna"] and "revenue grew" in secs["mdna"]
    assert "supply concentration" not in secs["mdna"], "risk text leaked into MD&A"
    # the two sections must not be the same span
    assert secs["mdna"] != secs["risk"]


def test_missing_section_is_none_not_empty():
    """A section that cannot be isolated must be MISSING. An empty string would score as
    'the company rewrote it completely' — the exact opposite of unknown."""
    secs = lp.extract_sections("This filing has no item headings at all.", "10-K")
    assert secs["mdna"] is None and secs["risk"] is None, secs
    assert lp.extract_sections("Item 7. tiny Item 8. x", "10-K")["mdna"] is None   # below floor


def test_item_regex_does_not_confuse_7_with_7a():
    assert lp._item_rx("7").search("see Item 7. Management") is not None
    assert lp._item_rx("7").search("see Item 7A. Quantitative") is None
    assert lp._item_rx("1a").search("Item 1A. Risk Factors") is not None
    assert lp._item_rx("1a").search("Item 1. Business") is None


# --------------------------------------------------------------------------- #
#  similarity maths
# --------------------------------------------------------------------------- #
def test_cosine_and_jaccard_endpoints():
    a = {"revenue": 3, "margin": 1}
    assert abs(lp.cosine(a, dict(a)) - 1.0) < 1e-12
    assert lp.cosine(a, {"lawsuit": 5}) == 0.0
    assert lp.jaccard(a, dict(a)) == 1.0
    assert lp.jaccard(a, {"lawsuit": 5}) == 0.0
    # |{revenue}| / |{revenue, margin, lawsuit}|
    assert abs(lp.jaccard(a, {"revenue": 9, "lawsuit": 1}) - 1 / 3) < 1e-12
    assert lp.cosine({}, a) is None and lp.jaccard(None, a) is None


def test_jaccard_ignores_repetition_but_cosine_does_not():
    """The two measures must not be redundant — that is the reason both are stored."""
    a, b = {"risk": 1, "growth": 1}, {"risk": 50, "growth": 1}
    assert lp.jaccard(a, b) == 1.0
    assert lp.cosine(a, b) < 0.8, lp.cosine(a, b)


def test_tfidf_downweights_boilerplate():
    """A word in every filing carries no information; a rare shared word carries a lot. Two
    pairs that look identical to a raw-count cosine must not look identical to TF-IDF."""
    n_docs = 1000
    df = {"company": 1000, "recall": 3}
    common = lp.tfidf_cosine({"company": 1, "zzz": 1}, {"company": 1, "yyy": 1}, df, n_docs)
    rare = lp.tfidf_cosine({"recall": 1, "zzz": 1}, {"recall": 1, "yyy": 1}, df, n_docs)
    assert rare > common, (rare, common)
    assert abs(lp.tfidf_cosine({"a": 2, "b": 1}, {"a": 2, "b": 1}, df, n_docs) - 1.0) < 1e-9


# --------------------------------------------------------------------------- #
#  pairing
# --------------------------------------------------------------------------- #
def test_pairs_same_quarter_a_year_back_not_the_adjacent_one():
    cur = _doc("A", "10-Q", "2025-05-01", "2025-03-31", "x y z")
    prior_year = _doc("A", "10-Q", "2024-05-01", "2024-03-31", "x y z")
    last_qtr = _doc("A", "10-Q", "2025-02-01", "2024-12-31", "x y z")
    got = lp.find_prior(cur, [last_qtr, prior_year])
    assert got is prior_year, got["report_date"]
    # a 10-K must never pair against a 10-Q
    assert lp.find_prior(_doc("A", "10-K", "2025-11-01", "2025-09-30", "x"),
                         [prior_year, last_qtr]) is None
    # nothing in the window -> no row, rather than a bad pair
    assert lp.find_prior(cur, [_doc("A", "10-Q", "2020-05-01", "2020-03-31", "x")]) is None


def test_first_year_of_history_is_unpaired_not_zero():
    docs = {d["accession"]: d for d in
            [_doc("A", "10-K", "2023-02-01", "2022-12-31", "alpha beta"),
             _doc("A", "10-K", "2024-02-01", "2023-12-31", "alpha beta")]}
    rows = lp.score_all({"A": docs})
    assert len(rows) == 1, rows
    assert rows[0]["available_from"] == "2024-02-01", rows[0]


# --------------------------------------------------------------------------- #
#  POINT-IN-TIME — the tests this module exists for
# --------------------------------------------------------------------------- #
def test_score_is_dated_by_filing_date_never_period_end():
    d = _doc("A", "10-K", "2024-02-20", "2023-12-31", "alpha beta")
    p = _doc("A", "10-K", "2023-02-20", "2022-12-31", "alpha beta")
    row = lp._score_pair("A", d, p, {}, 0)
    assert row["available_from"] == "2024-02-20", row
    assert row["report_date"] == "2023-12-31", row
    assert row["available_from"] > row["report_date"], "period end must never date the row"


def test_idf_is_point_in_time():
    """A pair scored on date D may only see document frequencies from filings BEFORE D —
    including not seeing the two documents in its own pair."""
    mk = lambda t, fd, rd: _doc(t, "10-K", fd, rd, "alpha beta gamma")   # noqa: E731
    cached = {
        "A": {d["accession"]: d for d in [mk("A", "2020-02-01", "2019-12-31"),
                                          mk("A", "2021-02-01", "2020-12-31"),
                                          mk("A", "2022-02-01", "2021-12-31")]},
        "B": {d["accession"]: d for d in [mk("B", "2020-06-01", "2019-12-31"),
                                          mk("B", "2021-06-01", "2020-12-31")]},
    }
    rows = lp.score_all(cached)
    by_date = {(r["ticker"], r["available_from"]): r for r in rows}
    # A's 2021-02-01 row: only A-2020-02-01 and B-2020-06-01 were filed before it.
    assert by_date[("A", "2021-02-01")]["idf_docs"] == 2, by_date[("A", "2021-02-01")]
    # A's 2022 row additionally sees A-2021 and B-2021.
    assert by_date[("A", "2022-02-01")]["idf_docs"] == 4, by_date[("A", "2022-02-01")]
    assert all(r["idf_docs"] >= 0 for r in rows)


def test_no_future_leak_into_past_rows():
    """Append filings from the future and re-score: every pre-existing row must be
    byte-identical. This is the check that would catch someone 'simplifying' score_all into
    a single global TF-IDF fit."""
    base = {"A": {d["accession"]: d for d in
                  [_doc("A", "10-K", "2020-02-01", "2019-12-31", "alpha beta"),
                   _doc("A", "10-K", "2021-02-01", "2020-12-31", "alpha beta gamma")]}}
    before = lp.score_all(base)
    grown = {"A": dict(base["A"])}
    grown["A"].update({d["accession"]: d for d in
                       [_doc("A", "10-K", "2022-02-01", "2021-12-31", "alpha delta"),
                        _doc("A", "10-K", "2023-02-01", "2022-12-31", "epsilon zeta")]})
    grown["Z"] = {d["accession"]: d for d in
                  [_doc("Z", "10-K", "2022-03-01", "2021-12-31", "alpha alpha alpha")]}
    after = [r for r in lp.score_all(grown) if r["available_from"] <= "2021-02-01"]
    assert before == after, (before, after)


def test_same_day_filings_do_not_enter_their_own_idf():
    a = _doc("A", "10-K", "2021-02-01", "2020-12-31", "alpha beta")
    b = _doc("B", "10-K", "2021-02-01", "2020-12-31", "alpha beta")
    cached = {"A": {a["accession"]: a,
                    (p := _doc("A", "10-K", "2020-02-01", "2019-12-31", "alpha"))["accession"]: p},
              "B": {b["accession"]: b,
                    (q := _doc("B", "10-K", "2020-02-01", "2019-12-31", "alpha"))["accession"]: q}}
    rows = {r["ticker"]: r for r in lp.score_all(cached)}
    # Two 2020 filings precede them; neither same-day 2021 filing counts.
    assert rows["A"]["idf_docs"] == 2 and rows["B"]["idf_docs"] == 2, rows


# --------------------------------------------------------------------------- #
#  listing / caching / output
# --------------------------------------------------------------------------- #
def test_amendments_and_other_forms_are_excluded():
    block = {"form": ["10-K", "10-K/A", "10-Q", "NT 10-K", "8-K", "10-KT"],
             "accessionNumber": ["a", "b", "c", "d", "e", "f"],
             "filingDate": ["2024-02-01"] * 6,
             "reportDate": ["2023-12-31"] * 6,
             "primaryDocument": ["x.htm"] * 6}
    got = lp._rows_from_block(block)
    assert [r["form"] for r in got] == ["10-K", "10-Q"], got
    assert [r["accession"] for r in got] == ["a", "c"], got


def test_document_url_falls_back_to_full_submission_and_flags_it():
    u, src = lp.document_url(320193, "0000320193-25-000079", "aapl-20250927.htm")
    assert src == "primary" and u.endswith("/000032019325000079/aapl-20250927.htm"), u
    u2, src2 = lp.document_url(320193, "0000320193-25-000079", "")
    assert src2 == "full" and u2.endswith("0000320193-25-000079.txt"), u2


def test_cache_round_trip_and_resume_skips_fetched_filings(monkeypatch=None):
    """Resumability: a second run must download nothing it already has."""
    d = _tmp()
    listed = [{"form": "10-K", "accession": "acc1", "filing_date": "2024-02-01",
               "report_date": "2023-12-31", "primary_doc": "x.htm"},
              {"form": "10-K", "accession": "acc2", "filing_date": "2025-02-01",
               "report_date": "2024-12-31", "primary_doc": "y.htm"}]
    calls = []
    orig_list, orig_fetch = lp.list_filings, lp.fetch_document
    lp.list_filings = lambda *a, **k: listed
    lp.fetch_document = lambda cik, f, lim, session=None: (
        calls.append(f["accession"]) or _doc("A", "10-K", f["filing_date"],
                                             f["report_date"], "alpha beta", acc=f["accession"]))
    try:
        lim = lp.RateLimiter(1000)
        first = lp.build_ticker_cache("A", 1, d, lim)
        assert sorted(calls) == ["acc1", "acc2"], calls
        assert os.path.exists(lp.cache_path(d, "A"))
        second = lp.build_ticker_cache("A", 1, d, lim)
        assert sorted(calls) == ["acc1", "acc2"], f"re-downloaded on resume: {calls}"
        assert set(second) == set(first) == {"acc1", "acc2"}
    finally:
        lp.list_filings, lp.fetch_document = orig_list, orig_fetch


def test_rebuild_sections_works_offline_from_the_text_cache():
    """The section heuristic has already needed one correction. Fixing it again must cost
    seconds from the text cache, not a re-download of the corpus."""
    d = _tmp()
    body = ("Item 7. Management's Discussion and Analysis " + "revenue grew margin " * 60 +
            "Item 8. Financial Statements see notes")
    rec = _doc("A", "10-K", "2024-02-01", "2023-12-31", "alpha beta", acc="acc1", sections=False)
    lp.save_cache(d, "A", {"acc1": rec})
    lp._save_gz(lp.text_cache_path(d, "A"), {"acc1": body})
    assert lp.load_cache(d, "A")["acc1"]["mdna_counts"] is None
    updated, total = lp.rebuild_sections("A", d)
    assert (updated, total) == (1, 1), (updated, total)
    got = lp.load_cache(d, "A")["acc1"]
    assert got["mdna_counts"] and "revenue" in got["mdna_counts"], got["mdna_counts"]
    assert lp.rebuild_sections("NOSUCH", d) == (0, 0)      # missing text cache -> no-op


def test_failed_filings_are_recorded_and_never_scored():
    docs = {"bad": {"form": "10-K", "accession": "bad", "filing_date": "2024-02-01",
                    "report_date": "2023-12-31", "error": "http_404"},
            "ok1": _doc("A", "10-K", "2023-02-01", "2022-12-31", "alpha beta", acc="ok1"),
            "ok2": _doc("A", "10-K", "2024-02-01", "2023-12-31", "alpha beta", acc="ok2")}
    rows = lp.score_all({"A": docs})
    assert len(rows) == 1 and rows[0]["accession"] == "ok2", rows
    cov = lp.coverage_report({"A": docs}, rows, ["A"], [])
    assert cov["filings_failed"] == {"http_404": 1}, cov["filings_failed"]
    assert cov["filings_parsed_ok"] == 2 and cov["filings_scored"] == 1, cov
    assert cov["filings_ok_but_unpaired"] == 1, cov


def test_written_row_has_every_declared_column():
    d = _tmp()
    docs = {x["accession"]: x for x in
            [_doc("A", "10-K", "2023-02-01", "2022-12-31", "alpha beta", acc="p"),
             _doc("A", "10-K", "2024-02-01", "2023-12-31", "alpha gamma", acc="c")]}
    rows = lp.score_all({"A": docs})
    for col in lp.COLUMNS:
        assert col in rows[0], f"missing column {col}"
    paths = lp.write_dataset(rows, d)
    with open(paths[0], encoding="utf-8") as f:
        head, body = f.read().splitlines()[:2]
    assert head.split(",") == lp.COLUMNS, head
    assert body.startswith("A,10-K,2024-02-01,"), body


def test_similarity_is_bounded_and_ordered_as_the_paper_reads_it():
    """Orientation guard: a near-copy must score HIGHER than a rewrite. If someone ever
    negates these columns, this fails."""
    prior = _doc("A", "10-K", "2023-02-01", "2022-12-31",
                 "revenue grew margin expanded competition supply chain", acc="p")
    lazyfiler = _doc("A", "10-K", "2024-02-01", "2023-12-31",
                     "revenue grew margin expanded competition supply chain", acc="c")
    rewriter = _doc("B", "10-K", "2024-02-01", "2023-12-31",
                    "impairment litigation restructuring goodwill writedown covenant breach",
                    acc="c2")
    rows = lp.score_all({"A": {"p": prior, "c": lazyfiler},
                         "B": {"p": dict(prior, accession="p2"), "c": rewriter}})
    by_t = {r["ticker"]: r for r in rows}
    assert by_t["A"]["cosine_tf"] > by_t["B"]["cosine_tf"], rows
    for r in rows:
        for k in ("cosine_tf", "jaccard", "cosine_tfidf"):
            assert 0.0 <= r[k] <= 1.0 + 1e-9, (k, r[k])


def test_module_is_not_imported_by_the_live_panel():
    """Non-interference, enforced rather than promised: nothing under valuation/edge,
    valuation/screener or the web app may import this research module."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    for sub in ("edge", "screener", "web", "saas", "engine", "report", "intraday"):
        base = os.path.join(root, "valuation", sub)
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                with open(os.path.join(dirpath, fn), encoding="utf-8", errors="ignore") as f:
                    if "lazy_prices" in f.read():
                        hits.append(os.path.join(sub, fn))
    assert not hits, f"research module leaked into production code: {hits}"


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
    print(f"\n{passed}/{len(tests)} lazy-prices tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
