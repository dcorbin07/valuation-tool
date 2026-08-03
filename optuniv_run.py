"""Roadmap 22b runner — score the scream-buy strategy across the whole cached universe.

Resumable and incremental: every name is banked as it finishes, so a kill at any point leaves a
usable log rather than nothing. Read-only on the miner's `data/options/` cache.

    python optuniv_run.py --data-root <repo>/data [--workers 6] [--analyse-only]
"""
from __future__ import annotations

import argparse
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
    _G["root"] = data_root
    _G["prov"] = ThetaBulk(root=os.path.join(data_root, "options"), max_years_in_memory=3)
    _G["bars_dir"] = os.path.join(data_root, "bulk", "prepared", "bars")
    _G["caps"] = U.load_caps(data_root)
    _G["aggression"] = aggression


def _score(ticker: str):
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_universe as U
    t0 = time.time()
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "rows": [], "n_cand": 0, "n_alert": 0,
                "rejects": {"no_bars": 1}, "seconds": time.time() - t0}
    out = U.run_name(_G["prov"], ticker, bars, caps=_G["caps"],
                     aggression=_G["aggression"])
    out["seconds"] = time.time() - t0
    return out


def _control(arg):
    """One name's random-entry control book."""
    from valuation.edge import options_backtest as OB
    from valuation.edge import options_universe as U
    ticker, trades, draws, seed = arg
    bars = OB.load_bars(ticker, cache_dir=_G["bars_dir"])
    if not bars:
        return {"ticker": ticker, "rows": []}
    rows = U.random_entry_control(_G["prov"], ticker, bars, trades, draws=draws, seed=seed,
                                 aggression=_G["aggression"], caps=_G["caps"])
    return {"ticker": ticker, "rows": rows}


def fetch_bars(names, bars_dir, workers=8):
    """Warm the Sharadar bar cache in the parent so the scoring workers never hit the network."""
    from concurrent.futures import ThreadPoolExecutor

    from valuation.edge import options_backtest as OB
    missing = [t for t in names if not os.path.exists(os.path.join(bars_dir, f"{t}.pkl"))]
    if not missing:
        return {"fetched": 0, "failed": []}
    print(f"[optuniv] fetching bars for {len(missing)} names ...", flush=True)
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for t, got in zip(missing, ex.map(lambda x: OB.load_bars(x, cache_dir=bars_dir),
                                          missing)):
            if not got:
                failed.append(t)
    return {"fetched": len(missing) - len(failed), "failed": failed}


