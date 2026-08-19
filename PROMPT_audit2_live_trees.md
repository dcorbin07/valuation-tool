# COMMISSION — Cold audit #2: the live product and the trust infrastructure

You are a cold auditor. You have no history with this codebase, and that is your entire value:
you see what insiders no longer can. Work in `C:\Users\donni\Downloads\valuation-tool`.
**STRICTLY READ-ONLY** — you change nothing, fix nothing, commit no code. Your only outputs are
the three deliverable files named at the end.

## What this audit is, and is not

This is the second audit. The first (`VALQUO_EDGE_AUDIT.md`, 134 items) read the backtest tree
and its findings are largely executed — `VALQUO_LEDGER.md` is the index of what happened to every
item. **You are auditing what the first audit never read**: the live product and the
infrastructure the project now trusts its own claims to.

**IN SCOPE:**
- `valuation/engine/**`, `valuation/data/**`, `valuation/screener/**` — the live valuation and
  scoring path (fair values, scores, the hot list, providers, FX, beta).
- `valuation/web/**`, `valuation/saas/**`, `valuation/report/**` — every surface a visitor, the
  demo link, or an outbound message (Discord, email, exports) can reach.
- **The trust layer, as CODE**: `web/withhold.py`, the publication decision in `engine/`,
  `edge/freeze_book*`, `edge/track_meter*`, `edge/paper_track.py`, `edge/results_file.py`,
  `scripts/research_log*`, `scripts/build_ledger.py`, `.github/workflows/**`, the backup scripts,
  `PAPER_TRACK_CONTRACT.md`'s enforcement points (the headline gate, the recorders).
- `scripts/ci_scan.py` and every scheduled/automated path that writes a record.

**OUT OF SCOPE — do not spend a page on it:**
- Re-adjudicating any research verdict (ADOPTED/REJECTED/NULL calls in the registers stand; you
  may audit whether the CODE enforces them, not whether they were right).
- The in-flight edge research (the dead-themes measurement, Session 17+). Moving targets void
  audits — the project learned that the hard way (item O16).
- **Proposing new signals or strategies.** That roadmap exists and is disciplined. If you cannot
  resist, one appendix page maximum, clearly labelled untested speculation.

## How to work

1. **Verify, do not trust.** `CLAUDE.md`, the handoffs, and the ledger are CLAIMS. Where a claim
   is load-bearing (a default, a threshold, a "this is fixed", a file:line cite), check it against
   the code as it stands. Sample at least 25 load-bearing claims and report the hit rate — the
   project ran this once (62 claims: 43 current, 6 wrong) and the exercise paid.
2. **Prove guards fire.** A guard that has never failed a bad input is indistinguishable from one
   that cannot. The suite has known-bad fixtures (`tests/test_withhold.py`, the M3 work) — check
   coverage: which guards have a fixture that would catch their target bug, and which are
   protected only by prose. List every guard without one.
3. **Hunt the recurring classes first, then hunt what nobody has named.** These classes each bit
   this project multiple times; assume more instances exist:
   - **units/currency mismatches** (millions vs dollars, local vs USD — `net_debt`, P7);
   - **silently-empty inputs** (wired columns null for the entire history — five factors, 43% of
     live weight);
   - **two recorders / two sources of truth** (the Discord divergence, three composites);
   - **guards that cannot see** (`if base_fv and …` dead when the value is withheld; `rule_fired`
     computed and never read);
   - **fixed field lists dropping computed values** (the snapshot INSERT, `build_payload`);
   - **positional reads of named data** (`.iloc[0]` taking the S&P's growth as Berkshire's);
   - **clamps disguising garbage as plausible values** (`min(1.0, nan)` → 100% growth).
   After those, read for what has never been named. The best finding of the last audit was a
   class nobody had listed.
4. **Every finding carries**: file:line · what is wrong · the evidence (measured or quoted code,
   never inferred) · blast radius (who sees a wrong number, or what record corrupts) · the
   cheapest way to verify or refute it. Severity: BLOCKING / HIGH / MEDIUM / LOW. If you assert
   something you could not verify, mark it HYPOTHESIS.
5. **Practical notes**: use `rg --no-ignore` for any search touching `valuation/data/` and
   confirm whether the unanchored `data/` gitignore pattern is still live before trusting any
   clean grep. Licensed data (`data/`, Sharadar, ThetaData) is gitignored — its ABSENCE from git
   is correct, not a finding. The site is public and free by design; the public/owner/demo split
   is intentional — audit its enforcement, not its existence.
6. Work as long as the findings justify and no longer. Depth of evidence beats page count. Ask
   Don questions only when an answer changes what you audit; otherwise record the assumption and
   proceed.

## Deliverables (the only files you create)

1. `VALQUO_LIVE_AUDIT.md` — findings IDed **LA1, LA2, …**, ordered by severity, in the format of
   rule 4. Open with a one-page honest summary: the three worst things, the overall state, and
   what you could NOT check and why.
2. `valquo_live_audit_items.json` — one entry per item: id, title, severity, files, class, so the
   execution machinery that processed the first audit can process this one.
3. `VALQUO_LIVE_AUDIT.pdf` — the readable version for Don.

Do not update the ledger, the handoffs, or anything else — the executing lanes do that when items
run. When finished, state plainly how many items, the severity split, and your one-paragraph
overall verdict on whether the live product can be trusted to say what it knows.
