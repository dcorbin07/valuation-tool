"""
Valquo Index export — the tracked paper book, as a plain JSON file.

A broad top-decile, large-cap-tilted book: the construction the backtest supports, and the
one whose result is least dependent on a handful of names. (The older note here said the
concentrated top-25 "lost" — that was true of the pre-P5 model and is no longer: post-P5 the
top-25 book scores HIGHER gross. It is also the noisiest statistic in the study, so breadth
is still the right choice for a tracked book — for robustness, not because concentration
underperforms.) What this exports:

  1. take the latest scan,
  2. keep the large caps (the market-cap tier where the measured IC was strongest),
  3. keep the top decile of those by hot score,
  4. weight them, and write the list out.

Written to data/ (gitignored) so the Cowork side can pick it up and track it against SPY
without this repo carrying a data file that changes every day.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from typing import Optional

DEFAULT_PATH = os.path.join("data", "valquo_index.json")
LARGE_CAP_MIN = 10e9          # $10B+ = "large cap" for the tilt
TOP_DECILE = 0.10
MIN_NAMES = 10                # a "decile" of a small scan would be too thin to be a book
MAX_WEIGHT = 0.08             # no single name dominates


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def build_index(rows, large_cap_min: float = LARGE_CAP_MIN,
                top_decile: float = TOP_DECILE, weighting: str = "score",
                top_n: int | None = None) -> dict:
    """Top-decile, large-cap-tilted book from scan rows. Pure function — easy to test."""
    scored = [r for r in rows if _f(r.get("hot_score")) is not None and _f(r.get("price"))]

    large = [r for r in scored if (_f(r.get("market_cap")) or 0) >= large_cap_min]
    tilt = "large-cap only"
    # If the scan doesn't carry market caps (or is a small universe), fall back to the
    # biggest half rather than silently emitting an all-cap book under a large-cap label.
    if len(large) < MIN_NAMES:
        with_mc = [r for r in scored if _f(r.get("market_cap"))]
        if len(with_mc) >= MIN_NAMES:
            with_mc.sort(key=lambda r: -_f(r.get("market_cap")))
            large = with_mc[:max(MIN_NAMES, len(with_mc) // 2)]
            tilt = "largest half (too few names above the large-cap floor)"
        else:
            large = scored
            tilt = "no market-cap data — all scored names"

    large.sort(key=lambda r: -_f(r.get("hot_score")))
    # A FIXED book size (top_n) or a fraction of the eligible tier (top_decile). The roth
    # config is a 25-name book; taxable is the decile.
    n = int(top_n) if top_n else max(MIN_NAMES, int(round(len(large) * top_decile)))
    n = max(MIN_NAMES, n)
    picks = large[:min(n, len(large))]

    if weighting == "equal" or not picks:
        raw = {r["ticker"]: 1.0 for r in picks}
    else:
        # Score-weighted above the cohort's floor, so the weight reflects the *edge*
        # rather than the arbitrary 1-100 offset every name carries.
        floor = min(_f(r.get("hot_score")) for r in picks)
        raw = {r["ticker"]: max(0.01, _f(r.get("hot_score")) - floor + 1.0) for r in picks}

    total = sum(raw.values()) or 1.0
    weights = {k: v / total for k, v in raw.items()}
    # The cap is only reachable if n * MAX_WEIGHT >= 1 — with 10 names an 8% cap would
    # sum to 80% and the redistribution below would loop forever pushing past it. So the
    # effective cap never goes below equal weight.
    cap = max(MAX_WEIGHT, 1.0 / len(picks)) if picks else MAX_WEIGHT
    if picks and cap <= 1.0 / len(picks) + 1e-12:
        # The cap has collapsed to equal weight, which is then the ONLY feasible
        # solution. Assign it directly — iterating would just oscillate toward it.
        weights = {k: 1.0 / len(picks) for k in raw}
    for _ in range(12):
        over = {k: w for k, w in weights.items() if w > cap + 1e-12}
        if not over:
            break
        excess = sum(w - cap for w in over.values())
        for k in over:
            weights[k] = cap
        rest = {k: w for k, w in weights.items() if k not in over}
        rest_total = sum(rest.values()) or 1.0
        if rest_total <= 0:
            break
        for k in rest:
            weights[k] += excess * rest[k] / rest_total

    positions = [{
        "ticker": r["ticker"], "name": (r.get("name") or "")[:60],
        "sector": r.get("sector") or "", "rank": r.get("rank"),
        "hot_score": round(_f(r.get("hot_score")), 2),
        "price": round(_f(r.get("price")), 4),
        "market_cap": _f(r.get("market_cap")),
        "weight": round(weights.get(r["ticker"], 0.0), 5),
    } for r in picks]

    # Sector breakdown. A source with no sector column (the Sharadar export has none) would
    # otherwise emit {"": 1.0} — which reads to a downstream consumer as "one real sector
    # holds the entire book" rather than "this data is missing". Say missing explicitly.
    sectors = {}
    for p in positions:
        key = p["sector"] or "unknown"
        sectors[key] = round(sectors.get(key, 0.0) + p["weight"], 5)
    sector_data = any(p["sector"] for p in positions)

    return {
        "name": "Valquo Index",
        "method": ("Broad top-decile of the large-cap tier by hot score, score-weighted and "
                   "capped at 8%. On the full 2,710-name / 110-date backtest the top decile "
                   "returns +11.8%/yr over equal-weight gross, +11.4% net of modelled "
                   "transaction costs (breakeven 236bps one-way vs ~37bps actual). Breadth is "
                   "chosen for robustness, not because concentration underperforms: the "
                   "top-25 book actually scores higher (+20.7% gross alpha) but is the "
                   "noisiest number in the study, so the decile is the honest book to track."),
        "criteria": {"large_cap_min": large_cap_min, "top_decile": top_decile,
                     "top_n": (int(top_n) if top_n else None),
                     "tilt": tilt, "weighting": weighting,
                     "max_weight": MAX_WEIGHT, "effective_max_weight": round(cap, 5)},
        "n_scored": len(scored), "n_eligible": len(large), "n_positions": len(positions),
        "sector_data_available": sector_data,
        "sector_weights": dict(sorted(sectors.items(), key=lambda kv: -kv[1])),
        "positions": positions,
    }


def _full_universe_rows(data_dir: str, limit: int = 3000):
    """Score the WHOLE Sharadar universe as of its latest date -> (rows, as_of, dropped).

    The live-scan store is whatever the last FMP scan happened to cover, which is a few
    hundred names at best — and a "top decile" of that collapses to the 10-name MIN_NAMES
    floor, i.e. ten mega-caps wearing a decile's label. Scoring the full point-in-time
    universe instead gives a real decile (86 of 861 eligible large caps at last run) and needs
    no live API, so a quarterly rebalance can run headless.
    """
    from .data_providers import WRDSProvider
    from .fundamental_panel import score_universe_now
    from ..screener import universe as U

    class _Cfg:
        wrds_data_dir = data_dir

    prov = WRDSProvider(_Cfg())
    ok, msg = prov.ready()
    if not ok:
        raise RuntimeError(f"Sharadar export not readable at {data_dir!r}: {msg}")
    tickers = prov.universe(limit=limit) or list(U.bundled_tickers())
    res = score_universe_now(prov, tickers)
    if not res or not res.get("rows"):
        raise RuntimeError("scored no rows from the full universe")
    return res["rows"], res.get("as_of"), (res.get("dropped_mc_divergence") or [])


def export(store=None, path: str = DEFAULT_PATH, data_dir: str | None = None,
           limit: int = 3000, config: str | None = None, **kw) -> dict:
    """Build the book and write the JSON. Returns the payload.

    `data_dir` -> score the full Sharadar universe point-in-time (the headless path, and the
    one that produces a genuine top decile). Otherwise fall back to the latest saved live scan.
    """
    # A named book config (settings.BOOK_CONFIGS) fixes width, cadence and band together, so
    # the emitted book cannot drift from the construction that was actually validated.
    cfg_meta = None
    if config:
        from ..screener import settings as S
        cfg_meta = (S.BOOK_CONFIGS or {}).get(config)
        if not cfg_meta:
            raise RuntimeError(f"unknown book config {config!r}; "
                               f"known: {sorted(S.BOOK_CONFIGS or {})}")
        if cfg_meta.get("top_n"):
            kw["top_n"] = cfg_meta["top_n"]
        if cfg_meta.get("top_frac"):
            kw["top_decile"] = cfg_meta["top_frac"]
    dropped, scan_date = [], None
    if data_dir:
        rows, scan_date, dropped = _full_universe_rows(data_dir, limit=limit)
        source = ("Sharadar SF1+SEP export via WRDSProvider (point-in-time), "
                  "shipped settings.py weights")
    else:
        if store is None:
            from ..screener.store import Store
            store = Store()
        scan_date = store.latest_scan_date()
        rows = store.load_snapshot(scan_date) if scan_date else []
        source = "latest saved live scan snapshot"
    payload = build_index(rows, **kw)
    payload["scan_date"] = scan_date
    payload["data_as_of"] = scan_date
    payload["source"] = source
    # Names whose market cap could not be established (DAILY vs shares x price disagree) are
    # excluded from a tradeable book; recorded so the omission is auditable, not silent.
    payload["excluded_market_cap_divergence"] = [
        {"ticker": d["ticker"], "daily_mc": d["daily_mc"], "derived_mc": d["derived_mc"],
         "ratio": round(d["ratio"], 2)} for d in dropped]
    if cfg_meta:
        # The band is a REBALANCE rule (it compares against the previous book), so a one-shot
        # export cannot apply it — it is emitted as instruction for whoever rebalances.
        payload["config"] = {
            "name": config, "label": cfg_meta.get("label"),
            "rebalance_days": cfg_meta.get("rebalance_days"),
            # TRADING days -> calendar months, which is what a human schedules on.
            "rebalance_months": (round(cfg_meta["rebalance_days"] / 21.0, 1)
                                 if cfg_meta.get("rebalance_days") else None),
            "exit_frac": cfg_meta.get("exit_frac"),
            "exit_mult": cfg_meta.get("exit_mult"),
            "band_note": ("hold an existing position until it falls past this rank/fraction; "
                          "requires the PREVIOUS book, so it is applied at rebalance time, not "
                          "in this snapshot"),
            "measured": cfg_meta.get("measured")}
    payload["generated_at"] = _dt.datetime.now().replace(microsecond=0).isoformat()

    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    payload["path"] = path
    return payload


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Export the Valquo Index (top-decile large caps).")
    ap.add_argument("--out", default=DEFAULT_PATH)
    ap.add_argument("--large-cap-min", type=float, default=LARGE_CAP_MIN)
    ap.add_argument("--top-decile", type=float, default=TOP_DECILE)
    ap.add_argument("--weighting", choices=("score", "equal"), default="score")
    ap.add_argument("--full-universe", nargs="?", const="data/backtest", default=None,
                    metavar="DATA_DIR",
                    help="score the whole Sharadar universe point-in-time instead of the last "
                         "live scan (headless; the only path that yields a real top decile). "
                         "Optionally takes the export dir, default data/backtest.")
    ap.add_argument("--limit", type=int, default=3000, help="universe size for --full-universe")
    ap.add_argument("--config", default=None,
                    help="named book config: 'roth' (top-25, 6-week, no band) or 'taxable' "
                         "(decile, quarterly, 20%% band). Sets width and emits the cadence.")
    a = ap.parse_args(argv)
    try:
        p = export(path=a.out, large_cap_min=a.large_cap_min, top_decile=a.top_decile,
                   weighting=a.weighting, data_dir=a.full_universe, limit=a.limit,
                   config=a.config)
    except RuntimeError as e:
        print(f"Could not build the book: {e}")
        return 1
    if not p["positions"]:
        print("No positions — no scan snapshot yet (run a scan first), or try --full-universe.")
        return 1
    print(f"Valquo Index -> {p['path']}   as of {p.get('data_as_of')}   "
          f"{p['n_positions']} of {p['n_eligible']} eligible ({p['n_scored']} scored)")
    print(f"  source: {p.get('source')}")
    if p.get("config"):
        _c = p["config"]
        print(f"  config: {_c['name']} — {_c.get('label')}")
        print(f"  rebalance every {_c.get('rebalance_days')} trading days "
              f"(~{_c.get('rebalance_months')} months)"
              + (f", no-trade band {_c['exit_frac']:.0%}" if _c.get("exit_frac") else ", no band"))
    print(f"  tilt: {p['criteria']['tilt']}")
    if p["n_scored"] < 200:
        print(f"  WARNING: only {p['n_scored']} names scored — a 'top decile' of that is not a "
              f"decile. Use --full-universe for a real book.")
    if p.get("excluded_market_cap_divergence"):
        print("  excluded (market cap unverifiable): "
              + ", ".join(f"{d['ticker']} ({d['ratio']:.0f}x)"
                          for d in p["excluded_market_cap_divergence"][:6]))
    for x in p["positions"][:15]:
        print(f"   {x['ticker']:6} {x['weight']*100:5.2f}%  hot {x['hot_score']:5.1f}  {x['sector'][:22]}")
    if len(p["positions"]) > 15:
        print(f"   ... and {len(p['positions']) - 15} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
