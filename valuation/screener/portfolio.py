"""
Portfolio construction from the hot list.

Turns the top-ranked names into an actual weighted basket you could hold:
equal- or score-weighted, with a per-sector cap so it isn't secretly a bet on one
sector, plus diversification and expected-characteristic stats. Long-only,
educational — it sizes positions, it doesn't place orders.
"""
from __future__ import annotations

from statistics import mean


def _normalize(weights: dict) -> dict:
    tot = sum(weights.values())
    if tot <= 0:
        n = len(weights)
        return {k: 1.0 / n for k in weights} if n else {}
    return {k: v / tot for k, v in weights.items()}


def _apply_sector_cap(weights: dict, sectors: dict, cap: float, passes=6) -> dict:
    w = dict(weights)
    for _ in range(passes):
        by_sector = {}
        for t, wt in w.items():
            by_sector.setdefault(sectors.get(t, "?"), 0.0)
            by_sector[sectors.get(t, "?")] += wt
        over = {s: tot for s, tot in by_sector.items() if tot > cap + 1e-9}
        if not over:
            break
        for s, tot in over.items():
            scale = cap / tot
            for t in [t for t in w if sectors.get(t, "?") == s]:
                w[t] *= scale
        w = _normalize(w)
    return _normalize(w)


def build_portfolio(rows: list, n=15, weighting="score", max_sector_weight=0.35,
                    weight_field="hot_score") -> dict:
    picks = [r for r in rows if r.get("price")][:n]
    if not picks:
        return {"positions": [], "stats": {}, "sector_allocation": []}

    sectors = {r["ticker"]: (r.get("sector") or "Unknown") for r in picks}
    if weighting == "equal":
        raw = {r["ticker"]: 1.0 for r in picks}
    else:  # score-weighted (shift so all positive)
        vals = [r.get(weight_field) or 0 for r in picks]
        lo = min(vals)
        raw = {r["ticker"]: (r.get(weight_field) or 0) - lo + 1.0 for r in picks}
    weights = _apply_sector_cap(_normalize(raw), sectors, max_sector_weight)

    positions = []
    for r in picks:
        t = r["ticker"]
        positions.append({"ticker": t, "name": r.get("name"), "sector": sectors[t],
                          "weight": round(weights.get(t, 0.0), 4), "hot_score": r.get("hot_score"),
                          "price": r.get("price"), "fair_value": r.get("fair_value"),
                          "upside": r.get("upside")})
    positions.sort(key=lambda p: p["weight"], reverse=True)

    # Sector allocation
    alloc = {}
    for p in positions:
        alloc[p["sector"]] = alloc.get(p["sector"], 0.0) + p["weight"]
    sector_allocation = sorted(({"sector": s, "weight": round(w, 4)} for s, w in alloc.items()),
                               key=lambda x: x["weight"], reverse=True)

    # Weighted factor exposures + diversification
    def wavg(field):
        num = sum((weights.get(r["ticker"], 0) * (r.get(field) or 0)) for r in picks)
        return num  # weights already sum to 1

    hhi = sum(p["weight"] ** 2 for p in positions)  # concentration (1/n .. 1)
    ups = [p["upside"] for p in positions if p.get("upside") is not None]
    stats = {
        "n_names": len(positions), "n_sectors": len(alloc),
        "max_sector_weight": round(max(alloc.values()), 4) if alloc else 0,
        "effective_names": round(1.0 / hhi, 1) if hhi else 0,
        "concentration_hhi": round(hhi, 4),
        "weighted_hot_score": round(wavg("hot_score"), 1),
        "exposure_value": round(wavg("z_value"), 2), "exposure_quality": round(wavg("z_quality"), 2),
        "exposure_growth": round(wavg("z_growth"), 2), "exposure_momentum": round(wavg("z_momentum"), 2),
        "avg_upside": round(mean(ups), 4) if ups else None,
        "weighting": weighting, "max_sector_cap": max_sector_weight,
    }
    return {"positions": positions, "stats": stats, "sector_allocation": sector_allocation}
