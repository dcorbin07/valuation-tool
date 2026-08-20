# HANDOFF — greeks / GEX derived layer (2026-08-04, GROWN 2026-08-08)

**One line:** every fully-mined name has a cached derived layer in `data/options_derived/` —
**502 names, 254,049,740 of 547,615,761 contract-days priced (46.4%)** across
**1,131,698 name-dates / 4,579 name-years**, with implied vol, the full greek stack through third
order, GEX by strike, zero-gamma, gamma walls, 25-delta skew, ATM-IV term structure, IV rank and
put/call ratios. Zero vendor option calls, zero writes to the miner's cache. **Nothing has been
tested for signal — that is the gated #23, and it was deliberately not started.**

---

## 2026-08-08 — THE LAYER GREW 315 → 502 NAMES. READ THIS BEFORE COMPARING ANY AUTOPSY NUMBER.

Breadth mining finished (502 of 1,000 names `complete`), so the enricher was re-run over the whole
cache. It had last been built when ~100–300 names existed.

| | before (2026-08-04) | **after (2026-08-08)** | change |
|---|---|---|---|
| names enriched | 315 | **502** | **+187 (+59.4%)** |
| contract-days in | 349,038,639 | **547,615,761** | +198,577,122 (+56.9%) |
| contract-days priced | 164,429,685 | **254,049,740** | +89,620,055 (+54.5%) |
| IV-solve rate | 47.11% | **46.39%** | −0.72pp |
| name-dates | 735,226 | **1,131,698** | +396,472 |
| OI `-1` sentinel share | 12.21% | **11.21%** | −1.00pp |
| names carrying ≥1 flag | 304 / 315 (96.5%) | **481 / 502 (95.8%)** | — |
| on disk | 17.8 GB / 3,577 files | **27.5 GB / 5,556 files** | +9.7 GB |

**THE WARNING THIS SECTION EXISTS FOR: any autopsy PBO, feature p-value or Deflated Sharpe
computed after 2026-08-08 is NOT comparable to any figure banked before it, and the difference is
NOT a finding.** `options_autopsy.py` reads the derived layer directly — `<SYM>-daily.pkl` at
`options_autopsy.py:150` and `<SYM>-<YEAR>.pkl` at `:181` — and those feed `build_features` →
the 64-feature gate → `pbo_cscv` and `deflated_sharpe`. This has already bitten once, and the
precedent is recorded in `derived_stamp`'s own docstring (`options_autopsy.py:542-545`): when the
layer went **111 → 317 names mid-audit, the SAME trades under the SAME code reported PBO 48.57%
against the 35.7% recorded eight days earlier, and nothing warned.** The jump just made is of
comparable size. Expect the gate's coverage to rise and the PBO to move; neither is evidence
about the strategy.

**"The autopsies stamp their fingerprint now, so growing the layer is safe" is HALF RIGHT, and
the conclusion does not follow.** The stamp is real and it works — `derived_stamp()` at
`options_autopsy.py:538`, shipped as the `derived_data` key at `:964`, a SHA-1 over sorted
(relative path, byte size) pairs, deliberately size-based rather than mtime-based so an
identical-bytes rewrite compares equal. But all four of these are true at the same time:

- **It gates nothing.** Self-described at `options_autopsy.py:553-555`: "DESCRIPTIVE ONLY. This
  block gates nothing and can fail no run." That is a deliberate and correct choice (RUN_RULES
  A5), but it means the stamp cannot stop a bad comparison — only let a reader notice one.
- **`derived_comparable(a, b)` (`:621`) has no production caller.** It is referenced at its own
  definition and in `tests/test_edge.py` only. No script diffs two result files with it.
- **`UNIVERSE_RESULTS.json` is not stamped at all.** `options_universe.py` contains zero
  references to `derived_stamp` or `options_derived`, yet it ships its own `deflated_sharpe`.
  Only the autopsy block inside `AUTOPSY_BROAD_RESULTS.json` carries the field.
- **No stamped baseline exists yet.** Per `HANDOFF_edge_audit.md`, not one banked autopsy figure
  in this project carries a stamp; the first stamped run becomes the baseline. **That run has
  still not happened, so this paragraph is currently the only record of the discontinuity.**

**Recommended: run one autopsy now purely to bank a stamped baseline**, before any research uses
the layer. It costs one run and it is the only thing that makes the next comparison meaningful.

### What the 413 eligible names actually were — it is NOT 413 new names

Skip-existing is **signature-based, not name-based**: `already_enriched()` compares each source
year-file's `(size, mtime)` (`options_greeks.py:681`). So the work split three ways:

- **187 never derived** — the genuine breadth growth.
- **226 re-derived because their source year-files were REWRITTEN IN PLACE**, not extended.
  1,100 year-files, all rewritten 2026-08-04 → 08-06 (913 grew, 7 shrank, 180 kept an identical
  size with a new mtime). **Zero new years were added to any of these 226 names.** Re-deriving
  them is correct, not waste: GEX consumes `open_interest` directly and that is exactly what the
  OI re-mine changed. The 180 same-size rewrites are probably content-identical and therefore
  genuinely redundant, but proving that costs an unpickle of each and it is 16% of the files.
- **89 unchanged** and skipped.

### Run notes

- **All 502 `complete` names are enriched. None missing.** `ALLY` failed its Sharadar bars fetch
  with a `ReadTimeout` on the first pass and would have been skipped; it recovered on the
  relaunch (361,003 rows priced). Worth knowing that a transient network error on the bars
  prefetch silently costs a whole name — it is reported, but only as one line among 502.
- Ran from the worktree against the main checkout's `data/` via `--data-root`. **The miner's
  cache was verified untouched afterwards** (zero files under `data/options/` modified since
  launch), so the read-only rule held.
- Real Treasury series in use (`2,896 daily observations`), **not** the coarse fallback, so the
  2022 rate problem described under finding 3 does not apply to this build. `rate_sources` is a
  single value across all 502 names.
- Started at 2 workers because another lane was running a 100-draw placebo sweep and the box was
  pegged at 100%; widened to 5 after that finished. **The restart cost nothing** — 413 eligible
  became 260 with 153 banked, exactly the completed count. Killing the tree needs `taskkill /T`
  (a fourth worker was alive that a `Win32_Process` snapshot had missed) and left **zero stray
  `.tmp` files**, which is a live confirmation that `_atomic_pickle` survives a hard kill.

### Flag census at 502 names — these supersede the per-kind counts in the 2026-08-04 section

Nothing new appeared and nothing was silenced; every kind below is one of the five findings
already written up further down, now measured on a layer 59% larger.

