@echo off
rem ============================================================================
rem  install_sync_task.bat  -  turn the drift cure on. Double-click once.
rem
rem  Registers a daily task, "ValquoSyncCheckout", that keeps this folder in step
rem  with GitHub and rescues anything that exists only on this PC. It needs NO
rem  administrator rights - it is an ordinary per-user task.
rem
rem  Safe to run more than once: /F replaces the task rather than adding a second.
rem  To remove it:   schtasks /Delete /TN "ValquoSyncCheckout" /F
rem  To watch it:    type "%LOCALAPPDATA%\Valquo\sync.log"
rem
rem  WHAT IT WILL AND WILL NOT DO ON ITS OWN
rem    will:     fetch, push commits that exist only here, bank uncommitted edits
rem              to GitHub, and fast-forward this folder
rem    will NOT: discard anything, or resolve a diverged branch. It stops and says
rem              so, because that step can destroy work and should have a human.
rem ============================================================================
setlocal enableextensions
cd /d "%~dp0"

set "TASK=ValquoSyncCheckout"
set "HOMEDIR=%LOCALAPPDATA%\Valquo"
set "BOOT=%HOMEDIR%\valquo_sync_bootstrap.bat"
set "WHEN=19:30"

echo.
echo   Installing the daily checkout sync...
echo.

if not exist "%HOMEDIR%" mkdir "%HOMEDIR%" >nul 2>nul
if not exist "scripts\valquo_sync_bootstrap.bat" (
  echo   [X] scripts\valquo_sync_bootstrap.bat is missing - is this folder up to date?
  goto :done
)

rem  Copied OUT of the repo on purpose. The task must keep working while this
rem  folder is stale, which is the whole failure MA20 describes.
copy /y "scripts\valquo_sync_bootstrap.bat" "%BOOT%" >nul
if errorlevel 1 ( echo   [X] could not write %BOOT% & goto :done )
echo   [OK] bootstrap installed at %BOOT%

rem  19:30, half an hour BEFORE ValuationToolAutoPush at 20:00. That task pushes
rem  and has never fetched, so on a diverged folder its push is rejected, it blames
rem  the login and exits 0 - four green days with nothing pushed. Syncing first is
rem  what makes its push a fast-forward.
schtasks /Create /TN "%TASK%" /TR "\"%BOOT%\" \"%CD%\"" /SC DAILY /ST %WHEN% /F >nul 2>&1
if errorlevel 1 (
  echo   [X] could not register the task. Run this and send me what it prints:
  echo       schtasks /Create /TN "%TASK%" /TR "\"%BOOT%\"" /SC DAILY /ST %WHEN% /F
  goto :done
)
echo   [OK] task "%TASK%" registered - daily at %WHEN%
echo.
echo   Running it once now so you can see what it says...
echo.
call "%BOOT%" "%CD%"
set "RC=%ERRORLEVEL%"
echo.
type "%HOMEDIR%\sync.log" 2>nul | more +0 >nul 2>nul
if "%RC%"=="0" (
  echo   [OK] This folder is current and nothing is stranded.
) else (
  echo   [!] It could not finish on its own. The full report is in:
  echo       %HOMEDIR%\sync.log
  echo   Nothing was discarded - work that existed only here is now on GitHub.
)

:done
echo.
if "%~1"=="" pause
