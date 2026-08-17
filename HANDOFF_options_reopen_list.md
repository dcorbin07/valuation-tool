# The options RE-OPEN LIST — written blind, before the holding-period mine lands

**Written 2026-08-17, before any new chain data exists.** The miner harvesting holding-period
full chains is expected around 2026-09-01. This list is written now, deliberately, because a
re-open list written *after* the new numbers are visible is a list of the results someone liked.

**Zero trials. Adopts nothing. Changes no verdict. Re-opens nothing.** It classifies what
*would* be re-openable and, more importantly, what would not. It touches no file under
`valuation/edge/options_*.py` and nothing under `.github/`.

**Scope: all 36 O-series and U-series ledger rows.** Every one is classified into exactly one
of `NOT-AFFECTED`, `CONSTRAINED`, `REFUSED`.

---

## 0. The headline, and it is not the one the brief expects

**The holding-period chains largely already exist. What does not exist is a *frozen* one.**

Measured on 25 sampled book names: **the EOD chain cache `data/options` already carries a chain
on 96.45% of holding-period weekdays** (5,929 of 6,147), and those chains are not thin — a
sampled NVDA holding day carries **2,100 rows, 224 distinct strikes, 8 expirations, both rights,
with bid, ask, volume and open interest 100% non-null**. That is wide enough to price an
alternative strike or a 0.15-delta wing.

And the registers already reached it. `scripts/o3_o4_o5_surface.py`,
`scripts/o6_o7_o17_earnings.py` and `scripts/o11_o19_o22_o25_portfolio.py` all set
`CHAINS = os.path.join(DATA, "options")` — **the EOD cache, not the freeze**.

So the gap the mine closes is **not availability. It is verdict-grade provenance.** The EOD
store is mutable and rewritten in place — NVDA's year files carry mtimes of 2026-08-02 and
2026-08-05, around and after the book was banked on 2026-08-05 19:51 — which is precisely the
failure `options_freeze.py` was built for and states in its own header:

> "the store is mutable, the miner re-pulls and deepens years in place, and 19.5% of the
> ticker-year files the book consumed were rewritten after it was banked"

**This changes what a re-open means.** Almost nothing on this list re-opens because *data
arrives*. Things re-open because a *pinned instrument* arrives. That distinction runs through
every row below, and it is the reason the CONSTRAINED list is shorter and its expected payoff
lower than the brief's framing implies.

**The one genuine unlock, and it is exact:** the freeze holds a forward price path for the
traded contract and for **zero** alternatives — measured exhaustively, not sampled, at
**3,800 of 3,800 distinct contracts with holding-period marks are traded contracts, 0 are not.**
Any question needing a contract the book never held is unanswerable on the frozen artifact
today, by construction. That is O21-D2 exactly.

---

## 1. The measured structure — read-only, reproducible, no verdict

Everything below was measured from `data/options_freeze/R2_CORRECTED_2026-08-08/chains.pkl.gz`
(2,870,811 rows) and `data/options_universe/state_r2_corrected.pkl` (3,885 trades).

| fact | measured |
|---|---|
| full-chain cells in the freeze (>= 5 contracts on a name-day) | **3,885** |
| of which ARE book entry cells | **3,885 — 100.00%** |
| full-chain cells that are NOT entry cells | **0** |
| entry cells with no full chain | **0** |
| name-days with exactly ONE contract (holding-period marks) | **102,922** |
| distinct contracts with holding-period marks | **3,800** |
| of those, traded contracts | **3,800 — all of them** |
| **alternatives with a forward path** | **0** |

**The entry-day concentration is total, not merely heavy.** The ledger records it as "3,869 of
the freeze's 3,884 full-chain days (99.6 pct)"; measured on the corrected freeze with a
>= 5-contract threshold it is **3,885 of 3,885, exactly one full chain per alert, zero
exceptions in either direction**.

### What the traded contract's own path does cover — O11's model case, on the full book

O11's evidence was a 120-contract sample. Re-measured on all 3,885:

