"""
Options fill + cost engine — PRE-SPECIFIED, committed results-free BEFORE any backtest ran.

Everything in the options track rests on this file. In the stock model, costs were a late check
that the edge survived; here they are the main event. A 35-delta 60-DTE call on a mid-cap can
quote 2.40 / 2.60 — an 8% round-trip haircut before the underlying moves at all. A backtest that
fills at the mid is not optimistic, it is measuring a different strategy that nobody can trade.

So this module is written to make the honest answer the DEFAULT and the flattering one opt-in.

--------------------------------------------------------------------------------------------
THE FILL RULE — you cross the spread, both ways, and it is not configurable away by accident.

  BUY  fills at mid + aggression * (ask - mid)
  SELL fills at mid - aggression * (mid - bid)

`aggression` is 1.0 by DEFAULT: buy at the ask, sell at the bid. That is what a retail market
order actually gets, and it charges the full spread twice on a round trip. Lower values model
patient limit orders and MUST be justified rather than assumed — the whole point of a realistic
engine is defeated if the first knob anyone turns is the one that manufactures edge. Aggression
0.0 (mid-to-mid) is provided ONLY as a diagnostic to show how much of a result is spread
assumption; it is never the headline number.

--------------------------------------------------------------------------------------------
QUOTE SANITY — a bad quote must be REJECTED, never silently repaired.

The stock model was bitten four times by data that was present but wrong. Option quotes are far
dirtier than stock quotes, so every quote is validated before it can produce a fill:

  * bid <= 0 or ask <= 0            - no two-sided market; not tradable
  * ask < bid                       - crossed quote; corrupt
  * ask == bid                      - locked; treat as untradable rather than free
  * spread% > MAX_SPREAD_PCT        - a quote this wide is a placeholder, not a market
  * mid < MIN_PREMIUM               - sub-nickel options are noise; a 1-tick move is +100%

A rejected quote returns a REASON, and the caller must count rejections. A backtest that quietly
skips unfillable contracts and keeps the rest is survivorship bias wearing a different hat: the
contracts that are hard to fill are disproportionately the ones that moved.

--------------------------------------------------------------------------------------------
LIQUIDITY FILTER — applied at ENTRY only, and deliberately so.

A contract must clear MIN_OI and MIN_VOLUME to be entered. It is NOT re-tested at exit: if you
own a contract that has gone illiquid you still have to get out of it, and pretending otherwise
would let the backtest abandon its losers. Exit therefore uses whatever quote exists, however
bad, and falls back to intrinsic value (`intrinsic`, applied inside `round_trip`) when there is
no quote at all, when the contract has expired, or when the only available quote is staler than
MAX_MARK_AGE_DAYS. AUDIT B16: this paragraph used to point at an `exit_value` function that does
not exist anywhere in the repository.

--------------------------------------------------------------------------------------------
COSTS AND WHAT GETS REPORTED.

Commission is charged per contract per leg (COMMISSION_PER_CONTRACT), matching a normal retail
schedule. The headline number is always net of spread AND commission.

BREAKEVEN IS THE NUMBER TO QUOTE, exactly as in the stock model. `breakeven_cost_per_contract`
answers "how much cost per contract could this strategy absorb before expectancy hits zero?" and
is then compared against what costs actually were. A breakeven of $180 against a realised $46 is
a claim that survives disagreement about any particular cost calibration; "net expectancy was
+$134" invites an argument about the model instead.
"""
from __future__ import annotations

from typing import Optional

# ---- Pre-committed cost + fill parameters -------------------------------------------------
DEFAULT_AGGRESSION = 1.0        # 1.0 = buy the ask / sell the bid. The honest default.
COMMISSION_PER_CONTRACT = 0.65  # per contract, per leg; standard retail schedule
CONTRACT_MULTIPLIER = 100       # US equity options

# ---- Pre-committed quote sanity + liquidity bars -------------------------------------------
MAX_SPREAD_PCT = 0.25           # spread / mid; wider than this is a placeholder, not a market
MIN_PREMIUM = 0.10              # sub-dime premium: one tick is a 10%+ move, pure noise
MIN_OI = 100                    # open interest at entry
MIN_VOLUME = 10                 # contracts traded on the decision day

REJECT_REASONS = ("no_quote", "non_positive", "crossed", "locked", "wide_spread",
                  "thin_premium", "low_oi", "unknown_oi", "low_volume")
