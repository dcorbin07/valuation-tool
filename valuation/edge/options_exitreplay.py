"""O1 + O23 — the exit ladder replayed from the FROZEN chain copy, and decomposed against the
underlying.

Register: `PREREG_o1_o23_exits.md`, committed at `dc2c486` before any policy was scored.

WHY THIS IS A SEPARATE MODULE. `options_exitlab.py` carries its own pre-registration, written on
2026-08-03 above a "RESULT" banner, and its 21 policies are the object of study here. Editing it
to add a replay path would put new code inside a register that was closed before this study
existed. So the policies, the gate and the evaluator are IMPORTED unamended and everything new
lives here: the frozen-chain provider, the four-way pattern label the brief required, and O23's
decomposition.

--------------------------------------------------------------------------------------------
WHAT "REPLAY FROM THE FROZEN BOOK ONLY" MEANS MECHANICALLY.

`options_exitlab.capture_path` needs two things from the chain store: the ENTRY quote on the
alert date, and the selected contract's daily history from entry to expiry. The 2026-08-08 freeze
contains both — the alert-day chain slice supplies the first and the contract-history slice the
second — which is why this study is runnable at all. `FrozenChains` serves exactly those two
reads and NOTHING else; it has no fallback to the live store, so a gap surfaces as a missing
path rather than as a silent live read.

That is the whole point. A provider with a fallback would make the freeze unfalsifiable: every
replay would succeed and no one would ever learn whether the frozen copy was sufficient.

--------------------------------------------------------------------------------------------
THE UNDERLYING LEG IS NOT COVERED BY THE OPTIONS FREEZE, AND O23 IS THE FIRST STUDY THAT CARES.

Underlying closes come from `data/bulk/prepared/bars/` (Sharadar SEP), a different store on a
different refresh cycle. The options freeze says nothing about it. O1 touches it only for
settlement at expiry; O23's headline rests on it directly. `stamp_bars()` fingerprints the bars
files a run consumed so the gap is recorded per-run instead of being rediscovered later.
"""
from __future__ import annotations

import hashlib
import math
import os
from typing import Optional

from . import options_backtest as OB
from . import options_exitlab as EL
from . import options_stats as OS

BARS_ROOT = OB.BARS_CACHE

# O23 verdict bars, fixed in the register before any number existed.
O23_UNDERLYING_R2 = 0.50        # >= this, with the CI95 LOWER bound also >= it -> UNDERLYING-DRIVEN
O23_OPTION_R2 = 0.25            # <= this, with the CI95 UPPER bound also <= it -> OPTION-DRIVEN
O23_MIN_DIFFERING = 30          # a policy needs this many differing-exit trades to be scored
BOOT_DRAWS = 2000
BOOT_SEED = 0


def _log(m):
    print("[exitreplay] %s" % m, flush=True)


def _right_letter(v) -> str:
    return "C" if str(v).lower().startswith("c") else "P"


# ============================ the frozen chain provider ====================================
class FrozenChains:
    """Serves `contract_history` and the alert-day entry quote from a frozen copy.

    NO FALLBACK TO THE LIVE STORE, deliberately. If the freeze is missing a contract this must
    fail visibly, because "did the freeze actually contain enough to replay the book" is the
    question the blocking gate exists to answer.
    """

    def __init__(self, df):
        import pandas as pd

        d = df.copy()
        d["_sym"] = d["symbol"].astype(str).str.upper()
        d["_exp"] = pd.to_datetime(d["expiration"]).dt.strftime("%Y-%m-%d")
        d["_r"] = d["right"].astype(str).str.upper().str[0]
        d["_date"] = pd.to_datetime(d["date"]).dt.strftime("%Y-%m-%d")
        d["_k"] = (d["_sym"] + "|" + d["_exp"] + "|"
                   + d["strike"].astype(float).round(3).map(lambda x: "%.3f" % x) + "|" + d["_r"])
        d = d.sort_values(["_k", "_date"], kind="mergesort")
        self._g = {k: v for k, v in d.groupby("_k", sort=False)}
        self.n_rows = len(d)
        self.n_contracts = len(self._g)

    @staticmethod
    def key(ticker, expiry, strike, right) -> str:
        return "%s|%s|%.3f|%s" % (str(ticker).upper(), str(expiry)[:10],
                                  float(strike), _right_letter(right))

    def contract_history(self, ticker, expiry, strike, right, start, end):
        """The signature `options_exitlab.capture_path` calls. Dates are inclusive."""
        import pandas as pd

        sub = self._g.get(self.key(ticker, expiry, strike, right))
        if sub is None or not len(sub):
            return None
        lo, hi = str(start)[:10], str(end)[:10]
        m = (sub["_date"] >= lo) & (sub["_date"] <= hi)
        out = sub.loc[m, ["date", "bid", "ask", "volume", "open_interest"]].copy()
        if not len(out):
            return None
        out["date"] = pd.to_datetime(out["date"]).dt.date
        return out

    def quote_on(self, ticker, expiry, strike, right, day) -> Optional[dict]:
        """The alert-day entry quote, from the frozen alert-day chain slice."""
        sub = self._g.get(self.key(ticker, expiry, strike, right))
        if sub is None:
            return None
        hit = sub[sub["_date"] == str(day)[:10]]
        if not len(hit):
            return None
        r = hit.iloc[0]
        return {"strike": float(r["strike"]), "right": _right_letter(r["right"]),
                "expiration": str(r["_exp"]), "bid": r["bid"], "ask": r["ask"],
                "open_interest": r["open_interest"], "volume": r["volume"]}


