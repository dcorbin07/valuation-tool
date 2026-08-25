# HANDOFF — the data-miner lane. Chain harvest (closed) + the I-4 event spine.

**LATEST: O-1 COVERAGE PULL — SHIPPED 2026-08-25, STAGE 1 COMPLETE, STAGE 2 NOT RUN. Zero
trials.** Full record in `O1_COVERAGE_PULL_RECORD.md`; four things a future reader needs:

1. **The pull raises `O-1`'s flagged coverage from 74 names to 2,969 usable cells — and that is
   0.82× its own registered floor of 3,600 matched trades.** Matching can only reduce it, so
   **the floor is not reachable at the registered primary tenor even from a complete pull of
   everything the vendor holds.** The half-split constraint *is* met (1,467 / 1,502 against a
   1,200 sub-floor) — the total binds, not the balance. A coverage fact, not a verdict.
2. **The vendor's option history starts 2012-07-17**, measured on the panel's own rebalance
   dates. **1,311 of 6,542 flagged rows (20.0%) are unobtainable at any price** — recorded as
   not-obtainable, never as a pull that fell short. The handoff's "chain store starts 2016" is
   *our store's* start, not the vendor's; using it would have discarded three good years.
3. **STAGE 2 — the exit path of a held contract — IS NOT PULLED**, and it is the thing to run
   next if anyone buys more vendor time. Sized at **53.6 s/span → ~78 h flagged, ~156 h with a
   control**, outside the window. Stage 1 supports a **hold-to-expiry** settlement (entry chain +
   the underlying's close at expiry, which we already own); **a stop-or-target exit rule needs
   stage 2.** Warning: 3 of 23 sampled spans returned 0 rows after 154 s, the call-timeout
   ceiling, so the per-span cost is bimodal and a mean understates the tail.
4. **Whole chains are stored to 1200 DTE, unfiltered** — not narrowed to puts or to a moneyness
   band, because collection must not bake in a selection rule that a register might move, and
   after 2026-09-01 there is no second chance. The secondary 330–400 DTE band is **thin at 771
   cells against the primary's 2,969**.

New freeze `D:\thetadata\freeze_o1_coverage_2026-08-25` — never a mutation of an existing one.

---

**LATEST: W-3b — IBES ACTUALS INTO THE EARNINGS-DATE SPINE, SHIPPED 2026-08-25. Executor run of
the scout's draft; ACCEPTED WITH TWO AMENDMENTS. Zero trials.** Adjudication in
`W3B_EXECUTION_RECORD.md`; the four things a future reader needs:

1. **The repair works and beats the draft: 29 of 29 FAIL_CLOSED names recovered, all 186 now
   COVERED.** Those 29 were every foreign private issuer in the book.
2. **`I-4`'s dates are "Item 2.02 results filings", not "earnings announcements", and the two
   differ in 23.3% of name-years.** PNC files 7.67 code-22 dates a year against IBES's 4.00, NKE
   6.20, ROST 8/yr until 2013 (monthly sales); MSFT/JPM/AAPL are exactly 4.00 = 4.00. The clean
   case is **AAPL `2019-01-02`, Apple's revenue-guidance letter**. **No landed number is wrong** —
   each is right for the dates it used — but `owns_the_event` has been answering *"owns the next
   Item 2.02 filing"*. **Nothing is re-read here.**
3. **THE MERGED SPINE IS A NEW INSTRUMENT, NOT A DROP-IN.** It is additive in dates (nothing
   deleted) and **not inert for consumers** — it adds 11,863 dates to already-covered names, so
   the predicates answer differently. It lives in its own artifact so adopting it is deliberate.
4. **Three identifier traps, all measured, all of which the obvious route walks into:** `oftic` is
   17.7% wrong-company across the 29; escaping reuse needs a **date**, not a different column
   (current-cusip-only truncated HWM by 82.9%); and **IBES masks cusip characters with `X`**
   (`0636711X` vs `06367110`), which returns zero rows and reads as "not covered" — it hit BMO,
   CNQ and TD. Use `valuation/edge/ibes_events.py`, never a bare ticker join.

---

**LATEST: WRDS — CENSUS, PULL, PHASE 2 PROBES, AND A RE-PROBE THAT CORRECTED THE CENSUS
(2026-08-24). Zero trials throughout; the full record is `WRDS_CENSUS.md`.** Four things a
future reader needs and will not guess:

1. **This account's Thomson verdict flipped, and the census had it wrong.** All eight `tfn.*`
   tables genuinely return `permission denied` — re-verified on eight FRESH connections — but
   `tfn` is a legacy shell, and WRDS's own SEC-derived products are ENTITLED:
   **`wrdssec_all.wrds_13f_holdings`, 103,984,958 rows, 1987→2025**, and
   **`wrdssec_insiders.table1`, 10,083,927 Form 4 transactions.** *A census that probes the names
   in a brief measures the brief* — enumerate libraries first.
2. **The 13F history does NOT repair the pre-2013 `institutional` hole. It buys ONE rebalance
   date.** Filing managers step from 71 (2012) to 3,457 (2013) at the SEC's structured-XML
   mandate, so pre-2013 rows are a handful of early filers touching many issuers. `MA58`'s
   49-of-69 defect stands, and it is structural rather than an entitlement problem.
3. **The pull had a silent hole and file-level checks could not see it.** `ibes.actu_epsus` was
   short **102,213** rows while every chunk read `ok` and every sha256 verified: a NULL date
   satisfies neither `>= Jan 1` nor `< Jan 1`, so those rows belonged to no chunk. Found by
   reconciling against the server's own `count(*)`. **`wrds_pull.py --reconcile` now does that,
   and all eight products reconcile to the row — 53,512,283 rows, 1.263 GB.**
4. **Two ledger rows unpark and one permanently-closed row re-opens**, on PHASE 2's probes:
   `B13`/`S7` on CRSP `dsf` ($ADV at 89.7% of the universe against the current path's 19.8%, over
   64 of 69 dates), and **`S25` on `comp.co_hgic`** — a genuinely dated GICS history, 94.9%
   coverage, 41.9% of our names reclassified — with the taxonomy caveat that its 11 GICS sectors
   are not the panel's 11 Yahoo-style ones, so the crosswalk is a choice a register must own.

**Fences unchanged: `D:\wrds` only, nothing licensed committed, derived statistics out.**

---

**LATEST: S3-I5 (ticker-reuse adjudication) + S3-I2 (catalyst calendar) — SHIPPED
2026-08-23.** S3-I5 **lifts the Tier C/E quotability block** this file imposed on itself: 45
units over 26 symbols adjudicated against a point-in-time identity — **36 REUSED, 7 SPLIT_YEAR
(with cut dates), 2 SAME_COMPANY**. S3-I2 ships the FDA half of the catalyst calendar
forward-only and records the index half **BLOCKED with evidence** rather than inventing one.
Both FIXED/collection class, **zero trials**. Jump to *S3-I5* and *S3-I2* at the end.

**I-4, THE EVENT SPINE — SHIPPED 2026-08-20.** One canonical point-in-time
earnings-date table, code 22, with the coverage census, the 29 fail-closed names, the 34/35
sunset, and a test that it agrees with the shipped `refuse_within` / `owns_the_event` paths.
**Zero trials, collection-and-provenance class.** Jump to *THE I-4 EVENT SPINE* below.

---

## The chain harvest (closed 2026-08-18)

**Lane:** data miner. **Status: HARVEST CLOSED 2026-08-18. THE MINER IS IDLE AND THE
SUBSCRIPTION CAN LAPSE ON SCHEDULE.** All five tiers complete, **2,850 units / 353.7 M rows /
17.69 GB, ZERO failed anywhere**, frozen and `--full-hash` verified.
**Zero trials — collection is not a test.** No analysis was run and none may be quoted
from this data beyond the integrity checks below.

**READ FIRST IF YOU ARE ABOUT TO USE THIS DATA:**

1. **The final all-tiers census** is the permanent record — what exists, what is unreachable in
   principle, what was skipped and why. Below, and in `D:\thetadata\HARVEST_CENSUS.json`.
2. **45 units over 26 symbols carry another company's option data** (`pre_panel_history`).
   Filter it or resolve those symbols against a point-in-time identifier. **This is not
   optional and it is not resolved.**
3. **`ok_partial` is not `ok`.** 145 units are short of a whole year, for three different
   reasons, and the census names which. Three separate bugs in this harvest came from treating
   a partial year as a whole one.

New files, all mine: `mine_deep_chains.py`, `freeze_chain_store.py`,
`scripts/options_coverage_census.py`, `tests/test_deep_harvest.py`,
`DEEP_HARVEST_SUMMARY.json`, this handoff.
Nothing under `valuation/edge/options_*.py` was touched. Nothing under `.github/` was touched.
**The existing freeze is untouched** — new work writes to a new root, `D:\thetadata`.

---

## THE HEADLINE: MOST OF THE QUEUE WAS ALREADY ON DISK, AND THE PULL WAS STOPPED

The four-tier harvest was queued on the premise that the holding periods behind the banked
options book were **not** cached, and that the expiring Pro window was the only way to get them.
**Measured exhaustively on every unit rather than sampled, that premise is false.**

**`data/options` already holds 42,608 of 42,650 required holding-period trading days = 99.90%,
with ZERO missing symbol-years.** The two tiers that consumed the entire queue — A and B — are
**dead**. The harvester was stopped and the window redirected.

**A correction to this file's own first version, because it matters for what was spent:** the
stopped run is recorded below as having banked 13 units. It had actually pulled **886** — the
checkpoint loop died while the workers kept going (BUG 5). The units were recovered from disk
rather than re-pulled, so **Tier A is 393 of 400 complete** as a side effect of a bug, and the
twelve hours were not wasted.

Reproduce: `python -m scripts.options_coverage_census`
Artifacts (gitignored, local): `data/free_analysis/OPTIONS_COVERAGE_CENSUS.json`,
`TIERC_FEED_PROBE.json`, `TIERC_SIZING.json`, `TIERC_NEVER_TRIED.json`.

### Q1 — holding-period coverage, per year, all 1,361 alert symbol-years

Measured against a **session calendar derived from the cache itself** (2,515 sessions,
2016-01-04 .. 2025-12-31), because a weekday is not a trading day and measuring against weekdays
understates coverage by the holiday count. Tier A years in bold.

| year | trading days needed | present | absent | % |
|---|---|---|---|---|
| **2016** | 3,442 | 3,441 | 1 | **99.9709** |
| **2017** | 5,500 | 5,500 | 0 | **100.0000** |
| **2018** | 3,882 | 3,882 | 0 | **100.0000** |
| 2019 | 3,496 | 3,457 | 39 | 98.8844 |
| 2020 | 4,056 | 4,055 | 1 | 99.9753 |
| 2021 | 6,689 | 6,689 | 0 | 100.0000 |
| 2022 | 1,774 | 1,774 | 0 | 100.0000 |
| 2023 | 3,595 | 3,595 | 0 | 100.0000 |
| 2024 | 6,588 | 6,588 | 0 | 100.0000 |
| 2025 | 3,628 | 3,627 | 1 | 99.9724 |
| **total** | **42,650** | **42,608** | **42** | **99.9015** |

**Zero missing symbol-years** (`q1_missing_units` is empty — no unit is absent or unreadable).
All 42 absent days are **39 of one contiguous MA gap** plus three isolated singletons
(DHR 2016-07-05, TMUS 2020-06-25, SONY 2025-09-29).

**CORRECTED 2026-08-18: ALL 42 ARE VENDOR ABSENCES AND NOT ONE OF THEM IS CLOSEABLE. The
coverage figure should therefore read 100% of what is obtainable, not 99.90%.** This file used
to call them "cheap to close as a targeted re-pull … ~4 units, minutes", which was an inference
from the cache rather than a measurement of the feed. Probed directly:

* **MA's option EOD data stops dead at 2019-08-23.** Every request past it returns
  `NoDataFoundError` — at `max_dte` 1200 and at 90, for single days and for month spans. The two
  stores agree to the day: `data/options` and the D: raw pull both end 2019-08-23, independently.
* **The three singletons are the same class, and the probe is unusually clean:** the feed serves
  DHR 2016-07-01 then 2016-07-06, TMUS 2020-06-24 then 06-26, SONY 2025-09-26 then 09-30 —
  skipping precisely the missing day while serving both neighbours.
* **A fresh reconciliation reproduces the census's 39 exactly.** MA has 89 holding-period
  *trading* days in 2019, 39 absent, every one of them after 2019-08-23. The first pass of that
  check counted 42 because it used weekdays, which swept in Memorial Day, 4 July and Labor Day —
  the weekday-is-not-a-trading-day trap this harvest has now hit twice.
* **One figure in the old sentence does not reproduce and is not restated:** the gap's END was
  recorded as 2019-09-20; re-derived it is 2019-10-18, the last 2019 day the book needed. The
  census artifact does not retain per-day detail, so the discrepancy cannot be reconciled from
  the repository — only re-derived. The count (39) and the start (2019-08-26) agree exactly, and
  the verdict does not depend on the end date, since every absent day falls after the vendor's
  last served one.

**The perishable years are the most complete ones.** That is the whole finding: 2016 is 99.97%
and 2017–2018 are exactly 100%, so the years that vanish on 2026-09-01 are the years with
nothing left to fetch.

### Q2 — alternatives, not just traded contracts. Already present.

| | |
|---|---|
| entry dates with a chain in `data/options` | **3,885 of 3,885 (100.00%)** |
| traded contract present | **3,885 of 3,885** |
| **alternative contracts the book never held** | **2,713,919** |
| median per entry date | **636 contracts, 8 expirations, 61 strikes** |
| mean per entry date | 699.6 contracts |

The mean slice of **699.6 rows** matches the figure independently measured in the options re-open
list (commit `10977a2`) — two passes, different code, same number, which is a clean cross-check.

**This changes what unblocks O21-D2.** The existing trade-scope freeze
(`data/options_freeze/R2_CORRECTED_2026-08-08/`) holds a forward path for the **traded** contract
and **zero** alternatives, so any question needing a contract the book never held is unanswerable
on it *by construction*. The live store holds 2.7 million such contracts. **The alternatives are
not missing — they are unpinned.** The unlock is a freeze, not a pull. See Tier 0.

### Q3 — the optionable universe. THIS IS THE ONE GENUINE GAP.

| | |
|---|---|
| panel names | 2,531 |
| symbol dirs in `data/options` | 1,000 |
| **optionable intersection** | **906** |
| with **any** 2016–2018 unit | **411** |
| with **all three** 2016–2018 | **384** |
| **with none of 2016–2018** | **495** |
| names beyond the mined alert book | 724 |

Distribution of 2016–2018 years held: 0 years → **495 names**, 1 → 16, 2 → 11, 3 → 384.

The 495 split cleanly, and the split matters because only one half is recoverable:

* **420 never tried.** 414 of them have **2024 as their earliest year** — these were never in
  scope for the breadth miner, so their absence is a *mining scope choice*, not a vendor gap.
* **75 tried and genuinely empty.** All three years returned `.empty`. Nothing to get.

**The feed does serve them.** Probed live on 14 randomly sampled never-tried names:
**11/14 served for 2016, 10/14 for 2018** (~75%; every failure was `NoDataFoundError`, not a
timeout). Sized on real full-year pulls at `max_dte=1200`: PKG 72,660 rows / 11.7 MB / 16.3 s,
MOD 33,970 / 5.5 MB / 11.2 s, AFG 56,408 / 9.1 MB / 13.5 s → **median 13.5 s and 8.8 MB per
symbol-year**. These are small names, roughly a quarter of a megacap.

**1,260 symbol-years ≈ 4.7 hours and ≈ 11.1 GB raw.**

### Q4 — the Index's 86 names. A real gap, but NOT perishable.

| | |
|---|---|
| with a cache dir | **80 of 86** |
| **no cache dir at all** | **6** — AGX, FORM, IX, POWL, VIAV, VICR |
| with a 2025 or 2026 unit | **45 of 86** |
| lacking any recent unit | 41 |

**None has a 2026 unit.** But 2025–2026 sits comfortably inside Standard's rolling 8-year window,
so **Tier D needs no Pro time** and should be run after the deadline, not before it.

---

## THE DEADLINE ARITHMETIC NOBODY HAD APPLIED

Standard's window is **8 years and rolls FORWARD**. Today is 2026-08-17, so the cutoff is roughly
**2018-08-17**. Everything from late 2018 onward is reachable on Standard **after** the Pro
subscription lapses.

**Only 2016 → mid-2018 is genuinely perishable.** Tier B (2019–2025) was never at risk from the
deadline at all — it is recoverable in perpetuity — and it is also 98.9–100% already cached. It
was queued on both a false coverage premise and a false urgency premise.

---

## RE-PRIORITISED QUEUE — which tiers died

| tier | verdict | why |
|---|---|---|
| **0 — freeze `data/options`** | **PROMOTED, running** | Free, no deadline, and the actual unlock for O21-D2 |
| **A** — alert 2016–2018 | **DEAD** | 99.97 / 100.00 / 100.00% already present |
| **B** — alert 2019–2025 | **DEAD TWICE OVER** | 98.9–100% present **and** inside Standard's window |
| **C** — 2016–18, 420 never-tried optionable names | **COMPLETE** | 6.39 h, 2.53 GB, 76.0% hit rate |
| **E** — tenor depth, 2016–18, 836 shallow-only units | **RUN 2026-08-18** | **PERISHABLE, and this file said it was not.** 393-pair sizing, ~5.1 GB |
| **D** — Index 86 names, 2025–26 | **RUN 2026-08-18** | Not perishable; run because the window was already paid for |

**On my own earlier redirect, plainly:** I found the date axis complete and redirected the harvest
to the **tenor** axis (0–1200 DTE instead of 0–90/200). That absence is real — 90 DTE dominates
every year in the cache — but no item on the re-open list is blocked on it, so it was the wrong
thing to spend an expiring window on **at that moment**. **I fixed the axis and not the
question.** It ranked below Tier C and below the freeze.

**CORRECTION 2026-08-18, and it reordered the closing run: THE TENOR DEPTH IS PERISHABLE AND
THIS FILE'S CLOSING SECTION SAID IT WAS NOT.** Standard's window rolls forward from roughly
2018-08-18, so the 836 shallow-only units — all 2016, 2017 and 2018 — go dark the day Pro lapses.
"Nothing perishable remains" was a true statement about the **date** axis, which Tier C closed,
and I carried it across to the **tenor** axis without re-deriving it. Demoting depth on *value*
was right and is unchanged; calling it *non-perishable* was wrong. It therefore ran **before**
Tier D, which stays reachable in perpetuity — if only one of the two had finished, it had to be
the one that cannot be re-fetched.

---

## TIER 0 — pinning the mutable store. The recommended next action.

**Why this is not optional.** `data/options` is the store the analysis scripts actually read —
`o3_o4_o5_surface.py`, `o6_o7_o17_earnings.py` and `o11_o19_o22_o25_portfolio.py` all set
`CHAINS = os.path.join(DATA, "options")`, **not** the freeze. And it is rewritten in place:

* every one of the **5,063** units carries an mtime inside **2026-08-01 .. 08-07**;
* **2,236 of them (44.2%) were written AFTER the authoritative book was banked** on
  2026-08-05 19:51.

That is audit **O16**'s failure on the store that matters, and it is **more than double O16's own
19.5%** — because O16 measured only the files the book *consumed*. A mutable store rewritten in
place cannot support a verdict. The store has been quiescent since 08-07, so this snapshot is
settled rather than racing a live miner.

**Measured cost, both designs:**

| design | extra storage | wall clock |
|---|---|---|
| fingerprint only (one sha256 per unit) | **329 KB** | **135 s** (measured 200.2 MB/s) |
| **full byte-for-byte copy** (chosen) | **26.98 GB** | **~28 min** (measured 16–20 MB/s C:→D:) |

D: has 426 GB free, so the full copy is **6% of the volume**. It was chosen over fingerprinting
because a hash proves drift but cannot undo it — only a copy lets a rejected result be re-derived.

`freeze_chain_store.py` copies **payload and sidecars alike** (`.dte`, `.sha256`, `.oi_degraded`,
`.alias` are part of the state), hashes **both source and destination** per file and **stops
loudly** if they disagree mid-copy, is resumable, and never writes into `data/options`.
`--verify --full-hash` re-hashes the frozen copy *and* separately reports whether the **source**
has drifted since the freeze.

### TIER 0 IS COMPLETE AND VERIFIED (2026-08-17 22:52 UTC)

`D:\thetadata\freeze_options_2026-08-17`

| | |
|---|---|
| files frozen | **12,302 of 12,302** |
| payload units | **5,063** |
| bytes | **26.98 GB** |
| **hash mismatches at copy** | **0** |
| source files not yet frozen | **0** |
| frozen files gone from source | **0** |

Independently re-verified with `--verify --full-hash` (545.8 s, every file re-hashed on both
sides): **12,302 records, 0 missing, 0 wrong-size, 0 wrong-hash, and `source_drifted_since_freeze`
= 0.** The last figure is the one that matters for O16 — the store did not move under the copy, so
the freeze is a coherent snapshot of a single instant rather than a smear across one.

The manifest (`manifest.jsonl`, one fsynced line per file carrying both hashes) and
`FREEZE_SUMMARY.json` are mirrored to `data/deep_harvest/` on the laptop, per the second-copy
rule. **The payload stays on D: and is never committed.**

### TIER 0 EXTENDED TO THE RAW PULL (2026-08-18)

`D:\thetadata\freeze_rawpull_2026-08-18` — the harvested tree (`D:\thetadata\chains`,
Tiers A, B and C together).

| | |
|---|---|
| units frozen | **1,865 of 1,865** |
| bytes | **12.44 GB** |
| hash mismatches at copy | **0** |
| `--verify --full-hash` | **1,865 records, 0 missing, 0 wrong-size, 0 wrong-hash** |
| `source_drifted_since_freeze` | **0** |

### EXTENDED AND BOTH RE-VERIFIED, 2026-08-18 (the close-out)

The raw-pull freeze was extended over Tiers D and E — **985 new units, +5.25 GB** — appended to
the same manifest rather than given a new dated root, because `freeze_chain_store` is append-only
(no existing record is rewritten) and **one manifest per source tree is what makes `--verify`
meaningful**: `summarise` reports `n_source_files_not_yet_frozen`, which two split roots would
each compute wrongly about the other. The folder's date is the freeze's *inception*; every record
carries its own UTC stamp.

| | raw pull `freeze_rawpull_2026-08-18` | chain store `freeze_options_2026-08-17` |
|---|---|---|
| records | **2,850** | **12,302** |
| bytes | **17.69 GB** | 26.98 GB |
| hash mismatches at copy | **0** | 0 |
| source files not yet frozen | **0** | 0 |
| frozen files gone from source | **0** | 0 |
| `--verify --full-hash` missing / wrong-size / wrong-hash | **0 / 0 / 0** | **0 / 0 / 0** |
| **source drift since freeze** | **0** | **0** |

**The 2026-08-17 chain-store freeze was re-hashed too, although nothing this session touched
it.** *"We did not touch it"* is a claim; re-hashing is the check — and `data/options` is a live
mutable store that other lanes write to, so source drift is the failure this harvest is actually
exposed to. 12,302 files, 607 s, zero drift.

**Deliberately a SIBLING tree rather than an extension of the existing manifest.** Folding the
new units into `freeze_options_2026-08-17` would have meant re-keying a manifest whose 12,302
records were already `--full-hash` verified — rewriting a provenance record to add to it is the
exact mutation Tier 0 exists to prevent. Two dated, independently verified manifests carry the
same guarantee and risk nothing already banked. They are also **different objects and should
stay separable**: one is a snapshot of a mutable live store, the other is raw vendor output.

---

## The overlap comparison — brief rule 3

Pulling 0–1200 DTE re-covers the 0–90 or 0–200 band the existing cache already holds, so **every
unit carries its own control** and overlap is free rather than wasted.

**Result, and it is exact.** AAPL-2018:

| | |
|---|---|
| cached rows | 203,778 |
| new rows | 384,590 |
| **shared keys** | **203,778 — every cached key is present in the new pull** |
| bid / ask / volume mismatches | **0** (max abs diff 0.000 on all three) |
| agreement | **1.000000** |

**No disagreement was ever seen: 13 of 13 completed units verdict `agree`.** Counts are carried in
`DEEP_HARVEST_SUMMARY.json` under `overlap_verdicts`; a single `DISAGREE` stops the run and is
logged in full with up to five example rows per column.

This is a real test rather than a formality — 200k+ shared keys per megacap symbol-year, on data
pulled years after the original mining, so a vendor revision of history would surface immediately.
**It is also the strongest evidence for the census result**: the vendor's 2016–2018 history and
the cache agree bit-for-bit on every shared key, so what is on disk is what a re-pull would return.

Two things deliberately not counted as disagreement, both by construction: the cached frame is
slim-filtered (`mine_options_cache.slim_filter`) so it legitimately holds **fewer** keys — only the
intersection is compared; and the cached frame is float32 where the raw arrives float64, so floats
are compared at 1e-3.

**TIER E IS THE FIRST TIER WHERE *EVERY* UNIT CARRIES A BASELINE**, because it is defined as the
symbol-years that already hold a shallow unit. Tier C had none by construction (982 of its units
returned `no_baseline`), so this is the widest overlap test the harvest has run.

**And it verifies Tier E's own premise per unit, which was checked BEFORE committing twelve more
hours to it rather than assumed:**

| unit | cached rows | new rows | × | cached max DTE | new max DTE | new rows >200 DTE |
|---|---|---|---|---|---|---|
| AA-2016 | 119,764 | 131,228 | 1.10 | **200** | 858 | 11,464 |
| ABBV-2016 | 155,080 | 203,316 | 1.31 | **88** | 823 | 28,320 |
| ADI-2016 | 24,913 | 65,892 | **2.64** | **88** | 795 | 23,824 |
| ADM-2018 | 88,892 | 132,050 | 1.49 | **88** | 851 | 21,476 |

**The cached units cap at exactly 88 or 200 DTE — the shallow bounds — and the deep pull reaches
795–858.** The premise holds. **But read the multiple, not the headline:** rows rise only
1.10–2.64×, because long-dated contracts are far fewer than short-dated ones. The quantity worth
quoting is the **11k–31k rows per unit beyond 200 DTE**, which exist in no other store. Units
cached at 88 DTE gain proportionally most, which is the expected direction and a small check that
the numbers mean what they say.

---

## The resume test I actually ran

A real hard kill, invariants checked on both sides — not an assumption.

1. **Before:** manifest 6 lines, 4 payloads, 0 stray `.tmp`.
2. Launched on 6 units, `--workers 1`, ran **50 seconds** — well inside a unit (30–140 s).
3. **`taskkill /PID <pid> /T /F`** — no signal, no cleanup, whole process tree.
4. **After:** manifest still 6 lines (**no torn line**), payloads still 4 (**no half-written
   file**), **0 stray `.tmp`**, process gone.
5. **Restarted.** Scope line **identical** before and after — `done {'A': 4}, to pull 6` — so the
   killed unit was correctly **not** counted done and the four complete ones were skipped.
6. **`--verify --full-hash`: 10 of 10 records re-hashed to their recorded sha256**, zero missing,
   zero wrong-size, zero wrong-hash.

The ordering that makes this safe: **the payload is written and `os.replace`d BEFORE its manifest
line is appended**, and that line is `fsync`ed. A kill can lose a unit's *record* (it re-pulls,
costing one unit) but can never record a unit complete when its bytes are absent or partial.

