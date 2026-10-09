# PROMPT — r1 — 2026-10-07 — calibrate the floors on the corrected universe, then re-measure what is unmeasured

Read `DECISIONS.md` first.

Context: `UNIVERSE-BIAS` part 2 showed the research headline does not survive the corrected full raw
universe (+7.17% → +2.83%, t 1.08) while the $10B Index tier does (18.42% → 18.02%), and
`STAGE1-BATCH1` scored its arms with every critical value labelled UNCALIBRATED. Every future screen
runs on the corrected universe, so it needs its own calibrated bars. Do these in order; each lands
on origin/main before the next starts.

1. **The X7 placebo sweep on the corrected panel** — `DECISION_canonical_universe.md` §"My
   recommendation" item 1 (`python -m scripts.placebo --panel UNIVERSE_BIAS_PANEL_full.pkl --n 100`,
   ~8 hours). It reads the local 2026-10 freeze, so it does not depend on the live Sharadar
   subscription. Same seeds and instrument as X7/session 10, all 100 draws retained (rule 9), the
   trial count it ran at recorded. Report all seven floors beside the current ones, and the
   corrected headline against them. Zero trials (calibration). **Do NOT move the canonical panel
   and do NOT change any public page** — that is Don's decision and is pending.
2. **Re-measure the eight claims `UNIVERSE-BIAS` part 2 listed as UNMEASURED** on the corrected
   universe (R1's factor alpha, S22's term structure, score_confidence, hold_horizon, payoff, V6-B,
   the Index tab's backtested column, and what the live Track Record can be compared against),
   each against the new floors, in the three-state vocabulary (SURVIVES / NO LONGER HOLDS /
   UNMEASURED). The Index tab's column is the priority: if INDEX-BOOK's fidelity gate refuses the
   new panel, build the corrected Index-book figures as a separately labelled object rather than
   weakening the gate. Write the result as one table Don can read.
3. **The dated IBES link** that `STAGE1-BATCH1` A9 handed forward, built and validated as an
   instrument (MB15) before any hypothesis reads it. WRDS: one connection attempt per session, no
   retries. If WRDS refuses, record it and stop that item.

Then continue with whatever the scout's batch-2 register (when it lands) asks of you.

Done means on origin/main, with a plain-words summary for Don.
