# PRE-REGISTRATION — `S17` (decode the rest of EVENTS) + `S19` (the MD&A anomaly)

**Written 2026-08-13, before any forward return was joined to any event indicator or any
MD&A score.** Committed **ALONE** — one `.md`, zero `.py` — as a strict git ancestor of every
measurement commit, which is the only thing that makes it a register rather than a write-up.

Two audit items, one register, because they are the last two untested **S**-series research
rows and both are "test an existing, already-paid-for data asset as a signal". They share no
data, no instrument and no statistic, so they are reported as two independent items and a
failure of one says nothing about the other.

---

## §0 — `S10`'s accounting half: NOT in this register, and why

The task asked whether `S10`'s accounting half is small enough to share this register, and to
**say so either way**. It is not. This is a measurement, not a preference:

1. **It needs a loader change and therefore a full panel rebuild.** The audit's four components
   are Beneish M-score, Altman Z-score, external financing and NT filings. Every SF1 column the
   first three need **exists in the export** — checked directly against
   `data/backtest/fundamentals.csv`'s 112-column header — but **eight of them are absent from
   `WRDSProvider._KEEP`** (`assetsc`, `ppnenet`, `depamor`, `workingcapital`, `retearn`,
   `liabilities`, `ncfcommon`, `ncfdebt`), so today they load as nothing. `_KEEP` is the
   allowlist whose own comment calls it load-bearing, and adding to it means rebuilding the
   panel and re-verifying coverage on eight new columns — the COVERAGE RULE's exact failure
   mode, which has bitten this project four times. **`S17` and `S19` need no rebuild at all.**
2. **One of the four components is not buildable from anything we own.** NT 10-K / NT 10-Q
   late-filing notices require new EDGAR collection. The audit's veto is *"exclude any name
   flagged by **two or more**"* of **four**. With three computable, "two or more of three" is a
   **different rule**, not a trimmed one — and choosing it after seeing which components happen
   to exist is precisely the degree of freedom a register exists to remove.
3. **Trial cost.** `S17` (10) + `S19` (2) already charges 12 equity trials. Adding `S10`'s four
   components plus the veto arm would charge ~17 in one session and take `N` past 200.

Scoped for a future session, not started, not charged: add the eight columns, rebuild, verify
coverage **first**, build Beneish and Altman as **exclusion flags** rather than ranked signals,
collect NT filings, and only then decide the veto rule — in its own register.

---

## §1 — Premise findings, measured BEFORE this register was written

Every number in this section is a fact about what data exists or what the code does. None
involves a forward return joined to either hypothesis. They are here because they change what
the audit's two methods can even mean.

### 1a — `S17`: the ledger row and the audit's step 1 are both wrong

The ledger row reads `src=auto` / *"prose mentions only, no section, no commit"*. **There is a
full section at `VALQUO_EDGE_AUDIT.md:838`.** `S19`'s row reads *"no mention anywhere in the
corpus"*; **it is `VALQUO_EDGE_AUDIT.md:1841`, plus two summary-table rows at `:2424` and
`:2538`.** That is the eleventh and twelfth time an `src=auto` "no section" note has been wrong.
**Those notes are not evidence of absence** and both rows are corrected.

**The audit's own method step 1 cannot be executed.** It says *"obtain the code legend from
Sharadar's documentation"*. `bulk.py:20` and `:235` record that **Sharadar ships no legend with
the EVENTS download**, and `D10` records that the documentation was never extracted and that
`scripts/verify_sharadar.py` **has never been run against the real key**. So the codes are
tested **by number, unlabelled**.

**This is a real and permanent limitation, stated before any result: a signal on an unlabelled
code is uninterpretable even if it works.** If code 91 predicts returns I will not be able to
say what code 91 *is*, only what it *does* — and an unlabelled predictor that cannot be
mechanistically explained is exactly the shape of a data artefact. A positive here would be a
lead requiring the legend, never an adoption.

### 1b — `S17`: frequency by code (the audit's step 2), measured

`events.pkl`, 17,779 tickers, **35 distinct codes**, **4,240,434 code-occurrences**,
**1993-11-08 → 2026-07-29**.

| rank | code | occurrences | tickers |
|---:|---:|---:|---:|
| 1 | 91 | 1,144,079 | 15,600 |
| 2 | 81 | 842,973 | 17,538 |
| 3 | 34 | 496,638 | 16,064 |
| 4 | **22** | **385,426** | **10,147** |
| 5 | 71 | 302,070 | 11,569 |
| 6 | 52 | 242,851 | 11,362 |
| 7 | 11 | 217,033 | 11,550 |

**Code 22 is the fourth most frequent and is already tested.** It was decoded empirically on
2026-08-01 and its signal — post-earnings-announcement drift — was tested and **REJECTED**
(roadmap #15, `pead_car` IC *t* +2.215 standalone but incremental *t* **+0.020** after
residualising on momentum, beaten by a control using no earnings data at all).

