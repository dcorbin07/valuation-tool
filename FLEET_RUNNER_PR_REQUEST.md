# FOR DON — one small PR to schedule the fleet runner

**2026-08-24, options-live lane.** `.github/` is untouchable to every agent lane (MA11's land
policy REFUSES any branch that touches it), so this is a request rather than a change. It is the
**exact `track-row.yml` precedent, PR #2's shape**: a cron that POSTs a door on the live service.
Nothing new is invented and no new secret is needed.

**READ THE HONEST LIMIT FIRST, because it decides whether this is urgent: SCHEDULING THIS TODAY
WILL PLACE NO TRADES.** Seventeen books are declared and every one of their entry rules is
**frozen in prose, not implemented as code**. The cycle reports that as `ARMED_NO_ENTRY_RULE` and
refuses to call it *"no candidates today"*. **The PR is still worth landing now** — it dates the
silence, it proves the path end to end while the stakes are zero, and the first implemented rule
starts accruing the day it lands rather than the day somebody remembers to wire a cron. It is
also the cheapest possible test of the door: a cycle that returns 200 with `breathing: false`
every evening is exactly what a correctly-plumbed, not-yet-built fleet should look like.

---

## The file to add: `.github/workflows/fleet-cycle.yml`

```yaml
name: FLEET CYCLE (S3-I1 declared paper books)

# The same architecture as PT-WRITER and for the same reason. A fleet cycle needs the
# Tradier sandbox token, network access AND the fleet records store at once, and only the
# Render service holds all three: Cowork has the book and no network, a GitHub runner has
# network and no book (`.gitignore` excludes /data/ with no negation). So this job is a
# scheduler plus a messenger -- no checkout of data, no pip install, no push permission.
#
# The door is POST /admin/fleet-cycle?run=1. Its rules live in valuation/edge/fleet.py,
# not here:
#   * append-only, hash-chained records -- a broken chain refuses the fill
#   * a book with no valid declaration committed ALONE before its first fill is REFUSED
#   * a stale, absent or failing day-1 self-check REFUSES every fill (three states)
#   * short books are REFUSED unless S3-I3's assignment provider is registered
#   * refusals are RECORDS, not crashes
#   * GET computes and returns; only POST?run=1 may write (a GET with run=1 is a 405)
#
# Secrets: SITE_BASE_URL and ADMIN_TOKEN -- both already exist; auto-scan, track-backup
# and track-row use the same two. DISCORD_WEBHOOK_URL optional.

on:
  workflow_dispatch: {}
  schedule:
    # 22:19 UTC is 6:19pm EDT / 5:19pm EST -- after the US close in BOTH halves of the
    # year, so no DST cron pair is needed. Deliberately 7 minutes after PT-WRITER's 22:12
    # so the two never contend for the same dyno wake-up. Odd minutes on purpose.
    - cron: "19 22 * * 1-5"

concurrency:
  group: fleet-cycle
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  cycle:
    runs-on: ubuntu-latest
    steps:
      - name: POST the fleet-cycle door
        env:
          SITE_BASE_URL: ${{ secrets.SITE_BASE_URL }}
          ADMIN_TOKEN: ${{ secrets.ADMIN_TOKEN }}
        run: |
          set -uo pipefail
          if [ -z "${SITE_BASE_URL:-}" ] || [ -z "${ADMIN_TOKEN:-}" ]; then
            echo "::error::SITE_BASE_URL or ADMIN_TOKEN is unset"; exit 1
          fi
          BODY=$(mktemp)
          CODE=$(curl -sS -o "$BODY" -w '%{http_code}' -X POST \
                   --max-time 120 \
                   -H "X-Admin-Token: ${ADMIN_TOKEN}" \
                   "${SITE_BASE_URL%/}/admin/fleet-cycle?run=1") || CODE="000"
          echo "HTTP ${CODE}"
          cat "$BODY"
          # 200 is the ONLY success. A cycle that placed nothing is not an error -- it is
          # the ordinary case and, until entry rules exist, the only case. Alerting on a
          # quiet day would teach everyone to ignore this job.
          [ "$CODE" = "200" ] || { echo "::error::fleet-cycle returned ${CODE}"; exit 1; }
          # Surface the state without failing on it.
          grep -q '"breathing": *true' "$BODY" \
            || echo "::warning::fleet is DECLARED-BUT-NOT-BREATHING (no entry rule implemented)"
```