# ============================ path building ================================================
def build_paths(rows, chains: FrozenChains, bars_by_ticker: dict) -> tuple:
    """Book rows -> `capture_path` dicts, sourced entirely from the freeze.

    Returns (paths, diagnostics). Every drop is counted and bucketed by REASON — a path builder
    that silently returns fewer paths than trades would quietly change the object of study.
    """
    import datetime as dt

    paths, diag = [], {"n_rows": len(rows), "no_entry_quote": 0, "no_contract": 0,
                       "no_bars": 0, "capture_none": 0, "ok": 0}
    for r in rows:
        tk = str(r.get("ticker") or "").upper()
        bars = bars_by_ticker.get(tk)
        if not bars:
            diag["no_bars"] += 1
            continue
        exp = str(r.get("expiry"))[:10]
        strike = float(r.get("strike"))
        right = _right_letter(r.get("opt_right"))
        day = str(r.get("alert_ts"))[:10]
        if chains.key(tk, exp, strike, right) not in chains._g:
            diag["no_contract"] += 1
            continue
        er = chains.quote_on(tk, exp, strike, right, day)
        if er is None:
            diag["no_entry_quote"] += 1
            continue
        p = EL.capture_path(chains, tk, er, dt.date.fromisoformat(day), bars)
        if p is None:
            diag["capture_none"] += 1
            continue
        p["cap_tier"] = r.get("cap_tier")
        p["alert_date"] = day
        p["book_pnl_pct"] = r.get("pnl_pct")
        p["book_exit_reason"] = r.get("exit_reason")
        p["book_held_days"] = r.get("held_days")
        paths.append(p)
        diag["ok"] += 1
    return paths, diag


def load_bars_for(tickers, root: str = BARS_ROOT) -> tuple:
    """Bars for a ticker set, from cache ONLY. Returns (mapping, missing)."""
    import pickle

    out, missing = {}, []
    for t in sorted({str(x).upper() for x in tickers}):
        p = os.path.join(root, "%s.pkl" % t)
        if not os.path.exists(p):
            missing.append(t)
            continue
        try:
            with open(p, "rb") as f:
                out[t] = pickle.load(f)
        except (OSError, pickle.UnpicklingError):
            missing.append(t)
    return out, missing


def stamp_bars(tickers, root: str = BARS_ROOT) -> dict:
    """Fingerprint the bars files a run consumed.

    The options freeze does NOT cover this store, and O23's headline depends on it. Recording the
    bytes per run is the cheapest thing that makes the gap auditable instead of invisible.
    """
    out = {}
    for t in sorted({str(x).upper() for x in tickers}):
        p = os.path.join(root, "%s.pkl" % t)
        if not os.path.exists(p):
            out[t] = {"present": False}
            continue
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        out[t] = {"present": True, "sha256": h.hexdigest(), "bytes": os.path.getsize(p)}
    return out


