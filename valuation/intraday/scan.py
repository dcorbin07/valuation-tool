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
from .signals import evaluate, evaluate_bearish
from .contracts import contract_idea, HORIZONS


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
        per_h = {h: evaluate(bars, opt, horizon=h) for h in HORIZONS}
        ev = per_h["swing"]
        if ev.get("score") is None:
            continue
        detail = ev.get("detail", {})
        price = detail.get("price")
        iv = detail.get("opt_atm_iv")
        # Per-horizon scores (for the UI toggle to re-rank) + matching contract ideas.
        detail["scores"] = {h: per_h[h].get("score") for h in HORIZONS}
        detail["contracts"] = {h: contract_idea(price, iv, h, "bull") for h in HORIZONS}
        # Bearish (short-side) mirror for the Bull/Bear toggle.
        bear_h = {h: evaluate_bearish(bars, opt, horizon=h) for h in HORIZONS}
        detail["scores_bear"] = {h: bear_h[h].get("score") for h in HORIZONS}
        detail["labels_bear"] = bear_h["swing"].get("labels", [])
        detail["contracts_bear"] = {h: contract_idea(price, iv, h, "bear") for h in HORIZONS}
        rows.append({
            "ticker": t, "score": ev["score"], "labels": ev["labels"], "summary": ev["summary"],
            "price": price,
            "technical_score": ev.get("technical_score"), "options_score": ev.get("options_score"),
            "detail": detail,
        })
        if progress and i % 20 == 0:
            progress(i, len(uni))

    rows.sort(key=lambda r: r["score"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    run_time = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    if save:
        # ITEM 45: RECORD THE FEED THAT SERVED THE RUN, not the class's name. `intraday_runs`
        # already has a `provider` column, and it read "Tradier" on runs Tradier served none
        # of -- so the stored provenance agreed with the broken selection rather than with the
        # data. `source_label` is the same string as `name` for Tradier, so no past row's
        # meaning changes; what changes is that a degraded run says so on disk.
        store.save_intraday(run_time, rows,
                            getattr(provider, "source_label", provider.name))
        # Archive the options/IV context to a dated file. Free (the data is already
        # fetched) and append-only, building the point-in-time options history that a
        # real options-exit backtest needs. Never allowed to break a scan.
        try:
            from ..edge.archive import archive_intraday
            archive_intraday(rows, run_time, provider.name)
        except Exception:
            pass
    # ITEM 45: THE FEED THAT SERVED THIS SCAN IS NAMED IN THE PAYLOAD, not inferred from
    # `provider.name`. When Tradier's token died the scan kept reporting `provider: "Tradier"`
    # while scoring nothing, so the payload named a feed that had served none of it. These
    # three fields say which source ran, how stale it is, and why it was not the first choice;
    # `get_provider` sets them, and a provider built directly carries the defaults.
    return {"run_time": run_time, "rows": rows, "universe": len(uni),
            "scored": len(rows), "provider": provider.name,
            "feed_source": getattr(provider, "source_label", provider.name),
            "feed_delay": getattr(provider, "feed_delay", None),
            "feed_degraded_reason": getattr(provider, "degraded_reason", "") or ""}
