# -*- coding: utf-8 -*-
"""`STAGE1-BATCH3` — the free pre-outcome kills, in their OWN pass.

    python -m scripts.b3_kills --panel <v3.pkl> --out <B3_KILLS.json>

**THE BUILD QUADRANT ONLY, AND THE RESTRICTION HAPPENS BEFORE ANY SIGNAL IS BUILT.** My first
version of this file read the WHOLE panel and would have computed every costume correlation and
every coverage figure across the CHECK quadrant as well — a Stage-2 look, and void condition 5 of
this batch's own register. It was killed before it computed anything. **`build_quadrant` is CALLED
from `scripts.stage1_kills`**, the same function batches 1 and 2 used, so there is one definition
of which rows are in scope rather than a second one written here.

**AND `costume_rho`, `verdict` AND `BUILD_HALF_SPLIT` ARE CALLED FOR THE SAME REASON** (`B7`). My
first version carried its own `mean_abs_rho` and its own Spearman — a second definition of the
costume bar's own statistic, which is how two numbers for one question come about. Each arm's
signal is attached to the quadrant frame as a column so the shared function can score it.

**NO FORWARD RETURN IS READ ANYWHERE IN THIS PASS — and that claim has been wrong once already,
so it is worth saying how it became true.** An earlier version of `C4` compounded the panel's
`fwd_ret` over the trailing window to get its return leg, which made the blanket claim false; the
docstring and the artifact both asserted it anyway. `C4` now takes BOTH of its five-year legs from
the provider — market cap from the DAILY cache, total return from `price_history` — so no arm in
this pass touches a forward-return column at all.

**THE REASON THAT REPAIR WAS NEEDED IS A SEPARATE FINDING AND IT IS RECORDED IN
`c4_composite_issuance`:** sourcing from the panel truncated the window at the panel's own grid
start (2009-03-27), which fired C4's coverage kill at 0.6094 against an untruncated 0.9239. **The
0.70 floor did not move** and the panel-sourced figure stays on the record beside it.

**THE RULE THE EPISODE LEAVES: a blanket claim that is false is worse than a narrow one that is
true**, because the blanket version is the one a reader relies on. The property this pass actually
needs is `O10`'s — no arm is related to an outcome at the date it is scored for — and its process
defect was computing a gating control in the same pass as the outcomes it gates, which makes
"the control was read first" unprovable.

**EVERY BAR IS THE REGISTER'S OWN AND IS A MODULE LITERAL.** These are kill bars, not calibrated
floors — `CORRECTED_FLOORS.json` is read by the ARM pass, for the statistics it was calibrated on,
and `MB22`/`U2`'s rule forbids putting a theme-IC floor beside an incremental IC. A bar read out of
the data it judges is not a bar (`W-28`).

**COVERAGE IS MEASURED ON THE TIER, WHICH GOVERNS** (charter §5 Stage 1b) — and within the build
quadrant, on the arm's own rows, because `O-1` applied an alert-book figure to the panel and was
~17x wrong.
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

from scripts.stage1_kills import (build_quadrant, costume_rho,              # noqa: E402
                                  verdict, BUILD_HALF_SPLIT)

# ---------------------------------------------------------------------------------- THE BARS
COSTUME_BAR = 0.60              # mean per-date |rho| against any one theme
C4_IDENTITY_BAR = 0.95          # LOOSER on purpose: C4 and neg_issuance measure the same
#:                                economics, so the question is whether they are the same COLUMN
COVERAGE_FLOOR = 0.70           # the project's inherited coverage rule
C3_NONZERO_FLOOR = 0.30         # a DISPERSION floor, not a coverage floor -- a firm with no R&D
#:                                is a valid observation at zero, so 0.70 would be the wrong object
C6_MAX_SECTOR_SHARE = 0.40      # or the arm is a sector bet (S7's C6, S10's 3x spread)
TIER_FLOOR_USD = 10e9           # charter §5 Stage 1b: the $10B tier governs

THEMES = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
          "institutional")

#: the shipped columns each arm must be told apart from, by arm. Every one is checked for
#: PRESENCE and reported absent rather than silently skipped.
AGAINST = {
    "C1": ("quality", "z_accruals_q"),
    "C2": ("z_f_score",),
    "C3": ("z_op_margin",),
    "C4": ("z_neg_issuance",),
    "C5": ("z_accruals_q", "z_roe"),
    "C6": ("z_accruals_q",),
    "C7": ("z_gp_on_capital", "z_op_margin"),
    "C8": ("z_neg_asset_growth",),
}


_PROV = None


def _prov():
    """The provider C4 sources its two five-year legs from, built once.

    `_bulk_dir` is pinned to the cache the PANEL's own `market_cap` was built from, rather than
    left to the default derivation from the export's parent -- an absent cache DEGRADES TO EMPTY
    rather than failing (the provider's own comment), so a wrong derivation would silently cost
    the market-cap series and read as a coverage hole rather than as an error.

    (This docstring had to be repaired: the backticks in it were eaten by bash command
    substitution when the edit was first applied through a shell heredoc -- a hazard this lane
    has already recorded, and hit again.)
    """
    global _PROV
    if _PROV is None:
        from valuation.edge.data_providers import WRDSProvider

        class _C:
            wrds_data_dir = r"C:/Users/donni/Downloads/valuation-tool/data/full2009/backtest"

        p = WRDSProvider(_C())
        p._bulk_dir = r"C:/Users/donni/Downloads/valuation-tool/data/bulk/prepared"
        ok, msg = p.ready()
        if not ok:
            raise SystemExit("provider not ready: %s" % msg)
        _PROV = p
    return _PROV


def attach(frame, sig, col):
    """Attach a `{date: {ticker: value}}` signal to the frame as `col`. Returns the frame."""
    dd = frame["date"].astype(str).str[:10]
    frame[col] = [
        (sig.get(d) or {}).get(t)
        for d, t in zip(dd, frame["ticker"].astype(str))
    ]
    return frame


def tier_coverage(frame, col):
    """Share of TIER rows the arm can score, inside the build quadrant. The tier GOVERNS."""
    mc = pd.to_numeric(frame["market_cap"], errors="coerce")
    tier = frame[mc >= TIER_FLOOR_USD]
    if not len(tier):
        return {"count_gate_passes": False, "cell_coverage": None,
                "why": "no tier rows in the build quadrant"}
    v = pd.to_numeric(tier[col], errors="coerce")
    per = []
    for _, g in tier.groupby("date"):
        gv = pd.to_numeric(g[col], errors="coerce")
        if len(g):
            per.append(float(gv.notna().mean()))
    return {"tier_rows": int(len(tier)), "tier_rows_scored": int(v.notna().sum()),
            "cell_coverage": float(v.notna().mean()),
            "per_date_min": (float(np.min(per)) if per else None),
            "per_date_median": (float(np.median(per)) if per else None),
            "n_dates": len(per),
            # MB21: a coverage of 1.0 over zero rows is not coverage.
            "count_gate_passes": True}


def costume_block(frame, col, arm):
    """Every theme at `COSTUME_BAR`, plus the arm's own named comparisons. ABSENT columns are
    REPORTED rather than skipped -- a comparison that did not run must not read as one that
    passed."""
    themes, worst = [], None
    for th in THEMES:
        if th not in frame.columns:
            themes.append({"column": th, "absent": True})
            continue
        r = costume_rho(frame, col, th)
        rec = {"column": th, "absent": False,
               "mean_abs_rho": (r or {}).get("mean_abs_rho"),
               "max_abs_rho": (r or {}).get("max_abs_rho"),
               "dates": (r or {}).get("dates")}
        themes.append(rec)
        if rec["mean_abs_rho"] is not None and (
                worst is None or rec["mean_abs_rho"] > worst["mean_abs_rho"]):
            worst = rec
    named = []
    for c in AGAINST.get(arm, ()):
        if c not in frame.columns:
            named.append({"column": c, "absent": True})
            continue
        r = costume_rho(frame, col, c)
        named.append({"column": c, "absent": False,
                      "mean_abs_rho": (r or {}).get("mean_abs_rho"),
                      "max_abs_rho": (r or {}).get("max_abs_rho"),
                      "dates": (r or {}).get("dates")})
    return {"themes": themes, "worst_theme": worst, "named": named}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--export", default=None)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    from scripts.tiered_pool_run import _hist
    from scripts import b3_signals as S1
    from scripts import b3_signals2 as S2

    panel = pd.read_pickle(args.panel)
    # ---- THE RESTRICTION HAPPENS HERE, BEFORE ANY SIGNAL IS BUILT ----
    quad, qcen = build_quadrant(panel)
    quad = quad.copy()
    print("[kills] build quadrant: %d rows, %d dates, %d names (%s..%s), halves %d/%d at %s"
          % (qcen["rows"], qcen["dates"], qcen["names"], qcen["first"], qcen["last"],
             qcen["halves"]["early_dates"], qcen["halves"]["late_dates"], BUILD_HALF_SPLIT),
          flush=True)

    export = args.export or os.path.join(
        r"C:/Users/donni/Downloads/valuation-tool/data", "full2009", "backtest")
    hist = _hist(export)

    res = {"item": "STAGE1-BATCH3", "part": "the free pre-outcome kills, in their own pass",
           "trials": 0,
           "trial_class": "CONTROL -- a kill can only BLOCK an arm, never produce a finding, so "
                          "it charges nothing (MB1-SEL).",
           "scope": "THE BUILD QUADRANT ONLY, restricted by scripts.stage1_kills.build_quadrant "
                    "BEFORE any signal is built. No check-quadrant row is read.",
           "build_quadrant": qcen,
           # NO ARM IN THIS PASS READS A FORWARD-RETURN COLUMN. C4 used to -- it compounded the
           # panel's `fwd_ret` for its trailing return leg -- and both legs now come from the
           # provider instead, for the frame-truncation reason recorded in
           # `c4_composite_issuance`. The weaker claim that preceded this one is kept in the
           # docstring rather than deleted, because the episode is the useful part.
           "no_forward_return_column_is_read_in_this_pass": True,
           "arms_that_ever_read_fwd_ret": [],
           "c4_leg_sources": {"market_cap": "WRDSProvider.daily_history (DAILY bulk cache)",
                              "total_return": "WRDSProvider.price_history(days=None), whose "
                                              "close IS closeadj",
                              "why": "the panel's grid starts 2009-03-27, so a panel-sourced "
                                     "five-year window is truncated for the 24 early-half dates; "
                                     "both sources reach 1997-1998 and are what the panel's own "
                                     "columns are built from"},
           "shared_definitions_called_not_reimplemented": ["build_quadrant", "costume_rho",
                                                           "verdict", "BUILD_HALF_SPLIT"],
           "bars": {"costume": COSTUME_BAR, "c4_identity": C4_IDENTITY_BAR,
                    "coverage": COVERAGE_FLOOR, "c3_nonzero": C3_NONZERO_FLOOR,
                    "c6_max_sector_share": C6_MAX_SECTOR_SHARE,
                    "tier_floor_usd": TIER_FLOOR_USD},
           "panel": os.path.basename(args.panel), "export": export,
           "arms": {}}

    zero_sink, cov5, cov4, legs = {}, {}, {}, {}
    builders = [
        ("C3", lambda: S1.c3_rnd_to_market(quad, hist, zero_sink=zero_sink)),
        ("C4", lambda: S2.c4_composite_issuance(quad, _prov(), cov_sink=cov4)),
        ("C1", lambda: S2.c1_abarbanell_bushee(quad, hist, leg_sink=legs)),
        ("C2", lambda: S2.c2_g_score(quad, hist)),
        ("C5", lambda: S1.c5_earnings_stability(quad, hist, cov_sink=cov5)),
        ("C7", lambda: S1.c7_operating_leverage(quad, hist)),
        ("C6", lambda: S1.c6_cash_conversion_cycle(quad, hist)),
    ]

    for arm, build in builders:
        print("[kills] building %s ..." % arm, flush=True)
        sig = build()
        if arm == "C5":
            # C5's signal is an (ar1, -sd) pair; the arm is their equally-weighted standardised
            # mean. Standardising HERE rather than in the signal module keeps both legs z-scored
            # within the SAME date and the SAME population -- otherwise the two legs would be
            # averaged over different name sets, which is MB8's rule in miniature.
            flat = {}
            for dd, per in sig.items():
                a = np.array([v[0] for v in per.values()], dtype=float)
                b = np.array([v[1] for v in per.values()], dtype=float)
                if a.std() == 0 or b.std() == 0:
                    continue
                za, zb = (a - a.mean()) / a.std(), (b - b.mean()) / b.std()
                flat[dd] = {t: float((za[i] + zb[i]) / 2.0) for i, t in enumerate(per.keys())}
            sig = flat

        col = "b3_%s" % arm.lower()
        attach(quad, sig, col)
        cov = tier_coverage(quad, col)
        cst = costume_block(quad, col, arm)
        block = {"n_dates_scored": len(sig), "coverage": cov, "costume": cst}

        fails = []
        if not cov.get("count_gate_passes") or cov.get("cell_coverage") is None:
            fails.append("coverage not measurable")
        elif arm != "C3" and cov["cell_coverage"] < COVERAGE_FLOOR:
            fails.append("tier coverage %.4f < %.2f" % (cov["cell_coverage"], COVERAGE_FLOOR))
        w = cst["worst_theme"]
        if w and w["mean_abs_rho"] is not None and w["mean_abs_rho"] >= COSTUME_BAR:
            fails.append("costume vs %s at %.4f" % (w["column"], w["mean_abs_rho"]))
        for n in cst["named"]:
            if n.get("absent"):
                fails.append("the named comparison column %s is ABSENT from the panel" % n["column"])
                continue
            if n["mean_abs_rho"] is None:
                continue
            bar = C4_IDENTITY_BAR if arm == "C4" else COSTUME_BAR
            if n["mean_abs_rho"] >= bar:
                fails.append("vs %s at %.4f >= %.2f" % (n["column"], n["mean_abs_rho"], bar))
        if arm == "C3":
            tot = zero_sink.get("scored_nonzero", 0) + zero_sink.get("scored_zero", 0)
            nz = (zero_sink["scored_nonzero"] / float(tot)) if tot else None
            block["nonzero_share"] = nz
            block["rnd_states"] = dict(zero_sink)
            if nz is None or nz < C3_NONZERO_FLOOR:
                fails.append("non-zero share %r < %.2f" % (nz, C3_NONZERO_FLOOR))

        block["fails"] = fails
        block["kill_passes"] = (len(fails) == 0)
        res["arms"][arm] = verdict(arm, block["kill_passes"], block)
        print("[kills] %s -> %s %s" % (arm, "PASS" if not fails else "FIRES", fails), flush=True)

    res["capex_states"] = dict(S1.CAPEX_STATES)
    res["c1_leg_presence"] = dict(legs)
    res["c5_history"] = dict(cov5)
    res["c4_coverage"] = dict(cov4)
    res["C8_and_C9"] = ("C8 needs its own pass (the expanding-window fit is expensive and its "
                        "strictness is a separate kill). C9 is NOT RUN -- register §0.1.")
    res["all_kills_pass"] = all(v["kill_passes"] for v in res["arms"].values())

    io.open(args.out, "w", encoding="utf-8").write(json.dumps(res, indent=1, default=str))
    print("\n-> %s   all_kills_pass=%s" % (args.out, res["all_kills_pass"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
