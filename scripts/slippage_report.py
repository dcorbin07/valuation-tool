#!/usr/bin/env python3
"""
V5 — measured slippage vs modelled costs on the forward paper track.

  python scripts/slippage_report.py                    # offline, reads data/screener.db
  python scripts/slippage_report.py --db PATH          # a different store (e.g. a Render copy)
  python scripts/slippage_report.py --broker           # also read limit prices from the sandbox
  python scripts/slippage_report.py --json OUT.json    # machine-readable alongside the text

Pre-registered in `PREREG_v5_slippage.md` BEFORE this file existed. Every threshold, sign
convention and verdict string below is a literal from that register; changing one here without
changing it there is a defect, and `tests/test_slippage_report.py` pins them.

--------------------------------------------------------------------------------------------
WHY A LIMIT-AT-THE-TOUCH BOOK NEEDS FOUR MEASURES AND NOT ONE.

The obvious statistic — did the fill beat the order's limit price — is worthless here, and the
register says so in advance. `paper_track` submits a LIMIT buy at the ask and a LIMIT sell at the
bid, so a fill can never be worse than its limit. Report that alone and you publish "0 bps of
slippage" forever, which is not a measurement, it is a restatement of the order type.

What a limit-at-the-touch book actually pays is:

  * the HALF-SPREAD it crosses to reach the touch   -> M3, the headline, vs 410.0 bps modelled
  * the trades it never gets filled on at all       -> M4, which M1/M2 structurally cannot see

and what it does NOT pay, though a reader will assume otherwise, is the gap between the ask when
the alert fired and the fill some minutes or days later -> M5, reported and labelled NOT SLIPPAGE.

--------------------------------------------------------------------------------------------
THE ENTRY LEG'S HALF-SPREAD IS NOT MEASURABLE AND THIS SCRIPT SAYS SO RATHER THAN GUESSING.

`paper_option_orders` stores no bid, ask or mid at submit time. The ASK is recoverable, because
`_place_entry` writes `target_premium = round(ask * (1 + target_pct), 4)`; the MID is not
recoverable by any route. A half-spread needs a mid, so M3 covers the EXIT leg only, where audit
B5a's `last_mid` sits beside `last_mark`. The fix is two columns written in `_place_entry`
(`entry_bid`, `entry_ask`); V5 is scoped to new files only, so this is ROUTED in the report's
own output, not made here.

--------------------------------------------------------------------------------------------
SANDBOX FILLS ARE OPTIMISTIC. Printed on every run, in every mode. Tradier's sandbox quotes are
delayed ~15 minutes and its fills are simulated against them, so a measured cost BELOW the model
is the direction the measurement error already points and is weak evidence. A measured cost ABOVE
the model runs against the bias and is correspondingly stronger.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import random
import sqlite3
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- Pre-registered constants. Literals from PREREG_v5_slippage.md sections 2 and 4. --------
MODELLED_ENTRY_HALF_SPREAD_BPS = 410.0     # mean, 3,885/3,885 banked R2-corrected trades
MODELLED_ENTRY_HALF_SPREAD_MEDIAN_BPS = 333.3
MODELLED_COMMISSION_ROUND_TRIP = 1.30      # $0.65/contract/leg, options_fill.COMMISSION_PER_CONTRACT
MODELLED_MEDIAN_ENTRY_PREMIUM = 2.58
MIN_N = 30                                 # filled legs of a kind before ANY aggregate is quoted
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 0
CI_LOW_PCT, CI_HIGH_PCT = 5.0, 95.0        # the 90% interval V5 asks for

# Audit B11's 33.4 bps is basis points of STOCK NOTIONAL on the fundamental panel. The options
# book pays basis points of PREMIUM. Kept here only so the report can say it does not apply.
EQUITY_ONE_WAY_BPS_NOT_APPLICABLE = 33.4

SANDBOX_CAVEAT = ("Tradier sandbox quotes are delayed ~15 minutes and its fills are simulated "
                  "against them, so every fill below is OPTIMISTIC relative to a live account. "
                  "Measured cost BELOW modelled is the direction the bias already points.")

DEFAULT_TARGET_PCT = 1.00                  # options_tracker.DEFAULT_TARGET_PCT
FILLED_STATES = ("open", "closing", "closed")


# ============================== small helpers ===============================================
def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


def week_key(ts) -> Optional[str]:
    """ISO year-week of a timestamp string. The bootstrap's cluster (register section 4).

    Legs are not independent: one alert engine fires several names on a day and a name can
    repeat. Audit R3 found every earlier options interval was optimistically narrow for exactly
    this reason, so the block is the calendar week and everything inside it travels together.
    """
    if not ts:
        return None
    s = str(ts).strip()
    for cut in (19, 10):
        try:
            d = _dt.datetime.fromisoformat(s[:cut]).date()
        except ValueError:
            continue
        y, w, _ = d.isocalendar()
        return "%04d-W%02d" % (y, w)
    return None


def exit_policy_target_pct(features) -> float:
    """The alert's OWN target_pct, else the shipped default. Mirrors `paper_track._exit_policy`.

    Read rather than assumed, because `_place_entry` derived `target_premium` with whatever this
    was, and M2 inverts that arithmetic.
    """
    try:
        d = json.loads(features) if isinstance(features, str) else (features or {})
        v = _f(((d or {}).get("exit_policy") or {}).get("target_pct"))
    except (ValueError, TypeError, AttributeError):
        v = None
    return DEFAULT_TARGET_PCT if v is None else v


def submit_ask_from_target(target_premium, target_pct: float = DEFAULT_TARGET_PCT) -> Optional[float]:
    """Recover the ASK the entry limit was placed at, from the stored target.

    `_place_entry` writes `target_premium = round(ask * (1 + target_pct), 4)`, so this inverts
    exactly, to within that 4-dp rounding. Returns None when the arithmetic is undefined — a
    target_pct of exactly -1.0 would divide by zero, and a missing target means the row is one
    of the audit-B5c casualties that carries no exit levels at all.
    """
    t = _f(target_premium)
    if t is None or t <= 0:
        return None
    denom = 1.0 + float(target_pct)
    if denom <= 0:
        return None
    return t / denom


def half_spread_bps(mid, fill, side: str) -> Optional[float]:
    """Basis points of the mid given up to reach the touch. POSITIVE IS A COST, both sides.

    side='sell' -> (mid - fill) / mid : a seller receives less than the mid
    side='buy'  -> (fill - mid) / mid : a buyer pays more than the mid
    """
    m, p = _f(mid), _f(fill)
    if m is None or p is None or m <= 0:
        return None
    if side == "sell":
        return (m - p) / m * 10000.0
    if side == "buy":
        return (p - m) / m * 10000.0
    raise ValueError("side must be 'buy' or 'sell', got %r" % (side,))


def signed_vs_limit(fill, limit, side: str) -> Optional[float]:
    """M1/M2: fill against the limit, in bps of the limit. POSITIVE IS WORSE THAN THE LIMIT.

    Structurally bounded at <= 0 for a marketable limit, which is why the register forbids it
    from being the headline. Computed anyway: price improvement is real information.
    """
    p, l = _f(fill), _f(limit)
    if p is None or l is None or l <= 0:
        return None
    if side == "buy":
        return (p - l) / l * 10000.0
    if side == "sell":
        return (l - p) / l * 10000.0
    raise ValueError("side must be 'buy' or 'sell', got %r" % (side,))


# ============================== inference ===================================================
def _mean(v):
    return sum(v) / len(v) if v else None


def _pct(sorted_vals, p: float) -> float:
    """Linear-interpolated percentile. `sorted_vals` must already be sorted."""
    if not sorted_vals:
        raise ValueError("empty")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


def clustered_bootstrap_ci(values, blocks, draws: int = BOOTSTRAP_DRAWS,
                           seed: int = BOOTSTRAP_SEED) -> Optional[dict]:
    """Percentile bootstrap of the MEAN, resampling BLOCKS not observations.

    Blocks are resampled with replacement to the same block count; every value inside a drawn
    block travels with it, so a week that fired eight correlated legs contributes as one draw
    rather than eight. Values with no block label form their own singleton blocks — dropping
    them would silently narrow the sample, and lumping them together would invent a cluster.
    """
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    labs = list(blocks)
    if len(labs) != len(vals):
        raise ValueError("values and blocks must be the same length")
    grouped = {}
    for i, (v, b) in enumerate(zip(vals, labs)):
        grouped.setdefault(b if b else ("_unblocked_%d" % i), []).append(v)
    keys = sorted(grouped)
    rng = random.Random(seed)
    means = []
    for _ in range(int(draws)):
        pool = []
        for _ in range(len(keys)):
            pool.extend(grouped[keys[rng.randrange(len(keys))]])
        if pool:
            means.append(sum(pool) / len(pool))
    if not means:
        return None
    means.sort()
    return {"lo": _pct(means, CI_LOW_PCT), "hi": _pct(means, CI_HIGH_PCT),
            "draws": int(draws), "seed": int(seed),
            "n_blocks": len(keys), "n": len(vals)}


def verdict(n: int, ci: Optional[dict], modelled: float = MODELLED_ENTRY_HALF_SPREAD_BPS) -> str:
    """The register's section-4 table, and nothing else. Ambiguity resolves to CONSISTENT."""
    if n < MIN_N or not ci:
        return "INSUFFICIENT"
    if ci["lo"] > modelled:
        return "DIVERGENT-COSTLIER"
    if ci["hi"] < modelled:
        return "DIVERGENT-CHEAPER"
    return "CONSISTENT"


