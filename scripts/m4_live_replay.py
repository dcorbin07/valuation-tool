#!/usr/bin/env python3
"""M4 — run the live-replay harness on a real historical date.

Executes the M4 section of `PREREG_x5_m4_b23_s10acct.md`. The deliverable is the harness
(`valuation/edge/live_replay.py`) plus ONE VERIFIED REPLAY — a harness with no executed
replay is the thing this catalogue keeps finding.

Builds the panel once with `metrics_sink`, which captures the panel's OWN metrics list per
date, then scores the last date through the LIVE path and the BACKTEST path and compares
ranks. The metrics are CAPTURED, never re-derived: a second assembly of the same quantity is
audit B7's defect class, which is the very thing M4 exists to detect.

Run:  python -m scripts.m4_live_replay --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG as CFG                    # noqa: E402
from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.studies import live_replay as LR                  # noqa: E402
from valuation.edge.data_providers import WRDSProvider        # noqa: E402

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]


def _log(m):
    print(m, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--sink-cache", default="data/free_analysis/m4_metrics_sink.pkl")
    ap.add_argument("--json", default="data/free_analysis/M4_LIVE_REPLAY.json")
    args = ap.parse_args()

    out = {"item": "M4", "register": "PREREG_x5_m4_b23_s10acct.md",
           "threshold": LR.MIN_RANK_CORRELATION, "controls": {}}

    if os.path.exists(args.sink_cache):
        _log(f"[m4] loading banked metrics sink {args.sink_cache}")
        sink, panel_shape = pickle.load(open(args.sink_cache, "rb"))
    else:
        _log("[m4] building the panel ONCE with metrics_sink (captures the panel's own inputs)")

        class _C:
            wrds_data_dir = args.data_dir
        prov = WRDSProvider(_C())
        sink = {}
        panel = FP.build_fundamental_panel(
            prov, prov.universe(None), rebalance_days=63,
            lookback_years=CFG.backtest_lookback_years, horizon=63, metrics_sink=sink)
        panel_shape = list(panel.shape)
        # C-INERT: the sink must not have changed the panel. Compare against the banked one
        # that three prior registers gated bit-identical.
        try:
            ref = pickle.load(open("data/free_analysis/panel_r5r6.pkl", "rb"))
            r = FP.quantile_backtest(panel, THEMES, {c: 0.125 for c in THEMES},
                                     n_q=10, horizon=63)
            got = {k: float(r.get(k)) for k in REC if r.get(k) is not None}
            out["controls"]["C_metrics_sink_is_inert"] = {
                "ok": all(got.get(k) == v for k, v in REC.items()),
                "measured": got,
                "why": ("`metrics_sink` only copies dicts out; if the headline moved, the "
                        "capture is not inert and M4's own instrument changed the panel."),
            }
            _log(f"[C] metrics_sink inert: {out['controls']['C_metrics_sink_is_inert']['ok']}")
        except Exception as e:
            out["controls"]["C_metrics_sink_is_inert"] = {"ok": None, "error": str(e)}
        os.makedirs(os.path.dirname(args.sink_cache), exist_ok=True)
        pickle.dump((sink, panel_shape), open(args.sink_cache, "wb"))

    out["panel_shape"] = panel_shape
    out["dates_captured"] = len(sink)
    _log(f"[m4] captured {len(sink)} dates; panel {panel_shape}")

    # ---- THE REPLAY ----
    date = sorted(sink)[-1]
    _log(f"[m4] replaying {date} through the LIVE path and the BACKTEST path")
    try:
        rep = LR.replay(sink[date], date=date, raise_on_divergence=False)
    except Exception as e:
        rep = {"date": date, "ok": False, "error": f"{type(e).__name__}: {e}"}
    out["replay"] = rep
    _log(f"[m4] rank correlation {rep.get('rank_correlation')} on {rep.get('n_names')} names "
         f"-> ok={rep.get('ok')}")

    # A second replay on the EARLIEST date, so the verdict does not rest on one cross-section
    d0 = sorted(sink)[0]
    try:
        out["replay_earliest"] = LR.replay(sink[d0], date=d0, raise_on_divergence=False)
    except Exception as e:
        out["replay_earliest"] = {"date": d0, "ok": False, "error": str(e)}
    _log(f"[m4] earliest {d0}: rho {out['replay_earliest'].get('rank_correlation')}")

    out["config_at_replay"] = {
        "sector_neutral": bool(getattr(CFG, "sector_neutral", None)),
        "residual_momentum": bool(getattr(CFG, "residual_momentum", None)),
        "why_it_matters": ("the panel hard-codes residual_momentum=False while the live path "
                           "reads CONFIG; they agree today only because the defaults were "
                           "changed to match, and nothing structurally holds them together."),
    }
    out["verdict"] = ("HARNESS BUILT AND VERIFIED - live and backtest agree"
                      if (rep.get("ok") and out["replay_earliest"].get("ok"))
                      else "DIVERGENCE DETECTED")
    _log(f"[m4] {out['verdict']}")

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    _log(f"[m4] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
