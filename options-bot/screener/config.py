"""Central configuration — every knob in one place. Edit here, not in the logic."""

# ---- Universe ----
MARKET_CAP_CEILING = 10_000_000_000        # $10B; names above are excluded...
OVERRIDE_TOP_RANK = 3                       # ...unless they land in the top N of composite,
OVERRIDE_INSIDER_CLUSTER = 2                #    or show >= N insiders making
OVERRIDE_INSIDER_USD = 1_000_000           #    open-market buys totaling >= this.
PRICE_FLOOR = 1.00                          # exclude sub-$1 names (manipulation/junk)
MIN_AVG_DOLLAR_VOLUME = 500_000            # liquidity floor: avg daily $ volume

# ---- Output sizes ----
TOP_N = 10                                  # deep-dived names per bucket
WATCHLIST_N = 10                            # mechanical-only names per bucket

# ---- Deep-dive control ----
DIVE_MEMORY_DAYS = 30                       # don't re-dive a name dived within this window
STALENESS_REFRESH_DAYS = 90                 # re-dive a name whose last dive is older than this

# ---- Universe build / efficiency ----
FUNDAMENTALS_TTL_DAYS = 90                  # reuse cached XBRL fundamentals younger than this
                                            #   (fundamentals change quarterly; only price needs daily refresh)
CANDIDATE_POOL_PER_BUCKET = 40              # how many top names (per bucket) get the expensive
                                            #   insider Form-4 pull + re-score. Deeper = fewer missed
                                            #   insider-driven names, but more EDGAR calls.
UNIVERSE_LIMIT = None                       # None = all EDGAR filers. For a first run / curated
                                            #   universe, set an int. See README: prefer seeding from
                                            #   IWM+IJR holdings (the actual <$10B universe) over a raw scan.
MIN_SECTOR_PEERS = 6                        # Value percentiles are computed WITHIN sector. A sector with

# ── Data-health gate ────────────────────────────────────────────────────────
# The gate used to be `if feed_errors > 0`, evaluated across ~13,000 tickers x
# 2 external feeds. Zero errors over 26,000 network calls is not achievable, so
# the gate aborted every run — it would have fired on the first live run and
# every one after. These are RATES, so the gate distinguishes "the feed is
# broken" from "the internet is the internet."
MAX_FEED_ERROR_RATE = 0.10        # >10% of attempted tickets erroring = broken
MAX_FEED_ERRORS_ABSOLUTE = 25     # ...but never trip on a handful
MIN_UNIVERSE_YIELD = 0.50         # <50% of attempted tickers usable = broken
MIN_UNIVERSE_ABSOLUTE = 50        # floor when no denominator is available.
                                  # NOT 500: the README recommends seeding from
                                  # IWM+IJR holdings and a curated sub-500 list
                                  # is a legitimate config, not a broken feed.
MAX_PRICE_AGE_HOURS = 48
                                            #   fewer than this many priceable peers falls back to the
                                            #   whole-cohort percentile; if the whole cohort is also
                                            #   thinner than this, the percentile is left undefined
                                            #   (a "rank" among 3 names is noise, not information) and
                                            #   the value weight is renormalized away for that name.

# ---- Cost guard ----
MAX_DAILY_AI_SPEND = 5.00                   # hard cap; stop diving + alert if exceeded
EST_COST_PER_DIVE = 0.12                    # Opus 4.8 ($5/$25) + web search, rough

# ---- Major-event triggers (override 30-day rule; fire an alert) ----
INSIDER_ALERT_USD = 250_000                 # single open-market buy >= this
ABNORMAL_MOVE_SIGMA = 2.0                   # price & volume both beyond this z-score
EVENT_8K_TYPES = {                          # 8-K item types we treat as material
    "1.01", "1.03", "2.01", "5.02", "8.01",  # M&A, bankruptcy, asset deal, exec change, other-material
}
EVENT_8K_LOOKBACK_DAYS = 30                 # an 8-K only counts as a *current* event inside this window.
                                            #   (The old code scanned "the last 50 filings" — for a busy
                                            #   filer that can miss every 8-K, and for a quiet one it can
                                            #   surface a three-year-old item as breaking news.)
