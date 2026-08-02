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

SOURCE CHANGED AFTER THIS GATE WAS COMMITTED, and the reason is worth recording. The originally
intended source (House/Senate Stock Watcher) is DEFUNCT: its S3 buckets return 403, its website
does not resolve, and the surviving GitHub mirror is Senate-only, stops in 2019, and - decisively
- HAS NO DISCLOSURE DATE FIELD AT ALL. Every one of its 8,350 rows carries `transaction_date`
only, so using it would have forced exactly the look-ahead this module exists to prevent. The
source used instead is kadoa-org/congress-trading-monitor, which carries `filing_date` separately
from `transaction_date` and is built from the official House Clerk and Senate eFD feeds. THE GATE
ITSELF - thresholds, orientation, placebo, power control - is unchanged; only the source moved.

The data is still a parse of PDFs that members file in inconsistent formats, rather than a
machine-readable feed from the issuing authority as FINRA/EDGAR/USAspending are.
Known consequences, none of which can be fully corrected here:

  * ticker fields are sometimes blank, malformed, or refer to non-equity assets;
  * amounts are RANGES ("$1,001 - $15,000"), never exact values, so any dollar weighting is an
    approximation by construction — midpoints are used;
  * disclosure dates are as-filed, so a member who files late produces a genuinely late signal.
    That is correct behaviour rather than a bug: the market really did not know until then;
  * coverage begins in 2014 (the STOCK Act is 2012, but this dataset's filing dates start
    2014-01-03), so roughly half the panel's history is structurally empty, as with FINRA;
  * MEASURED, not assumed: 21.9% of the 47,455 transactions are flagged late, and days from
    trade to filing have a median of 29 but a 90th PERCENTILE OF 210 DAYS and a max of 4,049.
    That is the quantitative case for this entire module: using the transaction date would
    inject up to SEVEN MONTHS of look-ahead for a tenth of the sample. It also means the signal
    is genuinely late - which is correct, because so was the public.

Executive-branch (OGE) filings in the same dataset are EXCLUDED: the premise under test is
congressional trading, so only house_clerk and senate_efd rows are used.

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

================================ RESULT (run after the above was committed) =================
INCONCLUSIVE - NOT a rejection. Reporting it that way is required by the rule committed above,
and the rule is what stops a convenient null being claimed as a finding.

42,912 transactions (8,146 late-filed) across 2,278 tickers, filing dates 2014-01-03 to
2026-07-30. Full universe, 136,478 rows / 110 dates.

    signal                     median IC    IC t   dates   avg names   coverage
    congress_net_buy             +0.0020   +0.97      49         314     11.27%
    congress_activity (PLACEBO)  -0.0040   +0.02      49         314     11.27%
    -- POWER CONTROLS, same restricted subset --
    ret_6_1                      +0.0484   +1.87      49         313
    inst_accum                   +0.0230   +1.80      49         313
    quality                      +0.0105   +1.09      49         309

    gate: standalone t >= 2.0                     FAIL (+0.97)
          net_buy beats activity placebo by >= 1  FAIL, barely (+0.95)
          coverage >= 2%                          PASS (11.27%)
          a control clears t 2.0 on the subset    FAIL (best +1.87) -> INCONCLUSIVE

WHY THIS IS NOT A REJECTION, stated plainly. congress_net_buy shows nothing (t +0.97, and it
would have to more than double to clear the bar). But the restricted subset cannot certify a
null: the best known-real control reaches only +1.87. The verdict the evidence supports is
"this test could not answer the question", and that is what is recorded.

THE LIMIT IS TIME, NOT CROSS-SECTION - which is worth knowing because it says what would fix it.
Coverage is healthy: 1,157 tickers and ~314 names per date, far wider than the USAspending test
that DID reach power. The binding constraint is that the data starts in 2014, giving only 49
rebalance dates, and over that particular decade momentum itself was weak (ret_6_1 is +3.40 over
the full 110 dates but only +1.87 here). No amount of extra tickers fixes that; only more years
would, and they do not exist - the STOCK Act is 2012 and this dataset begins in 2014.