def load_env(repo_root: str):
    """Bars come from Sharadar and need the key. Never printed, never written back."""
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
    ap.add_argument("--state", default=None)
    ap.add_argument("--analyse-only", action="store_true")
    ap.add_argument("--autopsy", action="store_true",
                    help="re-run the #23 entry-feature gate, unchanged, on the broad log")
    ap.add_argument("--control", action="store_true",
                    help="random-entry control: same name, same year, random day")
    ap.add_argument("--control-draws", type=int, default=2)
    ap.add_argument("--refresh-control", action="store_true")
    ap.add_argument("--universe-from", default=None,
                    help="pin the name list to an earlier run's state.pkl, so a second pass "
                         "varies one thing and not two")
    ap.add_argument("--limit", type=int, default=0, help="smoke test only; label it as one")
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    load_env(a.repo_root)
    from valuation.edge import options_universe as U

    root = os.path.abspath(a.data_root)
    out_dir = os.path.join(root, "options_universe")
    os.makedirs(out_dir, exist_ok=True)
    state_path = a.state or os.path.join(out_dir, "state.pkl")

    sel = U.universe_selection_report(root)
    if not sel.get("ok"):
        print(f"[optuniv] {sel.get('reason')}")
        return 1
    names = sel["universe"]
    if a.universe_from:
        # The miner keeps adding names, so a later run would silently score a DIFFERENT
        # universe. Pinning to an earlier run's frozen list is what makes a second pass (a
        # different aggression, say) a comparison of one variable instead of two.
        with open(a.universe_from, "rb") as f:
            names = list((pickle.load(f)["selection"])["universe"])
        print(f"[optuniv] universe PINNED to {len(names)} names from {a.universe_from}",
              flush=True)
        sel = dict(sel, universe=names, n_universe=len(names),
                   pinned_from=a.universe_from)
    if a.limit:
        names = names[:a.limit]
        print(f"[optuniv] SMOKE TEST: {a.limit} names only — not a verdict", flush=True)
    print(f"[optuniv] universe {len(names)} complete names "
          f"({sel['n_skipped']} skipped, {sel['n_skipped_thin']} of them as thin)", flush=True)

    state = {"rows": [], "done": [], "meta": {}, "selection": sel}
    if os.path.exists(state_path):
        try:
            with open(state_path, "rb") as f:
                prev = pickle.load(f)
            if isinstance(prev, dict) and "done" in prev:
                state = prev
                print(f"[optuniv] resumed: {len(state['done'])} names, "
                      f"{len(state['rows'])} trades", flush=True)
        except (OSError, pickle.UnpicklingError):
            pass

    if not a.analyse_only:
        todo = [t for t in names if t not in set(state["done"])]
        fetch_bars(todo, os.path.join(root, "bulk", "prepared", "bars"))

        def bank():
            tmp = state_path + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(state, f, protocol=5)
            os.replace(tmp, state_path)

        t_all = time.time()
        if a.workers > 1:
            from multiprocessing import Pool
            with Pool(a.workers, initializer=_init,
                      initargs=(root, a.aggression)) as pool:
                for i, res in enumerate(pool.imap_unordered(_score, todo), 1):
                    _absorb(state, res)
                    if i % 5 == 0 or i == len(todo):
                        bank()
                        _progress(state, i, len(todo), t_all)
        else:
            _init(root, a.aggression)
            for i, t in enumerate(todo, 1):
                _absorb(state, _score(t))
                bank()
                _progress(state, i, len(todo), t_all)
        bank()

    rows = state["rows"]
    print(f"\n[optuniv] {len(state['done'])} names, {len(rows)} trades", flush=True)
    if not rows:
        print("[optuniv] no trades — nothing to analyse")
        return 1
    if a.control:
        ctrl_path = os.path.join(out_dir, "control_rows.pkl")
        if os.path.exists(ctrl_path) and not a.refresh_control:
            with open(ctrl_path, "rb") as f:
                ctrl = pickle.load(f)
            print(f"[optuniv] reusing {len(ctrl)} control trades", flush=True)
        else:
            by_t = {}
            for r in rows:
                by_t.setdefault(r["ticker"], []).append(r)
            jobs = [(t, rs, a.control_draws, 0) for t, rs in sorted(by_t.items())]
            print(f"[optuniv] random-entry control over {len(jobs)} names "
                  f"({a.control_draws} draws per real trade) ...", flush=True)
            ctrl, t0 = [], time.time()
            from multiprocessing import Pool
            with Pool(a.workers, initializer=_init, initargs=(root, a.aggression)) as pool:
                for i, res in enumerate(pool.imap_unordered(_control, jobs), 1):
                    ctrl.extend(res["rows"])
                    if i % 25 == 0 or i == len(jobs):
                        print(f"[optuniv] control {i}/{len(jobs)} | {len(ctrl)} trades | "
                              f"{(time.time()-t0)/60:.1f}m", flush=True)
            with open(ctrl_path, "wb") as f:
                pickle.dump(ctrl, f, protocol=5)
        state["control"] = ctrl

    if a.autopsy:
        from valuation.edge import options_autopsy as A
        print("[optuniv] re-running the trade autopsy gate on the broad log ...", flush=True)
        ares = A.run(root, seed=0, trades=rows)
        # NOT A.save(): that writes data/options/AUTOPSY_RESULTS.json, which is the miner's
        # directory and holds the 55-name result. This run does not overwrite either.
        U.save(ares, out_dir, name="AUTOPSY_BROAD_RESULTS.json")
        print(f"[optuniv] autopsy: {ares['n_features_tested']} features, "
              f"{ares['n_hypotheses']} hypotheses, survivors={ares['survivors']}", flush=True)

    res = U.analyse(rows, meta=state.get("meta"), data_root=root)
    res["selection"] = state["selection"]
    if state.get("control"):
        res["random_entry_control"] = U.control_comparison(rows, state["control"])
        res["random_entry_control"]["n_control_trades"] = len(state["control"])
    res["meta"] = {"n_names": len(state["done"]), "n_trades": len(rows),
                   "aggression": a.aggression,
                   "window": [U.ENTRY_START, U.ENTRY_END],
                   "smoke_test": bool(a.limit)}
    path = U.save(res, out_dir)
    _print_headline(res)
    print(f"\nwritten: {path}", flush=True)
    return 0


