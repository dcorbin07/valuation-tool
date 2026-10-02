# PROPOSAL — the `themes` / `themes-assemble` jobs for `.github/workflows/auto-scan.yml`

**STATUS: CORRECTED AND SAFE TO PASTE (2026-10-02).** Session 70's text is **NOT** safe and has
not been pasted. Two defects were found on review; a third, more serious one falls out of the
second. All three are fixed below and the fixes are measured rather than argued.

**WHY THE TEXT LIVES HERE AND NOT IN `.github/`.** The auto-land policy **REFUSES any branch that
touches `.github/`** (`RUN_RULES`, and `MA11` split the land Action into two jobs for exactly this
reason), so an agent cannot ship a workflow change. Don pastes it. That makes the text a
deliverable like any other, so it is tracked, reviewed and **tested** here —
`tests/test_proposal_auto_scan_themes.py` parses this file and enforces the house rule that every
job names its own schedule.

**TARGET: live before 2026-10-12.**

---

## THE THREE DEFECTS

### 1. `themes-assemble` fired on EVERY scheduled event — 76 times a week instead of once

Session 70's condition:

```yaml
    if: ${{ always() && (github.event_name == 'schedule' || github.event.inputs.kind == 'themes') }}
```

Two independent faults in one line:

* **`always()`** makes the job run even when `themes` is **skipped** or has **failed**, so it runs
  on crons that have nothing to do with it.
* **`github.event_name == 'schedule'`** is true for **every** cron in the file, not just the
  themes one. Counted from the committed `schedule:` block:

  | cron | job | firings/week |
  |---|---|---|
  | `23 22 * * 1-5` | hot (primary) | 5 |
  | `41 23 * * 1-5` | hot (backup) | 5 |
  | `23 13-20 * * 1-5` | intraday | **40** |
  | `47 20 * * 1-5` / `47 21 * * 1-5` | paper (DST pair) | 10 |
  | `58 20 * * 1-4` / `58 21 * * 1-4` | recap daily (DST pair) | 8 |
  | `59 20 * * 5` / `59 21 * * 5` | recap weekly (DST pair) | 2 |
  | `15 13 * * 1-5` | watchdog | 5 |
  | `17 7 * * 0` | **themes (new)** | 1 |
  | | **TOTAL** | **76** |

  So `themes-assemble` would fire **76 times a week**, of which **75 are unwanted** — and on each
  of those it would re-crawl SEC for 1,500 names.

**Every other job in that file already names its own schedule** — `hot`, `intraday`, `watchdog`,
`paper` and `recap`, 5 of 5. The fix is to follow the house rule, which the `themes` job itself
already did.

### 2. The assemble job could not see the shards' work — `restore-keys` returns ONE cache

Each shard saved `live-themes-crawl-<run_id>-<shard>`; the assemble job restored with
`restore-keys: live-themes-crawl-`. **A restore-key prefix returns the single most recent match**,
so the assemble job got **one shard**, not three.

**MEASURED, on session 70's real crawl (1,534 payloads per leg on disk), through the real
`fetch_all` orchestration with the three per-leg fetchers counted and the network never touched:**

| what the assemble step sees | NEW SEC fetches it would make |
|---|---|
| all three shards merged | **39** — `cusip` 0 of 1500, `insider` 0 of 1500, `xbrl` 39 |
| **one shard** (what `restore-keys` gives) | **3,010** — `cusip` 999, `xbrl` 1,011, `insider` 1,000 |

3,010 is exactly the 1,000 names the other two shards hold, times three legs — the
"re-crawls about two-thirds of the universe" this was flagged for. At the rate session 70
actually achieved (4,135 calls in ~111 min ≈ 0.62 calls/s) and ~2.8 HTTP calls per name-leg,
3,010 name-legs is **~3h40m against a 90-minute timeout**, so it does not merely run slowly — it
**times out**. And `actions/cache` does not save on failure, so it would arrive at the same state
the following week, every week.

**THE 39 ARE NOT A RESIDUAL OF THE MECHANISM.** They are 39 names whose cached `xbrl` payload has
`shares_level: None` — `AEG`, `AZN`, `BP`, `ERIC`, `FMX`, `GFL` and so on, foreign private issuers
filing 20-F, which carry no dei cover-page share count. `xbrl_needs_shares` correctly calls an
absent level **incomplete**, so they are re-attempted on every run regardless of how the crawl is
restored. **Session 70's own real assemble run independently confirms the figure**:
`data/live_themes/PROGRESS.txt` ends

