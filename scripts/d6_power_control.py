# -*- coding: utf-8 -*-
"""D6 POWER CONTROL — added by the EXECUTOR and declared as a departure from the register.

WHY IT EXISTS. The Stage-2 instruction is explicit: *"If the design cannot resolve at the coverage
you measure, say so and report UNINTERPRETABLE rather than scoring a null that means 'could not
see it.'"* `PREREG_d6_analyst_revisions.md`'s C1-C6 contain no power control, so this is an
addition and is recorded as one rather than folded in silently.

IT CAN ONLY BLOCK, NEVER PRODUCE (`MB1-SEL`). Its only two possible effects are to leave the
verdict REJECTED or to downgrade it to UNINTERPRETABLE. It cannot turn a null into a finding, so
it adds no degree of freedom to any published claim and charges NO TRIAL.

THE RULE IS `MA58`'s. Score the panel's own KNOWN-REAL signals on **the rows the arm is actually
measured on** — not on the panel, and not on the covered dates across all names. `MA31`/`MA32`
measured that `U2`'s power control was computed on a WIDER population than `U2`'s arms and so
overstated the power they had; that correction is inherited here rather than repeated.

THE HONEST LIMIT SHIPS WITH IT, and it is `MB18`'s: **there is no valid INCREMENTAL power control
on this template at all.** Every known-real signal here is already an INPUT to an incumbent theme,
so residualising removes it by construction — `MB18` measured the same anchors scoring incremental
*t* of +1.55 and +0.26 for exactly that reason. So this control establishes that the RAW channel
resolves on these rows; the bound on the INCREMENTAL statistic is the MDE, which travels with the
verdict.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import incremental_ic as IIC              # noqa: E402
from valuation.studies import revisions as REV                   # noqa: E402
from valuation.studies.surface_stock import arm_ic               # noqa: E402
from scripts.d6_revisions import _build, _panel, OUT_DIR, IC_BAR  # noqa: E402

#: `MA58`'s and `MB18`'s own anchors, and the bar they were read against there.
ANCHORS = ("z_gp_on_capital", "z_ret_6_1", "z_fcf_margin")
ANCHOR_BAR = 2.0


def main() -> int:
    p = _build(_panel())
    present = [c for c in ANCHORS if c in p.columns]
    print("anchors present on the panel:", present)

    out: dict = {"anchor_bar": ANCHOR_BAR, "arm_bar": IC_BAR, "bases": {}}
    for basis in ("six", "seven"):
        inc = list(IIC.basis_for(basis))
        ed = list(IIC.effective_dates(p, REV.SIGNAL_COL, inc))
        # THE ROWS THE ARM IS MEASURED ON: effective dates AND the candidate non-null, which is
        # what `residualise`'s dropna enforces inside `arm_ic`.
        rows = p[p["date"].isin(set(ed)) & p[REV.SIGNAL_COL].notna()].copy()
        blk = {"n_dates": len(ed), "rows_on_arm_population": int(len(rows)), "anchors": {}}
        print("\nBASIS %s -- %d dates, %d rows on the arm's own population"
              % (basis, len(ed), len(rows)))
        for a in present:
            r = arm_ic(rows, a, ed, inc)
            t = r["raw_ic_tstat"]
            blk["anchors"][a] = {
                "raw_median_ic": r["raw_median_ic"], "raw_ic_tstat": t,
                "clears_anchor_bar": bool(t is not None and abs(t) >= ANCHOR_BAR),
                "clears_arm_bar": bool(t is not None and abs(t) >= IC_BAR)}
            print("   %-18s raw median IC %+.6f  raw t %+.4f   clears %.1f: %-3s  clears %.2f: %s"
                  % (a, r["raw_median_ic"] or float("nan"), t or float("nan"), ANCHOR_BAR,
                     "YES" if blk["anchors"][a]["clears_anchor_bar"] else "no", IC_BAR,
                     "YES" if blk["anchors"][a]["clears_arm_bar"] else "no"))
        blk["design_resolves_at_anchor_bar"] = any(
            v["clears_anchor_bar"] for v in blk["anchors"].values())
        blk["design_resolves_at_arm_bar"] = any(
            v["clears_arm_bar"] for v in blk["anchors"].values())
        out["bases"][basis] = blk

    resolves = all(out["bases"][b]["design_resolves_at_arm_bar"] for b in out["bases"])
    out["consequence"] = (
        "REJECTED STANDS. A known-real signal clears the arm's OWN calibrated bar on the arm's "
        "OWN rows, on both bases, so the null is INTERPRETABLE and is not 'could not see it'."
        if resolves else
        "DOWNGRADE TO UNINTERPRETABLE. No known-real signal clears on these rows, so the arm's "
        "null means 'not measurable here' and never 'absent' -- MA58's outcome.")
    out["limit"] = ("This establishes the RAW channel resolves. There is NO valid INCREMENTAL "
                    "power control on this template (MB18): every known-real signal is already an "
                    "input to an incumbent, so residualisation removes it by construction. The "
                    "bound on the incremental statistic is the MDE, quoted with the verdict.")
    print("\nCONSEQUENCE FOR THE LABEL: " + out["consequence"])
    path = os.path.join(OUT_DIR, "D6_POWER_CONTROL.json")
    json.dump(out, open(path, "w"), indent=1, default=str)
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
