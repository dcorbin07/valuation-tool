# -*- coding: utf-8 -*-
"""`C4`'s five-year coverage, measured from the UNTRUNCATED market-cap source.

**THE KILL FIRED FIRST AND IS ON THE RECORD AT 0.6094.** `B3_KILLS.json` carries it. This file
exists because chasing that number down showed it is partly a property of MY FRAME rather than of
the data, and the rule for what happens next is fixed HERE, before the measurement runs.

**THE DEFECT.** `C4` needs a market cap five years prior. My implementation read it from the
PANEL, and the corrected panel's grid starts **2009-03-27** — so for the 24 early-half dates of
the build quadrant no five-year base exists *in the frame*, whatever the data says. That is the
same class as this lane's own `_ttm` unsorted-history defect, where 12 failing dates turned out to
be **entirely artefactual**.

**WHY RE-SOURCING IS A REPAIR AND NOT A DESIGN CHANGE, and the argument is outcome-independent:**
the panel's own `market_cap` column **is built from the DAILY bulk cache**
(`cleanups.pit_market_cap_from_daily`), and `daily_history` carries month-end market caps from
**1997**. So a five-year-prior market cap from DAILY is **the same quantity from the same source**,
merely not truncated to the panel's date grid. The panel's start date is a property of the panel,
not of the arm. That sentence would be equally true if the coverage came out at 0.95 or at 0.40.

**THE RULE, PRE-COMMITTED HERE, BEFORE THE NUMBER EXISTS:**

1. **BOTH figures ship** — the panel-sourced 0.6094 and whatever this measures. Reporting only the
   kinder one is the thing this file exists not to do.
2. **The 0.70 bar DOES NOT MOVE** (`W-28`: a pre-committed bar may not be relaxed after watching
   it fail, and may not be tightened after watching it pass).
3. **If the untruncated figure is below 0.70, `C4` STAYS `NOT RUN`** and the artefact is recorded
   as a note on why its first reading was lower, not as grounds for a second attempt.
4. **If it is at or above 0.70, `C4` is scored** — and the write-up states plainly that the kill
   fired on the first implementation and that the correction was prompted by it.
5. **NO OTHER ARM IS RE-SOURCED.** `C1`'s 0.5488 reads the FULL fundamentals history (1980-2026)
   through `fundamentals_history`, so it is **not** frame-truncated and no analogous correction
   exists for it. Applying a repair only to the arm one would like to rescue is the failure this
   clause forbids.
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

from scripts.stage1_kills import build_quadrant                            # noqa: E402
from scripts.b3_kills import TIER_FLOOR_USD, COVERAGE_FLOOR                # noqa: E402

PANEL = r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/UNIVERSE_BIAS_PANEL_full_v3.pkl"
EXPORT = r"C:/Users/donni/Downloads/valuation-tool/data/full2009/backtest"
BULK = r"C:/Users/donni/Downloads/valuation-tool/data/bulk/prepared"
OUT = r"C:/Users/donni/Downloads/valuation-tool/data/free_analysis/B3_C4_SOURCE.json"

PANEL_SOURCED_COVERAGE = 0.6094          # from B3_KILLS.json, the figure already on the record


def main():
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = EXPORT

    prov = WRDSProvider(_C())
    prov._bulk_dir = BULK                 # the SAME cache the panel's market_cap came from
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready: %s" % msg)

    panel = pd.read_pickle(PANEL)
    quad, qcen = build_quadrant(panel)
    mc = pd.to_numeric(quad["market_cap"], errors="coerce")
    tier = quad[mc >= TIER_FLOOR_USD].copy()
    tier["_d"] = tier["date"].astype(str).str[:10]
    print("tier rows in the build quadrant: %d over %d dates"
          % (len(tier), tier["_d"].nunique()), flush=True)

    # month-end market-cap history per ticker, from DAILY
    hist = {}
    for t in sorted(set(tier["ticker"].astype(str))):
        rows = prov.daily_history(t) or []
        hist[t] = [(str(r[0])[:10], r[1]) for r in rows if r and r[1] is not None]

    spans = {t: (v[0][0], v[-1][0]) for t, v in hist.items() if v}
    earliest = min((v[0] for v in spans.values()), default=None)
    print("DAILY histories: %d tickers, earliest month-end %s" % (len(spans), earliest),
          flush=True)

    def mcap_at_or_before(t, when):
        v = hist.get(t) or []
        out = None
        for d, m in v:                     # ascending
            if d <= when:
                out = m
            else:
                break
        return out

    have = 0
    per_date = {}
    for d, g in tier.groupby("_d"):
        want = "%04d%s" % (int(d[:4]) - 5, d[4:])
        n = h = 0
        for t in g["ticker"].astype(str):
            n += 1
            if mcap_at_or_before(t, want) is not None:
                h += 1
                have += 1
        per_date[d] = (h / float(n)) if n else None

    cov = have / float(len(tier)) if len(tier) else None
    vals = [v for v in per_date.values() if v is not None]
    res = {
        "item": "STAGE1-BATCH3", "part": "C4's five-year coverage from the untruncated source",
        "trials": 0,
        "trial_class": "CONTROL -- a coverage census can only BLOCK an arm, never produce a "
                       "finding (MB1-SEL).",
        "the_kill_fired_first": True,
        "panel_sourced_coverage": PANEL_SOURCED_COVERAGE,
        "panel_grid_starts": qcen["first"],
        "why_the_panel_figure_was_low": "the corrected panel's grid starts %s, so no five-year "
                                        "base exists IN THE FRAME for the 24 early-half dates, "
                                        "whatever the data says" % qcen["first"],
        "untruncated_source": "WRDSProvider.daily_history (the DAILY bulk cache, the SAME source "
                              "the panel's own market_cap column is built from)",
        "daily_earliest_month_end": earliest,
        "tier_rows": int(len(tier)),
        "tier_rows_with_a_five_year_base": int(have),
        "cell_coverage": cov,
        "per_date_min": (float(np.min(vals)) if vals else None),
        "per_date_median": (float(np.median(vals)) if vals else None),
        "n_dates": len(vals),
        "floor": COVERAGE_FLOOR,
        "floor_did_not_move": True,
        "count_gate_passes": bool(len(tier) > 0),     # MB21
    }
    res["clears_the_floor"] = bool(cov is not None and cov >= COVERAGE_FLOOR)
    res["verdict"] = ("C4 IS SCOREABLE -- the first reading was a frame artefact"
                      if res["clears_the_floor"] else
                      "C4 STAYS NOT RUN -- the untruncated figure also misses the floor")

    io.open(OUT, "w", encoding="utf-8").write(json.dumps(res, indent=1, default=str))
    print()
    print("panel-sourced  : %.4f  (on the record, unchanged)" % PANEL_SOURCED_COVERAGE)
    print("untruncated    : %s" % (("%.4f" % cov) if cov is not None else "n/a"))
    print("floor          : %.2f  (UNMOVED)" % COVERAGE_FLOOR)
    print("per-date min/median: %s / %s" % (res["per_date_min"], res["per_date_median"]))
    print("VERDICT: %s" % res["verdict"])
    print("-> %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
