# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 2d -- FF5+MOM loadings on BOTH universes. ZERO TRIALS.

`POOL-SIZE` measured that the wider-pool gain on `data/backtest` arrives as an **SMB switch**
(+0.08 -> +0.79 across the ladder) and called it a size bet rather than selection skill. If the
corrected universe's ladder reverses, the loadings are where that shows: either the size bet is
still there and simply stops paying, or it was never a size bet at all.

**IT CALLS `pool_size_factors.main` RATHER THAN RE-IMPLEMENTING THE REGRESSION** (`B7`). That
module was parameterised so every existing caller is bit-identical; this passes its own series,
its own panel and its own output path. The net series are READ from `UNIVERSE_BIAS_ARMS.json` --
the books are not re-formed, because a second path to the same series is exactly what `B7` is
about.

**NO ALPHA CLAIM.** `INDEX-CHOICE` forbade one in advance and `PREREG_pool_size.md` inherited
the prohibition; this inherits it again. An intercept here is a **decomposition**.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.pool_size_factors as PF                                    # noqa: E402


def main(argv=None) -> int:
    if not PF.FA:
        raise SystemExit("the licensed panel is absent")
    arms_path = os.path.join(PF.FA, "UNIVERSE_BIAS_ARMS.json")
    if not os.path.exists(arms_path):
        print("REFUSING: no arms artifact at %s; run scripts.universe_bias_arms first"
              % arms_path)
        return 2
    d = json.load(io.open(arms_path, encoding="utf-8"))

    for side in ("restricted", "full"):
        arms = d[side]["arms"]
        missing = [k for k, a in arms.items() if not a.get("net_series")]
        if missing:
            print("REFUSING: %s arms carry no net series (%r). Re-run "
                  "scripts.universe_bias_arms -- it banks the series so the books are not "
                  "re-formed here." % (side, missing))
            return 2
        panel = os.path.join(PF.FA, "UNIVERSE_BIAS_PANEL_%s.pkl" % side)
        print("\n=== %s ===" % side, flush=True)
        rc = PF.main(rungs=arms, panel_path=panel,
                     out=os.path.join(PF.FA, "UNIVERSE_BIAS_FACTORS_%s.json" % side),
                     order=list(arms.keys()), item="UNIVERSE-BIAS",
                     part="2d FF5+MOM loadings (%s)" % side, trials=0, require_c1=False)
        if rc:
            return rc
    print("\nFACTORS DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
