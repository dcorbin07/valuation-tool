# -*- coding: utf-8 -*-
"""`STAGE1-BATCH1` — the scoring pass. Build quadrant only; refuses without the kill artifacts.

Three arms survived their free kills: **A3** (information discreteness), **A7** (net issuance)
and **A11** (52-week-high proximity). A11 additionally carries a **required second reading**
residualised on `momentum` alone, pre-committed in the register because its ρ against the
momentum theme is already measured at 0.7596.

**A3's signal is built here**, from the panel's own daily price export:
`ID = sign(PRET) × (%neg_days − %pos_days)` over the 12-month formation window, entered as its
own standardised column and **NOT as an interaction** — the register's choice, with `S7`'s four
rejected interactions behind it.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import scripts.stage1_kills as K                                            # noqa: E402
import scripts.stage1_score as S                                           # noqa: E402
from scripts.index_best import _data_root, data_candidates                  # noqa: E402
from scripts.sector_neutral_rerun import DEPLOYED                           # noqa: E402


def build_a3(data, b):
    """Information discreteness over the trailing 12 months, from the daily price export."""
    pdir = os.path.join(data, "full2009", "backtest", "prices")
    want = sorted(b["ticker"].unique())
    series = {}
    t0 = time.time()
    for i, t in enumerate(want):
        p = os.path.join(pdir, "%s.csv" % t)
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        df = df.dropna().sort_values("date")
        if len(df) < 30:
            continue
        series[t] = (df["date"].astype(str).values,
                     pd.to_numeric(df["close"], errors="coerce").values)
        if i % 800 == 0 and i:
            print("    a3 build %d/%d, %.0fs" % (i, len(want), time.time() - t0), flush=True)
    rows = []
    for d in sorted(b["date"].unique()):
        hi = str(d)[:10]
        lo = str(pd.Timestamp(d) - pd.Timedelta(days=365))[:10]
        g = b[b["date"] == d]
        for t in g["ticker"]:
            s = series.get(t)
            if s is None:
                continue
            dd, cc = s
            m = (dd > lo) & (dd <= hi)
            c = cc[m]
            if c.size < S.MIN_NAMES or np.isnan(c).any():
                continue
            r = np.diff(c) / c[:-1]
            if r.size < 50:
                continue
            pret = float(c[-1] / c[0] - 1.0)
            pos = float((r > 0).mean())
            neg = float((r < 0).mean())
            sgn = 1.0 if pret > 0 else (-1.0 if pret < 0 else 0.0)
            rows.append((str(d)[:10], t, sgn * (neg - pos)))
    return pd.DataFrame(rows, columns=["date", "ticker", "a3_id"])


#: §0's both-halves rule needs halves. `MA58` measured that complete-case residualisation on the
#: seven weighted incumbents silently restricts the panel, because `institutional` is thin and
#: starts late -- and on THIS quadrant it is worse than it was there. Measured, not assumed.
#: the floor now lives in `stage1_score` so the verdict rule and its floor are
#: ONE definition and can be exercised together (`B7`).
MIN_HALF_DATES = S.MIN_HALF_DATES


def template_restriction(frame, themes, col):
    """What the seven-theme complete-case residualisation costs, per date."""
    rows, first_ok = [], None
    for d in sorted(frame["date"].unique()):
        g = frame[frame["date"] == d]
        cc = g[[col, "fwd_ret"] + [c for c in themes if c in g.columns]].apply(
            pd.to_numeric, errors="coerce").dropna()
        rows.append({"date": str(d)[:10], "panel_rows": int(len(g)),
                     "complete_case_rows": int(len(cc))})
        if first_ok is None and len(cc) >= S.MIN_NAMES:
            first_ok = str(d)[:10]
    usable = [r for r in rows if r["complete_case_rows"] >= S.MIN_NAMES]
    cov = {c: float(pd.to_numeric(frame[c], errors="coerce").notna().mean())
           for c in themes if c in frame.columns}
    return {"quadrant_dates": len(rows), "usable_dates": len(usable),
            "first_usable_date": first_ok, "per_theme_nonnull": cov,
            "binding_theme": (min(cov, key=cov.get) if cov else None),
            "note": "MA58: complete-case residualisation on the seven incumbents makes an "
                    "incremental-IC gate a LATE-PERIOD test unless it says otherwise, and the "
                    "'early half' it reports is not the early half it thinks it is"}


def main(argv=None) -> int:
    data = _data_root(required=False)
    if not data:
        raise SystemExit("licensed data root absent; tried %r" % (data_candidates(),))
    fa = os.path.join(data, "free_analysis")

    kills = {}
    for part in ("A", "B"):
        p = os.path.join(fa, "STAGE1_KILLS_%s.json" % part)
        if not os.path.exists(p):
            print("REFUSING: no kill artifact at %s. The register requires the free kills run "
                  "FIRST, in their own pass (O10)." % p)
            return 2
        kills.update(json.load(io.open(p, encoding="utf-8"))["kills"])

    survivors = [a for a, v in kills.items() if v.get("kill_passes") is True]
    print("kill verdicts: %s" % json.dumps({a: v.get("kill_passes") for a, v in kills.items()}),
          flush=True)
    print("SURVIVORS to score: %r\n" % sorted(survivors), flush=True)

    panel = pd.read_pickle(os.path.join(fa, "UNIVERSE_BIAS_PANEL_full.pkl"))
    b, cen = K.build_quadrant(panel)
    kn = pd.read_pickle(os.path.join(fa, "S1_PANEL_keepnum.pkl"))
    knb, _ = K.build_quadrant(kn)

    themes = [c for c in DEPLOYED if c in knb.columns]
    grid = sorted(b["date"].unique())
    early = {str(x)[:10] for x in grid if str(x)[:10] <= K.BUILD_HALF_SPLIT}

    res = {"item": "STAGE1-BATCH1", "part": "scoring (build quadrant only)", "trials": 10,
           "register": "PREREG_stage1_batch1.md", "quadrant": cen,
           "check_quadrant_opened": False,
           "themes_residualised_on": themes,
           "no_x7_floor": "no calibrated floor exists for an incremental IC on this universe "
                          "(9,645 names against the 2,531 every published floor was measured "
                          "on); every critical value is LABELLED UNCALIBRATED (V2G, R1-VAR)",
           "kill_verdicts": {a: v.get("kill_passes") for a, v in kills.items()},
           "survivors_scored": sorted(survivors), "arms": {}}

    specs = []
    if "A7" in survivors:
        specs.append(("A7", knb, "z_neg_issuance", themes))
    if "A11" in survivors:
        specs.append(("A11", knb, "z_high_prox", themes))
        specs.append(("A11_momentum_only", knb, "z_high_prox", ["momentum"]))
    if "A3" in survivors:
        print("--- building A3's signal ---", flush=True)
        a3 = build_a3(data, b)
        print("    a3 rows %d over %d dates" % (len(a3), a3["date"].nunique()), flush=True)
        m = b.copy()
        m["date"] = m["date"].astype(str)
        m = m.merge(a3, on=["date", "ticker"], how="left")
        res["a3_merge"] = {"panel_rows": int(len(b)), "signal_rows": int(len(a3)),
                           "merged_non_null": int(m["a3_id"].notna().sum()),
                           "share": float(m["a3_id"].notna().mean())}
        print("    merged non-null %d of %d = %.4f"
              % (res["a3_merge"]["merged_non_null"], len(m), res["a3_merge"]["share"]),
              flush=True)
        specs.append(("A3", m, "a3_id", themes))

    if specs:
        n0, f0, c0, t0_ = specs[0]
        res["template_restriction"] = template_restriction(f0, t0_, c0)
        tr = res["template_restriction"]
        print("\nTEMPLATE RESTRICTION: %d of %d quadrant dates usable, first %s, binding theme "
              "%s at %.4f non-null"
              % (tr["usable_dates"], tr["quadrant_dates"], tr["first_usable_date"],
                 tr["binding_theme"], tr["per_theme_nonnull"][tr["binding_theme"]]), flush=True)
        res["min_half_dates_floor"] = S.MIN_HALF_DATES

    pvals = {}
    for name, frame, col, th in specs:
        print("\n--- %s on %s ---" % (name, col), flush=True)
        ics = S.incremental_ic(frame, col, th)
        if not ics:
            res["arms"][name] = {"error": "no scoreable date"}
            continue
        allv = [x[1] for x in ics]
        ev = [x[1] for x in ics if x[0] in early]
        lv = [x[1] for x in ics if x[0] not in early]
        full = S.hac_t(allv)
        e = S.hac_t(ev) if len(ev) >= 3 else None
        l = S.hac_t(lv) if len(lv) >= 3 else None
        p = S.two_sided_p(full["t"], full["n"]) if full else None
        same_sign = (e and l and (e["mean"] > 0) == (l["mean"] > 0))
        res["arms"][name] = {
            "column": col, "residualised_on": th, "dates": len(ics),
            "median_ic": float(np.median(allv)), "mean_ic": float(np.mean(allv)),
            "full": full, "early": e, "late": l,
            "two_sided_p": p,
            "halves_same_sign": bool(same_sign),
            "both_halves_t_above_2_UNCALIBRATED": bool(
                e and l and abs(e["t"]) >= 2.0 and abs(l["t"]) >= 2.0),
            "crit_label": "UNCALIBRATED -- 2.0 is conventional; no calibrated floor exists for "
                          "an incremental IC on this universe (V2G, R1-VAR)",
        }
        # §0's both-halves rule can only be READ where both halves exist. A half below the
        # shipped `min_dates` floor is not a half, and reporting a *t* on it as if it were is
        # how a 5-date cell comes to carry a verdict.
        ne = (e or {}).get("n") or 0
        nl = (l or {}).get("n") or 0
        state, words = S.stage1_verdict(e, l, same_sign)
        res["arms"][name]["halves_assessable"] = bool(state != "NOT_ASSESSABLE")
        res["arms"][name]["half_dates"] = {"early": ne, "late": nl,
                                           "floor": S.MIN_HALF_DATES}
        res["arms"][name]["stage1_state"] = state
        res["arms"][name]["stage1_verdict"] = words
        if name in S.BH_SET:
            pvals[name] = p
        print("  dates %d | median IC %+.6f | HAC t %+.4f | p %.5f | early t %s late t %s"
              % (len(ics), np.median(allv), full["t"], p or float("nan"),
                 ("%+.3f" % e["t"]) if e else "n/a", ("%+.3f" % l["t"]) if l else "n/a"),
              flush=True)

    # the arms that were never scored still occupy the BH set as un-scorable
    for a in S.BH_SET:
        pvals.setdefault(a, None)
    res["benjamini_hochberg"] = S.benjamini_hochberg(pvals)

    json.dump(res, io.open(os.path.join(fa, "STAGE1_SCORE.json"), "w", encoding="utf-8"),
              indent=2, default=str)
    print("\n=== BENJAMINI-HOCHBERG q=%.2f across k=%d ===" % (S.BH_Q, S.BH_K))
    for a, d in sorted(res["benjamini_hochberg"]["arms"].items(),
                       key=lambda kv: (kv[1].get("rank") or 99)):
        if d.get("p") is None:
            print("  %-20s p n/a  -> %s" % (a, d.get("why")))
        else:
            print("  %-20s p %.5f  rank %d  thr %.5f  -> survives_bh=%s"
                  % (a, d["p"], d["rank"], d["threshold"], d["survives_bh"]))
    print("\nwrote %s" % os.path.join(fa, "STAGE1_SCORE.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
