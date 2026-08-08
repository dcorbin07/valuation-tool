"""Screener knobs — factor weights and gates (in the spirit of the screener project)."""

# -------------------------------------------------------------------------- #
# Junk pre-filter — REMOVE non-investable garbage BEFORE scoring, using only
# "can I actually buy this?" tests (security type + tradeability), never quality.
# A genuine top-10 pick clears all of these comfortably, so nothing real is lost.
# Every rejection is logged with a reason so you can audit what got dropped.
# -------------------------------------------------------------------------- #
PRICE_FLOOR = 1.00                 # drop sub-$1 names (mostly manipulation/junk)
MIN_AVG_DOLLAR_VOLUME = 500_000    # drop names too illiquid to trade (kept low for small caps)
MIN_MARKET_CAP_MM = 50             # drop nano-caps under ~$50M (shells/junk); keeps real small caps
EXCLUDE_FUNDS = True               # drop ETFs / mutual funds / money-market (not operating companies)
FUND_TYPES = {"ETF", "MUTUALFUND", "MONEYMARKET", "CURRENCY", "INDEX", "FUND"}

# Two-bucket composite weights (each sums to 1.0).
#
# The score is built from a small set of ECONOMICALLY DISTINCT themes, and each
# theme is itself a blend of many individual numbers (see factors.py). This keeps
# the number of *tuned* weights small (so the monthly learner stays reliable and
# doesn't overfit) while still folding in lots of signal underneath each theme:
#
#   value   — cheapness: earnings/FCF/EBIT yields, sales multiples, book-to-price
#   quality — profitability + safety: ROIC/ROE, margins, low leverage, gross
#             profitability, FCF margin, accruals (earnings backed by cash), interest coverage
#   growth  — revenue growth + acceleration (used for the speculative bucket)
#   momentum— 12-1 and 6-1 return, 52-week-high proximity
#   low_risk— defensive/low-volatility: low beta, low realized volatility
#   capital_discipline — the "investment" factor: low share issuance, low asset growth (hook)
#   sentiment— estimate revisions / crowding (hook; activates with an estimates feed)
#   size    — small-cap tilt
#   insider — cluster insider buying
#
# The four proven themes carry most of the weight; the newer ones start LOW on
# purpose and the out-of-sample learner earns them more (or pushes them to zero).
# Nothing is trusted just because it's a "known" factor — the hold-out test judges.
#   institutional — "smart money": quarter-over-quarter change in 13F institutional
#                    holdings (lagged ~45 days; a hook until an institutional feed is wired)
# ADOPTED 2026-07-30 from CPCV on the full 2,710-name / 110-date universe: 'equal-weight'
# won with median OOS IC +0.0579 (100% of 15 paths) against the prior default's +0.0450, and
# PBO fell to 40% — under the <50% bar for the first time. CPCV is this project's designated
# authority on weights, and its pick being the LEAST-tuned candidate is consistent with the
# long-standing finding that weight-tuning here is mostly noise-chasing.
#
# Caveat kept in view: walk-forward did NOT adopt (it recommends holding the old defaults),
# and Deflated Sharpe is 72% — still under the 95% bar. So this is adopted because it is the
# better-validated weighting, not because the edge is proven.
#
# REVERSIBLE: the previous hand-set defaults are preserved immediately below. Swap the two
# blocks to restore them; nothing else depends on the values.
#   PREVIOUS (hand-set):
#     WEIGHTS_ESTABLISHED = {"value": 0.22, "quality": 0.22, "momentum": 0.15, "insider": 0.13,
#                            "low_risk": 0.08, "capital_discipline": 0.05, "sentiment": 0.05,
#                            "size": 0.05, "institutional": 0.05}
#     WEIGHTS_SPECULATIVE = {"value": 0.16, "growth": 0.22, "momentum": 0.16, "insider": 0.16,
#                            "low_risk": 0.07, "capital_discipline": 0.06, "sentiment": 0.06,
#                            "size": 0.05, "institutional": 0.06}
# sentiment stays at 0 in both: it has no point-in-time source (grades parked), so giving it
# weight would just dilute the live themes.
# P5 EXPERIMENT (2026-07-30): low_risk set to 0. Measured on the full 2,710-name panel with
# BOTH its inputs finally populated (neg_beta was empty in every prior run), the theme has
# median IC -0.0014 / t +0.71 — indistinguishable from zero, so its 12.5% weight was diluting
# the themes that do work. Restore by setting it back to 0.125 and rescaling.
# The weights need not sum to 1: the backtest ranks on a weighted sum (scale-invariant) and
# the live scorer renormalizes per name over whichever factors are present.
# P6.4 (2026-07-30): momentum and institutional are +0.50 correlated, so consolidating them
# into one theme weight was tested — and REJECTED. Full universe, and both time halves:
#     current (.125/.125)      LS t 3.48   top-decile +11.77%   net alpha +11.41%   <- KEPT
#     consolidated (.0625 ea)  LS t 2.53   top-decile  +9.21%   net alpha  +8.10%
#     momentum only            LS t 2.86   top-decile +10.64%   net alpha +10.18%
#     institutional only       LS t 2.33   top-decile  +9.40%   net alpha  +7.16%
# +0.50 correlation still leaves ~75% of variance unshared: the two are COMPLEMENTARY, not
# redundant, and both earn a full weight. (In the early half `current` and `momentum only`
# are identical, because institutional has no data before 2013-06-30 — an independent check
# on its 61.4% coverage.)
WEIGHTS_ESTABLISHED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
                       "low_risk": 0.0, "capital_discipline": 0.125, "sentiment": 0.0,
                       "size": 0.125, "institutional": 0.125}
