# PREREG_DRAFT_contract_amendment_2.md — proposed Amendment 2 to `PAPER_TRACK_CONTRACT.md`

**STATUS: ACCEPTED BY DON 2026-10-04 — IN FORCE AS AMENDMENT 2. See
`PAPER_TRACK_CONTRACT.md` §5a-2.** All three parts below were moved into the contract unchanged:
(a) two rows in §5's register, (b) the corrected power paragraph appended to §2, and (c) the
corporate-action rule appended to §5a. **This file is KEPT, not deleted**, as the record of what
was proposed and when — which is the point of drafting an amendment rather than editing a signed
document.

> **ITS ORIGINAL STATUS LINE, PRESERVED because the acceptance is only legible beside what was
> offered:** *"STATUS: DRAFT. NOTHING HERE IS IN FORCE. The signed contract is not edited by the
> change that produced this file. This is the correction written down for Don to accept or
> decline, in the form §5a's Amendment 1 established: recorded openly, nothing above it
> deleted."*

**ONE THING THE ACCEPTANCE DID NOT CHANGE: §3's PROPOSED TEXT IS NOW THE CONTRACT'S TEXT, so read
the contract rather than this file for what is in force.** Where the two could ever disagree the
contract governs; this file is history. The draft's own `<date>` placeholder in (a) resolved to
**2026-10-04**, and its (b) paragraph is dated by the ACCEPTANCE (2026-10-04) rather than by the
drafting (2026-10-03) — the measurement it rests on is still `INDEX-BOOK`, 2026-10-02.

**WHAT IT IS ABOUT.** §2's power arithmetic — the sentence that says 60 months runs at 49% power —
rests on an edge figure that is **the wrong book and gross**. `INDEX-BOOK` (r1, 2026-10-02,
`ceffd04`) measured the book the Index actually serves, and the input changes by a factor of five.

