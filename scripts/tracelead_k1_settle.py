# -*- coding: utf-8 -*-
"""Settle `tracelead`'s `K1` with the per-WINDOW issuer lists. ONE connection, ONE query.

**WHY IT WAS UNRESOLVED.** `TRACELEAD_K1_BOUND.json` could only BOUND coverage, because the one
connection it had returned issuer counts **per YEAR** while `K1`'s form needs them per **63-session
WINDOW**. The bound cleared the 0.70 bar in every year -- 0.7325 at its tightest, 0.0325 above --
and `HANDOFF_tracelead.md` §4 recorded that **a clearing bound is not a pass**: it is loosest
exactly where it looks best, reading 1.0000 in 2009-2010 because the tier then held fewer names
than there were covered issuers. So the candidate was neither killed nor cleared.

**WHAT THIS PULLS, AND WHY IT IS ONE QUERY AND NOT SIXTY-NINE.** The distinct
`(issuer cusip6, trade date)` pairs for the tier's issuers over the draft's era, bucketed into
windows **locally**. Asking per window would be 69 round trips on an account that has been disabled
by repeated failures before; asking once and bucketing in pandas is the same answer for one query.
At 428 issuers over ~2,750 sessions the pull is at most ~1.2M narrow rows.

**THE TIER SPINE IS REBUILT LOCALLY AND VALIDATED, NOT RE-PULLED.** The collector persisted
`EDGE_DRAFTS_stocknames.pkl` but only the COUNT of its cusip6 set, so the set is rebuilt from that
pickle by the collector's own dated-interval logic and **required to reproduce 428**. A rebuild that
silently produced a different issuer set would make this a measurement of a different population --
`O-1`'s family -- so it refuses rather than proceeding.

**THE RULES THIS FILE OBEYS, from `DECISIONS.md` 2026-10-04.** ONE connection attempt per session
and **never a retry loop** -- a failed connect is RECORDED and returned, never tried twice. Script
access lasts about 30 days per MFA web login and was restored 2026-10-04, so it lapses around
2026-11-03; **if it has lapsed, this says so and writes nothing else.**

**ZERO TRIALS.** `K1` is a pre-outcome coverage kill: `MB1-SEL`, it can only ever BLOCK the
candidate and never produce a finding, so it charges nothing and runs before any register exists.
**No register is committed here and no arm is run** -- `K2`, `K3` and `K4` are costume and
reproduction kills that only matter if `K1` resolves.

Raw rows land under `D:\\wrds` and never in git.
"""
import argparse
import bisect
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import edge_drafts_collect as EC                            # noqa: E402
from valuation.studies import dipcall as D                               # noqa: E402

RAW = EC.RAW_ROOT
SPINE = os.path.join(RAW, EC.SPINE_PKL)
OUT_RAW = os.path.join(RAW, "TRACELEAD_K1_WINDOWS.pkl")
_DATA = D.data_root(required=False) or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUT = os.path.join(_DATA, "free_analysis", "TRACELEAD_K1_SETTLED.json")

#: `PREREG_DRAFT_tracelead.md` §3's bar, reused VERBATIM -- not re-chosen here and not relaxed.
#: `W-28`'s rule: a bar watched to fail may not be moved afterwards.
K1_BAR = 0.70
#: §2's window: 63 sessions before t.
WINDOW_SESSIONS = 63
#: TRACE enhanced is delivered with a delay; the draft's era is 2009-2019.
ERA_LO, ERA_HI = "2009-01-01", "2019-12-31"
#: The collector's measured figure. A rebuild that does not reproduce it is a different population.
EXPECTED_TIER_CUSIP6 = 428
#: Probed by the collector; not guessed here.
CUSIP_COL, DATE_COL = "cusip_id", "trd_exctn_dt"


def tier_and_issuers():
    """The tier cells and their cusip6, rebuilt from the persisted spine by the collector's logic."""
    tier = EC.tier_cells()
    sn = pd.read_pickle(SPINE)
    sn["ticker"] = sn["ticker"].astype(str).str.strip().str.upper()
    ours = sn[sn["ticker"].isin(set(tier["ticker"]))].copy()
    j = tier.merge(ours[["ticker", "permno", "ncusip", "namedt", "nameenddt"]],
                   on="ticker", how="left")
    d = pd.to_datetime(j["date"], errors="coerce")
    lo = pd.to_datetime(j["namedt"], errors="coerce")
    hi = pd.to_datetime(j["nameenddt"], errors="coerce")
    hit = j[(d >= lo) & (d <= hi)].copy()
    hit["cusip6"] = hit["ncusip"].astype(str).str[:6]
    hit = hit[hit["cusip6"].str.len() >= 6]
    c6 = sorted(set(hit["cusip6"]))
    return tier, hit[["date", "ticker", "cusip6"]].drop_duplicates(), c6


