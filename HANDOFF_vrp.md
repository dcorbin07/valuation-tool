# HANDOFF — A3, the VRP / put-credit-spread arm (2026-08-02)

Single-item session, per `PROMPT_A3_vrp.md`. A4 (fold-in) and A5 (live book) were NOT started.
Written to this file rather than `HANDOFF_STATUS.md` because other agents were running
concurrently on the same repo.

## Verdict in one line

**The VRP put-credit-spread arm is REJECTED.** It fails five of the seven gate arms that were
committed results-free before the backtest ran, and it fails them by a wide margin on 2,496
trades across 55 names and 10 years.

## What was built

    valuation/edge/options_vrp.py            strategy + trade simulation + the gate  (committed
                                             results-free as 8f15a8c BEFORE any run)
    valuation/edge/options_vrp_portfolio.py  Ledoit-Wolf book sizing + arm correlation
    optvrp_run.py                            resumable per-name trade generation
    optvrp_report.py                         scores a bank against the committed gate
    OPTIONS_VRP_RESULTS.md                   the full write-up
    data/options/VRP_RESULTS*.json           machine-readable blocks (gitignored)

Strategy rules are PORTED, not invented — screener (25-50 DTE, 20-delta, 10% bid-ask, OI 100),
strategy ($5 width, $0.20 min credit), portfolio (50% profit / 2x stop / 21-DTE time exit) and
risk (2%/trade vol-scaled, 10 concurrent, 1 per ticker, 50% deployed) all come from
`options-bot/quant_bots/options` with field-by-field provenance in the module header. The bot's
raw-ATM-IV entry proxy is replaced by real IV rank from A2's daily ATM-IV series — the swap the
bot's own docstring says to make once historical IV exists.

Two rules are deliberately stricter than the live bot, both against the strategy: fills take the
touch on both legs both ways (the bot rests at 0.95x mid), and the min-credit floor is applied to
the achieved credit rather than the pre-slippage target.

## The numbers

    closed trades      2,496          hit rate        56.4%
    expectancy/trade  -7.99%          profit factor    0.28
    first half        -8.31%          second half     -7.70%
    book              $100k -> $20.7k, max drawdown -79.8%

Negative in 9 of 10 years, in every IV-rank band, on 53 of 55 names. Selling RICHER vol is worse
(IV rank >=0.80 gives -9.45% against -6.24% at 0.50-0.65).

Exit mix: 44% hit the +50% profit target for +6.4% of risk; 28% stop out for **-34.9%**; 28%
time-exit for -4.0%. Average loss is 4.55x the average win on a 56% hit rate.

## THE KEY NUMBER — correlation with the single-leg arm

    monthly correlation                        +0.246
    correlation in single-leg's DOWN months    +0.036   (52 months)
    Sharpe   single-leg +0.87   VRP -2.01   combined -0.17

**The diversification thesis is CONFIRMED and it rescues nothing.** These genuinely are
different trades — +0.036 in the long arm's losing months is close to independence. But an
uncorrelated arm that loses money drains a book rather than smoothing it.

In the three years the arm was recruited to fix, per $1,000 of risk per trade:

    2022   single-leg -8,626    VRP -49,660    combined -58,286
    2023   single-leg -3,229    VRP    -616    combined  -3,845
    2025   single-leg   +418    VRP -23,776    combined -23,358

Its three worst years (2018, 2020, 2022) are all vol events. The counter-cyclical hypothesis is
not merely unproven — it is contradicted in exactly the years it was aimed at.

## Why the reject is real and not my own modelling

  1. **Not the gap-through model.** Re-booking every stop at exactly 2x credit — the naive
     backtest that caps the loss at the theoretical stop — still gives **-4.72%**. The gap
     accounts for 3.3pp of the 8.0pp deficit. Ships as a standing `gap_through_counterfactual`.
  2. **Not a broken fill engine.** The no-edge self-test prices every trade as its exact mirror
     (same strikes, bought). The mirror loses -31.9% against the real arm's -8.0%; both sides
     are not profitable. The one gate arm that passes cleanly.
  3. **Not wiring.** 100% coverage on every input, sanity block clean, median short delta -0.202
     against a 0.20 target, median DTE 36 against 35.
  4. **Not the fill assumption either** — see the diagnostics below. At a perfect mid-to-mid
     fill, which nobody gets, the arm is BREAK-EVEN (PF 1.02), not good-but-costly.

## Pre-declared fill-quality diagnostics

