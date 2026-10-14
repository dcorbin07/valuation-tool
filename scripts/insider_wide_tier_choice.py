# -*- coding: utf-8 -*-
"""`INSIDER-WIDE` step 0 — choose the governing tier, from the BUILD quadrant and from costs.

    python -m scripts.insider_wide_tier_choice

**THE BUILD QUADRANT IS WHERE A DESIGN IS CHOSEN; THE CHECK QUADRANT IS THE ONE BLIND READ.**
`RESEARCH_CHARTER` §4: the BUILD cell is deliberately reused — *"every Stage-1 arm looks there,
which is the whole point of a cheap screen"* — while the CHECK cell is **not** reused. So this
pass reads BUILD outcomes freely to pick the tier, and reads **NOTHING** from the check quadrant
except **event COUNTS**, which are a feasibility fact and not an outcome.

**WHAT THIS PASS MAY AND MAY NOT TOUCH, stated because getting it wrong is irreversible:**

* BUILD quadrant (2009–2019 × ticker half 0) — **outcomes readable**, that is its purpose.
* CHECK quadrant (2020–2026 × ticker half 1) — **counts only**. No abnormal return is computed on
  a check-quadrant row anywhere in this file, and `tests/test_insider_wide.py` asserts it over the
  syntax tree.

**COSTS COME FROM THIS PROJECT'S OWN SIZE-TIERED MODEL, CALLED AND NEVER RE-IMPLEMENTED** (`B7`):
`fundamental_panel.one_way_cost_bps`, whose own comment is the honest caveat — *"deliberately
round, conservative-side numbers rather than a fitted microstructure model"*. A round trip is
twice it, charged at the name's **point-in-time** market cap rather than at one book-wide average.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import fundamental_panel as FP                          # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402

OUT = "INSIDER_WIDE_TIER_CHOICE.json"

#: The candidate floors, named here before anything is tabulated. They are exactly the breakpoints
#: this project's own cost table already uses, so the choice is between rungs that exist rather
#: than a continuum someone could tune along.
CANDIDATE_FLOORS = (10e9, 2e9, 500e6, 100e6, 0.0)

HALF_BOUNDARY = D.HALF_BOUNDARY


def cap_schedule(half: int) -> dict:
    """{ticker: [(panel_date, cap), ...]} for one ticker half, ascending.

    `dipcall.tier_schedule` is hard-wired to half 0 (its own docstring says so), and the CHECK
    quadrant is half 1 — so a half-1 count needs its own schedule. Writing this out rather than
    reusing a function whose filter is wrong for the question is the `wrong-object` family avoided
    rather than repeated.
    """
    d = pd.read_pickle(D.panel_path())
    d = d[["date", "ticker", "market_cap"]].copy()
    d["date"] = d["date"].astype(str)
    d["ticker"] = d["ticker"].astype(str)
    d = d[d["ticker"].map(D.stable_key_half) == int(half)]
    d["cap"] = pd.to_numeric(d["market_cap"], errors="coerce")
    d = d.dropna(subset=["cap"]).sort_values(["ticker", "date"])
    return {t: list(zip(g["date"].tolist(), g["cap"].tolist()))
            for t, g in d.groupby("ticker", sort=False)}


def cap_at(sched: dict, ticker: str, date: str):
    s = sched.get(ticker) or []
    c = [v for (dd, v) in s if dd <= date]
    return c[-1] if c else np.nan


def build_table() -> dict:
    """BUILD-quadrant h=63 market-adjusted result by cap tier. Outcomes, and that is allowed."""
    rows = pd.read_pickle(D.out_path("INSIDER_CLUSTER_ROWS_full_h63.pkl"))
    sched = cap_schedule(0)
    rows["cap"] = [cap_at(sched, t, d) for t, d in zip(rows["ticker"], rows["date"])]
    from scripts import dipcall_arm as DA
    out = {}
    for floor in CANDIDATE_FLOORS:
        m = (rows["cap"] >= floor) if floor > 0 else rows["cap"].notna() | True
        sub = rows[m.fillna(False)] if hasattr(m, "fillna") else rows[m]
        if len(sub) < 30:
            out["%.0f" % floor] = {"n": int(len(sub)), "status": "too few"}
            continue
        y = sub["mkt"].to_numpy(dtype=float)
        mean, se_d, t_d, g_d = DA.clustered(y, sub["date"].to_numpy(dtype=object))
        _m, se_t, t_t, g_t = DA.clustered(y, sub["ticker"].to_numpy(dtype=object))
        # the EVENT-WEIGHTED round-trip cost of exactly these events, from the shipped model
        rt = np.array([2.0 * FP.one_way_cost_bps(c) / 100.0 for c in sub["cap"].tolist()])
        out["%.0f" % floor] = {
            "floor_usd": floor, "n_events": int(len(sub)),
            "n_tickers": int(sub["ticker"].nunique()),
            "n_date_clusters": g_d,
            "mean_pp": mean * 100.0, "t_date": t_d, "t_ticker": t_t,
            "se_date_pp": se_d * 100.0, "se_ticker_pp": se_t * 100.0,
            "sd_pp": float(np.std(y, ddof=1)) * 100.0,
            "roundtrip_cost_pp_mean": float(rt.mean()),
            "roundtrip_cost_pp_median": float(np.median(rt)),
            "net_of_cost_pp": mean * 100.0 - float(rt.mean()),
            "cap_present_share": float(sub["cap"].notna().mean()),
            "median_cap_usd": float(np.nanmedian(sub["cap"].to_numpy(dtype=float))),
        }
    return out


def band_table() -> dict:
    """The same BUILD rows split into DISJOINT cap BANDS rather than cumulative floors.

    **CUMULATIVE FLOORS HIDE THE SHAPE, AND THE SHAPE IS THE FINDING.** A `$500M` floor contains
    every `$10B` name, so a floor table cannot say where the effect actually lives — and the floor
    table here is NON-MONOTONE (`$10B` +3.01pp, `$2B` +0.17pp, `$500M` +1.13pp), which is only
    interpretable once the bands are separated. Without this a reader would pick a floor on a
    number that is an average of two very different populations.
    """
    rows = pd.read_pickle(D.out_path("INSIDER_CLUSTER_ROWS_full_h63.pkl"))
    sched = cap_schedule(0)
    rows["cap"] = [cap_at(sched, t, d) for t, d in zip(rows["ticker"], rows["date"])]
    from scripts import dipcall_arm as DA
    edges = [(10e9, None), (2e9, 10e9), (500e6, 2e9), (100e6, 500e6), (0.0, 100e6)]
    out = {}
    for lo, hi in edges:
        m = rows["cap"] >= lo
        if hi is not None:
            m = m & (rows["cap"] < hi)
        sub = rows[m.fillna(False)]
        key = "%.0f_%s" % (lo, ("inf" if hi is None else "%.0f" % hi))
        if len(sub) < 30:
            out[key] = {"n": int(len(sub)), "status": "too few"}
            continue
        y = sub["mkt"].to_numpy(dtype=float)
        mean, se_d, t_d, g_d = DA.clustered(y, sub["date"].to_numpy(dtype=object))
        _m, se_t, t_t, g_t = DA.clustered(y, sub["ticker"].to_numpy(dtype=object))
        rt = np.array([2.0 * FP.one_way_cost_bps(c) / 100.0 for c in sub["cap"].tolist()])
        out[key] = {"lo_usd": lo, "hi_usd": hi, "n_events": int(len(sub)),
                    "n_tickers": int(sub["ticker"].nunique()),
                    "mean_pp": mean * 100.0, "t_date": t_d, "t_ticker": t_t,
                    "roundtrip_cost_pp_mean": float(rt.mean()),
                    "net_of_cost_pp": mean * 100.0 - float(rt.mean())}
    return out


def check_counts() -> dict:
    """CHECK-quadrant event COUNTS by tier. **COUNTS ONLY — no outcome is computed here.**"""
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    ck = ev[(ev["era"] == "check") & (ev["half"] == 1)].reset_index(drop=True)
    sched = cap_schedule(1)
    ck = ck.copy()
    ck["cap"] = [cap_at(sched, t, d) for t, d in zip(ck["ticker"], ck["date"])]
    mid = "2023-01-01"            # the check era's own midpoint, declared here
    out = {"check_era": "2020-01-01..2026", "half": 1, "inner_half_boundary": mid,
           "events_total": int(len(ck)), "COUNTS_ONLY": True}
    for floor in CANDIDATE_FLOORS:
        m = (ck["cap"] >= floor) if floor > 0 else pd.Series(True, index=ck.index)
        sub = ck[m.fillna(False)]
        out["%.0f" % floor] = {
            "floor_usd": floor, "n_events": int(len(sub)),
            "n_tickers": int(sub["ticker"].nunique()) if len(sub) else 0,
            "n_event_dates": int(sub["date"].nunique()) if len(sub) else 0,
            "early": int((sub["date"] < mid).sum()), "late": int((sub["date"] >= mid).sum()),
        }
    return out


def power(build: dict, check: dict) -> dict:
    """The check read's power, from the BUILD quadrant's MEASURED dispersion. Rule 11.

    The dispersion is the build cell's own realised SD of the market-adjusted return — not a
    trailing proxy and not borrowed from another construction (`MB8`) — and the effect it is
    powered against is the build cell's own measured mean, which is the only honest target for a
    confirmation read.
    """
    from valuation.edge import power_gate as PG
    out = {}
    for k, b in build.items():
        c = check.get(k) or {}
        if b.get("status") or not c.get("n_events"):
            continue
        n = int(c["n_events"])
        g_t = max(1, int(c["n_tickers"]))
        g_d = max(1, int(c["n_event_dates"]))
        sd = float(b["sd_pp"]) / 100.0
        eff = float(b["mean_pp"]) / 100.0
        se_naive = sd / (n ** 0.5)
        row = {"floor_usd": b["floor_usd"], "check_n": n,
               "check_tickers": g_t, "check_dates": g_d,
               "build_sd_pp": b["sd_pp"], "build_mean_pp": b["mean_pp"],
               "se_naive_pp": se_naive * 100.0}
        for nm, g in (("date", g_d), ("ticker", g_t)):
            se = se_naive * ((n / g) ** 0.5)
            row["se_clustered_%s_pp" % nm] = se * 100.0
            row["mde80_clustered_%s_pp" % nm] = (2.0 + PG.z_for_power(0.80)) * se * 100.0
            row["power_vs_build_effect_%s" % nm] = PG.power_at(eff, se, crit=2.0)
        row["worst_mde80_pp"] = max(row["mde80_clustered_date_pp"],
                                    row["mde80_clustered_ticker_pp"])
        row["worst_power"] = min(row["power_vs_build_effect_date"],
                                 row["power_vs_build_effect_ticker"])
        row["build_effect_over_worst_mde"] = (float(b["mean_pp"]) / row["worst_mde80_pp"]
                                              if row["worst_mde80_pp"] else float("nan"))
        out[k] = row
    return out



def power_realised(build: dict, check: dict) -> dict:
    """The check read's power from the BUILD cell's **REALISED CLUSTERED** standard error.

    **THIS REPLACES THE `sqrt(n/G)` BOUND AS THE FIGURE TO QUOTE, AND THE REASON IS MEASURED.**
    That bound assumes PERFECT within-cluster correlation, so it is the worst case rather than an
    estimate — and `BETA-FORECAST` measured how far out it lands: it predicted an MDE80 of 0.0548
    and the realised figure was **0.0094**, about 6x better. Here the build cell has already
    produced a *measured* cluster-robust `se` on the identical construction, so scaling it by
    `sqrt(n_build / n_check)` is an estimate rather than a bound. `MB8`'s rule is satisfied
    because the `se` is this construction's own and not borrowed from another.

    **BOTH are reported.** The bound is the conservative end and the realised scaling the central
    estimate; quoting only one would be the error `RUN_RULES` rule 11 exists to stop.

    The NET leg's power is the power to distinguish the gross mean from the COST, which is what
    clause A4 actually tests — so its effect size is `gross - cost`, not `gross`.
    """
    from valuation.edge import power_gate as PG
    out = {}
    for k, b in build.items():
        c = check.get(k) or {}
        if b.get("status") or not c.get("n_events"):
            continue
        n_b, n_c = int(b["n_events"]), int(c["n_events"])
        scale = (n_b / n_c) ** 0.5
        se_d = float(b["se_date_pp"]) * scale
        se_t = float(b["se_ticker_pp"]) * scale
        se_worst = max(se_d, se_t) / 100.0
        gross = float(b["mean_pp"]) / 100.0
        net = float(b["net_of_cost_pp"]) / 100.0
        out[k] = {
            "floor_usd": b["floor_usd"], "check_n": n_c, "build_n": n_b,
            "build_se_date_pp": b["se_date_pp"], "build_se_ticker_pp": b["se_ticker_pp"],
            "scale_sqrt_nb_over_nc": scale,
            "check_se_worst_pp": se_worst * 100.0,
            "mde80_pp": (2.0 + PG.z_for_power(0.80)) * se_worst * 100.0,
            "gross_effect_pp": b["mean_pp"],
            "power_gross": PG.power_at(gross, se_worst, crit=2.0),
            "net_effect_pp": b["net_of_cost_pp"],
            "power_net_vs_cost_bar": (PG.power_at(net, se_worst, crit=2.0)
                                      if net > 0 else 0.0),
            "expected_t_net": (net / se_worst if se_worst else float("nan")),
            "state_gross": PG.state(gross, se_worst, crit=2.0),
        }
    return out


def main(argv=None):
    out = {"item": "INSIDER-WIDE", "part": "step 0 -- the tier choice", "trials": 0,
           "trial_class": ("DESIGN CHOICE from the BUILD quadrant plus COUNTS from the check "
                           "quadrant. No check-quadrant outcome is computed anywhere in this "
                           "module."),
           "cost_model": {"source": "fundamental_panel.one_way_cost_bps, CALLED not re-implemented",
                          "table_bps_one_way": {str(int(f)): b
                                                for f, b in FP.COST_BPS_BY_MKTCAP},
                          "micro_bps": FP.COST_BPS_MICRO,
                          "roundtrip": "2x one-way, at the name's POINT-IN-TIME market cap",
                          "CAVEAT": ("the shipped table's own words: deliberately round, "
                                     "conservative-side numbers rather than a fitted "
                                     "microstructure model")}}
    print("[tier] BUILD quadrant h=63 by cap tier (outcomes -- this is what the build cell is "
          "for) ...", flush=True)
    out["build"] = build_table()
    for k, b in out["build"].items():
        if b.get("status"):
            continue
        print("  floor %-7s n %-5d tick %-4d | mkt %+.4fpp t %+.2f/%+.2f | cost %.3fpp -> NET "
              "%+.4fpp | median cap $%.2fbn"
              % ("$%.0fM" % (b["floor_usd"] / 1e6), b["n_events"], b["n_tickers"], b["mean_pp"],
                 b["t_date"], b["t_ticker"], b["roundtrip_cost_pp_mean"], b["net_of_cost_pp"],
                 b["median_cap_usd"] / 1e9), flush=True)

    print("\n[tier] BUILD quadrant by DISJOINT cap BAND -- the floor table is non-monotone "
          "and the bands are what make it readable ...", flush=True)
    out["bands"] = band_table()
    for k, b in out["bands"].items():
        if b.get("status"):
            print("  %-18s n %-5d  %s" % (k, b["n"], b["status"]), flush=True)
            continue
        hi = "inf" if b["hi_usd"] is None else "$%.0fM" % (b["hi_usd"] / 1e6)
        print("  $%-6.0fM..%-8s n %-5d tick %-4d | mkt %+.4fpp t %+.2f/%+.2f | cost %.3fpp -> "
              "NET %+.4fpp"
              % (b["lo_usd"] / 1e6, hi, b["n_events"], b["n_tickers"], b["mean_pp"],
                 b["t_date"], b["t_ticker"], b["roundtrip_cost_pp_mean"],
                 b["net_of_cost_pp"]), flush=True)

    print("\n[tier] CHECK quadrant EVENT COUNTS ONLY ...", flush=True)
    out["check_counts"] = check_counts()
    for k in out["build"]:
        c = out["check_counts"].get(k)
        if c:
            print("  floor %-7s n %-5d tick %-4d dates %-4d (early %d / late %d)"
                  % ("$%.0fM" % (c["floor_usd"] / 1e6), c["n_events"], c["n_tickers"],
                     c["n_event_dates"], c["early"], c["late"]), flush=True)

    print("\n[tier] POWER of the check read, from the BUILD cell's measured dispersion ...",
          flush=True)
    out["power"] = power(out["build"], out["check_counts"])
    for k, r in out["power"].items():
        print("  floor %-7s check n %-5d | worst MDE80 %.4fpp vs build effect %+.4fpp "
              "(%.2fx) | worst power %.1f%%"
              % ("$%.0fM" % (r["floor_usd"] / 1e6), r["check_n"], r["worst_mde80_pp"],
                 r["build_mean_pp"], r["build_effect_over_worst_mde"],
                 100 * r["worst_power"]), flush=True)

    print("\n[tier] POWER on the build cell's REALISED clustered se (the figure to quote) ...",
          flush=True)
    out["power_realised"] = power_realised(out["build"], out["check_counts"])
    for k, r in out["power_realised"].items():
        print("  floor %-7s check n %-5d | se %.4fpp MDE80 %.4fpp | GROSS %+.4fpp power %.1f%% "
              "| NET %+.4fpp expected t %+.2f power %.1f%%"
              % ("$%.0fM" % (r["floor_usd"] / 1e6), r["check_n"], r["check_se_worst_pp"],
                 r["mde80_pp"], r["gross_effect_pp"], 100 * r["power_gross"],
                 r["net_effect_pp"], r["expected_t_net"],
                 100 * r["power_net_vs_cost_bar"]), flush=True)

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[tier] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
