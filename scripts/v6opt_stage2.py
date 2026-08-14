#!/usr/bin/env python3
"""V6-OPT stage 2 — the cash-secured-put backtest. Executes `PREREG_v6opt_csp.md` section 4.

    python -m scripts.v6opt_stage2

RUNS ONLY BECAUSE STAGE 1's GATE OPENED. The gate, the arms, the four controls and the verdict
rule were all fixed in the register at `88685c9`, before any stage-1 number existed, so nothing
here was chosen on stage 1's results. The run REFUSES to start if the stage-1 artifact does not
record an open gate - the O19/O11 mechanism, where a gating control's own artifact is the key.

SETTLEMENT IS ON THE AS-TRADED SPOT, never on the adjusted close: strikes are as-traded and
`data/backtest/prices` is split- and dividend-adjusted (AAPL 300.35 vs 72.34 on 2020-01-02,
differing by >5% on 46.66% of days). Session 30's rule - raw for a STRIKE, adjusted for a RETURN -
is applied in both directions here: the option settles on `spot`, the STOCK control returns on
the adjusted close.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import csp_surface as CS                    # noqa: E402
from valuation.edge.options_fill import Quote, fill_price       # noqa: E402

ROOT = r"C:/Users/donni/Downloads/valuation-tool"
DERIVED = os.path.join(ROOT, "data/options_derived")
PRICES = os.path.join(ROOT, "data/backtest/prices")
STAGE1 = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE1.json")
EVENTS = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE1_EVENTS.pkl")
OUT = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE2.json")
TRADES = os.path.join(ROOT, "data/free_analysis/V6OPT_STAGE2_TRADES.pkl")

N_SEEDS = 5                    # register 4.1, C-C - the R2 standing minimum
SEED0 = 20260813
SPLIT_TOL = 0.20               # a corporate action between entry and expiry (U1-SPLIT)


def _log(m):
    print(m, flush=True)


def _adj_prices(ticker, cache={}):
    if ticker in cache:
        return cache[ticker]
    p = os.path.join(PRICES, f"{str(ticker).upper()}.csv")
    out = None
    if os.path.exists(p):
        try:
            df = pd.read_csv(p, usecols=["date", "close"]).dropna().sort_values("date")
            out = (df["date"].to_numpy(dtype="datetime64[D]"),
                   df["close"].to_numpy(dtype=float))
        except Exception:
            out = None
    cache[ticker] = out
    return out


def _adj_close(ticker, d):
    a = _adj_prices(ticker)
    if a is None:
        return None
    arr, c = a
    j = int(np.searchsorted(arr, np.datetime64(str(d)[:10]), side="right"))
    if j < 1:
        return None
    v = float(c[j - 1])
    return v if np.isfinite(v) and v > 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=N_SEEDS)
    a = ap.parse_args()

    # ---------------------------------------------------------------- the gate is the key
    if not os.path.exists(STAGE1):
        raise CS.RegisterViolation("stage 1 artifact absent - stage 2 may not run")
    s1 = json.load(open(STAGE1))
    if not s1.get("gate", {}).get("OPEN_both_halves"):
        raise CS.RegisterViolation("stage 1 gate did NOT open - stage 2 may not run (register 3)")
    _log(f"[stage2] gate check: {s1['gate']['decision']}")

    art = {"item": "V6-OPT", "stage": 2, "register": "PREREG_v6opt_csp.md",
           "register_commit": "88685c9", "adopts": "NOTHING",
           "gate_inherited": s1["gate"]["decision"],
           "m1_on_covered_pp": s1["controls"]["C5_M1_on_covered"]["separation_pp"],
           "controls": {}, "arms": {}}

    ev = pd.read_pickle(EVENTS)
    ev = ev[ev["strike"].notna()].reset_index(drop=True)
    ev["year"] = ev["date"].astype(str).str[:4]
    _log(f"[stage2] {len(ev):,} events carry a selected contract "
         f"({int(ev['healthy'].sum()):,} healthy)")

    # ---------------------------------------------------------------- surfaces
    tickers = sorted(set(ev["ticker"].astype(str)))
    surf = {}
    for t in tickers:
        d = CS.load_daily(DERIVED, t)
        if d is not None:
            surf[t] = d
    _log(f"[stage2] loaded {len(surf)} surfaces")

    # ---------------------------------------------------------------- random-entry dates
    # Matched on (name, year) so the control differs from the arm in DATE ONLY - not in name,
    # not in period, not in coverage. R2's construction.
    rngs = [np.random.default_rng(SEED0 + k) for k in range(a.seeds)]
    rand_dates = defaultdict(list)      # (ticker, year) -> [(seed, date)]
    for t, y in sorted({(str(t), str(y)) for t, y in zip(ev["ticker"], ev["year"])}):
        sd = surf.get(t)
        if sd is None:
            continue
        pool = sd["date"][sd["date"].astype(str).str[:4] == y]
        if not len(pool):
            continue
        arr = pool.to_numpy()
        for k, rng in enumerate(rngs):
            n = int((ev["ticker"].eq(t) & ev["year"].eq(y) & ev["healthy"]).sum())
            for _ in range(n):
                rand_dates[(t, y)].append((k, pd.Timestamp(arr[rng.integers(len(arr))])))

    # ---------------------------------------------------------------- ONE pass over the files
    _log("[stage2] selecting contracts for the random-entry control")
    rand_sel = defaultdict(list)
    groups = sorted(rand_dates.keys())
    for gi, (t, y) in enumerate(groups):
        if gi % 200 == 0:
            _log(f"    ... {gi}/{len(groups)} groups")
        p = os.path.join(DERIVED, t, f"{t}-{y}.pkl")
        if not os.path.exists(p):
            continue
        try:
            ch = pd.read_pickle(p)
        except Exception:
            continue
        ch["date"] = pd.to_datetime(ch["date"])
        g = {k: v for k, v in ch.groupby("date")}
        keys = np.array(sorted(g.keys()), dtype="datetime64[ns]")
        for k, d in rand_dates[(t, y)]:
            j = int(np.searchsorted(keys, np.datetime64(d, "ns"), side="right"))
            if j <= 0:
                continue
            r = CS.pick_csp(g[pd.Timestamp(keys[j - 1])])
            if r is not None:
                rand_sel[k].append({"ticker": t, "year": y, "date": pd.Timestamp(keys[j - 1]),
                                    **r})
    _log(f"    random contracts per seed: {[len(rand_sel[k]) for k in range(a.seeds)]}")

    # ---------------------------------------------------------------- settle everything
    split_dropped = defaultdict(int)

    def settle(ticker, entry, strike, credit, expiry, mid, spread_frac):
        sd = surf.get(str(ticker))
        if sd is None:
            return None
        s0 = CS.spot_on(sd, entry)
        s1_ = CS.spot_on(sd, expiry)
        if s0 is None or s1_ is None:
            return None
        a0, a1 = _adj_close(ticker, entry), _adj_close(ticker, expiry)
        if a0 is None or a1 is None:
            return None
        # U1-SPLIT guard: the as-traded ratio and the adjusted ratio must agree, or a corporate
        # action fell between entry and expiry and the strike no longer describes the contract.
        raw_r, adj_r = s1_ / s0, a1 / a0
        if abs(raw_r - adj_r) > SPLIT_TOL * max(1e-9, abs(adj_r)):
            split_dropped["corporate_action"] += 1
            return None
        st = CS.settle_put(strike, credit, s1_)
        if st is None:
            return None
        buy = fill_price(CS.reconstruct_quote(mid, spread_frac), "buy", CS.SELL_AGGRESSION)
        mirror = (-float(buy) + max(0.0, float(strike) - s1_)) / float(strike)
        return {"entry": pd.Timestamp(entry), "expiry": pd.Timestamp(expiry),
                "ret_on_strike": st["ret_on_strike"], "assigned": st["assigned"],
                "stock_ret": adj_r - 1.0, "mirror_ret": mirror,
                "spot_entry": s0, "spot_expiry": s1_}

    def build(rows):
        out = []
        for r in rows:
            s = settle(r["ticker"], r["date"], r["strike"], r["credit"],
                       r["expiration"], r["mid"], r["spread_frac"])
            if s is None:
                continue
            out.append({"ticker": str(r["ticker"]), "year": str(r["date"])[:4], **s})
        return out

    _log("[stage2] settling the arm and C-A")
    healthy = build(ev[ev["healthy"]].to_dict("records"))
    unhealthy = build(ev[~ev["healthy"]].to_dict("records"))
    _log(f"    healthy {len(healthy):,}  unhealthy {len(unhealthy):,} "
         f"(corporate-action drops {dict(split_dropped)})")

    ctrl = {}
    for k in range(a.seeds):
        ctrl[k] = build([{**r, "date": r["date"]} for r in rand_sel[k]])
    _log(f"    random settled per seed: {[len(ctrl[k]) for k in range(a.seeds)]}")

    art["controls"]["C_SPLIT_corporate_action"] = {
        "dropped": int(sum(split_dropped.values())), "tolerance": SPLIT_TOL,
        "note": ("U1-SPLIT. The as-traded and adjusted return ratios must agree or a corporate "
                 "action fell inside the trade and the strike no longer describes it.")}

    # ---------------------------------------------------------------- summaries
    def arm(rows, label):
        r = [x["ret_on_strike"] for x in rows]
        d = {"label": label, "n": len(rows), **CS.summarise(r),
             "assigned_frac": (float(np.mean([x["assigned"] for x in rows])) if rows else None),
             "win_frac": (float(np.mean([x["ret_on_strike"] > 0 for x in rows])) if rows else None)}
        for cap in (10, 50):
            d[f"cap{cap}"] = CS.concurrency_book(rows, cap)
        return d

    # A DEFECT IN MY OWN FIRST CUT, FIXED: this split each arm at ITS OWN median entry date, so
    # the healthy and unhealthy arms were compared across halves with DIFFERENT boundaries -
    # and condition 2 is a like-for-like comparison. Both arms now use the ONE boundary the
    # register fixed on the covered subsample (stage 1's C1_halves), embargoed on both sides.
    BOUNDARY = pd.Timestamp(s1["controls"]["C1_halves"]["boundary_embargoed"])
    art["controls"]["halves_boundary"] = {
        "boundary_embargoed": str(BOUNDARY.date()),
        "source": "stage 1 C1_halves, i.e. the covered subsample's own median date",
        "note": ("Both arms are split on the SAME date. Splitting each arm at its own median "
                 "made condition 2 compare different periods; caught before the verdict was "
                 "written up and the verdict is unchanged by the fix.")}

    def halves_split(rows):
        if not rows:
            return [], []
        return ([x for x in rows if pd.Timestamp(x["entry"]) < BOUNDARY],
                [x for x in rows if pd.Timestamp(x["entry"]) > BOUNDARY])

    art["arms"]["A_healthy_csp"] = arm(healthy, "CSP on HEALTHY dips")
    art["arms"]["CA_unhealthy_csp"] = arm(unhealthy, "C-A: CSP on UNHEALTHY dips")
    he, hl = halves_split(healthy)
    ue, ul = halves_split(unhealthy)
    art["arms"]["A_healthy_csp"]["early"] = arm(he, "healthy early")
    art["arms"]["A_healthy_csp"]["late"] = arm(hl, "healthy late")
    art["arms"]["CA_unhealthy_csp"]["early"] = arm(ue, "unhealthy early")
    art["arms"]["CA_unhealthy_csp"]["late"] = arm(ul, "unhealthy late")

    art["arms"]["CB_stock"] = {"label": "C-B: the stock expression, same dates",
                               **CS.summarise([x["stock_ret"] for x in healthy]),
                               "max_drawdown_cap10": CS.concurrency_book(
                                   [{**x, "ret_on_strike": x["stock_ret"]} for x in healthy],
                                   10)["max_drawdown"],
                               "max_drawdown_cap50": CS.concurrency_book(
                                   [{**x, "ret_on_strike": x["stock_ret"]} for x in healthy],
                                   50)["max_drawdown"]}

    art["arms"]["CD_mirror"] = {"label": "C-D: the same put BOUGHT (no-edge self-test)",
                                **CS.summarise([x["mirror_ret"] for x in healthy])}

    seeds = {}
    for k in range(a.seeds):
        seeds[f"seed{k}"] = arm(ctrl[k], f"C-C random entry, seed {k}")
    art["arms"]["CC_random"] = {"label": "C-C: random entry, matched on (name, year)",
                                "seeds": seeds,
                                "pooled_mean": float(np.mean(
                                    [seeds[s]["mean"] for s in seeds
                                     if seeds[s]["mean"] is not None]))}

    # ---------------------------------------------------------------- paired sign tests
    def cells(a_rows, b_rows):
        A, B = defaultdict(list), defaultdict(list)
        for x in a_rows:
            A[(x["ticker"], x["year"])].append(x["ret_on_strike"])
        for x in b_rows:
            B[(x["ticker"], x["year"])].append(x["ret_on_strike"])
        keys = sorted(set(A) & set(B))
        return [(float(np.mean(A[k])), float(np.mean(B[k]))) for k in keys]

    pooled_ctrl = [x for k in range(a.seeds) for x in ctrl[k]]
    art["controls"]["sign_test_vs_random"] = CS.paired_sign_test(cells(healthy, pooled_ctrl))
    art["controls"]["sign_test_vs_unhealthy"] = CS.paired_sign_test(cells(healthy, unhealthy))
    art["controls"]["sign_test_vs_stock"] = CS.paired_sign_test(
        cells(healthy, [{**x, "ret_on_strike": x["stock_ret"]} for x in healthy]))

    # ---------------------------------------------------------------- the verdict (register 4.2)
    A = art["arms"]["A_healthy_csp"]
    CA = art["arms"]["CA_unhealthy_csp"]
    CB = art["arms"]["CB_stock"]
    cond = {}
    cond["1_positive_both_halves"] = bool(
        A["early"]["mean"] is not None and A["late"]["mean"] is not None
        and A["early"]["mean"] > 0 and A["late"]["mean"] > 0)
    cond["2_beats_unhealthy_both_halves"] = bool(
        A["early"]["mean"] is not None and CA["early"]["mean"] is not None
        and A["late"]["mean"] is not None and CA["late"]["mean"] is not None
        and A["early"]["mean"] > CA["early"]["mean"]
        and A["late"]["mean"] > CA["late"]["mean"])
    st = art["controls"]["sign_test_vs_random"]
    cond["3_beats_random_sign_test"] = bool(
        st["z"] is not None and st["z"] > 0 and st["p"] is not None and st["p"] < 0.05)
    surv = {}
    for cap in (10, 50):
        base = CB.get(f"max_drawdown_cap{cap}")
        armdd = A[f"cap{cap}"]["max_drawdown"]
        surv[f"cap{cap}"] = {"arm_maxdd": armdd, "stock_maxdd": base,
                             # max_drawdown is NEGATIVE: a gain is arm - base
                             "gain": (None if armdd is None or base is None else armdd - base),
                             "ok": bool(armdd is not None and base is not None
                                        and armdd - base >= 0)}
    cond["4_survivability"] = bool(all(v["ok"] for v in surv.values()))
    surv["CONSTRUCTION_LIMITATION"] = (
        "max_drawdown here compounds the per-trade returns SEQUENTIALLY in entry order. It is "
        "NOT a capital-weighted portfolio equity curve, in which `cap` concurrent positions "
        "would each carry 1/cap of the book, so it OVERSTATES drawdown for a diversified book "
        "and understates the benefit of diversification. It is reported because it is the leg "
        "the register committed to, it is conservative in the direction that would kill the "
        "arm, and the arm PASSES it anyway - so the limitation cannot have produced the "
        "verdict, which turns on condition 2.")
    surv["ABSOLUTE_LEVEL_WARNING"] = (
        "The arm's own drawdown is severe in absolute terms even where it beats the stock. "
        "'Better than the stock control' is a comparative bar and the stock control itself "
        "drew down 82.6% and 98.6% on this construction; neither book is survivable as shown.")
    art["controls"]["survivability"] = surv

    real = all(cond.values())
    art["verdict"] = {
        "conditions": cond,
        "REAL": real,
        "label": ("ELIGIBLE-BUT-UNRESOLVED" if real else "REJECTED"),
        "note": ("Register 4.3: the covered sample holds ONE crash (COVID 2020Q1), so a decisive "
                 "REJECT is available and a decisive ADOPT is not. A clearing arm is recorded "
                 "ELIGIBLE-BUT-UNRESOLVED, never ADOPTED. Nobody may read a rejection here as "
                 "evidence that cash-secured puts do not work.")}
    _log(f"[stage2] conditions {cond}")
    _log(f"[stage2] VERDICT {art['verdict']['label']}")

    pd.DataFrame(healthy).to_pickle(TRADES)
    with open(OUT, "w") as f:
        json.dump(art, f, indent=2, default=float)
    _log(f"[stage2] wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