**The freeze tool was resume-tested separately and independently:** smoke run of 40 files → 0 hash
mismatches; `--verify --full-hash` → 40 records, 0 missing / 0 wrong-size / 0 wrong-hash / 0 source
drift; restarting advanced 40 → 45 without re-copying the first 40.

---

## TIER C — COMPLETE. The only perishable tier, and it is now banked.

Run 2026-08-18, `--workers 1`, `max_dte=1200`, 1,260 units for the 420 never-tried optionable
names. The 75 known-empty names were **skipped with a recorded reason and never re-probed**
(`D:\thetadata\tier_c_skipped.json`).

| outcome | units | |
|---|---|---|
| **`ok`** — full year | **958** | |
| **`ok_partial`** — listed mid-year, quarters labelled | **24** | |
| **`empty_vendor`** — terminal, vendor has nothing | **278** | pre-listing names |
| **`failed`** | **0** | |
| **total** | **1,260** | |

**982 units carry data, 50.6 M rows, 2.53 GB, in 6.39 h.** The hit rate is **76.0%**, against
the **~75%** the 14-name probe predicted before the run — the one projection here that held.

**TWO PROJECTIONS THAT DID NOT HOLD, stated because a projection quoted once should be scored:**
size came in at **2.53 GB against ~11 GB projected** (4.4× low) and time at **6.39 h against
~4.7 h** (1.4× high). Both have the same cause: the three names I sized on (PKG, MOD, AFG) are
liquid mid-caps at ~8.8 MB per symbol-year, while the Tier C population averages **2.6 MB** —
thinner chains, and more of them empty. **A three-name sample was too small to characterise a
420-name population, and it was wrong in both directions at once.**

