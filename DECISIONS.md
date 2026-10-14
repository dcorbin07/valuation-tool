# DECISIONS.md — Don's rulings, in one place

**Every lane reads this before starting work. One line per ruling, dated, newest first. A ruling
here overrides any older prose in a handoff or prompt. Only Don changes a ruling; a lane that
thinks one is wrong says so in its handoff and keeps obeying it.** Maintained by the Cowork
manager from Don's own words in chat.

## Research method

- **2026-10-06 — NO CAP ON TESTS. The twelve-arm cap in `RESEARCH_CHARTER.md` §5 is REMOVED.**
  Test everything that makes sense. Fluke risk is handled by COUNTING every test (the research
  log, the Harvey-Liu-Zhu hurdle, the deflated Sharpe), by Benjamini-Hochberg across a batch,
  by the both-halves rule, by blind pre-registration committed alone, and by staged confirmation
  (build quadrant → one read of the check quadrant → one read of the 1999-2008 proxy → forward
  paper book) — never by refusing to run a test. "It might be luck" is a reason to confirm, not
  a reason not to test.
- **2026-10-06 — ADOPT WHAT PASSES.** Anything that passes every stage above goes to Don as a
  candidate for the next rebalance, with its expected return quoted at half its backtested size
  (McLean-Pontiff). Nothing is adopted by a lane; adoption is Don's and is a vintage event.
- **2026-10-06 — THE STANDING DISCIPLINE DOES NOT RELAX AS THE PROJECT MATURES.** Both-halves
  (since 2026-07-30), pre-committed margins (since 2026-07-31), blind registers committed ALONE
  (since 2026-08-03), placebo-calibrated bars (since 2026-08-05), trial counting (since
  2026-08-05), the X1 name split (since 2026-08-13) and the forward contract (since 2026-08-09)
  all stay exactly as they are.
- **2026-10-06 — TIERED POOL** (stricter score hurdle for smaller companies, with and without a
  junk filter) is to be tested by r1 under a blind register, on the corrected full-universe
  panel for 2009-2026 and the 1999-2008 five-theme proxy. (TIERED-POOL, 2026-10-07: both arms
  failed on 2009-2026 on return and drawdown; the incumbent stays.)
- **2026-10-07 — MOVE THE CANONICAL BACKTEST TO THE CORRECTED UNIVERSE AND RESTATE ONCE.** After
  r1's full rebuild of the corrected panel, the canonical backtest moves to the corrected full raw
  universe and the public pages (/proof, /methodology, the Index tab, the landing tiles) are
  restated once from it — the DEPLOYED equal-weight book, never the CPCV-adopted one — including
  the deeper Index drawdown and replacing the "not a survey of survivors" sentence. No interim
  patch. The flat 1/7 weights stay: CPCV adopting a scheme does not change them (prove before
  changing). The forward contract's frozen meter parameters are not touched.
- **2026-10-13 — THE FLEET RE-CERTIFIES ITSELF WHEN THE ONLY PROBLEM IS A STALE CERTIFICATE.** The
  daily fleet cycle runs the self-check automatically when the certificate is stale because the
  harness code changed (SELFCHECK_STALE / SELFCHECK_ABSENT). If the self-check FAILS, the books
  stay shut and Don is alerted — a failing check is never re-run into a pass. Paper only.
- **2026-10-12 — AN OPTIONS STRATEGY IS JUDGED AS ITS OWN SYSTEM, NOT AGAINST THE INDEX OR THE
  SHARES.** The Valquo Index is an equity book (ETF-like); options trading is a separate system,
  shown separately and paper-traded separately from the Index record. So SELL-PREMIUM's pass rule
  has no "return given up versus holding the shares" margin. It passes if, under the standing
  discipline: it is profitable net of realistic costs on the capital it ties up, in both halves; it
  beats the same trade placed on random days in the same names (so the timing is shown to matter);
  it survives realistic sizing and concurrency (O11) and the pre-committed crash stress. The
  comparison with simply buying the shares is REPORTED for context and carries no verdict.
