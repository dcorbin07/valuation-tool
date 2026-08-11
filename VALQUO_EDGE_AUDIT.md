<!-- PROVENANCE
External audit, revision 2, 2026-08-03. Produced by a Cowork session with READ-ONLY access to this
repo. Nothing in the codebase was modified. This is NOT project memory in the sense of
HANDOFF_STATUS.md — it is an outside review, and where it contradicts the project record the
contradiction is the point.

Every finding is a CODE-READING finding. Nothing was executed. Magnitudes, directions and outcomes
are unverified; treat each item as a hypothesis with a file:line citation attached. All references
are against commit 7eb0046.

READ FIRST: PROMPT_edge_audit_execution.md — pre-commitments, tree reconciliation, session order.
BEFORE PARALLEL DISPATCH: VALQUO_AUDIT_DEPENDENCY_MAP.md + `python check_lanes.py <ids>`.

134 numbered items: B1-B26 / R1-R10 / X1-X8 / S1-S28 / O1-O26 / U1-U8 / C1-C7 / P1-P5 / D1-D10 / M1-M6.
Cite the ID in every result and commit message. Part I gates Part II gates everything else.
Full sequencing in Part XV. PDF of the same content: Valquo_Edge_Audit_and_Test_Catalogue.pdf
-->

# Valquo — Edge Audit and Test Catalogue

### A work order for the next research session

**Prepared 3 August 2026** · Scope: `C:\Users\donni\Downloads\valuation-tool` at commit `7eb0046` (branch `worktree-growth-valuation`, working tree dirty), plus the full handoff corpus and `BACKTEST_RESULTS.json` schema v4.

---

# 0. How to use this document

This is written to be executed by an autonomous coding session with repository access, not read once and filed. Four rules govern it.

**Order is load-bearing.** Part I contains corrections. Until they land, most numbers in the project measure something other than what their labels say, and running new tests on top of them wastes the runs. Part II re-decides questions that are currently believed settled but rest on the defects in Part I. Parts III onward are new work and assume both are done.

**Every item is pre-registered.** Each carries a hypothesis, an exact method, a pass/fail threshold committed *before* the run, an expected failure mode, and an effort estimate. An item whose result is ambiguous against its own threshold is a **null**, not a judgement call. This is the discipline the project already runs on; the catalogue just makes it explicit per item so no session has to re-derive it.

**The methodology rule from `CLAUDE.md` applies to everything here.** Verdicts come from the full ~2,710-name equity universe and the full mined options universe. Subsets are smoke tests and must be labelled as such. Where an item below can only be run on a subset, it says so and states what that costs.

**Most of this will reject.** That is the correct expectation and it is not a failure of the catalogue. The project's own hit rate across ~146 recorded tests is roughly one adoption in eight, and the adoptions cluster in bug fixes rather than new signals. The value of a catalogue like this is in running many cheap, orthogonal, honestly-gated ideas and keeping the two or three that survive — plus, importantly, in **closing** questions so they stop consuming attention.

A note on what this document is not. It does not re-litigate decisions that were made well. The rejections of TTM ROE/ROIC, robust z-scores, momentum+institutional consolidation, `iv_rank` as an entry filter, and the stock ML combiner at current data size each have an understood *mechanism* for why they fail, not merely an unfavourable number. Those are correctly closed and appear only on the do-not-reopen list in Part VIII.

---

# 1. Executive summary

Ten findings, ordered by how much they change what the project believes it knows. Detail and file references follow in the numbered parts.

### A. The headline equity number is not alpha, and has never been tested as alpha

`+11.88%/yr top-decile alpha` is computed as `4 × (mean top-decile 63-day return − mean equal-weighted universe 63-day return)`. That is the whole definition; it lives in three lines of `fundamental_panel.py` (`:1857`, `:1874`, `:1881`). There is no beta adjustment, no factor regression, no risk adjustment of any kind, and no t-statistic on the headline metric anywhere in the repository. A search for `fama`, `french`, `carhart`, `ff3`, `ff5` across the tree returns only prose in a documentation file.

This matters because the composite *is* one-seventh each of value, quality, momentum, size, capital discipline (net issuance) and institutional ownership. Those are, almost exactly, the Fama–French five factors plus momentum. The number as computed cannot distinguish "we found something" from "we assembled the standard factor premia and measured them against a cap-neutral average."

That is not an accusation that the edge is fake. It may well survive; the quality theme in particular (IC t +3.39, `gp_on_capital` t +4.61) is doing real work and gross profitability is a genuinely priced factor. But **the project does not currently know**, and the test costs one afternoon against free data from the Ken French library. Until it runs, the word *alpha* should not appear in the product copy.

### B. The one out-of-sample confirmation the model rests on is not out-of-sample

`holdout_theme_validate`'s docstring describes a clean protocol: flag a theme on one half using a pre-specified rule, then measure the effect of removing it *only* on the other half. The code computes the flag (`rule_fired`, `fundamental_panel.py:2898`), reports it, and never consults it. The verdict is `all(improves)` across both split directions (`:2906-2909`) — that is a stability check on the full sample, not an out-of-sample confirmation.

The consequence is specific. Zeroing `low_risk` is the single largest tuning decision in the model's history — it is the main driver of PBO falling from 40% to 13.3%, and of long-short *t* rising from 1.175 to 3.485. It is recorded in `CLAUDE.md` as "CONFIRMED on a held-out time split … measured on the later half that did NOT inform the decision." In the shipped run, `low_risk` is `confirmed` while `rule_fired = false` in one of the two directions, which is only possible because the flag is ignored.

Again: this does not mean zeroing `low_risk` was wrong. The mechanism given for it — a −0.352 correlation with `size`, so it was cancelling the small-cap tilt — is coherent and probably right. It means the *confirmation* is a both-halves stability result, and the model's headline validation claim overstates its own protocol.

### C. Deflated Sharpe ≈ 100% is an undeflated Probabilistic Sharpe Ratio

The deflation uses `N = 8` trials, and those eight are eight near-identical weightings of the same eight themes — their out-of-sample median ICs span +0.061 to +0.062. The Bailey–López de Prado benchmark `SR₀` scales with the cross-trial *variance* of Sharpes; when the trials are indistinguishable that variance is ~0, so `SR₀ ≈ 0` and the statistic collapses to `Φ(SR·√(n−1))`. It saturates at 0.9999986 because it is not deflating anything.

PBO of 6.7% has the same shape of problem: `pbo_cscv` scores only the weight-scheme selection step. It says "the best of eight nearly-identical weightings generalises." It says nothing about the ~146 signal-inclusion, theme-membership, universe, standardisation and construction decisions recorded in the project ledger — and the shipped strategy keeps `current-default` anyway, so the selection being scored is one the model never makes.

Two of the three statistical bars the project cites as cleared are therefore measuring something narrower than the claim they support. The third — long-short *t* of 3.52 — is real, and it clears the Harvey–Liu–Zhu multiple-testing hurdle of 3.0, which is the more meaningful benchmark. Lead with that one.

### D. The panel is 27 years long, not 18, and its first third has an inverted universe

`WRDSProvider.price_history` truncates with `df.sort_values("date").tail(days)` (`data_providers.py:338`), where `days = 252×18 + 63 + 60 = 4,659`. Each ticker keeps its *own last* 18.5 years. The panel calendar is the union, so it runs 1998-12-31 → 2026-04-22 — 110 rebalance dates over 27.3 years.

The bias this creates is unusual and worth stating carefully: at a 2001 cross-section, every name present is one that *stopped trading by about 2019*. Survivors are truncated out of the early sample entirely. This is the inverse of classic survivorship bias and it probably depresses early-period returns rather than inflating them — but it is severe, non-random, and it makes roughly the first 37 of 110 periods uninterpretable. Those same 37 dates have no benchmark at all (SPY is fetched under the same cap), which is why `construction.n_periods` reports 110 while `portfolio.n_periods` reports 73 over an undisclosed window. Two headline blocks in the same results file are measured over different date ranges.

### E. A price-basis bug sits underneath the project's most damaging options finding

`options_universe.py:327` and `:594` pass `w["close"]` — the split- *and dividend*-adjusted series — into `chain_summary`, `pick_contract` and `compute_signals`. The correct runner uses `w["raw_close"]` (`optbt_run.py:132`), and `options_backtest.py:49-68` documents this exact mixture at length as "silently fatal."

The corroboration is already in the project's own handoff, recorded as an unexplained anomaly. `HANDOFF_universe_backtest.md` §8 flags that the 187-name run's median entry IV reads **1.28–1.57 across tiers** and calls it "implausible as a real ATM vol." The correctly-priced 55-name run reports ATM IV quartiles of 18.1% / 33.1%. The arithmetic closes: for a front expiry at ~3 DTE, an ATM call is roughly `0.4·S·σ·√T`; if the spot is understated by a factor *k*, the solved vol is approximately `(k−1)/(0.4·√T)`, which for a 5% cumulative dividend adjustment and T = 3/365 gives σ ≈ 1.38 — squarely inside the observed range. The anomaly the handoff could not explain *is* this bug.

What it contaminates: the 187-name headline (+5.14%/trade), every tier table, the `term_slope` out-of-sample test, and **the random-entry control that produced "+13.22% random beats +5.14% signal"** — currently the most consequential negative result in the project. The −8.08pp gap is more robust than the levels, because the control is same-name and same-year and the adjustment factor is roughly constant within a year, so much of the distortion differences out. But no absolute number from that run should be quoted until it is re-run, and the `term_slope` out-of-sample test is not salvageable at all, because `term_slope` is a difference of two implied-vol solves whose at-the-money strike selection is itself corrupted.

Two independent audits found this separately. It is a two-character fix plus a re-run.

### F. Every options statistic treats correlated megacap long calls as independent observations

The permutation test shuffles individual trades (`options_autopsy.py:656-669`). The bootstrap resamples individual trades and its own docstring concedes it "ignores within-name clustering, so the CI is optimistically narrow" (`options_universe.py:527-528`). Deflated Sharpe uses `n` = raw trade count. Nothing anywhere computes an effective sample size.

A week of long calls across fifty correlated megacaps is, in risk terms, close to one bet on the market. Counting it as fifty inflates every t-like quantity by roughly the square root of the clustering factor. The only place clustering is handled at all is `pbo_cscv`, which blocks by date — and that one has no purge or embargo, so trades entered in an in-sample block are still open well into the adjacent out-of-sample block.

Separately: the two numbers the entire options conclusion rests on — the paired *t* of −2.18 and the sign-test *z* of −5.24 — **do not exist in the repository**. They were computed ad hoc in a session and are not reproducible from shipped code.

### G. The live product runs a configuration the research rejected twice

`screen.py:256` calls `build_frame(metrics)` with no keyword arguments, so it inherits `CONFIG.sector_neutral` (default **true**) and `CONFIG.residual_momentum` (default **true**). The backtest forces both to `False` (`fundamental_panel.py:1096`).

Sector-neutral ranking was tested on the full universe, rejected in both held-out directions, re-run independently on a later panel, and rejected again. The rejection is recorded in `CLAUDE.md` and in a dedicated handoff. The code default was never flipped. Unless `SCREENER_SECTOR_NEUTRAL=false` is set in the environment, the hot list users see is scored under the intervention the research eliminated.

More broadly there are three composite functions in the tree — the selection composite (which renormalises by present-weight mass), the measurement composite (which does not, so a name missing `institutional` on 38.6% of rows is scored as exactly average on it and pulled toward the middle), and the live composite (renormalised, plus soft-bucket blending). **No shipped code path reproduces the backtested composite exactly.**

### H. The forward paper track is not comparable to the thing it exists to validate

The track is the project's stated number-one priority and the only test on unseen data. Four defects make its output non-comparable:

The exit trigger fires on the **mid** (`paper_broker.py:184-187`) while the backtest fires on the **bid** (`options_backtest.py:330`). On a 10%-wide quote that is roughly 5 percentage points of measured return, and it is asymmetric — the paper book reaches +100% earlier and −50% later than the backtest would. `--dry-run` marks an alert `skipped`, and skipped alerts are permanently excluded from the live track (`paper_track.py:305-309` with `:225,241`). A resumed entry after a crash is placed as a **market** order with `target_premium` and `stop_premium` left NULL, so that position can never take profit or stop out — it silently becomes a different strategy. And P&L is recorded against the *alert-time* ask rather than the actual fill, so the broker fill is decorative for return purposes.

The track has one session of about 126. Fixing these now costs almost nothing; fixing them in three months means discarding three months.

### I. Three signals at t ≈ 2.0 score nowhere; two signals at t ≈ 0 score in the composite

`neg_ev_sales` (IC t **+2.05**), `neg_ev_ebitda` (**+1.99**) and `neg_ps` (**+1.51**) are computed, z-scored and enter no theme mean for *established* (profitable) names — they are wired only into the speculative branch. Meanwhile `book_to_price` (t **+0.15** at 100% coverage) and `neg_beta` (t **−0.05**) are in the composite.

This is not the same question as the EV/Sales promotion that was tested and rejected. That test added EV/Sales as a linear input to the established value branch and the *composite* got worse on every metric while the *theme* IC improved 17%. The open question is different and narrower: the value theme currently scores established names on `earnings_yield`, `fcf_yield`, `ebit_ev` and `book_to_price`, and one of those four contributes nothing measurable. Dropping a dead input is a different experiment from adding a live one.

Two related defects: `accruals_q` is computed in the panel as `−(NI−CFO)/assets` and then unconditionally overwritten in `factors.py:136` with `FCF/NI` restricted to profitable names — so the signal reported as `accruals_q` is not the one documented, and its IC fell from a recorded t +3.08 to +1.26. And `cash_op_prof` — cash-based operating profitability, one of the better-documented quality factors in the literature — is fully computed at `fundamental_panel.py:517-529`, assigned in `factors.py:151`, and never registered in `NUMBER_THEME`, so it is invisible even to the coverage guard.

### J. The two research programmes have never been joined

The stock model has a measured cross-sectional edge at 63 days, strongest in large caps. The options book, on its own evidence, has no entry edge — its own signal loses to a random-entry control on the same names in the same years.

Nobody has ever tested using the stock composite as the options entry signal.

Both datasets exist. They overlap precisely on the megacap names where the equity edge is strongest and where option spreads are narrowest. The natural expression — 60 to 90 days to expiry, moderately in-the-money for delta rather than convexity — sits inside the mined DTE band. The equity signal's horizon (63 trading days) and the option's tenor line up almost exactly.

This experiment appears on no roadmap, in no handoff, and in no prompt file. It is the single largest untested idea in the project and it is nearly free to run.

---

### What this adds up to

The project's research discipline is genuinely unusual — the pre-registration, the held-out gates, the corrections written into the record rather than quietly replaced, the refusal to adopt weight schemes the CPCV declines. That discipline is the reason this audit could find these things at all: a less rigorous project would not have left an audit trail precise enough to check.

But the discipline has been applied *downstream* of a measurement layer that nobody audited. The gates are sound; several of the quantities passing through them are not what their names say. The corrections in Part I are mostly small — a price basis, a decision rule, a benchmark definition — and they are worth doing before anything else because they determine whether the last six months of conclusions mean what the record says they mean.

The honest current state, restated:

- **The equity model** is a well-built, well-tested multi-factor portfolio with a long-short *t* of 3.5 that clears the Harvey–Liu–Zhu bar. Whether it produces *alpha* in the risk-adjusted sense is untested. Whether its top-decile excess return survives a stable-universe re-run is untested. Both are cheap to settle.
- **The options book** is long-volatility beta with one surviving filter, and the evidence that its entry signal is worse than random rests on a run with a corrupted price basis. That question is currently open, not closed.
- **The forward track**, the one genuinely out-of-sample instrument either programme has, is running with four known comparability defects and one session of data.

---

# PART I — Blocking corrections

Sixteen items. These are not improvements; they are the difference between a number meaning what it says and not. Each is small. Together they are perhaps three sessions of work, and every downstream test in this catalogue is contingent on them.

Effort key: **XS** under an hour · **S** a few hours · **M** most of a session · **L** more than one session.

---

### B1 · Price basis in the broad options universe — **do this first**

**Defect.** `valuation/edge/options_universe.py:327` (`run_name`) and `:594` (`random_entry_control`) set `und = w["close"][-1]`. `load_bars` (`options_backtest.py:172-175`) defines `close ← closeadj` (split *and* dividend adjusted, labelled "technicals only") and `raw_close ← closeunadj` ("AS-TRADED — all option maths"). The 55-name runner uses `raw_close` correctly at `optbt_run.py:132`. Three consumers receive the wrong spot: `chain_summary` (ATM IV), `pick_contract` (the 0.90–1.20 moneyness band and the 0.35-delta target), and `options_signals_v2.compute_signals` (`term_slope`, `skew_25d`, `vrp`, `gex_proxy`).

**Consequence.** On every pre-split date of every split name (AAPL 4:1 2020, TSLA 5:1 2020 and 3:1 2022, NVDA 4:1 2021 and 10:1 2024, AMZN and GOOGL 20:1 2022, plus mid-caps), the moneyness prefilter matches nothing and the silent `near = d` fallback at `:279-280` hands the whole ladder to the delta solver. Dividend adjustment corrupts *every* payer on *every* date, growing with lookback. Settlement, meanwhile, correctly uses `raw_close` (`options_backtest.py:344`), so entry and settlement of the same trade run on different price bases.

**Fix.** Change both lines to `w["raw_close"][-1]`.

**Then re-run, in this order:** the 187-name book; the random-entry control (both seeds); the `term_slope` out-of-sample test on the 133 names that never informed the threshold; the broad autopsy; the tier tables.

**Regression guards to add.** (a) A test pinning `run_name`'s underlying to the unadjusted series — the same shape as `test_options_split_adjustment_two_series`. (b) A `sanity()` flag when median entry IV falls outside [0.05, 1.00]; the current run would have fired it at 1.28–1.57.

**What to expect.** The −8.08pp real-versus-control gap is the most robust quantity in that run because the control is same-name and same-year, so a within-year-constant distortion largely differences out. Expect it to survive in sign, possibly shrink. Expect every *level* to move. Expect the `term_slope` out-of-sample retention figure (36.4%, which failed a 40% floor) to change materially, since it is a difference of two corrupted implied-vol solves.

**Effort: XS to fix, M to re-run.**

---

### B2 · The exit path silently deletes days from a trade's history

**Defect.** `options_backtest.py:327-328`:

```python
if F.quote_reject_reason(q, check_liquidity=False) is not None:
    continue
```

`check_liquidity=False` disables only the open-interest and volume tests. `wide_spread` (spread > 25% of mid) and `thin_premium` (mid < $0.10) still reject — and a rejected day is skipped entirely, as though it never happened.

**Consequence, in both directions.** A decaying out-of-the-money call quoting 0.25 / 0.35 has a 33% spread and vanishes from its own exit path — precisely in the price region where the −50% stop should fire. Losers that decay through the stop on wide-quote days are not stopped and ride on to a worse outcome (conservative). But losers that dip through −50% on a wide-quote day, are skipped, and then recover are **recorded as target wins** (optimistic, and unmeasured).

The module docstring asserts the opposite of what the code does — `options_fill.py:41-46` claims "Exit therefore uses whatever quote exists, however bad," and refers to an `exit_value` function that does not exist.

**Fix.** Introduce a separate, much looser exit tolerance: at exit, reject only `no_quote`, `non_positive` and `crossed`; mark thin or wide quotes at the bid anyway. Count skipped exit-days per trade and surface the rate in `sanity()`.

**Why this is blocking.** The exit sweep (item **O1**) is the highest-value untested lever in the options programme and it is meaningless until the exit path stops censoring the days the stop would have fired on.

**Effort: S.**

---

### B3 · "Expiry" exits are marked at a stale quote, not at intrinsic value

**Defect.** `options_fill.round_trip` (`:183-191`) prefers a quote over intrinsic value whenever one is available, and the quote it receives is `last_q` — the last quote that passed validation *at any point in the contract's life*, possibly weeks earlier. The trade is then stamped `exit_date = expiry`, `held_days = full DTE`, `settled_at_intrinsic = False`.

**Consequence.** Expiry trades show a mean of −29.3% where a genuinely expired long option should be at or near −100%. `sanity()`'s `settled_at_intrinsic_frac` check cannot see this, because the flag reads False. Roughly 1% of trades, but the direction is systematically optimistic and it corrupts the worst tail of the distribution — the part that matters most for sizing.

**Fix.** Add a flag forcing intrinsic settlement at expiry, default it on, and record the age of any quote used as a mark. Any mark older than, say, three trading days should be rejected in favour of intrinsic.

**Effort: XS.**

---

### B4 · The open-interest sentinel reaches the backtest untreated

**Defect.** `theta_bulk.py:218-229` performs a separate `option_history_open_interest` call. On failure it fills `open_interest` with **−1**, returns `failed=False`, and caches the year as complete. The derived greeks layer treats −1 correctly as a sentinel and computes every aggregate on known-OI rows only. **`options_backtest.chain_summary`'s `call_oi` / `put_oi` sums were never touched.**

**Scale.** 19,012,352 rows — 11.4% of the cache, 106 of 111 names, median 12.2% per name, worst cases above 20%. Every single row of AAPL 2020 has no open interest at all.

**Consequence.** Read as a number, −1 flips that contract's contribution in any OI sum and poisons the put/call open-interest ratio. `f_d_pc_oi` — one of the closest near-misses in the 64-feature autopsy, rejected on a permutation p of 0.0545 against a 0.05 bar — is built on exactly this. Also: every contract in an affected span fails the `low_oi` gate at entry and is silently counted as `no_contract_in_band`, which means alert-to-trade conversion is understated in an unknown, name-dependent way.

**Fix.** Treat −1 as missing everywhere. Add a coverage audit over `data/options/*/*.pkl` reporting the fraction of rows with `open_interest >= 0` per symbol-year, in the same spirit as `signal_coverage()` on the equity side. Re-mine AAPL 2020 and the other worst offenders.

**Effort: S, plus mining time.**

---

### B5 · Four defects in the forward paper track

The track is the only unseen-data instrument either programme has. Fix these before it accumulates.

| # | Defect | Location | Consequence |
|---|---|---|---|
| 5a | Exit triggers on the **mid**; the backtest triggers on the **bid** | `paper_broker.py:184-187` vs `options_backtest.py:330` | ~5pp of measured return on a 10%-wide quote, asymmetric: reaches +100% earlier, −50% later. Directly on the axis the track exists to test |
| 5b | `--dry-run` marks an alert `skipped`, and skipped alerts are permanently excluded | `paper_track.py:305-309` with `:225,241` | Any alert touched by a dry run never enters the real track |
| 5c | A resumed entry is placed as a **market** order with NULL `target_premium` / `stop_premium` | `paper_track.py:236-238` → `:293` → `paper_broker.py:238-242` | That position can never take profit or stop; it exits only on time or expiry. A crashed run silently converts trades into a different strategy |
| 5d | P&L is recorded against the **alert-time ask**, not the fill | `paper_track.py:439-441` → `options_tracker.py:120-133` | The broker fill is decorative for the return series; the stored `paper_option_orders.entry_premium` is never used |

Two lesser items worth folding in: `_record` returns `True` unconditionally (`:447`), so a failed `record_outcome` still closes the paper row and silently desynchronises the two tables; and a missing bid at close sends a market order (`:414`), outside the stated ask-in / bid-out convention.

**Fix 5a by changing the trigger basis to the bid** so the paper book and the backtest measure the same object. Everything else is straightforward.

**Effort: S.**

---

### B6 · Panel truncation and the two-date-range results file

**Defect.** `data_providers.py:338` — `df.sort_values("date").tail(days)` with `days = 4,659`. Each ticker keeps its own last 18.5 years, so the union spans 27.3 years and pre-2008 cross-sections contain only names that stopped trading by roughly 2019. Cross-section size runs from about 880 names per date early to about 1,676 late. Thirty-seven of 110 dates have no benchmark, which is why `construction.n_periods = 110` and `portfolio.n_periods = 73` in the same JSON, over different and undisclosed windows.

**Fix, three options in increasing order of correctness:**

1. Restrict the panel to a date range where universe composition is stable — roughly 2008 onward — and re-derive PBO, long-short *t*, top-decile alpha and monotonicity on it. Cheapest; loses half the history.
2. Fetch full price history per ticker and truncate the *calendar*, not each ticker's series. Correct; costs a longer load.
3. Do (2) and additionally report cross-section size per date and weight the period-level statistics by it, so a thin 1999 cross-section is not one observation of equal weight to a full 2024 one.

**Whichever is chosen, stamp the actual date range and period count on every block in the results file.** Two headline blocks currently disagree about what window they cover, with no marker.

**What to expect.** The direction is genuinely unclear. Early periods contain only eventual-delisters, which should depress returns, so the current figure may be *understated*. But the composition is non-random in ways that interact with `size` and `value`, so it could go either way. That uncertainty is exactly the problem.

