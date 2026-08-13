#!/usr/bin/env python3
"""S14 ADOPTION — CONSTRUCTION FIDELITY GATE.

Executes section 2 of `PREREG_s14_adoption.md` unmodified.

THE GATE: apply the LIVE book-construction entry point to the panel's most recent cross-section
and reproduce the MEASURED arm's book NAME-FOR-NAME. Exact set equality. One name of difference
fails, and on a failure the LIVE path is fixed -- the measured arm is never adjusted to meet it.

WHY IT IS BUILT THE WAY IT IS -- the vacuity problem, which is the only way this check could
lie. With no previously-held names a band has nothing to hold, so BOTH paths collapse to plain
top-N and a name-for-name comparison passes while proving nothing about the band. So the held
set here is not invented: the band is CHAINED across all 69 rebalance dates on the measured
path, exactly as `turnover_and_costs` chains it, and the gate is run at the final date against
the book the chain actually produced. The run asserts the comparison is non-vacuous -- that the
banded book DIFFERS from plain top-N at that date, and that at least one name is retained by the
band -- and ABORTS if it is not, rather than reporting a pass it did not earn.

Run:  python -m scripts.s14_construction_fidelity
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP          # noqa: E402
from valuation.edge import valquo_index as VI               # noqa: E402
from valuation.edge import no_trade_band as NTB             # noqa: E402
from valuation.screener.cross_sectional import zscore       # noqa: E402

# The measured arm, verbatim from S14 / S14-WIDTH. Not parameters of this script -- constants of
# the thing being reproduced.
THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
ENTER_FRAC = 0.10


def measured_chain(panel):
    """The measured arm's selection, chained over every date.

    Mirrors `turnover_and_costs`'s selection loop EXACTLY -- same composite function, same k,
    same exit-rank derivation, same `_band_select` object -- and carries `prev` forward the way
    that loop carries `prev_w`. Returns per-date books plus the held set entering each date.

    Deliberately reproduces the loop rather than calling `turnover_and_costs`, because that
    function returns performance aggregates and not the BOOK, and the book is what the gate
    compares. The reproduction is checked by the identity assertions in `main`.
    """
    dates = sorted(panel["date"].unique())
    prev, out = set(), []
    for d in dates:
        sub = panel[panel["date"] == d]
        if len(sub) < 20:
            continue
        comp = FP.composite_from_frame(sub, THEMES, {c: W for c in THEMES}, zscore)
        all_t = sub["ticker"].values
        k = max(1, int(len(sub) * ENTER_FRAC))
        xr = FP._exit_rank_for(len(sub), k, NTB.BAND_WIDTH)
        sel = FP._band_select(comp, all_t, set(prev), k, xr)
        plain = [all_t[j] for j in np.argsort(-comp)[:k]]
        out.append({"date": d, "sub": sub, "comp": comp, "all_t": all_t, "k": k,
                    "exit_rank": xr, "held_in": set(prev), "book": list(sel),
                    "plain_top_n": list(plain)})
        prev = set(sel)
    return out


def live_book(step):
    """The LIVE entry point, on the panel's cross-section.

    Calls `valquo_index.build_index` -- the function a real scan calls -- rather than the band
    rule directly. That is the point: a test that calls the same rule with the same arguments
    passes by construction, whereas this fails if the live path drops the band, mis-derives the
    exit rank, or fails to thread the held set.

    `large_cap_min=0` and an explicit `top_n` are supplied so the comparison ISOLATES THE BAND.
    The live book-size rule (`int(round(...))` with a MIN_NAMES floor) differs from the panel's
    (`int(...)`), which is a real and pre-existing divergence -- it is measured and reported
    separately by `book_size_divergence` rather than being allowed to contaminate this gate.
    """
    rows = [{"ticker": t, "hot_score": float(c), "price": 1.0, "market_cap": 1e12}
            for t, c in zip(step["all_t"], step["comp"]) if np.isfinite(c)]
    payload = VI.build_index(rows, large_cap_min=0.0, top_n=step["k"],
                             weighting="equal", held=step["held_in"],
                             exit_frac=NTB.BAND_WIDTH)
    return payload


def book_size_divergence(panel, steps):
    """A SEPARATE, PRE-EXISTING divergence, reported rather than folded into the gate.

    The panel truncates (`int(len(sub) * 0.10)`); the live default rounds and applies a
    MIN_NAMES floor (`max(10, int(round(len(large) * 0.10)))`). On any cross-section whose size
    is not a multiple of ten these disagree by one name. This predates the band and is not
    something S14 changed, but a name-for-name gate would blame the band for it, so it is
    measured on its own.
    """
    rows = []
    for s in steps:
        n_uni = len(s["sub"])
        live_n = max(VI.MIN_NAMES, int(round(n_uni * VI.TOP_DECILE)))
        if live_n != s["k"]:
            rows.append({"date": str(s["date"]), "n_universe": int(n_uni),
                         "panel_k": int(s["k"]), "live_n": int(live_n),
                         "delta": int(live_n - s["k"])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=r"C:/Users/donni/Downloads/valuation-tool/data/"
                                       r"free_analysis/panel_corrected_69d.pkl")
    ap.add_argument("--json", default="data/free_analysis/S14_CONSTRUCTION_FIDELITY.json")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel, "rb"))
    print(f"[fid] panel {panel.shape}, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names")
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, "SMOKE-TEST PANEL"

    out = {"gate": "construction fidelity - live book reproduces the measured arm name-for-name",
           "width": NTB.BAND_WIDTH, "controls": {}}

    # ---- C0: the rule is ONE OBJECT, not two equivalent implementations -------------------
    out["controls"]["rule_is_one_object"] = {
        "band_select_identity": FP._band_select is NTB.band_select,
        "exit_rank_identity": FP._exit_rank_for is NTB.exit_rank_for}
    assert FP._band_select is NTB.band_select, "the panel is not using the shared rule"

    steps = measured_chain(panel)
    print(f"[fid] chained {len(steps)} dates")
    last = steps[-1]

    # ---- C1: NON-VACUITY. Without this the gate can pass while proving nothing ------------
    banded, plain = set(last["book"]), set(last["plain_top_n"])
    retained = NTB.held_within_band(last["comp"], last["all_t"], last["held_in"],
                                    last["k"], last["exit_rank"])
    out["controls"]["non_vacuous"] = {
        "date": str(last["date"]), "n_universe": int(len(last["sub"])),
        "k": int(last["k"]), "exit_rank": int(last["exit_rank"]),
        "n_held_entering": len(last["held_in"]),
        "banded_vs_plain_differs": banded != plain,
        "n_names_band_changed": len(banded ^ plain) // 2,
        "n_band_retained": len(retained)}
    assert banded != plain, "VACUOUS: the banded book equals plain top-N; the gate proves nothing"
    assert retained, "VACUOUS: no name is retained by the band at the gate date"

    # ---- THE GATE ------------------------------------------------------------------------
    live = live_book(last)
    live_names = [p["ticker"] for p in live["positions"]]
    measured_names = list(last["book"])
    same = set(live_names) == set(measured_names)
    out["gate_result"] = {
        "n_measured": len(measured_names), "n_live": len(live_names),
        "identical_set": same,
        "in_measured_not_live": sorted(set(measured_names) - set(live_names)),
        "in_live_not_measured": sorted(set(live_names) - set(measured_names)),
        "identical_order": live_names == measured_names,
        "live_band_applied": live["no_trade_band"]["applied"],
        "live_exit_rank": live["no_trade_band"]["exit_rank"],
        "live_n_band_retained": live["no_trade_band"]["n_band_retained"],
        "retained_sets_match": (set(live["no_trade_band"]["band_retained"]) == set(retained)),
        "verdict": "PASS" if same else "FAIL"}

    # Every date, not just the last -- one cross-section could agree by luck.
    all_dates = []
    for s in steps:
        lb = live_book(s)
        ln = {p["ticker"] for p in lb["positions"]}
        all_dates.append({"date": str(s["date"]), "match": ln == set(s["book"]),
                          "n": len(s["book"])})
    n_bad = sum(1 for r in all_dates if not r["match"])
    out["gate_all_dates"] = {"n_dates": len(all_dates), "n_mismatched": n_bad,
                             "mismatches": [r for r in all_dates if not r["match"]][:10],
                             "verdict": "PASS" if n_bad == 0 else "FAIL"}

    # ---- Reported separately, NOT part of the gate ----------------------------------------
    out["book_size_divergence"] = {
        "note": ("pre-existing: the panel truncates the decile, the live default rounds and "
                 "floors at MIN_NAMES. Not caused by the band and not fixed here."),
        "n_dates_differing": len(book_size_divergence(panel, steps)),
        "n_dates_total": len(steps),
        "examples": book_size_divergence(panel, steps)[:5]}

    # Exact ties would make argsort order implementation-dependent between the two paths.
    ties = int(len(last["comp"]) - len(np.unique(last["comp"][np.isfinite(last["comp"])])))
    out["controls"]["exact_composite_ties_at_gate_date"] = ties

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    g, ga = out["gate_result"], out["gate_all_dates"]
    print(f"\n[fid] GATE (most recent cross-section): {g['verdict']}")
    print(f"      measured {g['n_measured']} names, live {g['n_live']}, "
          f"identical set {g['identical_set']}, identical order {g['identical_order']}")
    print(f"      band applied live: {g['live_band_applied']}, "
          f"retained sets match: {g['retained_sets_match']}")
    print(f"[fid] GATE (all {ga['n_dates']} dates): {ga['verdict']}, "
          f"{ga['n_mismatched']} mismatched")
    print(f"[fid] non-vacuity: band changed {out['controls']['non_vacuous']['n_names_band_changed']} "
          f"names vs plain top-N, retained {out['controls']['non_vacuous']['n_band_retained']}")
    print(f"[fid] book-size divergence (reported, not gated): "
          f"{out['book_size_divergence']['n_dates_differing']} of "
          f"{out['book_size_divergence']['n_dates_total']} dates")
    print(f"[fid] exact composite ties at gate date: {ties}")
    print(f"[fid] -> {args.json}")
    return 0 if (g["verdict"] == "PASS" and ga["verdict"] == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
