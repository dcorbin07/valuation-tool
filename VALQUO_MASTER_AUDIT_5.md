# VALQUO MASTER AUDIT #5 — THE INSTRUMENT AUDIT

**Date: 2026-08-26. Scope: the machinery built in the week to 2026-08-25 and never reviewed —
the S3-I1 fleet harness, the family (D) recorders, the WRDS collection path, and S25's
crosswalk / the IBES event spine.**

**ZERO TRIALS. This audit states no hypothesis, sets no bar and returns no verdict against
one.** It is an audit of instruments, not of ideas, and it deliberately generates no new
research items. The research queue is empty on purpose and the panel is converged;
manufacturing registers here would be the failure, not the deliverable.

---

## 0. HOW TO READ THIS, AND TWO THINGS ABOUT THE DOCUMENT ITSELF

**EVERY FINDING BELOW WAS MEASURED, NOT ARGUED.** Each item carries the command or the probe
that produced it and the literal output. Where a claim could only be reasoned about, it is
labelled as reasoning and not counted as a finding. Three candidate defects were investigated,
found to be wrong, and are recorded in section 7 beside the things that were clean — because an
audit that reports only problems cannot be distinguished from one that stopped looking.

**THE IN-SCOPE SUITES ARE ALL GREEN, AND THAT IS THE POINT RATHER THAN A REASSURANCE.** Eighteen
in-scope suites were run (`test_fleet_*` x11, plus `test_wrds_client`, `test_s25_sector_map`,
`test_ibes_events`, `test_event_spine`, `test_mb31_staleness_map`, `test_record_this_week`,
`test_research_log_integrity`) and **all eighteen pass**. **Not one finding in this document is
visible to that suite.** They fall into two families — something present where the code is
TESTED and absent or different where it RUNS, and a guard that reports success in a state it
was written to catch — and several belong to both. Both families are invisible to a green
local run by construction, which is not a comment on the suite. That is this
project's most repeated lesson and it is the reason the audit was commissioned before the
evidence accrues rather than after.

**A NOTE ON THIS FILE'S OWN SIDE EFFECT, found by measurement and acted on.**
`scripts/sc1_prior_calibration.py:458` and `scripts/sc1b_cluster_by_item.py:108` build the
prior-calibration corpus by globbing `VALQUO_MASTER_AUDIT*.md` at the repo root, so **this file
joins that corpus the moment it lands.** No published figure moves — `SC-1b` pins its corpus to
measurement commit `8e2e9fe` and its §6.2 forbids re-running on today's tree — but a future run
would score this document. `SC-1b`'s own measured limitation is that a write-up scoring
expectations as a pipe-delimited TABLE is visible to the classifier while a numbered LIST is
invisible. **So this audit deliberately contains no pipe-delimited expectation-and-outcome
table**, because an instrument audit that made no forecasts should not inject rows into a
calibration study that would score them as forecasts. Recorded here rather than left to be
discovered.

**SEVERITY MEANS BLAST RADIUS, NOT EFFORT.** `HIGH` = the record it produces is or will be
wrong, or cannot be recovered. `MEDIUM` = a guard that does not guard, or a claim the tree does
not honour. `LOW` = latent, correct-today, or presentational.

**FIX CLASS.** `CORRECTNESS` = zero trials, no hypothesis, no bar, no verdict — the `MA5` /
`I-3` / `MB42` class, landable as an ordinary repair. `DECISION` = it needs Don, or a register,
because it changes what a book is held to or what the system is allowed to do.

---

## 1. THE HEADLINE, IN ONE PARAGRAPH

**The fleet cannot place an order in production, and two of its three irreplaceable day-1
series have been recording a fabricated zero since the day they started.** Those are findings
1 and 2 and they are independent of each other. Everything else is secondary. The harness
itself — the declaration gate, the ancestry proof, the hash chain, the append-only writer, the
refusal vocabulary, the manifest fallback — is **well built and, with the exceptions listed,
does what it says.** The defects cluster in exactly two places: the seam between the harness
and the code that runs it, and the seam between a recorder and the source it was supposed to
read. Both are seams, not centres, which is what one would expect of machinery assembled in a
week under a correct design.

---

## 2. HIGH

### H1 — THE TWO ORDER-PLACING BOOKS RAISE INSTEAD OF FILLING, IN THE IMAGE, ON THE FIRST DAY THEY HAVE A PICK

**This is the fourth instance of the family the audit was commissioned to sweep for, and it is
in the module written *after* the manifest repair closed the third.**

`valuation/edge/fleet_books.py` resolves each book's declaration hash by reading the markdown
file directly, at lines 235 and 333:

```python
sha = F.declaration_sha(_read(F.declaration_path("f3_bear_puts", root)))
sha = F.declaration_sha(_read(F.declaration_path("f8_csp_entry_financing", root)))
```

`.dockerignore` excludes `*.md`, so **no `DECL_*.md` exists in the deployed image.**
`fleet.decl_sha_for()` exists precisely for this and its own docstring says why — *"Every writer
needs this and each one resolving it for itself is how two copies of a fact drift (`MA5`)"* —
and `fleet_books.py` does not use it.

**MEASURED.** An image-shaped root (`data_export/` present, no `DECL_*.md`, no `.git`), driven
on a real date from the published holdings artifact that genuinely has one pick:

```
image root contains DECL files: NONE (as in production)
manifest resolves books: 18
fleet.decl_sha_for('f3_bear_puts')      -> c10a70e074ccbc31
fleet_books' own resolution, same root:
   RAISES -> FileNotFoundError  ...\DECL_f3_bear_puts.md

assignment provider registered: True
picks on 2026-08-21: 1 -> ['BIO']
running f8_csp_entry_financing in the IMAGE root, on a day that HAS picks:
   RAISES -> FileNotFoundError  ...\DECL_f8_csp_entry_financing.md
```

**WHY IT HAS NEVER BEEN SEEN.** Both rules return `[]` before touching the declaration when
nothing qualifies. The read is reached only on a day the book would actually trade, so **every
quiet cycle so far has looked healthy and the defect fires exactly once — on the first day that
would have been evidence.**

