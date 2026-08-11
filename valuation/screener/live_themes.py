"""
Live `institutional` and `insider` inputs, read from a pre-built cache.

WHY THIS EXISTS (FIDELITY-2, 2026-08-11)
----------------------------------------
Both themes reached no live score: `institutional` was null on 500/500 served rows and
`insider` was CONSTANT (`factors.py:284` sets `df["insider"] = 0.0` when `insider_score` is
absent, and a constant column z-scores to all-NaN and is renormalised away).

They ship now because they passed a fidelity gate, having FAILED it once. Rebuilt to the panel's
own definitions and re-scored against the same bar (`PREREG_fidelity2_rebuild.md`, `ef765fc`):

    institutional   rho +0.1706 -> +0.9190   (n 382)
    insider         rho +0.3596 -> +0.8726   (n 328)

against a 0.60 bar. The first attempt failed because the columns were different quantities, not
noisy ones — the panel's `_inst_accum` reads DOLLARS where the first build read shares, and the
panel's insider statistic sums SIGNED dollars unweighted and returns None on an empty window
where the live scraper summed code-weighted roots and returned a neutral 50.

READS A CACHE, MAKES NO NETWORK CALLS. The inputs are quarterly (13F) and daily-incremental
(Form 4); building them inside a scan would put ~5,600 SEC requests on the critical path. The
builder is `scripts/fidelity2_rebuild.py build-live`, and the scan just reads what it wrote.

FAILS TO None, NEVER TO A GUESS. Missing file, stale file, unknown ticker, malformed row — all
return None, which `factors.py` treats as a neutral factor and `composite` renormalises away.
That is exactly the pre-restoration behaviour, so a missing cache costs coverage, never
correctness. STALENESS IS REPORTED, not silently tolerated: `status()` carries the build date so
a cache nobody refreshed is visible rather than quietly ageing.
"""
from __future__ import annotations

import json
import os
from typing import Optional

#: Written by `scripts/fidelity2_rebuild.py build-live`. Overridable so CI can point at the
#: directory the Action persists — the same lesson `issuance.py` learned.
CACHE = os.environ.get("LIVE_THEMES_CACHE") or os.path.join(
    "data", "live_cache", "theme_columns.json")

#: A cache older than this is not used. One quarter plus a margin: 13F periods land quarterly,
#: so a cache that has not been rebuilt in a quarter is describing a period that has rolled.
MAX_AGE_DAYS = 120

FIELDS = ("inst_accum", "sm_breadth", "insider_score")

_cache: Optional[dict] = None
_loaded = False


def _load() -> dict:
    global _cache, _loaded
    if _loaded:
        return _cache or {}
    _loaded = True
    _cache = None
    try:
        with open(CACHE, "r", encoding="utf-8") as fh:
            blob = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(blob, dict) or "rows" not in blob:
        return {}
    _cache = blob
    return blob


def status() -> dict:
    """Build date, row count and whether the cache is usable. For the scan health block."""
    blob = _load()
    if not blob:
        return {"available": False, "reason": f"no readable cache at {CACHE}"}
    import datetime as _dt
    built = blob.get("built")
    age = None
    try:
        age = (_dt.date.today() - _dt.date.fromisoformat(str(built)[:10])).days
    except (TypeError, ValueError):
        pass
    stale = age is None or age > MAX_AGE_DAYS
    return {"available": not stale, "built": built, "age_days": age,
            "rows": len(blob.get("rows") or {}), "max_age_days": MAX_AGE_DAYS,
            "reason": ("stale or undated — not used" if stale else "")}


def columns_for(ticker: str) -> dict:
    """`{inst_accum, sm_breadth, insider_score}` for one ticker; missing keys simply absent."""
    st = status()
    if not st.get("available"):
        return {}
    row = (_load().get("rows") or {}).get((ticker or "").upper())
    if not isinstance(row, dict):
        return {}
    out = {}
    for k in FIELDS:
        v = row.get(k)
        if isinstance(v, (int, float)) and v == v:      # reject NaN
            out[k] = float(v)
    return out


def reset_cache() -> None:
    """Drop the memoised blob. Tests only — the scan reads once per process by design."""
    global _cache, _loaded
    _cache, _loaded = None, False