| fact | measured |
|---|---|
| traded contract located in the freeze | **3,885 of 3,885 — 100.00%** |
| mark-days from entry onward | median **41**, mean 41.7, min 2, max 54 |
| trades whose mark path is short of `held_days` | **11 (0.28%)** |
| calendar days from last frozen mark to expiry | median **0** |
| trades whose frozen path reaches within 3 days of expiry | **3,857 (99.3%)** |

**O11's claim holds and generalises**: the traded contract's path is complete, and it reaches
*expiry* for 99.3% of trades, not merely the banked exit. That is what makes O1's exit sweep —
including hold-to-expiry policies — fully served by the freeze.

**One honest correction to O11's own words.** Its row says "zero short of `held_days`"; that
was true of its 120-contract sample and is **11 of 3,885 (0.28%)** on the full book. It does not
touch O11's verdict, and it is recorded because a sampled zero and a measured zero are different
claims.

### What the holding period does NOT cover

| fact | measured |
|---|---|
| trades with ZERO incidental full-chain days inside the hold | **2,246 (57.81%)** |
| incidental full-chain days per trade | median **0**, mean 0.50, p90 1, max 4 |

A holding-period day *can* carry a full chain — if a later alert fires on the same name that
day. **It usually does not.** Nothing can lean on incidental coverage.

### The cross-section, and what the mine would do to it

| | today, freeze only | upper bound if every holding day were mined |
|---|---|---|
| dates carrying >= 1 full chain | 1,574 | **2,498** |
| names per date | median **2**, max **17** | median **53**, max 106 |
| dates reaching 20 names | **0** | **2,247 (90.0%)** |
| total name-day full-chain cells | 3,885 | **130,899** |

This reproduces O3's own pre-register measurement rather than replacing it: O3 recorded "median
1 full-chain name per date, max 17, and 0 of 2,498 dates ... reach the ~20 a quintile sort
needs." Across **all** 2,498 candidate dates the median is 1 (924 carry nothing); across the
1,574 **covered** dates it is 2. **Max 17 and 0-of-2,498 agree exactly.**

**The projection is an UPPER BOUND and is labelled one.** It assumes the miner delivers a full
chain on every day of every banked trade's holding window. It is what perfect closure would
give, not a forecast.

---

## 2. The classification

**22 NOT-AFFECTED · 9 CONSTRAINED · 5 REFUSED · 36 total.**

