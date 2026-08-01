"""
FINRA short interest — PRE-SPECIFIED GATE. Committed BEFORE it was run.

Genuinely orthogonal to everything in the book: value, quality, momentum, size and 13F all
describe what a company IS or what its price DID. Short interest describes what informed
sceptics are betting against it. Free public data, no key.

Committed results-free so the git history proves the rule, the lag, the signal ORIENTATION and
the gate were all fixed before any number came back.

--------------------------------------------------------------------------------------------
POINT-IN-TIME — the trap this data sets, and how it is handled.

FINRA's API exposes `settlementDate` and NOTHING ELSE date-like. There is no dissemination
field. Short interest as of a settlement date is NOT public on that date: under FINRA Rule
4560 firms report within 2 business days and FINRA disseminates on roughly the 8th business
day after settlement. Using `settlementDate` as the as-of would therefore inject about two
weeks of look-ahead into every observation — the single most likely way to manufacture a fake
edge here.

So every observation is stamped with `settlementDate + PUBLICATION_LAG_DAYS` and used only from
that date onward. 15 CALENDAR days is deliberately generous against the ~8 BUSINESS day
schedule (~12 calendar days), because the cost of being a few days too conservative is a
slightly weaker signal, while the cost of being a day too aggressive is a result that is not
real.

--------------------------------------------------------------------------------------------
THE SIGNALS — orientation fixed in advance, higher = better, as the whole factor engine expects.

  neg_days_to_cover      -daysToCoverQuantity. Days-to-cover is short position / average daily
                         volume: how long the shorts would need to buy back. The documented
                         finding is that heavily-shorted stocks UNDERPERFORM — short sellers
                         are informed on average — so the signal is NEGATED: less shorted is
                         better. Stating the sign here, before running, matters: "it worked
                         with the other sign" is how a coin flip becomes a discovery.

  neg_short_interest_chg -(current - previous) / previous. RISING short interest is the bearish
                         event; the level is partly a stable stock characteristic (borrow cost,
                         index membership, convertible arb) while the CHANGE is closer to news.
                         Negated for the same reason.

--------------------------------------------------------------------------------------------
DATA WINDOW — a real limitation, stated up front rather than discovered later.

FINRA's API carries nothing before 2018 (2017 returns a partial 15,495 rows). The panel runs
1998-2026, so this signal can only be measured on roughly the last 34 of 110 rebalance dates.
Consequences, both of which are reported rather than worked around:
  * coverage against the FULL panel will be ~30%, and that is a data-availability ceiling, not
    a plumbing failure;
  * the held-out split has ~17 dates per half, which is LOW POWER. A split that "passes" on 17
    dates is weak evidence, and a split that fails is not proof of absence. The verdict is
    reported with that caveat attached.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, same shape as every other signal here:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT, measured ON THE DATES WHERE THE DATA EXISTS
     (2018+). Measuring it against 110 dates where 76 are structurally empty would understate
     it for a reason that has nothing to do with the signal.
  2. Adding it must clear the STANDING margins (100bps alpha, 0.25 long-short t) in BOTH
     held-out directions of that window.
  3. Coverage >= MIN_COVERAGE **within the 2018+ window**. Against the full panel the ceiling
     is ~30% and that number is reported separately.

Rejecting is the expected outcome, and the honest prior is worse than usual: short interest is
one of the most widely watched free datasets in the market, so any edge is heavily competed.
"""
from __future__ import annotations

import io
import json
import os
import time
from typing import Optional

# Pre-committed: point-in-time lag and gate.
PUBLICATION_LAG_DAYS = 15          # calendar days after settlement before the data is usable
MIN_IC_TSTAT = 2.0
MIN_COVERAGE = 0.50                # within the 2018+ window, where the data actually exists

API = "https://api.finra.org/data/group/otcMarket/name/consolidatedShortInterest"
# FINRA asks for an identifying User-Agent. Don's address, per his instruction for EDGAR too.
USER_AGENT = "Valquo research donniecorbin6@gmail.com"
START_DATE = "2018-01-01"          # nothing usable before this; see DATA WINDOW above


def _log(m):
    print(f"[shortint] {m}", flush=True)


def fetch_short_interest(start: str = START_DATE, end: Optional[str] = None,
                         cache_path: Optional[str] = None, page: int = 5000,
                         max_rows: int = 4_000_000) -> dict:
    """{ticker: [(available_date, days_to_cover, short_qty, prev_short_qty), ...]} ascending.

    `available_date` is settlementDate + PUBLICATION_LAG_DAYS — the earliest date the figure
    could actually have been acted on. The raw settlement date is deliberately NOT returned, so
    a caller cannot accidentally use it.
    """
    import csv
    import datetime as dt
    import requests

    if cache_path and os.path.exists(cache_path):
        import pickle
        with open(cache_path, "rb") as f:
            got = pickle.load(f)
        _log(f"cache hit: {len(got):,} tickers")
        return got

    end = end or dt.date.today().isoformat()
    hdrs = {"User-Agent": USER_AGENT, "Content-Type": "application/json"}
    out: dict = {}
    offset, t0, seen = 0, time.time(), 0
    while seen < max_rows:
        payload = {
            "limit": page, "offset": offset,
            "compareFilters": [
                {"fieldName": "settlementDate", "fieldValue": start, "compareType": "GTE"},
                {"fieldName": "settlementDate", "fieldValue": end, "compareType": "LTE"}],
        }
        r = requests.post(API, headers=hdrs, data=json.dumps(payload), timeout=90)
        if r.status_code != 200:
            _log(f"HTTP {r.status_code} at offset {offset} — stopping")
            break
        rows = list(csv.DictReader(io.StringIO(r.text)))
        if not rows:
            break
        for row in rows:
            t = (row.get("symbolCode") or "").strip().upper()
            sd = (row.get("settlementDate") or "")[:10]
            if not t or not sd:
                continue
            try:
                avail = (dt.date.fromisoformat(sd)
                         + dt.timedelta(days=PUBLICATION_LAG_DAYS)).isoformat()
            except ValueError:
                continue

            def _f(k):
                try:
                    return float(row.get(k) or "")
                except (TypeError, ValueError):
                    return None

            out.setdefault(t, []).append((avail, _f("daysToCoverQuantity"),
                                          _f("currentShortPositionQuantity"),
                                          _f("previousShortPositionQuantity")))
        seen += len(rows)
        offset += page
        if offset % 100000 == 0:
            _log(f"{seen:,} rows, {len(out):,} tickers, {time.time()-t0:.0f}s")
        if len(rows) < page:
            break
    for t in out:
        out[t].sort()
    _log(f"done: {seen:,} rows -> {len(out):,} tickers in {time.time()-t0:.0f}s")
    if cache_path:
        import pickle
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def signals_at(rows, as_of) -> dict:
    """{neg_days_to_cover, neg_short_interest_chg} from the latest PUBLISHED observation.

    Only observations whose `available_date` is on or before `as_of` are considered, so the
    publication lag is enforced here and not merely intended.
    """
    if not rows:
        return {}
    cutoff = str(as_of)[:10]
    usable = [r for r in rows if r[0] <= cutoff]
    if not usable:
        return {}
    _, dtc, cur, prev = usable[-1]
    out = {}
    if dtc is not None and dtc == dtc:
        out["neg_days_to_cover"] = -float(dtc)
    if cur is not None and prev not in (None, 0) and prev == prev and prev > 0:
        out["neg_short_interest_chg"] = -float(cur / prev - 1.0)
    return out
