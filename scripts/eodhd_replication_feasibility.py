# -*- coding: utf-8 -*-
"""Is a 2009-2026 second-vendor replication FEASIBLE? Bars fixed here, before any measurement.

**THIS FILE IS COMMITTED ALONE AND BEFORE IT IS RUN.** The bars below are therefore a git-provable
pre-commitment rather than a number chosen once the coverage was on screen, which is the whole
reason the ordering matters: `W-28`'s rule is that a pre-committed bar may not be relaxed after it
is watched to fail, and the only way to be held to that is for the bar to predate the reading.

**ZERO TRIALS, `FIXED`-class.** A feasibility measurement is a fact about what data exists. It can
only ever BLOCK a register (`MB1-SEL`), so it costs nothing and may be read first.

---

## WHAT A 2009-2026 REPLICATION COULD AND COULD NOT SHOW

Stated before the measurement so a clearing result cannot be oversold afterwards.

* **Prices would still be Sharadar's.** `momentum` and `size` are built from the price store on both
  sides -- step 3 measured them at 0.9993 and 0.9975 for exactly that reason -- so a replication
  tests the **fundamentals** only.
* **The period is the one the model was tuned on.** 2009-2026 IS the panel. **It is NOT
  out-of-sample in any sense**, and step 4 established that the only out-of-sample era available,
  1999-2008, is unreachable on both sides of the join.
* **So the question it answers is narrow and worth stating in one line: would the published
  backtest survive if its fundamentals had come from a different vendor?** That is a real
  robustness question -- a result resting on one vendor's restatement policy is weaker than one
  that does not -- and it is emphatically not new evidence that the edge exists.
* **A disagreement would not be attributable without the coverage split below**, because a thinner
  universe is a different book, not a different vendor.

---

## THE BARS, PRE-COMMITTED

A replication must score **the same book**, or it is measuring universe composition and calling it
vendor disagreement. Three conditions, all required; **ambiguous against any of them is NOT
FEASIBLE**, following `D9`'s own convention.

* **`R1` CELL COVERAGE >= 0.85.** The share of panel rows for which EODHD carries a statement period
  **filed on or before that row's rebalance date**. 0.85 is `W-1`'s bar on this panel, reused rather
  than re-chosen; `W-28` set 0.90 on a Compustat linkage and could not reach it, and the gap between
  those two is the honest range for a dated vendor join here.
* **`R2` PER-DATE COVERAGE >= 0.70 ON EVERY ONE OF THE 69 DATES.** A replication of a 17-year
  backtest cannot have an era hole; a mean can hide one entirely. `D6` ran at 69.09% of cells but
  checked that **all** its dates were covered, and that is the property being borrowed.
* **`R3` THE SURVIVORSHIP SPLIT MUST NOT EXCEED 0.15.** Coverage on names **still in the panel at
  its last date** minus coverage on names that **left before it**. Step 4 measured EODHD empty on
  **95.83%** of companies that died before 2009 against **10.53%** of survivors, so the obvious
  hazard is that the same hole bites one era later: many of the panel's 9,645 names died between
  2009 and 2026, and if the vendor is blank for them a replication silently becomes a
  survivors-only backtest. **This is the bar most likely to fail and it is the one worth measuring.**
  It is the `O-1` lesson stated as a condition rather than as a caveat: a pooled coverage rate is
  not evidence about the sub-population a result would actually rest on.

**NO BAR IS SET ON AGREEMENT**, because agreement is the register's business and not feasibility's.
This file measures whether the arm CAN be run, never whether it would pass.
"""
import argparse
import bisect
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as _D                              # noqa: E402
from valuation.studies import eodhd_provider as EP                       # noqa: E402

_DATA = _D.data_root(required=False) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(_DATA, "free_analysis", "EODHD_REPLICATION_FEASIBILITY.json")
FREEZE = os.path.join(r"D:\eodhd", "freeze_2026-10-22")

#: Pre-committed. Changing any of these after a reading voids the item.
R1_CELL_COVERAGE = 0.85
R2_PER_DATE_FLOOR = 0.70
R3_MAX_SURVIVORSHIP_SPLIT = 0.15


