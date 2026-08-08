#!/usr/bin/env python3
"""selection_rule_crosscountry.py — is a STABILITY selection rule better than the incumbent
argmax?  [SELRULE, on X8's data]

Session 8 proved this question is not answerable on the Sharadar panel: one panel is one draw,
and a paired sign test at n = 1 has a minimum achievable p of 0.50. It is answerable on X8's
Global Factor Data, which supplies 16 held-out countries instead of 1.

Pre-registered in PREREG_session9_selection_rule.md and HANDOFF_edge_audit.md SESSION 8 §2,
both committed before this script produced a number.

THE ORDER IS THE PROTOCOL AND IS ENFORCED HERE:
  STEP 1  calibrate the bar   -- measure country co-movement, re-derive the critical count.
                                 Uses ALL ten arm-pairs symmetrically, so it carries no
                                 selection information and inspects no country's sign.
  STEP 2  select on `usa`     -- Rule A (argmax) and Rule B (stability). Decide set only.
  STEP 3  unblind and count   -- the 16 measure countries, against the bar fixed in STEP 1.

LICENCE: the JKP data is CC BY-NC 4.0, RESEARCH ONLY. It validates the model and can never ship
in the product.

    python -m scripts.selection_rule_crosscountry --cache <dir> --json <out.json>
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.jkp_replication import EUROPE, MATCHED_END, MATCHED_START, THEME_MAP, load_themes, \
    composite_series
from valuation.edge.cross_country import country_design_effect, exact_binomial_tail, \
    sign_test_critical, sign_test_p

DECIDE = "usa"
MEASURE = EUROPE + ["jpn"]          # 16 held-out countries, none touched during selection
ARMS = sorted(THEME_MAP.values())   # value, quality, momentum, size, investment
ALPHA = 0.05
FLOOR_K = 12                        # the independent-countries bar; calibration may only raise it
MONTHS = 12.0
PCT = 100.0      # JKP `ret` is a decimal fraction, not a percent. Annualised = *12*100.


def arm_deltas(wide):
    """{arm: {date: Δ}} where Δ = mean of the 4 remaining themes − mean of all 5."""
    have = [c for c in ARMS if c in wide.columns]
    full = wide[have].mean(axis=1)
    out = {}
    for a in have:
        rest = [c for c in have if c != a]
        d = wide[rest].mean(axis=1) - full
        out[a] = {k: float(v) for k, v in d.dropna().items()}
    return out


def mean_of(d, keys=None):
    v = [d[k] for k in (keys if keys is not None else d)] if d else []
    return (sum(v) / len(v)) if v else float("nan")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="data/factors/research_only/jkp")
    ap.add_argument("--json", default="data/free_analysis/SELRULE_CROSSCOUNTRY.json")
    ap.add_argument("--null-draws", type=int, default=400)
    ap.add_argument("--sim-draws", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    print("SELRULE — the selection rule on X8's cross-country data")
    print(f"  decide: {DECIDE}    measure: {len(MEASURE)} held-out countries")
    print(f"  arms:   {ARMS}")
    print("  JKP data is CC BY-NC 4.0 RESEARCH ONLY\n")

    deltas, months = {}, {}
    for c in [DECIDE] + MEASURE:
        _, wide = composite_series(load_themes(c, args.cache), MATCHED_START, MATCHED_END)
        deltas[c] = arm_deltas(wide)
        months[c] = len(wide)
        missing = [a for a in ARMS if a not in deltas[c]]
        if missing:
            print(f"  FATAL: {c} is missing {missing}")
            return 2
    print(f"  loaded {len(deltas)} regions, "
          f"{min(months.values())}–{max(months.values())} months each\n")

    out = {"item": "SELRULE", "prereg": "PREREG_session9_selection_rule.md",
           "licence": "CC BY-NC 4.0 — research only, never shipped",
           "decide": DECIDE, "measure": MEASURE, "arms": ARMS,
           "window": [MATCHED_START, MATCHED_END], "months": months}

    # ---------------------------------------------------------------- STEP 1: calibrate
    print("STEP 1 — calibrate the bar (no selection, no country sign inspected)")
    pairs, rhos = [], []
    for a, b in itertools.combinations(ARMS, 2):
        panel = {c: {d: deltas[c][a][d] - deltas[c][b][d]
                     for d in deltas[c][a] if d in deltas[c][b]} for c in MEASURE}
        r = country_design_effect(panel, null_draws=args.null_draws, seed=args.seed)
        pairs.append({"pair": [a, b], "rho": r.get("rho"),
                      "mean_pairwise_corr": r.get("mean_pairwise_corr"),
                      "design_effect": r.get("design_effect"),
                      "null_p95": r.get("design_effect_null_p95"),
                      "clustering_measurable": r.get("clustering_measurable"),
                      "n_eff_countries": r.get("n_eff_countries")})
        rhos.append(r.get("rho") or 0.0)
        print(f"  {a:12s} vs {b:12s}  rho {r['rho']:.4f}  deff {r['design_effect']:.3f} "
              f"(null p95 {r['design_effect_null_p95']:.3f})  "
              f"measurable {r['clustering_measurable']}  n_eff {r['n_eff_countries']:.2f}")

    rho_max, rho_med = max(rhos), sorted(rhos)[len(rhos) // 2]
    cal = sign_test_critical(len(MEASURE), rho_max, alpha=ALPHA,
                             draws=args.sim_draws, seed=args.seed)
    crit = max(FLOOR_K, cal["critical_k"])
    any_measurable = any(p["clustering_measurable"] for p in pairs)
    print(f"\n  rho: max {rho_max:.4f}, median {rho_med:.4f}  (calibration uses the MAX, "
          f"pre-committed)")
    print(f"  clustering measurable on {sum(1 for p in pairs if p['clustering_measurable'])}"
          f"/{len(pairs)} pairs")
    print(f"  simulated critical k at rho={rho_max:.4f}: {cal['critical_k']} "
          f"(achieved alpha {cal['achieved_alpha']:.4f})")
    print(f"  independent-countries floor: {FLOOR_K} (exact alpha "
          f"{exact_binomial_tail(FLOOR_K, len(MEASURE)):.4f})")
    # THE ANSWERABILITY CHECK. If even a unanimous 16/16 does not reach alpha, no outcome of
    # this experiment is quotable and the design is dead on arrival -- the same class of finding
    # as session 8's n=1 sign test, but measured rather than derived.
    best_p = cal["tail"][len(MEASURE)]
    reachable = crit <= len(MEASURE)
    print(f"  ==> BAR FIXED AT k >= {crit} of {len(MEASURE)}")
    print(f"  best possible outcome ({len(MEASURE)}/{len(MEASURE)}) has calibrated "
          f"p = {best_p:.4f}")
    if not reachable:
        print(f"  *** UNREACHABLE: no count out of {len(MEASURE)} attains alpha "
              f"{ALPHA}. The design cannot return a positive verdict. ***")
    print()
    out["answerability"] = {"critical_k": crit, "n": len(MEASURE),
                            "reachable": bool(reachable),
                            "p_at_unanimous": best_p, "alpha": ALPHA,
                            "n_eff_countries_range":
                                [min(p["n_eff_countries"] for p in pairs),
                                 max(p["n_eff_countries"] for p in pairs)]}
    out["calibration"] = {"pairs": pairs, "rho_max": rho_max, "rho_median": rho_med,
                          "any_clustering_measurable": any_measurable,
                          "simulated_critical_k": cal["critical_k"],
                          "achieved_alpha": cal["achieved_alpha"],
                          "floor_k": FLOOR_K, "critical_k": crit,
                          "exact_binomial_alpha_at_floor":
                              exact_binomial_tail(FLOOR_K, len(MEASURE)),
                          "rule": "max rho over all 10 arm-pairs; the bar may only move up"}

    # ---------------------------------------------------------------- STEP 2: select on usa
    print(f"STEP 2 — select on {DECIDE} only")
    dd = deltas[DECIDE]
    dates = sorted(dd[ARMS[0]])
    cut = len(dates) // 2
    early, late = dates[:cut], dates[cut:]
    sel = {}
    for a in ARMS:
        e = mean_of(dd[a], early) * MONTHS * PCT
        l = mean_of(dd[a], late) * MONTHS * PCT
        sel[a] = {"early": e, "late": l, "mean": (e + l) / 2,
                  "same_sign": (e > 0) == (l > 0)}
        print(f"  {a:12s} early {e:+.3f}%/yr  late {l:+.3f}%/yr  mean {(e + l) / 2:+.3f}  "
              f"same-sign {'YES' if sel[a]['same_sign'] else 'no'}")

    arm_a = max(ARMS, key=lambda a: sel[a]["mean"])
    stable = [a for a in ARMS if sel[a]["same_sign"]]
    arm_b = max(stable, key=lambda a: sel[a]["mean"]) if stable else None
    print(f"\n  Rule A (argmax):    {arm_a}")
    print(f"  Rule B (stability): {arm_b if arm_b else 'ABSTAINS — no arm is same-sign'}")
    out["selection"] = {"halves": {"early": [early[0].strftime("%Y-%m-%d"),
                                             early[-1].strftime("%Y-%m-%d")],
                                   "late": [late[0].strftime("%Y-%m-%d"),
                                            late[-1].strftime("%Y-%m-%d")]},
                        "arms": {a: {k: v for k, v in sel[a].items()} for a in ARMS},
                        "rule_a": arm_a, "rule_b": arm_b,
                        "stable_arms": stable}

    if arm_b is None:
        print("\n  VERDICT: RULE B ABSTAINS — pre-registered outcome, not a failure.")
        out["verdict"] = "RULE_B_ABSTAINS"
    elif arm_b == arm_a:
        print(f"\n  VERDICT: NO CONTRAST — both rules select `{arm_a}`. Pre-registered "
              "outcome; every paired difference is identically zero and the sign test is "
              "vacuous. This is NOT a null and NOT a tie.")
        out["verdict"] = "NO_CONTRAST"
    else:
        out["verdict"] = None

    # ---------------------------------------------------------------- STEP 3: unblind
    if out["verdict"] is None:
        print(f"\nSTEP 3 — unblind the {len(MEASURE)} measure countries "
              f"(B=`{arm_b}` minus A=`{arm_a}`)")
        per, favour = {}, 0
        for c in MEASURE:
            d = (mean_of(deltas[c][arm_b]) - mean_of(deltas[c][arm_a])) * MONTHS * PCT
            per[c] = d
            if d > 0:
                favour += 1
            print(f"  {c:4s}  {d:+.3f}%/yr  {'B' if d > 0 else 'A'}")
        p_ind = exact_binomial_tail(favour, len(MEASURE))
        p_cal = sign_test_p(favour, len(MEASURE), rho_max,
                            draws=args.sim_draws, seed=args.seed)
        passed = favour >= crit
        print(f"\n  {favour}/{len(MEASURE)} countries favour Rule B  (bar: >= {crit})")
        print(f"  p (independent countries) {p_ind:.4f}   "
              f"p (calibrated, rho={rho_max:.4f}) {p_cal:.4f}")
        print(f"\n  VERDICT: {'RULE B IS BETTER' if passed else 'NULL'}")
        if not passed:
            print("  A NULL here means NOT SUBSTANTIALLY BETTER. Power is 8.5% against a rule "
                  "better in 55% of countries — it does NOT mean the rules are equivalent.")
        out["verdict"] = "RULE_B_BETTER" if passed else "NULL"
        out["measurement"] = {"per_country_pct_per_yr": per, "favour_b": favour,
                              "n": len(MEASURE), "critical_k": crit,
                              "p_independent": p_ind, "p_calibrated": p_cal,
                              "arm_b": arm_b, "arm_a": arm_a}

    os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
