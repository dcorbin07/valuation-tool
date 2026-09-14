"""Derive the backtested card's lines, PER BOOK CONFIG, and publish them for the service.

WHY THIS EXISTS RATHER THAN A LITERAL ON A PAGE. The card once printed a single unlabelled
"Alpha / yr" taken from `settings.BOOK_CONFIGS`, whose own comment records its `cost_drag_ann`
as a pre-B6 figure that was never re-measured. An alpha with no named benchmark is not a claim
anyone can check: on this project "alpha" has meant both "versus the equal-weighted universe"
(uninvestable, charged zero cost) and "versus SPY", and those differ by points a year.

**AND THE CARD WAS MIXING BOOKS, WHICH IS THE DEFECT THIS VERSION EXISTS TO FIX.** Version 1
published ONE book -- `costs.top_25`, the roth book -- while the page's Sharpe and turnover came
from whichever config the dropdown had selected. Choose "taxable" and the card showed the
top-25 book's gross return (32.1%) beside the decile's Sharpe on an AFTER-TAX basis (0.90) and
the decile's turnover: three different objects presented as one book. Every figure now comes
from one `turnover_and_costs`/`after_tax_backtest` pair per config, computed with the SAME
keyword construction `run_backtests` uses, and gated on reproducing that config's published
block before anything is written.

**TAXABLE NET IS NOT ROTH NET.** A tax-advantaged account pays costs and no tax; a taxable
account pays both, and on this book the tax drag is roughly three times the cost drag. So `net`
means `gross - costs` for roth and `gross - costs - taxes` for taxable, from the shipped
lot-level FIFO engine at 40.8% short / 23.8% long, and the card labels which it is rather than
printing one word over two different quantities.

**THE BENCHMARK MUST BE TAXED THE SAME WAY OR THE COMPARISON IS RIGGED.** Putting an after-tax
strategy beside an untaxed index would flatter the strategy by the whole of the index's tax
bill. In taxable mode SPY and SPMO are charged the qualified-dividend rate on their DIVIDENDS,
with capital gains treated as DEFERRED -- a buy-and-hold index fund realises almost nothing --
which is the honest asymmetry and is stated on the card rather than assumed. The dividend
component is MEASURED, by annualising the same series with and without dividend reinvestment,
not taken from a remembered yield.

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
SCHEMA = "backtest_card/2"

#: Invesco S&P 500 Momentum ETF listing date. Every figure on the partial line is defined
#: relative to it, and it is reported on the card itself.
SPMO_INCEPTION = "2015-10-09"

#: The shipped after-tax engine's own rates, IMPORTED at build time rather than retyped -- a
#: second copy of a tax rate is exactly how a card comes to describe a different calculation
#: from the one that produced its numbers.
QUALIFIED_DIVIDEND_RATE = 0.238          # long-term + NIIT; the rate a held index fund pays


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


def _cfg_kwargs(cfg: dict) -> dict:
    """EXACTLY `run_backtests`' construction, so the book measured here is the book published.

    Copied in shape rather than in spirit: the `if v` filter is what makes a None band absent
    rather than passed, and reproducing the published block depends on it.
    """
    return {k: v for k, v in (("top_n", cfg.get("top_n")),
                              ("top_frac", cfg.get("top_frac")),
                              ("exit_frac", cfg.get("exit_frac")),
                              ("exit_mult", cfg.get("exit_mult"))) if v}


def _etf_annualised(ticker, start, end):
    """(total_return_ann, price_only_ann, note) over exactly this window.

    Two fetches, because the DIFFERENCE is the dividend contribution and there is no other way
    to get it from a price series. `auto_adjust=True` reinvests dividends; `False` does not.
    yfinance is called directly here rather than through `screener.prices` because that module
    passes `auto_adjust=True` explicitly and deliberately -- inheriting a vendor default is a
    defect it names in its own comment -- so the unadjusted leg has no shipped accessor. This
    is a build-time script writing a static artifact, not a request path.
    """
    import pandas as pd
    import yfinance as yf

    def ann(adjust):
        h = yf.Ticker(ticker).history(period="max", auto_adjust=adjust)
        if h is None or h.empty:
            return None, 0
        d = pd.DataFrame({"Date": pd.to_datetime(h.index, utc=True).tz_localize(None),
                          "Close": h["Close"].values}).dropna()
        w = d[(d["Date"] >= pd.Timestamp(start)) & (d["Date"] <= pd.Timestamp(end))]
        if len(w) < 100:
            return None, len(w)
        yrs = (w["Date"].iloc[-1] - w["Date"].iloc[0]).days / 365.25
        return float(w["Close"].iloc[-1] / w["Close"].iloc[0]) ** (1.0 / yrs) - 1.0, len(w)

    tot, n = ann(True)
    pri, _ = ann(False)
    if tot is None or pri is None:
        return None, None, "insufficient closes (%d)" % n
    return tot, pri, "%s..%s, %d closes, total and price-only from yfinance" % (start, end, n)


def _after_tax_benchmark(total_ann, price_ann):
    """Charge the qualified-dividend rate on the DIVIDEND component only.

    Capital gains are treated as DEFERRED: a buy-and-hold index fund realises almost nothing,
    so taxing its appreciation annually would overstate its drag and flatter the strategy it is
    being compared against. That asymmetry is real and is stated on the card -- it is not a
    modelling convenience, it is what actually happens to someone holding SPY.

    An APPROXIMATION, and labelled as one: it charges the dividend tax as an annual drag rather
    than compounding it, which is within a basis point or two at these yields.
    """
    if total_ann is None or price_ann is None:
        return None, None
    div = max(0.0, total_ann - price_ann)
    return total_ann - div * QUALIFIED_DIVIDEND_RATE, div


def build() -> dict:
    import pandas as pd
    from valuation.edge import fundamental_panel as FP
    from valuation.screener import settings as S

    pub = json.load(open(RESULTS, encoding="utf-8"))
    rec = pub["cpcv"]["recommended_weights"]
    panel = pd.read_pickle(_panel_path())
    cols = [c for c in rec if c in panel.columns]

    dates = sorted(panel["date"].astype(str).unique())
    part = panel[panel["date"].astype(str) >= SPMO_INCEPTION].copy()
    pdates = [d for d in dates if d >= SPMO_INCEPTION]
    lo, hi = pdates[0], pdates[-1]
    end = (dt.date.fromisoformat(hi) + dt.timedelta(days=95)).isoformat()

    # Benchmarks, measured once. The FULL-window SPY level is the panel's own
    # `benchmarks.spy.benchmark_ann`; only its dividend SHARE comes from the price series.
    spy_full_t, spy_full_p, spy_full_note = _etf_annualised("SPY", dates[0], end)
    spy_part_t, spy_part_p, spy_part_note = _etf_annualised("SPY", lo, end)
    spmo_t, spmo_p, spmo_note = _etf_annualised("SPMO", lo, end)

    panel_spy = pub["benchmarks"]["spy"]["benchmark_ann"]
    # Apply the MEASURED dividend share to the PANEL's own SPY level, so the taxed and untaxed
    # benchmark are the same object with one deduction between them.
    spy_div_share = (max(0.0, spy_full_t - spy_full_p) / spy_full_t) if spy_full_t else 0.0
    panel_spy_at = panel_spy - panel_spy * spy_div_share * QUALIFIED_DIVIDEND_RATE

    books = {}
    for name, cfg in (S.BOOK_CONFIGS or {}).items():
        kw = _cfg_kwargs(cfg)
        c = FP.turnover_and_costs(panel, cols, rec, horizon=63, **kw) or {}
        t = FP.after_tax_backtest(panel, cols, rec, horizon=63, **kw) or {}

        # C1 -- THE GATE, per config. Nothing is written for a book that does not reproduce the
        # block already published for it. The card claims to describe that book; if it cannot
        # be identified, it has nothing to describe.
        want = (pub.get("book_configs") or {}).get(name) or {}
        for key, got in (("net_alpha", c.get("net_alpha")),
                         ("net_sharpe", c.get("net_sharpe")),
                         ("annual_turnover", c.get("annual_turnover")),
                         ("after_tax_alpha", t.get("after_tax_alpha")),
                         ("after_tax_sharpe", t.get("after_tax_sharpe"))):
            exp = want.get(key)
            if exp is None or got is None or abs(float(exp) - float(got)) > 1e-12:
                raise SystemExit("C1 FAILED for %s on %s: %r vs published %r"
                                 % (name, key, got, exp))

        taxable = bool(cfg.get("exit_frac") or cfg.get("top_frac")) and name == "taxable"
        gross = c["gross_ann"]
        net = (t["after_tax_ann"] if taxable else c["net_ann"])
        sharpe = (t["after_tax_sharpe"] if taxable else c["net_sharpe"])
        bench_full = (panel_spy_at if taxable else panel_spy)

        cp = FP.turnover_and_costs(part, cols, rec, horizon=63, **kw) or {}
        tp = FP.after_tax_backtest(part, cols, rec, horizon=63, **kw) or {}
        pgross = cp.get("gross_ann")
        pnet = (tp.get("after_tax_ann") if taxable else cp.get("net_ann"))

        spmo_b, spmo_div = ((_after_tax_benchmark(spmo_t, spmo_p)) if taxable
                            else (spmo_t, None))
        spy_p_b, _ = ((_after_tax_benchmark(spy_part_t, spy_part_p)) if taxable
                      else (spy_part_t, None))

        books[name] = {
            "label": cfg.get("label"),
            "mode": "taxable" if taxable else "tax_advantaged",
            "net_means": ("after costs and taxes" if taxable else "after costs"),
            "basis": ("recomputed from the banked panel with this config's own "
                      "top_n/top_frac/exit_frac/exit_mult, gated on reproducing "
                      "BACKTEST_RESULTS.json book_configs.%s" % name),
            "benchmark_basis": ("SPY and SPMO charged the %.1f%% qualified-dividend rate on "
                                "their dividends, capital gains treated as deferred"
                                % (QUALIFIED_DIVIDEND_RATE * 100) if taxable
                                else "SPY and SPMO at total return, untaxed - correct for a "
                                     "tax-advantaged account, which pays no tax either"),
            "full": {
                "first_date": dates[0], "last_date": dates[-1],
                "n_periods": c.get("n_periods"),
                "gross_ann": gross, "net_ann": net,
                "cost_drag_ann": c.get("cost_drag_ann"),
                "tax_drag_ann": (c["net_ann"] - t["after_tax_ann"]) if taxable else None,
                "sharpe": sharpe, "annual_turnover": c.get("annual_turnover"),
                # The equal-weight level THIS BOOK's own scorer used. Stored because the
                # results file carries TWO different equal-weight annual returns -- 0.17239
                # from `turnover_and_costs`/`after_tax_backtest` and 0.18137 from
                # `benchmark_panel` -- both correct for their own construction. An identity
                # check that reaches for the wrong one fails while every number involved is
                # right, which is a confusing way to spend an afternoon.
                "equal_weight_ann": c.get("equal_weight_ann"),
                "spy_ann": bench_full, "spy_untaxed_ann": panel_spy,
                "vs_spy_gross": gross - bench_full,
                "vs_spy_net": net - bench_full,
            },
            "partial": {
                "since": SPMO_INCEPTION, "first_date": lo, "last_date": hi,
                "n_periods": cp.get("n_periods"),
                "gross_ann": pgross, "net_ann": pnet,
                "spmo_ann": spmo_b, "spmo_note": spmo_note,
                "spy_ann": spy_p_b, "spy_note": spy_part_note,
                "vs_spmo_gross": (None if spmo_b is None or pgross is None
                                  else pgross - spmo_b),
                "vs_spmo_net": (None if spmo_b is None or pnet is None else pnet - spmo_b),
                "vs_spy_gross": (None if spy_p_b is None or pgross is None
                                 else pgross - spy_p_b),
                "vs_spy_net": (None if spy_p_b is None or pnet is None else pnet - spy_p_b),
            },
        }

        # THE BAND, stated honestly. `settings` carries `measured_width` because when the width
        # moved to 0.30 no run had measured it there. One has since: the results file's own git
        # commit has the 0.30 adoption as an ancestor, and these figures are recomputed at the
        # LIVE width regardless -- so the card reports both and says whether they agree.
        live_w = cfg.get("exit_frac")
        if live_w:
            books[name]["band"] = {
                "live_width": live_w,
                "settings_measured_width": cfg.get("measured_width"),
                "figures_measured_at": live_w,
                "stale_settings_note": (
                    "settings.BOOK_CONFIGS carries measured_width %s, from before the width "
                    "moved to %s; the figures on this card are recomputed AT %s and do not "
                    "inherit it" % (cfg.get("measured_width"), live_w, live_w)
                    if cfg.get("measured_width") and abs(float(cfg["measured_width"])
                                                         - float(live_w)) > 1e-9 else ""),
            }

    card = {"schema": SCHEMA,
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "qualified_dividend_rate": QUALIFIED_DIVIDEND_RATE,
            "spy_dividend_share_of_total_return": spy_div_share,
            "spy_full_note": spy_full_note,
            "books": books}
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
        drift = json.dumps(old.get("books"), sort_keys=True) != json.dumps(card["books"],
                                                                          sort_keys=True)
        print("DRIFT" if drift else "no drift")
        return 1 if drift else 0
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(card, f, indent=2, sort_keys=True)
        f.write("\n")
    print("wrote %s" % OUT)
    for nm, b in sorted(card["books"].items()):
        f_, p_ = b["full"], b["partial"]
        print("  %-8s [%s] gross %+.4f  net %+.4f (%s)  sharpe %.3f  turn %.2fx"
              % (nm, b["mode"], f_["gross_ann"], f_["net_ann"], b["net_means"],
                 f_["sharpe"], f_["annual_turnover"]))
        print("           vs SPY %+.4f/%+.4f   vs SPMO %s/%s"
              % (f_["vs_spy_gross"], f_["vs_spy_net"],
                 ("%+.4f" % p_["vs_spmo_gross"]) if p_["vs_spmo_gross"] is not None else "n/a",
                 ("%+.4f" % p_["vs_spmo_net"]) if p_["vs_spmo_net"] is not None else "n/a"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
