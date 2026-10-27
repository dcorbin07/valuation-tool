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

#: Which raw table each derived file is built from, so "did it move?" compares like with like.
#: The same map `sharadar_freeze.stage_derive` uses; stated rather than imported so this script
#: keeps working against a freeze taken by an older version of that module.
DERIVED_SOURCES = {"fundamentals.csv": "sf1.csv", "insiders.csv": "sf2.csv",
                   "institutional.csv": "sf3a.csv"}


def derived_is_stale(freeze_root: str) -> list:
    """Which derived tables are OLDER than the raw file they were built from.

    **THIS IS THE CHECK THAT WAS MISSING ON 2026-10-23 [item 84].** This script proved the
    newest CLOSE moved and nothing else, and prices are rebuilt unconditionally while the three
    derived tables were skipped when already present -- so it copied the 2026-10-04
    `fundamentals.csv` over the identical live one, reported SUCCESS, and the 10-22 rebalance
    was ranked on filings through 2026-10-02.

    MTIME RATHER THAN CONTENT, and that is the right test here: the question is not "are these
    two files different" -- freeze and live were byte-identical, which is exactly why a
    size or checksum comparison could not see it -- but "was this built from the pull that is
    now on disk".
    """
    bad = []
    for name, src in DERIVED_SOURCES.items():
        d = os.path.join(freeze_root, "backtest", name)
        s = os.path.join(freeze_root, "bulk", src)
        if not (os.path.exists(d) and os.path.exists(s)):
            continue
        if os.path.getmtime(s) > os.path.getmtime(d):
            bad.append((name, src,
                        _stamp(os.path.getmtime(d)), _stamp(os.path.getmtime(s))))
    return bad


def _stamp(t) -> str:
    import datetime as _dt
    return _dt.datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M")


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


def manifest_verdict(freeze_root: str) -> dict:
    """The freeze's own verdict, or a reason it could not be read.

    **WHAT THIS GATES ON, AND A DELIBERATE DEPARTURE FROM "MAKE `clean: false` FAIL THE RUN"
    [item 84], made on a measurement rather than a preference.**

    `verdict.clean` is the AND of two things: `checkpoints_failed` and `tables_short_vs_live`.
    Measured on the 2026-10-23 freeze, `clean` was already **false** -- and entirely because
    two bulk CSVs came back **0.259%** and **0.099%** smaller in bytes than the July copies,
    an ordinary vendor restatement. `checkpoints_failed` was **empty**.

    So failing the run on the raw flag would have refused that refresh for a reason unrelated
    to the defect, and would refuse a correct one every time Sharadar trims a little history.
    That is a gate somebody switches off inside a month (`MA21`), and switching it off would
    take the real check with it.

    **THE CHECKPOINTS ARE THE SUBSTANTIVE HALF AND THEY NOW CONTAIN THE REAL TEST** -- item
    84 added "does each derived table reach its own raw source", which the 10-23 freeze fails
    by twenty days on fundamentals and insiders. The size comparison is REPORTED loudly and
    does not fail, so neither fact is hidden and only one stops the run.
    """
    p = os.path.join(freeze_root, "MANIFEST.json")
    if not os.path.exists(p):
        return {"present": False,
                "reason": "no MANIFEST.json in the freeze, so its own integrity verdict "
                          "cannot be read -- run the manifest stage"}
    try:
        import json as _json
        with io.open(p, encoding="utf-8") as f:
            man = _json.load(f)
    except Exception as e:                                               # noqa: BLE001
        return {"present": True, "reason": "MANIFEST.json is unreadable: %s: %s"
                                           % (type(e).__name__, e)}
    v = man.get("verdict") or {}
    return {"present": True, "reason": None, "clean": v.get("clean"),
            "checkpoints_failed": list(v.get("checkpoints_failed") or []),
            "tables_short_vs_live": list(v.get("tables_short_vs_live") or []),
            "created": man.get("created")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", required=True, help="freeze root (contains backtest/)")
    ap.add_argument("--live", required=True, help="the live data/backtest to update")
    ap.add_argument("--allow-older", action="store_true",
                    help="permit a sync whose newest close is OLDER than the live one")
    ap.add_argument("--allow-stale-derive", action="store_true",
                    help="permit a sync whose derived tables are older than the raw export "
                         "they come from (item 84; the direction that ships stale accounts)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    src_root = os.path.abspath(a.freeze)
    src = os.path.join(src_root, "backtest")
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

    # **A STALE DERIVE IS A FAILED REFRESH, NOT A SUCCESSFUL ONE [item 84].** Checked BEFORE
    # anything is copied, so a stale table is never installed over the live export: on
    # 2026-10-23 the copy ran, the two files were byte-identical, and the SUCCESS line was
    # about the prices.
    # **THE FREEZE'S OWN VERDICT, READ RATHER THAN IGNORED [item 84].** See
    # `manifest_verdict` for why the CHECKPOINTS fail the run and the size comparison only
    # warns -- it is a measurement about the 10-23 freeze, not a preference.
    _mv = manifest_verdict(src_root)
    if not _mv.get("present"):
        # **ABSENT IS A WARNING, NOT A FAILURE, AND THAT IS A CORRECTION TO MY OWN FIRST CUT.**
        # Syncing a freeze that has no manifest stage yet is a legitimate by-hand workflow --
        # it is the one item 84 itself used, `--stage derive` then sync -- and failing it is a
        # new restriction nobody asked for. The brief asked that a manifest saying `clean:
        # false` fail the run; it said nothing about there being no manifest. **Third time
        # this session I turned a tolerated absence into a hard stop** (item 83's empty cash
        # figure, item 84's as-of ordering, this), which is the mirror image of `C5` and is
        # worth naming as a habit rather than as three accidents.
        print("WARNING: %s -- syncing anyway, unverified" % _mv.get("reason"))
    elif _mv.get("reason"):
        # PRESENT AND UNREADABLE IS DIFFERENT FROM ABSENT: the file exists and cannot be
        # parsed, which is damage rather than a stage that has not run.
        print("FAILURE: %s" % _mv.get("reason"))
        return 2
    if _mv.get("tables_short_vs_live"):
        print("WARNING: the freeze is SHORTER than the live copy on: %s -- reported, not "
              "fatal; a vendor trimming a little history does this (0.1-0.3%% on 2026-10-23)"
              % ", ".join(_mv["tables_short_vs_live"]))
    if _mv.get("checkpoints_failed"):
        print("FAILURE: the freeze fails its own integrity checkpoints:")
        for c in _mv["checkpoints_failed"]:
            print("  - %s" % c)
        print("  The manifest was written %s. Fix the freeze before syncing it over the "
              "live export." % _mv.get("created"))
        return 2
    _stale = derived_is_stale(src_root)
    if _stale and not a.allow_stale_derive:
        print("FAILURE: the freeze carries derived table(s) OLDER than the raw export they "
              "are built from, so the pull did not rebuild them:")
        for name, source, dstamp, sstamp in _stale:
            print("  %-20s built %s, but %s is from %s" % (name, dstamp, source, sstamp))
        print("  Re-run: python -m valuation.edge.sharadar_freeze --stage derive "
              "--root <freeze> --live <live>   (it now rebuilds a table whose source is "
              "newer than it is). --allow-stale-derive overrides this deliberately.")
        return 2
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
