"""RECENT EARNINGS AND HEADLINES, from free sources only.  [item 53 part 2]

WHAT THIS IS FOR
----------------
The valuation page shows the NEXT earnings date and nothing about the LAST one, and nothing at
all about what has been happening to the company. Both halves also go to the AI analysis, which
until now wrote from the page's numbers alone — its own label says so — so it could not know
that a company had just reported or just filed an 8-K.

THE HEADLINE SOURCE HAD TO BE MEASURED BEFORE IT COULD BE USED, AND THE OBVIOUS ONE IS DEAD
-------------------------------------------------------------------------------------------
`yfinance`'s `.news` returns **zero items** on this version (1.3.0) for every call shape tried —
`.news`, `get_news()`, `get_news(count=…)`, `get_news(tab="news")`. So the library already in
the dependency set carries no headlines at all.

Yahoo's **RSS** endpoint does work (18 items for NVDA), and it is a syndication feed served
without a key. But a symbol-requested feed is **not a feed about that symbol**, which is the
measurement that shaped this module: over 74 titles across NVDA, TSLA, KO and APLD on
2026-10-13, **31 — 42% — mention the company at all**, and for **NVDA it is 1 of 18 (6%)**. The
rest are about Citigroup, Goldman Sachs, Google, PepsiCo, Rivian, CoreWeave and so on. Handing
an NVDA analysis seventeen headlines about other companies would be worse than handing it none.

So the filter below is **mandatory rather than tidying**, and its yield ships with the result:
a reader and the model both need to know that "no headlines" here can mean "the feed had none
about this company", not "nothing is happening".

TWO SOURCES, BECAUSE ONE IS IMPURE AND THE OTHER IS PURE BY CONSTRUCTION
------------------------------------------------------------------------
* **SEC EDGAR filings** are about the company **by construction** — the feed is per-CIK — and
  their terms are unambiguous. The SEC's own webmaster FAQ: *"All Government-created content on
  sec.gov and EDGAR public filing content are free to access and reuse."* It asks callers to
  *"declare your user agent in request headers"* and states *"our current maximum access rate is
  10 requests per second"*; both are honoured below. These are **filings, not news**, and they
  are labelled as filings — an 8-K is a primary document rather than somebody's coverage of one,
  which for an analysis is better evidence, not worse.
* **Yahoo Finance RSS headlines**, filtered, labelled with their publisher, and carried with the
  filter's yield.

TITLES AND LINKS ONLY — STRUCTURALLY, NOT BY PROMISE
----------------------------------------------------
Nothing here ever requests an article URL. The RSS item's `title`, `link`, `pubDate` and
`source` are parsed and the `description` is **deliberately dropped**, so there is no path by
which article text could be stored, shown or sent to a model. A test holds it.

ESTIMATES ARE NOT AVAILABLE ON A FREE SOURCE, AND THAT IS REPORTED RATHER THAN FILLED IN
----------------------------------------------------------------------------------------
Don asked for revenue and EPS *"against estimates"* **where a free source has them**. Measured:
it does not. Consensus estimates are a licensed product — the project's own `D6` row records
that *"no retail point-in-time revisions exist at any price"* for the research panel, and the
live free stack carries no forward consensus either. So `estimates_available` is False with a
reason, and **no estimate is inferred, modelled or left as a plausible-looking blank**. An
absent comparison and a met expectation must not read the same.

THE TWO EARNINGS SOURCES AGREE, AND WHERE THEY DIFFER EDGAR IS RIGHT
--------------------------------------------------------------------
Measured on NVDA: `quarterly_income_stmt` gives diluted EPS **2.46** for a period it labels
**2026-07-31**, and EDGAR's XBRL gives **2.46** for a period ending **2026-07-26**, filed
**2026-08-26**. The EPS agrees; the dates do not, because yfinance rounds a fiscal quarter to
month-end. **EDGAR's period end is the real one and its `filed` date is the only source for
WHEN the quarter was reported**, which is the thing Don asked to see — so the dates come from
EDGAR and the revenue from yfinance, each labelled with where it came from.
"""
from __future__ import annotations

import datetime as _dt
import re
import time
import xml.etree.ElementTree as ET
from typing import Optional

