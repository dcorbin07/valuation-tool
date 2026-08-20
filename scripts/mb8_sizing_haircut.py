#!/usr/bin/env python3
"""mb8_sizing_haircut.py — MA28's crash flags as a position-SIZING haircut.  [MB8]

Executes VALQUO_MASTER_AUDIT_4.md item MB8. Everything -- the 0.5x haircut, the 20% crash-count
bar, the 1.8629pp non-inferiority margin, the controls, the fail-open disclosure and the prior --
is fixed in PREREG_mb8_sizing_haircut.md, committed ALONE at a6d57c1 BEFORE this file existed,
with the equity trial booked at 18a4ecc BEFORE this file was run.

THE ARITHMETIC THE REGISTER DID FIRST. A 0.5x haircut removes at most HALF the crash exposure it
touches, so

    reduction <= 0.5 * (flagged share of the book's crash exposure)

and clearing 20% needs that share to reach 40%. MA28's own pooled figures put it at 19.14%, which
implies ~6.1% renormalised. The register expects the kill to fire and says so; the arm runs because
the primary is the TOP DECILE, a different and megacap-tilted population.

JUDGED ON CRASH COUNT AND NEVER ON ALPHA. `top_decile_alpha` appears in the arm path ONLY as a
NON-INFERIORITY guard rail that can REJECT -- it can never make the arm pass. Pinned by an AST test
that reads the syntax tree.

ADOPTION IS A VINTAGE EVENT: an eligible result is ROUTED TO DON, never adopted. No file on a live
scoring path is touched and MA28_CARD.json is opened read-only.

    python -m scripts.mb8_sizing_haircut --controls
    python -m scripts.mb8_sizing_haircut --arm
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import valuation.edge.fundamental_panel as FP                                # noqa: E402
from valuation.edge import power_gate as PG                                  # noqa: E402
from valuation.screener.cross_sectional import zscore                        # noqa: E402
# THE FLAGS ARE MA28's. build_flags / beneish_m / altman_z are IMPORTED, never redefined, and the
# thresholds -1.78 and 1.81 are never retyped -- two definitions of one bar is audit B7's class,
# and MA28's own suite bans exactly this.
from scripts.s10_accounting_veto import build_flags                          # noqa: E402

# ---- PRE-REGISTERED; see PREREG_mb8_sizing_haircut.md ---------------------------------------
HAIRCUT = 0.5                 # register 2 -- FIXED, never swept
CRASH = -0.50                 # MA28's own named bad outcome, over the panel's 63d window
N_Q = 10
REDUCTION_BAR = 0.20          # register 3 -- KILL below this in EITHER half
ALPHA_MARGIN_PP = 1.8629      # register 4 -- X7 calibrated, MA19 recalibrated, MB31 proved unmoved
INERT_TOL = 0.0               # register 8 C4 -- at 1.0x the arm must be BIT-IDENTICAL

THEMES = ["value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional"]
W = 0.125

# register 8 C1 -- the published record this panel must reproduce, exactly.
REC = {"top_decile_alpha": 0.07174142332098163,
       "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884,
       "monotonicity": -0.8909090909090909}

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"


def _root(explicit=None):
    """`data/` is gitignored. Probe for the FILE, never the directory -- and note that MA28's own
    artifacts live in the WORKTREE's data dir while the panel lives in the primary, so the two are
    resolved separately."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, "data", "free_analysis", "panel_r5r6.pkl")):
            return c
    raise SystemExit("[mb8] no data root holding data/free_analysis/panel_r5r6.pkl")