### Ticker reuse: measured, not resolved

**28 of 982 units (2.9%), across 14 symbols, carry option data for a year BEFORE the panel knew
the ticker.** Every one is stamped `pre_panel_history: true` with its `panel_first_year`.

| symbol | flagged years | panel debut | what it is |
|---|---|---|---|
| FOXA | 2016, 2017, 2018 | 2019 | 21st Century Fox → Fox Corp |
| IR | 2016 | 2017 | Ingersoll Rand ticker reuse |
| VG | 2017, 2018 | 2025 | Vonage → Venture Global |
| CR | 2017, 2018 | 2023 | Crane |
| AZPN | 2017, 2018 | 2022 | Aspen Technology |

**These rows are real option data for whoever held the symbol at the time — they are simply not
the company the panel means.** The pull was not gated on this, deliberately: gating would have
spent the deadline, and the bytes are unreachable after 2026-09-01 while the adjudication is not.
**What was bought is detectability.** Any analysis touching Tier C must filter on
`pre_panel_history` or resolve the 14 symbols against a point-in-time identifier; **treating
these units as the modern company is a live way to get a wrong answer.**

---

## TIER E — the tenor axis, 2016–2018. COMPLETE, and it was the last perishable thing.

**836 of 836 units, 331 symbols, 0 failed.** 788 `ok`, 30 `ok_partial`, 18 `empty_vendor`.
**83,691,315 rows / 4.19 GB**, spread 278 / 266 / 292 across 2016 / 2017 / 2018.

