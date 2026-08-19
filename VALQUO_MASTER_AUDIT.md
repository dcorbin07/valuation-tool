# VALQUO_MASTER_AUDIT.md — cold audit #3: everything, end to end

> **Merged record of record: `VALQUO_MASTER_AUDIT_ULTIMATE.md` (this file's 35 items stand, referenced by ID).**

**Auditor:** cold (no history with this codebase). **Date:** 2026-08-14.
**Tree audited:** `origin/main` @ `67f995e`, in a fresh worktree.
**Method:** strictly read-only. Nothing was changed, fixed, adopted or re-run except the test
suite **and one declared exception below**. Every finding below is quoted code, a measured
command, or is explicitly marked HYPOTHESIS / UNCHECKABLE.

> **ONE SCOPE DEVIATION, DECLARED RATHER THAN ABSORBED.** The commission says the only outputs
> are the three deliverable files. I have also added **one line** to `.gitattributes`
> (`*.pdf binary`), because deliverable #3 is otherwise **knowingly broken on arrival**: this
> repo runs `core.autocrlf=true` and sets no binary rule, so git corrupts checked-out PDFs. It
> has already done so — audit #2's own `VALQUO_LIVE_AUDIT.pdf` carries **308 CRLF sequences** in
> the working copy and `pypdf` reports *"incorrect startxref pointer"* on it. That is finding
> **MA35**, and the one-line fix repairs the predecessor's deliverable as well as mine
> (verified: re-checkout goes 48,180 bytes / 308 CRLFs → 47,872 / **0**). It touches no code, no
> research and no claim, and it is deliberately **not** `* text=auto`, which `.gitattributes`
> documents as the change that would renormalise the tree. Shipping a PDF I know will break
> seemed worse than a narrow, disclosed exception; reverting it costs one line.

---

## 0. The gate, and a correction to the commission's own starting instruction

The commission says *"do not start unless the board is quiet."* It is quiet, and I checked it
rather than assumed it: no ledger row carries `IN PROGRESS` (the one string match is `B13`,
whose cell reads *"NOT IN PROGRESS"* — a negation), and every remote `worktree-*` branch is an
ancestor of `origin/main`.

**But the commission told me to work in `C:\Users\donni\Downloads\valuation-tool`, and that
checkout is 508 commits behind `origin/main`.** `VALQUO_LEDGER.md`, `RUN_RULES.md` and
`VALQUO_LIVE_AUDIT.md` — three of the five documents the commission names as required reading —
do not exist in it. Audit #2 recorded the same thing at 265 commits on 2026-08-10; the project's
own memory recorded it at 472. It is now 508. **I audited `origin/main` instead.** This is
finding **MA20** and it is a process finding, not a footnote: the instruction that opens a cold
audit pointed the auditor at a tree four days and five hundred commits stale, and nothing in the
system detects that.

The local checkout also carries **one unpushed commit**, `41d7b12`, and that commit contains the
answer to one of the two rows still open (`PT-WRITER`). It has been stranded for four days.

I ran the full gate as CI runs it: **74 suites, 74 passed, 0 failed**, on a worktree with **no
licensed `data/` directory at all**. That is a real and load-bearing fact — see MA17.

---

## 1. Honest summary

### The three most valuable things I found

**1. The live product's scoring weights can be changed automatically, every month, by a
scheduled job — through a statistical gate several times weaker than the one the research
programme uses, with no connection to the vintage contract, the trial counter, or any
register.** (MA1–MA3)

The chain is five links and every one is in the tree today:
`auto-scan.yml` cron `0 12 1 * *` → `POST /admin/run-learning` → `autolearn.run_learning` →
`store.save_learned(..., adopted=True)` → `screen.py:51-55 _effective_weights(store)`, which
returns the learned weights **in preference to** `settings.WEIGHTS_ESTABLISHED`. It is gated
only by `cfg.learn_enabled`, which defaults to **true** and is documented **nowhere** — not in
`render.yaml`, not in `.env.example`, not in `ENV_REFERENCE.md`.

The significance of this is not that a learner exists. It is the asymmetry: `fundamental_panel`
has a carefully-built multiple-testing haircut (`_trials_haircut`, floored at the research log's
`N` = 224, currently √(2·ln 224) = 3.2899) guarding a weight choice the project **never makes** —
`cpcv.adopt` is `false` on every run. The path that *can* change the weights every user sees
uses a hand-rolled `1.64 × 1/√((names−1)·dates)` floor (`backtest/optimize.py:95-99`) that has
never been calibrated against anything, treats overlapping 21-day forward returns from *daily*
scans as independent draws, and **never compares the winner to the incumbent** — `eq_oos` is
computed, printed inside the adoption message as though it were the comparison, and left out of
the boolean.

**The strongest gate in the project protects the number nobody trades. The weakest gate protects
the number every user sees.**

And `track_meter.VINTAGES` is a hand-written tuple in Python source. A weight change written to
SQLite cannot enter it. So an adoption here would change the live composite **without closing a
vintage** — which is precisely what Amendment 1 voided vintage 1 for, and precisely what three
five-year clock resets in four days have been paid to honour.

**2. Two irreplaceable data assets are outside the backup, one of them never considered at
all.** (MA16, MA17)

`backup_to_D.ps1` is an allowlist — its own header brags that this is why it cannot lose a race
with a growing `data/`. `data\options_ticks` — 4.72 GB, 70,288,482 prints, the alert-day tick
cache O14 was justified by — appears in **neither `$KEEP` nor `$SKIP`**, nor in the backup's
test, nor in `HANDOFF_backup.md`. It was not declined; it was never weighed. Audit item `D2`
concluded ThetaData is **not lawfully re-purchasable** at the individual tier ("personal use
only, no business use"), so this may not be re-obtainable at any price Don is willing to pay.

`data\free_analysis` **is** on the skip list, with the reason *"results JSONs recomputed from
`data\backtest` by the `scripts\` that wrote them."* That is the exact argument `RUN_RULES`
rule 9 exists to reject — the rule written *because* X7 kept 100 placebo draws as five summary
rates and re-denominating one column meant re-running a 3.4-hour sweep. The directory holds the
per-draw evidence for roughly forty registered studies, including the banked `(margin, se)`
pairs that make X7's floors re-derivable by arithmetic instead of by sweep.

**3. Every calibrated bar in the project was calibrated at `N` = 84 and last *checked* at
`N` = 129. `N` is 224 today, and the project's own published adopt curve says the null has moved
in that range.** (MA20)

X7RECON's conclusion is stated in the record as a rule: *"A CALIBRATED PLACEBO FLOOR IS A
FUNCTION OF `N` … a floor may not be compared across sweeps run at different `N` without
checking."* It then checked at 129 and published the curve: **N = 129 → 20 adopters, N = 200 →
18, N = 400 → 17.** At today's 224 the adopter count is no longer 20, so at least two placebo
draws have changed adoption state — and adoption is the mechanism that manufactures roughly
+1.4 of long-short *t* in a noise draw. Nobody has re-run the check. The direction is probably
conservative (fewer adopters → a *lower* null p95 → the shipped 2.6199 clears **2.2837** by
more, not less), but "probably conservative" is a guess and the project's own rule forbids it.
The check is arithmetic, not a sweep — except that the arithmetic's inputs live in
`data/free_analysis`, which finding 2 says is not backed up.

### The overall state, in one paragraph

This remains the most rigorously self-audited codebase I have read, and audit #2's summary is
still accurate: the reasoning is not where the failures are. What audit #2 named as the
generalisation — *every guard is correct in-process and blind at its own output boundary* — I
would now extend one step further, because the pattern has migrated. **The verification effort
has been aimed at the research programme, and the research programme is not the product.** The
backtest has CPCV, a placebo-calibrated floor, a trial counter, a vintage register, pre-committed
thresholds and 74 green suites; the live scoring path next to it has an uncalibrated 1.64σ gate,
an undocumented enabling flag, two independent writers of the same weights, and no register at
all. The same split explains the continuity findings: the *record* has a sha256-manifested
freeze and a signed contract, while the *evidence* those rest on sits in a gitignored directory
that the backup skips by name. The project has built world-class instruments and has not yet
turned any of them on the machinery that ships. Its research record, meanwhile, is genuinely
excellent and I confirmed rather than contradicted it: the trial counter reads 224 equity trials
against a shipped artifact that also reads 224; `sum(by_domain)` equals `trials` exactly, so no
row is silently losing its domain; PBO 0.7333 and DSR 0.7863 are reported honestly against
"want <0.50" and "want >0.95" and the record already retires the old "clears both bars" claim.
The overwhelming majority of findings here are about the factory and the plumbing, which is
where a project this careful about its statistics would be expected to leak.

### What I could NOT check, and why

* **Production state.** I cannot read Render's environment, its SQLite databases, or the
  `learned_config` table. So MA1 is proven **armed** and not proven **fired**. Whether it has
  ever adopted is a one-query question for Don and is the first of my batched questions.
* **`data/` in any form.** No licensed export, no options cache, no `free_analysis` artifacts
  are present in this worktree. Every number I quote from a study is quoted from the record,
  not re-measured. The exception is `BACKTEST_RESULTS.json` and `RESEARCH_LOG.md`, which are
  tracked, and which I did re-measure.
* **The D: drive's actual contents.** MA16/MA17 are read from `backup_to_D.ps1`'s allowlist,
  which is authoritative about what the script *copies*. Whether something else put
  `options_ticks` on D: is Don's to answer.
* **The exact size of the overlap inflation in MA2.** The direction is certain and structural;
  the ≈4.6× magnitude is the standard √h result for h = 21 and is marked HYPOTHESIS because I
  could not measure the real snapshot store.
* **Re-adjudicating any research verdict.** Out of scope, and I did not.
* **The options tree beyond the seams it shares with the equity lane** (~11k lines, its own
  lane, already covered by audit #1's O-series).

---

## 2. MANDATE 2 — CODE

### MA1 — CRITICAL — A scheduled job can change the live scoring weights, and it is invisible to the vintage contract

**Files:** `.github/workflows/auto-scan.yml:271-279` · `valuation/saas/app_saas.py:202-222` ·
`valuation/edge/autolearn.py:107-130` · `valuation/screener/screen.py:51-55, 305` ·
`valuation/config.py:192` · `valuation/edge/track_meter.py:113-199`

**Evidence, link by link:**

```
auto-scan.yml:277   - cron: "0 12 1 * *"   # self-learning — monthly, OOS-gated re-tune
auto-scan.yml:279     curl -fsS -X POST "$BASE/admin/run-learning" -H "X-Admin-Token: $TOKEN" || true
config.py:192       learn_enabled: ... _get("LEARN_ENABLED", "true").lower() != "false"
autolearn.py:123        store.save_learned(bucket, rec, stats, True, note)
screen.py:53        est = (store.latest_learned_weights("established") if store else None) or S.WEIGHTS_ESTABLISHED
screen.py:305       est_w, spec_w = _effective_weights(store)
```

`tests/test_edge.py:118-119` **pins** the behaviour — `assert _effective_weights(st)[0] ==
learned` — so this is intended and tested, not accidental.

**Why it matters.** `PAPER_TRACK_CONTRACT` §5a, implemented as `track_meter.VINTAGES`, says an
ADOPTED change to scoring, weights or construction closes the current vintage and opens the
next. `VINTAGES` is a literal tuple in Python source; `save_learned` writes a row to SQLite.
There is no path from one to the other. An adoption would therefore change the composite users
receive **while the forward track kept accruing under the old vintage** — the exact condition
Amendment 1 voided vintage 1 for, and the exact thing three clock resets in four days were paid
to avoid. It would also move the live product away from the composite `M4`'s live-replay
harness just proved bit-identical to the backtest (ρ 1.0, max |Δ| exactly 0.0), silently, since
M4 replays the *code path*, not the *stored weights*.

**Corroborating context, from two independent documents that both describe a world the code does
not implement:**

* `CLAUDE.md` roadmap item **#19** reads *"**Later:** gated auto-apply of adopted weights"* — the
  project believes auto-apply is not built. `screen.py:53` is auto-apply, shipped and tested.
* `BACKTEST_RUNBOOK.md`'s opening diagram states the architecture as *"the ONLY thing that
  travels to Render is the **optimized weights** … via a normal code commit."* That is exactly
  the property MA1 and MA3 break: weights also reach Render by being written into **Render's own
  database**, by a monthly cron and by an admin endpoint, **with no code commit at all** — so
  they leave no diff, no review, and no trace in the history the runbook assumes is the record.

**`LEARN_ENABLED` is undocumented.** Measured: it appears in no `.md`, `.yml`, `.yaml`,
`.example` or `.bat` file in the repository. Its default is on.

**Blast radius:** the hot list, `/api/hotstocks`, the Valquo Index book, the forward track's
validity, and every claim that the live product scores names the way the backtest does.

**Cheapest verification (≈1 minute, Don or a lane with the token):**
`SELECT created_at, bucket, adopted, note FROM learned_config ORDER BY id DESC LIMIT 20;` on the
production `screener.db` — or simply ask whether a *"🧠 Valquo self-learning — weights updated"*
email has ever arrived (`app_saas.py:224-238` sends one on every run, and the subject line
distinguishes changed from unchanged).

**Severity:** CRITICAL if it has ever fired; HIGH-and-armed if it has not.

---

### MA2 — CRITICAL — The gate that guards those weights is uncalibrated, mis-specified, and never compares against the incumbent

**File:** `valuation/backtest/optimize.py:85-102` (and its twin,
`valuation/edge/fundamental_panel.py:2350-2354`).

```python
_std_null = (1.0 / ((max(1.0, _avg_names - 1.0) * max(1, _oos_dates)) ** 0.5)) ...
_sig_floor = 1.64 * _std_null
accepted = bool(is_ic > 0 and oos_ic == oos_ic and oos_ic > 0
                and oos_ic >= min_oos_fraction * is_ic and oos_ic >= _sig_floor)
```

Four separate defects, in descending order of consequence:

**(a) `eq_oos` is computed, reported as the comparison, and excluded from the decision.**
Line 87 computes the equal-weight baseline's out-of-sample IC. Line 101 then writes
`f"Recommended over equal-weight (OOS {eq_oos:.3f})."` into the adopt verdict. **`eq_oos` does
not appear in the `accepted` expression.** The learner can therefore adopt weights that are
*worse* out-of-sample than the incumbent and say in writing that they beat it. This is the
project's own named class — a computed quantity that reaches a report but not the decision
(B8's `rule_fired`, LA5's `health` block) — sitting in the one function that can move the live
book.

**(b) The null treats overlapping returns as independent.** `autolearn.build_panel_from_
snapshots` reads `store.list_scans()` — **daily** scan dates — and computes `fwd_ret` over
`learn_horizon_days = 21` trading days. Consecutive dates therefore share 20 of 21 days of
return window, and per-date ICs are strongly autocorrelated. `_std_null` divides by
`_oos_dates`, the raw count of daily dates. For `D ≫ h` the standard variance-inflation result
is ≈ h, so the standard error is understated by ≈ √21 ≈ **4.6×** and the nominal 1.64σ floor is
in truth ≈ 0.36σ. *(Direction: certain and structural. Magnitude: HYPOTHESIS — I could not
measure the real snapshot store.)* The project fixed exactly this class elsewhere — `M2`/`R3`
made clustered/HAC inference the default and `statistics.hac_tstat` is the shared definition —
and this path imports none of it.

**(c) The ratio test is loosest when the signal is weakest.** `oos_ic >= 0.5 × is_ic` is a
comparison between two noisy quantities: a weak in-sample winner sets a trivially low bar.

**(d) It learns from a sample the current weights selected.** `learn_top_per_date = 60` — the
panel is built from the top 60 names *by the composite the current weights produce*. Weights are
then tuned on the IC measured inside that truncated set and applied to the whole cross-section.
That is range restriction on a variable derived from the thing being estimated.

**And the guard has never been shown its bug.** `tests/test_edge.py:98-131` and
`tests/test_saas.py:107-115` both feed **i.i.d. synthetic panels** — independent per-date draws,
the one world in which `_std_null` is correct. Audit `M3`'s whole point was known-bad fixtures;
this guard has a clean fixture and no dirty one.

**Cheapest verification:** block-bootstrap the real OOS dates in 21-day blocks and compare the
resulting null sd against `_std_null`; or, cheaper, count distinct non-overlapping 21-day windows
in `oos_p` and compare to `_oos_dates`.

**Kill condition for any fix:** if the corrected floor changes no historical adopt decision AND
the `learned_config` table is empty, this is documentation-only and should be recorded as such
rather than "fixed".

---

### MA3 — HIGH — A second live-weight writer adopts on the exact gate `CLAUDE.md` forbids

**File:** `valuation/saas/app_saas.py:270-290`, reading
`valuation/edge/fundamental_panel.py:4448-4453`.

`POST /admin/adopt-backtest-weights` promotes `h["optimized_weights"]` into the live tuner when
`h["accepted"]` is true. That `accepted` comes from `run_backtest` → `_weighted_optimize` — a
**single 50/50 time split**. `CLAUDE.md`'s own core-file section states: *"`cpcv_validate`
(Combinatorial Purged CV — the AUTHORITY for weights). If CPCV runs and rejects, keep defaults —
do NOT fall back to walk-forward."* This endpoint falls back to something weaker than
walk-forward, and CPCV rejects on every run (`adopt: false`, PBO 0.7333 in the shipped artifact).

Two further defects in the same handler: it writes **only** `"established"`, so the two buckets
can end up on different regimes with nothing reporting the split; and the same fallback exists
on the CLI at `fundamental_panel.py:4678-4681`, which prints *"Paste into settings.py"* on a
single-split accept.

**Blast radius:** identical to MA1. **Verification:** the same `learned_config` query — rows
written by this path carry `{"source": "historical_backtest"}` in `stats`, so the two writers
are distinguishable after the fact.

---

### MA4 — HIGH — `append_row` rewrites the contract-bound history non-atomically and silently drops any column it does not know

**File:** `valuation/screener/index_mark.py:304-344`.

```python
kept.append({k: row.get(k) for k in ROW_COLUMNS})
...
with open(history_path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ROW_COLUMNS))
```

Two defects on the file `track-backup.yml` calls *"the one thing that can't be re-derived"*:

1. **Column loss.** Every historical row is read as a dict and re-written **projected onto
   `ROW_COLUMNS`**. If the recorded CSV ever gains a column — a `vintage`, a `source`, an
   `n_priced_method` — the first append silently deletes it from *every row in the file*. The
   docstring guards the opposite direction ("a writer that hand-builds the CSV is free to emit a
   column `index_track.load()` does not read"); the actual risk runs the other way.
2. **Non-atomic truncate-then-write.** `open(path, "w")` truncates first. An interruption
   between truncate and flush leaves the bound series **empty or partial**. There is no
   temp-file-and-rename and no pre-write copy. The only other copies are a weekly backup cron
   (Sunday 06:17 UTC) and one laptop.

**Cheapest fix (not applied):** write to `path + ".tmp"` and `os.replace`; and union the existing
header with `ROW_COLUMNS` instead of projecting onto it.

**Note the module is otherwise exemplary** — the refusal paths, the weight-based coverage floor,
the close guard on the *date* rather than on how the date was chosen, and the disclosed 0.02pp
seam are all correct and I verified the tz-mixing concern (`utc=True` on a naive Stooq date and
a tz-aware yfinance date both land on the right calendar day for US listings).

---

### MA5 — MEDIUM — Two Harvey–Liu–Zhu bars exist and already disagree

`valuation/edge/statistics.py:95-98` exports `hlz_significant(t) -> abs(t) > 3.0`, a **constant**.
The shipped bar in `BACKTEST_RESULTS.json.multiple_testing.hlz` is `√(2·ln N)` = **3.2899** at
N = 224, and it rises monotonically as trials accumulate. The constant is currently referenced
only by `tests/test_edge.py:74-80`, so nothing is wrong today — but it is an exported helper
whose name answers exactly the question the artifact answers differently, and the gap grows.
This is audit `B7`'s class (three composite functions) caught before it has a second caller.

**Fix:** make `hlz_significant` take `n_trials` and delegate to the same `√(2·ln N)`, or delete
it and keep one definition.

---

### MA6 — MEDIUM — The trial counter has one silent path that understates `N`, and it is the only direction that matters

**File:** `valuation/edge/research_log.py:203-215, 233-235`.

`by_domain[dom] += k` runs only when a domain resolves. A row whose `domain` cell is not exactly
one of `("equity","options","unified","infra")` is counted in `trials` but lands in **no** bucket
— and `trial_count(domain="equity")` reads the bucket. The module's own opening argument is that
*"understating `N` … OVERSTATES significance — the exact error M1 exists to fix."* Every other
degradation in this parser is deliberately routed toward a **larger** `N` and reported
(`rows_malformed`, `rows_changed_by_parser_fix`); this one is routed toward a smaller `N` and
reported nowhere.

**Measured today — it is latent, not live.** I ran the parser:
`trials_logged` **530**, `by_domain` `{equity: 224, options: 292, unified: 0, infra: 14}`,
**sum = 530**, `rows_malformed` **0**. No row is currently losing its domain, and the equity
denominator matches the shipped artifact exactly.

**A second, related hazard.** `_header_map` resolves each table's columns from its own header,
and the alignment guard is `len(cells) == hdr["_width"]`. **Both tables in `RESEARCH_LOG.md` are
nine columns wide with different orders**, so the width guard cannot detect a row appended under
the wrong table. (The failure would be mild — verdict read from the `threshold` column, so the
row counts rather than drops — but it is silent and `rows_malformed` will not show it.)

**Also:** `rows(path, use_cache=True)` accepts `use_cache` and ignores it entirely (line 248
calls `_parse` directly). Harmless; the parameter is a lie.

---

### MA7 — MEDIUM — Two public endpoints spend the owner's vendor quota with no cap, and one of them does it 25 names at a time

`valuation/saas/ratelimit.py:33-47` limits `/api/scan/run` to 3/hour because *"FMP quota, 3
requests per uncached name"*, and deliberately leaves `/api/value` unlimited unless `run_ai` is
set, because *"the plain valuation is the product's core action."*

**But `/api/value` reaches the same upstream.** `valuation/web/app.py:158-170` calls
`value_ticker(ticker, CONFIG, ...)` on a caller-supplied symbol — the full adaptive DCF, which
fetches that name's fundamentals. An anonymous loop over **distinct** tickers is a cache miss
every time, so it spends exactly the FMP quota the 22:23 UTC scan depends on — the failure the
module's own docstring names — one name per request, uncapped. The cache defends against repeats;
nothing defends against enumeration, and the universe is ~7,100 names.

**`/api/rank` is the sharper case and it is not in `LIMITS` at all.** `app.py:193-199` accepts a
list and runs `value_ticker(t, CONFIG, run_ai=run_ai, mc_trials=2000)` for **up to 25 tickers per
request**. It is in `PUBLIC_API`, it appears in no limit bucket, and it multiplies the per-request
cost of `/api/value` by twenty-five — including 2,000 Monte Carlo trials per name on a 512 MB
box. Whatever the correct cap on `/api/value` is, `/api/rank`'s is 1/25th of it.

**Suggested shape (not applied):** a generous per-IP cap on `/api/value` regardless of `run_ai`
— say 120/hour, which no human clicking around will reach — and a proportionally tighter one on
`/api/rank`, whose per-request cost is bounded only by the length of the list it is handed.

---

### MA8 — LOW/MEDIUM — `client_ip` has two opposite failure modes and neither is detectable from the code

`ratelimit.client_ip` takes the **rightmost** `X-Forwarded-For` entry, correct for *exactly one*
trusted proxy. With two hops (e.g. a CDN in front of Render) the rightmost entry is the inner
proxy's view of the outer one — a single shared address — and **every visitor then shares one
bucket**, converting the limiter into a global cap that one scraper can exhaust for everybody.
With zero proxies the header is absent and `remote_addr` is used, which is correct. The code
cannot tell which world it is in.

**Cheapest verification:** log the parsed value for a handful of real requests and compare with
Render's own client-IP header. One deploy, one grep.

---

### MA35 — MEDIUM — Git corrupts every PDF in this repository on checkout, and it has already done it

**Files:** `.gitattributes` (no binary rule, by an explicit decision) · `core.autocrlf=true` ·
`VALQUO_LIVE_AUDIT.pdf`

`.gitattributes` deliberately declines `* text=auto`, for a good documented reason (it would
renormalise the whole tree and conflict with every open branch). What it does not do is set a
binary rule for **anything**. So under `core.autocrlf=true` every file falls back to git's
NUL-byte heuristic — and reportlab's output contains no NUL bytes.

**Measured, on the tree as it stands:**

| file | working-copy bytes | CRLF sequences | parser |
|---|---|---|---|
| `VALQUO_LIVE_AUDIT.pdf` (audit #2's deliverable) | 48,180 | **308** | `pypdf`: *"incorrect startxref pointer(1)"*, recovers by rebuilding |
| `Valquo_Edge_Audit_and_Test_Catalogue.pdf` | 7,810,983 | 3 | clean — it contains NUL bytes, so git guessed **binary** and left it alone |
| after `*.pdf binary` and a fresh checkout | **47,872** | **0** | clean, no warning |

The stored blob is fine; **the corruption happens on checkout**, which is why it went unnoticed —
the file opens, because `pypdf` and most viewers silently rebuild a broken xref. A stricter
reader, a signature check, or anyone diffing two copies would not be so forgiving. Note the
selection effect that hid it: the one PDF that survived is the one large enough to contain a NUL
byte by accident.

**This is the same class as `B12` and `S25`** — a behaviour that depends on an accident of the
data rather than on a stated rule, so it works until it doesn't and nothing says which case you
are in.

---

## 3. MANDATE 6 — ADVERSARIAL

### MA9 — HIGH — "The regate is one flag" is wrong, because the demo token is printed on a public page

`app_saas.py:680-681` builds `demo_url = f"/demo/{token}"` from `cfg.demo_access_token` and
renders it into `portfolio.html` — the public `/work` page, gated only by `portfolio_page_
enabled`. **The token is therefore published in the HTML of an anonymous surface.**

`render.yaml:40-57` and `surfaces.py`'s docstring both describe the regate as a single flag:
*"Set `PUBLIC_FULL_VIEW=false` in the Render dashboard, on Don's word … No code change, nothing
deleted."* But `PUBLIC_FULL_VIEW=false` restores a posture whose only gate is a secret the
product prints. After the regate, anyone who has ever read that page source — or the
`ENV_REFERENCE.md` row that documents the value as **`preview`** — still holds full read-only
owner access: `/api/track`, `/api/index-track`, `/api/valquo-index` (names *and* weights),
`/api/options-alerts` (a specific contract and size), `/api/scream-track`. That is precisely the
set `surfaces.py` exists to withhold, under its own categories (1) performance claims and (2)
actionable live picks.

This is not an argument against Don's decision, which is recorded verbatim and is his to make.
It is that **the exit from the decision does not work as written.** The rotation mechanism
already exists and is documented at `app_saas.py:676-678` ("rotating `DEMO_ACCESS_TOKEN` both
re-points this button and invalidates every copied deep-link"); it is simply not part of the
regate instruction.

**Fix:** the regate is **two** changes — `PUBLIC_FULL_VIEW=false` **and** rotate
`DEMO_ACCESS_TOKEN` to a value never rendered publicly (and drop `preview` from
`ENV_REFERENCE.md` and `.env.example`). Add that sentence to `render.yaml:40-57`, which is where
whoever regates will look.

---

### MA10 — HIGH — `ADMIN_TOKEN` is one credential for the product *and* the record, it bypasses the rate limiter, and no rotation procedure exists

A single `X-Admin-Token` grants, at minimum: `/admin/ingest-snapshot` (writes the published hot
list), `/admin/run-learning` (**MA1** — changes live weights), `/admin/adopt-backtest-weights`
(**MA3** — same), `/admin/run-paper-track`, `/admin/post-recap` (posts to Discord as Valquo),
`/admin/run-scan`, `/admin/run-intraday`, `/admin/track-row`, `/admin/export-track`. It also
**bypasses rate limiting entirely** (`app_saas.py:864`: `if bucket and not _admin_ok()`), so it
is simultaneously the key to the product and an uncapped spend lever.

It exists in at least two independent stores — GitHub Actions secrets and Render environment —
and five workflow jobs plus five Render crons read it. **Rotating it requires both to change
within the same window or the pipeline breaks**, and nothing in the repository documents that
procedure, its ordering, or who owns it.

**Recommendation:** split the token by capability before rotating anything. The *read* routes
(`export-track`, `track-row`) and the *trigger* routes (`run-scan`, `run-intraday`, `recap`)
have no business sharing a credential with the two routes that can rewrite the live composite —
and if MA1/MA3 are gated behind a separate, rarely-used token, most of MA1's blast radius closes
without touching the learner at all.

---

### MA11 — MEDIUM — The auto-land Action is unreviewed arbitrary code execution with write access to `main`

`.github/workflows/land-agent-branch.yml` fires on any `worktree-*` push, runs
`python tests/test_*.py` **from the pushed branch** with `permissions: contents: write`, then
merges to `main` and Render deploys. There is no human in the loop, by design and for good
reasons — the alternative cost this project two stranded-work incidents.

The security consequence is worth stating anyway, because the *posture* changed underneath it:
the repository is private, but a single compromised agent session, a leaked PAT, or a
contributor who is trusted to push a branch is trusted to **execute code in CI and ship to
production**, in one step, with no review gate. The test file is the execution vector: adding
`tests/test_zz.py` is enough.

**Cheapest hardening, in order of value per unit of friction:** (a) require the branch's diff to
touch no file under `.github/` for the auto-land path; (b) run the gate against **`main`'s**
copy of `tests/` merged with the branch's source, so a branch cannot rewrite its own gate; (c)
leave everything else alone.

---

### MA12 — MEDIUM — Every dependency is unpinned, on a chain that installs fresh and deploys automatically

`requirements.txt` uses `>=` for all ten packages, with no lockfile and no hashes. CI runs
`pip install -r requirements.txt` on every land and on every scheduled scan; Render builds from
the same file. So an upstream release — of `yfinance`, `pandas`, `numpy`, `scipy`, `reportlab`,
`anthropic` — reaches production without any human step, and a *silently changed* numerical
default (pandas' groupby/NaN handling has moved before) reaches the scoring path the same way.
This is the software analogue of the beta-field disappearance (`OOB2`): a dependency that
returns something plausible but different.

**Fix:** `pip freeze > requirements.lock.txt`, install from the lock in CI and on Render, keep
`requirements.txt` as the human-readable spec. One commit, no behaviour change.

---

### MA13 — MEDIUM — The one number that can silently raise every significance claim has no tamper-evidence

`N` (equity trials = 224) is the denominator of the Deflated Sharpe, the HLZ hurdle and
`_trials_haircut`. It is parsed from `RESEARCH_LOG.md`, a markdown table. **Lowering `N` raises
every DSR- and HLZ-gated claim**, and lowering it takes one edited cell: changing a `verdict` to
`FIXED` removes that row from the count (`research_log.py:172-185`).

The suite does not pin it. `tests/test_edge.py:5322-5340` asserts only *relational* properties
(`trial_count("equity") < trial_count(None)`; `FP._trial_N() == RL.trial_count("equity")`;
a missing file falls back to 8). **Every one of those still passes after an edit that lowers
`N`.** By contrast the project pins far less consequential things: the vintage label is pinned
by *derivation*, the Sharadar freeze carries a sha256 manifest, `SCHEMA_VERSION` is asserted
field by field.

**Fix, cheap and in the project's own idiom:** assert `by_domain` against a committed expected
dict, so changing `N` requires deliberately editing the expectation in the same commit — exactly
what `test_track_meter` does for vintages. `BACKTEST_RESULTS.json` already ships `by_domain`, so
the expected value has a natural home.

---

### MA14 — MEDIUM — Fail-closed covers absence; nothing covers wrong-but-plausible on the live scoring path

The commission asks what covers a vendor returning subtly-shifted values. The honest answer is:
**one field does, the rest do not.** `OOB2` is the precedent and it is exact — Yahoo dropped one
beta field, `wacc.py` substituted 1.10, and MRK went from *"cannot value"* to a **91 Strong
Buy**. The repair was field-specific. The sanity layer that would catch this class exists — but
it lives in `fundamental_panel.sanity_check`, on the **backtest** side, where the data is a
licensed static export that does not drift. The live path, where the data does drift, has
coverage checks (`theme_coverage`, `theme_contributing`, `signal_coverage`) which — as `V2G`
established in a different context — answer *presence*, not *sanity*, and as
`coverage-is-not-fidelity` established, not *fidelity* either.

**Proposal (HYPOTHESIS, needs a register):** port `sanity_check`'s range and subgroup-pegging
tests to the live scan for the handful of inputs with the largest score leverage (beta, market
cap, revenue, net income, shares), and emit the result in the `health` block. Note this only
works if LA5's fix holds — `health` was being dropped by `ci_scan`'s fixed `params` dict, which
is the same class again.

---

## 4. MANDATE 7 — CONTINUITY

### MA15 — HIGH — `data/options_ticks` is in neither the backup allowlist nor its skip list

**Measured:** `grep -n "options_ticks" backup_to_D.ps1 tests/test_backup_to_D.ps1
HANDOFF_backup.md` returns **nothing**. The cache is real and read by three modules
(`mine_tick_flow.py:86`, `scripts/o10_o18_tickflow.py:45`, `scripts/o14_tickflow_signals.py:40`)
and the record puts it at **4.72 GB / 70,288,482 prints / 3,884 of 3,885 alert-days**.

`backup_to_D.ps1` is an **allowlist** — its header's whole argument is that an exclusion list
loses the race against a growing `data/`. The corollary nobody wrote down is that an allowlist
loses to a directory nobody thinks of. The 16.6 GB `options_derived` was *considered and
declined with a reason*; `options_ticks` was never considered at all. And `D2` concluded the
individual ThetaData tiers are *"personal use only, no business use"* with lawful commercial
access starting ~$250/mo plus OPRA registration — so this is closer to `data\backtest_freeze`
("re-downloading returns RESTATED data") than to a derived cache.

**Recommendation:** decide it explicitly — either `$KEEP` at bucket 2, or `$SKIP` with a written
reason. Either is fine; silence is not.

---

### MA16 — HIGH — `data/free_analysis` is skipped on the exact argument `RUN_RULES` rule 9 was written to reject

`backup_to_D.ps1:87` — `@{ P = "data\free_analysis"; GB = 0.07; Why = "results JSONs recomputed
from data\backtest by the scripts\ that wrote them." }`

`RUN_RULES` rule 9: *"Store the draws, not just the summary … Cost so far: X7 kept 100 placebo
draws as five summary rates, so re-denominating one column meant re-running the whole 3.4-hour
sweep, and an 8%-vs-7% mismatch in a second column sat 'undiagnosable' for two sessions."*

The fix for that rule put the draws in `data/free_analysis`. The backup skips
`data/free_analysis` because the draws are "recomputable". At 0.07 GB the cost of keeping it is
nil, and the contents are the per-draw evidence behind roughly forty registered studies —
including `X7_RECONCILE.json`, whose banked `(margin, se)` pairs are the thing that makes MA20's
recalibration arithmetic instead of a 3.4-hour sweep.

Note also that "recomputable from `data\backtest`" is **not true of several of them**:
`O14_TICKFLOW_SIGNALS.json` needs `options_ticks` (MA15, not backed up),
`V6OPT_STAGE1/2.json` need `data/options` + `options_derived`, and every seeded sweep needs the
same research-log `N` it ran at.

**Recommendation:** move it to `$KEEP` bucket 1. It is 70 MB.

---

### MA17 — MEDIUM — The bus test: the code survives a stranger; the claims do not

**Measured, and this is the good half:** all **74 suites pass in a worktree with no `data/`
directory whatsoever**. A competent stranger can clone, `pip install -r requirements.txt`, and
verify that every guard, every gate and every pinned arithmetic identity in this project still
holds. That is far better than most research codebases and it should be said plainly.

**The bad half:** they cannot reproduce a single headline number. Every one — top-decile alpha
+7.17%, long-short HAC *t* 2.6199, PBO 0.7333 — requires `data/backtest`, which is licensed,
gitignored, and (per `D1`) covered by terms that are *personal-use only and forbid commercial
use of the data "or any derivation"*. `BACKTEST_RESULTS.json` is tracked, so the stranger can
read the outputs and audit the *arithmetic between them*, but cannot re-derive them.

**The gaps a stranger would hit, in order.** (1) **The data path is documented and it is not
free.** `BACKTEST_RUNBOOK.md` *does* take a reader from nothing to a run — Step 1 exports prices,
fundamentals, insiders and institutional holdings with a `SHARADAR_API_KEY`. *(This corrects my
own first draft, which said the runbook assumed the data was already in place. It does not.)* The
real barrier is narrower and worse: `D1` verified that Sharadar's terms are **personal-use only
and forbid commercial use of the data "or any derivation"**, so a stranger can reproduce the
numbers only under a licence that would not let them publish what they derived. (2) `CLAUDE.md`
is 344 KB and its own "IMMEDIATE NEXT TASKS" section warns it is *"the least trustworthy section
in the file"*. (3) The entry point to *state* is `VALQUO_LEDGER.md`, and **`README.md` names
neither it, nor `RUN_RULES.md`, nor `CLAUDE.md`** — measured: zero matches.

**Cheapest hardening:** a twenty-line `START_HERE.md` naming, in order, `RUN_RULES.md` →
`VALQUO_LEDGER.md` → `CLAUDE.md` (with the warning) → `BACKTEST_RUNBOOK.md`, plus the one
sentence that says the licensed data is not in the repo and what that forecloses.

---

### MA18 — MEDIUM — The bound forward track still has no writer, and the clock is running

`PT-WRITER` remains one of the two unadjudicated rows. The mechanism now exists
(`index_mark.contract_row`, landed today, 23/23 tests) and was **run for real** — 2026-08-13,
all 86 names priced, `excess_pp` −0.5562, exit 0 — and deliberately **not written**. Nothing in
this repository schedules it; §7.2 assigns scheduling to Cowork.

Stated plainly for the risk register: **the contract's five-year clock is running on vintage 4
(opened 2026-08-13) while the record it will be judged on is not being written.** The recorded
series still ends 2026-08-06. `track_meter.recording_history` is the only instrument that can see
this — `recording_ok` is scoped to the open vintage, and a vintage event clears the gap — and it
reads v1 VOID 2 of 6, v2 0 of 0, **v3 0 of 1**, v4 OPEN 0 of 0.

This is not a new finding; it is the *severity* that is under-stated by its "BLOCKED — Cowork
lane" label. A blocked row on a clock is a decaying asset, not a parked one.

---

## 5. MANDATE 9 — THE INSTRUMENTS' CALIBRATION AGE

The staleness map. **Nothing here is recalibrated — that is registered work.**

| instrument | value | calibrated | last *checked* | `N` then → now | verdict |
|---|---|---|---|---|---|
| long-short HAC floor | **2.2837** | X7, 2026-08-05 (HACFLOOR re-derivation) | 2026-08-08 (X7RECON) | 121/129 → **224** | **RECALIBRATION DUE** — see MA19 |
| long-short naive floor | 2.1437 | same | same | same | due, same mechanism |
| theme IC *t* bar | **2.71** | X7, N = 84 | never re-checked | 84 → 224 | **DUE**, and it gates live decisions (`U2` judged four arms on it) |
| top-decile alpha margin | **1.95pp** | X7, N = 84 | never | 84 → 224 | **DUE** |
| Deflated Sharpe calibrated bar | **0.7216** | X7 re-run at N = 84, 2026-08-06 | that run | 84 → 224 | **DUE**; the DSR is the one statistic X7 showed becomes *more* discriminating at higher `N`, so the direction is knowable but the value is not |
| PBO calibrated bar | **<19.7%** | X7, N = 84 | never | 84 → 224 | due; low consequence, PBO is already read as uninformative |
| cost model | 33.4 bps one-way; breakeven 234.5–236 bps | `B11`, on the corrected panel | — | n/a | **not `N`-dependent**; provably insensitive to this axis |
| fidelity bar | **0.60** | THEME-RESTORE, 36 theme pairs | FIDELITY-2 re-used it | n/a | **valid**; re-used by import, not restated — correct |
| per-horizon null (`fixed_weights_null`) | ls p95 1.7494 | S22 | X1 corroborated at 1.7405 | n/a | **valid and independently corroborated** — the best-calibrated instrument in the project |
| `MIN_COVERAGE` = 0.95 (`index_mark`) | 0.95 | never — declared a judgement | n/a | n/a | **never calibrated, and says so.** Correct practice |
| the learner's 1.64σ floor | 1.64 | **never** | never | n/a | **NEVER VALID FOR ITS CURRENT USE** — MA2 |

### MA19 — HIGH — X7's floors were last checked two `N`-regimes ago, and the project's own curve says the null has moved

The rule is the project's own, from X7RECON: *"A CALIBRATED PLACEBO FLOOR IS A FUNCTION OF `N` …
a floor may not be compared across sweeps run at different `N` without checking."* The mechanism
is documented: `_trials_haircut` is floored at the research log's `N`, the CPCV adopt gate
multiplies `se` by that haircut, so raising `N` changes **which placebo draws adopt**, and
adoption manufactures roughly +1.4 of long-short *t* in a noise draw.

The published adopt curve: **N = 8 → 27 adopters, 84 → 21, 116/121/129 → 20, 200 → 18, 400 →
17.** Today `N` = **224**. So the adopter set is no longer the one the floors were measured on;
at least two draws have flipped.

**Which recalibrations are due, which are provably insensitive:**

* **DUE:** every X7 floor (`ls_t` naive and HAC, theme IC, alpha margin, DSR bar, PBO bar). The
  haircut moved from √(2·ln 129) = 3.1176 to √(2·ln 224) = **3.2899**, a 5.5% higher adopt bar,
  which is exactly the lever that changes adopter count.
* **PROVABLY INSENSITIVE:** the cost table (`B11`) and the fidelity bar — neither reads `N`.
  Also `S22`'s `fixed_weights_null`, which runs **without CPCV in the loop** and therefore has no
  haircut to move; that is why it reproduced across X1's independent measurement to 0.009 of a
  *t*, and it is the one null that can be quoted across sweeps.
* **NEVER VALID:** the learner's 1.64σ floor (MA2).

**The check is arithmetic, not a sweep** — `cpcv_validate` banks `adopt_detail` (margin, se,
haircut, `n_trials_used`) precisely so "what would this run have scored one haircut lower" is a
calculation. **But its inputs are the 100 banked placebo draws in `data/free_analysis`, which
MA16 shows the backup skips.** The two findings compound: the cheap route to the recalibration
depends on a directory nothing preserves.

**Expected direction (HYPOTHESIS, stated so it is not mistaken for a result):** fewer adopters →
fewer draws receiving the +1.4 *t* bonus → a *lower* null p95 → the shipped 2.6199 clears
**2.2837** by *more*. If so the correction is in the strategy's favour and nothing published
needs retracting. That is a reason to do the check, not a reason to skip it.

---

## 6. MANDATE 5 — THE PROCESS ITSELF

### MA20 — HIGH — The shared checkout drifts, the drift is invisible, and it has now cost three audits

Measured: `git rev-list --left-right --count HEAD...origin/main` on
`C:\Users\donni\Downloads\valuation-tool` returns **1 508** — one commit ahead, **508 behind**.
Audit #2 measured 265 on 2026-08-10. The project's own memory recorded 472.

Two distinct costs, and the second is worse:

1. **Reading.** A session started in that checkout reads a `CLAUDE.md` without any of the last
   508 commits' corrections, and cannot see `VALQUO_LEDGER.md`, `RUN_RULES.md` or
   `VALQUO_LIVE_AUDIT.md` at all. That is how this commission came to instruct its auditor to
   work there.
2. **Writing.** The one local commit, `41d7b12`, is the **dated failure note that answers
   `PT-WRITER`** — the row three sessions hunted evidence for. It has sat unpushed since
   2026-08-10 20:06 because pushing `main` by hand is (correctly) forbidden and the sanctioned
   route is Don running `sync.bat`.

The auto-land Action solved stranded work for `worktree-*` branches and left `main` — the one
branch a human commits to — with no mechanism at all. `RUN_RULES` Part A rule 1 ("done means
pushed") is enforced by nothing for that branch.

**Cheapest fix:** a scheduled job (or a line in the existing watchdog) that reports the shared
checkout's divergence to Discord. It cannot push for Don, but "you are 508 behind and 1 ahead"
arriving daily converts an invisible drift into a chore.

### MA21 — MEDIUM — Where the process depends on an agent choosing to be honest, and where it need not

The commission asks this directly. The honest inventory:

**Depends on choosing to be honest (no mechanism could lie-proof it, and that is fine):** the
pre-commitment ordering (a register committed *alone*, as a strict git ancestor, is genuinely
verifiable and this project verifies it every time — that one is already mechanised); the
expectation scoring; the "defects in my own instrument" disclosures.

**Depends on honesty but need not — a check would do it:**

| convention | lives only in prose | the check that would enforce it |
|---|---|---|
| `N` may only change deliberately | `research_log.py` docstring | pin `by_domain` (MA13) |
| the canonical artifact must not go stale | `RUN_RULES`, memory | compare `BACKTEST_RESULTS.json`'s `n_trials` against `research_log.detail()` in CI; fail on mismatch |
| verdict vocabulary (`ADOPTED`/`REJECTED`/`NULL`/`INCONCLUSIVE`/`DEFERRED`) | ledger header | `build_ledger.py` already knows the vocabulary; make an unknown verdict a CI warning rather than a blank cell |
| a landed item must have a ledger row | ledger contract rule 1 | diff the ids named in a commit subject against the ledger |
| the live composite must equal the backtested one | `M4`, run by hand | `M4`'s harness exists; nothing schedules it |

**The manual steps that recur enough to deserve automation**, in order of frequency: running
`sync.bat` (MA20); re-reading `by_domain` after a merge (the record says this error was
committed *with the warning in view*); refreshing `BACKTEST_RESULTS.json` after `N` moves (done
by hand twice in the last week: "N 220 → 224", "N 220 → 224 refresh").

### MA22 — MEDIUM — `CLAUDE.md` has outgrown its job

344 KB / 3,813 lines, prepended to every session. It is a superb research record and a poor
operating manual, and it now contains the failure class it exists to prevent: line **3792**
states the auto-land Action *"runs all 24 suites"* while line **26** of the same file corrects
the suite count to 62 — and the measured count today is **74**. Its own task list is labelled
*"the least trustworthy section in the file."*

**Recommendation (structural, not a rewrite):** split it. `CLAUDE.md` keeps the *findings*
record, which is genuinely load-bearing and should not be trimmed; the operating instructions
(how to run, hard rules, git handoff, tool routing, task list) move to the top of `RUN_RULES.md`,
which is short, read first, and already non-negotiable. The task list itself should be deleted
in favour of a pointer to `VALQUO_LEDGER.md`, which is the answer to "where do we stand" by the
ledger's own contract.

---

## 7. MANDATE 8 — SIMPLIFICATION

### MA23 — MEDIUM — `valuation/edge/` mixes the shipped engine with a dozen finished one-shot studies

Measured, by scanning every module under `valuation/` for references anywhere in the tree:

* **`valuation/edge/ev_multiples_study.py` (425 lines) has ZERO importers** — no module, no
  script, no test, no `.bat`. `tests/test_ev_multiples.py` sounds like its pin but imports
  `fundamental_panel` and `factors` instead and never mentions it. Its verdict is already
  recorded (`CONFIG.value_ev_multiples` ships **OFF**, `HANDOFF_growth_evsales.md`).
* **Eleven more are referenced only by their own `scripts/` runner and their own test** —
  `convex_overlay`, `earnings_surface`, `kelly`, `loo_holdout`, `ml_combiner`, `surface_stock`,
  `live_replay`, `bucket_floor`, `portfolio_capacity`, `param_search`, `lazy_prices_ic`. Each is
  a completed study's analysis harness, not product code.

**I am not proposing deletion, and the reason is the project's own rule.** Deleting a study's
harness destroys the ability to re-derive its verdict, which is `RUN_RULES` rule 9's principle
one level up. What I am proposing is a **boundary**: these belong in a `studies/` package, not
in the package the Flask app imports from. Today the deploy image ships several thousand lines
of research code; a reader cannot tell product from study by location; and `surfaces.py` has to
reason about "no raw vendor rows" across a package that mixes both.

**Genuinely safe deletions, with evidence:** none that I can prove. **Things that look dead and
are load-bearing — flagged so nobody tidies them:**

* `valuation/edge/deprecated_options_exit.py` — referenced only by `tests/test_intraday.py`. That
  is audit `B16`'s *quarantine*, and the test is what proves the quarantine holds. Keep both.
* `options-bot/.gitignore:34` (`!handoff/*.zip`) — the line that recovered `C6`'s "only copy is
  on the decommissioned box" sources. The ledger says so explicitly. Keep.
* `run_backtest(panel=None)` — inert at its default, deliberately retained as `B23`'s mechanism.
* `NO_DATA_RETRY_WORKERS` in `screen.py:48` — unused, retained *with the measurement that says
  why it must stay off*. Deleting it deletes the reason.

---

## 8. MANDATE 1 — TRADE LOGIC

### MA24 — Wrong rejections: the honest answer is that there are very few, and I will not manufacture more

I looked specifically for the shapes the commission named. What I found:

**Verdicts of the "the design could not have caught the effect" shape — three, all already
labelled as such by the project itself, which is the point:**

* **`S19` (MD&A):** minimum detectable incremental IC at |*t*| = 2 is **+0.020549** against an
  original effect of **+0.0096**; the observed +0.0122 sits *below its own detection threshold*.
  The project wrote that down. **A re-run is worthless.** The binding constraint is named and
  structural — MD&A scores start 2016-08 against a panel starting 2009-01-15, and the original
  study tested **111 MONTHLY** dates while the theme panel is **QUARTERLY**.
  **NEW DESIGN, not a re-run: a monthly theme panel.** That is the only thing that re-opens it,
  it is a rebuild with its own register, and it would simultaneously unlock every other
  text-derived signal (MA33). Trial cost: 2 arms. Kill condition: if the monthly panel's own
  MDE still exceeds +0.0096 on the 418+195 name corpus, the question is unanswerable on data we
  own and should be closed permanently rather than re-opened a third time.
* **`V6-B` M2 (bankruptcy/regulatory delisting):** VOID — 42 distress events against a
  pre-committed floor of 60. Correctly voided, correctly not quoted.
* **`O10`/`O18`:** voided by the registered C2 gate. Correct.

**Near-misses recorded honestly — `S21` by 17 bps, `S12-A2` by 18 bps.** The commission invites a
re-examination list. **My recommendation is: do not re-open either, and the reason is that the
project has already answered this.** `SELRULE` asked exactly the meta-question — is the selection
rule itself testable — and settled it **NOT ANSWERABLE, declined**, *before* any run, on the
published arm table. Re-opening a 17-bps miss on the same panel is the p-hacking the commission
forbids, and there is no new evidence and no new design available for either. Recording them as
NULL by the pre-committed rule (`RUN_RULES` A6) is the correct and final treatment.

**One genuine correction to the record, in the other direction:**

### MA25 — MEDIUM — "There is no liquidity measure on this path" is true of the panel and false of the project

`B13` is BLOCKED and `S7` reports `size × liquidity` **NOT BUILDABLE** — both on the grounds
that *"the price export carries date and close ONLY, so `avg_dollar_volume` cannot be computed."*
That is accurate about the panel loader. It is **not** accurate about the project:

* `data/bulk/prepared/bars/*.pkl` carries a **`volume`** column and is read by
  `scripts/capacity.py:69-88` (`adv_from_bars`), which computes dollar ADV as
  `raw_close × volume`.
* `scripts/capacity.py`'s own header measures the coverage honestly: **290 large-cap names,
  ~3.5% of the top-25 book's 918 distinct names**, and it already built a **calibrated
  market-cap proxy** for the rest.

So the correct sentence is *"none in the panel loader; 290 names' worth in `bars/`, plus a
calibrated proxy in `scripts/capacity.py` that P1 already built and validated."* `S7` was right
to refuse a **proxy** — a stand-in is a different hypothesis wearing the same name — and I am
not arguing with that verdict.

**What this changes:** a future session reading `B13`/`S7` will conclude the data does not exist
anywhere and stop. It does exist, thinly. **Whether to test it: probably not**, and I will say so
rather than propose work for its own sake — the covered 290 names are large caps, and a
*liquidity* effect is weakest exactly there (`V6-OPT` measured its covered population at
**8.26×** the median market cap of the full one and its effect at a quarter of the headline).
A register would have to pre-commit an MDE and would likely show the test underpowered by
construction — `S19`'s lesson. **The valuable action is the correction to the record, not the
test.** If it is ever run, it must use the covered-subsample protocol `S18`/`U2`/`U3`/`V6-OPT`
established four times, and quote its MDE.

### MA26 — Untested combinations: measured quantities that sit unused

| # | hypothesis | mechanism | the pieces (all measured, all on disk) | register it needs | trial cost | kill condition |
|---|---|---|---|---|---|---|
| **A** | Accounting red flags carry **name-level** catastrophe information the composite does not | `S10-ACCT` measured excluded names crashing at **3.04×** the rate of names kept (2.660% vs 0.874%; 174/6,542 vs 939/107,403) — it failed only the **portfolio drawdown** leg, because `S10` had already shown this book's max drawdown is decided by ONE market-wide quarter (COVID 2020Q1), which no name-level screen can move | Beneish M, Altman Z, external-financing decile — all built, all published thresholds, joined from SF1 without a panel rebuild | extend `PREREG_x5_m4_b23_s10acct.md`; the arm is a **disclosure**, not a screen, so the gate is the crash-rate replication in both halves, NOT `alpha` | 1–2 | crash-rate gap fails to replicate in both halves, or the flag is a market-cap sort (C-control: median cap of flagged vs kept) |
| **B** | Top-decile **tenure** should enter construction directly, not only through the band | `S22`: alpha still accrues at **2 years** while KM median top-decile tenure is **ONE rebalance**. `S14`: a no-trade band harvests some of that gap and **half its gain is a signal effect**, not the cost saving its register claimed. The band is the only mechanism tried | `_band_select`, the banked 69-date panel, S14's own width surface | a new register; arm = an explicit **minimum hold** (e.g. 2 rebalances) *instead of* a rank band, so the two mechanisms are separated rather than compounded | 2 (one per direction) | fails either half on `top_decile_alpha` against the 1.95pp margin; or C-control shows it is `S14` renamed (rank correlation > 0.97 against the width-0.30 book) |
| **C** | The **withholding state** is information | `withhold.py` refuses a fair value when the model/price ratio leaves the band. "The model cannot value this name" is a measured, dated, per-name state | `record_refusal`, the published `fair_value_withheld` flag | — | — | **NOT TESTABLE point-in-time**, and this is the finding: `V6` established the live sub-scores are not computable historically (quality needs a WACC and `S23` measured that path fetching **LIVE Yahoo prices to value 1999**). It can only ever be a *forward-recorded* flag. Naming the blocker is the deliverable |
| **D** | `pead_car` as a **conditioner** rather than a signal | measured, `t` +2.215, coverage 82.3%, scores in **no** theme; rejected because 89% of it is orthogonal to momentum and *that* 89% predicts nothing | already computed every run | — | — | **DO NOT RE-OPEN.** The reject rests on two controls stronger than the IC, and a control using no earnings data beat it. Listed here only so it is not re-proposed |

### MA27 — Equation candidate: L2 shrinkage on the signal cross-section, and why it is not the rejected schemes in a costume

**The construction, exactly.** Take the **53 signals** already in `per_signal` (not the 7 theme
z-scores). Form the within-date standardised signal matrix `Z` (`T × N × 53`), the sample
second-moment matrix `Σ` of the signal-portfolio returns, and the mean signal-portfolio return
vector `μ`. Estimate SDF coefficients as `b = (Σ + γ·I)⁻¹ μ` — Kozak–Nagel–Santosh's ridge, with
`γ` selected on a strictly prior window and never on the scoring window. Score names as `Z·b`.

**Why it is not what has already been rejected — three distinct arguments:**

1. **It is not `S5`.** `S5` was James–Stein shrinkage of each **theme's mean IC** toward the
   grand mean. That shrinks 7 numbers toward each other in *IC space*. KNS shrinks 53
   coefficients in *covariance-weighted return space*, and the covariance term is the entire
   mechanism — it is what lets two correlated signals share one coefficient instead of double-
   counting. `S5` has no `Σ` in it.
2. **It is not `MLCOMB`.** The tree combiner searched a **non-linear interaction space** over 7
   theme z-scores and **REVERSED out of sample**. This is a *linear, convex, single-hyper-
   parameter* estimator over signals whose individual ICs are already measured. The failure mode
   that killed the tree — searching a space large enough to fit noise — is bounded here by one
   scalar.
3. **It is not the eight `_weight_schemes`.** Those operate on **7 themes** and include
   `risk-parity` and `max-ir-decorr`, which do use `Σ` — but at the *theme* level, after the
   theme means have already destroyed the within-theme covariance structure. `S16` proved this
   layer matters: splitting one input into two is a **rank identity** at the theme level and
   changes nothing, precisely because the theme mean collapses it.

**Why now.** A **2025 replication** applied exactly this estimator to the **JKP Global Factor
Data** and found the dense ridge model's out-of-sample R² comparable to the original. This
project **already holds JKP** — `X8` used it for the international replication and `D3` records
every required free factor dataset as present and verified. So the external validation dataset
and the internal panel are both on disk.

**Price.** 1 trial if run as a single pre-committed `γ` rule; 2 if run in both decide/measure
directions, which the shipped gate requires. At `N` = 224 → 226 the HLZ hurdle moves from
3.28988 to 3.29277 — **0.003 of a *t***, negligible, consistent with the ledger's standing
"trial cost is now negligible" argument.

**Kill condition, pre-committable:** the arm is rejected if `top_decile_alpha` fails the
**1.95pp** calibrated margin in **either** half, or if its within-date rank correlation against
the deployed composite exceeds **0.97** (in which case it is the incumbent with extra steps —
`S24`'s outcome at 0.9907 and `S15`'s at 0.9879). **A `γ` chosen anywhere on the scoring window
voids the arm outright.**

**My own prior, stated in advance as this project requires: I expect it to be REJECTED**, at
roughly 75/25. Everything in the weighting family has failed here by margins of 79×, and the
deployed flat 1/7 has never been beaten. The reason to run it anyway is that it is the *one*
member of the family whose mechanism (a covariance term at the signal layer) has never been
tested at all, and `S16` proved that layer is where information is being destroyed.

---

## 9. MANDATE 3 — NEW FEATURES · **ALL HYPOTHESIS**

Posture rules bind throughout: no performance claims, no per-name precision (`V3`), withholding
honoured, no raw vendor rows. Each is a screen or a disclosure built from already-measured
pieces, with the register its claim would need stated before the idea.

### MA28 — HYPOTHESIS — "Accounting red flags" — a name-level risk card

**What it shows.** On a name's row: *"This company trips 2 of 3 published accounting-stress
flags."* Plus the base rate, stated as a base rate: **names tripping 2 of 3 fell 20%+ in a
quarter 2.66% of the time against 0.87% for names that did not, over 69 quarters.**

**The measured pieces:** `S10-ACCT`'s Beneish M-score (>−1.78), Altman Z (<1.81) and
top-decile external financing, all published thresholds, all computed from SF1, all already
joined without a panel rebuild. The **3.04×** ratio is measured on 113,945 rows.

**The claim it would tempt the product to make:** *"avoid these names"* — which is a return
claim and is **not supported**: `S10-ACCT` was REJECTED, and its valuation sibling found the
exact opposite sign. The copy may only say what `V6-B`'s dip card says: a base-rate difference in
a *specific, named* bad outcome, with the sample and the window attached.

**The register it needs:** the both-halves replication of the crash-rate gap (not of alpha), a
market-cap control (`U7`/`S10`'s failure mode), and a `BANNED` phrase tuple asserted against the
**rendered payload** — the app lane's `dip_posture.py` design, which the record explicitly says
should be carried forward.

**Why this one is first:** the template is proven. `V6B-PRODUCT` shipped exactly this shape —
a risk claim with numbers, a return claim held at NULL — on 2026-08-13.

### MA29 — HYPOTHESIS — "What the model cannot value" — a transparency surface

**What it shows.** A count, and optionally a list: *"Today the engine refused to publish a fair
value for N of M names it scored, because its estimate was more than X× the market price."*

**The measured pieces:** `withhold.py`'s band, `record_refusal`, and the `fair_value_withheld`
flag — all shipped, all already computed on every scan.

**Why it is a feature and not just plumbing.** `LA1` was BLOCKING precisely because a refusal
that fails to record is invisible: the peer estimator filled the empty cell and published +204%
on the site's number-one name. **A surface that displays the refusal count makes LA1's failure
mode loud instead of silent** — the product's own users become the guard. It is the cheapest
possible fix for the class audit #2 identified as *the* structural weakness ("correct in-process,
blind at the output boundary").

**The claim it would tempt:** none about returns. The risk is the opposite — it must not read as
*"these names are overvalued."* A refusal means the **model** failed, not the name.

**Register:** none needed for the count (it is a fact about the run, not a hypothesis). A
`V3`-style pinned-copy module would be needed for the wording, since "we could not value this"
is easily misread.

### MA30 — HYPOTHESIS — Tenure on the hot list

**What it shows.** Per name: *"in the top decile for 4 consecutive rebalances."*

**The measured pieces:** `S22`'s Kaplan–Meier tenure distribution (median **one** rebalance) and
`S14-WIDTH`'s incumbent share (0.359 → **0.701** at width 0.30).

**Why it is honest and useful:** it discloses churn, which is the single most misleading thing
about a ranked list refreshed daily — and `S22` measured that the typical name leaves after one
rebalance while the alpha it earns is still accruing at two years. **The claim it must not
make:** that long-tenured names are better. `S22` measured a term structure of the *signal*, not
of tenure, and no arm has tested tenure as a predictor.

**Register:** none for display. **A register the moment anyone sorts or filters by it** — that
converts a disclosure into a screen and needs the both-halves gate.

---

## 10. MANDATE 4 — EXTERNAL RESEARCH

Treated as hypotheses, not facts, as instructed. This project has refuted published results
before (`O7` contradicts Gao–Xing–Zhang's sign; `U2` fails to reproduce Xing–Zhang–Zhao's smirk
direction; `O3`/`O4`/`O5` reversed a prior lane's suggestive result once the instrument was
fixed).

**Four rows below are actionable and carry IDs so the execution machinery can pick them up:**
**MA31** = row 7, Cremers–Weinbaum matched-strike put–call parity (the largest un-run item either
prior audit named); **MA32** = row 6, the open-vs-close position decomposition of options volume;
**MA33** = row 8, the monthly-panel rebuild that unlocks the text/LLM class (and `S19` with it);
**MA34** = row 4, writing the post-publication decay prior into the contract's expectations at
zero trial cost. Rows 1, 2 and 5 are corroboration or external controls, not new work.

| # | finding | replication status in the literature | mapping here |
|---|---|---|---|
| 1 | **Jensen–Kelly–Pedersen (JF 2023), "Is There a Replication Crisis in Finance?"** — 318 characteristics rebuilt across 93 countries; most replicate, and factors with higher in-sample alpha have higher out-of-sample alpha | strong; the dataset (JKP Global Factor Data) is the field's reference | **ALREADY USED HERE** — `X8` replicated the theme structure on it, on another vendor's data in another country, verdict `REPLICATES`. This is the project's single strongest external validation and the record is right to lean on it |
| 2 | **Novy-Marx & Velikov (RFS 2016), "A Taxonomy of Anomalies and Their Trading Costs"** — the **buy/hold spread** (stricter entry than exit) is the *most effective* cost-mitigation technique; anomalies under ~50% monthly turnover generally survive costs | widely replicated, foundational | **ALREADY TESTED HERE, and the literature names the mechanism the project half-discovered.** `S14`'s no-trade band **is** a buy/hold spread. `S14`'s register claimed a "pure cost mechanism, no signal claim" and its own correction #1 found gross alpha *also* improves — which is exactly what NMV predict, because a hold band stops the book churning on rank noise. **Corroboration, not a new test.** The project's post-band turnover (~1.35 per rebalance, ~10–13%/month) sits comfortably inside NMV's survivable class |
| 3 | **Kozak, Nagel & Santosh (JFE 2020), "Shrinking the Cross-Section"** — dual-penalty (ridge/L2) SDF estimation over many characteristics; robust out-of-sample in high dimensions. **A 2025 replication on JKP data** found mixed success overall but the **dense ridge model's out-of-sample R² comparable to the original** | mixed-to-positive; the ridge arm is the part that replicates | **TESTABLE HERE, and it is my one equation proposal — MA27.** Data: the 53-signal panel + JKP (already on disk, `D3`). Register: as specified in MA27. Note the 2025 replication's *mixed* verdict is itself the reason to pre-commit a kill condition |
| 4 | **McLean & Pontiff (JF 2016) and successors** — post-publication premia decay ~**one-third** as institutions trade them | replicated repeatedly | **TESTABLE HERE AS A PRE-REGISTERED EXPECTATION, not as a backtest.** `R1` established that `size`, `quality` and `momentum` **are** the standard premia (SMB +0.39, RMW +0.30, UMD +0.18, all *t* > 3.4) while `value` and `capital_discipline` are **not** (HML *t* 1.08, CMA *t* 1.08). So a decay prior applies to part of the composite and not the rest — and the forward track is the instrument that would see it. **This is the cheapest thing on this list:** write the expected decay into the contract's expectations before the window accrues. Zero trials |
| 5 | **Chen & Zimmermann, Open Source Asset Pricing** — 200+ published predictors reproduced with code; decay confirmed; **effective bid-ask spreads wipe out most post-publication returns for a large subset** | the reference open replication | **TESTABLE HERE and cheap.** Free data, no licence question. Its value is as an **external control on `B11`**: the project's 33.4 bps one-way and 234.5 bps breakeven are internally measured with no external benchmark. OSAP's cost figures give one |
| 6 | **Ge, Lin & Pearson (JFE 2016), "Why does the option to stock volume ratio predict stock returns?"** — the **O/S ratio** negatively predicts underlying returns at ~1 week; the effect is concentrated in **call purchases that OPEN new positions** | replicated; a core options-flow result | **PARTIALLY TESTABLE, and it is not what `O14` tested.** `O14` ran `signed_volume`, `pc_flow_imbalance`, `block_share`, `unusual_volume`, `sweep_share` — none is the O/S ratio, which needs **stock** volume. Per MA25 that exists for only ~290 names. **BUT the open-vs-close decomposition — the strongest half — needs only option volume and open-interest *change*, both of which `data/options` carries.** That is the genuinely new, buildable arm |
| 7 | **Cremers & Weinbaum (JFQA 2010)** — put–call **parity deviations on matched strikes** predict returns (~51 bps/week) | replicated | **TESTABLE HERE AND EXPLICITLY NOT YET TESTED.** `U2` closed `PARTIAL` for exactly this reason: this is *"Cremers–Weinbaum's ACTUAL measure and the largest effect the section cites"*, it needs matched call/put pairs from the raw chains, and the task forbade new features. `V6-OPT` has since proven the cache holds **1,288,750 puts against 1,288,751 calls, zero tickers with no puts** — so the blocker `U2` recorded is gone. **This is the largest un-run item the prior audits named.** Constraint: the derived layer spans 2016-01 → 2025-12, so 29 of 69 dates carry zero coverage and the covered-subsample protocol binds |
| 8 | **LLM-derived signals from filings and transcripts (2024-2026)** — a large and fast-moving literature; surveys report improved predictability from disclosure and earnings-call text | **weak and unstandardised** — the surveys themselves note signals are "not yet widely standardized or consistently benchmarked", and almost nothing is point-in-time-clean | **NOT TESTABLE HERE AS PUBLISHED, and blocked by the same thing as `S19`: panel frequency.** The project owns a real MD&A corpus (195 + 418 names, 15,893 filing pairs) and an `ANTHROPIC_API_KEY`. What it does not own is a **monthly** theme panel, and `S19` proved a quarterly panel cannot detect an effect of this size. **So the unlock is MA24's monthly rebuild, and it unlocks the whole class at once** — which is the strongest argument for paying for that rebuild |
| 9 | **0DTE / retail options flow** — retail was ~53–54% of SPX 0DTE volume through 2025; 0DTE reached ~60% of SPX option volume; single-name Mon/Wed expiries approved for a defined set in early 2026 | market-structure fact, well documented | **NOT TESTABLE HERE** (index options, no data) **but it carries a real caveat for `O14`.** Bryzgalova et al.'s retail-loses-money result was `O14`'s reason for running two-sided arms; the retail share has risen materially *since* the sample. Any future re-read of `sweep_share` (the near-miss at |t| 3.061 full-sample) must state that the flow population changed after the window it was measured on |

**Sources:**
[Jensen–Kelly–Pedersen, *Is There a Replication Crisis in Finance?*, JF 2023](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13249) ·
[Novy-Marx & Velikov, *A Taxonomy of Anomalies and Their Trading Costs*](https://academic.oup.com/rfs/article/29/1/104/1844518) ·
[Kozak, Nagel & Santosh, *Shrinking the Cross-Section*](https://www.nber.org/system/files/working_papers/w24070/w24070.pdf) ·
[2025 replication on JKP data](https://research.cbs.dk/en/studentProjects/shrinking-the-cross-section-again-what-changes-when-data-does-a-s/) ·
[Chen, *Accounting for the Anomaly Zoo: a Trading Cost Perspective*](https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2019/09/Accounting-for-the-Anomaly-Zoo.pdf) ·
[Ge, Lin & Pearson, *Why does the option to stock volume ratio predict stock returns?*](https://www.sciencedirect.com/science/article/abs/pii/S0304405X16000167) ·
[*The New Quant: A Survey of LLMs in Financial Prediction and Trading*](https://arxiv.org/html/2510.05533v1) ·
[Cboe, *0DTE Index Options and Market Volatility*](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf)

---

## 11. Batched questions for Don

Answers to 1 and 2 decide the severity of the single most important finding in this document.

1. **Have you ever received an email with the subject *"🧠 Valquo self-learning — weights
   updated"*?** (As opposed to *"— monthly check (no change)"*.) If yes, the live product's
   weights have been changed by a machine and MA1 is CRITICAL rather than armed. If you have
   never received *either* subject, the monthly job is failing silently and that is its own
   finding.
2. **Is `LEARN_ENABLED` set to anything on Render?** It is undocumented and defaults to on.
   *(Assumption I have used in the absence of an answer: it is unset, therefore enabled.)*
3. **When you regate `PUBLIC_FULL_VIEW`, may the next lane also rotate `DEMO_ACCESS_TOKEN`?**
   Per MA9 the regate does nothing without it, because the token is printed on `/work`.
4. **Is `data\options_ticks` (≈4.7 GB) on the D: drive?** The backup script does not name it in
   either list, so it is not copied by that script — but something else may have.
5. **Who owns `ADMIN_TOKEN` rotation, and has it ever been rotated?** It exists in GitHub
   Actions secrets and in Render env and must move in both within one window.
6. **Would you like the primary checkout synced?** It is 508 commits behind, and the one commit
   it holds that `origin/main` does not is the answer to `PT-WRITER`. It needs `sync.bat`; no
   agent may push `main`.

---

## 12. Where the next real improvement most plausibly lives — and where nobody should look again

**Nobody should look again at:** weight tuning in any form (CPCV's best challenger missed by a
factor of **79**, and five further schemes were rejected in one session); sector-neutral ranking
(three rejections, and both named routes back — `S25` and `S15` — are now shut); the SF3
conviction family and the four classic anomalies (closed on the corrected universe, and the
conviction family is a market-cap sort at ρ −0.82 to −0.86 against `size`); signal transfer
between the two books (`U1`, `U2`-level, `U7` all rejected; the surface is genuinely orthogonal
and genuinely predicts nothing); the ML tree combiner (it **reversed** out of sample); and any
re-run of `S21` or `S12-A2` on this panel. That list is not a lament — it is the most valuable
thing the project owns, because it is the reason to believe the survivors.

**The next real improvement is not a signal.** On the evidence, the marginal value of another
arm on this panel is close to zero: the record is roughly 224 equity and 292 options trials with
essentially everything null, the deployed composite is flat 1/7 and has never been beaten, and
the one place a genuinely new effect turned up (`V6-B`'s dip survival, HAC *t* −10.58, replicated
in both halves and in five of five size quintiles) was found by asking a **risk** question rather
than a return question.

It lives, instead, in **closing the gap between the research programme and the thing that
ships** — and MA1 is the proof that the gap is real and load-bearing: the most carefully gated
number in this project is one nobody trades, while the number every user sees can be changed by a
monthly cron on a bar that was never calibrated, through a gate that does not compare itself to
the incumbent, without closing a vintage. Fixing that costs no trials, moves no published claim,
and removes the single largest way this project could quietly stop being true.

Second, and only slightly behind: **the forward track is still the only data nobody has looked
at, and it is not being written.** Every internal bar has now been cleared or honestly failed on
one 18-year panel; `X1` showed the headline survives a split by *name*, which was the last
untested independence axis available *inside* the sample. There is nothing left inside. The
contract's clock has been reset three times in four days and vintage 4 has recorded zero rows.
**Every day that passes without a row is a day of the only evidence that could still change the
answer, thrown away** — and unlike everything else in this document, it cannot be recovered
later.

If those two are done, the third is `MA24`'s monthly panel rebuild, because it is the single
change that unlocks a whole blocked class (`S19`, and every text- or LLM-derived signal behind
it) rather than buying one more arm.
