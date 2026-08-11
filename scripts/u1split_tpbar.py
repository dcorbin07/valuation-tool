#!/usr/bin/env python3
"""u1split_tpbar.py — re-derive TP-BAR's calibrated bar and arms split-clean.  [U1-SPLIT / P7]

    python -m scripts.u1split_tpbar

`PREREG_u1split_repair.md` section 3 flags **P7 as the one figure that could change a verdict's
relationship to its bar.** TP-BAR rejected `tp150` on C1 alone, by a margin of
`+5.0812 − 3.1948 = 1.8864pp`, and BOTH that bar and that gain are computed on the corpus this
repair changes. If the corrected gain crosses the corrected bar, **item A reopens**.

This script re-runs C1's construction unchanged — the same `TP_RANGE`/`SL_RANGE`/`TIME_RANGE`,
the same 100 seeds, the same `apply_arm`, the same pairing on commonly-scored trades — on the
same frozen paths, with the split-crossing rows removed. **It does not overwrite TP-BAR's
artifact**; the published bar stays the record of what was published, and both numbers are
reported side by side.

ONE PATH BUILD SERVES BOTH BASES. Paths are keyed by row index, so the as-published and the
split-clean answers are two index sets over one build. Rebuilding twice would spend the expensive
half of the job to obtain identical paths.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.path_arms import ARMS, apply_arm, build_rich_paths           # noqa: E402
from scripts.path_study import SIGNAL_BOOK, SIGNAL_FREEZE, book_rows      # noqa: E402
from scripts.tp_bar import N_DRAWS, PCTILE, SEEDS, draw, percentile       # noqa: E402
from scripts.tp_bar_score import CANDIDATES, WINSOR_PCT                   # noqa: E402
from scripts.u1_entry import DATA                                         # noqa: E402
from valuation.edge import options_backtest as OB                         # noqa: E402

OUT = os.path.join(DATA, "options_pathstudy", "U1SPLIT_TPBAR.json")

# What TP-BAR published, from `PREREG_A_take_profit_bar.md` section 8-9. Restated here so the
# re-derivation reports a MOVE rather than a bare number.
PUBLISHED = {"bar_pp": 5.0812, "tp150_gain_pp": 3.1948, "tp200_gain_pp": 3.8238,
             "shipped_mean_pct": 3.410308}


def score(rows, paths, arm: dict, keep) -> dict:
    per = {}
    for i, days in paths.items():
        if i not in keep:
            continue
        g = apply_arm(rows[i], days, arm)
        if g.get("ok") and g.get("pnl_pct") is not None:
            per[i] = g["pnl_pct"]
    n = len(per)
    return {"n": n, "mean": (sum(per.values()) / n if n else float("nan")), "per": per}


def paired_gain(got, base) -> tuple:
    common = set(got["per"]) & set(base["per"])
    if not common:
        return float("nan"), 0, []
    diffs = [got["per"][i] - base["per"][i] for i in common]
    return sum(diffs) / len(diffs), len(common), diffs


def winsorised(diffs, pct: float = WINSOR_PCT) -> dict:
    cap = percentile(diffs, pct)
    capped = [min(d, cap) for d in diffs]
    return {"cap_pp": 100.0 * cap, "n_capped": sum(1 for d in diffs if d > cap),
            "mean_pp": 100.0 * sum(capped) / len(capped)}


def run(rows, paths, keep, label: str) -> dict:
    base = score(rows, paths, ARMS["shipped"], keep)
    gains = []
    for s in SEEDS:
        got = score(rows, paths, draw(s), keep)
        g, _n, _d = paired_gain(got, base)
        gains.append(100.0 * g)
    bar = percentile(gains, PCTILE)
    out = {"label": label, "n_rows_kept": len(keep), "shipped_n": base["n"],
           "shipped_mean_pct": 100.0 * base["mean"],
           "bar_pp": bar, "null_median_pp": percentile(gains, 50.0),
           "null_min_pp": min(gains), "null_max_pp": max(gains),
           "n_draws_beating_shipped": sum(1 for g in gains if g > 0),
           "arms": {}}
    for name, arm in sorted(CANDIDATES.items()):
        got = score(rows, paths, arm, keep)
        g, n_paired, diffs = paired_gain(got, base)
        gain_pp = 100.0 * g
        out["arms"][name] = {
            "gain_pp": gain_pp, "n_paired": n_paired,
            "clears_bar": bool(gain_pp > bar),
            "percentile_in_null": 100.0 * sum(1 for x in gains if x < gain_pp) / len(gains),
            "winsorised": winsorised(diffs)}
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="U1-SPLIT / P7 — TP-BAR re-derived split-clean.")
    ap.add_argument("--data-root", default=DATA)
    ap.add_argument("--json", default=OUT)
    args = ap.parse_args(argv)

    rows = book_rows(SIGNAL_BOOK)
    splits = OB.load_splits(args.data_root)

    def spans(r):
        a, e = str(r.get("alert_ts") or "")[:10], str(r.get("expiry") or "")[:10]
        return bool(a and e and OB.split_in_window(splits, r.get("ticker"), a, e))

    all_idx = set(range(len(rows)))
    clean_idx = {i for i in all_idx if not spans(rows[i])}
    print("[P7] signal book %d rows, %d cross a split -> %d clean"
          % (len(rows), len(all_idx) - len(clean_idx), len(clean_idx)), flush=True)

    print("[P7] building paths once (no greeks, as C1 did) ...", flush=True)
    paths = build_rich_paths(rows, SIGNAL_FREEZE, "signal", want_greeks=False)
    print("[P7] paths for %d rows" % len(paths), flush=True)

    res = {"item": "U1-SPLIT / P7", "n_draws": N_DRAWS, "pctile": PCTILE,
           "published": PUBLISHED,
           "as_published": run(rows, paths, all_idx, "as_published"),
           "split_clean": run(rows, paths, clean_idx, "split_clean")}

    for lab in ("as_published", "split_clean"):
        r = res[lab]
        print("\n[P7] %s" % lab.upper())
        print("   shipped %+.6f%%/trade on n=%d" % (r["shipped_mean_pct"], r["shipped_n"]))
        print("   BAR (p95) %+8.4fpp   null median %+7.4f  min %+8.4f  max %+8.4f  "
              "%d/%d draws beat shipped"
              % (r["bar_pp"], r["null_median_pp"], r["null_min_pp"], r["null_max_pp"],
                 r["n_draws_beating_shipped"], N_DRAWS))
        for name in sorted(r["arms"]):
            a = r["arms"][name]
            print("   %-6s gain %+8.4fpp at the %5.1fth pct -> %-6s | winsorised %+7.4fpp "
                  "(cap %+.1fpp, %d capped)"
                  % (name, a["gain_pp"], a["percentile_in_null"],
                     "CLEARS" if a["clears_bar"] else "FAILS",
                     a["winsorised"]["mean_pp"], a["winsorised"]["cap_pp"],
                     a["winsorised"]["n_capped"]))

    a, b = res["as_published"], res["split_clean"]
    res["moves"] = {
        "bar_pp": [a["bar_pp"], b["bar_pp"]],
        "tp150_gain_pp": [a["arms"]["tp150"]["gain_pp"], b["arms"]["tp150"]["gain_pp"]],
        "tp200_gain_pp": [a["arms"]["tp200"]["gain_pp"], b["arms"]["tp200"]["gain_pp"]],
        "tp150_still_fails": not b["arms"]["tp150"]["clears_bar"],
        "tp200_still_fails": not b["arms"]["tp200"]["clears_bar"],
        "verdict_unchanged": bool(not b["arms"]["tp150"]["clears_bar"]
                                  and not b["arms"]["tp200"]["clears_bar"])}
    print("\n[P7] bar %+.4f -> %+.4fpp | tp150 %+.4f -> %+.4fpp | tp200 %+.4f -> %+.4fpp"
          % (a["bar_pp"], b["bar_pp"], a["arms"]["tp150"]["gain_pp"],
             b["arms"]["tp150"]["gain_pp"], a["arms"]["tp200"]["gain_pp"],
             b["arms"]["tp200"]["gain_pp"]))
    print("[P7] TP-BAR VERDICT UNCHANGED (both arms still fail C1): %s"
          % res["moves"]["verdict_unchanged"])
    if not res["moves"]["verdict_unchanged"]:
        print("[P7] *** ITEM A REOPENS — a corrected arm crosses its corrected bar ***")

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=float)
    print("[P7] -> %s" % args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
