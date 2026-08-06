# HANDOFF — miner re-mine + DTE extension (audit B4 · O15 · the 158 names)

Session 2026-08-05/06. Owner: the data-miner terminal. Prompt: `PROMPT_miner_remine.md`.
Items 1, 2, 3, 4 are **DONE and landed**. Item 5 was **not started**, deliberately.

## Final coverage, measured after everything (the authoritative before/after)

| | before | after |
|---|---|---|
| symbol-years | 3,140 | 3,140 |
| rows | 366,424,776 | **397,072,955** (+30,648,179) |
| rows with KNOWN open interest | 322,959,829 | 352,778,430 |
| **known fraction** | **88.14%** | **88.84%** |
| symbol-years below the 95% floor | 834 | 832 |
| symbol-years with no known OI at all | 2 | 1 |
| names with at least one bad year | 284 | 284 |

**Only two spans were genuinely fixable: AAPL-2020 and FNV-2019. None became worse.** Coverage
moved 88.14% → 88.84%, and most of that is the +30.6M new deep rows (which are 97%+ covered)
rather than repaired old ones. **This is the honest headline of items 1+2: the −1 problem is
overwhelmingly a SOURCE limitation, not a mining bug, and re-mining cannot fix it.**

Depth after item 4: **913 symbol-years at 200 DTE, 2,227 at 90; 100 names fully deep, 0 mixed.**

Landed commits: `18f77db` (B4 writer side), `3c4ceb7` (shard support), `0e393b8` (merge),
`dc2bc5b` (O15). All verified present on `origin/main` by content, not by a green push.

---

## Item 1 — OI coverage audit (B4). DONE.

`oi_coverage_audit.py` → `OI_COVERAGE.json` + `OI_COVERAGE.md`, both committed so the −1
problem can never again be invisible.

| | |
|---|---|
| symbol-years scanned | 3,140 across 482 names |
| rows | 366,424,776 |
| rows with KNOWN open interest | 322,959,829 (**88.14%**) |
| rows with UNKNOWN OI (−1) | 43,464,947 (**11.86%**) |
| symbol-years below the 95% floor | 834 |
| symbol-years with no known OI at all | 2 |
| names with at least one bad year | 284 |