| flag kind | 2026-08-04 (of 315) | **2026-08-08 (of 502)** |
|---|---|---|
| `open interest missing (-1 sentinel)` | 297 | **446** (median 10.8% of a name's rows) |
| `gamma walls ... may be an OI artifact` | 170 | **240** |
| `GEX pegged to one strike` | 96 | **160** |
| `zero-gamma not found` | 26 | **88** |
| `rows with expiration before quote date` | 14 | **21** (62 rows in 548 million) |
| `rows had no underlying close` | 1 (`FTI`) | **7** (`AA`, `DOW`, `FIG`, `FTI`, `HUT`, `SN`, `SNDK`) |
| `no open interest at all on N% of dates` | 2 (`AAPL`, `AXON`) | **3** (`AXON`, `KNX`, `NIO`) |

Two of these move in a way worth naming.

**`AAPL` dropped off the no-OI list, and the repair is real but PARTIAL.** The 2020 OI gap
described under finding 1 is gone — 2020 now carries 1,529 missing-OI rows of 309,586 (**0.5%**),
with 2019 and 2021 at exactly **0.0%**. That is the first direct evidence in this file that the OI
re-mine fixed a specific, previously-documented case. **But it did not reach the early years:**
AAPL 2016/2017/2018 still sit at **22.8% / 33.6% / 28.0%** missing OI, and that is where the whole
of AAPL's remaining 9% comes from. Do not read "AAPL's OI gap is fixed" as "AAPL's OI is clean" —
the fix covers 2019 onward. Whether the early years are unrepairable at source (like the `-1`
sentinel) or simply were not re-mined is **not established here** and belongs to the miner lane.

**`zero-gamma not found` more than tripled** (26 → 88), faster than the 59% name growth; the
newly-added names are thinner on average, and a one-sided or sparse book is exactly the condition
that finding produces. Neither threshold was touched.

### The reuse-contaminated names show up here too, from an independent mechanism

The six names confirmed by strike-step in `TICKER_REUSE_AUDIT.json` to hold **two different
companies each** all price far below the 46.4% cache average, and four carry a flag caused
directly by the identity break:

| name | IV-solve rate | flag attributable to the break |
|---|---|---|
| `COR` | **24.2%** | — |
| `SN` | **26.6%** | rows had no underlying close |
| `FIG` | **26.7%** | rows had no underlying close |
| `SNDK` | **29.7%** | rows had no underlying close |
| `AXON` | **34.4%** | no open interest at all on some dates |
| `SNOW` | 45.2% | — |
| `DD` (screened, judged continuous) | 42.3% | — |
| `DOW` (screened, judged continuous) | 38.2% | — |
| `META` (collapsed 2021, no hole) | 46.8% | — |

**Mechanism:** the bars series is fetched for the ticker's CURRENT occupant, so the PREVIOUS
company's option rows find no spot and cannot be priced. `SNDK` is the cleanest illustration —
two year-files spanning 2016–2025, SanDisk having been acquired in 2016 and re-listed in 2025.
**This is corroboration, not proof:** `AA`, `DOW`, `FTI` and `HUT` carry the same flag from
ordinary spinoff/merger histories where the bar series simply starts late. **Do not use these
nine names in any options research until the miner lane ships per-symbol validity windows.**

---

## The 2026-08-04 build (the record below describes the 315-name snapshot)

**The layer is a MOVING TARGET, not a finished artifact.** The miner is still running and still
completing names; this build is a snapshot as of 2026-08-04. Re-running the enricher with no
arguments picks up whatever has finished since — that is the intended way to use it, and the
numbers above will grow.

## What shipped

| file | what it is |
|---|---|
| `valuation/edge/options_greeks.py` | the maths + per-symbol driver (new) |
| `greeks_enrich.py` | resumable unattended runner (new) |
| `tests/test_options_greeks.py` | 22 tests, offline, no data needed (new) |
| `GREEKS_COVERAGE.json` | committed coverage report — the only output that lives in git |
| `data/options_derived/**` | 17.8 GB across 3,577 files; gitignored like the raw cache |

Per name: `<SYM>-<YEAR>.pkl` (one row per priced contract-day, 26 float32 columns),
`<SYM>-daily.pkl` (one row per date — the aggregate surface), `coverage.json`. At the root:
`coverage_manifest.json` and `DERIVED_PROGRESS.txt`.

Re-run `python greeks_enrich.py` any time. It skips names already derived, picks up whatever the
miner has finished since, and re-derives any name that has been re-mined (each source file's size
and mtime is stored).

## Non-interference (the point of the task)

- Zero ThetaData calls. The only network in the whole job is the Sharadar bars fetch and a
  one-time Treasury series, both done ONCE in the parent before any worker starts.
- `data/options/` is opened read-only; everything written goes to `data/options_derived/`.
- A name is touched only when the manifest says `complete`, it is not within the last three lines
  of `MINING_PROGRESS.txt`, and none of its files were written in the last 10 minutes.
- Two workers, each pinned to one BLAS thread. ≈ 45 s per name of wall clock; the 204 names added
  on 2026-08-04 took ~100 minutes, alongside the miner and three other agents.

## Five things found on the way, all real

**1. `open_interest = -1` is a MISSING-DATA SENTINEL, it was being read as a number, and it is
SYSTEMIC — not a handful of bad names.** `theta_bulk` fills an OI merge miss with `.fillna(-1)`.
Across the full 315-name layer that is **42,635,017 rows, 12.2% of the cache, present on ALL 315
names and over the 2% flag threshold on 297 of them, median 12.3% of a name's rows** (worst
HIG 30%, OKE 28%, HPE 27%, CIEN 27%, AMT 27%; cleanest BKR 0.4%, TCOM 0.5%, TT 0.5%).
**Every single row of AAPL 2020 has no open interest at all.** Read as a
number, `-1` flips that contract's sign in the GEX sum and poisons the put/call OI ratio,
silently, while looking like data. It is now NaN, counted per name (`oi_sentinel_rows`), and
every aggregate is computed on known OI only. A date with no known OI gets **blank** GEX / walls
/ zero-gamma, never a confident `0.0` that would read as "dealers are flat". `oi_coverage_iv` on
the daily frame says how much of each date was known.
→ **The earlier version of this note undersold it** as a few bad names, because the flag that
would have shown otherwise was itself broken — see finding 4.
→ **Worth passing to whoever owns the miner:** the same `-1` also flows into
`options_backtest.chain_summary`'s `call_oi`/`put_oi` sums. That file was not touched here. AAPL
2020 may be worth re-mining for OI.

**2. Every option IV this project has ever solved used a coarse fallback rate curve.**
`blackscholes.risk_free_rate` fetches FRED; FRED is unreachable from this machine (connection
reset) and the failure path falls back SILENTLY to a hard-coded schedule — flat 2.0% for all of
2022, a year the 3-month bill went from 0.06% to 4.24%. That is worth roughly 0.5–0.8 vol points
on a 30-day ATM contract at the worst. The runner now primes the identical
`data/bulk/prepared/dgs3mo.csv` from treasury.gov (**2,896 daily observations**, 13-week coupon
equivalent — the same basis as FRED's DGS3MO), so `blackscholes.py` finds the file and never
reaches the network. **`blackscholes.py` itself is unchanged**, and the options backtest inherits
the fix. Every coverage file records which curve priced it (`rate_source`); all 315 names here
read `dgs3mo daily series`.

**3. The cache stops at 90 DTE, so there is no long-tenor term structure.** `theta_bulk.MAX_DTE`
is 90 by design. The first pass emitted `atm_iv_90` and `atm_iv_180` anyway and they came back
99.9% and 100% empty. Tenors are now 14/30/60, `BAND["max_dte"]` is pinned to `theta_bulk.MAX_DTE`
by a test, and a generic guard flags any derived column that is >95% empty.

**4. THE SENTINEL GUARD WAS ITSELF SILENTLY BLIND on 82 of the first 109 names.** `oi_missing_rows` was
counted per YEAR one change before it was summed per NAME, so every name derived in between
carried a name-level `0`. `sanity_flags` reads the name-level number — so it never raised the
sentinel warning on the names with the WORST rates (AZN 24%, AAPL 22%) while dutifully flagging a
freshly-derived name at 3%. The report's *counts* were right the whole time (a fallback summed the
year records); only the *flags* were missing, which is the more dangerous half — a quiet flag list
reads as "checked, fine". Fixed by `options_greeks.repair_coverage()`, which recomputes a stored
record's totals and flags from its own year records and now runs on **every** pass, so a record
written under an older revision of the accounting can never keep reporting stale numbers. Pinned
by `test_repair_coverage_reraises_a_flag_a_stale_record_lost`. **This is the fifth time this
project has shipped a guard that could not see the thing it was guarding** — the four in CLAUDE.md
plus this one. The lesson that generalises: a guard whose input is computed elsewhere needs a test
that feeds it a KNOWN-BAD record, not just a known-good one.

**5. THE SENTINEL MANUFACTURES FAKE GAMMA WALLS — found 2026-08-04, and it is the one finding
here that directly changes how #23 must use this layer.** Chasing why the "GEX pegged to one
strike" flag had spread to 85 names, the thin-chain explanation covered most of them but **18
names with perfectly normal chains were also pegged**. The real driver is finding 1 feeding
forward: when most of a date's open interest is the `-1` sentinel, the GEX sum is carried by
whichever few contracts' OI survived the merge, and that looks exactly like a wall. Measured
across the whole cache **as it stood at 280 names** (the study was not re-run at 315 — the flag
counts below are current, these medians are not), the top strike's share of gamma runs:

| known OI on that date | median top-strike gamma share |
|---|---|
| >95% | 0.309 |
| 75–95% | 0.302 |
| 50–75% | 0.360 |
| 25–50% | 0.380 |
| <25% | **0.545** |

