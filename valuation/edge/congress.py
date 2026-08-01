"""
Congressional trading disclosures — PRE-SPECIFIED GATE. Committed BEFORE it was run.

Members of Congress and their spouses must disclose securities transactions under the STOCK Act
(2012) via Periodic Transaction Reports. The premise under test is the popular one: that these
trades carry information — from committee work, briefings, or simply being unusually well
connected — that a broad quantitative book does not already have.

Committed results-free so the git history proves the dating, the orientation, the placebo and
the power control were fixed before any number came back.

--------------------------------------------------------------------------------------------
POINT-IN-TIME — THE DISCLOSURE DATE, NEVER THE TRANSACTION DATE. This is the whole ballgame.

Each record carries BOTH dates and they are far apart. The STOCK Act allows up to 45 days
between a trade and its PTR filing, and late filings beyond that are common and only lightly
penalised. The transaction date is when the member traded; the DISCLOSURE date is when anyone
else could possibly have known.

Using `transaction_date` would be the single most effective way to manufacture a spectacular
fake edge in this entire project: it would let the model act on a purchase up to 45+ days before
the information existed publicly, during exactly the window in which the member's own presumed
information advantage plays out. Any backtest of "congressional trades" that reports a large
edge should be assumed to have made this error until proven otherwise.

So `signals_at` filters on `disclosure_date` only, and the loader deliberately DISCARDS the
transaction date entirely rather than carrying it along — it is not stored, so it cannot be used
by mistake later.

--------------------------------------------------------------------------------------------
DATA RELIABILITY — flagged up front, because this is the least trustworthy source tested here.

The source is a free, community-maintained parse of the PTR filings (House/Senate Stock Watcher).
Unlike FINRA, EDGAR and USAspending, which are machine-readable feeds published by the issuing
authority, this data is scraped and OCR'd from PDFs that members file in inconsistent formats.
Known consequences, none of which can be fully corrected here:

  * ticker fields are sometimes blank, malformed, or refer to non-equity assets;
  * amounts are RANGES ("$1,001 - $15,000"), never exact values, so any dollar weighting is an
    approximation by construction — midpoints are used;
  * disclosure dates are as-filed, so a member who files late produces a genuinely late signal.
    That is correct behaviour rather than a bug: the market really did not know until then;
  * coverage begins with the STOCK Act in 2012, so roughly half the panel's history is
    structurally empty, exactly as with FINRA short interest.

Because of the OCR/parsing risk, rows without a clean uppercase ticker are dropped rather than
guessed at.

--------------------------------------------------------------------------------------------
THE SIGNALS — orientation fixed in advance, higher = better.

  congress_net_buy    (buy_dollars - sell_dollars) / (buy_dollars + sell_dollars) over the
                      trailing DISCLOSURE window, using amount-range midpoints. Bounded in
                      [-1, +1], which keeps a single enormous trade from dominating a
                      cross-section built from range midpoints. POSITIVE: net buying by members
                      is the claimed bullish signal.

  congress_activity   log1p(total disclosed transactions) in the same window. THE PLACEBO.
                      Members trade the same popular, liquid, heavily-covered large caps that
                      everyone trades. If raw ACTIVITY predicts as well as NET DIRECTION, then
                      the "signal" is merely identifying well-known stocks — a size and
                      attention characteristic the book already owns through `size` and
                      `momentum` — and it is rejected regardless of its own t-stat. Same
                      construction that made the 13D and USAspending verdicts interpretable.

--------------------------------------------------------------------------------------------
POWER CONTROL — mandatory, and it has already bitten once.

Coverage will be limited to names members actually trade, within 2012+. The USAspending test in
this same session returned a subset so small that `ret_6_1` fell from t +3.40 to +0.83 on it,
making a null result uninterpretable. So the same rule applies here and is committed in advance:
ret_6_1 and inst_accum are re-measured ON THE RESTRICTED SUBSET, and if neither clears
SUBSET_POWER_T there, the outcome is INCONCLUSIVE and may not be reported as a rejection.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, same shape as every other signal here:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT for congress_net_buy, on the rows where it
     exists.
  2. THE PLACEBO MUST STAY DOWN: net_buy must beat activity by >= MIN_NET_OVER_ACTIVITY_T.
  3. THE SUBSET MUST HAVE POWER: a control must clear SUBSET_POWER_T on the restricted subset,
     else INCONCLUSIVE rather than rejected.
  4. Coverage >= MIN_COVERAGE of panel rows.
  5. If 1-4 pass, the standing held-out margins (100bps alpha, 0.25 long-short t) in BOTH
     directions.

Rejecting is the expected outcome, and the prior is worse than for the other sources: this is
the most widely publicised "alternative data" story in retail investing, tracked by several free
public dashboards and at least two ETFs. Whatever edge existed is the most competed-away of
anything tested in this project. A clean null here is a useful thing to be able to say.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# Pre-committed gate.
MIN_IC_TSTAT = 2.0
MIN_NET_OVER_ACTIVITY_T = 1.0
MIN_COVERAGE = 0.02
SUBSET_POWER_T = 2.0

# Construction, fixed in advance.
TRAILING_DAYS = 126                # ~2 quarters of disclosures; matches the book's hold
START_DATE = "2012-01-01"          # STOCK Act; nothing usable earlier

SOURCES = {
    "house": "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com/data/all_transactions.json",
    "senate": "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json",
}
USER_AGENT = "Valquo research donniecorbin6@gmail.com"

_AMT = re.compile(r"\$?([\d,]+)")
_TICKER_OK = re.compile(r"^[A-Z][A-Z.\-]{0,6}$")


def _log(m):
    print(f"[congress] {m}", flush=True)


def amount_midpoint(s) -> float:
    """'$1,001 - $15,000' -> 8000.5. Ranges are all the filings give; midpoint is the honest read."""
    if not s:
        return 0.0
    nums = [float(x.replace(",", "")) for x in _AMT.findall(str(s))]
    if not nums:
        return 0.0
    return (nums[0] + nums[1]) / 2.0 if len(nums) >= 2 else nums[0]


def _is_buy(t) -> Optional[bool]:
    t = (t or "").lower()
    if "purchase" in t:
        return True
    if "sale" in t or "sold" in t:      # includes "sale (partial)" / "sale (full)"
        return False
    return None                          # exchanges, receipts: no directional claim


def fetch_congress_trades(cache_path: Optional[str] = None) -> dict:
    """{ticker: [(disclosure_date, signed_dollars), ...]} ascending.

    The TRANSACTION DATE IS DISCARDED HERE and never stored, so no downstream caller can use it
    by accident. Only the disclosure date survives into the cache.
    """
    import pickle

    import requests

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            got = pickle.load(f)
        _log(f"cache hit: {len(got):,} tickers")
        return got

    out: dict = {}
    kept = dropped = 0
    for src, url in SOURCES.items():
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
        except Exception as e:                                          # noqa: BLE001
            _log(f"{src}: {e}")
            continue
        if r.status_code != 200:
            _log(f"{src}: HTTP {r.status_code}")
            continue
        try:
            rows = json.loads(r.text)
        except json.JSONDecodeError as e:
            _log(f"{src}: bad JSON ({e})")
            continue
        n0 = len(out)
        for row in rows:
            tk = (row.get("ticker") or "").strip().upper()
            # OCR'd PDFs produce junk tickers; drop rather than guess.
            if not tk or tk in ("--", "N/A", "NA") or not _TICKER_OK.match(tk):
                dropped += 1
                continue
            dd = (row.get("disclosure_date") or "")[:10]
            if len(dd) != 10:
                dropped += 1
                continue
            if "/" in dd:                       # some rows use MM/DD/YYYY
                try:
                    mm, dd_, yy = dd.split("/")
                    dd = f"{yy}-{mm.zfill(2)}-{dd_.zfill(2)}"
                except ValueError:
                    dropped += 1
                    continue
            side = _is_buy(row.get("type"))
            if side is None:
                dropped += 1
                continue
            amt = amount_midpoint(row.get("amount"))
            if amt <= 0:
                dropped += 1
                continue
            out.setdefault(tk, []).append((dd, amt if side else -amt))
            kept += 1
        _log(f"{src}: {len(rows):,} rows -> {len(out)-n0:,} new tickers")
    for t in out:
        out[t].sort()
    _log(f"kept {kept:,} transactions, dropped {dropped:,}, {len(out):,} tickers")
    if cache_path and out:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def signals_at(rows, as_of, trailing_days: int = TRAILING_DAYS) -> dict:
    """{congress_net_buy, congress_activity} from disclosures PUBLISHED in the trailing window.

    Filters on the disclosure date, which is the only date this module ever sees.
    """
    import datetime as dt
    import math

    if not rows:
        return {}
    cutoff = str(as_of)[:10]
    try:
        lo = (dt.date.fromisoformat(cutoff) - dt.timedelta(days=trailing_days)).isoformat()
    except ValueError:
        return {}
    buys = sells = 0.0
    n = 0
    for d, amt in rows:
        if d > cutoff:
            break                       # ascending; not yet disclosed
        if d >= lo:
            n += 1
            if amt >= 0:
                buys += amt
            else:
                sells += -amt
    if n == 0:
        return {}
    out = {"congress_activity": float(math.log1p(n))}
    tot = buys + sells
    if tot > 0:
        out["congress_net_buy"] = float((buys - sells) / tot)
    return out