**Effort: M.**

---

### B7 · Unify the three composite functions

**Defect.** Three different scorers exist.

*Selection* (`cpcv_validate` at `:2074-2080`, `walk_forward` at `:1682`, `_weighted_optimize` at `:1588`) renormalises by present-weight mass, so a name missing a theme is scored on what it has.

*Measurement* (`quantile_backtest` at `:1843-1845`, and `_backtest`, `_backtest_hold`, `regime_split`, `_strategy_returns`, `turnover_and_costs`, `after_tax_backtest`) does not — a missing theme contributes zero, i.e. exactly the cross-sectional average, pulling the name toward the middle.

*Live* (`screen.py:256` → `factors.build_frame` with CONFIG defaults → `cross_sectional.composite_score` → soft-bucket blending) renormalises **and** applies sector-neutral ranking and residual momentum.

**Consequence.** `institutional` is missing on 38.6% of rows and `insider` on 15%. Under the measurement composite the extreme deciles are systematically biased toward data-complete names — larger, better-covered, institutionally-held stocks. The top-decile alpha and long-short *t* are computed under the biased composite; the weights that produced them were chosen under the other one. And the live product uses a third variant that includes an intervention the research rejected twice.

**Fix.** One composite function, one definition of missing-data handling, used in selection, measurement and live. Flip `CONFIG.sector_neutral` and `CONFIG.residual_momentum` to default `False` to match the recorded rejections, and add a test asserting the live path and the backtest path produce identical scores on a fixed fixture.

**Effort: M.** This is the highest-leverage structural fix in Part I after B1.

---

### B8 · Make `holdout_theme_validate` do what it documents

**Defect.** `rule_fired` is computed at `:2898` and never read; the verdict at `:2906-2909` is `all(improves)` across both directions.

**Two acceptable resolutions, and they lead to different places.**

*Option A — implement the documented rule.* Gate on `rule_fired` in the deciding half, then measure only in the other. Re-run every theme decision through it. Be prepared for `low_risk` to come back `not_replicated`, since it currently passes a test it may not pass under the stricter protocol. That would not automatically mean re-instating `low_risk` — the size-cancellation mechanism is independent evidence — but it would mean the model's headline validation claim needs rewriting.

*Option B — keep the both-halves stability test and rename it.* It is a legitimate and quite demanding test; it just is not out-of-sample confirmation. Rename the function and the verdict labels, and correct `CLAUDE.md`, `HANDOFF_STATUS.md` and the product copy.

**Do not leave it as it is.** The current state is a test whose documentation and behaviour disagree, supporting the project's most-cited claim.

**Note the related defect:** the gate evaluates equal weights across themes, never the deployed weights. So the shipped configuration has never been through its own theme gate.

**Effort: S for Option B, M for Option A plus re-runs.**

---

### B9 · Restate or recompute the Deflated Sharpe and PBO

**Fix, minimal:** relabel. Report the current statistic as a Probabilistic Sharpe Ratio, which is what it is, and report PBO as "probability of backtest overfitting *of the weight-scheme selection step*."

**Fix, honest:** maintain a research log (item **M1**) with a genuine trial counter across all sessions, and feed `N` from it. On the ledger's own count that is of the order of 100+ trials on the equity side, which gives `√(2·ln N) ≈ 3.0` as a haircut — coincidentally about the Harvey–Liu–Zhu hurdle. Also fix the two inconsistent conventions in the same file: `validate_institutional` calls `_deflated_sharpe(strat, [single_sharpe])` giving `N = 2` and `var_sr = 1/n`, a different formula from the main path.

Also reconcile the two Deflated Sharpe implementations across the repository — `fundamental_panel._deflated_sharpe` and `options_autopsy.deflated_sharpe` disagree on the key input (`var_sr` as sampling variance versus cross-trial variance) and will never reconcile.

**Effort: XS to relabel, S to do properly.**

---

### B10 · `accruals_q` is computed and then silently overwritten

**Defect.** `fundamental_panel.py:513-515` computes `m["accruals_q"] = −((NI − CFO) / assets)` — negated total accruals, the Sloan measure. `factors.py:136` then unconditionally overwrites it with `np.where(ni > 0, fcf / ni, np.nan)`.

`build_frame` guards the other two collision cases — `book_to_price` at `:131-133` prefers the caller's value, `growth_accel` at `:108-113` only derives when the caller did not — but not this one. Coverage of 75.3% is consistent with the `ni > 0` restriction; the accruals measure would sit near 95%. The recorded IC fell from t +3.08 (in `settings.py:195`) to +1.26.

**Fix.** Guard the collision the way the other two are guarded, then measure both definitions and keep the better one on its merits. Add a general test that fails when `build_frame` overwrites any column the caller supplied.

**Effort: XS.** One of the cheapest genuine signal recoveries available.

---

### B11 · The "37 bps actual cost" number is not computed anywhere

The project's most quotable tradeability claim is "236 bps breakeven against a 37 bps actual cost profile — a 6.4× margin." The breakeven side is computed, gridded and shipped. The 37 bps side appears once, in `HANDOFF_STATUS.md:1283`, and is never recomputed or regression-tested. There is no book-weighted average of `one_way_cost_bps` anywhere in the code.

**Fix.** Compute the realised turnover-weighted average cost inside `turnover_and_costs` and ship it in the `costs` block alongside the breakeven, so the ratio has both of its numbers under test.

**While there, note two limitations to state explicitly.** The cost table is keyed on point-in-time market cap only — no spread, no average daily volume, no price level, no participation rate. And the equal-weight benchmark is charged **zero** cost (`:2440-2441`) while the strategy pays, so every "alpha versus equal-weight" figure is a comparison in which only one side trades.

**Effort: S.**

---

### B12 · Every "800 largest names" result in the project's history was an alphabetical slice

**Defect.** `WRDSProvider.universe` (`data_providers.py:354-356`) returns `sorted(self._indexed("fundamentals").keys())[:limit]` — alphabetical. Only `SharadarProvider.universe` ranks by market cap, and the local-export path used by `run_backtest.bat` does not go through it.

**Consequence.** The 800-name era results — the first CPCV "adopt", PBO 13%, Deflated Sharpe 77%, `f_score` at t +5.66, `sm_breadth` at t 2.37, the 13F look-ahead stress test, and the four classic-anomaly rejections — were all computed on names beginning with A through roughly C, not on the 800 largest. This reframes the project's own calibration note. "PBO 13% on 800 → 53% on full" was not measuring how much a large-cap tier flatters results. It was measuring how much an arbitrary 30% alphabetical subsample does.

**Fix.** Correct the function, and add the sort key to the printed banner so a mislabelled universe is visible in the log. Then treat every 800-name result as needing a full-universe re-run before it is cited — see items **R5** and **R6**.

**Note** that `SharadarProvider.universe`'s ranking is itself a mild look-ahead, since `scalemarketcap` is today's size bucket. For a subset used only as a smoke test that is acceptable; for anything reported it is not.

**Effort: XS to fix, M to re-run what depends on it.**

---

### B13 · The backtest holds a book the live product would refuse

**Defect.** The only universe screen in `build_fundamental_panel` is a $50M point-in-time market-cap floor (`:998-999`). `prefilter` — which drops warrant, unit and rights suffixes, sub-$1.00 names and illiquid names (`factors.py:23-49`) — is called in `score_universe_now` (`:1301`) but **never in the backtest path**.

Separately, `MIN_AVG_DOLLAR_VOLUME` never binds anywhere on this data path: `prefilter` skips it when `adv is None` (`factors.py:46-48`) and `_sf1_to_metrics` never sets `avg_dollar_volume`. The liquidity screen has never once been active.

**Consequence.** The validated deciles can contain penny stocks and warrant tickers the live book will not buy — and `size` is one-seventh of the composite, pointing straight at them. The 236 bps breakeven is then computed on that book, with a cost model blind to price level and spread.

**Fix.** Run `prefilter` in the backtest, wire average dollar volume from SEP (it is on disk), and re-derive the cost and breakeven figures on the resulting investable book.

**Expect** the top-decile alpha to fall somewhat and the breakeven to fall too. That is the correct number.

**Effort: S.**

---

### B14 · The delisting mask's coverage is measured and thrown away

`fundamental_panel.py:949` increments `_masked` on every blanked series and `:957` never prints, returns or ships it. `BACKTEST_RESULTS.json → cleanups.survivorship_mask` is only a boolean meaning "the map is non-empty."

If ACTIONS misses a delisting, that name's last close is forward-filled to 2026 and it contributes a fake flat 0% forward return to *every* subsequent rebalance date — the exact failure the mask exists to prevent — and nothing surfaces it. Compare `ev_freshness`, which was built precisely to make a silent revert loud. Ship `_masked`, plus the count of names whose price series ends before the panel end without a corresponding ACTIONS row.

**Effort: XS.**

---

### B15 · The options headline is not net of commission, contrary to the documentation

`options_fill.py:204` computes `return_pct = exit_px / entry_px − 1.0`. `net_pnl` at `:199` does subtract commission; `to_alert_row` maps `pnl_pct ← return_pct` (`options_backtest.py:484`), and `expectancy_pct` averages `pnl_pct`. So "+10.4%/trade" is net of spread and **gross of commission**, while `options_fill.py:49-52` and `OPTIONS_BACKTEST_RESULTS.md:4-5` both state it is net of both.

Magnitude is small — $1.30 round trip on a $485 median position, about 0.27pp — but the claim is false as written, and the fix is one line.

While in that file: `profit_factor` is computed as a ratio of summed *percentages* rather than dollars (`options_tracker.py:149-175`). That is a non-standard definition and should be labelled wherever "PF 1.30" appears.

**Effort: XS.**

---

### B16 · Quarantine the dead exit module and fix the stale references

`valuation/edge/options_exit.py` is imported by nothing. It implements an *underlying-price* proxy — ±1σ on the stock — and has nothing to do with the results. `options_tracker.py:4` and `HANDOFF_STATUS.md:888` still describe it as the exit engine. It is the single most likely thing for a new session to mistake for the live exit logic, and the live exit logic is an inline loop at `options_backtest.py:319-341`.

Delete it or move it to an `archive/` directory with a banner. Fix the `exit_value` reference in `options_fill.py:46`. Remove the unreachable `if not t.get("ok"): continue` at `options_backtest.py:336-337`, which would silently skip a genuine exit trigger if it ever fired.

**Effort: XS.**

---

### Part I summary

| ID | Item | Effort | Blocks |
|---|---|---|---|
| **B1** | Price basis in `options_universe` | XS + M re-run | All options conclusions |
| **B2** | Exit-path quote censoring | S | O1, the exit sweep |
| **B3** | Stale-quote expiry marks | XS | Tail and sizing work |
| **B4** | OI sentinel into `chain_summary` | S | Any OI-based signal |
| **B5** | Four paper-track defects | S | The forward validation |
| **B6** | Panel truncation | M | All equity headline numbers |
| **B7** | Three composites → one | M | Live/backtest comparability |
| **B8** | Holdout rule vs documentation | S–M | The out-of-sample claim |
| **B9** | DSR / PBO trial accounting | XS–S | The statistical bars |
| **B10** | `accruals_q` overwrite | XS | A live signal |
| **B11** | Compute the 37 bps figure | S | The tradeability claim |
| **B12** | Alphabetical universe | XS + M | R5, R6 |
| **B13** | Prefilter in the backtest | S | Cost and breakeven realism |
| **B14** | Ship delisting-mask coverage | XS | Survivorship confidence |
| **B15** | Commission in `return_pct` | XS | Options headline accuracy |
| **B16** | Dead exit module | XS | Reader safety |

---

# PART II — Re-derivations

Ten questions the project currently treats as settled that are not, once Part I lands. These are not new ideas. They are existing conclusions that need to be re-earned, and several of them could move the project's headline story in either direction.

---

### R1 · Factor-adjusted alpha — **the single most important test in this document**

**The question.** Is the top-decile excess return alpha, or is it the Fama–French premia the composite is assembled from?

**Why it is unresolved.** `top_decile_alpha = 4 × (mean top-decile 63d return − mean equal-weighted universe 63d return)` and nothing else. No factor model, anywhere.

**Method.**

1. Build a 110-period series of top-decile-minus-equal-weight returns. This already exists inside `quantile_backtest` as `q_rets[0]` and `ewb`; it just needs to be shipped.
2. Download the Fama–French 5-factor plus momentum daily series from the Ken French library (free, no registration). Compound to the same 63-trading-day windows on the same date grid.
3. Regress: `r_t = α + β₁·MKT + β₂·SMB + β₃·HML + β₄·RMW + β₅·CMA + β₆·UMD + ε`.
4. Report the intercept, its Newey–West *t* with a lag of 1 (windows are adjacent, not overlapping, but factor spreads are autocorrelated), the R², and every loading.
5. Repeat against the Hou–Xue–Zhang q-factor model (MKT, ME, I/A, ROE) from global-q.org, which is a harder test for a quality-heavy portfolio.
6. Repeat on the long-short series, which is the cleaner object.

**Pre-registered thresholds.** Report all three of: raw excess return, FF5+MOM alpha with *t*, q-factor alpha with *t*. Adopt the language "alpha" in product copy only if the FF5+MOM intercept is positive with *t* > 2.0. If the intercept is indistinguishable from zero, the honest framing is *efficient factor exposure* — which is still a real product, just a different one.

**Expected outcome, stated in advance so it cannot be rationalised afterwards.** Some of the 11.9% will survive; most probably will not. The quality theme is the strongest contributor and RMW is a well-priced factor, so RMW will likely absorb a lot. `size` will load on SMB. `capital_discipline` (net issuance) will load on CMA. What survives is most likely to come from `institutional` — the one theme with no Fama–French analogue — and from the interaction structure of combining seven themes rather than sorting on one.

**What to do with a null.** Do not bury it. A model that delivers the standard premia cheaply, transparently, and with a public forward track is a legitimate product. The category is full of tools claiming secret alpha; a tool that says "here is diversified factor exposure, here is exactly what it is, here is the live track" is more defensible and more honest than the alternative. It also changes the roadmap: if the value is exposure rather than selection, then **construction, cost and tax work** (Part VI) becomes the entire remaining edge, and further signal hunting is close to worthless.

**Effort: S.** One afternoon. It is astonishing that it has not been run.

---

### R2 · Re-run the whole broad options study after B1

Everything in `HANDOFF_universe_backtest.md` is computed against a mis-stated underlying price. Re-run and re-decide:

- The 187-name expectancy, tier tables, and the mid-fill decomposition.
- The random-entry control, both seeds. **This is the one that matters.**
- The `term_slope` out-of-sample test on the 133 non-informing names.
- The broad autopsy's 64 features, particularly the four that touch `compute_signals`.

**Pre-register before running** — this is important, because the result is currently the project's most consequential negative finding and it will be tempting to read the re-run charitably. Commit in advance: if the corrected real-versus-control gap remains negative at conventional significance under a *date-block* bootstrap (item **R3**), the conclusion stands and the options entry signal is dead. If the gap closes to within its confidence interval, the honest verdict is *inconclusive*, not vindicated — a signal that cannot beat random entry by a measurable margin is not a signal, it is an alert-generation mechanism.

**Effort: M.**

---

### R3 · Clustered inference for the options book

**The problem.** Every options statistic treats trades as independent. Nothing computes an effective sample size. And the two numbers the headline conclusion rests on are not in the code.

**Method.**

1. Implement a **date-block bootstrap**: resample calendar months (or weeks) with replacement, keeping *all* trades within a sampled block together. Apply it to `expectancy_pct`, to `bootstrap_diff` in the control comparison, and to any tier or bucket comparison.
2. Report `n_eff` — a defensible estimate is the number of distinct entry months, or `n / (1 + (m̄ − 1)·ρ̄)` where `m̄` is the mean trades per block and `ρ̄` the mean within-block return correlation.
3. Put the paired name-year sign test and the paired *t* **into the repository**, with a test, so the headline numbers are reproducible.
4. Add purge and embargo to `pbo_cscv`. A trade entered in an in-sample block is open 30 to 60 days into the adjacent out-of-sample block, and performance is attributed by entry date. Embargo by the maximum holding period.
5. Recompute Deflated Sharpe with `n = n_eff`, not the raw trade count.

**Expect** every options *t*-like quantity to shrink by roughly the square root of the clustering factor. With ~2,700 alert-days across a decade on highly correlated megacaps, a factor of 2 to 4 would not be surprising, which would move a *t* of −5.24 into the −2.5 to −3.7 range. Still significant, but a different-looking result.

**Effort: M.**

---

### R4 · Project-level multiple-testing accounting

The ledger records approximately 146 distinct tests. The Deflated Sharpe uses `N = 8`. Those two facts cannot both inform the same claim.

**Method.** Build a single append-only research log — one row per pre-registered test, with date, hypothesis, universe, metric, threshold, verdict. Populate it retrospectively from the handoff corpus; the ledger work is most of the way done. Then:

- Feed the real `N` into the Deflated Sharpe.
- Apply Benjamini–Hochberg across the family of *equity* signal tests, as the options autopsy already does for its 126 features (and where it correctly found zero discoveries).
- Report the Harvey–Liu–Zhu adjusted hurdle for the number of trials actually run.

**What this buys.** Currently the project cannot honestly claim its statistical bars are cleared, because the bars are computed against a trial count of 8. With a real log it can — and the long-short *t* of 3.52 probably clears a properly-computed hurdle, which is a much stronger claim than the current one *because* it is defensible.

**Effort: M**, mostly clerical.

---

### R5 · The four classic anomalies, killed on an alphabetical subsample

Short-term reversal, idiosyncratic volatility, the MAX effect and low volatility were dismissed in a single clause — "did NOT replicate here" — on the 800-name run, with no per-signal numbers published anywhere in the corpus. Per **B12**, that run was names A through roughly C, not the 800 largest.

This is the weakest-evidenced rejection in the ledger: four separately-documented academic anomalies, one sentence, on a universe the project's own methodology rule forbids deciding on.

**Aggravating detail.** Three of the four are *already computed and already dead in the code*. `neg_ret_1m`, `neg_max_ret` and `neg_idio_vol` are calculated at `fundamental_panel.py:413-440`, assigned in `factors.py:152-154`, and absent from `NUMBER_THEME` — so they have no `z_` column, are invisible to `signal_coverage`, and appear in no IC table. Re-testing them is a three-line change.

**Method.** Register all four in `NUMBER_THEME`, run the full-universe panel, report per-signal median IC, IC *t*, coverage and the correlation matrix against existing themes. Then run any survivor through the held-out gate.

**Pre-registered threshold.** IC *t* > 2.0 standalone and a held-out verdict of `confirmed` to enter a theme. Note in advance that low-volatility and idiosyncratic-volatility are close cousins of the `low_risk` theme that was zeroed for cancelling the small-cap tilt — so a positive result here needs the same size-interaction check before it means anything.

**Effort: S.**

---

### R6 · The SF3 conviction family, also killed on the alphabetical subsample

`sm_conviction` and `sm_avg_position` were rejected in the 800-name era with no published figures. Their surviving sibling `sm_breadth` was flagged as "t 2.37 on 800, unverified on full" and later measured **+1.73** on the full universe — a 27% haircut, in the direction that makes a marginal rejection unsafe.

The three are computed at `fundamental_panel.py:1054-1063` and assigned at `factors.py:169-172`, but are absent from `NUMBER_THEME` — so, contrary to the comment in `settings.py:208` claiming "re-testing is one line," they are not even measured. There is no `z_` column and no IC.

**Method.** Register `sm_conviction`, `sm_holders` and `sm_avg_position`, measure on the full universe, and gate any survivor. `institutional` is one of only two themes with no Fama–French analogue, so it is the theme most likely to carry genuine residual alpha after **R1** — which raises the value of getting its inputs right.

**Effort: XS to register, S to gate.**

---

### R7 · Re-commit the `term_slope` retention floor before re-scoring

This is the thinnest rejection in the corpus. On the 133 names that never informed the threshold, the *economic* arm replicated almost exactly — **+8.89pp out of sample against the +8.12pp that got it adopted** — and it is mildly tail-enriching, retaining 41.2% of the ≥+100% winners while keeping 37.3% of trades. It failed on **one arm only: retention of 36.4% against a 40% floor**. The floor was cleared on the original 55 names by 0.6pp.

The handoff says so itself: "whether a 40% floor is the right bar for a 187-name universe is a legitimate question." This is a live, deployed, independently live-validated filter being marked FAIL on an arbitrary constant.

**Method, and the order matters.** *Before* re-scoring anything: argue from first principles what retention floor is appropriate for a universe of a given size and commit it in writing. The floor exists to prevent a filter from being a disguised cherry-pick of a handful of trades; the sample-size argument for it scales with the number of trades retained, not with a fixed percentage. Then re-score the banked log — but only after **B1**, since `term_slope` on the broad universe is computed from a corrupted spot.

**Effort: XS to re-commit, XS to re-score.**

---

### R8 · Returns are price-only; dividends are on disk and unused

`bulk.py:310` extracts `splits`, `delisted` and `dividends` from ACTIONS. Only `delisted` is consumed. Every forward return in the panel is `close_end / close_start − 1` on the adjusted series, which handles splits but excludes dividend income.

Over a 27-year US equity panel that is roughly 2% per year of missing return, and — this is the part that matters — **it is not distributed evenly across the composite's tilts**. A value-and-quality-tilted book holds more dividend payers than an equal-weighted universe does. So the top decile is losing more return to this omission than the benchmark is, and the top-decile alpha is understated by an unknown amount.

**Method.** Build total-return series from SEP closes plus ACTIONS dividends, re-run, and report the difference. Note that `closeadj` is dividend-adjusted retroactively, which is the wrong basis for point-in-time work but might already be capturing some of this — resolve which series is actually feeding forward returns before assuming a direction. This is worth doing carefully; there is a real risk of double-counting.

**Pre-register:** report gross, and separately report the dividend contribution to the top decile and to the benchmark, so the tilt effect is visible rather than buried in a single number.

**Effort: M.**

---

### R9 · Give the headline metric a t-statistic, and the long-short a HAC one

`top_decile_alpha` ships with no significance statistic at all. This is the number on the front of the product. A sibling function in the same repository already computes exactly what is needed — `valuation/engine/calibration.py:706-708` computes `top_decile_alpha_tstat` from the excess series. Port it.

Separately, the long-short *t* at `fundamental_panel.py:1868-1871` is a naive i.i.d. *t*-statistic. The 63-day windows genuinely do not overlap, so that is defensible on the overlap dimension — but factor spreads are strongly autocorrelated and regime-dependent, and there is no serial-correlation diagnostic anywhere. Add a Newey–West standard error with a small lag and report both, plus the Ljung–Box statistic on the spread series so the assumption is visible rather than implicit.

**Effort: XS.**

---

### R10 · Replace or supplement the uninvestable benchmark

Alpha is measured against the equal-weighted mean forward return of every name in the panel that date — roughly 1,240 names including sub-dollar stocks, rebalanced quarterly, **charged zero trading cost** while the strategy pays. That benchmark cannot be held by anyone.

**Method.** Report top-decile excess return against three benchmarks side by side: (a) the current equal-weight universe, charged the same cost model as the strategy; (b) SPY total return over the same windows, on the 73 dates where it exists and on a full series after **B6**; (c) a cap-weighted panel average, which is the closest investable analogue.

**Expect** the alpha versus a cost-charged equal-weight benchmark to be *higher* than the current figure — the benchmark's own turnover cost is substantial — and the alpha versus SPY to be considerably lower. Both numbers are honest; publish both.

**Effort: S.**

---

# PART III — Stock: new tests

Eighteen items. Ordered roughly by expected value per hour of work. Each assumes Part I is done; several assume **R1** has told you whether you are hunting alpha or engineering exposure.

---

### S1 · Fix the value theme's inputs before adding anything to it

**Observation.** The established (profitable) value branch scores four inputs: `earnings_yield` (IC t +2.41), `fcf_yield` (+3.17), `ebit_ev` (+2.36) and `book_to_price` (**+0.15 at 100% coverage**). Meanwhile `neg_ev_sales` (**+2.05**), `neg_ev_ebitda` (**+1.99**) and `neg_ps` (+1.51) are computed, z-scored, and score only in the speculative branch.

This is a different question from the EV/Sales promotion that was tested and rejected. That test *added* EV/Sales as an additional linear input and the composite worsened on every metric while the theme IC improved 17%. The open questions are narrower and have never been asked:

- **S1a.** Does *removing* `book_to_price` from the established value branch help? It contributes an IC indistinguishable from zero at full coverage — it is diluting three genuinely informative inputs with one uninformative one.
- **S1b.** Does *swapping* `book_to_price` for `neg_ev_ebitda` help? Same input count, so the theme's variance structure barely changes; this is a substitution, not an addition, and it avoids the mechanism that killed the EV/Sales test (a fourth correlated input compressing the theme's cross-sectional dispersion).
- **S1c.** Does the established branch do better with three inputs than four?