`corr(oi_coverage, wall_concentration)` is **negative on 231 of 280 names** (median −0.207).
So `gex_wall_conc`, and with it `gex_top_strike` / `call_wall` / `put_wall`, is **partly an
artifact of missing data**. A new sanity flag now fires when a name's walls are measurably more
concentrated on its low-coverage dates; it catches **170 of the 315 names**, median gap **0.110**
— twice the 0.05 trigger, and above 0.10 on half of them (worst AXON 0.71, SE 0.52, VST 0.44,
PLD 0.42, STM 0.39). **Read every wall conditional on
`oi_coverage_iv` on the same row.** Deliberately NOT corrected: the repair belongs in the miner's
merge, and this layer cannot invent the missing interest — filling it would be the exact silent
fill the module refuses everywhere else. Pinned by
`test_gamma_walls_built_on_missing_open_interest_are_flagged`, which checks the flag both fires on
a coverage-driven frame and stays quiet when the same concentration is present at full coverage
(real walls do exist).

## Coverage and what got skipped

**47.1%** of raw contract-days produced a valid IV. Every one of the 184,608,954 skipped rows has a
recorded reason, and they sum exactly to the shortfall — nothing is dropped unaccounted:

| reason | rows | share of skipped | why |
|---|---|---|---|
| `no_quote` | 76,804,162 | 41.6% | bid or ask missing/zero — nothing to invert |
| `mny_band` | 43,358,935 | 23.5% | outside 0.70–1.30 moneyness |
| `dte_band` | 30,354,474 | 16.4% | outside 7–90 DTE |
| `wide_spread` | 16,949,237 | 9.2% | spread wider than the mid |
| `below_intrinsic` | 11,993,825 | 6.5% | mid below intrinsic — broken quote, no vol explains it |
| `penny` | 4,975,253 | 2.7% | mid under $0.05 |
| `no_spot` | 150,730 | 0.1% | no underlying close that day (FTI alone is 33,823 of it) |
| `above_max_vol` | 17,246 | — | solved IV above the 5.0 ceiling |
| `crossed` | 5,055 | — | bid above ask |
| `neg_time` | 37 | — | expiration before the quote date |
| `iv_unsolved` | 0 | — | the bisection never failed on a row that reached it |

That 47.1% is not a defect — it is the deliberate refusal to publish an IV where the mid cannot
support one: **81.5% of the skips are an unusable quote or a row outside the moneyness/DTE band**,
and the solver itself failed on zero rows. The names that matter are covered: **735,226 name-dates**, essentially every trading day
of every mined name.

## The flags — investigated, not silenced

**304 of 315 names carry at least one flag**, which sounds alarming and is mostly two systemic
issues, both of them finding 1 wearing different hats. Grouped by kind (the runner prints this
breakdown rather than a bare count, because "one odd name" and "a property of the whole cache"
need to read differently):

- **`open interest missing (-1 sentinel)` — 297 names.** Finding 1. Systemic, median **12.3%**
  of a name's rows. Not a per-name anomaly; a property of the miner's merge. The threshold stays
  at 2% and is deliberately NOT raised to make the run quiet.
- **`gamma walls ... may be an OI artifact` — 170 names.** Finding 5, new on 2026-08-04, and the
  one that changes how the layer must be consumed. Median concentration gap 0.110, i.e. twice the
  trigger — this fires on over half the cache because the defect is on over half the cache, not
  because the threshold is loose.
- **`GEX pegged to one strike` — 96 names.** Two causes, and it is worth separating them.
  Most are **thin chains**: the pegged names price a median of 42 contracts a day against 300 for
  the unpegged, and UBS carries a median of 5 distinct strikes and 16 contracts against AAPL's 37
  and 328 — with 5 strikes, one strike holding most of the gamma is arithmetic. But **18 pegged
  names have normal-thickness chains** (AFL, AZN, CCJ, CSX, DB, FLEX, HIG, HPE, KKR, KMI, NU, OKE,
  PCG, SO, SYY, VALE, WBD, WMB — enumerated when the layer stood at 85 pegged names, before the
  last 25 were added); those are finding 5, not thin chains — their OI coverage on pegged
  dates is 0.80 against 1.00 elsewhere. **Read: GEX is not a usable number for the thin names, and
  is coverage-conditional for the rest.**
- **`zero-gamma not found` — 26 names** (ALAB, APP, AU, AXON, BE, CCJ, CLS, COHR, COR,
  CVE, DASH, DB, FLEX, HWM, INFY, LITE, NU, RKT, SE, VRT, VST, WBD + newer additions).
  Investigated on 2026-08-04 and it is **a one-sided book, not a solver failure**. The first
  explanation tried — "|GEX| is simply bigger there" — held for 20 of 22 names but FAILED on COR
  (0.07×) and WBD (0.80×), so magnitude is not the mechanism. The mechanism is direction: on the
  no-flip dates the book is call-dominated, median put/call OI **0.60** versus **0.72** on dates
  where a flip is found and **0.78** cache-wide, call-heavy on 20 of 22 names. Dealers sit
  one-sidedly long gamma and the profile never crosses zero anywhere in the ±25% spot grid, so a
  blank is the correct answer. Note this reading depends on the GEX sign convention below; if the
  convention is wrong the interpretation flips, but the "no crossing" fact does not.
- **`no open interest at all on N% of dates` — AAPL and AXON.** The AAPL 2020 OI gap described above.
- **`N rows with expiration before quote date` — 14 names** (AMD, BAC, CME, EXC, NEE, NSC, OKE,
  PNC and six more) — junk rows in the vendor cache: 2022 expirations on 2024/2025 quote dates,
  strike exactly 300 or 3000, bid/ask around $3,000 on a $50 stock, `open_interest = -1`. 37 rows
  in 349 million. Correctly skipped; harmless; noted because they exist in the miner's files.
- **`N rows had no underlying close` — FTI only**, 33,823 rows. Checked: FTI's option cache starts
  in 2016 but its prepared bar series starts **2017-01-17** (TechnipFMC was created by the
  FMC Technologies/Technip merger that month; the pre-merger ticker's history is not in
  `data/bulk/prepared/bars/`). Those 2016 rows get no spot, so no IV. Skipped, not filled — and a
  useful reminder that the option cache and the bar cache do not have identical date ranges.

## Caveats — do not drop these when this layer gets used

- **IV is inverted from the EOD mid**, which on a wide quote is the midpoint of two prices nobody
  traded at. Noisiest exactly where the spread is widest and vega smallest, which is why the band
  exists and why everything outside it is left empty rather than filled.
- **European Black-Scholes greeks on AMERICAN options, dividend yield hard-coded to zero.**
  Measured effect: the ATM put-minus-call IV gap is ~0.000 for AAPL and **+0.003 to +0.007 for
  ABBV** (a ~4%-yield name) — i.e. puts read 0.3–0.7 vol points rich on dividend payers, exactly
  the direction and size q=0 predicts. Stated, not corrected; identifiable from `right`/`moneyness`.
- **The GEX sign convention is an assumption** (dealers long gamma in calls, short in puts). It is
  the standard convention, not something this repo has verified. If it is wrong, every GEX sign
  flips; magnitudes and the strike profile do not.
- **Zero-gamma re-evaluates every contract's gamma on a spot grid with IV held fixed.** A real
  surface would move with spot. Standard construction, still an assumption.
- **Greeks are RAW analytic derivatives** (vega per 1.00 of vol; theta/charm/veta/color per YEAR).
  `blackscholes.greeks()` reports vega/100 and theta/365. A test pins the relationship. Do not mix.
- **Gamma walls must be read conditional on `oi_coverage_iv`** — finding 5. This is the newest
  caveat and the easiest one to forget, because `gex_wall_conc` looks like a clean number.
- **Nothing here has been shown to predict anything.**

## Verification

Every greek is checked against a central finite difference of the analytic price. That caught
`veta` and `color` pointing the wrong way in time — the published formulas are derivatives with
respect to time-to-expiry, and this module reports per calendar time like theta. Both were fixed
before any data was written. The vectorised pricer and IV solver are also checked against the
scalar `blackscholes` implementation the live code already uses, and the put/call greek identities
(gamma, vega, vomma equal; deltas differ by exactly the discount factor) are pinned.

Independent sanity on real output: AAPL ATM 30-day IV by year reads 0.224 (2016), 0.197 (2017),
0.354 (2020 — covid), 0.223 (2024); 25-delta skew is positive throughout (puts over calls, as it
should be for equity); zero-gamma is located on 96% of AAPL dates.

Suites after the change: **options-greeks 22/22, edge 119/119, bulk 14/14, engine 28/28,
intraday 18/18, saas 20/20, screener 28/28.**

Note: the CI gate (`land-agent-branch.yml`) runs only `tests/test_edge.py`, so
`tests/test_options_greeks.py` does not gate a deploy. Worth wiring in when someone owns that
file — left alone here to avoid a merge conflict with the other agents' branches.

