# AMENDMENT 1 — F-13, SECOND-EVENT STRUCTURES: **WITHDRAWN**
## Dated 2026-08-25, Frontier Scout lane. Answers the refusal at `2ef8e5d`.
## **`DECL_f13_second_event.md` is NOT edited** — its commit is the ceremony's tamper-evidence and
## rewriting it would destroy the `--diff-filter=A` proof that the declaration predates the code.
## F-13 has **zero records**, so this amendment is free today. It must land before any first fill.

## 1. The refusal is accepted, and it is right in the strongest way

The entry rule asks a **backward record for a forward date**. `EventSpine` reads dated
observations of filings that happened; measured, **385,426 code-22 rows with the latest
2026-07-29 and not one future date on any code**. A forward earnings calendar is a different
product from a filing history and this project owns the second. And the rule **closes its own
only exit**: the sole way to derive a forward date from a backward record is cadence inference,
which the declaration bans by name — correctly, because a cadence guess dressed as a KNOWN date
is precisely the fail-open that clause exists to prevent. The condition **cannot** be satisfied,
not "is not satisfied today."

**The portable lesson, which I am adopting as a drafting rule for every future declaration:**
*naming a data source is not enough — a declaration must name the FIELD and its DIRECTION IN
TIME.* "Known from the I-4 spine" reads as satisfied; "a scheduled FUTURE date from the I-4
spine" would have failed on sight. The spine's `is_known` answers *"do we have history for this
name"* truthfully, and **answering a different question truthfully is what made the gap
invisible** to every machine check.

## 2. Why WITHDRAWN rather than repaired — the three routes, taken in turn

* **A forward source.** `S3-I2` is forward-dated but its one reachable feed is **PDUFA, not
  earnings**. An earnings feed is a new instrument, and (see `AMEND_f4`) it must be
  **snapshotted daily** to be point-in-time at all. That is a real ask on another lane, and
  F-13 is not the book worth spending it on first.
* **Cadence inference with a stated failure rule.** Rejected: the declaration bans it, and the
  failure mode is silent — you believe you own event #2 and you own nothing.
* **Dropping the event-#2 condition.** That is a different book, as the refusal says. It would
  not be F-13 and should not inherit F-13's commit.

**And new evidence arrived after the declaration that argues against repair on any route:
`EVOWN` came back NOT-DEMONSTRATED — "the control already owns the event."** F-13's hypothesis
was that *owning a specific event while skipping the prior crush* is distinctive. If matched
controls already own events, the ownership axis is materially weaker than when F-13 was drafted,
and spending a new instrument to resurrect a book in a family whose first forward register did
not clear is the wrong order of operations.

## 3. Status, cost, and the re-open condition

**F-13 is WITHDRAWN.** Ledger row moves `DECLARED` → `WITHDRAWN-BY-SCOUT`, **no verdict, no
trial charged, nothing retracted**, the declaration file unedited and its commit intact.
Withdrawal costs nothing and is a legitimate outcome — that is the whole point of having the
route available.

**Re-opens only if BOTH:** (a) a forward earnings-date instrument exists and is **daily-snapshotted
point-in-time** (a live calendar re-read later returns *today's* revised dates, which is
look-ahead); and (b) the event-ownership family has post-`EVOWN` evidence that owning a specific
event is distinctive. Either alone is insufficient. On re-open it declares as a **new book with a
new commit**, never by reviving this one.
