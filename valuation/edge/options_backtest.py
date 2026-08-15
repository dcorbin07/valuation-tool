"""
Scream-buy options backtest — PRE-SPECIFIED, committed results-free BEFORE it was run.

Reconstructs the LIVE alert exactly as it would have fired historically, buys the contract the
live engine would have picked, fills at realistic NBBO, holds under the live exit discipline,
and scores the result with the SAME function the forward scorecard uses.

--------------------------------------------------------------------------------------------
BACKTEST == FORWARD SCORECARD, BY CONSTRUCTION.

This module does not reimplement the metrics. It emits rows in the shape `option_alerts` uses
and calls `options_tracker._stats` / `._bucket_of` directly. If the two ever disagree it is a
code bug, not a methodology difference — which is the only way to keep a historical study and a
live tracker honest about each other over time.

Likewise the SIGNAL is not reimplemented: `intraday.signals.evaluate` and
`intraday.notify.screaming_buys` are imported and called. The alert logic has exactly one
definition in this codebase.

--------------------------------------------------------------------------------------------
WHAT "POINT-IN-TIME" MEANS HERE, precisely.

  * Technicals use only bars up to and including the decision date.
  * The option chain is pulled for the decision date and no later one.
  * The contract is chosen from that chain by the live rule (~35 delta, 45-75 DTE) using greeks
    computed from that day's mid — never from a later day's data, and never from the outcome.
  * Exit marks walk FORWARD one day at a time and stop at the FIRST trigger. The simulator can
    never see the whole path and pick the best point on it.
  * Contracts that expire worthless settle at intrinsic and post -100%. They are not dropped.
    Dropping them is the survivorship bias that makes every options backtest look good.

--------------------------------------------------------------------------------------------
THE CHAIN-PULL PREFILTER IS EXACT, NOT AN APPROXIMATION.

Pulling a chain for every symbol-day would be tens of thousands of calls. It is unnecessary:
the live score is 0.70*technical + 0.30*options for the swing horizon, and `options_signals`
is bounded above by 70 (50 base + 12 call-heavy + 8 unusual-call-volume). So for the live
threshold of 80:

    0.70*tech + 0.30*70 >= 80   =>   tech >= 84.3   (when a chain exists)
    tech >= 80                                       (when it does not)

Therefore ANY firing alert requires tech >= 80, and chains are pulled only on those days. This
is a necessary condition derived from the scoring function, so no alert can be missed — it is a
bound, not a heuristic. `PREFILTER_TECH` records it so the reasoning is visible if the scoring
weights ever change (in which case this bound MUST be recomputed).

--------------------------------------------------------------------------------------------
SPLIT ADJUSTMENT: TWO PRICE SERIES ARE REQUIRED, AND MIXING THEM IS SILENTLY FATAL.

Sharadar `closeadj` is retro-adjusted for splits. Option STRIKES are as-traded and are never
retro-adjusted. Using the adjusted close as the underlying therefore compares a 2026-basis price
against 2019-basis strikes: AAPL on 2019-05-07 reads 48.34 adjusted against real strikes of
150-200, because of the 4:1 split in August 2020. Note that Sharadar's `close` is ALSO
split-adjusted - it reads 50.72 on that date, exactly 202.90/4 - so the as-traded column is
`closeunadj`, and using plain `close` fixes nothing.

The consequences were not subtle but were completely silent: ATM implied vol solved to None on
every pre-split date (the "nearest" strike was nowhere near the money), and contract selection
picked from the wrong end of the ladder. Nothing errored.

So both series are carried and used for different jobs:

    closeadj    ->  TECHNICALS. A split is not a 75% crash; indicators must see adjusted prices.
    closeunadj  ->  ALL OPTION MATHS. Underlying for IV/greeks, strike matching, moneyness, and
                  intrinsic settlement at expiry, because those meet the strike ladder as it
                  actually stood on the day.

--------------------------------------------------------------------------------------------
A KNOWN DEVIATION FROM LIVE, stated up front rather than discovered later.

The live scan gets bar VOLUME from Tradier. The Sharadar export on disk carries date+close
only, and ThetaData stock history is barred by subscription tier (options are Standard, stocks
are FREE-tier). Volume is therefore fetched separately from Sharadar SEP.

If volume is unavailable for a name, `technical_signals` cannot award the "Volume surge" bonus
(+6). "Volume surge" is NOT one of the bullish trigger labels, so this cannot change WHICH
labels fire — only the score, and only downward. The reconstruction is therefore STRICTER than
live: it fires fewer alerts, never more. That is the conservative direction, and any surviving
edge is not an artifact of it.

--------------------------------------------------------------------------------------------
PRE-COMMITTED ADOPTION BARS (§4 construction choice, §5 filters).

  1. A construction or filter may only be adopted if it improves EXPECTANCY PER TRADE by at
     least MIN_EXPECTANCY_GAIN, net of spread and commission at aggression 1.0.
  2. It must hold in BOTH held-out time halves — the same both-directions rule the stock model
     uses. A change that works in one half only is noise.
  3. Any bucket used to justify a change needs >= MIN_CLOSED_PER_BUCKET closed trades.
     Options outcomes are heavy-tailed; one triple-up moves every statistic.
  4. The headline is always the aggression=1.0 number. A result that exists only at mid fills
     is reported as "does not survive the spread", never as an edge.

Expect most add-ons to reject. The wins to look for are the scream-buy validation itself, the
single-leg-vs-spread calibration, and one or two filters — not a pile of new signals.
"""
from __future__ import annotations