**BLAST RADIUS.** `f3_bear_puts` and `f8_csp_entry_financing` are the **only two order-placing
rules in the fleet** (`f1_fill_ab` is a rider that returns `[]` by design). So **no fleet book
can record a fill on the service, ever, under the current tree.** `cycle()` catches the
exception and reports `ENTRY_RULE_RAISED`, which reads as a defect in the rule rather than as a
deployment gap — and that branch **writes no row on the book's stream**, so the lost day leaves
no dated record anywhere. The ledger's `ARMED — entry rule IMPLEMENTED` status for F-1, F-3 and
F-8 is true of a worktree and false of the service.

**FIX CLASS: CORRECTNESS.** Replace both call sites with `F.decl_sha_for(book, root)` and refuse
the candidate when it returns `None`. The one-line-per-site repair is smaller than the finding;
the durable part is that a second resolver was written three days after the first was built to
prevent exactly this.

---

### H2 — TWO OF THE THREE (D) RECORDERS WRITE A FABRICATED ZERO EVERY WEEKDAY, AND THE ALARM BUILT TO CATCH THAT IS DEFEATED BY IT

**These are the series whose entire justification is that they cannot be rebuilt backwards.**

`valuation/edge/fleet_history.py` exposes `record_all(date=None, *, store=None, rejects=None,
quotes=None, root=None)`. **The only production caller is `app_saas.py:781`, which passes
nothing:**

```
$ grep -rn "record_all|record_dip_rejects|record_iv60|record_alert_count" --include=*.py .
  (excluding fleet_history.py itself)
./valuation/saas/app_saas.py:781:                rec = fleet_history.record_all()
```

So on every write-path cycle `rejects` is `None` and `quotes` is `None`.
`record_dip_rejects(None)` records an empty list; `record_iv60(None)` records an empty dict.

**MEASURED**, on a clean root, with the production call shape:

```
record_all(no rejects, no quotes) ->
{ "recorded": 3, "failed_to_start": [], "ok": true, "loud": "" }

--- alert_count ---   date,n_alerts,payload
                      2026-08-26,0,"{""n"":0}"
--- dip_rejects ---   date,n_names,payload
                      2026-08-26,0,[]
--- iv60_atm ---      date,n_names,payload
                      2026-08-26,0,{}

coverage(): dip_rejects -> {present: true, n_days: 1, vacuous: false, ...}
            iv60_atm    -> {present: true, n_days: 1, vacuous: false, ...}

A reader asking 'was AAPL a dip-reject on 2026-08-26?' gets: []
   <- indistinguishable from a real 'no'
```

**THE ROWS ASSERT SOMETHING FALSE.** `dip_rejects` records *"zero names were rejected today"*
when the dip screen was never run. `iv60_atm` records *"no name had a solvable 60-DTE ATM IV
today"* when no chain was ever fetched. `alert_count` is the one genuine series — it reads
`store.load_intraday()`, a real source.

**THE ALARM IS DEFEATED BY THE EXACT FAILURE IT WAS WRITTEN FOR.** `record_all`'s own docstring
says: *"the one failure that would make that false while every test still passes is a series
that quietly records nothing — an unreachable service, a read-only disk, a permissions fault.
So after every attempt each series is RE-READ from disk, and one that is still ABSENT is
reported in `failed_to_start`"*, and *"ABSENT-AFTER-ATTEMPT IS THE TEST, not the return value of
the write."* **A content-free write is still a write**, so the series is present, `n` is
non-zero, `failed_to_start` is empty, `ok` is `true` and `loud` is the empty string.
`coverage()` reports `vacuous: false`. The runner's door surfaces none of it.

**AND IT CANNOT BE CORRECTED IN PLACE.** These are `append_only` streams keyed on `date` with a
backward write REFUSED, and the module's own `BACKFILL_HINT` reads *"A missed day is a GAP and
stays one ... Record the gap, never the guess."* **The door that would repair a fabricated row
is the one the design deliberately closes.** There is no `migrate_stream` equivalent for the
history series — that helper is fleet-records-only.

**BLAST RADIUS.** `F-11`'s declared hypothesis is a name's **FIRST appearance** in the
dip-reject population. Every fabricated empty day is a positive assertion of *absence* on that
date. When the screen is eventually wired, the first real appearance will be dated to that day
and the preceding months of empty rows will read as genuine observations of absence — the
finding will be manufactured by the recorder. `F-5` is partially protected by accident:
`history_for()` skips days a name is absent, so empty days do not enter its expanding percentile
as observations. That protects the percentile's *count* and not the series' *description of
itself*.

**FIX CLASS: CORRECTNESS**, and the shape is already established in this module. `record_iv60`
already refuses to record a name with no solvable IV — *"A name with no solvable IV is OMITTED,
never recorded as zero"*. The same rule has to apply one level up: **a source that was not
consulted is not an observation of nothing.** `record_dip_rejects(rejects=None)` and
`record_iv60(quotes=None)` should refuse and report, so the absent series lands in
`failed_to_start` and the `loud` alarm fires as designed. The existing rows are a `PT-AMEND1`
question — dated, disclosed, kept, and never edited away.

---

### H3 — THE TWO DATASETS THAT CANNOT BE REBUILT ARE NOT EQUALLY PROTECTED, AND THE FLEET SELF-HEALS OVER ITS OWN DATA LOSS

The bound paper track has a backup. `.github/workflows/track-backup.yml` exists for a reason it
states in its own header — *"the forward track cannot [be rebuilt], because it is a record of
what was observed"* — and it crosses the gap over HTTP via `GET /admin/export-track`, renders
into `data_export/`, guards against the committed copy, and commits weekly.

**The fleet records and the (D) history series have none of that.** Measured:

