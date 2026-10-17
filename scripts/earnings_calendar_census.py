"""Is there a FREE forward earnings calendar good enough for an event-aware book? (item 66b, part 3)

**WHY THIS IS A PREREQUISITE AND NOT A DETAIL.** The licensed event spine holds **385,426 code-22
rows and NOT ONE forward date** - which is why `F-4` earned the harness state
`RULE_ARMED_NEVER_FIRES` and *"as declared enters nothing, ever"*. Every event-aware book in the
fleet, `EARNINGS-CSP`'s stage 3, and any re-declaration of `F-4` or `F-10` need a calendar that
says when the NEXT announcement is. This measures whether the free route is good enough.

**NOTHING IS WIRED INTO A BOOK HERE.** It reports; the decision is Don's.

THE TWO LEGS, AND WHY BOTH ARE FREE
-----------------------------------
**YAHOO (forward).** `valuation/data/yahoo.py` already takes `earningsTimestampStart` for the live
app (`DECISIONS` 2026-10-14), so this is the route the project is on rather than a new vendor. It
also ships **`isEarningsDateEstimate`**, an explicit confirmed-versus-projected flag, and a
`Start`/`End` pair that is a RANGE when the date is not pinned. Those two fields are what make
"how far ahead the date is known" answerable from one read instead of from a year of snapshots.

**SEC 8-K ITEM 2.02 (realised).** `data.sec.gov/submissions/CIK*.json`, free, no key, no licence.
Item 2.02 is *Results of Operations and Financial Condition* - the earnings release itself - so
its filing date is the realised announcement date.

WHAT CAN AND CANNOT BE MEASURED FROM ONE READING, STATED BEFORE THE NUMBERS
--------------------------------------------------------------------------
Yahoo publishes only the NEXT date, so **a retrospective accuracy check against its own past
forecasts is impossible from one read** - it would need snapshots this project has never taken,
and claiming otherwise would be the easiest way to overstate the calendar. Two things are done
instead, and neither is a substitute dressed as the real thing:

1. **THE PROJECTION RULE IS TESTED DIRECTLY, ON SEC HISTORY ALONE.** Yahoo's *estimated* dates are
   a projection from the prior year's calendar position. That rule is testable retrospectively
   with no Yahoo data at all: take each name's realised Item 2.02 dates and ask how far the
   realised date sits from the same-quarter date one year earlier. **That distribution IS "how
   often it moves", and it bounds what any projection-based calendar can achieve.**
2. **THE TWO FREE SOURCES ARE CROSS-CHECKED TODAY.** The SEC history implies a next date by the
   same projection; Yahoo publishes one. Agreement between two independent free sources is weaker
   than a realised check and is available now, and it is labelled as the weaker thing.

    python scripts/earnings_calendar_census.py            # both legs
    python scripts/earnings_calendar_census.py --sec-only # skip the slow Yahoo leg
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import requests  # noqa: E402

from valuation.studies import dipcall as D  # noqa: E402  (data_root lives here)

SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_TICKERS = "https://www.sec.gov/files/company_tickers.json"
#: The SEC asks for a contact in the User-Agent and rate-limits at 10/s. Both are honoured.
UA = "Valquo research (donniecorbin6@gmail.com)"
SEC_PAUSE = 0.12
ITEM_202 = "2.02"
YEARS_BACK = 3
GATE = "optionable"


def _get(url, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"},
                             timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (403, 429):
                time.sleep(1.0 + i)
                continue
            return None
        except Exception:                                            # noqa: BLE001
            time.sleep(0.5 + i)
    return None


def gate_tickers(root=None):
    """The fleet's own optionable gate - read, never retyped."""
    from valuation.edge import fleet_gates as G
    g = (G.load(root).get("gates") or {}).get(GATE) or {}
    t = g.get("tickers")
    names = sorted(t.keys()) if isinstance(t, dict) else sorted(t or [])
    return names, g.get("as_of")


def cik_map():
    j = _get(SEC_TICKERS) or {}
    return {str(v["ticker"]).upper(): int(v["cik_str"]) for v in j.values()}


