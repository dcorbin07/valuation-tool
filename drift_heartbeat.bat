@echo off
rem ============================================================================
rem  drift_heartbeat.bat  -  MB28. What the scheduled task runs.
rem
rem  Measures the shared checkout ONCE and writes the result to
rem      %LOCALAPPDATA%\Valquo\drift.json
rem  It changes nothing. The file's timestamp IS the measurement: board_state.py
rem  reports how old it is, so a clock that has stopped shows up as a number in a
rem  report somebody reads, instead of as silence.
rem
rem  You do not normally run this by hand - install_drift_task.bat schedules it.
rem  For a one-off look use check_drift.bat, which prints instead of writing.
rem ============================================================================
setlocal
cd /d "%~dp0"

python scripts\drift_heartbeat.py %*
set RC=%ERRORLEVEL%

rem  The exit code is the ALARM's, passed straight through, so Task Scheduler's
rem  LastTaskResult means what checkout_drift.py means: 0 current, 1 drifted or
rem  unmeasurable. The heartbeat file is written either way.
exit /b %RC%
