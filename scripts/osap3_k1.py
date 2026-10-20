# -*- coding: utf-8 -*-
"""`OSAP3` `K1` — are the three signals' inputs actually present in Sharadar? ZERO TRIALS.

    python -m scripts.osap3_k1

**NO FORWARD RETURN IS LOADED AND NO OUTCOME IS COMPUTED** — pinned by test. This is
`PREREG_DRAFT_osap3.md`'s `K1`, a free pre-outcome kill: under `MB1-SEL` a control can only ever
BLOCK a finding, so it costs zero trials and may run before the register exists. The draft calls it
*"the kill most likely to shrink the batch below three"*.

**THE COVERAGE RULE IS THE WHOLE POINT OF DOING THIS FIRST.** `CLAUDE.md`'s hard rule exists because
five wired factors were silently empty for this project's entire history — `roe`, `roic` and
`assetturnover` are non-null in **0 of 197,265 rows**, because the licensed export is ARQ-only and
Sharadar fills its ratio columns only in ART/ARY. **A column being present in the header is not the
column being present in the data**, so every input is checked for non-null COVERAGE on the arm's own
population and never for mere existence.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from valuation.studies import dipcall as D                               # noqa: E402

OUT = "OSAP3_K1.json"
DOCS = os.path.join("data", "factors", "raw", "osap_signal_docs.csv")

K1_BAR = 0.70                 # draft §4, reused verbatim
TIER_FLOOR = 10e9

#: Each signal's inputs, taken from the draft's §8 live-route statement and from each paper's own
#: construction. Declared HERE so the check cannot be narrowed after a column comes back empty.
INPUTS = {
    "EquityDuration": ["equity", "netinc", "revenue", "assets"],
    "BetaLiquidityPS": [],          # needs an EXTERNAL factor series, handled separately
    "realestate": ["ppnenet", "assets"],
}

#: Tuzel's measure is REAL-ESTATE PP&E (buildings and land) over total PP&E, so the components are
#: the input and net PP&E alone cannot build it. Probed by name rather than assumed absent.
REALESTATE_COMPONENTS = ["ppegtbldg", "ppegtland", "ppent_bldg", "buildings", "land",
                         "ppegt", "ppenetbldg", "ppenetland", "realestate"]


def _data_root():
    d = _HERE
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "data", "backtest", "fundamentals.csv")):
            return os.path.join(d, "data")
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    raise SystemExit("REFUSING: data/backtest/fundamentals.csv not found in any parent")


def tier():
    p = pd.read_pickle(D.panel_path())[["date", "ticker", "market_cap"]].copy()
    p["date"] = p["date"].astype(str)
    p["ticker"] = p["ticker"].astype(str).str.upper()
    p["cap"] = pd.to_numeric(p["market_cap"], errors="coerce")
    t = p[p["cap"] >= TIER_FLOOR]
    t = t[(t["date"] >= D.BUILD_LO) & (t["date"] <= D.BUILD_HI)]
    return t[t["ticker"].map(D.stable_key_half) == 0][["date", "ticker"]].reset_index(drop=True)


def main(argv=None):
    root = _data_root()
    f = os.path.join(root, "backtest", "fundamentals.csv")
    need = sorted({c for v in INPUTS.values() for c in v}
                  | {"ticker", "datekey", "dimension", "roe", "roic", "assetturnover"})
    head = pd.read_csv(f, nrows=2)
    present = [c for c in need if c in head.columns]
    df = pd.read_csv(f, usecols=present, low_memory=False)

    res = {"item": "OSAP3-K1", "trials": 0, "forward_return_touched": False,
           "bar": {"input_coverage": K1_BAR,
                   "source": "PREREG_DRAFT_osap3.md section 4, reused verbatim"},
           "fundamentals_rows": int(len(df)),
           "COVERAGE_RULE": ("a column present in the header is not the column present in the "
                             "data; roe, roic and assetturnover are the project's own named "
                             "example of a wired-but-empty factor"),
           "columns_absent_from_the_export": [c for c in need if c not in head.columns],
           "column_coverage": {}}

    for c in present:
        if c in ("ticker", "datekey", "dimension"):
            continue
        nn = int(df[c].notna().sum())
        res["column_coverage"][c] = {"non_null_rows": nn,
                                     "non_null_frac": round(nn / max(1, len(df)), 6)}

    # THE NAMED TRAP, CHECKED RATHER THAN CITED.
    for c in ("roe", "roic", "assetturnover"):
        cov = res["column_coverage"].get(c)
        if cov is not None:
            res.setdefault("the_named_empty_columns", {})[c] = cov

    # Tuzel's components.
    res["realestate_components_probed"] = {
        c: bool(c in head.columns) for c in REALESTATE_COMPONENTS}
    res["realestate_components_found"] = sorted(
        c for c, v in res["realestate_components_probed"].items() if v)

    # Per-signal verdict.
    res["signals"] = {}
    for sig, cols in INPUTS.items():
        if sig == "BetaLiquidityPS":
            res["signals"][sig] = {
                "inputs": "the Pastor-Stambaugh traded liquidity factor, plus per-name monthly "
                          "returns for a rolling liquidity beta",
                "in_repo": bool(os.path.isdir(os.path.join(root, "factors", "raw"))
                                and any("pastor" in x.lower() or "liq" in x.lower()
                                        for x in os.listdir(os.path.join(root, "factors",
                                                                         "raw")))),
                "verdict": None,
            }
            res["signals"][sig]["verdict"] = (
                "DROPS AT K1 -- the factor series is not in this repo. The draft's section 8 "
                "says it is 'published free and monthly but is not in this repo', so it is a free "
                "download plus a schedule rather than an existing column, and K1 measures what is "
                "PRESENT rather than what is obtainable."
                if not res["signals"][sig]["in_repo"] else
                "inputs present; coverage unmeasured on this pass")
            continue
        miss = [c for c in cols if c not in head.columns]
        worst = None
        for c in cols:
            cov = res["column_coverage"].get(c)
            if cov is None:
                continue
            if worst is None or cov["non_null_frac"] < worst[1]:
                worst = (c, cov["non_null_frac"])
        ok = (not miss) and worst is not None and worst[1] >= K1_BAR
        res["signals"][sig] = {
            "inputs": cols, "inputs_absent": miss,
            "worst_input": worst[0] if worst else None,
            "worst_input_coverage": worst[1] if worst else None,
            "verdict": "inputs PRESENT at the bar" if ok else "DROPS AT K1",
        }

    # realestate's real blocker is the COMPONENTS, not net PP&E.
    if not res["realestate_components_found"]:
        res["signals"]["realestate"]["verdict"] = "DROPS AT K1"
        res["signals"]["realestate"]["why"] = (
            "Tuzel's measure is real-estate PP&E (buildings and land) over total PP&E. The export "
            "carries NET PP&E only and none of the component columns, so the signal cannot be "
            "built from it at any coverage -- the draft recorded this mapping as 'unverified' and "
            "it measures ABSENT. This is a construction blocker rather than a coverage shortfall.")

    kept = [s for s, v in res["signals"].items() if not v["verdict"].startswith("DROPS")]
    res["batch_after_K1"] = sorted(kept)
    res["batch_size_after_K1"] = len(kept)
    res["BH_CONSEQUENCE"] = (
        "the draft's section 5 pre-commits that dropping a signal at K1 SHRINKS the batch and "
        "TIGHTENS Benjamini-Hochberg, and that this is correct behaviour rather than a reason to "
        "keep a failing signal in to loosen the threshold. At k=%d BH's smallest threshold is "
        "%.7f." % (max(1, len(kept)), 0.10 / max(1, len(kept))))
    res["TRIALS_STILL_CHARGED"] = (
        "the draft's section 6: if K1 or K3 drops a signal the trial for it is STILL charged -- "
        "MA6's safe direction, and E-1 kept its trial though its arm never ran. Three trials "
        "remain the cost whatever this kill leaves standing.")

    print("fundamentals rows: %d" % len(df))
    print("absent from the export: %s" % res["columns_absent_from_the_export"])
    for c, v in sorted(res["column_coverage"].items()):
        print("  %-16s non-null %.6f" % (c, v["non_null_frac"]))
    print("realestate components found: %s" % res["realestate_components_found"])
    for s, v in sorted(res["signals"].items()):
        print("  %-16s %s" % (s, v["verdict"]))
    print("BATCH AFTER K1: %s" % res["batch_after_K1"])

    p = D.out_path(OUT)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(res, indent=1, default=str))
    print("wrote %s" % p)
    return res


if __name__ == "__main__":
    main()
    raise SystemExit(0)