**Method.** Three A/B panel runs through `holdout_compare_panels`, one column changed each time. Report the value theme IC, the composite long-short *t*, top-decile alpha, monotonicity and PBO for each.

**Pre-registered threshold.** The existing margins: `MIN_HOLDOUT_ALPHA_GAIN = 0.01`, `MIN_HOLDOUT_TSTAT_GAIN = 0.25`, confirmed in both directions.

**Why this might work where the EV/Sales addition failed.** The diagnostic from that test was explicit — EV/Sales was found to be orthogonal but *uninformative* at the margin (residual t +0.67, R² 15.7%). `book_to_price`'s problem is different: it is not orthogonal-and-uninformative, it is simply flat. Book-to-market has been the weakest of the classic value measures for two decades, and this panel's data agrees.

**Effort: S.**

---

### S2 · Register cash-based operating profitability

`cash_op_prof` is fully computed at `fundamental_panel.py:517-529` as `(revenue − COGS − SG&A − R&D + Δpayables − Δreceivables − Δinventory) / assets`, assigned in `factors.py:151`, and never registered in `NUMBER_THEME`. It has no `z_` column, appears in no IC table, and is invisible to the coverage guard.

This is Ball, Gerakos, Linnainmaa and Nikolaev's cash-based operating profitability — one of the better-replicating quality measures in the literature, and specifically documented to subsume accruals-based profitability. Given that `quality` is already this model's strongest theme (t +3.39) and `gp_on_capital` its strongest single signal (t +4.61), a related but distinct construction is a reasonable prior.

**Note the dead weight it explains.** `cor`, `sgna`, `rnd`, `receivables`, `inventory` and `payables` are all carried in `WRDSProvider._KEEP` *solely* to feed this function. Six columns are loaded on every run to compute a signal nothing consumes.

**Method.** One line in `NUMBER_THEME`. Measure. Gate. Check its correlation against `gp_on_capital` and `fcf_margin` before adding it to `quality` — if it is above about 0.7 with either, test it as a *replacement* rather than an addition, for the same dispersion-compression reason as **S1**.

**Effort: XS.** The single cheapest untested signal in the repository.

---

### S3 · The insider score is constructed in a way that could explain its negative IC

`insider` is the only negative theme in the model (IC t **−0.34**) and it carries one-seventh of the weight. Zeroing it was tested and came back `not_replicated` — Δt of +0.08 in one direction and −0.09 in the other, which is *no evidence in either direction*, not a validation.

Look at the construction (`fundamental_panel.py:740-741`):

```python
net, buys = float(w.sum()), int((w > 0).sum())
return max(0.0, min(100.0, 50 + 40*math.tanh(net / 5e6) + min(10, 2*buys)))
```

The `+ min(10, 2·buys)` term is **unconditionally additive**. A name with five large insider sales and one trivial buy receives a +2 bonus on top of a deeply negative net. The score also saturates: `tanh(net / 5e6)` is effectively flat beyond about $15M of net activity, so a $50M cluster purchase and a $15M one are indistinguishable — while for a $500M company the former is a far stronger signal.

**Three variants to test, each pre-registered:**

- **S3a.** Drop the `buys` bonus entirely. Pure net-dollar tanh.
- **S3b.** Scale net insider activity by market capitalisation before the tanh, rather than by a fixed $5M. This is the standard construction in the literature and it is the more likely of the three to matter.
- **S3c.** Separate the theme into *net buying* and *cluster breadth* as two inputs rather than one blended score, so the composite can weight them independently.

Also worth checking: `_insider_score_at` uses `searchsorted(dts, hi, "right")` at `:736`, so a Form 4 dated exactly `as_of` is usable at that day's close. That is at most one day of optimism, but it is free to fix.

**Note the latent hazard.** Two insider loaders disagree on sign precedence. `fundamental_panel._prep_insider` (`:714-716`) prefers `shares × price`; `bulk.prepare_insiders` (`:382-387`) prefers `transactionvalue` first. If `transactionvalue` is unsigned — as it is in several Sharadar SF2 exports — the bulk path mis-signs every sale as a buy. The panel currently uses the safe path, so the shipped run is fine, but switching to the bulk loader would silently invert the theme.

**Pre-registered threshold.** A variant enters only if its theme IC *t* clears +1.0 **and** the composite improves through `holdout_compare_panels` in both directions. If none does, then zeroing `insider` becomes a live proposal again — but note that the theme covers 85% of rows and is one of only two with no Fama–French analogue, so it is worth one honest attempt at fixing before deleting.

**Effort: S.**

---

### S4 · The growth theme carries zero weight in the entire backtest

`growth` is not a key of `WEIGHTS_ESTABLISHED` (`settings.py:75-77`) and the backtest runs `bucket="established"`. `BACKTEST_RESULTS.json → signals_wired` confirms: the eight scored themes do not include it. So `revenue_growth` (IC t +1.25) and `growth_accel` (+0.50) are measured and never used on profitable names, and the theme's own IC of **t +1.45** — comparable to `value` at +1.47 — is a number about a theme the model does not hold.

That may be deliberate; growth is the weakest of the classic factors and it correlates with momentum. But it is not recorded as a tested decision anywhere in the ledger. It reads as an omission rather than a choice.

**Method.** Add `growth` at the standard weight to `WEIGHTS_ESTABLISHED`, re-run, gate. Then test the opposite: is the *speculative* branch better without it? Report both.

**Effort: XS.**

---

### S5 · Hierarchical shrinkage across themes — the principled replacement for weight tuning

**The problem this solves.** The project has now run eight weight schemes through CPCV on several occasions and CPCV has declined to adopt any of them every single time. That is the right answer to the question being asked, and it means the question is not worth asking again. Weight tuning on 110 quarterly observations across eight themes is noise-fitting and the model correctly refuses to do it.

But there is a better-posed version. Jensen, Kelly and Pedersen (2023, *Journal of Finance*) address exactly this with a Bayesian hierarchical model: signals are grouped into themes, and each signal's expected return is shrunk toward its theme's mean, which is itself shrunk toward a global prior. The amount of shrinkage is determined by the data rather than chosen. Their result — 153 characteristics, 13 themes, 93 countries — is that this framework *strengthens* rather than weakens the evidence for factor replication, precisely because it handles the multiple-testing problem structurally instead of by post-hoc adjustment.

**Why it fits here.** Valquo already has the architecture — theme-level aggregation of correlated signals rather than signal-level selection. The missing piece is that the aggregation is a flat average with fixed weights, when it should be a shrinkage estimator.

**Method.**

1. Estimate each signal's IC mean and variance across the 110 periods.
2. Fit a two-level hierarchical model: signal → theme → global. A simple empirical-Bayes James–Stein estimator captures most of the benefit and needs no MCMC; a full Bayesian version with `numpyro` or `pymc` is a stretch goal.
3. Derive posterior-mean signal weights within each theme, and posterior-mean theme weights.
4. Validate under CPCV against the equal-weight default, exactly as the eight schemes were.

**Pre-registered threshold.** Adopt only if it clears the same CPCV trials-adjusted bar that has rejected every previous scheme. Expect it to be close — the honest prior is that shrinkage lands very near equal weight, which is the *point*: it would provide a principled justification for the equal weighting the model already uses, rather than an arbitrary one.

**Secondary value.** The posterior variances give a defensible confidence interval per signal, which is far more useful for the product's "why this score" surface than a point IC.

**Effort: L.** The most intellectually substantial item in this catalogue.

---

### S6 · Factor momentum on the model's own theme return series

Ehsani and Linnainmaa (2022, *Journal of Finance*) find that time-series factor momentum across 20 factors earns 4.2%/yr with a *t* of 7.04 and Sharpe 0.98; factors that returned positively over the prior year earn 53bps the next month against 1bp after a negative year. Adding factor momentum drives the alpha of individual-stock momentum to zero — stock momentum is *spanned* by factor momentum.

**Why this is well-matched to Valquo specifically.** The project has independently observed that its theme ICs are unstable across time: `low_risk` flips −0.031 to +0.041 between halves, `size` flips t +3.17 to −0.67 (the small-cap premium worked before 2012 and not after). That instability has been treated as a caveat. **It is also the raw material factor momentum trades on.**

**Method.** The theme-level long-short return series already exists inside `quantile_backtest`. For each theme, compute its trailing 12-month (four-period) return. Overweight themes with positive trailing returns, underweight negative, with weights bounded to avoid concentration. Validate under CPCV.

**Pre-registered threshold.** The standard CPCV bar. Cap any single theme at twice the equal weight and floor it at zero, decided before running.

**Important counterweight to record alongside.** Haddad, Kozak and Santosh (2020) find real out-of-sample factor timing (Sharpe 0.87 versus 0.76 static), but Asness's critique — that factor timing is deceptively difficult and most apparent gains are value-timing in disguise — is well-founded. Valquo's own CPCV has consistently declined to time anything. Treat a positive result here with more than usual suspicion, and require it to survive the both-halves gate.

**Effort: M.**

---

### S7 · Pre-registered interactions instead of another tree

The ML tree combiner was rejected decisively: median out-of-sample IC of +0.0393 against the linear composite's +0.0531, and a Roth net alpha of +2.04% against +10.27%. The framing in the handoff is correct — "do not re-open with a different model, re-open only with materially more data." A gradient-boosted model over 110 dates × 8 themes has roughly 880 effective observations and it is being asked to find interaction structure. It cannot.

But two later documents independently name the tree combiner as the remedy for a *different* rejection: the EV/Sales result is described as "a concrete demonstration that a linear composite cannot use a signal whose marginal information is non-linear." Those two positions are in tension, and the resolution is not a bigger model — it is a smaller hypothesis.

**Method.** Test three to five *specific, theory-motivated* interactions as explicit terms in the linear composite, each pre-registered:

- `value × quality` — the "quality-adjusted value" hypothesis; cheap-and-good beats cheap-and-bad. Best-documented of the set.
- `momentum × low_volatility_regime` — momentum crashes are a volatility phenomenon; conditioning on realised market volatility is standard.
- `value × (institutional accumulation)` — cheap names that smart money is buying, versus cheap names it is leaving.
- `size × liquidity` — the small-cap premium conditional on tradeability, which is where Hou–Xue–Zhang locate most anomaly failures.

Each is one added column, z-scored, weighted like any other input.

**Pre-registered threshold.** The standard held-out gate. Bonferroni across the number of interactions tested — with four interactions the effective bar is *p* < 0.0125.

**Why this beats the tree.** Four hypotheses at 880 observations is a tractable estimation problem. Two hundred implicit interactions is not. This is the difference between testing a theory and searching a space.

**Effort: M.**

---

### S8 · Signal-freshness weighting

The project measured 13F decay carefully — it peaks at Q−1, remains alive at Q−2 (*t* 1.36), and is dead by Q−3 (*t* −0.04). That measurement is used for nothing. Every signal enters the composite at full strength regardless of how stale its underlying data is at the rebalance date.

**Method.** Attach an age to each signal at each rebalance: days since the filing that produced it (`datekey`), days since the 13F quarter-end, days since the short-interest settlement date. Apply an exponential decay multiplier with a half-life estimated per signal from its own measured decay curve. Re-run and gate.

**Related defect worth fixing at the same time.** DAILY is down-sampled to **month-end** in `bulk.py:186-188`, so the "point-in-time market cap" and the re-priced EV equity leg can be up to 31 calendar days stale — while the price feeding `_price_factors` is same-day. The `_pit_ev` docstring claims it is "priced at the REBALANCE date"; it is priced at the preceding month-end. Given that the EV point-in-time fix moved EV by a median 5.1%, a month of staleness in the equity leg is the same order of magnitude as the thing that fix corrected.

**Effort: M.**

---

### S9 · Fundamental-data staleness as a conditioning variable

The panel rebalances on a fixed 63-trading-day calendar grid. Filing dates are not on that grid. So at any rebalance, some names last reported three days ago and some last reported eighty-nine days ago, and the composite treats those identically.

**Hypothesis.** The cross-sectional signal is stronger for names whose fundamental data is fresh, and decays for names approaching their next report — both because the data is more current and because the market has had less time to price it.

**Method.** `days_since_filing` is already computed in the options autopsy as `f_days_since_filing`. Port it to the equity panel, then split the top decile by staleness quartile and report forward returns per quartile. If a gradient exists, test it as a weight multiplier.

**Why this is attractive.** It requires no new data, is orthogonal to every existing theme by construction, and — unusually for this catalogue — has a clean mechanical story rather than a statistical one. It is also directly actionable in the product: "this score is based on data from 4 days ago" versus "89 days ago" is exactly the kind of honest qualifier the project's positioning is built on.

**Effort: S.**

---

### S10 · A downside-exclusion screen

Listed in `VALQUO_NEXT_EDGE.md` Tier 2 and never built.

**The argument for it.** For a long-only concentrated book, an *exclusion* screen is the cheapest form of edge available, because it does not need to beat anything — it only needs to avoid a small number of catastrophic outcomes. A 25-name book that avoids one −90% name per year gains roughly 3.6% of book value, which is a third of the claimed top-decile alpha, for a screen that requires no forecasting skill at all.

**Components, all computable from SF1 already on disk:**

- **Beneish M-score** — the eight-variable earnings-manipulation index. Well documented, cheap, and specifically designed for exclusion rather than ranking.
- **Altman Z-score** — distress. The model already has `interest_cov` and `neg_leverage` but no composite distress measure.
- **External financing** — the combined debt-and-equity issuance measure. `neg_issuance` covers the equity leg only.
- **NT filings** (late-filing notifications, forms NT 10-K / NT 10-Q) from EDGAR — free, and among the strongest single red flags in the accounting literature.

**Method.** Compute all four. Rather than adding them as ranked signals, test them as a **veto**: exclude any name flagged by two or more, then re-run the decile backtest on the surviving universe. Report the alpha change, the drawdown change, and — the number that matters most — the count and identity of the excluded names that subsequently fell more than 50%.

**Pre-registered threshold.** Adopt if maximum drawdown improves by more than 2 percentage points *and* top-decile alpha falls by less than 1 percentage point. Note this is deliberately asymmetric: a small return give-up for a real tail improvement is a good trade for a concentrated book.

**Effort: M.**

---

### S11 · Horizon ensemble

Three horizons are tested — 63, 252 and 756 trading days — and only 63 is accepted. But the per-horizon results are treated as competing candidates, when a blend is a different object entirely.

**Method.** Compute the composite rank at 63 days and at 252 days, average the ranks, and backtest the blend at the 63-day rebalance. Signals that predict at both horizons get reinforced; signals that predict at only one get diluted. This is a well-established way to reduce noise in cross-sectional ranking without adding any new information.

**Pre-registered threshold.** Standard held-out gate. Also report the turnover — a blend with a slower component should reduce turnover, which compounds with **S14** and the cost work.

**Effort: S.**

---

### S12 · Rank within bucket, not across

`factors.py:206` splits value by bucket — established names score on `earnings_yield`/`fcf_yield`/`ebit_ev`/`book_to_price`, speculative names on `neg_ev_sales`/`neg_ps`/`book_to_price`. But the resulting single `value` column is then z-scored **across the whole cross-section**, mixing two different factor definitions, and one weight vector is applied to both.

**Hypothesis.** Ranking should happen within bucket, with the deciles formed by combining the two ranked sets — otherwise the z-score of a speculative name's `neg_ev_sales` is being compared to the z-score of an established name's `earnings_yield` as though they were the same quantity.

**Method.** Add a `bucket_relative` toggle to the standardisation step, run the panel with it on and off, and gate. This is architecturally the same as the sector-neutral toggle that already exists and is already tested, so the plumbing is proven.

**Note the connection to the rejected sector-neutral test.** That rejection was specific and well-reasoned: neutralising by sector bought long-short *t* and sold top-decile alpha, which is the wrong trade for a long-only book. Bucket-relative ranking is a different intervention — the buckets are defined by *how a name is valued*, not by industry — and the failure mechanism does not obviously carry over. But run it expecting the same shape of result, and use the same metric priority: top-decile alpha decides, not the *t*-statistic.

**Effort: S.**

---

### S13 · Volatility-targeted weighting inside the book

The book is equal-weighted within the decile. A signal-weighted variant is computed and reported but not deployed.

**Method.** Test three weighting schemes at the 25-name book level: equal weight (current), inverse-volatility, and inverse-volatility capped at 2× the equal weight. Report CAGR, Sharpe, maximum drawdown and turnover for each.

**Expect** a Sharpe improvement and a drawdown improvement with a small return give-up — that is the standard result, and it is one of the few in the literature that replicates almost everywhere. Note that it will interact with the removal of `low_risk`: the composite no longer has any volatility awareness in the *selection* step, so putting it in the *sizing* step is a natural complement rather than a duplication.

**Effort: S.**

---

### S14 · Re-decide the no-trade band on the deterministic-cost argument

The no-trade band failed on one half (+0.60% early against a +1% floor) while passing on the other (+1.88%). It is positive in both halves and never hurts — unlike sector-neutral or zeroing `insider`, each of which hurt in one direction. It is currently live in the `taxable` configuration only.

**The argument for re-opening.** Turnover falls from 251% to 172%. That is *arithmetic*, not an estimated signal. The cost saving is deterministic in a way that a signal's IC never is, and the margin it failed was calibrated for signals. Applying a signal-strength threshold to a mechanical cost reduction is a category error.

**A caveat that cuts the other way.** The width surface is noisy — 15% is worse than both 12% and 20% on gross alpha, which should not happen on a smooth tradeoff. That suggests the sweep is picking up noise, and that the "knee" is not well identified.

**Method.** Re-run the width sweep after **B13** (with `prefilter` active, so the book is investable) and after **B11** (so the realised cost is measured, not assumed). Then decide on **net** alpha rather than gross, which is the quantity the band exists to improve. Pre-commit the decision rule: adopt the width that maximises net-of-cost top-decile alpha, provided it does not reduce gross alpha by more than 1.5 percentage points.

**Effort: S.**

---

### S15 · Sector-relative on the value theme only

Named in the project's own record as "the only version worth re-opening" after the wholesale sector-neutral rejection. It is a one-parameter experiment and the wiring is already pinned by `tests/test_sector_neutral.py`.

**The rationale.** Value is the theme where cross-sector comparison is least meaningful — a bank's book-to-price and a software company's are not the same quantity, and the value theme is the one whose raw ratios are most sector-determined. Quality and momentum travel across sectors far better.

**Method.** Apply sector-relative z-scoring to the `value` theme's inputs only, leaving every other theme cross-sectional. Gate.

**Carry the standing caveat.** Sharadar TICKERS gives *today's* sector classification applied to 1998 rows. That is a mild look-ahead and the one non-point-in-time input in the panel — a reason to be more sceptical of a positive result, not less.

**Effort: XS.**

---

### S16 · Decompose net issuance

`capital_discipline` has exactly one input: `neg_issuance = −(shares_t / shares_{t−365d} − 1)`, from `sharesbas`. That is a net number, and it conflates two economically opposite events — a buyback and a secondary offering — with two other things that are not capital decisions at all: shares issued for acquisitions, and employee stock compensation dilution.

**Method.** ACTIONS is already on disk and already parsed for delistings. Extract buyback announcements and dividend initiations, and separate the share-count change into repurchase, issuance, and other. Test each as its own signal, then as separate inputs to `capital_discipline`.

Buyback-announcement drift and dividend-initiation drift are both classic, well-documented, and cheap here because the data is downloaded and unused. Note that `capital_discipline` currently has only one input, so it is the theme most likely to benefit from a second — the theme mean of a single signal is just that signal.

**Effort: M.**

---

### S17 · Decode the rest of the EVENTS table

`bulk.py:255` extracts every `eventcode` per ticker. Only code **22** (earnings) is consumed. Codes 11, 34, 52, 57, 71, 81, 91 and others are parsed, cached and discarded.

The 8-K event stream runs from 1993 and is the cheapest structured corporate-event source the project owns. Getting the legend and testing the highest-frequency codes as catalyst or red-flag signals is a contained piece of work with an unusually good data-cost-to-optionality ratio.

**Method.** Obtain the code legend from Sharadar's documentation (do this *before* the subscription lapses — see **D10**). Tabulate frequency by code. Test the five most frequent as event-window signals: forward return over 21 and 63 days conditional on an event of that type in the trailing 21 days.

**Pre-register that most will be noise**, and apply Benjamini–Hochberg across however many codes are tested — this is exactly the kind of sweep that produces spurious discoveries without FDR control.

**Effort: M**, gated on documentation availability.

---

### S18 · Short interest as an interaction, not a standalone

`neg_days_to_cover` (IC t +1.04) and `neg_short_interest_chg` (+0.42) were tested standalone against a 2.0 bar on a 2018-onward window and rejected. The FINRA data is free, already built at `data/bulk/prepared/short_interest.pkl` (3.87M rows, 48,539 tickers), and covers 40% of the panel dates.

**The reason to re-open it in a different form.** Short interest is not a return predictor on its own in most modern samples — that effect has largely decayed. It is a *crowding* measure, and crowding conditions other signals. A cheap-and-heavily-shorted name is a different proposition from a cheap-and-lightly-shorted one, and the same is true for momentum.

**Method.** Test `value × short_interest` and `momentum × short_interest` as interaction terms in the sense of **S7**, rather than as standalone inputs. Also test short interest purely as an *exclusion* in the sense of **S10** — drop the top 5% most-shorted names from the book and measure what happens to drawdown.

**Pre-registered threshold.** Standard held-out gate; Bonferroni across the interactions tested. Note that coverage is 40% of dates, so this is structurally a partial-sample test and must be labelled as such.

**Effort: S.**

---

# PART IV — Options: new tests

Eighteen items. The framing that makes this part worth doing is the project's own: if the entry signal is dead, then an options edge — if one exists — is in the **exit**, the **sizing**, the **cross-section of which options**, or a **different strategy family**. The catalogue below works those four corners, plus one that the project's own sweep does not cover: the surface as a *stock* predictor, which is deferred to Part V because it belongs with the model that works.

One asset dominates the economics here. There are roughly **8 GB of derived option surface** — implied vol, thirteen greeks through third order, gamma exposure geometry, skew, term structure, IV rank — across 111 names (and a raw cache now at ~370) over ten years, at 263,698 name-dates. The **only** use ever made of it is 64 entry features on one strategy, tested twice, both times null. A cross-sectional option-return study is an entire research programme on data that is already paid for and sitting on disk.

---

### O1 · Exit optimisation — the project's own number-one, now unblocked

**Why it is the highest-value item here.** Every result to date uses one fixed exit: +100% take profit, −50% stop, exit at half the original DTE. For a convex long-option payoff the exit frequently *is* the edge. And critically, this test is **independent of the dead entry** — if an exit rule improves outcomes even on random entries, the edge is located in the exit.

**Prerequisite.** **B2** and **B3** must land first. The current exit path skips days whose quote is wide or thin, which is exactly where the stop should fire, and books expiry at a possibly-weeks-old quote. Sweeping exits over a censored path measures the censoring.

**The good news on effort.** `simulate_trade` already accepts `target_pct`, `stop_pct` and `time_stop_frac` as arguments (`options_backtest.py:299`). No caller passes them. A three-dimensional sweep is one keyword argument away.

**Method — run each variant against both the real entries and the random-entry control:**

| Dimension | Grid |
|---|---|
| Take profit | 50 / 75 / 100 / 150 / 200% / none |
| Stop | −30 / −40 / −50 / −60% / none |
| Time stop | 25 / 33 / 50 / 67% of original DTE |
| Trailing stop | none, and give-back of 25 / 40% from peak mark |
| Scale-out | none, and half at +75% with the remainder to a trailing stop |

**The key comparison**, stated in advance: *random entry + candidate exit* versus *random entry + current fixed exit*. If a rule wins on random entries, it is an exit edge and it is real. If it only wins on the signal entries, it is an interaction with the signal — interesting but much weaker evidence, and it must clear the held-out gate separately.

**Pre-registered thresholds.** Report expectancy under a date-block bootstrap (**R3**), not a naive mean. Adopt only a rule that improves expectancy in both held-out halves and does not concentrate the result further in the top 15 trades (the tail-share metric already exists).

**What to watch for, and it is the central tension.** The book's return is convex and 30.7% of trades return ≥ +100%. Banking early at +50% will raise the hit rate and almost certainly *lower* expectancy by clipping the tail that carries the book. The interesting candidates are therefore the ones that cut losers faster or trail winners further, not the ones that take profit sooner. Pre-commit to judging on expectancy, not on hit rate — the project already has this discipline in its confidence display and should carry it here.

