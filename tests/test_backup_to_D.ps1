<#
    Tests for backup_to_D.ps1. Run:
        powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_backup_to_D.ps1

    Windows-only and PowerShell, so the Linux CI job (which runs tests\test_*.py) does not
    pick these up. Run them by hand after touching the backup script.

    They exercise the real script against a scratch source and destination via its -Source /
    -Destination test hooks, so the copy, the junction handling, the space abort and the stray
    detection are all executed rather than reasoned about. The backup used to be untestable
    because its only destination was a USB drive; that is why it went wrong quietly.
#>
$ErrorActionPreference = "Continue"
$script:pass = 0
$script:fail = 0

function Check([string]$name, [bool]$ok, [string]$detail = "") {
    if ($ok) { Write-Host "  PASS  $name"; $script:pass++ }
    else     { Write-Host "  FAIL  $name $detail"; $script:fail++ }
}

$SCRIPT = Join-Path (Split-Path -Parent $PSScriptRoot) "backup_to_D.ps1"
if (-not (Test-Path -LiteralPath $SCRIPT)) { Write-Host "cannot find backup_to_D.ps1 at $SCRIPT"; exit 1 }

$ROOT = Join-Path $env:TEMP "valquo_backup_tests"
function Reset-Fixture {
    if (Test-Path -LiteralPath $ROOT) { Remove-Item -LiteralPath $ROOT -Recurse -Force -ErrorAction SilentlyContinue }
    $src = Join-Path $ROOT "src"; $dst = Join-Path $ROOT "dst"
    New-Item -ItemType Directory -Path $dst -Force | Out-Null

    # --- things the allowlist says to keep
    New-Item -ItemType Directory -Path "$src\data\backtest_freeze_2026-08\bulk" -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\data\options\aapl"                 -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\data\raw"                          -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\data\archive\scans"                -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\data\bulk\prepared\bars"           -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\data_export"                       -Force | Out-Null
    Set-Content "$src\.env"                                        "SECRET=x"     -Encoding utf8
    Set-Content "$src\data\backtest_freeze_2026-08\bulk\sep.csv"   "frozen"       -Encoding utf8
    Set-Content "$src\data\options\aapl\AAPL-2018.pkl"             "chain"        -Encoding utf8
    Set-Content "$src\data\raw\SHARADAR_DAILY.zip"                 "zip"          -Encoding utf8
    Set-Content "$src\data\archive\scans\2026-08-05.json.gz"       "scan"         -Encoding utf8
    Set-Content "$src\data\bulk\prepared\bars\AAPL.pkl"            "bars"         -Encoding utf8
    Set-Content "$src\data\app.db"                                 "users"        -Encoding utf8
    Set-Content "$src\data\valquo_track_history.csv"               "date,nav"     -Encoding utf8
    Set-Content "$src\data_export\paper_track_index.csv"           "track"        -Encoding utf8

    # --- things it must NOT copy
    New-Item -ItemType Directory -Path "$src\data\options_derived\aapl" -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\.claude\worktrees\r1"      -Force | Out-Null
    New-Item -ItemType Directory -Path "$src\.git\objects"              -Force | Out-Null
    Set-Content "$src\data\options_derived\aapl\AAPL-2018.pkl" "derived" -Encoding utf8
    Set-Content "$src\data\c5_pit_mirror.db"                   "mirror"  -Encoding utf8
    Set-Content "$src\data\bulk\daily.csv"                     "unzipped" -Encoding utf8
    Set-Content "$src\.git\objects\abc"                        "object"  -Encoding utf8

    return @{ Src = $src; Dst = $dst }
}
function Run-Backup([string]$src, [string]$dst, [string[]]$extra) {
    $a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$SCRIPT,"-Source",$src,"-Destination",$dst,"-MarginGB","0") + $extra
    $out = & powershell @a 2>&1
    return @{ Code = $LASTEXITCODE; Out = ($out -join "`n") }
}

Write-Host ""
Write-Host "backup_to_D.ps1 tests"
Write-Host ""

# ------------------------------------------------------------------ a real copy
$f = Reset-Fixture
$r = Run-Backup $f.Src $f.Dst @()
Check "a normal run exits 0" ($r.Code -eq 0) "(got $($r.Code))"
Check "crown jewel copied"        (Test-Path "$($f.Dst)\data\backtest_freeze_2026-08\bulk\sep.csv")
Check ".env copied"               (Test-Path "$($f.Dst)\.env")
Check "options chain copied"      (Test-Path "$($f.Dst)\data\options\aapl\AAPL-2018.pkl")
Check "raw zips copied"           (Test-Path "$($f.Dst)\data\raw\SHARADAR_DAILY.zip")
Check "archive copied"            (Test-Path "$($f.Dst)\data\archive\scans\2026-08-05.json.gz")
Check "prepared caches copied"    (Test-Path "$($f.Dst)\data\bulk\prepared\bars\AAPL.pkl")
Check "app.db copied"             (Test-Path "$($f.Dst)\data\app.db")
Check "track history copied"      (Test-Path "$($f.Dst)\data\valquo_track_history.csv")
Check "data_export copied"        (Test-Path "$($f.Dst)\data_export\paper_track_index.csv")

