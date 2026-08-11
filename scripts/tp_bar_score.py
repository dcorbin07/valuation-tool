"""Item A / TP-BAR — C2-C4 and the verdict (options bot, 2026-08-11).

    python -m scripts.tp_bar_score --run

DELIBERATELY A SEPARATE MODULE FROM `scripts/tp_bar.py`. The bar was committed at e8e5505 with
this file not yet in existence, so the bar cannot have been edited after seeing what it refuses.
Nothing here imports a threshold it is free to change: `BAR_PP` is READ from the artifact C1
wrote, and a mismatch against the value transcribed into the memo is a hard failure.

THE CAVEAT TRAVELS. The options ENTRY signal is dead (R2: +3.41%/trade against a five-seed
random-entry control's +10.06%, sign test z -4.903). This decides how a PAPER book exits and
cannot make the alert tradeable.

THE VERDICT IS MECHANICAL, as Don's instruction fixed it: `tp150` clears the calibrated bar and
C2-C4 -> ADOPT on the paper book; it fails -> item A closes REJECTED. No third state.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.path_arms import ARMS, apply_arm, build_rich_paths        # noqa: E402
from scripts.path_study import (DATA, SIGNAL_BOOK, SIGNAL_FREEZE, OUT_DIR,  # noqa: E402
                                book_rows, _log)
from scripts.tp_bar import NULL_PATH, percentile, score                 # noqa: E402

# The two arms Don's choice puts on trial. Their parameters are O1's, unchanged.
CANDIDATES = {
    "tp150": {"tp": 1.50, "sl": -0.50, "time_frac": 0.50},
    "tp200": {"tp": 2.00, "sl": -0.50, "time_frac": 0.50},
}

WINSOR_PCT = 99.0        # C2: cap the top 1% of per-trade differences
BAR_IN_MEMO = 5.0812     # transcribed into PREREG_A_take_profit_bar.md section 8 at e8e5505
O1_ARTIFACT = os.path.join(DATA, "options_exitlab", "EXITLAB_FROZEN_2026-08-08.json")
OUT_PATH = os.path.join(OUT_DIR, "TPBAR_VERDICT.json")


def load_bar() -> float:
    """The bar is read, never redefined. If the artifact disagrees with the number already
    published in the memo, stop rather than quietly score against a different bar."""
    with open(NULL_PATH, "r", encoding="utf-8") as f:
        null = json.load(f)
    bar = float(null["BAR_PP"])
    if abs(bar - BAR_IN_MEMO) > 5e-4:
        raise SystemExit("REFUSING TO SCORE: artifact bar %.6f != the %.4f published in the memo"
                         % (bar, BAR_IN_MEMO))
    return bar, null


def winsorised_mean(diffs, pct: float = WINSOR_PCT) -> dict:
    """C2 — a condition that does not run through the untouched mean.

    Caps the top 1% of per-trade differences at the 99th percentile and re-means. The point is
    that the raw gain is a tail average (the top 1% of trades carry 106-210% of each arm's
    measured gain), so an arm whose whole advantage is a handful of trades fails here.
    """
    cap = percentile(diffs, pct)
    capped = [min(d, cap) for d in diffs]
    return {"cap_pp": 100.0 * cap,
            "n_capped": sum(1 for d in diffs if d > cap),
            "mean_pp": 100.0 * sum(capped) / len(capped)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if not a.run:
        ap.error("pass --run")

    bar, null = load_bar()
    _log("bar read from C1 artifact: %+.4fpp" % bar)

    rows = book_rows(SIGNAL_BOOK)
    paths = build_rich_paths(rows, SIGNAL_FREEZE, "signal", want_greeks=False)
    base = score(rows, paths, ARMS["shipped"])
    _log("shipped n=%d mean=%+.6f  (R2 control: +3.4103%%)" % (base["n"], 100 * base["mean"]))

    gains = [d["gain_pp"] for d in null["draws"]]
    out = {"bar_pp": bar, "prereg": "PREREG_A_take_profit_bar.md sections 3 and 8",
           "caveat": "The options entry signal is dead (R2). Paper-book policy only.",
           "shipped_mean_pct": 100.0 * base["mean"], "n": base["n"], "arms": {}}

    for name, arm in CANDIDATES.items():
        got = score(rows, paths, arm)
        common = sorted(set(got["per"]) & set(base["per"]))
        diffs = [got["per"][i] - base["per"][i] for i in common]
        gain_pp = 100.0 * sum(diffs) / len(diffs)
        wins = winsorised_mean(diffs)
        # Where the arm sits inside the null it is being judged against.
        pctile = 100.0 * sum(1 for g in gains if g < gain_pp) / len(gains)
        clears = gain_pp >= bar
        out["arms"][name] = {
            "params": arm, "n_paired": len(common), "mean_pct": 100.0 * got["mean"],
            "gain_pp": gain_pp, "null_percentile": pctile,
            "C1_clears_bar": bool(clears),
            "C2_winsorised": wins, "C2_positive": bool(wins["mean_pp"] > 0),
        }
        _log("  %-6s gain %+.4fpp  (null pctile %.0f)  bar %+.4f -> %s | winsorised %+.4fpp"
             % (name, gain_pp, pctile, bar, "CLEARS" if clears else "FAILS", wins["mean_pp"]))

    # C3 / C4 are already measured on this exact book by O1 and are read from its artifact
    # rather than re-run, so the verdict cites a banked number instead of a fresh one.
    if os.path.exists(O1_ARTIFACT):
        with open(O1_ARTIFACT, "r", encoding="utf-8") as f:
            o1 = json.load(f)
        c34 = {"source": os.path.basename(O1_ARTIFACT),
               "pbo_signal": (o1.get("pbo_signal") or {}).get("pbo"),
               "pbo_random": (o1.get("pbo_random") or {}).get("pbo")}
        for k in CANDIDATES:
            sig, rnd = o1["signal"][k], o1["random"][k]
            c34[k] = {
                # C3 — the gain must hold on the five pooled random-entry seeds.
                "C3_random_gain_pp": 100.0 * rnd["vs_shipped"]["expectancy_diff"],
                "C3_signal_gain_pp": 100.0 * sig["vs_shipped"]["expectancy_diff"],
                # C4 — FDR discovery, both halves positive, both entry sets positive.
                "C4_fdr_discovery": (o1.get("fdr") or {}).get(k, {}).get("discovery"),
                "C4_sign_z_signal": sig["vs_shipped"]["paired"]["sign_z"],
                "C4_sign_z_random": rnd["vs_shipped"]["paired"]["sign_z"],
                "C4_holdout_signal": sig["held_out"],
                "C4_holdout_random": rnd["held_out"],
            }
            c34[k]["C3_passes"] = bool(c34[k]["C3_random_gain_pp"] > 0)
            c34[k]["C4_passes"] = bool(
                c34[k]["C4_fdr_discovery"] and sig["held_out"].get("both_positive")
                and rnd["held_out"].get("both_positive")
                and c34[k]["C3_random_gain_pp"] > 0 and c34[k]["C3_signal_gain_pp"] > 0
                and (c34["pbo_signal"] or 0) < 0.50 and (c34["pbo_random"] or 0) < 0.50)
        out["C3_C4_from_O1"] = c34

    # ADOPT requires ALL FOUR pre-registered conditions. Failing any one is REJECTED; there is
    # no third state, as Don's instruction fixed it.
    for name in CANDIDATES:
        r = out["arms"][name]
        c = out.get("C3_C4_from_O1", {}).get(name, {})
        r["C3_passes"] = c.get("C3_passes")
        r["C4_passes"] = c.get("C4_passes")
        r["VERDICT"] = ("ADOPT" if (r["C1_clears_bar"] and r["C2_positive"]
                                    and r["C3_passes"] and r["C4_passes"]) else "REJECTED")
        r["failed_conditions"] = [c_ for c_, ok in (("C1", r["C1_clears_bar"]),
                                                    ("C2", r["C2_positive"]),
                                                    ("C3", r["C3_passes"]),
                                                    ("C4", r["C4_passes"])) if not ok]
    out["ITEM_A"] = out["arms"]["tp150"]["VERDICT"]

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    _log("wrote " + OUT_PATH)
    print("\nITEM A (tp150) -> %s   [bar %+.4fpp, gain %+.4fpp]"
          % (out["ITEM_A"], bar, out["arms"]["tp150"]["gain_pp"]))


if __name__ == "__main__":
    main()