## What is NOT covered

**177** names the manifest marks `skipped_thin` and **3** marked `partial` have no derived layer,
because the miner did not finish them. Every one of the 315 it marks `complete` is derived — the
layer is exactly level with the miner as of this snapshot. That is the miner's call, not this job's —
if it ever completes them, re-running the enricher picks them up with no arguments. **This set is
still growing in both directions** as the miner works through its list, which is why the count is
given rather than the roster.

## Next

- #23 (options signal research) can start from a ready layer. It is **GATED** — no ICs, no
  backtests, no keep/reject calls on this until Don says so. When it does start, finding 5 is the
  first thing to honour: **do not use a gamma wall without its `oi_coverage_iv`.**
- **Re-run the enricher whenever the miner has advanced.** No arguments needed, it is resumable,
  and it now also repairs the flags on every record it has ever written.
- If the miner re-mines AAPL 2020 (or anything else) for open interest, just re-run the enricher;
  it will notice and redo those names on its own.
- **For whoever owns the miner:** the `-1` OI sentinel is the root of findings 1 and 5, and it
  also flows into `options_backtest.chain_summary`'s `call_oi`/`put_oi` sums. Not touched here.

---

# 2026-08-15 — MASTER AUDIT, THE GREEKS LANE'S LAST FOUR: MA4, MA18, MA30, MA52

**One line:** two real defects fixed on the contract-bound track and the licence boundary
(`MA4`, `MA52`), one disclosure built and deliberately not turned into a screen (`MA30`), and one
row verified and left blocked because the missing piece is a schedule this repository cannot own
(`MA18`) — **and MA18's own test became reachable for the first time and FAILED.**

**None of the four had been landed by any lane.** All four read `OPEN`, and that was correct.
Every claim below is a measurement taken this session, not a restatement of the audit.

## MA4 — the bound history was rewritten non-atomically and lost unknown columns. FIXED.

`valuation/screener/index_mark.py::append_row`. **Both defects confirmed in source before being
fixed**, and both are about EVERY row in the file rather than the row being added, because
appending one row rewrites the whole file — the file `track-backup.yml` calls *"the one thing that
can't be re-derived"*, whose only other copies are a WEEKLY backup cron and one laptop.

1. `open(path, "w")` truncated first, so an interruption between truncate and flush left the bound
   series empty or partial. Now written to `path + ".tmp"`, fsynced, and `os.replace`d over the
   original — **so a failed write leaves the PREVIOUS file intact**, which is also why no separate
   pre-write copy is taken: the original *is* the copy until the rename lands.
2. Every historical row was re-projected onto `ROW_COLUMNS`, so the first append after the file
   gained a column would have deleted that column **from every row at once, silently**. The header
   is now the union of what is on disk with `ROW_COLUMNS`.

**NEITHER PIN IS TAKEN ON TRUST.** The superseded write is kept verbatim as a test fixture and run
against the same inputs: it drops the added column from all three rows, and interrupted the same
way it leaves the file **shorter than it found it**. A regression test that cannot be shown to fail
against the defect it names is worth nothing.

**Three things the audit did not ask for, each because the fix exposed the question.** A ragged
file is now **REFUSED rather than normalised** — `csv.DictReader` pools surplus cells under one key
and pads short rows, so a rewrite would invent or discard cells in silence; refusing leaves a
recording gap that `track_meter.recording_history` can see, while normalising loses data nothing
can recover. A key on the incoming row that is in neither the file nor `ROW_COLUMNS` is still not
written — widening the bound schema should take a deliberate edit, not a caller's typo — but it now
comes back in `ignored_fields` instead of vanishing. **And the guard was checked against the REAL
file before shipping**, because a guard that refuses the live series is worse than the defect it
replaces: the tracked backup parses clean, zero ragged rows.

**A minor path correction against the record:** the shipped `data_export` backup of the live series
carries **no `day_n` column**, while `ROW_COLUMNS` says `day_n` is *"carried because the existing
rows carry it"*. The local copy does carry it, so the claim is true of one copy and not the other.
The union direction only ever ADDS, so this is inert either way.

`tests/test_index_mark.py` **31/31** (was 23/23).

## MA18 — verified, severity confirmed, and NOT closed.

`readonly`, `modifies: []`. The deliverable is evidence; the missing piece is a schedule.

**THE REPO HALF IS NOW MEASURED RATHER THAN ASSERTED.** Nothing here schedules the writer: the
mechanism and its script are named in no workflow, batch file or task definition, and every cron in
`.github/workflows/` is a scan, a recap, a watchdog or the weekly backup. The audit's
`evidence_needed` asks for confirmation from the Cowork lane; **that half is still theirs.**

**THE ROW'S OWN TEST BECAME REACHABLE FOR THE FIRST TIME AND IT FAILED.** The record says the test
— a dated miss on an OPEN vintage — had never been reached, a vintage event having intervened on
all three attempts. Measured today: **vintage 4 owed exactly ONE trading day, 2026-08-14, and
received nothing.** `recording_history` reads v1 VOID 2 of 6, v2 0 of 0, v3 0 of 1, **v4 OPEN 0 of
1** — that last cell is new, and it is the first honest reading.

**A ROW DID ARRIVE, AND IT IS NOT THE MECHANISM'S.** The local bound file gained a **2026-08-13**
row, written 2026-08-14 18:07, reading **4.25 / 4.88 / −0.62**. The documented mechanism computed
**4.3232 / 4.8794 / −0.5562** for that same date. So the recorded series is **still hand-made**, and
the discrepancy reproduces the module's own disclosed dissociation on a **THIRD date**: the
benchmark leg agrees to rounding (**+0.0006**) and the book leg does not (**−0.0732pp**, against the
disclosed 0.0201pp seam on 2026-08-06). **Same direction both times** — the recorded book leg sits
BELOW the re-derived one.

**AN HONEST LIMIT, the same one the record already carries:** all of this is measured on the LOCAL
copy. The last authoritative pull of the live file is 2026-08-10 18:09, two rows; the backup cron is
weekly and next fires **2026-08-16**. So the miss is confirmed locally and not yet on the live
service.

## MA30 — tenure on the hot list. BUILT as a disclosure, deliberately not as a screen.

`valuation/web/tenure.py`, wired additively into the hot list payload. `tests/test_tenure.py`
**16/16**.

**THE PREMISE WAS CHECKED FIRST AND IT HOLDS, THROUGH A SOURCE THE AUDIT DID NOT NAME.** The map
points at `index_track.py`; the data is actually in the **store**, whose `snapshot_rows` table is
keyed by scan date and ticker and carries `rank`, so a name's position on every past scan is already
recorded. No new vendor, no new table, and **not** the gzip scan archive — which is append-only and
by its own docstring never read by the live app.

**BOTH OF THE AUDIT'S CONSTRAINTS ARE ENFORCED BY TEST, NOT BY DOCSTRING.** The claim it must not
make — that long-tenured names are better — is a `BANNED` tuple asserted **against the RENDERED
payload** rather than the source, because rendering is where copy leaks (the `dip_posture.py` design
the record recommended carrying forward). The standing condition — *a register the moment anyone
sorts or filters by it* — is a source sweep that fails if the field reaches a sort key or a filter
predicate, checked for vacuity against a sample screen.

**Three design decisions worth the row.** The decile is taken over the scan's own recorded size and
**not** over the viewer's `top` parameter, which differs per tier and would have shown one name two
different tenures. A scan that never recorded its size is **SKIPPED as unknown** rather than counted
as a miss — a missing denominator must not read as everybody qualifying. And an unreachable store
leaves the rows untouched and reports `available: false`, because defaulting to 1 would caption
every name on the list as *new today*, which is a confident wrong caption rather than a missing one.

**WHAT HAS NEVER BEEN SEEN, STATED PLAINLY:** the arithmetic is pinned against fixtures and the
**numbers have not been observed anywhere**. The store in this checkout holds **ONE** scan, dated
**2099-01-01** with provider `ci`, and the local scan archive holds **one real day of eight**. The
history lives on the live service. Verified as a computation, unverified as a description of the
live book.

**A CORRECTION AGAINST MY OWN FIRST DRAFT**, kept because a plausible wrong reason is harder to
catch later than none: the store reader's docstring justified reading `scans.scored` by
`archive_scan`'s top-100 truncation, which is a **different sink** and does not touch that table.
The choice is still right — a partially deleted snapshot would shrink a `COUNT(*)` decile and admit
names never in the top tenth of the scan that ran — and that is now the stated reason, with its own
test. **Zero trials:** it measures no hypothesis and clears no threshold.

