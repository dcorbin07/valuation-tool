"""
Sharadar freeze tests (offline, tiny fixtures). Run:
    python tests/test_freeze.py

The freeze derives the whole offline backtest layout by FILTERING multi-GB streams. That is
the same shape as the four bugs CLAUDE.md records — `assets` missing from an allowlist, the
SF3 positional-arg bug, five all-empty columns, `invcap`/`taxexp`/`ebt` missing from _KEEP —
where a filter quietly kept nothing and every downstream number read as "no data" instead of
raising. So each filter here gets a fixture that would FAIL if it silently kept the wrong rows.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import sharadar_freeze as F


def _write(dirpath, name, header, rows):
    p = os.path.join(dirpath, name)
    with open(p, "w", newline="", encoding="utf-8") as f:
        f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    return p


def _tmp():
    return tempfile.mkdtemp()


# --------------------------------------------------------------------------- #
def test_fresh_universe_matches_the_provider_ranking():
    """SF1-covered domestic common stock, micro-cap and up, most investable first —
    the same rule SharadarProvider.universe() applies, read off the bulk TICKERS export."""
    d = _tmp()
    p = _write(d, "tickers.csv", ["ticker", "table", "category", "scalemarketcap"],
               [("MEGA", "SF1", "Domestic Common Stock", "6 - Mega"),
                ("MICRO", "SF1", "Domestic Common Stock", "2 - Micro"),
                ("NANO", "SF1", "Domestic Common Stock", "1 - Nano"),       # below the floor
                ("ANETF", "SFP", "ETF", "5 - Large"),                        # not SF1-covered
                ("PREF", "SF1", "Domestic Preferred Stock", "5 - Large")])   # not common stock
    u = F._fresh_universe(p)
    assert u == ["MEGA", "MICRO"], u


def test_fresh_universe_respects_the_limit_biggest_first():
    d = _tmp()
    p = _write(d, "tickers.csv", ["ticker", "table", "category", "scalemarketcap"],
               [("SMALL", "SF1", "Domestic Common Stock", "3 - Small"),
                ("BIG", "SF1", "Domestic Common Stock", "6 - Mega")])
    assert F._fresh_universe(p, limit=1) == ["BIG"]


def test_live_tickers_is_the_floor_the_freeze_must_clear():
    """A name already on disk must survive into the freeze even if it has since shrunk out
    of the fresh top-N — that is what makes 'at least as complete' true by construction."""
    d = _tmp()
    os.makedirs(os.path.join(d, "prices"))
    open(os.path.join(d, "prices", "DELISTED.csv"), "w").close()
    _write(d, "fundamentals.csv", ["ticker", "datekey"], [("oldname", "2001-01-01")])
    got = F._live_tickers(d)
    assert got == {"DELISTED", "OLDNAME"}, got


def test_filter_csv_keeps_only_the_universe_and_honours_the_where_clause():
    """The ARQ filter is load-bearing: the derived fundamentals.csv must be ARQ-only to stay
    a drop-in for the live file, even though the frozen SF1 holds every dimension."""
    d = _tmp()
    src = _write(d, "sf1.csv", ["ticker", "dimension", "datekey", "revenue"],
                 [("AAA", "ARQ", "2020-01-01", 10),
                  ("AAA", "ART", "2020-01-01", 40),     # wrong dimension
                  ("BBB", "ARQ", "2020-01-01", 20),
                  ("ZZZ", "ARQ", "2020-01-01", 30)])    # outside the universe
    dest = os.path.join(d, "out.csv")
    rows, tick = F._filter_csv(src, dest, {"AAA", "BBB"},
                               where=lambda h, r: r[h.index("dimension")] == "ARQ")
    assert (rows, tick) == (2, {"AAA", "BBB"}), (rows, tick)
    with open(dest) as f:
        body = f.read()
    assert "ART" not in body and "ZZZ" not in body, body
    assert body.splitlines()[0].startswith("ticker,"), "header must be preserved"


def test_filter_csv_is_case_insensitive_on_the_ticker():
    d = _tmp()
    src = _write(d, "x.csv", ["ticker", "date"], [("aapl", "2020-01-01")])
    rows, _ = F._filter_csv(src, os.path.join(d, "o.csv"), {"AAPL"})
    assert rows == 1


def test_split_prices_writes_closeadj_not_close():
    """closeadj is split- AND dividend-adjusted. Writing raw `close` would make every
    pre-split return look like a crash — the exact bias the ACTIONS mask exists to avoid."""
    d = _tmp()
    out = os.path.join(d, "prices")
    os.makedirs(out)
    src = _write(d, "sep.csv", ["ticker", "date", "close", "closeadj"],
                 [("AAA", "2020-01-02", 100, 50),
                  ("AAA", "2020-01-03", 101, 51),
                  ("ZZZ", "2020-01-02", 9, 9)])
    got = F._split_prices(src, out, {"AAA"}, "t")
    assert got == {"AAA"}
    assert not os.path.exists(os.path.join(out, "ZZZ.csv"))
    with open(os.path.join(out, "AAA.csv")) as f:
        assert f.read() == "date,close\n2020-01-02,50\n2020-01-03,51\n"


def test_split_prices_survives_interleaved_tickers_and_multiple_flushes():
    """SEP is genuinely NOT ordered by ticker (row 1 ABILF, row 3 AAC.U) — so the split must
    survive arbitrary interleaving AND a mid-stream flush without losing rows or re-emitting
    the header into the middle of a file."""
    d = _tmp()
    out = os.path.join(d, "prices")
    os.makedirs(out)
    rows = []
    for i in range(3):
        for t in ("AAA", "BBB", "CCC"):
            rows.append((t, f"2020-01-0{i+1}", 1, i + 1))
    src = _write(d, "sep.csv", ["ticker", "date", "close", "closeadj"], rows)
    F._HandleCache.__init__.__defaults__ = (2,)          # force several flush rounds
    try:
        got = F._split_prices(src, out, {"AAA", "BBB", "CCC"}, "t")
    finally:
        F._HandleCache.__init__.__defaults__ = (2_000_000,)
    assert got == {"AAA", "BBB", "CCC"}
    for t in ("AAA", "BBB", "CCC"):
        with open(os.path.join(out, f"{t}.csv")) as f:
            lines = f.read().splitlines()
        assert lines == ["date,close", "2020-01-01,1", "2020-01-02,2", "2020-01-03,3"], (t, lines)


def test_split_prices_sorts_a_date_descending_source():
    """SEP arrives newest-first within a ticker. Writing it through unsorted would leave the
    freeze's price files in a different order from the live ones for no reason."""
    d = _tmp()
    out = os.path.join(d, "prices")
    os.makedirs(out)
    src = _write(d, "sep.csv", ["ticker", "date", "close", "closeadj"],
                 [("AAA", "2021-11-09", 1, 33), ("AAA", "2021-11-08", 1, 35),
                  ("AAA", "2020-01-02", 1, 10)])
    F._split_prices(src, out, {"AAA"}, "t")
    with open(os.path.join(out, "AAA.csv")) as f:
        assert f.read().splitlines() == ["date,close", "2020-01-02,10",
                                         "2021-11-08,35", "2021-11-09,33"]


