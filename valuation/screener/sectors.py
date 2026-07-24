"""
Sector attractiveness — which corners of the market are screening best right now.

Aggregates a scan snapshot by sector: average composite and factor scores, how
many names land in the top decile, and average momentum. Lets you see, at a
glance, whether the "hot" names are concentrated in a few attractive sectors or
spread out — and which sectors to fish in.
"""
from __future__ import annotations

from statistics import mean, median


def _avg(vals):
    v = [x for x in vals if x is not None]
    return mean(v) if v else None


def sector_attractiveness(rows: list) -> list:
    """Return per-sector aggregates, sorted most attractive first."""
    by_sector: dict = {}
    n_total = len(rows)
    top_decile_cut = max(1, n_total // 10)
    for r in rows:
        s = r.get("sector") or "Unknown"
        by_sector.setdefault(s, []).append(r)

    out = []
    for sector, items in by_sector.items():
        comps = [r.get("composite") for r in items]
        n_top = sum(1 for r in items if (r.get("rank") or 1e9) <= top_decile_cut)
        out.append({
            "sector": sector,
            "count": len(items),
            "avg_composite": _avg(comps),
            "avg_value": _avg([r.get("z_value") for r in items]),
            "avg_quality": _avg([r.get("z_quality") for r in items]),
            "avg_growth": _avg([r.get("z_growth") for r in items]),
            "avg_momentum": _avg([r.get("z_momentum") for r in items]),
            "avg_hot_score": _avg([r.get("hot_score") for r in items]),
            "n_in_top_decile": n_top,
            "top_decile_share": n_top / len(items) if items else 0.0,
            "median_upside": _median([r.get("upside") for r in items]),
        })
    out.sort(key=lambda x: (x["avg_composite"] is not None, x["avg_composite"] or -9), reverse=True)
    for i, o in enumerate(out, 1):
        o["sector_rank"] = i
    return out


def _median(vals):
    v = [x for x in vals if x is not None]
    return median(v) if v else None
