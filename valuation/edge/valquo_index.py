"""
Valquo Index export — the tracked paper book, as a plain JSON file.

The backtest's one honest conclusion about *construction* is that a broad top-decile,
large-cap-tilted book is the only version that beat equal-weight; the concentrated
top-25 lost. So that's exactly what this exports:

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
                top_decile: float = TOP_DECILE, weighting: str = "score") -> dict:
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
    n = max(MIN_NAMES, int(round(len(large) * top_decile)))
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

    sectors = {}
    for p in positions:
        sectors[p["sector"]] = round(sectors.get(p["sector"], 0.0) + p["weight"], 5)

    return {
        "name": "Valquo Index",
        "method": ("Broad top-decile of the large-cap tier by hot score, score-weighted and "
                   "capped — the only construction that beat equal-weight in the backtest "
                   "(the concentrated top-25 lost)."),
        "criteria": {"large_cap_min": large_cap_min, "top_decile": top_decile,
                     "tilt": tilt, "weighting": weighting,
                     "max_weight": MAX_WEIGHT, "effective_max_weight": round(cap, 5)},
        "n_scored": len(scored), "n_eligible": len(large), "n_positions": len(positions),
        "sector_weights": dict(sorted(sectors.items(), key=lambda kv: -kv[1])),
        "positions": positions,
    }


def export(store=None, path: str = DEFAULT_PATH, **kw) -> dict:
    """Build from the latest saved scan and write the JSON. Returns the payload."""
    if store is None:
        from ..screener.store import Store
        store = Store()
    scan_date = store.latest_scan_date()
    rows = store.load_snapshot(scan_date) if scan_date else []
    payload = build_index(rows, **kw)
    payload["scan_date"] = scan_date
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
    a = ap.parse_args(argv)
    p = export(path=a.out, large_cap_min=a.large_cap_min,
               top_decile=a.top_decile, weighting=a.weighting)
    if not p["positions"]:
        print("No positions — no scan snapshot yet (run a scan first).")
        return 1
    print(f"Valquo Index -> {p['path']}   scan {p.get('scan_date')}   "
          f"{p['n_positions']} of {p['n_eligible']} eligible ({p['n_scored']} scored)")
    print(f"  tilt: {p['criteria']['tilt']}")
    for x in p["positions"][:15]:
        print(f"   {x['ticker']:6} {x['weight']*100:5.2f}%  hot {x['hot_score']:5.1f}  {x['sector'][:22]}")
    if len(p["positions"]) > 15:
        print(f"   ... and {len(p['positions']) - 15} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
