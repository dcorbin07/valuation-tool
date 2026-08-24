# DECL testbook - THE DAY-1 SELF-VERIFICATION TEST-BOOK

**THIS IS NOT A RESEARCH BOOK AND IT CARRIES NO VERDICT.** It exists for one reason:
`DECL_CEREMONY_RUNBOOK.md` section 1 requires the harness to prove itself end to end
against the REAL Tradier sandbox before any real book declares - one real fill, an
append-only round-trip compared bit-identical, the tamper case RUN rather than assumed,
the refusals fired, and the `F-1` randomizer reproducing its assignment.

**It is CLOSED in the same session it is declared, with a zero-charge closing row.** It is
`utility` class and charges NO trial in any domain, so no meter is ever read on it and the
harness's one-trial-per-book rule is never engaged.

Sandbox only. Nothing here licenses real money.

```json
{
  "book": "testbook",
  "domain": "options",
  "hypothesis_class": "utility",
  "entry_rule": "THROWAWAY TEST-BOOK, not a research book. One order only: the nearest-ATM SPY call with 25-60 DTE carrying a two-sided quote at the moment the day-1 self-verification runs. It exists to prove the harness end to end against the real Tradier sandbox and is CLOSED in the same session.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "dte": [
      25,
      60
    ],
    "right": "call"
  },
  "universe": "SPY only",
  "sizing": "1 contract, once",
  "concurrency_cap": 1,
  "side": "long",
  "sells_premium": false,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 0,
    "min_effect": 999.0,
    "sigma": 1.0,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 1,
    "earliest_honest_read": "NEVER - this book carries no verdict and no meter is read"
  },
  "verdict_grammar": [
    "NO VERDICT - test-book, closed on the day it is declared"
  ],
  "trial": {
    "domain": "none",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