#: The SEC asks callers to declare themselves. Don's address, as the other EDGAR caller in this
#: repo already uses -- one identity for the project rather than a second invented here.
SEC_UA = "Valquo (valquo.co) research donniecorbin6@gmail.com"

#: The SEC's stated ceiling is 10 requests per second. This is far under it; the gap is
#: deliberate, because a page can be loaded by several visitors at once and the limit is
#: per-IP rather than per-process, so a per-call sleep is the only thing this module can
#: actually guarantee.
SEC_MIN_INTERVAL_S = 0.2

#: Yahoo's per-symbol RSS. A syndication endpoint: no key, no auth, titles and links.
YAHOO_RSS = "https://feeds.finance.yahoo.com/rss/2.0/headline?s=%s&region=US&lang=en-US"

#: How many headlines to keep. Don asked for 3 to 5; this is the ceiling and the floor is
#: whatever the feed actually carries about the company, which on NVDA was ONE.
MAX_HEADLINES = 5

#: Measured on 2026-10-13 and recorded so a future reader can tell whether it has changed.
#: 31 of 74 titles across four tickers mentioned the company they were requested for.
FEED_PURITY_MEASURED = {"date": "2026-10-13", "titles": 74, "on_company": 31,
                        "share": 0.42, "worst_ticker": "NVDA", "worst": "1 of 18"}

_last_sec_call = [0.0]


def _sec_get(url: str, timeout: int = 30):
    """One EDGAR request, with the declared identity and a gap between calls."""
    import requests

    wait = SEC_MIN_INTERVAL_S - (time.time() - _last_sec_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_sec_call[0] = time.time()
    return requests.get(url, headers={"User-Agent": SEC_UA,
                                      "Accept-Encoding": "gzip, deflate"},
                        timeout=timeout)


def _iso(ts) -> str:
    try:
        return _dt.date.fromtimestamp(int(ts)).isoformat()
    except Exception:                                                       # noqa: BLE001
        return ""


def _rss_date(raw: str) -> str:
    """RFC-822 -> ISO date, or "" . The DATE only: a headline's time of day is noise."""
    raw = (raw or "").strip()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z",
                "%a, %d %b %Y %H:%M:%S"):
        try:
            return _dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return ""


def _company_keys(ticker: str, name: str) -> tuple:
    """Lower-case needles that mean "this title is about this company".

    Built from the ticker AND the company's own name, because a headline names the company far
    more often than the symbol. The name is trimmed of the corporate suffixes that never appear
    in a headline -- "NVIDIA Corporation" is written "Nvidia" -- and a one-word stem shorter
    than four characters is dropped rather than matched, because a two-letter stem matches
    everything. That is why `KO` is carried by "coca-cola" and not by "ko".
    """
    t = (ticker or "").strip().lower()
    keys = set()
    if len(t) >= 3:
        keys.add(t)
    nm = (name or "").strip().lower()
    for junk in (" corporation", " incorporated", " company", " holdings", " group",
                 " limited", " plc", ", inc.", " inc.", " inc", " corp.", " corp",
                 " co.", " ltd.", " ltd", " sa", " nv", " ag", " class a", " class b"):
        if nm.endswith(junk):
            nm = nm[: -len(junk)].strip()
    nm = nm.strip(" ,.")
    if len(nm) >= 4:
        keys.add(nm)
        # "Coca-Cola" is also written "Coca Cola".
        if "-" in nm:
            keys.add(nm.replace("-", " "))
    return tuple(sorted(keys))