- **2026-10-10 — HOW THE CANONICAL-MOVE RESTATEMENT PRESENTS THREE FIGURES** (from r1's
  `CANONICAL_MOVE_TABLE.md`):
  1. **The Index tab drops "alpha vs the all-cap equal-weighted universe".** On the corrected
     universe that benchmark falls (17.24% → 12.11%/yr), so the comparison would jump −0.06pp →
     +5.93pp without the Index improving. The Index is shown against SPY and against the
     equal-weighted $10B tier — like for like — with its return, drawdown and Sharpe beside them.
  2. **/proof shows the placebo result as it is**, even if the real result beats all 100 noise
     runs on every measure — provided the noise draws come from the SAME corrected panel and the
     page states that the old and new panels share no rebalance dates and keeps every bar it
     cannot score (PBO, deflated Sharpe) visible as unmeasured. The page's guard is changed to
     require a like-for-like comparison, not at least one failure.
  3. **The research decile's result vs SPY is shown plainly**, including that it is −1.14pp/yr
     net of costs on the corrected universe. No "beats SPY" claim anywhere, as before.
- **2026-10-08 — TRADIER IS CLOSED AND WILL NOT BE FUNDED AGAIN.** Don withdrew his funds and
  Tradier deactivated the account. Every feature that used Tradier moves to another source: free
  sources first, then a free official API (Alpaca's free tier is the candidate, measured before
  use). Robinhood cannot be used — no official equities/options data API — and no lane ever stores
  Don's login or keys; Don enters any key himself.
- **2026-10-08 — INTRADAY SIGNALS STAY ON GITHUB'S FREE SCHEDULER** (no paid Render cron). They
  feed the Signals tab, alert emails and the live options record, which research shows lose to
  random entry; afternoon-only delivery is accepted. The live check keeps reporting honestly.
- **2026-10-08 — DIP DETECTOR'S 52-WEEK HIGH STAYS ON THE SPLIT- AND DIVIDEND-ADJUSTED BASIS**
  (consistent with the V6/V6-B research and immune to the split trap), labelled on the page as a
  drop that includes dividends.
- **2026-10-08 — DEVELOP A PROFITABLE OPTIONS STRATEGY: "calls after a sharp drop in a strong,
  liquid company" is authorised as a research program** — stock-level bounce first, the option
  expression only if the bounce survives, then a forward paper book. Same discipline as all
  research; no real trades.
- **2026-10-07 — DIP DETECTOR: show banks, insurers, REITs and regulated utilities in their own
  group, labelled "health not scored for this kind of company".** Never counted as healthy, never
  silently excluded.
- **2026-10-04 — PROVE BEFORE CHANGING.** No construction change to the Index until the
  alternative is tested on data it was not tuned on and Don has approved in chat. Alternatives
  stay built and switched off. The 2026-10-22 rebalance uses the incumbent construction.
- **2026-10-04 — WIDEST POOL IF THE EVIDENCE HOLDS.** Don prefers the largest pool whose
  evidence survives; liquidity is not a constraint for a personal Roth. (UNIVERSE-BIAS,
  2026-10-06: on the corrected universe the wider pool does NOT survive; the incumbent stays.)
- **2026-10-03 (Addition 2) — new research is built on 2009-2019 × one fixed ticker half, checked
  ONCE on 2020-2026 × the other half; the frozen model is read ONCE per pre-2009 era.**
- **2026-09-30 — the free live data route is the goal; Sharadar is the fallback, rented around
  rebalances. (D9 and D9-SAMEDATE: the free route is NO-GO today, so rebalances use Sharadar.)**

## The Index and the record

- **2026-10-04 — Amendment 2 to `PAPER_TRACK_CONTRACT.md` ACCEPTED** (corrected power statement,
  dated note, and the corporate-action rule: a held name that is acquired or stops trading
  counts as sold at its last traded close, its weight redistributed pro-rata).
- **2026-10-02 — ONE Valquo Index.** A fixed book formed at the quarterly rebalance and held
  until the next; that same book is what the forward record measures. Hot stocks and options are
  daily; the Index is not.
- **2026-10-02 — the Index is whatever construction gives the best NET return in a Roth;
  taxable after-tax figures are shown for transparency only.**
- **2026-10-02 — NO "+32%" and NO "beats SPY" claims anywhere.** Any research-decile figure on a
  public page must say in the same sentence that it is not the Index and name its universe.

## The valuation page

- **2026-10-13 — NO MORE BUY / HOLD / REDUCE LABELS ON THE 1-100 SCORE.** The labels were never
  tested against returns, and they put "Buy" on businesses the model says are overpriced (NVDA
  read 79 / Buy at −36% upside, because valuation is only 20% of its weight). The page shows two
  separate reads in plain words instead: how good the business is (quality, growth, health,
  momentum) and how the price compares with the model.
