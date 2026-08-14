#!/usr/bin/env python3
"""R4 + X1 — multiple-testing accounting, and the universe split.

Executes `PREREG_r4_x1_accounting_and_universe_split.md` unmodified.

  R4  the two closable bullets: Benjamini-Hochberg across the EQUITY signal family, and the
      Harvey-Liu-Zhu hurdle REPORTED beside the headline instead of only used inside the
      CPCV adopt gate. Charged to INFRA - accounting over existing measurements.
  X1  split the universe by NAME rather than by DATE: the audit's own stable ticker-hash
      partition as the primary, inside a 100-random-split distribution, against a null
      rebuilt for a HALF book.

Run:  python -m scripts.r4_x1_accounting_universe --data-dir data/backtest
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import fundamental_panel as FP            # noqa: E402
from valuation.edge import research_log as RL                 # noqa: E402
from valuation.edge import statistics as ST                   # noqa: E402
from valuation.screener import settings as S                  # noqa: E402

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125
K_SPLITS = 100               # register 2.1
J_NULL = 200                 # register 2.2
BH_Q = 0.05                  # register 1.1
FRAC_HALFBOOKS = 0.80        # register 2.3 (b) - a judgement, labelled one
FRAC_BOTH = 0.64             # register 2.3 (c) - DERIVED: 0.80 ** 2
MIN_NAMES_PER_HALF = 400
SEED = 20260813

REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}
# X7's floors, reported BESIDE the half-universe null and never AS it (register 2.2, C5).
X7_FULL_UNIVERSE_LS_HAC_FLOOR = 2.2837
X7_FULL_UNIVERSE_ALPHA_MARGIN = 0.0195


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=2, default=float)


# ---------------------------------------------------------------------------------
# R4
# ---------------------------------------------------------------------------------
# DELEGATED, NOT RE-IMPLEMENTED. BH already existed three times in the options lane
# (`tickflow_signals`, `s17_event_codes`, `path_gate`); this session added the canonical
# definition to `statistics.py`, and a FOURTH copy here would be exactly the audit-B7 defect
# the shared one exists to end. The first cut of this file did carry its own copy.
_two_sided_p = ST.two_sided_p
benjamini_hochberg = ST.benjamini_hochberg


def r4_bh_equity_family(panel):
    """R4 bullet 3. The audit's analogue is the options autopsy's 126 FEATURES, not the log's
    rows - and the log has no p-value column, so BH across it is not computable at all
    (register 1.2). The equity family of FEATURES is the per-signal IC table."""
    ps = FP.per_signal_ic(panel)
    names = sorted(ps)
    rows = []
    for n in names:
        r = ps[n]
        t_plain = r.get("ic_tstat")
        t_hac = ((r.get("ic_inference") or {}).get("t"))
        rows.append({"signal": n, "median_ic": r.get("median_ic"),
                     "coverage": r.get("coverage"), "n_dates": r.get("n_dates"),
                     "ic_tstat": t_plain, "ic_t_hac": t_hac,
                     "p_plain": _two_sided_p(t_plain),
                     "p_hac": _two_sided_p(t_hac)})
    for key, pk in (("bh_reject_plain", "p_plain"), ("bh_reject_hac", "p_hac")):
        rej = benjamini_hochberg([x[pk] for x in rows], BH_Q)
        for x, v in zip(rows, rej):
            x[key] = bool(v)
    return {
        "family": "per-signal IC table (the equity analogue of the options autopsy's 126 features)",
        "q": BH_Q, "n_signals": len(rows),
        "n_discoveries_plain": sum(x["bh_reject_plain"] for x in rows),
        "n_discoveries_hac": sum(x["bh_reject_hac"] for x in rows),
        "discoveries_plain": sorted(x["signal"] for x in rows if x["bh_reject_plain"]),
        "discoveries_hac": sorted(x["signal"] for x in rows if x["bh_reject_hac"]),
        "signals": rows,
        "not_computable_across_the_LOG": (
            "RESEARCH_LOG.md records verdicts and has NO p-value column, so BH across the log "
            "is not computable and never was; reconstructing a p for 121 heterogeneous rows "
            "measured against different statistics on different universes would be an "
            "invention, not a measurement. R4's permanent residual (register 1.2)."),
    }


def r4_hlz_hurdle(headline_ls_hac):
    """R4 bullet 4. The haircut is computed by `_trials_haircut` and USED by the CPCV adopt
    gate, but nothing ever compared it to the HEADLINE. Both sides of the argument travel in
    the payload, because neither is 'the' answer (register 0b)."""
    d = RL.detail()
    by = d.get("by_domain") or {}
    n_eq = int(by.get("equity") or 0)
    hurdle = float(np.sqrt(2.0 * np.log(max(2, n_eq))))
    return {
        "statistic": "construction.long_short_tstat_nw (the HAC t this project quotes)",
        "value": float(headline_ls_hac),
        "n_trials_equity": n_eq,
        "hlz_hurdle_sqrt_2_ln_N": hurdle,
        "clears_hlz_hurdle": bool(headline_ls_hac > hurdle),
        "shortfall": float(hurdle - headline_ls_hac),
        "x7_calibrated_floor": X7_FULL_UNIVERSE_LS_HAC_FLOOR,
        "clears_x7_calibrated_floor": bool(headline_ls_hac > X7_FULL_UNIVERSE_LS_HAC_FLOOR),
        "by_domain": by,
        "unified_domain_is_declared_but_zero": bool((by.get("unified") or 0) == 0),
        "trials_logged_all_domains": d.get("trials_logged"),
        "audit_estimate": d.get("audit_estimate"),
        "gap_to_audit_estimate": d.get("gap_to_audit_estimate"),
        "THE_TENSION": (
            "The project CLEARS the bar measured against its own placebo (X7's calibrated "
            "2.2837) and FAILS the bar derived from counting its own trials (HLZ at the honest "
            "N). Both ship; neither is presented as the answer. The counter-argument, "
            "registered before the run: HLZ prices the BEST OF N draws, and the shipped "
            "composite is not the best of anything - flat 1/7, never tuned, cpcv.adopt false "
            "on every run - so the trials are overwhelmingly REJECTED ALTERNATIVES to it "
            "rather than candidates it won against."),
    }


# ---------------------------------------------------------------------------------
# X1
# ---------------------------------------------------------------------------------
def stable_key_half(ticker: str) -> int:
    """The audit's own construction: 'a stable key - a hash of the ticker'. No seed, no row
    order, no panel sort - reproducible by anyone holding the ticker list."""
    return int(hashlib.sha1(str(ticker).encode("utf-8")).hexdigest(), 16) % 2


def _score(panel, names):
    sub = panel[panel["ticker"].isin(names)]
    if sub["ticker"].nunique() < MIN_NAMES_PER_HALF:
        return None
    r = FP.quantile_backtest(sub, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    if not isinstance(r, dict) or r.get("top_decile_alpha") is None:
        return None
    return {"top_decile_alpha": float(r["top_decile_alpha"]),
            "long_short_tstat": float(r.get("long_short_tstat") or np.nan),
            "long_short_tstat_nw": float(r.get("long_short_tstat_nw") or np.nan),
            "monotonicity": float(r.get("monotonicity") or np.nan),
            "n_names": int(sub["ticker"].nunique()), "n_rows": int(len(sub))}


def _assert_split(a, b, universe):
    """C2: exhaustive, disjoint, balanced - asserted per split, not spot-checked."""
    A, B, U = set(a), set(b), set(universe)
    assert not (A & B), "split halves overlap"
    assert A | B == U, "split is not exhaustive"
    assert abs(len(A) - len(B)) <= 1, f"halves differ by {abs(len(A)-len(B))}"


def half_universe_null(panel, universe, rng, j=J_NULL):
    """The bar, rebuilt for a HALF book. Each draw: a random half, then placebo_panel shuffles
    the theme columns within date and quantile_backtest RECOMPUTES the composite from them -
    which is why this is a real null. X7's floors calibrate a FULL-universe decile book of
    twice the size and are reported beside this, never as it."""
    alphas, lst = [], []
    uni = np.array(sorted(universe))
    for i in range(j):
        idx = rng.permutation(len(uni))
        half = set(uni[idx[: len(uni) // 2]])
        sub = panel[panel["ticker"].isin(half)]
        pb = FP.placebo_panel(sub, seed=int(rng.integers(0, 2**31 - 1)))
        r = FP.quantile_backtest(pb, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
        if not isinstance(r, dict) or r.get("top_decile_alpha") is None:
            continue
        alphas.append(float(r["top_decile_alpha"]))
        v = r.get("long_short_tstat_nw")
        if v is not None and np.isfinite(v):
            lst.append(float(v))
        if (i + 1) % 25 == 0:
            _log(f"    null draw {i+1}/{j}")
    return {
        "n_draws_alpha": len(alphas), "n_draws_ls": len(lst),
        "alpha_p95": (float(np.percentile(alphas, 95)) if alphas else None),
        "alpha_p05": (float(np.percentile(alphas, 5)) if alphas else None),
        "alpha_median": (float(np.median(alphas)) if alphas else None),
        "ls_hac_p95": (float(np.percentile(lst, 95)) if lst else None),
        "ls_hac_p05": (float(np.percentile(lst, 5)) if lst else None),
        "ls_hac_median": (float(np.median(lst)) if lst else None),
        "alpha_draws": [round(x, 8) for x in alphas],
        "ls_hac_draws": [round(x, 8) for x in lst],
        "note": ("calibrated on HALF books (~1,265 names, ~126-name deciles). X7's full-"
                 "universe floors are reported beside this and are EXTRAPOLATIONS here."),
    }


def verdict_of(primary_ok, frac_halfbooks, frac_both, frac_neg_both) -> str:
    """Register 2.3, kept in ONE place so it can be pinned."""
    if frac_neg_both >= FRAC_BOTH:
        return "REVERSED"
    if primary_ok and frac_halfbooks >= FRAC_HALFBOOKS and frac_both >= FRAC_BOTH:
        return "SURVIVES"
    return "NULL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data/backtest")
    ap.add_argument("--panel-cache", default="data/free_analysis/panel_r5r6.pkl")
    ap.add_argument("--json", default="data/free_analysis/R4_X1_ACCOUNTING_UNIVERSE.json")
    ap.add_argument("--controls-only", action="store_true")
    args = ap.parse_args()

    panel = pickle.load(open(args.panel_cache, "rb"))
    n_d, n_t = panel["date"].nunique(), panel["ticker"].nunique()
    _log(f"[r4x1] panel {panel.shape}, {n_d} dates, {n_t} names")
    out = {"item": "R4+X1", "register": "PREREG_r4_x1_accounting_and_universe_split.md",
           "k_splits": K_SPLITS, "j_null": J_NULL, "bh_q": BH_Q, "seed": SEED,
           "frac_halfbooks_bar": FRAC_HALFBOOKS, "frac_both_bar": FRAC_BOTH,
           "controls": {}, "R4": {}, "X1": {}}

    # ---- C2-shape / C1 gating ----
    c2 = {"n_dates": int(n_d), "n_names": int(n_t),
          "ok": bool(n_d >= 60 and n_t >= 2400)}
    out["controls"]["C0_canonical_panel"] = c2
    if not c2["ok"]:
        out["ABORTED"] = "panel is not canonical"
        _w(args.json, out)
        return 2
    base = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    got = {k: float(base.get(k)) for k in REC if base.get(k) is not None}
    ok1 = all(got.get(k) == v for k, v in REC.items())
    out["controls"]["C1_full_universe_headline_reproduces"] = {
        "ok": bool(ok1), "measured": got, "expected": REC}
    _log(f"[C1] full-universe headline reproduces: {ok1}")
    if not ok1:
        out["ABORTED"] = "C1 FAILED - every split result is VOID per register 6.5"
        _w(args.json, out)
        return 2
    if args.controls_only:
        _w(args.json, out)
        _log("[r4x1] controls-only pass complete; nothing scored")
        return 0

    # ================= R4 =================
    _log("[R4] Benjamini-Hochberg across the equity signal family")
    out["R4"]["bullet3_bh_equity_family"] = r4_bh_equity_family(panel)
    b3 = out["R4"]["bullet3_bh_equity_family"]
    _log(f"[R4] BH q={BH_Q}: {b3['n_discoveries_plain']} discoveries (plain), "
         f"{b3['n_discoveries_hac']} (HAC), of {b3['n_signals']} signals")
    out["R4"]["bullet4_hlz_hurdle"] = r4_hlz_hurdle(REC["long_short_tstat_nw"])
    b4 = out["R4"]["bullet4_hlz_hurdle"]
    _log(f"[R4] HLZ: headline {b4['value']:.4f} vs hurdle {b4['hlz_hurdle_sqrt_2_ln_N']:.4f} "
         f"-> clears={b4['clears_hlz_hurdle']}; X7 floor {b4['x7_calibrated_floor']} "
         f"-> clears={b4['clears_x7_calibrated_floor']}")
    out["R4"]["verdict"] = ("DONE - both closable bullets delivered"
                            if (b3["n_signals"] > 0 and b4["hlz_hurdle_sqrt_2_ln_N"])
                            else "SUPERSEDED-BY-M1")
    out["R4"]["residual"] = [
        "BH across the research LOG is not computable - no p-value column, and reconstructing "
        "one for 121 heterogeneous rows would be invention (register 1.2).",
        "The `unified` domain is declared in research_log.DOMAINS and reads ZERO: every "
        "U-series item testing unified equity+options hypotheses was charged to equity or "
        "options. Measured and ROUTED, not decided.",
        "R5's ledger row already leaned on R4's note as routing input, so anything left open "
        "here is load-bearing elsewhere.",
    ]

    # ================= X1 =================
    universe = sorted(panel["ticker"].unique())
    rng = np.random.default_rng(SEED)

    # C3: the stable key is deterministic and order-independent
    ka = [t for t in universe if stable_key_half(t) == 0]
    kb = [t for t in universe if stable_key_half(t) == 1]
    ka2 = [t for t in reversed(universe) if stable_key_half(t) == 0]
    out["controls"]["C3_stable_key_deterministic"] = {
        "n_a": len(ka), "n_b": len(kb),
        "order_independent": bool(set(ka) == set(ka2)),
        "balanced_within_1": bool(abs(len(ka) - len(kb)) <= 1),
        "construction": "int(sha1(ticker).hexdigest(), 16) % 2",
    }
    _log(f"[C3] stable key: {len(ka)} / {len(kb)}")

    _log("[X1] scoring the stable-key split (the audit's own construction)")
    sa, sb = _score(panel, set(ka)), _score(panel, set(kb))
    _assert_split(ka, kb, universe)
    # C6: zero shared (date, ticker) keys
    ra = panel[panel["ticker"].isin(set(ka))][["date", "ticker"]]
    rb = panel[panel["ticker"].isin(set(kb))][["date", "ticker"]]
    shared = len(pd.merge(ra, rb, on=["date", "ticker"], how="inner"))
    out["controls"]["C6_halves_share_zero_keys"] = {"shared_keys": int(shared),
                                                    "ok": bool(shared == 0)}
    out["X1"]["stable_key_split"] = {"half_A": sa, "half_B": sb}
    _log(f"[X1] stable key A alpha {sa['top_decile_alpha']:+.5f} ls_hac "
         f"{sa['long_short_tstat_nw']:+.4f} | B alpha {sb['top_decile_alpha']:+.5f} ls_hac "
         f"{sb['long_short_tstat_nw']:+.4f}")

    _log(f"[X1] calibrating the HALF-UNIVERSE null, {J_NULL} draws")
    null = half_universe_null(panel, universe, rng, J_NULL)
    out["X1"]["half_universe_null"] = null
    _log(f"[X1] null: alpha p95 {null['alpha_p95']:+.5f}  ls_hac p95 {null['ls_hac_p95']:+.4f}")

    _log(f"[X1] {K_SPLITS} random splits")
    splits = []
    uni = np.array(universe)
    for i in range(K_SPLITS):
        idx = rng.permutation(len(uni))
        a = set(uni[idx[: len(uni) // 2]])
        b = set(uni) - a
        _assert_split(a, b, universe)
        ra_, rb_ = _score(panel, a), _score(panel, b)
        if ra_ and rb_:
            splits.append({"A": ra_, "B": rb_})
        if (i + 1) % 25 == 0:
            _log(f"    split {i+1}/{K_SPLITS}")
    out["X1"]["n_splits_scored"] = len(splits)

    for arm, key, p95, p05 in (("A1_top_decile_alpha", "top_decile_alpha",
                                null["alpha_p95"], null["alpha_p05"]),
                               ("A2_long_short_hac_t", "long_short_tstat_nw",
                                null["ls_hac_p95"], null["ls_hac_p05"])):
        halves = [h[k][key] for h in splits for k in ("A", "B")]
        clears = [v > p95 for v in halves]
        both = [(h["A"][key] > p95 and h["B"][key] > p95) for h in splits]
        neg_both = [(h["A"][key] < p05 and h["B"][key] < p05) for h in splits]
        prim = (sa[key] > p95 and sb[key] > p95 and sa[key] > 0 and sb[key] > 0)
        f_h = float(np.mean(clears)) if clears else 0.0
        f_b = float(np.mean(both)) if both else 0.0
        f_n = float(np.mean(neg_both)) if neg_both else 0.0
        out["X1"][arm] = {
            "bar_p95_half_universe": p95,
            "primary_stable_key_A": sa[key], "primary_stable_key_B": sb[key],
            "primary_both_clear": bool(prim),
            "n_half_books": len(halves),
            "frac_half_books_clearing": f_h,
            "frac_splits_both_clear": f_b,
            "frac_splits_both_negative": f_n,
            "half_book_median": float(np.median(halves)) if halves else None,
            "half_book_min": float(np.min(halves)) if halves else None,
            "half_book_max": float(np.max(halves)) if halves else None,
            "n_half_books_negative": int(sum(1 for v in halves if v < 0)),
            "full_universe_value": REC[key],
            "x7_full_universe_floor_EXTRAPOLATION_ONLY": (
                X7_FULL_UNIVERSE_LS_HAC_FLOOR if key == "long_short_tstat_nw" else None),
            "half_book_values": [round(v, 8) for v in halves],
            "verdict": verdict_of(prim, f_h, f_b, f_n),
        }
        _log(f"[{arm}] {out['X1'][arm]['verdict']}  primary_both {prim}  "
             f"frac_halves {f_h:.3f}  frac_both {f_b:.3f}  median {np.median(halves):+.5f}")

    # ---- C4: coverage ----
    out["controls"]["C4_coverage"] = {
        "half_names_median": float(np.median([h["A"]["n_names"] for h in splits])),
        "half_rows_median": float(np.median([h["A"]["n_rows"] for h in splits])),
        "implied_decile_size": float(np.median([h["A"]["n_rows"] for h in splits])) / 69.0 / 10.0,
        "full_universe_decile_size": 113945 / 69.0 / 10.0,
    }
    _log(f"[C4] {out['controls']['C4_coverage']}")

    # ---- C7: R4's BH covers already-charged tests only ----
    covered = [r["signal"] for r in b3["signals"]]
    out["controls"]["C7_bh_covers_registered_numbers_only"] = {
        "n_covered": len(covered),
        "all_in_NUMBERS_ALL": bool(set(covered) <= set(S.NUMBERS_ALL)),
        "charges_no_equity_trial": True,
        "note": "BH is a CORRECTION applied to already-charged tests, not a new search.",
    }

    _w(args.json, out)
    _log(f"[r4x1] wrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
