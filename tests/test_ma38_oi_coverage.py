"""AUDIT MA38 - the OI-coverage fraction B4 computed had no consumer, so the "unusual call
volume vs OI" bonus rested on a number nothing validated.

Run: python tests/test_ma38_oi_coverage.py

THE DEFECT. `chain_summary` sums `call_volume` over EVERY contract in the front expiry and
`call_oi` over only those whose open interest is KNOWN (B4 made it exclude the -1 the ThetaData
cache writes when the OI call failed, which was correct). `options_signals` then forms
`call_volume / call_oi > 0.5`, dividing a whole-chain numerator by a partial denominator, so on a
partially-covered chain the ratio is inflated by roughly 1/coverage and the bonus fires where the
module's own docstring says the reconstruction cannot ("STRICTER ... fires fewer, never more").

WHY IT IS NOT ALREADY CAUGHT by the shipped `coi > 0` guard: measured on 11,818 front-expiry
chain-days across 12 cached symbols, coverage is NOT all-or-nothing - 72.6% of days are fully
covered, 0.04% are empty, and 27.3% are PARTIAL. On an empty day `coi` is 0 and the guard does
block the bonus; on a partial day it does not.

THE REPAIR is to take both sums over the SAME rows. The audit proposed two alternatives and both
were measured to be far more disruptive than the defect they repair - scaling `coi` by
1/coverage kills 262 otherwise-legitimate fires against a 5-day defect (52x), and suppressing
below 0.9 coverage kills 660 (132x) - because volume is concentrated in the known-OI rows.
So no threshold is introduced, and `test_no_coverage_threshold_was_introduced` pins that.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.intraday.options import options_signals          # noqa: E402
from valuation.edge.options_backtest import chain_summary       # noqa: E402

BONUS = "Unusual call volume vs OI"


def _chain(rows):
    """rows: (right, strike, expiration, volume, open_interest) -> the DataFrame chain_summary eats."""
    import pandas as pd
    return pd.DataFrame([{"right": r, "strike": k, "expiration": e, "volume": v,
                          "open_interest": oi, "bid": 1.0, "ask": 1.2} for r, k, e, v, oi in rows])


# ----------------------------------------------------------------- the defect itself
def test_the_defect_a_partially_covered_chain_fired_the_bonus_on_a_mismatched_ratio():
    """Whole-chain volume over known-only OI clears 0.5; the like-for-like ratio does not."""
    # 2 known-OI contracts (volume 30 total, OI 100) + 2 unknown-OI contracts carrying volume 90.
    # whole-chain: 120/100 = 1.20  -> fires.   matched: 30/100 = 0.30 -> must not.
    opt = {"call_volume": 120.0, "call_oi": 100.0, "call_oi_known_frac": 0.5,
           "call_volume_oi_known": 30.0, "put_volume": 10.0, "put_oi": 100.0}
    assert 120.0 / 100.0 > 0.5 and 30.0 / 100.0 <= 0.5          # the setup is the defect
    out = options_signals(opt)
    assert BONUS not in out["labels"], "the bonus fired on a mismatched ratio"

    # ...and it DID fire before the repair, i.e. this test is not vacuous.
    before = dict(opt); before.pop("call_volume_oi_known")
    assert BONUS in options_signals(before)["labels"]


def test_the_bonus_still_fires_when_the_matched_ratio_genuinely_clears():
    """The repair must not simply delete the signal - a real burst still scores."""
    opt = {"call_volume": 900.0, "call_oi": 100.0, "call_oi_known_frac": 0.5,
           "call_volume_oi_known": 80.0, "put_volume": 10.0, "put_oi": 100.0}
    out = options_signals(opt)
    assert BONUS in out["labels"]
    assert out["score"] > 50.0


# ----------------------------------------------------------------- the live path is untouched
def test_the_live_path_is_bit_identical_because_it_ships_no_coverage_figure():
    """Tradier sends no `call_volume_oi_known`, so the fallback must be the old numerator.

    This is the whole reason the fix is scoped to the reconstruction: changing which alerts the
    LIVE engine fires would be a construction change, not a bug fix.
    """
    live = {"put_volume": 100.0, "call_volume": 400.0, "put_oi": 1000.0, "call_oi": 500.0,
            "atm_iv": 0.35}
    assert "call_volume_oi_known" not in live
    out = options_signals(live)
    assert BONUS in out["labels"]                     # 400/500 = 0.8 > 0.5, exactly as before
    assert out["detail"]["oi_ratio_basis"] == "whole_chain"

    quiet = dict(live, call_volume=100.0)             # 100/500 = 0.2
    assert BONUS not in options_signals(quiet)["labels"]


def test_zero_coverage_is_still_blocked_by_the_existing_guard():
    """coi == 0 must not fire, and must not divide by zero, on either basis."""
    for extra in ({}, {"call_volume_oi_known": 0.0, "call_oi_known_frac": 0.0}):
        opt = dict({"call_volume": 500.0, "call_oi": 0.0, "put_volume": 1.0, "put_oi": 10.0}, **extra)
        out = options_signals(opt)
        assert BONUS not in out["labels"]


# ----------------------------------------------------------------- the producer
def test_chain_summary_matched_volume_covers_exactly_the_known_oi_rows():
    import datetime as dt
    exp = dt.date(2020, 2, 21)
    ch = _chain([("C", 100.0, exp, 10.0, 50.0),      # known
                 ("C", 105.0, exp, 20.0, 70.0),      # known
                 ("C", 110.0, exp, 90.0, -1.0),      # OI UNKNOWN, and it carries most of the volume
                 ("P", 100.0, exp, 5.0, 40.0)])
    s = chain_summary(ch, 102.0, dt.date(2020, 1, 2))
    assert s["call_volume"] == 120.0                  # whole chain, unchanged (the P/C ratio wants it)
    assert s["call_volume_oi_known"] == 30.0          # ...and the matched sum excludes the -1 row
    assert s["call_oi"] == 120.0                      # B4: the -1 is never counted
    assert abs(s["call_oi_known_frac"] - (2.0 / 3.0)) < 1e-12


def test_at_full_coverage_the_matched_volume_equals_the_whole_chain_volume():
    """With nothing missing the repair is a no-op, which is what makes it safe to apply always."""
    import datetime as dt
    exp = dt.date(2020, 2, 21)
    ch = _chain([("C", 100.0, exp, 10.0, 50.0), ("C", 105.0, exp, 20.0, 70.0),
                 ("P", 100.0, exp, 5.0, 40.0)])
    s = chain_summary(ch, 102.0, dt.date(2020, 1, 2))
    assert s["call_oi_known_frac"] == 1.0
    assert s["call_volume_oi_known"] == s["call_volume"]
    assert s["put_volume_oi_known"] == s["put_volume"]


def test_the_producer_and_the_consumer_agree_end_to_end():
    """The real coupling: chain_summary's dict, fed straight to options_signals."""
    import datetime as dt
    exp = dt.date(2020, 2, 21)
    ch = _chain([("C", 100.0, exp, 5.0, 100.0),       # known: matched ratio 5/100 = 0.05
                 ("C", 110.0, exp, 400.0, -1.0),      # unknown, huge volume -> whole-chain 4.05
                 ("P", 100.0, exp, 5.0, 40.0)])
    s = chain_summary(ch, 102.0, dt.date(2020, 1, 2))
    assert s["call_volume"] / s["call_oi"] > 0.5      # the old ratio would have fired
    assert BONUS not in options_signals(s)["labels"]  # the matched one does not
    assert options_signals(s)["detail"]["oi_ratio_basis"] == "matched"