MAX_ALERTS_PER_NAME_PER_WEEK = 3            # throttle to prevent channel flooding
ALERT_WINDOW_DAYS = 7                       # rolling window the throttle counts over. The alert query
                                            #   filters on this too, so it does not load the whole table.

# ---- Scoring weights (each bucket sums to 100) ----
WEIGHTS_ESTABLISHED = {"value": 35, "quality": 30, "momentum": 15, "insider": 20}
WEIGHTS_SPECULATIVE = {"value": 20, "growth": 30, "momentum": 20, "insider": 30}

# Missing-data convention (see scoring.py): a sub-score returns None when it has NO
# information, and the composite renormalizes the remaining weights. That keeps a
# missing input neutral instead of scoring it as a zero. But a name scored on a
# sliver of the model is not comparable to a fully-scored one, so we require a
# minimum share of the nominal weight to be present before we rank a name at all.
MIN_FACTOR_COVERAGE = 0.50                  # fraction of bucket weight that must be computable

# Established value = sector-relative cheapness on two independent yields.
#   earnings_yield = net income / market cap      (equity holder's yield)
#   ebit_ev        = operating income / EV        (whole-capital yield; the EV/EBIT inverse)
# Both are held in YIELD form on purpose: a loss-making or negative-EV name then
# ranks at the bottom instead of looking "cheap" on a negative multiple.
VALUE_ESTABLISHED_WEIGHTS = {"earnings_yield": 0.50, "ebit_ev": 0.50}

# ---- Benchmarks for the track record ----
BENCHMARKS = ["IWM", "IJR"]                 # Russell 2000, S&P SmallCap 600
TRACK_HORIZONS_DAYS = [7, 30, 90]           # forward-return windows to log
DELISTING_GRACE_DAYS = 10                   # if a name has no price bar this long after a horizon
                                            #   closes, treat it as delisted and freeze its last
                                            #   observed return rather than dropping the row. Dropping
                                            #   delisted losers is exactly how a track record lies.

# ---- Data-health gate (see decisions.health_check) ----
# Zero errors across ~13k tickers x 2 feeds is not achievable: EDGAR carries funds,
# trusts and foreign filers with no usable XBRL, and Stooq simply does not have every
# US ticker. So the gate is a RATE, not a count. The thresholds below say "a normal
# run loses a minority of names to bad data; losing a quarter of them means something
# upstream broke".
MAX_FEED_ERROR_RATE = 0.25                  # fraction of attempted tickers that may raise
MIN_UNIVERSE_COVERAGE = 0.50                # fraction of attempted tickers that must yield data
MIN_UNIVERSE_SIZE = 500                     # absolute floor — but see health_check: it is capped by
                                            #   how many tickers we actually attempted, so a
                                            #   deliberately small UNIVERSE_LIMIT run is not "broken".
MAX_PRICE_AGE_DAYS = 5                      # staleness in CALENDAR days, measured for real from the
                                            #   newest bar we saw. Friday close -> Tuesday run after a
                                            #   Monday holiday is 4 days, so 5 leaves one day of slack.

# ---- Models ----
DIVE_MODEL = "claude-opus-4-8"              # deep dive (high stakes, low volume)
REVIEW_MODEL = "claude-opus-4-8"            # weekly/monthly self-review
SELF_REVIEW_MIN_SAMPLE = 40                 # don't draw conclusions below this many logged picks
                                            #   *with realized returns* — rows with NULL returns do
                                            #   not count toward it.
# C4: the second half of the review guard. SELF_REVIEW_MIN_SAMPLE alone is
# satisfied by an old table that stopped being filled in; this is the RATE, so a
# tracking loop that silently dies shows up as a failing review instead of as a
# sample that quietly stops growing. Both must pass — see pipeline.review_readiness.
MIN_TRACK_RETURN_COVERAGE = 0.50            # fraction of logged picks that must carry a realized
                                            #   30-session return before the review may run.

# ---- Discord channels ----
# One source of truth: the channel list and its env var mapping live together, so
# config.CHANNELS can't drift away from what discord_alerts actually posts to.
CHANNEL_WEBHOOK_ENV = {
    "daily_list": "DISCORD_WEBHOOK_DAILY",
    "insider_flags": "DISCORD_WEBHOOK_INSIDER",
    "improvement_suggestions": "DISCORD_WEBHOOK_IMPROVE",
}
CHANNELS = list(CHANNEL_WEBHOOK_ENV)

