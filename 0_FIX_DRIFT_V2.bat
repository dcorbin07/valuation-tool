@echo off
setlocal enableextensions
rem ============================================================================
rem  0_FIX_DRIFT_V2.bat   -   PUT IN C:\Users\donni\Downloads\valuation-tool
rem
rem  v1 had a real defect: it ran `git commit -q` and treated ANY failure as
rem  "nothing to commit", then pushed an empty rescue branch and looked like it
rem  had worked. Your uncommitted work was never saved. v2 shows every command's
rem  output, and VERIFIES the commit exists before it pushes or moves anything.
rem
rem  Safe to run repeatedly. It stops at the first real problem.
rem ============================================================================
title FIX DRIFT v2 - valuation-tool
cd /d "%~dp0"

set "BR=rescue/drift-20260914"

rem --- locate git -------------------------------------------------------------
set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. & goto :done )

"%GIT%" rev-parse --is-inside-work-tree >nul 2>nul || ( echo Not a git folder. & goto :done )

set "CURBR="
for /f "usebackq tokens=*" %%c in (`"%GIT%" rev-parse --abbrev-ref HEAD`) do set "CURBR=%%c"
echo.
echo  ============================================================
echo    FIX DRIFT v2      currently on: %CURBR%
echo  ============================================================
echo.

rem --- make sure we are on the rescue branch (v1 already created it) ----------
if /i "%CURBR%"=="main" (
  echo [1/6] Creating rescue branch %BR% ...
  "%GIT%" checkout -b "%BR%"
  if errorlevel 1 ( echo  [!] could not create it. & goto :done )
) else (
  echo [1/6] Already on %CURBR% - using it as the rescue branch.
  set "BR=%CURBR%"
)
echo.

rem --- record where HEAD is, so we can PROVE the commit happened --------------
set "BEFORE="
for /f "usebackq tokens=*" %%h in (`"%GIT%" rev-parse HEAD`) do set "BEFORE=%%h"
echo       HEAD before: %BEFORE%
echo.

echo [2/6] Staging everything (output shown - no silent failures)...
"%GIT%" add -A
if errorlevel 1 (
  echo  [!] `git add -A` FAILED. That is the real blocker - nothing else runs.
  echo      Send the message above to Claude.
  goto :done
)
echo       staged.
echo.

echo [3/6] Checking something is actually staged...
"%GIT%" diff --cached --quiet
if not errorlevel 1 (
  echo  [!] NOTHING IS STAGED. Your 1000+ modified files did not stage.
  echo      This is the real failure v1 hid. Send this screen to Claude.
  goto :done
)
"%GIT%" diff --cached --numstat | find /c /v "" > "%TEMP%\_n.txt"
set /p STAGED=<"%TEMP%\_n.txt"
del "%TEMP%\_n.txt" >nul 2>&1
echo       %STAGED% file^(s^) staged.
echo.

echo [4/6] Committing...
"%GIT%" commit -m "rescue: uncommitted local work before the drift sync (includes contract s8)"
set "AFTER="
for /f "usebackq tokens=*" %%h in (`"%GIT%" rev-parse HEAD`) do set "AFTER=%%h"
echo       HEAD after:  %AFTER%
if /i "%BEFORE%"=="%AFTER%" (
  echo  [!] HEAD DID NOT MOVE - the commit did not happen. Stopping.
  echo      Send the git output above to Claude.
  goto :done
)
echo       [OK] commit verified.
echo.

echo [5/6] Pushing %BR% to GitHub...
"%GIT%" push -u origin "%BR%"
if errorlevel 1 (
  echo  [!] push failed. Your work IS committed locally on %BR% and is safe.
  echo      Fix the login, then run:  git push -u origin %BR%
  goto :done
)
echo       [OK] backed up to GitHub.
echo.

echo [6/6] Fast-forwarding main to GitHub...
"%GIT%" checkout main
if errorlevel 1 ( echo  [!] could not switch to main. Work is safe on %BR%. & goto :done )
"%GIT%" fetch origin
"%GIT%" merge --ff-only origin/main
if errorlevel 1 (
  echo  [!] fast-forward refused. Nothing lost - work is on %BR%.
  goto :done
)
for /f "usebackq tokens=1,2" %%a in (`"%GIT%" rev-list --left-right --count main...origin/main`) do (
  echo       main ahead: %%a   behind: %%b    ^(0 and 0 = fixed^)
)
echo.
echo  ============================================================
echo    DONE. Work committed AND pushed on %BR%; main is current.
echo    Tell Claude: "v2 done, rescue branch pushed".
echo  ============================================================

:done
echo.
pause
