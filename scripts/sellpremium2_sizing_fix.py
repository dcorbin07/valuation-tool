"""The sizing grid, re-run on BOTH stages with a loop that can be ruined.

**THE DEFECT, FOUND BY DISBELIEVING A NUMBER RATHER THAN BY ANYTHING RAISING.** Stage 2's grid
reported terminal equities of **-$217,426** on a $250,000 account. A cash-secured put cannot lose
more than its strike and an account cannot fund positions it does not have the cash for, so a
deeply negative terminal equity is not a possible outcome -- it is an artefact of a loop that
(a) sized every position from the STARTING equity forever and (b) kept trading after the account
was gone.

**THE DIRECTION MATTERS AND IT IS THE UNSAFE ONE FOR A REJECTION.** Reporting -$217k where the
truth is "ruined at zero" makes a failing leg look worse than it is, and clause (c) is a leg this
stage FAILS. A defect that exaggerates a rejection has to be repaired before the rejection is
quoted, not after.

**THE REPAIR IS `O11`'s OWN CONSTRUCTION:** size from CURRENT equity, and stop when the account
can no longer fund a position. `MB3`'s separation of the two skip reasons is kept -- an
affordability skip is never a concurrency skip -- and a third state, RUINED, is recorded.

**BOTH STAGES ARE RE-RUN, because a repaired instrument must be applied to both or the two are
not comparable.** Stage 1's verdict is reported either way.

Usage:  python -m scripts.sellpremium2_sizing_fix
"""
import io
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402


def grid(bk: pd.DataFrame, equity0: float, cap: int) -> dict:
    """One cell. Sizes from CURRENT equity and STOPS at ruin."""
    bs = bk.sort_values("date").reset_index(drop=True)
    equity, slots = float(equity0), []
    aff = conc = taken = 0
    ruined_on = None
    for _i, r in bs.iterrows():
        slots = [x for x in slots if x > r["date"]]
        if equity <= 0:
            ruined_on = ruined_on or str(r["date"])
            break                       # the account is gone; it cannot trade on
        if len(slots) >= cap:
            conc += 1
            continue
        per = equity / float(cap)       # CURRENT equity, not the starting figure
        sec = float(r["secured"])
        if sec > per:
            aff += 1
            continue
        equity += sec * float(r["ret_pct"]) / 100.0
        slots.append(str(r["expiration"]))
        taken += 1
    return {"start": float(equity0), "terminal_equity": float(max(equity, 0.0)),
            "taken": taken, "affordability_skips": aff, "concurrency_skips": conc,
            "ruined": bool(ruined_on is not None or equity <= 0),
            "ruined_on": ruined_on,
            "survives": bool(equity > equity0)}


def run(label, book_path):
    bk = pd.read_pickle(book_path)
    out = {}
    print("\n%s  (%d trades)" % (label, len(bk)))
    for eq in SP.SIZING_EQUITY:
        for cap in SP.SIZING_CAPS:
            c = grid(bk, eq, cap)
            out["$%d/cap%d" % (int(eq), cap)] = c
            print("  $%-7d cap %-3d taken %5d  aff %5d  conc %5d -> $%10.0f  %s%s"
                  % (eq, cap, c["taken"], c["affordability_skips"], c["concurrency_skips"],
                     c["terminal_equity"], "survives" if c["survives"] else "DOES NOT SURVIVE",
                     ("  RUINED on %s" % c["ruined_on"]) if c["ruined"] else ""))
    return out


def main():
    art = {"item": "SELL-PREMIUM-2 sizing grid, repaired loop", "trials": 0,
           "defect": ("the first loop sized every position from the STARTING equity and kept "
                      "trading after the account was gone, so stage 2 reported terminal "
                      "equities as low as -$217,426 -- not a possible outcome for a "
                      "cash-secured book. The direction is the UNSAFE one for a rejection: it "
                      "made a failing leg look worse than it is."),
           "repair": ("size from CURRENT equity and STOP at ruin; RUINED recorded as its own "
                      "state beside MB3's two skip reasons")}
    s1 = D.out_path("SELLPREMIUM2_BOOK.pkl")
    s2 = D.out_path("SELLPREMIUM2_STAGE2_BOOK.pkl")
    if os.path.isfile(s1):
        art["stage1"] = run("STAGE 1 (build quadrant, 2016-2019 x half 0)", s1)
        art["stage1_all_survive"] = all(v["survives"] for v in art["stage1"].values())
    if os.path.isfile(s2):
        art["stage2"] = run("STAGE 2 (check quadrant, 2020-2026 x half 1)", s2)
        art["stage2_all_survive"] = all(v["survives"] for v in art["stage2"].values())
        art["stage2_cells_ruined"] = sorted(k for k, v in art["stage2"].items() if v["ruined"])
    with io.open(D.out_path("SELLPREMIUM2_SIZING_FIX.json"), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("\nstage 1 every cell survives: %s" % art.get("stage1_all_survive"))
    print("stage 2 every cell survives: %s ; ruined cells: %s"
          % (art.get("stage2_all_survive"), art.get("stage2_cells_ruined")))
    print("wrote %s" % D.out_path("SELLPREMIUM2_SIZING_FIX.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
