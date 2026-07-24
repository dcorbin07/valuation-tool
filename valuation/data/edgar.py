"""
SEC EDGAR adapter — authoritative US fundamentals (free, no key).

Used as a fallback / cross-check for US-listed companies when Yahoo is missing
fields. Pulls XBRL "company facts" and extracts annual (10-K) series.

SEC asks for a descriptive User-Agent with contact info (configurable).
"""
from __future__ import annotations

from typing import Optional
import requests

from .models import CompanyData, _safe

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

_REV = ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
        "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]
_OPINC = ["OperatingIncomeLoss"]
_NI = ["NetIncomeLoss"]
_CASH = ["CashCashEquivalentsAndShortTermInvestments", "CashAndCashEquivalentsAtCarryingValue"]
_DEBT_COMBINED = ["DebtLongtermAndShorttermCombinedAmount"]
_LTD = ["LongTermDebtNoncurrent", "LongTermDebt"]
_STD = ["LongTermDebtCurrent", "DebtCurrent"]
_DA = ["DepreciationDepletionAndAmortization", "DepreciationAmortizationAndAccretionNet",
       "DepreciationAndAmortization"]
_CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]
_SHARES = ["EntityCommonStockSharesOutstanding"]  # dei
_WADSO = ["WeightedAverageNumberOfDilutedSharesOutstanding"]

_cik_cache: dict = {}


def _headers(cfg):
    ua = getattr(cfg, "sec_user_agent", "valuation-tool contact@example.com")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def resolve_cik(ticker: str, cfg) -> Optional[int]:
    global _cik_cache
    ticker = ticker.upper()
    if not _cik_cache:
        try:
            r = requests.get(_TICKERS_URL, headers=_headers(cfg), timeout=20)
            r.raise_for_status()
            for row in r.json().values():
                _cik_cache[row["ticker"].upper()] = int(row["cik_str"])
        except Exception:
            return None
    return _cik_cache.get(ticker)


def _annual_series(facts: dict, concept_candidates, unit_hint=None):
    """Return recent-first list of (end_date, value) for the first matching concept."""
    ns_order = ["us-gaap", "dei", "ifrs-full"]
    for ns in ns_order:
        block = facts.get("facts", {}).get(ns, {})
        for c in concept_candidates:
            if c in block:
                units = block[c].get("units", {})
                # prefer USD, then shares, then anything
                unit_keys = ([unit_hint] if unit_hint else []) + ["USD", "shares"] + list(units.keys())
                for uk in unit_keys:
                    if uk and uk in units:
                        rows = [x for x in units[uk]
                                if x.get("form", "").startswith("10-K") and x.get("fp") == "FY"
                                and x.get("val") is not None and x.get("end")]
                        if not rows:
                            rows = [x for x in units[uk] if x.get("val") is not None and x.get("end")]
                        # dedupe by end date keeping latest filed
                        by_end = {}
                        for x in rows:
                            by_end[x["end"]] = x["val"]
                        series = sorted(by_end.items(), key=lambda kv: kv[0], reverse=True)
                        if series:
                            return series
    return []


def _latest(series):
    return _safe(series[0][1]) if series else None


def fetch(ticker: str, cfg) -> Optional[CompanyData]:
    """Build a CompanyData purely from EDGAR (US only). Returns None if not found."""
    cik = resolve_cik(ticker, cfg)
    if cik is None:
        return None
    try:
        r = requests.get(_FACTS_URL.format(cik=cik), headers=_headers(cfg), timeout=25)
        r.raise_for_status()
        facts = r.json()
    except Exception:
        return None

    cd = CompanyData(ticker=ticker.upper())
    cd.name = facts.get("entityName", ticker.upper())
    cd.sources.append("SEC EDGAR (XBRL company facts)")

    rev = _annual_series(facts, _REV, "USD")
    op = _annual_series(facts, _OPINC, "USD")
    ni = _annual_series(facts, _NI, "USD")

    cd.revenue = None if not rev else _latest(rev) / 1e6
    cd.revenue_history = [(_safe(v) / 1e6 if _safe(v) is not None else None) for _, v in rev[:6]]
    cd.fiscal_years = [end[:4] for end, _ in rev[:6]]
    cd.ebit = None if not op else _latest(op) / 1e6
    cd.ebit_history = [(_safe(v) / 1e6 if _safe(v) is not None else None) for _, v in op[:6]]
    cd.net_income = None if not ni else _latest(ni) / 1e6

    cash = _annual_series(facts, _CASH, "USD")
    cd.cash_sti = None if not cash else _latest(cash) / 1e6

    debt = _annual_series(facts, _DEBT_COMBINED, "USD")
    if debt:
        cd.total_debt = _latest(debt) / 1e6
    else:
        ltd = _annual_series(facts, _LTD, "USD")
        std = _annual_series(facts, _STD, "USD")
        tot = 0.0
        got = False
        if ltd:
            tot += _latest(ltd); got = True
        if std:
            tot += _latest(std); got = True
        cd.total_debt = tot / 1e6 if got else None

    da = _annual_series(facts, _DA, "USD")
    cd.da = None if not da else _latest(da) / 1e6
    capex = _annual_series(facts, _CAPEX, "USD")
    cd.capex = None if not capex else abs(_latest(capex)) / 1e6

    sh = _annual_series(facts, _SHARES, "shares") or _annual_series(facts, _WADSO, "shares")
    cd.shares_diluted = None if not sh else _latest(sh) / 1e6

    if cd.ebit_history and cd.revenue_history:
        cd.ebit_margin_history = [
            (e / r if (e is not None and r not in (None, 0)) else None)
            for e, r in zip(cd.ebit_history, cd.revenue_history)
        ]
    return cd


def enrich(cd: CompanyData, cfg) -> CompanyData:
    """Fill missing fields on an existing (Yahoo) CompanyData using EDGAR."""
    ed = fetch(cd.ticker, cfg)
    if ed is None:
        return cd
    filled = []
    for attr in ["revenue", "ebit", "net_income", "cash_sti", "total_debt",
                 "da", "capex", "shares_diluted"]:
        if getattr(cd, attr) is None and getattr(ed, attr) is not None:
            setattr(cd, attr, getattr(ed, attr))
            filled.append(attr)
    if not cd.revenue_history and ed.revenue_history:
        cd.revenue_history = ed.revenue_history
        cd.fiscal_years = ed.fiscal_years or cd.fiscal_years
    if not cd.ebit_history and ed.ebit_history:
        cd.ebit_history = ed.ebit_history
        cd.ebit_margin_history = ed.ebit_margin_history
    if filled:
        cd.sources.append("SEC EDGAR (gap-fill: " + ", ".join(filled) + ")")
    return cd
