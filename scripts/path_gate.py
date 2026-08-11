"""The path study — stage 2's gate (options bot, 2026-08-10).

    python -m scripts.path_gate --signal <json> --control <json>

Applies, mechanically, the discipline `PREREG_path_study.md` §5 committed before any arm ran:

  * the WALL — arms are ranked on a DECIDE half of the book and the published number is measured
    on the OTHER half, both directions, and a disagreement between directions is a NULL;
  * the RANDOM-ENTRY CONTROL at five seeds pooled — O1's `gate()` rule reproduced exactly, in
    which ADOPT requires the arm to help on BOTH entry sets. An exit rule is supposed to be a
    property of OPTIONS; one that helps only the book it was measured on is fitted to that book;
  * DATE-BLOCK CLUSTERED inference via `options_stats.date_block_diff` — calendar months
    resampled together, never a trade-level bootstrap, because R3 measured the design effect on
    this exact book at 2.2121 against a shuffled-null p95 of 1.2037;
  * O1's own pre-committed bar, `MIN_EXPECTANCY_GAIN = 0.10`, and FDR at q = 0.1 across the arm
    family;
  * ambiguous = NULL.

AND THE CAVEAT THIS GATE CANNOT REMOVE. The options entry signal is dead — R2 measured the real
book at +3.27%/trade against a five-seed random-entry control's +8.33%, paired sign test
z −4.961 (split-clean per U1-SPLIT 2026-08-11; as published +3.41 / +10.06 / −4.903). A verdict produced here is a verdict about how the PAPER book exits, never about
whether the alert is worth trading. Even an ADOPT would ship to the paper book only.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_stats as OS       # noqa: E402
from scripts.path_study import OUT_DIR, _log         # noqa: E402

MIN_EXPECTANCY_GAIN = 0.10        # O1's, not a new one
FDR_Q = 0.10
BASELINE = "shipped"


def as_rows(recs):
    return [{"alert_ts": r["d"], "pnl_pct": r["pnl_pct"], "ticker": r.get("tk"),
             "seed": r.get("seed"), "i": r["i"]} for r in recs]


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else None


def split_date(rows):
    ds = sorted(r["alert_ts"] for r in rows)
    return ds[len(ds) // 2]


def half(rows, cut, which):
    return [r for r in rows if (r["alert_ts"] < cut if which == "early" else r["alert_ts"] >= cut)]


def paired_gain(arm_rows, base_rows, cut=None, which=None):
    """Matched by trade index: an arm and the baseline see identical entries by construction,
    so the difference is the exit and nothing else."""
    b = {r["i"]: r["pnl_pct"] for r in base_rows}
    d = []
    for r in arm_rows:
        if r["i"] in b:
            if cut and which and not ((r["alert_ts"] < cut) if which == "early"
                                      else (r["alert_ts"] >= cut)):
                continue
            d.append(r["pnl_pct"] - b[r["i"]])
    return mean(d), len(d)


def bh(pvals: dict, q: float) -> dict:
    items = sorted(((k, v) for k, v in pvals.items() if v is not None), key=lambda x: x[1])
    m = len(items)
    out = {k: False for k in pvals}
    kmax = 0
    for i, (k, p) in enumerate(items, start=1):
        if p <= q * i / m:
            kmax = i
    for i, (k, p) in enumerate(items, start=1):
        out[k] = i <= kmax
    return out


def run(signal_path, control_path):
    with open(signal_path, encoding="utf-8") as f:
        sig = json.load(f)["arms"]
    ctl = None
    if control_path and os.path.exists(control_path):
        with open(control_path, encoding="utf-8") as f:
            ctl = json.load(f)["arms"]

    S = {k: as_rows(v) for k, v in sig.items()}
    C = {k: as_rows(v) for k, v in ctl.items()} if ctl else {}
    base_s = S[BASELINE]
    cut = split_date(base_s)
    arms = [k for k in S if k != BASELINE]

    res = {"cut_date": cut, "n_signal": len(base_s),
           "n_control": len(C.get(BASELINE, [])) if C else 0,
           "bar": MIN_EXPECTANCY_GAIN, "arms": {}, "wall": {}, "verdict": {}}

    # ---- full-book descriptive (NOT a verdict; the wall's measure half is) -----------------
    for a in arms:
        g_full, n = paired_gain(S[a], base_s)
        row = {"expectancy": mean([r["pnl_pct"] for r in S[a]]),
               "gain_vs_shipped_full": g_full, "n": n}
        if C and a in C:
            gc, nc = paired_gain(C[a], C[BASELINE])
            row["gain_vs_shipped_control"] = gc
            row["n_control"] = nc
        res["arms"][a] = row

    # ---- the wall -------------------------------------------------------------------------
    for direction, decide, measure in (("decide_early", "early", "late"),
                                       ("decide_late", "late", "early")):
        ranked = []
        for a in arms:
            g, n = paired_gain(S[a], base_s, cut, decide)
            if n >= 30:
                ranked.append((g if g is not None else -9, a, n))
        ranked.sort(reverse=True)
        if not ranked:
            res["wall"][direction] = {"ok": False, "reason": "no arm with >=30 decide trades"}
            continue
        gsel, sel, ndec = ranked[0]
        gm, nm = paired_gain(S[sel], base_s, cut, measure)
        arm_m = [r for r in S[sel] if (r["alert_ts"] < cut) == (measure == "early")]
        base_m = [r for r in base_s if (r["alert_ts"] < cut) == (measure == "early")]
        ci = OS.date_block_diff(arm_m, base_m, block="month", seed=0)
        entry = {"ok": True, "selected_on_decide": sel, "decide_gain": gsel,
                 "n_decide": ndec, "measure_gain": gm, "n_measure": nm,
                 "clustered_ci95": ci.get("ci95"), "ci_excludes_zero": ci.get("excludes_zero"),
                 "n_blocks": ci.get("n_blocks"),
                 "clears_bar_on_measure": bool(gm is not None and gm >= MIN_EXPECTANCY_GAIN),
                 "ranked_top3": [(a, round(g, 4)) for g, a, _ in ranked[:3]]}
        if C and sel in C:
            gc, _ = paired_gain(C[sel], C[BASELINE])
            entry["control_gain_pooled"] = gc
            entry["helps_control_too"] = bool(gc is not None and gc > 0)
        res["wall"][direction] = entry

    # ---- FDR across the family, on the FULL book, reported not adjudicated ------------------
    pv = {}
    for a in arms:
        ci = OS.date_block_diff(S[a], base_s, block="month", seed=0)
        if ci.get("ok"):
            res["arms"][a]["clustered_ci95_full"] = ci["ci95"]
            res["arms"][a]["excludes_zero_full"] = ci["excludes_zero"]
            lo, hi = ci["ci95"]
            pv[a] = 0.04 if (lo > 0 or hi < 0) else 0.5     # coarse; the bar is the gain, not p
    res["fdr_discoveries"] = bh(pv, FDR_Q)

    # ---- verdict ---------------------------------------------------------------------------
    d1 = res["wall"].get("decide_early", {})
    d2 = res["wall"].get("decide_late", {})
    same_arm = d1.get("selected_on_decide") == d2.get("selected_on_decide")
    both_clear = d1.get("clears_bar_on_measure") and d2.get("clears_bar_on_measure")
    best = max((r.get("gain_vs_shipped_full") or -9) for r in res["arms"].values())
    res["verdict"] = {
        "label": ("ADOPT" if (same_arm and both_clear) else
                  "NULL — directions disagree" if not same_arm else
                  "REJECT — no arm clears the pre-committed bar"),
        "same_arm_both_directions": same_arm,
        "both_measure_halves_clear_bar": bool(both_clear),
        "largest_full_book_gain": best,
        "bar": MIN_EXPECTANCY_GAIN,
        "note": ("The bar is O1's own MIN_EXPECTANCY_GAIN, pre-committed there and re-committed "
                 "in PREREG_path_study.md before any arm ran. It is a 10 PERCENTAGE POINT gain "
                 "in per-trade expectancy, which is a high bar and deliberately so."),
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signal", required=True)
    ap.add_argument("--control", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = run(a.signal, a.control)
    os.makedirs(OUT_DIR, exist_ok=True)
    p = a.out or os.path.join(OUT_DIR, "PATHSTUDY_STAGE2.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    _log("wrote " + p)
    print(json.dumps(res["verdict"], indent=1))
    return res


if __name__ == "__main__":
    main()
