#!/usr/bin/env python3
"""u1split_rebank.py — re-bank the options books split-clean and re-derive R2.  [U1-SPLIT]

    python -m scripts.u1split_rebank --data-root <repo>/data

Pre-registered in `PREREG_u1split_repair.md`, committed alone before any repair code existed.

WHAT IT DOES, AND WHAT IT DELIBERATELY DOES NOT.

It filters the banked books through the SAME predicate the source guard applies at entry
(`options_backtest.split_in_window`), writes the corrected books to NEW paths, fingerprints old
and new, and re-derives every published figure the register named. **It never overwrites an
original** — the uncorrected books are the record of what was published and are needed to check
this very correction.

FILTERING IS EXACTLY EQUIVALENT TO RE-MINING, AND THAT WAS VERIFIED RATHER THAN ASSUMED. The
guard refuses a candidate BEFORE simulation and changes no surviving trade's arithmetic, so the
two routes must agree. Re-mining the 2021-07-22 rebalance under the guard produced 146 trades
against 147 banked; the dropped row was GE; the key sets matched exactly and **0 of 146 shared
trades differed on any field**. That is why ~34,000 trades are re-banked by filter rather than
by a multi-hour re-mine.

THE CORRECTION'S DIRECTION IS DISCLOSED. Excluding is CONSERVATIVE with respect to R2's standing
negative verdict: the flagship case's true value is −100%, so re-pricing would push the control's
mean further down than excluding does, and would help the alert more.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.u1_entry import DATA                          # noqa: E402
from valuation.edge import options_backtest as OB          # noqa: E402
from valuation.edge import options_stats as OS             # noqa: E402
from valuation.edge import options_universe as U           # noqa: E402
from valuation.edge import options_veto as V               # noqa: E402

UNIV = os.path.join(DATA, "options_universe")
OUT_JSON = os.path.join(UNIV, "U1SPLIT_REDERIVATION.json")
MANIFEST = os.path.join(UNIV, "U1SPLIT_MANIFEST.json")
DRAWS = 4000


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _m(rows):
    return OS.mean_pnl(rows)


def _pp(x):
    return None if x is None else 100.0 * x


def rederive(alert, ctrl, label: str, seed: int = 0, draws: int = DRAWS) -> dict:
    """Every published R2 figure, from one book pair. Same functions the record used."""
    out = {"label": label, "n_alert": len(alert), "n_control": len(ctrl),
           "alert_mean_pct": _pp(_m(alert)), "control_mean_pct": _pp(_m(ctrl))}
    out["gap_pp"] = out["alert_mean_pct"] - out["control_mean_pct"]

    # P2 — date-block bootstrap, calendar months, paired across the two books.
    db = V.fast_block_diff(alert, ctrl, seed=seed, draws=draws)
    out["date_block"] = {"ci95_pp": [_pp(db["ci95"][0]), _pp(db["ci95"][1])],
                         "diff_pp": _pp(db["diff"]), "n_blocks": db["n_blocks"],
                         "excludes_zero": db["excludes_zero"],
                         "negative_at_significance": db["negative_at_significance"]}
    # P3 — the paired name-year sign test. R2's standing rule: this carries the verdict.
    pn = OS.paired_name_year(alert, ctrl)
    out["paired_name_year"] = {k: pn.get(k) for k in
                               ("n_cells", "n_wins", "win_rate", "sign_test_z", "sign_test_p",
                                "paired_t", "paired_p")}
    # P4 — breadth, on the module's own BASELINE_55 constant rather than a re-derived list.
    base = [r for r in alert if str(r.get("ticker") or "").upper() in U.BASELINE_55]
    fresh = [r for r in alert if str(r.get("ticker") or "").upper() not in U.BASELINE_55]
    out["breadth"] = {
        "baseline_n_names": len({r["ticker"] for r in base}), "baseline_n": len(base),
        "baseline_mean_pct": _pp(_m(base)),
        "new_n_names": len({r["ticker"] for r in fresh}), "new_n": len(fresh),
        "new_mean_pct": _pp(_m(fresh))}
    # P5 — O20 point-in-time liquidity.
    liq = [r for r in alert if r.get("pit_liquid") is True]
    ill = [r for r in alert if r.get("pit_liquid") is False]
    out["o20"] = {"n_liquid": len(liq), "liquid_mean_pct": _pp(_m(liq)),
                  "n_illiquid": len(ill), "illiquid_mean_pct": _pp(_m(ill))}
    cl = [r for r in ctrl if r.get("pit_liquid") is True]
    pn_liq = OS.paired_name_year(liq, cl)
    out["o20"]["liquid_subset_sign_z"] = pn_liq.get("sign_test_z")
    # P6 — R3 clustering, reported with its shuffled null (a raw design effect is not evidence).
    eff = OS.effective_n(alert)
    out["r3"] = {k: eff.get(k) for k in
                 ("n", "n_blocks", "icc", "design_effect", "design_effect_null_p95",
                  "clustering_measurable")}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U1-SPLIT — re-bank split-clean and re-derive R2.")
    ap.add_argument("--data-root", default=DATA)
    ap.add_argument("--draws", type=int, default=DRAWS)
    args = ap.parse_args(argv)

    splits = OB.load_splits(args.data_root)
    print("[U1-SPLIT] split table: %d tickers carry a real split" % len(splits), flush=True)

    def spans(r):
        a, e = str(r.get("alert_ts") or "")[:10], str(r.get("expiry") or "")[:10]
        return bool(a and e and OB.split_in_window(splits, r.get("ticker"), a, e))

    man = {"item": "U1-SPLIT", "books": [],
           "note": ("Originals are never overwritten - they are the record of what was published "
                    "and are needed to check this correction. Corrected books are new files.")}

    # ---- the alert book ---------------------------------------------------------------------
    src = os.path.join(UNIV, "state_r2_corrected.pkl")
    with open(src, "rb") as f:
        blob = pickle.load(f)
    raw_alert = blob["rows"]
    alert = [r for r in raw_alert if not spans(r)]
    dst = os.path.join(UNIV, "state_r2_splitclean.pkl")
    with open(dst, "wb") as f:
        pickle.dump(dict(blob, rows=alert, u1_split_clean=True,
                         n_dropped_u1_split=len(raw_alert) - len(alert)), f, protocol=4)
    man["books"].append({"role": "alert", "src": os.path.basename(src),
                         "dst": os.path.basename(dst),
                         "n_before": len(raw_alert), "n_after": len(alert),
                         "sha256_before": sha256(src), "sha256_after": sha256(dst)})
    print("[U1-SPLIT] alert book %d -> %d" % (len(raw_alert), len(alert)), flush=True)

    # ---- the five control seeds --------------------------------------------------------------
    raw_ctrl, ctrl = [], []
    for s in range(5):
        p = os.path.join(UNIV, "control_r2_seed%d.pkl" % s)
        with open(p, "rb") as f:
            rows = pickle.load(f)
        keep = [r for r in rows if not spans(r)]
        q = os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s)
        with open(q, "wb") as f:
            pickle.dump(keep, f, protocol=4)
        man["books"].append({"role": "control_seed%d" % s, "src": os.path.basename(p),
                             "dst": os.path.basename(q), "n_before": len(rows),
                             "n_after": len(keep), "sha256_before": sha256(p),
                             "sha256_after": sha256(q)})
        raw_ctrl.extend(rows)
        ctrl.extend(keep)
    print("[U1-SPLIT] control %d -> %d over 5 seeds" % (len(raw_ctrl), len(ctrl)), flush=True)

    # ---- the freeze is untouched, and that is checked rather than asserted --------------------
    fm = os.path.join(DATA, "options_freeze", "R2_CORRECTED_2026-08-08", "FREEZE_MANIFEST.json")
    man["freeze"] = {"manifest": fm, "exists": os.path.exists(fm)}
    if os.path.exists(fm):
        man["freeze"]["sha256"] = sha256(fm)
        try:
            with open(fm, encoding="utf-8") as f:
                stamp = json.load(f)
            from valuation.edge import options_freeze as FZ
            years = stamp.get("years") or stamp.get("stamp") or {}
            ver = FZ.verify_stamp(years, root=os.path.join(args.data_root, "options")) \
                if years else {"skipped": "no years block"}
            man["freeze"]["verify"] = {k: ver.get(k) for k in
                                       ("ok", "n_checked", "n_changed", "changed")} \
                if isinstance(ver, dict) else str(ver)
        except Exception as e:                                            # noqa: BLE001
            man["freeze"]["verify_error"] = "%s: %s" % (type(e).__name__, e)
    print("[U1-SPLIT] freeze manifest: %s" % json.dumps(man["freeze"].get("verify"))[:160],
          flush=True)

    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2)

    # ---- re-derive both ways -----------------------------------------------------------------
    out = {"item": "U1-SPLIT", "draws": args.draws,
           "as_published": rederive(raw_alert, raw_ctrl, "as_published", draws=args.draws),
           "split_clean": rederive(alert, ctrl, "split_clean", draws=args.draws)}
    a, b = out["as_published"], out["split_clean"]
    out["moves"] = {
        "gap_pp": [a["gap_pp"], b["gap_pp"]],
        "alert_mean_pct": [a["alert_mean_pct"], b["alert_mean_pct"]],
        "control_mean_pct": [a["control_mean_pct"], b["control_mean_pct"]],
        "sign_z": [a["paired_name_year"]["sign_test_z"], b["paired_name_year"]["sign_test_z"]],
        "date_block_ci_pp": [a["date_block"]["ci95_pp"], b["date_block"]["ci95_pp"]],
        "verdict_unchanged": bool(b["gap_pp"] < 0
                                  and b["date_block"]["negative_at_significance"]
                                  and (b["paired_name_year"]["sign_test_z"] or 0) < 0
                                  and (b["paired_name_year"]["sign_test_p"] or 1) < 0.05)}

    for lab in ("as_published", "split_clean"):
        r = out[lab]
        print("\n[U1-SPLIT] %s" % lab.upper())
        print("   alert %+8.4f%% (n=%d)   control %+8.4f%% (n=%d)   GAP %+8.4fpp"
              % (r["alert_mean_pct"], r["n_alert"], r["control_mean_pct"], r["n_control"],
                 r["gap_pp"]))
        print("   date-block CI95 [%+.4f, %+.4f]pp over %d months, negative_at_sig=%s"
              % (r["date_block"]["ci95_pp"][0], r["date_block"]["ci95_pp"][1],
                 r["date_block"]["n_blocks"], r["date_block"]["negative_at_significance"]))
        p = r["paired_name_year"]
        print("   sign test %d/%d cells (%.1f%%), z %+.4f, p %.3g"
              % (p["n_wins"], p["n_cells"], 100 * p["win_rate"], p["sign_test_z"],
                 p["sign_test_p"]))
        bd = r["breadth"]
        print("   breadth: baseline %d names %+8.4f%% (n=%d) | new %d names %+8.4f%% (n=%d)"
              % (bd["baseline_n_names"], bd["baseline_mean_pct"], bd["baseline_n"],
                 bd["new_n_names"], bd["new_mean_pct"], bd["new_n"]))
        o = r["o20"]
        print("   O20: liquid %d %+8.4f%% | illiquid %d %+8.4f%% | liquid-subset sign z %+.4f"
              % (o["n_liquid"], o["liquid_mean_pct"], o["n_illiquid"], o["illiquid_mean_pct"],
                 o["liquid_subset_sign_z"] or float("nan")))
        r3 = r["r3"]
        print("   R3: design effect %.4f vs shuffled-null p95 %.4f, measurable=%s"
              % (r3["design_effect"], r3["design_effect_null_p95"] or float("nan"),
                 r3["clustering_measurable"]))

    print("\n[U1-SPLIT] VERDICT UNCHANGED: %s" % out["moves"]["verdict_unchanged"])
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("[U1-SPLIT] -> %s" % OUT_JSON)
    print("[U1-SPLIT] -> %s" % MANIFEST)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
