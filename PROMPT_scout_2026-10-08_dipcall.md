# PROMPT — scout — 2026-10-08 — design the "calls after a sharp drop" program (DIP-CALL)

Read `DECISIONS.md` first: Don authorised this program on 2026-10-08. His idea, in his words:
when an extremely liquid, rock-solid company has a rapid large decline, buy a call with enough
time to expiry, because such companies recover. Design it so it can actually find out — and so a
pass, if one comes, can be trusted.

## What the record already says (read these before drafting; the draft must cite them)

V6 (healthy 20%/30% drawdowns from the 52-week high: four nulls, a drawdown is largely an
inverse-momentum sort), V6-B (healthy dips fall further less often — a RISK result, not a return
one), V6-OPT (cash-secured puts on healthy dips rejected), DC-1 (dip confirmation killed at
feasibility; its provenance note — the idea came from names that recovered, which is selection on
the outcome — binds here too), O17C4 (calls owning an event: a MEAN effect, the median trade is a
near-total loss), O13 (expectancy rises with tenor, not significant), R2 (the alert loses to
random entry), DEEPITM-FIN / SC-3 (long-dated call financing costs), O10/O18 (real fills pay about
two thirds of the quoted half-spread), O11 (positive per-trade expectancy can still lose money
under realistic sizing), and P1S0 (the equity composite only sorts the optionable universe after
2021). Say plainly which of these this program differs from and why it is not a re-run.

## The design, in three steps

**Step 1 — does the STOCK bounce? (equity data, decades of events, cheap).** Event: a name in the
Index's $10B tier (or a stated liquidity tier) falls by at least k times its own trailing daily
volatility over 1, 3 or 5 sessions. Volatility-relative, not a flat percentage — a 3% day is
ordinary for NVDA and extreme for KO. Split news-driven drops (earnings and other dated events)
from no-news drops: Chan (2003) and Savor (2012) find no-news shocks tend to reverse while
information shocks drift, so pooling them could hide both. Optionally condition on the shipped
quality/health scores ("rock solid"). Measure forward 5 / 21 / 63 / 126-session returns against
the stock's own normal return and the market, on the corrected universe, with the drops that kept
falling included (2000-02, 2008, 2022 — no survivor filtering). If the bounce is not larger than
costs here, no call can make it profitable, and the program stops.

**Step 2 — is a CALL the right way to own the bounce? (only if step 1 passes).** For each event,
price the call that would have been bought from the options data on disk, on a pre-fixed grid of
time to expiry (Y) and strike (Z: e.g. ITM 0.70 delta, ATM, 5% OTM), held to the horizon where
step 1 found the bounce. The specific hurdle: implied volatility jumps after a drop, so the call
costs more exactly when this strategy buys it; the bounce has to beat what the option price already
assumes. Controls: the identical call bought on random days on the same names (R2's method) and
simply buying the shares. Use the shipped fill engine and split guard. State coverage by year and
tenor (Tier E reaches past 200 DTE for 2016-2018 only) BEFORE any number is read.

**Step 3 — forward paper book** on the fleet harness, declared before any fill, if step 2 passes.

## Requirements

- Power FIRST, at the honest hurdle (MB22's gate): how many events each step needs to see an effect
  of the size the record has seen, against how many exist. DC-1 died because the event count could
  not resolve the effect; say up front whether that happens here.
- The full grid (k, window, news split, quality condition, Y, Z, holding period) fixed in the
  draft and every cell counted as a trial; Benjamini-Hochberg across the batch; both halves; blind
  register committed alone by the executor. No cell is chosen after the fact.
- Write a plain-words summary for Don: what would count as success, what the realistic odds are
  given the record, and roughly how long each step takes.

Design only: `PREREG_DRAFT_dipcall.md`, no trials, no measurement. Done means on origin/main.
