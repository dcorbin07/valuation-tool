# HANDOFF — O14 tick flow, alert days only (COLLECTION ONLY)

**Lane:** data-pull. **Status:** see the coverage census below.
**No analysis was run and none may be quoted from this cache.** No IC, no backtest, no keep/reject,
no put/call statistic. O14's analysis half is a separate, pre-registered options-bot job. This
session put bytes on disk and measured the COST of putting them there — nothing else.

New files, all mine: `mine_tick_flow.py`, `tests/test_tick_flow.py`, `TICK_FLOW_COVERAGE.json`.
Nothing existing was edited. **The chain freeze was not touched** — this is a new directory,
`data/options_ticks/`.

---

## What was collected

| | |
|---|---|
| Unit of work | one **symbol-day**, the whole option chain's prints |
| Scope | the **3,885 unique `(ticker, alert_ts)` pairs** in `state_r2_corrected.pkl` |
| Names / dates | 186 symbols, 1,574 distinct dates, 2016-01-19 → 2025-10-15 |
| Endpoint | `option_history_trade_quote` (trade + prevailing NBBO) |
| DTE ceiling | **none — full chain** (measured; see below) |
| Cache | `data/options_ticks/<SYM>/<SYM>-<YYYY-MM-DD>.pkl` |

The book is read-only here and a test asserts its mtime is unchanged by the read.

### Why the whole calendar was not mined

186 names × ~2,460 trading days is ~457,000 day-pulls to obtain the same 3,885 an alert-day
question can use — two orders of magnitude more feed time and disk for nothing extra. If a later
study needs non-alert days as a control, that is a deliberate, separately-costed pull, not
something to be smuggled in here.

### Why `trade_quote` and not `trade`

Flow questions are about the AGGRESSOR — did a print lift the offer or hit the bid? A trade tape
alone cannot answer that, so every classification scheme has to infer the side. `trade_quote`
returns the prevailing NBBO with each print, which makes the side a measurement. Same call cost,
and the account's Standard tier serves it (verified before anything was built).

**Caveat that must travel with this cache:** `quote_timestamp` can lag `trade_timestamp` by hours
on contracts whose quote had not refreshed. That is the genuine prevailing quote, not a bad join,
but a side-classifier that ignores quote staleness will mislabel those prints. The staleness is
left in the data — deciding what to do about it is the analysis lane's call, not this one's.

### `.empty` does NOT mean "no trades happened" — and the check that this is not worse

The one `.empty` unit found during the run, **BUD 2024-01-10**, is not a quiet tape:

* the EOD cache records **5,883 contracts traded across 476 quoted contracts** that day;
* `option_history_trade_quote` returns `NoDataFound` — **for every day of that week**;
* `option_history_trade` returns **766 rows** for the same day.

So the trade tape exists and the trade+quote JOIN does not, for that name in that period.
**`.empty` in this cache means "no quote-joined prints available", not "no trades existed".**

The real risk that raised was not the empty unit — it was whether `trade_quote` could return
*some* of a day's prints, which coverage cannot see and which would be silent under-collection of
exactly the kind this project has been bitten by four times. **Measured on 12 collected units
spanning 864 to 114,901 prints: stored / `trade` count is 1.000 on every one.** So the join is
complete wherever it exists at all, and BUD-type gaps are ALL-OR-NOTHING — therefore visible as
`.empty` and countable. That is the reassuring version of the finding, and it was checked rather
than assumed.

**The trade-only tape was deliberately NOT substituted** for the empty units. Rows without the
prevailing NBBO are a different object from the rest of this cache, and mixing them in would put
a silent schema inconsistency inside a dataset whose entire purpose is that the side is measured
rather than inferred. Empty units are listed individually in the coverage report so a later lane
can decide what it wants; that is its call, not this one's.

### Why there is no DTE cap

Mirroring the EOD cache's 200-DTE ceiling (audit O15) was the obvious default. Measured instead
of assumed, on both ends of the size distribution:

