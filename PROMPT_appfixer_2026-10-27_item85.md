# PROMPT — app fixer — 2026-10-27 — item 85: a workflow install from an old lane folder rolled two live workflows back ten days

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.** Read your item 84B and item 74.

## What happened, measured by the manager

- Commit **`ad29600`** (2026-10-27 12:05Z, "Install workflow(s): fleet-cycle.yml live-cycle.yml
  (via install_workflows.bat)") replaced both files on main with **10-16 / 10-17 versions**.
- Every item-74 step is gone from both files: the healthchecks start/end pings and the "tell Don
  this failed" Discord step. `live-cycle.yml` also lost item 65's per-field summary, the
  cycle-body artifact and the fractional/settlement census. The installed `live-cycle.yml` still
  carries `PENDING INSTALL 2026-10-16 (item 64)`.
- **The source is `.claude\worktrees\dipcall\`.** Its `pending_workflows\` holds exactly two
  files, `fleet-cycle.yml` (6,974 bytes, 10-17) and `live-cycle.yml` (9,295 bytes, 10-16). Those
  are the two names and versions installed, so the installer was run from that folder.
  `install_workflows.bat` copies `%~dp0pending_workflows\*.yml` from **whatever folder it sits
  in**, over a fresh `origin/main` worktree.
- Don's main folder is also **27 commits behind** origin. Running the installer from there would
  roll back any workflow that changed on main after 2026-10-20.
- **Item 84B's hot-list catch-up (`auto-scan.yml`) was NOT installed** by this run. Don ran the
  manual hot scan at 22:08Z and it succeeded.
- Still `?run=paper` and no live order is reachable. Today's five live cycles all returned 200.
  But a live-cycle or fleet-cycle failure would not now reach Discord, and healthchecks.io gets
  no pings for either job.

## The fix

1. **The installer takes pending files from the fetched `origin/main`** — its tracked
   `pending_workflows/` inside the temp worktree — and never from the folder the bat sits in.
   - The legacy `data\pending_workflows` route either goes, or requires an explicit typed
     confirmation naming the files.
   - Before committing, print per file whether it is NEW, CHANGED or unchanged against
     `.github/workflows`. Refuse if the file being installed is older in git history than the
     one it replaces.
   - Refuse to run from inside `.claude\worktrees\`.
2. **Restore both workflows and install 84B's `auto-scan.yml`** by putting the correct current
   versions in tracked `pending_workflows/` on main, so one run of the fixed installer puts all
   three right.
   - Show in the summary that item 74's healthchecks and Discord steps are back in both files,
     and that the send token is still `?run=paper`.
3. **A test** that fails whenever an installed workflow on main lacks a step its tracked
   `pending_workflows/` copy carries — today's regression exactly.
4. **Tell Don exactly what to run**, in order:
   - how to bring his main folder up to date without publishing anything (a `.bat` if there is
     none);
   - then the installer;
   - then what he should see.

   Also say whether he should delete or ignore `install_workflows.bat` inside the old worktree
   folders.
5. **Report from today's cycles, if readable:** did the paper account's self-heal trim run, and
   is its cash back to about zero?

## Done

On origin/main, with a plain-words summary for Don. No key printed, no live order, no percentage
changed, nothing appended to the record, no direct `.github` change.
