# -*- coding: utf-8 -*-
"""N1 -- the small/mid-cap band book, as an `INDEX-BOOK`-class DESCRIPTION. ZERO TRIALS.

`FREE_KILLS_RESULTS.md` specifies this exactly: *"Not a register -- an `INDEX-BOOK`-class
DESCRIPTION of N1's band book, at ZERO trials, first."* One construction, every knob already
FROZEN BY THE CENSUS (cap < $5B, ADV > $5M, score-weighted, 8% cap, 0.30 band, quarterly), run as
a description -- net-of-cost return vs SPY, early/late halves, turnover, realised cost, FF5+MOM
loadings, and **NO VERDICT**.

WHY ZERO TRIALS: `INDEX-BOOK`'s reasoning verbatim -- *"re-measuring a KNOWN construction on a
KNOWN panel selects nothing"*. No hypothesis, no bar, no second arm that could have come back the
other way. Both knobs were fixed by `FREE_KILLS_CENSUS.json` BEFORE any return was scored, which
is what keeps this one construction rather than a 9-cell grid: the census swept the grid for
BUILDABILITY ONLY and never touched a return.

THE QUESTION IT ANSWERS, which is Don's: `INDEX-BOOK` measured −4.1785pp/yr sitting in the part of
the universe the served book declines to hold, for capacity reasons a Roth does not have. **Is
that premium reachable, net of cost?**

THE INSTRUMENT, AND WHY IT IS NOT THE CENSUS'S. The census scored the band on `B13_ADV_PANEL`
(CRSP), which **ends 2024-10-23 and so excluded 5 of the panel's 69 rebalance dates** -- its own
note names MC9's SEP-based ADV as *"the natural substitute"* for exactly that reason. A return
figure that must sit beside the three 2026-10-22 options has to span the SAME 69 dates they do,
so the PRIMARY instrument here is **`adv_sep.adv_series`** (validated against CRSP at 0.02% on
the median over 89,998 cells), and the CRSP reading ships beside it on its own 64 dates as a
CROSS-CHECK. Both are reported; neither is hidden.

`adv_sep.adv_series`, `adv_sep.by_cell` and `adv_sep.pit_adv_at` are CALLED, not reimplemented
(`B7`), and the window constant is `adv.ADV_WINDOW_SESSIONS` -- one definition of the live
screen's 60 sessions.
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

from valuation.studies import served_index_book as IB                     # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                       # noqa: E402
from valuation.edge.valquo_index import CONTRACT_MIN_POSITIONS, TOP_DECILE  # noqa: E402
from valuation.edge.fundamental_panel import (after_tax_backtest as at_bt,  # noqa: E402
                                              TAX_LONG_TERM as TAX_LONG,
                                              TAX_SHORT_TERM as TAX_SHORT)
from valuation.edge import adv_sep as ADVSEP                              # noqa: E402
from valuation.edge.adv import ADV_WINDOW_SESSIONS                        # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
from scripts import factor_alpha as FAC                                   # noqa: E402
from scripts.index_best import (_ann, _hac_t, _halves, data_candidates,   # noqa: E402
                                _data_root)

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "N1_BAND_BOOK.json") if FA else None
CACHE = os.path.join(FA, "N1_SEP_ADV_CELLS.pkl") if FA else None
FACTOR_DIR = os.path.join(DATA, "factors", "parsed") if DATA else None

# ---- THE CENSUS'S FROZEN KNOBS. Read from FREE_KILLS_CENSUS.json rather than retyped, so a
# ---- drift in the census shows up here instead of being silently inherited.
CENSUS = os.path.join(_HERE, "FREE_KILLS_CENSUS.json")
# The census's own published counts for this band, committed as literals (`MA13`): the control
# must reproduce them or the universe builder is not the census's.
CENSUS_BAND_KEY = "cap<5B_adv>5M"
CENSUS_MEDIAN_ELIGIBLE = 506.5
CENSUS_MIN_ELIGIBLE = 437
CENSUS_MAX_ELIGIBLE = 625
CENSUS_N_DATES = 64
LAG = 1


def frozen_band():
    """(ceiling, floor) from the census, never retyped."""
    j = json.load(open(CENSUS, encoding="utf-8"))
    b = j["band"]
    assert j["N1"]["band_used"] == CENSUS_BAND_KEY, j["N1"]["band_used"]
    return float(b["ceiling_usd"]), float(b["floor_adv_usd"])


def sep_adv_cells():
    """`(ticker, date) -> adv` from MC9's raw SEP bars, via the VALIDATED instrument. Cached,
    because the roll is over 8.2M rows and this is a description nobody should have to wait for
    twice."""
    if CACHE and os.path.exists(CACHE):
        d = pd.read_pickle(CACHE)
        return d["cells"], d["sessions"], d["meta"]
    raw = pd.read_pickle(os.path.join(FA, "MC9_SEP_ADV.pkl"))
    by_ticker = raw["by_ticker"]
    ser = ADVSEP.adv_series(by_ticker)              # CALLED, not reimplemented (B7)
    cells = ADVSEP.by_cell(ser)
    sessions = sorted({d for _t, d in cells})
    meta = {"source": "MC9_SEP_ADV.pkl by_ticker", "tickers": len(by_ticker),
            "window_sessions": ADV_WINDOW_SESSIONS, "cells": len(cells),
            "sessions": len(sessions), "census": raw.get("census")}
    if CACHE:
        pd.to_pickle({"cells": cells, "sessions": sessions, "meta": meta}, CACHE)
    return cells, sessions, meta


def crsp_adv_cells():
    """The census's own instrument, for the cross-check. 64 dates by construction."""
    a = pd.read_pickle(os.path.join(FA, "B13_ADV_PANEL.pkl"))
    a["date"] = a["date"].astype(str)
    cells = {(str(r.ticker).upper(), str(r.date)[:10]): float(r.adv) for r in a.itertuples()}
    sessions = sorted({d for _t, d in cells})
    return cells, sessions, {"source": "B13_ADV_PANEL.pkl (CRSP)", "cells": len(cells),
                             "sessions": len(sessions)}


