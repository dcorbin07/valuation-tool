"""
Scream-buy options tracker — log the contract, score the expectancy, then tune.

WHY THIS REPLACES THE OLD REPORTING. The old `options_exit.py` (now in `edge/archive/`,
imported by nothing — AUDIT B16) measured the UNDERLYING's move under an
exit discipline. That was honest about its own limits but it answers the wrong question twice
over: an option's P&L is not the stock's move (premium, theta and vega all sit in between), and
a bare "success rate" is meaningless for a payoff this asymmetric — a 40%-hit-rate strategy
whose winners triple and losers halve is excellent, and a 70%-hit-rate strategy that gives it
all back on the losers is not. Hit rate without win/loss SIZE tells you nothing.

So this module does three things:

  1. LOG every alert with its fingerprint AND the specific contract (ticker, right, strike,
     expiry, entry premium) — the features that fired it are stored so "which setups pay" is
     answerable later rather than lost.
  2. SCORE closed trades on EXPECTANCY: hit rate, average win, average loss, profit factor,
     expectancy per trade, and cumulative P&L on a fixed 1-contract basis.
  3. TUNE only once there is enough evidence. `MIN_CLOSED_PER_BUCKET` is a hard floor: options
     outcomes are noisy and a handful of trades will always produce a flattering-looking
     subgroup. Nothing here changes a criterion below it.

WHERE OUTCOMES COME FROM. Real fills and contract marks live in the Robinhood connector, which
the web app cannot reach. This app writes the alert; an external scheduled process (Cowork)
writes `exit_*` back via `record_outcome`. Everything here is therefore designed to be useful
while outcomes are still missing — an open alert is a complete record of the setup, and the
scorecard simply reports how few closed trades exist yet.
"""
from __future__ import annotations

import json
from typing import Optional

# Hard floor before ANY criterion may be tuned on a bucket. Options outcomes are noisy and
# heavy-tailed: with ten trades a single triple-up decides the sign of every statistic. 30 is
# not a magic number, it is "enough that one lucky contract cannot flip the verdict".
MIN_CLOSED_PER_BUCKET = 30

# Contract exit discipline. Recorded on the alert so an external filler knows what to apply,
# and so a later change of policy is visible in the data rather than silently retroactive.
DEFAULT_TARGET_PCT = 1.00      # +100% on the premium — take the double
DEFAULT_STOP_PCT = -0.50       # -50% on the premium
DEFAULT_TIME_STOP_FRAC = 0.50  # or close at half the original DTE, whichever comes first

_FIELDS = ("alert_ts", "ticker", "opt_right", "strike", "expiry", "occ_symbol",
           "entry_premium", "underlying_price", "score", "momentum_score", "technical_score",
           "iv", "iv_rank", "horizon", "target_delta", "dte", "flow_read", "labels",
           "features", "record_epoch")


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def occ_symbol(ticker, expiry, right, strike) -> Optional[str]:
    """Canonical OCC option id, e.g. AAPL261218C00250000.

    Used as the dedupe key with the alert timestamp, so the same contract alerted twice in one
    run is stored once, while a genuinely new alert on a later day is its own row.
    """
    if not (ticker and expiry and right and strike is not None):
        return None
    try:
        y, m, d = str(expiry)[:10].split("-")
        cp = "C" if str(right).lower().startswith("c") else "P"
        return f"{str(ticker).upper()}{y[2:]}{m}{d}{cp}{int(round(float(strike) * 1000)):08d}"
    except (ValueError, AttributeError):
        return None


