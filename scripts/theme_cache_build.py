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
import io
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

#: THE FIDELITY REFERENCE, AND IT MAY NEVER BE THE LIVE PATH.
#:
#: `fidelity2_rebuild.LIVE_CACHE` and `live_themes.CACHE` are the SAME file,
#: `data/live_cache/theme_columns.json`. So restoring Don's banked copy there in order to run
#: `--fidelity` SILENTLY TURNS ON THE SEVEN-THEME BOOK for every local scan, and keeps it on for
#: up to `live_themes.MAX_AGE_DAYS` = 120 days — an unannounced **vintage 5**, arrived at by
#: putting a file somewhere rather than by a decision. The Oct 22 rebalance book is built
#: locally, so that is not hypothetical.
#:
#: The reference therefore lives under its own name. `--banked` overrides it; a test asserts it
#: is not `live_themes.CACHE`.
FIDELITY_REFERENCE = os.path.join(
    "data", "live_cache", "theme_columns.FIDELITY_REFERENCE_2026-08-11.json")


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
    # NOT `F2.LIVE_CACHE`, which IS the live reader's path — see `FIDELITY_REFERENCE`.
    banked = banked or FIDELITY_REFERENCE
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
    # `root` IS FORWARDED, and until now it was not. The first cut used it to decide WHERE to
    # look for the inputs and where to drop the probe file, and then called `build_live` with no
    # `root` at all — so the existence checks ran against the override while the build read
    # `F2.ROOT`. A half-applied override is worse than none: it reports that it checked one tree
    # and then measures another, which is the wrong-object family.
    got = F2.build_live(root=root, f4_dir=os.path.join(root, "form4_live"),
                        cache_path=os.path.join(root, "_fidelity_probe.json"),
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
    out["reason"] = ("reproduced %d rows at max abs delta %.3e%s" %
                     (len(keys), worst, "" if out["ok"] else " -- worst at %s" % worst_at))

    # THE BAR STAYS AT 0.0 AND IS NOT LOOSENED TO A TOLERANCE, but a Linux run must not be
    # misread as a fidelity failure. MEASURED by the manager on 2026-09-29: 440 rows,
    # max abs delta 1.42e-14 on 44 `insider_score` rows — and the PRE-PARAMETERISATION code at
    # f266c19^ gives the IDENTICAL 1.42e-14, while new-vs-old on the SAME machine is exactly
    # 0.0. So the residue is platform `math.tanh` in its last digit, not the refactor.
    #
    # The reference was built on Windows, so a Windows run is the one that can reach 0.0. This
    # is stated rather than absorbed: quietly widening the bar would make the control unable to
    # see a real regression of the same size.
    if not out["ok"] and worst and worst < 1e-12:
        out["platform_note"] = (
            "max abs delta %.3e is at the scale of platform `math.tanh` in its last digit. The "
            "reference was built on Windows; the same comparison on Linux measured 1.42e-14 on "
            "insider_score rows, and the PRE-parameterisation code gives the identical figure, "
            "so a residue this size is NOT evidence about the refactor. THE BAR REMAINS 0.0 -- "
            "re-run on the platform that built the reference rather than loosening it."
            % worst)
    return out


def newest_published_periods(as_of=None, max_back: int = 4) -> dict:
    """`latest_complete_periods`, stepped back until SEC actually HAS the dataset.

    MEASURED 2026-09-30, and this is why the function exists. The derivation asks for period
    **30-JUN-2026** (45-day lag from today) and SEC returns **404** for its window
    `01jun2026-31aug2026`. HEAD probes of the surrounding windows:

        01sep2025-30nov2025   200   85,618,099 bytes
        01dec2025-28feb2026   200   90,264,650 bytes
        01mar2026-31may2026   200   99,411,274 bytes
        01jun2026-31aug2026   404
        01sep2026-30nov2026   404

    So the newest PUBLISHED period is **31-MAR-2026**. The 13F *filing* deadline for Q2 has
    passed; SEC's *structured data set* for that filing window has not been posted. **The
    derivation is ahead of the publication schedule, and deriving without checking availability
    turns a working build into a 404 halfway through** -- which is exactly what happened: the
    first window downloaded and aggregated (22,626 CUSIPs, 8,741 filers, 3,108,293 share rows)
    and the second raised.

    AND IT CORRECTS THE BUILDER'S OWN WARNING. `main` prints `<-- STALE` whenever the pinned
    constants differ from the derived pair. Today the pinned pair (31-DEC-2025 / 31-MAR-2026) is
    the newest SEC publishes and the DERIVED pair is the unavailable one, so the warning points
    at the wrong side. The pin was not stale; the derivation was early.

    `max_back` is small on purpose: stepping back further than a year would silently build a
    cache from genuinely old holdings rather than refusing.
    """
    import requests
    per = latest_complete_periods(as_of) if as_of else latest_complete_periods()
    tried = []
    for _ in range(max_back):
        # THE URL COMES FROM THE DOWNLOADER'S OWN CONSTANT (B7). Rebuilding it here would be a
        # second copy of SEC's path, and the probe would then be able to say "published" about a
        # URL the downloader never fetches.
        url = M.DATASET_URL.format(window=per["window_curr"])
        try:
            r = requests.head(url, timeout=30, allow_redirects=True,
                              headers={"User-Agent": getattr(
                                  __import__("valuation.config", fromlist=["CONFIG"]).CONFIG,
                                  "sec_user_agent", "valuation-tool contact@example.com")})
            ok = r.status_code == 200
        except Exception:                                               # noqa: BLE001
            ok = False
        tried.append({"period": per["curr"], "window": per["window_curr"], "published": ok})
        if ok:
            per = dict(per)
            per["probed"] = tried
            per["stepped_back"] = len(tried) - 1
            return per
        # One quarter earlier. `latest_complete_periods` takes an as-of, so move the clock.
        import datetime as _dt
        base = _dt.date.fromisoformat(str(per["as_of"])) - _dt.timedelta(days=95)
        per = latest_complete_periods(base)
    per = dict(per)
    per["probed"] = tried
    per["stepped_back"] = len(tried)
    per["unpublished"] = True
    return per


def served_from_universe(spec: str, limit: int = 1500) -> dict:
    """`served_from_store`'s shape, from the broker ranking or a ticker file.

    SAME SHAPE, deliberately, so nothing downstream learns a second way to be handed a
    universe -- the build path, the refusal and the reporting are all unchanged.

    `scan_date` is set to the SOURCE rather than left blank, because a cache is only meaningful
    beside a statement of which population it covers, and "built for the broker top 1500" is a
    different claim from "built for the names the 2026-09-30 scan served".
    """
    if spec == "broker":
        from valuation.config import CONFIG
        from valuation.screener import broker_universe
        rows = broker_universe.build(CONFIG, limit=limit) or []
        served = sorted({str(r.get("ticker") or "").upper() for r in rows if r.get("ticker")})
        return {"served": served, "scan_date": "broker_top_%d" % limit,
                "reason": "the broker liquidity ranking" if served
                          else "the broker universe came back empty"}
    try:
        with io.open(spec, encoding="utf-8") as fh:
            served = sorted({ln.strip().upper() for ln in fh if ln.strip()})
    except OSError as e:
        return {"served": [], "scan_date": None,
                "reason": "could not read the universe file %s (%s)" % (spec, type(e).__name__)}
    return {"served": served, "scan_date": "file:%s" % spec,
            "reason": "a ticker file" if served else "the universe file is empty"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the production theme cache.")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the derived inputs and write nothing")
    ap.add_argument("--fidelity", action="store_true",
                    help="run the pinned-input fidelity control and exit")
    ap.add_argument("--as-of", default="", help="override today (testing only)")
    ap.add_argument("--banked", default="",
                    help="the fidelity reference to compare against (default: "
                         "FIDELITY_REFERENCE, which is deliberately NOT the live cache path)")
    ap.add_argument("--root", default="", help="the live_themes root holding the inputs")
    ap.add_argument("--universe", default="",
                    help=("build for this universe instead of the latest scan snapshot: "
                          "`broker` for the live broker liquidity ranking, or a path to a file "
                          "of one ticker per line. The local store may hold only a test "
                          "fixture, in which case the scan route builds a one-name cache and "
                          "reports it as a build."))
    ap.add_argument("--slice", default="",
                    help=("run one interleaved shard of the SEC crawl, as `i/n` (e.g. `0/3`). "
                          "Shards never collide -- each keeps its own manifest and the durable "
                          "cache is the per-leg payload file -- so several may run at once. "
                          "With a shard the crawl runs and the cache assembly is SKIPPED; run "
                          "once more with no --slice to assemble from what the shards fetched."))
    ap.add_argument("--limit", type=int, default=1500,
                    help="universe size for --universe broker (default: the scan's own 1500)")
    a = ap.parse_args(argv)

    # ARGUMENT VALIDATION FIRST, before the universe resolution, the SEC probe or any download.
    # A first cut checked this after resolving the universe, so a bad universe short-circuited
    # it and a malformed shard was never reported -- and the expensive work would already have
    # run by the time anyone found out the shard was nonsense.
    _si, _sn = 0, 1
    if a.slice:
        try:
            _si, _sn = (int(x) for x in str(a.slice).split("/", 1))
        except (TypeError, ValueError):
            print("REFUSED: --slice wants `i/n`, e.g. 0/3", file=sys.stderr)
            return 4
        if not (0 <= _si < _sn):
            print("REFUSED: --slice i must be in [0, n); got %s" % a.slice, file=sys.stderr)
            return 4

    if a.fidelity:
        r = fidelity_control(banked=a.banked or None, root=a.root or None)
        print("FIDELITY CONTROL")
        print("  runnable : %s" % r["runnable"])
        print("  ok       : %s" % r["ok"])
        print("  compared : %s   max |delta| %s" % (r["n_compared"], r["max_abs_delta"]))
        print("  %s" % r["reason"])
        if r.get("platform_note"):
            print("  NOTE: %s" % r["platform_note"])
        # A control that could not run exits NON-ZERO. It is not a pass.
        return 0 if r["ok"] else 1

    as_of = _dt.date.fromisoformat(a.as_of) if a.as_of else _dt.date.today()
    # DERIVED, THEN CHECKED AGAINST WHAT SEC HAS PUBLISHED. See
    # `newest_published_periods`: the 45-day derivation runs AHEAD of SEC's structured-data
    # schedule, so on 2026-09-30 it asks for a window that 404s after the first one has already
    # downloaded and aggregated.
    per = newest_published_periods(as_of)
    su = served_from_store()
    if a.universe:
        su = served_from_universe(a.universe, limit=a.limit)

    print("THEME CACHE BUILD")
    print("  as of        %s (13F lag %d days, from fundamental_panel._inst_accum)"
          % (per["as_of"], per["lag_days"]))
    print("  periods      %s (prior) -> %s (curr)   DERIVED, not pinned"
          % (per["prior"], per["curr"]))
    print("  windows      %s / %s" % (per["window_prior"], per["window_curr"]))
    print("  pinned were  %s / %s%s" % (M.PERIOD_PRIOR, M.PERIOD_CURR,
          "   <-- STALE" if M.PERIOD_CURR != per["curr"] else "   (same today)"))
    if per.get("stepped_back"):
        print("  STEPPED BACK %d quarter(s): the derived window is not published by SEC yet"
              % per["stepped_back"])
        for t in per.get("probed") or []:
            print("               %s  %s  published=%s" % (t["period"], t["window"],
                                                           t["published"]))
    if per.get("unpublished"):
        print("  REFUSING: no published 13F window within %d quarters" % 4)
    if a.slice:
        print("  shard        %d of %d (crawl only; assembly is skipped)" % (_si, _sn))
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
    # THE FORM 4 / CUSIP LEG GETS THE SAME UNIVERSE, not the pinned snapshot.
    #
    # `fetch_all` -> `load_served()` defaults to `live_theme_sources.SNAPSHOT`, a pinned
    # 2026-08-08 file that is not in this checkout -- so the build previously died AFTER both
    # 13F windows had downloaded and aggregated, which is the expensive half. Writing the
    # resolved universe in that function's own `{"rows": [...]}` shape means the leg is handed
    # the population the report already named, rather than learning a second way to be given a
    # universe.
    if a.universe:
        _served_path = os.path.join(os.path.dirname(cache_path()),
                                    "served_%s.json" % su["scan_date"].replace(":", "_"))
        with io.open(_served_path, "w", encoding="utf-8") as _fh:
            json.dump({"scan_date": su["scan_date"],
                       "rows": [{"ticker": t} for t in su["served"]]}, _fh)
        print("  served file  %s" % _served_path)
    else:
        _served_path = None
    M.fetch_all(snapshot=_served_path, slice_i=_si, slice_n=_sn)
    if a.slice:
        # A SHARD MUST NOT ASSEMBLE. It has fetched a third of the universe, so a cache built
        # here would cover a third and carry no sign of it -- the worst available outcome, since
        # a thin cache is indistinguishable from a complete one once written.
        print("SHARD %d/%d DONE - crawl only. Re-run with no --slice to assemble."
              % (_si, _sn))
        return 0

    out = F2.build_live(served=su["served"], period_curr=per["curr"],
                        period_prior=per["prior"], cache_path=cache_path(),
                        periods_source="derived from the calendar at %s (lag %d days)"
                                       % (per["as_of"], per["lag_days"]))
    print("built %s rows for %s served names" % (len(out["rows"]), out["n_served"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
