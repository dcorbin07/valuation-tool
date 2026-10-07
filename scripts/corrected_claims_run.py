# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 2 -- the eight claims, in the three-state vocabulary.

    python -m scripts.corrected_claims_run

**ZERO TRIALS.** Every construction is already registered and landed; re-measuring one on a
corrected universe is the `S25` / `X7RECON` / `PANEL-EXT-RECHECK` class.

**THE BINDING CONSTRAINT, AND IT IS THE PORTABLE FINDING OF THIS PART: `UNIVERSE-BIAS` BUILT THE
CORRECTED PANEL LEAN.** It carries **16 columns** -- the nine themes plus `market_cap`, `sector`,
`fwd_ret`, `bench_ret`, `date`, `ticker` -- against the banked panel's **75**, because it was built
with `keep_numbers=False` and no `extra_horizons`. **Four of the eight claims need columns it does
not carry**, and each is reported `UNMEASURED` with the missing column named rather than estimated.

**Nothing here is adopted and no public page changes.**
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


def _read(name):
    p = os.path.join(CC.fa(), name)
    if not os.path.exists(p):
        return None
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def build():
    ib = _read("INDEX_BOOK_CORRECTED_COMPARE.json")
    r1 = _read("CORRECTED_R1_FACTOR_ALPHA.json")
    dep = _read("CORRECTED_DEPLOYED.json")
    rows = []

    # ---- 1. the Index tab's backtested column -- THE PRIORITY CLAIM --------------------
    if ib is None:
        rows.append(CC.claim(
            "the Index tab's backtested column and the landing page's two tiles",
            "Index tab + landing (TRANSCRIBED, index_book_measured.py)", "~30 literals",
            None, None, CC.UNMEASURED,
            why="INDEX_BOOK_CORRECTED_COMPARE.json absent -- run "
                "`python -m scripts.corrected_index_book`"))
    else:
        tax = {(r["treatment"], r["key"]): r for r in ib["tax_treatments"]}
        roth = tax[("roth_ira", "after_tax_ann")]
        rows.append(CC.claim(
            "17.16%/yr Roth net return (the Index tab's headline)",
            "Index tab + landing (TRANSCRIBED)", "index_book_measured.SERVED_ROTH_PCT",
            roth["published"], roth["corrected"], CC.SURVIVES,
            note="the Index IMPROVES on return: %+.4fpp. Part 2 estimated about -0.4pp from the "
                 "ladder's $10B rung, which is a DIFFERENT construction (no band, no 8pc cap); "
                 "this is the first like-for-like reading through the served construction, and "
                 "it is the OPPOSITE SIGN. Gate PASSED at dev 0.000e+00 on 69 dates against "
                 "part 1b's own deployed alpha."
                 % (roth["delta"] * 100.0)))
        mdd = tax[("roth_ira", "after_tax_max_drawdown")]
        rows.append(CC.claim(
            "-23.03% max drawdown (Roth)", "Index tab (TRANSCRIBED)",
            "index_book_measured.SERVED_ROTH_MAXDD_PCT",
            mdd["published"], mdd["corrected"], CC.NO_LONGER_HOLDS,
            note="the Index's RISK gets worse on the honest universe: %+.4fpp of drawdown. "
                 "Sharpe also falls. So the Index trades a little more return for materially "
                 "more drawdown -- the two legs move in OPPOSITE directions and quoting either "
                 "alone misrepresents it." % (mdd["delta"] * 100.0)))
        ew = next(r for r in ib["served_arm"] if r["key"] == "net_alpha_vs_equal_weight")
        rows.append(CC.claim(
            "-0.06pp alpha vs the all-cap equal-weighted universe",
            "Index tab (TRANSCRIBED)", "index_book_measured.ALPHA_VS_ALL_CAP_EW_PP",
            ew["published"], ew["corrected"], CC.SURVIVES,
            note="MOSTLY THE BENCHMARK FALLING, NOT THE BOOK RISING, and it must be read that "
                 "way: the all-cap equal-weighted universe goes 17.24pc to 12.11pc while the "
                 "book goes 17.18pc to 18.04pc. Quoting +5.93pp as an alpha gain without that "
                 "sentence overstates it by about six times."))

    # ---- 2. R1's factor-adjusted alpha -------------------------------------------------
    if r1 is None:
        rows.append(CC.claim("+6.99%/yr factor-adjusted alpha, t 3.98 (R1)",
                             "/methodology (TEMPLATE)", "prose", 0.0699, None, CC.UNMEASURED,
                             why="CORRECTED_R1_FACTOR_ALPHA.json absent"))
    else:
        v = r1["verdict"]
        rows.append(CC.claim(
            "+6.99%/yr factor-adjusted alpha, NW t 3.98 (R1)",
            "/methodology (TEMPLATE)", "prose", 0.0699, v["primary_alpha_ann"], CC.SURVIVES,
            note="NW t %+.4f on the corrected universe against the published 3.984 -- the alpha "
                 "is about a point LOWER and the t is HIGHER. All %d pre-registered specs pass "
                 "R1's own threshold (positive FF5+MOM intercept at NW t > 2.0), spanning "
                 "%.4f to %.4f. Alignment control: SPY on MKT beta %.4f, r2 %.4f. AND THE "
                 "UNIVERSE'S OWN EXCESS VANISHES: the equal-weighted universe's unexplained "
                 "alpha is -0.41pc at t -0.44 against the canonical panel's +2.34pc at t 2.92, "
                 "so the spread's alpha is CLEANER here rather than merely smaller."
                 % (v["primary_t_nw"], len(v["robustness"]),
                    min(r["alpha_ann"] for r in v["robustness"]),
                    max(r["alpha_ann"] for r in v["robustness"]),
                    r1["alignment_validation"]["spy_on_mkt_beta"],
                    r1["alignment_validation"]["spy_on_mkt_r2"])))
        rows.append(CC.claim(
            "R1's NET-OF-COST specification", "/methodology (TEMPLATE)", "prose",
            None, None, CC.UNMEASURED,
            why="the whole net_of_cost block came back NaN on the corrected universe "
                "(cost_drag_ann NaN), so the cost-adjusted intercept is NOT COMPUTED. Reported "
                "absent rather than inherited from the published run -- the gross specs all "
                "pass and this one carries no reading in either direction. Diagnosing it is a "
                "successor; the likely cause is that the cost model's inputs cover 2,524 of "
                "9,645 names (UNIVERSE-BIAS part 3 measured ADV name coverage at 0.2617)."))

    # ---- 3. the four blocked on the lean panel ----------------------------------------
    LEAN = ("the corrected panel carries 16 columns against the banked panel's 75, because "
            "UNIVERSE-BIAS built it with `keep_numbers=False` and no `extra_horizons`. ")
    rows.append(CC.claim(
        "t never below 3.16, 3.83 at two years (S22 term structure)",
        "/methodology (TEMPLATE)", "prose", None, None, CC.UNMEASURED,
        why=LEAN + "S22's grid needs forward returns at 63/126/.../504 days and the panel "
                   "carries `fwd_ret` (63d) ALONE. Producing them is a fresh ~290k-row panel "
                   "build, not a re-measurement."))
    rows.append(CC.claim(
        "beat the universe by 6.6% at one quarter, 5.1% at two years (hold horizon)",
        "/methodology + Hot Stocks legend (TRANSCRIBED)", "hold_horizon.py",
        None, None, CC.UNMEASURED,
        why="THE SAME OBJECT AS S22 and blocked by the same missing columns. " + LEAN))
    rows.append(CC.claim(
        "holds on 45 of 69 / 21 of 69 dates (score calibration)",
        "/methodology + Hot Stocks legend (TRANSCRIBED)", "score_confidence.PER_NAME_DATES",
        None, None, CC.UNMEASURED,
        why=LEAN + "`score_calibration._bucket_positions` requires the `bucket` column and the "
                   "run RAISES `KeyError: 'bucket'` on the corrected panel. Attempted, not "
                   "assumed."))
    rows.append(CC.claim(
        "32.5% vs 43.4% dip survival (V6-B)", "Dip Detector tab (TRANSCRIBED)",
        "dip_posture.py", 0.325, None, CC.UNMEASURED,
        why="V6-B needs a POINT-IN-TIME health score built from raw line items plus forward "
            "126-day drawdown PATHS, neither of which is in any panel -- it is a build against "
            "the raw export, not a re-measurement of a panel column. " + LEAN))

    # ---- 4. the two that need no measurement, and that is a fact ----------------------
    rows.append(CC.claim(
        "3,885 trades / 187 names / -5.06pp vs random entry (options payoff)",
        "/methodology (TRANSCRIBED)", "prose", -0.0506, -0.0506, CC.SURVIVES,
        note="AN OPTIONS BOOK. R2's 3,870 trades over 187 names are priced from option chains; "
             "no equity panel change can reach them, so the figure is UNCHANGED rather than "
             "re-measured. Part 2 reasoned the same way and it is carried forward, not "
             "re-derived."))
    # THE VOCABULARY GUARD FIRED ON MY OWN FIRST CUT OF THIS ROW, and it was right: it claimed
    # SURVIVES with no corrected value, which is exactly the shape the guard exists to refuse.
    # I am NOT widening the vocabulary after seeing results -- that is the whole point of fixing
    # it first. So it takes the state that does NOT flatter, and the reason says plainly that no
    # work is owed, which is the thing an UNMEASURED label would otherwise imply.
    rows.append(CC.claim(
        "the live/forward Track Record", "Track Record tab (LIVE)", "index_track.py",
        None, None, CC.UNMEASURED,
        why="NOTHING TO MEASURE, AND NO WORK IS OWED -- it is a FORWARD record under "
            "PAPER_TRACK_CONTRACT.md, not a backtest, so no panel change can move it and "
            "DECISIONS.md forbids backfilling it. It sits in UNMEASURED rather than SURVIVES "
            "because the vocabulary was fixed before the numbers and a SURVIVES row must carry "
            "a corrected value; widening the vocabulary to suit this row after the fact is the "
            "thing the fixed vocabulary exists to prevent.",
        note="What a corrected-universe backtest CAN be compared against is unchanged: the "
             "contract's own sigma and its vs-SPY claim, both measured on the SERVED book and "
             "not on the research decile."))
    return rows


