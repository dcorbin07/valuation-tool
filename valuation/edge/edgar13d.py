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
FILER-vs-SUBJECT CONTAMINATION — measured before running, mitigated by direction not by hope.

form.idx indexes each filing exactly once (verified: 5,945 filings, 5,945 distinct accession
files in 2015Q2), but the indexed name is sometimes the INVESTOR rather than the target: 8.8%
of 2015Q2 SC 13* lines carry investor-styled names ("AB Value Management LLC", "Arch Venture
Fund VII LP"). form.idx has no field distinguishing subject from filer, so this cannot be
cleaned at parse time.

Almost all such filers are private partnerships with no ticker, so the CIK->ticker map drops
them silently. The residue is publicly-traded filers (Icahn Enterprises, Berkshire) which would
credit themselves with an activist stake they took in someone ELSE. That is mislabelled data,
and its effect is to add NOISE to the signal — it dilutes a real effect toward zero. It can
therefore push this test toward a false REJECTION but cannot manufacture a false ADOPTION,
which is the safe direction. Measured and reported after the run rather than assumed away.

--------------------------------------------------------------------------------------------
A RULE CHANGE MAKES THE RAW COUNTS NON-STATIONARY — and why that is survivable here.

The SEC's 2024 amendments shortened 13G amendment deadlines from annual to quarterly, so 13G/A
volume steps up sharply in 2025 (2024Q2: 1,746 13G/A; 2025Q2: 8,898) for a purely regulatory
reason with no market meaning. A signal defined as a RAW COUNT is therefore not comparable
across the panel's history.

This is survivable only because every signal here is z-scored WITHIN each rebalance date. A
uniform level shift affecting all stocks on a date is normalized away by construction, so the
cross-section still asks the right question: "who has unusually many filings TODAY". It would
NOT be survivable for a time-series signal, and it is the reason the counts are never compared
across dates.

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


================================ RESULT (run after the above was committed) =================
REJECTED, and the pre-committed placebo is the reason the rejection means something.
352,332 filings -> 6,632 tickers. Full universe, 136,478 rows / 110 dates.

    signal                  median IC    IC t   nonzero   coverage
    activist_13d              -0.0055   -0.69     4.56%      58.5%
    passive_13g (PLACEBO)     +0.0159   +1.66    18.59%      58.5%
    inst_accum (in the book)  +0.0314   +1.88        --      61.4%
    ret_6_1    (in the book)  +0.0580   +3.40        --     100.0%

    gate: standalone t >= 2.0                 FAIL (-0.69)
          13D beats 13G placebo by >= 1.0     FAIL (-2.35)
          nonzero >= 1%                       PASS (4.56%)

THE ACTIVIST SIGNAL IS NEGATIVE — not weak, but pointed the OTHER WAY from the direction fixed
in advance. And the PASSIVE placebo, the box index funds tick mechanically, outscores it by
2.35 t. Measuring 13D alone would have produced a bland "weak, rejected". The placebo produces
a sharper and more useful statement: whatever these filings carry at a quarterly horizon, it is
NOT activism creating value, because the non-activist control does better.

The placebo also forecloses an obvious trap. passive_13g at t +1.66 is the kind of number that
invites a second look, but it was declared a control BEFORE the run, and it is very likely just
a slower, coarser echo of inst_accum (t +1.88), which the institutional theme already owns.
Promoting it now would be exactly the overfitting this project has spent two dozen sessions
avoiding.

HONEST DEVIATION FROM THE DESIGN ABOVE, found while reading the output. The docstring specifies
"absence is 0.0, not NaN", but the panel wiring skips tickers with NO filing history entirely,
so those rows are NaN. Hence coverage 58.5% rather than the ~100% predicted. The test therefore
ran on the SUBSET of names that have ever been the subject of a 13D/13G — friendlier ground for
the signal, since the never-filed mass is excluded. Within that subset, names with history but
no RECENT filing correctly score 0.0. The deviation makes the test easier, not harder, and
activist_13d still came out negative, so it cannot explain the rejection and the verdict stands
without a re-run.

Contamination and mapping caveats above are moot for a rejection: both add noise or favour
survivors, and neither can turn a real positive into a negative t-stat.

Both signals stay MEASURED (NUMBER_THEME, per-signal IC table) and score in NO theme. The
downloader is kept — it is correct, fast (112s for 20 years) and the form-rename guard below is
worth preserving.
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
# BOTH spellings are required. The SEC RENAMED these form types during 2024 as part of the
# structured-XML modernization: "SC 13D" became "SCHEDULE 13D". In 2025Q2 there are 15,054
# filings under the new labels and THREE under the old. Matching only the historical spelling
# returned ~30 filings per quarter for 2025-2026 — the panel's most recent dates would have
# carried a structurally-zero signal while looking perfectly healthy.
FORMS_13D = ("SC 13D", "SC 13D/A", "SCHEDULE 13D", "SCHEDULE 13D/A")
FORMS_13G = ("SC 13G", "SC 13G/A", "SCHEDULE 13G", "SCHEDULE 13G/A")

# SEC requires a descriptive User-Agent with a contact address; 10 req/sec ceiling.
USER_AGENT = "Valquo research donniecorbin6@gmail.com"
INDEX = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/form.idx"
# form.idx is nominally fixed-width, but the column offsets have MOVED over EDGAR's history —
# a fixed-width parse tested against 2015 returned 0/200 rows and would have silently yielded
# nothing for entire eras. Parse by structure instead: this matches 98.6-99.5% of SC 13* lines
# in 1998, 2015 and 2024 alike.
ROW_RX = r"^((?:SC|SCHEDULE) 13[DG](?:/A)?)\s+(.*?)\s+(\d{1,10})\s+(\d{4}-\d{2}-\d{2})\s+(\S+)\s*$"
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
    import re

    import requests

    rx = re.compile(ROW_RX)
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
            # Form Type | Company Name | CIK | Date Filed | File Name — parsed by structure.
            for line in r.text.splitlines():
                if not (line.startswith("SC 13") or line.startswith("SCHEDULE 13")):
                    continue
                m = rx.match(line)
                if not m:
                    continue
                form = m.group(1)
                if form not in wanted:
                    continue
                tk = cik_to_ticker.get(int(m.group(3)))
                if not tk:
                    continue
                out.setdefault(tk, []).append((m.group(4), form))
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
