#!/usr/bin/env python3
"""
THEME RESTORATION — the fidelity gate, and the vintage arithmetic behind it.

Registered in `PREREG_theme_restoration.md`, committed ALONE at `1d12822` before this file
existed. Every threshold below is fixed there and none may move.

THE QUESTION. The live book scores 4 of 7 weighted themes and fails the calibrated long-short
floor (1.8811 vs 2.2837); the validated seven-theme composite clears it (2.6199). Restoring the
three dead themes is a COHERENCE fix — live must run what was validated. But the live sources are
raw-EDGAR APPROXIMATIONS of the panel's licensed SF2/SF3 themes, and wiring a different theme
under a validated theme's name is the B7 disease. So each theme must first prove it ranks names
the way the panel's own theme does.

    python -m scripts.theme_restoration fidelity     # offline; the gate
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# PREREG §2.1 — the bar. Fixed at 1d12822.
FIDELITY_FLOOR = 0.60
MIN_PAIRS = 100          # PREREG §2.2 — below this the theme is NOT MEASURABLE
MAX_P = 0.01             # PREREG §2.2 — direction/significance floor
CALIB_PCTILE = 95        # PREREG §2.1 — P95 of |rho| between DIFFERENT panel themes

# PREREG §3 — the standing coverage constants, unchanged.
COVERAGE_FLOOR = 0.05
MIN_COVERAGE = 0.30
MIN_DISTINCT = 2

# The three under test, and the panel column each claims to reproduce.
UNDER_TEST = ("capital_discipline", "institutional", "insider")

# Every theme the panel carries, used to calibrate the bar. `sentiment` is excluded because the
# record says it is empty; a constant column cannot enter a correlation.
PANEL_THEMES = ("value", "quality", "growth", "momentum", "insider", "low_risk",
                "capital_discipline", "size", "institutional")

PANEL = os.environ.get(
    "RESTORE_PANEL",
    r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/panel_corrected_69d.pkl")
OUT = os.path.join("data", "free_analysis", "THEME_RESTORATION.json")


def _spearman(x, y):
    """(rho, p, n) over pairwise-complete observations."""
    from scipy import stats
    import numpy as np
    a, b = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    m = ~(np.isnan(a) | np.isnan(b))
    if m.sum() < 3:
        return None, None, int(m.sum())
    r = stats.spearmanr(a[m], b[m])
    return float(r.statistic), float(r.pvalue), int(m.sum())


def _quintile_agreement(x, y):
    """Fraction of names landing in the same quintile on both sides. Diagnostic only."""
    import numpy as np
    import pandas as pd
    s = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(s) < 25:
        return None
    try:
        qx = pd.qcut(s["x"].rank(method="first"), 5, labels=False)
        qy = pd.qcut(s["y"].rank(method="first"), 5, labels=False)
    except ValueError:
        return None
    return float((qx == qy).mean())


def panel_cross_section(path: str = PANEL):
    """The panel's most recent rebalance cross-section, indexed by ticker."""
    import pandas as pd
    p = pd.read_pickle(path)
    last = p["date"].max()
    x = p[p["date"] == last].copy()
    x = x.drop_duplicates(subset="ticker").set_index("ticker")
    return x, str(last)[:10]


def calibrated_bar(x) -> dict:
    """PREREG §2.1 — P95 of |rho| between DIFFERENT panel themes, from the panel ALONE.

    This is the X7 method applied to a correlation. A live theme must agree with its panel
    counterpart better than distinct panel themes agree with each other; at or below this level
    the live column is statistically indistinguishable from A DIFFERENT THEME, which is the exact
    failure the gate exists to prevent.
    """
    import numpy as np
    cols = [c for c in PANEL_THEMES if c in x.columns]
    vals, pairs = [], []
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r, _p, n = _spearman(x[a], x[b])
            if r is not None and n >= MIN_PAIRS:
                vals.append(abs(r))
                pairs.append({"a": a, "b": b, "abs_rho": round(abs(r), 4), "n": n})
    p95 = float(np.percentile(vals, CALIB_PCTILE)) if vals else None
    pairs.sort(key=lambda d: -d["abs_rho"])
    return {"n_pairs": len(vals), "p95_abs_rho": p95,
            "median_abs_rho": float(np.median(vals)) if vals else None,
            "max_pair": pairs[0] if pairs else None, "top_pairs": pairs[:5]}


def live_columns() -> dict:
    from scripts import live_theme_sources as M
    return M.build_columns()


