"""
edgar.py — SEC EDGAR data layer (free, authoritative).

Pulls fundamentals (XBRL company-facts), insider Form 4 transactions, recent
8-K item types, the full filer list, and a recent-Form-4 firehose for the
intraday poller.

EDGAR requires a User-Agent header identifying you (set EDGAR_USER_AGENT in .env,
e.g. "Don Corbin don@example.com") and rate-limits to ~10 requests/sec.

NOTE: XBRL concept names vary across filers and statements get restated, so the
fundamentals extraction uses multiple concept fallbacks and prefers the most
recent annual (10-K / FY) value. This module is the one most in need of
live validation against real tickers — tune the concept lists as needed.
"""

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime
import requests
import datetime as _dt

UA = os.getenv("EDGAR_USER_AGENT", "screener someone@example.com")
HEADERS = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
_TIMEOUT = 20
_LAST = [0.0]
_MIN_INTERVAL = 0.12  # ~8 req/sec, under EDGAR's limit


def _get(url):
    """Rate-limited GET with EDGAR headers."""
    wait = _MIN_INTERVAL - (time.time() - _LAST[0])
    if wait > 0:
        time.sleep(wait)
    _LAST[0] = time.time()
    r = requests.get(url, headers=HEADERS, timeout=_TIMEOUT)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
#  Ticker / CIK directory
# ---------------------------------------------------------------------------

_TICKER_MAP = None

def all_filers():
    """Return {TICKER: cik_int} from EDGAR's company_tickers.json (cached)."""
    global _TICKER_MAP
    if _TICKER_MAP is None:
        data = _get("https://www.sec.gov/files/company_tickers.json").json()
        _TICKER_MAP = {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}
    return _TICKER_MAP


def _cik10(ticker):
    cik = all_filers().get(ticker.upper())
    return f"{cik:010d}" if cik else None


# ---------------------------------------------------------------------------
#  Fundamentals (XBRL company facts)
# ---------------------------------------------------------------------------

REV_CONCEPTS = ["RevenueFromContractWithCustomerExcludingAssessedTax",
                "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]
OPINC_CONCEPTS = ["OperatingIncomeLoss"]
NI_CONCEPTS = ["NetIncomeLoss"]
DEBT_LT = ["LongTermDebtNoncurrent", "LongTermDebt"]
DEBT_CUR = ["LongTermDebtCurrent", "DebtCurrent"]
CASH = ["CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments"]
STI = ["ShortTermInvestments"]
SHARES = ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"]
DA_CONCEPTS = ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
               "DepreciationAndAmortization"]
EQUITY_CONCEPTS = ["StockholdersEquity",
                   "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"]


def _is_annual_duration(p, tol_days=45):
    """
    True if this datapoint covers roughly a YEAR.

    Flow concepts (revenue, net income) appear in companyfacts at 3, 6, 9 and
    12-month durations. Nothing in `form`/`fp` distinguishes them — a 10-K
    carries all four for the year it reports — so a duration check is the only
    reliable way to isolate the annual figure.

    Instant concepts (balance-sheet items) have no `start`, and are passed
    through unchanged.
    """
    start, end = p.get("start"), p.get("end")
    if not start or not end:
        return True                     # instant fact, not a duration
    try:
        d0 = _dt.date.fromisoformat(start)
        d1 = _dt.date.fromisoformat(end)
    except (TypeError, ValueError):
        return False
    return abs((d1 - d0).days - 365) <= tol_days


