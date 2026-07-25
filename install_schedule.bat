@echo off
REM One-click: register the DAILY "hot stocks of the day" scan in Windows Task Scheduler.
REM Double-click this file. Runs run_weekly_scan.bat every day at 6:00 AM.
cd /d "%~dp0"
schtasks /create /tn "HotStocksDailyScan" /tr "\"%CD%\run_weekly_scan.bat\"" /sc DAILY /st 06:00 /f
if errorlevel 1 (
  echo.
  echo Could not register the task. Try running this file "as administrator".
) else (
  echo.
  echo Done. The "hot stocks of the day" scan is scheduled to run every day at 6:00 AM.
  echo Change or remove it anytime in Windows "Task Scheduler" ^(task name: HotStocksDailyScan^).
)
pause
