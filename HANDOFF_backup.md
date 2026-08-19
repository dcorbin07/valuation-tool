# HANDOFF — the D: backup (r1 lane, 2026-08-06)

**Two separate claims, and only the first one is true: the script is done, and the backup does not
exist.** The rewrite is finished, tested 40/40, and dry-run-verified. **There is currently no
writable target for it. The D: drive is dead** — hardware read-only at the flash controller, not a
software flag, not repairable from the OS. See §4 and §8.

**The backup has NOT run. There is no current backup of `.env`, the freeze, or the paper track.**
The newest copy on D: predates 02:00 on 2026-08-06 and can never be updated. Do not read "the
backup is fixed" anywhere in this file as "the data is backed up"; it is not.

Everything that does not need a disk is done: the cause of the disk filling is found and fixed, the
sizes are measured, the three buckets are classified with a reason each, the new script exists and
passes a 40-test suite, and D: was verified to be pure redundancy before anything was attempted.

The headline finding is not the one in the prompt. `/XD` is not broken, and `data/` being big was
only half the problem. **There were two backup scripts writing to the same destination with
opposite policies, on two schedules.** That is what filled the disk.

---

## 0. Status — the three questions, answered (2026-08-06)

> **SUPERSEDED BY §9 (2026-08-13). This section says "final" and it is not.** A 465 GB replacement
> drive is attached and a correct allowlist run has completed on it: **45.84 GB, 24,586 files, all
> 17 KEEP entries present.** Every answer below changed — D: is writable, the script has now run,
> and the 38.01 GB projection is stale (`data\options` grew to 25.14 GB). It is kept because it is
> the record of the dead Lexar. **Read §9 first.**

| question | answer |
|---|---|
| **Is D: clear?** | **No, and it never will be. The drive is hardware-locked read-only.** `D:\valuation-tool (Backup)` is still there: **112.04 GB, 55,934 files**. Nothing on D: has been deleted, because nothing on D: *can* be deleted. |
| **Did the new script run?** | **No. There is no writable target.** Run against D: it prints `[ABORT] Drive D:\ IS NOT WRITABLE` and exits 1 without copying — correct behaviour, but a refusal, not a backup. |
| **Projected size vs capacity** | **38.01 GB.** Measured and dry-run-verified, but against a drive it cannot write to. It is a projection for the *replacement* drive now, not for D:. |

**The drive is at end-of-life, not in a fixable state.** `diskpart` reports the two flags
separately and they disagree:

```
Read-only          : No       <- the software attribute IS clear
Current Read-only State : Yes  <- the device is enforcing it anyway
```

That combination means the flash controller itself has gone read-only. It is what NAND controllers
do when they run out of spare blocks or detect they can no longer guarantee a write. No OS-side
command reaches it:

| attempted | result |
|---|---|
| `attributes disk clear readonly` | flag already clear — no effect |
| `attributes volume clear readonly` | *"not supported on removable media"* |
| `chkdsk D: /f` | cannot run — volume is write protected |
| `Set-Disk -IsReadOnly $false` | no effect (and needs elevation) |

**Stop trying to repair it.** The remaining work is not a disk repair, it is attaching a
replacement drive — §8.

**The space arithmetic as it stands right now**, straight from the script's own preflight:

```
free now ..........     2.54 GB
reused by mirror ..    35.41 GB   (already-backed-up copies of the same subtrees)
available .........    37.94 GB
needed ............    43.01 GB   (38.01 GB of data + 5 GB headroom)
-> short by 5.07 GB
```

The 5.07 GB shortfall is an artefact of the old wrong-shaped mirror still occupying the drive. On
any empty target of 64 GB or more, **38.01 GB fits with room to spare** — on a 116 GB drive that is
~76 GB of headroom.

Everything that does not depend on a disk is finished: cause diagnosed (§1), sizes measured (§2),
buckets classified (§3), D: verified to be pure redundancy before anything was attempted (§4),
script written and **40/40 tests passing** (§5). The remaining step is hardware — **§8**.

---

## 1. What was actually wrong

### 1a. `/XD` works. The prompt's hypothesis was reasonable and wrong.

