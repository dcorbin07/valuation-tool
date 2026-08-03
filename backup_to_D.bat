@echo off
setlocal
REM ================================================================
REM  Valquo -> D: backup (mirror of the working project).
REM  GitHub already backs up code + history via git_push.bat.
REM  THIS covers the whole working copy INCLUDING the non-git
REM  essentials that live only on C::  .env (your API keys) and data\.
REM  First run copies everything (slow over USB if data\ is big);
REM  every run after is incremental (only changed files).
REM ================================================================

set "SRC=C:\Users\donni\Downloads\valuation-tool"
set "DST=D:\valuation-tool (Backup)"

REM --- safety guards: never mirror from a wrong/empty source ---
if not exist "%SRC%\CLAUDE.md" ( echo [ABORT] source not found: %SRC% & pause & exit /b 1 )
if not exist "D:\" ( echo [ABORT] D: not found - plug in the backup USB and re-run. & pause & exit /b 1 )

echo Backing up Valquo to "%DST%" ...
echo (excludes transient dirs; includes .env and data\)
echo.

robocopy "%SRC%" "%DST%" /MIR ^
  /XD ".git" ".claude" "__pycache__" "node_modules" ".venv" "venv" ^
  /XF "*.pyc" ".fuse_hidden*" ^
  /R:1 /W:3 /MT:16 /NP /NDL /TEE /LOG:"D:\valquo_backup_log.txt"

echo.
if %ERRORLEVEL% LSS 8 (echo [OK] Backup complete. Log: D:\valquo_backup_log.txt) else (echo [WARN] robocopy reported errors - check D:\valquo_backup_log.txt)
endlocal
pause
