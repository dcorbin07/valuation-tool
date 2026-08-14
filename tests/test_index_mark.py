"""PT-WRITER — the documented price mechanism for the bound Valquo Index forward track.

`valuation/screener/index_mark.py` exists because the recorder lane refused to write on
2026-08-10 and dated its refusal: "the mechanism for retrieving daily closing prices ... is
NOT DOCUMENTED IN THIS REPOSITORY", and it would not guess at a vendor. These tests are
written against the ways a price mechanism goes wrong, not against the happy path:

  * THE REQUIRED PIN — `test_the_emitted_row_reads_back_through_index_track_unchanged`. The
    row this mechanism emits must be the row `index_track.load()` reads. A writer that emits
    a column the reader ignores fails SILENTLY on both sides, so the round trip is asserted
    end to end rather than the header being eyeballed.
  * THE ENDPOINT AND THE SCRIPT MUST BE THE SAME NUMBER
    (`test_the_endpoint_returns_exactly_what_the_module_computes`). Two doors onto one
    function is fine; two implementations is the B7 split this project keeps paying for.
  * REFUSING MUST RETURN NO NUMBER. Every refusal path is asserted to carry `row: None`
    (`test_no_refusal_path_ever_leaks_a_number`). A mechanism that fills a gap with its best
    guess is worse than no mechanism, because the gap is then invisible.
  * THE CONVENTION IS CUMULATIVE-SINCE-INCEPTION, not daily
    (`test_the_marks_are_cumulative_since_inception_and_not_daily_returns`). Writing a daily
    return into those columns yields a plausible file that silently re-bases the whole track.
  * AN UNPRICED NAME IS NOT A ZERO RETURN
    (`test_an_unpriced_name_is_dropped_rather_than_held_flat`) — treating it as flat drags
    the mark toward zero in exactly the weeks a data outage is most likely.

Prices are injected in every test, so the whole mechanism runs offline against fixed
numbers. A price path that can only be exercised against the live internet is a path nobody
exercises — and the one test that names REAL recorded values
(`test_it_reproduces_the_recorded_2026_08_06_benchmark_mark`) pins the arithmetic that was
verified against live Stooq data when the module was written.

Run: python tests/test_index_mark.py
"""
from __future__ import annotations

import csv
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_mark              # noqa: E402
from valuation.screener import index_track             # noqa: E402
from valuation.screener import market_session          # noqa: E402

INCEPTION = "2026-07-30"


# --------------------------------------------------------------------------------------
# A deterministic price tape. `prices.get_history_df` returns a DataFrame with Date/Close;
# this builds one from a dict so a test can state exactly what priced and what did not.
# --------------------------------------------------------------------------------------
def _tape(mapping: dict):
    import pandas as pd

    def fetch(ticker, days=400):
        series = mapping.get(ticker.upper())
        if series is None:
            return None
        return pd.DataFrame({"Date": list(series.keys()), "Close": list(series.values())})
    return fetch


def _book(tmpdir, positions=None, inception=INCEPTION, benchmark="SPY"):
    """Write a tracker meta file shaped exactly like the real `valquo_track.json`."""
    positions = positions if positions is not None else [
        {"ticker": "AAA", "weight": 0.5}, {"ticker": "BBB", "weight": 0.5}]
    p = os.path.join(tmpdir, "valquo_track.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"inception_date": inception, "scan_date": "2026-07-24",
                   "benchmark": benchmark, "positions": positions}, f)
    return p


#: A tape where the book doubles nothing and the numbers are chosen so the expected answer
#: is checkable by hand: AAA +10%, BBB -2%, equal weight -> +4.0%; SPY +1%.
_SIMPLE = {
    "AAA": {INCEPTION: 100.0, "2026-08-06": 110.0},
    "BBB": {INCEPTION: 50.0, "2026-08-06": 49.0},
    "SPY": {INCEPTION: 400.0, "2026-08-06": 404.0},
}


def _row(tmpdir, tape=None, **kw):
    return index_mark.contract_row("2026-08-06", meta_path=_book(tmpdir, **kw),
                                   fetch=_tape(tape or _SIMPLE))


