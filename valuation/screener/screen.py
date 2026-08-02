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
from .factors import build_frame, prefilter
from .cross_sectional import composite_score
from .providers import get_provider
from .store import Store


def _effective_weights(store):
    """Live weights = the latest self-learning-adopted weights, else the defaults."""
    est = (store.latest_learned_weights("established") if store else None) or S.WEIGHTS_ESTABLISHED
    spec = (store.latest_learned_weights("speculative") if store else None) or S.WEIGHTS_SPECULATIVE
    return est, spec


def _p_established(df: pd.DataFrame) -> pd.Series:
    """Smooth probability a name is 'established' (profitable), from operating margin:
    0% → 0.5, +5% → 0.73, −5% → 0.27. Falls back to the hard bucket if margin is missing."""
    om = pd.to_numeric(df.get("op_margin"), errors="coerce")
    # Clip the exponent before exp(). A name with a huge negative operating margin (early-stage
    # biotech, a shell with token revenue) sends this to exp(1e4) and numpy warns about
    # overflow on every scan. The saturated answer is already correct — 0 or 1 — so this only
    # silences a spurious RuntimeWarning, it does not change any score.
    p = 1.0 / (1.0 + np.exp(np.clip(-(om / 0.05), -700.0, 700.0)))
    hard = (df["bucket"] == "established").astype(float)
    return p.fillna(hard)


def _composites(df: pd.DataFrame, est_w=None, spec_w=None, soft=None) -> pd.Series:
    est_w = est_w or S.WEIGHTS_ESTABLISHED
    spec_w = spec_w or S.WEIGHTS_SPECULATIVE
    if soft is None:
        soft = getattr(CONFIG, "soft_bucket", True)

    # Soft bucketing: a borderline name (tiny profit/loss) shouldn't be scored 100% by
    # one rulebook. Score it under BOTH and blend by how established it looks, so the
    # cutoff is a gradient, not a cliff.
    if soft and "value_est" in df.columns and "value_spec" in df.columns:
        d = df.copy()
        d["value"] = df["value_est"]
        comp_est = composite_score(d, est_w)
        d["value"] = df["value_spec"]
        comp_spec = composite_score(d, spec_w)
        p = _p_established(df)
        return p * comp_est + (1.0 - p) * comp_spec

    # Hard split (original behavior; used when soft bucketing is off).
    comps = pd.Series(index=df.index, dtype=float)
    for bucket, w in [("established", est_w), ("speculative", spec_w)]:
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
        # Persist EVERY theme column (not just the legacy five) so the monthly
        # learner can tune the newer themes too. Legacy z_* columns stay for the UI.
        extra["factors"] = {f: _f(r.get(f)) for f in S.FACTORS_ALL if f in scored.columns}
        # Persist each individual number's z-score too, so the Edge Lab can measure
        # each number's standalone predictive power over time (visibility only).
        extra["numbers"] = {n: _f(r.get("z_" + n)) for n in S.NUMBERS_ALL if ("z_" + n) in scored.columns}
        extra["vol"] = _f(r.get("realized_vol"))       # for inverse-volatility position sizing
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


def _cov(rows: list, ok) -> float:
    """Fraction of rows for which `ok` holds — used for the display-field health panel."""
    if not rows:
        return 0.0
    return round(sum(1 for r in rows if ok(r)) / len(rows), 3)


