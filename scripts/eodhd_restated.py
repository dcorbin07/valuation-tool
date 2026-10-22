# -*- coding: utf-8 -*-
"""`EODHD-CENSUS` part C — is the statement history AS-REPORTED or RESTATED? ZERO TRIALS.

    python -m scripts.eodhd_restated --names 60

**NO FORWARD RETURN IS LOADED AND NO OUTCOME IS COMPUTED** — pinned by test. **The committed
artifact carries agreement RATES and median relative differences only; no per-name value is ever
written to a tracked file.**

--------------------------------------------------------------------------------------------
WHY THE TEST IS AGAINST SHARADAR ARQ RATHER THAN AGAINST A NAMED RESTATEMENT.

The brief asks to "check a known restatement: does history show the original or the restated
figure?" Checking one famous case would answer it for one company, and a single case cannot
separate "this vendor restates" from "this vendor happens to carry the original for that one
filing".

The project already owns the right control: **`data/backtest/fundamentals.csv` is Sharadar's
`ARQ` dimension — AS-REPORTED quarterly** (the record's own COVERAGE-RULE note: the export is
ARQ-only, which is why `roe`/`roic` are empty). So for the same `(ticker, fiscal period)` pair:

  * if EODHD agrees with ARQ, **EODHD is carrying the as-reported figure too**;
  * if EODHD disagrees in a direction that tracks the passage of time, it is carrying a **later
    restatement**.

That is a RATE over hundreds of pairs rather than an anecdote, and the comparison is **derived
statistics only**, so it may be published.

**THE HONEST LIMIT, STATED RATHER THAN DISCOVERED:** agreement does not prove either vendor is
as-reported — both could carry the same restatement. It proves they are the SAME object, which is
what a replication needs. Disagreement is the informative direction.
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

OUT = "EODHD_RESTATED.json"
TIER_FLOOR = 10e9
SEED = 20261022

#: EODHD field -> Sharadar column. Chosen because all four are unambiguous line items that both
#: vendors carry under the same accounting definition; ratios are deliberately excluded, since a
#: ratio disagreement could be a denominator convention rather than a restatement.
FIELDS = [("totalRevenue", "revenue", "Income_Statement"),
          ("netIncome", "netinc", "Income_Statement"),
          ("totalStockholderEquity", "equity", "Balance_Sheet"),
          ("totalAssets", "assets", "Balance_Sheet")]

TOL = 0.005          # 0.5% -- below this the two are the same figure in different roundings


def _sharadar():
    d = _HERE
    for _ in range(6):
        p = os.path.join(d, "data", "backtest", "fundamentals.csv")
        if os.path.isfile(p):
            return p
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    raise SystemExit("REFUSING: data/backtest/fundamentals.csv not found in any parent")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", type=int, default=60)
    a = ap.parse_args(argv)
    t0 = time.time()

    cols = ["ticker", "dimension", "calendardate", "datekey", "reportperiod",
            "revenue", "netinc", "equity", "assets"]
    head = pd.read_csv(_sharadar(), nrows=2)
    use = [c for c in cols if c in head.columns]
    sh = pd.read_csv(_sharadar(), usecols=use, low_memory=False)
    if "dimension" in sh.columns:
        dims = dict(sh["dimension"].value_counts())
        sh = sh[sh["dimension"].astype(str).str.upper() == "ARQ"]
    else:
        dims = {}
    sh["ticker"] = sh["ticker"].astype(str).str.upper()
    per_col = "reportperiod" if "reportperiod" in sh.columns else "calendardate"
    sh[per_col] = sh[per_col].astype(str)

    panel = pd.read_pickle(D.panel_path())[["ticker", "market_cap"]].copy()
    panel["ticker"] = panel["ticker"].astype(str).str.upper()
    panel["cap"] = pd.to_numeric(panel["market_cap"], errors="coerce")
    tier = sorted(panel[panel["cap"] >= TIER_FLOOR]["ticker"].unique())
    pool = [t for t in tier if t in set(sh["ticker"])]
    rnd = random.Random(SEED)
    names = rnd.sample(pool, min(a.names, len(pool)))

    out = {"item": "EODHD-CENSUS-RESTATED", "trials": 0, "forward_return_touched": False,
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "licence": ("EODHD PERSONAL plan: private, non-commercial analysis only. This artifact "
                       "carries agreement RATES and median relative differences only -- never a "
                       "per-name value."),
           "control": {"file": "data/backtest/fundamentals.csv",
                       "dimension_used": "ARQ (as-reported quarterly)",
                       "dimensions_in_export": {str(k): int(v) for k, v in dims.items()},
                       "period_column": per_col},
           "sample": {"seed": SEED, "tier_names_in_both": len(pool), "names_requested": len(names)},
           "tolerance_relative": TOL,
           "fields": {}}

    stats = {e: {"pairs": 0, "agree": 0, "reldiffs": []} for e, _, _ in FIELDS}
    answered = 0
    for n, tk in enumerate(names, 1):
        st, f = EC._get("fundamentals/%s.US" % tk, {})
        if st != 200 or not isinstance(f, dict):
            continue
        answered += 1
        sub = sh[sh["ticker"] == tk]
        if not len(sub):
            continue
        shv = {}
        for _, r in sub.iterrows():
            shv[str(r[per_col])[:10]] = r
        fin = f.get("Financials") or {}
        for e_field, s_col, stmt in FIELDS:
            if s_col not in sh.columns:
                continue
            q = ((fin.get(stmt) or {}).get("quarterly") or {})
            for per, row in q.items():
                if not isinstance(row, dict):
                    continue
                key = str(row.get("date") or per)[:10]
                if key not in shv:
                    continue
                ev, sv = row.get(e_field), shv[key].get(s_col)
                try:
                    ev = float(ev)
                    sv = float(sv)
                except (TypeError, ValueError):
                    continue
                if not (ev == ev and sv == sv):          # NaN
                    continue
                base = max(abs(ev), abs(sv))
                if base <= 0:
                    continue
                rd = abs(ev - sv) / base
                stats[e_field]["pairs"] += 1
                stats[e_field]["reldiffs"].append(rd)
                if rd <= TOL:
                    stats[e_field]["agree"] += 1
        if n % 10 == 0:
            print("    %d/%d names" % (n, len(names)), flush=True)

    for e_field, s_col, _ in FIELDS:
        s = stats[e_field]
        ds = sorted(s["reldiffs"])
        out["fields"][e_field] = {
            "sharadar_column": s_col,
            "pairs_compared": s["pairs"],
            "agree_within_tolerance": s["agree"],
            "agreement_rate": round(s["agree"] / s["pairs"], 6) if s["pairs"] else None,
            "median_relative_difference": round(ds[len(ds) // 2], 6) if ds else None,
            "p90_relative_difference": round(ds[int(len(ds) * 0.9)], 6) if ds else None,
        }
        print("  %-24s pairs %5d  agree %.4f  median reldiff %s"
              % (e_field, s["pairs"],
                 out["fields"][e_field]["agreement_rate"] or -1,
                 out["fields"][e_field]["median_relative_difference"]), flush=True)

    out["names_answered"] = answered
    tot = sum(v["pairs_compared"] for v in out["fields"].values())
    ag = sum(v["agree_within_tolerance"] for v in out["fields"].values())
    out["overall"] = {"pairs": tot, "agree": ag,
                      "agreement_rate": round(ag / tot, 6) if tot else None}
    out["HOW_TO_READ_IT"] = (
        "Agreement does NOT prove either vendor is as-reported -- both could carry the same "
        "restatement. It proves they are the SAME object, which is what a vendor replication "
        "needs. DISAGREEMENT is the informative direction, and its rate is the figure to quote.")
    st, u = EC._get("user")
    if isinstance(u, dict):
        out["budget"] = {"apiRequests": u.get("apiRequests"),
                         "dailyRateLimit": u.get("dailyRateLimit")}
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[restated] overall agreement %s over %d pairs -> %s"
          % (out["overall"]["agreement_rate"], tot, p), flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
