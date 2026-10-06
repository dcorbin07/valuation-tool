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


def newest_published_periods(as_of=None, max_back: int = 4, guard=None,
                            patient: bool = True) -> dict:
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
    per = latest_complete_periods(as_of) if as_of else latest_complete_periods()
    # THE RUN'S REAL CLOCK, KEPT SEPARATE FROM THE DERIVATION'S -- and the two coming apart is
    # the "as of" discrepancy item 32 asks about. Stepping back a quarter is implemented by
    # MOVING THE CLOCK (`as_of - 95 days`) and re-deriving, so `per["as_of"]` is a SYNTHETIC
    # PAST DATE after any step-back, not the day the job ran. On 2026-10-04 one step back makes
    # it 2026-10-04 - 95d = 2026-07-01 exactly, which is why the shard step printed "as of
    # 2026-07-01" (it stepped back once and confirmed 31-MAR-2026) while the assemble step
    # printed "as of 2026-10-04" (its probe was throttled before it stepped anywhere). Neither
    # was wrong about the date; the field was being read as "today" when it means "the clock
    # these periods were derived from". Both now travel.
    _real_as_of = per["as_of"]
    tried = []
    g = guard or (M.Guard() if hasattr(M, "Guard") else None)
    for _ in range(max_back):
        # THE URL COMES FROM THE DOWNLOADER'S OWN CONSTANT (B7). Rebuilding it here would be a
        # second copy of SEC's path, and the probe would then be able to say "published" about a
        # URL the downloader never fetches.
        url = M.DATASET_URL.format(window=per["window_curr"])
        # A REFUSAL IS NOT AN ABSENCE, AND READING IT AS ONE IS THE DEFECT THIS CLOSES.
        #
        # This used to be a raw `requests.head` with `ok = r.status_code == 200`, which collapses
        # three answers into two: a 429 became "not published". On 2026-10-04 that walked back
        # four quarters, declared every one unpublished -- `30-SEP-2025` among them, whose 13Fs
        # were due in November 2025 -- printed "not published by SEC yet", and then took a 429
        # on the GET. Three crawl shards had just finished hammering SEC and this probe went out
        # unpaced, because `main()` did not build its `Guard` until thirty lines later.
        #
        # `head_published` is the module that OWNS the SEC status vocabulary (`B7`), on the same
        # `Guard`. `Throttled` STOPS THE WALK rather than counting as a miss: stepping back on a
        # rate-limit asks four more questions of a server that has just refused one, and records
        # four more false absences on the way.
        # NO GUARD IS ALSO "UNKNOWN". My own first cut of this fell back to `ok = False`, which
        # is the SAME conflation one level up: unable to ASK becomes "not published". If the
        # pacing machinery is not importable the honest answer is that nothing was determined.
        if g is None:
            tried.append({"period": per["curr"], "window": per["window_curr"],
                          "published": None,
                          "throttled": "no Guard available; the probe was not made"})
            per = dict(per)
            per["probed"] = tried
            per["stepped_back"] = len(tried) - 1
            per["undetermined"] = True
            per["run_as_of"] = _real_as_of
            return per
        try:
            ok = M.head_published(url, g, patient=patient)
        except getattr(M, "Throttled", ()) as exc:                      # noqa: B014
            tried.append({"period": per["curr"], "window": per["window_curr"],
                          "published": None, "throttled": str(exc)})
            per = dict(per)
            per["probed"] = tried
            per["stepped_back"] = len(tried) - 1
            per["undetermined"] = True
            per["run_as_of"] = _real_as_of
            return per
        except Exception:                                               # noqa: BLE001
            ok = False
        tried.append({"period": per["curr"], "window": per["window_curr"], "published": ok})
        if ok:
            per = dict(per)
            per["probed"] = tried
            per["stepped_back"] = len(tried) - 1
            per["run_as_of"] = _real_as_of
            return per
        # One quarter earlier. `latest_complete_periods` takes an as-of, so move the clock.
        import datetime as _dt
        base = _dt.date.fromisoformat(str(per["as_of"])) - _dt.timedelta(days=95)
        per = latest_complete_periods(base)
    per = dict(per)
    per["probed"] = tried
    per["stepped_back"] = len(tried)
    per["unpublished"] = True
    per["run_as_of"] = _real_as_of
    return per


def aggregate_covers(per: dict, root: str = None) -> bool:
    """Is the 13F aggregate on disk already the two periods `per` derives?

    WHY THIS IS WORTH A FUNCTION: if it is, there is NOTHING TO CONFIRM. An aggregate exists only
    because some earlier step downloaded and aggregated that window, which means SEC served it --
    so probing is spending a request on a question already answered, and on GitHub's shared
    runner IPs that request is the scarce thing.

    IT IS THE SAME TEST `build_13f` ALREADY MAKES before deciding to skip the download
    (`cached["periods"] == [PERIOD_PRIOR, PERIOD_CURR]`), read here so the probe and the
    download agree about what "already have it" means. Two different answers to that would mean
    skipping the probe and then downloading anyway, which is the worst of both.
    """
    root = root or M.DEFAULT_ROOT
    agg = M._read_json(os.path.join(root, "13f_aggregate.json")) or {}
    return (agg.get("periods") or []) == [per.get("prior"), per.get("curr")]


