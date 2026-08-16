#!/usr/bin/env python3
"""
check_lanes.py — is this set of audit items safe to run concurrently?

    python check_lanes.py B1 B7 C4 X3
    python check_lanes.py --lanes            # print the precomputed safe lanes
    python check_lanes.py --ready B1 B3      # what unblocks if these land
    python check_lanes.py --file B1          # what else touches B1's files

Reads valquo_audit_items.json (same directory).

Two kinds of collision are reported:
  HARD  - two items modify the same file. Textual merge conflict is likely.
  SOFT  - two items modify files where one imports the other. The merge will be
          clean and the build may still break. These need a shared owner or a
          landing order, not parallel lanes.
"""
import json, sys, itertools, pathlib, collections

HERE = pathlib.Path(__file__).parent
ITEMS = json.loads((HERE / "valquo_audit_items.json").read_text())

sys.path.insert(0, str(HERE / "scripts"))
import import_graph

# Import edges: "A imports B"  ->  editing B can break A.
#
# DERIVED, NOT TYPED (master audit MA60, 2026-08-15). This was a hand-maintained
# dict, and the audit's charge that it had "admitted gaps" understated it.
# Measured against the real graph on the day it was replaced:
#
#     hand-typed : 13 keys,  40 edges
#     derived    : 118 keys, 546 edges
#
# 105 files with real imports were absent from it entirely, and 12 of its 13
# keys were wrong. The failure that matters is not the absences -- it is that
# it was wrong in a direction that reads as safe. Four options modules were
# recorded as importing `statistics.py` when they actually import
# `options_stats.py`, so a SOFT collision between two options items fired
# against a file they do not share and never fired against the file they do.
# `screen.py` was recorded with 3 edges against a real 15.
#
# A lane checker whose graph is stale reports "safe to run in parallel" for
# work that is not, which is the one answer it exists to get right.
IMPORTS = import_graph.graph()

def w(i):   return set(ITEMS[i]["modifies"])
def soft(a, b):
    """does editing b's files endanger a's files (or vice versa) via imports?"""
    hits = set()
    for x, y in itertools.product(w(a), w(b)):
        if y in IMPORTS.get(x, ()) or x in IMPORTS.get(y, ()):
            hits.add((x, y))
    return hits

def unknown(ids):
    bad = [i for i in ids if i not in ITEMS]
    if bad:
        sys.exit(f"unknown item id(s): {', '.join(bad)}")

def check(ids):
    unknown(ids)
    hard, softs = [], []
    for a, b in itertools.combinations(sorted(ids), 2):
        ov = w(a) & w(b)
        if ov: hard.append((a, b, sorted(ov)))
        else:
            s = soft(a, b)
            if s: softs.append((a, b, sorted(s)))
    # unmet dependencies
    unmet = [(i, d) for i in ids for d in ITEMS[i]["depends_on"] if d not in ids]

    for i in sorted(ids):
        m = ITEMS[i]
        tag = "read-only" if m["readonly"] else f"{len(m['modifies'])} file(s)"
        print(f"  {i:5s} {m['title'][:52]:54s} {tag}")
    print()
    if hard:
        print("HARD COLLISIONS — same file, do not run in parallel:")
        for a, b, f in hard:
            print(f"  {a} x {b}: {', '.join(f)}")
    if softs:
        print("SOFT COLLISIONS — import-coupled, clean merge but possible break:")
        for a, b, f in softs:
            for x, y in f: print(f"  {a} x {b}: {x} <-> {y}")
    if unmet:
        print("UNMET DEPENDENCIES (must have landed already):")
        for i, d in sorted(set(unmet)):
            print(f"  {i} needs {d} ({ITEMS[d]['title']})")
    if not (hard or softs or unmet):
        print("SAFE — disjoint write sets, no import coupling, all dependencies met.")
    return 1 if (hard or unmet) else 0

TERRITORY = [
 ("PANEL",      ["valuation/edge/fundamental_panel.py","valuation/edge/data_providers.py"]),
 ("FACTORS",    ["valuation/screener/factors.py","valuation/screener/settings.py",
                 "valuation/screener/cross_sectional.py","valuation/screener/screen.py",
                 "valuation/config.py"]),
 ("OPT-ENGINE", ["valuation/edge/options_universe.py","valuation/edge/options_backtest.py",
                 "valuation/edge/options_fill.py","valuation/edge/options_signals_v2.py",
                 "valuation/edge/options_autopsy.py","valuation/edge/options_exit.py",
                 "valuation/edge/blackscholes.py"]),
 ("OPT-DATA",   ["valuation/edge/theta_bulk.py","valuation/edge/thetadata_provider.py",
                 "valuation/edge/options_greeks.py"]),
 ("LIVE",       ["valuation/edge/paper_track.py","valuation/edge/paper_broker.py",
                 "valuation/edge/options_tracker.py","valuation/edge/options_live.py",
                 "valuation/edge/options_sizing.py","valuation/edge/options_vrp_portfolio.py"]),
 ("DATASETS",   ["valuation/edge/bulk.py","valuation/edge/short_interest.py",
                 "valuation/research/lazy_prices_ic.py"]),
 ("STATS",      ["valuation/edge/statistics.py"]),
 ("OPTIONS-BOT",["options-bot/"]),
 ("INFRA",      [".github/","tests/","CLAUDE.md","valuation/web/"]),
]

def territories(i):
    t = set()
    for f in w(i):
        for name, pats in TERRITORY:
            if any(f == q or f.startswith(q) for q in pats):
                t.add(name); break
        else:
            t.add("?" + f)
    return t or {"FREE"}

def lanes():
    by = {}
    for i in ITEMS:
        ts = territories(i)
        key = "FREE" if ts == {"FREE"} else (list(ts)[0] if len(ts) == 1 else "CROSS")
        by.setdefault(key, []).append(i)
    return by

def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "--lanes":
        by = lanes()
        order = ["FREE","OPTIONS-BOT","INFRA","OPT-DATA","LIVE","DATASETS","STATS",
                 "OPT-ENGINE","FACTORS","PANEL","CROSS"]
        for k in order:
            if k not in by: continue
            L = sorted(by[k])
            print(f"\n{k}  ({len(L)} items)")
            print("  " + " ".join(L))
            if k == "CROSS":
                for i in L:
                    print(f"    {i}: {' + '.join(sorted(territories(i)))}")
        return
    if a[0] == "--file":
        unknown(a[1:])
        for i in a[1:]:
            for f in sorted(w(i)):
                others = sorted(k for k in ITEMS if f in w(k) and k != i)
                print(f"{f}\n  also modified by: {' '.join(others) or '(nobody)'}")
        return
    if a[0] == "--ready":
        unknown(a[1:])
        done = set(a[1:])
        for k, v in sorted(ITEMS.items()):
            if k not in done and v["depends_on"] and set(v["depends_on"]) <= done:
                print(f"  {k:5s} {v['title']}")
        return
    sys.exit(check(a))

if __name__ == "__main__":
    main()
