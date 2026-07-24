@echo off
rem ============================================================
rem  One-time GitHub connect for the valuation tool.
rem  Double-click, follow the one step, press Enter, done.
rem  Everything it does is written to github_connect.log so if
rem  anything goes wrong, send Claude that file and he'll fix it.
rem ============================================================
cd /d "%~dp0"
set "LOG=%~dp0github_connect.log"
echo GitHub connect - %DATE% %TIME% > "%LOG%"
echo.

where git >nul 2>nul || (
  echo  [!] Git is not installed. Get it at https://git-scm.com/download/win
  echo      (or open GitHub Desktop once - it installs Git - then run this again.)
  echo Git not installed >> "%LOG%"
  echo. & pause & exit /b 1
)

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
echo  Press Enter to use it, or paste a different link then Enter
echo  (change it if your GitHub username or repo name is different).
echo.
set /p REPO="  Repo link [Enter = keep the one above]: "
echo Using repo: %REPO% >> "%LOG%"

echo.
echo  Connecting and pushing... a GitHub sign-in window may pop up the first time.
echo.

(
  echo --- ensure repo exists locally ---
  git rev-parse --is-inside-work-tree >nul 2>nul || git init -b main
  git branch -M main
  echo --- identity (only set if missing) ---
  git config user.email >nul 2>nul || git config user.email "donniecorbin6@gmail.com"
  git config user.name  >nul 2>nul || git config user.name  "Donovan Corbin"
  echo --- remote ---
  git remote remove origin 2>nul
  git remote add origin %REPO%
  git remote -v
  echo --- add / commit ---
  git add -A
  git commit -q -m "Import valuation tool to GitHub" 2>&1
  echo (commit above: "nothing to commit" is normal and fine)
  echo --- push ---
  git push -u origin main 2>&1
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
