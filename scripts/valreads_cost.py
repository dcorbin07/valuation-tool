# -*- coding: utf-8 -*-
"""`VALREADS` step 0 — WHAT ONE WEEKLY RUN COSTS, measured before anything is registered.

    python -m scripts.valreads_cost --sample 12

The prompt's own ordering: *"Measure what one weekly run costs in time and vendor calls first."*
The population the register fixes depends on this number, so it is measured BEFORE the register
is written and the register cites it. **It measures cost, not an outcome** — no forward return is
read, no read is scored, nothing is compared to a bar.

**CANARY FIRST, AND REFUSE WHILE THROTTLED.** Measuring anything against the live Yahoo feed
consumes a rolling per-IP quota, and exhausting it does **not raise** — it silently degrades
`CompanyData` (measured 2026-08-07: 302 of 403 names arrived with `beta=None`, the tell being
many names reporting an identical WACC as it collapses to pure cost of debt). A cost measurement
taken through a throttled feed would be **fast and wrong in the flattering direction**, because a
degraded fetch returns sooner. So: one known name first, serial pacing, and contamination checked
**continuously** rather than after the fact.

**ZERO TRIALS.** A cost census searches nothing and has no bar.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

#: the canary. A name this project values on every scan, so "it did not resolve" is a fact about
#: the feed rather than about the ticker (`stooq-is-dead`'s control lesson).
CANARY = "AAPL"

#: serial pacing, from the measured recovery behaviour: a paced 46-name sample completed clean in
#: 2.2 min where 400 names at 6 workers throttled 176 of 402.
PACE_S = 1.5

#: A FIXED, DECLARED probe list -- not drawn from the hot list, because a population selected on
#: the reads' own correlate would bias anything measured on it later, and because a cost census
#: should span the kinds of name the reads behave differently on. Two megacaps, two of the names
#: item 52 names (NVDA hypergrowth, TSLA the story-rule case), a financial (the matching-question
#: branch), a mature dividend payer, a cash-burner, and a mid-cap.
PROBE = ["AAPL", "MSFT", "NVDA", "TSLA", "JPM", "KO", "JNJ", "APLD",
         "PLTR", "F", "T", "CVX"]


def out_path():
    from scripts.index_best import _data_root
    return os.path.join(_data_root(), "free_analysis", "VALREADS_COST.json")


#: the two PUBLIC, TOKENLESS reads a weekly recorder can reach. Measured rather than assumed --
#: `/api/hotstocks` caps at 500 rows whatever `top` asks for, and the Index's own holdings route
#: is a separate object.
BASE = "https://valquo.co"
HOT_URL = BASE + "/api/hotstocks?top=500"
INDEX_URL = BASE + "/api/valquo-index"


def population_census(timeout=60):
    """How many names a weekly run would have to value, and where they come from.

    **THE OVERLAP IS THE FINDING AND IT DECIDES THE POPULATION.** A population defined as "the
    published hot list" would miss most of the product's own book: the Index is a $10B-tier
    decile book and the hot list is ranked by hot score, so they are different selections.
    Measured here instead of reasoned about.
    """
    import urllib.request
    out = {"hot_url": HOT_URL, "index_url": INDEX_URL, "tokenless": True}
    try:
        with urllib.request.urlopen(HOT_URL, timeout=timeout) as r:
            h = json.load(r)
        hot = [x.get("ticker") for x in (h.get("rows") or []) if x.get("ticker")]
        out["hot_n"] = len(hot)
        out["hot_scan_date"] = h.get("scan_date")
        out["hot_fields_present"] = sorted(
            k for k in ("ticker", "rank", "hot_score", "price", "market_cap", "sector", "bucket")
            if (h.get("rows") or [{}])[0].get(k) is not None)
        out["hot_cap_note"] = ("the route caps at 500 rows whatever `top` requests, so this is "
                              "the ceiling of what the PUBLIC surface exposes -- not the scan's "
                              "whole universe")
    except Exception as e:                                                  # noqa: BLE001
        out["hot_error"] = repr(e)[:200]
        hot = []
    try:
        with urllib.request.urlopen(INDEX_URL, timeout=timeout) as r:
            d = json.load(r)
        idx = [p.get("ticker") for p in (d.get("positions") or []) if p.get("ticker")]
        out["index_n"] = len(idx)
        out["index_as_of"] = d.get("as_of")
        out["index_formed_on"] = d.get("formed_on")
    except Exception as e:                                                  # noqa: BLE001
        out["index_error"] = repr(e)[:200]
        idx = []
    H, I = set(hot), set(idx)
    out["index_inside_hot"] = len(H & I)
    out["index_outside_hot"] = len(I - H)
    out["union_n"] = len(H | I)
    out["WHY_THE_UNION"] = (
        "only %d of the Index's %d positions are inside the published hot list, so a hot-list "
        "population would omit %d names of the product's own book -- the one population a "
        "forward record of the valuation page's reads must certainly contain."
        % (len(H & I), len(I), len(I - H)))
    return out


def _wacc_of(res):
    w = getattr(res, "wacc", None)
    v = getattr(w, "wacc", None) if w is not None else None
    return None if v is None else round(float(v), 6)


def value_one(ticker):
    """One valuation, timed, with the contamination tells recorded beside it."""
    from valuation.engine import pipeline as P
    t0 = time.time()
    err = None
    res = None
    try:
        res = P.value_ticker(ticker, run_ai=False)
    except Exception as e:                                                  # noqa: BLE001
        err = repr(e)[:300]
    el = time.time() - t0
    cd = getattr(res, "company", None) if res is not None else None
    return {
        "ticker": ticker,
        "seconds": round(el, 3),
        "error": err,
        # THE CONTAMINATION TELLS, recorded per name rather than inferred at the end.
        "beta": (None if cd is None else getattr(cd, "beta", None)),
        "market_cap": (None if cd is None else getattr(cd, "market_cap", None)),
        "wacc": _wacc_of(res),
        "price": (None if cd is None else getattr(cd, "price", None)),
        "regime": (str(getattr(getattr(res, "classification", None), "regime", "") or "")
                   if res is not None else ""),
    }


def contaminated(rows):
    """Is this run degraded? Three independent tells, each measured rather than assumed.

    A throttled fetch does not raise, so the only honest check is on the DATA: a missing beta or
    market cap, and -- the sharpest one -- many names sharing one WACC, which is what WACC
    collapsing to pure cost of debt looks like.
    """
    done = [r for r in rows if r.get("error") is None]
    if not done:
        return {"ok": False, "why": "every valuation errored", "n_done": 0}
    no_beta = [r["ticker"] for r in done if r.get("beta") is None]
    no_cap = [r["ticker"] for r in done if not r.get("market_cap")]
    waccs = [r["wacc"] for r in done if r.get("wacc") is not None]
    mode_n = max([waccs.count(w) for w in set(waccs)], default=0)
    return {
        "ok": bool(len(no_beta) <= max(1, len(done) // 4)
                   and len(no_cap) <= max(1, len(done) // 4)
                   and (len(waccs) < 3 or mode_n < max(3, len(waccs) // 2))),
        "n_done": len(done),
        "names_without_beta": no_beta,
        "names_without_market_cap": no_cap,
        "identical_wacc_names": mode_n,
        "distinct_wacc": len(set(waccs)),
        "why": ("a throttled feed degrades CompanyData silently; a run where many names report "
                "one WACC is WACC collapsing to pure cost of debt because market_cap is "
                "missing (measured 2026-08-07)"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=len(PROBE))
    ap.add_argument("--pace", type=float, default=PACE_S)
    args = ap.parse_args(argv)

    print("[cost] CANARY %s first -- a cost measured through a throttled feed is fast and "
          "wrong in the flattering direction" % CANARY, flush=True)
    can = value_one(CANARY)
    print("[cost] canary: %.2fs  beta=%r  cap=%r  wacc=%r  err=%r"
          % (can["seconds"], can["beta"], can["market_cap"], can["wacc"], can["error"]),
          flush=True)
    out = {"item": "VALREADS", "part": "step 0 -- cost census", "trials": 0,
           "trial_class": "COST CENSUS -- no hypothesis, no bar, no outcome statistic, and no "
                          "forward return read anywhere in this module",
           "canary": can, "pace_s": args.pace, "probe_declared": PROBE,
           "reads_no_forward_return": True}
    if can["error"] or can["beta"] is None or not can["market_cap"]:
        out["ABORTED"] = ("the canary came back degraded or errored, so the feed is throttled or "
                          "unreachable and no cost figure measured now would be honest. "
                          "REFUSING rather than reporting a fast number.")
        print("[cost] " + out["ABORTED"], flush=True)
        return out

    names = [t for t in PROBE if t != CANARY][: max(0, args.sample - 1)]
    rows = [can]
    for i, t in enumerate(names, 1):
        time.sleep(args.pace)
        r = value_one(t)
        rows.append(r)
        print("[cost] %2d/%d %-6s %6.2fs  beta=%-6s cap=%-14s regime=%-12s err=%s"
              % (i, len(names), t, r["seconds"], r["beta"], r["market_cap"], r["regime"],
                 (r["error"] or "")[:40]), flush=True)
        # CONTINUOUSLY, not at the end: stop at the first sign rather than discovering it after
        # the figure is already written down.
        c = contaminated(rows)
        if not c["ok"] and len(rows) >= 4:
            out["ABORTED"] = ("contamination detected mid-run after %d names; stopping rather "
                              "than finishing a measurement the feed has already spoiled"
                              % len(rows))
            out["rows"] = rows
            out["contamination"] = c
            print("[cost] " + out["ABORTED"], flush=True)
            return out

    ok = [r for r in rows if r["error"] is None]
    secs = [r["seconds"] for r in ok]
    per = (sum(secs) / len(secs)) if secs else None
    out["rows"] = rows
    out["contamination"] = contaminated(rows)
    out["n_attempted"] = len(rows)
    out["n_valued"] = len(ok)
    out["seconds_per_name_mean"] = (None if per is None else round(per, 3))
    out["seconds_per_name_median"] = (None if not secs else
                                      round(sorted(secs)[len(secs) // 2], 3))
    out["seconds_per_name_max"] = (None if not secs else round(max(secs), 3))
    # VENDOR CALLS. `value_ticker` is ONE fetch per name plus the sector fallback (a no-op when
    # the primary returned a sector) -- so the honest unit is "fetches per name", counted from
    # the code path rather than guessed, and the wall clock is what a run actually costs.
    out["vendor_calls_per_name"] = {
        "company_fetch": 1,
        "sector_fallback": "0 when the primary returned a sector, else 1",
        "counted_from": "pipeline.value_ticker -- fetcher.get_company + resolve_sector",
        "note": "no options chain, no AI call (run_ai=False), no forward return",
    }
    out["population_census"] = population_census()
    if per is not None:
        sizes = [50, 86, 100, 250, 500, 1000, 1500]
        u = out["population_census"].get("union_n")
        if u:
            sizes.append(int(u))
        out["implied_wall_clock_minutes"] = {
            str(n): round((n * (per + args.pace)) / 60.0, 1) for n in sorted(set(sizes))
        }
        out["cost_of_the_union_population_minutes"] = (
            None if not u else round((u * (per + args.pace)) / 60.0, 1))
    write(out)
    return out


def write(out):
    p = out_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with io.open(p, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(out, indent=1, default=str))
    print("[cost] wrote %s" % p, flush=True)


if __name__ == "__main__":
    r = main()
    if "ABORTED" not in r:
        print("\n  per name: mean %.2fs, median %.2fs, max %.2fs over %d valued"
              % (r["seconds_per_name_mean"], r["seconds_per_name_median"],
                 r["seconds_per_name_max"], r["n_valued"]))
        print("  implied wall clock (incl. %.1fs pacing): %s"
              % (r["pace_s"], json.dumps(r["implied_wall_clock_minutes"])))
    raise SystemExit(0)
