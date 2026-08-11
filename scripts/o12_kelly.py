"""O12 — fractional Kelly and ruin for the options paper book.

    python -m scripts.o12_kelly

Pre-registered in `PREREG_o12_kelly_ruin.md`, committed alone at b0f287d before this file
existed. The f-grid, the ruin thresholds and the 2.0 half-agreement factor are all fixed there.

THE CAVEAT TRAVELS WITH EVERY NUMBER: Kelly needs an edge that is real, and R2 says this book's
entry is dead (+3.2702%/trade against a random-entry control's +8.3342%). Nothing here is a
sizing recommendation for real money.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import kelly as K              # noqa: E402
from valuation.edge import antisignal as A         # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
OUT = os.path.join(DATA, "free_analysis", "O12_KELLY_RUIN.json")

EQUITY_GRID = (5_000, 10_000, 25_000, 50_000, 100_000, 250_000)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="O12 - fractional Kelly and ruin")
    ap.add_argument("--paths", type=int, default=K.DEFAULT_PATHS)
    ap.add_argument("--boot", type=int, default=400)
    ap.add_argument("--seed", type=int, default=12)
    args = ap.parse_args(argv)

    with open(os.path.join(UNIV, "state_r2_splitclean.pkl"), "rb") as f:
        alert = pickle.load(f)["rows"]
    ctrl = []
    for s in range(5):
        with open(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s), "rb") as f:
            ctrl.extend(pickle.load(f))

    rets = [r["pnl_pct"] for r in alert if r.get("pnl_pct") is not None]
    cret = [r["pnl_pct"] for r in ctrl if r.get("pnl_pct") is not None]
    print("[O12] alert %d  control %d" % (len(rets), len(cret)), flush=True)

    res = {"item": "O12", "register": "PREREG_o12_kelly_ruin.md",
           "book": "split_clean (U1-SPLIT 2026-08-11)",
           "caveat": ("Kelly needs a real edge; R2 says this entry is dead. Not a sizing "
                      "recommendation for real money.")}

    # ---- the distribution, restated so the artifact is self-contained -----------------------
    srt = sorted(rets)
    res["distribution"] = {
        "n": len(rets), "mean": sum(rets) / len(rets), "median": srt[len(srt) // 2],
        "hit_rate_gt0": sum(1 for x in rets if x > 0) / len(rets),
        "min": srt[0], "max": srt[-1],
        "hit_rate_note": ("measured 0.3527; the task brief's 37% does not reproduce on either "
                          "book (as-published 0.3532)"),
    }

    # ---- Q1: f*, full sample and both halves ------------------------------------------------
    full = K.kelly_fraction(rets)
    a_early, a_late = A.split_halves(alert)
    e = K.kelly_fraction([r["pnl_pct"] for r in a_early if r.get("pnl_pct") is not None])
    l = K.kelly_fraction([r["pnl_pct"] for r in a_late if r.get("pnl_pct") is not None])
    print("[O12] f* full %.4f | early %.4f (n %d) | late %.4f (n %d)"
          % (full["f_star"], e["f_star"], e["n"], l["f_star"], l["n"]), flush=True)

    blocks = K.month_blocks(alert)
    boot = K.bootstrap_f_star(blocks, len(rets), n_draws=args.boot, seed=args.seed)
    print("[O12] bootstrap f* CI95 [%.4f, %.4f] over %d draws"
          % (boot.get("p2_5", float("nan")), boot.get("p97_5", float("nan")),
             boot.get("n_draws", 0)), flush=True)

    fe, fl = e["f_star"], l["f_star"]
    ratio = (max(fe, fl) / min(fe, fl)) if (fe and fl and min(fe, fl) > 0) else None
    ci_excludes_zero = bool(boot.get("p2_5") is not None and boot["p2_5"] > 0)
    usable = bool(fe and fl and fe > 0 and l["f_star"] > 0 and ratio is not None
                  and ratio <= 2.0 and ci_excludes_zero)
    res["q1"] = {"full": full, "early": e, "late": l, "bootstrap": boot,
                 "half_ratio": ratio, "ci_excludes_zero": ci_excludes_zero,
                 "verdict": "USABLE" if usable else "NOT USABLE"}
    print("[O12] Q1 verdict: %s (half ratio %s)"
          % (res["q1"]["verdict"], ("%.2f" % ratio) if ratio else "n/a"), flush=True)

    # ---- Q2: ruin ---------------------------------------------------------------------------
    dates = sorted(str(r.get("alert_ts"))[:10] for r in alert if r.get("alert_ts"))
    yrs = max(1e-9, (int(dates[-1][:4]) + int(dates[-1][5:7]) / 12.0)
              - (int(dates[0][:4]) + int(dates[0][5:7]) / 12.0))
    per_year = len(rets) / yrs
    fs = full["f_star"]
    fracs = [("f_star", fs), ("half_kelly", fs / 2), ("quarter_kelly", fs / 4),
             ("0.01", 0.01), ("0.02", 0.02), ("0.05", 0.05), ("0.10", 0.10), ("0.25", 0.25)]
    ruin = {}
    for name, f in fracs:
        if f <= 0 or f >= full["f_max"]:
            ruin[name] = {"f": f, "skipped": "outside the defined range (f_max %.5f)"
                          % full["f_max"]}
            continue
        ruin[name] = K.ruin_profile(blocks, f, int(round(per_year)), n_paths=args.paths,
                                    seed=args.seed)
        print("[O12]   ruin f=%-6.4f  medTerm %.3f  P(dd>50%%) %.3f  P(<0.2x) %.3f"
              % (f, ruin[name]["median_terminal"], ruin[name]["p_drawdown_over_50"],
                 ruin[name]["p_terminal_below_0.2x"]), flush=True)
    res["q2_ruin"] = {"trades_per_year": per_year, "span_years": yrs,
                      "one_year_horizon": True, "profiles": ruin,
                      "verdict": "DESCRIPTIVE - no verdict, as registered"}

    # ---- Q3: what flat sizing implies -------------------------------------------------------
    prem = sorted(float(r["entry_premium"]) for r in alert if r.get("entry_premium"))
    med_prem = prem[len(prem) // 2]
    res["q3_flat_sizing"] = {
        "live_rule": "paper_contracts_per_trade = 1, plus the alert's own $1,000 budget veto",
        "median_entry_premium": med_prem,
        "dollar_stake_per_trade": med_prem * 100.0,
        "implied_fraction_by_equity": {
            str(eq): K.implied_fraction(med_prem, 1, eq) for eq in EQUITY_GRID},
        "equity_at_f_star": K.equity_for_fraction(med_prem, 1, fs),
        "equity_at_half_kelly": K.equity_for_fraction(med_prem, 1, fs / 2),
        "equity_at_quarter_kelly": K.equity_for_fraction(med_prem, 1, fs / 4),
        "verdict": "DESCRIPTIVE - no verdict, as registered",
    }

    # ---- Q4: the sensitivity that matters most ----------------------------------------------
    zc = K.kelly_fraction(K.zero_edge(rets))
    cf = K.kelly_fraction(cret)
    res["q4_sensitivity"] = {
        "alert": {"f_star": fs, "mean": full["mean_return"]},
        "control": {"f_star": cf["f_star"], "mean": cf.get("mean_return"), "n": cf["n"]},
        "zero_edge": {"f_star": zc["f_star"], "note": zc.get("note")},
    }
    print("[O12] Q4  alert f* %.4f | control f* %.4f | zero-edge f* %.4f"
          % (fs, cf["f_star"], zc["f_star"]), flush=True)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True, default=str)
    print("[O12] -> %s" % OUT, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