# AUDIT B4: treat a contract whose open interest was never fetched as tradable (the
# volume test still applies) rather than as zero-OI. Flip for a sensitivity run.
REQUIRE_KNOWN_OI = False


class Quote:
    """One contract's NBBO at a decision timestamp, plus the liquidity context."""

    __slots__ = ("bid", "ask", "oi", "volume", "underlying", "strike", "right", "expiry", "date")

    def __init__(self, bid, ask, oi=None, volume=None, underlying=None, strike=None,
                 right=None, expiry=None, date=None):
        self.bid, self.ask = _f(bid), _f(ask)
        # AUDIT B4 — the ThetaData cache writes **-1** for "the open-interest call failed",
        # then returns failed=False and caches the year as complete: 19,012,352 rows, 11.4% of
        # the cache, 106 of 111 names, and every single row of AAPL 2020. Read as a NUMBER it
        # flips that contract's contribution in any OI sum and fails the MIN_OI gate as though
        # OI were zero. It means UNKNOWN, and unknown is None.
        _oi = _f(oi)
        self.oi = None if (_oi is not None and _oi < 0) else _oi
        self.volume = _f(volume)
        self.underlying, self.strike = _f(underlying), _f(strike)
        self.right, self.expiry, self.date = right, expiry, date

    @property
    def mid(self) -> Optional[float]:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / 2.0

    @property
    def spread_pct(self) -> Optional[float]:
        m = self.mid
        if not m or m <= 0 or self.bid is None or self.ask is None:
            return None
        return (self.ask - self.bid) / m

    def __repr__(self):
        return (f"Quote({self.right} {self.strike} {self.expiry} "
                f"{self.bid}/{self.ask} oi={self.oi} vol={self.volume})")


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def quote_reject_reason(q: Optional[Quote], check_liquidity: bool = True) -> Optional[str]:
    """None if the quote is tradable, else the reason string. Never repairs a bad quote."""
    if q is None or q.bid is None or q.ask is None:
        return "no_quote"
    if q.bid <= 0 or q.ask <= 0:
        return "non_positive"
    if q.ask < q.bid:
        return "crossed"
    if q.ask == q.bid:
        return "locked"
    m = q.mid
    if m is None or m < MIN_PREMIUM:
        return "thin_premium"
    sp = q.spread_pct
    if sp is None or sp > MAX_SPREAD_PCT:
        return "wide_spread"
    if check_liquidity:
        # AUDIT B4 — UNKNOWN open interest is not the same as ZERO open interest, and the two
        # used to be conflated. Every contract in an affected span failed `low_oi` and was
        # silently counted as `no_contract_in_band`, so alert-to-trade conversion was understated
        # in an unknown, NAME-DEPENDENT way (AAPL 2020 has no OI at all). Rejecting them is a
        # large systematic exclusion; accepting them leans on the VOLUME test, which is
        # independent and still applies. The default accepts and counts, so the rate is visible;
        # REQUIRE_KNOWN_OI=True restores the strict behaviour for a sensitivity run.
        if q.oi is None:
            if REQUIRE_KNOWN_OI:
                return "unknown_oi"
        elif q.oi < MIN_OI:
            return "low_oi"
        if q.volume is None or q.volume < MIN_VOLUME:
            return "low_volume"
    return None


# AUDIT B2 — the ONLY reasons a quote cannot be used to GET OUT of a position.
EXIT_FATAL = ("no_quote", "non_positive", "crossed")


def exit_reject_reason(q: Optional[Quote]) -> Optional[str]:
    """The exit tolerance, which is much looser than the entry one — and deliberately so.

    AUDIT B2. The exit day-walk used `quote_reject_reason(q, check_liquidity=False)`, which
    disables only the open-interest and volume tests. `wide_spread` (spread > 25% of mid) and
    `thin_premium` (mid < $0.10) still rejected — and a rejected day was `continue`d, i.e. the
    day vanished from the trade's history as though it had never happened.

    That is wrong in BOTH directions, and only one of them is conservative. A decaying
    out-of-the-money call quoting 0.25/0.35 has a 33% spread, so it disappears from its own exit
    path *precisely in the price region where the -50% stop should fire*. Losers that decay
    through the stop on wide-quote days are never stopped and ride on to a worse outcome — bad,
    but conservative. Losers that dip through -50% on a wide-quote day, are skipped, and then
    recover are **recorded as TARGET WINS** — optimistic, and until now unmeasured.

    You have to sell what you own at whatever the market shows. A wide or thin quote is a bad
    price, not an absent one: mark it at the bid and take the hit. Only a quote that does not
    exist, is non-positive, or is crossed is genuinely unusable.

    The module docstring asserted this behaviour all along; the code did the opposite.
    """
    r = quote_reject_reason(q, check_liquidity=False)
    return r if r in EXIT_FATAL else None