def adv_at(cells, ticker, as_of):
    """EXACT-CELL ADV lookup, and the exact cell is the CENSUS's definition rather than a
    simplification of it.

    `adv_sep.pit_adv_at` walks back to the last session STRICTLY BEFORE `as_of` with NO BOUND,
    and that is what broke the first run of this item: CRSP's ADV ends **2024-10-23**, so on the
    panel's five 2025-26 rebalance dates the walk-back happily returned an ADV from up to
    **fifteen months** earlier and the control refused. That is the vendor-cut-masquerading-as-
    coverage family -- `W-3b`'s lesson and `W-28`'s defect (a) -- and it is why the census
    EXCLUDED those five dates instead of walking back into them.

    Reproducing the census's published counts (437 / 506.5 / 625 over 64 dates) requires all
    three of its choices: the EXACT cell, the RAW panel rows, and its five excluded dates. An
    exact cell also needs no staleness parameter to justify, which is the second reason to
    prefer it: there is no bound here that a successor could quietly widen.
    """
    return cells.get((str(ticker).upper(), str(as_of)[:10]))


def band_filter(cells, ceiling, floor, counts=None):
    """The universe predicate: BELOW the cap ceiling AND ABOVE the dollar-ADV floor.

    A name with NO observable ADV is EXCLUDED, not admitted. That is the conservative direction
    and it is the one the live screen takes -- `factors.py` refuses a name whose
    `avg_dollar_volume` is below the floor, and an unobservable ADV cannot be shown to clear it.
    Admitting it would make the floor a data-availability screen that fails OPEN, which is the
    defect `S10` and `D6` both warn about. The excluded count is RECORDED per date, never
    silently absorbed.
    """
    def _f(rows, as_of):
        kept, no_adv, over_cap, under_floor = [], 0, 0, 0
        for r in rows:
            mc = r.get("market_cap")
            if mc is None or mc != mc or mc >= ceiling:
                over_cap += 1
                continue
            a = adv_at(cells, r["ticker"], as_of)
            if a is None:
                no_adv += 1
                continue
            if a <= floor:
                under_floor += 1
                continue
            kept.append(r)
        if counts is not None:
            counts.append({"date": as_of, "eligible": len(kept), "no_adv": no_adv,
                           "over_cap": over_cap, "under_floor": under_floor,
                           "scored": len(rows)})
        return kept
    return _f


