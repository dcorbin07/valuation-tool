"""
The validated single-leg engine, wired to the LIVE chain.

--------------------------------------------------------------------------------------------
THE ONE RULE THIS MODULE EXISTS TO ENFORCE: NO SECOND IMPLEMENTATION.

The scream-buy edge was validated by `options_backtest`, which reconstructed alerts by importing
and calling the live scan's own functions. That is why the backtest and the forward scorecard
cannot disagree. The obvious way to ruin it is to write a "live version" of contract selection
here that starts identical and drifts one commit at a time.

So this module selects nothing itself. It NORMALISES a broker chain into the frame shape the
backtest already consumes and then calls `options_backtest.pick_contract` - the exact function,
with the exact constants (`TARGET_DELTA` 0.35, `DTE_RANGE` 45-75, `HORIZON` swing), imported
rather than restated. If somebody re-tunes the band in the backtest, the live path moves with it.
`test_live_engine_reuses_the_backtested_selector` fails if this file ever grows its own copy.

Consequences worth stating, because they are choices:

  * DELTA IS RE-SOLVED FROM THE MID BY BLACK-SCHOLES, not taken from the broker's greeks, even
    though Tradier serves `greeks.delta` for free. The backtest's 35-delta target is defined in
    terms of the BS-from-mid delta that `blackscholes.enrich_chain` computes, and phase 1
    validated that estimator against ThetaData's own greeks (98.96% agreement, median error
    0.0016). Using a different estimator live would silently retarget the strategy. The broker's
    delta is still recorded as `broker_delta` so a large divergence surfaces as data, not as a
    quietly different trade.
  * THE LIQUIDITY GATE IS THE BACKTEST'S. `options_fill.quote_reject_reason` decides what is
    fillable, so a live alert cannot be issued on a contract the backtest would have refused.
  * ENTRY PREMIUM IS THE ASK, not the mid. The validated numbers are net of the punishing fill
    (`options_fill.DEFAULT_AGGRESSION` = 1.0, buy the ask / sell the bid). Sizing a live position
    off the mid would deploy more contracts than the tested book and quote a cheaper entry than
    anyone gets.

--------------------------------------------------------------------------------------------
TERM STRUCTURE: WHICH IV SERIES, AND WHY IT IS RECORDED.

`term_slope` = (~60-DTE ATM IV) - (front-expiry ATM IV), threshold 0.0105, fitted on 2016-2020
and applied unchanged to 2021-2025. The threshold is roughly ONE VOL POINT, which is small
enough that the IV ESTIMATOR MATTERS: the backtest solved IV from the mid by bisection, while a
broker serves its own smoothed surface (Tradier `mid_iv` / `smv_vol`). Those are not the same
number, and a threshold fitted on one does not automatically transfer to the other.

So `term_read` prefers the chain and solves IV the backtested way, falls back to the broker's
published IV when no chain is at hand, and always reports which one it used in `source`. The
live discard rate is logged for the same reason: the backtest kept 40.6% of alerts, so a live
retention rate near 40% is evidence the threshold transferred, and 5% or 90% is evidence it did
not. That check is the point of `term_filter_stats`, not bookkeeping.

--------------------------------------------------------------------------------------------
WHAT THIS MODULE WILL NOT DO.

It produces a SUGGESTION: a contract, a confidence, and a contract count against a dollar risk
budget. It does not place, route, or stage an order, and nothing here touches a broker's trading
endpoints. Autotrade is a separate, gated, later phase.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from . import options_fill as F
from . import options_backtest as OB
from . import options_confidence as C
from . import options_sizing as SZ
from ..intraday import term_filter as TF

# Re-exported so callers name the validated constants rather than literals. Imported, never
# restated - see the module docstring.
TARGET_DELTA = OB.TARGET_DELTA          # 0.35
DTE_RANGE = OB.DTE_RANGE                # (45, 75)
HORIZON = OB.HORIZON                    # "swing"
RIGHT = "C"                             # long call - the validated direction
TARGET_PCT = OB.TARGET_PCT              # +100%
STOP_PCT = OB.STOP_PCT                  # -50%
TIME_STOP_FRAC = OB.TIME_STOP_FRAC      # half the original DTE

# The backtest's late-half retention under the term gate. Live retention is compared against it
# so a threshold that failed to transfer between IV estimators shows up as a number.
BACKTEST_TERM_RETENTION = 0.406

DEFAULT_RISK_BUDGET = SZ.RISK_PER_TRADE  # $1,000 per signal


# ============================ chain normalisation =========================================
def normalize_chain(rows) -> "object":
    """Broker chain rows -> the DataFrame `options_backtest` consumes. None if unusable.

    Accepts Tradier's shape (`option_type`, `expiration_date`, nested `greeks`) and the already
    normalised shape, so a different provider only has to supply the same field names.
    """
    if not rows:
        return None
    import pandas as pd

    recs = []
    for o in rows:
        if not isinstance(o, dict):
            continue
        right = o.get("right") or o.get("option_type")
        expiry = o.get("expiration") or o.get("expiration_date")
        strike = o.get("strike")
        if right is None or expiry is None or strike is None:
            continue
        g = o.get("greeks") or {}
        recs.append({
            "right": str(right)[:1].upper(),
            "expiration": str(expiry)[:10],
            "strike": strike,
            "bid": o.get("bid"),
            "ask": o.get("ask"),
            "volume": o.get("volume"),
            "open_interest": o.get("open_interest"),
            "broker_delta": g.get("delta"),
            "broker_iv": g.get("mid_iv") or g.get("smv_vol"),
            "underlying_price": o.get("underlying_price"),
        })
    if not recs:
        return None
    return pd.DataFrame(recs)


def _atm_iv_bs(df, underlying: float, asof: _dt.date, expiry) -> Optional[float]:
    """ATM IV of one expiry, solved from the mid exactly as the backtest solves it."""
    from . import blackscholes as BS

    leg = df[df["expiration"].astype(str).str[:10] == str(expiry)[:10]]
    if leg is None or len(leg) == 0:
        return None
    enr = BS.enrich_chain(leg, underlying, asof)
    if enr is None or len(enr) == 0:
        return None
    near = enr.dropna(subset=["iv"]).copy()
    if not len(near):
        return None
    near["_d"] = (near["strike"].astype(float) - float(underlying)).abs()
    return float(near.sort_values("_d")["iv"].iloc[0])


# ============================ contract selection ==========================================
def pick_live_contract(chain_rows, underlying: float, as_of=None,
                       right: str = RIGHT) -> Optional[dict]:
    """The live contract, chosen by the BACKTESTED selector. None when nothing qualifies.

    None is the correct answer rather than a relaxed band: substituting a cheaper, further-OTM
    contract would keep the alert while changing the strategy it represents.
    """
    df = normalize_chain(chain_rows)
    if df is None or not underlying or float(underlying) <= 0:
        return None
    asof = _as_date(as_of)

    row = OB.pick_contract(df, float(underlying), asof, right=right,
                           target_delta=TARGET_DELTA, dte_range=DTE_RANGE)
    if row is None:
        return None

    bid, ask = F._f(row.get("bid")), F._f(row.get("ask"))
    q = F.Quote(bid=bid, ask=ask, oi=row.get("open_interest"), volume=row.get("volume"))
    # The ask, because the validated book is net of the punishing fill.
    entry = F.fill_price(q, "buy", aggression=F.DEFAULT_AGGRESSION)
    if entry is None or entry <= 0:
        return None

    expiry = str(row.get("expiration"))[:10]
    strike = float(row.get("strike"))
    delta = F._f(row.get("delta"))
    dte = (_dt.date.fromisoformat(expiry) - asof).days
    broker_delta = F._f(row.get("broker_delta"))
    return {
        "ticker": None,                       # filled by the caller
        "right": "call" if right.upper().startswith("C") else "put",
        "strike": strike,
        "expiry": expiry,
        "dte": dte,
        "delta": delta,
        "broker_delta": broker_delta,
        # A large gap means the broker's surface and a mid-solved BS delta disagree, which is a
        # data problem worth seeing rather than an excuse to pick a different contract.
        "delta_source_gap": (None if (delta is None or broker_delta is None)
                             else round(abs(abs(delta) - abs(broker_delta)), 4)),
        "iv": F._f(row.get("iv")),
        "bid": bid, "ask": ask, "mid": q.mid,
        "entry_premium": round(float(entry), 4),
        "premium_basis": "ask (punishing fill, matches the backtested book)",
        "open_interest": F._f(row.get("open_interest")),
        "volume": F._f(row.get("volume")),
        # Left None on purpose: the OCC id needs the ticker, which this function does not know.
        # A placeholder here would be a plausible-looking wrong symbol, and the dedupe key in
        # options_tracker is built from it. `build_alert` fills it once the ticker is attached.
        "occ_symbol": None,
        "target_delta": TARGET_DELTA,
        "dte_range": list(DTE_RANGE),
        "exit_policy": {"target_pct": TARGET_PCT, "stop_pct": STOP_PCT,
                        "time_stop_frac": TIME_STOP_FRAC},
    }


def _as_date(as_of) -> _dt.date:
    if isinstance(as_of, _dt.date):
        return as_of
    if as_of:
        return _dt.date.fromisoformat(str(as_of)[:10])
    return _dt.date.today()


# ============================ term structure, live ========================================
def term_read(chain_rows=None, summary: Optional[dict] = None, underlying: Optional[float] = None,
              as_of=None, threshold: float = TF.TERM_SLOPE_THRESHOLD) -> dict:
    """{term_slope, term_ok, reason, source}. Unknown is never treated as backwardation.

    Prefers the chain (IV solved from the mid, the way the threshold was fitted) and falls back
    to the broker's published IV. `source` records which, because a ~1 vol point threshold is
    small enough that the estimator can decide the answer.
    """
    if chain_rows is not None and underlying:
        df = normalize_chain(chain_rows)
        if df is not None and len(df):
            asof = _as_date(as_of)
            exps = sorted({str(e)[:10] for e in df["expiration"]
                           if _safe_date(e) and _safe_date(e) > asof})
            if len(exps) >= 2:
                front = exps[0]
                mid_exp = min(exps, key=lambda e: abs((_dt.date.fromisoformat(e) - asof).days - 60))
                if mid_exp != front:
                    f_iv = _atm_iv_bs(df, float(underlying), asof, front)
                    m_iv = _atm_iv_bs(df, float(underlying), asof, mid_exp)
                    if f_iv and m_iv:
                        out = TF.classify({"atm_iv": f_iv, "atm_iv_60d": m_iv}, threshold)
                        out["source"] = "chain (BS-from-mid, as fitted)"
                        out["front_expiry"], out["far_expiry"] = front, mid_exp
                        return out
    out = TF.classify(summary, threshold)
    out["source"] = ("broker IV (estimator differs from the fitted series)"
                     if out.get("term_slope") is not None else "unavailable")
    return out


def _safe_date(v):
    try:
        return _dt.date.fromisoformat(str(v)[:10])
    except (TypeError, ValueError):
        return None


def term_filter_stats(reads) -> dict:
    """Live retention under the term gate, against the backtested 40.6%.

    The comparison is the point: it is how we find out whether a threshold fitted on
    BS-solved ThetaData IV transferred to a live broker surface at all.
    """
    kept = sum(1 for r in reads if r.get("term_ok") is True)
    dropped = sum(1 for r in reads if r.get("term_ok") is False)
    unknown = sum(1 for r in reads if r.get("term_ok") is None)
    known = kept + dropped
    retention = (kept / known) if known else None
    note = "no alerts with a readable term structure yet"
    if known:
        if known < 30:
            note = (f"live retention {retention:.1%} on only {known} readable alerts - too thin "
                    f"to compare against the backtested {BACKTEST_TERM_RETENTION:.1%}")
        elif abs(retention - BACKTEST_TERM_RETENTION) <= 0.15:
            note = (f"live retention {retention:.1%} is consistent with the backtested "
                    f"{BACKTEST_TERM_RETENTION:.1%} - the threshold appears to have transferred")
        else:
            note = (f"live retention {retention:.1%} DIVERGES from the backtested "
                    f"{BACKTEST_TERM_RETENTION:.1%} - the threshold may not transfer across IV "
                    f"estimators; investigate before trusting the filter live")
    return {"n_alerts": len(reads), "kept": kept, "discarded": dropped, "unknown": unknown,
            "retention": retention, "backtest_retention": BACKTEST_TERM_RETENTION,
            "note": note}


# ============================ sizing suggestion ===========================================
def suggest_position(entry_premium: Optional[float], risk_budget: float = DEFAULT_RISK_BUDGET,
                     size_scale: float = 1.0) -> dict:
    """Whole contracts to a dollar risk budget. A SUGGESTION - never routed anywhere.

    Two rules that are easy to get wrong and are therefore explicit:

      * SKIP, DO NOT ROUND UP. If one contract already costs more than the budget the alert is
        skipped, because you cannot buy a fraction of a contract and taking one anyway silently
        breaks the risk rule. 13.0% of backtested signals fall here at a $1,000 budget.
      * THE SKIP TEST USES THE FULL BUDGET, NOT THE CONFIDENCE-SCALED ONE. Otherwise a
        moderate-confidence alert would be dropped for affordability rather than for conviction,
        and the confidence scale would quietly become a second liquidity filter.
    """
    prem = F._f(entry_premium)
    if prem is None or prem <= 0:
        return {"skip": True, "reason": "no entry premium", "contracts": 0,
                "dollar_risk": None, "risk_budget": risk_budget}
    if SZ.contracts_for(prem, risk_budget) == 0:
        cost = prem * SZ.CONTRACT_MULTIPLIER
        return {"skip": True,
                "reason": (f"one contract costs ${cost:,.0f}, above the ${risk_budget:,.0f} "
                           f"budget - cannot be sized correctly"),
                "contracts": 0, "cost_per_contract": round(cost, 2),
                "dollar_risk": None, "risk_budget": risk_budget}
    scaled = risk_budget * max(0.0, float(size_scale))
    n = SZ.contracts_for(prem, scaled)
    if n == 0 and size_scale > 0:
        n = 1                     # affordable at full budget, so a single contract is allowed
    if n == 0:
        return {"skip": True, "reason": "confidence scale is zero (avoid)", "contracts": 0,
                "dollar_risk": 0.0, "risk_budget": risk_budget}
    risk = prem * SZ.CONTRACT_MULTIPLIER * n
    return {"skip": False, "contracts": n,
            "cost_per_contract": round(prem * SZ.CONTRACT_MULTIPLIER, 2),
            "dollar_risk": round(risk, 2), "risk_budget": risk_budget,
            "size_scale": size_scale,
            "max_loss": round(risk, 2),
            "note": ("Max loss is the full premium - a long option can expire worthless. "
                     "Suggestion only; nothing is routed to a broker."),
            }


# ============================ the whole live alert ========================================
def build_alert(scan_row: dict, chain_rows=None, as_of=None,
                risk_budget: float = DEFAULT_RISK_BUDGET,
                term_threshold: float = TF.TERM_SLOPE_THRESHOLD) -> dict:
    """One scan row -> the full live alert: contract, term read, confidence, sizing.

    Degrades honestly rather than failing: with no chain the alert still carries its score, its
    term read from the broker summary, and a confidence based on what IS known - it simply
    cannot carry a contract or a size, and says so.
    """
    detail = scan_row.get("detail") or {}
    underlying = scan_row.get("price") or detail.get("price")
    summary = {"atm_iv": detail.get("opt_atm_iv"), "atm_iv_60d": detail.get("opt_atm_iv_60d")}

    term = term_read(chain_rows=chain_rows, summary=summary, underlying=underlying,
                     as_of=as_of, threshold=term_threshold)
    contract = pick_live_contract(chain_rows, underlying, as_of) if chain_rows else None
    if contract:
        contract["ticker"] = scan_row.get("ticker")
        from .options_tracker import occ_symbol
        contract["occ_symbol"] = occ_symbol(scan_row.get("ticker"), contract["expiry"],
                                            "call", contract["strike"])

    conf = C.confidence(atm_iv=(contract or {}).get("iv") or detail.get("opt_atm_iv"),
                        dte=(contract or {}).get("dte"),
                        delta=(contract or {}).get("delta"),
                        term_ok=term.get("term_ok"))
    sizing = (suggest_position((contract or {}).get("entry_premium"), risk_budget,
                               conf["size_scale"])
              if contract else
              {"skip": True, "reason": "no live contract available", "contracts": 0,
               "dollar_risk": None, "risk_budget": risk_budget})

    return {
        "ticker": scan_row.get("ticker"),
        "score": scan_row.get("score"),
        "labels": scan_row.get("labels") or [],
        "price": underlying,
        "horizon": HORIZON,
        "term": term,
        "contract": contract,
        "confidence": conf,
        "sizing": sizing,
        "actionable": bool(contract and not sizing.get("skip")
                           and term.get("term_ok") is not False),
        "not_advice": ("Educational only. A suggestion, not an order - Valquo never places "
                       "trades."),
    }


def build_alerts(scan_rows, provider=None, as_of=None,
                 risk_budget: float = DEFAULT_RISK_BUDGET,
                 term_threshold: float = TF.TERM_SLOPE_THRESHOLD):
    """Full live alerts for a list of scan rows. Returns (alerts, stats).

    The chain fetch is per-ticker and several HTTP calls deep, so a failure on one name must not
    take down the alert run: it degrades that alert to "no contract" and continues. `stats`
    reports how often that happened, because an alert path that silently stops producing
    contracts would otherwise look identical to a quiet market.
    """
    alerts, reads = [], []
    stats = {"n": 0, "with_contract": 0, "chain_failures": 0, "sized": 0, "skipped_too_costly": 0}
    for row in scan_rows or []:
        stats["n"] += 1
        chain = None
        if provider is not None:
            try:
                chain = provider.get_option_chain(row.get("ticker"), DTE_RANGE)
            except Exception:                                        # noqa: BLE001
                chain = None
            if chain is None:
                stats["chain_failures"] += 1
        a = build_alert(row, chain_rows=chain, as_of=as_of, risk_budget=risk_budget,
                        term_threshold=term_threshold)
        if a.get("contract"):
            stats["with_contract"] += 1
        if not (a.get("sizing") or {}).get("skip"):
            stats["sized"] += 1
        elif "budget" in str((a.get("sizing") or {}).get("reason", "")):
            stats["skipped_too_costly"] += 1
        reads.append(a["term"])
        alerts.append(a)
    stats["term_filter"] = term_filter_stats(reads)
    return alerts, stats