def item_202_dates(cik, years_back=YEARS_BACK, today=None):
    """Realised earnings-release dates: 8-K filings whose items include 2.02."""
    j = _get(SEC_SUBMISSIONS.format(cik=cik))
    if not j:
        return None
    rec = ((j.get("filings") or {}).get("recent") or {})
    forms = rec.get("form") or []
    dates = rec.get("filingDate") or []
    items = rec.get("items") or []
    cut = (today or _dt.date.today()) - _dt.timedelta(days=365 * years_back + 30)
    out = []
    for i, f in enumerate(forms):
        if not str(f).startswith("8-K"):
            continue
        it = str(items[i]) if i < len(items) else ""
        if ITEM_202 not in it:
            continue
        d = str(dates[i])[:10]
        try:
            if _dt.date.fromisoformat(d) >= cut:
                out.append(d)
        except ValueError:
            continue
    return sorted(set(out))


def year_over_year_drift(dates):
    """How far each release sits from the nearest release ~365 days earlier. In DAYS.

    **THIS IS THE "HOW OFTEN IT MOVES" MEASUREMENT**, and it is the ceiling on any projected
    calendar: a date predicted by last year's position cannot be more accurate than the year-on-
    year drift of the thing it is predicting.
    """
    ds = [_dt.date.fromisoformat(d) for d in sorted(dates)]
    out = []
    for d in ds:
        target = d - _dt.timedelta(days=365)
        prior = [p for p in ds if abs((p - target).days) <= 45]
        if not prior:
            continue
        best = min(prior, key=lambda p: abs((p - target).days))
        out.append((d - (best + _dt.timedelta(days=365))).days)
    return out


def yahoo_forward(tickers, pause=0.0):
    """Yahoo's NEXT date per name, with the flag that says whether it is pinned or projected."""
    import yfinance as yf
    today = _dt.date.today()
    rows = {}
    for n, t in enumerate(tickers, 1):
        rec = {"ok": False}
        try:
            i = yf.Ticker(t).info or {}
            s = i.get("earningsTimestampStart")
            e = i.get("earningsTimestampEnd")
            est = i.get("isEarningsDateEstimate")
            if s:
                d0 = _dt.date.fromtimestamp(int(s))
                d1 = _dt.date.fromtimestamp(int(e)) if e else d0
                rec = {"ok": True, "start": d0.isoformat(), "end": d1.isoformat(),
                       "range_days": (d1 - d0).days,
                       "days_ahead": (d0 - today).days,
                       "is_estimate": (None if est is None else bool(est)),
                       "in_future": d0 >= today}
        except Exception as ex:                                      # noqa: BLE001
            rec = {"ok": False, "error": type(ex).__name__}
        rows[t] = rec
        if pause:
            time.sleep(pause)
        if n % 50 == 0:
            print("  yahoo %d/%d" % (n, len(tickers)), flush=True)
    return rows


