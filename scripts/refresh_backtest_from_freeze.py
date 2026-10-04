# -*- coding: utf-8 -*-
"""Sync a Sharadar freeze's `backtest/` into the live `data/backtest`, and PROVE it moved.

ONE definition of this sync, called by `refresh_sharadar.bat` and usable by hand. The `.bat`
stays thin on purpose: a batch file that reimplements a copy is a second implementation nobody
tests, and this one has to be right on the evening of a rebalance.

WHY IT IS NOT A BARE `xcopy`:

  * **It reports the newest close BEFORE and AFTER.** The whole point of the refresh is that the
    panel can see the latest price; a copy that succeeds while the newest close does not move is
    a failure wearing a success's clothes, and the exit code says so.
  * **It will not mix two vintages.** The live `prices/` directory is made to MATCH the freeze
    rather than become a union of both: a price file for a name the new export dropped would
    otherwise sit there forever, point-in-time-looking and stale. Files not in the freeze are
    reported and removed, never silently left.
  * **It refuses to run backwards.** If the freeze's newest close is OLDER than the live one the
    sync is a downgrade, so it aborts untouched. `--allow-older` exists for a deliberate
    rollback and says what it is.
  * **Nothing is deleted before the copy succeeds.** The freeze is read-only once locked and is
    itself the backup, but the ordering still matters: copy first, prune second.
"""
from __future__ import annotations

import argparse
import io
import os
import shutil
import sys

DERIVED = ("fundamentals.csv", "insiders.csv", "institutional.csv")


def newest_close(prices_dir: str, sample: int = 400) -> str:
    """The newest date any price file carries. Sampled, because 3,700 files is slow and the
    MAXIMUM over a sample of that size cannot be older than the true maximum by a trading day
    on a universe this wide -- and the figure is a freshness check, not a published number."""
    if not os.path.isdir(prices_dir):
        return ""
    files = sorted(os.listdir(prices_dir))
    step = max(1, len(files) // sample)
    best = ""
    for f in files[::step]:
        p = os.path.join(prices_dir, f)
        try:
            with io.open(p, encoding="utf-8", errors="replace") as fh:
                head = fh.readline()
                last = ""
                for last in fh:
                    pass
            if not last:
                continue
            # the derived price files are `date,close` sorted ascending; the header names the
            # columns, so the date column is read rather than assumed to be first.
            cols = [c.strip().lower() for c in head.strip().split(",")]
            i = cols.index("date") if "date" in cols else 0
            d = last.strip().split(",")[i][:10]
            if d > best:
                best = d
        except Exception:                                   # noqa: BLE001
            continue
    return best


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", required=True, help="freeze root (contains backtest/)")
    ap.add_argument("--live", required=True, help="the live data/backtest to update")
    ap.add_argument("--allow-older", action="store_true",
                    help="permit a sync whose newest close is OLDER than the live one")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    src = os.path.join(os.path.abspath(a.freeze), "backtest")
    dst = os.path.abspath(a.live)
    if not os.path.isdir(src):
        print("FAILURE: no backtest/ inside the freeze at %s" % src)
        return 2

    s_new = newest_close(os.path.join(src, "prices"))
    l_new = newest_close(os.path.join(dst, "prices"))
    print("freeze newest close: %s" % (s_new or "NONE"))
    print("live   newest close: %s" % (l_new or "NONE"))
    if not s_new:
        print("FAILURE: the freeze carries no readable close date")
        return 2
    if l_new and s_new < l_new and not a.allow_older:
        print("FAILURE: the freeze is OLDER than the live data (%s < %s). Refusing to go "
              "backwards; pass --allow-older for a deliberate rollback." % (s_new, l_new))
        return 2

    if a.dry_run:
        print("dry run: would sync %s -> %s" % (src, dst))
        return 0

    os.makedirs(os.path.join(dst, "prices"), exist_ok=True)
    for f in DERIVED:
        p = os.path.join(src, f)
        if not os.path.exists(p):
            print("FAILURE: the freeze is missing %s" % f)
            return 2
        shutil.copy2(p, os.path.join(dst, f))
        print("  copied %-20s %7.1f MB" % (f, os.path.getsize(p) / 1e6))

    sp, dp = os.path.join(src, "prices"), os.path.join(dst, "prices")
    have = set(os.listdir(sp))
    n = 0
    for f in sorted(have):
        shutil.copy2(os.path.join(sp, f), os.path.join(dp, f))
        n += 1
    print("  copied %d price files" % n)

    # PRUNE SECOND, and report. A live file the new export dropped would otherwise sit there
    # looking point-in-time and be stale forever.
    stale = [f for f in os.listdir(dp) if f not in have]
    for f in stale:
        os.remove(os.path.join(dp, f))
    print("  pruned %d price file(s) the new export no longer carries%s"
          % (len(stale), (": " + ", ".join(sorted(stale)[:8]) +
                          (" ..." if len(stale) > 8 else "")) if stale else ""))

    after = newest_close(dp)
    print("live newest close after sync: %s" % after)
    if after != s_new:
        print("FAILURE: after the sync the live newest close is %s, not the freeze's %s"
              % (after, s_new))
        return 2
    if l_new and after == l_new:
        print("FAILURE: the sync completed but the newest close did NOT move (still %s). The "
              "export carried nothing newer." % after)
        return 1
    print("SUCCESS: data/backtest now holds closes through %s (was %s)" % (after, l_new or "none"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
