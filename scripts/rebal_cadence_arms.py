# -*- coding: utf-8 -*-
"""REBAL-CADENCE pass 1 — the arms. 3 EQUITY TRIALS, booked at b34bfc8 before this file existed.

`PREREG_rebal_cadence.md` at `727652c` is a strict git ancestor of this commit, and this script
REFUSES to run without a passing pass-0 control artifact -- so the kills that license the arms
were computed AND READ in their own pass (`O10`'s process defect, not repeated).

THE GATE, from the register and not re-chosen here: Δ net alpha > +100 bps AND Δ HAC *t* > +0.25,
in BOTH halves, against arm 1. `SECTOR-NEUTRAL-B6`'s gate reused verbatim.

AND THE VERDICT TRAVELS WITH ITS MDE. The register measured the 80%-power MDE at 2.4607 /
3.0063 / 1.9854 pp, so the +100 bps margin sits 2.0x to 3.0x BELOW what this design can detect.
A pass is a bar on the POINT ESTIMATE and is not a detection; a null is bounded at ~2-3pp. Both
sentences are emitted with every verdict rather than left to the write-up.
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

from valuation.edge.power_gate import critical_value                      # noqa: E402
from valuation.studies import rebal_cadence as rc                         # noqa: E402

EQUITY_N = 251                      # after this register's booking; derived in the artifact too
MARGIN_ALPHA_PP = 1.00              # +100 bps  -- SECTOR-NEUTRAL-B6, verbatim
MARGIN_TSTAT = 0.25                 # +0.25 t   -- SECTOR-NEUTRAL-B6, verbatim

# K3-K5 bars, from the register's §5. NOT relaxed after reading anything.
K3_TURNOVER_RATIO_MAX = 0.70
K4_DROPPED_SHARE_MAX = 0.05
K5_LEGS_REQUIRED = 4


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
    raise FileNotFoundError("no data root carrying panel_corrected_69d.pkl; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
CONTROL = os.path.join(FA, "REBAL_CADENCE_CONTROL.json")
OUT = os.path.join(FA, "REBAL_CADENCE_ARMS.json")
ROWS = os.path.join(FA, "REBAL_CADENCE_ARM_ROWS.pkl")


def _hac(x, lag=1):
    """(mean, se, t) with a Newey-West lag-1 standard error -- the panel's own convention."""
    x = np.asarray([v for v in x if v == v], dtype=float)
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), float("nan")
    m = float(x.mean())
    e = x - m
    s = float(np.dot(e, e) / n)
    for L in range(1, int(lag) + 1):
        if L >= n:
            break
        s += 2.0 * (1.0 - L / (lag + 1.0)) * float(np.dot(e[L:], e[:-L]) / n)
    se = float(np.sqrt(max(s, 1e-30) / n))
    return m, se, (m / se if se > 0 else float("nan"))


def _halves(dates):
    """Split in two with the BOUNDARY PERIOD EMBARGOED, because a cadence-4 formation spans it.

    Declared in the register as a rule; the realised counts are reported rather than assumed.
    """
    n = len(dates)
    mid = n // 2
    return list(range(0, mid)), list(range(mid + 1, n)), dates[mid]


def _alpha_ann(net, ew):
    a, b = rc.annualised(net), rc.annualised(ew)
    return None if (a is None or b is None) else a - b


