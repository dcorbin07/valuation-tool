# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 2a -- the Index tab's backtested column on the corrected universe.

    python -m scripts.corrected_index_book

**THE PRIORITY CLAIM.** `UNIVERSE-BIAS` part 2 could not re-derive it, because `INDEX-BOOK`'s own
`C1` fidelity gate REFUSES any panel but the banked one -- correctly, since the corrected panel is
not the object the published record describes. Part 2 recorded it `UNMEASURED` and estimated the
move at about -0.4pp from the ladder's $10B rung.

**THIS RUNS THE SHIPPED MEASUREMENT ON THE CORRECTED PANEL AS A SEPARATELY LABELLED OBJECT, AND
THE GATE KEEPS ITS FULL STRENGTH.** `served_index_book.main` is CALLED with its `expect_alpha`
parameter pointed at `UNIVERSE-BIAS` part 2's own landed `corrected` top-decile alpha, read from
that item's artifact rather than typed here. The gate still demands **EXACT** reproduction
(`dev == 0.0`) on **69** dates and still **ABORTS** -- only WHICH landed figure is a parameter.

**WHY NOT A FRESH SCRIPT.** `served_index_book` is ~150 lines of arms, tax treatments, the
one-knob decomposition and the contract power inputs. A second implementation of all of that is
`B7`'s defect -- two measurements of one object, free to drift -- and it is the defect
`index_book_measured.py`'s own thirty transcribed literals exist downstream of.

**THE BANKED ARTIFACT IS NOT OVERWRITTEN.** It writes `INDEX_BOOK_CORRECTED.json`. Nothing here
touches `INDEX_BOOK.json`, the canonical panel, or any public page -- pinned by test.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_claims as CC                                       # noqa: E402

PANEL = "UNIVERSE_BIAS_PANEL_full.pkl"
OUT = "INDEX_BOOK_CORRECTED.json"
LABEL = ("the CORRECTED full raw universe (9,645 names, 289,659 rows, 69 dates) -- a SEPARATE "
         "OBJECT from the published 2,531-name book, not a restatement of it")


