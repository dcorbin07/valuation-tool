"""MC14 / D8 — MISSING OPEN INTEREST IS UNKNOWN ON THE LIVE PATH TOO, NOT ZERO.

**WHAT WAS WRONG, IN TWO PLACES.** `intraday/providers.py` summed open interest with
`(o.get("open_interest") or 0)` on the Tradier leg and `["openInterest"].fillna(0)` on the
yfinance leg — so a contract whose OI the venue did not return counted as **zero**, shrinking
the denominator of `options_signals`' `call_volume / call_oi > 0.5` bonus. MA38 fixed exactly
this in the BACKTEST and CLAUDE.md's own bullet records that both live producers still had it.

**THE DEFECT CAN ONLY EVER ADD AN ALERT**, which is why it survived: a too-small denominator
makes the ratio too big. MA38 measured 27 of 41,321 front-expiry chain-days (0.065%) crossed by
the mismatch alone and **zero the other way**.

**THE RULE IS ONE CODE OBJECT (`B7`).** `oi_and_matched_volume` was `chain_summary`'s nested
`_oi_sum`; it is now module-level and both live legs delegate to it. A second implementation for
the live shape is precisely how a live numerator and a banked one come to disagree — and the
extraction is proved INERT on the backtest rather than assumed.

**AND IT IS THE MATCHED NUMERATOR, NOT AN IMPUTATION.** MA38 measured both alternatives and
rejected them: scaling by `1/known_frac` kills 501 legitimate fires (18.6× the defect) and a
0.9 coverage floor kills 1,005 (37.2×), because volume is CONCENTRATED in the known-OI rows.
Dividing like by like costs nothing.

Run: python tests/test_mc14_live_oi.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_isolation   # noqa: E402,F401  — LA15: temp state only. Import BEFORE `valuation`.

from valuation.edge.options_backtest import oi_and_matched_volume as OIMV   # noqa: E402

PASSED = FAILED = 0


def check(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print("  ok   %s" % name)
    except Exception as e:                                               # noqa: BLE001
        FAILED += 1
        print("  FAIL %s\n         %s: %s" % (name, type(e).__name__, e))


# =======================================================================================
# THE RULE
# =======================================================================================
def test_missing_open_interest_is_unknown_rather_than_zero():
    """The whole point: an absent OI must not enter the sum as a count of nothing."""
    oi_sum, frac, vol = OIMV([100, None, 50], [10, 999, 20])
    assert oi_sum == 150.0, oi_sum
    assert abs(frac - 2.0 / 3.0) < 1e-12, frac
    # ...and the 999 volume on the unknown-OI row is EXCLUDED, which is the matched numerator.
    assert vol == 30.0, vol


def test_a_negative_sentinel_is_unknown_and_never_a_count():
    """`-1` is what the cache writes when the OI call failed (B4). Reading it as a count
    would be worse than reading it as zero."""
    oi_sum, frac, vol = OIMV([-1, 40], [5, 7])
    assert oi_sum == 40.0 and vol == 7.0, (oi_sum, vol)
    assert frac == 0.5, frac


def test_nan_is_unknown_too_which_is_the_yfinance_shape():
    nan = float("nan")
    oi_sum, frac, vol = OIMV([nan, 20], [3, 4])
    assert oi_sum == 20.0 and vol == 4.0, (oi_sum, vol)
    assert frac == 0.5


def test_full_coverage_is_the_plain_sum_so_the_fix_is_inert_where_nothing_is_missing():
    oi_sum, frac, vol = OIMV([10, 20, 30], [1, 2, 3])
    assert (oi_sum, frac, vol) == (60.0, 1.0, 6.0)


def test_an_empty_chain_reports_zero_coverage_rather_than_dividing_by_nothing():
    assert OIMV([], []) == (0.0, 0.0, 0.0)
    assert OIMV(None, None) == (0.0, 0.0, 0.0)


def test_it_accepts_a_pandas_series_and_a_plain_list_identically():
    """The backtest holds DataFrame columns, the live paths hold lists of dicts. One rule must
    serve both or the two numerators drift -- which is the defect being fixed."""
    import pandas as pd
    a = OIMV(pd.Series([100, None, 50]), pd.Series([10, 999, 20]))
    b = OIMV([100, None, 50], [10, 999, 20])
    assert a == b, (a, b)


# =======================================================================================
# THE LIVE PATHS — delegation, not a second copy
# =======================================================================================
def _code_only(path: str) -> str:
    """The file's CODE, with comments and string literals removed.

    **MY OWN BAN FIRED ON MY OWN COMMENT**, minutes after writing it: the fix's comment quotes
    the defective spelling it documents — *"This used to read `(o.get("open_interest") or 0)`"*
    — and a raw substring search cannot tell that from live code. The substring-ban family,
    which this repository has now paid for repeatedly, and the documented remedy is to strip
    prose before asserting about code.
    """
    import io as _io
    import tokenize
    out = []
    with open(path, "rb") as fh:
        for tok in tokenize.tokenize(fh.readline):
            if tok.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            out.append(tok.string)
    return " ".join(out)


def test_neither_live_path_sums_a_missing_open_interest_as_zero():
    """Read from the CODE, not the prose about the code."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "valuation", "intraday", "providers.py")
    code = _code_only(path)
    raw = open(path, encoding="utf-8").read()

    # The stripper is PROVED NON-VACUOUS in both directions, or a stripper returning "" would
    # make this guard pass by seeing nothing.
    assert "oi_and_matched_volume" in code, "the stripper removed live code"
    assert "This used to read" not in code, "the stripper did not remove comments"

    # `or 0` applied to an open-interest lookup, in CODE.
    flat = code.replace(" ", "")
    assert 'o.get("open_interest")or0' not in flat, (
        "the Tradier leg still sums a missing open interest as zero")
    assert '["openInterest"].fillna(0)'.replace(" ", "") not in flat, (
        "the yfinance leg still fills a missing open interest with zero")
    assert raw.count("oi_and_matched_volume") >= 2, (
        "both live legs must delegate to the shared rule")


