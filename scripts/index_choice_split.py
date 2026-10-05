# -*- coding: utf-8 -*-
"""INDEX-CHOICE item 1 -- do the arms' advantages survive a NAME split? Executes
PREREG_index_choice.md section 1. 2 of the item's 3 equity trials, booked at 2d2b7a6.

WHY A NAME SPLIT IS THE RIGHT TEST HERE, and it is Don's own framing: every held-out gate this
project owns splits by DATE, which conflates "does the signal generalise" with "does the PERIOD
generalise". `INDEX-BEST` found EVERY arm's advantage carried by the late half -- so a date split
cannot distinguish a real construction difference from a late-period one. A universe split has
no time-period confound at all, which is why `X1` is the record's strongest positive result.

EVERY KEY IS IMPORTED FROM `X1`, NEVER RETYPED (`B7`, `MA5`), AND THAT IS ALSO THE BLINDNESS
ARGUMENT: `stable_key_half`, `SEED`, `K_SPLITS` and `_assert_split` were all fixed in August,
before arms 2 and 3 existed, so no split here can have been chosen to flatter one of them.

`X1`'s SCOPE LIMIT CARRIES OVER VERBATIM: layers 1-2 of the panel are computed once over the
full universe and are NOT rebuilt per half, so every figure here is a LOWER BOUND on total
name-selection uncertainty.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import served_index_book as IB                     # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                       # noqa: E402
from valuation.edge.fundamental_panel import (after_tax_backtest as at_bt,  # noqa: E402
                                              composite_from_frame)
from valuation.screener.cross_sectional import zscore                     # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
# X1's OWN construction, seed, split count and per-split control -- imported, not restated.
from scripts.r4_x1_accounting_universe import (K_SPLITS, SEED,            # noqa: E402
                                               _assert_split,
                                               stable_key_half)
from scripts.index_best import (ARMS, PER_YEAR, _ann, data_candidates,    # noqa: E402
                                _data_root)

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "INDEX_CHOICE_SPLIT.json") if FA else None
# `X1`'s own floor, scaled to a half: it required 400 names per half of a 2,531-name universe.
MIN_NAMES_PER_HALF = 400
# Only the three arms Don is choosing between. Arm 4 (the ceiling) is NOT carried in -- void
# condition 2.
CHOICE = ("1_incumbent_10bn", "2_liquid_decile", "3_liquid_top25")


def _roth(panel, cols, weights, kw):
    """Net-of-cost, no-tax annualised return, from the SAME lot path `INDEX-BEST` used -- rates
    set to zero is the Roth arm, not a second implementation."""
    bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    r = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
              short_rate=0.0, long_rate=0.0, return_series=True)
    if not isinstance(r, dict) or r.get("after_tax_ann") is None:
        return None
    return {"roth_ann": float(r["after_tax_ann"]), "net_series": list(r["series"]["net"]),
            "n_periods": int(r["n_periods"])}


def _spy_ann(panel):
    xs = [float(panel[panel["date"] == d]["bench_ret"].iloc[0])
          for d in sorted(panel["date"].unique())]
    return _ann(xs)


def _score_half(panel, names, cols, weights, choice=CHOICE):
    """All three arms on one half universe. The universe trim and the cross-sectional
    standardisation are both REBUILT WITHIN THE HALF, because each is a property of the
    population -- scoring a half against full-universe z-scores would measure neither.

    `choice` DEFAULTS TO THIS ITEM'S OWN THREE ARMS, so every existing caller is bit-identical
    and `INDEX-CHOICE`'s void condition 2 ("arm 4 is not carried into this item") is untouched.
    It is a parameter rather than a constant so that `INDEX-CHOICE-ARM4` can run THE SAME method
    on a different arm set without a second copy of it (`B7`) -- the pattern `S3-I1` used when it
    made the append-only writer's key a parameter instead of letting the fleet grow its own.
    ADDING ARM 4 TO THE TUPLE ITSELF WOULD HAVE BREACHED THAT VOID CONDITION and silently
    changed a landed artifact; it was the obvious route and it is the wrong one."""
    sub = panel[panel["ticker"].isin(names)]
    if sub["ticker"].nunique() < MIN_NAMES_PER_HALF:
        return None
    out = {"n_names": int(sub["ticker"].nunique()), "n_rows": int(len(sub)),
           "spy_ann": _spy_ann(sub), "arms": {}}
    for name, kw, _label, _b in ARMS:
        if name not in choice:
            continue
        r = _roth(sub, cols, weights, kw)
        if r is None:
            return None
        out["arms"][name] = r
    return out


def _shares(halves, choice=CHOICE):
    """The reported statistics, both of them: positive vs SPY, and positive vs the INCUMBENT on
    the SAME half. Two statistics, which is why this item charges two trials (`X1`'s rule).

    `choice` defaults to this item's own arms -- see `_score_half` for why it is a parameter."""
    res = {}
    for name in choice:
        vs_spy = [h["arms"][name]["roth_ann"] - h["spy_ann"] for h in halves]
        vs_inc = [h["arms"][name]["roth_ann"] - h["arms"]["1_incumbent_10bn"]["roth_ann"]
                  for h in halves]
        lv = [h["arms"][name]["roth_ann"] for h in halves]
        res[name] = {
            "n_half_books": len(halves),
            "roth_ann": {"min": float(np.min(lv)), "p05": float(np.percentile(lv, 5)),
                         "median": float(np.median(lv)), "p95": float(np.percentile(lv, 95)),
                         "max": float(np.max(lv))},
            "vs_spy": {"share_positive": float(np.mean([x > 0 for x in vs_spy])),
                       "median": float(np.median(vs_spy)),
                       "p05": float(np.percentile(vs_spy, 5)),
                       "min": float(np.min(vs_spy))},
            "vs_incumbent": {"share_positive": float(np.mean([x > 0 for x in vs_inc])),
                             "median": float(np.median(vs_inc)),
                             "p05": float(np.percentile(vs_inc, 5)),
                             "min": float(np.min(vs_inc))},
        }
    # The incumbent against itself is identically zero by construction. Reported as a CONTROL
    # rather than dropped: a non-zero value would mean the pairing is not per-half.
    res["control_incumbent_vs_itself_is_zero"] = bool(
        all(abs(h["arms"]["1_incumbent_10bn"]["roth_ann"]
                - h["arms"]["1_incumbent_10bn"]["roth_ann"]) == 0.0 for h in halves))
    return res


def main() -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    universe = sorted(panel["ticker"].unique())
    print("panel %s | %d names | arms %s" % (panel.shape, len(universe), list(CHOICE)),
          flush=True)

    res = {"item": "INDEX-CHOICE", "part": "1 name split", "trials": 2,
           "register": "PREREG_index_choice.md section 1",
           "method_source": "scripts/r4_x1_accounting_universe.py -- stable_key_half, SEED, "
                            "K_SPLITS and _assert_split IMPORTED, not retyped",
           "seed": SEED, "k_splits": K_SPLITS,
           "scope_limit": "layers 1-2 are computed once over the FULL universe and are not "
                          "rebuilt per half, so every figure is a LOWER BOUND on total "
                          "name-selection uncertainty (X1's own limit, carried over)",
           "full_universe_spy_ann": _spy_ann(panel)}

    # ---- the STABLE split: X1's own key, no seed, reproducible from the ticker list ----
    a = [t for t in universe if stable_key_half(t) == 0]
    b = [t for t in universe if stable_key_half(t) == 1]
    _assert_split(a, b, universe)
    print("stable split: %d / %d" % (len(a), len(b)), flush=True)
    stable = [_score_half(panel, h, cols, weights) for h in (a, b)]
    stable = [h for h in stable if h]
    res["stable_split"] = {"halves": len(stable), "sizes": [h["n_names"] for h in stable],
                           "shares": _shares(stable),
                           "per_half": [{"n_names": h["n_names"], "spy_ann": h["spy_ann"],
                                         "arms": {k: v["roth_ann"]
                                                  for k, v in h["arms"].items()}}
                                        for h in stable]}
    for k in CHOICE:
        s = res["stable_split"]["shares"][k]
        print("  %-20s roth med %.4f | vs SPY +%d/2 | vs incumbent +%d/2"
              % (k, s["roth_ann"]["median"],
                 round(s["vs_spy"]["share_positive"] * len(stable)),
                 round(s["vs_incumbent"]["share_positive"] * len(stable))), flush=True)

    # ---- the 100 SEEDED random splits, X1's seed and count ----
    rng = np.random.default_rng(SEED)
    halves, skipped = [], 0
    for i in range(K_SPLITS):
        perm = list(rng.permutation(universe))
        mid = len(perm) // 2
        x, y = sorted(perm[:mid]), sorted(perm[mid:])
        _assert_split(x, y, universe)
        for h in (x, y):
            sc = _score_half(panel, h, cols, weights)
            if sc is None:
                skipped += 1
                continue
            halves.append(sc)
        if (i + 1) % 20 == 0:
            print("  ... %d/%d splits (%d half-books)" % (i + 1, K_SPLITS, len(halves)),
                  flush=True)
    res["random_splits"] = {"k_splits": K_SPLITS, "half_books": len(halves),
                            "skipped_below_floor": skipped,
                            "min_names_per_half": MIN_NAMES_PER_HALF,
                            "shares": _shares(halves)}
    print("\nrandom splits: %d half-books (%d skipped below the %d-name floor)"
          % (len(halves), skipped, MIN_NAMES_PER_HALF), flush=True)
    for k in CHOICE:
        s = res["random_splits"]["shares"][k]
        print("  %-20s roth med %.4f [p05 %.4f] | vs SPY %.1f%% positive (med %+.4f, p05 %+.4f) "
              "| vs incumbent %.1f%% positive (med %+.4f, p05 %+.4f)"
              % (k, s["roth_ann"]["median"], s["roth_ann"]["p05"],
                 100 * s["vs_spy"]["share_positive"], s["vs_spy"]["median"], s["vs_spy"]["p05"],
                 100 * s["vs_incumbent"]["share_positive"], s["vs_incumbent"]["median"],
                 s["vs_incumbent"]["p05"]), flush=True)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, default=str)
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
