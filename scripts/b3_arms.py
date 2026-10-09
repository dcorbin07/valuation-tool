# -*- coding: utf-8 -*-
"""`STAGE1-BATCH3` — the arms, scored only for arms whose kill PASSED.

    python -m scripts.b3_arms --panel <v3.pkl> --kills <B3_KILLS.json> --out <B3_ARMS.json>

**IT REFUSES WITHOUT A PASSING KILL ARTIFACT FOR THE ARM IT IS ABOUT TO SCORE**, which is `O10`'s
ordering rule made mechanical: a gating control computed in the same pass as the outcomes cannot
be claimed to have been read first, so the kills ran in their own pass and this one reads their
artifact off disk.

**EVERY STATISTIC IS BATCH 2's, CALLED (`B7`).** `deployed_control`, `score_ic_arm`,
`incremental_ic`, `hac_t`, `two_sided_p`, `mde80`, `benjamini_hochberg`, `stage1_verdict`,
`tier_frame` and `build_quadrant` all come from the modules batches 1 and 2 used. This file
contributes orchestration and nothing else — a second definition of an incremental IC is how two
numbers for one question come about.

**THE INCREMENTAL CONTROL IS THE DEPLOYED COMPOSITE** as ONE regressor (charter §5 Stage 1a), not
complete-case residualisation on seven themes — which is why all 44 build-quadrant dates survive,
halves 24/20 at 2014-12-31.

**BOTH POPULATIONS ARE SCORED AND THE `cap >= $10B` TIER GOVERNS** (charter §5 Stage 1b). An arm
that clears wide and fails the tier is **`REAL BUT NOT INVESTABLE HERE`** and does not reach
Stage 2.

**BH IS ACROSS `k` = 9 WHILE EIGHT ARMS RUN** (register §0.4). Membership was fixed in the draft
before any outcome, so shrinking the denominator after withdrawing C9 would be choosing the
correction on the batch. The direction is conservative.

**NO CALIBRATED FLOOR IS QUOTED BESIDE AN INCREMENTAL IC.** `MB22`/`U2`: `ic_tstat` carries the
calibrated bar and an incremental *t* is a NEW statistic with none, so the critical value here is
the conventional 2.0 and it ships **LABELLED UNCALIBRATED**. Writing `CORRECTED_FLOORS`'
2.885180 beside these numbers would be `R1-VAR`'s category error.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.stage1_kills import build_quadrant, BUILD_HALF_SPLIT          # noqa: E402
from scripts.stage1_score import benjamini_hochberg                        # noqa: E402
from scripts.stage1_batch2_kills import tier_frame                        # noqa: E402
from scripts.stage1_batch2_arms import deployed_control, score_ic_arm, CRIT  # noqa: E402
from scripts.b3_kills import attach                                        # noqa: E402

BH_K = 9                  # register §0.4 -- k stays 9 while eight arms run
BH_Q = 0.10

#: `stage1_verdict`'s PASSING state, DERIVED from the shared module rather than typed.
#:
#: My first version of the Stage-1b label compared against the string `"SURVIVES"`, which that
#: function never returns -- its three states are `NOT_ASSESSABLE`, `CLEARS` and
#: `NOT_REPLICATED`. The charter's `REAL BUT NOT INVESTABLE HERE` label was therefore
#: UNREACHABLE, and it took an arm actually clearing wide-and-failing-tier (`C4`) to expose it.
#: Deriving the string means a rename upstream turns this red rather than quietly re-killing the
#: branch, which is the whole lesson of the `MA5` frozen-default and `MA4` unreachable-guard
#: families.
def _pass_verdict():
    from scripts.stage1_score import stage1_verdict as _sv
    half = {"n": 999, "t": 99.0}
    v, _ = _sv(half, half, True, crit=2.0)
    return v


PASS_VERDICT = _pass_verdict()
assert PASS_VERDICT not in (None, "", "NOT_REPLICATED", "NOT_ASSESSABLE"), (
    "the passing verdict could not be derived from stage1_verdict; the Stage-1b label would be "
    "unreachable again: got %r" % (PASS_VERDICT,))

#: the arms this pass can score, in the draft's own ranked order. C8 runs in its own pass (its
#: expanding-window fit is expensive and its strictness is a separate pre-committed kill) and C9
#: is NOT RUN (register §0.1).
ORDER = ("C3", "C4", "C1", "C2", "C5", "C7", "C6")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--kills", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    if not os.path.exists(args.kills):
        raise SystemExit("REFUSING: no kill artifact at %s. The kills run in their OWN pass and "
                         "this one reads their result off disk -- O10's rule." % args.kills)
    with io.open(args.kills, encoding="utf-8") as fh:
        kills = json.load(fh)

    from scripts.tiered_pool_run import _hist
    from scripts import b3_signals as S1
    from scripts import b3_signals2 as S2
    from scripts.b3_kills import _prov

    panel = pd.read_pickle(args.panel)
    quad, qcen = build_quadrant(panel)
    quad, cols, w = deployed_control(quad.copy())
    print("[arms] build quadrant %d rows / %d dates; deployed control over %d themes"
          % (qcen["rows"], qcen["dates"], len(cols)), flush=True)

    export = os.path.join(r"C:/Users/donni/Downloads/valuation-tool/data", "full2009", "backtest")
    hist = _hist(export)

    builders = {
        "C3": lambda: S1.c3_rnd_to_market(quad, hist),
        "C4": lambda: S2.c4_composite_issuance(quad, _prov()),
        "C1": lambda: S2.c1_abarbanell_bushee(quad, hist),
        "C2": lambda: S2.c2_g_score(quad, hist),
        "C5": lambda: S1.c5_earnings_stability(quad, hist),
        "C7": lambda: S1.c7_operating_leverage(quad, hist),
        "C6": lambda: S1.c6_cash_conversion_cycle(quad, hist),
    }

    res = {"item": "STAGE1-BATCH3", "part": "the arms",
           # DESCRIBES THE EXISTING BOOKING; CHARGES NOTHING FURTHER. The eight equity trials
           # were booked at 89593a6 before any runner existed (equity N 285 -> 293), and the
           # verdict is edited INTO that row's own cell -- `research_log._parse` has no dedup by
           # id, so a second row would charge the batch twice (`MB16`, the defect that
           # overstated options N by four).
           "trials_already_booked": 8,
           "trials_charged_by_this_pass": 0,
           "trial_class": "EIGHT equity trials, booked at 89593a6 BEFORE any runner existed "
                          "(equity N 285 -> 293). The register landed ALONE at 4e92445, a strict "
                          "git ancestor of both.",
           "build_quadrant": qcen, "half_boundary": BUILD_HALF_SPLIT,
           "control": "the DEPLOYED COMPOSITE as one regressor (charter Stage 1a)",
           "control_themes": cols,
           "k": BH_K, "q": BH_Q,
           "k_stays_9_because": "membership was fixed in the draft before any outcome; shrinking "
                                "the denominator after withdrawing C9 would be choosing the "
                                "correction on the batch. Conservative direction.",
           "crit": CRIT,
           "crit_is": "UNCALIBRATED -- conventional. MB22/U2: an incremental IC t has NO "
                      "calibrated floor, so CORRECTED_FLOORS' theme-IC bar may not be quoted "
                      "beside these numbers (R1-VAR's category error).",
           "tier_governs": True,
           "arms": {}, "not_scored": {}}

    pvals = {}
    for arm in ORDER:
        k = (kills.get("arms") or {}).get(arm) or {}
        if not k.get("kill_passes"):
            why = ((k.get("detail") or {}).get("fails") or ["no kill record"])
            res["not_scored"][arm] = {"state": "NOT RUN", "why": why,
                                      "note": "its free pre-outcome kill fired; the bar does not "
                                              "move (W-28) and the arm is not re-attempted"}
            print("[arms] %s NOT RUN -- %s" % (arm, why), flush=True)
            continue

        print("[arms] building %s ..." % arm, flush=True)
        sig = builders[arm]()
        if arm == "C5":
            flat = {}
            for dd, per in sig.items():
                a = np.array([v[0] for v in per.values()], dtype=float)
                b = np.array([v[1] for v in per.values()], dtype=float)
                if a.std() == 0 or b.std() == 0:
                    continue
                za, zb = (a - a.mean()) / a.std(), (b - b.mean()) / b.std()
                flat[dd] = {t: float((za[i] + zb[i]) / 2.0) for i, t in enumerate(per.keys())}
            sig = flat

        col = "b3_%s" % arm.lower()
        attach(quad, sig, col)
        tier = tier_frame(quad)
        tier = tier[0] if isinstance(tier, tuple) else tier

        wide = score_ic_arm(quad, col, arm, "wide")
        tr = score_ic_arm(tier, col, arm, "tier")

        # THE TIER GOVERNS. A wide pass with a tier fail is REAL BUT NOT INVESTABLE HERE and does
        # not advance -- charter Stage 1b, and the label exists so the two readings cannot be
        # collapsed into whichever is kinder.
        #
        # **AND MY FIRST VERSION OF THIS TEST COULD NOT FIRE.** It compared against "SURVIVES",
        # a string `stage1_verdict` never returns -- its vocabulary is NOT_ASSESSABLE / CLEARS /
        # NOT_REPLICATED. So the charter's own Stage-1b label was DEAD CODE, and C4 is precisely
        # the case it exists for: wide CLEARS, tier NOT_REPLICATED. "A label that cannot fire" is
        # the family this record names over and over, and the only reason it surfaced is that an
        # arm finally exercised the branch. `PASS_VERDICT` is read from the shared module's own
        # vocabulary below rather than retyped here, so a future rename turns this red instead of
        # silently killing the branch again.
        gov = tr.get("verdict")
        if wide.get("verdict") == PASS_VERDICT and gov != PASS_VERDICT:
            gov = "REAL BUT NOT INVESTABLE HERE"
        res["arms"][arm] = {"wide": wide, "tier": tr, "governing_verdict": gov}
        p = (tr or {}).get("p_two_sided")
        if p is not None:
            pvals[arm] = p
        print("[arms] %s -> wide %s | tier %s | GOVERNING %s"
              % (arm, wide.get("verdict"), tr.get("verdict"), gov), flush=True)

    if pvals:
        # `benjamini_hochberg` takes a DICT `{name: p}`, not a list -- it calls `.items()`. My
        # first version passed a list comprehension and crashed AFTER every arm had been scored
        # and printed, which is the worst place to find a contract error: the numbers existed and
        # the artifact did not. Third time in this batch that calling a shared helper (which is
        # right, `B7`) went wrong because I did not read its signature first -- after
        # `composite_from_frame`'s standardiser argument and `costume_rho`'s column-name form.
        res["benjamini_hochberg"] = benjamini_hochberg(pvals, k=BH_K, q=BH_Q)
        res["bh_order"] = sorted(pvals, key=lambda a: pvals[a])
        res["bh_on"] = "the TIER's two-sided p per arm, because the tier governs"

    res["arms_scored"] = sorted(res["arms"])
    res["arms_not_scored"] = sorted(res["not_scored"])
    res["C8"] = "runs in its own pass (scripts/b3_c8.py) -- the expanding-window fit is expensive "
    res["C9"] = "NOT RUN -- register 0.1. k stays 9."
    # THE SAME VOCABULARY BUG, A SECOND TIME IN ONE FILE. This read `== "SURVIVES"`, which
    # `stage1_verdict` never returns, so it would have reported `False` on every run no matter
    # what the arms did -- a headline field that cannot be true. `PASS_VERDICT` is derived.
    res["any_arm_clears_on_the_governing_population"] = any(
        v["governing_verdict"] == PASS_VERDICT for v in res["arms"].values())
    res["arms_real_but_not_investable_here"] = sorted(
        a for a, v in res["arms"].items()
        if v["governing_verdict"] == "REAL BUT NOT INVESTABLE HERE")

    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, indent=1, default=str))
    print("\n-> %s" % args.out)
    print("   any arm CLEARS on the governing population: %s"
          % res["any_arm_clears_on_the_governing_population"])
    print("   REAL BUT NOT INVESTABLE HERE: %s"
          % (res["arms_real_but_not_investable_here"] or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
