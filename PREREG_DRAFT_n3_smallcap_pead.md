# PREREG DRAFT — N3, POST-EARNINGS DRIFT IN SMALL CAPS

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.**

## AMENDED BY DON'S ADDITION 2 — PROMOTED TO **RANK 1 OF PART C**, AND BOTH OBJECTIONS BELOW ARE LARGELY DISSOLVED

**I ranked this third and that was wrong. Two things I had not read change it.**

**(a) THE EVENT-TIME SPACE IS AN ORDER OF MAGNITUDE MORE POWERFUL, AND IT IS ALREADY MEASURED.**
`SEARCH_DOCTRINE.md` §1.4 tabulates the searchable spaces: the equity cross-section has effective
n **58.65** and an 80%-power MDE of **0.4274–0.5071 SD**, while **event time on the same panel**
has n_eff in the **100s–1,000s** and an MDE of **1.66pp at n_eff 400**. Its own conclusion is
blunt: *"the 80%-power MDE is approximately equal to the largest effect the panel has ever
contained. That space can essentially only detect signals as strong as the best signal already in
it. A merely good new signal is invisible there BY CONSTRUCTION"* — **and 245 of the equity trials
were spent in that space.** An earnings surprise is a **dated, staggered, exogenous event**, which
is exactly what event time requires. **So the arm's primary design is now EVENT TIME, and the book
is a second, separate question per charter clause 4b.**

**(b) THE 29% DATE HOLE IS LARGELY FIXED, BY WORK ALREADY SHIPPED.** `W-3b` (DONE 2026-08-25) merged
**IBES** actuals into `I-4`'s canonical point-in-time earnings-date spine and **recovered 29 of 29
FAIL_CLOSED names — every foreign private issuer in the book — so the merged spine reads COVERED on
all 186.** Every date carries a **`date_sources` stamp** of `code22` / `ibes` / `both`.

**Two caveats from `W-3b` that must travel, because they replace the old objection with a sharper
one.** Its V1 agreement gate **FAILED at 86.18% against a 95% bar**, and **code 22 is measurably
BROADER than earnings in 23.3% of name-years** — so the union spine contains non-earnings events.
**The fix is free: filter the spine to `date_sources` in {`ibes`, `both`}** for a clean
earnings-only calendar, which is precisely why `W-3b` shipped the stamp. And `W-3b`'s coverage was
measured on the **186-name options universe, not the equity panel**, so the spine's coverage inside
a small-cap band is **UNMEASURED** and becomes this arm's free kill (§5, K1 revised).

**(c) THE SURPRISE ITSELF SHOULD COME FROM IBES, NOT FROM THE BANKED `pead_car`.** IBES is banked
and deep — `det_epsus` **34,540,574** rows and `statsum_epsus` **15,029,492** rows, both spanning
**1976–2026**, plus `act_epsus` actuals — which gives a true standardised unexpected earnings
(actual minus consensus, scaled by dispersion) rather than a price-based CAR. **It also reaches
back to 1976, so this arm is testable in BOTH pre-2009 eras**, which `pead_car` is not.

**THE REVISED ARM: a true IBES SUE, measured in EVENT TIME, inside the small/mid-cap band.** The
quarterly book remains as the §1 arm but becomes the SECOND question, not the first.

---

### The original draft follows, and its §3 cadence objection still stands for the BOOK half

---

## 1. MECHANISM

Prices under-react to earnings surprises and drift in the direction of the surprise for roughly
one to two months. The effect is documented as concentrated in **small, illiquid, low-analyst-
coverage** names — the part of the market where the information takes longest to be absorbed and
where institutions are least able to trade — which is precisely the niche a Roth book occupies.

**ARM — ONE arm.** A long-only book of names in the N1 small/mid-cap band whose **most recent
earnings surprise, as at the rebalance date, is in the top pre-committed fraction** of the band's
cross-section, at the served construction's weighting, 8% cap, 0.30 band and quarterly rebalance.
The surprise is the **already-banked** `pead_car` column — not a new construction — so the arm
changes the **universe and the selection rule**, nothing else.

## 2. EVIDENCE *FOR*

* **The signal already exists, is wired, and is reported every run.** `HANDOFF_pead.md` records
  the verdict as **REJECTED** for both variants, with the explicit decision that both stay
  **MEASURED** — *"wired, IC and coverage reported every run — so the negative result is permanent
  rather than folklore."* So `z_pead_car` and `z_pead_drift` are panel columns today.
* **`z_pead_car` individually is the fourth-strongest signal in `R4`'s BH list, at IC *t*
  +2.4572.** It fails `X7`'s calibrated **2.7072** and it fails BH — both stated — but it is not a
  dead column, and it is the strongest Part C candidate after `neg_issuance`.