def datekeys_by_ticker(tickers):
    """Sorted filing dates per name, read once from the freeze. Absent names return an empty list.

    An absent name is NOT dropped: it is a covered-zero, which is the whole point of the exercise.
    Silently excluding it would measure coverage on the names that have coverage.
    """
    out = {}
    for t in tickers:
        pay = EP.load_unit(FREEZE, t)
        if pay is None:
            out[t] = []
            continue
        out[t] = sorted({r["datekey"] for r in EP.fundamentals_rows(pay, t) if r.get("datekey")})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args(argv)

    p = pd.read_pickle(_D.panel_path())
    p = p[["ticker", "date"]].copy()
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["date"] = pd.to_datetime(p["date"]).dt.strftime("%Y-%m-%d")
    names = sorted(p["ticker"].unique())
    last_date = max(p["date"])

    dk = datekeys_by_ticker(names)
    have_payload = sum(1 for t in names if dk[t])

    # A row is covered when the vendor carries a period FILED ON OR BEFORE the rebalance date --
    # the same strictly-point-in-time rule step 3 scored under, not merely "the name exists".
    cov = [bool(dk[t]) and bisect.bisect_right(dk[t], d) > 0
           for t, d in zip(p["ticker"], p["date"])]
    p["covered"] = cov

    per_date = p.groupby("date")["covered"].mean().sort_index()
    alive_last = set(p.loc[p["date"] == last_date, "ticker"])
    p["alive_at_end"] = p["ticker"].isin(alive_last)
    by_surv = p.groupby("alive_at_end")["covered"].agg(["mean", "size"])

    cell = float(p["covered"].mean())
    surv_hi = float(by_surv.loc[True, "mean"]) if True in by_surv.index else None
    surv_lo = float(by_surv.loc[False, "mean"]) if False in by_surv.index else None
    split = (surv_hi - surv_lo) if (surv_hi is not None and surv_lo is not None) else None

    rep = {"item": "EODHD-REPL-FEAS", "trials": 0, "class": "FIXED",
           "freeze": FREEZE,
           "bars": {"R1_cell_coverage": R1_CELL_COVERAGE,
                    "R2_per_date_floor": R2_PER_DATE_FLOOR,
                    "R3_max_survivorship_split": R3_MAX_SURVIVORSHIP_SPLIT},
           "panel": {"rows": int(len(p)), "names": len(names), "dates": int(len(per_date)),
                     "first_date": min(p["date"]), "last_date": last_date},
           "names_with_any_payload": have_payload,
           "R1_cell_coverage": cell,
           "R1_pass": bool(cell >= R1_CELL_COVERAGE),
           "R2_per_date_min": float(per_date.min()),
           "R2_per_date_median": float(per_date.median()),
           "R2_per_date_max": float(per_date.max()),
           "R2_dates_below_floor": int((per_date < R2_PER_DATE_FLOOR).sum()),
           "R2_worst_dates": {str(d): float(v) for d, v in per_date.nsmallest(5).items()},
           "R2_pass": bool((per_date >= R2_PER_DATE_FLOOR).all()),
           "coverage_alive_at_end": surv_hi,
           "coverage_left_before_end": surv_lo,
           "rows_alive_at_end": int(by_surv.loc[True, "size"]) if True in by_surv.index else 0,
           "rows_left_before_end": int(by_surv.loc[False, "size"]) if False in by_surv.index else 0,
           "R3_survivorship_split": split,
           "R3_pass": bool(split is not None and split <= R3_MAX_SURVIVORSHIP_SPLIT)}
    rep["feasible"] = bool(rep["R1_pass"] and rep["R2_pass"] and rep["R3_pass"])
    rep["what_it_could_show"] = (
        "Prices stay Sharadar's on both sides and 2009-2026 IS the period the model was tuned on, "
        "so a replication tests vendor independence of the FUNDAMENTALS only. It is NOT "
        "out-of-sample. The only out-of-sample era, 1999-2008, is unreachable on both sides of the "
        "join (EODHD_DELISTED.json).")

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)

    print("panel %d rows, %d names, %d dates (%s -> %s)"
          % (len(p), len(names), len(per_date), rep["panel"]["first_date"], last_date))
    print("names with any EODHD payload: %d of %d" % (have_payload, len(names)))
    print("R1 cell coverage      %.4f   bar %.2f  -> %s" % (cell, R1_CELL_COVERAGE, rep["R1_pass"]))
    print("R2 per-date min       %.4f   bar %.2f  -> %s  (%d of %d dates below)"
          % (rep["R2_per_date_min"], R2_PER_DATE_FLOOR, rep["R2_pass"],
             rep["R2_dates_below_floor"], len(per_date)))
    print("   median %.4f  max %.4f" % (rep["R2_per_date_median"], rep["R2_per_date_max"]))
    print("R3 alive-at-end %.4f vs left-before-end %.4f -> split %.4f  bar %.2f  -> %s"
          % (surv_hi or 0.0, surv_lo or 0.0, split or 0.0, R3_MAX_SURVIVORSHIP_SPLIT,
             rep["R3_pass"]))
    print("   rows: alive %d, left %d" % (rep["rows_alive_at_end"], rep["rows_left_before_end"]))
    print("FEASIBLE: %s -> %s" % (rep["feasible"], OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