def main(argv=None):
    fa = CC.fa()
    panel_path = os.path.join(fa, PANEL)
    if not os.path.exists(panel_path):
        raise SystemExit("REFUSING: no corrected panel at %s" % panel_path)

    # THE DEPLOYED figure, not part 2's `corrected` column. `served_index_book` scores the
    # DEPLOYED composite, and part 2's corrected column is the CPCV-ADOPTED book -- handing it
    # the adopted figure is a numerator from one construction against a gate for another, which
    # is what part 1b exists to record and what the gate caught (twice).
    want = CC.landed_corrected_deployed_alpha()
    print("gate target  %.17f   (CORRECTED_DEPLOYED.json deployed.top_decile_alpha -- part 1b's "
          "own measurement, READ not typed)" % want, flush=True)
    print("  NOT part 2's corrected column (%.17f): that is the CPCV-ADOPTED book, and this "
          "measurement is the DEPLOYED one" % CC.landed_corrected_alpha(), flush=True)

    # DEFERRED IMPORT. `served_index_book` resolves its data root at module level and RAISES
    # without the banked panel, so importing it at the top of this file would make every test
    # that touches this module error on a CI runner (`UNIVERSE-BIAS`'s own CI failure).
    from scripts import served_index_book as SIB

    rc = SIB.main(panel_path=panel_path, out=os.path.join(fa, OUT), label=LABEL,
                  expect_alpha=want)
    if rc:
        return rc

    # --- the comparison table against the published book ---------------------------------
    with io.open(os.path.join(fa, "INDEX_BOOK.json"), encoding="utf-8") as fh:
        pub = json.load(fh)
    with io.open(os.path.join(fa, OUT), encoding="utf-8") as fh:
        cor = json.load(fh)

    # The SERVED arm is the Index. The others are the decomposition's rungs.
    KEYS = ("net_ann", "net_alpha_vs_equal_weight", "net_alpha_vs_tier_equal_weight",
            "net_alpha_vs_spy", "net_sharpe", "net_max_drawdown", "annual_turnover",
            "realised_one_way_bps", "spy_ann", "equal_weight_ann", "tier_equal_weight_ann")
    print("\n=== A_served (the Index), published vs corrected", flush=True)
    rows = []
    for k in KEYS:
        a, b = pub["arms"]["A_served"].get(k), cor["arms"]["A_served"].get(k)
        d = (None if a is None or b is None else b - a)
        rows.append({"key": k, "published": a, "corrected": b, "delta": d})
        print("  %-34s %-13s %-13s %s"
              % (k, ("%.6f" % a) if a is not None else "-",
                 ("%.6f" % b) if b is not None else "-",
                 ("%+.6f" % d) if d is not None else "-"), flush=True)

    print("\n=== tax treatments (the Roth figure the Index tab leads with)", flush=True)
    tax = []
    for lab in ("roth_ira", "taxable"):
        a = (pub.get("tax_treatments") or {}).get(lab) or {}
        b = (cor.get("tax_treatments") or {}).get(lab) or {}
        for k in ("after_tax_ann", "after_tax_alpha", "after_tax_sharpe",
                  "after_tax_max_drawdown"):
            x, y = a.get(k), b.get(k)
            d = (None if x is None or y is None else y - x)
            tax.append({"treatment": lab, "key": k, "published": x, "corrected": y, "delta": d})
            print("  %-9s %-26s %-13s %-13s %s"
                  % (lab, k, ("%.6f" % x) if x is not None else "-",
                     ("%.6f" % y) if y is not None else "-",
                     ("%+.6f" % d) if d is not None else "-"), flush=True)

    res = {
        "item": "CORRECTED-FLOORS",
        "part": "2a -- the Index tab's backtested column on the corrected universe",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of a registered construction on a corrected universe "
                       "(S25 / X7RECON / PANEL-EXT-RECHECK class) -- no hypothesis, no bar "
                       "chosen here, no second arm.",
        "object_label": LABEL,
        "gate": {
            "target": want,
            "target_source": "CORRECTED_DEPLOYED.json deployed.top_decile_alpha -- part 1b's "
                             "own measurement, read rather than typed, so the gate cannot be "
                             "satisfied by a number chosen to fit. NOT part 2's `corrected` "
                             "column, which is the CPCV-ADOPTED book: served_index_book scores "
                             "the DEPLOYED composite, and handing it the adopted figure is a "
                             "numerator from one construction against a gate for another. The "
                             "gate refused it twice, and the second refusal is what produced "
                             "part 1b.",
            "part2_corrected_column_is_the_adopted_book": CC.landed_corrected_alpha(),
            "C1_fidelity": cor.get("C1_fidelity"),
            "strength_unchanged": "dev == 0.0 on 69 dates, and it still ABORTS. Only WHICH "
                                  "landed figure is a parameter; the default is the published "
                                  "alpha, so every existing caller is bit-identical (proved by "
                                  "leaf diff: 5,633 shared leaves, ZERO moved).",
        },
        "banked_artifact_not_overwritten": "INDEX_BOOK.json",
        "served_arm": rows,
        "tax_treatments": tax,
        "part2_estimate_was": ("UNIVERSE-BIAS part 2 estimated the universe moves these figures "
                               "about -0.4pp, from the ladder's $10B rung (18.42pc restricted "
                               "against 18.02pc corrected). That rung is a DIFFERENT "
                               "construction from the served arm -- no band, no 8pc cap -- so "
                               "this is the first like-for-like reading."),
    }
    with io.open(os.path.join(fa, OUT.replace(".json", "_COMPARE.json")), "w",
                 encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote %s" % os.path.join(fa, OUT.replace(".json", "_COMPARE.json")), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
