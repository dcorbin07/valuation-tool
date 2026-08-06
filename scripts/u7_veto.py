#!/usr/bin/env python3
"""u7_veto.py — the equity composite as a VETO on options alerts.  [AUDIT U7]

Runs the three pre-registered cells from `HANDOFF_edge_audit.md` session 6, on the corrected
69-date panel and the corrected 187-name / 3,885-trade options book, with the identical veto
applied to the five-seed random-entry control alongside.

Coverage is reported BEFORE any verdict, per the pre-commitment: below 80% of alerts joined,
U7 is INCONCLUSIVE on coverage alone whatever the expectancy numbers say.

    python -m scripts.u7_veto --panel <panel.pkl> --state <r2_state.pkl> \
        --control <ctrl0.pkl> --control <ctrl1.pkl> ... --json U7_RESULTS.json
"""
from __future__ import annotations

import argparse
import json
import os
import pickle


def _fmt(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U7 — equity composite as an options veto.")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--state", required=True, help="options book state.pkl (the real alerts)")
    ap.add_argument("--control", action="append", default=[],
                    help="random-entry control rows pickle; pass five (R2 standing rule)")
    ap.add_argument("--json", default="U7_RESULTS.json")
    ap.add_argument("--draws", type=int, default=4000)
    args = ap.parse_args(argv)

    import pandas as pd
    from valuation.edge import options_veto as V
    from valuation.edge import options_stats as OS
    from valuation.edge.fundamental_panel import _base_weights, quantile_backtest
    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    weights = _base_weights(cols, "established")
    print(f"[U7] panel {len(panel):,} rows / {panel['date'].nunique()} dates / "
          f"{panel['ticker'].nunique()} names; composite over {len(cols)} themes", flush=True)

    with open(args.state, "rb") as f:
        real = pickle.load(f)["rows"]
    ctrl = []
    for p in args.control:
        with open(p, "rb") as f:
            ctrl.extend(pickle.load(f))
    print(f"[U7] {len(real):,} real alerts, {len(ctrl):,} control trades "
          f"from {len(args.control)} seeds", flush=True)

    out = {"item": "U7", "n_control_seeds": len(args.control),
           "panel": {"rows": int(len(panel)), "dates": int(panel["date"].nunique()),
                     "names": int(panel["ticker"].nunique()), "themes": cols},
           "book": {"n_real": len(real), "n_control": len(ctrl)}}

    # ---- the composite's own monotonicity on THIS panel. U7's rationale in the audit cites
    # -0.95, which is the pre-B6 figure; the corrected value is what the argument actually
    # rests on and it is measured here rather than quoted.
    qb = quantile_backtest(panel, cols, weights, n_q=10, horizon=63)
    out["panel"]["monotonicity"] = qb.get("monotonicity")
    out["panel"]["top_decile_alpha"] = qb.get("top_decile_alpha")
    print(f"[U7] panel monotonicity {_fmt(qb.get('monotonicity'), '+.3f')} "
          f"(audit U7 cites -0.95), top-decile alpha {_fmt(qb.get('top_decile_alpha'))}",
          flush=True)

    # ---- the join -------------------------------------------------------------------------
    by_date = V.composite_by_date(panel, cols, weights)
    universe = {str(r.get("ticker")) for r in real}
    jr = V.join_alerts(real, by_date, universe=universe)
    jc = V.join_alerts(ctrl, by_date, universe=universe)
    out["coverage_real"], out["coverage_control"] = jr["coverage"], jc["coverage"]
    cov = jr["coverage"]["alert_coverage"]
    print(f"[U7] COVERAGE: {jr['coverage']['n_joined']:,}/{jr['coverage']['n_alerts']:,} alerts "
          f"({_fmt(cov, '.1%')}), {jr['coverage']['n_names_joined']}/"
          f"{jr['coverage']['n_names_in_alerts']} names "
          f"({_fmt(jr['coverage']['name_coverage'], '.1%')})", flush=True)
    if jr["coverage"]["names_never_joined"]:
        print(f"[U7]   names never joined: "
              f"{', '.join(jr['coverage']['names_never_joined'][:25])}", flush=True)
    out["coverage_floor_met"] = bool(cov is not None and cov >= 0.80)

    rr, cr = jr["rows"], jc["rows"]
    out["n_pct_univ_real"] = sum(1 for r in rr if r.get("u7_pct_univ") is not None)

    # ---- the audit's actual instruction: expectancy per composite decile --------------------
    out["decile_table_full_panel"] = V.decile_table(rr, "u7_pct")
    out["decile_table_within_universe"] = V.decile_table(rr, "u7_pct_univ")
    out["decile_table_control"] = V.decile_table(cr, "u7_pct")
    print("\n[U7] expectancy by composite decile (1 = BEST composite), real book:")
    for d in out["decile_table_full_panel"]:
        print(f"   D{d['decile']:<2d} n={d['n_trades']:<5d} mean={_fmt(d['mean_pnl_pct']):>8s} "
              f"win={_fmt(d['win_rate'], '.1%'):>6s}", flush=True)

    # ---- the three pre-registered cells ------------------------------------------------------
    cells = [("i_bottom_decile_full_panel", 0.10, "u7_pct"),
             ("ii_bottom_quintile_full_panel", 0.20, "u7_pct"),
             ("iii_bottom_decile_within_universe", 0.10, "u7_pct_univ")]
    out["cells"] = {}
    for name, cut, field in cells:
        rep = V.veto_report(rr, cut, field=field, control_rows=cr, draws=args.draws)
        # R2's standing rule: the paired name-year sign test carries the options verdict.
        rep["sign_test_kept_vs_control_kept"] = OS.paired_name_year(
            V.apply_veto(rr, cut, field)[0], V.apply_veto(cr, cut, field)[0])
        out["cells"][name] = rep
        inter = (rep.get("interaction") or {})
        print(f"\n[U7] {name}: retention {_fmt(rep['retention'], '.1%')}  "
              f"mean {_fmt(rep['mean_all'])} -> {_fmt(rep['mean_kept'])}  "
              f"lift {_fmt(rep['lift'])}")
        lb = rep.get("lift_boot") or {}
        if lb.get("ok"):
            print(f"        lift CI95 [{_fmt(lb['ci95'][0])}, {_fmt(lb['ci95'][1])}] "
                  f"over {lb['n_blocks']} month-blocks, excludes_zero={lb['excludes_zero']}")
        c = rep.get("control") or {}
        print(f"        control: retention {_fmt(c.get('retention'), '.1%')}  "
              f"{_fmt(c.get('mean_all'))} -> {_fmt(c.get('mean_kept'))}  "
              f"lift {_fmt(c.get('lift'))}")
        if inter.get("ok"):
            print(f"        INTERACTION (real lift - control lift) {_fmt(inter['point'])} "
                  f"CI95 [{_fmt(inter['ci95'][0])}, {_fmt(inter['ci95'][1])}] "
                  f"excludes_zero={inter['excludes_zero']}")

    os.makedirs(os.path.dirname(os.path.abspath(args.json)) or ".", exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=float)
    print(f"\n[U7] -> {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
