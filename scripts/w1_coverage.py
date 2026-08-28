# -*- coding: utf-8 -*-
"""W-1 — DATED sector-map coverage on THE ARM'S OWN POPULATION, measured BEFORE any bar is set.

`W-28`'s closing sentence is the reason this file exists and runs first: *a pre-committed bar the
account structurally cannot clear is a register that can only ever void.* `W-28`'s K1 died on
exactly that -- a 90% dated-linkage bar that no dated route on this account can reach. So W-1
measures its instrument's reach FIRST and sets its bar afterwards, with the distribution in view.

**AND THE POPULATION MATTERS, WHICH IS `O-1`'s LESSON AND THIS RECORD ALREADY FLAGS IT FOR `S25`
SPECIFICALLY.** `S25` published **94.8%** coverage measured on the **S23 VALUATION panel**
(2,441 tickers), and the WRDS census published **94.9%** measured on the **2,531-name METRICS
panel** -- *"two nearly-equal percentages on different objects"*, in `CLAUDE.md`'s own words. The
sector-neutral arm re-ranks the **METRICS** panel, so neither figure may be inherited and coverage
is re-measured here on the 113,945 cells the arm actually scores.

`TAXONOMY_REVISIONS` are honoured rather than counted as reclassifications: GICS separated Real
Estate in 2016 and Communication Services in 2018, and those are **provider paperwork, not company
events**. The instrument flags them; this pass reports them as their own line.

**ZERO TRIALS. No outcome statistic** -- nothing here relates a sector to a forward return.
"""
from __future__ import annotations

import collections
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import sector_map as SM                   # noqa: E402

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
PANEL = os.path.join(_ROOT, "data", "free_analysis", "panel_corrected_69d.pkl")
OUT = os.path.join(_ROOT, "data", "free_analysis", "W1_COVERAGE.json")


def main() -> int:
    if not os.path.isfile(PANEL):
        raise FileNotFoundError(
            "%s is absent -- the corrected panel is never mirrored into a worktree. "
            "`DEEPITM-FIN` shipped a clean, plausible null from a directory that merely "
            "existed; refusing to report coverage from no rows." % PANEL)
    p = pd.read_pickle(PANEL)
    if not isinstance(p["date"].iloc[0], str):
        raise RuntimeError("panel dates must be STRINGS; a Timestamp filter matches zero rows")

    smap = SM.load()
    print("[w1] sector map loaded from %s" % SM.default_path())
    print("[w1] panel: %d cells, %d names, %d dates"
          % (len(p), p["ticker"].nunique(), p["date"].nunique()))

    states = collections.Counter()
    per_date_ok = collections.Counter()
    per_date_n = collections.Counter()
    names_ok = set()
    agree = disagree = both_known = 0
    rows = []
    for tk, d0, cur in zip(p["ticker"].astype(str).str.upper(), p["date"].astype(str),
                           p.get("sector", pd.Series([None] * len(p)))):
        r = smap.at(tk, d0)
        st = r["state"]
        states[st] += 1
        per_date_n[d0] += 1
        if st == "OK":
            per_date_ok[d0] += 1
            names_ok.add(tk)
            if isinstance(cur, str) and cur:
                both_known += 1
                if r["sector"] == cur:
                    agree += 1
                else:
                    disagree += 1
        rows.append(st)

    n = len(p)
    ok = states["OK"]
    fr = {d: per_date_ok[d] / per_date_n[d] for d in per_date_n}
    vals = sorted(fr.values())
    out = {
        "item": "W-1", "trials": 0,
        "population": "the 113,945-cell METRICS panel the sector-neutral arm re-ranks",
        "population_note": ("NOT S25's 94.8% (measured on the S23 VALUATION panel, 2,441 tickers) "
                            "and NOT the census's 94.9% (2,531-name metrics panel, ticker->gvkey "
                            "coverage, a different quantity). O-1's lesson, and CLAUDE.md already "
                            "flags these as two nearly-equal percentages on different objects."),
        "cells": n, "cells_OK": ok, "frac_cells_OK": ok / n,
        "states": dict(states),
        "names_OK": len(names_ok), "panel_names": int(p["ticker"].nunique()),
        "frac_names_OK": len(names_ok) / int(p["ticker"].nunique()),
        "per_date_min": vals[0], "per_date_p05": vals[max(0, len(vals) // 20)],
        "per_date_median": vals[len(vals) // 2], "per_date_max": vals[-1],
        "dates": len(vals),
        "taxonomy_disagreement_with_today": {
            "both_known": both_known, "agree": agree, "disagree": disagree,
            "frac_disagree": (disagree / both_known) if both_known else None,
            "note": ("the PIT sector against the panel's own TODAY sector. This is the cost S25 "
                     "measured at the NAME level (11.37%); here it is measured per CELL on the "
                     "arm's own population, which is the quantity a re-ranking actually pays.")},
        "taxonomy_revisions_flagged": [list(t) for t in SM.TAXONOMY_REVISIONS],
        "taxonomy_revisions_note": ("Real Estate 2016 and Communication Services 2018 are PROVIDER "
                                    "PAPERWORK, not company reclassification events. The "
                                    "instrument flags them and this pass does not count them as "
                                    "evidence of a name changing sector."),
    }
    print("\n=== COVERAGE ON THE ARM'S OWN POPULATION ===")
    print("  cells OK          : %d of %d = %.4f" % (ok, n, ok / n))
    print("  states            : %s" % dict(states))
    print("  names OK          : %d of %d = %.4f"
          % (len(names_ok), p["ticker"].nunique(), out["frac_names_OK"]))
    print("  per-date OK       : min %.4f | p05 %.4f | median %.4f | max %.4f"
          % (out["per_date_min"], out["per_date_p05"], out["per_date_median"],
             out["per_date_max"]))
    print("  PIT vs TODAY      : %d of %d cells disagree = %.4f"
          % (disagree, both_known, out["taxonomy_disagreement_with_today"]["frac_disagree"] or 0))
    json.dump(out, open(OUT, "w"), indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
