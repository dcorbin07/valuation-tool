# Youtube Stuff — start here
*Assembled 2026-09-15, updated 2026-09-16 with your decisions: the football channel is **DonTalksBall** (football in general, fantasy mixed in); the non-football channel is **If I Had a Dollar** — all world events that move money, 12–25 minutes; local journalism becomes an Instagram idea; the newsroom's two scheduled tasks are live.*

## What is in this folder

| file | what it is | read it when |
|---|---|---|
| `01_Channel_Decision_Brief.md` | the original recommendation and evidence (football first, the economics, the base rates); a note at the top records the decisions since | for the reasoning |
| `02_Channel_Blueprint.md` | **DonTalksBall** operating plan: positioning, the Tuesday Rundown and Thursday Call, the channel scorecard, the Flex Finder segment, offseason, first twelve videos, gear, packaging, season targets, monetization | when you are ready to plan the first month |
| `03_Engine_Design_Spec.md` | the rigorous start/sit engine: what it claims and does not, the two clocks, data layers and sources, the leakage catalogue, the full feature taxonomy with priors, the model stack, the evaluation harness, what is honestly backtestable, the forward track, build phases, costs | before writing any model code |
| `04_Compliance_Checklist.md` | reference only (you have decided not to seek the bank's approval): disclosure rules that protect you, the fantasy-vs-betting line, the finance-content rules | if you ever want it |
| `05_Research_Notes_and_Sources.md` | condensed findings from the three research passes with every source URL | when you want to check a number |
| `06_Channel_Ideas_Rundown.md` | **the decisions and the status of every channel**: DonTalksBall, If I Had a Dollar (what the newsroom now does for it, twelve openers), the local Instagram idea, shared infrastructure, the next fourteen days | second — this is the working plan for everything that is not the engine |
| `07_Gear_Checklist.md` | the priced gear list in three tiers (what you probably own, ~$280–360 to buy now, the step-up after ten videos), software, what not to buy, and the two setups | before ordering anything |
| `brand/` | **If I Had a Dollar, final:** the masthead logo, the 2560×1440 banner and the 800×800 coin avatar (PNG for upload, SVG to edit) — name only, no strap under the title | when you set the channel up |
| `08_Canva_Prompts.md` | paste-ready Canva prompts for If I Had a Dollar if you want variations, plus the brand facts (colours, fonts, exact wording) to keep in any prompt. DonTalksBall artwork: to be made in Canva (burgundy #5A1414 / gold #FFB612, the D as a football with laces on its right) | when you open Canva |
| `newsroom/` | the **live newsroom**: the design (`NEWSROOM_PIPELINE.md`), the exact prompts of the two scheduled tasks (`WEEKLY_TASK_PROMPT.md`, `BREAKING_TASK_PROMPT.md`), and the prototype storyboard with a pre-written Fed script (`storyboard_2026-09-15.md`). Outputs land in your Google Drive folder **YouTube Newsroom** | Monday mornings, and whenever an alert reaches your phone |
| `flex-finder/` | **Flex Finder, the engine — working code**: capture pipeline (store, sources, snapshot, verify, as-of loaders), scoring, historical backfill, the evaluation harness (run on real 2023–2025 data), 29 passing offline tests, systemd units for the Oracle VM, the rules file, the ledger, the first three pre-registrations, the **factor catalogue**, and the **pilot brief** for the session that will build it | this week — the timers need to be running; hand `flex-finder/PILOT_BRIEF.md` to the building session |

## How the engine gets built from here

> **Update, later on 2026-09-15:** the building session now owns Flex Finder outright. Hand it `flex-finder/HANDOFF_TAKEOVER.md`; the manager-lane arrangement described below is retired (author ≠ acceptor is kept by making you, plus a cold-audit pass, the acceptor).

Two lanes, the way the valuation-tool runs Claude Code and Cowork: a **pilot (building) session** works from `flex-finder/PILOT_BRIEF.md` — Sprint 1 is deploy → verify the API adapters → backfill → wire the consensus rankers → the as-of frame builder → leakage tests → output pinning; and a **manager session** (this one) reviews `HANDOFF_pilot.md`, accepts or rejects registers, and keeps `LEDGER.md` honest. The author of a register never accepts it. `flex-finder/FACTOR_CATALOGUE.md` is the complete list of what could be tested — roughly 300 factors across 29 families, each with its data source, when it is knowable, and what the evidence says before testing — and the order registers should be drafted in.

## The things to do this week, in order

1. **Hand the building session `flex-finder/HANDOFF_TAKEOVER.md`.** Its first job is the capture timers; every uncaptured week of 2026 is lost for backtesting.
2. **DonTalksBall:** check the handles and a domain, make the artwork in Canva (burgundy #5A1414 / gold #FFB612, the D as a football with laces on its right side), order the Tier 1 gear from `07`, record video 1 (the thesis — you keep score on yourself in public).
3. **If I Had a Dollar:** register the handles; upload the avatar and banner from `brand/`; read the prototype storyboard tonight; after the Fed decides tomorrow, look for the alert on your phone and the same-day script in Drive; read Monday's storyboard and record one script as an unlisted pilot.
4. **Local:** decide whether you want the weekly Virginia scan scheduled.

## What was verified versus taken from research

Marked ✔ in `05`: the Partner Program change (YouTube's own August 10 post), the nflverse file inventory and the missing `date_modified` column (downloaded and inspected), depth-chart timestamps (179 snapshots in 2026), the `nflreadpy` deprecation note, the Sleeper terms, the FantasyPros API tiers, The Odds API historical-props date, and the Fantasy Football Analytics variance figures. Channel statistics are third-party snapshots and approximate. Compliance content is informational, not legal advice.