def _ma28(root):
    """MA28_CARD.json, read-only. It may sit in the worktree rather than the primary root."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (here, root):
        p = os.path.join(base, "data", "free_analysis", "MA28_CARD.json")
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                return json.load(fh), p
    return None, None


# --------------------------------------------------------------------------- the book


def decile_rows(panel, dates=None):
    """Per-date TOP-DECILE membership, rebuilt from the SHIPPED primitives.

    `quantile_backtest` does not return membership, so this mirrors it exactly:
    composite_from_frame -> finite mask on (comp, fwd) -> argsort(-comp) -> array_split(.., n_q)
    -> buckets[0]. C2 then PROVES it identical by reproducing quantile_backtest's own per-date
    alpha to < 1e-12. That control exists because MB18 was burned two items ago by a re-derived
    construction that quietly answered a different question.

    Yields (date, sub_index_of_top_decile, fwd_of_all_finite_rows, positional_index_map).
    """
    out = []
    for d in (sorted(panel["date"].unique()) if dates is None else dates):
        sub = panel[panel["date"] == d]
        comp = FP.composite_from_frame(sub, THEMES, {c: W for c in THEMES}, zscore)
        fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        c2, f2 = np.asarray(comp)[ok], fwd[ok]
        if len(f2) < N_Q * 3:
            continue
        order = np.argsort(-c2)
        top = np.array_split(order, N_Q)[0]
        rows = sub.index.to_numpy()[ok][top]        # panel row labels of the holdings
        out.append({"date": str(d)[:10], "rows": rows, "fwd_top": f2[top],
                    "fwd_all_mean": float(np.mean(f2)), "n_all": int(len(f2))})
    return out


def _exposure(book, flagged_by_row, haircut):
    """Crash exposure and the weighted book return, per date.

    Weights are renormalised so they SUM TO THE NUMBER OF HOLDINGS (mean weight 1), which keeps
    the weighted crash count on the same scale as a count and keeps the book fully invested --
    register 2. `plain` is the un-renormalised sensitivity.
    """
    rec = []
    for b in book:
        fl = np.array([bool(flagged_by_row.get(r, False)) for r in b["rows"]])
        w = np.where(fl, haircut, 1.0)
        n = len(w)
        wn = w * (n / w.sum()) if w.sum() > 0 else w      # renormalised: mean weight 1
        crash = b["fwd_top"] < CRASH
        rec.append({
            "date": b["date"], "n_holdings": n,
            "n_flagged": int(fl.sum()), "n_unflaggable": 0,
            "crash_count_base": float(crash.sum()),
            "crash_exposure_renorm": float(wn[crash].sum()),
            "crash_exposure_plain": float(w[crash].sum()),
            "ret_base": float(np.mean(b["fwd_top"])),
            "ret_renorm": float(np.sum(wn * b["fwd_top"]) / wn.sum()),
            "ret_plain": float(np.sum(w * b["fwd_top"]) / n),   # cash drag kept, by design
            "ew_all": b["fwd_all_mean"],
            "n_crash_flagged": int((crash & fl).sum()),
            "n_crash_kept": int((crash & ~fl).sum()),
        })
    return pd.DataFrame(rec)


def _window(df, label, periods_per_year=4.0):
    base = df["crash_count_base"].sum()
    ren = df["crash_exposure_renorm"].sum()
    pla = df["crash_exposure_plain"].sum()
    a_base = float(np.mean(df["ret_base"] - df["ew_all"])) * periods_per_year
    a_ren = float(np.mean(df["ret_renorm"] - df["ew_all"])) * periods_per_year
    a_pla = float(np.mean(df["ret_plain"] - df["ew_all"])) * periods_per_year
    paired = (df["ret_renorm"] - df["ret_base"]).to_numpy(dtype=float)
    n_cf, n_ck = int(df["n_crash_flagged"].sum()), int(df["n_crash_kept"].sum())
    return {
        "label": label, "n_dates": int(len(df)),
        "holdings_per_date_median": float(df["n_holdings"].median()),
        "flagged_share_of_holdings": float(df["n_flagged"].sum() / df["n_holdings"].sum()),
        "crash_count_base": base,
        "crash_exposure_renorm": ren, "crash_exposure_plain": pla,
        "reduction_renorm": (1.0 - ren / base) if base else None,
        "reduction_plain": (1.0 - pla / base) if base else None,
        "clears_20pct_renorm": bool(base and (1.0 - ren / base) >= REDUCTION_BAR),
        "n_crash_flagged": n_cf, "n_crash_kept": n_ck,
        "flagged_share_of_crashes": (n_cf / (n_cf + n_ck)) if (n_cf + n_ck) else None,
        "implied_max_reduction": (0.5 * n_cf / (n_cf + n_ck)) if (n_cf + n_ck) else None,
        "dates_with_zero_crashes": int((df["crash_count_base"] == 0).sum()),
        # the guard rail
        "alpha_base_ann": a_base, "alpha_renorm_ann": a_ren, "alpha_plain_ann": a_pla,
        "alpha_delta_pp": (a_ren - a_base) * 100.0,
        "alpha_noninferior": bool((a_base - a_ren) * 100.0 <= ALPHA_MARGIN_PP),
        "paired_mean_pp": float(np.mean(paired)) * periods_per_year * 100.0,
        "paired_se_pp": (float(np.std(paired, ddof=1) / np.sqrt(len(paired)))
                         * periods_per_year * 100.0) if len(paired) > 1 else None,
    }


def _halves(dates):
    """MA28's own geometry: split with the boundary date EMBARGOED."""
    d = sorted(dates)
    mid = len(d) // 2
    return d[:mid], d[mid + 1:], d[mid]


