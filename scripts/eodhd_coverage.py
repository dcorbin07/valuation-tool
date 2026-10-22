# -*- coding: utf-8 -*-
"""`EODHD-CENSUS` part B — coverage of the corrected universe and the $10B tier. ZERO TRIALS.

    python -m scripts.eodhd_coverage --sample 150

**NO FORWARD RETURN IS LOADED AND NO OUTCOME IS COMPUTED** — pinned by test.

**THE LICENCE FENCE:** raw payload goes to `D:\\eodhd` and nowhere else; the committed artifact
carries **derived statistics only** — rates, counts, spans and field names — and **never a per-name
financial value**. A test asserts it.

--------------------------------------------------------------------------------------------
TWO COVERAGE FIGURES, AND THE WEAKER ONE IS LABELLED AS SUCH.

`W-28` measured that an **undated** identifier join assigned one company's dates to a DIFFERENT
company on 54 names, and `TRACELEAD` (three days ago) found a published coverage ratio that divided
a numerator from one population by a denominator from another. So this module reports:

  * **(a) the UNDATED ticker match** against EODHD's own US symbol list — an **UPPER BOUND**, said
    so in the artifact, because a ticker string matching proves nothing about whether the data
    behind it belongs to the company our panel means on that date;
  * **(b) a DATED check on a sample** — for each sampled `(date, ticker)` tier cell, the ticker must
    resolve inside a `crsp.stocknames` name interval covering that date, and EODHD's own statement
    history must carry a period whose **`filing_date` precedes the cell date**. That is the figure
    a study may use.

The dated leg reuses the `stocknames.pkl` already on `D:\\wrds`, so it costs no WRDS connection.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import random
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts import eodhd_census as EC                                    # noqa: E402
from valuation.studies import dipcall as D                               # noqa: E402

OUT = "EODHD_COVERAGE.json"
RAW_SYMBOLS = "us_symbol_list.json"
STOCKNAMES = r"D:\wrds\stocknames.pkl"
TIER_FLOOR = 10e9
SEED = 20261022          # fixed so the sample is reproducible rather than re-rolled


def tier_cells() -> pd.DataFrame:
    p = pd.read_pickle(D.panel_path())[["date", "ticker", "market_cap"]].copy()
    p["date"] = p["date"].astype(str)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    return p


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=150)
    a = ap.parse_args(argv)

    t0 = time.time()
    panel = tier_cells()
    universe = sorted(panel["ticker"].unique())
    tier = panel[panel["cap"] >= TIER_FLOOR]
    tier_tickers = sorted(tier["ticker"].unique())

    out = {"item": "EODHD-CENSUS-COVERAGE", "trials": 0, "forward_return_touched": False,
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "licence": ("EODHD PERSONAL plan: private, non-commercial analysis only. Displaying "
                       "or redistributing the data, in original or repackaged form, is "
                       "forbidden, so nothing here carries a per-name value and raw rows stay "
                       "under D:\\eodhd."),
           "panel": {"file": os.path.basename(D.panel_path()),
                     "universe_names": len(universe),
                     "tier_floor_usd": TIER_FLOOR,
                     "tier_names": len(tier_tickers),
                     "tier_cells": int(len(tier))}}

    # ------------------------------------------------- (a) the UNDATED upper bound
    st, syms = EC._get("exchange-symbol-list/US", {})
    if st != 200 or not isinstance(syms, list):
        raise SystemExit("REFUSING: the US symbol list did not answer (status %s)" % st)
    EC.save_raw(RAW_SYMBOLS, syms)
    eod = {}
    for r in syms:
        c = str(r.get("Code") or "").upper()
        if c and c not in eod:
            eod[c] = r
    uni_hit = [t for t in universe if t in eod]
    tier_hit = [t for t in tier_tickers if t in eod]
    out["undated_upper_bound"] = {
        "eodhd_us_symbols": len(syms),
        "eodhd_distinct_codes": len(eod),
        "universe_matched": len(uni_hit),
        "universe_matched_frac": round(len(uni_hit) / max(1, len(universe)), 6),
        "tier_matched": len(tier_hit),
        "tier_matched_frac": round(len(tier_hit) / max(1, len(tier_tickers)), 6),
        "LABEL": ("UPPER BOUND, and it is NOT a usable coverage figure. A ticker string matching "
                  "proves nothing about whether the data behind it belongs to the company this "
                  "panel means on that date -- W-28 measured an undated join assigning one "
                  "company's dates to a different company on 54 names."),
        "types_in_list": dict(pd.Series([str(r.get("Type")) for r in syms]).value_counts()
                              .head(8)),
    }
    print("[cov] EODHD US symbols %d | universe %d/%d = %.4f | tier %d/%d = %.4f"
          % (len(syms), len(uni_hit), len(universe),
             out["undated_upper_bound"]["universe_matched_frac"],
             len(tier_hit), len(tier_tickers),
             out["undated_upper_bound"]["tier_matched_frac"]), flush=True)

    # ------------------------------------------------- (b) the DATED sample
    if not os.path.isfile(STOCKNAMES):
        out["dated_sample"] = {"ok": False,
                               "why": "stocknames.pkl absent at %s; the dated leg cannot run and "
                                      "is NOT substituted with the undated one" % STOCKNAMES}
    else:
        sn = pd.read_pickle(STOCKNAMES)
        sn["ticker"] = sn["ticker"].astype(str).str.strip().str.upper()
        rnd = random.Random(SEED)
        cells = tier[["date", "ticker"]].drop_duplicates().reset_index(drop=True)
        idx = rnd.sample(range(len(cells)), min(a.sample, len(cells)))
        res = {"n_sampled_cells": len(idx), "seed": SEED,
               "in_eodhd_symbol_list": 0,
               "fundamentals_answered": 0,
               "has_a_period_filed_before_the_cell_date": 0,
               "ticker_inside_a_crsp_name_interval": 0,
               "BOTH_dated_legs": 0,
               "delisted_flag_true": 0,
               "cik_present": 0, "cusip_present": 0, "isin_present": 0,
               "filing_date_real_share": [], "errors": {}}
        seen = {}
        for n, i in enumerate(idx, 1):
            date = str(cells.at[i, "date"])
            tk = str(cells.at[i, "ticker"])
            if tk in eod:
                res["in_eodhd_symbol_list"] += 1
            # the CRSP dated leg: did this ticker belong to one company on that date?
            rows = sn[sn["ticker"] == tk]
            if len(rows):
                d = pd.to_datetime(date, errors="coerce")
                lo = pd.to_datetime(rows["namedt"], errors="coerce")
                hi = pd.to_datetime(rows["nameenddt"], errors="coerce")
                inside = bool(((d >= lo) & (d <= hi)).any())
            else:
                inside = False
            if inside:
                res["ticker_inside_a_crsp_name_interval"] += 1
            # EODHD's own statement history
            if tk in seen:
                f = seen[tk]
            else:
                stt, f = EC._get("fundamentals/%s.US" % tk, {})
                f = f if (stt == 200 and isinstance(f, dict)) else None
                seen[tk] = f
                if f is None:
                    res["errors"][str(stt)] = res["errors"].get(str(stt), 0) + 1
            filed_before = False
            if f:
                res["fundamentals_answered"] += 1
                gen = f.get("General") or {}
                if gen.get("IsDelisted"):
                    res["delisted_flag_true"] += 1
                res["cik_present"] += 1 if gen.get("CIK") else 0
                res["cusip_present"] += 1 if gen.get("CUSIP") else 0
                res["isin_present"] += 1 if gen.get("ISIN") else 0
                q = (((f.get("Financials") or {}).get("Income_Statement") or {})
                     .get("quarterly") or {})
                real = tot = 0
                for v in q.values():
                    if not isinstance(v, dict):
                        continue
                    pd_, fd = str(v.get("date") or ""), str(v.get("filing_date") or "")
                    if len(pd_) == 10 and len(fd) == 10:
                        tot += 1
                        if fd != pd_:
                            real += 1
                        if fd < date:
                            filed_before = True
                if tot:
                    res["filing_date_real_share"].append(real / tot)
            if filed_before:
                res["has_a_period_filed_before_the_cell_date"] += 1
            if filed_before and inside:
                res["BOTH_dated_legs"] += 1
            if n % 25 == 0:
                print("    %d/%d sampled cells" % (n, len(idx)), flush=True)
        k = max(1, res["n_sampled_cells"])
        shares = res.pop("filing_date_real_share")
        res["filing_date_real_share_mean"] = (round(sum(shares) / len(shares), 6)
                                             if shares else None)
        res["distinct_tickers_requested"] = len(seen)
        for key in ("in_eodhd_symbol_list", "fundamentals_answered",
                    "has_a_period_filed_before_the_cell_date",
                    "ticker_inside_a_crsp_name_interval", "BOTH_dated_legs",
                    "delisted_flag_true"):
            res[key + "_frac"] = round(res[key] / k, 6)
        for key in ("cik_present", "cusip_present", "isin_present"):
            res[key + "_frac"] = round(res[key] / max(1, res["fundamentals_answered"]), 6)
        res["ok"] = True
        res["THE_USABLE_FIGURE"] = ("BOTH_dated_legs_frac -- the share of sampled tier cells where "
                                    "the ticker sits inside a CRSP name interval covering that "
                                    "date AND EODHD carries a statement filed before it. The "
                                    "undated figure above is an upper bound and is not this.")
        out["dated_sample"] = res
        print("[cov] dated sample: both legs %d/%d = %.4f | filed-before %.4f | in CRSP window "
              "%.4f" % (res["BOTH_dated_legs"], res["n_sampled_cells"],
                        res["BOTH_dated_legs_frac"],
                        res["has_a_period_filed_before_the_cell_date_frac"],
                        res["ticker_inside_a_crsp_name_interval_frac"]), flush=True)

    st, u = EC._get("user")
    if isinstance(u, dict):
        out["budget"] = {"apiRequests": u.get("apiRequests"),
                         "dailyRateLimit": u.get("dailyRateLimit"),
                         "date": u.get("apiRequestsDate")}
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[cov] wrote %s in %.0fs" % (p, out["seconds"]), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
