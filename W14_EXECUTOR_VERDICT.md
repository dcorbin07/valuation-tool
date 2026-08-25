# W-14 — CBOE OPEN-CLOSE: **REJECTED AT THE CENSUS GATE, VOID(K3). ZERO TRIALS.**

**Executor: options-bot lane, 2026-08-25.** Draft: `PREREG_DRAFT_w14_cboe_openclose.md` (Frontier
Scout, 2026-08-24). **No register was committed. No arm ran. No hypothesis was scored against any
bar.** Options `N` stays **308**, equity 242, infra 20 — `by_domain` bit-identical across the log
append, `rows_fixed_not_counted` **77 → 78**, which is the proof the row was seen and correctly
excluded (`MB15`'s and `S25`'s precedent, both of which closed a data question at zero trials).

---

## 0. THE VERDICT IN ONE LINE

**The draft's central premise is false on this grant.** It reads *"`D4` priced this data at
$500/mo and declined it; WRDS makes it free."* **WRDS does not carry it at all** — not under any
name, in any of the 221 libraries this login can see. The draft's own **K3, the identification
kill, fires**, and the scout called that in advance: *"This is the one most likely to fire; it is
written first for that reason."*

**The draft is REJECTED AS WRITTEN and its reasoning is largely ACCEPTED.** Those are different
things and both are recorded, because the argument that survives is the reusable part.

---

## 1. WHAT WAS MEASURED, AND WHY THE EXISTING CENSUS COULD NOT ANSWER IT

The draft is census-gated in its own words — *"nothing below runs until `WRDS_CENSUS.md` confirms
the product, fields and span."* **`WRDS_CENSUS.md` does not confirm it, and it does not deny it
either.** That census probed the OptionMetrics-**replacement** shape — `optprice_2010`,
`optprice_2016`, `ivlisted_2010`, `eqmaster`, `optcontract`, `wrds_eq_opt_merged` — and found every
one `permission denied`. **It never probed open-close.** A denial of six optprice-shaped tables is
real evidence about the `cboe` grant and is **not a measurement of this product**, which is that
census's own stated lesson one level down: *"a census that probes the names in a brief measures the
brief."*

So the gate was measured directly, read-only and schema-only, with no licensed row materialised.

**(a) THE PRODUCT DOES NOT EXIST HERE.** Account-wide search of `information_schema.tables` for
`opencl` / `open_close` / `openclose`: **0 candidates**. The four Cboe-shaped libraries are
`cboe` (90 tables), `cboe_all` (1), `cboe_sample` (7), `cboesamp` (7), and enumerating every table
name in them shows what the library actually is: **the IvyDB/OptionMetrics-lineage schema** —
`optprice_1998…2026`, `ivlisted_1998…2026`, `optcontract`, `optdeliv`, `eqmaster`, `eqprice`,
`ivborrowrate`, `wrds_eq_opt_merged`. Contract-level prices and implied vols. **There is no
volume-by-origin table.**

**(b) THE ONLY OPTIONS VOLUME AVAILABLE CARRIES NO ORIGIN, WHICH IS K3'S EXACT FAILURE
CONDITION.** `cboe_sample.optprice` reads, at 12 columns: `optid, date_, exch, close_, high, low,
open_, volume, bid, ask, openint, _rowid`. **`volume` and `openint` are totals.** K3 requires the
product to *"separate customer from firm/market-maker opening volume"*; nothing here separates
anything. (`open_` is the session's opening **price**, not opening volume — a name that would read
as a hit to a grep and is not one.)

**(c) NO TABLE ANYWHERE ON THE ACCOUNT CARRIES THE SPLIT.** Column-level search across all 221
libraries for `customer|firm|market.?maker|professional|retail|origin` returns **4,863 columns over
2,719 tables**, and the tables carrying **both** a customer-ish and a firm-ish column number
**six** — all of them Bureau van Dijk corporate registries (`main_customers` against
`confirmation_dates`), i.e. false positives on the substring `firm`. A second, independent search
for columns naming opening volume (`open.?buy|open.?sell|opening|buy.?open|sell.?open`) returns
**3 columns in 3 tables**, all `audit.feed59_bank_holding_company`. **Nothing on this grant
identifies who opened an option position.**