| row | class | why |
|---|---|---|
| O1 exit sweep | NOT-AFFECTED | Exits are on the **same contract**. Frozen path reaches expiry for 99.3% of trades; its own gate passed 3,885/3,885 and 29,785/29,785 histories "with no live fallback". |
| O2 cross-sectional VRP | CONSTRAINED | Monthly straddle entered and exited on month-ends — neither is an entry day. Superseded on the instrument question by O3. |
| O3 delta-hedged vs idio vol | CONSTRAINED | Row's own words: forced substitution onto the EOD cache, disclosed. |
| O4 expected idio skew | CONSTRAINED | Same register, same substitution. |
| O5 vol-of-vol | CONSTRAINED | Same register, same substitution. |
| O6 cheapest-on-surface | CONSTRAINED | **Undisclosed.** Code prices an alternative strike's exit off a holding-period chain date in the mutable store. |
| O7 earnings straddles | CONSTRAINED | **Undisclosed.** Both legs priced on non-entry days (pre- and post-earnings). |
| O8 index VRP | NOT-AFFECTED | SPY/QQQ/IWM, a different data path; no single-name chain involved. |
| O9 IV rank as sell-timing | NOT-AFFECTED | Same ETF path. |
| O10 passive-limit fills | REFUSED | No verdict. Void condition C2 fired. |
| O11 portfolio layer | NOT-AFFECTED | The model case; verified above on the full book. |
| O12 Kelly / ruin | NOT-AFFECTED | Operates on the banked per-trade return distribution. |
| O13 anti-signal | NOT-AFFECTED | Banked returns plus entry-time features. |
| O14 tick flow | NOT-AFFECTED | Runs on the **tick** cache, not chains. Has its own analogous gap the chain mine does not close — see §5. |
| O15 re-mine beyond 90 DTE | NOT-AFFECTED | Mining infrastructure, no verdict against a bar. |
| O16 is term_slope a front-IV level | NOT-AFFECTED | Entry-day chain features, recomputed on the refrozen book. |
| O17 earnings filter | NOT-AFFECTED | Subsets banked trades; no chain read. |
| O18 spread-conditional cost | REFUSED | No verdict; voided with O10. |
| O19 sizing artefact | NOT-AFFECTED | Banked trades through the shipped sizer. |
| O20 PIT liquidity partition | NOT-AFFECTED | Entry-day screening. |
| O21 dividends / early exercise | **CONSTRAINED (D2 arm only)** | Row's own words: "NOT COMPUTABLE on the frozen book ... resolving it needs a re-mine". D1 and D3 are not affected. |
| O22 capacity | NOT-AFFECTED | Depth is `pit_atm_oi_notional`, an entry-day field, named in the register as the only one banked. |
| O23 exits vs the underlying | NOT-AFFECTED | Frozen replay of the same contracts plus SEP bars. |
| O24 term_slope earnings calendar | NOT-AFFECTED | Entry-day feature. |
| O25 sell the wing after the move | CONSTRAINED | Row's own words: chains from the EOD cache because the freeze's full-chain days are entry dates. |
| O26 per-bucket floor | NOT-AFFECTED | Resampling of banked returns. |
| O17C4 own the event | NOT-AFFECTED | Subsets banked and control books. |
| U1 composite to options entry | CONSTRAINED | **Undisclosed.** Its own docstring: "READ-ONLY on `data/options/`". Mines and exits on rebalance dates, which the freeze does not cover at all. |
| U1-SPLIT | NOT-AFFECTED | A repair; no verdict moved. |
| U2 surface to stock signals | NOT-AFFECTED | Surface features predicting **stock** returns. Its limit is 2016+ coverage, a different gap. |
| U3 convex overlay | NOT-AFFECTED | Banked book returns against the equity panel. |
| U4 one decision object | REFUSED | Design-recorded, never measured. |
| U5 tax-aware allocation | NOT-AFFECTED | No chain dependence. |
| U6 CSPs in, covered calls out | REFUSED | Design-recorded; blocked on 1.81% chain coverage of the **equity** book. |
| U7 composite as veto | NOT-AFFECTED | Subsets banked alerts. |
| U8 one risk budget | REFUSED | Design-recorded, never measured. |

---

## 3. The CONSTRAINED rows, one at a time

The question for each: **is the re-open the SAME hypothesis on a better instrument (legitimate),
or a DIFFERENT hypothesis wearing its name (a new register, new trials)?**

### O21 — the only unambiguous, unarguable re-open

**Its own words:** *"D2's P&L is NOT COMPUTABLE on the frozen book and is reported as unresolved
rather than zero: the freeze holds full chains only on ENTRY dates, so an unheld contract has no
forward path (median 2 chain dates, 10.1% with >3); resolving it needs a re-mine."*

**What the better instrument buys.** The corrected pricer picks a **different contract on 179
entries (4.63%)**, and not a near-substitute — median absolute delta gap 0.129 against a 0.35
target, 93.9% moving to a lower strike. Those 179 contracts have no forward path anywhere in the
frozen artifact; my exhaustive count says **0 of 3,800**. With frozen holding-period chains their
P&L becomes computable.

**SAME hypothesis.** The arm was defined, registered and reported UNRESOLVED against a bar
already fixed (the 1.00pp materiality clause). Resolving it answers the registered question, on
the registered instrument, against the registered bar. Nothing is chosen after the fact.

**What would NOT change.** D1 (early exercise) was measured **model-free** as `bid < intrinsic`
at 34 of 3,870 exits worth +0.2002pp — it needs no chain and does not move. D3 is arithmetic on
solved IV. And the row's *conclusion* — that the pricer is not changed — rests additionally on a
construction argument the data cannot touch: passing `q` into `pick_contract` "would change WHICH
CONTRACT the live engine buys on 4.63% of entries — a construction change, not a bug fix." **A
resolved D2 does not by itself license a pricer change.**

