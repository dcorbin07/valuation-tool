# PREREG DRAFT — N1, THE SMALL/MID-CAP CORE BOOK WITH A LIQUIDITY FLOOR

**DRAFT. Frontier Scout, 2026-10-03. Design only, ZERO trials.** Ranked **1 of 4** in Part C.
Charter clause 1 is the metric: net-of-cost return of a book the scan can build, Roth, vs SPY.

---

## 1. MECHANISM — AND IT IS THE ONLY ONE IN PART C THE RECORD HAS ALREADY MEASURED

`INDEX-BOOK` decomposed the **−6.1077pp/yr** gap between the served $10B book and the published
full-universe decile, one knob at a time, all four arms calling `build_index`:

```
tier            −5.9871pp   <-- and this splits further:
   signal          −1.9291pp     the composite works less well inside the tier
   universe        −4.1785pp     the tier's universe simply returns less
score weighting +0.6804pp
band            −0.8009pp
```

`INDEX-BOOK`'s own words for the universe component: **"about 70% of it is the small-cap premium
the tier declines to hold rather than the composite failing in large caps."**

**So the record has already measured that ~4.18pp/yr of return sits in the part of the universe
the product refuses to buy — and the reason it refuses is capacity, which a Roth book does not
have.** That is the entire thesis of Part C, and this arm is its most direct test.

**ARM — ONE arm.** The shipped five-to-seven-theme composite, scored on the **existing panel**,
with the $10B tier replaced by a **small/mid-cap band plus a liquidity floor**: eligible names are
those **below** a pre-committed cap ceiling and **above** a pre-committed dollar-ADV floor.
Everything else — weighting, 8% cap, 0.30 band, quarterly rebalance — is held at the served
construction. One arm. No sweep over the ceiling or the floor; both are fixed in the register from
the arithmetic in §4 and never moved.

## 2. EVIDENCE *FOR*

* **The −4.1785pp universe component above**, measured on the served construction itself.
* **The liquidity floor is now buildable and was not before.** `B13` stood **PARTIAL** for months —
  the categorical screen held, the liquidity screen *"cannot bind universally"* — and `MC9`
  (2026-09-29) **built the SEP $ADV / OHLC instrument** and found raw SEP volume had been on disk
  since 2026-08-02. **The instrument exists, is wired to nothing, and is exactly what this arm
  needs.** `capacity.py::adv_from_bars` already computes $ADV.
* **`U7` measured why a smaller universe should help the SIGNAL, not just the beta.** Inside 187
  megacaps *"the other themes are compressed and `size` dominates"*, with median market cap rising
  monotonically across composite deciles (**$62.7B → $133.5B**). A lower ceiling widens the
  dispersion the composite ranks on.
* **`X1` says the effect is broad rather than carried by a few names** — 200 of 200 half-books
  positive, median half-book alpha **+0.07233**, minimum **+0.04382** — which is the shape that
  survives a universe change.
* **Cost is survivable at Roth size, and this is the Roth advantage stated as arithmetic.** The
  served book realises **9.58 bps** one-way at **2.4372** turnover (≈0.23pp/yr). `P1` measured
  **87 bps at $1M** on the *top-25 all-cap* book — the concentrated, expensive extreme — which at
  the same turnover is **≈2.12pp/yr**, about half the 4.18pp universe premium. A **broader** book
  of 60–80 names at Roth size (tens of thousands, not $1M) sits **well below** that, and `P2`'s
  **$5.1B crowding cohort** is simply not binding at this size. **The published decile's breakeven
  is 134.1 bps one-way against a measured 33.35, a 4.0× margin.**

## 3. EVIDENCE *AGAINST* — AND THE RECORD GENUINELY CONFLICTS

* **`regime_split` measured the edge STRONGEST IN LARGE CAPS** (*"regime IC highest there"*). That
  is a direct contradiction of `U7`'s compression argument, **both are measured, and this draft
  cannot resolve them in advance.** The register must say so rather than quote whichever helps.
* **The −4.1785pp is a UNIVERSE PREMIUM, i.e. mostly BETA, not alpha.** Against SPY that is a size
  factor bet, and `R1`'s re-run on the corrected panel found **SMB NOT significant** for the
  long-short (**+0.208, *t* +1.39**) while the long-only book does load (**+0.691, *t* 3.89**).
  **So the arm is partly buying a factor whose premium this project has not demonstrated**, and the
  register must report the SMB loading beside the return rather than presenting the whole gain as
  skill.
