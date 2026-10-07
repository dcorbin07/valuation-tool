# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 2c -- the same book-composition census on BOTH universes. ZERO TRIALS.

A census: facts about what each book holds, no hypothesis and no bar (`S25` / `MB3` /
`MB1-SEL` class). It exists to say **why** the ladder reverses, and a census can only BLOCK an
interpretation of the ladder -- never produce one.

**IT CALLS `pool_size_diag.main` RATHER THAN RE-IMPLEMENTING IT** (`B7`): that module was
parameterised with `panel_path`/`out` defaulting to the banked panel, so every existing caller is
bit-identical and both sides here are measured by the same code against the same bucket lines.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.pool_size_diag as D                                        # noqa: E402


def main(argv=None) -> int:
    if not D.FA:
        raise SystemExit("the licensed panel is absent")
    for side in ("restricted", "full"):
        panel = os.path.join(D.FA, "UNIVERSE_BIAS_PANEL_%s.pkl" % side)
        if not os.path.exists(panel):
            print("REFUSING: no %s panel at %s; run scripts.universe_bias_arms first"
                  % (side, panel))
            return 2
        print("\n=== %s ===" % side, flush=True)
        rc = D.main(panel_path=panel,
                    out=os.path.join(D.FA, "UNIVERSE_BIAS_DIAG_%s.json" % side),
                    item="UNIVERSE-BIAS", part="2c book composition census (%s)" % side)
        if rc:
            return rc
    print("\nCENSUS DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
