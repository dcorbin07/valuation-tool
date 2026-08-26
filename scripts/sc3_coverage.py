"""SC-3 (TIER-E-FIN) pass 0 — THE COVERAGE CENSUS, run and read BEFORE any register.

`O-1` returned **0.19% power** because a coverage figure measured on the ALERT BOOK was applied
to the PANEL. `W-14` died on a premise nobody had measured. This census exists so SC-3 cannot
repeat either: it measures the population the arm would actually be scored on — **matched,
two-sided, deep-ITM call/put pairs at LONG tenor in the Tier E harvest freeze, 2016–2018** —
before a single line of register is written.

WHAT SC-3 IS. `DEEPITM-FIN` measured the financing question at **60–90 DTE** and closed it: the
option route costs **rf + 702 bps all-in** (financing 342.35 + roll 340.06 + commission 3.57) at
median DTE 73 and 5.0 rolls/yr, which is **more expensive than both cards an operator would use**
(Robinhood Gold rf + 420, IBKR Pro rf + 150). Its closing reading was that **60–90 DTE is the
WORST case** and the tenor we do not own is where the case could differ. **`MB4` then closed
"financing improves with tenor" as UNOWNABLE**, on the grounds that the owned cache is capped at
200 DTE and Tier E reaches 858 DTE **only for 2016–2018**. `S3-I5` lifted the Tier-E quoting
block, so the tenor is now readable — and whether 2016–2018 can answer the question is exactly
what this census measures.

NOTHING IS RE-IMPLEMENTED. `matched_pairs`, `call_delta`, `implied_rate`, `pv_dividends`,
`load_spot` and `load_dividends` are `DEEPITM-FIN`'s own, IMPORTED. Only the DTE band moves, and
it moves as a declared parameter rather than by editing that module (`B7`: a second copy of the
pair builder would stop this being the same measurement under a different tenor).

    python -m scripts.sc3_coverage
"""
from __future__ import annotations

import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import chain_store as cs                          # noqa: E402
import deepitm_financing as D                                         # noqa: E402

# ONE source for the rate, and it is DEEPITM-FIN's own. Importing blackscholes a second time by
# name would be a second path to the same primitive; taking it off D guarantees this census and
# that module cannot drift apart (B7).
BS = D.BS

OUT = "SC3_COVERAGE.json"

# The Tier E window. NOT chosen here - it is the only window Tier E reaches past 200 DTE, which
# is `MB4`'s own stated reason for closing the question as unownable.
YEARS = (2016, 2017, 2018)

# The tenor SC-3 exists to reach. The lower edge is the owned cache's hard cap, so every pair
# counted here is one `DEEPITM-FIN` structurally could not see.
LONG_LO, LONG_HI = 200, 858

# `DEEPITM-FIN`'s own band, reused verbatim so the two measurements are comparable.
DELTA_LO, DELTA_HI = D.DELTA_LO, D.DELTA_HI


def chain_frame(path: str) -> pd.DataFrame:
    """Read either payload shape - the harvest pickles a dict carrying `rows`."""
    p = pd.read_pickle(path)
    if isinstance(p, dict):
        if p.get("rows") is None:
            raise ValueError("harvest payload with no rows")
        return p["rows"]
    return p


def _data_root():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for cand in (os.path.join(here, "data"),
                 os.path.abspath(os.path.join(here, "..", "..", "..", "data"))):
        if os.path.isdir(os.path.join(cand, "free_analysis")):
            return cand
    return os.path.join(here, "data")


def _out(name):
    return os.path.join(_data_root(), "free_analysis", name)


