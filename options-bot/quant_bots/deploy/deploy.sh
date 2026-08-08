#!/usr/bin/env bash
#
# ############################################################################
# ##  DECOMMISSIONED 2026-08-07 — THERE IS NO BOX TO DEPLOY TO.             ##
# ##                                                                        ##
# ##  The Oracle host 141.148.45.115 is gone. Never ssh or scp to it. The   ##
# ##  usage line below is kept as the record of how deploys worked; it is   ##
# ##  not an instruction. This script is NOT modified otherwise: it is a    ##
# ##  working artifact and `tests/test_deploy_preflight.py` asserts against ##
# ##  its literal text (that it runs the preflight, that a preflight        ##
# ##  failure is fatal, that it does so before any restart, and that        ##
# ##  EXPECTED_CORE_TESTS has not gone stale). Editing it casually breaks   ##
# ##  four tests.                                                           ##
# ##                                                                        ##
# ##  The reason it could never complete is FIXED, for the record: the      ##
# ##  options suite failed with 14x "No module named 'data'" because        ##
# ##  options/data/*.py was untracked. Restored 2026-08-07 from             ##
# ##  handoff/quant_bots.zip; preflight now exits 0 and 353 tests pass.     ##
# ##                                                                        ##
# ##  NOTE, not fixed here on purpose: EXPECTED_CORE_TESTS below reads 163  ##
# ##  while the core suite measured 172 on 2026-08-07. That is a drift of   ##
# ##  9, inside the 12 the stale-constant test allows, so it passes — but   ##
# ##  it is drifting again, exactly as it did at 106-vs-148. Bump it if the ##
# ##  bots are ever revived.                                                ##
# ############################################################################
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
# C6: these were 106/181 — two generations stale, and therefore incapable of
# firing. FIXES.md says "if you see the old numbers after a deploy, the old code
# is still there", so a floor that no longer moves with the suites disables the
# only freshness signal the deploy had. Bump these whenever tests are added; the
# preflight below is the check that does NOT rot, because it looks for the fixes
# themselves rather than for a count that stands in for them.
EXPECTED_CORE_TESTS=163
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

# ─── 3b. Preflight (BEFORE the suites, because it explains their failures) ──
#
# C6. The suites already gated the deploy correctly, but when the options suite
# broke it broke as 14 identical `ModuleNotFoundError: No module named 'data'`
# lines — which reads as a broken test environment, not as "a source package is
# missing from this repository because .gitignore excludes it". A deploy that
# aborts for an undecodable reason is a deploy that quietly stops happening, and
# that is how three fixed bugs sat undeployed. preflight.py names the cause and
# checks that each FIXES.md fix is actually present in the code being deployed.
say "Preflight"
"$VENV/bin/python3" deploy/preflight.py || die "preflight failed — see above.
     Services untouched, still on the old code."

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
