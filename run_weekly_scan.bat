@echo off
REM Weekly hot-stocks scan. Schedule this with Windows Task Scheduler (see RUNBOOK.md).
cd /d "%~dp0"
if not exist ".venv" ( python -m venv .venv )
call ".venv\Scripts\activate.bat"
pip install -q -r requirements.txt
REM --whole-market is slow on the free feed; drop --limit once you add an FMP key.
python -m valuation.screener.scan --whole-market --limit 1500 --dcf-top 12 --insider
