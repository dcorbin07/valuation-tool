# Stage-1 batch 1 — plain words for Don

**2026-10-07. Nothing is adopted. No public page changed. The 2026-10-22 rebalance is untouched.**

## The answer

**Nothing survived.** Twelve ideas from the academic literature went in. Ten were registered to
run. **Five died on a free check before any return was looked at. Three got as far as being
scored. None of the three beat the bar.**

That is the result, and it cost ten trials out of a budget with no cap — which is what the
two-stage design is for: find out cheaply, on half the data, and keep the other half unspent.

## What died, and why

Five ideas were killed by a **coverage check** — a test of whether the data we own can even
compute the signal, run *before* any return was touched, so it cannot be influenced by whether
the answer looked good:

- **Intangible-adjusted value** (treating R&D and brand-building as an asset). Needs ten years of
  clean history per company; only 61% of our rows have it, against a 70% floor we did not choose
  for this test — it is the project's own standing rule.
- **The residual-momentum switch already in our code**, which had never actually been measured.
  It turns out to be **inert**: flipping it on barely changes the ranking (99.56% identical). So
  the switch is not a lever, and that is worth knowing on its own.
- **A small/mid-cap core book.** Needs a trading-volume measure we only have for 944 of 3,545
  names. We already knew this one would fail and said so in advance.
- **Earnings-surprise drift.** Our earnings-date coverage averages 2.69 announcements per company
  per year where the real world is about four, so a quarter of the events are simply missing.
- **Industry momentum.** Needs a dated sector map, and we only have one for 37% of rows.

**Read these as facts about our data, not about the ideas.** Every one of these is a perfectly
reasonable signal that someone with a better data subscription could test. We cannot.

Two more were not run, each blocked on something specific rather than on a relative's failure, so
both are **untested, not rejected**. **Residual momentum done properly** needs the signal built
first (three years of market-adjusted returns per company), and you cannot check whether a signal
is a disguise for momentum before the signal exists. **Analyst neglect** needs a *dated* link into
the analyst-estimates data — which is already on our list of things we owe ourselves, and our own
rule says a shared piece of plumbing gets validated before any experiment leans on it. **That is
the one concrete piece of work this batch hands forward.** One (**distress as a junk filter**) was
withdrawn by the scout's own scope rule, and one (**net payout yield**) was blocked before the
register even existed by a data-loading fact.

## What got scored, and why it still failed

Three signals passed their checks and were measured on the build half (2009-2019, half the
tickers):

| idea | strength | survived the multiple-testing ladder? |
|---|---|---|
| **52-week-high proximity** | the strongest, by a distance | **yes** |
| information discreteness | weak | no |
| net issuance | essentially nothing | no |

**The 52-week-high signal was the one real candidate, and it fails its own pre-committed test.**
We knew before running that it is 76% the same thing as momentum, which we already own — so the
register said in advance that it only counts if it adds something *on top of momentum alone*.
Measured that way, it works in the second half of the window and **not in the first** (a *t* of
1.6 early against 3.9 late). A signal that only works in half the window is the single most
repeated failure pattern in this project's whole record, and it is the pattern we test for first.

## The thing worth remembering, which is not about any of these ideas

**Our standard way of testing a new signal cannot support the stability check we require, on this
universe.** The method removes rows where any of our seven existing themes is missing, and one of
them (institutional ownership) does not start until late 2013. On this half of the data that
leaves **25 usable quarters out of 44, with only five of them in the "early" half** — against a
floor of 16 that we need before we will read a half at all.

So the honest statement about those three arms is **"this test could not tell"**, not **"these
signals do not work"**. We reported them that way rather than quoting a number off a five-quarter
cell, because a five-quarter cell is exactly how a weak idea comes to look strong.

**That is the real deliverable of this batch**, and it binds whatever comes next: before any more
signals are tested this way, the method needs fixing — either drop the theme that starts late from
the clean-up step, or move the stability boundary to somewhere the shortened window can actually
support. Decided and written down *before* the next test, not after.

## What was deliberately not looked at

**The 2020-2026 half and the other half of the tickers were never opened.** Nor was the 1999-2008
period. That data is the only thing we have left to check a surviving idea against, and spending
it to pick among ideas would destroy its value. It is still intact.

## Recommendation

1. **No Stage-2 test is proposed.** There is no survivor to take to it. Proposing one for the
   52-week-high signal would mean picking the reading that happened to pass, which is the error
   the register was written to prevent.
2. **Fix the method before the next batch.** The five-quarter early half is a blocker for every
   future signal test on this universe, not just these three.
3. **Three of the five coverage kills are a shopping list, not a verdict** — intangibles, trading
   volume, and dated sector classifications. If any of those ever becomes available, those ideas
   become testable again, unchanged.
4. **Nothing changes about the Index or the October rebalance.**

---

*Register: `PREREG_stage1_batch1.md`, committed alone before any code existed. Ten equity trials
booked before any runner existed (264 to 274). Full technical record:
`HANDOFF_edge_audit.md` section STAGE1-BATCH1. 37 tests, 17 of 17 deliberate sabotage attempts
caught.*
