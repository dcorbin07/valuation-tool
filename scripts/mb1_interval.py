"""MB1 - a CLUSTERED interval on the menu-median gap. REPORTS A DIAGNOSTIC, CARRIES NO VERDICT.

WHY THIS EXISTS, AND WHAT IT MAY NOT DO
---------------------------------------
`PREREG_mb1_alternatives_menu.md` commits NO uncertainty measure. Its kill condition is a raw
point-estimate comparison of two medians:

    "If the alert-day and random-day pooled menu medians differ by LESS THAN 1.0pp in EITHER
     half, contract selection is declared IRRELEVANT ... permanently."

That rule is pre-committed and `scripts/mb1_alternatives_menu.py` evaluates it EXACTLY as written.
This script may not change that verdict and does not compute it. It exists because the kill
condition closes a question PERMANENTLY, and a permanent closure resting on an un-intervalled
point estimate is a weakness of my own register that has to travel with the result. A 0.8pp gap
with a tight interval and a 0.8pp gap with an interval spanning [-6, +7] are different findings,
and the register cannot tell them apart.

WHY A NAIVE INTERVAL WOULD BE WORTHLESS
---------------------------------------
R3 measured this book's options statistics to be clustered, at a design effect of 2.1837 on the
split-clean book against a shuffled null p95 of 1.1898. The clustering here is far worse than
that, because the unit is a LEG rather than a trade: the ~5 legs of one entry are the same
underlying on the same day at adjacent strikes, so they are near-perfectly correlated. An i.i.d.
interval over ~225,000 legs would be narrow by a large factor and would read as authoritative.

THE CLUSTER IS (ticker, year), R3's own unit. Resampling NAMES alone leaves only 173 clusters;
name-year gives ~1,700 and is the unit R3's paired sign test already uses on this book.

THE SAME CLUSTER KEYS ARE RESAMPLED FOR BOTH ARMS, which is what makes this a PAIRED bootstrap:
a draw that happens to load up on a good name loads it up in both arms, so common name and period
effects cancel out of the gap exactly as they do in the point estimate.

WHAT IS REPORTED
----------------
Per half and full sample: the point gap (reproducing the arm's own figure as a control), the
percentile interval, and readings that are DESCRIPTIONS and not verdicts - whether the interval
contains zero, and which side of the register's 1.0pp bar it reaches. The reading that matters is
`interval_resolves_the_registers_rule`: FALSE means the interval contains both gaps that would fire
the kill and gaps that would not, so a PERMANENT closure would rest on where inside a wide
interval the point estimate happened to land. If that is the case it is said plainly.

Reads only `MB1_LEGS.pkl`, written by the arms pass. Touches no chain store and no network.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
LEGS_IN = os.path.join(DATA, "MB1_LEGS.pkl")
ARMS_IN = os.path.join(DATA, "free_analysis", "MB1_MENU.json")
OUT = os.path.join(DATA, "free_analysis", "MB1_INTERVAL.json")

B_DRAWS = 2000
SEED = 20260819
BAR_PP = 1.0          # quoted from the register; this script never tests against it


def _log(m):
    print("[MB1-INT] %s" % m, flush=True)


def _median(xs):
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else 0.5 * (s[n // 2 - 1] + s[n // 2])


def _pct(xs, q):
    if not xs:
        return None
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def _cluster(leg):
    """R3's unit: the name-year cell."""
    return (leg["ticker"], str(leg["entry"])[:4])


def _by_cluster(legs):
    out = {}
    for l in legs:
        out.setdefault(_cluster(l), []).append(l["ret"])
    return out


def bootstrap_gap(a_legs, c_legs, b=B_DRAWS, seed=SEED):
    """Paired name-year cluster bootstrap of (alert median - control median), in pp."""
    A, C = _by_cluster(a_legs), _by_cluster(c_legs)
    keys = sorted(set(A) | set(C))
    if not keys:
        return None
    rnd = random.Random(seed)
    gaps = []
    for _ in range(b):
        draw = [keys[rnd.randrange(len(keys))] for _ in range(len(keys))]
        av, cv = [], []
        for k in draw:
            av.extend(A.get(k, ()))
            cv.extend(C.get(k, ()))
        ma, mc = _median(av), _median(cv)
        if ma is None or mc is None:
            continue
        gaps.append((ma - mc) * 100.0)
    if not gaps:
        return None
    return {
        "n_clusters": len(keys), "n_draws": len(gaps),
        "point_gap_pp": ((_median([l["ret"] for l in a_legs]) -
                          _median([l["ret"] for l in c_legs])) * 100.0),
        "p2_5": _pct(gaps, 0.025), "p50": _pct(gaps, 0.50), "p97_5": _pct(gaps, 0.975),
    }