def main():
    chains, prov = cs.resolve_harvest()
    if not prov.get("pinned"):
        raise SystemExit("SC-3 reads the PINNED harvest freeze only")
    print("harvest: %s  manifest %s"
          % (chains, str(prov.get("manifest_sha256"))[:16]), flush=True)

    spot = D.load_spot()
    divs = D.load_dividends()
    print("spot series %d ; dividend series %d" % (len(spot), len(divs)), flush=True)
    if not spot:
        raise SystemExit("REFUSING: no spot series. EXISTENCE IS NOT POPULATION.")

    syms = sorted(d for d in os.listdir(chains) if os.path.isdir(os.path.join(chains, d)))
    print("harvest symbols: %d" % len(syms), flush=True)

    # ---- stage 1: how much LONG-TENOR chain exists at all? ---------------------------------
    stage = {"units_read": 0, "rows": 0, "rows_long": 0, "two_sided_long": 0}
    pair_rows = []
    per_year = {}
    names_with_long = set()

    for i, sym in enumerate(syms, 1):
        d = os.path.join(chains, sym)
        frames = []
        for y in YEARS:
            f = os.path.join(d, "%s-%d.pkl" % (sym, y))
            if not os.path.isfile(f):
                continue
            try:
                fr = chain_frame(f)
            except Exception:                                          # noqa: BLE001
                continue
            if isinstance(fr, pd.DataFrame) and len(fr):
                frames.append(fr)
                stage["units_read"] += 1
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        df["date"] = pd.to_datetime(df["date"])
        df["expiration"] = pd.to_datetime(df["expiration"])
        df["dte"] = (df["expiration"] - df["date"]).dt.days
        df["symbol"] = sym.upper()
        df["right"] = df["right"].astype(str).str.upper().str[:1]
        stage["rows"] += len(df)

        lo = df[(df["dte"] >= LONG_LO) & (df["dte"] <= LONG_HI)]
        stage["rows_long"] += len(lo)
        if not len(lo):
            continue
        names_with_long.add(sym.upper())

        # `matched_pairs` reads the module's band, so set it for the long window and restore.
        old = (D.DTE_LO, D.DTE_HI)
        D.DTE_LO, D.DTE_HI = LONG_LO, LONG_HI
        try:
            m = D.matched_pairs(df)
        finally:
            D.DTE_LO, D.DTE_HI = old
        stage["two_sided_long"] += len(m)
        if not len(m):
            continue

        s = spot.get(sym.upper())
        if s is None:
            continue
        rf_cache = {}
        for t in m.itertuples(index=False):
            try:
                S = float(s.asof(t.date))
            except Exception:                                          # noqa: BLE001
                continue
            if not np.isfinite(S) or S <= 0:
                continue
            key = t.date.date()
            r = rf_cache.get(key)
            if r is None:
                r = float(BS.risk_free_rate(key))
                rf_cache[key] = r
            K, T = float(t.strike), float(t.T)
            p_mid = (t.bid_p + t.ask_p) / 2.0
            dlt = D.call_delta(S, K, T, r, p_mid)
            if dlt is None or not (DELTA_LO <= dlt <= DELTA_HI):
                continue
            pvd = D.pv_dividends(sym.upper(), t.date, t.expiration, divs, r)
            c_mid = (t.bid_c + t.ask_c) / 2.0
            r_mid = D.implied_rate(S, pvd, c_mid, p_mid, K, T)
            r_exe = D.implied_rate(S, pvd, float(t.ask_c), float(t.bid_p), K, T)
            if r_mid is None or r_exe is None:
                continue
            y = int(t.date.year)
            per_year[y] = per_year.get(y, 0) + 1
            pair_rows.append({
                "symbol": sym.upper(), "date": t.date, "year": y, "dte": int(t.dte),
                "delta": dlt, "rf": r,
                "excess_mid_bps": (r_mid - r) * 1e4,
                "excess_exe_bps": (r_exe - r) * 1e4,
            })

        if i % 100 == 0:
            print("  ... %d/%d symbols, %d scoreable long pairs"
                  % (i, len(syms), len(pair_rows)), flush=True)

    pairs = pd.DataFrame(pair_rows)
    if len(pairs):
        pairs.to_pickle(_out("SC3_LONG_PAIRS.pkl"))     # RULE 9: draws land before summarising

    rec = {
        "item": "SC-3 (TIER-E-FIN)", "pass": "coverage-census",
        "status": "READ BEFORE ANY REGISTER - no hypothesis is scored anywhere in this file",
        "why": ("O-1 returned 0.19 percent power on a coverage figure measured on the ALERT BOOK "
                "and applied to the PANEL; W-14 died on an unmeasured premise. This measures the "
                "population the arm would be scored on, first."),
        "tenor": {"long_lo": LONG_LO, "long_hi": LONG_HI,
                  "deepitm_fin_band": [D.DTE_LO, D.DTE_HI],
                  "note": ("the lower edge is the owned cache's 200-DTE hard cap, so every pair "
                           "counted here is one DEEPITM-FIN structurally could not see")},
        "window": list(YEARS),
        "delta_band": [DELTA_LO, DELTA_HI],
        "harvest_symbols": len(syms),
        "units_read": stage["units_read"],
        "rows_total": stage["rows"], "rows_in_long_band": stage["rows_long"],
        "two_sided_long_pairs": stage["two_sided_long"],
        "names_with_any_long_chain": len(names_with_long),
        "scoreable_pairs": int(len(pairs)),
        "scoreable_names": int(pairs["symbol"].nunique()) if len(pairs) else 0,
        "scoreable_dates": int(pairs["date"].nunique()) if len(pairs) else 0,
        "pairs_per_year": {str(k): int(v) for k, v in sorted(per_year.items())},
        "deepitm_fin_reference": {
            "pairs_at_60_90_dte": 12904, "names": 185, "span": "2016-01-19..2025-10-15",
            "min_n_floor": D.MIN_N,
        },
    }
    if len(pairs):
        rec["dte_distribution"] = {
            "min": int(pairs["dte"].min()), "p25": float(pairs["dte"].quantile(0.25)),
            "median": float(pairs["dte"].median()), "p75": float(pairs["dte"].quantile(0.75)),
            "max": int(pairs["dte"].max()),
        }
        rec["rolls_per_year_at_median_dte"] = 365.0 / float(pairs["dte"].median())
        rec["names_reaching_min_n"] = int(
            (pairs.groupby("symbol").size() >= D.MIN_N).sum())

    with io.open(_out(OUT), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, default=str)

    print()
    print("rows in the %d-%d DTE band: %d over %d names"
          % (LONG_LO, LONG_HI, stage["rows_long"], len(names_with_long)))
    print("two-sided matched long pairs: %d" % stage["two_sided_long"])
    print("SCOREABLE long pairs (delta band + parity solve): %d over %d names, %d dates"
          % (rec["scoreable_pairs"], rec["scoreable_names"], rec["scoreable_dates"]))
    print("per year: %s" % rec["pairs_per_year"])
    if len(pairs):
        print("DTE median %.0f -> %.2f rolls/yr (DEEPITM-FIN measured 5.0 at median 73)"
              % (pairs["dte"].median(), rec["rolls_per_year_at_median_dte"]))
    print("DEEPITM-FIN's own reference: 12,904 pairs at 60-90 DTE over 185 names")
    print("wrote %s" % _out(OUT))


if __name__ == "__main__":
    main()