* **It is NOT a repackaged incumbent, measured.** `E-2`'s K2 tested its own candidate against the
  banked PEAD columns and found max **0.1030** (`z_pead_car` 0.1030, `z_pead_drift` 0.0986) — so
  PEAD is close to orthogonal to the themes the composite already carries, which is what makes a
  standalone book on it a different object from the composite.
* **THE MATERIAL DIFFERENCE FROM THE REJECTION, and the register must rest on it:** PEAD was tested
  **POOLED on the all-cap 2,531-name panel**, as an increment to the composite. **A pooled test of
  an effect the literature says is concentrated in a subgroup is diluted toward zero by
  construction** — and `z_pead_car`'s surviving +2.4572 on the pooled test is what that looks like.
  This arm tests the subgroup directly. **That argument is checkable and it is also exactly the
  kind of argument that can excuse re-running anything until it clears, which is why the charter's
  twelve-arm cap exists.**

## 3. EVIDENCE *AGAINST*

* **The earnings dates have a measured 29% hole.** `HANDOFF_pead.md`: dates come from EVENTS code
  22, decoded empirically, and coverage is *"partial — **~2.83 announcements per ticker-year
  against ~4 expected**."* **An incomplete, non-randomly-missing event calendar is the single most
  dangerous input in Part C**, because a missing announcement does not look like missing data — it
  looks like a name with no recent surprise, i.e. a name the rule silently declines to buy.
* **And the hole is probably WORSE in small caps**, which is the arm's own universe. `EVOWN`
  measured the same decode's failure shape on the options book: **29 of 186 names had ZERO earnings
  coverage and every one was a foreign private issuer**. The register must census the hole **inside
  the band** before anything else.
* **A CADENCE MISMATCH, and it is structural.** PEAD decays over roughly 1–2 months; the book
  rebalances **quarterly**. A quarterly book can hold a PEAD tilt but will hold it for a median of
  ~45 days past the drift window, so it captures a fraction of the documented effect and pays full
  turnover for it. **Fixing that needs a monthly panel, which `MA33` prices at ~3× per build PLUS
  ~5–7 hours of placebo recalibration** because every `X7` bar becomes an extrapolation — and
  which inherits `S8`'s `prepare_daily` staleness at a worse ratio (market cap up to **31 days**
  stale against a monthly rebalance interval). **The monthly variant is named and DECLINED here.**
* **`S7`/`S18`'s six interaction arms were all rejected**, and a surprise-conditioned small-cap
  book is in that family's neighbourhood.
* **Transaction cost works against it hardest of the four.** PEAD selection turns over faster than
  a fundamentals book by construction, and small-cap spreads are the widest; `P1`'s **87 bps at
  $1M** on a concentrated all-cap book is the relevant upper bound.

## 4. BAR AND MDE

**Bar: charter clause 1** — net-of-cost return vs SPY, long-only, Roth, **both halves**, against
the served book's **+1.9488pp/yr** and its recent-half **+0.2702pp**.

**MDE.** Row set changes; no paired SE. Derive from the arm's own realised tracking error. A
surprise-selected small-cap book is the **least** diversified and **highest** turnover of the four,
so its detectable edge is the largest — print it before scoring. Equity `N` **252**, hurdle
**3.3254862** (derived).

**One pre-commitment that costs nothing and prevents the obvious abuse:** the surprise fraction and
the holding rule are fixed in the register. **No sweep over the fraction, and no "we also tried
60 days" after the fact.**

## 5. THE FREE PRE-OUTCOME KILL

**K1 (FREE, zero trials, read FIRST, and it is likely to fire). The earnings-calendar census
inside the band.** Per date, within the small/mid-cap band: the share of names with a decoded
announcement in the trailing quarter, and announcements per ticker-year.

* **Announcements per ticker-year below a pre-committed floor, or the share of names with no
  decoded announcement above a pre-committed ceiling** → the rule is selecting on data
  availability rather than on surprise, and the arm **closes at zero trials**.
* The reference is the measured **~2.83 of ~4** on the whole panel; the band's own figure must be
  reported beside it, because the arm's exposure is the band's and not the panel's.

**K2 (FREE). The foreign-issuer check**, which `EVOWN` paid for: list the band names with zero
coverage and establish whether they are a coherent group (foreign private issuers filing 20-F/6-K).
**A filter that reads "no decoded date" as "no announcement" FAILS OPEN on a non-random group**,
and `EVOWN` measured that at 10.0% of its book.

**K3 (FREE). The drift-window arithmetic.** State, before scoring, what fraction of the documented
1–2 month drift a quarterly holding period can capture. If the honest answer is a small fraction,
the arm's expected edge should be discounted accordingly in the register rather than in hindsight.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption.** Derive it; derived today **vintage 4, OPEN since
2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES for the quarterly arm** — `z_pead_car` is a banked panel column, EVENTS code 22
is in the freeze, the band comes from `N1`. **NO for the monthly arm**, which needs a panel rebuild
and its own placebo sweep, and is declined.
