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
from .attribution import decompose, p_established as _p_established
from .factors import build_frame, prefilter
from .providers import get_provider
from .store import Store


def _effective_weights(store):
    """Live weights = the latest self-learning-adopted weights, else the defaults."""
    est = (store.latest_learned_weights("established") if store else None) or S.WEIGHTS_ESTABLISHED
    spec = (store.latest_learned_weights("speculative") if store else None) or S.WEIGHTS_SPECULATIVE
    return est, spec


def _decompose(df: pd.DataFrame, est_w=None, spec_w=None, soft=None):
    """(composite, per-theme contributions). The composite IS the row-sum of the pieces.

    Both live in `attribution.py` so the score and the explanation of the score cannot come
    from two different calculations — the failure mode where a "why" panel quietly stops
    describing the ranking it sits next to.
    """
    est_w = est_w or S.WEIGHTS_ESTABLISHED
    spec_w = spec_w or S.WEIGHTS_SPECULATIVE
    if soft is None:
        soft = getattr(CONFIG, "soft_bucket", True)
    return decompose(df, est_w, spec_w, soft=soft)


def _composites(df: pd.DataFrame, est_w=None, spec_w=None, soft=None) -> pd.Series:
    return _decompose(df, est_w, spec_w, soft)[0]


def _rows_from(scored: pd.DataFrame) -> list:
    rows = []
    for tkr, r in scored.iterrows():
        extra = {k: (None if pd.isna(r.get(k)) else float(r.get(k)))
                 for k in ["earnings_yield", "fcf_yield", "ev_ebitda", "ev_sales", "pe",
                           "op_margin", "roic", "revenue_growth", "ret_12_1", "net_debt_to_ebitda",
                           # net_debt + revenue let fairvalue.py bridge EV multiples to a
                           # per-share equity value and run the growth (revenue) lens.
                           "net_debt", "revenue", "gross_margin"]
                 if k in scored.columns}
        # Persist EVERY theme column (not just the legacy five) so the monthly
        # learner can tune the newer themes too. Legacy z_* columns stay for the UI.
        extra["factors"] = {f: _f(r.get(f)) for f in S.FACTORS_ALL if f in scored.columns}
        # Persist each individual number's z-score too, so the Edge Lab can measure
        # each number's standalone predictive power over time (visibility only).
        extra["numbers"] = {n: _f(r.get("z_" + n)) for n in S.NUMBERS_ALL if ("z_" + n) in scored.columns}
        extra["vol"] = _f(r.get("realized_vol"))       # for inverse-volatility position sizing
        # Which feed this row's fundamentals came from ("free+broker", "broker", "free").
        # Carried per NAME, not just as a scan-level total, because the two sources cover
        # different fields — a broker-only row has no margins, FCF or revenue growth, so its
        # score rests on fewer themes and a reader comparing two picks should be able to see
        # that rather than infer it.
        src = r.get("source")
        extra["source"] = None if (src is None or (isinstance(src, float) and pd.isna(src))) else str(src)
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


def _theme_contribution(scored: pd.DataFrame) -> dict:
    """Fraction of names each theme actually scores, measured after standardization.

    A theme that is present but constant across the cross-section carries no information:
    zscore() divides by a zero standard deviation and returns all-NaN, and composite_score
    then renormalizes the remaining weights over the themes that survive. Reported next to
    theme_coverage so "the column is full" and "the theme moves the score" stay distinct.
    """
    from .cross_sectional import standardize_factors
    cols = [t for t in S.FACTORS_ALL if t in scored.columns]
    if not cols or scored.empty:
        return {}
    z = standardize_factors(scored, cols)
    return {t: round(float(z[t].notna().mean()), 2) for t in cols}


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

    # Bulk-load fundamentals for the whole universe up front, where the provider supports it.
    # The broker serves 100 symbols per call, so this is ~3 calls per 100 names against a feed
    # that is already paid for — versus one metered per-name round trip each. Optional by
    # contract: a provider without prefetch() behaves exactly as it did before.
    if hasattr(provider, "prefetch"):
        try:
            provider.prefetch([u["ticker"] for u in uni])
        except Exception:
            pass

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
    est_w, spec_w = _effective_weights(store)
    df["composite"], contrib = _decompose(df, est_w, spec_w)
    scored = df[df["composite"].notna()].copy()
    if scored.empty:
        return {"scan_date": _today(), "rows": [], "universe_size": total, "scored": 0}

    scored["hot_score"] = scored["composite"].rank(pct=True) * 99 + 1
    scored = scored.sort_values("composite", ascending=False)
    scored["rank"] = range(1, len(scored) + 1)
    rows = _rows_from(scored)

    # Per-pick "why" — the exact decomposition of this name's composite into per-theme
    # contributions, biggest mover first, so a pick is explainable ("here because: quality,
    # value; held back by: momentum") rather than a bare number.
    #
    # These come from `decompose()`, the same call that produced the composite, so they SUM
    # to it. The previous version multiplied the stored weight by the pre-standardization
    # theme value and by whichever weight set the hard bucket named — it ranked the themes
    # roughly right but its numbers added up to nothing in particular, and under soft
    # bucketing it credited a weight set the name was only partly scored under.
    from .attribution import row_attribution
    for r in rows:
        tkr = r["ticker"]
        r["extra"]["why"] = row_attribution(contrib.loc[tkr]) if tkr in contrib.index else []
        r["extra"]["why_composite"] = r.get("composite")

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
        # PRESENT is not the same as USABLE, and reporting only the former is how a dead
        # theme hides in plain sight. `insider` is the live example: with no insider_score in
        # the metrics, build_frame sets the whole column to the constant 0.0 — so it is 100%
        # "covered", yet zscore() of a zero-variance column is all-NaN, composite_score
        # renormalizes it away, and its 12.5% weight does nothing. This measures the theme
        # AFTER standardization, i.e. what actually reaches the score.
        "theme_contributing": _theme_contribution(scored),
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
    # Where each name's fundamentals actually came from, and how completely each field is
    # filled. Without this the free route's real coverage is invisible: a name served entirely
    # by the broker still produces a score, so "it ran" says nothing about whether the flow
    # factors (margins, FCF, growth) were present or silently absent.
    try:
        from . import broker_fundamentals as BF
        health["fundamentals"] = BF.coverage(metrics)
    except Exception:
        pass
    bstats = getattr(provider, "broker_stats", None)
    if bstats:
        health.setdefault("fundamentals", {})["broker"] = bstats

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
