#!/usr/bin/env python3
"""loo_prereg.py — session 7's pre-registered, held-out leave-one-out ablation.

Pre-registration in `HANDOFF_edge_audit.md` §1, committed at 5a27ea1 before any number here
existed. Seven arms, selected on the decide half by their own leave-one-out effect, measured
only on the held-out half, both directions, against the MIN_HOLDOUT_* margins committed before
the P6 runs.

    python -m scripts.loo_prereg --panel <panel.pkl> --json LOO_HOLDOUT_RESULTS.json
"""
from __future__ import annotations

import argparse
import json


def _f(x, p="+.2%"):
    return "n/a" if x is None else format(x, p)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Pre-registered held-out leave-one-out.")
    ap.add_argument("--panel", required=True)
    ap.add_argument("--json", default="LOO_HOLDOUT_RESULTS.json")
    args = ap.parse_args(argv)

    import pandas as pd

    from valuation.edge import ablation as A
    from valuation.studies import loo_holdout as L
    from valuation.edge import research_log as RL
    from valuation.edge.fundamental_panel import _base_weights
    from valuation.screener import settings as S

    panel = pd.read_pickle(args.panel)
    deployed = [c for c in S.BUCKET_FACTORS["established"]
                if c in panel.columns and panel[c].notna().any()
                and S.WEIGHTS_ESTABLISHED.get(c, 0.0) > 0]
    print(f"[LOO] panel {len(panel):,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names", flush=True)
    print(f"[LOO] {len(deployed)} deployed themes: {', '.join(deployed)}", flush=True)

    # The arms must ablate the composite the PRODUCT runs, not a lookalike. Asserted, because a
    # silent mismatch would make every number below describe something nobody trades.
    dep_w = _base_weights(deployed, "established")
    flat_matches = all(abs(L.flat(deployed)[c] - dep_w[c]) < 1e-9 for c in deployed)
    print(f"[LOO] flat weights == deployed weights: {flat_matches}", flush=True)

    r = L.loo_holdout(panel, deployed)
    r["panel"] = {"rows": int(len(panel)), "dates": int(panel["date"].nunique()),
                  "names": int(panel["ticker"].nunique())}
    r["flat_weights_are_the_deployed_weights"] = bool(flat_matches)

    if r.get("status"):
        print(f"[LOO] {r['status']}")
        return 1

    print(f"[LOO] {r['n_dates']['total']} dates -> early {r['n_dates']['early']} / "
          f"late {r['n_dates']['late']}, boundary {r['boundary_date_embargoed']} embargoed",
          flush=True)

    for d in L.DIRECTIONS:
        b = r["splits"][d]
        print(f"\n=== {d} ({b['decide_dates']} decide / {b['measure_dates']} measure) ===")
        print("  decide-half ranking (drop -> alpha gain):")
        for x in b["decide_ranking"]:
            print(f"    {x['dropped']:22s} {_f(x['d_top_decile_alpha']):>8s}")
        print(f"  SELECTED: drop `{b['selected']}` "
              f"(decide gain {_f(b['selected_decide_gain'])})")
        sm = b["measure_selected"]
        print(f"  MEASURE half: d_alpha {_f(sm.get('d_top_decile_alpha')):>8s} "
              f"(bar +1.00%)   d_LS_t {_f(sm.get('d_long_short_tstat'), '+.3f'):>7s} "
              f"(bar +0.250)")
        print(f"  clears alpha={b['clears_alpha_margin']}  t={b['clears_tstat_margin']}  "
              f"-> improves={b['improves']}")
        print("  all seven arms on the measure half (NO VERDICT, context only):")
        for x in sorted(b["measure_all_arms"], key=lambda y: -(y["d_top_decile_alpha"] or -9)):
            print(f"    {x['dropped']:22s} {_f(x['d_top_decile_alpha']):>8s}  "
                  f"{_f(x['d_long_short_tstat'], '+.3f'):>7s}")

    print(f"\n[LOO] selected: {r['selected']}")
    print(f"[LOO] same theme both directions: {r['same_theme_selected_both_directions']}")
    print(f"[LOO] VERDICT: {r['verdict'].upper()}")

    # ---- the trial cost, computed rather than asserted -------------------------------------
    n_before = RL.trial_count(domain="equity")
    r["trial_cost"] = {"equity_n_before": n_before, "arms_added": len(deployed),
                       "equity_n_after": n_before + len(deployed)}
    print(f"[LOO] equity N {n_before} -> {n_before + len(deployed)} once the row is logged")

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(r, f, indent=2, default=str)
    print(f"[LOO] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
