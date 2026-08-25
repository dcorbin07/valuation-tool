"""EVENT-OWNERSHIP census - what universe can a "buy calls spanning earnings" strategy claim?

READ-ONLY. NO REGISTER BAR IS CHOSEN HERE, NO RETURN IS TOUCHED, NO ARM IS SCORED.

This runs BEFORE the register, in its own pass, because the register's bars cannot honestly be
chosen without knowing what the strategy can actually be measured on. `O17C4` measured the effect
on a spanning set capped at **157 names** by the foreign-issuer earnings hole; whether that cap is
the strategy's real universe or an artefact of the book it was drawn from is exactly what this
answers.

FAIL CLOSED, and it is the rule this family exists to protect. `refuse_within` / `owns_the_event`
return **None for UNKNOWN** - no earnings coverage for the name - and the caller MUST DROP those.
29 of the alert book's 186 names are foreign private issuers filing 20-F/6-K with ZERO Sharadar
code-22 coverage. Reading "no date" as "no announcement" fails open on a systematically non-random
tenth of the book. Those names are dropped, counted and listed here, never scored.

PINNED FREEZES ONLY, via the shared resolver, which RAISES rather than falling back to the mutable
store.

    python -m scripts.mb_evown_census --stage a     # name-level funnel, cheap
    python -m scripts.mb_evown_census --stage b     # (name, earnings-date) fillability, expensive
"""
from __future__ import annotations

import argparse
import io
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd

from valuation.edge.chain_store import resolve_chains

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Entry offsets in TRADING days before the announcement. A GRID FOR AVAILABILITY, not a search:
# the census reports what each buys and the register fixes one on availability before any return
# is computed (MA58's precedent, where K=10 was fixed on availability and the K=5 sweep carried no
# verdict). No return is computed anywhere in this file.
K_GRID = (5, 10, 15)


def _data_root() -> str:
    """Probe for the BOOKS, not for a directory that merely exists.

    The worktree carries a partial `data/` with `bulk/prepared` but no `options_universe`, so
    probing for the former picks the wrong root - `DEEPITM-FIN`'s defect, where an EMPTY dir was
    preferred over a populated one. Existence is not population, and the marker has to be the
    thing actually wanted.
    """
    for cand in (os.path.join(_HERE, "data"),
                 os.path.join(_HERE, "..", "..", "..", "data")):
        if os.path.isfile(os.path.join(cand, "options_universe", "state_r2_splitclean.pkl")):
            return os.path.abspath(cand)
    return os.path.abspath(os.path.join(_HERE, "data"))


DATA = _data_root()
OUT_A = os.path.join(DATA, "free_analysis", "MB_EVOWN_CENSUS_A.json")
OUT_B = os.path.join(DATA, "free_analysis", "MB_EVOWN_CENSUS_B.json")
UNIV = os.path.join(DATA, "options_universe")


def _bars_dir() -> str:
    """EXISTENCE IS NOT POPULATION - the worktree's bars dir is empty, the primary's holds 502."""
    for cand in (os.path.join(DATA, "bulk", "prepared", "bars"),
                 os.path.join(_HERE, "..", "..", "..", "data", "bulk", "prepared", "bars")):
        if os.path.isdir(cand) and len(os.listdir(cand)) > 50:
            return os.path.abspath(cand)
    raise RuntimeError("no POPULATED bars cache found; refusing to run on an empty one")


def _log(m):
    print("[EVOWN] %s" % m, flush=True)


def _alert_names():
    p = os.path.join(UNIV, "state_r2_splitclean.pkl")
    with open(p, "rb") as fh:
        d = pickle.load(fh)
    rows = d["rows"] if isinstance(d, dict) else d
    return sorted({r["ticker"] for r in rows})


def _earnings_map(names):
    from valuation.edge import bulk
    ev = bulk.prepare_events(os.path.join(DATA, "bulk", "events.csv"))
    return {t: sorted(str(x)[:10] for x in (bulk.earnings_dates(ev, t) or [])) for t in names}