def headlines(ticker: str, name: str = "", limit: int = MAX_HEADLINES) -> dict:
    """Recent headlines about this company: title, publisher, date and link. Never raises.

    `on_company` / `scanned` are the filter's yield and they are part of the answer, not
    diagnostics: "no headlines" has to be distinguishable from "the feed carried none about
    this company" (`V6`'s rule), and on NVDA the second is what happens.
    """
    out = {"available": False, "items": [], "source": "Yahoo Finance RSS",
           "terms": ("a public syndication feed, served without a key; titles, publishers, "
                     "dates and links only, with no article text requested or stored"),
           "scanned": 0, "on_company": 0, "filtered_out": 0, "reason": "",
           "keys": list(_company_keys(ticker, name))}
    if not out["keys"]:
        out["reason"] = "no usable company name or symbol to match a headline against"
        return out
    try:
        import requests

        r = requests.get(YAHOO_RSS % str(ticker or "").upper().strip(),
                         headers={"User-Agent": SEC_UA}, timeout=25)
        if r.status_code != 200 or not r.content:
            out["reason"] = "the headline feed returned HTTP %s" % r.status_code
            return out
        root = ET.fromstring(r.content)
        items = root.findall(".//item")
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the headline feed could not be read (%s)" % type(e).__name__
        return out

    out["scanned"] = len(items)
    keep = []
    for it in items:
        title = (it.findtext("title") or "").strip()
        if not title:
            continue
        low = title.lower()
        if not any(k in low for k in out["keys"]):
            continue
        # NOTE WHAT IS NOT READ: `description`. The feed carries a summary and this never
        # touches it, so no article text can reach the store, the page or the model.
        keep.append({"title": title,
                     "url": (it.findtext("link") or "").strip(),
                     "date": _rss_date(it.findtext("pubDate") or ""),
                     "publisher": (it.findtext("source") or "").strip() or "Yahoo Finance"})
    out["on_company"] = len(keep)
    out["filtered_out"] = max(0, out["scanned"] - len(keep))
    keep.sort(key=lambda x: x.get("date") or "", reverse=True)
    out["items"] = keep[: max(0, int(limit))]
    out["available"] = bool(out["items"])
    if not out["items"]:
        out["reason"] = ("the feed carried %d recent headlines and none of them named this "
                         "company" % out["scanned"])
    return out


def filings(cik, limit: int = 5) -> dict:
    """Recent SEC filings — about this company BY CONSTRUCTION. Never raises.

    The form type and its own description, dated and linked. 8-K is where a company announces
    results, a material agreement or a departure, so this is the closest thing to a "what has
    happened" feed that carries no terms problem at all.
    """
    out = {"available": False, "items": [], "source": "SEC EDGAR",
           "terms": ("SEC: \"All Government-created content on sec.gov and EDGAR public "
                     "filing content are free to access and reuse.\" Accessed with a declared "
                     "User-Agent, under the stated 10 requests/second ceiling."),
           "reason": "", "about_company": "by construction — the feed is this company's own"}
    try:
        c = re.sub(r"\D", "", str(cik or ""))
        if not c:
            out["reason"] = "no SEC company id (CIK) for this company"
            return out
        r = _sec_get("https://data.sec.gov/submissions/CIK%010d.json" % int(c))
        if r.status_code != 200:
            out["reason"] = "EDGAR returned HTTP %s" % r.status_code
            return out
        rec = ((r.json() or {}).get("filings") or {}).get("recent") or {}
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the EDGAR feed could not be read (%s)" % type(e).__name__
        return out

    forms = rec.get("form") or []
    dates = rec.get("filingDate") or []
    accs = rec.get("accessionNumber") or []
    docs = rec.get("primaryDocument") or []
    descs = rec.get("primaryDocDescription") or []
    items = []
    # The ownership forms are excluded: a company files dozens of Form 4s and they would crowd
    # out the 8-K that says what happened. They are not hidden -- the insider theme reads them
    # -- they are simply not "what has happened to this company" at this level.
    SKIP = {"4", "4/A", "3", "3/A", "5", "5/A", "144", "SC 13G/A", "SC 13G"}
    for i in range(min(len(forms), len(dates), len(accs))):
        f = str(forms[i] or "").strip()
        if f in SKIP:
            continue
        acc = str(accs[i] or "").replace("-", "")
        doc = str(docs[i]) if i < len(docs) else ""
        items.append({
            "form": f,
            "date": str(dates[i] or ""),
            "title": (str(descs[i]).strip() if i < len(descs) and descs[i] else "") or f,
            "url": ("https://www.sec.gov/Archives/edgar/data/%d/%s/%s"
                    % (int(c), acc, doc)) if doc else
                   ("https://www.sec.gov/Archives/edgar/data/%d/%s" % (int(c), acc)),
        })
        if len(items) >= max(0, int(limit)):
            break
    out["items"] = items
    out["available"] = bool(items)
    if not items:
        out["reason"] = "EDGAR lists no recent filings for this company other than ownership forms"
    return out


