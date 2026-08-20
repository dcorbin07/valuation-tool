"""MB1-SEL pass 2 - THE ARM. The mean selection residual with a paired cluster bootstrap.

REFUSES without a PASSING C-RANGE artifact. `PREREG_mb1sel_selection_residual.md` void condition 4
is "the arm run without a passing C-RANGE artifact", so the refusal is the register operating, not
a failure of this script.

AS OF 2026-08-19 THE CONTROL FIRES AND THIS ARM HAS NEVER BEEN RUN. The differential coverage
effect is -2.5454pp against a 1.00pp bar - twice the size of the -1.2762pp residual it would have
to explain, and in the SAME direction. The code is shipped complete so that (a) the refusal is
demonstrable rather than asserted, and (b) if the control is ever repaired or the scope narrowed
by a NEW register, the arm exists and was written before any outcome was seen.

THE MEDIAN IS COMPUTED NOWHERE HERE, by the register's own ban - `O17C4` and `MB1` both measured
that it cannot see this book's effect.

    python -m scripts.mb1sel_arm
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys

import numpy as np

from scripts.mb1sel_range_control import DATA, LEGS_IN, UNIV

CONTROL_IN = os.path.join(DATA, "free_analysis", "MB1SEL_RANGE_CONTROL.json")
ARMS_IN = os.path.join(DATA, "free_analysis", "MB1_MENU.json")
OUT = os.path.join(DATA, "free_analysis", "MB1SEL_ARM.json")

N_DRAWS = 2000
SEED = 20260820
BAR_PP = 1.00
TRIMS = (0.10, 0.20)          # declared SECONDARIES - no verdict power
N_SEEDS = 5


def _gate():
    """Refuse unless C-RANGE ran AND passed. Its own pass, read before anything is scored."""
    if not os.path.exists(CONTROL_IN):
        raise SystemExit("REFUSING: no C-RANGE artifact at %s - run "
                         "scripts.mb1sel_range_control first." % CONTROL_IN)
    c = json.load(io.open(CONTROL_IN, encoding="utf-8"))
    if not c.get("c_range_passes"):
        raise SystemExit(
            "REFUSING: C-RANGE FIRED. differential %+.4fpp against a bar of %.2fpp. The covered "
            "subset is not selected the same way in the two arms, so a confound at least as large "
            "as the effect cannot be ruled out as its cause. Register void condition 4: the arm "
            "does not run." % (c.get("differential_pp") or float("nan"), c.get("bar_pp")))
    return c


def _trimmed_mean(x, trim):
    """Symmetric trimmed mean. Returns None when trimming would empty the sample."""
    a = np.sort(np.asarray(x, dtype=np.float64))
    k = int(np.floor(len(a) * trim))
    a = a[k:len(a) - k] if k else a
    return float(a.mean()) if a.size else None


def _residual(a_pick, c_pick, a_menu, c_menu, agg):
    """(pick_gap - menu_gap) in pp under aggregator `agg`, or None on any empty component."""
    parts = [agg(x) if len(x) else None for x in (a_pick, c_pick, a_menu, c_menu)]
    if any(p is None for p in parts):
        return None
    ap, cp, am, cm = parts
    return ((ap - cp) - (am - cm)) * 100.0


def _load_book(p):
    with open(p, "rb") as fh:
        d = pickle.load(fh)
    return d["rows"] if isinstance(d, dict) else d


def _cluster(ticker, entry):
    """R3's own unit on this book: the name-year cell."""
    return (ticker, str(entry)[:4])


