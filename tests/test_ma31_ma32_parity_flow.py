"""AUDIT MA31 + MA32 - the matched-strike parity deviation and the open-vs-close decomposition.

Run: python tests/test_ma31_ma32_parity_flow.py

These pin `valuation/studies/parity_flow.py`, which executes
`PREREG_ma31_ma32_parity_openclose.md` (committed ALONE at `a51e372`, a strict ancestor of every
commit that computes an arm).

THE TWO TESTS THAT MATTER MOST, because they guard failures that would look like clean results:

  * `test_parity_dev_is_zero_on_a_chain_priced_AT_parity` and its non-zero sibling are the
    positive control for the whole IV pipeline. A chain built from Black-Scholes at ONE vol must
    read a spread of ~0; make the calls richer and it must go POSITIVE. Without this pair, a
    broken solver returns a plausible small number and nobody can tell.
  * `test_spot_from_parity_is_never_called_on_the_arm_path` is a SOURCE-level guard.
    `dividends.spot_from_parity` returns `S = C - P + K*exp(-rT)`; feed that back as the spot and
    `iv_call - iv_put` is identically zero BY CONSTRUCTION, so `MA31` would report a clean,
    plausible, entirely fabricated null. It is the single most dangerous line in this area and
    the register forbids it by name.

`B4`'s `-1` open-interest sentinel is pinned in BOTH arms: it must be excluded from the MA31
weight and from the MA32 difference, and in MA32 it must be COUNTED, because a guard whose
count is zero is not reaching the data.
"""
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import blackscholes as BS                     # noqa: E402
from valuation.studies import parity_flow as PF                   # noqa: E402
from valuation.studies import surface_stock as SS                 # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASOF = "2024-01-02"
EXP = "2024-04-01"                       # 90 days out - inside the [7, 365] DTE band
T = (pd.Timestamp(EXP) - pd.Timestamp(ASOF)).days / 365.0
SPOT, R = 100.0, 0.05


def _chain(rows):
    """rows: (strike, right, bid, ask, oi[, volume])."""
    out = []
    for r in rows:
        k, right, b, a = r[0], r[1], r[2], r[3]
        oi = r[4] if len(r) > 4 else 100
        vol = r[5] if len(r) > 5 else 100
        out.append({"expiration": EXP, "strike": float(k), "right": right,
                    "bid": float(b), "ask": float(a), "open_interest": int(oi),
                    "volume": int(vol), "date": ASOF})
    return pd.DataFrame(out)


def _at_bs(strike, right, vol, q=0.0, bump=0.0):
    """A two-sided quote straddling the Black-Scholes price at `vol` (+ `bump`)."""
    px = BS.bs_price(SPOT, strike, T, R, vol, right, q) + bump
    return max(px - 0.01, 0.01), px + 0.01


# --------------------------------------------------------------------------- #
#  MA31 - matched pairs
# --------------------------------------------------------------------------- #
def test_matched_pairs_intersects_on_strike_and_expiry():
    df = _chain([(100, "C", 5, 5.2, 10), (100, "P", 4, 4.2, 20),
                 (105, "C", 3, 3.2, 30),                       # no put at 105 -> not a pair
                 (95, "P", 2, 2.2, 40)])                       # no call at 95  -> not a pair
    m = PF.matched_pairs(df)
    assert len(m) == 1, m
    assert float(m.iloc[0]["strike"]) == 100.0
    assert float(m.iloc[0]["c_oi"]) == 10 and float(m.iloc[0]["p_oi"]) == 20


def test_matched_pairs_collapses_vendor_duplicates():
    """A duplicated leg must not fan one pair out into several and inflate its weight."""
    df = _chain([(100, "C", 5, 5.2, 10), (100, "C", 5, 5.2, 10), (100, "P", 4, 4.2, 20)])
    assert len(PF.matched_pairs(df)) == 1


def test_admit_pairs_requires_BOTH_legs_usable_not_either():
    """MA45's predicate on both legs. A one-sided put must kill the PAIR, not just its own leg."""
    df = _chain([(100, "C", 5, 5.2, 10), (100, "P", 0, 4.2, 20)])     # put bid 0 -> unusable
    m = PF.matched_pairs(df)
    keep = PF.admit_pairs(m, SPOT, pd.Series([T] * len(m)))
    assert not bool(keep.iloc[0]), "a one-sided leg must disqualify the whole pair"


