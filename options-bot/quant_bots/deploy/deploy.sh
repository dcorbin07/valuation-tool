#!/usr/bin/env bash
#
# deploy.sh — pull the latest code from GitHub and restart the bots.
#
# This REPLACES the old zip-through-Cloud-Shell-then-scp flow. That flow had
# five manual steps and three well-known ways to go wrong (wrong zip size,
# bracketed-paste mangling, unzipping from inside quant_bots/ so it nests as
# quant_bots/quant_bots/). None of them can happen here.
#
# Usage, from anywhere on the box:
#
#     bash ~/quant_bots/deploy/deploy.sh
#
# Or from your Windows machine, in one line, without logging in:
#
#     ssh -i ~/ssh-key-2026-05-29.key ubuntu@YOUR_IP "bash ~/quant_bots/deploy/deploy.sh"
#
# Design notes, because each of these is a deliberate choice:
#
#   * `git merge --ff-only`, never `git pull`. A merge conflict on a production
#     box, mid-deploy, is a bad place to be — especially at 3pm on a market day.
#     --ff-only refuses and leaves everything exactly as it was.
#   * Dependencies install BEFORE services restart, so a failed pip install
#     aborts while the OLD services are still running happily.
#   * Tests run BEFORE services restart, for the same reason. A deploy that
#     would break the bots stops here instead.
#   * State lives OUTSIDE the repo tree (see STATE_DIR). `.gitignore` alone is
#     not protection: `git clean -fdx` deletes ignored files, and it is exactly
#     the command you reach for when a pull goes wrong.

set -euo pipefail

REPO_DIR="${REPO_DIR:-$HOME/quant_bots}"
VENV="${VENV:-$REPO_DIR/venv}"
BOTS="trend-bot momentum-bot options-bot reversion-bot"
EXPECTED_CORE_TESTS=106
EXPECTED_OPTIONS_TESTS=181

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mDEPLOY ABORTED: %s\033[0m\n' "$*" >&2; exit 1; }

cd "$REPO_DIR" || die "no repo at $REPO_DIR"

# ─── 1. Refuse to deploy on top of local edits ──────────────────────────────
say "Checking working tree"
if [[ -n "$(git status --porcelain)" ]]; then
  git status --short
  die "the working tree has local changes. Commit, stash, or discard them first.
     Deploying over uncommitted edits is how you lose work you didn't know you had."
fi

BEFORE="$(git rev-parse --short HEAD)"

# ─── 2. Fetch and fast-forward ──────────────────────────────────────────────
say "Fetching from origin"
git fetch --prune origin

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if ! git merge --ff-only "origin/$BRANCH"; then
  die "cannot fast-forward $BRANCH. The box has commits origin doesn't, or the
     histories diverged. Nothing has been changed. Investigate before forcing."
fi

AFTER="$(git rev-parse --short HEAD)"
if [[ "$BEFORE" == "$AFTER" ]]; then
  say "Already up to date at $AFTER — nothing to deploy"
  systemctl is-active $BOTS || true
  exit 0
fi

echo "  $BEFORE -> $AFTER"
git --no-pager log --oneline "$BEFORE..$AFTER" | sed 's/^/    /'

# ─── 3. Dependencies (BEFORE any restart) ───────────────────────────────────
say "Installing dependencies"
[[ -x "$VENV/bin/python3" ]] || die "no venv at $VENV. Create it:
     python3 -m venv $VENV && $VENV/bin/pip install -r $REPO_DIR/requirements.txt"
"$VENV/bin/pip" install -q -r requirements.txt || die "pip install failed — old services left running"

# ─── 4. Tests (BEFORE any restart) ──────────────────────────────────────────
say "Running tests"
core_out="$("$VENV/bin/python3" -m unittest discover tests 2>&1 | tail -3)"
echo "$core_out" | sed 's/^/    /'
echo "$core_out" | grep -q '^OK' || die "core tests FAILED — services untouched, still on the old code"

opt_out="$(cd options && "$VENV/bin/python3" -m unittest discover 2>&1 | tail -3)"
echo "$opt_out" | sed 's/^/    /'
echo "$opt_out" | grep -q '^OK' || die "options tests FAILED — services untouched, still on the old code"

core_n="$(echo "$core_out" | grep -oE 'Ran [0-9]+' | grep -oE '[0-9]+')"
opt_n="$(echo "$opt_out" | grep -oE 'Ran [0-9]+' | grep -oE '[0-9]+')"
if [[ "$core_n" -lt "$EXPECTED_CORE_TESTS" || "$opt_n" -lt "$EXPECTED_OPTIONS_TESTS" ]]; then
  echo "  WARNING: expected >= $EXPECTED_CORE_TESTS core / $EXPECTED_OPTIONS_TESTS options tests,"
  echo "           got $core_n / $opt_n. Old code may be present. Continuing anyway."
fi

# ─── 5. Secrets survived? ───────────────────────────────────────────────────
say "Checking .env"
[[ -f "$REPO_DIR/.env" ]] || die ".env is missing. It is gitignored so a pull cannot
     have removed it — but the bots will not run without it."
echo "    present, $(grep -c '=' "$REPO_DIR/.env") keys"

# ─── 6. Restart ─────────────────────────────────────────────────────────────
say "Reinstalling units and restarting"
bash "$REPO_DIR/deploy/install_services.sh"

sleep 3
say "Status"
for b in $BOTS; do
  printf '    %-16s %s\n' "$b" "$(systemctl is-active "$b")"
done

say "Deployed $BEFORE -> $AFTER"
echo "  Logs:  tail -n 20 $REPO_DIR/<bot>_service.log"