The floor (95%) was pre-committed in `theta_bulk.OI_COVERAGE_FLOOR` **before** the audit ran
(RUN_RULES #6).

**THE AUDIT'S FRAMING OF THIS PROBLEM WAS WRONG, AND THE CORRECTION MATTERS.** The 11.4% figure
in the prompt is right (measured 11.86%, marginally worse), but it is not a mining defect. Split
by year:

| year | known OI |
|---|---|
| 2016 | 47.8% |
| 2017 | 47.5% |
| 2018 | 59.5% |
| 2019–2025 | 97–100% |

**829 of the 834 below-floor spans are pre-2019. Only 5 are 2019 or later.** Verified against the
feed directly rather than inferred: on the same 10-day window AJG returns 504 EOD rows but only
67 OI rows in 2017 (13%), against 1,728 / 864 in 2021. ThetaData's open-interest history is
simply sparse before 2019.

## Item 2 — re-mine the bad-OI spans. DONE.

`oi_remine.py`, worst-first, 3 shards (ThetaData Standard allows 4 concurrent). All **834** spans
attempted. Old data is never discarded until a new pull proves better.

**All 5 modern spans resolved**, measured on disk (not read off a status label — see BUGS):

| span | before | after | verdict |
|---|---|---|---|
| AAPL-2020 | 0.00% | **99.51%** | genuine mining failure, recovered |
| FNV-2019 | 85.58% | **100.00%** | genuine mining failure, recovered |
| KO-2020 | 92.90% | 92.90% | source ceiling, `.oi_degraded` |
| NBIS-2024 | 92.89% | 92.89% | source ceiling, `.oi_degraded` |
| ONC-2024 | 0.00% | 0.00% | 2-row stub, `.oi_nosource`, never retried |

Shard tallies across all 834: **260 improved, 347 no_source, 227 still_failing**. Treat these
LABELS as a lower bound on recovery, not as measurement — the status bug below inflates
`still_failing`. The authoritative post-re-mine figure is the audit rescan (pending, see below).

Spans that did NOT recover are marked on disk and will not be retried forever: `.oi_nosource`
(coverage did not improve and the OI call did not fault → the feed has nothing) and
`.oi_degraded` (coverage below floor, with the fault count recorded so the two causes stay
distinguishable).

## Item 3 — re-screen the 158 wrongly-condemned names. DONE.

Of **166** names ever condemned as "no data" by the probe-fetch bug:

* **99 are now COMPLETE — 11,470,711 rows recovered.**
* 53 are genuinely thin against the liquidity filter (correctly skipped).
* 14 are genuinely empty: BNY, CBRS, CRWV, FER, FISV, HONA, MDLN, MRSH, SKHY, SNDK, SUNB, UI,
  VG, XYZ — all carry `.empty` markers, and all are rename / new-listing cases. **They point at
  an `ALIASES` gap**, the same class as META/FB, not at missing data.

Cache now: **495 manifest entries — 315 complete, 177 skipped_thin, 3 partial**; 482 names hold
pickles.

## Item 4 — extend the DTE ceiling 90 → 200 (O15). RUNNING.

### Cost, measured BEFORE the pull (as required)

Identical spans (March 2023), three names spanning the chain-size range:

| name | rows × | bytes × | wall-clock × |
|---|---|---|---|
| AAPL | 1.30 | 1.30 | 0.96 |
| KO | 1.23 | 1.23 | 1.10 |
| BKNG | 1.19 | 1.19 | 0.90 |

**The prompt's "budget 2-3×" is too pessimistic; the real factor is ~1.2-1.3×, and wall-clock is
flat.** Past 90 DTE there are no weeklies, only monthlies and quarterlies, so the added tenor is
sparse, and the call is dominated by the server-side scan rather than the payload.

* **Disk: not a constraint.** Top-100 names are 6.67GB of the 17.15GB cache → net added
  **1.3-2.0GB** against **267GB free**. A hard floor refuses to start, and stops mid-run, below
  20GB free.
* **Runtime: estimated 7-13h; the early pace is running slower** (see below).

### Which names

Top 100 by **measured** `daily_option_volume` from `cache_manifest.json` (PLTR 313,546/day →
TFC 7,430/day), restricted to `complete` names — deepening a name with gaps buys nothing.
Market cap was NOT used.

### The design decision

Raising `MAX_DTE` alone would have made all 3,140 cached symbol-years look stale, so the next
ordinary `mine.bat` run would have silently re-pulled the whole 17GB cache. So:

* **Deepening is opt-in** — `ThetaBulk(upgrade_depth=True)`, which only `dte_extend.py` passes.
* **Depth is recorded per symbol-year** — a `.dte` sidecar names the ceiling that produced each
  file. Absent = 90, which is recorded history (MAX_DTE was 90 from the first bulk run until
  today), not a guess. `depth_report()` counts them; `cached_dte(sym, year)` reads one.

Without this the cache would be mined at two ceilings with 90-DTE and 200-DTE years
indistinguishable on disk, and a consumer asking for a 150-DTE contract would get data for some
names and silence for others with nothing to explain the difference.

### The band

`BAND["max_dte"]` raised 90 → 200 to track the ceiling, and its test updated with it.
**`TENORS` deliberately stays at (14, 30, 60), pinned against the LEGACY 90.** The deepening is
partial by design — ~100 of ~480 names — so a 180-day tenor would be populated for those and
100% empty for the rest, which is the mostly-empty-column failure the COVERAGE RULE exists to
stop. Widen `TENORS` when `depth_report()` says depth is universal.

**→ FOR THE CORRECTIONS AGENT:** widening the band means any cross-sectional statistic computed
over the 90-200 DTE range compares deep names against names that have no such rows at all. Check
`depth_report()` before ranking on one. A re-derive of the derived layer is your call, not mine.

### Result — DONE

**100/100 names fully at 200 DTE; 913 symbol-years deep.** 981 min (16.4h) for the main pass,
plus a 24 min resume pass.

| | projected before the run | actual |
|---|---|---|
| growth | ×1.19-1.30 | **×1.210** |
| net disk | +1.3-2.0 GB | **+1.40 GB** |
| runtime | 7-13h (revised to ~15h mid-run) | **16.4h** |

The size projection held tightly. **The RUNTIME estimate was wrong and I revised it publicly
mid-run**: it was extrapolated from single-span throughput (900-1700 rows/s), which ignored
per-call overhead and the fact that each span costs TWO calls (EOD + open interest) across ~12
monthly chunks per year. The per-span measurements were right; scaling them up was not.

**ZERO gRPC faults and ZERO channel rebuilds across 16.4 hours.** That is the fix from bug 3
holding under precisely the conditions that burned 455 names in one run before it, and is the
strongest evidence in this session that the miner can now run unattended.

**8 symbol-years across 4 names failed the first pass** (SHOP-2021, MCD-2022/23,
CMG-2020/21/22/23, RTX-2020). Every one kept its original rows and was marked `.missing`
(retryable), never `.exhausted` — the never-destroy guard firing 8 separate times. The resume
pass recovered **all 8 in 24 min**, including CMG's four years, which are the largest in the set
(229→249MB). Those failures were transient, and keeping the shallow frames cost nothing.

---

## Item 5 — breadth (STEP 4 of the follow-up prompt). IN PROGRESS.

Two of the prompt's premises did not survive contact with the data. Both are stated here
because the handoff they came from is the thing that will be read next.

**PREMISE 1, CORRECTED: the 505 manifest-less names are a CONTIGUOUS RANK TAIL, not scattered
channel-death damage.** They occupy universe positions **495–999 by market cap, with no gaps** —
every name at rank 0–494 already carries a verdict. So the prompt's "these are names the miner
already tried, and it is the cheapest coverage available" is only half right: `MINING_PROGRESS.txt`
does still hold `probe failed - will re-probe next run` lines for positions 823–827 from the
channel-death episode, so part of the tail WAS attempted, but positions 371–494 were evidently
re-probed successfully by a later run. Operationally it makes no difference — re-running the miner
probes all of them — but "re-probe the damaged names" and "mine the unmined tail" are not the same
job, and what remains is overwhelmingly the second.

**PREMISE 2, CORRECTED: only 5 of the 14 empty names were an `ALIASES` gap. The other 9 were a
different bug.** Resolved from Sharadar `permaticker` (stable across ticker changes) and then
verified against the feed by probing a 10-day span on each side of the rename, rather than from
recall:

| kind | names | evidence |
|---|---|---|
| genuine rename → alias gap | BNY←BK, FISV←FI, MRSH←MMC, UI←UBNT, XYZ←SQ | predecessor has rows, successor has none, disjoint in time |
| listed after the probe year | CRWV, SNDK, VG, FER (2025) · CBRS, HONA, MDLN, SUNB (2026) | 0 rows in 2024, thousands later |
| genuinely absent from the feed | SKHY | 0 rows in 2024, 2025 AND 2026 |

`UI` is a partial win and is recorded as such: `UBNT` recovers the early years, but **2024 returns
0 rows under BOTH symbols**, so Ubiquiti's recent option history is absent from this feed rather
than mis-keyed. Do not read a future `UI` gap as an alias failure.

### The alias fix, and why the mapping is no longer trusted to be hand-checked

Closing the gap meant reading `ALIASES` closely, which is how bug 7 below was found — one existing
mapping was pointing at a **different, still-live company** and had already written ~1.00M of its
rows into the cache. The lesson generalises: a wrong alias and a right alias are
**indistinguishable at the point of use**, because both return rows. Hand-checking cannot be the
control.

So the control is now structural. A genuine predecessor STOPS trading when the successor starts,
so the two must never both have data for the same year. `alias_overlap_conflicts()` reports any
mapping that violates it, judged on what is actually cached. On the corrected table it returns
`{}`; on the old `WBD -> T` mapping it returns `WBD<-T: [2023, 2024, 2025]` **even after the
contaminated years were purged**, so it would have caught this from the very first WBD pull.
Alias-supplied years now also write a `.alias` provenance sidecar naming the symbol that answered.

### The probe-year fix

`probe = 2024` was hard-coded, so a name that listed later returned an empty probe and was filed
`skipped_thin, reason "no data"` permanently. The probe now walks forward — **2024 still first**,
so every verdict already in the manifest stays comparable — and a name with nothing anywhere in
the 2016–2025 mining range gets its own `no_data_in_range` status instead of being pooled with
names that were measured and found untradeable. Those are opposite facts with opposite correct
responses.

### What the two fixes actually recovered

| fix | recovered into the universe | rejected, on MEASURED grounds |
|---|---|---|
| `ALIASES` gap | BNY, FISV, MRSH, XYZ | UI — 0 rows in 2024 under BOTH `UI` and `UBNT` |
| probe year | **CRWV**, SNDK | VG (18% spread), FER (2 contracts/day), MDLN (8-day chain) |
| `WBD -> DISCA` | re-mined; was present but contaminated | — |

**CRWV is the SECOND most liquid optionable name in the whole cached universe — 266,175
contracts/day, behind only PLTR and ahead of COIN, BABA and HOOD — and it was filed as "no
data".** That single name is the strongest argument that bug 8 was not a bookkeeping nicety.

The three rejections matter as much as the recoveries: they are the liquidity screen working on
real data instead of on a calendar artifact. A fix that made everything pass would be the
suspicious outcome.

**Note the mining range still ends at 2025** (`YEARS = 2016..2025`; 2026 is a partial year and was
deliberately excluded long before this session). So CBRS/HONA/MDLN/SUNB, whose only data is 2026,
correctly stay out — but they are now labelled `no_data_in_range` rather than "thin", which is the
honest label and gives a clean re-entry point once 2026 closes.

## BUGS FOUND (RUN_RULES #3)

1. **B4's stated precondition was not actually met.** The prompt gates this job on B4 having
   landed. It had — but only the CONSUMER side (`_oi_sum` masking, the MIN_OI gate). The WRITER
   in `theta_bulk.py` still filled a faulted OI call with −1 and cached the year as COMPLETE.
   Verified in code on `origin/main` before starting rather than taking the gate at face value.
   Fixed here: `.oi_degraded` sidecar + fault count.
2. **`CACHE_ROOT` was a relative path.** `data/` and `.env` are gitignored and exist only in the
   primary checkout, so running the miner from a worktree mined into a phantom empty directory
   beside the real 16GB cache while the API key silently failed to resolve. Two silent failures
   stacked. Fixed: absolute, anchored on the primary checkout, pinned by a test.
3. **A dead gRPC channel was never rebuilt.** One run pulled 318 names then failed EVERY call
   from queue position 371 to 826 — **455 names burned** — while a fresh process pulled AAPL in
   6.8s. Fixed: sustained consecutive faults rebuild the client.
4. **`prefetch` re-implemented the skip rule** with a bare `os.path.exists`, bypassing everything
   `ensure_year` enforces. Left as-is, the deep re-mine would have skipped every name and
   reported success. Fixed: one `needs_pull()`, pinned by a test.
5. **A SYMBOL-YEAR WAS SILENTLY LOST, AND THE LOSS DISGUISED ITSELF AS AN IMPROVEMENT.**
   `oi_remine` moves the old frame to `.bak_oi` BEFORE re-pulling, so a kill in that window
   leaves the span existing only as the backup. **NXPI-2017 (144,300 rows, 6.8MB) was lost
   exactly that way** when a shard was stopped and restarted mid-session. The nasty part: the
   coverage audit stops counting a span that has no `.pkl`, so NXPI-2017 appeared in the
   before/after diff as one of three spans that had been FIXED — a data loss reading as a
   repair. Caught only because the symbol-year COUNT dropped 3,140 → 3,139 and that one row of
   the diff was chased instead of waved off. Restored in full, and `oi_remine` now sweeps
   orphaned `.bak_oi` files back before it re-mines anything. Pinned by a test. **The genuinely
   fixed count is 2 (AAPL-2020, FNV-2019), not 3.**
6. **`oi_remine.py` reported a stale `before` as the outcome on restore.** When a re-pull faults
   the good frame is correctly restored, but the status was recorded from the audit snapshot
   rather than from the restored file — so AAPL-2020 and FNV-2019 were logged `still_failing`
   while sitting at 99.51% and 100.00% on disk. Fixed: measure the restored frame. **The shard
   tallies above were produced by the buggy version and understate recovery.**
7. **AN ALIAS POINTED AT A DIFFERENT LIVE COMPANY AND SILENTLY CACHED ITS OPTION CHAINS. THE
   WORST BUG IN THIS FILE.** `ALIASES["WBD"] = ["T"]` treated Warner Bros Discovery as the
   continuation of **AT&T**. It is not — WBD continues the DISCOVERY share line; AT&T
   *distributed* WBD shares and went on trading under `T` throughout. Because the fallback fires
   on any empty span, every WBD year before the April 2022 listing fell through to `T`:

   * **WBD 2016–2021 were byte-identical to T** — same row counts, same `(date, expiration,
     strike, right)` keys, same bids. **966,790 rows.**
   * **WBD 2022 Jan/Feb/Mar likewise** (33,964 rows); April is the partial listing month and
     everything from there is real WBD.
   * ≈ **1.00M rows of one company's options filed under another's ticker.**

   Nothing downstream could have noticed: the frames are well-formed, coverage is high, the
   sanity layer has no cross-symbol check, and the strike range (median 38/34/29 in 2016–2021)
   only looks wrong if you happen to know WBD traded near $10–25. Found by reading `ALIASES`
   while closing the gap behind the 14 empty names — **not** by any check that existed.
   Corrected to `WBD -> DISCA` (probed: DISCA 2016–2021 has rows and 2022+ has none; WBD is the
   mirror image — disjoint, as a real rename must be), contaminated years purged and re-mined,
   and the class is now guarded by `alias_overlap_conflicts()` plus a `.alias` provenance
   sidecar. Pinned by three tests.

   **BLAST RADIUS — measured, not assumed. ONE ITEM IS IN ANOTHER LANE AND NEEDS ACTION:**

   | artifact | state |
   |---|---|
   | `data/options/WBD/*` (miner, mine) | **FIXED** — 2016–2022 purged and re-mined under `DISCA` |
   | `data/options_derived/WBD/*` | **CONTAMINATED** — `WBD-2016..2022.pkl` and `WBD-daily.pkl` were derived from the AT&T rows. **→ greeks lane: re-derive WBD.** |
   | `GREEKS_COVERAGE.json` | **CONTAMINATED** — records WBD `rows_in 1,214,932` across 2016–2025, of which ~1.00M are AT&T |
   | `UNIVERSE_RESULTS.json`, `AUTOPSY_BROAD_RESULTS.json` | **CLEAN** — zero occurrences of WBD; no shipped verdict rests on this |

   I did **not** delete the derived files: `data/options_derived/**` is the greeks lane's output,
   not mine, and silently removing another lane's artifacts is its own failure mode. They are
   flagged here and in `HANDOFF_STATUS.md` instead.
8. **The probe year was hard-coded to 2024, which made the universe hostile to anything that
   listed later.** An empty 2024 probe wrote `skipped_thin, reason "no data"` and nothing ever
   revisited it. **Eight of the fourteen names carrying that verdict do have option data** —
   CRWV returns 11,605 rows in a single 10-day 2025 span, alongside SNDK, VG, FER (2025) and
   CBRS, HONA, MDLN, SUNB (2026). The verdict was about the calendar, not the names. Fixed: the
   probe walks forward, bounded, with 2024 still tried first.
9. **"Nothing to judge" and "judged and untradeable" shared one status.** `skipped_thin` was
   recorded both for names measured against the liquidity screen and for names with no data to
   measure — which is what let bug 8 hide, since a 2025 IPO was indistinguishable from a penny
   stock nobody writes options on. Fixed: `no_data_in_range` is its own status.

## What was NOT done

* **Item 5 (breadth mining) not started**, per instruction to stop after item 4.
* **`TENORS` was NOT widened** past the legacy 90 — see the band section for why.
* **The derived layer was NOT re-derived** after the band widened. That is the corrections
  agent's call, not mine.
* **The 832 spans still below the OI floor were NOT re-attempted again.** They are pre-2019 and
  marked; retrying them is burning budget on data the feed does not have.
* **505 universe names have no manifest entry** and need re-probing. That is channel-death damage
  (bug 3), not the 158-name bug, and mining them is item 5 work.
* **The 14 empty names point at an `ALIASES` gap** that was not closed.

## Recommended next step

**Item 5 (breadth mining), and it should re-probe the 505 manifest-less names FIRST** — those are
channel-death damage from bug 3, and the fix for that is now in place and proven over a 16-hour
run, so they should probe cleanly this time. Closing the `ALIASES` gap behind the 14 empty names
is a cheap win to fold into the same pass.

U1 is unblocked on the data side: the 120-180 DTE band now exists for the 100 most liquid names.
