"""
PEAD point-in-time guarantees. Run:
    python tests/test_pead.py

The signal was TESTED AND REJECTED (see `valuation/edge/pead.py` and `HANDOFF_pead.md`), and
these tests deliberately do NOT pin that verdict — it is a research finding that may change if
real analyst estimates ever arrive. What they pin is the WIRING and the one load-bearing
correctness property, following the `sector_neutral` precedent: a rejected signal keeps its
plumbing, and the plumbing has to stay honest so a re-test measures the thing it claims to.

`pead_signals` is called from `build_fundamental_panel` on every panel row and had no test
coverage at all. Its load-bearing property is that a signal NEVER contains a return from after
the rebalance date. A CAR is a forward-looking window by construction, so an off-by-one here
does not raise, does not dent coverage, and would manufacture an edge out of nothing — the
most dangerous possible failure in this codebase, and invisible to every other guard.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from valuation.edge.pead import CAR_WINDOW, DRIFT_WINDOW_DAYS, pead_signals


def _series(n=120, start="2020-01-01"):
    """n consecutive business days of prices and a flat benchmark."""
    dates = np.array([np.datetime64(start, "D") + i for i in range(n)], dtype="datetime64[D]")
    closes = np.array([100.0 + i * 0.1 for i in range(n)], dtype=float)
    bench = np.full(n, 50.0, dtype=float)
    return closes, dates, bench


# --------------------------------------------------------------------------- #
#  the load-bearing property: no future return may enter a signal
# --------------------------------------------------------------------------- #
def test_an_announcement_after_the_rebalance_is_invisible():
    closes, dates, bench = _series()
    as_of = dates[50]
    out = pead_signals(closes, dates, bench, [str(dates[80])], as_of)
    assert out == {}, f"used an announcement from the future: {out}"


def test_an_announcement_whose_car_window_has_not_closed_is_refused():
    """The subtler half. The announcement is in the past, but its [t-1, t+1] window extends
    past the rebalance — scoring it would use returns that had not happened yet."""
    closes, dates, bench = _series()
    i = 50
    as_of = dates[i]                      # window needs i+1, which is AFTER as_of
    assert pead_signals(closes, dates, bench, [str(dates[i])], as_of) == {}
    # one day later the window has closed, and it becomes usable
    out = pead_signals(closes, dates, bench, [str(dates[i])], dates[i + CAR_WINDOW[1]])
    assert "pead_car" in out, "a closed window should produce a signal"


def test_the_car_uses_only_prices_from_inside_its_window():
    """Corrupting the future must not change a signal whose window already closed."""
    closes, dates, bench = _series()
    i, as_of = 40, None
    as_of = dates[60]
    base = pead_signals(closes, dates, bench, [str(dates[i])], as_of)
    tampered = closes.copy()
    tampered[i + CAR_WINDOW[1] + 1:] *= 5.0        # everything after the window
    after = pead_signals(tampered, dates, bench, [str(dates[i])], as_of)
    assert base["pead_car"] == after["pead_car"], "a post-window price leaked into the CAR"


def test_the_most_recent_qualifying_announcement_wins():
    closes, dates, bench = _series()
    as_of = dates[70]
    anns = [str(dates[10]), str(dates[40]), str(dates[95])]   # last one is in the future
    out = pead_signals(closes, dates, bench, anns, as_of)
    only40 = pead_signals(closes, dates, bench, [str(dates[40])], as_of)
    assert out["pead_car"] == only40["pead_car"], "should use the latest PAST announcement"


# --------------------------------------------------------------------------- #
#  signal construction
# --------------------------------------------------------------------------- #
def test_the_car_is_abnormal_not_raw_when_a_benchmark_is_given():
    closes, dates, _ = _series()
    rising = np.array([50.0 * (1.0 + 0.01 * i) for i in range(len(dates))])
    as_of = dates[60]
    raw = pead_signals(closes, dates, None, [str(dates[40])], as_of)["pead_car"]
    abn = pead_signals(closes, dates, rising, [str(dates[40])], as_of)["pead_car"]
    assert abn < raw, "a rising benchmark must be subtracted off"


def test_drift_is_absent_rather_than_decayed_when_the_announcement_is_old():
    """An explicit absence is honest; a faded number pretends to information."""
    closes, dates, bench = _series(n=260)
    old = dates[10]
    as_of = dates[10 + DRIFT_WINDOW_DAYS + 30]
    out = pead_signals(closes, dates, bench, [str(old)], as_of)
    assert "pead_car" in out, "the all-ages CAR should still be present"
    assert "pead_drift" not in out, "a stale announcement must not produce a drift signal"


def test_drift_is_present_while_the_announcement_is_recent():
    closes, dates, bench = _series(n=260)
    i = 100
    as_of = dates[i + 5]
    out = pead_signals(closes, dates, bench, [str(dates[i])], as_of)
    assert out.get("pead_drift") == out.get("pead_car"), (
        "inside the window the two are the same number by construction")


def test_no_announcements_yields_no_signal_not_a_zero():
    """A name with no earnings date is UNKNOWN, not 'no news'. A zero would be scored as an
    average surprise and drag the theme mean toward the middle."""
    closes, dates, bench = _series()
    assert pead_signals(closes, dates, bench, [], dates[50]) == {}
    assert pead_signals(closes, dates, bench, None, dates[50]) == {}


def test_an_announcement_too_early_for_a_full_window_is_refused():
    closes, dates, bench = _series()
    assert pead_signals(closes, dates, bench, [str(dates[0])], dates[50]) == {}


# --------------------------------------------------------------------------- #
#  wiring — a rejected signal must stay MEASURED, not silently vanish
# --------------------------------------------------------------------------- #
def test_both_variants_are_still_registered_so_they_keep_being_measured():
    """Rejected means 'scores in no theme', NOT 'unwired'. Registration is what keeps the IC
    and coverage in every run, so the negative result stays visible instead of rotting."""
    from valuation.screener import settings as S
    for n in ("pead_car", "pead_drift"):
        assert n in S.NUMBERS_ALL, f"{n} dropped out of the measured set"
        assert S.NUMBER_THEME.get(n) == "momentum"


def test_neither_variant_scores_in_the_momentum_composite():
    """The actual verdict, pinned where it is enforced: momentum is the mean of its three
    price inputs and must not silently regain a PEAD term."""
    import inspect
    from valuation.screener import factors as F
    src = inspect.getsource(F.build_frame)
    line = [l for l in src.splitlines() if 'df["momentum"]' in l and "mean(axis=1)" in l]
    assert line, "could not find the momentum composite"
    assert "pead" not in line[0], f"PEAD re-entered the momentum composite: {line[0].strip()}"


def test_the_panel_still_calls_the_signal():
    import inspect
    from valuation.edge import fundamental_panel as P
    src = inspect.getsource(P.build_fundamental_panel)
    assert "pead_signals" in src, "the panel stopped computing PEAD entirely"


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
    print(f"\n{passed}/{len(tests)} PEAD tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
