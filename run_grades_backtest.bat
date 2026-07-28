@echo off
REM ===========================================================================
REM  Valquo - analyst-ratings (sentiment) export + backtest re-run.
REM
REM  Two steps, in order:
REM    1. Download dated analyst rating actions from FMP  -> data\backtest\grades.csv
REM       (upgrades / downgrades / maintains, history from ~2012). These are
REM       point-in-time by construction: every row is stamped with the day it
REM       happened, so there is no filing lag to model.
REM    2. Re-run the full backtest, which now scores the `sentiment` theme from
REM       that data, and reports Deflated Sharpe / CPCV / PBO.
REM
REM  WHEN TO RUN THIS - it matters:
REM    The FMP free tier has a daily request cap AND THE LIVE HOT-LIST SCAN USES
REM    THE SAME KEY. That scan runs at 22:23 UTC (23:41 UTC backup), Mon-Fri.
REM    The quota resets at 00:00 UTC. So the safe window is roughly
REM       00:00 - 20:00 UTC  =  8pm - 4pm US Eastern
REM    and the ideal time is just after 00:00 UTC (~8pm ET), when the quota is
REM    fresh and the next scan is ~22 hours away. Running this in the couple of
REM    hours BEFORE 22:23 UTC risks starving the daily scan.
REM    (The intraday scans use Tradier, not FMP, so they don't compete.)
REM
REM  SAFE TO RE-RUN: the export appends and skips tickers it already has, so if
REM  the quota runs out part-way you can simply run this again tomorrow and it
REM  picks up where it stopped.
REM
REM  Step 2 takes 20-40 minutes. Just double-click and leave it.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "DATADIR=data\backtest"
set "LIMIT=250"
set "PY=python"
where py >nul 2>nul && set "PY=py"

echo(
echo === Valquo - analyst ratings (sentiment) + backtest ===
echo(

if not exist "%DATADIR%\fundamentals.csv" (
    echo No local backtest data in %DATADIR%.
    echo Run run_backtest.bat once first to download it, then come back here.
    echo(
    pause
    exit /b 1
)

REM ---- current UTC hour, to warn if this is a bad time to run -------------
for /f %%H in ('%PY% -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).hour)"') do set "UTCH=%%H"
if "%UTCH%"=="22" goto :badtime
if "%UTCH%"=="23" goto :badtime
if "%UTCH%"=="21" goto :badtime
goto :goodtime

:badtime
echo  *** WARNING: it is currently %UTCH%:xx UTC. ***
echo  The daily hot-list scan runs at 22:23 UTC and shares this FMP key, so
echo  running the export now could use up the quota the scan needs.
echo  Better to run this just after 00:00 UTC (about 8pm US Eastern).
echo(
choice /C YN /M "Run anyway"
if errorlevel 2 exit /b 0
echo(

:goodtime
echo [1/2] Downloading analyst rating actions for the %LIMIT% largest names...
echo       (resumable - already-downloaded tickers are skipped)
echo(
%PY% -m valuation.edge.export_grades --out "%DATADIR%" --limit %LIMIT%
set "RC=%ERRORLEVEL%"

if "%RC%"=="2" (
    echo(
    echo ---------------------------------------------------------------------
    echo  The FMP daily quota ran out part-way through.
    echo  What was downloaded HAS been saved. Just run this file again after
    echo  00:00 UTC and it will continue from where it stopped.
    echo(
    echo  Continuing to the backtest anyway with whatever data we have...
    echo ---------------------------------------------------------------------
    echo(
) else if not "%RC%"=="0" (
    echo(
    echo  The download failed - read the message above.
    pause
    exit /b 1
)

echo(
echo [2/2] Re-running the backtest with the sentiment theme (20-40 minutes)...
echo(
%PY% -m valuation.edge.fundamental_panel --data-dir "%DATADIR%" --json "%DATADIR%\last_result.json"
if errorlevel 1 (
    echo(
    echo  The backtest failed - read the message above.
    pause
    exit /b 1
)

echo(
echo ---------------------------------------------------------------------------
echo  Done. What to look for in the output above:
echo    * "sentiment" should now appear with real coverage (it was empty before).
echo    * Deflated Sharpe above ~95%% = a genuine edge. Below that = still noise.
echo    * PBO well below 50%% = the weighting isn't just overfitting.
echo  If sentiment shows 0%% coverage, the grades download didn't get far enough -
echo  re-run this file after the quota resets at 00:00 UTC.
echo ---------------------------------------------------------------------------
echo(
pause