def summarise(values, blocks, label: str,
              modelled: Optional[float] = None) -> dict:
    """One measure's block: n ALWAYS present, aggregates only above MIN_N.

    Below MIN_N this returns n and the raw values and NOTHING derived — no mean, no CI, no
    verdict. That refusal is the point of the register's minimum: an aggregate over nine fills
    reads as a finding to anyone who skims past the n beside it.
    """
    vals = [v for v in values if v is not None]
    n = len(vals)
    out = {"label": label, "n": n, "min_n": MIN_N, "quotable": n >= MIN_N}
    if modelled is not None:
        out["modelled_bps"] = modelled
    if n == 0:
        out["note"] = "no filled legs of this kind"
        out["verdict"] = "INSUFFICIENT"
        return out
    if n < MIN_N:
        out["note"] = "NOT QUOTABLE (n=%d < %d) - raw values only, no mean and no CI" % (n, MIN_N)
        out["values"] = [round(v, 4) for v in vals]
        out["verdict"] = "INSUFFICIENT"
        return out
    kept = [(v, b) for v, b in zip(values, blocks) if v is not None]
    ci = clustered_bootstrap_ci([v for v, _ in kept], [b for _, b in kept])
    s = sorted(vals)
    out.update({"mean": _mean(vals), "median": _pct(s, 50.0),
                "p10": _pct(s, 10.0), "p90": _pct(s, 90.0),
                "ci90": ci})
    if modelled is not None:
        out["verdict"] = verdict(n, ci, modelled)
    return out


