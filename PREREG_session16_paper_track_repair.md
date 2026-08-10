# PRE-REGISTRATION — session 16, paper-track repair (BUG 1, BUG 2) and PT-SPLIT

**Written 2026-08-10, BEFORE any code was changed and BEFORE any repair was run.**
Owner: pipeline builder (`valuation/edge/**`). Routed by the options-bot lane,
`HANDOFF_optionsbot.md` §4 and §9.

This is a **correctness repair, not a search**. Nothing here selects a model, a weighting or a
parameter, so per the HACFLOOR / CHAINFREEZE precedent it is charged to **infra**, `n = 1`, and
**equity `N` stays 131**. No DSR-gated claim moves. That is stated here, before the work, so it
cannot be re-decided after seeing the result.

The reason a repair still gets a register: **it changes numbers in a live book.** Every changed
number is written down below with its expected post-repair value, computed by hand from the
committed export `data_export/paper_track_history.json` (`generated_at 2026-08-09T07:15:04`)
before the code existed. If the repair produces anything else, the register is what catches it.

---

## 1 · The three inputs, as they stand before the repair

From the committed Render backup — the only reachable read path (`HANDOFF_optionsbot.md` §5).

| alert | ticker | contract | state | fill (`entry_premium`) | live `target_premium` | live `stop_premium` | `last_mark` |
|---|---|---|---|---|---|---|---|
| 1 | TGT | TGT260918C00160000 | open | 3.55 | 8.90 | 2.225 | 3.50 |
| 2 | MET | MET261016C00100000 | open | 4.60 | 9.80 | 2.450 | 2.70 |
| 3 | ETN | ETN261016C00500000 | open | 16.10 | 32.20 | 8.050 | 11.10 |

All three alerts carry the identical logged exit policy
`{"target_pct": 1.00, "stop_pct": -0.50, "time_stop_frac": 0.50}`.

**Corroboration that the diagnosis is right, computed before the fix:** dividing each live
`target_premium` by 2 recovers the submit price — TGT 4.45, MET 4.90, ETN 16.10 — and dividing
each live `stop_premium` by 0.5 recovers *the same three numbers*. Two different multipliers
agreeing to four decimals is not a coincidence; the levels are anchored to the submit price, which
is exactly what BUG 1 says.

## 2 · BUG 1 — pre-committed expected values

The specification is the backtested one: `target = fill × (1 + target_pct)`,
`stop = fill × (1 + stop_pct)`, using **the alert's own logged policy**, not a default.

| alert | target: now → **expected** | stop: now → **expected** |
|---|---|---|
| 1 TGT | 8.90 → **7.1000** | 2.225 → **1.7750** |
| 2 MET | 9.80 → **9.2000** | 2.450 → **2.3000** |
| 3 ETN | 32.20 → **32.2000 (UNCHANGED)** | 8.050 → **8.0500 (UNCHANGED)** |

**Pre-committed acceptance criteria — all five must hold, or the repair is wrong and gets
reverted rather than explained:**

1. Exactly **2 of 3** rows change. ETN must be **bit-identical** after the repair: its fill
   equalled its limit, so a repair that moves it is repairing the wrong thing.
2. After the repair every row satisfies `target/entry == 2.000000` and `stop/entry == 0.500000`
   to six decimals.
3. **No row crosses a level as a result of the repair.** Checked by hand now: TGT mark 3.50 lies
   in (1.775, 7.10); MET 2.70 in (2.30, 9.20); ETN 11.10 in (8.05, 32.20). If any row DID cross,
   the repair must stop and report it rather than auto-exit — a bug fix may not execute a trade.
4. The repair is **idempotent**: running it twice changes nothing the second time.
5. It touches **only** `target_premium` and `stop_premium` (plus `note`/`updated_at`). No fill,
   no mark, no state, no exit, no timestamp of record.

### The direction of this repair is FLATTERING, and that is disclosed here rather than discovered

Both changed rows move their target **down** (easier to reach) and their stop **down** (looser,
harder to hit). Corrected, TGT's target falls 20.2% and MET's 6.1%.

