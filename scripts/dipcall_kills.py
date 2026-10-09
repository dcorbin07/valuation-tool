"""DIP-CALL step 1 — THE FREE PRE-OUTCOME KILL PASS. Run and read in its OWN invocation.

Register: `PREREG_dipcall.md`, committed ALONE at `c5e0b31`. Trials booked at `a984ec9`
(equity 274 -> 278) BEFORE this file existed.

`O10`'s process defect was that a gating control and its outcome statistics ran in one pass, so it
could not be claimed the control was read first. This file computes NO forward return, NO abnormal
return and NO arm statistic. `scripts/dipcall_arm.py` REFUSES to run without this file's artifact
reporting `all_kills_pass`.

THE FIVE KILLS (§2g), any one of which stops the program at zero further trials:
  K1  event count >= 1,500 in each news arm in each half, on the arm's own rows
  K2  earnings coverage >= 0.70 of tier names, UNKNOWN counted and excluded BY NAME
  K3  the design effect measured against its OWN shuffled null (R3)
  K4  the event must not be a volatility sort -- A3's TWO forms, fires if EITHER exceeds
  K5  the horizon dispersion MEASURED, and the power table re-derived from it (A10)

Usage:  python -m scripts.dipcall_kills [--k 2.5] [--limit N]
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

ART = "DIPCALL_KILLS.json"
EVENTS_PKL = "DIPCALL_EVENTS.pkl"


# ------------------------------------------------------------------------------------ build
def build_event_set(k: float, limit: int = 0) -> tuple:
    """The PRE-OUTCOME event frame for every half-0 name with a price file.

    Returns (events, scoreable_summary, per_date_tier, names). `events` carries one row per
    (ticker, event date) with the event-day z, the trailing volatility, the session index, the
    point-in-time tier flag and the name's own session count -- and NOTHING measured after the
    event day.
    """
    sched = D.tier_schedule()
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    bq = panel[(panel["date"] >= "2009") & (panel["date"] <= D.BUILD_HI)]
    half0 = sorted(set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"]))
    if limit:
        half0 = half0[:limit]

    ev_rows, meta, per_date_tier = [], [], {}
    # Pre-outcome dispersion inputs (K5): the trailing daily vol on the arm's own rows.
    scoreable_days = tier_scoreable_days = 0
    vol_all, vol_tier, sc_rows = [], [], []
    with_prices = 0
    t0 = time.time()
    for i, t in enumerate(half0):
        f = D.name_frame(t, sched.get(t, []), k=k)
        if f is None:
            continue
        with_prices += 1
        inb = (f["date"] >= D.BUILD_LO) & (f["date"] <= D.BUILD_HI)
        b = f[inb]
        if not len(b):
            continue
        sc = b["scoreable"].to_numpy()
        tr = b["tier"].to_numpy()
        scoreable_days += int(sc.sum())
        tier_scoreable_days += int((sc & tr).sum())
        v = b["vol"].to_numpy(dtype=float)
        vol_all.append(v[sc])
        vol_tier.append(v[sc & tr])
        # K4 needs every SCOREABLE name-day, not only the events. Kept here so the kill pass
        # makes ONE pass over the price files rather than two: a second pass would be a second
        # chance for the two readings to describe different row sets.
        if sc.any():
            sc_rows.append(b.loc[sc, ["date", "ticker", "vol", "ret", "event", "tier"]])
        # Charter Stage 1b: the per-date tier name count must ship.
        for d in b.loc[tr, "date"].tolist():
            per_date_tier[d] = per_date_tier.get(d, 0) + 1
        e = b[b["event"]]
        if len(e):
            ev_rows.append(e[["ticker", "date", "session_idx", "z", "vol", "tier"]])
        meta.append((t, int(len(f)), f["date"].tolist(), f["session_idx"].tolist()))
        if i and i % 400 == 0:
            print("  %d/%d names, %s scoreable name-days, %.0fs"
                  % (i, len(half0), "{:,}".format(scoreable_days), time.time() - t0))

    if not ev_rows:
        raise SystemExit("REFUSING: no events built -- the inputs did not load")
    events = pd.concat(ev_rows, ignore_index=True)

    # The name's own session calendar, needed by A1's news window and by the horizon rules.
    cal = {t: {"n": n, "dates": dates, "idx": idx} for t, n, dates, idx in meta}
    # The last build-quadrant session index per name (implementation decision 1).
    for t, c in cal.items():
        dd = c["dates"]
        last = -1
        for j, d in enumerate(dd):
            if d <= D.BUILD_HI:
                last = j
        c["last_build_idx"] = last
        c["date_to_idx"] = {d: j for j, d in enumerate(dd)}

    summary = {
        "names_half0_build_quadrant": len(half0),
        "names_with_prices": with_prices,
        "names_with_events": int(events["ticker"].nunique()),
        "scoreable_name_days_full": scoreable_days,
        "scoreable_name_days_tier": tier_scoreable_days,
        "events_full": int(len(events)),
        "events_tier": int(events["tier"].sum()),
        "sessions": int(events["date"].nunique()),
        "trailing_daily_sd_full_median": float(np.median(np.concatenate(vol_all))),
        "trailing_daily_sd_tier_median": float(np.median(np.concatenate(vol_tier)))
        if len(np.concatenate(vol_tier)) else None,
        "build_seconds": round(time.time() - t0, 1),
    }
    scoreable = pd.concat(sc_rows, ignore_index=True)
    return events, summary, per_date_tier, cal, scoreable


# ------------------------------------------------------------------------- A1 the news split
def classify_news(events: pd.DataFrame, cal: dict) -> tuple:
    """Attach A1's news class. Returns (events, coverage_report)."""
    names = sorted(set(events["ticker"].astype(str)))
    spine = EventSpine.build(names=names, csv_path=D.events_csv())

    ann, unknown_names = {}, []
    for t in names:
        a = D.announce_sessions(spine, t, cal[t]["date_to_idx"])
        if a is None:
            unknown_names.append(t)
        ann[t] = a

    cls = []
    for t, si in zip(events["ticker"].astype(str).tolist(),
                     events["session_idx"].tolist()):
        cls.append(D.news_class(spine, t, si, ann.get(t)))
    events = events.copy()
    events["news"] = cls

    tier_names = sorted(set(events.loc[events["tier"], "ticker"].astype(str)))
    known_tier = [t for t in tier_names if ann.get(t) is not None]
    cov = {
        "tier_names": len(tier_names),
        "tier_names_with_known_coverage": len(known_tier),
        "tier_coverage": (len(known_tier) / len(tier_names)) if tier_names else None,
        "floor": D.EARNINGS_COVERAGE_FLOOR,
        # A1b: UNKNOWN is counted and excluded BY NAME, never read as "no news".
        "unknown_names_count": len(unknown_names),
        "unknown_tier_names": sorted(set(tier_names) - set(known_tier)),
        "spine_source": spine.source,
        "class_counts_full": {c: int((events["news"] == c).sum())
                              for c in (D.NEWS, D.NO_NEWS, D.UNKNOWN)},
        "class_counts_tier": {c: int(((events["news"] == c) & events["tier"]).sum())
                              for c in (D.NEWS, D.NO_NEWS, D.UNKNOWN)},
    }
    cov["pass"] = bool(cov["tier_coverage"] is not None
                       and cov["tier_coverage"] >= D.EARNINGS_COVERAGE_FLOOR)
    return events, cov