# =======================================================================================
# THE REQUIRED PIN
# =======================================================================================
def test_the_emitted_row_reads_back_through_index_track_unchanged():
    """The row this mechanism emits IS the row the reader reads. End to end, not by eye."""
    with tempfile.TemporaryDirectory() as d:
        res = _row(d)
        assert res["ok"], res.get("reason")
        row = res["row"]
        hist = os.path.join(d, "valquo_track_history.csv")
        wrote = index_mark.append_row(row, hist)
        assert wrote["ok"], wrote.get("reason")

        loaded = index_track.load(meta_path=_book(d), history_path=hist)
        assert len(loaded["series"]) == 1, loaded["series"]
        got = loaded["series"][0]
        assert got["date"] == row["date"], (got, row)
        assert abs(got["valquo"] - row["valquo_pct"]) < 1e-12, (got, row)
        assert abs(got["spy"] - row["spy_pct"]) < 1e-12, (got, row)
        assert abs(got["excess"] - row["excess_pp"]) < 1e-12, (got, row)
        assert abs(got["n_priced"] - row["n_priced"]) < 1e-12, (got, row)


def test_the_header_is_exactly_what_index_track_reads():
    """A column the writer invents and the reader ignores is silent on both sides."""
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        index_mark.append_row(_row(d)["row"], hist)
        with open(hist, encoding="utf-8", newline="") as f:
            header = next(csv.reader(f))
        assert tuple(header) == index_mark.ROW_COLUMNS, header
        # every field index_track.load() reaches for by name is present
        for needed in ("date", "valquo_pct", "spy_pct", "excess_pp", "n_priced"):
            assert needed in header, needed