def main():
    _gate()          # never reached while the control fires

    legs = pickle.load(open(LEGS_IN, "rb"))
    a_legs, c_legs = legs["alert"], legs["control"]
    cut = json.load(io.open(ARMS_IN, encoding="utf-8"))["half_cut"]

    a_keys = {(l["ticker"], l["entry"]) for l in a_legs}
    c_keys = {(l["ticker"], l["entry"], l["seed"]) for l in c_legs}

    a_pick = [(r["ticker"], str(r["alert_ts"])[:10], float(r["pnl_pct"]))
              for r in _load_book(os.path.join(UNIV, "state_r2_splitclean.pkl"))
              if (r["ticker"], str(r["alert_ts"])[:10]) in a_keys and r.get("pnl_pct") is not None]
    c_pick = []
    for s in range(N_SEEDS):
        for r in _load_book(os.path.join(UNIV, "control_r2_splitclean_seed%d.pkl" % s)):
            if (r["ticker"], str(r["alert_ts"])[:10], s) in c_keys and r.get("pnl_pct") is not None:
                c_pick.append((r["ticker"], str(r["alert_ts"])[:10], float(r["pnl_pct"])))

    def bucket(rows, get):
        out = {}
        for r in rows:
            out.setdefault(_cluster(*get(r)), []).append(r)
        return out

    windows = {"full": lambda e: True, "early": lambda e: e < cut, "late": lambda e: e >= cut}
    rng = np.random.default_rng(SEED)
    payload = {"item": "MB1-SEL", "pass": "arm", "register": "PREREG_mb1sel_selection_residual.md",
               "n_draws": N_DRAWS, "seed": SEED, "bar_pp": BAR_PP,
               "cluster_unit": "(ticker, year) - R3's own unit",
               "median_is_banned": "the register bans it: O17C4 and MB1 both measured that the "
                                   "median cannot see this book's effect",
               "windows": {}}

    for wname, sel in windows.items():
        ap = [r for r in a_pick if sel(r[1])]
        cp = [r for r in c_pick if sel(r[1])]
        am = [l for l in a_legs if sel(l["entry"])]
        cm = [l for l in c_legs if sel(l["entry"])]
        keys = sorted({_cluster(r[0], r[1]) for r in ap}
                      | {_cluster(l["ticker"], l["entry"]) for l in am})
        bap, bcp = bucket(ap, lambda r: (r[0], r[1])), bucket(cp, lambda r: (r[0], r[1]))
        bam = bucket(am, lambda l: (l["ticker"], l["entry"]))
        bcm = bucket(cm, lambda l: (l["ticker"], l["entry"]))

        res = {}
        for label, agg in [("mean", np.mean)] + [("trim%d" % int(t * 100),
                                                  (lambda t_: lambda x: _trimmed_mean(x, t_))(t))
                                                 for t in TRIMS]:
            point = _residual([r[2] for r in ap], [r[2] for r in cp],
                              [l["ret"] for l in am], [l["ret"] for l in cm], agg)
            draws, dropped = [], 0
            for _ in range(N_DRAWS):
                pick = rng.choice(len(keys), size=len(keys), replace=True)
                sel_keys = [keys[i] for i in pick]           # PAIRED: same keys for both arms
                d = _residual([r[2] for k in sel_keys for r in bap.get(k, [])],
                              [r[2] for k in sel_keys for r in bcp.get(k, [])],
                              [l["ret"] for k in sel_keys for l in bam.get(k, [])],
                              [l["ret"] for k in sel_keys for l in bcm.get(k, [])], agg)
                if d is None:
                    dropped += 1
                else:
                    draws.append(d)
            arr = np.asarray(draws)
            lo, hi = (float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))
                      ) if arr.size else (None, None)
            res[label] = {
                "point_pp": point, "ci95_lo_pp": lo, "ci95_hi_pp": hi,
                "n_draws_used": int(arr.size), "n_draws_dropped": dropped,
                "excludes_zero": (lo is not None and (lo > 0 or hi < 0)),
                "entirely_inside_bar": (lo is not None and abs(lo) <= BAR_PP
                                        and abs(hi) <= BAR_PP),
                "nearer_end_beyond_bar": (lo is not None
                                          and min(abs(lo), abs(hi)) > BAR_PP),
                "is_primary": label == "mean",
            }
        payload["windows"][wname] = {"n_clusters": len(keys), "stats": res}

    # ---- the pre-committed three-state rule, on the PRIMARY ONLY -----------------------------
    prim = {w: payload["windows"][w]["stats"]["mean"] for w in windows}
    signs = {np.sign(prim[w]["point_pp"]) for w in windows if prim[w]["point_pp"] is not None}
    confirmed = (all(prim[w]["excludes_zero"] for w in windows)
                 and len(signs) == 1
                 and prim["full"]["nearer_end_beyond_bar"])
    refuted = bool(prim["full"]["entirely_inside_bar"])
    payload["verdict"] = ("CONFIRMED" if confirmed else ("REFUTED" if refuted else "UNRESOLVED"))
    payload["verdict_reads_primary_only"] = True
    payload["decision"] = {
        "CONFIRMED": "MB2's grid is UNPARKED and goes to Don",
        "REFUTED": "contract selection is CLOSED",
        "UNRESOLVED": "NEITHER - MB2 stays parked and contract selection stays open",
    }[payload["verdict"]]

    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)
    print("VERDICT:", payload["verdict"], "->", payload["decision"])
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