```
19:00:04  fetch: DONE 1500 names, calls=39, throttles=0
          cusip 0+1500, xbrl 39+1460, insider 0+1500
```

`calls=39` is the **real** `Guard` counter on a live network run, matching the offline measurement
to the digit. Earlier in the same log, three whole-universe passes over a complete crawl read
`calls=0` outright.

### 3. THE SERIOUS ONE — defect 2 would have **silently zeroed the insider theme for two-thirds of the universe, permanently**

This is not slowness, and it is the reason the merge is a correctness fix rather than an
optimisation.

The Form 4 producer reads the **cached submissions index** to decide which documents to fetch:

```python
sub = M._read_json(M.leg_path(ROOT, "submissions", t)) or {}
forms = sub.get("form") or []
picks = [... for i, f in enumerate(forms) if f == "4" and lo <= dates[i] < hi]
```

`submissions/` is populated **by the cusip leg**, so each shard fills it for its own 500 names. And
`fetch4` writes a payload durably when a name has no picks:

```python
if rec["n_filings"] == 0 or rec["parsed"] > 0:
    M._atomic_write_json(out_p, rec)        # n_filings == 0 is DURABLE
```

...while skipping any name whose payload already exists (`if os.path.exists(out_p): continue`).

**So with one shard restored: 1,499 of 1,500 served names have a submissions index locally, but
only shard 0's 500 would be present. The other 1,000 get `forms = []` → `n_filings: 0` → a durable
payload with `txns: []` → and are never retried.** Measured on the real cache, 1,277 of 1,500 names
genuinely have Form 4 filings (13,308 documents); the defect would report 223 such names as the
whole truth and look exactly like a universe with no insider activity.

**The zero-row refusal would NOT catch it.** That guard fires on an empty cache; this cache would
have its ~1,400 rows with the insider column mostly empty — which session 70 itself describes as
reading "as 'no insider data' rather than 'this producer was never pointed at this universe'". The
same failure shape, one layer along.

Merging all three artifacts fixes it, because `submissions/` for all 1,500 names arrives with them.

---

## ACTIONS MINUTES PER WEEK

**The repo is PUBLIC today, where GitHub bills no minutes for standard runners.** The figures
matter because Don may make it private, where the Free plan includes 2,000 minutes/month and
Linux overage is $0.008/min.

| | job-minutes/week | /month | vs a 2,000-min private allowance |
|---|---|---|---|
| **session 70's text, as written** | **~6,750** (75 timed-out runs x 90 min) | ~29,000 | **14.5x over** — quota gone in ~1.4 days; ~**$216/month** overage |
| **corrected, steady state** | **~52** | ~225 | **11%** |
| corrected, first run / quarterly 13F roll | ~385 that week | — | — |

Steady state is `themes` 3 shards x ~4 min (warm cache, crawl skips everything) = ~12, plus
`themes-assemble` ~40 — dominated by the **13,308 Form 4 documents**, which are paced at
`SEC_MIN_INTERVAL_S` 0.13s on a shared guard, so ~29 min is the floor. The cold figure is the
measured ~111-minute full crawl x 3 shards billed separately, which recurs when the 13F period
rolls (~4x a year) because new names and a new aggregate are needed.

Matrix jobs bill separately, and GitHub rounds each job up to the minute.

---

## THE CORRECTED TEXT — SAFE TO PASTE

### 1. ADD TO THE `schedule:` BLOCK

```yaml
    - cron: "17 7 * * 0"            # theme cache — Sunday 07:17 UTC, ahead of Monday's scan
```

### 2. ADD `themes` TO THE DISPATCH CHOICES

```yaml
        options: [hot, intraday, both, watchdog, paper, recap-daily, recap-weekly, themes]
```

### 3. NEW JOBS — append after the `hot` job