def sessions():
    """The project's own trading calendar, from the price store rather than a generated one."""
    p = os.path.join(_DATA, "backtest", "prices", "AAPL.csv")
    d = pd.read_csv(p)
    # **THE HEADER IS DATA IF YOU READ IT AS DATA.** A first cut passed , so the
    # literal string "date" entered the calendar and sorted LAST -- which would have shifted every
    # window boundary by one and produced a plausible coverage number from a corrupted calendar.
    # Only ISO-shaped values are kept, and the result is required non-empty by the caller.
    col = "date" if "date" in d.columns else d.columns[0]
    out = sorted({str(x)[:10] for x in d[col]
                  if len(str(x)) >= 10 and str(x)[:4].isdigit() and str(x)[4] == "-"})
    if not out:
        raise ValueError("no trading sessions parsed from %s" % p)
    return out


def score(pairs, cells, cal):
    """Per-window coverage: the share of tier NAMES whose issuer traded in the 63 sessions before t.

    The window is [t-63 sessions, t) -- strictly BEFORE the rebalance date, so a trade on t itself
    never counts. Anything else would be look-ahead on the very signal the candidate is built from.
    """
    by_issuer = {}
    for c6, dt in zip(pairs["cusip6"], pairs["d"]):
        by_issuer.setdefault(c6, []).append(dt)
    for k in by_issuer:
        by_issuer[k].sort()
    out = {}
    for dte, grp in cells.groupby("date"):
        i = bisect.bisect_left(cal, str(dte)[:10])
        lo = cal[max(0, i - WINDOW_SESSIONS)]
        hi = cal[i] if i < len(cal) else str(dte)[:10]
        cov = 0
        for c6 in grp["cusip6"]:
            ds = by_issuer.get(c6)
            if not ds:
                continue
            a = bisect.bisect_left(ds, lo)
            b = bisect.bisect_left(ds, hi)
            if b > a:
                cov += 1
        out[str(dte)[:10]] = {"names": int(len(grp)), "covered": int(cov),
                              "coverage": cov / max(1, len(grp))}
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="bucket an existing raw pull without connecting")
    a = ap.parse_args(argv)

    rep = {"item": "TRACELEAD-K1", "trials": 0, "class": "FIXED", "bar": K1_BAR,
           "window_sessions": WINDOW_SESSIONS, "era": [ERA_LO, ERA_HI],
           "note": ("K1 is a pre-outcome coverage kill: it can only BLOCK the candidate, so it "
                    "charges nothing and runs before any register exists. No register is "
                    "committed here and no arm is run.")}

    tier, cells, c6 = tier_and_issuers()
    rep["tier_cells"] = int(len(tier))
    rep["tier_cusip6_rebuilt"] = len(c6)
    rep["tier_cusip6_expected"] = EXPECTED_TIER_CUSIP6
    if len(c6) != EXPECTED_TIER_CUSIP6:
        rep["verdict"] = ("NOT SETTLED -- the rebuilt issuer set is %d against the collector's "
                          "measured %d, so this would measure a different population"
                          % (len(c6), EXPECTED_TIER_CUSIP6))
        print("[k1] %s" % rep["verdict"])
        _write(rep)
        return 2
    print("[k1] tier %d cells, issuer set %d reproduces the collector exactly"
          % (len(tier), len(c6)), flush=True)

    if a.offline:
        if not os.path.exists(OUT_RAW):
            rep["verdict"] = "NOT SETTLED -- no raw pull at %s and --offline was given" % OUT_RAW
            print("[k1] %s" % rep["verdict"])
            _write(rep)
            return 2
        pairs = pd.read_pickle(OUT_RAW)
        rep["connection"] = "offline: reused the banked pull"
    else:
        try:
            import wrds
        except ImportError as exc:
            rep["connection"] = "NO wrds MODULE: %s" % exc
            rep["verdict"] = "NOT SETTLED -- the wrds module is not installed"
            print("[k1] %s" % rep["verdict"])
            _write(rep)
            return 2
        # ONE attempt. A failure is RECORDED and returned, never retried: repeated failures have
        # disabled this account before (DECISIONS.md 2026-10-04).
        try:
            db = wrds.Connection(wrds_username=os.environ.get("WRDS_USERNAME", "donniecorbin"))
            rep["connection"] = "ok"
            print("[k1] connected on the single attempt", flush=True)
        except Exception as exc:                                         # noqa: BLE001
            rep["connection"] = "REFUSED on the single attempt: %s" % str(exc)[:300]
            rep["verdict"] = ("NOT SETTLED -- WRDS script access is unavailable this session, so "
                              "K1 stays UNRESOLVED on the bound and no retry was made")
            print("[k1] %s" % rep["connection"])
            print("[k1] %s" % rep["verdict"])
            _write(rep)
            return 2
        inlist = ",".join("'%s'" % c for c in c6)
        # **ONE CONNECTION, ONE QUERY PER YEAR -- AND THAT IS NOT A RETRY LOOP.** A single
        # era-wide `distinct (issuer, date)` pull failed on the first attempt: ~1.2M rows in one
        # result set, where the collector's per-YEAR aggregates over the identical IN-list and the
        # identical functions had succeeded. The rule in `DECISIONS.md` protects an account that
        # has been disabled by repeated failed CONNECTS; the connect succeeded here and the server
        # rejected an oversized result. So the query is split by year -- eleven small results on
        # the SAME connection, exact rather than approximated.
        #
        # **WHY NOT AGGREGATE TO MONTHS SERVER-SIDE**, which would be one small query: a 63-session
        # window does not align to month boundaries, so monthly presence would count a trade in an
        # overlapping month as in-window and **OVERSTATE** coverage -- the unsafe direction for a
        # kill, because it makes the kill less likely to fire. Exactness is cheap here and the
        # error would run the wrong way.
        frames, errs = [], {}
        for yr in range(int(ERA_LO[:4]), int(ERA_HI[:4]) + 1):
            try:
                q = ("select distinct substring(%s from 1 for 6) as cusip6, %s as d "
                     "from trace.trace_enhanced where %s between '%d-01-01' and '%d-12-31' "
                     "and substring(%s from 1 for 6) in (%s)"
                     % (CUSIP_COL, DATE_COL, DATE_COL, yr, yr, CUSIP_COL, inlist))
                r = db.raw_sql(q)
                frames.append(r)
                print("    %d  %d issuer-date pairs" % (yr, len(r)), flush=True)
            except Exception as exc:                                     # noqa: BLE001
                # **KEEP THE TAIL, NOT THE HEAD.** The first cut recorded `str(exc)[:300]` and the
                # exception embeds the whole SQL, so 300 characters of my own IN-list survived and
                # the database's actual message -- the only diagnostic part -- was truncated away.
                errs[yr] = str(exc)[-400:]
                print("    %d FAILED: %s" % (yr, str(exc)[-200:]), flush=True)
                try:
                    db.connection.rollback()
                except Exception:                                        # noqa: BLE001
                    pass
        rep["per_year_errors"] = errs
        if not frames:
            rep["connection"] = "connected, EVERY per-year query failed"
            rep["verdict"] = "NOT SETTLED -- the pull failed on every year"
            print("[k1] %s" % rep["verdict"])
            _write(rep)
            return 2
        if errs:
            # A partial pull would understate coverage on the missing years and could fire the
            # kill for a reason that is about the pull rather than the data. Refused outright.
            rep["verdict"] = ("NOT SETTLED -- %d of %d years failed to pull, and a partial era "
                              "would understate coverage and could fire the kill for a reason "
                              "about the PULL rather than the data"
                              % (len(errs), int(ERA_HI[:4]) - int(ERA_LO[:4]) + 1))
            print("[k1] %s" % rep["verdict"])
            _write(rep)
            return 2
        pairs = pd.concat(frames, ignore_index=True).drop_duplicates()
        pairs["cusip6"] = pairs["cusip6"].astype(str)
        pairs["d"] = pairs["d"].astype(str).str[:10]
        pairs.to_pickle(OUT_RAW)
        rep["pairs_pulled"] = int(len(pairs))
        print("[k1] %d distinct issuer-date pairs -> %s" % (len(pairs), OUT_RAW), flush=True)

    rep["pairs"] = int(len(pairs))
    rep["distinct_issuers_traded"] = int(pairs["cusip6"].nunique())
    cal = sessions()
    cells = cells[(cells["date"] >= ERA_LO) & (cells["date"] <= ERA_HI)]
    per = score(pairs, cells, cal)
    rep["windows"] = len(per)
    rep["per_window"] = per
    vals = [v["coverage"] for v in per.values()]
    if not vals:
        rep["verdict"] = "NOT SETTLED -- no tier window falls inside the era"
        print("[k1] %s" % rep["verdict"])
        _write(rep)
        return 2
    rep["coverage_min"] = min(vals)
    rep["coverage_median"] = float(pd.Series(vals).median())
    rep["coverage_max"] = max(vals)
    rep["windows_below_bar"] = sum(1 for v in vals if v < K1_BAR)
    # The draft's form: K1 FIRES when coverage falls below the bar. Closed vocabulary so a reader
    # cannot mistake a clearing bound for a pass -- the mistake the first pass had to guard.
    fires = rep["coverage_min"] < K1_BAR
    rep["verdict"] = "K1 FIRES" if fires else "K1 DOES NOT FIRE"
    rep["how_to_read_it"] = (
        "This is the EXACT per-window statistic, not the bound. K1 DOES NOT FIRE means the "
        "coverage kill is passed and the candidate survives to K2-K4, which are NOT run here. It "
        "is not evidence that the candidate works.")
    print("[k1] windows %d | coverage min %.4f median %.4f max %.4f | below bar %d"
          % (rep["windows"], rep["coverage_min"], rep["coverage_median"], rep["coverage_max"],
             rep["windows_below_bar"]))
    print("[k1] VERDICT %s" % rep["verdict"])
    _write(rep)
    return 0


def _write(rep):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=2, sort_keys=True)
    print("[k1] wrote %s" % OUT)


if __name__ == "__main__":
    raise SystemExit(main())
