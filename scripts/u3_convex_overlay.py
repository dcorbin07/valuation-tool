"""U3 — run the convex-overlay register.

    python -m scripts.u3_convex_overlay

Registered in `PREREG_u3_convex_overlay.md`, committed ALONE at `9603e64` before the instrument
existed. Frozen books on both sides; nothing here adopts anything and no live code path changes.

The controls run and are READ before any arm is scored — session 26's defect was computing a
gating control and the outcomes in the same pass, so that it could not be claimed the control
was read first. C1/C2 abort the run.
"""
from __future__ import annotations

import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.studies import convex_overlay as CO
from valuation.edge.fundamental_panel import quantile_backtest

# ---- PRE-REGISTERED constants -------------------------------------------------------------
DEPLOYED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
            "capital_discipline": 0.125, "size": 0.125, "institutional": 0.125}
COLS = list(DEPLOYED)

ROOT = r"C:/Users/donni/Downloads/valuation-tool"
PANEL = os.path.join(ROOT, "data/free_analysis/panel_corrected_69d.pkl")
BOOK = os.path.join(ROOT, "data/options_universe/state_r2_splitclean.pkl")
MARKS = os.path.join(ROOT, "data/free_analysis/O11_MARKS.pkl")
OUT = os.path.join(ROOT, "data/free_analysis/U3_CONVEX_OVERLAY.json")


def _load():
    panel = pd.read_pickle(PANEL)
    with open(BOOK, "rb") as fh:
        st = pickle.load(fh)
    book = pd.DataFrame(st["rows"])
    with open(MARKS, "rb") as fh:
        marks = pickle.load(fh)
    return panel, book, marks


