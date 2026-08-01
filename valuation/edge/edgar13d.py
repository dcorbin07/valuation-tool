"""
SEC EDGAR 13D/13G activist stakes — PRE-SPECIFIED GATE. Committed BEFORE it was run.

When an investor crosses 5% of a company they must disclose it: SC 13D if they intend to
influence the company (activist), SC 13G if they are passive. The academic finding (Brav,
Jiang, Partnoy & Thomas) is a large abnormal return around the 13D filing and continued drift
afterwards. This is the event the 13F theme in the book CANNOT see: 13F is a quarterly snapshot
of positions, filed 45 days late and used ~111 days stale here, whereas a 13D is a discrete,
dated, legally-mandated event filed within 10 days of crossing the threshold.

Committed results-free so the git history proves the rule, the dating, the signal ORIENTATION
and the gate were all fixed before any number came back.

--------------------------------------------------------------------------------------------
POINT-IN-TIME — this one is genuinely clean, which is why it is worth testing.

EDGAR's quarterly form index (`full-index/YYYY/QTRn/form.idx`) carries a `Date Filed` column.
That IS the public disclosure date: the moment a filing is indexed it is on EDGAR and readable
by anyone. There is no gap between "happened" and "public" to model, unlike FINRA short
interest (settlement vs dissemination) or congressional PTRs (transaction vs disclosure).

The event date — the day the investor actually crossed 5% — is deliberately NOT used, and is
not even parsed. It precedes the filing by up to 10 days and using it would be look-ahead. Only
`Date Filed` is read, and `signals_at` filters on it.

--------------------------------------------------------------------------------------------
THE SIGNALS — orientation fixed in advance, higher = better.

  activist_13d   count of SC 13D filings naming this company as subject in the last
                 RECENT_DAYS. POSITIVE: an activist taking a 5%+ stake is the documented
                 bullish event. Not negated.

  passive_13g    the same count for SC 13G. This is a PLACEBO, and stating that in advance is
                 the point of including it. 13G is the passive box — index funds and pension
                 managers crossing 5% mechanically as they track an index. If the activism
                 mechanism is real, 13D should score and 13G should not. If BOTH score about
                 equally, the "signal" is almost certainly a size/liquidity artifact (big,
                 liquid stocks attract more filings of every kind) rather than activism, and it
                 should be rejected even if the t-stat looks good. The FINRA test just showed
                 how much a pre-committed control is worth; this is the same idea aimed at a
                 confound instead of at power.

ABSENCE IS ZERO, NOT MISSING — a deliberate departure from how PEAD was treated. "No activist
filed on this stock" is real information, not an unknown, so a name with no filing scores 0.0
rather than NaN. The consequence, stated up front: nominal coverage will be ~100% while the
NONZERO fraction is small, so the cross-sectional z-score is effectively a rare-event
indicator. MIN_NONZERO below is the honest version of a coverage bar for a signal shaped like
this — a rare event needs enough occurrences to be measurable at all.

--------------------------------------------------------------------------------------------
CIK -> TICKER MAPPING and its caveat, stated before running rather than discovered after.

EDGAR identifies companies by CIK. The mapping to tickers comes from SEC's `company_tickers.json`,
which is a TODAY snapshot — the same look-ahead caveat already recorded for the Sharadar TICKERS
sector map in P10. A company that changed ticker or delisted may map imperfectly in the past.
This biases toward SURVIVORS, which if anything flatters the result, so it cannot manufacture a
rejection — only an adoption would need to be discounted for it.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, the same shape every other signal here has faced:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT for activist_13d, on the full universe.
  2. Adding it must clear the STANDING margins (100bps alpha, 0.25 long-short t) in BOTH
     held-out directions.
  3. At least MIN_NONZERO of panel rows must carry a nonzero value — see above.
  4. THE PLACEBO MUST STAY DOWN. activist_13d must beat passive_13g by at least
     MIN_13D_OVER_13G_T in IC t-stat. If passive index-fund crossings score as well as activist
     stakes, the mechanism claimed here is not what is being measured, and the signal is
     rejected regardless of its own t-stat.

Rejecting is the expected outcome. The 13D announcement effect is well documented but it is a
few-day event around the filing, while this book rebalances every 42-63 days and holds for a
quarter — the drift has to survive at that horizon to be usable here, and the event is rare
enough that it may simply not move a broad book.
"""
from __future__ import annotations

import os
import time
from typing import Optional