def _annual_series(facts, concepts):
    """
    Most-recent-first list of (period_end, value) for ANNUAL datapoints.

    THREE BUGS LIVED HERE, and all three silently produced wrong growth.

    1. KEYED BY THE WRONG YEAR. `fy`/`fp` describe the FILING's fiscal period,
       not the DATA's. A FY2023 10-K carries three years of comparatives and
       every one of them is tagged fy=2023, fp="FY". Keying on `fy` collapsed
       them into a single entry. Verified on a one-10-K filer: this returned
       [(2023, 1000)] when the filing contained 1000, 800 and 600. So
       `rev_hist` had one element, `latest_rev_growth` came back None, and
       growth_score fell back to neutral 50 — for a component carrying 30% of
       the Speculative weight, on exactly the recent-IPO names that bucket
       exists to find. Multi-year filers usually escaped by accident, because
       companyfacts happens to be ordered by `end` ascending.

    2. NO DURATION FILTER. Quarterly and annual values were mixed freely, so
       an annual "revenue" could silently be a Q3 figure.

    3. THE COMMENT LIED. It said "keep latest filed" — there was no `filed`
       comparison anywhere; it just relied on iteration order.

    Now keyed on `end` (the DATA period), duration-filtered to ~365 days, and
    genuinely resolving duplicates by latest `filed` — a restatement of the
    same period should win over the original.
    """
    usg = facts.get("facts", {}).get("us-gaap", {})
    dei = facts.get("facts", {}).get("dei", {})

    best: list = []
    for c in concepts:
        node = usg.get(c) or dei.get(c)
        if not node:
            continue
        units = node.get("units", {})
        series = units.get("USD") or units.get("shares") or next(iter(units.values()), [])

        by_end: dict = {}
        for p in series:
            if p.get("form") not in ("10-K", "20-F", "40-F"):
                continue
            if p.get("val") is None or not p.get("end"):
                continue
            if not _is_annual_duration(p):
                continue
            end, filed = p["end"], (p.get("filed") or "")
            prev = by_end.get(end)
            if prev is None or filed >= prev[0]:
                by_end[end] = (filed, p["val"])

        series_out = [(end, v) for end, (_, v) in
                      sorted(by_end.items(), key=lambda kv: kv[0], reverse=True)]
        # Prefer the RICHEST series rather than the first non-empty one. A filer
        # may report a stub `Revenues` tag alongside a full
        # `RevenueFromContractWithCustomer...` history; taking the first match
        # would pick the stub and throw away the history.
        if len(series_out) > len(best):
            best = series_out
    return best


def _latest(facts, concepts):
    s = _annual_series(facts, concepts)
    return s[0][1] if s else None


def get_fundamentals(ticker):
    """Return the data dict scoring.score_stock() consumes, or None."""
    cik = _cik10(ticker)
    if not cik:
        return None
    try:
        facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()
        sub = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    except Exception:
        return None

    rev_series = _annual_series(facts, REV_CONCEPTS)
    revenue = rev_series[0][1] if rev_series else None
    rev_hist = [v for _, v in rev_series]

    op_inc = _latest(facts, OPINC_CONCEPTS)
    ni = _latest(facts, NI_CONCEPTS)
    cash = (_latest(facts, CASH) or 0) + (_latest(facts, STI) or 0)
    total_debt = (_latest(facts, DEBT_LT) or 0) + (_latest(facts, DEBT_CUR) or 0)
    shares = _latest(facts, SHARES)

    # revenue growth (latest YoY) and prior YoY (for acceleration)
    def yoy(a, b):
        return (a / b - 1) if (a and b and b > 0) else None
    latest_rev_growth = yoy(rev_hist[0], rev_hist[1]) if len(rev_hist) >= 2 else None
    prior_rev_growth = yoy(rev_hist[1], rev_hist[2]) if len(rev_hist) >= 3 else None

    op_margin = (op_inc / revenue) if (op_inc is not None and revenue) else None
    da = _latest(facts, DA_CONCEPTS)
    equity = _latest(facts, EQUITY_CONCEPTS)
    ebitda = (op_inc + da) if (op_inc is not None and da is not None) else op_inc  # real EBITDA when D&A available
    roe = (ni / equity) if (ni is not None and equity and equity > 0) else None
    net_debt = (total_debt or 0) - (cash or 0)
    # None, NOT 0.0. `0.0` reads downstream as "zero net debt", which
    # quality_score rewards with FULL balance-sheet credit — so a company with
    # negative EBITDA scored a perfect leverage mark. None means "leverage is
    # not measurable here", and the weight renormalizes onto the factors that
    # are. (pit_data already handled this case correctly; the two modules
    # disagreed and the live pipeline used the wrong one.)
    nd_ebitda = (net_debt / ebitda) if (ebitda and ebitda > 0) else None

    sic = sub.get("sicDescription")
    name = sub.get("name")
    # crude common-equity check: exclude funds/trusts by entity type if present
    is_common = "fund" not in (sic or "").lower()

    return {
        "ticker": ticker.upper(), "name": name, "sector": sic,
        "is_common_equity": is_common,
        "revenue": revenue, "rev_hist": rev_hist, "operating_income": op_inc,
        "net_income": ni, "op_margin": op_margin, "roe": roe,
        "ebitda": ebitda, "da": da, "equity": equity,
        "latest_rev_growth": latest_rev_growth, "prior_rev_growth": prior_rev_growth,
        "total_debt": total_debt, "cash": cash, "net_debt": net_debt,
        "net_debt_to_ebitda": nd_ebitda, "shares": shares,
        "recent_8k_items": [],  # fetched fresh for candidate names (see pipeline); kept out of cache
    }