**What it actually bought: 14,278,981 rows beyond 200 DTE, reaching a maximum observed 858 DTE.**
Those rows are in no other store — the shallow cache stops dead at 88 or 200 by construction.

**THE CONTROL IS THE WIDEST THIS HARVEST HAS RUN, AND IT IS CLEAN: 818 of 818 units with a
baseline came back `agree`, ZERO disagreements**, zero bid/ask/volume mismatches. Tier E is
defined as the symbol-years that already hold a shallow unit, so **every** unit carries a
control — where Tier C had none at all (982 `no_baseline`). The vendor's 2016–2018 history and
the cache agree on every shared key, years after the original mining.

**BUG 8 did not recur: 0 units have an empty quarter.** All 30 `ok_partial` come from a *failed*
quarter (BUG 7's class, correctly labelled), not a silently-dropped empty one.

### The sizing method was the point, and it can now be scored

| method | projected | actual | error |
|---|---|---|---|
| Tier C — **3-name sample** | 11.1 GB | 2.53 GB | **+339%** |
| Tier E — **393-pair, median ratio** | 4.5 GB | **4.19 GB** | **+7.4%** |
| Tier E — 393-pair, mean ratio | 5.1 GB | 4.19 GB | +21.7% |
| Tier E — 393-pair, p90 (upper bound) | 8.0 GB | 4.19 GB | +90.9% |

**Pairing cut the sizing error from 339% to 7.4% — a 46× improvement** — and the **median** ratio
beat the mean, the expected direction for a right-skewed size distribution and a reason to quote
the median next time.

**The axis I did NOT pair was wrong by 34%: 5.2 h projected against 7.8 h actual** (33.7 s/unit
against 22.6 s projected). The time estimate reused the old population mean, which was dominated
by Tier C's small caps, while Tier E is the *liquid* names by construction — they have shallow
units precisely because they were worth mining for breadth. **I fixed the methodology on one
quantity and left the other on the method that had already failed once.** An early reading of
52 s/unit made it look worse still (~13 h); that was the alphabetically-first megacaps (AA, AAL,
ABBV) and the rate settled to 33.7 s once past them — **so a rate measured on the first units of
an alphabetical queue is itself a biased sample.**

**Interrupted twice and resumed cleanly both times**, which is the resume guarantee doing its
job on an unplanned event rather than a rehearsed one: **zero orphaned payloads**, nothing
re-pulled, no unit lost. The second relaunch went out **detached** (`Start-Process`) so the
harvest no longer shares a lifetime with the agent session that started it.

---

## TIER D — the Index's 86 names, 2025–26. COMPLETE.

**169 units over all 86 Index names, 0 failed.** 81 `ok` (2025), 86 `ok_partial` (2026, see
BUG 9), 2 `empty_vendor`. **21,351,202 rows / 1.07 GB**, of which **5,606,010 beyond 200 DTE**.

**The six names with no cache dir at all are now five with full chains and one that does not
exist:**

| name | 2025 | 2026 |
|---|---|---|
| AGX | 250 days, 96,872 rows | 156 days, 111,464 rows |
| FORM | 250 days, 28,918 | 156 days, 39,242 |
| POWL | 250 days, 97,408 | 156 days, 111,834 |
| VIAV | 250 days, 41,922 | 156 days, 88,698 |
| VICR | 250 days, 34,756 | 156 days, 90,028 |
| **IX** | **`empty_vendor`** | **`empty_vendor`** |

**IX is the only unreachable name in Tier D** — ORIX Corp, an ADR the feed carries no options
for. Not a gap in the harvest; a fact about the instrument.

**Scoped at `max_dte=1200`, not the 60–90 DTE band that was asked for**, and the reason is
arithmetic rather than preference: 1200 is a strict SUPERSET of the band, the whole tier cost
**1.07 GB against 378 GB free**, and a narrower band would have bought a **second unit namespace
for the same symbol-years** — one that could not be resumed alongside, compared with, or frozen
with the 2,850 units already banked at 1200. The band is a filter to apply when the data is
read; it is not worth a fork in the store.

**Overlap: 42 `agree`, 125 `no_baseline`, ZERO disagreements.** The high no-baseline count is
expected and is the point of the tier — these are recent years for names the breadth miner never
covered.

**NOT PERISHABLE, and it ran anyway because the window was already paid for.** 2025–26 sits well
inside Standard's rolling 8-year window and would have been reachable after 2026-09-01.

---

## Queue and per-tier completion

| tier | scope | symbol-years | status |
|---|---|---|---|
| **0** | freeze `data/options` → `D:\thetadata\freeze_options_2026-08-17` | 12,302 files / 26.98 GB | **DONE — verified, 0 mismatches, 0 drift** |
| **A** | alert symbol-years 2016–2018 | 400 | **CANCELLED — 99.97–100% already cached** |
| **B** | alert symbol-years 2019–2025 | 961 | **CANCELLED — cached, and not perishable** |
| **C** | 2016–18 for the 420 never-tried optionable names | **1,260** | **DONE — 982 with data, 278 terminal-empty, 0 failed; frozen + verified** |
| **D** | Index 86 names, recent years | ~41 | **DEFERRED past 2026-09-01 (Standard reaches it)** |

### Daily progress

| date | job | units done / total | GB | rate | projected finish |
|---|---|---|---|---|---|
| 2026-08-16 | deep chains (A) | 13 / 1,361 | 0.15 | 52.2 s/unit | *void — see BUG 3* |
| 2026-08-17 | **census** | 1,361 / 1,361 units read | — | 433 s total | **complete** |
| 2026-08-17 | **Tier 0 freeze** | **12,302 / 12,302 files** | **26.98** | 14–20 MB/s | **DONE + verified** |
| 2026-08-18 | **Tier C harvest** | **1,260 / 1,260 units** | **2.53** | 197 units/h | **DONE — 0 failed** |
| 2026-08-18 | **raw-pull freeze** | **1,865 / 1,865 units** | **12.44** | — | **DONE + verified, 0 drift** |
| 2026-08-18 | **BUG 8 repair + relabel** | 43 re-probed / 29 relabelled | 0 | — | **DONE — 0 improved, nothing recoverable** |
| 2026-08-18 | **Tier E (tenor depth)** | **836 / 836 units** | **4.19** | 107 units/h | **DONE — 0 failed, 818/818 overlap agree** |
| 2026-08-18 | **Tier D (Index 86)** | **169 / 169 units** | **1.07** | 108 units/h | **DONE — 0 failed** |
| 2026-08-18 | **freeze extension** | **2,850 / 2,850 units** | **17.69** | 19 MB/s | **DONE + `--full-hash` verified** |

**The 2026-08-16 projection of "~20 h / ~16 GB" is VOID** — it extrapolated from 13 units, and the
process then stalled for twelve hours without writing a fourteenth (BUG 3). It is left in the table
rather than deleted because a projection that was quoted once should stay visible after it fails.

---

## BUGS FOUND

**1. `theta_bulk` concurrency is unsafe for deep pulls — reported, not fixed (lane rule).**
At `--workers 2`, two of the first three symbol-years lost whole quarters to gRPC
`_MultiThreadedRendezvous` (AAPL-2016 lost Q1+Q4, AAPL-2017 lost Q2). Serially, all three
succeeded first try. Matches the O14 tick lane: ThetaData **serialises the account**, so per-call
latency scales with workers while throughput stays flat. `mine_options_cache.py` uses `WORKERS = 4`
because Standard *permits* 4 concurrent requests — permitted is not useful. This harvester runs
`--workers 1`.

**2. A failed quarter is silently a short year.** `_fetch_span` returns what it has, so a
symbol-year assembled from three good quarters and one failure looks like a complete year on disk.
This harvester treats **any** failed quarter as a failed **unit** (no payload, `status: failed`,
re-pulled next run). Flagged because the same shape exists in the breadth miner.

**3. The RPC deadline does not cover client construction — REAL, but NOT what cost twelve
hours. See BUG 5; this entry is corrected below.** `theta_bulk._call_with_timeout` bounds the
*call*, but callers write `tb._call_with_timeout(tb._cli().option_history_eod, ...)` — and
`tb._cli()` is evaluated as an **argument**, so it runs **outside** the deadline. On a fault the
recovery path sets `tb._client = None`, and the next `_cli()` then connects **unbounded**. That
is a genuine latent hang and it is fixed in this lane's script by submitting a closure. It is
**not** the cause of the 2026-08-17 twelve-hour episode, which I originally attributed to it.

*Fixed in my own scripts* by submitting a closure so construction is inside the deadline:

```python
def call():
    return tb._cli().option_history_eod(...)   # construction INSIDE the bound
bounded(call, timeout=120)
```

**Not fixed in `valuation/edge/theta_bulk.py` — that is the options-bot lane's file** (lane rule:
report, don't fix). Any lane calling `_call_with_timeout(tb._cli().x, ...)` has the same hang.

**5. THE TWELVE HOURS, CORRECTLY DIAGNOSED — AND THE FIRST DIAGNOSIS IN THIS FILE WAS WRONG.**
I reported the 2026-08-17 episode as a hang caused by BUG 3. **It was not a hang at all. The run
was pulling the whole time; what died was the loop that writes checkpoints.**

The evidence is not interpretable any other way: **883 payloads were written between 03:00 and
15:00 UTC at 43–94 units/hour**, against **15 manifest records** whose last entry is 03:26:39.
D: fell 436 GB → 398 GB. The process was doing useful work for twelve hours and recording none
of it.

The mechanism is the driver's shape. It was:

```python
with ThreadPoolExecutor(max_workers=workers) as ex:
    futs = {ex.submit(one, u): u for u in todo}      # ~1,350 futures submitted AT ONCE
    for fut in as_completed(futs):
        (tier, sym, year), rec = fut.result()        # <-- re-raises a worker exception
        ...
        append_manifest(root, rec)                   # <-- the only checkpoint
```

One unit raising propagates out of the `for`, and `ThreadPoolExecutor.__exit__` then calls
`shutdown(wait=True)`, which **does not cancel already-submitted futures**. So the worker kept
pulling all ~1,340 remaining units while the only code that writes the manifest was gone. There
is no log line and no traceback until exit, so **from outside it is indistinguishable from a
hang** — which is exactly why I misdiagnosed it.

`ADI-2016` is the unit where it died: it is the only symbol in the alphabetical run order with
**no payload** while later symbols (ADP, AEM, …) have theirs. **The precise exception is
unrecovered and I am not going to invent one** — the process was killed, so its stderr never
flushed. The *mechanism* above is established by the timeline regardless of which exception
started it.

**Fixed three ways:** every `fut.result()` is wrapped so one unit's exception is recorded as a
failed unit and can never stop the others being checkpointed; the executor is shut down with
`cancel_futures=True` so a stopped run cannot keep pulling in the background; and a new
`--adopt-orphans` mode re-checkpoints payloads that already exist on disk.

**The 883 orphans were recovered rather than re-pulled — 870 adopted, 0 skipped, 9.90 GB.**
Adoption is deliberately conservative: a payload is adopted only if it unpickles, carries this
miner's schema, and its **embedded** symbol/year match its own path, and adopted records are
stamped `adopted_from_disk: true` so they are never confused with a live checkpoint. Re-pulling
them would have cost roughly twelve hours of a fifteen-day window to re-fetch bytes already
paid for. **Tier A stands at 393 of 400 as a result** — the lost twelve hours were not lost.

**6. A no-data name and a broken pull shared one status.** `pull_unit` returned `failed` when
any quarter errored, so a name that simply did not exist yet (ABVX listed 2024; its 2016–2018 is
empty by construction) was marked retryable and would be re-probed on **every** restart. With
Tier C roughly a quarter pre-listing names, that is ~315 units of an irreplaceable window spent
re-confirming negatives. Four quarters of `NoDataFoundError` now record **`empty_vendor`**, which
`needs_pull` treats as terminal — mirroring the breadth cache's own `.pkl.empty` convention.

**7. A mid-year listing threw away the quarters that DID have data.** `pull_unit` returned
`failed` if *any* quarter errored, discarding the frames already fetched. For a name that listed
inside the window that is systematic: ARGX 2018 has no Q1/Q2 because it listed mid-2018, EQH 2018
no Q1 (May IPO), CCEP 2018 only Q4. **Tier C is precisely the late-listing population, so the
defect was aimed squarely at its own target** — it cost 26 units on the first pass, every one of
them a name whose listing falls inside 2016–2018. A partial year is now kept and **labelled**
(`status: ok_partial`, `quarters_missing: [...]`) so a short year can never be silently mistaken
for a complete one; a *real* fault on a quarter still refuses the whole unit. Re-running the 26
recovered **24 partial years and left 0 failed**.

**8. A quarter that returned ZERO ROWS was dropped in silence, so a short year was banked as
`ok`.** BUG 7's sibling, and the one it did not cover: 7 handles a quarter that *errored*, this
one a quarter that returned successfully with nothing in it. The empty frame was skipped by
`if r is not None and len(r)` and never recorded, so the unit reported `status: ok` — meaning a
complete year — while holding as little as 65% of one. **Measured across the finished harvest:
19 units carry `ok` while under 95% of their year's date count**, LLY / LMT / LOW / MA appearing
repeatedly and at identical counts (164 dates in 2019, 208 in 2020, 231 in 2022).

* **The label is now correct in code and on disk.** An empty quarter is recorded in
  `quarters_empty` and forces `ok_partial`. Existing records were corrected by an **offline**
  `--relabel` pass, which derives the empty quarters from the banked payload itself and so needs
  no vendor call: **29 units corrected, 14 already correct, 0 unreadable**, idempotent on a
  second run (0 further changes).
* **`--repair` re-pulled all 43 short units and recovered NOTHING: 0 improved, 43 confirmed
  short.** The vendor genuinely serves no more. The rule that makes that safe to run unattended
  is that **a repair may never shrink a unit** — the re-pull is written only if it holds strictly
  more dates, and otherwise the original is restored byte-for-byte from a `.prerepair` copy. 0
  safety copies were left behind. Pinned by `tests/test_deep_harvest.py`.
* **REPORTED BECAUSE I GOT IT WRONG MID-INVESTIGATION AND THE ERROR IS INSTRUCTIVE:** I probed
  Nov–Dec for these units, found the feed serving those months, and concluded ~15 units of
  recoverable data were sitting behind a bad label. **The short units are short at the START of
  the year, not the end** — PEN-2016 begins 2016-03-31, LLY-2020 begins 2020-03-09, WELL-2018
  begins 2018-02-28 — so the probe tested a span that was never missing. The full-year re-pull
  refuted it. **The defect was real and the recoverable data was not.**
* **What it cost: nothing in bytes, and it would have cost a verdict.** No data was lost. But
  `ok` meaning "complete" is exactly the kind of claim an analysis leans on without checking, and
  19 units silently missing a quarter is the shape of a bug that surfaces as a strange result
  months later. Same family as the five silently-empty factors in `CLAUDE.md`'s coverage rule.

**9. THE CURRENT YEAR IS NOT A WHOLE YEAR, and the miner kept asking for the rest of it.**
Third member of the same family, found on Tier D's first two units. Pulling 2026 on 2026-08-18
requests Q3 (half unwritten) and Q4 (entirely in the future): ACGL-2026 and AEIS-2026 both came
back **`failed`** — Q4 `NoDataFoundError`, Q3 `_MultiThreadedRendezvous`.

* **`failed` is the damaging part, and BUG 7's repair does not catch it**, because `nodata_only`
  is False when one of the errors is a gRPC fault rather than `NoDataFound`. So the whole unit
  was refused — **discarding seven and a half months of 2026 the vendor serves perfectly well**,
  and marking it retryable so it would be re-probed on every restart forever. **All 86 of
  Tier D's 2026 units were on that path.**
* **Fixed by a horizon rather than by another status.** A quarter that has not started is
  **skipped, not requested**; a quarter in progress is requested only up to the last completed
  session. Clamped to **yesterday**, not today, because an EOD bar does not exist until after the
  close. Verified live: the 2026 units now return `ok_partial` with `quarters_future: ["Q4"]`,
  `pulled_through: 2026-08-17` and **156 trading days each**.
* **`quarters_future` is deliberately a THIRD field, not folded into `quarters_missing`.** A year
  short because the calendar has not caught up is not a year short because a request faulted;
  conflating them makes a live year read as damaged in the census and re-pull forever.
* **The family, and why each hid differently.** BUG 7: a year short because the name **listed
  late** — thrown away. BUG 8: a year short because the **vendor stopped** — mislabelled
  complete. BUG 9: a year short because the **calendar has not caught up** — thrown away, by a
  path BUG 7's fix did not cover. All three are the same question — *what does a partial year
  mean?* — and each answered it wrong in a different direction.

**4. Windows `os.replace` races the AV scanner on a freshly written file.** The first full freeze
run died ~3,000 files in with `PermissionError [WinError 32]` on a `.tmp` rename. It is a race, not
corruption. Now retried with backoff, and **raised rather than skipped** if it still will not
land — a skipped file would be a silent hole in a freeze whose entire purpose is completeness.

---

## THE FINAL ALL-TIERS CENSUS — the permanent record of the harvest

*Generated by `python mine_deep_chains.py --census`. **Tracked in the repo as
`HARVEST_CENSUS.json`** — counts and symbol names only, no vendor payload — with copies at
`D:\thetadata\HARVEST_CENSUS.json` and in the `data/deep_harvest/` mirror. After 2026-09-01 this
table is the answer to "what did we get, and what can never be got", so it lives somewhere that
survives the loss of any one drive.*

| tier | ok | ok_partial | empty_vendor | failed | rows | GB | rows >200 DTE |
|---|---|---|---|---|---|---|---|
| **A** — alert 2016–18 | 393 | 0 | 0 | 0 | 69,715,407 | 3.49 | 12,732,656 |
| **B** — alert 2019–25 | 485 | 5 | 0 | 0 | 128,017,028 | 6.40 | 32,868,715 |
| **C** — never-tried names, 2016–18 | 958 | 24 | 278 | 0 | 50,910,785 | 2.55 | 8,054,183 |
| **D** — Index 86 names, 2025–26 | 81 | 86 | 2 | 0 | 21,351,202 | 1.07 | 5,606,010 |
| **E** — tenor depth, 2016–18 | 788 | 30 | 18 | 0 | 83,691,315 | 4.19 | 14,278,981 |
| **TOTAL** | **2,705** | **145** | **298** | **0** | **353,685,737** | **17.69** | **73,540,545** |

**THREE QUANTITIES, DELIBERATELY NOT SUMMED INTO ONE**, because collapsing them is how a fact
about the world gets mistaken for a decision:

* **BANKED — 2,850 units** with a payload on disk. **Zero failed, anywhere, in any tier.**
* **UNREACHABLE — 298 `empty_vendor` units.** The feed has nothing: mostly names that had not
  listed in 2016–18, plus IX, which has no listed options at all. **No future subscription
  recovers these.** Not "not pulled" — *not there*.
* **SKIPPED — 75 names** (Tier C), every one recorded with its reason
  (`known_empty_all_three_years`) in `tier_c_skipped.json`. A choice, and a cheap one: re-probing
  a recorded `.empty` spends an irreplaceable window re-confirming a negative already on disk.

**`ok_partial` is reported beside `ok`, never summed into it.** 145 units are short of a whole
year, and the census says why each is short: **55 from a failed quarter** (BUG 7's class), **29
from an empty one** (BUG 8's), **86 because 2026 is not over** (BUG 9's). A short year reading as
a whole one is the defect this harvest hit three times, so the distinction is structural rather
than editorial.

**THE INTEGRITY CONTROLS, all clean:**

| | |
|---|---|
| overlap `agree` | **873** |
| overlap `DISAGREE` | **0 — the run was never stopped** |
| `no_baseline` (nothing to compare against) | 1,107 |
| adopted from disk after BUG 5 | 870 |
| units relabelled by the offline BUG 8 pass | 29 |
| units a re-pull actually improved | **0 — the vendor served no more** |
| **`pre_panel_history` (ticker reuse) — MUST BE FILTERED** | **45 units, 26 symbols** |

---

## What was NOT pulled, and why

*After 2026-09-01 this section is the permanent record of what is unreachable.*

* **Tiers A and B (1,361 symbol-years of alert holding periods) — DELIBERATELY NOT PULLED.**
  99.90% already on disk with zero missing symbol-years, and the vendor agrees with the cache
  bit-for-bit on 13/13 overlap tests. Pulling them would have spent the entire window re-fetching
  bytes already held. **This is the finding, not a shortfall.**
* **Tier C — PULLED, 2026-08-18.** 982 units with data, 278 terminal-empty, 0 failed. **It was
  the only thing on this page that became permanently unreachable on 2026-09-01, and it is now
  banked and frozen.**
* **The 278 `empty_vendor` Tier C units are unreachable in principle, not merely unpulled.** The
  vendor has no 2016–2018 chains for those names because most of them had not listed yet. That is
  a fact about the world, not a gap in the harvest, and no future subscription recovers it.
* **Tier D — PULLED 2026-08-18, though it did not have to be.** 169 units, 0 failed. It sits
  inside Standard's rolling window and was reachable after the deadline; it ran because the
  window was already paid for. **IX is the one unreachable name** (ORIX, an ADR with no listed
  options) — 2 `empty_vendor` units.
* **Tier E, tenor depth 2016–2018 — PULLED 2026-08-18, and it WAS perishable.** 836 units, 0
  failed, 14.3 M rows beyond 200 DTE. **This file previously recorded it as non-perishable and
  that was wrong** — see the correction in the re-prioritised queue. It was the last thing on
  this page that expires.
* **Tier D's 86 `ok_partial` 2026 units are short BY CALENDAR, not by defect** — each reaches
  2026-08-17 and records `quarters_future: ["Q4"]`. **Re-pulling them after the year ends is
  free on Standard** and is the one item here that improves with time rather than expiring.
* **Tick-resolution data across holding periods.** ~190 GB; fits D:'s 426 GB but nothing else
  would. The existing tick cache (`data/options_ticks/`, 4.72 GB) is **entry-days only** — 3,884
  alert-days, 70.3 M prints.
* **The 42 absent holding-period chain-days — UNREACHABLE, not unpulled.** Measured 2026-08-18
  by probing the feed directly rather than inferring from the cache: MA stops at 2019-08-23 and
  every later request returns `NoDataFoundError`; the three singletons are served on both
  neighbouring days and skipped on the day itself. **No subscription recovers these.** See the
  correction under Q1.
* **Anything beyond ~836 DTE.** The feed stops there (`max_dte=1200` returns a max observed DTE of
  836 on AAPL) — a source limit, not a choice.

---

## TICKER REUSE — WIDER THAN TIER C, AND TIER E'S CASES ARE THE SHARPER ONES

**Measured 2026-08-18 across the whole harvest: 45 banked units over 26 symbols carry option
data for a year before the panel knew the ticker**, each stamped `pre_panel_history` with its
`panel_first_year`. Tier C contributes 28 over 14 symbols; **Tier E adds 17 over 12**, and those
are the ones to worry about, because several are textbook recycles rather than merely late panel
entries:

| symbol | years pulled | panel debut | what the early rows actually are |
|---|---|---|---|
| **SNOW** | 2016, 2017 | 2020 | Snowflake IPO'd Sept 2020. SNOW then was **Intrawest Resorts** |
| **SNDK** | 2016 | 2025 | SanDisk, **acquired by WD in May 2016**; SNDK relisted 2025 as the spinoff |
| **SN** | 2016, 2017, 2018 | 2023 | **Sanchez Energy**; SharkNinja took SN in 2023 |
| DOW | 2016, 2017 | 2019 | the DowDuPont/Dow Inc. restructuring |
| SE, FTI, BTI, AA | 2016–17 | 2017–18 | late panel entry and/or restructuring |
| MDB, MRNA | 2017, 2018 | 2018, 2019 | IPO year — **partly legitimate**, partly not |

**THE DISTINCTION THAT MATTERS AND THAT THE FLAG DOES NOT DRAW: `pre_panel_history` marks a
year the panel did not cover, which is a SUPERSET of genuine reuse.** MRNA-2018 is Moderna for
the part of the year after its December IPO; SNOW-2016 is a different company entirely. The flag
finds both and cannot separate them — that is the adjudication, and it is analysis rather than
collection.

**The full list, for whoever does the adjudication** (`pre_panel_history_symbols` in
`HARVEST_CENSUS.json`): AA, AM, AZPN, BAM, BTI, CR, DOW, EDR, FOXA, FTI, IR, LIN, LINE, MDB,
MRNA, RPRX, SE, SN, SNDK, SNOW, TAK, TLN, TME, TW, VG, ZTO. **Tier D contributes none** — its
years are 2025–26, after every panel debut.

**Nothing was gated on this, deliberately, and the reasoning is the same as Tier C's: the bytes
expire on 2026-09-01 and the adjudication does not.** What the flag buys is that the
contamination is **detectable** rather than invisible. **Any analysis touching Tier C or Tier E
must filter `pre_panel_history` or resolve those 26 symbols against a point-in-time identifier.**

---

## AN INTEGRITY RISK TIER C INHERITS, AND IT IS NOT RESOLVED

**Ticker reuse.** In the Tier C probe, **RPRX returned 1,320 rows for March 2016 — but RPRX listed
in 2020.** Those rows belong to whatever company held the ticker then, not to the panel name.

This is not incidental to Tier C, it is *structural*: Tier C names are precisely those whose panel
membership starts late, which is the population most likely to have inherited a recycled ticker.
A 2016 backfill keyed on today's symbol will silently attribute another company's chains to a
modern name.

**The reuse/alias check must be wired BEFORE the Tier C pull, not after.** A prior scan exists
(`TICKER_REUSE_SCAN.json`) and the cache already carries an `.alias` sidecar convention to build
on. Until that is done, Tier C data should be treated as **suspect for any name whose listing date
postdates its earliest pulled year**.

---

## Recommended next step

1. ~~Tier 0 freeze~~ **DONE and verified** — 12,302 files, 0 mismatches, 0 source drift.
   **O21-D2's referent now exists.** The analysis scripts still read the mutable
   `data/options`; pointing them at the freeze is the options-bot lane's call, not mine.
2. ~~Run Tier C~~ **DONE** — 982 units with data, 0 failed, frozen and `--full-hash` verified.
3. ~~Nothing perishable remains~~ **THAT WAS WRONG WHEN WRITTEN, AND THE MOP-UP FIXED IT.**
   Tenor depth (Tier E) *was* perishable — 2016 through mid-2018 leaves Standard's rolling
   window when Pro lapses. It has now been pulled. **The MA gap was not closeable at all.**
4. ~~Tier D~~ **DONE 2026-08-18** — 169 units, all 86 Index names, 0 failed. Five of the six
   names with no cache dir now hold full chains; IX has no listed options.
5. ~~Tier E, tenor depth~~ **DONE 2026-08-18** — 836 units, 0 failed, 14.3 M rows beyond 200 DTE.

### THE HARVEST IS CLOSED. What is left is analysis, and none of it expires.

1. **ADJUDICATE THE 26 REUSE SYMBOLS BEFORE ANY 2016–2018 DATA IS USED.** The precondition, and
   the only one. `pre_panel_history` makes contamination *detectable*; it does not resolve it,
   and it over-flags (a December IPO year is marked the same as a wholesale ticker recycle).
   Analysis, not collection, and it has no deadline — but nothing built on Tier C or Tier E is
   quotable until it is done.
2. **Point the analysis scripts at a freeze.** `o3_o4_o5_surface.py`, `o6_o7_o17_earnings.py`
   and `o11_o19_o22_o25_portfolio.py` still read the mutable `data/options`, which is the O16
   defect on the store that matters. **Both freezes now exist**; using them is the options-bot
   lane's call, not mine.
3. **Re-pull Tier D's 86 2026 units after the year ends.** Free on Standard, and the one item
   here that gets *better* with time rather than expiring. They record `pulled_through:
   2026-08-17` so the staleness is visible rather than assumed.
4. **The tick axis remains the only large unpulled thing** — ~190 GB for holding-period ticks,
   against a 4.72 GB entry-days-only cache. Not started, not scoped, and not deadline-bound in
   the years that matter.

**THE SUBSCRIPTION CAN NOW LAPSE ON SCHEDULE.** Nothing left on this page requires Pro.

**Zero trials. Nothing here is a research result and nothing here may be quoted as one.**
---

## MB6 — Tier C's 420 small caps: two constraints that go in the register BEFORE it runs

**Recorded here, not in the audit, because this is where a Tier C consumer will actually be
standing.** Zero trials; the equity-side question this population uniquely answers is `MB17`'s and
is not opened here.

The 420 never-tried optionable names hold **982 units with data, 50.6 M rows, 2016–2018** — a
population no options study has ever touched, and the only one that is small-cap. Both constraints
below come from the census, and both are live ways to get a confidently wrong answer.

**1. 28 of 982 units (2.9%), across 14 symbols, carry ANOTHER COMPANY'S option data.** They are
flagged `pre_panel_history`, with `panel_first_year` on every row — FOXA, IR, VG, CR, AZPN and nine
others. A ticker that was reassigned carries the *previous* issuer's chains before
`panel_first_year`, and treating them as the modern company silently mixes two firms into one
series. **The flag must be FILTERED ON, not merely present in the payload.**

**2. 278 units are `empty_vendor`.** A name's absence there is a fact about the **vendor**, not
about the market — reading it as "this name did not trade" is the COVERAGE RULE's own failure mode,
and this record has paid for that class four times.

**AND A CAUTION THAT MUST TRAVEL WITH CONSTRAINT 1, because it is how the filter passes without
doing anything.** Two separate registers have now reported the key **ABSENT** rather than present:
`O21-D2` recorded `pre_panel_history` **VACUOUS rather than PASSING** — absent on all 114 units it
read — and `MB15` reported the same across all 3,884 payloads it read. So a register must **assert
the key is PRESENT on the units it is about to score** before treating a clean filter as evidence
of anything. A filter that finds nothing because the field is missing looks identical to a filter
that finds nothing because the data is clean.

---

# THE I-4 EVENT SPINE — shipped 2026-08-20

**Instrument I-4 of Season 2.** One canonical point-in-time earnings-date table. **Zero trials,
collection-and-provenance class** — it computes no signal, scores no arm, returns no verdict.

`valuation/edge/event_spine.py` · `tests/test_event_spine.py` (16 tests) ·
`scripts/i4_event_spine.py` · artifact `data/free_analysis/I4_EVENT_SPINE.json` (gitignored).

Reproduce: `python -m scripts.i4_event_spine`

## Why one table, and why the test is the deliverable

The project has already paid for two mechanisms describing one named object: **`PT-SPLIT`** was
two recorders disagreeing about what the Valquo Index held, and it shipped an engine figure as an
Index claim. An earnings date is that shape exactly — several lanes need one, each could derive
one plausibly, and **two derivations that drift are indistinguishable from one that is right**
until something downstream disagrees.

So **X-2's census, O-2's 2×2 and every EO follow-on read this table and nothing else.** That is
worth nothing as an intention, which is why the instrument's real deliverable is the agreement
check, run in two independent places:

| check | scope | result |
|---|---|---|
| `tests/test_event_spine.py` — exhaustive synthetic grid | 7 calendars × 3 entries × 5 windows, plus 4 expiries | **agrees on every cell** |
| `scripts/i4_event_spine.py` — the real alert book | 3,870 rows × 3 windows + `owns_the_event` = **15,480 comparisons** | **0 disagreements** |

**Both are needed and they prove different things.** The synthetic grid proves the LOGIC matches
— including which cells are `UNKNOWN`, which a True/False-only test would miss. The real book
proves the DATA feeding it matches. A spine that agreed on invented calendars and disagreed on
the book would pass the first and be useless.

**Disagreements are LISTED, never counted** — the artifact carries the offending
`(row, ticker, fn, window, entry, expiry, spine, shipped)`, because "3 cells differ" is not
actionable and a named row is.

## It reproduces the banked join exactly

The ledger's validation for I-4 is *"reproduces `O6`/`O7`'s banked earnings joins"*. It does,
against `O6_O7_O17_EARNINGS.json` on the same split-clean book:

| | banked (O17) | spine | |
|---|---|---|---|
| zero-coverage names | 29 | **29** | **identical list, zero either way** |
| excluded trades | 388 | **388** | 10.03% of the book |
| `C_5d_avoid` kept / refused | 3045 / 437 | **3045 / 437** | ✓ |
| `C_10d_avoid` kept / refused | 2856 / 626 | **2856 / 626** | ✓ |
| `C_15d_avoid` kept / refused | 2642 / 840 | **2642 / 840** | ✓ |
| `C4_own_the_event` owns / not | 1987 / 1495 | **1987 / 1495** | ✓ |

## THE ONE RULE: a missing date is UNKNOWN, never "no announcement"

O17's rule, enforced here structurally rather than by convention:

* `coverage()` returns a **state**, never a bool.
* `dates()` **raises `UnknownCoverage`** for an uncovered name. Deliberately an exception and not
  `[]` — an empty list is precisely what a caller folds into "nothing announced in the window"
  without noticing. A raise cannot be folded into anything. `dates_or_unknown()` returns `None`
  for callers that want the sentinel.
* **`FAIL_CLOSED` names are listed BY NAME in the census, not merely counted**, so a consumer
  drops them deliberately.

**The exposure, measured on both scopes:**

| scope | names | COVERED | PARTIAL | **FAIL_CLOSED** | |
|---|---|---|---|---|---|
| options book | 186 | 157 | 0 | **29 (15.6%)** | **10.0% of trades** |
| equity panel | 2,531 | 2,215 | 10 | **306 (12.1%)** | for X-2 / O-2 |

The 29 are foreign private issuers filing 20-F/6-K rather than 8-K — ASML, AZN, BABA, GSK, NVO,
NVS, RIO, SHEL, TSM, TTE, UL, the Canadian banks. **The panel's 306 is the same mechanism at
scale** and is dominated by ADR tickers (ABBNY, ALLGF, ARVLF, ASAIY) and FPIs. A filter reading
"no date" as "safe" fails open on a systematically non-random tenth of the book, and the failure
is invisible because those rows look like passes.

**Four coverage states, not two.** `COVERED` (≥3 dates in the year) · `PARTIAL` (1–2: real
coverage, demonstrably incomplete) · `GAP` (the name has coverage elsewhere, none this year) ·
`FAIL_CLOSED` (none anywhere). Code 22 runs **~2.83 per ticker-year against a quarterly 4**, so
rounding `PARTIAL` up to `COVERED` is how a hole in a calendar becomes an implied "no
announcement". The `EXPECTED_MIN = 3` line is recorded, not tuned — no arm selects on it.

## Provenance, so nobody re-derives what is settled

* **Code 22 = "Results of Operations and Financial Condition"**, the 8-K item an earnings release
  is filed under. Decoded EMPIRICALLY in `bulk.py` (2026-08-01) by timing-vs-filing and by
  information content, then **CONFIRMED against the published legend** that `S17`'s correction
  retrieved from `SHARADAR/INDICATORS?table=EVENTCODES` and transcribed into
  `SHARADAR_REFERENCE.md` §2. **It is no longer an inference.** 385,896 occurrences, 10,149
  tickers, 2004-08-23 .. 2026-07-31.
* **`bulk.py`'s decode is REUSED, not reimplemented.** The spine calls `prepare_events` and
  `earnings_dates`; it never re-parses the CSV and never keeps its own `EARNINGS_CODES`. Pinned
  by a test that checks the module NAMESPACE and its AST assignments — not its text, because the
  docstring legitimately says the words while explaining that it keeps no copy.
* **The spine does NOT import the archived `earnings_surface`.** MA59 quarantines it, and a live
  module importing it would make a closed study reachable from the product. The comparison lives
  in the test and the script — never in the spine. Pinned by parsing the spine's imports.

## THE 34/35 SUNSET — recorded so nobody reads it as a signal

From the legend's own first/last-seen columns: **Schedule 13G (code 34) stops 2024-12-17** and
**Schedule 13D (code 35) stops 2025-05-16**. Every other `S17` arm code runs to 2026-07-31.

**A code that stops being emitted is era-concentrated BY CONSTRUCTION.** It is carried in the
census — attached to the table every event-time consumer reads — specifically so a future study
does not rediscover the cliff in its own data and report it as a finding.

**Its limits travel with it. It touches NO earnings date:** code 22 has no sunset, and this spine
is code 22 only. Whether the sunset drives anything anywhere is **UNMEASURED**.

## A second not-a-signal, found by building the census

**2026 shows 77 PARTIAL against 80 COVERED, and that is the calendar, not decay.** The source
ends 2026-07-31, so the last year is bounded by the extract rather than by data quality — as is
2004, where code 22 begins on 2004-08-23 and 113 of 186 names read PARTIAL.

The census now marks both ends as `source_bounded_years` with the reason. **This is the same
mistake in a different costume as BUG 9 in the chain harvest** — reading a not-yet-complete
period as a damaged one — which cost that harvest seven and a half months of data across 86
names before it was caught. An unmarked cliff at the end of a coverage census is exactly what a
trend-spotting consumer reports. Pinned by a test that also requires an INTERIOR year to be
excused by nothing.

**Interior coverage is healthy and rises as names list:** COVERED 121 (2005) → 157 (2025), GAP
falling 35 → 0 over the same span.

## What this is NOT

Not a full earnings calendar — code 22's ~2.83/ticker-year is partial even for covered names,
which is why coverage is stated per NAME-YEAR. Not a signal, not an arm, not a verdict: **zero
trials, and no figure here may be quoted as a research result.**

---

# S3-I5 — THE TICKER-REUSE ADJUDICATION. Shipped 2026-08-23. THE TIER C/E BLOCK IS LIFTED.

**FIXED-class: facts, not hypotheses. Zero trials.** `valuation/edge/ticker_identity.py` ·
`tests/test_ticker_identity.py` (14) · `scripts/s3i5_ticker_adjudication.py` · table
**`TICKER_REUSE_ADJUDICATION.json` (TRACKED)**.

Reproduce: `python -m scripts.s3i5_ticker_adjudication`

This is the precondition this handoff imposed on itself — *"nothing built on Tier C or Tier E is
quotable until the 26 symbols are adjudicated"* — and the map's *"single most blocking unbuilt
thing in Track B"*. It gates `SC-3`'s Tier-E strata, `B-14`'s long tenors, `B-15` and `B-6e`.

## The verdict, per unit

| verdict | units | meaning |
|---|---|---|
| **REUSED** | **36** | the whole year predates this company on this ticker — another company's data |
| **SPLIT_YEAR** | **7** | the listing date falls *inside* the year — part is this company, part is not |
| **SAME_COMPANY** | **2** | BTI, TAK — the flag was a late PANEL debut, not a change of hands |

**Scope taken from the harvest manifest, not transcribed:** 45 units, 26 symbols. A hand-copied
list goes stale the next time a tier runs.

## THE ANCHOR, AND THE CHECK THAT WOULD HAVE FAILED SILENTLY

The obvious test — *does this ticker map to two `permaticker`s?* — **returns a clean pass on every
one of the 26, including SNOW and SNDK.** `TICKERS` is a CURRENT snapshot: one row per
(ticker, table) for today's holder, so a reused ticker still shows exactly one permaticker. A
check built on it would have reported 26 clean symbols and been wrong about 43 of 45 units.

What the snapshot does carry is **`firstpricedate`** — the day *this* company began trading under
*this* symbol — which is a real point-in-time boundary: **a year entirely before it cannot be this
company.** The three verdicts follow mechanically from where the boundary falls.

**SPLIT_YEAR is why two states are not enough.** Seven units need a *cut date*, not a verdict:

| symbol | year | usable from | what it is |
|---|---|---|---|
| AA | 2016 | **2016-11-01** | Alcoa Corp lists; before that AA is Alcoa Inc |
| ZTO | 2016 | **2016-10-27** | ZTO Express IPO |
| MDB | 2017 | **2017-10-19** | MongoDB IPO |
| SE | 2017 | **2017-10-20** | Sea Ltd IPO (and SE-2016 is REUSED outright) |
| LIN | 2018 | **2018-10-31** | Linde plc post-merger listing |
| MRNA | 2018 | **2018-12-07** | Moderna IPO |
| TME | 2018 | **2018-12-12** | Tencent Music IPO |

Round it down and a year of real data is thrown away; round it up and another company's is
imported. `usable_from()` returns the date so a consumer cuts rather than guesses.

## THREE EVIDENCE STREAMS, AND A CROSS-TABLE CONTROL

Each verdict carries **registry** (`firstpricedate`, `permaticker`, `cusips`), **corporate
action** (`listed` / `tickerchangefrom` / `acquisitionby` from ACTIONS) and **behavioural**
(median-strike step, reusing `ticker_reuse_audit.py`'s discriminator and its 1.5 threshold —
one definition of "a step", not two).

**The cross-table control: ACTIONS' `listed` date equals TICKERS' `firstpricedate` on 25 of 26
symbols.** Two separately-built Sharadar tables agreeing on the exact boundary the whole verdict
turns on is independent confirmation, not a restatement. **The single exception is BTI, which has
no `listed` row at all because it listed in 1986, before ACTIONS coverage begins** — an
explainable absence, and BTI is a `SAME_COMPANY` verdict, so nothing rests on it.

## THE STRIKE TEST IS ONE-SIDED, AND THAT IS THE SUBTLE PART

Three symbols — **DOW (1.24), FTI (1.07), SE (1.03)** — show *no* strike step while the registry
says REUSED. **The disagreements are recorded and change no verdict**, because the two tests ask
different questions:

* A **large** step corroborates a change of hands: SNOW **15.71**, SN **8.33**, SNDK **1.94**.
  Two companies at very different price levels cannot be one continuous underlying.
* A **small** step proves nothing. Unrelated companies routinely trade at similar prices. **SE is
  the clean example: 1.03 across Spectra Energy → Sea Ltd is a coincidence of price level, not
  continuity.**

DOW and FTI are the honest middle — DowDuPont and TechnipFMC are restructurings where a roughly
continuous *business* is re-registered as a new *registrant*, so "same underlying" and "same
company" genuinely differ. **The prior `ticker_reuse_audit.py` independently called DOW
`continuous_underlying` (0.88), so both runs agree on the behaviour and on the registrant — they
are simply not the same fact.** Collapsing them would discard the only signal that a case is
subtle.

## What consumers must do

Read `TICKER_REUSE_ADJUDICATION.json`; do not re-derive. `verdict(ticker, year)` returns
`UNKNOWN` for anything unadjudicated — **never `SAME_COMPANY`** — because a fail-open default
turns an unexamined ticker into an implicit clean bill of health, which is the failure
`pre_panel_history` was invented to catch.

**Found and fixed while building it:** the first data-root resolver probed for the `data/bulk`
*directory*, and a worktree carries a thin one. It selected it happily and every symbol came back
`UNKNOWN` — the right failure *direction*, the wrong *outcome*, and easy to misread as
"adjudicated, nothing conclusive" rather than "pointed at an empty cupboard". It now probes for
the registry FILE and refuses to write an all-UNKNOWN table.

---

# S3-I2 — THE CATALYST CALENDAR, FREE TIER. Shipped 2026-08-23. FORWARD-ONLY.

**Collection-and-provenance, zero trials.** `valuation/edge/catalyst_calendar.py` ·
`tests/test_catalyst_calendar.py` (16) · `scripts/s3i2_catalyst_scrape.py` · store
`data/catalysts/CATALYST_CALENDAR.json` (gitignored, mirrored to `D:\thetadata\catalysts`) ·
**`CATALYST_CALENDAR_SUMMARY.json` (TRACKED)**.

Run: `python -m scripts.s3i2_catalyst_scrape` — safe on a schedule; it appends and never rewrites.

## THE HONEST NOTE, FIRST, BECAUSE IT BOUNDS EVERYTHING

**This table has no history and cannot be given one.** It records what a free surface published
on the day we asked. Snapshots are append-only, every row is stamped with when it was observed,
and nothing is ever rewritten. **The usable record starts at the first snapshot and accrues one
day per day — the earliest honest event-study is roughly a year out, by construction.** The map
said this in advance; it is a property of the instrument, not a shortfall in it.

## First live pull, 2026-08-23

| | |
|---|---|
| rows | **452** over **284 tickers** |
| by type | Readout 327 · PDUFA 82 · Conference 41 · AdComm 2 |
| **day precision** | **124** |
| **IMPRECISE (month or quarter)** | **328** |
| forward + day-precision (the usable set) | **99** |

**FAIL-CLOSED ON PRECISION IS THE BIGGEST TRAP HERE, AND IT IS MEASURED RATHER THAN ASSUMED.**
The source publishes a `date` field for all 452 events, and **328 of them are not dates** —
they are months or quarters. A consumer reading `date` as a day would silently acquire a 328-row
phantom calendar. `usable_date()` returns `None` for anything coarser than a day and **never
rounds to the first of the month** — rounding invents a day the source never published, which is
backfilling from *inference* rather than from memory and is no better for it.

## NEVER BACKFILLED FROM MEMORY — as a code path, not a promise

`add_snapshot()` **raises** on any row whose source has no *successful* fetch record in the same
snapshot. There is no path by which a remembered PDUFA date, a reconstructed Russell schedule, or
a hand-typed correction becomes a row. It raises rather than dropping, because a silently
discarded row makes a partial write look complete. Pinned by three tests.

## The index-reconstitution half: BLOCKED, with evidence

**It does not ship as an empty table, because empty would be a lie.** Probed 2026-08-23:

| surface | result |
|---|---|
| S&P Dow Jones Indices | **HTTP 403 on `/robots.txt` itself** — crawl permission cannot be established, so it was not fetched |
| FTSE Russell | **`/robots.txt` soft-404s to an HTML page** — no robots file to honour, not fetched |
| catalystalert.com | TLS `CERTIFICATE_VERIFY_FAILED` — **not bypassed**; verification is not disabled to make a scrape work |

`STATUS_BLOCKED` means *we did not have permission to look*, which is a different fact from *we
looked and found nothing*, and the four states (`OK` / `EMPTY` / `UNREACHABLE` / `BLOCKED`) are
distinguishable by test. **I did not write a reconstitution calendar from memory**, which would
have been easy and is precisely what the instrument forbids. Re-opening it needs a surface that
grants permission, or a paid feed.

## The source that does work, and its licence

**`https://www.pdufa.bio/api/v1/events`** — robots explicitly `Allow: /api/v1/` while
disallowing `/api/`, so the structured endpoint is the sanctioned one. Its licence is carried in
every artifact: **"Attribution + link-back required. Facts and historical statistics only — not
investment advice."** Attribution: <https://www.pdufa.bio/>.

## Durability — this store cannot be rebuilt

Unlike the chain harvest, which was re-fetchable until a deadline, **a lost catalyst snapshot is
lost permanently**: the free surfaces publish a current calendar and keep no history. `data/` is
gitignored, so the store is **mirrored to `D:\thetadata\catalysts`** and a **tracked provenance
summary** carries the snapshot count, dates, source states and the store's sha256 — counts only,
no vendor rows, so nothing is redistributed. A lost or silently truncated store is then loud
rather than invisible.
