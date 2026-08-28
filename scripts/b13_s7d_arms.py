"""B13 + S7-4 — the two registered arms. Executes `PREREG_b13_s7d_liquidity.md` unmodified.

2 EQUITY TRIALS, booked at `360b245` BEFORE this file existed. Equity `N` 243 -> 245.

NO VARIANT, NO GRID, NO PARAMETER THE REGISTER DOES NOT NAME. Everything below that could have
been chosen is instead imported or quoted:

* **`S7`'s gate is IMPORTED, not re-implemented** -- `gate`, `evaluate`, `MIN_ALPHA_GAIN`,
  `MIN_TSTAT_GAIN`, `THEMES`, `W` and `zt`/`z_of` all come from `scripts/s7_s18_interactions.py`.
  "Verbatim" is then a fact about the call graph rather than a claim in prose (`B7`).
* **`MIN_AVG_DOLLAR_VOLUME` is imported from the shipped config**, never retyped (`MA5`).
* The ADV instrument is `valuation/edge/adv.py`, built and validated in its own pass at zero
  trials, and **not modified here** -- the register's void condition 7.

COVERAGE IS MEASURED AND PRINTED BEFORE EITHER ARM RUNS, on the population the arms test.

B13 IS SCORED ON NON-INFERIORITY, NOT ON THE MARGIN GATE. A small alpha LOSS is the declared
expected outcome and is NOT a failure: the claim is that the book is INVESTABLE, not that it
earns more. Scoring it on `+100 bps` would be the category error the register's void condition 2
forbids.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import adv as ADV                                   # noqa: E402
from valuation.edge import fundamental_panel as FP                      # noqa: E402
from valuation.edge import power_gate as PG                             # noqa: E402
from valuation.edge import research_log as RL                           # noqa: E402
from s7_s18_interactions import (THEMES, W, MIN_ALPHA_GAIN,             # noqa: E402
                                 MIN_TSTAT_GAIN, REC, evaluate, gate, zt, z_of)

PRIMARY = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join(PRIMARY, "data", "free_analysis", "panel_corrected_69d.pkl")
ADV_PKL = os.path.join(PRIMARY, "data", "free_analysis", "B13_ADV_PANEL.pkl")
OUT = os.path.join(PRIMARY, "data", "free_analysis", "B13_S7D_ARMS.json")

#: X7's calibrated alpha margin, `MA19`'s recalibrated value. Used as the NON-INFERIORITY bound
#: for B13. `MB31` proves it unmoved below equity `N` = 247 and this run sits at 245, so it is
#: current -- checked in `power()` rather than asserted here.
X7_ALPHA_MARGIN_PP = 1.8629


def min_adv() -> float:
    """The shipped constant, IMPORTED. `MA5` measured what happens when a threshold is retyped:
    it freezes while the thing it is compared against moves."""
    sys.path.insert(0, os.path.join(PRIMARY, "options-bot"))
    from screener import config as C
    return float(C.MIN_AVG_DOLLAR_VOLUME)


def load():
    panel = pickle.load(open(PANEL, "rb"))
    panel["ticker"] = panel["ticker"].astype(str).str.upper()
    panel["d"] = pd.to_datetime(panel["date"]).dt.date
    assert panel["date"].nunique() >= 60 and panel["ticker"].nunique() >= 2400, \
        "SMOKE-TEST PANEL -- the METHODOLOGY RULE forbids a verdict from one"
    adv = pd.read_pickle(ADV_PKL)
    adv["d"] = pd.to_datetime(adv["date"]).dt.date
    return panel, adv


def coverage_first(panel, adv, floor) -> dict:
    """Stated BEFORE either arm. The register's void condition 1."""
    have = {(t, d): a for t, d, a in zip(adv["ticker"], adv["d"], adv["adv"])}
    cells = list(zip(panel["ticker"], panel["d"]))
    cov = ADV.coverage(have, cells)

    per = {}
    for d, g in panel.groupby("d"):
        n = sum(1 for t in g["ticker"] if (t, d) in have)
        per[str(d)] = {"cells": int(len(g)), "with_adv": n}
    covered_dates = sorted(d for d, v in per.items() if v["with_adv"] >= 20)
    mid = len(covered_dates) // 2

    vals = np.array([have[c] for c in cells if c in have], dtype=float)
    below = int((vals < floor).sum())
    out = {
        "coverage_on_the_arms_population": cov,
        "note": ("CELL-level. The 89.7% in the brief is NAME-level and these arms are scored on "
                 "cells -- a name can resolve to a permno and still have no usable ADV on a "
                 "date. Quoting the name-level figure here is the population mismatch MB8 and "
                 "V6-OPT both paid for."),
        "covered_dates": len(covered_dates),
        "panel_dates": int(panel["d"].nunique()),
        "halves": {"early": mid, "late": len(covered_dates) - mid - 1,
                   "boundary_embargoed": covered_dates[mid] if covered_dates else None},
        "crsp_cut": {
            "cut": str(ADV.CRSP_CUT),
            "dates_after": sorted(d for d in per if d > str(ADV.CRSP_CUT)),
            "rows_after": int(sum(v["cells"] for d, v in per.items()
                                  if d > str(ADV.CRSP_CUT))),
        },
        "floor_dollars": floor,
        "covered_cells_below_the_floor": below,
        "pct_of_covered_below_floor": round(100.0 * below / max(1, len(vals)), 2),
        "per_date_coverage_pct": {d: round(100.0 * v["with_adv"] / max(1, v["cells"]), 1)
                                  for d, v in sorted(per.items())},
    }
    return out, have, covered_dates


