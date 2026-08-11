"""O26 — how big must a bucket be before one lucky contract cannot flip its verdict?

    python -m scripts.o26_floor

Pre-registered in `PREREG_o26_bucket_floor.md`, committed alone at bf5324c before this file
existed. The n-grid, the 0.05 bar and the one-grid-step agreement rule are all fixed there.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import bucket_floor as BF        # noqa: E402
from valuation.edge import antisignal as A           # noqa: E402
from valuation.edge.options_tracker import MIN_CLOSED_PER_BUCKET   # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
OUT = os.path.join(DATA, "free_analysis", "O26_BUCKET_FLOOR.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O26 - per-bucket floor")
    ap.add_argument("--draws", type=int, default=BF.DRAWS)
    ap.add_argument("--seed", type=int, default=26)
    args = ap.parse_args(argv)

    with open(os.path.join(DATA, "options_universe", "state_r2_splitclean.pkl"), "rb") as f:
        alert = pickle.load(f)["rows"]
    rets = [r["pnl_pct"] for r in alert if r.get("pnl_pct") is not None]
    print("[O26] alert book n=%d  shipped floor=%d" % (len(rets), MIN_CLOSED_PER_BUCKET),
          flush=True)

    early, late = A.split_halves(alert)
    re_ = [r["pnl_pct"] for r in early if r.get("pnl_pct") is not None]
    rl = [r["pnl_pct"] for r in late if r.get("pnl_pct") is not None]
    print("[O26] halves %d / %d" % (len(re_), len(rl)), flush=True)

    res = {"item": "O26", "register": "PREREG_o26_bucket_floor.md",
           "book": "split_clean (U1-SPLIT 2026-08-11)",
           "shipped_floor": MIN_CLOSED_PER_BUCKET,
           "n_grid": list(BF.N_GRID), "bar": BF.FLIP_BAR, "draws": args.draws,
           "statistic": ("P(sign of bucket mean flips when the single most extreme trade, "
                         "argmax |R - mean|, is removed)")}

    for label, rr, seed in (("full", rets, args.seed),
                            ("early", re_, args.seed + 100),
                            ("late", rl, args.seed + 200)):
        c = BF.curve(rr, draws=args.draws, seed=seed)
        fl = BF.floor_from_curve(c)
        res[label] = {"curve": c, "floor": fl, "n": len(rr)}
        print("[O26] %-5s floor=%s" % (label, fl), flush=True)
        for row in c:
            print("[O26]    n=%-4d P_flip=%s" % (
                row["n"], ("%.4f" % row["p_flip"]) if row["p_flip"] is not None else "n/a"),
                flush=True)

    # SECONDARY, reported separately rather than folded into the primary.
    sec = [BF.half_sign_agreement(rets, n, draws=args.draws, seed=args.seed + 300 + i)
           for i, n in enumerate(BF.N_GRID)]
    res["secondary_half_sign_agreement"] = sec
    sec_floor = None
    for row in sorted(sec, key=lambda d: d["n"]):
        if row["agreement"] is not None and row["agreement"] >= 0.95:
            sec_floor = row["n"]
            break
    res["secondary_floor_at_95pct_agreement"] = sec_floor
    print("[O26] secondary (half sign agreement >= 0.95) floor = %s" % sec_floor, flush=True)

    res["verdict"] = BF.verdict(res["early"]["floor"], res["late"]["floor"])
    print("[O26] VERDICT: %s  (early %s, late %s)"
          % (res["verdict"], res["early"]["floor"], res["late"]["floor"]), flush=True)

    # Which live buckets would lose `enough_to_judge` at the new floor? Reported explicitly --
    # a floor change that retroactively unpublishes a finding is a finding in its own right.
    prop = res["full"]["floor"] if res["verdict"] == "RAISE" else MIN_CLOSED_PER_BUCKET
    lost = {}
    for field in ("cap_tier", "horizon"):
        g = {}
        for r in alert:
            g.setdefault(str(r.get(field)), 0)
            g[str(r.get(field))] += 1
        lost[field] = {k: {"n": v, "judgeable_at_30": v >= MIN_CLOSED_PER_BUCKET,
                           "judgeable_at_proposed": v >= (prop or MIN_CLOSED_PER_BUCKET)}
                       for k, v in sorted(g.items())}
    years = {}
    for r in alert:
        y = str(r.get("alert_ts"))[:4]
        years[y] = years.get(y, 0) + 1
    lost["entry_year"] = {k: {"n": v, "judgeable_at_30": v >= MIN_CLOSED_PER_BUCKET,
                              "judgeable_at_proposed": v >= (prop or MIN_CLOSED_PER_BUCKET)}
                          for k, v in sorted(years.items())}
    res["proposed_floor"] = prop
    res["live_bucket_impact"] = lost
    n_lost = sum(1 for grp in lost.values() for d in grp.values()
                 if d["judgeable_at_30"] and not d["judgeable_at_proposed"])
    res["n_buckets_losing_judgeable"] = n_lost
    print("[O26] buckets losing enough_to_judge at %s: %d" % (prop, n_lost), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True, default=str)
    print("[O26] -> %s" % OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
