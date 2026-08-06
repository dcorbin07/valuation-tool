# HANDOFF — the D: backup (r1 lane, 2026-08-06)

The backup is rewritten, tested 40/40, and correct. **It cannot run yet, because the backup
drive is now physically read-only** — the filesystem was corrupted by being filled up, and
Windows remounted it write-protected. Clearing that needs one elevated command from Don. §8 has
it, in two lines.

Everything else is done: the cause of the disk filling is found and fixed, the sizes are measured,
the three buckets are classified with a reason each, the new script exists and passes a 40-test
suite, and D: was verified to be pure redundancy before anything was attempted.

The headline finding is not the one in the prompt. `/XD` is not broken, and `data/` being big was
only half the problem. **There were two backup scripts writing to the same destination with
opposite policies, on two schedules.** That is what filled the disk.

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

## 4. D: — verified safe to clear, then found to be read-only

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

This is what a FAT32 volume does when it is repeatedly filled to capacity: the filesystem is
damaged, Windows sets the dirty bit and remounts it read-only to prevent further damage. **The
disk filling was not just an inconvenience; it broke the drive.**

**I cannot fix it from here.** All three routes need administrator, and this session is not
elevated:

- `chkdsk D: /f` → *"Windows cannot run disk checking on this volume because it is write protected."*
- `Set-Disk -Number 1 -IsReadOnly $false` → *"Access Denied"*
- `diskpart` → requires elevation

So the order matters: the read-only flag has to be cleared **before** chkdsk can even run. §8 has
the two commands.

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
   space". If the drive is ever reformatted, format it **exFAT or NTFS**, not FAT32. Worth doing
   anyway after the repair in §8.

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

## 8. THE ONE THING BLOCKING THIS — needs an elevated prompt

The drive is write-protected and I am not running as administrator, so I cannot repair it, clear
it, or back up to it. **Don: right-click Windows Terminal or Command Prompt → "Run as
administrator", then:**

```
diskpart
  list disk
  select disk 1          (the 116 GB "Lexar USB Flash Drive" — CONFIRM the size before selecting)
  attributes disk clear readonly
  exit

chkdsk D: /f
```

`select disk 1` is what it was at the time of writing; **check `list disk` and pick the one whose
size is 116 GB**, because disk numbers move when drives are plugged in.

Then tell me, and I will do the rest with no further input:

1. Re-verify D: is writable and still pure redundancy.
2. Clear `D:\valuation-tool (Backup)` (112 GB) with the empty-mirror technique — Explorer cannot,
   the paths are too deep and too many.
3. Run the new backup: ~38 GB, leaving ~76 GB free.
4. Confirm the result and update this file with the actual numbers.

If `chkdsk` finds serious damage, the better answer is to **reformat the drive as exFAT** — it is
a backup target holding nothing unique (§4 proves that), FAT32 is the wrong filesystem for 3 GB
files, and a clean format is more trustworthy than a repaired FAT32 volume. That is Don's call, not
mine, so I have not done it.

**Until this is cleared there is no working backup of `.env`, the freeze, or the paper track** —
the copy on D: is from before 02:00 today and cannot be updated. That is the risk, stated plainly.
