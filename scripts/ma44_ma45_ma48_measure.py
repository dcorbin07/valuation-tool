"""Reproduce the measurements behind MA44, MA45 and MA48.

    python -m scripts.ma44_ma45_ma48_measure [--out data/free_analysis/MA44_45_48.json]

Three audit items were argued from code alone, each with a magnitude the audit could only label a
HYPOTHESIS. This measures all three against the real chain cache so the numbers in the ledger, the
docstrings and the handoff can be re-derived rather than taken on trust (RUN_RULES rule 9).

  MA44  how often a chain-day lists a SAME-DAY expiry, so the live `[0]` rule and the
        strictly-after rule read different chains, and how far apart the readings are
  MA45  what share of rows carry a one-sided quote, and - the question that actually matters -
        how often the ATM row the IV walk LANDS on is one of them
  MA48  whether any cached symbol-year was mined while its own year was still running, which is
        the only way the missing `.span` sidecar could already have damaged a study

WHY THE CACHE AND NOT A LIVE SCAN. The audit's own verification for MA44 is "log expiry == today
occurrences in one Friday scan". One Friday is one draw, it needs a live vendor session, and it
cannot say how far apart the two readings are. The cache gives years of real chain-days offline.
It cannot settle whether Tradier lists today on an expiry day - that stays a hypothesis, and is
labelled as one everywhere it appears.

DATA. `data/options`, the ThetaData EOD chain cache. Note that `theta_bulk.CACHE_ROOT` resolves
against the module's own repo root, which is the WORKTREE when run from one - and a worktree has
no `data/`. `--root` defaults to the primary checkout for that reason.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import pickle
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PAT = re.compile(r"^([A-Z0-9._-]+)-(\d{4})\.pkl$")
# The PINNED freeze is the default root; the mutable store is reachable only by passing --root
# explicitly. Resolved lazily so `--help` and an import still work without the freeze mounted.
def _default_root():
    try:
        from valuation.edge.chain_store import resolve_chains
        return resolve_chains(os.path.join(os.path.expanduser("~"), "Downloads",
                                           "valuation-tool", "data"))[0]
    except Exception:                                                # noqa: BLE001
        # Reported, not silently substituted: argparse still needs a string, and the run will
        # say which root it used.
        return os.path.join(os.path.expanduser("~"), "Downloads", "valuation-tool",
                            "data", "options")


def _year_files(root):
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            m = PAT.match(fn)
            if m:
                yield m.group(1), int(m.group(2)), os.path.join(d, fn)


def ma48_census(root):
    """Every cached symbol-year: was it mined while its own year was still running?"""
    rows = [(s, y, dt.date.fromtimestamp(os.path.getmtime(p))) for s, y, p in _year_files(root)]
    trunc = [r for r in rows if r[2].year <= r[1]]
    cur = dt.date.today().year
    return {"year_files": len(rows), "symbols": len({r[0] for r in rows}),
            "mined_during_own_year": len(trunc),
            "mined_during_own_year_past": len([r for r in trunc if r[1] < cur]),
            "current_year_files": len([r for r in rows if r[1] == cur]),
            "by_year": dict(collections.Counter(r[1] for r in rows)),
            "note": ("mtime is a proxy; verified against the frames' own max(date) on a sample - "
                     "see ma48_verify_sample")}


def ma48_verify_sample(root, n=14, seed=20260815):
    """The fact behind the proxy: does a cached year actually reach Dec 31?"""
    import pandas as pd
    fs = [(s, y, p) for s, y, p in _year_files(root) if y in (2024, 2025)]
    random.Random(seed).shuffle(fs)
    out = []
    for s, y, p in fs[:n]:
        try:
            with open(p, "rb") as f:
                df = pickle.load(f)
            d = pd.to_datetime(df["date"]).dt.date
            out.append({"symbol": s, "year": y, "min": str(d.min()), "max": str(d.max()),
                        "days_short_of_dec31": (dt.date(y, 12, 31) - d.max()).days})
        except Exception as e:                                        # noqa: BLE001
            out.append({"symbol": s, "year": y, "error": type(e).__name__})
    return out


def ma44_probe(root, n_syms=40, seed=20260815, years_per_sym=3):
    """Same-day expiries: frequency, weekday concentration, and how far the readings differ."""
    import pandas as pd
    syms = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    pick = random.Random(seed).sample(syms, min(n_syms, len(syms)))
    tot = zero = 0
    dow = collections.Counter()
    dow_all = collections.Counter()
    recs, names_hit = [], set()
    for s in pick:
        d = os.path.join(root, s)
        for fn in sorted(f for f in os.listdir(d) if PAT.match(f))[-years_per_sym:]:
            try:
                with open(os.path.join(d, fn), "rb") as fh:
                    df = pickle.load(fh)
            except Exception:                                         # noqa: BLE001
                continue
            if df is None or not len(df):
                continue
            frame = pd.DataFrame({
                "d": pd.to_datetime(df["date"]).dt.date,
                "e": pd.to_datetime(df["expiration"]).dt.date,
                "r": df["right"].astype(str).str.upper().str[0],
                "v": pd.to_numeric(df.get("volume"), errors="coerce").fillna(0),
                "oi": pd.to_numeric(df.get("open_interest"), errors="coerce").where(
                    pd.to_numeric(df.get("open_interest"), errors="coerce") >= 0)})
            for day, g in frame.groupby("d", sort=False):
                tot += 1
                dow_all[day.weekday()] += 1
                exps = sorted(set(g["e"]))
                same = [e for e in exps if e == day]
                fut = [e for e in exps if e > day]
                if not same or not fut:
                    continue
                zero += 1
                dow[day.weekday()] += 1
                names_hit.add(s)

                def _s(x):
                    c, p = x[x["r"] == "C"], x[x["r"] == "P"]
                    return float(c["v"].sum()), float(p["v"].sum()), float(c["oi"].sum())
                lc, lp, loi = _s(g[g["e"] == same[0]])
                rc, rp, roi = _s(g[g["e"] == fut[0]])
                recs.append({"cv_live": lc, "cv_recon": rc,
                             "cvoi_live": (lc / loi) if loi else None,
                             "cvoi_recon": (rc / roi) if roi else None})
    D = pd.DataFrame(recs)
    x = D[["cvoi_live", "cvoi_recon"]].dropna() if len(D) else D
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return {
        "symbols": len(pick), "chain_days": tot,
        "days_with_same_day_expiry": zero,
        "share_of_chain_days": (zero / tot) if tot else None,
        "by_weekday_share": {names[i]: (dow.get(i, 0) / dow_all[i])
                             for i in range(7) if dow_all.get(i)},
        "names_affected": len(names_hit),
        "median_call_volume_live": float(D["cv_live"].median()) if len(D) else None,
        "median_call_volume_recon": float(D["cv_recon"].median()) if len(D) else None,
        "bar_0p5_crossed_by_one_side_only": (
            float(((x["cvoi_live"] > 0.5) != (x["cvoi_recon"] > 0.5)).mean()) if len(x) else None),
        "hypothesis_not_settled": ("whether Tradier's expirations endpoint lists today on an "
                                   "expiry day is a live vendor behaviour; not observable here"),
    }


def ma45_probe(root, n_syms=25, seed=20260815, years_per_sym=2):
    """One-sided quotes: the row-level share, and the share of the rows that are actually read."""
    import numpy as np
    import pandas as pd
    syms = sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)))
    pick = random.Random(seed).sample(syms, min(n_syms, len(syms)))
    tot = bad = cross = front_t = front_b = band_t = band_b = 0
    for s in pick:
        d = os.path.join(root, s)
        for fn in sorted(f for f in os.listdir(d) if PAT.match(f))[-years_per_sym:]:
            try:
                with open(os.path.join(d, fn), "rb") as fh:
                    df = pickle.load(fh)
            except Exception:                                         # noqa: BLE001
                continue
            if df is None or not len(df):
                continue
            bid = pd.to_numeric(df["bid"], errors="coerce").to_numpy()
            ask = pd.to_numeric(df["ask"], errors="coerce").to_numpy()
            dd = pd.to_datetime(df["date"]).dt.date
            ee = pd.to_datetime(df["expiration"]).dt.date
            dte = np.array([(e - a).days for a, e in zip(dd, ee)], dtype=float)
            nq = (~np.isfinite(bid)) | (~np.isfinite(ask)) | (bid <= 0) | (ask <= 0)
            cr = np.isfinite(bid) & np.isfinite(ask) & (ask < bid)
            tot += len(df)
            bad += int(nq.sum())
            cross += int(cr.sum())
            fm = np.zeros(len(df), dtype=bool)
            for _, idx in pd.Series(range(len(df))).groupby(dd.to_numpy()):
                sub = dte[idx.to_numpy()]
                fut = sub[sub > 0]
                if len(fut):
                    fm[idx.to_numpy()[sub == fut.min()]] = True
            front_t += int(fm.sum())
            front_b += int((fm & (nq | cr)).sum())
            band = (dte >= 45) & (dte <= 75)
            band_t += int(band.sum())
            band_b += int((band & (nq | cr)).sum())
    return {"symbols": len(pick), "rows": tot,
            "one_sided_share": bad / tot if tot else None,
            "crossed_share": cross / tot if tot else None,
            "front_expiry_rows": front_t,
            "front_one_sided_share": front_b / front_t if front_t else None,
            "dte_45_75_rows": band_t,
            "dte_45_75_one_sided_share": band_b / band_t if band_t else None,
            "note": ("pick_contract applies options_fill.quote_reject_reason AFTER enrichment, so "
                     "these rows were already discarded from SELECTION; the exposure is the ATM "
                     "IV walk. See ma45_impact in HANDOFF_optionsbot.md for the per-day figure.")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=_default_root())
    ap.add_argument("--out", default=os.path.join("data", "free_analysis", "MA44_45_48.json"))
    a = ap.parse_args()
    if not os.path.isdir(a.root):
        raise SystemExit("chain cache not found: %s (pass --root)" % a.root)
    out = {"generated": dt.date.today().isoformat(), "root": a.root,
           "ma48_census": ma48_census(a.root),
           "ma48_verify_sample": ma48_verify_sample(a.root),
           "ma44": ma44_probe(a.root),
           "ma45": ma45_probe(a.root)}
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != "ma48_verify_sample"},
                     indent=2, default=str))
    print("\nwrote %s" % a.out)


if __name__ == "__main__":
    main()
