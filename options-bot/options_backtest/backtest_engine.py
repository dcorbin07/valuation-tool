"""
Options put-credit-spread backtest — honest, free, index-ETF version.

Simulates the deployed strategy (not a generic template):
  Entry:  sell ~20-delta put, buy put $5 below (fixed $5 width), target 35 DTE
          (25-50 window). Credit = 0.95 x mid. Skip if credit < $0.20.
  Exits:  whichever first — 50% profit / 2x credit stop / 21-DTE time exit /
          expiration.
  Sizing: risk ~2% of account per trade, scaled DOWN when IV is extreme, capped
          at 10 contracts per spread, max 10 concurrent, <= 50% deployed.

The sizing rules above are a direct port of the live bot's
`quant_bots/options/risk/risk.py` (RiskConfig + RiskManager._vol_scale_factor,
_size_from_risk_budget, and the contract / concurrency / buying-power caps).
`vol_scale_factor()` below is the same formula, and the caps are read from
config fields with the same names and defaults, so the backtest and the bot can
be diffed field-by-field. Set `use_vol_scaled_sizing=False` to run the flat-2%
version and see what the vol scaling is worth.

The whole point is the variance risk premium — the gap between the IMPLIED vol
we sell at and the REALIZED vol that follows. So we MUST use real historical
implied vol, not realized vol (which would bake in zero premium by construction
and show no edge no matter what). The only free source of real historical
implied vol is the VIX family: VIX for SPY, VXN for QQQ, RVX for IWM. So this
tests the concept on the index ETFs, faithfully.

Two honesty features that make this err AGAINST the strategy (good):
  1. Using the index vol index (VIX) UNDERSTATES the premium on OTM puts,
     because it ignores put skew (OTM puts trade at higher implied vol). So our
     collected credit is conservative.
  2. STOP GAP-THROUGH: in a vol spike, a 2x-credit stop doesn't fill at exactly
     2x — the spread gaps through it overnight and you exit worse. We model the
     stop fill at the NEXT day's marked price, which can be well beyond 2x. This
     is the single most important realism feature: a naive backtest caps the
     loss at the theoretical stop and lies about exactly the tail that matters.

Plus conservative slippage (sell below mid, buy back above mid) + commissions.


WHAT THIS DOES NOT MODEL (read this before believing any number above)
---------------------------------------------------------------------
  - EUROPEAN pricing on AMERICAN options. Black-Scholes has no early exercise.
    Small error for OTM puts we exit before they go deep ITM; real error if one
    ever sits deep ITM near a dividend.

  - ONE IV FOR EVERY STRIKE AND EVERY MATURITY. This is the biggest modelling
    hole. VIX is a 30-day constant-maturity, at-the-money-ish number, and we use
    that single value for three different jobs: picking the 20-delta strike,
    pricing the 35-DTE spread at entry, and re-marking that same spread at 22
    DTE. Reality has a volatility SURFACE. Two things we therefore get wrong:
      * No skew. OTM puts trade at a HIGHER implied vol than ATM, so the real
        credit at the 20-delta strike is bigger than we compute, and the real
        20-delta strike sits FURTHER out of the money than the strike we pick.
        Both errors run against the strategy, which is the direction we want to
        be wrong in — but it does mean these results are not a fair estimate of
        the strategy's level, only a floor on it.
      * No term structure. VIX is a 30-day number; we apply it at 50 DTE and at
        22 DTE alike. In calm markets the curve is upward-sloping (we understate
        the 35-DTE vol, understating credit); in a spike it inverts (we
        UNDERSTATE how fast a short-dated spread would actually re-price, which
        runs FOR the strategy). So the term-structure error is not one-sided,
        and in a crash it flatters us.

  - THE STOP MODEL IS ONE-SIDED. Booking the stop at the next day's marked price
    is conservative on the tail — a real overnight gap does blow through a 2x
    stop and that is what we capture. But it is pessimistic on the ordinary
    case: a spread that grinds slowly to 2x would in real life have been hit
    INTRADAY at roughly 2x and closed there, better than our next-close fill.
    We only look at closes, so we never get that. Net: our stop exits are worse
    than reality on the slow losers and about right on the gaps.

  - NO PORTFOLIO / CORRELATION DIMENSION AT ALL. This runs a single stream of
    positions on ONE underlying. The live bot holds up to 10 spreads across 10
    DIFFERENT tickers (max_positions_per_ticker=1), and those 10 are all short
    puts — they are all the same trade wearing different hats. In a market-wide
    selloff their correlation goes to ~1 and all 10 stops trigger on the same
    morning. Nothing here can see that. A ladder of 10 overlapping SPY spreads
    is not a diversified book and this backtest is not a test of one; treat the
    concurrency limit here as a capital-usage rule, not as diversification.

  - EXPIRATION DATES are real Friday expirations (see `pick_expiration`), rolled
    back a day when the Friday is a market holiday, but the holiday roll can
    only be applied inside the span of the price data we were handed.

  - DIVIDEND YIELD is a flat constant (~1.3%), not the actual dividend stream.

  - RATES come from ^IRX (13-week T-bill), a proxy for the actual funding /
    discount rate, held flat between observations.

  - INDEX ETFs ONLY. Nothing here says anything about single-name spreads, which
    have wider markets, higher costs, earnings gaps and real blow-up risk.

  - NO EARNINGS, no assignment mechanics, no pin risk, no borrow, no taxes, and
    no execution risk beyond the flat slippage number.
"""
from __future__ import annotations

