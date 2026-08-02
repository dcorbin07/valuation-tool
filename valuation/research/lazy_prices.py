"""
"Lazy Prices" (Cohen, Malloy & Nguyen) — year-over-year 10-K/10-Q language-change dataset.

THE CLAIM BEING TESTED LATER, NOT HERE. Firms that barely change the wording of their
periodic filings tend to outperform firms that rewrite them; a big textual change flags
deterioration management has decided to disclose but not to headline. So the orientation,
fixed here in advance so it cannot be chosen after seeing returns, is:

    HIGHER SIMILARITY = "LAZY" = THE BULLISH READ. Not negated anywhere in this file.

This module BUILDS THE DATASET ONLY. It does not decide keep/reject, computes no ICs, and is
imported by nothing in the live panel. The gated test (does similarity predict forward
returns, via CPCV / held-out) runs later, on the file this writes.

--------------------------------------------------------------------------------------------
POINT-IN-TIME — the whole reason this is worth building.

A filing's score is usable only from its EDGAR FILING DATE forward, and that date is honest:
the moment a filing is accepted it is public and readable by anyone. Three places where
look-ahead could sneak in, and what is done about each:

  1. THE SCORE'S DATE. Every row carries `available_from` = the LATER filing's filing date.
     `report_date` (the fiscal period) is carried too, but only for pairing quarters — never
     as the availability date. A 10-K for FY2024 filed 2025-02-01 is unusable on 2025-01-31.

  2. THE PAIR. A filing is compared to the most recent EARLIER filing of the SAME form whose
     fiscal period sits 270-450 days back (i.e. the same quarter a year ago, as in the paper).
     Both documents are public by `available_from` by construction, since the earlier one was
     filed first.

  3. THE IDF. This is the subtle one. A TF-IDF cosine needs document frequencies from a
     corpus, and the obvious implementation — fit the vectorizer on every filing you
     downloaded — leaks the future into every historical row. Instead the scorer walks all
     filings in FILING-DATE ORDER and, for a pair scored on date D, uses document frequencies
     accumulated ONLY from filings with filing_date < D. Every row records `idf_docs`, the
     size of that corpus, because the earliest rows are computed against a nearly empty one
     and should be treated as noisier (or dropped) downstream.

     `cosine_tf` and `jaccard` need no corpus at all and are therefore immune to this by
     construction. If the three measures ever disagree in a way that favours only the
     TF-IDF one, suspect the IDF corpus, not the signal.

--------------------------------------------------------------------------------------------
THE MEASURES (all in [0, 1]; higher = more similar = more "lazy")

  cosine_tf      cosine on raw term-count vectors. This is the paper's primary measure and
                 needs no corpus.
  jaccard        |A n B| / |A u B| over the distinct-word sets. Insensitive to how often a
                 word is repeated, so it moves for different reasons than the cosines do.
  cosine_tfidf   cosine on L2-normalised sublinear-tf x smoothed-idf vectors, with the
                 point-in-time IDF described above.
  mdna_*/risk_*  the same measures restricted to the MD&A and Risk Factors sections when
                 they can be isolated (see extract_sections — a HEURISTIC, coverage reported).

Numbers, punctuation and a small stop-list are removed before any measure is computed:
without that, every filing pair is dominated by dates and dollar amounts that change
mechanically each period, which is noise for this question rather than signal.

--------------------------------------------------------------------------------------------
KNOWN LIMITATIONS — stated up front rather than discovered later.

  * AMENDMENTS ARE EXCLUDED. Only exact form types 10-K and 10-Q are used; 10-K/A restates
    part of a document and would compare a fragment against a full filing.
  * THE PRIMARY DOCUMENT ONLY, not the complete submission. Exhibits are excluded, which is
    what the paper wants, but it means the extracted text depends on EDGAR's
    `primaryDocument` field being right. Filings without one (mostly pre-2001) fall back to
    the complete text submission and are flagged `doc_source="full"` — those rows include
    exhibit text and are NOT comparable to `doc_source="primary"` rows. Filter on it.
  * SECTION EXTRACTION IS A HEURISTIC over "Item N" headings, and filings are not consistent.
    Coverage is measured and reported rather than assumed; a missing section is NaN, not 0.
  * TICKER -> CIK COMES FROM SEC's `company_tickers.json`, a TODAY snapshot. Same
    survivor-bias caveat already recorded for the 13D map and the Sharadar sector map: a
    company that delisted or changed ticker may map imperfectly. That biases toward
    survivors, which can flatter an adoption and cannot manufacture a rejection.
  * NO SURVIVORSHIP-FREE UNIVERSE YET. The default universe is today's large caps, so a
    first-pass IC on this dataset is a survivor-only IC. Say so when reporting it.

--------------------------------------------------------------------------------------------
RUN IT

    python -m valuation.research.lazy_prices --limit 60 --since 2018-01-01
    python -m valuation.research.lazy_prices --tickers AAPL,MSFT --out-dir data/filings

Resumable: every fetched document is cached under `<out-dir>/cache/<TICKER>.pkl.gz` as token
counts (not raw text), so a re-run re-downloads nothing and re-scoring is seconds. Kill it
whenever; it picks up where it stopped.

SEC fair access is respected: descriptive User-Agent with a contact address, a shared token
bucket well under the published 10 requests/second, and backoff on 403/429.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import pickle
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

DEFAULT_OUT_DIR = os.path.join("data", "filings")
FORMS = ("10-K", "10-Q")

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSION_SHARD = "https://data.sec.gov/submissions/{name}"
TICKER_MAP = "https://www.sec.gov/files/company_tickers.json"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
FULL_TXT = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{acc_dashed}.txt"

# SEC publishes a 10 req/sec ceiling. Stay well under it — this job is not urgent and a
# throttled-out run costs far more than a slow one.
REQ_PER_SEC = 5.0
MAX_RETRIES = 4
SAVE_EVERY = 20            # flush a ticker's cache this often, so a kill loses ~nothing

# Pairing window: the same fiscal quarter a year earlier. 270-450 days is wide enough for
# 52/53-week fiscal calendars and a shifted year-end, narrow enough that it cannot pair a
# 10-Q against the adjacent quarter.
PAIR_MIN_DAYS = 270
PAIR_MAX_DAYS = 450
PAIR_TARGET_DAYS = 365

# A document below this many words is a stub (cover page, incorporation-by-reference) and is
# not comparable to a real filing.
MIN_DOC_WORDS = 500
MIN_SECTION_WORDS = 50

# Deliberately small. A big stop-list starts making editorial choices about which business
# language counts; these are the words that carry no information in any filing.
STOPWORDS = frozenset("""
a an and are as at be been but by for from had has have if in into is it its of on or such
that the their then there these they this to was were which will with we our us you your
""".split())

_TOKEN_RX = re.compile(r"[a-z]{2,}")
_TAG_RX = re.compile(r"(?s)<[^>]+>")
_DROP_RX = re.compile(r"(?is)<(script|style|ix:header)[^>]*>.*?</\1>")
_WS_RX = re.compile(r"\s+")


def _log(m):
    print(f"[lazy_prices] {m}", flush=True)


# --------------------------------------------------------------------------- #
#  HTTP — one shared, rate-limited session
# --------------------------------------------------------------------------- #
class RateLimiter:
    """Token bucket shared by every worker thread. Simple, and simple is what we want here:
    exceeding SEC's limit gets the whole IP blocked, not just the offending request."""

    def __init__(self, per_sec: float = REQ_PER_SEC):
        self.interval = 1.0 / max(per_sec, 0.1)
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                delay = self._next - now
            else:
                delay = 0.0
                self._next = now
            self._next += self.interval
        if delay > 0:
            time.sleep(delay)


