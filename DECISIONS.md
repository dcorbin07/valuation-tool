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
- **2026-10-13 — SELL-PREMIUM-3 IS SHELVED — PENDING THE CORRECTED STAGE-2 READ.** Don shelved it
  because SELL-PREMIUM-2 read as failing its check (−9.26%/trade). **That read is VOID** (found by
  the manager the same evening): stage 2 settled every expiry after 2020-12-31 at the ticker's last
  2020 price, because it imported stage 1's spot maps (built over 2016-2020) — GE at $10.80, AAPL
  at $132.69, NVDA at $522.20 on every assigned trade, 73% of the book. The options lane repairs
  and re-runs it; if SELL-PREMIUM-2 then passes, SELL-PREMIUM-3 comes back to Don. Its draft
  (`a1d37ff`) is kept; no register, no trials. F-21/F-22 stay armed on paper as forward records.
  For any options strategy the staged ladder has three rungs (build → one check read → forward
  paper book), because no options data exists before 2016.
- **2026-10-13 — CLUSTERED INSIDER BUYING GOES TO A WIDER-TIER TEST.** It cleared every bar on the
  full universe in the build quadrant (+2.09pp market-adjusted over the next quarter, about +1.8pp
  net of the size tilt) and could not be resolved on the $10B+ tier, which governed that register.
  A new register with a wider tier governing and realistic size-tiered trading costs is written
  BEFORE the one check-quadrant read, and that read is taken once.