def test_both_live_payloads_expose_the_coverage_and_the_matched_numerator():
    """`known_frac` had ONE producer and ZERO readers when MA38 found it; a figure nothing can
    read is how that defect survived a year."""
    src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "valuation", "intraday", "providers.py"), encoding="utf-8").read()
    for key in ("call_oi_known_frac", "put_oi_known_frac",
                "call_volume_oi_known", "put_volume_oi_known"):
        assert src.count('"%s"' % key) >= 2, (
            "%s is not on BOTH live payloads (found %d)" % (key, src.count('"%s"' % key)))


def test_the_rule_is_not_reimplemented_in_the_provider():
    """B7. The provider may CALL the rule; it may not carry its own copy."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "valuation", "intraday", "providers.py")
    flat = _code_only(path).replace(" ", "")
    # In CODE, not in the comment that documents the rule — see `_code_only`.
    assert 'o.get("open_interest")or0' not in flat, "a second copy of the zero-fill survives"
    assert "defoi_and_matched_volume" not in flat, "the rule was copied into the provider"


# =======================================================================================
# THE EXTRACTION IS INERT ON THE BACKTEST — proved, not assumed
# =======================================================================================
def test_the_extracted_rule_reproduces_the_nested_one_it_replaced():
    """`_oi_sum` was `chain_summary`'s nested helper. Moving it must change no banked number.

    The pre-extraction body is restated HERE, once, purely as the reference — that is
    legitimate for a differential control, and it is the only place a second copy may live.
    """
    import pandas as pd

    def _old(part_oi, part_vol):
        v = pd.to_numeric(part_oi, errors="coerce")
        v = v.where(v >= 0)
        vol = pd.to_numeric(part_vol, errors="coerce").fillna(0)
        known = v.notna()
        return (float(v.sum()),
                float(known.mean()) if len(v) else 0.0,
                float(vol[known].sum()))

    cases = [
        ([100, 200, 300], [1, 2, 3]),
        ([100, None, 300], [1, 2, 3]),
        ([-1, 200, None], [5, 6, 7]),
        ([float("nan"), 0, 50], [0, 9, 1]),
        ([0, 0, 0], [0, 0, 0]),
        ([7], [None]),
    ]
    worst = 0.0
    for oi, vol in cases:
        a = _old(pd.Series(oi, dtype="float64"), pd.Series(vol, dtype="float64"))
        b = OIMV(oi, vol)
        for x, y in zip(a, b):
            worst = max(worst, abs(x - y))
    assert worst == 0.0, "the extraction changed the arithmetic: max abs delta %r" % worst


def run():
    global PASSED, FAILED
    print("MC14 / D8 — LIVE OPEN INTEREST")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            check(name, fn)
    print("\n%d passed, %d failed" % (PASSED, FAILED))
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
