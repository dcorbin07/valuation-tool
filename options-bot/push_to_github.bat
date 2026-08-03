@echo off
REM ===========================================================================
REM  push_to_github.bat  -  commit everything and push.
REM
REM  Safe to run any time, and safe to run when nothing has changed.
REM  Also the script the daily scheduled task runs.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "LOG=%~dp0push_log.txt"
for /f "tokens=*" %%t in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "NOW=%%t"

call :log "---- push run %NOW% ----"

where git >nul 2>&1
if errorlevel 1 (
  call :log "ERROR: git not found on PATH"
  echo  ERROR: git is not installed or not on your PATH.
  goto :done
)

if not exist ".git" (
  call :log "ERROR: not a git repository - run setup_git.bat first"
  echo  ERROR: this folder is not a git repository yet.
  echo  Run setup_git.bat first.
  goto :done
)

REM ---- anything to commit? --------------------------------------------------
git diff --quiet && git diff --cached --quiet && git ls-files --others --exclude-standard --directory --no-empty-directory | findstr . >nul
if errorlevel 1 (
  REM there IS something - fall through
) else (
  call :log "no changes"
  echo  No changes to push.
  goto :done
)

git add -A
if errorlevel 1 (
  call :log "ERROR: git add failed"
  goto :done
)

REM ---- SAFETY: never let a real .env through --------------------------------
git diff --cached --name-only > "%TEMP%\pb_staged.txt"
findstr /R /C:"\.env$" "%TEMP%\pb_staged.txt" | findstr /V /C:".env.example" >nul
if not errorlevel 1 (
  call :log "ABORTED: .env was staged"
  echo.
  echo  ABORTING: a .env file was about to be committed. Nothing was pushed.
  findstr /R /C:"\.env$" "%TEMP%\pb_staged.txt" | findstr /V /C:".env.example"
  git reset >nul
  del "%TEMP%\pb_staged.txt" >nul 2>&1
  goto :done
)
del "%TEMP%\pb_staged.txt" >nul 2>&1

REM ---- nothing actually staged? --------------------------------------------
git diff --cached --quiet
if not errorlevel 1 (
  call :log "nothing staged after add"
  echo  No changes to push.
  goto :done
)

git commit -m "Auto-commit %NOW%" >> "%LOG%" 2>&1
if errorlevel 1 (
  call :log "ERROR: commit failed - see above"
  echo  Commit failed. See push_log.txt
  goto :done
)

git push >> "%LOG%" 2>&1
if errorlevel 1 (
  call :log "ERROR: push failed - see push_log.txt"
  echo.
  echo  Push failed. Most likely your GitHub sign-in expired.
  echo  Run this file by hand once and sign in when the browser opens.
  goto :done
)

call :log "pushed OK"
echo  Pushed.

:done
if "%PB_NOPAUSE%"=="" pause
exit /b 0

:log
echo %~1>> "%LOG%"
exit /b 0