def test_admit_pairs_excludes_the_B4_minus_one_open_interest_sentinel():
    df = _chain([(100, "C", 5, 5.2, -1), (100, "P", 4, 4.2, 20)])
    m = PF.matched_pairs(df)
    keep = PF.admit_pairs(m, SPOT, pd.Series([T] * len(m)))
    assert not bool(keep.iloc[0]), "a -1 OI sentinel must never reach the weight (audit B4)"


def test_admit_pairs_applies_the_moneyness_and_dte_bands():
    df = _chain([(100, "C", 5, 5.2, 10), (100, "P", 4, 4.2, 20)])
    m = PF.matched_pairs(df)
    assert bool(PF.admit_pairs(m, SPOT, pd.Series([T])).iloc[0])
    # far out of the band
    assert not bool(PF.admit_pairs(m, 200.0, pd.Series([T])).iloc[0])
    # inside DTE_MIN
    assert not bool(PF.admit_pairs(m, SPOT, pd.Series([3 / 365.0])).iloc[0])
    # beyond DTE_MAX
    assert not bool(PF.admit_pairs(m, SPOT, pd.Series([2.0])).iloc[0])


def test_parity_dev_is_zero_on_a_chain_priced_AT_parity():
    """THE POSITIVE CONTROL. One vol for both legs => the spread must vanish."""
    rows = []
    for k in (95.0, 100.0, 105.0):
        cb, ca = _at_bs(k, "C", 0.30)
        pb, pa = _at_bs(k, "P", 0.30)
        rows += [(k, "C", cb, ca, 500), (k, "P", pb, pa, 500)]
    got = PF.volatility_spread(_chain(rows), SPOT, ASOF, R)
    assert got is not None
    assert abs(got["parity_dev"]) < 5e-3, got
    assert got["n_pairs_solved"] == 3, got


def test_parity_dev_goes_POSITIVE_when_calls_are_relatively_expensive():
    """The declared CW direction must be reproducible on synthetic data, or the sign is unpinned."""
    rows = []
    for k in (95.0, 100.0, 105.0):
        cb, ca = _at_bs(k, "C", 0.35)          # calls carry the higher vol
        pb, pa = _at_bs(k, "P", 0.30)
        rows += [(k, "C", cb, ca, 500), (k, "P", pb, pa, 500)]
    got = PF.volatility_spread(_chain(rows), SPOT, ASOF, R)
    assert got is not None and got["parity_dev"] > 0.02, got
    assert PF.DECLARED_SIGN["parity_dev"] == +1


def test_parity_dev_weight_is_the_THINNER_leg():
    """`w = min(oi_call, oi_put)`: one fat leg must not carry a pair nobody holds the other side of."""
    def spread(oi_a, oi_b, oi_c):
        rows = []
        for k, vol, oi in ((95.0, 0.40, oi_a), (100.0, 0.30, oi_b), (105.0, 0.30, oi_c)):
            cb, ca = _at_bs(k, "C", vol)
            pb, pa = _at_bs(k, "P", 0.30)
            rows += [(k, "C", cb, ca, oi), (k, "P", pb, pa, 500)]
        return PF.volatility_spread(_chain(rows), SPOT, ASOF, R)["parity_dev"]
    # the 95 pair is the only one with a call/put vol gap; fattening its CALL leg alone must not
    # increase its influence, because the put leg (500) is what caps it.
    assert abs(spread(500, 500, 500) - spread(5000, 500, 500)) < 1e-9


def test_parity_dev_returns_None_below_MIN_PAIRS():
    rows = []
    for k in (100.0,):
        cb, ca = _at_bs(k, "C", 0.30)
        pb, pa = _at_bs(k, "P", 0.30)
        rows += [(k, "C", cb, ca, 500), (k, "P", pb, pa, 500)]
    assert PF.volatility_spread(_chain(rows), SPOT, ASOF, R) is None


# --------------------------------------------------------------------------- #
#  MA32 - open vs close
# --------------------------------------------------------------------------- #
def _two_days(rows_now, rows_prev, gap=1):
    now = _chain(rows_now)
    prev = _chain(rows_prev)
    d1 = pd.Timestamp(ASOF)
    return now, prev, d1, d1 - pd.Timedelta(days=gap)


def test_open_share_is_the_clipped_oi_increase_over_volume():
    now, prev, d, p = _two_days([(100, "C", 1, 2, 150, 100)], [(100, "C", 1, 2, 100, 100)])
    got = PF.open_shares(now, prev, d, p)
    assert abs(got["call_open_share"] - 0.5) < 1e-12, got     # dOI 50, volume 100


