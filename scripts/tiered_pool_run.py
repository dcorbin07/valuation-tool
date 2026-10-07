# -*- coding: utf-8 -*-
"""`TIERED-POOL` runner — both arms, both periods, the coverage kill read FIRST.

Register `PREREG_tiered_pool.md`; two equity trials booked at `7ebf7aa` before any runner existed.

**THE COVERAGE KILL (§2c) IS COMPUTED AND READ IN ITS OWN PASS, BEFORE ANY ARM-B RETURN EXISTS.**
`O10`'s process defect was computing a gating control and the outcomes in one pass, so there was
no way to claim the control had been read first. Here `--kill` writes its own artifact and
`--arms` **refuses** without a passing one.

**NO ALPHA CLAIM** — inherited from `INDEX-CHOICE` via the register. An intercept anywhere in this item is a **DECOMPOSITION**, and **no X7 floor is quoted**; every critical value is **LABELLED UNCALIBRATED** (`V2G`, `R1-VAR`).

**`pool_size._roth` IS REUSED, NOT RE-IMPLEMENTED (`B7`).** It passes `**kw` to BOTH the
after-tax path and `IB.run`, and both accept `index_fn` and `universe_filter` — so the two paths
see the same hooks and cannot describe different books. It also takes each metric from the source
`INDEX-BEST` banked it from, which is a fact about that item rather than a choice made here.
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.tiered_pool as TP                                              # noqa: E402
from scripts.pool_size import _roth                                           # noqa: E402
from scripts.index_best import _data_root, data_candidates, _ann              # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT                # noqa: E402
from scripts.pool_size_oos import THEMES_PRE2009                              # noqa: E402

#: the incumbent, identical to `INDEX-BEST`'s `1_incumbent_10bn` and `UNIVERSE-BIAS`'s arm 1.
INCUMBENT_KW = {"large_cap_min": 1e10, "universe_rank": None, "top_n": None}

PERIODS = [
    # (label, panel artifact, export for fundamentals_history, theme set, note)
    ("2009_2026", "UNIVERSE_BIAS_PANEL_full.pkl", ("full2009", "backtest"), None,
     "CORRECTED full raw universe, 2026-10 vintage, all seven themes"),
    ("1999_2008", "POOL_SIZE_OOS_PANEL.pkl", ("oos1999", "backtest"), THEMES_PRE2009,
     "LABELLED FIVE-THEME PROXY for the tiering, never a test of the shipped composite; "
     "levels NOT comparable to 2009-2026 (PREREG_tiered_pool.md section 4)"),
]


def _fa():
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    return data, os.path.join(data, "free_analysis")


def _hist(export):
    """`fundamentals_history` per ticker, pre-sorted exactly as the panel builder sorts it."""
    from valuation.edge.data_providers import WRDSProvider

    class _C:
        wrds_data_dir = export

    prov = WRDSProvider(_C())
    ok, msg = prov.ready()
    if not ok:
        raise SystemExit("provider not ready on %s: %s" % (export, msg))
    out = {}
    for t in prov.universe(limit=None) or []:
        out[t] = sorted(prov.fundamentals_history(t) or [],
                        key=lambda r: (r.get("datekey") or r.get("date") or ""))
    return out


def kill_pass(argv=None) -> int:
    """§2c — read in its OWN pass, before any arm-B return exists."""
    data, fa = _fa()
    res = {"item": "TIERED-POOL", "part": "2c coverage kill", "trials": 0,
           "floor": TP.JUNK_COVERAGE_FLOOR,
           "floor_source": "INHERITED -- the panel's own theme_coverage rule, quoted at 0.70 in "
                           "PANEL-EXT-CENSUS. NOT chosen here.",
           "rule": "the three junk conditions must be jointly evaluable on at least 70% of the "
                   "sub-$10B rows arm A selects from, or arm B does NOT run and is reported "
                   "NOT-RUN with no figure quoted",
           "periods": {}}
    allok = True
    for label, pkl, exp, themes, _note in PERIODS:
        panel = pd.read_pickle(os.path.join(fa, pkl))
        hist = _hist(os.path.join(data, *exp))
        mc = pd.to_numeric(panel["market_cap"], errors="coerce")
        sub = panel[(mc >= TP.MICRO_CAP) & (mc < 1e10)]
        per_date, ev, rows = {}, 0, 0
        for d in sorted(sub["date"].unique()):
            g = sub[sub["date"] == d]
            as_of = str(d)[:10]
            ok, st = TP.junk_ok(list(g["ticker"]), hist, as_of)
            per_date[as_of] = st
            ev += st["evaluable"]
            rows += st["rows"]
        share = ev / max(1, rows)
        ok_period = share >= TP.JUNK_COVERAGE_FLOOR
        allok = allok and ok_period
        res["periods"][label] = {"sub_10bn_rows": rows, "evaluable": ev,
                                 "evaluable_share": share, "passes": bool(ok_period),
                                 "per_date": per_date}
        print("%-10s sub-$10B rows %7d | jointly evaluable %7d = %.4f | %s"
              % (label, rows, ev, share, "PASS" if ok_period else "KILL FIRES"), flush=True)
    res["all_pass"] = bool(allok)
    json.dump(res, io.open(os.path.join(fa, "TIERED_POOL_KILL.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\nall_pass = %s -> arm B %s" % (allok, "RUNS" if allok else "DOES NOT RUN"))
    return 0


def _score(panel, cols, weights, kw, label):
    r = _roth(panel, cols, weights, kw)
    if r is None:
        print("    %-16s no result" % label, flush=True)
        return None
    ns = r["net_series"]
    grid = sorted(panel["date"].unique())
    mid = len(grid) // 2
    early, late = set(grid[:mid]), set(grid[mid + 1:])
    e = [ns[i] for i, d in enumerate(grid[:len(ns)]) if d in early]
    l = [ns[i] for i, d in enumerate(grid[:len(ns)]) if d in late]
    r["early_roth_ann"] = _ann(e) if e else None
    r["late_roth_ann"] = _ann(l) if l else None
    r["roth_max_drawdown"] = TP._mdd(ns)
    r["roth_sharpe"] = TP._sharpe(ns)
    r.pop("gross_series", None)
    print("    %-16s roth %.4f  dd %.4f  early %.4f  late %.4f  turn %s  cost %s"
          % (label, r["roth_net_ann"], r["roth_max_drawdown"], r["early_roth_ann"] or 0,
             r["late_roth_ann"] or 0,
             ("%.3f" % r["annual_turnover"]) if r["annual_turnover"] else "n/a",
             ("%.1f" % r["realised_one_way_bps"]) if r["realised_one_way_bps"] else "n/a"),
          flush=True)
    return r


def _weight_below(panel, cols, weights, kw, cuts=(2e9, TP.MICRO_CAP)):
    """§5 — the share of BOOK WEIGHT below each cut, so a size bet is visible."""
    from valuation.studies import served_index_book as IB
    from valuation.edge.no_trade_band import BAND_WIDTH
    from valuation.edge.fundamental_panel import composite_from_frame
    from valuation.screener.cross_sectional import zscore
    bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    mc = {}
    for d, t, m in zip(panel["date"], panel["ticker"],
                       pd.to_numeric(panel["market_cap"], errors="coerce")):
        mc[(str(d)[:10], t)] = m
    held, acc, sizes = set(), {c: [] for c in cuts}, []
    for d in sorted(panel["date"].unique()):
        g = panel[panel["date"] == d]
        comp = composite_from_frame(g, cols, weights, zscore)
        bk = bf(g, comp, held)
        if not bk:
            continue
        held = set(bk)
        sizes.append(len(bk))
        tot = sum(bk.values()) or 1.0
        for c in cuts:
            acc[c].append(sum(w for t, w in bk.items()
                              if (mc.get((str(d)[:10], t)) or float("inf")) < c) / tot)
    return {"weight_below": {("%.0fM" % (c / 1e6)): {"mean": float(np.mean(v)),
                                                     "max": float(np.max(v))}
                             for c, v in acc.items() if v},
            "book_size": ({"min": int(min(sizes)), "median": float(np.median(sizes)),
                           "max": int(max(sizes))} if sizes else None),
            "dates": len(sizes)}


def arms_pass(argv=None) -> int:
    data, fa = _fa()
    kp = os.path.join(fa, "TIERED_POOL_KILL.json")
    if not os.path.exists(kp):
        print("REFUSING: no coverage-kill artifact at %s. Run --kill first; the register "
              "requires it read in its OWN pass before any arm-B return exists." % kp)
        return 2
    kill = json.load(io.open(kp, encoding="utf-8"))
    run_b = bool(kill.get("all_pass"))
    print("coverage kill: all_pass=%s -> arm B %s\n"
          % (run_b, "RUNS" if run_b else "DOES NOT RUN (reported NOT-RUN)"), flush=True)

    res = {"item": "TIERED-POOL", "trials": 2, "register": "PREREG_tiered_pool.md",
           "arm_b_runs": run_b,
           "arm_b_not_run_reason": (None if run_b else
                                    "the section 2c coverage kill fired; no arm-B figure is "
                                    "quoted"),
           "no_alpha_claim": "inherited from INDEX-CHOICE via the register; an intercept is a "
                             "DECOMPOSITION",
           "no_x7_floor": "no calibrated floor is quoted anywhere; every critical value is "
                          "LABELLED UNCALIBRATED (V2G, R1-VAR)",
           "periods": {}}

    for label, pkl, exp, themes, note in PERIODS:
        panel = pd.read_pickle(os.path.join(fa, pkl))
        want = list(themes or DEPLOYED)
        cols, dead = TP_live(panel, want)
        weights = {c: BASE_WEIGHT for c in cols}
        grid = sorted(panel["date"].unique())
        spy = [float(panel[panel["date"] == d]["bench_ret"].iloc[0]) for d in grid]
        mid = len(grid) // 2
        print("=== %s === %d names, %d dates, %s..%s, themes ALIVE %d%s"
              % (label, panel["ticker"].nunique(), len(grid), str(grid[0])[:10],
                 str(grid[-1])[:10], len(cols), (" DEAD %r" % dead) if dead else ""), flush=True)
        out = {"note": note, "themes": cols, "themes_dead": dead, "n_dates": len(grid),
               "n_names": int(panel["ticker"].nunique()), "spy_ann": _ann(spy),
               "half_boundary_embargoed": str(grid[mid])[:10], "arms": {}}

        out["arms"]["0_incumbent_10bn"] = _score(panel, cols, weights, dict(INCUMBENT_KW),
                                                 "0_incumbent_10bn")
        sinkA = []
        out["arms"]["A_tiered"] = _score(panel, cols, weights,
                                         {"index_fn": TP.tiered_index_fn(per_band_sink=sinkA),
                                          "large_cap_min": 0.0},
                                         "A_tiered")
        if run_b:
            hist = _hist(os.path.join(data, *exp))
            okbd = {}
            for d in grid:
                g = panel[panel["date"] == d]
                as_of = str(d)[:10]
                okbd[as_of], _st = TP.junk_ok(list(g["ticker"]), hist, as_of)
            sinkB = []
            out["arms"]["B_tiered_junk"] = _score(
                panel, cols, weights,
                {"index_fn": TP.tiered_index_fn(per_band_sink=sinkB),
                 "universe_filter": TP.junk_universe_filter(okbd),
                 "large_cap_min": 0.0},
                "B_tiered_junk")
        else:
            out["arms"]["B_tiered_junk"] = None

        # §5 — composition, for every arm that ran
        comp = {}
        for name, kw in (("0_incumbent_10bn", dict(INCUMBENT_KW)),
                         ("A_tiered", {"index_fn": TP.tiered_index_fn(), "large_cap_min": 0.0})):
            comp[name] = _weight_below(panel, cols, weights, kw)
        out["composition"] = comp
        res["periods"][label] = out

    # §1 — the rule, applied to each arm against the incumbent
    def pick(label, arm, key):
        a = ((res["periods"][label]["arms"].get(arm)) or {})
        return a.get(key)

    res["decision"] = {}
    for arm in ("A_tiered", "B_tiered_junk"):
        if not pick("2009_2026", arm, "roth_net_ann"):
            res["decision"][arm] = {"PASSES": None, "reason": "arm did not run"}
            continue
        a = {"full": pick("2009_2026", arm, "roth_net_ann"),
             "early": pick("2009_2026", arm, "early_roth_ann"),
             "late": pick("2009_2026", arm, "late_roth_ann"),
             "oos": pick("1999_2008", arm, "roth_net_ann"),
             "mdd_full": pick("2009_2026", arm, "roth_max_drawdown"),
             "mdd_oos": pick("1999_2008", arm, "roth_max_drawdown")}
        i = {"full": pick("2009_2026", "0_incumbent_10bn", "roth_net_ann"),
             "early": pick("2009_2026", "0_incumbent_10bn", "early_roth_ann"),
             "late": pick("2009_2026", "0_incumbent_10bn", "late_roth_ann"),
             "oos": pick("1999_2008", "0_incumbent_10bn", "roth_net_ann"),
             "mdd_full": pick("2009_2026", "0_incumbent_10bn", "roth_max_drawdown"),
             "mdd_oos": pick("1999_2008", "0_incumbent_10bn", "roth_max_drawdown")}
        res["decision"][arm] = TP.decide(a, i)

    json.dump(res, io.open(os.path.join(fa, "TIERED_POOL.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\n=== DON'S RULE ===")
    for arm, d in res["decision"].items():
        if d.get("PASSES") is None:
            print("  %-16s %s" % (arm, d.get("reason")))
            continue
        print("  %-16s PASSES=%s" % (arm, d["PASSES"]))
        for k, v in d["return_steps"].items():
            print("      %-18s arm %s vs inc %s -> beats %s"
                  % (k, _f4(v["arm"]), _f4(v["incumbent"]), v["beats"]))
        for k, v in d["drawdown"].items():
            print("      dd %-15s arm %s vs inc %s -> within 3pp %s"
                  % (k, _f4(v["arm"]), _f4(v["incumbent"]), v["within_3pp"]))
    print("\nwrote %s" % os.path.join(fa, "TIERED_POOL.json"))
    return 0


def _f4(v):
    try:
        return "%.4f" % float(v)
    except (TypeError, ValueError):
        return str(v)


def TP_live(panel, want):
    """Reuse `UNIVERSE-BIAS`'s live-theme check rather than counting columns PRESENT -- a
    constant column is present and dead, which cost that item a whole pass."""
    from scripts.universe_bias_arms import live_themes
    return live_themes(panel, want)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--kill" in argv:
        return kill_pass()
    if "--arms" in argv:
        return arms_pass()
    print("usage: python -m scripts.tiered_pool_run --kill   # section 2c, its OWN pass, first\n"
          "       python -m scripts.tiered_pool_run --arms   # refuses without a passing kill")
    return 2


if __name__ == "__main__":
    sys.exit(main())
