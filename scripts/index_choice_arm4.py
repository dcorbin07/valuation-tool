# -*- coding: utf-8 -*-
"""`INDEX-CHOICE-ARM4` — arm 4's own robustness checks. Register `PREREG_index_choice_arm4.md`.

Don asked for *"arm 4's checks on 2009-2026 — the same 200 name-splits, halves, factors and
buildability that `INDEX-CHOICE` gave arms 2 and 3."*

**NOTHING HERE IS A NEW METHOD.** Every key, seed, count, control and scoring helper is
**IMPORTED** from the scripts `INDEX-CHOICE` already landed (`B7`, `MA5`). The only thing that
changes is which arm set is passed in.

**WHY THIS IS A SEPARATE SCRIPT RATHER THAN A FOURTH ENTRY IN `index_choice_split.CHOICE`.**
That tuple carries `INDEX-CHOICE`'s own **void condition 2** — *"No new arm. Arms 1, 2, 3 only;
arm 4 (the ceiling) is not carried into this item."* Adding arm 4 to it would have breached a
landed register's void condition **and** silently changed `INDEX_CHOICE_SPLIT.json`. It was the
obvious route and it is the wrong one. So the arm set became a **parameter whose default is the
original tuple** — inert for every existing caller by construction — and this script passes its
own.

**ARM 4 REMAINS A CEILING.** `PREREG_index_choice_arm4.md` §1 pre-commits that no figure here
promotes it to a fourth option for 2026-10-22. It has no liquidity screen of any kind, so it
holds names no account can transact; that was known before any number was read and is not
revisited on the strength of one.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
from scripts.r4_x1_accounting_universe import (K_SPLITS, SEED,            # noqa: E402
                                               _assert_split,
                                               stable_key_half)
# THE METHOD, imported wholesale. `_score_half` and `_shares` take the arm set as a parameter
# whose default is INDEX-CHOICE's own three; this module passes a different one and copies
# nothing.
from scripts.index_choice_split import (MIN_NAMES_PER_HALF, _score_half,  # noqa: E402
                                        _shares, _spy_ann)
from scripts.index_best import data_candidates, _data_root                # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "INDEX_CHOICE_ARM4.json") if FA else None

ARM4 = "4_all_cap_ceiling"
# The incumbent travels with it because the SECOND registered statistic is "positive vs the
# INCUMBENT on the SAME half". Dropping it would leave only the vs-SPY leg.
CHOICE4 = ("1_incumbent_10bn", ARM4)

# `INDEX-BEST`'s banked arm-4 figures, quoted so `C1` compares against the record rather than
# against this run's own output. Source: data/free_analysis/INDEX_BEST.json, arms[ARM4].
BANKED_ROTH_NET_ANN = 0.24950546311372124


def c1_reproduces_index_best(fa):
    """GATE. The arm-4 figures this run is about must be the ones `INDEX-BEST` banked.

    The COUNT of compared leaves is gated non-zero: `MB21`'s `C1` once scored a perfect
    0.000e+00 on an empty frame by comparing nothing, and a control that passes by looking at
    nothing is worse than no control.
    """
    p = os.path.join(fa, "INDEX_BEST.json")
    if not os.path.exists(p):
        return {"ok": False, "reason": "INDEX_BEST.json absent at %s" % p, "compared": 0}
    d = json.load(io.open(p, encoding="utf-8"))
    arm = (d.get("arms") or {}).get(ARM4)
    if not isinstance(arm, dict):
        return {"ok": False, "reason": "INDEX_BEST.json carries no %s arm" % ARM4,
                "compared": 0}
    checks, worst = {}, 0.0
    for k, want in (("roth_net_ann", BANKED_ROTH_NET_ANN),):
        got = arm.get(k)
        if got is None:
            return {"ok": False, "reason": "banked arm is missing %r" % k, "compared": 0}
        dev = abs(float(got) - float(want))
        checks[k] = {"banked": float(got), "quoted": float(want), "abs_dev": dev}
        worst = max(worst, dev)
    # carried for the record, not compared to a retyped literal (MA5: do not restate a constant)
    for k in ("annual_turnover", "realised_one_way_bps", "net_sharpe", "max_drawdown"):
        if arm.get(k) is not None:
            checks[k] = {"banked": float(arm[k])}
    return {"ok": worst == 0.0 and len(checks) > 0, "max_abs_dev": worst,
            "compared": len(checks), "checks": checks}


def main(argv=None) -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))

    gate = c1_reproduces_index_best(FA)
    print("C1 reproduce INDEX-BEST's banked arm 4: ok=%s  max_abs_dev=%s  compared=%d"
          % (gate["ok"], gate.get("max_abs_dev"), gate["compared"]), flush=True)
    if not gate["ok"]:
        print("REFUSING: %s" % gate.get("reason", "C1 did not reproduce"), flush=True)
        json.dump({"item": "INDEX-CHOICE-ARM4", "c1": gate, "arms_scored": False},
                  io.open(OUT, "w", encoding="utf-8"), indent=2)
        return 2

    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    universe = sorted(panel["ticker"].unique())
    print("panel %s | %d names | arms %s" % (panel.shape, len(universe), list(CHOICE4)),
          flush=True)

    res = {
        "item": "INDEX-CHOICE-ARM4",
        "trials": 1,
        "register": "PREREG_index_choice_arm4.md",
        "arm": ARM4,
        "arm_is_a_ceiling_not_an_option": True,
        "method_source": "scripts/index_choice_split.py -- _score_half, _shares and _spy_ann "
                         "IMPORTED with the arm set passed as a parameter; "
                         "scripts/r4_x1_accounting_universe.py -- stable_key_half, SEED, "
                         "K_SPLITS, _assert_split IMPORTED, not retyped",
        "seed": SEED, "k_splits": K_SPLITS, "min_names_per_half": MIN_NAMES_PER_HALF,
        "c1": gate,
        "scope_limit": "layers 1-2 are computed once over the FULL universe and are not rebuilt "
                       "per half, so every figure is a LOWER BOUND on total name-selection "
                       "uncertainty (X1's own limit, inherited twice over)",
        "period_limit": "all half-books use the SAME 69 dates, so this settles WHICH NAMES and "
                        "says nothing about WHICH PERIOD; INDEX-BEST found every arm's "
                        "advantage concentrated in the late half and that is untouched",
        "full_universe_spy_ann": _spy_ann(panel),
    }

    # ---- the STABLE split: X1's own key, no seed ----
    a = [t for t in universe if stable_key_half(t) == 0]
    b = [t for t in universe if stable_key_half(t) == 1]
    _assert_split(a, b, universe)
    print("stable split: %d / %d" % (len(a), len(b)), flush=True)
    stable = [_score_half(panel, h, cols, weights, choice=CHOICE4) for h in (a, b)]
    stable = [h for h in stable if h]
    res["stable_split"] = {
        "halves": len(stable), "sizes": [h["n_names"] for h in stable],
        "shares": _shares(stable, choice=CHOICE4),
        "per_half": [{"n_names": h["n_names"], "spy_ann": h["spy_ann"],
                      "arms": {k: v["roth_ann"] for k, v in h["arms"].items()}}
                     for h in stable],
    }
    s = res["stable_split"]["shares"][ARM4]
    print("  %-20s roth med %.4f | vs SPY +%d/%d | vs incumbent +%d/%d"
          % (ARM4, s["roth_ann"]["median"],
             round(s["vs_spy"]["share_positive"] * len(stable)), len(stable),
             round(s["vs_incumbent"]["share_positive"] * len(stable)), len(stable)), flush=True)

    # ---- the 100 SEEDED random splits ----
    rng = np.random.default_rng(SEED)
    halves, skipped = [], 0
    for i in range(K_SPLITS):
        perm = list(rng.permutation(universe))
        mid = len(perm) // 2
        x, y = sorted(perm[:mid]), sorted(perm[mid:])
        _assert_split(x, y, universe)
        for h in (x, y):
            sc = _score_half(panel, h, cols, weights, choice=CHOICE4)
            if sc is None:
                skipped += 1
                continue
            halves.append(sc)
        if (i + 1) % 10 == 0:
            print("  split %d/%d, %d half-books" % (i + 1, K_SPLITS, len(halves)), flush=True)

    res["random_splits"] = {"k": K_SPLITS, "half_books": len(halves), "skipped": skipped,
                            "shares": _shares(halves, choice=CHOICE4)}
    r = res["random_splits"]["shares"][ARM4]
    print("\n%s over %d half-books:" % (ARM4, len(halves)))
    print("  roth_ann        min %.4f  p05 %.4f  median %.4f  max %.4f"
          % (r["roth_ann"]["min"], r["roth_ann"]["p05"], r["roth_ann"]["median"],
             r["roth_ann"]["max"]))
    print("  vs SPY          positive on %.4f of half-books, min %+.4f"
          % (r["vs_spy"]["share_positive"], r["vs_spy"]["min"]))
    print("  vs incumbent    positive on %.4f of half-books, min %+.4f"
          % (r["vs_incumbent"]["share_positive"], r["vs_incumbent"]["min"]))

    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2)
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