**REGISTERED ARM SET: the five most frequent codes EXCLUDING 22 — `91`, `81`, `34`, `71`,
`52`.** The exclusion is because re-testing an already-rejected code would charge a trial to
re-derive a known answer. **No other code is tested, and the set is fixed here.**

### 1c — `S17`: the prior is the project's own measurement, and it is discouraging

The empirical decode that identified code 22 did so by **information content**, and in doing so
it **already scored every arm in §1b's registered set**. Median absolute return on an event day
against a 1.292% baseline (`bulk.py:243-247`):

| code | ratio | |
|---:|---:|---|
| **22** | **1.64×** | the decoded earnings code |
| 91 | 1.15× | registered arm |
| 71 | 1.13× | registered arm |
| 81 | 0.98× | registered arm |
| 52 | 0.96× | registered arm |
| 34 | 0.94× | registered arm |
| 11 | 0.95× | not tested |
| 57 | 0.84× | not tested |

**So the mechanism question the task asks — do the remaining codes share code 22's mechanism —
is answerable before any arm runs, and the answer is NO.** Code 22's mechanism is an
*information shock*: a 1.64× day-of move is what an earnings release does to a price. PEAD is
**drift following that shock**. Every registered arm has already been measured at **0.84× to
1.15×**, i.e. indistinguishable from an ordinary day. **There is no shock for drift to follow.**

**The honest qualification, which is why the arms are still worth running.** Day-of absolute
return is a **volatility** measure and the test here is a **directional forward-return** one.
Those can come apart in two ways that are not exotic: a *scheduled* event (a dividend
declaration, a routine filing) moves no price on the day precisely because it was expected,
yet may still mark a state of the firm that predicts; and a slow-diffusing event (a governance
or ownership change) can predict drift with no announcement-day jump at all. So the prior is
discouraging and specific, not disqualifying.

### 1d — `S19`: the verdict statistic this task names has ALREADY been measured, on the original names

`HANDOFF_lazy_prices_ic.md` §6 reports, for the MD&A measure on the original 194 names:
**residual IC after regressing out all themes +0.010 (*t* 0.65)**, correlations with every theme
under 0.08, and *"added to the composite it takes the long-short from +8.8% to +4.5%/yr"*.

**That is the incremental-IC statistic this register is asked to use, and on the names that
generated the observation it is already a null.** It was measured on a thin restriction (49
dates, 37 with a usable cross-section). This matters for what `S19` can buy: **the trial is not
buying a first look at the incremental IC — it is buying the same statistic on names that did
not inform the observation.** If it fails, the finding is that a −2.58 *t* in a 28-cell grid did
not survive contact with new names, which is worth knowing and is what the audit asked for.

### 1e — `S19`: what the original study is, and the sign

195 tickers, 7,095 filing pairs, 194 priced, 2016-08 → 2026-03, **28-cell grid, filed as a
null**. Inside it, `mdna_cosine_tf@21` gave a long-short of **−11.2%/yr, NW *t* −2.58**, in
**both halves**, surviving word-count floors, and `mdna_jaccard@63` gave **−2.49**.

Decomposed by the original: firms that **rewrote their MD&A most** returned **+29.9%/yr**
against **18.7%/yr** for those that barely touched it, on a **+21.3%/yr** universe.

> **THE SIGN, COMMITTED HERE IN WRITING BEFORE ANY NEW RETURN IS JOINED: companies whose MD&A
> language changes MORE year-over-year subsequently OUTPERFORM.** The tested predictor is
> therefore `mdna_change = 1 − similarity`, expected **POSITIVELY** related to forward return.
> **This is a ONE-SIDED test.** A significant result with the opposite sign is a **REJECT**, not
> a discovery, and may not be reported as one.

---

## §2 — `S17` design

**Instrument.** An event-window signal, exactly as the audit specifies. It is **not** a decile
book and **not** a theme, so **none of X7's calibrated floors apply to it** and none is quoted.
(X7 calibrated the 69-date decile book: theme IC *t* 2.71, long-short HAC *t* 2.28, alpha
1.95pp. Quoting any of them here would be the cross-configuration error this record has paid
for twice.)

**Universe and prices.** `data/backtest/prices/<TICKER>.csv`, the panel's own survivorship-free
export (2,998 names, includes delisted). **The full series is read; `days` is never passed** —
per-ticker truncation is audit **B6**'s inverted-universe defect and is avoided by construction,
pinned by a control. **`close` is used, and only for RETURNS** — the split/dividend-adjusted
column, which is correct for a return and wrong for anything touching a strike (session 30).

