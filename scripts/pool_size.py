# -*- coding: utf-8 -*-
"""`POOL-SIZE` part (a) — the pool-size ladder on 2009-2026. Register `PREREG_pool_size.md`.

Does a wider pool keep helping, and where does it start to hurt? Seven pools, **one
construction**: top decile by the shipped composite, score-weighted, 8% cap, 0.30 no-trade band,
quarterly, flat 1/7, net of the shipped **size-aware market-cap cost table**. The pool is the
only thing that changes.

**THE MACHINERY IS CALLED, NEVER REBUILT** (`B7`, `MA5`): `served_index_book.book_fn`,
`after_tax_backtest`, `valquo_index.trim_universe`, `no_trade_band.BAND_WIDTH`. The Roth leg is
`after_tax_backtest` with both tax rates set to zero, which is `INDEX-BEST`'s own definition --
not a second implementation of it.

**THE LADDER IS CAP-RANKED, NOT LIQUIDITY-RANKED, AND THAT IS FORCED.** `trim_universe` ranks by
point-in-time market cap. A genuine ADV ladder is not constructible: `B13_ADV_PANEL` reaches 64
of 69 dates and a maximum of 1,832 names, so a 2,000-name liquidity rung cannot be formed on any
date. §2a of the register has the full argument.

**`C1` GATES EVERYTHING** -- three rungs are already banked by `INDEX-BEST` and must reproduce at
max absolute deviation 0.000e+00, with the compared-leaf count gated non-zero (`MB21`).
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

from valuation.studies import served_index_book as IB                     # noqa: E402
from valuation.edge.no_trade_band import BAND_WIDTH                       # noqa: E402
from valuation.edge.fundamental_panel import after_tax_backtest as at_bt  # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED, BASE_WEIGHT            # noqa: E402
from scripts.index_best import PER_YEAR, _ann, data_candidates, _data_root  # noqa: E402

DATA = _data_root(required=False)
FA = os.path.join(DATA, "free_analysis") if DATA else None
OUT = os.path.join(FA, "POOL_SIZE_LADDER.json") if FA else None

#: The ladder, ordered by POOL SIZE ASCENDING -- the order the decision rule scans.
#: `large_cap_min=0.0` means no tier floor; `universe_rank=None` means no trim.
RUNGS = [
    ("1_incumbent_10bn", {"large_cap_min": 1e10, "universe_rank": None, "top_n": None}),
    ("2_top500",         {"large_cap_min": 0.0, "universe_rank": 500, "top_n": None}),
    ("3_top1000",        {"large_cap_min": 0.0, "universe_rank": 1000, "top_n": None}),
    ("4_top1500",        {"large_cap_min": 0.0, "universe_rank": 1500, "top_n": None}),
    ("5_top2000",        {"large_cap_min": 0.0, "universe_rank": 2000, "top_n": None}),
    ("6_full_panel",     {"large_cap_min": 0.0, "universe_rank": None, "top_n": None}),
]

#: `INDEX-BEST`'s banked figures, QUOTED so `C1` compares against the record rather than against
#: this run's own output. Source: data/free_analysis/INDEX_BEST.json.
BANKED = {
    "1_incumbent_10bn": {"roth_net_ann": 0.1716188056513155,
                         "roth_max_drawdown": -0.23028569279336075,
                         "annual_turnover": 2.437245082733814,
                         "realised_one_way_bps": 9.584461976204357},
    "4_top1500": {"roth_net_ann": 0.2294646167705674,
                  "roth_max_drawdown": -0.27600090292443336,
                  "annual_turnover": 1.9268114715770899,
                  "realised_one_way_bps": 29.344051612262923},
    "6_full_panel": {"roth_net_ann": 0.24950546311372124,
                     "roth_max_drawdown": -0.2780650330457006,
                     "annual_turnover": 1.8590714732972382,
                     "realised_one_way_bps": 35.60466789248458},
}
#: `INDEX-BEST`'s own arm names for the three banked rungs, so the gate reads the right block.
BANKED_AS = {"1_incumbent_10bn": "1_incumbent_10bn", "4_top1500": "2_liquid_decile",
             "6_full_panel": "4_all_cap_ceiling"}

DD_ALLOWANCE = 0.03          # Don's 3pp, pre-committed. NOT to be moved (W-28).
MICRO_CAP = 300e6            # the register's "under $300M" line


def _mdd(xs):
    """Max drawdown of a compounded series. NEGATIVE by convention -- the sign is written out
    because `S10` once reported a 2.61pp worsening as an improvement by flipping it."""
    lvl, peak, worst = 1.0, 1.0, 0.0
    for x in xs:
        lvl *= (1.0 + x)
        peak = max(peak, lvl)
        worst = min(worst, lvl / peak - 1.0)
    return float(worst)


def _sharpe(xs):
    a = np.asarray([x for x in xs if x == x], dtype=float)
    if a.size < 2 or a.std(ddof=1) == 0:
        return None
    return float(a.mean() / a.std(ddof=1) * np.sqrt(PER_YEAR))


def _roth(panel, cols, weights, kw):
    """One rung, from the TWO sources `INDEX-BEST` itself banked -- which is a fact about that
    item, not a choice made here.

    **THE TWO PATHS ARE NOT THE SAME NUMBER, measured:** for the incumbent,
    `after_tax_backtest` (rates at zero) returns **0.1716188056513155** while `IB.run` returns
    **0.17181671234700224** -- they differ by about 0.02pp because the first walks TAX LOTS and
    the second compounds period returns. `INDEX-BEST` banked `roth_net_ann` from the former and
    `annual_turnover` / `realised_one_way_bps` from the latter, and its own gate quotes
    `IB.run`'s figure. So each metric is taken from the source that banked it; mixing them the
    other way would make `C1` fail against a correct tree.

    Turnover and realised cost agree EXACTLY between the two paths, which is why they can be
    taken from either -- checked rather than assumed.
    """
    bf = IB.book_fn(weighting="score", exit_frac=BAND_WIDTH, **kw)
    r = at_bt(panel, cols, weights, exit_frac=BAND_WIDTH, book_fn=bf,
              short_rate=0.0, long_rate=0.0, return_series=True)
    if not isinstance(r, dict) or r.get("after_tax_ann") is None:
        return None
    s = r["series"]
    g = IB.run(panel, cols, weights, weighting="score", exit_frac=BAND_WIDTH, **kw)
    return {
        "roth_net_ann": float(r["after_tax_ann"]),
        "net_series": [float(x) for x in s["net"]],
        "gross_series": [float(x) for x in s.get("gross", s["net"])],
        "n_periods": int(r["n_periods"]),
        "annual_turnover": (float(g["annual_turnover"])
                            if g.get("annual_turnover") is not None else None),
        "realised_one_way_bps": (float(g["realised_one_way_bps"])
                                 if g.get("realised_one_way_bps") is not None else None),
        "ib_run_net_ann": (float(g["net_ann"]) if g.get("net_ann") is not None else None),
        "ib_run_max_drawdown": (float(g["net_max_drawdown"])
                                if g.get("net_max_drawdown") is not None else None),
        "book_size": g.get("book_size"),
        "dates_below_contract_min_positions": g.get("dates_below_contract_min_positions"),
        "two_path_net_ann_gap_pp": (
            None if g.get("net_ann") is None
            else (float(g["net_ann"]) - float(r["after_tax_ann"])) * 100.0),
    }


def _spy_series(panel):
    return [float(panel[panel["date"] == d]["bench_ret"].iloc[0])
            for d in sorted(panel["date"].unique())]


def _paired(a, b):
    """Paired HAC inference on the per-period difference, with BOTH MDEs stated (MB22).

    EVERY CRITICAL VALUE HERE IS UNCALIBRATED and labelled so: `V2G` established and `R1-VAR`
    re-confirmed that no calibrated floor exists for a paired within-panel difference, and X7
    calibrates LEVELS. Nothing is compared to an X7 floor.
    """
    n = min(len(a), len(b))
    d = np.asarray(a[:n], dtype=float) - np.asarray(b[:n], dtype=float)
    d = d[~np.isnan(d)]
    if d.size < 3:
        return None
    m = float(d.mean())
    # Newey-West at lag 1, the project's own convention for this grid
    e = d - m
    g0 = float((e * e).mean())
    g1 = float((e[1:] * e[:-1]).mean()) if d.size > 1 else 0.0
    lrv = max(g0 + 2.0 * (1.0 - 1.0 / 2.0) * g1, 1e-30)
    se = float(np.sqrt(lrv / d.size))
    crit = 2.0
    return {
        "n": int(d.size), "mean_per_period": m, "paired_hac_se": se,
        "t_hac": (m / se if se > 0 else None),
        "crit_used": crit, "crit_LABEL": "UNCALIBRATED -- conventional 2.0; no calibrated floor "
                                         "exists for a paired within-panel difference (V2G, "
                                         "R1-VAR)",
        "mde_50pc": crit * se, "mde_80pc": (crit + 0.84) * se,
        "annualised_mean": float(np.prod([1.0 + x for x in d]) ** (PER_YEAR / d.size) - 1.0)
        if np.all(1.0 + d > 0) else None,
    }


def c1_gate(fa, scored):
    """Three banked rungs must reproduce at 0.000e+00. The COUNT is gated non-zero (MB21)."""
    p = os.path.join(fa, "INDEX_BEST.json")
    if not os.path.exists(p):
        return {"ok": False, "reason": "INDEX_BEST.json absent", "compared": 0}
    arms = (json.load(io.open(p, encoding="utf-8")).get("arms") or {})
    checks, worst, compared = {}, 0.0, 0
    for rung, want in BANKED.items():
        got = scored.get(rung)
        banked_arm = arms.get(BANKED_AS[rung]) or {}
        if got is None:
            return {"ok": False, "reason": "rung %s not scored" % rung, "compared": compared}
        for k, v in want.items():
            # compare against the ARTIFACT, and separately confirm the artifact matches the
            # literal quoted here -- a quoted constant that has drifted is worse than none
            art = banked_arm.get(k)
            if art is None or float(art) != float(v):
                return {"ok": False, "compared": compared,
                        "reason": "quoted %s/%s (%r) disagrees with INDEX_BEST.json (%r)"
                                  % (rung, k, v, art)}
            mine = got.get(k)
            if mine is None:
                return {"ok": False, "reason": "rung %s has no %s" % (rung, k),
                        "compared": compared}
            dev = abs(float(mine) - float(v))
            checks["%s/%s" % (rung, k)] = {"banked": float(v), "mine": float(mine),
                                           "abs_dev": dev}
            worst = max(worst, dev)
            compared += 1
    return {"ok": worst == 0.0 and compared > 0, "max_abs_dev": worst, "compared": compared,
            "checks": checks}


def decide(order, scored):
    """Don's rule, applied exactly as §1 of the register fixes it.

    LITERAL (primary): scan from the largest rung down, take the first whose OWN step clears
    both clauses against its immediate predecessor.
    CUMULATIVE (sensitivity): require both clauses at EVERY step up to the rung.
    """
    steps = []
    for i in range(1, len(order)):
        k, j = order[i], order[i - 1]
        a, b = scored.get(k), scored.get(j)
        if not a or not b:
            steps.append({"rung": k, "vs": j, "ok": None, "reason": "not scored"})
            continue
        ret_ok = float(a["roth_net_ann"]) >= float(b["roth_net_ann"])
        dd_ok = float(a["roth_max_drawdown"]) >= float(b["roth_max_drawdown"]) - DD_ALLOWANCE
        steps.append({
            "rung": k, "vs": j,
            "d_return_pp": (float(a["roth_net_ann"]) - float(b["roth_net_ann"])) * 100.0,
            "d_drawdown_pp": (float(a["roth_max_drawdown"])
                              - float(b["roth_max_drawdown"])) * 100.0,
            "return_not_lower": bool(ret_ok),
            "drawdown_within_3pp": bool(dd_ok),
            "ok": bool(ret_ok and dd_ok),
        })

    literal = order[0]
    for st in reversed(steps):
        if st.get("ok"):
            literal = st["rung"]
            break

    cumulative = order[0]
    for st in steps:
        if st.get("ok"):
            cumulative = st["rung"]
        else:
            break

    return {"steps": steps, "dd_allowance_pp": DD_ALLOWANCE * 100.0,
            "recommended_LITERAL_primary": literal,
            "recommended_CUMULATIVE_sensitivity": cumulative,
            "readings_agree": literal == cumulative,
            "rule": "the LARGEST pool whose net Roth return is not lower than the next-smaller "
                    "pool's and whose max drawdown is not more than 3pp worse (Don, "
                    "pre-committed in PREREG_pool_size.md section 1)"}


def main(argv=None) -> int:
    if not FA:
        raise SystemExit("the licensed panel is absent; tried %r" % (data_candidates(),))
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    cols, weights = list(DEPLOYED), {c: BASE_WEIGHT for c in DEPLOYED}
    grid = sorted(panel["date"].unique())
    spy = _spy_series(panel)
    print("panel %s | %d names | %d dates" % (panel.shape, panel["ticker"].nunique(), len(grid)),
          flush=True)

    # halves, boundary EMBARGOED exactly as INDEX-BEST does
    mid = len(grid) // 2
    early, late = set(grid[:mid]), set(grid[mid + 1:])

    scored = {}
    for name, kw in RUNGS:
        r = _roth(panel, cols, weights, kw)
        if r is None:
            print("  %-20s REFUSED (no result)" % name, flush=True)
            continue
        r["knobs"] = kw
        r["roth_max_drawdown"] = _mdd(r["net_series"])
        r["roth_sharpe"] = _sharpe(r["net_series"])
        r["spy_ann"] = _ann(spy)
        r["roth_excess_vs_spy"] = r["roth_net_ann"] - r["spy_ann"]
        # halves on the same series, by position against the grid
        ns = r["net_series"]
        e_idx = [i for i, d in enumerate(grid[:len(ns)]) if d in early]
        l_idx = [i for i, d in enumerate(grid[:len(ns)]) if d in late]
        r["early_roth_ann"] = _ann([ns[i] for i in e_idx]) if e_idx else None
        r["late_roth_ann"] = _ann([ns[i] for i in l_idx]) if l_idx else None
        r["early_spy_ann"] = _ann([spy[i] for i in e_idx]) if e_idx else None
        r["late_spy_ann"] = _ann([spy[i] for i in l_idx]) if l_idx else None
        scored[name] = r
        print("  %-20s roth %.4f  dd %.4f  turn %.4f  cost %.2fbps"
              % (name, r["roth_net_ann"], r["roth_max_drawdown"], r["annual_turnover"] or -1,
                 r["realised_one_way_bps"] or -1), flush=True)

    gate = c1_gate(FA, scored)
    print("\nC1 three-point reproduction: ok=%s max_abs_dev=%s compared=%d"
          % (gate["ok"], gate.get("max_abs_dev"), gate["compared"]), flush=True)
    if not gate["ok"]:
        print("REFUSING: %s" % gate.get("reason", "C1 did not reproduce"), flush=True)
        json.dump({"item": "POOL-SIZE", "part": "a", "c1": gate, "decided": False},
                  io.open(OUT, "w", encoding="utf-8"), indent=2)
        return 2

    order = [n for n, _ in RUNGS if n in scored]
    dec = decide(order, scored)

    pairs = {}
    for i in range(1, len(order)):
        k, j = order[i], order[i - 1]
        pairs["%s_vs_%s" % (k, j)] = _paired(scored[k]["net_series"], scored[j]["net_series"])

    res = {
        "item": "POOL-SIZE", "part": "a 2009-2026 ladder", "trials": 3,
        "register": "PREREG_pool_size.md",
        "construction": "top decile by the shipped composite, score-weighted, 8pc cap, 0.30 "
                        "no-trade band, quarterly, flat 1/7, net of the shipped size-aware "
                        "market-cap cost table; the POOL is the only thing that changes",
        "rank_key": "point-in-time market cap (trim_universe's default) -- CAP-RANKED, NOT "
                    "liquidity-ranked; forced, see register section 2a",
        "machinery": "served_index_book.book_fn + after_tax_backtest with both tax rates at "
                     "zero, which is INDEX-BEST's own Roth definition (B7)",
        "n_dates": len(grid), "n_names_panel": int(panel["ticker"].nunique()),
        "spy_ann": _ann(spy),
        "c1": gate,
        "rungs": scored,
        "decision": dec,
        "paired_steps": pairs,
        "significance_LABEL": "NO RUNG IS CALLED SIGNIFICANT. The rule is a PREFERENCE rule, "
                              "not a significance test; adjacent rungs are almost certainly not "
                              "separable and every MDE here says so.",
    }
    json.dump(res, io.open(OUT, "w", encoding="utf-8"), indent=2, default=str)

    print("\n=== THE LADDER ===")
    print("%-20s %>9s" % ("rung", "")) if False else None
    print("%-20s %9s %9s %9s %9s %9s" % ("rung", "roth/yr", "vs SPY", "maxDD", "turnover",
                                         "cost bps"))
    for n in order:
        r = scored[n]
        print("%-20s %8.2f%% %8.2f%% %8.2f%% %9.3f %9.1f"
              % (n, r["roth_net_ann"] * 100, r["roth_excess_vs_spy"] * 100,
                 r["roth_max_drawdown"] * 100, r["annual_turnover"] or float("nan"),
                 r["realised_one_way_bps"] or float("nan")))
    print("\n=== DON'S RULE, STEP BY STEP ===")
    for st in dec["steps"]:
        if st.get("ok") is None:
            print("  %-20s %s" % (st["rung"], st["reason"]))
            continue
        print("  %-20s vs %-18s dRet %+6.2fpp  dDD %+6.2fpp  ret_ok=%-5s dd_ok=%-5s -> %s"
              % (st["rung"], st["vs"], st["d_return_pp"], st["d_drawdown_pp"],
                 st["return_not_lower"], st["drawdown_within_3pp"],
                 "CLEARS" if st["ok"] else "fails"))
    print("\nRECOMMENDED (literal, primary) : %s" % dec["recommended_LITERAL_primary"])
    print("RECOMMENDED (cumulative, sens.): %s" % dec["recommended_CUMULATIVE_sensitivity"])
    print("readings agree: %s" % dec["readings_agree"])
    print("\nwrote %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
