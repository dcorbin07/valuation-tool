@echo off
REM One-click launcher for Windows. Double-click this file.
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
  echo Be sure to check "Add Python to PATH" during install.
  echo.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment ^(first run only^)...
  python -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Installing / updating dependencies ^(first run may take a minute^)...
python -m pip install --upgrade pip >nul 2>nul
pip install -q -r requirements.txt

echo.
echo Starting the Adaptive DCF Valuation Tool...
echo Your browser will open automatically. Close this window to stop.
echo.
python run.py
pause
