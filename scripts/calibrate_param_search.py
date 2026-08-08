"""
Calibrate the parameter search's own gates — i.e. test the tests.

Run the FULL protocol repeatedly on synthetic panels that contain NO signal whatsoever. Every
"edge" it reports is therefore false by construction, so this measures directly:

  * the NOISE FLOOR of the search - how good the winning config looks when nothing is there;
  * the FALSE-POSITIVE RATE of each gate - how often it certifies pure noise.

This is how we learned not to gate on the Hansen SPA p-value: it fires on ~35% of signal-free
panels, because its null compares against a single realisation of the baseline, and when that
realisation is unlucky essentially the whole config family beats it. (Hand the same test a
demeaned differential matrix, where its null is true by construction, and it returns p ~ 1.0 --
so the implementation is sound; the question it answers is just not the one we need.)

Re-run this whenever you change the search space, the objective, the selection rule or a gate.
A gate whose false-positive rate you have not measured is not a gate.

    python scripts/calibrate_param_search.py [n_runs] [n_permutations]

`n_permutations > 0` also calibrates the permutation gate itself, which is much slower (each run
re-runs the whole search n_permutations extra times). Use 0 for a quick structural check.
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from valuation.edge import param_search as PS
from valuation.screener import settings as S

THEMES = S.BUCKET_FACTORS["established"]

# Deliberately smaller than the production space so a calibration sweep is affordable; the
# structure (categorical scheme axis, open-ended numeric axes) is the same.
AXES = {
    "scheme": {"values": ["current-default", "equal-weight", "ic-shrunk-50", "ic-ir",
                          "max-ir-decorr"], "ordered": False},
    "top_n": {"values": [10, 15, 25, 40], "ordered": True, "open_left": True, "open_right": True},
    "exit_band": {"values": [1.5, 2.0, 3.0], "ordered": True, "open_left": True, "open_right": True},
    "min_hold": {"values": [1, 2, 3], "ordered": True, "open_left": False, "open_right": True},
    "cap_tier": {"values": ["all", "top33", "top10"], "ordered": True,
                 "open_left": False, "open_right": True},
}


def signal_free_panel(n_dates=48, n_names=250, seed=1, persist=0.7):
    """Themes persist through time the way real factors do, market and idiosyncratic returns are
    realistic in scale — and forward returns are related to NOTHING. Any edge found is false."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2008-01-02", periods=n_dates, freq="63B").strftime("%Y-%m-%d").tolist()
    caps = np.exp(rng.normal(20, 1.5, n_names))
    prev = {t: rng.normal(0, 1, n_names) for t in THEMES}
    rows = []
    for d in dates:
        f = {t: persist * prev[t] + np.sqrt(max(1e-9, 1 - persist ** 2)) * rng.normal(0, 1, n_names)
             for t in THEMES}
        prev = f
        mkt = rng.normal(0.02, 0.08)
        fwd = mkt + rng.normal(0, 0.18, n_names)
        for i in range(n_names):
            r = {"date": d, "ticker": f"T{i:03d}", "fwd_ret": float(fwd[i]),
                 "bench_ret": float(mkt), "market_cap": float(caps[i])}
            r.update({t: float(f[t][i]) for t in THEMES})
            rows.append(r)
    return pd.DataFrame(rows)


def main(n_runs=20, n_perm=0):
    base = PS.FP._base_weights(THEMES, "established")
    ann = 252.0 / 63
    gate_hits, spa, gross, adopted = {}, [], [], 0
    print(f"\nCalibrating on {n_runs} SIGNAL-FREE panels "
          f"({len(PS.build_space(AXES))} configs each, {n_perm} permutations)\n")
    for k in range(n_runs):
        t0 = time.time()
        r = PS.honest_search(signal_free_panel(seed=500 + k), THEMES, base, axes=AXES,
                             n_perm=n_perm, n_boot=1000, seed=7)
        if r.get("status"):
            print(f"  run {k + 1:>2}: {r['status']}")
            continue
        for g, v in r["gates"].items():
            gate_hits[g] = gate_hits.get(g, 0) + int(bool(v))
        spa.append(r["reality_check"].get("spa_pvalue"))
        gross.append(r["edge_decomposition"]["gross_edge_ann"])
        adopted += int(bool(r["adopt"]))
        print(f"  run {k + 1:>2}: apparent edge {gross[-1]:+.2%}/yr  SPA p={spa[-1]:.3f}  "
              f"PBO={r['pbo']:.2f}  adopt={r['adopt']}  ({time.time() - t0:.0f}s)", flush=True)

    n = len(gross)
    if not n:
        return 1
    print(f"\n  NOISE FLOOR of the search (apparent gross edge of the winner, on no signal):")
    print(f"    mean {np.mean(gross):+.2%}/yr   p95 {np.percentile(gross, 95):+.2%}/yr   "
          f"max {np.max(gross):+.2%}/yr")
    print(f"    -> a real result must clear this, not zero.")
    print(f"\n  FALSE-POSITIVE RATE per gate (want ~5% or less; these are all pure noise):")
    for g, hits in sorted(gate_hits.items(), key=lambda kv: -kv[1]):
        print(f"    {hits / n:>5.0%}  {g}")
    s = np.array([x for x in spa if x is not None], float)
    if len(s):
        print(f"    {np.mean(s < 0.05):>5.0%}  hansen_spa_p_lt_0.05  [diagnostic, NOT a gate]")
    print("\n  Individually, several gates are near-useless — a 100% false-positive rate here means")
    print("  that gate alone certifies pure noise every time. Only the CONJUNCTION is a filter,")
    print("  which is exactly why adoption requires all of them rather than a headline p-value.")
    print(f"\n  ADOPTED (all gates passed on pure noise): {adopted}/{n} — must be 0.")
    if not n_perm:
        print("  NOTE: with 0 permutations the permutation gate always fails, so this 0 is")
        print("        guaranteed and proves nothing. Re-run with >=20 permutations to actually")
        print("        calibrate the full gate.")
    return 0 if adopted == 0 else 1


if __name__ == "__main__":
    a = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    b = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    raise SystemExit(main(a, b))
