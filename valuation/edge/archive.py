"""
Live data archive — build our own point-in-time history, for free.

The one thing we cannot buy cheaply is OUR OWN past. Options history is expensive and
Sharadar doesn't carry IV/skew at all, which is exactly why the options exit rule in
options_exit.py has to approximate sigma from realized vol instead of the implied vol a
trader would actually have seen. Every scan already fetches that data and then throws it
away.

So: every run, write what we already have to a dated file. No new API calls, no new
subscription — just disk. In a year this becomes the point-in-time options dataset that
makes a real options-exit backtest possible, and a survivorship-free record of every pick
the tool ever made.

Layout (all gzipped JSON, one file per run):

    data/archive/intraday/2026-07-29/1345.json.gz     options + IV/skew snapshot
    data/archive/scans/2026-07-29.json.gz             that day's ranked picks

Design notes:
  * Append-only and never read by the live app, so a corrupt or missing file can't
    affect anything a user sees.
  * Failures are swallowed. Archiving is a side benefit; it must never take down a scan.
  * Only the fields worth keeping are stored (per-name IV, put/call, the top strikes),
    not entire raw chains — a full chain per name per run would be gigabytes a month.
"""
from __future__ import annotations

import datetime as _dt
import gzip
import json
import os
from typing import Optional

DEFAULT_ROOT = os.path.join("data", "archive")

# Per-name fields worth keeping from an intraday row. Deliberately narrow: this needs to
# stay small enough to run every 15-30 minutes for years.
_INTRADAY_KEEP = ("ticker", "score", "rank", "price", "technical_score", "options_score")
_DETAIL_KEEP = ("price", "opt_atm_iv", "opt_put_call", "opt_put_oi", "opt_call_oi",
                "opt_put_volume", "opt_call_volume", "opt_iv_skew", "realized_vol")


def _write(path: str, payload: dict) -> Optional[str]:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
        return path
    except Exception:
        return None


def archive_intraday(rows, run_time: str, provider: str = "", root: str = DEFAULT_ROOT) -> Optional[str]:
    """Snapshot the options/IV context of an intraday run to a dated file.

    `run_time` is "YYYY-MM-DD HH:MM"; the file lands under that date with an HHMM name, so
    multiple runs a day each keep their own point-in-time snapshot rather than overwriting.
    """
    if not rows:
        return None
    try:
        date_part, _, time_part = run_time.partition(" ")
        stamp = (time_part or "0000").replace(":", "")[:4] or "0000"
        out = []
        for r in rows:
            rec = {k: r.get(k) for k in _INTRADAY_KEEP if r.get(k) is not None}
            d = r.get("detail") or {}
            det = {k: d.get(k) for k in _DETAIL_KEEP if d.get(k) is not None}
            if det:
                rec["detail"] = det
            # Keep the framed contract ideas: these are what a later options backtest
            # would need to know what we would actually have traded.
            if d.get("contracts"):
                rec["contracts"] = d["contracts"]
            out.append(rec)
        payload = {"kind": "intraday", "run_time": run_time, "provider": provider,
                   "n": len(out), "rows": out}
        return _write(os.path.join(root, "intraday", date_part, f"{stamp}.json.gz"), payload)
    except Exception:
        return None


def archive_scan(rows, scan_date: str, provider: str = "", top: int = 100,
                 root: str = DEFAULT_ROOT) -> Optional[str]:
    """Snapshot a day's ranked picks — a survivorship-free record of what we said, when.

    Only the top `top` names are kept: the tail of a 3,000-name scan is noise for this
    purpose and would bloat the archive.
    """
    if not rows:
        return None
    try:
        out = []
        for r in rows[:top]:
            out.append({"ticker": r.get("ticker"), "rank": r.get("rank"),
                        "hot_score": r.get("hot_score"), "price": r.get("price"),
                        "sector": r.get("sector"), "bucket": r.get("bucket"),
                        "market_cap": r.get("market_cap"),
                        "fair_value": r.get("fair_value"), "upside": r.get("upside"),
                        "factors": ((r.get("extra") or {}).get("factors") or None)})
        payload = {"kind": "scan", "scan_date": scan_date, "provider": provider,
                   "n": len(out), "archived_at": _dt.datetime.now().replace(microsecond=0).isoformat(),
                   "rows": out}
        return _write(os.path.join(root, "scans", f"{scan_date}.json.gz"), payload)
    except Exception:
        return None


def stats(root: str = DEFAULT_ROOT) -> dict:
    """How much history have we accumulated? Cheap enough to surface in the Edge Lab."""
    def walk(sub):
        n, size, days = 0, 0, set()
        base = os.path.join(root, sub)
        for dirpath, _dirs, files in os.walk(base):
            for fn in files:
                if fn.endswith(".json.gz"):
                    n += 1
                    try:
                        size += os.path.getsize(os.path.join(dirpath, fn))
                    except OSError:
                        pass
                    days.add(os.path.basename(dirpath) if sub == "intraday" else fn[:10])
        return {"files": n, "bytes": size, "days": len(days)}
    return {"intraday": walk("intraday"), "scans": walk("scans"), "root": root}
