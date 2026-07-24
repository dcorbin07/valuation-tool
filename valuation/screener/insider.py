"""
Insider (SEC Form 4) signal — free, from EDGAR.

Open-market insider *buying* (transaction code P), especially clustered buying by
senior officers, is one of the few fundamentally-grounded sentiment signals with
real evidence behind it. We weight buys heavily, penalize sales, scale by role and
reward multiple distinct buyers, then map to a 0–100 score (50 = neutral / no
recent activity). Ported from the screener project's weighting scheme.

Network-dependent (EDGAR); returns 50 (neutral) on any failure, so it never blocks.
"""
from __future__ import annotations

import math
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


def _parse_form4(xml_text: str):
    """Return list of {code, value_usd, role_mult} from a Form 4 XML doc."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out
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


def insider_score(ticker: str, cfg=CONFIG, days: int = 90) -> float:
    """0–100 quality-weighted insider signal (50 = neutral)."""
    try:
        import requests
        cik = _edgar.resolve_cik(ticker, cfg)
        if cik is None:
            return 50.0
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
            acc = accn.replace("-", "")
            url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
            try:
                xml = requests.get(url, headers=_headers(cfg), timeout=20).text
            except Exception:
                continue
            txns = _parse_form4(xml)
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

        if pressure == 0.0 and buyers == 0:
            return 50.0
        # squash: neutral 50, +/-40 by tanh, +cluster bonus for multiple buying filings.
        scale = 4000.0   # ~ sqrt($16M) reference
        score = 50.0 + 40.0 * math.tanh(pressure / scale)
        score += min(10.0, 3.0 * max(0, buyers - 1))
        return float(max(0.0, min(100.0, score)))
    except Exception:
        return 50.0


def enrich_insider(rows: list, cfg=CONFIG, top: int = 25) -> list:
    """Attach insider_score to the top `top` rows (network calls; best-effort)."""
    for r in rows[:top]:
        s = insider_score(r["ticker"], cfg)
        r.setdefault("extra", {})["insider_score"] = s
    return rows
