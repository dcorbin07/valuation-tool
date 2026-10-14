# -*- coding: utf-8 -*-
"""`BETA-FORECAST` — the census, then the contest.

    python -m scripts.beta_forecast_contest --census     # feasibility only, no loss computed
    python -m scripts.beta_forecast_contest              # the contest

Register: `PREREG_beta_forecast.md`, committed ALONE, a strict git ancestor of every commit that
computes a loss. **The census pass computes NO LOSS and compares nothing to a bar** — it answers
only how many cells exist and how well each candidate is covered, which are the inputs the
register's floors come from (`O-1`'s lesson: a floor set from the wrong population was wrong by
~17x).

**NO FORWARD RETURN IS READ IN THIS ITEM AT ALL.** The realised beta is a covariance with the
market over the following two years. Nothing here is scored against a return and no cell is a
performance claim.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import sector_map as SM                                 # noqa: E402
from valuation.studies import beta_forecast as BF                           # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402

OUT_CENSUS = "BETA_FORECAST_CENSUS.json"
OUT = "BETA_FORECAST_CONTEST.json"
CELLS_PKL = "BETA_FORECAST_CELLS.pkl"

#: Quarter-end formation months only. A monthly grid would give 12x the cells and ~1/12th the
#: independence (a 60-month trailing window moved one month is almost the same window), so it
#: would inflate `n` without adding information -- and the standard errors are clustered on the
#: formation date anyway, which is the honest treatment either way.
QUARTER_ENDS = ("03", "06", "09", "12")


def panel_names() -> list:
    panel = pd.read_pickle(D.panel_path())
    return sorted(set(panel["ticker"].astype(str)))


def build_cells(names, verbose=True) -> pd.DataFrame:
    """One row per (ticker, formation month) with all three candidates and the realised beta.

    Nothing is dropped silently: a row missing any piece is still emitted with that piece NaN, and
    the contest reports the intersection it scores on. **Scoring three candidates on three
    different populations would make the comparison meaningless**, which is `S10`'s failure mode
    in a new costume.
    """
    mkt_c = BF.monthly_closes(BF.MARKET)
    if mkt_c is None:
        raise SystemExit("REFUSING: no %s price series" % BF.MARKET)
    mkt = BF.monthly_returns(mkt_c)
    months = [m for m in BF.formation_months(mkt.index) if m[5:7] in QUARTER_ENDS]
    if verbose:
        print("[beta] %d quarterly formation months, %s -> %s"
              % (len(months), months[0], months[-1]), flush=True)

    keep = set(months)
    parts = []
    t0 = time.time()
    for i, tk in enumerate(names):
        c = BF.monthly_closes(tk)
        if c is None:
            continue
        r = BF.monthly_returns(c)
        if len(r) < BF.MIN_TRAIL_OBS + BF.MIN_FWD_OBS:
            continue
        # VECTORISED, and gated against the explicit loop at max |delta| 1.5e-14 over 1,709 cells
        # by `tests/test_beta_forecast.py` -- the per-cell loop would have taken hours on 9,645
        # names, and a faster path returning a different number is worthless.
        roll = BF.rolling_betas(r, mkt)
        if not len(roll):
            continue
        roll = roll[roll["month"].isin(keep)]
        if not len(roll):
            continue
        roll = roll.copy()
        roll["ticker"] = tk
        parts.append(roll)
        if verbose and i and i % 1500 == 0:
            print("    %d/%d names, %d cells, %.0fs"
                  % (i, len(names), sum(len(x) for x in parts), time.time() - t0), flush=True)
    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if not len(df):
        raise SystemExit("REFUSING: no cells built -- the contest would compare nothing")
    df["b_blume"] = df["b_raw"].map(BF.blume)
    return df


def attach_sector(df: pd.DataFrame, verbose=True) -> pd.DataFrame:
    """`S25`'s DATED point-in-time GICS map, never the panel's `sector` column.

    **THE PANEL'S OWN `sector` IS TODAY'S CLASSIFICATION** — `S25` measured it and `S25-REPAIR`
    measured what the look-ahead costs (the fair value moves on EVERY row it touches and the
    valuation REGIME flips on 57%). Using it for a FORECASTING contest would hand candidate (c)
    knowledge of the future, i.e. would bias the test toward the candidate under test. The dated
    map refuses rather than carrying a lapsed classification forward, and a refusal is recorded as
    `NOT_COVERED` instead of silently becoming a sector.
    """
    smap = SM.load()
    secs, states = [], []
    cache = {}
    for tk, m in zip(df["ticker"].tolist(), df["month"].tolist()):
        key = (tk, m)
        if key not in cache:
            # the formation month's last day, as a date the map can resolve
            d = str(pd.Period(m, freq="M").end_time.date())
            try:
                r = smap.at(tk, d)
            except Exception:                                               # noqa: BLE001
                r = None
            cache[key] = r or {}
        r = cache[key]
        secs.append(r.get("sector"))
        states.append(r.get("state") or "NO_RESULT")
    df = df.copy()
    df["sector"] = secs
    df["sector_state"] = states
    if verbose:
        print("[beta] dated sector coverage: %s"
              % json.dumps(pd.Series(states).value_counts().to_dict()), flush=True)
    # the sector median of the RAW beta, within formation month, point-in-time by construction
    med = (df.dropna(subset=["sector"])
             .groupby(["month", "sector"])["b_raw"]
             .agg(["median", "size"]).reset_index()
             .rename(columns={"median": "b_sector", "size": "n_sector"}))
    med = med[med["n_sector"] >= BF.MIN_SECTOR_NAMES]
    df = df.merge(med, on=["month", "sector"], how="left")
    return df


def census(df: pd.DataFrame) -> dict:
    both = df.dropna(subset=["b_raw", "b_blume", "b_sector", "b_real"])
    months = sorted(set(df["month"]))
    mid = months[len(months) // 2] if months else None
    return {
        "item": "BETA-FORECAST", "part": "census -- feasibility only, NO LOSS COMPUTED",
        "trials": 0,
        "trial_class": ("CENSUS -- no hypothesis, no bar, no loss, and no forward return read "
                        "anywhere in this item"),
        "cells_all": int(len(df)),
        "cells_with_all_three_candidates": int(len(both)),
        "sector_coverage_of_cells": (len(both) / len(df)) if len(df) else float("nan"),
        "distinct_tickers": int(df["ticker"].nunique()),
        "distinct_tickers_scored": int(both["ticker"].nunique()) if len(both) else 0,
        "formation_months": len(months),
        "first_month": months[0] if months else None,
        "last_month": months[-1] if months else None,
        "half_boundary": mid,
        "early_cells": int((both["month"] < mid).sum()) if mid else 0,
        "late_cells": int((both["month"] >= mid).sum()) if mid else 0,
        "sector_state_counts": {str(k): int(v) for k, v
                                in df["sector_state"].value_counts().items()},
        "b_raw_quantiles": {q: float(df["b_raw"].quantile(q)) for q in (0.05, 0.5, 0.95)},
        "b_real_quantiles": {q: float(df["b_real"].quantile(q)) for q in (0.05, 0.5, 0.95)},
        "estimator": {"trail_months": BF.TRAIL_MONTHS, "min_trail_obs": BF.MIN_TRAIL_OBS,
                      "fwd_months": BF.FWD_MONTHS, "min_fwd_obs": BF.MIN_FWD_OBS,
                      "market": BF.MARKET, "blume_w": BF.BLUME_W,
                      "sector_map": "S25 dated GICS, never the panel's today-sector"},
    }


# ------------------------------------------------------------------ REGISTER BARS (sections 5-7)
#: `cap >= $10B` at the most recent PRIOR quarterly observation -- the incumbent's own tier and the
#: register's PRIMARY population. The sensitivity is declared beside it so neither can be reached
#: for after seeing which reads better.
TIER_FLOOR = 10e9
TIER_SENSITIVITY = 2e9

#: B4's materiality floor, in BETA UNITS, DERIVED from item 53's fair-value sensitivity: NVDA
#: 145.67 -> 230.65 for beta 2.22 -> 1.00 is about 0.478 percent of fair value per 0.01 of beta,
#: so 0.05 beta units is about 2.4 percent -- the same order as the 2 percent do-no-harm ceiling
#: the prior Blume test breached at 2.491 percent. NOT set to what is detectable: `R1-VAR`'s
#: lesson is that a detection threshold used as a preference threshold is a category error, and
#: the reverse is one too.
MATERIALITY_BETA = 0.05

#: B2's bar. LABELLED UNCALIBRATED -- no X7 or CORRECTED-FLOORS figure transfers to a paired
#: beta-forecast error and none is quoted.
T_BAR = 2.0


def clustered_mean(y, groups):
    """`(mean, se, t, n_clusters)` -- DELEGATED to `dipcall_arm.clustered`.

    One cluster-robust mean in this repository (`B7`), and it is the same estimator
    `INSIDER-CLUSTER` used an hour earlier. A second implementation is how two items come to
    report two standard errors for one quantity.
    """
    from scripts import dipcall_arm as DA
    return DA.clustered(np.asarray(y, dtype=float), np.asarray(groups, dtype=object))


def score_candidate(d, cand):
    """One candidate against RAW on IDENTICAL rows. The register's section 5 paired contrast.

    A paired contrast removes everything that differs between names and dates, which is why
    `MB8`'s paired se came out 8x smaller than `V2G`'s unpaired one -- and it is also why the
    candidate and the incumbent must be scored on the same rows rather than on each one's own
    coverage (`S10`'s failure mode).
    """
    from valuation.edge import power_gate as PG
    sub = d.dropna(subset=["b_raw", "b_real", cand])
    if len(sub) < 30:
        return {"status": "too few rows", "n": int(len(sub))}
    e_raw = (sub["b_raw"] - sub["b_real"]).abs().to_numpy(dtype=float)
    e_c = (sub[cand] - sub["b_real"]).abs().to_numpy(dtype=float)
    diff = e_c - e_raw                      # NEGATIVE means the candidate is CLOSER
    m, se_m, t_m, g_m = clustered_mean(diff, sub["month"].to_numpy(dtype=object))
    _m, se_t, t_t, g_t = clustered_mean(diff, sub["ticker"].to_numpy(dtype=object))
    out = {
        "n": int(len(sub)), "n_month_clusters": g_m, "n_ticker_clusters": g_t,
        "mae_raw": float(e_raw.mean()), "mae_candidate": float(e_c.mean()),
        "mean_paired_diff": float(m),
        "se_month": float(se_m), "t_month": float(t_m),
        "se_ticker": float(se_t), "t_ticker": float(t_t),
        # SECONDARY, declared, NO VERDICT -- and quoting one loss without the other is a void
        # condition, so both always ship together.
        "rmse_raw": float(np.sqrt((e_raw ** 2).mean())),
        "rmse_candidate": float(np.sqrt((e_c ** 2).mean())),
    }
    out["rmse_improves"] = bool(out["rmse_candidate"] < out["rmse_raw"])
    out["B1_direction"] = bool(m < 0)
    out["B2_both_clusterings"] = bool(abs(t_m) > T_BAR and abs(t_t) > T_BAR and m < 0)
    out["B4_materiality"] = bool(abs(m) > MATERIALITY_BETA)
    # THE MDE TRAVELS WITH THE VERDICT AND IS THIS CONTEST'S OWN, on the WORSE clustering because
    # B2 requires clearing under both (`MB8`: never borrow an se).
    se_worst = max(se_m, se_t)
    out["mde80_own_se"] = (T_BAR + PG.z_for_power(0.80)) * se_worst
    out["power_state_own_se"] = PG.state(MATERIALITY_BETA, se_worst, crit=T_BAR)
    return out


def contest(df):
    out = {"item": "BETA-FORECAST", "part": "the contest",
           "register": "PREREG_beta_forecast.md", "register_commit": "67831e7",
           "trials_booked_at": "1c2200f",
           "reads_no_forward_return": True,
           "bars": {"t_bar": T_BAR,
                    "t_bar_LABEL": "UNCALIBRATED (V2G, R1-VAR); no X7 figure transfers",
                    "materiality_beta_units": MATERIALITY_BETA,
                    "materiality_DERIVED_FROM": ("item 53: NVDA 145.67 -> 230.65 for beta 2.22 -> "
                                                 "1.00, about 0.478 percent of fair value per "
                                                 "0.01 of beta, so 0.05 is about 2.4 percent"),
                    "primary_loss": "mean ABSOLUTE error (the realised beta has fat tails)",
                    "secondary_loss": "RMSE -- declared, NO VERDICT, never quoted alone"},
           "populations": {}}

    pops = [("tier_cap_ge_10bn", (df["cap"] >= TIER_FLOOR), True),
            ("tier_cap_ge_2bn", (df["cap"] >= TIER_SENSITIVITY), False),
            ("full_universe", pd.Series(True, index=df.index), False)]
    for name, mask, is_primary in pops:
        d = df[mask.fillna(False)]
        months = sorted(set(d["month"]))
        mid = months[len(months) // 2] if months else None
        blk = {"is_primary": bool(is_primary), "n_cells": int(len(d)),
               "n_tickers": int(d["ticker"].nunique()) if len(d) else 0,
               "n_months": len(months), "half_boundary": mid,
               "corr_raw_real": (float(d[["b_raw", "b_real"]].corr().iloc[0, 1])
                                 if len(d) > 2 else float("nan")),
               "sd_b_real": float(d["b_real"].std()) if len(d) > 2 else float("nan")}
        if not is_primary:
            blk["NO_VERDICT"] = ("declared in the register as a sensitivity or a reported "
                                 "reading. The tier governs.")
        for cand in ("b_blume", "b_sector"):
            full = score_candidate(d, cand)
            halves = {}
            if mid and "mean_paired_diff" in full:
                for nm, m2 in (("early", d["month"] < mid), ("late", d["month"] >= mid)):
                    halves[nm] = score_candidate(d[m2], cand)
            full["halves"] = halves
            same_sign = (all(halves.get(x, {}).get("mean_paired_diff", 0.0) < 0
                             for x in ("early", "late")) if halves else False)
            full["B3_both_halves"] = bool(
                same_sign
                and halves.get("early", {}).get("B2_both_clusterings")
                and halves.get("late", {}).get("B2_both_clusterings"))
            full["ALL_FOUR"] = bool(full.get("B1_direction") and full.get("B2_both_clusterings")
                                    and full.get("B3_both_halves") and full.get("B4_materiality"))
            if is_primary:
                full["verdict"] = "BEATS RAW" if full["ALL_FOUR"] else "NULL"
                full["verdict_note"] = (
                    "all four bars of section 6" if full["ALL_FOUR"] else
                    "at least one of section 6's four bars failed; the register makes any other "
                    "outcome a NULL and the MDE travels with it")
            else:
                full["verdict"] = "NO VERDICT -- sensitivity"
            blk[cand] = full
        out["populations"][name] = blk
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--limit-names", type=int, default=0,
                    help="SMOKE TEST only -- labelled, and a smoke test carries no verdict")
    a = ap.parse_args(argv)

    names = panel_names()
    if a.limit_names:
        names = names[:a.limit_names]
        print("[beta] SMOKE TEST on %d names -- NOT a verdict" % len(names), flush=True)
    print("[beta] %d panel names" % len(names), flush=True)

    cells_p = D.out_path(CELLS_PKL)
    if os.path.isfile(cells_p) and not a.limit_names:
        df = pd.read_pickle(cells_p)
        print("[beta] reusing %d banked cells (rule 9)" % len(df), flush=True)
    else:
        df = build_cells(names)
        df = attach_sector(df)
        if not a.limit_names:
            df.to_pickle(cells_p)
            print("[beta] banked %d cells -> %s" % (len(df), cells_p), flush=True)

    c = census(df)
    print("[beta] census: %s" % json.dumps({k: v for k, v in c.items()
                                            if not isinstance(v, dict)}), flush=True)
    p = D.out_path(OUT_CENSUS)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(c, indent=1, default=str))
    print("[beta] wrote %s" % p, flush=True)
    if a.census:
        return c

    res = contest(df)
    p2 = D.out_path(OUT)
    with io.open(p2, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=1, default=str))
    tier = res["populations"]["tier_cap_ge_10bn"]
    for cand in ("b_blume", "b_sector"):
        b = tier[cand]
        if "mean_paired_diff" not in b:
            print("[beta] %-9s %s" % (cand, b.get("status")), flush=True)
            continue
        print("[beta] %-9s MAE raw %.4f -> %.4f | paired %+.5f  t %+.3f/%+.3f | "
              "B1 %s B2 %s B3 %s B4 %s -> %s"
              % (cand, b["mae_raw"], b["mae_candidate"], b["mean_paired_diff"],
                 b["t_month"], b["t_ticker"], b["B1_direction"], b["B2_both_clusterings"],
                 b["B3_both_halves"], b["B4_materiality"], b["verdict"]), flush=True)
    print("[beta] wrote %s" % p2, flush=True)
    return res


if __name__ == "__main__":
    main()