**(d) AND THE `cboe` PRODUCTION TABLES ARE DENIED ANYWAY**, re-confirmed here rather than quoted:
`cboe.optprice_2020`, `cboe.optcontract` and `cboe.eqmaster` all return
`psycopg2.errors.InsufficientPrivilege: permission denied`. So even had the product been in that
library, the grant would not read it. **Two independent reasons, and the first is sufficient.**

---

## 2. A CORRECTION TO `WRDS_CENSUS.md`, FOUND ON THE WAY AND REPORTED RATHER THAN EDITED

That census states: *"Searched all **221** visible library names: **Intraday Indicators by WRDS**
and **Historical SPDJI** are not present. Reported as measured rather than as concluded — a name I
cannot find is weaker evidence than a table that returns `permission denied`, and the honest state
is ABSENT-ON-THIS-LOGIN rather than proven unavailable."*

**Measured: Intraday Indicators IS PRESENT, and it returns `permission denied` — the stronger
evidence that census said it lacked.** It is not a library. It is a set of **tables**:
`taqm_2003.wrds_iid_2003` … `taqm_2013.wrds_iid_2013` and onward, plus
`form_metadata.wrdsapps_all_iid_ms_orderflow`, **94 tables carrying a `retail` column**, 13 retail
columns each — `buyvol_retail`, `avg_buy_price_retail`, `bs_ratio_retail_vol`, `buynumtrades_retail`
and siblings, which is the Boehmer–Jones–Zhang–Zhang retail order-imbalance shape.

**Its conclusion stands and its reason changes**, and the failure mode is the census's own: **it
searched LIBRARY names for a product that lives in TABLE names.** `B13`/`S7`'s consequence is
untouched — the data is still unreadable, so the CRSP `dsf` route for a $ADV remains the answer.
**Not edited here** — it is the data lane's file, and a factual correction to a shared census that
other registers gate on should be applied by its owner rather than by a passing reader.

**AND IT SHARPENS W-14's OWN EPITAPH: a retail identifier does exist on this account. It is on the
EQUITY tape, not the options tape, and it is denied.**

---

## 3. THE GRAVEYARD ARGUMENTS, ASSESSED ONE BY ONE

The brief asked for these to be argued properly rather than gestured at. **Three of the four
survive the rejection and are the part worth keeping.**

**`MB15` — and why open/close is genuinely a different axis, not the same one renamed.** `MB15`
died on **identification**: in options there is no off-exchange execution at all, so the equities
venue identifier has no analogue, and it measured **zero TRF prints in 70,288,482**. Its named
successor axis is **condition + size** — the OPRA single-leg-auction flag plus small trade size,
Bryzgalova–Pavlova–Sikorskaya's SLIM proxy. **Open/close is a different axis and the draft is right
about that:** condition+size is a **trade-level inference** from our own tape about whether a print
*looks* retail, while open/close is a **venue-published aggregate of position-opening intent** —
who is opening versus closing, reported by the exchange rather than inferred by us. One is an
inference we make; the other is a fact the venue publishes. **The distinction is real and it does
not save the item, because the fact the venue publishes is not on this grant.**
**AND THE COMPARISON CUTS THE OTHER WAY TOO:** `MB15`'s successor axis **is** buildable — the
condition and size fields are in our own tick cache — but that cache is **alert-days-only**, so it
inherits precisely the conditioning defect W-14 was invented to escape. **Neither route currently
gives an unconditioned retail identifier on options.**

**`MB16` and `O14`'s six null flow features — the conditioning argument SURVIVES INTACT.** All six
(`sweep_share`, VPIN, `unusual_volume`, `signed_volume`, `block_share`, `pc_flow_imbalance`) were
computed on the alert-day tick cache — 3,884 units, 186 symbols — selected by our own screen, which
`MB15`'s scope note calls *"selected toward the retail-heavy tail… does not generalise to ordinary
days."* **A full-market unconditioned test of flow has never been run on this project**, and the
six NULLs genuinely do not settle it. That is the strongest sentence in the draft and it is
**accepted and preserved for a successor**; it simply has no data to run on.

**`R2` — accepted, and it must travel with any successor.** The alert entry loses to random entry
by **−5.0640pp/trade**, so a full-market flow signal would be a signal **for a book that does not
yet exist**, and the draft says so. Nothing here reopens it.

