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
REM    The FMP free allowance is shared with THE LIVE HOT-LIST SCAN, which runs
REM    at 22:23 UTC (23:41 UTC backup), Mon-Fri. When the allowance is spent, FMP
REM    returns 429 on EVERY endpoint for the whole account - so a big export can
REM    stop the daily scan from getting data.
REM
REM    Measured, not assumed: the allowance did NOT come back at 00:00 UTC after
REM    being spent, and was still refusing calls ~19 hours later. So do not count
REM    on a midnight reset. This file now PRE-CHECKS the key with a single call
REM    and stops immediately if it's blocked, instead of collecting 429s.
REM
REM    The fix that actually removes the conflict is FMP_BACKTEST_API_KEY - a
REM    second (free) FMP account used only by this export, so research work can
REM    never eat the live scan's allowance. See ENV_REFERENCE.md. Strongly
REM    recommended before running a full export.
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

REM ---- preflight: is there any allowance left on the key right now? -------
echo Checking the FMP key before starting...
%PY% -m valuation.edge.export_grades --check
if errorlevel 3 (
    echo(
    echo ---------------------------------------------------------------------
    echo  FMP is refusing calls on this key right now, so there is nothing to
    echo  download. Note this ALSO affects the live hot-list scan until it
    echo  clears - the allowance is per-account, not per-endpoint.
    echo(
    echo  What to do:
    echo    * Wait and try again later. It does NOT reliably reset at midnight.
    echo    * Better: set FMP_BACKTEST_API_KEY in .env to a second free FMP key,
    echo      so this export has its own allowance and can never block the scan.
    echo      See ENV_REFERENCE.md.
    echo ---------------------------------------------------------------------
    echo(
    pause
    exit /b 1
)

REM ---- warn if we're close to the daily scan's slot ------------------------
for /f %%H in ('%PY% -c "import datetime;print(datetime.datetime.now(datetime.timezone.utc).hour)"') do set "UTCH=%%H"
if "%UTCH%"=="22" goto :badtime
if "%UTCH%"=="23" goto :badtime
if "%UTCH%"=="21" goto :badtime
goto :goodtime

:badtime
echo(
echo  *** WARNING: it is currently %UTCH%:xx UTC. ***
echo  The daily hot-list scan runs at 22:23 UTC and shares this FMP key, so
echo  exporting now could leave the scan without data.
echo  Safer: run this earlier in the day, or set FMP_BACKTEST_API_KEY.
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