**Also worth adding to the sweep, and untested anywhere:** an exit conditioned on the *underlying* rather than the option — close if the stock breaks its 50-day moving average, or if the technical score that generated the alert drops below a threshold. The exit loop currently sees only option quotes. This is the one variant that uses information the current exit is structurally blind to.

**Effort: M.**

---

### O2 · Cross-sectional variance risk premium — Goyal–Saretto

**The literature.** Goyal and Saretto (2009, *JFE* 94(2), 310–326): sort stocks on the difference between historical realised volatility and at-the-money implied volatility. A zero-cost strategy long the large-positive-difference portfolio and short the large-negative earns an economically and statistically significant monthly return, robust to market conditions, stock characteristics, industry, option liquidity and standard factor models. This is the most implementable cross-sectional option result in the literature and it needs only ATM implied vol and a realised-vol estimate.

**Why Valquo is unusually well placed.** `atm_iv_30` per name-date is already computed and shipped in `<SYM>-daily.pkl`. `_realized_vol` already exists at `options_universe.py:190-200`. The join is one function. And `data/options/atm_iv_series.pkl` holds 137,418 observations across 55 names on *every* trading day, not just alert days — built to make `iv_rank` testable, used once, and described in the record as "reusable for any vol-regime read." Nothing else has ever used it.

**Method.**

1. For every name-date, compute `IV30 − RV_hist` where the realised vol is measured over a matched window.
2. Rank cross-sectionally each month. Form quintiles.
3. Measure returns to a long-only position in the highest quintile (cheap implied vol) — the long-only version is what an IRA can hold.
4. Also measure straddle returns and delta-hedged returns per quintile, which is the paper's construction.
5. Net of the honest fill model (touch on both sides), and separately under a passive-limit model (**O10**).

**Pre-registered thresholds.** Quintile monotonicity in the correct direction; long-short *t* > 2.0 under a date-block bootstrap; positive in both held-out halves. And — this is the one that will bind — the effect must survive the spread. The project has already measured that the market takes 6.59 percentage points of a ~11.7% gross edge at the touch.

**Effort: M.** The highest-value new options item after **O1**.

---

### O3 · Delta-hedged option returns versus idiosyncratic volatility — Cao–Han

**The literature.** Cao and Han (2013, *JFE* 108(1), 231–249): delta-hedged equity option returns decrease monotonically in the underlying's idiosyncratic volatility. Long low-ivol, short high-ivol delta-hedged calls earns roughly **1.4% per month**, equal-weighted, significant after standard risk controls, robust across calls and puts. The mechanism is that constrained intermediaries charge more for options that are harder to hedge.

**Feasibility here.** Delta-hedged returns need a daily delta and a daily underlying price. Both exist — the derived layer carries `delta` per contract-day and `spot`. Daily rebalancing of the hedge is exactly what EOD data supports.

**Method.** Compute idiosyncratic volatility per name (residual from a market-model regression; the panel already computes betas at `fundamental_panel.py:421-436`). Sort into quintiles. For each, compute the return to a delta-hedged ATM call held one month with daily hedge rebalancing at the closing spot. Report per quintile, net of the hedge's own transaction costs on the underlying.

**Important caveat to record before running.** A delta-hedged option position is not something this account will trade — it requires daily equity rebalancing and the transaction costs on the hedge leg are real. The value of this test is **diagnostic**: it tells you whether the options this book buys are systematically rich or cheap *conditional on a characteristic you can observe at entry*, which then becomes a contract-selection rule (**O6**) rather than a strategy of its own.

**Effort: M.**

---

### O4 · Expected idiosyncratic skewness — Boyer–Vorkink

**The literature.** Boyer and Vorkink (2014, *Journal of Finance*): ex-ante idiosyncratic skewness is strongly negatively related to option returns. The low-minus-high skewness spread is reported at **10 to 50 percent per week** across option portfolios after risk adjustment. The mechanism is that intermediaries earn a premium for bearing unhedgeable risk from investor demand for lottery-like payoffs.

**Read the magnitude correctly.** Those are gross returns on hugely levered raw option positions, against an average retail option spread documented at 12.6% (Bryzgalova, Pavlova and Sikorskaya 2023). **Treat this as a hurdle, not an opportunity.** Its practical value is as a warning: the options this book buys — out-of-the-money calls on high-momentum names near 52-week highs — are precisely the lottery-like contracts the paper identifies as systematically overpriced.

**That is worth testing directly.** If Valquo's scream-buy alerts concentrate in high-expected-skewness names, that is a candidate structural explanation for why the entry loses to random entry — and it would be a mechanism, not just a number, which is what the autopsy has been missing.

**Method.** Build the Boyer–Vorkink expected-skewness measure (a cross-sectional regression predicting future idiosyncratic skewness from current characteristics — the specification is in the paper). Rank names. Then test two things: whether option returns decline in expected skewness on this panel, and whether the alert population is skewed toward high-expected-skewness names relative to the universe.

**Effort: L.** The measure itself is the work.

---

### O5 · Volatility of volatility — Ruan

Ruan (2020, *Journal of Financial Markets* 48): VOV, defined as the standard deviation of 30-day ATM implied vol divided by its mean, has a significantly negative relation to option returns. The long-lowest-VOV / short-highest-VOV spread earns about 0.16% held to maturity. Small, but it survives extensive controls.

**Cost to test here: near zero.** `atm_iv_30` is already a shipped column. VOV is a rolling standard deviation over it. This is a half-day test.

**Method.** Compute rolling 60-day VOV per name from `atm_iv_30`. Quintile-sort. Report option returns per quintile. Then test it as a **contract-selection conditioner** on the existing book rather than as a standalone strategy — which is the form in which a 0.16% effect could actually matter, since it would be applied on top of an existing position rather than traded for its own sake.

**Effort: XS.**

---

### O6 · Replace mechanical 35-delta selection with cheapest-on-surface selection

**The observation.** `pick_contract` chooses the contract whose delta is nearest 0.35 among those in the 45–75 DTE band and the 0.90–1.20 moneyness band. That is a *mechanical* rule with no view on whether the contract is cheap. Two contracts with identical deltas can have materially different implied vols relative to their own history, relative to the name's term structure, and relative to peers.

**This is the single most direct way to convert Part IV's cross-sectional results into money**, because it improves an existing book rather than proposing a new one, and it does not require the entry signal to work.

**Method.** Keep the entry signal and the exit exactly as they are. Change only the contract choice, testing four rules against the current one:

- **O6a.** Among candidates within ±0.05 delta of target, pick the lowest implied vol.
- **O6b.** Among candidates, pick the lowest IV *relative to that name's own trailing IV rank* — a within-name cheapness measure rather than a cross-name one.
- **O6c.** Pick the lowest IV relative to the fitted smile — i.e. the contract that is cheap relative to the surface it sits on, which is the ORATS "smoothed market value" idea implemented locally.
- **O6d.** Pick on the ratio of vega to spread cost — the most theta-efficient expression of the same directional view.

**Pre-registered threshold.** Expectancy improvement in both held-out halves under a date-block bootstrap, with no increase in tail concentration.

**Why this is attractive.** It is a strictly-better contract-selection rule if any of the cross-sectional results in **O2**–**O5** hold, it is cheap to implement, and it applies to the live book immediately. It also cleanly separates "which name" (the dead signal) from "which contract" (never tested).

**Effort: S.**

---

### O7 · Earnings straddles — and note the sign is opposite to the folklore

**The literature.** Gao, Xing and Zhang (2018, *JFQA* 53(6), 2587–2617): ATM straddles bought **three days before** an earnings announcement and held through it earn **+3.34%**, highly significant. Stronger for smaller firms, higher volatility, higher kurtosis, more volatile past earnings surprises, and lower trading volume.

**Read that carefully, because it inverts the retail consensus.** The published finding is that pre-earnings straddles are *underpriced* — the implied move systematically undershoots the realised one. That is the opposite of "sell the IV crush." The project's roadmap item #24 frames earnings as an IV-crush opportunity; the literature says the tradeable side is the other one.

**Feasibility.** Sharadar EVENTS code 22 is already decoded and already used by the VRP arm. The surface has ATM IV. Straddle construction from the chain is straightforward. This is directly implementable today.

**Method.**

1. For each name-earnings-date, compute the **implied move** as the ATM straddle price divided by spot, and the **realised move** as the absolute return over the announcement window.
2. Report the distribution of realised-minus-implied, pooled and by market-cap tier. This alone is a valuable diagnostic and settles whether earnings moves are rich or cheap on *this* universe.
3. Backtest the paper's construction: buy the ATM straddle three days before, close the day after, net of the honest fill model on both legs.
4. Test the conditioners the paper identifies — firm size, past earnings-surprise volatility, option volume.

**Pre-registered thresholds.** Positive expectancy net of two round-trip spreads (a straddle crosses four times), in both held-out halves, under a date-block bootstrap clustered by earnings date. Straddles on the same day across names are heavily correlated through the market factor, so the clustering matters more here than anywhere else in this catalogue.

**Expect the spread to be brutal.** A straddle pays the bid-ask twice on entry and twice on exit. At the project's measured spread cost — 6.59 percentage points on a single leg — a +3.34% gross effect does not obviously survive. Run it anyway: the *diagnostic* in step 2 is worth the run regardless of the strategy result, and it is the cleanest possible test of whether this universe's options are systematically rich or cheap.

**Secondary and cheaper.** The long arm currently has **no earnings filter at all** (`optbt_run.py`, `options_universe.py`). The VRP arm had one. A rule of "do not open a new long position within N days before an announcement" is a one-line test, and the loser autopsy already flagged buying into an IV crush as a plausible loss mechanism. See **O17**.

**Effort: M.**

---

### O8 · The variance risk premium on index options — and run the backtest that already exists

**The state of the evidence.** The single-name put-credit-spread arm was rejected decisively and correctly: −7.99% per trade, profit factor 0.28, negative in nine of ten years, 2,496 trades. But the rejection's scope is narrower than it reads.

Three things bound it. First, the arm was entered **conditionally on IV rank ≥ 0.50** (`optvrp_run.py:214-223`) — it was never an always-on strategy, and the low-IV-rank half of the sample was never generated at all, because `IV_RANK_MIN` is not environment-overridable. Second, exactly one parameterisation was tested: 20-delta short, fixed $5 width, 25–50 DTE, 2× credit stop, single-name, retail touch fills. Third, and most importantly, the *measured mechanism* of the loss is execution — roughly **$28 of a ~$65 mid credit is consumed crossing two spreads twice**. The mid-fill ceiling is a profit factor of 1.02, i.e. break-even.

That last fact is what makes index options the natural next test rather than a re-parameterisation of single names. On SPY and QQQ the bid-ask is a fraction of single-name, which attacks the measured killer directly. The project's own handoff says exactly this: "if short vol is revisited at all, the honest place to start is index options, where the bid-ask is a fraction of single-name and where the bot's own free-data backtest already lives."

**And that backtest exists and has never been run.** `options-bot/options_backtest/backtest_engine.py` implements SPY/QQQ/IWM put credit spreads with real historical implied vol from the VIX family (VIX→SPY, VXN→QQQ, RVX→IWM — correctly, since the edge *is* the implied-versus-realised gap so realised vol must not be substituted), conservative slippage and commissions, explicit stop gap-through, a full equity curve, cash accounting, a ruin halt, concurrency caps, vol-scaled sizing, and a risk-free-subtracted Sharpe. It runs on free Stooq data. The command is in the handoff:

```
python run_options_backtest.py --etf SPY --start 2018-01-01 --end 2025-12-31
```

**No result from it appears anywhere in the corpus.**

**Method.** Run it. Then, if the result is not obviously negative, port the arm to real index option chains rather than Black–Scholes reconstructions — the single IV per name-date with no skew and no term structure is described in that engine's own docstring as "the biggest modelling hole," and for a strategy that sells 20-delta puts the skew *is* the trade.

**One critical caveat to carry.** Dew-Becker et al. (Chicago Fed working paper 2025-17) document that the **index variance risk premium has declined** in the 2020s. Anyone sizing a VRP strategy off 1996–2015 numbers is fitting a regime that has changed. Restrict the primary test window to 2018 onward and report the pre-2018 period separately.

**Effort: XS to run the existing backtest. M to do it properly on real chains.**

---

### O9 · IV rank as a sell-timing rule, which is not how it was tested

`iv_rank` has been rejected three times — but always as a **filter on a long-vol strategy**, i.e. "buy calls only when IV rank is low." It has never been tested as a **sell-timing rule**: "sell premium only when IV rank is high, and otherwise do nothing."

Those are different hypotheses. The first asks whether cheap vol predicts good long-option outcomes. The second asks whether expensive vol predicts good short-option outcomes. The VRP arm's IV-rank ≥ 0.50 condition is closer to the second but was applied as a floor on an otherwise always-on strategy, and the arm's own banding shows the effect running the *wrong* way inside the admitted range — 0.50–0.65 gives −6.24%, 0.65–0.80 gives −8.16%, ≥0.80 gives −9.45%.

That monotone worsening is genuinely informative and it argues against the hypothesis. But it is measured inside a strategy whose base rate is negative because of execution, so it cannot separate "high IV rank is bad for short vol" from "high IV rank names have wider spreads."

**Method.** On index options, where execution is not the binding constraint (**O8**), test IV rank as an on/off switch: hold premium only in the top tercile of the index's own trailing IV rank, and hold cash otherwise. Report the conditional expectancy and the fraction of time invested.

**Pre-registered threshold.** If the effect does not appear on index options where the spread is small, close the question permanently.

**Effort: S**, contingent on **O8**.

---

### O10 · A passive-limit fill model with non-fills

**The gap.** Every options result uses `aggression = 1.0` — buy the ask, sell the bid. The aggression parameter interpolates between mid and touch on a *guaranteed* fill. It does not model a resting limit order that sometimes does not fill, which changes the **sample**, not just the price.

**Why this matters more than it sounds.** Muravyev and Pearson (2020, *RFS* 33(11), 4973–5014) decompose S&P 500 option trading costs: quoted half-spread 11.6% of option price, conventional effective half-spread 9.2%, adjusted effective 7.1%, and the "algo half-spread" — the true cost after removing execution-timing gains — **4.7%**. Roughly 37–42% of traders benefit from timing. Against that, Bryzgalova et al. document a **12.6%** average spread for retail crossing on cheap weeklies.

Both are true. The cost is ~4.7% of premium if you work orders patiently in liquid names and ~12.6% if you cross the spread. Valquo's backtest assumes the latter on both sides of every trade. That is admirably conservative — and it means **the project has never measured what its own edge looks like under achievable execution.**

**Method.** Implement a limit-order model: place at mid, or mid plus a fraction of the half-spread; fill only if the next day's quote crosses the limit; expire unfilled after N days and record it as a non-fill. Report expectancy, fill rate, and — critically — whether non-fills are *adversely selected* (i.e. whether the trades you fail to get are the ones that would have won).

**Pre-register the interpretation.** This is not licence to quote a better number. It produces a *range*: touch fills as the floor, patient limits as the ceiling, with the adverse-selection measurement telling you where in the range reality sits. Publish the range.

**Effort: M.**

---

### O11 · The single-leg book has no portfolio layer at all

**The defect.** The scream-buy book has no capital constraint, no concurrency limit, no cash accounting and no equity curve. `to_alert_row` records P&L at one contract; `_stats.cum_pnl_dollars` sums it. "Profit factor 1.30" says nothing about whether the strategy is survivable, because there is no drawdown series to survive.

**The irony worth noting.** `options_vrp_portfolio.py` implements exactly what is missing — Ledoit–Wolf shrinkage sizing, concurrency caps, per-ticker limits, deployed-capital caps, a marked-to-market equity curve, and correlation-aware vol targeting. It was built for the VRP arm, which died. It has **never been applied to the arm that lived**. And the older `options-bot` engine has a full equity curve, cash, ruin halt and margin-breach counter that the newer engine lacks.

**Method.** Apply the existing portfolio layer to the single-leg book. Report the equity curve, maximum drawdown, longest drawdown duration, and time-to-recovery, at several concurrency and capital-deployment settings.

**Pre-register that this could reverse the verdict in either direction.** A convex strategy with a 37% hit rate and heavy tail dependence can be perfectly good on per-trade expectancy and completely unsurvivable at realistic sizing — or it can turn out that the diversification across names smooths it more than expected. Nobody currently knows, because the number has never been computed.

**Effort: S.** The layer already exists.

---

### O12 · Fractional Kelly and risk of ruin on the actual distribution

Listed as `OPTIONS_DEEP_RESEARCH` #7 and never started. The book has a 37% hit rate, an average win near +120%, an average loss near −55%, and a fat right tail. Sizing is currently a flat $1,000 risk budget per trade with whole contracts.

**Method.** Fit the empirical trade-return distribution. Compute the full-Kelly fraction, and the growth-versus-drawdown frontier at fractions from 0.1 to 1.0 of it. Compute risk of ruin at each, and the drawdown distribution by simulation using **date-block resampling** so correlated cohorts stay together — this is essential, because independent resampling will dramatically understate drawdowns for a strategy whose losers cluster in calm markets and whose winners cluster in volatility events.

**Deliverable.** A single recommended risk fraction with an explicit statement of the drawdown it implies at the 95th percentile. This is the number that turns "positive expectancy" into "an amount to actually trade," and it is currently missing.

**Effort: S.**

---

### O13 · The anti-signal test

If the scream-buy genuinely picks worse-than-random entry days, the mirror is informative. Not as a trade — but as a falsification.

**Method.** After **B1**, test the inverse: buy the same contracts on alert days for names in the *bottom* technical decile, or short the alert (which the account cannot do, but which can be measured). Also decompose the −8.08pp gap: how much is spread (alert-day contracts may be wider), how much is IV level (alert days may follow a run-up that has pumped the implied vol), and how much is genuine timing?

**Why this is the right diagnostic.** A real anti-signal is as interesting as a signal, and much more likely to be an artefact. If the gap decomposes mostly into IV level — buying calls after a momentum run means buying implied vol that has already expanded — then the finding is "the signal buys expensive options," which is fixable through contract selection (**O6**) rather than fatal. If it decomposes into genuine timing, the signal is dead and the project should say so and move on.

The project's own in-flight entry-fix work is asking a version of this question. Fold it into the same run, after **B1**.

**Effort: S.**

---

### O14 · Tick flow, alert-days only

**The one options signal untested purely on cost rather than on evidence.** `option_history_trade_quote` pairs trades with the prevailing quote — exactly what aggressor-side classification needs. A full historical pull was measured at 1,537–1,957 hours. But an **alert-days-only** pull was costed at approximately 1,841 alerts × 6.4 seconds ≈ **3.3 hours**.

That is one overnight run for the only unexplored feature family in the options programme.