**ROUTED, NOT DECIDED:** whether the hot list *renders* the field is the web lane's call. The
payload carries it; no template was touched.

## MA52 — the licence boundary had no structural guard. FIXED, and the row was wrong twice.

**TWO CORRECTIONS AGAINST THE AUDIT, BOTH FOUND BY CHECKING BEFORE FIXING.** Its file path is wrong
— the constant is in **`valuation/saas/surfaces.py`**, not `screener/` — and **the second half of
its proposed fix already ships**: a test that fails when a new read route is unclassified has
existed since **LA13, 2026-08-10**, walking the app's own URL map through `surfaces.classify`, and
it is non-vacuous. The audit asked for something already built.

**SO THE DEFECT IS NARROWER AND SHARPER THAN THE ROW SAYS, AND POPULATING THE SET WOULD HAVE BEEN
WRONG.** The deny set is empty because it **should** be empty — no read route echoes a vendor row,
checked route by route. What was missing is that **an empty deny list and an UNCONSIDERED one are
indistinguishable from outside**, so the licence boundary rested on somebody remembering the set
exists. The fix is LA13's own mechanism on a second axis: `vendor_review()` returns `None` for a
route nobody has answered for, exactly as `classify()` returns `None` for an unclassified one, and
the sweep fails on it. **A deny list cannot be forgotten if the suite will not go green until the
route is on one side of it.**

**THE REVIEW SET IS WHAT A PREVIEW CAN READ — 20 routes, and the scope is a judgement.**
Redistribution bites where an un-authenticated or preview reader sees the payload, so an owner route
the demo tier is denied, and an admin-token route that refuses a tokenless caller, are excluded —
both already pinned elsewhere, and re-asserting them here would have been a second copy of someone
else's policy.

**THE CLOSEST CALL IS RECORDED AS A JUDGEMENT RATHER THAN ASSUMED.** The module's own docstring
names the research prefix as *"the one place Sharadar-derived output reaches an HTTP route"*, and the
gating layer deliberately grants exactly one path under it to the read tier. Its payload is adopted
weights, learning history and two summary blobs — IC statistics, weight vectors, and accept/reject
flags computed **over** the licensed panel. **No ticker-date fundamental, no price, no filing
figure.** Cleared on that basis, and named as the entry to re-read first if that payload ever widens.

**Four pins**, including one that the `denied` verdict is actually expressible and does deny —
otherwise the set the audit asked to populate would be decorative — and one that a cleared entry
naming a route the app no longer registers fails, since a stale clearance reads as *reviewed*
forever and covers nothing.

`tests/test_public.py` **39/39**, `tests/test_public_full_view.py` **19/19**.

## What I did NOT do

- **MA18 is not closed and must not be read as closed.** Nothing was scheduled; the writer is still
  Cowork's under the contract's §7.2. The five-year clock keeps running on vintage 4.
- **No template renders tenure.** The field is in the payload only.
- **`DEMO_DENIED_VENDOR_ROWS` is still empty**, on purpose — see above. Populating it would have
  denied routes that return derived numbers, which is the product.
- **The live service was not read** for any of this. Every measurement is local, and MA18's section
  says exactly where that limit bites.

---

# I-1 — the Breeden–Litzenberger RND builder (2026-08-20)

`valuation/studies/rnd.py`, `tests/test_rnd.py` (**45/45**), `scripts/i1_rnd_census.py`,
artifact `data/free_analysis/I1_RND_CENSUS.json` (gitignored, re-derivable by the script).

**ZERO TRIALS. This is an INSTRUMENT, and its neutrality is the deliverable.** It computes no
relationship between any RND quantity and any forward return — not a correlation, not an IC, not
a bucketed mean. It is consumed by `PREREG_DRAFT_o1_flagged_puts.md` as a **stage-0 kill that
fires before any arm exists**, so a builder that had already been pointed at returns would be
scoring that kill on a tool which had seen the answer. Enforced, not promised: `test_rnd.py`
sweeps the module's own source (AST, docstrings stripped) for forward-return vocabulary and for
a mutable-store escape hatch, and both sweeps carry a positive control.

## 1. The headline: SR-677 as written does not survive contact with an equity chain

The scout's citation names NY Fed SR-677 (Malz 2014) as the standard stable implementation, and
it was implemented **literally first** — implied vols, cubic spline in **delta** space, **flat**
vol extrapolation, Breeden–Litzenberger by finite difference. On the frozen chains it produced
**0 usable slices out of 387**. Two distinct causes, both measured before anything was changed:

* **The delta→strike map is not invertible on a steep skew.** Measured on AAPL 2025-07-07:
  **7 folding steps at delta 0.0059–0.0074, where K doubles back through 265–270**, exactly where
  `max|d²σ|` peaks. Sorting by K and de-duplicating silently discards the folded branch, leaving
  a jump in σ(K) that BL turns into a density spike of **−0.90 against a peak of +0.72**. Delta is
  the right coordinate for FX, where SR-677 is aimed and quotes arrive at five well-separated
  deltas; it is the wrong one for a 31-strike equity chain.
* **Flat extrapolation manufactures negative density at BOTH seams, by construction.** The density
  carries `C_σ·σ''`. Clamping vol flat puts a **step in σ′**, and a step in σ′ is a **delta
  function in σ''** — so a negative spike at each edge is guaranteed whenever the smile has any
  slope there, which an equity skew always does. This is arithmetic, not bad luck.

**Two departures, each adopted only after the literal version was measured to fail:**

1. **Abscissa is `ln(K/F)`**, monotone in K by construction — the fold is removed structurally
   rather than detected and patched.
2. **Wings are C¹ smooth-pasted**, `σ(x) = σ_e + slope_e·L·(1 − exp(−|x−x_e|/L))` — no delta
   function at the seam, and **asymptotically constant**, so the far tails stay lognormal, which
   is the property flat extrapolation existed to provide.

Effect of the pasting alone, holding everything else fixed: benchmark negative mass
**1.1e-3 → 1e-12**, real-chain median **3.3e-2 → 1e-11**, share of clean densities **0.04 → 0.83**.

**The smile fit is a spread-weighted smoothing spline** (`s = n`, the standard chi-square target).
Each point's vol uncertainty is *measured* — solve IV at the bid, at the ask, halve the difference
— so one rule serves a 31-quote AAPL chain and a 9-quote ABBV chain without anyone choosing a
smoothing constant per name. Interpolating every quote exactly puts tick noise straight into σ''
and rings; a rigid polynomial cannot follow a real skew. Selected on the benchmarks plus
real-chain stability and **better on both axes at once** — max mixture error **7.0e-3 vs 1.6e-2**
for a cubic polynomial, real-chain clean share **0.913 vs 0.812** — so the choice cost no
trade-off. `SMOOTH_S_MULT = 1.0` was checked to sit on a **plateau** (1.0/2.0/4.0 identical), not
at a tuned edge.

## 2. Verified against published closed forms, because that is the only honest test

* **Flat smile → Black–Scholes lognormal**, tail mass exactly `N(−d2)`. Max error **1.8e-5**.
* **Two-lognormal mixture — Bahra, BoE WP 66 (1997)**, the canonical published RND test case:
  skewed, fat-tailed, and priceable in closed form so the estimator is fed EXACT prices and any
  error found is its own. Errors **1.9e-4 to 7.0e-3**.
* **The control that makes the mixture test mean something.** A lognormal is the case a broken
  estimator still gets right, so an estimator tested only against it has not been tested. At the
  0.70 threshold the true mass is **0.10715**, a single lognormal at the ATM vol says **0.03966**,
  and this estimator returns **0.10563** — it recovers a tail a lognormal understates ~2.7-fold.
  The test asserts the lognormal control **fails**, so it cannot pass vacuously.
* **The benchmarks are themselves verified before anything is scored against them** — the mixture
  CDF against numerical integration of its own density, the mixture call against numerical
  integration of the payoff, and the one-component mixture against the lognormal formula to 1e-12.
  A benchmark nobody checked is not a benchmark.
* **Mutation battery on the tail-mass arithmetic, 7 mutations, all caught**: survival-instead-of-CDF,
  flipped BL sign, corrupted discount factor, corrupted second-difference stencil, threshold read at
  the wrong strike, corrupted parity forward, and `N(−d2)→N(−d1)` **in the analytic reference
  itself**. A baseline test asserts the suite is green before mutation, so no mutation can "pass"
  against an already-red baseline.

