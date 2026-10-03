# -*- coding: utf-8 -*-
"""INDEX-BEST diagnostics: stickiness, the size tilt, conformance and capacity. ZERO TRIALS.

Runs AFTER the arms and adds no arm. Everything here is a DESCRIPTION of books already scored --
it carries no verdict and cannot change the registered pick (void condition 2). It exists
because three of the four arms win and the register requires that a win be reported with what
would make a reader distrust it:

  * `B17` -- the top-25 book is the noisiest number this project publishes, so arm 3's
    stability is reported rather than assumed;
  * the 30% band is ~18x arm 3's book against ~3x arm 1's, so a win driven by a near-frozen
    book has to be visible (`S14-WIDTH` measured a book FREEZING at a wide enough band);
  * Don's ruling allows smaller companies to win, so HOW MUCH SMALLER is required output and
    the cost and capacity that come with it are the price of that win.
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
from valuation.edge.valquo_index import (CONTRACT_MIN_POSITIONS, LARGE_CAP_MIN,  # noqa: E402
                                         MAX_WEIGHT, conformance)
from valuation.edge.fundamental_panel import (composite_from_frame,      # noqa: E402
                                              one_way_cost_bps)
from valuation.screener.cross_sectional import zscore                    # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT           # noqa: E402
from scripts.index_best import (ARMS, LIQUID_N, _data_root,  # noqa: E402
                                data_candidates)

# Import must never raise on a runner with no licensed data -- see index_best._data_root.
DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "INDEX_BEST_DIAG.json") if FA else None
# P1's measured figure for the shape arm 3 is, quoted rather than re-derived.
P1_TOP25_BPS_AT_1M = 87.0


def main() -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    dates = sorted(panel["date"].unique())
    adv = pd.read_pickle(os.path.join(FA, "B13_ADV_PANEL.pkl"))
    adv["date"] = adv["date"].astype(str)
    advmap = {(r.date, r.ticker): r.adv for r in adv.itertuples()}

    res = {"item": "INDEX-BEST", "pass": "diagnostics", "trials": 0, "arms": {}}
    for name, kw, label, buildable in ARMS:
        bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
        prev, overlaps, sizes, caps, advs, costs, confs, maxw = set(), [], [], [], [], [], [], []
        for d in dates:
            g = panel[panel["date"] == d]
            if len(g) < 20:
                continue
            comp = composite_from_frame(g, cols, weights, zscore)
            w = bf(g, comp, prev)
            if not w:
                continue
            cur = set(w)
            if prev:
                overlaps.append(len(cur & prev) / max(1, len(cur)))
            prev = cur
            sizes.append(len(cur))
            mw = max(w.values())
            maxw.append(mw)
            confs.append(bool(conformance(len(cur), max(MAX_WEIGHT, 1.0 / len(cur)),
                                          len(g)).get("conforms")))
            mc = dict(zip(g["ticker"].values, g["market_cap"].values))
            cm = [mc.get(t) for t in cur if mc.get(t) == mc.get(t)]
            if cm:
                caps.append(float(np.median(cm)))
                costs.append(float(np.mean([one_way_cost_bps(mc.get(t)) for t in cur])))
            av = [advmap.get((str(d), t)) for t in cur]
            av = [x for x in av if x is not None and x == x]
            if len(av) >= max(5, len(cur) // 2):
                advs.append(float(np.median(av)))

        a = {"label": label, "buildable_from_live_scan": buildable,
             "book_size": {"min": int(min(sizes)), "median": float(np.median(sizes)),
                           "max": int(max(sizes))},
             "period_to_period_overlap": {
                 "n": len(overlaps), "min": float(np.min(overlaps)),
                 "median": float(np.median(overlaps)), "max": float(np.max(overlaps))},
             "median_market_cap_usd": {"min": float(np.min(caps)),
                                       "median": float(np.median(caps)),
                                       "max": float(np.max(caps))},
             "mean_modelled_cost_bps": float(np.mean(costs)),
             "median_book_dollar_adv_usd": (float(np.median(advs)) if advs else None),
             "adv_dates_scored": len(advs),
             "contract_conformant_dates": int(sum(confs)),
             "contract_min_positions": CONTRACT_MIN_POSITIONS,
             "max_weight_seen": float(np.max(maxw)),
             }
        res["arms"][name] = a
        print("%-20s book %d/%.0f/%d | overlap med %.3f | med cap $%.2fbn | cost %.1f bps | "
              "ADV $%.1fm | conformant %d/%d"
              % (name, a["book_size"]["min"], a["book_size"]["median"], a["book_size"]["max"],
                 a["period_to_period_overlap"]["median"],
                 a["median_market_cap_usd"]["median"] / 1e9, a["mean_modelled_cost_bps"],
                 (a["median_book_dollar_adv_usd"] or 0) / 1e6,
                 a["contract_conformant_dates"], len(confs)), flush=True)

    # Capacity: at what AUM does a 1% participation cap on the MEDIAN name bind, per `P1`'s
    # shape. An UPPER BOUND -- `P1`'s own caveat, because the ADV sources are survivor-biased.
    for name, a in res["arms"].items():
        if a["median_book_dollar_adv_usd"]:
            a["capacity_note"] = (
                "median book name trades $%.1fm/day; at a 1%% participation cap and a %d-name "
                "equal-ish book, one day's full rebalance of the whole book is ~$%.0fm. UPPER "
                "BOUND (P1): the ADV sources are survivor-biased."
                % (a["median_book_dollar_adv_usd"] / 1e6, a["book_size"]["median"],
                   a["median_book_dollar_adv_usd"] * 0.01 * a["book_size"]["median"] / 1e6))
    res["p1_reference"] = ("P1 measured %.0f bps at $1M on the top-25 all-cap book against "
                           "33.4 bps on the decile" % P1_TOP25_BPS_AT_1M)

    # ---- THE SPLIT THAT DECIDES HOW THE RESULT MAY BE DESCRIBED ---------------------------
    # Every arm's headline is measured against SPY and against arm 1, and both of those mix two
    # different things: a universe that returned more, and a composite that sorted it better.
    # `U7` and `S10` were each decided by that conflation, so it is separated here. Each arm is
    # also scored against ITS OWN universe's equal weight -- the universe it actually drew from,
    # AFTER the same trim -- so "the composite sorts this universe" is isolated from "this
    # universe went up".
    import json as _json
    best = _json.load(open(os.path.join(FA, "INDEX_BEST.json"), encoding="utf-8"))
    base_u = None
    split = {}
    for name, kw, label, _b in ARMS:
        ur, lcm = kw.get("universe_rank"), kw.get("large_cap_min")
        ew = []
        for d in dates:
            g = panel[panel["date"] == d]
            if len(g) < 20:
                continue
            gg = g[g["market_cap"] >= lcm] if lcm else g
            if ur:
                gg = gg.reindex(gg["market_cap"].sort_values(ascending=False).index[:ur])
            r = gg["fwd_ret"].values
            ew.append(float(np.nanmean(r)) if np.isfinite(r).any() else np.nan)
        pr = 4.0
        xs = [x for x in ew if x == x]
        u = float(np.prod([1.0 + x for x in xs]) ** (pr / len(xs)) - 1.0)
        if base_u is None:
            base_u = u
        roth = best["arms"][name]["roth_net_ann"]
        split[name] = {"own_universe_equal_weight_ann": u,
                       "alpha_vs_own_universe": roth - u,
                       "universe_vs_arm1_universe": u - base_u}
    a1 = split["1_incumbent_10bn"]
    a2 = split["2_liquid_decile"]
    a3 = split["3_liquid_top25"]
    split["three_way_split_of_arm3_over_arm1"] = {
        "total": best["arms"]["3_liquid_top25"]["roth_net_ann"]
                 - best["arms"]["1_incumbent_10bn"]["roth_net_ann"],
        "universe": a3["universe_vs_arm1_universe"],
        "selection_in_a_wider_universe": (a2["alpha_vs_own_universe"]
                                          - a1["alpha_vs_own_universe"]),
        "concentration_25_vs_150_of_the_SAME_universe": (a3["alpha_vs_own_universe"]
                                                         - a2["alpha_vs_own_universe"]),
        "note": "the three sum to the total by construction; the concentration term is the one "
                "B17 calls the noisiest number this project publishes",
    }
    res["universe_vs_selection"] = split
    print("\nSPLIT of arm 3 over arm 1: %s"
          % _json.dumps({k: round(v, 6) for k, v in
                         split["three_way_split_of_arm3_over_arm1"].items()
                         if isinstance(v, float)}))
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