- **2026-10-14 — ALPACA REPLACES TRADIER: PAPER FOR EVERY PAPER BOOK NOW, AND THE SIGNED §8
  LIVE PATH IS BUILT ON ALPACA, SHIPPING AT 0%.** Don opened Alpaca (Trading API, not Broker
  API). Paper keys drive the paper books; Alpaca's paper fills match against the real-time
  national best bid and offer, closer to reality than the Tradier sandbox's 15-minute-delayed
  data. Don's instruction in chat: build the percentage-of-portfolio real-money path he signed
  as `PAPER_TRACK_CONTRACT.md` §8 (2026-09-02), on Alpaca because Alpaca allows fractional
  shares and Tradier did not, and start it at 0% until he is comfortable switching it on.
  **Correction to his recollection, recorded so it is not repeated:** that path was signed but
  never built. It was refused twice (2026-09-02 and 2026-09-15, `LIVE_PILOT_BLOCKED.md`), and
  whole shares at Tradier left 51 of 68 names at zero shares on a $5,000 book. §8 keeps all its
  rails; only the execution container moves to Alpaca. Don enters every key himself and
  only he ever raises the percentage above 0. Paper keys go on Render now. Live keys go on
  Render only, never on GitHub or in a local `.env`, and only after the §8 auditor review has
  landed. **Many accounts, by numbered slot** (Don, same day): each slot is
  `ALPACA_ACCOUNT_<n>_*`, discovered automatically, and slot 1 is Don's. A new slot starts at
  0%. A slot other than 1 cannot arm until the contract records that holder's own signed
  authorization (§8's family-slot rule). **Fully disciplined, no loss stops** (Don, same day):
  each slot holds the Index book at its percentage of the account's equity, worked out stock by
  stock. It buys and sells only at a quarterly rebalance or when its percentage changes; 0 to X
  buys in, and X to 0 sells out. Nothing else happens, and §8's loss-stop requirement is removed
  by his instruction. `LIVE_PILOT_ENABLED=0` pauses every slot without selling. **If anything
  is broken or wrong** — unreadable book, missing price, unreadable account, orders that don't
  match the math, a broker error — that slot doesn't trade that cycle, alerts Don, and tries
  again next cycle. An error never sells.
- **2026-10-14 — ALPACA BECOMES THE PRIMARY PRICE SOURCE WHEREVER IT MEASURES AT LEAST AS
  GOOD**, with the current routes as fallbacks (item 59). Measure first, on `ALPACA_SETUP.md`'s
  222-name sample. The Index record switches at a segment boundary, with base and mark from one
  vendor and the seam recorded; that is a price-vendor change, not a vintage event.
  Fundamentals, descriptions and earnings dates stay on Yahoo plus SEC, because Alpaca does not
  carry them.
- **2026-10-15 — INSIDER CLUSTERS: THE 1999–2008 RUNG IS UNOBTAINABLE; F-23 MOVES TO SEC
  INSIDER IDS, CHECKED FIRST.** r1 measured the older-data rung. Free data starts in 2008, giving
  31 events at 6.3% power. Raw SEC filings would add only 2006–2007, and pre-2003 filings were on
  paper. The rung is recorded as unobtainable and nothing is purchased. The forward paper book is
  the remaining test. F-23 cannot fill on the licensed file, which is a frozen snapshot, and the
  SEC's free feed counts insiders differently because the licensed file has names only, no IDs.
  So the rule is re-measured on the SEC's insider ID numbers on the 2009–2019 build data only,
  with stage 1's bar. F-23 moves to that rule only if it clears.
- **2026-10-16 — F-4 AND F-10 ARE NOT RE-DECLARED YET.** Both avoid scheduled earnings, and the
  event spine holds no forward dates, so they could not enter. They are revisited once a free
  forward earnings calendar is measured. Next for options: Don adds the fleet's second Alpaca
  paper account, which lets F-21, F-22 and F-8 trade; EARNINGS-CSP's free kill; the
  forward-calendar measurement; and F-21b's rule frozen before F-21's first fill. MB2's single
  cell and the cap-3 sizing test wait for Don.
- **2026-10-18 — HOW THE LIVE SLOT SPENDS CASH (Don, chat; item 73).**
  1. **Buys are spread proportionally** across every stock in the book when cash is short, never
     filled stock by stock.
  2. **The shortfall stays open until filled**, measured against that event's own per-name targets
     frozen when it opened, never re-derived from daily equity. New cash tops it up, never past
     the targets. A new rebalance or a percentage change replaces it.
  3. **No cash budget or cap**: the slot uses whatever spendable cash exists, up to its frozen
     targets, and never sells anything it did not buy.
  4. **A top-up happens only when at least $250 can be bought.** It is ONE universal setting,
     `LIVE_MIN_TOPUP` on Render, for every live slot and the paper slot; there is no per-account
     setting. Don can change it. Smaller names that fall under the $1 order minimum lag and
     catch up later, which Don accepts.
  5. **"Waiting for cash" is a normal state:** one plain alert, and no ceiling burn.

  The auditor reviews item 73 before any percentage above 0.
- **2026-10-24 — SHARADAR IS NOT RENEWED IN NOVEMBER (Don, chat).** Access lapses around
  2026-11-03 and that is fine. Don renews around January only if the 2027-01-25 rebalance needs it.
  The manager and the lanes do not raise renewal again before then; the January runbook's §0 is
  settled by this entry.
- **2026-10-24 — CORRECTION TO THE ENTRY BELOW (manager's error; found by item 81).** The
  recorded 10-22 book was scored on **2026-10-02 market caps and 1,835 names**, not 10-22 caps
  on the ~2,038-name universe. Two causes: the freeze's caches had never been rebuilt from the
  10-23 export, and the manager's one-off script left out the runbook's `--limit 4000`. A fully
  correct build shares 70 of the 81 names, and the shared weights differ by at most 0.0029. The
  record is append-only, so the recorded book stands and is not re-derived; it conformed, and it
  is not a vintage event. Item 81 fixes all three causes for 2027-01-25.
  - **Added 2026-10-27 (manager, measured):** the book's fundamentals, insider and 13F files were
    also the 10-04 export's (filings through 10-02). The 10-23 refresh downloaded new raw files
    but rebuilt none of them: its manifest records zero rows derived. In the 10-23 raw SF1, 230
    companies filed a quarter between 10-03 and 10-22; 69 of them are $10B+, and 5 are in the
    recorded book (GGG, JEF, MEDP, MU, SYF). Item 84 fixes this for January.
- **2026-10-23 — THE 2026-10-22 REBALANCE IS RECORDED** (HTTP 201, 81 positions, Path B on the
  refreshed Sharadar export, built `--as-of 2026-10-22`, incumbent construction, not a vintage
  event). 49 names kept, 32 added, 37 dropped; the 30% band retained 27. Built with the
  manager's one-off `rebalance_build_2026-10-22.py`, which took the market-cap and 13F caches
  from the 2026-10-04 freeze because the July caches were three months stale. Two door bugs were
  fixed on the night (items 80 and 80b). The next rebalance is dated 2027-01-25; item 81
  prepares it. Sharadar renewal timing: see the 2026-10-24 entry above.
- **2026-10-22 — FAIR VALUES FAR BELOW PRICE (Don, chat; item 79).** A fair value below 0.5x
  price is never labelled "high confidence"; its confidence is capped one level down. This is a
  display judgment, not a measured threshold, and nothing is hidden or revalued. The loud flag
  below 0.2x stays.
- **2026-10-22 — THE SIX-MONTH CHECKPOINT MOVES TO MARCH (Don approved the direction; he signs
  the text).** Amendment 4 is to be drafted: the operational-gate window starts 2026-09-23, when
  the daily writer became gapless, so the gate date becomes 2027-03-23. The 11 missed days stay
  as visible gaps and are never backfilled. The gate's outdated cost figure is replaced with the
  served Index's own. The 2031 verdict date and the frozen meter do not change.
- **2026-10-22 — AUDITOR'S NINTH REVIEW: SAFE TO RAISE ABOVE 0% WHEN DON CHOOSES** (`fb78445`,
  after items 77 and 78). Going live still takes three steps, all Don's: a lane hands over a
  `live-cycle.yml` that sends `?run=1` (installed with `install_workflows.bat`), then
  `LIVE_PILOT_ENABLED=1`, then raising `ALPACA_ACCOUNT_1_LIVE_PCT`. The manager's advice: wait
  until the paper slot has carried out the 2026-10-22 rebalance cleanly, and start small.
- **2026-10-22 — EODHD FUNDAMENTALS DATA FEED (Don bought it; PERSONAL plan, ~1 month).** Key in
  the local `.env` as `EODHD_API_KEY` only; never on Render or GitHub. The personal licence
  forbids displaying or redistributing the data, so nothing from EODHD reaches valquo.co, the
  public repo or `data_export/`; raw rows live under `D:\eodhd\`. r1 runs a census, harvests
  everything useful into a dated freeze, and checks before Sharadar lapses (~2026-11-03) whether
  EODHD reproduces the 10-22 book. Switching the rebalance vendor, or any use on the public
  site (which needs a commercial licence), is Don's decision.
- **2026-10-21 — AUDITOR'S EIGHTH REVIEW: NOT YET** (on `worktree-auditor-live-path-review`).
  Item 73's cash arithmetic is correct, but three blockers stand before any percentage above 0:
  (A) a missing or misnamed percentage variable is read as 0% and sells the book; (B) each
  percentage event works only once, and a second 0% can silently do nothing; (C) a price move
  inside an open event still trades the difference. Item 77 fixes them, then review 9. The live
  slot is at 0% and holds nothing, so none of this can act today.
- **2026-10-21 — FIXES FROM THE OUTSIDE REVIEW (Don, chat; item 76).** Restate stale figures and
  claims on public pages and docs from the tracked artifacts. A fair value below 0.2x price is
  flagged loudly, never hidden. The valuation page shows how much the fair value moves with beta
  (vendor beta and +/-0.3). Lists show score bands (e.g. "top 10%" plus the driving themes)
  instead of two-decimal scores, because position inside the top decile is no better than chance.
  Every score says how many of the seven themes fed it, and below seven it is labelled "not the
  backtested model". No change to scoring, ranking, the fair-value math, the Index or live trading.
  The valuation-engine model changes the review proposed wait for Don, each as its own tested
  change.
- **2026-10-18 — ALERTS GO TO DISCORD (Don, chat; item 74).**
  1. **Anything breaking, and any rebalance that cannot happen or is late, posts to a separate
     `#valquo-alerts` channel** (`DISCORD_ALERT_WEBHOOK_URL`). Routine posts (recaps, order
     fills) stay on the existing channel.
  2. **A free outside monitor (healthchecks.io, `HC_PING_KEY`) alerts the same channel if a key
     job never runs at all.**
  3. One post when a problem starts, one when it clears, and a daily reminder while it stays
     broken. No P&L or returns, and never a key, token, webhook or account number.
  4. Don creates the channel, the webhook and the healthchecks.io account, and enters every URL
     himself on Render and GitHub. Messages change; trading does not.