**`MB12` / structural orthogonality — correctly declined as a motivation.** The draft leans on a
**mechanism** (retail opening flow is uninformed on average) rather than on novelty, which is the
right shape after five items died motivated by orthogonality alone.

---

## 4. POWER, AT BOTH VOCABULARIES, BEFORE ANY FLOOR — AND THE DRAFT'S OWN REFERENCE NUMBER IS
COMPUTED AT A RETIRED BAR

The brief required this ahead of any floor, and it exposes a defect in the draft independent of
the census.

Today: options `N` **308**, hurdle **3.3853**; equity `N` **242**, hurdle **3.3133**. The
80%-power multiplier is **4.2253** (options) and **4.1533** (equity), i.e. **1.2481×** and
**1.2535×** the 50%-power figure.

The draft's §4 fixes the number a successor must beat as *"`MB16`'s banked SE 0.04817 → a 50%-power
MDE of +9.64pp against an observed 8.35pp."* **That +9.64pp is `2.0 × 0.04817` — the RETIRED 2.0
convention.** At this project's own hurdle the same SE gives a **50%-power MDE of +16.31pp** and an
**80%-power MDE of +20.35pp**, and **power against MB16's own observed 8.35pp is 4.93%.** So the
design the draft holds up as the one to beat is **worse than the draft says by roughly a factor of
two**, and a successor inheriting that reference would set its floor at half the required size.
**This is `MB22`'s vocabulary correction landing on a live draft** — the same error the record has
now paid for in `S19`, `V2G` and `V6`.

**What a successor would actually need**, on the draft's own premise that a full-market monthly
panel shrinks the per-month SE (SE scales roughly as 1/√names-per-month, against the alert cache's
**median of 2 names per date**): to detect a **3.00pp** long-short effect at **80% power** against
the options hurdle requires **≈5,293 months** at MB16's SE, **≈1,323** at SE/2, **≈588** at SE/3
and **≈212 months — 17.7 years — at SE/5.** **So even a 25-fold larger cross-section per month
needs nearly two decades of full-market data**, which is a real constraint on any revival and is
knowable now, before anyone buys anything.

---

## 5. WHAT WOULD RE-OPEN IT, CHECKABLE RATHER THAN ASPIRATIONAL

1. **A grant that actually reads the product.** The Cboe **Open-Close Volume Summary** is sold
   through Cboe DataShop/LiveVol and is not the WRDS `cboe` library, which is IvyDB-lineage. This
   is `D4`'s **$500/mo purchase question, undissolved** — the draft's belief that entitlement
   dissolved it is the one thing measured false here.
2. **`taqm_YYYY.wrds_iid_YYYY` becoming readable**, which would give an unconditioned **equity**
   retail identifier — not this hypothesis, but the nearest live one, and it is a **subscription
   question for Don**, the same class as the `cboe` page-versus-grant disagreement that census
   already routed to him.
3. **The `MB15` condition+size successor**, which is buildable today and inherits the alert-day
   conditioning defect — so it answers a **narrower** question than W-14 asked and must say so.

**None of the three is proposed here.** Each needs its own blind register and its own trials.

---

## 6. WHAT THIS DOES NOT SAY

**It is not a finding that retail opening flow carries no information.** No arm ran; the hypothesis
is **untested, not rejected**, and the draft's mechanism claim is the literature's and is untouched.
It is not a finding about `MB16`'s six NULLs either — the conditioning critique of those stands and
is strengthened by being written down. And **it is not a claim that WRDS lacks retail-flow data**:
it has it, for equities, and cannot read it.

**Trials: ZERO.** Nothing was measured against a bar; this is a fact about what a data grant
contains, which is the `S25` (`UNOBTAINABLE-WITHOUT-NEW-DATA`) and `MB15` (kill fired pre-arm)
precedent. **The scout's proposed 2 options trials are NOT charged**, and the counter question the
draft flagged for the executor — equity or options — is **moot and deliberately left undecided**,
since deciding it would imply an arm that will not run.

`scripts/w14_census.py`; `data/free_analysis/W14_CENSUS.json`, `W14_CENSUS_COLUMNS.json`,
`W14_RETAIL_IDENTIFIER.json`.
