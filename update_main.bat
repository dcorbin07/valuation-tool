@echo off
setlocal enableextensions
rem ============================================================
rem  UPDATE MAIN - brings this folder up to date with GitHub, and sends nothing.
rem
rem  ITEM 85. Use this before install_workflows.bat.
rem
rem  There was already sync.bat, and it does more than this: it PUSHES every worktree-* branch
rem  on the machine, which hands those branches to the land gate and can merge work into main.
rem  That is what it is for, and it is the wrong tool for "my folder is 27 commits behind and I
rem  am about to run the installer" -- which is how today's rollback happened, with an installer
rem  reading a folder older than the thing it was overwriting.
rem
rem  So this file does exactly two things and neither of them publishes:
rem    1. fetch from GitHub (read),
rem    2. fast-forward your main to match origin/main (local).
rem
rem  It will NOT discard your work. If this folder has uncommitted changes it stops and shows
rem  them, because throwing those away silently to win a fast-forward would be worse than being
rem  out of date.
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

echo [1/3] Reading the newest main from GitHub...
"%GIT%" fetch -q origin main
if errorlevel 1 ( echo Could not reach GitHub. Nothing changed. & goto :done )

echo [2/3] Checking this folder for uncommitted work...
"%GIT%" diff --quiet
set "DIRTY=%errorlevel%"
"%GIT%" diff --cached --quiet
if errorlevel 1 set "DIRTY=1"
if "%DIRTY%"=="1" (
  echo.
  echo STOPPED - this folder has uncommitted changes:
  "%GIT%" status --short
  echo.
  echo Nothing was changed or sent. Commit or set those aside, then run this again.
  goto :done
)

echo [3/3] Moving your main up to origin/main...
for /f %%B in ('"%GIT%" rev-parse --abbrev-ref HEAD') do set "BR=%%B"
if /i not "%BR%"=="main" "%GIT%" checkout -q main
for /f %%N in ('"%GIT%" rev-list --count HEAD..origin/main 2^>nul') do set "BEHIND=%%N"
"%GIT%" merge --ff-only origin/main
if errorlevel 1 (
  echo.
  echo Could not fast-forward - your main has commits of its own that are not on GitHub.
  echo Nothing was changed or sent. Tell a lane before going further.
  goto :done
)

echo.
echo Up to date. Moved forward %BEHIND% commit^(s^). Nothing was sent to GitHub.
echo You can run install_workflows.bat now.

:done
echo.
pause
