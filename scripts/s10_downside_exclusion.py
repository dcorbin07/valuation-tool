#!/usr/bin/env python3
"""s10_downside_exclusion.py — should a name whose BULL case is already below price be bought?

S10, Don's question formalized. Everything — the flag, the arms, the decision rule, the
controls, the trial charge and the expectations — is fixed in PREREG_s10_downside_exclusion.md,
committed ALONE at a041e09 BEFORE this file existed. Nothing here restates a threshold from a
result.

ADOPTS NOTHING. An adopted entry screen changes the live scoring path, which is a VINTAGE EVENT
that resets the five-year forward clock; on this evidence that is Don's call.

    python -m scripts.s10_downside_exclusion \
        --panel C:/.../data/free_analysis/panel_corrected_69d.pkl \
        --band  C:/.../data/free_analysis/panel_s10_band.pkl \
        --json  C:/.../data/free_analysis/S10_DOWNSIDE_EXCLUSION.json
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

# ---- PRE-REGISTERED constants (PREREG_s10_downside_exclusion.md) ---------------------------
DEPLOYED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
            "capital_discipline": 0.125, "size": 0.125, "institutional": 0.125}
COLS = list(DEPLOYED)

DD_BAR_PP = 2.0        # drawdown must improve by MORE than this... (UNCALIBRATED - see §5)
ALPHA_BAR_PP = 1.0     # ...and alpha must fall by LESS than this (a non-inferiority allowance)
N_Q = 10
HORIZON = 63
PPY = 252.0 / HORIZON
TOP_N = 25
EXIT_RANK = 50
MIN_HOLD = 2
BPS_ONE_WAY = 33.4     # B11's MEASURED realised cost
DISASTER = -0.50       # "subsequently fell more than 50%" - the audit's key count

# The published record, for control C5.
REC = {"top_decile_alpha": 0.07174142332098163, "long_short_tstat": 2.8360640685320595,
       "long_short_tstat_nw": 2.6199121240414884, "monotonicity": -0.8909090909090909}


def _hac(series, lag=1):
    from valuation.edge.statistics import hac_tstat
    return hac_tstat(series, lag=lag)


def _dd(rets):
    """Max drawdown via the SHIPPED risk_stats, never a second copy."""
    from valuation.edge.fundamental_panel import risk_stats
    return risk_stats(rets, PPY)


def drawdown_gain_pp(arm_dd, base_dd):
    """How much an arm IMPROVES max drawdown, in percentage points. Positive = better.

    `max_drawdown` is NEGATIVE (-0.28 is a 28% peak-to-trough), so an arm improves it by
    being LESS negative: the gain is `arm - base`. The first cut of this script wrote
    `base - arm`, which reports a DEEPER drawdown as a gain — it turned a 2.6pp worsening
    into a 2.6pp improvement and would have inverted the reported reason for the verdict.
    Same class of error as the `monotonicity` sign this project read backwards for months.
    Pinned by test_s10_a_deeper_drawdown_is_never_reported_as_an_improvement.
    """
    if arm_dd is None or base_dd is None:
        return None
    return (float(arm_dd) - float(base_dd)) * 100.0


def _dd_span(rets):
    """How many periods the worst peak-to-trough actually spans.

    The register calls max drawdown "a single order statistic" and warns it is far noisier
    than a mean. If the worst run is ONE 63-day period, the whole 2.0pp drawdown leg is being
    decided by one quarter, and that is worth stating as a measured fact rather than a caveat.
    """
    a = np.asarray([r for r in rets if r == r], dtype=float)
    if len(a) < 3:
        return None
    eq = np.cumprod(1.0 + a)
    peak = np.maximum.accumulate(eq)
    dd = eq / peak - 1.0
    trough = int(np.argmin(dd))
    start = trough
    while start > 0 and eq[start - 1] < peak[trough]:
        start -= 1
    return {"periods": int(trough - start + 1), "trough_index": trough,
            "depth": float(dd[trough])}


def _books(panel, flag, cols=COLS, weights=DEPLOYED):
    """Per-date top-decile books for all three arms, mirroring quantile_backtest exactly.

    Selection is `argsort(-comp)` then `array_split` into deciles, which is the shipped
    construction; the only thing that differs between arms is WHICH members of bucket 0 are
    kept. The benchmark stays the FULL unscreened universe, so the comparison is against the
    same yardstick every published figure uses.
    """
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore

    dates = sorted(panel["date"].unique())
    out = {a: {"ret": [], "alpha": [], "n": [], "names": {}}
           for a in ("A0", "A1_DROP", "A2_BACKFILL")}
    used, mech = [], {"flag_ret": [], "unflag_ret": [], "n_flag": [], "n_unflag": []}
    diag = {"n_top": 0, "n_top_flagged": 0, "disaster_flag": 0, "disaster_unflag": 0,
            "flag_theme": {c: [] for c in cols}, "unflag_theme": {c: [] for c in cols},
            "flag_regime": {}, "top_regime": {}, "flag_sector": {}, "top_sector": {}}

    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, cols, weights, zscore)
        fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(fwd)
        if ok.sum() < N_Q * 3:
            continue
        idx = np.flatnonzero(ok)
        comp_o, fwd_o = comp[idx], fwd[idx]
        tick = sub["ticker"].to_numpy()[idx]
        reg = (sub["regime"].to_numpy()[idx] if "regime" in sub.columns
               else np.array([""] * len(idx)))
        sec = (sub["sector"].to_numpy()[idx] if "sector" in sub.columns
               else np.array([""] * len(idx)))
        fl = np.array([bool(flag.get((str(d)[:10], str(t)), False)) for t in tick])

        order = np.argsort(-comp_o)
        buckets = np.array_split(order, N_Q)
        top = buckets[0]
        k = len(top)
        used.append(str(d)[:10])
        ew = float(np.mean(fwd_o))

        top_fl = fl[top]
        diag["n_top"] += k
        diag["n_top_flagged"] += int(top_fl.sum())
        diag["disaster_flag"] += int((fwd_o[top][top_fl] < DISASTER).sum())
        diag["disaster_unflag"] += int((fwd_o[top][~top_fl] < DISASTER).sum())
        for c in cols:
            if c in sub.columns:
                zc = zscore(sub[c]).values[idx][top]
                diag["flag_theme"][c].extend([float(x) for x in zc[top_fl] if x == x])
                diag["unflag_theme"][c].extend([float(x) for x in zc[~top_fl] if x == x])
        for r, f in zip(reg[top], top_fl):
            diag["top_regime"][r] = diag["top_regime"].get(r, 0) + 1
            if f:
                diag["flag_regime"][r] = diag["flag_regime"].get(r, 0) + 1
        for s, f in zip(sec[top], top_fl):
            diag["top_sector"][s] = diag["top_sector"].get(s, 0) + 1
            if f:
                diag["flag_sector"][s] = diag["flag_sector"].get(s, 0) + 1

        # M1 MECHANISM — within the decile, flagged vs unflagged, paired by date.
        if top_fl.any() and (~top_fl).any():
            mech["flag_ret"].append(float(np.mean(fwd_o[top][top_fl])))
            mech["unflag_ret"].append(float(np.mean(fwd_o[top][~top_fl])))
            mech["n_flag"].append(int(top_fl.sum()))
            mech["n_unflag"].append(int((~top_fl).sum()))
        else:
            mech["flag_ret"].append(np.nan)
            mech["unflag_ret"].append(np.nan)
            mech["n_flag"].append(int(top_fl.sum()))
            mech["n_unflag"].append(int((~top_fl).sum()))

        arms = {
            "A0": top,
            "A1_DROP": top[~top_fl],
            # BACKFILL — walk the ranking and take unflagged names until the book is the
            # SAME SIZE as the incumbent decile, so concentration is not a confound.
            "A2_BACKFILL": np.array([j for j in order if not fl[j]][:k], dtype=int),
        }
        for a, sel in arms.items():
            if len(sel) == 0:
                out[a]["ret"].append(np.nan)
                out[a]["alpha"].append(np.nan)
                out[a]["n"].append(0)
                continue
            out[a]["ret"].append(float(np.mean(fwd_o[sel])))
            out[a]["alpha"].append(float(np.mean(fwd_o[sel]) - ew))
            out[a]["n"].append(int(len(sel)))
            out[a]["names"][str(d)[:10]] = [str(x) for x in tick[sel]]
    return out, used, mech, diag


def _turnover(names_by_date, dates):
    """One-way turnover per rebalance: the fraction of the book replaced."""
    ts = []
    for a, b in zip(dates, dates[1:]):
        pa, pb = set(names_by_date.get(a, [])), set(names_by_date.get(b, []))
        if pa and pb:
            ts.append(1.0 - len(pa & pb) / float(len(pb)))
    return float(np.mean(ts)) if ts else None


def summarize(arm, dates):
    r, a = arm["ret"], arm["alpha"]
    rr = [x for x in r if x == x]
    aa = [x for x in a if x == x]
    risk = _dd(rr)
    return {"alpha_ann": float(np.mean(aa) * PPY) if aa else None,
            "alpha_hac_t": _hac(aa), "book_ret_ann": float(np.mean(rr) * PPY) if rr else None,
            "max_drawdown": risk.get("max_drawdown"), "sharpe": risk.get("sharpe"),
            "drawdown_span": _dd_span(rr),
            "vol_ann": risk.get("vol_ann"), "n_periods": len(aa),
            "mean_book_size": float(np.mean([x for x in arm["n"] if x])) if arm["n"] else None,
            "turnover_one_way": _turnover(arm["names"], dates)}


def paired(base, arm):
    """HAC t on the per-period alpha DIFFERENCE, arm - base, over shared dates."""
    d = [(y - x) for x, y in zip(base["alpha"], arm["alpha"]) if x == x and y == y]
    return {"delta_alpha_ann_pp": float(np.mean(d) * PPY * 100) if d else None,
            "hac_t": _hac(d), "n": len(d)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--band", required=True)
    ap.add_argument("--json", required=True)
    args = ap.parse_args(argv)

    panel = pd.read_pickle(args.panel)
    band = pd.read_pickle(args.band)
    print(f"[s10] factor panel {len(panel):,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique()} names", flush=True)
    print(f"[s10] band panel   {len(band):,} rows, {band['date'].nunique()} dates, "
          f"{band['ticker'].nunique()} names", flush=True)

    band["_d"] = band["date"].astype(str).str[:10]
    band["_t"] = band["ticker"].astype(str)

    # `regime` is a VALUATION-panel field (which lens priced the name), not a factor-panel one.
    # It is carried across so the composition block can answer whether this is a valuation
    # screen or a regime/sector bet in disguise - U7's failure mode.
    panel["_d"] = panel["date"].astype(str).str[:10]
    panel["_t"] = panel["ticker"].astype(str)
    _reg = dict(zip(zip(band["_d"], band["_t"]), band["regime"].astype(str)))
    panel["regime"] = [_reg.get((d, t), "") for d, t in zip(panel["_d"], panel["_t"])]
    bull = pd.to_numeric(band["bull_value"], errors="coerce").to_numpy(dtype=float)
    bear = pd.to_numeric(band["bear_value"], errors="coerce").to_numpy(dtype=float)
    base_fv = pd.to_numeric(band["fair_value"], errors="coerce").to_numpy(dtype=float)
    price = pd.to_numeric(band["price"], errors="coerce").to_numpy(dtype=float)

    # C3 — band ordering MEASURED, not assumed.
    trio = np.isfinite(bear) & np.isfinite(base_fv) & np.isfinite(bull)
    viol = int((~((bear <= base_fv) & (base_fv <= bull)))[trio].sum())

    # §3 — the flag. A name with NO bull case is KEPT, never excluded.
    has_bull = np.isfinite(bull) & np.isfinite(price) & (price > 0)
    flagged = has_bull & (bull <= price)
    flag = {(d, t): True for d, t, f in zip(band["_d"], band["_t"], flagged) if f}
    have = {(d, t) for d, t, h in zip(band["_d"], band["_t"], has_bull) if h}

    print(f"[s10] band rows {len(band):,}  bull non-null {int(has_bull.sum()):,} "
          f"({has_bull.mean():.1%})  flagged {int(flagged.sum()):,} "
          f"({flagged.mean():.1%})  ordering violations {viol:,}", flush=True)

    # ---- C5 — the harness must reproduce the PUBLISHED record before any arm is read.
    # A mismatch voids the run: the known `insider` nondeterminism is exactly what this catches.
    from valuation.edge.fundamental_panel import quantile_backtest
    _qb = quantile_backtest(panel, COLS, DEPLOYED, n_q=N_Q, horizon=HORIZON)
    c5 = {k: {"got": _qb.get(k), "want": v, "match": _qb.get(k) == v} for k, v in REC.items()}
    c5["top_decile_alpha"] = {
        "got": (_qb["decile_ann_return"][0] - _qb["equal_weight_ann"]),
        "want": REC["top_decile_alpha"],
        "match": abs((_qb["decile_ann_return"][0] - _qb["equal_weight_ann"])
                     - REC["top_decile_alpha"]) < 1e-12}
    print("\n=== C5: harness reproduces the published record ===")
    for k, v in c5.items():
        print(f"  {k:22s} got {v['got']!r:24s} want {v['want']!r:24s} "
              f"{'ok' if v['match'] else 'MISMATCH'}")
    if not all(v["match"] for v in c5.values()):
        print("\nC5 FAILED — the harness does not reproduce the record. VOID; no arm is read.")
        return 2

    out, dates, mech, diag = _books(panel, flag)

    # ---- coverage on the object that matters: the top decile (COVERAGE RULE)
    n_top = diag["n_top"]
    top_cov = None
    cov_n = 0
    for d, names in out["A0"]["names"].items():
        cov_n += sum(1 for t in names if (d, t) in have)
    top_cov = cov_n / float(max(1, n_top))

    res = {"prereg": "PREREG_s10_downside_exclusion.md",
           "prereg_commit": "a041e09",
           "adopts": False,
           "adoption_note": ("ADOPTS NOTHING - an entry screen on the live scoring path is a "
                             "VINTAGE EVENT and is Don's call on this evidence."),
           "panel": {"rows": int(len(panel)), "dates": int(panel["date"].nunique()),
                     "names": int(panel["ticker"].nunique()), "scored_dates": len(dates)},
           "coverage": {"band_rows": int(len(band)),
                        "bull_non_null": float(has_bull.mean()),
                        "flagged_all_rows": float(flagged.mean()),
                        "top_decile_bull_coverage": float(top_cov),
                        "top_decile_rows": int(n_top),
                        "top_decile_flagged": int(diag["n_top_flagged"]),
                        "top_decile_flagged_frac": float(diag["n_top_flagged"] / max(1, n_top))},
           "controls": {"C3_band_ordering_violations": viol,
                        "C3_rows_with_full_trio": int(trio.sum()),
                        "C5_record": c5}}

    # ---- C6 — degenerate flag voids the test
    ff = res["coverage"]["top_decile_flagged_frac"]
    res["controls"]["C6_flag_not_degenerate"] = bool(0.0 < ff < 1.0)

    # ---- arms
    res["arms"] = {a: summarize(out[a], dates) for a in out}
    res["paired"] = {a: paired(out["A0"], out[a]) for a in ("A1_DROP", "A2_BACKFILL")}

    # ---- M1 MECHANISM
    md = [(f - u) for f, u in zip(mech["flag_ret"], mech["unflag_ret"])
          if f == f and u == u]
    res["M1_MECHANISM"] = {
        "flagged_mean_fwd": float(np.nanmean(mech["flag_ret"])),
        "unflagged_mean_fwd": float(np.nanmean(mech["unflag_ret"])),
        "delta_ann_pp": float(np.mean(md) * PPY * 100) if md else None,
        "hac_t": _hac(md), "n_dates": len(md),
        "mean_n_flagged": float(np.mean(mech["n_flag"])),
        "mean_n_unflagged": float(np.mean(mech["n_unflag"]))}

    # M1 by half, for the same both-halves discipline the decision rule uses.
    _mid = len(dates) // 2
    for _h, _sl in (("early", slice(0, _mid)), ("late", slice(_mid + 1, None))):
        _d = [(f - u) for f, u in zip(mech["flag_ret"][_sl], mech["unflag_ret"][_sl])
              if f == f and u == u]
        res["M1_MECHANISM"][_h] = {
            "delta_ann_pp": float(np.mean(_d) * PPY * 100) if _d else None,
            "hac_t": _hac(_d), "n_dates": len(_d)}

    # ---- the top-25 HOLD book, through the SHIPPED _backtest_hold.
    # The screen is applied by REMOVING flagged rows from the panel, which means a name that
    # becomes flagged while held also leaves the ranking. That makes this arm an entry AND
    # continuation screen - a STRONGER intervention than the pure entry screen the decile book
    # measures - and it is labelled as such rather than quoted as the same object. B17's caveat
    # travels with it: this book holds up to `exit_rank` names and pays no taxes.
    from valuation.edge.fundamental_panel import _backtest_hold
    _flagged_keys = set(flag)
    _keep = ~np.array([(d, t) in _flagged_keys
                       for d, t in zip(panel["_d"], panel["_t"])])
    res["hold_book"] = {
        "note": ("top-25 hold book; the screened arm applies the screen at entry AND "
                 "continuation, so it is a stronger intervention than the decile arms. "
                 "B17: this book holds up to exit_rank names and charges no taxes."),
        "A0": _backtest_hold(panel, COLS, DEPLOYED, top_n=TOP_N, exit_rank=EXIT_RANK,
                             min_hold=MIN_HOLD, horizon=HORIZON,
                             cost_bps_one_way=BPS_ONE_WAY),
        "A2_BACKFILL": _backtest_hold(panel[_keep], COLS, DEPLOYED, top_n=TOP_N,
                                      exit_rank=EXIT_RANK, min_hold=MIN_HOLD, horizon=HORIZON,
                                      cost_bps_one_way=BPS_ONE_WAY)}

    # ---- the audit's key count
    res["disasters"] = {
        "note": f"top-decile names with 63d forward return < {DISASTER:.0%}",
        "flagged": diag["disaster_flag"], "unflagged": diag["disaster_unflag"],
        "flagged_rate": diag["disaster_flag"] / max(1, diag["n_top_flagged"]),
        "unflagged_rate": diag["disaster_unflag"] / max(1, n_top - diag["n_top_flagged"])}

    # ---- composition of the flagged set (is this a valuation screen or a sector bet?)
    res["composition"] = {
        "theme_z_mean_flagged": {c: (float(np.mean(v)) if v else None)
                                 for c, v in diag["flag_theme"].items()},
        "theme_z_mean_unflagged": {c: (float(np.mean(v)) if v else None)
                                   for c, v in diag["unflag_theme"].items()},
        "regime_flagged_rate": {r: diag["flag_regime"].get(r, 0) / n
                                for r, n in sorted(diag["top_regime"].items()) if n >= 50},
        "sector_flagged_rate": {s: diag["flag_sector"].get(s, 0) / n
                                for s, n in sorted(diag["top_sector"].items()) if n >= 50}}

    # ---- halves, boundary embargoed
    mid = len(dates) // 2
    halves = {"early": dates[:mid], "late": dates[mid + 1:]}
    res["halves"] = {}
    for h, ds in halves.items():
        keep = set(ds)
        sel = [i for i, d in enumerate(dates) if d in keep]

        def cut(arm):
            return {"ret": [arm["ret"][i] for i in sel], "alpha": [arm["alpha"][i] for i in sel],
                    "n": [arm["n"][i] for i in sel],
                    "names": {d: arm["names"][d] for d in ds if d in arm["names"]}}

        cuts = {a: cut(out[a]) for a in out}
        res["halves"][h] = {
            "n_dates": len(ds), "first": ds[0], "last": ds[-1],
            "arms": {a: summarize(cuts[a], ds) for a in cuts},
            "paired": {a: paired(cuts["A0"], cuts[a]) for a in ("A1_DROP", "A2_BACKFILL")}}

    # ---- top-25 before/after, by name, on the most recent scored date
    last = dates[-1]
    sub = panel[panel["date"].astype(str).str[:10] == last]
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    comp = composite_from_frame(sub, COLS, DEPLOYED, zscore)
    fwd = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
    ok = np.isfinite(comp) & np.isfinite(fwd)
    idx = np.flatnonzero(ok)
    tick = sub["ticker"].to_numpy()[idx]
    order = np.argsort(-comp[idx])
    fl = np.array([bool(flag.get((last, str(t)), False)) for t in tick])
    inc = [str(tick[j]) for j in order[:TOP_N]]
    scr = [str(tick[j]) for j in order if not fl[j]][:TOP_N]
    res["top25_before_after"] = {
        "date": last, "incumbent": inc, "screened": scr,
        "dropped": [t for t in inc if t not in scr],
        "added": [t for t in scr if t not in inc],
        "n_changed": len([t for t in inc if t not in scr])}

    # ---- VERDICT, by the pre-registered asymmetric rule, in BOTH halves
    def leg(full, half_e, half_l, arm):
        # SIGN. `max_drawdown` is NEGATIVE (-0.28 = a 28% peak-to-trough). Drawdown IMPROVES
        # when it becomes LESS negative, i.e. arm > A0. The gain is therefore `arm - A0`, and
        # writing it the other way round reports a deeper drawdown as an improvement - which
        # is what the first cut of this script did, and is the same sign error this project
        # read into `monotonicity` for months. Pinned by
        # test_s10_a_deeper_drawdown_is_never_reported_as_an_improvement.
        dd_gain = [drawdown_gain_pp(res["arms"][arm]["max_drawdown"],
                                    res["arms"]["A0"]["max_drawdown"])]
        for h in ("early", "late"):
            hh = res["halves"][h]["arms"]
            dd_gain.append(drawdown_gain_pp(hh[arm]["max_drawdown"], hh["A0"]["max_drawdown"]))
        alpha_fall = [-(res["paired"][arm]["delta_alpha_ann_pp"])]
        for h in ("early", "late"):
            alpha_fall.append(-(res["halves"][h]["paired"][arm]["delta_alpha_ann_pp"]))
        return dd_gain, alpha_fall

    res["verdict"] = {}
    for arm in ("A1_DROP", "A2_BACKFILL"):
        dd_gain, alpha_fall = leg(None, None, None, arm)
        dd_ok = all(g > DD_BAR_PP for g in dd_gain[1:])       # both halves
        al_ok = all(f < ALPHA_BAR_PP for f in alpha_fall[1:])
        res["verdict"][arm] = {
            "drawdown_gain_pp": {"full": dd_gain[0], "early": dd_gain[1], "late": dd_gain[2]},
            "alpha_fall_pp": {"full": alpha_fall[0], "early": alpha_fall[1],
                              "late": alpha_fall[2]},
            "drawdown_leg_passes_both_halves": bool(dd_ok),
            "alpha_leg_passes_both_halves": bool(al_ok),
            "eligible": bool(dd_ok and al_ok),
            "note": ("ELIGIBLE is not ADOPTED - adoption is a vintage event. The 2.0pp drawdown "
                     "bar is UNCALIBRATED (X7 calibrates no drawdown floor); the 1.0pp alpha leg "
                     "sits BELOW X7's 1.95pp calibrated alpha margin, so a pass means 'no alpha "
                     "loss detectable at this panel's resolution', never 'the loss is under "
                     "1pp'.")}

    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)
    print(f"[s10] wrote {args.json}", flush=True)

    # ---- console summary
    print("\n=== COVERAGE (read before any verdict) ===")
    c = res["coverage"]
    print(f"  top-decile rows          {c['top_decile_rows']:,}")
    print(f"  bull-case coverage       {c['top_decile_bull_coverage']:.2%}")
    print(f"  FLAGGED (bull <= price)  {c['top_decile_flagged']:,} "
          f"= {c['top_decile_flagged_frac']:.2%}")
    print(f"  band ordering violations {viol:,} of {int(trio.sum()):,}")
    print("\n=== ARMS (full sample) ===")
    for a, s in res["arms"].items():
        sp = s.get("drawdown_span") or {}
        print(f"  {a:12s} alpha {s['alpha_ann']:+.4%}  bookret {s['book_ret_ann']:+.4%}  "
              f"maxDD {s['max_drawdown']:+.4f} (spans {sp.get('periods')} period(s))  "
              f"sharpe {s['sharpe']:.3f}  n {s['mean_book_size']:.0f}  "
              f"turn {s['turnover_one_way']:.3f}")
    print("\n=== PAIRED vs A0 ===")
    for a, p in res["paired"].items():
        print(f"  {a:12s} dAlpha {p['delta_alpha_ann_pp']:+.4f}pp/yr  HAC t {p['hac_t']:+.4f}  "
              f"n {p['n']}")
    m = res["M1_MECHANISM"]
    print(f"\n=== M1 MECHANISM (within decile) ===")
    print(f"  flagged   {m['flagged_mean_fwd']:+.4%} per 63d  (mean {m['mean_n_flagged']:.0f} names)")
    print(f"  unflagged {m['unflagged_mean_fwd']:+.4%} per 63d  (mean {m['mean_n_unflagged']:.0f} names)")
    print(f"  delta {m['delta_ann_pp']:+.4f}pp/yr   HAC t {m['hac_t']:+.4f}  n {m['n_dates']}")
    d = res["disasters"]
    print(f"\n=== DISASTERS (fwd < -50%) ===")
    print(f"  flagged   {d['flagged']:,} ({d['flagged_rate']:.3%})")
    print(f"  unflagged {d['unflagged']:,} ({d['unflagged_rate']:.3%})")
    print("\n=== VERDICT ===")
    for a, v in res["verdict"].items():
        print(f"  {a}: eligible={v['eligible']}  dd_leg={v['drawdown_leg_passes_both_halves']}  "
              f"alpha_leg={v['alpha_leg_passes_both_halves']}")
        print(f"     drawdown gain pp {v['drawdown_gain_pp']}")
        print(f"     alpha fall   pp {v['alpha_fall_pp']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
