"""
O14 tick-flow miner tests (offline, no network, no feed key). Run:
    python tests/test_tick_flow.py

These pin the CACHE SEMANTICS, not the data. The miner's three standing rules are exactly the
ones this project has broken before and paid for:

  * SKIP-EXISTING must treat `.empty` as covered and `.missing` as still-owed. The EOD cache
    lost AAPL 2026 permanently to a sticky `.missing` marker; the distinction is the fix and it
    is worth a test that fails loudly if anyone "simplifies" the three states into two.
  * NEVER-DESTROY: the write is atomic, and no code path unlinks a payload.
  * The SLIM step must be lossless. It narrows dtypes for size, and a narrowing that silently
    wrapped a value would corrupt flow data in a way no run would report.
"""
import datetime as dt
import os
import shutil
import sys
import tempfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mine_tick_flow as M  # noqa: E402


def _frame(n=50):
    rng = np.random.default_rng(0)
    return pd.DataFrame({
        "symbol": ["ZZZ"] * n,
        "expiration": pd.to_datetime(["2024-03-15"] * n),
        "strike": rng.uniform(10, 500, n).astype("float64"),
        "right": ["CALL" if i % 2 else "PUT" for i in range(n)],
        "trade_timestamp": pd.to_datetime(["2024-01-05 10:00:00"] * n),
        "quote_timestamp": pd.to_datetime(["2024-01-05 09:35:00"] * n),
        "sequence": rng.integers(-2_000_000, 2_000_000, n),
        "ext_condition1": np.full(n, 255), "ext_condition2": np.full(n, 255),
        "ext_condition3": np.full(n, 255), "ext_condition4": np.full(n, 255),
        "condition": rng.integers(0, 200, n),
        "size": rng.integers(1, 5000, n),
        "exchange": rng.integers(0, 60, n),
        "price": rng.uniform(0.01, 90, n),
        "bid_size": rng.integers(0, 9000, n), "bid_exchange": rng.integers(0, 60, n),
        "bid": rng.uniform(0, 90, n), "bid_condition": rng.integers(0, 60, n),
        "ask_size": rng.integers(0, 9000, n), "ask_exchange": rng.integers(0, 60, n),
        "ask": rng.uniform(0, 90, n), "ask_condition": rng.integers(0, 60, n),
    })


def test_tri_state_skip_existing():
    """`.pkl` and `.empty` are COVERED; `.missing` is a GAP that must be retried."""
    root = tempfile.mkdtemp()
    try:
        sym, day = "ZZZ", "2024-01-05"
        p = M.unit_path(sym, day, root)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        assert M.needs_pull(sym, day, root), "an absent unit is owed"

        open(p + ".missing", "w").close()
        assert M.needs_pull(sym, day, root), \
            "a .missing marker must NOT be sticky - this is the AAPL-2026 bug"

        os.remove(p + ".missing")
        open(p + ".empty", "w").close()
        assert not M.needs_pull(sym, day, root), "a genuinely empty unit is covered"

        os.remove(p + ".empty")
        open(p, "wb").close()
        assert not M.needs_pull(sym, day, root), "a payload is covered"
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_slim_is_lossless():
    """Every narrowing must round-trip. A wrapped int here would be invisible corruption."""
    df = _frame(200)
    before = df.copy()
    out, notes = M.slim(df.copy(), "2024-01-05")
    assert "symbol" not in out.columns, "symbol is constant per unit; it lives in the header"
    assert len(out) == len(before)
    for c in ("condition", "size", "exchange", "bid_size", "ask_size", "sequence",
              "ext_condition1"):
        assert (out[c].astype("int64").to_numpy()
                == before[c].astype("int64").to_numpy()).all(), f"{c} did not round-trip"
    # float32 is a deliberate precision choice, so assert the tolerance rather than equality.
    for c in ("strike", "price", "bid", "ask"):
        assert np.allclose(out[c].astype("float64"), before[c], rtol=1e-6), c
    assert set(out["right"].astype(str)) <= {"C", "P"}, set(out["right"].astype(str))
    assert not notes.get("kept_wide"), notes


def test_out_of_range_keeps_the_wide_type_and_says_so():
    """A value that will not fit must be REPORTED, never silently wrapped."""
    df = _frame(20)
    df.loc[0, "condition"] = 70_000          # far past uint8
    out, notes = M.slim(df.copy(), "2024-01-05")
    assert out["condition"].max() == 70_000, "the value must survive intact"
    assert any(n.startswith("condition[") for n in notes.get("kept_wide", [])), notes
    assert out["condition"].dtype != np.uint8


def test_alert_days_are_unique_symbol_date_pairs():
    """The unit of work is the banked alert-day. Read-only, and deduplicated."""
    book = os.path.join(M.REPO, "data", "options_universe", "state_r2_corrected.pkl")
    if not os.path.exists(book):
        print("    (skipped: book not on disk)")
        return
    before = os.path.getmtime(book)
    units = M.alert_days(book)
    assert len(units) == len(set(units)), "units must be unique"
    assert all(len(d) == 10 and d[4] == "-" for _, d in units), "dates are ISO"
    assert os.path.getmtime(book) == before, "the book must never be written"


def test_coverage_counts_every_state_and_sums_to_the_total():
    root = tempfile.mkdtemp()
    try:
        units = [("AAA", "2024-01-05"), ("BBB", "2024-01-05"), ("CCC", "2024-01-05"),
                 ("DDD", "2024-01-05")]
        for sym in ("AAA", "BBB", "CCC"):
            os.makedirs(os.path.join(root, sym), exist_ok=True)
        open(M.unit_path("AAA", "2024-01-05", root), "wb").write(b"x" * 100)
        open(M.unit_path("BBB", "2024-01-05", root) + ".empty", "w").close()
        open(M.unit_path("CCC", "2024-01-05", root) + ".missing", "w").close()
        old = M.TICKROOT
        M.TICKROOT = root
        try:
            cov = M.coverage_report(units, root)
        finally:
            M.TICKROOT = old
        assert cov["units_with_data"] == 1, cov
        assert cov["units_empty"] == 1 and cov["units_missing"] == 1, cov
        assert cov["units_not_attempted"] == 1, cov
        assert (cov["units_with_data"] + cov["units_empty"] + cov["units_missing"]
                + cov["units_not_attempted"] == cov["units_total"]), "states must partition"
        # An empty unit is COVERED but still surfaced, because a liquid name with no prints on
        # an alert day is more likely a bad date than a quiet tape.
        assert cov["coverage_frac"] == 0.5, cov["coverage_frac"]
        assert "BBB|2024-01-05" in cov["empty_units"], cov["empty_units"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_no_code_path_deletes_a_payload():
    """Never-destroy, asserted against the source rather than trusted."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "mine_tick_flow.py"), encoding="utf-8").read()
    for bad in ("os.remove(path)", "os.unlink(path)", "shutil.rmtree"):
        assert bad not in src, f"{bad} must not appear: payloads are never destroyed"
    assert src.count("os.remove(") == 1, "the only unlink is the .missing marker"
    assert 'os.remove(path + ".missing")' in src
    assert "os.replace(tmp, path)" in src, "writes must be atomic"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}"); passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:                                            # noqa: BLE001
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{passed}/{len(tests)} tick-flow tests passed")
    return passed == len(tests)


if __name__ == "__main__":
    sys.exit(0 if _run_all() else 1)
