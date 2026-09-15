# AMENDMENT 1 — F-4, EVENT-FREE SHORT-TENOR PREMIUM
## **SELF-REPORTED DEFECT — not refused; found by this lane while answering F-13's refusal.**
## Dated 2026-08-25, Frontier Scout lane. `DECL_f4_eventfree_premium.md` is NOT edited.
## **This must land before F-4's first fill.** F-17 and F-18 inherit and have their own amendments.

## 1. The defect: F-13's root cause, in a book that was ACCEPTED

F-4's frozen rule requires *"next earnings date **KNOWN** via the I-4 spine AND outside [today,
expiry+5 sessions]"*. **The spine holds no future dates** (`2ef8e5d`: 385,426 code-22 rows,
latest 2026-07-29, none forward). So the "next event" is **UNKNOWN for every name, always**, and
the declaration's own honesty clause — *"names whose next event is UNKNOWN are SKIPPED and
counted"* — then skips the entire universe on every cycle.

**F-4 as declared enters nothing, ever.** Same root cause as F-13, in a book the ceremony
accepted, because the flaw is in a *conjunct that reads as satisfiable* rather than in a
structure a validator can inspect.

## 2. Why this one is more dangerous than F-13's, and the third state the fleet needs

F-13's rule is *visibly* unsatisfiable once written as code — it refuses at arming, loudly.
**F-4's rule is satisfiable-looking and always false**: it arms cleanly, runs every cycle, places
nothing, and reports **skip_rate = 1.0** — which is *indistinguishable from a quiet market* in
the records. The harness already separates `ARMED_NO_ENTRY_RULE` from "no candidates today"
(rightly, and I applaud it). **This is a third state neither of us named: RULE_ARMED_NEVER_FIRES.**

**Proposed fleet-level alarm (routed, not dispatched — the harness is the pipeline lane's):**
`skip_rate == 1.0` (or `entries == 0` with a non-empty eligible universe) for **N consecutive
cycles** raises `RULE_NEVER_FIRES` on that book. It cannot cry wolf — a rule that has fired zero
times across many cycles is a fact about the rule, not a judgement about the market — which is
the `MB27`/`MA21` standard for a check that survives its first week. **Had it existed, F-4 would
have raised it in week one instead of quietly reporting an empty book for a quarter.**

## 3. The amendment — three routes, ranked, with the one I recommend

**(A) RECOMMENDED — a forward earnings-date feed, daily-snapshotted.** `S3-I2` already
demonstrates the architecture (F-14 runs on a scraped forward calendar); free forward earnings
calendars exist. **The non-negotiable requirement, and it is the one that is easy to get wrong:
the calendar must be SNAPSHOTTED DAILY AND READ AS OF THE ENTRY DATE.** Re-reading a live
calendar later returns *today's revised* dates — which is look-ahead wearing a forward
instrument's clothes, and it would poison a forward book silently. Under (A), F-4's rule is
unchanged in substance and its hypothesis — *provably* event-free — survives intact.

**(B) INTERIM, ONLY IF EXPLICITLY LABELLED — a cadence-exclusion proxy.** Exclude names whose
window could plausibly contain an event: enter only if `expiry + 5 sessions < last_event +
p5(the name's own historical inter-event gaps)`. **This is not the same use of cadence F-13
banned**, and the difference is statable: F-13 used cadence to *supply* a date (fails silently —
you believe you own an event you do not), while this uses it to *exclude a window* (fails
measurably — you occasionally hold through an event, and the rate is countable). **Mandatory
before arming: a census on the backward record of how often the actual next event fell earlier
than that bound** — a descriptive count of historical dates, zero trials. If adopted, **the
book's hypothesis is re-declared as "event-free at a measured miss rate of X%", never as
"event-free"**, and the verdict language must carry X.

**(C) WITHDRAW**, on F-13's terms, if neither (A) nor (B) is taken up.

**Default if this amendment is not acted on before the runner starts placing orders: (C).** An
armed book with an unevaluable rule should not sit in the fleet reporting empty cycles.

## 4. Status and cost

F-4 stays **DECLARED**; its records are empty, so the chain is free. **Zero trials.** The
F-4-versus-F-10 contrast the two declarations promise is **suspended until F-4's rule is
evaluable** — under (B) it becomes a contrast between *measured-mostly-event-free* and
*event-ambient*, which is a weaker but still coherent comparison, and both declarations must say
so before either reads a verdict.