# ---------------------------------------------------------------- K1 counts, halves, embargo
def arm_cells(events: pd.DataFrame, cal: dict) -> tuple:
    """Per-(news arm x horizon x half) event counts after the embargo and the
    horizon-inside-the-build-years rule. Returns (cells, events_with_flags)."""
    ev = events.copy()
    for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
        ok, cross = [], []
        for t, si in zip(ev["ticker"].astype(str).tolist(), ev["session_idx"].tolist()):
            c = cal[t]
            ok.append(D.horizon_ok(c["n"], si, h, c["last_build_idx"]))
            cross.append(D.crosses_boundary(c["dates"], si, h))
        ev["ok_h%d" % h] = ok
        ev["cross_h%d" % h] = cross
    ev["half"] = [D.half_of(d) for d in ev["date"].tolist()]

    cells = {}
    for pop, mask in (("tier", ev["tier"]), ("full", pd.Series(True, index=ev.index))):
        for h in D.HORIZONS_PRIMARY:
            usable = mask & ev["ok_h%d" % h] & (~ev["cross_h%d" % h])
            for arm in (D.NEWS, D.NO_NEWS):
                for half in ("early", "late"):
                    n = int((usable & (ev["news"] == arm) & (ev["half"] == half)).sum())
                    cells["%s|h%d|%s|%s" % (pop, h, arm, half)] = n
    tier_cells = {k: v for k, v in cells.items() if k.startswith("tier|")}
    worst = min(tier_cells.values()) if tier_cells else 0
    k1 = {
        "floor": D.MIN_EVENTS_PER_CELL,
        "cells": cells,
        "tier_min_cell": worst,
        "tier_min_cell_name": (min(tier_cells, key=tier_cells.get) if tier_cells else None),
        "dropped_by_embargo": {("h%d" % h): int((ev["tier"] & ev["cross_h%d" % h]).sum())
                               for h in D.HORIZONS_PRIMARY},
        "dropped_horizon_outside_build": {
            ("h%d" % h): int((ev["tier"] & (~ev["ok_h%d" % h])).sum())
            for h in D.HORIZONS_PRIMARY},
        # THE TIER GOVERNS (charter Stage 1b). The full-universe cells ship beside it as a
        # reported surface and do NOT decide the kill.
        "pass": bool(worst >= D.MIN_EVENTS_PER_CELL),
        "note": ("the TIER cells decide this kill because the tier governs advancement "
                 "(RESEARCH_CHARTER.md section 5 Stage 1b); the full-universe cells are a "
                 "reported surface carrying NO verdict"),
    }
    return k1, ev


