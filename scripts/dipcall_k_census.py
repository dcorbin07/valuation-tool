"""DIP-CALL — IS THE NEWS ARM REACHABLE AT ALL? A FEASIBILITY CENSUS. ZERO TRIALS.

`K1` fired at the registered primary k = 2.5: the two NO-NEWS tier arms clear the 1,500 floor
(2,326 / 4,004) and the two NEWS arms cannot (614 / 1,049), because only 1,669 news events exist
on the whole point-in-time $10B tier. **The program stopped there** and `PREREG_dipcall.md` §2g
forbids relaxing the floor after watching it fail (`W-28`).

THIS FILE DOES NOT RE-OPEN THAT. It answers a different and narrower question, for a successor:
**at what event threshold, if any, does the NEWS arm reach the floor?** That is a fact about what
data exists -- the `S25` / `MB15` / `MB3` / `W-14` census class, every one logged at ZERO trials --
and it touches **no forward return**: the event-day return DEFINES the event and nothing after the
event day is loaded anywhere in this file.

WHY IT IS NOT k-SHOPPING, STATED PLAINLY BECAUSE THE SHAPE INVITES THE SUSPICION. A successor
register would have to commit its k BEFORE running, carry its own BH burden, and inherit this
program's priors -- and the honest finding this census produces is mostly a NEGATIVE one, because
a lower k buys events by making the event SMALLER, and §2a's whole argument is that the event must
be a shock. The census reports the median event-day move at each k so that trade is visible rather
than implied. **Nothing here is a verdict and nothing here advances the program.**

Usage:  python -m scripts.dipcall_k_census
"""
import collections
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge.event_spine import EventSpine                             # noqa: E402
from valuation.studies import dipcall as D                                    # noqa: E402

ART = "DIPCALL_K_CENSUS.json"
KS = (1.5, 2.0, 2.5, 3.0)