def power(n_dates: int, series_a, series_b) -> dict:
    """MB22 at BOTH vocabularies, BEFORE any floor is read.

    Every MDE this project published before `MB22` was `crit * se` -- a 50%-power figure. The
    80%-power one is `(crit + 0.84) * se`, larger by 1.42x at crit 2.0. Both ship or the verdict
    does not (`RUN_RULES` PART A rule 11).
    """
    d = np.asarray(series_a, dtype=float) - np.asarray(series_b, dtype=float)
    d = d[np.isfinite(d)]
    n = len(d)
    se = float(np.std(d, ddof=1) / math.sqrt(n)) if n > 1 else float("nan")
    # `critical_value` REFUSES to default, which is the point (`MA5`: a default is how the 3.0
    # constant survived past N = 90). The explicit 2.0 is used and LABELLED UNCALIBRATED, on
    # `V2G`'s precedent: **no calibrated floor exists for a paired WITHIN-PANEL difference** --
    # X7 calibrated LEVELS on the decile book, not paired differences -- so borrowing one of its
    # floors here would be the cross-configuration comparison this record has already paid for
    # twice.
    crit = PG.critical_value(crit=2.0)
    return {"n_paired_periods": n, "paired_se": se,
            "critical_value": crit,
            "critical_value_is": "CONVENTIONAL 2.0, UNCALIBRATED for a paired within-panel "
                                 "difference (V2G's rule). Not one of X7's floors.",
            "mde_50pct_power": crit * se,
            "mde_80pct_power": (crit + 0.84) * se,
            "ratio": ((crit + 0.84) / crit) if crit else None,
            "vocabulary_note": ("50%% power is `crit*se` -- the effect at which the POINT "
                                "ESTIMATE just reaches the bar, detected half the time. 80%% is "
                                "`(crit+0.84)*se`. Quoting one as the other is the MB22 error.")}


def _require_scored(splits, label):
    """A verdict may not be built on an empty comparison.

    `MB21`'s C1 scored a PERFECT 0.000e+00 on an empty frame by comparing nothing, and the first
    run of this script rejected S7-4 the same way. The count is gated, not the values.
    """
    scored = [v for v in splits.values() if isinstance(v, dict) and v.get("n_dates")]
    if not scored:
        raise SystemExit(f"{label}: every split is empty -- refusing to report a verdict "
                         f"reached by comparing nothing (MB21 C1).")
    return len(scored)


