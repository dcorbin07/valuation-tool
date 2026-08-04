"""
run_backtest.py — does the screener's composite predict forward returns?

Builds a point-in-time panel from FREE data (EDGAR fundamentals + yfinance
prices) and runs the edge backtest on it.

    pip install -r requirements.txt
    cp .env.example .env        # only EDGAR_USER_AGENT is needed for the backtest
    python run_backtest.py --model both

NO Discord. NO Opus/AI calls. NO cost. It prints one report to the console.

-----------------------------------------------------------------------------
 C1 (Jul 2026): this script now backtests THE MODEL THAT SHIPS.
-----------------------------------------------------------------------------
It used to define its own six-factor model inline —

    WEIGHTS = {"ey_sn": .30, "roe": .10, "opm": .10, "neg_lev": .10,
               "mom": .20, "growth": .20}

— and never import `scoring.py` at all. No bucket split, no gates, no insider
component, and `ey_sn` (sector-demeaned earnings yield) does not exist in the
live model in any form. So the screener backtest did not measure the screener:
whatever it reported was a property of a model nobody ships, and the insider
component — 20-30% of the live weight — had never been backtested in any form.

Both models now run against ONE panel:

    --model live     `scoring.score_stock` — bucket split, gates, value
                     percentiles, insider, the $10B ceiling. What ships.
    --model legacy   the old inline composite. Kept ONLY so the size of the
                     defect is a measured number rather than an assertion.
    --model both     runs each and prints them side by side. Default.

-----------------------------------------------------------------------------
 C2 (Jul 2026): the universe was the exact inverse of the target.
-----------------------------------------------------------------------------
The universe was `edgar.all_filers().keys()[:300]`. EDGAR's company_tickers.json
is ordered by market capitalisation DESCENDING — verified, not assumed: entries
1-10 are NVDA, AAPL, GOOGL, MSFT, AMZN, AVGO, META, TSLA, MU, BRK-B, and entries
290-300 are NKE, O, MET, CTVA, COR, OKE, TEL, GWLIF, MPLX, FANG. The screener's
stated target is sub-$10B names. Not one of those 300 is within an order of
magnitude of the ceiling, so the intersection between what was tested and what
is traded was EMPTY — and the equity programme's own regime split shows large
and small caps behaving least alike of any two tiers.

`--universe target` (default) draws a band from further down the same cap-ordered
list and then applies the screener's OWN gates AS OF EACH REBALANCE DATE:
market cap <= config.MARKET_CAP_CEILING, price >= config.PRICE_FLOOR, average
dollar volume >= config.MIN_AVG_DOLLAR_VOLUME. The cap gate is genuinely
point-in-time — it uses shares outstanding known on that date times the close on
that date, not today's cap.

`--universe legacy` reproduces the old broken universe for comparison.

WHAT IS STILL BIASED, AND BY HOW MUCH WE CANNOT SAY FROM HERE
-------------------------------------------------------------
The candidate POOL is still drawn from today's EDGAR filer list, so any company
that delisted over the window is structurally absent and the panel remains
survivorship-biased. The point-in-time cap gate fixes the LOOK-AHEAD SELECTION
(we no longer pick names using a cap we could not have known); it does not and
cannot fix survivorship on a free feed. `core/pit_universe.py` fixes that
properly from a Sharadar mirror and is audit item C5 — which is a different
lane. Until C5 runs, read every number here as an upper bound.
"""
import argparse
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
import numpy as np
import pandas as pd

load_dotenv()
import config as C
import edgar
import scoring as S
import cross_sectional as X
import backtest_engine as B
import pit_data
import panel_cache as PC

# ---------------- CONFIG ----------------
START, END    = "2021-01-01", "2025-06-01"   # rebalance window (needs ~1y of prior price + forward window)
REBALANCE     = "MS"                          # monthly (month start)
HORIZON_TD    = 21                            # 1-month holding = matches monthly rebalance (no overlap)
COST_BPS      = 8.0                           # per-side cost; small-caps are wide, be honest
BENCH         = "IWM"
# The legacy inline model, preserved verbatim as the thing C1 is replacing.
LEGACY_WEIGHTS = {"ey_sn": 0.30, "roe": 0.10, "opm": 0.10,
                  "neg_lev": 0.10, "mom": 0.20, "growth": 0.20}