# ============================ G0b — replay fidelity ========================================
def replay_fidelity(paths, book_rows, tol: float = 1e-6) -> dict:
    """Does the `shipped` policy, replayed from the FREEZE, reproduce the banked book?

    The register's blocking gate. `options_exitlab.replay_matches_shipped` answers a narrower
    question (does the evaluator reproduce production, at 1e-9, on last_quote settlement); this
    one is stated at the register's own tolerance and also compares `exit_reason`, because a
    policy that lands the same P&L for a different reason has not reproduced the book.
    """
    got = {(r["ticker"], str(r["alert_ts"])[:10]): r
           for r in EL.score_paths(paths, EL.BASELINE, dict(EL.SHIPPED), settle="last_quote")}
    want = {(str(r.get("ticker")).upper(), str(r.get("alert_ts"))[:10]): r for r in book_rows}
    shared = sorted(set(got) & set(want))
    pnl_bad, reason_bad, ex = [], [], []
    for k in shared:
        a, b = got[k], want[k]
        pa, pb = a.get("pnl_pct"), b.get("pnl_pct")
        if pa is None or pb is None or abs(float(pa) - float(pb)) > tol:
            pnl_bad.append(k)
            if len(ex) < 5:
                ex.append({"key": list(k), "replay_pnl": pa, "book_pnl": pb,
                           "replay_reason": a.get("exit_reason"),
                           "book_reason": b.get("exit_reason")})
        if str(a.get("exit_reason")) != str(b.get("exit_reason")):
            reason_bad.append(k)
    n = len(shared)
    return {"n_book": len(want), "n_replayed": len(got), "n_shared": n,
            "n_pnl_mismatch": len(pnl_bad), "n_reason_mismatch": len(reason_bad),
            "pnl_match_rate": (n - len(pnl_bad)) / n if n else None,
            "reason_match_rate": (n - len(reason_bad)) / n if n else None,
            "only_in_replay": len(set(got) - set(want)),
            "only_in_book": len(set(want) - set(got)),
            "tol": tol, "examples": ex,
            "matching_keys": [list(k) for k in shared if k not in set(pnl_bad)][:0]}


# ============================ O1 — the four-way pattern label ==============================
def pattern_labels(res: dict) -> dict:
    """The brief required which pattern counts as which to be fixed BEFORE the run. It is, in
    the register; this applies it mechanically.

        both sets    -> EXIT EFFECT      (a property of the exit)
        signal only  -> SIGNAL-ONLY      (entry information leaking through the exit)
        random only  -> CONTROL-ONLY     (explicitly NOT adopted: no deployment path here)
        neither      -> REJECT
    """
    g = res.get("gate") or {}
    out = {}
    for name, d in g.items():
        bs = bool(d.get("beats_shipped_on_signal_by_bar"))
        br = bool(d.get("beats_shipped_on_random"))
        label = ("EXIT EFFECT" if (bs and br) else
                 "SIGNAL-ONLY" if bs else
                 "CONTROL-ONLY" if br else "REJECT")
        out[name] = {
            "label": label, "beats_signal_by_bar": bs, "beats_random": br,
            "signal_gain": d.get("expectancy_gain_vs_shipped_signal"),
            "random_gain": d.get("expectancy_gain_vs_shipped_random"),
            "adopt_eligible": bool(label == "EXIT EFFECT" and d.get("X1_adopt")),
        }
    return out


def clustered_policy_diff(rows_by_policy: dict, name: str, draws: int = BOOT_DRAWS,
                          seed: int = BOOT_SEED) -> dict:
    """Date-block (calendar-month) bootstrap of a policy's expectancy difference vs shipped."""
    base = rows_by_policy.get(EL.BASELINE) or []
    rows = rows_by_policy.get(name) or []
    if not base or not rows:
        return {"ok": False}
    d = OS.date_block_diff(rows, base, draws=draws, seed=seed)
    lo, hi = d.get("ci95") or (None, None)
    return {"ok": True, "diff": d.get("diff"), "ci95_lo": lo, "ci95_hi": hi,
            "excludes_zero": bool(lo is not None and hi is not None and (lo > 0 or hi < 0)),
            "n_blocks": d.get("n_blocks")}


# ============================ O23 — the decomposition ======================================
def _und_close(bars, day) -> Optional[float]:
    """As-traded close at or before `day`. Options maths never uses the adjusted series."""
    if not bars:
        return None
    ds, px = bars["date"], (bars.get("raw_close") or bars["close"])
    d = str(day)[:10]
    out = None
    for i, x in enumerate(ds):
        if x <= d:
            out = px[i]
        else:
            break
    return out


def _ols_r2(xs, ys) -> Optional[dict]:
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx <= 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    if syy <= 0:
        return None
    b = sxy / sxx
    return {"n": n, "slope": b, "intercept": my - b * mx, "r2": (sxy * sxy) / (sxx * syy)}


