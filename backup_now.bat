@echo off
rem ============================================================
rem  Backs up this folder to the D: backup drive.
rem   C:\...\valuation-tool  ->  D:\valuation-tool (Backup)
rem
rem  Uses robocopy (built into Windows). It only copies what
rem  CHANGED, so after the first run it's fast, and it never
rem  DELETES from the backup - a backup can't lose a file the
rem  original later drops. Also keeps a dated copy of your data
rem  + keys so a corrupted file can't overwrite a good backup.
rem
rem  Double-click anytime. setup_backup_schedule.bat makes it
rem  run automatically.
rem ============================================================
setlocal
set "SRC=%~dp0"
set "DST=D:\valuation-tool (Backup)"

if not exist "D:\" (
  echo  [!] Backup drive D: was not found. Plug it in, then run this again.
  echo.
  if "%~1"=="" pause
  exit /b 1
)

rem Skip regenerable junk that would just bloat the backup.
set XD=/XD ".venv" "__pycache__" ".pytest_cache" "node_modules"
set XF=/XF "*.pyc" "*.log"
set OPTS=/E /R:1 /W:1 /NFL /NDL /NP /NJH %XD% %XF%

echo  Backing up valuation-tool  ->  %DST%
robocopy "%SRC%." "%DST%" %OPTS%
set RC=%ERRORLEVEL%

rem --- extra safety: a dated copy of the irreplaceable data + keys ---
set "STAMP=%date:~-4%%date:~4,2%%date:~7,2%"
set "SNAP=%DST%\daily-data\%STAMP%"
if not exist "%SNAP%" mkdir "%SNAP%" 2>nul
if exist "%SRC%data\*.db" copy /Y "%SRC%data\*.db" "%SNAP%\" >nul 2>nul
if exist "%SRC%.env" copy /Y "%SRC%.env" "%SNAP%\.env" >nul 2>nul

rem robocopy codes below 8 = success (0 = nothing changed, 1 = copied, etc.)
if %RC% GEQ 8 (
  echo  [!] Backup finished with errors ^(code %RC%^). Check the drive and try again.
) else (
  echo  [OK] Backup complete. Dated data copy: %SNAP%
)
echo.
if "%~1"=="" pause
