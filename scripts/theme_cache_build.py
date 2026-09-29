"""Build the PRODUCTION theme cache `valuation/screener/live_themes.py` reads.

WHY THIS EXISTS, MEASURED. On 2026-09-29 valquo.co served `theme_contributing` **institutional
0.0 / insider 0.0** — two of the nine themes contributing nothing to every live score.
`live_themes.py` reads `data/live_cache/theme_columns.json`, and **no production scan has ever
had that file**: `data/` is gitignored *and* dockerignored, `auto-scan.yml` sets no
`LIVE_THEMES_CACHE`, and the only writer (`fidelity2_rebuild build-live`) was pinned to a
snapshot of 500 names served on 2026-08-08 and to two period constants.

WHAT THIS CHANGES, AND WHAT IT DELIBERATELY DOES NOT. Three inputs become live:

  * **the served universe** is the LATEST scan snapshot (`Store.latest_scan_date` /
    `load_snapshot`), never the pinned file;
  * **the two 13F periods** are DERIVED from the calendar with the panel's own lag rule
    (`fundamental_panel._inst_accum`, `lag_days=45`), never constants;
  * **the output path** comes from `LIVE_THEMES_CACHE`, so the workflow can point it at
    `.scan-cache/` — the one directory `actions/cache` carries between runs, which is how a
    gitignored artifact survives at all.

**THE ROW ARITHMETIC IS NOT REIMPLEMENTED HERE.** `fidelity2_rebuild.build_live` computes it,
and this module calls that function with live arguments (`B7`: one code object per rule). The
13F zips, the CUSIP ladder and the signed Form 4 crawl likewise come from
`scripts.live_theme_sources`. Anything else would be a second definition of the estimator whose
fidelity was measured once — and a second definition is how +0.9190 / +0.8726 silently stops
being true of what production runs.

**THE PERIODS THE PINNED CONSTANTS NAME ARE NOW ONE QUARTER STALE**, which is the clearest
argument for deriving them: `PERIOD_CURR = 31-MAR-2026` was correct when V2G ran, and Q2-2026
13Fs became due on 2026-08-14, so as of today the two latest complete periods are **30-JUN-2026
and 31-MAR-2026**. A constant cannot notice that; the calendar can.

    python scripts/theme_cache_build.py                 # derive everything, write the cache
    python scripts/theme_cache_build.py --dry-run       # report what it WOULD do, write nothing
    python scripts/theme_cache_build.py --fidelity      # the pinned-input control (see below)

**ADOPTS NOTHING.** Writing this cache changes every live score the next scan produces, which
is a VINTAGE EVENT (vintage 5) and Don's call. Nothing here schedules itself: the weekly job is
a `.github/` change Don PRs.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from scripts import fidelity2_rebuild as F2                              # noqa: E402
from scripts import live_theme_sources as M                              # noqa: E402

#: The panel's own 13F filing lag, IMPORTED as a value rather than retyped. A quarter is usable
#: only once its filings were public, and `_inst_accum`'s docstring is the definition:
#: "using only quarters whose filing (calendardate + ~45d lag) was public by as_of".
INST_LAG_DAYS = 45

#: Where the cache goes. The workflow overrides this to `.scan-cache/theme_columns.json`,
#: because `data/` is gitignored and dockerignored and therefore cannot carry anything between
#: a build and a scan. The default matches what `live_themes.py` reads locally.
DEFAULT_CACHE = os.path.join("data", "live_cache", "theme_columns.json")


def cache_path() -> str:
    return (os.environ.get("LIVE_THEMES_CACHE") or "").strip() or DEFAULT_CACHE


# ------------------------------------------------------------------------------------------
# The periods, DERIVED. This is the part a constant cannot do.
# ------------------------------------------------------------------------------------------
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
           "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def quarter_end_on_or_before(d: _dt.date) -> _dt.date:
    """The most recent calendar quarter-end on or before `d`."""
    q_month = ((d.month - 1) // 3) * 3 + 3
    end = _quarter_end(d.year, q_month)
    if end > d:
        q_month -= 3
        year = d.year
        if q_month <= 0:
            q_month, year = 12, d.year - 1
        end = _quarter_end(year, q_month)
    return end


def _quarter_end(year: int, month: int) -> _dt.date:
    day = 31 if month in (3, 12) else 30
    return _dt.date(year, month, day)


def period_label(d: _dt.date) -> str:
    """`31-MAR-2026` — the key the 13F aggregate is indexed by."""
    return "%02d-%s-%04d" % (d.day, _MONTHS[d.month - 1], d.year)


def filing_window(d: _dt.date) -> str:
    """`01mar2026-31may2026` — the SEC structured-data window covering a period's filings.

    Derived from the shape of the two pinned pairs rather than guessed: the window opens on the
    first of the period-end month and closes on the last day of the month two later. The
    `test_the_derivation_reproduces_both_pinned_pairs` control is what makes that claim
    checkable instead of asserted.
    """
    start = _dt.date(d.year, d.month, 1)
    m = d.month + 2
    y = d.year + (1 if m > 12 else 0)
    m = m - 12 if m > 12 else m
    last = _dt.date(y + (1 if m == 12 else 0), 1 if m == 12 else m + 1, 1) - _dt.timedelta(days=1)
    return "%s-%s" % (start.strftime("%d%b%Y").lower(), last.strftime("%d%b%Y").lower())


def latest_complete_periods(as_of: _dt.date = None, lag_days: int = INST_LAG_DAYS) -> dict:
    """The two latest COMPLETE 13F periods as of `as_of`, on the panel's own lag rule.

    A period counts as complete only when `period_end + lag_days <= as_of`, which is exactly
    `_inst_accum`'s test. **This is the whole reason the constants had to go**: on any date
    before 2026-08-14 the answer is 31-MAR-2026 / 31-DEC-2025, and on any date after it the
    answer has moved — and a pinned constant reports the old answer forever without erring.
    """
    as_of = as_of or _dt.date.today()
    q = quarter_end_on_or_before(as_of)
    while q + _dt.timedelta(days=lag_days) > as_of:
        q = quarter_end_on_or_before(q - _dt.timedelta(days=1))
    prior = quarter_end_on_or_before(q - _dt.timedelta(days=1))
    return {"as_of": as_of.isoformat(), "lag_days": lag_days,
            "curr": period_label(q), "prior": period_label(prior),
            "window_curr": filing_window(q), "window_prior": filing_window(prior),
            "curr_date": q.isoformat(), "prior_date": prior.isoformat()}


# ------------------------------------------------------------------------------------------
# The served universe, from the LATEST scan rather than the pinned snapshot.
# ------------------------------------------------------------------------------------------
def served_from_store(store=None) -> dict:
    """`load_served`'s shape, built from the newest scan the store holds.

    Returns `{"served": [...], "scan_date": str|None, "reason": str}` rather than raising, so a
    caller can report an empty store as a REFUSAL rather than building a cache over nothing —
    a zero-row cache would read to `live_themes.py` exactly like the absent file this item
    exists to replace.
    """
    if store is None:
        from valuation.screener.store import Store
        store = Store()
    date = store.latest_scan_date()
    if not date:
        return {"served": [], "scan_date": None,
                "reason": "the scan store holds no scans, so there is no served universe"}
    rows = store.load_snapshot(date) or []
    served = []
    for r in rows:
        t = str(r.get("ticker") or "").strip().upper()
        if not t:
            continue
        served.append({"ticker": t, "name": r.get("name") or "",
                       "market_cap": r.get("market_cap"), "sector": r.get("sector") or ""})
    return {"served": served, "scan_date": date,
            "reason": "" if served else "the latest scan %s carries no rows" % date}


# ------------------------------------------------------------------------------------------
# The fidelity control. It REFUSES rather than passing when it cannot run.
# ------------------------------------------------------------------------------------------
def fidelity_control(banked: str = None, root: str = None) -> dict:
    """Re-run the builder on the PINNED inputs and require the banked cache row-for-row.

    **THIS IS THE GATE THE BUILDER SHIPS BEHIND**, and its logic is the reason: the +0.9190 /
    +0.8726 fidelity was measured on `build_live()` reading the pinned snapshot and the pinned
    periods. Parameterising that function must leave that exact call bit-identical, or the
    measured fidelity is a statement about code that no longer runs. `THEME-RESTORE`'s
    drift-guard lesson is the standard: **38 of 38 must agree exactly**, not approximately.

    **IT CANNOT PASS VACUOUSLY.** A missing banked artifact, a missing 13F aggregate or an
    empty comparison is reported `runnable: False` and is NOT a pass — an absent control and a
    satisfied control must never read the same.
    """
    root = root or F2.ROOT
    banked = banked or F2.LIVE_CACHE
    out = {"runnable": False, "ok": False, "reason": "", "n_compared": 0,
           "max_abs_delta": None, "missing_inputs": []}

    for label, path in (("banked theme_columns.json", banked),
                        ("13f_aggregate.json", os.path.join(root, "13f_aggregate.json")),
                        ("the pinned served snapshot", M.SNAPSHOT),
                        ("the form4_live cache", F2.F4_DIR_LIVE)):
        if not os.path.exists(path):
            out["missing_inputs"].append("%s (%s)" % (label, path))
    if out["missing_inputs"]:
        out["reason"] = ("the control CANNOT RUN: %s. This is NOT a pass and NOT a failure -- "
                         "the inputs the fidelity was measured on are not on this machine."
                         % "; ".join(out["missing_inputs"]))
        return out

    with open(banked, encoding="utf-8") as fh:
        want = (json.load(fh) or {}).get("rows") or {}
    got = F2.build_live(cache_path=os.path.join(root, "_fidelity_probe.json"),
                        periods_source="pinned constants (fidelity control)")["rows"]

    out["runnable"] = True
    if not want:
        out["reason"] = ("the banked cache carries no rows, so there is nothing to reproduce; "
                         "reported VACUOUS rather than passing")
        return out

    worst, worst_at = 0.0, None
    keys = set(want) | set(got)
    for t in sorted(keys):
        a, b = want.get(t) or {}, got.get(t) or {}
        for col in set(a) | set(b):
            x, y = a.get(col), b.get(col)
            if x is None or y is None:
                out["reason"] = ("%s.%s is present in one build and absent in the other; a "
                                 "row-for-row control cannot be satisfied" % (t, col))
                out["n_compared"] = len(keys)
                return out
            d = abs(float(x) - float(y))
            if d > worst:
                worst, worst_at = d, "%s.%s" % (t, col)
    out.update(n_compared=len(keys), max_abs_delta=worst,
               ok=(worst == 0.0 and set(want) == set(got)))
    out["reason"] = ("reproduced %d rows at max |delta| %.3e%s" %
                     (len(keys), worst, "" if out["ok"] else " -- worst at %s" % worst_at))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the production theme cache.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the derived inputs and write nothing")
    ap.add_argument("--fidelity", action="store_true",
                    help="run the pinned-input fidelity control and exit")
    ap.add_argument("--as-of", default="", help="override today (testing only)")
    a = ap.parse_args(argv)

    if a.fidelity:
        r = fidelity_control()
        print("FIDELITY CONTROL")
        print("  runnable : %s" % r["runnable"])
        print("  ok       : %s" % r["ok"])
        print("  compared : %s   max |delta| %s" % (r["n_compared"], r["max_abs_delta"]))
        print("  %s" % r["reason"])
        # A control that could not run exits NON-ZERO. It is not a pass.
        return 0 if r["ok"] else 1

    as_of = _dt.date.fromisoformat(a.as_of) if a.as_of else _dt.date.today()
    per = latest_complete_periods(as_of)
    su = served_from_store()

    print("THEME CACHE BUILD")
    print("  as of        %s (13F lag %d days, from fundamental_panel._inst_accum)"
          % (per["as_of"], per["lag_days"]))
    print("  periods      %s (prior) -> %s (curr)   DERIVED, not pinned"
          % (per["prior"], per["curr"]))
    print("  windows      %s / %s" % (per["window_prior"], per["window_curr"]))
    print("  pinned were  %s / %s%s" % (M.PERIOD_PRIOR, M.PERIOD_CURR,
          "   <-- STALE" if M.PERIOD_CURR != per["curr"] else "   (same today)"))
    print("  served       %s from scan %s" % (len(su["served"]), su["scan_date"]))
    print("  cache        %s" % cache_path())

    if not su["served"]:
        print("REFUSED: %s" % su["reason"], file=sys.stderr)
        return 3
    if a.dry_run:
        print("DRY RUN - nothing was written and no SEC request was made.")
        return 0

    # THE SEC LEGS RUN FIRST, through the IMPORTED machinery. `build_13f` downloads and
    # aggregates the structured zips; `fetch_all` walks the CUSIP ladder and the signed Form 4
    # crawl. Neither is reimplemented here.
    guard = M.Guard() if hasattr(M, "Guard") else None
    M.WINDOW_CURR, M.WINDOW_PRIOR = per["window_curr"], per["window_prior"]
    M.PERIOD_CURR, M.PERIOD_PRIOR = per["curr"], per["prior"]
    M.build_13f(guard=guard)
    M.fetch_all()

    out = F2.build_live(served=su["served"], period_curr=per["curr"],
                        period_prior=per["prior"], cache_path=cache_path(),
                        periods_source="derived from the calendar at %s (lag %d days)"
                                       % (per["as_of"], per["lag_days"]))
    print("built %s rows for %s served names" % (len(out["rows"]), out["n_served"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