def _stale_label(n: int) -> str:
    """`13F one quarter stale` — the exact wording item 32 asks for, pluralised honestly.

    It goes into the cache's own `periods_source`, which is what `live_themes.py` reads, so a
    consumer cannot see the data without seeing the label. A staleness recorded only in a log
    line is a staleness nobody downstream can act on.
    """
    if n <= 0:
        return "13F current"
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    return "13F %s quarter%s stale" % (words.get(n, str(n)), "" if n == 1 else "s")


def periods_from_labels(curr_label: str, prior_label: str, run_as_of: str) -> dict:
    """`latest_complete_periods`'s shape, rebuilt from two period LABELS.

    The windows are DERIVED with `filing_window` rather than stored, so a fallback cannot name a
    window the downloader would not fetch -- the same `B7` reason the probe takes its URL from
    the downloader's own constant.
    """
    c = _dt.datetime.strptime(curr_label, "%d-%b-%Y").date()
    p = _dt.datetime.strptime(prior_label, "%d-%b-%Y").date()
    return {"as_of": run_as_of, "lag_days": INST_LAG_DAYS,
            "curr": period_label(c), "prior": period_label(p),
            "window_curr": filing_window(c), "window_prior": filing_window(p),
            "curr_date": c.isoformat(), "prior_date": p.isoformat(),
            "run_as_of": run_as_of}


def confirmed_fallback(per: dict, root: str = None) -> dict | None:
    """The newest 13F window this run can actually HAVE, when the derived one is unconfirmable.

    TWO SOURCES, NEWEST FIRST, and both are things that were CONFIRMED PUBLISHED rather than
    guessed at:

      1. **a window this run's own probe confirmed** before it was throttled or ran out of
         step-backs. (With the probe walking newest-first a confirm ENDS the walk, so this can
         only be non-empty when the walk ended for a different reason -- it is here because the
         walk's contract permits it, not because it fires today.)
      2. **the window of the 13F aggregate already ON DISK.** This is the one that fires, and it
         is not a guess either: an aggregate exists only because some earlier step downloaded
         and aggregated that window, which means SEC served it. On the sharded workflow it is
         the window the CRAWL SHARDS confirmed -- `13f_aggregate.json` travels to the assemble
         job in the artifact (only the zips are excluded, for size), so the fallback needs NO
         SEC REQUEST AT ALL. That is the whole reason this is the right fallback rather than
         "probe one quarter older": a probe can be throttled, and a file cannot.

    Returns None when there is nothing confirmed to fall back to, because inventing a window
    here would be exactly the conflation item 28 removed one level up.
    """
    run_as_of = per.get("run_as_of") or per.get("as_of")
    for t in reversed(per.get("probed") or []):
        if t.get("published") is True:
            # The label is the CURRENT period; its prior is the quarter before it.
            c = _dt.datetime.strptime(t["period"], "%d-%b-%Y").date()
            pr = quarter_end_on_or_before(c - _dt.timedelta(days=1))
            out = periods_from_labels(t["period"], period_label(pr), run_as_of)
            out["fallback_source"] = "a window this run's probe confirmed"
            return out
    root = root or M.DEFAULT_ROOT
    agg = M._read_json(os.path.join(root, "13f_aggregate.json")) or {}
    periods = agg.get("periods") or []
    if len(periods) == 2:
        try:
            out = periods_from_labels(periods[1], periods[0], run_as_of)
        except ValueError:
            return None
        out["fallback_source"] = ("the 13F aggregate already on disk (downloaded and aggregated "
                                  "by an earlier step, so SEC served that window)")
        return out
    return None


