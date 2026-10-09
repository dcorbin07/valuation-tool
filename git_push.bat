@echo off
setlocal enableextensions
rem ============================================================
rem  Saves your changes and pushes them to GitHub. Run anytime
rem  after you've connected once. Works with Git for Windows OR
rem  GitHub Desktop's built-in git. Secrets (.env, *.db) are
rem  never pushed. Always pushes commits that aren't on GitHub
rem  yet, even if there are no new file edits this run.
rem ============================================================
cd /d "%~dp0"

set "GIT="
where git >nul 2>nul && set "GIT=git"
if not defined GIT (
  for /f "delims=" %%d in ('dir /b /ad /o-n "%LOCALAPPDATA%\GitHubDesktop\app-*" 2^>nul') do (
    if not defined GIT if exist "%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe" set "GIT=%LOCALAPPDATA%\GitHubDesktop\%%d\resources\app\git\cmd\git.exe"
  )
)
if not defined GIT ( echo Git not found. Use GitHub Desktop, or run connect_github.bat first. & goto :done )

"%GIT%" rev-parse --is-inside-work-tree >nul 2>nul || ( echo Not connected yet - run connect_github.bat first. & goto :done )
"%GIT%" remote get-url origin >nul 2>nul || ( echo No GitHub remote yet - run connect_github.bat first. & goto :done )

rem --- Agent branches ---------------------------------------------------------------------
rem  REMOVED 2026-10-06. This script used to merge every local worktree-* branch into main
rem  here, which predates the land gate (MA11): agent branches land on GitHub through
rem  land-agent-branch.yml, which merges, runs the land policy and every suite, then pushes.
rem  Merging one locally bypassed all of that, and a branch the gate had ALREADY landed showed
rem  up here as a conflict that blocked Don's own push - which is how DECISIONS.md sat unpushed
rem  on 2026-10-06. This script pushes only the files edited in this folder.
echo Agent branches land through the GitHub gate - not merged here.

rem --- Never deploy red ------------------------------------------------------------------
echo Running tests before pushing...
python tests\test_edge.py >nul 2>nul
if errorlevel 1 (
  echo  [!] TESTS FAILED - refusing to push. Fix them, then run this again.
  echo      ^(If python is not on PATH this also fails - that is deliberate: the tests are
  echo       the gate, so no python means no push.^)
  goto :done
)
echo   [OK] tests pass.

rem --- Save, replay, push -----------------------------------------------------------------
rem  ITEM 43. THE ORDER HERE IS THE FIX, AND IT USED TO BE THE BUG. This script used to run
rem  sync_checkout.py FIRST and then commit. The sync correctly refuses to fast-forward over
rem  uncommitted edits to tracked files, so when GitHub had also changed those files the
rem  commit below landed on STALE main - ahead 1 / behind 1, DIVERGED - the push was rejected
rem  as a non-fast-forward, and sync.bat refuses a diverged branch by design, so the cure was
rem  not available either. Every single step was correct; the ORDER made a divergence out of
rem  two things that were merely out of step.
rem
rem  publish_folder.py commits FIRST, then fetches, then replays this folder's own commits on
rem  top of GitHub (rebase), aborting and reporting - never discarding - on a conflict, and
rem  only then pushes. It is python rather than batch so the dirty-tree-plus-landed-lane case
rem  is driven by a test against a real temporary repo with a fake remote.
python "%~dp0scripts\publish_folder.py" --repo "%CD%" --tests-passed
if errorlevel 1 echo.
if errorlevel 1 echo       Nothing was discarded. Read the report above - it names the step
if errorlevel 1 echo       that stopped and what to do next.

goto :done

:done
if "%~1"=="" pause
