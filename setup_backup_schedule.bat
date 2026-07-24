@echo off
rem ============================================================
rem  Turns ON automatic backups to D:\valuation-tool (Backup).
rem  Runs backup_now.bat every 6 hours (8am, 2pm, 8pm, 2am).
rem  Double-click once to set it up.
rem ============================================================
cd /d "%~dp0"

rem The "scheduled" argument tells backup_now.bat not to pause.
schtasks /create /tn "ValuationToolBackup" /tr "\"%CD%\backup_now.bat\" scheduled" /sc HOURLY /mo 6 /st 08:00 /f
if errorlevel 1 (
  echo.
  echo  [!] Couldn't create the task. Right-click this file, "Run as administrator", try again.
) else (
  echo.
  echo  [OK] Automatic backup is ON - every 6 hours to D:\valuation-tool (Backup).
  echo      Change the frequency or turn it off in Windows "Task Scheduler"
  echo      (task name: ValuationToolBackup).
)
echo.
pause