**Trial accounting is the register author's call, not this list's.** D2 was a named arm inside a
register already charged one trial; completing a paid arm is arguably not a new search. Flagged,
not decided.

### O25 — re-opens as a pinning exercise, and the verdict will not move

**Its own words:** *"Chains from the EOD cache, because 3,869 of the freeze's 3,884 full-chain
days (99.6 pct) are banked ENTRY dates - the same structural fact O21 and O3 each hit."*

Verified in code: `build_wings` requires a usable chain on `cross_d`, the **crossing day** — a
holding-period day — and skips the trade when it is absent. So n (1,332 and 1,082) is bounded by
holding-day chain availability in a mutable store.

**What the better instrument buys.** A frozen crossing-day chain, and a modestly larger n where
the EOD cache is among the missing ~3.5% of holding days.

**SAME hypothesis** — identical rule, identical comparators, better provenance.

**What would NOT change, and this is the point: O25 failed on economics, not on measurement.**
The wing loses **-9.34pp and -9.69pp at +75%**, and **-13.03pp and -7.76pp at +100%**, negative
in **both halves against both comparators with every CI95 excluding zero**. No plausible change
of chain source moves a 9-13pp gap with that consistency. **O25 should be re-pinned, not
re-litigated.** Re-running it expecting a different answer is the error this list exists to
prevent.

**A DIFFERENT hypothesis, named so it is not smuggled in:** switching from *first* crossing to
*best* crossing. The row already rules it out — "First crossing, not best - the latter is a
look-ahead that picks the peak." Better data does not make a look-ahead legitimate.

### O3, O4, O5 — the cross-section genuinely changes, and that is exactly why the re-open is not the same object

**O3's own words:** *"THE FROZEN CHAINS NAMED IN THE TASK PROVABLY CANNOT DO THIS, MEASURED
BEFORE THE REGISTER. The freeze holds a full chain only on ENTRY dates: median 1 full-chain name
per date, max 17, and 0 of 2,498 dates and 0 of 120 month-ends reach the ~20 a quintile sort
needs. The panel is the EOD chain cache instead - a forced substitution, disclosed in §1 rather
than quietly made."*

**What the better instrument buys, and it is the largest single change on this list.** A daily
cross-section becomes possible: **zero dates reach 20 names today; up to 90.0% of 2,498 dates
would.** These three registers were forced onto a substitute panel precisely because a
freeze-based cross-section was impossible.

**But it is only the SAME hypothesis if the universe is held fixed, and it would not be.** The
mine covers **the options book's holding windows — 186 names**. The EOD panel these arms actually
ran on is wider. Re-running them on the mined data alone **narrows** the universe, and a narrower
universe is a different object wearing the same name — the failure mode this project has recorded
under `U7`, `S10` and `V6-OPT`. **A legitimate re-open must state its universe before it runs and
must not compare a mined-universe result against these banked numbers as though they were the
same panel.**

**What would NOT change.** All three fail on **monotonicity**, by a factor of three to fifteen,
**in both halves**: -0.1717, -0.0380 and -0.0690 against a 0.6 bar. That is a *sorting* failure,
not a precision failure — a cleaner instrument makes the estimate sharper, it does not make an
unordered quintile ladder ordered. O5 already clears its long-short bar widely (2.9703 against
1.9459) and is still NULL for this reason. **O4 is the one row where sharper measurement could
plausibly matter** — it missed its own calibrated bar by **0.0086 of a t** — but it also fails
monotonicity in both halves, so a re-open on the t alone would resolve nothing.

**The genuine prize here is not a re-run of O3/O4/O5. It is that a frozen daily cross-section on
the book's names is an instrument this project has never had.** What to build on it is a new
question, needing its own register and its own trials.

### O6 — constrained, and the row does not say so

**No quote is available, because the row does not disclose it.** This is a finding in its own
right: O6's ledger note says only "Entry date, expiry and holding period held fixed; ONLY THE
STRIKE CHANGES; incumbent re-priced identically."