```
$ ls .github/workflows/
auto-scan.yml  fleet-cycle.yml  land-agent-branch.yml  track-backup.yml  track-row.yml

$ grep -n 'app.route("/admin' valuation/saas/app_saas.py
  ... /admin/export-track ... /admin/track-row ... /admin/fleet-cycle ... /admin/track-seed ...
  (no fleet export route)

$ grep -rni "export.fleet|fleet.export|backup.*fleet" --include=*.py --include=*.yml .
  (nothing but fleet_export_declarations / fleet_export_gates, which export the
   DECLARATIONS and the GATES -- inputs, not records)
```

So `data/fleet/*.csv` and `data/fleet/history/*.csv` exist in **exactly one place**: the Render
persistent disk (`render.yaml`, `disk: {mountPath: /app/data, sizeGB: 1}`). `data/` is excluded
from the image, is gitignored, and there is no export door, no backup job and no snapshot. A
disk loss, a service recreation, or a blueprint edit that drops the disk destroys the fleet's
entire evidence base permanently.

**AND THE SYSTEM REPAIRS OVER THE LOSS RATHER THAN REPORTING IT.** The hash chain's stated
bound (`CHAIN_BOUND`) claims detection of *"reordering, an interior deletion, a truncation"*.
**Whole-file loss is none of those and is not detected.** Measured:

```
C. Is the LOSS OF A WHOLE STREAM detectable?
   with records : ok=True  vacuous=False n=2
   file DELETED : ok=True  vacuous=True  n=0
   may_fill after deletion: False SELFCHECK_ABSENT

C2. After a stream is lost, does the next write-path cycle SELF-HEAL over it?
   before loss: 2 rows, chain ok=True
   after loss : may_fill -> SELFCHECK_ABSENT
   after run_day1 re-certifies: may_fill -> True | rows = 1 | chain ok = True
```

`may_fill` refuses immediately after the loss — but with `SELFCHECK_ABSENT`, which reads as
*"this book has never been certified"* rather than *"this book's history was destroyed"*. And
the endpoint's write path runs `run_day1` for exactly the books whose self-check is not `ok`,
which **re-stamps a passing certificate and the book resumes at seq 1 with a chain that
verifies and nothing anywhere recording that a prior history existed.** The catch is incidental
(the self-check row happened to be inside the deleted file), not a property of the chain.

**FIX CLASS: DECISION.** The cheapest correct answer is the one the track already uses — an
owner-only `GET /admin/export-fleet` returning the streams, plus a weekly job that commits them
under `data_export/`, with the same guard-against-committed check `track-backup` runs. That is a
new outbound surface carrying sandbox trade records, so it is Don's call rather than a repair to
be landed quietly. A strictly smaller correctness half is available immediately and does not
need a decision: **record the book's expected row count somewhere outside the stream** (the
declaration manifest cannot, being immutable; a sibling high-water file on the same disk can),
so that a stream shorter than its own recorded high-water mark refuses rather than re-certifies.

---

## 3. MEDIUM

### M1 — THE DAY-1 CERTIFICATE COUNTS NOT-RUN CHECKS AS PASSES, AND SAYS THE OPPOSITE IN ITS OWN DOCSTRING

`scripts/fleet_selfcheck.py`:

```python
def skip(name, why):
    """NOT-RUN, and never counted as a pass. `O21-D2`'s C5: a check that could not run
    and one that ran and found nothing must not read the same."""
    checks.append({"check": name, "pass": True, "skipped": True, "detail": why})
...
n_pass = sum(1 for c in checks if c["pass"])
return {..., "n_pass": n_pass, "ok": n_pass == len(checks) and len(checks) >= 15}
```

**MEASURED**, reproducing the image's actual condition (`python:3.11-slim` ships no git binary,
which `git_available()`'s own docstring documents):

```
n_checks=20 n_pass=20 ok=True
SKIPPED (never executed): ['6 an UNCOMMITTED declaration refuses the fill',
                          '7 a declaration committed ALONGSIDE another file refuses the fill']
their 'pass' values: [True, True]

What run_day1 forwards into the endpoint response body:
{ "ok": true, "n_pass": 20, "n_checks": 20, "failed": [] }
```

The `skipped: True` flag exists in `checks`, but `run_day1` forwards only
`{ok, n_pass, n_checks, failed}` and **drops the per-check list**, so the flag reaches neither
the endpoint response, nor the workflow log, nor any human.

**BLAST RADIUS.** This is the gate that opens every book's ability to fill, and on the service
it reports a perfect score for a run in which 10% of its checks did not execute. The mitigation
is real and should be stated: checks 6 and 7 exercise `declaration_commit`, which is genuinely
unreachable in the image, and the commit facts they protect are verified where git exists and
carried in the manifest. **So no unverified rule is being relied on. What is wrong is the
number** — and "20/20" is precisely the figure a reader trusts.

**FIX CLASS: CORRECTNESS.** Count skips apart (`n_pass`, `n_skipped`, `n_run`), make `ok`
require `n_pass == n_run` with a floor on `n_run` rather than on `len(checks)`, and forward
`skipped` into `run_day1`'s summary. The `len(checks) >= 15` non-vacuity floor is good and
should be kept — it should simply count executed checks.

---

### M2 — `read_meter` RETURNS A VERDICT WITH `ok: True` WHEN THE READ WAS NOT RECORDED

`fleet.read_meter`'s docstring: *"Read a book's meter AND RECORD THE READ. There is no
unrecorded door ... So this is the only reader, and it writes before it returns."* The trial
rule depends on it: *"every meter read is itself a record — otherwise the rule is an honour
system and 'nobody peeked' is a memory rather than a dated fact."*

The code computes the meter, calls `record(...)`, sets `m["recorded"] = bool(w.get("wrote"))`,
then sets `m["ok"] = True` unconditionally and returns the verdict either way.

**MEASURED**, in the documented real scenario — a stream written before the four `(C)` columns
were added on 2026-08-24, which `append_only` refuses to widen:

```
stream header is the PRE-(C) one, 26 columns (current is 30)
verify_chain: True        may_fill: True

read_meter ->  ok                    : True
               state                 : NO CONCLUSION
               is_first_verdict_read : True
               trial_charge          : CHARGE ONE TRIAL NOW, to options
               recorded              : False
               record_reason         : refusing to widen the header ... append-only write
meter_read rows now on the stream    : 0
```