import datetime as dt
import os
import pickle
from typing import Optional

from . import blackscholes as BS
from . import options_fill as F

# ---- Pre-committed reconstruction parameters (mirror the live engine) ----------------------
ALERT_MIN_SCORE = 80.0          # valuation.config alert_min_score default
HORIZON = "swing"               # live picks swing when present
TARGET_DELTA = 0.35             # _CALL_DELTA["swing"] = 35
DTE_RANGE = (45, 75)            # _DTE["swing"]
TARGET_PCT = 1.00               # options_tracker.DEFAULT_TARGET_PCT
STOP_PCT = -0.50                # options_tracker.DEFAULT_STOP_PCT
TIME_STOP_FRAC = 0.50           # options_tracker.DEFAULT_TIME_STOP_FRAC
PREFILTER_TECH = 80.0           # exact bound; see the prefilter note above

# ---- Pre-committed adoption bars -----------------------------------------------------------
MIN_EXPECTANCY_GAIN = 0.10      # +10 percentage points of expectancy per trade

# ---- Section 4: matched vertical debit spread, defined BEFORE it was measured -------------
# The long leg is IDENTICAL to the single-leg arm, so the comparison isolates one thing: the
# effect of selling a further-OTM call against it. Anything else (different strike, different
# expiry, different entry rule) would confound the construction question with a timing question.
SHORT_LEG_DELTA = 0.20          # sell the ~20-delta call, same expiry
MIN_SPREAD_STRIKE_GAP = 0.01    # short strike must be strictly above the long strike
BARS_CACHE = os.path.join("data", "bulk", "prepared", "bars")


def _log(m):
    print(f"[optbt] {m}", flush=True)