# ============================== reading the store ===========================================
def _table_exists(conn, name: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())


def read_store(db_path: str) -> dict:
    """READ-ONLY. Paper option rows joined to their alerts. Never writes, never migrates.

    Opened through a `mode=ro` URI so a bug here cannot touch the book being measured, and so
    pointing this at a live Render copy is safe.
    """
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    conn = sqlite3.connect("file:%s?mode=ro" % db_path.replace("?", "%3f"), uri=True)
    try:
        if not _table_exists(conn, "paper_option_orders"):
            return {"orders": [], "alerts": {}, "schema": "absent",
                    "note": "paper_option_orders does not exist in this store - the paper "
                            "track has never run against it"}
        cur = conn.execute("SELECT * FROM paper_option_orders")
        keys = [d[0] for d in cur.description]
        orders = [dict(zip(keys, r)) for r in cur.fetchall()]
        alerts = {}
        if _table_exists(conn, "option_alerts"):
            cur = conn.execute("SELECT id, entry_premium, features, alert_ts FROM option_alerts")
            for r in cur.fetchall():
                alerts[r[0]] = {"entry_premium": r[1], "features": r[2], "alert_ts": r[3]}
        return {"orders": orders, "alerts": alerts, "schema": "present"}
    finally:
        conn.close()