```yaml
  themes:
    # THE FREE ROUTE'S INSTITUTIONAL + INSIDER + CAPITAL-DISCIPLINE INPUTS, from SEC alone:
    # 13F aggregates, XBRL company facts, Form 4. No vendor, no key, no licence.
    #
    # WEEKLY, not daily: the 13F period and the XBRL share counts change quarterly at most, and
    # the crawl is ~1,500 names against SEC's rate ceiling. Measured: ~12,400 calls and about
    # 111 minutes wall across three concurrent shards.
    if: ${{ (github.event_name == 'schedule' && github.event.schedule == '17 7 * * 0') || (github.event_name == 'workflow_dispatch' && github.event.inputs.kind == 'themes') }}
    runs-on: ubuntu-latest
    timeout-minutes: 150
    strategy:
      fail-fast: false
      matrix:
        shard: [0, 1, 2]
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install --require-hashes -r requirements.lock.txt   # MA12
      # WARM START, AND SCOPED TO THIS SHARD. The restore-key prefix carries the shard number,
      # so it returns THIS shard's most recent crawl rather than whichever shard happened to
      # finish last. A prefix without the shard number is defect 2 in the restore direction.
      #
      # The 13F zips are NOT cached: they are 190MB for the pair, and `build_13f` short-circuits
      # on `13f_aggregate.json` (4.6MB) whenever the periods match, so caching the aggregate is
      # the whole benefit at 2.4% of the size. They re-download only when the period rolls.
      - name: Warm start from this shard's last crawl
        uses: actions/cache/restore@v4
        with:
          path: |
            data/live_themes/cusip
            data/live_themes/xbrl
            data/live_themes/insider
            data/live_themes/submissions
            data/live_themes/cik_map.json
            data/live_themes/13f_aggregate.json
          key: live-themes-crawl-${{ matrix.shard }}-${{ github.run_id }}
          restore-keys: live-themes-crawl-${{ matrix.shard }}-
      - name: Crawl shard ${{ matrix.shard }}
        env:
          SEC_USER_AGENT: "Donovan Corbin donniecorbin6@gmail.com"
          # The universe is the broker liquidity ranking, so this needs the market-data token
          # for the same reason the hot job does — and `live` because the sandbox host serves a
          # different universe (config.py:53 defaults to sandbox). Verified: without it the
          # build REFUSES with "the broker universe came back empty" and crawls nothing.
          TRADIER_TOKEN: ${{ secrets.TRADIER_TOKEN }}
          TRADIER_ENV: live
        # A shard crawls and REFUSES to assemble: a cache built from one third of the universe
        # would carry no sign that it covers a third, and a thin cache is indistinguishable from
        # a complete one once written.
        run: python scripts/theme_cache_build.py --universe broker --slice ${{ matrix.shard }}/3
      # SAVED EVEN ON FAILURE, which is the point. `actions/cache` (the combined action) does NOT
      # save when the job fails, so a shard that timed out or hit SEC's ceiling threw away every
      # name it HAD fetched and arrived at the same wall the following week, forever. An explicit
      # `cache/save` with `if: always()` keeps the partial progress, so a bad week costs latency
      # rather than the whole crawl.
      - name: Keep this shard's crawl for next week
        if: always()
        uses: actions/cache/save@v4
        with:
          path: |
            data/live_themes/cusip
            data/live_themes/xbrl
            data/live_themes/insider
            data/live_themes/submissions
            data/live_themes/cik_map.json
            data/live_themes/13f_aggregate.json
          key: live-themes-crawl-${{ matrix.shard }}-${{ github.run_id }}
      # THE HAND-OFF TO THE ASSEMBLE JOB, and it is an ARTIFACT rather than a cache because the
      # assemble job needs ALL THREE shards. `restore-keys` returns the single most recent match,
      # so a cache prefix can only ever deliver one of them — measured, that leaves the assemble
      # step re-crawling 3,010 name-legs instead of 39, AND it silently zeroes the insider theme
      # for the 1,000 names whose `submissions/` index is missing.
      #
      # AN ALLOWLIST, NOT AN EXCLUSION LIST. `form4_live` must NEVER travel: its window is
      # `today - 90d .. today`, it moves every day, and `fetch4` skips any name whose payload
      # already exists — so a carried-over payload freezes the insider window and serves a stale
      # score with nothing looking wrong. The 13F zips are excluded for size. Listing what goes
      # IN cannot accidentally ship either one.
      - name: Hand this shard's crawl to the assemble job
        uses: actions/upload-artifact@v4
        with:
          name: live-themes-crawl-${{ matrix.shard }}
          path: |
            data/live_themes/cusip
            data/live_themes/xbrl
            data/live_themes/insider
            data/live_themes/submissions
            data/live_themes/cik_map.json
            data/live_themes/13f_aggregate.json
          retention-days: 1
          # A SILENTLY EMPTY ARTIFACT IS THE DEFECT THIS WHOLE JOB EXISTS TO AVOID.
          if-no-files-found: error

  themes-assemble:
    needs: themes
    # NAMES ITS OWN SCHEDULE, exactly as `hot`, `intraday`, `watchdog`, `paper` and `recap` do.
    # Session 70's `always() && github.event_name == 'schedule'` fired on all 76 scheduled events
    # in this file — 75 of them unwanted, each re-crawling SEC for 1,500 names and timing out.
    #
    # `always()` is GONE deliberately. With a plain `needs:` this runs only if all three shards
    # SUCCEEDED, which is what we want: a failed shard means an incomplete crawl, the assemble
    # would refuse it anyway, and the `hot` job's restore then misses and the scan runs on the
    # themes it runs on today — a degradation, not a failure.
    if: ${{ (github.event_name == 'schedule' && github.event.schedule == '17 7 * * 0') || (github.event_name == 'workflow_dispatch' && github.event.inputs.kind == 'themes') }}
    runs-on: ubuntu-latest
    timeout-minutes: 90
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install --require-hashes -r requirements.lock.txt   # MA12
      # ALL THREE SHARDS, MERGED INTO ONE TREE. `merge-multiple` is what makes this work: without
      # it each artifact lands in its own subdirectory and the crawl root stays empty. Measured
      # with all three present, the assemble step fetches 39 names (the 20-F filers with no dei
      # share count) instead of 3,010, and `submissions/` covers all 1,500 names so the Form 4
      # leg cannot write 1,000 durable empties.
      - name: Bring in all three shards' crawls
        uses: actions/download-artifact@v4
        with:
          path: data/live_themes
          pattern: live-themes-crawl-*
          merge-multiple: true
      - name: Show what arrived
        # PRINTED, because "the merge worked" and "one shard arrived" look identical in a log that
        # does not count. Expect ~1500 per leg; anything near 500 is the defect returning.
        run: |
          for leg in cusip xbrl insider submissions; do
            printf '%-12s %s\n' "$leg" "$(ls data/live_themes/$leg 2>/dev/null | wc -l)"
          done
      # THE FORM 4 LEG, and it is a SEPARATE producer rather than part of the crawl above.
      # `build_live` reads raw transactions from `form4_live/` and computes the score itself
      # from the constants the FIDELITY-2 control validated; the crawl's own `insider` leg
      # stores a pre-computed score instead and is not what the builder reads. `--snapshot` is
      # not optional: without it `fetch4` reads a PINNED served file and crawls the wrong
      # universe, which is why `form4_live` was empty.
      #
      # The first line writes the served file `--snapshot` names and, with the shards merged,
      # makes 39 SEC calls rather than 3,010. `|| true` is kept: its own failure must not cost
      # the Form 4 crawl, and the assemble step below refuses on a thin crawl anyway.
      - name: Crawl Form 4 for the served universe
        env:
          SEC_USER_AGENT: "Donovan Corbin donniecorbin6@gmail.com"
          TRADIER_TOKEN: ${{ secrets.TRADIER_TOKEN }}
          TRADIER_ENV: live
        run: |
          python scripts/theme_cache_build.py --universe broker --slice 0/1 || true
          python -m scripts.fidelity2_rebuild fetch4 --current \
            --snapshot data/live_cache/served_broker_top_1500.json
      - name: Assemble the theme cache
        env:
          SEC_USER_AGENT: "Donovan Corbin donniecorbin6@gmail.com"
          TRADIER_TOKEN: ${{ secrets.TRADIER_TOKEN }}
          TRADIER_ENV: live
          LIVE_THEMES_CACHE: data/live_cache/theme_columns.json
        # No --slice: this assembles from what the shards fetched. It re-derives nothing already
        # on disk, and it RAISES rather than writing a zero-row cache.
        run: python scripts/theme_cache_build.py --universe broker
      - name: Publish the theme cache for the hot scan
        uses: actions/cache/save@v4
        with:
          path: data/live_cache/theme_columns.json
          key: live-themes-cache-${{ github.run_id }}
```

