"""
Deep-chain harvest tests (offline, tiny fixtures). Run:
    python tests/test_deep_harvest.py

These pin the two defects that actually bit this harvest, both of the same family: a unit that
was short of a full year got recorded as though it were complete.

  * BUG 7 -- a quarter that ERRORED discarded the quarters that had already succeeded, so 26
    units of a late-listing population were thrown away entirely.
  * BUG 8 -- a quarter that returned ZERO ROWS was dropped in silence, so 19 units carried
    status `ok` (complete) while holding under 95% of their year.

Neither raised, neither logged, and both are only visible by comparing a unit against its own
year. That is the same shape as the four coverage bugs CLAUDE.md records, so the rules that
stop them recurring get fixtures rather than comments:

  * a repair may never SHRINK a unit -- a transient vendor hiccup during a repair must not
    destroy good data;
  * a relabel may never TOUCH a payload -- it corrects a record, not the bytes;
  * `ok` must mean the whole year.
"""
import datetime as dt
import json
import os
import pickle
import shutil
import sys
import tempfile

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mine_deep_chains as M


# ------------------------------------------------------------------ fixtures

def _root():
    return tempfile.mkdtemp(prefix="harvest_")


def _payload(root, sym, year, months):
    """Write a unit whose rows fall only in `months`, plus its manifest record."""
    dates = [dt.date(year, m, 5) for m in months]
    df = pd.DataFrame({"date": dates,
                       "expiration": [dt.date(year, 12, 20)] * len(dates),
                       "strike": [100.0] * len(dates),
                       "right": ["C"] * len(dates),
                       "bid": [1.0] * len(dates), "ask": [1.1] * len(dates),
                       "volume": [1] * len(dates), "open_interest": [1] * len(dates)})
    p = M.unit_path(root, sym, year)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        pickle.dump({"schema": 1, "symbol": sym, "year": year, "rows": df}, f, protocol=5)
    rec = {"tier": "T", "symbol": sym, "year": year, "status": "ok",
           "rows": len(df), "dates": len(dates), "bytes": os.path.getsize(p),
           "sha256": M.sha256(p), "utc": "2026-08-18T00:00:00+00:00"}
    M.append_manifest(root, rec)
    return p, rec


# ------------------------------------------------------------------ short_units

