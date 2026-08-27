# FOR DON — one small PR to back up the fleet record streams

**2026-08-27, app-fixer lane. Audit #5 `H3`.** `.github/` is untouchable to every agent lane
(MA11's land policy REFUSES any branch that touches it), so this is a request rather than a
change. It is the **exact `track-backup.yml` precedent**: a weekly cron that GETs an admin-token
endpoint on the live service and commits what it renders. Nothing new is invented and **no new
secret is needed** — `SITE_BASE_URL` and `ADMIN_TOKEN` are the same two `track-backup`,
`auto-scan` and `track-row` already use.

**READ THE HONEST LIMIT FIRST, BECAUSE IT DECIDES WHETHER THIS IS URGENT: TODAY THIS WILL BACK
UP VERY LITTLE.** Most declared books have entry rules frozen in prose rather than implemented,
so few streams have rows yet. **Land it anyway, and the reason is the asymmetry:** the cost of
landing it early is a weekly no-op commit; the cost of landing it late is measured in evidence
that cannot be recreated, because a fleet record is a statement about what a book did on a day
that has already passed. `track-backup.yml`'s own header makes the same argument about the
forward track, and that record is the one this project protects best.

**AND THE OTHER HALF OF `H3` HAS ALREADY SHIPPED, WHICH CHANGES WHAT THIS PR IS FOR.** The audit
measured that **whole-file loss is not a chain break** — delete a book's CSV and it re-certifies,
resumes at `seq 1`, and every row chains correctly with no trace. `valuation/edge/fleet_highwater.py`
now keeps the highest `seq` ever seen for each book **outside the file it describes** and
`fleet.record` refuses to append to a stream that has gone backwards. So a single lost stream is
already caught. **What is still missing is the ability to get it back**, and that is this PR.

Backup protects against loss; the high-water mark makes loss visible. Neither substitutes for
the other: a backup nobody notices they need is restored a year late, and a mark with no backup
tells you precisely what you can no longer recover.

---

## The file to add: `.github/workflows/fleet-backup.yml`

```yaml
name: Fleet backup (the OTHER thing that can't be re-derived)

# Commits a plain-text snapshot of the FLEET RECORD STREAMS into the repo every week.
#
# WHY THIS EXISTS. This project holds exactly two datasets that cannot be rebuilt from the
# vendor exports: the contract-bound forward track, and the fleet's append-only record
# streams. `track-backup.yml` has protected the first since 2026-08-10. This protects the
# second, which is the one about to accrue five years of evidence.
#
# Both live on the Render web service's persistent disk (render.yaml: disk `data`, /app/data).
# That disk survives redeploys but not the service being deleted or recreated. Render cannot
# commit to git and GitHub Actions cannot read Render's disk, so the backup crosses the gap
# over HTTP -- the same architecture, for the same reason.
#
# WHAT IT CARRIES: one CSV per book exactly as written (including prev_hash/row_hash, so a
# restored stream can be RE-VERIFIED against its declaration rather than trusted), plus
# `fleet_highwater.json` -- the marks that make a lost stream visible. A directory loss takes
# the marks with it, and then this commit is the only surviving evidence that the books ever
# held more rows than the disk shows.
#
# Secrets (repo -> Settings -> Secrets and variables -> Actions): SITE_BASE_URL and
# ADMIN_TOKEN. Both already exist. DISCORD_WEBHOOK_URL optional.

on:
  workflow_dispatch: {}          # run it by hand, e.g. right before touching Render
  schedule:
    # Sunday 06:41 UTC. Weekly matches the track's cadence, and an ODD minute for the same
    # reason track-backup uses :17 -- GitHub routinely drops top-of-the-hour runs. Offset
    # from :17 so the two backups do not contend for the same service.
    - cron: "41 6 * * 0"

permissions:
  contents: write                # writes files to the repo and nothing else

concurrency:
  group: fleet-backup
  cancel-in-progress: false

jobs:
  backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"

      - name: Pull the fleet records from the live service
        env:
          BASE: ${{ secrets.SITE_BASE_URL }}
          TOKEN: ${{ secrets.ADMIN_TOKEN }}
        run: |
          set -euo pipefail
          if [ -z "${BASE:-}" ] || [ -z "${TOKEN:-}" ]; then
            echo "::error::SITE_BASE_URL and ADMIN_TOKEN must both be set as Actions secrets."
            exit 1
          fi
          # -f so an HTTP error is a FAILED STEP rather than a committed error page. That
          # matters more here than anywhere: silently committing {"error":"unauthorized"}
          # over a good backup would destroy the thing being backed up.
          curl -fsS "$BASE/admin/export-fleet" -H "X-Admin-Token: $TOKEN" -o fleet.json
          python - <<'PY'
          import json, sys
          d = json.load(open("fleet.json"))
          if not d.get("ok"):
              print("::error::export endpoint returned an error:", d.get("error"))
              sys.exit(1)
          e = d.get("export") or {}
          print("books:", e.get("n_books"), "| rows:", e.get("n_rows_total"),
                "| highwater:", (e.get("highwater") or {}).get("state"))
          # A stream whose chain was ALREADY broken is backed up and SAID SO, never hidden:
          # a restore that silently reinstates a break as sound is worse than no restore.
          for b, v in sorted((e.get("books") or {}).items()):
              c = (v.get("chain") or {})
              if v.get("ok") and not c.get("ok"):
                  print("::warning::book %s has a BROKEN chain in this backup: %s"
                        % (b, c.get("reason")))
          PY

      - name: Snapshot the committed backup, so the guard has something to compare against
        run: |
          set -euo pipefail
          # Taken BEFORE the render, because the render overwrites data_export/ in place.
          mkdir -p .guard-fleet/fleet_records
          git show HEAD:data_export/fleet_highwater.json > .guard-fleet/fleet_highwater.json \
            2>/dev/null || true
          for f in $(git ls-tree --name-only HEAD data_export/fleet_records/ 2>/dev/null); do
            git show "HEAD:$f" > ".guard-fleet/fleet_records/$(basename "$f")" || true
          done
          ls -l .guard-fleet/fleet_records/ || true

      - name: Render the backup, and refuse to lose a row of any book
        run: |
          set -euo pipefail
          # --guard-against fails the step when ANY book comes back with fewer rows than the
          # committed copy. LA2's lesson, applied in advance: a relative guard alone is not
          # enough, which is why the absolute check below exists too.
          python -m valuation.edge.fleet_export \
            --from-json fleet.json --out data_export --guard-against .guard-fleet
          rm -rf .guard-fleet

      - name: The high-water marks must be present, not merely un-regressed
        run: |
          set -euo pipefail
          # ABSOLUTE, not relative — LA2 found a series that had never been backed up at all
          # staying green for months, because zero is never fewer than zero. The marks are the
          # part that cannot be reconstructed from the streams themselves, so their ABSENCE is
          # the failure worth naming.
          python - <<'PY'
          import json, sys
          m = json.load(open("data_export/fleet_highwater.json"))
          books = (m or {}).get("books") or {}
          print("high-water marks in the backup:", len(books), sorted(books))
          if (m or {}).get("state") == "UNREADABLE":
              print("::error::the high-water marks came back UNREADABLE. They are the only "
                    "evidence that a stream ever held more rows than it now does.")
              sys.exit(1)
          PY

      - name: Commit if anything changed
        run: |
          set -euo pipefail
          git config user.name  "valquo-fleet-backup[bot]"
          git config user.email "actions@github.com"
          git add data_export/fleet_records data_export/fleet_highwater.json
          # The export is deterministic apart from `generated_at`, which the renderer does not
          # write to disk, so "no diff" is the normal outcome on a quiet week.
          if git diff --cached --quiet; then
            echo "no change since the last fleet backup"
            exit 0
          fi
          git commit -m "Fleet backup: record streams as of $(date -u +%Y-%m-%d)"
          git push

      - name: Say so if the backup failed
        if: failure()
        env:
          HOOK: ${{ secrets.DISCORD_WEBHOOK_URL }}
        run: |
          if [ -n "${HOOK:-}" ]; then
            curl -fsS -X POST "$HOOK" -H "Content-Type: application/json" \
              -d '{"content":"⚠️ Valquo **fleet backup FAILED**. The fleet record streams are one of the two datasets that cannot be rebuilt — check the Actions run."}' || true
          fi
```

---

## What is already landed and needs nothing from you

* **`GET|POST /admin/export-fleet`** — the door this cron calls. Token-gated with `_admin_ok`,
  the same as `/admin/export-track`, and a **pure read**: it writes nothing and advances no
  mark. Verified from the service's own response body **before** it shipped
  (`/admin/export-fleet` → HTTP 404) so the after-state is checkable.
* **`valuation/edge/fleet_export.py`** — the payload, the renderer (`--from-json … --out`) and
  the anti-regression guard (`--guard-against`) the workflow above calls.
* **`valuation/edge/fleet_highwater.py`** — the marks, enforced in `fleet.record`, the only
  write door. 24 tests, including the audit's exact scenario reproduced: the chain returns
  `ok: true, vacuous: true` on a deleted stream and the write is refused anyway.

## What this PR does NOT do, named so it is not mistaken for done

* **It does not make a lost DIRECTORY visible.** The marks are a sibling file and die with the
  directory. This backup is the layer that covers that, and only from the last commit onward.
* **It does not restore anything.** Restoring is a deliberate human act — copy the CSVs and the
  marks back — and there is no one-call restore, for the same reason there is no `reset()` in
  `fleet_highwater`: recovering from a real loss is a decision about evidence, and a single
  function turns it into a reflex.
* **It changes nothing about what the fleet records or when.**