def _cov(values: dict, n: int) -> dict:
    vals = [v for v in values.values() if v is not None]
    cov = len(vals) / n if n else 0.0
    distinct = len(set(round(v, 12) for v in vals))
    return {"covered": len(vals), "n": n, "coverage": round(cov, 4),
            "distinct_values": distinct,
            "above_coverage_floor": cov >= COVERAGE_FLOOR,
            "above_min_coverage": cov >= MIN_COVERAGE,
            "usable": cov >= MIN_COVERAGE and distinct >= MIN_DISTINCT}


def fidelity(panel_path: str = PANEL) -> dict:
    import numpy as np
    x, asof = panel_cross_section(panel_path)
    calib = calibrated_bar(x)
    bar = max(FIDELITY_FLOOR, calib["p95_abs_rho"] or 0.0)

    live = live_columns()
    themes = live["themes"]
    n_served = len(next(iter(themes.values()))) if themes else 0

    out = {}
    for t in UNDER_TEST:
        lv = themes.get(t, {})
        cov = _cov(lv, n_served)
        common = [k for k in lv if k in x.index]
        a = [lv[k] if lv[k] is not None else np.nan for k in common]
        b = [x.at[k, t] if t in x.columns else np.nan for k in common]
        rho, p, n = _spearman(a, b)
        measurable = n >= MIN_PAIRS
        passes = bool(measurable and rho is not None and rho > 0
                      and p is not None and p < MAX_P and rho >= bar)
        out[t] = {
            "rho": rho, "p": p, "n_pairs": n, "overlap_names": len(common),
            "bar": bar, "measurable": measurable,
            "quintile_agreement": _quintile_agreement(a, b),
            "coverage": cov,
            "fidelity_pass": passes,
            "coverage_pass": cov["usable"],
            "restores": bool(passes and cov["usable"]),
        }
    return {"prereg": "PREREG_theme_restoration.md", "prereg_commit": "1d12822",
            "panel_asof": asof, "n_served": n_served,
            "bar": {"floor": FIDELITY_FLOOR, "calibrated_p95": calib["p95_abs_rho"],
                    "applied": bar, "calibration": calib},
            "themes": out,
            "restored": sorted(t for t, v in out.items() if v["restores"]),
            "not_restored": sorted(t for t, v in out.items() if not v["restores"])}


def render(p: dict) -> str:
    L, A = [], None
    A = L.append
    A("=" * 92)
    A("THEME RESTORATION — FIDELITY GATE")
    A(f"register {p['prereg']} @ {p['prereg_commit']}   panel as-of {p['panel_asof']}   "
      f"served {p['n_served']}")
    A("=" * 92)
    b = p["bar"]
    c = b["calibration"]
    A(f"BAR = max(floor {b['floor']:.2f}, calibrated P95 {b['calibrated_p95']:.4f}) "
      f"= {b['applied']:.4f}")
    A(f"  calibration: {c['n_pairs']} distinct panel-theme pairs, median |rho| "
      f"{c['median_abs_rho']:.4f}, strongest "
      f"{c['max_pair']['a']}~{c['max_pair']['b']} {c['max_pair']['abs_rho']:.4f}")
    A("")
    A(f"{'theme':<20} {'rho':>8} {'p':>10} {'n':>6} {'quint':>7} {'cov':>7} "
      f"{'distinct':>9}  verdict")
    A("-" * 92)
    for t, v in p["themes"].items():
        rho = f"{v['rho']:+.4f}" if v["rho"] is not None else "   n/a"
        pv = f"{v['p']:.2e}" if v["p"] is not None else "  n/a"
        q = f"{v['quintile_agreement']:.3f}" if v["quintile_agreement"] is not None else "  n/a"
        cov = v["coverage"]
        if not v["measurable"]:
            verdict = "NOT MEASURABLE"
        elif not v["fidelity_pass"]:
            verdict = "FIDELITY FAIL"
        elif not v["coverage_pass"]:
            verdict = "COVERAGE FAIL"
        else:
            verdict = "RESTORES"
        A(f"{t:<20} {rho:>8} {pv:>10} {v['n_pairs']:>6} {q:>7} "
          f"{cov['coverage']:>7.3f} {cov['distinct_values']:>9}  {verdict}")
    A("-" * 92)
    A(f"RESTORED:     {', '.join(p['restored']) or '(none)'}")
    A(f"NOT RESTORED: {', '.join(p['not_restored']) or '(none)'}")
    A("=" * 92)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fidelity"])
    ap.add_argument("--panel", default=PANEL)
    ap.add_argument("--json", default=OUT)
    a = ap.parse_args(argv)
    p = fidelity(a.panel)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(p, fh, indent=2, default=str)
    print(render(p))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
