"""THE COMPANY'S NAME, INDUSTRY AND DESCRIPTION FROM FREE SOURCES.  [item 57 A2]

WHY THIS EXISTS
---------------
Yahoo's `info` dictionary stopped answering on the server, and it was the sole source of five
things: the company's NAME, its INDUSTRY, its business DESCRIPTION, its vendor BETA, and its
next earnings date and analyst target. `fast_info` kept working, so price, shares and market cap
were fine and the page looked healthy -- while heading itself **"KNSL (KNSL)"** with no industry
and no description, because `cd.name` falls back to the ticker.

WHAT THE CAUSE IS, MEASURED RATHER THAN GUESSED
-----------------------------------------------
Both candidates in the brief were tested and **both are wrong**:

* **Not the yfinance version.** `info` returns 186 keys with correct names and betas on
  yfinance **1.3.0** AND on **1.6.0** -- the version the lockfile pins and the server runs --
  from this machine, today.
* **Not a blanket IP block.** `fast_info` works on the server at the same moment `info` fails.

`info` and `fast_info` hit **different Yahoo endpoints**: `info` reads `quoteSummary`, which is
gated behind a cookie-and-crumb handshake, while `fast_info` reads the chart/quote API, which is
not. So the live symptom -- one working and the other not, from one process -- points at the
**crumb handshake failing from the server's address**, not at the library and not at the host
being blocked. That is consistent with a datacenter IP: Yahoo gates `quoteSummary` and not the
chart API.

**IT IS ALSO NOT ITEM 54's RETRY.** That was the brief's third candidate and it is refuted by
size: the retry is capped at 300 attempts / 420s per scan and the proving scan spent **6
retries and 2.13 seconds** on Yahoo. A two-second burst once a day cannot throttle an address;
the daily scan's own ~500-name sweep dwarfs it and predates item 54.

**SO THIS MODULE DOES NOT TRY TO FIX YAHOO.** Nothing here can: the handshake fails at Yahoo's
end, for this address. What it does is make the page whole from sources that do answer, and make
the degradation VISIBLE instead of silent.

WHAT EACH FIELD COMES FROM, AND THE YIELD IT WAS KEPT ON
---------------------------------------------------------
Measured on the seven names the brief named -- AAPL, NVDA, TSLA, KO, KNSL, APLD, JPM:

| field | source | yield |
|---|---|---|
| name | SEC `company_tickers.json` title, then `submissions.name` | **7 of 7** |
| industry | SEC `submissions.sicDescription` | **7 of 7** |
| description | Wikipedia, searched then VERIFIED | **5 of 7, 0 wrong** |

`sicDescription` is a real industry label rather than a code -- "Fire, Marine & Casualty
Insurance" for KNSL, "National Commercial Banks" for JPM, "Semiconductors & Related Devices"
for NVDA -- and it is the regulator's own classification of the filer, which is a better
provenance than a vendor's taxonomy.

THE DESCRIPTION NEARLY SHIPPED WRONG, TWICE, AND THAT IS WHY THE GUARD IS WHAT IT IS
-------------------------------------------------------------------------------------
A Wikipedia summary looked like the obvious free description. Measured:

* **By title guess: 2 of 7, and one of the two was the FRUIT.** Asking for "Apple" returns
  *"An apple is the round, edible fruit of an apple tree"*; "Tesla" returns a disambiguation
  page.
* **By search plus a company-ish check: 5 of 7 correct and 2 CONFIDENTLY WRONG** -- KNSL got
  "Historical components of the S&P 400", and **APLD got "X Corp.", a fluent and accurate
  description of a completely different company.**

A description that is plausibly, fluently about the wrong business is worse than no description:
a reader cannot detect it. So acceptance requires the article to **share a distinctive word with
the company's own filed name** (`_name_tokens`), which rejects both of those and keeps the five
that are right. **An absent description is a state this page already renders; a wrong one is
not.** Every accepted description ships with its source name and a link to the article.
"""
from __future__ import annotations

