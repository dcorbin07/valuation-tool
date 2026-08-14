<#
    Valquo -> D: backup engine.

    POLICY: back up what cannot be recreated, not what is large.

    This is an ALLOWLIST. Nothing is copied unless it is named in $KEEP below. That is a
    deliberate reversal of the old design, which copied everything and tried to exclude the
    big directories -- a race the exclusion list always loses, because data\ grows faster
    than anyone remembers to update the list. D: filled twice that way.

    Every excluded directory is named in $SKIP with the reason it is safe to lose. An
    unexplained exclusion is how something irreplaceable gets dropped later, so the run
    prints both lists in plain English every time.

    Usage (normally you want the .bat, which just calls this):
        powershell -File backup_to_D.ps1              # measure, check space, back up
        powershell -File backup_to_D.ps1 -DryRun      # measure and report, copy nothing
        powershell -File backup_to_D.ps1 -Prune       # also delete destination dirs that
                                                      # are no longer in the allowlist
#>
param(
    [switch]$DryRun,
    [switch]$Prune,
    # Test hooks. The real run never passes these -- the defaults below are the pinned paths.
    # They exist so test_backup_to_D.ps1 can exercise the copy, report and prune logic against
    # a scratch tree, which is the only way to test any of it when D: is not available.
    [string]$Source,
    [string]$Destination,
    [int]$MarginGB = 5
)

$ErrorActionPreference = "Stop"

# The source is PINNED, not derived from $PSScriptRoot. There are ten git worktrees under
# .claude\worktrees\, each with its own copy of this script and a junction back to data\;
# a copy that backed up "its own folder" would back up a worktree instead of the real thing.
$SRC        = "C:\Users\donni\Downloads\valuation-tool"
$DST        = "D:\valuation-tool (Backup)"
$LOG        = "D:\valquo_backup_log.txt"
$TESTMODE   = $false
if ($Source -and $Destination) {
    $SRC = $Source; $DST = $Destination
    $LOG = Join-Path $Destination "backup_log.txt"
    $TESTMODE = $true
}

$MARGIN_GB  = $MarginGB   # never fill the drive to the brim; leave this much headroom
$SNAP_KEEP  = 30          # dated copies of the tiny live-state files to retain

$DRIVE_ROOT = [System.IO.Path]::GetPathRoot($DST)          # "D:\"
$DRIVE_LTR  = $DRIVE_ROOT.Substring(0,1)                   # "D"
# The summary sits beside the backup on the backup drive. Under test the drive root is C:\,
# which is not writable, so keep it inside the destination instead.
$SUMMARY    = if ($TESTMODE) { Join-Path $DST "backup_summary.txt" }
              else           { Join-Path $DRIVE_ROOT "valquo_backup_summary.txt" }

