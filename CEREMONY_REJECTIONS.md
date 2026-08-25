# THE DECLARATION CEREMONY — THE THREE REJECTIONS, WITH REASONS

**2026-08-24, options-live lane (executor).** The scout drafted twenty fleet books and declined
to accept its own work. Seventeen were accepted and committed one file per commit. **Three are
REJECTED and returned here.** A rejection costs nothing and reverses nothing: the drafts stay on
disk as `DECL_DRAFT_f7_band_exit_calls.md`, `DECL_DRAFT_f9_flag_transition_puts.md` and
`DECL_DRAFT_f16_13f_surge.md`, unedited, and each reason below names what a revision would have
to change. **None of these is a finding that the hypothesis is wrong.** F-7 is a plumbing
problem, F-9 and F-16 are arithmetic.

---

## F-7 — COVERED CALLS ON BAND-EXITING NAMES — **REJECTED, and on a stronger ground than the runbook anticipated**

The runbook's own test is *"if that read requires touching the scoring path rather than a
published artifact, reject."* F-7 fails it, and it fails a prior one as well.

**1. THE STATE THE ENTRY RULE READS DOES NOT EXIST, ANYWHERE.** The rule enters *"every name the
shipped S14 band logic marks **pending-exit** (the live band state READ from the scoring path,
never recomputed here)."* Measured: `grep -rn "pending[_-]exit"` over every `.py`, `.md`, `.csv`
and `.json` in the tree returns **zero hits**. Nothing marks it, because nothing has the concept.

**2. AND IT IS NOT MERELY UNSTORED — THE BAND EMITS NO SUCH STATE BY CONSTRUCTION.**
`no_trade_band.band_select(comp, tickers, held, n_target, exit_rank)` returns **a list of names
to hold**. A name is in that list or it is not; **the decision and the exit are the same
instant.** There is no interval during which a name is held *and* marked for exit, which is
precisely the window F-7's structure needs — it wants to sell a call against a position the band
has condemned but not yet sold. To know at rebalance *t* that a name exits at *t+1* you need
*t+1*'s composite, which is the future. **So the literal reading of the entry rule is not a
plumbing gap; it is look-ahead.**

**3. THE ONE DEFENSIBLE READING IS REAL, AND IS STILL UNREADABLE FROM ANYTHING PUBLISHED.** There
*is* an observable state with a fair claim to the name: a held name sitting in the hysteresis
grace zone, `n_target <= rank < exit_rank` — kept only because it is already held, one it would
not be re-entered on merit. That is genuine, computable, and exactly the object F-7 is reaching
for. **But it needs the composite RANK, and the published book carries no rank.**
`data_export/paper_track_holdings.csv` has eight columns —
`ticker, weight, entry_date, entry_price, bench_entry_price, shares, order_id, note` — and not
one is a rank or a score. Reading it means reaching into the scoring path, which is the runbook's
reject condition verbatim.

**WHAT WOULD MAKE F-7 ACCEPTABLE — two changes, neither large.** (a) Re-write the entry rule on
the **grace-zone** definition above, which is a real state rather than a forward-looking one; and
(b) get the composite rank into a published artifact — one more column on the holdings export —
so the entry is a read and not a recomputation. **Do (b) first**: until the rank is published the
book cannot prove at fill time which names qualified, and a declaration whose entry rule cannot
be evidenced is exactly what the harness exists to refuse.

**CONTRAST, so this does not read as a general hostility to state-dependent books.** Two of the
seventeen accepted books were checked against the identical test and **passed it**, which is what
makes F-7's failure specific rather than categorical. **F-8** enters on names *"newly entering"*
the book — and `entry_date` is a published column, so the state is a row in a shipped CSV.
**F-11** enters on dip-screen REJECTS — and the classifier is the screen's own published
`valuation.web.dip.health_check` / `dip.clamp_drawdown`, run on the same rows the live screen
uses; only `screen()`'s aggregation discards the failures. **The classifier exists and is
published. F-7's `pending_exit` is the one that is neither.**

---

## F-9 — FLAG-TRANSITION PUTS — **REJECTED ON HORIZON: 11.5 YEARS**

The draft is admirably honest — it heads its own horizon section *"the honest number"* and warns
the book runs **2–4 transitions per quarter**, i.e. about **one fill a month**. The problem is the
number it pairs that rate with. **"30 fills" is not derived from anything.**

Derived from the anytime-valid boundary this book's own declaration commits to
(`track_meter.boundary`, rho 3.0, alpha 0.05), at the book's own declared **MEI +25pp/trade** and
at **sigma 92.51pp — MEASURED, not assumed** (`O12` reports this project's own options book at
per-trade sd 0.9251):