# the whole point: the big derived trees must be absent
Check "options_derived NOT copied (16.6 GB saved)" (-not (Test-Path "$($f.Dst)\data\options_derived"))
Check "c5_pit_mirror.db NOT copied"                (-not (Test-Path "$($f.Dst)\data\c5_pit_mirror.db"))
Check "unzipped bulk CSV NOT copied"               (-not (Test-Path "$($f.Dst)\data\bulk\daily.csv"))
Check ".git NOT copied"                            (-not (Test-Path "$($f.Dst)\.git"))
Check ".claude NOT copied"                         (-not (Test-Path "$($f.Dst)\.claude"))

# an allowlist, not an exclusion list: a NEW directory nobody listed is skipped by default
Check "an unlisted new directory is not copied" (-not (Test-Path "$($f.Dst)\data\brand_new_miner_output"))

# dated snapshot of the small live state
$stamp = Get-Date -Format "yyyy-MM-dd"
Check "dated state snapshot written"      (Test-Path "$($f.Dst)\daily-state\$stamp\.env")
Check "snapshot holds app.db too"         (Test-Path "$($f.Dst)\daily-state\$stamp\app.db")
Check "snapshot does NOT hold the 1.8 GB mirror db" (-not (Test-Path "$($f.Dst)\daily-state\$stamp\c5_pit_mirror.db"))

# the run must explain itself
Check "report names what was backed up" ($r.Out -match "WHAT WAS BACKED UP")
Check "report names what was skipped"   ($r.Out -match "WHAT WAS DELIBERATELY SKIPPED")
Check "report gives a reason for options_derived" ($r.Out -match "ZERO vendor option calls")

# ------------------------------------------------------------------ junctions
# This is the bug that filled the drive: a junction inside a copied tree pointing at a big
# directory, followed by robocopy, duplicating the whole target.
$f = Reset-Fixture
New-Item -ItemType Directory -Path "$($f.Src)\junction_target" -Force | Out-Null
Set-Content "$($f.Src)\junction_target\enormous.bin" "pretend 62 GB" -Encoding utf8
cmd /c mklink /J "$($f.Src)\data\options\link_to_target" "$($f.Src)\junction_target" 2>&1 | Out-Null
$r = Run-Backup $f.Src $f.Dst @()
Check "junction inside a backed-up tree is NOT followed" (-not (Test-Path "$($f.Dst)\data\options\link_to_target\enormous.bin"))

# ------------------------------------------------------------------ space abort
$f = Reset-Fixture
$a = @("-NoProfile","-ExecutionPolicy","Bypass","-File",$SCRIPT,"-Source",$f.Src,"-Destination",$f.Dst,"-MarginGB","999999")
$out = (& powershell @a 2>&1) -join "`n"
$code = $LASTEXITCODE
Check "impossible space requirement aborts with code 1" ($code -eq 1) "(got $code)"
Check "space abort says NOT ENOUGH ROOM"                ($out -match "NOT ENOUGH ROOM")
Check "space abort promises nothing was touched"        ($out -match "Nothing was copied and nothing was deleted")
Check "space abort copies nothing"                      (-not (Test-Path "$($f.Dst)\data\options\aapl\AAPL-2018.pkl"))
Check "space abort names the folder to delete"          ($out -match [regex]::Escape($f.Dst))

# ------------------------------------------------------------------ dry run
$f = Reset-Fixture
$r = Run-Backup $f.Src $f.Dst @("-DryRun")
Check "dry run exits 0"          ($r.Code -eq 0) "(got $($r.Code))"
Check "dry run copies nothing"   (-not (Test-Path "$($f.Dst)\data\options\aapl\AAPL-2018.pkl"))
Check "dry run still measures"   ($r.Out -match "TOTAL")