# ---------------------------------------------------------------- what we back up, and why
# Bucket 1 = irreplaceable. Bucket 2 = recreatable, but expensive enough to be worth the space.
$KEEP = @(
    @{ P = ".env";                          B = 1; Why = "the API keys. They exist nowhere else -- not in git, not on Render." }
    @{ P = "data\backtest_freeze_2026-08";  B = 1; Why = "THE CROWN JEWEL. A point-in-time freeze: re-downloading it from Sharadar returns RESTATED data, so losing it does not cost a download, it costs every reproducible result the project has." }
    @{ P = "data\archive";                  B = 1; Why = "our own past scans. Self-made history -- it cannot be bought or recomputed, only re-lived." }
    @{ P = "data\valquo_track.json";        B = 1; Why = "the live forward paper track vs SPY. A record of what the model said on days that already happened." }
    @{ P = "data\valquo_track_history.csv"; B = 1; Why = "the paper track's history rows. Same reason -- forward record, not derivable." }
    @{ P = "data\valquo_index.json";        B = 1; Why = "a DATED index book. Re-running the builder today produces today's book, not that one." }
    @{ P = "data\app.db";                   B = 1; Why = "live SaaS state: user accounts, password hashes, Stripe customer ids. No market data can rebuild it." }
    @{ P = "data\screener.db";              B = 1; Why = "scan snapshots and paper-track tables. The cache half rebuilds; the snapshot half does not." }
    @{ P = "data\c5_survivorship.json";     B = 1; Why = "12 KB, and regenerating it means rebuilding a 1.8 GB mirror first. Cheaper to keep." }
    @{ P = "data_export";                   B = 1; Why = "the exported copy of the production paper-track tables -- the project's own note calls this the one thing that cannot be re-derived. It IS tracked in git, so GitHub already holds it; kept anyway because it costs nothing and it is the last thing anyone should be clever about." }

    @{ P = "data\options";                  B = 2; Why = "ThetaData option chains. Re-mining is 45-55 hours of vendor pulls, and a previous re-mine lost 455 names to a channel-death bug." }
    @{ P = "data\raw";                      B = 2; Why = "the four Sharadar source zips. 1.2 GB here replaces 5.1 GB of extracted CSVs in data\bulk -- verified: each zip holds exactly one CSV of the matching size." }
    @{ P = "data\bulk\prepared";            B = 2; Why = "prepared caches. bars\ in particular needs a Sharadar API pull to rebuild -- it is NOT derivable from the zips -- and options_derived depends on it." }
    @{ P = "data\backtest";                 B = 2; Why = "the panel every backtest reads. Mostly rebuildable from the freeze, but grades.csv comes from a provider I could not identify, so 0.9 GB buys certainty." }
    @{ P = "data\filings";                  B = 2; Why = "the SEC EDGAR filing cache. Free to re-pull but rate-limited and slow, and 0.7 GB is nothing." }
    @{ P = "data\factors";                  B = 2; Why = "cached Ken French / global-q factor zips. Tiny, and it keeps the factor work reproducible offline." }
    @{ P = "data\_from_D_quarantine";       B = 2; Why = "two files that existed only on D: before the 2026-08-06 rebuild; rescued to C: so the backup is pure redundancy." }
)

# ---------------------------------------------------------------- what we deliberately skip
$SKIP = @(
    @{ P = "data\options_derived";  GB = 16.6; Why = "pure arithmetic over data\options + bulk\prepared\bars + dgs3mo.csv. Its own header says 'ZERO vendor option calls'. Re-runnable offline." }
    @{ P = "data\bulk (loose CSVs)";GB = 5.1;  Why = "the unzipped form of data\raw, which we DO back up. Verified byte-for-byte at MB resolution: actions 44.4, daily 2373.1, events 50.3, sf3 2763.8." }
    @{ P = "data\c5_pit_mirror.db"; GB = 1.8;  Why = "rebuilt by build_freeze_mirror.py from data\backtest_freeze_2026-08\bulk\*.csv, which we DO back up." }
    @{ P = "data\backtest_med";     GB = 0.21; Why = "a 500-name test subset of data\backtest. Regenerated by test_backtest_500.bat." }
    @{ P = "data\backtest_test";    GB = 0.04; Why = "a 50-name test subset. Same." }
    @{ P = "data\free_analysis";    GB = 0.07; Why = "results JSONs recomputed from data\backtest by the scripts\ that wrote them." }
    @{ P = "data\options_entry";    GB = 0.03; Why = "a read-only pass over data\options. Re-runnable." }
    @{ P = "data\options_exitlab";  GB = 0.01; Why = "same -- derived from data\options." }
    @{ P = "data\options_universe"; GB = 0.01; Why = "same -- derived from data\options." }
    @{ P = "data\options_xsection"; GB = 0.00; Why = "same -- derived from data\options." }
    @{ P = ".git";                  GB = 0.13; Why = "every commit is on GitHub. Cloning restores it." }
    @{ P = ".claude";               GB = 0.37; Why = "agent scratch and TEN git worktrees, each with a junction back to data\. It is only 0.37 GB of its own, but following those junctions put 61.6 GB on D: and filled the drive. Worktree branches are pushed to GitHub." }
    @{ P = ".venv";                 GB = 0.32; Why = "pip install -r requirements.txt." }
    @{ P = "__pycache__ / node_modules"; GB = 0.00; Why = "build artifacts." }
    @{ P = "the tracked source tree"; GB = 0.02; Why = "valuation\, scripts\, tests\, options-bot\, *.bat, *.md -- all on GitHub. Anything untracked at the repo root is drafts, and drafts are not backups." }
)

# Destination entries this script legitimately owns, beyond the $KEEP paths.
$OWNED_EXTRA = @("daily-state", "backup_log.txt", "backup_summary.txt")