- **2026-10-18 — AUDITOR'S SEVENTH REVIEW: LIVE KEYS MAY BE ENTERED AT 0%** (`4d6f09e`); **DON'S IRA
  KEYS ARE IN.**
  - **What the auditor found:** for the first time, no route by which the path loses money,
    trades without authority, trades twice, or records a conclusion without evidence. Item 71
    fixed the 0% sell-out (sell-only, slot-owned shares only; hand-held shares untouched), the
    shared close, and writes on cycles that never read. Its 2,240-row transition table found
    1,641 wrong rows before the fix.
  - **What `/admin/live-slots` showed at 03:09Z:** slot 1 ("Donovan") has both keys present, 0%,
    `LIVE_PILOT_ENABLED=0` so paused, not armed, 0 holdings, and isolation ok.
  - **Going live** takes three separate steps, all Don's: set `LIVE_PILOT_ENABLED=1`; hand over
    and install a `live-cycle.yml` sending `?run=1`; raise the percentage. The recommendation is
    to wait until the paper slot has carried out the 2026-10-22 rebalance cleanly.
  - **Item 72** handles the non-blocking leftovers: a stale `open_event` message, five unchecked
    combinations, and watching the paper rebalance.
  - **Fractional shares in the IRA** are still unconfirmed. At 0% nothing reads the IRA, so Don
    checks the Alpaca app's dollar-amount ticket on the IRA by hand.
