@echo off
REM ===========================================================================
REM  Valquo - 13F (institutional) signal due-diligence.
REM  The whole backtest edge rests on the institutional theme. This re-runs that
REM  signal ALONE, at 15 / 45 / 135 / 225-day filing-lag assumptions, on the
REM  largest names, to see if it's a real tradeable signal or a look-ahead artifact.
REM  (The lags must cross a 13F quarter boundary to measure anything - the old
REM  45/60/90 grid all resolved to the SAME filed quarter, so it always printed
REM  three identical rows. See INST_LAG_GRID in fundamental_panel.py.)
REM  Uses the data already in data\backtest - no new download. Just double-click.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "DATADIR=data\backtest"
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo 13F signal validation ===
echo(

if not exist "%DATADIR%\fundamentals.csv" (
    echo No local data in %DATADIR% - run run_backtest.bat once first to download it.
    pause
    exit /b 1
)

%PY% -m valuation.edge.fundamental_panel --data-dir "%DATADIR%" --validate-institutional --json "%DATADIR%\institutional_validation.json"
if errorlevel 1 (
    echo Validation failed - read the message above.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo Done. Read the table as an information-decay curve:
echo   STRONGER at 15d than 45d = leans on filings that weren't public yet
echo                              (a look-ahead artifact, NOT tradeable).
echo   Peaks at 45d, decays 135d - 225d = a real, slowly-decaying signal.
echo   Flat across all four rows = no information at any horizon; noise.
echo A Deflated Sharpe above ~95%% at a realistic (45d+) lag is the bar for real.
echo ---------------------------------------------------------------------------
pause
