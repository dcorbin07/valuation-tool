# HANDOFF — the ThetaData Pro harvest. Deadline 2026-09-01.

**Lane:** data miner. **Status:** TIER C COMPLETE. Nothing perishable remains.
The queue was stopped and re-prioritised on an exhaustive coverage census; the one tier that
survived it has now been pulled, frozen and verified. **Zero trials — collection is not a test.** No analysis was run and none may be quoted
from this data beyond the integrity checks below.

New files, all mine: `mine_deep_chains.py`, `freeze_chain_store.py`,
`scripts/options_coverage_census.py`, `DEEP_HARVEST_SUMMARY.json`, this handoff.
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
All 42 absent days are **39 of one contiguous MA gap** (2019-08-26 → 2019-09-20) plus three
isolated singletons (DHR 2016-07-05, TMUS 2020-06-25, SONY 2025-09-29).

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
| **C** — 2016–18, 420 never-tried optionable names | **COMPLETE** | Was the only perishable item. 6.39 h, 2.53 GB, 76.0% hit rate |
| **D** — Index 86 names | **DEFERRED past Sep 1** | 2025–26 stays reachable on Standard |
| *depth (the tenor redirect)* | **DEMOTED** | Real absence, but no re-open row is blocked on tenor |

**On my own earlier redirect, plainly:** I found the date axis complete and redirected the harvest
to the **tenor** axis (0–1200 DTE instead of 0–90/200). That absence is real — 90 DTE dominates
every year in the cache — but no item on the re-open list is blocked on it, so it was the wrong
thing to spend an expiring window on. **I fixed the axis and not the question.** It ranks below
Tier C and below the freeze, and only for 2016–2018.

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

**4. Windows `os.replace` races the AV scanner on a freshly written file.** The first full freeze
run died ~3,000 files in with `PermissionError [WinError 32]` on a `.tmp` rename. It is a race, not
corruption. Now retried with backoff, and **raised rather than skipped** if it still will not
land — a skipped file would be a silent hole in a freeze whose entire purpose is completeness.

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
* **Tier D — deferred on purpose.** 2025–26 stays inside Standard's rolling window.
* **Tick-resolution data across holding periods.** ~190 GB; fits D:'s 426 GB but nothing else
  would. The existing tick cache (`data/options_ticks/`, 4.72 GB) is **entry-days only** — 3,884
  alert-days, 70.3 M prints.
* **The 42 absent holding-period chain-days**, of which 39 are one contiguous MA gap
  (2019-08-26 → 2019-09-20). Cheap to close as a targeted re-pull of MA-2019 and three singletons —
  ~4 units, minutes — and **not deadline-bound** (all are 2019+, inside Standard's window).
* **Anything beyond ~836 DTE.** The feed stops there (`max_dte=1200` returns a max observed DTE of
  836 on AAPL) — a source limit, not a choice.

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
3. **NOTHING PERISHABLE REMAINS.** Everything still outstanding sits inside Standard's rolling
   8-year window and is reachable after 2026-09-01:
   * **Tier D** — 6 Index names with no cache dir, 41 lacking a 2025 unit, none with 2026.
   * **The MA-2019 gap** — 39 contiguous days plus three singletons, ~4 units, minutes.
   * **Tenor depth** — real, but no re-open row is blocked on it. 2016–2018 only.
4. **Adjudicate the 14 reuse symbols** before any Tier C data is used. That is analysis, not
   collection, and it has no deadline — but it is a precondition for quoting anything built on
   Tier C.

**Zero trials. Nothing here is a research result and nothing here may be quoted as one.**
