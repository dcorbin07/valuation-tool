"""Run the trade autopsy (#23) and write AUTOPSY_RESULTS.json.

    python optautopsy_run.py --data-root data

The data root is a parameter because the licensed panels live only in the primary checkout;
a git worktree has no `data/`.
"""
from __future__ import annotations

import argparse
import json

from valuation.edge import options_autopsy as A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--min-coverage", type=float, default=0.50)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    res = A.run(data_root=a.data_root, seed=a.seed, min_coverage=a.min_coverage,
                verbose=not a.quiet)
    path = A.save(res, a.data_root)

    o = res["overall"]
    print("\n================ TRADE AUTOPSY ================")
    print(f"trades {res['n_trades']}  (contract greeks on {res['n_with_contract']}, "
          f"surface on {res['n_with_daily']})")
    print(f"expectancy {o['expectancy']:+.4f}  hit {o['hit_rate']:.3f}  "
          f"P(>=+100%) {o['p_tail']:.3f}  P(stop) {o['p_stop']:.3f}  "
          f"P(total loss) {o['p_total_loss']:.4f}")
    print(f"features tested {res['n_features_tested']}  hypotheses {res['n_hypotheses']}")
    print(f"SURVIVORS (both split directions): {res['survivors'] or 'NONE'}")
    print()
    print("loss buckets:")
    for k, v in res["loss_autopsy"]["buckets"].items():
        print(f"  {k:<24} n={v['n']:<5} exp {v['expectancy']:+.3f}")
    print()
    print("top held-out results by forward gain:")
    rs = sorted(res["results"],
                key=lambda r: -(r["fit_early_test_late"].get("gain") or -9))
    print(f"  {'feature':<26}{'cov':>6}{'dir':>5}{'gain(L)':>9}{'keep':>7}"
          f"{'tailR':>7}{'p':>7}  {'gain(E)':>9}{'both':>6}")
    for r in rs[:20]:
        a1, a2 = r["fit_early_test_late"], r["fit_late_test_early"]
        def g(d, k, fmt="{:+.3f}"):
            v = d.get(k)
            return fmt.format(v) if isinstance(v, (int, float)) else "  -  "
        print(f"  {r['feature']:<26}{r['coverage']:>6.2f}"
              f"{(a1.get('direction') or 0):>5}"
              f"{g(a1,'gain'):>9}{g(a1,'retention','{:.2f}'):>7}"
              f"{g(a1,'tail_ratio','{:.2f}'):>7}{g(a1,'perm_p','{:.3f}'):>7}  "
              f"{g(a2,'gain'):>9}{str(r['passes_both_directions']):>6}")
    print()
    print(f"written: {path}")
    if res["survivors"]:
        print("\nstacked on term_slope:")
        print(json.dumps({k: (v.get("passes_both_directions") if isinstance(v, dict) else v)
                          for k, v in res["stacked_on_term_slope"].items()}, indent=1))


if __name__ == "__main__":
    main()
