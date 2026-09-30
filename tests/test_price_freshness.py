"""FRESHNESS IS PART OF SUCCESS — a stale-but-valid vendor frame must fall through.

**THE DEFECT, AND IT COST THE BOUND TRACK ELEVEN TRADING DAYS.** `prices.get_history_df` tested
Stooq's answer with `df.empty or "Close" not in df.columns`. A CSV that is perfectly well-formed
and simply STALE passes both, so the frame was returned as SUCCESS and the yfinance fallback
never ran. `index_mark._closes` then built a date→close map that did not contain the mark date,
and the name read as UNPRICED — no exception, no warning, no fallback, no way to tell the
difference from a genuinely unpriceable symbol.

**THE SYMPTOM WAS DIAGNOSTIC AND IS WHY THE CAUSE IS KNOWN RATHER THAN GUESSED.** Two PT-WRITER
runs on different dates reported coverage identical to fifteen decimal places —
`0.812767489300428` — and the same sixteen unpriced names, symmetric difference empty.
Throttling is stochastic; that is deterministic, and deterministic is what a consistently-stale
vendor file looks like.

**THE CANNED CASE IS THE ONE THE BRIEF ASKED FOR**: a Stooq CSV whose last row is 2026-09-19,
asked for 2026-09-25. Today's code returns it as success; the fixed code must fall through.

**AND OMITTING `as_of` MUST BE BIT-IDENTICAL TO TODAY**, because every other caller in the
repository omits it. A caller that does not name the date it needs cannot be told its frame is
too old for it, and must not be.

Run: python tests/test_price_freshness.py
"""
from __future__ import annotations

import io as _io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.screener import index_mark as IM                          # noqa: E402
from valuation.screener import prices as PR                             # noqa: E402

PASSED = FAILED = 0

STALE_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2026-09-17,700.0,701.0,699.0,700.5,1000\n"
    "2026-09-18,701.0,702.0,700.0,701.5,1000\n"
    "2026-09-19,702.0,703.0,701.0,702.5,1000\n"
)


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


class _Resp:
    """A successful HTTP 200 carrying a valid, stale CSV."""
    status_code = 200
    text = STALE_CSV

    def raise_for_status(self):
        return None


def _with_stale_stooq(fn):
    """Run `fn` with Stooq answering 200-with-stale-CSV and yfinance unavailable.

    yfinance is made to FAIL deliberately: this test is about whether the stale frame is
    RETURNED, and leaving the real fallback in place would reach the network and make the
    result depend on the internet.
    """
    import requests
    real_get, real_yf = requests.get, PR._yf_history
    requests.get = lambda *a, **k: _Resp()
    PR._yf_history = lambda ticker, days, as_of=None: None
    try:
        return fn()
    finally:
        requests.get, PR._yf_history = real_get, real_yf


def test_a_stale_stooq_frame_is_returned_when_no_date_is_named():
    """The unchanged contract: without `as_of` nothing can judge freshness."""
    df = _with_stale_stooq(lambda: PR.get_history_df("SPY", days=400))
    assert df is not None and len(df) == 3, df
    assert PR.source_of(df) == PR.SRC_STOOQ, PR.source_of(df)
    assert PR._last_date(df) == "2026-09-19", PR._last_date(df)


def test_the_same_frame_is_REFUSED_when_the_caller_names_a_later_date():
    """THE pin. Today's code returned this as success; it must now fall through.

    yfinance is stubbed to None here, so falling through means the whole call returns None —
    which is the honest answer: no vendor could price 2026-09-25.
    """
    df = _with_stale_stooq(lambda: PR.get_history_df("SPY", days=400, as_of="2026-09-25"))
    assert df is None, (
        "a stale frame was returned as success for a date it does not contain: last=%r"
        % PR._last_date(df))


def test_a_frame_that_reaches_the_requested_date_is_accepted():
    """Not a blanket refusal — the fix must not reject a fresh frame."""
    df = _with_stale_stooq(lambda: PR.get_history_df("SPY", days=400, as_of="2026-09-19"))
    assert df is not None, "a frame containing the requested date was refused"
    assert PR._last_date(df) == "2026-09-19"


