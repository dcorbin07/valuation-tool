# RUN_RULES.md — non-negotiables. Read at the start of every session.

Short on purpose. A long checklist gets ignored; these are the things that have actually cost this
project time, and each one is here because it went wrong at least once.

**New to the repo?** `START_HERE.md` is the clone-to-number page. **"Is item X done?"** is answered
by `VALQUO_LEDGER.md` and nowhere else.

---

## PART 0 — OPERATING INSTRUCTIONS (moved here 2026-08-15, master audit MA22)

*These four sections lived at the top of `CLAUDE.md`, which is now 4,100+ lines prepended to every
session. Instructions buried in a findings record rot: that file carried **three different counts of
its own test suites** — "24", "62" and, measured, **83** — and its task list self-described as "the
least trustworthy section in the file". Operating instructions belong in the short file that is read
first. `CLAUDE.md` keeps the findings record, which is load-bearing and was not trimmed.*

### 0.1 How to run (you can run these directly — Don cannot / will not)
- **Full backtest:** `python -m valuation.edge.fundamental_panel --data-dir data/backtest --json data/backtest/last_result.json` (or `run_backtest.bat`). Reads licensed Sharadar exports in `data/backtest`. Takes 20–40 min.
- **13F due-diligence:** `python -m valuation.edge.fundamental_panel --data-dir data/backtest --validate-institutional` (or `validate_13f.bat`).
- **Tests — and `test_edge.py` is NOT the gate.** The auto-land Action runs **every** suite in
  `tests/` (audit C7), so verify the same way before pushing:
  ```bash
  for f in tests/test_*.py; do python "$f" || echo "FAILED $f"; done
  ```
  **Never quote a hard-coded suite count** — three stale ones are what produced this section.
  Count them when you need the number: `ls tests/test_*.py | wc -l`.
  **Judge a suite by its EXIT CODE, never by grepping for `OK`.** They print at least three summary
  formats (`OK`, `20 passed, 0 failed`, `14/14 bulk tests passed`), and a loop scraping for `OK`
  reports `test_build_ledger`, `test_bulk` and `test_calibration` as FAILING when they pass. A gate
  that cries wolf is one you learn to ignore.
- **Local install:** `pip install -r requirements.txt`. **Not** `requirements.lock.txt` — that is a
  hash-pinned linux/CPython-3.11 lock for CI and the container and will not resolve on Windows (MA12).
- **Deploy:** landing on `main` deploys. See 0.3.

### 0.2 HARD RULES (do not violate)
- **Never commit/push `data/`** (licensed Sharadar exports; gitignored) or `*.db`.
- **`.env` holds real secrets** (SHARADAR_API_KEY, ANTHROPIC_API_KEY, TRADIER_TOKEN, SECRET_KEY) — never print, commit, or overwrite.
- **Do NOT execute trades or move money** — a Robinhood connector exists (Cowork side); produce target/rebalance lists, Don executes.
- **Ignore Don's resume files entirely.**
- Repo is private; keep it clean. Keep the suites green after every change.
- **Sharadar data is personal-use only and forbids commercial use of it "or any derivation"**
  (ledger `D1`); the JKP factor data is CC BY-NC 4.0, research-only, and may never ship in the
  product. Both constraints travel with any number derived from them.

### 0.3 Git handoff — MERGING IS AUTOMATIC. DO NOT MERGE `main` BY HAND.
Several agents share the primary checkout and `main` moves under you mid-session, so a hand-merge
there can clobber another lane. The close-out is:

1. Commit in your worktree.
2. `git push -u origin worktree-<name>`
3. **Verify it landed:** `git fetch origin main -q` then `git merge-base --is-ancestor HEAD origin/main`.

The Action installs the pinned dependencies and runs every suite, so allow time. If it never lands,
the gate failed or the merge conflicted and `main` is **deliberately** untouched — fix the branch, do
not merge by hand. **Do not strand work on an unpushed branch** (twice, the P5 and held-out work sat
unmerged while `main` stayed on P4; and a commit holding the answer to `PT-WRITER` sat unpushed for
five days). On Windows PowerShell, paste commands on SEPARATE lines — its shell rejects `&&`.

**A branch that changes `.github/` or deletes a test suite will be REFUSED by the auto-land policy
and needs a human (MA11).** That is intended: those are changes to the gate itself.

### 0.4 Tool routing — Claude Code vs Cowork (tell Don when to switch)
Don runs TWO agents. They do not talk live; they sync through this shared git repo.

- **You (Claude Code)** own: running the backtest / tests, editing this codebase, git, quant
  research — anything that executes code locally. Do these yourself rather than handing Don a `.bat`.
- **Cowork** owns: the Robinhood connector (read-only account data + rebalance lists — NEVER execute
  trades), the tracked "Valquo Index vs SPY", scheduled scans/tasks, and phone/mobile sessions.

When a task needs Cowork, say so plainly: **"→ Take this to the Cowork chat — it needs the Robinhood
connector, which I don't have here."**

### 0.5 Working with Don
Concise, direct, honest. He is non-technical but sharp and rightly skeptical — show reasoning and
caveats, don't inflate.

### 0.6 End of every session
Overwrite `HANDOFF_STATUS.md` (shared project state: what you did, concrete numbers, what's blocked,
the recommended next step — plain markdown, factual). Write your **full** write-up to your own
`HANDOFF_<name>.md`, so parallel agents never clobber each other. Cowork reads both directly, so Don
never has to screenshot.

---

## PART A — EVERY AGENT, EVERY RUN. No exceptions.

