# -*- coding: utf-8 -*-
"""`STAGE1-BATCH2` — the five arms, scored ONLY after the kill pass has been read.

    python -m scripts.stage1_batch2_arms

**IT REFUSES WITHOUT A PASSING KILL ARTIFACT**, so an arm can never be scored before its own
pre-outcome control has run (`O10`). The refusal is conditional and reachable — a constant-guard
would make it unreachable, which is `MB31`'s and `STAGE1-BATCH1`'s own repeated defect.

**THE STATISTIC IS CHARTER STAGE 1a's: the DEPLOYED COMPOSITE as a SINGLE control**, from
`composite_from_frame` (CALLED, never re-implemented), z-scored within date. Batch 1's
complete-case residualisation on seven themes left a FIVE-date early half; this restores all 44
dates at halves 24 / 20.

**BOTH POPULATIONS, AND THE TIER GOVERNS** (charter Stage 1b). An arm passing wide and failing
the tier is `REAL BUT NOT INVESTABLE HERE` and does not reach Stage 2.

**EVERY CRITICAL VALUE IS LABELLED UNCALIBRATED.** No bar calibrated on the 2,531-name panel
transfers to this universe.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts.stage1_kills import build_quadrant                             # noqa: E402
from scripts.stage1_score import (incremental_ic, hac_t, two_sided_p,       # noqa: E402
                                  benjamini_hochberg, stage1_verdict,
                                  MIN_HALF_DATES)
from scripts.stage1_batch2_kills import (tier_frame, monthly_closes,        # noqa: E402
                                         b3_signal, b5_signal, attach_signal,
                                         BUILD_HALF_SPLIT, PANEL)

REGISTER = "PREREG_stage1_batch2.md"
KILLS = "STAGE1_BATCH2_KILLS.json"
OUT = "STAGE1_BATCH2_ARMS.json"

#: the register's own ladder. `k` STAYS 6 whatever is run (register 1).
BH_K = 6
BH_Q = 0.10
#: UNCALIBRATED — conventional. No bar calibrated on the 2,531-name panel transfers.
CRIT = 2.0
#: Don's own margins, reused verbatim rather than re-chosen.
DON_DRAWDOWN_ALLOWANCE_PP = 3.0
#: 80%-power MDE: the effect at which a design of this `se` would reach `CRIT` four times in five.
POWER_Z = 0.84


def fa():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis")


def data_root():
    from scripts.index_best import _data_root
    return _data_root()


def mde80(se, crit=CRIT):
    """`(crit + 0.84) * se` — the 80%-power minimum detectable effect.

    `MB22` measured that every MDE this project had published was a 50%-power figure
    (`crit * se`), which is **1.42x smaller** at crit 2.0. Quoting one as the other is the error;
    `RUN_RULES` PART A rule 11 requires the 80% figure.
    """
    return None if se in (None, 0) else float((crit + POWER_Z) * se)


# ============================================================================================
# the control column — charter Stage 1a
# ============================================================================================
def deployed_control(frame):
    """`composite_from_frame`'s output, z-scored within date, as ONE regressor.

    **CALLED, NEVER RE-IMPLEMENTED (`B7`).** It renormalises by present-weight mass, so the
    composite is defined on every row carrying any theme — which is exactly why all 44 dates
    survive where complete-case residualisation on seven columns left five in the early half.
    **It drops no theme**: `institutional` still enters, at whatever weight the shipped
    renormalisation gives it per row.
    """
    from valuation.edge.fundamental_panel import composite_from_frame, _base_weights
    from valuation.screener.cross_sectional import zscore
    from valuation.screener import settings as S
    cols = [c for c in S.BUCKET_FACTORS["established"]
            if c in frame.columns and frame[c].notna().any()]
    w = _base_weights(cols, "established")
    # PER DATE, AND WITH THE SHIPPED `zscore` PASSED IN. `composite_from_frame(sub, cols,
    # weights, zscore)` standardises WITHIN the slice it is given, so calling it on the whole
    # frame would standardise across the panel's entire history and the "composite" would be a
    # level rather than a cross-sectional standing. Its fourth argument is the standardiser, and
    # the shipped `cross_sectional.zscore` is passed rather than a local one -- that function
    # carries the 2% winsorisation `S21` measured to be load-bearing, and a hand-rolled
    # standardiser would quietly drop it.
    out = []
    for d in sorted(frame["date"].unique()):
        g = frame[frame["date"] == d].copy()
        comp = np.asarray(composite_from_frame(g, cols, w, zscore), dtype=float)
        v = pd.Series(comp, index=g.index)
        sd = float(v.std(ddof=0)) if v.notna().sum() > 1 else 0.0
        g["_composite"] = comp
        g["_dc"] = ((v - v.mean()) / sd) if sd > 0 else np.nan
        out.append(g)
    return pd.concat(out, ignore_index=True), cols, w


def _halves(ic_rows):
    early = [r for r in ic_rows if r[0] <= BUILD_HALF_SPLIT]
    late = [r for r in ic_rows if r[0] > BUILD_HALF_SPLIT]
    return early, late


def score_ic_arm(frame, col, label, population):
    """One incremental-IC arm on one population: full sample, both halves, and its own MDE."""
    rows = incremental_ic(frame, col, ["_dc"])
    if not rows:
        return {"arm": label, "population": population, "state": "NOT SCOREABLE",
                "why": "no date carried 20+ names with the signal, the control and an outcome"}
    vals = [r[1] for r in rows]
    full = hac_t(vals)
    e, l = _halves(rows)
    eh = hac_t([r[1] for r in e]) if len(e) >= 3 else None
    lh = hac_t([r[1] for r in l]) if len(l) >= 3 else None
    same_sign = bool(eh and lh and (eh["mean"] > 0) == (lh["mean"] > 0))
    v, why = stage1_verdict(
        {"n": len(e), "t": (eh or {}).get("t", 0.0)} if eh else {"n": len(e), "t": 0.0},
        {"n": len(l), "t": (lh or {}).get("t", 0.0)} if lh else {"n": len(l), "t": 0.0},
        same_sign, crit=CRIT, floor=MIN_HALF_DATES)
    return {
        "arm": label, "population": population,
        "dates": len(rows), "early_dates": len(e), "late_dates": len(l),
        "half_boundary": BUILD_HALF_SPLIT,
        "full": full, "early": eh, "late": lh,
        "halves_same_sign": same_sign,
        "median_ic": float(np.median(vals)), "mean_ic": float(np.mean(vals)),
        "p_two_sided": two_sided_p((full or {}).get("t"), len(rows)),
        "mde80": mde80((full or {}).get("se")),
        "observed_over_mde80": (None if not full or not mde80(full.get("se")) else
                                abs(full["mean"]) / mde80(full["se"])),
        "verdict": v, "verdict_why": why,
        "crit": CRIT, "crit_is": "UNCALIBRATED — conventional. No bar calibrated on the "
                                 "2,531-name panel transfers to this universe.",
    }


# ============================================================================================
# the construction arms — Don's margins, on the Index book
# ============================================================================================
def _ann(series):
    from scripts.tiered_pool_run import _ann as A
    return A(series)


def tier_junk_filter(ok_by_date, stats_sink=None):
    """A `universe_filter(rows, date)` that applies `junk_ok`'s verdict to EVERY name.

    **WHY NOT `TIERED-POOL`'s `junk_universe_filter`.** That wrapper's own docstring says it
    *"touches ONLY the bands below $10B; the >= $10B band is arm A's, unchanged"*, and its code
    passes `UNFILTERED_BAND` names through unconditionally. **So it cannot filter the incumbent
    tier**, which is exactly B1's population -- and reusing it returned an arm BIT-IDENTICAL to
    the incumbent, which is how the no-op was caught.

    `PREREG_stage1_batch2.md` says this itself: *"the filter has never touched the incumbent
    tier"*, which is the register's own reason B1 is genuinely un-run rather than a re-run.

    **THE SCREENS ARE STILL `TIERED-POOL`'s, VERBATIM.** `junk_ok` computes the verdict and is
    called unchanged; only the band exemption is dropped, because the band exemption is what the
    arm exists to remove. A name whose inputs do not resolve is NOT ok -- the conservative
    direction, inherited from `junk_ok` rather than re-decided here.
    """
    def _f(rows, date):
        ok = ok_by_date.get(str(date)[:10]) or {}
        out, dropped = [], 0
        for r in rows:
            if ok.get(r["ticker"]):
                out.append(r)
            else:
                dropped += 1
        if stats_sink is not None:
            stats_sink.setdefault(str(date)[:10], {})["dropped_by_junk"] = dropped
        return out
    return _f


def construction_arm(panel, cols, weights, kw, label):
    """One Index-book arm, via `TIERED-POOL`'s own `_score` (`B7`).

    **THE HALVES ARE THE REGISTER'S, NOT `_score`'s.** `_score` splits at the median date with
    the boundary embargoed; the register pre-committed the charter's Stage-1a boundary
    (2014-12-31, 24 / 20). Using `_score`'s own split would judge the arm on a boundary the
    register does not name, so the series is taken from `_score` and split here.
    """
    from scripts.tiered_pool_run import _score
    import scripts.tiered_pool as TP
    r = _score(panel, cols, weights, kw, label)
    if r is None:
        return {"arm": label, "state": "NOT SCOREABLE", "why": "_roth returned nothing"}
    ns = r.get("net_series") or []
    grid = sorted(panel["date"].unique())
    pairs = [(str(d)[:10], ns[i]) for i, d in enumerate(grid[:len(ns)])]
    e = [v for d, v in pairs if d <= BUILD_HALF_SPLIT]
    l = [v for d, v in pairs if d > BUILD_HALF_SPLIT]
    return {
        "arm": label,
        # CARRIED because `b2_overlay` scales it. Without it B2 reported NOT SCOREABLE for my
        # bug, which reads exactly like a data blocker.
        "net_series": ns,
        "roth_net_ann": r.get("roth_net_ann"),
        "roth_max_drawdown": r.get("roth_max_drawdown"),
        "roth_sharpe": r.get("roth_sharpe"),
        "annual_turnover": r.get("annual_turnover"),
        "realised_one_way_bps": r.get("realised_one_way_bps"),
        "early_ann_at_register_boundary": _ann(e) if e else None,
        "late_ann_at_register_boundary": _ann(l) if l else None,
        "early_mdd": TP._mdd(e) if e else None,
        "late_mdd": TP._mdd(l) if l else None,
        "early_periods": len(e), "late_periods": len(l),
        "half_boundary": BUILD_HALF_SPLIT,
        "halves_are_the_registers": "_score splits at the median date with the boundary "
                                    "embargoed; the register pre-committed 2014-12-31, so the "
                                    "series is re-split here rather than judged on a boundary "
                                    "the register does not name",
    }


def dons_rule(inc, arm):
    """Don's margins on BOTH halves of the build quadrant (register 0.5).

    **A CLEARING ARM IS `STAGE-1 PASS, 1999-2008 LEG NOT RUN`, AND THAT LABEL MAY NOT BE READ AS
    MEETING DON'S RULE.** His rule is a conjunction over 2009-2026 AND the 1999-2008 proxy;
    Stage 1 is the build quadrant only, so neither is available and reading either would spend a
    look that cannot be replaced. A FAILURE needs no proxy leg, because the rule is a
    conjunction.
    """
    out = {"allowance_pp": DON_DRAWDOWN_ALLOWANCE_PP, "halves": {}}
    ok = True
    for half in ("early", "late"):
        a = arm.get("%s_ann_at_register_boundary" % half)
        b = inc.get("%s_ann_at_register_boundary" % half)
        da = arm.get("%s_mdd" % half)
        db = inc.get("%s_mdd" % half)
        if None in (a, b, da, db):
            out["halves"][half] = {"state": "NOT ASSESSABLE"}
            ok = False
            continue
        ret_ok = bool(a > b)
        # max_drawdown is NEGATIVE, so the arm is worse when its value is MORE negative. The
        # gain is `arm - incumbent`, and S10's sign error is the one this reverses.
        dd_gain_pp = (float(da) - float(db)) * 100.0
        dd_ok = bool(dd_gain_pp >= -DON_DRAWDOWN_ALLOWANCE_PP)
        out["halves"][half] = {
            "arm_ann": a, "incumbent_ann": b, "return_beats": ret_ok,
            "arm_mdd": da, "incumbent_mdd": db,
            "drawdown_gain_pp": dd_gain_pp, "within_allowance": dd_ok,
            "clears": bool(ret_ok and dd_ok),
        }
        ok = ok and ret_ok and dd_ok
    out["verdict"] = ("STAGE-1 PASS, 1999-2008 LEG NOT RUN" if ok else "REJECTED")
    out["label_warning"] = ("a STAGE-1 PASS may NOT be read as meeting Don's rule: his rule is a "
                            "conjunction over 2009-2026 AND the 1999-2008 proxy, and Stage 1 "
                            "holds neither. It means the arm is worth a Stage-2 look and nothing "
                            "more.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=None)
    args = ap.parse_args(argv)
    f = fa()

    # ---- THE GATE. Conditional and reachable; a constant guard would make it dead code. ----
    kp = os.path.join(f, KILLS)
    if not os.path.exists(kp):
        raise SystemExit("REFUSING: no kill artifact at %s. The kills run in their OWN pass and "
                         "are READ before any arm is scored (O10)." % kp)
    with io.open(kp, encoding="utf-8") as fh:
        kills = json.load(fh)
    failed = [k for k, v in (kills.get("kills") or {}).items() if v.get("kill_passes") is not True]
    if failed:
        raise SystemExit("REFUSING: these kills did not pass: %s. An arm behind a failed "
                         "pre-outcome control is not scored." % failed)

    ppath = args.panel or os.path.join(f, PANEL)
    panel = pd.read_pickle(ppath)
    quad, qcen = build_quadrant(panel)
    tier, tcen = tier_frame(quad)
    print("quadrant %d rows | tier %d rows (%d names)"
          % (qcen["rows"], tcen["rows"], tcen["names"]), flush=True)

    # ---- the control column, on both populations ----
    qf, cols, weights = deployed_control(quad)
    tf, _, _ = deployed_control(tier)
    print("control: deployed composite z-scored within date, %d themes alive" % len(cols),
          flush=True)

    # ---- the signals ----
    from scripts.tiered_pool_run import _hist
    hist = _hist(os.path.join(data_root(), "full2009", "backtest"))
    mc = monthly_closes(sorted(quad["ticker"].astype(str).unique()))

    print("building B3 (residual momentum) ...", flush=True)
    s3 = b3_signal(quad, mc)
    print("building B5 (net payout) ...", flush=True)
    s5 = b5_signal(quad, hist)
    print("building B4 (analyst neglect) ...", flush=True)
    s4, b4cov = b4_neglect(quad)
    print("  B4 coverage: %s" % {k: v for k, v in b4cov.items() if k != "note"}, flush=True)

    ic_arms, pvals = {}, {}
    for label, sig in (("B3_residual_momentum", s3),
                       ("B4_analyst_neglect", s4),
                       ("B5_net_payout", s5)):
        if not sig:
            ic_arms[label] = {"arm": label, "state": "NOT RUN",
                              "why": "the signal could not be built on this quadrant"}
            pvals[label] = None
            continue
        wide = score_ic_arm(attach_signal(qf, sig, "_sig"), "_sig", label, "FULL corrected")
        tiny = score_ic_arm(attach_signal(tf, sig, "_sig"), "_sig", label,
                            "the incumbent's own $10B tier")
        gov = tiny.get("verdict")
        ic_arms[label] = {
            "arm": label, "full_universe": wide, "tier": tiny,
            "THE_TIER_GOVERNS": gov,
            "stage1b": ("REAL BUT NOT INVESTABLE HERE"
                        if (wide.get("verdict") == "CLEARS" and gov != "CLEARS")
                        else gov),
        }
        pvals[label] = (tiny or {}).get("p_two_sided")

    bh = benjamini_hochberg(pvals, k=BH_K, q=BH_Q)

    # ---- the construction arms ----
    print("construction arms on the Index book ...", flush=True)
    import scripts.tiered_pool as TP
    from scripts.tiered_pool_run import INCUMBENT_KW
    okbd = {}
    for d in sorted(quad["date"].unique()):
        as_of = str(d)[:10]
        g = quad[quad["date"] == d]
        okbd[as_of], _ = TP.junk_ok(list(g["ticker"].astype(str)), hist, as_of)
    inc = construction_arm(quad, cols, weights, dict(INCUMBENT_KW), "0_incumbent")
    # `tier_junk_filter`, NOT `TP.junk_universe_filter` -- that wrapper exempts the >= $10B
    # band by design and returned an arm BIT-IDENTICAL to the incumbent. The SCREENS are
    # TIERED-POOL's verbatim (`junk_ok` above); only the band exemption is dropped.
    b1sink = {}
    b1 = construction_arm(quad, cols, weights,
                          dict(INCUMBENT_KW,
                               universe_filter=tier_junk_filter(okbd, stats_sink=b1sink)),
                          "B1_junk_on_the_tier")
    b1["dropped_by_junk_per_date"] = b1sink
    b1["filter_is_not_inert"] = bool(
        any((v or {}).get("dropped_by_junk", 0) > 0 for v in b1sink.values()))
    b2 = b2_overlay(inc, quad, tier, mc)

    res = {
        "item": "STAGE1-BATCH2 — the five arms",
        "register": REGISTER, "panel": os.path.basename(ppath),
        "trials": 5, "trials_booked_before_any_runner_existed": True,
        "kill_pass_read_first": True,
        "statistic": "charter Stage 1a — the DEPLOYED COMPOSITE as a SINGLE control, "
                     "composite_from_frame CALLED and z-scored within date",
        "populations": "charter Stage 1b — BOTH, and THE TIER GOVERNS",
        "crit_is_UNCALIBRATED": CRIT,
        "k": BH_K, "q": BH_Q,
        "build_quadrant": qcen, "tier": tcen,
        "ic_arms": ic_arms,
        "benjamini_hochberg": bh,
        "construction_arms": {
            # A GATE, ADDED AFTER A BIT-IDENTICAL ARM WAS NEARLY REPORTED AS REJECTED. If the
            # filter changed no figure, the result is a statement about a DROPPED ARGUMENT and
            # not about junk -- so it is flagged rather than scored.
            "B1_identical_to_incumbent": bool(
                b1.get("roth_net_ann") == inc.get("roth_net_ann")
                and b1.get("roth_max_drawdown") == inc.get("roth_max_drawdown")),
            "0_incumbent": inc,
            "B1_junk_on_the_tier": b1, "B1_dons_rule": dons_rule(inc, b1),
            "B2_vol_managed": b2, "B2_dons_rule": dons_rule(inc, b2),
        },
        "B4_data_coverage": b4cov,
        "B6": "WITHDRAWN (register 0.1); k STAYS 6",
        "adopts_nothing": True, "changes_no_public_page": True,
    }
    dest = os.path.join(f, OUT)
    with io.open(dest, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2, default=str)

    print("\n=== IC ARMS (the tier governs)", flush=True)
    for k, v in ic_arms.items():
        print("  %-24s %s" % (k, v.get("stage1b") or v.get("state")), flush=True)
    print("\n=== BH at k=%d q=%.2f" % (BH_K, BH_Q), flush=True)
    for k, v in (bh.get("arms") or {}).items():
        print("  %-24s p=%s survives=%s" % (k, v.get("p"), v.get("survives_bh")), flush=True)
    print("\n=== CONSTRUCTION ARMS (Don's margins, both halves)", flush=True)
    for k in ("B1_dons_rule", "B2_dons_rule"):
        print("  %-24s %s" % (k, res["construction_arms"][k]["verdict"]), flush=True)
    print("\nwrote %s" % dest, flush=True)
    return 0


#: DECLARED, because the register names `numest` without naming the forecast period. `fpi == "1"`
#: and `fiscalp == "ANN"` is the one-year-ahead ANNUAL consensus -- the conventional "number of
#: analysts covering", and the only `fpi` whose count is comparable across names. A mixed-`fpi`
#: count sums a name's annual and quarterly panels and reads as coverage twice over.
B4_FPI = "1"
B4_FISCALP = "ANN"
B4_FIRST_YEAR = 2006        # the quadrant starts 2009; a few prior years cover the lookback
B4_LAST_YEAR = 2020


def b4_neglect(frame, hist=None):
    """`numest` from IBES `statsum`, on the DATED link, scaled by firm size.

    **`K0` MEASURED THE LINK, NOT THE DATA, AND THAT IS A REAL DISTINCTION.** `K0`'s 0.8597 is
    the dated `ibes_id` link's coverage of the tier; `numest` lives in `ibes_statsum_epsus`, a
    different table, and a name the link resolves may still carry no consensus row. So this
    function reports its OWN coverage and the arm's scoreability follows from it rather than
    from `K0`.

    **SCALED BY SIZE SO IT IS NEGLECT RATHER THAN A SIZE PROXY**: the signal is the residual of
    `log(1 + numest)` on `log(market_cap)` WITHIN DATE, so it measures coverage *relative to
    what a name of that size usually attracts*. The costume kill against `size` ran first and
    independently -- this scaling is the CONSTRUCTION, not the control, and conflating the two
    is how a candidate comes to be judged by its own adjustment.

    **THE SIGN: MORE NEGLECT IS A HIGHER SIGNAL.** The residual is NEGATED, so a name with fewer
    analysts than its size predicts scores high. The hypothesis is that neglect is rewarded, and
    getting the sign backwards would test the opposite hypothesis under this one's name.
    """
    import glob
    import numpy as np
    import pandas as pd
    from valuation.edge import ibes_link as IL

    # ---- the consensus panel, read once -------------------------------------------------
    rows = []
    for y in range(B4_FIRST_YEAR, B4_LAST_YEAR + 1):
        g = glob.glob(os.path.join(IL.RAW, "ibes_statsum_epsus",
                                   "ibes_statsum_epsus_%d.*" % y))
        for q in g:
            try:
                d = IL._read(q)
            except Exception:
                continue
            if d is None or getattr(d, "empty", True):
                continue
            keep = [c for c in ("ticker", "statpers", "fpi", "fiscalp", "numest") if c in d.columns]
            if len(keep) < 5:
                continue
            d = d[keep]
            d = d[(d["fpi"].astype(str) == B4_FPI)
                  & (d["fiscalp"].astype(str).str.upper() == B4_FISCALP)]
            if not d.empty:
                rows.append(d)
    if not rows:
        return {}, {"state": "NOT RUN", "why": "no ibes_statsum_epsus files resolved under %s"
                                               % IL.RAW}
    sm = pd.concat(rows, ignore_index=True)
    sm["statpers"] = pd.to_datetime(sm["statpers"], errors="coerce")
    sm["numest"] = pd.to_numeric(sm["numest"], errors="coerce")
    sm = sm.dropna(subset=["statpers", "numest", "ticker"])
    sm = sm.sort_values("statpers")

    # ---- the dated link, through the SAME code the validator uses (B7) -------------------
    ids = IL.ibes_id()
    cusip_spans, _ = IL.spans(ids, key="cusip")
    crsp = IL.crsp_names()
    cr = IL.crsp_spans(crsp) if crsp is not None else None
    if cr is None:
        return {}, {"state": "NOT RUN", "why": "crsp_stocknames absent, so no DATED route"}
    cells = frame[["ticker", "date"]].drop_duplicates().copy()
    cells["date"] = pd.to_datetime(cells["date"])
    rb = IL.resolve_route_b(cusip_spans, cr, cells)
    link = {(t, pd.Timestamp(d)): v for t, d, v, st
            in rb[["ticker", "date", "resolved", "state"]].itertuples(index=False)
            if st == IL.OK and v}

    # ---- latest consensus at or before each date, per IBES ticker ------------------------
    by_tk = {}
    for tk, g in sm.groupby(sm["ticker"].astype(str)):
        by_tk[tk] = (g["statpers"].values, g["numest"].values)

    sig, cov = {}, {"cells": 0, "linked": 0, "with_consensus": 0}
    for d in sorted(frame["date"].unique()):
        dd = pd.Timestamp(str(d)[:10])
        g = frame[frame["date"] == d]
        raw = {}
        for t, mc in zip(g["ticker"].astype(str),
                         pd.to_numeric(g["market_cap"], errors="coerce")):
            cov["cells"] += 1
            ib = link.get((t, dd))
            if not ib:
                continue
            cov["linked"] += 1
            got = by_tk.get(str(ib))
            if got is None:
                continue
            idx = np.searchsorted(got[0], np.datetime64(dd), side="right") - 1
            if idx < 0:
                continue
            n = float(got[1][idx])
            if not np.isfinite(n) or n < 0:
                continue
            m = float(mc) if mc == mc and mc and mc > 0 else None
            if m is None:
                continue
            cov["with_consensus"] += 1
            raw[t] = (np.log1p(n), np.log(m))
        if len(raw) < 20:
            continue
        ts = sorted(raw)
        y = np.array([raw[t][0] for t in ts], dtype=float)
        x = np.array([raw[t][1] for t in ts], dtype=float)
        A = np.column_stack([np.ones(len(x)), x])
        try:
            beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        except Exception:
            continue
        resid = y - A @ beta
        # NEGATED: more neglect is a HIGHER signal. The hypothesis is that neglect is rewarded.
        sig[str(d)[:10]] = {t: float(-r) for t, r in zip(ts, resid)}
    cov["cell_coverage"] = (cov["with_consensus"] / cov["cells"]) if cov["cells"] else 0.0
    cov["dates_scored"] = len(sig)
    cov["note"] = ("K0 measured the LINK's coverage; this is the DATA's. A name the link "
                   "resolves may carry no consensus row, so the arm's scoreability follows from "
                   "THIS figure rather than from K0's 0.8597.")
    return sig, cov


def b2_overlay(inc, quad, tier, mc):
    """Volatility-managed exposure: scale the incumbent book's per-period net return by
    `min(1, c / sigma^2_{t-1})`, with `c` set so average exposure over the quadrant is 1.0.

    **HOLDING LESS IS HOLDING CASH, SO THE OVERLAY SCALES THE RETURN SERIES** rather than the
    universe — which is why it is not an `index_fn` or a `universe_filter`. Un-held weight earns
    nothing, which is the conservative treatment: crediting it a cash yield would flatter the
    arm on a Roth with no money-market sleeve modelled.
    """
    import scripts.tiered_pool as TP
    from scripts.stage1_batch2_kills import MIN_NAMES_PER_DATE
    ns = inc.get("net_series") or []
    grid = sorted(quad["date"].unique())
    rets = mc.pct_change()
    sig2 = {}
    for d in grid:
        dd = pd.Timestamp(str(d)[:10])
        names = [t for t in tier[tier["date"] == d]["ticker"].astype(str).unique()
                 if t in rets.columns]
        if len(names) < MIN_NAMES_PER_DATE:
            continue
        win = rets.loc[(rets.index < dd), names].tail(3)
        if win.shape[0] < 2:
            continue
        book = win.mean(axis=1).dropna()
        if len(book) < 2:
            continue
        v = float(np.var(book.values, ddof=1))
        if v > 0:
            sig2[str(d)[:10]] = v
    if not sig2 or not ns:
        return {"arm": "B2_vol_managed", "state": "NOT SCOREABLE",
                "why": "no prior-window variance, or the incumbent produced no net series"}
    inv = {d: 1.0 / v for d, v in sig2.items()}
    c = 1.0 / float(np.mean(list(inv.values())))
    w = {d: min(1.0, c * iv) for d, iv in inv.items()}
    scaled, pairs = [], []
    for i, d in enumerate(grid[:len(ns)]):
        dd = str(d)[:10]
        x = ns[i] * w.get(dd, 1.0)
        scaled.append(x)
        pairs.append((dd, x))
    e = [v for d, v in pairs if d <= BUILD_HALF_SPLIT]
    l = [v for d, v in pairs if d > BUILD_HALF_SPLIT]
    return {
        "arm": "B2_vol_managed",
        "net_series": scaled,
        "roth_net_ann": _ann(scaled),
        "roth_max_drawdown": TP._mdd(scaled),
        "roth_sharpe": TP._sharpe(scaled),
        "early_ann_at_register_boundary": _ann(e) if e else None,
        "late_ann_at_register_boundary": _ann(l) if l else None,
        "early_mdd": TP._mdd(e) if e else None,
        "late_mdd": TP._mdd(l) if l else None,
        "early_periods": len(e), "late_periods": len(l),
        "half_boundary": BUILD_HALF_SPLIT,
        "mean_exposure": float(np.mean(list(w.values()))),
        "median_exposure": float(np.median(list(w.values()))),
        "dates_capped_at_1": int(sum(1 for v in w.values() if v >= 1.0)),
        "cap_is_a_declared_deviation": "the paper levers UP when volatility is low; a Roth has "
                                       "no margin, so this is de-risk-only and WEAKER than the "
                                       "paper's -- declared, not discovered",
        "un_held_weight_earns_nothing": "the conservative treatment; crediting a cash yield "
                                        "would flatter the arm on a Roth with no money-market "
                                        "sleeve modelled",
        "R1_VAR_governs": "a Sharpe or volatility gain alone is NOT a pass. The Index book's own "
                          "net Sharpe is 1.0318 published and 0.9694 corrected -- not bad -- so "
                          "R1-VAR's antecedent does not fire. (The draft cited 0.5866, which is "
                          "the RESEARCH DECILE book's Sharpe; register 0.4.)",
    }


if __name__ == "__main__":
    sys.exit(main())