WEIGHTS_SPECULATIVE = {"value": 0.125, "growth": 0.125, "momentum": 0.125, "insider": 0.125,
                       "low_risk": 0.0, "capital_discipline": 0.125, "sentiment": 0.0,
                       "size": 0.125, "institutional": 0.125}

# -------------------------------------------------------------------------- #
# BOOK CONFIGS — two tuned constructions, chosen on RISK-ADJUSTED return.
#
# Raw alpha is the wrong yardstick for concentration: a tighter book almost always shows a
# higher mean AND a much higher variance, so ranking widths on return reliably picks the
# noisiest one. Measured on the full 2,710-name / 18-year panel, net of modelled costs:
#
#   width     net alpha   net Sharpe (full/early/late)   maxDD    turnover
#   top 5       +7.20%      0.68 / 0.92 / 0.54          -50.2%      336%
#   top 10     +20.19%      1.12 / 1.35 / 0.93          -24.5%      322%
#   top 25     +14.99%      1.12 / 1.17 / 1.06          -38.6%      300%
#   top 40     +12.85%      1.10 / 1.14 / 1.05          -37.0%      286%
#   decile     +11.44%      1.11 / 1.19 / 1.02          -41.7%      251%
#
# top 5 is the clearest result: worst return AND worst risk. top 10 and top 25 TIE on
# full-sample Sharpe (1.12) — top 25 is chosen because top 10's edge does not hold up
# (1.35 -> 0.93 across halves, vs 1.17 -> 1.06) and top 25 wins the recent half outright.
# top 10 has a genuinely better max drawdown in both halves and is the tighter alternative
# if you want it, but a 10-name book over 110 periods is a thin basis for a drawdown claim.
#
# ROTH (tax-free): no tax drag, so optimize NET-OF-COST Sharpe and rotate freely.
#   Rebalance frequency swept on the same panel (top 25, net of costs). NOTE THE UNITS:
#   these are TRADING days, so 42d is ~8.4 calendar weeks (~2 months), NOT 6 weeks — an
#   earlier version of this note mislabelled it and the true 6-week point was then measured:
#     monthly   (21d)  Sharpe 1.09 (1.19/1.01)  turnover 523%  cost drag 6.03%
#     6-week    (30d)  Sharpe 1.11 (1.09/1.13)  turnover 437%  cost drag 5.04%
#     2-month   (42d)  Sharpe 1.17 (1.12/1.20)  turnover 379%  cost drag 4.40%  <- BEST, and
#     quarterly (63d)  Sharpe 1.12 (1.17/1.06)  turnover 300%  cost drag 3.35%     best LATE
#   Faster pays only to a point: monthly's 6.03% cost drag overwhelms the benefit, and the
#   genuine 6-week cadence is WORSE than both its neighbours. The optimum is ~2 months.
#   NOTE: fundamentals only update QUARTERLY, so a 6-week rebalance is re-ranking on fresh
#   prices (momentum, market cap) over stale fundamentals — that it still wins says the
#   price-based components carry real short-horizon information.
#   CAVEAT: max drawdown is NOT comparable across frequencies — a coarser grid observes the
#   equity curve fewer times and understates the true drawdown. Do not read quarterly's
#   shallower figure as lower risk.
#
# TAXABLE: ~250%/yr turnover means ~87% of gains are short-term, and tax drag (7.8%/yr) is
#   over 3x the trading cost. Optimize AFTER-TAX Sharpe instead, which favours breadth plus a
#   no-trade band: decile + 20% band scores 0.89 after-tax Sharpe vs 0.84 unbanded, and lifts
#   after-tax alpha +3.63% -> +4.86%. (The band failed the pre-committed held-out margin in
#   one half — see HANDOFF — so it is enabled HERE, for the account where it matters, rather
#   than made the global default.)
BOOK_CONFIGS = {
    "roth": {
        "label": "Tax-free (Roth/IRA): Sharpe-optimal, full rotation, ~2-month rebalance",
        # 42 TRADING days ~= 2 calendar months. Best Sharpe of the cadences tested.
        "top_n": 25, "top_frac": None, "rebalance_days": 42, "horizon": 42,
        "exit_frac": None, "exit_mult": None,          # no band: no tax cost to churning
        # RE-MEASURED 2026-08-08 on the corrected 2,531-name / 69-date panel (P2 sweep).
        # These were the PRE-B6 2,710-name figures (net_alpha 0.1737, net_sharpe 1.17,
        # turnover 3.79) and they RENDER PUBLICLY on the landing page via
        # index_track.backtested -> "Backtested net alpha", so the page was showing
        # +17.4%/yr against a corrected +11.6%/yr. Source: BACKTEST_RESULTS.json
        # book_configs.roth (same construction — identical `label`, rebalance_days 42).
        # `cost_drag_ann` is NOT re-measured here (the results file does not emit it for a
        # book config) and is not read by the export; it remains a pre-B6 figure.
        "measured": {"net_alpha": 0.1163, "net_sharpe": 1.10, "annual_turnover": 3.17,
                     "cost_drag_ann": 0.0440},
    },
    "taxable": {
        "label": "Taxable: after-tax-optimal, decile + 20% no-trade band",
        "top_n": None, "top_frac": 0.10, "rebalance_days": 63, "horizon": 63,
        "exit_frac": 0.20, "exit_mult": None,
        # RE-MEASURED 2026-08-08, same sweep and same source (book_configs.taxable).
        # Was: after_tax_alpha 0.0486, after_tax_sharpe 0.89, net_alpha 0.1169,
        # turnover 1.72. The after-tax alpha moved most — 4.86% -> 0.81%, a sixfold
        # overstatement — because the pre-B6 panel's inverted early universe carried it.
        "measured": {"after_tax_alpha": 0.0081, "after_tax_sharpe": 0.90,
                     "net_alpha": 0.0698, "annual_turnover": 1.84},
    },
}
# ADOPTED 2026-07-31 (Don's call): `roth`. Don trades in a Roth, where there is no tax drag,
# so the book optimizes net-of-cost Sharpe (1.17) with free rotation rather than after-tax
# Sharpe. `taxable` remains fully supported for the product's taxable users and is the right
# default for anyone whose account type is unknown.
DEFAULT_BOOK_CONFIG = "roth"

