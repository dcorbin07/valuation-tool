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
