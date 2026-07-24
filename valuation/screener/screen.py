"""
The scan — turn a universe into a ranked list of "hot" buy candidates.

Flow: pull the universe → fetch each name's metrics (cached) → apply liquidity/
hygiene gates → build standardized factors → composite-score within each bucket →
convert to a 1–100 hot score by cross-sectional percentile → rank. Optionally run
the full adaptive DCF on just the top names to attach a fair-value gap to the
winners (cheap, because it's only the top dozen, not the whole market).

Results are saved as a dated snapshot so the web UI reads instantly and we keep a
week-over-week history.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional, Callable

import numpy as np
import pandas as pd

from ..config import CONFIG
from . import settings as S
from .factors import build_frame, passes_gates
from .cross_sectional import composite_score
from .providers import get_provider
from .store import Store


def _composites(df: pd.DataFrame) -> pd.Series:
    comps = pd.Series(index=df.index, dtype=float)
    for bucket, w in [("established", S.WEIGHTS_ESTABLISHED),
                      ("speculative", S.WEIGHTS_SPECULATIVE)]:
        sub = df[df["bucket"] == bucket]
        if len(sub) >= 5:
            comps.loc[sub.index] = composite_score(sub, w)
        elif len(sub) > 0:
            comps.loc[sub.index] = composite_score(df, w).loc[sub.index]
    return comps


def _rows_from(scored: pd.DataFrame) -> list:
    rows = []
    for tkr, r in scored.iterrows():
        extra = {k: (None if pd.isna(r.get(k)) else float(r.get(k)))
                 for k in ["earnings_yield", "fcf_yield", "ev_ebitda", "ev_sales", "pe",
                           "op_margin", "roic", "revenue_growth", "ret_12_1", "net_debt_to_ebitda"]
                 if k in scored.columns}
        rows.append({
            "ticker": tkr, "name": r.get("name") or tkr, "sector": r.get("sector") or "",
            "bucket": r.get("bucket"), "price": _f(r.get("price")), "market_cap": _f(r.get("market_cap")),
            "hot_score": _f(r.get("hot_score")), "composite": _f(r.get("composite")),
            "rank": int(r.get("rank")),
            "z_value": _f(r.get("value")), "z_quality": _f(r.get("quality")),
            "z_growth": _f(r.get("growth")), "z_momentum": _f(r.get("momentum")),
            "z_insider": _f(r.get("insider")), "fair_value": None, "upside": None, "extra": extra,
        })
    return rows


def _f(x):
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        return float(x)
    except (TypeError, ValueError):
        return None


def run_scan(scope: str = "bundled", limit: Optional[int] = None, cfg=CONFIG,
             store: Optional[Store] = None, provider=None, run_dcf_top: int = 0,
             progress: Optional[Callable] = None, save: bool = True) -> dict:
    store = store or Store()
    provider = provider or get_provider(cfg, store)

    uni = provider.get_universe(scope)
    if limit:
        uni = uni[:limit]
    sector_hint = {u["ticker"]: u.get("sector") for u in uni}

    metrics = []
    total = len(uni)
    for i, u in enumerate(uni):
        m = provider.get_metrics(u["ticker"])
        if not m:
            continue
        if not m.get("sector") and sector_hint.get(u["ticker"]):
            m["sector"] = sector_hint[u["ticker"]]
        m.setdefault("ticker", u["ticker"])
        if not passes_gates(m):
            continue
        metrics.append(m)
        if progress and i % 25 == 0:
            progress(i, total)

    if not metrics:
        return {"scan_date": _today(), "rows": [], "universe_size": total, "scored": 0}

    df = build_frame(metrics)
    df["composite"] = _composites(df)
    scored = df[df["composite"].notna()].copy()
    if scored.empty:
        return {"scan_date": _today(), "rows": [], "universe_size": total, "scored": 0}

    scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1
    scored = scored.sort_values("composite", ascending=False)
    scored["rank"] = range(1, len(scored) + 1)
    rows = _rows_from(scored)

    # Deep-value the top names with the full DCF (optional, network-heavy).
    if run_dcf_top and run_dcf_top > 0:
        _enrich_with_dcf(rows[:run_dcf_top], cfg)

    scan_date = _today()
    if save:
        store.save_snapshot(scan_date, rows, provider.name,
                            {"universe_size": total, "scope": scope})
    return {"scan_date": scan_date, "rows": rows, "universe_size": total,
            "scored": len(rows), "provider": provider.name}


def _enrich_with_dcf(rows, cfg):
    try:
        from ..engine.pipeline import value_ticker
    except Exception:
        return
    for r in rows:
        try:
            res = value_ticker(r["ticker"], cfg, mc_trials=1500)
            r["fair_value"] = res.base_fair_value
            r["upside"] = res.upside
        except Exception:
            continue


def _today() -> str:
    return _dt.date.today().isoformat()