| unit | capped at 200 DTE | uncapped |
|---|---|---|
| NVDA 2025-01-06 (largest alert-day) | 594,016 rows | 617,458 rows |
| CSCO 2023-05-08 (near median) | 3,951 rows | 4,757 rows |

+3.9% and +20% of rows, and **wall-clock is unchanged** — the call is dominated by the
server-side scan, not the payload, the same mechanism that made `strike_range` not worth using in
the EOD miner. So the cap bought nothing and would have written a silent completeness bias into a
cache whose whole point is a later put/call and unusual-volume study. The ceiling actually used is
recorded INSIDE every payload, so a future run at a different setting can never be confused with
this one — the failure the EOD cache needed `.dte` sidecars to prevent.

---

## The 20-day sample and the projection

The projection was made and reported BEFORE the full pull, as required.

A uniform random sample would have been the wrong instrument: the top 5% of alert-days carry
**50.2%** of all contract volume, so a random 20 would miss the tail that dominates the total.
Instead every alert-day's chain volume was computed OFFLINE from the existing EOD cache — zero
API calls, and it covers **3,885 of 3,885 days** — giving a KNOWN total of **396,048,088
contracts traded**. The projection then only has to fit a rate, not extrapolate a heavy tail. The
20 units are the median-volume day of each of 20 equal-count volume strata (deterministic, no
seed), pulled through the production code path so the sample measures the real thing.

| | projected for all 3,885 |
|---|---|
| prints | ~43,476,624 |
| **size** | **2.93 GB** |
| share of free disk | **1.20%** (243 GB free, floor 40 GB) |

Fitted on the sample: bytes/print is near-constant at **67.3 B**; prints fit volume log-log at
**R² 0.927**.

**The size projection was then validated against the hardest name in the book and held:** the
first 15 completed AAPL days came in at **1.08× predicted on average** (range 0.46–2.04×). Disk
was never at risk, so the pull proceeded. A 3×-pessimistic 8.8 GB would still have left 235 GB.

### The time estimate was wrong twice, and is corrected here

Reported first as ~1.0 h at 4 workers. That fitted seconds against contracts-quoted from the EOD
cache — but that cache is capped at 200 DTE and slim-filtered, so it **undercounts the true scan
width on LEAPS-heavy megacaps**: AAPL ran 34.4 s/unit against a predicted 4.6 s. Re-derived on
seconds-per-MB (stable at 6.7–8.6 across names as different as NVS and AAPL) it became 1.3–1.7 h.
The final serial design lands near **~2 h**. **Only the time estimate moved; the size projection
that governed the go/no-go never did.**

---

## The first launch failed, and the obvious diagnosis was wrong

18 units died on 75 s timeouts, every one of them AAPL. The natural reading — payload too big,
split it — is **refuted by measurement**: that exact unit returns **231,537 rows in 12.7 s** when
run standalone.

Throughput against worker count, 8 hard units, fresh channel each:

| workers | success | wall | median/call | throughput |
|---|---|---|---|---|
| 1 | 8/8 | 266 s | 29.8 s | 1.8/min |
| 2 | 8/8 | 193 s | 42.5 s | **2.5/min** |
| 4 | 8/8 | 247 s | 120.1 s | 1.9/min |

**Per-call latency scales almost linearly with workers while throughput stays flat — the server
serialises the account.** So four workers bought nothing and pushed the median call (120 s) past
`theta_bulk.CALL_TIMEOUT` (75 s). Calls that were progressing normally were abandoned as
timeouts, at 150 s of wasted wall-clock each.

**Then the failure fed itself.** An abandoned call counts as a fault, six faults rebuild the gRPC
client, and that client is SHARED across the pool — so one slow thread's timeout tore the channel
down underneath three healthy in-flight calls, producing more faults. This is worth remembering
because the log looks like a flaky feed and is nothing of the kind.