def fill_price(q: Quote, side: str, aggression: float = DEFAULT_AGGRESSION) -> Optional[float]:
    """Realistic fill. side='buy' pays up toward the ask; side='sell' hits down toward the bid.

    aggression 1.0 (default) = full touch. 0.0 = mid, a diagnostic only - never the headline.
    """
    m = q.mid
    if m is None:
        return None
    a = max(0.0, min(1.0, float(aggression)))
    if side == "buy":
        return m + a * (q.ask - m)
    if side == "sell":
        return m - a * (m - q.bid)
    raise ValueError(f"side must be 'buy' or 'sell', got {side!r}")


def intrinsic(right: str, strike: float, underlying: float) -> float:
    """Payoff at expiry. The ONLY legitimate fallback when no exit quote exists."""
    if right and str(right).upper().startswith("P"):
        return max(0.0, float(strike) - float(underlying))
    return max(0.0, float(underlying) - float(strike))


MAX_MARK_AGE_DAYS = 3       # AUDIT B3: a quote older than this is not a mark, it is a memory


def round_trip(entry_q: Quote, exit_q: Optional[Quote], right: str, strike: float,
               exit_underlying: Optional[float] = None, contracts: int = 1,
               aggression: float = DEFAULT_AGGRESSION,
               expired: bool = False, exit_quote_age_days: Optional[int] = None,
               force_intrinsic_at_expiry: bool = True) -> dict:
    """One long-option trade, entry to exit, net of spread and commission.

    Returns a dict with entry/exit fills, gross and net P&L in dollars, and the total cost
    charged. `expired=True` with no exit quote settles at intrinsic against `exit_underlying` -
    which is how a contract that expired WORTHLESS gets its -100% recorded instead of vanishing
    from the sample.

    AUDIT B3 — STALE MARKS AT EXPIRY. This function used to prefer a quote over intrinsic value
    whenever ANY quote was supplied, and the caller supplies `last_q`: the last quote that passed
    validation at any point in the contract's life, possibly weeks earlier. A position that
    outlived its last usable quote was therefore stamped `exit_date = expiry`, `held_days = full
    DTE`, `settled_at_intrinsic = False` and marked at a price from before it decayed. Expiry
    trades showed a mean of -29.3% where a genuinely expired long option belongs at or near
    -100%, and `sanity()`'s `settled_at_intrinsic_frac` check could not see it because the flag
    read False. Independently measured in the exit lab: the stale mark was HIGHER than the truth
    in 94.7% of cases, 86.1% of marks were positive on contracts that were in fact worthless, and
    the mean read -77.75% against a true -92.22%.

    Two guards, both on by default:
      * `force_intrinsic_at_expiry` - at expiry, settle against the underlying whenever a settle
        price exists. A payoff needs no mark.
      * `exit_quote_age_days` - any mark older than MAX_MARK_AGE_DAYS is rejected in favour of
        intrinsic. Pass it and the guard binds; omit it and only the expiry rule applies.

    `settled_at_intrinsic` and the new `stale_mark_rejected` / `exit_quote_age_days` fields make
    the choice visible in the trade row rather than implicit in the arithmetic.
    """
    reason = quote_reject_reason(entry_q, check_liquidity=True)
    if reason:
        return {"ok": False, "reason": reason}
    entry = fill_price(entry_q, "buy", aggression)
    if entry is None or entry <= 0:
        return {"ok": False, "reason": "no_quote"}

    # Exit does NOT re-apply the liquidity filter: you must exit what you own. AUDIT B2 — and it
    # no longer applies the SPREAD or PREMIUM filters either. A wide or thin quote is a bad
    # price, not an absent one; it gets marked at the bid.
    exit_reason = exit_reject_reason(exit_q) if exit_q else "no_quote"
    can_settle = exit_underlying is not None
    stale = (exit_quote_age_days is not None and exit_quote_age_days > MAX_MARK_AGE_DAYS)
    # AUDIT B3: prefer the payoff over the mark whenever the payoff is knowable.
    prefer_intrinsic = can_settle and ((expired and force_intrinsic_at_expiry) or stale)
    settled_at_intrinsic = False
    if exit_reason is None and not prefer_intrinsic:
        exit_px = fill_price(exit_q, "sell", aggression)
    elif can_settle and (expired or stale):
        exit_px = intrinsic(right, strike, exit_underlying)
        settled_at_intrinsic = True
    else:
        return {"ok": False, "reason": f"exit_{exit_reason}"}
    if exit_px is None or exit_px < 0:
        return {"ok": False, "reason": "exit_no_quote"}

    mult = CONTRACT_MULTIPLIER * max(1, int(contracts))
    commission = COMMISSION_PER_CONTRACT * max(1, int(contracts)) * 2       # both legs
    # "Gross" prices at the MID both ways: the spread is then an explicit, visible cost.
    _marked = (exit_q is not None and exit_reason is None and not settled_at_intrinsic)
    gross = ((exit_q.mid if _marked else exit_px) - entry_q.mid) * mult
    net = (exit_px - entry) * mult - commission
    return {"ok": True, "entry_fill": entry, "exit_fill": exit_px,
            "entry_mid": entry_q.mid, "exit_mid": exit_q.mid if exit_q else None,
            "gross_pnl": gross, "net_pnl": net, "cost": gross - net,
            "commission": commission, "contracts": max(1, int(contracts)),
            # AUDIT B15 — net of spread AND commission, as the module docstring and
            # OPTIONS_BACKTEST_RESULTS.md have always claimed. This was `exit_px / entry - 1`,
            # i.e. gross of commission, and `pnl_pct` / `expectancy_pct` inherit it. Small
            # ($1.30 round trip on a ~$485 median position, about 0.27pp) but the claim was
            # false as written. `return_pct_gross_comm` keeps the old quantity for continuity.
            "return_pct": (net / (entry * mult)) if entry > 0 else None,
            "return_pct_gross_comm": (exit_px / entry - 1.0) if entry > 0 else None,
            "settled_at_intrinsic": settled_at_intrinsic,
            "stale_mark_rejected": bool(stale and settled_at_intrinsic),
            "exit_quote_age_days": exit_quote_age_days,
            "entry_spread_pct": entry_q.spread_pct}


