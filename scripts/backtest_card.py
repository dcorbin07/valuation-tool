"""Derive the backtested card's four lines and publish them where the service can read them.

WHY THIS EXISTS RATHER THAN A LITERAL ON A PAGE. The card used to print a single unlabelled
"Alpha / yr" taken from `settings.BOOK_CONFIGS`, whose own comment records that its
`cost_drag_ann` is a **pre-B6 figure that was never re-measured**. An alpha with no named
benchmark is not a claim anyone can check: this project's `alpha` has at various times meant
"versus the equal-weighted universe" (uninvestable, charged zero cost) and "versus SPY", and
those differ by several points a year on the same book.

**EVERY LINE NAMES ITS BENCHMARK, AND ALL FOUR COME OFF ONE SERIES.** The basis is
`costs.top_25` in `BACKTEST_RESULTS.json` -- the roth book -- and that identification is
MEASURED rather than assumed: its `annual_turnover` equals `book_configs.roth.annual_turnover`
exactly, and it is the only block in the file carrying a gross AND a net figure produced by the
same cost model on the same series.

**A CORRECTION TO THE BRIEF, MADE BECAUSE THE TWO NAMES POINT AT DIFFERENT BOOKS.** The task
says "the portfolio block (the roth book)". Those are not the same object: `portfolio` is the
B17 hysteresis book (`target_n` 25 but `exit_rank` 50, realised median 42 names) and it ships
`charges_costs: false`, while roth carries no band at all (`exit_frac` and `exit_mult` are both
None). Building on `portfolio` would have meant inventing its net, because `_backtest_hold`
charges only a FLAT bps and the measured model is a market-cap table -- so the only available
net would have been a rate measured on a different construction, which is the borrowed-number
defect `MB8` recorded. The roth book needs no invention: its net is already measured.

**THE SPMO LINE IS A PARTIAL WINDOW AND IS RE-SCORED, NOT SLICED FROM AN ANNUAL FIGURE.** SPMO
listed 2015-10-09. Comparing the book's 17-year annualised return against a 10-year ETF would
be wrong by construction, so the BOOK is re-scored on the panel restricted to that window and
both are measured over the same span.

**AND THE PARTIAL-WINDOW SPY FIGURE IS NOT OPTIONAL.** The book earned more in the recent
window than over the full history, so a reader comparing a full-window SPY excess against a
partial-window SPMO excess would conclude SPMO is the EASIER benchmark. It is the harder one:
on the same window the book beats SPY by more than it beats SPMO. Publishing the SPMO line
without its window-matched SPY line would invite exactly that misreading, so both ship.

Run: python -m scripts.backtest_card [--check]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

OUT = os.path.join(ROOT, "data_export", "backtest_card.json")
RESULTS = os.path.join(ROOT, "BACKTEST_RESULTS.json")
SCHEMA = "backtest_card/1"

#: Invesco S&P 500 Momentum ETF listing date. A constant, not a guess: every figure on the
#: partial line is defined relative to it and it is reported on the card itself.
SPMO_INCEPTION = "2015-10-09"


def _panel_path() -> str:
    for root in (os.environ.get("VALQUO_DATA_ROOT"),
                 os.path.join(ROOT, "data"),
                 r"C:\Users\donni\Downloads\valuation-tool\data"):
        if not root:
            continue
        p = os.path.join(root, "free_analysis", "panel_corrected_69d.pkl")
        if os.path.exists(p):
            return p
    return ""


def build() -> dict:
    """Re-derive everything. Requires the banked panel and a network price fetch."""
    import pandas as pd
    from valuation.edge import fundamental_panel as FP
    from valuation.screener import prices as PR

    pub = json.load(open(RESULTS, encoding="utf-8"))
    rec = pub["cpcv"]["recommended_weights"]
    want = pub["costs"]["top_25"]

    panel = pd.read_pickle(_panel_path())
    cols = [c for c in rec if c in panel.columns]

    # C1 -- THE GATE. Nothing below is trustworthy unless the book reproduces the published
    # block exactly, because the whole card claims to describe that book.
    full = FP.turnover_and_costs(panel, cols, rec, top_n=25, horizon=63)
    for k in ("gross_ann", "net_ann", "cost_drag_ann", "annual_turnover"):
        if abs(float(full[k]) - float(want[k])) > 1e-12:
            raise SystemExit("C1 FAILED on %s: %r vs published %r -- refusing to publish a "
                             "card for a book that is not the one on record" % (k, full[k],
                                                                                want[k]))

    dates = sorted(panel["date"].astype(str).unique())
    part_dates = [d for d in dates if d >= SPMO_INCEPTION]
    lo, hi = part_dates[0], part_dates[-1]
    part = FP.turnover_and_costs(panel[panel["date"].astype(str) >= SPMO_INCEPTION].copy(),
                                 cols, rec, top_n=25, horizon=63)

    # The last scored window ENDS ~63 trading days after the last rebalance, so the ETFs are
    # measured to that end rather than to the last rebalance date -- otherwise the benchmark is
    # short by a quarter and every excess on this card is flattered.
    end = (dt.date.fromisoformat(hi) + dt.timedelta(days=95)).isoformat()

    def etf(ticker):
        df = PR.get_history_df(ticker, days=4200)
        if df is None or not len(df):
            return None, "no series returned"
        d = df.copy()
        d["Date"] = pd.to_datetime(d["Date"], utc=True).dt.tz_localize(None)
        w = d[(d["Date"] >= pd.Timestamp(lo))
              & (d["Date"] <= pd.Timestamp(end))].dropna(subset=["Close"])
        if len(w) < 100:
            return None, "only %d closes in the window" % len(w)
        yrs = (w["Date"].iloc[-1] - w["Date"].iloc[0]).days / 365.25
        # A window that does not actually START at the book's first date is not window-matched,
        # and a silently late start is how a 10y price cap nearly shipped as a real comparison.
        if (w["Date"].iloc[0] - pd.Timestamp(lo)).days > 10:
            return None, ("series starts %s, %d days after the book's window opens"
                          % (w["Date"].iloc[0].date(), (w["Date"].iloc[0]
                                                        - pd.Timestamp(lo)).days))
        return (float(w["Close"].iloc[-1] / w["Close"].iloc[0]) ** (1.0 / yrs) - 1.0,
                "%s..%s, %.2f yrs, %d closes, %s" % (w["Date"].iloc[0].date(),
                                                     w["Date"].iloc[-1].date(), yrs, len(w),
                                                     PR.source_of(df)))

    spmo, spmo_note = etf("SPMO")
    spy_p, spy_p_note = etf("SPY")

    card = {
        "schema": SCHEMA,
        "basis": "costs.top_25 in BACKTEST_RESULTS.json - the roth book (25 names, no band)",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "full": {
            "first_date": dates[0], "last_date": dates[-1], "n_periods": full["n_periods"],
            "gross_ann": full["gross_ann"], "net_ann": full["net_ann"],
            "cost_drag_ann": full["cost_drag_ann"],
            "realised_one_way_bps": full.get("realised_one_way_bps"),
            "spy_ann": pub["benchmarks"]["spy"]["benchmark_ann"],
            "vs_spy_gross": full["gross_ann"] - pub["benchmarks"]["spy"]["benchmark_ann"],
            "vs_spy_net": full["net_ann"] - pub["benchmarks"]["spy"]["benchmark_ann"],
        },
        "partial": {
            "since": SPMO_INCEPTION, "first_date": lo, "last_date": hi,
            "n_periods": part["n_periods"],
            "gross_ann": part["gross_ann"], "net_ann": part["net_ann"],
            "spmo_ann": spmo, "spmo_note": spmo_note,
            "spy_ann": spy_p, "spy_note": spy_p_note,
            "vs_spmo_gross": (None if spmo is None else part["gross_ann"] - spmo),
            "vs_spmo_net": (None if spmo is None else part["net_ann"] - spmo),
            "vs_spy_gross": (None if spy_p is None else part["gross_ann"] - spy_p),
            "vs_spy_net": (None if spy_p is None else part["net_ann"] - spy_p),
        },
    }
    body = json.dumps(card, sort_keys=True, separators=(",", ":")).encode("utf-8")
    card["sha256"] = hashlib.sha256(body).hexdigest()
    return card


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="rebuild and compare against the published file; write nothing")
    a = ap.parse_args()
    card = build()
    if a.check:
        old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
        drift = [k for k in ("full", "partial")
                 if json.dumps(old.get(k), sort_keys=True) != json.dumps(card[k],
                                                                        sort_keys=True)]
        print("DRIFT in %s" % drift if drift else "no drift")
        return 1 if drift else 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(card, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote %s" % OUT)
    for k in ("gross_ann", "net_ann", "vs_spy_gross", "vs_spy_net"):
        print("  full.%-14s %+.4f" % (k, card["full"][k]))
    for k in ("gross_ann", "net_ann", "vs_spy_gross", "vs_spmo_gross", "vs_spmo_net"):
        v = card["partial"][k]
        print("  partial.%-11s %s" % (k, ("%+.4f" % v) if v is not None else "unavailable"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
