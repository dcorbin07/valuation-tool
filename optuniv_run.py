"""Roadmap 22b runner — score the scream-buy strategy across the whole cached universe.

Resumable and incremental: every name is banked as it finishes, so a kill at any point leaves a
usable log rather than nothing. Read-only on the miner's `data/options/` cache.

    python optuniv_run.py --data-root <repo>/data [--workers 6] [--analyse-only]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pickle
import shutil
import sys
import time
import warnings
from typing import Optional

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


# ============================ banked-result guard (session-5 closeout, item 2) ==============
# The runner used to write its state, its control and its results straight into
# `data/options_universe/`, overwriting whatever was there. During audit session 5 the
# pre-correction `state.pkl`, both control seeds, `UNIVERSE_RESULTS.json` and
# `AUTOPSY_BROAD_RESULTS.json` had to be copied out BY HAND before the re-run -- otherwise the
# record's own book would have been destroyed and the Part 6 A/B would have been impossible.
# That is a data-loss risk, not untidiness: the artifact destroyed is the thing a later session
# needs in order to check the current one.
MANIFEST = "BANK_MANIFEST.json"
BANKED_DIR = "banked"
GUARDED = ("UNIVERSE_RESULTS.json", "AUTOPSY_BROAD_RESULTS.json",
           "control_rows.pkl", "state.pkl")


def run_key(names, aggression: float, window, smoke: bool) -> dict:
    """What makes two invocations THE SAME RUN. Resuming one of these is the feature; landing a
    different one on top of it is the defect, so the key is exactly the set of things that would
    make the banked trades not belong to this run."""
    import hashlib

    h = hashlib.sha1("\n".join(sorted(str(n) for n in names)).encode()).hexdigest()[:16]
    return {"n_universe": len(names), "universe_sha1": h,
            "aggression": round(float(aggression), 6),
            "entry_window": [str(window[0]), str(window[1])],
            "smoke_test": bool(smoke)}


def _read_manifest(out_dir: str) -> Optional[dict]:
    p = os.path.join(out_dir, MANIFEST)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _occupants(out_dir: str, state_path: str) -> list:
    """Banked artifacts this invocation would write over."""
    found = [n for n in GUARDED if os.path.exists(os.path.join(out_dir, n))]
    if os.path.exists(state_path) and os.path.dirname(os.path.abspath(state_path)) != \
            os.path.abspath(out_dir):
        found.append(state_path)
    return found


def guard_bank(out_dir: str, state_path: str, key: dict, overwrite: bool) -> dict:
    """Refuse to land on a banked result, BEFORE any scoring work happens.

    Three outcomes: `clear` (nothing banked), `resume` (the manifest says this is the same run),
    `refuse` (something else is banked here). `--overwrite` converts a refusal into an ARCHIVE:
    the prior artifacts are MOVED into `banked/<timestamp>/`, never deleted. No path through this
    runner destroys a banked book -- that is the property being defended, and it is stronger than
    merely asking first.
    """
    occ = _occupants(out_dir, state_path)
    if not occ:
        return {"action": "clear", "occupants": [], "archived_to": None}
    man = _read_manifest(out_dir)
    if man and man.get("run_key") == key:
        return {"action": "resume", "occupants": occ, "archived_to": None,
                "banked_key": man.get("run_key")}
    why = ("no BANK_MANIFEST.json -- these artifacts predate the guard, so whether they belong "
           "to this run is UNKNOWABLE, not merely unproven"
           if not man else "the banked run_key differs from this invocation's")
    if not overwrite:
        return {"action": "refuse", "occupants": occ, "reason": why,
                "banked_key": (man or {}).get("run_key"), "this_key": key,
                "archived_to": None}
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    dest = os.path.join(out_dir, BANKED_DIR, stamp)
    os.makedirs(dest, exist_ok=True)
    moved = []
    for n in occ:
        src = n if os.path.isabs(n) or os.sep in n else os.path.join(out_dir, n)
        try:
            shutil.move(src, os.path.join(dest, os.path.basename(src)))
            moved.append(os.path.basename(src))
        except OSError as e:                                             # noqa: BLE001
            return {"action": "refuse", "occupants": occ,
                    "reason": f"could not archive {src}: {e}", "archived_to": dest}
    if man:
        try:
            shutil.copy2(os.path.join(out_dir, MANIFEST), os.path.join(dest, MANIFEST))
        except OSError:
            pass
    return {"action": "archived", "occupants": occ, "archived_to": dest, "moved": moved,
            "reason": why}


def _stamp_chains(out_dir: str, state_path: str, rows) -> Optional[str]:
    """Record the fingerprint of every chain symbol-year this book consumed (audit O16).

    Why it exists: `data/options` is mutable — the miner re-pulls faulted years and `dte_extend`
    deepens them in place — and until O16 nothing recorded which bytes a banked book had
    actually read. The authoritative book was measured at 86.435% reproducible against the
    store it came from, with the drift attributable entirely to re-mined ticker-years. The
    stamp written here makes the next such divergence loud instead of silent.
    """
    try:
        from valuation.edge import options_freeze as FZ
    except Exception:                                                    # noqa: BLE001
        return None
    return FZ.stamp_run(out_dir, os.path.basename(state_path), rows)


def write_manifest(out_dir: str, key: dict, artifacts) -> str:
    p = os.path.join(out_dir, MANIFEST)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"run_key": key, "artifacts": sorted(set(artifacts)),
                   "written": dt.datetime.now().isoformat(timespec="seconds"),
                   "note": "Written by optuniv_run.py. Deleting this file does not free the "
                           "directory -- a missing manifest is treated as UNKNOWN and refused."},
                  f, indent=1)
    return p


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
    ap.add_argument("--out-dir", default=None,
                    help="write artifacts somewhere other than data/options_universe -- the "
                         "clean way to run a second book without touching a banked one")
    ap.add_argument("--overwrite", action="store_true",
                    help="proceed onto a banked result. The prior artifacts are MOVED into "
                         "<out-dir>/banked/<timestamp>/, never deleted.")
    ap.add_argument("--repo-root", default=os.path.dirname(os.path.abspath(__file__)))
    a = ap.parse_args()

    load_env(a.repo_root)
    from valuation.edge import options_universe as U

    root = os.path.abspath(a.data_root)
    out_dir = os.path.abspath(a.out_dir or os.path.join(root, "options_universe"))
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

    # ---- the banked-result guard, BEFORE any scoring. Twenty minutes of compute then a refusal
    # would be worse than useless: it would tempt the next person to pass --overwrite blind.
    key = run_key(names, a.aggression, (U.ENTRY_START, U.ENTRY_END), bool(a.limit))
    g = guard_bank(out_dir, state_path, key, a.overwrite)
    if g["action"] == "refuse":
        print(f"\n[optuniv] REFUSING to write into {out_dir}", flush=True)
        print(f"[optuniv]   banked here: {', '.join(g['occupants'])}", flush=True)
        print(f"[optuniv]   why: {g['reason']}", flush=True)
        if g.get("banked_key"):
            print(f"[optuniv]   banked run_key: {g['banked_key']}", flush=True)
        print(f"[optuniv]   this run_key:   {key}", flush=True)
        print("[optuniv] Either write elsewhere:  --out-dir <new dir>", flush=True)
        print("[optuniv] or archive and proceed:  --overwrite   "
              "(moves the above into banked/<timestamp>/, deletes nothing)", flush=True)
        return 2
    if g["action"] == "archived":
        print(f"[optuniv] archived {len(g['moved'])} banked artifact(s) -> {g['archived_to']}",
              flush=True)
    elif g["action"] == "resume":
        print("[optuniv] same run_key as the banked result — resuming, not overwriting",
              flush=True)
    # Claim the directory NOW, not at the end. A run killed at minute 12 leaves a state.pkl; if
    # the manifest only appeared on success, its own resume would then be refused as UNKNOWN and
    # the guard would have broken the feature it is supposed to protect.
    write_manifest(out_dir, key,
                   [n for n in GUARDED if os.path.exists(os.path.join(out_dir, n))])

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
                   "smoke_test": bool(a.limit),
                   "run_key": key}
    path = U.save(res, out_dir)
    write_manifest(out_dir, key,
                   [n for n in GUARDED if os.path.exists(os.path.join(out_dir, n))])
    _stamp_chains(out_dir, state_path, rows)
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
