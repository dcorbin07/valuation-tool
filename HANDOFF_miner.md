# HANDOFF — unattended ThetaData cache mining

Separate from `HANDOFF_STATUS.md` on purpose: this session is a **pure data-pull**, and mixing it
into the shared handoff buries the research state.

**Status: RUNNING.** No research, signals or backtests have been run on this data — per the
prompt, A3 (VRP arm) and the small/mid-cap backtest (roadmap 22b) happen on this cache when Don
is back.

---

## One-line status

**29 of 500 names cached; 3 skipped as too illiquid (HSBC, SKHY, SPCX); 0 partial; 5.3GB on
disk** as of ~80 minutes in. Running at ~3 min/name → roughly **25–30 hours** for the full 500.

Check it any time:

```powershell
cd C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs
python mine_status.py
```

Greppable progress: `data/options/MINING_PROGRESS.txt` (lines read `N of 500 names cached`).
Per-name manifest with years, gaps and skip reasons: `data/options/cache_manifest.json`.

Restart after any interruption with `python mine_options_cache.py` — it skips everything already
on disk, so a kill costs at most the year in flight.

---

## What is being pulled

| | |
|---|---|
| Universe | Top **500** optionable US names, market-cap ranked most-liquid-first |
| Reach | Megacaps down to ~$27B (#100 SNDK, #300 FIX, #500 LPLA) |
| Years | 2016–2025, ten complete years each (2026 excluded — year in progress) |
| Already had | The 55 names from the earlier overnight run, all inside this universe, so none are re-pulled |

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
remaining nine years are pulled. A bad proxy costs one year, not ten. Thresholds: ≥5 tradeable
contracts/day (against the real entry screen) and ≥100 days with a chain.

That check is working — HSBC, SKHY and SPCX have already been dropped.

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