# ---------------------------------------------------------------------------- helpers
function Get-SizeBytes([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return 0 }
    if (-not (Get-Item -LiteralPath $path -Force).PSIsContainer) {
        return (Get-Item -LiteralPath $path -Force).Length
    }
    # robocopy /L walks fast and copes with paths past MAX_PATH; /XJ so junctions are never
    # followed -- that is the bug that filled D: twice.
    $out = robocopy $path "NULL_DEST_DOES_NOT_EXIST" /L /S /XJ /NJH /BYTES /NFL /NDL /R:0 /W:0 2>$null
    foreach ($l in $out) { if ($l -match '^\s*Bytes\s*:\s+(\d+)') { return [int64]$Matches[1] } }
    return 0
}
function GB([int64]$b) { [math]::Round($b / 1GB, 2) }
function Say([string]$m) { Write-Host $m; Add-Content -LiteralPath $script:LogBuf -Value $m -ErrorAction SilentlyContinue }

$script:LogBuf = Join-Path $env:TEMP "valquo_backup_run.txt"
Set-Content -LiteralPath $script:LogBuf -Value "" -Encoding utf8

Say ""
Say "=============================================================="
Say " Valquo backup to D:      $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Say " Policy: back up what cannot be recreated, not what is large."
if ($DryRun) { Say " MODE: DRY RUN -- nothing will be copied." }
Say "=============================================================="

# ---------------------------------------------------------------------------- guards
if (-not $TESTMODE) {
    if (-not (Test-Path -LiteralPath (Join-Path $SRC "CLAUDE.md"))) {
        Say ""
        Say "[ABORT] The source does not look like the Valquo repo:"
        Say "        $SRC"
        Say "        CLAUDE.md is missing. Refusing to mirror from a wrong or half-populated"
        Say "        folder, because that would empty the backup."
        exit 1
    }
    if ($SRC -match '\\\.claude\\worktrees\\') {
        Say "[ABORT] This is running against a git worktree, not the real checkout. Stopping."
        exit 1
    }
}
if (-not (Test-Path -LiteralPath $DRIVE_ROOT)) {
    Say ""
    Say "[ABORT] Drive $DRIVE_ROOT was not found. Plug in the backup drive and run this again."
    Say "        Nothing was copied and nothing was deleted."
    exit 1
}
# A full FAT32 volume can corrupt and Windows then remounts it read-only. That is what
# happened on 2026-08-06: 'Full Repair Needed', dirty bit set, disk IsReadOnly. Copying into
# it silently does nothing, so check before doing 38 GB of work and reporting success.
if (-not $TESTMODE -and -not $DryRun) {
    $probe = Join-Path $DRIVE_ROOT "_valquo_write_probe.tmp"
    try { [System.IO.File]::WriteAllText($probe, "probe"); [System.IO.File]::Delete($probe) }
    catch {
        Say ""
        Say "  [ABORT] Drive $DRIVE_ROOT IS NOT WRITABLE."
        Say "          $($_.Exception.Message.Trim())"
        Say ""
        Say "  Nothing was copied. This usually means the filesystem was damaged by being"
        Say "  filled up, and Windows remounted it read-only to stop further damage."
        Say "  Check with:   Get-Volume -DriveLetter $DRIVE_LTR"
        Say "  Repair it from an ADMINISTRATOR prompt:"
        Say "      chkdsk ${DRIVE_LTR}: /f"
        Say "  and if it is still read-only afterwards:"
        Say "      diskpart -> select disk <n> -> attributes disk clear readonly"
        Say ""
        exit 1
    }
}