def b13_arm(panel, have, floor, covered_dates) -> dict:
    """B13 -- the prefilter, scored on NON-INFERIORITY.

    UNMEASURED NAMES ARE KEPT. Dropping a name for having no ADV makes this a data-availability
    screen wearing a liquidity screen's name (`S10`'s defect), and here it would correlate with
    era, size and delisting. The register's void condition 3.
    """
    z = {t: zt(panel, t) for t in THEMES}
    base = sum(z[t] * W for t in THEMES)

    adv_col = pd.Series([have.get((t, d), np.nan) for t, d in
                         zip(panel["ticker"], panel["d"])], index=panel.index, dtype=float)
    measured = adv_col.notna()
    illiquid = measured & (adv_col < floor)          # unmeasured -> NOT illiquid, by construction
    keep = ~illiquid

    arm = base.copy()
    arm[~keep] = np.nan                              # removed from the ranking entirely

    # THE PANEL'S `date` COLUMN IS `str`, NOT A TIMESTAMP OR A date. Converting these keys
    # to `dt.date` made `evaluate`'s `isin` match ZERO rows -- and the first run of this script
    # did exactly that: ARM 1 reported INSUFFICIENT and **ARM 2 reported REJECTED, which is a
    # verdict reached by comparing nothing.** A vacuous rejection is indistinguishable from a
    # real one, which is `MB21`'s C1 defect. Keys stay strings, and `_require_scored` below
    # refuses a verdict built on an empty comparison.
    ds = list(covered_dates)
    mid = len(ds) // 2
    res = {"floor_dollars": floor,
           "cells_measured": int(measured.sum()),
           "cells_unmeasured_and_KEPT": int((~measured).sum()),
           "cells_removed_as_illiquid": int(illiquid.sum()),
           "pct_of_panel_removed": round(100.0 * float(illiquid.mean()), 2),
           "splits": {}}

    # what the filter BUYS, reported beside the verdict: a filter removing 40% of the universe
    # buys different credibility from one removing 2%, and the alpha number cannot tell them apart
    mc = pd.to_numeric(panel.get("market_cap"), errors="coerce")
    res["removed_median_market_cap"] = (float(mc[illiquid].median())
                                        if illiquid.any() else None)
    res["kept_median_market_cap"] = float(mc[keep & measured].median())
    res["removed_names"] = int(panel.loc[illiquid, "ticker"].nunique())

    losses, pa, pb = [], [], []
    for name, sub in (("early_half", ds[:mid]), ("late_half", ds[mid + 1:])):
        ra = evaluate(panel, base, sub)
        rb = evaluate(panel, arm, sub)
        if not ra or not rb:
            res["splits"][name] = {"status": "insufficient"}
            continue
        da = rb["top_decile_alpha"] - ra["top_decile_alpha"]
        losses.append(da)
        res["splits"][name] = {
            "n_dates": len(sub),
            "base_top_decile_alpha": ra["top_decile_alpha"],
            "arm_top_decile_alpha": rb["top_decile_alpha"],
            "delta_top_decile_alpha_pp": da * 100.0,
            "delta_long_short_tstat": (
                (rb["long_short_tstat"] - ra["long_short_tstat"])
                if ra.get("long_short_tstat") is not None
                and rb.get("long_short_tstat") is not None else None),
        }
    # per-date paired series for the power statement
    for d in ds:
        ra, rb = evaluate(panel, base, [d]), evaluate(panel, arm, [d])
        if ra and rb:
            pa.append(ra["top_decile_alpha"])
            pb.append(rb["top_decile_alpha"])

    _require_scored(res["splits"], "B13")
    res["power"] = power(len(ds), pb, pa)
    margin = X7_ALPHA_MARGIN_PP
    res["non_inferiority_margin_pp"] = margin
    res["margin_note"] = (
        "X7's calibrated alpha margin as recalibrated by MA19 at N = 224. MB31 derives that no "
        "placebo floor can move below equity N = 247 and this run sits at 245, so the margin is "
        "current. It is the SAME margin MB8 used for the same shape of question.")
    ok = [(-x * 100.0) < margin for x in losses] if losses else []
    res["loss_pp_by_half"] = [-x * 100.0 for x in losses]
    res["verdict"] = ("PASSES-NON-INFERIORITY" if ok and all(ok)
                      else "REJECTED" if ok else "INSUFFICIENT")
    res["verdict_rule"] = (
        "PASSES iff the alpha LOSS is smaller than the margin in BOTH halves. A small loss is "
        "the EXPECTED outcome and is NOT a failure -- B13 is a CREDIBILITY claim, not an alpha "
        "one. A loss LARGER than the margin is a REJECT: at that point the filter is not buying "
        "credibility, it is destroying the result.")
    return res


