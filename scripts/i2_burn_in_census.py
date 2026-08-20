"""I-2 -- the burn-in census, and the validation that licenses the engine to have consumers.

`IDEAS_LEDGER.md` PART 3: the engine *"ships with the burn-in census so the survivorship cost is
a printed fact before any arm."* `E-6`'s pre-outcome kill reads the row share this prints.

**ZERO TRIALS, NO VERDICT, AND NO OUTCOME RELATIONSHIP.** `fwd_ret` is never loaded -- an
allowlist on the columns makes that structural rather than a promise, the way `MB18`'s
look-ahead pin was built. This script counts what survives a burn-in. Whether the surviving
rows predict anything is `E-6`'s arm, `E-6`'s register and `E-6`'s trial.

**IT DOES NOT RESOLVE `E-6` AND MUST NOT BE READ AS DOING SO.** `E-6` pre-commits a >= 60%
eligible-row bar. This prints the fraction; it does not compare it, does not record a verdict
and does not write one anywhere. `MB1-SEL`'s precedent is the exact shape and the reason it
costs nothing: *"a control can only ever BLOCK a finding, never produce one, so it adds no
degree of freedom to any published claim."*

Run:
    python -m scripts.i2_burn_in_census
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from valuation.studies import name_percentile as NP  # noqa: E402

DEFAULT_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join("data", "free_analysis", "panel_r5r6.pkl")

#: THE ALLOWLIST. `fwd_ret` is not in it and cannot be, so no outcome relationship is reachable
#: from this script even by accident -- `MB18`'s structural pin rather than a promise.
KEEP = ("date", "ticker", "value")

#: `E-6`'s own axis: the value theme against the name's own history. Quarterly panel, so a
#: burn-in in OBSERVATIONS is a burn-in in quarters when the name is present throughout.
BURN_INS = (4, 8, 12, 16, 20, 24, 28, 32, 40)
FIVE_YEARS, TEN_YEARS = 20, 40

#: `S18`'s floor, the thinnest split this project's shipped gate accepts, reported so a reader
#: can see whether a burn-in leaves enough dates to halve at all. Not a bar applied here.
S18_MIN_DATES_PER_HALF = 16


def _root(explicit=None):
    """`data/` is gitignored; probe for the FILE, never the directory (DEEPITM-FIN)."""
    cands = [explicit, os.environ.get("VALQUO_DATA_ROOT"), DEFAULT_ROOT]
    here = REPO
    for _ in range(6):
        cands.append(here)
        here = os.path.dirname(here)
    for c in cands:
        if c and os.path.isfile(os.path.join(c, PANEL)):
            return c
    raise SystemExit(f"[i2] no data root holding {PANEL}")


def _load(root):
    panel = pickle.load(open(os.path.join(root, PANEL), "rb"))
    missing = [c for c in KEEP if c not in panel.columns]
    if missing:
        raise SystemExit(f"[i2] panel is missing {missing}")
    sub = panel[list(KEEP)].copy()
    if sub.empty:
        raise SystemExit("[i2] the allowlisted frame is EMPTY -- refusing rather than "
                         "reporting a census over nothing (MB21's vacuous-control lesson)")
    return sub


def main():
    root = _root()
    p = _load(root)
    print(f"[i2] data root : {root}")
    print(f"[i2] frame     : {p.shape[0]:,} rows x {p.shape[1]} cols "
          f"(allowlist {KEEP}; fwd_ret is NOT loaded)")

    cen = NP.burn_in_census(p, "value", BURN_INS, invert=False,
                            min_names_per_date=30)
    print(f"[i2] panel     : {cen['panel_names']:,} names, {cen['panel_dates']} dates, "
          f"{cen['panel_first_date']} -> {cen['panel_last_date']}, "
          f"{cen['panel_rows_with_a_value']:,} rows carrying a value")

    print("\n  burn-in   eligible rows      share   names   dates  first eligible   "
          "median yrs @ eligibility")
    for r in cen["burn_ins"]:
        mh = r["median_history_years_at_eligibility"]
        print(f"  {r['burn_in_observations']:>7}   {r['eligible_rows']:>13,}   "
              f"{r['eligible_row_share']:>8.4f}   {r['eligible_names']:>5,}   "
              f"{r['eligible_dates']:>5}   {str(r['first_eligible_date']):>14}   "
              f"{('%.2f' % mh) if mh is not None else 'n/a':>10}")

    five = next(r for r in cen["burn_ins"] if r["burn_in_observations"] == FIVE_YEARS)
    ten = next(r for r in cen["burn_ins"] if r["burn_in_observations"] == TEN_YEARS)
    print(f"\n[i2] the two the ledger names:")
    print(f"     5y  ({FIVE_YEARS} obs): {five['eligible_row_share']:.4f} of rows, "
          f"{five['eligible_dates']} dates, first {five['first_eligible_date']}")
    print(f"     10y ({TEN_YEARS} obs): {ten['eligible_row_share']:.4f} of rows, "
          f"{ten['eligible_dates']} dates, first {ten['first_eligible_date']}")
    print(f"     S18's 16-date-per-half floor needs {2 * S18_MIN_DATES_PER_HALF} dates; "
          f"5y leaves {five['eligible_dates']}, 10y leaves {ten['eligible_dates']}")

    # --------------------------------------------------------------- "five years" has two readings
    # The module docstring's decision, made numerical. On a QUARTERLY panel the 20th observation
    # sits 19 quarters after the first, so twenty observations buy 4.75 calendar years and not
    # five. A register meaning CALENDAR time therefore gets a different, stricter population from
    # one meaning OBSERVATIONS -- and the two readings are reported side by side so whoever
    # writes E-6 picks deliberately instead of inheriting whichever the code happened to do.
    p20 = NP.name_percentiles(p, "value", burn_in=FIVE_YEARS, invert=False)
    obs_only = int(NP.eligible_rows(p20, "value_pct").sum())
    cal_5y = int(NP.eligible_rows(p20, "value_pct", min_history_years=5.0).sum())
    tot = int(p["value"].notna().sum())
    p21 = NP.name_percentiles(p, "value", burn_in=FIVE_YEARS + 1, invert=False)
    obs21 = int(NP.eligible_rows(p21, "value_pct").sum())
    readings = {
        "observations_20": {"eligible_rows": obs_only, "share": obs_only / tot},
        "observations_20_AND_calendar_5y": {"eligible_rows": cal_5y, "share": cal_5y / tot},
        "observations_21": {"eligible_rows": obs21, "share": obs21 / tot},
        "note": ("on a quarterly panel the 20th observation is 19 quarters after the first, so "
                 "20 observations buy 4.75 calendar years, not 5. A register meaning calendar "
                 "time must say so; the two readings give different populations."),
    }
    print(f"\n[i2] 'a five-year burn-in' has two readings, and they differ:")
    print(f"     20 observations                      : {obs_only:>7,} rows  "
          f"({obs_only / tot:.4f})")
    print(f"     20 observations AND >= 5.00 cal years: {cal_5y:>7,} rows  ({cal_5y / tot:.4f})")
    print(f"     21 observations (the first to span 5y): {obs21:>7,} rows  ({obs21 / tot:.4f})")

    # --------------------------------------------------------------- the no-look-ahead proof
    # Rule 2, demonstrated on the REAL panel rather than only on a fixture. Truncating the panel
    # to its first k dates must give bit-identical percentiles to computing on the whole panel
    # and truncating afterwards.
    dates = sorted(p["date"].astype(str).str[:10].unique())
    k = len(dates) // 2
    keep = set(dates[:k])
    full = NP.name_percentiles(p, "value", burn_in=FIVE_YEARS, invert=False)
    short = NP.name_percentiles(p[p["date"].astype(str).str[:10].isin(keep)],
                                "value", burn_in=FIVE_YEARS, invert=False)
    f2 = full[full["date"].isin(keep)].sort_values(["ticker", "date"]).reset_index(drop=True)
    s2 = short.sort_values(["ticker", "date"]).reset_index(drop=True)
    same_shape = (f2.shape == s2.shape)
    a = f2["value_pct"].to_numpy(dtype=float)
    b = s2["value_pct"].to_numpy(dtype=float)
    both_nan = np.isnan(a) & np.isnan(b)
    worst = float(np.nanmax(np.abs(np.where(both_nan, 0.0, a - b)))) if a.size else float("nan")
    compared = int(a.size)
    print(f"\n[i2] rule 2 on the REAL panel: truncate to the first {k} of {len(dates)} dates")
    print(f"     rows compared    : {compared:,}   (shapes match: {same_shape})")
    print(f"     max |delta|      : {worst:.3e}")
    keys_equal = bool((f2["ticker"].to_numpy() == s2["ticker"].to_numpy()).all()
                      and (f2["date"].to_numpy() == s2["date"].to_numpy()).all())
    print(f"     keys identical   : {keys_equal}")

    ok = bool(same_shape and keys_equal and compared > 10_000 and worst == 0.0)

    out = {
        "item": "I-2",
        "module": "valuation/studies/name_percentile.py",
        "panel": PANEL,
        "columns_loaded": list(KEEP),
        "fwd_ret_loaded": False,
        "census": cen,
        "five_year_readings": readings,
        "no_lookahead_on_the_real_panel": {
            "truncated_to_first_k_dates": k, "of_dates": len(dates),
            "rows_compared": compared, "shapes_match": same_shape,
            "keys_identical": keys_equal, "max_abs_delta": worst},
        "s18_min_dates_per_half": S18_MIN_DATES_PER_HALF,
        "e6_reads_this_but_no_verdict_is_recorded_here": True,
        "all_pass": ok,
    }
    dest = os.path.join(REPO, "data", "free_analysis", "I2_BURN_IN_CENSUS.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with io.open(dest, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(f"\n[i2] wrote {dest}")
    print(f"[i2] ALL PASS = {ok}")
    print("[i2] NOTE: the row share above is E-6's INPUT. No verdict is recorded here.")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
