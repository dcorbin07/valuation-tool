@echo off
REM ===========================================================================
REM  Valquo - QUICK SMOKE TEST (50 names, ~2 minutes).
REM  Confirms your Sharadar key + the whole backtest pipeline work end-to-end
REM  BEFORE you kick off the full 3,000-name run in run_backtest.bat.
REM  Just double-click it.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo backtest SMOKE TEST (50 names) ===
echo(

echo Downloading a small sample to data\backtest_test ...
%PY% -m valuation.edge.export_sharadar --limit 50 --out data\backtest_test
if errorlevel 1 (
    echo(
    echo Download failed - read the message just above ^(it will say if it's the key,
    echo the subscription, or the network^).
    pause
    exit /b 1
)

echo(
echo Running the backtest on the sample ...
%PY% -m valuation.edge.fundamental_panel --data-dir data\backtest_test
if errorlevel 1 (
    echo Backtest step failed - read the message above.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo If a results table printed above ^(returns vs the benchmark^), the pipeline works.
echo Glance that the insider + institutional columns are not blank, then run
echo   run_backtest.bat   for the full 3,000-name backtest.
echo ---------------------------------------------------------------------------
pause