A verdict state, a first-read flag and a trial-charge instruction were returned, and **no dated
record of the read exists.**

**BLAST RADIUS.** Bounded today: `run_day1` invokes `migrate_stream` for every declared book on
the write path, which would clear a pre-`(C)` stream on the next cycle. But `read_meter` is a
library function a human can call at any time, `migrate_stream` runs only when a self-check is
already stale, and the refusal class is general — a read-only disk or a ragged file produces the
same shape. The rule this defeats is the one that makes the fleet's trial accounting auditable
rather than remembered.

**FIX CLASS: CORRECTNESS.** Return `ok: False` with the verdict fields withheld when the record
did not land, or record first and compute second. The stronger form is the second: a reader who
cannot be recorded should not be shown the number.

---

### M3 — `RULE_ARMED_NEVER_FIRES` IS STRUCTURALLY UNREACHABLE FOR BOTH IMPLEMENTED ORDER-PLACING RULES

`never_fires()` counts rows of kind `fill` or `skip` as observations, and fires when
`fired == 0 and n_obs >= after`. A rule returning `[]` causes `cycle()` to write **no row at
all**, so `n_obs` never leaves zero.

**MEASURED, with a positive control** so the alarm is not being blamed for something it does
correctly:

```
40 cycles run, every one selecting nobody:
   observations : 0     fired : 0     skipped : 0     after (bar) : 10
   skip_rate    : None  STATE : OK
   cycle().never_fires list: []
   rows on the stream      : 1

positive control -- a rule that RECORDS its skips:
   observations=12 state=RULE_ARMED_NEVER_FIRES
```

**The alarm works. Its coverage does not reach the rules that exist.** `f3_bear_puts` and
`f8_csp_entry_financing` both return `[]` on a quiet day and emit no skip records, so the third
state — the one the Frontier Scout added specifically to separate *"the rule ran and nobody
qualified"* from *"the rule CANNOT qualify anybody, ever"* — can never fire for either of them.
The docstring's own worked example (`F-4`, *"reports a skip rate of 1.0"*) assumes a rule that
records its skips.

**FIX CLASS: CORRECTNESS.** Either count *cycles in which the rule ran* rather than rows it
wrote (which needs a cheap per-book cycle counter the streams do not currently carry), or
require an implemented rule to emit a `skip` for each candidate it declined. The second is
better and matches `F-14`'s framing that *"the skips ARE the control population"* — but it is a
change to what the streams contain, so it wants stating in the affected declarations.

---

### M4 — THE HARNESS FINGERPRINT COVERS TWO OF THE EIGHT MODULES ITS CERTIFICATE ATTESTS TO

`harness_fingerprint()` hashes `fleet.py` and `append_only.py` and nothing else. The day-1
certificate it stamps attests to behaviour that also lives in:

```
modules the GATE depends on but the fingerprint does NOT cover:
   ['assignment.py', 'fleet_books.py', 'fleet_gates.py', 'fleet_history.py',
    'paper_broker.py', 'track_meter.py']
```

**The sharpest case is `paper_broker.py`.** The self-check's load-bearing live check — `L9b`,
*"the RECORD AGREES WITH THE BROKER — no fill price without an execution"* — exists because a
prior cut of `fill_fields` reported a pending order as filled at its own limit price, and the
repair delegates to `PaperBroker.fill_price`. **A change to `PaperBroker.fill_price` does not
make a single book's self-check go STALE**, so the fabricated-fill defect could be reintroduced
and every book would keep its passing certificate.

Same for `fleet_books.py`: an entry-rule change does not re-trigger day-1 verification.

**FIX CLASS: CORRECTNESS.** Widen the fingerprint to the modules the certificate covers. The
stated cost is real and should be weighed — the endpoint re-runs `run_day1` (which places a real
sandbox order) whenever any book is stale, so a wider fingerprint means more day-1 runs. That is
the correct direction: a certificate should go stale when the thing it certifies moves.

---

### M5 — NOTHING KEEPS THE SHIPPED DECLARATION MANIFEST FRESH

`data_export/fleet_declarations.json` is the **entire evidence base for the gate in
production** — in the image it supplies the declaration, its content hash and its commit facts,
and `may_fill` reports `evidence: "manifest"` on every result.

**It is currently fresh.** Measured against the tree today:

```
manifest entries: 18
DRIFT: none - every manifest decl_sha matches the on-disk DECL file
parseable DECL files absent from manifest: none
```

**Nothing enforces that.** No workflow regenerates or verifies it:

```
$ grep -rn "fleet_declarations" --include=*.py --include=*.yml .
   (only the exporter, fleet.py, and a fixture in fleet_selfcheck.py -- no .yml at all)
```

And `tests/test_fleet_manifest.py` does **not** compare the committed artifact to a fresh build.
Its `TheManifestOnlyCarriesVerifiedBooks` class calls `EX.build(REPO)` and asserts properties of
*that fresh payload*; the one test that reads the committed file
(`test_a_root_with_no_markdown_finds_the_books_via_the_manifest`) asserts only
`len(got) >= 17` — which a stale manifest satisfies.

**BLAST RADIUS, and it is asymmetric.** For a book that **already has records**, drift is caught:
the chain anchors on the first row's `prev_hash`, so a changed `decl_sha` produces `CHAIN_BROKEN`
and the book refuses. For a book with **no records yet** — which is all eighteen today — drift is
silent: the book begins recording under whatever declaration the stale manifest carries, and the
repo's `DECL_*.md` says something else. Every row stamps its `decl_sha`, so the divergence is
*auditable after the fact*; it is not *detected*.

**FIX CLASS: CORRECTNESS.** One test: build the manifest and require it to equal the committed
bytes, exactly as the ledger's own regeneration check works. It fails loudly the moment a
declaration lands without a re-export, which is the only moment it matters.

---

### M6 — `write_pgpass`'s PERMISSION VERIFICATION IS UNREACHABLE ON THE ONLY PLATFORM THAT RUNS IT

