"""The path study — stage 1, descriptive (options bot, 2026-08-10).

    python -m scripts.path_study --stage1

Pre-registered in `PREREG_path_study.md`, committed before any table here was computed.

WHAT THIS ANSWERS. The shipped exit is +100% target / -50% stop / half-DTE time stop. O1 raced
static ladders against it and rejected all of them; O23 showed half of any exit's P&L difference
is just the underlying. Neither looked at the PATH: how deep a trade digs before it dies, whether
a -40% option comes back, how long a winner takes, what happens after a winner hits its target.

THE CAVEAT TRAVELS WITH EVERY NUMBER. The options entry signal is dead (R2: +3.41%/trade against
a five-seed random-entry control's +10.06%, sign-test z -4.903). Nothing computed here is a
tradeable-edge claim. It is paper-book policy and structural knowledge.

THE SOURCE. Paths are rebuilt from the frozen chains
(`data/options_freeze/R2_CORRECTED_2026-08-08/chains.pkl.gz`, 2,870,811 rows, frozen against the
book banked three days earlier) rather than read from `data/options_exitlab/paths.pkl`, which
covers only 1,099 of the 3,885 banked trades and carries 2,020 the book does not.

THE COUNTERFACTUAL IS HYPOTHETICAL. A trade the shipped policy stopped at -50% did not actually
continue. The post-exit marks say what the CONTRACT did, not what a POSITION did. That is the
question being asked, and it is not a realised P&L.
"""
import argparse
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import options_fill as F          # noqa: E402
from valuation.edge import options_freeze as FZ       # noqa: E402

