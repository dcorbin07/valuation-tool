# -*- coding: utf-8 -*-
"""`UNIVERSE-BIAS` part 1 — how biased is `data/backtest`'s universe for 2009-2026? ZERO TRIALS.

`POOL-SIZE` established that `data/backtest` is selected on **2026** market cap:
`sharadar_freeze._fresh_universe` ranks the TICKERS snapshot by today's `scalemarketcap`, keeps
`scale >= 2`, takes the top **3,000**, and unions the live set. That is a PRESENT-DAY property,
so it can flatter small-cap and wider-pool results **for 2009-2026 too**, not only before 2009.

This measures the bias directly, against the freeze's **full raw** SEP/SF1/SFP under the **same
filter** the provider applies (a name counts if it has SF1 ARQ coverage, which is what
`WRDSProvider.universe` derives its universe from).

**THE SHARP QUESTION IS THE THIRD ONE.** Names per date and delisted share describe the gap;
what makes it a *bias* rather than a *gap* is whether the missing names are **non-random in
exactly the direction that matters** — small at the start and dead by the end. A name that was a
micro-cap in 2009 and delisted in 2013 has no 2026 market cap at all, so the top-3,000 ranking
cannot see it, and a wider-pool arm that never holds it is never charged for it.

**ZERO TRIALS, `FACTS` class.** No hypothesis, no bar, no verdict against a threshold -- facts
about what two universes contain (`S25` / `MB3` / `W-28-PULL` / `PANEL-EXT-RECHECK` class).

Streams the zips; nothing is extracted and nothing licensed leaves `data/`.
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

WINDOW = ("2009-01-01", "2026-10-02")
#: "small in 2009" -- the panel's own micro-cap line, the one POOL-SIZE's diagnostics used.
SMALL_2009 = 300e6
#: a name is "dead" if its last close is more than a year before the window's end.
DEAD_BEFORE = "2025-10-02"
#: the per-date sample. A full per-date census over 20,997 tickers x 69 dates is not needed to
#: see the shape, and the dates are the panel's own quarterly cadence.
SAMPLE_DATES = ("2009-01-15", "2011-01-20", "2013-01-17", "2015-01-15",
                "2017-01-19", "2019-01-17", "2021-01-21", "2023-01-19", "2025-01-16")


def _zip_csv(path):
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.lower().endswith(".csv")][0]
    return z, csv.reader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace"))


def _pick(raw, prefix):
    return [os.path.join(raw, f) for f in os.listdir(raw) if f.startswith(prefix)][0]


def restricted_universe(live_dir):
    """What `data/backtest` actually contains -- the universe the published panel was built on."""
    pr = os.path.join(live_dir, "prices")
    return {f[:-4].upper() for f in os.listdir(pr) if f.endswith(".csv")}


def sep_spans(raw):
    """First and last close per ticker, plus which tickers have an in-window row."""
    z, r = _zip_csv(_pick(raw, "SHARADAR_SEP_"))
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    first, last = {}, {}
    rows, t0 = 0, time.time()
    for row in r:
        rows += 1
        t, d = row[ti], row[di][:10]
        if t not in first or d < first[t]:
            first[t] = d
        if t not in last or d > last[t]:
            last[t] = d
        if rows % 15_000_000 == 0:
            print("    sep %dM rows, %d tickers, %.0fs"
                  % (rows / 1e6, len(first), time.time() - t0), flush=True)
    z.close()
    return first, last, rows


def sf1_covered(raw):
    """Tickers with ARQ fundamentals -- the SAME filter the provider's universe applies."""
    z, r = _zip_csv(_pick(raw, "SHARADAR_SF1_"))
    head = next(r)
    ti = head.index("ticker")
    dim = head.index("dimension") if "dimension" in head else None
    di = head.index("datekey")
    out = set()
    for row in r:
        if dim is not None and row[dim] != "ARQ":
            continue
        d = (row[di] or "")[:10]
        if d and d <= WINDOW[1]:
            out.add(row[ti].upper())
    z.close()
    return out


def cap_at_2009(raw):
    """Market cap at the first month-end on or after 2009-01-01, from DAILY."""
    z, r = _zip_csv(_pick(raw, "SHARADAR_DAILY_"))
    head = next(r)
    ti, di = head.index("ticker"), head.index("date")
    mi = head.index("marketcap") if "marketcap" in head else None
    if mi is None:
        z.close()
        return {}
    best = {}
    for row in r:
        d = row[di][:10]
        if d < "2009-01-01" or d > "2009-12-31":
            continue
        t = row[ti].upper()
        v = row[mi]
        if not v:
            continue
        if t not in best or d < best[t][0]:
            try:
                best[t] = (d, float(v))
            except ValueError:
                continue
    z.close()
    return {t: v for t, (_d, v) in best.items()}


