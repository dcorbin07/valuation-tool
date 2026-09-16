# Youtube Stuff — start here
*Assembled 2026-09-15. One session's worth of research, a decision, a plan, and a running piece of code.*

## What is in this folder

| file | what it is | read it when |
|---|---|---|
| `01_Channel_Decision_Brief.md` | the recommendation (football + engine, finance sequenced later), the evidence, the economics, the pre-committed re-read criteria, and what would change the call | first |
| `02_Channel_Blueprint.md` | positioning, name candidates, the two weekly slots, the 10–15-hour rhythm, the offseason plan, the first twelve videos, gear, packaging, disclosures, the monetization ladder | when you are ready to plan the first month |
| `03_Engine_Design_Spec.md` | the rigorous start/sit engine: what it claims and does not, the two clocks, data layers and sources, the leakage catalogue, the full feature taxonomy with priors, the model stack, the evaluation harness, what is honestly backtestable, the forward track, build phases, costs | before writing any model code |
| `04_Compliance_Checklist.md` | what to check in AUB's policies, the outside-activity request language, disclosure rules, the fantasy-vs-betting line, the finance-content rules for later | this week, before recording |
| `05_Research_Notes_and_Sources.md` | condensed findings from the three research passes with every source URL | when you want to check a number |
| `ff-engine/` | **working code**: the capture pipeline (store, sources, snapshot, verify, as-of loaders), 16 passing offline tests, systemd units for the Oracle VM, the rules file, the ledger, and the first three pre-registrations | this week — the timers need to be running |

## The three things to do this week, in order

1. **Deploy the capture pipeline** (`ff-engine/deploy/README.md`). The free injury data has had no timestamps since 2025 and lines get overwritten at close; every uncaptured week is unbacktestable forever. The nflverse side is verified; the first `--dry-run` from your machine is the real test of the Sleeper, weather and odds adapters (that machine could not reach them from here). This is register `PREREG_000`.
2. **Read AUB's code of conduct and file the outside-activity request** for a fantasy-analysis channel, using the scope language in `04`. Get the approval in writing before the first upload.
3. **Pick the name and register the handles** (candidates in `02`; none checked for availability). Then film video 1.

## What was verified versus taken from research

Marked ✔ in `05`: the Partner Program change (YouTube's own August 10 post), the nflverse file inventory and the missing `date_modified` column (downloaded and inspected), depth-chart timestamps (179 snapshots in 2026), the `nflreadpy` deprecation note, the Sleeper terms, the FantasyPros API tiers, The Odds API historical-props date, and the Fantasy Football Analytics variance figures. Channel statistics are third-party snapshots and approximate. Compliance content is informational, not legal advice.