# --------------------------------------------------------------------------------------- #
# Locations. `data/` is gitignored and lives in the primary checkout, so a worktree looks up.
# --------------------------------------------------------------------------------------- #
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data_root() -> str:
    """The licensed data lives in the primary checkout, so a worktree looks three levels up.

    MUST NOT raise at import. `data/` is gitignored, so CI has no freeze at all — and this
    module is imported by `tests/test_path_study.py`, which pins the algebra and the arm set
    and needs none of it. An import-time `SystemExit` here would fail the whole auto-land gate
    on a fresh checkout. The scripts that genuinely need the freeze fail when they open it,
    which is the right place for that error.
    """
    for cand in (os.path.join(_HERE, "data"),
                 os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isdir(os.path.join(cand, "options_freeze")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
SIGNAL_BOOK = os.path.join(DATA, "options_universe", "state_r2_corrected.pkl")
CONTROL_BOOKS = [os.path.join(DATA, "options_universe", "control_r2_seed%d.pkl" % s)
                 for s in range(5)]
SIGNAL_FREEZE = os.path.join(DATA, "options_freeze", "R2_CORRECTED_2026-08-08", "chains.pkl.gz")
CONTROL_FREEZE = os.path.join(DATA, "options_freeze", "R2_CONTROLS_2026-08-08", "chains.pkl.gz")
OUT_DIR = os.path.join(DATA, "options_pathstudy")

AGGRESSION = 1.0
TOUCH_LEVELS = (-0.25, -0.40, -0.50, -0.60)
DTE_BUCKETS = ((0, 7, "<=7"), (8, 21, "8-21"), (22, 45, "22-45"), (46, 10**6, ">45"))
TARGET = 1.00


def _log(m):
    print(m, flush=True)


def _key(sym, expiry, strike, right) -> str:
    return "%s|%s|%.3f|%s" % (sym, expiry, round(float(strike), 3), str(right)[0].upper())


def book_rows(path: str) -> list:
    import pickle
    with open(path, "rb") as f:
        d = pickle.load(f)
    return d["rows"] if isinstance(d, dict) else d


def _row_key(r) -> str:
    return _key(r["ticker"], r["expiry"], r["strike"], r["opt_right"])


# --------------------------------------------------------------------------------------- #
# Path reconstruction
# --------------------------------------------------------------------------------------- #
def build_paths(rows: list, freeze_path: str, label: str) -> dict:
    """(trade key -> ordered list of (date, ret)) for every banked trade we can price.

    `ret` uses the SELL-side fill and the banked entry premium, which is exactly what
    `options_exitlab.apply_policy` tests its levels against — not mid, and not a re-derivation.
    """
    import pandas as pd

    _log("[%s] loading freeze %s" % (label, os.path.basename(os.path.dirname(freeze_path))))
    df = FZ.load_frozen(freeze_path)
    _log("[%s] freeze rows %d" % (label, len(df)))

    wanted = {}
    for i, r in enumerate(rows):
        wanted.setdefault(_row_key(r), []).append(i)

    k = (df["symbol"].astype(str) + "|" + df["expiration"].astype(str) + "|"
         + df["strike"].astype(float).round(3).map(lambda v: "%.3f" % v) + "|"
         + df["right"].astype(str).str[0].str.upper())
    df = df.assign(_k=k)
    df = df[df["_k"].isin(wanted)]
    _log("[%s] rows for banked contracts: %d" % (label, len(df)))
    df = df.sort_values(["_k", "date"])

    by_key = {}
    for kk, sub in df.groupby("_k", sort=False, observed=True):
        by_key[kk] = list(zip(sub["date"].astype(str).tolist(),
                              sub["bid"].tolist(), sub["ask"].tolist()))

    out, missing, no_days = {}, 0, 0
    for kk, idxs in wanted.items():
        quotes = by_key.get(kk)
        if not quotes:
            missing += len(idxs)
            continue
        for i in idxs:
            r = rows[i]
            entry = r["alert_ts"]
            fill = float(r["entry_premium"])
            if not fill or fill <= 0:
                missing += 1
                continue
            seq = []
            for ds, bid, ask in quotes:
                if ds <= entry or ds > r["expiry"]:
                    continue
                q = F.Quote(bid=bid, ask=ask)
                if F.exit_reject_reason(q) is not None:
                    continue                       # post-B2 rule, as the banked book was built
                mark = F.fill_price(q, "sell", AGGRESSION)
                if mark is None:
                    continue
                seq.append((ds, mark / fill - 1.0))
            if not seq:
                no_days += 1
                continue
            out[i] = seq
    _log("[%s] paths built %d / %d trades  (no contract %d, no usable day %d)"
         % (label, len(out), len(rows), missing, no_days))
    return out


# --------------------------------------------------------------------------------------- #
# Stage 1 measures
# --------------------------------------------------------------------------------------- #
def _dte_bucket(days: int) -> str:
    for lo, hi, name in DTE_BUCKETS:
        if lo <= days <= hi:
            return name
    return ">45"


def trade_facts(r, seq) -> dict:
    """Everything stage 1 needs from one trade, computed once."""
    entry = dt.date.fromisoformat(r["alert_ts"])
    expiry = dt.date.fromisoformat(r["expiry"])
    dte0 = (expiry - entry).days
    exit_day = entry + dt.timedelta(days=int(r["held_days"]))

    pre, post = [], []
    for ds, ret in seq:
        (pre if dt.date.fromisoformat(ds) <= exit_day else post).append((ds, ret))

    mae_pre = min((x[1] for x in pre), default=None)
    mae_all = min((x[1] for x in seq), default=None)
    mfe_all = max((x[1] for x in seq), default=None)

    # first touch of each adverse level, on the FULL life
    touches = {}
    for lvl in TOUCH_LEVELS:
        hit = next((i for i, (_, ret) in enumerate(seq) if ret <= lvl), None)
        if hit is None:
            touches[lvl] = None
            continue
        ds = seq[hit][0]
        rest = seq[hit + 1:]
        touches[lvl] = {
            "date": ds,
            "dte_left": (expiry - dt.date.fromisoformat(ds)).days,
            "back_to_zero": any(ret >= 0.0 for _, ret in rest),
            "to_target": any(ret >= TARGET for _, ret in rest),
            "max_after": max((ret for _, ret in rest), default=None),
            "final_after": rest[-1][1] if rest else None,
            "days_left": len(rest),
        }

    tgt = next((i for i, (_, ret) in enumerate(seq) if ret >= TARGET), None)
    target_block = None
    if tgt is not None:
        ds = seq[tgt][0]
        d = dt.date.fromisoformat(ds)
        rest = seq[tgt + 1:]
        target_block = {
            "date": ds,
            "days_to": (d - entry).days,
            "frac_dte": (d - entry).days / dte0 if dte0 else None,
            "dte_left": (expiry - d).days,
            "half_dte_left": ((expiry - d).days > dte0 / 2.0) if dte0 else False,
            "max_after": max((ret for _, ret in rest), default=None),
            "final_after": rest[-1][1] if rest else None,
            "reached_200": any(ret >= 2.0 for _, ret in rest),
            "fell_below_100": any(ret < TARGET for _, ret in rest),
            "fell_below_0": any(ret < 0.0 for _, ret in rest),
            "days_left": len(rest),
            "last_quote_dte": (expiry - dt.date.fromisoformat(rest[-1][0])).days if rest else 0,
        }

    return {"dte0": dte0, "n_days": len(seq), "n_pre": len(pre), "n_post": len(post),
            "mae_pre": mae_pre, "mae_all": mae_all, "mfe_all": mfe_all,
            "banked_pnl_pct": r.get("pnl_pct"), "banked_reason": r.get("exit_reason"),
            "held_days": r.get("held_days"), "touches": touches, "target": target_block}


def _pct(a, b):
    return None if not b else round(100.0 * a / b, 1)


def _quantiles(vals, qs=(0.05, 0.25, 0.50, 0.75, 0.95)):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return {}
    out = {}
    for q in qs:
        i = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
        out["p%d" % int(q * 100)] = round(v[i], 4)
    out["mean"] = round(sum(v) / len(v), 4)
    out["n"] = len(v)
    return out


def stage1_tables(facts: list) -> dict:
    n = len(facts)
    base_target = sum(1 for f in facts if f["target"] is not None)

    # --- MAE ------------------------------------------------------------------------------
    mae = {
        "before_banked_exit": _quantiles([f["mae_pre"] for f in facts]),
        "full_contract_life": _quantiles([f["mae_all"] for f in facts]),
        "by_banked_outcome": {},
    }
    for reason in sorted({str(f["banked_reason"]) for f in facts}):
        sel = [f for f in facts if str(f["banked_reason"]) == reason]
        mae["by_banked_outcome"][reason] = {
            "n": len(sel), "mae_pre": _quantiles([f["mae_pre"] for f in sel])}

    # --- recovery from a touch, by DTE remaining ------------------------------------------
    recovery = {}
    for lvl in TOUCH_LEVELS:
        name = "%d" % int(round(lvl * 100))
        hits = [f for f in facts if f["touches"][lvl]]
        rows = {"n_touched": len(hits), "pct_of_book": _pct(len(hits), n), "by_dte_left": {}}
        rows["pooled"] = {
            "n": len(hits),
            "back_to_zero_pct": _pct(sum(1 for f in hits if f["touches"][lvl]["back_to_zero"]),
                                     len(hits)),
            "to_target_pct": _pct(sum(1 for f in hits if f["touches"][lvl]["to_target"]),
                                  len(hits)),
            "median_max_after": _quantiles(
                [f["touches"][lvl]["max_after"] for f in hits]).get("p50"),
        }
        for _, _, bname in DTE_BUCKETS:
            sel = [f for f in hits if _dte_bucket(f["touches"][lvl]["dte_left"]) == bname]
            rows["by_dte_left"][bname] = {
                "n": len(sel),
                "back_to_zero_pct": _pct(
                    sum(1 for f in sel if f["touches"][lvl]["back_to_zero"]), len(sel)),
                "to_target_pct": _pct(
                    sum(1 for f in sel if f["touches"][lvl]["to_target"]), len(sel)),
            }
        recovery[name] = rows

    # --- time to target -------------------------------------------------------------------
    tg = [f["target"] for f in facts if f["target"]]
    time_to_target = {
        "n_reached": len(tg), "pct_of_book": _pct(len(tg), n),
        "days": _quantiles([t["days_to"] for t in tg]),
        "frac_of_dte0": _quantiles([t["frac_dte"] for t in tg]),
    }

    # --- post-target continuation ---------------------------------------------------------
    early = [t for t in tg if t["half_dte_left"]]
    cont = {
        "n_target_with_half_dte_left": len(early),
        "pct_of_targets": _pct(len(early), len(tg)),
        "max_after": _quantiles([t["max_after"] for t in early]),
        "final_after": _quantiles([t["final_after"] for t in early]),
        "reached_200_pct": _pct(sum(1 for t in early if t["reached_200"]), len(early)),
        "fell_below_100_pct": _pct(sum(1 for t in early if t["fell_below_100"]), len(early)),
        "fell_below_0_pct": _pct(sum(1 for t in early if t["fell_below_0"]), len(early)),
        # O1's stale-mark hazard, reported rather than averaged over.
        "median_dte_of_last_quote": _quantiles(
            [t["last_quote_dte"] for t in early]).get("p50"),
        "pct_last_quote_more_than_5d_before_expiry": _pct(
            sum(1 for t in early if t["last_quote_dte"] > 5), len(early)),
    }

    return {"n_trades": n, "base_rate_reached_target_pct": _pct(base_target, n),
            "mae": mae, "recovery": recovery, "time_to_target": time_to_target,
            "post_target_continuation": cont}


# --------------------------------------------------------------------------------------- #
def run_stage1(with_controls: bool = True) -> dict:
    res = {"definitions": {
        "mark": "options_fill.fill_price(Quote(bid,ask),'sell',1.0) — sell-side, not mid",
        "ret": "mark / banked entry_premium - 1, gross of commission",
        "days_kept": "frozen quote days after the alert date to expiry with "
                     "exit_reject_reason is None (post-B2 rule)",
        "counterfactual": "recovery is measured on the FULL contract life, ignoring the "
                          "shipped exit — what the CONTRACT did, not what a POSITION did",
        "aggression": AGGRESSION,
    }}

    rows = book_rows(SIGNAL_BOOK)
    paths = build_paths(rows, SIGNAL_FREEZE, "signal")
    facts = [trade_facts(rows[i], seq) for i, seq in sorted(paths.items())]
    res["signal"] = stage1_tables(facts)
    res["signal"]["coverage"] = {
        "banked_trades": len(rows), "paths_built": len(paths),
        "coverage_pct": _pct(len(paths), len(rows))}

    if with_controls:
        import pickle
        allrows, allfacts, per_seed = [], [], {}
        cdf = None
        for s, bp in enumerate(CONTROL_BOOKS):
            if not os.path.exists(bp):
                continue
            with open(bp, "rb") as f:
                crows = pickle.load(f)
            crows = crows["rows"] if isinstance(crows, dict) else crows
            per_seed[s] = len(crows)
            allrows.append((s, crows))
        if allrows:
            flat = [r for _, crows in allrows for r in crows]
            cpaths = build_paths(flat, CONTROL_FREEZE, "control-pooled")
            cfacts = [trade_facts(flat[i], seq) for i, seq in sorted(cpaths.items())]
            res["control_pooled"] = stage1_tables(cfacts)
            res["control_pooled"]["coverage"] = {
                "seeds": per_seed, "banked_trades": len(flat),
                "paths_built": len(cpaths), "coverage_pct": _pct(len(cpaths), len(flat))}
            allfacts = cfacts
        res["control_note"] = ("five random-entry seeds pooled; R2's standing rule is five "
                               "seeds minimum because a single seed's mean ranges +6.46%% to "
                               "+15.34%%")
        del allfacts, cdf
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1", action="store_true")
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if not a.stage1:
        ap.error("nothing to do; pass --stage1")
    res = run_stage1(with_controls=not a.no_controls)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = a.out or os.path.join(OUT_DIR, "PATHSTUDY_STAGE1.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    _log("wrote " + out)
    return res


if __name__ == "__main__":
    main()