def test_the_stale_rejection_is_counted_not_only_logged():
    """A silent fallback is how this defect survived; the census has to show it."""
    PR.reset_census()
    _with_stale_stooq(lambda: PR.get_history_df("SPY", days=400, as_of="2026-09-25"))
    c = PR.source_census()
    # REPOINTED when yfinance became the primary (2026-09-30). This test was written while
    # Stooq was primary and asserted `primary_failures`, which is a fact about WHICH VENDOR IS
    # FIRST -- not about the property it exists to protect. The property is that a stale answer
    # is COUNTED rather than silently swallowed, and `stale_rejections` is the counter that
    # says so whichever vendor produced it.
    assert c.get("stale_rejections", 0) >= 1, (
        "the stale Stooq answer was not counted at all: %r" % c)


def test_a_stale_frame_is_NOT_retried_with_backoff():
    """AUDIT 6 (2026-09-29). Staleness is deterministic; the backoff is for blips.

    With the stale raise travelling the ordinary except-clause, a consistently one-session-old
    vendor file was fetched THREE times per name with 1.2 s of sleep between -- ~87 x that on
    a stale night is longer than the service's 180 s request timeout, so the writer would have
    failed on timeout rather than on staleness. Exactly ONE Stooq request, no sleep, and the
    census still counts the rejection.
    """
    import requests
    import time as _time
    calls, naps = [], []
    real_get, real_yf, real_sleep = requests.get, PR._yf_history, _time.sleep
    requests.get = lambda *a, **k: (calls.append(a), _Resp())[1]
    PR._yf_history = lambda ticker, days, as_of=None: None
    _time.sleep = lambda s: naps.append(s)
    try:
        PR.reset_census()
        df = PR.get_history_df("SPY", days=400, as_of="2026-09-25")
        assert df is None, df
        assert len(calls) == 1, "a stale frame was fetched %d times" % len(calls)
        assert naps == [], "the stale path slept: %r" % naps
        c = PR.source_census()
        # `primary_failures` deliberately NOT asserted here: Stooq is the fallback now, so a
        # stale Stooq frame is not a primary failure. The count that matters is the rejection.
        assert c.get("stale_rejections", 0) == 1, c
    finally:
        requests.get, PR._yf_history, _time.sleep = real_get, real_yf, real_sleep


def test_the_mark_date_reaches_the_fetcher_from_index_mark():
    """`_closes` must hand the date down, or the vendor can never judge freshness."""
    got = {}

    def fetch(ticker, days=400, as_of=None):
        got["as_of"] = as_of
        return None

    IM._closes("SPY", fetch, {}, as_of="2026-09-25")
    assert got.get("as_of") == "2026-09-25", got


def test_an_old_two_argument_fetcher_still_works_EVEN_WHEN_as_of_IS_SET():
    """THE GAP MY FIRST VERSION OF THIS TEST MISSED, caught by `tests/test_index_mark.py`.

    It originally called `_closes` WITHOUT `as_of` and passed — but `contract_row` ALWAYS sets
    it, so the real path handed every legacy two-argument fetcher an unexpected keyword. That
    raises TypeError, `_closes` swallows it into an empty map, the benchmark leg lost its
    inception price, and 31 tests failed with "SPY could not be priced". A test that exercises
    the easy call and not the shipped one proves nothing about the shipped one.
    """
    calls = []

    def legacy(ticker, days=400):
        calls.append(days)
        return None

    IM._closes("SPY", legacy, {}, as_of="2026-09-25")
    assert calls == [IM.HISTORY_DAYS], (
        "a legacy fetcher was not called, so as_of was passed to something that cannot take "
        "it: %r" % calls)
    assert IM._accepts_as_of(legacy) is False
    assert IM._accepts_as_of(lambda t, days=400, as_of=None: None) is True
    assert IM._accepts_as_of(lambda t, **kw: None) is True


def test_a_stale_frame_makes_the_name_read_unpriced_which_is_the_original_symptom():
    """The end-to-end shape: valid frame, no exception, and the mark date simply absent."""
    import pandas as pd

    def stale(ticker, days=400, as_of=None):
        d = pd.DataFrame({"Date": pd.to_datetime(["2026-09-18", "2026-09-19"]),
                          "Close": [700.0, 702.5]})
        d.attrs["valquo_src"] = "stooq"
        return d

    m = IM._closes("SPY", stale, {}, as_of="2026-09-25")
    assert "2026-09-25" not in m, m
    assert "2026-09-19" in m, "the frame's own dates should still be mapped"


def run():
    global PASSED, FAILED
    print("PRICE FRESHNESS")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
