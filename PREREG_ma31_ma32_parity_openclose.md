# PRE-REGISTRATION — `MA31` (matched-strike parity deviation) + `MA32` (open-vs-close volume)

**Status: REGISTERED, NOT RUN. Committed ALONE — one `.md`, zero `.py` — as a strict git ancestor
of every commit that computes an arm.** No arm value, no IC, no verdict existed anywhere when this
file was written. The premise facts in §0 are facts about **what is on disk**, measured before this
file and reported here so the design is built against reality rather than against the audit's
description of it; none of them is an arm and none carries a threshold.

**ADOPTS NOTHING.** No file under `valuation/` that the live product imports changes behaviour.
Both items are `HYPOTHESIS`-class and **charge trials**, which is precisely why they were kept out
of the wave-2 correctness batch: `MA31` was mis-listed as wave 2 in the dispatch brief and is
wave 3.

---

## 0. Premise facts — measured BEFORE this register, none of them an arm

| # | fact | measured |
|---|---|---|
| P1 | raw chain cache | **1,000 tickers, 5,063 ticker-year files, 26.98 GB**, years **2016–2025** |
| P2 | raw chain schema | `expiration, strike, right, date, bid, ask, volume, open_interest` — every input both arms need is in **one** file |
| P3 | matched pairs exist and are near-universal | on every sampled cross-section the call and put counts are **equal at the (expiration, strike) level** (92/92, 329/329, 1152/1153, …) — the cache is symmetric by construction |
| P4 | **but a PAIR needs BOTH legs usable, and that is far rarer** | usable-pair counts on the same cross-sections: 42 of 92, 133 of 329, 10 of 64, **2 of 25** |
| P5 | **B4's `-1` open-interest sentinel is live and material** | `open_interest < 0` on **2.5273%** of 610,186 sampled rows |
| P6 | panel | `panel_corrected_69d.pkl`, 113,945 rows, **69 dates 2009-01-15 → 2026-01-28, 2,531 names** |
| P7 | coverage is the U2 situation again | **41 of 69 panel dates** fall inside the chain span; **28 carry ZERO coverage and ALL are early** |
| P8 | universe overlap | **906 of the 1,000 cache tickers are panel names** |
| P9 | neither arm has ever been built here | `grep` finds **no** volatility-spread, `vol_spread`, `oi_change` or `opening_volume` implementation anywhere in `valuation/` or `scripts/` |

**P4 is the fact that shapes `MA31` and it is new.** `V6-OPT` established the cache is not
call-only (1,288,750 puts vs 1,288,751 calls, zero tickers with no puts) and that removed `U2`'s
recorded blocker. **It does not follow that matched pairs are usable.** A pair needs a two-sided
quote on *both* legs, so the pair-level usable rate is roughly the **square** of the leg-level
rate — `MA45` measured 26.08% of rows one-sided, and P4 is what that does to a pair. Coverage is
therefore a *primary* risk to `MA31`, not a footnote, and §3 C-COV gates on it.

**P7 restates, for the fifth time, a constraint this project keeps meeting** (`S18`, `U2`, `U3`,
`V6-OPT`, now this): a full-panel both-halves gate is **IMPOSSIBLE, not merely weak**. Every split
below is a split of the **COVERED SUBSAMPLE**. *A pass on 20-date halves is not the same object as
a pass on 34-date halves*, and no result here may be quoted as though it were.

**A correction to the audit in passing**: `MA31`'s note says *"29 of 69 dates carry ZERO
coverage"*. Measured against the raw layer it is **28**. `U2`'s 29 was measured on the *derived*
layer, which starts 2016-01-04. Direction unaffected; recorded so the figure is not repeated as if
re-measured.

---

## 1. The two hypotheses, and exactly what is computed

### 1.1 `MA31` — A1 `parity_dev`, the Cremers–Weinbaum volatility spread

For a (ticker, chain-date) cross-section, over every matched pair sharing an identical
`(expiration, strike)`:

```
parity_dev = sum_i w_i * (iv_call_i - iv_put_i) / sum_i w_i
w_i        = min(open_interest_call_i, open_interest_put_i)
```

Admission rules, **all fixed here**:

- **both legs must pass `blackscholes.usable_quote`** — the shared predicate `MA45` shipped this
  same session. Deliberately that predicate and nothing else: it is a statement about whether a
  number *is a price*, and folding a selection criterion into it would change a result it was
  never meant to touch.
