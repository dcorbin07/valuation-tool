# PRE-REGISTRATION — S16: decompose net issuance

**Committed before any arm has been scored.** Written after a premise check against the ACTIONS
table and SF1 (§1), reported here in full because **it removes half the audit's stated method**.
No arm's IC, alpha or gate result exists at this commit.

Ledger row `S16`. Why now: **`capital_discipline` re-entered the LIVE book on 2026-08-11** — that
restoration is what opened vintage 3 — and the theme has **exactly one input**, so "which issuance
behaviour carries its IC" is no longer an idle question.

---

## 0. Scope, and what is NOT in this register

This register covers **S16 only**. Two other items are worked this session and are deliberately
register-free:

* **S28** (distribution, not just the mean) is **reporting infrastructure**: it adds quantiles and
  worst/best periods to statistics the payload already publishes. **No hypothesis, no verdict, no
  new claim, and no equity trial** — logged to the `infra` domain at n=1 on the M2/M6 precedent,
  where infra `N` gates no published claim.
* **The O14 and B13 ledger corrections** are facts about the record checked against the code, not
  measurements.

---

## 1. PREMISE CHECK — the audit's method is half unbuildable

The audit's method reads: *"ACTIONS is already on disk and already parsed for delistings. Extract
buyback announcements and dividend initiations, and separate the share-count change into
repurchase, issuance, and other."* Measured against the table:

**(a) THERE ARE NO BUYBACK ANNOUNCEMENTS IN ACTIONS.** All 671,417 rows carry one of nineteen
action types — `dividend` (548,716), `listed`, `delisted`, `tickerchangeto/from`, `split`,
`relation`, `initiated`, `acquisitionof`/`acquisitionby`, `bankruptcyliquidation`,
`regulatorydelisting`, `spinoff`, `spunofffrom`, `spinoffdividend`, `adrratiosplit`,
`voluntarydelisting`, `mergerto`, `mergerfrom` — and **none of them is a repurchase
authorisation.** Buyback-announcement drift is **not testable on data we own**, and this register
does not attempt it. Same class as S25: `src` provenance is a lead, not a fact.

**(b) `initiated` IS NOT DIVIDEND INITIATION.** It is index/security listing initiation — its
earliest rows are `^VIX`, `^RUT` and `^IXIC`, all dated 1997-12-31. Dividend-initiation drift
would have to be **derived** from the `dividend` stream (a first payment after a gap), which is a
different signal from issuance decomposition and is **out of scope here**, named so it is not
mistaken for untested.

**(c) M&A IS GENUINELY AVAILABLE, and it is the audit's most interesting leg.**
`acquisitionof` / `acquisitionby` carry **8,248 rows each**, dated, with the deal value and both
counterparties — e.g. `2026-07-23 | BRK.B | 6768.8 | TMHC`. So *"shares issued for acquisitions"*
can be separated from organic dilution, which is exactly what a net share count conflates.

**(d) THE SIGN SPLIT IS NOT DEGENERATE.** Measured on all 185,958 year-over-year share-count
observations in SF1:

| | count | share |
|---|---|---|
| share count FELL (net repurchase) | 63,365 | **34.07%** |
| share count ROSE (dilution) | 108,335 | **58.26%** |
| flat within ±0.1% | 14,258 | 7.67% |

Both sides are substantial, so neither component is a near-empty column. **And the two sides are
wildly asymmetric** — p01 **−13.2%** against p99 **+107.2%** — because a firm can only repurchase
so much while a secondary offering or a stock-funded acquisition can multiply the count. **That
asymmetry is the whole argument for separating them: one z-score is being asked to describe two
distributions that do not look alike.**

**(e) THE INCUMBENT, for the record.** `share_issuance = shares_t / shares_{t−1y} − 1` from
`sharesbas` (falling back to `shareswa`, `shareswadil`); `neg_issuance = −share_issuance`;
`capital_discipline = mean([z_neg_issuance])` — a **single-input theme**, so the theme *is* the
signal and per S20/S21 it is rank-invariant under a standardiser swap.

---

## 2. THE INSTRUMENT

With `net = share_issuance`, define two **non-negative** components whose difference is exactly
the incumbent:

```
buyback  = max(0, -net)          # magnitude of share reduction, else 0
dilution = max(0,  net)          # magnitude of share growth,   else 0
neg_issuance == buyback - dilution        (an identity, asserted as control C5)
```

**M&A attribution, point-in-time.** A row `(t, as_of)` is **M&A-flagged** iff ACTIONS holds an
`acquisitionof` row for ticker `t` with `date < as_of` and `date >= as_of − 365d`. **Strictly
`<`, never `<=`** — B26's same-day rule, because an announcement dated `as_of` is not reliably
public when the panel scores. Then:

```
mna_dilution     = dilution if M&A-flagged else 0
organic_dilution = dilution if not M&A-flagged else 0
```

A name with no computable share change scores **None** in every arm, exactly as today. **No arm
may impute a neutral 0 for missing data** — that converts an availability gap into a signal, which
is S10's failure mode.

---

## 3. THE ARMS — four, one weighting, no grid

| arm | `capital_discipline` = |
|---|---|
| **A0 INCUMBENT** | `z(neg_issuance)` |
| **S16A BUYBACK ONLY** | `z(buyback)` |
| **S16B DILUTION ONLY** | `z(−dilution)` |
| **S16C TWO INPUTS** | `mean( z(buyback), z(−dilution) )` |
| **S16D M&A SPLIT** | `mean( z(buyback), z(−organic_dilution), z(−mna_dilution) )` |