**Two workers then failed too, and the probe had not caught it.** Retrying the 18 at workers=2
recovered only 8; the other 10 died with gRPC `_MultiThreadedRendezvous` — a channel kill, not a
timeout. The 8-unit probe lacked the true giants: **AAPL's 2020–21 alert-days carry 340,811–667,796
prints EACH** (the retail options boom) against ~231k in 2024. Two such streams overlapping exceed
what the account is served concurrently. All three then succeeded **serially on a fresh channel,
first try, in 20.7–45.1 s**.

Final configuration: **1 worker, 300 s deadline, one gRPC channel per thread.** Since throughput
is flat in workers, serial costs almost nothing and buys certainty — and with a 300 s deadline a
failed unit costs 600 s, so reliability *is* the throughput argument.

**Nothing was lost to any of this.** The tri-state exists so a fault is retried rather than
becoming a silent hole; the completed units were skipped on relaunch, and zero `.tmp` files
survived the kill, so the atomic write held.

---

## Two more defects found and fixed, both mine

### 1. A cached gRPC client disabled the only channel-recovery path there is (141 units)

After the concurrency fix the run began failing again — a contiguous alphabetical block (GS, GSK,
then HD/HLT/HON/HOOD/HWM/IBM/INTC/ISRG), 141 units, while the feed itself was fine. That is
verbatim the signature `theta_bulk`'s own docstring records for a dead channel.

The cause was the per-thread client I had just introduced: it cached the client OBJECT once.
`_note_fault` recovers a dead channel by setting `self._client = None` so the *next* `_cli()`
rebuilds it — but this worker never called `_cli()` again and went on invoking a bound method of
the dead client. Holding the ThetaBulk is right; holding its client defeats the recovery.

Fixed by re-fetching `tb._cli()` per unit, plus forcing a rebuild immediately after any failed
unit rather than waiting for the six-consecutive-faults rule (a rebuild costs ~1s; a failed unit
at a 300s deadline costs 600s). **Verified over the next 250 units: zero faults, zero rebuilds,
all 141 recovered, and throughput rose to ~92/min** — the dead channel had been slowing
everything, not just failing.

### 2. Ticker renames — 31 of the 32 `.empty` units were not empty at all

The first complete run ended with 32 `.empty` units: **21 META, 10 RTX, 1 BUD**. Every META date
predates the June 2022 FB→META rename and every RTX date predates the April 2020 UTX→RTX rename.
Options are stored under the symbol as it was AT THE TIME, so asking for `META` in 2016 correctly
returns nothing. `theta_bulk` has an `ALIASES` map for exactly this, and calling the endpoint
directly **bypassed it**.

The miner now tries aliases, in the order `_fetch_span_once` established and for the reason it
documents: the CURRENT symbol is always tried FIRST, so a fallback can only ever fill a span the
name itself has nothing for — which is what keeps an alias safe across years when the old ticker
belonged to an unrelated live company. A one-time repair pass cleared those 32 markers and
re-pulled: **31 recovered, one still empty (BUD).** META 2016-01-28 alone came back with 117,479
prints that had been recorded as "no data".

Provenance is on disk, not re-derived: every payload carries `alias_used`, and 31 manifest rows
name it (21 `FB`, 10 `UTX`). **These rows are NOT this ticker's own** and any study joining them
to a symbol-keyed series must know that.

### The migration that followed, and why it was worth 70 seconds

Adding `alias_used` created a subtler problem: payloads written before it lacked the key while
still reporting `schema: 1`, so the field's ABSENCE meant either "no alias" or "written before
the field existed". That is the same indistinguishable-on-disk defect the `dte_cap` field exists
to prevent, sitting inside the very file that argues against it. All 3,884 payloads were migrated
to **schema 2 — `alias_used` always present** — atomically, in 70s, with **row counts identical
before and after (70,288,482)** and all 31 aliases preserved. `schema >= 2` now guarantees the key.

### A third, in the coverage report itself

