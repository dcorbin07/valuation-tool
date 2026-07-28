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
WEIGHTS_ESTABLISHED = {"value": 0.22, "quality": 0.22, "momentum": 0.15, "insider": 0.13,
                       "low_risk": 0.08, "capital_discipline": 0.05, "sentiment": 0.05,
                       "size": 0.05, "institutional": 0.05}
WEIGHTS_SPECULATIVE = {"value": 0.16, "growth": 0.22, "momentum": 0.16, "insider": 0.16,
                       "low_risk": 0.07, "capital_discipline": 0.06, "sentiment": 0.06,
                       "size": 0.05, "institutional": 0.06}

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
}
NUMBERS_ALL = list(NUMBER_THEME.keys())

# How many names to surface, and how many of those to deep-value with the full DCF.
TOP_N = 25
DCF_ON_TOP_N = 12

# Forward-return horizons (trading days) used by the backtest track record.
TRACK_HORIZONS_DAYS = [21, 63, 126]
BENCHMARK = "SPY"
