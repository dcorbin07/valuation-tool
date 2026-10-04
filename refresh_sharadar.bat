@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

rem ===================================================================
rem  VALQUO - REFRESH SHARADAR
rem
rem  One double-click. Pulls a fresh Sharadar export into a dated freeze,
rem  then updates data\backtest so the panel can see the latest close.
rem  Prints one plain SUCCESS or FAILURE line at the end.
rem
rem  Written for the 2026-10-22 rebalance: Don runs this on the evening
rem  of 2026-10-23, then follows REBALANCE_RUNBOOK_2026-10-22.md Path B.
rem
rem  THE API KEY IS NEVER PRINTED. It is read from .env by the Python
rem  tool; nothing here echoes it and nothing here writes it anywhere.
rem
rem  Sharadar access ends around 2026-11-03. After that this script will
rem  fail at step 1 with an auth error, which is the correct behaviour --
rem  the already-taken freezes under data\backtest_freeze_* are what a
rem  later session points WRDS_DATA_DIR at instead.
rem ===================================================================

echo.
echo =================================================
echo    VALQUO  -  REFRESH SHARADAR
echo =================================================
echo.
echo This takes roughly 20-30 minutes: about 6 GB of
echo download, then a few minutes of preparation.
echo Leave the window open until it prints SUCCESS.
echo.

if not exist ".env" (
  echo FAILURE: .env is missing, so there is no Sharadar key to use.
  goto END
)

rem Step 1 - the full export, into data\backtest_freeze_YYYY-MM (the tool
rem dates the folder itself, so this needs no date arithmetic in batch).
echo [1/3] Pulling a fresh full Sharadar export...
python -m valuation.edge.sharadar_freeze --stage all
if errorlevel 1 goto PULLFAIL
echo.

rem Step 2 - find the freeze the pull just wrote. Ordered by NAME descending,
rem not by modification time: the folder is named backtest_freeze_YYYY-MM, so
rem lexicographic descending IS chronologically newest, and unlike an mtime
rem order nothing can promote an older freeze by merely touching a file in it.
echo [2/3] Locating the freeze that was just written...
set "FREEZE="
for /f "delims=" %%D in ('dir /b /ad /o-n "data\backtest_freeze_*" 2^>nul') do (
  if not defined FREEZE set "FREEZE=data\%%D"
)
if not defined FREEZE goto NOFREEZE
echo       using !FREEZE!
echo.

rem Step 3 - update data\backtest. The Python tool is the one definition
rem of this sync: it reports the newest close before and after, refuses
rem to go backwards, and fails if the close did not actually move.
echo [3/3] Updating data\backtest to the latest close...
python -m scripts.refresh_backtest_from_freeze --freeze "!FREEZE!" --live "data\backtest"
if errorlevel 2 goto SYNCFAIL
if errorlevel 1 goto NOTNEWER
echo.
echo =================================================
echo  SUCCESS: data\backtest now holds the latest close. Follow Path B.
echo =================================================
goto END

:PULLFAIL
echo.
echo =================================================
echo  FAILURE: the Sharadar export did not download. Check the messages
echo  above. If they mention authorisation, the subscription has lapsed
echo  and the existing freezes under data\backtest_freeze_* are the
echo  fallback - nothing needs re-pulling for research.
echo =================================================
goto END

:NOFREEZE
echo.
echo =================================================
echo  FAILURE: no data\backtest_freeze_* folder was found, so there is
echo  nothing to sync from.
echo =================================================
goto END

:NOTNEWER
echo.
echo =================================================
echo  FAILURE: the copy worked but the newest close did not move. The
echo  export carried nothing newer than what was already on disk - the
echo  market may not have closed yet, or the vendor has not published.
echo =================================================
goto END

:SYNCFAIL
echo.
echo =================================================
echo  FAILURE: data\backtest was NOT updated. See the messages above.
echo =================================================
goto END

:END
echo.
pause
endlocal
