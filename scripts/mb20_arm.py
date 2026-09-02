# -*- coding: utf-8 -*-
"""PKG-MB20 — the kills and the arm, on the panel built ONCE with BOTH insider columns.

TWO PASSES, AND THE ORDER IS ENFORCED RATHER THAN PROMISED. `--kills` writes the artifact;
`--arms` REFUSES to run without one that passes. `O10`'s process defect was computing a gating
control and its outcomes in a single pass, so it could not be claimed the control was read first.

EVERY CONSTANT BELOW IS FROM `PREREG_mb20_insider_routine.md`. Changing one after a measurement
voids the item.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

_ROOT = r"C:\Users\donni\Downloads\valuation-tool"
FA = os.path.join(_ROOT, "data", "free_analysis")
CACHE = os.path.join(FA, "panel_mb20_pair.pkl")
KILLS = os.path.join(FA, "MB20_KILLS.json")
ARM = os.path.join(FA, "MB20_ARM.json")

#: `SECTOR-NEUTRAL-B6`'s OWN two weightings, IMPORTED rather than retyped. `W-1`'s `K4` fired
#: against a correct panel because it scored the NINE bucket themes at 0.125 when the deployed
#: composite is SEVEN -- `MA28`'s C1 defect. Importing is the only repair that cannot rot.
from scripts.sector_neutral_rerun import DEPLOYED, FLAT, BASE_WEIGHT   # noqa: E402

#: The register's bars.
K1_COVERAGE_BAR = 0.95
K2_BITE_BAR = 0.05
K3_COSTUME_BAR = 0.60          # R6's own bar, reused verbatim
MARGIN_T = 0.25                # B6 / S3 / W-1, reused verbatim
MARGIN_ALPHA_BPS = 100.0
EMBARGO_BOUNDARY = "2017-07-20"

PUBLISHED = {"top_decile_alpha": 0.071741423321,
             "long_short_tstat": 2.8360640685320595,
             "long_short_tstat_nw": 2.6199121240414884,
             "monotonicity": -0.890909}
TOL = {"top_decile_alpha": 1e-9, "long_short_tstat": 1e-9,
       "long_short_tstat_nw": 1e-9, "monotonicity": 1e-5}

#: `factors.py:344` -- the `insider` theme is NOT z-scored, it is this fixed affine map of the
#: raw score. That is why the variant theme is EXACT here where `S3`'s `C3` could only bound
#: itself: there is no cross-sectional standardisation to reproduce.
INSIDER_NEUTRAL, INSIDER_SCALE = 50.0, 25.0


def _theme_from_score(s):
    return (pd.to_numeric(s, errors="coerce") - INSIDER_NEUTRAL) / INSIDER_SCALE


def _filter_factory():
    """The duck-typed filter handed to the builder. Counts what it does, so the bite is
    measured by the same object that applies it rather than by a second implementation."""
    from valuation.studies import insider_routine as IR
    seen = {"rows": 0, "kept": 0, "routine": 0, "unclassifiable": 0, "lookahead": 0}

    def keep(rows):
        if not rows:
            return rows
        df = pd.DataFrame(rows)
        for c in ("ticker", "ownername", "transactiondate"):
            if c not in df.columns:
                df[c] = None
        lab = IR.classify(df)
        seen["rows"] += len(df)
        seen["routine"] += int((lab == IR.ROUTINE).sum())
        seen["unclassifiable"] += int((lab == IR.UNCLASSIFIABLE).sum())
        # K5 -- a label may never rest on a year at or after the trade's own. The classifier is
        # point-in-time BY CONSTRUCTION (it tests y-1 and y-2 only), so this must read zero; it
        # is a structural check that the construction is the one shipped, not a filter.
        seen["lookahead"] += _lookahead_violations(df, lab, IR)
        mask = IR.opportunistic_mask(lab)
        seen["kept"] += int(mask.sum())
        return [r for r, k in zip(rows, mask) if k]

    keep.seen = seen
    return keep


def _lookahead_violations(df, lab, IR):
    """A ROUTINE label must be reproducible from years strictly BEFORE the trade's own."""
    td = pd.to_datetime(df["transactiondate"], errors="coerce")
    ok = df["ticker"].notna() & df["ownername"].notna() & td.notna()
    if not ok.any():
        return 0
    y, m = td.dt.year, td.dt.month
    seen = set(zip(df.loc[ok, "ticker"].astype(str), df.loc[ok, "ownername"].astype(str),
                   m[ok].astype(int), y[ok].astype(int)))
    bad = 0
    for i in df.index[ok & (lab == IR.ROUTINE)]:
        t, o = str(df.at[i, "ticker"]), str(df.at[i, "ownername"])
        yy, mm = int(y[i]), int(m[i])
        if not all((t, o, mm, yy - b) in seen for b in (1, 2)):
            bad += 1
    return bad