# ------------------------------------------------------------------ second-writer guard
# A .claude or .git directory under the backup root cannot have been put there by THIS script.
# This is an allowlist and neither is in $KEEP, so finding one is proof that something else is
# writing to the same destination under the opposite policy -- and that is the exact failure
# that killed the first drive.
#
# What it caught on 2026-08-13: backup_now.bat was still a SECOND, independent backup on its own
# schedule. It mirrored the whole tree with /E (which never deletes) and without /XJ (so robocopy
# followed all ten worktree junctions and copied data\ once per worktree). The exclusion-based
# backup that ran afterwards could not undo any of it, because /MIR does not purge a directory it
# is excluding. Two schedules, one destination, opposite policies -- and the drive fills.
#
# So the check is not really about these two directories. It is a cheap, reliable detector for a
# second writer, and a backup that quietly runs alongside one is reporting a success it cannot
# support. -Prune is deliberately allowed through: it is the documented remedy, and blocking it
# would leave the destination in a state the script itself could not repair.
if (Test-Path -LiteralPath $DST) {
    $poison = @()
    foreach ($n in @(".claude", ".git")) {
        if (Test-Path -LiteralPath (Join-Path $DST $n)) { $poison += $n }
    }
    # Nested copies count too -- a worktree mirror carries its own .git, and a check that only
    # looked at the top level would pass a destination that is still full of them.
    Get-ChildItem -LiteralPath $DST -Recurse -Directory -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -eq ".claude" -or $_.Name -eq ".git" } |
        ForEach-Object { $poison += $_.FullName.Substring($DST.Length).TrimStart('\') }
    $poison = @($poison | Sort-Object -Unique)

    if ($poison.Count -gt 0) {
        Say ""
        Say "  Found $($poison.Count) director$(if ($poison.Count -eq 1) { 'y' } else { 'ies' }) named .claude or .git in the destination:"
        foreach ($p in ($poison | Select-Object -First 8)) { Say "      $p" }
        if ($poison.Count -gt 8) { Say "      ... and $($poison.Count - 8) more" }
        if (-not $Prune) {
            Say ""
            Say "  [ABORT] The destination contains directories this script never writes."
            Say "          It is an ALLOWLIST -- .claude and .git are not in it -- so something"
            Say "          ELSE is backing up to $DST under a different policy."
            Say "          Backing up alongside a second writer reports a success it cannot support,"
            Say "          and .claude holds the worktree junctions that filled the last drive."
            Say ""
            Say "  Do this, in order:"
            Say "    1. Find the other writer. Check the scheduled tasks and what they actually run:"
            Say "         Get-ScheduledTask | Where-Object { `$_.TaskName -match 'backup' } |"
            Say "           ForEach-Object { `$_.TaskName; `$_.Actions.Execute }"
            Say "       Every task must land on backup_to_D.bat. If one runs a different script,"
            Say "       or an OLD copy of this one, that is the writer -- disable it."
            Say "    2. Clear what it left behind, then re-run:"
            Say "         powershell -File backup_to_D.ps1 -Prune"
            Say ""
            Say "  Nothing was copied and nothing was deleted."
            exit 1
        }
        Say "  -Prune was given, so these are treated as strays and removed below."
    }
}

# ---------------------------------------------------------------------------- measure
Say ""
Say "Measuring what needs to be backed up (this takes a minute) ..."
Say ""
$rows = @()
$total = [int64]0
$missing = @()
foreach ($k in $KEEP) {
    $full = Join-Path $SRC $k.P
    if (-not (Test-Path -LiteralPath $full)) { $missing += $k.P; continue }
    $b = Get-SizeBytes $full
    $total += $b
    $rows += [pscustomobject]@{ Path = $k.P; Bucket = $k.B; Bytes = $b; Why = $k.Why }
}

Say "  BACKING UP"
Say "  ----------"
foreach ($r in ($rows | Sort-Object -Property @{e='Bucket'}, @{e='Bytes'; Descending=$true})) {
    Say ("  [{0}] {1,-34} {2,8} GB" -f $r.Bucket, $r.Path, (GB $r.Bytes))
}
Say ("      {0,-34} {1,8} GB   <- TOTAL" -f "", (GB $total))
if ($missing.Count) {
    Say ""
    Say "  NOT FOUND ON C: (listed in the allowlist but absent -- check whether this is expected):"
    foreach ($m in $missing) { Say "    - $m" }
}

# ---------------------------------------------------------------------------- space check
$drive     = Get-PSDrive -Name $DRIVE_LTR
$free      = [int64]$drive.Free
# Space currently held by the subtrees we are about to mirror over is recycled by the copy,
# so it counts as available. Anything else on D: does not.
$reusable  = [int64]0
foreach ($r in $rows) {
    $d = Join-Path $DST $r.Path
    if (Test-Path -LiteralPath $d) { $reusable += (Get-SizeBytes $d) }
}
$available = $free + $reusable
$required  = $total + ([int64]$MARGIN_GB * 1GB)

Say ""
Say "  SPACE ON $DRIVE_ROOT"
Say ("    free now .......... {0,8} GB" -f (GB $free))
Say ("    reused by mirror .. {0,8} GB   (already-backed-up copies of the same subtrees)" -f (GB $reusable))
Say ("    available ......... {0,8} GB" -f (GB $available))
Say ("    needed ............ {0,8} GB   ({1} GB of data + {2} GB headroom)" -f (GB $required), (GB $total), $MARGIN_GB)

if ($required -gt $available) {
    $short = GB ($required - $available)
    Say ""
    Say "  [ABORT] NOT ENOUGH ROOM ON $DRIVE_ROOT -- short by $short GB."
    Say ""
    Say "  Nothing was copied and nothing was deleted. The backup is exactly as it was."
    Say ""
    Say "  To make room, delete the old backup folder and run this again:"
    Say "      $DST"
    Say ""
    Say "  Explorer will choke on it (tens of thousands of files in deep folders, and paths"
    Say "  longer than Explorer will open), so delete it with robocopy instead:"
    Say "      mkdir `"%TEMP%\empty`""
    Say "      robocopy `"%TEMP%\empty`" `"$DST`" /MIR"
    Say "      rmdir /s /q `"$DST`""
    Say ""
    exit 1
}
Say "    -> fits."

if ($DryRun) {
    Say ""
    Say "  DRY RUN: stopping here. Nothing was copied."
    exit 0
}

# ---------------------------------------------------------------------------- copy
Say ""
Say "Copying ..."
if (-not (Test-Path -LiteralPath $DST)) { New-Item -ItemType Directory -Path $DST -Force | Out-Null }
Set-Content -LiteralPath $LOG -Value "Valquo backup $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -Encoding utf8

$failed = @()
foreach ($r in $rows) {
    $s = Join-Path $SRC $r.Path
    $d = Join-Path $DST $r.Path
    $isDir = (Get-Item -LiteralPath $s -Force).PSIsContainer
    if ($isDir) {
        # /MIR so a file deleted on C: eventually leaves the backup; /XJ so junctions are
        # never followed. Scoped to ONE allowlisted subtree, so a bad path cannot wipe the rest.
        robocopy $s $d /MIR /XJ /R:1 /W:3 /MT:16 /NP /NFL /NDL /NJH `
                 /XF "*.pyc" ".fuse_hidden*" /LOG+:$LOG | Out-Null
    } else {
        $sDir = Split-Path -Parent $s
        $dDir = Split-Path -Parent $d
        $name = Split-Path -Leaf $s
        robocopy $sDir $dDir $name /XJ /R:1 /W:3 /NP /NFL /NDL /NJH /LOG+:$LOG | Out-Null
    }
    $rc = $LASTEXITCODE
    if ($rc -ge 8) { $failed += "$($r.Path) (robocopy code $rc)" ; Say ("  FAILED  {0}  (robocopy code {1})" -f $r.Path, $rc) }
    else           { Say ("  ok      {0}" -f $r.Path) }
}