- **2026-10-17 — AUDITOR'S SIXTH REVIEW: NOT YET** (`439eef1`). Item 70 closed the fifth blocker
  in all four cases. Three new blockers:
  - **(A) The X→0 sell-out cannot execute on a live slot at all.** `armed()` refuses at 0%, so
    Don's documented way out does not exist. The global pause still works, and it does not sell.
  - **(B)** A second event's close clears the first event's remainder.
  - **(C)** Paper, dry and GET cycles write state and close events for a live slot whose order
    read was never attempted.

  Item 71 fixes all three, and builds one table-driven test of every slot state × event × read
  outcome × mode × pilot combination, instead of a seventh patch. Item 70 landed, and Amendment 3
  was SIGNED by Don, effective 2027-01-25.
- **2026-10-17 — AUDITOR'S FIFTH REVIEW: NOT YET** (`6b84008`). Item 69 closed the fourth blocker.
  The new one: since item 67 subtracts this slot's own resting orders, an empty plan can mean
  "orders still working", but the close branch reads it as "targets met". So an event closes while
  orders rest, they expire, and nothing retries. **At a 0% sell-out the slot would stay fully
  invested at a declared 0%.** Item 70 fixes it before the 10/22 rebalance; then the auditor
  reviews a sixth time. **Workflows reinstalled 2026-10-17** (`2dc5496`), after Don fast-forwarded
  the main folder: the five-cron `live-cycle.yml` and the 12:00Z `fleet-cycle.yml` now match the
  pending copies. The first install had used a stale local copy. **Amendment 3 (spin-offs) is
  drafted, effective from segment base 2027-01-25, and awaits Don's signature;** unsigned, the
  record is bit-identical.
- **2026-10-17 — LANES: DO NOT EDIT THIS FILE.** It is the Cowork manager's record of Don's rulings.
  Lane entries pushed to `origin/main` collide with the manager's uncommitted copy in the main
  folder and block Don's `git merge --ff-only`. Report rulings and results in your handoff; the
  manager records them here.
- **2026-10-17 — ITEM 69 AND THE WORKFLOW REPLACEMENT LANDED; INSTALL IS SAFE.** An exit the feed
  cannot price now keeps the event open, alerts and retries. Both pending workflows (`live-cycle.yml`
  with five crons, and `fleet-cycle.yml` at 12:00Z) replace their installed files by name, so one
  `install_workflows.bat` run leaves one schedule each. The fleet's paper keys and its dedicated
  account are confirmed in use.

  **SPIN-OFFS (item 69 part 2):** a held name that spins something off would book a FAKE loss in
  the record, and Amendment 2 cannot catch it, because the parent keeps trading. The proposed fix,
  a contract amendment and Don's decision: a distribution is RECEIVED; measure it against the
  parent's price plus the distributed value, stored on the row. The book in force holds none of
  the named names (MSGS, KBR, FLEX, GPC, CMCSA). The 10/23 rebalance task now checks the new book
  for them.
- **2026-10-17 — AUDITOR'S FOURTH REVIEW: NOT YET** (`e345bb2`). Question 6 (duplicate orders)
  passes for the first time. The new blocker: an exit the free feed cannot price is dropped in
  silence and the event closes as "targets met" (item 69). The auditor cleared the five-cron
  `live-cycle.yml` as safe, but Don installs only after the options lane turns
  `fleet-cycle-in-hours.yml` into a same-name replacement, because installing both would add a
  second fleet schedule. Item 68: Alpaca and yfinance each restate different corporate actions,
  and yfinance, the incumbent, left Aptiv's and Unilever's spin-offs as cliffs. The 0.98 bar
  compared two conventions that were never the same, and it is not changed. Item 69 checks what a
  held name's spin-off does to the bound record. The options lane re-anchored F-21/F-22, fixed the
  clock that kept every entry rule blind, and declared F-4b (25 delta, 9-day earnings buffer).
- **2026-10-17 — LEVERAGE PROJECT (separate from Valquo, `Market Rotation\leverage`): NOTHING
  SURVIVED.** 28 rules were built on US 1963–2026 and checked once on 9 unseen countries and US
  1926–63. Don's dip rule, the headline and news rules, and 3x all fail. The published 200-day rule
  beats holding in only 4 of 9 countries and loses in Japan. At half its edge it earns +0.4 points
  a year for a −55% drop. The one build-set winner (growth-trend timing) broke the drawdown limit
  on unseen data (the 1962 crash). SSO is the cheapest fund by measured total cost; the fee is the
  smaller part of the cost. The unseen data is now spent, so a re-run with a new bar would not be
  a fresh test.
- **2026-10-17 — THE ALPACA PRICE SEAM DID NOT PASS; THE INDEX STAYS ON ITS CURRENT PRICE SOURCE
  FOR 10/22.** The pull was complete (217 names, 58,318 bars) once Don replaced stale paper keys.
  - **Adjusted closes agree at 0.9020 against the declared 0.98**, while as-traded closes agree at
    0.9915. The worst rows look like spin-offs and listing changes.
  - **The leg against the recorded Index never ran**: SPY could not be priced at inception.
  - `PRICES_PRIMARY_ALPACA` stays unset. Item 68 explains both failures without changing the bar,
    and the next possible switch is the January rebalance.
