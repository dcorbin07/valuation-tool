# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 2a — a FULL-UNIVERSE 2009-2026 export. ZERO TRIALS.

The point of this item is to vary **one** thing: the universe. So the export is cut at the SAME
date `data/backtest` reaches (**2026-10-02**, both now coming from the 2026-10 freeze), and it is
built from the **same raw tables**. Then:

  * **restricted** = `data/backtest` — the top-3,000-by-2026-cap universe the published panel
    uses;
  * **full** = this export — every name with an in-window close and SF1 coverage.

Holding the vintage fixed is what makes the pair a pair. Comparing a fresh full-universe panel
against the **banked** `panel_corrected_69d.pkl` would conflate the universe with a rolled
window, which is the confound `SHARADAR-REFRESH` measured (2,531 names at 2026-07-24 against
3,049 at 2026-10-02).

**IT REUSES `pool_size_oos_prep`'s FUNCTIONS RATHER THAN COPYING THEM** (`B7`): the SEP, SF1 and
SFP readers are the same code, with only the cutoff and the output root differing. A second copy
of an export writer is how two panels come to be built on quietly different rules.

**The benchmark comes from SFP**, because SEP is equities and SPY is a fund — the lesson
`pool_size_oos_prep` learned when the builder refused a full-universe export with no benchmark.
"""
from __future__ import annotations

import io
import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.pool_size_oos_prep as P                                    # noqa: E402

#: `data/backtest`'s own newest close, so restricted and full share a vintage exactly.
CUT = "2026-10-02"
#: the window the published panel covers; a name must trade inside it to be in the universe.
WINDOW_FROM = "2009-01-01"


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    raw = os.path.join(data, "backtest_freeze_2026-10", "raw")
    if not os.path.isdir(raw):
        print("REFUSING: no raw freeze at %s" % raw)
        return 2

    root = os.path.join(data, "full2009", "backtest")
    os.makedirs(root, exist_ok=True)

    # The shared readers are parameterised by module constants, so they are set for this run
    # rather than copied. Restored afterwards so a later import of the OOS prep is unaffected.
    old_cut, old_from = P.CUT, P.WINDOW_FROM
    P.CUT, P.WINDOW_FROM = CUT, WINDOW_FROM
    try:
        print("preparing a FULL-UNIVERSE export cut at %s (window from %s) -> %s"
              % (CUT, WINDOW_FROM, root), flush=True)
        print("  fundamentals (SF1 ARQ) ...", flush=True)
        f = P.prep_fundamentals(raw, os.path.join(root, "fundamentals.csv"))
        print("    %s" % json.dumps(f), flush=True)
        print("  prices (SEP closeadj) ...", flush=True)
        pr = P.prep_prices(raw, os.path.join(root, "prices"))
        print("    %s" % json.dumps(pr), flush=True)
        print("  benchmark (SFP -- SPY is a FUND and is not in SEP) ...", flush=True)
        b = P.prep_benchmark(raw, os.path.join(root, "prices"))
        print("    %s" % json.dumps(b), flush=True)
    finally:
        P.CUT, P.WINDOW_FROM = old_cut, old_from

    res = {"item": "UNIVERSE-BIAS", "part": "2a full-universe export prep", "trials": 0,
           "cut": CUT, "window_from": WINDOW_FROM, "export_root": root,
           "fundamentals": f, "prices": pr, "benchmark": b,
           "readers": "scripts/pool_size_oos_prep.py -- prep_prices, prep_fundamentals and "
                      "prep_benchmark REUSED, not copied (B7)",
           "vintage_note": "cut at data/backtest's own newest close so the restricted and full "
                           "universes share a vintage exactly; comparing against the BANKED "
                           "panel instead would conflate the universe with a rolled window "
                           "(SHARADAR-REFRESH: 2,531 names at 2026-07-24 vs 3,049 at "
                           "2026-10-02)",
           "bulk_reused": "data/bulk/prepared -- already full-universe; NOT rebuilt and NOT "
                          "overwritten"}
    fa = os.path.join(data, "free_analysis")
    json.dump(res, io.open(os.path.join(fa, "UNIVERSE_BIAS_PREP.json"), "w", encoding="utf-8"),
              indent=2)
    print("\nwrote %s" % os.path.join(fa, "UNIVERSE_BIAS_PREP.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