def test_the_endpoint_returns_exactly_what_the_module_computes():
    """Two doors onto one function. Two implementations would be the B7 split again."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "saas", "app_saas.py"), encoding="utf-8").read()
    i = src.find("def admin_track_row")
    assert i > 0, "the /admin/track-row route is gone"
    body = src[i:i + 2000]
    assert "index_mark.contract_row" in body, "the endpoint does not delegate to the module"
    # It must not do its own arithmetic: no price maths anywhere in the handler.
    for forbidden in ("get_history_df", "/ base", "valquo_pct =", "* 100.0"):
        assert forbidden not in body, "the endpoint re-implements the mark: " + forbidden


def test_the_LIVE_endpoint_row_equals_what_index_track_reads_back():
    """The literal ask, driven end to end through Flask rather than by reading source.

    The route is exercised with a fixed tape, its row is written, and `index_track.load()`
    reads it back. If the endpoint ever grew its own arithmetic, or emitted a column the
    reader ignores, this is where it shows — the source-level delegation test above cannot
    see either failure.
    """
    from valuation.config import CONFIG
    from valuation.saas.app_saas import create_saas_app
    from valuation.screener import prices

    CONFIG.admin_token = "test-token-index-mark"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True

    # The book and the history both land on the temp paths state_isolation redirects to.
    meta_path, hist_path = index_track.default_paths()
    os.makedirs(os.path.dirname(os.path.abspath(meta_path)), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"inception_date": INCEPTION, "benchmark": "SPY",
                   "positions": [{"ticker": "AAA", "weight": 0.5},
                                 {"ticker": "BBB", "weight": 0.5}]}, f)

    real = prices.get_history_df
    prices.get_history_df = _tape(_SIMPLE)
    try:
        c = app.test_client()
        hdr = {"X-Admin-Token": CONFIG.admin_token}
        assert c.get("/admin/track-row?date=2026-08-06").status_code in (401, 403), \
            "the endpoint answered without a token"
        r = c.get("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert r.status_code == 200, r.status_code
        body = r.get_json()
        assert body.get("ok") is True, body
        row = body["row"]
        assert body.get("append", {}).get("ok") is True, body.get("append")

        series = index_track.load(meta_path=meta_path, history_path=hist_path)["series"]
        assert len(series) == 1, series
        got = series[0]
        assert got["date"] == row["date"], (got, row)
        assert abs(got["valquo"] - row["valquo_pct"]) < 1e-12, (got, row)
        assert abs(got["spy"] - row["spy_pct"]) < 1e-12, (got, row)
        assert abs(got["excess"] - row["excess_pp"]) < 1e-12, (got, row)
        # and it is the hand-checkable answer, not merely self-consistent
        assert abs(row["valquo_pct"] - 4.0) < 1e-9, row
        assert abs(row["spy_pct"] - 1.0) < 1e-9, row
    finally:
        prices.get_history_df = real
        try:
            os.remove(hist_path)
        except OSError:
            pass


def test_a_refusal_is_a_200_and_not_a_500():
    """A 5xx tells a scheduler to retry something that is not broken."""
    from valuation.config import CONFIG
    from valuation.saas.app_saas import create_saas_app
    from valuation.screener import prices

    CONFIG.admin_token = "test-token-index-mark"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True

    # Self-contained: this must fail on the DATE, not on a missing book, or it would pass
    # for the wrong reason whenever it happens to run before the test that writes one.
    meta_path, _ = index_track.default_paths()
    os.makedirs(os.path.dirname(os.path.abspath(meta_path)), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"inception_date": INCEPTION, "benchmark": "SPY",
                   "positions": [{"ticker": "AAA", "weight": 1.0}]}, f)

    real = prices.get_history_df
    prices.get_history_df = _tape(_SIMPLE)
    try:
        c = app.test_client()
        r = c.get("/admin/track-row?date=2026-08-08",          # a Saturday
                  headers={"X-Admin-Token": CONFIG.admin_token})
        assert r.status_code == 200, r.status_code
        body = r.get_json()
        assert body.get("ok") is False and body.get("row") is None, body
        assert "trading day" in (body.get("reason") or ""), body
    finally:
        prices.get_history_df = real


def test_the_script_delegates_to_the_same_module():
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "scripts", "track_row.py")
    src = open(p, encoding="utf-8").read()
    assert "index_mark.contract_row" in src, "the CLI does not delegate to the module"
    for forbidden in ("get_history_df", "* 100.0"):
        assert forbidden not in src, "the CLI re-implements the mark: " + forbidden


def test_the_cli_can_be_pointed_at_a_book_outside_its_own_checkout():
    """`data/` is gitignored, so a recorder running from a worktree or a fresh clone has no
    book at the default path. Found the hard way: the first live run of this CLI could not
    reach the real 86-name book at all. Without `--book` the mechanism is unusable from
    exactly the places an automated writer is most likely to run."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as d:
        # A Saturday, so it refuses on the DATE — no network, fast, and it still proves the
        # book was found and parsed rather than missed.
        book = _book(d)
        out = subprocess.run([sys.executable, "-m", "scripts.track_row",
                              "--date", "2026-08-08", "--book", book],
                             cwd=root, capture_output=True, text=True, timeout=180)
        assert out.returncode == 2, (out.returncode, out.stderr[-400:])
        assert "not a trading day" in (out.stderr + out.stdout), out.stderr[-400:]
        assert "missing or unreadable" not in (out.stderr + out.stdout), \
            "--book was ignored; the CLI looked at the default path"


def test_the_cli_exit_code_distinguishes_a_row_from_a_refusal():
    """Exit 0 means a row exists; exit 2 means it refused. A scheduler branches on this, and
    a mechanism that exits 0 on a refusal would look like it wrote every day."""
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with tempfile.TemporaryDirectory() as d:
        out = subprocess.run([sys.executable, "-m", "scripts.track_row",
                              "--date", "2026-08-06",
                              "--book", os.path.join(d, "does-not-exist.json")],
                             cwd=root, capture_output=True, text=True, timeout=180)
        assert out.returncode == 2, (out.returncode, out.stdout[-300:])
        assert "REFUSED" in out.stderr, out.stderr[-300:]


