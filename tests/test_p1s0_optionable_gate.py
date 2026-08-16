"""P1 Stage 0 — the optionable-universe gate, pinned.  [PREREG_p1s0_optionable_gate.md]

The load-bearing assertions here are the ones that would let a WRONG result read as a right
one, so they are the ones written first:

  * the partition cannot see a forward return (it is what lets it be built before the register);
  * the miner's liquidity thresholds are IMPORTED, never re-typed in this lane (B7);
  * `pit_liquid_ok`'s tri-state survives into the universes — an unmeasurable day is not a
    failed day, and collapsing the two silently deletes names for a data reason;
  * the boundary date is EMBARGOED between halves;
  * the three-state verdict grammar cannot collapse to two, because an UNDERPOWERED cell read
    as a FAIL would close the whole options family on a power artefact.

Vacuity is checked wherever a guard could pass by finding nothing (the `sector-neutral` lesson).
"""
from __future__ import annotations

import ast
import contextlib
import io
import os
import shutil
import sys
import tempfile
import tokenize

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import state_isolation  # noqa: F401,E402  (must precede any `valuation` import)

from valuation.studies import optionable_universe as OU  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "valuation", "studies", "optionable_universe.py")


@contextlib.contextmanager
def raises(exc, contains=None):
    try:
        yield
    except exc as e:                                                  # noqa: BLE001
        if contains is not None and contains not in str(e):
            raise AssertionError("expected %r in %r" % (contains, str(e)))
        return
    raise AssertionError("expected %s, nothing raised" % exc.__name__)


def approx(a, b, tol=1e-9):
    return abs(float(a) - float(b)) <= tol


def _code_only(path):
    """Source with comments and strings stripped — a guard that cannot tell code from prose
    about code is not measuring the tree (MA5's own defect, not repeated)."""
    with open(path, encoding="utf-8") as fh:
        src = fh.read()
    out = []
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type not in (tokenize.COMMENT, tokenize.STRING):
            out.append(tok.string)
    return " ".join(out)


# ------------------------------------------------------------------ the partition is blind
def test_the_partition_never_reads_a_forward_return():
    """C2. This is what lets the universe be built BEFORE the register without leaking."""
    blob = _code_only(SRC)
    assert "fwd" not in blob, "optionable_universe references something forward-shaped"
    # vacuity: the stripper must have left real code behind
    assert "date_ticker_partition" in blob and len(blob) > 2000, "the source scan read nothing"


def test_the_builder_is_not_even_handed_the_panel():
    """Stronger than a source scan: it cannot read a return because it never receives one."""
    import inspect
    params = list(inspect.signature(OU.date_ticker_partition).parameters)
    assert params[:2] == ["dates", "tickers"], params
    assert "panel" not in params, "the builder takes a panel — it could see an outcome"


def test_the_miner_thresholds_are_imported_not_retyped():
    """B7 — one definition. A re-typed constant drifts, and this lane refuses to hold one."""
    blob = _code_only(SRC)
    for lit in ("0.15", "500", "2500000", "2_500_000"):
        assert lit not in blob, (
            "optionable_universe hard-codes %s — the miner's bar must be imported via "
            "options_universe.pit_liquidity/_miner_thresholds, never copied" % lit)
    tree = ast.parse(open(SRC, encoding="utf-8").read())
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                imported.add(a.name)
    assert {"pit_liquidity", "pit_liquid_ok"} <= imported, imported


# ------------------------------------------------------------------ as-of slicing
def _chain(days, rows_per_day=4):
    recs = []
    for d in days:
        for i in range(rows_per_day):
            recs.append({"date": pd.Timestamp(d), "strike": 100 + i, "right": "call",
                         "bid": 1.0 + i, "ask": 1.2 + i, "volume": 10, "open_interest": 600})
    return pd.DataFrame(recs)


def test_as_of_takes_the_most_recent_day_at_or_before():
    ch = _chain(["2020-01-06", "2020-01-08", "2020-01-10"])
    sl, stale = OU._as_of_slice(ch, pd.Timestamp("2020-01-09"))
    assert stale == 1
    assert set(pd.to_datetime(sl["date"]).unique()) == {pd.Timestamp("2020-01-08")}


def test_as_of_includes_the_day_itself_at_zero_staleness():
    """ON-OR-BEFORE is deliberate: a chain's existence today is contemporaneous, not a forecast."""
    ch = _chain(["2020-01-08", "2020-01-09"])
    sl, stale = OU._as_of_slice(ch, pd.Timestamp("2020-01-09"))
    assert stale == 0
    assert set(pd.to_datetime(sl["date"]).unique()) == {pd.Timestamp("2020-01-09")}


def test_as_of_never_looks_forward():
    ch = _chain(["2020-01-10"])
    sl, stale = OU._as_of_slice(ch, pd.Timestamp("2020-01-09"))
    assert sl is None and stale is None, "the as-of slice reached a FUTURE chain day"


