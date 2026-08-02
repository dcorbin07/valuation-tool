@echo off
REM ===========================================================================
REM  setup_git.bat  -  ONE-TIME setup. Run this once, then never again.
REM
REM  Creates a git repo in this folder, makes the first commit, and connects
REM  it to a GitHub repository you have already created (empty, no README).
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo.
echo  === Porkbelly git setup ===
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo  ERROR: git is not installed, or not on your PATH.
  echo.
  echo  Install "Git for Windows" from https://git-scm.com/download/win
  echo  Accept all the defaults - in particular leave "Git Credential Manager"
  echo  enabled, which is what remembers your GitHub login.
  echo.
  echo  Then close this window, open a NEW one, and run this file again.
  pause
  exit /b 1
)

if not exist ".gitignore" (
  echo  ERROR: .gitignore is missing. Do not continue without it -
  echo  it is what keeps your .env secrets out of GitHub.
  pause
  exit /b 1
)

if exist ".git" (
  echo  This folder is already a git repository. Nothing to do.
  echo  Use push_to_github.bat to push changes.
  pause
  exit /b 0
)

echo  Before continuing, create an EMPTY repository on GitHub:
echo    1. Go to https://github.com/new
echo    2. Name it (e.g. quant-system)
echo    3. Choose Private
echo    4. Do NOT tick "Add a README" - it must be completely empty
echo    5. Click "Create repository" and copy the https:// URL
echo.
set /p REPO_URL="  Paste the repository URL here: "

if "%REPO_URL%"=="" (
  echo  No URL entered. Aborting.
  pause
  exit /b 1
)

echo.
echo  Initializing...
git init -b main
if errorlevel 1 goto :fail

git add -A
if errorlevel 1 goto :fail

REM ---- SAFETY: refuse to continue if a real .env got staged -----------------
git diff --cached --name-only > "%TEMP%\pb_staged.txt"
findstr /R /C:"\.env$" "%TEMP%\pb_staged.txt" | findstr /V /C:".env.example" >nul
if not errorlevel 1 (
  echo.
  echo  ABORTING: a .env file was about to be committed.
  echo  Files matched:
  findstr /R /C:"\.env$" "%TEMP%\pb_staged.txt" | findstr /V /C:".env.example"
  echo.
  echo  Check your .gitignore before retrying. Nothing has been pushed.
  git reset >nul
  del "%TEMP%\pb_staged.txt" >nul 2>&1
  pause
  exit /b 1
)
del "%TEMP%\pb_staged.txt" >nul 2>&1

git commit -m "Initial commit - quant bots, screener, backtests"
if errorlevel 1 goto :fail

git remote add origin "%REPO_URL%"
if errorlevel 1 goto :fail

echo.
echo  Pushing. A browser window may open asking you to sign in to GitHub -
echo  that is Git Credential Manager. Sign in once and it will remember.
echo.
git push -u origin main
if errorlevel 1 goto :fail

echo.
echo  === Done. ===
echo.
echo  From now on:
echo    - push_to_github.bat        push your changes any time
echo    - setup_daily_push.bat      run once, to push automatically every day
echo.
pause
exit /b 0

:fail
echo.
echo  Something failed above. Nothing was force-pushed; your files are safe.
echo  Copy the error text and send it over.
pause
exit /b 1
