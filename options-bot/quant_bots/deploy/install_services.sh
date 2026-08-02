#!/usr/bin/env bash
#
# One-command install of all bot services + timers on a fresh Oracle box.
#
# Assumes the project lives at /home/ubuntu/quant_bots with its venv already
# created (python3 -m venv venv && pip install -r requirements.txt) and a
# populated .env. Run from anywhere:
#
#     bash ~/quant_bots/deploy/install_services.sh
#
# Safe to re-run — it overwrites the unit files and re-enables them.
set -e

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing systemd units from $DEPLOY_DIR ..."
sudo cp "$DEPLOY_DIR"/*.service /etc/systemd/system/
sudo cp "$DEPLOY_DIR"/*.timer   /etc/systemd/system/

sudo systemctl daemon-reload

echo "Enabling + starting the three bots (start on boot, restart on crash)..."
sudo systemctl enable --now trend-bot momentum-bot options-bot reversion-bot

echo "Enabling + starting the timers (daily summary, weekly report)..."
sudo systemctl enable --now daily-summary.timer weekly-report.timer

echo ""
echo "Done. Current status:"
systemctl is-active trend-bot momentum-bot options-bot reversion-bot
echo "Timers:"
systemctl list-timers daily-summary.timer weekly-report.timer --no-pager
