# PROMPT — app fixer — 2026-10-08 — item 41

Read `DECISIONS.md` first.

## (a) 507 names a scan get no sector, so their valuation is withheld

Item 40 found `sector_resolve.py:145` calls FMP's retired api/v3/profile, and 507 names in the
scan are UNRESOLVED on every source — regime UNKNOWN, valuation withheld. That is about a third of
the ~1,492-name hot-list universe showing no fair value. Fix sector resolution with a source that
is free, official and covers US filers: SEC EDGAR's SIC code from the submissions JSON (for a
live valuation dated today, today's classification IS the point-in-time one), mapped onto the
engine's eleven sector strings by IMPORTING the engine's own keys (S25's rule — no retyped list,
and an unmapped code is a named state, never a silent default to the middle of the margin range).
Respect SEC's fair-access rules (declared User-Agent, rate limit) and cache results. Measure first
on the 507: how many resolve, by mapped sector, and how many still cannot (foreign filers, funds).
Report how many valuations stop being withheld, live.

## (b) A price-history rung that is not Yahoo

Item 39 showed the price chain has no rung that does not depend on Yahoo, and item 40 showed FMP
cannot fill it on the current plan. The service already holds a live Tradier token (the intraday
scan uses it). Measure Tradier's daily history the way you measured FMP — as-traded closes, the
52-week high, split handling, coverage on a sample that includes REITs, utilities, ADRs and recent
splitters, and its rate limits — and report. Do NOT enable it; Don decides after the numbers.

## Still held

The 52-week-high basis (await DECISIONS.md), intraday scheduling (await DECISIONS.md), and the
public pages (until r1's canonical move lands).

Done means on origin/main, verified live, with a plain-words summary for Don.
