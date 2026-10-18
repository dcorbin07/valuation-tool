# PROMPT — options lane — 2026-10-17 (b) — make the in-hours fleet schedule a REPLACEMENT, so Don installs once safely

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) and your commits
`320afb8`, `d45877f` and `b232f2f` first.

`install_workflows.bat` installs **everything** in `pending_workflows/`. Right now that is the
auditor-cleared `live-cycle.yml` plus your `fleet-cycle-in-hours.yml`. The second would be
**added beside** `fleet-cycle.yml`, so two schedules would run and each could enter, which is the
double-fill your own file warns about. Don does not edit or disable things on GitHub by hand.

1. **Turn the handover into a replacement of `fleet-cycle.yml` itself**: the same filename, the
   12:00Z cron, and the body otherwise verbatim. Delete `fleet-cycle-in-hours.yml` from
   `pending_workflows/`.
   - Your measurement that the cycle lands about 17 minutes before the dip recorder every day is
     reason enough on its own, whether or not out-of-hours option orders work.
   - Confirm that one install leaves exactly one fleet schedule.
2. **Report from the next cycle's own body**, using the broker-state fields you just added:
   - are the fleet paper keys present, and is the dedicated fleet account in use?
   - did any book (F-21, F-22, F-8, F-11, F-4b) produce a candidate or an order, and what did
     Alpaca answer?
   - with the clock fixed, do F-21, F-22 and F-11 now see the dip series?
3. Tell Don in one line when he can double-click `install_workflows.bat`. The app fixer's item 69
   adds no workflow.

Paper only; no real trades. Done means on origin/main, with a plain-words summary for Don.
