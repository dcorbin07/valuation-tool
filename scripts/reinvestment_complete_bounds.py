#!/usr/bin/env python3
"""
Item C — re-run reinvestment Arm B against the COMPLETE bound set.

Registered in `PREREG_C_reinvestment_complete_bounds.md`, committed ALONE at `abeb4f7` before
this file existed. Read that first; every threshold below is fixed there and none may move.

WHAT THIS IS FOR. Arm B passed all seven of its original bounds and was rejected anyway, on harm
the original register never encoded — negative enterprise values, negative terminal values, DCFs
pushed non-positive. A passed-every-bound result sitting under an unregistered rejection is the
state that decays into "we tested it and it worked". This scores the same arm, at the same
parameters, against a bound set that asks whether the output is still a valuation.

THE VERDICT IS MECHANICAL. Twelve bounds; all twelve hold and Arm B ships, any one fails and the
item closes REJECTED-COMPLETE, any VOID precondition unmet and the run is VOID rather than either.

    python -m scripts.reinvestment_complete_bounds fetch    # paced, resumable; safe to re-run
    python -m scripts.reinvestment_complete_bounds score    # offline; zero network calls
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pickle
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.config import CONFIG                        # noqa: E402
from valuation.data import fetcher                         # noqa: E402
from valuation.engine import dcf as D                      # noqa: E402
from valuation.engine.pipeline import value_from_company   # noqa: E402
from valuation.engine.wacc import compute_wacc             # noqa: E402
from valuation.screener import universe as U               # noqa: E402

# --------------------------------------------------------------------------------------------
# PREREG §2 — the universe. No discretionary selection: every bundled ticker, plus exactly the
# foreign filers the Part 8 record names in its own decisive populations and the bundled list
# lacks. Both inputs are fixed documents.
# --------------------------------------------------------------------------------------------
RECORD_FOREIGN = ["BHP", "E", "PBR", "TTE", "RIO", "NVO", "CNI"]

SNAP = os.path.join("data", "free_analysis", "reinvest_snapshot.pkl")
OUT = os.path.join("data", "free_analysis", "REINVEST_COMPLETE_BOUNDS.json")

# PREREG §2.1 — VOID preconditions. Every Group-B bound passes trivially on an empty population,
# and a throttled fetch empties it silently, so these decide VOID before anything else is read.
V1_FETCH_RATE = 0.95
V2_MIN_TREATED = 80
V3_MIN_DECISIVE = 20

# PREREG §4 — thresholds. Fixed at abeb4f7; none may move.
F1_TOL = 0.25            # year-1 reinvestment within +/-25% of observed net capex
F2_MAX_UNDERCHARGED = 5  # count undercharged >5% of revenue must fall to <= 5
F4_TERMINAL_DROP = -0.05  # decisive-set median terminal FCFF change <= -5%
UNDERCHARGE_FRAC = 0.05  # ">5% of revenue" defines the decisive set
FLAT_REVENUE_TOL = 0.05  # |rev_last/rev_1 - 1| <= 5% is "flat"
C1_EV_POSITIVE_RATE = 0.99
C4_RISE_TOL = 0.01       # float/renormalisation tolerance, not a budget
C5_BLAST_MULTIPLE = 1.5  # names changed <= 1.5 x decisive-set size
P2_REINVEST_RISE = 0.10  # capex-boom names: year-1 reinvestment may not rise >10%

SEC_PAUSE = 0.15


def universe() -> list:
    seen, out = set(), []
    for t in list(U.bundled_tickers()) + RECORD_FOREIGN:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# --------------------------------------------------------------------------------------------
# fetch
# --------------------------------------------------------------------------------------------

def fetch(path: str = SNAP) -> dict:
    """One live fetch of the whole universe, pickled so scoring is offline and repeatable.

    Resumable: an existing pickle is loaded and only missing names are fetched, so a throttled
    run is retried rather than banked. A name that raises is simply ABSENT — never stored as an
    empty CompanyData, which would look like a fetched name with no capex and quietly leave the
    treated population (the vacuous-pass hazard §2.1 exists for).
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    snap = {}
    if os.path.exists(path):
        with open(path, "rb") as fh:
            snap = pickle.load(fh)
        print(f"resuming: {len(snap)} names already cached")
    names = universe()
    todo = [t for t in names if t not in snap]
    print(f"universe {len(names)}, to fetch {len(todo)}", flush=True)
    for i, t in enumerate(todo, 1):
        try:
            cd = fetcher.get_company(t, CONFIG)
            if getattr(cd, "revenue", None) is None:
                print(f"  {t}: no revenue — NOT stored (retried next run)", flush=True)
            else:
                snap[t] = cd
        except Exception as e:                                        # noqa: BLE001
            print(f"  {t}: {type(e).__name__} {str(e)[:70]} — NOT stored", flush=True)
        if i % 25 == 0:
            with open(path, "wb") as fh:
                pickle.dump(snap, fh)
            print(f"  ...{i}/{len(todo)} ({len(snap)} cached)", flush=True)
        time.sleep(SEC_PAUSE)
    with open(path, "wb") as fh:
        pickle.dump(snap, fh)
    print(f"fetched: {len(snap)}/{len(names)}")
    return snap


