"""Screener knobs — factor weights and gates (in the spirit of the screener project)."""

# Liquidity / hygiene gates
PRICE_FLOOR = 1.00                 # exclude sub-$1 names
MIN_AVG_DOLLAR_VOLUME = 1_000_000  # avg daily $ volume liquidity floor

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
