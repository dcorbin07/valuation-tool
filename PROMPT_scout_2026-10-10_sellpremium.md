# PROMPT — scout — 2026-10-10 — the options angle that is left: SELLING the expensive premium

Read `DECISIONS.md` (Don wants a profitable options strategy developed, 2026-10-08) and the
DIP-CALL-3 draft (7cb4657).

DIP-CALL-3 showed buying calls after a sharp drop is foreclosed by arithmetic: implied volatility is
elevated exactly then (V6-OPT measured +17.71% over the name's own trailing median) and any
plausible drift is a few percent of the move the option already prices. The same fact points the
other way: if options are systematically EXPENSIVE right after a sharp drop in a strong name, the
side that might earn is the SELLER of that premium. V6-OPT is the nearest measurement: its
cash-secured 25-delta put on healthy dips earned +1.13%/trade on cash secured, positive in both
halves, an 84% win rate, and beat random entry decisively (z +7.25) — and was rejected only
because the HEALTH filter added nothing (unhealthy dips earned more), so it read as "just short
vol". Also read: A3 (short vol, rejected at −7.99%/trade — reconcile it with V6-OPT and say why
they differ), O11 (survivability under realistic sizing), O10/O18 (real fills), O7 (earnings
options rich on this universe), and the one-crash asymmetry V6-OPT pre-committed.

Your job, design only:

1. Say plainly whether "sell puts (cash-secured, no margin — a Roth) after a sharp drop in a $10B
   name, conditioned on the drop rather than on health" is a NEW hypothesis or a re-run of V6-OPT,
   and what changes if any.
2. If new, draft `PREREG_DRAFT_sellpremium.md`: the event (DIP-CALL-2's volatility-relative drop
   on the point-in-time tier), strike rule held by MONEYNESS as well as delta (V6-OPT's
   mechanism), tenor, exit, the random-entry control on the same names, survivability at Don's
   real account size and O11's concurrency caps, crash handling (2020 and 2022 must count), coverage
   by year on the options data on disk, power, and the trial count.
3. Plain-words summary for Don, including the worst case: what a 2020-style crash does to a book
   of short puts.

No trials, no measurement. Done means on origin/main.
