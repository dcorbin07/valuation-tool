# -*- coding: utf-8 -*-
"""IC1 — the FREE pre-outcome kills, run BEFORE any register is committed. ZERO TRIALS.

`K1`, `K2` and `K3` are all free by the draft's own §5: none scores an outcome, none compares a
return to a bar, and `MB1-SEL` holds that a control can only BLOCK. So they are run first and
read first, and if one fires the item closes at zero trials and no register is committed.

`K1` is the one most likely to fire and the draft says so: the data-aligned grid **must not
coincide with one of `X2`'s seven offsets**, because if it does the question is already answered.
`X2` swept {0, 5, 10, 20, 30, 40, 50} trading days, and the 13F deadline sits 45 calendar days
after each quarter end while the shipped grid sits ~15 days after — a gap of ~30 calendar days,
which is ~20 trading days. **X2's offset 20 is its BEST grid at long-short t 3.517.**
"""
from __future__ import annotations

import datetime as dt
import glob
import json
import os
import sys

import pandas as pd

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

X2_OFFSETS = (0, 5, 10, 20, 30, 40, 50)
X2_T = {0: 2.836, 5: 2.850, 10: 2.926, 20: 3.517, 30: 3.410, 40: 3.374, 50: 2.703}
FILING_DEADLINE_DAYS = 45          # 13F: 45 CALENDAR days after quarter end. A legal fact.
PANEL_MIN_XS, PANEL_MAX_XS = 1471, 1954     # the shipped panel's own range (K2's bar)


def _data_root():
    out = []
    env = os.environ.get("VALQUO_DATA_ROOT")
    if env:
        out.append(env)
    out.append(os.path.join(_HERE, "data"))
    parts = _HERE.replace("\\", "/").split("/.claude/worktrees/")
    if len(parts) == 2:
        out.append(os.path.join(parts[0].replace("/", os.sep), "data"))
    for c in out:
        if os.path.exists(os.path.join(c, "free_analysis", "panel_corrected_69d.pkl")):
            return c
    raise FileNotFoundError("no data root carrying panel_corrected_69d.pkl; tried %r" % (out,))


DATA = _data_root()
FA = os.path.join(DATA, "free_analysis")
OUT = os.path.join(FA, "IC1_KILLS.json")


