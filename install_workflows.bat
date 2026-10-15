@echo off
setlocal enableextensions enabledelayedexpansion
rem ============================================================
rem  INSTALL WORKFLOWS - puts GitHub Actions files on main for you.
rem
rem  Agents cannot change .github/ (the land gate refuses it, by design), so
rem  a lane or Cowork drops the finished file into
rem      data\pending_workflows\<name>.yml
rem  and you double-click this. It:
rem    1. fetches the latest main from GitHub,
rem    2. makes a throwaway copy of main in your TEMP folder (your own
rem       folder and its uncommitted work are never touched),
rem    3. copies each pending .yml into .github\workflows\,
rem    4. commits and pushes to main,
rem    5. moves the installed files to data\pending_workflows\installed\.
rem  data\ is gitignored, so the pending files are never committed by
rem  git_push.bat. Safe to run twice: an already-installed file changes nothing.
rem ============================================================
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. & goto :done )

rem ITEM 58b -- TWO SOURCE DIRECTORIES, and the tracked one is the point.
rem
rem `data\pending_workflows` is inside the gitignored `/data/`, so every workflow handed over
rem through it has existed only on this machine: unreviewable in the repo and unpinnable by any
rem test. For a file that POSTs an admin door on a schedule that is the one place a `?run=1`
rem could appear with nobody able to see it.
rem
rem `pending_workflows` at the repo root is TRACKED. New handovers go there and a test reads
rem them. The old path is still read so anything already waiting on disk still installs.
set "SRC=%~dp0data\pending_workflows"
set "SRC2=%~dp0pending_workflows"
set "HAVE="
if exist "%SRC%\*.yml" set "HAVE=1"
if exist "%SRC2%\*.yml" set "HAVE=1"
if not defined HAVE (
  echo Nothing waiting in pending_workflows or data\pending_workflows - nothing to install.
  goto :done
)

echo Fetching the latest main from GitHub...
"%GIT%" fetch -q origin main || ( echo Could not reach GitHub. Nothing was changed. & goto :done )

set "WT=%TEMP%\valquo_install_wf_%RANDOM%%RANDOM%"
"%GIT%" worktree add -q --detach "%WT%" origin/main || ( echo Could not make a temporary copy of main. Nothing was changed. & goto :done )

set "NAMES="
for %%F in ("%SRC%\*.yml") do (
  copy /y "%%F" "%WT%\.github\workflows\%%~nxF" >nul
  echo   staged  .github\workflows\%%~nxF
  set "NAMES=!NAMES! %%~nxF"
)
for %%F in ("%SRC2%\*.yml") do (
  copy /y "%%F" "%WT%\.github\workflows\%%~nxF" >nul
  echo   staged  .github\workflows\%%~nxF  [tracked]
  set "NAMES=!NAMES! %%~nxF"
)

pushd "%WT%"
"%GIT%" add .github/workflows
"%GIT%" diff --cached --quiet
if not errorlevel 1 (
  echo.
  echo Already installed on main - nothing changed.
  popd
  goto :installed
)
"%GIT%" commit -q -m "Install workflow(s):%NAMES% (via install_workflows.bat)"
"%GIT%" push -q origin HEAD:main
if errorlevel 1 (
  echo Main moved while this ran - retrying once on top of the newest main...
  "%GIT%" pull -q --rebase origin main
  "%GIT%" push -q origin HEAD:main
  if errorlevel 1 (
    echo.
    echo PUSH FAILED. Nothing reached GitHub. Your files are still in data\pending_workflows.
    popd
    goto :cleanup
  )
)
echo.
echo INSTALLED on main:%NAMES%
popd

:installed
rem Only the LEGACY, untracked directory is cleared. Moving a TRACKED file would appear as a
rem deletion in the next commit, and the installer is idempotent anyway -- it compares against
rem main and reports "already installed" when nothing differs.
if exist "%SRC%\*.yml" (
  if not exist "%SRC%\installed" mkdir "%SRC%\installed"
  for %%F in ("%SRC%\*.yml") do move /y "%%F" "%SRC%\installed\" >nul
)

:cleanup
"%GIT%" worktree remove --force "%WT%" >nul 2>nul

:done
echo.
pause
