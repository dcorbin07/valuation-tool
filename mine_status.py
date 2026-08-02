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
          f"{c.get('skipped_thin', 0)} skipped as too illiquid)")

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