def test_a_unit_missing_a_whole_quarter_is_flagged_and_a_full_one_is_not():
    root = _root()
    _payload(root, "FULL", 2020, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    _payload(root, "SHORT", 2020, [4, 5, 6, 7, 8, 9])
    got = {u["symbol"] for u in M.short_units(root)}
    assert got == {"SHORT"}, f"expected only SHORT flagged, got {got}"


def test_the_reference_is_the_years_own_best_not_a_weekday_calendar():
    """A weekday is not a trading day. The bar is what the vendor actually served that year."""
    root = _root()
    # nothing in this year reaches 12 months; the best observed IS the bar
    _payload(root, "AAA", 2021, [1, 2, 3, 4, 5, 6])
    _payload(root, "BBB", 2021, [1, 2, 3, 4, 5, 6])
    assert M.short_units(root) == [], "no unit is short when none beats it"
    _payload(root, "CCC", 2021, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    got = {u["symbol"] for u in M.short_units(root)}
    assert got == {"AAA", "BBB"}, f"a longer sibling should move the bar, got {got}"


# ------------------------------------------------------------------ relabel

def test_relabel_corrects_ok_to_ok_partial_and_names_the_empty_quarters():
    root = _root()
    _payload(root, "FULL", 2020, [1, 4, 7, 10])
    _payload(root, "SHORT", 2020, [4, 5, 6])              # Q1, Q3, Q4 empty
    out = M.relabel(root)
    assert len(out["relabelled"]) == 1, out
    r = out["relabelled"][0]
    assert r["symbol"] == "SHORT" and r["now"] == "ok_partial", r
    assert r["quarters_empty"] == ["Q1", "Q3", "Q4"], r
    man = M.load_manifest(root)
    assert man["SHORT|2020"]["status"] == "ok_partial"
    assert man["SHORT|2020"]["quarters_empty"] == ["Q1", "Q3", "Q4"]
    assert man["FULL|2020"]["status"] == "ok", "a complete unit must not be relabelled"


def test_relabel_never_touches_the_payload():
    """It corrects a RECORD. If it can rewrite bytes it is a re-pull wearing a label's name."""
    root = _root()
    _payload(root, "FULL", 2020, [1, 4, 7, 10])
    p, rec = _payload(root, "SHORT", 2020, [4, 5, 6])
    before = open(p, "rb").read()
    M.relabel(root)
    assert open(p, "rb").read() == before, "relabel rewrote the payload"
    man = M.load_manifest(root)
    assert man["SHORT|2020"]["sha256"] == rec["sha256"], "hash changed without a re-pull"
    assert man["SHORT|2020"]["bytes"] == rec["bytes"]


def test_relabel_is_idempotent():
    root = _root()
    _payload(root, "FULL", 2020, [1, 4, 7, 10])
    _payload(root, "SHORT", 2020, [4, 5, 6])
    assert len(M.relabel(root)["relabelled"]) == 1
    second = M.relabel(root)
    assert second["relabelled"] == [], f"second pass re-corrected: {second}"
    assert second["already_correct"] == 1


# ------------------------------------------------------------------ repair

def test_a_repair_may_never_shrink_a_unit():
    """The rule that makes repair safe to run unattended.

    A vendor hiccup during a repair would otherwise overwrite a good year with a short one --
    turning a tool meant to recover data into one that destroys it.
    """
    root = _root()
    _payload(root, "FULL", 2020, [1, 4, 7, 10])
    p, rec = _payload(root, "SHORT", 2020, [4, 5, 6])
    before = open(p, "rb").read()

    real = M.pull_unit

    def worse(tb, sym, year, r):
        with open(M.unit_path(r, sym, year), "wb") as f:      # a re-pull DOES write
            pickle.dump({"schema": 1, "symbol": sym, "year": year,
                         "rows": pd.DataFrame({"date": [dt.date(year, 4, 5)]})}, f, protocol=5)
        return {"status": "ok", "dates": 1, "rows": 1, "bytes": 1, "sha256": "x"}

    M.pull_unit = worse
    try:
        out = M.repair(root, dry=False)
    finally:
        M.pull_unit = real

    assert out["improved"] == [], f"a shorter re-pull was accepted: {out}"
    assert len(out["confirmed_short"]) == 1
    assert open(p, "rb").read() == before, "the payload was not restored byte-for-byte"
    assert not os.path.exists(p + ".prerepair"), "the safety copy was left behind"
    assert M.load_manifest(root)["SHORT|2020"]["sha256"] == rec["sha256"]


def test_a_repair_that_improves_is_recorded_with_both_counts():
    root = _root()
    _payload(root, "FULL", 2020, [1, 4, 7, 10])
    _payload(root, "SHORT", 2020, [4, 5, 6])
    real = M.pull_unit

    def better(tb, sym, year, r):
        return {"status": "ok", "dates": 99, "rows": 99, "bytes": 5, "sha256": "y"}

    M.pull_unit = better
    try:
        out = M.repair(root, dry=False)
    finally:
        M.pull_unit = real
    assert len(out["improved"]) == 1, out
    imp = out["improved"][0]
    assert (imp["before"], imp["after"]) == (3, 99), imp
    rec = M.load_manifest(root)["SHORT|2020"]
    assert rec["repair"]["dates_before"] == 3 and rec["repair"]["dates_after"] == 99


# ------------------------------------------------------------------ tier scopes

def test_tier_e_selects_exactly_the_shallow_units_that_exist():
    """E is the names holding a shallow 2016-2018 unit; C is the names holding none.

    Disjoint by construction, and the disjointness is what stops an expiring window being spent
    pulling the same symbol-year twice. Checked behaviourally against a synthetic cache rather
    than by reading the source, so a rewrite that keeps the comment and loses the rule fails.
    """
    fake = tempfile.mkdtemp(prefix="opt_")
    os.makedirs(os.path.join(fake, "AAA"))
    os.makedirs(os.path.join(fake, "BBB"))
    open(os.path.join(fake, "AAA", "AAA-2016.pkl"), "wb").close()
    open(os.path.join(fake, "AAA", "AAA-2018.pkl"), "wb").close()
    open(os.path.join(fake, "BBB", "BBB-2017.pkl.empty"), "wb").close()   # tri-state sidecar
    real = M.OPT
    M.OPT = fake
    try:
        units, _ = M.tier_e_units()
    finally:
        M.OPT = real
    assert sorted(units) == [("E", "AAA", 2016), ("E", "AAA", 2018)], units
    assert all(u[1] != "BBB" for u in units), \
        "a `.empty` sidecar is not a payload -- that name belongs to tier C, not E"


# ------------------------------------------------------------------ BUG 9: the current year

def test_a_quarter_that_has_not_happened_yet_is_never_requested():
    """The current year is not a whole year.

    Tier D pulled 2026 on 2026-08-18 and the first two units came back `failed` -- Q4
    NoDataFoundError, Q3 a gRPC fault -- which threw away seven months of 2026 the vendor serves
    perfectly well, and would have re-probed them on every restart forever. BUG 7's repair does
    not catch it, because a gRPC fault is not NoDataFound.
    """
    seen = []

    class _Cli:
        def option_history_eod(self, start_date, end_date, symbol, expiration, max_dte):
            seen.append((start_date, end_date))
            return None

    class _TB:
        def _cli(self):
            return _Cli()

    root = _root()
    horizon = dt.date.today() - dt.timedelta(days=1)
    rec = M.pull_unit(_TB(), "CUR", horizon.year, root)

    assert seen, "no request was made at all"
    assert all(e <= horizon for _, e in seen), (
        f"a request reached past the last completed session: {seen}")
    started = {s.month for s, _ in seen}
    for q in range(4):
        q_start = dt.date(horizon.year, 1 + q * 3, 1)
        if q_start > horizon:
            assert (1 + q * 3) not in started, f"Q{q+1} has not started and was requested anyway"
    assert rec.get("quarters_future"), "a future quarter must be recorded, not silently dropped"


def test_a_future_quarter_is_not_recorded_as_a_missing_one():
    """`quarters_future` is the calendar; `quarters_missing` is a fault. A live year that reads
    as damaged would re-pull forever and would look like a data defect in the census."""
    src = open(M.__file__, encoding="utf-8").read()
    assert '"quarters_future": future_q or None' in src
    assert '"pulled_through"' in src, "a partial-because-live year must say how far it reaches"


def test_relabel_does_not_call_a_future_quarter_empty():
    root = _root()
    yr = dt.date.today().year
    _payload(root, "FULL", yr, [1, 2])
    _payload(root, "SHORT", yr, [1])
    out = M.relabel(root)
    for r in out["relabelled"]:
        for q in r["quarters_empty"]:
            qi = int(q[1]) - 1
            assert dt.date(yr, 1 + qi * 3, 1) <= dt.date.today(), \
                f"{q} of {yr} has not started and was called empty"


def test_terminal_statuses_are_never_re_probed():
    """An irreplaceable window may not be spent re-confirming a negative the cache already holds."""
    root = _root()
    for st in ("empty", "empty_vendor"):
        M.append_manifest(root, {"symbol": f"S{st}", "year": 2016, "status": st})
    man = M.load_manifest(root)
    for st in ("empty", "empty_vendor"):
        assert not M.needs_pull(root, f"S{st}", 2016, man), f"{st} would be re-probed"
    M.append_manifest(root, {"symbol": "SFAIL", "year": 2016, "status": "failed"})
    assert M.needs_pull(root, "SFAIL", 2016, M.load_manifest(root)), \
        "a real fault must still retry"


if __name__ == "__main__":
    fns = [(k, v) for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  ok  {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {name}\n      {e}")
        except Exception as e:                       # noqa: BLE001
            failed += 1
            print(f"ERR   {name}\n      {type(e).__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
