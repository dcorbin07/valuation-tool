"""The path study — stage 2, the pre-registered arms (options bot, 2026-08-10).

    python -m scripts.path_arms --run

Arms are fixed in `PREREG_path_study.md`, committed BEFORE stage 1's tables existed, so they
cannot have been chosen to suit them. Every arm was diffed against O1's tested set
(`shipped, tp50, tp75, tp150, tp200, tp_none, sl30, sl70, sl_none, time25, time75, time100,
dte21, dte14, dte7, trail25, trail35, trail50, ratchet35, run_winners, tp100_only`); nothing
O1 rejected re-runs here.

THE CAVEAT, in the module that produces the numbers rather than only in the write-up: the
options ENTRY signal is dead (R2). No arm here can be a tradeable-edge claim. The most an exit
rule can do on a dead entry is lose less of what the underlying was going to do anyway — and
O23 measured that half of any exit's P&L difference IS the underlying.

CONSTRUCTION. `apply_arm` mirrors `options_exitlab.apply_policy` line for line and adds the
path-conditional state the pre-registered families need. The `shipped` arm must reproduce the
banked book exactly; `--verify` asserts it on the real trade log rather than on a fixture.
"""
import argparse
import datetime as dt
import json
import math
import os
import pickle
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_fill as F            # noqa: E402
from valuation.edge import options_freeze as FZ         # noqa: E402
from valuation.edge import options_greeks as G          # noqa: E402
from scripts.path_study import (DATA, SIGNAL_BOOK, SIGNAL_FREEZE, CONTROL_BOOKS,   # noqa: E402
                                CONTROL_FREEZE, OUT_DIR, book_rows, _row_key, _log)

AGGRESSION = 1.0
RISK_FREE = 0.04            # flat; the arms use delta/IV as a STATE FLAG, not for pricing

# ----------------------------------------------------------------------------------------- #
# The arms. Exactly the pre-registered set, no more and no fewer.
# ----------------------------------------------------------------------------------------- #
SHIPPED = {"tp": 1.0, "sl": -0.5, "time_frac": 0.5}

ARMS = {
    "shipped":           dict(SHIPPED),
    # A — ratchets
    "be50":              dict(SHIPPED, be_after=0.5),
    "trail50_after100":  dict(SHIPPED, tp=None, trail=0.5, trail_after=1.0),
    "step50":            dict(SHIPPED, step=0.5),
    # B — time-conditioned
    "sl_by_dte":         dict(SHIPPED, sl=None, sl_by_dte=((21, -0.40), (0, -0.60))),
    "time_cond25":       dict(SHIPPED, time_frac=0.5, time_hold_above=0.25),
    # C — state-based
    "extrinsic20":       dict(SHIPPED, extrinsic_lt=0.20),
    "delta85":           dict(SHIPPED, abs_delta_gt=0.85),
    "ivcrush30":         dict(SHIPPED, iv_drop_gt=0.30),
    # D — underlying-triggered
    "stock_stop":        dict(SHIPPED, stock_stop=-0.08),
    "gap_open":          dict(SHIPPED, gap_abs=0.05),
    # E — partial exits
    "half_at_100":       dict(SHIPPED, tp=None, half_at=1.0, runner_sl=0.0),
    # F — target escalation
    "escalate_fast":     dict(SHIPPED, tp=None, fast_frac=0.25, fast_trail=0.35),
    "clean_runner":      dict(SHIPPED, clean_floor=-0.10, clean_tp=1.5),
}

FAMILY = {"be50": "A", "trail50_after100": "A", "step50": "A",
          "sl_by_dte": "B", "time_cond25": "B",
          "extrinsic20": "C", "delta85": "C", "ivcrush30": "C",
          "stock_stop": "D", "gap_open": "D",
          "half_at_100": "E",
          "escalate_fast": "F", "clean_runner": "F"}


# ----------------------------------------------------------------------------------------- #
_BARS = {}


def load_bars(ticker: str):
    """Cached: `apply_arm` asks for the settle price on every expiry path, and an uncached
    pickle load per trade turned a 30-second scoring pass into minutes."""
    tk = ticker.upper()
    if tk in _BARS:
        return _BARS[tk]
    _BARS[tk] = _load_bars_uncached(tk)
    return _BARS[tk]


def _load_bars_uncached(ticker: str):
    p = os.path.join(DATA, "bulk", "prepared", "bars", "%s.pkl" % ticker.upper())
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            b = pickle.load(f)
    except Exception:                                                    # noqa: BLE001
        return None
    px = b.get("raw_close") or b.get("close")
    if not px:
        return None
    return dict(zip(b["date"], px))


