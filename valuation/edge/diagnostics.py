"""
Number diagnostics — VISIBILITY ONLY.

Measures each individual number's *standalone* predictive power (its information
coefficient: the correlation between the number's cross-sectional rank and the
realized forward return) over the tool's accumulated snapshots.

This does NOT tune anything. Numbers stay equal-weighted inside their theme — this
is here so you can SEE which numbers are actually pulling weight and which are dead,
and decide by hand whether to retire one or promote it to its own theme. Auto-tuning
correlated numbers within a theme is exactly where overfitting bites, so we don't.
"""
from __future__ import annotations

import datetime as _dt

from ..screener import settings as S


def compute_number_ic(store, price_fn=None, top_per_date=80, horizon=21, min_dates=6) -> dict:
    from ..backtest.engine import information_coefficient
    from .autolearn import build_panel_from_snapshots
    if price_fn is None:
        from ..screener.prices import close_series
        price_fn = lambda t: close_series(t, days=1500)

    panel = build_panel_from_snapshots(store, price_fn, top_per_date=top_per_date,
                                       horizon=horizon, source_key="numbers", columns=S.NUMBERS_ALL)
    dates = 0 if (panel is None or panel.empty) else int(panel["date"].nunique())
    if panel is None or panel.empty or dates < min_dates:
        return {"status": "insufficient data", "dates": dates, "numbers": []}

    out = []
    for n in S.NUMBERS_ALL:
        if n not in panel.columns:
            continue
        cov = float(panel[n].notna().mean())
        ic = None
        if cov > 0:
            v = information_coefficient(panel, n, "fwd_ret", "date").get("mean_ic")
            ic = float(v) if v == v else None            # drop NaN
        out.append({"number": n, "theme": S.NUMBER_THEME.get(n), "ic": ic, "coverage": round(cov, 2)})

    # group by theme, strongest |IC| first within each
    out.sort(key=lambda r: (r["theme"], -(abs(r["ic"]) if r["ic"] is not None else -1.0)))
    return {"status": "ok", "dates": dates, "rows": int(len(panel)),
            "horizon": horizon, "numbers": out}


def run_number_diagnostics(cfg, store, price_fn=None) -> dict:
    """Compute + persist the number-IC snapshot (called on the monthly learning run)."""
    res = compute_number_ic(store, price_fn=price_fn,
                            top_per_date=int(getattr(cfg, "learn_top_per_date", 60)),
                            horizon=int(getattr(cfg, "learn_horizon_days", 21)),
                            min_dates=int(getattr(cfg, "learn_min_dates", 6)))
    res["computed_at"] = _dt.datetime.utcnow().isoformat()
    try:
        store.set_meta("number_ic", res)
    except Exception:
        pass
    return res