S16A and S16B answer *"which behaviour carries the IC"* directly. S16C and S16D are the
**membership changes** — they make a single-input theme multi-input, which is the audit's actual
proposal and the only kind of arm that could be adopted.

---

## 4. THE GATE — the shipped one, at the already-committed margins

**`holdout_compare_panels`**, the same shipped gate and the same pre-committed margins used by
`SECTOR-NEUTRAL-B6`, `S20`, `S21` and `S3`: **B beats A by ≥ +0.25 long-short *t* AND ≥ +100 bps
top-decile alpha, in BOTH split directions, boundary date embargoed.**

* **ONE weighting: the deployed flat 1/7.** No grid, no sweep.
* **ONE panel build, five scorings, provably identical rows** — every arm is a column on one
  frame, so the arms differ in the theme's construction and in nothing else.
* Verdict per arm: **ADOPT-ELIGIBLE** iff it clears both margins in both directions; otherwise
  **REJECTED**. Ambiguous is a **NULL** (`RUN_RULES` A6).

**Per-component IC is a DIAGNOSTIC and may never carry a verdict** — X7 calibrates the theme-IC
floor at **2.71**, and P6.3 / X3 / S20/S21 / S3 have now demonstrated four times that theme IC
does not judge a construction change. S16 is a construction change.

---

## 5. WHAT ADOPTION WOULD COST — and it is higher here than usual

Adoption is a **VINTAGE EVENT**. The current vintage is **DERIVED, never assumed** (`PT-GAPDUE`):
`track_meter.current_vintage()` returns **vintage 3, opened 2026-08-11**, and its recorded reason
is *"the theme restoration — capital_discipline reaches a live score"*.

**So vintage 3 exists BECAUSE of this theme.** Changing its construction now would close a vintage
that is days old and open vintage 4, spending a second five-year clock reset on the same theme.
**Therefore an eligible arm is recorded ELIGIBLE, not adopted**, and it **QUEUES BEHIND vintage
3's own evidence** — the same clause S20/S21 fixed in advance, and it binds harder here.

---

## 6. CONTROLS — all read BEFORE any arm's verdict

* **C1 — the harness reproduces the published record.** The incumbent arm must return
  `top_decile_alpha` 0.07174142332098163, `long_short_tstat` 2.8360640685320595, HAC
  2.6199121240414884, `monotonicity` −0.8909090909090909. **The run ABORTS before any arm is read
  if it does not.**
* **C2 — identical rows.** All arms share one `(date, ticker)` key set.
* **C3 — the rebuilt incumbent is bit-identical** to the shipped `capital_discipline` column over
  the shared keys.
* **C4 — no arm is inert.** Within-date rank correlation against the incumbent, per arm.
* **C5 — THE IDENTITY HOLDS: `buyback − dilution == neg_issuance`** to floating-point equality on
  every row. If it does not, the decomposition is not a decomposition.
* **C6 — COVERAGE FIRST, per the COVERAGE RULE.** Each component's non-null and non-zero rate is
  reported before any verdict. **A component that is zero on more than 90% of rows is flagged
  DEGENERATE and its arm is reported as such rather than as a failure** — O13's treatment of
  `opt_right`, fixed here in advance because §1(d) makes this unlikely but not impossible on the
  panel's own (narrower) universe.
* **C7 — the M&A flag is not vacuous**: its firing rate on the panel is reported, and if it fires
  on under 1% of dilution rows, S16D is flagged rather than reported as a failure.

---

## 7. EXPECTATIONS, written before any arm was scored

1. **No arm clears the gate in both directions — 70/30.** Every construction change put through
   this gate since B6 has failed it.
2. **DILUTION carries more of the signal than BUYBACK — 65/35.** The dilution side has the far
   larger dispersion (§1d), and the issuance anomaly in the literature is mostly a
   *distress/overvaluation* story on the issuing side rather than a reward for repurchasing.
3. **S16A (buyback only) is the weakest arm — 60/40**, for the same reason.
4. **Separating M&A improves on undifferentiated dilution (S16D beats S16C) — 55/45.** Low
   confidence; stock-funded M&A is a real economic event but the flag is coarse.
5. **The M&A flag fires on 5–25% of dilution rows — 60/40.**
6. **At least one component's IC exceeds the incumbent's while its arm still fails the gate —
   65/35.** That dissociation is the standing rule restated and would be its fifth demonstration.

---

## 8. TRIAL COST

**Four arms, one weighting, no grid: equity `N` 161 → 165.** Charged whatever the verdicts are.
S28, the ledger corrections and every §1 premise check charge **nothing** — they measure what the
code and the data already are.

`BACKTEST_RESULTS.json` is re-run **from a clean tree** so the artifact carries the honest
denominator.

---

## 9. WHAT THIS REGISTER DOES NOT DO

* It does **not** test buyback-announcement drift (§1a — not on data we own) or dividend-initiation
  drift (§1b — derivable, different signal, out of scope). Both are named so they are not later
  mistaken for tested-and-failed.
* It does **not** change the 365-day window, the `sharesbas` fallback chain, or any weight.
* It does **not** re-open whether `capital_discipline` should carry weight at all. That is
  `holdout_theme_validate`'s question and it has its own history.
