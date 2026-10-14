# -*- coding: utf-8 -*-
"""`BETA-FORECAST` §9 — how fair values across the scan would move under Blume.

    python -m scripts.beta_forecast_fairvalue

**A CONSEQUENCE, NOT A BAR.** The register's §12 says so explicitly: no fair value is re-derived
inside the contest and this pass changes no verdict. It exists because the prompt asks what the
winner would cost, and because `wacc.py`'s own note records the PRIOR rejection in exactly these
units — *"it breached the do-no-harm bound at 2.491% against a 2% ceiling"* — so the only way to
put this item's result beside that one is to measure the same quantity.

**EACH NAME IS VALUED TWICE THROUGH THE SHIPPED PATH**, once at the vendor beta and once at
`blume(vendor beta)`, via `pipeline.value_ticker(..., overrides={"beta": ...})`. Nothing is
re-implemented: `_resolve_beta`'s rung 1 takes the override, so the only thing that differs
between the two valuations is the beta (`B7`).

**THE SAMPLE IS DECLARED HERE, BEFORE IT RUNS, AND IT IS NOT CHOSEN ON THE RESULT**: every
constituent of the published Valquo Index, plus the three names item 53 reasons from (NVDA, KO,
TSLA). The Index is the book the product actually holds, which is the population a fair-value
consequence matters for, and the three named ones are there so the figures item 53 published can
be checked against this pass rather than taken on trust.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import beta_forecast as BF                           # noqa: E402
from valuation.studies import dipcall as D                                  # noqa: E402

OUT = "BETA_FORECAST_FAIRVALUE.json"

#: DECLARED: item 53's own worked names, so its published figures can be checked here.
ITEM53 = ["NVDA", "KO", "TSLA"]
INDEX_URL = "https://valquo.co/api/valquo-index"
PACE_S = 1.5
CANARY = "AAPL"


def sample() -> tuple:
    import urllib.request
    try:
        with urllib.request.urlopen(INDEX_URL, timeout=60) as r:
            d = json.load(r)
        idx = [str(p.get("ticker")).upper() for p in (d.get("positions") or [])
               if p.get("ticker")]
    except Exception as e:                                                  # noqa: BLE001
        raise SystemExit("REFUSING: the Index route is unreachable (%s). The sample is declared "
                         "as the Index's own constituents and substituting another population "
                         "would be choosing it after the fact." % repr(e)[:120])
    names = sorted(set(idx) | set(ITEM53))
    return names, len(idx)


def value_at(ticker: str, beta):
    from valuation.engine import pipeline as P
    try:
        res = P.value_ticker(ticker, run_ai=False,
                             overrides=({"beta": float(beta)} if beta is not None else None))
    except Exception as e:                                                  # noqa: BLE001
        return None, repr(e)[:160]
    return res, None


def main(argv=None):
    t0 = time.time()
    names, n_index = sample()
    print("[fv] sample: %d names (%d Index constituents + item 53's three)"
          % (len(names), n_index), flush=True)

    # THE CANARY, same rule as every other live pass in this project: the vendor quota does not
    # raise when exhausted, it silently empties CompanyData, and a degraded run would report a
    # fair-value move of zero on names that never valued.
    res, err = value_at(CANARY, None)
    cd = getattr(res, "company", None) if res else None
    if err or cd is None or getattr(cd, "beta", None) is None or not getattr(cd, "market_cap", 0):
        raise SystemExit("REFUSING: the canary %s came back degraded (%s). A fair-value "
                         "consequence measured through a throttled feed would be wrong in the "
                         "flattering direction." % (CANARY, err or "no beta/market cap"))
    print("[fv] canary ok: beta %.4f" % cd.beta, flush=True)

    rows = []
    for i, tk in enumerate(names, 1):
        if i > 1:
            time.sleep(PACE_S)
        r0, e0 = value_at(tk, None)
        cd0 = getattr(r0, "company", None) if r0 else None
        vb = getattr(cd0, "beta", None) if cd0 is not None else None
        if vb is None or not np.isfinite(float(vb)):
            rows.append({"ticker": tk, "status": "NO_VENDOR_BETA", "reason": e0 or "beta None"})
            continue
        fv0 = getattr(r0, "base_fair_value", None)
        bb = BF.blume(float(vb))
        r1, e1 = value_at(tk, bb)
        fv1 = getattr(r1, "base_fair_value", None) if r1 else None
        row = {"ticker": tk, "status": "OK", "vendor_beta": float(vb), "blume_beta": bb,
               "fv_vendor": (None if fv0 is None else float(fv0)),
               "fv_blume": (None if fv1 is None else float(fv1)),
               "price": (None if cd0 is None else getattr(cd0, "price", None))}
        if fv0 and fv1 and float(fv0) > 0:
            row["pct_move"] = (float(fv1) / float(fv0) - 1.0) * 100.0
        else:
            row["status"] = "NOT_VALUABLE_BOTH_SIDES"
            row["reason"] = (e1 or "one side produced no base fair value")
        rows.append(row)
        if i % 20 == 0:
            print("    %d/%d, %.1f min" % (i, len(names), (time.time() - t0) / 60.0), flush=True)

    ok = [r for r in rows if r.get("pct_move") is not None]
    mv = np.array([r["pct_move"] for r in ok], dtype=float)
    out = {
        "item": "BETA-FORECAST", "part": "section 9 -- the fair-value consequence",
        "IT_IS_A_CONSEQUENCE_NOT_A_BAR": True,
        "register": "PREREG_beta_forecast.md", "register_commit": "67831e7",
        "sample_declared": "the published Valquo Index's constituents plus NVDA, KO and TSLA",
        "n_sample": len(names), "n_index_constituents": n_index,
        "n_valued_both_sides": len(ok),
        "n_no_vendor_beta": sum(1 for r in rows if r["status"] == "NO_VENDOR_BETA"),
        "n_not_valuable": sum(1 for r in rows if r["status"] == "NOT_VALUABLE_BOTH_SIDES"),
        "rows": rows,
    }
    if len(ok):
        out["pct_move"] = {
            "median_abs": float(np.median(np.abs(mv))),
            "mean_abs": float(np.abs(mv).mean()),
            "p95_abs": float(np.percentile(np.abs(mv), 95)),
            "max_abs": float(np.abs(mv).max()),
            "median_signed": float(np.median(mv)),
            "n_up": int((mv > 0).sum()), "n_down": int((mv < 0).sum()),
            "n_moved_over_25pct": int((np.abs(mv) > 25).sum()),
        }
        out["prior_do_no_harm"] = {
            "bound_pct": 2.0, "measured_pct": 2.491,
            "source": "HANDOFF_live_data_bugs.md Part 2, on 128 live names",
            "NOTE": ("the prior figure is a MEDIAN ABSOLUTE move on its own 128-name population; "
                     "this pass's median_abs is the comparable statistic, and the two populations "
                     "are different -- the comparison is of the same quantity, not of the same "
                     "sample"),
        }
        print("\n[fv] %d of %d valued both sides | median |move| %.3f%%  mean %.3f%%  p95 %.3f%%  "
              "max %.3f%%  | up %d down %d  | >25%%: %d"
              % (len(ok), len(names), out["pct_move"]["median_abs"],
                 out["pct_move"]["mean_abs"], out["pct_move"]["p95_abs"],
                 out["pct_move"]["max_abs"], out["pct_move"]["n_up"],
                 out["pct_move"]["n_down"], out["pct_move"]["n_moved_over_25pct"]), flush=True)
        for tk in ITEM53:
            r = next((x for x in rows if x["ticker"] == tk), None)
            if r and r.get("pct_move") is not None:
                print("    %-5s vendor beta %.3f -> Blume %.3f | fair value %.2f -> %.2f (%+.2f%%)"
                      % (tk, r["vendor_beta"], r["blume_beta"], r["fv_vendor"], r["fv_blume"],
                         r["pct_move"]), flush=True)
    out["seconds"] = round(time.time() - t0, 1)
    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[fv] wrote %s" % p, flush=True)
    return out


if __name__ == "__main__":
    main()
    raise SystemExit(0)
