#!/usr/bin/env bash
#
# backup_state.sh — snapshot the bots' state off-box, into a private git repo.
#
# WHY THIS MATTERS MORE THAN WHICH HOST YOU USE:
#
# Everything the bots have ever learned lives in data/ — the sim books, the
# equity curves, the journals. It exists in exactly ONE place: the boot volume
# of a free-tier VM. Every documented Oracle free-tier horror story ends the
# same way: no warning, no appeal, and no successful data recovery. Whether that
# risk is 1% or 0.1% a year, the fix costs twenty minutes and turns a
# catastrophic, unrecoverable loss into an hour of annoyance.
#
# This uses a second private GitHub repo rather than object storage because you
# already have git working, it needs no new account, and it gives you a dated
# history of every state file for free — which is itself useful when a curve
# looks wrong and you want to know when it started.
#
# ONE-TIME SETUP
#   1. Create a second EMPTY private repo on GitHub, e.g. quant-bots-state.
#   2. On the box:
#        mkdir -p ~/quant_bots_state && cd ~/quant_bots_state
#        git init -b main
#        git remote add origin git@github.com:YOURNAME/quant-bots-state.git
#        git config user.email "bot@localhost"
#        git config user.name  "quant-bots box"
#      (the deploy key you set up needs WRITE access on THIS repo — unlike the
#       code repo, where read-only is correct)
#   3. Add to crontab (crontab -e), nightly after the close:
#        0 22 * * 1-5 /bin/bash /home/ubuntu/quant_bots/deploy/backup_state.sh >> /home/ubuntu/state_backup.log 2>&1
#
# Restoring is just: clone the state repo, copy data/ back, restart.

set -euo pipefail

SRC="${SRC:-$HOME/quant_bots/data}"
DEST="${DEST:-$HOME/quant_bots_state}"

[[ -d "$SRC" ]]  || { echo "no state dir at $SRC"; exit 1; }
[[ -d "$DEST/.git" ]] || { echo "no git repo at $DEST — see the setup notes at the top of this file"; exit 1; }

# Mirror state across. --delete keeps the backup an accurate reflection rather
# than an ever-growing pile, but we EXCLUDE the caches: they are large, they
# regenerate on their own, and they are not state you would ever want back.
rsync -a --delete \
  --exclude 'cache/' \
  --exclude '__pycache__/' \
  "$SRC/" "$DEST/data/"

cd "$DEST"

if [[ -z "$(git status --porcelain)" ]]; then
  echo "$(date -Is) no state changes"
  exit 0
fi

# Record what actually changed, so the commit log is readable months later.
rows=""
for b in trend momentum reversion options; do
  f="$DEST/data/sim/$b/equity_curve.jsonl"
  [[ -f "$f" ]] && rows="$rows $b=$(wc -l < "$f")"
done

git add -A
git commit -q -m "state $(date -Is)${rows:+ —$rows}"
git push -q origin main
echo "$(date -Is) backed up${rows:+ —$rows}"