- **2026-10-17 — ITEM 67 LANDED; THE FLEET IS UNBLOCKED BY REMEDY (b); F-4 IS RE-DECLARED.**
  Item 67 landed, covering the stacking fix, pagination, settlement waits, a trading-day ceiling,
  fractional reads, and one more fix: a name leaving the book had never been sold. The auditor
  reviews it a fourth time. The pending workflows are still not installed.

  F-21 and F-22 were blocked by a hash chain broken when their declarations were amended after
  the first record. Remedy (b), continuing the sequence at high-water + 1, is approved, along
  with a guard against it happening again.

  A free forward earnings calendar exists. Yahoo gives future dates for 91% of the 487 optionable
  names, and dates drift by up to about a week. So F-4 is re-declared at 25 delta, 30 DTE, with a
  buffer of at least 7 days and names without a date refused. F-10 stays retired.

  EARNINGS-CSP stops: its free kill was unresolved (0.6486 against 0.65, and 0.7358 at matched
  tenor). F-21b's stress gate was frozen before F-21's first fill. The fleet's paper account is
  recommended at $250,000, which covers 25 concurrent cash-secured puts at the median contract.
- **2026-10-17 — AUDITOR'S THIRD REVIEW: STILL NOT YET** (`bff4532`). Its last blocker is closed,
  but a new one arrived. Re-sending an unfilled remainder adds to the order still resting instead
  of replacing it: reproduced at up to 5x the target, and the pending five-cron schedule would
  make that a routine day. Order-list pagination is also needed within about two rebalances. Do
  NOT install the pending workflows until the app fixer says the fix is on main. The fix goes
  first in item 67; the auditor reviews it and item 67 together. Item 65 part 5 (the seam's
  evening `end`) landed, so the price check can run.
- **2026-10-17 — DON'S IRA IS OPEN; KEYS GO IN AT 0% ONLY AFTER THE AUDITOR'S YES.** Don's
  instructions:
  - **A rebalance waits for settlement.** Sells go first, buys are sized only to cash that needs
    no borrowing, and a buy refused for unsettled cash is retried the next trading day without
    an alarm. Don is alerted only if the wait outlasts T+1 by a full trading day.
  - **Fractional shares in the IRA are checked read-only.** Alpaca documents fractional shares
    for its accounts but not for IRAs. The definitive test is a $1 buy that Don makes by hand,
    or not.

  Item 67 does both, and the auditor reviews it before any percentage above 0.
- **2026-10-16 — THE OPTIONS PAPER FLEET HAS NEVER TRADED, AND FIXING THAT COMES FIRST.** Its
  broker is still the Tradier sandbox, and Tradier closed on 10-08. In the last fleet backup
  (10-04) no book had recorded a single order, only self-checks. Since a forward paper book is
  the last rung for every options strategy, the options lane moves the fleet onto Alpaca paper
  before any new options test. Don asked for an options edge "as long as it isn't super
  expensive". The scout drafts the remaining candidates and ranks them: earnings-spanning
  cash-secured puts (O7 found earnings options rich, and that has never been tested from the
  selling side), a stress gate for put selling judged forward, a census only for O-1's data,
  and the DTE question answered from the record. The alert-driven long-call entry is not
  re-opened: it loses to random days in every score band and at every threshold.
- **2026-10-17 — DON APPROVES THE SPIN-OFF RULE; AMENDMENT 3 IS DRAFTED FOR HIS SIGNATURE AND
  IMPLEMENTED DORMANT.** Item 69 measured that a held name spinning something off would book a
  **fake loss** in the bound record — the vendor left Aptiv's spin-off as a −10.58% cliff and
  Unilever's demerger as −7.03% — and that Amendment 2's corporate-action rule cannot reach it,
  because its trigger is "acquired or stops trading" and a spin-off is the one action where the
  name keeps trading. **The rule: a distribution is RECEIVED, so the holding is measured against
  the parent's price PLUS the distributed value per parent share at the distribution date, with
  that value stored at the time.** `PAPER_TRACK_CONTRACT.md` **§5a-3**, and **the signature row
  reads NO** — `index_mark._amendment_3()` parses it on every mark through the same parser the
  operational gate uses, so **unsigned the record is bit-identical**, pinned by test. Anything that
  is not a clean signature is not one (blank, `pending`, hedged prose, or two rows disagreeing),
  and **signed with no effective date is NOT in force**, because that would reach recorded rows.
  **Effective from segment base 2027-01-25** — derived from `next_rebalance("2026-10-22")` rather
  than typed, and deliberately January rather than the 10-22 boundary five days away: a signature
  landing after a boundary would switch the rule on part-way through a segment whose earlier marks
  were recorded under the old one. **No backfill, and it is structural**: the credit window is
  `base < distribution <= mark`, so a segment that opened before the effective date cannot be
  touched — and there is nothing to backfill, both measured cases predating the 2026-07-30
  inception. The value is declared in tracked source (`index_mark.DISTRIBUTIONS`, empty today)
  following `EXITS`'s idiom, because committed source is "stored at the time". **It claims nothing
  about what the distributed shares did next**, in Amendment 2's own terms. **A known gap, named
  in the amendment: nothing watches for a distribution** — the entry is made by a human who
  noticed, and item 68's `classify_disagreement` on the book since inception is the detector, which
  is the same measurement already routed to Don. **Not a vintage event; no clock, σ or threshold
  moved; Amendment 2 untouched.**