## 3. The census — fit diagnostics per slice, not an assumption of convergence

`python -m scripts.i1_rnd_census --symbols 60 --dates 3`, pinned harvest freeze
(`manifest_sha256 ee6d38e5…`), **2,174 slices over 60 symbols**:

| | |
|---|---|
| in DTE band | 1,700 of 2,174 (474 refused as weeklies/LEAPS, a designed exclusion) |
| **usable** | **1,168 = 68.7% of in-band** |
| **K1 parity vs `raw_close` within quoted-spread band** | **0.9858 — PASS**, register wants ≥0.95 |
| integral | med 0.999999, p95 1.000003, max 1.0171 |
| negative mass | med 4.5e-12, p95 5.0e-4, max 9.7e-3 (gate 1e-2) |
| CDF two-route gap | med 2.2e-6 |
| \|parity dev frac\| | med 0.0028, p95 0.0175 |

Refusals are attributed, never silent: `cdf_not_monotone_in_read_region` 417,
`negative_density` 124, `too_few_smile_points` 73, `integral_off` 35, `parity_spot_mismatch` 15,
`no_parity_forward` 8. `build_name_day` **returns unusable slices rather than dropping them**,
because a caller writing a coverage census needs the refusals.

## 4. Two findings the consumer must read before quoting anything

* **80.5% of `Q(S_T ≤ 0.50·S_0)` readings are EXTRAPOLATIONS beyond the lowest quoted strike** —
  and that is precisely the threshold O-1's **K2** reads. By threshold: **0.50 → 80.5%,
  0.60 → 62.2%, 0.70 → 46.1%, 0.80 → 27.7%, 0.90 → 5.7%.** Every slice carries a per-threshold
  `threshold_extrapolated` flag and the builder will not hide it. **The error is one-directional**:
  a real equity smile keeps steepening into the left wing while the pasted continuation flattens
  it, so an extrapolated left-tail mass is a **LOWER BOUND**. For K2 — "does the market already
  price the flag?" — that is the conservative direction: it biases toward *the market charges less
  than it really does*, making the `ρ_RND ≥ 3.04` **VOID** verdict **harder** to reach, not easier.
  K2 is still runnable; it must be quoted with the extrapolated share beside it, and a
  ratio-of-medians is far more robust here than either median alone.
* **O-1's K1 "integrates to 1 ± 0.02" is close to VACUOUS as a check, and should not be leaned on.**
  Computed this way the integral **telescopes** — it is a sum of second differences of the call
  curve — so it returns ≈1 almost regardless of how badly the smile behaves. Measured: on the
  AAPL chain whose density was oscillating between **−0.90 and +0.72**, the integral read
  **1.00000**. It is retained because the register asks for it and it does catch one real thing (a
  grid that truncates mass), but **`negative_mass` is the diagnostic that actually detects a broken
  density** and is the one to read first. The other two legs of K1 — monotone CDF, parity vs
  as-traded spot — are genuine and both are enforced.

## 5. The traps, handled

* **`raw_close`, never `close`** (`U1-SPLIT`, `O6`). Pinned from both sides: the correct spot
  passes the parity check, and a 4-for-1 "adjusted" spot **fails and says
  `parity_spot_mismatch`**. An adjustment mismatch throws parity by tens of percent, so that
  check's real job is catching a corporate action, not auditing dividends.
* **The circular-parity trap, avoided by name.** `dividends.spot_from_parity` returns
  `S = C − P + K·e^{−rT}`; deriving the forward from parity and checking it against a spot derived
  from parity is TRUE BY CONSTRUCTION — MA31 named that failure. The check here is against
  `raw_close` from the bars, an **independent** series.
* **`usable_quote` on BOTH legs**, the one shipped definition (`MA45`), delegated to and pinned by
  identity (`R.usable_quote is BS.usable_quote`) — audit B7's class. A matched pair with one dead
  leg is not a pair. Excluded rows are **counted**, never imputed.
* **`bs_price`/`implied_vol` reused, not re-derived.** Black-76 is obtained by passing
  `S = F·e^{−rT}, q=0` to the shipped solver — the substitution cancels the `rT` term exactly — so
  no second pricer sits beside the first.
* **PINNED FREEZE ONLY.** `chain_store.resolve_chains` / `resolve_harvest`, which **raise** rather
  than fall back; the mutable store is `O16`'s defect (44.2% of payload units rewritten after the
  books were banked). Pinned by a source sweep plus a test that a missing freeze raises.

## What I did NOT do

- **No relationship to forward returns, anywhere.** That is the point of the instrument and it is
  the one thing that would void it. O-1's stage 1 is not started and not designed here.
- **`I1_RND_CENSUS.json` is NOT committed** — it lands under gitignored `data/`. Re-derive with the
  script; the provenance block records the freeze manifest hash the numbers came from.
- **The options freeze (`freeze_options_2026-08-17`) was not censused**, only the harvest freeze.
  The harvest holds a full chain on every session while the options store holds one only on entry
  dates, so it is the right source for per-name-day densities — but `--store options` exists and
  its coverage is **unmeasured**. Anyone running O-1 against entry-date chains should census it
  first rather than assume these rates carry over.
- **No term structure and no cross-expiry interpolation.** Each (name, date, expiry) is independent;
  nothing here builds a constant-maturity RND.
- **31.3% of in-band slices are refused**, and I did not chase the residual. The dominant reason is
  `cdf_not_monotone_in_read_region` (417), which is a genuine butterfly violation in the quotes
  rather than an instrument defect — but I did not separate "the chain is arbitraged" from "the fit
  could be better", and that split is worth having before anyone reads a coverage number as a
  data-quality claim.
- **`GRID_SIGMAS`, `PASTE_L` and the DTE band were not swept jointly.** `PASTE_L = 0.50` was taken
  from a 1-D sweep (pass rates climb steeply 0.10→0.50 then flatten); a joint sweep might do
  better, and nothing here claims these are optimal — only that they are on a plateau rather than
  an edge.

---

# E-4 — the market-tail crash flag beside the accounting card (2026-08-20)

**Season 2 register `E-4` (`IDEAS_LEDGER.md`, S-SEED-5), the OPTION-IMPLIED half — the half the
ledger's own `I-1` entry names as unblocked by the RND builder.** Executed by this lane, which
also built `I-1`.

`PREREG_e4_market_tail_flag.md` committed **ALONE and BLIND at `cf7c7fc`** — markdown only, zero
`.py`, 378 lines, a strict git ancestor of every measurement commit. **ONE equity trial booked at
`654326a` BEFORE the runner existed**, equity **238 → 239**; options 305 and infra 19 untouched,
re-read from `by_domain` after merging rather than quoted from a mid-run figure (`MA37`).
**ADOPTS NOTHING** — no file under `valuation/` that the product imports changed, and no card is
built. `MB31` proves no calibrated permutation floor can move below equity `N` = 247.

**AND THE FIGURE TO QUOTE IS 241, NOT 239 — RE-READ AFTER MERGING, WHICH IS `MA37`'s RULE FOR THE
FOURTH TIME.** `238 → 239` describes *this item's own booking*. While it ran, two other lanes
landed `E-2` and `E-3`, each of which had also booked off a base of 238, so **both sides of the
resulting `EXPECTED_BY_DOMAIN` conflict were wrong** — mine said 239, `origin/main` said 240, and
the merged log carries all three rows. **The stamp was reconciled to the MEASURED count of 241**
(options 305, infra 19 untouched) and the HLZ hurdle it drives re-derived to
**3.312037721249761**, rather than by taking a side, which would have mis-stamped a domain
neither lane had wrong — `MB22`/`MB23`'s exact situation, resolved the same way. **Keep-both is
right for ROWS and wrong for CONSTANTS:** the nine Season-2 ledger rows were all kept (one each,
verified), while the stamp is asserted to be assigned **exactly once**, because a duplicated copy
silently defeats the tamper-evidence it exists for. Equity 241 is still below `MB31`'s 247, so no
calibrated floor moves.

## 1. THE VERDICT IS `UNDERPOWERED`, AND THE COMPARISON THE ITEM EXISTS FOR SURVIVES IT