# Market-regime risk-off overlay (valuation/edge/regime.py). TESTED AND NOT ADOPTED: it cuts
# max drawdown 20pp on the full sample for only 2.7pp of return and even improves Sharpe, but
# the ENTIRE benefit comes from the half containing 2008-09 — in the recent half it does
# nothing for drawdown and costs Sharpe. A rule fitted to one episode.
# Left as a toggle for anyone who wants the crash insurance and accepts paying for it the rest
# of the time. Set to 0.5 (or 0.0) to enable at that risk-off exposure.
REGIME_OVERLAY = None          # None = off. 0.0 = to cash, 0.5 = half exposure when below MA.

# Valuation-regime overlay (valuation/edge/valuation_regime.py). TESTED AND REJECTED harder
# than the trend filter: max drawdown does not move AT ALL (-57.0% in every config), Sharpe is
# worse in both halves, and while risk-off the book returned +10%/period — it sat out the BEST
# periods, not the worst. "Expensive" is not "about to fall".
VALUATION_REGIME_OVERLAY = None    # None = off. 0.0 / 0.5 = risk-off exposure if ever enabled.

# Which theme columns each bucket scores on (keys of the weight dicts above).
# autolearn + the live scorer both read this, so there's one source of truth.
BUCKET_FACTORS = {
    "established": list(WEIGHTS_ESTABLISHED.keys()),
    "speculative": list(WEIGHTS_SPECULATIVE.keys()),
}
# Every theme column build_frame produces (superset across buckets), in a stable
# order — used when persisting factors into snapshots for the learner.
FACTORS_ALL = ["value", "quality", "growth", "momentum", "insider",
               "low_risk", "capital_discipline", "sentiment", "size", "institutional"]