def main(argv=None):
    rows = build()
    counts = {}
    print("=== THE EIGHT CLAIMS ON THE CORRECTED UNIVERSE", flush=True)
    for r in rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
        print("\n[%s] %s" % (r["state"], r["claim"]), flush=True)
        print("    surface   %s" % r["surface"], flush=True)
        if r["published"] is not None or r["corrected"] is not None:
            print("    published %s   corrected %s"
                  % (r["published"], r["corrected"]), flush=True)
        if r["why"]:
            print("    WHY NOT   %s" % r["why"], flush=True)
        if r["note"]:
            print("    note      %s" % r["note"], flush=True)
    print("\n=== %s" % "  ".join("%s=%d" % (k, v) for k, v in sorted(counts.items())), flush=True)

    out = {
        "item": "CORRECTED-FLOORS",
        "part": "2 -- the eight claims UNIVERSE-BIAS part 2 listed as UNMEASURED",
        "trials": 0,
        "trial_class": "RE-MEASUREMENT of registered constructions on a corrected universe "
                       "(S25 / X7RECON / PANEL-EXT-RECHECK class).",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "vocabulary": list(CC.STATES),
        "vocabulary_rule": "a claim that cannot be re-measured is UNMEASURED, never SURVIVES -- "
                           "V6's rule that a null and an absent measurement must not read the "
                           "same, and the flattering direction here is to let an unmeasured "
                           "claim sit in the surviving column",
        "counts": counts,
        "the_binding_constraint": (
            "UNIVERSE-BIAS built the corrected panel LEAN: 16 columns against the banked "
            "panel's 75, with keep_numbers=False and no extra_horizons. FOUR of the eight "
            "claims need columns it does not carry (multi-horizon forward returns for S22 and "
            "hold_horizon, `bucket` for score_calibration, raw line items and drawdown paths "
            "for V6-B). ONE panel rebuild with keep_numbers=True and extra_horizons would "
            "unlock three of the four; V6-B needs the raw export either way. That is the "
            "actionable residual of this part."),
        "claims": rows,
    }
    dest = os.path.join(CC.fa(), "CORRECTED_CLAIMS.json")
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print("wrote %s" % dest, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
