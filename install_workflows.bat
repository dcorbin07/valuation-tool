@echo off
setlocal enableextensions
rem ============================================================
rem  INSTALL WORKFLOWS - puts GitHub Actions files on main for you.
rem
rem  Agents cannot change .github/ (the land gate refuses it, by design), so the finished file
rem  is committed to the TRACKED folder
rem      pending_workflows\<name>.yml
rem  and you double-click this. It shows you what would change, then asks before touching main.
rem
rem  ITEM 85 -- WHY THIS FILE IS NOW FOUR LINES OF WORK AND A PYTHON CALL.
rem
rem  Until today this bat did the job itself, and it copied `%~dp0pending_workflows\*.yml` --
rem  the folder the bat happened to sit in. A copy of this bat exists in every lane worktree.
rem  On 2026-10-27 one was run from .claude\worktrees\dipcall\, whose pending folder held
rem  10-16/10-17 copies of two live workflows, and commit ad29600 put them on main: 338 lines
rem  deleted, including every healthchecks ping and every "tell Don this failed" Discord step
rem  from both the live and fleet cycles. It reported success, because it had done what it was
rem  told. The source was never meant to be "wherever this file is".
rem
rem  So the decision moved into scripts\install_workflows.py, which reads the pending folder of
rem  the FETCHED origin/main and nothing else, refuses to run from a worktree, prints NEW /
rem  CHANGED / unchanged per file, and refuses a file that would put an older version over a
rem  newer one. Two implementations of a rule is how the rule rots, so this file holds none of
rem  it -- it finds python and calls that one.
rem ============================================================
cd /d "%~dp0"

rem THE PARENTHESES ARE LOAD-BEARING. Written flat as
rem     if not defined PY where py >nul 2>nul && set "PY=py"
rem cmd binds the `&&` to the whole `if`, and an `if` whose condition is FALSE still succeeds --
rem so `PY` was overwritten with `py` on exactly the machines where `python` had already been
rem found, and broke wherever `py` does not exist. Found by reading it back rather than by it
rem failing, which is the only way a batch parsing bug like this ever surfaces.
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
  where py >nul 2>nul && set "PY=py"
)
if not defined PY (
  echo Python not found on PATH, so the installer cannot run.
  echo Install Python, or run this from a terminal where `python` works.
  goto :done
)

echo ============================================================
echo  WHAT WOULD CHANGE ON MAIN
echo ============================================================
echo.
%PY% -m scripts.install_workflows
rem Batch `errorlevel N` means "N or higher", so the codes are tested highest first.
if errorlevel 4 (
  echo.
  echo Main is already up to date. Nothing to install.
  goto :done
)
if errorlevel 2 (
  echo.
  echo Nothing was installed. Read the reason above.
  goto :done
)

echo.
set "GO="
set /p "GO=Install these on main? Type yes to go ahead: "
if /i not "%GO%"=="yes" (
  echo.
  echo Nothing was installed.
  goto :done
)

echo.
%PY% -m scripts.install_workflows --send

:done
echo.
pause
