# DECL DRAFT — F-15: INSIDER-CLUSTER CALLS (long book)
## Tag: [MB20-designed (the routine/opportunistic machinery and the 24-column export — B-1 is its freeze register and neither gates the other) / S3-scope (the S3 corpse rebuilt SCORES; the cluster EVENT was never an arm) / VIRGIN as an options feed]

**Entry rule (frozen):** daily, on the **filing-date clock** (PIT: filingdate, never
transactiondate): a CLUSTER fires when **≥3 distinct `ownername`s** on one ticker file
**open-market purchases (`transactioncode` P)** within any rolling **5-session** window.
Enter the session after the third filing. **Max 1 entry per name per quarter.** Cap 2
entries/session (tie-break: most distinct buyers, then alphabetical).

**Structure:** buy call, nearest-ATM strike, expiry nearest **60 DTE** (ties → longer).
Hold to expiry, no exits. Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable names with insider coverage; cap 10 open; equal premium;
sandbox; `O11` binds.

**Records:** the cluster detail (buyer names count, codes, filing dates), days-from-third-
filing at entry, quote pair. Where MB20's routine/opportunistic classifier exists by launch,
the cluster's opportunistic share is STAMPED as a label — recorded, never used as a rule in
this declaration (a conditioned version is a new declaration).

**Verdict horizon:** clusters are uncommon: est. **3–8 qualifying entries/month**
(re-stated at launch from a trailing-90-day census of the owned export) → **30 fills ≈ 2–3
quarters**. Meter: mean per-trade return on premium vs 0; **MEI +15pp/trade**; both
vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** transaction-date clocking (look-
ahead); sale-code or blank-code rows counting toward a cluster; conditioning entries on the
routine/opportunistic label.

---

## MACHINE-CHECKABLE DECLARATION — added at ACCEPTANCE by the options-bot lane, 2026-08-24

**The prose above is the scout's, preserved verbatim.** It carries the citations and the
corpses this book must out-select, and none of it is edited. What follows is the same book in
the form `valuation/edge/fleet.py` can ENFORCE: prose cannot be validated, and the harness
refuses a declaration it cannot read. Converting is part of acceptance, not a rewrite.

**TWO FIELDS DIFFER FROM THE DRAFT, DELIBERATELY, AND BOTH ARE HARDER.**

1. **`fills_needed` IS DERIVED, AND IT IS NOT 30.** Every draft wrote "30 fills". Thirty is a
   round number, not a derivation. The figure below is the smallest `n` at which
   `track_meter.boundary(n, sigma, rho, alpha)/n` falls to this book's OWN declared minimum
   effect — the boundary the harness actually uses. Across the fleet it runs **93 to 4,563**,
   so the drafts were optimistic by 3x to 40x. The runbook's §3 exists for exactly this:
   *"the number goes on the declaration so nobody reads a six-month book at six weeks."*
2. **`sigma` is a PRIOR unless it says MEASURED**, and `track_meter`'s rule binds: it may only
   ever be **RAISED**, never lowered. `book_meter` reports `sigma_breach` when realised
   volatility exceeds it, and a breach means the band was too narrow, not that the book did
   well.

```json
{
  "sells_premium": false,
  "side": "long",
  "book": "f15_insider_cluster",
  "domain": "options",
  "hypothesis_class": "edge",
  "entry_rule": "Daily, on the FILING-DATE clock (filingdate, never transactiondate): a CLUSTER fires when >=3 distinct ownernames on one ticker file open-market purchases (transactioncode P) within any rolling 5-session window. Enter the session after the third filing. Max 1 entry per name per quarter. Cap 2 entries/session; tie-break most distinct buyers then alphabetical.",
  "structure": {
    "strike_selection": "moneyness",
    "moneyness": 1.0,
    "right": "call",
    "dte": 60,
    "dte_rule": "nearest 60, ties -> longer",
    "exit": "hold to expiry, no exits"
  },
  "universe": "optionable names with insider coverage",
  "sizing": "equal premium",
  "concurrency_cap": 10,
  "records_schema": [],
  "verdict_horizon": {
    "expected_fills_per_month": 5.5,
    "min_effect": 15.0,
    "sigma": 92.51,
    "sigma_provenance": "MEASURED. O12 reports this project's own options book at mean 0.0327, sd 0.9251 per trade, so 92.51pp is the per-trade return SD of a long option book on this universe. Borrowed across books, not across perturbation sizes (MB8's rule).",
    "sigma_may_only_be_raised": true,
    "rho": 3.0,
    "alpha": 0.05,
    "fills_needed": 420,
    "fills_needed_derivation": "smallest n with track_meter.boundary(n, sigma, rho, alpha)/n <= min_effect. DERIVED, not the draft's round 30.",
    "earliest_honest_read": "6.4 years at the projected 5.50 fills/month (420 fills). The draft said 30 fills; 30 is a round number and this is the derivation. MB20's routine/opportunistic share is STAMPED as a label where the classifier exists by launch, and is NEVER used as a rule here -- a conditioned version is a new declaration.",
    "years_to_horizon_at_projected_rate": 6.36,
    "power_gate_note": "Anytime-valid, so the 50%/80% power vocabularies of a fixed-n design do not apply directly: the boundary IS the threshold at every n, and `fills_needed` is where it first falls to the declared minimum effect. The fixed-n analogue at crit 1.96 is n = ((1.96+0.84)*sigma/mei)^2 = 298, reported beside it so the two vocabularies are both on the face."
  },
  "verdict_grammar": [
    "PAYS",
    "BLEEDS",
    "CANNOT-TELL(horizon)"
  ],
  "trial": {
    "domain": "options",
    "charged_at": "first_verdict_read"
  },
  "o11_sentence": "O11 binds this book: positive per-trade expectancy is not survivability. Sandbox only. Nothing here licenses real money."
}
```
