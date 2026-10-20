# `F13SKILL` — **the census that failed now runs, and it kills the item on the charter's own split: the early half has 8 dates against a 16-date floor**

**2026-10-19, r1 lane. ZERO TRIALS, `FIXED`-class.** Equity `N` stays **307**. **NO REGISTER WAS
COMMITTED, NO ARM RAN, NO SKILL WEIGHT WAS BUILT, NO FORWARD RETURN WAS LOADED** — pinned by test.
**ADOPTS NOTHING.** No app file, no live path, no change to the Index or the 2026-10-22 rebalance.

`PREREG_DRAFT_f13skill.md` §3 records that its opening census **failed** on the scout's own error and
that the register's first act is to re-run it. The 2026-10-19 brief requires that census first, "as a
free pre-outcome kill, before any trial is booked". **It ran, `K0` passes, and the item then stops on
an arithmetic fact that needed no outcome at all.**

---

## 1. `K0` — THE CENSUS RAN, AND THE SCOUT'S DEFECT IS RESOLVED RATHER THAN REPEATED

The failed query was `count(distinct mgrno)`, and `mgrno` is **Thomson's** `s34` column applied to
**WRDS's own** 13F product. This session probed the columns before aggregating anything — the
portable rule that error bought, *entitlement is not schema* — and the real column is **`cik`**.

| year | distinct filing managers | rows |
|---|---|---|
| 2010 | 43 | 27,818 |
| 2011 | 63 | 48,988 |
| **2012** | **149** | 153,452 |
| **2013** | **3,945** | 4,416,573 |
| 2016 | 4,770 | 6,643,777 |
| 2019 | 5,859 | 8,066,824 |

**`K0` PASSES from 2013** against its bar of ≥ 1,000 managers, reused verbatim from the draft's §4.

**AND IT CORRECTS THE CENSUS FIGURE THE DRAFT CARRIES.** The draft cites the step as **71 → 3,457**;
measured on the real column it is **149 → 3,945**. **The shape reproduces exactly — a two-order-of-
magnitude step at 2013 — and the levels differ**, which is what you would expect from counting a
different column. The draft's conclusion that **only 2013 onward is usable** is confirmed.

---

## 2. THE SPLIT — AND IT IS WORSE THAN THE DRAFT ASSUMED, IN A WAY THAT DECIDES THE ITEM

The draft's §5 says the register must decide the split **in the register, before any outcome**,
because choosing one after seeing a result is `MA58`'s void condition 5. So it is decided here, from
date counts alone:

| | |
|---|---|
| build-quadrant dates (2009-2019 × `sha1(ticker) % 2 == 0`, $10B tier) | **44** |
| usable from 2013, where `K0` first clears | **28** |
| **early half** (before 2015-01-01) | **8** |
| late half | **20** |
| the shipped both-halves floor | **16** |

**THE EARLY HALF HAS EIGHT DATES AGAINST A SIXTEEN-DATE FLOOR, SO THE ITEM IS `NOT ASSESSABLE ON THE
CHARTER'S SPLIT`.** The draft offered exactly two honest responses — declare it, or widen the window
and lose the charter's protection — and **forbade quietly doing the second**. This takes the first.

**THE DRAFT'S OWN ARITHMETIC WAS CLOSE ON THE MDE AND WRONG ON THE SHAPE.** It estimated "~14
build-quadrant dates in the 2013-2019 window" with halves "each about three years" and an MDE of
"roughly 1.1 SD". Measured: **28 dates, not 14** — but split **8 / 20, not 14 / 14**, because the
charter's boundary sits at 2015-01-01 and the data's start at 2013 leaves only two years on the early
side. **So there are twice as many dates as the draft thought and the split is three times more
lopsided, and it is the lopsidedness that binds.**

---

## 3. THE MDE TRAVELS WITH THE VERDICT, derived and not borrowed

| window | dates | 80%-power MDE |
|---|---|---|
| all build dates | 44 | 0.4284 SD |
| usable window (2013+) | 28 | **0.5370 SD** |
| **early half** | **8** | **1.0047 SD** |
| late half | 20 | 0.6354 SD |

**Every critical value is LABELLED UNCALIBRATED** — no placebo sweep exists for this statistic, and
`STAGE1-BATCH1` establishes that no bar measured on the 2,531-name panel transfers.

**THE SENTENCE THAT MATTERS: the early half's MDE of 1.0047 SD is 2.3× the largest raw anchor this
panel has ever carried** (`MB18`'s `z_fcf_margin` at **0.4346 SD**). So even on the usable window the
design could not detect anything as large as the best thing the panel has ever held — and on the half
that binds, it is nowhere near. **That is `MB22`'s and `V6`'s sentence, stated before any outcome
rather than discovered after.**

---

## 4. WHAT THIS DOES AND DOES NOT CLOSE

**It does not answer the hypothesis.** Whether *which* managers are buying predicts returns is
**UNTESTED, not rejected** — no skill weight was built and no arm ran.

**What it does close is cheaper and worth having: the charter's own staged design cannot carry this
item, and that is now a measured fact rather than a suspicion.** A successor has exactly two routes,
both of which are decisions rather than discoveries:

1. **accept a 8-date early half** and report `UNDERPOWERED` in advance (the `E-4` precedent, declined
   by name in the draft); or
2. **widen the window past the charter's build quadrant** — which §7's void condition 3 permits only
   if declared first, and which costs the charter's protection.

**`K2` — the `size` costume kill the draft makes pre-outcome, and the thing most likely to end this
item for a measured reason — was NOT REACHED**, because building the signal to correlate it is the
arm. `R6` measured this family at **−0.815 to −0.854 against `size`** and `E-1` was withdrawn at
**0.6114**; that risk is untouched and undiminished. **`K1` (tier cells with ≥ 20 identified
managers) is also UNMEASURED** — it needs a second WRDS query and the one connection was spent on the
four steps that ran.

**NOT DONE:** `R6`, `P3`, `S8`, `13F-LAG` and `13F-DEP` are **not re-opened**; `crowding` is **not
run** (§7's void condition 1); nothing is claimed about SEC EDGAR as a live route beyond the draft's
own note that the 13F `cusip → ticker` join is **a different join from Form 4's** and that
`sec_ticker_join.repair` **must not be assumed to transfer**. **The literature leg is still
INCOMPLETE**: Gompers & Metrick (QJE 2001) is **still unread**, so that obligation carries forward.

**14 tests.** `scripts/f13skill_split.py`; `data/free_analysis/F13SKILL_SPLIT.json`; the `K0` census
in `C:\wrds_local\EDGE_DRAFTS_COLLECT.json` (licensed, outside the repo, never committed).