def read_export(path: str) -> dict:
    """The SAME shape as `read_store`, from `track_export`'s backup payload.

    THIS IS THE ONLY REACHABLE SOURCE OF REAL FILLS AND THE INSTRUMENT WOULD BE ORNAMENTAL
    WITHOUT IT. The paper track runs on Render's persistent disk behind
    `/admin/run-paper-track`; every screener store on a development machine holds zero paper
    rows. What DOES reach the repository is `.github/workflows/track-backup.yml`, which curls
    `/admin/export-track` and commits `data_export/paper_track_history.json` — and
    `track_export.payload` carries `paper_option_orders` verbatim under `paper_orders`.

    So the backup written to protect the record doubles as the read path for measuring it.
    """
    with open(path, encoding="utf-8") as fh:
        pay = json.load(fh)
    # `--from-json` payloads nest the export under "export"; the rendered history file does not.
    pay = pay.get("export") if isinstance(pay.get("export"), dict) else pay
    orders = list(pay.get("paper_orders") or [])
    alerts = {}
    for a in (pay.get("option_alerts") or []):
        if a.get("id") is not None:
            alerts[a["id"]] = {"entry_premium": a.get("entry_premium"),
                               "features": a.get("features"), "alert_ts": a.get("alert_ts")}
    return {"orders": orders, "alerts": alerts,
            "schema": "export(v%s) generated %s" % (pay.get("schema_version"),
                                                    pay.get("generated_at"))}


def exit_level_fidelity(orders, alerts) -> dict:
    """POST-HOC DIAGNOSTIC, NO VERDICT. Are the live exit levels the ones that were backtested?

    NOT in `PREREG_v5_slippage.md`: it was found while reading the first three real fills, and
    it is reported as a bug with numbers rather than dressed up as a registered result.

    `paper_track._place_entry` derives `target_premium` and `stop_premium` from the price the
    order was SUBMITTED at, and `mark_open` later overwrites `entry_premium` with the broker's
    actual fill WITHOUT recomputing either level. Whenever the fill differs from the submit
    price, the position therefore runs a different +target / -stop than the one every backtested
    number assumes — in the book whose entire purpose is to be comparable to that backtest.
    Same family as audit B5c, which fixed the RESUME branch's missing levels; the fresh path
    still anchors them to the pre-fill price.
    """
    rows, off = [], 0
    for o in orders:
        a = alerts.get(o.get("alert_id")) or {}
        tp = exit_policy_target_pct(a.get("features"))
        fill, tgt, stp = _f(o.get("entry_premium")), _f(o.get("target_premium")), _f(o.get("stop_premium"))
        if fill is None or fill <= 0 or tgt is None:
            continue
        realised_t = tgt / fill - 1.0
        realised_s = (stp / fill - 1.0) if stp is not None else None
        drift_t = realised_t - tp
        if abs(drift_t) > 1e-6:
            off += 1
        rows.append({"alert_id": o.get("alert_id"), "ticker": o.get("ticker"),
                     "entry_fill": fill, "intended_target_pct": tp,
                     "realised_target_pct": realised_t, "target_drift_pct": drift_t,
                     "realised_stop_pct": realised_s})
    return {"n_positions": len(rows), "n_off_spec": off, "rows": rows,
            "what": ("exit levels are derived from the SUBMIT price and never recomputed to the "
                     "actual fill, so a position whose fill differs from its limit runs a "
                     "different strategy from the backtested one"),
            "verdict": "NO VERDICT - post-hoc diagnostic, not in the register"}


