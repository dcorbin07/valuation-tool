"""The Piotroski F-Score on the FREE path, delegating to the panel's own definition.

WHY THIS EXISTS. `D9-DIAG` located the free route's quality gap, and the sharpest part of it is
not a disagreement at all: **the live side does not compute the F-score.** The panel's `quality`
theme averages it with nine other inputs, so a live `quality` built without it is a mean over a
different set of columns — which is one of the reasons `D9`'s B3 read `quality` **0.6256** against
a 0.70 bar while `value`, `momentum` and `size` cleared theirs at 0.79, 0.97 and 0.98.

**IT DELEGATES (B7), AND THE DELEGATION IS THE WHOLE POINT.** The nine tests, the "at least six
must be evaluable" floor and the asset-turnover derivation all live in
`fundamental_panel._f_score`. A second implementation on the live path would be a second
definition of the number the two sides are being compared ON — so a fidelity measurement against
it would be measuring the gap between two of my own functions, not between two vendors. This
module's only job is to put SEC's XBRL facts into the field names that function already reads.

WHY SEC XBRL AND NOT THE BROKER FEED. Seven of the nine tests need a **prior fiscal year** value
(ROA, long-term debt, current ratio, share count, gross margin, asset turnover), and the live
`CompanyData` carries year-over-year history for revenue, EBIT, FCF and net income only. Assets,
operating cash flow, non-current debt, the current ratio and the share count have **no history at
all** on that object, so the F-score is not merely unwired — it is not computable from what the
live fetch returns. SEC's companyfacts is free, keyless, authoritative and already reachable
(`edgar.py` resolves the CIK and holds the headers).

THE FIELD NAMES ARE SHARADAR'S, DELIBERATELY. `_f_score` reads `assets`, `netinc`, `ncfo`,
`debtnc`, `currentratio`, `sharesbas`/`shareswa`, `grossmargin`, `revenue`. Translating INTO that
vocabulary keeps the panel's function untouched; translating the function into a live vocabulary
would mean editing the definition both sides are measured against.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

_LOG = logging.getLogger(__name__)

#: XBRL concept candidates per Sharadar field, most-preferred first. Lists rather than single
#: names because filers legitimately use different concepts for the same line -- the same reason
#: `edgar.py` already carries candidate lists for revenue and debt.
_CONCEPTS = {
    "assets": ["Assets"],
    "netinc": ["NetIncomeLoss", "ProfitLoss"],
    "ncfo": ["NetCashProvidedByUsedInOperatingActivities",
             "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
    "debtnc": ["LongTermDebtNoncurrent", "LongTermDebt"],
    "assetsc": ["AssetsCurrent"],
    "liabilitiesc": ["LiabilitiesCurrent"],
    "shareswa": ["WeightedAverageNumberOfDilutedSharesOutstanding",
                 "WeightedAverageNumberOfSharesOutstandingBasic"],
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                "SalesRevenueNet"],
    "cor": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold"],
}


def _annual_map(facts: dict, names) -> dict:
    """{fiscal_year: value} for the first concept that yields anything.

    `frame`-less and `fy`-keyed: SEC's companyfacts carries one entry per filed period, and the
    annual ones carry `fp == "FY"` with a `form` of 10-K. Taking the LAST such entry per year
    rather than the first is deliberate -- a restated year is filed again, and the restatement is
    the number the issuer stands behind.
    """
    units = ((facts.get("facts") or {}).get("us-gaap") or {})
    for name in names:
        node = units.get(name) or {}
        out = {}
        for rows in (node.get("units") or {}).values():
            for r in rows or []:
                if (r.get("fp") or "") != "FY" or not str(r.get("form", "")).startswith("10-K"):
                    continue
                fy, val = r.get("fy"), r.get("val")
                if fy is None or val is None:
                    continue
                out[int(fy)] = float(val)
        if out:
            return out
    return {}


def _rows_from_facts(facts: dict) -> Tuple[Optional[dict], Optional[dict]]:
    """`(current, prior)` in the panel's field vocabulary, or `(None, None)`.

    DERIVED FIELDS ARE DERIVED HERE, NOT IN `_f_score`. `currentratio` and `grossmargin` are
    Sharadar-computed columns with no XBRL concept of their own, so they are built from their
    own inputs -- and built the SAME way for both years, because test 6 and test 8 compare them
    to each other and a definition that drifted between the two years would fabricate a pass.
    """
    series = {k: _annual_map(facts, v) for k, v in _CONCEPTS.items()}
    years = sorted(series.get("assets", {}))
    if len(years) < 2:
        return None, None
    cur_y, prior_y = years[-1], years[-2]
    if cur_y - prior_y != 1:
        # A GAP IS NOT A YEAR-OVER-YEAR CHANGE. Tests 3, 5, 6, 7, 8 and 9 all read "improved
        # since last year"; comparing 2025 against 2022 answers a different question and the
        # score would look like a real one.
        _LOG.warning("fscore: the two most recent annual rows are %s and %s, not consecutive",
                     prior_y, cur_y)
        return None, None

    def row(y):
        g = {k: series[k].get(y) for k in series}
        rev, cor = g.get("revenue"), g.get("cor")
        if rev and cor is not None and rev != 0:
            g["grossmargin"] = (rev - cor) / rev
        ac, lc = g.get("assetsc"), g.get("liabilitiesc")
        if ac is not None and lc:
            g["currentratio"] = ac / lc
        return {k: v for k, v in g.items() if v is not None}

    return row(cur_y), row(prior_y)


def f_score(ticker: str, cfg) -> Tuple[Optional[int], str]:
    """`(score, source)` -- `(None, reason)` when it cannot be computed. Never a guess.

    A `None` is returned rather than a low score, because `_f_score`'s own floor says the same
    thing one level down: a thin row must not masquerade as a genuinely weak company. On this
    path the difference matters more, since the live feed's coverage is the thing being measured.
    """
    try:
        import requests
        from . import edgar
        cik = edgar.resolve_cik(ticker, cfg)
        if not cik:
            return None, "no CIK"
        r = requests.get(edgar._FACTS_URL.format(cik=cik),
                         headers=edgar._headers(cfg), timeout=25)
        r.raise_for_status()
        cur, prior = _rows_from_facts(r.json() or {})
        if not cur or not prior:
            return None, "no consecutive annual pair in XBRL"
        from ..edge.fundamental_panel import _f_score
        s = _f_score(cur, prior)
        return (s, "sec_xbrl") if s is not None else (None, "fewer than six tests evaluable")
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("fscore: %s failed (%s)", ticker, type(e).__name__)
        return None, "%s" % type(e).__name__
