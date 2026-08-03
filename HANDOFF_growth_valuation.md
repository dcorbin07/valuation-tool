# HANDOFF — growth / pre-profit valuation (RKLB $2.63 bug)

Branch: `worktree-growth-valuation`. Scoped to the fair-value engine only — no edits to
`valuation/edge/`, the data loader, or the scan pipeline beyond carrying two extra fields per row.
Date: 2026-08-02.

## What was actually wrong

Not "the DCF is too bearish". RKLB's $2.63 came from `comps.py` applying the **Industrials sector
benchmark of 2.0x EV/Sales** to a company growing 40-140%/yr that trades at **66x sales**. The DCF
was negative (-$4.26), so `blend.py` dropped it and the headline became **100% that mature multiple**.
The scenario cards meanwhile still printed the raw DCF cone: **-$4.95 / -$4.26 / -$1.45** under a
positive $2.63 headline.

On the screener side the same class of name got *nothing at all*: `fairvalue.py` used only
earnings yield and FCF yield, both negative for a loss-maker, and deliberately skipped EV/Sales and
EV/EBITDA because the scan didn't carry net debt per row.

## What changed

**New `valuation/engine/growth.py`** — the growth lens, and the pure helpers both halves of the app
now share:

- `maturity_score(op_margin, fcf_margin, growth, market_cap)` -> 0..1. Replaces the old
  `p_established` (which read operating margin alone). Weighted sigmoids: margin .35, cash .25,
  growth .25, size .15; missing inputs renormalize; nothing at all -> 0.5.
- `growth_fair_value(...)` — compound revenue over a horizon of `n_years x (1 - maturity)` using
  the DCF's own faded growth path, exit at a mature sales multiple, discount back, charge the
  operating losses funded on the way, bridge EV -> equity with net debt.
- `exit_sales_multiple()` — half a **fundamental** anchor `margin x (1-tax) x (1-g/ROIC) / (r-g)`,
  half the peer/sector benchmark, with the peer half **capped at 2x the fundamental**.
- `build_growth_scenarios()` — bear/base/bull with growth and margin shifted (same deltas as the
  DCF scenarios) **plus exit-multiple compression/expansion** (0.80x / 1.00x / 1.25x).

**`blend.py`** — three lenses instead of two, weighted continuously:
`w_dcf = quality x maturity`, `w_mult = (1 - quality) x maturity`, `w_growth = 1 - maturity`,
renormalized over whichever produced a positive number. New fields: `maturity`, `maturity_parts`,
`growth_led`, `headline_mode`, `headline`, `confidence`, `value_low`, `value_high`.
`p_established` is kept as a legacy alias for `maturity`.

**`pipeline.py`** — wires the lens in and adds `fair_value_scenarios` (bear/base/bull run through
the SAME blend as the headline) plus `growth_lens` to the API payload.

**`reverse_dcf.py`** — the implied-growth solver saturates at its +60% search bound far more often
than anyone noticed, including on RKLB. It now reports `implied_growth_bounded` and the text reads
**"at least ~94%"** instead of a fake point estimate.

**`screener/fairvalue.py`** — rewritten. `providers.company_to_metrics` now emits `net_debt`, and
`screen._rows_from` carries `net_debt` / `revenue` / `gross_margin` per row, so EV multiples work:
`implied EV = current EV x (peer / own)`, `implied equity = implied EV - net debt`,
`implied price = price x implied equity / market cap`. Same maturity blend and the same
`engine.growth` math as the deep page (with fixed 13% -> 9% discount constants, since the scan has
no per-name WACC). Rows gain `fair_value_confidence`.

**UI / CLI** — `app.js` scenario cards and the range bar read `fair_value_scenarios`; a growth-led
name shows a **range** in the hero instead of a point value and leads with the implied-growth
sentence; `cli.py` prints the same-method cone. One `<div id="scenarioNote">` added to `index.html`.

**Warning guard** (`scoring.py`, `pipeline.py`) — "fair value < 0.2x price = almost certainly a data
problem" no longer fires on a growth-led valuation. On a pre-profit name that gap **is** the thesis;
labelling it a data error trained the reader to ignore the one number that matters. The >5x side is
unchanged.

