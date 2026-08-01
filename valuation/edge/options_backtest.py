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
                return pickle.load(f)
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
                      "qopts.columns": "date,closeadj,volume"}
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
               "close": [float(r[1]) for r in rows],
               "volume": [float(r[2] or 0) for r in rows]}
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
            "high": bars["close"][lo:hi + 1], "low": bars["close"][lo:hi + 1]}


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
    coi = float(pd.to_numeric(calls.get("open_interest"), errors="coerce").fillna(0).sum())
    poi = float(pd.to_numeric(puts.get("open_interest"), errors="coerce").fillna(0).sum())
    atm_iv = None
    enr = BS.enrich_chain(f, underlying, asof)
    if enr is not None and len(enr):
        near = enr.dropna(subset=["iv"]).copy()
        if len(near):
            near["dist"] = (near["strike"] - underlying).abs()
            atm_iv = float(near.sort_values("dist")["iv"].iloc[0])
    return {"call_volume": cv, "put_volume": pv, "call_oi": coi, "put_oi": poi,
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
    enr = BS.enrich_chain(d, underlying, asof)
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
def simulate_trade(provider, ticker: str, entry_row, entry_date, bars: dict,
                   aggression: float = F.DEFAULT_AGGRESSION,
                   target_pct: float = TARGET_PCT, stop_pct: float = STOP_PCT,
                   time_stop_frac: float = TIME_STOP_FRAC) -> Optional[dict]:
    """Walk forward day by day; exit at the FIRST trigger. Never sees the whole path."""
    import pandas as pd

    strike = float(entry_row["strike"])
    right = str(entry_row["right"])
    expiry = pd.Timestamp(entry_row["expiration"]).date()
    entry_q = F.Quote(bid=entry_row.get("bid"), ask=entry_row.get("ask"),
                      oi=entry_row.get("open_interest"), volume=entry_row.get("volume"))
    reason = F.quote_reject_reason(entry_q)
    if reason:
        return {"ok": False, "reason": reason}
    entry_fill = F.fill_price(entry_q, "buy", aggression)
    dte0 = (expiry - entry_date).days
    time_stop_date = entry_date + dt.timedelta(days=int(round(dte0 * time_stop_frac)))

    dates = [d for d in bars["date"] if entry_date.isoformat() < d <= expiry.isoformat()]
    last_q = None
    for ds in dates:
        day = dt.date.fromisoformat(ds)
        ch = provider.chain_on(ticker, day)
        if ch is None or len(ch) == 0:
            continue
        m = ch[(ch["strike"].astype(float) == strike)
               & (ch["right"].astype(str).str.upper() == right.upper())
               & (pd.to_datetime(ch["expiration"]).dt.date == expiry)]
        if len(m) == 0:
            continue
        row = m.iloc[-1]
        q = F.Quote(bid=row.get("bid"), ask=row.get("ask"))
        if F.quote_reject_reason(q, check_liquidity=False) is not None:
            continue
        last_q = q
        mark = F.fill_price(q, "sell", aggression)
        ret = mark / entry_fill - 1.0
        hit_target = ret >= target_pct
        hit_stop = ret <= stop_pct
        if hit_target or hit_stop or day >= time_stop_date:
            t = F.round_trip(entry_q, q, right=right, strike=strike, aggression=aggression)
            if not t.get("ok"):
                continue
            t.update({"exit_date": ds, "held_days": (day - entry_date).days,
                      "exit_reason": ("target" if hit_target else
                                      "stop" if hit_stop else "time_stop")})
            return t
    # Never triggered: hold to expiry and settle at intrinsic against the underlying.
    und = None
    for i, ds in enumerate(bars["date"]):
        if ds <= expiry.isoformat():
            und = bars["close"][i]
    t = F.round_trip(entry_q, last_q, right=right, strike=strike, exit_underlying=und,
                     aggression=aggression, expired=True)
    if t.get("ok"):
        t.update({"exit_date": expiry.isoformat(), "held_days": (expiry - entry_date).days,
                  "exit_reason": "expiry"})
    return t


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