# --------------------------------------------------------- K3 design effect vs its OWN null
def design_effect(events: pd.DataFrame) -> dict:
    """R3. A RAW DESIGN EFFECT IS NOT EVIDENCE OF CLUSTERING -- 600 independent draws in 12
    blocks returned a design effect near 1.8 from sampling error alone, and applying it as a
    haircut *"would have manufactured a correction out of noise."* So the shipped
    `options_stats.effective_n` is CALLED, never re-implemented, and it scores the observed
    design effect against a null that shuffles outcomes across blocks preserving every block
    size exactly.

    THE VARIABLE IS THE EVENT-DAY z, NOT AN OUTCOME (implementation decision 2). A design effect
    is a within-cluster correlation of SOMETHING, and the only quantity a pre-outcome pass may
    read is the event day itself -- which is also the census's own stated worry, *"a market-wide
    drop creates thousands of simultaneous events that share one shock."* The library's field is
    named `pnl_pct` because that is its shipped schema; the VALUE here is the event-day z and is
    declared as such so nobody reads the figure as a return.
    """
    out = {}
    for pop in ("tier", "full"):
        e = events[events["tier"]] if pop == "tier" else events
        for arm in (D.NEWS, D.NO_NEWS):
            # Each arm's design effect is measured SEPARATELY rather than pooled (draft section
            # 3b): an earnings-dated drop is idiosyncratic and spread across the calendar, a
            # no-news drop is far more likely to be market-driven and therefore clustered.
            a = e[e["news"] == arm]
            if len(a) < 50:
                out["%s|%s" % (pop, arm)] = {"ok": False, "n": int(len(a))}
                continue
            rows = [{"alert_ts": d, "pnl_pct": float(z)}
                    for d, z in zip(a["date"].tolist(), a["z"].tolist())]
            r = options_stats.effective_n(rows, block="day", null_draws=200, seed=0)
            r["variable"] = "event-day z (PRE-OUTCOME, not a return)"
            r["bracket_lower_rho1_distinct_days"] = r.get("n_blocks")
            r["bracket_upper_raw"] = r.get("n")
            out["%s|%s" % (pop, arm)] = r
    return {"by_arm": out,
            "note": ("the effective-n BRACKET is reported, never either end alone. The INFERENCE "
                     "does not rest on this figure: A2 makes the arm's standard errors "
                     "cluster-robust on BOTH event date and ticker, which absorbs within-cluster "
                     "correlation directly instead of applying a haircut."),
            # Diagnostic, never a gate: this kill is REPORTED and cannot stop the program on its
            # own, because R3's whole lesson is that a design effect is not self-interpreting.
            "pass": True}