import bisect
import logging
import math
from dataclasses import dataclass
from datetime import date, timedelta

import bs_pricing as bs

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    # ── Strategy params (mirror the deployed bot's StrategyConfig) ──
    target_short_delta: float = 0.20
    spread_width: float = 5.0
    target_dte: int = 35
    min_dte: int = 25
    max_dte: int = 50
    credit_fraction_of_mid: float = 0.95
    min_credit_dollars: float = 0.20
    profit_target_pct: float = 0.50
    stop_loss_multiple: float = 2.0
    time_exit_dte: int = 21

    # ── Sizing / caps: ported 1:1 from the live bot's risk.RiskConfig ──
    # Same names, same defaults, same order of operations, so the two can be
    # compared field-by-field.
    risk_pct_per_trade: float = 0.02
    max_concurrent: int = 10             # risk.RiskConfig.max_concurrent_positions
    max_contracts_per_spread: int = 10   # sanity cap against runaway compounding
    max_total_deployed_pct: float = 0.50
    # Volatility-scaled sizing. Shrinks the per-trade budget as ATM IV rises
    # from iv_scale_start to iv_scale_cap, down to vol_scale_floor. Matters
    # exactly in the stress windows (Feb-Mar 2020, 2022) where the flat-2%
    # version overstates the real bot's losses. Flip to False to compare.
    use_vol_scaled_sizing: bool = True
    iv_scale_start: float = 0.40
    iv_scale_cap: float = 1.00
    vol_scale_floor: float = 0.40

    # ── Capital ──
    initial_capital: float = 100_000.0

    # ── Costs (conservative) ──
    commission_per_contract: float = 0.65      # per leg, per contract (round-trip = 4x)
    slippage_per_share: float = 0.02           # each side, each leg

    # ── Market assumptions ──
    dividend_yield: float = 0.013              # ~1.3% for SPY; rough for the others
    strike_step: float = 1.0
    default_rate: float = 0.03                 # used before the first ^IRX observation

    # ── Performance reporting ──
    # Risk-free rate for the EXCESS-return Sharpe. None = use the ^IRX series
    # actually passed in (averaged over the test window). Set a float to pin it.
    risk_free_rate: float | None = None

    # ── Ruin / margin ──
    # Halt the run when equity falls to or below this. Without it the sim
    # compounds through zero and reports meaningless returns off negative
    # equity. 0.0 = halt on insolvency.
    ruin_equity_threshold: float = 0.0
    # A broker holds the FULL max loss of a defined-risk spread as buying power.
    # If equity drops below total deployed max loss you are in a margin call and
    # would be liquidated. We always COUNT those days; halting on them is opt-in
    # because forced liquidation is a different strategy.
    halt_on_margin_breach: bool = False

    # ── Expiration calendar ──
    # "weekly"   — every Friday (what SPY/QQQ/IWM chains actually list, and what
    #              the live screener therefore picks from). Default.
    # "monthly"  — third Friday only.
    # "calendar" — legacy today + target_dte. Kept only for comparison; it is
    #              wrong (expiries are not arbitrary weekdays) and misprices
    #              decay near expiry.
    expiration_calendar: str = "weekly"

    # Entry cadence: attempt a new entry every N trading days (to build a ladder
    # of overlapping positions, like the real bot opening ~daily). 1 = every day.
    entry_every_n_days: int = 1