def _fill_from_universe(m: dict, u: Optional[dict]) -> dict:
    """Backfill display fields the per-name fetch didn't supply, from the universe listing.

    Only fills what is genuinely missing, so a real fetched value always wins. A `name` equal
    to the ticker counts as missing: that is what the Yahoo path falls back to when its `.info`
    call is throttled, and "DELL" is not a company name. Market cap is a display/eligibility
    field here, and the listing reports it in USD dollars like everything else.
    """
    if not u:
        return m
    tkr = (m.get("ticker") or u.get("ticker") or "").upper()
    if not (m.get("name") or "").strip() or (m.get("name") or "").strip().upper() == tkr:
        if (u.get("name") or "").strip():
            m["name"] = u["name"]
    for k in ("sector", "industry"):
        if not (m.get(k) or "").strip() and (u.get(k) or "").strip():
            m[k] = u[k]
    # Live quote fields the broker supplies for free with the universe (price, average
    # dollar volume, nearness to the 52-week high). Only used where the fundamentals feed
    # left a hole — which for `high_prox` is every FMP row, so momentum gains an input it
    # never had rather than having one overwritten.
    for k in ("price", "avg_dollar_volume", "high_prox"):
        if m.get(k) is None and u.get(k) is not None:
            m[k] = u[k]
    if not m.get("market_cap") and u.get("market_cap"):
        m["market_cap"] = u["market_cap"]
    return m


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
    # The universe listing already carries a company name / sector / market cap (FMP's
    # screener returns all three; SEC EDGAR's filer list returns the legal name). The
    # per-name fetch does NOT reliably re-supply them — yfinance's `.info` is rate-limited
    # from cloud IPs and comes back empty, which is how the book ended up showing bare
    # tickers and an "unknown" sector breakdown. Keep the listing's values as a fallback.
    hints = {u["ticker"]: u for u in uni}

    total = len(uni)
    workers = max(1, int(getattr(cfg, "scan_workers", 8) or 8)) if cfg is not None else 8

    # Fetch metrics concurrently — each get_metrics is I/O-bound (network), so a bounded
    # thread pool cuts a whole-market scan from ~sequential minutes to a fraction. Results
    # are keyed by ticker, then processed in the original order for deterministic output.
    fetched = {}
    if workers > 1 and total > 1:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(provider.get_metrics, u["ticker"]): u["ticker"] for u in uni}
            for fut in as_completed(futs):
                try:
                    fetched[futs[fut]] = fut.result()
                except Exception:
                    fetched[futs[fut]] = None
                done += 1
                if progress and done % 50 == 0:
                    progress(done, total)
    else:
        for i, u in enumerate(uni):
            try:
                fetched[u["ticker"]] = provider.get_metrics(u["ticker"])
            except Exception:
                fetched[u["ticker"]] = None
            if progress and i % 25 == 0:
                progress(i, total)

    metrics = []
    filtered = {}          # reason -> count
    filtered_examples = {}  # reason -> sample tickers
    for u in uni:
        m = fetched.get(u["ticker"])
        if not m:
            filtered["no data"] = filtered.get("no data", 0) + 1
            continue
        _fill_from_universe(m, hints.get(u["ticker"]))
        m.setdefault("ticker", u["ticker"])
        keep, reason = prefilter(m)
        if not keep:
            filtered[reason] = filtered.get(reason, 0) + 1
            ex = filtered_examples.setdefault(reason, [])
            if len(ex) < 8:
                ex.append(m["ticker"])
            continue
        metrics.append(m)

    audit = {"total_removed": sum(filtered.values()), "by_reason": filtered,
             "examples": filtered_examples}

    if not metrics:
        return {"scan_date": _today(), "rows": [], "universe_size": total,
                "scored": 0, "filtered": audit}

    df = build_frame(metrics)
    df["composite"] = _composites(df, *_effective_weights(store))
    scored = df[df["composite"].notna()].copy()
    if scored.empty:
        return {"scan_date": _today(), "rows": [], "universe_size": total, "scored": 0}

    scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1
    scored = scored.sort_values("composite", ascending=False)
    scored["rank"] = range(1, len(scored) + 1)
    rows = _rows_from(scored)

    # Per-pick "why" — the top theme contributions (weight × standardized theme) behind
    # each name's score, so a pick is explainable ("here because: quality, value").
    est_w, spec_w = _effective_weights(store)
    for r in rows:
        fac = (r.get("extra") or {}).get("factors") or {}
        w = est_w if r.get("bucket") == "established" else spec_w
        contribs = [(k, w.get(k, 0.0) * v) for k, v in fac.items() if v is not None and k in w]
        contribs.sort(key=lambda x: abs(x[1]), reverse=True)
        r["extra"]["why"] = [{"theme": k, "c": round(c, 3)} for k, c in contribs[:4] if abs(c) > 1e-6]

    # Deep-value the top names with the full DCF (optional, network-heavy).
    if run_dcf_top and run_dcf_top > 0:
        _enrich_with_dcf(rows[:run_dcf_top], cfg)

    # Data-health panel — catch silent data rot (a whole theme going missing, coverage
    # cratering) the day it happens, instead of finding out via bad picks weeks later.
    health = {
        "universe": total,
        "fetched": int(sum(1 for v in fetched.values() if v)),
        "passed_filter": len(metrics),
        "scored": len(rows),
        "theme_coverage": {t: round(float(scored[t].notna().mean()), 2)
                           for t in S.FACTORS_ALL if t in scored.columns},
        # Display-field coverage. A blank company name or sector is not a scoring bug, so
        # nothing else would ever report it — and it went unnoticed on the live site for
        # weeks. Measured on the rows that actually ship.
        "display_coverage": {
            "name": _cov(rows, lambda r: (r.get("name") or "").strip()
                         and (r.get("name") or "").strip().upper() != r["ticker"].upper()),
            "sector": _cov(rows, lambda r: (r.get("sector") or "").strip()),
            "market_cap": _cov(rows, lambda r: r.get("market_cap")),
        },
    }
    note = getattr(provider, "universe_note", "")
    if note:
        health["universe_note"] = note
    budget = getattr(provider, "budget", None)
    if budget:
        health["api_budget"] = budget

    scan_date = _today()
    if save:
        store.save_snapshot(scan_date, rows, provider.name,
                            {"universe_size": total, "scope": scope, "filtered": audit, "health": health})
        # Dated, append-only archive of what we picked and when — a survivorship-free
        # record independent of the DB (which a Render restart can lose without a disk).
        try:
            from ..edge.archive import archive_scan
            archive_scan(rows, scan_date, provider.name)
        except Exception:
            pass
    return {"scan_date": scan_date, "rows": rows, "universe_size": total,
            "scored": len(rows), "provider": provider.name, "filtered": audit, "health": health}


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