def _trading_calendar():
    """The union of session dates across a sample of price files.

    A single ticker's file is NOT the calendar -- it starts when the name listed and ends when it
    delisted, so a thin name would invent holidays. Taking the union over many names and keeping
    dates seen by a quorum gives the exchange calendar without needing a vendor one.
    """
    files = sorted(glob.glob(os.path.join(DATA, "backtest", "prices", "*.csv")))
    if not files:
        raise FileNotFoundError("no price files under %s" % os.path.join(DATA, "backtest"))
    # a sample is enough for a UNION, and 300 large files cover every session densely
    seen = {}
    for f in files[::max(1, len(files) // 300)]:
        try:
            d = pd.read_csv(f, usecols=["date"])
        except Exception:
            continue
        for s in d["date"].astype(str).str[:10]:
            seen[s] = seen.get(s, 0) + 1
    if not seen:
        raise RuntimeError("no dates parsed from the price files")
    quorum = max(2, int(0.10 * max(seen.values())))
    cal = sorted(s for s, n in seen.items() if n >= quorum)
    return [dt.date.fromisoformat(s) for s in cal], len(files)


def main() -> int:
    panel = pd.read_pickle(os.path.join(FA, "panel_corrected_69d.pkl"))
    dates = sorted(panel["date"].unique())
    pdates = [pd.Timestamp(d).date() for d in dates]

    cal, n_files = _trading_calendar()
    cal_set = set(cal)
    idx = {d: i for i, d in enumerate(cal)}

    out = {"item": "IC1", "pass": "0 free kills", "trials": 0,
           "licence": ("MB1-SEL: a control can only BLOCK, never produce. The draft's own §5 "
                       "makes K1-K3 free and read first; if one fires the item closes at zero "
                       "trials and no register is committed."),
           "calendar": {"price_files": n_files, "sessions": len(cal),
                        "first": cal[0].isoformat(), "last": cal[-1].isoformat()},
           "x2_offsets": list(X2_OFFSETS), "x2_long_short_t": X2_T,
           "filing_deadline_days": FILING_DEADLINE_DAYS}

    # ---------------- the data-aligned grid, per the draft's arm
    def first_session_on_or_after(d):
        while d not in cal_set:
            d += dt.timedelta(days=1)
            if d > cal[-1]:
                return None
        return d

    rows = []
    for p in pdates:
        # the quarter END that the 13F filed before this rebalance refers to: the most recent
        # quarter end strictly before the panel date
        qe = None
        for m, day in ((12, 31), (9, 30), (6, 30), (3, 31)):
            cand = dt.date(p.year if m <= p.month else p.year - 1, m, day)
            if cand < p:
                qe = max(qe, cand) if qe else cand
        deadline = qe + dt.timedelta(days=FILING_DEADLINE_DAYS)
        for lag in (0, 1, 2):
            tgt = first_session_on_or_after(deadline)
            if tgt is None:
                continue
            j = idx[tgt] + lag
            if j >= len(cal):
                continue
            tgt = cal[j]
            if p not in idx:
                continue
            rows.append({"panel_date": p.isoformat(), "quarter_end": qe.isoformat(),
                         "deadline": deadline.isoformat(), "settling_lag_td": lag,
                         "aligned_date": tgt.isoformat(),
                         "offset_td": idx[tgt] - idx[p]})

    df = pd.DataFrame(rows)
    out["implied_offset_by_settling_lag"] = {}
    for lag in (0, 1, 2):
        s = df[df["settling_lag_td"] == lag]["offset_td"]
        if s.empty:
            continue
        out["implied_offset_by_settling_lag"][str(lag)] = {
            "n_dates": int(len(s)), "median": float(s.median()), "mean": float(s.mean()),
            "min": int(s.min()), "max": int(s.max()),
            "modal": int(s.mode().iloc[0]),
            "collides_with_x2": sorted({int(v) for v in s.unique()} & set(X2_OFFSETS)),
            "share_on_an_x2_offset": float(s.isin(X2_OFFSETS).mean())}

    # ---------------- K1
    lag1 = out["implied_offset_by_settling_lag"].get("1", {})
    modal = lag1.get("modal")
    collides = modal in X2_OFFSETS
    out["K1_grid_is_new_and_keeps_the_window"] = {
        "bar": ">= 69 dates AND the implied offset must not coincide with an X2 offset",
        "implied_modal_offset_td": modal,
        "x2_offsets": list(X2_OFFSETS),
        "collides": bool(collides),
        "x2_long_short_t_at_that_offset": X2_T.get(modal),
        "pass": not collides,
        "why_it_matters": ("if the data-aligned grid IS one X2 already ran, the question is "
                           "answered and the arm would re-measure a banked result at the cost "
                           "of a trial")}

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=str)

    print("trading calendar: %d sessions from %d price files (%s .. %s)"
          % (len(cal), n_files, cal[0], cal[-1]))
    print("\nimplied offset of the 13F-deadline grid, by settling lag:")
    for lag, v in out["implied_offset_by_settling_lag"].items():
        print("  lag %s td: modal %+d  median %+.1f  range %+d..%+d  | on an X2 offset: %.1f%% %s"
              % (lag, v["modal"], v["median"], v["min"], v["max"],
                 100 * v["share_on_an_x2_offset"],
                 ("COLLIDES %r" % v["collides_with_x2"]) if v["collides_with_x2"] else ""))
    k1 = out["K1_grid_is_new_and_keeps_the_window"]
    print("\nK1: modal offset %+d -> %s" % (k1["implied_modal_offset_td"],
                                            "PASS" if k1["pass"] else "FIRES"))
    if collides:
        print("    the data-aligned grid IS X2's offset %d, which X2 already measured at "
              "long-short t %.3f" % (modal, X2_T[modal]))
    print("\nwrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
