# PROMPT — The Dip Detector tab, and the scream-buys track rebuilt with real fields

**Owner:** `app fixer`. **Handoff:** append to `HANDOFF_appfixes.md`.
**Status: OUT-OF-BAND, product — Don's direction, recorded verbatim below so nobody re-litigates.**

> Don, 2026-08-13: a new tab, the **Dip Detector** — "when a rock solid company sees a dip of X%+
> and the financials are all healthy, no good reason besides sentiment or something that will very
> likely pass over, we have it alerted." And: "the options scream buys track record wiped, and
> include target sale, price bought in, and current price, same as our paper account tracks."

## SCOPE / collision safety
You own `valuation/web/**`, `valuation/report/**`, `valuation/saas/**`. Greeks is doing the
scream-buy LOGGER backend in parallel (schema + archive) — coordinate through the handoff on the
field names it emits; do not build a second logger. Pipeline builder is pre-registering the dip
research separately. Not `valuation/edge/**`, `valuation/screener/**` beyond reading.

## ITEM 1 — the Dip Detector tab

**What it is, built entirely from measured pieces that already exist:** a screen listing names
where (a) drawdown from recent high exceeds a threshold (default X = 20% from 52-week high;
make X a visible control, 10–40%), (b) the fundamentals score HEALTHY — quality, financial health
and growth sub-scores above floors you take from the existing score machinery, (c) nothing
disqualifying is known: valuation not withheld, no fail-closed/no-data flag, confidence not
floored by the terminal-share rule, beta provenance clean. Each row shows the drawdown, the
healthy sub-scores as chips, the fair-value band as context, and the score with its calibrated
language.

**THE POSTURE LINE, and it is hard:** the tab may say what is MEASURED — "this name is down X%
while its fundamentals score healthy" — and may NOT say "this will pass," "buy the dip,"
"sentiment-driven," or any recovery prediction. The claim Don wants ("very likely passes over")
is EXACTLY what pipeline builder is pre-registering on the panel right now (V6). Until that
verdict lands, the tab's own explainer says so, in the product's plain voice: *"Whether healthy
names in drawdown actually recover better than the market is a testable claim — we are testing
it, and this page will say the answer when the register closes. Until then this is a screen, not
a prediction."* If V6 comes back positive, the copy upgrades WITH its numbers; if it comes back
null, the copy says that too. Wire the explainer to a constant the V6 close-out can flip — not
prose someone must remember to edit.

Public tier gets the screen with full disclaimers (it is model output, same class as the hot
list); the usual rules — no raw vendor rows, no per-name precision claims (V3), withholding
honoured. Discord/email digests do NOT pick it up until V6 lands — an outbound "dip alert" is a
recommendation-shaped push and waits for the evidence.

## ITEM 2 — the scream-buys track record, reset and rebuilt

Don's call, and the honest way to do a wipe: **ARCHIVE, never delete.** The old record moves to a
dated archive file with a register note — *"record reset 2026-08-13 at Don's direction; prior
record archived at <path>; reason: predates the corrected alert stack (B1 price basis, C-series
fixes) and lacked entry/target/current fields"* — visible from the tab's footer. A silent wipe of
a track record is the one thing this project must never do; a dated, reasoned reset with the old
record inspectable is legitimate.

The rebuilt display, per alert (greeks' logger emits these — consume, do not recompute):
**price bought in** (entry premium at alert), **target sale** (the exit policy's target premium —
+100% unless the alert's own policy differs), **current price** (live quote, marked stale if the
quote is old), plus stop level, DTE remaining, and status (LIVE / HIT TARGET / STOPPED / TIME-
STOPPED / EXPIRED) — the same rendering conventions as the paper account table. The R2 context
line stays on the tab: the entry signal measured dead; these are convex, low-hit-rate alerts;
P3's streak framing applies. Premium/owner tier per the existing surface split.

## Report

Append to `HANDOFF_appfixes.md`: the tab live with a screenshot-equivalent rendering, the V6-gated
explainer wired to its constant, the archive path + register note for the old scream record, the
new table consuming greeks' fields, catch-all walks extended to the new surfaces, `## BUGS FOUND`.
Ledger note under V6 (product half). Merge main first; suites green; push and verify.