**WHAT IT IS NOT.** It is not a proposal to retune the meter. σ **may never be revised downward**
(the contract's own rule: at 1.5× the assumed volatility the false-crossing rate is 20%), and
`INDEX-BOOK`'s own handoff says in terms that its figures are *"an input for Don, not an edit"*.
Nothing below asks for a lower σ or an easier bar.

---

## 1. THE DEFECT, IN ONE TABLE

Each arm scored at **its own** measured tracking error, because `MB8`'s rule is that an `se` may
not be borrowed across constructions — pairing one book's edge with another's denominator is the
recurring defect this project has already paid for.

| | net edge vs SPY | own tracking error (pp/yr) | months to detect | years |
|---|---|---|---|---|
| **in use in §2 today** | **+9.9864pp** — all-cap decile, **GROSS** | 11.40 (hard-coded) | 242 | 20.2 |
| the all-cap decile, NET | +8.0564pp | 11.3878 | 385 | 32.1 |
| **the book the Index SERVES** | **+1.9488pp** | **8.4381** | **4,383** | **365** |

**The figure in use is wrong twice over: wrong book, and gross rather than net.**

A free corroboration that these are the right objects: the all-cap arm's measured tracking error
comes back **11.3878 pp/yr** against the contract's hard-coded **11.40**, reproducing σ from
scratch by a different route.

## 2. WHAT THIS DOES AND DOES NOT CHANGE ABOUT THE TEST

**It does not weaken the contract.** Every threshold, the 6-month operational gate, the 60-month
verdict horizon and the meter's constants are unchanged by this draft.

**It changes what a null MEANS, and that is the whole point.** §2 already says a 60-month test
sits at 49% power against the figure it uses. On the served book the honest statement is stronger:

> The five-year forward test **can** show whether the Index is being recorded honestly, and
> whether its costs and turnover behave as modelled. It **cannot** show whether the Index beats
> SPY — no five-year result, in either direction, would settle that.

That sentence is already live on the Index tab, sourced from
`screener/index_book_measured.power_sentence()` so the page and this draft cannot drift apart.

## 3. PROPOSED TEXT

Three changes, all additive. Nothing is deleted and nothing above §5a moves. **(c) was added 2026-10-03** on Don's ruling of 2026-10-02; the count is corrected here rather than left reading "two", because a section that miscounts its own parts is the first thing a signer notices and the last thing they should have to check.

**(a) A new row in §5a's amendment table**, in Amendment 1's own form:

| | |
|---|---|
| **Amended** | **Amendment 2, <date> — see §5a.** §2's power input corrected to the served book |
| **What changed** | the edge and tracking error §2's arithmetic uses; **no threshold, no clock, no σ** |

**(b) A paragraph appended to §2**, after its existing arithmetic:

> **CORRECTED 2026-10-03 (Amendment 2).** The +9.9864pp used above is the full-universe
> equal-weighted decile's edge, measured GROSS. That is not the book this contract tracks.
> `INDEX-BOOK` measured the served construction — the $10B large-cap tier, score-weighted, 8%
> cap, 0.30 no-trade band — at **+1.9488pp net vs SPY** with its own tracking error of **8.4381
> pp/yr**, which requires about **4,383 months**. σ is NOT revised: it stays at 11.40 by the
> rule above, and the arm-specific figure is reported beside it rather than substituted for it.
> **Consequence:** the 60-month verdict can settle whether the Index is recorded honestly and
> whether its costs behave; it cannot settle whether the Index beats SPY.

**(c) A paragraph appended to §5a**, stating the corporate-action rule. Don's ruling of
2026-10-02, recorded here because until now the contract was silent on it and the engine was
not:

> **CORPORATE ACTIONS (Don's ruling, 2026-10-02).** A held name that is acquired or stops
> trading counts as **sold at its last traded close**, its weight **redistributed pro-rata
> across the rest of the book**.

**WHY THIS BELONGS IN THE CONTRACT AND NOT ONLY IN THE CODE.** It is the one rule in this
amendment that changes a RECORDED NUMBER rather than a power calculation, so it has to be
written where the record is defined. The live book has already exercised it: **WBS left the
book after the 2026-07-30 inception and the served card reports `1 left the book since (WBS),
with the weight spread across the survivors`** — so the behaviour is live, it is visible on
the Index tab, and the contract that governs the series did not mention it. A rule the engine
follows and the contract omits is a rule nobody can check the engine against.

**IT IS NOT A THRESHOLD, A CLOCK OR A σ CHANGE**, which is what keeps it inside this
amendment's additive scope: §3's own framing is that nothing above §5a moves and no statistic
is revised. This fixes an OMISSION — what happens to a position that ceases to exist — and the
answer it records is the one the engine already implements.

**THE ALTERNATIVES ARE WORSE AND ARE NAMED SO THE CHOICE IS LEGIBLE.** Holding a delisted name
at its last price forever would let a dead position carry the book's return indefinitely.
Dropping it and renormalising the DENOMINATOR silently would change the book's size mid-vintage
and make the series discontinuous. Treating an acquisition as a 100% loss would be false, and
treating it as cash held to the end would require a reinvestment assumption this contract does
not make. **Sold at the last traded close, redistributed pro-rata** keeps the book fully
invested, keeps its size fixed, and makes no claim about what the proceeds did next.

**ONE LIMIT, STATED: "last traded close" is a VENDOR-DEPENDENT figure on a delisted name**, and
the project's own price path has already been measured to disagree with the recorded series by
~0.02pp on an ordinary day. For a name that stops trading the disagreement can be larger,
because the last close is exactly where vendors diverge most. The rule is still the right one;
a successor wanting the series reproducible to the digit needs the delisting close STORED on
the row at the time, not re-fetched later.

## 4. WHAT A SIGNER SHOULD KNOW BEFORE AGREEING

* **It makes the contract's own stated power WORSE, not better.** Nobody gains from this
  amendment; it removes an overstatement.
* **It does not void any window.** §5a's void clause triggers on a change to the statistics or
  the thresholds, and this changes neither — it corrects a described INPUT. The current vintage's
  clock is untouched.
* **It cannot be read as a reason to stop recording.** A test that cannot resolve a return claim
  can still resolve a RECORDING claim, which is what the 6-month operational gate is for, and
  that gate is unaffected.
* **The alternative to amending is worse:** §2 currently states a power figure that is
  demonstrably about a different book, and leaving it there means the contract overstates what
  its own verdict will be able to say.

## 5. IF DECLINED — NOT TAKEN; Don accepted on 2026-10-04

**This branch did not fire.** Kept verbatim because a recorded alternative is what makes the
accepted path a choice rather than a default:

> Then §2 keeps its figure and **this file stays as the record that the discrepancy was measured,
> dated and surfaced** rather than discovered at the verdict. The Index tab's power sentence is
> sourced from the measurement either way, so a reader is not misled in the meantime.