# ------------------------------------------------- K4 the event must not be a volatility sort
def volatility_sort(d: pd.DataFrame) -> dict:
    """A3. TWO forms, and the kill fires if EITHER exceeds.

    The draft's registered form -- mean per-date |rho| between the event flag and the name's own
    trailing volatility rank -- is small BY CONSTRUCTION here, because at k = 2.5 the flag is 1 on
    roughly 1.5% of a date's rows. A kill that cannot fire is not a kill (W-1's hook guard,
    S3-I3's banned name, MB16's blind statistic, MB15's 60.4%-pass gate). So the discriminating
    form is added: the event rate by trailing-volatility QUINTILE, measured on all scoreable
    name-days, with the top/bottom ratio barred at 3.0x.

    THE BAR IS ONE-SIDED AS REGISTERED, AND THAT IS DELIBERATE. The kill guards against *"a -2.5
    sigma day is just this is a volatile name"*, which is a TOP-heavy gradient. A BOTTOM-heavy
    gradient is a different phenomenon and not the one A3 bars: a low-volatility name's sigma is
    small, so a modest percentage move is a large z. It is therefore REPORTED rather than killed,
    together with the event-day move's MAGNITUDE by quintile, which is the number that says
    whether a low-volatility event is economically a dip at all.
    """
    out = {}
    for pop in ("tier", "full"):
        x = d[d["tier"]] if pop == "tier" else d
        # Quintiles of the trailing volatility, ranked WITHIN each date so the comparison is
        # cross-sectional and not a statement about which years were volatile.
        q = x.groupby("date")["vol"].rank(pct=True)
        bins = np.clip((q.to_numpy() * 5).astype(int), 0, 4)
        rates, mags, sds = [], [], []
        ev = x["event"].to_numpy()
        ret = x["ret"].to_numpy(dtype=float)
        for b_i in range(5):
            m = bins == b_i
            rates.append(float(ev[m].mean()) if m.any() else float("nan"))
            # The event-day move's MAGNITUDE, in percentage points: the number that says whether
            # a low-volatility name's -2.5 sigma day is economically a dip at all.
            me = m & ev
            mags.append(float(np.median(ret[me]) * 100.0) if me.any() else float("nan"))
            sds.append(float(np.median(x["vol"].to_numpy(dtype=float)[m]) * 100.0)
                       if m.any() else float("nan"))
        ratio = (rates[4] / rates[0]) if rates[0] and rates[0] == rates[0] else float("inf")
        # The registered |rho| form, per date, flag against the within-date volatility rank.
        rhos = []
        for dt, g in x.groupby("date"):
            if g["event"].nunique() < 2 or len(g) < 20:
                continue
            a = g["event"].to_numpy(dtype=float)
            r = g["vol"].rank(pct=True).to_numpy(dtype=float)
            if a.std() == 0 or r.std() == 0:
                continue
            rhos.append(abs(float(np.corrcoef(a, r)[0, 1])))
        mean_rho = float(np.mean(rhos)) if rhos else None
        out[pop] = {
            "event_rate_by_vol_quintile_low_to_high": [None if r != r else round(r, 6)
                                                       for r in rates],
            "median_event_day_move_pp_by_quintile": [None if m != m else round(m, 4)
                                                     for m in mags],
            "median_trailing_daily_sd_pp_by_quintile": [None if s != s else round(s, 4)
                                                        for s in sds],
            "top_over_bottom_ratio": None if ratio != ratio else round(float(ratio), 4),
            "ratio_bar": D.VOL_QUINTILE_RATIO_BAR,
            "mean_per_date_abs_rho": None if mean_rho is None else round(mean_rho, 6),
            "rho_bar": D.VOL_RHO_BAR,
            "dates_scored_for_rho": len(rhos),
            "n_scoreable": int(len(x)),
        }
        out[pop]["fires_on_ratio"] = bool(ratio == ratio and ratio >= D.VOL_QUINTILE_RATIO_BAR)
        out[pop]["fires_on_rho"] = bool(mean_rho is not None and mean_rho >= D.VOL_RHO_BAR)
        out[pop]["fires"] = bool(out[pop]["fires_on_ratio"] or out[pop]["fires_on_rho"])

    return {"by_population": out,
            # The TIER governs, consistent with K1.
            "pass": bool(not out["tier"]["fires"]),
            "note": ("A3: fires if EITHER form exceeds. The full five-quintile profile ships "
                     "either way, pass or fail. 3.0x is PRE-COMMITTED and LABELLED UNCALIBRATED "
                     "and is deliberately generous -- a genuine volatility sort reads in the "
                     "TENS, and a bar tight enough to kill a legitimate arm is W-1's K2 error.")}