**So the bug ran against the paper book and the fix runs for it.** That is not a reason to leave
it broken — the levels are wrong against the specification either way, and comparability is the
entire purpose of the track — but it must travel with the repair, because "we fixed a bug and the
book improved" is the single easiest way for a forward test to flatter itself.

One number makes it concrete. **MET sat 10.2% above a stop level no backtest ever specified**;
at its specified stop it sits 17.4% above. The bug was days away from recording a stop-out that
the strategy being tested would not have taken.

## 3 · BUG 2 — pre-committed expected values

`_eligible` must honour `features.sizing.skip`. Applied to the three logged alerts:

| alert | `sizing.skip` | expected verdict |
|---|---|---|
| 1 TGT | false | **eligible** |
| 2 MET | false | **eligible** |
| 3 ETN | **true** ("one contract costs $1,610, above the $1,000 budget") | **REFUSED**, and the alert's own reason recorded on the row |

**Pre-committed: exactly 1 of 3 refused, and it is alert 3.**

**What this fix does NOT do, committed in advance so it is not presented later as a choice:** it
does **not** unwind the ETN position already open. `_eligible` gates *new* entries only. Closing
a live position to tidy the record is a trade decision and a book change, and "backfill nothing"
cuts both ways — the book must show what it actually did. ETN stays, labelled, and the
register records that the largest position in the book is one the alert's own sizing refused.

**Also not done, deliberately:** position *size* still comes from `cfg.paper_contracts_per_trade`,
not from `features.sizing.contracts`. Reading the sizing quantity would change the book's
construction; reading its veto only prevents trades the alert already refused. The routed fix was
the veto. The quantity is left alone and named here as an open question.

## 4 · PT-SPLIT — the pre-committed conformance test

The routed framing is that the engine "violates the contract's 8% cap". **Measured before
writing anything, that framing is wrong, and the register records the correction:**
`valquo_index.build_index` sets `cap = max(MAX_WEIGHT, 1/len(picks))` with an explicit comment —
on a 10-name book an 8% cap would sum to 80%, so the effective cap *is* 10% and the payload has
always self-reported `effective_max_weight`. The weights are correct for the book they describe.

**The real divergence is BOOK SIZE — 10 names against the published Index's 86 — and it is one
construction fed two different inputs.** `n = max(MIN_NAMES, round(len(large) × TOP_DECILE))`
with `MIN_NAMES = 10`, so a 10-name book means the eligible large-cap tier held **fewer than 100
names**. The published Index's 86 implies a tier of roughly 860. The engine was seeded from a
truncated scan, not from the published book.

Pre-committed conformance definition, fixed before it is measured — a book conforms iff:

- `n_positions >= CONTRACT_MIN_POSITIONS` (**50**), and
- `effective_max_weight <= MAX_WEIGHT + 1e-9` (i.e. the 8% cap actually binds), and
- it did not land on the `MIN_NAMES` floor.

**Expected verdict on the live engine book, committed before running: NON-CONFORMING**, on
`n_positions = 10` and `effective_max_weight = 0.10`.

**The action that follows is fixed in advance, so the outcome cannot pick it:** the engine is
**aligned going forward** (it may only seed a conforming book, and must refuse loudly rather than
silently substitute a truncated one), and the **four already-recorded days are registered as a
separate experiment** that may never be quoted as the Index. Every row lands in exactly one of
those two states — there is no third.

## 5 · Expectations, written down to be scored later

Per the project's standing rule that its directional guesses keep being wrong:

- **BUG 1 repair matches all five criteria exactly: 85/15.** The arithmetic is closed-form; the
  risk is a code path I have not read, not the numbers.
- **The repair will need to run on Render, not here: 95/5.** Every local screener store holds
  zero paper rows.
- **PT-SPLIT: the alignment will NOT retroactively fix the 4 recorded days: 99/1.** They were
  built from an input that no longer exists.

## 6 · What would make this register a failure

If any pre-committed value in §2 or §3 comes back different and the difference is explained
*after* seeing it. The correct response to a mismatch is to revert the repair and report the
mismatch — not to adjust the expected value.