def log_alert(store, alert: dict) -> Optional[int]:
    """Record one scream-buy alert + its contract. Returns the row id, or None if duplicate.

    Deliberately permissive about MISSING contract detail: when the chain is unavailable the
    alert is still worth recording (ticker, timestamp, fingerprint), because the fingerprint is
    what the tuning loop learns from. A row with no strike simply cannot be scored later.
    """
    a = dict(alert or {})
    if not a.get("ticker") or not a.get("alert_ts"):
        return None
    a["ticker"] = str(a["ticker"]).upper()
    a.setdefault("occ_symbol", occ_symbol(a.get("ticker"), a.get("expiry"),
                                          a.get("opt_right"), a.get("strike")))
    for k in ("labels", "features"):
        if isinstance(a.get(k), (list, dict)):
            a[k] = json.dumps(a[k], sort_keys=True)
    # Stamp the epoch here rather than at the call site, so every caller of the logger lands in
    # the right era of the record. A row written without one would silently join the ORIGINAL
    # record, which after a reset is precisely the record it does not belong to.
    from . import scream_log as _SL
    _SL.ensure_schema(store)
    a.setdefault("record_epoch", _SL.current_epoch(store))
    cols = [c for c in _FIELDS if c in a]
    sql = (f"INSERT OR IGNORE INTO option_alerts ({','.join(cols)}, status) "
           f"VALUES ({','.join('?' * len(cols))}, 'open')")
    with store._conn() as c:
        cur = c.execute(sql, [a.get(k) for k in cols])
        return cur.lastrowid if cur.rowcount else None


def record_outcome(store, alert_id=None, occ=None, alert_ts=None, ticker=None,
                   exit_premium=None, exit_ts=None, exit_reason=None,
                   contracts: int = 1, entry_premium=None) -> bool:
    """Write a realized outcome back. Called by the EXTERNAL (Cowork/Robinhood) job.

    P&L is computed here rather than trusted from the caller, so the scorecard cannot silently
    disagree with the stored premiums. `pnl_dollars` is on a fixed 1-contract, 100-share basis:
    the point is comparing setups, not modelling position sizing.

    AUDIT B5d — `entry_premium` overrides the ALERT-TIME entry with the price actually PAID.
    The paper track fills at the broker and stores that fill in
    `paper_option_orders.entry_premium`, but this function read `option_alerts.entry_premium`,
    which is the ask quoted when the alert fired. So the broker fill was decorative for return
    purposes and the stored paper fill was never used — in the one book whose entire purpose is
    to measure what a real account would have got. When the override is supplied the basis is
    recorded in `exit_reason` so a row's provenance is readable after the fact.
    """
    ex = _f(exit_premium)
    if ex is None:
        return False
    where, args = [], []
    if alert_id is not None:
        where, args = ["id = ?"], [alert_id]
    elif occ and alert_ts:
        where, args = ["occ_symbol = ?", "alert_ts = ?"], [occ, alert_ts]
    elif ticker and alert_ts:
        where, args = ["ticker = ?", "alert_ts = ?"], [str(ticker).upper(), alert_ts]
    else:
        return False
    with store._conn() as c:
        row = c.execute(f"SELECT id, entry_premium FROM option_alerts "
                        f"WHERE {' AND '.join(where)} AND status = 'open'", args).fetchone()
        if not row:
            return False
        rid, entry = row[0], _f(row[1])
        _paid = _f(entry_premium)                    # AUDIT B5d: the price actually paid
        if _paid is not None and _paid > 0:
            entry = _paid
            exit_reason = f"{exit_reason or 'exit'} [pnl vs fill]"
        if entry is None or entry <= 0:
            # No entry premium means no P&L is computable; close it as unscoreable rather than
            # inventing a return.
            c.execute("UPDATE option_alerts SET status='closed', exit_ts=?, exit_premium=?, "
                      "exit_reason=? WHERE id=?",
                      (exit_ts, ex, exit_reason or "no entry premium", rid))
            return True
        pnl_pct = ex / entry - 1.0
        pnl_dollars = (ex - entry) * 100.0 * max(1, int(contracts))
        c.execute("UPDATE option_alerts SET status='closed', exit_ts=?, exit_premium=?, "
                  "exit_reason=?, pnl_pct=?, pnl_dollars=? WHERE id=?",
                  (exit_ts, ex, exit_reason, pnl_pct, pnl_dollars, rid))
        return True


def open_alerts(store, limit: int = 500) -> list:
    """Alerts still awaiting an outcome — the work list for the external filler."""
    with store._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts WHERE status='open' "
                        "ORDER BY alert_ts DESC LIMIT ?", (limit,))
        keys = [d[0] for d in cur.description]
        return [dict(zip(keys, r)) for r in cur.fetchall()]


