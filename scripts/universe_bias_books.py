# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 3 -- `INDEX-BOOK` and `N1`'s band book against both universes. ZERO TRIALS.

Both are already `INDEX-BOOK`-class **DESCRIPTIONS** with no hypothesis, no bar and no second
arm, logged at zero trials for `INDEX-BOOK`'s own stated reason -- *"re-measuring a KNOWN
construction on a KNOWN panel selects nothing"*. Re-measuring the same construction on a
**corrected** panel selects nothing either (the `S25` / `X7RECON` / `PANEL-EXT-RECHECK`
correction class), so this charges nothing.

**BOTH SCRIPTS ARE CALLED, NOT COPIED** (`B7`), each parameterised with `panel_path`/`out`
defaulting to the banked panel and its own artifact so every existing caller is bit-identical.

**AND THE HEADLINE OF THIS FILE IS THAT `INDEX-BOOK` REFUSES, CORRECTLY.** Its pre-committed
`C1` requires the panel to reproduce the *published* top-decile alpha
`0.07174142332098163`, and a **2026-10** panel is not the object the record describes, so C1
fires and the script aborts. **That refusal is not weakened here and must not be** -- a fidelity
gate that is repointed so it stops comparing against the banked figure is not a fidelity gate.
What the refusal buys is free and is the measurement this item most needed: C1 prints the
reproduced value, so the **vintage effect on the headline is read off a gate rather than
estimated.**

The Index book's own figures on both universes therefore come from `UNIVERSE-BIAS` part 2, whose
arm 1 **is** this construction (the $10B tier, score-weighted, 8% cap, 0.30 band, quarterly) and
whose C1 reproduced three banked `INDEX-BEST` rungs at max absolute deviation 0.000e+00.

**N1 CARRIES A COVERAGE HAZARD THAT MUST BE MEASURED RATHER THAN ASSUMED.** Its band is
*cap < $5B AND ADV > $5M*, and the ADV inputs were built on the **restricted** universe. On the
corrected universe a name with **no ADV observation at all** fails *ADV > $5M* exactly as a
genuinely illiquid name does -- so the band would quietly become *"small AND present in the old
ADV input"*, which is the incumbent universe wearing the corrected universe's name. Coverage is
therefore measured FIRST, at both name and cell level, and against the inputs' **real shapes**:
`MC9_SEP_ADV.pkl` is a `{"census", "by_ticker"}` **dict of raw SEP bars**, not a frame, and
`B13_ADV_PANEL.pkl` is a long frame. A probe that assumed a frame for both returned a confident
**0.0000 on both sides** -- a check that could not answer the question, answering it anyway.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# DEFERRED, and not as a style preference. `served_index_book` computes
# `DATA = _data_root()` at MODULE level with `required` defaulting to True, so importing it
# RAISES wherever the licensed `data/` is absent -- which is every CI runner. A module-level
# import here made this file unimportable in CI, and the test that reads `coverage` errored
# rather than running. Importing inside `main` is the pattern the sibling runners already use.
SIDES = ("restricted", "full")

#: `INDEX-BOOK`'s own published reference, quoted so the vintage delta its gate exposes is
#: computed against the record rather than against a remembered figure.
PUBLISHED_TOP_DECILE_ALPHA = 0.07174142332098163


def adv_inputs(fa):
    """Return (names_with_bars, cell_keys) from the ADV inputs, read at their REAL shapes."""
    names = set()
    p = os.path.join(fa, "MC9_SEP_ADV.pkl")
    if os.path.exists(p):
        d = pd.read_pickle(p)
        if isinstance(d, dict):
            names |= {str(t).upper() for t in (d.get("by_ticker") or {})}
    cells = set()
    p = os.path.join(fa, "B13_ADV_PANEL.pkl")
    if os.path.exists(p):
        a = pd.read_pickle(p)
        if isinstance(a, pd.DataFrame) and {"date", "ticker"} <= set(a.columns):
            cells = {(str(d)[:10], str(t).upper()) for d, t in zip(a["date"], a["ticker"])}
            names |= {t for _d, t in cells}
    return names, cells