**Method.** Pull alert-day trade-and-quote data. Classify aggressor side by the standard Lee–Ready rule. Construct: signed volume, sweep detection (multiple exchanges within a short window), block detection (size relative to the contract's own average), and the ratio of aggressive-buy to aggressive-sell premium. Test these through the existing autopsy harness.

**Pre-registered threshold.** The same gate every other feature faced, and Benjamini–Hochberg across however many features are constructed. The autopsy has found zero discoveries across 126 hypotheses twice; expect the same and run it anyway, because it is the last unexplored corner and it is cheap.

**A note on what the literature actually supports.** Pan and Poteshman (2006) found that buyer-initiated, open-interest-increasing put-call ratios predict next-day returns — but they used proprietary CBOE data with participant identification. Bryzgalova et al. (2023) used wholesaler flags to identify *retail* option flow and found retail is over 60% of options volume, concentrates in cheap weeklies at 12.6% spreads, and **loses money on average**. So signed retail flow is a **fade** candidate, not a follow candidate. Public tick data cannot separate the two populations. Build the features, but expect the sign to be ambiguous, and see **D6** for the one dataset that can separate them.

**Effort: S plus one overnight pull.**

---

### O15 · The 90-day mining ceiling forecloses an entire strategy space

`theta_bulk.MAX_DTE = 90` is a mining decision, pinned by a test to `BAND["max_dte"] = 90` in the derived layer. Consequently: no LEAPS, no calendars, no diagonals, no 6-month structures — and `atm_iv_90` and `atm_iv_180` came back 99.9% and 100% empty when tried.

**Why this matters now.** Part V proposes pairing the 63-trading-day equity signal with a long-dated option expression. Sixty-three trading days is about 92 calendar days. **The natural tenor for that pairing sits exactly at the mining boundary and slightly beyond it.**

**Method.** Re-mine a focused subset — the 50 to 100 most liquid names — at `MAX_DTE = 200`. Estimate the cost first from the existing throughput figures (mean 5.4 minutes per name-decade at 90 DTE; the row count scales roughly with the number of listed expiries, so budget 2–3×). Then test: does a 120–180 DTE expression of the same directional view outperform a 45–75 DTE one, net of the wider spread on longer-dated contracts?

**The prior is favourable and worth stating.** Longer-dated options have lower theta decay per day, lower gamma (so less sensitivity to the entry-timing problem that appears to be killing the current book), and a much longer window for a fundamental thesis to play out. If the entry signal's problem is timing — and the random-entry control suggests it is — then a longer tenor mechanically reduces the cost of bad timing. This is the single most plausible route to rescuing a long-option book whose entry timing does not work.

**Effort: M plus mining time.**

---

### O16 · Is `term_slope` actually a front-end implied-vol level?

`term_slope = atm_iv_60d − atm_iv_front`, where the front expiry is the *very next* one — median **3 DTE** on the names checked. A 3-DTE ATM implied vol is enormously more volatile than a 60-day one, so the *variance* of `term_slope` is dominated by the front leg. And the autopsy measured `f_entry_iv` at **−0.479** rank correlation with `term_slope` — "low IV goes with contango."

**The decisive test has never been run: `atm_iv_front` alone as a filter.** `f_entry_iv` was tested and failed, but that is the *contract's* implied vol at 45–75 DTE, which is a different variable.

**Why this matters.** `term_slope` is the only surviving options signal in the entire programme. If it is a proxy for "the front-month implied vol is low," that is a simpler, more robust, and more interpretable filter — and it would change how it is computed live, since a single ATM IV read is far less fragile than a difference of two solves on a sparse ladder.

**Method.** Three filters, same harness, same gate: (a) `atm_iv_front` alone, (b) `term_slope` as currently defined, (c) `term_slope` computed against a 14-day rather than a 3-day front leg. Report retention, expectancy gain and tail behaviour for each. Also test the second-order question: is the signal picking up **earnings proximity**? A near-dated announcement lifts the front expiry's implied vol, producing backwardation and a suppressed alert. Sharadar EVENTS code 22 is a far better instrument for that than the filing dates the autopsy used, and it is already decoded.

**Effort: S.**

---

### O17 · The long arm has no earnings filter

The VRP arm excluded windows containing an announcement. The long arm excludes nothing. The loser autopsy flagged buying into an implied-vol crush as a plausible loss mechanism and it was never tested directly.

**Method.** Using EVENTS code 22, test three rules on the banked log: no new position within 5 / 10 / 15 calendar days before an announcement; and separately, only open positions whose *expiry* falls after the next announcement (so you own the event rather than paying for it and exiting before it).

Note that the second rule is close to the opposite of the first, which is deliberate — the Gao–Xing–Zhang result (**O7**) says pre-earnings implied moves are underpriced, so owning the event may be favourable while paying decay into it and exiting first is not. Test both directions and let the data choose.

**Pre-register that this interacts with `term_slope`** and may partially explain it (**O16**). Run them together, not sequentially, and report the marginal effect of each conditional on the other.

**Effort: S.**

---

### O18 · Option illiquidity as a cost calibrator, not a signal

Christoffersen, Goyenko, Jacobs and Karoui (2018, *RFS* 31(3), 811–851) sort on the effective relative option spread and find a risk-adjusted return spread of **3.4% per day** for ATM calls and 2.5% for ATM puts.

**Do not attempt to trade this.** These are raw, unhedged, extremely levered option returns, and the sort variable *is* the transaction cost. It is essentially unharvestable.

**Its value is as calibration.** It is the best available evidence that option illiquidity is priced, which means the honest cost model for an options overlay is not a fixed haircut but a *spread-conditional* one. Use it to build a cost model where the assumed slippage varies with the contract's own spread percentile — and then re-run every options result under it.

**Related, and this belongs in the cost model too.** The derived greeks layer admits contracts with `spread_frac ≤ 1.00` against the entry gate's `MAX_SPREAD_PCT = 0.25`. Roughly half the priced rows in that layer would be untradeable. Any signal built on the derived layer must re-apply a tradability filter or it is measuring market-maker placeholder quotes.

**Effort: S.**

---

# PART V — The unification

Valquo has run two research programmes side by side for months. They share a repository, a data directory and a set of megacap tickers. They have never been joined, in either direction.

The asymmetry is stark. The **equity model** has a measured cross-sectional edge at 63 trading days, strongest in large caps, built on point-in-time fundamentals with survivorship-free returns — and it expresses that view only through shares. The **options book** has a mined surface across ~370 names and a decade, no working entry signal, and expresses views on names chosen by a technical alert that its own control test suggests is worse than random.

One programme has a signal and no leverage. The other has leverage and no signal.

Five items. **U1** and **U2** are the two directions of the same bridge, and between them they are the largest untested ideas in this document.

---

### U1 · The stock composite as the options entry signal

**The hypothesis.** The scream-buy technical alert does not predict which names' options will pay. The fundamental composite *does* predict which names' shares will outperform over 63 days. Long calls on high-composite names should therefore outperform long calls on randomly-chosen names — and if they do, the options book acquires the entry signal it lacks, from a source that has already been validated on 27 years of data rather than fitted on the options log.

**Why this has never been tested.** The two programmes were built by different sessions against different roadmaps, and no document in the corpus proposes joining them. The options roadmap treats entry signals as a *technical* problem — momentum, breakouts, implied-vol structure, order flow. The equity roadmap treats options as an unrelated product surface. The idea falls in the gap between two well-organised plans.

**Why the pieces line up unusually well.**

The equity signal's horizon is 63 trading days ≈ 92 calendar days. The mined option cache covers up to 90 DTE. Those match almost exactly — which is fortunate, and also the reason for **O15**, since the ideal tenor sits just past the mining ceiling.

The equity edge is strongest in **large caps** (`regime_split` reports the highest median IC there). The options cache is a liquid-name cache with the narrowest spreads exactly in that tier. The single measured killer of the options book is the spread, which takes 6.59 percentage points of an ~11.7% gross edge. So the equity signal is strongest precisely where the options friction is lowest. That is not a coincidence — both facts follow from the same underlying property, institutional attention and liquidity — but it is a favourable one.

And the equity signal is quarterly and slow-moving, which suits a 60–90 day option far better than a daily technical trigger does. A signal that decays over months paired with a contract that decays over days is a mismatch; the current book has that mismatch and the proposal removes it.

**Method.**

1. Take the equity panel's composite score on each rebalance date, restricted to names present in the options cache — roughly 111 to 370 names depending on the mining state.
2. On the rebalance date, open a long call on each of the top-*N* names by composite. Use the current contract-selection rule initially (35 delta, 45–75 DTE) so the only variable changed is *which name*.
3. Hold to the equity signal's own horizon, or apply the exit rules that survive **O1** — test both.
4. Compare against three controls, all on the same names and same dates: random-name selection within the cache; bottom-decile composite names; and the existing scream-buy alerts.

**Pre-registered thresholds.** Top-decile-composite call returns must exceed random-name call returns in both held-out halves, under a date-block bootstrap clustered by rebalance date. All trades on a rebalance date are one cohort — this clustering is not optional here, since every position opens on the same day and the market factor dominates.

**Also report, as a separate and equally important result**, the *ratio* of option return to underlying stock return per composite decile. If the composite's stock edge is roughly 11.9% annualised and a 35-delta call gives ~3× effective leverage, the naive expectation is ~35% annualised gross — against which the option's time decay, the spread, and the fact that a 63-day forward return has to arrive *within the contract's life* all subtract. That decomposition is the real deliverable: it tells you whether options are a sensible expression of this signal at all, independent of whether this particular backtest wins.

**Expected failure modes, stated in advance.**

The most likely one is that the composite's 63-day edge is a *cross-sectional mean* effect — the top decile beats the universe by a few percentage points on average — while an option needs a *specific name to move a specific amount within a specific window*. Averages that work across 250 names do not necessarily convert into convex payoffs on 25 of them. If the equity signal's alpha comes mostly from the middle of the return distribution rather than the right tail, options will not express it well, and the test will say so cleanly.

Second: the composite tilts toward value and quality, which are characteristically *low*-volatility, slow-moving names. Long calls need movement. There may be a structural mismatch between the signal's preferred names and the payoff structure — which is itself worth knowing, and points to the variant below.

**A variant worth running in the same session.** Instead of the full composite, use only the themes that produce *movement*: momentum, growth, and institutional accumulation. That is a "which names will move" signal rather than a "which names are mispriced" signal, and it is closer to what a long option needs. If the full composite fails and the momentum-weighted variant works, that is a real finding about the relationship between the two books.

**Effort: M.** Both datasets exist. The join is a merge on ticker and date. This is perhaps two days of work for the largest untested question in the project.

---

### U2 · The options surface as a stock signal — the direction that feeds the model that works

**The hypothesis.** The options market leads the stock market. This is one of the best-replicated findings in the empirical options literature, and Valquo has a mined surface and a validated equity panel and has never connected them.

**The literature, with the numbers that matter.**

*Cremers and Weinbaum (2010, JFQA 45(2), 335–367).* Deviations from put–call parity, measured as the implied-vol difference between matched call/put pairs. **Stocks with relatively expensive calls outperform stocks with relatively expensive puts by 51 basis points per week** — roughly 26.5% annualised. Both legs contribute. Short-sale constraints do not explain it. Important caveat the authors themselves report: the predictability was stronger in earlier years and has diminished, consistent with a mispricing that has been partly arbitraged away.

*Xing, Zhang and Zhao (2010, JFQA 45(3), 641–662).* The volatility smirk — out-of-the-money put implied vol minus ATM call implied vol. **Steepest-smirk stocks underperform flattest-smirk stocks by about 10.9% per year**, risk-adjusted, and **the predictability persists for at least six months**. The mechanism is that informed traders with negative news prefer OTM puts and the equity market incorporates that information slowly.

That six-month persistence is the crucial property for Valquo specifically. Most options-lead-stock effects decay within days and require fast execution. This one does not. **It is exactly the right shape for a quarterly-rebalanced equity panel.**

*Bali and Hovakimian (2009, Management Science 55(11)).* Both the realised-minus-implied volatility spread and the call-minus-put implied-vol spread predict the cross-section of stock returns.

**Why this is the highest-expected-value item in the entire catalogue.**

It feeds the programme that works, not the one that doesn't. The equity model has a real, gated, honestly-measured pipeline with a held-out validation gate, coverage guards, a sanity layer and a cost model. Adding a signal to it is a well-worn path with known thresholds.

And the signal is **structurally orthogonal to everything already in the panel**. Every current theme is derived from accounting data, price history or ownership filings. None derives from the options market. The `sentiment` theme has been structurally empty since inception (0.0% coverage, `grades.csv` is 58 bytes) and is blocked on WRDS/IBES access that has no realistic path — see **D8**. An options-derived signal is the most plausible occupant of that slot, and it is available today from data already on disk.

**Method.**

1. From the derived layer, compute per name-date: `skew_25d` (already shipped), the ATM call-minus-put implied-vol spread (both legs are computable from `<SYM>-<YEAR>.pkl`), the put–call parity deviation on matched strikes, and the change in each over 21 days.
2. Join to the equity panel on ticker and rebalance date. **Coverage will be the binding constraint** — roughly 111 to 370 names against a 2,710-name panel, i.e. 4% to 14%. See the coverage discussion below.
3. Measure median IC, IC *t* and coverage exactly as every other signal is measured.
4. Run any survivor through `holdout_compare_panels`.

**The coverage problem, and how to handle it honestly.** A signal covering 4–14% of the panel cannot move a broad book, and the project has already learned this the expensive way with USAspending (4.03% coverage, correctly noted as "a gov-exposure sleeve, not a composite change"). Three responses, in order of preference:

- Test it **within the covered subset** as a self-contained cross-sectional study — is the effect real on the names where it can be measured? This is a legitimate finding and it is the right first step.
- If it is real, **expand coverage by mining more names**. The record shows 158 names were wrongly condemned by a probe-fetch bug and have been cleared for re-screening, so the real liquid-universe plateau is unknown and is larger than 370. A signal that works is a reason to mine.
- If coverage cannot reach the panel, deploy it as a **large-cap sleeve** — which is where the equity edge is strongest anyway, and where the live 800-name book actually trades. A signal that only works on the top 800 names is still a signal for the book that holds them.

**Pre-registered thresholds.** IC *t* > 2.0 on the covered subset, with the subset's own power control (the project's standard practice: verify that a *known-real* signal such as `ret_6_1` or `gp_on_capital` clears 2.0 on the same restricted subset, so a null is interpretable as a null rather than as low power). Then the standard held-out gate.

**Expected outcome.** Cremers–Weinbaum's own authors report decay, and McLean and Pontiff (2016) find published predictors deliver **26% lower returns out of sample and 58% lower post-publication**. Apply that haircut in advance: a 26.5% annualised gross effect becomes roughly 11% post-publication, before costs, on a universe of megacaps that are the most efficiently priced names in the market. Xing–Zhang–Zhao's smirk effect, at 10.9% annualised with six-month persistence, haircuts to roughly 4.6% — small, but as an *orthogonal* input to a seven-theme composite it does not need to be large to be worth its weight.

**Effort: M.** The single best expected-value-per-hour item in this catalogue.

---

### U3 · A convex overlay on the equity book, sized as insurance rather than as a strategy

**The reframe.** If **R1** shows the equity model's excess return is largely factor exposure, and if the options book is long-volatility beta with no entry edge, then neither is a standalone alpha engine — but their *combination* has a property neither has alone. A factor-tilted long-only equity book has a known weakness: it is short volatility in the tail, it drops hard in a crash, and its worst drawdowns are exactly when correlations converge and diversification fails.

A small, systematic long-volatility sleeve is the natural hedge for that, and Valquo has already built one by accident.

**Why this is a better use of the options book than trying to make it predict.** The scream-buy book's honest description is: buy convexity on liquid names, win 37% of the time, with big winners and small losses. That is a *long-vol profile*. Long-vol profiles are chronically expensive to hold as standalone strategies — which is precisely what the fade from +16.4% to +4.4% expectancy is telling you — but they are valuable as portfolio insurance, because they pay when everything else does not.

**Method.**

1. Construct a combined equity curve: the 25-name equity book at *X*% of capital plus the single-leg options book at *(100−X)*%, at X from 90 to 99.
2. Report combined CAGR, Sharpe, maximum drawdown, and the correlation of the options sleeve to the equity book **specifically in the equity book's worst decile of quarters**. That conditional correlation is the whole question.
3. Test whether the options sleeve reduces the equity book's drawdown enough to justify its cost of carry.

**The measurement trap to avoid, which the project has already fallen into once.** The VRP work found that "stress correlation falls in a selloff (0.233 versus 0.335)" and then correctly identified it as a **conditioning artefact** — selecting days on the cross-sectional mean and then correlating deviations around that mean compresses the estimate. Splitting on ATM implied vol instead moved it from 0.254 to 0.610. Use the implied-vol split here, not a return-based one. This lesson is recorded in the corpus and is directly applicable.

**Pre-registered threshold.** Adopt only if the combined Sharpe improves *and* maximum drawdown falls. A long-vol sleeve that improves Sharpe by raising return is not doing the job it is being hired for.

**Effort: S**, given **O11**'s portfolio layer.

---

### U4 · One decision object

Currently a user sees an opportunity score, a hot-stock list, and separately an options alert. The alert is generated by a technical signal that the research suggests does not work. The score is generated by a model that does.

Whatever **U1** and **U2** return, the product should present a single object per name: the fundamental view, its confidence, the recommended expression (shares, or a specific contract with sizing), and the live track record of that expression. This is roadmap item #33 and it should be gated on the research above rather than shipped as a presentation layer over two disconnected engines.

**One thing to get right in the copy, which the project already gets right internally and should keep.** The options profile is convex with a ~37% hit rate. It must be framed as *expectancy*, never as win probability. A user who sees "high confidence" and reads it as "likely to win" will abandon the strategy after four losses, which on this distribution is an entirely ordinary run.

**Effort: L**, and it is product work rather than research.

---

### U5 · Tax-aware arm allocation

The project has already measured the number that governs this: the equity strategy returns roughly **+17.4% in a Roth versus +4.86% after tax in a taxable account**. Single-stock options are 100% short-term / ordinary income, so their after-tax gap is even wider.

That is close to a 3.6× difference, and it is larger than any signal improvement in this entire catalogue. It means account placement is not an administrative detail — it is the largest single lever on realised return that the project has identified, and it requires no research at all.

**The allocation that follows:** the options sleeve belongs entirely in the Roth, where its short-term character costs nothing. The equity book's slower, lower-turnover configuration belongs in the taxable account, where the no-trade band (**S14**) and any turnover reduction compound directly into after-tax return. The `roth` and `taxable` book configurations already exist in the codebase; this is about making the allocation explicit and consistent with them.

**One product note.** For Valquo's users the taxable case is the common one, which makes tax-aware construction a genuine product differentiator rather than a personal optimisation — most competing tools report gross returns and never mention it. "Here is the after-tax number for your account type" is exactly the kind of honest, checkable claim the project's positioning is built on.

**Effort: XS** to decide. It is already measured.

---

# PART VI — Data sources, ranked by value per dollar

All prices verified against vendor pages on 3 August 2026. Where a price could not be confirmed, this says so rather than guessing. The project's standing instruction is "buy nothing new," which is correct as a default — the trade autopsy demonstrated that flow, gamma exposure and skew products do not help. This section is ordered so that the free and money-*saving* items come first.

---

### D1 · Sharadar went direct — verify the current bill immediately

Sharadar launched a direct individual channel in July 2026 (`blog.sharadar.com`, "Sharadar Launches Direct"). Institutional customers stay on Nasdaq Data Link; individuals can buy at `sharadar.com/subscribe`:

| Plan | Price |
|---|---|
| Fundamentals | $19/mo |
| Prices | $9/mo |
| Investors | $9/mo |
| **Bundle — all 14 tables** | **$29/mo** |

The Bundle covers fundamentals (100+ indicators, ~18,000 companies since 1998), prices (EOD OHLCV, 25,000+ securities since 1998), investors (institutional since 2013, insider since 2008), corporate actions, 8-K events since 1993, tickers, and S&P 500 constituents — that is, everything the panel consumes.

**Action.** Check what is currently being paid to Nasdaq Data Link. NDL's per-dataset pricing pages are JavaScript-rendered and could not be scraped, so the current list price is unconfirmed — but the historical individual price for SF1 alone was well above $29/mo. This is plausibly the largest single cost saving available, and it also **resolves the "one month of access left" problem** that prompted the data freeze.

**Two things to confirm before switching.** The subscribe page does not spell out personal versus commercial licensing, and valquo.co is a commercial SaaS — confirm the licence covers it. And confirm the direct API's table schemas and bulk-export format match what `valuation/edge/bulk.py` expects.

**Value: potentially the highest in this section, at negative cost.**

---

### D2 · ThetaData — establish which tier is held, and check the licence

| Tier | Price | History | Granularity | Greeks / IV |
|---|---|---|---|---|
| Free | $0 | 1 yr from 2023-06 | EOD | No |
| Value | $40/mo | 4 yr (1-min from 2020-01) | 1-minute | **No** |
| **Standard** | **$80/mo** | 8 yr (tick from 2016-01) | Tick | **Yes — 1st order + IV** |
| Pro | $160/mo | 12 yr (tick from 2012-06) | Tick | Yes — 1st, 2nd, 3rd order |

**Implied vol and greeks begin at Standard, not Value.** ThetaData's own documentation places "Greeks Access (1st order)" and "Implied Volatility" in the Standard column. A third-party comparison article claims Value includes them; trust the vendor docs.

This matters because the project hand-rolls every greek and inverts every implied vol from the mid — which was validated well (98.96% delta agreement, 100% implied-vol agreement within |delta| 0.20–0.80) but consumed real engineering effort and carries the European-on-American and zero-dividend approximations documented in the layer's own header. If the subscription is already Standard, vendor implied vol is available at tick level and the ~40,000 calls / 12 hours cost estimate that drove the hand-rolled decision is worth re-checking against the bulk endpoints Standard also unlocks.

**Standard also adds bulk historical and bulk real-time endpoints** — one call per date rather than one per contract. For panel construction that is a step change in mining throughput, and it is directly relevant to **O15**'s proposed re-mine at longer DTE.

**Licence check.** ThetaData's Individual licence reads "personal use only, no redistribution or business use." valquo.co is a commercial product. If any of this data touches the product — and the greeks/GEX layer is proposed for exactly that — that is worth resolving before launch rather than after.

**Value: high, at zero or modest cost. Do the tier check this week.**

---

### D3 · Free datasets required by Part II — get these first

| Dataset | Contents | Licence |
|---|---|---|
| **Ken French Data Library** (Dartmouth) | FF3, FF5 in several constructions, momentum, short/long-term reversal, accruals, net share issues, variance factors, 5–49 industry portfolios, developed-market international sets. Daily, weekly, monthly | Free, no registration |
| **Hou–Xue–Zhang q-factors** (global-q.org) | MKT, ME, I/A, ROE — the harder test for a quality-tilted book | Free |
| **Open Source Asset Pricing** (Chen–Zimmermann) | 319 predictors from 153 papers, with signed characteristics *and* portfolio returns, plus hand-collected documentation of each original paper's method | Free. Regenerating from scratch needs CRSP+Compustat, but **the pre-computed signal files and portfolio returns download with no data licence** |
| **AQR Data Library** | Hypothetical portfolio returns from AQR papers, US and global, long-only and long/short | Free |
| **Global Factor Data** (jkpfactors.com) | 153 characteristics, 13 themes, 93 countries, updated through December 2025 | Free but **CC BY-NC 4.0 — non-commercial only.** Usable for research; **not shippable into the product** |
| **SEC EDGAR structured APIs** | XBRL `frames` (a full cross-section in one request), `companyfacts`, `companyconcept`, full-text search; Financial Statement Data Sets 2009 → 2026 Q1 | Free, no key, 10 requests/second |
| **FINRA** | Bi-monthly short interest, daily and monthly short-sale volume | Free — already in use |
| **USPTO Open Data Portal** | PatentsView disambiguated patent data; **migrated from patentsview.org on 20 March 2026** (a vendor press release claiming USPTO "discontinued" PatentsView is marketing; trust USPTO) | Free |

**Ken French is a hard prerequisite for R1**, which is the most important test in this document. Note the JKP non-commercial licence carefully — it is fine for validating the model and not fine for shipping.

**Value: essential, at zero cost.**

---

### D4 · Cboe Open-Close Volume Summary — the one dataset that would unlock a genuinely new signal class

This deserves a flag on its own. Fields: volume broken out by **participant capacity** (customer, professional customer, broker-dealer, market maker) × **buy/sell** × **open/close** × trade-size bucket for customers. History: C1 end-of-day since 2005-01-03, 10-minute since 2011, 1-minute since 2019; BZX/C2/EDGX EOD since 2018. Delivery via SFTP or Snowflake.

**Why this is categorically different from every retail flow product.** It is the only publicly purchasable dataset that gives **signed, open-interest-flagged option volume by participant type** — the closest legal approximation to the proprietary CBOE data behind Pan and Poteshman (2006) and the wholesaler flags behind Bryzgalova et al. (2023). Public tick data cannot separate informed institutional flow from retail lottery-ticket buying; this dataset can, and those two populations have *opposite* predictive signs.

If the project ever wants an options-flow signal with actual academic grounding rather than a vendor's heuristic, this is the dataset, not Unusual Whales.

**Pricing is not displayed** — DataShop is a configurator requiring symbol and date selection. Third-party forum reports suggest roughly $600/yr for full-market EOD chains without calculations and ~$1,000/yr with, but those are for a different product and are indicative only. There is an **academic discount of 50% on select historical datasets with a $500 minimum**, restricted to accredited institutions.

**Recommendation.** One sales call, and only after **O14** (free alert-day tick flow) has been run. If unsigned tick flow shows nothing, capacity-tagged flow is the only version of this hypothesis left worth paying for. If unsigned flow shows something, this dataset tells you whether it is informed or retail — which determines the sign.

**Value: high if flow is pursued at all; unknown cost. Gate on O14.**

---

### D5 · ORATS — the realistic upgrade if the surface work pays off

| Tier | Price | Requests/mo |
|---|---|---|
| Delayed Data API | $99/mo | 20,000 |
| Live Data API | $199/mo | 100,000 |
| Live Intraday API | $399/mo | 1,000,000 |

History to 2007, 5,000+ symbols. The near-EOD snapshot is taken 14 minutes before the close with full chains, derived greeks, theoretical values and implied vols. One-minute intraday from August 2020. Bulk historical is a one-time or recurring purchase; bulk pricing is not published.

**The differentiator is Smoothed Market Values** — a fitted, cleaned volatility surface rather than raw quotes. That is the closest cheap analogue to OptionMetrics' standardized surface, and it is directly relevant to **O6c** (pick the contract that is cheap relative to the fitted smile) and to every cross-sectional test in Part IV, where raw mid-quotes on wide markets are the dominant noise source.

**Note the dependency already in the stack.** Tradier's greeks and implied vols are supplied by ORATS and refreshed hourly. So the live path already consumes a downstream copy of this data.

**Recommendation.** Do not buy until **O2** or **O6** returns something on the existing cache. If one does, ORATS is the natural upgrade — a fitted surface would materially improve the signal-to-noise of exactly those tests.

**Value: conditional. Gate on O2/O6.**

---

### D6 · What the estimate-revision situation actually is

Roadmap item #20 (`sentiment` theme, blocked on point-in-time estimate revisions) should stay parked. Nothing has changed.

**Genuinely point-in-time sources:** IBES Detail History unadjusted via WRDS (institutional, requires affiliation — see **D8**); Zacks historical consensus files (annual EPS from 1979, quarterly from 1982, recommendations from 1985; pricing not published, contact required); S&P Capital IQ / Visible Alpha (institutional; Visible Alpha was absorbed into S&P Global, completed May 2024); Refinitiv/LSEG and FactSet direct.

**Not point-in-time, despite appearances:** FMP (analyst estimates limited to ~87 sample symbols below the $149 Ultimate tier; the `grades` upgrade/downgrade endpoint from Starter is a genuinely dated *event* stream and is the one usable piece — exactly the weak workaround already identified); Finnhub, EODHD, Tiingo, Alpha Vantage, Intrinio — all snapshot or restated; Benzinga (dated rating and price-target events, same category as FMP grades, enterprise-quoted).

**A specification detail that matters if WRDS ever becomes available.** Use the **unadjusted** IBES files — `detu`, `actu`, `excu`, `statsumu`, `actpsumu`. The adjusted files retroactively apply splits, producing spurious surprises; WRDS's own note uses the June 1998 Amazon 2-for-1 split, where an estimate made on 20 May 1998 appears to miss by roughly 6× purely as an artefact. Getting this wrong would produce a signal that looks strong and is entirely a corporate-actions artefact.

**Recommendation.** Keep parked. The `sentiment` slot is better filled by the options-derived signal in **U2**, which uses data already on disk.

---

### D7 · WRDS — there is no path for an unaffiliated individual

The complete list of account types is Faculty, PhD Student, Research Assistant, Staff, Visitor, Master's/Undergraduate Student, and Class Accounts. **There is no alumni account, no corporate account, and no unaffiliated-individual account.** "Visitor" means visiting *faculty* on a limited appointment at a member institution; it is not a guest pass.

Two further complications. **WRDS is a platform, not a bundle** — each institution subscribes to a subset, and OptionMetrics and RavenPack are commonly *not* included even at subscribing schools. And student accounts are term-limited, typically expiring with enrolment.

The route people actually use is enrolling in a part-time or online master's programme at a subscribing school — real cost, real time, and still no guarantee that OptionMetrics is in that school's subscription.

**Recommendation.** Treat WRDS as unavailable and stop planning around it. The roadmap currently lists "WRDS/IBES estimate revisions" as the #1 remaining stock lever and "BLOCKED on Don setting up WRDS access; then it's a prompt." The realistic assessment is that this is not one step away — it is a degree away. **Remove it from the critical path and promote U2 into that slot.**

---

### D8 · What not to buy

**Retail gamma-exposure and flow products** — Unusual Whales ($50/mo web, $150–375/mo API), SpotGamma ($99–299/mo), Cheddar Flow ($85–99/mo, no API at any tier), SqueezeMetrics (~$720/mo, third-party reported). This category has the weakest evidence-to-price ratio available, for three specific reasons.

There *is* real peer-reviewed evidence for dealer-gamma effects — Barbon and Buraschi on gamma fragility, Baltussen et al. on hedging demand and intraday momentum, with Gârleanu, Pedersen and Poteshman's demand-based option pricing as the theoretical foundation. But: the best-measured index-level estimate, Amaya et al. (2025, published by Cboe) using **actual dealer trade data** rather than a public proxy, finds maximum gamma-induced effects of +3.3 pp on daily annualised realised vol and **an average effect of about −0.2 pp per day**, concluding these maxima are "not large." Every retail product infers dealer positioning from public open interest plus a sign-assignment heuristic; **none observes actual inventory**. And no source establishes that vendor GEX correlates well with measured dealer gamma.

