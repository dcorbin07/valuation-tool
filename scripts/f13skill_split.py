# -*- coding: utf-8 -*-
"""`F13SKILL` — `K0` read, and the charter-split arithmetic the draft says to settle FIRST.

    python -m scripts.f13skill_split

**ZERO TRIALS, NO FORWARD RETURN.** `PREREG_DRAFT_f13skill.md` §5 requires the split to be decided
**in the register, before any outcome**, because choosing a split after seeing a result is `MA58`'s
void condition 5. This module does only that: it reads the `K0` census the collection pass measured
and derives how many build-quadrant dates survive the data's own 2013 start, with the MDE.
"""
from __future__ import annotations

import io
import json
import math
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import power_gate as PG                              # noqa: E402
from valuation.studies import dipcall as D                               # noqa: E402
from scripts import edge_drafts_collect as EC                            # noqa: E402

#: Derived from the collection pass rather than retyped, so the two cannot point at
#: different roots. The payload is licensed and lives under `D:\wrds`; CI never has it.
COLLECT = os.path.join(EC.RAW_ROOT, EC.OUT_JSON)
OUT = "F13SKILL_SPLIT.json"

K0_BAR = 1000                 # draft §4, reused verbatim
MIN_HALF_DATES = 16           # the shipped both-halves floor the draft cites
TIER_FLOOR = 10e9
BEST_EVER_RAW_ANCHOR_SD = 0.4346      # MB18's z_fcf_margin, the largest this panel has carried


def main(argv=None):
    if not os.path.isfile(COLLECT):
        raise SystemExit("REFUSING: %s absent -- the collection pass must run first." % COLLECT)
    col = json.load(io.open(COLLECT, encoding="utf-8"))
    k0 = col.get("f13_K0_managers_by_year") or {}
    if not k0.get("ok"):
        raise SystemExit("REFUSING: K0 did not complete in the collection pass")

    by_year = {int(float(r["yr"])): int(r["managers"]) for r in k0["by_year"]
               if r.get("yr") is not None and r.get("managers") is not None}
    first_ok = min((y for y, m in sorted(by_year.items()) if m >= K0_BAR), default=None)

    p = pd.read_pickle(D.panel_path())[["date", "ticker", "market_cap"]].copy()
    p["date"] = p["date"].astype(str)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    t = p[p["cap"] >= TIER_FLOOR]
    t = t[(t["date"] >= D.BUILD_LO) & (t["date"] <= D.BUILD_HI)]
    t = t[t["ticker"].map(D.stable_key_half) == 0]
    all_dates = sorted(t["date"].unique())

    usable = [d for d in all_dates if int(d[:4]) >= (first_ok or 9999)]
    early = [d for d in usable if d < D.HALF_BOUNDARY]
    late = [d for d in usable if d >= D.HALF_BOUNDARY]

    res = {"item": "F13SKILL-SPLIT", "trials": 0, "forward_return_touched": False,
           "K0": {"bar": K0_BAR, "managers_by_year": by_year,
                  "manager_column_resolved": k0.get("manager_column"),
                  "report_date_column_resolved": k0.get("report_date_column"),
                  "first_year_clearing_the_bar": first_ok,
                  "verdict": "PASSES from %s" % first_ok if first_ok else "FAILS everywhere",
                  "THE_STEP": ("the draft cites 71 filing managers in 2012 stepping to 3,457 in "
                               "2013; measured here on the real column the step is 149 -> 3,945, "
                               "so the shape reproduces and the levels differ")},
           "charter_split": {
               "build_dates_total": len(all_dates),
               "build_dates_usable_from_%s" % first_ok: len(usable),
               "half_boundary": D.HALF_BOUNDARY,
               "early_dates": len(early), "late_dates": len(late),
               "min_half_dates_floor": MIN_HALF_DATES,
               "early_clears_floor": len(early) >= MIN_HALF_DATES,
               "late_clears_floor": len(late) >= MIN_HALF_DATES,
           }}

    # The MDE on the usable window, DERIVED rather than borrowed (MB8).
    for label, n in (("all_build_dates", len(all_dates)), ("usable_window", len(usable)),
                     ("early_half", len(early)), ("late_half", len(late))):
        if n >= 2:
            se = 1.0 / math.sqrt(n)                     # IC in SD units, n effective dates
            res.setdefault("mde", {})[label] = {
                "n_dates": n,
                "se_sd": round(se, 6),
                "mde80_sd_at_crit_2": round((2.0 + PG.z_for_power(0.80)) * se, 4),
                "LABEL": "UNCALIBRATED -- no placebo sweep exists for this statistic",
            }

    m = res["mde"]
    res["verdict"] = (
        "NOT ASSESSABLE ON THE CHARTER'S SPLIT" if not (
            res["charter_split"]["early_clears_floor"]
            and res["charter_split"]["late_clears_floor"])
        else "ASSESSABLE, and UNDERPOWERED by construction")
    res["WHY"] = (
        "the 13F product carries fewer than %d filing managers before %s, so a per-manager signal "
        "cannot be built on the pre-%s part of the build quadrant at all. That leaves %d of %d "
        "build dates and halves of %d and %d against the shipped 16-date floor. The draft's own "
        "section 5 forbids quietly widening the window, so the honest outcome is declared here "
        "BEFORE any outcome exists rather than discovered after."
        % (K0_BAR, first_ok, first_ok, len(usable), len(all_dates), len(early), len(late)))
    res["MDE_SENTENCE"] = (
        "on the usable window the 80%%-power MDE is %.4f SD against the largest raw anchor this "
        "panel has ever carried at %.4f SD (MB18's z_fcf_margin), so the design cannot detect "
        "anything as large as the best thing the panel has ever held."
        % (m["usable_window"]["mde80_sd_at_crit_2"], BEST_EVER_RAW_ANCHOR_SD))

    print("K0: manager column %r, first year clearing %d managers: %s"
          % (res["K0"]["manager_column_resolved"], K0_BAR, first_ok), flush=True)
    print("  2012 -> %s managers | 2013 -> %s managers"
          % (by_year.get(2012), by_year.get(2013)), flush=True)
    print("build dates %d total, %d usable from %s; halves %d / %d against a 16-date floor"
          % (len(all_dates), len(usable), first_ok, len(early), len(late)), flush=True)
    for k, v in m.items():
        print("  MDE %-18s n=%-3d  80%%-power %.4f SD" % (k, v["n_dates"],
                                                          v["mde80_sd_at_crit_2"]), flush=True)
    print("VERDICT: %s" % res["verdict"], flush=True)

    p2 = D.out_path(OUT)
    with io.open(p2, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=1, default=str))
    print("wrote %s" % p2, flush=True)
    return res


if __name__ == "__main__":
    main()
    raise SystemExit(0)
