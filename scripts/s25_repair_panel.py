#!/usr/bin/env python3
"""S25's FIRST CONSUMER — the look-ahead repair, WIRED and MEASURED.  [S25-REPAIR]

`calibration.py` passes TODAY's sector into `pit_company` for a 1998 or 2009 valuation, where
it selects `SECTOR_TARGET_MARGIN` (a 2.70x range) and `SECTOR_MULTIPLES`. This rebuilds the
valuation panel with S25's dated map wired in and reports what the repair MOVES — regime,
method and FAIR VALUE — against the incumbent scored on the same rows.

    python -m scripts.s25_repair_panel --data-dir .../data/backtest --build
    python -m scripts.s25_repair_panel --report

**ONE BUILD, THREE SCORINGS, A PROVABLY IDENTICAL ROW SET.** The base valuation and both
repair arms are computed inside one pass over the same `(date, ticker)` rows from the same
`CompanyData` inputs, differing in the sector string ALONE. Three separate builds would let
the row set drift and would confound the repair with whatever else moved.

**ADOPTS NOTHING.** `CONFIG` is untouched, the live path is untouched, and the banked panel is
not overwritten. Adopting this is a VINTAGE EVENT and Don's call.

**ZERO TRIALS** — no hypothesis, no bar, no verdict against a threshold.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT_PANEL = "panel_s25_repair.pkl"
OUT_JSON = "S25_REPAIR_VALUED.json"


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root():
    """PRIMARY data root, FOUND not assumed (`DEEPITM-FIN`: an empty worktree `data/` shadows
    the populated one and turns a real read into a silent zero)."""
    here = _repo()
    for c in (os.path.join(here, "data"),
              os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(here))), "data")):
        if os.path.exists(os.path.join(c, "free_analysis", "panel_s23_fairvalue.pkl")):
            return c
    raise SystemExit("no data root carries the banked S23 valuation panel")


def build(data_dir, limit=None, out=None):
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge import sector_map as SM
    from valuation.engine.calibration import build_valuation_panel

    class _C:
        wrds_data_dir = data_dir

    t0 = time.time()
    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready: %s" % msg)
    tickers = prov.universe(limit=limit) or []
    if not tickers:
        raise SystemExit("no tickers in the export")
    if limit:
        print("*** SMOKE TEST (%d names) - NOT a verdict ***" % len(tickers), flush=True)
    smap = SM.load()
    print("[s25] universe %d names, map %d tickers" % (len(tickers), len(smap.spans)),
          flush=True)

    panel = build_valuation_panel(prov, tickers, rebalance_days=63, lookback_years=18,
                                  horizon=63, offline=True, with_scenarios=False,
                                  sector_map=smap)
    if panel.empty:
        raise SystemExit("empty panel")
    dest = out or os.path.join(_data_root(), "free_analysis", OUT_PANEL)
    panel.to_pickle(dest)
    print("[s25] wrote %s  rows %d  dates %d  names %d  in %.0fs"
          % (dest, len(panel), panel["date"].nunique(), panel["ticker"].nunique(),
             time.time() - t0), flush=True)
    return panel


def _q(v):
    s = sorted(v)
    if not s:
        return {"n": 0}

    def pct(p):
        return round(float(s[min(len(s) - 1, int(p * len(s)))]), 6)
    return {"n": len(s), "mean": round(sum(s) / len(s), 6), "min": round(float(s[0]), 6),
            "p05": pct(0.05), "median": pct(0.50), "p95": pct(0.95),
            "max": round(float(s[-1]), 6)}


def report(panel_path=None):
    import pandas as pd
    root = _data_root()
    p = panel_path or os.path.join(root, "free_analysis", OUT_PANEL)
    df = pd.read_pickle(p)
    n = len(df)

    out = {"panel_rows": n,
           "dates": int(df["date"].nunique()),
           "names": int(df["ticker"].nunique()),
           "register": "PREREG_s25_sector_crosswalk.md",
           "adopts": "NOTHING - CONFIG untouched, live path untouched, banked panel not "
                     "overwritten. Adoption is a VINTAGE EVENT and Don's call."}

    # ---- the control that licenses every number below --------------------------------
    # The base columns must reproduce the BANKED panel, or the arms are being compared
    # against a different object than the record describes.
    banked = os.path.join(root, "free_analysis", "panel_s23_fairvalue.pkl")
    if os.path.exists(banked):
        b = pd.read_pickle(banked)
        k = ["date", "ticker"]
        m = df[k + ["fair_value", "regime", "sector"]].merge(
            b[k + ["fair_value", "regime", "sector"]], on=k, suffixes=("_new", "_old"))
        fv = m.dropna(subset=["fair_value_new", "fair_value_old"])
        dev = (fv["fair_value_new"] - fv["fair_value_old"]).abs()
        out["C1_base_reproduces_the_banked_panel"] = {
            "rows_compared": int(len(m)),
            "max_abs_fair_value_deviation": (float(dev.max()) if len(dev) else None),
            "regime_identical": int((m["regime_new"] == m["regime_old"]).sum()),
            "sector_identical": int((m["sector_new"] == m["sector_old"]).sum()),
            "note": ("GATED: a nonzero deviation means the arms are measured against a "
                     "different object than the record describes."),
        }
        if len(m) == 0:
            out["C1_base_reproduces_the_banked_panel"]["VACUOUS"] = (
                "ZERO rows compared - reported VACUOUS, never PASSING (O21-D2 C5).")

    states = df["sector_state"].fillna("ABSENT").value_counts().to_dict()
    out["lookup_states"] = {str(k): int(v) for k, v in states.items()}

    for tag, label in (("a", "repair_a_change_only_PRIMARY"),
                       ("b", "repair_b_full_CONFOUNDED")):
        sec_col, fv_col = "sector_" + tag, "fair_value_" + tag
        moved = df[df[sec_col].astype(str) != df["sector"].astype(str)]
        both = moved.dropna(subset=["fair_value", fv_col])
        both = both[both["fair_value"].astype(float).abs() > 1e-9]
        rel = ((both[fv_col].astype(float) - both["fair_value"].astype(float))
               / both["fair_value"].astype(float))
        # A PRICE-DENOMINATED MEASURE, because the relative one has a denominator that goes
        # to zero. The `financial` regime values on justified P/B from ROE and can return a
        # fair value of 0.027 on a real name; switching out of it then reads as +109x, which
        # is a property of the DENOMINATOR and not of the repair. Fair-value-over-price is
        # the ratio the product actually renders and is bounded by the price instead.
        pr = both[both["price"].astype(float) > 0]
        fvp = ((pr[fv_col].astype(float) - pr["fair_value"].astype(float))
               / pr["price"].astype(float))
        blk = {
            "rows_sector_moved": int(len(moved)),
            "share_of_panel": round(len(moved) / n, 6) if n else None,
            "rows_revalued": int(df["revalued_" + tag].fillna(False).sum()),
            "fair_value_comparable": int(len(both)),
            "fair_value_changed": int((rel.abs() > 1e-9).sum()),
            "fair_value_unchanged_though_sector_moved": int((rel.abs() <= 1e-9).sum()),
            "rel_fair_value_delta": _q(list(rel.values)),
            "rel_delta_MEAN_IS_OUTLIER_DRIVEN": (
                "The relative delta's denominator is the BASE fair value, which the "
                "`financial` regime can return near zero. Quote the MEDIAN, and quote "
                "fv_over_price_delta beside it."),
            "fv_over_price_delta": _q(list(fvp.values)),
            "rel_delta_ge_1pct": int((rel.abs() >= 0.01).sum()),
            "rel_delta_ge_10pct": int((rel.abs() >= 0.10).sum()),
            "fv_over_price_moves_ge_10pp": int((fvp.abs() >= 0.10).sum()),
            "regime_changed": int((moved["regime_" + tag].astype(str)
                                   != moved["regime"].astype(str)).sum()),
            "method_changed": int((moved["method_" + tag].astype(str)
                                   != moved["method"].astype(str)).sum()),
            # A row the repair could not value is a HOLE in the repair, counted directly
            # rather than differenced against the base's own NaNs.
            "revaluation_failed": int((moved[fv_col].isna()
                                       & moved["fair_value"].notna()).sum()),
            "top_regime_transitions": [
                {"from": str(a), "to": str(b), "n": int(c)} for (a, b), c in
                moved[moved["regime_" + tag].astype(str) != moved["regime"].astype(str)]
                .groupby(["regime", "regime_" + tag]).size()
                .sort_values(ascending=False).head(6).items()],
        }
        # The fair value is the numerator of the gap the product renders, so the DIRECTION
        # matters as much as the size: a repair that only ever raises fair value would read
        # as a systematic upgrade rather than a correction.
        blk["direction"] = {"up": int((rel > 1e-9).sum()), "down": int((rel < -1e-9).sum())}
        out[label] = blk

    out["repair_b_full_CONFOUNDED"]["note"] = (
        "CONFOUNDED BY CONSTRUCTION: fixes look-ahead AND switches taxonomy in one step. The "
        "register makes quoting this without the taxonomy disagreement beside it a VOID "
        "CONDITION.")
    try:
        mp = os.path.join(root, "free_analysis", "S25_SECTOR_MAP.json")
        with io.open(mp, encoding="utf-8") as fh:
            d = (json.load(fh).get("taxonomy_disagreement") or {})
        out["repair_b_full_CONFOUNDED"]["taxonomy_disagreement_rate"] = d.get(
            "disagreement_rate")
    except Exception:
        out["repair_b_full_CONFOUNDED"]["taxonomy_disagreement_rate"] = None

    dest = os.path.join(root, "free_analysis", OUT_JSON)
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps(out, indent=2)[:4000])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    if a.build:
        if not a.data_dir:
            raise SystemExit("--build needs --data-dir")
        build(a.data_dir, limit=a.limit, out=a.out)
    if a.report:
        report(a.out)
    if not (a.build or a.report):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
