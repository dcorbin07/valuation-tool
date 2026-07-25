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
# Established (profitable): value + quality + momentum + insider.
# Speculative (unprofitable): value(vs-peers) + growth + momentum + insider.
WEIGHTS_ESTABLISHED = {"value": 0.35, "quality": 0.30, "momentum": 0.15, "insider": 0.20}
WEIGHTS_SPECULATIVE = {"value": 0.20, "growth": 0.30, "momentum": 0.20, "insider": 0.30}

# How many names to surface, and how many of those to deep-value with the full DCF.
TOP_N = 25
DCF_ON_TOP_N = 12

# Forward-return horizons (trading days) used by the backtest track record.
TRACK_HORIZONS_DAYS = [21, 63, 126]
BENCHMARK = "SPY"
