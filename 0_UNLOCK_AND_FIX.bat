@echo off
setlocal enableextensions
rem ============================================================================
rem  0_UNLOCK_AND_FIX.bat   -   PUT IN C:\Users\donni\Downloads\valuation-tool
rem
rem  THE ROOT CAUSE: .git/index.lock, 0 bytes, left behind by a crashed git on
rem  2026-08-27. Since that moment git has been unable to stage ANY file, so
rem  git_push.bat's `git add -A` failed every run, reported "No new file edits",
rem  and pushed nothing - which is how this folder fell 215 commits behind while
rem  every terminal looked green.
rem
rem  This clears the stale locks, then runs the full rescue + fast-forward.
rem ============================================================================
title UNLOCK AND FIX - valuation-tool
cd /d "%~dp0"

echo.
echo  ============================================================
echo    UNLOCK AND FIX
echo  ============================================================
echo.
echo  BEFORE CONTINUING, close:
echo    - GitHub Desktop
echo    - any Claude Code terminals open on valuation-tool
echo    - any other git window
echo.
pause
echo.

echo [1/8] Checking nothing is using git right now...
tasklist /FI "IMAGENAME eq git.exe" 2>nul | find /i "git.exe" >nul
if not errorlevel 1 (
    echo  [!] git.exe is STILL RUNNING. Close the apps above, then re-run.
    tasklist /FI "IMAGENAME eq git.exe"
    goto :done
)
echo       clear - no git process.
echo.

echo [2/8] Removing the stale locks...
if exist ".git\index.lock" (
    del /f /q ".git\index.lock"
    if exist ".git\index.lock" ( echo  [!] could not delete index.lock & goto :done )
    echo       removed .git\index.lock  ^(the Aug-27 one^)
) else (
    echo       index.lock already gone
)
if exist ".git\objects\maintenance.lock" (
    del /f /q ".git\objects\maintenance.lock" >nul 2>&1
    echo       removed .git\objects\maintenance.lock
)
echo.

rem --- locate git -------------------------------------------------------------
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. & goto :done )

set "CURBR="
for /f "usebackq tokens=*" %%c in (`"%GIT%" rev-parse --abbrev-ref HEAD`) do set "CURBR=%%c"
set "BR=%CURBR%"
echo [3/8] On branch %BR% - using it as the rescue branch.
set "BEFORE="
for /f "usebackq tokens=*" %%h in (`"%GIT%" rev-parse HEAD`) do set "BEFORE=%%h"
echo       HEAD before: %BEFORE%
echo.

echo [4/8] Staging everything ^(this is the step that has been failing^)...
"%GIT%" add -A
if errorlevel 1 ( echo  [!] `git add -A` STILL failing. Send this screen to Claude. & goto :done )
"%GIT%" diff --cached --quiet
if not errorlevel 1 ( echo  [!] nothing staged - send this screen to Claude. & goto :done )
echo       [OK] staged for the first time since Aug 27.
echo.

echo [5/8] Committing...
"%GIT%" commit -m "rescue: uncommitted local work stranded by a stale index.lock since 2026-08-27"
set "AFTER="
for /f "usebackq tokens=*" %%h in (`"%GIT%" rev-parse HEAD`) do set "AFTER=%%h"
if /i "%BEFORE%"=="%AFTER%" ( echo  [!] HEAD did not move - commit failed. & goto :done )
echo       [OK] commit verified: %AFTER%
echo.

echo [6/8] Pushing %BR% to GitHub...
"%GIT%" push -u origin "%BR%"
if errorlevel 1 (
  echo  [!] push failed, but your work IS committed locally on %BR% and safe.
  echo      Fix the login then run:  git push -u origin %BR%
  goto :done
)
echo       [OK] backed up to GitHub.
echo.

echo [7/8] Fast-forwarding main...
"%GIT%" checkout main
if errorlevel 1 ( echo  [!] cannot switch to main. Work is safe on %BR%. & goto :done )
"%GIT%" fetch origin
"%GIT%" merge --ff-only origin/main
if errorlevel 1 ( echo  [!] fast-forward refused. Work is safe on %BR%. & goto :done )
echo       main updated.
echo.

echo [8/8] Confirming...
for /f "usebackq tokens=1,2" %%a in (`"%GIT%" rev-list --left-right --count main...origin/main`) do (
  echo       main ahead: %%a   behind: %%b     ^(0 and 0 = fixed^)
)
echo.
echo  ============================================================
echo    DONE. Tell Claude: "unlocked, rescue pushed, main current".
echo  ============================================================

:done
echo.
pause
