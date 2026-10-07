# The corrected universe now has its own yardstick — and the headline survives after all

**2026-10-07. Nothing is adopted. No public page changed. The canonical panel is untouched — that
is still your call and still pending.**

> **This memo was rewritten the same day it was first written.** My first version said the
> headline fails on the corrected universe. **It does not, and the error was mine.** The
> explanation is in "The correction" below — I am leading with the corrected answer and keeping
> the account of what I got wrong, because the wrong version was briefly in the record.

## What this was

Every number this project calls "significant" is measured against a **floor**: we shuffle the
signal until it is definitionally worthless, push it through the real machinery 100 times, and see
how big a number pure noise produces. Anything below that floor is noise-shaped.

All seven of our floors were measured on the **old 2,531-name universe**. UNIVERSE-BIAS showed
that universe was selected on today's market caps, so every new screen now runs on the corrected
9,645-name universe — against floors that did not belong to it. Last week's Stage-1 batch had to
stamp every one of its critical values **UNCALIBRATED** for exactly this reason.

This re-ran the same test, same seeds, same settings, **changing only the universe**.

## The answer

**Compared like with like, the research headline survives the corrected universe, and most of it
gets better.**

| what it measures | old universe | corrected | change |
|---|---|---|---|
| top-decile edge over the universe | 7.17%/yr | **6.07%/yr** | **−1.11pp** |
| how solid that edge is | 4.38 | **4.41** | unchanged |
| long/short spread | 11.0%/yr | **18.1%/yr** | **+7.1pp** |
| how solid the spread is | 2.62 | **4.59** | **nearly doubles** |
| are the deciles cleanly ordered? | −0.891 | **−0.964** | **better** |

And against the corrected universe's own floors, **all five measurable bars are cleared** — the
top-decile edge clears its floor by **3.2×**.

**So the edge is not a creature of the old universe.** It costs about a point of annual alpha to
measure it on the honest universe, and every other property improves.

## The correction, because the wrong version was in the record for an hour

Our backtest has a weight-picking step (CPCV) that is normally **switched off** — it has rejected
every alternative weighting we have ever tried, so the shipped strategy is a flat 1/7 blend that
was never tuned.

**On the corrected universe it switches itself on for the first time in the project's history**,
picks a weighting called `ic-proportional`, and the headline the backtest prints is then **that**
book — not the flat one that ships. Both my part 1 and yesterday's UNIVERSE-BIAS compared the
**old universe's flat-weight** figure against the **new universe's tuned** figure. That is two
different strategies, not two different universes.

Measured properly — flat against flat — you get the table above. The figure I reported yesterday
(2.83% at a solidity of 1.08) is the *tuned* book, and **the tuned book is worse than the flat
one on every single measure**.

**That last part is the genuinely interesting bit.** We have known since 2026-08 that letting the
machine pick weights makes results look *better* than they are — it manufactures about +1.4 of
apparent solidity out of nothing. Here it does the opposite, badly, because it picks weights by a
criterion (out-of-sample ranking skill) that is not the thing we care about (return). A candidate
reason, which I have **not** tested: `size` is a very strong signal on this universe pointing the
*wrong* way, and a weighting proportional to signal strength would load up on it.

**What this means in practice: on the corrected universe the backtest's headline is only the
strategy we ship when the weight-picker stays off, and it no longer does.** Any corrected-universe
figure has to say which weighting it is, or it cannot be compared to anything published.

## What still does not hold

- **The Deflated Sharpe still fails** (essentially zero against a floor of 0.59). That is the
  statistic that penalises us for all 274 tests we have run, and it is computed for the tuned
  book; the flat book's version is not computed anywhere, so I am reporting it **absent rather
  than borrowed**.
- **The overfitting statistic (PBO) still tells us nothing**, as we have known since 2026-08 —
  pure noise passes the old "under 50%" version 41% of the time.