# --------------------------------------------------------------------------------------------
# score
# --------------------------------------------------------------------------------------------

def _value(cd, mode: str, ov: dict):
    """Value ONE company under ONE floor mode.

    `cd` is deep-copied because `value_from_company` appends to `cd.quality_notes`; valuing the
    same object twice would carry the control's notes into the treated arm and make a "control
    bit-identical" comparison meaningless in the one field that records why a name was treated.
    """
    was = D.REINVESTMENT_FLOOR_MODE
    D.REINVESTMENT_FLOOR_MODE = mode
    try:
        return value_from_company(copy.deepcopy(cd), CONFIG, overrides=ov)
    finally:
        D.REINVESTMENT_FLOOR_MODE = was


def _row(res) -> dict:
    b = res.scenarios.base
    return {
        "fair_value": res.base_fair_value,
        "dcf": res.dcf_per_share,
        "ev": getattr(b, "enterprise_value", None),
        "tv": getattr(b, "terminal_value", None),
        "reinvest_y1": getattr(b, "reinvestment_y1", None),
        "net_capex": getattr(b, "observed_net_capex", None),
        "wacc": res.wacc.wacc,
        "score": getattr(res.score, "total", None),
        "published": res.base_fair_value is not None,
        "confidence": getattr(res.fair_value_blend, "confidence", None),
        "rev1": (b.rows[0].get("revenue") if getattr(b, "rows", None) else None),
        "revlast": (b.rows[-1].get("revenue") if getattr(b, "rows", None) else None),
    }


def measure(path: str = SNAP) -> dict:
    with open(path, "rb") as fh:
        snap = pickle.load(fh)
    names = universe()
    rows = {}
    for i, t in enumerate(sorted(snap), 1):
        cd = snap[t]
        try:
            # WACC inputs pinned ONCE and passed to both arms, so the only difference between
            # the two runs is the floor mode (PREREG §3). Without this a re-resolved beta could
            # move a control name and break H1 for a reason that has nothing to do with the arm.
            w = compute_wacc(cd, CONFIG)
            ov = {"beta": w.beta, "risk_free": w.risk_free, "erp": w.erp}
            ctl = _value(cd, "off", ov)
            trt = _value(cd, "persistent", ov)
            rows[t] = {"control": _row(ctl), "treated": _row(trt),
                       "financial": ctl.classification.regime == "financial"}
        except Exception as e:                                        # noqa: BLE001
            rows[t] = {"error": f"{type(e).__name__}: {str(e)[:90]}"}
        if i % 40 == 0:
            print(f"  scored {i}/{len(snap)}", flush=True)
    return evaluate(rows, len(names))


def _frac(x, y):
    return (x / y) if (y not in (None, 0)) else None


