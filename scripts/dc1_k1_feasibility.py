# -*- coding: utf-8 -*-
"""DC-1 STAGE 1 — K1, THE FREE FEASIBILITY KILL. ZERO TRIALS, NO REGISTER, NO ARM.

`PREREG_DRAFT_dc1_dip_confirmation.md` §8 K1, quoted:

    "From `V6`'s BANKED calendar-window statistics and the measured dispersion ratio
     k = sigma_e/sigma_d, derive the IMPLIED EVENT-TIME t. If even that implied t falls short of
     the bar, the effect `V6` could not see does not clear when re-clocked either, and DC-1
     STOPS -- zero trials. This is the strongest available kill because it tests the PREMISE of
     the whole register rather than its hypothesis."

This file executes exactly that and nothing else. **No panel is scored. No signal is related to a
forward return. No register is committed and no trial is booked** -- the `MB15` and `W-14`
precedent, where a pre-outcome kill fired first and the item closed at zero cost.

WHICH `V6` ARM IS THE MATCHED ONE, because it decides the answer
---------------------------------------------------------------
DC-1 §6(a) declares a **>= 30% drawdown**. `V6` banked FOUR arms: A1/A2 at depth 0.20 and A3/A4
at depth 0.30. **A3 (depth 0.30, horizon 63) is the matched arm** -- matched in depth to DC-1's
own declaration and in horizon to §2's own `sqrt(63)` arithmetic. Using A1's larger statistic to
license a 30%-depth register would import a figure measured on a DIFFERENT population, which is
the substitution that cost `O-1` its power (an alert-book figure applied to the panel, ~17x wrong)
and that killed `W-14`'s premise the same week. A1/A2 are reported as a LABELLED SENSITIVITY and
carry no weight in the verdict.

`sigma_e` IS A WINDOW SD, NOT A DAY SD -- a correction to my own first measurement
---------------------------------------------------------------------------------
§2 writes `t ~ J/(sigma_d*sqrt(W))` for a calendar window and `t ~ J/sigma_e` for the event
window, so `sigma_e` is the SD of the EVENT-WINDOW CUMULATIVE return -- DC-1's declared **[0,+1]**,
i.e. TWO sessions. A two-session cumulative return carries SD ~ `sqrt(2)*sigma_d` from its LENGTH
ALONE, with no event effect at all. Measuring the SD of daily returns that happen to fall on event
days therefore UNDERSTATES `k` and makes the kill look closer than it is: it returns a median of
2.07 against the correct 2.91. Both are reported below.
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import research_log                          # noqa: E402
from valuation.edge.event_spine import EventSpine                # noqa: E402
from valuation.edge.power_gate import (critical_value,           # noqa: E402
                                       Z_POWER_CONVENTION)

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
V6_JSON = os.path.join(_ROOT, "data", "free_analysis", "V6_DIP_DETECTOR.json")
BARS = os.path.join(_ROOT, "data", "bulk", "prepared", "bars")
OUT = os.path.join(_ROOT, "data", "free_analysis", "DC1_K1.json")

#: `V6`'s own panel window. The dispersion is measured on the same period the banked t came from.
LO, HI = "2009-01-15", "2026-01-28"
#: DC-1 §6(a). The matched `V6` arm is the one sharing this depth.
DC1_DEPTH = 0.30
#: DC-1 §6(c): the event window is [0, +1] sessions -- TWO sessions.
EVENT_SESSIONS = 2


def measure_k() -> dict:
    """k = sigma_e / sigma_d, with sigma_e the [0,+1] CUMULATIVE window SD."""
    if not os.path.isdir(BARS):
        raise FileNotFoundError(
            "%s is absent. `DEEPITM-FIN` shipped a clean, plausible null from a directory that "
            "merely existed; refusing to report a dispersion from no bars." % BARS)
    files = sorted(glob.glob(os.path.join(BARS, "*.pkl")))
    spine = EventSpine.build(names=[os.path.basename(f)[:-4].upper() for f in files])
    kw, kd, sig_e, pooled, n_win = [], [], [], [], 0
    for f in files:
        t = os.path.basename(f)[:-4].upper()
        ds = spine.dates_or_unknown(t)
        if not ds:
            continue
        b = pd.read_pickle(f)
        if not isinstance(b, dict) or "close" not in b or "date" not in b:
            continue
        # `close` is the ADJUSTED series, which is the right basis for a RETURN. `raw_close` is
        # for anything touching a strike (`U1-SPLIT`).
        df = pd.DataFrame({"date": b["date"], "close": b["close"]}).dropna()
        df["date"] = df["date"].astype(str).str[:10]
        df = df[(df["date"] >= LO) & (df["date"] <= HI)].sort_values("date").reset_index(drop=True)
        if len(df) < 300:
            continue
        c = df["close"].astype(float).values
        r1 = np.full(len(c), np.nan)
        r1[1:] = c[1:] / c[:-1] - 1.0
        r2 = np.full(len(c), np.nan)
        r2[EVENT_SESSIONS:] = c[EVENT_SESSIONS:] / c[:-EVENT_SESSIONS] - 1.0
        idx = np.where(df["date"].isin({str(d)[:10] for d in ds}).values)[0]
        win = [r2[i + 1] for i in idx if i + 1 < len(r2) and np.isfinite(r2[i + 1])]
        mask = np.zeros(len(c), dtype=bool)
        for i in idx:
            for j in (i, i + 1):
                if 0 <= j < len(c):
                    mask[j] = True
        ordinary = r1[(~mask) & np.isfinite(r1)]
        evday = r1[mask & np.isfinite(r1)]
        if len(win) >= 20 and len(ordinary) >= 250:
            sd_d = float(np.std(ordinary, ddof=1))
            if sd_d > 0:
                kw.append(float(np.std(win, ddof=1)) / sd_d)
                kd.append(float(np.std(evday, ddof=1)) / sd_d)
                sig_e.append(float(np.std(win, ddof=1)))
                pooled.extend(win)
                n_win += len(win)
    kw, kd = np.asarray(kw), np.asarray(kd)
    return {"n_names": int(kw.size), "n_event_windows": int(n_win),
            "k_window_median": float(np.median(kw)), "k_window_mean": float(kw.mean()),
            "k_window_p05": float(np.percentile(kw, 5)),
            "k_window_p95": float(np.percentile(kw, 95)),
            "k_dayonly_median_UNDERSTATES": float(np.median(kd)),
            "sqrt2_length_floor": float(math.sqrt(EVENT_SESSIONS)),
            "sigma_e_pooled_pp": float(100.0 * np.std(np.asarray(pooled), ddof=1)),
            "sigma_e_per_name_median_pp": float(100.0 * np.median(np.asarray(sig_e)))}


def main() -> int:
    v6 = json.load(open(V6_JSON))
    neq = research_log.detail()["by_domain"]["equity"]
    bar = critical_value(n_trials=neq)
    print("equity N = %d ; DC-1's bar |t| > %.7f (re-read at run, MA37; the draft writes 3.3145)"
          % (neq, bar))

    cells = []
    for arm in ("A1", "A2", "A3", "A4"):
        a = v6["arms"][arm]
        for leg in ("L1", "L2"):
            f = a["legs"][leg]["full"]
            cells.append({"arm": arm, "leg": leg, "depth": a["depth"], "W": a["horizon"],
                          "n": f["n"], "mean_pp": 100.0 * f["mean"], "t": f["t"],
                          "matched": a["depth"] == DC1_DEPTH and a["horizon"] == 63})

    k = measure_k()
    K = k["k_window_median"]
    print("\n=== MEASURED k (the draft says 'the MEASURED dispersion ratio') ===")
    print("  %d names, %d event windows, window = [0,+1] CUMULATIVE" % (k["n_names"],
                                                                        k["n_event_windows"]))
    print("  k median %.4f | mean %.4f | p05 %.4f | p95 %.4f"
          % (K, k["k_window_mean"], k["k_window_p05"], k["k_window_p95"]))
    print("  (daily-on-event-days would read %.4f and UNDERSTATES it; the sqrt(2) floor from"
          % k["k_dayonly_median_UNDERSTATES"])
    print("   window LENGTH alone, with no event effect at all, is %.4f)" % k["sqrt2_length_floor"])
    print("  sigma_e pooled %.4f pp (the draft parameterised 8.0 pp)" % k["sigma_e_pooled_pp"])

    print("\n=== ROUTE A: implied event-time t = V6_t * sqrt(W)/k ===")
    res = []
    for c in cells:
        gain_meas = math.sqrt(c["W"]) / K
        it_meas = c["t"] * gain_meas
        it_best = c["t"] * (math.sqrt(c["W"]) / 2.0)      # the draft's own best tabulated k
        k_needed = abs(c["t"]) * math.sqrt(c["W"]) / bar if c["t"] else float("nan")
        c.update({"implied_t_at_measured_k": it_meas, "implied_t_at_k2": it_best,
                  "k_required_to_clear": k_needed,
                  "clears_at_measured_k": bool(abs(it_meas) >= bar),
                  "clears_at_k2": bool(abs(it_best) >= bar)})
        res.append(c)
        tag = "<-- MATCHED" if c["matched"] else "   (depth %.2f: different population)" % c["depth"]
        print("  %s %s W=%3d  banked t %+.4f | implied @k=%.3f %+.4f %-6s | @k=2 %+.4f %-6s | "
              "needs k<=%.4f  %s"
              % (c["arm"], c["leg"], c["W"], c["t"], K, it_meas,
                 "CLEARS" if c["clears_at_measured_k"] else "FAILS", it_best,
                 "CLEARS" if c["clears_at_k2"] else "FAILS", k_needed, tag))

    matched = [c for c in res if c["matched"]]
    any_matched_clears = any(c["clears_at_measured_k"] for c in matched)
    any_cell_clears = any(c["clears_at_measured_k"] for c in res)

    print("\n=== ROUTE B: the EFFECT SIZE, independent of Route A ===")
    print("  Best case the mechanism permits: the ENTIRE 63-day excess sits in the event window.")
    s = k["sigma_e_pooled_pp"]
    for c in matched:
        J = c["mean_pp"]
        if J <= 0:
            print("  %s %s: J = %+.4f pp -- NEGATIVE, the banked effect points AGAINST the "
                  "mechanism." % (c["arm"], c["leg"], J))
            c["n_eff_required_80"] = None
            continue
        n80 = ((bar + Z_POWER_CONVENTION) * s / J) ** 2
        n50 = (bar * s / J) ** 2
        c["n_eff_required_80"] = n80
        print("  %s %s: J = %+.4f pp at measured sigma_e %.4f pp"
              % (c["arm"], c["leg"], J, s))
        print("     n_eff required: %.0f at 80%% power, %.0f at 50%%. The draft's most optimistic "
              "tabulated row is 400." % (n80, n50))

    verdict = "K1 FIRES -- DC-1 STOPS, ZERO TRIALS" if not any_matched_clears else \
              "K1 does not fire on the matched arm"
    print("\n=== VERDICT: %s ===" % verdict)
    print("  matched-arm cells clearing at the measured k: %d of %d"
          % (sum(c["clears_at_measured_k"] for c in matched), len(matched)))
    print("  ANY V6 full-sample cell clearing at the measured k, either depth: %s"
          % ("yes" if any_cell_clears else "NO"))

    out = {"item": "DC-1", "stage": 1, "kill": "K1", "trials": 0,
           "register_committed": False, "arm_run": False,
           "equity_N": neq, "bar": bar, "dc1_depth": DC1_DEPTH,
           "k": k, "cells": res, "verdict": verdict,
           "matched_cells_clearing": int(sum(c["clears_at_measured_k"] for c in matched)),
           "any_cell_clearing": bool(any_cell_clears)}
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
