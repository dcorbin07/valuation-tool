"""SELL-PREMIUM-3 — `B1`-`B4` on the build quadrant. Refuses without a passing kills artifact.

Register: `PREREG_sellpremium3.md`. Every scoring primitive imported (`B7`); the settlement is
the REPAIRED one (amendment A1) with the years taken from the trades and refusals counted.
"""
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import research_log                                      # noqa: E402
from valuation.edge.statistics import hlz_hurdle                             # noqa: E402
from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402
from scripts import sellpremium2_arm as A2M                                  # noqa: E402
from scripts import sellpremium3 as S3                                       # noqa: E402
from scripts.sellpremium2_sizing_fix import grid as _grid                    # noqa: E402

PREFIX = "SELLPREMIUM3"


def settle_all(picks, label):
    """Settle every spread on the REPAIRED map. Returns the book and the refusal count."""
    years = A2M.years_spanning(picks)
    print("   spot maps over %d-%d (from the trades, not an era constant)"
          % (min(years), max(years)))
    spots = A2M.spot_maps(sorted(set(picks["ticker"])), years)
    rows, refused = [], 0
    for _i, r in picks.iterrows():
        s = SP.settlement_spot(spots.get(r["ticker"], {}), str(r["expiration"]),
                               max_stale_days=SP.MAX_SETTLEMENT_STALE_DAYS)
        if s is None:
            refused += 1
            continue
        got = S3.settle_spread({"strike": r["strike"], "bid": r["bid"]},
                               {"strike": r["long_strike"], "ask": r["long_ask"]}, s)
        rows.append({"ticker": r["ticker"], "date": r["date"], "year": r["year"],
                     "expiration": str(r["expiration"]), "strike": r["strike"],
                     "long_strike": r["long_strike"], "width": r["width"],
                     "width_frac": r["width_frac"], "dte": r["dte"], "spot": r["spot"],
                     "spot_at_expiry": s, "secured": got["capital_draft"],
                     "secured_broker": got["capital_broker"],
                     "ret_pct": got["ret_pct"], "ret_pct_broker": got["ret_pct_broker"],
                     "pnl_dollars": got["pnl_dollars"], "band": got["band"],
                     "credit": got["credit"]})
    print("   %s: settled %d of %d; %d REFUSED for want of a settlement price"
          % (label, len(rows), len(picks), refused))
    return pd.DataFrame(rows), refused