def stage_a():
    chains, prov = resolve_chains(DATA)
    _log("chain store: %s pinned=%s" % (prov.get("source"), prov.get("pinned")))
    opt = chains          # resolve_chains already returns the `options` root
    freeze_names = sorted(d for d in os.listdir(opt) if os.path.isdir(os.path.join(opt, d)))
    bars = _bars_dir()
    bar_names = {f[:-4].upper() for f in os.listdir(bars) if f.endswith(".pkl")}
    alert = _alert_names()

    _log("freeze tickers %d, bars tickers %d, alert-book names %d"
         % (len(freeze_names), len(bar_names), len(alert)))

    universes = {
        "alert_book_186": alert,
        "freeze_with_bars": sorted(set(freeze_names) & bar_names),
    }
    out = {"item": "MB-EVOWN", "pass": "census-A-name-level",
           "status": "READ-ONLY - no register bar chosen, no return touched",
           "chain_store_source": prov.get("source"), "chain_store_pinned": prov.get("pinned"),
           "chain_store_root": chains, "freeze_generated_utc": prov.get("generated_utc"),
           "freeze_ticker_dirs": len(freeze_names), "bars_tickers": len(bar_names),
           "k_grid_trading_days": list(K_GRID), "universes": {}}

    for label, names in universes.items():
        em = _earnings_map(names)
        zero = sorted(t for t in names if not em.get(t))
        withe = sorted(t for t in names if em.get(t))
        have_chain = [t for t in withe if os.path.isdir(os.path.join(opt, t))]
        have_bars = [t for t in have_chain if t.upper() in bar_names]
        n_events = sum(len(em[t]) for t in have_bars)
        out["universes"][label] = {
            "names": len(names),
            "names_zero_earnings_FAIL_CLOSED": len(zero),
            "zero_earnings_names": zero[:40],
            "names_with_earnings": len(withe),
            "names_with_earnings_and_chain": len(have_chain),
            "names_scoreable": len(have_bars),
            "earnings_events_on_scoreable_names": n_events,
        }
        _log("%-20s names %4d | zero-earnings DROPPED %3d | with chain %4d | scoreable %4d | "
             "events %6d" % (label, len(names), len(zero), len(have_chain), len(have_bars),
                             n_events))

    os.makedirs(os.path.dirname(OUT_A), exist_ok=True)
    with io.open(OUT_A, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)
    _log("wrote %s" % OUT_A)
    return 0


def _chain_dates(opt, tk, year):
    p = os.path.join(opt, tk, "%s-%d.pkl" % (tk, year))
    if not os.path.isfile(p):
        return None
    try:
        return pd.read_pickle(p)
    except Exception:                                                  # noqa: BLE001
        return None


