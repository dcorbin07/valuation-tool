# -*- coding: utf-8 -*-
"""`CORRECTED-FLOORS` part 1b -- A CORRECTION AGAINST MY OWN PART 1, AND IT IS SUBSTANTIVE.

    python -m scripts.corrected_deployed

**THE DEFECT.** Part 1 reported the "corrected headline" against each corrected floor. Those
headline figures are `UNIVERSE-BIAS` part 2's `corrected` column, which `placebo.py`'s real
iteration reproduces to sixteen digits -- so the harness control was sound and the floors are
sound. **What neither item said is WHICH COMPOSITE those figures describe.**

`placebo.py` mirrors `run_backtests`: CPCV is the authority, and **on the corrected universe CPCV
ADOPTS** (`ic-proportional`, the first time this project has ever adopted). So the landed
corrected figures are the **ADOPTED-WEIGHTS** book. **The DEPLOYED book -- flat 1/7, never tuned,
which is what ships -- is a different object on this universe, and it was not measured.**

Measured here: deployed top-decile alpha is **0.06067443460377794** against the landed
**0.02825480485561374** -- **more than double**. Found by the gate in part 2a refusing the
corrected panel for a reason I first mistook for the gate working as designed.

**THE DIRECTION IS THE SURPRISE AND IT IS WORTH MORE THAN THE NUMBER.** `X7`'s standing warning is
that CPCV adoption produces an *optimistically* biased headline, because the weights are chosen on
the panel the headline is then measured on. **Here adoption makes the headline look WORSE**, and
the mechanism is visible: CPCV selects on out-of-sample rank IC inside its decide folds, not on
alpha, so a scheme can win that contest and lose alpha.

**SO THE CORRECTED UNIVERSE NEEDS TWO READINGS, NOT ONE, AND EACH AGAINST ITS OWN MATCHED NULL.**

* The **ADOPTED** reading against the FULL null, in which 16 of 100 draws also adopt. That is the
  shipped pipeline against itself and it is what part 1 reported. It stands.
* The **DEPLOYED** (flat 1/7) reading against the **NON-ADOPTING SUB-NULL** -- the 84 draws that
  kept base weights. `MB8`'s rule is that an `se` may not be borrowed across constructions, and
  `S22` built exactly such a `fixed_weights_null` for the same reason: a floor whose draws adopt
  is not the floor for a book that does not.

Both sub-nulls come from the SAME retained draws (rule 9 paying for itself -- no re-sweep), and
the 84-draw count travels with every figure read off it.

**ZERO TRIALS.** A correction to a calibration is still a calibration. **ADOPTS NOTHING, CHANGES
NO PUBLIC PAGE.**
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.corrected_floors as CF                                       # noqa: E402



def out_path():
    """Resolved on CALL -- see `corrected_floors.fa`."""
    return os.path.join(CF.fa(), "CORRECTED_DEPLOYED.json")

#: the floors and their tails, X7's own -- IMPORTED, not re-listed (`B7`).
FLOORS = CF.FLOORS

#: a p95 over fewer draws than this is set by its largest one or two values.
MIN_SUBNULL_DRAWS = 40


def deployed_statistics(panel_path):
    """The DEPLOYED composite's own figures: flat 1/7 via `_base_weights`, CPCV never consulted.

    `quantile_backtest` is CALLED (`B7`) -- the same function `placebo.py` and `run_backtests`
    call, so the only thing that differs from the adopted reading is the weight vector.
    """
    import pandas as pd
    from valuation.edge import fundamental_panel as FP
    from valuation.screener import settings as S
    panel = pd.read_pickle(panel_path)
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in panel.columns and panel[c].notna().any()]
    base = FP._base_weights(cols, "established")
    qb = FP.quantile_backtest(panel, cols, base, n_q=10, horizon=63) or {}
    themes = FP.theme_ic(panel) or {}
    themes = themes.get("themes") if isinstance(themes.get("themes"), dict) else themes
    t_abs = [abs(v["ic_tstat"]) for v in themes.values()
             if isinstance(v, dict) and v.get("ic_tstat") is not None]
    return {
        "weights": {k: v for k, v in base.items()},
        "nonzero_themes": sorted(k for k, v in base.items() if v),
        "top_decile_alpha": qb.get("top_decile_alpha"),
        "top_decile_alpha_tstat_nw": qb.get("top_decile_alpha_tstat_nw"),
        "long_short_tstat": qb.get("long_short_tstat"),
        "long_short_tstat_nw": qb.get("long_short_tstat_nw"),
        "long_short_ann": qb.get("long_short_ann"),
        "monotonicity": qb.get("monotonicity"),
        "n_periods": qb.get("n_periods"),
        "max_abs_theme_ic_t": (max(t_abs) if t_abs else None),
        "pbo": None,
        "deflated_sharpe": None,
        "pbo_and_dsr_are": "DELIBERATELY None -- both come out of `cpcv_validate`, and the "
                           "DEPLOYED reading is the one that does NOT consult CPCV. Reporting "
                           "the adopted run's PBO beside flat-weight alpha would pair a "
                           "numerator from one construction with a denominator from another, "
                           "which is MA19's own recurring defect and MB8's rule.",
    }


def subnull(sweep, adopting):
    """Percentiles over the draws that DID or did NOT adopt, from the retained draws.

    No re-sweep: rule 9 kept all 100, so splitting them is arithmetic. The count travels with
    every figure, because a p95 over a thin split is set by its largest values.
    """
    rows = [d for d in sweep["draws"] if bool(d.get("cpcv_adopt")) == adopting]
    out = {"n": len(rows), "adopting": adopting}
    for key, _label, pct, _dirn in FLOORS:
        vals = [d.get(key) for d in rows]
        vals = [float(v) for v in vals if v is not None and v == v]
        if len(vals) < 2:
            out[key] = None
            continue
        out[key] = float(np.percentile(vals, 5 if pct == "p05" else 95))
    return out


#: the figures `UNIVERSE-BIAS` part 2 tabulates, mapped to the sweep/quantile_backtest keys that
#: carry them, so the like-for-like row is read off that item's own artifact and not re-typed.
LIKE_FOR_LIKE = (
    ("construction.top_decile_alpha", "top_decile_alpha", "top-decile alpha"),
    ("construction.top_decile_alpha_tstat_nw", "top_decile_alpha_tstat_nw",
     "top-decile alpha HAC t"),
    ("construction.long_short_tstat", "long_short_tstat", "long-short naive t"),
    ("construction.long_short_tstat_nw", "long_short_tstat_nw", "long-short HAC t"),
    ("construction.long_short_ann", "long_short_ann", "long-short /yr"),
    ("construction.monotonicity", "monotonicity", "monotonicity"),
)


def like_for_like(dep):
    """Part 2's PUBLISHED column (deployed) against the corrected DEPLOYED reading.

    Part 2 compared its published column against its corrected one, and those are DIFFERENT
    CONSTRUCTIONS -- deployed flat 1/7 against CPCV-adopted `ic-proportional`. This is the
    comparison that holds the construction fixed and varies only the universe, which is what
    part 2 set out to measure.
    """
    p = os.path.join(CF.fa(), "UNIVERSE_BIAS_PUBLIC.json")
    with io.open(p, encoding="utf-8") as fh:
        figs = {r["payload_path"]: r for r in json.load(fh)["figures"]}
    out = []
    for path, key, label in LIKE_FOR_LIKE:
        r = figs.get(path)
        if r is None:
            continue
        pub, ad, cd = r["published"], r["corrected"], dep.get(key)
        out.append({
            "figure": label, "payload_path": path,
            "published_DEPLOYED": pub,
            "corrected_DEPLOYED": cd,
            "corrected_ADOPTED_as_part2_reported": ad,
            "d_universe_like_for_like": (None if pub is None or cd is None else cd - pub),
            "d_as_part2_reported": (None if pub is None or ad is None else ad - pub),
        })
    return out


def main(argv=None):
    sweep = CF.read_sweep()
    panel_path = sweep["panel"]
    if not os.path.exists(panel_path):
        raise SystemExit("REFUSING: the sweep's own panel is not on disk at %s" % panel_path)

    print("panel %s" % os.path.basename(panel_path), flush=True)
    dep = deployed_statistics(panel_path)
    adopted = sweep["real"]
    print("\n=== THE TWO READINGS OF THE CORRECTED UNIVERSE", flush=True)
    print("  deployed themes (%d): %s" % (len(dep["nonzero_themes"]),
                                          ", ".join(dep["nonzero_themes"])), flush=True)
    print("  %-28s %-22s %-22s" % ("", "ADOPTED (ic-proportional)", "DEPLOYED (flat 1/7)"),
          flush=True)
    pairs = []
    for key, label, pct, dirn in FLOORS:
        a, b = adopted.get(key), dep.get(key)
        pairs.append((key, label, pct, dirn, a, b))
        print("  %-28s %-22s %-22s"
              % (label, ("%.6f" % a) if a is not None else "-",
                 ("%.6f" % b) if b is not None else "-"), flush=True)

    full = {k: v for k, v in ((key, (sweep["null"].get(key) or {}).get(pct))
                              for key, _l, pct, _d in FLOORS)}
    non = subnull(sweep, adopting=False)
    yes = subnull(sweep, adopting=True)
    print("\n=== THE MATCHED NULLS  (same retained draws, split on whether CPCV adopted)",
          flush=True)
    print("  full null n=%d | non-adopting n=%d | adopting n=%d"
          % (sweep["n_draws"], non["n"], yes["n"]), flush=True)

    thin = non["n"] < MIN_SUBNULL_DRAWS
    rows = []
    print("\n  %-28s %-11s %-11s %-11s  %s"
          % ("floor", "FULL null", "NON-ADOPT", "deployed", "verdict"), flush=True)
    for key, label, pct, dirn, a, b in pairs:
        f_full, f_non = full.get(key), non.get(key)
        v_dep = CF.clears(b, f_non, dirn)
        v_ad = CF.clears(a, f_full, dirn)
        rows.append({
            "key": key, "floor": label, "percentile": pct, "direction": dirn,
            "adopted_value": a, "deployed_value": b,
            "floor_full_null": f_full, "floor_non_adopting_null": f_non,
            "floor_adopting_null": yes.get(key),
            "adopted_clears_full_null": v_ad,
            "deployed_clears_non_adopting_null": v_dep,
        })
        print("  %-28s %-11s %-11s %-11s  deployed -> %s   (adopted -> %s)"
              % (label,
                 ("%.6f" % f_full) if f_full is not None else "-",
                 ("%.6f" % f_non) if f_non is not None else "-",
                 ("%.6f" % b) if b is not None else "-",
                 {True: "CLEARS", False: "FAILS", None: "n/a"}[v_dep],
                 {True: "CLEARS", False: "FAILS", None: "n/a"}[v_ad]), flush=True)

    lfl = like_for_like(dep)
    print("\n=== LIKE FOR LIKE -- deployed to deployed, universe the only thing varying",
          flush=True)
    print("  %-26s %-13s %-13s %-11s   %s"
          % ("figure", "published", "corrected", "delta", "as part 2 reported it"), flush=True)
    for r in lfl:
        print("  %-26s %-13s %-13s %-11s   %s (delta %s)"
              % (r["figure"],
                 ("%.6f" % r["published_DEPLOYED"]) if r["published_DEPLOYED"] is not None
                 else "-",
                 ("%.6f" % r["corrected_DEPLOYED"]) if r["corrected_DEPLOYED"] is not None
                 else "-",
                 ("%+.6f" % r["d_universe_like_for_like"])
                 if r["d_universe_like_for_like"] is not None else "-",
                 ("%.6f" % r["corrected_ADOPTED_as_part2_reported"])
                 if r["corrected_ADOPTED_as_part2_reported"] is not None else "-",
                 ("%+.6f" % r["d_as_part2_reported"])
                 if r["d_as_part2_reported"] is not None else "-"), flush=True)

    res = {
        "item": "CORRECTED-FLOORS",
        "part": "1b -- a CORRECTION against my own part 1: which composite the corrected "
                "headline describes",
        "trials": 0,
        "trial_class": "CALIBRATION -- a correction to a calibration is still a calibration. "
                       "No hypothesis, no bar chosen here, no second arm.",
        "adopts_nothing": True,
        "changes_no_public_page": True,
        "the_correction": (
            "Part 1 reported a 'corrected headline' against each corrected floor without saying "
            "WHICH COMPOSITE those figures describe. placebo.py mirrors run_backtests, so CPCV "
            "is the authority -- and on the corrected universe CPCV ADOPTS (ic-proportional), "
            "the first adoption in this project's history. The landed corrected figures are "
            "therefore the ADOPTED-weights book. The DEPLOYED book -- flat 1/7, never tuned, "
            "which is what ships -- is a DIFFERENT object on this universe and was not "
            "measured. Its top-decile alpha is %r against the landed %r, more than double. "
            "The floors themselves are unaffected and part 1's harness control was sound; what "
            "was missing is the label on the numerator."
            % (dep["top_decile_alpha"], adopted.get("top_decile_alpha"))),
        "the_direction_is_the_surprise": (
            "X7's standing warning is that CPCV adoption produces an OPTIMISTICALLY biased "
            "headline, because the weights are chosen on the panel the headline is then "
            "measured on. Here adoption makes the headline look WORSE, and the mechanism is "
            "visible: CPCV selects on out-of-sample rank IC inside its decide folds, not on "
            "alpha, so a scheme can win that contest and lose alpha."),
        "panel": panel_path,
        "deployed": dep,
        "adopted": {k: adopted.get(k) for k, _l, _p, _d in FLOORS},
        "nulls": {"full": full, "non_adopting": non, "adopting": yes,
                  "why_split": "MB8: an se may not be borrowed across constructions, and S22 "
                               "built a fixed_weights_null for exactly this reason. A floor "
                               "whose draws adopt is not the floor for a book that does not. "
                               "Both splits come from the SAME retained draws -- rule 9 paying "
                               "for itself, no re-sweep."},
        "rows": rows,
        "like_for_like": lfl,
        "like_for_like_is": (
            "UNIVERSE-BIAS part 2's PUBLISHED column is the DEPLOYED flat-1/7 book -- cpcv.adopt "
            "is false on the canonical run -- and its CORRECTED column is the ADOPTED book. "
            "Comparing those two is a numerator from one construction against a numerator from "
            "another, which is MA19's own recurring defect and MB8's rule. This row holds the "
            "CONSTRUCTION fixed and varies only the UNIVERSE, which is what part 2 set out to "
            "measure."),
    }
    if thin:
        res["THIN_SUBNULL"] = ("the non-adopting sub-null carries %d draws, below the %d this "
                               "item requires; its percentiles are set by too few values to be "
                               "read as floors" % (non["n"], MIN_SUBNULL_DRAWS))
    dest = out_path()
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print("\nwrote %s" % dest, flush=True)
    if thin:
        print("*** THIN SUB-NULL -- %d draws ***" % non["n"], flush=True)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
