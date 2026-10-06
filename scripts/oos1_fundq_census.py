"""A read-only census of the banked `comp_fundq`. ZERO TRIALS, no construction scored.

Measures what OOS1's K3 branch needs and what the draft left unmeasured: `rdq` coverage INSIDE
the 1972-1998 holdout era specifically, not the 1972-2008 figure the server returned. A coverage
figure is a fact about what data exists -- the `S25`/`MB15`/`MB3` zero-trial class -- and under
`MB1-SEL` a pre-outcome control can only ever BLOCK a design, never produce a finding, so it adds
no degree of freedom and may be read before the holdout is opened. **No return is computed and no
construction is scored anywhere in this file.**
"""
import glob
import io
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

RAW = r"D:\wrds"


def _data_root():
    """The PRIMARY populated data root, never the worktree's empty one.

    `E-5` recorded this failure twice: an artifact written by a worktree-run script does not
    survive the worktree, and every register reading a prior item's artifact inherits that.
    """
    d = REPO
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "data", "free_analysis")):
            return os.path.join(d, "data", "free_analysis")
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    raise SystemExit("REFUSING: no populated data root found")


OUT = os.path.join(_data_root(), "OOS1_FUNDQ_CENSUS.json")
ERAS = {"holdout_1972_1998": (1972, 1998),
        "r1_sharadar_1999_2008": (1999, 2008),
        "overlap_2009_2026": (2009, 2026)}
RULE = 0.70

paths = sorted(glob.glob(os.path.join(RAW, "comp_fundq", "comp_fundq_*.pkl")))
print("chunks on disk: %d" % len(paths))

KEEP = ["datadate", "rdq", "gvkey", "cusip", "indfmt", "datafmt", "consol", "popsrc",
        "curcdq", "atq", "revtq", "ceqq", "piq", "xrdq", "cogsq", "oancfy", "capxy",
        "cshoq", "oiadpq", "txtq", "icaptq", "dlttq", "dlcq", "gpq", "sstky", "prstkcy"]

parts = []
for p in paths:
    d = pd.read_pickle(p, compression="gzip")
    parts.append(d[[c for c in KEEP if c in d.columns]])
f = pd.concat(parts, ignore_index=True)
print("rows banked: %s | cols %d" % ("{:,}".format(len(f)), f.shape[1]))

art = {"item": "comp_fundq census (zero trials, no construction scored)",
       "chunks": len(paths), "rows_banked": int(len(f)),
       "nonnull_rule": RULE, "eras": {}}

n0 = len(f)
for col, val in (("indfmt", "INDL"), ("datafmt", "STD"), ("consol", "C"), ("popsrc", "D")):
    if col in f.columns:
        f = f[f[col] == val]
art["rows_after_standard_filter"] = int(len(f))
art["rows_dropped_by_standard_filter"] = int(n0 - len(f))
print("after INDL/STD/C/D filter: %s (dropped %s)"
      % ("{:,}".format(len(f)), "{:,}".format(n0 - len(f))))

n1 = len(f)
usd = f[f["curcdq"] == "USD"] if "curcdq" in f.columns else f
art["rows_usd"] = int(len(usd))
art["rows_dropped_non_usd"] = int(n1 - len(usd))
print("USD only: %s (dropped %s)" % ("{:,}".format(len(usd)), "{:,}".format(n1 - len(usd))))

usd = usd.copy()
usd["datadate"] = pd.to_datetime(usd["datadate"], errors="coerce")
usd["rdq"] = pd.to_datetime(usd["rdq"], errors="coerce")
usd = usd.dropna(subset=["datadate"])
usd["yr"] = usd["datadate"].dt.year

FIELDS = ["atq", "revtq", "ceqq", "piq", "xrdq", "cogsq", "oancfy", "capxy", "cshoq",
          "oiadpq", "txtq", "icaptq", "dlttq", "dlcq", "gpq", "sstky", "prstkcy"]

print("\n%-26s %10s %9s %9s %9s" % ("era", "rows", "rdq", "gvkeys", "rdq<dd"))
for name, (lo, hi) in ERAS.items():
    e = usd[(usd["yr"] >= lo) & (usd["yr"] <= hi)]
    if not len(e):
        art["eras"][name] = {"rows": 0, "note": "no banked rows"}
        print("%-26s %10d  -- no banked rows" % (name, 0))
        continue
    share = float(e["rdq"].notna().mean())
    bad = int((e["rdq"].notna() & (e["rdq"] < e["datadate"])).sum())
    cov = {c: round(float(e[c].notna().mean()), 4) for c in FIELDS if c in e.columns}
    art["eras"][name] = {
        "years": [lo, hi], "rows": int(len(e)), "gvkeys": int(e["gvkey"].nunique()),
        "rdq_nonnull_share": round(share, 6),
        "rdq_clears_70pct_rule": bool(share >= RULE),
        "rows_rdq_before_datadate": bad,
        "field_nonnull": cov,
        "fields_below_rule": sorted([c for c, v in cov.items() if v < RULE]),
    }
    print("%-26s %10s %8.4f %9d %9d" % (name, "{:,}".format(len(e)), share,
                                        e["gvkey"].nunique(), bad))

print("\nrdq non-null by 5-year block, holdout era only:")
h = usd[(usd["yr"] >= 1972) & (usd["yr"] <= 1998)]
blocks = {}
for lo in range(1970, 2000, 5):
    b = h[(h["yr"] >= lo) & (h["yr"] < lo + 5)]
    if len(b):
        s = round(float(b["rdq"].notna().mean()), 4)
        blocks["%d-%d" % (lo, lo + 4)] = {"rows": int(len(b)), "rdq": s}
        print("  %d-%d  rows %9s  rdq %.4f" % (lo, lo + 4, "{:,}".format(len(b)), s))
art["holdout_rdq_by_block"] = blocks

if "holdout_1972_1998" in art["eras"] and art["eras"]["holdout_1972_1998"].get("rows"):
    hh = art["eras"]["holdout_1972_1998"]
    print("\nfields BELOW the %.0f%% rule in the holdout era: %s"
          % (RULE * 100, hh["fields_below_rule"] or "none"))

with io.open(OUT, "w", encoding="utf-8") as fh:
    json.dump(art, fh, indent=2, sort_keys=True, default=str)
print("\nwrote %s" % OUT)