LEGACY_FACTORS = ["ey_sn", "roe", "opm", "neg_lev", "mom", "growth"]
# Candidate band into EDGAR's cap-descending filer list for `--universe target`.
# Ranks 1-300 are the megacaps the old universe used. Names in this band are
# mostly $1B-$30B today, which is the right catchment for a sub-$10B screen once
# the point-in-time cap gate has run.
TARGET_BAND = (500, 2000)
LEGACY_LIMIT = 300
# ----------------------------------------


def _rebalance_dates(start, end):
    return list(pd.date_range(start, end, freq=REBALANCE))


# ---------------------------------------------------------------------------
#  Universe
# ---------------------------------------------------------------------------

def universe(kind, band=TARGET_BAND, limit=LEGACY_LIMIT):
    """
    Candidate tickers BEFORE the point-in-time gates.

    `legacy` is the defect: the 300 largest US filers, applied to a sub-$10B
    strategy. `target` is a band from further down the same list; the actual
    sub-$10B selection happens per-date in `apply_live_gates`, on a cap we could
    have known at the time.
    """
    allf = list(edgar.all_filers().keys())
    if kind == "legacy":
        return allf[:limit]
    lo, hi = band
    return allf[lo:hi]


def apply_live_gates(panel):
    """
    The screener's own eligibility rules, AS OF EACH ROW'S DATE.

    Deliberately uses `config` rather than re-stating the numbers, so a change
    to the live ceiling or liquidity floor moves the backtest with it. Returns
    (filtered_panel, per-reason counts).

    ONE DELIBERATE SIMPLIFICATION, stated so it is not mistaken for an oversight:
    the live pipeline applies the $10B ceiling through `market_cap_eligible`,
    which lets a name through anyway if it ranks in the top `OVERRIDE_TOP_RANK`
    (3) of its bucket or shows an insider cluster. That override is applied
    AFTER ranking, so reproducing it here would make universe membership depend
    on the score — and then the two models would be scored on two different
    universes, which is the one thing C1 exists to prevent. The ceiling is
    applied as a hard gate instead. Effect: a handful of megacap names the live
    product would occasionally surface are absent from both models' panels.
    """
    n0 = len(panel)
    junk = panel["ticker"].map(S.is_junk_ticker)
    reasons = {"junk_ticker": int(junk.sum())}
    p = panel[~junk]

    not_common = ~p["is_common_equity"].fillna(True).astype(bool)
    reasons["not_common_equity"] = int(not_common.sum())
    p = p[~not_common]

    cheap = p["price"].fillna(0) < C.PRICE_FLOOR
    reasons[f"price_below_{C.PRICE_FLOOR:g}"] = int(cheap.sum())
    p = p[~cheap]

    illiquid = p["avg_dollar_volume"].fillna(0) < C.MIN_AVG_DOLLAR_VOLUME
    reasons["below_liquidity_floor"] = int(illiquid.sum())
    p = p[~illiquid]

    # The point-in-time cap gate. A name is in the universe on a date if the cap
    # KNOWN ON THAT DATE was under the ceiling — not if today's cap is.
    no_cap = p["market_cap"].isna()
    reasons["no_market_cap"] = int(no_cap.sum())
    p = p[~no_cap]
    too_big = p["market_cap"] > C.MARKET_CAP_CEILING
    reasons[f"above_{C.MARKET_CAP_CEILING/1e9:g}B_ceiling"] = int(too_big.sum())
    p = p[~too_big]

    reasons["kept"] = len(p)
    reasons["from"] = n0
    return p.reset_index(drop=True), reasons


# ---------------------------------------------------------------------------
#  Scoring — one panel, two models
# ---------------------------------------------------------------------------