**Screen.** The live investability screen's two legs that this data can support:
`PRICE_FLOOR = $1.00` and `MIN_MARKET_CAP_MM = $50M` (market cap from the monthly `daily.pkl`
cache, as-of the rebalance date). The third leg, `MIN_AVG_DOLLAR_VOLUME`, is **not applicable —
the price export carries date and close only** (audit **B13**, `PARTIAL — BLOCKED ON DATA`), and
a market-cap stand-in would be a different screen wearing its name.

**Grid.** Month-end trading dates over the full event × price overlap. A date is scorable only
with **≥ 50 screened names carrying a computable forward return**; the per-date cross-section
sizes are reported.

**Conditioning.** For each (name, date): indicator = 1 if a code-*c* event occurred in the
**trailing 21 CALENDAR days**, strictly **before** the rebalance date. Events are calendar-dated;
returns are measured in **trading** days.

**Statistic.** Per date, the cross-sectional **mean forward return of event names minus mean of
non-event names**, at **21 and 63 trading days**. HAC (Newey–West) *t* over dates, lag chosen for
the horizon's overlap. **5 codes × 2 horizons = 10 arms.**

**Direction: TWO-SIDED, forced.** The codes are unlabelled (§1a), so no sign can be declared
without inventing a meaning for a number. Two-sidedness costs power and that is the honest
price — the same forced choice `O14` made and for the same reason.

**Significance, all four required for a positive:**
1. Full-sample |HAC *t*| exceeds the arm's **own permutation p95**. The null shuffles the event
   indicator **within each date**, preserving the per-date event count and the return
   cross-section exactly.
2. Two-sided permutation *p*.
3. **Benjamini–Hochberg at q = 0.05 across all 10 arms** — the audit asks for FDR control by
   name and this is the sweep it warns about.
4. **Both halves**: the same sign in both, and each half clearing its **own** permutation p95.

Anything less is a **NULL**. Ambiguous against a pre-committed threshold is a NULL
(`RUN_RULES` A6).

---

## §3 — `S19` design

**Held-out names, mechanically selected and frozen before collection began.** Today's largest by
market cap from the Sharadar DAILY cache — **the same `large_cap_universe` ranking the original
study used** — minus the 195 already spent, taking the next **600** in rank order. The spent
names occupy ranks 0–248, so every held-out name is rank ≥ 249. The list was written to disk
**before** the collector was launched and is reproduced in the artifact.

**This is X1's universe split as the audit asks for it: the original 195 are the deciding set by
construction, so every one of these names is genuinely held out.** Collection is EDGAR document
acquisition and is **not** a measurement — the same standing this project gave the `O14` tick
cache and the JKP download, neither pre-registered. **No forward return is joined to any MD&A
score until after this register is committed.**

**Expected attrition, predicted here rather than explained afterwards.** The rank-ordered list
begins with TSM, ASML, HSBC, NVS, RY, AZN, BABA, MUFG — **foreign private issuers, which file
20-F/6-K and not 10-K/10-Q**, so they will yield zero filings. ETFs and trusts likewise. **They
are NOT filtered out**, because any filter is a choice; they drop out naturally and the
attrition is reported as coverage. This is the same non-random hole `O6/O7/O17` found (29 of 186
names, every one a foreign private issuer).

**Arms — EXACTLY TWO, and no grid.** The original was a 28-cell grid; re-sweeping it would
repeat the sin that made it a null. Only the two cells the original flagged are tested:

| arm | measure | horizon |
|---|---|---|
| **A1** | `mdna_cosine_tf` | 21 trading days |
| **A2** | `mdna_jaccard` | 63 trading days |

**Verdict statistic — incremental IC against the seven incumbent themes, the PEAD
residualisation template.** Per rebalance date, the MD&A change score is regressed
cross-sectionally on the deployed theme columns from the banked corrected panel
(`panel_corrected_69d.pkl`), and the **residual**'s rank IC against forward return is the number
that decides. This is the statistic that killed `pead_car` (+2.215 standalone → **+0.020**
incremental) and it is the right one: a signal that merely re-expresses momentum or growth adds
nothing to a composite that already carries both.

**Thresholds, all required:**
1. **NW *t* > 2.0 on the incremental IC, in the committed POSITIVE direction** (the audit's own
   bar), on held-out names only.
2. **Both halves** of the covered subsample, same sign.
3. A positive verdict through **`holdout_compare_panels`** at the shipped margins (audit's own
   second clause).

**A STRUCTURAL LIMIT, stated before running, in `S18`'s class.** The panel starts 2009-01-15;
MD&A scores start 2016-08. **38 of 69 panel dates are covered**, all in the late portion, so a
both-halves gate **on the full panel is impossible, not merely underpowered**. Halves are
therefore halves of the **covered subsample** (≈19 dates each, against the shipped gate's
`min_dates=16` floor). **A pass on 19-date halves is not the same object as a pass on 34-date
halves** and will not be reported as one.

