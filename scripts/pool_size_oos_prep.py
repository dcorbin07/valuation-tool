# -*- coding: utf-8 -*-
"""`POOL-SIZE` part (b) STAGE 2a — prepare a FULL-UNIVERSE pre-2009 export. ZERO TRIALS.

Register §4: part (b) must be built from the freeze's **full raw** tables and **not** from
`data/backtest`, which is selected on 2026 size. This writes a `backtest`-shaped export covering
**every** ticker priced in 1999-2008, so the shipped `build_fundamental_panel` can be pointed at
it — **one** panel implementation, not a second one.

**WHAT IT WRITES, AND WHAT IT DELIBERATELY DOES NOT.**

  * `prices/<TICKER>.csv` — `date,close` from SEP's **`closeadj`**, because that is what the
    live export carries (checked: `data/backtest/prices/AAPL.csv` starts 1997-12-31 at 0.098,
    which is split-adjusted, not the ~$13 unadjusted price).
  * `fundamentals.csv` — SF1 **ARQ** rows, header byte-identical to the live file's.
  * **NOTHING for `daily` or `actions`.** Those bulk caches are ALREADY full-universe and
    already reach into the window — measured: `daily.pkl` holds **17,421** tickers from
    **1998-12-01** with 8,061 covered by 1999-12-31, and `actions.pkl` holds 31,937. Rebuilding
    them would be a second copy of data that already exists, and **overwriting the shared ones
    would break every 2009-2026 panel build in the repo.** The runner points `_bulk_dir` at the
    existing cache instead.

**THE CUTOFF IS A PROPERTY OF THE EXPORT, NOT OF A FLAG.** Only rows dated on or before
`CUT` are written, so the builder's own calendar naturally lands inside 1999-2008 and there is no
window parameter anyone can forget to pass. Post-cutoff rows in the *shared* daily cache are
harmless: the panel selects the last row at or before each scoring date, so a 2010 row can never
be read when scoring 2003 -- the same point-in-time rule the live panel uses.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
import zipfile

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

CUT = "2008-12-31"
WINDOW_FROM = "1999-01-01"
FLUSH_ROWS = 2_000_000           # bounds memory; files are appended, never rewritten


def _zip_reader(raw, prefix):
    p = [os.path.join(raw, f) for f in os.listdir(raw) if f.startswith(prefix)][0]
    z = zipfile.ZipFile(p)
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    return z, csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace"))


def prep_prices(raw, out_dir):
    """One SEP pass. Writes `date,close` (from closeadj) for every ticker with an in-window row.

    Two passes would be cleaner but SEP is 45M rows; instead rows are buffered and appended in
    batches, so memory is bounded and a ticker's file is built up across flushes. The header is
    written once, on a file's first touch.
    """
    os.makedirs(out_dir, exist_ok=True)
    z, r = _zip_reader(raw, "SHARADAR_SEP_")
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    ci = head.index("closeadj") if "closeadj" in head else head.index("close")

    buf, seen, n_buf, rows, kept = {}, set(), 0, 0, 0
    in_window = set()
    t0 = time.time()

    def flush():
        nonlocal buf, n_buf
        for t, lines in buf.items():
            p = os.path.join(out_dir, "%s.csv" % t)
            new = t not in seen
            with io.open(p, "a", encoding="utf-8", newline="") as fh:
                if new:
                    fh.write("date,close\n")
                    seen.add(t)
                fh.write("".join(lines))
        buf, n_buf = {}, 0

    for row in r:
        rows += 1
        d = row[di][:10]
        if d > CUT:
            continue
        t = row[ti].upper()
        c = row[ci]
        if not c:
            continue
        if d >= WINDOW_FROM:
            in_window.add(t)
        buf.setdefault(t, []).append("%s,%s\n" % (d, c))
        n_buf += 1
        kept += 1
        if n_buf >= FLUSH_ROWS:
            flush()
            print("    sep %dM rows read, %d kept, %d files, %.0fs"
                  % (rows / 1e6, kept, len(seen), time.time() - t0), flush=True)
    flush()
    z.close()

    # a ticker with history but NO in-window row is dead weight; remove it so the universe the
    # provider derives is the one the window can actually score.
    dropped = 0
    for t in sorted(seen - in_window):
        try:
            os.remove(os.path.join(out_dir, "%s.csv" % t))
            dropped += 1
        except OSError:
            pass
    return {"sep_rows": rows, "rows_written": kept, "files": len(seen) - dropped,
            "files_dropped_no_in_window_row": dropped, "price_col": head[ci]}


def prep_benchmark(raw, out_dir, tickers=("SPY",)):
    """The benchmark comes from SFP, NOT from SEP, and the builder caught that by REFUSING.

    A full-universe export built from SEP alone has no benchmark: SEP is equities and SPY is a
    fund. Measured on this freeze -- **SEP carries 0 SPY rows and SFP carries 7,233 from
    1997-12-31**. The first build stopped with `benchmark 'SPY' unavailable (0 days) ... cannot
    build the panel`, which is the right behaviour: a panel with no benchmark would have
    produced excess returns against nothing, and nothing would have raised.
    """
    z, r = _zip_reader(raw, "SHARADAR_SFP_")
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    ci = head.index("closeadj") if "closeadj" in head else head.index("close")
    want = {t.upper() for t in tickers}
    rows = {t: [] for t in want}
    for row in r:
        t = row[ti].upper()
        if t not in want:
            continue
        d = row[di][:10]
        if d > CUT or not row[ci]:
            continue
        rows[t].append((d, row[ci]))
    z.close()
    out = {}
    for t, rs in rows.items():
        rs.sort()
        with io.open(os.path.join(out_dir, "%s.csv" % t), "w", encoding="utf-8",
                     newline="") as fh:
            fh.write("date,close\n")
            for d, c in rs:
                fh.write("%s,%s\n" % (d, c))
        out[t] = {"rows": len(rs), "first": rs[0][0] if rs else None,
                  "last": rs[-1][0] if rs else None}
    return out


def prep_fundamentals(raw, out_path):
    """One SF1 pass. ARQ rows with `datekey` on or before the cutoff, header unchanged."""
    z, r = _zip_reader(raw, "SHARADAR_SF1_")
    head = next(r)
    di = head.index("datekey")
    dim = head.index("dimension") if "dimension" in head else None
    rows = kept = 0
    tick = set()
    ti = head.index("ticker")
    with io.open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(head)
        for row in r:
            rows += 1
            if dim is not None and row[dim] != "ARQ":
                continue
            d = (row[di] or "")[:10]
            if not d or d > CUT:
                continue
            w.writerow(row)
            tick.add(row[ti].upper())
            kept += 1
    z.close()
    return {"sf1_rows": rows, "arq_rows_written": kept, "tickers": len(tick)}


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    raw = os.path.join(data, "backtest_freeze_2026-10", "raw")
    if not os.path.isdir(raw):
        print("REFUSING: no raw freeze at %s" % raw)
        return 2

    root = os.path.join(data, "oos1999", "backtest")
    os.makedirs(root, exist_ok=True)
    print("preparing a FULL-UNIVERSE export cut at %s -> %s" % (CUT, root), flush=True)

    print("  fundamentals (SF1 ARQ) ...", flush=True)
    f = prep_fundamentals(raw, os.path.join(root, "fundamentals.csv"))
    print("    %s" % json.dumps(f), flush=True)

    print("  prices (SEP closeadj) ...", flush=True)
    p = prep_prices(raw, os.path.join(root, "prices"))
    print("    %s" % json.dumps(p), flush=True)

    print("  benchmark (SFP -- SPY is a FUND and is not in SEP) ...", flush=True)
    b = prep_benchmark(raw, os.path.join(root, "prices"))
    print("    %s" % json.dumps(b), flush=True)

    res = {"item": "POOL-SIZE", "part": "b stage 2a export prep", "trials": 0,
           "cut": CUT, "window_from": WINDOW_FROM, "export_root": root,
           "fundamentals": f, "prices": p, "benchmark": b,
           "bulk_reused": "data/bulk/prepared (daily 17,421 tickers from 1998-12-01; actions "
                          "31,937) -- NOT rebuilt and NOT overwritten; the runner points "
                          "_bulk_dir at it",
           "note": "the cutoff is a property of the EXPORT, so the builder's own calendar lands "
                   "inside the window with no flag to forget"}
    fa = os.path.join(data, "free_analysis")
    json.dump(res, io.open(os.path.join(fa, "POOL_SIZE_OOS_PREP.json"), "w", encoding="utf-8"),
              indent=2)
    print("\nwrote %s" % os.path.join(fa, "POOL_SIZE_OOS_PREP.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