- **both legs' `open_interest` must be `>= 0`** — P5's sentinel. A `-1` reaching a weight or a
  difference manufactures flow out of a sentinel (`B4`, and the audit's own `MA32` note).
- **moneyness band `|K/S - 1| <= 0.10`**, `S` the as-traded close. A priori, not discovered: deep
  wings carry unreliable IVs and near-zero OI, and CW's own measure is dominated by liquid pairs.
  **A `0.20` band is computed as a REPORTED CONTROL carrying NO verdict** (§3 C-BAND).
- **DTE band `[7, 365]`**, and at least **`MIN_PAIRS = 3`** admitted pairs, else the name is absent
  that date.
- `iv` from `blackscholes.implied_vol` on the **mid**, with `r = blackscholes.risk_free_rate(date)`
  (FRED DGS3MO, cached offline, never silently zero) and `q = dividends.q_trailing(...)`.

**THE TRAP, NAMED BEFORE THE RUN, AND IT WOULD HAVE SET THE ANSWER TO ZERO BY CONSTRUCTION.**
`dividends.spot_from_parity` exists and recovers `S = C - P + K*exp(-rT)`. Using it to supply `S`
here would define the parity deviation to be **exactly zero**, and the arm would report a clean,
plausible, entirely fabricated null. **`S` is the as-traded `raw_close` from
`data/bulk/prepared/bars` and nothing else.** `spot_from_parity` is named in
`FORBIDDEN_CALLS` and a source-level test asserts it never appears on the arm path.

**AND THE OTHER HALF OF THE SAME TRAP: `raw_close`, NEVER `close`.** Strikes are as-traded;
`close` is split- and dividend-adjusted. Session 30 measured NVDA 2012 at 0.27 against a raw 11.97
— a 43× ratio — and the failure is **silent**: the option still prices, it is simply nowhere near
the money. Session 31's shared `portfolio_capacity.assert_raw_spot` **raises** and is used.

**DECLARED SIGN: POSITIVE.** Cremers–Weinbaum (JFQA 2010): stocks whose calls are relatively
expensive (high `iv_call - iv_put`) **outperform**, ~51 bps/week. A result of the opposite sign,
at any magnitude, **is not a pass** and may not be reported as one.

### 1.2 `MA32` — A2 `call_open_share` and A3 `put_open_share`

Ge–Lin–Pearson (JFE 2016). The **full O/S ratio is NOT buildable** — it needs *stock* volume,
which per `MA25` exists for only ~290 names — and it is **not built and not proxied**. What is
buildable is the decomposition the audit calls *"the strongest half"*: volume that **opens** new
positions, from option volume and open-interest change alone.

Per contract, between consecutive **cached** chain dates `d_prev < d`:

```
dOI_i          = open_interest_i(d) - open_interest_i(d_prev)
opening_i      = clip(dOI_i, 0, volume_i(d))          # volume that can be attributed to opening
call_open_share = sum(opening_i over calls) / sum(volume_i over calls)
put_open_share  = sum(opening_i over puts)  / sum(volume_i over puts)
```

Admission rules, **all fixed here**:

- a contract contributes **only if BOTH `open_interest(d)` and `open_interest(d_prev)` are `>= 0`**
  (P5/`B4`), and only if `d_prev` is within **`MAX_OI_GAP = 5`** calendar days of `d`, so a hole in
  the cache cannot be read as a week of accumulated flow;
- the denominator must be **`>= MIN_VOLUME = 100`** contracts, else the name is absent that date;
- same DTE band `[7, 365]`; **no moneyness band** — the published measure is about flow, not the
  surface, and imposing one would be a different hypothesis.

**Two separate denominators, deliberately.** `call_open_share` and `put_open_share` are *not*
shares of one total, so they are not mechanically complementary. If they were, they would be one
arm and its negation — the `skew_25d` duplicate `U2` caught in its §0.3, which this register is
explicitly built to avoid repeating. §3 C-DUP tests it rather than assuming it.

**DECLARED SIGN: NEGATIVE for A2.** GLP's parent measure predicts returns *negatively* and the
audit states the effect concentrates in call purchases that open new positions, so the component
carrying the effect inherits the parent's sign. **A3 `put_open_share` is TWO-SIDED**: no published
direction for the put leg of the decomposition can be established from the audit's one-line
description, and inventing one would be worse than paying the power. **The inheritance in A2 is an
argument, not a citation** — it is recorded as such, and A2 is reported with its two-sided p beside
its one-sided verdict.

**A STALENESS PROPERTY, NOT A LOOK-AHEAD, STATED SO IT IS NOT MISTAKEN FOR ONE.** Reported open
interest for date `d` reflects the prior session's clearing, so `dOI(d)` attributes to `d`
positions opened on `d-1`. That makes the signal **older**, never fresher — safe in the only
direction that matters, and stated rather than discovered.

---

## 2. Join, splits, and the statistic — the U2 geometry, reused not re-implemented

- **JOIN: the last chain date STRICTLY BEFORE the rebalance date**, staleness ceiling
  `MAX_STALE_DAYS = 7` calendar days. `fwd_ret` runs from the rebalance close, so a same-day EOD
  surface would be contemporaneous rather than look-ahead; strictly-before is used anyway because
  it costs one day on a quarterly signal and **removes the argument instead of winning it**.
  Violations must be **exactly zero** (§3 C-PIT).
- **SPLITS: `surface_stock.halves`** — boundary date embargoed, the shipped
  `holdout_compare_panels` geometry, refusing any split that cannot give both sides
  `MIN_DATES = 16`. Handed the **covered subsample only**.
- **STATISTIC: incremental rank IC**, each arm residualised against the seven weighted incumbents
  (`value, quality, momentum, insider, capital_discipline, size, institutional`) via
  `surface_stock.residualise`, `t` from `surface_stock.ic_tstat`.
- **`surface_stock`'s machinery is IMPORTED, not copied.** Re-typing `halves`, `ic_tstat`,
  `residualise` or `_spearman` would be audit `B7`'s defect class — the error this project has now
  recorded four times (`hlz_hurdle`, BH, `_insider_formula`, `usable_quote`). `join_pit` gains a
  `cols` parameter defaulting to its current tuple so **existing callers stay bit-identical**;
  a test pins that.

---

## 3. Controls — gating controls run and are READ in their own pass, before any arm is scored

Session 26's defect (a gating control and its outcomes computed in one pass) is not repeated:
`--controls-only` exits **before** any arm is scored, and a failure **aborts**.

| id | control | gating? | rule |
|---|---|---|---|
| **C-PIT** | point-in-time violations on the join | **YES** | must be **exactly 0** |
| **C-SPOT** | `assert_raw_spot` over every (ticker, date) spot used | **YES** | **raises**; an empty overlap reporting success is the same failure in a new costume, so it also raises when it can check nothing |
| **C-DUP** | is an arm another arm, or an incumbent, renamed? | **YES** | if `|Spearman|` vs `-skew_25d` (U2's arm) **or** between A2 and A3 exceeds **0.90**, that arm is declared a **DUPLICATE** and carries **no independent verdict** |
| **C-COV** | coverage: names/date, dates, admitted pairs/name | **YES** | a date needs `MIN_NAMES = 20`; halves need `MIN_DATES = 16`; else `RegisterViolation` |
| **C-SENT** | the `-1` sentinel is excluded, counted, and reported | **YES** | the count must be **> 0** — a zero would mean the filter is not reaching the data (a vacuous guard) |
| C-POWER | `gp_on_capital` and `ret_6_1` on the identical covered rows | no | the audit's own power control; **below 2.0 the nulls are uninterpretable and are labelled so** |
| C-INC | R² of each arm on the seven incumbents | no | `U2`'s orthogonality diagnostic — is the information new? |
| C-BAND | A1 at a `0.20` moneyness band | no | **REPORTED, NO VERDICT** — a sensitivity, not a second hypothesis |
| C-DIV | A1 on non-dividend-payers vs payers | no | a mis-specified `q` biases `iv_call - iv_put`; if the arm lives only in payers it is a dividend artefact |
| C-AMER | early-exercise wedge: A1 restricted to `DTE <= 60` | no | **REPORTED, NO VERDICT** — American options carry a parity wedge CW's European framing does not |

---

## 4. Verdict rules — the audit's own kill conditions, quoted, and fixed here

**A1 `parity_dev` (`MA31`)** — the audit's kill condition verbatim: *"Fails X7's calibrated 2.71
theme-IC bar in either half of the covered subsample; or the incremental-IC-vs-incumbents control
(the PEAD/U2 template) shows it is a repackaged incumbent."*

**A2 / A3 (`MA32`)** — verbatim: *"Fails its own within-date permutation p95 in either half; or
fails the incremental-IC control against the momentum inputs."*

So, precisely:

- **A1 PASSES** iff incremental IC `t >= 2.71` in **BOTH** halves **and** the sign is **POSITIVE**
  in both **and** C-DUP does not declare it a duplicate.
- **A2 PASSES** iff incremental IC `t` clears **its own within-date permutation p95** (500 draws,
  seeded, per half) in **BOTH** halves **and** the sign is **NEGATIVE** in both **and** C-DUP is
  clean. **A3** is identical but **two-sided**, requiring only sign *agreement* across halves.
- **Anything else is a NULL.** Ambiguous against a pre-committed threshold is a NULL
  (`RUN_RULES` A6). A null is *"could not be separated at this resolution"*, **never** *"absent"*,
  and every null is quoted with its **minimum detectable effect** or not quoted at all (`S19`'s
  rule, `V6`'s restatement).

**2.71 IS AN EXTRAPOLATION HERE AND IS LABELLED ONE EVERYWHERE.** X7 calibrated it on the full
69-date 2,531-name panel; this is a 41-date covered subsample. `U2` already measured that the
panel's own best-known signals land **below 2.71** on a comparable subsample — so **if C-POWER
comes back under 2.0, a null on A1 is uninterpretable and will be reported as uninterpretable**,
not as evidence of absence.

**FAMILY-WISE, FIXED NOW: three arms against one bar.** At-least-one-clears is roughly a 14%
event under independence at a 5% bar. Any arm that clears is reported **"1 of 3 sibling arms"**
and is **NOT eligible for adoption** on that basis alone.

---

## 5. Void conditions

1. Any change to an arm definition, admission rule, band, bar or control **after any arm value is
   read**. Bands and floors are fixed in §1 and §3.
2. Adding a fourth arm. The quadratic space of surface × flow features is exactly what the tree
   combiner searched and it **reversed** out of sample.
3. Reporting a verdict from a smoke-test subset, or from the full panel rather than the covered
   subsample.
4. Using `spot_from_parity`, or `close` in place of `raw_close`, anywhere on the arm path.
5. Relaxing C-SENT, C-PIT, C-SPOT or C-COV to make a run complete. *Never silence a check to make
   a run green* (`RUN_RULES` rule 5).
6. Quoting `MA56` as a tested result. It is `trial_cost: 0 (record only)` with the explicit
   kill condition *"do not run today"*, and **nothing in this register measures it**.

---

## 6. Trial accounting — fixed before the run

**Three arms, three trials, charged to the EQUITY domain.** Equity because these predict the
**underlying's** forward return on the equity panel — the `U2` precedent exactly, which charged
equity for the same reason. The naive assumption (options lane ⇒ options domain) would be wrong,
and `R4` already measured that the `unified` bucket reads zero.

Expected: **equity `N` 224 → 227**. Options `N` stays **292**. The controls charge nothing —
they carry no hypothesis and no bar. `MA56` charges **zero**.

`N` will be **re-read from `research_log.detail()` after merging `origin/main`**, never quoted
from `CLAUDE.md` — the `S17`/`S19` defect, and the `MA36` correction, both of which came from
quoting a mid-session figure.

---

## 7. Expectations, written down first and scored afterwards whatever they say

| # | expectation | confidence |
|---|---|---|
| E1 | **A1 is NULL** — every options-surface arm this project has tested has failed | 70/30 |
| E2 | A1's usable-**pair** coverage is materially worse than `U2`'s row coverage, because P4 squares `MA45`'s one-sided rate | 75/25 |
| E3 | C-DUP does **not** fire for A1 vs `-skew_25d`: a whole-chain OI-weighted matched-strike object is not a single 25-delta pair | 65/35 |
| E4 | **A2 and A3 are NULL** | 75/25 |
| E5 | C-DUP does **not** fire between A2 and A3 (separate denominators) | 70/30 |
| E6 | C-POWER **clears 2.0**, so the nulls are interpretable | 55/45 |
| E7 | C-INC shows all three arms carry genuinely new information (low R² on incumbents) and it **predicts nothing** — `U2`'s dissociation, reproduced | 60/40 |
| E8 | The `-1` sentinel (C-SENT) removes a **non-trivial** number of contract-days, i.e. `B4`'s hazard is live rather than historical | 80/20 |

**These are expected to be wrong.** The record's own tally is that this project's directional
priors have been wrong more often than right, which is exactly why they are written before the run.

---

## 8. What this register does NOT do

- It does **not** build the O/S ratio (no stock volume — `MA25`), and does not proxy it.
- It does **not** test the 21-day **changes** of any surface feature (`U2`'s other declined half,
  a different hypothesis — surface *momentum*, not surface *level*).
- It does **not** touch `valuation/web/`, the live scan, or any live scoring path.
- It does **not** re-open `U2`'s three rejected level arms.
- It does **not** run `MA56`, which is a record-only row.

---

*Registered 2026-08-15, options-bot lane, before any arm existed.*