# --------------------------------------------------------------------------- controls


def run_controls(root, out_path):
    fa = os.path.join(root, "data", "free_analysis")
    panel = pd.read_pickle(os.path.join(fa, "panel_r5r6.pkl"))
    res = {"item": "MB8", "register": "PREREG_mb8_sizing_haircut.md",
           "haircut": HAIRCUT, "crash_threshold": CRASH, "reduction_bar": REDUCTION_BAR,
           "alpha_margin_pp": ALPHA_MARGIN_PP,
           "panel_rows": int(len(panel)), "panel_dates": int(panel["date"].nunique()),
           "panel_names": int(panel["ticker"].nunique())}
    gate = {}

    # ---- C1: the panel is the published object ---------------------------------------------
    r = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=N_Q, horizon=63,
                             return_series=True)
    c1 = {k: {"record": v, "measured": r.get(k if k != "long_short_tstat_nw"
                                             else "long_short_tstat_nw", r.get(k)),
              } for k, v in REC.items()}
    got = {"top_decile_alpha": r["top_decile_alpha"],
           "long_short_tstat": r["long_short_tstat"],
           "long_short_tstat_nw": r.get("long_short_tstat_nw"),
           "monotonicity": r["monotonicity"]}
    worst = max(abs(float(got[k]) - v) for k, v in REC.items() if got.get(k) is not None)
    res["C1_record"] = {"record": REC, "measured": got, "max_abs_delta": worst}
    gate["C1_record"] = bool(worst < 1e-9)
    print("[mb8] C1 max |delta| vs the published record: %.3e" % worst, flush=True)
    if not gate["C1_record"]:
        res["ABORTED"] = "C1 FAILED - the panel is not the object the register describes"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2, default=str)
        raise SystemExit("[mb8] C1 failed; refusing to go further")

    # ---- C2: my membership IS the shipped one ----------------------------------------------
    book = decile_rows(panel)
    shipped = r["series"]["alpha"]
    mine = [b["fwd_top"].mean() - b["fwd_all_mean"] for b in book]
    n = min(len(shipped), len(mine))
    dmax = max(abs(float(shipped[i]) - float(mine[i])) for i in range(n)) if n else 1.0
    res["C2_membership"] = {"n_dates_shipped": len(shipped), "n_dates_mine": len(mine),
                            "max_abs_delta_per_date_alpha": dmax,
                            "why": ("quantile_backtest does not return membership, so it is "
                                    "rebuilt from the same primitives and PROVED identical - "
                                    "MB18 was burned by a re-derived construction two items ago")}
    gate["C2_membership"] = bool(len(shipped) == len(mine) and dmax < 1e-12 and n > 0)
    print("[mb8] C2 membership: %d/%d dates, max |delta| per-date alpha %.3e"
          % (len(mine), len(shipped), dmax), flush=True)

    # ---- C3: the flags are MA28's -----------------------------------------------------------
    data_dir = os.path.join(root, "data", "backtest")
    dates = sorted(panel["date"].unique())
    flags = build_flags(data_dir, sorted(panel["ticker"].unique()), dates)
    p = panel.merge(flags, on=["date", "ticker"], how="left")
    n_flags = (p[["beneish_flag", "altman_flag", "extfin_flag"]].fillna(False).astype(int)
               .sum(axis=1))
    p["_flagged"] = n_flags >= 2
    p["_eligible"] = (p[["beneish_m", "altman_z", "extfin"]].notna().sum(axis=1) >= 2)
    share = float(p["_flagged"].mean())
    res["C3_flags"] = {"flagged_share": share, "flagged_rows": int(p["_flagged"].sum()),
                       "ma28_flagged_share": 0.057414, "ma28_flagged_rows": 6542,
                       "unflaggable_share": float(1.0 - p["_eligible"].mean()),
                       "ma28_unflaggable_share": 0.22009741541972003,
                       "build_flags_imported_from": "scripts.s10_accounting_veto"}
    gate["C3_flags"] = bool(abs(share - 0.057414) < 5e-4
                            and abs(int(p["_flagged"].sum()) - 6542) <= 5)
    print("[mb8] C3 flags: share %.6f vs MA28 0.057414 | rows %d vs 6542 | unflaggable %.4f"
          % (share, int(p["_flagged"].sum()), 1.0 - p["_eligible"].mean()), flush=True)

    # ---- C4: the haircut is inert at 1.0x ---------------------------------------------------
    fl_by_row = dict(zip(p.index.to_numpy(), p["_flagged"].to_numpy()))
    e1 = _exposure(book, fl_by_row, 1.0)
    d_exp = float(np.max(np.abs(e1["crash_exposure_renorm"] - e1["crash_count_base"])))
    d_ret = float(np.max(np.abs(e1["ret_renorm"] - e1["ret_base"])))
    res["C4_inert_at_1x"] = {"max_abs_delta_exposure": d_exp, "max_abs_delta_return": d_ret,
                             "tolerance": INERT_TOL}
    gate["C4_inert_at_1x"] = bool(d_exp <= INERT_TOL and d_ret <= 1e-15)
    print("[mb8] C4 inert at 1.0x: exposure |delta| %.3e  return |delta| %.3e" % (d_exp, d_ret),
          flush=True)

    # ---- the power statement, before the arm -------------------------------------------------
    nd = len(book)
    res["power_before_the_run"] = {
        "n_paired_dates": nd,
        "crit": 2.0, "crit_is": "UNCALIBRATED - V2G: no calibrated floor exists for a paired "
                                "within-panel difference",
        "mde_80pct_power_sd": PG.mde_at_power(nd, crit=2.0),
        "detection_threshold_50pct_power_sd": 2.0 / np.sqrt(nd),
        "note": ("V2G measured the paired HAC SE of an annual alpha difference at 0.9354pp, so "
                 "the resolution is near 1.87pp - almost exactly the non-inferiority margin, "
                 "which means this design is matched to its bar with no room to spare"),
    }

    # ---- the register's own arithmetic bound, restated from MA28 -----------------------------
    card, card_path = _ma28(root)
    if card is not None:
        pool = card["diagnostics_no_verdict"]["eligible_rows_only"]["windows"]["full_sample"]["pooled"]
        fshare = pool["n_crash_flagged"] / (pool["n_crash_flagged"] + pool["n_crash_kept"])
        res["register_1_arithmetic"] = {
            "ma28_flagged_share_of_crashes_panelwide": fshare,
            "implied_max_reduction_panelwide": 0.5 * fshare,
            "share_needed_for_20pct": 0.40,
            "read_only_source": os.path.basename(card_path),
        }
    res["fail_open"] = {
        "unflaggable_rows_take_NO_haircut": True,
        "ma28_unflaggable_share": 0.22009741541972003,
        "ma28_crash_rate_of_unflaggable": 0.0081342956258224,
        "ma28_crash_rate_of_flaggable_kept": 0.008928137602643214,
        "statement": ("An unflaggable name takes NO haircut: the sizing rule FAILS OPEN. On a "
                      "screen that is a coverage caveat; on a sizing rule it means the rule "
                      "silently declines to protect the fifth of the book it cannot see. MA28's "
                      "own measurement prices it: those rows crash at 0.8134% against the "
                      "flaggable-and-kept 0.8928%, so they are marginally SAFER than the names "
                      "the rule sees and declines to haircut."),
    }

    res["gating"] = gate
    res["all_gating_pass"] = bool(all(gate.values()))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    print("\n[mb8] gating: %s" % json.dumps(gate), flush=True)
    print("[mb8] all_gating_pass = %s -> %s" % (res["all_gating_pass"], out_path), flush=True)
    return 0 if res["all_gating_pass"] else 2