# ---- Insider transaction codes (SEC Form 4) ----
INSIDER_CODE_WEIGHTS = {
    "P": 1.0,    # open-market purchase  -> the real signal
    "M": 0.15,   # option exercise
    "A": 0.0,    # grant/award (not a conviction signal)
    "S": -1.0,   # open-market sale       -> negative
    "F": 0.0,    # tax withholding
}
INSIDER_ROLE_WEIGHTS = {  # multiplier on buy conviction by filer role
    "CEO": 1.5, "CFO": 1.4, "Pres": 1.3, "Officer": 1.1, "Dir": 1.0, "10%": 1.2,
}
# Only these codes count toward the "several different insiders are buying" cluster
# bonus. Option exercises (M) are a calendar event, not a conviction event — letting
# them into the cluster hands an exercise the same bonus as an open-market purchase,
# which is the exact distinction INSIDER_CODE_WEIGHTS exists to make.
INSIDER_CLUSTER_CODES = {"P"}
INSIDER_CLUSTER_BONUS = 0.5                 # per distinct open-market buyer
INSIDER_CLUSTER_MAX_BUYERS = 4              # ...counted up to here (max +2.0 pressure)

# Size weighting. log1p(size)/log1p(250k) was almost flat over the range that matters
# ($1k earned 0.56 of what $250k earned). This is a decade-based scale instead:
# every 10x in dollars adds INSIDER_SIZE_DECADE_W, anchored so $1k ~ 0.
INSIDER_SIZE_FLOOR_USD = 1_000              # buys below this are treated as $1k (noise floor)
INSIDER_SIZE_DECADE_W = 0.5                 # $10k=0.5, $100k=1.0, $250k=1.2, $1M=1.5, $10M=2.0
INSIDER_SIZE_MAX_W = 3.0                    # cap so one enormous ticket can't own the score
INSIDER_SIZE_UNKNOWN_W = 0.3                # size not parseable -> small, not large

# Where the score pins to 0/100. The old squash was 50 + 25*tanh(raw/2): it could
# never leave [25,75] (so a nominal 20-30% weight delivered half the dispersion of
# every other 0-100 component) and it saturated at one large buy. This scale is
# logarithmic in raw pressure, so it still separates "one good buy" (~66) from
# "the whole C-suite is buying" (~97).
INSIDER_SATURATION_RAW = 40.0

# ---- Ticker hygiene ----
# Separator forms (XYZ.W / XYZ-W) are the NYSE/AMEX convention...
JUNK_SUFFIXES = ("W", "WS", "WT", "U", "UN", "RT", "R")
# ...but most SPAC warrants and units trade on Nasdaq as a bare 5th letter appended
# to a 4-letter root (ABCDW = warrant, ABCDU = unit, ABCDR = right). On Nasdaq a
# 5-letter ticker's 5th character IS a suffix code, so this is safe as a class;
# it also catches 5-letter preferred series, which are not common equity either.
JUNK_FIFTH_LETTERS = {"W", "U", "R"}

# ---- Feed hygiene ----
PRICE_MIN_INTERVAL_SEC = 0.25               # floor between price requests (~4/s). Stooq is a free
                                            #   endpoint with no key; 13k unthrottled hits gets blocked.
                                            #   13k names at this rate is ~55 min — another reason the
                                            #   README recommends seeding from IWM+IJR (~2.6k names).
TICKER_MAP_TTL_HOURS = 24                   # EDGAR's ticker->CIK map is cached in-process; expire it so
                                            #   a long-lived process doesn't run on a stale map forever.
SEEN_FILING_RETENTION_DAYS = 14             # dedup rows for the intraday poller are pruned after this.

# ---- AI cost rates ($ per million tokens). Verified vs anthropic.com, Jun 2026. ----
MODEL_RATES = {
    "claude-opus-4-8": {"in": 5.0, "out": 25.0},       # confirmed: $5/$25 per MTok
    "claude-sonnet-4-6": {"in": 3.0, "out": 15.0},     # confirmed: $3/$15 per MTok
}
WEB_SEARCH_COST_PER_USE = 0.01   # confirmed: $10 / 1,000 web searches