- **2026-10-13 — EVERY NAME LEADS WITH WHAT THE PRICE ASSUMES** (the growth the market price
  implies, against what the business grows today). For hypergrowth, cash-burning and story stocks
  — TSLA included — the page says plainly not to use the DCF fair value to decide. The hot score
  is shown beside these reads with its drivers and its limits (its evidence is about the top
  decile as a group; the size theme marks megacaps down by design). A plain description of the
  company opens the page.
- **2026-10-13 — THE AI ANALYSIS RUNS AUTOMATICALLY,** in the background after the numbers
  appear, saved per ticker per day, under a daily cap Don sets (the lane measures the cost per
  call first). It is labelled as written by AI from the page's numbers, not from news, and it
  gives no buy or sell recommendation.
- **2026-10-13 — THE VALUATION PAGE'S READS ARE RECORDED FORWARD, SO THEY CAN BE TESTED.** They
  cannot be rebuilt for past dates, so a weekly append-only record is the only way to learn
  whether "price vs our model" or "business quality" predicts anything. The test is registered
  blind before the first row is recorded. Also queued: Index rows link to each name's valuation
  with a "why is this held?" breakdown; recent earnings and headlines on the page and in the AI
  analysis; the fair value at an ordinary discount rate beside the headline, and plain definitions.
- **2026-10-13 — THE LIVE SCAN'S MISSING DATA IS FIXED ON THE FREE ROUTE, AND IT IS A REPAIR, NOT
  A VINTAGE EVENT.** FMP is unpaid and is taken out of the fetch chain (not renewed); a name whose
  fetch failed is retried on Yahoo; a name scored on too few themes is marked as such and is not
  ranked at the top of the hot list. No scoring rule changes — inputs the rules already expect come
  back — and the Index record is built from Sharadar, not the live scan, so vintage 4 stays open.
- **2026-10-13 — RESEARCH QUEUED:** SELL-PREMIUM-3 (the put-spread version) after SELL-PREMIUM-2's
  stage 2; clustered insider buying tested in SHARES (F-15's options form is dead on arithmetic);
  and a test of an adjusted beta against the vendor's raw beta before any change to the valuation
  engine.
- **2026-10-13 — HEADLINES MAY COME FROM ANY VERIFIABLE, TRUSTWORTHY SOURCE, NOT ONLY SEC AND
  YAHOO.** The line is between a conclusion and a narrative: a reported fact or a conclusion
  attributed to someone (guidance, an analyst's rating change, a regulator's decision, a press
  release) is allowed; opinion and promotional pieces ("should you buy", "3 reasons it will soar",
  price-prediction hype, paid promotion) are not. Every headline names its source and links to it.

## How Don works

- **2026-10-13 — KEEP THE MANAGER'S FILES OFF GITHUB.** Don is not asked to run `git_push.bat`
  unless something would break without it. Lanes read this file and their prompts by absolute path
  in the main folder (`C:\Users\donni\Downloads\valuation-tool\`), so they see rulings that have
  not been pushed; a lane's own worktree copy of this file can be out of date. To bring the main
  folder up to date without publishing anything, use `git merge --ff-only origin/main` rather than
  `sync.bat` (which banks uncommitted edits to a `rescue/` branch on GitHub).
- **2026-10-04 — Don does not create or edit files on GitHub.** Changes go through a Claude Code
  lane, a .bat file he double-clicks, or — for `.github/` files, which the land gate refuses to
  lanes — `data/pending_workflows/<name>.yml` plus `install_workflows.bat`.
- **2026-10-04 — Sharadar renewed for one month (to ~2026-11-03).** Anything that needs it is
  done before then; r1 keeps a verified full freeze (`data/backtest_freeze_2026-10`).
- **2026-10-04 — WRDS restored.** Script access from Don's PC lasts ~30 days per MFA web login;
  one connection attempt per session, never a retry loop (repeated failures disabled the account).
- **Standing security rules:** never read, print or overwrite `.env`; never print the admin
  token (Don enters it masked); no real trades or orders, ever; `data/` is never committed; no
  backfill of the forward record; findings in chat, not in a lane's terminal only.
- **2026-10-06 — written records resume.** Lanes keep writing their handoffs, the ledger and the
  research log. The manager keeps this file and saves every lane prompt as `PROMPT_<lane>_<date>.md`.