# Every individual number and the theme it feeds. This is the single source of
# truth for both the factor engine (which z-scores each) and the Edge Lab
# diagnostic (which measures each number's standalone predictive power).
NUMBER_THEME = {
    "earnings_yield": "value", "fcf_yield": "value", "ebit_ev": "value",
    "neg_ev_sales": "value", "neg_ps": "value", "book_to_price": "value",
    "neg_ev_ebitda": "value",
    "roic": "quality", "roe": "quality", "op_margin": "quality", "gross_margin": "quality",
    "neg_leverage": "quality", "gp_on_capital": "quality", "fcf_margin": "quality",
    "accruals_q": "quality", "interest_cov": "quality",
    "revenue_growth": "growth", "growth_accel": "growth",
    "ret_12_1": "momentum", "ret_6_1": "momentum", "high_prox": "momentum",
    "neg_beta": "low_risk", "neg_vol": "low_risk",
    "neg_issuance": "capital_discipline", "neg_asset_growth": "capital_discipline",
    "earn_rev": "sentiment", "neg_log_mktcap": "size", "inst_accum": "institutional",
    # Analyst rating actions (FMP stable/grades) — dated, so point-in-time by construction.
    # rating_rev = net upgrades-minus-downgrades over a trailing quarter; neg_rating_disp
    # penalizes analysts being split (disagreement = uncertainty).
    "rating_rev": "sentiment", "neg_rating_disp": "sentiment",
    # Sharadar-only additions, measured on the panel (400 names, 12y, 110 rebalances).
    # Kept: f_score
    # (median IC +0.061, IC t +5.66 - the strongest single number in the panel),
    # accruals_q (+0.026, t +3.08, newly populated) and inst_breadth (+0.024, t +2.71).
    # Rejected and deliberately NOT listed: the short-horizon price anomalies
    # neg_ret_1m / neg_max_ret / neg_idio_vol (all wrong-signed here). Adding a name back
    # here is all it takes to re-test one.
    "f_score": "quality", "inst_breadth": "institutional",
    # S2 (2026-08-06) — cash-based operating profitability. TESTED AND REJECTED, twice, and
    # now LISTED so it stays MEASURED, exactly like roe_ttm/roic_ttm below: registering a
    # number here gives it a z_ column and puts it in the coverage guard and the per-signal
    # IC table, but it only SCORES if factors.py names it in a theme mean, and the quality
    # mean does not. Verified: the composite is bit-identical with it registered
    # (long-short t 2.8360640685320595 either way).
    #   400-name run (the original rejection):        t +0.22
    #   FULL 2,710-name / 69-date re-run, 2026-08-06: median IC +0.0026, t +0.84
    # Against X7's CALIBRATED bar of 2.71 that is a clear miss, and it is not redundancy —
    # correlations are only 0.27 (gp_on_capital), 0.31 (fcf_margin), 0.44 (roic), so it is
    # distinct from what quality already holds and still uninformative. Folding it into the
    # quality mean LOWERS that theme's IC t from 3.10 to 2.91 and the composite's long-short
    # t from 2.836 to 2.790. The audit called this "the single cheapest untested signal in
    # the repository"; it was tested, and the reason to re-run was that the first test was on
    # 400 names, which this project's own methodology rule calls a smoke test.
    "cash_op_prof": "quality",
    # SF3 per-manager 13F detail (smart money), 45-day filing lag like the rest of the 13F
    # data. Measured on 800 large caps / 110 rebalances / 63d forward:
    #     sm_breadth       +0.0293  t +2.37   KEPT
    #     sm_avg_position  +0.0203  t +1.26   rejected
    #     sm_holders       +0.0175  t +1.57   rejected
    #     sm_conviction    +0.0040  t +1.25   rejected (position-vs-AUM carries little signal)
    # sm_breadth also beats the aggregate inst_breadth (t +1.48) — same quantity, but SF3
    # counts actual managers rather than a vendor holder tally, so it replaces it in the
    # theme mean. The rejected three stay computed in the panel, so re-testing is one line.
    "sm_breadth": "institutional",
    # P6.2 — trailing-twelve-month ROE/ROIC. TESTED AND REJECTED; kept here so they stay
    # MEASURED (z-scored, in the per-signal IC table) but they are deliberately NOT in the
    # quality mean in factors.py, so they do not score. Head-to-head on identical rows,
    # full universe:
    #     roe      +0.0439  t +2.84  cov 93.4%   <- KEPT (quarterly)
    #     roe_ttm  +0.0279  t +2.01  cov 91.0%
    #     roic     +0.0420  t +3.38  cov 96.7%   <- KEPT (quarterly)
    #     roic_ttm +0.0354  t +2.57  cov 94.2%
    # Smoothing over four quarters LOSES signal on both. The likely reason is recency: last
    # quarter's profitability predicts the next quarter better than a smoothed year does, and
    # that outweighs the fiscal-quarter seasonality TTM removes. So the ARQ quarterly figure
    # is an advantage here, not the wart it was previously recorded as. Swapping them in is
    # one edit to the quality list in factors.py if this is ever revisited.
    "roe_ttm": "quality", "roic_ttm": "quality",
    # PEAD (post-earnings announcement drift), testable since the EVENTS earnings code was
    # decoded. Listed here so they are z-scored and MEASURED; whether either enters a theme
    # mean in factors.py is the gate's decision, not an assumption.
    # TESTED AND REJECTED (2026-08-01). pead_car clears the standalone bar (t +2.21, 82.3%
    # coverage) but fails the held-out margin in BOTH directions, and two diagnostics say why:
    # the recent-only drift variant has NO signal (t -0.47), which is backwards for PEAD; and
    # pead_car is +0.286 correlated with ret_6_1, which already scores t +3.40. Measured but
    # NOT in any theme mean — re-adding is one line in factors.py.
    "pead_car": "momentum", "pead_drift": "momentum",
    # Elite-manager 13F conviction: AUM-relative position weighted by the buying
    # manager's POINT-IN-TIME track record. Measured; theme membership is the gate's
    # decision, not an assumption.
    # TESTED AND REJECTED (2026-08-01): t +1.32 vs a 2.0 bar, and BELOW both signals
    # already in the theme (sm_breadth +1.73, inst_accum +1.88). Weighting by manager
    # track record moved conviction from ~1.26 to 1.32 — noise. Measured, not scored.
    "sm_elite_conviction": "institutional",
    # FINRA short interest — orthogonal to everything else here. Measured; theme
    # membership is the gate's decision. Data starts 2018, so full-panel coverage is
    # capped ~30% by availability.
    # TESTED AND REJECTED (2026-08-01): t +1.04 and +0.42 vs a 2.0 bar on the 2018+
    # window where the data exists. Not low power — the same window shows ret_6_1 at
    # t +3.53. Genuinely orthogonal (+0.048 vs ret_6_1) but simply not predictive.
    # Measured, not scored.
    "neg_days_to_cover": "low_risk", "neg_short_interest_chg": "low_risk",
    # SEC 13D/13G. passive_13g is a deliberate PLACEBO, not a candidate.
    "activist_13d": "institutional", "passive_13g": "institutional",
    # USAspending. govt_award_level is a deliberate PLACEBO, not a candidate.
    "govt_award_momentum": "growth", "govt_award_level": "growth",
    # Congressional trades. congress_activity is a deliberate PLACEBO.
    "congress_net_buy": "sentiment", "congress_activity": "sentiment",
}
NUMBERS_ALL = list(NUMBER_THEME.keys())

# How many names to surface, and how many of those to deep-value with the full DCF.
TOP_N = 25
DCF_ON_TOP_N = 12

# Forward-return horizons (trading days) used by the backtest track record.
TRACK_HORIZONS_DAYS = [21, 63, 126]
BENCHMARK = "SPY"
