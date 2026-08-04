"""
Insider (SEC Form 4) signal — free, from EDGAR.

Open-market insider *buying* (transaction code P), especially clustered buying by
senior officers, is one of the few fundamentally-grounded sentiment signals with
real evidence behind it. We weight buys heavily, penalize sales, scale by role and
reward multiple distinct buyers, then map to a 0–100 score (50 = neutral / no
recent activity). Ported from the screener project's weighting scheme.

Network-dependent (EDGAR). A name with no recent Form 4 activity scores 50 (neutral),
which is an honest answer. A name whose filings we FAILED to read scores `None` — not
50 — because "we could not look" and "we looked and saw nothing" are different claims
and collapsing them is what made this signal a constant for every ticker (see
`form4_xml_url`).
"""
from __future__ import annotations

import math
import re
import datetime as _dt
from xml.etree import ElementTree as ET

from ..config import CONFIG
from ..data import edgar as _edgar

CODE_WEIGHTS = {"P": 1.0, "M": 0.15, "A": 0.0, "S": -1.0, "F": 0.0}
ROLE_WEIGHTS = {"CEO": 1.5, "CFO": 1.4, "Pres": 1.3, "Officer": 1.1, "Dir": 1.0, "10%": 1.2}


def _headers(cfg):
    return {"User-Agent": cfg.sec_user_agent, "Accept-Encoding": "gzip, deflate"}


def _role_multiplier(rel_text: str) -> float:
    t = (rel_text or "").lower()
    if "chief executive" in t or t.strip() == "ceo":
        return ROLE_WEIGHTS["CEO"]
    if "chief financial" in t or "cfo" in t:
        return ROLE_WEIGHTS["CFO"]
    if "president" in t:
        return ROLE_WEIGHTS["Pres"]
    if "officer" in t:
        return ROLE_WEIGHTS["Officer"]
    if "10" in t and "%" in t:
        return ROLE_WEIGHTS["10%"]
    return ROLE_WEIGHTS["Dir"]


class Form4ParseError(Exception):
    """A Form 4 document could not be parsed as XML. Never swallowed into a neutral score."""


# EDGAR's `primaryDocument` for a Form 4 is the XSL-RENDERED view — e.g.
# `xslF345X06/form4.xml` — which despite the .xml suffix serves an HTML page
# (`<!DOCTYPE html ...>`). Feeding that to ET.fromstring raises, and the old code
# swallowed the raise and returned [], so EVERY name scored a neutral 50 on every run.
# The raw XML sits at the SAME path with the `xslF345X0N/` directory removed.
# Verified live 2026-08-04 on AAPL 0001140361-26-025622:
#   .../000114036126025622/xslF345X06/form4.xml -> HTML, 18,351 bytes, ParseError
#   .../000114036126025622/form4.xml            -> XML,   7,692 bytes, parses
_XSL_RENDER_DIR = re.compile(r"^xslF345X\d{2}/", re.I)


def form4_xml_url(cik: int, accession: str, primary_document: str) -> str:
    """URL of the RAW Form 4 XML, not EDGAR's rendered HTML view."""
    doc = _XSL_RENDER_DIR.sub("", (primary_document or "").strip())
    return (f"https://www.sec.gov/Archives/edgar/data/{cik}/"
            f"{(accession or '').replace('-', '')}/{doc}")


