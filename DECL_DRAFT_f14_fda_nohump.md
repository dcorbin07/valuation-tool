# DECL DRAFT — F-14: FDA NO-HUMP CONVEXITY (long book)
## Tag: [O7-scope (earnings only — the market's overpricing was measured on its CALENDAR; a date the IV surface shows no hump for is definitionally not on it) / VIRGIN for non-earnings catalysts. S3-I2 (built — the calendar starts 2026-08-2x) and I-1 are the instruments.]

**Entry rule (frozen):** weekly: every optionable name with an S3-I2 catalyst date
(PDUFA/decision class) inside **90 days**. Hump check at entry via I-1's term structure:
compute event-month ATM IV vs the adjacent later month; **if event-month ≤ 1.10× adjacent
(NO hump), enter; if > 1.10× (priced), RECORD-AND-SKIP** — the skips are the control
population and are first-class records. All qualifying no-hump names enter (sparse; if >8
in a week, largest by market cap, alphabetical tie-break, skips counted).

**Structure:** buy the straddle (nearest-ATM call + put, same strike where listed, else
nearest strangle — rule: minimize |call strike − put strike|, ties → tighter around spot),
expiry nearest above the catalyst date. **Exit at catalyst date + 2 sessions** at bid
(frozen). Entry at ask via the F-1 randomizer.

**Universe/sizing:** optionable S3-I2-covered names; cap 6 open; equal premium; sandbox;
`O11` binds.

**Records:** the calendar source row (vendor, scrape date), the hump ratio and both months'
IVs, quote pairs both ends, the skip population's identical fields.

**Verdict horizon — the honest number:** binary-catalyst names ∩ optionable is thin; est.
**a handful of qualifying entries per quarter → 12+ months to 30 fills**, declared plainly
(the map's own number). The no-hump RATE and skip census are reported descriptively from
week one — those are findings about pricing even before any P&L verdict. Meter: mean
per-trade return on premium vs 0; **MEI +30pp/trade** (sparse books must clear big); both
vocabularies at commit.

**Verdict grammar:** PAYS / BLEEDS / CANNOT-TELL(horizon).

**Trial:** 1, options, at first verdict read. **Void:** entering humped names (they are the
control); holding past the frozen exit; any earnings-date entry through this book (I-4
events belong to F-12/F-13).
