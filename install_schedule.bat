@echo off
REM One-click: register the weekly hot-stocks scan in Windows Task Scheduler.
REM Double-click this file. Runs run_weekly_scan.bat every Monday at 6:00 AM.
cd /d "%~dp0"
schtasks /create /tn "HotStocksWeeklyScan" /tr "\"%CD%\run_weekly_scan.bat\"" /sc weekly /d MON /st 06:00 /f
if errorlevel 1 (
  echo.
  echo Could not register the task. Try running this file "as administrator".
) else (
  echo.
  echo Done. The weekly scan is scheduled for Mondays at 6:00 AM.
  echo Change or remove it anytime in Windows "Task Scheduler" ^(task name: HotStocksWeeklyScan^).
)
pause
