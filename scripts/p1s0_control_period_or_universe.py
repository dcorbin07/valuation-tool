"""P1S0-CONTROL — was P1S0's dead early half a PERIOD or a UNIVERSE?

Register: `PREREG_p1s0control_period_or_universe.md`, committed ALONE at `dc618c4`, markdown
only, a strict git ancestor of this file. Budget booked at `be4bd36`, before this ran.

**THIS IS NOT A RE-RUN OF P1S0.** No arm of P1S0 is re-scored, its placebo is not recomputed and
`P1S0_GATE.json` is never written to — every optionable figure is READ from that shipped
artifact. `restrict()` is called for exactly one purpose, to obtain the DATE LIST, so the
comparison is same-dates by construction; no restricted arm is scored anywhere in this file.

**The options-expression family is NOT reopened here, whatever this returns.**

What is new: P1S0 ships `reference_full_panel_same_dates` carrying the FULL sample only. The
early/late split of the full panel on those dates has never been computed, and that split is the
whole question.

Run:
    python -m scripts.p1s0_control_period_or_universe --arms       # real arms, fast
    python -m scripts.p1s0_control_period_or_universe --placebo    # 200 draws, slow
    python -m scripts.p1s0_control_period_or_universe --verdict    # reads both, applies the rule

THREE PASSES, deliberately. The verdict pass REFUSES unless both artifacts exist, so the bar
cannot be computed after the statistic it judges is known.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts"))

# EVERYTHING BELOW IS FROM THE REGISTER. Changing one after a measurement voids the item.
HORIZONS = [63, 252, 504]          # 504 is a DIAGNOSTIC only; it may not decide (§4)
ANCHOR = 63                        # leg 1, the power anchor
LEG2_H = 252                       # leg 2, the horizon where optionable read -0.08%
PLACEBO_H = [63, 252]              # floors are needed only where the rule reads
PLACEBO_DRAWS = 200                # §3, matching P1S0
PLACEBO_SEED0 = 7100               # §3, matching P1S0's sequence so seed choice is not free
MODE = "pit_liquid"                # P1S0's PRIMARY mode

DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
P1S0_GATE = os.path.join(DATA, "free_analysis", "P1S0_GATE.json")
ARMS_JSON = os.path.join(DATA, "free_analysis", "P1S0_CONTROL_ARMS.json")
PLACEBO_JSON = os.path.join(DATA, "free_analysis", "P1S0_CONTROL_PLACEBO.json")
OUT_JSON = os.path.join(DATA, "free_analysis", "P1S0_CONTROL.json")


def _log(m):
    print(m, flush=True)


def _w(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=float)


def _r(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def windows():
    """The date list and halves, IMPORTED from P1S0 rather than re-typed (audit B7's class).

    `restrict` is used ONLY to derive the dates. Nothing restricted is scored.
    """
    import scripts.p1s0_optionable_gate as P
    from valuation.studies.optionable_universe import restrict
    panel, part = P.load()
    r = restrict(panel, part, MODE)
    out = {}
    for h in HORIZONS:
        ds = P.scorable_dates(r, h)
        e, l, b = P.halves(ds)
        out[h] = {"dates": ds, "early": e, "late": l, "boundary": b}
    return panel, out


def _cells(panel, h, ds, e, l):
    from scripts.term_structure import arm
    cells = {}
    for nm, dd in (("full", ds), ("early", e), ("late", l)):
        a = arm(panel, h, dates=dd, label="p1s0control_h%d_%s" % (h, nm)) if dd else {}
        cells[nm] = {"n_periods": a.get("n_periods"), "cum_alpha": a.get("cum_alpha"),
                     "alpha_ann": a.get("alpha_ann"), "alpha_t_hac": a.get("alpha_t_hac"),
                     "alpha_t_naive": a.get("alpha_t_naive"),
                     "ls_t_hac": a.get("ls_t_hac"), "monotonicity": a.get("monotonicity")}
    return cells


def run_arms(a):
    panel, win = windows()
    _log("[control] FULL panel %s, %d dates, %d names"
         % (panel.shape, panel["date"].nunique(), panel["ticker"].nunique()))
    out = {"item": "P1S0-CONTROL", "register": "PREREG_p1s0control_period_or_universe.md",
           "register_commit": "dc618c4", "budget_commit": "be4bd36",
           "NOT_a_rerun_of": "P1S0 — no arm of it is re-scored; its figures are read from "
                             "P1S0_GATE.json",
           "panel": "full equity panel (panel_s22_h504.pkl)", "mode_dates_from": MODE,
           "horizons": {}}
    for h in HORIZONS:
        w = win[h]
        out["horizons"][str(h)] = {
            "n_dates": len(w["dates"]),
            "embargoed": str(w["boundary"])[:10] if w["boundary"] is not None else None,
            "early_window": [str(w["early"][0])[:10], str(w["early"][-1])[:10]] if w["early"] else None,
            "late_window": [str(w["late"][0])[:10], str(w["late"][-1])[:10]] if w["late"] else None,
            "full_panel": _cells(panel, h, w["dates"], w["early"], w["late"]),
        }
        c = out["horizons"][str(h)]["full_panel"]
        _log("[arms] H=%d  full ann %s  early ann %s (t %s)  late ann %s"
             % (h, c["full"]["alpha_ann"], c["early"]["alpha_ann"],
                c["early"]["alpha_t_hac"], c["late"]["alpha_ann"]))
    _w(a.arms_json, out)
    _log("[arms] wrote %s" % a.arms_json)
    return 0


def run_placebo(a):
    """The FULL PANEL's own fixed_weights_null. P1S0's floors were calibrated on 619 names and
    may NOT be used here (§3, §7 void condition 3)."""
    from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols
    from scripts.term_structure import arm
    panel, win = windows()
    leaked = [c for c in placebo_signal_cols(panel) if str(c).startswith(("fwd_ret", "ret_"))]
    if leaked:
        raise SystemExit("[control] placebo would permute forward returns: %s" % leaked)
    rows, t0 = [], time.time()
    for i in range(PLACEBO_DRAWS):
        pp = placebo_panel(panel, seed=PLACEBO_SEED0 + i)
        rec = {"seed": PLACEBO_SEED0 + i}
        for h in PLACEBO_H:
            w = win[h]
            cell = {}
            for nm, dd in (("full", w["dates"]), ("early", w["early"]), ("late", w["late"])):
                r = arm(pp, h, dates=dd) if dd else {}
                cell[nm] = r.get("alpha_t_hac")
                if nm == "early":
                    cell["cum_alpha_early"] = r.get("cum_alpha")
            rec[str(h)] = cell
        rows.append(rec)
        if i == 2 or (i + 1) % 25 == 0:
            el = time.time() - t0
            _log("[placebo] %d/%d  %.0fs elapsed, ~%.0fs left"
                 % (i + 1, PLACEBO_DRAWS, el, el / (i + 1) * (PLACEBO_DRAWS - i - 1)))

    def pct(h, nm, q):
        v = [r[str(h)][nm] for r in rows if r[str(h)].get(nm) is not None]
        return float(np.percentile(v, q)) if v else None

    def med(h, nm):
        v = [r[str(h)][nm] for r in rows if r[str(h)].get(nm) is not None]
        return float(np.median(v)) if v else None

    floors = {}
    for h in PLACEBO_H:
        floors[str(h)] = {
            **{("%s_p95" % nm): pct(h, nm, 95) for nm in ("full", "early", "late")},
            **{("%s_median" % nm): med(h, nm) for nm in ("full", "early", "late")},
            "cum_alpha_early_p95": pct(h, "cum_alpha_early", 95),
        }
    out = {"item": "P1S0-CONTROL", "instrument": "fixed_weights_null",
           "computed_on": "the FULL panel — P1S0's floors were calibrated on 619 names and may "
                          "NOT be used here",
           "not_comparable_with": "X7/session-10 floors (those include CPCV adoption), and NOT "
                                  "comparable with P1S0's restricted-universe floors either",
           "draws": PLACEBO_DRAWS, "seeds": [PLACEBO_SEED0, PLACEBO_SEED0 + PLACEBO_DRAWS - 1],
           "floors": floors, "rows": rows}
    _w(a.placebo_json, out)
    _log("[placebo] wrote %s" % a.placebo_json)
    return 0


def run_verdict(a):
    for p in (a.arms_json, a.placebo_json):
        if not os.path.exists(p):
            _log("[verdict] REFUSED — missing %s. The bar must exist before the statistic is "
                 "judged against it." % p)
            return 2
    arms, plac = _r(a.arms_json), _r(a.placebo_json)
    p1s0 = _r(P1S0_GATE)["modes"][MODE]

    anchor = arms["horizons"][str(ANCHOR)]["full_panel"]["early"]
    leg2 = arms["horizons"][str(LEG2_H)]["full_panel"]["early"]
    floor = plac["floors"][str(ANCHOR)]["early_p95"]

    leg1_clears = bool(anchor["alpha_t_hac"] is not None and anchor["alpha_t_hac"] >= floor)
    leg2_positive = bool(leg2["cum_alpha"] is not None and leg2["cum_alpha"] > 0)

    if leg1_clears and leg2_positive:
        reading = "UNIVERSE"
        meaning = ("The full panel is healthy over 2016-2020 while the optionable subset is "
                   "dead. P1S0's failure is about OPTIONABLE NAMES and the family closed "
                   "correctly. IT STAYS CLOSED.")
    elif (not leg1_clears) and (not leg2_positive):
        reading = "PERIOD"
        meaning = ("The full panel is weak over that window too. P1S0's early half was "
                   "measuring a PERIOD, not a universe, and the gate closed on an artifact. "
                   "This is a finding about THE GATE and NOT a licence to reopen the family — "
                   "a reopen needs its own register.")
    else:
        reading = "NULL"
        meaning = ("The two legs disagree. Ambiguous against the pre-committed rule is a NULL "
                   "(RUN_RULES A6), never a judgement call.")

    out = dict(arms)
    out["placebo_artifact"] = os.path.basename(a.placebo_json)
    out["decision"] = {
        "leg1_anchor_h63": {"full_panel_early_alpha_t_hac": anchor["alpha_t_hac"],
                            "own_full_panel_early_p95": floor, "clears": leg1_clears},
        "leg2_h252": {"full_panel_early_cum_alpha": leg2["cum_alpha"],
                      "bar": 0.0, "positive": leg2_positive},
        "reading": reading, "meaning": meaning,
        "rule": ("UNIVERSE = both legs clear; PERIOD = both fail; anything else NULL. Fixed in "
                 "PREREG_p1s0control_period_or_universe.md section 4 before any measurement.")}

    # the optionable side, READ from P1S0's shipped artifact and never recomputed
    out["p1s0_optionable_READ_not_recomputed"] = {
        str(h): {w: p1s0["arms"][str(h)][w] for w in ("full", "early", "late")}
        for h in HORIZONS}
    out["p1s0_reference_full_sample_only"] = p1s0["reference_full_panel_same_dates"]
    out["family_state"] = {
        "P1S0_verdict": _r(P1S0_GATE)["family_verdict"]["state"],
        "changed_by_this_item": False,
        "note": "The options-expression family is NOT reopened by this register, whatever the "
                "reading. That would need its own register, its own trials and its own blind "
                "commitment."}
    _w(a.out_json, out)
    _log("[VERDICT] %s" % reading)
    _log("[VERDICT] %s" % meaning)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms-json", default=ARMS_JSON)
    ap.add_argument("--placebo-json", default=PLACEBO_JSON)
    ap.add_argument("--out-json", default=OUT_JSON)
    ap.add_argument("--arms", action="store_true")
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--verdict", action="store_true")
    a = ap.parse_args()
    if a.arms:
        return run_arms(a)
    if a.placebo:
        return run_placebo(a)
    if a.verdict:
        return run_verdict(a)
    ap.error("choose --arms, --placebo or --verdict")


if __name__ == "__main__":
    raise SystemExit(main())
