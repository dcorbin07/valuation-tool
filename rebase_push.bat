@echo off
setlocal enableextensions
rem ============================================================
rem  One-time fix for "rejected (non-fast-forward)": puts the
rem  commits that exist only in this folder ON TOP of GitHub's
rem  latest main, then pushes. Nothing is discarded: if the
rem  replay hits a conflict it stops and undoes itself.
rem ============================================================
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. & goto :done )

"%GIT%" diff --quiet
if errorlevel 1 ( echo You have unsaved file edits. Run git_push.bat once first, then this. & goto :done )
"%GIT%" diff --cached --quiet
if errorlevel 1 ( echo You have staged edits. Run git_push.bat once first, then this. & goto :done )

echo Fetching GitHub...
"%GIT%" fetch -q origin
if errorlevel 1 ( echo Could not reach GitHub. & goto :done )

echo Replaying this folder's own commits on top of GitHub's main...
"%GIT%" rebase origin/main
if errorlevel 1 (
  echo  [!] Conflict - undoing the replay. Nothing was lost.
  "%GIT%" rebase --abort
  goto :done
)

echo Pushing...
"%GIT%" push origin HEAD:main
if errorlevel 1 ( echo  [!] Push failed. & goto :done )
echo  [OK] GitHub is up to date.

:done
pause