- **2026-10-17 — ITEM 69: AN UNPRICED EXIT WAS DROPPED IN SILENCE (the auditor's fourth blocker,
  and item 67's own fix half done); AND A SPIN-OFF WOULD BOOK A FAKE LOSS IN THE RECORD.** The
  auditor reproduced it through `run_cycle` with the real broker: the slot knows MSFT must go,
  cannot price it on a one-sided IEX quote, **sends nothing, raises no alert, records the
  rebalance COMPLETE, and reports "1 of 1 priced, missing: none"** — indistinguishable from a
  healthy day on every surface Don reads. §8 requires no-trade, an alert and a retry; only the
  first happened. **Three places computed "the names this cycle cares about" from the book's held
  positions and item 67 widened only the quote list** — and an exit is by definition not in the
  book's held positions. One definition now (`tradable_names`), read by all three, scoped to the
  slot's own record so it can never reach Don's other holdings. **And the close branch tested `not
  plan["orders"]`, which is true of both "nothing to do" and "I could not work out what to do" —
  the third collapse of two epistemic states on this path**, so the planner's outcome is now a
  value from a declared set and exactly one of them closes an event. Two defects in my own first
  cut: it refused the whole cycle for any skip, which would have reverted item 67's per-name
  granularity that the auditor endorsed; and `exits_planned` vanished from the refusing cycle,
  losing the diagnostic that made the blocker legible. 17 of 20 new tests fail on the old code.
  **PART 2, REPORTED AND PROPOSED, NOTHING CHANGED: a held name that spins something off would
  book a FAKE LOSS** — the record contributes `cur/base − 1` on yfinance's adjusted close, and
  item 68 measured yfinance leaving Aptiv's spin-off as a −10.58% cliff and Unilever's demerger as
  −7.03%. Demonstrated through `contract_row`: a two-name book reads −5.3% having lost nothing.
  **Amendment 2's corporate-action rule does not cover it by CONSTRUCTION, not omission** — its
  trigger sits behind `if not cur:` plus `_stopped_trading`, and a spin-off is the one action where
  the held name keeps trading. The size is the distributed fraction, so it is unbounded below 100%
  (Corteva's separation was ~85%, harmless only because yfinance restated that one). Neither
  measured case has touched the record: both predate the 2026-07-30 inception, so the exposure is
  prospective. **The proposed rule — a distribution is RECEIVED, so the contribution is measured
  against the parent plus what was distributed, with that value STORED on the row at the time —
  is Don's decision and a contract amendment; the alternatives are named.** The trigger needs no
  new feed: item 68's `classify_disagreement` pointed at the book since inception detects it, and
  is the same narrow measurement already routed to Don. **Which current holdings are affected is
  UNMEASURED from a lane** (the book is on the service); the names to check against are MSGS
  (distribution 2026-10-26, days after the rebalance), KBR (2027-01-04), FLEX, GPC and CMCSA —
  none of which is in today's 218-name live screen, which is not the same as not in the book.
- **2026-10-17 — THE ALPACA PRICE SEAM FAILED, AND IT IS CORPORATE ACTIONS ON BOTH SIDES. NO
  SWITCH; ALPACA STAYS OFF THE INDEX PRICE PATH FOR THE 10-22 REBALANCE.** Don's run completed:
  217 names, 58,318 bars, coverage 95.5%. **Daily closes on the declared `all` basis agree on
  0.9020 against the declared 0.98, while the AS-TRADED leg agrees on 0.9915** — and that
  asymmetry is the whole diagnosis, because the as-traded close is the same number on both sides.
  The gap is **restatements for corporate actions that one vendor applied and the other did not,
  in BOTH directions**: yfinance restated Corteva's Vylor spin-off (factor 6.665, encoded as a
  "stock split") and AstraZeneca's ADS→0.5-ordinary listing change, which Alpaca did not; Alpaca
  restated Aptiv's Versigent spin-off and Unilever's Magnum demerger, which **yfinance left in its
  series as −10.6% and −7.0% cliffs.** The arithmetic closes on Don's own figure: yfinance's
  restated CTVA close for 2025-12-03 is 9.732215, and ×6.665 that is **64.8652 against the 64.87
  he measured**. **So neither vendor is consistent, and the one that is wrong on Aptiv and
  Unilever is the incumbent** — the record is priced on yfinance. **0.9020 is about 21 affected
  names of 215**, not a thin spread across 58,318 bars, because one action poisons every earlier
  bar for that name. **The recorded-series leg never ran at all**: the pull's universe is a screen
  of today's hot list, so SPY and any book name that has since left the screen were never pulled —
  now fixed to include the benchmark and every bound-book segment since inception, with the
  declared sample still reported separately. A second defect in that leg: it recorded both
  `n_priced` counts and read neither, so a vendor pricing 60 of 86 names could report agreement in
  basis points **on a different book**. **The declared 0.98 bar and the declared basis are
  UNCHANGED.** What is recorded instead is that they were never two copies of one convention, and
  that **the leg is answering a question the record does not ask**: the record is cumulative from
  2026-07-30, four of the five worst rows' events are pre-inception, and only Corteva's falls after
  it — where the incumbent is the one that got it right, so switching would have carried a 6.665×
  error into that holding. **A narrow replacement is put to Don as a new, separately declared
  measurement — agreement since inception on the book's names only — and is not run as a
  substitute.** A January switch is not worth preparing for until that or `vs_recorded` passes.
- **2026-10-17 — ITEM 67: SETTLEMENT, FRACTIONAL SHARES, AND THE AUDITOR'S THIRD BLOCKER.**
  Don: *"let's account for waiting for cash to settle now and try again to buy next day when it
  is settled. also the whole point of us switching to alpaca from tradier was because we could
  use fractional shares so lets check that now."* The auditor's third review is still **NOT
  YET**: 7 of 8 pass and question 6 fails a third time, for a third reason — a remainder re-send
  **stacked** on its own resting order. **Reproduced at the auditor's exact ratio: 30 shares
  against a 6-share target, 5×.** Fixed by subtracting this slot's own resting SAME-SIDE
  quantity — their preferred option, for their reason, that it keeps a working order working.
  Only the same side: an opposite-side order is cancelled just before the send, so subtracting
  it too over-sizes the buy by what was cancelled (my first cut did, and ended at 12 against a
  target of 6). **A rebalance now sends its sells first and sizes buys only to what the broker
  reports as spendable WITHOUT BORROWING** — `non_marginable_buying_power`, never a margin
  figure, pinned by a test driving an account whose buying power is 4× its cash. A buy refused
  for want of funds is a **settlement wait**: the sells stand, the buys go next trading day, and
  Don is alerted only once the wait outlasts T+1 by a full trading day. That **amends §8a's own
  open question 2**, which specified the opposite; `PAPER_TRACK_CONTRACT.md` §8b records it with
  the superseded text left in place. **The no-progress ceiling now counts TRADING DAYS**, because
  item 64's five crons made a five-cycle ceiling spendable before lunch. **And nothing in the
  live path had ever sold a name that left the book** — it reached the planner in neither shape,
  so it was held for ever; it has never fired because the live path has run one event, and the
  first book change in its life is the 2026-10-22 rebalance. **Fractional shares: the paper
  account accepts them (85 on 10-16); which of the book's names Alpaca will trade fractionally is
  recorded by the cycle and is UNMEASURED until one runs on Render; whether the IRA may is
  reported by `/v2/account/configurations` and is UNMEASURED until Don's keys are in.** A name
  that is not fractionable costs that one name per cycle and then stops the whole event after
  five trading days — **the remedy is Don's choice between leaving it, rounding to whole shares,
  or skipping it, and the last two are construction changes.** `pending_workflows/live-cycle.yml`
  now opens with **DO NOT INSTALL YET** stating a condition rather than a date, because that
  five-cron schedule is what made the stacking routine. **Item 67 changes the live path, so the
  auditor reviews it too before any percentage above 0.**
- **2026-10-16 — AUDITOR RE-REVIEW: STILL NOT YET** (`4eb4fa6`). 7 of 8 questions pass. One
  route to a duplicate buy-in survives: state lost, the order list unreadable, the position list
  readable. The fix is to refuse on a failed order read (item 65). Item 64 landed: IEX priced 85
  of 85 names during market hours, so no $99/month plan is needed. The paper slot placed and
  filled real paper orders (81 of 85 names held after five cycles). Two order-id defects were
  fixed, and Alpaca's wash-trade refusal surfaced (item 65). The auditor reviews a third time
  after item 65, and live keys stay out until then.
- **2026-10-16 — ITEM 63 LANDED; THE FIRST REAL PAPER CYCLE RAN.** On the service, the paper
  keys authenticate, the Index book is readable, and the paper order path works. The cycle,
  dispatched after hours, refused because 26 names had no two-sided IEX quote. Whether IEX can
  quote the book during market hours is item 64's first question. If it can't, Don chooses
  between the $99/month data plan and a different mark rule; no fallback mark is invented. Also
  measured: GitHub ran PT-WRITER about five hours late on Oct 15 and 16, and the live-cycle
  schedule had not fired by 17:19Z on Oct 16, so item 64 adds backup schedules. The auditor
  re-reviews item 63 before any live key goes in.
- **2026-10-15 — AUDITOR: NO LIVE KEY YET** (branch `worktree-auditor-live-path-review`, not
  yet landed). There are two blockers. First, the paper slot cannot place an order, because of a
  method-name mismatch that every stub-based test missed. Second, a duplicate buy-in is reachable
  through an empty record and a discarded state write. Parity and the unreadable-positions case
  also fail. Item 63 fixes all of them; the auditor re-reviews before any live key goes in.
- **2026-10-15 — F23-JOIN: THE REPAIRED JOIN STILL DOES NOT CLEAR.** The join was broken, and
  repairing it moved the arm from +0.16 to +0.87 points, but the halves still disagree in sign.
  F-23 stays declared and unfilled, and no variant is searched for.
- **2026-10-15 — F23-SECID DID NOT CLEAR, BUT IT RAN ON A BROKEN TICKER JOIN** (`f712be2`).
  Counting insiders by SEC ID instead of by name changed almost nothing (Jaccard 0.987). The
  SEC-sourced cell, though, covered 608 tickers against SF2's 1,344, because of a join defect
  between the SEC trading symbol and the panel. r1 repairs the join and re-runs the same
  registered check as a correctness repair, with no new trial and no variant search. F-23
  stays unfilled unless the repaired read clears.
- **2026-10-14 — THE PROOF PAGE LEADS WITH THE PRODUCT** (item 61). It opens on the Valquo
  Index's own backtested figures (+2.22 points a year over SPY, net Sharpe 0.97, the after-tax
  line) and the forward track's honest status. The research decile, the top 10% of all ~9,645
  companies, follows as the evidence that the ranking works.
