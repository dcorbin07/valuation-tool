"""A3 — score the VRP arm against the gate committed in `options_vrp`'s header, and compute
THE KEY NUMBER: its return correlation with the single-leg arm.

Reads the trade bank written by `optvrp_run.py` and the single-leg bank written by
`optbt_run.py`, and writes one JSON with every block the close-out requires: coverage, sanity,
costs, the no-edge self-test, the held-out split, the left tail, the portfolio book (plain and
vol-targeted), the stress correlation, and the arm correlation.

Nothing here chooses a parameter. Every threshold it reports against is a module constant that
was committed before the backtest ran.
"""
import sys, os, json, pickle, warnings

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from valuation.edge import options_backtest as OB
from valuation.edge import options_vrp as V
from valuation.edge import options_vrp_portfolio as P
from valuation.edge.options_tracker import _stats

ROOT = r"C:\Users\donni\Downloads\valuation-tool"
OPTROOT = os.path.join(ROOT, "data", "options")
# Optional argv[1] names a different trade bank (the pre-registered 25% bid-ask sensitivity
# writes its own). The output JSON is named after it so a sensitivity run can never overwrite
# the headline.
_TAG = sys.argv[1] if len(sys.argv) > 1 else ""
VRP_STATE = os.path.join(OPTROOT, "optvrp_state%s.pkl" % _TAG)
SINGLE_STATE = os.path.join(OPTROOT, "optbt_state.pkl")
OUT_JSON = os.path.join(OPTROOT, "VRP_RESULTS%s.json" % _TAG)


def load(path):
    with open(path, "rb") as f:
        return pickle.load(f)


def main():
    st = load(VRP_STATE)
    rows = [r for r in st["trades"] if r.get("pnl_pct") is not None]
    mirror = st.get("mirror") or []
    single = load(SINGLE_STATE)["trades"] if os.path.exists(SINGLE_STATE) else []
    print(f"VRP trades {len(rows)} | mirror {len(mirror)} | single-leg {len(single)} "
          f"| names {len(st['done'])}", flush=True)
    if not rows:
        print("no trades — nothing to score", flush=True)
        return

    tickers = sorted({r["ticker"] for r in rows})
    bars_by = {t: OB.load_bars(t) for t in tickers}
    bars_by = {t: b for t, b in bars_by.items() if b}
    panel = P.build_returns_panel(bars_by)

    # Cross-sectional average ATM IV per day — the exogenous marker the regime split uses.
    iv_by_date = {}
    iv_path = os.path.join(OPTROOT, "atm_iv_series.pkl")
    if os.path.exists(iv_path):
        acc = {}
        for t, ser in load(iv_path).items():
            for d, v in (ser or {}).items():
                if v is not None and v == v:
                    a = acc.setdefault(d, [0.0, 0])
                    a[0] += v
                    a[1] += 1
        iv_by_date = {d: s / n for d, (s, n) in acc.items() if n >= 10}

    book = P.simulate_book(rows, panel, vol_target=False)
    book_vt = P.simulate_book(rows, panel, vol_target=True)
    corr = P.arm_correlation(rows, single) if single else None
    gate = V.evaluate_gate(rows, mirror, portfolio=book, correlation=corr)

    out = {
        "generated": __import__("datetime").date.today().isoformat(),
        "universe": {"names_scored": len(st["done"]), "names_with_trades": len(tickers),
                     "gaps": st.get("gaps", {})},
        "config": st.get("config", {}),
        "overall": _stats(rows),
        "held_out": V.held_out_split(rows),
        "by_year": V.by_year(rows),
        "by_iv_rank": V.by_iv_rank(rows),
        "tail": V.tail_report(rows),
        "stress": V.stress_test(rows),
        "gap_through_counterfactual": V.gap_through_counterfactual(rows),
        "costs": V.costs_block(rows),
        "signal_coverage": V.coverage_block(rows, st.get("funnel", {})),
        "sanity_check": V.sanity_block(rows),
        "self_test": V.self_test_block(rows, mirror),
        "portfolio": book,
        "portfolio_vol_targeted": book_vt,
        "stress_correlation": P.stress_correlation(panel, tickers, iv_by_date=iv_by_date),
        "arm_correlation": corr,
        "gate": gate,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"wrote {OUT_JSON}", flush=True)

    o = out["overall"]
    h = out["held_out"]
    print("\n=== VRP put-credit-spread arm ===")
    print(f"  closed trades   {o['n_closed']}")
    print(f"  hit rate        {o['hit_rate']}")
    print(f"  expectancy/risk {o['expectancy_pct']}")
    print(f"  profit factor   {o['profit_factor']}")
    print(f"  first half      n={h['first_half']['n_closed']} "
          f"exp={h['first_half']['expectancy_pct']}")
    print(f"  second half     n={h['second_half']['n_closed']} "
          f"exp={h['second_half']['expectancy_pct']}")
    print(f"  self-test       both_sides_profitable="
          f"{out['self_test']['both_sides_profitable']} "
          f"(mirror exp {out['self_test']['mirror_expectancy_pct']})")
    print(f"  book            final={book.get('final_equity')} "
          f"maxDD={book.get('max_drawdown')} sharpe={book.get('sharpe')}")
    if corr and "monthly_correlation" in corr:
        print(f"  ARM CORRELATION {corr['monthly_correlation']} "
              f"(down-months {corr['correlation_in_single_leg_down_months']})")
        print(f"  sharpe          single={corr['single_leg_sharpe']} "
              f"vrp={corr['vrp_sharpe']} combined={corr['combined_sharpe']}")
    g = out["gap_through_counterfactual"]
    print(f"  gap model       honest {g['honest_expectancy_pct']} vs naive-2x-stop "
          f"{g['naive_expectancy_pct']} (median gap {g['median_gap_multiple']}x) "
          f"| verdict rests on it: {g['verdict_rests_on_the_gap_model']}")
    print(f"  sanity          {out['sanity_check']['flags'] or 'clean'}")
    print(f"  GATE            adopt={gate['adopt']} checks={gate['checks']}")


if __name__ == "__main__":
    main()