def stage_b(limit_names=0):
    """For each (name, earnings date, K): is there a chain on the entry date, and does the
    ENGINE'S OWN rule produce a fillable in-band contract whose expiry spans the announcement?

    `pick_contract` is IMPORTED, never re-implemented - a second copy of the selection rule would
    be the B7 defect class and would stop this measuring the engine's own menu.
    """
    from valuation.edge.options_backtest import pick_contract
    from valuation.studies.earnings_surface import owns_the_event

    chains, prov = resolve_chains(DATA)
    opt = chains          # resolve_chains already returns the `options` root
    bars_dir = _bars_dir()
    a = json.load(io.open(OUT_A, encoding="utf-8"))
    names = sorted(set(_alert_names()))
    em = _earnings_map(names)
    names = [t for t in names if em.get(t) and os.path.isdir(os.path.join(opt, t))
             and os.path.isfile(os.path.join(bars_dir, "%s.pkl" % t.upper()))]
    if limit_names:
        names = names[:limit_names]
    _log("stage B over %d scoreable alert-book names" % len(names))

    tally = {k: {"events": 0, "entry_date_has_chain": 0, "engine_menu_nonempty": 0,
                 "spans_announcement": 0} for k in K_GRID}
    per_name = {}

    for i, tk in enumerate(names, 1):
        try:
            bars = pd.read_pickle(os.path.join(bars_dir, "%s.pkl" % tk.upper()))
        except Exception:                                              # noqa: BLE001
            continue
        # The prepared bars cache is a dict of parallel LISTS, not a frame.
        # U1-SPLIT: raw_close for anything touching a STRIKE, never the adjusted close.
        if not isinstance(bars, dict) or "raw_close" not in bars:
            continue
        px = {}
        for d0, rc in zip(bars["date"], bars["raw_close"]):
            if rc is None:
                continue
            v = float(rc)
            if np.isfinite(v) and v > 0:
                px[str(d0)[:10]] = v
        sess = sorted(px)
        if not sess:
            continue
        pos = {d: j for j, d in enumerate(sess)}

        by_year = {}
        nm = {k: {"events": 0, "chain": 0, "menu": 0, "spans": 0} for k in K_GRID}
        for ann in em[tk]:
            if not ("2016-01-01" <= ann <= "2025-12-31"):
                continue
            j = pos.get(ann)
            if j is None:                       # announcement not a session in the bar series
                nxt = [d for d in sess if d >= ann]
                if not nxt:
                    continue
                j = pos[nxt[0]]
            for k in K_GRID:
                tally[k]["events"] += 1
                nm[k]["events"] += 1
                if j - k < 0:
                    continue
                entry = sess[j - k]
                yr = int(entry[:4])
                if yr not in by_year:
                    by_year[yr] = _chain_dates(opt, tk, yr)
                ch = by_year[yr]
                if ch is None:
                    continue
                day = ch[ch["date"].astype(str).str[:10] == entry]
                if not len(day):
                    continue
                tally[k]["entry_date_has_chain"] += 1
                nm[k]["chain"] += 1
                u = px.get(entry)
                if u is None or not np.isfinite(u) or u <= 0:
                    continue
                best = pick_contract(day, float(u), entry)
                if best is None:
                    continue
                tally[k]["engine_menu_nonempty"] += 1
                nm[k]["menu"] += 1
                if owns_the_event(entry, str(best["expiration"])[:10], em[tk]) is True:
                    tally[k]["spans_announcement"] += 1
                    nm[k]["spans"] += 1
        per_name[tk] = nm
        if i % 10 == 0:
            _log("  %d/%d names, K=10 events %d chain %d menu %d spans %d"
                 % (i, len(names), tally[10]["events"], tally[10]["entry_date_has_chain"],
                    tally[10]["engine_menu_nonempty"], tally[10]["spans_announcement"]))

    out = {"item": "MB-EVOWN", "pass": "census-B-event-level",
           "status": "READ-ONLY - no register bar chosen, no return touched, no arm scored",
           "chain_store_source": prov.get("source"),
           "chain_store_pinned": prov.get("pinned"),
           "selection_rule": "valuation.edge.options_backtest.pick_contract, IMPORTED - the "
                             "engine's own ~35-delta 45-75 DTE in-band fillable rule",
           "fail_closed": "names with no code-22 earnings coverage are DROPPED, never scored - "
                          "owns_the_event returns None for UNKNOWN",
           "k_grid_trading_days": list(K_GRID),
           "names_scoreable": len(names),
           "tally": tally,
           "per_name_k10": {t: v[10] for t, v in per_name.items()},
           "census_a_universes": a.get("universes"),
           }
    for k in K_GRID:
        t = tally[k]
        t["chain_rate"] = t["entry_date_has_chain"] / max(t["events"], 1)
        t["menu_rate"] = t["engine_menu_nonempty"] / max(t["events"], 1)
        t["spans_rate"] = t["spans_announcement"] / max(t["events"], 1)
    with io.open(OUT_B, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print()
    for k in K_GRID:
        t = tally[k]
        print("K=%-3d events %6d | chain %6d (%.1f%%) | engine menu %6d (%.1f%%) | spans %6d (%.1f%%)"
              % (k, t["events"], t["entry_date_has_chain"], 100 * t["chain_rate"],
                 t["engine_menu_nonempty"], 100 * t["menu_rate"],
                 t["spans_announcement"], 100 * t["spans_rate"]))
    _log("wrote %s" % OUT_B)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="event-ownership coverage census (READ-ONLY)")
    ap.add_argument("--stage", choices=("a", "b"), required=True)
    ap.add_argument("--limit-names", type=int, default=0)
    ns = ap.parse_args(argv)
    return stage_a() if ns.stage == "a" else stage_b(ns.limit_names)


if __name__ == "__main__":
    sys.exit(main())
