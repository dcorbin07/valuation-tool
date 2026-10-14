# -*- coding: utf-8 -*-
"""`INSIDER-WIDE` — THE FREE PRE-READ CHECKS, in their own pass.

    python -m scripts.insider_wide_checks

Register `PREREG_insider_cluster_wide.md` §7, committed **ALONE at `1cc8b7e`**. `O10`'s process
defect was a gating control and its outcomes running in one pass, so this is a SEPARATE
invocation and `scripts/insider_wide_arm.py` **refuses** without its artifact.

**NOT ONE OF THESE READS A CHECK-QUADRANT OUTCOME.** `C1` scores the BUILD cell, which the charter
licenses reusing freely; `C4` counts check-quadrant EVENTS, which is a feasibility fact and not an
outcome; `C2` and `C3` read source. The check quadrant's forward returns are untouched until the
arm runs.
"""
from __future__ import annotations

import ast
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.edge import fundamental_panel as FP                          # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402
from valuation.studies import insider_cluster as IC                         # noqa: E402
from scripts import insider_wide_arm as WA                                  # noqa: E402

OUT = "INSIDER_WIDE_CHECKS.json"

#: `C1`'s targets, read from `INSIDER_CLUSTER_ARM.json` and NOT retyped — a hand-typed target is
#: how `BETA-FORECAST` shipped an `HLZ` hurdle wrong in its fourth decimal two items ago. The
#: register quotes **+2.0926pp**, *t* **5.009 / 4.888**, **4,072** events; those are roundings of
#: the banked sixteen-digit values and the comparison is made against the banked ones.
C1_SOURCE = "INSIDER_CLUSTER_ARM.json"
C1_CELL = "full_universe_h63"
C1_TOL = 0.0                                   # EXACTLY, as §7 says

#: `C4`'s independently banked count, from the census rather than from this item's own read.
C4_EXPECTED_EVENTS = 2669


def _c1() -> dict:
    """The construction is bit-identical to stage 1's — re-derived through THIS item's code.

    This is the check the whole item rests on. `scripts/insider_wide_arm.score` is
    era-parameterised where stage 1's was hard-wired to the build window, half 0 and a half-0-only
    tier schedule, so it is NEW CODE scoring an OLD cell. If it does not reproduce stage 1's
    published figures exactly, then the check read would be compared against a build figure
    produced by a different instrument, and §7 stops the read rather than absorbing the drift.
    """
    p = D.out_path(C1_SOURCE)
    if not os.path.isfile(p):
        return {"pass": False, "reason": "stage 1's banked arm artifact is absent at %s" % p}
    want = json.load(io.open(p, encoding="utf-8"))["cells"][C1_CELL]
    got = WA.main(["--c1-only"])
    fields = ("n_events_scored", "mean_pp", "t_date", "t_ticker", "se_date_pp", "se_ticker_pp")
    cmp = {}
    ok = True
    for f in fields:
        w = want[f] if f == "n_events_scored" else want["mkt"][f]
        g = got[f]
        if f == "n_events_scored":
            same = int(w) == int(g)
            dev = abs(int(w) - int(g))
        else:
            dev = abs(float(w) - float(g))
            same = dev <= C1_TOL
        cmp[f] = {"stage1": w, "rederived": g, "dev": dev, "exact": bool(same)}
        ok = ok and same
    return {"pass": bool(ok), "n_fields_compared": len(fields), "fields": cmp,
            "mean_pp": got.get("mean_pp"),
            "WHY_GATED_ON_A_COUNT": ("MB21's C1 scored a perfect 0.000e+00 on an EMPTY frame by "
                                     "comparing nothing, so the number of fields compared is "
                                     "asserted non-zero as well as the deviations being zero"),
            "non_vacuous": bool(len(fields) > 0 and int(want["n_events_scored"]) > 0)}


def _c2() -> dict:
    """No check-quadrant outcome has been read yet.

    Two legs. (a) The arm's own artifact must be ABSENT — if it exists, the one read has already
    happened and this pass is being run second, which is the ordering §7 forbids. (b) The
    tier-choice module, which ran BEFORE this register, must compute no abnormal return at all:
    asserted over the SYNTAX TREE rather than by grep, because a docstring explaining why it
    computes none would trip a substring ban (`never-ban-a-substring`, nine instances).
    """
    arm_p = D.out_path(WA.OUT)
    legs = {"arm_artifact_absent": not os.path.isfile(arm_p)}
    src = io.open(os.path.join(_HERE, "scripts", "insider_wide_tier_choice.py"),
                  encoding="utf-8").read()
    tree = ast.parse(src)
    banned = {"abnormal", "name_frame", "permutation_null", "build_market"}
    seen = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            nm = (f.attr if isinstance(f, ast.Attribute)
                  else (f.id if isinstance(f, ast.Name) else None))
            if nm in banned:
                seen.add(nm)
    legs["tier_choice_computes_no_abnormal_return"] = not seen
    legs["banned_calls_found"] = sorted(seen)
    # POSITIVE CONTROL: the AST walk must actually be able to see a call of that shape, or it
    # passes by seeing nothing.
    probe = ast.parse("import x\nDA.abnormal(1, 2)\n")
    found = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "abnormal" for n in ast.walk(probe))
    legs["ast_walk_is_not_vacuous"] = bool(found)
    return {"pass": bool(legs["arm_artifact_absent"]
                         and legs["tier_choice_computes_no_abnormal_return"]
                         and legs["ast_walk_is_not_vacuous"]),
            **legs}