def main() -> int:
    # ---------------- the gate: no control artifact, no arms
    if not os.path.exists(CONTROL):
        raise SystemExit(
            "REFUSING: no pass-0 control artifact at %s. The kills that license these arms "
            "(K1 the incumbent reproduces the published contract book, K2 cadence=1 is "
            "bit-identical) must be computed AND READ in their own pass before any arm is "
            "scored. Run scripts/rebal_cadence_control.py first." % CONTROL)
    with open(CONTROL, encoding="utf-8") as fh:
        ctl = json.load(fh)
    k1 = ctl.get("C1_incumbent_reproduces_published_contract_book", {}).get("pass")
    k2 = ctl.get("C2_cadence_1_is_bit_identical_to_the_shipped_default", {}).get("pass")
    if not (k1 and k2):
        raise SystemExit(
            "REFUSING: the pass-0 control did not pass (K1=%r, K2=%r). An arm scored against "
            "an incumbent that is not the published contract book measures a lookalike."
            % (k1, k2))

    panel = pd.read_pickle(PANEL)
    import valuation.screener.settings as S
    cols = [c for c in S.FACTORS_ALL if c in panel.columns]
    rec = {k: v for k, v in S.WEIGHTS_ESTABLISHED.items() if k in cols}

    crit = critical_value(n_trials=EQUITY_N)
    out = {"item": "REBAL-CADENCE", "pass": "1 arms", "trials": 3,
           "register": "PREREG_rebal_cadence.md @ 727652c",
           "trials_booked_at": "b34bfc8 (before this runner existed)",
           "equity_n": EQUITY_N, "hlz_hurdle": crit,
           "gate": {"margin_alpha_pp": MARGIN_ALPHA_PP, "margin_tstat": MARGIN_TSTAT,
                    "source": "SECTOR-NEUTRAL-B6, reused verbatim",
                    "both_halves_required": True},
           "uncalibrated": ("every critical value here is UNCALIBRATED: V2G and R1-VAR "
                            "establish that no calibrated floor exists for a paired "
                            "within-panel difference; X7 calibrates LEVELS"),
           "control_gate": {"K1": bool(k1), "K2": bool(k2), "read_before_any_arm": True}}

    arms_full = rc.build_all(panel, cols, rec)
    common = rc.common_dates(arms_full)
    arms = rc.restrict(arms_full, common)
    early_i, late_i, boundary = _halves(common)
    out["window"] = {"common_periods": len(common), "first": common[0], "last": common[-1],
                     "early_periods": len(early_i), "late_periods": len(late_i),
                     "boundary_embargoed": boundary}

    # ---------------- K3-K5, read before the primary is scored
    q_turn = arms_full["quarterly"]["legs"][0]["annual_turnover"]
    a_turn = arms_full["annual"]["legs"][0]["annual_turnover"]
    ratio = (a_turn / q_turn) if q_turn else float("nan")
    held_name_periods = {}
    dropped = {}
    for name, a in arms_full.items():
        hp = sum((l["held_only_periods"] or 0) for l in a["legs"])
        dropped[name] = sum((l["dropped_held_name_periods"] or 0) for l in a["legs"])
        held_name_periods[name] = hp
    # the share is of HELD name-periods: held periods x book size, book size ~ decile of panel
    _bk = int(np.median([len(panel[panel["date"] == d]) for d in common[:5]]) * 0.1)
    denom = {k: max(1, v * _bk) for k, v in held_name_periods.items()}
    share = {k: dropped[k] / denom[k] for k in dropped}
    legs_ok = all(len(a["legs"]) == (K5_LEGS_REQUIRED if n == "staggered" else len(a["legs"]))
                  for n, a in arms_full.items())
    out["kills"] = {
        "K3_cadence_is_not_inert": {
            "bar": "annual turnover <= %.2f x quarterly" % K3_TURNOVER_RATIO_MAX,
            "quarterly_annual_turnover": q_turn, "annual_annual_turnover": a_turn,
            "ratio": ratio, "pass": bool(ratio <= K3_TURNOVER_RATIO_MAX)},
        "K4_holding_is_not_attrition": {
            "bar": "dropped held name-periods < %.0f%% of held name-periods"
                   % (K4_DROPPED_SHARE_MAX * 100),
            "approx_book_size": _bk,
            "dropped_held_name_periods": dropped,
            "held_periods_per_arm": held_name_periods,
            "share": share,
            "pass": all(v < K4_DROPPED_SHARE_MAX for v in share.values())},
        "K5_staggered_has_four_live_sub_books": {
            "bar": "4 of 4 on every scored period",
            "n_legs": len(arms_full["staggered"]["legs"]),
            "per_leg_periods": [l.get("formation_dates")
                                for l in arms_full["staggered"]["legs"]],
            "pass": bool(len(arms_full["staggered"]["legs"]) == K5_LEGS_REQUIRED and legs_ok)}}
    if not all(v["pass"] for v in out["kills"].values()):
        out["status"] = "A KILL FIRED -- see kills; the primary is NOT scored"
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=str)
        print(json.dumps(out["kills"], indent=1, default=str))
        return 3

    # ---------------- per-arm levels and the arm's own HAC t on net alpha
    levels = {}
    for name, a in arms.items():
        ex = [n - e for n, e in zip(a["net"], a["equal_weight"])]
        m, se, tt = _hac(ex)
        spy = [float(panel.loc[panel["date"] == d, "bench_ret"].iloc[0]) for d in a["dates"]]
        levels[name] = {
            "net_alpha_ann": _alpha_ann(a["net"], a["equal_weight"]),
            "net_ann": rc.annualised(a["net"]),
            "gross_ann": rc.annualised(a["gross"]),
            "equal_weight_ann": rc.annualised(a["equal_weight"]),
            "excess_hac_t": tt, "excess_hac_se": se, "excess_mean_per_period": m,
            # SECONDARY, NO VERDICT
            "vs_spy_ann_pp": ((rc.annualised(a["net"]) - rc.annualised(spy)) * 100.0
                              if rc.annualised(spy) is not None else None),
            "spy_ann": rc.annualised(spy),
            "annual_turnover_mean_over_legs": float(np.mean(
                [l["annual_turnover"] for l in arms_full[name]["legs"]])),
            "realised_one_way_bps_mean_over_legs": float(np.mean(
                [l["realised_one_way_bps"] for l in arms_full[name]["legs"]])),
            "net_max_drawdown": _mdd(a["net"]),
        }
    out["levels"] = levels

    # ---------------- PRIMARY: the paired gate
    prim = {}
    for name in rc.ARMS:
        if name == rc.INCUMBENT:
            continue
        pdiff = rc.paired_difference(arms, name)
        cells = {}
        for label, idx in (("full", list(range(len(common)))),
                           ("early", early_i), ("late", late_i)):
            d_sub = [pdiff["dates"][i] for i in idx]
            keep = set(d_sub)
            a_idx = [i for i, d in enumerate(arms[name]["dates"]) if d in keep]
            b_idx = [i for i, d in enumerate(arms[rc.INCUMBENT]["dates"]) if d in keep]
            a_net = [arms[name]["net"][i] for i in a_idx]
            a_ew = [arms[name]["equal_weight"][i] for i in a_idx]
            b_net = [arms[rc.INCUMBENT]["net"][i] for i in b_idx]
            b_ew = [arms[rc.INCUMBENT]["equal_weight"][i] for i in b_idx]
            d_alpha = ((_alpha_ann(a_net, a_ew) or 0.0) - (_alpha_ann(b_net, b_ew) or 0.0)) * 100.0
            _, _, ta = _hac([x - y for x, y in zip(a_net, a_ew)])
            _, _, tb = _hac([x - y for x, y in zip(b_net, b_ew)])
            dm, dse, dt = _hac([pdiff["diff"][i] for i in idx])
            cells[label] = {
                "n": len(idx),
                "delta_net_alpha_pp": d_alpha,
                "delta_hac_t": ta - tb,
                "arm_hac_t": ta, "incumbent_hac_t": tb,
                "paired_mean_per_period": dm, "paired_hac_se": dse, "paired_hac_t": dt,
                "paired_mean_ann_pp": dm * rc.PER_YEAR * 100.0,
                "alpha_leg_pass": bool(d_alpha > MARGIN_ALPHA_PP),
                "tstat_leg_pass": bool((ta - tb) > MARGIN_TSTAT)}
        eligible = all(cells[h]["alpha_leg_pass"] and cells[h]["tstat_leg_pass"]
                       for h in ("early", "late"))
        se_full = cells["full"]["paired_hac_se"]
        prim[name] = {
            "cells": cells,
            "verdict": ("ELIGIBLE -- ROUTED TO DON, NOT ADOPTED" if eligible else "REJECTED"),
            "mde_50_ann_pp": 2.0 * se_full * rc.PER_YEAR * 100.0,
            "mde_80_ann_pp": (2.0 + 0.84) * se_full * rc.PER_YEAR * 100.0,
            "mde_80_at_hurdle_ann_pp": (crit + 0.84) * se_full * rc.PER_YEAR * 100.0,
            "observed_over_mde80": (abs(cells["full"]["paired_mean_ann_pp"])
                                    / ((2.0 + 0.84) * se_full * rc.PER_YEAR * 100.0)
                                    if se_full and se_full == se_full else None),
            "bound": ("the margin sits BELOW the 80%-power MDE, so a pass is a bar on the "
                      "POINT ESTIMATE and not a detection, and a null is BOUNDED at roughly "
                      "this MDE rather than a finding that cadence does not matter")}
    out["primary"] = prim

    # ---------------- SECONDARY, NO VERDICT: after-tax through the shipped machinery
    # Called through the SHIPPED after_tax_backtest with the same opt-in cadence, so the FIFO
    # lot clock is the real one -- which is the whole point: it runs on the calendar against
    # LONG_TERM_DAYS = 366, so an annual hold crosses the long-term line and a quarterly one
    # cannot. TAXABLE-account statement only; a Roth/IRA pays no such drag.
    from valuation.edge.fundamental_panel import after_tax_backtest, LONG_TERM_DAYS
    at = {}
    for name in rc.ARMS:
        legs = []
        for cad, off in rc.SPEC[name]:
            r = after_tax_backtest(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                                   cadence=cad, offset=off) or {}
            legs.append(r)
        at[name] = {
            "after_tax_alpha_mean_over_legs": float(np.mean(
                [l["after_tax_alpha"] for l in legs if l.get("after_tax_alpha") is not None])),
            "after_tax_sharpe_mean_over_legs": float(np.mean(
                [l["after_tax_sharpe"] for l in legs if l.get("after_tax_sharpe") is not None])),
            "short_term_share_of_gains_mean_over_legs": float(np.mean(
                [l["short_term_share_of_gains"] for l in legs
                 if l.get("short_term_share_of_gains") is not None])),
            "total_drag_ann_mean_over_legs": float(np.mean(
                [l["total_drag_ann"] for l in legs if l.get("total_drag_ann") is not None])),
            "n_legs": len(legs)}
    out["secondary_after_tax_NO_VERDICT"] = {
        "arms": at, "long_term_days": LONG_TERM_DAYS,
        "mechanism_declared_in_advance": (
            "the lot clock runs on the real calendar against LONG_TERM_DAYS, so an annual hold "
            "crosses the long-term capital-gains line and a quarterly one cannot -- the "
            "after-tax leg should favour the slow arms even where the pre-tax leg does not"),
        "scope": ("TAXABLE account only. A Roth/IRA pays no such drag and earns the "
                  "net-of-cost figure instead. R1-VAR: this may not convert a failing primary "
                  "into an eligible arm, and X7 calibrates no floor for it.")}

    # ---------------- DIAGNOSTIC, NO VERDICT: the offset sweep X2 motivates
    from valuation.edge.fundamental_panel import turnover_and_costs
    offs = {}
    for cad in (2, 4):
        for off in range(cad):
            r = turnover_and_costs(panel, cols, rec, top_frac=0.1, horizon=63, exit_frac=0.3,
                                   cadence=cad, offset=off, return_series=True)
            offs["cadence%d_offset%d" % (cad, off)] = {
                "net_alpha_ann": r.get("net_alpha"),
                "annual_turnover": r.get("annual_turnover"),
                "n_periods": r.get("n_periods")}
    # AND WINDOW-MATCHED, on the SAME 66 common periods the primary uses -- otherwise each
    # offset is scored on its own window and the spread confounds timing luck with a different
    # date set, which is the very thing this register forbids elsewhere.
    matched = {}
    for cad in (2, 4):
        for off in range(cad):
            a = rc.build_arm(panel, cols, rec, [(cad, off)])
            a = rc.restrict({"x": a}, common)["x"]
            matched["cadence%d_offset%d" % (cad, off)] = {
                "net_alpha_ann": _alpha_ann(a["net"], a["equal_weight"]),
                "n_periods": a["n_periods"]}
    spread = {}
    for cad in (2, 4):
        vals = [v["net_alpha_ann"] for k, v in offs.items()
                if k.startswith("cadence%d_" % cad) and v["net_alpha_ann"] is not None]
        mv = [v["net_alpha_ann"] for k, v in matched.items()
              if k.startswith("cadence%d_" % cad) and v["net_alpha_ann"] is not None]
        spread["cadence%d" % cad] = {
            "own_window": {"min": min(vals), "max": max(vals),
                           "spread_pp": (max(vals) - min(vals)) * 100.0},
            "window_matched_to_the_primary": {
                "min": min(mv), "max": max(mv),
                "spread_pp": (max(mv) - min(mv)) * 100.0}}
    out["diagnostic_offset_sweep_NO_VERDICT"] = {
        "cells_own_window": offs, "cells_window_matched": matched, "spread": spread,
        "why": ("X2 measured the rebalance-date grid ALONE moving the long-short t from 2.70 "
                "to 3.52. This quantifies the timing luck arms 2 and 3 carry and arm 4 removes. "
                "NO VERDICT: picking the best offset after seeing it is design-on-outcome, and "
                "the register makes quoting one a void condition.")}

    pd.to_pickle({"arms": arms, "arms_full": arms_full, "common_dates": common,
                  "early_idx": early_i, "late_idx": late_i, "boundary": boundary},
                 ROWS)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    # ---------------- report
    print("window: %d common periods %s .. %s | halves %d / %d, boundary %s embargoed"
          % (len(common), common[0], common[-1], len(early_i), len(late_i), boundary))
    print("kills: K3 %s (ratio %.4f)  K4 %s  K5 %s"
          % (out["kills"]["K3_cadence_is_not_inert"]["pass"], ratio,
             out["kills"]["K4_holding_is_not_attrition"]["pass"],
             out["kills"]["K5_staggered_has_four_live_sub_books"]["pass"]))
    print("\nLEVELS (net alpha ann, turnover, vs SPY pp, maxDD)")
    for n in rc.ARMS:
        L = levels[n]
        print("  %-11s %+.4f%%  turn %.4f  spy %+.2fpp  mdd %.4f  own HAC t %.4f"
              % (n, 100 * (L["net_alpha_ann"] or 0), L["annual_turnover_mean_over_legs"],
                 L["vs_spy_ann_pp"] or 0, L["net_max_drawdown"] or 0, L["excess_hac_t"]))
    print("\nPRIMARY (vs quarterly; gate +%.2fpp alpha AND +%.2f t, BOTH halves)"
          % (MARGIN_ALPHA_PP, MARGIN_TSTAT))
    for n, p in prim.items():
        print("  %-11s %s" % (n, p["verdict"]))
        for h in ("full", "early", "late"):
            c = p["cells"][h]
            print("      %-5s n %2d  dAlpha %+.4fpp %s  dt %+.4f %s  paired t %+.4f"
                  % (h, c["n"], c["delta_net_alpha_pp"],
                     "PASS" if c["alpha_leg_pass"] else "fail",
                     c["delta_hac_t"], "PASS" if c["tstat_leg_pass"] else "fail",
                     c["paired_hac_t"]))
        print("      MDE80 %.4fpp | observed %.4fpp = %.3fx its own 80%%-power threshold"
              % (p["mde_80_ann_pp"], p["cells"]["full"]["paired_mean_ann_pp"],
                 p["observed_over_mde80"] or float("nan")))
    print("\nwrote", OUT, "and", ROWS)
    return 0


def _mdd(xs):
    v, peak, worst = 1.0, 1.0, 0.0
    for x in xs:
        if x != x:
            continue
        v *= (1.0 + x)
        peak = max(peak, v)
        worst = min(worst, v / peak - 1.0)
    return float(worst)


if __name__ == "__main__":
    raise SystemExit(main())