`valuation/edge/wrds_client.py` promises, unconditionally: *"If the tightening cannot be
verified the file is REMOVED and the call raises, because a secret written somewhere loose is
worse than no secret written at all."*

The verification is:

```python
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    if os.name != "nt":
        mode = stat.S_IMODE(os.stat(p).st_mode)
        if mode & 0o077:
            os.remove(p)
            raise RuntimeError(...)
```

`pgpass_path()` returns `%APPDATA%\postgresql\pgpass.conf` **when `os.name == "nt"`**, and the
WRDS lane runs on Don's Windows box. So on the only platform where this code executes, the
`os.chmod` is a near-no-op (Windows honours only the read-only bit), the `except OSError: pass`
swallows any failure, and **the verification branch is structurally unreachable.** The file
inherits whatever ACL `%APPDATA%\postgresql` grants.

**BLAST RADIUS.** Real-world exposure on a single-user Windows profile is low — the directory is
under the user profile and `%APPDATA%` is not world-readable by default. **The defect is that
the guard's promise is false on the platform it runs on**, which is the `MB42` family exactly: a
guard whose only real execution is skipped. It is listed at MEDIUM for the claim, not for the
exposure.

**FIX CLASS: CORRECTNESS.** Either verify on Windows too (`icacls` or a `win32security` ACL read
behind a capability check), or — cheaper and honest — state the platform limit in the docstring
and return the verification status so a caller can see it was not performed. An unconditional
promise that cannot fire is worse than a stated gap.

---

### M7 — `connect()`'s DEADLINE BOUNDS THE CALLER AND NOT THE PROCESS

`wrds_client.connect()` exists to prevent one specific failure, stated in its own docstring:
*"`wrds.Connection` prompts on stdin when it cannot authenticate, and a prompt in a
non-interactive run waits forever — a blocked call that looks exactly like a working one from
outside. The chain harvest lost twelve hours to that shape once already."*

The implementation is `ThreadPoolExecutor(max_workers=1)` + `.result(timeout=timeout_s)` +
`shutdown(wait=False)`. `concurrent.futures.thread` registers a `_python_exit` hook that
**joins** its non-daemon workers at interpreter shutdown, and `shutdown(wait=False)` does not
detach them.

**MEASURED**, reproducing the exact shape with a worker that blocks the way a prompt does:

```
caller was released after 2.0s by the deadline -- as designed
worker still running: True
active threads: 2
TOTAL PROCESS WALL TIME: 60.1s  (deadline was 2s, worker sleeps 60s)
```

The deadline released the caller in 2.0 seconds and **the process took the worker's full 60.1
seconds to exit.** If `wrds.Connection` genuinely blocks on stdin, the worker never returns and
the process hangs at exit **forever** — having first printed a timeout error saying it did not.
That is arguably worse than the original: the twelve-hour hang now comes with a message
asserting it was bounded.

**BLAST RADIUS.** The WRDS lane is manual and attended, so a human notices. It matters because
the docstring's premise is non-interactive runs, and because `scripts/wrds_pull.py` calls
`W.connect()` inside its retry loop — up to `MAX_RECONNECTS + 1` times per chunk across dozens
of chunks, so a single poisoned auth can leave many hung workers.

**FIX CLASS: CORRECTNESS.** Run the connect in a **daemon thread** (or a subprocess with a hard
kill), so a hung worker cannot hold the interpreter open. A daemon thread is a two-line change
and makes the stated guarantee true.

---

## 4. LOW

### L1 — `fleet.record` SILENTLY DROPS A BOOK'S DECLARED EXTRA COLUMNS, DEFEATING `append_only`'s OWN DISCLOSURE

`append_only`'s module docstring, rule 3: *"A key on the incoming row that is in neither the
file nor `columns` is NOT written **and comes back in `ignored_fields` rather than being dropped
in silence.**"*

`fleet.record` filters first — `payload.update({k: v for k, v in (fields or {}).items() if k in
cols})` — so the extra key never reaches `append`, and `ignored_fields` comes back empty.
Neither `record_fill` nor `record_skip` passes `columns=`, so a book's declared `records_schema`
never reaches the writer at all.

**MEASURED:**

```
f1's declared records_schema: []
record_fill wrote: True
'my_declared_extra' in the written columns: False
returned ignored_fields: []
```

**Latent**: all eighteen declarations currently carry `records_schema: []`.
`validate_declaration` nonetheless accepts non-empty schemas and checks them for clashes with
`RECORD_COLUMNS`, so the feature is presented as supported and is not.

**FIX CLASS: CORRECTNESS.** Thread the declaration's `records_schema` into `record()` as
`columns=` from `record_fill`/`record_skip` (the gate result already carries the declaration),
and report anything still unmatched rather than dropping it.

---

### L2 — THE FLEET WORKFLOW STILL PRINTS A HARD-CODED CAUSE THAT THE CODE NOW MEASURES

`.github/workflows/fleet-cycle.yml`:

```yaml
grep -q '"breathing": *true' "$BODY" \
  || echo "::warning::fleet is DECLARED-BUT-NOT-BREATHING (no entry rule implemented)"
```

`fleet.cycle()` computes `not_breathing_reason` precisely because a guessed cause shipped and
was wrong in production — its own comment says so and anticipates *"a future one-line workflow
fix"*. That fix has not been made, so the annotation still asserts one cause for five possible
states (`NO_BOOKS_VISIBLE`, `NO_ENTRY_RULE_IMPLEMENTED`, `ALL_BOOKS_BLOCKED_AT_GATE:*`,
`NO_ARMED_BOOK_RAN`, and the empty string). **Given H1, the cause a reader will actually meet is
none of the ones printed.**

**FIX CLASS: CORRECTNESS.** One line: print `not_breathing_reason` from the body.

---

### L3 — THE GATES ARTIFACT IS 210 TO 303 DAYS STALE, HAS NO CONSUMER, AND NO DEFAULT STALENESS BAR

Measured from the shipped `data_export/fleet_gates.json` against today:

