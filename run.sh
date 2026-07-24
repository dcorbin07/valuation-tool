#!/usr/bin/env bash
# One-click launcher for macOS / Linux:  ./run.sh
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.10+ is required. Install it from https://www.python.org/downloads/"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (first run only)..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Installing / updating dependencies (first run may take a minute)..."
python -m pip install --upgrade pip >/dev/null 2>&1 || true
pip install -q -r requirements.txt

echo ""
echo "Starting the Adaptive DCF Valuation Tool — your browser will open automatically."
echo ""
python run.py
