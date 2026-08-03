# HANDOFF — greeks / GEX derived layer (2026-08-02)

**One line:** all 111 fully-mined names now have a cached derived layer in `data/options_derived/`
— **81,241,745 of 166,393,445 contract-days priced (48.8%)** across **263,698 name-dates**, with
implied vol, the full greek stack through third order, GEX by strike, zero-gamma, gamma walls,
25-delta skew, ATM-IV term structure, IV rank and put/call ratios. Zero vendor option calls, zero
writes to the miner's cache. **Nothing has been tested for signal — that is the gated #23, and it
was deliberately not started.**

## What shipped

| file | what it is |
|---|---|
| `valuation/edge/options_greeks.py` | the maths + per-symbol driver (new) |
| `greeks_enrich.py` | resumable unattended runner (new) |
| `tests/test_options_greeks.py` | 21 tests, offline, no data needed (new) |
| `GREEKS_COVERAGE.json` | committed coverage report — the only output that lives in git |
| `data/options_derived/**` | 8.16 GB payload; gitignored like the raw cache |

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
- Two workers, each pinned to one BLAS thread. ≈ 100 s per name; the full 111-name build took
  about 2 hours across three resumed passes as the miner finished more names.

## Four things found on the way, all real

**1. `open_interest = -1` is a MISSING-DATA SENTINEL, it was being read as a number, and it is
SYSTEMIC — not a handful of bad names.** `theta_bulk` fills an OI merge miss with `.fillna(-1)`.
Across the full 111-name layer that is **19,012,352 rows, 11.4% of the cache, on 106 of 111 names,
median 12.2% of a name's rows** (worst AZN 24%, ETN 23%, AAPL 22%, RTX 19%, MO 19%; cleanest
TTE 0.9%, UBER 1.4%). **Every single row of AAPL 2020 has no open interest at all.** Read as a
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
the fix. Every coverage file records which curve priced it (`rate_source`); all 111 names here
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

## Coverage and what got skipped

48.8% of raw contract-days produced a valid IV. Every skipped row has a recorded reason:

| reason | rows | why |
|---|---|---|
| `no_quote` | 33.2M | bid or ask missing/zero — nothing to invert |
| `mny_band` | 20.7M | outside 0.70–1.30 moneyness |
| `dte_band` | 14.8M | outside 7–90 DTE |
| `wide_spread` | 7.7M | spread wider than the mid |
| `below_intrinsic` | 5.5M | mid below intrinsic — broken quote, no vol explains it |
| `penny` | 3.2M | mid under $0.05 |
| `no_spot` 35,610 / `crossed` 3,358 / `above_max_vol` 1,513 / `neg_time` 22 | tiny | rare |

That 48.8% is not a defect — it is the deliberate refusal to publish an IV where the mid cannot
support one. The names that matter are covered: 263,698 name-dates, essentially every trading day
of every mined name.

## The flags — investigated, not silenced

**107 of 111 names carry at least one flag**, which sounds alarming and is mostly one systemic
issue. Grouped by kind (the runner now prints this breakdown rather than a bare count, because
"one odd name" and "a property of the whole cache" need to read differently):

- **`open interest missing (-1 sentinel)` — 106 names.** Finding 1. Systemic, median 12.2% of a
  name's rows. Not a per-name anomaly; a property of the miner's merge. The threshold stays at 2%
  and is deliberately NOT raised to make the run quiet.
- **`GEX pegged to one strike` — 16 names** (ENB 77%, UBS 83%, BMO 65%, APH 64%, BTI 60%, TD/UL
  54%, TTE 52%, PLD 49%, NVS 43%, WELL/NVO/TM/AZN/NEE/PGR 26–33%) — **not a bug, a thin chain.**
  UBS has a median of 5 distinct strikes and 16 contracts per day against AAPL's 37 and 328. With
  5 strikes, one strike holding most of the gamma is arithmetic. **Read: GEX is not a usable
  number for these names.** The flag is the warning.
- **`zero-gamma not found on 59% of dates` — APP only.** Investigated: on exactly those dates
  APP's `|total_gex|` is **3.7× larger** than on dates where a flip IS found (2.18M vs 0.60M) and
  76% positive — the book is so one-sidedly long gamma that it never crosses zero anywhere in the
  ±25% spot grid. A missing zero-gamma there is the correct answer, not a solver failure.
- **`no open interest at all on 10% of dates` — AAPL.** The 2020 OI gap described above.
- **`N rows with expiration before quote date` — 6 names** (WFC/TTE 7, WDC 5, AMD/BAC/NEE 1) —
  junk rows in the vendor cache: 2022 expirations on 2024/2025 quote dates, strike exactly 300 or
  3000, bid/ask around $3,000 on a $50 stock, `open_interest = -1`. Correctly skipped; harmless;
  noted because they exist in the miner's files.

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

Suites after the change: **options-greeks 21/21, edge 119/119, bulk 14/14, engine 28/28,
intraday 18/18, saas 20/20, screener 28/28.**

Note: the CI gate (`land-agent-branch.yml`) runs only `tests/test_edge.py`, so
`tests/test_options_greeks.py` does not gate a deploy. Worth wiring in when someone owns that
file — left alone here to avoid a merge conflict with the other agents' branches.

## What is NOT covered

22 names the manifest marks `skipped_thin` (BBVA, BLK, HDB, HSBC, ING, KLAC, LIN, LRCX, MFG,
MUFG, PBR, RY, SAP, SKHY, SMFG, SNDK, SPCX, SPGI, SYK, TMO, VRTX) and one `partial` (BKNG) have
no derived layer, because the miner did not finish them. That is the miner's call, not this
job's — if it ever completes them, re-running the enricher picks them up with no arguments.

## Next

- #23 (options signal research) can start from a ready layer. It is **GATED** — no ICs, no
  backtests, no keep/reject calls on this until Don says so.
- If the miner re-mines AAPL 2020 (or anything else) for open interest, just re-run the enricher;
  it will notice and redo those names on its own.