def census_eligible(panel, cells, ceiling, floor, skip_dates=()):
    """The CENSUS's own count: the EXACT cell on RAW panel rows, over its own dates.

    Kept separate from the book's filter on purpose. The book can only hold names it can RANK,
    so its universe is the SCORED rows; the census counted RAW rows. Those are different
    populations and both are reported rather than conflated -- reporting only one would make a
    ~1% difference look like a reproduction failure or hide it.
    """
    out = []
    for d in sorted(panel["date"].unique()):
        ds = str(d)[:10]
        if ds in set(skip_dates):
            continue
        g = panel[panel["date"] == d]
        n = 0
        for t, mc in zip(g["ticker"].values, g["market_cap"].values):
            if mc != mc or mc >= ceiling:
                continue
            a = adv_at(cells, t, ds)
            if a is not None and a > floor:
                n += 1
        out.append({"date": ds, "eligible": n})
    return out


def main(panel_path=None, out=None, label=None) -> int:
    """`panel_path`/`out` default to the banked panel and this item's own artifact, so
    every existing caller is bit-identical. `UNIVERSE-BIAS` passes a corrected-universe
    panel rather than copying this measurement (`B7`)."""
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    ceiling, floor = frozen_band()
    panel = pd.read_pickle(panel_path or os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    print("band FROZEN BY CENSUS: cap < $%.1fbn, ADV > $%.1fm | panel %s"
          % (ceiling / 1e9, floor / 1e6, panel.shape), flush=True)

    res = {"item": "N1", "class": "INDEX-BOOK-class DESCRIPTION", "trials": 0,
           "no_verdict": "no hypothesis, no bar, no second arm -- a description, exactly as "
                         "FREE_KILLS_RESULTS.md specifies",
           "band": {"ceiling_usd": ceiling, "floor_adv_usd": floor,
                    "source": "FREE_KILLS_CENSUS.json, frozen before any return was scored"},
           "construction": {"weighting": "score", "max_weight": "8% (build_index)",
                            "band_width": BAND_WIDTH, "top_decile": TOP_DECILE,
                            "rebalance_days": 63},
           "readings": {}}

    spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0])
           for d in sorted(panel["date"].unique())]
    res["spy_ann"] = _ann(spy)

    excluded = list(json.load(open(CENSUS, encoding="utf-8"))["N1"]
                    ["excluded_dates_zero_adv_coverage"])
    res["census_excluded_dates"] = {
        "dates": excluded,
        "reason": "B13_ADV_PANEL (CRSP) ends 2024-10-23; these are the panel's rebalance dates "
                  "past the vendor cut. READ from the census artifact, not retyped. The first "
                  "run of this item walked back INTO them via `pit_adv_at` and used ADV up to "
                  "15 months stale, which is why the control refused.",
    }
    for label, loader in (("sep_primary", sep_adv_cells), ("crsp_crosscheck", crsp_adv_cells)):
        cells, sessions, meta = loader()
        skip = excluded if label == "crsp_crosscheck" else []
        sub = (panel[~panel["date"].astype(str).str[:10].isin(set(skip))]
               if skip else panel)
        print("\n=== %s | %s | dates %d" % (label, meta.get("source"),
                                            sub["date"].nunique()), flush=True)
        counts = []
        bf = IB.book_fn(large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                        universe_filter=band_filter(cells, ceiling, floor, counts))
        roth = at_bt(sub, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
                     short_rate=0.0, long_rate=0.0, return_series=True)
        n_scored_dates = len(counts)      # the eligible census from the FIRST pass only
        el = [c["eligible"] for c in counts[:n_scored_dates] if c["eligible"] > 0]
        taxd = at_bt(sub, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
                     short_rate=TAX_SHORT, long_rate=TAX_LONG, return_series=True)
        cen = IB.run(sub, cols, weights, large_cap_min=0.0, weighting="score",
                     exit_frac=BAND_WIDTH,
                     universe_filter=band_filter(cells, ceiling, floor))
        # THE CENSUS'S OWN POPULATION, separately: RAW rows, not the scored subset.
        craw = [c["eligible"] for c in census_eligible(panel, cells, ceiling, floor, skip)
                if c["eligible"] > 0]
        net = roth["series"]["net"]
        n = len(net)
        eh, lh = _halves(n)
        spy_sub = [float(sub[sub["date"] == d]["bench_ret"].iloc[0])
                   for d in sorted(sub["date"].unique())]
        spy_m = spy_sub[:n]
        r = {
            "instrument": meta,
            "excluded_dates": list(skip),
            "eligible_scored_rows": {"n_dates": len(el), "min": int(min(el)),
                                     "median": float(np.median(el)), "max": int(max(el)),
                                     "population": "rows the book can RANK (scan_rows)"},
            "eligible_raw_rows": {"n_dates": len(craw), "min": int(min(craw)),
                                  "median": float(np.median(craw)), "max": int(max(craw)),
                                  "population": "RAW panel rows -- the CENSUS's definition"},
            "excluded_for_no_observable_adv": {
                "total": int(sum(c["no_adv"] for c in counts)),
                "median_per_date": float(np.median([c["no_adv"] for c in counts]))},
            "roth_net_ann": roth["after_tax_ann"], "gross_ann": roth["gross_ann"],
            "roth_sharpe": roth["after_tax_sharpe"],
            "roth_max_drawdown": roth["after_tax_max_drawdown"],
            "taxable_after_tax_ann": taxd["after_tax_ann"],
            "tax_cost_pp": roth["after_tax_ann"] - taxd["after_tax_ann"],
            "short_term_share_of_gains": taxd["short_term_share_of_gains"],
            "spy_ann_matched": _ann(spy_m),
            "net_vs_spy": roth["after_tax_ann"] - _ann(spy_m),
            "annual_turnover": cen["annual_turnover"],
            "realised_one_way_bps": cen["realised_one_way_bps"],
            "cost_drag_ann": cen["cost_drag_ann"],
            "book_size": cen["book_size"],
            "dates_below_contract_min_positions": cen["dates_below_contract_min_positions"],
            "contract_min_positions": CONTRACT_MIN_POSITIONS,
            "n_periods": n,
        }
        for lab, idx in (("early_half", eh), ("late_half", lh)):
            ix = [i for i in idx if i < n]
            r[lab] = {"n": len(ix), "net_ann": _ann([net[i] for i in ix]),
                      "spy_ann": _ann([spy_m[i] for i in ix]),
                      "net_vs_spy": _ann([net[i] for i in ix]) - _ann([spy_m[i] for i in ix])}
        # tracking error vs SPY and the MDE the draft required printed BEFORE any reading
        ex = np.asarray([net[i] - spy_m[i] for i in range(n)], dtype=float)
        t, se = _hac_t(list(ex))
        r["vs_spy_inference"] = {
            "hac_t": t, "hac_se_per_period": se,
            "tracking_error_ann_pp": float(ex.std(ddof=1) * np.sqrt(4.0) * 100.0),
            "mde_80_ann_pp": (None if se is None else (2.0 + 0.84) * se * 4.0 * 100.0),
            "critical_value_note": "UNCALIBRATED (V2G, R1-VAR). This is NOT a paired "
                                   "within-panel difference -- it changes the row set -- so no "
                                   "calibrated floor applies and none is invented.",
        }
        res["readings"][label] = r
        print("  eligible RAW %d/%.0f/%d over %d dates | SCORED %d/%.0f/%d | book %d/%.0f/%d "
              "| below contract min %d"
              % (r["eligible_raw_rows"]["min"], r["eligible_raw_rows"]["median"],
                 r["eligible_raw_rows"]["max"], r["eligible_raw_rows"]["n_dates"],
                 r["eligible_scored_rows"]["min"], r["eligible_scored_rows"]["median"],
                 r["eligible_scored_rows"]["max"],
                 r["book_size"]["min"], r["book_size"]["median"], r["book_size"]["max"],
                 r["dates_below_contract_min_positions"]), flush=True)
        print("  roth %.4f vs SPY %.4f -> %+.4f | early %+.4f late %+.4f"
              % (r["roth_net_ann"], r["spy_ann_matched"], r["net_vs_spy"],
                 r["early_half"]["net_vs_spy"], r["late_half"]["net_vs_spy"]), flush=True)
        print("  sharpe %.4f maxDD %.4f turnover %.4f cost %.2f bps | taxable %.4f (tax %.4f)"
              % (r["roth_sharpe"], r["roth_max_drawdown"], r["annual_turnover"],
                 r["realised_one_way_bps"], r["taxable_after_tax_ann"], r["tax_cost_pp"]),
              flush=True)
        print("  vs SPY: HAC t %s | TE %.3f pp/yr | MDE80 %s"
              % (("%+.3f" % t) if t is not None else "n/a", r["vs_spy_inference"]
                 ["tracking_error_ann_pp"],
                 ("%+.3fpp" % r["vs_spy_inference"]["mde_80_ann_pp"])
                 if r["vs_spy_inference"]["mde_80_ann_pp"] else "n/a"), flush=True)

    # ---- CONTROL: the CRSP reading must reproduce the census's own eligible counts ----------
    c = res["readings"]["crsp_crosscheck"]["eligible_raw_rows"]
    res["control_vs_census"] = {
        "published": {"median": CENSUS_MEDIAN_ELIGIBLE, "min": CENSUS_MIN_ELIGIBLE,
                      "max": CENSUS_MAX_ELIGIBLE, "n_dates": CENSUS_N_DATES},
        "reproduced": c,
        "median_abs_dev": abs(c["median"] - CENSUS_MEDIAN_ELIGIBLE),
        "pass": bool(c["median"] == CENSUS_MEDIAN_ELIGIBLE
                     and c["min"] == CENSUS_MIN_ELIGIBLE
                     and c["max"] == CENSUS_MAX_ELIGIBLE),
        "note": "the census scored this band on CRSP over 64 dates; reproducing its counts is "
                "what proves this universe builder is the census's and not a lookalike",
    }
    print("\nCONTROL vs census (CRSP, 64 dates): median %.1f vs %.1f | min %d vs %d | max %d vs "
          "%d -> %s" % (c["median"], CENSUS_MEDIAN_ELIGIBLE, c["min"], CENSUS_MIN_ELIGIBLE,
                        c["max"], CENSUS_MAX_ELIGIBLE,
                        "PASS" if res["control_vs_census"]["pass"] else "DOES NOT REPRODUCE"),
          flush=True)

    # ---- FF5+MOM, R1's machinery, on the PRIMARY reading -----------------------------------
    FAC.set_factor_dir(FACTOR_DIR)
    grid = sorted(panel["date"].unique())
    F = FAC.factor_windows(grid)
    bf = IB.book_fn(large_cap_min=0.0, weighting="score", exit_frac=BAND_WIDTH,
                    universe_filter=band_filter(sep_adv_cells()[0], ceiling, floor))
    y = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
              short_rate=0.0, long_rate=0.0, return_series=True)["series"]["net"]
    m = min(len(F), len(y))
    F = F.iloc[:m].reset_index(drop=True)
    yv = np.asarray(y[:m], dtype=float) - F["RF"].values
    bench = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid][:m]
    v = pd.DataFrame({"bench": bench, "MKT": F["MKT"].values, "RF": F["RF"].values}).dropna()
    b = FAC.ols_nw((v["bench"] - v["RF"]).values, v[["MKT"]].values, lag=LAG)
    res["factors"] = {
        "model": list(FAC.FF_MODEL), "lag": LAG, "n_windows": int(m),
        "alignment_control": {"spy_on_mkt_beta": float(b["beta"][1]), "r2": float(b["r2"])},
        "excess_of_rf": FAC.regress(yv, F, list(FAC.FF_MODEL), "N1 band book", lag=LAG),
        "no_alpha_verdict": "a DESCRIPTION. The intercept is reported as a decomposition and is "
                            "not called alpha -- this item has no bar and takes no verdict.",
    }
    r = res["factors"]["excess_of_rf"]
    print("\nFF5+MOM (in excess of RF), %d windows | alignment beta %.4f R2 %.4f"
          % (m, b["beta"][1], b["r2"]), flush=True)
    print("  intercept %+.4f/yr  t %+.3f  R2 %.4f" % (r["alpha_ann"], r["alpha_t_nw"], r["r2"]),
          flush=True)
    print("  " + "  ".join("%s %+.3f(t%+.2f)" % (c2, r["loadings"][c2]["beta"],
                                                 r["loadings"][c2]["t"])
                           for c2 in FAC.FF_MODEL), flush=True)

    # a run on a non-default panel must SAY so in its own artifact, or a reader of
    # the file cannot tell which universe it describes.
    res["panel"] = os.path.basename(panel_path or "panel_corrected_69d.pkl")
    res["universe_label"] = label or "incumbent data/backtest universe"
    dest = out or OUT
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nwrote", dest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
