# -*- coding: utf-8 -*-
"""MC9 (AUDIT 6) — build the SEP $ADV / OHLC instrument and census it. ZERO TRIALS.

`MB15` ORDERING IS STRUCTURAL HERE, NOT PROMISED: nothing in this file ranks, filters or scores.
No forward return is loaded, `MIN_AVG_DOLLAR_VOLUME` is never read, and the B13 arm is not run.
Pinned by `tests/test_mc9_adv_sep.py`.

Steps, in the brief's order: verify the export -> build the instrument -> census coverage on the
PANEL's own cells -> `B7` fidelity against the two existing ADV series.
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import adv_sep as A                                # noqa: E402

#: The PRIMARY root. A worktree carries `data/` empty, and a bare resolve there would report the
#: 3.2 GB export as absent -- which is the exact defect this item is correcting.
_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
DATA = os.path.join(_ROOT, "data")
FA = os.path.join(DATA, "free_analysis")
PANEL = os.path.join(FA, "panel_corrected_69d.pkl")
OHLCV = os.path.join(DATA, A.OHLCV_DIRNAME)
CACHE = os.path.join(FA, "MC9_SEP_ADV.pkl")
OUT = os.path.join(FA, "MC9_SEP_INSTRUMENT.json")

#: The five rebalance dates after CRSP's 2024-12-31 cut -- the window a CRSP ADV cannot reach
#: and the one the paper track lives in.
POST_CRSP_DATES = ("2025-01-27", "2025-04-28", "2025-07-29", "2025-10-27", "2026-01-28")

#: The halves boundary the brief names.
HALVES_BOUNDARY = "2017-01-19"

#: Split-consistency subjects, with an unsplit control. Named in the brief.
SPLIT_NAMES = ("CMG", "AAPL", "WMT", "MSTR", "SIRI")
SPLIT_CONTROL = "JPM"


def build(tickers):
    if os.path.exists(CACHE):
        print("  [cache] %s" % CACHE, flush=True)
        d = pd.read_pickle(CACHE)
        return d["by_ticker"], d["census"]
    p = A.sep_path(DATA)
    hdr = A.assert_header(p)
    print("  header verified: %s" % (",".join(hdr)), flush=True)
    print("  streaming %.2f GB ..." % (os.path.getsize(p) / 1e9), flush=True)
    t0 = time.time()
    written = {"n": 0}

    def sink(t, rows):
        A.write_ohlcv(OHLCV, t, rows)
        written["n"] += 1

    res = A.scan(p, tickers, on_ticker=sink)
    print("  scanned in %.1f min; %d sidecars written to %s"
          % ((time.time() - t0) / 60.0, written["n"], OHLCV), flush=True)
    pd.to_pickle(res, CACHE)
    return res["by_ticker"], res["census"]


def _split_check(by_ticker):
    """Is `close * volume` split-consistent? Measured against `closeunadj`.

    The test is the RATIO `closeunadj / close` -- the split factor accumulated to date -- and
    whether dollar volume computed the two ways agrees. It cannot, unless volume is adjusted on
    the same basis as `close`; the point is to show WHICH basis, on names that split hard.
    """
    out = {}
    for t in SPLIT_NAMES + (SPLIT_CONTROL,):
        rows = by_ticker.get(t)
        if not rows:
            out[t] = {"note": "absent from the export"}
            continue
        d = pd.DataFrame(rows, columns=["date", "o", "h", "l", "close", "volume", "closeunadj"])
        f = d["closeunadj"] / d["close"]
        out[t] = {
            "rows": int(len(d)),
            "split_factor_min": float(f.min()), "split_factor_max": float(f.max()),
            "ever_split": bool(f.max() / max(f.min(), 1e-12) > 1.01),
            "dv_adjusted_median": float((d["close"] * d["volume"]).median()),
            "dv_unadjusted_median": float((d["closeunadj"] * d["volume"]).median()),
        }
    return out


def main() -> int:
    panel = pd.read_pickle(PANEL)
    panel["_d"] = panel["date"].astype(str).str[:10]
    panel["_t"] = panel["ticker"].astype(str).str.upper()
    tickers = sorted(panel["_t"].unique())
    dates = sorted(panel["_d"].unique())
    cells = list(zip(panel["_t"], panel["_d"]))

    by_ticker, census = build(tickers)
    rep = {"item": "MC9", "trials": 0,
           "sep_bytes": os.path.getsize(A.sep_path(DATA)),
           "sep_header": list(A.SEP_HEADER),
           "scan_census": census,
           "panel": {"cells": len(cells), "tickers": len(tickers), "dates": len(dates)}}

    rep["split_consistency"] = _split_check(by_ticker)

    ser = A.adv_series(by_ticker)
    idx = A.by_cell(ser)
    sessions_by_t = {t: [r[0] for r in rows] for t, rows in by_ticker.items()}

    # ---- 3. COVERAGE CENSUS ON THE PANEL'S OWN CELLS, before any fidelity comparison
    have = {}
    for t, d0 in cells:
        v = A.pit_adv_at(idx, t, d0, sessions_by_t.get(t, ()))
        if v is not None:
            have[(t, d0)] = v
    per_date = {}
    for d0 in dates:
        sub = [1 for (t, dd) in cells if dd == d0 and (t, dd) in have]
        tot = sum(1 for (_t, dd) in cells if dd == d0)
        per_date[d0] = (len(sub), tot, len(sub) / tot if tot else None)
    fr = [v[2] for v in per_date.values() if v[2] is not None]
    rep["coverage"] = {
        "cells_with_pit_adv": len(have), "cells": len(cells),
        "frac": len(have) / len(cells) if cells else None,
        "per_date_min": float(np.min(fr)), "per_date_median": float(np.median(fr)),
        "per_date_max": float(np.max(fr)),
        "dates_with_at_least_20_covered": int(sum(1 for v in per_date.values() if v[0] >= 20)),
        "dates": len(dates),
        "post_crsp_dates": {d: per_date.get(d) for d in POST_CRSP_DATES},
        "halves_boundary": HALVES_BOUNDARY,
        "early_half_frac": float(np.mean([v[2] for d, v in per_date.items()
                                          if d < HALVES_BOUNDARY and v[2] is not None])),
        "late_half_frac": float(np.mean([v[2] for d, v in per_date.items()
                                         if d >= HALVES_BOUNDARY and v[2] is not None])),
        "null_volume_share_of_kept": (census["nonpositive_volume_rows"] /
                                      max(1, census["nonpositive_volume_rows"]
                                          + census["rows_kept"])),
    }
    rep["per_date_coverage"] = {d: {"covered": v[0], "cells": v[1], "frac": v[2]}
                                for d, v in per_date.items()}

    json.dump(rep, open(OUT, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_date_coverage"},
                     indent=1, default=str))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