### 4. TWO ADDITIONS TO THE EXISTING `hot` JOB

Insert immediately after the existing `Restore the scan cache` step:

```yaml
      # THE FREE ROUTE'S THREE MISSING THEMES. Read-only here: `themes-assemble` is the only
      # writer, so a hot scan can never publish a partial cache under this key. If the restore
      # misses, `live_themes` finds no cache and the scan runs on the themes it runs on today —
      # the same behaviour as before this job existed, which is why a miss is a degradation and
      # not a failure.
      - name: Restore the live theme cache
        uses: actions/cache/restore@v4
        with:
          path: data/live_cache/theme_columns.json
          key: live-themes-cache-never-matches-force-restore-keys
          restore-keys: live-themes-cache-
```

---

## WHAT CHANGED FROM SESSION 70'S TEXT

| | session 70 | corrected |
|---|---|---|
| `themes-assemble` `if:` | `always() && (event_name == 'schedule' \|\| inputs.kind == 'themes')` | names `17 7 * * 0` and the `themes` dispatch, no `always()` |
| shard → assemble transfer | `actions/cache` + `restore-keys: live-themes-crawl-` (one shard) | `upload-artifact` per shard + `download-artifact` with `merge-multiple` (all three) |
| shard warm start | prefix without the shard number | `restore-keys: live-themes-crawl-<shard>-` |
| partial progress on failure | lost (`actions/cache` does not save on failure) | `cache/save` with `if: always()` |
| what travels | whole `data/live_themes` | an **allowlist**; `form4_live` and the 190MB zips cannot travel |
| visibility | none | per-leg file counts printed before the crawl |
| empty artifact | silent | `if-no-files-found: error` |