def _stats(rows) -> dict:
    """Expectancy statistics from closed trades. Hit rate ALONE is not reported anywhere."""
    pnl = [_f(r.get("pnl_pct")) for r in rows]
    pnl = [p for p in pnl if p is not None]
    n = len(pnl)
    if not n:
        return {"n_closed": 0, "hit_rate": None, "avg_win_pct": None, "avg_loss_pct": None,
                "profit_factor": None, "expectancy_pct": None, "cum_pnl_dollars": 0.0,
                "enough_to_tune": False, "min_required": MIN_CLOSED_PER_BUCKET}
    wins = [p for p in pnl if p > 0]
    losses = [p for p in pnl if p <= 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    dollars = sum(_f(r.get("pnl_dollars")) or 0.0 for r in rows)
    return {
        "n_closed": n,
        "hit_rate": len(wins) / n,
        "avg_win_pct": (gross_win / len(wins)) if wins else None,
        "avg_loss_pct": (sum(losses) / len(losses)) if losses else None,
        # Profit factor is None (not inf) with no losses — an undefined ratio should read as
        # "not enough evidence", never as a spectacular score.
        "profit_factor": (gross_win / gross_loss) if gross_loss > 0 else None,
        "expectancy_pct": sum(pnl) / n,
        "cum_pnl_dollars": dollars,
        "enough_to_tune": n >= MIN_CLOSED_PER_BUCKET,
        "min_required": MIN_CLOSED_PER_BUCKET,
    }


def _bucket_of(row, dim) -> Optional[str]:
    if dim == "horizon":
        return row.get("horizon") or None
    if dim == "flow_read":
        return row.get("flow_read") or None
    if dim == "opt_right":
        return row.get("opt_right") or None
    if dim == "iv_rank":
        v = _f(row.get("iv_rank"))
        if v is None:
            return None
        return "low (<30)" if v < 30 else ("mid (30-70)" if v < 70 else "high (>=70)")
    if dim == "score":
        v = _f(row.get("score"))
        if v is None:
            return None
        return "80-90" if v < 90 else ("90-95" if v < 95 else ">=95")
    return None


BUCKET_DIMS = ("horizon", "iv_rank", "score", "flow_read", "opt_right")

# AUDIT MA37. Sentinel for "every era at once". `None` already means "the current epoch" in
# `scream_log.records`, and two modules disagreeing about what `None` means is exactly the
# two-conventions defect this repair exists to remove — so the blended view gets its own name.
# DECLARED DEVIATION from PREREG section 3, which spelled this `epoch=None`: the substance it
# asked for (the blend stays computable on demand) is unchanged; only the spelling is, and it
# is changed toward the convention already shipped rather than away from it.
EPOCH_ALL = "__all__"


def epoch_filter(store, epoch=None):
    """`(sql_fragment, args, resolved_epoch)` for an `option_alerts` query. AUDIT MA37.

    `epoch=None` -> the store's CURRENT era, the same default `scream_log.records` uses.
    `epoch=EPOCH_ALL` -> no filter, i.e. the blended figure, explicitly asked for.
    """
    from . import scream_log as _SL
    _SL.ensure_schema(store)
    if epoch == EPOCH_ALL:
        return "", [], EPOCH_ALL
    ep = epoch or _SL.current_epoch(store)
    if ep == _SL.EPOCH_ORIGINAL:
        # Rows written before the column existed carry NULL, and a NULL IS the original record.
        return " AND COALESCE(record_epoch, ?) = ?", [_SL.EPOCH_ORIGINAL, ep], ep
    return " AND record_epoch = ?", [ep], ep


def epoch_census(store) -> dict:
    """Row count per era. Ships beside every filtered figure so the ARCHIVE stays VISIBLE.

    `scream_log`'s first principle is that a reset is an archive and never a delete; filtering
    an era out of a statistic without saying it exists would honour the letter of that and not
    the point.
    """
    from . import scream_log as _SL
    _SL.ensure_schema(store)
    try:
        with store._conn() as c:
            rows = c.execute("SELECT COALESCE(record_epoch, ?), COUNT(*) FROM option_alerts "
                             "GROUP BY 1", (_SL.EPOCH_ORIGINAL,)).fetchall()
        return {str(k): int(v) for k, v in rows}
    except Exception:                                                    # noqa: BLE001
        return {}


def scorecard(store, dims=BUCKET_DIMS, epoch=None) -> dict:
    """Overall + per-fingerprint expectancy. The thing the Signals tab shows.

    Every bucket carries `enough_to_tune`, so a promising-looking subgroup with six trades is
    visibly NOT actionable rather than quietly treated as a finding.

    AUDIT MA37 — SCOPED TO ONE ERA, defaulting to the current one. This used to be a bare
    `SELECT ... WHERE status='closed'`, so after the 2026-08-13 reset it blended a record the
    project had FORMALLY RETIRED ("predates the corrected alert stack (B1 price basis, C-series
    fixes)") into the expectancy on `/api/options-scorecard`, in `hero.py`, in `unified.py` and
    in `tuning_candidates` — a tuning loop learning from rows the project retired. `record_epoch`
    was stamped on every row and read as a filter by `scream_log` alone. Pass `EPOCH_ALL` for the
    blend; `epochs` reports every era's row count either way, so nothing is hidden by the default.
    """
    clause, args, ep = epoch_filter(store, epoch)
    with store._conn() as c:
        cur = c.execute("SELECT * FROM option_alerts WHERE status='closed'" + clause, args)
        keys = [d[0] for d in cur.description]
        closed = [dict(zip(keys, r)) for r in cur.fetchall()]
        n_open = c.execute("SELECT COUNT(*) FROM option_alerts WHERE status='open'" + clause,
                           args).fetchone()[0]
    out = {"overall": _stats(closed), "n_open": int(n_open), "buckets": {},
           "record_epoch": ep, "epochs": epoch_census(store),
           "min_closed_per_bucket": MIN_CLOSED_PER_BUCKET}
    for dim in dims:
        groups = {}
        for r in closed:
            b = _bucket_of(r, dim)
            if b is not None:
                groups.setdefault(b, []).append(r)
        if groups:
            out["buckets"][dim] = {b: _stats(rs) for b, rs in sorted(groups.items())}
    return out


def tuning_candidates(store, dims=BUCKET_DIMS, min_expectancy_gap: float = 0.10,
                      epoch=None) -> dict:
    """Which fingerprints separate winners from losers — ONLY where evidence is sufficient.

    Returns suggestions, never applies them. Every candidate has cleared MIN_CLOSED_PER_BUCKET
    on BOTH sides of the comparison, so a suggestion can never rest on a handful of trades.
    `min_expectancy_gap` keeps a trivially small difference from being dressed up as a finding.

    AUDIT MA37 — this is the consumer that matters most. It inherits `scorecard`'s era scope,
    so it can no longer propose favouring a fingerprint on the strength of a record the project
    retired. The era it learned from is reported in `record_epoch` rather than left implicit.
    """
    sc = scorecard(store, dims=dims, epoch=epoch)
    out = {"ready": False, "min_closed_per_bucket": MIN_CLOSED_PER_BUCKET,
           "record_epoch": sc.get("record_epoch"), "epochs": sc.get("epochs"),
           "min_expectancy_gap": min_expectancy_gap, "suggestions": [], "blocked": []}
    for dim, buckets in (sc.get("buckets") or {}).items():
        usable = {b: s for b, s in buckets.items() if s["enough_to_tune"]}
        thin = {b: s["n_closed"] for b, s in buckets.items() if not s["enough_to_tune"]}
        for b, n in thin.items():
            out["blocked"].append({"dim": dim, "bucket": b, "n_closed": n,
                                   "needs": MIN_CLOSED_PER_BUCKET})
        if len(usable) < 2:
            continue
        best = max(usable.items(), key=lambda kv: kv[1]["expectancy_pct"])
        worst = min(usable.items(), key=lambda kv: kv[1]["expectancy_pct"])
        gap = best[1]["expectancy_pct"] - worst[1]["expectancy_pct"]
        if gap >= min_expectancy_gap:
            out["ready"] = True
            out["suggestions"].append({
                "dim": dim, "favour": best[0], "avoid": worst[0],
                "expectancy_favour": best[1]["expectancy_pct"],
                "expectancy_avoid": worst[1]["expectancy_pct"],
                "gap": gap, "n_favour": best[1]["n_closed"], "n_avoid": worst[1]["n_closed"],
                "note": (f"{dim}={best[0]} has expectancy {best[1]['expectancy_pct']:+.1%} vs "
                         f"{worst[0]} at {worst[1]['expectancy_pct']:+.1%} "
                         f"({best[1]['n_closed']} vs {worst[1]['n_closed']} closed trades)")})
    return out