**1. "Done" means PUSHED, not written.**
Commit, push, then **verify** the push landed (`git log --oneline -1 origin/<your-branch>`). If you finish
without pushing, your work is invisible — the manager reads `origin/main`, sees nothing, and re-issues the
task. That has already happened. Never end a run without confirming the push.

**2. Write the handoff BEFORE you report done.**
`HANDOFF_<yourname>.md`, per item, in the project's format: committed threshold (written *before* the run) ·
what was run (command, universe, date range, n) · the numbers · verdict (ADOPTED / REJECTED / NULL /
INCONCLUSIVE / DEFERRED) · the mechanism, not just the number · what it unblocks or forecloses.
**Code without a handoff entry is not finished work.**

**3. Report every bug you find — including outside your lane.**
A `## BUGS FOUND` section in your handoff. Anything you noticed and did not fix goes there too, with the
file:line. Bugs found in passing have been some of this project's most valuable output; losing one because it
"wasn't my item" is unacceptable.

**4. State what you did NOT do, and why.**
Deferred, partial, or impossible items get recorded explicitly — never left looking complete. If a thing
half-works, ship the flag that says so (e.g. `prefilter_adv_wired: false`) with the reason attached.

**5. Never silence a check to make a run green.**
A failing sanity flag, a coverage warning, a red test: investigate it or record why it is expected. Turning
it off is the single fastest way to reintroduce a bug this project already paid for.

**6. Thresholds are committed BEFORE the run, in writing.**
If you did not pre-commit one, say so and mark the result **provisional**. A result that is ambiguous against
its own threshold is a **null**, not a judgement call.

**7. Keep the suites green. If a test fails, report it — do not skip it.**

**8. Verify the audit's claims; do not obey them.**
`VALQUO_EDGE_AUDIT.md` is code-reading hypotheses with file:line citations, not scripture. Where it is wrong,
prove it and record the correction (B25 is precedent — the two Deflated Sharpe implementations *did* reconcile).

**9. Store the draws, not just the summary.**
Any sweep, bootstrap, permutation or grid ships its **per-draw rows** alongside the percentiles — and banks the
*inputs* to every derived statistic, not only the derived number. Cost so far: X7 kept 100 placebo draws as
five summary rates, so re-denominating one column meant re-running the whole 3.4-hour sweep, and an 8%-vs-7%
mismatch in a second column sat "undiagnosable" for two sessions. A summary answers the question you had; the
draws answer the one you get asked later, and you will be asked.

**10. An incremental-IC register states its BASIS and prints its EFFECTIVE coverage.**
The PEAD/U2 template residualises a candidate on the seven weighted incumbents and drops rows missing any
of them. On this panel that silently costs **20 of 69 rebalance dates** — `institutional` covers 71.7% and
its first date with 20+ names is **2014-01-17**, while every other weighted theme starts 2009-01-15
(verified by leave-one-out: dropping any *other* incumbent still leaves 49 dates). The damage is not the
dates, it is that **the shipped `MIN_DATES = 16` floor gets checked against a date set the statistic never
uses**: `halves()` passes at 34/34 on the raw covered dates and the residualised statistic is then scored
on an early cell of **14**. So: name the basis with `incremental_ic.basis_for('six'|'seven')` — it has NO
default, deliberately — say in the register *why*, print `effective_coverage()`, and **split the EFFECTIVE
dates, never the raw ones** (49 → 24/24, and disclose that the boundary moves). Run the power controls on
those same rows. A register reporting one date count for its coverage and a different one for its verdict
has not satisfied this rule. Cost so far: `MA58-SEAS` returned `UNINTERPRETABLE` partly on this, and the
audit's own claim that `U2`/`MA31`/`MA32` inherited it is **false** — they score on the post-2016 options
layer and are immune by construction, which is exactly the rule: **you are exposed only if your covered
window reaches back before 2014-01-17.**

---

## PART B — COWORK (the manager). Failure modes, and the rule that closes each.

**1. Never assert an agent's status without checking for unpushed commits.**
If a branch is ahead of `origin/main`, the answer is **"unknown until synced"** — never "not done." Cost so
far: one redundant Session-2 instruction to an agent that had already finished it.

**2. Every prompt states three things, or it is not sent:**
its **audit session**, whether the **previous session is verified complete** (checked in the handoff, not
assumed), and its **`needs first` list** with each dependency's status. If it is not a catalogue item, label
it **OUT-OF-BAND** explicitly.

**3. `check_lanes.py` answers collisions ONLY.**
It does not answer "are this item's inputs correct yet?" Collision-safe ≠ dependency-ready. Conflating them
put R1 on an uncorrected panel. Its map also has known gaps (it reported "(nobody)" for `config.py` and
`screen.py` while the app-fixer lane was live in both) — treat it as advisory, cross-check `git log`.

**4. A provisional number carries its caveat in the same sentence.**
Not a paragraph later, not "worth noting." If it is provisional, the first mention says so.

**5. When unsure and verification is cheap, ASK — do not guess.**
Don would rather run `sync.bat` or send a screenshot than have the manager infer wrong. Guessing has cost
more time than asking ever has.

**6. Handoffs only cover finished, pushed work.**
An agent's live reasoning exists in no file. If the question is about work in flight, **ask for a
screenshot** — that is not a failure of the handoff method, it is its boundary.

---

## Automation status
- **Merging is automatic** — the GitHub Action lands any pushed `worktree-*` branch behind the test gate.
  So Part A rule 1 (push + verify) is the only manual link in the chain. If every agent obeys it, `sync.bat`
  becomes a status check rather than a repair tool.
- **`sync.bat`** (repo root, double-click) pushes anything stranded locally, updates `main`, and reports what
  has not merged. Run it when in doubt; it is idempotent and safe.