```
evt_clean    as_of 2025-10-27  age = 303 days   n=211   types={'bool': 211}
ma28_clean   as_of 2026-01-28  age = 210 days   n=2531  types={'bool': 2531}
optionable   as_of 2026-08-24  age =   2 days   n=487   types={'bool': 487}
```

`fleet_gates.gate()` **has no callers anywhere**:

```
$ grep -rn "fleet_gates\.|max_age_days" --include=*.py valuation/ scripts/
valuation/saas/app_saas.py:792:  _g = fleet_gates.coverage()
valuation/saas/app_saas.py:802:  res["image_audit"] = fleet_gates.image_audit()
   (no gate() call site)
```

`max_age_days` is optional with **no default**, which is the right call and is defended by
`MA5`'s frozen-bar lesson. The consequence is that whoever implements `F-4` or `F-10` must
remember to pass one against an artifact that will by then be a year old, and nothing forces it.
`coverage()` and `image_audit()` report `age_days` and no caller acts on it. Nothing regenerates
the artifact — it requires the licensed exports, so it can only be rebuilt by hand where they
live.

**Currently inert**, which is why this is LOW: the machinery was built ahead of its consumers,
which is the `I-3` pattern and is correct. **FIX CLASS: DECISION** — the register that
implements the first gate-consuming book should declare its own staleness bar, and until then
the honest move is to record the artifact's vintage in that book's declaration rather than to
invent a default here.

---

### L4 — THE HARNESS FINGERPRINT IS LINE-ENDING DEPENDENT, SO IT IS NOT A PORTABLE HARNESS IDENTITY

`harness_fingerprint()` hashes the source **bytes**. This repo runs `core.autocrlf=true` and
`.gitattributes` deliberately does not set `* text=auto`, so the working copy is CRLF and the
stored blob is LF. Measured:

```
core.autocrlf: true
fleet.py on disk       -> CRLF count: 1766  bare LF: 0
append_only.py on disk -> CRLF count:  167  bare LF: 0
```

The Linux image checks out LF, so the same commit yields a **different fingerprint** in the
image than on Windows. **It fails safe** — a self-check recorded on one platform reads `STALE`
on the other, which refuses rather than permits — and in practice both the recording and the
checking happen inside the image, so production is self-consistent. Recorded because the
fingerprint is documented as denoting *"a property of the CODE"* and it denotes a property of
the code *as checked out on a platform*.

**FIX CLASS: CORRECTNESS**, if taken at all: normalise line endings before hashing. The
`.gitattributes` route (`* text=auto`) is explicitly ruled out there for good reasons and should
stay ruled out.

---

### L5 — CLAUDE.md's "THIRTEEN TRIALS OF HEADROOM" IS NOW FOUR

`MB31`'s bullet states: *"the next draw to flip is seed 1003 at `margin/se` 3.319188, and it
flips when `sqrt(2 ln N)` exceeds that — i.e. at equity `N` = 247. **THIRTEEN TRIALS OF HEADROOM
FROM TODAY.**"*

Re-derived, and `MB31`'s arithmetic is exact:

```
MB31 says the next draw flips at margin/se 3.319188
re-derived: the FIRST equity N whose hurdle exceeds it is N = 247
   N=224  hurdle=3.2898772171
   N=234  hurdle=3.3031261300
   N=243  hurdle=3.3145320766     <- the LIVE equity N today
   N=247  hurdle=3.3194542734  FLIPS
```

Live `by_domain` reads `{'equity': 243, 'options': 310, 'unified': 0, 'infra': 20}`, so the
headroom is **four trials, not thirteen**, and at `N` = 247 the calibrated-floor table in
CLAUDE.md — six entries of which are stated as provably unmoved — requires the bounded
re-derivation that bullet describes.

**THE MACHINERY IS CORRECT AND THIS IS ONLY THE PROSE.** `valuation/web/research_record.py`
derives the number live and a test pins that it is derived rather than typed:

```
floor block: { "flip_n": 247, "n": 243, "headroom": 4, "due": false }
FLOOR_FLIP_MARGIN_OVER_SE = 3.3191884951841053
floor_flip_n() = 247
```

CLAUDE.md's own instruction already says *"Derive it; do not quote it from here."* Listed
because the audit was asked to spot-check load-bearing numbers, and this is the one that has
moved most.

**FIX CLASS: CORRECTNESS** — a one-word correction in place, on that file's usual convention.

---

### L6 — `wrds_client._env` HARD-CODES AN ABSOLUTE PATH TO THE PRIMARY CHECKOUT

```python
    if not os.path.exists(p):
        # the worktree has no .env; the main checkout does
        alt = os.path.join(r"C:\Users\donni\Downloads\valuation-tool", ".env")
        p = alt if os.path.exists(alt) else p
```

A worktree run silently reads credentials from outside the worktree, via a machine-specific
literal. It is deliberate and commented, it fails closed (`CredentialsMissing` names the absent
key and never a value), and `wrds_client` is not on the fleet path — so this is portability
housekeeping rather than a defect. Recorded because a hard-coded user path in a library module
is exactly the thing that will read as inexplicable to the next reader on a different machine.

---

### L7 — `DECL_testbook.md` SHIPS IN THE PRODUCTION DECLARATION MANIFEST AS AN EIGHTEENTH BOOK

The manifest carries eighteen books; seventeen are `F-*` research books with ledger rows, and
the eighteenth is `testbook` — the day-1 verification fixture. It is correctly built: `utility`
class, `trial.domain: "none"`, `concurrency_cap: 1`, SPY only, one order, and closed with a
zero-charge row in the session that declares it, so `validate_declaration`'s
`UTILITY_BOOK_CHARGES_A_TRIAL` refusal keeps it from ever charging anything.

It is listed because a test fixture is a member of the production declared set: it appears in
`declared_books()`, in `cycle()`'s per-book rows, and in `books_declared: 18` — a figure a
reader will compare against the seventeen ledger rows. Whether its `close` row exists on the
service is not observable from here.

**FIX CLASS: DECISION**, and the honest answer may well be to leave it exactly as it is — the
live leg has to run on a *declared* book to go through the gate rather than around it, which is
the whole design. A `closed` book being excluded from `cycle()`'s counts would be the smaller
change.

