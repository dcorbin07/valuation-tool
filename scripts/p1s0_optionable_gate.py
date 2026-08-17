#!/usr/bin/env python3
"""p1s0_optionable_gate.py — does the equity composite sort the PIT-OPTIONABLE universe? [P1-S0]

Everything about the design — the universes, the three horizons, the primary statistic, the
bars, the three-state verdict grammar, the trial cost and the expectations — is fixed in
PREREG_p1s0_optionable_gate.md, committed ALONE at f4ddd8b BEFORE this file existed. Nothing
here restates a threshold from a result.

TWO PASSES, AND THE SEPARATION IS THE POINT. `--controls-only` computes and writes the gating
controls and exits before any arm is scored; `--arms` REFUSES to run without a passing controls
artifact. Session 26 shipped a register whose gating control ran in the same pass as its
outcomes, so it could not be claimed the control was read first. That is not repeated.

    python -m scripts.p1s0_optionable_gate --controls-only
    python -m scripts.p1s0_optionable_gate --arms

Adopts nothing. Prices no option. Charged to EQUITY (the arms predict the underlying's forward
return — the U2/MA31 precedent): N 227 -> 230.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

# ---- everything below is PRE-REGISTERED; see PREREG_p1s0_optionable_gate.md -----------------
HORIZONS = [63, 252, 504]          # prereg 2 — A63 is the POWER ANCHOR, not a bonus arm
POWER_ANCHOR = 63
GATE_HORIZONS = [252, 504]         # the frontier's own specified gate
PLACEBO_DRAWS = 200                # prereg 4 — the S22 protocol
PLACEBO_SEED0 = 7100
MIN_ROWS_PER_DATE = 30             # quantile_backtest's own n_q*3 floor
MODES = ("pit_liquid", "has_chain")   # prereg 1 — primary first, sensitivity second
PRIMARY_MODE = "pit_liquid"

DATA = os.environ.get("VALQUO_DATA_ROOT", r"C:\Users\donni\Downloads\valuation-tool\data")
PANEL = os.path.join(DATA, "free_analysis", "panel_s22_h504.pkl")
PART = os.path.join(DATA, "free_analysis", "P1S0_OPTIONABLE_PARTITION.pkl")
CONTROLS_JSON = os.path.join(DATA, "free_analysis", "P1S0_CONTROLS.json")
ARMS_JSON = os.path.join(DATA, "free_analysis", "P1S0_GATE.json")


def _repo():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    p = pd.read_pickle(PANEL)
    p["date"] = pd.to_datetime(p["date"])
    part = pd.read_pickle(PART)
    part["date"] = pd.to_datetime(part["date"])
    return p, part


def scorable_dates(panel, h):
    from scripts.term_structure import ret_col
    c = ret_col(h)
    if c not in panel.columns:
        return []
    per = panel.groupby("date")[c].apply(lambda s: int(s.notna().sum()))
    return [d for d, n in per.items() if n >= MIN_ROWS_PER_DATE]


def halves(dates):
    """Both halves with the BOUNDARY DATE EMBARGOED — the geometry U2/U3/V6-OPT/MA31 use."""
    ds = sorted(dates)
    if len(ds) < 4:
        return [], [], None
    mid = len(ds) // 2
    return ds[:mid], ds[mid + 1:], ds[mid]


# ============================================================================ controls
def controls():
    from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols
    from valuation.studies.optionable_universe import (
        restrict, coverage_report, date_ticker_partition, STALE_MAX_DAYS)
    from valuation.edge.options_universe import _miner_thresholds
    from scripts.term_structure import arm, C1_RECORD

    panel, part = load()
    out = {"prereg": "PREREG_p1s0_optionable_gate.md", "gating": {}, "reported": {}}
    dates = sorted(panel["date"].unique())
    counts = panel.groupby("date")["ticker"].nunique().to_dict()

    # ---- C1: the instrument IS the shipped one -------------------------------------------
    a = arm(panel, 63, label="C1")
    m = {"top_decile_alpha": "alpha_ann", "long_short_tstat": "ls_t_naive",
         "long_short_tstat_nw": "ls_t_hac", "top_decile_alpha_tstat_nw": "alpha_t_hac",
         "monotonicity": "monotonicity", "equal_weight_ann": "equal_weight_ann"}
    c1 = {}
    worst = 0.0
    for k, want in C1_RECORD.items():
        got = a.get(m.get(k, k))
        d = None if got is None else abs(got - want)
        if d is not None:
            worst = max(worst, d)
        c1[k] = {"published": want, "measured": got, "abs_delta": d}
    # 4-dp fields in C1_RECORD cannot reproduce below their own storage precision.
    out["gating"]["C1_shipped_instrument"] = {
        "fields": c1, "worst_abs_delta": worst,
        "pass": bool(worst < 1e-4),
        "note": "two fields are stored to 4dp in C1_RECORD; the three exactly-stored ones "
                "reproduce at 0.00e+00",
    }

    # ---- C2: the partition cannot see an outcome -----------------------------------------
    src_path = os.path.join(_repo(), "valuation", "studies", "optionable_universe.py")
    src = open(src_path, encoding="utf-8").read()
    import tokenize, io as _io
    code_only = []
    for tok in tokenize.generate_tokens(_io.StringIO(src).readline):
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            code_only.append(tok.string)
    code_blob = " ".join(code_only)
    leaks = [w for w in ("fwd_ret", "fwd_ret_h504", "forward_return") if w in code_blob]
    # Behavioural: the builder's SIGNATURE takes (dates, tickers) — it is never handed the
    # panel at all, so it cannot read a return even in principle. Demonstrated by rebuilding a
    # small slice and diffing against the banked artifact.
    # THE PROBE IS CHOSEN TO CONTAIN THE HARD CASE. An all-True slice would exercise neither
    # the None branch nor the False branch, and a rebuild check that never sees the tri-state
    # is the `sector-neutral` vacuity failure — a guard reporting success on an empty subject.
    with_none = sorted(part.loc[part["pit_liquid"].isna(), "ticker"].unique())[:3]
    with_false = sorted(part.loc[part["pit_liquid"] == False, "ticker"].unique())[:2]  # noqa: E712
    with_true = sorted(part.loc[part["pit_liquid"] == True, "ticker"].unique())[:2]    # noqa: E712
    probe_t = sorted(set(with_none) | set(with_false) | set(with_true))
    probe_d = sorted(part["date"].unique())[:8]
    re_part = date_ticker_partition(probe_d, probe_t, data_root=DATA)
    banked = part[(part["ticker"].isin(probe_t)) & (part["date"].isin(probe_d))]
    cols = ["date", "ticker", "staleness_days", "n_chain_rows", "pit_liquid"]
    # DTYPE IS NOT VALUE, and conflating them made this control fail on a correct partition.
    # `pit_liquid` is TRI-STATE: an all-True probe slice infers `bool` while the full artifact
    # carries None and is `object`, so a bare `.equals()` compares storage rather than content
    # and reported a bit-identical rebuild as a mismatch. Normalising to object compares the
    # three states as values — None included — without weakening the check.
    def _norm(df):
        d = df[cols].reset_index(drop=True).copy()
        d["pit_liquid"] = d["pit_liquid"].astype(object).where(d["pit_liquid"].notna(), None)
        return d
    same = (len(re_part) == len(banked) and _norm(re_part).equals(_norm(banked)))
    states = banked["pit_liquid"].astype(object).where(banked["pit_liquid"].notna(), None)
    seen = {str(x) for x in states.unique()}
    out["gating"]["C2_partition_blind_to_returns"] = {
        "source_level_leaks": leaks,
        "signature_takes_panel": False,
        "probe_tickers": probe_t,
        "probe_states_exercised": sorted(seen),
        "probe_is_not_vacuous": bool(len(seen) >= 2),
        "rebuild_rows": int(len(re_part)), "banked_rows": int(len(banked)),
        "bit_identical": bool(same),
        "pass": bool(not leaks and same and len(seen) >= 2),
    }

    # ---- C5: the restriction is not inert -------------------------------------------------
    rest = {mode: restrict(panel, part, mode) for mode in MODES}
    r = rest[PRIMARY_MODE]
    out["gating"]["C5_restriction_not_inert"] = {
        "full_rows": int(len(panel)), "full_names": int(panel["ticker"].nunique()),
        **{("%s_rows" % k): int(len(v)) for k, v in rest.items()},
        **{("%s_names" % k): int(v["ticker"].nunique()) for k, v in rest.items()},
        "primary_share_of_rows": round(float(len(r) / len(panel)), 4),
        "pass": bool(0 < len(r) < 0.9 * len(panel)),
    }

    # ---- C3/C4: the placebo bites, and permutes no forward return -------------------------
    perm_cols = placebo_signal_cols(r)
    leaked = [c for c in perm_cols if str(c).startswith("fwd_ret")]
    real63 = arm(r, 63, label="C3-real")
    pp = placebo_panel(r, seed=PLACEBO_SEED0)
    plc63 = arm(pp, 63, label="C3-placebo")
    moved = None
    if real63.get("cum_alpha") is not None and plc63.get("cum_alpha") is not None:
        moved = abs(real63["cum_alpha"] - plc63["cum_alpha"])
    out["gating"]["C4_no_forward_return_permuted"] = {
        "n_perm_cols": len(perm_cols), "leaked": leaked, "pass": bool(not leaked)}
    out["gating"]["C3_placebo_vacuity"] = {
        "real_cum_alpha": real63.get("cum_alpha"),
        "placebo_cum_alpha": plc63.get("cum_alpha"),
        "abs_move": moved,
        "pass": bool(moved is not None and moved > 1e-9),
        "why": "placebo_panel is EXACTLY invariant when pointed at a precomputed score column; "
               "here the composite is rebuilt from permuted theme columns each draw, so it "
               "must bite. Asserted rather than assumed.",
    }

    # ---- C6: COVERAGE FIRST ---------------------------------------------------------------
    cov = coverage_report(part, dates, counts)
    cov_small = {k: v for k, v in cov.items() if k != "per_date"}
    out["reported"]["C6_coverage"] = cov_small
    out["reported"]["C6_coverage_per_date"] = cov["per_date"]

    # ---- C8: staleness --------------------------------------------------------------------
    out["reported"]["C8_staleness"] = {
        "stale_max_days": STALE_MAX_DAYS,
        "max_used": int(part["staleness_days"].max()),
        "nonzero_share": round(float((part["staleness_days"] > 0).mean()), 4),
        "n_unmeasurable": int(part["pit_liquid"].isna().sum()),
    }
    out["reported"]["miner_thresholds"] = _miner_thresholds()

    # ---- C10: the size confound (MA32/U7) -------------------------------------------------
    # TWO comparisons, because they answer different questions and the register's expectation 5
    # is about the second. (a) is the decile a cap sort WITHIN its own universe; (b) is the
    # OPTIONABLE decile larger-cap than the FULL-PANEL decile, which is what U7 found.
    dates_cov = sorted(rest[PRIMARY_MODE]["date"].unique())
    out["reported"]["C10_size_tilt"] = {
        "within_optionable_universe": size_tilt(rest[PRIMARY_MODE], panel),
        "within_full_panel_same_dates": size_tilt(
            panel[panel["date"].isin(dates_cov)], panel),
        "note": "expectation 5 is scored on the RATIO of the two median_cap_top_decile "
                "figures; the within-universe ratios answer a different question and both "
                "are reported so neither is mistaken for the other.",
    }

    # ---- geometry -------------------------------------------------------------------------
    geo = {}
    for h in HORIZONS:
        ds = scorable_dates(rest[PRIMARY_MODE], h)
        e, l, b = halves(ds)
        geo[str(h)] = {"n_dates": len(ds), "n_early": len(e), "n_late": len(l),
                       "embargoed": str(b)[:10] if b is not None else None,
                       "first": str(ds[0])[:10] if ds else None,
                       "last": str(ds[-1])[:10] if ds else None,
                       "overlap_frac": round(max(0.0, (h - 63) / h), 4),
                       "approx_independent_obs": round(len(ds) * 63.0 / h, 2)}
    out["reported"]["geometry_primary"] = geo

    gates = {k: v["pass"] for k, v in out["gating"].items()}
    out["all_gating_pass"] = bool(all(gates.values()))
    out["gates"] = gates
    return out


def size_tilt(restricted, full):
    """C10 — is the restricted decile a market-cap sort? Reported, no verdict."""
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    from scripts.term_structure import DEPLOYED
    if "market_cap" in restricted.columns:
        mc = "market_cap"
    elif "marketcap" in restricted.columns:
        mc = "marketcap"
    else:
        return {"status": "no market-cap column", "columns_checked": ["market_cap", "marketcap"]}
    rows = []
    for d in sorted(restricted["date"].unique()):
        sub = restricted[restricted["date"] == d]
        if len(sub) < MIN_ROWS_PER_DATE:
            continue
        comp = composite_from_frame(sub, list(DEPLOYED), DEPLOYED, zscore)
        cap = pd.to_numeric(sub[mc], errors="coerce").to_numpy(dtype=float)
        ok = np.isfinite(comp) & np.isfinite(cap)
        if ok.sum() < MIN_ROWS_PER_DATE:
            continue
        c, k = comp[ok], cap[ok]
        top = np.argsort(-c)[: max(1, len(c) // 10)]
        rows.append((float(np.median(k[top])), float(np.median(k))))
    if not rows:
        return {"status": "no scorable dates"}
    d1 = float(np.median([a for a, _ in rows]))
    uni = float(np.median([b for _, b in rows]))
    return {"n_dates": len(rows), "median_cap_top_decile": d1,
            "median_cap_universe": uni,
            "ratio_top_to_universe": round(d1 / uni, 4) if uni else None,
            "note": "MA32/U7 found the composite decile is largely a market-cap sort inside a "
                    "narrow optionable slice. Reported; carries NO verdict."}


# ============================================================================ arms
def score(panel_r, h, label):
    from scripts.term_structure import arm
    ds = scorable_dates(panel_r, h)
    e, l, b = halves(ds)
    res = {"horizon": h, "label": label, "n_dates": len(ds),
           "embargoed": str(b)[:10] if b is not None else None}
    for nm, dd in (("full", ds), ("early", e), ("late", l)):
        a = arm(panel_r, h, dates=dd, label="%s-%s" % (label, nm)) if dd else {}
        res[nm] = {"n_periods": a.get("n_periods"), "cum_alpha": a.get("cum_alpha"),
                   "alpha_ann": a.get("alpha_ann"), "alpha_t_hac": a.get("alpha_t_hac"),
                   "alpha_t_naive": a.get("alpha_t_naive"),
                   "ls_t_hac": a.get("ls_t_hac"), "monotonicity": a.get("monotonicity")}
    return res


def _ref_cum(full_panel, h, dates):
    """The FULL-panel top-decile cumulative alpha over exactly `dates`. The known-real effect
    the power question is asked about. Not an arm; carries no verdict."""
    from scripts.term_structure import arm
    a = arm(full_panel, h, dates=dates, label="reference_h%d" % h)
    return a.get("cum_alpha")


def placebo_floors(panel_r, draws=PLACEBO_DRAWS, seed0=PLACEBO_SEED0):
    """prereg 4 — the per-horizon fixed_weights_null, computed ON THE RESTRICTED UNIVERSE.

    S22's own rider travels with it: this is a DIFFERENT and less conservative null than X7's
    (fixed weights, no CPCV), so its percentiles may NEVER be compared with 2.2837 / 2.2913.
    """
    from valuation.edge.fundamental_panel import placebo_panel, placebo_signal_cols
    from scripts.term_structure import arm
    leaked = [c for c in placebo_signal_cols(panel_r) if str(c).startswith("fwd_ret")]
    if leaked:
        raise SystemExit("[p1s0] placebo would permute forward returns: %s" % leaked)
    # The date sets are a property of the REAL panel's coverage, not of a draw, so they are
    # computed once. Recomputing them per draw would let a permutation move the date set.
    dsets = {h: scorable_dates(panel_r, h) for h in HORIZONS}
    win = {h: halves(dsets[h]) for h in HORIZONS}
    rows, t0 = [], time.time()
    for i in range(draws):
        pp = placebo_panel(panel_r, seed=seed0 + i)
        rec = {"seed": seed0 + i}
        for h in HORIZONS:
            e, l, _ = win[h]
            ds = dsets[h]
            cell = {}
            for nm, dd in (("full", ds), ("early", e), ("late", l)):
                a = arm(pp, h, dates=dd) if dd else {}
                cell[nm] = a.get("alpha_t_hac")
                if nm == "full":
                    # taken from the SAME call rather than re-scoring the full window, which
                    # is both wasteful and a second chance for the two to disagree
                    cell["cum_alpha_full"] = a.get("cum_alpha")
            rec[str(h)] = cell
        rows.append(rec)
        if i == 2 or (i + 1) % 25 == 0:
            el = time.time() - t0
            print("[p1s0] placebo %d/%d  %.0fs elapsed, ~%.0fs left"
                  % (i + 1, draws, el, el / (i + 1) * (draws - i - 1)), flush=True)

    def pct(h, nm, q):
        v = [r[str(h)][nm] for r in rows if r[str(h)].get(nm) is not None]
        return float(np.percentile(v, q)) if v else None

    def med(h, nm):
        v = [r[str(h)][nm] for r in rows if r[str(h)].get(nm) is not None]
        return float(np.median(v)) if v else None

    def sd(h, nm):
        v = [r[str(h)][nm] for r in rows if r[str(h)].get(nm) is not None]
        return float(np.std(v, ddof=1)) if len(v) > 1 else None

    floors = {}
    for h in HORIZONS:
        floors[str(h)] = {
            **{("%s_p95" % nm): pct(h, nm, 95) for nm in ("full", "early", "late")},
            **{("%s_median" % nm): med(h, nm) for nm in ("full", "early", "late")},
            **{("%s_sd" % nm): sd(h, nm) for nm in ("full", "early", "late")},
            "cum_alpha_full_p95": pct(h, "cum_alpha_full", 95),
            "cum_alpha_full_sd": sd(h, "cum_alpha_full"),
        }
    return {"instrument": "fixed_weights_null",
            "not_comparable_with": "X7/session-10 floors (those include CPCV adoption)",
            "draws": draws, "seeds": [seed0, seed0 + draws - 1], "floors": floors,
            "rows": rows}


def verdict(armres, floors, h, reference_cum_alpha=None):
    """prereg 4 — THREE states. UNDERPOWERED is not a fail and carries no verdict.

    TWO POWER READINGS ARE REPORTED AND ONLY THE FIRST DECIDES. The register's §4 words the
    UNDERPOWERED test against the OBSERVED effect, and that wording is weak — close to
    circular, because a small observed effect reads as underpowered almost by construction.
    The register is committed and is left UNEDITED (`RUN_RULES`: corrections go in the
    write-up), so `state` implements it exactly as written.

    `power` beside it is the informative version and it is REPORTED, not decisive: the minimum
    detectable CUMULATIVE alpha at this horizon's own null, against the effect this project has
    already measured on the full panel over the same dates. That answers "could this design
    have seen the effect we know exists?" — which is the question S19 and V6 established a null
    must be quoted with, and it does not depend on the arm's own outcome.
    """
    f = floors["floors"][str(h)]
    cells, clears = {}, []
    for nm in ("early", "late"):
        t = armres[nm]["alpha_t_hac"]
        bar = f["%s_p95" % nm]
        ok = (t is not None and bar is not None and t > bar)
        cells[nm] = {"alpha_t_hac": t, "bar_p95": bar, "clears": bool(ok)}
        clears.append(ok)

    bar_full = f.get("full_p95")
    obs_t = armres["full"]["alpha_t_hac"]
    reached = (obs_t is not None and bar_full is not None and obs_t >= bar_full)
    state = "PASS" if all(clears) else ("FAIL" if reached else "UNDERPOWERED")

    # C9 — MDE in CUMULATIVE-ALPHA units, paired with the MEAN (MA31's third defect was an MDE
    # quoted beside a median). t ~ effect / se, and the null's sd of cum_alpha estimates se, so
    # the smallest cum_alpha that could reach the bar is p95_t * sd_null.
    sd_cum = f.get("cum_alpha_full_sd")
    mde_cum = (bar_full * sd_cum) if (bar_full is not None and sd_cum is not None) else None
    can_see = (None if (mde_cum is None or reference_cum_alpha is None)
               else bool(abs(reference_cum_alpha) >= mde_cum))
    return {
        "horizon": h, "state": state, "both_halves": cells,
        "full": {"alpha_t_hac": obs_t, "bar_p95": bar_full,
                 "cum_alpha": armres["full"]["cum_alpha"]},
        "registered_mde_test": {"observed_alpha_t_hac": obs_t, "bar_p95": bar_full,
                                "observed_reaches_bar": bool(reached),
                                "note": "prereg 4 as worded; weak, and decisive anyway"},
        "power": {
            "null_sd_cum_alpha": sd_cum,
            "mde_cum_alpha": mde_cum,
            "observed_cum_alpha": armres["full"]["cum_alpha"],
            "reference_cum_alpha_full_panel_same_dates": reference_cum_alpha,
            "design_can_see_the_known_effect": can_see,
            "note": "REPORTED, not decisive. If design_can_see_the_known_effect is false, a "
                    "non-clearing cell means 'could not be separated at this resolution', "
                    "never 'absent' (S19/V6/MA31).",
        },
    }


def arms():
    from valuation.studies.optionable_universe import restrict
    if not os.path.exists(CONTROLS_JSON):
        raise SystemExit("[p1s0] REFUSING: no controls artifact at %s. Run --controls-only "
                         "first — a gating control must be computed AND READ in its own pass."
                         % CONTROLS_JSON)
    ctl = json.load(open(CONTROLS_JSON))
    if not ctl.get("all_gating_pass"):
        raise SystemExit("[p1s0] REFUSING: gating controls did not pass: %s" % ctl.get("gates"))
    print("[p1s0] controls artifact read, all gating controls pass: %s" % ctl["gates"], flush=True)

    panel, part = load()
    out = {"prereg": "PREREG_p1s0_optionable_gate.md",
           "controls_artifact": os.path.basename(CONTROLS_JSON),
           "controls_gates": ctl["gates"], "primary_mode": PRIMARY_MODE, "modes": {}}

    for mode in MODES:
        r = restrict(panel, part, mode)
        print("[p1s0] mode=%s rows=%d names=%d" % (mode, len(r), r["ticker"].nunique()), flush=True)
        node = {"n_rows": int(len(r)), "n_names": int(r["ticker"].nunique()), "arms": {}}
        for h in HORIZONS:
            node["arms"][str(h)] = score(r, h, "%s_h%d" % (mode, h))
        print("[p1s0] mode=%s placebo (%d draws x %d horizons x 3 windows)"
              % (mode, PLACEBO_DRAWS, len(HORIZONS)), flush=True)
        node["placebo"] = placebo_floors(r)
        # C9's reference: the effect this project has ALREADY measured, on the FULL panel over
        # the SAME dates. Not an arm and it carries no verdict — it is the known-real quantity
        # the power question is asked about, the MA31 C-POWER pattern.
        ref = {}
        for h in HORIZONS:
            ds = scorable_dates(r, h)
            ref[str(h)] = {"n_dates": len(ds),
                           "full": {"cum_alpha": (_ref_cum(panel, h, ds) if ds else None)}}
        node["reference_full_panel_same_dates"] = ref
        node["verdicts"] = {
            str(h): verdict(node["arms"][str(h)], node["placebo"], h,
                            reference_cum_alpha=ref[str(h)]["full"]["cum_alpha"])
            for h in HORIZONS}
        out["modes"][mode] = node

    prim = out["modes"][PRIMARY_MODE]["verdicts"]
    anchor = prim[str(POWER_ANCHOR)]["state"]
    gate = [prim[str(h)]["state"] for h in GATE_HORIZONS]
    if anchor == "FAIL":
        fam = "CLOSED"
    elif anchor == "PASS" and all(s == "PASS" for s in gate):
        fam = "OPEN"
    elif anchor == "PASS":
        fam = "PARTIAL"
    else:
        fam = "UNRESOLVED"
    out["family_verdict"] = {
        "state": fam, "power_anchor_h63": anchor,
        "gate_horizons": dict(zip((str(h) for h in GATE_HORIZONS), gate)),
        "rule": "prereg 4 — FAIL at the power anchor CLOSES the family; PASS at the anchor "
                "with a failing/underpowered long horizon is PARTIAL (the S10 precedent); an "
                "UNDERPOWERED anchor resolves nothing.",
    }
    # The sensitivity may never rescue the primary (prereg 4).
    sens = out["modes"]["has_chain"]["verdicts"]
    out["sensitivity_discrepancy"] = {
        str(h): {"primary": prim[str(h)]["state"], "sensitivity": sens[str(h)]["state"],
                 "agree": prim[str(h)]["state"] == sens[str(h)]["state"]}
        for h in HORIZONS}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-only", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, _repo())
    if a.controls_only:
        r = controls()
        with open(CONTROLS_JSON, "w") as fh:
            json.dump(r, fh, indent=2, default=str)
        print(json.dumps({k: v for k, v in r.items() if k != "reported"}, indent=2, default=str))
        print("\n[p1s0] wrote %s" % CONTROLS_JSON)
        print("[p1s0] ALL GATING CONTROLS PASS: %s" % r["all_gating_pass"])
        return 0 if r["all_gating_pass"] else 2
    if a.arms:
        r = arms()
        with open(ARMS_JSON, "w") as fh:
            json.dump(r, fh, indent=2, default=str)
        print("\n[p1s0] wrote %s" % ARMS_JSON)
        print(json.dumps(r["family_verdict"], indent=2))
        return 0
    ap.error("pass --controls-only or --arms")


if __name__ == "__main__":
    raise SystemExit(main())
