# HANDOFF — D4, the Cboe Open-Close Volume Summary (the last open D item) — 2026-08-11

Research and a recommendation. **No code was changed.** Don makes the call; this exists to make it
decidable. Companion to `HANDOFF_data_spend.md` (2026-08-06), which priced D1, D2, D5, D6, D7 and
recommended buying nothing. D4 was explicitly left out of that pass — its own unresolved-list entry
reads *"D4 (Cboe Open-Close) — not in this task's list, still unpriced, still gated on O14."*

This memo prices it, tests the gate, and applies the same standard: **no purchase is recommended
that cannot name its ledger item.**

---

## THE HEADLINE, BEFORE THE TABLE

**DON'T BUY. And — the finding that makes this cheap rather than merely negative — you do not have
to buy it to find out, because Cboe gives away six months of exactly this dataset for free, to
exactly your account type.**

Four things drive that, and three of them are new rather than restatements of the audit.

**1. It is priced, publicly, and the audit's indicative figure understates it by an order of
magnitude on the recurring line and has no counterpart at all for the expensive one.** The audit
said *"Pricing is not displayed"* and offered *"roughly $600/yr … indicative only."* The product
page still displays no price — that part is right — but **the real rates are in fee schedules filed
with the SEC**, which the product page itself points at (*"Fee Schedules have been filed with the
SEC (see 'LiveVol Fees')"*). Stated on comparable bases:

* **Recurring:** the EOD subscription is **$500/mo = $6,000/yr**, about **10×** the audit's
  $600/yr — **per exchange**, and there are four.
* **One-time:** the history this project would actually need costs **$28,200–$37,600 for ONE
  exchange**. The audit's figure has **no counterpart for this at all**, because it was quoting an
  annual subscription to a different product.

**Do not compress those into a single multiple** — the $28,200 is a one-time purchase and the
$600/yr is a recurring rate, and dividing one by the other produces a number that means nothing.
The audit's own caveat that its figures were *"for a different product and are indicative only"*
was right to be there.

**2. There is a six-month free trial of ad-hoc historical EOD Open-Close data, and Don is
eligible.** Filed December 2025, clarified July 2026, and open to **"both TPHs and non-TPHs who have
not previously subscribed … or previously received a free trial."** Don is a non-Trading-Permit-
Holder who has never subscribed. **The one-sales-call recommendation in the audit is obsolete: the
correct action is a free trial, not a negotiation.** It is one-shot, which is why *when* it is spent
matters more than whether.

**3. The licence forbids what Valquo is, unless you pay $5,000/month.** Quoted exactly from the
product page:

> "Raw data is licensed for internal use only and may not be redistributed externally in any form."
>
> "External distribution of derived data is permitted subject to additional licensing fees and
> approval. External redistribution of non-derived data is strictly prohibited."

A hot score computed from open-close data and shown on valquo.co is **derived data distributed
externally**. The filed fee for that is **$5,000 per month — $60,000/yr — on top of the data.**
This is D1's Sharadar finding in a second costume, and the same one JKP already imposes: usable for
research, never shippable in the product.

**4. The gate the audit set has never been run, and the item it gates is the wrong series anyway.**
`O14` (free alert-day tick flow) is `OPEN` in the ledger with the note *"no mention anywhere in the
corpus."* It costs about **7 hours of compute on data the project already holds**. Buying a
$28k dataset to answer a question a free overnight run has not been asked is the exact trap `D8`
names.

---

## THE TABLE

| | Finding |
|---|---|
| **Cost today (verified, SEC-filed)** | EOD subscription **$500/mo**. EOD ad-hoc historical **$400 per request per month**, and **one request = one month of data** — confirmed verbatim: *"Customers may currently purchase Open-Close Data on a subscription basis (monthly or annually) or by ad hoc request for a specified month."* Ten-minute intraday **$1,000/mo**; one-minute intraday **$6,000/mo ($72,000/yr)**, ad-hoc **$2,500/request-month**. Fees are filed **per exchange** (C1, C2, BZX, EDGX) |
| **Cost for what this project would need** | Alert book window is **2016-01-01 → 2025-10-15 = 118 months**. Ad-hoc history starts **January 2018**, so **94 months are purchasable and 24 are not, at any price**. 94 × $400 = **$37,600**; at the C1 filing's five-years-or-more tier ($300/month of data) = **$28,200**. **One exchange.** Full-market coverage multiplies toward four |
| **Free trial** | **Up to six months of ad-hoc historical EOD Open-Close data, $0**, for *"both TPHs and non-TPHs who have not previously subscribed to EOD Open-Close Data or previously received a free trial."* Separate, independent trials exist for ten-minute and one-minute intraday. **One-shot** |
| **What it uniquely unlocks (OPEN items)** | **Exactly one open item that is not its own gate: `U2`.** See the section below — and note the audit filed D4 under the options series, which is the series where the application is dead |
| **Licence posture** | **Internal use only. External distribution of derived data $5,000/mo and requires approval.** Non-derived redistribution *"strictly prohibited."* No academic or non-professional tier is offered on the product page; the audit's *"50% academic discount"* is restricted to accredited institutions — the **D7 blocker**, unchanged |
| **Free substitutes** | A **free sample file** on the product page; **Cboe's free daily market statistics archive** (aggregate volume and put/call, **not** signed, **not** per-participant, **not** open/close); and `O14` itself — signed flow reconstructed by Lee–Ready from the ThetaData endpoint the project already pays for. **None is a substitute for participant capacity tagging**, which is the one thing D4 uniquely sells |
| **Call** | **DON'T BUY.** Run `O14` first, free. If and only if it returns something, spend the **free six-month trial** — not money — on whether capacity tagging sharpens it |

---

## THE CLAIM I WAS ASKED TO TEST RATHER THAN REPEAT: CAN D4 NAME ITS LEDGER ITEM?

The buy-nothing precedent's standard. D4's pitch is order-flow imbalance. **Of the twenty OPEN O and
U items, exactly two are flow items, and one of those is D4's own free precursor.**

- **`O14` · Tick flow, alert days only — OPEN, never run.** This is the gate, not a payoff. D4 is
  the paid upgrade to it.
- **`U2` · Options surface → stock signals — OPEN, unblocked.** The only open item D4 would feed
  that is not itself.

Everything else open in the options series is execution, sizing, exits or the vol surface — `O10`
passive-limit fills, `O11` portfolio layer, `O17` earnings filter, `O18` spread-conditional costs,
`O19` cheap-contract sizing, `O21` dividends, `O22` capacity replay, `O25` sell-the-wing, `O26`
bucket floor, `O3`/`O4`/`O5`/`O6`/`O7` surface and vol. **Not one is a flow item.** D4 does not feed
them and should never be justified by their length.

**The reframing the audit missed, and it cuts both ways.** The audit filed D4 in the options
programme and gated it on an options item — but its own cited literature, **Pan and Poteshman
(2006), predicts *stock* returns from option volume, not option returns.** The options entry is dead
(`R2`, re-confirmed split-clean at −5.0640pp on 2026-08-11); the equity book is alive. So the only
live application runs through **`U2` into the equity composite**, not through the options book at
all. That is a point in D4's favour that the audit did not make.

**It does not survive contact with the horizon.** Pan–Poteshman is a next-day-to-weekly effect. The
equity book rebalances on **63 days**, and `S22` measured its alpha essentially flat from three
months to two years. A daily flow signal feeding a quarterly long-only book is a horizon mismatch of
roughly 60×, and nothing in the record suggests the book is short-horizon. **U2 can be run on the
surface data already held**, and should be, before anyone prices a flow feed for it.

---

## WHAT O13 DID TO THIS QUESTION, YESTERDAY — AND IT CUTS TOWARD RUNNING O14

Reported because it is the strongest argument *for* the flow family and it landed after the audit
was written. `O13` (2026-08-11) decomposed the anti-signal and found:

> **"The alert does not lose because it picks different CONTRACTS from random entry. It loses
> inside every kind of contract it picks."**

The rate component runs −4.23pp to −5.79pp against a −5.0640pp total; the largest mix component
anywhere in 32 arms is 0.7711pp. **Composition is not where the damage is — the day chosen is.** And
flow is a day-level feature. So `O14` is aimed at the one place the damage demonstrably lives, which
is a better reason to run it than the audit had.

**Two things stop that becoming a reason to buy.** First, `O13`'s own Q3: refusal rules fitted on
one half made the other half **worse in both directions** (−0.0977pp and −0.7774pp) and selected
**different features** each way — the third instance of that pattern after session 7's LOO and
session 11's ML combiner. The prior on a new day-level feature rescuing this book is low, and it is
low for measured reasons. Second, `O13` established that **you cannot short the gap**: the alert
book's own expectancy is positive (+3.27%/trade), so the anti-signal is relative to the control and
not tradeable. A confirmed flow effect on the options side would still have nowhere to go.

---

## THE ARITHMETIC THAT DECIDES IT

| | |
|---|---|
| Run `O14` on data already held | **~7 hours** (3,870 alerts × 6.4s), **$0** |
| Free trial, six months of real D4 | **$0**, one-shot, non-TPH eligible |
| Buy the 94 purchasable months, one exchange | **$28,200 – $37,600** |
| …and ship anything derived from it | **+$60,000/yr** |
| Months of the book's own window unavailable at any price | **24 of 118 (20.3%)**, and they are the early ones |

**That last row is a research defect, not just a cost.** The alert book runs from 2016-01-01, ad-hoc
history begins January 2018, and the project's early/late half-split is the instrument nearly every
options verdict rests on. Buying D4 would give a signal testable on the late half and **silent on
much of the early half** — in a programme whose signature failure mode, recorded three times now, is
exactly that a result holds on one half and reverses on the other. **D4 cannot be tested by the
standard this project actually uses.** Nothing in the audit noticed this, because nothing in the
audit checked the start date against the book's own window.

---

## IF ANYTHING IS DONE HERE, THIS ORDER

1. **Run `O14`.** Free, ~7 hours, on data already paid for. It is the last unexplored corner of the
   options programme, it is now aimed at the one place `O13` proved the damage lives, and it needs a
   pre-registered threshold with Benjamini–Hochberg across however many features are built — the
   same gate every other feature faced. Expect a null; the autopsy has found zero discoveries across
   126 hypotheses twice.
2. **Run `U2`** on the surface data already held. It is the only open item D4 would feed, and it is
   free.
3. **Only if 1 or 2 returns something: take the six-month free trial.** Not a sales call. It is
   one-shot, so spending it before there is a hypothesis wastes the one free look.
4. **Stop.** Do not buy. If a trial ever justified a purchase, the derived-data licence at
   $60,000/yr still means it could inform research and never ship — decide that *before* paying,
   not after.

---

## UNRESOLVED — listed, not estimated

1. **Whether the $500/mo EOD subscription is per exchange or all-Cboe.** The C2 filing states $500;
   the December 2025 C1 filing describes *"EOD Open-Close Data for all Cboe Securities … $600 per
   month, for one to four years, and $300 per month for five or more years"*, which is a different
   structure. I have quoted both and multiplied neither. **One question on the trial signup settles
   it.**
2. **The earliest purchasable month, per exchange.** Filings say ad-hoc runs *"beginning with
   January 2018"* (EOD) and *"beginning with March 2019"* (one-minute), while the audit says C1 EOD
   exists from **2005-01-03**. Deep history may exist and simply not be sold ad-hoc. **The 24-month
   hole above assumes January 2018; if C1 sells from 2005 the hole closes and the cost roughly
   triples.** Not resolvable from public pages.
3. **Whether the free trial is still open.** Effective November 2025, clarified July 2026 with no
   end date stated. Recent, but not confirmed live today.
4. **Whether the trial's six months may be chosen** (e.g. six alert-dense months) **or are
   consecutive/most-recent.** This decides whether the trial can actually test anything.
5. **What "approval" means for derived-data distribution** beyond the $5,000/mo fee. Cboe may
   decline a public retail product outright, in which case the fee is moot.
6. **The 2025 20% discount is expired** (April 23 – June 30, 2025, on ad-hoc purchases of $20,000 or
   more). Its existence corroborates that a full-history purchase is a $20k+ transaction; it is not
   available today.

---

## BUGS FOUND

1. **`D4`'s gate points at the wrong series.** The audit gates D4 on `O14`, an options item, while
   its own cited literature predicts **stock** returns and the options entry is measured dead. On
   the audit's own reasoning D4 should be gated on `U2`. The gate is not wrong to exist — it is
   pointed one series over.
2. **The audit's indicative price understates the recurring cost ~10× and omits the large cost
   entirely, and it reads as reassuring.** *"Roughly $600/yr"* against a verified **$6,000/yr per
   exchange** recurring, plus a **$28,200–$37,600 one-time** history purchase the figure has no
   counterpart for. The audit labelled the figure indicative, but it sits in a paragraph headed
   *"Pricing is not displayed"* and is the only number there — anyone skimming takes $600/yr as the
   order of magnitude. Same failure shape as D1's *"potentially the highest value in this section,
   at negative cost."*
3. **Nobody checked the dataset's start date against the book's own window.** A 20.3% hole in the
   early half is disqualifying under this project's both-halves standard, and it is checkable from
   the vendor's own filing in one step.
4. **The audit recommends "one sales call" for a product that has a public free trial.** The trial
   post-dates the audit, so this is staleness rather than error — but it inverts the recommended
   action, and a sales call is the expensive way to learn something a signup page answers.
5. **`HANDOFF_data_spend.md` records D4 as *"still gated on O14"* without noting that O14 has never
   run.** A gate nobody has approached reads, at a glance, like a gate that was tried.

---

## Sources

- [Cboe DataShop — Open-Close Volume Summary](https://datashop.cboe.com/cboe-options-open-close-volume-summary) (product page; no price shown, licence language quoted above)
- [Cboe DataShop — Volume Summary Data](https://datashop.cboe.com/volume-summary-data) (free sample file; internal-use language)
- [Cboe — DataShop Fee Schedule notice](https://www.cboe.com/services/analytics/notices/datashop-fee-schedule/)
- [SEC / Federal Register — free trial for ad-hoc historical EOD Open-Close Data (Cboe, Dec 2025)](https://www.govinfo.gov/content/pkg/FR-2025-12-16/html/2025-22868.htm)
- [SEC / Federal Register — free-trial clarification, ten-minute and one-minute intraday (Jul 2026)](https://www.govinfo.gov/content/pkg/FR-2026-07-13/html/2026-14032.htm)
- [SEC / Federal Register — One-Minute Intraday Open-Close Report fees, Cboe BZX (Aug 2025)](https://www.govinfo.gov/content/pkg/FR-2025-08-26/html/2025-16294.htm)
- [SEC / Federal Register — temporary discount on historical Open-Close Data, Cboe (May 2025)](https://www.govinfo.gov/content/pkg/FR-2025-05-22/html/2025-09183.htm)
- Internal: `VALQUO_EDGE_AUDIT.md` D4 (line 1383) and O14 (line 1106); `VALQUO_LEDGER.md` rows D4,
  O14, U2, R2, O13; `HANDOFF_universe_backtest.md` (window and universe);
  `HANDOFF_optionsbot.md` session 24 (O13); `HANDOFF_data_spend.md` (the buy-nothing precedent)