---

## 5. WHAT WAS CHECKED AND FOUND CLEAN

Listed so this audit can be told apart from one that stopped looking. Each was probed, not
assumed.

**DEPLOYMENT PARITY (Q1)**

- **Every env var the fleet path reads is declared in `render.yaml`.** The closure was derived
  by AST from the six real entry points (24 first-party modules) and swept for
  `os.getenv`/`os.environ`; the credentials the path actually needs — `TRADIER_PAPER_TOKEN`,
  `TRADIER_PAPER_ACCOUNT_ID`, `TRADIER_TOKEN` (for the distinctness refusal), `ADMIN_TOKEN`,
  `OPTIONS_TERM_FILTER` — are all present as `render.yaml` keys.
- **Every third-party package the closure imports is in the hash-pinned lock.** `numpy`,
  `pandas`, `requests`, `python-dotenv`, `yfinance` all pinned in
  `requirements-saas.lock.txt`, which the Dockerfile installs with `--require-hashes`.
- **`zoneinfo` works in the image.** `market_session.py` is the only closure member using it,
  and `tzdata==2026.3` is pinned in the lock — so the classic slim-image
  `ZoneInfoNotFoundError` cannot occur. This was the most likely remaining instance of the
  family and it is closed.
- **`git` is the only subprocess binary on the fleet path**, it is absent from the image, and
  every path that needs it is already fenced: `may_fill` takes the manifest branch,
  `declaration_commit` is unreachable, and `git_available()` is checked rather than assumed.
- **`data_export/` ships and both fleet artifacts are tracked.** `.dockerignore` does not
  exclude it; `git ls-files` confirms `fleet_declarations.json` and `fleet_gates.json` are
  tracked, so they exist in a clone-built image.
- **`scripts/` ships** (not excluded), and `scripts/fleet_selfcheck.py` imports nothing from
  `tests/` (which is excluded) — checked, because that would have been a fifth instance.
- **No licensed vendor data reaches the image.** `.dockerignore` excludes `data/` wholesale;
  `image_audit()` probes for five named licensed exports and censuses every gate value by type.
  The shipped artifact carries `{'bool': 211}`, `{'bool': 2531}`, `{'bool': 487}` — booleans
  only, no floats, no strings.
- **No public surface reaches IBES or WRDS content.** Nothing under `valuation/web/`,
  `valuation/saas/`, `valuation/screener/` or `valuation/engine/` imports `ibes_events`, and
  the `D:\wrds` fence is pinned by tests in `test_wrds_client.py` and `test_w14_census.py`.

**CAN THE RECORD LIE (Q2)**

- **The hash chain is correct for what it claims.** `_canonical` hashes the written cell rather
  than the passed-in value (the defect that made the chain unverifiable on its own first run is
  fixed); `verify_chain` reads the file's **own header**, so streams predating a column addition
  still verify; an empty stream is reported `vacuous: True` and never as a pass; the seq
  monotonicity check is enforced on read as well as on write.
- **`append_only`'s refusals are real and correctly ordered.** Idempotency is tested before the
  backward check (so a retry is a no-op rather than an error), a ragged file is refused rather
  than normalised, and the write is tmp + `fsync` + `os.replace`.
- **The fabricated-fill defect is genuinely closed.** `fill_fields` delegates to
  `PaperBroker.fill_price` rather than reading `avg_fill_price or price`, `_fate` reads the
  broker's status vocabulary rather than inferring from a present number, and `L9b` cross-checks
  the record against `exec_quantity`. The `0.0`-is-falsy trap cannot recur through this path.
- **`quote_mid` returns `None` on a one-sided quote and never falls back to `last`**, and
  `submit` prices arm B's limit from the same function that records the mid — so the two cannot
  drift.
- **`check_structure` refuses a naked short, a single leg, an unusable quote and a net credit
  under `debit_only`, and returns before the broker is touched** — so no partial structure can
  exist for the duration of an exception.
- **`submit`'s cancel is checked before the market leg is sent**, so a failed cancel returns
  `B-cancel-failed` rather than opening a double position.
- **`skip_fields` raises on an empty `skip_reason`** rather than recording an unexplained skip.
- **`fleet_aggregate` raises `NotImplementedError`** rather than returning a cross-book number a
  reader would quote.
- **`validate_declaration` collects refusals rather than raising serially**, tests **presence**
  rather than truthiness (so an empty `records_schema` is not mistaken for an unanswered field),
  requires `o11_sentence` verbatim, and requires `side` and `sells_premium` to **agree** rather
  than resolving a contradiction silently.
- **The S25 crosswalk's anti-drift guard is not vacuous.** `engine_sector_keys()` is genuinely
  compared in `tests/test_s25_sector_map.py:78`, and measured today the eleven crosswalk values
  and the eleven engine keys match exactly, both directions empty.
- **The `MB31` floor-flip trigger is derived, live and tested**, not typed — `floor_flip_n()`
  returns 247 from the recorded margin ratio through the one hurdle definition, and a test
  asserts the literal `247` does not appear in the module's code.

**IRREVERSIBILITY (Q3)**

- **The fleet records do land on a persistent disk.** `render.yaml` mounts a 1 GB disk at
  `/app/data`, so `data/fleet/` survives a redeploy. (What it does not survive is the disk
  itself — H3.)
- **`migrate_stream` is conservative and correct.** It migrates **only a pure widening** (the
  on-disk header must be an exact prefix of the current columns), **renames rather than
  deletes**, numbers the archive so it cannot overwrite a previous one, and states in its own
  return value that the chain is SPLIT rather than pretending continuity.
- **The `/admin/fleet-cycle` GET/POST split holds.** `run=1` on a GET returns 405 and touches
  nothing; the dry run computes the identical report and records nothing. The recorders and the
  self-check are both on the write path only.