@dataclass
class OpenSpread:
    entry_date: date
    expiration: date
    short_strike: float
    long_strike: float
    contracts: int
    credit_per_share: float          # net credit collected per share (after 0.95x + slippage)
    entry_spot: float
    max_loss_total: float = 0.0      # (width - credit) * 100 * contracts, i.e. buying power held

    @property
    def credit_per_spread(self) -> float:
        return self.credit_per_share * 100.0

    @property
    def total_credit(self) -> float:
        return self.credit_per_spread * self.contracts


# ─── Sizing helpers (ported from the live bot) ──────────────────────────────


def vol_scale_factor(atm_iv: float, cfg: BacktestConfig) -> float:
    """
    Size multiplier in [vol_scale_floor, 1.0] based on ATM IV.

    EXACT port of RiskManager._vol_scale_factor in
    quant_bots/options/risk/risk.py — full size below iv_scale_start, linear
    ramp down to vol_scale_floor at iv_scale_cap, floored above that. Keep this
    identical to the bot; if the bot's formula changes, change it here too or
    the backtest stops being a backtest OF the bot.
    """
    if not cfg.use_vol_scaled_sizing or atm_iv <= cfg.iv_scale_start:
        return 1.0
    if atm_iv >= cfg.iv_scale_cap:
        return cfg.vol_scale_floor
    span = cfg.iv_scale_cap - cfg.iv_scale_start
    frac = (atm_iv - cfg.iv_scale_start) / span if span > 0 else 1.0
    return 1.0 - frac * (1.0 - cfg.vol_scale_floor)


# ─── Expiration calendar ────────────────────────────────────────────────────


def third_friday(year: int, month: int) -> date:
    """Third Friday of the month — the standard monthly option expiration."""
    first = date(year, month, 1)
    days_to_first_friday = (4 - first.weekday()) % 7   # Mon=0 .. Fri=4
    return first + timedelta(days=days_to_first_friday + 14)


def _fridays_in(lo: date, hi: date) -> list[date]:
    """Every Friday in [lo, hi]."""
    d = lo + timedelta(days=(4 - lo.weekday()) % 7)
    out = []
    while d <= hi:
        out.append(d)
        d += timedelta(days=7)
    return out


def _third_fridays_in(lo: date, hi: date) -> list[date]:
    """Every third-Friday-of-a-month in [lo, hi]."""
    out = []
    y, m = lo.year, lo.month
    while date(y, m, 1) <= hi:
        tf = third_friday(y, m)
        if lo <= tf <= hi:
            out.append(tf)
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def _roll_to_trading_day(d: date, trading_days: set[date],
                         first: date, last: date) -> date:
    """
    Market holidays that land on a Friday (Good Friday) move expiration to the
    preceding Thursday. We can only apply that inside the span of the data we
    were handed; outside it we take the Friday as-is and say so.
    """
    if not trading_days or d < first or d > last:
        return d
    probe = d
    for _ in range(7):
        if probe in trading_days:
            return probe
        probe -= timedelta(days=1)
    return d


def pick_expiration(today: date, cfg: BacktestConfig,
                    trading_days: set[date] | None = None,
                    first: date | None = None,
                    last: date | None = None) -> date | None:
    """
    Pick the expiration in [min_dte, max_dte] closest to target_dte.

    Same rule as the live screener's _pick_target_expiration, but against a
    generated Friday calendar instead of the broker's expiration list. Returns
    None when nothing in the chain lands inside the DTE window (which does
    happen in "monthly" mode for a few days each cycle — that is real, and the
    bot would also find no candidate on those days if only monthlies existed).
    """
    if cfg.expiration_calendar == "calendar":
        # Legacy approximation. Not a real expiration date; kept only so the
        # old numbers can be reproduced.
        return today + timedelta(days=cfg.target_dte)

    lo = today + timedelta(days=cfg.min_dte)
    hi = today + timedelta(days=cfg.max_dte)
    if cfg.expiration_calendar == "monthly":
        cands = _third_fridays_in(lo, hi)
    elif cfg.expiration_calendar == "weekly":
        cands = _fridays_in(lo, hi)
    else:
        raise ValueError(f"unknown expiration_calendar: {cfg.expiration_calendar!r}")

    if trading_days:
        cands = [_roll_to_trading_day(c, trading_days, first, last) for c in cands]
    # A holiday roll can push a candidate back out of the DTE window; re-filter.
    cands = [c for c in cands if cfg.min_dte <= (c - today).days <= cfg.max_dte]
    if not cands:
        return None
    return min(cands, key=lambda e: abs((e - today).days - cfg.target_dte))


