$ErrorActionPreference = 'SilentlyContinue'
$ROOT = "C:\Users\donni\.claude\jobs\7819c8eb\tmp\sc2"
$SRC  = "C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs\git_push.bat"
$HOME_DIR = "C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs"

function Setup {
  param([switch]$Conflict, [switch]$RedTests)
  Set-Location "C:\"
  if (Test-Path $ROOT) { Remove-Item -Recurse -Force $ROOT }
  New-Item -ItemType Directory -Force "$ROOT\bare" | Out-Null
  New-Item -ItemType Directory -Force "$ROOT\repo" | Out-Null
  git init -q --bare "$ROOT\bare"
  Set-Location "$ROOT\repo"
  git init -q -b main .
  git config user.email t@t.co; git config user.name t
  git remote add origin "$ROOT\bare"
  New-Item -ItemType Directory -Force tests | Out-Null
  if ($RedTests) { "import sys" | Out-File -Encoding ascii tests\test_edge.py
                   "sys.exit(1)"  | Out-File -Encoding ascii -Append tests\test_edge.py }
  else           { "print('ok')"  | Out-File -Encoding ascii tests\test_edge.py }
  "base" | Out-File -Encoding ascii shared.txt
  git add -A; git commit -q -m base; git push -q -u origin main
  git checkout -q -b worktree-agent
  "agentwork" | Out-File -Encoding ascii agent_file.txt; git add -A; git commit -q -m a1
  if ($Conflict) { "agentver" | Out-File -Encoding ascii shared.txt; git add -A; git commit -q -m aconf }
  git checkout -q main
  "mainmoved" | Out-File -Encoding ascii main_file.txt; git add -A; git commit -q -m m1
  if ($Conflict) { "mainver" | Out-File -Encoding ascii shared.txt; git add -A; git commit -q -m mconf }
  Copy-Item $SRC "$ROOT\repo\git_push.bat"
}

# Invoke by FULL PATH: the script does `cd /d "%~dp0"` itself, so it lands in the scratch repo
# regardless of the caller's working directory. That was the harness bug last session.
function RunScript { & cmd.exe /c "`"$ROOT\repo\git_push.bat`" quiet" 2>&1 }

$pass = @{}

Write-Output "=== 1. DIVERGED branch (old FF-only script silently skipped these) ==="
Setup
$before = (git rev-list --count main)
RunScript | ForEach-Object { "   | $_" }
$after = (git rev-list --count main)
git cat-file -e main:agent_file.txt 2>$null; $landed = $?
$remoteOk = ((git -C "$ROOT\bare" rev-parse main) -eq (git rev-parse main))
Write-Output "   main commits $before -> $after ; agent work on main: $landed ; remote updated: $remoteOk"
$pass['diverged_merges'] = ($landed -and $remoteOk -and ($after -gt $before))

Write-Output ""
Write-Output "=== 2. RED TESTS must block the push ==="
Setup -RedTests
RunScript | ForEach-Object { "   | $_" }
$remoteSame = ((git -C "$ROOT\bare" rev-parse main) -eq (git rev-parse main))
Write-Output "   pushed despite red tests: $remoteSame  (want False)"
$pass['red_blocks_push'] = (-not $remoteSame)

Write-Output ""
Write-Output "=== 3. CONFLICT must abort, report, block push ==="
Setup -Conflict
RunScript | ForEach-Object { "   | $_" }
# Exclude the harness own untracked copy of git_push.bat: on conflict the script correctly
# bails BEFORE its git add -A, so that file is legitimately still untracked.
$dirty = ((git status --porcelain) | Where-Object { $_ -notmatch "git_push.bat" } | Measure-Object -Line).Lines
$mh = Test-Path "$ROOT\repo\.git\MERGE_HEAD"
$remoteSame3 = ((git -C "$ROOT\bare" rev-parse main) -eq (git rev-parse main))
Write-Output "   dirty=$dirty MERGE_HEAD=$mh pushed=$remoteSame3  (want 0 / False / False)"
$pass['conflict_aborts'] = (($dirty -eq 0) -and (-not $mh) -and (-not $remoteSame3))

Write-Output ""
Write-Output "=== VERDICT ==="
foreach ($k in $pass.Keys) { Write-Output ("   {0,-20} {1}" -f $k, $(if ($pass[$k]) {'PASS'} else {'FAIL'})) }
$all = -not ($pass.Values -contains $false)
Write-Output "   ALL SCENARIOS PASS: $all"
Set-Location $HOME_DIR
