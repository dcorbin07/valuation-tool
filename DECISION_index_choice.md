# The Index construction decision — 2026-10-22

**For Don. Prepared under `PREREG_index_choice.md`. Nothing here is adopted.**

`INDEX-BEST` picked arm 3 by the rule you set. This memo is the evidence that pick could not
supply about itself. **The register forbade a recommendation unless the evidence made one
obvious. It makes one obvious on ONE of the two questions, and I say which below.**

---

## The three options, side by side

| | **keep the incumbent** | **arm 2 — liquid top 10%** | **arm 3 — liquid top 25** | *N1 band book †* |
|---|---|---|---|---|
| names in the book | 23 / 54 / 82 | 147 / 150 / 150 | 25 every date | 50 / 62 / 79 |
| **net return, Roth** | **+17.16%/yr** | **+22.95%/yr** | **+28.84%/yr** | *+25.75%/yr* |
| over SPY (+15.23%) | +1.93pp | +7.71pp | +13.61pp | *+10.52pp* |
| early half vs incumbent | — | +4.08pp | +4.53pp | *—* |
| late half vs incumbent | — | +7.32pp | +18.57pp | *—* |
| early / late **vs SPY** | +3.72 / +0.27pp | — | — | *+5.99 / +15.44pp* |
| **beats incumbent on name splits** | — | **200 of 200** | **200 of 200** | *not measured* |
| worst half-book vs incumbent | — | **+1.83pp** | **+1.42pp** | *not measured* |
| half-book range | 13.6–21.4% | **21.3–28.0%** | 19.6–35.9% | *not measured* |
| Sharpe | 1.032 | 1.144 | **1.224** | *1.038* |
| max drawdown | −23.03% | −27.60% | **−19.85%** | *−29.66%* |
| turnover | 2.44 | 1.93 | **1.71** | *2.25* |
| trading cost paid | 9.6 bps | 30.4 bps | 33.1 bps | *32.8 bps* |
| after tax, taxable account | +12.20% | +17.06% | +21.80% | *+18.66%* |
| capacity (1% participation) | ~$77m | ~$24m | **~$3.7m** | *not measured* |
| contract-conformant | 44 of 69 dates | **69 of 69** | **0 of 69** | ***69 of 69*** |
| buildable free route, Oct 22 | yes (it is live) | **no** | **no** | *no* |
| **SMB loading** | +0.08 (*t* 0.6) | +0.64 (*t* 5.0) | +0.42 (*t* 1.6) | ***+1.13 (t 3.1)*** |

**† N1 is NOT one of the three options.** It is a **DESCRIPTION at zero trials** of a different
construction — the small/mid-cap band (cap < $5B, ADV > $5M) with the same weighting, cap, band
and cadence — run because `FREE_KILLS_RESULTS.md` asked for it and because it tests whether the
−4.18pp the served tier forgoes is reachable. **It has no verdict, it was not name-split, and it
is shown here only so the four sit in one place.** Its figures are in italics for that reason.

Every return figure means this and only this: *an in-sample backtest over 69 quarterly
rebalances of an 18-year point-in-time panel, net of modelled trading costs, assuming no tax,
not a forward test; and the difference between any two of these constructions is **not
statistically separable** on this sample.*

---

## The one genuinely new piece of evidence: the name split

Every held-out test this project owns splits by **date**, and `INDEX-BEST` found that *all* of
every arm's advantage sits in the late half. A date split therefore cannot tell a real
construction difference from a late-period one. **Splitting the universe by NAME has no
time-period confound at all** — which is why `X1` is the strongest positive result in the record.

Using `X1`'s own keys, seed and split count (fixed in August, before these arms existed):

* **Arm 2 and arm 3 each beat the incumbent on 200 of 200 half-books.** Not "mostly" — always,
  and the *worst* half-book still beats it by +1.83pp and +1.42pp respectively.
* **The incumbent is the only one of the three whose own edge over SPY is not robust**: positive
  on 91% of half-books, with a 5th percentile of **−0.56pp** and a worst case of −1.68pp. Both
  challengers are positive on 100%, with 5th percentiles of +7.44pp and +7.70pp.
* **Arm 3's spread is 2.4× arm 2's** (16.2pp wide against 6.7pp). Its 25-name book does not
  shrink when the universe halves, so it is mechanically noisier — and it is also the thing
  `B17` calls the noisiest number this project publishes.

**What this does and does not settle.** It settles that the advantage is not an artifact of
*which names* are in the panel. It says nothing about *which period* — all 200 half-books use the
same 69 dates, and the late-half concentration survives untouched. **So the strongest statement
available is: not a name artifact, possibly still a period artifact.**

---

## What the extra return is made of

FF5+MOM, R1's own machinery (its alignment check reproduces R1 exactly: SPY beta 0.933, R² 0.988).

* **The incumbent has essentially nothing of its own left**: intercept +1.73%/yr at *t* +0.91,
  with 86% of its variance explained by market, value and momentum.
