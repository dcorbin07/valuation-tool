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
import ast
import re
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
    # THE WHOLE HANDLER, not a fixed character count. It used to be `src[i:i + 2000]`, which
    # silently became a window over the DOCSTRING ALONE the moment the handler's prose grew
    # past 2 kB -- and a delegation check that cannot see the code passes vacuously while
    # reporting that the endpoint delegates. Bounded by the next route instead, so the window
    # tracks the function rather than a guess about its length.
    j = src.find("@app.route", i)
    assert j > i, "could not find the end of the handler"
    body = src[i:j]
    assert "index_mark.contract_row" in body, "the endpoint does not delegate to the module"
    # It must not do its own arithmetic: no price maths anywhere in the handler.
    for forbidden in ("get_history_df", "/ base", "valquo_pct =", "* 100.0"):
        assert forbidden not in body, "the endpoint re-implements the mark: " + forbidden
    # ...nor its own file IO. The append-only and idempotency rules live in
    # `index_mark.append_row`, and a handler that opened the CSV itself would be a second
    # writer with its own idea of the contract.
    for forbidden in ("open(", "csv.", "os.replace"):
        assert forbidden not in body, "the endpoint writes the series itself: " + forbidden
    assert "append_only=True" in body, "the endpoint appends without the contract's rules"


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
        # POST, not GET: writing the bound series is POST-only (see the handler). 201 is
        # "a row was written" -- the status the unattended writer branches on.
        r = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert r.status_code == 201, r.status_code
        body = r.get_json()
        assert body.get("ok") is True, body
        row = body["row"]
        assert body.get("append", {}).get("ok") is True, body.get("append")
        assert body["append"].get("wrote") is True, body["append"]

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


def test_it_never_marks_an_unclosed_session_and_targets_the_last_closed_one():
    """The recorded day-1 row disagrees with a close-based re-derivation by 0.03pp, which is
    what an intraday mark looks like. This is the guard against repeating it.

    IT USED TO ASSERT A REFUSAL, AND THAT WAS THE DEFECT ONE LEVEL UP. Refusing at 10:00 is
    right about the DAY and wrong about the JOB: the writer's target was "today", so a run
    that slipped past midnight ET could only ever refuse and the bound track lost a row
    (measured on the service 2026-08-27, HTTP 422 at 00:58 ET). The target is now the last
    CLOSED session, so the property this test protects is stated directly — the door never
    emits a row dated a session that has not closed — rather than via a refusal that also
    threw away legitimate work.
    """
    import datetime as dt
    from valuation.screener import market_session as _ms

    open_session = dt.datetime(2026, 8, 6, 10, 0)          # a Thursday, 10:00 ET
    self_date = open_session.date().isoformat()
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row(meta_path=_book(d), fetch=_tape(_SIMPLE),
                                      now=open_session)
        # Whatever else happens, it may NEVER produce a row dated the open session.
        if res.get("ok"):
            assert res["row"]["date"] != self_date, res["row"]
            assert res["row"]["date"] == _ms.last_closed_session(open_session).isoformat()
        else:
            assert res["row"] is None, res
    # And the structural half: the default target cannot BE an unclosed day.
    assert _ms.last_closed_session(open_session) < open_session.date()


def test_a_delayed_run_past_midnight_marks_the_session_it_was_scheduled_for():
    """THE DEFECT, reproduced. The cron is scheduled for the evening ET; GitHub delayed it to
    00:58 ET the next calendar day, at which point it asked to mark a day that could not have
    closed and was refused forever."""
    import datetime as dt
    from valuation.screener import market_session as _ms

    scheduled = dt.datetime(2026, 8, 6, 18, 12)     # Thursday evening, after the close
    delayed = dt.datetime(2026, 8, 7, 0, 58)        # Friday 00:58 ET — the real run's time

    # The old target was `session_state(...)["date"]`, i.e. the calendar day.
    assert _ms.session_state(delayed)["date"] == "2026-08-07"
    assert _ms.session_state(delayed)["ok"] is False, "the guard was right; the target was not"

    # The new target is the session that actually closed — the SAME one the on-time run means.
    assert _ms.last_closed_session(delayed) == dt.date(2026, 8, 6)
    assert _ms.last_closed_session(scheduled) == dt.date(2026, 8, 6)

    # ...AND `contract_row` ITSELF EMITS IT. Asserted on the door rather than only on the
    # helper: a tripwire run caught that reverting the door's default to `session_state`'s
    # date left every assertion above green, because at 18:12 the two agree. The delayed run
    # is the case where they differ, so it is the case the door has to be checked on.
    with tempfile.TemporaryDirectory() as d:
        res = index_mark.contract_row(meta_path=_book(d), fetch=_tape(_SIMPLE), now=delayed)
        assert res["ok"] is True, res
        assert res["row"]["date"] == "2026-08-06", res["row"]
        assert res["row"]["date"] != delayed.date().isoformat(), res["row"]


def test_the_walk_back_skips_weekends_and_holidays_rather_than_naming_one():
    """A run just after midnight on a Monday must reach FRIDAY, not Sunday. Caught by a
    tripwire: without the trading-day test in the walk, `last_closed_session` happily returns
    a weekend, and every other case in this suite still passed."""
    import datetime as dt
    from valuation.screener import market_session as _ms

    monday_early = dt.datetime(2026, 8, 31, 0, 30)         # Monday 00:30 ET
    got = _ms.last_closed_session(monday_early)
    assert got == dt.date(2026, 8, 28), got                # the Friday
    assert _ms.is_trading_day(got), got

    # A Saturday run reaches the same Friday.
    assert _ms.last_closed_session(dt.datetime(2026, 8, 29, 2, 0)) == dt.date(2026, 8, 28)

    # And whatever it returns, from any hour of any day across a fortnight, is a trading day
    # that is not in the future — the two properties the door depends on.
    base = dt.datetime(2026, 8, 20, 0, 0)
    for h in range(0, 24 * 14, 7):
        n = base + dt.timedelta(hours=h)
        d = _ms.last_closed_session(n)
        assert d is not None and _ms.is_trading_day(d), (n, d)
        assert d <= n.date(), (n, d)


