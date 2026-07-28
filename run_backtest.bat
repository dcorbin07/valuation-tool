@echo off
REM ===========================================================================
REM  Valquo - run the historical backtest vs the S&P (local).
REM  Downloads Sharadar data once, then backtests offline and prints the
REM  paste-ready optimized starting weights.
REM
REM  Requires your local .env to have:
REM     EDGE_DATA_PROVIDER=sharadar
REM     SHARADAR_API_KEY=<your Nasdaq Data Link key>
REM
REM  Usage:
REM     run_backtest.bat            (download only if missing, then backtest)
REM     run_backtest.bat export     (force a fresh download first)
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "DATADIR=data\backtest"
set "LIMIT=3000"

set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo backtest ===
echo(

if /I "%~1"=="export" goto :doexport
if exist "%DATADIR%\fundamentals.csv" (
    echo Local data found in %DATADIR% - skipping download.
    echo   ^(run "run_backtest.bat export" to re-download the latest^)
    goto :backtest
)

:doexport
echo Downloading Sharadar data to %DATADIR% ^(one-time; this can take a while^)...
%PY% -m valuation.edge.export_sharadar --out "%DATADIR%" --limit %LIMIT%
if errorlevel 1 (
    echo(
    echo Export failed - check that SHARADAR_API_KEY is set in your .env and your subscription is active.
    pause
    exit /b 1
)

:backtest
echo(
echo Running the backtest offline against %DATADIR% ...
%PY% -m valuation.edge.fundamental_panel --data-dir "%DATADIR%" --json "%DATADIR%\last_result.json"
if errorlevel 1 (
    echo Backtest failed.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo Done. If a horizon above says  beats-default-OOS: True  then copy the
echo   WEIGHTS_ESTABLISHED = { ... }
echo line into  valuation\screener\settings.py  and run  git_push.bat  to deploy it.
echo ^(If nothing beat the default out-of-sample, keep your current weights.^)
echo ---------------------------------------------------------------------------
pause
