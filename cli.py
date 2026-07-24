"""
Command-line / batch mode — value or rank tickers without the web UI.

    python cli.py AAPL                 # value one ticker, print summary
    python cli.py AAPL --excel --pdf   # also write the Excel model + PDF report
    python cli.py AAPL MSFT NVDA KO --rank    # score & rank a watchlist
    python cli.py AAPL --ai            # include AI qualitative analysis
"""
import argparse
import sys

from valuation.config import CONFIG
from valuation.engine.pipeline import value_ticker


def _fmt_money(x):
    return f"${x:,.2f}" if x is not None else "n/a"


def _fmt_pct(x):
    return f"{x*100:+.0f}%" if x is not None else "n/a"


def value_one(ticker, args):
    r = value_ticker(ticker, CONFIG, run_ai=args.ai)
    c = r.company
    print("\n" + "=" * 58)
    print(f"  {c.name} ({c.ticker})   [{r.classification.regime}]")
    print("=" * 58)
    print(f"  Price          {_fmt_money(c.price)}")
    print(f"  Base fair value{_fmt_money(r.base_fair_value):>14}   ({_fmt_pct(r.upside)})")
    print(f"  Bear/Base/Bull {_fmt_money(r.scenarios.bear.per_share)} / "
          f"{_fmt_money(r.scenarios.base.per_share)} / {_fmt_money(r.scenarios.bull.per_share)}")
    print(f"  WACC           {r.wacc.wacc*100:.1f}%")
    print(f"  SCORE          {r.score.score}/100  -> {r.score.recommendation} "
          f"(confidence: {r.score.confidence})")
    subs = r.score.subscores
    print("  sub-scores     " + "  ".join(f"{k}:{v:.0f}" for k, v in subs.items() if v is not None))
    if r.montecarlo.prob_undervalued is not None:
        print(f"  Monte Carlo    P(undervalued) {r.montecarlo.prob_undervalued*100:.0f}%  "
              f"median {_fmt_money(r.montecarlo.median)}")
    print(f"  Reverse DCF    {r.reverse.growth_verdict}")
    if r.ai:
        print(f"\n  AI take: {r.ai.get('overall_take','')}")
    if r.company.quality_notes:
        print("  ! " + "; ".join(r.company.quality_notes))

    if args.excel:
        from valuation.report import excel
        p = f"{ticker}_DCF_Model.xlsx"
        excel.build_workbook(r, p)
        print(f"  wrote {p}")
    if args.pdf:
        from valuation.report import pdf
        if r.ai is None:
            from valuation.ai.analyst import analyze
            r.ai = analyze(r, CONFIG)
        p = f"{ticker}_Valuation_Report.pdf"
        pdf.build_pdf(r, p)
        print(f"  wrote {p}")


def rank(tickers, args):
    rows = []
    for t in tickers:
        try:
            r = value_ticker(t, CONFIG, mc_trials=2000)
            rows.append((r.score.score, t, r.company.name, r.company.price,
                         r.base_fair_value, r.upside, r.score.recommendation, r.classification.regime))
        except Exception as e:
            rows.append((-1, t, f"ERROR: {e}", None, None, None, "-", "-"))
    rows.sort(reverse=True)
    print(f"\n{'#':>2}  {'TICKER':<7}{'SCORE':>6}  {'PRICE':>9}{'FAIRVAL':>10}{'UPSIDE':>8}  {'CALL':<11}{'REGIME'}")
    print("-" * 74)
    for i, (score, t, name, px, fv, up, rec, reg) in enumerate(rows, 1):
        if score < 0:
            print(f"{i:>2}  {t:<7}   -    {name}")
            continue
        print(f"{i:>2}  {t:<7}{score:>6}  {_fmt_money(px):>9}{_fmt_money(fv):>10}"
              f"{_fmt_pct(up):>8}  {rec:<11}{reg}")


def main():
    ap = argparse.ArgumentParser(description="Adaptive DCF valuation — CLI")
    ap.add_argument("tickers", nargs="+", help="one or more ticker symbols")
    ap.add_argument("--rank", action="store_true", help="score and rank all tickers")
    ap.add_argument("--ai", action="store_true", help="include AI qualitative analysis")
    ap.add_argument("--excel", action="store_true", help="write Excel model (single-ticker mode)")
    ap.add_argument("--pdf", action="store_true", help="write PDF report (single-ticker mode)")
    args = ap.parse_args()
    tickers = [t.strip().upper() for t in args.tickers]
    if args.rank or len(tickers) > 1 and not (args.excel or args.pdf):
        rank(tickers, args)
    else:
        for t in tickers:
            value_one(t, args)


if __name__ == "__main__":
    sys.exit(main())