All documented effects are **intraday**. For an end-of-day, long-only, fundamentally-driven book this category has no demonstrated application. The project's own autopsy independently rejected GEX, skew and implied-vol rank as entry filters, which is the same answer arriving from its own data.

**Intrinio** ($150/mo) — US EOD historical options history is **two years**. Disqualifying for backtesting.

**Databento** ($199/mo Standard, per-byte usage) — raw OPRA microstructure, no greeks or implied vol. The right vendor for microstructure work and the wrong one for this project.

**Polygon.io** — note that `polygon.io/pricing` now redirects to `massive.com/pricing`; the company appears to have rebranded. Options tiers run $29–199/mo. Flag it if anything in the codebase points at the old domain.

**Ortex** ($49 Basic / $149 Advanced) — real-time short interest, cost-to-borrow and API access are Advanced-only. FINRA is free and already in use; the project's own short-interest tests came back at IC *t* +1.04 and +0.42. Do not pay to improve the timeliness of a signal that does not work in its free form.

---

### D9 · Options costs are a step change, not an increment

Two numbers to hold together, because they bound the same quantity from opposite ends.

Muravyev and Pearson (2020, *RFS* 33(11), 4973–5014) decompose S&P 500 option trading costs: quoted half-spread **11.6%** of option price, conventional effective **9.2%**, adjusted effective **7.1%**, and the "algo half-spread" — the true cost after removing execution-timing gains — **4.7%**. Roughly 37–42% of traders benefit from timing.

Bryzgalova, Pavlova and Sikorskaya (2023, *Journal of Finance*) document that retail is over 60% of total options volume, concentrates in cheap weeklies carrying an average bid-ask of **12.6%**, and loses money on average.

Both are true. The cost is ~4.7% of premium if you work orders patiently in liquid names and ~12.6% if you cross on a cheap weekly.

**The calibration that matters for Valquo.** The equity book runs at 37 bps one-way against a 236 bps breakeven — a 6.4× margin. An options overlay at even the optimistic 4.7% of premium is a different *order of magnitude* of friction relative to notional at risk. **The 6.4× margin does not transfer, and no options result should ever be compared to the equity book's cost cushion as though it did.** This is the single most important calibration fact in this section, and it is the reason **O10** (the passive-fill model) matters — it is the only way to find out where in the 4.7%–12.6% range this book actually sits.

---

### D10 · Sharadar lapse contingency

The freeze at `data/backtest_freeze_2026-08/` is done, verified against known checkpoints (AAPL 2015Q2 at $722.6B, ~197,265 rows, ~2,710 names), and runs with no API key. Two things remain.

**Run one full backtest from the freeze before access ends.** The current run still reads `data/backtest` (the 2026-07-24 export). Nobody has confirmed end-to-end that the freeze produces the same numbers. That confirmation is worth an hour now and is impossible later.

**Extract the documentation while the subscription is live.** Specifically: the EVENTS eventcode legend (needed for **S17**), the complete ACTIONS action enum, the exhaustive TICKERS.category values, and — the highest-value unknown in the corpus — **whether a restatement appends a new ARQ row.** If it does, the obvious query pattern (latest `datekey` per `reportperiod`) silently returns the restated figure, which is look-ahead bias in a backtest that would look completely clean. `pit_fundamental()` defensively takes the *earliest* `datekey`, which is correct under both behaviours, but nobody knows what that costs. `scripts/verify_sharadar.py` was written to settle exactly these questions and has **never been run against the real key**.

A compounding hazard worth knowing: a missing or invalid Sharadar key returns **sample data, not an error**. A truncated sample looks exactly like a successful small query.

**Also worth resolving before D1's switch:** whether SF1 percentage fields arrive as `0.15` or `15.0`. Getting that wrong scales a factor by 100× silently.

---

# PART VII — Methodology upgrades

Six items. These do not add signal; they change what the project is able to know. Several of the findings in this audit exist only because a guard was measuring something narrower than its name implied, and the pattern is recurrent enough to be worth engineering against directly.

---

### M1 · A single append-only research log with a real trial counter

The ledger reconstructed for this audit has roughly 146 distinct tests across the corpus. The Deflated Sharpe uses `N = 8`. Every multiple-testing claim in the project is computed against the wrong denominator, and the only reason anyone can now count the real one is that the handoff discipline was good enough to reconstruct it after the fact.

**Build.** One append-only file — CSV or JSONL — with a row per pre-registered test: date, domain, hypothesis, universe, metric, threshold committed *before* the run, verdict, source document, and a stable ID. Populate it retrospectively from the corpus; that work is largely done and appears as section A of the ledger. Then wire the row count into `_deflated_sharpe` as `N` and into `_trials_haircut`.

**What it buys.** Right now the project cannot honestly claim its statistical bars are cleared, because the bars are computed against eight near-identical trials. With a real log it *can* — and a long-short *t* of 3.52 probably does clear a properly-computed hurdle. That is a much stronger claim than the current one precisely because it is defensible. It also makes the "do not re-open without a new reason" rule enforceable, since the reason is recorded next to the original verdict.

---

### M2 · Clustered and block inference as the default, everywhere

Currently: the equity long-short *t* is naive i.i.d.; the top-decile alpha has no *t* at all; every options statistic treats correlated trades as independent; and nothing computes an effective sample size.

**Standardise on three things.** A date-block bootstrap for anything trade-level, resampling calendar blocks and keeping all trades within a block together. Newey–West standard errors for anything period-level, with the lag chosen from the autocorrelation of the series rather than by convention. And `n_eff` reported alongside `n` wherever a *t*-like quantity appears.

Add purge and embargo to `pbo_cscv` on the options side — a trade entered in an in-sample block is open 30 to 60 days into the adjacent out-of-sample block, and performance is attributed by entry date.

On the equity side, note that the CPCV embargo of **one rebalance period** is a quarter of what the longest feature lookback requires: `ret_12_1` reaches back 252 trading days, which is four rebalance periods, so a test period's realised returns feed the momentum features of the next four training dates. Set the embargo from the maximum feature lookback, not from the label horizon.

---

### M3 · Engineer against the "guard that cannot see" pattern

This failure mode has now occurred at least six times in the project's history: `assets` dropped from the loader allowlist; five ARQ-empty factors contributing nothing for the project's entire life; the SF3 positional-argument bug; `invcap`/`taxexp`/`ebt` missing from `_KEEP`; the greeks sentinel guard blind on 82 of 109 names because a count was aggregated per year one change before it was summed per name; and the autopsy's regime cache keyed only on its path, serving a stale dict so 64 features were silently reported as 63.

The shape is always the same. **A guard whose input is computed elsewhere is not a guard.** And the more dangerous half is not the wrong count — it is the *missing flag*, because a quiet flag list reads as "checked, fine."

**Three concrete defences.**

*Every guard gets a known-bad fixture.* A test that feeds the guard a record it must flag, so the guard's own wiring is under test rather than just its arithmetic.

*Coverage guards must enumerate from the source of truth, not from a registry.* `signal_coverage` iterates `S.NUMBERS_ALL`, so the seven signals computed but never registered — `cash_op_prof`, `neg_ret_1m`, `neg_max_ret`, `neg_idio_vol`, `sm_conviction`, `sm_holders`, `sm_avg_position` — are invisible to it. It cannot see a signal that was never registered, which is exactly the class of bug it exists to catch. Make it enumerate the columns the panel actually produces and flag any that are computed and unregistered.

*Extend coverage guarding to the options lane, which has none.* The `open_interest = −1` sentinel affects 11.4% of the cache and no code anywhere audits it. `theta_bulk` returning `failed=False` on a failed open-interest fetch is the same bug class as the five empty factors, in a subsystem where the equivalent guard was never built.

---

### M4 · A live-replay harness

Three composite functions exist and no shipped code path reproduces the backtested one. That was found by reading code. It should have been found by a test.

**Build.** A harness that scores a historical universe using the **live** code path — `screen.py` → `build_frame` with production CONFIG → `composite_score` → soft-bucket blending — and compares the resulting ranks to the backtest's on the same date and universe. Assert rank correlation above a threshold, and fail loudly below it.

This is the cheapest possible detector for the entire class of live-versus-backtest divergence, and the options lane needs its own version: three different ATM implied-vol definitions currently ship in production (calls-only nearest-strike; calls-and-puts pooled; nearest-|delta|-to-0.50 off the broker summary; plus a fourth, the call/put mean, in the derived layer). On a put-skewed equity surface the gap between them is a vol point or more — the same order as the 0.0105 `term_slope` threshold that decides whether an alert fires.

---

### M5 · Some hypotheses cannot pass a both-halves gate, and the gate should know it

The regime overlay passed both of its numeric criteria on the full sample — maximum drawdown improved from −57.0% to −37.0%, a 20-point gain, for a 2.70-point return give-up, with Sharpe improving 1.13 → 1.17. It was rejected because the entire benefit sits in one episode, and the late half shows a zero drawdown improvement.

That rejection is correct discipline applied to a test the rule could not have passed. **A crash-insurance rule cannot clear a both-halves gate unless the sample contains two comparable crashes.** The panel has one. Structuring the test this way guarantees rejection regardless of the rule's merit.

**Adopt a distinct protocol for conditional or tail-hedging rules:** does the rule fire on the days it is supposed to (a conditional accuracy test, not a return test)? What is the explicit cost of carry in the ~90% of the time it is wrong? And what is the payoff conditional on firing, measured against a pre-specified definition of the state it is insuring against?

Judged that way, the overlay might be adoptable as an *optional* configuration with an honest cost statement — which is roughly where it has landed anyway (`settings.REGIME_OVERLAY`, default `None`). The point is that the current framing records it as a failed test when it is actually an untestable hypothesis under the chosen protocol, and that distinction should be in the record so nobody re-runs the same doomed test.

---

### M6 · Fix the results file's silent-failure mode, and its date ranges

Two structural problems with `BACKTEST_RESULTS.json`.

**Silent partial failure.** `run_backtests` wraps the entire diagnostic and validation block in one `try/except Exception` (`fundamental_panel.py:3501`, `:3628-3633`) that stamps `{"status": "error: …"}` onto five keys. A failure two-thirds of the way through — say inside `costs` — discards `holdout_validation`, `book_configs`, `no_trade_band` and `after_tax` **with no status marker on them at all**. They are simply absent, and `errors: []` remains empty. A consumer sees a clean-looking file with four missing blocks. Wrap each block individually and stamp each independently.

**Undisclosed and inconsistent date ranges.** `construction` reports 110 periods; `portfolio` reports 73 over a different window; `per_horizon["63"]` publishes an `accepted: true` weighting (`low_risk: 0.1704, institutional: 0.0`) that is the mirror image of the deployed configuration and would lead a consumer to the opposite conclusion from the shipped one. Stamp the actual date range, period count and universe size on every block, and either suppress the superseded per-horizon weights or label them explicitly as a rejected single-split result.

**A third, smaller item.** The ledger surfaced fourteen internal contradictions across the corpus — four different "current" PBO values (6.7%, 13.3%, 20.0%, 26.7%), three different equal-weight benchmark returns inside one JSON (16.55%, 14.78%, 13.96%), two "current" greeks-layer sizes (82 names and 111 names), two figures for the same 55-name options result (+10.4% and +12.33%, both attached to n=1,540), and a direct contradiction between two handoffs written the same day about whether `ev_point_in_time` shipped. Most are stale numbers in prose rather than code defects — but the project's memory *is* these documents, and a reader cannot tell which figure is current without checking the JSON. A single generated "current numbers" block, emitted by the code and included by reference rather than retyped, would end this class of drift permanently.

---

# PART VIII — Corrections not in Part I

Ten further defects found during the audit. None blocks the Part I sequence, so they were held back from the critical path — but several change a number that appears in the record, and two of them affect figures currently quoted in the product.

---

### B17 · The "top-25 hold" book holds up to fifty names, and pays neither costs nor taxes

`_backtest_hold` (`fundamental_panel.py:1398-1407`) sells a name only when it drops below `exit_rank`, which defaults to `top_n * 2`:

```python
for t in list(held):                      # SELL: band drop-out or stop
    rank_out = (t not in rank or rank[t] > exit_rank) and (i - entry_i) >= min_hold
for r in range(min(top_n, len(order))):   # BUY: new top-N
    held.setdefault(tickers[order[r]], [i, 1.0, 1.0])
```

With `top_n = 25` and `exit_rank = 50`, the held set converges toward roughly fifty positions, not twenty-five. `BACKTEST_RESULTS.json → portfolio.cagr = 27.15%` comes from this function and is presented as the top-25 hold strategy. It also charges **no costs and no taxes**, unlike every other book in the results file.

The project's own record already flags the +27.9% figure as "the noisiest number in the file — do not quote it." That caution is correct but incomplete: the number is not only noisy, it describes a different portfolio from the one it is labelled as, measured without the frictions every other book pays.

**Fix.** Report the realised held-position count per period alongside the CAGR, and run this book through the same cost and tax layers as the others. Then decide whether the no-trade band it implicitly implements is the same one **S14** evaluates — because it is, and the two are currently measured under different conventions.

**Effort: S.**

---

### B18 · Negative enterprise value is read two opposite ways, and the sanity layer is exempt from checking it

```python
"ebit_ev":   (ebit_usd / ev) if (ebit_usd is not None and ev) else None,   # neg EV → looks EXPENSIVE
"ev_sales":  (ev / rev_usd) if (ev and rev_usd) else None,                # neg EV → neg_ev_sales huge → CHEAPEST
"ev_ebitda": (ev / ebitda_usd) if (ev and ebitda_usd and ebitda_usd > 0) else None,
```

`neg_ev_ebitda` is guarded (`_evebitda.where(_evebitda > 0)`, `factors.py:101`). `neg_ev_sales` is not (`factors.py:91`). So a net-cash company ranks simultaneously as the most expensive name in the cross-section on one value input and the cheapest of all on another.

This affects about 0.70% of rows, which is small — but note that `ev_sales` sits on the `SANE_RANGE_EXEMPT` list (`fundamental_panel.py:2954`), so the sanity layer built specifically to catch this class of error cannot see it. The exemption exists because EV/Sales legitimately takes a wide range; the consequence is that the one place a sign error would hide is the one place that is not checked.

**Fix.** Decide a single convention for negative EV — the defensible one is to treat it as missing rather than as an extreme, since a negative multiple is not on the same scale as a positive one — and apply it to all three. Replace the blanket range exemption with a sign check, which is cheap and does not require a range.

This matters more after **S1**, which proposes moving `neg_ev_ebitda` into the established branch.

**Effort: XS.**

---

### B19 · Every "Sharpe" in the results file is a return-to-volatility ratio

`risk_stats(rets, per_year, rf=0.0)` (`fundamental_panel.py:2338-2359`) is always invoked with `rf = 0`. Over 1998–2026, with the risk-free rate averaging somewhere around 2%, that overstates a true Sharpe by roughly 0.05 to 0.10.

Small, and in a consistent direction across every book, so relative comparisons are unaffected. But the label is wrong, the figure appears in product-facing material, and the options-bot's own engine already does this correctly — it subtracts the risk-free rate. Two subsystems in the same repository use different definitions of the same word.

**Fix.** Pass a real rate series (FRED DGS3MO, free) or state plainly in the results file that the reported figure is an information ratio versus zero.

**Effort: XS.**

---

### B20 · `earnings_yield` silently switches numerator definition mid-cross-section

`_to_usd(sf1, "netinccmnusd", ni, div)` (`fundamental_panel.py:324`) returns *net income available to common* when the USD column is populated, and falls back to *total net income divided by the FX rate* when it is not.

For most names those are the same number. For preferred-heavy names — banks, REITs, recently-recapitalised companies — they differ by the preferred dividend, which can be material. The result is one cross-section in which the same factor is computed two different ways depending on data availability, and the names where it differs are systematically clustered in one sector.

**Fix.** Pick one definition, compute it consistently, and record a coverage figure for the fallback path so the size of the affected group is visible.

**Effort: XS.**

---

### B21 · `_sector_capped` is fully implemented and never invoked

`fundamental_panel.py:2362` implements sector concentration capping. `run_backtests` never passes `max_sector_w`, so it never runs.

This is not the same intervention as sector-neutral ranking, which was tested and rejected twice. Neutralising *scores* by sector destroys cross-sector selection, which is why it sold top-decile alpha. Capping *weights* by sector leaves the selection intact and only bounds the concentration. The record shows a sector cap was rejected as a risk control on the Roth top-25, but that is a different application from the decile book, and the function's existence suggests it was built for one and tested on the other.

**Fix.** Run the decile book at sector caps of 25%, 30% and 40%. Report alpha, drawdown and the realised maximum sector weight. Pre-register that this is a **risk** intervention: adopt if drawdown improves materially for a small alpha give-up, on the same asymmetric logic as **S10**.

**Effort: XS**, since the function exists.

---

### B22 · The results file can lose four blocks with no error marker

`run_backtests` wraps the entire diagnostic and validation section in a single `try/except Exception` (`fundamental_panel.py:3501`, `:3628-3633`) that stamps a status onto five keys. A failure partway through — inside `costs`, say — discards `holdout_validation`, `book_configs`, `no_trade_band` and `after_tax` **with no status marker on them at all**. They are simply absent from the JSON, and `errors: []` stays empty.

A consumer, human or agent, sees a clean file with four blocks missing and no signal that anything went wrong. Given that the project's memory is these files, this is a silent-corruption path into the record itself.

**Fix.** Wrap each block independently and stamp each independently. Add a schema assertion listing the blocks a complete run must contain, and fail the run loudly if any is absent.

**Effort: S.**

---

### B23 · Four panel builds per run, two of them identical

`run_backtests` loops `horizons = [63, 252, 756]`, each calling `build_fundamental_panel` (`:3197`), then builds a **fourth** panel at 63 days with `keep_numbers=True` (`:3506`). The 63-day build therefore runs twice with identical parameters except for the diagnostic columns.

Inside the panel, `closes = frame[t].values` followed by `cl = closes.tolist()` (`:980`, `:1005`) executes per ticker per date — roughly 7,245 floats across 2,710 tickers and 110 dates of list conversion, per build.

This is purely a speed issue, but speed compounds into research throughput: a run that takes four hours instead of one is a run nobody does casually, and casual re-runs are exactly what the sixty-odd tests in this catalogue require.

**Fix.** Cache the 63-day panel and reuse it for the diagnostic pass. Keep the numpy arrays rather than round-tripping through lists.

**Effort: S.** Likely a 40–50% reduction in wall-clock per full run.

---

### B24 · `sanity_check` evaluates several factors twice, on different bases

```python
for name in (list(ranges) + list(SANE_RANGE_EXEMPT)
             + [c[2:] for c in panel.columns if c.startswith("z_")]):
```

`SANE_RANGES` keys and `SANE_RANGE_EXEMPT` overlap with the derived `z_*` names, so factors are checked more than once — and the raw-versus-z preference at `:3023` means the same factor can be evaluated on a raw level in one pass and a standardised value in another. The shipped output shows the artefact plainly: `ev_ebitda` at a foreign median percentile of 0.362 and `neg_ev_ebitda` at 0.640, which is the same information reported twice with opposite sign.

Cosmetic, but it inflates the flag count, and an inflated flag count in a guard trains readers to ignore the guard.

**Effort: XS.**

---

### B25 · Two Deflated Sharpe implementations that will never agree

`fundamental_panel._deflated_sharpe` and `options_autopsy.deflated_sharpe` differ on the key input: one treats `var_sr` as the cross-trial variance of Sharpe ratios, the other as a sampling variance. They also differ internally on degrees of freedom — `ddof=1` for the Sharpe and `ddof=0` for the skew and kurtosis scale (`fundamental_panel.py:1976-1980`).

And within the equity file alone, `validate_institutional` calls `_deflated_sharpe(strat, [single_sharpe])`, giving `N = 2` and `var_sr = 1/n` — a different convention from the main path in the same module.

Three conventions, one statistic, one repository. Pick one, put it in a shared module, and test it against a published worked example.

**Effort: S.**

---

### B26 · Same-day inclusion for insider filings and rating actions

`_insider_score_at` uses `searchsorted(dts, hi, "right")` (`:736`) and `_grades_at` does the same (`:815`), so a Form 4 or rating action **dated `as_of`** is usable at that day's close.

At most one day of optimism, and grades are empty in the current run, so the live exposure is limited to the insider theme at 85% coverage and an IC *t* of −0.34. But it is free to fix and it is the kind of thing that becomes material if **S3** succeeds in making the insider theme work.

**Effort: XS.**

---

# PART IX — Robustness: a category of test never run

Every validation in the project splits on **time**. The panel is halved chronologically, CPCV blocks are chronological, the options book is split early and late. That is one axis, and it is the axis most exposed to the objection the project already knows about: both halves come from the same panel, the same vendor, the same universe, and the same set of construction decisions.

There are at least four other axes, all free, and none has ever been used. This is the largest methodological gap in the programme and it is cheaper to close than any signal test in this catalogue.

---

### X1 · Split on the universe, not on time

**The idea.** Randomly partition the ~2,710 names into two halves by a stable key — a hash of the ticker, or odd/even CIK. Make every decision on half A. Measure on half B. Nothing about the time series changes, so a result that holds is not a regime artefact; and nothing about the decision process leaks, because the names are disjoint.

**Why this is strictly better than the time split for most questions.** The time split conflates two things: whether the signal generalises, and whether the *period* generalises. A signal that works in 1998–2012 and fails in 2012–2026 might be dead, or the second period might simply be a different regime — and the project has hit exactly this ambiguity repeatedly (`size` flipping from *t* +3.17 to −0.67, the options fade from +16.4% to +4.4%, the regime overlay that cannot pass a both-halves test because there is only one crash). A universe split has no regime confound at all.

**Method.** Add a `universe_split` parameter to the panel builder. Re-run every theme decision, every held-out comparison, and the weight selection under it. Report both the time-split and universe-split verdicts side by side.

**What to watch for.** A decision that passes on time and fails on universe is probably fitted to the particular names, which for a 110-period panel with a heavy megacap tail is a real risk. A decision that passes both is far better evidenced than anything currently in the record.

**Effort: M.** This is the highest-value item in Part IX and possibly the highest-value methodological change in the document.

---

### X2 · Rebalance-grid offset sensitivity

The rebalance grid is `range(TD, len(cal) - horizon, rebalance_days)` starting at `TD = 252` — an arbitrary offset. Every result in the project is measured on that one grid.

**The test.** Re-run on grids offset by 5, 10, 20, 30, 40 and 50 trading days. Report the distribution of top-decile alpha, long-short *t* and PBO across the seven grids.

**Why this matters more than it sounds.** If the alpha varies by, say, ±1 percentage point across offsets, the result is robust and the point estimate is meaningful. If it varies by ±4 points, then the headline number is one draw from a wide distribution and the honest statement is a range, not a figure. This is the cheapest possible test of whether the project's central number is fragile, and it has never been run.

It also produces something directly useful: an **ensemble** across offsets, which is a strictly lower-variance estimator of the same strategy and is trivially implementable as an overlapping-cohort portfolio.

**Effort: S.** Mechanically it is a loop.

---

### X3 · Ablate to the best single signal

**The test.** Run the decile backtest on `gp_on_capital` alone (IC *t* +4.61, the strongest signal in the model). Then on the `quality` theme alone (theme *t* +3.39). Then on the full seven-theme composite. Report all three.

**Why this is the most uncomfortable test in the catalogue, and why it should be run first among the robustness set.** If one signal delivers most of the composite's alpha, the seven-theme architecture is decoration — expensive decoration, since it brings in `insider` at *t* −0.34 and `book_to_price` at +0.15. The project has never established that its complexity is earning anything.

**Extend it into a proper ablation curve.** Add themes one at a time in order of theme IC and report the alpha at each step. The shape of that curve is the single most informative diagnostic about the model's structure that could be produced from data already on disk, and it directly informs **S5** (hierarchical shrinkage), **S7** (interactions) and the honest product description.

**Pre-register the interpretation.** If the curve flattens after three themes, say so and simplify. A simpler model with the same alpha is better in every way that matters — less to overfit, less to break, easier to explain, and cheaper to compute.

**Effort: S.**

---

### X4 · Benchmark against what a user could actually buy instead

The current benchmarks are an uninvestable equal-weighted universe charged zero cost, and SPY on the 73 dates where it exists.

Neither is the competitor. The competitor for a multi-factor long-only equity model is **a blend of cheap factor ETFs** — value, quality, momentum, size, and a low-volatility sleeve — available at roughly 15 to 25 basis points a year with no turnover cost, no tax drag from rebalancing, and no research burden.

**Method.** Construct an equal-weighted blend of liquid factor ETFs matched to the composite's theme weights. Compound to the same 63-day windows. Report the strategy's excess return over it, net of the strategy's own costs and gross of the ETF's fees.