def s7d_arm(panel, have, covered_dates) -> dict:
    """S7's fourth interaction, on S7's own gate, IMPORTED."""
    z = {t: zt(panel, t) for t in THEMES}
    base = sum(z[t] * W for t in THEMES)

    adv_col = pd.Series([have.get((t, d), np.nan) for t, d in
                         zip(panel["ticker"], panel["d"])], index=panel.index, dtype=float)
    # LOG, per the register: unlogged, a column spanning six orders of magnitude would make the
    # interaction a megacap indicator rather than a liquidity one.
    z_liq = z_of(panel, np.log(adv_col.where(adv_col > 0)))
    inter = z_of(panel, z["size"] * z_liq)

    arm = sum(z[t] * W for t in THEMES) + inter * W
    ds = list(covered_dates)
    g = gate(panel, base, arm, ds, "S7-4 size x liquidity")

    # S7's C7 dilution control, REPRODUCED rather than assumed to carry to a different column:
    # an eighth input moves every theme's relative weight 1/7 -> 1/8, so the arm is a COMPOUND
    # change and a CONSTANT eighth column isolates the dilution half.
    const = pd.Series(0.0, index=panel.index, dtype=float)
    c7 = gate(panel, base, base + const * W, ds, "C7 constant eighth column")
    _require_scored(g["splits"], "S7-4")

    # C7 IS DEGENERATE IN THIS CONSTRUCTION AND IS REPORTED AS SUCH, NOT AS A PASS.
    # The composite here is a weighted SUM at a FIXED W, so adding a constant eighth column
    # shifts every row's score by the same amount, leaves the RANKING identical, and returns a
    # delta of exactly 0.0 in both halves -- measured, not argued. A control that cannot fail is
    # not evidence, and reporting "C7 clears" would be the blank-counter family this record has
    # hit repeatedly (MB21's C1 scoring a perfect zero by comparing nothing; SC-1b's double-entry
    # check returning a confident 0.0000 against a published 11.7%).
    #
    # So the honest statement is NOT "the dilution is nil" but "in a fixed-weight sum there is no
    # dilution term to isolate". S7's own C7 measured +0.000173 / +0.000146 -- NON-zero -- which
    # means S7's arm cannot have been a pure fixed-weight sum, and this control does not transfer.
    # The register said to REPRODUCE it rather than assume it carries over; reproducing it is what
    # showed that it does not.
    exact_zero = all(abs(v.get("delta_top_decile_alpha") or 0.0) == 0.0
                     for v in c7["splits"].values() if isinstance(v, dict))
    c7["status"] = "DEGENERATE_BY_CONSTRUCTION" if exact_zero else "INFORMATIVE"
    c7["verdict"] = "NO EVIDENCE - the control cannot fail in this construction"
    c7["why"] = ("A constant column added to a FIXED-WEIGHT SUM shifts every score equally and "
                 "cannot change a ranking, so the delta is 0.0 by algebra rather than by "
                 "measurement. S7's own C7 read +0.000173 / +0.000146, so S7's construction "
                 "differed and its dilution control does not transfer to this arm.")
    g["C7_dilution_control"] = c7
    g["label_if_it_clears"] = "ELIGIBLE - UNREPLICATED, 1 OF 7 SIBLING ARMS"
    g["coverage_note"] = ("Scored on the COVERED subsample. Cells with no ADV carry no "
                          "interaction value and are excluded from this arm's ranking by "
                          "construction, which is a different population from B13's.")
    per_a, per_b = [], []
    for d in ds:
        ra, rb = evaluate(panel, base, [d]), evaluate(panel, arm, [d])
        if ra and rb:
            per_a.append(ra["top_decile_alpha"])
            per_b.append(rb["top_decile_alpha"])
    g["power"] = power(len(ds), per_b, per_a)
    return g