def decompose_vs_underlying(scored_by_policy: dict, paths_by_key: dict, bars_by_ticker: dict,
                            draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> dict:
    """O23 primary: how much of a policy's P&L difference vs `shipped` is the underlying moving?

    Policies share the IDENTICAL entry and differ only in the exit date, so the difference is
    entirely attributable to the two exit dates -- which is what makes this decomposition clean
    and is why it is stated as a difference rather than as a level.

    Restricted to trades whose exit date DIFFERS from shipped's. Including identical exits would
    pad the sample with (0, 0) pairs and drive R2 toward 1 mechanically; the register fixes this.
    """
    base = {(r["ticker"], str(r["alert_ts"])[:10]): r
            for r in (scored_by_policy.get(EL.BASELINE) or [])}
    per_policy, pooled_x, pooled_y, pooled_rows = {}, [], [], []

    for name, rows in scored_by_policy.items():
        if name == EL.BASELINE:
            continue
        xs, ys, keep = [], [], []
        for r in rows:
            k = (r["ticker"], str(r["alert_ts"])[:10])
            b = base.get(k)
            if b is None:
                continue
            if str(r.get("exit_date") or "") == str(b.get("exit_date") or ""):
                continue
            if r.get("held_days") == b.get("held_days"):
                continue
            bars = bars_by_ticker.get(r["ticker"])
            p = paths_by_key.get(k)
            if not bars or p is None:
                continue
            s0 = _und_close(bars, p["entry_date"])
            s_p = _und_close(bars, _exit_day(r, p))
            s_b = _und_close(bars, _exit_day(b, p))
            if not s0 or not s_p or not s_b:
                continue
            d_opt = (r.get("pnl_pct") or 0) - (b.get("pnl_pct") or 0)
            d_und = (s_p / s0 - 1.0) - (s_b / s0 - 1.0)
            xs.append(d_und)
            ys.append(d_opt)
            keep.append({"alert_ts": r["alert_ts"], "ticker": r["ticker"],
                         "d_und": d_und, "d_opt": d_opt})
        if len(xs) < O23_MIN_DIFFERING:
            per_policy[name] = {"ok": False, "n_differing": len(xs),
                                "reason": "fewer than %d differing-exit trades"
                                          % O23_MIN_DIFFERING}
            continue
        fit = _ols_r2(xs, ys)
        per_policy[name] = {"ok": True, "n_differing": len(xs), **(fit or {})}
        pooled_x.extend(xs)
        pooled_y.extend(ys)
        pooled_rows.extend(keep)

    pooled = _ols_r2(pooled_x, pooled_y)
    boot = _bootstrap_r2(pooled_rows, draws=draws, seed=seed) if pooled_rows else None
    out = {"per_policy": per_policy, "pooled": pooled, "pooled_ci95": boot,
           "n_pairs": len(pooled_rows),
           "restriction": "trades whose policy exit date differs from shipped's"}
    out["verdict"] = o23_verdict(pooled, boot)
    return out


def _exit_day(row, path) -> str:
    ed = row.get("exit_date")
    if ed:
        return str(ed)[:10]
    import datetime as dt
    return (dt.date.fromisoformat(path["entry_date"])
            + dt.timedelta(days=int(row.get("held_days") or 0))).isoformat()


def _bootstrap_r2(rows, draws: int = BOOT_DRAWS, seed: int = BOOT_SEED) -> Optional[dict]:
    """Date-block (calendar-month) bootstrap of the pooled R2 -- the register's clustered CI."""
    import random

    by_block = {}
    for r in rows:
        by_block.setdefault(str(r["alert_ts"])[:7], []).append(r)
    blocks = list(by_block.values())
    if len(blocks) < 3:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(draws):
        xs, ys = [], []
        for _ in range(len(blocks)):
            for r in blocks[rng.randrange(len(blocks))]:
                xs.append(r["d_und"])
                ys.append(r["d_opt"])
        f = _ols_r2(xs, ys)
        if f:
            vals.append(f["r2"])
    if not vals:
        return None
    vals.sort()
    return {"draws": len(vals), "n_blocks": len(blocks),
            "lo": vals[int(0.025 * len(vals))], "hi": vals[min(len(vals) - 1,
                                                               int(0.975 * len(vals)))],
            "median": vals[len(vals) // 2]}


def o23_verdict(pooled, boot) -> dict:
    """The register's rule, applied mechanically. Ambiguous is a NULL."""
    if not pooled or not boot:
        return {"label": "NULL", "why": "no pooled fit"}
    r2, lo, hi = pooled["r2"], boot["lo"], boot["hi"]
    if r2 >= O23_UNDERLYING_R2 and lo >= O23_UNDERLYING_R2:
        lab = "UNDERLYING-DRIVEN"
    elif r2 <= O23_OPTION_R2 and hi <= O23_OPTION_R2:
        lab = "OPTION-DRIVEN"
    else:
        lab = "NULL"
    return {"label": lab, "r2": r2, "ci95_lo": lo, "ci95_hi": hi,
            "bar_underlying": O23_UNDERLYING_R2, "bar_option": O23_OPTION_R2}


# ============================ O23 secondary — Greek attribution ============================
def greek_attribution(scored_by_policy: dict, paths_by_key: dict, bars_by_ticker: dict,
                      chains: FrozenChains, rate: float = 0.03, max_pairs: int = 60000) -> dict:
    """Attribute the option's mark change between the two exit dates to delta / gamma / vega /
    theta, with Greeks evaluated at the interval's start.

    SECONDARY AND CARRIES NO VERDICT. It exists to say WHICH option-specific component matters
    when the primary decomposition says the underlying does not explain the difference.

    Implied vol is solved at exit dates ONLY, not on every day of every path -- an interval
    attribution needs the endpoints and nothing else, and that is what makes this arm affordable.
    """
    from .options_greeks import greeks, implied_vol

    base = {(r["ticker"], str(r["alert_ts"])[:10]): r
            for r in (scored_by_policy.get(EL.BASELINE) or [])}
    acc = {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "theta": 0.0, "residual": 0.0}
    absacc = dict(acc)
    n, skipped = 0, 0
    for name, rows in scored_by_policy.items():
        if name == EL.BASELINE:
            continue
        for r in rows:
            if n >= max_pairs:
                break
            k = (r["ticker"], str(r["alert_ts"])[:10])
            b, p = base.get(k), paths_by_key.get(k)
            if b is None or p is None:
                continue
            d1, d2 = _exit_day(b, p), _exit_day(r, p)
            if d1 == d2:
                continue
            if d1 > d2:
                d1, d2 = d2, d1
            bars = bars_by_ticker.get(r["ticker"])
            v1, v2 = _mark_on(chains, p, d1), _mark_on(chains, p, d2)
            s1, s2 = _und_close(bars, d1), _und_close(bars, d2)
            if not (v1 and v2 and s1 and s2):
                skipped += 1
                continue
            exp = p["expiry"]
            t1 = max(1e-6, _yearfrac(d1, exp))
            t2 = max(1e-6, _yearfrac(d2, exp))
            is_put = not str(p["right"]).upper().startswith("C")
            sig1 = implied_vol(v1, s1, p["strike"], t1, rate, is_put)
            sig2 = implied_vol(v2, s2, p["strike"], t2, rate, is_put)
            if not sig1 or not sig2 or sig1 <= 0 or sig2 <= 0:
                skipped += 1
                continue
            g = greeks(s1, p["strike"], t1, rate, sig1, is_put)
            ds, dsig, dt_ = s2 - s1, sig2 - sig1, -(t2 - t1) * 365.0
            dv = v2 - v1
            c_delta = (g.get("delta") or 0) * ds
            c_gamma = 0.5 * (g.get("gamma") or 0) * ds * ds
            c_vega = (g.get("vega") or 0) * dsig * 100.0
            c_theta = (g.get("theta") or 0) * dt_
            resid = dv - (c_delta + c_gamma + c_vega + c_theta)
            for kk, vv in (("delta", c_delta), ("gamma", c_gamma), ("vega", c_vega),
                           ("theta", c_theta), ("residual", resid)):
                acc[kk] += vv
                absacc[kk] += abs(vv)
            n += 1
    tot = sum(absacc.values()) or 1.0
    return {"n_pairs": n, "n_skipped": skipped, "rate_assumed": rate,
            "mean_contribution": {k: v / n for k, v in acc.items()} if n else {},
            "share_of_absolute_movement": {k: v / tot for k, v in absacc.items()},
            "note": "Greeks at the interval start; vega per 1 vol point; theta per day. "
                    "Shares are of TOTAL ABSOLUTE movement, so they sum to 1 by construction "
                    "and a large share means the term moves the mark, not that it helps."}


def _mark_on(chains: FrozenChains, path, day) -> Optional[float]:
    sub = chains._g.get(chains.key(path["ticker"], path["expiry"], path["strike"], path["right"]))
    if sub is None:
        return None
    hit = sub[sub["_date"] == str(day)[:10]]
    if not len(hit):
        return None
    r = hit.iloc[0]
    try:
        bid, ask = float(r["bid"]), float(r["ask"])
    except (TypeError, ValueError):
        return None
    if not (bid > 0 and ask > 0 and ask >= bid):
        return None
    return 0.5 * (bid + ask)


def _yearfrac(a, b) -> float:
    import datetime as dt
    return (dt.date.fromisoformat(str(b)[:10])
            - dt.date.fromisoformat(str(a)[:10])).days / 365.0


def _is_finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False
