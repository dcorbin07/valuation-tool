# PROMPT — app fixer — 2026-10-21 — item 76: fix what the outside review found — stale public figures, the lopsided fair-value check, false precision, beta sensitivity, and the writer sign-off

Read `C:\Users\donni\Downloads\valuation-tool\DECISIONS.md` (this exact path) first. **Do not edit
`DECISIONS.md`.**

An outside review of valquo.co and the repo (2026-10-21, repo @ `2be2745`) was checked against the
code by the manager. These are the points that held up. **This item changes what users see and
read. It changes no scoring, ranking, weight, fair-value arithmetic, Index construction,
rebalance path or live-trading code.**

**Do not land anything between Friday 2026-10-23 4pm ET and the 10-22 rebalance being recorded**
that night. A deploy restarts the service during the rebalance send.

## 1. Stale figures and claims on public pages and docs

Found by grep on origin/main:

- `valuation/web/templates/methodology.html:58` and `portfolio.html:489` still say breakeven
  **134 bps against a measured 33 bps**. That is the superseded 2,531-name panel. The corrected
  canonical figure is **98 against 55 (a 1.78× margin)**.
- The review also found a **123.5 / 77.0 bps** pair on another page. Find every cost pair on every
  public page and stamp each, inline, with the book it describes:
  - the research decile, or the served Index;
  - which universe;
  - which account type (Roth or taxable).
- Read every number from the tracked artifact. Never retype one.
- Add a guard test that fails if any public page carries a figure from the superseded panel.
- `README.md:29` says the valuation engine *"has never been backtested as a return signal."* That
  is wrong. Restate it, citing the record:
  - the fair-value gap was tested and does not predict returns (growth calibration, IC *t* +0.99,
    NULL);
  - as an exit rule it was NULL (`S23`);
  - as an entry filter it was rejected (`S10`);
  - so it is a framing tool, not alpha.
- `README.md:138-139` says the track *"is currently not recording"* (`recording_ok: false`). The
  bound series has been written every trading day since 2026-09-23. Restate what is true today,
  using section 6's finding.
- `DATA_AND_METHODS.md` still describes the superseded 2,531-name panel and its old conclusions,
  and some `settings.py` comments still reference it. Bring both current.

## 2. The publication band is lopsided

A model value above 5× price is withheld; one below 0.2× only gets a quiet warning. The Dip tab
showed AppLovin at $130.08 fair value against a $272.46 price, labelled healthy.

**Don's ruling (2026-10-21): flag low values LOUDLY, do not hide them.**

- Below the mirror threshold (0.2×, imported from the same place as `FV_BAND_HIGH`, never retyped),
  show a visible low-confidence flag on every surface that shows a fair value: the valuation page,
  Hot Stocks, Dip Detector, and the Index holdings. Make it as prominent as the high-side refusal.
- **Measure, don't invent:** report how many currently served names sit between 0.2× and 0.5× of
  price. Don can then decide whether a second, softer tier is wanted. Add no new threshold.

## 3. Show how much the fair value depends on beta

KO reads $58.50 at its vendor beta of 0.32 and $35.11 at beta 1.0.

- On the valuation page, show the fair value at the vendor beta and at ±0.3 around it, bounded by
  the engine's own beta limits.
- Compute it with the SHIPPED engine, never a re-implementation.
- Label it plainly: *"how much this value depends on one input"*.
- The point value does not change.
- Names already flagged on beta provenance keep that flag visible everywhere the name appears.

## 4. Replace two-decimal scores with bands

**Don's ruling (2026-10-21).**

- The project's own chance-universe test: the top decile beats chance as a group, but a name's
  position INSIDE it is not distinguishable from chance.
- In lists (Hot Stocks, Index holdings, Dip Detector):
  - show the band, e.g. "top 10%", and the themes driving it, instead of the two-decimal
    composite;
  - keep the existing sort order.
- In a name's detail view, a whole-number score may stay, with one plain sentence that position
  within the top 10% is not meaningful.
- Test that no list renders a two-decimal score.

## 5. Say how many themes fed each live score

The live scan can run on fewer than the seven backtested themes; FMP's lapse put one hot name on a
single theme.

- Everywhere a score shows, say how many of the seven themes fed it today.
- Below seven, label it *"not the backtested model"*.
- Read the count from the scan's own coverage, and pin it by test.

## 6. The writer sign-off (a question to answer, not a gate to set)

`PAPER_TRACK_CONTRACT.md` §5's `Operational gate passed` row cannot pass *"until the bound series
has a verified automated daily writer (§7.2)."* `PT-WRITER` is still open. Report to Don in plain
words:

- (a) what §7.2 requires for "verified";
- (b) whether `track-row.yml` has met it since 2026-09-23;
- (c) whether vintage 4's missed days from August and September, which the site shows as
  reconstructed, still let the 2027-02-13 gate pass under §3's tolerances;
- (d) exactly what would have to happen for it to pass.

**Do NOT edit the gate row** — only Don's signature does that. Update `PT-WRITER`'s ledger row and
the README to what is measured.

## Not in this item

The review's model suggestions are construction changes to the valuation engine. Each needs its
own tested change if Don wants it:

- reinvestment floor;
- dilution-aware growth lens;
- correlated Monte Carlo;
- a bear case that moves WACC;
- estimated sector constants;
- calibrated health breakpoints.

The fair-value gap as a ranking signal (`MA55`) is r1's.

## Done

On origin/main, with a plain-words summary for Don, including:

- every stale figure corrected, with page and line;
- the count of served names between 0.2× and 0.5× of price;
- before-and-after screenshots of the valuation page (KO), Hot Stocks and Dip Detector;
- the section 6 answer.

No key, no percentage, and no `.github` change.
