"""
A3 — the VRP / put-credit-spread arm. PRE-SPECIFIED, committed results-free BEFORE it was run.

--------------------------------------------------------------------------------------------
WHY A SECOND ARM AT ALL.

The single-leg scream-buy arm is real but FADING: +16.4%/trade over 2016-2020 against
+4.4% over 2021-2025, with 2022 (-11.4%), 2023 (-4.6%) and 2025 (-0.1%) negative. The §2
signal hunt that tried to arrest that fade is closed — term_slope adopted, skew / VRP-as-filter
/ GEX rejected, iv_rank untestable until A2, tick flow infeasible. There is no more juice in
making the long arm better.

So this is not another attempt at the long arm. It is the OPPOSITE trade: selling defined-risk
downside vol. A long call arm is long vol and long delta; a put credit spread is short vol and
short-ish delta. The variance risk premium (implied consistently above subsequent realised) is
the most robust documented options edge, and it should earn in exactly the flat-to-grinding
tapes where a bought call bleeds theta. **The prize is not this arm's own expectancy — it is
its CORRELATION with the long arm.** A mediocre uncorrelated arm improves the book more than a
good correlated one, and a short-vol arm that turns out to lose in the same months the long arm
loses is worth nothing at all no matter what its average is.

--------------------------------------------------------------------------------------------
THE STRATEGY IS PORTED, NOT INVENTED.

Every entry, exit and sizing rule below is the deployed options-bot's, so this measures THAT
strategy rather than a research variant of it. Provenance, field by field:

    entry / screening   quant_bots/options/screener/screener.py   ScreenerConfig
        min_dte 25, max_dte 50, target_dte 35 (nearest expiry inside the window)
        target_short_delta 0.20, max_delta_distance 0.05
        max_bid_ask_pct 0.10 and min_short_put_open_interest 100 on the SHORT leg only
        earnings filter: no announcement between entry and expiration
        ATM-IV filter (the bot's stand-in for IV rank — see the IV RANK note below)
    construction        quant_bots/options/strategy/strategy.py   StrategyConfig
        flat $5 width, min_credit_dollars 0.20, 1 contract before risk sizing
    management          quant_bots/options/portfolio/portfolio.py PortfolioConfig
        profit_target_pct 0.50, stop_loss_multiple 2.0, time_exit_dte 21
    sizing / caps       quant_bots/options/risk/risk.py           RiskConfig
        risk_pct_per_trade 0.02, max_concurrent 10, max_positions_per_ticker 1,
        max_total_deployed_pct 0.50, max_contracts_per_spread 10,
        vol-scaled sizing (iv_scale_start 0.40 -> iv_scale_cap 1.00, floor 0.40)

Two rules are deliberately STRICTER here than in the bot, both in the direction that costs the
strategy money, and both stated rather than discovered later:

  * The bot places its opening order at 0.95 x mid and waits for a fill. We do not model a
    passive fill at all: we take the touch (sell the short at the BID, buy the wing at the ASK).
    On a typical 20-delta spread the touch is worse than 0.95 x mid, so our credit is smaller
    than the bot's target credit on every single trade.
  * `min_credit_dollars` is applied to the ACHIEVED touch credit, not to the pre-slippage target
    the bot's order builder sees. That rejects marginal trades the live bot would send.

--------------------------------------------------------------------------------------------
IV RANK REPLACES THE BOT'S ATM-IV FILTER — and that is an upgrade, not a deviation.

The bot's screener gates on raw ATM IV >= 0.25 and says so in its own docstring: "This is NOT
IV rank. True IV rank requires historical IV data, which Tradier does not expose... When a paid
options data source is added this gets swapped for real IV rank without changing the rest of the
pipeline." A2 built exactly that data — a daily ATM-IV series per name across all trading days
from the cached ThetaData — so this arm ships the intended filter rather than the stand-in.

    iv_rank = fraction of the name's own trailing IV_RANK_LOOKBACK ATM-IV observations that sit
              BELOW today's, requiring at least IV_RANK_MIN_OBS of them. Entry requires
              iv_rank >= IV_RANK_MIN.

Raw IV cannot express what a short-vol entry needs: 40% IV is cheap for TSLA and rich for KO.
A day with no usable IV history is SKIPPED and counted, never entered on a defaulted value.

--------------------------------------------------------------------------------------------
FILLS: BOTH LEGS, BOTH WAYS, AT THE TOUCH. This is the whole credibility of the exercise.

A credit-spread backtest that nets legs at the mid manufactures most of the "risk-adjusted
improvement" spreads are supposed to deliver — it is the same error that made the §4 debit
spread look tradable before it was priced honestly. So:

    entry credit / share  =  short_bid  -  long_ask       (you receive less than mid)
    close cost  / share   =  short_ask  -  long_bid       (you pay more than mid)

plus COMMISSION_PER_CONTRACT per contract per leg, four legs on a round trip. The close cost is
clamped to [0, width]: a negative close cost on a put credit spread is arithmetically impossible
and means the quotes are crossed or stale (the live bot logs and clamps the same way), and a
cost above the width would be worse than assignment. Every clamp is COUNTED and reported in the
sanity block rather than silently applied — a clamp that fires often is a data problem, not a
rounding detail.

--------------------------------------------------------------------------------------------
STOP GAP-THROUGH: the one modelling choice that decides whether this is honest.

Short vol has negative skew: many small wins and rare large losses. A backtest that books the
2x-credit stop AT 2x caps the loss at the theoretical stop and therefore lies about precisely
the tail that determines whether the strategy is survivable. It is the single easiest way to
make a short-vol book look wonderful.

So the stop is evaluated on the REAL MARKED CLOSE COST each day and filled at that same marked
cost — which in a gap can be far beyond 2x the credit, up to the full width. The trigger and the
fill are the same number, so no trade can exit at a price that was never available.

The residual bias, stated in both directions rather than only the flattering one:
  * We only see DAILY closes. A spread that grinds slowly to 2x would in life have been closed
    intraday at roughly 2x, better than our next-close fill. Our slow losers are pessimistic.
  * A genuine overnight gap is captured correctly, which is the case that matters.
  * Loss per trade is bounded by the width, as it must be for a defined-risk spread. A run that
    ever reports a loss beyond max risk has a bug, and the sanity block asserts it does not.

--------------------------------------------------------------------------------------------
EARNINGS. The bot refuses any candidate with an announcement between entry and expiration.

Historical earnings dates come from Sharadar EVENTS code 22 (decoded empirically 2026-08-01 by
timing-vs-filing and by information content; see `bulk.EARNINGS_CODES`). Its coverage is
PARTIAL — ~2.83 events per ticker-year against the ~4 a full quarterly calendar would give — so
some real announcements are not in the file and will slip through the filter. That makes this
backtest hold MORE earnings risk than the live bot does, not less. Wrong in the conservative
direction, and the earnings coverage figure ships in the coverage block so nobody has to guess.
A missing date is UNKNOWN, never "no announcement".

--------------------------------------------------------------------------------------------
THE NO-EDGE SELF-TEST — the mirrored debit spread.

The classic way an options backtest fools its author is a fill model that quietly pays the
tester on both sides of the market. So every run also prices the EXACT MIRROR of each trade:
the same two strikes, same expiry, same days, BOUGHT instead of sold (buy the 20-delta put at
the ask, sell the wing at the bid, close at the touch the other way).

    A correct engine must make the mirror LOSE roughly what the real arm makes, MINUS a further
    full round trip of spread — the two sides cannot both be profitable.

If both are positive the fill engine is broken and the headline is void, whatever it says. This
is reported as `self_test.both_sides_profitable`, and it is a hard blocker on the gate below.

--------------------------------------------------------------------------------------------
WHAT THE PER-TRADE RETURN IS MEASURED AGAINST.

`pnl_pct` is P&L divided by MAX RISK — (width - credit) x 100 — not by the credit. That is the
capital a broker actually holds against a defined-risk spread and the only denominator on which
a +50% profit target and a -2x stop are commensurable. It is bounded in [-1, +something small],
which is the honest shape of the payoff: you can lose everything you risked and you can never
make more than the credit. Reporting return-on-credit instead would put a 3:1 winner and a
150%-of-risk loser on the same axis and flatter the arm enormously.

`pnl_dollars` is on the fixed 1-contract convention used everywhere else in this project, so the
same `options_tracker._stats` scores this arm and the long one. Position sizing is applied by
`options_vrp_portfolio`, never here.

--------------------------------------------------------------------------------------------
PRE-COMMITTED ADOPTION GATE — written and committed BEFORE the backtest was run.

The arm ships as a live second arm only if ALL of the following hold.

  1. SAMPLE.       >= MIN_TRADES_TOTAL closed trades, and >= MIN_TRADES_PER_HALF in EACH
                   held-out time half (2016-2020 / 2021-2025). Short-vol outcomes are
                   heavy-tailed; a thin half cannot settle anything.
  2. EXPECTANCY.   Positive expectancy per trade, net of touch fills and commission, in BOTH
                   halves. The same both-directions rule every other change in this project has
                   faced. A strategy that only worked before 2021 is the long arm's problem
                   already and is not worth adding a second one to repeat.
  3. PROFIT FACTOR. >= MIN_PROFIT_FACTOR on the full sample.
  4. THE TAIL IS MODELLED AND SURVIVABLE. Two arms, both required:
       (a) STRESS: multiply EVERY losing trade's loss by STRESS_LOSS_MULTIPLIER (capped at max
           risk, which is where a defined-risk spread's loss actually stops) and expectancy must
           remain positive. This asks whether the edge depends on the gap model being exactly
           right.
       (b) DRAWDOWN: peak-to-trough drawdown of the ported-sizing equity curve must not exceed
           MAX_DRAWDOWN_BAR of starting equity.
  5. THE SELF-TEST PASSES: the mirrored debit spread must NOT also be profitable.
  6. IT IS ACTUALLY A SECOND ARM. Monthly-P&L correlation with the single-leg arm must be
       <= MAX_ARM_CORRELATION, AND the combined book's Sharpe must exceed the single-leg arm's
       alone. A correlated arm that merely doubles the same bet fails here even if 1-5 pass.
       This is the criterion the whole exercise exists to test, so it is the one that cannot be
       waived: an arm that clears 1-5 and fails 6 is a finding about VRP, not a reason to trade.

Failing any arm is a REJECT and gets written up as one. Given how crowded short vol is and how
punishing a two-legged touch fill is, rejection is the more likely outcome and that is fine —
the alternative is a second arm that quietly correlates with the first and doubles the drawdown
the month everything goes wrong.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from . import options_fill as F

# ---- Strategy: screener (options-bot ScreenerConfig) --------------------------------------
MIN_DTE, MAX_DTE, TARGET_DTE = 25, 50, 35
TARGET_SHORT_DELTA = 0.20
MAX_DELTA_DISTANCE = 0.05
MAX_BID_ASK_PCT = 0.10          # short leg only, exactly as the bot gates it
MIN_SHORT_OI = 100
# Pre-registered SENSITIVITY, not an alternative headline: the project's own quote-sanity bar
# (options_fill.MAX_SPREAD_PCT). Reported alongside so "the 10% gate starved the sample" is a
# measurable claim rather than a suspicion. The headline is always the 10% run.
ALT_BID_ASK_PCT = F.MAX_SPREAD_PCT

# ---- Strategy: construction (options-bot StrategyConfig) -----------------------------------
SPREAD_WIDTH = 5.0
WING_TOLERANCE = 0.51           # strike ladders are not exactly $5 apart on every name
MIN_CREDIT = 0.20               # applied to the ACHIEVED touch credit (stricter than the bot)

# ---- Management (options-bot PortfolioConfig) ----------------------------------------------
PROFIT_TARGET_PCT = 0.50        # capture 50% of the credit
STOP_LOSS_MULTIPLE = 2.0        # loss >= 2x credit
TIME_EXIT_DTE = 21

# ---- Entry filter: real IV rank (A2's daily ATM-IV series) ---------------------------------
IV_RANK_MIN = 0.50
IV_RANK_LOOKBACK = 252          # one trading year of the name's own ATM IV
IV_RANK_MIN_OBS = 120           # below this a percentile is not a percentile

# ---- Sizing / caps (options-bot RiskConfig) — consumed by options_vrp_portfolio -------------
RISK_PCT_PER_TRADE = 0.02
MAX_CONCURRENT = 10
MAX_POSITIONS_PER_TICKER = 1
MAX_CONTRACTS_PER_SPREAD = 10
MAX_TOTAL_DEPLOYED_PCT = 0.50
USE_VOL_SCALED_SIZING = True
IV_SCALE_START, IV_SCALE_CAP, VOL_SCALE_FLOOR = 0.40, 1.00, 0.40
INITIAL_CAPITAL = 100_000.0

# ---- Pre-committed adoption gate ------------------------------------------------------------
MIN_TRADES_TOTAL = 200
MIN_TRADES_PER_HALF = 60
MIN_PROFIT_FACTOR = 1.20
STRESS_LOSS_MULTIPLIER = 1.5
MAX_DRAWDOWN_BAR = 0.25
MAX_ARM_CORRELATION = 0.30
LATE_START = "2021-01-01"       # the held-out split used by every other options study here

CONTRACT_MULTIPLIER = F.CONTRACT_MULTIPLIER
COMMISSION = F.COMMISSION_PER_CONTRACT


def _log(m):
    print(f"[vrp] {m}", flush=True)


# ============================ sizing helper (ported from risk.py) ==========================
def vol_scale_factor(atm_iv: Optional[float]) -> float:
    """Size multiplier in [VOL_SCALE_FLOOR, 1.0]. EXACT port of RiskManager._vol_scale_factor.

    Short vol should size DOWN when IV is extreme: a "rich" 90% IV is usually compensation for a
    real pending jump, not free premium. An unknown IV gets full size, matching the bot, which
    only shrinks on evidence.
    """
    if not USE_VOL_SCALED_SIZING or atm_iv is None or atm_iv <= IV_SCALE_START:
        return 1.0
    if atm_iv >= IV_SCALE_CAP:
        return VOL_SCALE_FLOOR
    span = IV_SCALE_CAP - IV_SCALE_START
    frac = (atm_iv - IV_SCALE_START) / span if span > 0 else 1.0
    return 1.0 - frac * (1.0 - VOL_SCALE_FLOOR)


# ============================ IV rank ======================================================
def iv_rank(iv_series: dict, as_of: str, lookback: int = IV_RANK_LOOKBACK,
            min_obs: int = IV_RANK_MIN_OBS) -> Optional[float]:
    """Percentile of today's ATM IV within this name's own trailing history. None if unknowable.

    STRICTLY point-in-time: only observations BEFORE `as_of` form the reference window, and the
    current value is compared against them. Including today in its own reference window would be
    harmless here but would drift toward look-ahead the moment the window got longer.
    """
    if not iv_series:
        return None
    today = iv_series.get(as_of)
    if today is None or today != today:
        return None
    prior = [v for d, v in iv_series.items() if d < as_of and v is not None and v == v]
    if len(prior) < min_obs:
        return None
    prior = prior[-lookback:] if len(prior) > lookback else prior
    if len(prior) < min_obs:
        return None
    return sum(1 for v in prior if v < today) / len(prior)


def build_iv_index(iv_series: dict) -> list:
    """Pre-sort a name's ATM-IV dict into an ascending (date, value) list.

    `iv_rank` above is O(history) per call, which is fine for a handful of lookups and quadratic
    across a ten-year daily walk. The runner uses `iv_rank_at` with this index instead.
    """
    return sorted((d, v) for d, v in (iv_series or {}).items()
                  if v is not None and v == v)


def iv_rank_at(index: list, i: int, lookback: int = IV_RANK_LOOKBACK,
               min_obs: int = IV_RANK_MIN_OBS) -> Optional[float]:
    """IV rank of index[i] against the `lookback` observations before it. Same rule as iv_rank."""
    if not index or i <= 0 or i >= len(index):
        return None
    lo = max(0, i - lookback)
    prior = index[lo:i]
    if len(prior) < min_obs:
        return None
    today = index[i][1]
    return sum(1 for _, v in prior if v < today) / len(prior)


# ============================ contract selection (the bot's rules) =========================
def pick_expiration(expirations, as_of: dt.date) -> Optional[dt.date]:
    """Expiry inside [MIN_DTE, MAX_DTE] closest to TARGET_DTE — Screener._pick_target_expiration."""
    viable = [e for e in expirations if MIN_DTE <= (e - as_of).days <= MAX_DTE]
    if not viable:
        return None
    return min(viable, key=lambda e: abs((e - as_of).days - TARGET_DTE))


def short_leg_reject_reason(q: F.Quote, max_bid_ask_pct: float = MAX_BID_ASK_PCT) -> Optional[str]:
    """Liquidity + quote sanity on the SHORT leg only, exactly as the bot screens it.

    The wing is deliberately NOT gated: a far-OTM long put legitimately quotes wide and thin, and
    refusing to buy it would be refusing to define the risk. You still have to own the wing.
    """
    base = F.quote_reject_reason(q, check_liquidity=False)
    if base:
        return base
    sp = q.spread_pct
    if sp is None or sp > max_bid_ask_pct:
        return "bid_ask_too_wide"
    if q.oi is None or q.oi < MIN_SHORT_OI:
        return "low_open_interest"
    return None


def find_short_put(enriched, target_delta: float = TARGET_SHORT_DELTA,
                   max_distance: float = MAX_DELTA_DISTANCE,
                   max_bid_ask_pct: float = MAX_BID_ASK_PCT):
    """Nearest-to-20-delta put that is actually fillable. (row, None) or (None, reason).

    Distance is checked against the target BEFORE liquidity, then the search walks outward
    through the remaining candidates: a chain whose 20-delta strike is unquotable can still have
    a tradable 22-delta one, and the bot would take it. Refusing to walk would silently bias the
    sample toward the most liquid days.
    """
    cand = []
    for _, r in enriched.iterrows():
        d = r.get("delta")
        if d is None or d != d:
            continue
        cand.append((abs(abs(float(d)) - target_delta), r))
    if not cand:
        return None, "no_delta_in_chain"
    cand.sort(key=lambda x: x[0])
    if cand[0][0] > max_distance:
        return None, "delta_too_far_from_target"
    reason = "no_fillable_short_leg"
    for dist, r in cand:
        if dist > max_distance:
            break
        q = F.Quote(bid=r.get("bid"), ask=r.get("ask"), oi=r.get("open_interest"),
                    volume=r.get("volume"))
        why = short_leg_reject_reason(q, max_bid_ask_pct)
        if why is None:
            return r, None
        reason = why
    return None, reason


def find_wing(rows, target_strike: float, tolerance: float = WING_TOLERANCE):
    """The long put `SPREAD_WIDTH` below the short — Screener._find_strike. None if the ladder
    has no strike there; the trade is then SKIPPED rather than re-widened, because a spread of a
    different width is a different trade with a different max loss."""
    best, best_d = None, float("inf")
    for _, r in rows.iterrows():
        try:
            k = float(r["strike"])
        except (KeyError, TypeError, ValueError):
            continue
        d = abs(k - target_strike)
        if d < best_d and d <= tolerance:
            best, best_d = r, d
    return best


# ============================ spread pricing ================================================
def entry_credit(short_row, long_row, aggression: float = F.DEFAULT_AGGRESSION):
    """Credit per share at the touch: sell the short at the bid, buy the wing at the ask.

    The wing must have a POSITIVE ASK. An absent or zero ask is not a free wing, it is no quote —
    and a put credit spread whose long leg cannot be bought is a naked short put, which is a
    different strategy with unbounded risk. Skip rather than "define" risk that was never bought.
    """
    sq = F.Quote(bid=short_row.get("bid"), ask=short_row.get("ask"))
    lq = F.Quote(bid=long_row.get("bid"), ask=long_row.get("ask"))
    if lq.ask is None or lq.ask <= 0:
        return None
    if lq.bid is not None and lq.bid > lq.ask:
        return None
    s = F.fill_price(sq, "sell", aggression)
    b = F.fill_price(lq, "buy", aggression)
    if s is None or b is None:
        return None
    return s - b


def close_cost(short_row, long_row, width: float,
               aggression: float = F.DEFAULT_AGGRESSION) -> Optional[dict]:
    """Cost per share to buy the spread back, clamped to the no-arbitrage band [0, width].

    PRICEABILITY IS ASYMMETRIC, and this is a straight port of `price_credit_spread` in the
    bot's portfolio.py rather than the symmetric entry-quality gate, because marking a position
    you already own is a different question from deciding to open one:

      * The SHORT leg is priceable only if its ASK is positive. You cannot buy an option back
        for nothing; a zero ask means no quote, not a free close.
      * The LONG wing needs only that SOME market exists (any positive bid or ask), and its bid
        is then taken at face value EVEN WHEN IT IS ZERO. A far-OTM wing bid of 0.00 is a real
        quote with real meaning — nobody will pay a cent for it — and it is the normal state of
        a spread that is WINNING. Rejecting it as unpriceable would freeze exactly the positions
        the 50% profit target and the 21-DTE time exit most need to close, which is the bug the
        live bot documents having shipped.

    Entry-quality gates (wide_spread, thin_premium, open interest) are deliberately NOT applied
    here. You must exit what you own, however badly it quotes — the same doctrine `options_fill`
    already applies to the long arm's exits.

    Returns {'cost', 'clamped'} or None. The clamp is REPORTED, never hidden: a negative buy-back
    cost on a put credit spread is arithmetically impossible and means crossed or stale quotes,
    and booking one manufactures free money exactly the way the live bot's phantom-profit bug did.
    """
    sb, sa = F._f(short_row.get("bid")), F._f(short_row.get("ask"))
    lb, la = F._f(long_row.get("bid")), F._f(long_row.get("ask"))
    if sa is None or sa <= 0:
        return None                                  # short leg unpriceable: no ask
    if sb is not None and sb > sa:
        return None                                  # crossed
    if not ((lb is not None and lb > 0) or (la is not None and la > 0)):
        return None                                  # wing has no market at all
    if lb is not None and la is not None and lb > la:
        return None                                  # crossed wing
    if lb is None:
        lb = 0.0
    a = max(0.0, min(1.0, float(aggression)))
    # Buy the short back toward its ask; sell the wing toward its bid. With only one side
    # quoted there is no mid to interpolate from, so the touch is the only honest price.
    buy = sa if sb is None else (sa + sb) / 2.0 + a * (sa - (sa + sb) / 2.0)
    sell = lb if la is None else (la + lb) / 2.0 - a * ((la + lb) / 2.0 - lb)
    raw = buy - sell
    cost = min(max(raw, 0.0), float(width))
    return {"cost": cost, "clamped": cost != raw}


def settle_at_expiry(short_strike: float, long_strike: float, underlying: float) -> float:
    """Value of the spread at expiration: intrinsic of the short minus intrinsic of the wing.

    Assignment mechanics, pin risk and early exercise are NOT modelled; an American put credit
    spread that goes deep ITM before a dividend can be exercised early. All three would make the
    result slightly worse, and none is available from an EOD quote file.
    """
    width = abs(short_strike - long_strike)
    v = (F.intrinsic("P", short_strike, underlying)
         - F.intrinsic("P", long_strike, underlying))
    return min(max(v, 0.0), width)


def trade_result(entry_date, exit_date, credit_ps: float, cost_ps: float, width: float,
                 reason: str, expired: bool = False, **extra) -> dict:
    """One closed spread on the 1-contract convention, net of commission.

    Commission: two legs to open always; two legs to close UNLESS the spread expired worthless,
    which costs nothing. An expiring ITM spread is assigned rather than closed and would in life
    carry an assignment fee — not modelled, noted here.
    """
    mult = CONTRACT_MULTIPLIER
    legs_to_close = 0 if (expired and cost_ps <= 0) else 2
    commission = COMMISSION * (2 + legs_to_close)
    gross = (credit_ps - cost_ps) * mult
    net = gross - commission
    # CAPITAL AT RISK = the defined max loss PLUS the full four-leg commission, because the
    # commission is cash that can also be lost. Two consequences, both deliberate:
    #   * the worst possible trade returns exactly -1.0, so `pnl_pct <= -1` is an exact
    #     invariant the sanity block can assert rather than a near-miss it has to tolerate;
    #   * the denominator does NOT depend on how the trade turned out (it always assumes the
    #     four-leg round trip), so returns across trades stay commensurable.
    max_risk = (float(width) - credit_ps) * mult + COMMISSION * 4
    return {
        "ok": True, "alert_ts": entry_date.isoformat(), "exit_date": exit_date.isoformat(),
        "held_days": (exit_date - entry_date).days,
        "credit_ps": credit_ps, "close_cost_ps": cost_ps, "width": float(width),
        "max_risk_dollars": max_risk,
        "gross_pnl": gross, "pnl_dollars": net, "commission": commission,
        "pnl_pct": (net / max_risk) if max_risk > 0 else None,      # of MAX RISK, not of credit
        "pnl_pct_of_credit": ((credit_ps - cost_ps) / credit_ps) if credit_ps > 0 else None,
        "exit_reason": reason, "settled_at_intrinsic": expired,
        **extra,
    }


# ============================ the walk-forward simulation ==================================
def simulate_spread(short_hist, long_hist, entry_date: dt.date, expiration: dt.date,
                    short_strike: float, long_strike: float, credit_ps: float,
                    underlying_at_expiry: Optional[float],
                    aggression: float = F.DEFAULT_AGGRESSION,
                    profit_target: float = PROFIT_TARGET_PCT,
                    stop_multiple: float = STOP_LOSS_MULTIPLE,
                    time_exit_dte: int = TIME_EXIT_DTE) -> Optional[dict]:
    """Walk forward one day at a time and exit at the FIRST trigger. Never sees the whole path.

    `short_hist` / `long_hist` are that contract's daily quote rows keyed by date. The exit
    priority matches the live bot's `_price_and_decide`: profit, then stop, then time. The stop
    fills at the SAME marked cost that triggered it — see the gap-through note in the header.
    """
    width = abs(short_strike - long_strike)
    days = sorted(d for d in short_hist if d in long_hist and d > entry_date)
    clamps = 0
    marks = []                            # (date, close_cost_ps) — the mark-to-market path
    for day in days:
        if day > expiration:
            break
        cc = close_cost(short_hist[day], long_hist[day], width, aggression)
        if cc is None:
            continue                      # no two-sided market that day: cannot mark, cannot act
        clamps += 1 if cc["clamped"] else 0
        cost = cc["cost"]
        marks.append((day.isoformat(), cost))
        captured = (credit_ps - cost) / credit_ps if credit_ps > 0 else 0.0
        dte = (expiration - day).days
        reason = None
        if captured >= profit_target:
            reason = "profit"
        elif captured <= -stop_multiple:
            reason = "stop"
        elif dte <= time_exit_dte:
            reason = "time"
        if reason:
            return trade_result(entry_date, day, credit_ps, cost, width, reason,
                                marks_seen=len(marks), clamped_marks=clamps, marks=marks,
                                last_mark_ps=cost)
    # Never triggered: hold to expiration and settle at intrinsic against the as-traded close.
    if underlying_at_expiry is None:
        return {"ok": False, "reason": "no_settle_price"}
    cost = settle_at_expiry(short_strike, long_strike, underlying_at_expiry)
    marks.append((expiration.isoformat(), cost))
    return trade_result(entry_date, expiration, credit_ps, cost, width, "expiration",
                        expired=True, marks_seen=len(marks) - 1, clamped_marks=clamps,
                        marks=marks, last_mark_ps=cost)


def simulate_mirror(short_hist, long_hist, entry_date: dt.date, expiration: dt.date,
                    short_strike: float, long_strike: float,
                    underlying_at_expiry: Optional[float],
                    aggression: float = F.DEFAULT_AGGRESSION) -> Optional[dict]:
    """THE NO-EDGE SELF-TEST. The same two strikes BOUGHT as a debit spread, same exit rules.

    Entry debit = buy the near put at the ASK, sell the wing at the BID — the touch, the other
    way round. Exit at the touch again. If this is also profitable the fill engine is paying the
    tester on both sides of the market and the headline is void.
    """
    width = abs(short_strike - long_strike)
    sq = F.Quote(bid=short_hist.get(entry_date, {}).get("bid"),
                 ask=short_hist.get(entry_date, {}).get("ask"))
    lq = F.Quote(bid=long_hist.get(entry_date, {}).get("bid"),
                 ask=long_hist.get(entry_date, {}).get("ask"))
    buy = F.fill_price(sq, "buy", aggression)
    sell = F.fill_price(lq, "sell", aggression)
    if buy is None or sell is None:
        return None
    debit = buy - sell
    if debit <= 0:
        return None
    days = sorted(d for d in short_hist if d in long_hist and d > entry_date)
    for day in days:
        if day > expiration:
            break
        s2 = F.Quote(bid=short_hist[day].get("bid"), ask=short_hist[day].get("ask"))
        l2 = F.Quote(bid=long_hist[day].get("bid"), ask=long_hist[day].get("ask"))
        if (F.quote_reject_reason(s2, check_liquidity=False) is not None
                or F.quote_reject_reason(l2, check_liquidity=False) is not None):
            continue
        sell_back = F.fill_price(s2, "sell", aggression) - F.fill_price(l2, "buy", aggression)
        sell_back = min(max(sell_back, 0.0), width)
        captured = (sell_back - debit) / debit if debit > 0 else 0.0
        dte = (expiration - day).days
        if captured >= PROFIT_TARGET_PCT or captured <= -STOP_LOSS_MULTIPLE or dte <= TIME_EXIT_DTE:
            gross = (sell_back - debit) * CONTRACT_MULTIPLIER
            return {"ok": True, "alert_ts": entry_date.isoformat(),
                    "exit_date": day.isoformat(),
                    "pnl_dollars": gross - COMMISSION * 4,
                    "pnl_pct": (gross - COMMISSION * 4) / (debit * CONTRACT_MULTIPLIER)}
    if underlying_at_expiry is None:
        return None
    val = settle_at_expiry(short_strike, long_strike, underlying_at_expiry)
    gross = (val - debit) * CONTRACT_MULTIPLIER
    return {"ok": True, "alert_ts": entry_date.isoformat(),
            "exit_date": expiration.isoformat(),
            "pnl_dollars": gross - COMMISSION * 2,
            "pnl_pct": (gross - COMMISSION * 2) / (debit * CONTRACT_MULTIPLIER)}


# ============================ reporting =====================================================
def _half(rows, late: bool):
    return [r for r in rows
            if (r["alert_ts"] >= LATE_START) == late]


def held_out_split(rows) -> dict:
    """The 2016-2020 / 2021-2025 split every options study in this project reports."""
    from .options_tracker import _stats

    early, late = _half(rows, False), _half(rows, True)
    e, l = _stats(early), _stats(late)
    return {"first_half": e, "second_half": l,
            "positive_in_both": bool((e["expectancy_pct"] or 0) > 0
                                     and (l["expectancy_pct"] or 0) > 0),
            "split_at": LATE_START}


def by_year(rows) -> dict:
    from .options_tracker import _stats

    groups = {}
    for r in rows:
        groups.setdefault(r["alert_ts"][:4], []).append(r)
    return {y: _stats(rs) for y, rs in sorted(groups.items())}


def by_iv_rank(rows) -> dict:
    """Expectancy by entry IV-rank regime. The filter admits >= 0.50 only, so these are the
    three bands INSIDE the admitted range — the question is whether richer is better, not
    whether the filter works."""
    from .options_tracker import _stats

    def band(v):
        if v is None:
            return None
        return "0.50-0.65" if v < 0.65 else ("0.65-0.80" if v < 0.80 else ">=0.80")

    groups = {}
    for r in rows:
        b = band(r.get("iv_rank"))
        if b:
            groups.setdefault(b, []).append(r)
    return {b: _stats(rs) for b, rs in sorted(groups.items())}


def tail_report(rows, worst_pct=(0.01, 0.05)) -> dict:
    """THE LEFT tail. Short vol's risk is the losses, so this is the mirror of `options_tail`.

    `options_tail` asks what survives when the best trades are removed, which is the right
    question for a convex long-option book. For a short-vol book the question is the opposite:
    how much of the loss lives in the worst few trades, and does the average survive making them
    worse. Both directions are reported so the two arms can be read on the same page.
    """
    from .options_tracker import _stats

    ok = [r for r in rows if r.get("pnl_pct") is not None]
    if not ok:
        return {"n": 0}
    asc = sorted(ok, key=lambda r: r["pnl_pct"])
    desc = list(reversed(asc))
    n = len(asc)
    out = {"n": n, "overall": _stats(ok)}
    for p in worst_pct:
        k = max(1, int(round(n * p)))
        out[f"worst_{int(p*100)}pct"] = {
            "n_dropped": k,
            "mean_of_worst": sum(r["pnl_pct"] for r in asc[:k]) / k,
            "dollars_of_worst": sum(r.get("pnl_dollars") or 0.0 for r in asc[:k]),
            "excluding_them": _stats(asc[k:]),
        }
        out[f"best_{int(p*100)}pct_excluded"] = _stats(desc[k:])
    losses = [r["pnl_pct"] for r in ok if r["pnl_pct"] <= 0]
    wins = [r["pnl_pct"] for r in ok if r["pnl_pct"] > 0]
    out["worst_trade_pct"] = asc[0]["pnl_pct"]
    out["best_trade_pct"] = desc[0]["pnl_pct"]
    out["loss_to_win_ratio"] = (abs(sum(losses) / len(losses)) / (sum(wins) / len(wins))
                                if losses and wins else None)
    # CVaR at 5%: the average outcome CONDITIONAL on being in the worst twentieth. For a short
    # vol book this is the number that decides position size, not the standard deviation.
    k5 = max(1, int(round(n * 0.05)))
    out["cvar_05"] = sum(r["pnl_pct"] for r in asc[:k5]) / k5
    out["skew_note"] = ("negative skew is EXPECTED here; the question the gate asks is whether "
                        "expectancy survives the stress multiplier, not whether skew exists")
    return out


def stress_test(rows, multiplier: float = STRESS_LOSS_MULTIPLIER) -> dict:
    """Gate 4(a): make every loss `multiplier` times worse, capped at max risk, and re-score.

    Capping at max risk is not a kindness — it is what defined risk MEANS. A spread cannot lose
    more than the width, so a stress that pushed past it would be testing a different instrument.
    Where the cap binds is reported, because a stress that is mostly capped is a weak stress.
    """
    from .options_tracker import _stats

    out, capped = [], 0
    for r in rows:
        p = r.get("pnl_pct")
        if p is None or p > 0:
            out.append(r)
            continue
        worse = p * multiplier
        if worse < -1.0:
            worse, capped = -1.0, capped + 1
        out.append({**r, "pnl_pct": worse,
                    "pnl_dollars": (r.get("pnl_dollars") or 0.0) * (worse / p) if p else 0.0})
    s = _stats(out)
    return {"multiplier": multiplier, "n_losses_capped_at_max_risk": capped,
            "stressed": s, "passes": bool((s["expectancy_pct"] or 0) > 0)}


def costs_block(rows) -> dict:
    """Breakeven vs realised, the number to QUOTE — same logic as the stock model's costs block.

    Breakeven here is per SPREAD (four commissioned legs), and it is compared against the
    commission actually charged. Note this deliberately does NOT credit the strategy for the
    spread it crossed: the touch fill is already inside `pnl_dollars`, so the breakeven answers
    "how much MORE cost could this absorb", which is the conservative reading.
    """
    ok = [r for r in rows if r.get("pnl_dollars") is not None]
    if not ok:
        return {"n": 0}
    n = len(ok)
    gross = sum(r.get("gross_pnl") or 0.0 for r in ok)
    comm = sum(r.get("commission") or 0.0 for r in ok)
    spread_cost = []
    for r in ok:
        c, w = r.get("credit_ps"), r.get("mid_credit_ps")
        if c is not None and w:
            spread_cost.append((w - c) * CONTRACT_MULTIPLIER)
    return {
        "n": n,
        "breakeven_cost_per_spread": gross / n,
        "actual_commission_per_spread": comm / n,
        "margin_multiple": (gross / n) / (comm / n) if comm else None,
        "avg_entry_spread_cost_dollars": (sum(spread_cost) / len(spread_cost)
                                          if spread_cost else None),
        "net_pnl_total": sum(r["pnl_dollars"] for r in ok),
        "aggression_note": "headline is aggression=1.0 on BOTH legs, BOTH ways (the touch)",
    }


def coverage_block(rows, funnel: dict, floor: float = 0.05) -> dict:
    """Which inputs were actually PRESENT. The coverage rule, applied to the options arm.

    Five wired factors in the stock panel were empty for this project's entire history and
    nothing surfaced it. An absent option input fails the same way — the trade simply never
    fires and the run completes normally — so every input this arm depends on is counted, and
    anything under the floor is named in `below_floor`.
    """
    n = max(len(rows), 1)
    present = {
        "iv_rank": sum(1 for r in rows if r.get("iv_rank") is not None) / n,
        "atm_iv": sum(1 for r in rows if r.get("atm_iv") is not None) / n,
        "short_delta": sum(1 for r in rows if r.get("short_delta") is not None) / n,
        "open_interest": sum(1 for r in rows if r.get("short_oi") is not None) / n,
        "earnings_known": sum(1 for r in rows if r.get("earnings_known")) / n,
    }
    return {"n_trades": len(rows), "coverage": present,
            "below_floor": sorted(k for k, v in present.items() if v < floor),
            "floor": floor, "funnel": funnel,
            "note": ("earnings_known < 1 is EXPECTED: Sharadar EVENTS code 22 covers ~2.83 "
                     "announcements per ticker-year against ~4 actual, so some earnings are "
                     "not filtered and this book carries MORE event risk than the live bot")}


def sanity_block(rows) -> dict:
    """Is the output SANE, not merely present. Coverage says a field exists; this says it is real.

    Every check below is an arithmetic invariant of a defined-risk put credit spread, so a
    failure is a BUG, not a market observation. Do not silence one to make a run green.
    """
    flags = []
    n = max(len(rows), 1)
    bad_loss = [r for r in rows if (r.get("pnl_pct") or 0) < -1.0001]
    if bad_loss:
        flags.append(f"{len(bad_loss)} trade(s) lost MORE than max risk — impossible, bug")
    bad_credit = [r for r in rows
                  if r.get("credit_ps") is not None and r.get("width")
                  and not (0 < r["credit_ps"] < r["width"])]
    if bad_credit:
        flags.append(f"{len(bad_credit)} trade(s) have credit outside (0, width)")
    bad_delta = [r for r in rows if r.get("short_delta") is not None
                 and not (0.05 <= abs(r["short_delta"]) <= 0.45)]
    if bad_delta:
        flags.append(f"{len(bad_delta)} trade(s) have a short delta outside [0.05, 0.45]")
    bad_dte = [r for r in rows if r.get("dte") is not None
               and not (MIN_DTE <= r["dte"] <= MAX_DTE)]
    if bad_dte:
        flags.append(f"{len(bad_dte)} trade(s) entered outside the {MIN_DTE}-{MAX_DTE} DTE window")
    clamped = sum(r.get("clamped_marks") or 0 for r in rows)
    marks = sum(r.get("marks_seen") or 0 for r in rows)
    clamp_rate = clamped / marks if marks else 0.0
    if clamp_rate > 0.02:
        flags.append(f"{clamp_rate:.1%} of daily marks needed a no-arbitrage clamp "
                     f"— crossed/stale quotes are common in this sample")
    no_mark = [r for r in rows if not r.get("marks_seen")]
    if len(no_mark) / n > 0.05:
        flags.append(f"{len(no_mark)/n:.1%} of trades never got a single usable daily mark "
                     f"and went straight to expiry settlement")
    reasons = {}
    for r in rows:
        reasons[r.get("exit_reason", "?")] = reasons.get(r.get("exit_reason", "?"), 0) + 1
    dominant = max(reasons.values()) / n if reasons else 0.0
    if dominant > 0.90:
        flags.append(f"one exit reason accounts for {dominant:.0%} of trades — the exit "
                     f"discipline may not be binding as intended")
    return {"flags": flags, "clean": not flags, "exit_reasons": reasons,
            "clamped_mark_rate": clamp_rate, "trades_without_a_mark": len(no_mark)}


def self_test_block(real_rows, mirror_rows) -> dict:
    """Gate 5. The mirror must lose; if both sides make money the fill engine is broken."""
    from .options_tracker import _stats

    r, m = _stats(real_rows), _stats(mirror_rows)
    both = bool((r["expectancy_pct"] or 0) > 0 and (m["expectancy_pct"] or 0) > 0)
    return {
        "real_expectancy_pct": r["expectancy_pct"], "real_n": r["n_closed"],
        "mirror_expectancy_pct": m["expectancy_pct"], "mirror_n": m["n_closed"],
        "both_sides_profitable": both,
        "passes": not both,
        "note": ("the mirror is the SAME strikes bought instead of sold; it should lose roughly "
                 "what the real arm makes plus another round trip of spread"),
    }


def evaluate_gate(rows, mirror_rows, portfolio: Optional[dict] = None,
                  correlation: Optional[dict] = None) -> dict:
    """Score the run against the gate committed in the header. Nothing here is chosen after."""
    from .options_tracker import _stats

    overall = _stats(rows)
    split = held_out_split(rows)
    stress = stress_test(rows)
    st = self_test_block(rows, mirror_rows)
    arms = {}
    checks = {
        "1_sample": bool(overall["n_closed"] >= MIN_TRADES_TOTAL
                         and split["first_half"]["n_closed"] >= MIN_TRADES_PER_HALF
                         and split["second_half"]["n_closed"] >= MIN_TRADES_PER_HALF),
        "2_expectancy_both_halves": split["positive_in_both"],
        "3_profit_factor": bool((overall["profit_factor"] or 0) >= MIN_PROFIT_FACTOR),
        "4a_stress": stress["passes"],
        "5_self_test": st["passes"],
    }
    if portfolio is not None:
        dd = abs(portfolio.get("max_drawdown") or 1.0)
        checks["4b_drawdown"] = bool(dd <= MAX_DRAWDOWN_BAR)
        arms["max_drawdown"] = dd
    else:
        checks["4b_drawdown"] = None
    if correlation is not None:
        c = correlation.get("monthly_correlation")
        sh_c = correlation.get("combined_sharpe")
        sh_s = correlation.get("single_leg_sharpe")
        checks["6_second_arm"] = bool(c is not None and c <= MAX_ARM_CORRELATION
                                      and sh_c is not None and sh_s is not None
                                      and sh_c > sh_s)
        arms.update({"monthly_correlation": c, "combined_sharpe": sh_c,
                     "single_leg_sharpe": sh_s})
    else:
        checks["6_second_arm"] = None
    decided = [v for v in checks.values() if v is not None]
    return {
        "checks": checks, "measured": arms,
        "bars": {"MIN_TRADES_TOTAL": MIN_TRADES_TOTAL,
                 "MIN_TRADES_PER_HALF": MIN_TRADES_PER_HALF,
                 "MIN_PROFIT_FACTOR": MIN_PROFIT_FACTOR,
                 "STRESS_LOSS_MULTIPLIER": STRESS_LOSS_MULTIPLIER,
                 "MAX_DRAWDOWN_BAR": MAX_DRAWDOWN_BAR,
                 "MAX_ARM_CORRELATION": MAX_ARM_CORRELATION},
        "overall": overall, "held_out": split, "stress": stress, "self_test": st,
        "adopt": bool(decided and all(decided) and len(decided) == len(checks)),
        "undecided": [k for k, v in checks.items() if v is None],
    }
