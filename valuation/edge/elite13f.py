"""
Elite-manager 13F conviction — PRE-SPECIFIED GATE. Committed BEFORE it was run.

`sm_breadth` (growth in the NUMBER of managers holding) is already in the institutional theme,
and P4 found the plain conviction measures worthless: `sm_conviction` scored t +1.25 and
`sm_avg_position` t +1.26. The hypothesis here is that those failed because they treat every
manager as equally informative. Weighting by WHO is buying — a concentrated position from a
manager with a good track record, rather than an index fund's mechanical stake — is the version
worth testing.

Committed results-free so the git history proves the gate was fixed before any number came back.

--------------------------------------------------------------------------------------------
CONSTRUCTION — two bounded streaming passes over the 2.9GB SF3 file.

bulk.prepare_sf3 aggregates the per-manager detail away to keep memory bounded, so manager
quality needs its own passes. Both are bounded by (manager, quarter) or (ticker, quarter) keys —
roughly 660k and 700k entries — never by the 79M rows.

  PASS 1 — manager quality.
      For each (manager, quarter): the value-weighted forward return of everything they held.
          quality_raw[m, q] = sum_t(value * fwd_ret[t, q]) / sum_t(value)
      A manager's SKILL at time T is then the mean of their quality_raw over quarters STRICTLY
      BEFORE T (expanding, minimum MIN_QUARTERS). Using a manager's whole-sample record would
      be look-ahead of the worst kind: "funds that did well over 2008-2026 bought this in 2009"
      is not a signal, it is the answer key.

  PASS 2 — elite conviction per (ticker, quarter).
          elite_conviction[t, q] = sum_m (value[m,t,q] / AUM[m,q]) * skill[m, as of q]
      i.e. the existing AUM-relative conviction, but each manager's contribution scaled by the
      track record they had AT THAT TIME. Managers without enough history contribute 0 rather
      than an assumed-average score — an unknown manager is unknown, not average.

  Both signals are then lagged the standard 45 days like every other 13F input, so a quarter's
  filings are only used once they are public.

--------------------------------------------------------------------------------------------
ADOPTION BAR — pre-committed, identical in spirit to every other signal here:

  1. Standalone median IC t-stat >= MIN_IC_TSTAT on the full universe.
  2. Adding it must clear the STANDING margins (100bps alpha, 0.25 long-short t) in BOTH
     held-out directions via holdout_compare_panels.
  3. Coverage >= MIN_COVERAGE of panel rows. 13F data does not exist before 2013-06-30, so the
     ceiling here is ~61% — the bar is set against what is achievable, not against 100%.
  4. It must beat the PLAIN conviction measures it is meant to improve on (sm_conviction t
     +1.25, sm_avg_position t +1.26). Matching them proves the weighting added nothing.

Rejecting is the expected outcome. 13F is quarterly, 45 days stale by rule and ~111 days stale
in practice, and the aggregate signal already in the book (sm_breadth) is the one that survived
testing. The specific claim under test is narrow: that manager IDENTITY carries information the
crowd average does not.
"""
from __future__ import annotations

import csv
import os
import time
from typing import Optional

import numpy as np

# Pre-committed gate.
MIN_IC_TSTAT = 2.0
MIN_COVERAGE = 0.30
BEAT_PLAIN_CONVICTION_T = 1.26     # sm_avg_position, the better of the two P4 rejects

# Construction, fixed in advance.
MIN_QUARTERS = 4                   # a manager needs this much history before they count at all
SECURITY_TYPE = "SHR"              # common shares only, as in prepare_sf3


def _log(m):
    print(f"[elite13f] {m}", flush=True)