def build():
    """ONE build, BOTH insider columns. Cached, because it is ~20 minutes."""
    if os.path.exists(CACHE):
        print("  [cache] %s" % CACHE)
        return pd.read_pickle(CACHE), None
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel

    # The provider is pointed at the PRIMARY root. A worktree carries `data/` empty and
    # `CONFIG.wrds_data_dir` resolves to "", so a bare `WRDSProvider()` here indexes ZERO
    # tickers and returns an empty insider history for every name -- silently, since an empty
    # history is a legitimate state. That is `E-5`'s wrong-object family and it would have
    # produced a clean, plausible panel in which the insider theme was absent everywhere.
    # Caught by a smoke test on AAPL returning 0 rows against 3,712 in the export.
    class _C:
        wrds_data_dir = os.path.join(_ROOT, "data", "backtest")

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready: %s" % msg)
    names = prov.universe(limit=CONFIG.backtest_universe_limit)
    keep = _filter_factory()
    t0 = time.time()
    print("  %d names; ONE build, both insider columns" % len(names), flush=True)
    panel = build_fundamental_panel(
        prov, names, rebalance_days=CONFIG.backtest_rebalance_days, horizon=63,
        lookback_years=CONFIG.backtest_lookback_years,
        with_insider_raw=True, insider_filter=keep)
    print("  built %d rows x %d dates in %.1f min"
          % (len(panel), panel["date"].nunique(), (time.time() - t0) / 60.0))
    panel.to_pickle(CACHE)
    with open(os.path.join(FA, "MB20_FILTER_SEEN.json"), "w") as fh:
        json.dump(keep.seen, fh, indent=1)
    return panel, keep.seen


def split_arms(panel):
    """`A_BASE` and `A_OPP`: identical frames differing in the `insider` column alone."""
    base = panel.copy()
    opp = panel.copy()
    opp["insider"] = _theme_from_score(panel["insider_score_opp"])
    return base, opp