# --------------------------------------------- K5 the dispersion MEASURED and the power table
def power_table(summary: dict, cells: dict, n_trials_equity: int) -> dict:
    """A10. The draft's 20pp 63-session SD is an ANCHOR; this measures the dispersion on the
    arm's own rows and re-derives the table from it.

    PRE-OUTCOME, SO IT IS AN UPPER BOUND ON POWER (implementation decision 3). The horizon
    dispersion is estimated as the median trailing DAILY sd on the arm's own rows scaled by
    sqrt(h). Volatility is clustered, so realised post-event dispersion EXCEEDS this -- which
    UNDERSTATES the required n and so OVERSTATES power. That is the unsafe direction and is
    labelled rather than hidden: the MDE that travels with the verdict comes from the arm's own
    REALISED sd (MB8: never borrow an se).
    """
    crit = hlz_hurdle(n_trials_equity)
    sd_daily = summary["trailing_daily_sd_tier_median"]
    rows = {}
    for h in D.HORIZONS_PRIMARY + D.HORIZONS_SENSITIVITY:
        sd_h_pp = float(sd_daily * np.sqrt(h) * 100.0)
        need = {}
        # The economic floor is IMPORTED, never retyped -- `MA5`'s lesson, and this line is where
        # the shipped guard in `tests/test_dipcall.py` actually fired on its first run.
        for eff in (0.25, 0.5, D.ECONOMIC_FLOOR_PP, 1.0, 2.0):
            need["+%.2fpp" % eff] = int(np.ceil(
                power_gate.required_n(eff / sd_h_pp, n_trials=n_trials_equity)))
        avail = cells["cells"].get("tier|h%d|%s|%s" % (h, D.NO_NEWS, "early"), 0) if h in \
            D.HORIZONS_PRIMARY else None
        rows["h%d" % h] = {"measured_sd_pp": round(sd_h_pp, 4),
                           "anchor_sd_pp_draft": round(20.0 * np.sqrt(h / 63.0), 4),
                           "required_n_at_80pc_power": need,
                           "smallest_tier_cell_at_this_horizon": avail}
    return {"crit_hlz_derived": crit, "n_trials_equity": n_trials_equity,
            "median_trailing_daily_sd_tier": sd_daily,
            "by_horizon": rows,
            "direction_of_error": ("UPPER BOUND ON POWER -- the trailing estimate understates "
                                   "post-event dispersion because volatility is clustered, so "
                                   "it understates the required n. The UNSAFE direction, and the "
                                   "verdict's MDE comes from the arm's REALISED sd instead."),
            "pass": True}