- **UNIVERSE-BIAS's universe findings are untouched and stand**: 72% of the in-window universe was
  missing from `data/backtest`, and 81% of the small companies that later died were missing
  against 42% of the small survivors. The data really was selected. What changes is only how much
  that selection moved the headline.

## The other thing worth knowing

**The individual signals are stronger on the corrected universe than this project has ever
measured them.** Five of nine clear a deliberately hard bar — quality, size, capital discipline,
value and insider — against **two** on the old universe. More names means each one is measured
more precisely.

## A bug I found in our own tooling

The script that answers "are our floors out of date?" was **one update behind** — it did not know
about a re-derivation done in August, so it was reporting *every* floor as needing re-work that
had already been done. A tool whose job is to cry wolf, crying wolf. Fixed.

The detail worth keeping: **its own test suite was green the whole time**, because one test
checked the right answer directly and nothing ever compared that to what the tool was *reporting*.
Two parts of the same system disagreeing, with nothing looking at both.

## The eight claims we had not re-measured (item 2)

I also worked through the eight public claims UNIVERSE-BIAS left unmeasured. **Four survive, one
no longer holds, six could not be measured** (eleven rows, because the Index tab is three separate
figures and the factor test is two).

**The Index tab — the one that mattered most:**

| | published | corrected | |
|---|---|---|---|
| **Roth return** | 17.16%/yr | **18.02%/yr** | **+0.86pp — better** |
| **Roth max drawdown** | −23.0% | **−29.0%** | **−5.9pp — worse** |
| Roth Sharpe | 1.032 | 0.969 | worse |
| taxable return | 12.20% | 12.50% | +0.30pp |

**The Index buys a little return and pays materially more drawdown.** The two legs move in
opposite directions, so quoting either alone misrepresents it. Note this is the *opposite sign*
from yesterday's estimate of about −0.4pp, which came from a different construction (no band, no
8% cap).

**One number here will be misquoted if the sentence after it is dropped:** the Index's alpha
against the all-cap equal-weighted universe goes from −0.06pp to **+5.93pp**. That is mostly the
*benchmark falling* (17.2% → 12.1%), not the book rising (17.2% → 18.0%). Quoting it as a
six-point alpha gain overstates it about sixfold.

**The factor-adjusted alpha survives and gets more solid:** +5.94%/yr at a solidity of 4.45,
against the published +6.99% at 3.98 — a point less alpha, a *higher* t. All six pre-registered
variants pass. And the universe's own unexplained excess disappears (−0.41% against +2.34% on the
old panel), which makes the result cleaner rather than just smaller.

**Four could not be measured, and the reason is one thing:** yesterday's corrected panel was built
lean — 16 columns against the old panel's 75 — so the term-structure claim, the hold-horizon
claim, the score-confidence claim and the Dip Detector survival claim all need columns it does not
carry. I attempted each rather than assuming: the score-confidence run fails outright on a missing
`bucket` column. **One panel rebuild would unlock three of the four.** The Dip Detector needs the
raw data export either way.

Two need no measurement at all: the options figure is priced from option chains (no equity change
can reach it) and the Track Record is a forward record, not a backtest.

## Recommendation

1. **The corrected universe is now safe to research on** — it has its own floors, and they are
   mostly a little easier than the old ones because more names means less noise.
2. **The canonical panel can move when you want it to**, and the case is stronger than it was
   yesterday: the headline survives. I am still not moving it — that is your call.
3. **One thing to decide eventually**: on this universe the weight-picker switches on and makes
   things worse. The clean answer is to pin it off so the backtest always reports the strategy we
   ship. That is a construction change, so it is yours, and it needs its own test.
4. **Nothing changes about the Index or the October rebalance.**

---

*Zero trials charged — a floor measurement can only move a bar, never produce a finding. Full
technical record: `HANDOFF_edge_audit.md` sections CORRECTED-FLOORS part 1 and part 1b.*