# ----------------------------------------------------------------- MA38's actual subject
def test_the_coverage_fraction_now_reaches_a_consumer():
    """MA38 is "ships a fraction no consumer reads". A field only ever written is the defect."""
    import datetime as dt
    exp = dt.date(2020, 2, 21)
    ch = _chain([("C", 100.0, exp, 10.0, 50.0), ("C", 110.0, exp, 20.0, -1.0),
                 ("P", 100.0, exp, 5.0, 40.0)])
    d = options_signals(chain_summary(ch, 102.0, dt.date(2020, 1, 2)))["detail"]
    assert d["call_oi_known_frac"] == 0.5
    assert d["put_oi_known_frac"] == 1.0
    # and it degrades to None rather than lying when the producer cannot say
    assert options_signals({"call_volume": 1.0, "call_oi": 1.0})["detail"]["call_oi_known_frac"] is None


def test_no_coverage_threshold_was_introduced():
    """A source-level pin, because the audit's own option (b) is a 0.9 bar nobody calibrated.

    Measured, it would kill 660 legitimate fires against a 5-day defect. If a future session
    decides to add one anyway that is a decision to argue for, not to slip in - this test makes
    it visible in the diff.
    """
    import re
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "intraday", "options.py"), encoding="utf-8").read()
    code = "\n".join(l for l in src.split("\n") if not l.strip().startswith("#"))
    # the only bare numeric literals the scorer may compare against are the shipped ones
    lits = set(re.findall(r"[<>]=?\s*(0\.\d+)", code))
    assert lits <= {"0.5", "0.7", "0.6", "0.2"}, "a new numeric bar appeared in the scorer: %s" % lits
    assert "known_frac" in code, "the coverage figure must be read by the consumer"


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
    print("%d passed, %d failed" % (sum(1 for n in globals() if n.startswith("test_")) - fails, fails))
    sys.exit(1 if fails else 0)
