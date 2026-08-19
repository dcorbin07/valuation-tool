"""MB15 pass 3 - COVERAGE of the axis the literature's identifier actually lives on.

READ-ONLY. NO ARM, NO TRIALS, NO VERDICT, AND NO RETAIL SHARE COMPUTED.

Why this pass exists.  MB15 registers the VENUE axis on the premise that "the retail-flow
literature's identifier lives on exactly that axis".  It does not.  Bryzgalova-Pavlova-Sikorskaya
(J. Finance 2023) define their retail proxy on the OPRA trade CONDITION flags and on trade SIZE -
single-leg auction trades, or automatic executions of fewer than five contracts.  Both fields are
in this cache and neither has been read by any study.

Before routing a successor item at them, the COVERAGE RULE says measure whether they are
populated.  Five wired factors were silently empty for this project's entire history and nothing
surfaced it; a successor registered against a 0%-populated column would repeat that exactly.

WHAT THIS DELIBERATELY DOES NOT COMPUTE: the union `single-leg auction OR (auto-execution AND
size < 5)` - the retail share itself.  That statistic IS the successor register's gate, and
computing it here, after seeing the registered axis fail, would be choosing the design on the
outcome.  Marginal coverage of each field is a feasibility fact; their union is the hypothesis.
The separation is pinned by `tests/test_mb15_venue_axis.py`.

    python -m scripts.mb15_condition_census
"""
import io
import json
import os
from collections import Counter

import pandas as pd

from scripts.mb15_venue_census import DATA, ROOT

OUT = os.path.join(DATA, "free_analysis", "MB15_CONDITION_CENSUS.json")

# ThetaData's published trade-condition legend, read 2026-08-19 from
# http-docs.thetadata.us/Articles/Data-And-Requests/Values/Trade-Conditions.html
NAMES = {18: "AUTO_EXECUTION", 35: "SPREAD", 36: "STRADDLE", 37: "BUY_WRITE", 38: "COMBO",
         45: "MATCH_CROSS", 125: "SINGLE_LEG_AUCTION_NON_ISO", 126: "SINGLE_LEG_AUCTION_ISO",
         127: "SINGLE_LEG_CROSS_NON_ISO", 128: "SINGLE_LEG_CROSS_ISO",
         129: "SINGLE_LEG_FLOOR_TRADE", 130: "MULTI_LEG_AUTOELEC_TRADE", 131: "MULTI_LEG_AUCTION",
         132: "MULTI_LEG_CROSS", 133: "MULTI_LEG_FLOOR_TRADE", 134: "ML_AUTO_ELEC_TRADE_AGSL",
         135: "STOCK_OPTIONS_AUCTION", 136: "ML_AUCTION_AGSL", 138: "STK_OPT_AUTO_ELEC_TRADE",
         142: "STK_OPT_AUCTION_AGSL"}
AUCTION = (125, 126, 131, 135, 136, 142)


def main():
    cond = Counter()
    cond_by_year = {}
    size_buckets = Counter()
    ext_nondefault = Counter()
    prints = units = 0

    syms = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
    print("[MB15c] %d symbol directories" % len(syms), flush=True)

    for si, sym in enumerate(syms):
        sd = os.path.join(ROOT, sym)
        for f in sorted(os.listdir(sd)):
            if not f.endswith(".pkl"):
                continue
            obj = pd.read_pickle(os.path.join(sd, f))
            r = obj["rows"]
            units += 1
            prints += len(r)
            vc = r["condition"].value_counts().to_dict()
            cond.update(vc)
            cond_by_year.setdefault(str(obj.get("date"))[:4], Counter()).update(vc)
            sz = r["size"]
            size_buckets["eq1"] += int((sz == 1).sum())
            size_buckets["lt5"] += int((sz < 5).sum())
            size_buckets["ge5"] += int((sz >= 5).sum())
            for c in ("ext_condition1", "ext_condition2", "ext_condition3", "ext_condition4"):
                ext_nondefault[c] += int((r[c] != 255).sum())
        if si % 25 == 0:
            print("[MB15c]   %d/%d symbols, %s prints"
                  % (si, len(syms), "{:,}".format(prints)), flush=True)

    tot = sum(cond.values())
    shares = {int(k): v / tot for k, v in sorted(cond.items(), key=lambda kv: -kv[1])}

    out = {
        "item": "MB15",
        "pass": "condition-size-coverage",
        "status": "READ-ONLY COVERAGE FACTS - no arm, no trials, no verdict, NO retail share",
        "deliberately_not_computed": "the union 'single-leg auction OR (auto-execution AND "
                                     "size<5)' - that union is the successor register's gate and "
                                     "computing it here would be choosing the design after the "
                                     "outcome",
        "units": units, "prints": prints,
        "condition_codes_observed": len(cond),
        "condition_shares": shares,
        "condition_names_from_vendor_legend": {str(k): v for k, v in NAMES.items()},
        "auction_condition_counts": {str(c): cond.get(c, 0) for c in AUCTION},
        "any_single_leg_auction_present": bool(cond.get(125, 0) + cond.get(126, 0)),
        "size_marginals": {k: {"prints": v, "share": v / prints} for k, v in size_buckets.items()},
        "ext_condition_nondefault_counts": dict(ext_nondefault),
        "condition_shares_by_year": {y: {int(k): v / max(1, sum(c.values()))
                                         for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:8]}
                                     for y, c in sorted(cond_by_year.items())},
    }
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print()
    print("[MB15c] prints %s over %s units" % ("{:,}".format(prints), "{:,}".format(units)))
    print("[MB15c] distinct condition codes: %d" % len(cond))
    for k, v in list(shares.items())[:18]:
        print("        %3d %-28s %8.4f%%  %s"
              % (k, NAMES.get(k, "?UNKNOWN"), 100 * v, "{:,}".format(cond[k])))
    print()
    print("[MB15c] AUCTION codes:")
    for c in AUCTION:
        print("        %3d %-28s %s" % (c, NAMES.get(c, "?"), "{:,}".format(cond.get(c, 0))))
    print()
    for k, v in size_buckets.items():
        print("[MB15c] size %-4s %8.4f%%" % (k, 100 * v / prints))
    print("[MB15c] wrote %s" % OUT)


if __name__ == "__main__":
    main()
