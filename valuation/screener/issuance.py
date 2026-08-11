"""
Live net share issuance — the input that restores `capital_discipline` to the live composite.

WHY THIS EXISTS (theme restoration, 2026-08-11)
----------------------------------------------
The live book scored **4 of 7** weighted themes. `capital_discipline` was null on 500/500 served
rows, not because the theme was unwired but because its one input was never supplied:
`providers.py` carried `"share_issuance": None` with the comment *"needs share history"*, and
`factors.py:161` has read `share_issuance` all along. The hook was there; the data was not.

This module supplies it, from **free public SEC XBRL company facts** — the same source the V2G
measured-only column used, and the same quantity `fundamental_panel.py:699` computes for the
backtest (`shares_now / shares_prior - 1`, low or negative = disciplined).

IT SHIPS BECAUSE IT PASSED A FIDELITY GATE, NOT BECAUSE IT WAS AVAILABLE.
`PREREG_theme_restoration.md` (committed alone at `1d12822`) required each candidate theme to
rank names the way the panel's own theme does, against a bar calibrated on the panel itself.
Measured on the panel's 2026-01-28 cross-section, **`capital_discipline` scored Spearman +0.8421
over 416 overlapping names** against a bar of 0.60. The other two candidates FAILED and are NOT
wired: `institutional` +0.1706 and `insider` +0.3596. Restoring those would have put a different
theme under a validated theme's name, which is the B7 disease.

DELIBERATELY REUSES `valuation/data/edgar.py` rather than reimplementing. That module already
resolves CIKs and walks annual XBRL series, and a second copy of that logic in the same package
is how two sources of one number drift apart.

FAILS TO None, NEVER TO A GUESS. Every failure path — no CIK, no facts, one data point, a network
error — returns `None`, which `factors.py` treats as a neutral factor and `composite` renormalises
away. That is exactly the pre-restoration behaviour, so a bad day for SEC's endpoint costs
coverage, never correctness.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional

# EXACTLY the concept list the V2G column used, passed in ONE call, because the fidelity gate
# was measured on THAT column and a different selection would not inherit its +0.8421.
#
# This was not free. The first cut listed four concepts and looped them one at a time, which
# tries concept 1 across every namespace before concept 2 — where passing the list in a single
# call tries both concepts WITHIN a namespace first. Different winner, different number: PEP came
# out -0.003537 against the measured column's -0.003628. Close enough to look right in a
# spot-check and not the quantity the gate cleared. `test_issuance_reproduces_the_measured
# _column` pins the agreement over the whole cached universe.
_SHARE_CONCEPTS = ["EntityCommonStockSharesOutstanding",
                   "WeightedAverageNumberOfDilutedSharesOutstanding"]

#: Share counts change quarterly at most, and a scan runs daily. A long TTL keeps the daily scan
#: to a trickle of SEC calls; the cache is per ticker so a miss costs one request, not a sweep.
CACHE_TTL_S = 30 * 24 * 3600

#: Overridable so CI can point it at the directory the Action actually persists. `auto-scan.yml`
#: caches `.scan-cache` between runs and NOT `data/`, so without this every scheduled scan would
#: refetch the whole universe from SEC — ~800 requests a day to learn share counts that change
#: quarterly. Default stays under `data/` for local runs, which is gitignored either way.
_CACHE_DIR = os.environ.get("ISSUANCE_CACHE_DIR") or os.path.join("data", "live_cache", "issuance")

_mem: dict = {}


def available(cfg=None) -> bool:
    """True when this source can be used at all. It needs no key — only a User-Agent."""
    return True


def _cache_path(ticker: str) -> str:
    return os.path.join(_CACHE_DIR, f"{ticker.upper()}.json")


def _read_cache(ticker: str):
    if ticker in _mem:
        return _mem[ticker]
    p = _cache_path(ticker)
    try:
        st = os.stat(p)
    except OSError:
        return None
    if time.time() - st.st_mtime > CACHE_TTL_S:
        return None
    try:
        with open(p, "r", encoding="utf-8") as fh:
            row = json.load(fh)
    except (OSError, ValueError):
        return None
    _mem[ticker] = row
    return row


def _write_cache(ticker: str, row: dict) -> None:
    _mem[ticker] = row
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        tmp = _cache_path(ticker) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(row, fh)
        os.replace(tmp, _cache_path(ticker))
    except OSError:
        pass          # a cache that cannot be written is a slow source, not a broken one


def _annual_shares(facts: dict):
    """Recent-first [(end, shares)]. ONE call with the whole list — see `_SHARE_CONCEPTS`.

    The length check belongs to the CALLER, not here: taking the first series that resolves and
    then testing it is what the measured column does, and rejecting a one-point series here
    would fall through to a different concept and pick a different number.
    """
    from ..data.edgar import _annual_series
    return _annual_series(facts, _SHARE_CONCEPTS, "shares")


def share_issuance(ticker: str, cfg) -> Optional[float]:
    """YoY net share issuance, or None.

    Positive = shares issued (dilution). Negative = buyback. `factors.py` negates it, so
    disciplined names score high — the same orientation as the panel.
    """
    ticker = (ticker or "").upper()
    if not ticker:
        return None
    cached = _read_cache(ticker)
    if cached is not None:
        return cached.get("share_issuance")

    row = {"share_issuance": None, "points": 0, "end": None}
    try:
        from ..data import edgar
        cik = edgar.resolve_cik(ticker, cfg)
        if cik is None:
            # A terminal answer for this ticker (foreign issuers with no CIK), so it is cached:
            # re-asking every scan would spend a request to learn the same thing.
            _write_cache(ticker, row)
            return None
        # `requests`, not `urllib`, and not by preference: `edgar._headers` sends
        # `Accept-Encoding: gzip, deflate` and SEC honours it, so a raw urllib read returns
        # gzip bytes and dies on `.decode()`. `requests` decompresses transparently, which is
        # why every other caller in `edgar.py` uses it. Caught by a canary that returned None
        # for all four test names before this line changed.
        import requests
        r = requests.get(edgar._FACTS_URL.format(cik=cik),
                         headers=edgar._headers(cfg), timeout=30)
        r.raise_for_status()
        facts = r.json()
        series = _annual_shares(facts)
        row["points"] = len(series)
        if len(series) >= 2 and series[1][1]:
            row["share_issuance"] = series[0][1] / series[1][1] - 1.0
            row["end"] = series[0][0]
        _write_cache(ticker, row)
        return row["share_issuance"]
    except Exception:                                            # noqa: BLE001
        # NOT cached: a transient failure must be retried next scan rather than banked as
        # "this name has no issuance", which would quietly shrink coverage for a month.
        return None