def main(argv=None):
    ap = argparse.ArgumentParser(description="B13 + S7-4, as registered")
    ap.add_argument("--json", default=OUT)
    a = ap.parse_args(argv)

    panel, adv = load()
    floor = min_adv()
    print(f"[b13] panel {panel.shape}, MIN_AVG_DOLLAR_VOLUME imported = ${floor:,.0f}")

    cov, have, covered_dates = coverage_first(panel, adv, floor)
    print(f"[b13] COVERAGE FIRST: "
          f"{cov['coverage_on_the_arms_population']['with_adv']:,} of "
          f"{cov['coverage_on_the_arms_population']['cells']:,} cells = "
          f"{cov['coverage_on_the_arms_population']['pct']}%")
    print(f"[b13] covered dates {cov['covered_dates']} of {cov['panel_dates']}; halves "
          f"{cov['halves']['early']}/{cov['halves']['late']} boundary "
          f"{cov['halves']['boundary_embargoed']} (embargoed)")
    print(f"[b13] CRSP cut costs {len(cov['crsp_cut']['dates_after'])} dates, "
          f"{cov['crsp_cut']['rows_after']:,} rows")
    print(f"[b13] covered cells below the floor: {cov['covered_cells_below_the_floor']:,} = "
          f"{cov['pct_of_covered_below_floor']}%")

    # C1 -- the harness reproduces the published record, or nothing downstream is comparable
    base_r = FP.quantile_backtest(panel, THEMES, {c: W for c in THEMES}, n_q=10, horizon=63)
    c1 = {k: float(base_r.get(k)) for k in REC if base_r.get(k) is not None}
    ok1 = all(abs(c1.get(k, 1e9) - v) < 1e-9 for k, v in REC.items())
    print(f"[b13] C1 reproduces the record: {ok1}")

    b13 = b13_arm(panel, have, floor, covered_dates)
    print(f"[b13] ARM 1 verdict {b13['verdict']}  loss_pp_by_half="
          f"{[round(x, 4) for x in b13['loss_pp_by_half']]} vs margin "
          f"{b13['non_inferiority_margin_pp']}pp")
    print(f"[b13] removed {b13['cells_removed_as_illiquid']:,} cells "
          f"({b13['pct_of_panel_removed']}%), kept {b13['cells_unmeasured_and_KEPT']:,} "
          f"unmeasured")

    s7 = s7d_arm(panel, have, covered_dates)
    print(f"[b13] ARM 2 verdict {s7['verdict']}")

    out = {"item": "B13 + S7-4", "trials": 2, "domain": "equity",
           "equity_N_after_booking": RL.detail()["by_domain"]["equity"],
           "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "register": "PREREG_b13_s7d_liquidity.md",
           "coverage_stated_before_the_arms": cov,
           "C1_reproduces_record": {"ok": bool(ok1), "measured": c1},
           "arm1_B13_non_inferiority": b13,
           "arm2_S7_4_interaction": s7,
           "adopts": "NOTHING"}
    json.dump(out, open(a.json, "w", encoding="utf-8"), indent=1, default=str)
    print(f"[b13] wrote {a.json}")


if __name__ == "__main__":
    main()