# --------------------------------------------------------------------------- cap-sanity report
def cap_sanity() -> dict:
    """REPORTED, NOT A KILL, and declared BEFORE any outcome exists.

    A defect found in the corrected panel while implementing A12, and it is NOT this lane's file:
    `AEHL`'s `market_cap` reads 1.131e12 on 2010-12-27 between a 5.418e7 quarter and a 2.697e8
    quarter. A corrupt cap injects a micro-cap into a tier whose entire purpose is *"an extremely
    liquid, rock-solid company"*. Measured exposure: ONE name of the 459 ever in the tier.

    The REGISTERED rule is the panel's `market_cap` as it stands and that is the PRIMARY; a
    cap-sanity exclusion is declared here as a SENSITIVITY carrying no verdict, before any
    outcome, so it cannot be reached for afterwards.
    """
    sched = D.tier_schedule()
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    bq = panel[(panel["date"] >= "2009") & (panel["date"] <= D.BUILD_HI)]
    half0 = set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"])
    susp, ever = [], 0
    for t, v in sched.items():
        if t not in half0:
            continue
        caps = np.array([c for d, c in v if "2009" <= d <= D.BUILD_HI], dtype=float)
        if not len(caps) or not (caps >= D.TIER_FLOOR).any():
            continue
        ever += 1
        if len(caps) > 1:
            r = caps[1:] / np.maximum(caps[:-1], 1.0)
            if (r > 20).any() and (r < 1 / 20.0).any():
                susp.append({"ticker": t, "cap_min": float(caps.min()),
                             "cap_max": float(caps.max())})
    return {"names_ever_in_tier": ever, "census_control_459": ever == 459,
            "suspect_names": susp, "detector": ">20x round-trip cap jump between quarters",
            "treatment": "REPORTED. Primary uses the registered rule unchanged; a cap-sanity "
                         "exclusion is a declared SENSITIVITY carrying no verdict.",
            "pass": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=float, default=D.K_PRIMARY)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    n_eq = research_log.trial_count(domain="equity")
    print("DIP-CALL step 1 — FREE KILL PASS. k = %.1f ; equity N = %d ; hurdle %.7f"
          % (a.k, n_eq, hlz_hurdle(n_eq)))
    print("NO forward return and NO abnormal return is computed in this file.\n")

    print("building the pre-outcome event set ...")
    events, summary, per_date_tier, cal, scoreable = build_event_set(a.k, a.limit)
    print("  %s scoreable name-days (tier %s); %s events (tier %s) over %d sessions\n"
          % ("{:,}".format(summary["scoreable_name_days_full"]),
             "{:,}".format(summary["scoreable_name_days_tier"]),
             "{:,}".format(summary["events_full"]),
             "{:,}".format(summary["events_tier"]), summary["sessions"]))

    print("K2  classifying news (A1: i - j in {0,1} SESSIONS; UNKNOWN is a third state) ...")
    events, k2 = classify_news(events, cal)
    print("  tier coverage %.4f against floor %.2f ; %s\n"
          % (k2["tier_coverage"], k2["floor"], "PASS" if k2["pass"] else "FIRES"))

    print("K1  counting arm cells (embargo + horizon inside the build years) ...")
    k1, events = arm_cells(events, cal)
    print("  smallest TIER cell: %s = %s against floor %d ; %s\n"
          % (k1["tier_min_cell_name"], "{:,}".format(k1["tier_min_cell"]),
             k1["floor"], "PASS" if k1["pass"] else "FIRES"))

    print("K3  design effect against its OWN shuffled null (R3) ...")
    k3 = design_effect(events)
    for key, r in sorted(k3["by_arm"].items()):
        if r.get("ok"):
            print("  %-16s deff %.4f vs null p95 %.4f -> measurable=%s ; n %s, blocks %s"
                  % (key, r["design_effect"], r["design_effect_null_p95"],
                     r["clustering_measurable"], "{:,}".format(r["n"]), "{:,}".format(r["n_blocks"])))
    print()

    print("K4  is the event a volatility sort? (A3, two forms) ...")
    k4 = volatility_sort(scoreable)
    for pop, r in k4["by_population"].items():
        print("  %-5s rate by vol quintile %s" % (pop, r["event_rate_by_vol_quintile_low_to_high"]))
        print("        median event-day move pp %s ; median trailing sd pp %s"
              % (r["median_event_day_move_pp_by_quintile"],
                 r["median_trailing_daily_sd_pp_by_quintile"]))
        print("        top/bottom %s (bar %.1f) ; mean |rho| %s (bar %.2f) ; %s"
              % (r["top_over_bottom_ratio"], r["ratio_bar"], r["mean_per_date_abs_rho"],
                 r["rho_bar"], "FIRES" if r["fires"] else "pass"))
    print()

    print("K5  dispersion measured, power table re-derived (A10) ...")
    k5 = power_table(summary, k1, n_eq)
    for h, r in k5["by_horizon"].items():
        print("  %-5s measured sd %7.3fpp (draft anchor %7.3fpp)  need at 80%% power: %s"
              % (h, r["measured_sd_pp"], r["anchor_sd_pp_draft"], r["required_n_at_80pc_power"]))
    print()

    cs = cap_sanity()
    print("cap sanity: %d names ever in tier (census control 459: %s); %d suspect\n"
          % (cs["names_ever_in_tier"], cs["census_control_459"], len(cs["suspect_names"])))

    # Charter Stage 1b: the per-date tier name count, and the 50-position floor.
    pdt = sorted(per_date_tier.items())
    counts = [c for _, c in pdt]
    tier_size = {
        "per_date_min": int(min(counts)) if counts else 0,
        "per_date_median": int(np.median(counts)) if counts else 0,
        "per_date_max": int(max(counts)) if counts else 0,
        "dates": len(counts),
        "contract_min_positions": D.CONTRACT_MIN_POSITIONS,
        "dates_below_floor": int(sum(1 for c in counts if c < D.CONTRACT_MIN_POSITIONS)),
        "first_date": pdt[0][0] if pdt else None, "last_date": pdt[-1][0] if pdt else None,
    }
    tier_size["pass"] = bool(tier_size["dates_below_floor"] == 0)
    print("tier size per date: min %d median %d max %d over %d dates ; below the 50-position "
          "floor on %d dates ; %s\n"
          % (tier_size["per_date_min"], tier_size["per_date_median"], tier_size["per_date_max"],
             tier_size["dates"], tier_size["dates_below_floor"],
             "PASS" if tier_size["pass"] else "NOT ASSESSABLE on the governing population"))

    gates = {"K1_event_count": k1["pass"], "K2_earnings_coverage": k2["pass"],
             "K3_design_effect": k3["pass"], "K4_not_a_volatility_sort": k4["pass"],
             "K5_power_table": k5["pass"], "tier_size": tier_size["pass"]}
    all_pass = all(gates.values())

    art = {
        "item": "DIP-CALL step 1 free pre-outcome kill pass",
        "register": "PREREG_dipcall.md committed ALONE at c5e0b31",
        "trials_booked_at": "a984ec9 (equity 274 -> 278)",
        "trials_this_pass": 0,
        "forward_return_touched": False,
        "abnormal_return_touched": False,
        "k": a.k, "build_quadrant": [D.BUILD_LO, D.BUILD_HI],
        "half_boundary": D.HALF_BOUNDARY,
        "equity_N": n_eq, "hlz_hurdle_equity": hlz_hurdle(n_eq),
        "summary": summary, "tier_size_per_date": tier_size,
        "K1_event_count": k1, "K2_earnings_coverage": k2, "K3_design_effect": k3,
        "K4_volatility_sort": k4, "K5_power": k5, "cap_sanity": cs,
        "gates": gates, "all_kills_pass": all_pass,
    }
    with io.open(D.out_path(ART), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    # Rule 9: store the draws, not just the summary. The arm pass reads this rather than
    # rebuilding, so the two passes provably score the SAME event set.
    events.to_pickle(D.out_path(EVENTS_PKL))
    import pickle
    with open(D.out_path("DIPCALL_CAL.pkl"), "wb") as fh:
        pickle.dump(cal, fh)

    print("=" * 78)
    for g, v in gates.items():
        print("  %-28s %s" % (g, "PASS" if v else "FIRES"))
    print("  ALL KILLS PASS: %s" % all_pass)
    print("=" * 78)
    print("wrote %s and %s" % (D.out_path(ART), D.out_path(EVENTS_PKL)))
    return 0 if all_pass else 3


if __name__ == "__main__":
    sys.exit(main())