def sizing_veto_ignored(orders, alerts) -> dict:
    """POST-HOC DIAGNOSTIC, NO VERDICT. Did the paper track buy something the alert refused?

    Also found in the first three fills. The live alert carries its own sizing decision in
    `features.sizing` — including `skip: true` with a reason — and `submit_new_alerts` never
    reads it: contract count comes from `cfg.paper_contracts_per_trade` and `_eligible` tests
    only the contract, the expiry and the alert's age. A name the product's own sizing logic
    declined can therefore end up in the paper book.
    """
    rows = []
    for o in orders:
        a = alerts.get(o.get("alert_id")) or {}
        try:
            feats = json.loads(a.get("features")) if isinstance(a.get("features"), str) else (a.get("features") or {})
        except (ValueError, TypeError):
            continue
        sz = (feats or {}).get("sizing") or {}
        if sz.get("skip"):
            rows.append({"alert_id": o.get("alert_id"), "ticker": o.get("ticker"),
                         "state": o.get("state"), "entry_fill": _f(o.get("entry_premium")),
                         "sizing_contracts": sz.get("contracts"), "reason": sz.get("reason")})
    return {"n_traded_against_a_skip": len(rows), "rows": rows,
            "verdict": "NO VERDICT - post-hoc diagnostic, not in the register"}


def build_legs(orders, alerts) -> dict:
    """Turn rows into the four measures' inputs. Pure: no I/O, so tests can drive it directly."""
    entry_vs_touch, entry_blocks = [], []
    exit_vs_touch, exit_blocks = [], []
    exit_half, exit_half_blocks = [], []
    drift, drift_blocks = [], []
    states = {}
    detail = []

    for o in orders:
        st = str(o.get("state") or "?")
        states[st] = states.get(st, 0) + 1
        a = alerts.get(o.get("alert_id")) or {}
        tp = exit_policy_target_pct(a.get("features"))
        row = {"alert_id": o.get("alert_id"), "ticker": o.get("ticker"), "state": st,
               "target_pct": tp}

        # ---- entry leg
        fill_in = _f(o.get("entry_premium"))
        ask_in = submit_ask_from_target(o.get("target_premium"), tp)
        wk_in = week_key(o.get("entry_ts") or o.get("created_at"))
        if fill_in is not None and ask_in is not None:
            v = signed_vs_limit(fill_in, ask_in, "buy")
            entry_vs_touch.append(v)
            entry_blocks.append(wk_in)
            row["entry_fill"], row["entry_limit_ask"], row["entry_vs_touch_bps"] = fill_in, ask_in, v
        # M5 - alert-time ask vs the fill. NOT slippage; different timestamps.
        ask_alert = _f(a.get("entry_premium"))
        if fill_in is not None and ask_alert is not None and ask_alert > 0:
            d = (fill_in - ask_alert) / ask_alert * 10000.0
            drift.append(d)
            drift_blocks.append(wk_in)
            row["alert_ask"], row["alert_to_fill_bps"] = ask_alert, d

        # ---- exit leg
        fill_out = _f(o.get("exit_premium"))
        wk_out = week_key(o.get("exit_ts") or o.get("updated_at"))
        if fill_out is not None:
            touch_out = _f(o.get("last_mark"))
            if touch_out is not None:
                v = signed_vs_limit(fill_out, touch_out, "sell")
                exit_vs_touch.append(v)
                exit_blocks.append(wk_out)
                row["exit_touch_bid"], row["exit_vs_touch_bps"] = touch_out, v
            mid_out = _f(o.get("last_mid"))
            # THE HEADLINE. Only rows carrying audit B5a's `last_mid` can contribute; a row
            # written before that migration has no mid and is counted as a coverage gap rather
            # than filled in from the bid, which would report a zero half-spread by construction.
            hs = half_spread_bps(mid_out, fill_out, "sell")
            if hs is not None:
                exit_half.append(hs)
                exit_half_blocks.append(wk_out)
                row["exit_mid"], row["exit_half_spread_bps"] = mid_out, hs
            row["exit_fill"] = fill_out
        detail.append(row)

    return {"entry_vs_touch": (entry_vs_touch, entry_blocks),
            "exit_vs_touch": (exit_vs_touch, exit_blocks),
            "exit_half_spread": (exit_half, exit_half_blocks),
            "alert_to_fill": (drift, drift_blocks),
            "states": states, "detail": detail}


