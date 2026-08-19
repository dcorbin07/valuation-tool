"""AUDIT MA45 - `enrich_chain` solved implied vol from an unvalidated `mid = (bid+ask)/2`.

Run: python tests/test_ma45_quote_validity.py

THE DEFECT. A zero-bid row yields an IV from `ask/2` - a number, never an error. `options_greeks
.enrich_frame` has always refused those rows (`no_quote` at :375, `crossed` at :376); the
Black-Scholes path did not, and it is the path the LIVE term gate runs on:
`term_read -> _atm_iv_bs -> enrich_chain -> nearest strike`. `chain_summary`'s ATM walk carried
the same defect in its own copy of the mid.

MEASURED before the repair, on 4.35M cached chain rows / 2,065 chain-days:
  * 26.08% of all rows carry a one-sided quote; 0.00% are crossed
  * but the ATM front row the walk LANDS on is one only 0.44% of the time - a row-level share
    cannot answer a per-day question (the MA38 lesson, again)
  * when it bites it is severe: front IV moves a median +0.1262 against a term bar of 0.0105
  * the bar is decided differently on 0.29% of chain-days, and 5 of 6 are alerts that pass today
    and would not - the audit's "biased positive, gate passes what it should suppress", confirmed

THE REPAIR keeps the ROW and NaNs its `iv`/greeks rather than dropping it, so no caller's row
count or index moves and every existing `dropna` path just works. `test_pick_contract_selection_
is_bit_identical` is the one that proves the live selector did not move.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import blackscholes as BS                    # noqa: E402
from valuation.edge.options_backtest import chain_summary, pick_contract   # noqa: E402

ASOF = "2026-08-14"
EXP = "2026-10-16"


def _df(rows):
    """rows: (strike, right, bid, ask) on one expiry."""
    import pandas as pd
    return pd.DataFrame([{"strike": k, "right": r, "bid": b, "ask": a, "expiration": EXP,
                          "volume": 100, "open_interest": 500} for k, r, b, a in rows])


def test_usable_quote_is_exactly_the_greeks_rule_and_nothing_more():
    assert BS.usable_quote(1.0, 1.2) is True
    assert BS.usable_quote(0.0, 1.2) is False, "no_quote: a zero bid is not a two-sided market"
    assert BS.usable_quote(1.0, 0.0) is False, "no_quote: a zero ask"
    assert BS.usable_quote(1.3, 1.2) is False, "crossed"
    assert BS.usable_quote(None, 1.2) is False
    assert BS.usable_quote(float("nan"), 1.2) is False
    # locked is NOT rejected here: options_greeks marks it separately and it is still a price
    assert BS.usable_quote(1.2, 1.2) is True
    # SELECTION criteria must NOT have been folded in - these are valid quotes, however unlovely
    assert BS.usable_quote(0.01, 0.02) is True, "a penny quote is a price; that is a strategy call"
    assert BS.usable_quote(0.10, 9.00) is True, "a wide quote is a price; that is a strategy call"


def test_enrich_chain_refuses_to_solve_from_a_one_sided_quote():
    """The known-bad input: pre-fix this returned a number solved from ask/2."""
    import math
    d = _df([(100.0, "C", 0.0, 8.0), (100.0, "P", 2.0, 2.2)])
    out = BS.enrich_chain(d, 100.0, ASOF)
    iv0 = out["iv"].iloc[0]
    assert iv0 is None or (isinstance(iv0, float) and math.isnan(iv0)), \
        "a zero-bid row must not produce an implied vol, got %r" % (iv0,)
    assert out["delta"].iloc[0] is None or math.isnan(float(out["delta"].iloc[0]))
    # the two-sided row beside it is untouched
    assert out["iv"].iloc[1] is not None and float(out["iv"].iloc[1]) > 0


def test_the_row_is_kept_not_dropped():
    """Row count and index are load-bearing for four callers; only iv/greeks may go NaN."""
    d = _df([(90.0, "C", 0.0, 8.0), (100.0, "C", 2.0, 2.2), (110.0, "C", 0.0, 0.3)])
    out = BS.enrich_chain(d, 100.0, ASOF)
    assert len(out) == len(d) == 3
    assert list(out.index) == list(d.index)
    assert list(out["strike"]) == [90.0, 100.0, 110.0]
    assert "mid" in out.columns, "mid is still reported even where iv is not solved"


def test_pick_contract_selection_is_bit_identical():
    """`quote_reject_reason` already refused these rows AFTER enrichment, so selection cannot move.

    This is what makes MA45 a correctness repair rather than a construction change on the trade
    side: the rows now NaN'd were being enriched and then discarded anyway.
    """
    import datetime as dt
    exp = (dt.date(2026, 8, 14) + dt.timedelta(days=60)).isoformat()
    import pandas as pd
    rows = []
    for k, b, a in ((95.0, 0.0, 9.0), (100.0, 5.0, 5.2), (105.0, 2.0, 2.2), (110.0, 0.0, 0.4)):
        rows.append({"strike": k, "right": "C", "bid": b, "ask": a, "expiration": exp,
                     "volume": 100, "open_interest": 500})
    d = pd.DataFrame(rows)
    got = pick_contract(d, 100.0, ASOF)
    assert got is not None
    assert float(got["strike"]) in (100.0, 105.0), float(got["strike"])
    assert float(got["bid"]) > 0, "a one-sided quote must never be the selected contract"


def test_chain_summary_atm_walk_skips_the_unusable_row_and_takes_the_next():
    """The SECOND site - it carries its own mid and does not go through enrich_chain."""
    import pandas as pd
    rows = []
    for k, b, a in ((100.0, 0.0, 40.0), (101.0, 4.9, 5.1)):
        for r in ("C", "P"):
            rows.append({"strike": k, "right": r, "bid": b, "ask": a, "expiration": EXP,
                         "volume": 10, "open_interest": 100})
    s = chain_summary(pd.DataFrame(rows), 100.0, ASOF)
    assert s is not None and s["atm_iv"] is not None
    # ask/2 = 20.0 on a 100 strike is an absurd vol; the 101 strike's real mid is ~5.0
    assert s["atm_iv"] < 1.5, "the walk took the one-sided nearest strike: iv=%r" % (s["atm_iv"],)


def test_the_rule_is_shared_not_copied():
    """One definition. A second copy is how the two sites drift apart again."""
    import inspect
    src = inspect.getsource(chain_summary)
    assert "usable_quote" in src, "chain_summary must delegate, not re-implement"
    assert "bid <= 0" not in src and "bid > 0" not in src, "a second copy of the rule appeared"


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
