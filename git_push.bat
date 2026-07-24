@echo off
rem ============================================================
rem  Saves your changes and pushes them to GitHub. Run anytime
rem  after you've connected once with connect_github.bat.
rem  Does nothing if git isn't installed, the folder isn't a
rem  repo, no remote is set, or nothing has changed.
rem
rem  Secrets are never pushed: .env, *.db, and generated files
rem  are all gitignored.
rem ============================================================
cd /d "%~dp0"

where git >nul 2>nul || ( echo Git is not installed yet. Run connect_github.bat first. & goto :done )
git rev-parse --is-inside-work-tree >nul 2>nul || ( echo Not a git repo yet. Run connect_github.bat first. & goto :done )
git remote get-url origin >nul 2>nul || ( echo No GitHub remote set yet. Run connect_github.bat first. & goto :done )

git add -A
git diff --cached --quiet && ( echo Nothing has changed since the last push. & goto :done )

git commit -q -m "Update %DATE% %TIME%"
echo Pushing to GitHub...
git push
if errorlevel 1 (
  echo.
  echo  [!] Push failed. If this is your FIRST push, run connect_github.bat once
  echo      so Windows can save your GitHub login.
) else (
  echo  [OK] Pushed to GitHub.
)

:done
if "%~1"=="" pause