def main():
    sched = D.tier_schedule()
    panel = pd.read_pickle(D.panel_path())
    panel["date"] = panel["date"].astype(str)
    panel["ticker"] = panel["ticker"].astype(str)
    bq = panel[(panel["date"] >= "2009") & (panel["date"] <= D.BUILD_HI)]
    half0 = sorted(set(bq[bq["ticker"].map(D.stable_key_half) == 0]["ticker"]))

    print("DIP-CALL k-census. ZERO TRIALS. No forward return is read anywhere in this file.")
    print("One pass over the price files; every k is a threshold on the SAME z.\n")

    # One pass, keeping z, so every k is a threshold on one object rather than a rebuild.
    rows = []
    t0 = time.time()
    for i, t in enumerate(half0):
        f = D.name_frame(t, sched.get(t, []), k=min(KS))
        if f is None:
            continue
        b = f[(f["date"] >= D.BUILD_LO) & (f["date"] <= D.BUILD_HI) & f["scoreable"] & f["tier"]]
        if len(b):
            rows.append(b[["date", "ticker", "session_idx", "z", "ret"]])
        if i and i % 800 == 0:
            print("  %d/%d names, %.0fs" % (i, len(half0), time.time() - t0))
    d = pd.concat(rows, ignore_index=True)
    d["ticker"] = d["ticker"].astype(str)
    print("  %s scoreable TIER name-days over %d sessions, %d names\n"
          % ("{:,}".format(len(d)), d["date"].nunique(), d["ticker"].nunique()))

    names = sorted(set(d["ticker"]))
    spine = EventSpine.build(names=names, csv_path=D.events_csv())
    ann = {}
    for t in names:
        sub = d[d["ticker"] == t]
        d2i = dict(zip(sub["date"].tolist(), sub["session_idx"].tolist()))
        ann[t] = D.announce_sessions(spine, t, d2i)

    cls = [D.news_class(spine, t, si, ann.get(t))
           for t, si in zip(d["ticker"].tolist(), d["session_idx"].tolist())]
    d["news"] = cls
    d["half"] = [D.half_of(x) for x in d["date"].tolist()]

    out = {}
    print("%-5s %9s %9s %9s %9s %9s %9s %11s"
          % ("k", "news-ear", "news-late", "nn-ear", "nn-late", "unknown", "events",
             "med move pp"))
    for k in KS:
        e = d[d["z"] <= -k]
        cell = {}
        for arm in (D.NEWS, D.NO_NEWS):
            for half in ("early", "late"):
                cell["%s|%s" % (arm, half)] = int(
                    ((e["news"] == arm) & (e["half"] == half)).sum())
        med = float(np.median(e["ret"].to_numpy(dtype=float)) * 100.0) if len(e) else None
        news_min = min(cell["%s|%s" % (D.NEWS, h)] for h in ("early", "late"))
        nn_min = min(cell["%s|%s" % (D.NO_NEWS, h)] for h in ("early", "late"))
        out["%.1f" % k] = {
            "events_tier": int(len(e)),
            "cells": cell,
            "unknown": int((e["news"] == D.UNKNOWN).sum()),
            "median_event_day_move_pp": med,
            "news_arm_min_cell": news_min,
            "no_news_arm_min_cell": nn_min,
            "news_arm_reaches_1500_floor": bool(news_min >= D.MIN_EVENTS_PER_CELL),
            "no_news_arm_reaches_1500_floor": bool(nn_min >= D.MIN_EVENTS_PER_CELL),
        }
        print("%-5.1f %9d %9d %9d %9d %9d %9d %11.3f"
              % (k, cell["%s|early" % D.NEWS], cell["%s|late" % D.NEWS],
                 cell["%s|early" % D.NO_NEWS], cell["%s|late" % D.NO_NEWS],
                 out["%.1f" % k]["unknown"], len(e), med))

    # The structural ceiling: news sessions are a FIXED ~3% of sessions, so the news arm's size is
    # bounded by the tier's own session count whatever k is chosen. At k -> 0 every news session
    # becomes an "event", which is the arm's absolute maximum and is not a dip study at all.
    news_sessions = int((d["news"] == D.NEWS).sum())
    ceiling = {
        "scoreable_tier_name_days": int(len(d)),
        "news_classified_tier_name_days": news_sessions,
        "news_session_share": round(news_sessions / len(d), 6),
        "absolute_ceiling_per_half_at_k_zero": int(news_sessions / 2),
        "note": ("the news arm's size is bounded by how many TIER name-days are earnings "
                 "reactions at all. Lowering k buys events only by making the event smaller, and "
                 "at k -> 0 the 'event' is simply every earnings reaction, which is not a dip "
                 "study. The median event-day move column is what makes that trade visible."),
    }
    print("\nstructural ceiling: %s news-classified tier name-days of %s scoreable (%.2f%%), "
          "so the news arm cannot exceed ~%s per half at ANY k"
          % ("{:,}".format(news_sessions), "{:,}".format(len(d)),
             100.0 * news_sessions / len(d),
             "{:,}".format(int(news_sessions / 2))))

    art = {"item": "DIP-CALL k-census: is the NEWS arm reachable at all?",
           "register": "PREREG_dipcall.md committed ALONE at c5e0b31",
           "trials": 0, "forward_return_touched": False,
           "is_a_verdict": False,
           "advances_the_program": False,
           "registered_primary_k": D.K_PRIMARY,
           "floor": D.MIN_EVENTS_PER_CELL,
           "by_k": out, "structural_ceiling": ceiling,
           "scope": ("point-in-time $10B tier, half 0, 2009-2019, BEFORE the embargo and the "
                     "horizon-inside-the-build-years rule, so these counts are an UPPER BOUND on "
                     "the arm cells the kill pass measured")}
    with io.open(D.out_path(ART), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\nwrote %s" % D.out_path(ART))
    return 0


if __name__ == "__main__":
    sys.exit(main())