def _t_years(d_from: date, d_to: date) -> float:
    return max((d_to - d_from).days, 0) / 365.0


def _spread_close_cost_per_share(spot, short_k, long_k, t, r, sigma, q):
    """Cost to BUY BACK the spread now (per share): buy short leg, sell long leg."""
    short_val = bs.put_price(spot, short_k, t, r, sigma, q)
    long_val = bs.put_price(spot, long_k, t, r, sigma, q)
    return short_val - long_val   # net debit to close


@dataclass
class Trade:
    entry_date: date
    exit_date: date
    reason: str
    contracts: int
    credit_collected: float       # total $ received at open (after costs)
    close_cost: float             # total $ paid to close (after costs)
    pnl: float                    # realized $ P&L


class OptionsBacktester:
    def __init__(self, config: BacktestConfig):
        self.config = config

    def run(self, price_series, vol_series, rate_series) -> dict:
        """
        price_series: dict {date: close} for the underlying ETF
        vol_series:   dict {date: implied_vol_decimal} (e.g. VIX/100) for that ETF
        rate_series:  dict {date: risk_free_decimal} (e.g. 3mo T-bill/100)

        Returns a result dict with the equity curve, trade log, and stats.
        """
        cfg = self.config
        dates = sorted(d for d in price_series if d in vol_series)
        if len(dates) < cfg.max_dte + 5:
            return {"error": "not enough overlapping price/vol data"}

        cash = cfg.initial_capital
        open_spreads: list[OpenSpread] = []
        trades: list[Trade] = []
        equity_curve = []  # list of {date, equity}

        # Nearest available rate on or before d. Sorted keys + bisect: O(log n)
        # per lookup instead of the old O(n) scan over the whole dict, which
        # made the run O(n^2) in the number of days.
        rate_days = sorted(rate_series)
        rate_vals = [rate_series[d] for d in rate_days]

        def rate_on(d):
            i = bisect.bisect_right(rate_days, d)
            return rate_vals[i - 1] if i else cfg.default_rate

        trading_days = set(dates)
        first_day, last_day = dates[0], dates[-1]

        halted = False
        halt_reason = None
        halt_date = None
        margin_breach_days = 0

        for i, today in enumerate(dates):
            spot = price_series[today]
            iv = vol_series[today]
            r = rate_on(today)

            # ---- 1. Manage existing spreads (mark, apply exits) ----
            still_open = []
            for sp in open_spreads:
                t = _t_years(today, sp.expiration)
                # Mark to market: cost to close now (per share)
                close_cost_ps = _spread_close_cost_per_share(
                    spot, sp.short_strike, sp.long_strike, t, r, iv, cfg.dividend_yield)
                # P&L as % of credit: (credit - close_cost) / credit
                pnl_pct = ((sp.credit_per_share - close_cost_ps) / sp.credit_per_share
                           if sp.credit_per_share > 0 else 0.0)
                dte = (sp.expiration - today).days

                exit_reason = None
                if t <= 0:
                    exit_reason = "expiration"
                elif pnl_pct >= cfg.profit_target_pct:
                    exit_reason = "profit"
                elif pnl_pct <= -cfg.stop_loss_multiple:
                    # STOP GAP-THROUGH: we don't fill at exactly 2x. We exit at
                    # the actual marked close cost today, which may be worse than
                    # 2x (models overnight gaps). close_cost_ps is already the
                    # real marked cost, so using it here captures the gap.
                    exit_reason = "stop"
                elif dte <= cfg.time_exit_dte:
                    exit_reason = "time"

                if exit_reason:
                    # Close: pay the marked close cost + slippage + commissions
                    close_ps = close_cost_ps
                    if exit_reason != "expiration":
                        close_ps += 2 * cfg.slippage_per_share  # buy short high, sell long low
                    close_total = close_ps * 100.0 * sp.contracts
                    commissions = 2 * cfg.commission_per_contract * sp.contracts  # 2 legs to close
                    cash -= (close_total + commissions)
                    pnl = sp.total_credit - close_total - commissions
                    trades.append(Trade(sp.entry_date, today, exit_reason, sp.contracts,
                                        sp.total_credit, close_total + commissions, pnl))
                else:
                    still_open.append(sp)
            open_spreads = still_open

            # ---- 2. Mark equity (cash + liability of open spreads) ----
            liability = 0.0
            for sp in open_spreads:
                t = _t_years(today, sp.expiration)
                cc = _spread_close_cost_per_share(spot, sp.short_strike, sp.long_strike,
                                                  t, r, iv, cfg.dividend_yield)
                liability += cc * 100.0 * sp.contracts
            equity = cash - liability
            equity_curve.append({"date": today.isoformat(), "equity": round(equity, 2)})

            # ---- 2b. Ruin / margin checks ----
            # Without this the sim happily compounds through zero: equity goes
            # negative, "2% of equity" becomes negative, sizing inverts and every
            # number downstream is garbage. Stop and say so instead.
            deployed = sum(sp.max_loss_total for sp in open_spreads)
            if equity < deployed:
                margin_breach_days += 1

            if equity <= cfg.ruin_equity_threshold:
                halted = True
                halt_date = today
                halt_reason = (
                    f"RUIN: equity ${equity:,.2f} fell to or below the ruin "
                    f"threshold ${cfg.ruin_equity_threshold:,.2f} on {today}. "
                    f"Run halted with {len(open_spreads)} position(s) still open; "
                    f"everything after this date is untested."
                )
            elif cfg.halt_on_margin_breach and equity < deployed:
                halted = True
                halt_date = today
                halt_reason = (
                    f"MARGIN CALL: equity ${equity:,.2f} is below the ${deployed:,.2f} "
                    f"of buying power held against {len(open_spreads)} open spread(s) "
                    f"on {today}. A real broker would have liquidated. Run halted."
                )

            if halted:
                logger.error("%s", halt_reason)
                break

            # ---- 3. Attempt a new entry (cadence + capacity gates) ----
            if i % cfg.entry_every_n_days != 0:
                continue
            if len(open_spreads) >= cfg.max_concurrent:
                continue

            target_exp = pick_expiration(today, cfg, trading_days, first_day, last_day)
            if target_exp is None:
                continue
            t_entry = _t_years(today, target_exp)
            if t_entry <= 0:
                continue

            short_k = bs.find_strike_for_delta(spot, cfg.target_short_delta, t_entry,
                                               r, iv, cfg.dividend_yield, cfg.strike_step)
            long_k = short_k - cfg.spread_width
            if long_k <= 0:
                continue
            credit_mid = (bs.put_price(spot, short_k, t_entry, r, iv, cfg.dividend_yield)
                          - bs.put_price(spot, long_k, t_entry, r, iv, cfg.dividend_yield))
            target_credit = credit_mid * cfg.credit_fraction_of_mid

            # min_credit_dollars is tested PRE-slippage, matching the live bot:
            # strategy.py compares `credit_at_mid * credit_target_fraction_of_mid`
            # against the floor and never sees slippage (slippage is a fill
            # outcome, not something the order builder knows about). This
            # backtest used to test it POST-slippage, which rejected trades
            # (those with target credit between $0.20 and $0.24) that the real
            # bot would happily send.
            if target_credit < cfg.min_credit_dollars:
                continue

            credit_ps = target_credit - 2 * cfg.slippage_per_share  # sell short low, buy long high
            if credit_ps <= 0:
                continue

            # Size: 2% of equity, vol-scaled, then the same caps as risk.py.
            # NOTE: we compute max loss off the POST-slippage credit; the live
            # bot uses the pre-slippage target credit. That makes our max loss
            # ~$4 larger per contract on a ~$430 risk, i.e. we size marginally
            # smaller than the bot. Deliberate: it is the cash actually at risk
            # in the sim, and erring small errs against the strategy.
            max_loss_per_contract = (cfg.spread_width - credit_ps) * 100.0
            if max_loss_per_contract <= 0:
                continue

            scale = vol_scale_factor(iv, cfg)
            risk_budget = equity * cfg.risk_pct_per_trade * scale
            contracts = math.floor(risk_budget / max_loss_per_contract)
            if contracts < 1:
                continue
            # Cap AFTER the fit check, exactly as risk.py orders it.
            contracts = min(contracts, cfg.max_contracts_per_spread)

            # Total deployed buying power cap (risk.py step 3d). With 2% x 10
            # concurrent this never binds today in either system; it is here so
            # the two stay comparable if the limits ever move.
            order_max_loss = max_loss_per_contract * contracts
            if deployed + order_max_loss > equity * cfg.max_total_deployed_pct:
                continue

            credit_received = credit_ps * 100.0 * contracts
            commissions = 2 * cfg.commission_per_contract * contracts  # 2 legs to open
            cash += (credit_received - commissions)
            open_spreads.append(OpenSpread(
                entry_date=today, expiration=target_exp,
                short_strike=short_k, long_strike=long_k, contracts=contracts,
                credit_per_share=credit_ps, entry_spot=spot,
                max_loss_total=order_max_loss,
            ))
            deployed += order_max_loss

        # Risk-free for the excess-return Sharpe: an explicit override if given,
        # otherwise the average of the ^IRX series actually used over the window.
        if cfg.risk_free_rate is not None:
            rf = cfg.risk_free_rate
        elif equity_curve:
            used = [rate_on(date.fromisoformat(e["date"])) for e in equity_curve]
            rf = sum(used) / len(used)
        else:
            rf = cfg.default_rate

        return self._summarize(equity_curve, trades, cfg, rf,
                               halted=halted, halt_reason=halt_reason,
                               halt_date=halt_date,
                               open_at_halt=len(open_spreads) if halted else 0,
                               margin_breach_days=margin_breach_days)

    def _summarize(self, equity_curve, trades, cfg, rf, halted=False,
                   halt_reason=None, halt_date=None, open_at_halt=0,
                   margin_breach_days=0) -> dict:
        if not equity_curve:
            return {"error": "no equity curve produced"}
        equities = [e["equity"] for e in equity_curve]
        end = equities[-1]
        total_return = end / cfg.initial_capital - 1.0

        # daily returns
        rets = [equities[i] / equities[i-1] - 1.0
                for i in range(1, len(equities)) if equities[i-1] > 0]
        if len(rets) >= 2:
            mean = sum(rets) / len(rets)
            var = sum((x - mean) ** 2 for x in rets) / (len(rets) - 1)
            ann_vol = math.sqrt(var) * math.sqrt(252)
            ann_ret = mean * 252
            # Sharpe is an EXCESS return ratio: (return - risk-free) / vol.
            # Omitting rf on a ~5%-vol strategy while cash pays ~4% inflates the
            # number by ~0.8, which is most of the headline. `sharpe_raw` is the
            # old (wrong) figure, kept only so the two can be compared.
            sharpe = (ann_ret - rf) / ann_vol if ann_vol > 0 else 0.0
            sharpe_raw = ann_ret / ann_vol if ann_vol > 0 else 0.0
        else:
            ann_vol = ann_ret = sharpe = sharpe_raw = 0.0

        # max drawdown
        peak = -float("inf"); max_dd = 0.0
        for e in equities:
            peak = max(peak, e)
            if peak > 0:
                max_dd = min(max_dd, e / peak - 1.0)

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = len(wins) / len(trades) if trades else 0.0
        avg_win = sum(t.pnl for t in wins) / len(wins) if wins else 0.0
        avg_loss = sum(t.pnl for t in losses) / len(losses) if losses else 0.0
        worst = min((t.pnl for t in trades), default=0.0)
        by_reason = {}
        for t in trades:
            by_reason[t.reason] = by_reason.get(t.reason, 0) + 1

        return {
            "equity_curve": equity_curve,
            "trades": [t.__dict__ for t in trades],
            "stats": {
                "total_return": total_return,
                "final_equity": end,
                "annualized_return": ann_ret,
                "annualized_vol": ann_vol,
                "risk_free_rate_used": rf,
                "sharpe": sharpe,                 # excess return / vol  <- the real one
                "sharpe_raw": sharpe_raw,         # no rf subtraction    <- the old, inflated one
                "max_drawdown": max_dd,
                "num_trades": len(trades),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "worst_trade": worst,
                "exits_by_reason": by_reason,
                "halted_early": halted,
                "halt_reason": halt_reason,
                "halt_date": halt_date.isoformat() if halt_date else None,
                "open_positions_at_halt": open_at_halt,
                "margin_breach_days": margin_breach_days,
            },
        }
