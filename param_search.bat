@echo off
REM ===========================================================================
REM  Valquo - HONEST parameter search.
REM  Finds the best settings (theme weighting, top_n, exit band, min hold,
REM  market-cap tier) while doing everything known to stop a backtest fooling
REM  you: a locked-away hold-out, one declared search space scored on identical
REM  CPCV paths, selection by plateau instead of peak, White/Hansen bootstrap
REM  tests across the WHOLE search, a permanent trials ledger, and a
REM  permutation null that re-runs the entire search on signal-free data.
REM
REM  It only says "adopt" when EVERY gate passes. "Keep the defaults" is the
REM  normal and correct answer for a weak signal - that is the point.
REM
REM  Uses the data already in data\backtest - no new download. Double-click.
REM  First run builds and caches the point-in-time panel (20-40 min); after
REM  that the cache makes re-runs take minutes.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "DATADIR=data\backtest"
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo honest parameter search ===
echo(

if not exist "%DATADIR%\fundamentals.csv" (
    echo No local data in %DATADIR% - run run_backtest.bat once first to download it.
    pause
    exit /b 1
)

%PY% -m valuation.edge.fundamental_panel --data-dir "%DATADIR%" --param-search --permutations 25 --json "%DATADIR%\param_search.json"
if errorlevel 1 (
    echo Parameter search failed - read the message above.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo Read the GATES block at the bottom. Adoption needs all of them to PASS.
echo If it says KEEP THE DEFAULTS, that is a real result: the settings we would
echo have "optimised" to are not distinguishable from search luck.
echo ---------------------------------------------------------------------------
pause