def _coverage_census():
    """K1's SUBJECT: classifiability on THE ROWS THE SHIPPED SCORE CAN VALUE.

    THIS FUNCTION EXISTS BECAUSE MY FIRST INSTRUMENT MEASURED THE WRONG POPULATION AND K1 FIRED
    AGAINST A CORRECT PANEL. The filter's own counter tallied every row handed to it -- the whole
    per-ticker history -- and returned 0.7263, which is the EXPORT-level figure. The register's
    K1 is declared on "the arm's own scored rows", and §2b measured that at 1.0000 precisely
    because the rows that cannot be classified are EXACTLY the rows `_prep_insider` already
    discards for carrying neither price nor value.

    So this is a repair to the INSTRUMENT and NOT a relaxation of the bar. The bar stays 0.95,
    which it was set to before any of this was measured. It is `O-1`'s lesson -- a coverage
    figure carried across populations, ~17x wrong -- landing inside the register that corrects
    it, and `W-1`'s `K4` shape a second time: a kill firing against a correct panel because of
    the author's own instrument.

    Both denominators are reported. Nothing is hidden by fixing the one that governs.
    """
    from valuation.config import CONFIG
    from valuation.edge.data_providers import WRDSProvider
    from valuation.edge.fundamental_panel import _f
    from valuation.studies import insider_routine as IR

    class _C:
        wrds_data_dir = os.path.join(_ROOT, "data", "backtest")

    prov = WRDSProvider(_C())
    idx = prov._indexed("insiders")
    n_all = n_scoreable = 0
    unc_all = unc_scoreable = routine_scoreable = 0
    for _tk, rows in idx.items():
        if not rows:
            continue
        df = pd.DataFrame(rows)
        for c in ("ticker", "ownername", "transactiondate"):
            if c not in df.columns:
                df[c] = None
        lab = IR.classify(df).to_numpy()
        # `_prep_insider`'s OWN test, so the denominator is the score's population and not a
        # lookalike: a row counts when it carries a filing date AND a value the score can form.
        sh = pd.to_numeric(df.get("transactionshares"), errors="coerce")
        pr = pd.to_numeric(df.get("transactionpricepershare"), errors="coerce")
        va = pd.to_numeric(df.get("transactionvalue"), errors="coerce")
        val = (sh * pr).where(sh.notna() & pr.notna(), va)
        fd = pd.to_datetime(df.get("filingdate"), errors="coerce")
        sc = (val.notna() & fd.notna()).to_numpy()
        n_all += len(df)
        unc_all += int((lab == IR.UNCLASSIFIABLE).sum())
        n_scoreable += int(sc.sum())
        unc_scoreable += int(((lab == IR.UNCLASSIFIABLE) & sc).sum())
        routine_scoreable += int(((lab == IR.ROUTINE) & sc).sum())
    return {
        "rows_all": n_all,
        "unclassifiable_all": unc_all,
        "frac_classifiable_all_rows": (1.0 - unc_all / n_all) if n_all else None,
        "rows_the_score_can_value": n_scoreable,
        "unclassifiable_among_them": unc_scoreable,
        "frac_classifiable_on_scored_population": (
            (1.0 - unc_scoreable / n_scoreable) if n_scoreable else None),
        "routine_share_of_scoreable": (
            (routine_scoreable / n_scoreable) if n_scoreable else None),
    }