# ============================ bars (close + volume, point-in-time) =========================
def load_bars(ticker: str, api_key: Optional[str] = None, cache_dir: str = BARS_CACHE):
    """{'date','close','volume'} from Sharadar SEP, cached. Volume is the reason for this call:
    the on-disk export is date+close only (see the deviation note above)."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"{ticker.upper()}.pkl")
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                got = pickle.load(f)
            # Older caches predate raw_close; refetch rather than silently run split-mixed.
            if isinstance(got, dict) and "raw_close" in got:
                return got
        except (OSError, pickle.UnpicklingError):
            pass
    key = api_key or os.environ.get("SHARADAR_API_KEY", "")
    if not key:
        return None
    try:
        import requests
        rows, cursor = [], None
        for _ in range(20):
            params = {"ticker": ticker.upper(), "api_key": key,
                      "qopts.columns": "date,closeadj,closeunadj,volume"}
            if cursor:
                params["qopts.cursor_id"] = cursor
            r = requests.get("https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP.json",
                             params=params, timeout=90)
            if r.status_code != 200:
                break
            j = r.json()
            dtb = j.get("datatable") or {}
            rows.extend(dtb.get("data", []))
            cursor = (j.get("meta") or {}).get("next_cursor_id")
            if not cursor:
                break
        if not rows:
            return None
        rows.sort(key=lambda x: x[0])
        out = {"date": [str(r[0])[:10] for r in rows],
               "close": [float(r[1]) for r in rows],        # ADJUSTED - technicals only
               "raw_close": [float(r[2]) for r in rows],    # AS-TRADED - all option maths
               "volume": [float(r[3] or 0) for r in rows]}
        with open(path, "wb") as f:
            pickle.dump(out, f, protocol=pickle.HIGHEST_PROTOCOL)
        return out
    except Exception as e:                                              # noqa: BLE001
        _log(f"{ticker}: bars fetch failed {type(e).__name__}")
        return None


def bars_asof(bars: dict, as_of: str, lookback: int = 400) -> Optional[dict]:
    """Trailing window ending ON `as_of`. Nothing after it is visible — this is the PIT guard."""
    if not bars:
        return None
    ds = bars["date"]
    hi = -1
    for i, d in enumerate(ds):
        if d <= as_of:
            hi = i
        else:
            break
    if hi < 60:
        return None
    lo = max(0, hi - lookback + 1)
    return {"close": bars["close"][lo:hi + 1], "volume": bars["volume"][lo:hi + 1],
            "high": bars["close"][lo:hi + 1], "low": bars["close"][lo:hi + 1],
            # As-traded price for option maths; never feed this to the indicators.
            "raw_close": (bars.get("raw_close") or bars["close"])[lo:hi + 1]}


def spot_asof(w) -> Optional[float]:
    """The ONE way to get a spot price for option maths out of a `bars_asof` window.

    AUDIT B1. Five call sites across four modules independently wrote `w["close"][-1]` here.
    `close` is `closeadj` — split AND dividend adjusted, for indicators only — while strikes
    trade unadjusted, so an adjusted spot throws the 0.90-1.20 moneyness prefilter and the
    0.35-delta target on every pre-split date of every split name (AAPL 4:1, TSLA 5:1 and 3:1,
    NVDA 4:1 and 10:1, AMZN/GOOGL 20:1), and corrupts every dividend payer on every date by a
    factor that grows with lookback. Settlement always used the unadjusted series, so entry and
    settlement of the same trade ran on different price bases.

    Named and exported so the next module gets it right by reaching for the obvious function
    rather than by remembering a two-word comment.
    """
    if not w:
        return None
    px = w.get("raw_close") or w.get("close")
    return px[-1] if px else None


# ============================ option-chain summary (the live shape) ========================
def chain_summary(chain, underlying: float, as_of) -> Optional[dict]:
    """The dict `intraday.options.options_signals` expects, rebuilt from a historical chain.

    Uses the FRONT expiry, matching the live provider which reads expirations[0].
    """
    import pandas as pd

    if chain is None or len(chain) == 0:
        return None
    d = chain.copy()
    exp = pd.to_datetime(d["expiration"]).dt.date
    asof = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    future = sorted({e for e in exp if e > asof})
    if not future:
        return None
    front = future[0]
    f = d[exp == front]
    calls, puts = f[f["right"].astype(str).str.upper().str.startswith("C")], \
        f[f["right"].astype(str).str.upper().str.startswith("P")]
    cv = float(pd.to_numeric(calls.get("volume"), errors="coerce").fillna(0).sum())
    pv = float(pd.to_numeric(puts.get("volume"), errors="coerce").fillna(0).sum())
    # AUDIT B4 — the ThetaData cache writes -1 for "the open-interest call failed" (11.4% of
    # rows, 106 of 111 names, all of AAPL 2020). `.fillna(0).sum()` read that as a NUMBER, so
    # every unknown row SUBTRACTED one from its side's total and poisoned the put/call OI ratio.
    # `f_d_pc_oi` — one of the closest near-misses in the 64-feature autopsy, rejected on a
    # permutation p of 0.0545 against a 0.05 bar — is built on exactly this quantity.
    # AUDIT MA38 - the third return value. `cv`/`pv` above sum EVERY contract's volume while the
    # OI sums cover only the contracts whose open interest is KNOWN, so `cv / coi` divides a
    # whole-chain numerator by a partial denominator and is inflated by roughly 1/coverage. The
    # matched sum below is the same quantity taken over the SAME rows, so the ratio the consumer
    # forms is like-for-like without imputing anything.
    def _oi_sum(part):
        v = pd.to_numeric(part.get("open_interest"), errors="coerce")
        v = v.where(v >= 0)                       # -1 is UNKNOWN, never a count
        vol = pd.to_numeric(part.get("volume"), errors="coerce").fillna(0)
        known = v.notna()
        return (float(v.sum()),
                float(known.mean()) if len(v) else 0.0,
                float(vol[known].sum()))
    coi, coi_known, cv_oi = _oi_sum(calls)
    poi, poi_known, pv_oi = _oi_sum(puts)
    # ATM IV only. Enriching the WHOLE front chain solved IV on ~100 contracts to return one
    # number - the dominant cost of the whole backtest. Solve the nearest strike, walking out
    # a few if the closest quote is unusable.
    atm_iv = None
    calls_only = f[f["right"].astype(str).str.upper().str.startswith("C")].copy()
    if len(calls_only):
        calls_only["_d"] = (calls_only["strike"].astype(float) - underlying).abs()
        r_free = BS.risk_free_rate(asof)
        for _, r in calls_only.sort_values("_d").head(5).iterrows():
            bid, ask = r.get("bid"), r.get("ask")
            try:
                mid = (float(bid) + float(ask)) / 2.0
            except (TypeError, ValueError):
                continue
            T = (pd.Timestamp(r["expiration"]).date() - asof).days / 365.0
            v = BS.implied_vol(mid, underlying, float(r["strike"]), T, r_free, "C")
            if v:
                atm_iv = float(v)
                break
    return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi,
            # AUDIT B4: what share of each side had a REAL open-interest figure. An OI
            # ratio built on 20% coverage is not the same statistic as one on 100%.
            "call_oi_known_frac": coi_known, "put_oi_known_frac": poi_known,
            # AUDIT MA38: volume over the SAME rows those OI sums were taken over. `call_volume`
            # stays whole-chain because the put/call ratio wants it that way and volume coverage
            # is complete - it is only OI that goes missing. These exist so the ONE ratio that
            # mixes the two, `intraday.options.options_signals`'s volume-vs-OI bonus, can be
            # formed like-for-like. Absent on the live Tradier path, which ships no coverage
            # figure at all; the consumer falls back there and behaves exactly as before.
            "call_volume_oi_known": cv_oi, "put_volume_oi_known": pv_oi,
            "atm_iv": atm_iv}


# ============================ contract selection (the live rule) ==========================
def pick_contract(chain, underlying: float, as_of, right: str = "C",
                  target_delta: float = TARGET_DELTA, dte_range=DTE_RANGE):
    """The contract the live engine describes: ~35 delta, 45-75 DTE, on that day's chain.

    Returns the enriched row, or None when the chain has nothing tradable in the band. Returning
    None rather than relaxing the band matters: silently substituting a 10-delta lottery ticket
    would change the strategy while keeping its name.
    """
    import pandas as pd

    if chain is None or len(chain) == 0:
        return None
    asof = as_of if isinstance(as_of, dt.date) else dt.date.fromisoformat(str(as_of)[:10])
    d = chain.copy()
    d = d[d["right"].astype(str).str.upper().str.startswith(right.upper())]
    if len(d) == 0:
        return None
    exp = pd.to_datetime(d["expiration"]).dt.date
    dte = pd.Series([(e - asof).days for e in exp], index=d.index)
    d = d[(dte >= dte_range[0]) & (dte <= dte_range[1])]
    if len(d) == 0:
        return None
    # Narrow by moneyness FIRST. A ~35-delta call is a few percent OTM, so solving IV across
    # the whole ladder to locate it was the single biggest compute cost in the run.
    mny = d["strike"].astype(float) / float(underlying)
    lo, hi = (0.90, 1.20) if right.upper().startswith("C") else (0.80, 1.10)
    near = d[(mny >= lo) & (mny <= hi)]
    if len(near) == 0:
        near = d
    enr = BS.enrich_chain(near, underlying, asof)
    enr = enr.dropna(subset=["delta"])
    if len(enr) == 0:
        return None
    # Only contracts that would actually be fillable at entry.
    ok = []
    for _, r in enr.iterrows():
        q = F.Quote(bid=r.get("bid"), ask=r.get("ask"), oi=r.get("open_interest"),
                    volume=r.get("volume"))
        if F.quote_reject_reason(q) is None:
            ok.append(r)
    if not ok:
        return None
    best = min(ok, key=lambda r: abs(abs(float(r["delta"])) - target_delta))
    return best


# ============================ trade simulation ============================================
# ------------------------------------------------------------ corporate actions [U1-SPLIT] ---
# THE CANONICAL SPLIT HELPERS LIVE HERE, at the lowest level that needs them, and
# `composite_entry` delegates to them rather than carrying a second copy. A project that ends up
# with two split tables ends up with two answers.
#
# The defect these exist to close, reproduced in `PREREG_u1split_repair.md`: option chains are
# AS-TRADED and unadjusted for splits while `bars` are adjusted, and nothing consulted the split
# table. GE's 1-for-8 reverse split (2021-08-02) moves `raw_close` 12.95 -> 100.60 while the
# strike stays pre-split, and a $0.27 call books +31,921% against a true value of ZERO.
def load_splits(data_root: str) -> dict:
    """{ticker: [(iso_date, ratio)]} for every ticker with a real split. Ratio 1.0 is dropped."""
    p = os.path.join(data_root, "bulk", "prepared", "actions.pkl")
    with open(p, "rb") as f:
        act = pickle.load(f)
    out = {}
    for t, rec in act.items():
        ss = [(str(d)[:10], float(r)) for d, r in (rec.get("splits") or [])
              if r and abs(float(r) - 1.0) > 1e-9]
        if ss:
            out[str(t)] = sorted(ss)
    return out


def split_in_window(splits: dict, ticker: str, entry_date, expiry) -> bool:
    """True if a split falls in `(entry_date, expiry]` — the CONTRACT LIFE.

    The contract life, not the realised holding period, and the reason is measured rather than
    assumed: most affected rows never reach the settlement line at all. 106 of the 131 affected
    control rows exit on target or stop, i.e. on POST-SPLIT QUOTES — for a reverse split the OCC
    keeps the strike, so `contract_history`, which matches on exact strike, returns quotes that
    now refer to an adjusted deliverable, and a "+100% target hit" on that series is spurious.

    Judged at ENTRY so it is provably outcome-independent. Dropping only trades whose EXIT lands
    after the split would be keyed on exit timing, which is determined by the payoff.
    """
    ss = splits.get(str(ticker or "")) if splits else None
    if not ss:
        return False
    a = entry_date.isoformat() if hasattr(entry_date, "isoformat") else str(entry_date)[:10]
    e = expiry.isoformat() if hasattr(expiry, "isoformat") else str(expiry)[:10]
    return any(a < d <= e for d, _ in ss)


def simulate_trade(provider, ticker: str, entry_row, entry_date, bars: dict,
                   aggression: float = F.DEFAULT_AGGRESSION,
                   target_pct: float = TARGET_PCT, stop_pct: float = STOP_PCT,
                   time_stop_frac: float = TIME_STOP_FRAC,
                   splits: Optional[dict] = None) -> Optional[dict]:
    """Walk forward day by day; exit at the FIRST trigger. Never sees the whole path.

    `splits` defaults to None, which is the historical behaviour exactly — no caller that does
    not pass it changes by one digit. Callers that BUILD BOOKS pass it, and a candidate whose
    contract life crosses a split is refused before it is simulated.
    """
    import pandas as pd

    strike = float(entry_row["strike"])
    right = str(entry_row["right"])
    expiry = pd.Timestamp(entry_row["expiration"]).date()
    # U1-SPLIT. Refused BEFORE simulation, so the decision cannot depend on the outcome.
    if splits and split_in_window(splits, ticker, entry_date, expiry):
        return {"ok": False, "reason": "split_in_contract_life"}
    entry_q = F.Quote(bid=entry_row.get("bid"), ask=entry_row.get("ask"),
                      oi=entry_row.get("open_interest"), volume=entry_row.get("volume"))
    reason = F.quote_reject_reason(entry_q)
    if reason:
        return {"ok": False, "reason": reason}
    entry_fill = F.fill_price(entry_q, "buy", aggression)
    dte0 = (expiry - entry_date).days
    time_stop_date = entry_date + dt.timedelta(days=int(round(dte0 * time_stop_frac)))

    # ONE call for the contract's whole life, rather than a chain pull per holding day.
    hist = provider.contract_history(ticker, expiry, strike, right, entry_date, expiry)
    last_q, last_q_day = None, None
    n_skipped_days = n_exit_days = 0        # AUDIT B2: days censored from the exit path
    if hist is not None and len(hist):
        for _, row in hist.iterrows():
            day = row["date"]
            if day <= entry_date:
                continue
            q = F.Quote(bid=row.get("bid"), ask=row.get("ask"))
            # AUDIT B2 — the EXIT tolerance, not the entry one. This used to reject on
            # `wide_spread` and `thin_premium` as well, and a rejected day was skipped as though
            # it had never happened. A decaying OTM call quoting 0.25/0.35 is 33% wide, so it
            # vanished from its own exit path exactly where the -50% stop should fire: losers
            # that dipped through the stop on a wide-quote day and then recovered were recorded
            # as TARGET WINS. Now only a quote that is absent, non-positive or crossed is
            # unusable; a bad price is still a price and gets marked at the bid.
            if F.exit_reject_reason(q) is not None:
                n_skipped_days += 1
                continue
            n_exit_days += 1
            last_q, last_q_day = q, day
            mark = F.fill_price(q, "sell", aggression)
            ret = mark / entry_fill - 1.0
            hit_target = ret >= target_pct
            hit_stop = ret <= stop_pct
            if hit_target or hit_stop or day >= time_stop_date:
                t = F.round_trip(entry_q, q, right=right, strike=strike, aggression=aggression)
                # AUDIT B16: this used to `continue` on a not-ok round trip, silently skipping a
                # genuine exit trigger and letting the trade ride on. It is unreachable — the
                # entry quote cleared the liquidity filter at line 331 and `q` cleared the exit
                # filter just above — so if it ever fires, something upstream changed and the
                # right response is to say so, not to swallow the exit.
                if not t.get("ok"):
                    return {"ok": False, "reason": f"exit_trigger_unfillable:{t.get('reason')}"}
                t.update({"exit_date": day.isoformat(), "held_days": (day - entry_date).days,
                          "exit_reason": ("target" if hit_target else
                                          "stop" if hit_stop else "time_stop"),
                          "exit_days_used": n_exit_days,
                          "exit_days_skipped": n_skipped_days})   # AUDIT B2
                return t
    # Never triggered: hold to expiry and settle at intrinsic against the underlying.
    und = None
    _px = bars.get("raw_close") or bars["close"]      # as-traded: strikes are not adjusted
    for i, ds in enumerate(bars["date"]):
        if ds <= expiry.isoformat():
            und = _px[i]
    # AUDIT B3 — pass the AGE of `last_q`. It is the last quote that passed validation at ANY
    # point in the contract's life, so on a position that outlived its quotes it can be weeks
    # old; `round_trip` now prefers the payoff over that memory whenever a settle price exists.
    age = ((expiry - last_q_day).days if (last_q is not None and last_q_day is not None)
           else None)
    t = F.round_trip(entry_q, last_q, right=right, strike=strike, exit_underlying=und,
                     aggression=aggression, expired=True, exit_quote_age_days=age)
    if t.get("ok"):
        t.update({"exit_date": expiry.isoformat(), "held_days": (expiry - entry_date).days,
                  "exit_reason": "expiry",
                  "exit_days_used": n_exit_days,
                  "exit_days_skipped": n_skipped_days})           # AUDIT B2
    return t


def simulate_spread(provider, ticker, entry_row, entry_date, bars, chain,
                    underlying, aggression=F.DEFAULT_AGGRESSION,
                    target_pct=TARGET_PCT, stop_pct=STOP_PCT,
                    time_stop_frac=TIME_STOP_FRAC, short_delta=SHORT_LEG_DELTA):
    """The matched vertical debit spread: same long leg, short a further-OTM call.

    Both legs cross the spread in the punishing direction at BOTH ends - buy the long at the
    ask and sell the short at the bid on entry, then sell the long at the bid and buy the short
    back at the ask on exit. A spread backtest that nets legs at mid manufactures most of the
    "risk-adjusted improvement" that spreads are supposed to deliver.
    """
    import pandas as pd

    long_strike = float(entry_row["strike"])
    right = str(entry_row["right"])
    expiry = pd.Timestamp(entry_row["expiration"]).date()
    enr = BS.enrich_chain(
        chain[(pd.to_datetime(chain["expiration"]).dt.date == expiry)
              & (chain["right"].astype(str).str.upper().str.startswith("C"))],
        underlying, entry_date)
    if enr is None or len(enr) == 0:
        return {"ok": False, "reason": "no_short_leg"}
    cand = enr.dropna(subset=["delta"])
    cand = cand[cand["strike"].astype(float) > long_strike + MIN_SPREAD_STRIKE_GAP]
    ok = []
    for _, r in cand.iterrows():
        q = F.Quote(bid=r.get("bid"), ask=r.get("ask"), oi=r.get("open_interest"),
                    volume=r.get("volume"))
        if F.quote_reject_reason(q) is None:
            ok.append(r)
    if not ok:
        return {"ok": False, "reason": "no_short_leg"}
    short_row = min(ok, key=lambda r: abs(abs(float(r["delta"])) - short_delta))
    short_strike = float(short_row["strike"])

    lq = F.Quote(bid=entry_row.get("bid"), ask=entry_row.get("ask"),
                 oi=entry_row.get("open_interest"), volume=entry_row.get("volume"))
    sq = F.Quote(bid=short_row.get("bid"), ask=short_row.get("ask"),
                 oi=short_row.get("open_interest"), volume=short_row.get("volume"))
    if F.quote_reject_reason(lq) or F.quote_reject_reason(sq):
        return {"ok": False, "reason": "unfillable_leg"}
    # Entry debit: pay the ask on the long, receive the bid on the short.
    debit = F.fill_price(lq, "buy", aggression) - F.fill_price(sq, "sell", aggression)
    if debit <= 0:
        return {"ok": False, "reason": "non_positive_debit"}

    lh = provider.contract_history(ticker, expiry, long_strike, right, entry_date, expiry)
    sh = provider.contract_history(ticker, expiry, short_strike, right, entry_date, expiry)
    if lh is None or len(lh) == 0 or sh is None or len(sh) == 0:
        return {"ok": False, "reason": "no_leg_history"}
    sh_by = {r["date"]: r for _, r in sh.iterrows()}
    dte0 = (expiry - entry_date).days
    time_stop_date = entry_date + dt.timedelta(days=int(round(dte0 * time_stop_frac)))
    last = None
    for _, lr in lh.iterrows():
        day = lr["date"]
        if day <= entry_date or day not in sh_by:
            continue
        srr = sh_by[day]
        lq2 = F.Quote(bid=lr.get("bid"), ask=lr.get("ask"))
        sq2 = F.Quote(bid=srr.get("bid"), ask=srr.get("ask"))
        if (F.quote_reject_reason(lq2, check_liquidity=False)
                or F.quote_reject_reason(sq2, check_liquidity=False)):
            continue
        # Exit credit: sell the long at the bid, buy the short back at the ask.
        credit = F.fill_price(lq2, "sell", aggression) - F.fill_price(sq2, "buy", aggression)
        last = credit
        ret = credit / debit - 1.0
        if ret >= target_pct or ret <= stop_pct or day >= time_stop_date:
            return _spread_result(debit, credit, day, entry_date,
                                  "target" if ret >= target_pct else
                                  "stop" if ret <= stop_pct else "time_stop",
                                  long_strike, short_strike)
    # Held to expiry: the spread settles at its intrinsic width.
    und = None
    _px = bars.get("raw_close") or bars["close"]      # as-traded: strikes are not adjusted
    for i, ds in enumerate(bars["date"]):
        if ds <= expiry.isoformat():
            und = _px[i]
    if und is None:
        return {"ok": False, "reason": "no_settle_price"}
    credit = (F.intrinsic(right, long_strike, und) - F.intrinsic(right, short_strike, und))
    return _spread_result(debit, credit, expiry, entry_date, "expiry",
                          long_strike, short_strike)


# ============================ SECTION 4 RESULT: SPREAD REJECTED =============================
# Run on 1,313 matched pairs (same alert, same day, same long leg; 227 alerts had no fillable
# short leg). The hypothesis was that capping vega/theta trades the fragile tail for a steadier
# edge. It does not - it removes the edge:
#
#     single-leg      exp +12.33%/trade   hit 38%   pf 1.36
#     vert spread     exp  -4.46%/trade   hit 36%   pf 0.88
#
#     by IV regime    low  +21.14% vs  +2.35%    mid +6.57% vs -9.22%    high +15.04% vs -1.73%
#     held-out        first +19.15% vs +0.50%    second +5.51% vs -9.41%
#
# Worse in every IV regime and both held-out halves, and it does not even deliver the higher hit
# rate that was its rationale (36% vs 38%). The mechanism is the exit rule: the live target is
# +100% ON THE DEBIT, but a debit spread's maximum value is the strike width, so +100% often sits
# at or near the spread's ceiling. Targets therefore rarely fill while the -50% stop still
# triggers normally - the payoff is truncated on the winning side and intact on the losing one.
# REJECTED against the pre-committed +0.10 expectancy bar (it is 16.8pp WORSE). Kept for the
# record and for anyone tempted to re-open it; a credit/short-vol construction is a different
# strategy and remains untested here.
def _spread_result(debit, credit, exit_day, entry_date, reason, long_strike, short_strike):
    mult = F.CONTRACT_MULTIPLIER
    commission = F.COMMISSION_PER_CONTRACT * 4          # two legs, both ways
    return {"ok": True, "entry_fill": debit, "exit_fill": credit,
            "net_pnl": (credit - debit) * mult - commission,
            "gross_pnl": (credit - debit) * mult,
            "cost": commission, "contracts": 1,
            "return_pct": (credit / debit - 1.0) if debit > 0 else None,
            "exit_date": exit_day.isoformat(), "held_days": (exit_day - entry_date).days,
            "exit_reason": reason, "long_strike": long_strike, "short_strike": short_strike,
            "entry_spread_pct": None, "settled_at_intrinsic": reason == "expiry"}


def to_alert_row(ticker, entry_date, entry_row, trade, score, labels, iv, iv_rank) -> dict:
    """The `option_alerts` row shape, so options_tracker._stats can score it unchanged."""
    import pandas as pd

    return {
        "alert_ts": entry_date.isoformat(), "ticker": ticker,
        "opt_right": "call" if str(entry_row["right"]).upper().startswith("C") else "put",
        "strike": float(entry_row["strike"]),
        "expiry": str(pd.Timestamp(entry_row["expiration"]).date()),
        "entry_premium": trade.get("entry_fill"), "exit_premium": trade.get("exit_fill"),
        "pnl_pct": trade.get("return_pct"), "pnl_dollars": trade.get("net_pnl"),
        "score": score, "labels": labels, "horizon": HORIZON,
        "iv": iv, "iv_rank": iv_rank,
        "target_delta": float(entry_row.get("delta")) if entry_row.get("delta") is not None else None,
        "dte": int(entry_row.get("dte")) if entry_row.get("dte") is not None else None,
        "flow_read": next((l for l in (labels or [])
                           if "call" in l.lower() or "put" in l.lower()), None),
        "exit_reason": trade.get("exit_reason"), "held_days": trade.get("held_days"),
        "status": "closed",
    }


def expectancy_report(rows, dims=None) -> dict:
    """Overall + per-bucket expectancy, computed by the LIVE scorecard functions."""
    from .options_tracker import BUCKET_DIMS, _bucket_of, _stats

    dims = dims or BUCKET_DIMS
    out = {"overall": _stats(rows), "buckets": {}}
    for dim in dims:
        groups = {}
        for r in rows:
            b = _bucket_of(r, dim)
            if b is not None:
                groups.setdefault(b, []).append(r)
        if groups:
            out["buckets"][dim] = {b: _stats(rs) for b, rs in sorted(groups.items())}
    return out