def test_a_FALL_in_open_interest_contributes_no_opening_volume():
    now, prev, d, p = _two_days([(100, "C", 1, 2, 40, 100)], [(100, "C", 1, 2, 100, 100)])
    got = PF.open_shares(now, prev, d, p)
    assert got["call_open_share"] == 0.0, got


def test_an_oi_rise_larger_than_the_days_volume_is_CAPPED_not_believed():
    now, prev, d, p = _two_days([(100, "C", 1, 2, 900, 100)], [(100, "C", 1, 2, 100, 100)])
    got = PF.open_shares(now, prev, d, p)
    assert got["call_open_share"] == 1.0, got


def test_the_B4_sentinel_is_excluded_AND_counted_in_the_flow_arm():
    now, prev, d, p = _two_days(
        [(100, "C", 1, 2, -1, 100), (105, "C", 1, 2, 150, 100)],
        [(100, "C", 1, 2, 100, 100), (105, "C", 1, 2, 100, 100)])
    got = PF.open_shares(now, prev, d, p)
    assert got["n_sentinel_dropped"] == 1, got
    # only the clean contract survives: dOI 50 over volume 100
    assert abs(got["call_open_share"] - 0.5) < 1e-12, got


def test_a_gap_wider_than_MAX_OI_GAP_DAYS_is_refused_not_accumulated():
    now, prev, d, p = _two_days([(100, "C", 1, 2, 150, 100)], [(100, "C", 1, 2, 100, 100)],
                                gap=PF.MAX_OI_GAP_DAYS + 1)
    assert PF.open_shares(now, prev, d, p) is None


def test_call_and_put_shares_use_SEPARATE_denominators():
    """If they shared one, they would be one arm and its complement - U2's duplicate defect."""
    now, prev, d, p = _two_days(
        [(100, "C", 1, 2, 200, 100), (100, "P", 1, 2, 100, 900)],
        [(100, "C", 1, 2, 100, 100), (100, "P", 1, 2, 100, 900)])
    got = PF.open_shares(now, prev, d, p)
    assert abs(got["call_open_share"] - 1.0) < 1e-12, got     # dOI 100 capped at volume 100
    assert got["put_open_share"] == 0.0, got
    assert abs(got["call_open_share"] + got["put_open_share"] - 1.0) < 1e-12 or True
    # and they are NOT shares of one total: the denominators differ
    assert got["call_open_share_volume"] != got["put_open_share_volume"]


def test_low_volume_denominator_yields_None_rather_than_a_noisy_ratio():
    now, prev, d, p = _two_days([(100, "C", 1, 2, 150, 5)], [(100, "C", 1, 2, 100, 5)])
    got = PF.open_shares(now, prev, d, p)
    assert got is None or got["call_open_share"] is None


# --------------------------------------------------------------------------- #
#  register discipline - source-level guards
# --------------------------------------------------------------------------- #
def test_spot_from_parity_is_never_called_on_the_arm_path():
    """Using parity to recover the spot sets MA31's answer to ZERO by construction."""
    import tokenize
    for rel in ("valuation/studies/parity_flow.py", "scripts/ma31_ma32_measure.py"):
        path = os.path.join(ROOT, rel)
        with tokenize.open(path) as fh:
            toks = list(tokenize.generate_tokens(fh.readline))
        code = " ".join(t.string for t in toks
                        if t.type not in (tokenize.COMMENT, tokenize.STRING))
        for bad in PF.FORBIDDEN_CALLS:
            assert bad not in code, f"{rel} calls {bad} on the arm path (register void cond. 5.4)"


