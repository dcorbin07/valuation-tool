@echo off
rem ============================================================
rem  Is this folder still current with GitHub?
rem
rem  Double-click any time. It only LOOKS - it changes nothing.
rem  If it reports a problem, the cure is sync.bat.
rem
rem  Why this exists: agents work in .claude\worktrees\ and land
rem  through GitHub, so nothing in the normal day refreshes THIS
rem  folder - and every scheduled task on this PC runs the .bat
rem  files from HERE. On 2026-08-14 this folder was 514 commits
rem  behind and holding one commit that existed nowhere else.
rem ============================================================
setlocal
cd /d "%~dp0"

python scripts\checkout_drift.py
set RC=%ERRORLEVEL%

if "%RC%"=="0" goto :done
echo.
echo   TO FIX IT NOW:      sync.bat
echo   TO STOP IT COMING BACK:  install_sync_task.bat  ^(once - registers a
echo                       daily sync; no administrator rights needed^)
echo.
echo   Neither discards anything. Work that exists only on this PC is pushed
echo   to a rescue/ branch on GitHub before anything else happens.
echo.

:done
if "%~1"=="" pause
exit /b %RC%
