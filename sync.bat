@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo =================================================
echo    VALQUO  -  SYNC AND LAND AGENT WORK
echo =================================================
echo.

if exist ".git\index.lock" (
  echo Clearing a stale git lock file...
  del /f /q ".git\index.lock" >nul 2>&1
  echo.
)

echo [1/3] Fetching the latest from GitHub...
git fetch origin --prune
if errorlevel 1 goto NETFAIL
echo.

echo [2/3] Pushing any agent work still sitting on this machine...
for /f "usebackq tokens=*" %%B in (`git for-each-ref --format^="%%(refname:short)" refs/heads/worktree-*`) do (
  git push -q origin "%%B" >nul 2>&1 && echo     sent: %%B
)
echo.

echo [3/3] Updating your local copy of main...
git checkout main >nul 2>&1
if errorlevel 1 (
  echo     SKIPPED - you have uncommitted changes in the main folder.
) else (
  git merge --ff-only origin/main
)
echo.

echo -------------------------------------------------
echo   AGENT WORK NOT YET MERGED INTO MAIN
echo -------------------------------------------------
set ANY=0
for /f "usebackq tokens=*" %%B in (`git for-each-ref --format^="%%(refname:short)" refs/heads/worktree-*`) do (
  for /f %%N in ('git rev-list --count origin/main..%%B 2^>nul') do (
    if not "%%N"=="0" (
      echo     %%B  --  %%N commit^(s^) waiting
      set ANY=1
    )
  )
)
if "!ANY!"=="0" echo     none  --  everything is merged. You are fully up to date.
echo.

echo -------------------------------------------------
echo   WHAT TO DO NEXT
echo -------------------------------------------------
if "!ANY!"=="0" (
  echo   Nothing. All agent work is on GitHub and merged into main.
) else (
  echo   Work was just pushed. GitHub now runs the tests and merges
  echo   it into main automatically - usually within a minute or two.
  echo   Run this file again shortly; the list above should go empty.
  echo.
  echo   If a branch is STILL listed after a few minutes, its tests
  echo   failed. Tell Cowork the branch name and it will sort it out.
)
echo.
echo   NOTE: this can only send work an agent has COMMITTED. If an
echo   agent finished but never committed, ask it to "commit and push".
echo.
pause
goto :EOF

:NETFAIL
echo.
echo   ERROR: could not reach GitHub.
echo   Check your internet connection, then run this file again.
echo.
pause