The census took unit EXISTENCE from the filesystem and print COUNTS from the manifest — but the
manifest is written every 25 units, so units the killed first run had written had files and no
record, and their prints counted as **zero**. Understated by **67,523 prints**. The report now
reads the payload wherever a record is absent, and the total agrees exactly with a full
independent recount of all 3,884 payloads.

---

## The miner's standing rules, as implemented

* **Skip-existing** — one `needs_pull()` decides. `.pkl` and `.empty` are covered; `.missing` is
  still owed.
* **Never-destroy** — every payload is temp-written then `os.replace`d, so a kill mid-write
  cannot leave a truncated file that later loads as short data. Nothing deletes a `.pkl`; the
  single `os.remove` in the file removes a `.missing` marker before its retry, and a test asserts
  that.
* **Tri-state units** — the distinction that has repeatedly cost this project data:

  | marker | meaning | refetched? |
  |---|---|---|
  | `.pkl` | data | no |
  | `.pkl.empty` | the feed genuinely returned nothing | no — but reported anyway |
  | `.pkl.missing` | the fetch FAILED | **yes, every run** |

  `.missing` must never be sticky. The EOD cache lost AAPL 2026 permanently to a sticky marker,
  and `test_tri_state_skip_existing` fails loudly if anyone collapses the three states into two.
  An `.empty` unit is *covered* but still listed in the coverage report, because a liquid name
  with zero prints on an alert day is likelier a bad date than a quiet tape.
* **Manifest as you go** — `tick_manifest.json` is rewritten atomically every 25 units and on
  every non-ok unit, so a kill loses at most the unit in flight.
* **Coverage report at the end** — `TICK_COVERAGE.json` in the cache, and the tracked copy at
  repo root.

### Schema

Payload is a self-describing dict: `schema` (**2**), `symbol`, `date`, `dte_cap`, `source`,
`alias_used`, `pulled_utc`, and `rows` (the DataFrame). Self-describing rather than
sidecar-described because there is no legacy to stay compatible with and a sidecar can be
separated from its data.

```python
import pickle
p = pickle.load(open(r"data/options_ticks/NVDA/NVDA-2025-01-06.pkl", "rb"))
p["rows"]          # DataFrame: expiration, strike, right, trade_timestamp, quote_timestamp,
                   # sequence, condition, ext_condition1-4, size, exchange, price,
                   # bid_size/bid_exchange/bid/bid_condition, ask_size/ask_exchange/ask/ask_condition
p["alias_used"]    # None, or the historical ticker these rows actually came from
```

**No column is dropped.** Narrowing is range-checked first and a value that will not fit keeps its
wide dtype and is NAMED in the manifest, so an unexpected range is a recorded fact rather than a
silent overflow. `symbol` is the one removal — constant within a unit, and it lives in the header.
A column dropped here would cost a full re-pull to recover; bytes were measured and are cheap.

---

## Tests

`python tests/test_tick_flow.py` — **6/6.** They pin the cache SEMANTICS, not the data: the
tri-state including the non-sticky `.missing`, slim losslessness (every narrowing round-trips),
out-of-range values keeping their wide type and being reported, the coverage states partitioning
the total, the book being read-only, and a source-level assertion that no code path deletes a
payload. Both new files parse clean under Python 3.11 (CI is 3.11, local is 3.13).

---

## Coverage census — MEASURED

`TICK_FLOW_COVERAGE.json` (tracked, repo root) and `data/options_ticks/TICK_COVERAGE.json`.

| | |
|---|---|
| units in scope | **3,885** |
| **units with data** | **3,884** |
| units empty | **1** (BUD 2024-01-10 — a real feed gap, autopsied above) |
| units missing | **0** |
| units not attempted | **0** |
| **coverage** | **1.0000** |
| prints | **70,288,482** |
| contracts traded | **433,725,746** |
| on disk | **4.721 GB** |
| symbols / dates | 186 / 1,574, 2016-01-19 → 2025-10-15 |

Per-year, and the shape is worth knowing before anyone designs a study on it — **2020-21 and
2024 carry over half the prints**, which is the retail options boom, not a collection artifact:

