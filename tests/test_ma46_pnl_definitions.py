"""AUDIT MA46 - the two options recorders defined `pnl_pct` differently after B15.

Run: python tests/test_ma46_pnl_definitions.py

THE DEFECT. B15 made the backtest's `return_pct` NET of the round-trip commission and kept the
old quantity beside it as `return_pct_gross_comm`. The forward tracker went on computing
`ex / entry - 1` - precisely the quantity B15 had just renamed - so the live book was being
scored against a reference computed a different way, on the one axis (live vs backtest) the
forward book exists to measure. The paper broker's real sandbox commissions never entered
recorded P&L either.

THE REPAIR IS RECORD-BOTH, which is the second fix the audit offers and the one this codebase can
take. One shared `options_fill.net_return_pct` serves both modules; the tracker keeps `pnl_pct`
gross and reports `expectancy_pct_net` beside it. The contract count cancels out of the formula,
so the net series is complete over the whole book with no migration and no assumption about size.

WHY NOT SIMPLY NET THE HEADLINE, which was the first cut and is pinned here as a fact rather than
an opinion: it collides with MA36. A worthless expiry must read EXACTLY -100%; netting makes it
-100.26%, and an expiring option is never sold, so there is no second commission leg to charge in
the first place. See `test_netting_the_headline_would_have_broken_MA36s_minus_100_convention`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_fill as F                     # noqa: E402
from valuation.edge import options_tracker as T                  # noqa: E402


def test_net_return_pct_is_the_backtests_own_arithmetic():
    """Reproduces B15's expression exactly - the one it replaced, not a plausible rewrite."""
    entry, exit_px, n = 2.57, 3.10, 3
    mult = F.CONTRACT_MULTIPLIER * n
    commission = F.COMMISSION_PER_CONTRACT * n * 2
    expected = ((exit_px - entry) * mult - commission) / (entry * mult)
    assert F.net_return_pct(entry, exit_px, n) == expected


def test_the_contract_count_cancels():
    """Why an old row can be restated without knowing how many contracts it held.

    ALGEBRAICALLY exact, and NOT bit-exact in IEEE754: `((x-e)*M*n - c*n) / (e*M*n)` evaluates
    through different intermediate magnitudes for different `n`, and the measured spread across
    n = 1..50 is one unit in the last place (~3e-17). Stated rather than papered over with a
    round(), because the restatement in `net_pnl_pct_of_row` leans on this cancellation and a
    reader is entitled to know it holds to floating point and not beyond it.
    """
    vals = [F.net_return_pct(2.57, 3.10, n) for n in (1, 2, 7, 50)]
    assert max(vals) - min(vals) < 1e-15, vals
    assert abs(max(vals) - min(vals)) > 0.0 or len(set(vals)) == 1   # either is fine; document it


def test_it_is_strictly_below_the_gross_figure_and_by_the_commission():
    entry, exit_px = 2.57, 3.10
    gross = exit_px / entry - 1.0
    net = F.net_return_pct(entry, exit_px, 1)
    assert net < gross
    drop = gross - net
    expected = (2 * F.COMMISSION_PER_CONTRACT) / (F.CONTRACT_MULTIPLIER * entry)
    assert abs(drop - expected) < 1e-12
    assert 0.001 < drop < 0.01, "about half a point on a $2.57 premium: %r" % drop


def test_round_trip_delegates_rather_than_keeping_a_second_copy():
    import inspect
    src = inspect.getsource(F.round_trip)
    assert "net_return_pct(entry, exit_px, contracts)" in src
    assert "net / (entry * mult)" not in src, "the second copy is back"
    # and the gross quantity B15 kept for continuity is still there
    assert "return_pct_gross_comm" in src


def test_round_trip_still_reports_the_same_net_number_it_always_did():
    """Delegation must not have changed the backtest's own figure."""
    q_in = F.Quote(bid=2.50, ask=2.64, oi=900, volume=400)
    q_out = F.Quote(bid=3.05, ask=3.15, oi=900, volume=400)
    r = F.round_trip(q_in, q_out, "C", 100.0, contracts=2)
    assert r["ok"], r
    mult = F.CONTRACT_MULTIPLIER * 2
    expected = (r["net_pnl"]) / (r["entry_fill"] * mult)
    assert abs(r["return_pct"] - expected) < 1e-12
    assert r["return_pct"] < r["return_pct_gross_comm"]


def test_the_net_figure_is_derived_for_a_row_that_never_stored_one():
    """Old rows need no migration: the contract count cancels, so it reconstructs exactly."""
    row = {"pnl_pct": 3.10 / 2.57 - 1.0, "entry_premium": 2.57, "exit_premium": 3.10}
    val, derived = T.net_pnl_pct_of_row(row)
    assert derived is True
    assert val == F.net_return_pct(2.57, 3.10, 1)
    assert val < row["pnl_pct"], "net is below gross, always"


def test_a_stored_net_value_is_read_rather_than_recomputed():
    net = F.net_return_pct(2.57, 3.10, 1)
    row = {"pnl_pct": 3.10 / 2.57 - 1.0, "pnl_pct_net": net,
           "entry_premium": 2.57, "exit_premium": 3.10}
    val, derived = T.net_pnl_pct_of_row(row)
    assert derived is False and val == net


def test_a_row_with_nothing_to_derive_from_yields_nothing_rather_than_a_guess():
    row = {"pnl_pct": 0.2, "entry_premium": None, "exit_premium": None}
    val, derived = T.net_pnl_pct_of_row(row)
    assert derived is False and val is None


def test_stats_reports_BOTH_bases_and_moves_no_published_figure():
    """The repair is labelling, not restating: `expectancy_pct` keeps its meaning exactly."""
    rows = [{"pnl_pct": 1.0, "entry_premium": 5.0, "exit_premium": 10.0, "pnl_dollars": 500.0},
            {"pnl_pct": -0.5, "entry_premium": 5.0, "exit_premium": 2.5, "pnl_dollars": -250.0}]
    s = T._stats(rows)
    assert s["n_closed"] == 2
    assert abs(s["expectancy_pct"] - 0.25) < 1e-12, "the GROSS mean, unchanged"
    assert abs(s["cum_pnl_dollars"] - 250.0) < 1e-9, "dollars gross, unchanged"
    assert s["expectancy_pct_net"] < s["expectancy_pct"]
    assert s["n_net"] == 2 and s["rows_net_derived"] == 2
    assert "gross" in s["pnl_basis"] and "expectancy_pct_net" in s["pnl_basis"]


def test_netting_the_headline_would_have_broken_MA36s_minus_100_convention():
    """Why the gross figure is the one left in place — the collision, pinned as a fact.

    MA36 requires a worthless expiry to read EXACTLY -100%. Netting would make it -100.26%, and
    an expiring option is never sold, so there is no second commission leg to charge at all.
    """
    rows = [{"pnl_pct": -1.0, "entry_premium": 5.0, "exit_premium": 0.0, "pnl_dollars": -500.0}]
    s = T._stats(rows)
    assert s["expectancy_pct"] == -1.0, "MA36: a worthless expiry is exactly -100%"
    assert s["expectancy_pct_net"] < -1.0, "which is precisely why it is not the headline"
    assert abs(s["expectancy_pct_net"] - (-1.0026)) < 1e-9


def test_the_empty_book_also_declares_its_basis():
    """An empty scorecard must not be the one place the basis is unstated."""
    s = T._stats([])
    assert s["n_closed"] == 0
    assert "gross" in s["pnl_basis"]
    assert s["expectancy_pct_net"] is None and s["rows_net_derived"] == 0


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
