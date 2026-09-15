@echo off
setlocal enableextensions
rem ============================================================================
rem  0_FIX_DRIFT.bat  -  repairs the 211-commit drift in valuation-tool.
rem
rem  PUT THIS FILE IN:  C:\Users\donni\Downloads\valuation-tool
rem  then right-click -> Run as administrator is NOT needed; just double-click.
rem
rem  Why you have to run this and an agent cannot: Claude Code sessions are
rem  worktree-isolated, and every step below must happen in the MAIN folder,
rem  where main is checked out.
rem
rem  It is preserve-first. Nothing is discarded at any point:
rem    1. commits every uncommitted change to a NEW rescue branch
rem    2. PUSHES that branch to GitHub, so it is off this PC
rem    3. only then fast-forwards main to origin/main
rem  If any step fails it stops and tells you, leaving the repo as it was.
rem ============================================================================
title FIX DRIFT - valuation-tool
cd /d "%~dp0"

set "STAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%"
set "BR=rescue/drift-%STAMP%"

rem --- locate git (same logic git_push.bat uses) ------------------------------
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. Run connect_github.bat first. & goto :done )

rem --- sanity: right folder, right branch -------------------------------------
"%GIT%" rev-parse --is-inside-work-tree >nul 2>nul || ( echo Not a git folder - are you in valuation-tool? & goto :done )
set "CURBR="
for /f "usebackq tokens=*" %%c in (`"%GIT%" rev-parse --abbrev-ref HEAD`) do set "CURBR=%%c"
if /i not "%CURBR%"=="main" ( echo You are on %CURBR%, not main. Switch to main first. & goto :done )

echo.
echo  ============================================================
echo    FIXING THE DRIFT
echo    rescue branch: %BR%
echo  ============================================================
echo.

echo [1/5] Refreshing what GitHub has...
"%GIT%" fetch origin
if errorlevel 1 ( echo  [!] fetch failed - check your GitHub login. & goto :done )
for /f "usebackq tokens=1,2" %%a in (`"%GIT%" rev-list --left-right --count main...origin/main`) do (
  echo       local-only commits: %%a    behind GitHub: %%b
)
echo.

echo [2/5] Saving EVERY uncommitted change to %BR% ...
"%GIT%" checkout -b "%BR%"
if errorlevel 1 ( echo  [!] could not create the rescue branch. & goto :done )
"%GIT%" add -A
"%GIT%" commit -q -m "rescue: uncommitted local work before the 211-commit sync"
if errorlevel 1 echo       (nothing to commit - continuing)
echo       saved.
echo.

echo [3/5] Pushing %BR% to GitHub so it is no longer on one machine...
"%GIT%" push -u origin "%BR%"
if errorlevel 1 (
  echo  [!] PUSH FAILED. Stopping here ON PURPOSE - your work is committed
  echo      locally on %BR% but not yet backed up. Fix the login, then
  echo      run:   git push -u origin %BR%
  goto :done
)
echo       backed up.
echo.

echo [4/5] Returning to main and fast-forwarding to GitHub...
"%GIT%" checkout main
if errorlevel 1 ( echo  [!] could not switch back to main. & goto :done )
"%GIT%" merge --ff-only origin/main
if errorlevel 1 (
  echo  [!] fast-forward refused. main is not a clean ancestor.
  echo      Nothing lost - your work is safe on %BR%. Send this to Claude.
  goto :done
)
echo       main is now current.
echo.

echo [5/5] Confirming...
for /f "usebackq tokens=1,2" %%a in (`"%GIT%" rev-list --left-right --count main...origin/main`) do (
  echo       local-only commits: %%a    behind GitHub: %%b     ^(0 and 0 = fixed^)
)
echo.
echo  ============================================================
echo    DONE. Your old work is on branch %BR%, on GitHub.
echo.
echo    NEXT: tell Claude "drift fixed, branch is %BR%" so the
echo    genuinely-new work can be re-applied onto current main.
echo  ============================================================

:done
echo.
pause
