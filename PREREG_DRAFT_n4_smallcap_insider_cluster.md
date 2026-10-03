# PREREG DRAFT — N4, CLUSTERED OPPORTUNISTIC INSIDER BUYING IN SMALL CAPS

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Ranked **4 of 4** in Part C —
last, and the ranking is itself the finding: **this family has the richest instrument already
built and the worst measured track record in the record.**

---

## 1. MECHANISM

An insider buying their own company's stock with their own money is the least ambiguous signal a
company emits. The literature's refinements are that **opportunistic** purchases (off the insider's
habitual calendar) carry information while **routine** ones do not, and that a **cluster** — several
distinct insiders buying the same name in a short window — is far stronger than a single purchase.
Both refinements concentrate in **small caps**, where insiders have an informational edge over a
market that is barely watching.

**ARM — ONE arm.** A long-only book of names in the N1 small/mid-cap band with **two or more
distinct opportunistic open-market purchasers** in the trailing window at the rebalance date, at
the served construction's weighting, 8% cap, 0.30 band and quarterly rebalance. The classifier is
**imported** from `valuation/studies/insider_routine.py` (`MB20`'s), not rebuilt.

## 2. EVIDENCE *FOR*

* **The instrument is already built, validated and shipped.** `MB20` built
  `valuation/studies/insider_routine.py`, implementing Cohen-Malloy-Pomorski's routine test, and
  validated it to the digit: **42,537 of 87,318 (`ownername`, ticker) pairs = 0.48715** under
  `MA57`'s own four-year rule against its published 0.4872, with the three-year rule reading
  **60.47%** on the identical population. Nothing needs inventing.
* **Coverage of the classification is total on the rows that matter.** `MB20` measured that the
  rule reads only `ownername` (missing on **0 of 5,636,964 rows**) and `transactiondate`, never
  `transactioncode` — so **every one of the 3,454,363 rows the score can value is classifiable**,
  coverage **1.0000**.
* **The clean buy signal is isolated and large.** `V6-B` established that
  `transactioncode == "P"` gives **124,181 open-market purchases with ZERO negative-share rows**,
  and that the shipped `_insider_score` silently **skips 2,182,601 rows (38.7%)** carrying neither
  price nor value — so a purpose-built purchase signal is cleaner than the shipped theme.
* **The data is deep and free.** The licensed export spans **1980-11-25 → 2026-07-24**,
  5,636,964 rows, and SEC Form 4 is free at source — so a positive result here is extensible
  without a purchase.
* **`V6-B` measured that the raw ingredient is plentiful**: a median **106 buy-flagged names per
  date** on the all-cap panel.

## 3. EVIDENCE *AGAINST* — AND IT IS THE HEAVIEST IN PART C

* **The `insider` theme's own IC is NEGATIVE: −0.2259.** It is the only negative theme in the
  project and it still carries 0.125 of the weight.
* **`MB20`'s finding binds any successor and it binds this one.** It removed routine insiders from
  **37.95%** of scoreable rows and **moved the score on 54.83% of scored cells** — a wholesale
  re-ranking of the theme — and the composite **did not care**: per-date rank correlation between
  arms **0.9774**, top-25 overlap **22.65 of 25**, full-sample alpha **0.071741 → 0.072128**.
  `CLAUDE.md`'s own words: *"that binds any future attempt to improve `insider` by changing what it
  reads."* **The register must argue explicitly that a STANDALONE BOOK in a DIFFERENT UNIVERSE is
  not "improving the theme", and a reader is entitled to find that argument thin.**
* **`S3`'s three insider rebuild arms were all REJECTED** (drop the buys bonus, scale by market cap,
  split into two z-scored inputs) — and the one the audit predicted would be best, market-cap
  scaling, was the only arm with a positive theme IC and **still did not clear**.
* **`V6-B`'s arm 3 — dip × insider open-market buying — is NULL, and NOT on coverage**, which
  removes the easy excuse: it had a median 106 buy-flagged names per date against a floor of 10,
  and read full **+1.147pp/yr at *t* +0.5904** with a **late half of +0.011pp (*t* +0.0041)**, i.e.
  absent.
* **`MB20`'s own purchases-only measurement is the most specific warning**: the routine share among
  **purchases only is 2.72%**. So "opportunistic" is nearly vacuous as a filter on purchases —
  almost all purchases are already opportunistic — which means **the opportunistic refinement adds
  essentially nothing to a purchase-only book**, and the arm's novelty reduces to **clustering
  alone**.
* **Clusters are rare, and that is the likely killer.** Requiring two or more distinct purchasers
  in a window, inside a small-cap band, inside a liquidity floor, is three successive restrictions
  on a 124,181-row purchase population spread over 46 years and thousands of names.

## 4. BAR AND MDE

**Bar: charter clause 1** — net-of-cost return vs SPY, long-only, Roth, **both halves**, against
the served book's **+1.9488pp/yr** and recent-half **+0.2702pp**.

**MDE.** Row set changes; no paired SE. Derive from the arm's own realised tracking error. A
cluster-selected small-cap book will be the **most concentrated** of the four, so its tracking error
is the largest and its detectable edge the largest. Equity `N` **252**, hurdle **3.3254862**
(derived). **If K1 shows the book is routinely below `CONTRACT_MIN_POSITIONS` = 50 names, the MDE
is not the binding problem — buildability is — and the arm should close there.**

## 5. THE FREE PRE-OUTCOME KILL

**K1 (FREE, zero trials, read FIRST, and on the arithmetic in §3 it is MORE LIKELY THAN NOT to
fire). The cluster census.** Per rebalance date, inside the small/mid-cap band and above the
liquidity floor: how many names carry **two or more distinct opportunistic open-market purchasers**
in the trailing window?

* **Median below 50** → the book cannot reach `CONTRACT_MIN_POSITIONS` and the arm **closes at zero
  trials**.
* **Median below 20** → not even a diversifiable book; close and say so.
* The reference is `V6-B`'s median **106 buy-flagged names per date on the ALL-CAP panel with no
  cluster requirement and no liquidity floor** — three restrictions away from this arm's
  population, so the register should price the expected count **in advance** rather than discover
  it.

**K2 (FREE). The opportunistic filter's bite on purchases**, reusing `MB20`'s own measurement: if
the routine share among purchases in the band is near the **2.72%** `MB20` measured, **state in the
register that "opportunistic" is doing no work and that the arm is a CLUSTER arm**, so the verdict
is attributed to the right mechanism.

**K3 (FREE). The pre-2003 coverage cliff**, if the arm is ever extended backwards: `MC12` measured
insider coverage at **0.001 in 1995 rising to 0.307 by 2008**, because electronic Form 4 filing
became mandatory only in 2003. **This arm is therefore NOT a candidate for the pre-2009 holdout**,
and the register must say so rather than leave it as an apparent option.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption.** Derive it; derived today **vintage 4, OPEN since
2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES, entirely** — the licensed insider export, `MB20`'s classifier, the band from
`N1`. No pull, no purchase, no rebuild. **The cost of this arm is almost entirely the risk of
spending a trial on a family that has already returned four nulls.**
