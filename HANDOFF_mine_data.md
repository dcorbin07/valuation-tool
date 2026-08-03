# HANDOFF — options cache miner: throughput fix + standalone runner

Full report for the `PROMPT_dataminer_fix.md` work. Miner lane only; no other agent's files
touched. Tests 89/89.

---

## How Don runs it (the point of this fix)

Double-click **`mine.bat`** in the worktree root, or:

```
cd C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs
mine.bat            REM runs in this window, shows progress, Ctrl-C to stop
mine.bat bg         REM runs hidden, returns immediately
```

Equivalent CLI forms:

```
python mine_options_cache.py
python -m valuation.edge.theta_bulk
```

It is **resumable** — every symbol-year already on disk is skipped, so closing the window and
reopening later costs nothing. It stops only when the universe is done, the disk floor (40GB
free) is hit, or you close it. **It is no longer driven by an agent session**, which is what
caused it to do ~10 names and stop.

Watch it: `data\options\MINING_PROGRESS.txt` (a `-> [n/1000] SYM ...` line when a name starts,
a completion line with per-name elapsed time when it ends), or `python mine_status.py`.

---

## Root cause of the ~17 min/name stalls

**It was response SIZE, not flakiness, and not rate limiting.** Measured directly:

| call | rows | time |
|---|---|---|
| BKNG, one quarter | 396,240 | **72.8s** (deadline was 75s) |
| BKNG, one month | 122,488 | 20.9s |
| AAPL, one quarter | 110,416 | 41.4s |
| AAPL, one month | 34,996 | 9.0s |

BKNG is the highest-priced US stock and carries an enormous strike ladder, so a *quarterly* span
sat right on the deadline and failed whenever the connection was under any load. It failed the
same way every run, which is why BKNG and NOW each came back missing exactly **four consecutive
years** rather than random ones — a signature of a systematic size limit, not a transient fault.

Three things then multiplied that into ~17 minutes per name:

1. **Gap years were retried inline on every run.** `partial` was not in the main loop's skip
   list, so a name with unrecoverable years was re-attempted *first*, before any new name.
2. **Failure cost was paid per quarter.** Each failing span burned `2 retries x 75s = 150s`
   before anything adapted, four times per year.
3. **The retry never terminated.** A `.missing` marker did not count attempts, so a doomed year
   was retried forever, every run.

**Explicitly ruled out:** throttling. A control test run after hours of pulling returned AAPL in
9.0s and BKNG in 20.9s — the connection was healthy; only the large spans failed.

---

## The fix

**Monthly chunks by default (was quarterly).** Smaller responses turn out to be *faster in
total*, not just safer: three monthly AAPL calls take 27s against 41.4s for the quarter. This
removes the failure entirely for large names rather than working around it.

**Per-name adaptive chunk size.** If a name still fails, the chunk halves (30d → 22d floor) and
**stays** halved for the rest of that name, so the discovery cost is paid once per name instead
of once per quarter.

**Per-name wall-clock budget (900s).** Past it the name is abandoned with whatever it has. One
pathological symbol can no longer consume an entire unattended run.

**Retry cap.** A `.missing` marker now counts attempts; after 2 failed runs the year is marked
`.exhausted` and never retried. Three marker states now mean three different things:

| marker | meaning | retried? |
|---|---|---|
| `.empty` | the feed genuinely has no data (pre-IPO, pre-rename) | never — counts as covered |
| `.missing` | fetch failed, attempts < 2 | yes, next run |
| `.exhausted` | failed 2+ times | never — this is what stops the blackhole |

**Partial names deferred.** The main loop skips them; the bounded retry pass at the end handles
them, so they are attempted once per run rather than first.

---

## The bigger bug this uncovered: 158 good names were being silently excluded

While verifying the skips I found names like **CAH, FIX, ABNB, ACN, ADP, AEP, AFL, ALL, AMT,
AON, APD** marked `SKIP - no data` and permanently removed from the universe. They are not empty:
**CAH returns 12,456 rows and FIX 4,298** for a single probe month.