def entry_quote(r) -> F.Quote:
    """The banked entry bid/ask, reconstructed exactly from what the book stores.

    The book keeps the FILL and the spread, not the two sides. At aggression 1.0 a buy fills at
    the ask, so `ask = entry_premium`; and with `spread_pct = (ask - bid) / mid`,

        bid = ask * (2 - spread_pct) / (2 + spread_pct)

    which is algebra, not an approximation. CHECKED, not assumed: against the 1,099 trades that
    also appear in `data/options_exitlab/paths.pkl` (which stores the true `entry_bid`), the
    maximum absolute error is 0.000000000 and the mean is 2.8e-16 — i.e. floating point. That
    28.3% overlap is useless as a book but is exactly the right control for this one step.

    `oi` and `volume` are NOT reconstructed — they are read from the alert-date chain slice in
    the freeze, because `round_trip` applies a liquidity screen to the entry quote and a
    fabricated pair would decide which trades are scoreable.
    """
    ask = float(r["entry_premium"])
    s = float(r.get("entry_spread_pct") or 0.0)
    bid = ask * (2.0 - s) / (2.0 + s)
    return F.Quote(bid=bid, ask=ask, oi=r.get("_entry_oi"), volume=r.get("_entry_volume"))


def build_rich_paths(rows: list, freeze_path: str, label: str, want_greeks: bool = True) -> dict:
    """Per trade: an ordered list of day-states carrying everything the arms read.

    Richer than `path_study.build_paths` on purpose — that one produced stage 1's banked tables
    and is left untouched so those numbers cannot move under a stage 2 edit.
    """
    df = FZ.load_frozen(freeze_path)
    _log("[%s] freeze rows %d" % (label, len(df)))
    wanted = {}
    for i, r in enumerate(rows):
        wanted.setdefault(_row_key(r), []).append(i)
    k = (df["symbol"].astype(str) + "|" + df["expiration"].astype(str) + "|"
         + df["strike"].astype(float).round(3).map(lambda v: "%.3f" % v) + "|"
         + df["right"].astype(str).str[0].str.upper())
    df = df.assign(_k=k)
    df = df[df["_k"].isin(wanted)].sort_values(["_k", "date"])
    _log("[%s] rows for banked contracts %d" % (label, len(df)))
    by_key = {}
    for kk, sub in df.groupby("_k", sort=False, observed=True):
        by_key[kk] = list(zip(sub["date"].astype(str).tolist(), sub["bid"].tolist(),
                              sub["ask"].tolist(), sub["open_interest"].tolist(),
                              sub["volume"].tolist()))
    del df

    bars_cache, out = {}, {}
    for kk, idxs in wanted.items():
        quotes = by_key.get(kk)
        if not quotes:
            continue
        for i in idxs:
            r = rows[i]
            fill = float(r["entry_premium"] or 0)
            if fill <= 0:
                continue
            tk = r["ticker"].upper()
            if tk not in bars_cache:
                bars_cache[tk] = load_bars(tk)
            bars = bars_cache[tk]
            entry, expiry = r["alert_ts"], r["expiry"]
            K = float(r["strike"])
            is_put = str(r["opt_right"])[0].upper() == "P"
            exp_d = dt.date.fromisoformat(expiry)
            days, prev_iv, prev_S = [], None, None
            for ds, bid, ask, oi, vol in quotes:
                if ds == entry:            # the alert-date slice carries the entry liquidity
                    r["_entry_oi"], r["_entry_volume"] = oi, vol
                if ds <= entry or ds > expiry:
                    continue
                q = F.Quote(bid=bid, ask=ask)
                if F.exit_reject_reason(q) is not None:
                    continue
                mark = F.fill_price(q, "sell", AGGRESSION)
                if mark is None:
                    continue
                S = bars.get(ds) if bars else None
                intrinsic = None if S is None else max(0.0, (K - S) if is_put else (S - K))
                mid = None
                if bid is not None and ask is not None:
                    mid = (float(bid) + float(ask)) / 2.0
                iv = delta = None
                if want_greeks and S and mid and mid > 0:
                    T = max((exp_d - dt.date.fromisoformat(ds)).days, 0) / 365.0
                    if T > 0:
                        try:
                            got = G.implied_vol(mid, S, K, T, RISK_FREE, is_put)
                            iv = got[0] if isinstance(got, tuple) else got
                            if iv and iv > 0:
                                delta = G.greeks(S, K, T, RISK_FREE, iv, is_put).get("delta")
                        except Exception:                                # noqa: BLE001
                            iv = delta = None
                gap = None
                if S is not None and prev_S:
                    gap = S / prev_S - 1.0
                days.append({
                    "d": ds, "bid": bid, "ask": ask, "mark": mark, "ret": mark / fill - 1.0,
                    "S": S, "extr_frac": (None if (S is None or mark <= 0)
                                          else max(0.0, mark - intrinsic) / mark),
                    "iv": iv, "delta": delta, "gap": gap,
                    "iv_drop": (None if (iv is None or not prev_iv) else 1.0 - iv / prev_iv),
                })
                if iv:
                    prev_iv = iv
                if S is not None:
                    prev_S = S
            if days:
                out[i] = days
    _log("[%s] rich paths %d / %d" % (label, len(out), len(rows)))
    return out


