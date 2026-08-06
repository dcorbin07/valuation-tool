@echo off
REM ================================================================
REM  Backs up this project to the D: drive.
REM
REM  2026-08-06: this used to be a SECOND, independent backup with its
REM  own rules, and it was the reason D: kept filling up. It excluded
REM  only .venv / __pycache__ / .pytest_cache / node_modules, so it
REM  copied .git and .claude too -- and .claude holds ten git worktrees,
REM  each with a junction pointing back at data\. Robocopy follows
REM  junctions unless told not to, so every worktree duplicated the
REM  whole 62 GB data\ tree. It also used /E, which never deletes, so
REM  nothing it copied ever went away again.
REM
REM  Two schedules, one destination, opposite policies. Now there is one
REM  policy: back up what cannot be recreated, not what is large. Both
REM  scheduled tasks land here.
REM
REM  Double-click anytime. Everything real happens in backup_to_D.ps1.
REM ================================================================
setlocal
call "%~dp0backup_to_D.bat" %*
exit /b %ERRORLEVEL%