The `themes` job's own `if:` was already correct and is unchanged. Items 1, 2 and 4 are unchanged
from session 70 apart from one comment.

---

## VERIFICATION PERFORMED

* **Every job's `if` names its own schedule or dispatch kind** — enforced by
  `tests/test_proposal_auto_scan_themes.py`, which parses THIS file's YAML and the committed
  `.github/workflows/auto-scan.yml`, and fails on `always()` or on a bare
  `event_name == 'schedule'`. The real file passes it today, 5 jobs of 5.
* **Zero new SEC calls for names the shards already fetched** — measured through the real
  `fetch_all`: merged 39 (all `xbrl`, all 20-F filers with no share count), one-shard 3,010.
  Corroborated by session 70's own live log at `calls=39`, and by three logged whole-universe
  passes at `calls=0`.
* **Run as a fresh runner would, with no `data/`** — `git archive HEAD` into a clean directory
  (`data/` is gitignored, so this is exactly what `actions/checkout` produces). The three modules
  import, `--slice 9/3` and `--slice bogus` are REFUSED before any download, and
  `--universe broker` fails with "the broker universe came back empty" — the missing
  `TRADIER_TOKEN`, which the job supplies. With the token the same command resolves
  **1,500 names from scan `broker_top_1500`**, confirming the `--snapshot` filename the Form 4
  step passes.
* **The period derivation works offline on a bare tree** and currently STEPS BACK one quarter:
  `30-JUN-2026` is not published by SEC yet, so `curr` is `31-MAR-2026`.

**NOT verified: nothing was run under Python 3.11.** Only 3.13 is installed here, and the job pins
3.11. The repo's own `test_the_repo_parses_on_the_ci_python` covers the parse, which is the defect
that cost three land attempts; a 3.11 runtime difference would not be caught locally.

---

## RESIDUALS — reported, not fixed

* **`xbrl_needs_shares` does not refetch a STALE level, only a look-ahead one.** It returns
  `end > asof`, which refetches when the cached level is NEWER than needed and skips when it is
  OLDER — while its own docstring says it exists so "moving to a new 13F period refetches rather
  than silently reusing the prior quarter's level". It does not. Not live today (`curr` is still
  `31-MAR-2026`), and it will bite the first week the period rolls: the anchor would divide by the
  previous quarter's share count. **`live_theme_sources.py` is not this lane's file.**
* **The 39 20-F filers are re-attempted every run**, ~107 HTTP calls a week. Correct behaviour for
  an absent value; cheap; listed so it is not mistaken for the merge failing.
* **`form4_live` is deliberately re-crawled weekly** — 13,308 documents, ~29 min floor. It is the
  bulk of the assemble job's time and it cannot be cached, because the window moves daily and
  `fetch4` skips on file existence alone.
* **The split guard will print `ABSENT` on a runner** (`data/bulk/actions.csv` is licensed and
  untracked), as session 70 documented. Unchanged here.
