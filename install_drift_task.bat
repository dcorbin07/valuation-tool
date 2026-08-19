@echo off
rem ============================================================================
rem  install_drift_task.bat  -  MB28. Give the staleness monitor a clock.
rem  Double-click once. This is the two-line wiring; everything else is shipped.
rem
rem  Registers "ValquoDriftCheck", daily at 20:30, running drift_heartbeat.bat.
rem  NO administrator rights - an ordinary per-user task, same as the sync one.
rem
rem  Safe to run more than once: /F replaces rather than adding a second.
rem  To remove it:  schtasks /Delete /TN "ValquoDriftCheck" /F
rem  To see it:     type "%LOCALAPPDATA%\Valquo\drift.json"
rem
rem  WHY 20:30 AND NOT EARLIER
rem    ValquoSyncCheckout runs 19:30 and ValuationToolAutoPush 20:00. Measuring
rem    after both is what makes the number mean "the state the day's automation
rem    left behind" rather than "the state before it ran".
rem
rem  WHY THIS IS A SEPARATE TASK AND NOT A LINE IN THE SYNC ONE
rem    Bolting it onto the sync bootstrap would make it die exactly when the sync
rem    task dies - which is the failure it exists to detect.
rem
rem  WHAT IT WILL AND WILL NOT DO
rem    will:     measure and write %LOCALAPPDATA%\Valquo\drift.json once a day
rem    will NOT: fetch-and-merge, push, discard, or repair anything. It only looks.
rem              The cure is still sync.bat, and it is still a human's call.
rem ============================================================================
setlocal enableextensions
cd /d "%~dp0"

set "TASK=ValquoDriftCheck"
set "WHEN=20:30"

echo.
echo   Installing the daily drift heartbeat...
echo.

if not exist "drift_heartbeat.bat" (
  echo   [X] drift_heartbeat.bat is missing - is this folder up to date? Run sync.bat
  goto :done
)
if not exist "scripts\drift_heartbeat.py" (
  echo   [X] scripts\drift_heartbeat.py is missing - is this folder up to date?
  goto :done
)

schtasks /Create /TN "%TASK%" /TR "\"%CD%\drift_heartbeat.bat\"" /SC DAILY /ST %WHEN% /F >nul 2>&1
if errorlevel 1 (
  echo   [X] could not register the task. Run this and send me what it prints:
  echo       schtasks /Create /TN "%TASK%" /TR "\"%CD%\drift_heartbeat.bat\"" /SC DAILY /ST %WHEN% /F
  goto :done
)
echo   [OK] task "%TASK%" registered - daily at %WHEN%
echo.
echo   Running it once now so the heartbeat exists from today...
echo.

call "drift_heartbeat.bat"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo   [OK] The checkout is current, and the heartbeat is now beating.
) else (
  echo   [!] It measured a drift, or could not measure at all. The heartbeat was
  echo       still written - read it with:
  echo         type "%LOCALAPPDATA%\Valquo\drift.json"
  echo       The cure is sync.bat. Nothing here changed anything.
)
echo.
echo   From now on:  python scripts\board_state.py
echo   reports the heartbeat's age, so a stopped clock is visible.

:done
echo.
if "%~1"=="" pause
