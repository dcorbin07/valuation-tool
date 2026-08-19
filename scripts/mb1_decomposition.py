"""MB1 - the selection-vs-timing DECOMPOSITION. DESCRIPTIVE. CARRIES NO VERDICT.

WHAT THIS IS AND WHY IT IS NOT THE VERDICT
------------------------------------------
`PREREG_mb1_alternatives_menu.md` makes the pooled menu MEDIAN the primary and closes contract
selection permanently if the alert-day and random-day medians differ by less than 1.0pp in either
half. `scripts/mb1_alternatives_menu.py` evaluates that rule exactly as written and it FIRES.
Nothing here changes that. This computes the quantity the item actually set out to obtain - the
split of R2's loss between the DAY and the CONTRACT - because the registered statistic cannot
deliver it, and reports the split beside the verdict.

THE IDENTITY, on one entry set:

    pick_gap  =  menu_gap  +  selection_residual
                 (DAY)        (how much worse the shipped rule's own pick is, relative to its own
                               menu, on alert days than on random days)

SCOPE, FIXED BEFORE THE ARITHMETIC. R2's published -5.0640pp is over ALL 3,870 alert and 29,654
control entries; MB1's menu covers 2,446 and 18,227. Differencing a whole-book figure against a
covered-subset figure is the scope error this record has paid for repeatedly, so the picked-contract
gap is RE-DERIVED on exactly the entries that produced menu legs, matched by (ticker, entry, seed)
from the legs artifact. The published -5.0640pp is printed for orientation and is never differenced
against anything here.

THE ONE REAL WEAKNESS, STATED RATHER THAN BURIED. The two sides come from different instruments:
the pick's return is the BANKED `pnl_pct` from R2's own simulation, the menu's returns are
re-simulated on the pinned harvest freeze. But the residual is a DIFFERENCE OF DIFFERENCES -
(pick_a - menu_a) - (pick_c - menu_c) - so any instrument bias that is constant across the two
arms CANCELS EXACTLY. It is only vulnerable to a bias that differs between alert days and random
days, which is a far weaker exposure. O21-D2 separately measured banked-versus-harvest reproduction
on this same book at 2,309 of 2,309 exact.

WEIGHTING IS CONSISTENT BY CONSTRUCTION: a (ticker, date, seed) appearing twice in the control book
is two real trades, and the arms pass builds its menu once PER BOOK ROW, so both sides double-count
such an entry identically.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd  # noqa: E402

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    for cand in (os.path.join(_HERE, "data"), os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isfile(os.path.join(cand, "MB1_LEGS.pkl")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
UNIV = os.path.join(DATA, "options_universe")
LEGS_IN = os.path.join(DATA, "MB1_LEGS.pkl")
ARMS_IN = os.path.join(DATA, "free_analysis", "MB1_MENU.json")
OUT = os.path.join(DATA, "free_analysis", "MB1_DECOMPOSITION.json")

R2_PUBLISHED_GAP_PP = -5.0640      # orientation only; never differenced against anything here


def _log(m):
    print("[MB1-DEC] %s" % m, flush=True)


def _load_book(p):
    with open(p, "rb") as fh:
        d = pickle.load(fh)
    return d["rows"] if isinstance(d, dict) else d


def _mean(xs):
    return (sum(xs) / len(xs)) if xs else None


def decompose(a_pick, c_pick, a_menu, c_menu):
    """The identity, in pp. Returns None components when an input is empty."""
    if None in (a_pick, c_pick, a_menu, c_menu):
        return None
    pick_gap = (a_pick - c_pick) * 100.0
    menu_gap = (a_menu - c_menu) * 100.0
    resid = pick_gap - menu_gap
    return {
        "pick_gap_pp": pick_gap, "menu_gap_pp": menu_gap, "selection_residual_pp": resid,
        "day_share": (menu_gap / pick_gap) if pick_gap else None,
        "selection_share": (resid / pick_gap) if pick_gap else None,
        "alert_pick_minus_own_menu_pp": (a_pick - a_menu) * 100.0,
        "control_pick_minus_own_menu_pp": (c_pick - c_menu) * 100.0,
    }


def main(argv=None) -> int:
    argparse.ArgumentParser(description="MB1 decomposition - DESCRIPTIVE, NO VERDICT").parse_args(argv)

    for p in (LEGS_IN, ARMS_IN):
        if not os.path.exists(p):
            _log("REFUSING: missing %s. Run the arms pass first." % p)
            return 2

    legs = pd.read_pickle(LEGS_IN)
    a_legs, c_legs = legs["alert"], legs["control"]
    cut = json.load(open(ARMS_IN, encoding="utf-8"))["half_cut"]
    _log("legs alert %s, control %s; half boundary %s"
         % ("{:,}".format(len(a_legs)), "{:,}".format(len(c_legs)), cut))

    a_keys = {(l["ticker"], l["entry"]) for l in a_legs}
    c_keys = {(l["ticker"], l["entry"], l["seed"]) for l in c_legs}

    a_rows = [r for r in _load_book(os.path.join(UNIV, "state_r2_splitclean.pkl"))
              if (r["ticker"], str(r["alert_ts"])[:10]) in a_keys and r.get("pnl_pct") is not None]
    c_rows = []
    for s in range(5):
        for r in _load_book(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s)):
            if (r["ticker"], str(r["alert_ts"])[:10], s) in c_keys and r.get("pnl_pct") is not None:
                c_rows.append(r)
    if not a_rows or not c_rows:
        raise RuntimeError("ZERO banked trades matched the legs. An instrument failure, not a "
                           "finding - refusing to write a decomposition from an empty join.")
    _log("matched banked trades: alert %s, control %s"
         % ("{:,}".format(len(a_rows)), "{:,}".format(len(c_rows))))

    out = {"item": "MB1", "pass": "decomposition-diagnostic",
           "status": "DESCRIPTIVE - CARRIES NO VERDICT",
           "note": ("the register's primary is the pooled menu MEDIAN and the arms pass evaluates "
                    "its kill condition on that, as pre-committed. This is the split the item set "
                    "out to obtain, reported beside that verdict and never in place of it."),
           "instrument_caveat": ("pick returns are BANKED pnl_pct, menu returns are re-simulated on "
                                 "the pinned harvest freeze. The residual is a difference of "
                                 "differences, so a bias constant across the arms cancels exactly; "
                                 "only an alert-vs-random-differential bias would survive."),
           "r2_published_whole_book_gap_pp": R2_PUBLISHED_GAP_PP,
           "r2_published_is_a_different_entry_set": True,
           "half_cut": cut, "windows": {}}

    for name, sel in (("full", lambda e: True),
                      ("early", lambda e: e < cut),
                      ("late", lambda e: e >= cut)):
        d = decompose(
            _mean([float(r["pnl_pct"]) for r in a_rows if sel(str(r["alert_ts"])[:10])]),
            _mean([float(r["pnl_pct"]) for r in c_rows if sel(str(r["alert_ts"])[:10])]),
            _mean([l["ret"] for l in a_legs if sel(l["entry"])]),
            _mean([l["ret"] for l in c_legs if sel(l["entry"])]),
        )
        out["windows"][name] = d
        if d:
            _log("%-5s pick %+8.4f = day %+8.4f (%.1f pct) + selection %+8.4f (%.1f pct)"
                 % (name, d["pick_gap_pp"], d["menu_gap_pp"], 100 * d["day_share"],
                    d["selection_residual_pp"], 100 * d["selection_share"]))

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
