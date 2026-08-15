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

rem --- Drift alarm ----------------------------------------------------------------------
rem  This script runs daily and never fetches, so on its own it cannot tell that this folder
rem  has fallen behind GitHub - which is how it kept reporting success while a commit sat
rem  unpushed for four days. This LOOKS ONLY and never blocks: if the tree is behind, the
rem  push below fails anyway, and the cure (sync.bat) is a separate, deliberate step.
rem  No parenthesised block around `if errorlevel`: inside one, cmd evaluates it at PARSE
rem  time and it silently reads the wrong value. And the python-missing case is reported as
rem  ITSELF rather than as drift - an alarm that misdiagnoses is the defect being fixed
rem  three lines further down, not one to re-create here.
where python >nul 2>nul || goto :nodrift
python "%~dp0scripts\checkout_drift.py"
if errorlevel 1 echo.
if errorlevel 1 echo   [!] This folder is out of step with GitHub - see above. Run sync.bat.
if errorlevel 1 echo       Continuing anyway; nothing below depends on it.
if errorlevel 1 echo.
goto :drifted
:nodrift
echo Skipping the drift check - python is not on PATH ^(this is not a drift warning^).
:drifted

rem --- Auto-land finished agent work ---------------------------------------------------
rem  Claude Code works on worktree-* branches (its harness will not push to main), so every
rem  session used to end with a manual merge. This now does a REAL merge (--no-edit), not
rem  fast-forward-only: main and the agent branches routinely diverge because main picks up
rem  its own commits, and FF-only silently skipped every diverged branch - which is exactly
rem  the manual-merge treadmill this is meant to kill.
rem
rem  Safety: a genuine conflict is aborted, reported, and BLOCKS the push, so a half-merged
rem  tree is never deployed. Tests then run, and a red suite also blocks the push - this
rem  script deploys to Render, and auto-deploying a failing build is worse than not landing.
set "LANDFAIL="
set "CURBR="
for /f "usebackq tokens=*" %%c in (`"%GIT%" rev-parse --abbrev-ref HEAD`) do set "CURBR=%%c"
if /i not "%CURBR%"=="main" (
  echo Not on main ^(on %CURBR%^) - skipping auto-land.
) else (
  echo Checking for finished agent branches to land...
  rem  "delims=* " strips the leading "* " / "  " that git branch prints, so %%b is the bare name.
  for /f "usebackq tokens=* delims=* " %%b in (`"%GIT%" branch --list worktree-*`) do (
    call :try_merge "%%b"
  )
)
if defined LANDFAIL (
  echo.
  echo  [!] A branch could not be merged cleanly. Nothing was pushed.
  goto :done
)

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

:try_merge
rem  Merge one agent branch. Called (not inlined) so plain %VAR% expansion works - doing this
rem  inside the for-loop needs delayed expansion, which is how this script broke twice before.
set "BR=%~1"
set "AHEAD=0"
for /f "usebackq tokens=*" %%n in (`"%GIT%" rev-list --count main..%BR% 2^>nul`) do set "AHEAD=%%n"
if "%AHEAD%"=="0" (
  echo   [skip]    %BR% - nothing new
  goto :eof
)
"%GIT%" merge --no-edit "%BR%" >nul 2>nul
if errorlevel 1 (
  "%GIT%" merge --abort >nul 2>nul
  echo   [conflict] %BR% - resolve manually
  set "LANDFAIL=1"
) else (
  echo   [merged]  %BR% ^(%AHEAD% commits^)
)
goto :eof

:done
if "%~1"=="" pause
