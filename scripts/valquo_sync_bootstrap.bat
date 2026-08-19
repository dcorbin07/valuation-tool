@echo off
rem ============================================================================
rem  valquo_sync_bootstrap.bat  -  MA20, the unattended cure.
rem
rem  THE POINT OF THIS FILE IS WHERE IT RUNS FROM, NOT WHAT IT DOES.
rem  install_sync_task.bat copies it to %LOCALAPPDATA%\Valquo and points a daily
rem  scheduled task at THAT copy, deliberately not at the one in the repo.
rem
rem  Why: MA20 is "the shared checkout is 540 commits behind, so every .bat
rem  Windows runs from it is 540 commits old". A fix that lives inside that
rem  folder is subject to the disease it treats - it could only ever start
rem  working after somebody had already done the thing it exists to do.
rem  This copy sits outside the repo and, on every run, pulls the CURRENT
rem  script straight out of origin/main. So it is correct on its first run,
rem  from a stale tree, with nobody in the loop.
rem
rem  It keeps its own logic tiny for the same reason: this file is the one
rem  piece that cannot auto-update, so it must be small enough never to need to.
rem  Everything that might change lives in scripts/sync_checkout.py.
rem ============================================================================
setlocal enableextensions

set "REPO=C:\Users\donni\Downloads\valuation-tool"
if not "%~1"=="" set "REPO=%~1"

set "HOMEDIR=%LOCALAPPDATA%\Valquo"
set "STAGE=%HOMEDIR%\current\scripts"
set "LOG=%HOMEDIR%\sync.log"
if not exist "%STAGE%" mkdir "%STAGE%" >nul 2>nul

echo. >> "%LOG%"
echo ===== %DATE% %TIME% ===== >> "%LOG%"

where git >nul 2>nul || (echo   bootstrap: git is not on PATH >> "%LOG%" & exit /b 3)
where python >nul 2>nul || (echo   bootstrap: python is not on PATH >> "%LOG%" & exit /b 3)
if not exist "%REPO%\.git" (echo   bootstrap: no repo at %REPO% >> "%LOG%" & exit /b 3)

cd /d "%REPO%"

rem --- Fetch the CURRENT script, not the one on disk -------------------------
set "SRC=origin/main"
git fetch origin main --quiet
if errorlevel 1 goto :uselocal
git show origin/main:scripts/checkout_drift.py > "%STAGE%\checkout_drift.py" 2>nul
if errorlevel 1 goto :uselocal
git show origin/main:scripts/sync_checkout.py > "%STAGE%\sync_checkout.py" 2>nul
if errorlevel 1 goto :uselocal
rem  A failed `git show` still leaves a zero-byte file behind, and python would
rem  run it happily and report a clean sync. Size-check both before trusting them.
for %%F in ("%STAGE%\sync_checkout.py") do if %%~zF LSS 1000 goto :uselocal
for %%F in ("%STAGE%\checkout_drift.py") do if %%~zF LSS 500 goto :uselocal
set "RUN=%STAGE%\sync_checkout.py"
goto :run

:uselocal
rem  Offline, or the script is not on main yet. Fall back to this folder's copy and
rem  SAY SO - a run against a stale script that claimed to be current would be the
rem  same silent-staleness failure one level up.
set "SRC=local copy (could not read origin/main)"
set "RUN=%REPO%\scripts\sync_checkout.py"
if not exist "%RUN%" (echo   bootstrap: no sync_checkout.py anywhere >> "%LOG%" & exit /b 3)

:run
echo   using %SRC% >> "%LOG%"
python "%RUN%" --repo "%REPO%" >> "%LOG%" 2>&1
set "RC=%ERRORLEVEL%"
echo   exit %RC% >> "%LOG%"
exit /b %RC%
