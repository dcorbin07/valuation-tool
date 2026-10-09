# PROMPT — app fixer — 2026-10-09 — item 44

Read `DECISIONS.md` first.

1. **A correction to your item-42 report.** You wrote that the `53 17-19` backup cron "is still not
   installed". It IS: `.github/workflows/auto-scan.yml` on origin/main carries it, installed at
   d66155e on 2026-10-08 08:15 ET, and the intraday job's `if:` already matches it. Your worktree
   was reading a stale copy. Start the one-week re-measurement from 2026-10-08, and fix whatever
   made the check read the wrong copy.
2. **Run the Tradier history measurement where the working token lives.** Your lane's token returns
   401 while the service's works. Do not ask for or handle any token. Write a dispatchable
   (`workflow_dispatch` only, no schedule) workflow that runs your existing measurement script with
   the repository's existing `TRADIER_TOKEN` secret — read-only market-data calls only, nothing that
   can place an order, token never echoed — and uploads the result as an artifact. Put it in
   `data/pending_workflows/` for Don to install with `install_workflows.bat`, and tell him the one
   click to run it. Then report the measurement. Nothing is enabled.
3. You noted broker fundamentals loaded 0 of 1,500 names. Say whether anything depends on them
   today; if nothing does, record it and move on.

Done means on origin/main, with a plain-words summary for Don.