| | draft | derived |
|---|---|---|
| fills needed | 30 | **138** |
| at ~1 fill/month | ~12 months | **11.5 YEARS** |

**The draft's round 30 understates its own requirement by 4.6×.** A book that cannot return a
verdict inside five years is not a forward test; it is a filing cabinet, and it would sit in the
fleet consuming a declaration slot and a runner cycle while never reaching a read.

**WHAT WOULD MAKE F-9 ACCEPTABLE.** To resolve inside five years at one fill a month (60 fills)
the minimum effect of interest would have to be **>= +36.8pp/trade**. That is a defensible bar for
a deep-OTM put book that bleeds by default — but it is a **different declaration**, and raising an
MEI is a decision to make in writing beforehand, never after seeing a horizon one dislikes. The
alternative is to widen the entry so the rate rises; **note that widening toward standing-flag
names is void by F-9's own terms** (that is `O-1`'s question), so the widening has to come from
somewhere else.

**WHAT IS NOT SAID: MA28's 3.04× is untouched.** It is measured, it replicates in both halves,
and it survived the size control that killed three sibling items. The transition-moment
hypothesis is live and interesting. **It is the SPEED of this particular expression that fails.**

---

## F-16 — 13F BREADTH-SURGE CALLS — **REJECTED ON HORIZON: 21 YEARS**

The runbook pre-authorises this one by name. The draft calls itself *"the fleet's slowest, said
plainly"* and fixes its own rate by construction: **5 fills per quarter, one shot per quarter, no
mid-quarter entries ever.** That is 1.67 fills a month and it cannot be raised without voiding
the book's own rule.

At the declared **MEI +15pp/trade** and the same MEASURED sigma 92.51:

| | draft | derived |
|---|---|---|
| fills needed | 30 | **420** |
| at 5/quarter | ~6 quarters | **21 YEARS** |

**Understated by 14×** — the largest gap between a draft's stated horizon and its real one
anywhere in the twenty. The draft's care here is genuine and it is aimed at the wrong risk: it
froze the horizon *"so nobody reads a year-and-a-half book at six months"*, when the book is not
a year-and-a-half book.

**WHAT WOULD MAKE F-16 ACCEPTABLE.** Resolving inside five years (100 fills) needs
**MEI >= +29.0pp/trade**. Or the entry has to stop being once-a-quarter — but the once-a-quarter
rule is what makes it a clean event study, so that is a different book rather than a wider one.

**AND A CAUTION FOR WHOEVER REVISES IT.** The nearest thing this project has measured is `E-1`,
which found a flat aggregate of institutional-conviction signals reading **0.6114 against the
`size` theme** and withdrawing before its arm ran. `S8` separately found `days_since_13f` had no
cross-sectional variation at all. Neither kills the surge-EVENT hypothesis — the scout is right
that an event is a different object from a weighting — but **a revision should carry a costume
kill against `size` in its declaration**, because a holder-count surge is a plausible size proxy
and this fleet has been fooled by that family before.

---

## HOW TO READ THE THREE TOGETHER

**None is a verdict about a hypothesis and no trial is charged for any of them** — the harness
charges at first verdict read, and none of these three will ever have one. Seventeen of twenty is
a high acceptance rate for adversarial review, and the drafts earned it: the two horizon
rejections were both **self-declared as slow by the scout**, which is exactly the disclosure that
made them checkable. The failure mode they share is not carelessness, it is that **"30 fills" was
carried across all twenty drafts as a convention rather than derived per book** — and it is wrong
by 3× to 40× everywhere it appears, **including in books that were accepted**. Every accepted
declaration now carries a `fills_needed` derived from its own boundary, its own MEI and its own
sigma. **A round number is not a horizon.**

---

## F-13 (THE SECOND EVENT) — REFUSED BACK AT ARMING, 2026-08-24, options-live lane

**Refused during implementation rather than at the ceremony, and the ceremony was right to
accept it.** Its declaration is well-formed, its horizon is derived, its verdict grammar is
complete — it passed every check the harness can make against a declaration. **What it cannot
survive is being written as code**, and that is a category of defect a validator cannot reach:
the rule is internally consistent and names a source that cannot supply what it asks for.

### THE FROZEN RULE ASKS THE I-4 SPINE FOR A DATE THE SPINE CANNOT HOLD

> *"Each session: names whose earnings event #1 occurred EXACTLY 5 sessions ago **AND whose
> event #2 date is KNOWN from the I-4 spine**. Both dates known or no entry; **cadence
> inference is BANNED**."*

**Event #2 is in the future. The I-4 spine is a record of filings that have HAPPENED.**
`EventSpine.build` reads `bulk.prepare_events` over the Sharadar EVENTS export, whose rows are
dated observations of code-22 filings. **Measured on the real file: 385,426 code-22 rows, and
the latest is 2026-07-29 — there is not one date in the future, on any code, anywhere in the
file.** A forward earnings calendar is a different product from a filing history, and this
project owns the second.