**Code evidence.** `_o6_for_ticker` reads the mutable EOD cache and prices the exit at *"the
available chain date closest to entry + held_days"*, selecting `exit_ds` from whatever days
exist. So a register whose stated design holds the holding period fixed in fact lets the exit
date float to cache availability.

**What saves it, and it must be said plainly: the substitution is like-for-like.** The incumbent
and every alternative are priced from the **same** `exit_bid` map on the **same** `exit_ds`, so
a mismatched exit date cancels in the *difference*, which is what O6 reports. **The verdict is
not threatened by this; the row's silence about it is the defect.**

**SAME hypothesis** if re-opened. **What would NOT change:** A3, the audit's own headline
suggestion, is **-11.099pp** and the random-alternative control p95 is about **-11.3pp** — the
incumbent 35-delta rule beats arbitrary in-band selection by ~11pp. And the mechanism finding
holds regardless of chain source: the cheapness rules **change the delta** (mean absolute delta
gap up to 0.310) rather than repricing a fixed trade, so the audit's claim that this separates
"which name" from "which contract" is refuted by construction, not by data quality.
**Recommendation: correct the row's disclosure; do not re-run it.**

### O7 — constrained, undisclosed, and the mine may not even reach it

**Code evidence.** B1 prices the straddle from a **pre-earnings** day chain and B2 exits on the
**post-earnings** day (`ch["ds"] == po_`), dropping the event when that day is absent. Neither is
an alert entry day.

**What the better instrument would buy:** frozen quotes on both legs and a larger sample than
coverage 0.4459.

**The qualification that decides it: earnings days are not the book's holding days.** If the mine
is scoped to holding windows of banked trades, it closes O7's gap only where the two coincide.
**O7 re-opens only if the mine's scope includes earnings-adjacent days for these names — which
this list cannot verify, because the miner's specification was not available when it was
written.**

**What would NOT change.** B2 is **-10.340% per straddle** net of four crossings, negative in
both halves. B1's sign finding is a universe statement already correctly caveated — the published
effect is strongest in small firms and "this book has none of" them. Better chains do not add
small firms.

### U1 — constrained, undisclosed, and the mine as scoped does not reach it

**No quote is available; the row does not disclose it.** Its note describes the design in detail
— "ONE grid mined once - 182 names x 39 rebalance dates in the options window, 6,811 cells to
5,186 trades" — without saying which store served it.

**Source evidence, from the script's own docstring:** `scripts/u1_entry.py` is *"READ-ONLY on
`data/options/`"*, calls `chain_on(ticker, day)` at each **rebalance** date and then runs the
shipped +100/-50/half-DTE exit, which needs a forward path. **Rebalance dates are not alert
dates, so the freeze never held any of this** — entry or exit.

**The mine as scoped does not fix it.** U1's grid is a different trade set from the banked book;
holding-period chains for the *book's* trades do not cover 182 names across 39 rebalance dates.
**U1 re-pins only if the mine's scope is wider than the banked book's holding windows.**

**What would NOT change.** U1 failed all four pre-registered conditions, and the decisive ones
are not measurement-limited: **every decile's median trade is between -52.5% and -54.3%** — all
ten — so the composite does not move the typical option trade at all, and TOP10's mean is
tail-carried to the tune of 158.9%. Its paired sign test is **z -2.7840** against the grid. A
frozen chain sharpens none of that. **SAME hypothesis if ever re-pinned; no re-run is
recommended.**

### O2 — do not re-open it separately

A monthly straddle sort on month-end dates, and an **audit of another lane's run** rather than an
independent test, by its own write-up. Its instrument question is O3's, and O3 already re-ran the
delta-hedged version and reported the sign reversal. **O2 re-opens with O3/O4/O5 or not at all.**
Re-opening it on its own would be a third pass at one hypothesis.

---

## 4. The REFUSED rows — they re-open by definition, and they are not all the same kind

