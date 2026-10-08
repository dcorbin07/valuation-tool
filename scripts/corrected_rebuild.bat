@echo off
REM CORRECTED-REBUILD -- ONE rebuild of the corrected full-universe panel.
REM
REM Detached: a ~290k-row build with eight forward horizons and keep_numbers=True outlives any
REM tool timeout. It REFUSES if its own output already exists, so a re-launch cannot silently
REM overwrite a panel a successor item has already read.
setlocal
set ROOT=C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\r1b
set LOG=C:\Users\donni\Downloads\valuation-tool\data\free_analysis\CORRECTED_REBUILD.log
cd /d "%ROOT%"
echo [launch] %DATE% %TIME% > "%LOG%"
python -u -m scripts.corrected_rebuild >> "%LOG%" 2>&1
echo [exit %ERRORLEVEL%] %DATE% %TIME% >> "%LOG%"
endlocal
