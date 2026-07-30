"""
Sharadar BULK loader tests (offline, tiny fixtures). Run:
    python tests/test_bulk.py

These exist because bulk.py shipped without them and immediately cost us: prepare_sf3()
silently returned ZERO rows for the whole 79M-row file because main() passed `rebuild`
positionally into what was then the `security_type` parameter, so the filter compared
securitytype to True. It reported success. test_sf3_keyword_binding_regression below is
the one-line check that would have caught it, and the panel now depends on this code.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import bulk


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
#  fixtures mirroring the real bulk schemas
# --------------------------------------------------------------------------- #
def _sf3_fixture(d):
    # Two managers, two quarters, one ticker each + a CLL row that must be ignored.
    # BIG has a $900 book, SMALL has $100 — so the same $50 position is far more
    # conviction for SMALL, which is exactly what the AUM-relative measure should show.
    return _write(d, "sf3.csv",
                  ["ticker", "investorname", "securitytype", "calendardate", "value", "units", "price"],
                  [("AAA", "BIG", "SHR", "2024-03-31", 850, 10, 85),
                   ("BBB", "BIG", "SHR", "2024-03-31", 50, 5, 10),
                   ("BBB", "SMALL", "SHR", "2024-03-31", 50, 5, 10),
                   ("BBB", "SMALL", "SHR", "2024-03-31", 50, 5, 10),   # second lot, same qtr
                   ("BBB", "BIG", "CLL", "2024-03-31", 9999, 1, 1),    # calls: must be excluded
                   ("AAA", "BIG", "SHR", "2024-06-30", 800, 9, 88),
                   ("BBB", "BIG", "SHR", "2024-06-30", 100, 9, 11)])


def _daily_fixture(d):
    return _write(d, "daily.csv",
                  ["ticker", "date", "lastupdated", "ev", "evebit", "evebitda",
                   "marketcap", "pb", "pe", "ps"],
                  [("AAA", "2024-01-10", "x", 1, 1, 8.0, 100.0, 2.0, 15.0, 3.0),
                   ("AAA", "2024-01-31", "x", 1, 1, 9.0, 110.0, 2.1, 16.0, 3.1),  # month-end
                   ("AAA", "2024-02-15", "x", 1, 1, 9.5, 120.0, 2.2, 17.0, 3.2),
                   ("BBB", "2024-01-20", "x", 1, 1, 5.0, 50.0, 1.0, 9.0, 1.5)])


def _actions_fixture(d):
    return _write(d, "actions.csv",
                  ["date", "action", "ticker", "name", "value", "contraticker", "contraname"],
                  [("2020-08-31", "split", "AAA", "A Co", 4.0, "N/A", "N/A"),
                   ("2014-06-09", "split", "AAA", "A Co", 7.0, "N/A", "N/A"),
                   ("2024-02-01", "dividend", "AAA", "A Co", 0.24, "N/A", "N/A"),
                   ("2008-12-31", "delisted", "DEAD", "Dead Co", "", "N/A", "N/A"),
                   ("2024-03-01", "split", "BAD", "Bad Co", "", "N/A", "N/A")])  # no ratio


def _events_fixture(d):
    return _write(d, "events.csv", ["ticker", "date", "eventcodes"],
                  [("AAA", "2024-02-01", "22|91"), ("AAA", "2024-01-01", "11"),
                   ("BBB", "2024-03-01", "57")])


def _insiders_fixture(d):
    return _write(d, "insiders.csv",
                  ["ticker", "filingdate", "date", "transactionshares",
                   "transactionpricepershare", "transactionvalue"],
                  [("AAA", "2024-02-05", "2024-02-01", 100, 10, 1000),
                   ("AAA", "2024-01-05", "2024-01-01", -50, 10, -500),
                   ("BBB", "2024-02-05", "2024-02-01", 20, 5, "")])   # value derived from sh*px


# --------------------------------------------------------------------------- #
#  each prepare_* returns non-empty with the expected shape
# --------------------------------------------------------------------------- #
def test_prepare_sf3_shape_and_conviction():
    d = _tmp()
    out = bulk.prepare_sf3(_sf3_fixture(d), cache_dir=os.path.join(d, "c"))
    assert out, "SF3 must not be empty — this is the zero-rows failure mode"
    assert set(out) == {"AAA", "BBB"}, out.keys()
    q = out["BBB"]["2024-03-31"]
    assert set(q) == {"holders", "value", "conviction"}
    # BBB 2024-03-31: BIG one lot at 50, SMALL two lots at 50 => 3 holder-rows, value 150.
    assert q["holders"] == 3, q
    assert abs(q["value"] - 150.0) < 1e-9, q
    # Calls excluded: the 9999 CLL row must not appear anywhere.
    assert q["value"] < 9999
    # Conviction: BIG's book is 850+50=900, SMALL's is 100.
    #   BIG  50/900 = 0.0556 ; SMALL 50/100 + 50/100 = 1.0  -> 1.0556
    assert abs(q["conviction"] - (50 / 900 + 1.0)) < 1e-6, q["conviction"]
    # A concentrated small fund contributes far more conviction than a giant's token stake.
    assert q["conviction"] > out["AAA"]["2024-03-31"]["conviction"]


def test_sf3_keyword_binding_regression():
    """The actual bug: `rebuild` landing in `security_type` filtered out every row.

    Calling positionally the way main() did must still work now that the signature puts
    rebuild third, and passing rebuild by keyword must never be mistaken for a filter.
    """
    d = _tmp()
    path = _sf3_fixture(d)
    by_kw = bulk.prepare_sf3(path, cache_dir=os.path.join(d, "k"), rebuild=True)
    by_pos = bulk.prepare_sf3(path, os.path.join(d, "p"), True)      # 3rd positional = rebuild
    assert by_kw, "keyword call returned nothing"
    assert by_pos, "positional call returned nothing — rebuild bound to the wrong parameter"
    assert by_kw == by_pos
    # And an explicit security_type still filters as intended.
    only_calls = bulk.prepare_sf3(path, cache_dir=os.path.join(d, "c2"),
                                  rebuild=True, security_type="CLL")
    assert list(only_calls) == ["BBB"], only_calls
    assert only_calls["BBB"]["2024-03-31"]["value"] == 9999


def test_prepare_daily_keeps_month_end_only():
    d = _tmp()
    out = bulk.prepare_daily(_daily_fixture(d), cache_dir=os.path.join(d, "c"))
    assert set(out) == {"AAA", "BBB"}
    # January had two rows; only the later one survives, and rows stay ascending.
    jan = [r for r in out["AAA"] if r[0].startswith("2024-01")]
    assert len(jan) == 1 and jan[0][0] == "2024-01-31", out["AAA"]
    assert [r[0] for r in out["AAA"]] == sorted(r[0] for r in out["AAA"])
    # (date, marketcap, pe, pb, ps, evebitda) — order matters, _daily_at unpacks positionally.
    assert jan[0] == ("2024-01-31", 110.0, 16.0, 2.1, 3.1, 9.0), jan[0]


def test_prepare_actions_split_parse():
    d = _tmp()
    out = bulk.prepare_actions(_actions_fixture(d), cache_dir=os.path.join(d, "c"))
    a = out["AAA"]
    assert a["splits"] == [("2014-06-09", 7.0), ("2020-08-31", 4.0)], a["splits"]
    assert a["dividends"] == [("2024-02-01", 0.24)]
    assert a["delisted"] is None
    assert out["DEAD"]["delisted"] == "2008-12-31"
    # A split row with no ratio must be dropped, not stored as None/0.
    assert out["BAD"]["splits"] == []


def test_prepare_events_keeps_raw_codes_and_earnings_is_inert():
    d = _tmp()
    out = bulk.prepare_events(_events_fixture(d), cache_dir=os.path.join(d, "c"))
    assert out["AAA"] == [("2024-01-01", ["11"]), ("2024-02-01", ["22", "91"])], out["AAA"]
    # Deliberately inert until the code legend is confirmed — must NOT invent dates.
    assert bulk.earnings_dates(out, "AAA") == []
    # ...but works the moment a caller supplies codes.
    assert bulk.earnings_dates(out, "AAA", codes={"91"}) == ["2024-02-01"]


def test_prepare_insiders_streams_and_derives_value():
    d = _tmp()
    out = bulk.prepare_insiders(_insiders_fixture(d), cache_dir=os.path.join(d, "c"))
    assert out["AAA"] == [("2024-01-05", -500.0), ("2024-02-05", 1000.0)], out["AAA"]
    # Missing transactionvalue is derived from shares x price rather than dropped.
    assert out["BBB"] == [("2024-02-05", 100.0)], out["BBB"]


def test_caches_are_reused_and_rebuild_forces_a_reread():
    d = _tmp()
    path = _actions_fixture(d)
    cache = os.path.join(d, "c")
    first = bulk.prepare_actions(path, cache_dir=cache)
    assert os.path.exists(os.path.join(cache, "actions.pkl"))
    # Truncate the source: a cache hit must still return the original data...
    open(path, "w").close()
    assert bulk.prepare_actions(path, cache_dir=cache) == first
    # ...and rebuild must actually re-read (now-empty) source.
    assert bulk.prepare_actions(path, cache_dir=cache, rebuild=True) == {}


def test_missing_files_degrade_to_empty():
    """A absent bulk table must return {} so every consumer falls back, not crash."""
    d = _tmp()
    miss = os.path.join(d, "nope.csv")
    for fn in (bulk.prepare_sf3, bulk.prepare_daily, bulk.prepare_actions,
               bulk.prepare_events, bulk.prepare_insiders):
        assert fn(miss, cache_dir=os.path.join(d, "c")) == {}, fn.__name__


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} bulk tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
