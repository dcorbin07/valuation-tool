@echo off
REM CORRECTED-FLOORS item 1 -- the X7 placebo sweep on the CORRECTED full raw universe.
REM
REM Same instrument, same seeds (1000..1099) and same n as X7 / session 10, so the only thing
REM that differs is the universe. Costs are MEASURED (no --no-costs), as X7 measured them.
REM
REM It writes to its OWN artifact and touches NOTHING canonical: placebo.py has no code path to
REM BACKTEST_RESULTS.json, and PLACEBO_HAC.json (session 10's draws) is not opened.
REM
REM Every draw is written as it completes (rule 9), so a sweep killed at draw 63 is still usable.
REM Launch detached -- this is a multi-hour run and outlives any tool timeout.
setlocal
set ROOT=C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\r1b
set OUT=C:\Users\donni\Downloads\valuation-tool\data\free_analysis\PLACEBO_CORRECTED.json
set PANEL=C:\Users\donni\Downloads\valuation-tool\data\free_analysis\UNIVERSE_BIAS_PANEL_full.pkl
set LOG=C:\Users\donni\Downloads\valuation-tool\data\free_analysis\PLACEBO_CORRECTED.log
cd /d "%ROOT%"
echo [launch] %DATE% %TIME% > "%LOG%"
python -u -m scripts.placebo --panel "%PANEL%" --n 100 --seed0 1000 --out "%OUT%" >> "%LOG%" 2>&1
echo [exit %ERRORLEVEL%] %DATE% %TIME% >> "%LOG%"
endlocal