## Result on RKLB (live data, price $64.95)

| | before | after |
|---|---|---|
| headline | **$2.63** (100% mature multiple) | **$6.88**, 90% growth lens / 10% multiples |
| scenario cards | **-$4.95 / -$4.26 / -$1.45** (the excluded DCF) | **$0.95 / $6.88 / $20.37**, same method |
| confidence | not stated | **low**, and the hero shows the range not the point |
| headline text | none | "price implies **at least ~94%/yr** revenue growth; our base case ~34%" |
| growth lens detail | — | revenue -> ~$9.8bn over 8.8y, exits 1.5x sales, justified **6.1x sales today vs the 66x it trades at** |

Screener: RKLB previously got **no fair value at all** (both equity yields negative); it now gets
$9.06 at low confidence.

Spot-checked live and all ordered, with the base card equal to the headline: PLTR $20.20, TSLA
$24.41, AAPL $119.65, KO $65.15, NET $37.75, SHOP $32.94, IONQ $13.25, JPM/BAC unchanged on P/B-ROE.

## Be honest about this

- **RKLB is still far below the price, and that is the model's real opinion, not a bug.** Three
  assumptions drive it: a 17.5% WACC (beta 2.2), an Industrials-normal 13% terminal margin, and
  capital intensity of ~$0.89 of investment per $1 of new revenue. The fix makes the *method* valid
  and the presentation honest; it does not make the model bullish. If Don wants a number closer to
  the street's, the argument has to be made on those three inputs, not on the lens.
- **The growth lens does NOT charge growth capex** — the exit multiple is the value of what that
  capital builds, and the DCF lens charges it in full. The two deliberately bracket the answer.
  Charging it in both places takes RKLB to ~$1 and collapses the lens back into the DCF.
- **It also ignores dilution beyond the operating-loss charge.** A company that funds itself with
  equity at depressed prices lands below this.
- The 0.80x / 1.25x scenario multiple factors and the 13%/9% screener discount constants are
  judgement calls, not measured numbers.
- Nothing here is backtested. This is valuation-page arithmetic, not a factor with an IC.

## Tests

All green, run on this branch:

| suite | result |
|---|---|
| `tests/test_engine.py` | **28/28** (was 19; 9 added, 2 rewritten) |
| `tests/test_screener.py` | **16/16** (was 13; 3 added) |
| `tests/test_edge.py` | 89/89 unchanged |
| `tests/test_bulk.py` | 14/14 |
| `tests/test_saas.py` | 20/20 |
| `tests/test_intraday.py` | 18/18 |

Two existing engine tests were rewritten on purpose: `test_blend_favours_multiples_for_cash_burning_growth`
became `..._favours_the_growth_lens_...` (a loss-making grower must no longer be carried by a mature
multiple — that assertion was pinning the bug), and the established-name test now checks the headline
sits inside the span of all live lenses rather than just the two old ones.

Notable new coverage: scenario cards equal the headline and stay ordered and positive; the
implied-growth read says "at least" when the solver is bounded; the growth lens degenerates to a
plain sales multiple at maturity (no cliff); a frothy sector multiple is capped against the
fundamental anchor; the EV/net-debt bridge charges leverage.

## Bug found and fixed en route

Scenario blending originally let each case pick its own lenses, so Unity (U) came out **bear $15.68
above bull $7.30** — the DCF survived the bull case and not the bear one. The base case now decides
which lenses are live, and in the other cases a lens that goes non-positive is floored at zero
rather than dropped. That also guarantees the base card equals the headline.

## Next, if anyone picks this up

1. Sector multiples in `comps.SECTOR_MULTIPLES` are hardcoded large-cap norms from an unknown date
   and now feed the exit multiple as well. Worth refreshing from real data.
2. `_target_margin` gives every Industrials name 13%. RKLB has 34% gross margins; that assumption is
   doing more work than the multiple choice is.
3. The growth lens is only wired to the deep page and the hot list. `report/pdf.py` and
   `report/excel.py` still export the raw DCF cone.