def _absorb(state, res):
    state["rows"].extend(res.get("rows") or [])
    state["done"].append(res["ticker"])
    state["meta"][res["ticker"]] = {k: res.get(k) for k in
                                    ("n_cand", "n_alert", "rejects", "seconds")}
    state["meta"][res["ticker"]]["n_trades"] = len(res.get("rows") or [])


def _progress(state, i, n, t0):
    from valuation.edge.options_tracker import _stats
    s = _stats(state["rows"])
    print(f"[optuniv] {i}/{n} names | {len(state['rows'])} trades | "
          f"exp={s['expectancy_pct']} pf={s['profit_factor']} | "
          f"{(time.time()-t0)/60:.1f}m", flush=True)


def _print_headline(res):
    o = res["overall"]
    v = res["verdict"]
    print("\n================ BROAD-UNIVERSE HEADLINE (aggression 1.0) ================")
    print(f"  n={o['n']}  expectancy={o['expectancy_pct']:.4f}  pf={o['profit_factor']}  "
          f"hit={o['hit_rate']:.3f}")
    print(f"  P(>=+100%)={o['p_tail_win']:.4f}  P(total loss)={o['p_total_loss']:.4f}  "
          f"P(stop)={o['p_stop_out']:.4f}")
    h = res["held_out"]
    print(f"  early exp={h['early'].get('expectancy_pct')}  "
          f"late exp={h['late'].get('expectancy_pct')}  both_positive={h['both_positive']}")
    print("\n---- by point-in-time cap tier ----")
    for t, d in res["tiers"].items():
        print(f"  {t:>6}  n={d['n']:>5}  names={d['n_names']:>3}  "
              f"exp={d['expectancy_pct']:+.4f}  pf={d['profit_factor']}  "
              f"P(tail)={d['p_tail_win']:.4f}  spread={d['median_entry_spread_pct']}")
    print("\n---- 54 baseline names vs 133 new names, SAME window, SAME rules ----")
    for lbl, key in (("baseline", "baseline_55_names"), ("new", "new_names_only")):
        d = res.get(key) or {}
        s = d.get("stats") or {}
        if s.get("n"):
            print(f"  {lbl:>8}  names={d['n_names']:>3}  n={s['n']:>5}  "
                  f"exp={s['expectancy_pct']:+.4f}  pf={s['profit_factor']}  "
                  f"P(tail)={s['p_tail_win']:.4f}  tail_hhi={d['concentration']['tail_hhi']}")
    ts = (res.get("new_names_only") or {}).get("term_slope_out_of_sample") or {}
    if ts.get("ok"):
        print(f"  term_slope OUT OF SAMPLE on new names: kept {ts['n_kept']}/{ts['n_all']} "
              f"({ts['retained']:.1%})  {ts['exp_all']:+.4f} -> {ts['exp_filtered']:+.4f}  "
              f"gain {ts['gain']:+.4f}  passes_B2={ts['passes_B2']}")
    rc = res.get("random_entry_control")
    if rc:
        print("\n---- random-entry control (same name, same year, random day) ----")
        for k in ("overall",) + tuple(t for t in ("mega", "large", "mid", "small") if t in rc):
            d = rc[k]
            print(f"  {k:>8}  real n={d['real']['n']:>5} exp={d['real']['expectancy_pct']:+.4f}"
                  f"   control n={d['control']['n']:>5} exp={d['control']['expectancy_pct']:+.4f}"
                  f"   diff={d['expectancy_diff']:+.4f} ci={[round(x,4) for x in d['ci95']]}"
                  f" beats={d['beats_control']}")
    print("\n---- verdict ----")
    for k, val in v.items():
        if not k.endswith("_detail"):
            print(f"  {k}: {val}")


if __name__ == "__main__":
    sys.exit(main())