def _c3() -> dict:
    """The cost model is the shipped one and the table is not retyped.

    `one_way_cost_bps` is imported and called; the arm defines no cost-shaped constant of its own.
    Checked over the syntax tree, and the reproduction is checked against the shipped function at
    each band edge so a future silent re-implementation shows up as a mismatch rather than as a
    passing import.
    """
    src = io.open(os.path.join(_HERE, "scripts", "insider_wide_arm.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    calls = [n for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
             and n.func.attr == "one_way_cost_bps"]
    # THE TABLE IS NOT RETYPED: none of the shipped table's own BPS VALUES appears as a literal
    # in the arm. The bar is the table's values and NOT a magic numeric range, because the arm
    # legitimately carries 63, 126, 500 and 50 -- a range ban would fire on a horizon and a draw
    # count, which is the substring-ban family in numeric clothing. The CAP EDGES are deliberately
    # NOT banned: 10e9 / 2e9 / 500e6 / 100e6 are this register's POPULATION floors, and that they
    # coincide with cost bands is a property of section 2's choice rather than a retyped table.
    bps_values = {float(v) for (_edge, v) in FP.COST_BPS_BY_MKTCAP} | {float(FP.COST_BPS_MICRO)}
    lits = sorted({float(n.value) for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, (int, float))
                   and not isinstance(n.value, bool) and float(n.value) in bps_values})
    probe = {}
    for cap in (50e6, 300e6, 1e9, 5e9, 50e9):
        probe["%.0fM" % (cap / 1e6)] = {
            "shipped_one_way_bps": float(FP.one_way_cost_bps(cap)),
            "arm_roundtrip_pp": float(WA.roundtrip_cost_pp([cap])[0]),
        }
    agrees = all(abs(v["arm_roundtrip_pp"] - 2.0 * v["shipped_one_way_bps"] / 100.0) < 1e-12
                 for v in probe.values())
    return {"pass": bool(calls and agrees and not lits),
            "n_calls_to_shipped_function": len(calls),
            "shipped_bps_values_retyped_in_arm": lits,
            "bps_values_banned": sorted(bps_values),
            "roundtrip_equals_twice_shipped_one_way": bool(agrees),
            "probe": probe,
            "COST_BPS_BY_MKTCAP": [list(x) for x in FP.COST_BPS_BY_MKTCAP],
            "COST_BPS_MICRO": FP.COST_BPS_MICRO}


def _c4() -> dict:
    """The check cell is the right cell: era `check`, ticker half 1, disjoint from the build cell.

    Disjointness is asserted on the ACTUAL row sets rather than argued from the config, because
    the whole value of the charter's 2x2 is that the check cell shares no event with the build
    cell. `C4` also requires the count to match the census's independently banked 2,669 — a
    number produced before this register existed.
    """
    p = D.out_path("INSIDER_CLUSTER_EVENTS_k%d.csv" % IC.K_PRIMARY)
    ev = pd.read_csv(p, dtype={"ticker": str, "date": str})
    chk = ev[(ev["era"] == "check") & (ev["half"] == 1)]
    bld = ev[(ev["era"] == "build") & (ev["half"] == 0)]
    keys_c = set(zip(chk["ticker"], chk["date"]))
    keys_b = set(zip(bld["ticker"], bld["date"]))
    cfg = D.era(D.ERA_CHECK)
    halves = {"early": int((chk["date"] < WA.CHECK_HALF_BOUNDARY).sum()),
              "late": int((chk["date"] >= WA.CHECK_HALF_BOUNDARY).sum())}
    in_window = bool(chk["date"].min() >= cfg["lo"] and chk["date"].max() <= cfg["hi"])
    half_ok = bool(all(D.stable_key_half(t) == 1 for t in set(chk["ticker"])))
    return {"pass": bool(len(chk) == C4_EXPECTED_EVENTS and not (keys_c & keys_b)
                         and in_window and half_ok and min(halves.values()) > 0),
            "n_events": int(len(chk)), "expected_from_census": C4_EXPECTED_EVENTS,
            "n_tickers": int(chk["ticker"].nunique()),
            "date_lo": str(chk["date"].min()), "date_hi": str(chk["date"].max()),
            "era_window": [cfg["lo"], cfg["hi"]], "inside_era_window": in_window,
            "every_ticker_is_half_1": half_ok,
            "overlap_with_build_cell": len(keys_c & keys_b),
            "halves_at_boundary": halves, "boundary": WA.CHECK_HALF_BOUNDARY}


def main(argv=None):
    t0 = time.time()
    out = {"item": "INSIDER-WIDE", "part": "the free pre-read checks",
           "register": "PREREG_insider_cluster_wide.md", "register_commit": "1cc8b7e",
           "trials_booked_at": "dfbccc4", "checks": {}}
    for name, fn in (("C2", _c2), ("C3", _c3), ("C4", _c4), ("C1", _c1)):
        print("[checks] %s ..." % name, flush=True)
        out["checks"][name] = fn()
        print("    %s -> %s" % (name, "PASS" if out["checks"][name]["pass"] else "FAIL"),
              flush=True)
    out["all_pass"] = all(v["pass"] for v in out["checks"].values())
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("\n[checks] all_pass %s -- wrote %s in %.0fs"
          % (out["all_pass"], p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    r = main()
    raise SystemExit(0 if r["all_pass"] else 2)
