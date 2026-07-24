@echo off
rem ============================================================
rem  Turns on AUTOMATIC daily upload to GitHub (like your Trustee
rem  auto-backup). After this, any changes you or Claude make to
rem  this folder get committed + pushed once a day - hands off.
rem
rem  Requirement: you must have pushed successfully at least once
rem  (via GitHub Desktop or connect_github.bat) so Windows has
rem  saved your GitHub login. Otherwise the silent push can't sign in.
rem ============================================================
cd /d "%~dp0"

rem Runs git_push.bat with an argument so it never pauses (scheduler-safe).
schtasks /create /tn "ValuationToolAutoPush" /tr "\"%CD%\git_push.bat\" scheduled" /sc daily /st 20:00 /f
if errorlevel 1 (
  echo.
  echo  [!] Couldn't create the task. Try right-click this file, "Run as administrator".
) else (
  echo.
  echo  [OK] Automatic daily upload is ON - every day at 8:00 PM.
  echo      Change the time/frequency in Windows "Task Scheduler"
  echo      (task name: ValuationToolAutoPush), or delete it there to turn this off.
)
echo.
pause