THE POINT-IN-TIME DISCIPLINE WAS THE MOST VALUABLE PART OF THIS EXERCISE, and it is now
quantified rather than asserted. Of 47,455 transactions, 21.9% were filed late; days from trade
to filing have a median of 29 but a 90th percentile of 210 and a maximum of 4,049. Using the
transaction date - as any test built on the obvious field would - injects up to SEVEN MONTHS of
look-ahead for a tenth of the sample, precisely during the window in which a member's presumed
advantage would play out. A published "congressional trades beat the market" result that does
not say which date it used should be assumed to have used the wrong one.

A SECOND FINDING WORTH KEEPING: the originally intended source is defunct AND unusable. The
surviving Stock Watcher mirror carries `transaction_date` and NOTHING ELSE - no disclosure date
at all in any of its 8,350 rows. A test built on the first free dataset that comes to hand would
therefore have had no way to be correct, and no field present to warn anyone.

Both signals stay MEASURED and score in NO theme. Re-testing costs one line in factors.py if a
longer history ever becomes available.
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

REPO = "https://github.com/kadoa-org/congress-trading-monitor.git"
TICKER_SUBDIR = "public/data/ticker"           # one JSON per ticker; clone beats 2,373 GETs
KEEP_SOURCES = ("house_clerk", "senate_efd")   # not oge_executive: that is not Congress
USER_AGENT = "Valquo research donniecorbin6@gmail.com"

_AMT = re.compile(r"\$?([\d,]+)")
_TICKER_OK = re.compile(r"^[A-Z][A-Z.\-]{0,6}$")


def _log(m):
    print(f"[congress] {m}", flush=True)


def amount_midpoint(low=None, high=None, label=None) -> float:
    """Midpoint of a disclosed amount RANGE. Filings never give an exact value, so this is an
    approximation by construction - numeric bounds when present, else parsed from the label."""
    try:
        lo, hi = float(low), float(high)
        if lo > 0 and hi > 0:
            return (lo + hi) / 2.0
    except (TypeError, ValueError):
        pass
    try:
        if low is not None and float(low) > 0:
            return float(low)
    except (TypeError, ValueError):
        pass
    nums = [float(x.replace(",", "")) for x in _AMT.findall(str(label or ""))]
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


def fetch_congress_trades(repo_dir=None, cache_path=None) -> dict:
    """{ticker: [(filing_date, signed_dollars), ...]} ascending.

    THE TRANSACTION DATE IS DISCARDED HERE and never stored, so no downstream caller can reach it
    by accident. Only `filing_date` - the public disclosure date - survives into the cache.

    `repo_dir` is a clone of REPO (2,373 per-ticker files make a shallow clone far cheaper than
    fetching each over HTTP).
    """
    import glob
    import pickle

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            got = pickle.load(f)
        _log(f"cache hit: {len(got):,} tickers")
        return got
    if not repo_dir or not os.path.isdir(repo_dir):
        _log(f"no repo_dir given; clone {REPO} first")
        return {}

    out = {}
    kept = dropped = late = 0
    pattern = os.path.join(repo_dir, TICKER_SUBDIR.replace("/", os.sep), "*.json")
    for fp in glob.glob(pattern):
        try:
            with open(fp, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        rows = doc.get("trades") or doc.get("transactions") or []
        for row in rows:
            if row.get("source_id") not in KEEP_SOURCES:
                dropped += 1
                continue
            tk = (row.get("ticker") or "").strip().upper()
            if not tk or tk in ("--", "N/A", "NA") or not _TICKER_OK.match(tk):
                dropped += 1
                continue
            fd = (row.get("filing_date") or "")[:10]          # NEVER transaction_date
            if len(fd) != 10 or fd[4] != "-":
                dropped += 1
                continue
            side = _is_buy(row.get("transaction_type") or row.get("type"))
            if side is None:
                dropped += 1
                continue
            amt = amount_midpoint(row.get("amount_range_low"), row.get("amount_range_high"),
                                  row.get("amount") or row.get("amount_range_label"))
            if amt <= 0:
                dropped += 1
                continue
            if row.get("is_late"):
                late += 1
            out.setdefault(tk, []).append((fd, amt if side else -amt))
            kept += 1
    for t in out:
        out[t].sort()
    _log(f"kept {kept:,} ({late:,} late-filed), dropped {dropped:,}, {len(out):,} tickers")
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
