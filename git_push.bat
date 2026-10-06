@echo off
setlocal enableextensions
rem ============================================================
rem  Saves your changes and pushes them to GitHub. Run anytime
rem  after you've connected once. Works with Git for Windows OR
rem  GitHub Desktop's built-in git. Secrets (.env, *.db) are
rem  never pushed. Always pushes commits that aren't on GitHub
rem  yet, even if there are no new file edits this run.
rem ============================================================
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. Use GitHub Desktop, or run connect_github.bat first. & goto :done )

"%GIT%" rev-parse --is-inside-work-tree >nul 2>nul || ( echo Not connected yet - run connect_github.bat first. & goto :done )
"%GIT%" remote get-url origin >nul 2>nul || ( echo No GitHub remote yet - run connect_github.bat first. & goto :done )

rem --- Sync before pushing ---------------------------------------------------------------
rem  MA20. This script runs daily and never fetched, so it could not tell that the folder had
rem  fallen behind GitHub: once main diverges its push is rejected as a non-fast-forward, and
rem  the handler below used to call that a login problem and exit 0 - four green Task Scheduler
rem  days with nothing pushed. It first gained an ALARM here; the alarm was right and changed
rem  nothing, so the divergence simply got reported daily instead of fixed.
rem
rem  So this now runs the CURE, and it runs BEFORE the merges below rather than after: a
rem  fast-forward first is what makes the push at the end a fast-forward. It is still allowed
rem  to fail - it never discards anything, and it refuses a diverged branch by design - so a
rem  non-zero result is reported and execution continues.
rem
rem  No parenthesised block around `if errorlevel`: inside one, cmd evaluates it at PARSE time
rem  and silently reads the wrong value. The python-missing case is reported as ITSELF rather
rem  than as drift - an alarm that misdiagnoses is the very defect being fixed here.
where python >nul 2>nul || goto :nodrift
python "%~dp0scripts\sync_checkout.py" --repo "%CD%"
if errorlevel 1 echo.
if errorlevel 1 echo   [!] This folder is still not in step with GitHub - see the report above.
if errorlevel 1 echo       Nothing was discarded; work that was only here is now on a rescue/ branch.
if errorlevel 1 echo       Continuing anyway; the push below may still be rejected.
if errorlevel 1 echo.
goto :drifted
:nodrift
echo Skipping the sync - python is not on PATH ^(this is not a drift warning^).
:drifted

rem --- Auto-land of agent branches: REMOVED 2026-10-06 ---------------------------------
rem  This script used to merge every local worktree-* branch into main here. That predates
rem  the land gate (MA11): agent branches now land on GitHub through land-agent-branch.yml,
rem  which merges, runs the land policy and every test suite, and only then pushes main.
rem  Merging a branch locally bypassed all of that, and a branch the gate had ALREADY landed
rem  (under a different merge commit) showed up here as a conflict that blocked Don's own
rem  push - which is how DECISIONS.md sat unpushed on 2026-10-06. Agent work is the gate's;
rem  this script pushes only the files edited in this folder.
set "LANDFAIL="
echo Agent branches land through the GitHub gate - not merged here.

rem --- Never deploy red ------------------------------------------------------------------
echo Running tests before pushing...
python tests\test_edge.py >nul 2>nul
if errorlevel 1 (
  echo  [!] TESTS FAILED - refusing to push. Fix them, then run this again.
  goto :done
)
echo   [OK] tests pass.

"%GIT%" add -A
"%GIT%" diff --cached --quiet
if errorlevel 1 (
  "%GIT%" commit -q -m "Update %DATE% %TIME%"
  echo Committed your latest changes.
) else (
  echo No new file edits - checking for commits not yet on GitHub...
)

echo Pushing to GitHub...
"%GIT%" push
if errorlevel 1 (
  rem  This used to blame the login unconditionally. The commonest cause is the OTHER one:
  rem  main has diverged from GitHub, so the push is rejected as a non-fast-forward and no
  rem  credential will fix it. Naming the likelier cause first cost four days once.
  echo  [!] Push failed - the two likeliest causes, in order:
  echo        1. This folder has diverged from GitHub. Run sync.bat, then run this again.
  echo        2. Windows has not saved your GitHub login. Run connect_github.bat once.
) else (
  echo  [OK] GitHub is up to date.
)

goto :done

:done
if "%~1"=="" pause