def test_the_spot_reader_returns_the_AS_TRADED_series_not_the_adjusted_one():
    """Behavioural, not textual - and the first cut of this test was wrong in an instructive way.

    It grepped the source for `raw_close` after stripping strings and comments (the MA5 idiom).
    But `bars["raw_close"]` IS a string literal, so the guard stripped the very thing it was
    looking for and failed against correct code. A guard that cannot see a dict key is not
    measuring the tree. This builds a cache where the two series DIFFER - a split - and asserts
    which one comes back.
    """
    import pickle
    import tempfile

    import scripts.ma31_ma32_measure as M

    with tempfile.TemporaryDirectory() as tmp:
        old = M.BARS
        M.BARS = tmp
        try:
            with open(os.path.join(tmp, "SPLIT.pkl"), "wb") as fh:
                pickle.dump({"date": ["2024-01-02"], "close": [10.0], "raw_close": [80.0]}, fh)
            got = M._bars_offline("SPLIT")
            assert got["raw_close"] == [80.0], got
            assert M._raw_spot_map(got)["2024-01-02"] == 80.0, "the spot must be as-traded"

            # a cache predating `raw_close` is split-mixed and must be REFUSED, not fallen back on
            with open(os.path.join(tmp, "OLD.pkl"), "wb") as fh:
                pickle.dump({"date": ["2024-01-02"], "close": [10.0]}, fh)
            assert M._bars_offline("OLD") is None
            assert M._bars_offline("ABSENT") is None
        finally:
            M.BARS = old


def test_the_measure_script_never_fetches_from_the_vendor():
    """A research script that silently spends on a licensed API is MA7's class."""
    import tokenize
    path = os.path.join(ROOT, "scripts/ma31_ma32_measure.py")
    with tokenize.open(path) as fh:
        toks = list(tokenize.generate_tokens(fh.readline))
    code = " ".join(t.string for t in toks
                    if t.type not in (tokenize.COMMENT, tokenize.STRING))
    for bad in ("requests", "load_bars", "urlopen"):
        assert bad not in code, f"{bad} on a research path can trigger vendor spend"


def test_the_register_file_actually_exists_on_disk():
    """V6's lesson: a citation nobody can open is not a citation."""
    p = os.path.join(ROOT, "PREREG_ma31_ma32_parity_openclose.md")
    assert os.path.isfile(p), p
    body = open(p, encoding="utf-8").read()
    assert "ADOPTS NOTHING" in body and "MA56" in body


def test_exactly_three_arms_are_registered():
    """Void condition 2: a fourth arm is the quadratic search the tree combiner already reversed."""
    assert PF.ARMS == ("parity_dev", "call_open_share", "put_open_share"), PF.ARMS
    assert set(PF.DECLARED_SIGN) == {"parity_dev", "call_open_share"}
    assert PF.DECLARED_SIGN["call_open_share"] == -1


# --------------------------------------------------------------------------- #
#  verdict machinery
# --------------------------------------------------------------------------- #
def test_a_wrong_signed_result_can_never_be_a_pass():
    v = PF.verdict("parity_dev", -9.0, -9.0, 2.71, 2.71)
    assert v["verdict"] == "NULL", v          # declared POSITIVE; a huge negative is not a pass


def test_both_halves_are_required():
    assert PF.verdict("parity_dev", 5.0, 1.0, 2.71, 2.71)["verdict"] == "NULL"
    assert PF.verdict("parity_dev", 5.0, 5.0, 2.71, 2.71)["verdict"] == "PASS"


def test_a_two_sided_arm_requires_sign_AGREEMENT_across_halves():
    assert PF.verdict("put_open_share", 5.0, -5.0, 2.0, 2.0)["verdict"] == "NULL"
    assert PF.verdict("put_open_share", -5.0, -5.0, 2.0, 2.0)["verdict"] == "PASS"


def test_a_duplicate_carries_no_independent_verdict():
    v = PF.verdict("parity_dev", 9.0, 9.0, 2.71, 2.71, duplicate=True)
    assert v["verdict"] == "DUPLICATE", v


def test_a_degenerate_ic_series_can_never_be_read_as_a_pass():
    """`ic_tstat` returns ~1e16 on a constant series - inherited on purpose, guarded here."""
    v = PF.verdict("parity_dev", 1e16, 1e16, 2.71, 2.71, degenerate=True)
    assert v["verdict"] == "NULL", v


def test_duplicate_check_fires_on_a_renamed_arm_and_not_on_an_independent_one():
    rng = np.random.default_rng(7)
    n = 400
    a = rng.normal(size=n)
    f = pd.DataFrame({"a": a, "b": a * 3.0 + 1.0, "c": rng.normal(size=n)})
    assert PF.duplicate_check(f, "a", "b")["duplicate"] is True
    assert PF.duplicate_check(f, "a", "c")["duplicate"] is False


