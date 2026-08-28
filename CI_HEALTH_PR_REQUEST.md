# FOR DON — two small `.github/` changes: close the cron hole, and get back inside the budget

**2026-08-27, app-fixer lane.** `.github/` is untouchable to every agent lane (MA11's land
policy REFUSES any branch that touches it), so this is a request rather than a change.

**READ THIS FIRST, BECAUSE IT DECIDES THE ORDER: THE GATE IS NOT CRYING WOLF.** I measured 120
runs over 7.8 days before proposing anything, and **every red run in the window had a cause and
most had a real one.** The census is in `HANDOFF_appfixes.md` session 49; the short version is
that the land gate failed 5 times in 57 runs and every failure was correct — a merge conflict, a
genuinely broken suite the owning lane then fixed, and a data change made by a cron that never
passed the gate. Only the third is a hole, and it is change **1** below.

---

## 1. `track-backup.yml` — a cron that can redden the shared gate

**THE HOLE, and it fired for real on 2026-08-24.** `track-backup` runs on a schedule, pulls the
live record and **commits it straight to `main` without passing the land gate**. On 2026-08-24
it re-pointed `data_export/paper_track_history.json`, and `tests/test_paper_track.py` — which
asserts a fact **about that data** — went red. Five branches then failed to land with no lane at
fault, and `09ea4cc` had to go and repair a test that nothing in any lane had broken.

**Every other write to `main` in this repository passes the gate.** This one does not, so it is
the only path by which `main` can become red without a human or an agent having pushed code.
The same applies to `fleet-backup.yml`, which I asked for last session and which has the same
shape — it has not bitten yet only because the fleet has written almost nothing.

**THE FIX IS THE GATE'S OWN RULE APPLIED TO THE CRON: run the suites the commit can break,
before committing.** Add this step to `track-backup.yml` (and the same to `fleet-backup.yml`)
immediately **before** the "Commit if anything changed" step:

```yaml
      - name: The data this commit changes must not redden the shared gate
        run: |
          set -euo pipefail
          # A scheduled commit is the ONLY write to main that does not pass the land gate, so
          # it is the only way main can go red with no lane at fault. That happened on
          # 2026-08-24: this job re-pointed data_export/paper_track_history.json and
          # tests/test_paper_track.py -- which asserts a fact ABOUT that data -- went red for
          # five branches.
          #
          # Only the suites that READ the committed export are run. A full 176-suite gate here
          # would triple this job's cost to re-prove things a data refresh cannot affect.
          pip install -q -r requirements.txt || pip install -q pandas requests
          fail=0
          for f in tests/test_paper_track.py tests/test_fleet_manifest.py; do
            python "$f" || { echo "::error::$f FAILED against the refreshed data"; fail=1; }
          done
          if [ "$fail" -ne 0 ]; then
            echo "::error::REFUSING to commit refreshed data that reddens the shared gate. The data is not lost -- it is still on the service and this job can be re-run. Fix the test or the register first."
            exit 1
          fi
```

**WHY REFUSE RATHER THAN COMMIT-AND-WARN.** The refreshed data is not lost by refusing: it stays
on the service and the job can be re-run by hand any time. What *is* lost by committing is every
other lane's ability to land, until somebody works out that a cron did it. A backup that can
block five branches is worse than a backup that is a week late.

**The alternative I considered and rejected:** making the test tolerant of whatever the export
holds. That is silencing a check — `test_paper_track` is asserting a real property (the engine
must not record a truncated top-N list under the Index's name), and `09ea4cc` was right to
repair the register instead. The test is fine. The unguarded write is the defect.

---

## 2. `auto-scan.yml` — the intraday cadence, to get back inside 2,000 minutes

**MEASURED, AND IT CORRECTS THE ASSUMPTION I WAS GIVEN.** Over 7.8 days and 200 runs:

| workflow | runs/day | share of minutes | projected /30d |
|---|---|---|---|
| Land agent branch | 12.5 | **72%** | ~2,821 |
| Auto scans | 9.6 | 21% | ~835 |
| PT-WRITER | 1.3 | 6% | ~222 |
| FLEET CYCLE | 1.9 | 1% | ~54 |
| Track backup | 0.1 | 0% | ~1 |
| Fleet backup | 0.1 | 0% | ~1 |

**Total ≈ 3,933 minutes per 30 days against a 2,000-minute allowance — about 2× over.**

Two corrections to the stated prior, both measured. **Auto-scan is not 48 runs/day**: its
intraday cron is `*/30 13-20 * * 1-5`, so it is every 30 minutes for **eight hours on weekdays
only** — 16 runs a weekday, 9.6/day averaged. And **land, not auto-scan, is the dominant
consumer** at 72%.

**THE FOUR THAT CANNOT BE MISSED COST 278 MINUTES — 14% OF THE ALLOWANCE.** `track-row`,
`fleet-cycle`, `track-backup` and `fleet-backup` together are 7% of current usage. They would
fit inside the free tier seven times over. **Nothing below touches them.**

**The change:** widen the intraday cron from every 30 minutes to hourly.

```yaml
    - cron: "*/30 13-20 * * 1-5"    # BEFORE
    - cron: "23 13-20 * * 1-5"      # AFTER — hourly, on the same odd minute the others use
```

**Saving ≈ 420 minutes per 30 days.** The cost is that the hot list refreshes hourly rather
than half-hourly during market hours — a convenience surface, not a record. Nothing that writes
an unrebuildable dataset changes cadence.

---

## 3. What I do NOT recommend, and the measurement is why

**`cancel-in-progress: true` on the land gate.** It looked like the obvious win: the workflow
runs on every push to `worktree-*` with `cancel-in-progress: false`, so a lane that pushes three
times in a row runs three full gates. **Measured: only 3 of 120 runs were superseded — 2% of
runs and 22 minutes, 3% of the land total.** It is not worth the risk of cancelling a run that
is mid-land.

**Weakening or splitting the land gate.** The gate is what makes `main` trustworthy and it
caught a real broken suite in this very window. Do not trade it for minutes.

**THE HONEST REMAINING LEVER IS AGENT DISCIPLINE, AND IT IS PARTLY MINE.** 120 land runs over 30
branches is four pushes per landed branch. `worktree-ma5-ma6-inference-bars` alone ran **35
gates for 278 minutes — 14% of the monthly allowance on one lane's branch.** My own
`worktree-hero-shelf` took 4 runs and 35 minutes. Fewer, better-verified pushes per land is a
larger saving than either change above, and it is not a workflow change.

---

## 4. THE STANDING RISK, recorded because it must not be discovered later

**Today this is free.** `valuation-tool` is public, the public-repo discount covers the overage
in full, and $24.31 gross is $0 billable. Budgets are $0 with stop-usage at 100%, which on a
public repo does nothing.

**The day the repository goes private, that discount disappears and every one of those
workflows stops at the budget.** Not degrades — **stops**. That includes `track-row`, which
means **the contract-bound forward track silently stops recording**, and a gap in that record is
the one loss this project cannot repair: it is a statement about what the model said on a day
that has already passed.

**So going private is not only a visibility decision; it is a decision to fund the automations
or lose the record.** At current volume that is ~3,933 minutes against 2,000 included. Getting
under the line before the switch — change 2 above, plus fewer pushes per land — is the cheap
version of this; raising the budget is the other. **Deciding it at the moment of the switch, or
after, is the expensive version.**
