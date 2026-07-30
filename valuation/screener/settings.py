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
WEIGHTS_ESTABLISHED = {"value": 0.125, "quality": 0.125, "momentum": 0.125, "insider": 0.125,
                       "low_risk": 0.0, "capital_discipline": 0.125, "sentiment": 0.0,
                       "size": 0.125, "institutional": 0.125}
WEIGHTS_SPECULATIVE = {"value": 0.125, "growth": 0.125, "momentum": 0.125, "insider": 0.125,
                       "low_risk": 0.0, "capital_discipline": 0.125, "sentiment": 0.0,
                       "size": 0.125, "institutional": 0.125}

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
    # Rejected and deliberately NOT listed: cash_op_prof (t +0.22, no signal) and the
    # short-horizon price anomalies neg_ret_1m / neg_max_ret / neg_idio_vol (all wrong-
    # signed here). Adding a name back here is all it takes to re-test one.
    "f_score": "quality", "inst_breadth": "institutional",
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
}
NUMBERS_ALL = list(NUMBER_THEME.keys())

# How many names to surface, and how many of those to deep-value with the full DCF.
TOP_N = 25
DCF_ON_TOP_N = 12

# Forward-return horizons (trading days) used by the backtest track record.
TRACK_HORIZONS_DAYS = [21, 63, 126]
BENCHMARK = "SPY"
