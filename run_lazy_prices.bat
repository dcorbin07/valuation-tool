@echo off
REM ---------------------------------------------------------------------------
REM Build the "lazy prices" 10-K/10-Q language-change dataset from SEC EDGAR.
REM
REM RESEARCH ONLY — this builds a dataset, it does not score the live book and is
REM not wired into the panel. Free EDGAR data, no API key, no licensed data.
REM
REM Resumable: kill it and re-run, it re-downloads nothing it already cached.
REM Writes data\filings\lazy_prices.csv + coverage.json (both gitignored).
REM Takes ~1-2 hours for 250 names back to 2016 — it is rate-limited on purpose.
REM ---------------------------------------------------------------------------
cd /d "%~dp0"
python -X utf8 -u -m valuation.research.lazy_prices --limit 250 --since 2016-01-01 ^
    --workers 6 --req-per-sec 7 %*
pause