def _pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, max(0, int(q * len(s))))] if s else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sec-only", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    names, as_of = gate_tickers()
    if a.limit:
        names = names[:a.limit]
    print("gate %r as_of %s -> %d names" % (GATE, as_of, len(names)), flush=True)

    cm = cik_map()
    mapped = {t: cm[t] for t in names if t in cm}
    print("ticker -> CIK: %d of %d" % (len(mapped), len(names)), flush=True)

    sec, drift_all, counts = {}, [], []
    for n, (t, cik) in enumerate(sorted(mapped.items()), 1):
        ds = item_202_dates(cik)
        time.sleep(SEC_PAUSE)
        if ds is None:
            sec[t] = {"ok": False}
            continue
        dr = year_over_year_drift(ds)
        sec[t] = {"ok": True, "n_releases": len(ds), "last": (ds[-1] if ds else None),
                  "drift_days": dr}
        if ds:
            counts.append(len(ds))
        drift_all.extend(dr)
        if n % 50 == 0:
            print("  sec %d/%d" % (n, len(mapped)), flush=True)

    with_rel = [t for t, v in sec.items() if v.get("ok") and v.get("n_releases")]
    ad = [abs(x) for x in drift_all]
    res = {
        "gate": GATE, "gate_as_of": as_of, "n_gate": len(names),
        "measured_on": _dt.date.today().isoformat(),
        "sec_item_202": {
            "ticker_to_cik": len(mapped),
            "names_with_releases": len(with_rel),
            "coverage_of_gate": (len(with_rel) / len(names)) if names else None,
            "median_releases_per_name_3y": (statistics.median(counts) if counts else None),
            "n_yoy_pairs": len(drift_all),
            "drift_abs_days": {
                "median": (statistics.median(ad) if ad else None),
                "p75": _pct(ad, 0.75), "p90": _pct(ad, 0.90), "p95": _pct(ad, 0.95),
                "max": (max(ad) if ad else None),
                "within_0": (sum(1 for x in ad if x == 0) / len(ad)) if ad else None,
                "within_3": (sum(1 for x in ad if x <= 3) / len(ad)) if ad else None,
                "within_7": (sum(1 for x in ad if x <= 7) / len(ad)) if ad else None,
            },
        },
    }

    if not a.sec_only:
        print("yahoo leg over %d names..." % len(names), flush=True)
        # paced, not batched:  is one call per name and Yahoo throttles a
        # tight loop (the 401-Invalid-Crumb the CI logs show). 0.3s is cheap here.
        yh = yahoo_forward(names, pause=0.3)
        ok = [v for v in yh.values() if v.get("ok")]
        fut = [v for v in ok if v.get("in_future")]
        est = [v for v in fut if v.get("is_estimate") is True]
        con = [v for v in fut if v.get("is_estimate") is False]
        ahead = [v["days_ahead"] for v in fut]
        res["yahoo_forward"] = {
            "n_queried": len(names),
            "n_with_a_date": len(ok),
            "n_in_future": len(fut),
            "coverage_of_gate": (len(fut) / len(names)) if names else None,
            "n_confirmed": len(con), "n_estimated": len(est),
            "confirmed_share_of_future": (len(con) / len(fut)) if fut else None,
            "days_ahead": {"median": (statistics.median(ahead) if ahead else None),
                           "p10": _pct(ahead, 0.10), "p90": _pct(ahead, 0.90),
                           "min": (min(ahead) if ahead else None),
                           "max": (max(ahead) if ahead else None)},
            "confirmed_days_ahead_median": (
                statistics.median([v["days_ahead"] for v in con]) if con else None),
            "estimated_days_ahead_median": (
                statistics.median([v["days_ahead"] for v in est]) if est else None),
            "n_with_a_date_range": sum(1 for v in fut if v.get("range_days")),
        }
        # the weaker cross-check, labelled as weaker: does Yahoo's date agree with the date the
        # SEC history implies by the SAME projection Yahoo uses for its estimated rows?
        agree = []
        for t, v in yh.items():
            s = sec.get(t) or {}
            if not (v.get("ok") and v.get("in_future") and s.get("ok") and s.get("last")):
                continue
            implied = _dt.date.fromisoformat(s["last"]) + _dt.timedelta(days=91)
            agree.append(abs((_dt.date.fromisoformat(v["start"]) - implied).days))
        res["cross_check_weaker_than_realised"] = {
            "n": len(agree),
            "median_abs_days": (statistics.median(agree) if agree else None),
            "within_7": (sum(1 for x in agree if x <= 7) / len(agree)) if agree else None,
            "note": "two free sources agreeing is NOT a realised check; Yahoo publishes only the "
                    "next date, so its own forecasts cannot be scored without snapshots this "
                    "project has never taken. This run starts that record.",
        }
        res["yahoo_snapshot"] = yh

    out = os.path.join(D.data_root(), "free_analysis", "EARNINGS_CALENDAR_CENSUS.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    slim = {k: v for k, v in res.items() if k != "yahoo_snapshot"}
    print(json.dumps(slim, indent=1))
    print("\nwrote", out)


if __name__ == "__main__":
    main()