import json
import re
import urllib.parse

from .recent import SEC_UA, _sec_get   # ONE EDGAR identity and rate gate for the project

#: Wikipedia's terms, carried so the page can name them. CC BY-SA requires attribution and a
#: link, which is why `description_source` and `description_url` are not optional.
WIKI_TERMS = ("Wikipedia, CC BY-SA 4.0 — attributed with a link to the article, as the licence "
              "requires. Summary text only; the article is not stored.")

#: Corporate suffixes that are not distinctive: every filer has one, so matching on them would
#: accept "X Corp." for "Applied Digital Corp." -- which is exactly what happened.
_SUFFIX = {"inc", "incorporated", "corp", "corporation", "co", "company", "companies", "plc",
           "ltd", "limited", "group", "holding", "holdings", "the", "and", "class", "common",
           "stock", "shares", "trust", "lp", "llc", "sa", "nv", "ag", "se", "spa", "ab"}

#: A company article says so in its own one-line description. A fruit does not, and neither
#: does a disambiguation page -- this is the first of the two gates.
_COMPANYISH = re.compile(
    r"\b(company|companies|corporation|corporate|conglomerate|bank|banking|insurer|insurance|"
    r"manufacturer|retailer|automaker|business|firm|enterprise|holding|multinational|"
    r"brand|chain|airline|utility|operator|developer|producer)\b", re.I)

#: Measured 2026-10-14 on the brief's seven names; see the module docstring.
MEASURED = {
    "date": "2026-10-14",
    "names": ["AAPL", "NVDA", "TSLA", "KO", "KNSL", "APLD", "JPM"],
    "name_from_sec": "7 of 7",
    "industry_from_sec": "7 of 7",
    "description_from_wikipedia": "5 of 7 accepted, 0 wrong",
    "description_rejected": {"KNSL": "search returned an S&P 400 index article",
                             "APLD": "search returned X Corp., a different company"},
}

_TICKER_MAP = {"loaded": False, "by_symbol": {}}


def _name_tokens(name: str) -> set:
    """The distinctive words in a filed company name, lower-cased.

    Corporate suffixes are dropped and so are words under three characters, because they are
    what made "X Corp." look like a match for "Applied Digital Corp.".
    """
    words = re.findall(r"[A-Za-z][A-Za-z0-9&']*", str(name or "").lower())
    return {w for w in words if len(w) >= 3 and w not in _SUFFIX}


def ticker_map() -> dict:
    """`{SYMBOL: (cik, title)}` from EDGAR's own ticker file. Cached per process."""
    if _TICKER_MAP["loaded"]:
        return _TICKER_MAP["by_symbol"]
    out = {}
    try:
        r = _sec_get("https://www.sec.gov/files/company_tickers.json")
        if getattr(r, "status_code", 0) == 200:
            for row in (r.json() or {}).values():
                sym = str(row.get("ticker") or "").upper().strip()
                if sym:
                    out[sym] = (int(row.get("cik_str")), str(row.get("title") or "").strip())
    except Exception:                                                       # noqa: BLE001
        out = {}
    # Cached even when EMPTY, deliberately: a failed fetch must not make every name on the page
    # re-request a 1MB file. The process restarts often enough on this host.
    _TICKER_MAP["by_symbol"] = out
    _TICKER_MAP["loaded"] = True
    return out