| year | units | prints | GB |
|---|---|---|---|
| 2016 | 309 | 1,253,431 | 0.085 |
| 2017 | 471 | 3,053,179 | 0.206 |
| 2018 | 351 | 3,243,785 | 0.218 |
| 2019 | 308 | 2,552,178 | 0.172 |
| 2020 | 379 | 11,862,474 | 0.796 |
| 2021 | 584 | 12,745,033 | 0.856 |
| 2022 | 173 | 2,285,965 | 0.155 |
| 2023 | 345 | 8,573,245 | 0.576 |
| 2024 | 604 | 15,526,081 | 1.043 |
| 2025 | 361 | 9,125,588 | 0.613 |

Largest names NVDA (7.86M prints), AAPL (6.07M), TSLA (5.10M); smallest CM (362 prints over 3
units). Per-symbol rollups for all 186 are in the tracked coverage file.

**Independent consistency check:** contracts traded summed from the ticks is **433.7M** against
the EOD cache's **396.0M** over the identical days — ticks are **9.5% higher**, which is the
expected direction and roughly the expected size, because the tick pull is uncapped while the EOD
figure stops at 200 DTE. Two independently-sourced measurements of the same quantity agreeing to
within their known methodological difference is the check that the join is not silently dropping
or duplicating prints.

### How the projection scored

| | projected | actual | error |
|---|---|---|---|
| prints | 43,476,624 | **70,288,482** | **−38%** |
| size | 2.93 GB | **4.721 GB** | **−38%** |

**The projection under-called by about 61% (actual/predicted 1.61).** It was flagged mid-run at
1.636 on completed units, so the direction was known before the end. The cause is the predictor:
prints were fitted against EOD chain VOLUME, and the EOD cache is capped at 200 DTE and
slim-filtered, so it cannot see the LEAPS breadth an uncapped tick pull collects — the same blind
spot that made the timing model 7.4× wrong on AAPL. **The go/no-go was never close** (4.7 GB is
1.9% of the free disk, against a 40 GB floor), but a projection that is 61% light would matter for
a job sized nearer its limit, and the honest lesson is that a predictor built from a FILTERED
cache systematically understates an UNFILTERED pull.

---

## What NOT to do with this cache

* **Do not quote a statistic from it.** Collection lane. O14's analysis half is a separate
  pre-registered job, and this project's own record is that a number computed before its
  pre-registration is the number that gets believed.
* **Do not treat print counts as "flow" without handling quote staleness** — see the caveat above.
* **Do not assume the alert-day set is a clean sample of anything.** These are the days the alert
  fired; they are selected, and R2 already established the alert's day-selection subtracts value.
  A flow statistic measured only on alert days has no control until non-alert days are pulled.
* **Do not re-pull to "fix" a `.missing`** by hand — re-run the miner; it retries them by design.
* **Do not join the 31 alias-supplied units to a symbol-keyed series without checking
  `alias_used`.** Those rows are FB's and UTX's, filed under META and RTX. The field exists so
  this is a fact on disk rather than something to rediscover.
* **Do not read the 2020-21 print concentration as a signal.** Over half the prints sit in
  2020-21 and 2024; that is the options-volume boom and it is a property of the market, not of
  the alerts.

---

## Reproduce / extend

```bash
# resume or top up (skip-existing; retries any .missing; safe to re-run any time)
python mine_tick_flow.py --workers 1

# census only, no feed calls
python mine_tick_flow.py --report-only

# the 20-unit stratified sample, if the projection needs redoing
python mine_tick_flow.py --sample 20 --sizes <alertday_sizes.json>

python tests/test_tick_flow.py     # 6/6
```

**Run it serially.** `--workers 1` is the measured configuration; anything higher fails on the
2020-21 megacap units, and the throughput gain is nil (see the table above). The run took ~46
minutes of feed time for the bulk 2,239 units after the fixes.

**Full test gate at close: 25 of 25 suites pass** (edge 259/259, tick-flow 6/6).
