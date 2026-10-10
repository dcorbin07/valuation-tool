"""DIP-CALL-3 — THE FREE PRE-OUTCOME KILL PASS for the 1999-2008 era. Own invocation.

Register: `PREREG_dipcall3.md`, committed ALONE at `4d50597`. Trials booked at `6c40cb4`
(equity 293 -> 297) BEFORE this file existed.

`O10`'s process defect was a gating control and its outcome statistics sharing one pass, so it
could not be claimed the control was read first. **This file computes NO forward return, NO
abnormal return and NO arm statistic.** `scripts/dipcall3_arm.py` REFUSES without its artifact.

THE KILLS (§3), any one of which stops the program at zero further trials:
  K0  coverage and TIER SIZE -- the 155 price-file-less tier names counted, and every date must
      clear CONTRACT_MIN_POSITIONS = 50 on the governing population
  K1  the design effect against its OWN shuffled null (R3), and the required-n REFUSAL at
      max(1865, the requirement re-derived from THIS era's own measured dispersion)  [B3]
  K2  news coverage >= 0.70 of tier names ON THE COVERED SUBSET ONLY -- meaningless on the full
      era, where code-22 coverage is zero by construction  [B1]
  K3  the event must not be a volatility sort -- A3's TWO forms, fires if EITHER exceeds  [B7]
  K4  the dispersion MEASURED on this era's own rows and the power table re-derived  [A10]

Every scoring primitive is IMPORTED from the landed modules and never re-implemented (`B7`): the
event construction from `valuation.studies.dipcall`, the shuffled-null design effect from the
shipped `options_stats.effective_n`, the power arithmetic from `power_gate`.

Usage:  python -m scripts.dipcall3_kills [--k 2.5] [--limit N]
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_stats, power_gate, research_log            # noqa: E402
from valuation.edge.event_spine import EventSpine                            # noqa: E402
from valuation.edge.statistics import hlz_hurdle                             # noqa: E402
from valuation.studies import dipcall as D                                   # noqa: E402

PREFIX = "DIPCALL3"
ERA = D.ERA_OOS9908
_NEWS_CODE = {D.NEWS: 0, D.NO_NEWS: 1, D.UNKNOWN: 2}
# `B3`: the correctly-paired reference requirement on DIP-CALL-2's OWN measured dispersion. The
# committed bar is the LARGER of this and the era's own re-derived figure, so the correction can
# only RAISE it.
REQUIRED_N_FLOOR = 1865
# DIP-CALL-2's banked market-adjusted effects -- the hypothesis under test, charged as an input
# and never re-derived (`MB4`).
BANKED_EFFECT_PP = {63: 1.1176, 126: 1.6367}


def build_event_set(k: float, limit: int = 0) -> tuple:
    """The PRE-OUTCOME event frame for the era. No forward return is computed here."""
    cfg = D.era(ERA)
    lo, hi = cfg["lo"], cfg["hi"]
    sched, universe = D.tier_schedule_era(ERA)
    ever_tier = [t for t, v in sched.items()
                 if v and max(c for _, c in v) >= D.TIER_FLOOR]
    with_file = [t for t in ever_tier
                 if os.path.isfile(os.path.join(D.prices_dir(), "%s.csv" % t))]
    missing = sorted(set(ever_tier) - set(with_file))
    if limit:
        with_file = with_file[:limit]

    ev_rows, sc_rows, per_date_tier, meta = [], [], {}, []
    scoreable = tier_scoreable = 0
    vol_tier = []
    t0 = time.time()
    for i, t in enumerate(with_file):
        f = D.name_frame(t, sched.get(t, []), k=k)
        if f is None:
            continue
        b = f[(f["date"] >= lo) & (f["date"] <= hi)]
        if not len(b):
            continue
        sc = b["scoreable"].to_numpy()
        tr = b["tier"].to_numpy()
        scoreable += int(sc.sum())
        tier_scoreable += int((sc & tr).sum())
        v = b["vol"].to_numpy(dtype=float)
        vol_tier.append(v[sc & tr])
        if sc.any():
            sc_rows.append(b.loc[sc, ["date", "ticker", "vol", "ret", "event", "tier"]])
        for d in b.loc[tr, "date"].tolist():
            per_date_tier[d] = per_date_tier.get(d, 0) + 1
        e = b[b["event"]]
        if len(e):
            ev_rows.append(e[["ticker", "date", "session_idx", "z", "vol", "tier"]])
        meta.append((t, f["date"].tolist()))
        if i and i % 150 == 0:
            print("  %d/%d names, %s scoreable name-days, %.0fs"
                  % (i, len(with_file), "{:,}".format(scoreable), time.time() - t0))

    if not ev_rows:
        raise SystemExit("REFUSING: no events built -- the inputs did not load")
    events = pd.concat(ev_rows, ignore_index=True)
    cal = {t: {"dates": dd, "date_to_idx": {d: j for j, d in enumerate(dd)}} for t, dd in meta}
    summary = {
        "era": ERA, "era_window": [lo, hi],
        "panel_names": len(universe),
        "names_ever_in_tier": len(ever_tier),
        "names_ever_in_tier_with_price_file": len(with_file if not limit else with_file),
        "names_ever_in_tier_WITHOUT_price_file": len(missing),
        "price_file_coverage_of_tier": (len(with_file) / len(ever_tier)) if ever_tier else None,
        "missing_tier_names": missing[:200],
        "scoreable_name_days_full": scoreable,
        "scoreable_name_days_tier": tier_scoreable,
        "events_full": int(len(events)), "events_tier": int(events["tier"].sum()),
        "sessions": int(events["date"].nunique()),
        "trailing_daily_sd_tier_median": float(np.median(np.concatenate(vol_tier)))
        if len(np.concatenate(vol_tier)) else None,
        "build_seconds": round(time.time() - t0, 1),
    }
    return events, summary, per_date_tier, cal, pd.concat(sc_rows, ignore_index=True)


def classify(events: pd.DataFrame, cal: dict) -> tuple:
    """`A1` + `A1b` + `B1`. Returns (events, coverage report)."""
    cfg = D.era(ERA)
    names = sorted(set(events["ticker"].astype(str)))
    spine = EventSpine.build(names=names, csv_path=D.events_csv())
    ann, unknown_by_name = {}, []
    for t in names:
        a = D.announce_sessions(spine, t, cal[t]["date_to_idx"])
        if a is None:
            unknown_by_name.append(t)
        ann[t] = a

    base = [_NEWS_CODE[D.news_class(spine, t, si, ann.get(t))]
            for t, si in zip(events["ticker"].astype(str).tolist(),
                             events["session_idx"].tolist())]
    gated, n_gated = D.apply_news_era_gate(
        events["date"].tolist(), base, cfg["news_lo"], _NEWS_CODE[D.NEWS],
        _NEWS_CODE[D.UNKNOWN])
    inv = {v: k for k, v in _NEWS_CODE.items()}
    events = events.copy()
    events["news"] = [inv[int(c)] for c in gated]
    events["in_news_era"] = events["date"] >= cfg["news_lo"]

    sub = events[events["in_news_era"] & events["tier"]]
    tier_names_sub = sorted(set(sub["ticker"].astype(str)))
    known = [t for t in tier_names_sub if ann.get(t) is not None]
    cov = {
        "news_lo": cfg["news_lo"],
        "rows_gated_to_unknown_BY_ERA": n_gated,
        "share_of_tier_events_before_news_lo":
            float((~events.loc[events["tier"], "in_news_era"]).mean()),
        "covered_subset_tier_names": len(tier_names_sub),
        "covered_subset_tier_names_with_coverage": len(known),
        "covered_subset_coverage": (len(known) / len(tier_names_sub)) if tier_names_sub else None,
        "floor": D.EARNINGS_COVERAGE_FLOOR,
        "unknown_by_name_count": len(unknown_by_name),
        "unknown_tier_names_in_subset": sorted(set(tier_names_sub) - set(known))[:200],
        "class_counts_tier_full_era": {c: int(((events["news"] == c) & events["tier"]).sum())
                                       for c in (D.NEWS, D.NO_NEWS, D.UNKNOWN)},
        "class_counts_tier_covered_subset": {c: int((sub["news"] == c).sum())
                                             for c in (D.NEWS, D.NO_NEWS, D.UNKNOWN)},
        "note": "B1: an event before code 22's own first date is UNKNOWN BY ERA and enters "
                "neither news arm. K2 gates the NO-NEWS cells only; on the full era news "
                "coverage is zero by construction and the bar is meaningless there.",
    }
    cov["pass"] = bool(cov["covered_subset_coverage"] is not None
                       and cov["covered_subset_coverage"] >= D.EARNINGS_COVERAGE_FLOOR)
    return events, cov


def cells(events: pd.DataFrame, cal: dict, market_dates) -> tuple:
    """`B2`'s four primary cells, after `B6`'s horizon rule and the embargo."""
    cfg = D.era(ERA)
    idx = {d: j for j, d in enumerate(market_dates)}
    last = len(market_dates) - 1
    ev = events.copy()
    ev["dcode"] = [idx.get(d, -1) for d in ev["date"].tolist()]
    is_early = np.array([d < cfg["half_boundary"] for d in market_dates])
    is_early_news = np.array([d < cfg["news_half_boundary"] for d in market_dates])

    out = {}
    for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]:
        cut = max(0, last - h)
        j2 = np.minimum(np.arange(len(market_dates)) + h, last)
        emb = is_early & (~is_early[j2])
        emb_news = is_early_news & (~is_early_news[j2])
        ok = (ev["dcode"] >= 0) & (ev["dcode"] <= cut)
        d = ev["dcode"].to_numpy()
        safe = np.clip(d, 0, None)
        ev["ok_h%d" % h] = ok & (~emb[safe])
        ev["ok_news_h%d" % h] = ok & (~emb_news[safe])
        ev["early_h%d" % h] = is_early[safe]
        ev["early_news_h%d" % h] = is_early_news[safe]

    for h in cfg["horizons_primary"]:
        # cells 1-2: POOLED on the FULL era
        m = ev["tier"] & ev["ok_h%d" % h]
        for half, hm in (("early", ev["early_h%d" % h]), ("late", ~ev["early_h%d" % h])):
            out["pooled|h%d|%s" % (h, half)] = int((m & hm).sum())
        out["pooled|h%d|full" % h] = int(m.sum())
        # cells 3-4: NO-NEWS on the COVERED SUBSET
        n = (ev["tier"] & ev["ok_news_h%d" % h] & ev["in_news_era"]
             & (ev["news"] == D.NO_NEWS))
        for half, hm in (("early", ev["early_news_h%d" % h]),
                         ("late", ~ev["early_news_h%d" % h])):
            out["no_news|h%d|%s" % (h, half)] = int((n & hm).sum())
        out["no_news|h%d|full" % h] = int(n.sum())
        # the NEWS arm is a declared sensitivity carrying NO verdict
        w = (ev["tier"] & ev["ok_news_h%d" % h] & ev["in_news_era"]
             & (ev["news"] == D.NEWS))
        out["SENSITIVITY_news|h%d|full" % h] = int(w.sum())
    return out, ev


def design_effect(ev: pd.DataFrame, cell_counts: dict, sd_by_h: dict, n_eq: int) -> dict:
    """`K1`. `R3`: a RAW design effect is not evidence of clustering -- 600 independent draws in 12
    blocks returned one near 1.8 from sampling error alone -- so the shipped
    `options_stats.effective_n` is CALLED and scores the observed figure against a null that
    shuffles outcomes across blocks preserving every block size exactly.

    THE VARIABLE IS THE EVENT-DAY z, NOT AN OUTCOME: a design effect is a within-cluster
    correlation OF SOMETHING, and the only quantity a pre-outcome pass may read is the event day.
    The library's field is named `pnl_pct` because that is its shipped schema; the VALUE is the
    event-day z and is declared as such.
    """
    cfg = D.era(ERA)
    out, refused = {}, []
    for h in cfg["horizons_primary"]:
        req_era = power_gate.required_n(BANKED_EFFECT_PP[h] / sd_by_h[h], n_trials=n_eq)
        bar = max(float(REQUIRED_N_FLOOR), float(req_era))
        for arm in ("pooled", "no_news"):
            if arm == "pooled":
                m = ev["tier"] & ev["ok_h%d" % h]
            else:
                m = (ev["tier"] & ev["ok_news_h%d" % h] & ev["in_news_era"]
                     & (ev["news"] == D.NO_NEWS))
            a = ev[m]
            key = "%s|h%d" % (arm, h)
            if len(a) < 50:
                out[key] = {"ok": False, "n": int(len(a)), "bar": bar}
                refused.append(key)
                continue
            rows = [{"alert_ts": d, "pnl_pct": float(z)}
                    for d, z in zip(a["date"].tolist(), a["z"].tolist())]
            r = options_stats.effective_n(rows, block="day", null_draws=200, seed=0)
            r["variable"] = "event-day z (PRE-OUTCOME, not a return)"
            r["bracket_lower_rho1_distinct_days"] = r.get("n_blocks")
            r["bracket_upper_raw"] = r.get("n")
            r["required_n_floor_B3"] = REQUIRED_N_FLOOR
            r["required_n_era_own_dispersion"] = float(req_era)
            r["bar"] = bar
            r["effect_pp_tested"] = BANKED_EFFECT_PP[h]
            r["era_sd_pp"] = sd_by_h[h]
            # The BRACKET is reported and the bar is applied to the CONSERVATIVE end that the
            # measurement supports: n_eff_icc where clustering is measurable, n_blocks where it
            # is not (the assumption-free floor). Never the raw count alone.
            n_eff = (r["n_eff_icc"] if r.get("clustering_measurable")
                     else float(r["n_blocks"]))
            r["n_eff_applied"] = float(n_eff)
            r["clears_required_n"] = bool(n_eff >= bar)
            if not r["clears_required_n"]:
                refused.append(key)
            out[key] = r
    return {"by_cell": out, "cells_refused": sorted(set(refused)),
            "pass": bool(not refused),
            "note": "K1 REFUSES a cell whose effective n falls below max(1865, the requirement "
                    "re-derived from THIS era's own measured dispersion) -- PREREG_dipcall3.md "
                    "B3. The effective-n BRACKET is reported, never either end alone, and the "
                    "INFERENCE does not rest on this figure: A2 makes the arm's standard errors "
                    "cluster-robust on BOTH event date and ticker."}


def volatility_sort(d: pd.DataFrame) -> dict:
    """`K3` / `B7`. A3's TWO forms; the kill fires if EITHER exceeds. The one-sided ratio bar is
    deliberate -- the kill guards against "a -2.5 sigma day is just a volatile name", which is a
    TOP-heavy gradient -- and the magnitudes ship either way."""
    out = {}
    for pop in ("tier", "full"):
        x = d[d["tier"]] if pop == "tier" else d
        q = x.groupby("date")["vol"].rank(pct=True)
        bins = np.clip((q.to_numpy() * 5).astype(int), 0, 4)
        ev = x["event"].to_numpy()
        ret = x["ret"].to_numpy(dtype=float)
        rates, mags, sds = [], [], []
        for b in range(5):
            m = bins == b
            rates.append(float(ev[m].mean()) if m.any() else float("nan"))
            me = m & ev
            mags.append(float(np.median(ret[me]) * 100.0) if me.any() else float("nan"))
            sds.append(float(np.median(x["vol"].to_numpy(dtype=float)[m]) * 100.0)
                       if m.any() else float("nan"))
        ratio = (rates[4] / rates[0]) if rates[0] and rates[0] == rates[0] else float("inf")
        rhos = []
        for _, g in x.groupby("date"):
            if g["event"].nunique() < 2 or len(g) < 20:
                continue
            a = g["event"].to_numpy(dtype=float)
            r = g["vol"].rank(pct=True).to_numpy(dtype=float)
            if a.std() == 0 or r.std() == 0:
                continue
            rhos.append(abs(float(np.corrcoef(a, r)[0, 1])))
        mean_rho = float(np.mean(rhos)) if rhos else None
        rec = {"event_rate_by_vol_quintile_low_to_high":
               [None if r != r else round(r, 6) for r in rates],
               "median_event_day_move_pp_by_quintile":
               [None if m != m else round(m, 4) for m in mags],
               "median_trailing_daily_sd_pp_by_quintile":
               [None if s != s else round(s, 4) for s in sds],
               "top_over_bottom_ratio": None if ratio != ratio else round(float(ratio), 4),
               "ratio_bar": D.VOL_QUINTILE_RATIO_BAR,
               "mean_per_date_abs_rho": None if mean_rho is None else round(mean_rho, 6),
               "rho_bar": D.VOL_RHO_BAR, "dates_scored_for_rho": len(rhos),
               "n_scoreable": int(len(x))}
        rec["fires_on_ratio"] = bool(ratio == ratio and ratio >= D.VOL_QUINTILE_RATIO_BAR)
        rec["fires_on_rho"] = bool(mean_rho is not None and mean_rho >= D.VOL_RHO_BAR)
        rec["fires"] = bool(rec["fires_on_ratio"] or rec["fires_on_rho"])
        out[pop] = rec
    return {"by_population": out, "pass": bool(not out["tier"]["fires"])}


def power(summary: dict, n_eq: int) -> dict:
    """`K4` / `A10`. The dispersion MEASURED on this era's own rows, pre-outcome, and the power
    table re-derived from it. The direction of the error is labelled: a trailing estimate
    understates post-event dispersion, which OVERSTATES power -- the unsafe direction -- and the
    MDE that travels with any verdict comes from the arm's own REALISED clustered se (`MB8`)."""
    cfg = D.era(ERA)
    crit = hlz_hurdle(n_eq)
    sd_daily = summary["trailing_daily_sd_tier_median"]
    rows, sd_by_h = {}, {}
    for h in cfg["horizons_primary"] + cfg["horizons_sensitivity"]:
        sd_h = float(sd_daily * np.sqrt(h) * 100.0)
        sd_by_h[h] = sd_h
        need = {}
        for eff in (D.ECONOMIC_FLOOR_PP, 1.0, BANKED_EFFECT_PP.get(h, 1.0), 2.0):
            need["%+.4fpp" % eff] = int(np.ceil(
                power_gate.required_n(eff / sd_h, n_trials=n_eq)))
        rows["h%d" % h] = {
            "measured_sd_pp": round(sd_h, 4),
            "dipcall2_measured_tier_sd_own_pp": {63: 19.352, 126: 33.986}.get(h),
            "dipcall2_measured_tier_sd_mkt_pp": {63: 11.453, 126: 16.737}.get(h),
            "required_n_at_80pc_power": need,
        }
    return {"crit_hlz_derived": crit, "n_trials_equity": n_eq,
            "median_trailing_daily_sd_tier": sd_daily,
            "by_horizon": rows, "sd_by_h": sd_by_h,
            "direction_of_error": "UPPER BOUND ON POWER -- a trailing pre-outcome estimate "
                                  "understates post-event dispersion because volatility is "
                                  "clustered, so it understates the required n. The UNSAFE "
                                  "direction, and the verdict's MDE comes from the arm's "
                                  "REALISED se instead.",
            "pass": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=D.K_PRIMARY)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    cfg = D.era(ERA)
    n_eq = research_log.trial_count(domain="equity")
    print("DIP-CALL-3 FREE KILL PASS [%s]  era %s..%s  k = %.1f"
          % (PREFIX, cfg["lo"], cfg["hi"], a.k))
    print("equity N = %d ; hurdle %.7f ; NO forward return is computed in this file.\n"
          % (n_eq, hlz_hurdle(n_eq)))

    print("building the pre-outcome event set ...")
    events, summary, per_date_tier, cal, scoreable = build_event_set(a.k, a.limit)
    print("  tier names %d of %d ever-tier have a price file (%.4f); %d MISSING and counted"
          % (summary["names_ever_in_tier_with_price_file"], summary["names_ever_in_tier"],
             summary["price_file_coverage_of_tier"],
             summary["names_ever_in_tier_WITHOUT_price_file"]))
    print("  %s scoreable name-days (tier %s); %s events (tier %s) over %d sessions\n"
          % ("{:,}".format(summary["scoreable_name_days_full"]),
             "{:,}".format(summary["scoreable_name_days_tier"]),
             "{:,}".format(summary["events_full"]),
             "{:,}".format(summary["events_tier"]), summary["sessions"]))

    print("K2  classifying news (A1 + A1b + B1's era gate) ...")
    events, k2 = classify(events, cal)
    print("  %s of tier events predate code 22 (%s) and are UNKNOWN BY ERA"
          % ("{:.4f}".format(k2["share_of_tier_events_before_news_lo"]), k2["news_lo"]))
    print("  covered-subset coverage %.4f against floor %.2f ; %s"
          % (k2["covered_subset_coverage"], k2["floor"], "PASS" if k2["pass"] else "FIRES"))
    print("  class counts, full era %s ; covered subset %s\n"
          % (k2["class_counts_tier_full_era"], k2["class_counts_tier_covered_subset"]))

    print("K4  dispersion measured on this era's own rows (A10) ...")
    k4 = power(summary, n_eq)
    for h, r in k4["by_horizon"].items():
        print("  %-5s measured sd %8.3fpp   (DIP-CALL-2 measured own %s / mkt %s)  need %s"
              % (h, r["measured_sd_pp"], r["dipcall2_measured_tier_sd_own_pp"],
                 r["dipcall2_measured_tier_sd_mkt_pp"], r["required_n_at_80pc_power"]))
    print()

    print("K0 + cells  counting the four primary cells (B2, B6) ...")
    market_dates = sorted(set(scoreable["date"].astype(str)))
    counts, ev = cells(events, cal, market_dates)
    for key in sorted(counts):
        print("  %-30s %7s" % (key, "{:,}".format(counts[key])))
    print()

    print("K1  design effect vs its OWN shuffled null, and the required-n refusal (R3, B3) ...")
    k1 = design_effect(ev, counts, k4["sd_by_h"], n_eq)
    for key, r in sorted(k1["by_cell"].items()):
        if not r.get("ok"):
            print("  %-16s too thin to score: n %s" % (key, r.get("n")))
            continue
        print("  %-16s n %7s blocks %6s deff %.4f vs p95 %.4f measurable=%-5s "
              "n_eff %8.1f vs bar %8.1f -> %s"
              % (key, "{:,}".format(r["n"]), "{:,}".format(r["n_blocks"]),
                 r["design_effect"], r["design_effect_null_p95"],
                 str(r["clustering_measurable"]), r["n_eff_applied"], r["bar"],
                 "ok" if r["clears_required_n"] else "REFUSED"))
    print()

    print("K3  is the event a volatility sort? (B7, two forms) ...")
    k3 = volatility_sort(scoreable)
    for pop, r in k3["by_population"].items():
        print("  %-5s rate by vol quintile %s" % (pop, r["event_rate_by_vol_quintile_low_to_high"]))
        print("        median event-day move pp %s" % r["median_event_day_move_pp_by_quintile"])
        print("        top/bottom %s (bar %.1f) ; mean |rho| %s (bar %.2f) ; %s"
              % (r["top_over_bottom_ratio"], r["ratio_bar"], r["mean_per_date_abs_rho"],
                 r["rho_bar"], "FIRES" if r["fires"] else "pass"))
    print()

    pdt = sorted(per_date_tier.items())
    cts = [c for _, c in pdt]
    tier_size = {"per_date_min": int(min(cts)) if cts else 0,
                 "per_date_median": int(np.median(cts)) if cts else 0,
                 "per_date_max": int(max(cts)) if cts else 0,
                 "dates": len(cts),
                 "contract_min_positions": D.CONTRACT_MIN_POSITIONS,
                 "dates_below_floor": int(sum(1 for c in cts
                                              if c < D.CONTRACT_MIN_POSITIONS)),
                 "first_date": pdt[0][0] if pdt else None,
                 "last_date": pdt[-1][0] if pdt else None}
    tier_size["pass"] = bool(tier_size["dates_below_floor"] == 0)
    print("K0  tier size per date: min %d median %d max %d over %d dates ; below the %d-position "
          "floor on %d dates ; %s"
          % (tier_size["per_date_min"], tier_size["per_date_median"], tier_size["per_date_max"],
             tier_size["dates"], D.CONTRACT_MIN_POSITIONS, tier_size["dates_below_floor"],
             "PASS" if tier_size["pass"] else "NOT ASSESSABLE on the governing population"))
    # B4's disclosed staleness: the tier source ends 2008-07-10, so H2-2008 events carry the
    # July cap. Flagged so a reader can see how much of any result rests on them.
    h2 = events[events["tier"] & (events["date"] >= "2008-07-11")]
    tier_size["h2_2008_tier_events_on_a_stale_cap"] = int(len(h2))
    print("  H2-2008 tier events carrying the stale 2008-07-10 cap: %s (B4, disclosed)\n"
          % "{:,}".format(len(h2)))

    gates = {"K0_tier_size": tier_size["pass"], "K1_design_effect_and_required_n": k1["pass"],
             "K2_news_coverage": k2["pass"], "K3_not_a_volatility_sort": k3["pass"],
             "K4_power_table": k4["pass"]}
    all_pass = all(gates.values())

    art = {"item": "DIP-CALL-3 free pre-outcome kill pass",
           "register": "PREREG_dipcall3.md committed ALONE at 4d50597",
           "trials_booked_at": "6c40cb4 (equity 293 -> 297)",
           "trials_this_pass": 0,
           "forward_return_touched": False, "abnormal_return_touched": False,
           "k": a.k, "era": ERA, "era_window": [cfg["lo"], cfg["hi"]],
           "half_boundary": cfg["half_boundary"],
           "news_half_boundary": cfg["news_half_boundary"],
           "equity_N": n_eq, "hlz_hurdle_equity": hlz_hurdle(n_eq),
           "summary": summary, "cell_counts": counts, "tier_size_per_date": tier_size,
           "K1_design_effect": k1, "K2_news_coverage": k2, "K3_volatility_sort": k3,
           "K4_power": k4, "gates": gates, "all_kills_pass": all_pass,
           "cells_cleared_for_the_arm": sorted(
               set("%s|h%d" % (arm, h) for arm in ("pooled", "no_news")
                   for h in cfg["horizons_primary"]) - set(k1["cells_refused"]))}
    with io.open(D.out_path("%s_KILLS.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    ev.to_pickle(D.out_path("%s_EVENTS.pkl" % PREFIX))

    print("=" * 78)
    for g, v in gates.items():
        print("  %-34s %s" % (g, "PASS" if v else "FIRES"))
    print("  ALL KILLS PASS: %s" % all_pass)
    print("  cells cleared for the arm: %s" % (art["cells_cleared_for_the_arm"] or "NONE"))
    print("=" * 78)
    print("wrote %s" % D.out_path("%s_KILLS.json" % PREFIX))
    return 0 if all_pass else 3


if __name__ == "__main__":
    sys.exit(main())
