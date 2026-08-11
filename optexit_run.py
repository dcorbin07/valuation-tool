"""OPTIONS_DEEP_RESEARCH thread #1 runner — capture contract paths once, score 21 exit policies.

    python optexit_run.py --data-root <repo>/data --collect [--workers 6]
    python optexit_run.py --data-root <repo>/data            # analyse the banked paths

Resumable and banked per name. Read-only on the miner's `data/options/`; writes only to
`data/options_exitlab/`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import pickle
import sys
import time
import warnings

warnings.filterwarnings("ignore")

_G = {}


def _init(data_root: str, aggression: float):
    from valuation.edge import options_universe as U
    from valuation.edge.theta_bulk import ThetaBulk
    _G["prov"] = ThetaBulk(root=os.path.join(data_root, "options"), max_years_in_memory=3)
    _G["bars_dir"] = os.path.join(data_root, "bulk", "prepared", "bars")
    _G["caps"] = U.load_caps(data_root)
    _G["aggression"] = aggression


def collect_name(ticker: str) -> dict:
    """One name: the alert list under the SHIPPED occupancy rule, the signal-entry contract paths,
    the random-entry contract paths, and the production simulator's own result for each signal
    entry so the replay check has something independent to compare against."""
    from valuation.intraday.signals import evaluate as sig_evaluate
    from valuation.intraday.technical import technical_signals
    from valuation.saas.notify import _BULL

    from valuation.edge import options_backtest as OB
    from valuation.edge import options_exitlab as EL
    from valuation.edge import options_universe as U

    t0 = time.time()
    prov, caps, agg = _G["prov"], _G["caps"], _G["aggression"]
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "signal": [], "random": [], "shipped_rows": [],
                "n_alert": 0, "rejects": {"no_bars": 1}, "seconds": time.time() - t0}

    paths, shipped_rows, alerts, rejects = [], [], [], {}
    open_until = None
    for d in bars["date"]:
        if not (EL.ENTRY_START <= d <= EL.ENTRY_END):
            continue
        if open_until and d <= open_until:
            continue
        w = OB.bars_asof(bars, d)
        if not w:
            continue
        ts = technical_signals(w).get("score")
        if ts is None or ts < OB.PREFILTER_TECH:
            continue
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(ticker, day)
        if chain is None or len(chain) == 0:
            rejects["no_chain"] = rejects.get("no_chain", 0) + 1
            continue
        und = OB.spot_asof(w)      # AUDIT B1 — as-traded
        summ = OB.chain_summary(chain, und, day)
        ev = sig_evaluate(w, summ, horizon=OB.HORIZON)
        sc, labels = ev.get("score"), ev.get("labels") or []
        if sc is None or sc < OB.ALERT_MIN_SCORE:
            continue
        if not any(any(bl in l for bl in _BULL) for l in labels):
            continue
        alerts.append(d)
        row = OB.pick_contract(chain, und, day, right="C")
        if row is None:
            rejects["no_contract_in_band"] = rejects.get("no_contract_in_band", 0) + 1
            continue
        # The PRODUCTION simulator, unchanged — this is what the replay check must reproduce,
        # and what sets occupancy so the alert list matches every earlier study.
        tr = OB.simulate_trade(prov, ticker, row, day, bars, aggression=agg)
        if not tr or not tr.get("ok"):
            why = (tr or {}).get("reason", "sim_failed")
            rejects[why] = rejects.get(why, 0) + 1
            continue
        path = EL.capture_path(prov, ticker, row, day, bars)
        if path is None:
            rejects["no_path"] = rejects.get("no_path", 0) + 1
            continue
        mc = U.cap_at(caps, ticker, d)
        path.update({"alert_date": d, "cap_tier": U.tier_of(mc), "marketcap_musd": mc,
                     "entry_spread_pct": tr.get("entry_spread_pct"), "score": sc})
        paths.append(path)
        shipped_rows.append({"ticker": ticker, "entry_date": d, "alert_ts": d,
                             "pnl_pct": tr.get("return_pct"),
                             "exit_reason": tr.get("exit_reason"),
                             "held_days": tr.get("held_days")})
        open_until = tr.get("exit_date")

    # Random entries: the 22b/22c placebo, same name, same calendar year, random day. The KEY
    # TEST needs paths for these, not just outcomes.
    import random
    rnd = random.Random(f"exit:{ticker}")
    by_year = {}
    for d in bars["date"]:
        if EL.ENTRY_START <= d <= EL.ENTRY_END:
            by_year.setdefault(d[:4], []).append(d)
    rpaths = []
    for a in alerts:
        pool = by_year.get(a[:4]) or []
        if len(pool) < 20:
            continue
        for _ in range(2):
            d = pool[rnd.randrange(len(pool))]
            w = OB.bars_asof(bars, d)
            if not w:
                continue
            day = dt.date.fromisoformat(d)
            chain = prov.chain_on(ticker, day)
            if chain is None or len(chain) == 0:
                continue
            row = OB.pick_contract(chain, OB.spot_asof(w), day, right="C")  # AUDIT B1
            if row is None:
                continue
            p = EL.capture_path(prov, ticker, row, day, bars)
            if p is None:
                continue
            mc = U.cap_at(caps, ticker, d)
            p.update({"alert_date": d, "cap_tier": U.tier_of(mc), "marketcap_musd": mc})
            rpaths.append(p)

    return {"ticker": ticker, "signal": paths, "random": rpaths,
            "shipped_rows": shipped_rows, "n_alert": len(alerts), "rejects": rejects,
            "seconds": time.time() - t0}


def load_env(repo_root: str):
    path = os.path.join(repo_root, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--aggression", type=float, default=1.0)
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--state", default=None)
    ap.add_argument("--limit", type=int, default=0, help="smoke test only; label it as one")
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    load_env(a.repo_root)
    from valuation.edge import options_exitlab as EL
    from valuation.edge import options_universe as U

    root = os.path.abspath(a.data_root)
    out_dir = os.path.join(root, "options_exitlab")
    os.makedirs(out_dir, exist_ok=True)
    state_path = a.state or os.path.join(out_dir, "paths.pkl")

    sel = U.universe_selection_report(root)
    if not sel.get("ok"):
        print(f"[exitlab] {sel.get('reason')}")
        return 1
    names = sel["universe"]
    if a.limit:
        names = names[:a.limit]
        print(f"[exitlab] SMOKE TEST: {a.limit} names only — not a verdict", flush=True)
    print(f"[exitlab] universe {len(names)} complete names "
          f"({sel['n_skipped']} skipped, {sel['n_skipped_thin']} of them as thin)", flush=True)

    state = {"signal": [], "random": [], "shipped_rows": [], "done": [], "meta": {},
             "selection": sel}
    if os.path.exists(state_path):
        try:
            with open(state_path, "rb") as f:
                prev = pickle.load(f)
            if isinstance(prev, dict) and "done" in prev:
                state = prev
                print(f"[exitlab] resumed: {len(state['done'])} names, "
                      f"{len(state['signal'])} signal paths", flush=True)
        except (OSError, pickle.UnpicklingError):
            pass

    if a.collect:
        todo = [t for t in names if t not in set(state["done"])]
        bars_dir = os.path.join(root, "bulk", "prepared", "bars")
        missing = [t for t in todo if not os.path.exists(os.path.join(bars_dir, f"{t}.pkl"))]
        if missing:
            print(f"[exitlab] fetching bars for {len(missing)} names ...", flush=True)
            from concurrent.futures import ThreadPoolExecutor

            from valuation.edge import options_backtest as OB
            with ThreadPoolExecutor(max_workers=8) as ex:
                list(ex.map(lambda x: OB.load_bars(x, cache_dir=bars_dir), missing))

        def bank():
            tmp = state_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(state, f, protocol=5)
            os.replace(tmp, state_path)

        t0 = time.time()
        from multiprocessing import Pool
        with Pool(a.workers, initializer=_init, initargs=(root, a.aggression)) as pool:
            for i, res in enumerate(pool.imap_unordered(collect_name, todo), 1):
                state["signal"].extend(res["signal"])
                state["random"].extend(res["random"])
                state["shipped_rows"].extend(res["shipped_rows"])
                state["done"].append(res["ticker"])
                state["meta"][res["ticker"]] = {k: res.get(k) for k in
                                                ("n_alert", "rejects", "seconds")}
                if i % 5 == 0 or i == len(todo):
                    bank()
                    print(f"[exitlab] {i}/{len(todo)} names | {len(state['signal'])} signal "
                          f"paths | {len(state['random'])} random paths | "
                          f"{(time.time()-t0)/60:.1f}m", flush=True)
        bank()

    if not state["signal"]:
        print("[exitlab] no paths — run --collect first")
        return 1

    print(f"\n[exitlab] {len(state['done'])} names | signal {len(state['signal'])} | "
          f"random {len(state['random'])} paths", flush=True)
    res = EL.analyse({"signal": state["signal"], "random": state["random"]},
                     shipped_rows=state["shipped_rows"])
    res["selection"] = {k: state["selection"].get(k) for k in
                        ("n_evaluated", "n_universe", "n_skipped", "n_skipped_thin")}
    res["meta"] = {"n_names": len(state["done"]), "aggression": a.aggression,
                   "smoke_test": bool(a.limit)}
    path = EL.save(res, out_dir)
    # audit O16 follow-on: pin the chain bytes this book was scored against. Descriptive here;
    # blocking only on a replay (valuation/edge/options_freeze.py).
    try:
        from valuation.edge import options_freeze as FZ
        FZ.stamp_run(out_dir, os.path.basename(state_path),
                     {"signal": state["signal"], "shipped": state["shipped_rows"]})
    except Exception as e:                                               # noqa: BLE001
        print(f"[exitlab] WARNING: chain stamp failed ({type(e).__name__}: {e})", flush=True)
    _print(res)
    print(f"\nwritten: {path}", flush=True)
    return 0


def _print(res):
    from valuation.edge import options_exitlab as EL

    rc = res.get("replay_check") or {}
    print("\n================ THREAD #1 — EXIT OPTIMIZATION (aggression 1.0) ================")
    print(f"  replay check vs the production simulator: ok={rc.get('ok')} "
          f"shared={rc.get('n_shared')} mismatched={rc.get('n_mismatched')}")
    for es in ("signal", "random"):
        cmp_ = res.get(es) or {}
        if not cmp_:
            continue
        print(f"\n---- {es.upper()} entries (n={res['n_entries'].get(es)}) ----")
        print(f"  {'policy':>13} {'n':>5} {'exp':>9} {'pf':>6} {'hit':>6} {'tail':>6} "
              f"{'held':>6} {'exp/day':>9} {'vs shipped':>11} {'halves':>7}")
        for name in EL.POLICY_NAMES:
            d = cmp_.get(name)
            if not d:
                continue
            s = d["stats"]
            vs = (d.get("vs_shipped") or {}).get("expectancy_diff")
            print(f"  {name:>13} {s['n']:>5} {s['expectancy_pct']:>+9.4f} "
                  f"{s['profit_factor']:>6.3f} {s['hit_rate']:>6.3f} "
                  f"{s['p_tail_win']:>6.3f} {(s['mean_held_days'] or 0):>6.1f} "
                  f"{(s['expectancy_per_day_held'] or 0):>+9.5f} "
                  f"{('' if vs is None else f'{vs:+.4f}'):>11} "
                  f"{str(d['held_out']['both_positive']):>7}")
    print("\n---- PBO (CSCV over the policy grid) ----")
    for k in ("pbo_signal", "pbo_random"):
        d = res.get(k) or {}
        if d.get("ok"):
            print(f"  {k}: {d['pbo']:.3f} over {d['n_splits']} splits, "
                  f"{d['n_policies']} policies, passes={d['passes']}")
        else:
            print(f"  {k}: {d.get('reason')}")
    print("\n---- X4: choose on one half, measure on the other ----")
    for k in ("holdout_signal", "holdout_random"):
        h = res.get(k) or {}
        for d in ("decide_early", "decide_late"):
            v = h.get(d) or {}
            if v.get("ok"):
                print(f"  {k}/{d}: chose {v['chosen_policy']} "
                      f"(+{v['gain_on_decide_half']:.4f}) -> {v['measure_half']} "
                      f"{(v.get('gain_on_measure_half') or 0):+.4f}")
        print(f"  {k}: survives both directions = {h.get('survives_both_directions')}")
    print("\n---- gate ----")
    for n, d in (res.get("gate") or {}).items():
        if d.get("X1_adopt") or d.get("X2_signal_only"):
            print(f"  {n}: adopt={d['X1_adopt']} signal_only={d['X2_signal_only']}")
    print("\n---- verdict ----")
    for k, v in res["verdict"].items():
        if k != "note":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    sys.exit(main())
