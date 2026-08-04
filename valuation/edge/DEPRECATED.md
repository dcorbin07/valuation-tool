# Deprecated modules — NOT part of any result

Nothing listed here is imported by the live product, the backtests, or the tests. It is
kept only so the project's history stays readable.

**Do not reason from anything in here about how the system behaves today.**

- `deprecated_options_exit.py` — a first-cut exit rule evaluated on the UNDERLYING (+/-1 sigma on the
  stock), written before real option price history existed. It has never contributed to a
  reported number. Quarantined by AUDIT B16, which flagged it as "the single most likely thing
  for a new session to mistake for the live exit logic." It IS exercised by
  tests/test_intraday.py, so the audit's "imported by nothing" is corrected: nothing in the
  PRODUCT imports it.

  **The live exit logic is the inline day-walk loop in `options_backtest.simulate_trade`.**
