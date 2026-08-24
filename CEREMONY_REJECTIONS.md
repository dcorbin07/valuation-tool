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
