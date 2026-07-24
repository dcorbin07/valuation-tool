@echo off
setlocal enableextensions
rem ============================================================
rem  One-time GitHub connect for the valuation tool.
rem  Works with Git for Windows OR GitHub Desktop's built-in git.
rem  Double-click, follow the one step, press Enter, done.
rem  Everything it does is written to github_connect.log.
rem ============================================================
cd /d "%~dp0"
set "LOG=%~dp0github_connect.log"
echo GitHub connect - %DATE% %TIME% > "%LOG%"
echo.

rem --- find git: system PATH first, else GitHub Desktop's bundled git ---
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT (
  echo  [!] Couldn't find Git on this PC. Two easy options:
  echo      A^) EASIEST - open GitHub Desktop, File ^> Add Local Repository ^> pick this
  echo         folder, then click "Publish repository" ^(Private^). No command line needed.
  echo      B^) Or install Git for Windows: https://git-scm.com/download/win  then rerun this.
  echo Git not found >> "%LOG%"
  echo. & pause & exit /b 1
)
echo Using git: %GIT% >> "%LOG%"

echo  STEP 1 - make the empty repo (only the first time):
echo    1) Go to  https://github.com/new
echo    2) Repository name:  valuation-tool
echo    3) Choose  Private
echo    4) Do NOT check "Add a README" or a .gitignore or license
echo    5) Click  Create repository
echo.
echo  Then come back here.
echo.

set "REPO=https://github.com/dcorbin07/valuation-tool.git"
echo  Your repo link is pre-filled: %REPO%
echo  Press Enter to use it, or paste a different link then Enter.
echo.
set /p REPO="  Repo link [Enter = keep the one above]: "
echo Using repo: %REPO% >> "%LOG%"

echo.
echo  Connecting and pushing... a GitHub sign-in window may pop up the first time.
echo.

(
  echo --- ensure repo exists locally ---
  "%GIT%" rev-parse --is-inside-work-tree >nul 2>nul || "%GIT%" init -b main
  "%GIT%" branch -M main
  echo --- identity (only set if missing) ---
  "%GIT%" config user.email >nul 2>nul || "%GIT%" config user.email "donniecorbin6@gmail.com"
  "%GIT%" config user.name  >nul 2>nul || "%GIT%" config user.name  "Donovan Corbin"
  echo --- remote ---
  "%GIT%" remote remove origin 2>nul
  "%GIT%" remote add origin %REPO%
  "%GIT%" remote -v
  echo --- add / commit ---
  "%GIT%" add -A
  "%GIT%" commit -q -m "Import valuation tool to GitHub" 2>&1
  echo (commit above: "nothing to commit" is normal and fine)
  echo --- push ---
  "%GIT%" push -u origin main 2>&1
) >> "%LOG%" 2>&1

echo ============================================================
type "%LOG%"
echo ============================================================
echo.
findstr /i /c:"Everything up-to-date" /c:"main -> main" /c:"new branch" "%LOG%" >nul && (
  echo  [OK] Looks like it pushed. Refresh your GitHub repo page to confirm.
) || (
  echo  [?] If your files aren't on GitHub yet, send Claude the file
  echo      github_connect.log ^(in this folder^) and he'll sort it out.
)
echo.
pause
