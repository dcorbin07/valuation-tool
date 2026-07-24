@echo off
REM Double-click to view the FULL site on your own PC (landing + login + pricing
REM + the gated dashboard) — exactly what visitors will see, but private to you.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  Python isn't installed ^(or not on PATH^). Get it at https://www.python.org/downloads/
  echo  and check "Add Python to PATH" during install, then run this again.
  echo.
  pause & exit /b 1
)

if not exist ".venv" (
  echo Setting up ^(first run only, ~1 min^)...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul 2>nul
pip install -q -r requirements.txt stripe

echo.
echo  Starting your site at  http://127.0.0.1:5000
echo  Your browser will open. Close this window to stop.
echo.
start "" http://127.0.0.1:5000
python run_saas.py
pause