**AND THE RULE ITSELF CLOSES THE ONLY DOOR OUT.** The one way to derive a forward earnings
date from a backward filing record is to infer it from the name's reporting cadence — which
the declaration **bans by name**, correctly, because a cadence guess dressed as a KNOWN date
is exactly the fail-open this book's `"both dates known or no entry"` clause exists to
prevent.

**So the entry condition can never be satisfied. Not "is not satisfied today" — cannot be, by
construction.** An implementation would be a rule that provably returns `[]` forever while
reporting itself as a market observation, which is the precise blur `ARMED_NO_ENTRY_RULE` was
built to prevent one level up.

### WHY THIS WAS NOT VISIBLE AT THE CEREMONY

The ceremony validated declarations. **A declaration cannot state that its named source is
capable of answering it**, and no machine check the harness owns could have caught this: the
spine EXISTS, it is IMPORTABLE, it has an `is_known` method, and `is_known` returns `True` for
thousands of names. It answers a different question — *"do we have any history for this
name"* — and answering it truthfully is what makes the gap invisible.

**The portable half: a declaration that names a data source should name the FIELD and its
DIRECTION IN TIME.** *"Known from the I-4 spine"* reads as satisfied because the spine knows
things. *"A scheduled future date from the I-4 spine"* would have failed on sight.

### WHAT A REVISION HAS TO MOVE, and there are three routes

1. **Name a forward source.** `valuation/edge/catalyst_calendar.py` (S3-I2) is a live scraper
   of forward-dated events and is already the source F-14 uses — but its one reachable source
   is **PDUFA/FDA decision dates, not earnings**, so it does not answer this book as written.
   A forward earnings calendar would be a new dependency with its own licence question.
2. **Permit cadence inference under a stated, frozen rule** — and then say what happens when
   the inference is wrong, because the whole point of the ban was that a wrong guess enters a
   position the book believes is event-free.
3. **Drop the event-#2 condition** and declare the book on event #1 alone. That is a
   materially different hypothesis and needs its own horizon, not an edit to this one.

**Route 3 is the cheapest and the most honest; it is also a different book.** This lane is not
choosing — the drafts are the scout's.

### NOT REFUSED FOR THIS, and worth separating

**F-13's horizon is the fleet's second shortest (0.88 years, 420 fills at 40/month).** Nothing
about the refusal is a judgement on the hypothesis, which is untested and interesting. It is
refused on the mechanics of one clause.

### WHAT IS REFUSED IS THE ENTRY RULE, NOT THE BOOK — and the distinction is not pedantry

**F-13 is DECLARED. It is not a draft.** F-7, F-9 and F-16 were refused *before* acceptance
and their `DECL_DRAFT_*` files never became declarations; F-13's did, at `6bab2d4`, committed
alone. **That commit is tamper-evidence and it is not being undone.** Renaming the file back
to a draft would rewrite the ceremony's own record and destroy the `--diff-filter=A` evidence
that this declaration predates every line of fleet code — which is the whole reason the
ceremony committed things alone.

**So the accurate state is: DECLARED, ENTRY RULE REFUSED AS UNIMPLEMENTABLE.** The file stays
exactly as it is, its ledger row stays `DECLARED - no verdict`, no trial is charged, no meter
exists and nothing is retracted. **What the book needs is a dated AMENDMENT from the scout —
in the file, below the rule, on `PT-AMEND1`'s terms — and it must land before F-13's first
fill**, because `verify_chain` anchors on the declaration's content hash and an amendment
after records exist breaks the book's own chain at row 0. F-13 has zero records, so that
amendment is free today.

---

## F-2 (THE MENU GATE) — ENTRY RULE REFUSED BACK AT ARMING, 2026-08-24, options-live lane

**Refused on a PREMISE ERROR that is checkable line by line, not on a judgement.** F-2's
entry rule claims to reproduce a shipped function *"verbatim"* and then describes something
that function does not do. The sentence is self-contradictory, and the contradiction is
material because the menu COUNT is what the gate's `< 4` threshold is measured against — two
different menus give two different counts and therefore two different refusal sets.

> *"compute the host entry's fillable in-band menu by **MB1's shipped prefilter verbatim**
> (side-matched right -> DTE band **+/-25% of target** -> moneyness **0.85-1.15** -> two-sided
> usable quotes -> volume > 0)"*

**The prefilter it names is `scripts/mb1_alternatives_menu.py::build_menu`**, whose own
docstring says *"`pick_contract`'s prefilter, VERBATIM, minus the final argmin ... Removing
the fallback would make this a different menu from the engine's, which is a void condition of
the register."* Read against it, the parenthetical diverges FIVE ways:

1. **THE MONEYNESS BAND IS NOT 0.85-1.15, AND IT IS SIDE-DEPENDENT.** `build_menu` uses
   **(0.90, 1.20) for calls and (0.80, 1.10) for puts**. F-2's band is neither, and being
   side-independent it cannot be either.
2. **THE MONEYNESS FILTER IS NOT BINDING IN THE ORIGINAL.** `build_menu` carries an explicit
   fallback — `if len(near) == 0: near = d` — kept deliberately, and called out in its own
   docstring as load-bearing. F-2 presents moneyness as a filter; in the shipped prefilter it
   is a preference that yields entirely when it would empty the set. **A gate that drops the
   fallback refuses names the engine would happily trade.**
3. **THE DTE BAND IS FIXED, NOT RELATIVE TO THE HOST'S TARGET — AND THIS ONE BREAKS A REAL
   HOST.** `build_menu` takes `OB.DTE_RANGE`, which is the constant `(45, 75)`, commented
   `_DTE["swing"]`. For a 60-DTE host that happens to equal +/-25% of target, which is
   presumably where the phrasing came from. **For F-11, whose declared structure is `dte: 91,
   "nearest above 91"`, the fixed band EXCLUDES ITS OWN CONTRACT ENTIRELY** — the gate would
   compute a menu that cannot contain the entry it is judging and refuse every F-11 order, not
   because the menu is thin but because it was built on the wrong tenor. A fleet-wide gate
   must be tenor-relative or it is a swing-only gate wearing a fleet-wide name.
4. **A SOLVABLE DELTA IS REQUIRED AND IS NOT MENTIONED.** `build_menu` runs `enrich_chain`
   then `dropna(subset=["delta"])`, so a contract whose IV will not solve is off the menu.
   **That is in direct tension with the books this gate would host:** F-3's and F-11's
   structures are moneyness-fixed and F-3's void condition is *"delta-targeted strikes"*,
   honouring `V6-OPT`'s autopsy. A gate that silently requires the delta machinery those books
   declined is not a neutral breadth check.
5. **"TWO-SIDED USABLE QUOTES -> VOLUME > 0" UNDER-DESCRIBES `quote_reject_reason`**, which
   also rejects `locked` (bid == ask), `thin_premium` (below `MIN_PREMIUM`) and `wide_spread`
   (above `MAX_SPREAD_PCT`). Those are the filters that actually bite on a thin chain, so the
   description omits most of what makes the count small.

### AND A SIXTH, STRUCTURAL RATHER THAN NUMERICAL

**`build_menu` is in `scripts/`, and `valuation/` may not import it.** `MA23`'s boundary test
forbids a product module importing a study, and the direction here is worse — a package
importing a runner. It also operates on a **pandas frame with columns `right` / `expiration` /
`strike`**, while a live Tradier chain is a **list of dicts with `option_type` /
`expiration_date` / `strike`**. So *"verbatim"* is not available even in principle without an
adapter, and the moment an adapter exists the claim needs re-verifying rather than asserting.

### WHY THIS MATTERS EVEN THOUGH THE GATE IS INERT TODAY

**No book in the fleet has opted in.** `gates:` appears in ZERO of the seventeen declarations,
so F-2 refuses nothing today whatever it is implemented to do. **It is refused anyway, because
the moment a host opts in the gate becomes load-bearing on that host's every entry** — and
the opt-in is a one-line declaration amendment that someone will make without re-reading this.
A defect that is harmless until it is suddenly decisive is worth fixing while it is harmless.

### WHAT A REVISION HAS TO MOVE

**Pick one and say which:** (a) *the shipped prefilter*, in which case delete the parenthetical
and accept the fallback, the side-dependent bands, the fixed swing tenor and the delta
requirement, and say what happens to non-swing hosts; or (b) *this parenthetical as its own
frozen spec*, in which case drop the word "verbatim", drop the claim of lineage to MB1, and
state the band, the fallback behaviour and the tenor rule in F-2's own terms. **(b) is
cleaner and this lane recommends it** — the gate's hypothesis is about menu BREADTH, which
does not need the engine's exact argmin prefilter to be meaningful. Either way the DTE rule
must be relative to the host's declared target, or the gate must declare itself swing-only.

**`DECL_f2_menu_gate.md` STAYS ON DISK, unedited, and the book stays DECLARED** — the same
treatment as F-13. Its commit is tamper-evidence; the fix is a dated amendment below the
rule, and it must land before F-2's first fill because `verify_chain` anchors on the
declaration's content hash. F-2 has zero records. No trial is charged and nothing is retracted.