def main() -> int:
    panel, book, marks = _load()
    art = {"item": "U3", "register": "PREREG_u3_convex_overlay.md",
           "register_commit": "9603e64", "controls": {}, "arms": {}}

    # ---------------------------------------------------------------- C1 / C2: gate the run
    print("C1 — reproducing the published equity record ...")
    qb = quantile_backtest(panel, COLS, DEPLOYED, n_q=10, horizon=63, return_series=True)
    c1 = {"top_decile_alpha": qb["top_decile_alpha"],
          "long_short_tstat": qb["long_short_tstat"],
          "equal_weight_ann": qb["equal_weight_ann"],
          "monotonicity": qb["monotonicity"]}
    c1_ok = (abs(c1["top_decile_alpha"] - CO.RECORD["top_decile_alpha"]) < 1e-4
             and abs(c1["equal_weight_ann"] - CO.RECORD["equal_weight_ann"]) < 1e-4
             and abs(c1["long_short_tstat"] - CO.RECORD["long_short_tstat"]) < 1e-3)
    c1["passes"] = bool(c1_ok)
    art["controls"]["C1_harness"] = c1
    print(f"    alpha {c1['top_decile_alpha']:+.6f} (record {CO.RECORD['top_decile_alpha']:+.6f})"
          f"  ls_t {c1['long_short_tstat']:.4f}  ew {c1['equal_weight_ann']:+.6f}"
          f"  -> {'PASS' if c1_ok else 'FAIL'}")
    if not c1_ok:
        print("VOID (condition 1): the harness does not reproduce the record. No arm read.")
        return 2

    print("C2 — reproducing the split-clean book's own record ...")
    mean_pnl = float(pd.to_numeric(book["pnl_pct"], errors="coerce").mean())
    c2_ok = abs(mean_pnl - CO.BOOK_MEAN_PNL) < 1e-4
    art["controls"]["C2_book"] = {"mean_pnl_pct": mean_pnl,
                                  "record": CO.BOOK_MEAN_PNL, "n": int(len(book)),
                                  "passes": bool(c2_ok)}
    print(f"    mean per-trade P&L {mean_pnl:+.6f} on {len(book)} trades "
          f"-> {'PASS' if c2_ok else 'FAIL'}")
    if not c2_ok:
        print("VOID (condition 1): the book does not reproduce its record. No arm read.")
        return 2

    eq = CO.top_decile_series(qb)
    print(f"\nequity periods: {len(eq)}  {eq['date'].min().date()} .. {eq['date'].max().date()}")

    # ---------------------------------------------------------------- sleeve curves
    boundaries = list(eq["date"])
    curves = {}
    for cap in CO.CONCURRENCY_CAPS:
        c = CO.sleeve_curve(book, marks, boundaries, cap=cap)
        curves[cap] = c
        print(f"sleeve cap {cap:>2}: taken {c.attrs['taken']}, refused {c.attrs['refused']}, "
              f"quarters with marks {int(c['sleeve'].notna().sum())}")

    # covered quarters: those with >= MIN_TRADES_PER_QUARTER open positions at BOTH caps
    base = curves[CO.CONCURRENCY_CAPS[-1]]
    merged = eq.merge(base[["date", "sleeve", "n_open"]], on="date", how="left")
    covered = merged[(merged["n_open"].fillna(0) >= CO.MIN_TRADES_PER_QUARTER)
                     & merged["sleeve"].notna()].reset_index(drop=True)
    print(f"\ncovered quarters: {len(covered)} of {len(eq)}  "
          f"{covered['date'].min().date()} .. {covered['date'].max().date()}")
    art["coverage"] = {"n_covered": int(len(covered)), "n_panel": int(len(eq)),
                       "first": str(covered["date"].min().date()),
                       "last": str(covered["date"].max().date()),
                       "n_uncovered_early": int((eq["date"] < covered["date"].min()).sum()),
                       "n_uncovered_late": int((eq["date"] > covered["date"].max()).sum())}

    # ---------------------------------------------------------------- C3: no look-ahead
    viol = 0
    checked = 0
    bd = list(eq["date"])
    for (tkr, alert, _e, _s), seq in marks.items():
        for d, _p in seq:
            dt = pd.Timestamp(d)
            if dt < pd.Timestamp(alert):
                viol += 1
            checked += 1
    art["controls"]["C3_lookahead"] = {"marks_checked": checked, "violations": viol,
                                       "passes": viol == 0}
    print(f"C3 — {checked} marks checked, {viol} dated before their own alert "
          f"-> {'PASS' if viol == 0 else 'FAIL'}")
    if viol:
        print("VOID (condition 2).")
        return 2

    # ---------------------------------------------------------------- C4: the identity
    d4 = float(np.max(np.abs((np.asarray(qb["series"]["alpha"])
                              + np.asarray(qb["series"]["equal_weight"]))
                             - eq["top"].to_numpy())))
    art["controls"]["C4_identity"] = {"max_abs_dev": d4, "passes": d4 < 1e-12}
    print(f"C4 — top == alpha + equal_weight, max |dev| {d4:.3e} "
          f"-> {'PASS' if d4 < 1e-12 else 'FAIL'}")

    # ---------------------------------------------------------------- C8: X=100 exact
    e_list = list(covered["top"])
    s_list = list(covered["sleeve"])
    d8 = float(np.max(np.abs(np.asarray(CO.combine(e_list, s_list, 100)) - np.asarray(e_list))))
    art["controls"]["C8_endpoint"] = {"max_abs_dev": d8, "passes": d8 < 1e-12}
    print(f"C8 — X=100 reproduces the equity book, max |dev| {d8:.3e} "
          f"-> {'PASS' if d8 < 1e-12 else 'FAIL'}")
    if d8 >= 1e-12:
        print("VOID (condition 3).")
        return 2

    # ---------------------------------------------------------------- halves
    try:
        early, late, boundary = CO.halves(len(covered))
    except CO.RegisterViolation as exc:
        print(f"VOID (condition 4): {exc}")
        return 2
    art["halves"] = {"n_early": len(early), "n_late": len(late),
                     "boundary_embargoed": str(covered["date"].iloc[boundary].date())}
    print(f"halves: {len(early)} early, {len(late)} late, boundary "
          f"{covered['date'].iloc[boundary].date()} embargoed")

    # ---------------------------------------------------------------- C5: costs only hurt
    dear = CO.sleeve_curve(book, marks, boundaries, cap=CO.CONCURRENCY_CAPS[-1], rho=1.0)
    dm = eq.merge(dear[["date", "sleeve"]], on="date", how="left", suffixes=("", "_dear"))
    dm = dm[dm["date"].isin(covered["date"])]
    worse = float(np.nanmax(np.asarray(dm["sleeve"]) - np.asarray(s_list)))
    art["controls"]["C5_costs_only_hurt"] = {"max_improvement_at_rho_1": worse,
                                             "passes": worse <= 1e-12}
    print(f"C5 — at rho=1.0 the largest IMPROVEMENT is {worse:+.3e} "
          f"-> {'PASS' if worse <= 1e-12 else 'FAIL'}")

    # ---------------------------------------------------------------- C7: beta, or the book?
    c_top = float(np.corrcoef(covered["top"], covered["sleeve"])[0, 1])
    c_ew = float(np.corrcoef(covered["equal_weight"], covered["sleeve"])[0, 1])
    art["controls"]["C7_market_proxy"] = {
        "corr_with_top_decile": c_top, "corr_with_equal_weight": c_ew,
        "abs_gap": abs(c_top - c_ew),
        "note": ("If these are indistinguishable the sleeve carries no BOOK-specific "
                 "information and A2 is a statement about beta, not about this book.")}
    print(f"C7 — sleeve vs top-decile {c_top:+.4f}, vs equal-weight {c_ew:+.4f}, "
          f"gap {abs(c_top - c_ew):.4f}")

    # ---------------------------------------------------------------- ARMS
    print("\n" + "=" * 78)
    print("A2 — THE MECHANISM: does the sleeve pay when the equity book does not?")
    print("=" * 78)
    ivq = []
    bk = book.copy()
    bk["alert_ts"] = pd.to_datetime(bk["alert_ts"])
    for i in range(len(covered)):
        t0 = covered["date"].iloc[i]
        t1 = covered["date"].iloc[i + 1] if i + 1 < len(covered) else t0 + pd.Timedelta(days=95)
        w = bk[(bk["alert_ts"] >= t0) & (bk["alert_ts"] < t1)]
        ivq.append(float(pd.to_numeric(w["iv"], errors="coerce").median())
                   if len(w) else np.nan)
    a2 = CO.arm_a2(list(covered["top"]), list(covered["sleeve"]), ivq)
    a2["iv_proxy"] = "median entry IV of trades alerted in the quarter"
    art["arms"]["A2_mechanism"] = a2
    print(f"  unconditional correlation      {a2['correlation_unconditional']:+.4f}")
    print(f"  high-IV half (audit's PRIMARY) {a2['correlation_high_iv']}")
    print(f"  low-IV half                    {a2['correlation_low_iv']}")
    print(f"  equity worst decile (RETURN-conditioned, audit step 2) "
          f"{a2['correlation_equity_worst_decile_RETURN_CONDITIONED']}")
    print(f"  sleeve mean, all quarters      {a2['sleeve_mean_all_quarters']:+.4%}")
    print(f"  sleeve mean, worst {a2['n_worst']} quarters   "
          f"{a2['sleeve_mean_worst_decile']:+.4%}  "
          f"(equity {a2['equity_mean_worst_decile']:+.4%})")
    print(f"  IS INSURANCE: {a2['is_insurance']}")
    print(f"  -> {a2['reading']}")

    print("\n" + "=" * 78)
    print("A1 — THE OVERLAY")
    print("=" * 78)
    a1_by_cap = {}
    for cap in CO.CONCURRENCY_CAPS:
        cc = eq.merge(curves[cap][["date", "sleeve"]], on="date", how="left",
                      suffixes=("", f"_c{cap}"))
        cc = cc[cc["date"].isin(covered["date"])].reset_index(drop=True)
        r = CO.arm_a1(list(cc["top"]), list(cc["sleeve"]), early, late)
        a1_by_cap[str(cap)] = r
        b = r["baseline"]["full"]
        print(f"\n  cap {cap}: equity alone  Sharpe {b['sharpe']:.4f}  "
              f"maxDD {b['max_drawdown']:+.4f}  ann {b['ann']:+.4%}")
        for x in CO.X_GRID:
            c = r["cells"]["full"][x]
            print(f"    X={x}  Sharpe {c['sharpe']:.4f}  maxDD {c['max_drawdown']:+.4f}  "
                  f"ann {c['ann']:+.4%}   dSharpe {c['sharpe']-b['sharpe']:+.4f}  "
                  f"dMaxDD {c['max_drawdown']-b['max_drawdown']:+.4f}")
        print(f"  X clearing BOTH halves: {r['x_clearing_both_halves'] or 'NONE'}")
        print(f"  VERDICT: {r['verdict']}")
    art["arms"]["A1_overlay"] = a1_by_cap

    verdicts = {c: a1_by_cap[str(c)]["verdict"] for c in CO.CONCURRENCY_CAPS}
    art["arms"]["A1_overall"] = ("REJECTED" if all(v == "REJECTED" for v in verdicts.values())
                                 else "ELIGIBLE-BUT-UNRESOLVED")

    print("\n" + "=" * 78)
    print("A3 — THE COST OF CARRY (measurement, no bar, charges no trial)")
    print("=" * 78)
    a3 = CO.arm_a3(list(covered["top"]), list(covered["sleeve"]))
    art["arms"]["A3_cost_of_carry"] = a3
    print(f"  equity alone {a3['equity_ann']:+.4%}/yr   sleeve alone "
          f"{a3['sleeve_ann_geometric']:+.4%}/yr geometric, "
          f"{a3['sleeve_mean_arithmetic']:+.4%}/quarter arithmetic")
    for x in CO.X_GRID:
        print(f"    X={x}  combined {a3['by_x'][x]['ann']:+.4%}/yr  "
              f"combined-minus-equity {a3['by_x'][x]['combined_minus_equity_pp']:+.4f}pp")

    # drawdown episode count — the number that must travel with any drawdown claim
    ep = CO.drawdown_episodes(list(covered["top"]))
    art["drawdown_episodes_equity"] = ep
    worst_i = int(np.argmin(covered["top"].to_numpy()))
    worst_s = int(np.argmin(covered["sleeve"].to_numpy()))
    art["worst_quarter"] = {"date": str(covered["date"].iloc[worst_i].date()),
                            "equity_top": float(covered["top"].iloc[worst_i]),
                            "sleeve": float(covered["sleeve"].iloc[worst_i])}
    # expectation 7 needs the SLEEVE's own worst quarter, not only the equity book's
    art["worst_quarter_for_sleeve"] = {"date": str(covered["date"].iloc[worst_s].date()),
                                       "sleeve": float(covered["sleeve"].iloc[worst_s]),
                                       "equity_top": float(covered["top"].iloc[worst_s]),
                                       "is_the_same_quarter": bool(worst_s == worst_i)}
    print(f"\ndistinct equity drawdown episodes deeper than 5%: {ep}")
    print(f"worst covered quarter for EQUITY: {art['worst_quarter']}")
    print(f"worst covered quarter for SLEEVE: {art['worst_quarter_for_sleeve']}")

    art["verdict"] = {
        "A1": art["arms"]["A1_overall"],
        "A2": "NOT INSURANCE" if not a2["is_insurance"] else "consistent with insurance",
        "headline": ("The sleeve co-moves WITH the equity book and loses most in the quarters "
                     "the equity book loses in. It is leverage, not insurance."
                     if not a2["is_insurance"] else
                     "The sleeve moves against the equity book; the SIZE of the benefit rests "
                     "on the crash count and is not resolvable on this sample."),
    }

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, default=str)
    print(f"\nartifact -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
