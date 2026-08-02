# HANDOFF — unattended ThetaData cache mining

Separate from `HANDOFF_STATUS.md` on purpose: this session is a **pure data-pull**, and mixing it
into the shared handoff buries the research state.

**Status: RUNNING.** No research, signals or backtests have been run on this data — per the
prompt, A3 (VRP arm) and the small/mid-cap backtest (roadmap 22b) happen on this cache when Don
is back.

---

## One-line status

**Target raised to 1,000 names** (updated brief). ~30 cached, 0 partial, ~5.8GB on disk at the
time of writing; ~3 min/name → roughly **45–55 hours** for the full 1,000. Disk projects to
~199GB at megacap scale against 322GB free, and mid/small caps are far smaller, so the real
figure lands well below that. A guard stops the run cleanly below 40GB free.

Check it any time:

```powershell
cd C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs
python mine_status.py
```

Greppable progress: `data/options/MINING_PROGRESS.txt` (lines read `N of 1000 names cached`).
Per-name manifest with years, gaps and skip reasons: `data/options/cache_manifest.json`.

Restart after any interruption with `python mine_options_cache.py` — it skips everything already
on disk, so a kill costs at most the year in flight.

---

## What is being pulled

| | |
|---|---|
| Universe | Top **1,000** optionable US names, market-cap ranked most-liquid-first |
| Reach | Megacaps through the liquid mid/small-cap tier — the high-IV movers worth testing |
| Years | 2016–2025, ten complete years each (2026 excluded — year in progress) |
| Already had | The 55 names from the earlier overnight run, all inside this universe, so none are re-pulled |
| Disk | ~199MB/name at megacap scale; guard stops the run below 40GB free |

### Where the cache lives — two locations, only one current

* `data/options/<SYM>/<SYM>-<YEAR>.pkl` — **the current cache.** 63 name folders as of writing.
* `data/bulk/prepared/theta/` — **superseded.** 15 folders, 28MB, left over from the phase-1
  per-day puller. Nothing reads it. If a folder count ever looks wrong, check which of these two
  is being counted; that discrepancy has already caused one false alarm.

A folder containing only `<SYM>-<YEAR>.pkl.empty` (e.g. SKHY) is correct, not a gap: it records
that the feed genuinely has no data for that name-year, so it counts as covered and is never
re-fetched. A `.missing` marker is the opposite — a fetch that FAILED, which is retried on the
next run and reported as a gap.

---

## Two design decisions worth knowing before anyone backtests on this

### 1. The cache filter is deliberately LOOSER than the backtest's entry filter

This is the one thing here that could silently corrupt every future result.

`options_fill` screens **entries** at OI≥100 / volume≥10 / spread≤25%, and deliberately does
**not** re-apply that at exit — you must be able to exit a contract you already own after it goes
illiquid, otherwise the backtest gets to abandon its losers, which is survivorship bias wearing a
different hat.

Filtering the *cache* at those entry thresholds would delete exactly those exit quotes from disk,
and every future run on this cache would inherit that bias invisibly. So the row filter drops
only information-free rows: no two-sided quote **and** no open interest **and** no volume, or
spreads above 300% (placeholders, not markets).

Verified before launch: on AAPL 2019 it drops **0 of 203,666 rows** and preserves all **82,461**
low-OI-but-quoted rows a trade would need to exit.

Junk is excluded at the **name** level instead — see below.

### 2. Ranking is a market-cap proxy, corrected by measured liquidity

Ranking on true options liquidity would need a chain pull across all 15,669 optionable names
before the first useful byte is cached. ThetaData's all-symbol flat file would answer it in one
call but requires a **PROFESSIONAL** subscription — verified, this account is Standard and it
returns `PERMISSION_DENIED`.

So market cap orders the queue, and reality corrects it: after a name's **first** year is cached,
its actual option liquidity is measured, and names too thin to trade are abandoned before their
remaining nine years are pulled. A bad proxy costs one year, not ten. The thresholds it applies are in the next section.

### The screen, and the mis-measurement that nearly defeated it

Thresholds sit at the **permissive end** of the brief's ranges — near-ATM OI ≥500, daily option
volume ≥100, median spread ≤15% — because the whole point of reaching past the megacaps is to
capture high-IV movers, and the tight end of each range would exclude exactly those.

**Spread is measured only on contracts with a real premium (mid ≥ $0.50).** This matters more
than any threshold. Measured across every quoted contract, the median sweeps in far-OTM lottery
tickets where a one-cent tick on a five-cent mid reads as 20% — which is not what a 35-delta,
45–75 DTE call pays. On that metric **RKLB scored 18.2% and was rejected**, despite 8,198
contracts/day and 1,821 ATM OI — and the brief names RKLB explicitly as the kind of name that
should pass. On real premium it is **8.7%** and passes. AAPL goes 6.3% → 3.4%, INTC 10.5% → 5.0%.

Near-the-money is approximated by the **top decile of open interest** rather than distance from
spot, which avoids needing a per-name spot series just to screen.

Names skipped under the earlier, superseded metric (HSBC, SKHY, SPCX) were cleared from the
manifest so they are re-judged under these criteria.

---

## Bugs found and fixed while setting this up

1. **Years ran sequentially** — ~18 min/name, ~133 hours for the universe. Now 4-concurrent per
   name (the Standard tier's limit), ~3 min/name.
2. **Miner exited instantly with "no THETADATA_API_KEY"** — the provider's key fallback searches
   the CWD and the package parent, neither of which is the main checkout when running from a
   worktree. `.env` is now loaded from the repo explicitly.
3. **`mine_status.py` reported "thinnest kept 0"** — it was including *skipped* names in the
   liquidity spread, so a name that had been correctly rejected looked like one that was kept.
   Fixed to report only names actually cached.

---

## Rules being observed

* Raw cache is gitignored and stays on disk (licensed Sharadar/ThetaData data is never committed
  — verified: 0 files under `data/` are tracked).
* Only code, the manifest tooling and this handoff are committed.
* No research run on the new names. That is deliberate and is the next session's work.
