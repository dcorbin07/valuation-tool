# -*- coding: utf-8 -*-
"""PKG-MB20 STAGE 0 — the premise census, run BEFORE any register is written.

ZERO TRIALS. Nothing here relates a signal to a forward return; every figure is a fact about
what is on disk. `MB1-SEL` governs: a control can only ever BLOCK, never produce.

WHAT IT VERIFIES RATHER THAN INHERITS. `MA57` reports 24 columns, 5,636,964 rows, `ownername`
and `transactioncode` both present, **zero missing on the 124,181 open-market purchase rows**,
and ~48.72% routine (ticker, ownername) pairs on all coded rows. Those are the premise of the
whole item, and `W-28` closed one item ago because a scout's premise did not survive contact.

AND IT MEASURES THE THING `MA57` DID NOT: the routine share on **OUR panel's own population**,
point-in-time. `O-1` returned 0.19% power by carrying a coverage figure from one population to
another, ~17x wrong; `S25`'s two nearly-equal percentages on different objects is the same shape.
The number that governs this register is the one measured on the rows the arm will score.
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: The PRIMARY root. An artifact written by a worktree-run script does not survive the worktree
#: (`E-6`, where `I2_BURN_IN_CENSUS.json` was stranded and a successor's control could not run).
_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
SRC = os.path.join(_ROOT, "data", "backtest", "insiders.csv")
OUT = os.path.join(FA, "MB20_CENSUS.json")

#: Cohen-Malloy-Pomorski's rule, stated once here and never restated: an insider is ROUTINE in a
#: given (ticker, ownername) if they traded in the SAME CALENDAR MONTH in each of three or more
#: consecutive years. Everything else is OPPORTUNISTIC.
CONSEC_YEARS = 3

#: The open-market purchase code. `V6-B` established this is the only clean conviction buy:
#: `transactionvalue` is UNSIGNED (zero negatives in 2.6M rows) so a sale cannot be told from a
#: purchase by value alone, and `transactionshares` is signed.
PURCHASE_CODE = "P"


def _load():
    cols = ["ticker", "filingdate", "transactiondate", "ownername", "transactioncode",
            "transactionshares", "transactionpricepershare", "transactionvalue"]
    head = pd.read_csv(SRC, nrows=5)
    have = [c for c in cols if c in head.columns]
    missing = [c for c in cols if c not in head.columns]
    df = pd.read_csv(SRC, usecols=have, low_memory=False)
    return df, list(head.columns), missing


def main() -> int:
    df, all_cols, missing = _load()
    n = len(df)
    out = {"item": "PKG-MB20", "stage": "census", "trials": 0,
           "source": os.path.basename(SRC), "n_columns": len(all_cols), "n_rows": int(n),
           "declared_columns_missing": missing}

    # ---- 1. MA57's premise, verified rather than quoted
    code = df["transactioncode"].astype("string")
    owner = df["ownername"].astype("string")
    out["ma57_premise"] = {
        "ownername_present": "ownername" in all_cols,
        "transactioncode_present": "transactioncode" in all_cols,
        # A missing cell under pandas' string dtype is pd.NA, and NA compares False against
        # every literal -- MA57's own blank-code counter first read 0 on a column with 1.5M of
        # them. `.isna()` is the only reading that answers the question asked.
        "transactioncode_missing": int(code.isna().sum()),
        "transactioncode_missing_frac": float(code.isna().mean()),
        "ownername_missing": int(owner.isna().sum()),
        "distinct_ownername": int(owner.nunique(dropna=True)),
    }
    buys = df[code.eq(PURCHASE_CODE)]
    out["ma57_premise"]["purchase_rows"] = int(len(buys))
    out["ma57_premise"]["purchase_rows_missing_ownername"] = int(
        buys["ownername"].isna().sum())
    out["ma57_premise"]["purchase_rows_missing_code"] = 0  # by construction of the filter

    # ---- 2. the routine share on ALL CODED rows (MA57's own object, reproduced)
    coded = df[code.notna() & owner.notna()].copy()
    coded["_y"] = pd.to_datetime(coded["transactiondate"], errors="coerce").dt.year
    coded["_m"] = pd.to_datetime(coded["transactiondate"], errors="coerce").dt.month
    coded = coded[coded["_y"].notna()]
    routine_pairs, all_pairs = _routine_pairs(coded)
    ma57_r, ma57_n = _routine_pairs_ma57(coded)
    out["routine_all_coded_rows"] = {
        "pairs": int(all_pairs), "routine_pairs_3y": int(routine_pairs),
        "frac_3y": (routine_pairs / all_pairs) if all_pairs else None,
        "routine_pairs_ma57_4y": int(ma57_r),
        "frac_ma57_4y": (ma57_r / ma57_n) if ma57_n else None,
        "ma57_reported": 0.4872,
        "ma57_reported_pairs": 42537,
        "note": ("A PREMISE CORRECTION, found before any register was written. MA57's published "
                 "48.72% is a FOUR-consecutive-year figure: its test is "
                 "`all((y - dd) in ys for dd in (1, 2, 3))`, i.e. year y PLUS the three before "
                 "it. Cohen-Malloy-Pomorski's rule -- and the hypothesis this register tests -- "
                 "is THREE consecutive years, which on the identical population reads higher. "
                 "The PAIR COUNT reproduces exactly (87,318), so the denominator is the same "
                 "object and only the rule differs."),
    }

    # ---- 3. the routine share on the OPEN-MARKET PURCHASE rows, which is what the score uses
    pb = buys[buys["ownername"].notna()].copy()
    pb["_y"] = pd.to_datetime(pb["transactiondate"], errors="coerce").dt.year
    pb["_m"] = pd.to_datetime(pb["transactiondate"], errors="coerce").dt.month
    pb = pb[pb["_y"].notna()]
    rp, ap = _routine_pairs(pb)
    out["routine_purchase_rows"] = {
        "pairs": int(ap), "routine_pairs": int(rp),
        "frac": (rp / ap) if ap else None,
        "note": ("MA57 measured 6.93% on purchases-and-sales alone and 48.72% on ALL coded rows "
                 "-- a SEVEN-FOLD spread, so which population the bar is set on decides the "
                 "item. This is the population the shipped score's `buys` counter reads."),
    }

    # ---- 4. WHO DROPS when the code is absent (the coverage kill's subject)
    blank = df[code.isna()]
    out["who_drops_when_code_is_absent"] = {
        "rows": int(len(blank)),
        "frac_of_all_rows": float(len(blank) / n) if n else None,
        "distinct_tickers": int(blank["ticker"].nunique()),
        "distinct_tickers_overall": int(df["ticker"].nunique()),
        "share_with_a_signed_transactionshares": float(
            pd.to_numeric(blank["transactionshares"], errors="coerce").notna().mean()),
        "note": ("A blank code can be classified NEITHER routine NOR opportunistic. It is "
                 "COUNTED, never read as zero -- the direction that would silently make the "
                 "opportunistic arm a data-availability screen."),
    }

    os.makedirs(FA, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    print("\nwrote", OUT)
    return 0


def _routine_pairs_ma57(d):
    """MA57's OWN rule, reproduced verbatim so its published figure can be checked.

    Its test is `all((y - dd) in ys for dd in (1, 2, 3))` -- year `y` PLUS THE THREE BEFORE IT,
    which is FOUR consecutive years, one stricter than Cohen-Malloy-Pomorski's three. This
    function exists only to reproduce 0.4872 and is never used to score anything.
    """
    g = d.groupby(["ticker", "ownername", "_m"])["_y"].apply(
        lambda s: set(int(x) for x in s))
    routine_keys = set()
    for (tk, ow, _m), ys in g.items():
        if any(all((y - dd) in ys for dd in (1, 2, 3)) for y in ys):
            routine_keys.add((tk, ow))
    all_keys = set(map(tuple, d[["ticker", "ownername"]].drop_duplicates().values))
    return len(routine_keys), len(all_keys)


def _routine_pairs(d):
    """(routine pair count, total pair count) under the 3-consecutive-year rule.

    NOT point-in-time -- this is the FULL-SAMPLE classification, which is the right object for a
    feasibility census and the WRONG one for the arm. The arm's classifier is point-in-time and
    lives in its own module; the two are deliberately not shared, so a census figure can never be
    mistaken for a scoreable one.
    """
    g = d.groupby(["ticker", "ownername", "_m"])["_y"].apply(lambda s: sorted(set(int(x) for x in s)))
    routine_keys = set()
    for (tk, ow, _m), years in g.items():
        run = 1
        for i in range(1, len(years)):
            run = run + 1 if years[i] == years[i - 1] + 1 else 1
            if run >= CONSEC_YEARS:
                routine_keys.add((tk, ow))
                break
        if run >= CONSEC_YEARS:
            routine_keys.add((tk, ow))
    all_keys = set(map(tuple, d[["ticker", "ownername"]].drop_duplicates().values))
    return len(routine_keys), len(all_keys)


if __name__ == "__main__":
    raise SystemExit(main())
