# The corrected universe now has its own yardstick — plain words for Don

**2026-10-07. Nothing is adopted. No public page changed. The canonical panel is untouched — that
is still your call and still pending.**

## What this was

Every number this project calls "significant" is measured against a **floor**: we shuffle the
signal until it is definitionally worthless, push it through the real machinery 100 times, and see
how big a number pure noise produces. Anything below that floor is noise-shaped.

All seven of our floors were measured on the **old 2,531-name universe**. UNIVERSE-BIAS showed
that universe was selected on today's market caps and overstates small-cap results, so every new
screen now runs on the corrected 9,645-name universe — against floors that did not belong to it.
Last week's Stage-1 batch had to stamp every one of its critical values **UNCALIBRATED** for
exactly this reason.

This re-ran the same test, same seeds, same settings, **changing only the universe**.

## The answer

**Five of the seven floors are now cleared, and the two that are not are the two the product
rests on.**

| what it measures | floor | our number | |
|---|---|---|---|
| is any single theme real? | 2.89 | **6.62** | clears, comfortably |
| does the long/short spread sort? | 1.49 | **2.12** | clears |
| is the top-decile edge bigger than noise? | 0.97pp | **2.83pp** | clears |
| is the deciles' ordering real? | 0.13 | **0.00** | clears |
| **is the top-decile edge statistically solid?** | **1.64** | **1.08** | **fails** |
| **does it survive counting every test we've run?** | **0.59** | **0.00** | **fails** |

The two failures are the **long-only** book — which is what the product actually is — and the
statistic that penalises us for the 274 tests we have run.

**So UNIVERSE-BIAS's conclusion holds, and now it holds properly.** Last week we could only say
the headline fell apart on the corrected universe *when judged by the old universe's yardstick*.
A fair objection was that the yardstick might be wrong. It is now the corrected universe's own
yardstick, and **the answer did not change.**

## The thing I did not expect

**It is the exact opposite shape from the old universe.** There, the long-only book was our
*best*-measured number and the long/short spread our weakest. Here the spread clears and the
long-only book does not.

And underneath that, something stranger: **the individual themes are stronger than this project
has ever measured them.** Five of nine now clear a deliberately hard bar — quality, size, capital
discipline, value and insider — against **two** on the old universe. The pieces are more clearly
real than ever. The blend of them is not.

**One lead, and it is only a lead because I have not tested it.** The `size` theme sorts at −6.21
on the corrected universe against −0.30 on the old one — a very strong signal pointing the *wrong*
way, while carrying a seventh of the blend's weight. That would drag the whole thing down. Two
earlier findings point the same way (X3 found `size` has the worst theme score yet carries the
blend's entire significance; UNIVERSE-BIAS found the wide pool is mostly a size bet). **Checking
it properly needs its own pre-registered test, which is not this item.**

## Two caveats that have to travel with these numbers

1. **The long/short floor is softer than it looks.** On the corrected universe the weight-picking
   step switches itself on, and we measured years ago that switching it on manufactures roughly
   +1.4 of apparent significance out of nothing. Both our number and the floor carry that, which
   is why comparing them is still fair — but quoting the 2.12 on its own does not survive.
2. **The overfitting statistic (PBO) still tells us nothing**, as we have known since 2026-08.
   Pure noise passes the old "under 50%" version 41% of the time.

## A bug I found in our own tooling

The script that answers "are our floors out of date?" was **one update behind** — it did not know
about a re-derivation done in August, so it was reporting *every* floor as needing re-work that
had already been done. A tool whose job is to cry wolf, crying wolf. Fixed.

The detail worth knowing: **its own test suite was green the whole time**, because one test
checked the right answer directly and nothing ever compared that to what the tool was *reporting*.
Two parts of the same system disagreeing, with nothing looking at both. That check exists now.

## What this does not say, and what comes next

- **It does not say the Index is in trouble.** This is the research decile on the wide universe,
  not the Index. UNIVERSE-BIAS measured the $10B Index tier moving only −0.4pp.
- **It does not move the canonical panel.** That remains your decision, and the recommendation
  from last week stands: the floors needed re-running first, and now they have been.
- **Nothing on any public page changed**, per your pending ruling on the disclosure.

Next in this queue: re-measuring the eight claims UNIVERSE-BIAS listed as unmeasured — the factor
alpha, the hold-horizon numbers, the score-confidence figures, the Dip Detector survival rates and
the Index tab's backtested column — each against these new floors. The Index tab's column is first.

---

*Zero trials charged — a floor measurement can only move a bar, never produce a finding. Full
technical record: `HANDOFF_edge_audit.md` section CORRECTED-FLOORS part 1. 20 new tests, 11 of 11
deliberate sabotage attempts caught, plus 6 of 6 on the tooling fix.*
