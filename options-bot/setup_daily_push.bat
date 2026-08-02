@echo off
REM ===========================================================================
REM  setup_daily_push.bat  -  ONE-TIME. Schedules an automatic daily push.
REM
REM  Creates a Windows scheduled task that runs push_to_github.bat every day
REM  at 18:00. The task runs as you, while you are logged in - if the laptop
REM  is off at 18:00, Windows runs it at the next opportunity.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "TASKNAME=Porkbelly Daily GitHub Push"
set "SCRIPT=%~dp0push_to_github.bat"
set "RUNTIME=18:00"

echo.
echo  === Scheduling the daily push ===
echo.

if not exist "%SCRIPT%" (
  echo  ERROR: push_to_github.bat is not in this folder.
  pause
  exit /b 1
)

if not exist ".git" (
  echo  ERROR: run setup_git.bat first - there is no repository yet.
  pause
  exit /b 1
)

set /p CUSTOM="  Time to run each day [%RUNTIME%], press Enter to accept: "
if not "%CUSTOM%"=="" set "RUNTIME=%CUSTOM%"

schtasks /create ^
  /tn "%TASKNAME%" ^
  /tr "cmd /c set PB_NOPAUSE=1 && \"%SCRIPT%\"" ^
  /sc daily ^
  /st %RUNTIME% ^
  /rl LIMITED ^
  /f

if errorlevel 1 (
  echo.
  echo  Could not create the scheduled task.
  echo  Try again from an Administrator command prompt.
  pause
  exit /b 1
)

echo.
echo  === Scheduled. ===
echo.
echo  "%TASKNAME%" will run every day at %RUNTIME%.
echo.
echo  To check it:     schtasks /query /tn "%TASKNAME%"
echo  To run it now:   schtasks /run   /tn "%TASKNAME%"
echo  To remove it:    schtasks /delete /tn "%TASKNAME%" /f
echo.
echo  Results are appended to push_log.txt in this folder.
echo.
pause
exit /b 0
