# RUN_RULES.md — non-negotiables. Read at the start of every session.

Short on purpose. A long checklist gets ignored; these are the things that have actually cost this
project time, and each one is here because it went wrong at least once.

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