# Pre-committed gate.
MIN_IC_TSTAT = 2.0
MIN_NONZERO = 0.01                 # >=1% of rows must carry an event to be measurable
MIN_13D_OVER_13G_T = 1.0           # activist must beat the passive placebo by this much

# Signal construction, fixed in advance.
RECENT_DAYS = 126                  # ~2 quarters; matches the book's hold, not the 3-day event
FORMS_13D = ("SC 13D", "SC 13D/A")
FORMS_13G = ("SC 13G", "SC 13G/A")

# SEC requires a descriptive User-Agent with a contact address; 10 req/sec ceiling.
USER_AGENT = "Valquo research donniecorbin6@gmail.com"
INDEX = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"
TICKER_MAP = "https://www.sec.gov/files/company_tickers.json"
REQ_PAUSE = 0.15                   # deliberately under SEC's 10/sec limit


def _log(m):
    print(f"[edgar13d] {m}", flush=True)


def fetch_cik_ticker_map(cache_path: Optional[str] = None) -> dict:
    """{cik_int: TICKER} from SEC's public mapping. TODAY snapshot — see caveat above."""
    import json
    import requests

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    r = requests.get(TICKER_MAP, headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    out = {}
    for row in r.json().values():
        t = (row.get("ticker") or "").strip().upper()
        if t:
            out[int(row["cik_str"])] = t
    _log(f"cik->ticker: {len(out):,} companies")
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in out.items()}, f)
    return out


def fetch_13d_filings(start_year: int, end_year: int, cik_to_ticker: dict,
                      cache_path: Optional[str] = None) -> dict:
    """{ticker: [(date_filed, form), ...]} ascending, from EDGAR's quarterly form indexes.

    Only `Date Filed` is read. The event date (when the investor crossed 5%) is not parsed at
    all, so it cannot leak in.
    """
    import pickle
    import requests

    if cache_path and os.path.exists(cache_path):
        with open(cache_path, "rb") as f:
            got = pickle.load(f)
        _log(f"cache hit: {len(got):,} tickers")
        return got

    wanted = set(FORMS_13D) | set(FORMS_13G)
    out: dict = {}
    hdrs = {"User-Agent": USER_AGENT}
    t0, n_rows = time.time(), 0
    for year in range(start_year, end_year + 1):
        for qtr in (1, 2, 3, 4):
            url = INDEX.format(year=year, qtr=qtr)
            try:
                r = requests.get(url, headers=hdrs, timeout=90)
            except Exception as e:                                  # noqa: BLE001
                _log(f"{year}Q{qtr} request failed: {e}")
                continue
            time.sleep(REQ_PAUSE)
            if r.status_code != 200:
                continue
            # form.idx is fixed-width: Form Type | Company Name | CIK | Date Filed | File Name
            for line in r.text.splitlines():
                if len(line) < 98 or not line[:12].strip().startswith("SC 13"):
                    continue
                form = line[:12].strip()
                if form not in wanted:
                    continue
                try:
                    cik = int(line[74:86].strip())
                except ValueError:
                    continue
                tk = cik_to_ticker.get(cik)
                if not tk:
                    continue
                filed = line[86:98].strip()
                if len(filed) != 10:
                    continue
                out.setdefault(tk, []).append((filed, form))
                n_rows += 1
        _log(f"{year}: {n_rows:,} filings, {len(out):,} tickers, {time.time()-t0:.0f}s")
    for t in out:
        out[t].sort()
    _log(f"done: {n_rows:,} filings -> {len(out):,} tickers in {time.time()-t0:.0f}s")
    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
    return out


def signals_at(rows, as_of, recent_days: int = RECENT_DAYS) -> dict:
    """{activist_13d, passive_13g} — counts filed in the trailing window, as of `as_of`.

    Filters on the FILING date, which is the public disclosure date. Returns zeros rather than
    {} when a stock has no recent filing: no activist is information, not an unknown.
    """
    import datetime as dt

    cutoff = str(as_of)[:10]
    try:
        lo = (dt.date.fromisoformat(cutoff) - dt.timedelta(days=recent_days)).isoformat()
    except ValueError:
        return {}
    d13, g13 = 0, 0
    for filed, form in (rows or []):
        if filed > cutoff:
            break                      # ascending; nothing further is public yet
        if filed >= lo:
            if form in FORMS_13D:
                d13 += 1
            elif form in FORMS_13G:
                g13 += 1
    return {"activist_13d": float(d13), "passive_13g": float(g13)}
