"""
Company profiles — ticker -> company name / sector / industry, from the LIVE feed.

Why this exists: the tracked book can be built from the point-in-time Sharadar export
(`valquo_index --full-universe`), and that export carries no company name and no sector
column at all. The book that came out of it listed bare tickers and reported
`sector_data_available: false`, so its diversification was invisible to anyone reading it.

Sectors and names are *descriptive* fields, not point-in-time signals, so sourcing them
live is correct here — but it would NOT be correct inside the backtest panel, where
today's classification applied to a 1998 row is look-ahead. Nothing in this module is
wired into the panel; it decorates an already-built book.

Lookup order, cheapest and most trustworthy first:

  1. the store's own live-scan data (snapshot rows, then the fundamentals cache) — this is
     FMP/Yahoo data already fetched and paid for, so it costs nothing to reuse;
  2. the SEC's filer list — one keyless call returns the legal name of every US filer;
  3. the bundled sector map — GICS-ish buckets for the liquid names we ship with;
  4. FMP's profile endpoint for whatever is still missing, hard-capped so a big book can
     never burn the free-tier quota.

Everything found is written back to the store's `universe` table, so a repeat export is free.
"""
from __future__ import annotations

import datetime as _dt
from typing import Iterable, Optional

from ..config import CONFIG
from . import universe as U

# One SEC filer-list fetch per process. It is ~1 MB and changes about as often as companies
# are born, so re-fetching it per export would be pure waste.
_SEC_NAMES: Optional[dict] = None

MAX_API_LOOKUPS = 60          # ceiling on paid per-ticker calls in a single lookup()


def _blank(v) -> bool:
    return not (v or "").strip()


def _sec_names() -> dict:
    """ticker -> registered company name, from the SEC's public filer list. Keyless."""
    global _SEC_NAMES
    if _SEC_NAMES is not None:
        return _SEC_NAMES
    out = {}
    try:
        import requests
        r = requests.get("https://www.sec.gov/files/company_tickers.json",
                         headers={"User-Agent": CONFIG.sec_user_agent}, timeout=25)
        r.raise_for_status()
        for v in r.json().values():
            t = (v.get("ticker") or "").upper()
            if t and v.get("title"):
                out[t] = v["title"]
    except Exception:
        pass                                  # keyless best-effort; the caller degrades cleanly
    _SEC_NAMES = out
    return out


def _from_store(store, tickers: set) -> dict:
    """Names/sectors the live scan already fetched — snapshot rows first, then the cache."""
    found: dict = {}
    if store is None:
        return found
    try:
        for r in store.get_profiles(sorted(tickers)) or []:
            found[r["ticker"]] = {"name": r.get("name") or "", "sector": r.get("sector") or "",
                                  "industry": r.get("industry") or ""}
    except Exception:
        pass
    try:
        for r in store.load_snapshot() or []:
            t = (r.get("ticker") or "").upper()
            if t not in tickers:
                continue
            cur = found.setdefault(t, {"name": "", "sector": "", "industry": ""})
            for k in ("name", "sector"):
                if _blank(cur[k]) and not _blank(r.get(k)):
                    cur[k] = r[k]
    except Exception:
        pass
    for t in list(tickers):
        cur = found.get(t)
        if cur and not _blank(cur["name"]) and not _blank(cur["sector"]):
            continue
        try:
            m = store.get_cached_fundamentals(t) or {}
        except Exception:
            continue
        if not m:
            continue
        cur = found.setdefault(t, {"name": "", "sector": "", "industry": ""})
        for k in ("name", "sector", "industry"):
            if _blank(cur[k]) and not _blank(m.get(k)):
                cur[k] = m[k]
    return found


def _fmp_profile(ticker: str, cfg) -> dict:
    from .providers import FMPProvider
    p = FMPProvider(cfg)
    d = (p._get("profile", symbol=ticker) or [{}])[0]
    return {"name": d.get("companyName") or "", "sector": d.get("sector") or "",
            "industry": d.get("industry") or ""}


def lookup(tickers: Iterable[str], cfg=CONFIG, store=None,
           max_api: int = MAX_API_LOOKUPS) -> dict:
    """Return {TICKER: {"name", "sector", "industry"}} for every ticker we can identify.

    Never raises and never blocks on a dead feed — a ticker we cannot identify is simply
    absent from the result, and the caller leaves its existing (blank) value alone.
    """
    want = {(t or "").upper() for t in tickers if t}
    if not want:
        return {}

    out = _from_store(store, want)
    for t in want:
        out.setdefault(t, {"name": "", "sector": "", "industry": ""})

    missing_name = {t for t in want if _blank(out[t]["name"])}
    if missing_name:
        sec = _sec_names()
        for t in missing_name:
            if sec.get(t):
                out[t]["name"] = sec[t]

    smap = U.bundled_sector_map()
    for t in want:
        if _blank(out[t]["sector"]) and smap.get(t):
            out[t]["sector"] = smap[t]

    # Anything still unidentified goes to the paid feed, newest-first and hard-capped.
    still = sorted(t for t in want if _blank(out[t]["name"]) or _blank(out[t]["sector"]))
    if still and getattr(cfg, "fmp_api_key", ""):
        for t in still[:max(0, int(max_api))]:
            try:
                d = _fmp_profile(t, cfg)
            except Exception:
                continue
            for k in ("name", "sector", "industry"):
                if _blank(out[t][k]) and not _blank(d.get(k)):
                    out[t][k] = d[k]

    resolved = {t: v for t, v in out.items()
                if not _blank(v["name"]) or not _blank(v["sector"])}
    if store is not None and resolved:
        try:
            store.cache_profiles(resolved)
        except Exception:
            pass
    return resolved


def decorate(rows: list, cfg=CONFIG, store=None, max_api: int = MAX_API_LOOKUPS) -> int:
    """Fill blank `name` / `sector` on a list of book rows in place. Returns rows changed."""
    need = [r for r in rows if _blank(r.get("name")) or _blank(r.get("sector"))]
    if not need:
        return 0
    prof = lookup([r.get("ticker") for r in need], cfg=cfg, store=store, max_api=max_api)
    changed = 0
    for r in need:
        p = prof.get((r.get("ticker") or "").upper())
        if not p:
            continue
        before = (r.get("name"), r.get("sector"))
        for k in ("name", "sector"):
            if _blank(r.get(k)) and not _blank(p.get(k)):
                r[k] = p[k]
        if (r.get("name"), r.get("sector")) != before:
            changed += 1
    return changed


def _now() -> str:
    return _dt.datetime.utcnow().isoformat(timespec="seconds")
