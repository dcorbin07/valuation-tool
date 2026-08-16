#!/usr/bin/env python3
"""u6_overwrite_coverage.py — U6's blocker, measured against the leg it actually applies to.

ZERO TRIALS. No hypothesis, no threshold, no verdict against a bar — this is a fact about what
is on disk and about which set a published number was computed over. It is the `S25`/`PT-WRITER`
class of item, and it is a CORRECTION to the ledger rather than a retest of U6.

--------------------------------------------------------------------------------------------
WHAT THE ROW SAYS, AND WHY IT IS THE WRONG DENOMINATOR TWICE.

`VALQUO_LEDGER.md` closes U6 `DESIGN-RECORDED / NOT BUILDABLE ON DATA WE OWN` on one measured
number, quoted from the row itself:

    "of 7,132 names ENTERING the top decile across 68 transitions only 129 have mined chains
     = 1.81%, and of 7,095 LEAVING only 128 = 1.80% ... a MEDIAN OF 2 covered names in a book
     whose mean top-decile size is 165.6, with ZERO covered entries on 18 of 68 dates"

That number is correct for what it measures and it is measured over the wrong set, in two
independent ways:

  1. TRANSITIONS, NOT HOLDINGS. U6 is a TWO-LEG proposal — cash-secured puts on the entry leg,
     covered calls on the exit leg. An overwrite is written on what you HOLD, not on what
     changes hands. Entries and exits are both transitions; membership is a different and
     larger set.
  2. THE 187-NAME ALERT UNIVERSE, NOT THE CHAIN CACHE. The row says "against the 187-name mined
     universe" — the universe the OPTIONS ALERT book was built from. The chain cache holds
     1,000 ticker directories, 906 of them names in the equity panel. That is a ~4.8x larger
     denominator, and it is the one a covered-call replay would actually draw on.

Neither correction touches the CSP entry leg, which remains genuinely coverage-bound. So this
does not overturn U6; it establishes that the row currently reads as though BOTH legs are dead
and one of them is not.

--------------------------------------------------------------------------------------------
IT USES THE SHIPPED DECILE CONVENTION. Membership comes from `argsort(-composite)` split into
ten buckets — the same construction `quantile_backtest` uses — so "top decile" here is the same
object every published top-decile figure describes, not a re-derivation that happens to agree.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
PANEL = os.path.join(DATA, "free_analysis", "panel_s22_h504.pkl")
PART = os.path.join(DATA, "free_analysis", "P1S0_OPTIONABLE_PARTITION.pkl")
OUT = os.path.join(DATA, "free_analysis", "U6_OVERWRITE_COVERAGE.json")


def main():
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    from scripts.term_structure import DEPLOYED

    panel = pd.read_pickle(PANEL)
    panel["date"] = pd.to_datetime(panel["date"])
    part = pd.read_pickle(PART)
    part["date"] = pd.to_datetime(part["date"])

    liquid = {}
    anychain = {}
    for d, g in part.groupby("date"):
        anychain[d] = set(g["ticker"])
        liquid[d] = set(g.loc[g["pit_liquid"] == True, "ticker"])          # noqa: E712

    dates = sorted(panel["date"].unique())
    rows, prev = [], None
    for d in dates:
        sub = panel[panel["date"] == d]
        comp = composite_from_frame(sub, list(DEPLOYED), DEPLOYED, zscore)
        base = pd.to_numeric(sub["fwd_ret"], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(base)
        if int(ok.sum()) < 30:
            prev = None
            continue
        tick = sub["ticker"].to_numpy()[ok]
        order = np.argsort(-comp[ok])
        members = set(tick[np.array_split(order, 10)[0]])
        ent = (members - prev) if prev is not None else None
        lv = (prev - members) if prev is not None else None
        lq, ac = liquid.get(d, set()), anychain.get(d, set())
        rec = {"date": str(d)[:10], "covered_date": bool(ac),
               "decile_size": len(members),
               "hold_liquid": len(members & lq), "hold_any": len(members & ac),
               "entries": (None if ent is None else len(ent)),
               "entry_liquid": (None if ent is None else len(ent & lq)),
               "entry_any": (None if ent is None else len(ent & ac))}
        rows.append(rec)
        prev = members

    cov = [r for r in rows if r["covered_date"]]

    def med(key, src=cov):
        v = [r[key] for r in src if r.get(key) is not None]
        return float(np.median(v)) if v else None

    def tot(key, src=cov):
        return int(sum(r[key] for r in src if r.get(key) is not None))

    hold_share = (tot("hold_liquid") / tot("decile_size")) if tot("decile_size") else None
    hold_share_any = (tot("hold_any") / tot("decile_size")) if tot("decile_size") else None
    ent_tot = tot("entries")
    ent_share = (tot("entry_liquid") / ent_tot) if ent_tot else None
    ent_share_any = (tot("entry_any") / ent_tot) if ent_tot else None

    out = {
        "what_this_is": "ZERO TRIALS. A coverage correction to the U6 ledger row, not a retest.",
        "ledger_claim": {"entries_with_chains": 129, "entries_total": 7132, "share": 0.0181,
                         "measured_against": "the 187-name ALERT universe",
                         "dates_with_zero_covered_entries": 18},
        "scope": {"panel_dates": len(dates), "covered_dates": len(cov),
                  "uncovered_dates": len(dates) - len(cov),
                  "chain_cache_ticker_dirs": 1000,
                  "chain_cache_names_in_panel": 906},
        "on_covered_dates": {
            "median_decile_size": med("decile_size"),
            "median_holdings_pit_liquid": med("hold_liquid"),
            "median_holdings_any_chain": med("hold_any"),
            "share_of_decile_slots_pit_liquid": (round(hold_share, 4) if hold_share else None),
            "share_of_decile_slots_any_chain": (round(hold_share_any, 4) if hold_share_any else None),
            "median_entries": med("entries"),
            "median_entries_pit_liquid": med("entry_liquid"),
            "median_entries_any_chain": med("entry_any"),
            "share_of_entries_pit_liquid": (round(ent_share, 4) if ent_share else None),
            "share_of_entries_any_chain": (round(ent_share_any, 4) if ent_share_any else None),
            "covered_dates_with_zero_liquid_holdings":
                int(sum(1 for r in cov if r["hold_liquid"] == 0)),
            "covered_dates_with_zero_any_holdings":
                int(sum(1 for r in cov if r["hold_any"] == 0)),
        },
        # LIKE-FOR-LIKE WITH THE LEDGER. Its 1.81% is entries over ALL transitions, uncovered
        # dates included (they contribute entries and zero coverage). Recomputed on that exact
        # denominator, the only thing changed is the UNIVERSE: the full chain cache instead of
        # the 187-name alert universe.
        "all_dates_like_for_like": {
            "entries_total": tot("entries", rows),
            "entries_pit_liquid": tot("entry_liquid", rows),
            "entries_any_chain": tot("entry_any", rows),
            "share_pit_liquid": (round(tot("entry_liquid", rows) / tot("entries", rows), 4)
                                 if tot("entries", rows) else None),
            "share_any_chain": (round(tot("entry_any", rows) / tot("entries", rows), 4)
                                if tot("entries", rows) else None),
            "holdings_total": tot("decile_size", rows),
            "holdings_pit_liquid": tot("hold_liquid", rows),
            "holdings_any_chain": tot("hold_any", rows),
            "holdings_share_any_chain": (round(tot("hold_any", rows) / tot("decile_size", rows), 4)
                                         if tot("decile_size", rows) else None),
            "dates_with_zero_covered_entries":
                int(sum(1 for r in rows if r.get("entry_any") == 0)),
        },
        "per_date": rows,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "per_date"}, indent=2))
    print("\n[u6] wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
