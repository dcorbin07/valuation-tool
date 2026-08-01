"""
USAspending.gov federal contract awards — PRE-SPECIFIED GATE. Committed BEFORE it was run.

Federal contract obligations are a real, large, publicly-disclosed cash flow that arrives on a
schedule unrelated to earnings season. For a defense or services contractor, a step-change in
awards is genuine news about future revenue. Nothing in the book sees it: the fundamental themes
read financial statements after the fact, and momentum reads price.

Committed results-free so the git history proves the dating, the orientation, the placebo and
the bar were all fixed before any number came back.

--------------------------------------------------------------------------------------------
POINT-IN-TIME — award action date, plus a deliberately generous reporting lag.

Each award has an ACTION DATE (when the obligation was made). That is what the API aggregates
on, and it is what is used here. But the action date is NOT the date the public could see it:
contract actions flow into FPDS with a reporting delay, and historically DoD actions were
withheld from public display for 90 days.

So the quarterly total for a fiscal quarter is treated as available only at
    quarter_end + PUBLICATION_LAG_DAYS
and never before. 60 calendar days is chosen to sit safely past normal FPDS reporting while
staying inside the 90-day worst case. The asymmetry is the same one that governed the FINRA
test: being too conservative costs a little signal strength, being too aggressive produces a
number that is not real.

--------------------------------------------------------------------------------------------
THE SIGNALS — orientation fixed in advance, higher = better.

  govt_award_momentum   trailing-4-quarter obligations / prior-4-quarter obligations - 1.
                        POSITIVE: accelerating federal awards should be good news. Four
                        quarters over four quarters because federal contracting is violently
                        seasonal — obligations spike in the September fiscal year-end "use it or
                        lose it" window, so any shorter window measures the calendar, not the
                        company.

  govt_award_level      log(1 + trailing-4-quarter obligations). This is the PLACEBO, and
                        naming it in advance is the point. The level is a stable characteristic
                        — "this is a defense contractor" — not news. If the LEVEL scores as well
                        as the MOMENTUM, then what is being measured is membership in the
                        defense/government-services sector (with its own beta, valuation and
                        size profile), not the arrival of contract news, and the signal is
                        rejected regardless of its own t-stat. This is the same construction
                        that made the 13D verdict interpretable.

--------------------------------------------------------------------------------------------
COVERAGE IS SMALL BY CONSTRUCTION, AND THAT NEEDS A POWER CONTROL.

Only public companies that are large federal contractors get a value at all — on the order of
100-300 names out of ~2,710, so panel coverage will be a few percent. That is by design (this is
explicitly a signal for government-exposed names), but it has a consequence that must not be
glossed: the cross-section on each date is small, so the IC is measured on far fewer names and
is correspondingly noisy.

Therefore, exactly as in the FINRA test, CONTROL SIGNALS ARE MEASURED ON THE SAME RESTRICTED
SUBSET: ret_6_1 and inst_accum are re-measured using only rows where the award signal exists. If
those known-real signals still show up on the subset, the subset has power and a null result for
awards is a real null. If they collapse too, the test is underpowered and NO verdict can be
claimed — that outcome must be reported as "inconclusive", not as a rejection.

There is also a practical point that survives any statistical result: a signal present on ~5% of
the universe cannot move a broad book much even if it is real. Adoption would mean a
gov-exposure sleeve, not a change to the main composite.

--------------------------------------------------------------------------------------------
RECIPIENT -> TICKER MAPPING and its two acknowledged errors.

USAspending identifies recipients by name and UEI, never by ticker. Mapping is by exact match on
a NORMALIZED company name (strip punctuation and INC/CORP/LLC/HOLDINGS/THE...) against SEC's
`company_tickers.json` titles. Exact-normalized matching is chosen over fuzzy matching because a
false match silently attributes another company's contracts to a stock, which is worse than a
miss.

  1. SUBSIDIARIES ARE MISSED. "ELECTRIC BOAT CORPORATION" ($10.5B over 2015-2016) is General
     Dynamics; "SIKORSKY AIRCRAFT" is Lockheed. Their spend is not credited to the parent. This
     UNDERSTATES gov exposure for conglomerates and adds noise.
  2. THE SEC TITLE LIST IS A TODAY SNAPSHOT, so companies that renamed, merged or delisted map
     imperfectly in the past — the same survivor caveat already recorded for the P10 sector map
     and the P24.2 CIK map.

Both errors add noise or favour survivors. Noise dilutes a real effect toward zero, so they can
push this test toward a false REJECTION but cannot manufacture a false ADOPTION. That is the
safe direction, and it is the reason a rejection here does not need them cleaned up first.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, same shape as every other signal here:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT for govt_award_momentum, measured on the rows
     where it exists.
  2. THE PLACEBO MUST STAY DOWN: momentum must beat level by >= MIN_MOMENTUM_OVER_LEVEL_T in IC
     t-stat, else this is a sector characteristic rather than news.
  3. THE SUBSET MUST HAVE POWER: at least one of the control signals must still clear t >= 2.0
     on the restricted subset. If not, the result is INCONCLUSIVE rather than a rejection.
  4. Coverage >= MIN_COVERAGE of panel rows.
  5. If 1-4 pass, the standing held-out margins (100bps alpha, 0.25 long-short t) in BOTH
     directions.

Rejecting is the expected outcome. Federal contract awards are public, unembargoed, and watched
closely by every defense analyst; and a quarterly-resolution signal on a handful of large,
heavily-covered names is not where undiscovered edge usually lives.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# Pre-committed gate.
MIN_IC_TSTAT = 2.0
MIN_MOMENTUM_OVER_LEVEL_T = 1.0    # momentum must beat the level placebo by this much
MIN_COVERAGE = 0.02                # small by construction; see the coverage note above
SUBSET_POWER_T = 2.0               # a control must clear this on the subset, or: inconclusive

# Construction, fixed in advance.
PUBLICATION_LAG_DAYS = 60          # quarter_end + this before the total is usable
TRAILING_QUARTERS = 4              # federal awards are violently seasonal; 4q vs prior 4q
AWARD_TYPES = ["A", "B", "C", "D"]  # definitive contracts + purchase orders, not IDV ceilings
START_FY = 2008                    # the API rejects anything earlier (422)

API = "https://api.usaspending.gov/api/v2"
USER_AGENT = "Valquo research donniecorbin6@gmail.com"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
REQ_PAUSE = 0.2

_SUFFIX = (r"\b(INC|CORP|CORPORATION|COMPANY|CO|LLC|L L C|LP|L P|LTD|PLC|HOLDINGS|HOLDING"
           r"|GROUP|THE|INCORPORATED|SA|NV|AG|COMPANIES|ENTERPRISES|INTERNATIONAL)\b")


def _log(m):
    print(f"[usaspend] {m}", flush=True)


def normalize_name(n: str) -> str:
    """Uppercase, strip punctuation and corporate suffixes. Exact match on this, never fuzzy."""
    n = re.sub(r"[^A-Z0-9 ]", " ", (n or "").upper())
    n = re.sub(_SUFFIX, " ", n)
    return re.sub(r"\s+", " ", n).strip()


def sec_name_to_ticker(cache_path: Optional[str] = None) -> dict:
    """{normalized_company_name: TICKER} from SEC. TODAY snapshot — see caveat above."""
    import requests

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    r = requests.get(SEC_TICKERS, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    out = {}
    for v in r.json().values():
        k = normalize_name(v.get("title"))
        if k:
            out.setdefault(k, (v.get("ticker") or "").upper())
    _log(f"sec names: {len(out):,}")
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(out, f)
    return out


def top_recipients(pages: int = 20, limit: int = 100,
                   start: str = "2008-10-01", end: str = "2026-06-30") -> list:
    """[(recipient_name, total_obligations)] — the biggest federal contractors, descending."""
    import requests

    hdrs = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    out = []
    for page in range(1, pages + 1):
        body = {"filters": {"time_period": [{"start_date": start, "end_date": end}],
                            "award_type_codes": AWARD_TYPES},
                "limit": limit, "page": page}
        r = requests.post(f"{API}/search/spending_by_category/recipient/",
                          headers=hdrs, data=json.dumps(body), timeout=180)
        if r.status_code != 200:
            _log(f"page {page}: HTTP {r.status_code} — stopping")
            break
        res = r.json().get("results", [])
        if not res:
            break
        out.extend((x.get("name") or "", float(x.get("amount") or 0.0)) for x in res)
        time.sleep(REQ_PAUSE)
    _log(f"top recipients: {len(out):,}")
    return out


def _quarter_end(fy: int, q: int) -> str:
    """Federal fiscal quarters: FY starts Oct 1 of the PRIOR calendar year."""
    import datetime as dt

    # FY Q1 ends Dec 31 (of fy-1), Q2 Mar 31, Q3 Jun 30, Q4 Sep 30.
    return {1: dt.date(fy - 1, 12, 31), 2: dt.date(fy, 3, 31),
            3: dt.date(fy, 6, 30), 4: dt.date(fy, 9, 30)}[q].isoformat()


def fetch_awards(names_to_tickers: dict, cache_path: Optional[str] = None,
                 start: str = "2008-10-01", end: str = "2026-06-30") -> dict:
    """{ticker: [(available_date, quarter_obligations), ...]} ascending.

    `available_date` is the fiscal quarter end plus PUBLICATION_LAG_DAYS. The raw quarter end is
    deliberately not returned, so a caller cannot use the un-lagged figure.
    """
    import datetime as dt
    import pickle

    import requests

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            got = pickle.load(f)
        _log(f"cache hit: {len(got):,} tickers")
        return got

    hdrs = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    out: dict = {}
    t0 = time.time()
    for i, (name, tk) in enumerate(names_to_tickers.items(), 1):
        body = {"group": "quarter",
                "filters": {"recipient_search_text": [name],
                            "time_period": [{"start_date": start, "end_date": end}],
                            "award_type_codes": AWARD_TYPES},
                "subawards": False}
        try:
            r = requests.post(f"{API}/search/spending_over_time/", headers=hdrs,
                              data=json.dumps(body), timeout=180)
        except Exception as e:                                          # noqa: BLE001
            _log(f"{name}: {e}")
            continue
        time.sleep(REQ_PAUSE)
        if r.status_code != 200:
            continue
        series = []
        for row in r.json().get("results", []):
            tp = row.get("time_period") or {}
            try:
                fy, q = int(tp.get("fiscal_year")), int(tp.get("quarter"))
            except (TypeError, ValueError):
                continue
            amt = float(row.get("aggregated_amount") or 0.0)
            avail = (dt.date.fromisoformat(_quarter_end(fy, q))
                     + dt.timedelta(days=PUBLICATION_LAG_DAYS)).isoformat()
            series.append((avail, amt))
        if series:
            series.sort()
            prev = out.get(tk)
            # Two recipient names can map to one ticker; sum them into a single series.
            if prev:
                merged = {}
                for d, a in prev + series:
                    merged[d] = merged.get(d, 0.0) + a
                out[tk] = sorted(merged.items())
            else:
                out[tk] = series
        if i % 25 == 0:
            _log(f"{i}/{len(names_to_tickers)} recipients, {len(out)} tickers, "
                 f"{time.time()-t0:.0f}s")
    _log(f"done: {len(out):,} tickers in {time.time()-t0:.0f}s")
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def signals_at(series, as_of, trailing: int = TRAILING_QUARTERS) -> dict:
    """{govt_award_momentum, govt_award_level} from quarters PUBLISHED by `as_of`.

    Needs 2*trailing published quarters to compare a trailing window against the prior one; with
    fewer, returns {} rather than a half-formed number.
    """
    import math

    if not series:
        return {}
    cutoff = str(as_of)[:10]
    usable = [a for d, a in series if d <= cutoff]
    if len(usable) < 2 * trailing:
        return {}
    recent = sum(usable[-trailing:])
    prior = sum(usable[-2 * trailing:-trailing])
    out = {"govt_award_level": float(math.log1p(max(recent, 0.0)))}
    if prior > 0:
        out["govt_award_momentum"] = float(recent / prior - 1.0)
    return out