# --------------------------------------------- dated copy of the tiny irreplaceable state
# Guards against a corrupted file quietly overwriting a good backup. Only the small live-state
# files -- a few hundred KB a day -- and capped, so it cannot become the next thing that fills D:.
$stamp = Get-Date -Format "yyyy-MM-dd"
$snap  = Join-Path (Join-Path $DST "daily-state") $stamp
New-Item -ItemType Directory -Path $snap -Force | Out-Null
foreach ($f in @(".env", "data\app.db", "data\screener.db", "data\valquo_track.json",
                 "data\valquo_track_history.csv", "data\valquo_index.json", "data\c5_survivorship.json")) {
    $p = Join-Path $SRC $f
    if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination $snap -Force -ErrorAction SilentlyContinue }
}
$snaps = @(Get-ChildItem -LiteralPath (Join-Path $DST "daily-state") -Directory -Force | Sort-Object Name)
if ($snaps.Count -gt $SNAP_KEEP) {
    foreach ($old in $snaps[0..($snaps.Count - $SNAP_KEEP - 1)]) { Remove-Item -LiteralPath $old.FullName -Recurse -Force -ErrorAction SilentlyContinue }
}

# ---------------------------------------------------------------------------- strays
# A directory that WAS in the allowlist and later left it does not get removed by /MIR --
# robocopy skips excluded trees entirely, which is exactly how 61.6 GB of .claude survived
# every "mirror" for days. So look for them explicitly.
$ownedTop = @{}
foreach ($k in $KEEP)      { $ownedTop[($k.P -split '\\')[0]] = $true }
foreach ($o in $OWNED_EXTRA) { $ownedTop[$o] = $true }
$ownedData = @{}
foreach ($k in $KEEP) { $parts = $k.P -split '\\'; if ($parts[0] -eq 'data' -and $parts.Count -gt 1) { $ownedData[$parts[1]] = $true } }