def evaluate(rows: dict, n_universe: int) -> dict:
    ok = {t: r for t, r in rows.items() if "error" not in r}
    err = {t: r["error"] for t, r in rows.items() if "error" in r}

    # ---- populations, all recomputed on THIS snapshot -------------------------------------
    treated, untreated = [], []
    for t, r in ok.items():
        c = r["control"]
        nc = c.get("net_capex")
        touched = (not r["financial"]) and nc is not None and nc > 0
        (treated if touched else untreated).append(t)

    def undercharge(t, arm):
        a = ok[t][arm]
        nc, ri, rev = a.get("net_capex"), a.get("reinvest_y1"), a.get("rev1")
        if nc is None or ri is None or not rev:
            return None
        return (nc - ri) / rev

    decisive = [t for t in treated
                if (undercharge(t, "control") or 0) > UNDERCHARGE_FRAC]

    def is_flat(t):
        c = ok[t]["control"]
        r1, rl = c.get("rev1"), c.get("revlast")
        if not r1 or not rl:
            return None
        return abs(rl / r1 - 1.0) <= FLAT_REVENUE_TOL

    flat_pop = [t for t in decisive if is_flat(t) is True]
    boom_pop = [t for t in decisive if is_flat(t) is False]

    # ---- VOID preconditions (PREREG §2.1) --------------------------------------------------
    fetch_rate = len(ok) / n_universe if n_universe else 0.0
    voids = {
        "V1_fetch_rate": {"value": round(fetch_rate, 4), "floor": V1_FETCH_RATE,
                          "ok": fetch_rate >= V1_FETCH_RATE},
        "V2_treated": {"value": len(treated), "floor": V2_MIN_TREATED,
                       "ok": len(treated) >= V2_MIN_TREATED},
        "V3_decisive": {"value": len(decisive), "floor": V3_MIN_DECISIVE,
                        "ok": len(decisive) >= V3_MIN_DECISIVE},
    }

    # ---- the twelve bounds ------------------------------------------------------------------
    B = {}

    # F1 — flat-revenue treated names charged within +/-25% of observed net capex.
    f1_bad = []
    f1_pop = [t for t in treated if is_flat(t) is True]
    for t in f1_pop:
        a = ok[t]["treated"]
        nc, ri = a.get("net_capex"), a.get("reinvest_y1")
        if nc and ri is not None and abs(ri - nc) / abs(nc) > F1_TOL:
            f1_bad.append(t)
    B["F1"] = {"held": not f1_bad, "n_pop": len(f1_pop), "violations": len(f1_bad),
               "names": f1_bad[:15],
               "desc": "flat-revenue names charged within +/-25% of observed net capex"}

    # F2 — the undercharged tail closes.
    f2_after = [t for t in treated if (undercharge(t, "treated") or 0) > UNDERCHARGE_FRAC]
    B["F2"] = {"held": len(f2_after) <= F2_MAX_UNDERCHARGED, "before": len(decisive),
               "after": len(f2_after), "max": F2_MAX_UNDERCHARGED, "names": f2_after[:15],
               "desc": "count undercharged >5% of revenue falls to <=5"}

    # F3 — nobody is paid to shrink.
    f3 = [t for t in treated if (ok[t]["treated"].get("reinvest_y1") or 0) < 0]
    B["F3"] = {"held": not f3, "violations": len(f3), "names": f3[:15],
               "desc": "treated names with NEGATIVE modelled reinvestment falls to 0"}

    # F4 — the terminal is reached.
    tv_chg = []
    for t in decisive:
        c, a = ok[t]["control"].get("tv"), ok[t]["treated"].get("tv")
        if c and a is not None and c != 0:
            tv_chg.append(a / c - 1.0)
    f4_med = statistics.median(tv_chg) if tv_chg else None
    B["F4"] = {"held": f4_med is not None and f4_med <= F4_TERMINAL_DROP,
               "median_change": f4_med, "bar": F4_TERMINAL_DROP, "n": len(tv_chg),
               "desc": "decisive-set terminal FCFF falls by a median of at least 5%"}

    # H1 — the control group is BIT-IDENTICAL.
    #
    # SCORED ON EXACTLY THE FIELDS THE REGISTER NAMES: "fair value, WACC, score, confidence and
    # published flag". The first cut of this function also compared `ev`, `tv` and `dcf`, which
    # made H1 read VIOLATED on one name (C). That is STRICTER THAN THE REGISTERED BOUND, and
    # scoring a bound on fields the register does not list — after seeing the result — is the
    # exact error this whole task exists to correct. The register is the authority.
    #
    # The movement it found is real and is reported as a FINDING (`financial_gate`, below),
    # never folded into the verdict. PREREG §5 says a thirteenth thing worth bounding is
    # recorded for whoever re-opens it, not added to this scorecard.
    H1_FIELDS = ("fair_value", "wacc", "score", "confidence", "published")
    h1 = []
    for t in untreated:
        c, a = ok[t]["control"], ok[t]["treated"]
        for k in H1_FIELDS:
            if c.get(k) != a.get(k):
                h1.append(t)
                break
    B["H1"] = {"held": not h1, "n_control": len(untreated), "moved": len(h1),
               "fields": list(H1_FIELDS), "names": h1[:15],
               "desc": "control group bit-identical to the last digit"}

    # H2 — zero publish/withhold flips in the control.
    h2 = [t for t in untreated
          if ok[t]["control"]["published"] != ok[t]["treated"]["published"]]
    B["H2"] = {"held": not h2, "flips": len(h2), "names": h2[:15],
               "desc": "publish/withhold flips are zero in the control"}

    # H3 — the direction is DOWN on the decisive set.
    fv_chg = []
    for t in decisive:
        c, a = ok[t]["control"].get("fair_value"), ok[t]["treated"].get("fair_value")
        if c and a is not None and c != 0:
            fv_chg.append(a / c - 1.0)
    h3_med = statistics.median(fv_chg) if fv_chg else None
    B["H3"] = {"held": h3_med is not None and h3_med < 0, "median_change": h3_med,
               "n": len(fv_chg), "desc": "decisive-set median fair value falls"}

    # C1 — enterprise value stays positive.
    ev_pos = [t for t in ok if (ok[t]["control"].get("ev") or 0) > 0]
    c1_bad = [t for t in ev_pos if (ok[t]["treated"].get("ev") or 0) <= 0]
    c1_rate = _frac(len(ev_pos) - len(c1_bad), len(ev_pos))
    B["C1"] = {"held": c1_rate is not None and c1_rate >= C1_EV_POSITIVE_RATE,
               "rate": c1_rate, "floor": C1_EV_POSITIVE_RATE, "n_pop": len(ev_pos),
               "violations": len(c1_bad), "names": c1_bad[:15],
               "desc": "EV stays positive for >=99% of names that had a positive EV"}

    # C2 — terminal value stays positive.
    tv_pos = [t for t in ok if (ok[t]["control"].get("tv") or 0) > 0]
    c2_bad = [t for t in tv_pos if (ok[t]["treated"].get("tv") or 0) <= 0]
    B["C2"] = {"held": not c2_bad, "n_pop": len(tv_pos), "violations": len(c2_bad),
               "names": c2_bad[:15],
               "desc": "terminal value stays positive for EVERY name that had one"}

    # C3 — the DCF stays positive.
    dcf_pos = [t for t in ok if (ok[t]["control"].get("dcf") or 0) > 0]
    c3_bad = [t for t in dcf_pos if (ok[t]["treated"].get("dcf") or 0) <= 0]
    B["C3"] = {"held": not c3_bad, "n_pop": len(dcf_pos), "violations": len(c3_bad),
               "names": c3_bad[:15],
               "desc": "DCF stays positive for EVERY name that had a positive DCF"}

    # C4 — no fair value moves UP.
    up_any, up_tol = [], []
    for t in ok:
        c, a = ok[t]["control"].get("fair_value"), ok[t]["treated"].get("fair_value")
        if c and a is not None and c > 0:
            ch = a / c - 1.0
            if ch > 0:
                up_any.append((t, ch))
            if ch > C4_RISE_TOL:
                up_tol.append((t, ch))
    up_tol.sort(key=lambda x: -x[1])
    B["C4"] = {"held": not up_tol, "rose_over_tol": len(up_tol), "rose_at_all": len(up_any),
               "tol": C4_RISE_TOL,
               "worst": [{"ticker": t, "change": round(c, 4)} for t, c in up_tol[:10]],
               "desc": "no published fair value rises by more than 1%"}

    # C5 — bounded blast radius.
    changed = [t for t in ok
               if ok[t]["control"].get("fair_value") != ok[t]["treated"].get("fair_value")]
    ceiling = C5_BLAST_MULTIPLE * len(decisive)
    ratio = _frac(len(changed), len(decisive))
    # PREREG §4: if the multiplier decides the answer, C5 is INDECISIVE and carries no weight.
    indecisive = ratio is not None and 1.0 <= ratio <= 2.3 and len(changed) > ceiling
    B["C5"] = {"held": len(changed) <= ceiling, "changed": len(changed),
               "decisive": len(decisive), "ceiling": ceiling, "ratio": ratio,
               "indecisive": bool(indecisive), "multiple": C5_BLAST_MULTIPLE,
               "desc": "names whose fair value changes <= 1.5x the decisive set"}

    # P2 — the capex-boom population is left alone.
    p2_bad = []
    for t in boom_pop:
        c = ok[t]["control"].get("reinvest_y1")
        a = ok[t]["treated"].get("reinvest_y1")
        if a is None:
            continue
        if c is None or c <= 0:
            if a > 0:
                p2_bad.append((t, None))
        elif a / c - 1.0 > P2_REINVEST_RISE:
            p2_bad.append((t, a / c - 1.0))
    p2_bad.sort(key=lambda x: -(x[1] if x[1] is not None else 1e18))
    B["P2"] = {"held": not p2_bad, "n_pop": len(boom_pop), "violations": len(p2_bad),
               "tol": P2_REINVEST_RISE,
               "worst": [{"ticker": t, "rise": (round(c, 3) if c is not None else "from<=0")}
                         for t, c in p2_bad[:10]],
               "desc": "capex-boom names' year-1 reinvestment does not rise >10%"}

    # P1 is F1+F2 restated; recorded so the target population is explicit.
    B["P1"] = {"held": B["F1"]["held"] and B["F2"]["held"], "n_flat_decisive": len(flat_pop),
               "desc": "the target is the flat-revenue population (= F1 and F2)"}

    # ---- FINDING, NOT A BOUND (PREREG §5) ---------------------------------------------------
    # The original register's census asserts "financials (out of scope) 31 — no [cannot be
    # touched]". That is FALSE AT THE CODE LEVEL: `_net_capex_floor` gates on `capex - D&A > 0`
    # alone and never asks the regime, so a financial with positive net capex IS run through the
    # floor. It goes unseen because the financial regime REPLACES the headline per-share value
    # with a P/B-ROE model, so the change hides inside EV and year-1 reinvestment while fair
    # value, published flag and score are all untouched — which is precisely why the original
    # H1, scoring only those fields, could never have caught it.
    fin_touched = []
    for t, r in ok.items():
        if not r["financial"]:
            continue
        c, a = r["control"], r["treated"]
        if c.get("ev") != a.get("ev") or c.get("reinvest_y1") != a.get("reinvest_y1"):
            fin_touched.append({
                "ticker": t,
                "ev_control": c.get("ev"), "ev_treated": a.get("ev"),
                "reinvest_control": c.get("reinvest_y1"), "reinvest_treated": a.get("reinvest_y1"),
                "fair_value_moved": c.get("fair_value") != a.get("fair_value")})
    finding = {
        "name": "the reinvestment floor's gate does not exclude financials",
        "carries_verdict_weight": False,
        "n_financial_scored": sum(1 for r in ok.values() if r["financial"]),
        "n_touched": len(fin_touched),
        "any_fair_value_moved": any(f["fair_value_moved"] for f in fin_touched),
        "detail": fin_touched[:15],
        "why_it_was_invisible": ("the financial regime replaces the headline per-share value with "
                                 "a P/B-ROE model, so EV and year-1 reinvestment move while fair "
                                 "value, score and published flag do not"),
    }

    # ---- verdict ---------------------------------------------------------------------------
    void = [k for k, v in voids.items() if not v["ok"]]
    decisive_bounds = {k: v for k, v in B.items()
                       if not (k == "C5" and v.get("indecisive"))}
    failed = sorted(k for k, v in decisive_bounds.items() if not v["held"])
    if void:
        verdict = "VOID"
    elif failed:
        verdict = "REJECTED-COMPLETE"
    else:
        verdict = "SHIPS"

    return {
        "prereg": "PREREG_C_reinvestment_complete_bounds.md",
        "prereg_commit": "abeb4f7",
        "arm": "B (persistent floor, explicit years AND terminal)",
        "mode": "persistent",
        "verdict": verdict,
        "failed_bounds": failed,
        "void_failures": void,
        "voids": voids,
        "bounds": B,
        "finding_not_a_bound": finding,
        "universe": {"requested": n_universe, "scored": len(ok), "errors": len(err)},
        "populations": {"treated": len(treated), "untreated": len(untreated),
                        "decisive": len(decisive), "flat_revenue": len(flat_pop),
                        "capex_boom": len(boom_pop),
                        "decisive_names": sorted(decisive),
                        "capex_boom_names": sorted(boom_pop),
                        "flat_revenue_names": sorted(flat_pop)},
        "errors": err,
    }


