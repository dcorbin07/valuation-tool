# PREREG DRAFT — N2, NET ISSUANCE IN SMALL CAPS

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Ranked **2 of 4** in Part C.

**Why it ranks above PEAD and insiders: it is the only Part C family whose signal already clears
a CALIBRATED bar on this panel.**

---

## 1. MECHANISM

`capital_discipline` is a **single** z-column — `neg_issuance`, built from net share issuance — and
it is one of only **two** of the nine themes that clear `X7`'s calibrated theme-IC floor of
**2.7072**, at **+2.76**. (The other is `quality` at +3.10.) The literature's mechanism is that
firms issue shares when management believes them overvalued and retire shares when undervalued, and
the effect is documented as **largest in small firms**, where the information asymmetry is widest
and the issuance is largest relative to the existing float.

**ARM — ONE arm.** A long-only book selected on `neg_issuance` **alone** inside the N1 small/mid-cap
band with the same liquidity floor, at the served construction's weighting, 8% cap, 0.30 band and
quarterly rebalance. **Not** the composite, and **not** a new theme inside the composite — a
standalone single-signal book, which is what charter clause 1 asks about and what the graveyard has
never tested.

## 2. EVIDENCE *FOR*

* **It clears the calibrated bar.** `capital_discipline` theme IC *t* **+2.76** against `X7`'s
  placebo-calibrated **2.7072** — and `X7` retired the conventional 2.0 precisely because **39% of
  pure-noise draws** produce at least one theme at 2.0 or better. Clearing 2.71 is therefore a real
  statement, and only two themes in the project do it.
* **It survived Benjamini–Hochberg once.** `R4` ran BH across the 53-signal equity family;
  `neg_issuance` appears at **+2.7556** in the list of signals **rejected** by BH — so it is near
  the surviving boundary rather than deep in the tail, which is a weaker claim than "it survives"
  and is stated as such.
* **`S16`'s rank identity does NOT bind this arm, and that is the material difference.** `S16`
  tried to split issuance into a buyback leg and a dilution leg so the composite could weight them
  separately, and found the split is a **rank identity** — because `buyback = max(0, −net)` and
  `−dilution = −max(0, net)` are both non-increasing in `net`, the mean of their z-scores
  **preserves the ordering of `neg_issuance` exactly**, verified at within-date rank correlation
  **1.000000000000 on all 69 dates**. **That identity is about DECOMPOSING the signal. It says
  nothing whatever about restricting the UNIVERSE**, which changes which rows are ranked rather
  than how they are ordered.
* **`INDEX-BOOK`'s −4.1785pp universe component** applies here as it does to `N1`: the premium is in
  the part of the universe the product declines to hold.
* **The data is free and deep.** Net issuance needs only share counts and the cash-flow financing
  line — `ncfcommon` in Sharadar, `cshoq`/the `…y` financing family in Compustat — both of which the
  pre-2009 holdout route would also carry, so a positive here is testable out of sample later.

## 3. EVIDENCE *AGAINST*

* **All four `S16` arms were REJECTED** against the shipped gate: buyback-only **+0.47pp / +0.05pp**,
  dilution-only +0.23 / −0.26, the two-input split +0.20 / −0.06, the M&A variant +0.17 / −0.19.
  The family has been tried and came back flat **on the composite**.
* **`S16`'s sharpest lesson cuts at the motivation**: buyback-only posted the *best* theme IC of the
  four at **+3.21** — clearing `X7`'s 2.71 — **and still failed the gate**, which `CLAUDE.md` calls
  *"the fifth demonstration that theme IC does not judge a construction change."* **So the +2.76
  that makes this arm attractive is precisely the kind of number the record has five times shown
  not to predict a book's performance.** This is the strongest argument against and it belongs in
  the register's own §3.
* **`P6`/`X3`'s rule generalises it**: `size` has the **worst** theme IC (−0.30) and carries the
  composite's **entire** significance, so a per-signal IC is not a per-book forecast.
* **A single-signal book is undiversified by construction** and will have a far worse tracking error
  against SPY than the composite, which makes the charter's metric harder to clear, not easier.
* **Small-cap issuance is mechanically noisy**: a small firm's share count moves on a single
  placement, so the signal's tail is wide and the z-score is outlier-driven — which is the exact
  territory `S21` showed matters, where removing the 2% winsorisation changed the book's anchor
  names and only 8 of the shipped top 25 survived.

## 4. BAR AND MDE

**Bar: charter clause 1** — net-of-cost return vs SPY, long-only, Roth, **both halves**, measured
against the served book's **+1.9488pp/yr** and its recent-half **+0.2702pp**. A single-signal book
must beat the composite's served book to be interesting; matching it is not a finding.

**MDE.** Row set changes, so no paired SE. Derive from the arm's own realised tracking error against
SPY; a single-signal small-cap book will have a **larger** TE than the composite's 11.401 pp/yr, so
the detectable edge is **larger** than `N1`'s and the register must print it before scoring. Equity
`N` **252**, hurdle **3.3254862** (derived).

## 5. THE FREE PRE-OUTCOME KILL

**K1 (FREE, zero trials, read FIRST). Coverage and dispersion inside the band.** Per date, within
the small/mid-cap band: the non-null share of `neg_issuance` and its cross-sectional dispersion.

* **Non-null share below the 70% rule** → no book, closes at zero trials.
* **Dispersion dominated by a handful of names** (a pre-committed concentration bar on the top and
  bottom tails) → the signal is a placement detector, not a discipline measure, and the arm stops.

**K2 (FREE). The rank-identity check, reused verbatim from `S16`.** Confirm that the arm's selection
ordering is the ordering of `neg_issuance` itself at within-date rank correlation **1.0** — if it is
not, the arm has silently become a decomposition and `S16`'s closure applies to it.

**K3 (FREE). The winsorisation sensitivity, reported not swept.** The book's top names with the
shipped 2% clip and without it. If the unclipped book shares fewer than a pre-committed share of
names with the clipped one, the arm is an outlier detector and its verdict is about the tail —
`S21`'s measured 8-of-25 is the reference.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption** — it would be a different product, not a tweak to this one.
Derive the vintage; derived today **vintage 4, OPEN since 2026-08-13**. **ELIGIBLE, NOT ADOPTED**,
routed to Don.

**Owned data: YES, entirely.** `neg_issuance` is already a panel column at every date; the band and
floor come from `N1`'s machinery. No pull, no purchase, no rebuild.