# =======================================================================================
# REFUSALS — none of them may return a number
# =======================================================================================
def test_no_refusal_path_ever_leaks_a_number():
    """Every way this can fail returns `row: None`, never a partial mark."""
    with tempfile.TemporaryDirectory() as d:
        cases = {
            "missing book": index_mark.contract_row(
                "2026-08-06", meta_path=os.path.join(d, "nope.json"), fetch=_tape(_SIMPLE)),
            "not a trading day": _row(d) if False else index_mark.contract_row(
                "2026-08-08", meta_path=_book(d), fetch=_tape(_SIMPLE)),   # a Saturday
            "on inception": index_mark.contract_row(
                INCEPTION, meta_path=_book(d), fetch=_tape(_SIMPLE)),
            "benchmark unpriced": index_mark.contract_row(
                "2026-08-06", meta_path=_book(d),
                fetch=_tape({k: v for k, v in _SIMPLE.items() if k != "SPY"})),
            "coverage floor": index_mark.contract_row(
                "2026-08-06", meta_path=_book(d),
                fetch=_tape({k: v for k, v in _SIMPLE.items() if k != "AAA"})),
        }
        for name, res in cases.items():
            assert res.get("ok") is False, name + " did not refuse: " + repr(res)
            assert res.get("row") is None, name + " leaked a row: " + repr(res.get("row"))
            assert res.get("reason"), name + " refused without saying why"


def test_it_refuses_before_the_close_rather_than_marking_an_intraday_quote():
    """The recorded day-1 row disagrees with a close-based re-derivation by 0.03pp, which
    is what an intraday mark looks like. This is the guard against repeating it."""
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        # A Thursday, 10:00 ET — a trading day whose session has NOT closed.
        open_session = dt.datetime(2026, 8, 6, 10, 0)
        res = index_mark.contract_row(meta_path=_book(d), fetch=_tape(_SIMPLE),
                                      now=open_session)
        assert res["ok"] is False and res["row"] is None, res
        assert "not closed" in res["reason"] or "intraday" in res["reason"], res["reason"]


def test_naming_todays_date_explicitly_does_not_buy_what_omitting_it_refuses():
    """The close guard is on the DATE, not on how the date was chosen.

    Found by re-reading rather than by a failure: the session check originally sat inside the
    `as_of is None` branch, so `--date <today>` walked straight past it. A vendor returning a
    partial bar for a live session would then have priced the row against an intraday quote
    under a closing-price column — the exact failure the recorded day-1 row appears to carry.
    """
    import datetime as dt
    open_session = dt.datetime(2026, 8, 6, 10, 0)          # a Thursday, 10:00 ET
    with tempfile.TemporaryDirectory() as d:
        mp = _book(d)
        implicit = index_mark.contract_row(meta_path=mp, fetch=_tape(_SIMPLE), now=open_session)
        explicit = index_mark.contract_row("2026-08-06", meta_path=mp, fetch=_tape(_SIMPLE),
                                           now=open_session)
        assert implicit["ok"] is False, implicit
        assert explicit["ok"] is False, "naming today explicitly bypassed the close guard"
        assert explicit["row"] is None, explicit
        # A DIFFERENT, already-closed day is still allowed — the guard must not freeze backfill.
        past = index_mark.contract_row("2026-08-05", meta_path=mp, now=open_session,
                                       fetch=_tape({
                                           "AAA": {INCEPTION: 100.0, "2026-08-05": 110.0},
                                           "BBB": {INCEPTION: 100.0, "2026-08-05": 110.0},
                                           "SPY": {INCEPTION: 100.0, "2026-08-05": 100.0}}))
        assert past["ok"] is True, past.get("reason")


def test_the_close_refusal_can_be_lifted_only_deliberately():
    """`refuse_before_close=False` exists for backfill; it must be opt-in, and the default
    must be the safe one."""
    import datetime as dt
    import inspect
    sig = inspect.signature(index_mark.contract_row)
    assert sig.parameters["refuse_before_close"].default is True, "the default is unsafe"
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row(meta_path=_book(d), fetch=_tape(_SIMPLE),
                                      now=dt.datetime(2026, 8, 6, 10, 0),
                                      refuse_before_close=False)
        # It gets past the session gate and then fails honestly on the price lookup or
        # succeeds — either way it must not silently invent.
        assert res.get("ok") in (True, False)
        if not res.get("ok"):
            assert res.get("row") is None