def main(argv=None) -> int:
    from scripts.index_best import _data_root, data_candidates
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    raw = os.path.join(data, "backtest_freeze_2026-10", "raw")
    live = os.path.join(data, "backtest")
    if not os.path.isdir(raw):
        print("REFUSING: no raw freeze at %s" % raw)
        return 2
    fa = os.path.join(data, "free_analysis")

    rest = restricted_universe(live)
    print("restricted (data/backtest): %d tickers" % len(rest), flush=True)

    print("scanning SEP ...", flush=True)
    first, last, sep_rows = sep_spans(raw)
    print("  %d rows, %d tickers" % (sep_rows, len(first)), flush=True)
    print("scanning SF1 ...", flush=True)
    covered = sf1_covered(raw)
    print("  %d tickers with ARQ fundamentals" % len(covered), flush=True)
    print("scanning DAILY for 2009 market caps ...", flush=True)
    cap09 = cap_at_2009(raw)
    print("  %d tickers with a 2009 market cap" % len(cap09), flush=True)

    # ---- the FULL universe under the SAME filter ------------------------------------------
    in_win = {t for t in first
              if first[t] <= WINDOW[1] and last[t] >= WINDOW[0]}
    full = in_win & covered
    missing = full - rest
    print("\nfull raw universe (in-window AND SF1-covered): %d" % len(full), flush=True)
    print("  of which MISSING from data/backtest: %d (%.2f%%)"
          % (len(missing), 100.0 * len(missing) / max(1, len(full))), flush=True)

    # ---- (1a) names per date ---------------------------------------------------------------
    per_date = {}
    for d in SAMPLE_DATES:
        f_n = sum(1 for t in full if first[t] <= d <= last[t])
        r_n = sum(1 for t in full & rest if first[t] <= d <= last[t])
        per_date[d] = {"full": f_n, "restricted": r_n,
                       "restricted_share": (r_n / f_n) if f_n else None}
        print("  %s  full %5d   restricted %5d   (%.1f%%)"
              % (d, f_n, r_n, 100.0 * r_n / max(1, f_n)), flush=True)

    # ---- (1b) delisted share ---------------------------------------------------------------
    def dead_share(names):
        n = len(names)
        dead = sum(1 for t in names if last[t] < DEAD_BEFORE)
        return {"names": n, "dead": dead, "share": (dead / n) if n else None}

    d_full, d_rest = dead_share(full), dead_share(full & rest)
    print("\ndelisted-in-window (last close before %s):" % DEAD_BEFORE, flush=True)
    print("  full       %d of %d = %.2f%%"
          % (d_full["dead"], d_full["names"], 100.0 * d_full["share"]), flush=True)
    print("  restricted %d of %d = %.2f%%"
          % (d_rest["dead"], d_rest["names"], 100.0 * d_rest["share"]), flush=True)
    ratio = (d_full["share"] / d_rest["share"]) if d_rest["share"] else None

    # ---- (1c) THE SHARP ONE: small in 2009 AND later died --------------------------------
    small_dead = {t for t in full
                  if cap09.get(t, float("inf")) < SMALL_2009 and last[t] < DEAD_BEFORE}
    sd_missing = small_dead - rest
    small_alive = {t for t in full
                   if cap09.get(t, float("inf")) < SMALL_2009 and last[t] >= DEAD_BEFORE}
    sa_missing = small_alive - rest
    print("\nsmall in 2009 (< $%.0fM) AND later died: %d names, %d MISSING from data/backtest "
          "(%.2f%%)" % (SMALL_2009 / 1e6, len(small_dead), len(sd_missing),
                        100.0 * len(sd_missing) / max(1, len(small_dead))), flush=True)
    print("small in 2009 AND still alive:          %d names, %d MISSING (%.2f%%)"
          % (len(small_alive), len(sa_missing),
             100.0 * len(sa_missing) / max(1, len(small_alive))), flush=True)
    print("  -> the missing rate among small-and-DEAD vs small-and-ALIVE is the bias, and it is "
          "%s" % ("NON-RANDOM" if len(small_dead) and len(small_alive) and
                  (len(sd_missing) / len(small_dead)) >
                  (len(sa_missing) / max(1, len(small_alive))) else "NOT in that direction"),
          flush=True)

    res = {
        "item": "UNIVERSE-BIAS", "part": "1 census", "trials": 0,
        "class": "FACTS -- facts about what two universes contain; no hypothesis, no bar, no "
                 "verdict (S25 / MB3 / PANEL-EXT-RECHECK class)",
        "window": list(WINDOW), "small_2009_usd": SMALL_2009, "dead_before": DEAD_BEFORE,
        "mechanism": "sharadar_freeze._fresh_universe ranks the TICKERS snapshot by TODAY's "
                     "scalemarketcap, keeps scale >= 2, takes the top 3,000 and unions the live "
                     "set -- a PRESENT-DAY property",
        "restricted_tickers": len(rest),
        "sep_rows": sep_rows, "sep_tickers": len(first),
        "sf1_covered": len(covered),
        "full_universe": len(full), "missing_from_restricted": len(missing),
        "missing_share": len(missing) / max(1, len(full)),
        "names_per_date": per_date,
        "delisted_full": d_full, "delisted_restricted": d_rest,
        "delisted_ratio_full_over_restricted": ratio,
        "small_2009_and_died": {"names": len(small_dead), "missing": len(sd_missing),
                                "missing_share": len(sd_missing) / max(1, len(small_dead))},
        "small_2009_and_alive": {"names": len(small_alive), "missing": len(sa_missing),
                                 "missing_share": len(sa_missing) / max(1, len(small_alive))},
    }
    json.dump(res, io.open(os.path.join(fa, "UNIVERSE_BIAS_CENSUS.json"), "w",
                           encoding="utf-8"), indent=2)
    print("\nwrote %s" % os.path.join(fa, "UNIVERSE_BIAS_CENSUS.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