---

## Why each choice

* **`?run=1` on a POST, never a GET.** The fleet streams are append-only and hash-chained. A
  side-effecting GET on an append-only record is reachable by a retry, a prefetch, a proxy or a
  pasted link, and none of those is a decision to record a trading day. This is the defect
  `/admin/track-row` shipped and then split; here the split is in the first commit. A GET with
  `run=1` returns **405** and writes nothing, pinned by test.
* **One cron, not two.** `track-row.yml` runs a backup at 23:37 because GitHub's free scheduler
  drops runs and that endpoint is idempotent per DAY. **The fleet door is not idempotent per
  day** — a book legitimately records many orders a day, which is the whole reason S3-I1 keys its
  streams on a sequence rather than a date (register finding E2). A blind retry could therefore
  double-record. **One cron until a per-day idempotency key exists**; a dropped run costs one
  day's fills and is recoverable, a double-recorded day is not.
* **200 is the only success, and a quiet day is a 200.** A refusal as 5xx tells a scheduler to
  retry something that is not broken; a quiet day as an error teaches an operator to ignore the
  alert. The state travels in the body (`breathing`, `note`, `books_with_no_entry_rule`) and
  surfaces as a GitHub **warning**, not a failure.
* **No new secret.** `SITE_BASE_URL` and `ADMIN_TOKEN` already exist and are already used by
  three workflows.

## The stopgap, if the PR waits

**A Cowork scheduled task named `valquo-fleet-cycle`**, weekdays at 18:19 America/New_York,
running the identical one-liner against the same door with the same token. It is a strictly
worse home for it — Cowork's schedule is not in the repo, so it rots invisibly, which is the
`PT-WRITER` failure exactly (a task nobody could find, a write nobody could date) — but it is
better than nothing accruing. **If the task is used, say so in `PAPER_TRACK_CONTRACT.md` so the
schedule's existence is at least written down somewhere tracked.**

## How to verify it worked, in one command

```
curl -sS -H "X-Admin-Token: $ADMIN_TOKEN" "$SITE_BASE_URL/admin/fleet-cycle" | python -m json.tool
```

A GET computes the identical report and writes nothing. Expect `books_declared: 17` (plus the
closed `testbook`), `entry_rules_implemented: 0`, `breathing: false` and every book at
`SELFCHECK_ABSENT` until each runs its day-1 gate on the service.

---

## ONE MORE HONEST LIMIT, FOUND AFTER THIS FILE WAS FIRST WRITTEN

**The six SHORT books will refuse even once the cron lands**, and the reason is an
architectural boundary rather than a bug in any of them.

`valuation/edge/assignment.py` (S3-I3, the assignment model every short book needs) imports
`valuation/edge/dividends.py`, which is an **ARCHIVED study** under `MA59`'s quarantine. The
fleet-cycle handler briefly registered the model itself — the runner is, after all, the natural
composition root — and `tests/test_ma59_quarantine.py` caught it immediately: *"reaching one
from the live app means the product is running an experiment."*

**So the registration was removed and the refusal is the shipped behaviour.** F-4, F-6, F-8,
F-10, F-17 and F-18 return `SHORT_BOOK_WITHOUT_ASSIGNMENT`, and the cycle body says exactly why
in `assignment_note` rather than leaving a reader to guess that six declarations are malformed.

**THE COST TODAY IS ZERO** — no book of any side can fill while no entry rule is implemented —
and refusing is the safe direction regardless. **Resolving it is the S3-I3 lane's call**, and it
is a real choice between three: lift `dividends` out of the archive with a register, break
`assignment`'s dependency on it, or run the fleet from a process that is not the web app. This
lane must not quietly pick one.