# =======================================================================================
# ARITHMETIC AND CONVENTION
# =======================================================================================
def test_the_book_mark_is_the_weighted_return_of_the_recorded_positions():
    with tempfile.TemporaryDirectory() as d:
        res = _row(d)
        assert res["ok"], res.get("reason")
        # AAA +10% at 0.5, BBB -2% at 0.5 -> +4.0000%
        assert abs(res["row"]["valquo_pct"] - 4.0) < 1e-9, res["row"]
        assert abs(res["row"]["spy_pct"] - 1.0) < 1e-9, res["row"]
        assert abs(res["row"]["excess_pp"] - 3.0) < 1e-9, res["row"]
        assert res["row"]["n_priced"] == 2, res["row"]


def test_the_marks_are_cumulative_since_inception_and_not_daily_returns():
    """The recorded series holds cumulative levels; `index_track._daily_returns` un-chains
    them. A daily return in these columns re-bases the whole track and looks fine."""
    tape = {
        "AAA": {INCEPTION: 100.0, "2026-08-05": 110.0, "2026-08-06": 121.0},
        "BBB": {INCEPTION: 100.0, "2026-08-05": 110.0, "2026-08-06": 121.0},
        "SPY": {INCEPTION: 100.0, "2026-08-05": 100.0, "2026-08-06": 100.0},
    }
    with tempfile.TemporaryDirectory() as d:
        mp = _book(d)
        day1 = index_mark.contract_row("2026-08-05", meta_path=mp, fetch=_tape(tape))
        day2 = index_mark.contract_row("2026-08-06", meta_path=mp, fetch=_tape(tape))
        assert abs(day1["row"]["valquo_pct"] - 10.0) < 1e-9, day1["row"]
        # +21% since INCEPTION, not the +10% day-over-day move.
        assert abs(day2["row"]["valquo_pct"] - 21.0) < 1e-9, day2["row"]


def test_an_unpriced_name_is_dropped_rather_than_held_flat():
    """Renormalise over what priced. Holding an unpriced name at zero drags the mark toward
    zero in exactly the weeks a data outage is most likely."""
    tape = {
        "AAA": {INCEPTION: 100.0, "2026-08-06": 110.0},   # +10%
        "BBB": {INCEPTION: 100.0, "2026-08-06": 110.0},   # +10%
        "CCC": {},                                        # unpriced
        "SPY": {INCEPTION: 100.0, "2026-08-06": 100.0},
    }
    pos = [{"ticker": "AAA", "weight": 0.49}, {"ticker": "BBB", "weight": 0.49},
           {"ticker": "CCC", "weight": 0.02}]
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row("2026-08-06", meta_path=_book(d, positions=pos),
                                      fetch=_tape(tape))
        assert res["ok"], res.get("reason")
        # Renormalised: +10%. Held-flat would give 0.98*10% = +9.8%.
        assert abs(res["row"]["valquo_pct"] - 10.0) < 1e-9, res["row"]
        assert res["row"]["n_priced"] == 2, res["row"]
        assert res["unpriced"] == ["CCC"], res["unpriced"]


def test_the_coverage_floor_is_measured_on_weight_not_on_name_count():
    """Losing one 2.3% name is not the same event as losing one 0.4% name."""
    tape = {"AAA": {INCEPTION: 100.0, "2026-08-06": 110.0},
            "SPY": {INCEPTION: 100.0, "2026-08-06": 100.0}}
    # One unpriced name out of five names = 80% by count, but only 4% by weight.
    pos = [{"ticker": "AAA", "weight": 0.96}] + [
        {"ticker": "Z" + str(i), "weight": 0.01} for i in range(4)]
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row("2026-08-06", meta_path=_book(d, positions=pos),
                                      fetch=_tape(tape))
        assert res["ok"], "a 96%-weight book was refused on a name COUNT: " + str(res.get("reason"))


def test_day_n_agrees_with_the_projects_own_trading_day_primitive():
    import datetime as dt
    with tempfile.TemporaryDirectory() as d:
        res = _row(d)
        expected = market_session.trading_days_between(
            dt.date(2026, 7, 30), dt.date(2026, 8, 6), inclusive_start=False)
        assert res["row"]["day_n"] == expected, (res["row"]["day_n"], expected)
        # The real recorded row for this date carries day_n 5.
        assert res["row"]["day_n"] == 5, res["row"]["day_n"]


