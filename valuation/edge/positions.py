"""
Paper account with sell logic for the Track Record.

A hot stock won't stay hot forever — but "another name got hotter" is NOT a reason
to sell one that's still strong. So we trade it like a rule-based position:

  ENTRY   buy when a name enters the top-N hot list (at that day's close).
  HOLD    keep it at least `min_hold_days` so we don't churn on noise, and keep
          holding as long as it stays hot — even if it slips out of the top-N.
  SELL    after the minimum hold, exit only when the name is genuinely no longer
          hot (its hot score drops below `exit_score`) or it reaches its DCF fair
          value. Optional `max_hold_days` time stop (0 = never, so gems can
          compound for years). The exit price is that day's close.

  SIZE    suggested position size is score-weighted (hotter = bigger), capped, so
          you're not equal-weighting a 90 with a 60.

Entry/exit prices + scores come straight from the daily snapshots, so this is
self-contained — no extra price fetching.
"""
from __future__ import annotations

import datetime as _dt


def _days(a: str, b: str) -> int:
    try:
        return (_dt.date.fromisoformat(b[:10]) - _dt.date.fromisoformat(a[:10])).days
    except Exception:
        return 0


def update_positions(store, source, scan_date, ranked_rows, top_n=10, min_hold_days=30,
                     max_hold_days=0, exit_score=55, target_key="fair_value",
                     coverage_gap_days=21, exit_band=0, price_fn=None) -> dict:
    rows = [r for r in ranked_rows if r.get("ticker")]
    price_map = {r["ticker"]: r.get("price") for r in rows if r.get("price")}
    score_map = {r["ticker"]: r.get("hot_score") for r in rows}
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

    # EXITS — sell only when genuinely no longer hot, at fair value, or a time stop.
    closed = []
    for p in open_pos:
        price = price_map.get(p["ticker"])
        if price is None:
            # Not in today's scan. Keep holding for a grace window, but if it's been
            # gone too long it likely delisted/was acquired — close it at its last
            # known price (reason logged) so a dropped loser can't live forever and
            # quietly inflate the record (survivorship bias).
            #
            # 2026-09-30: "LAST KNOWN PRICE" WAS USUALLY THE ENTRY PRICE. The live scan covers
            # the ~800 most liquid names and its membership churns at the edge, so a name can
            # enter the top 10 and never be scanned again. It was then closed at its entry
            # price, booking a return of exactly minus costs -- 19 of the first 23 closes were
            # "left coverage", several at exit == entry. `price_fn` re-prices a skipped name
            # from the price vendor so the mark (and the eventual close) is a real close. It
            # does NOT count as being seen: the grace clock still runs off the scan.
            if price_fn is not None:
                try:
                    vp = price_fn(p["ticker"])
                except Exception:                                       # noqa: BLE001
                    vp = None
                if vp and vp > 0:
                    store.mark_position(source, p["ticker"], p["entry_date"], float(vp))
                    p["last_price"] = float(vp)
            last_seen = p.get("last_seen_date") or p.get("entry_date")
            if _days(last_seen, scan_date) > coverage_gap_days:
                mark = p.get("last_price") or p.get("entry_price")
                if mark:
                    store.close_position(source, p["ticker"], p["entry_date"], scan_date, mark, "left coverage")
                    closed.append(p["ticker"])
            continue
        store.touch_position(source, p["ticker"], p["entry_date"], scan_date, price)   # still covered
        hold = _days(p["entry_date"], scan_date)
        score = score_map.get(p["ticker"])
        reason = None
        if max_hold_days and hold >= max_hold_days:
            reason = "time stop"
        elif hold >= min_hold_days and score is not None and score < (exit_score - exit_band):
            reason = f"no longer hot (score {score:.0f})"
        elif hold >= min_hold_days and fair_map.get(p["ticker"]) and price >= fair_map[p["ticker"]]:
            reason = "hit fair value"
        if reason:
            store.close_position(source, p["ticker"], p["entry_date"], scan_date, price, reason)
            closed.append(p["ticker"])
    return {"entered": entered, "closed": closed, "open": len(store.open_positions(source))}


def _size_weights(open_rows, score_map, max_weight=0.20, vol_map=None):
    """Suggested sizing: score-weighted AND inverse-volatility scaled (a hot-but-calm
    name gets more than an equally-hot wild one), capped and renormalized."""
    n = len(open_rows)
    if not n:
        return
    vol_map = vol_map or {}

    def raw(t):
        s = max(0.0, (score_map.get(t) or 0.0))
        v = vol_map.get(t)
        return (s / v) if (v and v > 0) else s          # inverse-vol when we have it
    scores = {r["ticker"]: raw(r["ticker"]) for r in open_rows}
    tot = sum(scores.values())
    if tot <= 0:
        for r in open_rows:
            r["weight"] = 1.0 / n
        return
    capped = {t: min(s / tot, max_weight) for t, s in scores.items()}
    s2 = sum(capped.values()) or 1.0
    for r in open_rows:
        r["weight"] = capped[r["ticker"]] / s2


