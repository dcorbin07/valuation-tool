# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` step 0 — the PRE-OUTCOME census, run BEFORE the register is written.

    python -m scripts.insider_cluster_census

**IT READS NO FORWARD RETURN AND HAS NO BAR.** It answers only feasibility questions — how many
rows, how many carry a usable code, how many cluster events exist in each quadrant cell, how large
the governing tier is, and what dispersion the design will face. Those are the inputs the
register's floors and its MDE must be DERIVED from, which is why the census comes first: the
alternative is a register whose bars were chosen after seeing what the data could supply.

**THE PRECEDENT THIS FOLLOWS.** `O-1` measured coverage *"on the population the arm was scored
on, BEFORE any bar was set"* and recorded that borrowing an alert-book figure onto the panel had
made its own register wrong by ~17×; `MB20` ran a census before its register; `MB15` closed a whole
item on one. **A census is a fact about what data exists, not a search** — so it charges ZERO
trials, and nothing here is compared to a threshold.

**THE DISPERSION FIGURE IS AN UPPER BOUND ON POWER AND IS LABELLED ONE.** A pre-outcome pass
cannot measure a realised forward dispersion, so it uses the trailing 60-session daily SD scaled
by sqrt(h). Volatility is clustered, so post-event dispersion EXCEEDS that — which means this
estimate UNDERSTATES the required n and OVERSTATES power. That is the unsafe direction, so it is
named here and the MDE that travels with any verdict comes from the arm's OWN realised SD
(`MB8`: never borrow an se). `DIP-CALL`'s decision 3, reused.
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

from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from valuation.studies import insider_routine as IR                         # noqa: E402

OUT = "INSIDER_CLUSTER_CENSUS.json"
OUT_BROAD = "INSIDER_CLUSTER_CENSUS_broad.json"


def quadrant_split(ev: pd.DataFrame) -> pd.DataFrame:
    """Tag each event with its ticker half and its era cell. No outcome is touched."""
    ev = ev.copy()
    ev["half"] = ev["ticker"].map(D.stable_key_half)
    d = ev["date"].astype(str)
    ev["era"] = np.where(d <= "2008-12-31", "pre2009",
                         np.where(d <= D.BUILD_HI, "build", "check"))
    ev["build_half"] = np.where(d <= D.BUILD_HI, "", "")
    ev["inner_half"] = np.where(d < D.HALF_BOUNDARY, "early", "late")
    return ev


def tier_flags(ev: pd.DataFrame, sched: dict) -> np.ndarray:
    """`cap >= $10B` at the most recent PRIOR quarterly date, per event (Stage 1b's tier)."""
    out = np.zeros(len(ev), dtype=bool)
    for i, (tk, dt) in enumerate(zip(ev["ticker"].tolist(), ev["date"].astype(str).tolist())):
        s = sched.get(tk) or []
        if not s:
            continue
        caps = [c for (pd_, c) in s if pd_ <= dt]
        if caps and float(caps[-1]) >= D.TIER_FLOOR:
            out[i] = True
    return out


