"""EXHAUSTIVE coverage census of `data/options`, run before spending an expiring subscription.

    python -m scripts.options_coverage_census [--out data/free_analysis/OPTIONS_COVERAGE_CENSUS.json]

WHY THIS EXISTS. A four-tier ThetaData Pro harvest was queued on the premise that the holding
periods behind the banked options book were not cached, and that the subscription window
(expires 2026-09-01, and Standard's 8-year window only rolls FORWARD) was the only way to get
them. The premise was never measured exhaustively -- only sampled. This measures it on every
unit, and the answer killed most of the queue.

The five questions, and what they were measured at on 2026-08-17:

  Q1  What fraction of the book's HOLDING-PERIOD days does the cache already hold, per year?
      42,608 of 42,650 trading days = 99.90%, ZERO missing symbol-years. The perishable years
      are the most complete ones: 2016 99.97%, 2017 100.00%, 2018 100.00%.

  Q2  Does it carry ALTERNATIVES -- contracts the book never held -- or only traded ones?
      3,885 of 3,885 entry dates carry a chain, the traded contract is present on 3,885 of
      3,885, and there are 2,713,919 alternative contracts (median 636 per entry date, 8
      expirations, 61 strikes). The existing trade-scope freeze holds ZERO alternatives, so
      audit O21-D2 is unblocked by FREEZING this store, not by pulling anything.

  Q3  Does it reach the optionable panel universe or only the mined alert names?
      906 optionable names; 411 have any 2016-2018 unit and 384 have all three, so 495 have
      none. THIS IS THE ONE GENUINE GAP.

  Q4  How many of the Index's 86 names are covered?
      80 have a cache dir, 45 have a 2025/2026 unit. A real gap, but 2025-26 stays inside
      Standard's rolling window, so it does NOT need the expiring subscription.

  Q5  What would a fingerprinted freeze of the whole store cost?
      5,063 payload units / 26.98 GB / 7,239 sidecars, 1,571 units already carrying .sha256.

MEASUREMENT ONLY. Zero trials, no verdicts. It opens every cached unit read-only and writes
one JSON artifact.

TWO TRAPS IT HANDLES, both of which broke the first attempt:
  * the cache is NOT dtype-uniform -- some units store `date`/`expiration` as object or as
    tz-aware timestamps -- so every date column goes through `_dtcol`;
  * a WEEKDAY is not a TRADING DAY. Coverage measured against weekdays understates itself by
    the holiday count. The session calendar is derived from the cache itself (2,515 sessions,
    2016-01-04..2025-12-31) and coverage is measured against that.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pickle
import statistics
import time

import pandas as pd

from valuation.edge.theta_bulk import cached_dte

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEF_OPT = os.path.join(REPO, "data", "options")
DEF_BOOK = os.path.join(REPO, "data", "options_universe", "state_r2_corrected.pkl")
DEF_PANEL = os.path.join(REPO, "data", "free_analysis", "panel_s22_h504.pkl")
DEF_INDEX = os.path.join(REPO, "data", "valquo_index.json")
DEF_OUT = os.path.join(REPO, "data", "free_analysis", "OPTIONS_COVERAGE_CENSUS.json")


def _dtcol(s: pd.Series) -> pd.Series:
    """Normalise a cached date column. The store is not uniform across units."""
    s = pd.to_datetime(s, errors="coerce")
    try:
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_localize(None)
    except (AttributeError, TypeError):
        pass
    return s.dt.normalize()


def _years_for(sym: str, opt: str) -> set:
    d = os.path.join(opt, sym)
    if not os.path.isdir(d):
        return set()
    out = set()
    for f in os.listdir(d):
        if f.endswith(".pkl") and f.startswith(sym + "-"):
            try:
                out.add(int(f[len(sym) + 1:-4]))
            except ValueError:
                pass
    return out


def census(opt=DEF_OPT, book=DEF_BOOK, panel_p=DEF_PANEL, index_p=DEF_INDEX) -> dict:
    t0 = time.time()
    # `data/` is a junction that exists in the primary checkout and NOT in an agent worktree,
    # so the computed default can point at nothing. A coverage census that silently measures an
    # empty store would report 0% and read as a catastrophic gap. Fail loud instead.
    if not os.path.isdir(opt):
        raise SystemExit(f"[census] no chain store at {opt} -- pass --options "
                         f"(data/ is a junction and is absent from worktrees)")
    st = pickle.load(open(book, "rb"))
    rows = st["rows"]
    alert_names = sorted({str(r["ticker"]).upper() for r in rows})

    need = collections.defaultdict(set)          # (sym, year) -> {iso calendar day}
    by_symyear = collections.defaultdict(list)
    for r in rows:
        sym = str(r["ticker"]).upper()
        d0 = dt.date.fromisoformat(str(r["alert_ts"])[:10])
        for k in range(0, int(r.get("held_days") or 0) + 1):
            d = d0 + dt.timedelta(days=k)
            need[(sym, d.year)].add(str(d))
        by_symyear[(sym, d0.year)].append(r)

    print(f"[census] {len(rows)} alerts, {len(alert_names)} names, {len(need)} symbol-years, "
          f"{sum(len(v) for v in need.values()):,} calendar days needed", flush=True)

    present_days, depth, alt_rows, missing_units = {}, {}, [], []
    units = sorted(need.keys())
    for i, (sym, yr) in enumerate(units, 1):
        p = os.path.join(opt, sym, f"{sym}-{yr}.pkl")
        if not os.path.exists(p):
            missing_units.append(f"{sym}-{yr}")
            continue
        try:
            obj = pickle.load(open(p, "rb"))
        except Exception as e:                                          # noqa: BLE001
            missing_units.append(f"{sym}-{yr}:UNREADABLE:{type(e).__name__}")
            continue
        df = obj["rows"] if isinstance(obj, dict) and "rows" in obj else obj
        if df is None or not len(df):
            present_days[(sym, yr)] = set()
            continue
        day = _dtcol(df["date"])
        daystr = day.dt.strftime("%Y-%m-%d")
        present_days[(sym, yr)] = set(daystr.unique().tolist())
        depth[(sym, yr)] = cached_dte(sym, yr, opt)
        exp = _dtcol(df["expiration"])
        dte = (exp - day).dt.days

        # Q2: alternatives, evaluated on each alert's own ENTRY date
        expstr = exp.dt.strftime("%Y-%m-%d")
        strike_r = df["strike"].astype(float).round(3)
        right1 = df["right"].astype(str).str.upper().str[0]
        for r in by_symyear.get((sym, yr), []):
            d0 = str(r["alert_ts"])[:10]
            m = (daystr == d0).to_numpy()
            if not m.any():
                alt_rows.append({"sym": sym, "date": d0, "n_chain": 0, "traded_present": None})
                continue
            rt = "C" if str(r.get("opt_right", "")).lower().startswith("c") else "P"
            hit = ((expstr[m] == str(r["expiry"])[:10])
                   & (strike_r[m] == round(float(r["strike"]), 3))
                   & (right1[m] == rt))
            alt_rows.append({
                "sym": sym, "date": d0, "n_chain": int(m.sum()),
                "n_exp": int(expstr[m].nunique()), "n_strike": int(strike_r[m].nunique()),
                "traded_present": bool(hit.any()),
                "max_dte": int(dte[m].max()) if m.any() else None,
            })
        if i % 200 == 0:
            print(f"[census] pass1 {i}/{len(units)}  {time.time()-t0:.0f}s", flush=True)

    # A weekday is not a trading day. Derive the session calendar from the cache itself.
    sess = set()
    for s in present_days.values():
        sess |= s
    sessions = sorted(sess)

    per_year = collections.defaultdict(lambda: {"needed": 0, "present": 0, "absent": []})
    for (sym, yr), days in need.items():
        trad = {d for d in days if d in sess}
        got = present_days.get((sym, yr), set())
        y = per_year[yr]
        y["needed"] += len(trad)
        y["present"] += len(trad & got)
        for d in sorted(trad - got):
            if len(y["absent"]) < 50:
                y["absent"].append(f"{sym} {d}")

    q1 = {str(yr): {"trading_days_needed": v["needed"], "present": v["present"],
                    "absent": v["needed"] - v["present"],
                    "pct": round(100.0 * v["present"] / v["needed"], 4) if v["needed"] else None,
                    "absent_examples": v["absent"][:10]}
          for yr, v in sorted(per_year.items())}

    depth_year = collections.defaultdict(collections.Counter)
    for (sym, yr), d in depth.items():
        depth_year[yr][d] += 1

    with_chain = [a for a in alt_rows if a["n_chain"] > 0]
    traded_hit = [a for a in with_chain if a.get("traded_present")]
    q2 = {
        "alerts": len(alt_rows),
        "entry_dates_with_a_chain": len(with_chain),
        "entry_dates_with_no_chain": len(alt_rows) - len(with_chain),
        "traded_contract_present_in_cache": len(traded_hit),
        "median_contracts_on_entry_date": (statistics.median([a["n_chain"] for a in with_chain])
                                           if with_chain else None),
        "mean_contracts_on_entry_date": (
            round(sum(a["n_chain"] for a in with_chain) / len(with_chain), 1)
            if with_chain else None),
        "median_expirations_on_entry_date": (statistics.median([a["n_exp"] for a in with_chain])
                                             if with_chain else None),
        "median_strikes_on_entry_date": (statistics.median([a["n_strike"] for a in with_chain])
                                         if with_chain else None),
        "total_alternative_contracts": sum(a["n_chain"] for a in with_chain) - len(traded_hit),
    }

    cache_dirs = {d for d in os.listdir(opt) if os.path.isdir(os.path.join(opt, d))}
    panel = pd.read_pickle(panel_p)
    panel_names = sorted({str(t) for t in panel["ticker"].unique()})
    optionable = sorted(cache_dirs & set(panel_names))
    cov = collections.Counter()
    for s in optionable:
        cov[len(_years_for(s, opt) & {2016, 2017, 2018})] += 1
    q3 = {
        "panel_names": len(panel_names), "cache_dirs": len(cache_dirs),
        "optionable_intersection": len(optionable),
        "of_those_with_any_2016_2018_unit": sum(
            1 for s in optionable if _years_for(s, opt) & {2016, 2017, 2018}),
        "with_all_three_2016_2018": sum(
            1 for s in optionable if {2016, 2017, 2018} <= _years_for(s, opt)),
        "alert_names": len(alert_names),
        "optionable_beyond_alert_names": len(set(optionable) - set(alert_names)),
        "years_of_2016_2018_held": dict(sorted(cov.items())),
        "with_none_of_2016_2018": cov[0],
    }

    idx = json.load(open(index_p, encoding="utf-8"))
    idx_names = [p["ticker"] for p in idx["positions"]]
    have = [s for s in idx_names if s in cache_dirs]
    recent = [s for s in idx_names if _years_for(s, opt) & {2025, 2026}]
    q4 = {"index_names": len(idx_names), "with_a_cache_dir": len(have),
          "missing": sorted(set(idx_names) - set(have)),
          "with_a_2025_or_2026_unit": len(recent),
          "missing_recent": sorted(set(idx_names) - set(recent))}

    files = []
    for d in sorted(cache_dirs):
        dd = os.path.join(opt, d)
        for f in os.listdir(dd):
            p = os.path.join(dd, f)
            if os.path.isfile(p):
                files.append((os.path.getsize(p), f))
    payload = [n for n, f in files if f.endswith(".pkl")]
    side = [n for n, f in files if not f.endswith(".pkl")]
    have_sha = sum(1 for _, f in files if f.endswith(".sha256"))
    q5 = {"payload_units": len(payload), "payload_bytes": sum(payload),
          "payload_gb": round(sum(payload) / 1e9, 2),
          "sidecar_files": len(side), "sidecar_bytes": sum(side),
          "units_with_existing_sha256": have_sha,
          "units_without_sha256": len(payload) - have_sha}

    return {"generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "elapsed_s": round(time.time() - t0, 1),
            "q1_holding_day_coverage_by_year": q1,
            "q1_missing_units": missing_units,
            "q1_depth_by_year": {str(y): dict(c) for y, c in sorted(depth_year.items())},
            "q2_alternatives": q2, "q3_optionable_universe": q3, "q4_index_names": q4,
            "q5_freeze_cost": q5,
            "session_calendar": {"n": len(sessions),
                                 "first": sessions[0] if sessions else None,
                                 "last": sessions[-1] if sessions else None}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--options", default=DEF_OPT)
    ap.add_argument("--book", default=DEF_BOOK)
    ap.add_argument("--panel", default=DEF_PANEL)
    ap.add_argument("--index", default=DEF_INDEX)
    ap.add_argument("--out", default=DEF_OUT)
    a = ap.parse_args(argv)
    res = census(a.options, a.book, a.panel, a.index)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w", encoding="utf-8"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "q1_missing_units"}, indent=1)[:4000])
    print(f"[census] -> {a.out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