def main():
    S3.require_kills()
    n_opt = research_log.trial_count(domain="options")
    crit = hlz_hurdle(n_opt)                       # DERIVED at run time (amendment A2)
    print("SELL-PREMIUM-3 ARMS   options N %d  hurdle %.7f (UNCALIBRATED)\n" % (n_opt, crit))

    picks = pd.read_pickle(D.out_path("%s_PICKS.pkl" % PREFIX))
    bk, refused = settle_all(picks, "B1")

    # ---------------------------------------------------------------- B1, clause (a)
    dates = sorted(set(bk["date"]))
    boundary = dates[len(dates) // 2]
    early, late = bk[bk["date"] < boundary], bk[bk["date"] > boundary]
    b1 = {"full": A2M.score(bk["ret_pct"], bk["date"], bk["ticker"], crit, "B1 full"),
          "early": A2M.score(early["ret_pct"], early["date"], early["ticker"], crit, "early"),
          "late": A2M.score(late["ret_pct"], late["date"], late["ticker"], crit, "late"),
          "boundary": boundary, "boundary_embargoed": True,
          "n": int(len(bk)), "settlement_refusals": int(refused),
          "band_mix": {k: int(v) for k, v in bk["band"].value_counts().items()},
          "mean_pct_broker_denominator": float(bk["ret_pct_broker"].mean()),
          "clause_a_pass": bool(early["ret_pct"].mean() > 0 and late["ret_pct"].mean() > 0)}
    print("B1  full %+.4f%% (t_d %+.3f)  early %+.4f%%  late %+.4f%%  -> clause (a) %s"
          % (b1["full"]["mean_pct"], b1["full"]["date_clustered"]["t"],
             b1["early"]["mean_pct"], b1["late"]["mean_pct"],
             "CLEARS" if b1["clause_a_pass"] else "FAILS"))
    print("    n %d  bands %s  refusals %d" % (len(bk), b1["band_mix"], refused))
    print("    on Fidelity's denominator (A4): %+.4f%%"
          % b1["mean_pct_broker_denominator"])

    # ---------------------------------------------------------------- B2, clause (b)
    print("\nB2 - the SPREAD twin on random days, 5 seeds ...")
    need = bk.groupby(["ticker", "year"]).size().to_dict()
    per_seed, ctrl_rows = [], []
    t0 = time.time()
    for seed in list(SP.SEEDS)[:5]:
        rng = np.random.default_rng(1000 + seed)
        got = []
        for (t, y), n in need.items():
            if not SP.has_chain(t, int(y)):
                continue
            raw = SP.read_raw_chain(t, int(y))
            if raw is None:
                continue
            byd = SP.index_by_date(raw)
            spot = SP.spot_by_date(t, int(y))
            grk = SP.greeks_by_key(t, int(y))
            days = sorted(spot)
            if len(days) < n:
                continue
            smap = {}
            for yy in range(int(y), int(y) + 2):
                smap.update(SP.spot_by_date(t, yy))
            for d in rng.choice(days, size=n, replace=False):
                d = str(d)
                f = SP.put_funnel(None, spot, d, mon_band=None, day=byd.get(d))
                if f.get("cands") is None:
                    continue
                pk = SP.pick_put_by_delta(f["cands"], grk, d)["pick"]
                if not pk:
                    continue
                day = byd.get(d)
                puts = day[day["right"].astype(str).str.upper().str[0] == "P"]
                lg = S3.long_leg(puts, pk["expiration"], pk["strike"], pk["spot"])
                if lg is None:
                    continue
                s = SP.settlement_spot(smap, str(pk["expiration"]),
                                       max_stale_days=SP.MAX_SETTLEMENT_STALE_DAYS)
                if s is None:
                    continue
                r = S3.settle_spread(pk, lg, s)
                got.append({"ticker": t, "year": y, "date": d, "ret_pct": r["ret_pct"],
                            "pnl_dollars": r["pnl_dollars"], "seed": seed})
        c = pd.DataFrame(got)
        ctrl_rows.append(c)
        per_seed.append({"seed": seed, "n": int(len(c)),
                         "mean_pct": float(c["ret_pct"].mean()) if len(c) else float("nan"),
                         "mean_dollars": float(c["pnl_dollars"].mean()) if len(c)
                         else float("nan")})
        print("    seed %d: %d twin spreads, %+.4f%%  ($%+.2f)  (%.0fs)"
              % (seed, len(c), per_seed[-1]["mean_pct"], per_seed[-1]["mean_dollars"],
                 time.time() - t0))
    ctrl = pd.concat(ctrl_rows, ignore_index=True) if ctrl_rows else pd.DataFrame()

    # THE PAIRED STATISTIC IS ON DOLLARS (register §4), because spread capital varies with the
    # credit so a mean of return-on-capital silently weights the cheapest spreads most.
    arm_cell = bk.groupby(["ticker", "year"])["pnl_dollars"].mean()
    ctl_cell = (ctrl.groupby(["ticker", "year"])["pnl_dollars"].mean() if len(ctrl)
                else pd.Series(dtype=float))
    common = sorted(set(arm_cell.index) & set(ctl_cell.index))
    diffs = [float(arm_cell[k] - ctl_cell[k]) for k in common]
    pos = sum(1 for d in diffs if d > 0)
    z = ((pos - len(diffs) / 2.0) / np.sqrt(len(diffs) / 4.0)) if diffs else float("nan")
    b2 = {"seeds": per_seed, "n_cells": len(diffs), "n_positive": pos, "z": float(z),
          "arm_mean_dollars": float(bk["pnl_dollars"].mean()),
          "control_mean_dollars": float(ctrl["pnl_dollars"].mean()) if len(ctrl) else None,
          "arm_mean_pct": float(bk["ret_pct"].mean()),
          "control_mean_pct": float(ctrl["ret_pct"].mean()) if len(ctrl) else None,
          "capital_dispersion_per_cell": float(
              bk.groupby(["ticker", "year"])["secured"].std().median()),
          "clause_b_pass": bool(len(diffs) > 0 and z > 0 and pos > len(diffs) / 2.0)}
    print("  B2 arm $%+.2f vs twin $%+.2f ; %d cells, %d positive, z %+.4f -> %s"
          % (b2["arm_mean_dollars"], b2["control_mean_dollars"] or float("nan"),
             b2["n_cells"], b2["n_positive"], b2["z"],
             "CLEARS" if b2["clause_b_pass"] else "FAILS"))
    print("     pooled on return-on-capital beside it (void 8): arm %+.4f%% vs twin %+.4f%%"
          % (b2["arm_mean_pct"], b2["control_mean_pct"] or float("nan")))

    # ---------------------------------------------------------------- B3, spread vs naked
    naked = pd.read_pickle(D.out_path("SELLPREMIUM2_BOOK.pkl"))
    nk = naked.set_index(["ticker", "date", "expiration"])["ret_pct"]
    sp = bk.set_index(["ticker", "date", "expiration"])["ret_pct"]
    shared = sorted(set(nk.index) & set(sp.index))
    d3 = np.array([float(sp[k] - nk[k]) for k in shared], dtype=float)
    se3 = float(np.std(d3, ddof=1) / np.sqrt(len(d3))) if len(d3) > 1 else float("nan")
    t3 = float(np.mean(d3) / se3) if se3 and np.isfinite(se3) and se3 > 0 else float("nan")
    b3 = {"n_identical_events": int(len(d3)), "mean_diff_pct": float(np.mean(d3)),
          "se": se3, "t": t3, "mde80": float((crit + 0.84) * se3) if np.isfinite(se3) else None,
          "spread_mean_pct": float(sp[shared].mean()) if shared else None,
          "naked_mean_pct": float(nk[shared].mean()) if shared else None,
          "pass": bool(np.isfinite(t3) and np.mean(d3) > 0)}
    print("\nB3  on %d identical events: spread %+.4f%% vs naked %+.4f%% -> paired %+.4f%% "
          "(t %+.3f, MDE80 %.4f) -> %s"
          % (b3["n_identical_events"], b3["spread_mean_pct"] or float("nan"),
             b3["naked_mean_pct"] or float("nan"), b3["mean_diff_pct"], b3["t"],
             b3["mde80"] or float("nan"), "spread better" if b3["pass"] else "naked better"))

    # ---------------------------------------------------------------- B4, SENSITIVITY ONLY
    qs = bk["width_frac"].quantile([0.0, 0.25, 0.5, 0.75, 1.0]).to_dict()
    b4 = {"NO_VERDICT": "a width sweep is a grid; the declared rule is 7.5% (void 1)",
          "width_frac_quantiles": {str(k): float(v) for k, v in qs.items()},
          "by_width_bucket": {}}
    bb = pd.qcut(bk["width_frac"], 4, duplicates="drop")
    for g, s in bk.groupby(bb, observed=True):
        b4["by_width_bucket"][str(g)] = {"n": int(len(s)),
                                         "mean_pct": float(s["ret_pct"].mean())}
    print("\nB4 (sensitivity, NO verdict): %s"
          % json.dumps({k: round(v["mean_pct"], 3)
                        for k, v in b4["by_width_bucket"].items()}))

    # ---------------------------------------------------------------- the account table
    print("\naccount table - ONLY the 35%% cap rows are offered configurations (void 9)")
    acct = {}
    for eq in S3.ACCOUNT_SIZES:
        for cap_label, cap in (("35pc_cap", int(max(1, round(eq * S3.DEPLOY_CAP
                                                            / max(1.0, bk["secured"].median()))))),
                               ("o11_cap10", 10), ("o11_cap50", 50)):
            c = _grid(bk, eq, cap)
            acct["$%d/%s" % (int(eq), cap_label)] = dict(c, concurrent_cap=cap,
                                                         offered=bool(cap_label == "35pc_cap"))
            print("  $%-7d %-10s cap %3d  taken %4d -> $%9.0f  %s%s"
                  % (eq, cap_label, cap, c["taken"], c["terminal_equity"],
                     "survives" if c["survives"] else "DOES NOT SURVIVE",
                     "" if cap_label == "35pc_cap" else "   [NOT OFFERED]"))

    verdict = {"clause_a_B1": b1["clause_a_pass"], "clause_b_B2": b2["clause_b_pass"],
               "B3_spread_beats_naked": b3["pass"]}
    passes = bool(b1["clause_a_pass"] and b2["clause_b_pass"])
    label = ("CLEARS stage 1 - ELIGIBLE-BUT-UNRESOLVED" if passes
             else "NOT CONFIRMED on the build quadrant")
    art = {"item": "SELL-PREMIUM-3 stage 1 arms", "register": "PREREG_sellpremium3.md",
           "options_N": n_opt, "hlz_hurdle": crit, "critical_values": "ALL UNCALIBRATED",
           "B1_clause_a": b1, "B2_clause_b": b2, "B3_vs_naked": b3, "B4_sensitivity": b4,
           "account_table": acct, "verdict_checks": verdict, "passes": passes,
           "label": label}
    with io.open(D.out_path("%s_ARM.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    bk.to_pickle(D.out_path("%s_BOOK.pkl" % PREFIX))
    print("\n" + "=" * 90)
    print("STAGE 1 VERDICT: %s" % label)
    for k, v in sorted(verdict.items()):
        print("   %-28s %s" % (k, "PASS" if v else "FAILS"))
    print("wrote %s" % D.out_path("%s_ARM.json" % PREFIX))
    return 0


if __name__ == "__main__":
    sys.exit(main())