**Why this belongs alongside R1 rather than after it.** R1 asks whether the excess return is explained by factor exposure in a regression sense. X4 asks the practical version of the same question: could someone get the same exposure for 20bps without any of this? These are different questions with potentially different answers — a regression can show full factor loading while the implementation still adds value through better factor construction, fresher data, or a tighter universe. That gap, if it exists, is the actual product.

**Pre-register the honest outcome.** If the strategy does not beat a cheap factor blend net of costs and taxes, the product's claim has to change. If it does — and that is entirely possible, since retail factor ETFs are constructed crudely and rebalance slowly — then *that margin* is the number to publish, and it is far more defensible than an alpha figure measured against an equal-weighted average of penny stocks.

**Effort: M.**

---

### X5 · Bootstrap the entire pipeline

Every uncertainty estimate in the project is computed on the *output* of one pipeline run. None propagates uncertainty from the inputs.

**Method.** Resample the universe with replacement — say 200 draws of 2,710 names — re-run the full panel and decile backtest on each, and report the distribution of top-decile alpha, long-short *t*, monotonicity and PBO. This is expensive, which is why **B23** (four panel builds per run) is worth fixing first.

**What it produces.** A confidence interval on the headline number that accounts for name-selection uncertainty, which is the dominant uncertainty in a cross-sectional strategy and is currently unmeasured. If the 5th percentile of that distribution is positive, the result is strong. If it straddles zero, the point estimate has been carrying more weight than it can bear.

**Effort: L**, mostly compute.

---

### X6 · Test for structural breaks rather than assuming drift

Two of the project's most important observations are decay stories: the options edge fading from +16.4% to +4.4%, and `size` flipping from *t* +3.17 to −0.67 around 2012. Both are currently handled by splitting the sample in half, which is the crudest possible response.

**Method.** Run a Bai–Perron multiple-break test on the theme IC series and on the options expectancy series. It identifies break *dates* endogenously rather than assuming the midpoint, and it distinguishes a genuine regime change from gradual drift.

**Why the distinction is actionable.** If `size` broke in 2012, then pre-2012 data is arguably a different regime and should be down-weighted or excluded — which would change the weights, the ICs, and the top-decile alpha. If it drifted, the honest response is an exponentially-weighted estimator (**S27**). Those are different remedies, and the project currently applies neither because it has not established which case it is in.

**Effort: M.**

---

### X7 · A no-signal placebo through the full pipeline

The options-bot has a no-edge self-test that confirms its engine does not manufacture edge from noise. **The equity pipeline has no equivalent.**

**Method.** Replace the composite with a column of cross-sectionally shuffled ranks — preserving the exact distribution and the exact missingness pattern — and run the complete pipeline end to end: quantile backtest, CPCV, PBO, Deflated Sharpe, held-out gates, costs. Repeat 100 times.

**What it tells you.** The null distribution of every headline statistic under a signal that is definitionally worthless. If PBO on pure noise comes back at 30%, then a PBO of 6.7% is impressive. If noise comes back at 8%, it is not. Right now nobody knows where the floor is, and every threshold in the project — the 2.0 IC *t* bar, the 0.25 t-gain margin, the 1% alpha margin — was chosen by convention rather than calibrated against the pipeline's own noise floor.

This single test would put every other threshold in the project on a measured footing.

**Effort: M.** High value, and it is the natural companion to **R4**.

---

### X8 · Replicate the theme structure on a different vendor's data, in a different country

The deepest unaddressed risk in the equity programme is that everything — every signal, every IC, every verdict — rests on one vendor's construction of one country's fundamentals over one window.

**The free route.** Global Factor Data (jkpfactors.com) publishes 153 characteristics grouped into 13 themes across 93 countries, updated through December 2025, built from an entirely different data pipeline. The Chen–Zimmermann Open Source Asset Pricing dataset publishes 319 predictors with both signals and portfolio returns.

**Method.** Map the seven scored themes onto their nearest JKP equivalents. Ask one question: does a composite with the same theme structure and the same equal weights produce a positive, monotone decile spread in developed Europe and in Japan? Do not tune anything — the value is entirely in the absence of tuning.

**Pre-register the interpretation.** A positive result is the strongest evidence the project could obtain, because it is out-of-sample in vendor, country, construction and period simultaneously. A negative result does not kill the US model, but it would mean the edge is US-specific and should be described that way.

**One licence caution.** JKP data is CC BY-NC 4.0 — non-commercial only. It can validate the model; it cannot ship inside the product.

**Effort: M.** The best evidence-per-hour available anywhere in this document.

---

# PART X — Stock: further tests

Ten more, including one finding the project already made, wrote down, and deliberately left on the table.

---

### S19 · The MD&A anomaly the lazy-prices study found and did not exploit

This is the most under-appreciated result in the corpus.

The lazy-prices work is filed as a null — a 28-cell grid of measures and horizons on 195 filers, nothing survived, correctly rejected. But inside that null the study surfaced something else: the **MD&A section measure is significant in the wrong direction**, at a long-short spread of **−11.2%/yr with a Newey–West *t* of −2.58**, present in **both halves**, surviving word-count floors, and **unexplained by growth or momentum**.

It was left unexploited for a defensible reason: reading a pre-registered direction backwards is a new hypothesis, and acting on it inside the study that generated it would be exactly the sin the project is built to avoid. That was the right call at the time.

But the correct response to a new hypothesis is not to discard it. It is to give it its own out-of-sample test.

**Method.**

1. State the hypothesis in the direction the data suggests, in writing, before touching anything: companies whose MD&A language changes *more* year-over-year subsequently outperform (or underperform — take the sign the original study found and commit to it).
2. Test it on data the original study did not see. Two routes: extend the filer set beyond the 195 survivors (the record costs this at roughly one hour per 250 names), or test on a different section, a different horizon, or a different period than the one that produced the observation.
3. Apply **X1**'s universe split, which is ideal here — the original 195 names are the deciding set by construction, so any new name is genuinely held out.

**Pre-registered threshold.** Newey–West *t* beyond 2.0 in the pre-committed direction on names that did not inform the observation, plus a positive verdict through `holdout_compare_panels`.

**Two things to carry.** The original dataset is 194 surviving large caps — 7% of the panel, ten years, zero delisted names — so the survivor bias is real and runs toward a positive. And the paper's own effect is documented as strongest in smaller, less-covered names, which is precisely the tier this dataset excludes. So a positive here on large caps would be *more* surprising than the literature predicts, not less, which is a reason for extra scepticism rather than excitement.

**Effort: M.** But it is a live, measured, unexplained −2.58 *t* sitting in a file marked null.

---

### S20 · Rank the composite instead of summing z-scores

The robust z-score rejection came with an unusually clean mechanism: rank-IC is invariant to a monotone rescaling, but *the composite is a weighted sum of z-scores and is therefore scale-sensitive*. MAD is smaller than SD for fat-tailed data, so dividing by the smaller scale inflates the tails, and the top decile ends up selected by whoever has one extreme reading.

The project diagnosed that mechanism precisely and then never applied the obvious remedy.

**The remedy.** Replace the z-score with a **cross-sectional percentile rank** before combining. Rank is bounded in [0,1], immune to outliers by construction, invariant to any monotone transformation of the underlying signal, and eliminates the entire class of scale-sensitivity bug — including the one that killed robust z-scores and the one that makes `neg_ev_sales` explode on negative EV (**B18**).

**Method.** Add a `standardisation` parameter with three settings: `z` (current), `rank`, and `winsorised_z` (**S21**). Run the full panel under each and gate.

**Pre-registered threshold.** The standard held-out gate. Report the top-decile alpha, the long-short *t*, and — the number that will decide it — the **turnover**, since a rank composite is typically more stable period to period than a z-score composite and therefore cheaper to trade.

**Why this could matter more than any single new signal.** It changes how *every* signal enters the model simultaneously. If the current composite is being driven by outliers in one or two inputs — and a fat-tailed panel of 2,710 names including microcaps makes that plausible — rank-combining would show up as a modest alpha change and a large stability improvement.

**Effort: S.** One of the highest value-to-effort ratios in the catalogue.

---

### S21 · Winsorise before standardising

Related and even cheaper. There is no winsorisation anywhere in the standardisation path. Cross-sectional z-scores on raw accounting ratios across 2,710 names will contain values many standard deviations from the mean — a company with near-zero equity produces an enormous `book_to_price`, one with near-zero EBIT produces an enormous `ebit_ev`.

The `sanity_check` range bounds exist and are wide (`book_to_price ∈ [−50, 50]`, `ebit_ev ∈ [−25, 25]`) and they *flag* rather than *clip*.

**Method.** Winsorise each signal at the 1st and 99th cross-sectional percentiles before z-scoring. Sweep 0.5/99.5, 1/99, and 2/98. Gate.

**Effort: XS.** Standard practice everywhere in the literature; absent here.

---

### S22 · Does the model have a term structure?

Three horizons were tested — 63, 252 and 756 days — and only 63 was accepted. The short end was never examined.

**Method.** Measure the composite's IC at 5, 10, 21, 42, 63, 126 and 252 trading days. Plot the decay curve.

**Three things this produces, all useful.** The optimal rebalance frequency falls out of it directly. The shape distinguishes a *mispricing* signal (fast decay, information gets incorporated) from a *risk-premium* signal (flat, you are being paid to hold exposure) — which is the same question **R1** asks, arrived at from a completely different direction, and the two answers should agree. And it tells Part V exactly what option tenor matches the signal, which **U1** currently has to guess at.

**Effort: S.**

---

### S23 · An exit rule for the equity book

The equity book has no stop-loss, no take-profit, and no drawdown rule. A name is held until it exits the decile at the next rebalance, however far it falls in between.

That is a defensible design — cross-sectional models generally should not stop out, because the signal is relative and a falling name may simply be getting cheaper. But it has never been *tested*, and the project has an entire research thread (**O1**) premised on exits mattering enormously for the options book.

**Method.** Test three rules against the current hold-to-rebalance baseline: a hard stop at −25% / −35% from entry; a stop conditional on the composite score itself deteriorating (which is the theoretically correct version — exit when the *reason* to hold disappears, not when the price falls); and a trailing stop from peak.

**Pre-register the likely outcome.** Hard price stops will probably hurt, because they sell into exactly the mean reversion a value tilt is trying to harvest. The score-conditional exit is the interesting one and it has no analogue anywhere in the project.

**Effort: S.**

---

### S24 · Ensemble the composite across bootstrap draws

Instead of one composite, compute the score many times over bootstrap resamples of the *signals* (not the names), and average the resulting ranks.

This is bagging, and it addresses the same fragility as **S20** from a different angle: an ensemble rank is far less sensitive to any single signal's outliers or to any single weight choice. It also produces a **dispersion measure per name** — how much the rank varies across draws — which is a defensible confidence figure for the product's per-name display and is currently unavailable.

**Effort: M.**

---

### S25 · Sector as a point-in-time field

Sharadar TICKERS supplies **today's** sector classification, applied to 1998 rows. That is the one non-point-in-time input in the entire panel, and it silently affects **S12**, **S15**, **B21** and the rejected sector-neutral work — every sector-aware result rests on it.

Companies do change classification, and they do so non-randomly: a company reclassified from Technology to Communication Services in the 2018 GICS restructure was a specific kind of company. Sector-aware conclusions drawn on today's map are therefore mildly forward-looking.

**Fix.** SIC codes are in the SEC Financial Statement Data Sets, dated per filing, free. Build a point-in-time sector map from them and re-run any sector-aware test against it. Or, at minimum, measure how many names have changed classification and report it as a caveat on every sector result.

**Effort: M.**

---

### S26 · Test the model's failure cases directly

**Method.** Extract the twenty worst-performing names the top decile held over the panel's history. For each, print the full signal vector at entry, the theme scores, and the composite. Then read them.

**Why a qualitative test earns a place in a quantitative catalogue.** Every statistical test in this document asks whether the average is positive. None asks *what the model is wrong about*, and models are usually wrong in patterned rather than random ways — a value tilt buys value traps, a quality tilt buys companies at peak margin, a momentum tilt buys the top of a run. Finding the pattern is what produces the next real signal, and it cannot be found by looking at averages.

This also feeds the product directly. Roadmap item #32 wants a per-name "why this score" attribution; this exercise is the same machinery pointed at the cases where the score was wrong, which is far more informative about the model than the cases where it was right.

**Effort: S.**

---

### S27 · Weight recent observations more

Every IC is a full-sample median. Every weight is fixed. Given that the project has documented `size` flipping sign around 2012 and the options edge halving over the same window, the assumption that a 1999 observation and a 2025 observation carry equal information is doing real work and has never been examined.

**Method.** Estimate signal ICs with an exponentially-weighted mean at half-lives of 3, 5 and 10 years, and derive weights from those. Validate under CPCV against the full-sample equal weighting.

**Run this after X6**, not before — if the structural-break test says these are breaks rather than drift, the correct response is a regime split rather than exponential weighting, and the two remedies are not interchangeable.

**Effort: S.**

---

### S28 · Value the tails of the model, not just its centre

Every equity metric in the project is a mean or a median: median IC, mean decile return, mean spread. Nothing measures the distribution.

**Method.** For the top decile, report the full return distribution per period — skewness, kurtosis, the 5th and 95th percentiles, the fraction of names with returns below −30%, and the fraction above +50%. Compare against the equal-weighted universe.

**Why this matters for the product specifically.** A concentrated 25-name book is held by a person, and people experience distributions, not means. If the top decile achieves its alpha through a handful of large winners and a long tail of mild losers — which is the characteristic shape of a momentum-inclusive composite — then the user experience is mostly disappointment punctuated by occasional vindication, and the product's framing needs to say so *in advance*. The options side already has this discipline: the confidence display is expressly framed as expectancy, never as win probability, precisely because the hit rate is 37%. The equity side has no equivalent and probably needs one.

**Effort: S.**

---

# PART XI — Options: further tests

Eight more.

---

### O19 · Whole-contract sizing systematically over-weights cheap options

Sizing is a fixed dollar risk budget filled with whole contracts. A $5.00 contract gets two; a $0.50 contract gets twenty.

Cheap options are not a random sample. They are further out of the money, shorter dated, lower delta, wider in percentage spread, and structurally more lottery-like — which is precisely the population Boyer and Vorkink identify as systematically overpriced (**O4**). So fixed-dollar-risk whole-contract sizing places the largest *contract counts* on the contracts most likely to be overpriced, and the aggregate expectancy is a contract-weighted average that leans toward them.

The project has already found and fixed one sizing artefact — the "too tail-dependent" scare turned out to be one-contract-per-signal sizing. This is the same class of question about the fix.

**Method.** Report expectancy three ways: equal-weighted per trade (current), contract-weighted, and dollar-weighted. Then re-run with a minimum premium floor of $1.00 and $2.00 and see whether the edge concentrates in or away from cheap contracts.

**Effort: XS.** It is a re-aggregation of the existing log.

---

### O20 · The option universe was selected with hindsight, and the fix is cheap

The record already contains the finding: the mined cache is biased toward names that did well, and **the bias runs toward the edge**. Names were selected for mining by *current* liquidity, and current liquidity is a function of how the company did over the sample.

**Fix.** Select the option universe by **point-in-time** liquidity — the names that were liquid *as of* each entry date, using the open interest and volume already in the cache — rather than by the names that are liquid today. This is a filter applied at evaluation time, not a re-mine, so it costs nothing but a re-run.

Then re-report the headline. **Expect it to fall.** That is the correct number.

**Effort: S.**

---

### O21 · The pricing model ignores dividends on names that pay them

The greeks layer documents its own zero-dividend approximation, and `blackscholes.py` implements a European model applied to American options.

For a 45–75 DTE call on a dividend-paying megacap — which is most of the 55-name universe — an ignored dividend biases the implied vol solve and the delta. It also removes the possibility of early exercise, which for a deep in-the-money call ahead of a large dividend is a real event with a real cash consequence.

**Method.** Quantify before fixing: for each name, compute the total dividend within the option's life as a fraction of spot, and split the trade log by that fraction. If the effect is confined to a handful of high-yield names it can be documented and left. If it correlates with anything in the results, the pricing needs a dividend term — and the ACTIONS dividend data is already on disk and, per **R8**, already unused.

**Effort: S.**

---

### O22 · How many alerts could a real account actually take?

The book has no capital constraint, so every alert becomes a position. In practice a $50,000 account at a $1,000 risk budget can hold perhaps fifty concurrent positions at absolute maximum, and far fewer with any prudence.

**Method.** Replay the alert stream with a capital constraint and a concurrency cap. When more alerts fire than capacity allows, apply a selection rule — highest confidence, best `term_slope`, first-come — and measure the realised expectancy of the *taken* subset versus the full population.

**Why this could go either way, which is what makes it worth running.** If the selection rule picks better than average, the constrained book beats the unconstrained one and the constraint is a feature. If it picks worse, capacity is destroying edge and the sizing needs rethinking. And there is a third possibility worth pre-registering: alerts may cluster in time — a volatility event fires many at once — so the constraint may bind exactly when the opportunity is richest, which would be the worst case and is entirely plausible given a long-vol strategy.

**Effort: S**, and it composes with **O11**.

---

### O23 · Test the exit against the underlying, not just the option

Noted inside **O1** but it deserves its own line, because it is the only exit variant that uses information the current exit is structurally blind to.

The exit loop sees option quotes and nothing else. It cannot know that the stock has broken its 50-day moving average, that the technical score which generated the alert has collapsed, that the company has pre-announced, or that the sector has rolled over.

**Method.** Add underlying-conditional exits to the **O1** sweep: close on a 50-day moving-average break; close when the generating signal's score falls below its entry value by a set margin; close on a volatility-regime change measured on the underlying.

The second is the theoretically motivated one — exit when the reason to be in the trade has evaporated — and it is the direct analogue of **S23** on the equity side. Neither book has ever had it.

**Effort: S** as an extension of **O1**.

---

### O24 · Measure how much of `term_slope` is an earnings calendar

Flagged inside **O16** and worth isolating. A near-dated earnings announcement lifts the front expiry's implied vol, which produces backwardation, which suppresses the alert. If that is most of what `term_slope` does, then the only surviving options signal in the programme is an earnings-avoidance rule wearing a volatility-surface costume.

**Method.** Compute the distribution of days-to-next-announcement for alerts that pass the `term_slope` gate versus those that fail it, using EVENTS code 22 rather than filing dates. Then test a plain earnings-proximity filter head to head against `term_slope` through the same gate.

**Pre-register both readings.** If a plain earnings filter matches `term_slope`'s performance, adopt it instead — it is simpler, more robust, computable without an options chain, and it would work on names that have no mined surface at all, which multiplies the tradeable universe. If `term_slope` beats it, the signal has genuine volatility-structure content beyond the calendar and that is worth knowing too.

**Effort: S.**

---

### O25 · Sell the wing you are already long

A single-leg long call has one economically obvious partner: sell a further out-of-the-money call against it once the position is deeply profitable, converting a long call into a spread **after** the move rather than before it.

The vertical-debit-spread rejection does not cover this. That test entered as a spread and lost because the +100% target sat at or above the spread's ceiling, truncating winners while the stop still fired — a target-rule mismatch, correctly diagnosed in the record. Converting *after* a large move is a different trade with a different payoff: the upside is already banked in the long leg's value, and the short wing monetises the volatility premium at the point where it is richest.

**Method.** On the existing trade log, at each point where a position reaches +75% or +100%, test selling a 15-delta call in the same expiry instead of closing. Measure the resulting distribution against both closing and holding.

**Pre-register the risk.** This caps exactly the tail that carries the book — 30.7% of trades return over +100%. It will very likely reduce expectancy and improve consistency. Whether that is a good trade depends on **O12**'s risk-of-ruin answer, which is why the two should be read together.

**Effort: S.**

---

### O26 · Put a floor under the sample before believing any bucket

The record already flags that the `small` tier is 33 trades on 10 names with 14.78× median hindsight market-cap growth, calls it "the most contaminated cell in the study," and says to ignore it — and it still appears in the shipped tier table.

The `MIN_CLOSED_PER_BUCKET = 30` floor exists but 33 clears it by three, which is not a meaningful margin for a distribution with this much tail.

**Fix.** Raise the floor for any *reported* bucket to something defensible for a fat-tailed distribution — 100 trades and 25 distinct names would be a reasonable pre-commitment — and have the results writer **omit** rather than emit sub-threshold cells. A cell that must not be quoted should not be printed; the record shows that a warning in prose does not survive contact with a table.

**Effort: XS.**

---

# PART XII — Unification: three more

---

### U6 · Express the rebalance with options instead of a market order

The most IRA-legal, structurally sensible link between the two books is not a directional bet. It is using options to execute the equity book's own rebalance.

**Cash-secured puts on names entering the decile.** When the model says buy a name at the next rebalance, sell a 30-delta put roughly a month out instead of buying the shares. Either the put expires and you keep the premium, or you are assigned and you own the stock you wanted at a lower net cost. You are being paid to enter a position you had already decided to take.

**Covered calls on names leaving the decile.** When a name drops out and is scheduled to be sold, sell a 30-delta call against the existing shares instead of selling immediately. Either it expires and you keep the premium plus the shares for another period, or it is called away at a higher price than the market order would have got.

**Why this fits this project specifically.** Both are defined-risk and IRA-permitted — no naked positions, no margin. Both harvest the variance risk premium in its most robust and most retail-accessible form, without the execution problem that killed the credit-spread arm (one leg, not four crossings). Both use the equity model's existing decisions rather than requiring a new signal. And the tax treatment is favourable relative to long single-stock options, which are 100% short-term.

**The honest risk, stated plainly.** This trades away the right tail. A cash-secured put caps your upside at the premium if the stock gaps up, and a covered call caps it if the exiting name rips. On a momentum-inclusive composite, some exiting names do rip. This is a *return-shaping* trade, not a return-increasing one, and the test must measure the give-up as carefully as the pickup.

**Method.** Replay the equity book's entries and exits over the panel, substituting the option expression, using the mined chains for the names where they exist. Report total return, the assignment and call-away rates, the premium collected, and — critically — the return forgone on the names that moved through the strike.

**Effort: M.** It is the most immediately tradeable idea in Part V, and it is absent from every roadmap.

---

### U7 · Use the equity model to *veto* options trades, not to generate them

**U1** proposes the composite as an options entry signal. The weaker, cheaper, more likely-to-work version is the inverse: keep the existing alert generation, and simply refuse any alert on a name in the **bottom** decile of the composite.

**Why this is the better first test.** A veto needs only that the composite's bottom decile underperforms — which the monotonicity of −0.95 already establishes — whereas an entry signal needs the top decile to move enough, within the contract's life, to overcome decay and spread. The veto is a strictly easier bar and it is one line of code.

**Method.** On the banked alert log, split alerts by the underlying's composite decile at the alert date and report expectancy per decile. Then test the simple filter.

**Pre-register.** Coverage will be the constraint — alerts fire on names in the options cache, and the composite covers the full panel, so the join should be near-complete on the mined names. Report the retention rate; a veto that discards 10% of alerts and lifts expectancy is adoptable, one that discards 60% is a different strategy.

**Effort: S.** It should probably run *before* **U1**, as the cheap probe of the same hypothesis.

---

### U8 · One risk budget across both books

The equity book sizes by equal weight within a decile. The options book sizes by a fixed dollar risk budget per trade. Neither knows the other exists.

If the two are run from the same capital — and they are — then the combined exposure is unmanaged. A volatility event that fires twenty options alerts simultaneously is also the event in which the equity book is drawing down, and nothing anywhere accounts for that.

**Method.** Define a single risk budget. Allocate between the two arms by their measured contribution to combined drawdown rather than by a fixed split. Use the Ledoit–Wolf machinery already built for the VRP arm, applied across arms rather than within one.

**Effort: M**, and it depends on **O11**.

---

# PART XIII — The second codebase

`options-bot/` is a separate, largely independent system containing a screener, a backtest engine, a point-in-time universe builder and four live strategies. The main research programme has audited itself carefully. This subsystem has not been audited to the same standard, and several of its problems are more serious than anything in Part I — because unlike the research code, some of it is live.

Seven items.

---

### C1 · Two scoring models coexist, and the backtest does not test the live one

`options-bot/screener/scoring.py` is the live scorer. `run_backtest.py` **never imports it**. It defines its own weights inline:

```python
WEIGHTS = {"ey_sn": .30, "roe": .10, "opm": .10, "neg_lev": .10, "mom": .20, "growth": .20}
```

No bucket split. No insider score. No DCF. No gates. And `ey_sn` **does not exist in the live model at all**.

The consequence is direct: **the screener backtest does not measure the screener.** Whatever it reports is a property of a model nobody ships. And the insider component — which carries 20–30% of the live weight — has therefore never been backtested in any form.