def test_scan_csv_reports_rows_tickers_and_the_true_date_span():
    d = _tmp()
    p = _write(d, "x.csv", ["ticker", "datekey"],
               [("AAA", "2005-03-31"), ("AAA", "1998-01-01"), ("BBB", "2026-07-31")])
    r = F._scan_csv(p, "datekey")
    assert (r["rows"], r["tickers"]) == (3, 2)
    assert (r["date_min"], r["date_max"]) == ("1998-01-01", "2026-07-31")


def test_scan_csv_degrades_on_a_missing_or_headerless_file():
    """A dead download must read as 'not present' / 'empty', never crash the manifest run."""
    d = _tmp()
    assert F._scan_csv(os.path.join(d, "nope.csv"), "date") == {"present": False}
    p = os.path.join(d, "empty.csv")
    open(p, "w").close()
    assert F._scan_csv(p, "date")["rows"] == 0


def test_compare_live_flags_a_table_that_came_back_shorter():
    """A partial pull is the failure mode this whole job exists to catch: it looks like a
    successful freeze and is silently missing years."""
    root, live = _tmp(), _tmp()
    os.makedirs(os.path.join(root, "bulk"))
    os.makedirs(os.path.join(root, "backtest", "prices"))
    os.makedirs(os.path.join(live, "prices"))
    live_bulk = os.path.join(os.path.dirname(os.path.normpath(live)), "bulk")
    os.makedirs(live_bulk, exist_ok=True)
    with open(os.path.join(root, "bulk", "daily.csv"), "w") as f:
        f.write("x")                                     # 1 byte
    with open(os.path.join(live_bulk, "daily.csv"), "w") as f:
        f.write("x" * 100)                               # 100 bytes on disk already
    out = F._compare_live(root, live)
    short = [c["item"] for c in out if c["SHORT"]]
    assert "bulk/daily.csv size" in short, out


def test_aapl_checkpoint_reads_daily_marketcap_as_millions():
    """Sharadar's DAILY marketcap is in MILLIONS. AAPL 2015-06-30 is stored as 722571.4,
    which IS the $722.6B checkpoint in CLAUDE.md — verified byte-identical between the freeze
    and the live cache. Reading it as dollars makes a correct freeze report 0.0 and look
    like a failed pull, which is exactly the false alarm this whole job must not raise."""
    import pickle
    d = _tmp()
    cache = os.path.join(d, "bulk", "prepared")
    os.makedirs(cache)
    os.makedirs(os.path.join(d, "backtest", "prices"))
    with open(os.path.join(cache, "daily.pkl"), "wb") as f:
        pickle.dump({"AAPL": [("2015-06-30", 722571.4, 15.1, 5.6, 3.4, 10.1)]}, f)
    _write(os.path.join(d, "backtest"), "fundamentals.csv", ["ticker", "datekey"], [])
    chk = {c["check"]: c for c in F._checkpoints(d)}
    mc = [v for k, v in chk.items() if k.startswith("AAPL 2015Q2")][0]
    assert mc["pass"], mc
    assert mc["got"] == 722.6, mc


def test_manifest_never_contains_the_api_key():
    """The manifest is the one file from this job that gets committed."""
    src = open(F.__file__, encoding="utf-8").read()
    assert "api_key" not in src.split("def stage_manifest")[1], \
        "stage_manifest must never touch the key"


# --------------------------------------------------------------------------- #
def main():
    fns = [(k, v) for k, v in sorted(globals().items())
           if k.startswith("test_") and callable(v)]
    passed = 0
    for name, fn in fns:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {name}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(fns)} freeze tests passed")
    return 0 if passed == len(fns) else 1


if __name__ == "__main__":
    raise SystemExit(main())