def render(p: dict) -> str:
    L = []
    A = L.append
    A("=" * 88)
    A(f"ITEM C — reinvestment Arm B against the COMPLETE bound set")
    A(f"register {p['prereg']} @ {p['prereg_commit']}   arm: {p['arm']}")
    A("=" * 88)
    u = p["universe"]
    A(f"universe requested {u['requested']}, scored {u['scored']}, errors {u['errors']}")
    pop = p["populations"]
    A(f"treated {pop['treated']}  untreated {pop['untreated']}  decisive {pop['decisive']} "
      f"(flat-revenue {pop['flat_revenue']}, capex-boom {pop['capex_boom']})")
    A("")
    A("VOID preconditions")
    for k, v in p["voids"].items():
        A(f"  {'ok ' if v['ok'] else 'VOID'}  {k:16s} {v['value']} (floor {v['floor']})")
    A("")
    A("BOUNDS")
    for k in ("F1", "F2", "F3", "F4", "H1", "H2", "H3", "C1", "C2", "C3", "C4", "C5", "P1", "P2"):
        if k not in p["bounds"]:
            continue
        b = p["bounds"][k]
        mark = "HELD    " if b["held"] else "VIOLATED"
        extra = ""
        if b.get("indecisive"):
            mark = "INDECIS."
        for key in ("violations", "flips", "moved", "rose_over_tol", "changed", "after"):
            if key in b:
                extra = f"  [{key}={b[key]}]"
                break
        if "median_change" in b and b["median_change"] is not None:
            extra = f"  [median={b['median_change']:+.4f}]"
        if "rate" in b and b["rate"] is not None:
            extra = f"  [rate={b['rate']:.4f}, violations={b.get('violations')}]"
        A(f"  {mark}  {k:3s} {b['desc']}{extra}")
    A("")
    A(f"VERDICT: {p['verdict']}")
    if p["failed_bounds"]:
        A(f"  failed: {', '.join(p['failed_bounds'])}")
    if p["void_failures"]:
        A(f"  void:   {', '.join(p['void_failures'])}")
    A("=" * 88)
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "score"])
    ap.add_argument("--snapshot", default=SNAP)
    ap.add_argument("--json", default=OUT)
    a = ap.parse_args()
    if a.cmd == "fetch":
        fetch(a.snapshot)
        return 0
    payload = measure(a.snapshot)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    print(render(payload))
    print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