Aggression 1.0 = the touch on both legs both ways (the headline, and the only verdict). Lower
values are the diagnostic `options_fill` already declares — "provided ONLY to show how much of a
result is spread assumption; never the headline number".

    aggression      n       hit     expectancy   profit factor   book final   combined Sharpe
    0.00 mid      2,609   73.7%     +0.13%          1.02         $104.1k         +0.77
    0.50 half     2,522   65.0%     -4.37%          0.50          $32.9k         +0.22
    1.00 touch    2,496   56.4%     -7.99%          0.28          $20.7k         -0.17

Expectancy is close to linear in fill aggression, so the break-even fill is about **1.5% of the
way from the mid to the touch** — i.e. you would need an essentially perfect mid fill, on both
legs, both ways, every time. The live bot's own 0.95x-mid resting order is more aggressive
than that.

**The ceiling is break-even.** This is not a strategy ruined by execution; it is a strategy with
no premium left after the market has priced it, and execution then makes it negative. Even the
costless version fails the gate (PF 1.02 against a 1.20 bar, negative first half) and even the
costless version LOWERS the combined Sharpe (0.87 -> 0.77).

The pre-registered liquidity-gate sensitivity closes the last alternative explanation. Loosening
the short-leg bid-ask gate from the bot's 10% to the project's own 25% quote-sanity bar admits
**28% more trades and makes the arm worse** (n 2,496 -> 3,191, expectancy -7.99% -> -9.35%, PF
0.28 -> 0.22). The tight gate was not starving the sample of good trades.

## What this does and does not say

**Does:** the deployed options-bot put-credit-spread strategy, on 55 liquid large caps with real
NBBO on both legs, lost money 2016-2025 — robustly, and for a reason that is measured rather
than asserted: ~$28 of a ~$65 mid credit is consumed crossing two bid-ask spreads twice, and the
mid-fill version has no edge to protect in the first place.

**Does not:** that the variance risk premium is not real. Index options (SPY/QQQ), wider spreads
with better credit-to-width ratios, and genuinely passive fills are all untested here and none
is refuted by this.

## A measurement bug found and fixed while writing this up

The obvious stress-correlation test — average pairwise correlation on the worst 20 basket days —
reported **0.233 against a 0.335 full sample**, i.e. correlation FALLING in a selloff, which
would have contradicted the options-bot's central warning. That is a conditioning artifact:
selecting days on the cross-sectional mean and then correlating the deviations around it
compresses the estimate. Splitting on average ATM IV instead (exogenous to returns) gives

    normal days                       0.254
    top-decile implied-vol days       0.610      2.4x

which is the effect the bot warns about, now measured. Ten short-put spreads across ten tickers
are not ten independent bets when it matters. The biased figure still ships as
`avg_pairwise_corr_worst_days_BIASED` with the caveat attached rather than being deleted.

**Generalisable lesson worth keeping:** never select a stress subsample on the same quantity you
are about to measure the co-movement of. This is the same class of error as judging a
standardisation change by per-signal IC (P6) — the statistic is invariant or biased in a way the
naive reading cannot see.

## Tests

99/99 edge tests green. 10 new, covering: the ported entry constants and each gate biting; IV
rank point-in-time and its thin-history refusal; touch fills on both legs both ways plus the
asymmetric exit-mark rule; all four exit triggers and the stop gap-through being worse than a 2x
fill; return measured against max risk; the self-test refusing a both-sides-profitable engine;
the sanity block catching arithmetically impossible trades; the stress/gate arithmetic; the
ported Ledoit-Wolf shrinkage properties; and the arm-correlation common-risk footing.

## Recommended next step

**Do not spend more effort on single-name credit spreads.** The ceiling is break-even before
costs; there is no configuration of width, delta or stop that recovers a premium that is not
there. Specifically do NOT re-open: this arm at a different width or delta, or with a looser
stop — the mid-fill run already bounds what any of those can achieve.

The live options track's remaining value is where the prompt left it: **A4 (options-bot engine
fold-in / deconstruct)** and **A5 (live engine + tracked book + per-alert confidence + sizing)**
for the single-leg arm plus term_slope, which is the only thing in the options track that has
cleared a held-out gate. And the standing top priority is unchanged and belongs to Cowork: a
**forward paper track vs SPY**, because everything here — both arms — has still only ever seen
this one 2016-2025 panel.

If short vol is revisited at all, the honest place to start is **index options (SPY/QQQ)**, where
the bid-ask is a fraction of single-name and where the bot's own free-data backtest already
lives. That is a different data pull, not a re-run of this.