**The market flag DOES catch crashes the accounting flags miss.** On the **8,275 + 1,980 =
10,255 accounting-CLEAN rows**, the market flag separates at **ratio 3.0541 — 0.9596% (19 crashes
of 1,980) against 0.3142% (26 of 8,275)** — and both buckets clear the declared `min_events = 10`,
so that ratio is **quotable**.

**Whether the accounting flag catches crashes the MARKET flag misses is UNANSWERABLE on this
universe, and the register said so before the run.** On market-clean rows the accounting flag has
**286 rows carrying 4 crashes**; `crash_gate.quotable` **withholds the ratio** with its reason
attached. §7 predicted exactly this — *"if that is what happens, the 'vice versa' half of the
comparison is UNANSWERABLE and will be reported as unanswerable, not as a null."* It is reported
as unanswerable.

**THE 2×2** (crash = `fwd_ret ≤ −0.50` over the panel's 63-trading-day window; 10,707 rows,
40 dates, 486 names, 54 crashes):

| | accounting-flagged | accounting-clean |
|---|---|---|
| **market-flagged** | 166 rows, 5 crashes, **3.0120%** | 1,980 rows, 19 crashes, **0.9596%** |
| **market-clean** | 286 rows, 4 crashes, **1.3986%** | 8,275 rows, 26 crashes, **0.3142%** |

**The two flags are very nearly independent: Cohen's κ = 0.0624**, co-firing odds ratio 2.4257.
They are finding different names, which is what makes the 2×2 worth having. Arithmetic on those
published cells, no new computation and no extra arm: the market flag fires on **20.04%** of rows
and carries **24 of 54 crashes (44.4%)**; the accounting flag fires on **4.22%** and carries **9
of 54 (16.7%)**; their union fires on **22.71%** and carries **28 of 54 (51.9%)**. **Neither flag
sees the other 26.**

## 2. WHY IT IS `UNDERPOWERED` AND NOT `PASS`, DECIDED BY ARITHMETIC RATHER THAN JUDGEMENT

| window | dates | mean per-date diff | NW *t* | pooled ratio | B1 | B2 ≥ 2.0× | B3 ≥ 0.50pp | all three |
|---|---|---|---|---|---|---|---|---|
| **full** | 40 | **+0.6789pp** | **+2.3813** | **3.1914** | ✔ | ✔ | ✔ | **✔** |
| early | 19 | +0.3875pp | +1.1117 | 1.6882 | ✘ | ✘ | ✘ | ✘ |
| late | 20 | +0.9897pp | +2.2483 | *withheld* | ✔ | ✔ | ✔ | ✔ |

Halves boundary **embargoed at 2020-10-20**. Bars are `MA28`'s, reused verbatim.

**The full sample clears all three of `MA28`'s legs at a ratio of 3.1914 — within 5% of `MA28`'s
own 3.0422 — and the early half does not.** The register requires full **and** both halves, so
this is not a PASS.

**And the pre-committed three-state rule then makes it UNDERPOWERED rather than FAIL, because the
observed effect sits below the design's own detection threshold:**

> MDE at |*t*| > 3.3095 (N = 239): detection threshold **0.00880349** (50% power); **0.0110379**
> at 80% power. Power against the observed effect 0.00678927 is **22.4%**.

> MDE at |*t*| > 2.0000: detection threshold **0.0053201** (50% power); **0.00755454** at 80%
> power. Power against the observed effect is **71.0%**.

**Both vocabularies, as `RUN_RULES` PART A rule 11 requires, and they disagree in the way that
matters: at the conventional bar this effect is visible (*t* +2.38, and the design has 71% power
against it); at this project's own multiple-testing hurdle it is not.** `V6`/`S19`'s rule stands
— **UNDERPOWERED means "could not be separated at this resolution", never "absent".**

**THE LATE HALF'S RATIO IS WITHHELD AND MUST NEVER BE QUOTED.** It computes to 12.96, on **4
crashes in the kept bucket of 4,650 rows**. `quotable()` refuses it. This is `MB8`'s lesson
firing for real rather than as a precaution.

**THE PRE-RUN POWER STATEMENT WAS RIGHT AND ITS SE WAS 1.62× TOO OPTIMISTIC.** The register
predicted the binomial se would understate, at 80/20; measured, the **realised per-date se is
0.2660pp against the pre-run binomial 0.1638pp**. Crashes cluster — `MA28` measured the base rate
moving 4× between halves around COVID 2020Q1 — so the independence assumption was wrong in the
direction stated in advance. At the realised base rate the pooled route needs **54,854 rows at
the 2.0× floor and 19,176 at 3.0422×** against **10,707** available.

## 3. THE CONTROL THAT SHOULD DECIDE HOW ANYONE READS THIS

**`C-VOL` reads 0.8901 against my own 0.90 relabel bar. It missed by 0.0099.**

The pre-committed rule was that at |ρ| ≥ 0.90 the flag **must** be described as an implied-vol
sort. **It did not fire, so I do not claim the mandatory relabel — and nobody should lean on a
margin of 0.0099 either.** The honest sentence is that **at a mean per-date Spearman of 0.8901
against ATM implied vol, this design cannot distinguish "the RND's left-tail shape predicts
crashes" from "implied volatility predicts crashes"**, and the second is a far older and duller
claim. A register wanting the first would have to hold implied vol fixed, which is a different
construction needing its own trial.

**`C-TENOR` reads 0.4608 and is a real confound, foreseen but larger than I expected.**
`Q(S_T ≤ 0.70·S_0)` grows mechanically with T, the band is [50,140] (median DTE 86, p05 53, p95
119, a 2.8× range), so the within-date quintile is partly a tenor sort. Reported, no bar.

**`C-SIZE`: flagged names are 3.2× SMALLER** — median market cap $11.50bn against $36.91bn
(ratio 0.3115) — and the flag fires overwhelmingly in the small end (1,018 of 2,158 rows in the
smallest cap quintile against 84 of 2,146 in the largest).

**Within cap quintile, EVERY RATIO IS WITHHELD, and that is the finding rather than a gap:**

| cap quintile | flagged n / crashes / rate | kept n / crashes / rate | ratio |
|---|---|---|---|
| 1 (smallest) | 1,018 / 8 / 0.786% | 1,140 / 7 / 0.614% | withheld |
| 2 | 535 / 7 / 1.308% | 1,599 / 7 / 0.438% | withheld |
| 3 | 320 / 5 / 1.562% | 1,815 / 10 / 0.551% | withheld |
| 4 | 189 / 2 / 1.058% | 1,945 / 6 / 0.308% | withheld |
| 5 (largest) | 84 / 2 / 2.381% | 2,062 / 0 / 0.000% | withheld |

**The direction is the same in 5 of 5 — flagged above kept in every quintile — and not one cell
carries enough crashes to support a ratio.** So `MA28`'s C4, the control that decided `U7`,
`S10` and `V6-B`, **cannot be evaluated on this universe**. The size story is neither confirmed
nor refuted here, and saying so is the whole point of the `min_events` rule.

## 4. THE KILL, AND THE ARITHMETIC THAT HAD TO COME FIRST

The ledger's condition is *"flag-overlap census vs accounting flags > 70% → withdrawn"*.

**Stated in the register before running it: as literally written it CANNOT FIRE.** `MA28` flags
5.74% of the panel and this flag flags 20% by construction, so `P(accounting | market)` is
bounded above by the accounting share divided by 0.20. **Measured, that ceiling is 0.2111 and the
statistic reads 0.0774** — the bar is 0.70. **This is `MB8`'s failure exactly** — an audit that
set a 20% bar and a 0.5× haircut without multiplying them together — **and it applies to the
ledger's own Hill-index proposal too**, since that flag is also a quintile. **Anyone running the
physical half of E-4 should read this before quoting its kill as a safeguard.**

The kill was therefore taken on the direction that can attain the same bar:
**`P(market | accounting) = 0.3673` against 0.70 — DOES NOT FIRE.** The arm was licensed to run.

## 5. CONTROLS, AND THE ONE THAT IS EXACT

* **`C-PIN` — the covered date set is IDENTICAL to `P1S0_OPTIONABLE_PARTITION.pkl`'s**: 40 dates
  each, **zero in either direction only**. An independently produced object, built from the same
  store for a different question — which is what makes it a check rather than a restatement.
  Store provenance asserted `pinned: True`, `manifest_sha256 dc8e9b35…`; the mutable
  `data/options` store is never opened, pinned by an AST test.