def last_reported_quarter(ticker: str, cik=None) -> dict:
    """The quarter just reported: when it ended, when it was reported, revenue and EPS.

    Dates from EDGAR (the fiscal period end and the FILING date — the only free source for
    when it was actually reported); revenue from the quarterly income statement. Each figure
    carries where it came from, because they are two vendors and they disagree about the
    period end by five days on NVDA.
    """
    out = {"available": False, "period_end": None, "reported_on": None, "fiscal": None,
           "revenue": None, "eps_diluted": None, "revenue_source": "", "eps_source": "",
           "dates_source": "", "estimates_available": False,
           "estimates_reason": ("consensus revenue and EPS estimates are a licensed product; "
                                "no free source on this stack carries them, so no comparison "
                                "against expectations is shown rather than one being guessed"),
           "reason": ""}
    # ---- EDGAR: the authoritative period end, the filing date, and EPS ----
    try:
        c = re.sub(r"\D", "", str(cik or ""))
        if c:
            r = _sec_get("https://data.sec.gov/api/xbrl/companyconcept/CIK%010d/"
                         "us-gaap/EarningsPerShareDiluted.json" % int(c))
            if r.status_code == 200:
                units = ((r.json() or {}).get("units") or {}).get("USD/shares") or []
                q = [u for u in units
                     if u.get("fp") in ("Q1", "Q2", "Q3", "Q4")
                     and u.get("form") in ("10-Q", "10-K") and u.get("end")]
                # The LATEST period end, and within it the latest filing -- a restatement
                # files the same period again and the newer filing is the one that stands.
                q.sort(key=lambda u: (u.get("end") or "", u.get("filed") or ""))
                if q:
                    u = q[-1]
                    out["period_end"] = u.get("end")
                    out["reported_on"] = u.get("filed")
                    out["fiscal"] = "%s %s" % (u.get("fp") or "", u.get("fy") or "")
                    out["eps_diluted"] = u.get("val")
                    out["eps_source"] = "SEC EDGAR (XBRL, as filed)"
                    out["dates_source"] = "SEC EDGAR (fiscal period end and filing date)"
    except Exception:                                                       # noqa: BLE001
        pass
    # ---- Revenue, from the statement the project already fetches ----
    try:
        import yfinance as yf

        q = yf.Ticker(str(ticker or "").upper()).quarterly_income_stmt
        if q is not None and len(q.columns):
            col = q.columns[0]
            for row in ("Total Revenue", "Operating Revenue"):
                if row in q.index:
                    v = q.loc[row, col]
                    if v is not None:
                        out["revenue"] = float(v)
                        out["revenue_source"] = "Yahoo Finance quarterly income statement"
                        break
            if out["period_end"] is None:
                # No EDGAR period end, so fall back to the statement's own column label and
                # SAY SO -- yfinance rounds a fiscal quarter to month-end, which is why this
                # is the fallback rather than the source.
                out["period_end"] = str(col)[:10]
                out["dates_source"] = ("Yahoo Finance quarterly income statement "
                                       "(month-end approximation)")
            if out["eps_diluted"] is None and "Diluted EPS" in q.index:
                ev = q.loc["Diluted EPS", col]
                if ev is not None:
                    out["eps_diluted"] = float(ev)
                    out["eps_source"] = "Yahoo Finance quarterly income statement"
    except Exception:                                                       # noqa: BLE001
        pass

    out["available"] = bool(out["period_end"] and
                            (out["revenue"] is not None or out["eps_diluted"] is not None))
    if not out["available"]:
        out["reason"] = "no free source carried a completed quarter for this company"
    return out


def recent_block(ticker: str, name: str = "", cik=None) -> dict:
    """Everything part 2 adds, in one object, for the page and the AI analysis."""
    return {
        "ticker": str(ticker or "").upper(),
        "last_quarter": last_reported_quarter(ticker, cik=cik),
        "headlines": headlines(ticker, name=name),
        "filings": filings(cik),
        "feed_purity_measured": dict(FEED_PURITY_MEASURED),
    }