def test_as_of_refuses_beyond_the_staleness_window():
    ch = _chain(["2020-01-01"])
    sl, _ = OU._as_of_slice(ch, pd.Timestamp("2020-01-20"), stale_max=5)
    assert sl is None


# ------------------------------------------------------------------ tri-state survives
def _part(rows):
    return pd.DataFrame(rows, columns=["date", "ticker", "staleness_days", "n_chain_rows",
                                       "pit_liquid", "median_spread_pct", "atm_oi",
                                       "atm_oi_notional"])


def _panel(pairs):
    return pd.DataFrame([{"date": pd.Timestamp(d), "ticker": t, "value": 1.0} for d, t in pairs])


def test_unmeasurable_is_excluded_from_primary_and_included_in_sensitivity():
    """`pit_liquid_ok` returns None, not False, when the day cannot answer. Collapsing the two
    would delete names for a DATA reason and report it as a LIQUIDITY finding."""
    part = _part([
        [pd.Timestamp("2020-01-15"), "AAA", 0, 50, True, 0.05, 900, 9e6],
        [pd.Timestamp("2020-01-15"), "BBB", 0, 50, False, 0.90, 10, 1e3],
        [pd.Timestamp("2020-01-15"), "CCC", 0, 50, None, None, 0, 0],
    ])
    panel = _panel([("2020-01-15", t) for t in ("AAA", "BBB", "CCC", "DDD")])
    prim = OU.restrict(panel, part, "pit_liquid")
    sens = OU.restrict(panel, part, "has_chain")
    assert set(prim["ticker"]) == {"AAA"}
    assert set(sens["ticker"]) == {"AAA", "BBB", "CCC"}, "sensitivity dropped the unmeasurable day"
    assert "DDD" not in set(sens["ticker"]), "a name with NO chain leaked into the universe"


def test_restrict_refuses_an_unknown_mode():
    with raises(ValueError):
        OU.restrict(_panel([("2020-01-15", "AAA")]), _part([]), "whatever_clears")


def test_restrict_on_an_empty_partition_returns_empty_not_everything():
    """A failure that returned the FULL panel would silently score the unrestricted book and
    report it as the optionable result — the worst available failure direction."""
    panel = _panel([("2020-01-15", "AAA"), ("2020-01-15", "BBB")])
    out = OU.restrict(panel, _part([]), "pit_liquid")
    assert len(out) == 0


# ------------------------------------------------------------------ coverage
def test_coverage_report_counts_liquid_unmeasurable_and_zero_dates():
    part = _part([
        [pd.Timestamp("2020-01-15"), "AAA", 0, 50, True, 0.05, 900, 9e6],
        [pd.Timestamp("2020-01-15"), "BBB", 2, 50, None, None, 0, 0],
    ])
    dates = [pd.Timestamp("2020-01-15"), pd.Timestamp("2020-04-15")]
    cov = OU.coverage_report(part, dates, {dates[0]: 10, dates[1]: 10})
    assert cov["n_panel_dates"] == 2
    assert cov["n_dates_any_chain"] == 1
    assert cov["n_dates_zero_chain"] == 1
    assert cov["n_unmeasurable"] == 1
    assert cov["staleness_days_max"] == 2
    assert cov["per_date"][0]["pit_liquid"] == 1


# ------------------------------------------------------------------ the cache-root trap
def test_an_existing_but_empty_options_dir_is_not_a_populated_cache():
    """A git worktree carries its own EMPTY data/. Resolving to it reads as 'no coverage'
    rather than 'wrong root' — `options_backtest.BARS_CACHE`'s defect (session 25). EXISTENCE
    IS NOT POPULATION, and this is the assertion that keeps the two apart."""
    tmp = tempfile.mkdtemp()
    try:
        root = os.path.join(tmp, "data")
        os.makedirs(os.path.join(root, "options"))
        assert OU.is_populated_cache(root) is False, "an empty options/ passed as populated"
        with open(os.path.join(root, "options", "README.txt"), "w") as fh:
            fh.write("not a ticker dir")
        assert OU.is_populated_cache(root) is False, "a stray FILE passed as a ticker dir"
        os.makedirs(os.path.join(root, "options", "AAPL"))
        assert OU.is_populated_cache(root) is True
        assert OU.is_populated_cache(None) is False
        assert OU.is_populated_cache(os.path.join(tmp, "nope")) is False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_data_root_honours_an_explicit_path_and_raises_when_nothing_is_populated():
    assert OU._data_root("/explicit/path") == "/explicit/path"
    old = OU.is_populated_cache
    try:
        OU.is_populated_cache = lambda r: False
        with raises(FileNotFoundError, contains="populated"):
            OU._data_root(None)
    finally:
        OU.is_populated_cache = old