* **Arm 2's move is a large, highly significant SIZE exposure — SMB +0.559 at *t* +5.59 — that
  did NOT pay as a factor premium over this window.** The factor loadings net to −0.53pp; the
  return is in the intercept. So it is not "small caps happened to win", even though it carries a
  big small-cap exposure. It also *reduces* momentum exposure (UMD −0.142, *t* −2.91).
* **Arm 3's move is barely factor-explained at all: R² 0.196, nothing significant.** ~80% of what
  the move does is name-specific. That cuts both ways — it is not a repackaged factor, and for a
  25-name book it is concentration risk by another name.

**No alpha claim is made.** The register forbade one in advance: these intercepts are
decompositions, not a new finding, because the arms are not separable from each other and the
whole effect is late-half.

---

## What must be true on 2026-10-22

**Neither challenger can be built correctly by the free route.** On D9's own shared population
the live-route book overlaps the Sharadar-built book by **23% at a decile and 12% at a top-25**,
against D9's pre-committed 60% bar. (My instrument reproduces D9's published decile figure at
0.000e+00, so this is D9's measurement extended, not a lookalike.) Overlap gets *worse* as the
cut tightens, which is exactly what a 25-name book should fear.

**So both challengers require Path B — your renewed Sharadar, ~2026-10-12.** The theme job's
first run is 2026-10-04, so `institutional` and `insider` may stop contributing zero before the
22nd; that is a forward fact none of this can measure, and it is a condition rather than a
finding. **If Path B slips, the only thing buildable on the 22nd is the incumbent.**

**Either change is a vintage event.** Book vintage **4** has been open since 2026-08-13; adopting
anything on 2026-10-22 closes it and opens **vintage 5**, discarding ~70 days of accrued clock
and restarting the 60-month verdict horizon at a cost of no statistical gain. **Arm 3
additionally requires changing `CONTRACT_MIN_POSITIONS` from 50**, because a 25-name book is
refused by `seed_book` on every date — it is not a conformant Index as the contract is written.

---

## The recommendation, and which case this is

**ON ONE QUESTION THE EVIDENCE IS CLEAR, and it is arm 2 over arm 3.** Arm 3's extra +5.9pp/yr
is real in this sample, but buying it costs: a change to the contract's position floor, 2.4× the
half-book dispersion, roughly a sixth of the capacity (~$3.7m against ~$24m), the worst
live-route reproducibility of the three (12% overlap), and a book whose advantage is ~80%
name-specific. **Arm 2 captures +7.71pp over SPY with none of that**: it is conformant on all 69
dates, has the tightest half-book distribution of the three, and beats the incumbent on every one
of 200 half-books with its worst case still positive.

**ON THE OTHER QUESTION — whether to move at all — THE EVIDENCE DOES NOT DECIDE, and I am not
going to pretend otherwise.** The case for moving is the 200-of-200 name split and the
incumbent's own un-robust SPY edge. The case against is that every bit of the advantage sits in
the late half, no arm separates from the incumbent at |*t*| = 2 in the early half, and adopting
resets a five-year clock. A name split cannot resolve that, and nothing available before the 22nd
can.

**If you move, move to arm 2. Whether to move is your call on the period risk, and it is a
genuine call rather than a gap in the work.**

---

## Appendix — what the N1 band book adds, and what it does not

`INDEX-BOOK` measured **−4.18pp/yr** sitting in the part of the universe the served $10B book
declines to hold, for a capacity reason a Roth does not have. The band book is the direct test of
whether that is reachable. **It is: +25.75%/yr net of cost, +10.52pp over SPY**, on a book of
**50–79 names that is contract-conformant on all 69 dates** — the only one of the four that is
conformant *and* clears SPY by double digits.

**Three things keep it from being the obvious answer, and the third is the one that matters.**

1. **It is the most volatile of the four**: max drawdown **−29.66%** against the incumbent's
   −23.03%, and a tracking error against SPY of **16.78 pp/yr**.
2. **Its own +10.52pp sits BELOW its 80%-power detection threshold of +12.14pp**, so it does not
   separate from SPY on 69 quarters. N1's own draft printed that expectation before the run — at
   this tracking error a 2pp edge needs ~30 years and the panel is 17.
3. **It is overwhelmingly a size bet: SMB +1.13 at *t* +3.09.** That is nearly twice arm 2's
   loading and the largest of the four. `R1`'s re-run on the corrected panel found **SMB NOT
   significant** for the long-short spread, so this book is leaning hardest on a factor premium
   this project has not itself demonstrated. The +10.52pp should be read as *mostly a small-cap
   exposure that paid over this window*, not as selection skill.

**It also inherits the same Oct 22 blocker**: it is built from the same composite, so D9's 23% /
12% live-route overlap applies to it too. **No recommendation is made about it** — it is a
description, it has no bar, and it was not put through the name split the three options were.
