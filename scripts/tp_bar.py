"""Item A / TP-BAR — C1, the calibrated bar (options bot, 2026-08-11).

    python -m scripts.tp_bar --calibrate

Don chose Option 2 of `PREREG_A_take_profit_bar.md` on 2026-08-11: run C1-C4 and decide the
take-profit question against a bar that was MEASURED rather than chosen. This module is C1 and
only C1. It is committed, and its bar is committed, BEFORE `tp150` is scored against anything —
that ordering is the whole point of the exercise and is visible in the git history.

THE CAVEAT TRAVELS WITH THE NUMBER. The options ENTRY signal is dead (R2: the alert book returns
+3.41%/trade against a five-seed random-entry control's +10.06%, paired sign test z -4.903).
Nothing here is a tradeable-edge claim. This decides how a PAPER book exits.

WHAT THE NULL IS, AND WHAT IT IS NOT — read this before quoting the bar.

`PREREG_A_take_profit_bar.md` C1 fixes the construction: score the shipped policy against
randomly perturbed exit parameters drawn from the same family, target/stop/time-stop levels
jittered within their TESTED ranges, n = 100 draws, seeds 1000-1099, on the identical frozen
paths through the identical `apply_arm`. The bar is the p95 of that null.

It is NOT a no-effect null. Every draw is a real policy scored on real paths, and this record
already says raised targets tend to help on this book, so draws that beat `shipped` are EXPECTED
and are not evidence of a defect. What the p95 answers is the selection question, which is the
actual hazard item A carries: is `tp150`'s +3.19pp distinguished WITHIN ITS OWN FAMILY, or is it
one of many parameter choices that happen to beat the shipped exit on this one 3,885-trade book?
A bar built this way can therefore land ABOVE the effect and refuse it. That was pre-committed
(memo section 5, Option 2: "it may return a bar above +3.82pp and refuse the change") and it is
binding whichever way it comes out.

THE TESTED RANGES are read off O1's own grid (`options_exitlab.POLICIES`), not invented here:
target 0.50 (tp50) to 2.00 (tp200), stop -0.30 (sl30) to -0.70 (sl70), time-stop fraction 0.25
(time25) to 1.00 (time100). The `None` variants are deliberately NOT drawn — the memo says
"levels jittered within their tested ranges", and switching a leg off is a categorical change,
not a jitter. Pinned by `tests/test_tp_bar.py`.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.path_arms import ARMS, apply_arm, build_rich_paths      # noqa: E402
from scripts.path_study import (SIGNAL_BOOK, SIGNAL_FREEZE, OUT_DIR,  # noqa: E402
                                book_rows, _log)

# The tested ranges, from `options_exitlab.POLICIES`. Endpoints are the extreme arms O1 ran.
TP_RANGE = (0.50, 2.00)          # tp50 .. tp200
SL_RANGE = (-0.70, -0.30)        # sl70 .. sl30
TIME_RANGE = (0.25, 1.00)        # time25 .. time100

N_DRAWS = 100
SEEDS = tuple(range(1000, 1000 + N_DRAWS))   # the project's convention, as X7 and PLACEBO_HAC
PCTILE = 95                                   # the bar is the p95 of the null

NULL_PATH = os.path.join(OUT_DIR, "TPBAR_NULL.json")


def draw(seed: int) -> dict:
    """One jittered policy. Seeded per draw so any single draw is reproducible on its own."""
    rng = random.Random(seed)
    return {"tp": rng.uniform(*TP_RANGE),
            "sl": rng.uniform(*SL_RANGE),
            "time_frac": rng.uniform(*TIME_RANGE)}


def percentile(xs, p: float) -> float:
    """Linear-interpolated percentile. Written out rather than imported so the bar does not
    depend on which numpy happens to be installed."""
    s = sorted(xs)
    if not s:
        return float("nan")
    if len(s) == 1:
        return float(s[0])
    k = (len(s) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return float(s[lo] + (s[hi] - s[lo]) * (k - lo))


def score(rows, paths, arm: dict) -> dict:
    """Mean per-trade return of one policy, plus the per-trade series keyed by path index."""
    per = {}
    for i, days in paths.items():
        g = apply_arm(rows[i], days, arm)
        if g.get("ok") and g.get("pnl_pct") is not None:
            per[i] = g["pnl_pct"]
    n = len(per)
    return {"n": n, "mean": (sum(per.values()) / n if n else float("nan")), "per": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibrate", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not a.calibrate:
        ap.error("pass --calibrate")

    rows = book_rows(SIGNAL_BOOK)
    # No greeks: neither `shipped` nor any jittered draw reads delta or IV, and the greek pass
    # is the expensive half of the path build. The paths are otherwise identical.
    paths = build_rich_paths(rows, SIGNAL_FREEZE, "signal", want_greeks=False)

    base = score(rows, paths, ARMS["shipped"])
    _log("shipped: n=%d mean=%+.6f" % (base["n"], base["mean"]))

    draws = []
    for s in SEEDS:
        arm = draw(s)
        got = score(rows, paths, arm)
        # Paired on the trades BOTH policies scored, so a draw that loses a trade to a rejected
        # exit quote cannot move the gain through the denominator.
        common = set(got["per"]) & set(base["per"])
        gain = (sum(got["per"][i] - base["per"][i] for i in common) / len(common)
                if common else float("nan"))
        draws.append({"seed": s, "tp": arm["tp"], "sl": arm["sl"],
                      "time_frac": arm["time_frac"], "n": got["n"], "n_paired": len(common),
                      "mean": got["mean"], "gain_pp": 100.0 * gain})
        _log("  seed %d  tp %.3f sl %+.3f t %.3f  ->  gain %+.4fpp"
             % (s, arm["tp"], arm["sl"], arm["time_frac"], 100.0 * gain))

    gains = [d["gain_pp"] for d in draws]
    bar = percentile(gains, PCTILE)
    out = {
        "what": "C1 calibrated bar for a paper-book exit-policy change (item A / TP-BAR)",
        "prereg": "PREREG_A_take_profit_bar.md section 3, C1",
        "caveat": "The options entry signal is dead (R2). Paper-book policy only.",
        "construction": {"tp_range": TP_RANGE, "sl_range": SL_RANGE,
                         "time_frac_range": TIME_RANGE, "n_draws": N_DRAWS,
                         "seeds": [SEEDS[0], SEEDS[-1]], "percentile": PCTILE,
                         "book": "signal (R2-corrected)", "scorer": "scripts.path_arms.apply_arm",
                         "paired": "gain is the mean per-trade difference on commonly-scored "
                                   "trades, not a difference of two book means"},
        "shipped": {"n": base["n"], "mean_pct": 100.0 * base["mean"]},
        "null": {"n": len(gains), "min_pp": min(gains), "p5_pp": percentile(gains, 5),
                 "median_pp": percentile(gains, 50), "p95_pp": bar, "max_pp": max(gains),
                 "mean_pp": sum(gains) / len(gains),
                 "frac_positive": sum(1 for g in gains if g > 0) / len(gains)},
        "BAR_PP": bar,
        "draws": draws,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    p = a.out or NULL_PATH
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    _log("wrote " + p)
    print("\nCALIBRATED BAR (p95 of the null) = %+.4f pp" % bar)
    print("null: min %+.3f  p5 %+.3f  median %+.3f  p95 %+.3f  max %+.3f  %.0f%% positive"
          % (min(gains), percentile(gains, 5), percentile(gains, 50), bar, max(gains),
             100.0 * out["null"]["frac_positive"]))


if __name__ == "__main__":
    main()