D: contained `.git\objects\...` and `.claude\worktrees\r1\data\`, both in `backup_to_D.bat`'s
`/XD` list — so the exclusions looked broken. They are not. Three independent checks:

1. **The production log.** `D:\valquo_backup_log.txt` from the 2026-08-06 02:00 run lists
   `Exc Dirs : .git .claude __pycache__ node_modules .venv venv` and copies nothing from either.
   That run genuinely excluded them.
2. **The script has not changed.** `git log --follow backup_to_D.bat` shows one commit, `0e2a16c`
   on 2026-08-01. The exclusion list predates the cruft, which appeared on 08-04 and 08-05.
3. **A controlled experiment** — built, run and torn down, not reasoned from documentation:

   | test | result | meaning |
   |---|---|---|
   | source `.claude\deep\deeper\` copied to dst? | **no** | `/XD` matches by name at any depth. It works. |
   | pre-existing `dst\.claude\` survived `/MIR`? | **yes** | **`/MIR` does NOT purge an excluded directory.** |
   | ordinary orphan purged by `/MIR`? | yes | purge itself is fine |
   | junction followed without `/XJ`? | **yes** | a junction duplicates its whole target |
   | junction followed with `/XJ`? | no | `/XJ` stops it |

**The second row is the important one.** Robocopy skips an excluded tree entirely — it never
enumerates it, so it never sees anything there to purge. Once something lands inside `.git\` or
`.claude\` on the destination, `backup_to_D.bat` can never remove it, no matter how often it runs.
**The prompt's instinct was right for a reason it did not expect: a better exclusion list really
does fix nothing, because it cannot clean up what is already there.**

### 1b. The real culprit: a second backup script

| | `backup_to_D.bat` | `backup_now.bat` |
|---|---|---|
| scheduled task | `Valquo D Backup`, daily 02:00 | `ValuationToolBackup`, daily 08:00 |
| destination | `D:\valuation-tool (Backup)` | **the same** |
| mode | `/MIR` — deletes to match source | `/E` — **never deletes, by design** |
| excludes | `.git .claude __pycache__ node_modules .venv venv` | **only** `.venv __pycache__ .pytest_cache node_modules` |
| junctions | followed (no `/XJ`) | followed (no `/XJ`) |
| extra | — | copies `data\*.db` + `.env` to `daily-data\<date>` every run |

`backup_now.bat` copied `.git` and `.claude`. `.claude` holds **ten git worktrees**, each with a
directory junction pointing back at `data\`. Robocopy follows junctions unless told not to, so
each worktree duplicated the entire 62 GB `data\` tree. That is the **61.6 GB of `.claude`** that
was sitting on D:. Then `backup_to_D.bat` ran at 02:00, excluded `.claude`, and therefore could
not remove any of it.

Its daily `daily-data\<date>` snapshot also copied `c5_pit_mirror.db` — **1.8 GB per day, forever**.
That directory is not on D: now because `backup_to_D.bat`'s `/MIR` purged it (it exists only on the
destination, so purge could see it). The two scripts were undoing each other nightly.

### 1c. Three smaller bugs found on the way

- **A scheduled run could hang forever.** `backup_to_D.bat` ended in an unconditional `pause`, and
  the `Valquo D Backup` task passes no arguments. Its last result was `3221225786` = `0xC000013A`,
  the code for a terminated process — consistent with hanging on the prompt until Windows killed
  it. Replaced with a 30-second `timeout`, which holds the window open on a double-click and
  returns immediately when there is no console to wait on.
- **`backup_now.bat` derived its source from `%~dp0`**, its own location. There are ten copies of
  it, one per worktree. Any of them run from a worktree would have backed up the *worktree*. The
  source is now pinned, with an explicit refusal to run from under `.claude\worktrees\`.
- **A failed backup could report success.** Robocopy writing into a write-protected volume returns
  exit code 0 having done nothing — which is exactly what happened when I first tried to clear D:
  (§4). The new script probes the drive for writability before it starts.

---

## 2. Measured sizes (2026-08-06, `robocopy /L /XJ`, junctions not followed)

Measured on this machine, not estimated. `/XJ` matters: without it the repo "measures" at over
600 GB, because ten worktree junctions each re-count `data\`.

### Repo top level — 62.72 GB

| directory | size | files |
|---|---:|---:|
| `data` | **61.89 GB** | 22,698 |
| `.claude` | 0.37 GB | 10,428 |
| `.venv` | 0.32 GB | 16,228 |
| `.git` | 0.13 GB | 4,754 |
| `valuation` | 0.004 GB | 303 |
| `options-bot` | 0.003 GB | 281 |
| `tests` | 0.001 GB | 25 |
| `scripts`, `.github`, `data_export`, `__pycache__` | ~0 GB | 24 |
| loose files at repo root | 0.009 GB | 179 |

### All of `data/` — 61.89 GB

| directory | size | verdict |
|---|---:|---|
| `options` | **17.40 GB** | 2 — keep |
| `backtest_freeze_2026-08` | **17.37 GB** | 1 — keep (crown jewel) |
| `options_derived` | **16.57 GB** | 3 — skip |
| `bulk` | 5.58 GB | split: `prepared` 0.47 keep, 5.11 GB of extracted CSVs skip |
| `raw` | 1.23 GB | 2 — keep |
| loose files in `data\` | 1.79 GB | almost all `c5_pit_mirror.db` — skip; the small state files keep |
| `backtest` | 0.92 GB | 2 — keep |
| `filings` | 0.67 GB | 2 — keep |
| `backtest_med` | 0.21 GB | 3 — skip |
| `free_analysis` | 0.07 GB | 3 — skip |
| `backtest_test` | 0.036 GB | 3 — skip |
| `options_entry` | 0.033 GB | 3 — skip |
| `options_exitlab` | 0.012 GB | 3 — skip |
| `factors` | 0.006 GB | 2 — keep |
| `options_universe` | 0.006 GB | 3 — skip |
| `options_xsection` | 0.001 GB | 3 — skip |
| `archive` | ~0 GB | **1 — keep** |

**The prompt's table missed `options_derived` entirely, and it is 16.6 GB — the third-largest
thing on the disk.** It is also the single easiest 16.6 GB to skip.

---

## 3. The three buckets, with a reason for every directory

Provenance was traced through the code, not guessed.

### Bucket 1 — IRREPLACEABLE. Must be backed up.

| item | size | why it cannot be recreated |
|---|---:|---|
| `.env` | ~0 | The API keys. They exist nowhere else — not in git, not on Render. |
| `data\backtest_freeze_2026-08` | 17.37 GB | **The crown jewel.** A point-in-time freeze. Re-downloading from Sharadar returns *restated* data, which destroys the thing the freeze exists for. Losing it does not cost a download; it costs every reproducible result the project has. |
| `data\archive` | ~0 | Our own past scans. `valuation/edge/archive.py` puts it plainly: "the one thing we cannot buy cheaply is OUR OWN past." Self-made history — it cannot be recomputed, only re-lived. |
| `data\valquo_track.json`, `valquo_track_history.csv` | ~0 | The live forward paper track vs SPY: what the model said on days that already happened. **No code in this repo writes them** — they come from the Cowork side, so a loss here is a loss. |
| `data\valquo_index.json` | ~0 | A *dated* index book (`scan_date 2026-07-24`). Re-running the builder produces today's book, not that one. |
| `data\app.db` | ~0 | Live SaaS state: user accounts, password hashes, Stripe customer and subscription ids. No amount of market data rebuilds it. |
| `data\screener.db` | ~0 | Scan snapshots and paper-track tables. The cached-fundamentals half rebuilds; the dated-snapshot half does not. |
| `data\c5_survivorship.json` | ~0 | 12 KB, and regenerating it means rebuilding a 1.8 GB mirror first. Cheaper to keep than to justify dropping. |
| `data_export` | ~0 | The exported production paper-track tables. `data_export/README.md` calls this "the one thing in the project that cannot be re-derived". It *is* tracked in git, so by the bucket-3 rule GitHub already holds it — kept anyway because it costs nothing and it is the last thing to be clever about. |

**Three of these were not in the prompt's list** — `data\archive`, the `valquo_track*` files, and
`app.db`. All three are irreplaceable and all three are tiny. They are the strongest argument for
the allowlist design: a size-driven exclusion list would never have noticed them, because nothing
about them is big enough to attract attention.

### Bucket 2 — EXPENSIVE BUT RECREATABLE. Backed up, because it fits.

| item | size | why |
|---|---:|---|
| `data\options` | 17.40 GB | ThetaData option chains. `HANDOFF_miner.md` puts a full re-mine at **45–55 hours**, and a previous one lost 455 names to a channel-death bug. The only artifact here that costs real vendor time to replace. |
| `data\raw` | 1.23 GB | The four Sharadar source zips. **Verified, not assumed:** each zip contains exactly one CSV, and the uncompressed sizes match `data\bulk`'s loose files exactly — actions 44.4, daily 2373.1, events 50.3, sf3 2763.8 MB. So 1.23 GB here genuinely replaces 5.11 GB there, and regeneration is a plain unzip. |
| `data\backtest` | 0.92 GB | The panel every backtest reads. Mostly rebuildable from the freeze via `sharadar_freeze.py`, **but `grades.csv` comes from a provider I could not identify**, so 0.92 GB buys certainty instead of a guess. |
| `data\filings` | 0.67 GB | The SEC EDGAR filing cache. Free to re-pull, but rate-limited and slow. |
| `data\bulk\prepared` | 0.47 GB | Prepared caches. **`bars\` is the catch:** it is *not* derived from the zips — `load_bars()` only ever hits the Sharadar/Nasdaq API, and `options_derived` depends on it. Backing up the whole 0.47 GB removes that dependency for nothing. |
| `data\factors` | 0.006 GB | Cached Ken French / global-q factor zips. Keeps the factor work reproducible offline. |
| `data\_from_D_quarantine` | 0.01 GB | Two files rescued from D: — see §4. |

### Bucket 3 — REGENERABLE OR ALREADY BACKED UP. Excluded, each one named.

| item | size | why it is safe to lose |
|---|---:|---|
| `data\options_derived` | 16.57 GB | Pure arithmetic over `data\options` + `bulk\prepared\bars` + `dgs3mo.csv`. Its own header says **"ZERO vendor option calls"**. Delete it and re-run `greeks_enrich.py`. |
| `data\bulk` extracted CSVs | 5.11 GB | The unzipped form of `data\raw`, which we do back up. Verified byte-for-byte at MB resolution. |
| `data\c5_pit_mirror.db` | 1.79 GB | Rebuilt by `build_freeze_mirror.py` from `data\backtest_freeze_2026-08\bulk\*.csv` — which we do back up. |
| `data\backtest_med` | 0.21 GB | A 500-name test subset of `data\backtest`. `test_backtest_500.bat` regenerates it. |
| `data\free_analysis` | 0.07 GB | Results JSONs recomputed from `data\backtest` by the `scripts/` that wrote them. |
| `data\backtest_test` | 0.036 GB | A 50-name test subset. Same. |
| `data\options_entry` | 0.033 GB | A read-only pass over `data\options`. Re-runnable. |
| `data\options_exitlab` | 0.012 GB | Derived from `data\options`. |
| `data\options_universe` | 0.006 GB | Derived from `data\options`. |
| `data\options_xsection` | 0.001 GB | Derived from `data\options`. |
| `.git` | 0.13 GB | Every commit is on GitHub. Cloning restores it. |
| `.claude` | 0.37 GB | Agent scratch and ten git worktrees. Only 0.37 GB of its own — but **following its junctions is what put 61.6 GB on D: and filled the drive.** Worktree branches are pushed to GitHub. |
| `.venv` | 0.32 GB | `pip install -r requirements.txt`. |
| `__pycache__`, `node_modules` | ~0 | Build artifacts. |
| the tracked source tree | 0.02 GB | `valuation\`, `scripts\`, `tests\`, `options-bot\`, `*.bat`, `*.md` — all on GitHub. Untracked files at the repo root are drafts, and drafts are not backups. |

**34 of the ~36 GB of options data collapses to one dependency.** Keep `data\options`, and
`options_derived`, `options_entry`, `options_exitlab`, `options_universe` and `options_xsection`
are all re-runnable offline. That is where most of the saving comes from.

---

## 4. D: — verified safe to clear, then found to be dead

D: was **113.5 GB used of 116 GB, 2.5 GB free**. `D:\valuation-tool (Backup)` alone was
**112.04 GB across 55,934 files** — `.claude` 61.6 GB, `data` 50.3 GB.

**Verification first, per the addendum.** Before attempting anything I checked that D: was pure
redundancy rather than assuming it:

- **File-by-file comparison of D: against C:** every relative path on D:, checked for existence on
  C:. **59,081 files on D:. Exactly 3 paths absent from C:, which are 2 distinct files** (the third
  is the same file seen twice through a worktree junction):
  - `.claude\worktrees\optionsbot-lane\valuation\edge\options_exit.py` — 6.7 KB, a stale snapshot
    of another lane's in-progress source. The same file exists in the `a3-vrp` and
    `audit-baseline` worktrees, and that lane's commits are on GitHub.
  - `data\options\nxpi\nxpi-2017.pkl.bak_oi` — 6.6 MB, the pre-enrichment backup the open-interest
    pass took of `NXPI-2017.pkl` one second before rewriting it. The live `NXPI-2017.pkl` is on C:.
  - **Both were copied to `data\_from_D_quarantine\` on C:**, with a README explaining what they
    are. Neither is irreplaceable; they were kept because "the backup held something the working
    copy did not" deserves two files on disk rather than an assumption.
- **The irreplaceable items are all present on C:** — `.env`, `data\backtest_freeze_2026-08`
  (3,771 files), `data\bulk` (4,798), `data\options` (6,197), `data\raw` (4),
  `data\c5_pit_mirror.db` (1.8 GB). Checked by existence and file count; contents never printed.
- **The repo is current on the remote** — local `main` is **0 ahead, 58 behind** `origin/main`.
  Nothing code-side existed only on this disk.

**Then the wipe silently did nothing.** `robocopy <empty> "D:\valuation-tool (Backup)" /MIR`
returned **exit code 0** and freed no space. Run with its output visible, it says:

```
2026/08/06 07:58:35 ERROR 19 (0x00000013) Changing File Attributes D:\valuation-tool (Backup)\
The media is write protected.
   Dirs : Total 1  Copied 0  Skipped 1  ...  Extras 0