$strays = @()
foreach ($e in (Get-ChildItem -LiteralPath $DST -Force -ErrorAction SilentlyContinue)) {
    if (-not $ownedTop.ContainsKey($e.Name)) { $strays += $e.FullName }
}
$dataDst = Join-Path $DST "data"
if (Test-Path -LiteralPath $dataDst) {
    foreach ($e in (Get-ChildItem -LiteralPath $dataDst -Force -ErrorAction SilentlyContinue)) {
        if (-not $ownedData.ContainsKey($e.Name)) { $strays += $e.FullName }
    }
}

# ---------------------------------------------------------------------------- report
Say ""
Say "=============================================================="
Say " WHAT WAS BACKED UP"
Say "=============================================================="
foreach ($r in ($rows | Sort-Object -Property @{e='Bucket'}, @{e='Bytes'; Descending=$true})) {
    Say ("  {0}  ({1} GB)" -f $r.Path, (GB $r.Bytes))
    Say ("      {0}" -f $r.Why)
}
Say ("  plus a dated copy of the small live-state files in daily-state\{0} (last {1} kept)" -f $stamp, $SNAP_KEEP)

Say ""
Say "=============================================================="
Say " WHAT WAS DELIBERATELY SKIPPED, AND WHY IT IS SAFE TO LOSE"
Say "=============================================================="
$skipTotal = 0
foreach ($s in $SKIP) {
    $skipTotal += $s.GB
    Say ("  {0}  (~{1} GB)" -f $s.P, $s.GB)
    Say ("      {0}" -f $s.Why)
}
Say ("  Skipped roughly {0} GB." -f [math]::Round($skipTotal,1))

if ($strays.Count) {
    Say ""
    Say "=============================================================="
    Say " ON D: BUT NO LONGER IN THE BACKUP SET"
    Say "=============================================================="
    Say "  These are leftovers from an older policy. A mirror does NOT remove them, because"
    Say "  robocopy skips trees it is not told to copy. They will sit there forever until"
    Say "  something removes them."
    foreach ($s in $strays) { Say "    $s" }
    if ($Prune) {
        Say ""
        $empty = Join-Path $env:TEMP "valquo_empty_dir"
        New-Item -ItemType Directory -Path $empty -Force | Out-Null
        foreach ($s in $strays) {
            Say "  removing $s"
            robocopy $empty $s /MIR /R:0 /W:0 /NP /NFL /NDL /NJH | Out-Null
            Remove-Item -LiteralPath $s -Recurse -Force -ErrorAction SilentlyContinue
        }
        Say "  strays removed."
    } else {
        Say ""
        Say "  Re-run with -Prune to delete them."
    }
}

Say ""
Say "=============================================================="
$freeAfter = (Get-PSDrive -Name $DRIVE_LTR).Free
# Best-effort: a summary we cannot write is not a reason to call a good backup a failure.
try { Copy-Item -LiteralPath $script:LogBuf -Destination $SUMMARY -Force -ErrorAction Stop }
catch { Write-Host "  (could not write the summary to $SUMMARY -- the backup itself is unaffected)" }
if ($failed.Count) {
    Say " [WARN] Backup finished, but these did not copy cleanly:"
    foreach ($f in $failed) { Say "        $f" }
    Say ("        {0} now has {1} GB free. Detail: {2}" -f $DRIVE_ROOT, (GB $freeAfter), $LOG)
    exit 1
}
Say (" [OK] Backup complete. {0} GB backed up, {1} GB free on {2}." -f (GB $total), (GB $freeAfter), $DRIVE_ROOT)
Say ("      Summary: {0}   File detail: {1}" -f $SUMMARY, $LOG)
Say "=============================================================="
exit 0