def user_agent() -> str:
    try:
        from ..config import CONFIG
        ua = (CONFIG.sec_user_agent or "").strip()
    except Exception:                                          # noqa: BLE001
        ua = ""
    return ua or "Valquo research donniecorbin6@gmail.com"


def _get(url: str, limiter: RateLimiter, timeout: int = 90, session=None):
    """GET with SEC-appropriate headers and backoff. Returns a response or None."""
    import requests

    hdrs = {"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"}
    get = (session or requests).get
    for attempt in range(MAX_RETRIES):
        limiter.wait()
        try:
            r = get(url, headers=hdrs, timeout=timeout)
        except Exception as e:                                  # noqa: BLE001
            if attempt == MAX_RETRIES - 1:
                _log(f"request failed after {MAX_RETRIES}: {url} ({e})")
                return None
            time.sleep(2 ** attempt)
            continue
        if r.status_code == 200:
            return r
        if r.status_code in (403, 429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        return r          # 404 etc — caller decides; retrying will not help
    return None


# --------------------------------------------------------------------------- #
#  text -> tokens
# --------------------------------------------------------------------------- #
def html_to_text(raw: str) -> str:
    """Strip HTML/inline-XBRL to plain text. Regex, deliberately, not a DOM parser: filings
    run to 10MB+ of tag soup and we only need the words in reading order, so a parser buys
    nothing here and costs seconds per document."""
    import html as _html

    if not raw:
        return ""
    s = _DROP_RX.sub(" ", raw)
    s = _TAG_RX.sub(" ", s)
    s = _html.unescape(s)
    return _WS_RX.sub(" ", s).strip()


def tokenize(text: str) -> list:
    """Lowercase alphabetic words of 2+ characters, stop-words removed.

    Numbers are dropped ON PURPOSE: every filing restates dates and dollar amounts that
    change mechanically each period, so keeping them measures the calendar, not the prose.
    """
    return [t for t in _TOKEN_RX.findall(text.lower()) if t not in STOPWORDS]


def _item_rx(item: str) -> re.Pattern:
    """`item 7` but not `item 7a`, tolerant of the whitespace/punctuation filings use."""
    body = item[:-1] + r"\s*" + item[-1] if item[-1].isalpha() else item
    return re.compile(r"item\s*" + body + r"(?![a-z0-9])", re.I)


# CROSS-REFERENCES ARE NOT HEADINGS, and this cost a rewrite of the section logic to notice.
# AAPL's 10-Q says "...factors discussed in Part I, Item 1A of the 2025 Form 10-K and Part II,
# Item 1A of this Form 10-Q..." INSIDE the MD&A. Treating that as the start of Risk Factors
# produced a "risk" section that began in the middle of MD&A and ran to the end of it — so
# mdna_* and risk_* were near-duplicates of each other (caught by eyeballing the top terms of
# both sections on a real filing: they were identical). A heading match must therefore be
# (a) followed by the section's actual title and (b) not preceded by a reference cue.
_XREF_RX = re.compile(r"\b(?:see|in|into|under|of|to|and|with|from|per|within)\s+"
                      r"(?:part\s+[ivx]+\s*[,\.]?\s*)?$", re.I)
_TITLES = {"mdna": re.compile(r"management\W{0,4}s?\W{0,4}discussion", re.I),
           "risk": re.compile(r"risk\s*factors", re.I)}
_TITLE_WINDOW = 80
_XREF_WINDOW = 45

# start marker -> the markers that can end it, per form. The first END match after a START
# closes that candidate span; the LONGEST candidate wins, which is what discards the
# table-of-contents hit (in a TOC, "Item 7" is followed by "Item 8" a line later).
_SECTIONS = {
    "10-K": {"mdna": ("7", ("7a", "8")), "risk": ("1a", ("1b", "2"))},
    "10-Q": {"mdna": ("2", ("3", "4")), "risk": ("1a", ("2", "3", "4"))},
}


def _is_xref(text: str, pos: int) -> bool:
    return bool(_XREF_RX.search(text[max(0, pos - _XREF_WINDOW):pos]))


def extract_sections(text: str, form: str) -> dict:
    """{'mdna': str|None, 'risk': str|None} by Item-heading heuristic.

    HEURISTIC, and filings do not obey a schema — so a section that cannot be isolated comes
    back None (missing), never an empty string that would silently score as "changed
    completely". Coverage is reported by the runner.
    """
    spec = _SECTIONS.get(form)
    if not spec or not text:
        return {"mdna": None, "risk": None}
    out = {}
    for name, (start_item, end_items) in spec.items():
        title = _TITLES[name]
        starts = [m.end() for m in _item_rx(start_item).finditer(text)
                  if not _is_xref(text, m.start())
                  and title.search(text[m.end():m.end() + _TITLE_WINDOW])]
        ends = sorted(m.start() for e in end_items for m in _item_rx(e).finditer(text)
                      if not _is_xref(text, m.start()))
        best = None
        for s in starts:
            nxt = [e for e in ends if e > s + 50]
            if not nxt:
                continue
            span = text[s:nxt[0]]
            if best is None or len(span) > len(best):
                best = span
        out[name] = best if (best and len(best.split()) >= MIN_SECTION_WORDS) else None
    return out


# --------------------------------------------------------------------------- #
#  similarity
# --------------------------------------------------------------------------- #
def cosine(a: dict, b: dict) -> Optional[float]:
    """Cosine on raw term counts — the paper's measure. No corpus, so no look-ahead."""
    if not a or not b:
        return None
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    dot = sum(v * large.get(k, 0) for k, v in small.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0 or nb <= 0:
        return None
    return dot / (na * nb)


def jaccard(a: dict, b: dict) -> Optional[float]:
    if not a or not b:
        return None
    sa, sb = set(a), set(b)
    union = len(sa | sb)
    return (len(sa & sb) / union) if union else None


def tfidf_cosine(a: dict, b: dict, df: dict, n_docs: int) -> Optional[float]:
    """Cosine on sublinear-tf x smoothed-idf vectors.

    `df`/`n_docs` MUST be the point-in-time corpus (documents filed strictly before the date
    this pair becomes usable). With an empty corpus every idf is equal and this degenerates
    to a cosine on log-scaled counts — informative but not the same statistic, which is why
    `idf_docs` is written on every row.
    """
    if not a or not b:
        return None

    def vec(c):
        out = {}
        for k, v in c.items():
            if v <= 0:
                continue
            idf = math.log((1.0 + n_docs) / (1.0 + df.get(k, 0))) + 1.0
            out[k] = (1.0 + math.log(v)) * idf
        norm = math.sqrt(sum(x * x for x in out.values()))
        return out, norm

    va, na = vec(a)
    vb, nb = vec(b)
    if na <= 0 or nb <= 0:
        return None
    small, large = (va, vb) if len(va) <= len(vb) else (vb, va)
    dot = sum(v * large.get(k, 0.0) for k, v in small.items())
    return dot / (na * nb)


# --------------------------------------------------------------------------- #
#  EDGAR
# --------------------------------------------------------------------------- #
def fetch_ticker_cik_map(limiter: RateLimiter, cache_path: Optional[str] = None) -> dict:
    """{TICKER: cik_int} from SEC's public mapping. TODAY snapshot — see the caveat up top."""
    if cache_path and os.path.exists(cache_path):
        try:
            with open(cache_path, encoding="utf-8") as f:
                return {k: int(v) for k, v in json.load(f).items()}
        except Exception:                                      # noqa: BLE001
            pass
    r = _get(TICKER_MAP, limiter, timeout=60)
    if r is None or r.status_code != 200:
        return {}
    out = {}
    for row in r.json().values():
        t = (row.get("ticker") or "").strip().upper()
        if t:
            out[t] = int(row["cik_str"])
    _log(f"ticker->cik: {len(out):,} companies")
    if cache_path:
        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(out, f)
    return out


# Tickers whose filing history does NOT live under the CIK SEC's ticker map points at.
# A holdco reorganization registers a successor entity and the history stays with the
# predecessor, so the mapped CIK looks like a company that has never filed a 10-K. Found by
# noticing XOM came back with zero filings — a coverage check, not a guess. Values are
# [predecessor, successor]: both are fetched and merged into one continuous history.
CIK_OVERRIDES = {
    "XOM": [34088, 2115436],        # Exxon Mobil Corp -> ExxonMobil Holdings Corp (0 filings
                                    #   under the mapped CIK, 42 under the predecessor)
    "BLK": [1364742, 2012383],      # BlackRock Inc -> BlackRock Funding (35 + 7, split 2024-08)
}


def load_cik_overrides(out_dir: str) -> dict:
    """Built-in overrides, plus any `<out-dir>/cik_overrides.json` ({"TICKER": cik or [ciks]}).

    A file so the next reorganization is a one-line data fix rather than a code change.
    """
    out = {k: list(v) for k, v in CIK_OVERRIDES.items()}
    p = os.path.join(out_dir, "cik_overrides.json")
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                for k, v in json.load(f).items():
                    out[k.strip().upper()] = v if isinstance(v, list) else [v]
        except Exception as e:                                 # noqa: BLE001
            _log(f"cik_overrides.json ignored ({e})")
    return out


def _rows_from_block(block: dict, cik: int = 0) -> list:
    """One EDGAR filings block (`recent` or a shard) -> list of filing dicts."""
    forms = block.get("form") or []
    out = []
    for i, form in enumerate(forms):
        if form not in FORMS:                 # exact match: excludes 10-K/A, 10-KT, NT 10-K
            continue

        def g(key):
            v = block.get(key) or []
            return v[i] if i < len(v) else ""

        out.append({"form": form,
                    "cik": cik,               # kept per filing: a ticker can span two CIKs
                    "accession": g("accessionNumber"),
                    "filing_date": g("filingDate"),
                    "report_date": g("reportDate"),
                    "primary_doc": g("primaryDocument")})
    return out


def list_filings(cik: int, limiter: RateLimiter, since: str = "", session=None) -> list:
    """Every 10-K / 10-Q for a CIK, ascending by filing date.

    `recent` holds the last ~1,000 filings; anything older lives in shard files, which are
    only fetched when `since` actually reaches back that far.
    """
    r = _get(SUBMISSIONS.format(cik=cik), limiter, session=session)
    if r is None or r.status_code != 200:
        return []
    j = r.json()
    filings = j.get("filings") or {}
    rows = _rows_from_block(filings.get("recent") or {}, cik)
    oldest = min((x["filing_date"] for x in rows if x["filing_date"]), default="")
    for shard in filings.get("files") or []:
        if since and oldest and (shard.get("filingTo") or "") < since:
            continue
        rs = _get(SUBMISSION_SHARD.format(name=shard.get("name", "")), limiter, session=session)
        if rs is not None and rs.status_code == 200:
            rows.extend(_rows_from_block(rs.json(), cik))
    if since:
        rows = [x for x in rows if (x["filing_date"] or "") >= since]
    rows = [x for x in rows if x["accession"] and x["filing_date"]]
    rows.sort(key=lambda x: (x["filing_date"], x["accession"]))
    return rows


def document_url(cik: int, accession: str, primary_doc: str) -> tuple:
    """(url, doc_source). Filings with no primaryDocument (mostly pre-2001) fall back to the
    complete submission text, which INCLUDES EXHIBITS — flagged so those rows can be filtered
    rather than silently mixed with primary-document rows."""
    acc = accession.replace("-", "")
    if primary_doc:
        return ARCHIVE.format(cik=cik, acc=acc, doc=primary_doc), "primary"
    return FULL_TXT.format(cik=cik, acc=acc, acc_dashed=accession), "full"


def _apply_sections(rec: dict, text: str) -> dict:
    """Recompute the section token counts on a record from its plain text."""
    secs = extract_sections(text, rec["form"])
    for name in ("mdna", "risk"):
        body = secs.get(name)
        st = tokenize(body) if body else []
        rec[f"{name}_words"] = len(st)
        rec[f"{name}_counts"] = dict(Counter(st)) if st else None
    return rec


def fetch_document(cik: int, filing: dict, limiter: RateLimiter, session=None) -> dict:
    """Download one filing and reduce it to token counts.

    The stripped plain text comes back under `_text` so the caller can put it in the text
    cache; it is never stored in the scoring cache, which has to stay small enough to hold
    the whole universe in memory at once.
    """
    url, source = document_url(cik, filing["accession"], filing["primary_doc"])
    r = _get(url, limiter, session=session)
    rec = dict(filing)
    rec["doc_source"] = source
    rec["url"] = url
    if r is None:
        rec["error"] = "request_failed"
        return rec
    if r.status_code != 200:
        rec["error"] = f"http_{r.status_code}"
        return rec
    text = html_to_text(r.text)
    toks = tokenize(text)
    if len(toks) < MIN_DOC_WORDS:
        rec["error"] = "too_short"
        rec["n_words"] = len(toks)
        return rec
    rec["error"] = None
    rec["n_chars"] = len(text)
    rec["n_words"] = len(toks)
    rec["counts"] = dict(Counter(toks))
    rec["_text"] = text
    return _apply_sections(rec, text)


# --------------------------------------------------------------------------- #
#  per-ticker cache (resumability lives here)
# --------------------------------------------------------------------------- #
def cache_path(out_dir: str, ticker: str) -> str:
    return os.path.join(out_dir, "cache", f"{ticker.upper()}.pkl.gz")


def text_cache_path(out_dir: str, ticker: str) -> str:
    return os.path.join(out_dir, "text", f"{ticker.upper()}.pkl.gz")


def _load_gz(path: str, label: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with gzip.open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:                                     # noqa: BLE001
        _log(f"{label}: unreadable cache ({e}) — treating as absent")
        return {}


def _save_gz(path: str, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with gzip.open(tmp, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)                  # atomic: a killed run never leaves a torn cache


def load_cache(out_dir: str, ticker: str) -> dict:
    return _load_gz(cache_path(out_dir, ticker), ticker)


def save_cache(out_dir: str, ticker: str, docs: dict):
    _save_gz(cache_path(out_dir, ticker), docs)


def load_text_cache(out_dir: str, ticker: str) -> dict:
    return _load_gz(text_cache_path(out_dir, ticker), f"{ticker} text")


def rebuild_sections(ticker: str, out_dir: str) -> tuple:
    """Recompute mdna/risk counts from the TEXT cache — no network.

    Section extraction is the most heuristic part of this module and it has already been
    wrong once (cross-references read as headings). Keeping the plain text means the next
    correction costs seconds instead of re-downloading the corpus. Returns (updated, total).
    """
    texts = load_text_cache(out_dir, ticker)
    if not texts:
        return (0, 0)
    docs = load_cache(out_dir, ticker)
    n = 0
    for acc, rec in docs.items():
        if rec.get("error") or acc not in texts:
            continue
        _apply_sections(rec, texts[acc])
        n += 1
    if n:
        save_cache(out_dir, ticker, docs)
    return (n, len(docs))


def build_ticker_cache(ticker: str, cik, out_dir: str, limiter: RateLimiter,
                       since: str = "", workers: int = 4, retry_errors: bool = False,
                       keep_text: bool = True, session=None) -> dict:
    """Fetch+tokenize every not-yet-cached 10-K/10-Q for one ticker. Returns {accession: rec}.

    `cik` may be a LIST. A holdco reorganization moves a company to a new CIK and leaves its
    filing history under the old one — SEC's ticker map points at the new entity, so XOM
    resolved to "ExxonMobil Holdings Corp" with ZERO 10-Ks while 42 sat under CIK 34088.
    A ticker spanning both CIKs is a normal, continuous filing history and is treated as one.
    """
    docs = load_cache(out_dir, ticker)
    ciks = cik if isinstance(cik, (list, tuple)) else [cik]
    listed, seen = [], set()
    for c in ciks:
        for f in list_filings(int(c), limiter, since=since, session=session):
            if f["accession"] not in seen:
                seen.add(f["accession"])
                listed.append(f)
    listed.sort(key=lambda x: (x["filing_date"], x["accession"]))
    todo = [f for f in listed
            if f["accession"] not in docs
            or (retry_errors and docs[f["accession"]].get("error"))]
    if todo:
        texts = load_text_cache(out_dir, ticker) if keep_text else {}

        def flush():
            save_cache(out_dir, ticker, docs)
            if keep_text and texts:
                _save_gz(text_cache_path(out_dir, ticker), texts)

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            fetch = lambda f: fetch_document(f.get("cik") or ciks[0], f, limiter,   # noqa: E731
                                             session=session)
            for rec in pool.map(fetch, todo):
                text = rec.pop("_text", None)
                if keep_text and text:
                    texts[rec["accession"]] = text
                docs[rec["accession"]] = rec
                done += 1
                if done % SAVE_EVERY == 0:      # so killing it mid-ticker loses ~nothing
                    flush()
        flush()
    ok = sum(1 for d in docs.values() if not d.get("error"))
    _log(f"{ticker}: {len(listed)} listed, {len(todo)} fetched, {ok}/{len(docs)} usable")
    return docs


# --------------------------------------------------------------------------- #
#  pairing + scoring
# --------------------------------------------------------------------------- #
def _days(a: str, b: str) -> Optional[int]:
    """Days from b to a, both YYYY-MM-DD."""
    from datetime import date
    try:
        ya, ma, da = (int(x) for x in a[:10].split("-"))
        yb, mb, db = (int(x) for x in b[:10].split("-"))
        return (date(ya, ma, da) - date(yb, mb, db)).days
    except Exception:                                          # noqa: BLE001
        return None


def find_prior(filing: dict, earlier: list) -> Optional[dict]:
    """The same-form filing from ~a year earlier, or None.

    Matched on `report_date` (fiscal period) so a 10-Q meets the same quarter a year back;
    falls back to filing_date when a period is missing. `earlier` must already be restricted
    to filings that were PUBLIC before this one — the caller guarantees that.
    """
    ref = filing.get("report_date") or filing.get("filing_date")
    best, best_err = None, None
    for cand in earlier:
        if cand["form"] != filing["form"]:
            continue
        cref = cand.get("report_date") or cand.get("filing_date")
        gap = _days(ref, cref)
        if gap is None or not (PAIR_MIN_DAYS <= gap <= PAIR_MAX_DAYS):
            continue
        err = abs(gap - PAIR_TARGET_DAYS)
        if best_err is None or err < best_err:
            best, best_err = cand, err
    return best


def score_ticker(ticker: str, docs: dict, df: dict, n_docs: int) -> list:
    """Score one ticker's filings against the CURRENT point-in-time IDF corpus.

    Caller drives the chronology: `df`/`n_docs` are the corpus as of each filing's date, so
    this is only correct when invoked from `score_all`, which walks every ticker's filings in
    global filing-date order. Kept separate anyway because a single ticker is what you want
    when debugging one name.
    """
    usable = sorted((d for d in docs.values() if not d.get("error") and d.get("counts")),
                    key=lambda d: (d["filing_date"], d["accession"]))
    rows = []
    for i, doc in enumerate(usable):
        prior = find_prior(doc, usable[:i])
        if prior is None:
            continue
        rows.append(_score_pair(ticker, doc, prior, df, n_docs))
    return rows


def _score_pair(ticker: str, doc: dict, prior: dict, df: dict, n_docs: int) -> dict:
    row = {"ticker": ticker,
           "form": doc["form"],
           "available_from": doc["filing_date"],       # THE date — see module docstring
           "report_date": doc.get("report_date") or "",
           "accession": doc["accession"],
           "prior_accession": prior["accession"],
           "prior_filing_date": prior["filing_date"],
           "gap_days": _days(doc.get("report_date") or doc["filing_date"],
                             prior.get("report_date") or prior["filing_date"]),
           "doc_source": doc.get("doc_source", ""),
           "prior_doc_source": prior.get("doc_source", ""),
           "n_words": doc.get("n_words"),
           "prior_n_words": prior.get("n_words"),
           "word_growth": (doc["n_words"] / prior["n_words"] - 1.0)
                          if prior.get("n_words") else None,
           "idf_docs": n_docs,
           "cosine_tf": cosine(doc["counts"], prior["counts"]),
           "jaccard": jaccard(doc["counts"], prior["counts"]),
           "cosine_tfidf": tfidf_cosine(doc["counts"], prior["counts"], df, n_docs)}
    for name in ("mdna", "risk"):
        a, b = doc.get(f"{name}_counts"), prior.get(f"{name}_counts")
        row[f"{name}_cosine_tf"] = cosine(a, b) if (a and b) else None
        row[f"{name}_jaccard"] = jaccard(a, b) if (a and b) else None
        row[f"{name}_words"] = doc.get(f"{name}_words")
    return row


def score_all(cached: dict) -> list:
    """Score every ticker with a POINT-IN-TIME IDF corpus.

    `cached` is {ticker: {accession: rec}}. Filings are walked in global filing-date order;
    a pair dated D is scored against document frequencies from filings strictly BEFORE D,
    and same-day filings are only folded into the corpus after the whole day is scored (so
    a filing can never contribute to its own IDF). This is the one piece of machinery that
    stops the dataset being quietly contaminated — do not "optimise" it by fitting the IDF
    over everything at once.
    """
    stream = []
    for ticker, docs in cached.items():
        usable = sorted((d for d in docs.values() if not d.get("error") and d.get("counts")),
                        key=lambda d: (d["filing_date"], d["accession"]))
        for i, doc in enumerate(usable):
            stream.append((doc["filing_date"], ticker, doc, usable[:i]))
    stream.sort(key=lambda x: (x[0], x[1], x[2]["accession"]))

    df: dict = {}
    n_docs = 0
    rows, pending = [], []
    cur_date = None
    for fdate, ticker, doc, earlier in stream:
        if fdate != cur_date:
            for d in pending:                      # yesterday's filings join the corpus now
                for tok in d["counts"]:
                    df[tok] = df.get(tok, 0) + 1
                n_docs += 1
            pending, cur_date = [], fdate
        prior = find_prior(doc, earlier)
        if prior is not None:
            rows.append(_score_pair(ticker, doc, prior, df, n_docs))
        pending.append(doc)
    rows.sort(key=lambda r: (r["available_from"], r["ticker"]))
    return rows


# --------------------------------------------------------------------------- #
#  universe
# --------------------------------------------------------------------------- #
def large_cap_universe(limit: int = 60, data_dir: str = os.path.join("data", "backtest")) -> list:
    """Today's largest names by market cap, from the Sharadar DAILY bulk cache.

    Falls back to the fundamentals export, then to the bundled screener list, so this runs
    with no licensed data at all — just on a worse universe. SURVIVOR-ONLY either way; see
    the caveat in the module docstring.
    """
    caps = {}
    try:
        from ..edge.bulk import _load_cache
        prepared = os.path.join(os.path.dirname(os.path.normpath(data_dir)), "bulk", "prepared")
        daily = _load_cache("daily", prepared) or {}
        # STALENESS FILTER. Ranking on last-known market cap alone puts long-dead giants in
        # "today's large caps": the first run pulled in TWX (last quoted 2018), RAI (2017) and
        # WLA, which SEC's ticker map cannot resolve, so 17 slots produced nothing. Require a
        # quote within a year of the cache's own latest date.
        latest = max((r[0] for rows in daily.values() if rows for r in rows), default="")
        cutoff = f"{int(latest[:4]) - 1}{latest[4:]}" if latest else ""
        for tk, rows in daily.items():
            if not rows:
                continue
            last = max(rows, key=lambda r: r[0])
            if last[1] and (not cutoff or last[0] >= cutoff):
                caps[tk.upper()] = float(last[1])
    except Exception as e:                                     # noqa: BLE001
        _log(f"DAILY cache unavailable ({e})")
    if not caps:
        try:
            import csv as _csv
            with open(os.path.join(data_dir, "fundamentals.csv"), encoding="utf-8") as f:
                for r in _csv.DictReader(f):
                    mc = r.get("marketcap")
                    if mc:
                        tk = (r.get("ticker") or "").upper()
                        caps[tk] = max(float(mc), caps.get(tk, 0.0))
        except Exception as e:                                 # noqa: BLE001
            _log(f"fundamentals.csv unavailable ({e})")
    if caps:
        ranked = sorted(caps.items(), key=lambda kv: -kv[1])
        return [t for t, _ in ranked[:limit]]
    try:
        from ..screener.universe import bundled_tickers
        _log("falling back to the bundled screener universe (no market-cap ranking)")
        return list(bundled_tickers())[:limit]
    except Exception:                                          # noqa: BLE001
        return []


# --------------------------------------------------------------------------- #
#  output
# --------------------------------------------------------------------------- #
COLUMNS = ["ticker", "form", "available_from", "report_date", "accession", "prior_accession",
           "prior_filing_date", "gap_days", "doc_source", "prior_doc_source",
           "cosine_tf", "jaccard", "cosine_tfidf",
           "mdna_cosine_tf", "mdna_jaccard", "mdna_words",
           "risk_cosine_tf", "risk_jaccard", "risk_words",
           "n_words", "prior_n_words", "word_growth", "idf_docs"]


def write_dataset(rows: list, out_dir: str) -> list:
    """CSV always; parquet too when pyarrow is installed (it is not, in this environment)."""
    import csv as _csv

    os.makedirs(out_dir, exist_ok=True)
    written = []
    csv_path = os.path.join(out_dir, "lazy_prices.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = _csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in COLUMNS})
    written.append(csv_path)
    try:
        import pandas as pd
        pq = os.path.join(out_dir, "lazy_prices.parquet")
        pd.DataFrame(rows, columns=COLUMNS).to_parquet(pq, index=False)
        written.append(pq)
    except Exception as e:                                     # noqa: BLE001
        _log(f"parquet not written ({type(e).__name__}: {e}) — CSV is the dataset")
    return written


def coverage_report(cached: dict, rows: list, requested: list, unmapped: list,
                    no_filings: Optional[list] = None) -> dict:
    """What got a score, what did not, and WHY. A coverage number that only counts successes
    is how five factors sat empty in this project for a year — the skip reasons are the point."""
    listed = sum(len(d) for d in cached.values())
    errs: Counter = Counter()
    ok = 0
    for docs in cached.values():
        for d in docs.values():
            if d.get("error"):
                errs[d["error"]] += 1
            else:
                ok += 1
    scored_acc = {r["accession"] for r in rows}
    unpaired = ok - len(scored_acc)

    # SHORT-HISTORY DETECTOR. XOM was caught because it returned ZERO filings; BLK returns
    # SEVEN, which looks like a working ticker unless something compares it to its peers. Both
    # are the same fault — a holdco reorganization split the history across two CIKs — and a
    # 7-of-42 history is the more dangerous one because nothing about it looks broken. Every
    # ticker under 60% of the universe median is listed for a human to resolve into
    # CIK_OVERRIDES; the alternative is a factor that is quietly missing years of data.
    per_ticker = {t: sum(1 for d in docs.values() if not d.get("error"))
                  for t, docs in cached.items()}
    counts = sorted(per_ticker.values())
    median = counts[len(counts) // 2] if counts else 0
    floor = 0.6 * median
    short = []
    for t, n in sorted(per_ticker.items(), key=lambda kv: kv[1]):
        if median and n < floor:
            fd = sorted(d["filing_date"] for d in cached[t].values() if not d.get("error"))
            short.append({"ticker": t, "filings": n,
                          "first": fd[0] if fd else "", "last": fd[-1] if fd else ""})
    by_form = Counter(r["form"] for r in rows)
    dates = [r["available_from"] for r in rows]

    def _mean(key, subset=None):
        vals = [r[key] for r in (subset if subset is not None else rows)
                if r.get(key) is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    return {
        "tickers_requested": len(requested),
        "tickers_unmapped_to_cik": unmapped,
        # Mapped to a CIK but filing no 10-K/10-Q at all — overwhelmingly foreign issuers
        # (TSM, ASML, HSBC file 20-F) and trusts/ETFs. Structurally out of scope, not a bug.
        "tickers_no_10k_10q": no_filings or [],
        "tickers_with_filings": sum(1 for d in cached.values() if d),
        "tickers_scored": len({r["ticker"] for r in rows}),
        "filings_listed": listed,
        "filings_parsed_ok": ok,
        "filings_failed": dict(errs),
        "filings_scored": len(rows),
        "filings_ok_but_unpaired": unpaired,
        "median_filings_per_ticker": median,
        "tickers_short_history": short,
        "short_history_note": ("Under 60% of the universe median. Usually a genuinely younger "
                               "company (recent IPO), but a holdco reorganization splitting "
                               "the history across two CIKs looks exactly like this — see "
                               "CIK_OVERRIDES. BLK returned 7 of ~42 for that reason."),
        "unpaired_note": ("No same-form filing 270-450 days earlier — the first year of any "
                          "ticker's history can never pair, by construction."),
        "pct_of_parsed_scored": round(100.0 * len(rows) / ok, 1) if ok else 0.0,
        "by_form": dict(by_form),
        "date_range": [min(dates), max(dates)] if dates else [],
        "section_coverage_pct": {
            "mdna": round(100.0 * sum(1 for r in rows if r.get("mdna_cosine_tf") is not None)
                          / len(rows), 1) if rows else 0.0,
            "risk": round(100.0 * sum(1 for r in rows if r.get("risk_cosine_tf") is not None)
                          / len(rows), 1) if rows else 0.0,
        },
        "doc_source": dict(Counter(r["doc_source"] for r in rows)),
        "mean_similarity": {"cosine_tf": _mean("cosine_tf"),
                            "jaccard": _mean("jaccard"),
                            "cosine_tfidf": _mean("cosine_tfidf"),
                            "mdna_cosine_tf": _mean("mdna_cosine_tf"),
                            "risk_cosine_tf": _mean("risk_cosine_tf")},
        "rows_with_thin_idf_corpus": sum(1 for r in rows if (r.get("idf_docs") or 0) < 100),
        "orientation": "HIGHER similarity = lazy = the paper's BULLISH read. Not negated here.",
        "gate": "Dataset only. No IC, no keep/reject, not wired into the panel.",
    }


def write_report_md(cov: dict, path: str, out_dir: str = DEFAULT_OUT_DIR) -> str:
    """Human-readable coverage report, written OUTSIDE data/ so it can be committed.

    The dataset itself is gitignored (data/), so this markdown is the only record of what the
    build actually covered. Skip reasons are reported, not just successes — a coverage number
    that counts only what worked is how five factors sat empty in this project for a year.
    """
    def pct(n, d):
        return f"{100.0 * n / d:.1f}%" if d else "n/a"

    ok = cov.get("filings_parsed_ok", 0)
    listed = cov.get("filings_listed", 0)
    dr = cov.get("date_range") or ["", ""]
    ms = cov.get("mean_similarity", {})
    sc = cov.get("section_coverage_pct", {})
    L = [
        "# Lazy Prices — 10-K/10-Q language-change dataset: coverage report",
        "",
        "Generated by `python -m valuation.research.lazy_prices`. The dataset itself lives in "
        f"`{out_dir.replace(os.sep, '/')}/lazy_prices.csv` and is **gitignored**, so this file "
        "is the committed record.",
        "",
        "**What it is.** Year-over-year document similarity between a company's consecutive "
        "same-type filings (Cohen-Malloy-Nguyen). **HIGHER similarity = 'lazy' = the paper's "
        "bullish read** — orientation fixed in advance and not negated anywhere in the code.",
        "",
        "**What it is NOT.** No IC, no keep/reject, not wired into the panel. The gated test "
        "(CPCV / held-out) runs later, on this dataset.",
        "",
        "## Universe",
        "",
        f"- Tickers requested: **{cov.get('tickers_requested', 0)}**",
        f"- Not in SEC's ticker->CIK map: **{len(cov.get('tickers_unmapped_to_cik') or [])}**",
        f"- Mapped but filing no 10-K/10-Q: **{len(cov.get('tickers_no_10k_10q') or [])}** — "
        f"`{', '.join(cov.get('tickers_no_10k_10q') or []) or 'none'}`",
        "",
        "  Mostly foreign issuers (20-F) and trusts/ETFs, which are structurally out of scope. "
        "**But check this list every run**: a holdco reorganization looks identical here. XOM "
        "resolved to a successor entity with zero 10-Ks while 42 filings sat under the "
        "predecessor CIK; it is fixed via `CIK_OVERRIDES` / `cik_overrides.json`, which fetch "
        "both CIKs and merge them into one history.",
        f"- Tickers with at least one scored pair: **{cov.get('tickers_scored', 0)}**",
        "",
        "## Filings",
        "",
        "| | count | |",
        "|---|---:|---|",
        f"| 10-K/10-Q attempted (no amendments) | {listed:,} | every one EDGAR listed for these "
        "tickers in the window |",
        f"| downloaded and parsed | {ok:,} | {pct(ok, listed)} of listed |",
        f"| **scored (paired with a prior-year filing)** | **{cov.get('filings_scored', 0):,}** "
        f"| {cov.get('pct_of_parsed_scored', 0)}% of parsed |",
        f"| parsed but unpaired | {cov.get('filings_ok_but_unpaired', 0):,} | "
        "no same-form filing 270-450 days earlier — the first year of any ticker's history "
        "can never pair, by construction |",
        "",
        f"Failures by reason: `{cov.get('filings_failed') or 'none'}`",
        "",
        f"By form: `{cov.get('by_form')}`  |  Date range (availability dates): "
        f"**{dr[0]} to {dr[1]}**" if dr and dr[0] else "",
        "",
        "## Short histories — resolve these, do not ignore them",
        "",
        f"Median filings per ticker: **{cov.get('median_filings_per_ticker', 0)}**. "
        f"Tickers under 60% of it: **{len(cov.get('tickers_short_history') or [])}**.",
        "",
        cov.get("short_history_note", ""),
        "",
        "| ticker | filings | first | last |",
        "|---|---:|---|---|",
    ] + [f"| {s['ticker']} | {s['filings']} | {s['first']} | {s['last']} |"
         for s in (cov.get("tickers_short_history") or [])[:40]] + [
        "",
        "## Section isolation (heuristic — Item headings)",
        "",
        f"- MD&A isolated on **{sc.get('mdna', 0)}%** of scored pairs",
        f"- Risk Factors isolated on **{sc.get('risk', 0)}%** of scored pairs",
        "",
        "A section that cannot be isolated is written as MISSING, never as an empty string "
        "(which would score as 'the company rewrote it completely').",
        "",
        "## Mean similarity (sanity, not a result)",
        "",
        "| measure | mean |",
        "|---|---:|",
    ]
    for k in ("cosine_tf", "jaccard", "cosine_tfidf", "mdna_cosine_tf", "risk_cosine_tf"):
        L.append(f"| `{k}` | {ms.get(k)} |")
    L += [
        "",
        f"Rows computed against a thin (<100 document) point-in-time IDF corpus: "
        f"**{cov.get('rows_with_thin_idf_corpus', 0):,}** — the earliest rows have little "
        "corpus to draw on. Every row carries `idf_docs` so they can be filtered downstream.",
        "",
        "## Caveats to carry into the IC test",
        "",
        "1. **Survivor-only universe.** Today's large caps, so a first-pass IC is a "
        "survivors' IC. Not survivorship-free like the Sharadar panel.",
        "2. **Today's ticker->CIK map** (SEC `company_tickers.json`) applied to history — the "
        "same caveat already recorded for the 13D map and the sector map.",
        "3. **Section extraction is a heuristic** and was wrong once already (cross-references "
        "read as headings). Trust `cosine_tf` / `jaccard` on the FULL document first; the "
        "section measures are secondary.",
        "4. **10-Q risk sections are heterogeneous** — often just 'no material changes', "
        "sometimes the full list. `risk_words` is on every row; filter on it.",
        "5. **Amendments (10-K/A) are excluded** and rows built from a complete text "
        "submission rather than the primary document are flagged `doc_source=\"full\"` "
        "(they include exhibits and are not comparable to `primary` rows).",
        "",
        f"_Build time: {cov.get('elapsed_sec', 0)}s._",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(x for x in L if x is not None))
    return path


# --------------------------------------------------------------------------- #
#  runner
# --------------------------------------------------------------------------- #
def run(tickers: list, out_dir: str = DEFAULT_OUT_DIR, since: str = "", workers: int = 4,
        req_per_sec: float = REQ_PER_SEC, retry_errors: bool = False,
        score_only: bool = False, rebuild_sections_only: bool = False,
        keep_text: bool = True, report_path: str = "") -> dict:
    import requests

    os.makedirs(out_dir, exist_ok=True)
    limiter = RateLimiter(req_per_sec)
    session = requests.Session()
    tickers = [t.strip().upper() for t in tickers if t.strip()]
    offline = score_only or rebuild_sections_only

    cik_map = {} if offline else fetch_ticker_cik_map(
        limiter, os.path.join(out_dir, "ticker_cik.json"))
    # Sharadar writes class shares as BRK.B, SEC as BRK-B. Without this the largest names in
    # the universe silently map to nothing.
    if cik_map:
        for tk in list(cik_map):
            if "-" in tk:
                cik_map.setdefault(tk.replace("-", "."), cik_map[tk])
        cik_map.update(load_cik_overrides(out_dir))
    unmapped = [t for t in tickers if t not in cik_map] if cik_map else []

    cached, t0, rebuilt, no_filings = {}, time.time(), 0, []
    for i, tk in enumerate(tickers, 1):
        if rebuild_sections_only:
            n, _tot = rebuild_sections(tk, out_dir)
            rebuilt += n
            docs = load_cache(out_dir, tk)
        elif score_only:
            docs = load_cache(out_dir, tk)
        elif tk in cik_map:
            docs = build_ticker_cache(tk, cik_map[tk], out_dir, limiter, since=since,
                                      workers=workers, retry_errors=retry_errors,
                                      keep_text=keep_text, session=session)
        else:
            _log(f"{tk}: no CIK in SEC's mapping — skipped")
            continue
        if docs:
            cached[tk] = docs
        elif not offline:
            no_filings.append(tk)
        if i % 10 == 0:
            _log(f"{i}/{len(tickers)} tickers, {time.time()-t0:.0f}s")

    rows = score_all(cached)
    paths = write_dataset(rows, out_dir)
    cov = coverage_report(cached, rows, tickers, unmapped, no_filings)
    cov["elapsed_sec"] = round(time.time() - t0, 1)
    if rebuild_sections_only:
        cov["sections_rebuilt"] = rebuilt
    cov["files"] = paths
    with open(os.path.join(out_dir, "coverage.json"), "w", encoding="utf-8") as f:
        json.dump(cov, f, indent=2)
    if report_path:
        write_report_md(cov, report_path, out_dir)
        _log(f"coverage report -> {report_path}")
    _log(f"{len(rows):,} scored pairs over {cov['tickers_scored']} tickers "
         f"-> {paths[0]} ({cov['elapsed_sec']}s)")
    return cov


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the lazy-prices 10-K/10-Q similarity dataset")
    ap.add_argument("--tickers", default="", help="comma-separated; default = large-cap tier")
    ap.add_argument("--tickers-file", default="", help="one ticker per line")
    ap.add_argument("--limit", type=int, default=60, help="universe size when tickers not given")
    ap.add_argument("--since", default="2015-01-01", help="earliest FILING date to fetch")
    ap.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    ap.add_argument("--data-dir", default=os.path.join("data", "backtest"),
                    help="Sharadar exports, used only to rank the universe by market cap")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--req-per-sec", type=float, default=REQ_PER_SEC)
    ap.add_argument("--retry-errors", action="store_true", help="refetch filings that failed")
    ap.add_argument("--score-only", action="store_true",
                    help="re-score from cache, download nothing")
    ap.add_argument("--rebuild-sections", action="store_true",
                    help="recompute MD&A/risk sections from the text cache, then re-score")
    ap.add_argument("--report", default="LAZY_PRICES_COVERAGE.md",
                    help="markdown coverage report path (outside data/, so it can be committed)")
    ap.add_argument("--no-text-cache", action="store_true",
                    help="do not keep stripped filing text (saves disk, forbids --rebuild-sections)")
    a = ap.parse_args(argv)

    if a.tickers:
        tickers = a.tickers.split(",")
    elif a.tickers_file:
        with open(a.tickers_file, encoding="utf-8") as f:
            tickers = [ln.strip() for ln in f if ln.strip()]
    elif a.score_only or a.rebuild_sections:
        tickers = [os.path.basename(p)[:-7] for p in
                   sorted(_glob_cache(a.out_dir))]
    else:
        tickers = large_cap_universe(a.limit, a.data_dir)
    if not tickers:
        _log("no tickers — nothing to do")
        return 1
    _log(f"{len(tickers)} tickers, filings since {a.since or 'inception'}")
    run(tickers, out_dir=a.out_dir, since=a.since, workers=a.workers,
        req_per_sec=a.req_per_sec, retry_errors=a.retry_errors, score_only=a.score_only,
        rebuild_sections_only=a.rebuild_sections, keep_text=not a.no_text_cache,
        report_path=a.report)
    return 0


def _glob_cache(out_dir: str) -> list:
    import glob
    return glob.glob(os.path.join(out_dir, "cache", "*.pkl.gz"))


if __name__ == "__main__":
    raise SystemExit(main())
