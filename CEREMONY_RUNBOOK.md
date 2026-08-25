# CEREMONY_RUNBOOK.md — the declaration ceremony, packaged for the executing lane
## Frontier Scout, 2026-08-24. For Don to route to the options-bot lane (the harness owner).

**Why this is a runbook and not the ceremony itself, in one paragraph:** the scout drafted
all twenty declarations. Under the charter (`PROMPT_frontier_scout.md` §0: no tests run, no
files outside the scout's own, no dispatch) and under the fleet's own logic, **the author
may not also be the acceptor** — twenty self-acceptances would be the "list of results
someone liked" failure in a new costume, and "the executor may still reject it; that is
their right and the system working" only functions when the executor is a different mind.
Two of the ceremony's steps are also physically impossible from the scout's sandbox (no
network to the Tradier sandbox for the self-verification's real fills; no push). So this
file makes the ceremony a **one-session job for the executing lane**, with the scout's own
adversarial notes attached so rejections are easy.

## 0. Preconditions (all checkable in one minute)

1. **The scout branch must land first** — `worktree-scout-brainstorm` (3 commits:
   `3b9bda7`, `ed58d7f`, `c9d0012` + this session's) holds the 20 `DECL_DRAFT_*` files.
   **As of this writing it has NOT landed** — one `sync.bat` / push, then the Action.
2. S3-I1 (harness, `9b1d064`), S3-I3 (`f676f69` + `30c52e5`) merged to main — confirm on
   `origin/main`, not on a branch ref.
3. The S3-I3 short-leg consumer set is **F-4, F-6, F-7, F-8, F-10, F-17, F-18** (the
   lane's own verified list; the map is amended to match).

## 1. Day-1 self-verification FIRST (the gate; green before anything declares)

Per the harness register §4, the run-#6 pattern: declare a throwaway **TEST-BOOK** (its
declaration says it is a test and will be closed), place one real sandbox fill through the
recorder, and prove: append-only round-trip bit-identical on read-back; the hash chain
detects a tampered row (run the tamper case, don't assume it); the refusal tests fire (a
short test-declaration without the §1.4 module is REFUSED); the F-1 randomizer reproduces
its per-order assignment from (book, date, symbol). **Then close the test-book with a
zero-charge closing row.** If any leg fails: fix the harness, not the check (`RUN_RULES`
A-5), and re-run. Nothing declares until this is green end-to-end against the real sandbox.

## 2. The ceremony: twenty accept-or-reject decisions, map order

**Each accepted declaration commits ALONE, touching exactly one file** (rename
`DECL_DRAFT_x.md` → `DECL_x.md` in the commit that accepts it — the rename is the
acceptance; the commit is the tamper-evidence). **Each rejection goes back to the scout
with the reason — a rejection costs nothing and is the system working.** Order: F-1, F-2
(gate), F-3, F-5, F-6, F-19 (gate), then Wave 2: F-4, F-7, F-8, F-10, F-17, F-18 (the
seven short books — confirm the §1.4 interface text in each against the LANDED S3-I3, not
against the map), then F-9, F-11, F-12, F-13, F-14, F-15, F-16, F-20.

**Per-book acceptance checklist (the harness refuses on 3 and 4 — let it):**
1. Entry rule computable at order time from named live data — no judgement words survive.
2. Strikes moneyness-fixed on **as-traded** spot (S3-I3's C3 put a number on why: 29.1% of
   assignment verdicts flip on adjusted closes).
3. Short books: §1.4 interface present and matching the landed module (secured-cash
   denominator confirmed unchanged; worthless-short-expiry settles at ZERO, not −100% —
   `MA36`'s rule is the long-side rule and the module knows the difference).
4. Verdict-horizon field complete, field-by-field (fills/month projection + fills-needed +
   earliest-read date + both power vocabularies). **If the harness refuses, fix the draft
   and re-commit — never soften the check.**
5. Gates (F-2, F-19): no positions, host-attachment rule present, labeling-vs-refusing
   semantics as declared.
6. One ledger row per accepted book, written by THIS lane at declaration (status DECLARED,
   no verdict, zero trials — the charge comes at first verdict read per harness §2).

**The scout's own adversarial notes — where a real executor should push hardest:**
* **F-13** (second-event): the both-dates-known constraint may starve the book below any
  honest horizon — demand the eligible-count census before accepting, and reject if it
  reads under ~5/month.
* **F-16** (13F surge): a 6-quarter book at 5 fills/quarter is the fleet's slowest —
  reject if the lane judges the sandbox's lifetime horizon shorter than that; the idea
  survives as a Track B register later.
* **F-7/F-8** (counterfactual mechanics): both depend on reading the paper book's own
  band/selection state cleanly — if that read requires touching the scoring path rather
  than a published artifact, reject and send back for a cleaner state source.
* **F-14** (FDA): S3-I2's calendar started accruing ~2026-08-2x — accept only with the
  forward-only caveat restated in the commit message; the skips-are-controls design is the
  part to keep.
* **F-12/F-13**: both carry EVOWN's NOT-DEMONSTRATED family verdict as a stated hostile
  prior — acceptance should re-affirm that the prior is on the declaration's face.

## 3. The RUNNER — stated plainly, and routed

**What executes the daily fill cycle:** a process needing three things at once — the
Tradier sandbox token, network, and the fleet records store. **`PT-WRITER`'s lesson is the
architecture:** Cowork had the book but no network; the GitHub runner had network but no
book; **Render had both** — the writer became a GitHub Actions cron POSTing the service's
admin door, proven by run #6 GREEN. The fleet runner is the same shape: a
`fleet-cycle` endpoint on the Render service (it holds token, network, and records),
kicked daily by a scheduler.

**Routing (the sanctioned paths only — `.github/` is untouchable to every agent lane):**
* **Primary: a Don PR** adding `fleet-cycle.yml` (cron, weekdays, POST the door) — the
  exact `track-row.yml` precedent, PR #2's shape. One small PR, permanent.
* **Fallback: a Cowork scheduled task** that hits the service door daily until the PR
  lands.
* The endpoint itself is options-bot lane work (service code, not workflow code) and can
  land through the normal gate.

**LOUDLY: until one of those exists, the fleet is DECLARED-BUT-UNSCHEDULED — twenty frozen
entry rules and zero fills accruing. Declaring without scheduling is a paper fleet in the
worst sense.** The ceremony session should end by either landing the endpoint + requesting
the PR, or saying in its handoff, in bold, that the fleet is not yet breathing.

## 4. The count to report when the ceremony ends

Books declared / books refused (with reasons, back to the scout) / fills-pending-on:
the runner PR or task, and nothing else.