| row | why no verdict | does the chain mine help? |
|---|---|---|
| **O10** | Void condition C2 fired — a behavioural condition-code split failed to replicate on the full book. | **No.** The blocker is the **tick** cache, which "is exactly the alert-days and nothing else": the next session is cached for **0 of 3,870** trades and the exit day for **0 of 3,870**. A chain is not a tape. |
| **O18** | Voided with O10 on the shared C2 gate. | **No.** Same tick-cache blocker. |
| **U6** | Design-recorded, NOT BUILDABLE: **1.81%** chain coverage of names entering the equity top decile; median **2** covered names per rebalance against a mean decile size of 165.6; **zero** covered entries on 18 of 68 dates. | **No — and this is the most likely misreading of the whole mine.** U6 needs chains over the **EQUITY book's** names. The mine covers the **options book's 186 names** on their holding days. It does not touch the 1.81%. |
| **U4** | Design-recorded, never measured; a product-design memo. | Not applicable. |
| **U8** | Design-recorded, never measured; its prescribed optimiser returns a corner. | Not applicable. |

**O10 and O18 are the two rows where "re-open by definition" is most misleading.** They refused
for want of *tick* data on non-alert days. The chain mine does not supply it, and the live
order-working question they declined to answer — submit after the close, rest on D+1 — stays
unanswerable.

---

## 5. What the mine does NOT unlock — named so it is not mistaken for unlocked

- **R2's standing verdict.** The alert book loses to random entry by **-5.0640pp**. Both books
  are priced by the same rule, and the verdict rests on **entry-day** selection. Nothing on a
  holding-period chain touches it.
- **O14's tick gap, O10's and O18's.** Alert-days-only tick coverage is a different cache and a
  different gap.
- **U6's coverage blocker.** Different universe. See above.
- **The options-expression family.** `P1S0` closed it on a pre-registered both-halves failure,
  and `P1S0-CONTROL` could not move it. **Better chains are not a reason to reopen a family
  closed on an equity-panel gate**, and no reopen is proposed here.
- **Anything needing more than ~73 days of expiry reach.** The sampled cache day reached a
  maximum DTE of 73. Long-dated work inherits the store's known ceiling unless the mine
  explicitly deepens it.
- **O22's capacity number.** Its depth measure is entry-day open interest, "the ONLY depth field
  banked". Measuring depth at *exit* would be a better instrument for the strategy's true
  capacity — **and the row's own void conditions forbid it**: "swapping the depth measure after
  reading the number is what the void conditions forbid." That is a **new register**, not a
  re-open.

---

## 6. Assumptions, and what this list could not verify

1. **The miner's specification was not available.** This list classifies against the stated
   deliverable — *holding-period full chains* for the banked book. **If the mine also deepens DTE,
   adds names beyond the 186, or covers the equity book's universe, then O7, U6 and the
   long-dated work change class.** Re-read this list against the mine's actual manifest before
   acting on it.
2. **The 96.45% EOD coverage figure is a 25-name sample**, not a census. The direction is not in
   doubt — every sampled name sits between 94.5% and 97.5% — but the exact figure is a sample.
3. **The cross-section projection is an upper bound**, assuming perfect closure on every holding
   day of every trade.
4. **The freeze measurements are exhaustive, not sampled**: 3,885 of 3,885 full-chain cells,
   3,800 of 3,800 contracts, all 3,885 trades.
5. **No new data was pulled and no verdict was recomputed.** Everything here is a fact about what
   is on disk and what the code reads.

---

## 7. The one-line recommendation

**When the mine lands, resolve O21-D2 — the one unambiguous re-open — and re-pin O25, O3, O4,
O5, O6 and O7 to a frozen instrument. Do not expect a verdict to move, and treat any that does
as a finding about the instrument rather than about the market, because five of those six failed
on economics, in both halves, by margins no chain source can bridge.** U1 and O2 are constrained
but out of the mine's scope as stated; neither should be re-run.

**And correct the disclosure on O6, O7 and U1 regardless of whether anything is re-run.** Three
registers priced non-entry-day chains from a mutable store without saying so. That is a record
defect, it is free to fix, and it is the kind of thing this project has repeatedly found by
reading code rather than prose.

The genuinely new capability is a **frozen daily cross-section on the book's own names**, which
this project has never had. What to ask of it is a new question, and it needs its own blind
register and its own trials.
