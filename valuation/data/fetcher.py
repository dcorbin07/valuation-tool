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

import re as _re

from typing import Optional

from ..config import CONFIG
from .models import CompanyData
from . import yahoo, edgar, macro


#: A share class written with a dot, which the ordinary vendor symbol spells with a hyphen.
#:
#: ITEM 25. `BRK.B` returned sector `""`, industry `""`, regime `unknown`, price `None` -- and
#: then **a score of 40 and a recommendation of "Reduce"**. `BRK-B` on the same service returned
#: `financial`, price 502.65, score 63, "Hold". Same company, two spellings, and one of them
#: produced a recommendation out of nothing.
#:
#: NARROW BY DESIGN: one to five letters, a dot, then a SINGLE letter. That is the US
#: share-class form (BRK.B, BF.B, LEN.B) and nothing else matches it -- not an index (`^GSPC`),
#: not a pair (`BTC-USD`), not a decimal. Widening it to "any dot" would start rewriting
#: symbols nobody asked about, and the failure direction there is a silent lookup of the WRONG
#: company rather than a clean miss.
_SHARE_CLASS_DOT = _re.compile(r"^([A-Z]{1,5})\.([A-Z])$")


def normalise_ticker(ticker: str) -> str:
    """The vendor spelling of a user-typed symbol. Idempotent; a no-op for everything else."""
    t = (ticker or "").strip().upper()
    m = _SHARE_CLASS_DOT.match(t)
    return "%s-%s" % (m.group(1), m.group(2)) if m else t


def looks_not_found(cd) -> bool:
    """Did EVERY source come back with nothing for this symbol?

    **A NAMED PREDICATE BECAUSE A MUTATION WALKED THROUGH WITHOUT ONE.** The rule was inline in
    `get_company`, and changing its `and` to an `or` -- which would refuse any real company
    missing any ONE of the three fields -- was caught by nothing: the suite's positive control
    used AAPL, which has all three, so the disjunction is INERT for it. **A control that cannot
    distinguish the two versions is not a control**, and the shape of the fix is to give the
    rule a name so it can be driven directly with the case that separates them.

    THE CONJUNCTION IS THE WHOLE POINT. A price, a revenue AND a share count all absent means
    nothing was found. **Any ONE of them present means something was**, and that is not a
    technicality: a pre-revenue biotech has a price and no revenue, a thin ADR can have revenue
    and no usable share count, a company mid-halt has revenue and shares and no live quote. An
    `or` here would refuse all three as "not found", which is the one direction this refusal
    must never fail in -- it would turn a data gap into a claim that the company does not exist.
    """
    return (getattr(cd, "price", None) is None
            and getattr(cd, "revenue", None) is None
            and getattr(cd, "shares_diluted", None) is None)


def get_company(ticker: str, cfg=CONFIG) -> CompanyData:
    # ITEM 25 -- normalise BEFORE the first fetch, not after it fails. Retrying on failure would
    # work too and would be worse: it makes the hyphen form a FALLBACK, so the two spellings
    # take different code paths and only one of them is exercised by anything.
    _asked = (ticker or "").strip().upper()
    ticker = normalise_ticker(ticker)
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


    # ITEM 25 -- NOT FOUND, MARKED AFTER EVERY SOURCE HAS BEEN ASKED.
    #
    # `ZZZZQ` does not exist and `/api/value` answered **HTTP 200, score 40, recommendation
    # "Reduce"** -- as did `BRK.B`, which does exist and was merely spelled the other way. The
    # 40 is `health: 40.0` standing alone after the valuation was withheld and the weights
    # renormalised, so it is literally one sub-score of a company nobody identified, rendered
    # as a recommendation. **Every honest caveat downstream is about the VALUATION and none of
    # them can say the company was not found:** `partial_note` explains at length that the
    # valuation contributes nothing, and cannot explain that there is no company.
    #
    # **A CORRECTION TO THIS CHANGE'S OWN FIRST CUT, found by driving it rather than reading
    # it.** I set this flag inside the `cd is None` branch above, on the reasonable-looking
    # assumption that a symbol nobody can find produces no object. **It does not.**
    # `yahoo.fetch` RETURNS a `CompanyData` for `ZZZZQ` -- ticker and name populated from the
    # argument, everything else `None` -- so `cd is None` never fired, the flag was never set,
    # and the route went on answering 200 with a full valuation built from
    # `base_revenue: 0.0` and an assumed 10% margin. The branch I put it in cannot be reached
    # by the case it was written for.
    #
    # THE DETECTOR IS THEREFORE THE MEASURED EMPTINESS, and it is a CONJUNCTION on purpose: a
    # price, a revenue AND a share count all absent after Yahoo, EDGAR gap-fill and EDGAR
    # standalone have each been asked. Any ONE of them present means something was found --
    # a real company mid-halt still has revenue and shares, a fresh listing still has a price
    # -- so requiring all three to be missing cannot refuse a company that exists. Yahoo's own
    # answer for this symbol was `Quote not found for symbol: ZZZZQ`.
    #
    # A BOOLEAN RATHER THAN AN INFERENCE AT EACH CALL SITE: "price is None" is a different
    # question, and this is the one place that knows every source was asked.
    if looks_not_found(cd):
        cd.fetch_failed = True

    # Say so when the symbol was rewritten, in the object that carries the decision. A reader
    # who typed `BRK.B` and gets a page headed `BRK-B` is owed the reason.
    if _asked and _asked != ticker:
        cd.quality_notes.append(
            "Symbol normalised from %s to %s: a share class written with a dot is spelled with "
            "a hyphen by the market-data source." % (_asked, ticker))

    # Attach live macro
    rf, rf_note = macro.risk_free_rate(cfg)
    cd.risk_free_rate = rf  # dynamic attribute consumed by WACC
    cd.sources.append(rf_note)

    return cd
