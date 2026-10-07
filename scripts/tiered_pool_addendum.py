# -*- coding: utf-8 -*-
"""`TIERED-POOL` addendum — §5's required reporting, §3's diagnostic, and the MDEs. ZERO TRIALS.

Register `PREREG_tiered_pool.md` §5 makes an arm's verdict **VOID** if the size-exposure
reporting is omitted, so this is not optional output: **the SMB loading, the intercept and the
share of book weight below $2B** are what stop a size bet being read as selection.

**§3 OF MY OWN REGISTER IS DEGENERATE, AND THAT IS REPORTED RATHER THAN REPAIRED.** It specifies
the size-neutral diagnostic as *"rank within each band and select the same count per band as arm
A … i.e. a pure within-band sort"* — **which is arm A.** Arm A's percentile is already taken
within band and within date, so the diagnostic as written is the same construction, and the
identity is **measured here rather than asserted**. `E-3`'s `K3` precedent: a control that is
structurally absent on the arm's own rows is reported `STRUCTURALLY ABSENT`, not quietly swapped
for a different control — swapping it **after** seeing the arms would be choosing a design on the
outcome, which is the thing the register exists to prevent.

What a NON-degenerate version would be is named and **NOT run**: equalising the three bands'
**weight** (1/3 each) rather than letting score-weighting across the union hand most of the book
to the largest band. That isolates within-band selection from the cross-band weight mix, it is a
different construction, and it needs its own register.

**`pool_size_factors.main` IS CALLED, NOT COPIED** (`B7`): parameterised with
`rungs`/`panel_path`/`out`/`order` defaulting to `POOL-SIZE`'s own objects, so every existing
caller is bit-identical.

**NO ALPHA CLAIM** — inherited from `INDEX-CHOICE`. An intercept is a **DECOMPOSITION**. **No X7
floor is quoted**; every critical value is **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`).
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

import scripts.tiered_pool as TP                                              # noqa: E402
import scripts.pool_size_factors as PF                                        # noqa: E402
from scripts.tiered_pool_run import (PERIODS, INCUMBENT_KW, _weight_below,    # noqa: E402
                                     TP_live, _hist)
from scripts.index_best import _data_root, data_candidates                    # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT                # noqa: E402


def main(argv=None) -> int:
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")
    arms_path = os.path.join(fa, "TIERED_POOL.json")
    if not os.path.exists(arms_path):
        print("REFUSING: no arms artifact at %s; run scripts.tiered_pool_run --arms first"
              % arms_path)
        return 2
    A = json.load(io.open(arms_path, encoding="utf-8"))

    res = {"item": "TIERED-POOL", "part": "addendum -- s5 reporting, s3 diagnostic, MDEs",
           "trials": 0, "register": "PREREG_tiered_pool.md sections 3 and 5",
           "no_alpha_claim": "inherited from INDEX-CHOICE; an intercept is a DECOMPOSITION",
           "section_3_status": "DEGENERATE BY CONSTRUCTION -- see module docstring; the "
                               "diagnostic as REGISTERED is arm A, because arm A's percentile is "
                               "already within band and within date. Reported, not swapped "
                               "(E-3's K3 precedent).",
           "size_neutral_verdict": "NO-VERDICT",
           "periods": {}}

    from scripts.pool_size import _roth

    for label, pkl, exp, themes, _note in PERIODS:
        panel = pd.read_pickle(os.path.join(fa, pkl))
        want = list(themes or DEPLOYED)
        cols, _dead = TP_live(panel, want)
        weights = {c: BASE_WEIGHT for c in cols}
        arms = A["periods"][label]["arms"]
        out = {"factors": None, "composition": {}, "mde": {}, "size_neutral": None}

        # ---- §5: FF5+MOM on every arm that ran, via POOL-SIZE's own machinery -------------
        rungs = {k: {"net_series": v["net_series"]} for k, v in arms.items()
                 if v and v.get("net_series")}
        if rungs:
            fout = os.path.join(fa, "TIERED_POOL_FACTORS_%s.json" % label)
            print("\n=== factors / %s ===" % label, flush=True)
            PF.main(rungs=rungs, panel_path=os.path.join(fa, pkl), out=fout,
                    order=list(rungs.keys()), item="TIERED-POOL",
                    part="FF5+MOM loadings (%s)" % label, trials=0, require_c1=False)
            out["factors"] = fout

        # ---- §5: the share of BOOK WEIGHT below $2B and $300M, for EVERY arm --------------
        print("\n=== composition / %s ===" % label, flush=True)
        kws = {"0_incumbent_10bn": dict(INCUMBENT_KW),
               "A_tiered": {"index_fn": TP.tiered_index_fn(), "large_cap_min": 0.0}}
        if arms.get("B_tiered_junk"):
            hist = _hist(os.path.join(data, *exp))
            okbd = {}
            for d in sorted(panel["date"].unique()):
                g = panel[panel["date"] == d]
                as_of = str(d)[:10]
                okbd[as_of], _ = TP.junk_ok(list(g["ticker"]), hist, as_of)
            kws["B_tiered_junk"] = {"index_fn": TP.tiered_index_fn(),
                                    "universe_filter": TP.junk_universe_filter(okbd),
                                    "large_cap_min": 0.0}
        for name, kw in kws.items():
            c = _weight_below(panel, cols, weights, kw)
            out["composition"][name] = c
            wb = c["weight_below"]
            print("  %-16s under $2bn mean %.4f max %.4f | under $300M mean %.4f | book %s"
                  % (name, wb.get("2000M", {}).get("mean", float("nan")),
                     wb.get("2000M", {}).get("max", float("nan")),
                     wb.get("300M", {}).get("mean", float("nan")), c["book_size"]), flush=True)

        # ---- §1.5: every margin ships with its own MDE -----------------------------------
        inc = (arms.get("0_incumbent_10bn") or {}).get("net_series")
        for arm in ("A_tiered", "B_tiered_junk"):
            s = (arms.get(arm) or {}).get("net_series")
            if not (inc and s):
                continue
            n = min(len(inc), len(s))
            out["mde"][arm] = TP.mde([float(s[i]) - float(inc[i]) for i in range(n)])
            m = out["mde"][arm]
            print("  MDE %-16s paired mean %+.6f  se %.6f  MDE80 %.6f"
                  % (arm, m["paired_mean"], m["paired_se"], m["mde_80pc"]), flush=True)

        # ---- §3: the diagnostic, and the DEGENERACY measured rather than asserted --------
        sn = _roth(panel, cols, weights,
                   {"index_fn": TP.size_neutral_index_fn(), "large_cap_min": 0.0})
        if sn:
            a = arms.get("A_tiered") or {}
            dev = (None if a.get("roth_net_ann") is None
                   else abs(float(sn["roth_net_ann"]) - float(a["roth_net_ann"])))
            sn.pop("net_series", None)
            sn.pop("gross_series", None)
            sn["verdict"] = "NO-VERDICT"
            sn["degenerate_vs_arm_A"] = {
                "max_abs_dev_roth": dev,
                "identical": (None if dev is None else bool(dev == 0.0)),
                "why": "arm A's percentile is ALREADY within band and within date, so the "
                       "diagnostic as REGISTERED is the same construction. Measured, not "
                       "asserted. E-3's K3 precedent: reported STRUCTURALLY DEGENERATE rather "
                       "than swapped for a different control after seeing the arms.",
                "non_degenerate_version_NOT_run": "equalise the three bands' WEIGHT (1/3 each) "
                                                  "instead of score-weighting across the union; "
                                                  "a different construction, needs its own "
                                                  "register",
            }
            out["size_neutral"] = sn
            print("  size-neutral (NO VERDICT) roth %.4f | |dev| vs arm A %s"
                  % (sn["roth_net_ann"], ("%.3e" % dev) if dev is not None else "n/a"),
                  flush=True)

        res["periods"][label] = out

    json.dump(res, io.open(os.path.join(fa, "TIERED_POOL_ADDENDUM.json"), "w",
                           encoding="utf-8"), indent=2, default=str)
    print("\nwrote %s" % os.path.join(fa, "TIERED_POOL_ADDENDUM.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