**Fix.** Make `run_backtest.py` import and call `scoring.py`. If the live scorer cannot be replayed historically, that is the finding, and it should be recorded as such rather than papered over with a parallel model.

This is the same defect class as **B7** on the equity side — selection, measurement and live disagreeing — but more severe, because here the two models do not merely differ in missing-data handling, they share almost no inputs.

**Effort: M.**

---

### C2 · The backtest universe is the exact inverse of the target universe

`run_backtest.py` builds its universe from `all_filers().keys()[:300]`. The SEC's company-tickers file is ordered by **market capitalisation, descending**. So the first 300 entries are the ~300 largest US companies.

The screener's stated target is sub-$10B names.

Every backtest result from this system was therefore measured on megacaps and applied to small caps — the two tiers where the equity programme's own regime split shows the *most* different behaviour.

**Fix.** Build the universe from the point-in-time module (`core/pit_universe.py`), which already exists and already refuses to filter on `scalemarketcap`/`scalerevenue` on the correct grounds that max-observed-over-lifetime is look-ahead.

**Effort: S.** The correct component is already written; it just is not wired.

---

### C3 · One of four live strategies has never been backtested at all

`run_backtest.py` supports `trend` and `momentum`. **`--bots reversion` silently does nothing and prints "Backtests complete."**

A flag that accepts an argument, runs nothing, and reports success is worse than an unimplemented flag, because it produces a clean-looking result that a reader will interpret as evidence.

**Fix.** Either implement it or make the flag error. Then backtest the reversion strategy before it trades anything.

**Effort: XS to fail loudly, M to implement.**

---

### C4 · The self-improvement loop is wired to nothing and reviews an empty table

`store.update_returns`, `prices.benchmark_return`, `config.BENCHMARKS` and `config.TRACK_HORIZONS_DAYS` are all implemented. **Nothing calls any of them.**

So `ret_7`, `ret_30` and `ret_90` stay NULL forever — and `run_review` hands an all-NULL table to Claude for self-assessment. Its only guard is a **row count**: rows exist, values do not. The review therefore always runs, always finds nothing, and always reports success.

**Why this is the most valuable thing in Part XIII to fix.** This loop is supposed to accrue real dated forward returns on real picks — proprietary, look-ahead-free, and over time worth more than any historical backtest, because it is the only data in the entire project that nobody has looked at. It has been silently accruing nothing.

**Fix.** Wire the loop. Add a guard that fails when the fraction of non-NULL returns falls below a threshold — the same "a guard whose input is computed elsewhere is not a guard" principle as **M3**.

**Effort: S.** High value; it starts a clock that cannot be started retroactively.

---

### C5 · The point-in-time universe has only ever been tested against a synthetic mirror

`core/pit_universe.py` rebuilds a survivorship-free universe from `firstpricedate <= D <= lastpricedate` and reports how many names in each historical universe are invisible to a live screener today — a figure the module correctly describes as *being* the bias the old results carried. `AsOfHistory` provides a structural look-ahead backstop.

Both were verified end to end **only on a synthetic 30-name mirror where 8 names delist mid-window**. No real-data run is recorded anywhere.

The bias the module exists to remove is quantified in the record in unusually plain terms: a 2021–2024 momentum backtest traded the 150 largest companies *as of today*, filtered on today's price and cap, sorted by today's size, on every day of the window — pre-selecting the winners of the period being measured.

**Fix.** Run `scripts/run_sharadar_backtest.py` on real data before the Sharadar subscription lapses (see **D10**). Report the invisible-name count per period, which is the number that quantifies every prior result's bias.

**Effort: S**, and it is time-limited.

---

### C6 · Three fixed bugs sit in the repository undeployed

The record shows three defects found, fixed in the repo, and **not deployed**: exit orders silently dropped in simulation, reversion shorts oversold names in a selloff, and risk limits doing nothing in simulation.

Each of those is a correctness bug in an execution path. "Fixed in repo, not deployed" is a state that decays — it is forgotten, and then someone assumes the deployed system has the fix.

**Fix.** Deploy them, or if they are superseded, delete them and say so in the record. Do not leave them in the third state.

**Effort: XS to decide.**

---

### C7 · The CI gate covers one suite of fifteen

`.github/workflows/land-agent-branch.yml` auto-merges every `worktree-*` push into `main` behind a test gate, and Render auto-deploys. That hands-off pipeline is genuinely good infrastructure and it is doing real work.

But the gate runs **only `tests/test_edge.py`**. The other fourteen suites — bulk, engine, intraday, screener, saas, options-greeks, paper-track, calibration, freeze, lazy-prices, lazy-prices-ic, security, sector-neutral, ev-multiples — do not gate a deploy. Roughly 464 tests exist; a fraction of them can block a merge.

Given that this catalogue proposes changes to `options_universe.py`, `options_backtest.py`, `paper_track.py`, `factors.py` and `screen.py` — none of which `test_edge.py` covers in full — the gate should be widened **before** Part I begins, not after.

**Fix.** Add the suites to the workflow. Accept the longer CI time; it is cheaper than an auto-merged regression reaching production.

**Effort: XS.** Do this first, before any Part I edit lands.

---

# PART XIV — Product, capacity and crowding

Five items that are not research questions but are risks the research implies, and none appears in the roadmap.

---

### P1 · Capacity has never been estimated

The strategy holds a 25-name book with a deliberate small-cap tilt (`size` is one-seventh of the composite) at roughly 249% annual turnover, and the cost model is keyed on market capitalisation with **no participation-rate term at all**.

That is fine for one personal account. It is not obviously fine for a product.

**Method.** For each historical book, compute the position size as a fraction of each name's average daily dollar volume at a range of assumed assets under management — $1M, $10M, $50M, $250M. Report the number of positions exceeding 5% and 10% of ADV, and re-run the cost model with a square-root participation term rather than a flat basis-point figure.

**What it produces.** A capacity number: the AUM at which the modelled cost crosses the measured breakeven. Every real strategy has one, and a small-cap-tilted quarterly-rebalanced book will have a lower one than intuition suggests.

**Why this belongs on the roadmap now rather than later.** It determines whether the product can ever be a managed vehicle or must remain a research tool that users implement themselves — which is a strategic decision that affects pricing, positioning and regulatory posture, and it is much cheaper to know before launch than after.

**Effort: S.** The ADV data is in SEP, already on disk, and currently unused (per **B13**, the liquidity screen has never once bound).

---

### P2 · The product's users are a crowding mechanism

The Index tab publishes holdings. If the product succeeds, some number of users buy the same 25 small-cap names within a short window of each other, on the same quarterly cadence.

That is a self-inflicted crowding problem with three distinct effects: entry prices move against the cohort at each rebalance; the alpha decays as the trade becomes consensus among a growing group; and — the one that is genuinely dangerous — exits correlate, so a drawdown becomes a coordinated sell into the same illiquidity.

McLean and Pontiff measured this for published anomalies: returns fall 26% out of sample and 58% post-publication. A product that publishes its holdings daily is running an accelerated version of that experiment on itself.

**Method.** Model it. At *N* users each deploying *X* dollars, what fraction of each name's ADV does the cohort represent at a rebalance? Combine with **P1**'s participation-cost curve to get the price impact, and subtract it from the published alpha as a function of subscriber count.

**Mitigations worth testing, all cheap.** Stagger rebalance dates across users — this composes directly with **X2**'s grid-offset ensemble, and if that ensemble performs comparably it solves two problems at once. Publish holdings on a lag. Widen the book beyond 25 names for the published version while keeping a concentrated version private. Or lean into transparency and publish the capacity estimate itself, which is the move most consistent with the project's existing positioning.

**Effort: M.**

---

### P3 · A 37% hit rate needs to be designed for, not just disclosed

The options book wins 37% of the time. The record shows the confidence display was already corrected once to frame expectancy rather than win probability, which was the right call.

But disclosure is not the same as design. On a 37% hit rate, a run of six consecutive losses has a probability of roughly 6%, which means it happens routinely. A user who sees "high confidence" and then loses six times will conclude the product is broken, and they will be reasoning correctly from the evidence they have been given.

**What to build.** Show the *expected* loss streak alongside the expectancy, before the user takes the first trade. Show the running track against the modelled distribution, so a bad run reads as "within the expected band" rather than as failure. And make the sizing recommendation from **O12** prominent, since the actual defence against a 37% hit rate is position sizing, not conviction.

This is product work, but it is downstream of a research number and it will determine whether the research ever gets used properly.

**Effort: M.**

---

### P4 · The live track needs its rules fixed before it accumulates, not after

Beyond the four defects in **B5**, the record notes one more that is arguably worse: `seed_book` adds new names and never resets an existing entry price, and **it does not sell names that leave the book.** A track that silently drops losers is worthless — and worse than worthless, because it produces a curve that looks like evidence.

Rebalance is not automated. Until it is, the Index track measures a book that only ever adds.

**Fix.** Implement the sell side of the rebalance and add an assertion that the tracked holdings match the model's current decile at every rebalance date. Fail loudly on divergence.

**Do this before the track accumulates further.** It has one session of roughly 126. Every session that passes with the wrong rules is a session that has to be discarded.

**Effort: S.** The highest-urgency item in Part XIV.

---

### P5 · Decide what the product claims before R1 answers

**R1** will return one of two answers, and they imply different products.

If the excess return survives factor adjustment, the claim is "we find alpha," and the supporting evidence is the regression intercept and the forward track.

If it does not, the claim is "we deliver diversified factor exposure, transparently, with an honest live track, and here is exactly what it is." That is a *smaller* claim and a more defensible one — and the natural competitor becomes a cheap factor-ETF blend (**X4**), so the marketing has to compete on construction quality, freshness, transparency and tax awareness rather than on a return number.

**Why decide the framing in advance.** Because the alternative is deciding it after seeing the number, and that is how a research programme with excellent discipline acquires a marketing department that quietly stops citing the test. Write both versions of the product claim now, while the answer is unknown, and commit to publishing whichever one the regression supports.

The project's stated moat is honesty and auditability. This is the single decision that most tests whether that is real.

**Effort: XS**, and it costs nothing but nerve.

---

# PART XV — Sequencing and full backlog

Supersedes nothing above; this is the ordering across all one hundred and eight items.

---

## The recommended order

**Before anything else — two housekeeping items, both cheap and one time-limited.**
Widen the CI gate (**C7**) so the auto-merge pipeline actually protects the files Part I edits. And run one backtest from the Sharadar freeze plus the documentation extraction (**D10**, **C5**) before the subscription lapses — that window closes and does not reopen.

**Session 1 — the cheap corrections.** B1, B3, B10, B12, B14, B15, B16, B18, B19, B20, B24, B26, plus the B9 relabel. All extra-small. Kick off the B1 re-run at the end so it works overnight.

**Session 2 — the corrections that need thought.** B2, B4, B5, B7, B11, B13, B17, B21, B22, B23, B25. Then begin B6, the longest item in Part I.

**Session 3 — establish the noise floor before trusting any threshold.** **X7** (the placebo through the full pipeline) and **X2** (rebalance-grid offset). Together these tell you how big a number has to be before it means anything, and how stable the headline is. Everything downstream is easier to interpret once they exist, and both are cheap.

**Session 4 — the test that decides the story.** **R1**, factor-adjusted alpha, alone and carefully, with **X4** (the factor-ETF benchmark) in the same session since they answer the same question from two directions. Then R9 and R10. **Do not start Parts III–V until this returns.** Its answer determines whether further signal hunting is worth anything, or whether construction, cost, tax and capacity work is the entire remaining edge.

**Session 5 — re-derive the options conclusions.** R2 and R3 together, with R7 committed *before* re-scoring. Add **O20** (point-in-time universe selection) to the same run, since it changes the same headline and costs nothing extra.

**Session 6 — the cheap probes of the big ideas.** **U7** (the composite as an options *veto*) and **X3** (ablate to the best single signal). Both are one-line tests of hypotheses that would otherwise take a full session, and both can kill or promote a much larger item.

**Session 7 — the unification proper.** U2, then U1, then U6. U2 first: it feeds the programme that works.

**Session 8 onward, in descending value.** O1 (the exit sweep, now unblocked). S20 and S21 (rank and winsorised composites — highest value-to-effort on the stock side). X1 (universe-split validation). S2, S19, X8, O2, O6, S1, S10, O15, C1–C4, P1, P4, S5.

---

## Full backlog by part

Effort: **XS** under an hour · **S** a few hours · **M** most of a session · **L** more than one session.

### Part I + IX — corrections (26)

| ID | Item | Effort | Value |
|---|---|---|---|
| B1 | Price basis in `options_universe` (`:327`, `:594`) | XS + M | Critical |
| B7 | Unify the three composite functions | M | Critical |
| B6 | Panel truncation and the two date ranges | M | Critical |
| B5 | Four paper-track defects | S | High |
| B2 | Exit-path quote censoring | S | High |
| B8 | Holdout rule versus its documentation | S–M | High |
| B13 | Run `prefilter` in the backtest | S | High |
| B4 | OI sentinel reaching `chain_summary` | S | High |
| B17 | "Top-25 hold" holds fifty, pays no costs or taxes | S | High |
| B22 | Results file can lose four blocks silently | S | Medium–High |
| B11 | Compute the 37 bps figure | S | Medium |
| B12 | Alphabetical universe in `WRDSProvider` | XS | Medium |
| B9 | DSR / PBO trial accounting | XS–S | Medium |
| B10 | `accruals_q` silent overwrite | XS | Medium |
| B3 | Stale-quote expiry marks | XS | Medium |
| B18 | Negative EV read two opposite ways | XS | Medium |
| B21 | `_sector_capped` implemented, never invoked | XS | Medium |
| B23 | Four panel builds per run | S | Medium |
| B25 | Three Deflated Sharpe conventions | S | Medium |
| B19 | Every "Sharpe" uses rf = 0 | XS | Low–Medium |
| B20 | `earnings_yield` numerator switches mid-section | XS | Low–Medium |
| B15 | Commission in `return_pct` | XS | Low |
| B14 | Ship delisting-mask coverage | XS | Low |
| B16 | Quarantine the dead exit module | XS | Low |
| B24 | `sanity_check` double-counts axes | XS | Low |
| B26 | Same-day insider / grades inclusion | XS | Low |

### Part II — re-derivations (10)

| ID | Item | Effort | Value |
|---|---|---|---|
| R1 | **Factor-adjusted alpha (FF5+MOM, q-factor)** | S | **Highest in document** |
| R2 | Re-run the broad options study after B1 | M | Critical |
| R3 | Clustered inference for the options book | M | Critical |
| R8 | Total return instead of price-only | M | High |
| R5 | Four classic anomalies on the full universe | S | High |
| R4 | Project-level multiple-testing accounting | M | High |
| R10 | Investable benchmark comparison | S | Medium |
| R6 | SF3 conviction family on the full universe | XS–S | Medium |
| R9 | t-statistic on the headline; HAC on long-short | XS | Medium |
| R7 | Re-commit the `term_slope` retention floor | XS | Medium |

### Part IX — robustness (8)

| ID | Item | Effort | Value |
|---|---|---|---|
| X7 | **Placebo through the full pipeline** — calibrates every threshold | M | Very high |
| X1 | **Split on universe, not time** | M | Very high |
| X3 | Ablate to the best single signal | S | Very high |
| X4 | Benchmark against a cheap factor-ETF blend | M | High |
| X2 | Rebalance-grid offset sensitivity | S | High |
| X8 | Replicate the theme structure on JKP / another country | M | High |
| X6 | Structural-break test (Bai–Perron) | M | Medium |
| X5 | Bootstrap the entire pipeline | L | Medium |

### Parts III + XI — stock (28)

| ID | Item | Effort | Value |
|---|---|---|---|
| S20 | **Rank composite instead of z-score sum** | S | Very high |
| S2 | Register `cash_op_prof` | XS | High |
| S21 | Winsorise before standardising | XS | High |
| S19 | The MD&A anomaly left on the table | M | High |
| S1 | Fix the value theme's inputs (a/b/c) | S | High |
| S10 | Downside-exclusion screen | M | High |
| S22 | Term structure of the signal | S | Medium–High |
| S3 | Rebuild the insider score (a/b/c) | S | Medium–High |
| S26 | Read the twenty worst holdings | S | Medium–High |
| S5 | Hierarchical shrinkage across themes | L | Medium–High |
| S24 | Ensemble the composite across draws | M | Medium |
| S9 | Fundamental-data staleness conditioning | S | Medium |
| S7 | Pre-registered interactions | M | Medium |
| S13 | Volatility-targeted weighting in the book | S | Medium |
| S23 | Exit rule for the equity book | S | Medium |
| S16 | Decompose net issuance | M | Medium |
| S14 | Re-decide the no-trade band on net alpha | S | Medium |
| S11 | Horizon ensemble (63 + 252) | S | Medium |
| S28 | Distribution, not just the mean | S | Medium |
| S6 | Factor momentum on theme series | M | Medium |
| S12 | Rank within bucket | S | Medium |
| S27 | Weight recent observations more | S | Medium |
| S25 | Point-in-time sector map | M | Medium |
| S8 | Signal-freshness weighting | M | Medium |
| S4 | Growth theme carries zero weight | XS | Low–Medium |
| S18 | Short interest as an interaction | S | Low–Medium |
| S17 | Decode the rest of EVENTS | M | Low–Medium |
| S15 | Sector-relative on value only | XS | Low |

### Parts IV + XII — options (26)

| ID | Item | Effort | Value |
|---|---|---|---|
| O1 | **Exit sweep, including on random entries** | M | Highest in options |
| O20 | Point-in-time option-universe selection | S | High |
| O2 | Cross-sectional VRP (Goyal–Saretto) | M | High |
| O6 | Cheapest-on-surface contract selection | S | High |
| O15 | Re-mine beyond 90 DTE | M + mining | High |
| O11 | Portfolio layer for the single-leg book | S | High |
| O24 | Is `term_slope` an earnings calendar? | S | High |
| O22 | Capacity-constrained alert replay | S | Medium–High |
| O8 | Index VRP — run the existing backtest | XS → M | Medium–High |
| O13 | Anti-signal decomposition | S | Medium–High |
| O10 | Passive-limit fill model | M | Medium–High |
| O23 | Exits conditioned on the underlying | S | Medium–High |
| O19 | Whole-contract sizing over-weights cheap options | XS | Medium |
| O7 | Earnings straddles + implied/realised diagnostic | M | Medium |
| O16 | Is `term_slope` a front-IV level? | S | Medium |
| O12 | Fractional Kelly and risk of ruin | S | Medium |
| O25 | Sell the wing after the move | S | Medium |
| O3 | Delta-hedged returns vs idio vol | M | Medium |
| O17 | Earnings filter for the long arm | S | Medium |
| O21 | Dividends and early exercise | S | Medium |
| O14 | Tick flow, alert days only | S + pull | Medium |
| O5 | Volatility of volatility | XS | Low–Medium |
| O18 | Spread-conditional cost model | S | Low–Medium |
| O26 | Raise the reporting floor per bucket | XS | Low–Medium |
| O9 | IV rank as a sell-timing rule | S | Low |
| O4 | Expected idiosyncratic skewness | L | Low (diagnostic) |

### Parts V + XIII — unification (8)

| ID | Item | Effort | Value |
|---|---|---|---|
| U7 | **Composite as an options veto** — the cheap probe | S | Very high per hour |
| U2 | **Options surface → stock signals** | M | Highest new-signal item |
| U1 | **Stock composite → options entry** | M | Highest untested idea |
| U6 | Cash-secured puts in, covered calls out | M | High |
| U5 | Tax-aware arm allocation | XS | High (already measured) |
| U3 | Convex overlay sized as insurance | S | Medium–High |
| U8 | One risk budget across both books | M | Medium |
| U4 | One decision object | L | Product |

### Part XIII — the second codebase (7)

| ID | Item | Effort | Value |
|---|---|---|---|
| C7 | **Widen the CI gate — do this first** | XS | High |
| C4 | Wire the forward-return tracking loop | S | High |
| C1 | Backtest the model that actually ships | M | High |
| C2 | Universe is the inverse of the target | S | High |
| C5 | Run the PIT universe on real data | S | High (time-limited) |
| C3 | `--bots reversion` silently does nothing | XS–M | Medium |
| C6 | Three fixed-but-undeployed bugs | XS | Medium |

### Part XIV — product, capacity, crowding (5)

| ID | Item | Effort | Value |
|---|---|---|---|
| P4 | **Fix the track's rules before it accumulates** | S | Urgent |
| P1 | Estimate capacity | S | High |
| P5 | Decide the product claim before R1 answers | XS | High |
| P2 | Model user crowding | M | Medium–High |
| P3 | Design for a 37% hit rate | M | Medium |

### Part VI — data (10)

Covered in full in Part VI. The three that need action irrespective of any research outcome: **D1** (Sharadar direct at $29/mo — check the current bill), **D2** (which ThetaData tier, and the commercial-licence question), **D10** (freeze verification and documentation extraction, time-limited).

---

## Do not re-open

Each has an understood *mechanism* for failing, not merely an unfavourable number. Re-opening requires new data or a new mechanism, not a new parameterisation.

| Item | Why it stays closed |
|---|---|
| **TTM ROE/ROIC** | Quarterly measurably better (roe *t* +2.84 vs +2.01; roic +3.38 vs +2.57). Recency beats smoothing |
| **Median/MAD robust z-scores** | Halves the long-short *t*; mechanism understood. Note **S20** and **S21** attack the same underlying problem correctly, by removing scale-sensitivity rather than changing the scale |
| **Momentum + institutional consolidation** | +0.50 correlated but complementary; both earn a full weight |
| **Sector-neutral as a wholesale change** | Buys long-short *t*, sells top-decile alpha, doubles PBO. Wrong trade for a long-only book; rejected twice. (**S15** and **B21** are different interventions) |
| **`iv_rank` as an entry filter** | Three independent tests, negative both directions, destructive at year level. (**O9** tests a different hypothesis) |
| **Stock ML tree combiner at current data size** | 110 dates × 8 themes cannot support interaction search. (**S7** is the tractable version) |
| **Single-name put credit spreads as implemented** | Mid-fill ceiling is PF 1.02 — break-even. No premium is being lost to execution because there is no premium, on these instruments. (**O8**, **U6** are different instruments) |
| **Vertical debit spreads with the single-leg exit rule** | Target sits at or above the spread's ceiling, truncating winners while the stop fires normally. Re-test only after **O1**. (**O25** is a different structure) |
| **Conviction tier for options** | Fitted on ~15 tail points; does not predict out of sample |
| **65–75 DTE band** | Failed held-out; and live chains resolve to a single 49-DTE expiry, so the bucket is unreachable in practice |
| **Lazy Prices as originally specified** | Null across a 28-cell grid. But see **S19** — the MD&A reverse-direction result is a separate, live, untested hypothesis |
| **Zeroing `insider`** | `not_replicated`, Δt +0.08 / −0.09 — no evidence either way. Not a validation of keeping it either; see **S3** |

**Two cells that must never be quoted**, both flagged in the project's own record and both still present in shipped output: the options `small` tier (33 trades, 10 names, 14.78× median hindsight cap growth), and the concentrated top-25 stock book at +27.9% CAGR. **O26** and **B17** address the fact that a prose warning has not been enough to stop either from being printed.

---

## Closing note

One hundred and eight items is a lot, and most will come back negative. That is the correct expectation and it is worth stating plainly, because the alternative reading — that a long catalogue implies a long list of available improvements — is exactly the error this project has been careful to avoid.

The items that would most change things are few and they are not evenly distributed.

**R1** determines whether the equity model produces alpha or efficient factor exposure, and that single answer reshapes the roadmap more than any signal in the catalogue. **X7** determines how large any number has to be before it means anything, and it is the missing calibration under every threshold the project uses. **B1** determines whether the options entry signal is genuinely worse than random or whether that conclusion rests on a corrupted price. **X1** adds an entire validation axis the programme has never used. **U1**, **U2**, **U6** and **U7** connect two research programmes that have run in parallel for months without ever touching. **P4** protects the only genuinely out-of-sample instrument either programme has, and it is urgent in a way nothing else here is, because every session that accumulates under the wrong rules is a session that has to be thrown away.

Everything else is incremental.

The project's real asset is not any individual signal. It is that the research record is honest enough that an outside audit could find these things at all — corrections written in place rather than quietly replaced, rejections kept with their numbers, caveats that survive from session to session, and a methodology rule strict enough that its own violations are visible. Most quantitative projects at this scale cannot be audited, because there is nothing to audit against.

That property is worth more than the edge, and it is worth protecting deliberately rather than incidentally. The corrections in Parts I and IX are, in the end, mostly about making the measurements match the labels the record already applies to them — and the robustness work in Part IX is about finding out how much of the rest survives being looked at from a second angle.
