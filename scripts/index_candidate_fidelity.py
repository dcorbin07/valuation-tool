# -*- coding: utf-8 -*-
"""INDEX-CANDIDATE -- does the shipped candidate builder produce INDEX-BEST's arm-2 book?

THE QUESTION. `INDEX-CHOICE` settled "if you move, move to arm 2" and left "move at all?" to
Don. So arm 2 has to exist as something an operator can BUILD on 2026-10-22, and the thing worth
proving about it is not that it runs -- it is that the book it writes is the book that was
MEASURED. A construction that is 95% of the measured one carries a measured return it does not
have, and nothing downstream could tell.

WHAT IS PROVED, AND WHAT THAT IS WORTH.

  1. `trim_universe` MOVED out of `served_index_book.book_fn` and the move is INERT: arm 2's
     whole 69-date chain reproduces `INDEX_BEST.json`'s banked `roth_net_ann`, `annual_turnover`
     and `realised_one_way_bps` at max |delta| 0.000e+00. This is the load-bearing gate. If the
     shared trim changed anything, every figure below would be describing a different book while
     looking fine.
  2. The book `build_candidate` writes for the panel's LAST date is NAME-FOR-NAME the book the
     backtest formed at that date, at the same weights.
  3. (2) IS NEAR-TAUTOLOGICAL BY DELEGATION AND IS STILL THE POINT. Both paths call the same
     `trim_universe` and the same `build_index`, so exactness is what SHOULD happen -- that is
     precisely the claim: the shipped builder is the measured construction and not a lookalike.
     A number that cannot fail proves nothing, so it is checked for VACUITY two ways: the book
     must be non-empty and of the banked size, and a PERTURBED candidate (universe_rank 1400,
     a 6.7% change) must FAIL to reproduce it. If the perturbation still reproduces, the
     comparison is not looking at the universe at all and the run refuses.
  4. An INDEPENDENT reading against the artifact rather than against this run: the eligible tier
     and the book size at that date must sit inside `INDEX_BEST.json`'s banked ranges.

ONE ASYMMETRY IS REPORTED RATHER THAN SMOOTHED. In the BACKTEST the universe is "the top 1,500
or all of them where fewer exist" -- the artifact's `eligible_tier.min` is 1471, so early
cross-sections genuinely are smaller. `build_candidate` REFUSES below 1,500 instead, because for
a one-shot operator build a short universe means an incomplete export, and a silently smaller
"top 1500" is the exact failure this item exists to prevent. The two therefore differ on the
early dates, which is why the fidelity date is the LAST one and why the count of affected dates
is printed instead of being left to be discovered.

NOTHING HERE ADOPTS ANYTHING. No book is written to `data/valquo_index.json`, `TRACKED_CONFIG`
is untouched, and the candidate is not default on any path.

    python -m scripts.index_candidate_fidelity
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

# EVERYTHING IS IMPORTED FROM THE THING THAT MEASURED IT (`B7`, `MA5`). The arm's knobs come out
# of `index_best.ARMS` rather than being retyped here -- retyping them is how a fidelity check
# comes to certify a construction nobody ran.
from scripts.index_best import ARMS, FA, data_candidates                   # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT             # noqa: E402
from valuation.studies import served_index_book as IB                      # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                        # noqa: E402
from valuation.edge import valquo_index as VI                              # noqa: E402
from valuation.edge.fundamental_panel import after_tax_backtest as at_bt   # noqa: E402

CANDIDATE = "liquid-decile"
ARM = "2_liquid_decile"
PERTURBED_RANK = 1400          # 6.7% off; must break the comparison or the comparison is blind


def _arm_kw(name):
    for nm, kw, _label, _b in ARMS:
        if nm == name:
            return dict(kw)
    raise RuntimeError("no arm %r in index_best.ARMS" % (name,))


def _norm(d):
    tot = sum(d.values()) or 1.0
    return {k: v / tot for k, v in d.items()}


def main() -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    banked_p = os.path.join(FA, "INDEX_BEST.json")
    if not os.path.exists(banked_p):
        raise SystemExit("INDEX_BEST.json is absent at %s -- nothing to be faithful to" % banked_p)
    with open(banked_p, encoding="utf-8") as f:
        banked = json.load(f)["arms"][ARM]

    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    kw = _arm_kw(ARM)
    print("panel %s | %d dates | arm %s knobs %s"
          % (panel.shape, panel["date"].nunique(), ARM, kw), flush=True)

    # --- replay arm 2's whole chain through the MEASURED driver, recording every date -------
    base = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    seen = []

    def _rec(sub, comp, held):
        out = base(sub, comp, held)
        seen.append({"sub": sub, "comp": comp, "held": set(held), "book": out})
        return out

    roth = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=_rec,
                 short_rate=0.0, long_rate=0.0, return_series=True)
    cen = IB.run(panel, cols, weights, weighting="score", exit_frac=BAND_WIDTH, **kw)

    # --- (1) THE INERTNESS GATE. The trim moved; the measurement must not have. -------------
    gate = {
        "roth_net_ann": (roth["after_tax_ann"], banked["roth_net_ann"]),
        "annual_turnover": (cen["annual_turnover"], banked["annual_turnover"]),
        "realised_one_way_bps": (cen["realised_one_way_bps"], banked["realised_one_way_bps"]),
    }
    dev = {k: abs(a - b) for k, (a, b) in gate.items()}
    gate_ok = all(v == 0.0 for v in dev.values())
    print("GATE trim_universe is inert: %s"
          % " ".join("%s %.3e" % (k, v) for k, v in dev.items()), flush=True)
    if not gate_ok:
        print("REFUSING: the shared universe trim moved a landed figure. Nothing below is read.")
        return 2
    if not seen:
        print("REFUSING: the book hook never ran, so there is nothing to compare (vacuous).")
        return 2
    print("  dates recorded: %d (panel has %d)" % (len(seen), panel["date"].nunique()), flush=True)

    # --- the asymmetry, counted rather than described ---------------------------------------
    short = sum(1 for s in seen if len(IB.scan_rows(s["sub"], s["comp"])) < kw["universe_rank"])
    print("  dates whose cross-section is smaller than the %d-name universe: %d "
          "(the backtest trims to what exists; build_candidate REFUSES)"
          % (kw["universe_rank"], short), flush=True)

    # --- (2) the LAST date, built both ways -------------------------------------------------
    last = seen[-1]
    rows = IB.scan_rows(last["sub"], last["comp"])
    # THE MEASURED SIDE IS TAKEN AS `book_fn` RETURNED IT AND IS NOT RE-NORMALISED. `book_fn`
    # already divides by the book's own total, so normalising again divides by ~1.0 and the
    # round-off of that no-op was the whole residual: the first run of this script read
    # max |dw| 1.735e-18 -- one ulp on a 0.0067 weight -- against a gate that demands
    # 0.000e+00. The fix is to apply the SAME normalisation ONCE to each side rather than to
    # loosen the gate to a tolerance; a tolerance here is exactly what would let an invented
    # number through, which is the defect `index_best.py`'s own gate literals hit.
    measured = {k: float(v) for k, v in last["book"].items()}
    built = VI.build_candidate(rows, CANDIDATE, held=last["held"] or None)
    shipped = _norm({p["ticker"]: float(p["weight"]) for p in built["positions"]})

    inter = set(measured) & set(shipped)
    union = set(measured) | set(shipped)
    overlap = len(inter) / (len(union) or 1)
    wmax = max((abs(measured[t] - shipped[t]) for t in inter), default=None)
    print("LAST DATE: measured %d names | built %d names | overlap %.4f | max |dw| %s"
          % (len(measured), len(shipped),
             overlap, "n/a" if wmax is None else "%.3e" % wmax), flush=True)
    exact = (set(measured) == set(shipped)) and (wmax is not None and wmax == 0.0)

    # --- (3) VACUITY: size, and a perturbation that must break it --------------------------
    bs = banked["book_size"]
    size_ok = bs["min"] <= len(shipped) <= bs["max"] and len(shipped) >= 100
    et = banked["eligible_tier"]
    tier = built["candidate"]["eligible_tier"]
    tier_ok = et["min"] <= tier <= et["max"]
    print("  artifact check: book %d in [%d, %d] -> %s | eligible tier %d in [%d, %d] -> %s"
          % (len(shipped), bs["min"], bs["max"], size_ok,
             tier, et["min"], et["max"], tier_ok), flush=True)

    pert = dict(VI.INDEX_CANDIDATES[CANDIDATE])
    pert["universe_rank"] = PERTURBED_RANK
    saved = VI.INDEX_CANDIDATES[CANDIDATE]
    VI.INDEX_CANDIDATES[CANDIDATE] = pert
    try:
        pb = VI.build_candidate(rows, CANDIDATE, held=last["held"] or None)
    finally:
        VI.INDEX_CANDIDATES[CANDIDATE] = saved
    pw = _norm({p["ticker"]: float(p["weight"]) for p in pb["positions"]})
    p_over = len(set(pw) & set(measured)) / (len(set(pw) | set(measured)) or 1)
    pert_bites = p_over < 1.0
    print("  NON-VACUITY: universe_rank %d -> %d gives overlap %.4f (must be < 1.0000) -> %s"
          % (kw["universe_rank"], PERTURBED_RANK, p_over, pert_bites), flush=True)

    # --- the free route is refused, and the refusal is exercised rather than asserted -------
    try:
        VI.export(candidate_name=CANDIDATE, path=os.devnull, data_dir=None)
        free_refused = False
    except RuntimeError as e:
        free_refused = "NOT buildable by the free live route" in str(e)
    print("  free route refused by name: %s" % free_refused, flush=True)

    ok = bool(gate_ok and exact and size_ok and tier_ok and pert_bites and free_refused)
    out = {
        "candidate": CANDIDATE, "arm": ARM,
        "gate_trim_universe_inert": {k: {"run": a, "banked": b, "abs_dev": dev[k]}
                                     for k, (a, b) in gate.items()},
        "last_date": str(last["sub"]["date"].iloc[0]),
        "n_measured": len(measured), "n_built": len(shipped),
        "name_overlap": overlap, "name_sets_identical": set(measured) == set(shipped),
        "max_abs_weight_deviation": wmax, "exact": exact,
        "dates_short_of_the_universe": short,
        "eligible_tier": tier, "banked_eligible_tier": et, "banked_book_size": bs,
        "non_vacuity": {"perturbed_universe_rank": PERTURBED_RANK,
                        "overlap": p_over, "bites": pert_bites},
        "free_route_refused": free_refused,
        "adopted": False, "default": False, "published": False,
        "pass": ok,
    }
    dest = os.path.join(FA, "INDEX_CANDIDATE_FIDELITY.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print("\n%s -> %s" % ("PASS" if ok else "FAIL", dest), flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