# ------------------------------------------------------------------ the gate's own helpers
def test_halves_embargo_the_boundary_date():
    from scripts.p1s0_optionable_gate import halves
    ds = [pd.Timestamp("2020-01-%02d" % i) for i in range(1, 11)]
    e, l, b = halves(ds)
    assert len(e) == 5 and len(l) == 4
    assert b == ds[5]
    assert b not in e and b not in l, "the boundary date was scored in a half"


_FLOORS = {"floors": {"63": {"early_p95": 2.0, "late_p95": 2.0, "full_p95": 2.0,
                             "cum_alpha_full_sd": 0.01}}}


def test_verdict_cannot_collapse_three_states_into_two():
    """An UNDERPOWERED cell read as a FAIL closes the entire options family on a power
    artefact. That is the most expensive single mistake available in this register."""
    from scripts.p1s0_optionable_gate import verdict
    passing = {"full": {"alpha_t_hac": 3.0, "cum_alpha": 0.05},
               "early": {"alpha_t_hac": 2.5}, "late": {"alpha_t_hac": 2.4}}
    assert verdict(passing, _FLOORS, 63, reference_cum_alpha=0.05)["state"] == "PASS"

    # does not clear either half, but the full-sample statistic DID reach the bar -> FAIL
    failing = {"full": {"alpha_t_hac": 2.2, "cum_alpha": 0.03},
               "early": {"alpha_t_hac": 1.0}, "late": {"alpha_t_hac": 1.1}}
    assert verdict(failing, _FLOORS, 63, reference_cum_alpha=0.05)["state"] == "FAIL"

    # nowhere near the bar anywhere -> UNDERPOWERED, which carries NO verdict
    weak = {"full": {"alpha_t_hac": 0.2, "cum_alpha": 0.001},
            "early": {"alpha_t_hac": 0.1}, "late": {"alpha_t_hac": 0.3}}
    assert verdict(weak, _FLOORS, 63, reference_cum_alpha=0.05)["state"] == "UNDERPOWERED"


def test_verdict_requires_BOTH_halves_not_either():
    from scripts.p1s0_optionable_gate import verdict
    one_half = {"full": {"alpha_t_hac": 2.9, "cum_alpha": 0.05},
                "early": {"alpha_t_hac": 3.5}, "late": {"alpha_t_hac": 0.4}}
    v = verdict(one_half, _FLOORS, 63, reference_cum_alpha=0.05)
    assert v["state"] != "PASS", "one half cleared and the arm passed"
    assert v["both_halves"]["early"]["clears"] is True
    assert v["both_halves"]["late"]["clears"] is False


def test_the_power_reading_is_reported_and_does_not_decide():
    """The register's §4 wording is weak and is left UNEDITED; the informative power reading
    travels beside it as REPORTED. Both must be present, and only `state` decides."""
    from scripts.p1s0_optionable_gate import verdict
    weak = {"full": {"alpha_t_hac": 0.2, "cum_alpha": 0.001},
            "early": {"alpha_t_hac": 0.1}, "late": {"alpha_t_hac": 0.3}}
    # MDE = p95_t * sd_null = 2.0 * 0.01 = 0.02; a reference below it is invisible to the design
    v = verdict(weak, _FLOORS, 63, reference_cum_alpha=0.005)
    assert approx(v["power"]["mde_cum_alpha"], 0.02)
    assert v["power"]["design_can_see_the_known_effect"] is False
    v2 = verdict(weak, _FLOORS, 63, reference_cum_alpha=0.50)
    assert v2["power"]["design_can_see_the_known_effect"] is True
    assert v2["state"] == "UNDERPOWERED", "the reported power reading changed the VERDICT"


def test_the_gate_refuses_to_score_arms_without_a_controls_artifact():
    """The O19 two-pass design. Session 26 shipped a register whose gating control ran in the
    same pass as its outcomes; the refusal is what makes 'the control was read first' checkable."""
    import scripts.p1s0_optionable_gate as G
    old = G.CONTROLS_JSON
    G.CONTROLS_JSON = os.path.join(REPO, "no_such_controls_artifact_p1s0.json")
    try:
        with raises(SystemExit, contains="REFUSING"):
            G.arms()
    finally:
        G.CONTROLS_JSON = old


def test_the_registered_horizons_are_exactly_the_three_and_the_anchor_is_h63():
    """Void condition 3 — the grid is {63,252,504} and nothing else. A fourth horizon scored
    would be searching until something clears."""
    import scripts.p1s0_optionable_gate as G
    assert G.HORIZONS == [63, 252, 504]
    assert G.POWER_ANCHOR == 63
    assert G.GATE_HORIZONS == [252, 504]
    assert G.PRIMARY_MODE == "pit_liquid"
    assert G.MODES == ("pit_liquid", "has_chain")
    assert G.PLACEBO_DRAWS == 200


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                        # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