def test_it_reproduces_the_recorded_2026_08_06_benchmark_mark():
    """The real closes, and the real recorded answer.

    SPY closed 741.6900024414062 on the inception date and 768.5599975585938 on 2026-08-06
    (Stooq, via `screener/prices.py`). The recorded row says spy_pct 3.6228, and this
    arithmetic returns 3.6228.

    THAT CONFIRMS THE CONVENTION AND NOT THE WHOLE ROW. A wrong base date, or a daily-return
    convention in a cumulative column, would miss by percent rather than by nothing — so the
    exact hit pins closing-price, cumulative-since-inception, this vendor. The BOOK leg of
    the same row does NOT reproduce exactly (+0.0201pp, all 86 names priced both sides), so
    this suite deliberately does not assert one, and the module docstring says why."""
    tape = {"AAA": {INCEPTION: 100.0, "2026-08-06": 100.0},
            "BBB": {INCEPTION: 100.0, "2026-08-06": 100.0},
            "SPY": {INCEPTION: 741.6900024414062, "2026-08-06": 768.5599975585938}}
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row("2026-08-06", meta_path=_book(d), fetch=_tape(tape))
        assert res["ok"], res.get("reason")
        assert res["row"]["spy_pct"] == 3.6228, res["row"]["spy_pct"]


# =======================================================================================
# THE WRITE HELPER
# =======================================================================================
def test_appending_the_same_date_twice_rewrites_it_rather_than_duplicating():
    """`index_track.load()` already keeps the LAST row per date; the writer must not rely on
    that to hide a duplicate it created."""
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        row = _row(d)["row"]
        index_mark.append_row(row, hist)
        second = dict(row, valquo_pct=9.9999)
        out = index_mark.append_row(second, hist)
        assert out["replaced"] is True, out
        with open(hist, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1, rows
        assert float(rows[0]["valquo_pct"]) == 9.9999, rows


def test_appending_preserves_rows_it_did_not_write_and_keeps_them_ordered():
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        with open(hist, "w", encoding="utf-8", newline="") as f:
            f.write("date,day_n,valquo_pct,spy_pct,excess_pp,n_priced\n")
            f.write("2026-08-11,8,1.0,1.0,0.0,86\n")
        index_mark.append_row(_row(d)["row"], hist)          # an EARLIER date
        with open(hist, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert [r["date"] for r in rows] == ["2026-08-06", "2026-08-11"], rows


def test_the_module_never_writes_unless_asked():
    """`contract_row` computes and returns. The write is a separate call, on purpose."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "screener", "index_mark.py"), encoding="utf-8").read()
    i, j = src.find("def contract_row"), src.find("def append_row")
    assert 0 < i < j, "the functions moved"
    body = src[i:j]
    assert "open(" not in body.replace("open(meta_path", ""), "contract_row opens a file to write"
    assert "append_row" not in body, "contract_row writes as a side effect"


# =======================================================================================
# NO NEW VENDOR — half the original blocker
# =======================================================================================
def test_the_price_source_is_the_services_own_module_and_not_a_new_vendor():
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "screener", "index_mark.py"), encoding="utf-8").read()
    assert "from . import prices" in src, "the mechanism does not use screener/prices.py"
    for vendor in ("api_key", "apikey", "API_KEY", "fmpcloud", "polygon", "tradier",
                   "thetadata", "sharadar", "intrinio"):
        assert vendor not in src, "a new vendor appeared in the price mechanism: " + vendor


def test_the_mechanism_is_documented_where_the_contract_points():
    """A fresh session must find this by READING, which was the whole failure."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    contract = open(os.path.join(root, "PAPER_TRACK_CONTRACT.md"), encoding="utf-8").read()
    assert "index_mark" in contract, "the contract's recorder section does not name the module"
    assert "scripts.track_row" in contract or "scripts/track_row" in contract, \
        "the contract's recorder section does not name the command"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print("  PASS  " + t.__name__); passed += 1
        except AssertionError as e:
            print("  FAIL  " + t.__name__ + ": " + str(e))
        except Exception as e:
            print("  ERROR " + t.__name__ + ": " + type(e).__name__ + ": " + str(e))
    print("\n" + str(passed) + "/" + str(len(tests)) + " PT-WRITER index-mark tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