def kills(panel, seen):
    from valuation.edge import research_log as RL
    from valuation.edge.fundamental_panel import quantile_backtest
    out = {"item": "PKG-MB20", "trials": 1,
           "equity_N": RL.detail()["by_domain"]["equity"], "filter_seen": seen}

    if seen is None:
        seen = json.load(open(os.path.join(FA, "MB20_FILTER_SEEN.json")))
        out["filter_seen"] = seen
    cen = _coverage_census()
    cov = cen["frac_classifiable_on_scored_population"]
    out["K1_coverage"] = dict(cen, bar=K1_COVERAGE_BAR, frac=cov,
                              fires=(cov is None or cov < K1_COVERAGE_BAR),
                              note=("Measured on THE ROWS THE SHIPPED SCORE CAN VALUE, which is "
                                    "the population the register declares. The all-rows figure "
                                    "is reported beside it and is the EXPORT's, not the arm's."))

    a = pd.to_numeric(panel["insider_score"], errors="coerce")
    b = pd.to_numeric(panel["insider_score_opp"], errors="coerce")
    both = a.notna() & b.notna()
    moved = int((both & (a != b)).sum())
    scored = int(a.notna().sum())
    out["K2_bite"] = {"bar": K2_BITE_BAR, "cells_scored": scored, "cells_moved": moved,
                      "frac": (moved / scored) if scored else None,
                      "fires": (not scored) or (moved / scored) < K2_BITE_BAR}

    d = panel.assign(_moved=(both & (a != b)).astype(float))
    rs = []
    for _dt, g in d.groupby(d["date"].astype(str).str[:10]):
        gg = g[g["size"].notna() & g["_moved"].notna()]
        if len(gg) >= 20 and gg["_moved"].nunique() > 1:
            r = gg[["size", "_moved"]].corr(method="spearman").iloc[0, 1]
            if pd.notna(r):
                rs.append(abs(float(r)))
    out["K3_size_costume"] = {"bar": K3_COSTUME_BAR, "dates": len(rs),
                              "mean_abs_spearman": float(np.mean(rs)) if rs else None,
                              "fires": bool(rs) and float(np.mean(rs)) > K3_COSTUME_BAR}

    cols = [c for c in DEPLOYED if c in panel.columns]
    w = {c: BASE_WEIGHT for c in cols}
    r = quantile_backtest(panel, cols, w, n_q=10, horizon=63)
    meas = {k: r.get(k) for k in PUBLISHED}
    out["K4_fidelity"] = {"published": PUBLISHED, "measured": meas,
                          "fires": any(meas.get(k) is None
                                       or abs(meas[k] - v) > TOL[k]
                                       for k, v in PUBLISHED.items())}

    out["K5_lookahead"] = {"violations": seen["lookahead"],
                           "fires": seen["lookahead"] > 0}

    # C-IDENT: the incumbent theme IS the affine map of its own raw score. Non-vacuous by a
    # perturbation, and it REFUSES an empty comparison rather than scoring it perfect (MB21's
    # C1 once returned 0.000e+00 by comparing nothing).
    rec = _theme_from_score(panel["insider_score"])
    shipped = pd.to_numeric(panel["insider"], errors="coerce")
    m = rec.notna() & shipped.notna()
    dev = float((rec[m] - shipped[m]).abs().max()) if int(m.sum()) else None
    pert = rec.copy()
    if int(m.sum()):
        pert.iloc[int(np.flatnonzero(m.to_numpy())[0])] += 1e-12
    out["C_IDENT"] = {
        "rows_compared": int(m.sum()), "max_abs_dev": dev,
        "non_vacuous": bool(int(m.sum()) and
                            float((pert[m] - shipped[m]).abs().max()) > 0.0),
        "fires": (int(m.sum()) == 0) or dev is None or dev > 0.0,
    }

    out["all_kills_pass"] = not any(out[k]["fires"] for k in
                                    ("K1_coverage", "K2_bite", "K3_size_costume",
                                     "K4_fidelity", "K5_lookahead", "C_IDENT"))
    with open(KILLS, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps(out, indent=1, default=str))
    return out


def arm(panel):
    from valuation.edge.fundamental_panel import holdout_compare_panels
    if not os.path.exists(KILLS):
        raise SystemExit("REFUSING: no kills artifact. Run --kills first and READ it (O10).")
    k = json.load(open(KILLS))
    if not k.get("all_kills_pass"):
        raise SystemExit("REFUSING: a kill fired; the register stops and the arm does not run.")

    base, opp = split_arms(panel)
    out = {"item": "PKG-MB20", "kills_read_from": KILLS, "weightings": {}}
    for label, cset in (("deployed", DEPLOYED), ("flat", FLAT)):
        cols = [c for c in cset if c in base.columns]
        # The SHIPPED gate, and its own defaults ARE the registered margins -- min_alpha_gain
        # 0.01 (=100bps) and min_tstat_gain 0.25 -- so they are passed EXPLICITLY rather than
        # inherited, because a default that silently changed would change the verdict.
        res = holdout_compare_panels(base, opp, cols,
                                     label_a="A_BASE", label_b="A_OPP",
                                     horizon=63, base_weight=BASE_WEIGHT,
                                     min_alpha_gain=MARGIN_ALPHA_BPS / 10000.0,
                                     min_tstat_gain=MARGIN_T)
        out["weightings"][label] = res
        print("\n=== %s ===" % label.upper())
        print(json.dumps(res, indent=1, default=str)[:1800])
    out["margins"] = {"delta_t": MARGIN_T, "delta_alpha_bps": MARGIN_ALPHA_BPS}
    with open(ARM, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\nwrote", ARM)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args(argv)
    panel, seen = build()
    if a.kills:
        kills(panel, seen)
    if a.arms:
        arm(panel)
    if not (a.kills or a.arms):
        print("nothing to do: pass --kills, then READ it, then --arms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