- **2026-10-14 — VALUATION PAGE HEADLINE: A VALUATION VERDICT, NOT BUY/HOLD/SELL** (item 60).
  The headline reads "Undervalued", "Fairly valued" or "Overvalued vs our model", set by the
  price against the model's bear/base/bull range. Beside it: the fair-value range, the model's
  confidence, the two reads, and what the price assumes. Names the model cannot value say so
  instead. No buy, sell or target-price wording anywhere. Everything else on the page is
  ordered from most to least relevant, with the deep model detail behind a "Show the full
  model" control.
- **2026-10-14 — SELL-PREMIUM-3 RESULT: NOT CONFIRMED AND UNDERPOWERED AT STAGE 1** (`2a970bb`).
  The early half was +4.59%, the late half −1.21%, and no cell reached its own detection
  threshold. 37% of entries had no strike in the declared width band. Stage 2 was not run, so the
  check read is unspent. Separately, Alpaca IRAs cannot hold spreads (level 2 only), whereas
  Fidelity, Schwab and tastytrade publish that they allow defined-risk spreads in IRAs. Nothing
  adopted.
- **2026-10-14 — SELL-PREMIUM-3 IS TESTED AS DRAFTED.** The corrected stage 2 left SELL-PREMIUM-2
  NOT CONFIRMED at −0.43%/trade, the loss being the 2020 COVID crash (2021 slightly negative,
  2022-2026 positive). Don chose to test the capped-loss version anyway. Its construction is frozen at the
  draft `a1d37ff`, which predates every check-quadrant read; the register must say that the check
  window has already been seen through SELL-PREMIUM-2, and no amendment may be informed by that
  read. Build quadrant first, then the one check read; full trial charge.
- **2026-10-14 — CLUSTERED INSIDER BUYING GOES TO THE 1999-2008 CHECK AND A PAPER BOOK.** It passed
  its one check read on the $500M+ tier (+3.49pp gross / +2.91pp net over the next quarter), with
  the caveat that 2023-2026 nets about zero after costs in every tier. Next: the one 1999-2008 proxy
  read, and a forward paper book in shares on the registered construction, started now so forward
  data accrues. Paper only; if the proxy read returns NOT CONFIRMED, the book is retired with that
  result. **Measured the same day: the licensed insider file's filing dates begin in 2008**, and the
  rule needs two prior years of each insider's history, so the first usable event is about 2010 and
  the 1999-2008 read cannot be run on owned data. r1 checks whether the SEC's own free insider data
  reaches far enough back, and reports the size of that build to Don before building it. If no
  source reaches, the older-data rung is recorded as unobtainable and the paper book carries on.
- **2026-10-13 — TRY TWO MORE FREE HEADLINE SOURCES:** titles of company press releases filed
  with the SEC, and GDELT restricted to established outlets, under the same conclusions-only filter.

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
