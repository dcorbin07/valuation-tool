# HANDOFF — what to buy, what not to buy (D series) — 2026-08-06

Research and a recommendation. **No code was changed.** Don makes the call; this exists to make it
decidable.

---

## THE HEADLINE, BEFORE THE TABLE

**My recommendation is to buy nothing right now, with one possible $22/mo exception, and to send
two emails instead.** Two things drive that, and both are new findings rather than restatements
of the audit:

**1. The single cheapest item in the audit — Sharadar direct at $29/mo, which the audit called
"potentially the highest value in this section, at negative cost" — is licensed for personal use
only, and its terms explicitly forbid what Valquo is.** From `sharadar.com/terms`, quoted exactly:

> "This License is granted solely to natural persons for personal use."
>
> "You may not use the Services or the Services Data (**or any derivation of the Services Data**)
> for professional, commercial, institutional, or organizational purposes of any kind."

"Or any derivation" is the phrase that matters. A backtest result is a derivation. The audit
flagged this as *"confirm the licence covers it"*; the answer is that **it does not cover a
commercial product**, and that is not a technicality I can argue around.

**2. The same question is now open on the data the live site already runs on.** FMP sells
*personal-use* subscriptions separately from commercial ones, and displaying FMP data publicly
appears to require a separate Data Display and Licensing Agreement. valquo.co is public and
displays that data today. **I could not verify this from FMP's own pages — they return 403 to
automated fetches — so I am flagging it as unresolved, not asserting it.** It needs one email.

Everything else on the list is either gated on a signal that has been measured dead, or blocked
behind an institutional affiliation you do not have.

---

## THE TABLE

