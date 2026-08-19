"""AUDIT MA44 - live and reconstruction disagree on the front expiry, and the docstring said
they matched.

Run: python tests/test_ma44_front_expiry.py

THE DEFECT. Four sites choose a "front expiry" and they implement TWO rules:

  * `intraday.providers.TradierProvider.get_option_summary` - `dl[0]`, no date filter
  * `intraday.providers.FreeProvider.get_option_summary`    - `exps[0]`, no date filter
  * `edge.options_backtest.chain_summary`                   - strictly after `as_of`
  * `edge.options_live.term_read`                           - strictly after `as_of`

so on a day when the venue lists a same-day expiry, the live scan's OWN legs disagree: volume,
OI and `atm_iv` come from the dying chain while `term_slope` comes from the next one. Measured on
19,825 cached chain-days across 39 names: 12.46% list a same-day expiry alongside a future one -
60.2% of Fridays - and on 23.14% of those the 0.5 volume-vs-OI bar is crossed by one side only.

WHAT IS PINNED HERE, and what deliberately is not. Whether Tradier really lists today on an
expiry day is a live vendor behaviour this repository cannot observe; it stays the audit's
HYPOTHESIS. So the default is pinned BIT-IDENTICAL, the other rule is pinned as reachable and
testable via `include_expiring`, and both paths are pinned to REPORT the expiry they used. The
false parity claim is pinned OUT of the docstring so it cannot come back.
"""
import inspect
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge.options_backtest import chain_summary        # noqa: E402

TODAY = "2026-08-14"          # a Friday
NEXT = "2026-08-21"


def _chain(expirations):
    """A two-sided chain listing each expiry, so only the expiry choice can move an answer."""
    import pandas as pd
    rows = []
    for e, vol, oi in expirations:
        for right in ("C", "P"):
            for k in (95.0, 100.0, 105.0):
                rows.append({"right": right, "strike": k, "expiration": e, "volume": vol,
                             "open_interest": oi, "bid": 1.0, "ask": 1.2})
    return pd.DataFrame(rows)


def test_the_two_rules_read_different_chains_on_a_same_day_expiry():
    """The defect itself: one chain, two rules, two different answers."""
    ch = _chain([(TODAY, 500, 10), (NEXT, 7, 900)])
    recon = chain_summary(ch, 100.0, TODAY)
    live = chain_summary(ch, 100.0, TODAY, include_expiring=True)
    assert recon["front_expiry"] == NEXT, recon["front_expiry"]
    assert live["front_expiry"] == TODAY, live["front_expiry"]
    # and they are not cosmetically different - the alert's own inputs move
    assert recon["call_volume"] != live["call_volume"]
    assert recon["call_oi"] != live["call_oi"]


def test_the_default_is_unchanged_so_no_banked_result_moves():
    """`include_expiring` defaults False = the strictly-after rule this function always used."""
    ch = _chain([(TODAY, 500, 10), (NEXT, 7, 900)])
    a = chain_summary(ch, 100.0, TODAY)
    b = chain_summary(ch, 100.0, TODAY, include_expiring=False)
    for k in ("call_volume", "put_volume", "call_oi", "put_oi", "atm_iv"):
        assert a[k] == b[k], k
    assert a["front_expiry"] == NEXT
    # the parameter is opt-in, not merely defaulted somewhere else
    assert inspect.signature(chain_summary).parameters["include_expiring"].default is False


def test_the_disclosure_reports_the_expiry_used_and_whether_one_was_skipped():
    ch = _chain([(TODAY, 500, 10), (NEXT, 7, 900)])
    s = chain_summary(ch, 100.0, TODAY)
    assert s["front_expiry"] == NEXT
    assert s["expiring_listed"] is True, "a same-day expiry WAS on the board and was skipped"
    # and on an ordinary day the flag is False rather than absent
    ch2 = _chain([(NEXT, 7, 900)])
    s2 = chain_summary(ch2, 100.0, TODAY)
    assert s2["expiring_listed"] is False
    assert s2["front_expiry"] == NEXT


def test_an_expiring_only_chain_still_returns_nothing_by_default():
    """Not a silent fallback: with only a same-day expiry the default rule has no chain to read.

    This is the behaviour that existed before, and it is pinned because 'helpfully' falling back
    to the expiring chain would be the construction change this repair refuses to make.
    """
    ch = _chain([(TODAY, 500, 10)])
    assert chain_summary(ch, 100.0, TODAY) is None
    assert chain_summary(ch, 100.0, TODAY, include_expiring=True) is not None


def test_the_docstring_no_longer_claims_a_parity_that_does_not_hold():
    """The confirmed defect was a FALSE CLAIM; pin it out so it cannot be restored."""
    doc = chain_summary.__doc__ or ""
    assert "matching the live provider" not in doc, "the false parity claim is back"
    assert "MA44" in doc
    # it must still say what rule it DOES use, not merely delete the wrong sentence
    assert "STRICTLY AFTER" in doc.upper()


def test_both_live_providers_now_report_which_expiry_they_read():
    """Source-level: nothing consumed `expiry` before, so the divergence was unobservable live."""
    import valuation.intraday.providers as P
    src = inspect.getsource(P)
    assert src.count("\"front_expiry\"") >= 2, "both live providers must disclose it"
    # and the rule itself is untouched - reporting is not changing
    assert "expiry = dl[0]" in src, "the live rule must NOT have been silently changed"
    assert "exps[0]" in src


def test_the_two_strictly_after_sites_still_agree_with_each_other():
    """`term_read` is the other strictly-after site and the one the threshold was fitted on."""
    import valuation.edge.options_live as OL
    src = inspect.getsource(OL.term_read)
    assert "> asof" in src, "term_read must still take the first STRICTLY LATER expiry"


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