def test_two_runs_on_the_same_day_target_one_session_so_the_write_stays_idempotent():
    """Required by the fix: an on-time run and a delayed retry must not produce two rows.

    They cannot, because they resolve to the same session date and the write door is
    idempotent per date — but this asserts it end to end rather than by reading the code.
    """
    import datetime as dt

    scheduled = dt.datetime(2026, 8, 6, 18, 12)
    delayed = dt.datetime(2026, 8, 7, 0, 58)
    with tempfile.TemporaryDirectory() as d:
        meta, hist = _book(d), os.path.join(d, "valquo_track_history.csv")
        a = index_mark.contract_row(meta_path=meta, fetch=_tape(_SIMPLE), now=scheduled)
        b = index_mark.contract_row(meta_path=meta, fetch=_tape(_SIMPLE), now=delayed)
        if not (a.get("ok") and b.get("ok")):
            return                                   # the tape cannot price it; nothing to pin
        assert a["row"]["date"] == b["row"]["date"], (a["row"], b["row"])

        first = index_mark.append_row(a["row"], hist, append_only=True)
        second = index_mark.append_row(b["row"], hist, append_only=True)
        assert first.get("wrote") is True, first
        assert second.get("wrote") is False and second.get("already_present"), second
        with open(hist, encoding="utf-8") as f:
            body = [l for l in f.read().splitlines() if l.strip()]
        assert len(body) == 2, body            # header + exactly one row


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
    """`contract_row` computes and returns. The write is a separate call, on purpose.

    BOUNDED BY THE NEXT TOP-LEVEL `def`, NOT BY `def append_row`. It used to end the slice at
    `append_row`, which was the same thing right up until `seed` and its three helpers were
    added BETWEEN the two — at which point the window covered four functions that write files
    by design and the guard failed against a correct tree. A window anchored on a distant
    landmark measures whatever drifts into it; this is the `src[i:i+2000]` defect on the write
    door in a different shape, and the fix is the same one: bound it by the thing that ends it.
    """
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "screener", "index_mark.py"), encoding="utf-8").read()
    i = src.find("def contract_row")
    assert i > 0, "contract_row moved"
    j = re.search(r"\n(?=def |@)", src[i:])
    assert j, "contract_row is the last definition in the file, which it is not"
    body = src[i:i + j.start()]
    assert "def append_row" not in body and "def seed" not in body, \
        "the slice ran past the end of contract_row"
    assert "open(" not in body.replace("open(meta_path", ""), "contract_row opens a file to write"
    assert "append_row" not in body, "contract_row writes as a side effect"
    assert "_write_atomic" not in body, "contract_row writes as a side effect"


def test_the_never_writes_guard_is_not_vacuous():
    """The slice above must actually contain `contract_row`'s body.

    A regex that matched too early would leave a one-line window in which no `open(` can
    appear, and the guard would pass by seeing nothing — which is how a check that measures
    nothing survives for months.
    """
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "screener", "index_mark.py"), encoding="utf-8").read()
    i = src.find("def contract_row")
    j = re.search(r"\n(?=def |@)", src[i:])
    body = src[i:i + j.start()]
    assert len(body.splitlines()) > 40, "the window is too small to be contract_row"
    # things that ARE in contract_row, so the window is demonstrably over the right code
    for token in ("refuse_before_close", "MIN_COVERAGE", "day_n", "_session"):
        assert token in body, "%r missing — the window is not over contract_row" % token


# =======================================================================================
# MA4 — THE WHOLE FILE IS REWRITTEN ON EVERY APPEND, so both hazards are about the rows
# ALREADY THERE, on the file `track-backup.yml` calls "the one thing that can't be
# re-derived". Each test below is checked for vacuity by running the SUPERSEDED write
# against the same fixture and asserting it does the damage.
# =======================================================================================
_SEEDED = ("date,day_n,valquo_pct,spy_pct,excess_pp,n_priced\n"
           "2026-07-31,0,0.0,0.6903,-0.6903,86\n"
           "2026-08-11,8,1.0,1.0,0.0,86\n"
           "2026-08-12,9,1.5,1.2,0.3,86\n")


def _seed(d, text=_SEEDED, name="h.csv"):
    p = os.path.join(d, name)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return p


def _superseded_append(row, history_path):
    """The write MA4 replaced, verbatim, so the pins above it can be shown non-vacuous.

    Kept as a fixture rather than described in prose: a regression test that cannot be
    demonstrated to fail against the defect it names is worth nothing.
    """
    try:
        with open(history_path, encoding="utf-8", newline="") as f:
            existing = [r for r in csv.DictReader(f)]
    except FileNotFoundError:
        existing = []
    kept = [r for r in existing if (r.get("date") or "").strip() != row["date"]]
    kept.append({k: row.get(k) for k in index_mark.ROW_COLUMNS})
    kept.sort(key=lambda r: (r.get("date") or ""))
    with open(history_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(index_mark.ROW_COLUMNS))
        w.writeheader()
        for r in kept:
            w.writerow({k: r.get(k) for k in index_mark.ROW_COLUMNS})


#: Captured BEFORE any patching. `index_mark` imports the same `csv` module object this file
#: does, so patching `index_mark.csv.DictWriter` also rebinds `csv.DictWriter` here — and a
#: blow-up writer that looks the real class up by name at construction time finds ITSELF and
#: recurses. Caught by running it; the first cut did exactly that.
_REAL_DICTWRITER = csv.DictWriter


class _BlowUpWriter:
    """A `csv.DictWriter` that dies partway through, i.e. an interrupted write."""

    def __init__(self, f, fieldnames=None, **kw):
        self._w = _REAL_DICTWRITER(f, fieldnames=fieldnames, **kw)
        self._n = 0

    def writeheader(self):
        self._w.writeheader()

    def writerow(self, r):
        self._n += 1
        if self._n > 1:
            raise IOError("disk full")
        self._w.writerow(r)


def test_ma4_a_column_the_file_gained_survives_an_append():
    """A projection onto ROW_COLUMNS deletes an unknown column from EVERY row, at once."""
    with tempfile.TemporaryDirectory() as d:
        hist = _seed(d, _SEEDED.replace("n_priced\n", "n_priced,vintage\n")
                     .replace(",86\n", ",86,3\n"))
        out = index_mark.append_row(_row(d)["row"], hist)
        assert out["ok"], out
        with open(hist, encoding="utf-8", newline="") as f:
            rd = csv.DictReader(f)
            rows, header = list(rd), rd.fieldnames
        assert "vintage" in header, header
        assert [r["vintage"] for r in rows if r["date"] == "2026-08-11"] == ["3"], rows
        assert list(index_mark.ROW_COLUMNS) == header[:len(index_mark.ROW_COLUMNS)], header


def test_ma4_the_column_loss_pin_is_not_vacuous():
    """The same fixture through the superseded write: the column goes, on all three rows."""
    with tempfile.TemporaryDirectory() as d:
        hist = _seed(d, _SEEDED.replace("n_priced\n", "n_priced,vintage\n")
                     .replace(",86\n", ",86,3\n"))
        _superseded_append(_row(d)["row"], hist)
        with open(hist, encoding="utf-8", newline="") as f:
            header = csv.DictReader(f).fieldnames
        assert "vintage" not in header, "the superseded write kept the column; pin is vacuous"


def test_ma4_an_interrupted_write_leaves_the_previous_file_intact():
    """Truncate-then-write loses the series; write-then-rename cannot."""
    with tempfile.TemporaryDirectory() as d:
        hist = _seed(d)
        before = open(hist, "rb").read()
        real = index_mark.csv.DictWriter
        index_mark.csv.DictWriter = _BlowUpWriter
        try:
            out = index_mark.append_row(_row(d)["row"], hist)
        finally:
            index_mark.csv.DictWriter = real
        assert out["ok"] is False and out["wrote"] is False, out
        assert "disk full" in out["reason"], out
        assert open(hist, "rb").read() == before, "the bound series was damaged by a failed write"
        assert not os.path.exists(hist + ".tmp"), "a temp file survived the failure"