def sec_identity(ticker: str, cik=None) -> dict:
    """Name, industry and CIK for a filer, from SEC only. Never raises."""
    out = {"ticker": str(ticker or "").upper(), "cik": None, "name": "", "industry": "",
           "sic": "", "source": "SEC EDGAR",
           "terms": ("SEC: \"All Government-created content on sec.gov and EDGAR public filing "
                     "content are free to access and reuse.\""),
           "reason": ""}
    sym = out["ticker"]
    try:
        c = re.sub(r"\D", "", str(cik or ""))
        if c:
            out["cik"] = int(c)
        else:
            hit = ticker_map().get(sym)
            if hit:
                out["cik"], out["name"] = hit[0], hit[1]
        if out["cik"] is None:
            out["reason"] = "this symbol is not in EDGAR's ticker file"
            return out
        r = _sec_get("https://data.sec.gov/submissions/CIK%010d.json" % int(out["cik"]))
        if getattr(r, "status_code", 0) != 200:
            out["reason"] = "EDGAR returned HTTP %s" % getattr(r, "status_code", "?")
            return out
        d = r.json() or {}
        out["name"] = (d.get("name") or out["name"] or "").strip()
        out["industry"] = (d.get("sicDescription") or "").strip()
        out["sic"] = str(d.get("sic") or "").strip()
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the EDGAR identity could not be read (%s)" % type(e).__name__
    return out


def wikipedia_description(filed_name: str, *, get=None) -> dict:
    """A company description, or an empty one with the reason it is empty. Never raises.

    TWO GATES, and both were earned by a measured failure (see the module docstring): the
    article must describe a COMPANY, and it must share a distinctive word with the filed name.
    """
    out = {"text": "", "source": "", "url": "", "title": "", "terms": WIKI_TERMS,
           "reason": "", "candidates": 0, "rejected": []}
    want = _name_tokens(filed_name)
    # The LEAD distinctive word, in filed order -- `_name_tokens` returns a set, so the order
    # has to come from the name itself.
    lead = next((w for w in re.findall(r"[A-Za-z][A-Za-z0-9&']*", str(filed_name or "").lower())
                 if w in want), "")
    if not want or not lead:
        out["reason"] = "no filed company name to search on"
        return out

    def _fetch(url):
        if get is not None:
            return get(url)
        import requests
        return requests.get(url, headers={"User-Agent": SEC_UA}, timeout=20)

    q = re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9&.,' -]", " ", str(filed_name))).strip()
    try:
        r = _fetch("https://en.wikipedia.org/w/rest.php/v1/search/page?"
                   + urllib.parse.urlencode({"q": q, "limit": "4"}))
        if getattr(r, "status_code", 0) != 200:
            out["reason"] = "the article search returned HTTP %s" % getattr(
                r, "status_code", "?")
            return out
        pages = (r.json() or {}).get("pages") or []
    except Exception as e:                                                  # noqa: BLE001
        out["reason"] = "the article search could not be read (%s)" % type(e).__name__
        return out

    out["candidates"] = len(pages)
    for pg in pages:
        key = pg.get("key") or pg.get("title")
        if not key:
            continue
        try:
            rr = _fetch("https://en.wikipedia.org/api/rest_v1/page/summary/"
                        + urllib.parse.quote(str(key)))
            if getattr(rr, "status_code", 0) != 200:
                continue
            d = rr.json() or {}
        except Exception:                                                   # noqa: BLE001
            continue
        if d.get("type") != "standard":
            out["rejected"].append("%s (not an article)" % key)
            continue
        desc, extract = (d.get("description") or ""), (d.get("extract") or "").strip()
        if not (_COMPANYISH.search(desc) or _COMPANYISH.search(extract[:220])):
            out["rejected"].append("%s (not about a company)" % key)
            continue
        # GATE 2, THE IDENTITY GATE, and it took two tries to get right. Requiring ANY shared
        # distinctive word rejected "X Corp." and then ACCEPTED **"Western Digital"** for
        # Applied Digital Corp., because they share "digital". A company's identity is its LEAD
        # word -- Applied, Western, Apple, Kinsale -- so that is what has to match.
        got = _name_tokens(d.get("title") or key)
        if not lead or lead not in got:
            out["rejected"].append("%s (a different company)" % key)
            continue
        out["text"] = extract
        out["title"] = str(d.get("title") or key)
        out["source"] = "Wikipedia"
        out["url"] = (((d.get("content_urls") or {}).get("desktop") or {}).get("page")
                      or "https://en.wikipedia.org/wiki/" + urllib.parse.quote(str(key)))
        return out
    out["reason"] = ("no article matched this company by name, so no description is shown "
                     "rather than one about a different company")
    return out