def manager_quality(csv_path: str, fwd_by_ticker_quarter: dict,
                    security_type: str = SECURITY_TYPE) -> dict:
    """PASS 1 — {(manager, quarter): value-weighted forward return of their book}.

    `fwd_by_ticker_quarter` maps (ticker, quarter) -> the stock's realized return over the
    quarter FOLLOWING that 13F date. Bounded by manager-quarters, not rows.
    """
    if not os.path.exists(csv_path):
        return {}
    num, den = {}, {}
    t0 = time.time()
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if not h:
            return {}
        iT, iM, iS, iD, iV = (h.index("ticker"), h.index("investorname"),
                              h.index("securitytype"), h.index("calendardate"), h.index("value"))
        for n, row in enumerate(r, 1):
            if row[iS] != security_type:
                continue
            try:
                v = float(row[iV])
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            fr = fwd_by_ticker_quarter.get((row[iT], row[iD]))
            if fr is None:
                continue
            k = (row[iM], row[iD])
            num[k] = num.get(k, 0.0) + v * fr
            den[k] = den.get(k, 0.0) + v
            if n % 20_000_000 == 0:
                _log(f"pass1 {n/1e6:.0f}M rows, {time.time()-t0:.0f}s")
    out = {k: num[k] / den[k] for k in num if den.get(k, 0) > 0}
    _log(f"pass1: {len(out):,} manager-quarters in {time.time()-t0:.0f}s")
    return out


def skill_as_of(quality: dict, min_quarters: int = MIN_QUARTERS) -> dict:
    """{(manager, quarter): skill known BEFORE that quarter} — expanding mean, never itself.

    This is the whole point of the design. A manager's score at quarter q uses only quarters
    strictly earlier than q, so the signal can never encode how they did afterwards.
    """
    by_mgr = {}
    for (m, q), v in quality.items():
        by_mgr.setdefault(m, []).append((q, v))
    out = {}
    for m, rows in by_mgr.items():
        rows.sort()
        run, n = 0.0, 0
        for q, v in rows:
            if n >= min_quarters:
                out[(m, q)] = run / n          # decided BEFORE adding this quarter
            run += v
            n += 1
    return out


def elite_conviction(csv_path: str, skill: dict, aum: dict,
                     security_type: str = SECURITY_TYPE) -> dict:
    """PASS 2 — {ticker: {quarter: elite_conviction}}.

    Each manager's AUM-relative position scaled by the track record they had AT THAT TIME.
    A manager with too little history contributes 0 — unknown is unknown, not average.
    """
    if not os.path.exists(csv_path):
        return {}
    out, t0 = {}, time.time()
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if not h:
            return {}
        iT, iM, iS, iD, iV = (h.index("ticker"), h.index("investorname"),
                              h.index("securitytype"), h.index("calendardate"), h.index("value"))
        for n, row in enumerate(r, 1):
            if row[iS] != security_type:
                continue
            try:
                v = float(row[iV])
            except (TypeError, ValueError):
                continue
            if v <= 0:
                continue
            q = row[iD]
            sk = skill.get((row[iM], q))
            if sk is None:
                continue
            book = aum.get((row[iM], q))
            if not book or book <= 0:
                continue
            out.setdefault(row[iT], {}).setdefault(q, 0.0)
            out[row[iT]][q] += (v / book) * sk
            if n % 20_000_000 == 0:
                _log(f"pass2 {n/1e6:.0f}M rows, {time.time()-t0:.0f}s")
    _log(f"pass2: {len(out):,} tickers in {time.time()-t0:.0f}s")
    return out


def manager_aum(csv_path: str, security_type: str = SECURITY_TYPE) -> dict:
    """{(manager, quarter): total book value} — same quantity prepare_sf3 computes in pass A."""
    if not os.path.exists(csv_path):
        return {}
    aum = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.reader(f)
        h = next(r, None)
        if not h:
            return {}
        iM, iS, iD, iV = (h.index("investorname"), h.index("securitytype"),
                          h.index("calendardate"), h.index("value"))
        for row in r:
            if row[iS] != security_type:
                continue
            try:
                v = float(row[iV])
            except (TypeError, ValueError):
                continue
            if v > 0:
                k = (row[iM], row[iD])
                aum[k] = aum.get(k, 0.0) + v
    return aum
