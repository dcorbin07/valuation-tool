"""At-a-glance status of the unattended ThetaData cache mining.

    python mine_status.py

Read-only. Safe to run while the miner is going.
"""
import json
import os
from collections import Counter

REPO = r"C:\Users\donni\Downloads\valuation-tool"
OPTROOT = os.path.join(REPO, "data", "options")
MANIFEST = os.path.join(OPTROOT, "cache_manifest.json")
PROGRESS = os.path.join(OPTROOT, "MINING_PROGRESS.txt")
TARGET = 1000


def human(nbytes):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{u}"
        nbytes /= 1024
    return f"{nbytes:.1f}PB"


def main():
    if not os.path.exists(MANIFEST):
        print("No manifest yet - the miner has not finished its first name.")
        return
    m = json.load(open(MANIFEST, encoding="utf-8"))
    c = Counter(v.get("status") for v in m.values())
    done = c.get("complete", 0) + c.get("partial", 0)
    print(f"NAMES   {done} of {TARGET} cached "
          f"({c.get('complete', 0)} complete, {c.get('partial', 0)} partial, "
          f"{c.get('skipped_thin', 0)} skipped as too illiquid, "
          f"{c.get('no_data_in_range', 0)} with no option data in range)")
    # How far the QUEUE got, which is the question a killed run leaves behind. A name with no
    # manifest entry has never been judged; the miner walks the universe in market-cap order,
    # so the count of unjudged names is what remains.
    print(f"QUEUE   {len(m)} of {TARGET} names judged, {TARGET - len(m)} never reached")

    partial = {k: v.get("gaps") for k, v in m.items() if v.get("status") == "partial"}
    if partial:
        print(f"PARTIAL {', '.join(f'{k}{v}' for k, v in list(partial.items())[:8])}"
              + (" ..." if len(partial) > 8 else ""))
    thin = [k for k, v in m.items() if v.get("status") == "skipped_thin"]
    if thin:
        print(f"THIN    {', '.join(thin[:12])}" + (" ..." if len(thin) > 12 else ""))

    # disk
    total = nfiles = 0
    for root, _dirs, files in os.walk(OPTROOT):
        for fn in files:
            if fn.endswith(".pkl"):
                nfiles += 1
                try:
                    total += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
    print(f"DISK    {nfiles:,} year-files, {human(total)}")

    # DEPTH. The 90 -> 200 DTE widening is partial by design, so any claim about the 90-200
    # band has to say which names it covers. Printing it here means nobody has to go looking.
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from valuation.edge.theta_bulk import (LEGACY_MAX_DTE, MAX_DTE,
                                               alias_overlap_conflicts,
                                               collapsed_year_suspects, depth_report,
                                               reused_ticker_suspects)
        rep = depth_report()
        print(f"DEPTH   {rep['by_depth']} symbol-years by DTE ceiling; "
              f"{len(rep['names_fully_deep'])} names fully at {MAX_DTE}, "
              f"{len(rep['names_mixed'])} mixed, {rep['n_names']} names total")
        print(f"        rankable to {LEGACY_MAX_DTE} DTE across ALL names; past that, only "
              f"the {len(rep['names_fully_deep'])} deep ones -- a cross-sectional statistic "
              f"in the {LEGACY_MAX_DTE}-{MAX_DTE} band compares them against names with no "
              f"such rows at all.")
        # Alias provenance: which symbol-years hold another ticker's rows, and whether any
        # mapping still overlaps its successor (the WBD <- T failure).
        borrowed = []
        for root, _d, files in os.walk(OPTROOT):
            borrowed += [f[:-len(".pkl.alias")] for f in files if f.endswith(".pkl.alias")]
        conflicts = alias_overlap_conflicts()
        print(f"ALIAS   {len(borrowed)} symbol-years supplied by an alias"
              + (f" ({', '.join(sorted(borrowed)[:8])}"
                 + (" ..." if len(borrowed) > 8 else "") + ")" if borrowed else "")
              + f"; overlap conflicts: {conflicts or 'none'}")
        if conflicts:
            print("        *** AN ALIAS OVERLAPS ITS SUCCESSOR. That is how ~1.00M rows of "
                  "AT&T were cached under WBD. Investigate before trusting those names. ***")
        # REUSED TICKERS. Neither check above can see these: no alias is involved, and no
        # alias could fix them either -- a fallback only fires on an EMPTY span, and a ticker
        # that changed hands answers with the new holder's chains instead of nothing.
        reused = reused_ticker_suspects()
        collapsed = collapsed_year_suspects()
        hole_bits = ", ".join(f"{k} {v['hole']}" for k, v in sorted(reused.items()))
        coll_bits = ", ".join(f"{k} {[x['year'] for x in v]}"
                              for k, v in sorted(collapsed.items()))
        print(f"REUSE   {len(reused)} name(s) with an interior hole"
              + (f" ({hole_bits})" if hole_bits else "")
              + f"; {len(collapsed)} with a collapsed year"
              + (f" ({coll_bits})" if coll_bits else ""))
        if reused or collapsed:
            print("        Both are SCREENS, not verdicts -- a hole can be an outage and a "
                  "thin year can be real. Confirm by strike range, which tracks the "
                  "underlying's price level: COR steps 103 -> 195 across its hole (CoreSite "
                  "Realty -> Cencora) and META-2021 holds a $15 name at 9,398 rows between "
                  "years of 247k and 172k at strikes 130-350.")
    except Exception as e:                                               # noqa: BLE001
        print(f"DEPTH   unavailable ({type(e).__name__}: {e})")

    # Only names actually CACHED. Including skipped_thin ones made a correctly-rejected
    # name look like the thinnest one kept ("thinnest kept 0").
    live = [v for v in m.values()
            if v.get("tradeable_per_day") is not None
            and v.get("status") in ("complete", "partial")]
    if live:
        tp = sorted(v["tradeable_per_day"] for v in live)
        print(f"LIQUIDITY  median {tp[len(tp)//2]:.0f} tradeable contracts/day; "
              f"thinnest kept {tp[0]:.0f}, richest {tp[-1]:.0f}")

    if os.path.exists(PROGRESS):
        try:
            lines = [l for l in open(PROGRESS, encoding="utf-8", errors="replace")
                     .read().splitlines() if l.strip()]
            print("\nlast progress lines:")
            for l in lines[-3:]:
                print("  " + l[:140])
        except OSError:
            pass


if __name__ == "__main__":
    main()