# ---------------------------------------------------------------------------
#  8-K item types (from the submissions feed)
# ---------------------------------------------------------------------------

def get_8k_items(ticker, sub=None, lookback=10):
    """Return a list of recent 8-K item codes (best-effort from primaryDocDescription)."""
    if sub is None:
        cik = _cik10(ticker)
        if not cik:
            return []
        try:
            sub = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
        except Exception:
            return []
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    items = recent.get("items", [])
    out = []
    for i, form in enumerate(forms[:lookback * 5]):
        if form == "8-K" and i < len(items) and items[i]:
            out.extend([x.strip() for x in items[i].split(",")])
    return out


# ---------------------------------------------------------------------------
#  Insider Form 4 transactions
# ---------------------------------------------------------------------------

def _parse_form4_xml(xml_text):
    """Parse one Form 4 XML into a list of {code, role, person, value_usd, date}."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out

    def txt(node, path):
        el = node.find(path)
        return el.text.strip() if (el is not None and el.text) else None

    owner = root.find(".//reportingOwner")
    person, role = None, "Dir"
    if owner is not None:
        person = txt(owner, ".//rptOwnerName")
        rel = owner.find(".//reportingOwnerRelationship")
        if rel is not None:
            title = txt(rel, "officerTitle") or ""
            if (txt(rel, "isOfficer") or "").lower() in ("1", "true"):
                t = title.lower()
                role = "CEO" if "chief executive" in t or "ceo" in t else \
                       "CFO" if "chief financial" in t or "cfo" in t else \
                       "Pres" if "president" in t else "Officer"
            elif (txt(rel, "isTenPercentOwner") or "").lower() in ("1", "true"):
                role = "10%"
            elif (txt(rel, "isDirector") or "").lower() in ("1", "true"):
                role = "Dir"

    for tx in root.findall(".//nonDerivativeTransaction"):
        code = txt(tx, ".//transactionCoding/transactionCode")
        shares = txt(tx, ".//transactionAmounts/transactionShares/value")
        price = txt(tx, ".//transactionAmounts/transactionPricePerShare/value")
        d = txt(tx, ".//transactionDate/value")
        value = None
        try:
            if shares and price:
                value = float(shares) * float(price)
        except ValueError:
            pass
        if code:
            out.append({"code": code, "role": role, "person": person,
                        "value_usd": value, "date": d})
    return out


def get_insider_txns(ticker, since=None, limit=10):
    """Recent insider transactions for a ticker (parses up to `limit` Form 4s)."""
    cik = _cik10(ticker)
    if not cik:
        return []
    try:
        sub = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
    except Exception:
        return []
    recent = sub.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accns = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    dates = recent.get("filingDate", [])
    txns, fetched = [], 0
    for i, form in enumerate(forms):
        if form != "4":
            continue
        if since and i < len(dates) and dates[i] < since:
            break
        accn = accns[i].replace("-", "")
        doc = docs[i] if i < len(docs) else None
        if not doc:
            continue
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn}/{doc}"
        try:
            txns.extend(_parse_form4_xml(_get(url).text))
        except Exception:
            pass
        fetched += 1
        if fetched >= limit:
            break
    return txns


def recent_form4(max_items=100):
    """
    Firehose for the intraday poller: recent Form 4 filings across all companies,
    via EDGAR's 'getcurrent' Atom feed. Returns [{ticker?, cik, accession, url}].
    """
    url = ("https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent"
           f"&type=4&company=&dateb=&owner=include&count={max_items}&output=atom")
    try:
        feed = _get(url).text
    except Exception:
        return []
    out = []
    try:
        root = ET.fromstring(feed)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            link = entry.find("a:link", ns)
            href = link.get("href") if link is not None else None
            if href:
                out.append({"url": href})
    except ET.ParseError:
        pass
    return out


def companyfacts(ticker):
    """Raw SEC companyfacts JSON for a ticker (rate-limited). Used by the point-in-time backtest."""
    cik = _cik10(ticker)
    if not cik:
        return None
    try:
        return _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()
    except Exception:
        return None


def sector(ticker):
    """Coarse sector (SIC description) for sector-relative value. One light submissions call."""
    cik = _cik10(ticker)
    if not cik:
        return None
    try:
        return _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json().get("sicDescription") or "?"
    except Exception:
        return None
