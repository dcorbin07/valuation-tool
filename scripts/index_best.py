# -*- coding: utf-8 -*-
"""INDEX-BEST -- which construction should the Valquo Index be? Executes PREREG_index_best.md.

Don's ruling 2026-10-03: the Index is whatever construction gives the best NET-OF-TRADING-COST
return in a Roth. Taxable figures are transparency only and may not pick.

FOUR ARMS, ONE KNOB APART, ALL FOUR CALLING `build_index` (`B7`). Arm 1 charges zero trials and
is the fidelity gate; arms 2, 3 and 4 were booked at `b86e0f9` before this file existed.

BOTH TAX TREATMENTS COME FROM ONE `after_tax_backtest` LOT PATH with the rates as the only knob,
and the PAIRED test reads the SAME computation's per-period series -- so a book's reported level
and its pairing against the incumbent can never describe two slightly different objects.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import served_index_book as IB                    # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                      # noqa: E402
from valuation.edge.valquo_index import LARGE_CAP_MIN                    # noqa: E402
from valuation.edge.fundamental_panel import (after_tax_backtest as at_bt,  # noqa: E402
                                              TAX_LONG_TERM as TAX_LONG,
                                              TAX_SHORT_TERM as TAX_SHORT)
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT           # noqa: E402

PER_YEAR = 4.0
LIQUID_N = 1500                       # the register's universe size for arms 2 and 3
CONCENTRATED_N = 25                   # arm 3's book size
# INDEX_BOOK.json's A_served, committed as literals so a drift shows as a diff here (`MA13`).
#
# THE FIRST CUT OF THESE WAS FABRICATED AND THE GATE CAUGHT IT. I typed plausible-looking digits
# from memory instead of copying the artifact, and the run refused at 1.795e-07 rather than
# proceeding. That is the committed-literal idiom working exactly as intended -- on its author --
# and it is the reason the gate demands 0.000e+00 rather than a tolerance: a tolerance of 1e-6
# would have swallowed invented numbers and scored four arms against a comparator nobody checked.
GATE = {"net_ann": 0.17181671234700224, "net_sharpe": 1.0318455238307307,
        "annual_turnover": 2.4372450827338139}


def _data_root():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(_HERE, "data"))
    parts = _HERE.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    for c in out:
        if os.path.exists(os.path.join(c, "free_analysis", "panel_corrected_69d.pkl")):
            return c
    raise FileNotFoundError("no data root; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
OUT = os.path.join(FA, "INDEX_BEST.json")

ARMS = [
    ("1_incumbent_10bn", dict(large_cap_min=LARGE_CAP_MIN, universe_rank=None, top_n=None),
     "$10B tier, top decile -- THE INCUMBENT", True),
    ("2_liquid_decile", dict(large_cap_min=0.0, universe_rank=LIQUID_N, top_n=None),
     "top %d by point-in-time market cap, top decile" % LIQUID_N, True),
    ("3_liquid_top25", dict(large_cap_min=0.0, universe_rank=LIQUID_N, top_n=CONCENTRATED_N),
     "top %d by point-in-time market cap, top %d" % (LIQUID_N, CONCENTRATED_N), True),
    ("4_all_cap_ceiling", dict(large_cap_min=0.0, universe_rank=None, top_n=None),
     "the whole scored cross-section, top decile -- A CEILING", False),
]


def _ann(xs):
    xs = [x for x in xs if x == x]
    return None if not xs else float(np.prod([1.0 + x for x in xs]) ** (PER_YEAR / len(xs)) - 1.0)


def _hac_t(d, lag=1):
    """Newey-West t on the mean of a paired difference series. The critical value this is read
    against is UNCALIBRATED (`V2G`, `R1-VAR`): no calibrated floor exists for a paired
    within-panel difference, and none is invented here."""
    a = np.asarray([x for x in d if x == x], dtype=float)
    n = len(a)
    if n < 5:
        return None, None
    mu = a.mean()
    e = a - mu
    g0 = float(e @ e) / n
    s = g0
    for k in range(1, lag + 1):
        gk = float(e[k:] @ e[:-k]) / n
        s += 2.0 * (1.0 - k / (lag + 1.0)) * gk
    # THE FLOOR IS RELATIVE, AND THIS IS THE FIFTH TIME THIS RECORD HAS HIT THE SAME DEFECT --
    # the second in two consecutive items by me. `s <= 0` is a VALUE-DEPENDENT test: a constant
    # difference series gives s ~ 1e-34 rather than exactly zero, so an absolute test misses and
    # this returns ~1.8e16 -- a confident, enormous, meaningless t, on the very statistic the
    # pick rule's halves are read against. `SECTOR-NEUTRAL-B6`'s `zscore`, `U2`'s `theme_ic`,
    # `MA58`'s `_tstat` and `INDEX-BOOK`'s `_sharpe` are the others. Found by the test again.
    scale = max(1.0, float(np.abs(a).max())) ** 2
    if s <= 1e-24 * scale:
        return None, None
    se = (s / n) ** 0.5
    return float(mu / se), float(se)


def _halves(n):
    """The register's split: median, with the BOUNDARY PERIOD EMBARGOED."""
    mid = n // 2
    return list(range(0, mid)), list(range(mid + 1, n))