**Survivorship, carried from the audit verbatim:** today's large caps, zero delisted names, and
the paper's own effect is documented as **strongest in smaller, less-covered firms** — the tier
this universe excludes. **A positive here would be more surprising than the literature predicts,
not less, which is a reason for extra scepticism rather than excitement.**

---

## §4 — Expectations, written before any result

Scored honestly afterwards. This project's directional calls have been wrong more often than
right, which is exactly why they are written down first.

1. **All 10 `S17` arms NULL — 80/20.** §1c is a measured mechanism prior, and when the prior has
   been a measurement rather than intuition this record's calls have been right.
2. **At least one `S17` arm clears full-sample but fails both-halves or BH — 65/35.** Ten
   correlated arms against a 5% bar; this is the shape every sweep here has produced.
3. **Code 91 is the most likely to show something — 55/45**, on nothing better than its 1.15×
   being the highest of the five and its 73 events/ticker being the densest.
4. **`S19` A1 NULL — 75/25.** The incremental IC was already +0.010 (*t* 0.65) on the names that
   generated the effect; new names should not do better.
5. **`S19` A2 NULL — 80/20.** `mdna_jaccard@63` was the weaker of the original's two cells.
6. **Held-out attrition exceeds 25% of the 600 — 70/30**, from foreign issuers and funds.
7. **The `S19` sign, if anything shows at all, comes back POSITIVE as committed — 60/40.** The
   original's effect was stable across both its halves, which is weak evidence it is not pure
   noise even though it was 1 of 28 cells.
8. **`S17` and `S19` both return a verdict rather than voiding — 70/30.**

---

## §5 — Controls, fixed here

* **C1 — the event join reproduces the project's own decode.** Code 22's day-of median absolute
  return ratio must come back at **≈1.64×** against a ~1.29% baseline. **If it does not, the
  event join is wrong and every `S17` arm is VOID** — this runs and is read **before** any arm.
* **C2 — point-in-time.** Zero events dated on or after their rebalance date; zero negative
  conditioning gaps; forward returns strictly forward.
* **C3 — no per-ticker truncation.** The B6 defect: assert the loader reads whole series and that
  the earliest cross-sections are not composed of names that stopped trading early.
* **C4 — coverage FIRST**, per the standing rule: names, dates, cross-section sizes, event rates
  per code, and what the screen removed, all reported before any arm is read.
* **C5 — `S19` disjointness.** The held-out ticker set ∩ the original 195 = **∅**, asserted.
* **C6 — the strong one: my incremental-IC instrument reproduces the ORIGINAL study's published
  number.** Pointed at the original 195 names it must return the residual IC **+0.010 at *t*
  0.65** reported in `HANDOFF_lazy_prices_ic.md` §6. **If it does not reproduce, the discrepancy
  is reported and no `S19` verdict is issued on that instrument** — a new instrument agreeing
  with nothing is not evidence.
* **C7 — the permutation null is calibrated**, not assumed: its own false-positive rate is
  measured against its own p95 (the `R3` lesson — a raw design effect or an uncalibrated null
  manufactures corrections out of noise).
* **C8 — `S19` is not a momentum proxy.** Report the residualisation's own R², and the MD&A
  score's correlation with each theme, so an incremental result cannot be a repackaged incumbent.

---

## §6 — Void conditions

1. **Testing any code outside `{91, 81, 34, 71, 52}`, or any `S19` cell outside `{A1, A2}`**,
   voids the item. The sets are fixed in §1b and §3.
2. **C1 failing voids `S17` entirely.**
3. **C6 failing withdraws the `S19` verdict**, as stated.
4. **`S19` is UNDERPOWERED and returns NO VERDICT** if the collection yields fewer than **100
   held-out names with usable filings** or fewer than **24 covered rebalance dates with ≥ 30
   scorable names**. Trials are **charged in full anyway** — running and then voiding does not
   refund the search (session 26's precedent).
5. **Reading the `S19` sign backwards is forbidden.** §1e commits to POSITIVE. A significant
   negative is a REJECT.
6. **No threshold, universe, screen, horizon or statistic in this register may be changed after
   any number is seen.** If one is wrong, the item is reported void and re-registered.
7. **Neither item adopts anything.** An adopt would be a **VINTAGE EVENT** and Don's call. The
   vintage must be **DERIVED** via `track_meter.current_vintage()`, never quoted from a prompt or
   a handoff (`PT-GAPDUE`).

---

## §7 — Trial cost

**`S17` 10 arms + `S19` 2 arms = 12 equity trials. Equity `N` 186 → 198.** Charged whether or
not anything clears, and charged in full on a void. Options (285) and infra (11) are untouched.
`BACKTEST_RESULTS.json` is owed a refresh at the new denominator.

Understating `N` overstates the significance of every DSR-gated claim, which is why the count is
fixed here rather than after the arms are read.