def coverage(panel, names, cells):
    pt = {str(t).upper() for t in panel["ticker"]}
    keys = {(str(d)[:10], str(t).upper()) for d, t in zip(panel["date"], panel["ticker"])}
    return {"panel_names": len(pt), "names_with_adv_input": len(pt & names),
            "name_share": len(pt & names) / max(1, len(pt)),
            "panel_cells": len(keys), "cells_in_crsp_adv": len(keys & cells),
            "cell_share": len(keys & cells) / max(1, len(keys))}


def main(argv=None) -> int:
    import scripts.served_index_book as IBK
    import scripts.n1_band_book as N1
    if not IBK.FA:
        raise SystemExit("the licensed panel is absent")
    fa = IBK.FA
    names, cells = adv_inputs(fa)
    print("ADV inputs: %d names with SEP bars or a CRSP ADV row, %d CRSP (date,ticker) cells"
          % (len(names), len(cells)), flush=True)

    panels = {}
    for side in SIDES:
        pp = os.path.join(fa, "UNIVERSE_BIAS_PANEL_%s.pkl" % side)
        if not os.path.exists(pp):
            print("REFUSING: no %s panel at %s; run scripts.universe_bias_arms first"
                  % (side, pp))
            return 2
        panels[side] = pp

    cov = {}
    for side in SIDES:
        cov[side] = coverage(pd.read_pickle(panels[side]), names, cells)
        c = cov[side]
        print("  %-11s names %4d of %4d = %.4f | CRSP cells %6d of %6d = %.4f"
              % (side, c["names_with_adv_input"], c["panel_names"], c["name_share"],
                 c["cells_in_crsp_adv"], c["panel_cells"], c["cell_share"]), flush=True)

    res = {"item": "UNIVERSE-BIAS", "part": "3 INDEX-BOOK and N1 against both universes",
           "trials": 0,
           "class": "DESCRIPTION re-measured on a corrected universe -- no hypothesis, no bar, "
                    "no second arm; INDEX-BOOK's own zero-trial reasoning (S25 / X7RECON class)",
           "adv_coverage": cov,
           "adv_caveat": "N1's band is cap < $5B AND ADV > $5M, and the ADV inputs were built on "
                         "the RESTRICTED universe. On the corrected universe a name with NO ADV "
                         "observation fails the band exactly as a genuinely illiquid name does, "
                         "so a corrected N1 band is NOT like-for-like. Read it against the "
                         "coverage above.",
           "ran": {}}

    for side in SIDES:
        for name, mod, stem in (("index_book", IBK, "UNIVERSE_BIAS_INDEX_BOOK"),
                                ("n1_band_book", N1, "UNIVERSE_BIAS_N1_BAND")):
            out = os.path.join(fa, "%s_%s.json" % (stem, side))
            lab = ("data/backtest universe, 2026-10 vintage" if side == "restricted"
                   else "CORRECTED full raw universe, 2026-10 vintage")
            key = "%s_%s" % (name, side)
            print("\n=== %s / %s ===" % (name, side), flush=True)
            try:
                rc = mod.main(panel_path=panels[side], out=out, label=lab)
                res["ran"][key] = {"ok": rc == 0, "rc": rc, "out": out}
            except SystemExit as e:
                # A REFUSAL IS A RECORD, NOT A CRASH -- and `SystemExit` is not an `Exception`,
                # so catching only `Exception` let the first refusal kill the whole runner.
                res["ran"][key] = {"ok": False, "refused": str(e)}
                print("  REFUSED: %s" % e, flush=True)
            except Exception as e:
                res["ran"][key] = {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
                print("  RAISED: %s: %s" % (type(e).__name__, e), flush=True)

    json.dump(res, io.open(os.path.join(fa, "UNIVERSE_BIAS_BOOKS.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\nBOOKS DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