def score_legacy(panel):
    """The old inline composite. Sector-demeaned value, then a weighted z-score."""
    parts = []
    for _, g in panel.groupby("date"):
        g = g.copy()
        g["ey_sn"] = g.groupby("sector")["ey"].transform(lambda s: s - s.mean())
        g["composite_legacy"] = X.composite_score(g, LEGACY_WEIGHTS)
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


_LIVE_FIELDS = ("ticker", "sector", "price", "avg_dollar_volume", "market_cap",
                "revenue", "net_income", "operating_income", "total_debt",
                "cash", "op_margin", "roe", "net_debt_to_ebitda",
                "latest_rev_growth", "prior_rev_growth", "ret_12_1",
                "is_common_equity")


def _denan(row):
    """
    NaN -> None on the way from the panel into the live scorer.

    THIS IS LOAD-BEARING, and it is the same defect class that has bitten this
    project four times. `pit_data` correctly returns None for a missing input,
    but the moment those values pass through a DataFrame pandas stores them as
    float NaN, and `to_dict("records")` hands NaN back. Every missing-data
    branch in `scoring.py` tests `is None`, so a NaN sails through as PRESENT:

        quality_score(op_margin=nan, ...) -> _clip01(nan/0.25) -> nan
        -> _weighted() counts it as present -> quality = nan
        -> the whole composite = nan -> the name is DROPPED

    So one missing input deleted a name from the book instead of renormalizing
    the remaining weights onto what was there — and it did it without raising,
    without appearing in the coverage tally (which only counts names that
    reached the `sc is None` branch), and while looking exactly like a name that
    simply failed a gate. Measured on a 60-name slice: 89 unscored rows, of
    which the skip counter saw 19 and this silently ate the other 70.

    Reasoning about it the other way round is what makes it obvious: an
    all-NaN-tolerant scorer is impossible here BY DESIGN, because `insider_score`
    has to tell `None` ("not fetched", renormalize away) apart from `[]`
    ("fetched, nothing there", a real neutral 50). A convention that fine cannot
    survive a silent None->NaN coercion in the transport layer.
    """
    out = {}
    for k, v in row.items():
        out[k] = None if (isinstance(v, float) and v != v) else v
    return out


def score_live(panel, with_insider=True, insider_limit=6):
    """
    Score every cross-section with `scoring.score_stock` — the deployed model.

    Runs the real sequence: `compute_value_percentiles` over the whole
    cross-section (value is relative, so it cannot be computed per name), then
    `score_stock` per name, which classifies the bucket, applies the gates and
    renormalizes the bucket weights over whatever inputs are present.

    with_insider=False passes `insider_transactions=None`, which
    `scoring.insider_score` treats as "not fetched" and renormalizes away. That
    is the live model MINUS its insider component — a legitimate measurement,
    but it is NOT the live model and is labelled as such everywhere it appears.
    """
    out, skips = [], {}
    for _, g in panel.groupby("date"):
        rows = [_denan(r) for r in g[list(_LIVE_FIELDS)].to_dict("records")]
        for r, (_, src) in zip(rows, g.iterrows()):
            r["insider_transactions"] = (
                PC.insider_asof(r["ticker"], src["date"], insider_limit)
                if with_insider else None)
        S.compute_value_percentiles(rows)
        comps, buckets, covs = [], [], []
        for r in rows:
            sc, why = S.score_stock_verbose(r)
            if sc is None:
                # Bucket the reason, don't key on the raw string: the coverage
                # message embeds a per-row percentage, so keying on it would
                # produce one dict entry per row instead of a tally.
                key = ("insufficient factor coverage"
                       if why.startswith("insufficient factor coverage") else why)
                skips[key] = skips.get(key, 0) + 1
                comps.append(np.nan); buckets.append(None); covs.append(np.nan)
            else:
                comps.append(sc.composite); buckets.append(sc.bucket); covs.append(sc.coverage)
        g = g.copy()
        g["composite_live"] = comps
        g["bucket"] = buckets
        g["live_coverage"] = covs
        out.append(g)
    return pd.concat(out, ignore_index=True), skips


