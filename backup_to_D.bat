@echo off
REM ================================================================
REM  Valquo -> D: backup.
REM
REM  All the logic lives in backup_to_D.ps1 next to this file. This is
REM  just the double-clickable launcher, so Task Scheduler and Explorer
REM  keep working.
REM
REM  POLICY: back up what cannot be recreated, not what is large.
REM  It is an ALLOWLIST -- nothing is copied unless backup_to_D.ps1 names
REM  it. The old version copied everything and tried to exclude the big
REM  directories; data\ grew faster than the exclusion list and D: filled
REM  up twice.
REM
REM  Pass "auto" (as the scheduled task does) to skip the pause at the end.
REM  Pass "dryrun" to measure and report without copying anything.
REM  Pass "prune"  to also delete backup folders that left the allowlist.
REM ================================================================
setlocal

set "PSFILE=%~dp0backup_to_D.ps1"
if not exist "%PSFILE%" (
  echo  [ABORT] backup_to_D.ps1 was not found next to this file.
  echo          Expected: "%PSFILE%"
  if "%~1"=="" pause
  exit /b 1
)

set "ARGS="
if /I "%~1"=="dryrun" set "ARGS=-DryRun"
if /I "%~1"=="prune"  set "ARGS=-Prune"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PSFILE%" %ARGS%
set "RC=%ERRORLEVEL%"

echo.
REM A plain "pause" here used to HANG the scheduled run forever -- the task passes no
REM arguments and there is no console to press a key on, so Windows eventually killed it
REM (last result 0xC000013A). A timeout holds the window open when you double-click and
REM returns immediately when there is no input to wait on.
timeout /t 30 >nul 2>&1
exit /b %RC%
