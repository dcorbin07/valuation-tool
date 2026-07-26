"""
Paper account with sell logic for the Track Record.

A hot stock won't stay hot forever, so we trade it like a rule-based position:

  ENTRY   buy when a name enters the top-N hot list (at that day's close).
  HOLD    keep it at least `min_hold_days` so we don't churn on noise.
  SELL    after the minimum hold, exit when it:
            • leaves the top-N ("cooled off"),         ← the main rule
            • reaches its DCF fair value (take profit), ← if the pick has one
            • or hits `max_hold_days` (time stop).
          The exit price is that day's close, recorded on the position.

Entry/exit prices come straight from the daily snapshots (which carry a price for
every scored name), so this is self-contained — no extra price fetching.
"""
from __future__ import annotations

import datetime as _dt


def _days(a: str, b: str) -> int:
    try:
        return (_dt.date.fromisoformat(b[:10]) - _dt.date.fromisoformat(a[:10])).days
    except Exception:
        return 0


def update_positions(store, source, scan_date, ranked_rows, top_n=10,
                     min_hold_days=30, max_hold_days=180, target_key="fair_value") -> dict:
    rows = [r for r in ranked_rows if r.get("ticker")]
    price_map = {r["ticker"]: r.get("price") for r in rows if r.get("price")}
    top = [r["ticker"] for r in sorted(rows, key=lambda r: r.get("rank") or 10 ** 9)[:top_n]]
    fair_map = {r["ticker"]: r.get(target_key) for r in rows} if target_key else {}

    open_pos = store.open_positions(source)
    held = {p["ticker"] for p in open_pos}

    # ENTRIES — new top-N names we don't already hold.
    entered = []
    for t in top:
        if t not in held and price_map.get(t):
            store.open_position(source, t, scan_date, price_map[t])
            entered.append(t)

    # EXITS — apply the sell rules to each open position we can price today.
    closed = []
    for p in open_pos:
        price = price_map.get(p["ticker"])
        if price is None:
            continue                                  # can't mark today — keep holding
        hold = _days(p["entry_date"], scan_date)
        reason = None
        if hold >= max_hold_days:
            reason = "time stop"
        elif hold >= min_hold_days and p["ticker"] not in top:
            reason = f"cooled off (left top {top_n})"
        elif hold >= min_hold_days and fair_map.get(p["ticker"]) and price >= fair_map[p["ticker"]]:
            reason = "hit fair value"
        if reason:
            store.close_position(source, p["ticker"], p["entry_date"], scan_date, price, reason)
            closed.append(p["ticker"])
    return {"entered": entered, "closed": closed, "open": len(store.open_positions(source))}


def paper_summary(store, source, latest_price_map=None, recent=25) -> dict:
    latest_price_map = latest_price_map or {}
    allp = store.all_positions(source)
    closed = [p for p in allp if p.get("exit_date")]
    openp = [p for p in allp if not p.get("exit_date")]

    def ret(p, mark=None):
        e = p.get("entry_price")
        x = p.get("exit_price") if p.get("exit_date") else mark
        return (x / e - 1) if (e and x and e > 0) else None

    def avg(a):
        return (sum(a) / len(a)) if a else None

    closed_rets = [r for r in (ret(p) for p in closed) if r is not None]
    open_rets = [r for r in (ret(p, latest_price_map.get(p["ticker"])) for p in openp) if r is not None]
    all_rets = closed_rets + open_rets

    by_reason = {}
    for p in closed:
        k = p.get("exit_reason") or "?"
        by_reason[k] = by_reason.get(k, 0) + 1

    summary = {
        "n_total": len(allp), "n_closed": len(closed), "n_open": len(openp),
        "avg_return": avg(all_rets),                    # per-pick, closed realized + open marked to today
        "avg_return_closed": avg(closed_rets),
        "win_rate": avg([1.0 if r > 0 else 0.0 for r in closed_rets]) if closed_rets else None,
        "avg_hold_days": avg([_days(p["entry_date"], p["exit_date"]) for p in closed]) if closed else None,
        "by_reason": by_reason,
    }

    today = _dt.date.today().isoformat()

    def row(p, mark=None):
        return {"ticker": p["ticker"], "entry_date": p["entry_date"], "entry_price": p.get("entry_price"),
                "exit_date": p.get("exit_date"), "exit_price": p.get("exit_price"),
                "reason": p.get("exit_reason") or "open", "ret": ret(p, mark),
                "hold_days": _days(p["entry_date"], p.get("exit_date") or today)}

    positions = [row(p, latest_price_map.get(p["ticker"])) for p in openp] + [row(p) for p in closed[:recent]]
    return {"summary": summary, "positions": positions}