# ---------------------------------------------------------------------------
#  Reporting
# ---------------------------------------------------------------------------

def _report(label, panel, score_col, factor_cols):
    scored = panel.dropna(subset=[score_col])
    if scored.empty:
        print(f"\n### {label}: no scored rows.")
        return None
    res = B.summarize(scored, score_col=score_col, factor_cols=factor_cols,
                      cost_bps=COST_BPS, q=5)
    print("\n" + "=" * 72)
    print(f"### {label}   ({len(scored):,} scored rows, "
          f"{scored['ticker'].nunique():,} names, {scored['date'].nunique()} dates)")
    print("=" * 72)
    B.print_report(res)
    return res


def _universe_profile(panel, label):
    caps = panel.groupby("ticker")["market_cap"].median().dropna()
    if caps.empty:
        print(f"{label}: no market caps.")
        return
    under = (caps <= C.MARKET_CAP_CEILING).mean() * 100
    print(f"{label}: {len(caps):,} names | median cap ${caps.median()/1e9:,.2f}B | "
          f"p25 ${caps.quantile(.25)/1e9:,.2f}B  p75 ${caps.quantile(.75)/1e9:,.2f}B | "
          f"{under:.1f}% at or under the ${C.MARKET_CAP_CEILING/1e9:g}B ceiling")