| Option | Cost today (verified) | What it unlocks (open items) | Licence posture | Free substitute | Call |
|---|---|---|---|---|---|
| **D1 · Sharadar direct** | Bundle **$29/mo**; Fundamentals $19, Prices $9, Investors $9 — verified on `sharadar.com/subscribe` | Ongoing data after the freeze. Unblocks **nothing currently open** — the 18 GB freeze already runs the whole panel with no key | **Personal use only. Forbids commercial use of the data "or any derivation."** Verified verbatim | The freeze already on disk (18 GB, verified) | **DON'T BUY** — the licence excludes a commercial product, and the freeze already does the research job |
| **D2 · ThetaData tier** | Individual **$40 / $80 / $160**; **commercial from $250/mo**, sales-contact only, and you must register the firm with OPRA — verified | Bulk endpoints would speed a re-mine (**O15**). Vendor greeks/IV would replace the hand-rolled layer that already works | Individual tier is **"personal use only, no redistribution or business use."** Commercial is a different product at ~3× the price | The greeks/GEX layer is **already built and validated** from the existing cache | **DON'T BUY** — you would be paying to replace something you already have, for a book whose entry signal is dead |
| **D5 · ORATS** | **$99 / $199 / $399** per month — verified on `orats.com/data-api`. Bulk historical is quote-only ("hard drive delivery", no price shown) | Gated on **O2/O6** returning something. Neither has | **Not stated on the pricing page.** Third-party sources suggest $99 individual vs $299 professional — **ambiguous, unresolved** | Tradier already serves ORATS-derived greeks/IV downstream | **DON'T BUY** — the gate has not opened |
| **D6 · Estimate revisions** | No purchasable retail option exists at any price | Roadmap #20 (`sentiment` theme). Real source is IBES, which means WRDS | n/a | `stable/grades` — weak, quota-starved | **DON'T BUY** — same decision as D7, not a separate one |
| **D7 · WRDS** | Institutional subscription only; no individual price exists | Would unlock D6 | **Seven account types, every one requiring affiliation with a subscribing institution** (Faculty, PhD, Research Assistant, Staff, Visitor, Master's/Undergrad, Class). No alumni, no unaffiliated, no corporate — verified on WRDS's own page | Open Source Asset Pricing, Ken French, JKP — all free, all already downloaded (**D3 DONE**) | **DON'T BUY** — it is not purchasable. It is a degree away, not a decision away |
| **FMP Starter** (app lane, not a D item) | **$22/mo**; Premium $59, Ultimate $149 | The **only** item here that touches the live product — the scan runs on the free stack today because bulk endpoints return 402 | **Personal-use tiers sold separately from commercial; public display appears to need a Data Display and Licensing Agreement. UNVERIFIED — FMP returns 403 to fetches** | The free stack it already falls back to | **DECIDE LATER — after one email.** Do not buy until the display licence is answered, because that answer may also apply to the free tier you use now |

---

## THE THREE CLAIMS I WAS ASKED TO VERIFY RATHER THAN REPEAT

**"The options entry signal is measured dead" — TRUE, and it is the load-bearing fact here.**
Ledger row R2: `DONE / REJECTED — "The entry signal does not beat random entry on corrected data.
Survived the correction."` **But the number in the brief does not match the record.** The brief
says −7.47pp; the primary write-ups say paired **−3.72pp** (sign z −3.48, negative in both halves
at −5.88 and −5.96pp, 15 corrected arms all failing) in `HANDOFF_appfixes.md`, and **8.08pp** in
`HANDOFF_universe_backtest.md`. I could not find −7.47pp in any handoff. The *direction and the
verdict* are solidly established across several measurements; the specific figure is not, and one
handoff adds the caveat that **the random-entry control is a yardstick, not a tradable
alternative.** The conclusion survives; quote the verdict, not the decimal.

**"The Sharadar freeze is 18 GB and irreplaceable" — TRUE.** `data/backtest_freeze_2026-08/`
measures **18 GB** on disk and runs with no API key. This is the fact that makes D1 a
DON'T BUY rather than a hard call: **$29/mo buys continuation, not the corpus.**

**"D6 has been parked for months on the same blocker" — TRUE**, and D6 and D7 are one decision.
There is no retail point-in-time estimate-revision product at any price. The path is IBES via
WRDS, and WRDS has no door for you.

---

## D8 — WHAT NOT TO BUY (the item that saves money)

**Do not buy any of D1, D2, D5, D6 or D7.** Reasons, one line each:

- **D1** — licence forbids it, and the freeze already does the work.
- **D2** — you would be buying vendor greeks to replace a layer you have already built and
  validated, to improve a book whose entry signal is measured dead. The commercial tier that
  would actually be lawful is **$250/mo**, not $80.
- **D5** — explicitly gated on O2/O6, and neither has returned anything.
- **D6/D7** — not purchasable by an unaffiliated individual at any price.

**And the whole retail GEX/flow category stays on the no-list**, with one addition from this
project's own work: the greeks/GEX derived layer built over the last week found that the `-1`
open-interest sentinel **manufactures fake gamma walls** — the top strike's gamma share runs 0.31
at >95% known open interest and 0.55 under 25%. Vendors selling GEX infer dealer positioning from
the same public open interest. **The project has now measured, in its own data, that this input is
unreliable in exactly the way that would corrupt the product being sold.** That is a stronger
reason to decline than the price.

**The trap D8 names is live in this list.** ORATS and the ThetaData upgrade are both "better
options data." The options entry signal is dead. Better data does not resurrect a signal that
loses to random entry; it measures the same nothing more precisely.

---

## D9 — options costs are a step change (calibration, not a purchase)

Nothing to buy. The number to hold: the equity book runs **37 bps one-way against a 236 bps
breakeven — a 6.4× margin**. Option trading costs run **4.7% of premium** if you work orders
patiently in liquid names and **12.6%** if you cross on a cheap weekly. **The 6.4× cushion does
not transfer**, and no options result should ever be quoted as though it did. I have not
independently verified the two papers behind those percentages; they are the audit's citations and
they are consistent with each other, but treat them as literature rather than as measurements from
this project.

---

## THE BUY-NOTHING CASE — and it is strong

**Everything currently on the critical path can be finished on data already on disk.**

- The **18 GB Sharadar freeze** runs the full panel with no key.
- The **free factor libraries are already downloaded and verified** (D3 is DONE) — Ken French,
  q-factors, Open Source Asset Pricing, AQR. **R1, the most important test in the audit, needs
  Ken French and nothing else.**
- The **options cache and the derived greeks/GEX layer** cover 315 names with implied vol, the
  full greek stack, GEX, zero-gamma and skew — built without a single vendor call.
- SEC EDGAR, FINRA and USPTO are free and already in use.

**The binding constraint on this project is unrun research, not missing data.** The S series —
described in the state of play as "the actual product roadmap" — is **2 of 28 done**. Not one of
those 26 is blocked on a purchase. Spending money now buys inputs for tests nobody has had time to
run on the inputs already held.

One caveat I will not soften: buying nothing means **the freeze ages**. It is a point-in-time
corpus, and a live subscription is the only thing that extends it. That is a real cost of waiting
— but it is a cost of waiting, not a reason to buy today, and the licence problem means the $29
tier is not the answer to it anyway.

---

## IF YOU BUY ANYTHING, THIS ORDER

1. **Nothing — send two emails first.** (a) FMP: *"Does my subscription permit displaying this
   data on a free public website, and if not, what does?"* (b) Sharadar: *"Is there a commercial
   licence, and what does it cost?"* Both are free and both change the table above.
2. **FMP Starter, $22/mo** — *only if* the licence answer is clean. It is the one item that
   affects what users actually see rather than what research can measure.
3. **Stop.** Everything else needs a gate to open first: ORATS needs O2/O6 to return something,
   ThetaData's bulk endpoints need O15 to be worth mining for, and D6/D7 need an affiliation.

---

## UNRESOLVED — listed, not estimated

1. **FMP's display/commercial licence.** Vendor pages 403 to automated fetch. Third-party sources
   say personal and commercial subscriptions are separate and that public display needs a Data
   Display and Licensing Agreement. **Not verified from FMP. One email settles it.**
2. **What is actually being paid to Nasdaq Data Link today**, and under what licence the existing
   freeze was obtained. I can read the *new* direct terms; I cannot see the *old* NDL contract,
   and the freeze's status depends on it.
3. **ThetaData's greeks/IV tier boundary.** The pricing page does not state which tier includes
   them. The audit says Standard on the strength of vendor docs; the pricing page neither confirms
   nor denies.
4. **ThetaData commercial pricing above the $250/mo startup tier** — sales-quote only.
5. **ORATS licence posture** — not stated on the pricing page at all. Third-party sources suggest
   $99 individual vs $299 professional. **Ambiguous, and I am leaving it ambiguous.**
6. **ORATS bulk historical price** — "hard drive delivery", quote-only.
7. **D4 (Cboe Open-Close)** — not in this task's list, still unpriced, still gated on O14.

## BUGS FOUND

1. **The audit's D1 recommendation is unsafe as written.** It calls Sharadar direct "potentially
   the highest value in this section, at negative cost" and lists the licence only as a thing to
   confirm. The licence forbids commercial use of the data or any derivation. Anyone acting on
   D1's summary without reading its caveat would put the project in breach.
2. **The −7.47pp figure for R2 is not in the corpus.** It appears only in two PROMPT files. The
   handoffs record −3.72pp paired and 8.08pp. The verdict is right; the number is unsourced.
3. **The licence question the audit raised for Sharadar and ThetaData was never asked of FMP**,
   which is the vendor the *live public site* actually runs on. That is the exposure that matters
   most, and it was the one nobody had looked at.

## Sources

- [Sharadar — subscribe](https://sharadar.com/subscribe) · [Sharadar — terms](https://sharadar.com/terms)
- [ThetaData — pricing](https://www.thetadata.net/pricing) · [ThetaData — commercial use](https://www.thetadata.net/commercial-use)
- [ORATS — data API](https://orats.com/data-api)
- [WRDS — account types](https://wrds-www.wharton.upenn.edu/pages/about/wrds-account-types/)
- [FMP — pricing plans](https://site.financialmodelingprep.com/pricing-plans) (403 to fetch; pricing via [Find My Moat](https://www.findmymoat.com/tools/financial-modeling-prep-fmp))