- **The WRDS pull's resume discipline is sound.** Payload is written atomically **before** its
  manifest line is appended and fsynced; `needs_pull` re-does any unit whose payload is absent
  or whose size disagrees; `verify(full=True)` re-hashes; `_acquire_lock` fails closed against a
  second puller on the same product; and `reconcile()` compares the summed chunk rows against
  the server's own `count(*)` — the one check that can see rows that were never fetched, which
  is how the 102,213-row null-date hole was found.
- **The WRDS SQL has no injection surface**: `lib`/`table`/`year_col` come from a closed literal
  dict and the chunk key is `int()`-cast before interpolation.

**RECORD VERSUS TREE (Q4)**

- **Every load-bearing figure spot-checked reproduces exactly.** `top_decile_alpha`
  0.07174142332098163, `long_short_tstat` 2.8360640685320595, HAC 2.6199121240414884,
  `monotonicity` -0.8909090909090909, universe 2,531 names over 69 dates labelled `full`,
  Deflated Sharpe 0.7863213339664521 — all match CLAUDE.md to the digit.
- **The artifact's documented lag is real, benign and correctly signed.**
  `BACKTEST_RESULTS.json` stamps `equity 224 / options 292 / infra 14` against a live
  `243 / 310 / 20`. Per `MA21` the artifact may lag and may never lead, and it does not: the
  hurdle moves 3.2898772171 to 3.3145320766 and `clears_hlz_hurdle` is `false` at both, so **no
  claim changes side.**
- **`rows_malformed` and `rows_domain_unresolved` are both empty**, so the `M1-PARSE` pipe
  hazard and the `MA6` unattributed-domain hazard are currently clean.
- **The fleet's ledger rows are complete and carry real commits.** All seventeen `F-*` rows
  exist, none reads `PENDING` or `IN PROGRESS`, and `F-2` and `F-13` honestly record
  `ENTRY RULE REFUSED BACK` rather than a status that overstates them. The one status this
  audit disputes is `ARMED — entry rule IMPLEMENTED` on F-3 and F-8, which is true of a
  worktree and false of the service (H1).
- **The declaration manifest matches the tree today** — eighteen entries, zero `decl_sha`
  drift, zero parseable declarations missing — and the three prose `DECL_DRAFT_*` files are
  correctly **skipped with a reason** rather than silently dropped.

---

## 6. THREE CANDIDATE DEFECTS THAT TURNED OUT NOT TO BE ONES

Recorded because a hypothesis that dies on measurement is worth as much here as one that
survives, and because two of them are the sort of thing a future reader will re-suspect.

1. **"The `zoneinfo` call will raise on `python:3.11-slim`."** A real and common deployment
   defect, and the closure does reach `ZoneInfo(MARKET_TZ)`. **Refuted:** `tzdata==2026.3` is
   hash-pinned in `requirements-saas.lock.txt`. Nothing to fix.

2. **"Nothing watches the `N` = 247 calibrated-floor trigger, so it will pass unnoticed."**
   **Refuted:** `valuation/web/research_record.py` computes `floor.headroom` and `floor.due`
   from the live equity `N`, derived rather than typed, and `tests/test_record_this_week.py`
   pins both the derivation and the anti-typing rule. The readout is live and correct
   (`headroom: 4, due: false`). Only CLAUDE.md's prose is stale (L5).

3. **"`read_meter` will return an unrecorded verdict whenever the stream has an extra
   column."** Half right, and the first probe was wrong: widening a stream by one column does
   **not** trip `append_only`, because `fields` and `on_disk` compare equal after the union.
   The defect is real but reaches it by the *narrower*-header route (a stream predating a
   column addition), which is the documented `(C)` case. Corrected before writing up, and M2
   states the mechanism that actually fires rather than the one first suspected.

---

## 7. WHAT THIS AUDIT DOES NOT SAY

- **It does not say the harness is unsound.** The declaration gate, the ancestry proof against
  git, the manifest fallback with its explicit `evidence` grade, the append-only hash chain, the
  three-state self-check, the refusal-as-record discipline and the two-grade honesty about what
  the chain does and does not detect are **well built and mostly do exactly what they claim.**
  Seventeen findings against machinery of this size and this age is a good result, and thirteen
  of them are `CORRECTNESS`.
- **It does not audit the declarations' content.** Whether `F-3`'s entry rule is a good
  hypothesis, whether its horizon arithmetic is right, whether its sigma is a prior or a
  measurement — none of that was examined. This is an audit of the recorder, not of what it
  records.
- **It does not establish what the service currently holds.** No fleet records exist in either
  checkout (`data/` is gitignored), and the audit had no authenticated read of the live
  instance. Every claim about production behaviour is derived from the code plus an
  image-shaped fixture, and is labelled as such. **In particular, whether any book has ever
  been certified on the service, and whether the (D) series have begun accruing fabricated
  rows there, is not established here and should be the first thing checked.**
- **It proposes no research and unparks nothing.** No item below `DECISION` needs a register,
  and the three that do (H3's export door, L3's staleness bar, L7's test-book in the declared
  set) are design questions rather than hypotheses. Counted: thirteen `CORRECTNESS`, three
  `DECISION`, and `L6` is housekeeping carrying neither.

---

## 8. THE ONE THING TO CARRY FORWARD

**Every high-severity finding in this document is a seam between a component and the process
that runs it, and every one of them was invisible to a suite that is entirely green.** H1 is a
module resolving a fact for itself instead of calling the resolver built for it three days
earlier. H2 is a recorder given a default argument where it needed a refusal. H3 is a backup
that exists for one irreplaceable dataset and not for its twin. M1, M2 and M3 are each a guard
that reports success in a state it was written to catch.

The pattern is not "the code is wrong". It is that **a component tested in isolation and a
component wired into a runner are different objects, and this project keeps testing the first
and shipping the second.** The image audit in `fleet_gates.image_audit()` is the right answer to
this and it is the best thing in the week's work — it measures the deployed process *from
inside the deployed process*. The lesson of this audit is that its coverage should be widened
until it can answer H1 and H2 as well: **can each armed book actually resolve its declaration
here, and did each recorder's source actually get consulted today?** Both are one boolean, both
belong in the cycle's own response body, and both would have caught their finding on the first
dispatch.
