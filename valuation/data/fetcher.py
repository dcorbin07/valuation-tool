"""
Data orchestration: pull a company from the best available source(s).

Strategy (all free, no key required):
  1. Yahoo Finance (yfinance) — broad coverage, live market data + statements.
  2. SEC EDGAR — gap-fill / cross-check for US names when Yahoo is thin.
  3. If Yahoo fails entirely, try EDGAR standalone (US only).
  4. Attach the live risk-free rate.

A paid source (FMP etc.) can be slotted in ahead of Yahoo later via config; the
rest of the tool only ever sees the normalized CompanyData object.
"""
from __future__ import annotations

from typing import Optional

from ..config import CONFIG
from .models import CompanyData
from . import yahoo, edgar, macro


def get_company(ticker: str, cfg=CONFIG) -> CompanyData:
    ticker = ticker.strip().upper()
    cd: Optional[CompanyData] = None

    try:
        cd = yahoo.fetch(ticker)
    except Exception as e:
        cd = None
        _note = f"Yahoo fetch error: {e}"
    else:
        _note = None

    # Gap-fill with EDGAR for US names when core fields are missing.
    if cd is not None and (cd.revenue is None or cd.total_debt is None
                           or cd.shares_diluted is None or not cd.revenue_history):
        try:
            cd = edgar.enrich(cd, cfg)
        except Exception:
            pass

    # If Yahoo produced nothing usable, try EDGAR standalone.
    if cd is None or cd.revenue is None:
        try:
            ed = edgar.fetch(ticker, cfg)
            if ed is not None and ed.revenue is not None:
                if cd is None:
                    cd = ed
                else:
                    cd = edgar.enrich(cd, cfg)
        except Exception:
            pass

    if cd is None:
        cd = CompanyData(ticker=ticker)
        cd.quality_notes.append(f"Could not fetch data for {ticker} from any source.")
        if _note:
            cd.quality_notes.append(_note)

    # Attach live macro
    rf, rf_note = macro.risk_free_rate(cfg)
    cd.risk_free_rate = rf  # dynamic attribute consumed by WACC
    cd.sources.append(rf_note)

    return cd