def _readings(r):
    """DESCRIPTIONS of the interval. Not verdicts - the register's rule is the point estimate.

    The register's kill fires when |gap| < 1.0pp, so the interval splits the line into two
    regions: KILL = (-1.0, +1.0) and NO-KILL = everything at least 1.0pp from zero. What is worth
    reporting is which regions the interval reaches:

      * it reaches only KILL      -> the closure is robust to sampling error
      * it reaches only NO-KILL   -> a non-closure is robust to sampling error
      * it reaches BOTH           -> the interval does NOT resolve the decision, and a PERMANENT
                                     closure would rest on where inside it the point estimate
                                     happened to land. That has to be said out loud.
    """
    lo, hi = r["p2_5"], r["p97_5"]
    inside_bar = bool(lo < BAR_PP and hi > -BAR_PP)            # intersects (-bar, +bar)
    beyond_bar = bool(lo <= -BAR_PP or hi >= BAR_PP)           # has a point with |x| >= bar
    return {
        "interval_contains_zero": bool(lo <= 0.0 <= hi),
        "interval_reaches_inside_the_bar": inside_bar,
        "interval_reaches_beyond_the_bar": beyond_bar,
        # FALSE = the interval spans both regions, so the register's rule is not resolved by it
        "interval_resolves_the_registers_rule": bool(inside_bar != beyond_bar),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MB1 clustered interval - DIAGNOSTIC, NO VERDICT")
    ap.add_argument("--draws", type=int, default=B_DRAWS)
    a = ap.parse_args(argv)

    if not os.path.exists(LEGS_IN):
        _log("REFUSING: no legs artifact at %s. Run the arms pass first." % LEGS_IN)
        return 2
    d = pd.read_pickle(LEGS_IN)
    a_legs, c_legs = d["alert"], d["control"]
    _log("legs: alert %s, control %s" % ("{:,}".format(len(a_legs)), "{:,}".format(len(c_legs))))

    cut = None
    if os.path.exists(ARMS_IN):
        with open(ARMS_IN, encoding="utf-8") as fh:
            cut = json.load(fh).get("half_cut")
    if cut is None:
        _log("REFUSING: no half_cut in the arms artifact; the halves must be the arm's own.")
        return 2
    _log("half boundary read from the arms artifact: %s" % cut)

    out = {"item": "MB1", "pass": "interval-diagnostic",
           "status": "DIAGNOSTIC - CARRIES NO VERDICT",
           "note": ("the register commits no uncertainty measure and its kill condition is a raw "
                    "point-estimate comparison, evaluated as written by the arms pass. This is "
                    "reported beside that verdict, never in place of it."),
           "cluster_unit": "(ticker, year) - R3's own unit on this book",
           "paired": True, "n_draws_requested": a.draws, "seed": SEED,
           "bar_pp_quoted_from_register": BAR_PP, "windows": {}}

    for name, sel in (("full", lambda e: True),
                      ("early", lambda e: e < cut),
                      ("late", lambda e: e >= cut)):
        al = [l for l in a_legs if sel(l["entry"])]
        cl = [l for l in c_legs if sel(l["entry"])]
        r = bootstrap_gap(al, cl, b=a.draws)
        if r is None:
            out["windows"][name] = None
            continue
        r.update(_readings(r))
        r["n_alert_legs"], r["n_control_legs"] = len(al), len(cl)
        out["windows"][name] = r
        _log("%-5s gap %+.4f pp   CI95 [%+.4f, %+.4f]   clusters %d   %s"
             % (name, r["point_gap_pp"], r["p2_5"], r["p97_5"], r["n_clusters"],
                "contains zero" if r["interval_contains_zero"] else "excludes zero"))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
