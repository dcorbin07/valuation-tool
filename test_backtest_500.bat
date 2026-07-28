@echo off
REM ===========================================================================
REM  Valquo - MID-SIZE CONFIDENCE CHECK (500 names, ~10 minutes).
REM  Proves the backtest scales cleanly (memory + speed) before you commit to
REM  the full 3,000-name run. Just double-click it.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo backtest CONFIDENCE CHECK (500 names) ===
echo(

if exist "data\backtest_med\fundamentals.csv" (
    echo Data already downloaded in data\backtest_med - skipping download.
    echo   ^(delete that folder, or run test_backtest.bat, to re-download^)
) else (
    echo Downloading 500 names to data\backtest_med ...
    %PY% -m valuation.edge.export_sharadar --limit 500 --out data\backtest_med
    if errorlevel 1 (
        echo Download failed - read the message above.
        pause
        exit /b 1
    )
)

echo(
echo Running the backtest on 500 names ...
%PY% -m valuation.edge.fundamental_panel --data-dir data\backtest_med
if errorlevel 1 (
    echo Backtest step failed - read the message above.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo If this printed sane CAGR numbers with no slowdown or memory error, the full
echo run is safe - run  run_backtest.bat  for the real 3,000-name backtest.
echo ---------------------------------------------------------------------------
pause
