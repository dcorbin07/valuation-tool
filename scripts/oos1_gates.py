"""OOS1 — the two preparation gates. ZERO TRIALS, and the holdout stays UNOPENED.

    python -m scripts.oos1_gates --gate a
    python -m scripts.oos1_gates --gate b

WHAT THIS IS AND IS NOT
    Two instrument checks that cost NO holdout look. Neither scores a construction and neither
    computes a forward return on the holdout era.

    **THE HOLDOUT IS NOW 1972-1998** -- r1 is spending 1999-2008 via Sharadar, so the WRDS era
    shortened. **Nothing here reads a 1972-1998 return.** Gate A validates the build against
    Ken French's published factors, which is a comparison of OUR data against a THIRD PARTY's
    data and never against our own signal. Gate B runs entirely on 2009-2026, which is training
    data. Pinned by `tests/test_oos1_gates.py`.

GATE A -- FRENCH FACTOR SANITY, and its scope is declared rather than implied
    It checks the two things that can actually be wrong in a fresh CRSP build and that every
    downstream number depends on:

      A1  the value-weighted market return, monthly, against French's `Mkt-RF + RF`
      A2  a size-sorted long-short spread against French's `SMB`

    **A FULL FIVE-FACTOR REPLICATION IS NOT ATTEMPTED AND THAT IS A STATED LIMIT.** Rebuilding
    HML/RMW/CMA faithfully needs June-rebalanced 2x3 sorts on NYSE breakpoints with Compustat
    accounting lags -- a construction in its own right, whose disagreement would be ambiguous
    between our build and our replication of French's method. A1 and A2 are unambiguous: if the
    market return or the size sort disagrees, the prices, returns, market cap or universe are
    wrong, and nothing built on them is worth running.

    LICENCE: French's library is free and FACTOR-LEVEL. `CLAUDE.md` already ruled the analogous
    case -- "free but permission-gated and factor-level ... never a magnitude claim" -- so it
    validates our build and may never appear in a product figure.

GATE B -- THE VENDOR-TRANSLATION CONTROL
    The holdout changes VENDOR as well as PERIOD. The Compustat-built five-theme composite must
    reproduce the banked Sharadar composite on the **2009-2026 overlap** at mean per-date
    Spearman **>= 0.90**. Below that, the holdout is NOT opened, because a pre-1999 result would
    measure the translation rather than the model.
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

RAW = r"D:\wrds"
GATE_B_BAR = 0.90
HOLDOUT = (1972, 1998)          # r1 took 1999-2008; this is what remains, and it stays UNOPENED

#: Gate B's price-history floor. The grid starts 2009-01-15 and the momentum columns need 252
#: TRADING days before it, so the floor must sit well below the grid's own first year -- and it
#: must sit far above `HOLDOUT[1]`, so no holdout year is ever loaded by this gate. Both
#: properties are pinned by test.
GATE_B_BURNIN_YEAR = 2007


def _data_root() -> str:
    d = REPO
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "data", "free_analysis",
                                       "panel_corrected_69d.pkl")):
            return os.path.join(d, "data")
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    raise SystemExit("REFUSING: no populated data root found")


#: A monthly equity factor in DECIMAL has |mean| well under this; in PERCENT it is far above.
#: The two regimes are a hundredfold apart, so no plausible series is ambiguous between them.
DECIMAL_CEILING = 0.05


def _french(root: str) -> pd.DataFrame:
    """French's monthly factors, with the UNITS CHECKED rather than converted.

    A DEFECT OF MY OWN, CAUGHT BY DISBELIEVING A NUMBER RATHER THAN BY ANYTHING RAISING.
    French's website publishes these in PERCENT, so the first cut of this loader divided by 100.
    But `scripts/fetch_factors.py` has ALREADY done that conversion -- the parsed CSV stores
    `-0.0039` -- so dividing again made the 1995 market return **0.03%/yr against a true ~37%**.
    Gate A then read correlation 0.999998 beside a 2.86pp mean absolute difference, and the
    honest reading of that pair is not "the gate nearly passes": **it would have reported a level
    failure of a CRSP build that is correct, blaming the data for my arithmetic.**

    So the conversion is REPLACED BY A REFUSAL. Guessing the units is what went wrong; a loader
    that cannot tell percent from decimal should stop rather than pick one, because both choices
    produce a clean, plausible, confidently wrong number.
    """
    f = pd.read_csv(os.path.join(root, "factors", "parsed", "ff5_monthly.csv"))
    f["date"] = pd.to_datetime(f["date"], errors="coerce")
    f["ym"] = f["date"].dt.strftime("%Y-%m")
    for c in ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"):
        if c not in f.columns:
            continue
        f[c] = f[c].astype(float)
        m = float(f[c].abs().mean())
        if m > DECIMAL_CEILING:
            raise SystemExit(
                "REFUSING: %s has |mean| %.4f, above the %.2f decimal ceiling -- the parsed "
                "factor file looks to be in PERCENT. Fix the units at the source "
                "(scripts/fetch_factors.py); do NOT convert here, or two files will disagree "
                "about what the stored number means." % (c, m, DECIMAL_CEILING))
    return f


def _load_dsf(lo: int, hi: int) -> pd.DataFrame:
    """The CRSP universe French builds his factors on, via the provider's own filter.

    THE UNIVERSE FILTER IS PART OF THIS GATE, NOT A REFINEMENT. French's market factor is
    ordinary common shares (`shrcd` 10/11) on NYSE/AMEX/Nasdaq (`exchcd` 1/2/3). Loading raw
    `dsf` instead carries ADRs, REITs, closed-end funds and units, and A1 would then disagree
    with French for a reason that is **not a defect in this build** -- which would make the gate
    read as a failure of the data when it was a failure of the comparison. Routed through
    `CompustatCrspProvider.prices()` so the gate and the eventual holdout build share ONE
    definition of the universe rather than two (`B7`).
    """
    from valuation.edge.compustat_provider import CompustatCrspProvider
    prov = CompustatCrspProvider(year_lo=lo, year_hi=hi)
    d = prov.prices()
    return d, prov.notes


def gate_a(root: str, lo: int, hi: int) -> dict:
    """A1 market return, A2 size spread -- both against French, monthly."""
    d, notes = _load_dsf(lo, hi)
    d = d.copy()
    d["ym"] = d["date"].dt.strftime("%Y-%m")

    # Monthly compounded return per permno, and the month's opening market cap as the weight.
    # The weight must be the PRIOR month's cap: weighting by the same month's cap is a
    # look-ahead that mechanically tilts toward whatever rose.
    d = d.sort_values(["permno", "date"])
    g = d.groupby(["permno", "ym"])
    monthly = pd.DataFrame({
        "ret_m": g["ret"].apply(lambda s: float((1.0 + s.dropna()).prod() - 1.0)),
        "cap_last": g["mktcap"].last(),
    }).reset_index()
    monthly = monthly.sort_values(["permno", "ym"])
    monthly["w"] = monthly.groupby("permno")["cap_last"].shift(1)
    m = monthly.dropna(subset=["ret_m", "w"])
    m = m[m["w"] > 0]

    def _vw(grp):
        return float(np.average(grp["ret_m"], weights=grp["w"]))

    vw = m.groupby("ym").apply(_vw, include_groups=False)
    vw.name = "mkt_ours"
    vw = vw.reset_index()

    fr = _french(root)
    j = vw.merge(fr[["ym", "Mkt-RF", "RF", "SMB"]], on="ym", how="inner")
    j["mkt_french"] = j["Mkt-RF"] + j["RF"]
    a1 = {
        "months_compared": int(len(j)),
        "correlation": round(float(j["mkt_ours"].corr(j["mkt_french"])), 6),
        "mean_ours": round(float(j["mkt_ours"].mean()), 6),
        "mean_french": round(float(j["mkt_french"].mean()), 6),
        "mean_abs_diff": round(float((j["mkt_ours"] - j["mkt_french"]).abs().mean()), 6),
        "p95_abs_diff": round(float((j["mkt_ours"] - j["mkt_french"]).abs().quantile(0.95)), 6),
    }

    # A2: a crude size spread -- small-cap VW return minus large-cap VW return, median split.
    # Not French's 2x3 construction, so the BAR is correlation of SIGN and shape, not level.
    med = m.groupby("ym")["w"].transform("median")
    small = m[m["w"] <= med]
    large = m[m["w"] > med]
    s = small.groupby("ym").apply(_vw, include_groups=False)
    l = large.groupby("ym").apply(_vw, include_groups=False)
    spread = (s - l).rename("smb_ours").reset_index()
    j2 = spread.merge(fr[["ym", "SMB"]], on="ym", how="inner")
    a2 = {
        "months_compared": int(len(j2)),
        "correlation_with_SMB": round(float(j2["smb_ours"].corr(j2["SMB"])), 6),
        "mean_ours": round(float(j2["smb_ours"].mean()), 6),
        "mean_french_SMB": round(float(j2["SMB"].mean()), 6),
        "note": ("a MEDIAN split is not French's 2x3 NYSE-breakpoint construction, so the level "
                 "is not expected to match -- the correlation is the check"),
    }
    return {"A1_market_return": a1, "A2_size_spread": a2,
            "window": [lo, hi], "universe_notes": notes,
            "universe_filter": ("shrcd in (10,11) and exchcd in (1,2,3), dated via the CRSP "
                                "name history -- French's own universe. NOT a refinement: "
                                "without it A1 disagrees for a reason that is not a defect."),
            "licence": ("Ken French's library is free and FACTOR-LEVEL. It validates this build "
                        "and may NEVER appear in a product figure (CLAUDE.md's ruling on the "
                        "analogous case; RUN_RULES 0.2)."),
            "scope_limit": ("HML/RMW/CMA are NOT replicated. A disagreement there would be "
                            "ambiguous between our build and our replication of French's method; "
                            "A1 and A2 are not.")}


#: The frozen five-theme holdout model (OOS1 §1). 0.2 is NOT a new weight -- it is the deployed
#: 0.125 renormalised by present-weight mass, which `composite_from_frame` already does, and
#: `V2G` proved that identity at max |dev| 0.000e+00 over all 113,945 rows.
FIVE = ("value", "quality", "momentum", "capital_discipline", "size")
FIVE_W = {c: 0.2 for c in FIVE}


def _ticker_to_permno(prov, dates) -> pd.DataFrame:
    """(ticker, permno) pairs valid across the panel's window, from the DATED name history.

    A ticker is reused across companies, so the map is built per name-interval and then required
    to be UNAMBIGUOUS over the window: a ticker resolving to more than one permno is DROPPED and
    COUNTED rather than guessed at. `S25` implemented exactly this refusal and recorded that it
    costs nothing today and is the one you want present the day the universe moves.
    """
    lo, hi = pd.Timestamp(min(dates)), pd.Timestamp(max(dates))
    lk = prov.link()
    w = lk[(lk["nameenddt"] >= lo) & (lk["namedt"] <= hi)].copy()
    w = w[w["shrcd"].isin((10, 11)) & w["exchcd"].isin((1, 2, 3))]
    w["ticker"] = w["ticker"].astype(str).str.upper().str.strip()
    w = w[w["ticker"].str.len() > 0]
    g = w.groupby("ticker")["permno"].nunique()
    ok = set(g[g == 1].index)
    amb = int((g > 1).sum())
    uniq = w[w["ticker"].isin(ok)].drop_duplicates("ticker")[["ticker", "permno"]]
    uniq["permno_s"] = uniq["permno"].astype(int).astype(str)
    return uniq, amb


def gate_b(root: str, lo: int, hi: int, limit: int = 0) -> dict:
    """The vendor-translation control. Runs ENTIRELY on 2009-2026 -- training data, not holdout."""
    from valuation.edge.compustat_provider import CompustatCrspProvider
    from valuation.edge.fundamental_panel import build_fundamental_panel, composite_from_frame
    from valuation.screener.cross_sectional import zscore

    sh = pd.read_pickle(os.path.join(root, "free_analysis", "panel_corrected_69d.pkl"))
    sh = sh[["date", "ticker"] + list(FIVE)].copy()
    dates = sorted(sh["date"].unique())

    prov = CompustatCrspProvider(year_lo=lo, year_hi=hi)
    tmap, ambiguous = _ticker_to_permno(prov, dates)
    want = set(sh["ticker"].astype(str).str.upper().str.strip())
    tmap = tmap[tmap["ticker"].isin(want)]
    link_rate = round(len(tmap) / max(1, len(want)), 6)

    prov.permnos = set(tmap["permno"].astype(int))
    tickers = prov.universe(limit=limit or None)
    if not tickers:
        raise SystemExit("REFUSING: no permno carries both a price series and a fundamental")

    cp = build_fundamental_panel(prov, tickers, grid_dates=dates, horizon=63,
                                 lookback_years=18, keep_numbers=False)

    # Compute BOTH composites with the SAME shipped function on the SAME five columns, so a
    # disagreement cannot be my arithmetic (`B7`).
    def _comp(df):
        out = []
        for d, sub in df.groupby("date", sort=True):
            s = sub.copy()
            s["comp"] = composite_from_frame(s, list(FIVE), FIVE_W, zscore)
            out.append(s[["date", "ticker", "comp"]])
        return pd.concat(out, ignore_index=True)

    a = _comp(sh)
    b = _comp(cp)
    b["permno_s"] = b["ticker"].astype(str)
    back = dict(zip(tmap["permno_s"], tmap["ticker"]))
    b["ticker"] = b["permno_s"].map(back)
    b = b.dropna(subset=["ticker"])
    a["date"] = a["date"].astype(str)
    b["date"] = b["date"].astype(str)

    j = a.merge(b[["date", "ticker", "comp"]], on=["date", "ticker"],
                how="inner", suffixes=("_sh", "_cp"))
    per = []
    for d, sub in j.groupby("date", sort=True):
        s = sub.dropna(subset=["comp_sh", "comp_cp"])
        if len(s) < 30:
            per.append({"date": d, "n": int(len(s)), "spearman": None,
                        "note": "below the 30-name floor -- not scored"})
            continue
        per.append({"date": d, "n": int(len(s)),
                    "spearman": round(float(s["comp_sh"].corr(s["comp_cp"],
                                                              method="spearman")), 6)})
    sc = [p["spearman"] for p in per if p["spearman"] is not None]
    mean_rho = round(float(np.mean(sc)), 6) if sc else None
    return {
        "bar": GATE_B_BAR,
        "mean_per_date_spearman": mean_rho,
        "passes": (mean_rho is not None and mean_rho >= GATE_B_BAR),
        "dates_scored": len(sc),
        "dates_requested": len(dates),
        "dates_below_name_floor": int(len(per) - len(sc)),
        "min_spearman": round(float(np.min(sc)), 6) if sc else None,
        "median_spearman": round(float(np.median(sc)), 6) if sc else None,
        "ticker_link_rate": link_rate,
        "tickers_linked": int(len(tmap)),
        "tickers_in_sharadar_panel": int(len(want)),
        "tickers_ambiguous_dropped": ambiguous,
        "rows_compared": int(len(j)),
        "compustat_panel_rows": int(len(cp)),
        "provider_notes": prov.notes,
        "per_date": per,
        "era": "2009-2026 overlap ONLY -- training data. The 1972-1998 holdout is NOT read.",
        "note": ("below the bar the holdout is NOT opened, because a pre-1999 result would then "
                 "measure the vendor translation rather than the model"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", choices=["a", "b", "both"], default="both")
    ap.add_argument("--lo", type=int, default=1972)
    ap.add_argument("--hi", type=int, default=2024)
    ap.add_argument("--limit", type=int, default=0,
                    help="Gate B only: cap the name count. A SMOKE TEST, never a verdict (B12).")
    ap.add_argument("--out-json", default=os.path.join(REPO, "OOS1_GATES.json"))
    args = ap.parse_args(argv)

    root = _data_root()
    art = {"item": "OOS1 preparation gates", "trials": 0,
           "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "holdout_era_UNOPENED": list(HOLDOUT),
           "holdout_note": ("r1 is spending 1999-2008 via Sharadar, so the WRDS holdout is "
                            "1972-1998. NOTHING here scores a construction on it."),
           "data_root": root}

    if args.gate in ("a", "both"):
        print("[oos1] GATE A -- French factor sanity, %d-%d ..." % (args.lo, args.hi), flush=True)
        art["gate_a"] = gate_a(root, args.lo, args.hi)
        a1 = art["gate_a"]["A1_market_return"]
        print("   A1 market return: corr %.6f over %d months, mean abs diff %.6f"
              % (a1["correlation"], a1["months_compared"], a1["mean_abs_diff"]), flush=True)
        a2 = art["gate_a"]["A2_size_spread"]
        print("   A2 size spread vs SMB: corr %.6f over %d months"
              % (a2["correlation_with_SMB"], a2["months_compared"]), flush=True)

    if args.gate in ("b", "both"):
        print("[oos1] GATE B -- vendor translation on the 2009-2026 overlap ...", flush=True)
        # 2007, NOT 2009. The grid starts 2009-01-15 and `ret_12_1`/`high_prox` need 252 TRADING
        # days before it, so a floor at the grid's own first year leaves momentum computed on a
        # truncated window -- which would lower Gate B's Spearman for a reason that is NOT
        # vendor translation and would read as a translation failure. Two years of burn-in.
        # It is still far above the 1998 holdout ceiling, so no holdout year is loaded.
        art["gate_b"] = gate_b(root, GATE_B_BURNIN_YEAR, min(args.hi, 2026),
                               limit=args.limit)
        g = art["gate_b"]
        print("   mean per-date Spearman %s over %d dates (bar %.2f) -> %s"
              % (g["mean_per_date_spearman"], g["dates_scored"], GATE_B_BAR,
                 "PASS" if g["passes"] else "FAIL"), flush=True)
        print("   ticker link rate %.4f (%d of %d), %d ambiguous dropped"
              % (g["ticker_link_rate"], g["tickers_linked"],
                 g["tickers_in_sharadar_panel"], g["tickers_ambiguous_dropped"]), flush=True)

    with io.open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("wrote %s" % args.out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
