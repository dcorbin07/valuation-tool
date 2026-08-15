"""AUDIT MA48 - a current-year theta cache freezes at its mine date and `needs_pull` refuses it.

Run: python tests/test_ma48_cache_span.py

THE DEFECT. `_fetch_year` clamps `year_end = min(Dec 31, today)`, so a year mined while it was
still current is RIGHT-TRUNCATED, and nothing recorded where it stopped. `needs_pull`'s only
refresh trigger was DEPTH (`cached_dte < max_dte`) - a DTE ceiling, not a calendar - so such a
file was cached forever and any study whose window ran past the mine date read empty `chain_on`
slices, uncounted. Once the calendar rolled over, the year looked complete and the evidence was
gone.

MEASURED on the cache as it stands (2026-08-15): 0 of 5,063 cached symbol-years were mined
during their own year, verified against the frames' own max(date) on a sample - 14 of 14 ran
Jan 2 to Dec 31 - and there are no 2026 files at all. So the trap is LATENT: no banked study is
affected and the repair re-mines nothing. That measurement is what licenses treating a legacy
file (no `.span` sidecar) as complete for a PAST year; a legacy CURRENT-year file is treated as
stale, which is the safe direction and costs nothing today.

The sibling in `thetadata_provider.chain_on` is the same disease: `_call` returned None for both
"no data" and "every retry failed", and the empty frame was cached permanently for both.
"""
import datetime as dt
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import theta_bulk as TB                      # noqa: E402


def _mk(root, sym, year, span=None):
    d = os.path.join(root, sym.upper())
    os.makedirs(d, exist_ok=True)
    p = TB.year_path(sym, year, root)
    with open(p, "wb") as f:
        f.write(b"x")
    if span:
        with open(p + ".span", "w", encoding="utf-8") as f:
            f.write("%s pulled %s\n" % (span, span))
    return p


def test_requested_span_end_is_the_fetchers_own_clamp():
    assert TB.requested_span_end(2024, dt.date(2026, 8, 15)) == dt.date(2024, 12, 31)
    assert TB.requested_span_end(2026, dt.date(2026, 8, 15)) == dt.date(2026, 8, 15)


def test_the_clamp_has_one_definition():
    """_fetch_year must use the shared helper, not a second copy of min(Dec31, today)."""
    import inspect
    src = inspect.getsource(TB.ThetaBulk._fetch_year)
    assert "requested_span_end(year, today)" in src
    assert "dt.date(year, 12, 31), today" not in src, "the second copy of the clamp is back"


def test_a_truncated_year_is_stale_and_a_complete_one_is_not():
    root = tempfile.mkdtemp()
    try:
        _mk(root, "AAA", 2026, span="2026-03-01")          # mined while 2026 was running
        _mk(root, "BBB", 2025, span="2025-12-31")          # finished year, fully covered
        today = dt.date(2026, 8, 15)
        assert TB.span_is_stale("AAA", 2026, root, today) is True
        assert TB.span_is_stale("BBB", 2025, root, today) is False
        assert TB.cached_span_end("AAA", 2026, root) == dt.date(2026, 3, 1)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_year_mined_during_itself_becomes_stale_once_time_passes():
    """The case the old code could never see: same file, later date, now incomplete."""
    root = tempfile.mkdtemp()
    try:
        _mk(root, "CCC", 2026, span="2026-08-15")
        assert TB.span_is_stale("CCC", 2026, root, dt.date(2026, 8, 15)) is False
        assert TB.span_is_stale("CCC", 2026, root, dt.date(2026, 9, 30)) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_a_legacy_file_is_complete_for_a_past_year_and_stale_for_the_current_one():
    """No sidecar. The past-year answer is the MEASURED one; the current-year answer is safe."""
    root = tempfile.mkdtemp()
    try:
        _mk(root, "DDD", 2024)
        _mk(root, "EEE", 2026)
        today = dt.date(2026, 8, 15)
        assert TB.cached_span_end("DDD", 2024, root) is None
        assert TB.span_is_stale("DDD", 2024, root, today) is False, \
            "re-mining the whole legacy cache would be a false alarm; 0 of 5,063 are truncated"
        assert TB.span_is_stale("EEE", 2026, root, today) is True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_needs_pull_now_refuses_a_short_span():
    """The known-bad case: pre-fix this returned False and the year was cached forever."""
    root = tempfile.mkdtemp()
    try:
        _mk(root, "FFF", 2026, span="2026-01-31")
        b = TB.ThetaBulk.__new__(TB.ThetaBulk)
        b.root, b.upgrade_depth, b.max_dte = root, False, 90
        assert b.needs_pull("FFF", 2026) is True, "depth alone can never see a short span"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_needs_pull_is_unchanged_for_a_complete_year():
    """No spurious re-mining: the whole existing cache must stay cached."""
    root = tempfile.mkdtemp()
    try:
        _mk(root, "GGG", 2024, span="2024-12-31")
        _mk(root, "HHH", 2023)                              # legacy, no sidecar
        b = TB.ThetaBulk.__new__(TB.ThetaBulk)
        b.root, b.upgrade_depth, b.max_dte = root, False, 90
        assert b.needs_pull("GGG", 2024) is False
        assert b.needs_pull("HHH", 2023) is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_an_exhausted_year_still_wins_over_a_stale_span():
    """Ordering matters: a name that repeatedly fails must not be re-queued forever."""
    root = tempfile.mkdtemp()
    try:
        p = _mk(root, "III", 2026, span="2026-01-31")
        with open(p + ".exhausted", "w", encoding="utf-8") as f:
            f.write("3 failed attempts\n")
        b = TB.ThetaBulk.__new__(TB.ThetaBulk)
        b.root, b.upgrade_depth, b.max_dte = root, False, 90
        assert b.needs_pull("III", 2026) is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_the_writer_records_the_span_beside_the_dte():
    import inspect
    src = inspect.getsource(TB.ThetaBulk.ensure_year)
    assert '.span' in src and "requested_span_end(year).isoformat()" in src


def test_a_failed_feed_call_is_not_cached_as_an_empty_chain():
    """The sibling defect: `chain_on` cached a transient outage permanently."""
    import inspect
    from valuation.edge import thetadata_provider as TP
    src = inspect.getsource(TP.ThetaProvider.chain_on)
    assert "_last_call_failed" in src, "chain_on must not cache a failure"
    call_src = inspect.getsource(TP.ThetaProvider._call)
    assert call_src.count("_last_call_failed = True") >= 2, \
        "both the retries-exhausted paths must be marked"
    assert "_last_call_failed = False" in call_src, "and it must be reset per call"


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(list(globals().items())):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:                                   # noqa: BLE001
                fails += 1
                print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (sum(1 for n in globals() if n.startswith("test_")) - fails,
                                    fails))
    sys.exit(1 if fails else 0)