def test_ma4_the_atomicity_pin_is_not_vacuous():
    """The superseded write, interrupted the same way, destroys the file. That is the point."""
    with tempfile.TemporaryDirectory() as d:
        hist = _seed(d)
        before = open(hist, "rb").read()
        real = csv.DictWriter
        try:
            globals()["csv"].DictWriter = _BlowUpWriter
            try:
                _superseded_append(_row(d)["row"], hist)
            except IOError:
                pass
        finally:
            globals()["csv"].DictWriter = real
        after = open(hist, "rb").read()
        assert after != before, "the superseded write survived interruption; pin is vacuous"
        assert len(after) < len(before), (len(after), len(before))


def test_ma4_a_successful_write_leaves_no_temp_file():
    with tempfile.TemporaryDirectory() as d:
        row = _row(d)["row"]                       # this writes the book meta into `d`
        sub = os.path.join(d, "hist")
        os.makedirs(sub)
        hist = _seed(sub)
        assert index_mark.append_row(row, hist)["ok"]
        assert sorted(os.listdir(sub)) == ["h.csv"], os.listdir(sub)


def test_ma4_a_ragged_file_is_refused_rather_than_normalised():
    """DictReader pads and pools, so a rewrite would invent or discard cells in silence."""
    with tempfile.TemporaryDirectory() as d:
        for bad in (_SEEDED + "2026-08-13,10,2.0,1.5,0.5,86,SURPLUS\n",
                    _SEEDED + "2026-08-13,10,2.0\n"):
            hist = _seed(d, bad)
            before = open(hist, "rb").read()
            out = index_mark.append_row(_row(d)["row"], hist)
            assert out["ok"] is False and out["wrote"] is False, out
            assert "does not match its header" in out["reason"], out
            assert open(hist, "rb").read() == before, "a refused write still touched the file"


def test_ma4_a_key_in_neither_the_file_nor_the_header_is_reported_not_silently_dropped():
    """Widening the bound schema takes an edit to ROW_COLUMNS, never a caller's typo — but
    the caller is told, because a silent drop is how the reader and writer disagree."""
    with tempfile.TemporaryDirectory() as d:
        hist = _seed(d)
        out = index_mark.append_row(dict(_row(d)["row"], vaquo_pct=1.0), hist)
        assert out["ok"], out
        assert out["ignored_fields"] == ["vaquo_pct"], out
        with open(hist, encoding="utf-8", newline="") as f:
            assert "vaquo_pct" not in (csv.DictReader(f).fieldnames or []), "typo widened the file"


def _code_only(src):
    """The source with every docstring blanked, so a guard sees code and not prose about it.

    THE ELEVENTH COPY OF THIS HELPER IN `tests/`. Reported, deliberately not consolidated
    here: eleven suites would have to change in one commit for a helper that is four lines,
    and `S3-I1`'s own subject is that consolidating a WRITER is worth its blast radius while
    consolidating a test helper is not obviously so. Left for whoever wants it.
    """
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body[0].value.value = ""
    return ast.unparse(tree)


def _func_src(src, name):
    """One function's source, resolved by the SYNTAX TREE rather than by a text offset."""
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.unparse(node)
    return ""


def _opens_for_writing(src, varname):
    """True if `src` calls `open(<varname>, "w"...)` anywhere. Structural, not textual.

    A TEXT MATCH CANNOT DO THIS JOB AND THE MUTATION PROVED IT. The first cut asserted the
    literal `open(path, "w"` was absent from `ast.unparse` output -- and `unparse` normalises
    string quoting to single quotes, so the needle could never appear and the guard PASSED
    against a delegate mutated to truncate the target in place. A check that cannot fail is
    not a check; matching the call SHAPE is immune to how the quotes are spelled.
    """
    for node in ast.walk(ast.parse(src)):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open" and node.args):
            continue
        target = node.args[0]
        if not (isinstance(target, ast.Name) and target.id == varname):
            continue
        mode = node.args[1] if len(node.args) > 1 else None
        for kw in node.keywords:
            if kw.arg == "mode":
                mode = kw.value
        if isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
                and ("w" in mode.value or "a" in mode.value):
            return True
    return False


