# PREREG — MB16: quote-classified VPIN on the alert-day option tape

**Status: BLIND. Committed ALONE, markdown only, zero `.py`, as a strict git ancestor of every
commit that scores an outcome.** Written after the instrument pass and the item's mandated
pre-scoring kill, and **before any return has been touched** — see §0.

Item: `VALQUO_MASTER_AUDIT_4.md` → `MB16`. EV MEDIUM, **1 trial, options**, prior ~10%.

---

## 0. What has already run, and why that does not break blindness

MB16's kill condition is explicitly **pre-scoring**: *"if quote-classified VPIN correlates above
0.90 within date with `O14`'s already-null `signed_volume` or `unusual_volume`, it is those
features renamed and the arm is withdrawn before any outcome is read."* So the instrument pass and
the kill necessarily precede this register; running them afterwards would invert the item's own
sequencing.

**They touched no return, and that is checkable rather than asserted.** `MB16_VPIN_UNITS.pkl`
carries 14 columns — ticker, date, month, print/classification counts, the VPIN values and O14's
two banked features — and **no P&L column of any kind**. The arm's outcome is unseen at the moment
this file is committed. A test pins that the kill pass cannot read `pnl_pct`.

**Already measured, and none of it is an outcome:**

| | |
|---|---|
| units | 3,863 (O14's own, missing 0) |
| gating control — classified-rate median | **0.9854035696220825**, reproducing O14's published value to all 16 digits |
| gating control — `signed_volume` vs O14's banked | **max abs deviation 0.0** on 3,863 units |
| kill vs `signed_volume` | pooled **−0.0683**, within-month **−0.0429** |
| kill vs `unusual_volume` | pooled **−0.0348**, within-month **−0.0372** |
| **registered kill statistic** | **0.0683 against a bar of 0.90 → DOES NOT FIRE** |
| reported beside it, NOT the registered comparison | vs **\|signed_volume\|**: pooled **+0.5661**, within-month **+0.5357** |

---

## 1. What is built, and the one version that is worth building

Easley, López de Prado & O'Hara's VPIN is proposed as an order-flow-toxicity measure.
Andersen & Bondarenko's critique is specific and names its target: the **Bulk Volume
Classification** scheme, which they find inferior to a standard tick rule, with VPIN predicting
volatility largely because rising volatility induces systematic BVC classification errors. The
authors dispute the characterisation. **The contested component is the classifier.**

That component is exactly the one this project already does properly: `O14` built a quote-based
Lee–Ready classifier, measured it classifying a median **98.54%** of eligible prints, and found and
fixed a real defect in it. **So only the quote-classified version is built, and the BVC classifier
is not built anywhere** — pinned by an AST test over the shipped script.

**Construction, fixed:** classified prints in TIME order across the alert-day chain; total
classified volume cut into `N_BUCKETS` **equal-volume** buckets with straddling prints **split
exactly** at boundaries; per bucket `|buy − sell| / V`; VPIN is the mean over buckets. Degenerate
input returns `None`, never `0.0`.

**`N_BUCKETS = 50`** — EL O'H's own standard, **fixed on availability before any correlation**
(a 60-day sample showed 100% of alert-days carry ≥5 contracts per bucket at n=50, median 248).
`n = 10 / 20 / 100` are computed as a **sensitivity that carries no verdict**, and a test forbids
any of them becoming primary. This is `MA58`'s precedent, where K=10 was fixed on availability and
the K=5 sweep carried no verdict.

**Eligibility, classification and the unit are `O14`'s, imported rather than restated:** the same
`SINGLE_LEG_CODES` filter, the same ≥20-print floor, the same per-contract Lee–Ready applied in
time order. A second copy of the classifier would be the `B7` defect class.

---

## 2. A DEPARTURE FROM THE ITEM'S WORDING, DECLARED HERE RATHER THAN MADE SILENTLY

MB16 specifies the kill **"within date"**. **That cross-section does not exist on this book.**
Measured: **1,570 dates, median 2 names per date, max 17, ZERO dates reaching 20 names, and 39.7%
of dates carrying exactly one name.** A within-date Spearman is undefined at n = 1 and identically
±1 at n = 2, so the registered statistic would be a constant or noise rather than a measurement.

**`O14` hit the identical wall and sorted MONTHLY.** The kill is therefore taken on the
cross-section the study actually sorts on — **within month** — with the **pooled** correlation
reported beside it, and **it fires if EITHER exceeds the bar**, which is strictly more conservative
than either alone. The same monthly cross-section is the arm's, for the same reason.

## 2a. AND THE REGISTERED KILL CANNOT DETECT THE RENAMING IT EXISTS TO CATCH

**VPIN is UNSIGNED and `signed_volume` is SIGNED.** Flipping every aggressor side leaves VPIN
bit-identical and negates `signed_volume` — both pinned by test. So a correlation between them
cannot see a VPIN that is a pure function of that feature's **magnitude**, which is the renaming
the kill is for.

**The rule is run AS WRITTEN and the defect is reported, not silently repaired** (`MB1`'s
discipline: running a registered rule verbatim is what surfaces that it does not follow). The
magnitude comparison is reported beside it and **also clears the bar** — +0.5661 against 0.90 — so
**the blind spot is real and concealed nothing**, and roughly two-thirds of VPIN's rank variance is
information neither O14 feature carries.

---

## 3. THE ARM — one arm, fixed completely, no grid

**A1.** Does quote-classified VPIN sort the alert book's realised trade returns?

* **Unit:** the alert, `(ticker, date)`; `pnl_pct` from `state_r2_splitclean.pkl`, the split-clean
  book, exactly `O14`'s.
* **Cross-section:** MONTHLY (§2).
* **Statistic:** quintile long-short mean return with a month-block *t*, computed by **`O14`'s own
  `score_arm`, imported** — the identical arithmetic `O3`/`O4`/`O5` and `O14` were judged by.
* **TWO-SIDED on |t|.** No sign is declarable: VPIN is unsigned by construction, and EL O'H's own
  claim is about **volatility**, not direction, so neither a positive nor a negative return
  prediction follows from the theory. This is `O14`'s constraint inherited, not a choice.
* **A SIGN-AGREEMENT CLAUSE does the work a declared sign would:** an arm strongly positive in one
  half and strongly negative in the other clears on |t| twice while carrying no usable information.

**Bar — all three, or the arm is NULL:**

1. full-sample **|t| > the arm's own within-month permutation p95** (2,000 draws, `O14`'s null);
2. **both halves** clear their own permutation p95 (400 draws each, `O14`'s split at the median
   month);
