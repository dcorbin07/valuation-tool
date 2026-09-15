@echo off
rem ============================================================================
rem  0_PUSH.bat  -  THE ONE YOU DOUBLE-CLICK TO GO LIVE.
rem
rem  Named with a leading 0 so it sorts to the TOP of this folder, which holds
rem  300+ files. It is a thin wrapper: all the real work is in git_push.bat,
rem  which is unchanged and still the file everything else calls. Nothing was
rem  renamed, so the scheduled tasks and installers that reference it by name
rem  keep working.
rem
rem  What happens when you run it:
rem    1. syncs this folder with GitHub
rem    2. merges any finished agent (worktree-*) branches into main
rem    3. RUNS THE TESTS - and refuses to push if they fail
rem    4. commits and pushes
rem    5. Render auto-deploys valquo.co a minute or two later
rem
rem  Safe to run anytime. It never discards work, and it will not deploy a
rem  red test suite.
rem ============================================================================
title PUSH VALQUO LIVE
cd /d "%~dp0"

echo.
echo  ============================================================
echo    PUSHING VALQUO LIVE
echo    tests run first - a red suite blocks the deploy
echo  ============================================================
echo.

call "%~dp0git_push.bat"