* **`C-ACCT-FIDELITY`** — the accounting arm is `MA28`'s flag, built on the **full panel
  cross-section** and restricted afterwards: flagged share **0.06017** on 85,332 rows across
  those 40 dates, against `MA28`'s published panel-wide **0.057414**. On the optionable subset it
  is **0.04222** — lower, as predicted, because accounting flags fire on distressed small names.
* **`C-INSTRUMENT`** — integral median **0.9999970**, negative-mass p95 **0.00177**,
  `Q(≤0.70)` extrapolated on **41.20%** of rows (I-1's census said 46.06%). Outcome coverage
  **1.0**, so `crash_flag`'s NaN fail-open never fires — reported because a filter that cannot
  fire and one that fires and finds nothing must not read the same (`O21-D2`'s C5).
* **Coverage** — 17,558 name-days attempted, **10,707 usable (60.98%)**, all on qualifying dates,
  min 163 names per date, median 273.5. Refusals: `cdf_not_monotone_in_read_region` 3,164,
  `negative_density` 1,560, `no_expiry_in_dte_band` 854, `too_few_smile_points` 737,
  `integral_off` 291, `no_chain_on_date` 148, `parity_spot_mismatch` 67, `no_parity_forward` 30.
  **`chain_unreadable` is 0**, which matters because that path emits one refusal row per
  *ticker-year* rather than per date and would have undercounted; it never fired.

**SENSITIVITY, NO VERDICT (quoting one of these as the result voids the register §8.1).** The
finding is not an artefact of the 0.70 choice: ratios **2.5386 (0.50), 2.5386 (0.60), 3.1914
(0.70, primary), 2.9598 (0.80), 3.9893 (0.90)**, rank agreement with the primary **0.8712 to
0.9741**. The 0.50 and 0.60 cells are identical because the quintile membership is identical
there.

## 6. WHAT THIS DOES NOT SAY

* **It is not about the panel or the book.** 40 late dates, 486 names, and **this universe
  crashes at 0.4218% against 1.3250% for all panel names on the SAME 40 dates — 3.14× lower, a
  UNIVERSE effect and not a period one**, since the same-dates row controls for period.
* **It does not weaken `MA28`.** That register measured its flag on the panel, replicated it in
  both halves against its own permutation maximum, and survived a size control this one cannot
  even evaluate.
* **It is not evidence the market prices the flag.** That is `O-1`'s K2, it is not run here, and
  it needs its own register and its own trials.
* **It licenses no card and no trade.** `MA28-CARD`'s deliverable was the *sentence*; a surface
  is the app lane's, with the `BANNED` phrase tuple asserted against the RENDERED payload.

## 7. DEFECTS IN MY OWN WORK, all caught before the arm ran

1. **The accounting arm would not have been `MA28`'s flag.** `build_flags` computes the
   external-financing leg as a **top decile WITHIN EACH DATE**, so passing only the ~440
   optionable names computes the boundary on a different universe. It raises nothing and returns
   a clean, plausible flag answering a different question — `MA31`'s column-name trap in a new
   costume. Flags are now built on the full cross-section and restricted afterwards.
2. **Two controls the register promised were absent** until I audited the runner against the
   register line by line: `C-SIZE`'s within-cap-quintile comparison and `C-PIN`'s P1S0
   reproduction. **Writing a control and implementing it are not the same act.**
3. **`cg.halves` returns three values**, not two — the third is the embargoed boundary, now
   recorded, because a half-split whose boundary is unreported cannot be checked against another
   item's.
4. **Two defects in my own mutation battery, and the second is the instructive one.** The three
   2×2 mutations called the patched name and recursed into themselves, so a `RecursionError` was
   reading as *caught* for entirely the wrong reason. And **mutation m3 — `>` replaced by `>=` at
   the quantile — SURVIVED**: on 0..99 the 80th percentile interpolates to 79.2 and both flag
   exactly 20 rows, so the accuracy property contained no tie. It now includes a constant column,
   which `>=` flags entirely and `>` flags not at all. **A battery whose property cannot
   distinguish the mutation reports 8 of 8 while testing 7.**
5. **The build wrote once at the end and lost 15 minutes to a kill.** Now checkpointed every 25
   names, **keyed on the completed SYMBOL set rather than a row count** (a count-keyed resume
   both duplicates and skips the moment a symbol yields a different number of rows), and
   relaunched detached. `RUN_RULES` rule 9; `O21-D2` lost 75 minutes to the same shape.
6. **My completion watchers were pointed at the wrong path for ~40 minutes.** `_data()` resolves
   a *directory* to the worktree when it is non-empty but a *file* to the primary checkout, so
   inputs came from the primary while outputs landed in the worktree — see BUGS FOUND.

## 8. EXPECTATIONS: 7 right, 0 wrong — and DISCOUNTED, not celebrated

(1) verdict UNDERPOWERED ✔ · (2) `P(market|accounting)` < 0.40 ✔ (0.3673) · (3) `C-VOL` |ρ| ≥
0.70 ✔ (0.8901) · (4) flagged names smaller ✔ (0.3115) · (5) accounting arm withheld ✔ ·
(6) pooled ratio > 1 ✔ (3.1914) · (7) realised sd exceeds the binomial estimate ✔ (1.62×).

**Five of the seven were derived from measured facts already in the record** — `MA28`'s size
gradient, `MB8`'s thin-events lesson, the overlap ceiling's arithmetic — **so a clean sweep is
mostly a statement about the record, not about my judgement** (`SC-1`'s lesson). Only (1) and (3)
were genuine calls.

## BUGS FOUND

* **`scripts/e4_market_tail_flag.py` and `scripts/i1_rnd_census.py` share a `_data()` helper that
  resolves DIRECTORIES and FILES to different checkouts.** `_data("free_analysis")` returns the
  **worktree** path when that directory is non-empty (it holds one unrelated pickle), while
  `_data("free_analysis", "panel_r5r6.pkl")` falls through to the **primary** checkout because
  that file is absent from the worktree. Both behaviours are individually correct — the helper's
  docstring is about *"existence is not population"* — and together they mean a run reads its
  inputs from one checkout and writes its outputs to another. Nothing is wrong with the numbers;
  it cost me ~40 minutes watching an output path that would never be written. **Reported, not
  fixed** — changing the resolution order would move where every existing consumer's artifacts
  land, which is not this item's call.
* **`valuation/edge/power_gate.py` carries TWO definitions of the 80%-power z, and they
  disagree in the fifth decimal.** `state()` — the one-line statement `RUN_RULES` PART A rule 11
  asks every register to print — defaults to `Z_POWER_CONVENTION = 0.84`, while `z_for_power(0.80)`
  returns the exact quantile **0.8416212335729144**. On this item the two MDEs are **0.011037928**
  and **0.011042240**, a difference of **4.31e-06** (0.0004pp), which changes nothing here and has
  changed nothing anywhere yet. It is reported because it is the `B7`/`MA5` family — one idea
  written twice, with only one copy in the printed statement — and because a register that
  computes its own MDE with `z_for_power` and prints `state()` beside it is quoting two numbers
  for one quantity. **Both appear in `E4_ARM.json`**: the verdict branch uses the exact route and
  the printed statement uses the convention, and the handoff quotes 1.1038pp from the statement.
  **Reported, not fixed** — `power_gate` is calibration infrastructure that several landed
  registers have already printed from, and changing which constant `state()` uses would move a
  figure in every future printed statement for no measurable gain. Edge lane's call.
* **No other bug found outside this lane this session.**

## What I did NOT do

* **The `O-1` question is NOT answered.** Whether the market *prices* the accounting flag is
  `O-1`'s K2; it charges its own trials and needs its own blind register. Nothing here is
  evidence about it.
* **The physical half of `E-4` (the Hill tail index) is NOT run.** This is the option-implied
  half only. **Its kill condition is broken in the same way (§4) and should be repaired before
  it runs.**
* **`C-VOL` was not converted into an incremental test.** Holding implied vol fixed and asking
  whether the RND's *shape* adds anything is a different construction, a different arm and a
  different trial. **The 0.8901 reading is why it is the obvious next item, and also why it
  should not be run casually.**
* **No card, no surface, no product copy.** `MA28` is not re-opened, re-scored or weakened.
* **The tenor confound is reported, not removed.** A tenor-matched construction is a new design.
* **The options freeze's 2026 dates were not reachable** — the panel's last date is 2026-01-28
  and the freeze's files stop at 2025, so the covered window ends 2025-10-27.