def dispersion_bound(ev: pd.DataFrame, horizons, max_names: int = 1200) -> dict:
    """Trailing-SD × sqrt(h) at the event dates. AN UPPER BOUND ON POWER — see the docstring."""
    names = sorted(set(ev["ticker"].tolist()))[:max_names]
    per_h = {int(h): [] for h in horizons}
    for tk in names:
        s = D.read_prices(tk)
        if s is None or len(s) < D.VOL_WIN + 10:
            continue
        s = s.reset_index(drop=True)
        vol = s["close"].pct_change().rolling(D.VOL_WIN,
                                              min_periods=D.MIN_VOL_OBS).std().shift(1)
        idx = {d: i for i, d in enumerate(s["date"].astype(str).tolist())}
        for dt in ev.loc[ev["ticker"] == tk, "date"].astype(str).tolist():
            i = idx.get(dt)
            if i is None:
                continue
            v = vol.iloc[i]
            if not np.isfinite(v) or v <= 0:
                continue
            for h in per_h:
                per_h[h].append(float(v) * (h ** 0.5))
    out = {}
    for h, xs in per_h.items():
        a = np.asarray(xs, dtype=float)
        out[str(h)] = {
            "n": int(a.size),
            "median_sd": (float(np.median(a)) if a.size else float("nan")),
            "mean_sd": (float(a.mean()) if a.size else float("nan")),
            "LABEL": "UPPER BOUND ON POWER -- trailing SD, so it understates the required n",
        }
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-disp-names", type=int, default=1200)
    ap.add_argument("--broad", action="store_true",
                    help="the DECLARED SENSITIVITY: the broad opportunistic label, without the "
                         "prior-year-presence condition. The default is STRICT.")
    a = ap.parse_args(argv)
    t0 = time.time()

    print("[census] loading the FREEZE's raw SF2 (not data/backtest -- see the module docstring)",
          flush=True)
    df = IC.load_sf2()
    print("[census] %d rows in %.0fs" % (len(df), time.time() - t0), flush=True)

    out = {"item": "INSIDER-CLUSTER", "part": "step 0 -- pre-outcome census", "trials": 0,
           "trial_class": ("CENSUS -- no hypothesis, no bar, no outcome statistic, and no forward "
                           "return read anywhere in this module"),
           "sf2": os.path.basename(IC.sf2_zip()),
           "definition": {"k_primary": IC.K_PRIMARY, "k_sensitivity": IC.K_SENSITIVITY,
                          "window_days": IC.WINDOW_DAYS,
                          "dated_on": "filingdate (public information)",
                          "habit_measured_in": "transactiondate months (insider_routine's rule)"},
           "code_census": IC.code_census(df)}
    print("[census] code census: %s" % json.dumps(out["code_census"]), flush=True)

    # THE SCOUT'S OWN FIGURES, re-measured on the freeze rather than carried over. The comparison
    # IS the finding: data/backtest is universe-filtered by TODAY's cap.
    out["scout_measured_on_data_backtest"] = {
        "rows": 6688777, "code_missing_share": 0.2852, "purchase_rows": 163653,
        "source": "a8c1a75, on data/backtest/insiders.csv",
    }
    cc = out["code_census"]
    out["freeze_vs_export"] = {
        "rows_ratio": cc["rows"] / 6688777.0,
        "purchase_rows_ratio": cc["purchase_rows"] / 163653.0,
        "WHY": ("data/backtest keeps the top 3,000 names by TODAY's scalemarketcap, so the export "
                "is selected on a present-day property -- the charter's own reason for banning it "
                "as a PANEL, measured here on the insider file"),
    }

    print("[census] classifying ROUTINE / OPPORTUNISTIC on the FULL history ...", flush=True)
    labels = IC.label_rows(df)
    out["routine_census"] = IR.coverage(labels)
    print("[census] %s" % json.dumps(out["routine_census"]), flush=True)

    out["definition"]["strict"] = (not a.broad)
    buys = IC.opportunistic_purchases(df, labels, strict=(not a.broad))
    out["opportunistic_purchase_rows"] = int(len(buys))
    out["distinct_tickers_with_a_buy"] = int(buys["ticker"].nunique())
    print("[census] %d opportunistic open-market purchase rows over %d tickers"
          % (len(buys), buys["ticker"].nunique()), flush=True)

    del df
    for k in (IC.K_PRIMARY, IC.K_SENSITIVITY):
        print("[census] clustering at k=%d ..." % k, flush=True)
        ev = IC.cluster_events(buys, k=k)
        ev = quadrant_split(ev)
        blk = {"events_total": int(len(ev)),
               "distinct_tickers": int(ev["ticker"].nunique()) if len(ev) else 0,
               "by_era": {str(x): int(n) for x, n in ev["era"].value_counts().items()},
               "median_insiders": (float(ev["n_insiders"].median()) if len(ev) else float("nan"))}
        bq = ev[(ev["era"] == "build") & (ev["half"] == 0)]
        blk["build_half0"] = {
            "events": int(len(bq)),
            "distinct_tickers": int(bq["ticker"].nunique()) if len(bq) else 0,
            "early": int((bq["inner_half"] == "early").sum()),
            "late": int((bq["inner_half"] == "late").sum()),
            "distinct_event_dates": int(bq["date"].nunique()) if len(bq) else 0,
        }
        chk = ev[(ev["era"] == "check") & (ev["half"] == 1)]
        blk["check_half1_NOT_READ"] = {
            "events": int(len(chk)),
            "NOTE": ("counted for feasibility only. Stage 2 gets ONE read of this cell and this "
                     "census does not spend it -- no outcome is computed here at all."),
        }
        if k == IC.K_PRIMARY:
            sched = D.tier_schedule()
            tf = tier_flags(bq, sched)
            blk["build_half0_tier"] = {
                "events_cap_ge_10bn": int(tf.sum()),
                "share": (float(tf.mean()) if len(tf) else float("nan")),
                "distinct_tickers": int(bq.loc[tf, "ticker"].nunique()) if tf.any() else 0,
                "early": int(((bq["inner_half"] == "early").to_numpy() & tf).sum()),
                "late": int(((bq["inner_half"] == "late").to_numpy() & tf).sum()),
                "TIER_IS": "the incumbent's own absolute cap >= $10B floor (charter Stage 1b)",
            }
            print("[census] dispersion bound (trailing SD x sqrt(h)) ...", flush=True)
            blk["dispersion_bound"] = dispersion_bound(bq, (5, 21, 63, 126),
                                                       max_names=a.max_disp_names)
            # banked so the register's MDE can be derived rather than retyped
            p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d%s.csv"
                           % (k, "_broad" if a.broad else ""))
            ev.to_csv(p, index=False)
            blk["events_csv"] = os.path.basename(p)
        out["k%d" % k] = blk
        print("[census] k=%d: %s" % (k, json.dumps(blk.get("build_half0"))), flush=True)

    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT_BROAD if a.broad else OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[census] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