* **`S10`'s sector asymmetry bites exactly here.** The engine's bull-case band withholds **48.88%**
  of Financial Services rows and **40.32%** of Real Estate against **15.79%** of Industrials — and
  `D9` found the names missing from the free scan are **mid-cap financials**. So a lower ceiling
  admits disproportionately the names the product most often declines to value.
* **`V6-B`'s standing caveat, pointed the other way for once.** Its survival effect runs
  **−14.287pp** in the smallest quintile against **−3.787pp** in megacaps, with the note that
  *"the claim is strongest exactly where the product is not."* Going smaller moves the product
  toward where that risk claim is strong — an argument for the arm on risk and silent on return.
* **`B13` remains PARTIAL and the liquidity screen still "cannot bind universally"** on the
  Sharadar-derived path; `MC9` built the instrument and **wired nothing**. The floor is therefore
  new machinery, and new machinery is where this record's defects live.

## 4. BAR AND MDE

**Bar: charter clause 1.** Net-of-cost annualised return vs **SPY**, long-only, Roth, on the
served construction with the universe swapped — **both halves must clear**, and the arm must beat
the served book's own measured **+1.9488pp/yr** (and be reported against its recent-half
**+0.2702pp**). No long-short figure, no gross figure, no alpha-vs-equal-weight figure may carry
the verdict.

**The cap ceiling and ADV floor are set by arithmetic, not by taste**, and this is what keeps it
one arm: the floor is the lowest $ADV at which the modelled one-way cost at Don's actual Roth size
stays below a pre-committed share of the expected premium, computed from `MC9`'s instrument and
`P1`'s measured curve **before** any return is scored. The ceiling is set so the eligible count
matches the served book's own realised **227 / 542 / 822** order of magnitude, so book size is not
a confound.

**MDE.** This is **not** a paired within-panel difference — it changes the row set — so a paired
SE does not apply and `V2G`/`R1-VAR`'s "no calibrated floor" warning is replaced by a harder
problem: comparing two books on two universes. The register must state which comparison it makes
and derive the MDE from the **realised tracking error of the arm against SPY**. For scale, the
forward contract measured the published decile's tracking error at **11.401 pp/yr** for an IR of
**~0.88/yr**; at that TE a 2pp/yr edge needs ~30 years for *t* = 2, and the panel is **17**.
**So this arm will probably NOT separate from SPY on 69 quarterly dates, and the register must
print that before scoring.** Its honest job is to measure the *size and sign* of the universe
premium net of cost, not to prove significance. Equity `N` **252**, hurdle **3.3254862** (derived).

## 5. THE FREE PRE-OUTCOME KILL

**K1 (FREE, zero trials, read FIRST). The buildability and cost census.** Using `MC9`'s $ADV
instrument on the banked panel, per date: how many names clear the ceiling-and-floor band, and what
is the modelled one-way cost at Don's stated Roth size?

* **Median eligible < 50** → the book cannot reach `CONTRACT_MIN_POSITIONS` and the arm closes at
  zero trials. `INDEX-BOOK` records the served book already falling below 50 on **25 of 69 dates**,
  so this is a live risk, not a formality.
* **Modelled annual cost > the 4.18pp universe premium** → the premium is unreachable at this size
  and the arm closes at zero trials.

**K2 (FREE).** The admitted names' sector mix against `S10`'s withholding rates. If the band is
dominated by the sectors the band withholds at ~49%, the book cannot be valued and the arm stops.

**K3 (FREE).** `MC9`'s instrument must be validated before it gates anything — it has **never been
wired** — by reproducing a known $ADV figure. `MB15`'s rule: validate the instrument before the
hypothesis, not after.

## 6. VINTAGE AND OWNED DATA

**Vintage: a VINTAGE EVENT on adoption, and the heaviest kind** — it changes the served universe,
so it changes what the Index *is*. Derive the vintage from `track_meter.VINTAGES`; never quote one.
Derived today: **vintage 4, OPEN, opened 2026-08-13**. **ELIGIBLE, NOT ADOPTED**, routed to Don.

**Owned data: YES, entirely.** Banked panel, raw SEP volume (on disk since 2026-08-02), `MC9`'s
instrument, `P1`/`P2`'s banked capacity figures, `build_index` itself. **No pull, no purchase, no
rebuild.**