def fill_funnel(orders, states) -> dict:
    """M4 — the cost a fill-vs-limit measure structurally cannot see.

    A limit at the touch buys a bounded fill price by accepting the risk of no fill. A book with
    excellent measured slippage and a 40% non-fill rate is a WORSE book, and only this shows it.
    """
    n = len(orders)
    filled = sum(1 for o in orders if str(o.get("state")) in FILLED_STATES)
    rejected = int(states.get("rejected", 0))
    working = int(states.get("submitted", 0)) + int(states.get("claimed", 0))
    skipped = int(states.get("skipped", 0))
    pending = int(states.get("pending", 0))
    deferred = sum(1 for o in orders
                   if "deferred" in str(o.get("note") or "").lower()
                   or "no bid" in str(o.get("note") or "").lower())
    out = {"n_rows": n, "n_filled": filled, "n_rejected": rejected, "n_still_working": working,
           "n_skipped": skipped, "n_pending_dry_run": pending, "n_deferred_no_bid": deferred,
           "states": dict(states)}
    decided = filled + rejected
    out["fill_rate_of_decided"] = (filled / decided) if decided else None
    out["fill_rate_of_all_rows"] = (filled / n) if n else None
    return out


def broker_limits(orders, broker) -> dict:
    """M1 — the true limit prices, which the store does not keep. Optional, needs the sandbox.

    Failures are counted, not raised: an order the sandbox has aged out is a data gap, and a
    report that dies on the first missing id measures nothing.
    """
    out = {"entry": {}, "exit": {}, "errors": 0, "missing": 0}
    for o in orders:
        for leg, key in (("entry", "entry_order_id"), ("exit", "exit_order_id")):
            oid = o.get(key)
            if not oid:
                continue
            try:
                od = broker.order(oid) or {}
            except Exception:                                          # noqa: BLE001
                out["errors"] += 1
                continue
            lim, fill = _f(od.get("price")), _f(od.get("avg_fill_price"))
            if lim is None or fill is None:
                out["missing"] += 1
                continue
            out[leg][o.get("alert_id")] = {"limit": lim, "fill": fill,
                                           "bps": signed_vs_limit(
                                               fill, lim, "buy" if leg == "entry" else "sell")}
    return out


# ============================== the report ==================================================
def build_report(db_path: str, broker=None, export_path: Optional[str] = None) -> dict:
    store = read_export(export_path) if export_path else read_store(db_path)
    orders, alerts = store["orders"], store["alerts"]
    legs = build_legs(orders, alerts)
    funnel = fill_funnel(orders, legs["states"])

    rep = {
        "measure": "V5 - measured slippage vs modelled costs",
        "register": "PREREG_v5_slippage.md",
        "db": os.path.abspath(export_path or db_path),
        "schema": store.get("schema"),
        "sandbox_caveat": SANDBOX_CAVEAT,
        "modelled": {
            "entry_half_spread_bps_mean": MODELLED_ENTRY_HALF_SPREAD_BPS,
            "entry_half_spread_bps_median": MODELLED_ENTRY_HALF_SPREAD_MEDIAN_BPS,
            "commission_round_trip_usd": MODELLED_COMMISSION_ROUND_TRIP,
            "median_entry_premium_usd": MODELLED_MEDIAN_ENTRY_PREMIUM,
            "source": ("data/options_universe/state_r2_corrected.pkl, 3885/3885 trades with "
                       "entry_spread_pct; half-spread = entry_spread_pct / 2"),
            "equity_33_4bps_does_not_apply": (
                "audit B11's %.1f bps one-way is basis points of STOCK NOTIONAL on the "
                "fundamental panel. This book pays basis points of PREMIUM. The ratio is about "
                "12x and the two are not the same currency."
                % EQUITY_ONE_WAY_BPS_NOT_APPLICABLE),
        },
        "m3_exit_half_spread_HEADLINE": summarise(
            *legs["exit_half_spread"], label="exit half-spread vs mid (bps, + = cost)",
            modelled=MODELLED_ENTRY_HALF_SPREAD_BPS),
        "m2_entry_vs_touch": summarise(
            *legs["entry_vs_touch"],
            label="entry fill vs reconstructed submit ask (bps, + = worse than the limit)"),
        "m2_exit_vs_touch": summarise(
            *legs["exit_vs_touch"],
            label="exit fill vs last bid (bps, + = worse than the limit)"),
        "m5_alert_to_fill_NOT_SLIPPAGE": summarise(
            *legs["alert_to_fill"],
            label="alert-time ask -> entry fill (bps). SIGNAL DECAY AND LATENCY, NOT SLIPPAGE"),
        "m4_fill_funnel": funnel,
        "diagnostic_exit_level_fidelity": exit_level_fidelity(orders, alerts),
        "diagnostic_sizing_veto_ignored": sizing_veto_ignored(orders, alerts),
        "not_measurable": {
            "entry_half_spread": (
                "paper_option_orders stores no bid/ask/mid at submit, so the entry MID does not "
                "exist in the schema and the entry half-spread cannot be computed. The ASK is "
                "recoverable from target_premium; the MID is not. ROUTED, NOT MADE (V5 is scoped "
                "new files only): add entry_bid and entry_ask, written in "
                "paper_track._place_entry beside the existing target/stop."),
            "market_impact": ("a sandbox has no book to move, so nothing here bears on the "
                              "capacity number beyond a 1-lot fill"),
            "size": ("paper_contracts_per_trade defaults to 1; a 1-lot fill says nothing about "
                     "a 100-lot fill"),
            "equity_mirror": ("seed_book(place_equity=False) is the default, so no equity fills "
                              "exist; S14's no-trade band and the capacity number are EQUITY "
                              "constructs and option-leg slippage cannot feed them"),
        },
        "m1_fill_vs_limit_structurally_bounded": (
            "a marketable limit cannot fill worse than its limit, so this can only show zero or "
            "price improvement. Pre-registered as never the headline. Use --broker to populate."),
    }
    if broker is not None:
        rep["m1_broker_limits"] = broker_limits(orders, broker)
    return rep


