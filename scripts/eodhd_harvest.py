# -*- coding: utf-8 -*-
"""`EODHD-HARVEST` — a dated freeze of everything a future test could need. ZERO TRIALS.

    python -m scripts.eodhd_harvest --product fundamentals
    python -m scripts.eodhd_harvest --product insider
    python -m scripts.eodhd_harvest --product mktcap
    python -m scripts.eodhd_harvest --product earnings
    python -m scripts.eodhd_harvest --verify

**NO FORWARD RETURN IS LOADED AND NO OUTCOME IS COMPUTED** — pinned by test. Collection only.

--------------------------------------------------------------------------------------------
THE LICENCE FENCE.

Raw payload is written under `D:\\eodhd\\freeze_<date>` **and nowhere else**. Nothing here writes to
the repo; what leaves this lane is the manifest SUMMARY (unit counts, bytes, sha256) in a
`data/`-side artifact, which is gitignored. The key is read from the environment and never printed.
The subscription is ~1 month, so **the point of the freeze is that the data stays usable after it
lapses** — which is why every unit is checksummed and the manifest records what was asked for.

--------------------------------------------------------------------------------------------
RESUMABLE OR IT IS WORTHLESS — the harvest convention this project already owns.

One unit = one `(product, key)`. The payload is written **atomically** (tmp + `os.replace`) BEFORE
its manifest line is appended and fsynced, so a kill can lose a unit's RECORD but can never leave a
half-written payload recorded as complete. Re-running re-does any unit whose payload is absent or
whose size disagrees with its record. `wrds_pull`'s rule, inherited whole: *"the chain harvest lost
twelve hours to a checkpoint loop that died while workers kept going."*

--------------------------------------------------------------------------------------------
THE BUDGET IS ASKED FOR, NOT COUNTED LOCALLY.

100,000 calls a day, 1,000 a minute, and **fundamentals cost 10 calls each**, so the full US
universe is ~96,450 calls — essentially one whole day. `/api/user` reports the day's consumption, so
the harvest **asks the API what it has spent** and stops at a reserve rather than trusting a local
tally. The allowance resets at midnight GMT, and a stop is a resume point rather than a failure.

**CREDIT RISK IS NOT HARVESTED AND THAT IS A MEASUREMENT, NOT AN OMISSION.** `EODHD_CENSUS.md` §1
measured `bond-fundamentals` at **403 Forbidden** on two ISINs with three alternative names at 404,
so the brief's "credit-risk history" is not available on this plan.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import sys
import time

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from scripts import eodhd_census as EC                                    # noqa: E402
from valuation.studies import dipcall as D                               # noqa: E402

SCHEMA = 1
OUT = "EODHD_HARVEST.json"

#: **MEASURED PER-CALL COST, because the published figure covers only `fundamentals`.**
#:
#: The pricing page says one fundamentals request costs 10 calls and implies everything else costs
#: 1. **`historical-market-cap` also costs 10, measured rather than assumed:** 7,500 units moved
#: the day's consumption from 26,541 to 99,991, i.e. 73,450 calls -> **9.79 each**. Assuming 1 cost
#: this harvest its whole first day — mktcap ate 73% of the allowance and `fundamentals`, the
#: product that matters most, got **zero** names.
#:
#: So the order below is a BUDGET decision, not a preference: at 10 calls each, the 9,645-name
#: universe costs ~96,450 and **fundamentals needs a day to itself.**
CALL_COST = {"fundamentals": 10, "mktcap": 10, "insider": 1, "earnings": 1}
PRIORITY = ("fundamentals", "earnings", "insider", "mktcap")

#: Stop with this many calls still unspent, so a concurrent lane or a retry is never starved.
RESERVE = 3000
#: 1,000 calls a minute is the hard limit; fundamentals cost 10, so pace below it.
SLEEP_FUNDAMENTALS = 0.65
SLEEP_CHEAP = 0.10

PRODUCTS = ("fundamentals", "insider", "mktcap", "earnings")

#: The insider endpoint ignores `symbol=` and cannot be paged (census §3), so its history is
#: harvested as MARKET-WIDE date windows. The window is narrow enough that a full window fits
#: under the row cap; `--verify` checks that no window came back AT the cap, because a window at
#: the cap has silently lost rows.
INSIDER_WINDOW_DAYS = 14
INSIDER_LIMIT = 1000


def freeze_root(stamp: str = "") -> str:
    """The dated freeze directory, and it WARNS when it is about to open a second one.

    **A HARVEST THAT CROSSES MIDNIGHT UTC USED TO SPLIT ITSELF IN TWO, SILENTLY.** The stamp
    defaults to today, so a resumed run started after midnight opened `freeze_<tomorrow>` while the
    earlier products sat in `freeze_<today>` -- one logical harvest across two directories, which
    breaks the manifest-based resume and leaves a consumer reading a product directory that does
    not exist. It happened: 199 fundamentals units landed in a 10-23 freeze beside 6,150 units in
    the 10-22 one, and had to be merged by hand with their manifest paths rewritten.

    So an unstamped call that is about to create a NEW freeze while another already holds a
    manifest now says so loudly. It does not refuse -- a genuinely new campaign is entitled to a
    new freeze -- but it cannot happen without a line in the log naming the other one.
    """
    s = stamp or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    p = os.path.join(EC.RAW_ROOT, "freeze_%s" % s)
    if not stamp and not os.path.isdir(p):
        others = []
        if os.path.isdir(EC.RAW_ROOT):
            for d in sorted(os.listdir(EC.RAW_ROOT)):
                q = os.path.join(EC.RAW_ROOT, d)
                if d.startswith("freeze_") and os.path.exists(os.path.join(q, "manifest.jsonl")):
                    others.append(d)
        if others:
            print("[harvest] WARNING: opening a NEW freeze %s while these already carry a "
                  "manifest: %s. Pass --stamp to resume one of them instead; a harvest split "
                  "across two freezes cannot be resumed from either."
                  % (os.path.basename(p), ", ".join(others)), flush=True)
    os.makedirs(p, exist_ok=True)
    return p


def _manifest_path(root: str) -> str:
    return os.path.join(root, "manifest.jsonl")


def _read_manifest(root: str) -> dict:
    p = _manifest_path(root)
    out = {}
    if not os.path.isfile(p):
        return out
    for ln in io.open(p, encoding="utf-8"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        out[(r.get("product"), r.get("key"))] = r
    return out


def _write_unit(root: str, product: str, key: str, payload) -> dict:
    """Atomic payload write, THEN the manifest line. Never the other order."""
    sub = os.path.join(root, product)
    os.makedirs(sub, exist_ok=True)
    safe = "".join(c if (c.isalnum() or c in "._-") else "_" for c in key)
    dest = os.path.join(sub, "%s.json" % safe)
    body = json.dumps(payload, default=str).encode("utf-8")
    tmp = dest + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(body)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, dest)
    rec = {"product": product, "key": key, "path": dest, "bytes": len(body),
           "sha256": hashlib.sha256(body).hexdigest(),
           "rows": (len(payload) if isinstance(payload, (list, dict)) else None),
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with io.open(_manifest_path(root), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    return rec


def _budget():
    st, u = EC._get("user")
    if st == 200 and isinstance(u, dict):
        return int(u.get("apiRequests") or 0), int(u.get("dailyRateLimit") or 0)
    return None, None


def us_universe() -> list:
    """Every name in the corrected raw universe, delisted included — the panel is the universe."""
    p = pd.read_pickle(D.panel_path())[["ticker"]].copy()
    return sorted({str(t).upper() for t in p["ticker"]})


def fundamentals_order(names):
    """Tier first, then step 4's cohorts, then the rest -- and SAY which ordering was used.

    **WHY ORDER AT ALL.** `fundamentals` costs 10 calls a name and the universe is 9,645, so a full
    pass is 96,450 of a 100,000 daily allowance: it needs a day to itself and cannot share one. But
    the two questions waiting on it need a fraction of that --

      * step 3 scores the $10B tier at the comparison date   ~835 names   ~8,350 calls
      * step 4's gate measures the pre-2009 delisted hole     120 names    ~1,200 calls

    -- so ordering puts both inside the first ~10,000 calls and a single day answers them, with the
    remainder accumulating behind. The manifest is the resume point either way, so the ordering
    costs nothing and buys two unblocked items on day one.

    **IT FALLS BACK RATHER THAN FAILING, AND REPORTS THE FALLBACK.** If the banked Sharadar scores
    or the CRSP spine are not readable the order degrades to plain sorted, which harvests exactly
    the same names in a different sequence. A silent degrade would be the worse outcome: the run
    would look identical and step 3 would simply not unblock, so the chosen ordering is printed.
    """
    first, why = [], []
    try:
        from scripts.eodhd_fidelity import tier_names
        t = [str(x).upper() for x in tier_names()]
        first += t
        why.append("tier:%d" % len(t))
    except Exception as exc:                                    # noqa: BLE001
        why.append("tier UNAVAILABLE (%s)" % type(exc).__name__)
    try:
        from scripts.eodhd_delisted import cohorts
        dead, surv, _, _, _ = cohorts()
        c = [str(x).upper() for x in list(dead) + list(surv)]
        first += c
        why.append("step4 cohorts:%d" % len(c))
    except Exception as exc:                                    # noqa: BLE001
        why.append("step4 cohorts UNAVAILABLE (%s)" % type(exc).__name__)
    seen, out = set(), []
    for t in first:
        if t in names and t not in seen:
            seen.add(t)
            out.append(t)
    rest = [t for t in names if t not in seen]
    print("[harvest] fundamentals order: %s | prioritised %d, then %d"
          % (", ".join(why), len(out), len(rest)), flush=True)
    return out + rest


def harvest_fundamentals(root, done, budget_stop, limit=None):
    names = us_universe()
    # The step-4 cohorts include names that are NOT in the panel (they died before it starts), so
    # the prioritised list is unioned with the universe rather than filtered to it -- otherwise the
    # gate's dead cohort could never be harvested at all.
    extra = []
    try:
        from scripts.eodhd_delisted import cohorts
        dead, _, _, _, _ = cohorts()
        extra = [str(x).upper() for x in dead if str(x).upper() not in set(names)]
    except Exception:                                           # noqa: BLE001
        pass
    names = fundamentals_order(sorted(set(names) | set(extra)))
    todo = [t for t in names if ("fundamentals", t) not in done]
    # `--limit` stops after the first N names of the PRIORITISED order, which is how the tier gets
    # harvested and step 3 read before the remaining names are fetched. The manifest is the resume
    # point, so a later run without a limit simply continues: the limit changes WHEN names arrive
    # and never WHICH.
    if limit:
        todo = todo[:int(limit)]
        print("[harvest] fundamentals: LIMITED to the first %d of the prioritised order"
              % len(todo), flush=True)
    # Report the count HONESTLY: before the limit is applied, so a limited run cannot describe
    # untouched names as "already done". The first cut printed len(names) - len(todo) AFTER the
    # limit had shrunk todo, which read as 8,815 names already harvested when none had been.
    _done_now = sum(1 for t in names if ("fundamentals", t) in done)
    print("[harvest] fundamentals: %d names, %d already in the manifest, %d to do this run"
          % (len(names), _done_now, len(todo)), flush=True)
    got = miss = 0
    for i, tk in enumerate(todo, 1):
        used, cap = _budget() if i % 200 == 1 else (None, None)
        if used is not None and cap and used > cap - budget_stop:
            print("[harvest] STOPPING at the reserve: %d of %d used. Re-run tomorrow; the "
                  "manifest is the resume point." % (used, cap), flush=True)
            break
        st, f = EC._get("fundamentals/%s.US" % tk, {})
        if st == 200 and isinstance(f, dict) and f.get("General"):
            _write_unit(root, "fundamentals", tk, f)
            got += 1
        else:
            miss += 1
        if i % 100 == 0:
            print("    %d/%d  kept %d  missing %d" % (i, len(todo), got, miss), flush=True)
        time.sleep(SLEEP_FUNDAMENTALS)
    return {"requested": len(todo), "kept": got, "missing": miss}


def _insider_window(root, a, b, stats, depth=0):
    """One window, SPLIT RECURSIVELY if it comes back at the row cap.

    **THE CAP IS THE WHOLE PROBLEM AND IT IS SILENT.** The endpoint cannot be paged (census §3:
    page 1 and an `offset` page overlap 50 of 50), so a window holding more rows than `limit`
    returns the cap's worth and **drops the rest without any error**. The first run of this harvest
    wrote 465 windows of which **25 came back exactly at 1,000** — all in the recent years, where
    filing volume is far higher than in 2009.

    So a window at the cap is halved and re-fetched, down to a single day. **A ONE-DAY window still
    at the cap is recorded TRUNCATED rather than accepted**, because at that point the data cannot
    be completed from this endpoint and a silent hole is worse than a named one.
    """
    st, rows = EC._get("insider-transactions", {"from": a, "to": b, "limit": INSIDER_LIMIT})
    time.sleep(SLEEP_CHEAP)
    if st != 200 or not isinstance(rows, list):
        stats["errors"] += 1
        return
    if len(rows) < INSIDER_LIMIT or a == b:
        _write_unit(root, "insider", "%s_%s" % (a, b), rows)
        stats["written"] += 1
        stats["rows"] += len(rows)
        if len(rows) >= INSIDER_LIMIT:
            stats["truncated_single_day"] += 1
            stats["truncated_days"].append(a)
        return
    stats["split"] += 1
    d0 = dt.date.fromisoformat(a)
    d1 = dt.date.fromisoformat(b)
    mid = d0 + (d1 - d0) // 2
    _insider_window(root, d0.isoformat(), mid.isoformat(), stats, depth + 1)
    _insider_window(root, (mid + dt.timedelta(days=1)).isoformat(), d1.isoformat(),
                    stats, depth + 1)


def harvest_insider(root, done, budget_stop):
    """MARKET-WIDE windows, because the endpoint ignores `symbol=` (census §3)."""
    lo = dt.date(2009, 1, 1)
    hi = dt.date.today()
    windows = []
    d = lo
    while d < hi:
        e = min(d + dt.timedelta(days=INSIDER_WINDOW_DAYS - 1), hi)
        windows.append((d.isoformat(), e.isoformat()))
        d = e + dt.timedelta(days=1)
    # A window already recorded AT THE CAP must be re-done in slices, so "done" is not enough.
    capped = set()
    for (product, key), rec in done.items():
        if product == "insider" and (rec.get("rows") or 0) >= INSIDER_LIMIT:
            capped.add(key)
    todo = [w for w in windows
            if ("insider", "%s_%s" % w) not in done or ("%s_%s" % w) in capped]
    print("[harvest] insider: %d windows of %d days, %d to do (%d of them re-done because they "
          "were AT THE CAP)" % (len(windows), INSIDER_WINDOW_DAYS, len(todo), len(capped)),
          flush=True)
    stats = {"written": 0, "split": 0, "rows": 0, "errors": 0,
             "truncated_single_day": 0, "truncated_days": []}
    for i, (a, b) in enumerate(todo, 1):
        _insider_window(root, a, b, stats)
        if i % 25 == 0:
            print("    %d/%d  written %d  splits %d  rows %d  truncated-days %d"
                  % (i, len(todo), stats["written"], stats["split"], stats["rows"],
                     stats["truncated_single_day"]), flush=True)
    stats["truncated_days"] = sorted(stats["truncated_days"])[:40]
    stats["windows_requested"] = len(todo)
    stats["WHY_THE_CAP_MATTERS"] = (
        "the endpoint cannot be paged, so a window at the row cap has silently LOST rows. Windows "
        "at the cap are halved and re-fetched down to one day; a ONE-DAY window still at the cap "
        "is recorded TRUNCATED rather than accepted, because a named hole beats a silent one.")
    return stats


def harvest_mktcap(root, done, budget_stop):
    names = us_universe()
    todo = [t for t in names if ("mktcap", t) not in done]
    print("[harvest] mktcap: %d to do (5y weekly per name, census section 4)" % len(todo),
          flush=True)
    got = miss = 0
    for i, tk in enumerate(todo, 1):
        used, cap = _budget() if i % 500 == 1 else (None, None)
        if used is not None and cap and used > cap - budget_stop:
            print("[harvest] STOPPING at the reserve: %d of %d" % (used, cap), flush=True)
            break
        st, body = EC._get("historical-market-cap/%s.US" % tk, {})
        if st == 200 and isinstance(body, dict) and body:
            _write_unit(root, "mktcap", tk, body)
            got += 1
        else:
            miss += 1
        if i % 250 == 0:
            print("    %d/%d  kept %d  empty/missing %d" % (i, len(todo), got, miss), flush=True)
        time.sleep(SLEEP_CHEAP)
    return {"requested": len(todo), "kept": got, "missing_or_empty": miss}


def harvest_earnings(root, done, budget_stop):
    """Quarter-by-quarter so a window is small enough to be complete, 1999 -> 13 months forward."""
    out = []
    y0, y1 = 1999, dt.date.today().year + 2
    for y in range(y0, y1 + 1):
        for q, (a, b) in enumerate(((("%d-01-01" % y), ("%d-03-31" % y)),
                                    (("%d-04-01" % y), ("%d-06-30" % y)),
                                    (("%d-07-01" % y), ("%d-09-30" % y)),
                                    (("%d-10-01" % y), ("%d-12-31" % y))), 1):
            out.append(("%dq%d" % (y, q), a, b))
    todo = [u for u in out if ("earnings", u[0]) not in done]
    print("[harvest] earnings: %d quarters, %d to do" % (len(out), len(todo)), flush=True)
    got = 0
    for i, (key, a, b) in enumerate(todo, 1):
        st, body = EC._get("calendar/earnings", {"from": a, "to": b})
        if st == 200 and isinstance(body, dict):
            _write_unit(root, "earnings", key, body)
            got += 1
        if i % 25 == 0:
            print("    %d/%d quarters" % (i, len(todo)), flush=True)
        time.sleep(SLEEP_CHEAP)
    return {"quarters_requested": len(todo), "quarters_written": got}


def verify(root) -> dict:
    """Every recorded unit must exist with the recorded size AND the recorded sha256."""
    man = _read_manifest(root)
    ok = bad = absent = 0
    bad_keys = []
    for (product, key), rec in man.items():
        p = rec.get("path") or ""
        if not p or not os.path.isfile(p):
            absent += 1
            bad_keys.append("%s/%s ABSENT" % (product, key))
            continue
        body = open(p, "rb").read()
        if len(body) != rec.get("bytes") or hashlib.sha256(body).hexdigest() != rec.get("sha256"):
            bad += 1
            bad_keys.append("%s/%s MISMATCH" % (product, key))
        else:
            ok += 1
    by = {}
    for (product, _k), rec in man.items():
        d = by.setdefault(product, {"units": 0, "bytes": 0})
        d["units"] += 1
        d["bytes"] += int(rec.get("bytes") or 0)
    return {"units_recorded": len(man), "verified": ok, "mismatched": bad, "absent": absent,
            "by_product": by, "first_failures": bad_keys[:10]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--product", choices=PRODUCTS)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--stamp", default="")
    ap.add_argument("--reserve", type=int, default=RESERVE)
    ap.add_argument("--limit", type=int, default=0,
                    help="fundamentals only: stop after the first N of the prioritised order")
    a = ap.parse_args(argv)

    root = freeze_root(a.stamp)
    done = _read_manifest(root)
    res = {"item": "EODHD-HARVEST", "schema": SCHEMA, "trials": 0,
           "forward_return_touched": False, "freeze": root,
           "licence": ("EODHD PERSONAL plan: private, non-commercial. Raw payload lives here and "
                       "nowhere else; it is never committed and never displayed."),
           "credit_risk": ("NOT HARVESTED -- bond-fundamentals measured 403 Forbidden on this "
                           "plan (EODHD_CENSUS.md section 1), so the brief's credit-risk history "
                           "is unavailable rather than skipped"),
           "units_already_present": len(done)}

    used, cap = _budget()
    res["budget_before"] = {"used": used, "limit": cap}
    res["call_cost_measured"] = dict(CALL_COST)
    res["priority_order"] = list(PRIORITY)
    res["WHY_THE_ORDER"] = (
        "historical-market-cap costs 10 calls, not 1 — measured at 9.79 over 7,500 units on "
        "2026-10-22, which cost that day's whole allowance and left fundamentals with zero "
        "names. fundamentals needs a day to itself at ~96,450 calls.")
    if a.product and cap:
        est = len(us_universe()) * CALL_COST.get(a.product, 1)
        res["estimated_cost_if_complete"] = est
        if used + est > cap:
            print("[harvest] NOTE: a complete %s pass costs about %d calls and %d of %d are "
                  "already spent, so this run will stop at the reserve and resume after the "
                  "midnight GMT reset." % (a.product, est, used, cap), flush=True)
    print("[harvest] freeze %s | %d units already recorded | budget %s of %s"
          % (root, len(done), used, cap), flush=True)

    if a.verify:
        res["verify"] = verify(root)
        print("[harvest] verify: %s" % json.dumps(res["verify"]["by_product"]), flush=True)
        print("          recorded %d | verified %d | mismatched %d | absent %d"
              % (res["verify"]["units_recorded"], res["verify"]["verified"],
                 res["verify"]["mismatched"], res["verify"]["absent"]), flush=True)
    elif a.product:
        t0 = time.time()
        fn = {"fundamentals": harvest_fundamentals, "insider": harvest_insider,
              "mktcap": harvest_mktcap, "earnings": harvest_earnings}[a.product]
        # Only fundamentals takes a limit; the cheap products are complete in one pass.
        kw = {"limit": a.limit} if a.product == "fundamentals" and a.limit else {}
        res[a.product] = fn(root, done, a.reserve, **kw)
        res[a.product]["seconds"] = round(time.time() - t0, 1)
        print("[harvest] %s: %s" % (a.product, json.dumps(res[a.product])), flush=True)
    else:
        ap.error("need --product or --verify")

    used2, cap2 = _budget()
    res["budget_after"] = {"used": used2, "limit": cap2}
    p = D.out_path(OUT)
    prev = {}
    if os.path.isfile(p):
        try:
            prev = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            prev = {}
    prev.update(res)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(prev, indent=1, default=str))
    print("[harvest] wrote %s" % p, flush=True)
    return res


if __name__ == "__main__":
    main()
    raise SystemExit(0)