def fill_from_free_sources(cd, *, want_description: bool = True) -> dict:
    """Fill a `CompanyData`'s name, industry and description where Yahoo left them empty.

    **IT ONLY EVER FILLS AN EMPTY FIELD.** Where Yahoo's `info` answered, Yahoo wins -- this is
    a fallback, not a second opinion, and two sources quietly disagreeing about a company's
    industry is worse than one source being absent. Returns what it did, for the page to show.
    """
    did = {"used": False, "name": None, "industry": None, "description": False,
           "description_source": "", "description_url": "", "reason": "",
           "sec": {}, "fields_filled": []}
    try:
        ticker = str(getattr(cd, "ticker", "") or "").upper()
        if not ticker:
            did["reason"] = "no ticker"
            return did
        # THE TEST FOR "YAHOO DID NOT ANSWER" IS THE NAME FALLING BACK TO THE TICKER, which is
        # what `yahoo.fetch` does when `info` is empty. Checking the quality note instead would
        # couple this to a sentence somebody may reword.
        name_missing = (not getattr(cd, "name", "")) or str(cd.name).upper() == ticker
        industry_missing = not (getattr(cd, "industry", "") or "").strip()
        summary_missing = not (getattr(cd, "business_summary", "") or "").strip()
        if not (name_missing or industry_missing or summary_missing):
            did["reason"] = "Yahoo supplied all three, so no fallback was needed"
            return did

        ident = sec_identity(ticker, cik=getattr(cd, "cik", None))
        did["sec"] = ident
        if name_missing and ident.get("name"):
            cd.name = ident["name"]
            did["name"] = ident["name"]
            did["fields_filled"].append("name")
        if industry_missing and ident.get("industry"):
            cd.industry = ident["industry"]
            did["industry"] = ident["industry"]
            did["fields_filled"].append("industry")
        if summary_missing and want_description:
            w = wikipedia_description(ident.get("name") or getattr(cd, "name", "") or ticker)
            if w.get("text"):
                cd.business_summary = w["text"]
                # THE SOURCE STAMP IS THE LICENCE CONDITION, not decoration.
                cd.business_summary_source = "%s — %s" % (w["source"], w["url"])
                did["description"] = True
                did["description_source"] = w["source"]
                did["description_url"] = w["url"]
                did["fields_filled"].append("description")
            else:
                did["reason"] = w.get("reason") or did["reason"]
        did["used"] = bool(did["fields_filled"])
        if did["used"]:
            # ONE SENTENCE ABOUT ONE STATE. `yahoo.fetch` has already said the provider did not
            # answer; this REPLACES that line rather than appending a second, so the page does
            # not carry two warnings describing the same outage from two points of view.
            _f = did["fields_filled"]
            got = (_f[0] if len(_f) == 1 else
                   " and ".join([", ".join(_f[:-1]), _f[-1]]))
            srcs = "SEC EDGAR" + (" and Wikipedia" if did["description"] else "")
            note = ("Some company details were unavailable from the market-data provider, so "
                    "the %s %s from %s instead. The price, share count and filed financial "
                    "statements the valuation is built from are unaffected."
                    % (got, "comes" if len(did["fields_filled"]) == 1 else "come", srcs))
            if not did["description"]:
                note += (" No company description is shown, because no article could be "
                         "matched to this company by name -- an absent description is better "
                         "than one about a different company.")
            notes = getattr(cd, "quality_notes", None)
            if isinstance(notes, list):
                from .yahoo import YAHOO_PROFILE_DOWN
                notes[:] = [n for n in notes if n != YAHOO_PROFILE_DOWN]
                if note not in notes:
                    notes.append(note)
            did["note"] = note
    except Exception as e:                                                  # noqa: BLE001
        did["reason"] = "the free fallback failed (%s)" % type(e).__name__
    return did
