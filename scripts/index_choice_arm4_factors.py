# -*- coding: utf-8 -*-
"""`INDEX-CHOICE-ARM4`, the factor leg. Register `PREREG_index_choice_arm4.md` §2.

`INDEX-CHOICE`'s own decomposition is CALLED, not copied: `index_choice_factors.main` takes the
arm set and the output path as parameters whose defaults are that item's own, so this module
changes neither its behaviour nor its artifact.

**NO ALPHA CLAIM.** `INDEX-CHOICE` forbade one in advance — the arms are not separable from each
other and the whole effect is late-half — and §3 of this item's register inherits that
prohibition verbatim rather than re-arguing it. A positive intercept here is a DECOMPOSITION.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts import index_choice_factors as F                             # noqa: E402
from scripts.index_choice_arm4 import ARM4, CHOICE4, c1_reproduces_index_best  # noqa: E402


def main(argv=None) -> int:
    if not F.FA:
        raise SystemExit("the licensed panel is absent")

    # the SAME gate the split leg uses -- arm 4's figures must be the ones INDEX-BEST banked
    gate = c1_reproduces_index_best(F.FA)
    print("C1 reproduce INDEX-BEST's banked arm 4: ok=%s compared=%d"
          % (gate["ok"], gate["compared"]), flush=True)
    if not gate["ok"]:
        print("REFUSING: %s" % gate.get("reason", "C1 did not reproduce"))
        return 2

    out = os.path.join(F.FA, "INDEX_CHOICE_ARM4_FACTORS.json")
    assert out != F.OUT, "arm 4 must not write INDEX-CHOICE's own artifact"
    return F.main(choice=CHOICE4, out=out, item="INDEX-CHOICE-ARM4",
                  part="factor loadings for the ceiling arm (%s)" % ARM4,
                  register="PREREG_index_choice_arm4.md section 2")


if __name__ == "__main__":
    sys.exit(main())