def _fmt_measure(m: dict) -> str:
    head = "  %-58s n=%d" % (m["label"], m["n"])
    if not m.get("quotable"):
        out = head + "\n      %s" % m.get("note", "NOT QUOTABLE")
        # The register promises the individual values below the minimum. Printing "NOT QUOTABLE"
        # and nothing else would hide the only data there is.
        if m.get("values"):
            out += "\n      raw: " + ", ".join("%+.1f" % v for v in m["values"])
        return out
    ci = m.get("ci90") or {}
    line = ("\n      mean %+.1f bps   median %+.1f   p10 %+.1f   p90 %+.1f"
            % (m["mean"], m["median"], m["p10"], m["p90"]))
    if ci:
        line += ("\n      90%% CI [%+.1f, %+.1f]  (%d week-blocks, %d draws, seed %d)"
                 % (ci["lo"], ci["hi"], ci["n_blocks"], ci["draws"], ci["seed"]))
    if m.get("verdict"):
        line += "\n      vs modelled %.1f bps -> %s" % (m.get("modelled_bps", 0.0), m["verdict"])
    return head + line


def render(rep: dict) -> str:
    L = []
    L.append("=" * 92)
    L.append("V5 - MEASURED SLIPPAGE vs MODELLED COSTS   (register: %s)" % rep["register"])
    L.append("=" * 92)
    L.append("store : %s  [schema %s]" % (rep["db"], rep["schema"]))
    L.append("")
    L.append("SANDBOX CAVEAT: " + rep["sandbox_caveat"])
    L.append("")
    md = rep["modelled"]
    L.append("MODELLED BAR: entry half-spread mean %.1f bps of premium (median %.1f), "
             "commission $%.2f round trip"
             % (md["entry_half_spread_bps_mean"], md["entry_half_spread_bps_median"],
                md["commission_round_trip_usd"]))
    L.append("  source: %s" % md["source"])
    L.append("  NOTE:   %s" % md["equity_33_4bps_does_not_apply"])
    L.append("")
    L.append("-" * 92)
    L.append("M3  HEADLINE - exit half-spread paid vs the mid")
    L.append(_fmt_measure(rep["m3_exit_half_spread_HEADLINE"]))
    L.append("")
    L.append("M2  fill vs the touch (structurally bounded at <= 0; never a headline)")
    L.append(_fmt_measure(rep["m2_entry_vs_touch"]))
    L.append(_fmt_measure(rep["m2_exit_vs_touch"]))
    L.append("")
    L.append("M5  alert -> fill drift  (NOT SLIPPAGE - different timestamps)")
    L.append(_fmt_measure(rep["m5_alert_to_fill_NOT_SLIPPAGE"]))
    L.append("")
    f = rep["m4_fill_funnel"]
    L.append("M4  fill funnel - the cost a fill-vs-limit measure cannot see")
    L.append("      rows %d | filled %d | rejected %d | still working %d | skipped %d | "
             "dry-run pending %d | deferred no-bid %d"
             % (f["n_rows"], f["n_filled"], f["n_rejected"], f["n_still_working"],
                f["n_skipped"], f["n_pending_dry_run"], f["n_deferred_no_bid"]))
    fr = f.get("fill_rate_of_decided")
    L.append("      fill rate of decided rows: %s"
             % ("n/a (no decided rows)" if fr is None else "%.1f%%" % (fr * 100.0)))
    if "m1_broker_limits" in rep:
        b = rep["m1_broker_limits"]
        L.append("")
        L.append("M1  broker limit prices: %d entry, %d exit, %d errors, %d missing"
                 % (len(b["entry"]), len(b["exit"]), b["errors"], b["missing"]))
    L.append("")
    ef = rep["diagnostic_exit_level_fidelity"]
    L.append("DIAGNOSTIC (no verdict, not in the register) - are the LIVE exit levels the "
             "BACKTESTED ones?")
    L.append("      %d positions, %d OFF SPEC" % (ef["n_positions"], ef["n_off_spec"]))
    for r in ef["rows"]:
        st = ("" if r["realised_stop_pct"] is None
              else "  stop %+.1f%%" % (r["realised_stop_pct"] * 100.0))
        L.append("        %-6s fill %7.2f  target %+.1f%% (intended %+.1f%%)%s"
                 % (r["ticker"], r["entry_fill"], r["realised_target_pct"] * 100.0,
                    r["intended_target_pct"] * 100.0, st))
    if ef["n_off_spec"]:
        L.append("      %s" % ef["what"])
    sv = rep["diagnostic_sizing_veto_ignored"]
    if sv["n_traded_against_a_skip"]:
        L.append("")
        L.append("DIAGNOSTIC (no verdict) - positions the ALERT'S OWN SIZING REFUSED: %d"
                 % sv["n_traded_against_a_skip"])
        for r in sv["rows"]:
            L.append("        %-6s state=%-7s fill %s  sizing said contracts=%s: %s"
                     % (r["ticker"], r["state"], r["entry_fill"], r["sizing_contracts"],
                        r["reason"]))
    L.append("")
    L.append("NOT MEASURABLE HERE:")
    for k, v in rep["not_measurable"].items():
        L.append("  * %-20s %s" % (k, v))
    L.append("=" * 92)
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1].strip())
    ap.add_argument("--db", default=os.path.join("data", "screener.db"),
                    help="screener store to read (READ-ONLY)")
    ap.add_argument("--from-export", dest="export_path", default=None,
                    help="read track_export's backup payload instead of a store "
                         "(data_export/paper_track_history.json) - the only source of real "
                         "fills reachable off Render")
    ap.add_argument("--broker", action="store_true",
                    help="also read limit prices from the Tradier SANDBOX (M1)")
    ap.add_argument("--json", dest="json_out", default=None, help="write the report as JSON too")
    args = ap.parse_args(argv)

    broker = None
    if args.broker:
        from valuation.edge.paper_broker import NotSandboxError, PaperBroker
        try:
            broker = PaperBroker()
        except NotSandboxError as e:
            print("--broker unavailable: %s" % e, file=sys.stderr)
            broker = None

    try:
        rep = build_report(args.db, broker=broker, export_path=args.export_path)
    except FileNotFoundError as e:
        print("no such store: %s" % e, file=sys.stderr)
        return 2
    print(render(rep))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=2, default=str)
        print("\nwrote %s" % args.json_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