# --------------------------------------------------------------------------- the arm


def run_arm(root, controls_path, out_path):
    if not os.path.isfile(controls_path):
        raise SystemExit("[mb8] --arm REFUSES: no controls artifact at %s" % controls_path)
    with open(controls_path, encoding="utf-8") as fh:
        ctrl = json.load(fh)
    if not ctrl.get("all_gating_pass"):
        raise SystemExit("[mb8] --arm REFUSES: controls do not pass (gating=%s)"
                         % json.dumps(ctrl.get("gating")))

    fa = os.path.join(root, "data", "free_analysis")
    panel = pd.read_pickle(os.path.join(fa, "panel_r5r6.pkl"))
    flags = build_flags(os.path.join(root, "data", "backtest"),
                        sorted(panel["ticker"].unique()), sorted(panel["date"].unique()))
    p = panel.merge(flags, on=["date", "ticker"], how="left")
    nf = (p[["beneish_flag", "altman_flag", "extfin_flag"]].fillna(False).astype(int).sum(axis=1))
    p["_flagged"] = nf >= 2
    p["_eligible"] = (p[["beneish_m", "altman_z", "extfin"]].notna().sum(axis=1) >= 2)
    fl_by_row = dict(zip(p.index.to_numpy(), p["_flagged"].to_numpy()))
    el_by_row = dict(zip(p.index.to_numpy(), p["_eligible"].to_numpy()))

    book = decile_rows(panel)
    df = _exposure(book, fl_by_row, HAIRCUT)
    # fail-open census on the book itself
    df["n_unflaggable"] = [int(sum(1 for r in b["rows"] if not el_by_row.get(r, False)))
                           for b in book]

    # ---- C5: the fail-open census the register promised, IN THE BOOK ------------------------
    # register 8 C5: "count and share of unflaggable top-decile holdings, and their crash rate".
    # The first cut of this script counted them and did NOT report their crash rate, which is the
    # half that matters -- so the census is completed here rather than left under-delivered.
    cen = {"flagged": [0, 0], "flaggable_kept": [0, 0], "unflaggable": [0, 0]}
    for b in book:
        for rr, ret in zip(b["rows"], b["fwd_top"]):
            crashed = 1 if ret < CRASH else 0
            k = ("unflaggable" if not el_by_row.get(rr, False)
                 else ("flagged" if fl_by_row.get(rr, False) else "flaggable_kept"))
            cen[k][0] += 1
            cen[k][1] += crashed
    tot_h = sum(v[0] for v in cen.values())
    tot_c = sum(v[1] for v in cen.values())
    census = {k: {"holdings": v[0], "share_of_holdings": v[0] / tot_h,
                  "crashes": v[1], "share_of_crashes": (v[1] / tot_c) if tot_c else None,
                  "crash_rate": (v[1] / v[0]) if v[0] else None} for k, v in cen.items()}

    all_d = [b["date"] for b in book]
    early_d, late_d, boundary = _halves(all_d)
    win = {
        "full_sample": _window(df, "full_sample"),
        "early_half": _window(df[df["date"].isin(early_d)], "early_half"),
        "late_half": _window(df[df["date"].isin(late_d)], "late_half"),
    }

    both = win["early_half"]["clears_20pct_renorm"] and win["late_half"]["clears_20pct_renorm"]
    guard_ok = all(win[w]["alpha_noninferior"] for w in ("full_sample", "early_half", "late_half"))
    if not guard_ok:
        verdict = "REJECTED - alpha non-inferiority FAILS"
        consequence = ("The guard rail rejects regardless of the crash result: a risk control "
                       "that costs more than the calibrated margin is a trade, and this register "
                       "may not make it.")
    elif both:
        verdict = "ELIGIBLE - ROUTED TO DON"
        consequence = ("Adoption is a VINTAGE EVENT and is NOT taken here. Recorded ELIGIBLE and "
                       "routed; it resets the five-year clock and is Don's call.")
    else:
        verdict = "KILL - the sizing family CLOSES PERMANENTLY"
        consequence = ("Crash-count reduction below 20% in at least one half. Per the register's "
                       "own section 1 this is a finding about the 0.5x-haircut DESIGN and NOT "
                       "about MA28's flag, which stands on its own evidence.")

    # sensitivities
    el_book = [{"date": b["date"],
                "rows": np.array([r for r in b["rows"] if el_by_row.get(r, False)]),
                "fwd_top": np.array([f for r, f in zip(b["rows"], b["fwd_top"])
                                     if el_by_row.get(r, False)]),
                "fwd_all_mean": b["fwd_all_mean"], "n_all": b["n_all"]} for b in book]
    el_book = [b for b in el_book if len(b["rows"]) >= 10]
    el_df = _exposure(el_book, fl_by_row, HAIRCUT)

    out = {
        "item": "MB8", "register": "PREREG_mb8_sizing_haircut.md",
        "haircut": HAIRCUT, "reduction_bar": REDUCTION_BAR,
        "alpha_margin_pp": ALPHA_MARGIN_PP,
        "boundary_date_embargoed": boundary,
        "windows": win,
        "verdict": verdict, "consequence": consequence,
        "guard_rail_passed": guard_ok, "crash_bar_cleared_both_halves": both,
        "sensitivity_eligible_rows_only": {
            "full_sample": _window(el_df, "eligible_only_full"),
            "note": "MA28's C7: 22.01% of panel rows carry fewer than two computable inputs",
        },
        "sensitivity_unrenormalised": {
            w: {"reduction_plain": win[w]["reduction_plain"],
                "alpha_plain_ann": win[w]["alpha_plain_ann"]} for w in win},
        "register_1_arithmetic": ctrl.get("register_1_arithmetic"),
        "C5_fail_open_census_in_book": census,
        "C5_note": ("POST-HOC, NO VERDICT (MA28's C4 precedent). The register priced the "
                    "fail-open from MA28's PANEL-WIDE figures, where unflaggable rows crash at "
                    "0.8134% against the flaggable-and-kept 0.8928% and are therefore marginally "
                    "SAFER. IN THE BOOK THAT REVERSES: see crash_rate above. A ratio is REFUSED "
                    "on the flagged bucket, which carries a single crash - one event is not a "
                    "rate."),
        "fail_open": ctrl.get("fail_open"),
        "power_before_the_run": ctrl.get("power_before_the_run"),
        "reporting_rule": ("QUOTE RATIOS AND BOTH RATES, NEVER DIFFERENCES - MA28 measured the "
                           "base rate moving 4x between halves (kept 0.3413% early against "
                           "1.3595% late), so an absolute gap describes neither half."),
        "trials": {"charged": 1, "domain": "equity",
                   "booked_before_the_run_at": "18a4ecc", "equity_n": "235 -> 236"},
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print("\n" + "=" * 78)
    print("MB8 -- MA28's crash flags as a 0.5x position-SIZING haircut")
    print("=" * 78)
    print("%-12s %6s %8s %10s %10s %9s %9s" %
          ("window", "dates", "crashes", "reduction", "bar 20%", "alpha b", "alpha a"))
    for w in ("full_sample", "early_half", "late_half"):
        c = win[w]
        print("%-12s %6d %8.0f %9.2f%% %10s %8.3f%% %8.3f%%"
              % (w, c["n_dates"], c["crash_count_base"], 100 * (c["reduction_renorm"] or 0),
                 "CLEARS" if c["clears_20pct_renorm"] else "FAILS",
                 100 * c["alpha_base_ann"], 100 * c["alpha_renorm_ann"]))
    f = win["full_sample"]
    print("-" * 78)
    print("flagged share of top-decile crashes: %.4f  -> arithmetic ceiling on reduction %.2f%%"
          % (f["flagged_share_of_crashes"] or 0, 100 * (f["implied_max_reduction"] or 0)))
    print("alpha delta (arm - base): %+.4f pp   non-inferiority margin %.4f pp -> %s"
          % (f["alpha_delta_pp"], ALPHA_MARGIN_PP, "PASSES" if guard_ok else "FAILS"))
    print("VERDICT: %s" % verdict)
    print(consequence)
    print("=" * 78)
    print("[mb8] wrote %s" % out_path, flush=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=None)
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--arm", action="store_true")
    a = ap.parse_args(argv)
    root = _root(a.root)
    fa = os.path.join(root, "data", "free_analysis")
    controls = os.path.join(fa, "MB8_CONTROLS.json")
    if a.controls:
        return run_controls(root, controls)
    if a.arm:
        return run_arm(root, controls, os.path.join(fa, "MB8_SIZING_HAIRCUT.json"))
    ap.error("one of --controls / --arm is required")


if __name__ == "__main__":
    raise SystemExit(main())
