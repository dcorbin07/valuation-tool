"""O13 — anti-signal decomposition. Runs the register, writes one artifact.

    python -m scripts.o13_decompose

Pre-registered in `PREREG_o13_antisignal.md`, committed alone at b0f287d before this file
existed. Nothing here chooses a bin, a bar or a margin — all three are fixed in that file.

Reads the SPLIT-CLEAN banked books only (U1-SPLIT, 2026-08-11). No re-mine, no new data, no
change to the exit policy.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import antisignal as A          # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
OUT = os.path.join(DATA, "free_analysis", "O13_ANTISIGNAL.json")


def load_books() -> tuple:
    with open(os.path.join(UNIV, "state_r2_splitclean.pkl"), "rb") as f:
        alert = pickle.load(f)["rows"]
    ctrl = []
    for s in range(5):
        with open(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s), "rb") as f:
            ctrl.extend(pickle.load(f))
    return alert, ctrl


def feature_specs(alert: list) -> list:
    """(name, track, binner). Fixed by the register; nothing is chosen here."""
    out = []
    for f in A.TRACK_A:
        if f in A.LIST_VALUED:
            for lab in A.label_levels(alert):
                out.append(("labels:%s" % lab, "A", A.make_label_binner(lab)))
        else:
            out.append((f, "A", A.make_binner(f, alert)))
    for f in A.TRACK_S:
        out.append((f, "S", A.make_binner(f, alert)))
    return out


def score_feature(name: str, binner, alert: list, ctrl: list, n_draws: int, seed: int) -> dict:
    """Observed gap table, S_worst, and the feature's own calibrated p95."""
    tab = A.gap_table(alert, ctrl, binner)
    obs = A.s_worst(tab)
    rate = A.rate_component(tab)
    cm = [r.get("pnl_pct") for r in ctrl if r.get("pnl_pct") is not None]
    mix = A.mix_component(tab, sum(cm) / len(cm)) if cm else None

    names_a, sizes_a, rets_a = A.bin_sizes(alert, binner)
    names_c, sizes_c, rets_c = A.bin_sizes(ctrl, binner)
    common = [b for b in names_a if b in set(names_c)]
    draws = []
    if obs is not None and common:
        idx_a = [names_a.index(b) for b in common]
        idx_c = [names_c.index(b) for b in common]
        draws = A.null_draws_fast(sizes_a, rets_a, sizes_c, rets_c, idx_a, idx_c,
                                  sum(sizes_a), n_draws, seed)
    p95 = A.percentile(draws, 95) if draws else None
    degen = A.is_degenerate(tab)
    return {
        "feature": name,
        "n_alert": tab["n_alert"], "n_ctrl": tab["n_ctrl"], "n_bins": len(tab["bins"]),
        "degenerate": degen,
        "can_express_refusal": A.can_express_refusal(tab),
        "rate_component_pp": (rate * 100.0) if rate is not None else None,
        "mix_component_pp": (mix * 100.0) if mix is not None else None,
        "s_worst": obs, "null_p95": p95, "null_draws": len(draws),
        "clears": (not degen and obs is not None and p95 is not None and obs > p95),
        "bins": {b: {"n_alert": d["n_alert"], "n_ctrl": d["n_ctrl"],
                     "mean_alert_pct": (d["mean_alert"] * 100.0)
                     if d["mean_alert"] is not None else None,
                     "mean_ctrl_pct": (d["mean_ctrl"] * 100.0)
                     if d["mean_ctrl"] is not None else None,
                     "gap_pp": (d["gap"] * 100.0) if d["gap"] is not None else None,
                     "w": d["w"]}
                 for b, d in tab["bins"].items()},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O13 — anti-signal decomposition")
    ap.add_argument("--draws", type=int, default=A.N_PERM_DRAWS)
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args(argv)

    alert, ctrl_raw = load_books()
    print("[O13] alert %d  control %d" % (len(alert), len(ctrl_raw)), flush=True)

    # Track A needs the parent alert's features on every control row.
    joinable = [f for f in A.TRACK_A if f != "labels"] + ["labels"]
    ctrl, orphans = A.attach_parent_features(ctrl_raw, alert, joinable)
    print("[O13] control joined %d, orphans dropped %d (%.2f%%)"
          % (len(ctrl), orphans, 100.0 * orphans / max(1, len(ctrl_raw))), flush=True)

    ma = sum(r["pnl_pct"] for r in alert) / len(alert)
    mc_all = sum(r["pnl_pct"] for r in ctrl_raw) / len(ctrl_raw)
    mc_join = sum(r["pnl_pct"] for r in ctrl) / len(ctrl)
    print("[O13] alert %+.4f%%  control(all) %+.4f%%  gap %+.4fpp"
          % (ma * 100, mc_all * 100, (ma - mc_all) * 100), flush=True)

    res = {
        "item": "O13",
        "register": "PREREG_o13_antisignal.md",
        "book": "split_clean (U1-SPLIT 2026-08-11)",
        "n_alert": len(alert), "n_ctrl_all": len(ctrl_raw), "n_ctrl_joined": len(ctrl),
        "n_orphans_dropped": orphans,
        "alert_mean_pct": ma * 100, "ctrl_mean_pct": mc_all * 100,
        "ctrl_joined_mean_pct": mc_join * 100,
        "total_gap_pp": (ma - mc_all) * 100,
        "n_perm_draws": args.draws,
        "iv_rank_bug": ("wired and 0.0% populated on BOTH books; excluded for having no values, "
                        "not for scoring badly"),
    }

    specs = feature_specs(alert)
    print("[O13] %d feature arms" % len(specs), flush=True)

    a_early, a_late = A.split_halves(alert)
    c_early, c_late = A.split_halves(ctrl)
    print("[O13] halves: alert %d/%d  control %d/%d"
          % (len(a_early), len(a_late), len(c_early), len(c_late)), flush=True)

    full, early, late = [], [], []
    for i, (name, track, binner) in enumerate(specs):
        f = score_feature(name, binner, alert, ctrl, args.draws, args.seed + i)
        e = score_feature(name, binner, a_early, c_early, args.draws, args.seed + 1000 + i)
        l = score_feature(name, binner, a_late, c_late, args.draws, args.seed + 2000 + i)
        f["track"] = e["track"] = l["track"] = track
        f["clears_both_halves"] = bool(e["clears"] and l["clears"])
        full.append(f)
        early.append(e)
        late.append(l)
        print("[O13]   %-34s S=%s p95=%s full=%s early=%s late=%s"
              % (name,
                 ("%.3f" % f["s_worst"]) if f["s_worst"] is not None else "  n/a",
                 ("%.3f" % f["null_p95"]) if f["null_p95"] is not None else "  n/a",
                 "Y" if f["clears"] else "n", "Y" if e["clears"] else "n",
                 "Y" if l["clears"] else "n"), flush=True)

    degen = [f["feature"] for f in full if f["degenerate"]]
    res["degenerate_features"] = degen
    res["degenerate_note"] = (
        "constant on this book, so they carry a single bin and can never clear a bar: the banked "
        "options book is 100%% calls and 100%% 'swing' horizon. Read them as 'the book contains "
        "no contrast', NOT as evidence about calls vs puts.")
    res["full_sample_EXPLORATORY"] = full
    res["early_half"] = early
    res["late_half"] = late
    cleared = [f["feature"] for f in full if f["clears_both_halves"]]
    res["features_clearing_both_halves"] = cleared
    res["q2_verdict"] = A.concentration_verdict(cleared)
    print("[O13] Q2 verdict: %s  (cleared both halves: %s)"
          % (res["q2_verdict"], cleared or "none"), flush=True)

    # ---- Q3a, the selection inverse ---------------------------------------------------------
    # The register's rule ranks bins by decide-half gap. It does not name WHICH feature, so the
    # feature is selected ON THE DECIDE HALF ONLY -- highest decide-half S_worst -- and the
    # measure half is untouched during that choice. The underspecification is disclosed rather
    # than resolved after seeing results, and the all-feature table below is EXPLORATORY.
    byname = {n: b for n, _, b in specs}
    dirs = {}
    for label, (da, dc, ma_, mc_) in {
            "early_decides": (a_early, c_early, a_late, c_late),
            "late_decides": (a_late, c_late, a_early, c_early)}.items():
        # ELIGIBILITY, on bin structure only (see the register's amendment A2): a feature that
        # cannot express a refusal under the 30% cap is excluded BEFORE any gap is consulted.
        # Without this the selection reliably lands on a 98.5%/1.5% label whose refusal set is
        # necessarily empty, which measures the statistic's own lopsidedness, not the book.
        pool = early if label == "early_decides" else late
        elig = [x for x in pool if x["s_worst"] is not None and not x["degenerate"]
                and x["can_express_refusal"]]
        scored = [(x["s_worst"], x["feature"]) for x in elig if x["clears"]]
        if not scored:
            scored = [(x["s_worst"], x["feature"]) for x in elig]
        scored.sort(reverse=True)
        pick = scored[0][1] if scored else None
        if pick is None:
            dirs[label] = None
            continue
        binner = byname[pick]
        dtab = A.gap_table(da, dc, binner)
        refused = A.refusal_set(dtab)
        out = A.apply_refusal(ma_, mc_, binner, refused)
        out["selected_feature"] = pick
        out["selected_on"] = label
        out["decide_s_worst"] = scored[0][0]
        dirs[label] = out
        print("[O13] %s -> feature %s, refuse %s, improvement %s pp"
              % (label, pick, refused,
                 ("%+.4f" % out["improvement_pp"]) if out["improvement_pp"] is not None
                 else "n/a"), flush=True)

    res["q3a_directions"] = dirs
    res["q3a_verdict"] = A.inverse_verdict(dirs.get("early_decides"), dirs.get("late_decides"))
    print("[O13] Q3a verdict: %s" % res["q3a_verdict"], flush=True)

    # ---- Q3b, the instrument inverse: arithmetic, no verdict --------------------------------
    spreads = [r.get("entry_spread_pct") for r in alert if r.get("entry_spread_pct") is not None]
    spreads.sort()
    med_spread = spreads[len(spreads) // 2] if spreads else None
    res["q3b_instrument_inverse"] = {
        "alert_absolute_mean_pct": ma * 100,
        "median_entry_spread_pct": (med_spread * 100.0) if med_spread is not None else None,
        "round_trip_spread_cost_pct": (med_spread * 200.0) if med_spread is not None else None,
        "reading": ("the anti-signal is RELATIVE to the control, not absolute: the alert book's "
                    "own expectancy is positive, so mechanically reversing it is negative before "
                    "any cost, and the round-trip spread is paid on top"),
        "verdict": "NO VERDICT - arithmetic, as registered",
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True, default=str)
    print("[O13] -> %s" % OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
