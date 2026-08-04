# HANDOFF — greeks / GEX derived layer (2026-08-04)

**One line:** every fully-mined name has a cached derived layer in `data/options_derived/` —
**315 names, 164,429,685 of 349,038,639 contract-days priced (47.1%)** across
**735,226 name-dates**, with implied vol, the full greek stack through third order, GEX by
strike, zero-gamma, gamma walls, 25-delta skew, ATM-IV term structure, IV rank and put/call
ratios. Zero vendor option calls, zero writes to the miner's cache. **Nothing has been tested for
signal — that is the gated #23, and it was deliberately not started.**

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