def paper_summary(store, source, latest_price_map=None, latest_score_map=None,
                  max_weight=0.20, recent=25, cost_bps=0.0, vol_map=None) -> dict:
    latest_price_map = latest_price_map or {}
    latest_score_map = latest_score_map or {}
    allp = store.all_positions(source)
    closed = [p for p in allp if p.get("exit_date")]
    openp = [p for p in allp if not p.get("exit_date")]

    rt_cost = 2.0 * (cost_bps or 0.0) / 1e4          # round-trip transaction cost

    def ret(p, mark=None):
        e = p.get("entry_price")
        x = p.get("exit_price") if p.get("exit_date") else mark
        return (x / e - 1 - rt_cost) if (e and x and e > 0) else None

    def avg(a):
        return (sum(a) / len(a)) if a else None

    # AN EXIT THAT WAS NEVER RE-PRICED IS UNKNOWN, NOT ZERO. A "left coverage" close whose exit
    # price equals its entry price means the name was never observed again after the day it
    # was bought, so its return is not measured -- booking it at minus costs pulled the realised
    # average toward zero. Counted and shown, never averaged in.
    def _unpriced_exit(p):
        return ((p.get("exit_reason") or "").startswith("left coverage")
                and p.get("exit_price") is not None and p.get("entry_price") is not None
                and float(p["exit_price"]) == float(p["entry_price"]))

    unpriced_exits = [p for p in closed if _unpriced_exit(p)]
    priced_closed = [p for p in closed if not _unpriced_exit(p)]

    # AN OPEN NAME THE LATEST SCAN SKIPPED is marked at its last real price (a scan price, or a
    # vendor close written by `update_positions(price_fn=...)`) rather than silently dropped
    # from the average -- dropping it averaged only the names that happened to be scanned today.
    # A last price equal to the entry price is no mark at all, so that name stays unmarked.
    def _mark(p):
        m = latest_price_map.get(p["ticker"])
        if m:
            return m, "scan"
        lp = p.get("last_price")
        if lp and p.get("entry_price") and float(lp) != float(p["entry_price"]):
            return lp, "last price"
        return None, None

    closed_rets = [r for r in (ret(p) for p in priced_closed) if r is not None]
    open_rets = [r for r in (ret(p, _mark(p)[0]) for p in openp) if r is not None]

    by_reason = {}
    for p in closed:
        k = p.get("exit_reason") or "?"
        by_reason[k] = by_reason.get(k, 0) + 1

    summary = {
        "n_total": len(allp), "n_closed": len(closed), "n_open": len(openp),
        "avg_return": avg(closed_rets + open_rets),      # closed realized + open marked to today
        "avg_return_closed": avg(closed_rets),
        "win_rate": avg([1.0 if r > 0 else 0.0 for r in closed_rets]) if closed_rets else None,
        "avg_hold_days": avg([_days(p["entry_date"], p["exit_date"]) for p in closed]) if closed else None,
        "by_reason": by_reason,
        "n_unpriced_exits": len(unpriced_exits),
        "n_open_marked": len(open_rets),
    }

    today = _dt.date.today().isoformat()

    # Open positions = the actively-held / watched book, with suggested sizing.
    watching = []
    for p in openp:
        watching.append({"ticker": p["ticker"], "entry_date": p["entry_date"],
                         "entry_price": p.get("entry_price"),
                         "score": latest_score_map.get(p["ticker"]),
                         "ret": ret(p, _mark(p)[0]),
                         "marked_from": _mark(p)[1],
                         "hold_days": _days(p["entry_date"], today)})
    _size_weights(watching, latest_score_map, max_weight, vol_map)
    watching.sort(key=lambda r: (r.get("weight") or 0), reverse=True)

    closed_rows = [{"ticker": p["ticker"], "entry_date": p["entry_date"], "entry_price": p.get("entry_price"),
                    "exit_date": p.get("exit_date"), "exit_price": p.get("exit_price"),
                    "reason": p.get("exit_reason"),
                    "ret": (None if _unpriced_exit(p) else ret(p)),
                    "unpriced": _unpriced_exit(p),
                    "hold_days": _days(p["entry_date"], p.get("exit_date") or today)}
                   for p in closed[:recent]]
    return {"summary": summary, "watching": watching, "closed": closed_rows}