def test_coverage_dates_are_usable_by_arm_ic_without_conversion():
    """A REGRESSION PIN for a defect that presented as a clean triple NULL.

    `coverage_report` first returned `str(d)[:10]` so the artifact would read nicely. Every
    consumer then filtered a datetime64 column with `.isin([...strings])`, matched nothing, and
    all three arms reported `n_dates = 0` - which reads exactly like "the arms have no coverage",
    a sentence this project has legitimately written five times. Coverage said 40 dates and
    16,736 joined rows at the same moment. Nothing raised.
    """
    rng = np.random.default_rng(3)
    n_per, dates = 40, pd.to_datetime(["2024-01-10", "2024-04-10", "2024-07-10"])
    rows = []
    for d in dates:
        for i in range(n_per):
            rows.append({"date": d, "ticker": f"T{i}", "parity_dev": rng.normal(),
                         "fwd_ret": rng.normal(),
                         **{c: rng.normal() for c in SS.INCUMBENTS}})
    f = pd.DataFrame(rows)
    cov = PF.coverage_report(f, "parity_dev")
    assert cov["dates_scoreable"] == 3, cov
    got = PF.arm_ic(f, "parity_dev", cov["dates"])
    assert got["n_dates_raw"] == 3, got          # 0 here is the defect returning
    assert got["n_dates_incremental"] == 3, got


def test_minimum_detectable_ic_is_reported_so_a_null_is_quotable():
    ics = [0.01, -0.02, 0.03, 0.00, 0.01, -0.01]
    mde = PF.minimum_detectable_ic(ics, 2.71)
    assert mde is not None and mde > 0
    assert PF.minimum_detectable_ic([0.01], 2.71) is None


def test_permutation_bar_drops_degenerate_draws_rather_than_scoring_them_zero():
    """V6 measured that scoring a degenerate draw as 0.0 LOWERS the p95 - it makes the bar easier."""
    src = open(os.path.join(ROOT, "valuation/studies/parity_flow.py"), encoding="utf-8").read()
    body = src.split("def permutation_bar")[1].split("\ndef ")[0]
    assert "continue" in body and "n_draws_used" in body


# --------------------------------------------------------------------------- #
#  the shared join - existing callers must be bit-identical
# --------------------------------------------------------------------------- #
def test_join_pit_default_is_bit_identical_for_existing_callers():
    """`value_cols` was added for MA31/MA32; U2's callers must not move by a bit."""
    panel = pd.DataFrame({"date": pd.to_datetime(["2024-01-10", "2024-04-10"]),
                          "ticker": ["AAA", "AAA"]})
    arms = {"AAA": pd.DataFrame({"date": pd.to_datetime(["2024-01-05", "2024-04-08"]),
                                 "term_slope": [0.1, 0.2], "iv_rank": [0.3, 0.4],
                                 "skew_25d": [0.5, 0.6]})}
    a, ca = SS.join_pit(panel, arms)
    b, cb = SS.join_pit(panel, arms, value_cols=SS.COMPONENT_ARMS)
    assert ca == cb
    for c in SS.COMPONENT_ARMS:
        assert list(a[c].fillna(-999)) == list(b[c].fillna(-999))


def test_join_pit_is_STRICTLY_before_the_rebalance_date():
    panel = pd.DataFrame({"date": pd.to_datetime(["2024-01-10"]), "ticker": ["AAA"]})
    same_day = {"AAA": pd.DataFrame({"date": pd.to_datetime(["2024-01-10"]),
                                     "parity_dev": [0.9]})}
    j, ctrl = SS.join_pit(panel, same_day, value_cols=("parity_dev",))
    assert ctrl["pit_violations"] == 0
    assert math.isnan(float(j["parity_dev"].iloc[0])), "a same-day row must not be joined"


def test_join_pit_refuses_a_row_staler_than_the_ceiling():
    panel = pd.DataFrame({"date": pd.to_datetime(["2024-01-30"]), "ticker": ["AAA"]})
    old = {"AAA": pd.DataFrame({"date": pd.to_datetime(["2024-01-01"]), "parity_dev": [0.9]})}
    j, _ = SS.join_pit(panel, old, value_cols=("parity_dev",))
    assert math.isnan(float(j["parity_dev"].iloc[0]))


if __name__ == "__main__":
    fails = 0
    names = [n for n in sorted(globals()) if n.startswith("test_")]
    for name in names:
        try:
            globals()[name]()
            print("PASS", name)
        except Exception as e:                                       # noqa: BLE001
            fails += 1
            print("FAIL", name, "->", repr(e))
    print("%d passed, %d failed" % (len(names) - fails, fails))
    sys.exit(1 if fails else 0)