def main() -> int:
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    print("panel %s | %d dates | %d themes at %.4f"
          % (panel.shape, panel["date"].nunique(), len(cols), BASE_WEIGHT), flush=True)

    # ---- GATE: arm 1 must reproduce INDEX-BOOK exactly, or nothing is read ----------------
    g = IB.run(panel, cols, weights, large_cap_min=LARGE_CAP_MIN, weighting="score",
               exit_frac=BAND_WIDTH)
    dev = {k: abs(g[k] - v) for k, v in GATE.items()}
    ok = all(v == 0.0 for v in dev.values()) and g["n_periods"] == 69
    print("GATE arm 1 vs INDEX-BOOK: %s | n_periods %d"
          % (" ".join("%s %.3e" % (k, v) for k, v in dev.items()), g["n_periods"]), flush=True)
    if not ok:
        raise SystemExit("GATE FAILED -- arm 1 is not the object INDEX-BOOK measured; abort")
    print("GATE PASS (max |delta| 0.000e+00)\n", flush=True)

    spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0])
           for d in sorted(panel["date"].unique())]
    spy_ann = _ann(spy)

    res = {"item": "INDEX-BEST", "register": "PREREG_index_best.md", "trials": 3,
           "ruling": "Don 2026-10-03 -- best NET-OF-COST return in a Roth; taxable is "
                     "transparency only and may not pick",
           "gate": {"literals": GATE, "abs_dev": dev, "pass": True},
           "spy_ann": spy_ann, "rates": {"short": TAX_SHORT, "long": TAX_LONG},
           "arms": {}}

    for name, kw, label, buildable in ARMS:
        print("=== %s  (%s)" % (name, label), flush=True)
        bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
        roth = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
                     short_rate=0.0, long_rate=0.0, return_series=True)
        taxd = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
                     short_rate=TAX_SHORT, long_rate=TAX_LONG, return_series=True)
        cen = IB.run(panel, cols, weights, weighting="score", exit_frac=BAND_WIDTH, **kw)
        a = {
            "label": label, "buildable_from_live_scan": buildable, "knobs": kw,
            "roth_net_ann": roth["after_tax_ann"], "gross_ann": roth["gross_ann"],
            "roth_sharpe": roth["after_tax_sharpe"],
            "roth_max_drawdown": roth["after_tax_max_drawdown"],
            "taxable_after_tax_ann": taxd["after_tax_ann"],
            "taxable_sharpe": taxd["after_tax_sharpe"],
            "taxable_max_drawdown": taxd["after_tax_max_drawdown"],
            "tax_cost_pp": roth["after_tax_ann"] - taxd["after_tax_ann"],
            "short_term_share_of_gains": taxd["short_term_share_of_gains"],
            "roth_excess_vs_spy": roth["after_tax_ann"] - spy_ann,
            "annual_turnover": cen["annual_turnover"],
            "realised_one_way_bps": cen["realised_one_way_bps"],
            "cost_drag_ann": cen["cost_drag_ann"],
            "book_size": cen["book_size"], "eligible_tier": cen["eligible_tier"],
            "dates_below_contract_min_positions": cen["dates_below_contract_min_positions"],
            "tilt_values": cen["tilt_values"],
            "dates_on_the_fallback": cen["dates_on_the_fallback"],
            "cap_binds_on_dates": cen["cap_binds_on_dates"],
            "net_series": roth["series"]["net"],
        }
        res["arms"][name] = a
        print("  roth %.4f (vs SPY %+.4f) | taxable %.4f | tax cost %.4f"
              % (a["roth_net_ann"], a["roth_excess_vs_spy"], a["taxable_after_tax_ann"],
                 a["tax_cost_pp"]), flush=True)
        print("  sharpe %.4f | maxDD %.4f | turnover %.4f | %.2f bps | book %d/%.0f/%d"
              % (a["roth_sharpe"], a["roth_max_drawdown"], a["annual_turnover"],
                 a["realised_one_way_bps"], a["book_size"]["min"],
                 a["book_size"]["median"], a["book_size"]["max"]), flush=True)

    # ---- PAIRED against arm 1, both halves, boundary embargoed ----------------------------
    base = res["arms"]["1_incumbent_10bn"]["net_series"]
    n = len(base)
    eh, lh = _halves(n)
    res["halves"] = {"n_periods": n, "early_idx": [eh[0], eh[-1]],
                     "late_idx": [lh[0], lh[-1]], "embargoed_index": n // 2}
    for name in res["arms"]:
        if name == "1_incumbent_10bn":
            continue
        a = res["arms"][name]
        s = a["net_series"]
        m = min(len(s), n)
        d = [s[i] - base[i] for i in range(m)]
        t_full, se_full = _hac_t(d)
        rho = float(np.corrcoef(np.asarray(s[:m]), np.asarray(base[:m]))[0, 1])
        pair = {"n": m, "mean_per_period": float(np.mean(d)),
                "ann_difference": _ann(s[:m]) - _ann(base[:m]),
                "hac_t_full": t_full, "paired_hac_se": se_full,
                "correlation_with_arm1": rho,
                "critical_value_note": "UNCALIBRATED -- no calibrated floor exists for a paired "
                                       "within-panel difference (V2G, R1-VAR)"}
        if se_full:
            pair["mde_50_ann_pp"] = 2.0 * se_full * PER_YEAR * 100
            pair["mde_80_ann_pp"] = (2.0 + 0.84) * se_full * PER_YEAR * 100
            pair["observed_over_mde80"] = abs(pair["ann_difference"] * 100) / pair["mde_80_ann_pp"]
        for lab, idx in (("early", eh), ("late", lh)):
            ds = [s[i] - base[i] for i in idx if i < m]
            t, se = _hac_t(ds)
            pair[lab] = {"n": len(ds), "ann_difference": _ann([s[i] for i in idx if i < m])
                         - _ann([base[i] for i in idx if i < m]),
                         "hac_t": t, "paired_hac_se": se}
        pair["beats_arm1_in_both_halves"] = bool(
            pair["early"]["ann_difference"] > 0 and pair["late"]["ann_difference"] > 0)
        a["paired_vs_arm1"] = pair
        print("PAIRED %-20s ann %+.4f | t %s | early %+.4f late %+.4f | both halves %s"
              % (name, pair["ann_difference"],
                 ("%+.4f" % t_full) if t_full is not None else "n/a",
                 pair["early"]["ann_difference"], pair["late"]["ann_difference"],
                 pair["beats_arm1_in_both_halves"]), flush=True)

    # ---- THE PICK RULE, applied exactly as registered -------------------------------------
    qual = [k for k, a in res["arms"].items()
            if k != "1_incumbent_10bn" and a["paired_vs_arm1"]["beats_arm1_in_both_halves"]
            and a["buildable_from_live_scan"]]
    winner = (max(qual, key=lambda k: res["arms"][k]["roth_net_ann"]) if qual
              else "1_incumbent_10bn")
    ranked = sorted(res["arms"], key=lambda k: -res["arms"][k]["roth_net_ann"])
    res["pick"] = {
        "rule": "highest net Roth return among arms beating arm 1 in BOTH halves AND buildable "
                "from the live scan; ties to the incumbent; otherwise arm 1 stands",
        "qualifying": qual, "winner": winner,
        "ranked_by_roth_net": [(k, res["arms"][k]["roth_net_ann"]) for k in ranked],
        "highest_overall": ranked[0],
        "highest_overall_is_buildable": res["arms"][ranked[0]]["buildable_from_live_scan"],
        "arm1_stands": winner == "1_incumbent_10bn",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nRANKED by net Roth: %s" % ", ".join("%s %.4f" % (k, v)
                                                 for k, v in res["pick"]["ranked_by_roth_net"]))
    print("QUALIFYING: %s" % (qual or "NONE"))
    print("WINNER: %s%s" % (winner, "  (ARM 1 STANDS)" if res["pick"]["arm1_stands"] else ""))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
