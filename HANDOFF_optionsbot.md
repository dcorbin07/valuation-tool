# HANDOFF — options-bot lane (C1, C2, C3, C4, C6, O8)

Owner: `options-bot lane`. Source: `VALQUO_EDGE_AUDIT.md` Part XIII (C1-C7) and Part IV (O8).
Scope: `options-bot/**` only. `valuation/**` untouched.

---

## 0. PRE-REGISTERED THRESHOLDS — written BEFORE any run

These are committed here first, in writing, and are not re-derived after seeing a number.

### O8 — index variance risk premium (SPY / QQQ / IWM put credit spreads)

Primary window **2018-01-01 to 2025-12-31**. Pre-2018 is reported separately and is
**not permitted to change the verdict** (Dew-Becker et al. 2025-17: the index VRP declined
in the 2020s, so a 1990s-2010s number is a different regime, not more evidence).

The verdict rests on **SPY** — the deepest and tightest index chain, and the one the VRP
literature is actually about. QQQ and IWM are reported as robustness, not as votes.

* **ADOPT** (i.e. proceed to O8's stage 2, porting the arm to real option chains) requires
  ALL FOUR on SPY over the primary window, default config (vol-scaled sizing ON, weekly
  expiries, 20-delta, $5 wide, 35 DTE):
  1. total return > 0
  2. **excess Sharpe >= 0.50** (a fat-left-tail premium-selling strategy has to clear cash
     by a real margin before real-chain work is worth paying for)
  3. no ruin halt
  4. COVID-crash window (2020-02-15 to 2020-04-30) return >= **-25%**
* **REJECT** if SPY total return <= 0, or excess Sharpe < 0, or the run halts for ruin.
* Anything in between is **INCONCLUSIVE** and gets reported as such, not rounded up.

### C1 — backtest the model that ships

The threshold is **the one already compiled into `screener/backtest_engine.py:summarize()`**,
chosen deliberately so it cannot be tuned after the fact — it predates this session:
`edge = (mean IC > 0 AND |IC t| >= 2.0) AND (in-sample mean IC > 0 AND out-of-sample mean IC > 0)
AND (top-minus-bottom quintile spread net of 8 bps/side > 0)`.

* **ADOPTED** = the LIVE model (`scoring.py`) clears that bar on the point-in-time panel.
* **REJECTED** = it does not.
* Reported alongside: the SAME statistic for the discarded inline 6-factor model, so the
  size of the C1 defect is quantified rather than asserted.
* If the live scorer cannot be replayed point-in-time at all, **that is the finding** and it
  is recorded as such (the audit's own instruction), not papered over.

### C2 — universe

No statistical threshold; this is a correctness item. The deliverable is a universe whose
**median market cap sits below the screener's own `MARKET_CAP_CEILING` ($10B)**, versus the
current one. Pass = median cap of the backtest universe < $10B and > 50% of names below the
ceiling. Reported with the before/after number.

### C3 — `--bots reversion`

Correctness item, no statistic. Pass = the flag can no longer accept an argument, run nothing,
and print success. Verified by an executable test.

### C4 — the tracking loop

Pass = (a) something calls `store.update_returns` on a schedule, (b) `run_review` refuses to
run on an all-NULL table, and (c) the guard is exercised by a test that fails against the old
code. Threshold for the review to run at all: **>= `SELF_REVIEW_MIN_SAMPLE` (40) rows with a
non-NULL realized return**, and non-NULL fraction >= 50% of rows whose horizon has closed.

### C6 — three undeployed fixes

Decision item. Pass = each of the three is in exactly one of two states — deployed, or deleted
and recorded — and none is left in the third state ("fixed in repo, not deployed").

---

*(Results are appended below, per item, as each is completed.)*