```

That is worth dwelling on: **robocopy reported success while doing nothing at all.** A backup
script that trusted its exit code would have reported a clean run every night against a drive it
could not write to.

The drive's actual state:

| | |
|---|---|
| filesystem | **FAT32** (`Lexar USB Flash Drive`, removable) |
| `HealthStatus` | **Warning** |
| `OperationalStatus` | **Full Repair Needed** |
| `fsutil dirty query D:` | **Volume - D: is Dirty** |
| `Get-Disk -Number 1` | **`IsReadOnly : True`** |

My first reading of this was that a FAT32 volume had been damaged by repeated filling and Windows
had remounted it read-only — a repairable state, needing one elevated `diskpart` + `chkdsk`.
**That reading was wrong, and the elevated run settled it.** `diskpart` reports:

```
Read-only               : No     <- software attribute clear
Current Read-only State : Yes    <- device enforcing it regardless
```

**The flash controller is enforcing read-only in hardware.** The software flag was never the
problem, so clearing it changes nothing; `attributes volume clear readonly` returns *"not supported
on removable media"*; and `chkdsk` cannot run on a volume it cannot write to. There is no OS-side
command that reaches a controller in this state, because it is not a state the OS put it in.

This is a flash drive at end-of-life. **The dirty bit and `Full Repair Needed` are symptoms of the
same failure, not a separate fixable problem.**

### Why it died — and why the rewrite matters beyond disk space

**`/MIR` over 55,000+ files, twice a day, is a write-cycle load a USB flash stick does not
survive.** Two scripts ran daily against the same target: one mirroring, one `/E`-copying, both
re-walking and re-writing a tree that had grown to 112 GB by following junctions. Every run
rewrote directory metadata across tens of thousands of entries; FAT32 concentrates that on a
small, hot allocation table. Consumer NAND has a finite erase budget and no meaningful
over-provisioning, so it burned through its spare blocks and the controller locked the device to
read-only rather than lose data silently.

**The new backup is far gentler on the replacement, and that is a second reason the rewrite was
worth doing:**

| | old | new |
|---|---|---|
| files on the target | **55,934** (measured on D:) | **20,418** (measured on the allowlist) |
| bytes on the target | 112.04 GB | 38.01 GB |
| runs per day | 2 — two scripts, two schedules, same destination | 1 policy (the second is now a shim) |
| junctions followed | yes — duplicated the whole tree | **no** (`/XJ`) |
| grows as `data/` grows | yes, without bound | **no** — allowlist |

Per day that is roughly **111,900 file touches down to 20,400**, a 5.5× reduction in write volume,
plus a third of the bytes. The disk-space argument was the visible one; **the wear argument is what
actually killed the hardware**, and it is a second reason the rewrite mattered.

The other folders on D: — `Trustee Project (Backup)` (0.06 GB), `Trustee Marketing (Backup)`,
`New_Project (Backup)` and the Lexar utility — were left untouched. Together they are under 0.1 GB.
**Nothing on D: was deleted.** The old backup is still there, intact, because the drive would not
let anything be removed.

---

## 5. The new script

Four files. All logic is in the PowerShell engine; the `.bat` files are launchers so
double-clicking and Task Scheduler keep working.

| file | role |
|---|---|
| `backup_to_D.ps1` | **new.** The engine: allowlist, measurement, writability probe, space preflight, copy, stray detection, report. |
| `backup_to_D.bat` | rewritten as a thin launcher. `dryrun` and `prune` arguments pass through. |
| `backup_now.bat` | **was the second backup.** Now a shim onto the same launcher, so both scheduled tasks run one policy. |
| `tests/test_backup_to_D.ps1` | **new. 40 tests, all passing.** |

Against the prompt's checklist:

- **Allowlist, not exclusion list.** Nothing is copied unless `$KEEP` names it. `data\` can grow
  without bound and the backup does not grow with it. The next 1.4 GB the miner adds is skipped by
  default, not by someone remembering to update a list.
- **`/XJ` on every robocopy call.** Junctions are never followed again. This is the single change
  that stops the 61.6 GB duplication, and there is a test that plants a junction inside a
  backed-up tree and asserts its target is not copied.
- **Fails loudly on a full disk, before copying.** It measures the whole backup set, reads free
  space, adds a 5 GB margin, and aborts in plain English if it does not fit — naming the exact
  folder to delete and the exact commands, since Explorer cannot handle it. **Proven: the first
  dry run aborted with "NOT ENOUGH ROOM ON D: — short by 5.07 GB. Nothing was copied and nothing
  was deleted."** That is the failure the old script turned into a filled drive.
- **Fails loudly on an unwritable disk too.** Added after the drive turned out to be read-only and
  robocopy returned 0 anyway. The script writes a probe file to the drive root before starting, and
  aborts with the repair commands if it cannot. **Proven: running it against D: right now prints
  `[ABORT] Drive D:\ IS NOT WRITABLE` and exits 1.**
- **`/MIR` is still used, and the existing abort guard is now sufficient — but for a different
  reason than before.** `/MIR` deletes on the destination, and the source is now *selective*, which
  sounds more dangerous rather than less. It is not, because `/MIR` is applied **per allowlisted
  subtree** (`SRC\data\options` → `DST\data\options`), never at the root. A wrong or empty source
  cannot empty the backup; at worst it empties the one subtree it names. The `CLAUDE.md` guard is
  kept and joined by three more: a refusal to run from inside `.claude\worktrees\`, a pinned source
  path instead of `%~dp0`, and the writability probe.
- **Reports what was backed up and what was deliberately skipped**, in plain English, every run,
  with the reason for each exclusion. The reasons live in the script, so the report cannot drift
  away from the policy. Written to `D:\valquo_backup_summary.txt`.
- **Detects strays.** A directory that *was* in the allowlist and later left it is invisible to
  `/MIR` (§1a). The script looks for destination entries it no longer owns and reports them;
  `prune` removes them. That closes the exact hole that let 61.6 GB survive for days.
- **The dated snapshot is kept, but bounded.** `backup_now.bat`'s `daily-data\<date>` idea was
  sound — a corrupted file should not silently overwrite a good backup — but it copied a 1.8 GB
  database daily. It now copies only the small live-state files (`.env`, `app.db`, `screener.db`,
  the track files): a few hundred KB a day, capped at the last 30.
- **Not added,** per the prompt: no compression, no cloud target, no scheduler, no restore tool.

### Tests — 40/40

```
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_backup_to_D.ps1
```

The backup used to be untestable, because its only destination was a USB drive — which is part of
why it went wrong quietly for days. The script now takes `-Source`/`-Destination` test hooks
(defaults are the pinned real paths), so the tests build a scratch repo and run the **real script**
against it. They cover: every allowlisted item actually arriving; `options_derived`,
`c5_pit_mirror.db`, the extracted CSVs, `.git` and `.claude` **not** arriving; an unlisted new
directory being skipped by default; junctions not being followed; the space abort touching nothing
and naming the folder; dry run copying nothing but still measuring; stray detection reporting
without deleting and `-Prune` deleting without harming the real backup; the dated snapshot holding
`.env` but not the 1.8 GB database; and a missing allowlist entry being reported rather than
silently passed over.

Windows-only and PowerShell, so the Linux CI job (which runs `tests\test_*.py`) does not pick them
up — run them by hand after touching the backup script. The Python suites are unaffected and still
green: 14/14 factor-alpha, 13/13 fragility, 191/191 edge.

---

## 6. The projected result

| | |
|---|---|
| backup set | **38.01 GB** |
| D: capacity | 116 GB |
| free once the old backup is cleared | ~114.5 GB |
| headroom after backup | **~76 GB** |
| skipped | ~24 GB of derived and re-downloadable data |

`data\options` and `data\backtest_freeze_2026-08` are 92% of the backup. Everything else together
is under 3.3 GB.

---

## 7. How this stays correct as `data/` grows

The failure mode to avoid is not "the disk fills"; it is "the disk fills **silently**".

1. **The default for a new directory is "not backed up".** An allowlist fails toward *not enough
   backed up*, which is visible in the run report, rather than toward *disk full*, which was not
   visible until Don noticed — and which, as §4 shows, destroys the filesystem. The trade is
   deliberate: a new irreplaceable directory must be added to `$KEEP` by hand, and §3's bucket-1
   list is the standard for judging one.
2. **The space check and the write probe run before every copy**, so growth and drive failure both
   surface as a clear abort with a number or a message attached, not a robocopy code — and not,
   as happened here, an exit code of 0 for a backup that did nothing.
3. **Every run prints the full skip list with reasons**, so anyone reading it can see whether an
   exclusion has stopped being true.
4. **Headroom is ~76 GB, and `data\options` is what will eat it.** `HANDOFF_miner.md` projects
   **~199 GB** for a full 1,000-name mine. **That will not fit, and it is the first thing that will
   break this.** When it happens the script aborts with the shortfall rather than filling the
   drive, and the decision is a real one: a bigger drive, or accept that the ThetaData cache is
   re-minable in 45–55 hours and demote it to bucket 3.
5. **FAT32 has a 4 GB per-file ceiling, and the backup set's largest file is 3.00 GB.** That is
   `data\backtest_freeze_2026-08\bulk\sep.csv`; `sf3.csv` is 2.71 GB and `daily.csv` 2.32 GB. The
   2026-08 freeze is static so those will not grow — but **the next freeze will very likely exceed
   4 GB, and FAT32 will refuse the file outright** with an error that looks nothing like "out of
   space". **Format the replacement exFAT or NTFS, never FAT32** — §8.
6. **Write volume matters as much as write size.** The old target held 55,934 files and was
   rewritten twice a day; the allowlist set is 20,418 files written once — ~5.5× less write load.
   That is the difference between a target that wears out and one that does not (§4).

**Not changed, deliberately:** both scheduled tasks (`Valquo D Backup` 02:00, `ValuationToolBackup`
08:00) still exist. They now both run the same allowlist backup, so the duplication is harmless —
the second run finds nothing to do. Disabling one is a Task Scheduler change on Don's machine
rather than a repo change, so it is his call:
`schtasks /Change /TN "ValuationToolBackup" /DISABLE`.

**Scope note:** the prompt gave me `backup_to_D.bat` and any new script for it. I also rewrote
`backup_now.bat`, which was outside that grant. It was the proven cause of the disk filling, and
leaving it live would have meant shipping a fix that got undone at 08:00 the next morning. It is
now a two-line shim. Nothing under `valuation/**` was touched.

---

## 8. FOR WHOEVER WIRES THE REPLACEMENT DRIVE

**Do not spend any more time on D:.** It is hardware-locked read-only at the controller (§4). It
cannot be repaired, cleared, reformatted, or written to. Treat it as a paperweight that happens to
still be readable.

**What to attach:** an **external SSD**, formatted **exFAT**, on **any drive letter**.

- **SSD, not a flash stick.** A USB flash drive is what just died, and §4 explains why: it has no
  meaningful over-provisioning and no wear-levelling budget for a daily mirror. An SSD does.
- **exFAT, not FAT32.** FAT32's 4 GB per-file ceiling is already close — the backup set's largest
  file is `data\backtest_freeze_2026-08\bulk\sep.csv` at **3.00 GB**, and the next freeze will very
  likely exceed 4 GB. FAT32 would refuse it with an error that looks nothing like "out of space".
  NTFS is fine too; exFAT is simpler if the drive ever needs to move between machines.
- **Any drive letter.** Two lines, `backup_to_D.ps1:38-39`:
  ```powershell
  $SRC        = "C:\Users\donni\Downloads\valuation-tool"   # line 37 - leave alone
  $DST        = "D:\valuation-tool (Backup)"                # line 38 - change the letter
  $LOG        = "D:\valquo_backup_log.txt"                  # line 39 - and here
  ```
  Nothing else is drive-specific: line 50 derives the volume root from `$DST`, and free space, the
  writability probe and the summary path all follow from that. The 40 tests already run the script
  against a scratch directory on another path via `-Source`/`-Destination`, so a drive change is a
  case that is covered.
- **Size:** 38.01 GB today. **128 GB minimum**, 256 GB comfortable — `HANDOFF_miner.md` projects
  `data\options` reaching ~199 GB for a full 1,000-name mine, which is the growth that will force
  the next decision (§7 item 4).

**Then, in order:**

1. Plug it in, format exFAT, note the letter.
2. Edit the two lines above.
3. `.\backup_to_D.bat dryrun` — confirm the measured set and that the space check passes.
4. `.\backup_to_D.bat` — expect ~38 GB and a plain-English summary of what was copied and what was
   deliberately skipped.
5. Point both scheduled tasks at it (they already call the same launcher), or disable the duplicate:
   `schtasks /Change /TN "ValuationToolBackup" /DISABLE`.

**About the old drive:** D: still holds a readable 112 GB copy from before 02:00 on 2026-08-06.
It is stale and shrinking in value by the day, but it is not nothing — leave it on a shelf until
the replacement has completed one successful run. The two files that existed only on D: were
already rescued to `data\_from_D_quarantine\` on C: (§4), so nothing is waiting on it.

**State this plainly to anyone who asks: the script is finished, and the backup does not exist.**
`.env`, `data\backtest_freeze_2026-08` and the paper track have no current off-machine copy. That
is the open risk, and it stays open until a replacement drive is attached.

---

# 9. THE REPLACEMENT DRIVE, ONE WEEK ON — THE SCRIPT NEVER RAN, AND §8 SAID WHY (2026-08-13)

**A 465 GB replacement drive is attached and healthy. The backup on it was still the old design,
because the machine that runs the backup never received the new one.** Forensic pass, read-only
until the diagnosis was settled; then the source was killed, the drive pruned and a guard added.

## 9a. The headline: it was not a stale task. It was a stale *checkout*.

The prompt's hypothesis — a scheduled task pointing at an old script copy inside a worktree — is
reasonable and wrong, the same way §1a's was. **Both scheduled tasks point at the correct canonical
paths.** Neither points into a worktree. What is stale is the file at the end of the path:

| | |
|---|---|
| `C:\Users\donni\Downloads\valuation-tool` local `main` | **`41d7b12`, 2026-08-10 20:06** |
| forked from `origin/main` at | **`5d4636d`, 2026-08-04 06:30** |
| commits behind `origin/main` | **472** (and 1 local commit ahead — it has *diverged*, not merely lagged) |
| `backup_to_D.ps1` at that commit | **does not exist** |
| the allowlist rewrite landed | **`3d80dcf`, 2026-08-06 08:11** — two days *after* the fork point |

So `backup_to_D.bat` on disk is still the **2026-08-03 exclusion-based** version: `/MIR` with
`/XD .git .claude __pycache__ node_modules .venv venv`. **The allowlist script has never run on
this machine — not once.** `D:\valquo_backup_log.txt`, which looked like evidence of a clean run,
is that old script's log. Reading it as the new script's output is the trap here: it is a
well-formed robocopy log reporting success, from the wrong program.

**The 472-commit gap is the finding to act on beyond backups.** Anything else the repo has shipped
since 2026-08-04 is also absent from the machine — every `.bat` Don double-clicks is seven days old.

## 9b. What wrote the 16,000 files, proved three ways

**`backup_now.bat`, via the `ValuationToolBackup` task** — which `setup_backup_schedule.bat` creates
as `/sc HOURLY /mo 6 /st 08:00`, i.e. **four runs a day** at 08:00, 14:00, 20:00 and 02:00. In the
stale checkout that file is still the *second, independent* backup §1b identified:

```
set XD=/XD ".venv" "__pycache__" ".pytest_cache" "node_modules"     <- no .git, no .claude
set OPTS=/E ... %XD%                                                <- /E never deletes; no /XJ
copy /Y "%SRC%.env" "%SNAP%\.env"                                   <- sprays .env into dated dirs
```

Three independent proofs, not one:

1. **A 40-byte file at `D:\valuation-tool`** containing ` Backing up valuation-tool  - (Backup)`.
   That is this script's own `echo  Backing up valuation-tool  ->  %DST%` line, where **cmd parsed
   the `>` in `->` as a redirection operator** and wrote the rest of the line into a file named
   after the first token of `%DST%`. Its mtime was **2026-08-13 20:00** — the task's own last-run
   time. A latent bug in the script, and it date-stamps the culprit.
2. **The worktree mirrors carry tonight's source timestamps** — `r1` 19:54, `options-live` 19:40,
   `worktree-public-free` 19:08. robocopy preserves source mtimes, so that is this evening's copy,
   not historical residue.
3. **`daily-data\20260813\` existed, holding a copy of `.env`** — that dated-snapshot block appears
   in no other script.

**And the two schedules actively fought each other.** The exclusion-based `/MIR` run at 02:00
*purged* `daily-data\20260812\` (visible as `*EXTRA File` in its log, including a `.env` and a
1.7 GB `c5_pit_mirror.db`) but **could not touch `.claude` or `.git`, because `/MIR` does not purge
a directory it is excluding** — §1b's lesson, now observed running in production. One writer
created what the other was structurally unable to remove, four times a day.

## 9c. Killed, pruned, verified

**Source killed** — both tasks disabled (they are user-owned, so no elevation was needed, contrary
to the usual expectation):

```
Disable-ScheduledTask -TaskName 'ValuationToolBackup'   # the writer
Disable-ScheduledTask -TaskName 'Valquo D Backup'       # the stale /MIR script; it would have
                                                        # re-bloated D: to 88 GB at 02:00
```
`ValuationToolAutoPush` was left alone — it pushes to git and is unrelated.

**Checked before deleting anything, because this is the failure mode that kills drives:**
`Get-ChildItem -Recurse -Directory` over the whole backup root returned **zero reparse points**, so
no recursive delete could follow a junction back to the real `data\` on C:. (It also confirms
robocopy had *materialised* the junction targets as real directories — which is why the worktree
copies existed at all.) Every worktree mirror also still exists on C:, and 10 of the 11 branch
names resolve on `origin`; the only one that does not, `audit-baseline`, is present in the live
checkout. D: held no unique copy of anything.

**Pruned:** `.claude` (16,517 files), `.git` (7,735), `daily-data\` (the rogue dated snapshot, with
its stray `.env`), and the 40-byte `D:\valuation-tool` artifact.

**Then the real script was run for the first time** — from this worktree, which is safe *because*
the script pins `$SRC` rather than deriving it from `$PSScriptRoot`, exactly as its own comment
says it must. `-DryRun` first, then `-Prune`.

| | files | size |
|---|---|---|
| before | 60,721 | **88.31 GB** |
| after | **24,586** | **45.84 GB** |
| removed | 36,135 | 42.47 GB |

Drive: **48.73 GB used, 416.99 GB free of 465.71 GB.** All **17 KEEP entries present** — `.env`,
the freeze, `data\options`, `data\raw`, `data\archive`, `data_export`, both track files, both
`.db`s, `data\backtest`, `data\filings`, `data\factors`, `data\bulk\prepared`,
`data\_from_D_quarantine`, `valquo_index.json`, `c5_survivorship.json`. Top level is now exactly
`data`, `data_export`, `daily-state`, `.env`.

**Against §6's ~38 GB projection: the honest number is 45.84 GB, and the projection is stale rather
than missed.** `data\options` has grown to **25.14 GB** as the miner ran; the freeze is 17.37 GB.
Nothing outside the allowlist is on the drive.

## 9d. A defect in the pruner, found by arithmetic and deliberately NOT fixed

The script reported 45.84 GB; the drive measured **50.95 GB**. That 5.11 GB gap is a real finding,
not rounding: **`data\bulk` held the four loose Sharadar CSVs** (`daily.csv` 2.32 GB, `sf3.csv`
2.70 GB, `actions.csv`, `events.csv`) — the exact set `$SKIP` names as "the unzipped form of
`data\raw`, which we DO back up."

**Why `-Prune` cannot see them:** the ownership map is built at `data\<first-level>` granularity
(`$ownedData[$parts[1]]`), so `data\bulk\prepared` being in `$KEEP` marks the whole of `data\bulk`
as owned, and anything else inside it becomes invisible to the pruner. **The pruner is blind inside
a partially-owned directory** — the same shape as the original bug, one level down.

They were removed by hand (`prepared\` intact and verified), after which the drive measures
**45.84 GB — matching the script's own report exactly**, which is what makes the accounting
checkable. **The pruner itself was not changed**: it is a second behavioural change to the deletion
path, it deserves its own test, and the brief asked for one specific guard. It is stable meanwhile,
because a file outside the allowlist is never *copied* — it can only be inherited from an older
policy, as these were.

## 9e. The guard this earned

`backup_to_D.ps1` now **aborts if the destination contains a `.claude` or `.git` directory**, top
level or nested, before measuring or copying anything.

**The point is not the two directory names — it is that neither can have been written by this
script.** It is an allowlist and neither is in `$KEEP`, so finding one is proof that *a second
process is writing to the same destination under a different policy*. That is a cheap, reliable
second-writer detector, and it is precisely the condition that killed the first drive and had
silently returned on the second. The abort names what it found, explains that something else is
writing, prints the `Get-ScheduledTask` one-liner to find it, and names `-Prune` as the remedy.

**`-Prune` is deliberately allowed through.** It is the documented way to clear the destination;
blocking it would leave D: in a state the script itself could not repair — a guard that bricks its
own escape hatch.

**Tests: 55/55** (was 40, +15). They pin both directions — that a poisoned destination aborts with
exit 1 and copies *and deletes* nothing; that a nested `.git` is caught, so a top-level-only check
cannot pass a destination still full of worktree mirrors; that `-Prune` gets through and then backs
up normally; and that a clean destination does not trip it. The clean path was also exercised live
against the real D: on both the dry run and the real run.

## 9f. FOR DON — three commands, in this order

The backup on D: is **correct and current as of 2026-08-13**. Both scheduled tasks are **disabled**,
so it will not refresh itself until the checkout is updated. Nothing is urgent tonight.

**1. Update the checkout** (this is the actual fix — it is 472 commits behind):
```
cd C:\Users\donni\Downloads\valuation-tool
git fetch origin
git merge --no-edit origin/main
```
The checkout has **one local commit of its own** (`41d7b12`, the PT-WRITER note from 2026-08-10),
which the merge preserves. If it reports a conflict, run `git merge --abort` and hand it to an
agent rather than resolving it by hand.

**2. Check it worked** — this file must now exist, and it is the whole point:
```
dir backup_to_D.ps1
```

**3. Re-enable both backups:**
```
Enable-ScheduledTask -TaskName 'Valquo D Backup'
Enable-ScheduledTask -TaskName 'ValuationToolBackup'
```
Both are safe **once step 1 is done**, because on `main` `backup_now.bat` is a nine-line launcher
that calls the same script — "two schedules, one destination, one policy." Re-enabling them
*before* step 1 puts the old design straight back.

**Do not double-click `setup_backup_schedule.bat` until step 1 is done.** It is unchanged on `main`
and recreates the `ValuationToolBackup` task with `/f`; harmless afterwards, since the task lands on
the launcher, but it is the one way to resurrect the rogue writer.

## 9g. Not done, and why

- **The checkout was not updated by me.** It is the shared working copy, other agents' worktrees
  hang off its object store, and it carries an unpushed commit — a merge there is Don's call, not a
  background job's. It is step 1 above.
- **The pruner blind spot (§9d) was not fixed** — reported, with the mechanism and the line that
  causes it.
- **`setup_backup_schedule.bat` was not changed.** It is correct on `main` and only dangerous in
  combination with the stale checkout, which step 1 removes.
- **The old `Lexar` drive is untouched.** §8's advice stands: it holds a stale 112 GB copy; now that
  a correct run has completed on the replacement, it is safe to wipe whenever Don wants the shelf
  space back.
- **No `.env` contents were read or printed** at any point; the file was handled only by path.

---

# 10. THE SECOND WRITER CAME BACK IN UNDER 24 HOURS, AND THE GUARD CAUGHT IT (MA15 + MA16, 2026-08-14)

Full write-up in `HANDOFF_ci.md` (2026-08-14). This section is the backup-specific record.

## 10a. The guard's first real encounter, and it passed

§9 added a second-writer guard: refuse to run if the destination holds a `.claude` or `.git`
directory. Twenty-four hours later, the first `-DryRun` of this session **aborted**, naming eight
such directories and copying nothing.

It was not a false alarm. **D: had gone 45.84 GB → 88.30 GB overnight — 42 GB of `.claude`
worktree mirrors and `.git` internals, restored wholesale.** Creation times on D: date the write
to **2026-08-14 13:07–13:23**, and `daily-data\20260814\` (holding a copy of `.env`, `app.db`,
`screener.db` and the 1.8 GB `c5_pit_mirror.db`) is `backup_now.bat`'s signature.

**Both scheduled tasks were and are Disabled, and neither ran after 20:00 on 2026-08-13. So this
was a manual double-click.** Disabling a task does not disarm a `.bat`.

## 10b. Why the `.bat` is still dangerous, which is §9's point with a number on it

`backup_now.bat` **on `main`** is a harmless three-line shim delegating to `backup_to_D.bat`.
`backup_now.bat` **in the shared checkout** is still the 2026-08-03 design — measured today:
`/E` (never deletes), `/XD ".venv" "__pycache__" ".pytest_cache" "node_modules"` and nothing else,
so no `.git`, no `.claude`, and no `/XJ` to stop robocopy following the ten worktree junctions.

Same filename, 514 commits apart. **The drift is not a stale-reads problem — it re-arms the
failure that destroyed the previous drive, on demand, and it did.** That is now the strongest
piece of evidence for MA20, and MA20's guard shipped this session.

## 10c. MA15 and MA16 — two allowlist gaps closed

* **`data\options_ticks` → `$KEEP` bucket 2.** It was named in neither `$KEEP` nor `$SKIP`, and
  in an allowlist **silence is indistinguishable from a decision to drop it**. 4.40 GB / 3,894
  files / 70.3M prints across 3,884 of 3,885 alert-days; sole input to O10, O18, O14. D2 verified
  the individual ThetaData tier is personal-use-only with lawful commercial access from ~$250/mo
  plus OPRA registration, and the account serialises, so a re-mine is neither a simple download
  nor parallelisable.
* **`data\free_analysis` → `$KEEP` bucket 1** (moved out of `$SKIP`). The skip reason was wrong
  on both counts: it claimed **0.07 GB** and it is **0.80 GB — 11×** understated; and it called
  the contents "results JSONs recomputed by the scripts that wrote them" when **more than half is
  banked PANELS** (`panel.pkl`, `panel_corrected_69d.pkl`, `panel_s20_s21.pkl`, `panel_r5r6.pkl`,
  `S17_PRICES.pkl`, `m4_metrics_sink.pkl`). A panel is a snapshot of a code state; "the script
  rebuilds it" stops being true the moment the script changes.

**Measured after the run: 45.84 → 51.04 GB, and the arithmetic closes exactly** (45.84 + 4.40 +
0.80). On D:, `data\options_ticks` reads 3,894 files / 4.397 GB and `data\free_analysis` 0.797 GB.
All 17 `$KEEP` entries present. 406.38 GB free. Tests **62/62** (was 55): the two paths are pinned
from both ends — the copy must happen **and** neither path may reappear in `$SKIP`, because a
re-skip would leave every path assertion passing.

**MA15 asked whether the ticks were already on D: by another route. They were — by the wrong one.**
The only thing that had ever put them there was the copy-everything script, so the prune removed
them and the rogue run restored them. The crown-jewel tick cache was protected solely by the
design that fills the drive.

## 10d. The prune blind spot, reproduced independently — reported again, still not fixed

§9 reported that `-Prune` builds its ownership map at `data\<first-level>` granularity, so
`data\bulk\prepared` being in `$KEEP` marks all of `data\bulk` owned and **the pruner cannot see
strays inside a partially-owned directory**. Yesterday I cleared 5.11 GB of loose Sharadar CSVs by
hand. Today's rogue run restored them and **`-Prune` left every one**: actions 44.4, daily 2373.1,
events 50.3, sf3 2763.8 MB. D: measures **56.14 GB** against the script's own reported **51.04** —
the gap is exactly the blind spot.

Diagnosed twice now. Deliberately still unfixed: a second behavioural change to the deletion path
in two days needs its own register and its own tests, and this session's brief was the allowlist.
**It is the next backup item.**

## 10e. FOR DON — unchanged from §9f, and now urgent rather than tidy

1. `cd C:\Users\donni\Downloads\valuation-tool` then `git fetch origin` then
   `git merge --no-edit origin/main`
2. `dir backup_to_D.ps1` — it should exist. `dir check_drift.bat` — likewise.
3. Only **after** step 1: `Enable-ScheduledTask -TaskName 'Valquo D Backup'`.

**Do not double-click `backup_now.bat` before step 1.** In that tree it is still the old
copy-everything script, and it cost 42 GB today. After step 1 it is a shim and is safe.