The cause: `name_is_viable` treated an absent frame as "the feed has nothing", but an absent
frame also results from a probe fetch that *failed* — exactly the large-chain timeout above. A
transient failure was therefore being recorded as a permanent verdict of "illiquid".

Viability now returns three states — viable / thin / **unknown** — and an unknown name is left
out of the manifest entirely so the next run re-probes it, rather than inheriting a verdict the
data never supported. **158 wrongly-condemned names have been cleared and will be re-screened.**

This matters for the brief's framing: the note that "the liquid universe naturally plateaus well
under 1,000" was substantially *this bug*, not genuine illiquidity. The real plateau is not yet
known and will be visible once the re-probe completes.

---

## Throughput — measured over 72 completed names, not extrapolated from one

An earlier draft of this file quoted **4.2 min/name** from a single fast name (NDAQ). That was
optimistic by about 50%. With 72 full-history names now on the clock the real figures are:

| case | measured |
|---|---|
| **Fresh name, full 10-year history** | **mean 5.4 min, median 6.0 min** (last 30: mean 6.4) |
| p10 / p90 of the same set | 0.1 min (mostly cached) / 9.0 min |
| slowest completed name | 12.5 min |
| Already-cached name | instant (manifest skip) |
| Genuinely thin / empty name | 5–20s (one probe month, then skipped) |
| Gap-heavy name | **bounded at 900s** then abandoned, versus unbounded before |

**Plan with ~6.4 min for a fresh 10-year name (~38s per symbol-year), not 4.2.**

End-to-end queue rate is better than the per-name figure suggests, because most queue positions
are cheap: the queue advanced **9 → 236 in 413 minutes of mining — ~1.8 min per position, about
33 positions screened per hour**. 65 names were rejected as thin along the way, each costing
seconds rather than minutes.

**Projected wall clock:** ~764 positions remain at ~1.8 min each ≈ **23 hours**, and the mix
downstream skews thinner (cheaper) while the 158 re-probes add back some full pulls — so
**20–30 hours** of continuous running is the honest range. It is resumable, so that is elapsed
time across as many sittings as you like.

---

## The fix did not reach `main` on its first push — now unblocked

Worth recording, because it would have silently stranded this work. The repo auto-lands any
pushed `worktree-*` branch via `.github/workflows/land-agent-branch.yml`, and that job had been
**failing on a merge conflict in `HANDOFF_STATUS.md`** — two lanes appended a new section at the
top of the same file on the same day. The workflow does exactly what it should on a conflict
(abort, leave `main` untouched), so nothing broke; it just meant the miner commit sat on the
branch looking shipped.

Resolved by merging `origin/main` into the branch and keeping **both** sections (lazy-prices
first, miner/A2 second — they are independent lanes, not competing edits). `test_edge.py` is
**133/133** on the merged tree, so the CI test gate passes too.

Cheap check for next time: `git merge-tree --write-tree origin/main HEAD` reports a conflict
without touching anything. Do not assume a green push means a landed merge.

---

## Current state

**186 of 1,000 cached** (183 complete, 3 partial, 53 skipped as too illiquid) at queue position
236, **1,815 year-files, 11.4GB**. Liquidity of what was kept: median 101 tradeable
contracts/day, thinnest 42, richest 897. Still running.

Partial (missing years, retried by the end-of-run pass, then `.exhausted`):
`BKNG [2018-2021]`, `NOW [2020-2023]`, `BP [2016, 2019-2023, 2025]`.

Skipped as untradeable: overwhelmingly foreign ADRs with wide US option spreads (BBVA, HDB,
HSBC, ING, MFG, MUFG, PBR, RY) plus names failing the 15% spread cut (BLK, KLAC, LIN, LRCX).
That is the intended cut.

Raw cache is gitignored and stays on disk — **0 files under `data/` are tracked**. No research,
signals or backtests have been run on this data; A3 and the small/mid-cap backtest are the next
session's work.