def test_ma4_the_write_goes_through_a_rename_and_never_opens_the_target_for_writing():
    """REPOINTED 2026-08-23 (`S3-I1`), IN THE SAME COMMIT AS THE MOVE — `MA59`'s rule.

    This guard asserted `os.replace(tmp, history_path)` inside `append_row`'s own source, and
    `S3-I1` moved the implementation to `valuation/edge/append_only.py` so the fleet's books
    could share it instead of growing a second copy (the B7 split `append_row`'s docstring
    warns about). **The guard then FAILED against the CORRECT tree**, because it keyed on
    WHERE the rename lives rather than on WHETHER the write is a rename.

    It is repointed rather than relaxed, and it is now STRICTLY STRONGER: it FOLLOWS the
    delegation instead of hard-coding a path, and it holds the property against BOTH modules,
    so neither the caller nor the shared writer can start truncating the bound file in place.
    A delegation to a module that does not exist, or to one that does not rename, fails here.

    THE NEGATIVE HALF READS CODE, NOT PROSE ABOUT CODE. The first repoint grepped the raw
    source for `open(path, "w"` and fired on the delegate's own DOCSTRING, which quotes that
    call while explaining why it is forbidden -- `MA49`'s comment-versus-code family, which
    this record has now hit enough times that `MB1` wrote the fix down: strip comments and
    string literals with `tokenize` and match on what is left. The stripper is itself pinned
    non-vacuous below, because one returning "" would make this guard pass by seeing nothing.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, "valuation", "screener", "index_mark.py"),
               encoding="utf-8").read()
    body = _code_only(_func_src(src, "append_row"))
    assert body, "append_row moved"
    assert not _opens_for_writing(body, "history_path"), \
        "the bound file is opened for writing in place"

    if "os.replace(tmp, history_path)" not in body:
        # Delegated: resolve the module it delegates to and hold the property THERE.
        m = re.search(r"from \.\.(\w+) import (\w+) as (\w+)", body)
        assert m, "append_row neither renames nor delegates to a module that could"
        pkg, mod, alias = m.group(1), m.group(2), m.group(3)
        assert (alias + ".append(") in body, "the import is not the writer append_row uses"
        dele = open(os.path.join(root, "valuation", pkg, mod + ".py"), encoding="utf-8").read()
        code = _code_only(dele)
        assert "def append(" in code and "os" in code, \
            "the comment stripper returned nothing recognisable, so this guard sees nothing"
        assert "os.replace(tmp, path)" in code, "the delegate's write is not a rename"
        assert not _opens_for_writing(code, "path"), \
            "the delegate opens the target for writing"


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


# =======================================================================================
# THE APPEND DOOR — POST /admin/track-row?append=1
#
# The contract's rules are not advisory and they are not enforced by the caller. Every one
# of them is asserted here against the RUNNING endpoint, because the caller is an unattended
# GitHub Action and the failure mode that matters is a writer that silently rewrites a
# five-year evidence record on a retry.
# =======================================================================================

#: The `_SIMPLE` tape plus a second trading day, so a test can append 08-07 AFTER 08-06 and
#: ask what happened to the row already on disk. One date cannot exercise append-only at all.
_SEQ = {
    "AAA": {INCEPTION: 100.0, "2026-08-05": 105.0, "2026-08-06": 110.0, "2026-08-07": 120.0},
    "BBB": {INCEPTION: 50.0, "2026-08-05": 49.5, "2026-08-06": 49.0, "2026-08-07": 48.0},
    "SPY": {INCEPTION: 400.0, "2026-08-05": 402.0, "2026-08-06": 404.0, "2026-08-07": 408.0},
}


def _client(positions=None):
    """A live app, a book on the isolated temp path, and the deterministic tape installed.

    Returns `(client, headers, meta_path, hist_path, restore)`. `restore` must be called.
    """
    from valuation.config import CONFIG
    from valuation.saas.app_saas import create_saas_app
    from valuation.screener import prices

    CONFIG.admin_token = "test-token-index-mark"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True

    meta_path, hist_path = index_track.default_paths()
    os.makedirs(os.path.dirname(os.path.abspath(meta_path)), exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({"inception_date": INCEPTION, "benchmark": "SPY",
                   "positions": positions or [{"ticker": "AAA", "weight": 0.5},
                                              {"ticker": "BBB", "weight": 0.5}]}, f)
    try:
        os.remove(hist_path)
    except OSError:
        pass

    real = prices.get_history_df
    prices.get_history_df = _tape(_SEQ)

    def restore():
        prices.get_history_df = real
        try:
            os.remove(hist_path)
        except OSError:
            pass

    return (app.test_client(), {"X-Admin-Token": CONFIG.admin_token},
            meta_path, hist_path, restore)


def test_a_second_post_for_the_same_date_is_a_no_op_and_never_a_duplicate():
    """Idempotency, at the door the scheduler actually calls.

    Both crons in `track-row.yml` can fire on one day — the backup exists precisely because
    GitHub drops scheduled runs — so a second POST for a date already recorded is the NORMAL
    case, not an error case. It must add no row and change no value.
    """
    c, hdr, _, hist, restore = _client()
    try:
        first = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert first.status_code == 201, first.status_code
        assert first.get_json()["append"]["wrote"] is True

        second = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert second.status_code == 200, second.status_code
        ap = second.get_json()["append"]
        assert ap["wrote"] is False, ap
        assert ap["already_present"] is True, ap

        with open(hist, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1, rows
        assert [r["date"] for r in rows] == ["2026-08-06"], rows
    finally:
        restore()


def test_the_no_op_returns_the_row_on_disk_and_not_the_one_just_computed():
    """The two can differ, and the difference is the whole reason to return the recorded one.

    A vendor revises; the yfinance fallback answers where Stooq did not; a retry an hour
    later computes a different close for a day already written. Handing back the freshly
    computed row would report a number the bound file does not contain — which is the same
    class of failure as writing it would be, minus the evidence.
    """
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        with open(hist, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=index_mark.ROW_COLUMNS)
            w.writeheader()
            w.writerow({"date": "2026-08-06", "day_n": 5, "valquo_pct": 999.0,
                        "spy_pct": 888.0, "excess_pp": 111.0, "n_priced": 2})

        fresh = _row(d)["row"]
        assert abs(fresh["valquo_pct"] - 4.0) < 1e-9, fresh

        out = index_mark.append_row(fresh, hist, append_only=True)
        assert out["ok"] is True and out["wrote"] is False, out
        assert out["already_present"] is True, out
        # the RECORDED number comes back, not the 4.0 just computed
        assert float(out["existing"]["valquo_pct"]) == 999.0, out["existing"]

        with open(hist, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1 and float(rows[0]["valquo_pct"]) == 999.0, rows


def test_the_write_door_refuses_to_backfill_a_prior_row():
    """A gap stays a logged gap. 409, and the file is untouched.

    Filling a gap is a deliberate human act under the contract's section 3 same-week clause
    and lives on the CLI. An unattended writer that can reach backwards can rewrite history
    on a retry, and there is no way to tell that apart from the record afterwards.
    """
    c, hdr, _, hist, restore = _client()
    try:
        assert c.post("/admin/track-row?date=2026-08-07&append=1",
                      headers=hdr).status_code == 201
        before = open(hist, "rb").read()

        r = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert r.status_code == 409, r.status_code
        body = r.get_json()
        assert body["append"]["ok"] is False, body
        assert body["append"].get("would_modify") is True, body["append"]
        assert "append-only" in body["append"]["reason"], body["append"]["reason"]

        assert open(hist, "rb").read() == before, "the refused write touched the file"
    finally:
        restore()


def test_an_append_only_write_leaves_the_previous_bytes_as_an_exact_prefix():
    """The guarantee stated in the same terms the Action checks it in.

    `track-row.yml` compares `head -n N` of the new file against the old with `cmp` and fails
    the job on any difference. A guarantee phrased more weakly than the check — "the values
    are preserved", say — would be untestable against it, so this asserts BYTES.
    """
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        first = index_mark.contract_row("2026-08-06", meta_path=_book(d),
                                        fetch=_tape(_SEQ))["row"]
        index_mark.append_row(first, hist, append_only=True)
        before = open(hist, "rb").read()

        second = index_mark.contract_row("2026-08-07", meta_path=_book(d),
                                         fetch=_tape(_SEQ))["row"]
        out = index_mark.append_row(second, hist, append_only=True)
        assert out["ok"] and out["wrote"], out

        after = open(hist, "rb").read()
        assert after.startswith(before), "the append rewrote earlier bytes"
        assert len(after) > len(before), "nothing was appended"


def test_the_byte_prefix_check_is_not_vacuous():
    """The positive control for the test above: a write that DOES break the prefix.

    Without this, `after.startswith(before)` would pass for any implementation that appends —
    including one that had quietly stopped writing anything at all — and it would pass just as
    happily if the prefix guarantee were unreachable in practice.
    """
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        later = index_mark.contract_row("2026-08-07", meta_path=_book(d),
                                        fetch=_tape(_SEQ))["row"]
        index_mark.append_row(later, hist, append_only=True)
        before = open(hist, "rb").read()

        # DEFAULT mode, an EARLIER date: it sorts ahead of the existing row, so the file is
        # genuinely rewritten and the prefix is genuinely broken.
        earlier = index_mark.contract_row("2026-08-06", meta_path=_book(d),
                                          fetch=_tape(_SEQ))["row"]
        out = index_mark.append_row(earlier, hist)
        assert out["ok"] and out["wrote"], out
        assert not open(hist, "rb").read().startswith(before), \
            "the control did not break the prefix, so the guarantee above proves nothing"


def test_the_write_door_cannot_be_talked_out_of_the_close_refusal():
    """Marking an unclosed session writes an intraday quote under a closing-price column.

    That is what the recorded day-1 row appears to carry (contract section 7.2a), so there is
    deliberately no query string, header or body key that switches the refusal off. Asserted
    behaviourally AND at source, because the behavioural half alone would keep passing if a
    parameter were added and simply defaulted to safe.
    """
    import valuation.screener.market_session as ms

    c, hdr, _, hist, restore = _client()
    real_state = ms.session_state
    ms.session_state = lambda now=None: {"ok": False, "date": "2026-08-07",
                                         "reason": "the session has not closed"}
    try:
        for query in ("append=1",
                      "append=1&refuse_before_close=0",
                      "append=1&allow_open_session=1",
                      "append=1&force=1"):
            r = c.post("/admin/track-row?" + query, headers=hdr)
            assert r.status_code == 422, (query, r.status_code)
            assert r.get_json()["ok"] is False, query
            assert not os.path.exists(hist) or open(hist).read() == "", \
                "an unclosed session was recorded via " + query
    finally:
        ms.session_state = real_state
        restore()

    # THE SOURCE HALF READS THE SYNTAX TREE, NOT THE TEXT. A substring sweep fires on the
    # handler's own COMMENT explaining why the refusal is not a parameter -- which is how the
    # first cut of this test failed against a correct tree. A guard that cannot tell code from
    # prose about code is not measuring the tree; this project has now paid for that four
    # times (MA5's source sweep, MA49(c)'s fixture, MA23's stale-path guard, and here).
    import ast

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tree = ast.parse(open(os.path.join(root, "valuation", "saas", "app_saas.py"),
                          encoding="utf-8").read())
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "admin_track_row"), None)
    assert fn is not None, "the /admin/track-row handler is gone"

    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                assert kw.arg != "refuse_before_close", \
                    "the handler passes refuse_before_close; the refusal became optional"
        # ...and it must not read one from the request either, under any spelling.
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in ("refuse_before_close", "allow_open_session"), \
                "the handler reads a close-refusal override from the request: " + node.value


def test_a_refusal_on_the_write_door_is_a_non_200_the_caller_can_branch_on():
    """The Action must tell wrote / already had it / refused apart from the status alone.

    It writes a pushed failure note on a refusal and commits a row on a success, so a shared
    status code between those two outcomes is not a cosmetic problem.
    """
    c, hdr, _, hist, restore = _client()
    try:
        r = c.post("/admin/track-row?date=2026-08-08&append=1", headers=hdr)  # a Saturday
        assert r.status_code == 422, r.status_code
        body = r.get_json()
        assert body["ok"] is False and body["row"] is None, body
        assert "trading day" in body["reason"], body
        assert not os.path.exists(hist), "a refused day was recorded"
    finally:
        restore()


def test_the_four_outcomes_have_four_distinct_status_codes():
    """Stated as the property the caller depends on, rather than four separate assertions."""
    c, hdr, _, _, restore = _client()
    try:
        seen = {
            "wrote": c.post("/admin/track-row?date=2026-08-06&append=1",
                            headers=hdr).status_code,
            "already": c.post("/admin/track-row?date=2026-08-06&append=1",
                              headers=hdr).status_code,
            "backfill": c.post("/admin/track-row?date=2026-08-05&append=1",
                               headers=hdr).status_code,
            "refused": c.post("/admin/track-row?date=2026-08-08&append=1",
                              headers=hdr).status_code,
        }
        assert seen == {"wrote": 201, "already": 200, "backfill": 409, "refused": 422}, seen
        assert len(set(seen.values())) == 4, seen
    finally:
        restore()


def test_a_get_can_no_longer_write_the_bound_series():
    """The write moved to POST and the old door is CLOSED, not merely undocumented.

    A side-effecting GET on the one dataset here that cannot be re-derived is reachable by a
    retry, a prefetch, a proxy or a pasted link, and none of those is a decision to record a
    day. `GET ?append=1` used to write; it now refuses with a 405 and touches nothing.
    """
    c, hdr, _, hist, restore = _client()
    try:
        r = c.get("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert r.status_code == 405, r.status_code
        assert not os.path.exists(hist), "a GET wrote the bound series"

        # ...and the read half still works, unchanged.
        ok = c.get("/admin/track-row?date=2026-08-06", headers=hdr)
        assert ok.status_code == 200, ok.status_code
        assert ok.get_json()["ok"] is True
        assert not os.path.exists(hist), "a plain GET wrote the bound series"
    finally:
        restore()


def test_the_default_append_mode_is_untouched_so_the_cli_backfill_still_works():
    """The CLI's documented `--date` backfill is a deliberate human act and must survive.

    The new rules are opt-in for exactly this reason: `append_only=True` is the unattended
    writer's mode, and narrowing the shared default would have silently removed the one
    sanctioned way to fill a same-week gap under the contract's section 3.
    """
    with tempfile.TemporaryDirectory() as d:
        hist = os.path.join(d, "h.csv")
        later = index_mark.contract_row("2026-08-07", meta_path=_book(d),
                                        fetch=_tape(_SEQ))["row"]
        index_mark.append_row(later, hist, append_only=True)

        earlier = index_mark.contract_row("2026-08-06", meta_path=_book(d),
                                          fetch=_tape(_SEQ))["row"]
        out = index_mark.append_row(earlier, hist)          # default mode
        assert out["ok"] and out["wrote"], out

        with open(hist, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert [r["date"] for r in rows] == ["2026-08-06", "2026-08-07"], rows

        # and replacing a date in default mode still replaces
        again = index_mark.append_row(earlier, hist)
        assert again["replaced"] is True, again


def test_the_appended_row_reads_back_through_index_track_load_unchanged():
    """The module's REQUIRED pin, re-asserted through the POST door specifically.

    The round trip is pinned for the library and for the GET path already; this is the path
    that will actually write the bound series every weekday, so it is pinned here too rather
    than assumed to inherit.
    """
    c, hdr, meta, hist, restore = _client()
    try:
        r = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert r.status_code == 201, r.status_code
        row = r.get_json()["row"]

        series = index_track.load(meta_path=meta, history_path=hist)["series"]
        assert len(series) == 1, series
        got = series[0]
        assert got["date"] == row["date"], (got, row)
        for a, b in (("valquo", "valquo_pct"), ("spy", "spy_pct"),
                     ("excess", "excess_pp"), ("n_priced", "n_priced")):
            assert abs(got[a] - row[b]) < 1e-12, (a, got, row)
    finally:
        restore()


def test_the_no_op_and_the_write_agree_on_the_type_of_every_field():
    """One payload key must not change type depending on which outcome the caller got.

    Found by inspecting the live endpoint rather than by a failing test: the 201 body carried
    `valquo_pct: 4.0` and the 200 body carried `"4.0"` for the same recorded day, because the
    no-op path returns a row that has been through a CSV and is therefore all strings. A
    consumer that adds to that field works on the day it writes and breaks on the day it
    retries -- which is the rarer path and so the later discovery.
    """
    c, hdr, _, _, restore = _client()
    try:
        wrote = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        noop = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert (wrote.status_code, noop.status_code) == (201, 200)

        a, b = wrote.get_json()["row"], noop.get_json()["row"]
        assert set(a) == set(b), (sorted(a), sorted(b))
        for k in a:
            assert type(a[k]) is type(b[k]), (k, type(a[k]).__name__, type(b[k]).__name__)
            assert a[k] == b[k], (k, a[k], b[k])
    finally:
        restore()


def test_an_unreadable_cell_is_reported_verbatim_rather_than_nulled():
    """Typing the row back must not hide a corrupt record behind a well-typed payload.

    The reason to return the row ON DISK is to report what is actually recorded. Replacing an
    unreadable cell with `None` would be the same failure as normalising a ragged file: the
    caller gets something well-formed and false, and the corruption becomes invisible.
    """
    out = index_mark.typed_row({"date": "2026-08-06", "day_n": "5", "valquo_pct": "4.0",
                                "spy_pct": "n/a", "excess_pp": "3.0", "n_priced": "2.5"})
    assert out["day_n"] == 5 and isinstance(out["day_n"], int), out
    assert out["valquo_pct"] == 4.0 and isinstance(out["valquo_pct"], float), out
    assert out["spy_pct"] == "n/a", out          # unreadable: kept, not nulled
    assert out["n_priced"] == "2.5", out         # a fraction in an integer column is not a 2
    # a column the file has gained is passed through untouched, not guessed at
    assert index_mark.typed_row({"vintage": "4"})["vintage"] == "4"


# =======================================================================================
# THE SEED DOOR — POST /admin/track-seed
#
# The write door was never the blocker. On 2026-08-18 the PT-WRITER Action reached it,
# authenticated, and was refused: "the book file /app/data/valquo_track.json is missing or
# unreadable". `data/` is gitignored, so the book has never shipped with a deploy. These
# tests are about the door that fixes that — and about the fact that it is, by some distance,
# the most destructive admin route in the app: it installs the file the backup workflow calls
# "the one thing that can't be re-derived".
# =======================================================================================

#: A CONFORMING book: 50 names at 2% each, so `valquo_index.conformance` passes both legs
#: (>= 50 positions, and the 8% cap genuinely binds). `_client`'s two-name book is deliberately
#: NOT reused — it fails conformance, which is the whole point of the refusal test below.
_SEED_TICKERS = ["T%02d" % i for i in range(50)]
_SEED_BOOK = {"inception_date": INCEPTION, "benchmark": "SPY", "scan_date": "2026-07-24",
              "positions": [{"ticker": t, "weight": 0.02} for t in _SEED_TICKERS]}

#: Prices for every name in that book, so the WRITE door can actually run after a seed. A
#: sequence test whose second half cannot price the book would pass on a coverage refusal and
#: prove nothing about the sequence.
_SEED_SEQ = {t: {INCEPTION: 100.0, "2026-08-05": 105.0, "2026-08-06": 110.0,
                 "2026-08-07": 120.0} for t in _SEED_TICKERS}
_SEED_SEQ["SPY"] = {INCEPTION: 400.0, "2026-08-05": 402.0, "2026-08-06": 404.0,
                    "2026-08-07": 408.0}

_H = "date,day_n,valquo_pct,spy_pct,excess_pp,n_priced\r\n"
_R1 = "2026-07-31,1,0.4126,0.6903,-0.2777,50\r\n"
_R2 = "2026-08-03,2,0.7760,3.6228,-2.8468,50\r\n"
_R3 = "2026-08-04,3,4.2500,4.8800,-0.6200,50\r\n"


def _seed_client():
    """A live app on isolated temp paths holding NEITHER file — the live service's real state.

    Returns `(client, headers, meta_path, hist_path, restore)`.
    """
    from valuation.config import CONFIG
    from valuation.saas.app_saas import create_saas_app
    from valuation.screener import prices

    CONFIG.admin_token = "test-token-index-mark"
    app = create_saas_app(CONFIG)
    app.config["TESTING"] = True

    meta_path, hist_path = index_track.default_paths()
    os.makedirs(os.path.dirname(os.path.abspath(meta_path)), exist_ok=True)
    for f in (meta_path, hist_path):
        try:
            os.remove(f)
        except OSError:
            pass

    real = prices.get_history_df
    prices.get_history_df = _tape(_SEED_SEQ)

    def restore():
        prices.get_history_df = real
        for f in (meta_path, hist_path):
            try:
                os.remove(f)
            except OSError:
                pass

    return (app.test_client(), {"X-Admin-Token": CONFIG.admin_token},
            meta_path, hist_path, restore)


def _post_seed(c, hdr, book=None, history=_H + _R1 + _R2):
    body = {"book": _SEED_BOOK if book is None else book}
    if history is not None:
        body["history"] = history
    return c.post("/admin/track-seed", headers=hdr, json=body)


def test_the_seed_installs_a_book_and_a_history_on_a_service_that_has_neither():
    """The happy path, which is the state the live service is actually in."""
    c, hdr, meta, hist, restore = _seed_client()
    try:
        assert not os.path.exists(meta) and not os.path.exists(hist)
        r = _post_seed(c, hdr)
        assert r.status_code == 201, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["ok"] and j["book_wrote"] and j["history_wrote"], j
        assert j["history_rows_added"] == 2 and j["n_positions"] == 50, j
        assert j["conformance"]["conforms"] is True, j["conformance"]
        assert os.path.exists(meta) and os.path.exists(hist)
    finally:
        restore()


def test_the_seeded_files_read_back_through_index_track_load_unchanged():
    """The pin the whole module is built on: what is written must be what the reader reads.

    `index_track.load()` is the only reader of these two files that anything user-facing goes
    through, so a seed that writes something it cannot read back has installed a record that
    does not exist as far as the product is concerned.
    """
    c, hdr, meta, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr, history=_H + _R1 + _R2 + _R3).status_code == 201
        lo = index_track.load(meta, hist)
        assert [r["date"] for r in lo["series"]] == ["2026-07-31", "2026-08-03", "2026-08-04"]
        assert lo["series"][0]["valquo"] == 0.4126 and lo["series"][0]["spy"] == 0.6903
        assert lo["series"][-1]["excess"] == -0.62
        assert lo["meta"]["inception_date"] == INCEPTION
        assert lo["meta"]["benchmark"] == "SPY"
        assert len(lo["meta"]["positions"]) == 50
    finally:
        restore()


def test_a_book_that_is_not_the_index_is_refused_and_nothing_at_all_is_written():
    """PT-SPLIT's conformance check, as a GATE rather than a description.

    The Tradier sandbox engine ran a 10-name book for four days and it was reported under the
    words "Valquo Index vs SPY". `conformance` exists so that book can be NAMED; this door is
    where naming it becomes refusing it. The second half of the assertion is the load-bearing
    one: a refusal must not leave a half-installed service behind.
    """
    c, hdr, meta, hist, restore = _seed_client()
    try:
        small = dict(_SEED_BOOK,
                     positions=[{"ticker": "T%d" % i, "weight": 0.10} for i in range(10)])
        r = _post_seed(c, hdr, book=small)
        assert r.status_code == 422, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["ok"] is False and j["stage"] == "conformance", j
        assert j["conformance"]["conforms"] is False
        assert "below the contract floor of 50" in j["reason"], j["reason"]
        assert "does not bind" in j["reason"], j["reason"]
        assert not os.path.exists(meta), "a refused seed still wrote the book"
        assert not os.path.exists(hist), "a refused seed still wrote the history"
    finally:
        restore()


def test_the_upload_may_extend_the_recorded_series():
    """The rule is EXTEND, so the extending case has to work, not merely the refusals."""
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        r = _post_seed(c, hdr, history=_H + _R1 + _R2 + _R3)
        assert r.status_code == 201, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["history_rows_before"] == 2 and j["history_rows_after"] == 3
        assert j["history_rows_added"] == 1 and j["prefix_verified"] is True, j
    finally:
        restore()


def test_the_upload_may_not_rewrite_a_recorded_day():
    """The rule that makes this door safe to point at a five-year evidence record.

    A stale local copy re-uploaded after the service has moved on is the ordinary way this
    fires — not malice. The refusal names the row, the column and both values, because a
    caller that is told only "refused" will reach for a flag to turn the refusal off.
    """
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        before = open(hist, "rb").read()

        r = _post_seed(c, hdr, history=_H + _R1.replace("0.4126", "9.9999") + _R2)
        assert r.status_code == 409, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["would_rewrite"] is True, j
        assert "rewrites a recorded day" in j["reason"], j["reason"]
        assert "0.4126" in j["reason"] and "9.9999" in j["reason"], j["reason"]
        assert open(hist, "rb").read() == before, "a refused upload still changed the file"
    finally:
        restore()


def test_the_upload_may_not_truncate_the_recorded_series():
    """Dropping rows is the other way to lose a recorded day, and it is the quieter one."""
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        before = open(hist, "rb").read()
        r = _post_seed(c, hdr, history=_H + _R1)
        assert r.status_code == 409, (r.status_code, r.get_json())
        assert "never truncate" in r.get_json()["reason"], r.get_json()["reason"]
        assert open(hist, "rb").read() == before
    finally:
        restore()


def test_an_extending_seed_leaves_the_previous_bytes_as_an_exact_prefix():
    """The guarantee is byte-level because the append door's is, and they share a serialiser.

    Stating it in weaker terms (same rows, same values) would be untestable against
    `track-row.yml`'s own `cmp` on `head -n N`, and would permit a rewrite that changed only
    formatting — which still rewrites every line of the file the contract binds.
    """
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        before = open(hist, "rb").read()
        assert _post_seed(c, hdr, history=_H + _R1 + _R2 + _R3).status_code == 201
        after = open(hist, "rb").read()
        assert after.startswith(before), (before, after)
        assert len(after) > len(before)
    finally:
        restore()


def test_the_seed_byte_prefix_check_is_not_vacuous():
    """A positive control: the assertion above must be capable of failing.

    NAMED `seed_` DELIBERATELY. The write door has a control of the same shape, and giving this
    one the same name SHADOWED it: Python rebinds silently, `globals()` keeps one entry, and the
    older control stopped running the moment these tests landed. Found by comparing `def test_`
    (62) against what the runner reported (61) - a test deleted by a name collision is invisible
    in a green run, which is why the census below is now itself a test.

    Two rows written by the DEFAULT append mode in the wrong order produce a file whose
    earlier bytes are not a prefix of the later ones — so `startswith` is measuring something.
    """
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr, history=_H + _R2).status_code == 201
        before = open(hist, "rb").read()
        index_mark.append_row({"date": "2026-07-31", "day_n": 1, "valquo_pct": 0.4126,
                               "spy_pct": 0.6903, "excess_pp": -0.2777, "n_priced": 50}, hist)
        after = open(hist, "rb").read()
        assert not after.startswith(before), "the control cannot fail, so the check proves nothing"
    finally:
        restore()


def test_re_seeding_exactly_what_the_service_already_holds_changes_nothing_and_says_so():
    """Idempotency, so a re-run of `scripts/seed_track.py` is safe rather than merely harmless.

    200 rather than 201 is a FACT about the two files, not an assumption: both writes are
    skipped when the bytes already match, so a caller that retries touches neither file.
    """
    c, hdr, meta, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        m0, h0 = os.path.getmtime(meta), open(hist, "rb").read()

        r = _post_seed(c, hdr)
        assert r.status_code == 200, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["ok"] and j["changed"] is False, j
        assert j["book_wrote"] is False and j["history_wrote"] is False, j
        assert open(hist, "rb").read() == h0
        assert os.path.getmtime(meta) == m0, "the book was rewritten on a no-op"
    finally:
        restore()


def test_a_book_may_not_be_seeded_without_a_history_to_stand_on():
    """The trap that would have lost the recorded days INVISIBLY.

    Seed a book onto an empty series and the next append starts a fresh series at today's
    date. `day_n` is computed from the inception date, so the new first row carries a
    plausible day number and nothing raises — the four recorded days would simply not be in
    the copy this seed is about to declare the record.
    """
    c, hdr, meta, hist, restore = _seed_client()
    try:
        r = _post_seed(c, hdr, history=None)
        assert r.status_code == 422, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["stage"] == "history", j
        assert "start a NEW series at today" in j["reason"], j["reason"]
        assert not os.path.exists(meta), "a refused seed still installed the book"

        # ...and it is allowed once the service HAS rows, because then there is nothing to lose.
        assert _post_seed(c, hdr).status_code == 201
        r = _post_seed(c, hdr, book=dict(_SEED_BOOK, scan_date="2026-08-14"), history=None)
        assert r.status_code == 201, (r.status_code, r.get_json())
        assert r.get_json()["history_wrote"] is False
    finally:
        restore()


def test_the_seeded_header_must_be_the_one_the_append_door_would_compute():
    """Otherwise the seed installs a series the unattended writer can never append to.

    `append_row(append_only=True)` REFUSES a header it would have to widen, because widening
    rewrites every line and so cannot preserve the byte prefix. A seed that accepted a
    differently-shaped header would therefore succeed, look healthy, and produce a service
    where every subsequent write is refused — with the reason pointing at the writer.
    """
    c, hdr, _, _, restore = _seed_client()
    try:
        wrong = ("day_n,date,valquo_pct,spy_pct,excess_pp,n_priced\r\n"
                 "1,2026-07-31,0.4126,0.6903,-0.2777,50\r\n")
        r = _post_seed(c, hdr, history=wrong)
        assert r.status_code == 422, (r.status_code, r.get_json())
        assert "append_row would compute" in r.get_json()["reason"], r.get_json()["reason"]
    finally:
        restore()


def test_a_ragged_or_duplicated_upload_is_refused_rather_than_normalised():
    """`csv.DictReader` pads short rows and files surplus cells under one key, so a rewrite of
    a ragged file discards or invents cells and looks perfectly well-formed afterwards. And a
    repeated date lets `index_track.load`'s keep-the-last rule silently pick which of two
    readings of one day is the record."""
    c, hdr, _, _, restore = _seed_client()
    try:
        r = _post_seed(c, hdr, history=_H + "2026-07-31,1,0.4126,0.6903\r\n")
        assert r.status_code == 422, (r.status_code, r.get_json())
        assert "ragged" in r.get_json()["reason"], r.get_json()["reason"]

        r = _post_seed(c, hdr, history=_H + _R1 + _R1)
        assert r.status_code == 422, (r.status_code, r.get_json())
        assert "repeats a date" in r.get_json()["reason"], r.get_json()["reason"]
    finally:
        restore()


def test_after_a_seed_the_write_door_works_end_to_end():
    """THE DELIVERABLE. The seed is worth nothing unless the sequence completes.

    This is the exact pair of calls the live service will receive: `scripts/seed_track.py`
    once, then `track-row.yml` every weekday. Asserting them separately would leave the join
    untested, and the join is where the header rule and the append-only rule meet.
    """
    c, hdr, meta, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr, history=_H + _R1 + _R2).status_code == 201
        seeded = open(hist, "rb").read()

        w = c.post("/admin/track-row?date=2026-08-06&append=1", headers=hdr)
        assert w.status_code == 201, (w.status_code, w.get_json())
        j = w.get_json()
        assert j["ok"] and j["append"]["wrote"] is True, j
        assert j["row"]["date"] == "2026-08-06" and j["row"]["n_priced"] == 50, j["row"]

        # the write extended the seeded file rather than reshaping it
        assert open(hist, "rb").read().startswith(seeded)
        assert [r["date"] for r in index_track.load(meta, hist)["series"]] == \
            ["2026-07-31", "2026-08-03", "2026-08-06"]

        # and the door is still idempotent on the seeded series
        assert c.post("/admin/track-row?date=2026-08-06&append=1",
                      headers=hdr).status_code == 200
    finally:
        restore()


def test_a_recorded_file_not_in_the_writers_own_form_is_refused_not_rewritten():
    """The byte check, reached only when every recorded VALUE already agrees.

    Found by mutation: replacing this branch with `if False:` left the whole suite green, so
    nothing was exercising it. It fires when the file on disk holds the right records in the
    wrong bytes — hand-edited, or saved by a tool that writes bare LF. Rewriting it would be
    the one thing the append-only guarantee forbids (every line moves), so it refuses, and the
    reason names the encoding rather than leaving a caller to guess at a rejected upload whose
    numbers are visibly identical.
    """
    c, hdr, _, hist, restore = _seed_client()
    try:
        assert _post_seed(c, hdr).status_code == 201
        # same records, bare LF: a real file this project could receive back from a laptop
        open(hist, "wb").write((_H + _R1 + _R2).replace("\r\n", "\n").encode())
        stale = open(hist, "rb").read()

        r = _post_seed(c, hdr, history=_H + _R1 + _R2 + _R3)
        assert r.status_code == 409, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["would_rewrite"] is True, j
        assert "every recorded value matches" in j["reason"], j["reason"]
        assert "line endings" in j["reason"], j["reason"]
        assert open(hist, "rb").read() == stale, "a refused upload still rewrote the file"
    finally:
        restore()


def test_an_upload_may_not_drop_a_column_the_recorded_file_has_gained():
    """A second header rule, and it is NOT the one two tests above.

    That one refuses a header `append_row` would never compute. This one refuses a
    canonically-shaped header that simply disagrees with the file on disk — the case where the
    service's series has gained a column (`MA4` preserves those forever) and a local copy
    predates it. Also found by mutation: the earlier header check fires first on every fixture
    I had written, so this branch was never reached.
    """
    c, hdr, _, hist, restore = _seed_client()
    try:
        wide_h = "date,day_n,valquo_pct,spy_pct,excess_pp,n_priced,vintage\r\n"
        wide = wide_h + _R1.rstrip("\r\n") + ",3\r\n" + _R2.rstrip("\r\n") + ",3\r\n"
        assert _post_seed(c, hdr, history=wide).status_code == 201
        before = open(hist, "rb").read()

        # canonically shaped (ROW_COLUMNS then extras — there are none), and NOT what is there
        r = _post_seed(c, hdr, history=_H + _R1 + _R2)
        assert r.status_code == 409, (r.status_code, r.get_json())
        j = r.get_json()
        assert j["would_rewrite"] is True, j
        assert "differs from the one on disk" in j["reason"], j["reason"]
        assert "vintage" in j["reason"], j["reason"]
        assert open(hist, "rb").read() == before
    finally:
        restore()


def test_the_seed_door_needs_the_admin_token_and_is_post_only():
    """It installs the file `track-backup.yml` calls the one thing that cannot be re-derived."""
    c, hdr, meta, _, restore = _seed_client()
    try:
        assert c.post("/admin/track-seed", json={"book": _SEED_BOOK}).status_code == 401
        assert c.post("/admin/track-seed", headers={"X-Admin-Token": "wrong"},
                      json={"book": _SEED_BOOK}).status_code == 401
        assert c.get("/admin/track-seed", headers=hdr).status_code == 405
        assert not os.path.exists(meta), "an unauthorised call still wrote the book"

        r = c.post("/admin/track-seed", headers=hdr, json={})
        assert r.status_code == 400, (r.status_code, r.get_json())
    finally:
        restore()


def test_the_seed_handler_delegates_and_does_no_file_io_of_its_own():
    """One implementation per rule — the B7 split this project keeps paying for.

    Bounded by the NEXT route rather than a fixed character window: the same check on the
    write door used `src[i:i+2000]` and the handler grew past it, leaving the window over the
    docstring alone. It would have passed vacuously while reporting that the endpoint
    delegates.
    """
    import valuation.saas.app_saas as m

    src = open(m.__file__, encoding="utf-8").read()
    i = src.find('@app.route("/admin/track-seed"')
    assert i > 0
    body = src[i:src.find("@app.route", i + 10)]
    assert len(body) > 500, "the slice did not reach the handler body"

    assert "index_mark.seed(" in body, "the handler does not call the library at all"
    for banned in ("open(", "csv.", "os.replace", "conformance(", "json.dumps"):
        assert banned not in body, (
            "the seed handler contains %r — the rules and the writing belong in "
            "index_mark.seed, so the CLI and this door cannot drift" % banned)
    assert "would_rewrite" in body and "409" in body and "422" in body


def test_the_prefix_flag_does_not_report_a_check_that_never_ran():
    """`prefix_verified` is None on a first seed, True only when a prefix was actually checked.

    On an empty service there is nothing on disk to be a prefix of, so reporting True would be
    a green light for a comparison that did not happen - the vacuous-pass pattern this project
    keeps paying for, and the reason `contract_track.recording_ok` returns None before its
    vintage opens rather than a cheerful true.
    """
    c, hdr, _, _, restore = _seed_client()
    try:
        first = _post_seed(c, hdr)
        assert first.status_code == 201
        assert first.get_json()["prefix_verified"] is None, first.get_json()

        second = _post_seed(c, hdr, history=_H + _R1 + _R2 + _R3)
        assert second.status_code == 201
        assert second.get_json()["prefix_verified"] is True, second.get_json()
    finally:
        restore()


def test_no_test_in_this_file_is_shadowed_by_a_duplicate_name():
    """Every `def test_` in this file must survive to `globals()`.

    A second definition of an existing name rebinds it silently: nothing raises, the suite stays
    green, and one test simply stops running. It happened here - the seed door's byte-prefix
    control was written with the write door's name and deleted it - and it was caught by
    comparing two counts by hand, which is not a thing to rely on twice.
    """
    src = open(os.path.abspath(__file__), encoding="utf-8").read()
    names = re.findall(r"^def (test_\w+)", src, re.M)
    dupes = sorted({n for n in names if names.count(n) > 1})
    assert not dupes, ("these test names are defined more than once, so the earlier one never "
                       "runs: " + ", ".join(dupes))
    live = [k for k in globals() if k.startswith("test_") and callable(globals()[k])]
    assert len(live) == len(names), (
        "%d `def test_` in the file but %d reachable - %s"
        % (len(names), len(live), sorted(set(names) - set(live))))


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
