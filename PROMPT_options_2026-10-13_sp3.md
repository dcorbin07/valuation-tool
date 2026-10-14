# PROMPT — options lane — 2026-10-13 — execute SELL-PREMIUM-3 (after SELL-PREMIUM-2 stage 2)

Start this only after `PROMPT_options_2026-10-13_sp2_stage2.md` is on origin/main. Read
`C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path — your worktree's copy may be out of date) (2026-10-13, "Research queued") and the scout's draft `a1d37ff`.

SELL-PREMIUM-3 is the put-spread successor to SELL-PREMIUM-2: the same entry events, short leg and
tenor, plus a long put at the nearest listed strike at or below K_short − 7.5% of spot (refused
outside 5%–12.5%), held to expiry. Its point is to deploy at a realistic account size, where
SELL-PREMIUM-2 earns ~1.2%/yr at $25k because one contract secures more than $2,500.

Execute it as drafted, with your executor review and amendments BEFORE any outcome: register
ALONE, trials booked before any runner, kills in their own pass, build quadrant only, Don's
2026-10-12 pass rule. In particular:

- **Compute everything on the MEASURED net credit**, never on the draft's forecast table — the
  draft itself names three forecast errors that all flatter the spread (BS at median IV, the long
  leg priced at the short leg's IV despite skew, and the tail haircut).
- **Keep both crash bars:** K3-POS unchanged at 6.0 with the synthetic row, and K3-ACCT governing at
  35% of the account (inherited from SELL-PREMIUM-2's measured exposure at $25k, not chosen).
- **Charge the equity round trip** in the middle band (short assigned, long expires worthless).
- **The account-size table at $10k, $25k and $50k is a required leg.** The 100%-deployment rows are
  shown in order to be refused.
- State plainly in the summary whether the brokers Don could use allow spreads in a Roth IRA, as
  measured from their own published rules.

A pass is labelled ELIGIBLE-BUT-UNRESOLVED as before. Paper only; nothing adopted; no real trades.
Done means on origin/main, with a plain-words summary for Don.