# ----------------------------------------------------------------------------------------- #
def apply_arm(r, days, arm: dict) -> dict:
    """One arm against one path. Mirrors `options_exitlab.apply_policy` and extends it.

    Returns the realised return net of the project's own commission via `options_fill.round_trip`,
    so an arm is scored by the same money function every other options result in this project
    uses. `half_at` books a 50/50 blend of two round trips rather than a re-implementation.
    """
    entry = dt.date.fromisoformat(r["alert_ts"])
    expiry = dt.date.fromisoformat(r["expiry"])
    dte0 = max((expiry - entry).days, 1)
    right, K = r["opt_right"], float(r["strike"])
    entry_q = entry_quote(r)
    fill = float(r["entry_premium"])

    tp, sl = arm.get("tp"), arm.get("sl")
    time_frac = arm.get("time_frac")
    trail, trail_after = arm.get("trail"), arm.get("trail_after")
    be_after, step = arm.get("be_after"), arm.get("step")
    sl_by_dte = arm.get("sl_by_dte")
    hold_above = arm.get("time_hold_above")
    extr_lt, dlt_gt, ivd_gt = (arm.get("extrinsic_lt"), arm.get("abs_delta_gt"),
                               arm.get("iv_drop_gt"))
    stock_stop, gap_abs = arm.get("stock_stop"), arm.get("gap_abs")
    half_at, runner_sl = arm.get("half_at"), arm.get("runner_sl")
    fast_frac, fast_trail = arm.get("fast_frac"), arm.get("fast_trail")
    clean_floor, clean_tp = arm.get("clean_floor"), arm.get("clean_tp")

    tstop = entry + dt.timedelta(days=int(round(dte0 * time_frac))) if time_frac else None
    half_day = entry + dt.timedelta(days=int(round(dte0 * 0.5)))
    S0 = None
    peak = None
    armed = trail is not None and trail_after is None
    floor_ret = None                       # a ratcheted / breakeven stop level
    half_done = None                       # (exit ret of the first half)
    clean_ok = True
    fast_armed = False
    last_q = None

    for st in days:
        d = dt.date.fromisoformat(st["d"])
        ret, mark = st["ret"], st["mark"]
        q = F.Quote(bid=st["bid"], ask=st["ask"])
        last_q = q
        if S0 is None and st["S"] is not None:
            S0 = st["S"]
        peak = ret if peak is None else max(peak, ret)

        if clean_floor is not None and d <= half_day and ret < clean_floor:
            clean_ok = False
        eff_tp = tp
        if clean_tp is not None:
            eff_tp = clean_tp if clean_ok else tp
        if fast_frac is not None:
            if not fast_armed and ret >= 1.0:
                if (d - entry).days <= dte0 * fast_frac:
                    fast_armed = True            # runner: trail instead of closing
                else:
                    eff_tp = 1.0
        if be_after is not None and peak is not None and peak >= be_after:
            floor_ret = max(floor_ret if floor_ret is not None else -9, 0.0)
        if step is not None and peak is not None and peak >= 0.5:
            steps = math.floor(peak / 0.5)
            floor_ret = max(floor_ret if floor_ret is not None else -9, (steps - 1) * 0.5)
        if trail is not None and not armed and trail_after is not None and ret >= trail_after:
            armed = True

        eff_sl = sl
        if sl_by_dte:
            left = (expiry - d).days
            for lim, lvl in sl_by_dte:
                if left > lim:
                    eff_sl = lvl
                    break
            else:
                eff_sl = sl_by_dte[-1][1]

        hit_target = eff_tp is not None and ret >= eff_tp
        hit_stop = eff_sl is not None and ret <= eff_sl
        hit_floor = floor_ret is not None and ret <= floor_ret and peak > floor_ret
        eff_trail = fast_trail if fast_armed else trail
        hit_trail = bool(eff_trail is not None and (armed or fast_armed) and peak is not None
                         and ret <= (1 + peak) * (1 - eff_trail) - 1)
        hit_time = bool(tstop is not None and d >= tstop
                        and (hold_above is None or ret < hold_above))
        hit_extr = bool(extr_lt is not None and st["extr_frac"] is not None
                        and st["extr_frac"] < extr_lt)
        hit_delta = bool(dlt_gt is not None and st["delta"] is not None
                         and abs(st["delta"]) > dlt_gt)
        hit_ivc = bool(ivd_gt is not None and st["iv_drop"] is not None
                       and st["iv_drop"] > ivd_gt)
        hit_stk = bool(stock_stop is not None and S0 and st["S"] is not None
                       and (st["S"] / S0 - 1.0) <= stock_stop)
        hit_gap = bool(gap_abs is not None and st["gap"] is not None
                       and abs(st["gap"]) >= gap_abs)

        if half_at is not None and half_done is None and ret >= half_at:
            t = F.round_trip(entry_q, q, right=right, strike=K, aggression=AGGRESSION)
            if t.get("ok"):
                half_done = t.get("return_pct")
                floor_ret = max(floor_ret if floor_ret is not None else -9, runner_sl or 0.0)
                continue

        if (hit_target or hit_stop or hit_floor or hit_trail or hit_time or hit_extr
                or hit_delta or hit_ivc or hit_stk or hit_gap):
            t = F.round_trip(entry_q, q, right=right, strike=K, aggression=AGGRESSION)
            if not t.get("ok"):
                continue
            pnl = t.get("return_pct")
            if half_done is not None:
                pnl = 0.5 * half_done + 0.5 * pnl
            reason = ("target" if hit_target else "stop" if hit_stop else
                      "ratchet" if hit_floor else "trail" if hit_trail else
                      "time_stop" if hit_time else "extrinsic" if hit_extr else
                      "delta" if hit_delta else "iv_crush" if hit_ivc else
                      "stock" if hit_stk else "gap")
            return {"ok": True, "pnl_pct": pnl, "exit_reason": reason,
                    "held_days": (d - entry).days, "exit_date": st["d"]}

    # Held past the last usable quote: settle at intrinsic, never at a stale mark (O1's finding).
    und = None
    bars = load_bars(r["ticker"])
    if bars:
        for ds in sorted(bars):
            if ds <= r["expiry"]:          # both ISO strings; `expiry` here is a date object
                und = bars[ds]
    t = F.round_trip(entry_q, None if und is not None else last_q, right=right, strike=K,
                     exit_underlying=und, aggression=AGGRESSION, expired=True,
                     force_intrinsic_at_expiry=und is not None)
    if not t.get("ok"):
        return {"ok": False}
    pnl = t.get("return_pct")
    if half_done is not None:
        pnl = 0.5 * half_done + 0.5 * pnl
    return {"ok": True, "pnl_pct": pnl, "exit_reason": "expiry",
            "held_days": (expiry - entry).days, "exit_date": r["expiry"],
            "stale_mark_used": und is None and last_q is not None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="shipped arm must match the book")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--no-greeks", action="store_true")
    ap.add_argument("--control", action="store_true",
                    help="score the five random-entry seeds instead of the signal book")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    if a.control:
        rows, seed_of = [], {}
        for s, bp in enumerate(CONTROL_BOOKS):
            with open(bp, "rb") as f:
                cr = pickle.load(f)
            cr = cr["rows"] if isinstance(cr, dict) else cr
            for r in cr:
                seed_of[len(rows)] = s
                rows.append(r)
        _log("control rows %d across %d seeds" % (len(rows), len(CONTROL_BOOKS)))
        paths = build_rich_paths(rows, CONTROL_FREEZE, "control", want_greeks=not a.no_greeks)
    else:
        seed_of = {}
        rows = book_rows(SIGNAL_BOOK)
        paths = build_rich_paths(rows, SIGNAL_FREEZE, "signal", want_greeks=not a.no_greeks)

    if a.verify:
        same = tot = 0
        for i, days in sorted(paths.items()):
            r = rows[i]
            got = apply_arm(r, days, ARMS["shipped"])
            if not got.get("ok"):
                continue
            tot += 1
            if got["exit_reason"] == r["exit_reason"]:
                same += 1
        print("VERIFY shipped arm vs banked book: %d/%d exit reasons match (%.3f%%)"
              % (same, tot, 100.0 * same / max(tot, 1)))
        return

    if not a.run:
        ap.error("pass --run or --verify")

    res = {"arms": {}, "n_paths": len(paths)}
    for name, arm in ARMS.items():
        out = []
        for i, days in sorted(paths.items()):
            g = apply_arm(rows[i], days, arm)
            if g.get("ok") and g.get("pnl_pct") is not None:
                out.append({"i": i, "pnl_pct": g["pnl_pct"], "reason": g["exit_reason"],
                            "held": g["held_days"], "d": rows[i]["alert_ts"],
                            "tk": rows[i]["ticker"],
                            **({"seed": seed_of[i]} if seed_of else {})})
        res["arms"][name] = out
        m = sum(x["pnl_pct"] for x in out) / max(len(out), 1)
        _log("  %-18s n=%d  mean=%+.4f" % (name, len(out), m))
    os.makedirs(OUT_DIR, exist_ok=True)
    p = a.out or os.path.join(OUT_DIR, "PATHSTUDY_ARMS_SIGNAL.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(res, f, default=str)
    _log("wrote " + p)


if __name__ == "__main__":
    main()