def quarters_between(newer_iso: str, older_iso: str) -> int:
    """How many quarters a fallback is behind the derived window. 0 if it is not behind."""
    a = _dt.date.fromisoformat(newer_iso)
    b = _dt.date.fromisoformat(older_iso)
    return max(0, (a.year - b.year) * 4 + (a.month - b.month) // 3)


def write_served_file(su: dict, path: str) -> str:
    """Write the served universe where `load_served` can read it back.

    EXTRACTED so a test can call THIS rather than re-implement it. The round-trip test that was
    supposed to pin the shape built its own file instead, so it tested the test and the writer
    stayed uncovered -- a mutation that re-broke the writer went undetected. B7, in a test.

    `su["served"]` IS ALREADY `load_served`'s row shape, so it is written straight through. A
    first cut wrapped each element as `{"ticker": t}` on the assumption it was a bare string --
    correct while `served_from_universe` wrongly returned strings, and wrong the moment that was
    fixed, at which point it produced `{"ticker": {...dict...}}` and `fetch_all` died on
    `tkr.upper()`. TWO consumers read this file and they do NOT disagree about the shape: both
    want dicts, and the two crashes were ONE defect surfacing at two depths.
    """
    # ITEM 28 -- THE PARENT DIRECTORY IS CREATED, BECAUSE A FRESH RUNNER HAS NO `data/`.
    #
    # This is where the themes job died: manual run #541 (2026-10-04), all three shards, three
    # seconds into "Crawl shard N", with `FileNotFoundError: [Errno 2] No such file or
    # directory: 'data/live_cache/served_broker_top_1500.json'`. **THE JOB HAD NEVER ONCE BEEN
    # ABLE TO RUN**, and the reason is a conjunction of three ordinary facts: `data/` is
    # gitignored so the checkout brings no directories; the workflow's cache restore lists only
    # `data/live_themes/*`, so `data/live_cache/` is created by nobody; and this was the FIRST
    # write of the run, so it failed before anything else could.
    #
    # It never showed up locally because every machine that has ever run this already had a
    # `data/live_cache/` from some earlier scan -- the directory is a side effect of history,
    # not of the code, so the code's dependence on it was invisible.
    #
    # `exist_ok=True` and `or "."` for the same reason `_atomic_write_json` in
    # `live_theme_sources.py` has them: a bare filename has no dirname, and `makedirs("")`
    # raises. That function is the pattern here rather than the import, because this script
    # deliberately keeps its plumbing local -- its own comment says *"kept local so this script
    # has no dependency on that one's internals"* -- and reaching into it for one line would
    # trade a one-line duplication for a coupling that comment exists to prevent.
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as fh:
        json.dump({"scan_date": su["scan_date"], "rows": su["served"]}, fh)
    return path


def _period_end(per: dict) -> str:
    """The ISO date the CURRENT 13F period ends on, from the period label the builder derived.

    The labels are Sharadar-style (`31-MAR-2026`), so this parses that form rather than inventing
    a second place where the quarter end is decided -- if the label and the date disagreed, the
    market cap would be dated to a quarter the 13F values do not come from, which is the exact
    mismatch this change removes.
    """
    import datetime as _dt
    lab = str(per.get("curr") or "")
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return _dt.datetime.strptime(lab, fmt).date().isoformat()
        except (TypeError, ValueError):
            continue
    raise SystemExit("cannot read a period end from the 13F period label %r -- refusing rather "
                     "than dating the market cap to a guess" % lab)


def period_market_caps(served, period_end: str, root: str = None, batch=None) -> dict:
    """`{ticker: detail}` -- shares outstanding AT the 13F period end times the close ON it.

    **WHY THIS EXISTS, AND IT IS A CORRECTNESS FIX RATHER THAN AN ENRICHMENT.** `join_13f`'s
    anchor is `institutional dollars held / market cap`, bounded in `(0, ANCHOR_MAX]`, and it is
    what stops a fuzzy name match being accepted as the right issuer. Session 69 measured that
    the shipped path divides a 13F value as of the PERIOD END by a market cap as of TODAY -- with
    the period 183 days behind, market drift moves every anchor at once, loosening the guard on
    every name after a rally and manufacturing `anchor_failed` after a selloff. Both halves are
    now dated to the same day.

    **FAIL CLOSED, DELIBERATELY.** A name with no shares level, or no close on or before the
    period end, gets `market_cap: None` -- which makes the anchor REFUSE that name rather than
    score it against a guessed denominator. The whole point of the anchor is that it declines
    what it cannot verify, so filling a gap here would defeat the thing being repaired.

    **IT NEEDS NO SCAN STORE**, which is what lets the assemble job run on a fresh runner: the
    shares come from SEC companyfacts via the xbrl leg's own cache and the close from the price
    vendors. Nothing here reads a saved scan.

    `batch` is injectable for tests; production passes `prices.get_history_batch`.
    """
    from valuation.screener import prices as _prices
    import scripts.live_theme_sources as M

    root = root or M.DEFAULT_ROOT
    want = str(period_end)[:10]
    tickers = [r["ticker"] for r in served]

    # The PRICE leg, batched. `days` is generous on purpose: the frame has to reach back PAST the
    # period end, and a window that merely touches it would leave a name unpriced whenever the
    # period end is a holiday or the vendor is missing that single session.
    try:
        span = (_dt.date.today() - _dt.date.fromisoformat(want)).days + 120
    except (TypeError, ValueError):
        span = 500
    fetch = batch or _prices.get_history_batch
    frames = fetch(tickers, days=max(span, 120)) or {}

    out = {}
    for r in served:
        t = r["ticker"]
        x = M._read_json(M.leg_path(root, "xbrl", t)) or {}
        sh = x.get("shares_level")
        d = {"shares": sh, "shares_end": x.get("shares_level_end"),
             "shares_days_stale": x.get("shares_level_days_stale"),
             "shares_form": x.get("shares_level_form"),
             "close": None, "close_date": None, "market_cap": None, "reason": ""}
        if sh is None:
            d["reason"] = "no shares-outstanding level at or before %s" % want
            out[t] = d
            continue
        px, pxd = _close_on_or_before(frames.get(t), want)
        if px is None:
            d["reason"] = "no close at or before %s" % want
            out[t] = d
            continue
        d["close"], d["close_date"] = px, pxd
        # THE SPLIT CHECK, AND IT REFUSES RATHER THAN CORRECTS. The close is back-adjusted to
        # today while the share count is in the terms of its own filing, so a split in between
        # makes the product wrong by exactly the split factor -- and a 2-for-1 would HALVE the
        # cap and DOUBLE the anchor, moving a name across the bar for a reason that has nothing
        # to do with whether the CUSIP match is right. Correcting it would mean trusting the
        # tape's ratio to rescale a guard's denominator; refusing costs one name and cannot be
        # wrong in a direction nobody sees.
        f = split_between(t, want, _dt.date.today().isoformat())
        d["split_factor"] = f
        # WHETHER THE TAPE COULD SPEAK FOR THIS NAME AT ALL, counted rather than assumed.
        #
        # `_split_table` reads `data/bulk/actions.csv`, which is Sharadar-licensed, gitignored
        # and UNTRACKED -- so on a GitHub runner it does not exist, the table is empty, and
        # `split_between` returns 1.0 for every name. That is a guard failing OPEN, and silently:
        # the build would look identical while checking nothing. Measured locally, 12 of 1,500
        # names split in the window at ratios up to 25x, so the thing being skipped is real.
        #
        # Not a refusal: gating the whole free route on a licensed file would defeat its purpose.
        # It is COUNTED, and the count is printed and stored, so "no splits found" and "no tape
        # to look in" can never read the same.
        d["split_checked"] = bool(_split_table())
        if f != 1.0:
            d["reason"] = ("split %.4gx between %s and today, so the adjusted close and the "
                           "as-filed share count are not comparable" % (f, want))
            out[t] = d
            continue
        d["market_cap"] = float(sh) * float(px)
        out[t] = d
    return out


def _close_on_or_before(frame, want: str):
    """`(close, date)` for the last session at or before `want`, or `(None, None)`.

    NEVER a later session: a close from after the period end is look-ahead for a period-end
    market cap, and it would make the anchor's denominator newer than its numerator -- the exact
    mismatch this whole change removes.

    **THE FRAME'S SHAPE IS A DATE COLUMN AND AN INTEGER INDEX, NOT A DATE INDEX.** A first cut
    read `frame.index` for dates and looked for a lowercase `close`/`raw_close`; both price paths
    actually return `['Date', 'Open', 'High', 'Low', 'Close', 'Volume']` with a positional index,
    so it found no date it could compare and reported "no close at or before 2026-03-31" for
    **1,457 of 1,500 names** -- a total failure that looked exactly like a coverage problem.
    Reading the wrong object, again, and the symptom imitated a data gap.
    """
    if frame is None or getattr(frame, "empty", True):
        return None, None
    # NO `or []` ON AN INDEX: pandas raises `The truth value of a Index is ambiguous` on a
    # truthiness test, so the usual empty-default idiom is a crash here rather than a
    # fallback. Converted first, defaulted second.
    cols = list(frame.columns) if hasattr(frame, "columns") else []
    lower = {str(c).lower(): c for c in cols}
    col = next((lower[k] for k in ("raw_close", "close") if k in lower), None)
    dcol = next((lower[k] for k in ("date",) if k in lower), None)
    if col is None:
        return None, None
    try:
        if dcol is not None:
            dates = [str(x)[:10] for x in frame[dcol]]
        else:
            dates = [str(i)[:10] for i in frame.index]
    except Exception:                                                    # noqa: BLE001
        return None, None
    best = None
    for i, dt in enumerate(dates):
        if dt <= want and (best is None or dt > best[1]):
            v = frame[col].iloc[i]
            if v is not None and v == v and float(v) > 0:
                best = (float(v), dt)
    return best if best else (None, None)


def split_between(ticker: str, lo: str, hi: str, actions=None) -> float:
    """Cumulative split factor for `ticker` strictly after `lo` and up to `hi`. 1.0 if none.

    **THIS EXISTS BECAUSE A BACK-ADJUSTED CLOSE AND AN AS-OF-DATE SHARE COUNT DO NOT MULTIPLY.**
    The price vendors return a split-adjusted series, so a close at the period end is expressed
    in TODAY's share terms, while the shares-outstanding level is in the terms of ITS filing. A
    split in between makes `shares x close` wrong by exactly the split factor -- a 2-for-1 would
    halve the market cap and so DOUBLE the anchor, pushing a good name over the bar or a bad one
    under it. This project has paid for that confusion once already (`raw_close` for anything
    touching a share count, adjusted only for a return).

    Read from the ACTIONS tape, which is a local file and needs no network. A name the tape does
    not cover returns 1.0 and the caller treats that as "no KNOWN split" -- which is why the
    census reports how many names the tape could speak for.
    """
    if actions is None:
        actions = _split_table()
    f = 1.0
    for d, ratio in actions.get(str(ticker).upper(), ()):
        if str(lo)[:10] < d <= str(hi)[:10] and ratio and ratio > 0:
            f *= float(ratio)
    return f


_SPLITS = None


def _split_table() -> dict:
    """`{TICKER: [(date, ratio), ...]}` from the ACTIONS tape, loaded once."""
    global _SPLITS
    if _SPLITS is not None:
        return _SPLITS
    import csv
    out = {}
    for cand in (os.path.join("data", "bulk", "actions.csv"),
                 os.path.join("data", "backtest", "actions.csv")):
        pth = _primary(cand)
        if not pth or not os.path.exists(pth):
            continue
        try:
            with io.open(pth, encoding="utf-8", errors="replace") as fh:
                for row in csv.DictReader(fh):
                    if str(row.get("action") or "") != "split":
                        continue
                    t = str(row.get("ticker") or "").upper()
                    try:
                        r = float(row.get("value") or 0) or 0.0
                    except (TypeError, ValueError):
                        continue
                    if t and r > 0:
                        out.setdefault(t, []).append((str(row.get("date") or "")[:10], r))
        except OSError:
            continue
        break
    _SPLITS = out
    return out


def _primary(rel: str):
    """`rel` under the PRIMARY repo root, because a worktree's `data/` is empty.

    The same resolution the reconstruction needed: `data/` is gitignored, so a path relative to
    the worktree finds nothing and a bare `os.path.exists` reports a populated file as absent.
    """
    here = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    for base in (here, os.path.abspath(os.path.join(here, "..", "..", ".."))):
        c = os.path.join(base, rel)
        if os.path.exists(c):
            return c
    return os.path.join(here, rel)


def attach_period_caps(served, caps: dict) -> dict:
    """Overwrite each served row's `market_cap` with the period-end one. Census returned.

    OVERWRITE, not fill: the broker universe supplies no cap at all and the scan store supplies a
    CURRENT one, and a current cap is the defect. A row whose period cap could not be computed
    gets `None` so the anchor refuses it -- it is never left holding a live cap that would pass
    the guard for the wrong reason.
    """
    n_set = n_none = n_split_checked = 0
    for r in served:
        d = caps.get(r["ticker"]) or {}
        c = d.get("market_cap")
        r["market_cap"] = c
        r["market_cap_basis"] = "period_end"
        if d.get("split_checked"):
            n_split_checked += 1
        if c is None:
            n_none += 1
        else:
            n_set += 1
    return {"n_set": n_set, "n_none": n_none, "n": len(served),
            "n_split_checked": n_split_checked,
            "split_tape": ("present" if n_split_checked else
                           "ABSENT -- the split guard checked NOTHING on this run")}


def _as_served_rows(rows) -> list:
    """`served_from_store`'s row shape, from anything carrying a `ticker`.

    ONE converter, so the two universe sources cannot drift into two shapes -- which is exactly
    what happened when this function did not exist. De-duplicated and sorted by ticker so a
    source returning the same name twice cannot inflate the crawl.
    """
    out, seen = [], set()
    for r in rows or []:
        t = str((r or {}).get("ticker") or "").strip().upper()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append({"ticker": t, "name": (r or {}).get("name") or "",
                    "market_cap": (r or {}).get("market_cap"),
                    "sector": (r or {}).get("sector") or ""})
    out.sort(key=lambda r: r["ticker"])
    return out


def served_from_universe(spec: str, limit: int = 1500) -> dict:
    """`served_from_store`'s shape, from the broker ranking or a ticker file.

    SAME SHAPE, deliberately, so nothing downstream learns a second way to be handed a
    universe -- the build path, the refusal and the reporting are all unchanged.

    AND THE FIRST CUT VIOLATED THAT SENTENCE WHILE ASSERTING IT. It returned a list of plain
    TICKER STRINGS against `served_from_store`'s list of dicts, so the crawl ran happily for two
    hours over 1,500 names and then `join_13f` died on `row["ticker"]` with
    `TypeError: string indices must be integers`. The docstring made it HARDER to spot, not
    easier: it stated the invariant confidently enough that nobody checked it, which is the
    failure mode of a comment that documents an intention rather than a measurement.

    `market_cap` and `sector` are carried through as whatever the source gives -- the broker
    ranking returns `market_cap: None` and `sector: ""` -- and are NOT filled in. A fabricated
    market cap here would be indistinguishable from a real one downstream.

    `scan_date` is set to the SOURCE rather than left blank, because a cache is only meaningful
    beside a statement of which population it covers, and "built for the broker top 1500" is a
    different claim from "built for the names the 2026-09-30 scan served".
    """
    if spec == "broker":
        from valuation.config import CONFIG
        from valuation.screener import broker_universe
        rows = broker_universe.build(CONFIG, limit=limit) or []
        served = _as_served_rows(rows)
        return {"served": served, "scan_date": "broker_top_%d" % limit,
                "reason": "the broker liquidity ranking" if served
                          else "the broker universe came back empty"}
    try:
        with io.open(spec, encoding="utf-8") as fh:
            served = _as_served_rows(
                [{"ticker": ln.strip()} for ln in fh if ln.strip()])
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
    # ONE GUARD FOR THE WHOLE RUN, BUILT BEFORE THE FIRST SEC CALL. It used to be created
    # thirty lines below this, AFTER the publication probe had already gone out unpaced -- which
    # is how the probe came to be rate-limited by the crawl shards that ran minutes earlier. A
    # shared guard also means the probe's refusals count against the same circuit breaker as
    # the download's, which is the point of having a budget at all.
    guard = M.Guard() if hasattr(M, "Guard") else None
    # SPEND NO SEC REQUEST ON A QUESTION ALREADY ANSWERED (item 32(1)).
    #
    # The ordering the item asks for -- 13F before the Form 4 crawl -- IS ALREADY HOW main()
    # runs: `build_13f` is called ~20 lines before `fetch_all`, in the shard step too. Measured
    # on run 37237240057, that is not where the budget goes: the three shards crawl 14,504
    # documents over ~11 minutes and the ASSEMBLE JOB starts afterwards, so its 13F probe is
    # first within its own job and still arrives after eleven minutes of three-way hammering.
    # Re-ordering inside one job cannot fix a budget spent across jobs.
    #
    # WHAT DOES FIX IT is not asking. `13f_aggregate.json` TRAVELS from the shards to the
    # assemble job in the artifact (only the zips are excluded, for size), so when the shards
    # have already built the window the assemble step needs, the answer is on disk and the probe
    # is pure cost. `build_13f` would skip the download anyway; this skips the CONFIRMATION too.
    _derived = latest_complete_periods(as_of)
    if aggregate_covers(_derived):
        per = dict(_derived)
        per["run_as_of"] = _derived["as_of"]
        per["probe_skipped"] = ("the 13F aggregate on disk already covers this window, so SEC "
                                "has served it and there is nothing to confirm")
    else:
        per = newest_published_periods(as_of, guard=guard)
    # FALL BACK TO A CONFIRMED WINDOW RATHER THAN WRITING NOTHING (item 32).
    #
    # Refusing was the right fix for reading a 429 as "not published" -- but on GitHub's SHARED
    # RUNNER IPs it can mean the job never completes, which trades a wrong cache for no cache.
    # A cache one quarter behind, LABELLED, is better than no cache: `institutional` and
    # `insider` contribute nothing at all without one, which is the state the live check has
    # been reporting as 0.00.
    #
    # THE FALLBACK IS A CONFIRMED WINDOW, NEVER A GUESSED ONE -- see `confirmed_fallback`. In
    # the sharded workflow it is the window the CRAWL SHARDS confirmed, read off the aggregate
    # they handed over, so it costs NO SEC REQUEST. If nothing is confirmed there is nothing to
    # fall back to and the run still refuses.
    _fallback_note = None
    # CAPTURED BEFORE THE FALLBACK REPLACES `per`, because otherwise the fallback SILENCES THE
    # DIAGNOSIS: the "CANNOT DETERMINE" line below keys on `per["undetermined"]`, and the
    # fallback dict does not carry it. My first cut did exactly that -- it fell back correctly
    # and stopped saying why, which is the shape of defect this whole item is about.
    _probe_undetermined = bool(per.get("undetermined"))
    _probe_unpublished = bool(per.get("unpublished"))
    if per.get("undetermined") or per.get("unpublished"):
        _fb = confirmed_fallback(per)
        if _fb:
            _stale = quarters_between(per["curr_date"], _fb["curr_date"])
            _fb["stale_quarters"] = _stale
            _fb["stale_label"] = _stale_label(_stale)
            _fb["derived_curr"] = per["curr"]
            _fb["derived_window_curr"] = per["window_curr"]
            _fb["fallback_reason"] = ("the derived window could not be confirmed published"
                                      + (" (SEC refused the probe)"
                                         if per.get("undetermined") else ""))
            _fb["probed"] = per.get("probed")
            _fallback_note = _fb
            per = _fb
    su = served_from_store()
    if a.universe:
        su = served_from_universe(a.universe, limit=a.limit)

    print("THEME CACHE BUILD")
    # BOTH CLOCKS, because they come apart and item 32 asked why. `as_of` is the clock the
    # PERIODS were derived from, and a step-back moves it into the past (`- 95 days` per
    # quarter) -- which is why one step back on 2026-10-04 prints 2026-07-01. `run_as_of` is the
    # day the job ran. Two steps printing different "as of" values were both correct and the
    # label was wrong.
    print("  as of        %s (13F lag %d days, from fundamental_panel._inst_accum)"
          % (per["as_of"], per["lag_days"]))
    if per.get("probe_skipped"):
        print("  probe        SKIPPED -- %s" % per["probe_skipped"])
    if per.get("run_as_of") and per["run_as_of"] != per["as_of"]:
        print("  run date     %s   <-- the job's own clock; 'as of' above is the clock the "
              "periods were DERIVED from, moved back by the step-back" % per["run_as_of"])
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
    # TWO DIFFERENT SENTENCES, BECAUSE THEY ARE TWO DIFFERENT FACTS AND ONLY ONE IS ABOUT SEC'S
    # SCHEDULE. "No published window" is a statement about publication; "SEC would not say" is a
    # statement about this run. Printing the first when the second is true is what sent a reader
    # looking for a filing deadline that had passed eleven months earlier.
    if _probe_undetermined:
        print("  CANNOT DETERMINE: SEC refused the publication probe (rate-limited), so "
              "whether the window is published is UNKNOWN -- not 'unpublished'.")
        for t in per.get("probed") or []:
            if t.get("throttled"):
                print("               %s  %s  %s" % (t["period"], t["window"], t["throttled"]))
    if _probe_unpublished:
        print("  REFUSING: no published 13F window within %d quarters" % 4)
    if _fallback_note:
        print("  FELL BACK:   %s -> %s (%s)"
              % (_fallback_note["derived_window_curr"], _fallback_note["window_curr"],
                 _fallback_note["stale_label"]))
        print("               %s" % _fallback_note["fallback_reason"])
        print("               source: %s" % _fallback_note["fallback_source"])
        print("               the cache is LABELLED with this, so a consumer cannot read the "
              "data without the staleness")
    if a.slice:
        print("  shard        %d of %d (crawl only; assembly is skipped)" % (_si, _sn))
    print("  served       %s from scan %s" % (len(su["served"]), su["scan_date"]))
    print("  cache        %s" % cache_path())

    if not su["served"]:
        print("REFUSED: %s" % su["reason"], file=sys.stderr)
        return 3
    if a.dry_run:
        # CORRECTED 2026-10-04: this said "no SEC request was made" and that was FALSE, and
        # measurably so -- `newest_published_periods` probes SEC's dataset URL above, before
        # this branch is reached, and with the pacing repair it may now make up to
        # `MAX_ATTEMPTS` of them. A dry run that claims to touch nothing while touching the
        # vendor is the kind of sentence someone reaches for precisely when they want to check
        # something safely.
        # AND IT SAYS WHAT A REAL RUN WOULD DO, which is the thing a dry run is actually for
        # and the thing it did not say. Added 2026-10-04 with the fallback: the decision -- build
        # from the derived window, build from a stale confirmed one, or refuse -- is made from
        # the probe's answer and the aggregate on disk, both of which are known HERE, before any
        # price fetch or crawl. Printing it is what lets the decision be checked without doing
        # the work, and it is what the suite asserts on rather than letting the run proceed into
        # a live vendor.
        if (_probe_undetermined or _probe_unpublished) and not _fallback_note:
            print("WOULD REFUSE: the 13F window cannot be confirmed published and there is no "
                  "confirmed window to fall back to.")
        elif _fallback_note:
            print("WOULD BUILD, LABELLED: %s (from %s)"
                  % (_fallback_note["stale_label"], _fallback_note["window_curr"]))
        else:
            print("WOULD BUILD from the derived window %s (13F current)." % per["window_curr"])
        print("DRY RUN - nothing was written. ONE SEC request class was made: the publication "
              "probe above (paced, retried, HEAD only). No dataset was downloaded.")
        return 0

    # AND THE RUN STOPS, WHICH IT DID NOT BEFORE. The old code printed "REFUSING" and then
    # downloaded the window anyway -- a refusal that does not refuse. It sits AFTER the dry-run
    # report on purpose (my own first cut put it before, which silenced the diagnosis in the one
    # mode whose whole job is to print it): `--dry-run` should SAY what it found and exit 0.
    # Exit 4 is distinct from the served-universe refusal above (3) so a scheduler can tell
    # "SEC is rate-limiting, try later" from "this build has no universe" -- different problems,
    # different fixes. `undetermined` is RETRYABLE and `unpublished` is not; both stop here.
    if (_probe_undetermined or _probe_unpublished) and not _fallback_note:
        print("REFUSED: the 13F window could not be confirmed published AND there is no "
              "confirmed window to fall back to (no aggregate on disk and nothing confirmed by "
              "this run's probe); refusing to download and aggregate a window this run could "
              "not verify.", file=sys.stderr)
        return 4

    # THE SEC LEGS RUN FIRST, through the IMPORTED machinery. `build_13f` downloads and
    # aggregates the structured zips; `fetch_all` walks the CUSIP ladder and the signed Form 4
    # crawl. Neither is reimplemented here.
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
        write_served_file(su, _served_path)
        print("  served file  %s" % _served_path)
    else:
        _served_path = None
    # `shares_asof` makes the xbrl leg keep the shares-outstanding LEVEL at the period end,
    # which is GAP 1's missing denominator. `_period_end` is the ONE place the quarter end
    # is derived, so the level and the 13F values cannot end up dated to different quarters.
    M.fetch_all(snapshot=_served_path, slice_i=_si, slice_n=_sn,
                shares_asof=_period_end(per))
    # THE FORM 4 LEG THE CACHE ACTUALLY READS, and until now nothing ran it.
    #
    # THE DEFECT, measured on the 2026-10-05 build: `theme_columns.json` came out with
    # `insider_score` coverage **0.012** against `inst_accum` 0.8547, and the live hot list
    # showed `theme_contributing.insider` 0.01 against `institutional` 0.83. There were TWO
    # insider producers and the cache writer read the one nothing filled:
    #
    #   * `M.fetch_all`'s `insider` leg writes `live_themes/insider/<t>.json` -- it ran for all
    #     1,500 names, and it TRAVELS to the assemble job in the artifact;
    #   * `F2.build_live` reads `live_themes/form4_live/<t>.json` (`_f4 = f4_dir or
    #     F4_DIR_LIVE`), written ONLY by `F2.fetch4(current=True)` -- which `main()` never
    #     called. The workflow also deliberately keeps `form4_live` out of both the cache and
    #     the artifact, so it starts empty in this job every time.
    #
    # THE FIX IS TO RUN THE MISSING PRODUCER, NOT TO REPOINT THE READER, and the panel settles
    # which is right. `insider_detail` (the crawl leg) returns **50.0** for a quiet window;
    # `insider_score_from_txns` (what `build_live` uses) returns **None**. The panel's own
    # `_insider_score` returns `None` when `net == 0 and buys == 0` -- so the gated formula
    # matches the panel and the 50.0 is the deviation. Repointing the reader at the crawl leg
    # would have lifted coverage to ~85% of names ALL SITTING AT EXACTLY 50, which is the
    # 179-name tie block `FIDELITY-2` rejected: it would have looked fixed and measured nothing.
    #
    # WHY COVERAGE SHOULD CLEAR THE BAR ONCE THIS RUNS: the panel scores insider over the SAME
    # 90-day lookback and reaches 83.1% coverage, so a correctly-populated window is expected to
    # land near there rather than near zero.
    #
    # IT RUNS IN THE ASSEMBLE JOB ONLY. A shard crawls a third of the universe, and `fetch4`
    # SKIPS any name whose payload already exists -- so a shard's partial `form4_live` would be
    # indistinguishable from a complete one to the next step. The shards return below without
    # reaching this.
    if not a.slice:
        print("  form 4       crawling the CURRENT window into form4_live (the directory "
              "build_live reads)", flush=True)
        F2.fetch4(current=True, snapshot=_served_path)

    if a.slice:
        # A SHARD MUST NOT ASSEMBLE. It has fetched a third of the universe, so a cache built
        # here would cover a third and carry no sign of it -- the worst available outcome, since
        # a thin cache is indistinguishable from a complete one once written.
        print("SHARD %d/%d DONE - crawl only. Re-run with no --slice to assemble."
              % (_si, _sn))
        return 0

    # THE PERIOD-END MARKET CAP, BETWEEN THE CRAWL AND THE ASSEMBLY (GAP 1).
    #
    # `join_13f`'s anchor divides a 13F dollar value by a market cap, and until now the two came
    # from different dates -- the 13F from the period end, the cap from today. With the period
    # 183 days behind, market drift moved every anchor at once. Both halves are now dated to the
    # period end, and a name whose cap cannot be computed is left at None so the anchor REFUSES
    # it rather than scoring it against a guess.
    _pend = _period_end(per)
    _caps = period_market_caps(su["served"], _pend)
    _cen = attach_period_caps(su["served"], _caps)
    print("  period cap   %s: %d of %d priced, %d left None (anchor will refuse those)"
          % (_pend, _cen["n_set"], _cen["n"], _cen["n_none"]))
    print("  split guard  %s (%d of %d names checkable against the ACTIONS tape)"
          % (_cen["split_tape"], _cen["n_split_checked"], _cen["n"]))
    _stale = [d["shares_days_stale"] for d in _caps.values()
              if d.get("shares_days_stale") is not None]
    if _stale:
        _stale.sort()
        print("  shares lag   median %d days, p95 %d, max %d (level at or before %s, never after)"
              % (_stale[len(_stale) // 2], _stale[int(len(_stale) * 0.95)], _stale[-1], _pend))

    # THE STALENESS TRAVELS IN THE CACHE, not only in this log. `periods_source` is what
    # `live_themes.py` reads, so a consumer cannot see the columns without seeing that they are
    # a quarter behind -- which is the difference between a labelled fallback and a quiet one.
    _src = "derived from the calendar at %s (lag %d days)" % (per["as_of"], per["lag_days"])
    if _fallback_note:
        _src = ("%s -- %s: fell back from the derived %s because %s; %s"
                % (_src, _fallback_note["stale_label"],
                   _fallback_note["derived_window_curr"],
                   _fallback_note["fallback_reason"],
                   _fallback_note["fallback_source"]))
    out = F2.build_live(served=su["served"], period_curr=per["curr"],
                        period_prior=per["prior"], cache_path=cache_path(),
                        periods_source=_src)
    print("built %s rows for %s served names" % (len(out["rows"]), out["n_served"]))
    # THE INSIDER COLUMN GETS ITS OWN LINE, because it is the one that was silently empty and a
    # coverage dict buried in a `wrote ...` line is what let 0.012 go unnoticed for a build.
    _cov = (out.get("coverage") or {})
    if "insider_score" in _cov:
        _ic = _cov["insider_score"]
        # THE THIRD CAUSE WAS MISSING AND IT WAS THE ACTUAL ONE. This line named two
        # possibilities -- an unpopulated directory and a quiet quarter -- and the 2026-10-06
        # build was neither: SEC refused 963 of 1,116 names' documents and `fetch4` banked the
        # refusals as parse failures. A reader checking the two causes offered would have found
        # `form4_live` populated and the quarter busy, and had nowhere left to look. The crawl
        # now prints its own LOST line directly above this one.
        print("  insider      coverage %.4f%s" % (_ic, "" if _ic >= 0.5 else
              "   <-- BELOW 0.5: read the crawl's LOST line above. Either SEC refused the "
              "documents, form4_live was not populated, or the window is genuinely quiet -- "
              "they are different failures and the crawl says which."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
