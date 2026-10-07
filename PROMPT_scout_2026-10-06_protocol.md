# PROMPT — scout — 2026-10-06 — remove the arm cap, write the staged protocol, draft the first batch

Read `DECISIONS.md` first (new; Don's rulings in one place). Don's ruling of 2026-10-06: the
twelve-arm cap in `RESEARCH_CHARTER.md` §5 is REMOVED. Fluke risk is controlled by counting,
calibration and staged confirmation, never by declining to test. Nothing else in the charter
relaxes: both-halves, pre-committed margins, blind registers committed ALONE, placebo-calibrated
bars and trial counting all stay exactly as they are.

## 1. Amend `RESEARCH_CHARTER.md` (markdown only, its own commit)

Replace §5 with the staged protocol below, and make §4(b)'s 2×2 the mechanism for NEW signals:

- **STAGE 1 — SCREEN, unlimited arms.** Every candidate is scored on the BUILD quadrant only:
  2009-2019 × the fixed ticker half (`X1`'s `sha1(ticker) % 2`) of the CORRECTED full raw
  universe — the panel `UNIVERSE-BIAS` built from the 2026-10 freeze — never `data/backtest`.
  Every arm is booked in the research log (so the HLZ hurdle and the deflated Sharpe keep
  counting it), and a batch is judged with Benjamini-Hochberg at q = 0.10 across the batch.
  Universe filters must be RELATIVE (percentiles), never absolute ranks (INDEX-CHOICE-ARM4).
  The both-halves rule applies INSIDE the build quadrant (2009-2014 / 2015-2019).
- **STAGE 2 — CONFIRM, rationed.** Only Stage-1 survivors, with the bar fixed in the register
  before the look, get ONE read of the CHECK quadrant: 2020-2026 × the other ticker half. Each
  read is logged; a construction gets one.
- **STAGE 3 — HOLDOUTS AND FORWARD.** Survivors get one read of the 1999-2008 five-theme proxy
  (disclose that POOL-SIZE already read it for pool width) and a forward paper book on the fleet
  harness. The 1972-1998 WRDS era stays closed until Gate B clears its pre-committed 0.90.
- **ADOPTION.** Anything that passes all three goes to Don with its expected return quoted at
  half its backtested size (McLean-Pontiff). Adoption is Don's and is a vintage event.

## 2. Draft the first Stage-1 batch as ONE register draft (`PREREG_DRAFT_stage1_batch1.md`)

Candidates, each with its exact construction and a free pre-outcome kill:

1. Intangible-adjusted value — Eisfeldt-Kim-Papanikolaou (2022), Peters-Taylor (2017) — capitalise
   R&D and a share of SG&A from Sharadar SF1 so `W-28`'s Compustat-linkage kill does not apply.
2. Residual momentum — Blitz-Huij-Martens (2011). Note `CONFIG.residual_momentum` exists in the
   code with no recorded test.
3. Information discreteness / "frog in the pan" — Da-Gurun-Warachka (2014).
4. Campbell-Hilscher-Szilagyi (2008) distress probability, as a junk FILTER (ties to r1's tiered
   pool register; do not duplicate its arms).
5. Net payout yield — Boudoukh-Michaely-Richardson-Roberts (2007); state its overlap with the
   shipped issuance signal and the rank-identity lesson from `S16`.
6. Every surviving FREE_KILLS candidate: N1, N2, N3, N5, N6, N7.

Also note, without drafting, volatility-managed exposure (Moreira-Muir 2017; critique Cederburg
et al. 2020) as a possible risk overlay for a later batch.

Design only: no trials, no measurement, no register committed (a draft is not a register). Done
means both files on origin/main and a short plain-words summary for Don of what is in the batch
and what each candidate's kill is.