def main():
    ap = argparse.ArgumentParser(description="Screener edge backtest (C1 + C2).")
    ap.add_argument("--model", default="both", choices=["live", "legacy", "both"])
    ap.add_argument("--universe", default="target", choices=["target", "legacy"])
    ap.add_argument("--start", default=START)
    ap.add_argument("--end", default=END)
    ap.add_argument("--band", type=int, nargs=2, default=list(TARGET_BAND),
                    help="Rank band into EDGAR's cap-descending filer list.")
    ap.add_argument("--no-gates", action="store_true",
                    help="Skip the point-in-time eligibility gates (diagnostic only).")
    ap.add_argument("--no-insider", action="store_true",
                    help="Score the live model WITHOUT its insider component. "
                         "Much faster; not the live model.")
    ap.add_argument("--prefetch-only", action="store_true",
                    help="Populate the on-disk cache and exit.")
    args = ap.parse_args()

    if not os.environ.get("EDGAR_USER_AGENT"):
        print("!! Set EDGAR_USER_AGENT in .env (e.g. 'Your Name you@email.com') — EDGAR requires it.")
        return 1

    dates = _rebalance_dates(args.start, args.end)
    tickers = universe(args.universe, tuple(args.band))
    print(f"Universe: {args.universe} ({len(tickers)} candidates) | "
          f"rebalance {args.start}..{args.end} ({REBALANCE}, {len(dates)} dates) | "
          f"horizon {HORIZON_TD}td | model {args.model}")

    # ---- 1. prices (bulk; fast) ----
    px_start = (pd.Timestamp(args.start) - pd.Timedelta(days=520)).strftime("%Y-%m-%d")
    px_end = (pd.Timestamp(args.end) + pd.Timedelta(days=120)).strftime("%Y-%m-%d")
    print(f"Fetching prices {px_start}..{px_end} (cached)...", flush=True)
    PC.bulk_prices(tickers + [BENCH], px_start, px_end)
    bench_px = PC.prices(BENCH)
    if bench_px is None:
        print("!! Could not load benchmark prices."); return 1
    priced = [t for t in tickers if PC.prices(t) is not None]
    print(f"  priceable: {len(priced)}/{len(tickers)}")

    # ---- 2. fundamentals + filer metadata (EDGAR; the slow part, cached) ----
    print("Fetching EDGAR companyfacts + SIC (cached; first run is slow)...", flush=True)
    sectors, common = {}, {}
    have_facts = []
    for i, t in enumerate(priced, 1):
        if PC.companyfacts(t) is None:
            continue
        have_facts.append(t)
        sectors[t], common[t] = PC.sector_and_common(t)
        if i % 100 == 0:
            print(f"  {i}/{len(priced)} filers, {len(have_facts)} with XBRL", flush=True)
    print(f"  usable filers: {len(have_facts)}")

    want_insider = (args.model in ("live", "both")) and not args.no_insider

    if args.prefetch_only and not want_insider:
        print("Fundamentals cache populated; exiting (--prefetch-only).")
        return 0

    # ---- 3. panel ----
    print("Building the point-in-time panel...", flush=True)
    panel = pit_data.build_panel(
        have_facts, dates,
        get_facts=PC.companyfacts, get_prices=PC.prices,
        bench_prices=bench_px, horizon_td=HORIZON_TD,
        sectors=sectors, is_common_equity=common)
    if panel.empty:
        print("!! Empty panel."); return 1
    print(f"Panel: {len(panel):,} rows, {panel['date'].nunique()} dates, "
          f"{panel['ticker'].nunique():,} names.")
    _universe_profile(panel, "  BEFORE gates")

    if not args.no_gates:
        panel, reasons = apply_live_gates(panel)
        print("  gate rejections: " + ", ".join(f"{k}={v:,}" for k, v in reasons.items()))
        if panel.empty:
            print("!! Every row was gated out."); return 1
        _universe_profile(panel, "  AFTER gates ")

    # ---- 4. insider Form 4 history (the slowest step) ----
    # Deliberately AFTER the gates. The gates remove most of the candidate band —
    # a name the screener would never rank does not need four years of Form 4
    # history pulled one document at a time at EDGAR's rate limit.
    if want_insider:
        need = sorted(panel["ticker"].unique())
        print(f"Fetching point-in-time Form 4 history for the {len(need)} names "
              f"that survive the gates (cached; the slowest step)...", flush=True)
        PC.prefetch_insider(need, sorted(panel["date"].unique()))
        if args.prefetch_only:
            print("Cache populated; exiting (--prefetch-only).")
            return 0

    # ---- 5. score + report ----
    results = {}
    if args.model in ("legacy", "both"):
        panel = score_legacy(panel)
        results["legacy"] = _report(
            "LEGACY inline model (ey_sn/roe/opm/neg_lev/mom/growth) — NOT what ships",
            panel, "composite_legacy", LEGACY_FACTORS)
    if args.model in ("live", "both"):
        panel, skips = score_live(panel, with_insider=want_insider)
        tag = "LIVE model (scoring.score_stock) — what ships" if want_insider else \
              "LIVE model MINUS the insider component — NOT the live model"
        results["live"] = _report(tag, panel, "composite_live", LEGACY_FACTORS)
        if skips:
            print("  live-model skips: " + ", ".join(f"{k}={v:,}" for k, v in
                                                     sorted(skips.items(), key=lambda kv: -kv[1])))
        sc = panel.dropna(subset=["composite_live"])
        if len(sc):
            print("  bucket mix: " + ", ".join(
                f"{k}={v:,}" for k, v in sc["bucket"].value_counts().items()))

    print("\n" + "=" * 72)
    print("DO NOT QUOTE cum_port / cum_bench. HORIZON_TD=21 was chosen because")
    print("'1-month holding = matches monthly rebalance (no overlap)' — but calendar")
    print("months are not uniformly 21 sessions, so windows anchored at month starts")
    print("do not tile: some leave a gap, some overlap. Measured on IWM over this")
    print("window, buy-and-hold is +4.6% while the compounded 21-session windows give")
    print("-4.5% — a 9pp artefact. It hits both models identically and cancels out of")
    print("IC and of the quantile spread (both computed WITHIN a date), so the C1")
    print("comparison is unaffected; only the cumulative figures are distorted.")
    print("=" * 72)
    print("SURVIVORSHIP CAVEAT: the candidate pool is today's EDGAR filer list, so")
    print("names that delisted over the window are structurally absent and every")
    print("number above is biased optimistic. The point-in-time cap gate removes the")
    print("LOOK-AHEAD selection, not survivorship. Audit item C5 (Sharadar mirror)")
    print("is the only thing that fixes the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