def _parse_form4(xml_text: str):
    """Return list of {code, value_usd, role_mult} from a Form 4 XML doc.

    Raises Form4ParseError if the document is not parseable XML — the caller counts
    and surfaces that. Returning [] here (the old behaviour) is indistinguishable from
    "this insider genuinely transacted nothing", which is why the bug went unnoticed.
    """
    out = []
    try:
        root = ET.fromstring(xml_text)
    except Exception as e:
        head = (xml_text or "")[:80].replace("\n", " ")
        raise Form4ParseError(f"{type(e).__name__}: {e} | document starts: {head!r}") from e
    # reporting owner role
    rel = root.find(".//reportingOwner/reportingOwnerRelationship")
    role_txt = ""
    if rel is not None:
        if (rel.findtext("isOfficer") or "").strip() in ("1", "true"):
            role_txt = rel.findtext("officerTitle") or "Officer"
        elif (rel.findtext("isDirector") or "").strip() in ("1", "true"):
            role_txt = "Director"
        elif (rel.findtext("isTenPercentOwner") or "").strip() in ("1", "true"):
            role_txt = "10%"
    role_mult = _role_multiplier(role_txt)
    for tx in root.findall(".//nonDerivativeTable/nonDerivativeTransaction"):
        code = (tx.findtext(".//transactionCoding/transactionCode") or "").strip()
        shares = _num(tx.findtext(".//transactionAmounts/transactionShares/value"))
        price = _num(tx.findtext(".//transactionAmounts/transactionPricePerShare/value"))
        val = (shares or 0) * (price or 0)
        out.append({"code": code, "value_usd": val, "role_mult": role_mult})
    return out


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def insider_detail(ticker: str, cfg=CONFIG, days: int = 90) -> dict:
    """The scorer with its bookkeeping exposed.

    Returns {score, form4_seen, parsed, parse_failures, fetch_failures, error}. `score`
    is None whenever we could not read the filings we found — a refusal, not a neutral.
    """
    st = {"score": None, "form4_seen": 0, "parsed": 0, "parse_failures": 0,
          "fetch_failures": 0, "error": ""}
    try:
        import requests
        cik = _edgar.resolve_cik(ticker, cfg)
        if cik is None:
            st["error"] = "CIK not resolved"
            return st
        sub = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
                           headers=_headers(cfg), timeout=20).json()
        recent = sub.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accns = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        dates = recent.get("filingDate", [])
        cutoff = (_dt.date.today() - _dt.timedelta(days=days)).isoformat()

        pressure = 0.0
        buyers = 0
        for form, accn, doc, fdate in zip(forms, accns, docs, dates):
            if form != "4" or fdate < cutoff:
                continue
            st["form4_seen"] += 1
            url = form4_xml_url(cik, accn, doc)
            try:
                xml = requests.get(url, headers=_headers(cfg), timeout=20).text
            except Exception as e:
                st["fetch_failures"] += 1
                st["error"] = st["error"] or f"fetch: {type(e).__name__}"
                continue
            try:
                txns = _parse_form4(xml)
            except Form4ParseError as e:
                st["parse_failures"] += 1
                st["error"] = st["error"] or str(e)
                continue
            st["parsed"] += 1
            filing_buy = False
            for t in txns:
                cw = CODE_WEIGHTS.get(t["code"], 0.0)
                if cw == 0.0:
                    continue
                pressure += cw * t["role_mult"] * math.sqrt(max(0.0, t["value_usd"]))
                if cw > 0:
                    filing_buy = True
            if filing_buy:
                buyers += 1

        # Found filings but read NONE of them: refuse rather than return a neutral that
        # looks like evidence of no insider activity.
        if st["form4_seen"] and st["parsed"] == 0:
            return st

        if pressure == 0.0 and buyers == 0:
            st["score"] = 50.0     # genuinely quiet (or no Form 4s in the window)
            return st
        # squash: neutral 50, +/-40 by tanh, +cluster bonus for multiple buying filings.
        scale = 4000.0   # ~ sqrt($16M) reference
        score = 50.0 + 40.0 * math.tanh(pressure / scale)
        score += min(10.0, 3.0 * max(0, buyers - 1))
        st["score"] = float(max(0.0, min(100.0, score)))
        return st
    except Exception as e:
        st["error"] = st["error"] or f"{type(e).__name__}: {e}"
        return st


def insider_score(ticker: str, cfg=CONFIG, days: int = 90):
    """0–100 quality-weighted insider signal (50 = neutral), or None if unreadable.

    None is deliberate: the old contract returned a confident 50 on every failure, and
    since the URL was wrong for 99%+ of Form 4s, EVERY name scored exactly 50 forever.
    """
    return insider_detail(ticker, cfg, days)["score"]


def enrich_insider(rows: list, cfg=CONFIG, top: int = 25) -> list:
    """Attach insider_score to the top `top` rows (network calls; best-effort).

    Also attaches `insider_detail` so a run that silently reads nothing is visible in the
    output instead of looking like a market with no insider activity.
    """
    unreadable = 0
    for r in rows[:top]:
        d = insider_detail(r["ticker"], cfg)
        extra = r.setdefault("extra", {})
        extra["insider_score"] = d["score"]
        extra["insider_detail"] = {k: d[k] for k in
                                   ("form4_seen", "parsed", "parse_failures", "fetch_failures")}
        if d["score"] is None:
            unreadable += 1
    if unreadable:
        print(f"  insider: {unreadable} of {len(rows[:top])} names unreadable "
              f"(Form 4 fetch/parse failed) — scored None, not 50.")
    return rows
