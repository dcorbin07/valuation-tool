@echo off
setlocal enableextensions
rem ============================================================
rem  ThetaData options cache miner — double-click and leave running.
rem
rem  Runs the WHOLE ranked universe in ONE long-lived process. It is
rem  resumable: every symbol-year already on disk is skipped, so
rem  closing this window and reopening it later costs nothing.
rem
rem  Stops only when the universe is done, the disk floor is hit,
rem  or you close the window.
rem
rem  Progress:  data\options\MINING_PROGRESS.txt
rem  Status:    python mine_status.py
rem ============================================================
cd /d "%~dp0"

where python >nul 2>nul || (
  echo Python not found on PATH. Install it or open a shell where "python" works.
  pause
  exit /b 1
)

echo ============================================================
echo  Valquo options cache miner
echo  Resumable - safe to close and restart at any time.
echo  Progress: data\options\MINING_PROGRESS.txt
echo ============================================================
echo.

rem -detach runs it without holding this window; default keeps it in view so
rem you can watch. Pass "bg" to run it hidden and return immediately.
if /i "%~1"=="bg" (
  start "" /b python mine_options_cache.py > "%~dp0..\..\..\data\options\miner_stdout.log" 2>&1
  echo Started in the background. Watch data\options\MINING_PROGRESS.txt
  exit /b 0
)

python mine_options_cache.py
echo.
echo Miner exited. Re-run this file to resume where it left off.
pause