3. **the two halves agree in sign.**

**Ambiguous against a pre-committed threshold is a NULL** (`RUN_RULES` A6). Benjamini–Hochberg at
q = 0.10 is stated for continuity with `O14` and is **trivial at one arm** — said here so nobody
later reports it as a surviving multiple-testing correction.

---

## 4. Void conditions

1. Fewer than **40 months** or fewer than **2,500 usable rows** → the arm is UNDERPOWERED, not
   null (`O14`'s floors, `MIN_MONTHS` / `MIN_TRADES`).
2. Any sensitivity bucket count reported as the primary, or the primary changed after seeing an
   outcome.
3. The Bulk Volume classifier built or scored anywhere.
4. Quoting a result as evidence about the ALERT ENTRY. **`R2` stands**: the alert book loses to
   random entry by −5.0640pp/trade, so a candidate here is a candidate for a **future book that
   does not exist** — never evidence the alert works, never an adoption. `O11` binds.
5. Quoting any figure without the alert-days-only conditioning (§6).
6. Re-running the arm with a different bucket count, cross-section or bar and reporting the better
   one.

---

## 5. Controls

* **C1 (gating, own pass, ALREADY RUN AND READ):** the classifier reproduces `O14`'s banked
  `classified_rate` median exactly and its per-unit `signed_volume` at max abs deviation **0.0**.
  Without this, VPIN is not built on `O14`'s instrument and no comparison means anything.
* **C2 (gating, own pass, ALREADY RUN AND READ):** the item's kill, §0.
* **C3 (reported):** the magnitude comparison, §2a.
* **C4 (reported, no verdict):** VPIN's own distribution and its stability across the sensitivity
  bucket counts.

---

## 6. Scope, stated in every output

**ALERT DAYS ONLY.** The tick cache is exactly the alert days and nothing else, so every figure is
conditioned on them and **none generalises to the tape**. There is **no pinned freeze for the tick
cache** — `D:` holds only the two CHAIN freezes — so the units are pinned by a recorded fingerprint
instead (`MB15`'s finding, inherited).

---

## 7. Expectations, recorded before the arm runs

| # | prediction | confidence |
|---|---|---|
| E1 | A1 is NULL | 85% |
| E2 | if it fails, it fails the both-halves leg rather than the full-sample leg | 60% |
| E3 | VPIN's full-sample \|t\| exceeds `signed_volume`'s +0.6577 | 60% |
| E4 | the quintile means are non-monotone | 70% |
| E5 | VPIN correlates with `sweep_share` above 0.30 (both are concentration-of-flow measures) | 55% |

---

## 8. Trial cost

**1 options trial, booked BEFORE the arm runs**, taking options `N` **304 → 305**. The item's own
counter says 302 → 303 and is stale by the two trials `MB1` booked; the live count is re-read from
`by_domain` rather than quoted.

The instrument pass and the kill charge **nothing** — they score no hypothesis against a bar.

---

## 9. What a result here can and cannot mean

A NULL means *"could not be separated from zero at this resolution on alert days"*, **never
"absent"** — and it must be quoted with the design's own resolution.

A CANDIDATE is a candidate for a future book that does not exist. It is **not** evidence that the
options alert works, **not** an adoption, and **not** a licence to trade. `R2` stands and `O11`
binds.

Nothing here reopens `O14`, whose five arms stay NULL, and nothing here is a claim about VPIN on
equities or on a full tape — this is one unsigned statistic on one alert-conditioned option tape.
