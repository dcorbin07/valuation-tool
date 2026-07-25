"""
Intraday scan — score every name in the liquid universe for buy setups and rank.

Runs on demand (a refresh) or on a schedule during market hours. Saves a
timestamped snapshot so the dashboard shows the latest instantly and can poll for
updates. Options data is optional (skipped per-name if unavailable) so a missing
chain never blocks the technical read.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional, Callable

from ..config import CONFIG
from ..screener.store import Store
from .providers import get_provider
from .signals import evaluate


def run_intraday(cfg=CONFIG, store: Optional[Store] = None, provider=None,
                 universe=None, with_options=True, limit=None,
                 progress: Optional[Callable] = None, save=True) -> dict:
    store = store or Store()
    provider = provider or get_provider(cfg)
    uni = universe or provider.get_universe()
    if limit:
        uni = uni[:limit]

    rows = []
    for i, t in enumerate(uni):
        bars = provider.get_bars(t)
        if not bars:
            continue
        opt = provider.get_option_summary(t) if with_options else None
        ev = evaluate(bars, opt)
        if ev.get("score") is None:
            continue
        rows.append({
            "ticker": t, "score": ev["score"], "labels": ev["labels"], "summary": ev["summary"],
            "price": (ev.get("detail") or {}).get("price"),
            "technical_score": ev.get("technical_score"), "options_score": ev.get("options_score"),
            "detail": ev.get("detail", {}),
        })
        if progress and i % 20 == 0:
            progress(i, len(uni))

    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    run_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    if save:
        store.save_intraday(run_time, rows, provider.name)
    return {"run_time": run_time, "rows": rows, "universe": len(uni),
            "scored": len(rows), "provider": provider.name}