# ------------------------------------------------------------------ strays
# A directory that used to be in the allowlist and left it is invisible to /MIR, because
# robocopy never enumerates a tree it was not told to copy. 61.6 GB survived that way.
$f = Reset-Fixture
New-Item -ItemType Directory -Path "$($f.Dst)\data\options_derived\aapl" -Force | Out-Null
Set-Content "$($f.Dst)\data\options_derived\aapl\old.pkl" "left by an older policy" -Encoding utf8
New-Item -ItemType Directory -Path "$($f.Dst)\some_old_top_level" -Force | Out-Null
$r = Run-Backup $f.Src $f.Dst @()
Check "stray is reported"                  ($r.Out -match "NO LONGER IN THE BACKUP SET")
Check "stray subdirectory is named"        ($r.Out -match "options_derived")
Check "stray top-level dir is named"       ($r.Out -match "some_old_top_level")
Check "stray is NOT deleted without -Prune" (Test-Path "$($f.Dst)\data\options_derived\aapl\old.pkl")
$r = Run-Backup $f.Src $f.Dst @("-Prune")
Check "-Prune removes the stray subdirectory" (-not (Test-Path "$($f.Dst)\data\options_derived"))
Check "-Prune removes the stray top-level"    (-not (Test-Path "$($f.Dst)\some_old_top_level"))
Check "-Prune leaves the real backup intact"  (Test-Path "$($f.Dst)\data\options\aapl\AAPL-2018.pkl")

# ------------------------------------------------------------------ second-writer guard
# A .claude or .git under the backup root can only come from a writer that is not this script.
# That is what happened on 2026-08-13: backup_now.bat was a second schedule with /E and no /XJ,
# so it followed the worktree junctions, and the exclusion-based backup could not purge what it
# was excluding. The guard turns a silent two-writer race into a refusal that names the cause.
$f = Reset-Fixture
New-Item -ItemType Directory -Path "$($f.Dst)\.claude\worktrees\r1" -Force | Out-Null
Set-Content "$($f.Dst)\.claude\worktrees\r1\stray.txt" "left by another writer" -Encoding utf8
$r = Run-Backup $f.Src $f.Dst @()
Check "a .claude in the destination aborts the run"   ($r.Code -eq 1) "(got $($r.Code))"
Check "the abort names the offending directory"       ($r.Out -match "\.claude")
Check "the abort says something else is writing"      ($r.Out -match "ELSE is backing up")
Check "the abort points at the scheduled tasks"       ($r.Out -match "Get-ScheduledTask")
Check "the abort names -Prune as the remedy"          ($r.Out -match "-Prune")
Check "the aborted run copied NOTHING"        (-not (Test-Path "$($f.Dst)\data\backtest_freeze_2026-08\bulk\sep.csv"))
Check "the aborted run deleted NOTHING"       (Test-Path "$($f.Dst)\.claude\worktrees\r1\stray.txt")

# -Prune is the documented way out, so it must NOT be blocked -- otherwise the guard leaves the
# destination in a state the script itself cannot repair.
$r = Run-Backup $f.Src $f.Dst @("-Prune")
Check "-Prune is allowed through the guard"           ($r.Code -eq 0) "(got $($r.Code))"
Check "-Prune removes the second writer's .claude"    (-not (Test-Path "$($f.Dst)\.claude"))
Check "-Prune then backs up normally"                 (Test-Path "$($f.Dst)\data\backtest_freeze_2026-08\bulk\sep.csv")

# the same for .git, which is the other half of what the old backup left behind
$f = Reset-Fixture
New-Item -ItemType Directory -Path "$($f.Dst)\.git\objects" -Force | Out-Null
$r = Run-Backup $f.Src $f.Dst @()
Check "a .git in the destination aborts the run"      ($r.Code -eq 1) "(got $($r.Code))"

# a NESTED one counts: a worktree mirror carries its own .git, so a top-level-only check would
# pass a destination that is still full of them.
$f = Reset-Fixture
New-Item -ItemType Directory -Path "$($f.Dst)\data\options\aapl\.git" -Force | Out-Null
$r = Run-Backup $f.Src $f.Dst @()
Check "a NESTED .git aborts the run too"              ($r.Code -eq 1) "(got $($r.Code))"
Check "the nested path is named, not just the leaf"   ($r.Out -match "options")

# and the guard must stay quiet on a clean destination, or every normal run pays for it
$f = Reset-Fixture
$r = Run-Backup $f.Src $f.Dst @()
Check "a clean destination does not trip the guard"   ($r.Code -eq 0) "(got $($r.Code))"
Check "a clean run says nothing about a second writer" (-not ($r.Out -match "ELSE is backing up"))

# ------------------------------------------------------------------ missing source item
$f = Reset-Fixture
Remove-Item -LiteralPath "$($f.Src)\data\archive" -Recurse -Force
$r = Run-Backup $f.Src $f.Dst @()
Check "a missing allowlist entry is reported, not silent" ($r.Out -match "NOT FOUND ON C:")
Check "a missing allowlist entry does not fail the run"   ($r.Code -eq 0) "(got $($r.Code))"

if (Test-Path -LiteralPath $ROOT) { Remove-Item -LiteralPath $ROOT -Recurse -Force -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "$script:pass/$($script:pass + $script:fail) backup tests passed"
if ($script:fail -gt 0) { exit 1 } else { exit 0 }