def breakeven_cost_per_contract(trades) -> Optional[float]:
    """Cost per contract at which mean net P&L would hit zero - the number to QUOTE.

    Independent of any particular cost calibration, which is exactly why it is more robust than
    a net-P&L figure: it invites no argument about the model, only about whether real costs are
    above or below the threshold.
    """
    ok = [t for t in trades if t.get("ok")]
    if not ok:
        return None
    n = sum(t["contracts"] for t in ok)
    if n <= 0:
        return None
    gross_total = sum(t["gross_pnl"] for t in ok)
    return gross_total / n


def cost_summary(trades) -> dict:
    """What costs actually were, so breakeven can be compared against something real."""
    ok = [t for t in trades if t.get("ok")]
    rejected = [t for t in trades if not t.get("ok")]
    reasons = {}
    for t in rejected:
        reasons[t.get("reason", "?")] = reasons.get(t.get("reason", "?"), 0) + 1
    if not ok:
        return {"n_filled": 0, "n_rejected": len(rejected), "reject_reasons": reasons}
    n = sum(t["contracts"] for t in ok)
    spreads = [t["entry_spread_pct"] for t in ok if t.get("entry_spread_pct") is not None]
    return {
        "n_filled": len(ok),
        "n_rejected": len(rejected),
        "reject_reasons": reasons,
        "avg_cost_per_contract": sum(t["cost"] for t in ok) / max(n, 1),
        "avg_entry_spread_pct": (sum(spreads) / len(spreads)) if spreads else None,
        "commission_per_contract_round_trip": COMMISSION_PER_CONTRACT * 2,
        "aggression_note": ("headline uses aggression=1.0 (buy ask / sell bid); "
                            "mid-to-mid is a diagnostic only"),
    }
