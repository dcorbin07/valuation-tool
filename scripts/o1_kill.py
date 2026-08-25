"""O-1 pass 1 - THE PRE-OUTCOME KILL. Does the market already price the accounting flag?

`PREREG_o1_long_puts_accounting_flags.md` (ALONE and BLIND at `c82c15b`; trial booked at
`5423515` BEFORE this runner existed).

READ BEFORE ANY ARM, IN ITS OWN PASS - `O10`'s process defect, not repeated. `scripts/o1_arm.py`
REFUSES without the artifact this writes.

THE QUESTION. If flagged names' options already carry a fatter left tail, the put is already
expensive and the edge is dead before an arm runs. That is a FINDING, and it saves the arm's cost.

    KILL: withdraw the arm if the flagged/unflagged left-tail-mass ratio at x = 0.50 is >= 2.0.

**2.0 is `MA28`'s OWN ratio bar, reused verbatim** rather than chosen here, and 0.50 is `MA28`'s
own crash definition. 0.65 and 0.80 are declared secondaries carrying no kill power.

WHY THIS CANNOT REUSE `E-4`'s BANKED PANEL, measured rather than assumed. `E4_TAIL_PANEL.pkl`
holds 17,558 rows from this same instrument, but its tenor spans **51-123 DTE, median 86** -
**ZERO rows** in this register's declared 150-210 band and zero in 330-400. E-4's band was right
for E-4 (its `TARGET_DTE` 92 matches `MA28`'s 63-trading-day crash window in calendar days); it
simply does not measure the tail at the tenor THIS arm would buy. Reusing it would answer a
different question at a tenor `E-5`'s arithmetic argues against.

NOTHING IS RE-IMPLEMENTED. `market_tail.tail_mass_row` and `rnd.build_slice` are IMPORTED and
driven at this register's declared tenor and thresholds, both of which are already parameters;
`build_flags` is `s10_accounting_veto`'s ONE definition.

    python -m scripts.o1_kill --build     # the tail panel at 150-210 DTE (slow, checkpointed)
    python -m scripts.o1_kill --kill      # the comparison and the verdict
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import chain_store as cs                          # noqa: E402
from valuation.studies import market_tail as mt                       # noqa: E402
from s10_accounting_veto import build_flags                           # noqa: E402  ONE definition

# ---- the register's declared constants. None is chosen here. ---------------------------------
PRIMARY_X = 0.50                  # MA28's own crash definition
SECONDARY_X = (0.65, 0.80)        # declared secondaries, NO kill power
KILL_RATIO = 2.0                  # MA28's own ratio bar, reused verbatim
TARGET_DTE = 180                  # register sec 4: primary tenor 150-210, midpoint
BAND = (150, 210)                 # register sec 4, fixed by E-5's arithmetic before any outcome
RATE = 0.03

PANEL_NAME = "panel_corrected_69d.pkl"
TAIL_PANEL = "O1_TAIL_PANEL.pkl"
OUT = "O1_KILL.json"

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _data(*parts) -> str:
    """Probe for a FILE this run cannot proceed without, never for a directory.

    EXISTENCE IS NOT POPULATION - `DEEPITM-FIN`'s defect, and the first cut of this function
    walked straight into it: the worktree carries `data/free_analysis/` AND
    `data/bulk/prepared/bars/`, both of which EXIST and the latter of which holds ZERO files
    against the primary checkout's 502. Probing on the directory picked the empty one, and
    `raw_close_series` then returned None for every name - which would have produced a clean
    coverage refusal rather than an error. Caught by the smoke test, not by anything raising.
    """
    for cand in (os.path.join(_HERE, "data"),
                 os.path.abspath(os.path.join(_HERE, "..", "..", "..", "data"))):
        if os.path.isfile(os.path.join(cand, "free_analysis", PANEL_NAME)):
            return os.path.join(cand, *parts)
    return os.path.join(_HERE, "data", *parts)


def _bars_dir() -> str:
    """The bars cache, resolved on POPULATION. See `_data`."""
    for cand in (_data("bulk", "prepared", "bars"),
                 os.path.abspath(os.path.join(_HERE, "..", "..", "..", "data",
                                              "bulk", "prepared", "bars"))):
        if os.path.isdir(cand) and len(os.listdir(cand)) > 50:
            return cand
    raise SystemExit("REFUSING: no POPULATED bars cache; a density needs an as-traded spot")


def _out(name):
    return _data("free_analysis", name)


def raw_close_series(bars_dir: str, sym: str):
    """As-traded closes. U1-SPLIT: a density built on an ADJUSTED close is centred nowhere near
    the money and will not raise - rnd's parity diagnostic is what catches it."""
    p = os.path.join(bars_dir, "%s.pkl" % sym)
    if not os.path.exists(p):
        return None
    try:
        import pickle
        with open(p, "rb") as fh:
            b = pickle.load(fh)
    except Exception:                                                  # noqa: BLE001
        return None
    if not isinstance(b, dict) or "raw_close" not in b:
        return None
    idx, val = [], []
    for d, rc in zip(b["date"], b["raw_close"]):
        if rc is None:
            continue
        v = float(rc)
        if np.isfinite(v) and v > 0:
            idx.append(pd.Timestamp(str(d)[:10]))
            val.append(v)
    return pd.Series(val, index=pd.DatetimeIndex(idx)) if idx else None


def tail_row(chain, spot, asof, symbol, thresholds) -> dict:
    """One row of left-tail mass at THIS register's declared thresholds.

    WHY THIS DOES NOT CALL `market_tail.tail_mass_row`, and it is a DEFECT REPORT rather than a
    preference (`RUN_RULES` rule 3). That wrapper takes `thresholds` as a parameter and then does
    `out["tail_mass"] = float(s.tail_mass[PRIMARY_THRESHOLD])` against a hard-coded 0.70, so it
    RAISES `KeyError` for any caller whose thresholds omit 0.70 - while the sensitivity loop two
    lines below guards with `if frac in s.tail_mass`. The parameter is honoured everywhere except
    the one column named for it. Worse for this register, its emitted columns come from
    `SENSITIVITY_THRESHOLDS = (0.50, 0.60, 0.80, 0.90)`, which does not contain this register's
    declared 0.65, so even passing a superset could not emit the secondary this register fixed in
    advance.

    So the wrapper's SCHEMA is `E-4`'s and cannot express this register's thresholds. The shipped
    primitives underneath it can: `pick_expiry` chooses the expiry and `rnd.build_slice` builds
    the density, both taking their thresholds as real parameters. Nothing is re-implemented and
    `E-4`'s instrument is NOT edited - editing it would move a landed figure.
    """
    from valuation.studies import rnd

    asof = pd.Timestamp(asof)
    out = {"symbol": str(symbol), "date": asof, "usable": False, "reason": None,
           "spot": float(spot) if spot is not None else None}
    if spot is None or not (np.isfinite(float(spot)) and float(spot) > 0):
        out["reason"] = "bad_spot"
        return out
    if chain is None or not len(chain):
        out["reason"] = "no_chain_on_date"
        return out
    e = mt.pick_expiry(pd.to_datetime(chain["expiration"]).unique(), asof,
                       target=TARGET_DTE, band=BAND)
    if e is None:
        out["reason"] = "no_expiry_in_dte_band"
        return out
    xs = chain.loc[pd.to_datetime(chain["expiration"]) == e]
    sl = rnd.build_slice(xs, spot=float(spot), asof=asof, expiry=e, symbol=str(symbol), r=RATE,
                         thresholds=tuple(thresholds))
    out["expiry"] = pd.Timestamp(e)
    out["dte_days"] = int((pd.Timestamp(e) - asof).days)
    if not sl.usable:
        out["reason"] = (sl.reasons or ("(none)",))[0]
        return out
    out["usable"] = True
    for x in thresholds:
        out["tail_%s" % x] = (float(sl.tail_mass[x]) if x in sl.tail_mass else None)
        out["extrap_%s" % x] = bool(sl.threshold_extrapolated.get(x, False))
    d = sl.diagnostics or {}
    out["atm_vol"] = d.get("atm_vol")
    out["integral"] = d.get("integral")
    out["negative_mass"] = d.get("negative_mass")
    out["parity_spot_dev_frac"] = d.get("parity_spot_dev_frac")
    out["n_smile"] = (d.get("smile") or {}).get("n_smile")
    return out


def chain_frame(path: str) -> pd.DataFrame:
    """Read either payload shape. The EOD freeze pickles a bare DataFrame; the harvest pickles a
    dict carrying `rows` plus its own `max_dte` provenance. Two shapes, one reader - a second
    reader per shape is the `B7` split this project keeps paying for."""
    p = pd.read_pickle(path)
    if isinstance(p, dict):
        if p.get("rows") is None:
            raise ValueError("harvest payload with no rows")
        return p["rows"]
    return p


def build() -> pd.DataFrame:
    panel = pd.read_pickle(_out(PANEL_NAME))
    panel["_d"] = pd.to_datetime(panel["date"])
    panel["_t"] = panel["ticker"].astype(str)

    chains, prov = cs.resolve_harvest()
    if not prov.get("pinned"):
        raise SystemExit("O-1 reads the PINNED freeze only; provenance says pinned=%r"
                         % prov.get("pinned"))
    print("chains: %s  manifest %s" % (chains, str(prov.get("manifest_sha256"))[:16]), flush=True)

    bars = _bars_dir()
    bar_syms = {f[:-4] for f in os.listdir(bars) if f.endswith(".pkl")}
    freeze = {d for d in os.listdir(chains) if os.path.isdir(os.path.join(chains, d))}
    names = sorted(freeze & set(panel["_t"]) & bar_syms)
    print("names with chain + raw_close + panel: %d" % len(names), flush=True)

    dates = sorted(panel["_d"].unique())
    by_year = {}
    for d in dates:
        by_year.setdefault(str(d)[:4], []).append(d)
    have = set(zip(panel["_t"], panel["_d"]))

    rows, done = [], set()
    ckpt = _out(TAIL_PANEL + ".partial")
    if os.path.exists(ckpt):
        prev = pd.read_pickle(ckpt)
        rows = prev.to_dict("records")
        done = set(prev["symbol"].astype(str))
        print("resuming: %d rows, %d symbols done" % (len(rows), len(done)), flush=True)

    thresholds = (PRIMARY_X,) + SECONDARY_X
    for i, t in enumerate(names, 1):
        if t in done:
            continue
        rc = raw_close_series(bars, t)
        if rc is None:
            continue
        tdir = os.path.join(chains, t)
        for y, ds in sorted(by_year.items()):
            f = os.path.join(tdir, "%s-%s.pkl" % (t, y))
            if not os.path.exists(f):
                continue
            want = [d for d in ds if (t, d) in have]
            if not want:
                continue
            try:
                df = chain_frame(f)
            except Exception as e:                                     # noqa: BLE001
                rows.append({"symbol": t, "date": pd.Timestamp(want[0]), "usable": False,
                             "reason": "chain_unreadable:%s" % type(e).__name__})
                continue
            dcol = pd.to_datetime(df["date"])
            for d in want:
                d = pd.Timestamp(d)
                spot = float(rc.loc[d]) if d in rc.index else None
                rows.append(tail_row(df.loc[dcol == d], spot, d, t, thresholds))
        if i % 25 == 0:
            pd.DataFrame(rows).to_pickle(ckpt)
            print("  ... %d/%d names, %d rows (checkpointed)" % (i, len(names), len(rows)),
                  flush=True)

    out = pd.DataFrame(rows)
    out.to_pickle(_out(TAIL_PANEL))       # RULE 9: the draws land before anything is summarised
    if os.path.exists(ckpt):
        os.remove(ckpt)
    print("wrote %s  rows %d  usable %d"
          % (TAIL_PANEL, len(out), int(out["usable"].sum())), flush=True)
    return out


def kill() -> dict:
    tail = pd.read_pickle(_out(TAIL_PANEL))
    tail["date"] = pd.to_datetime(tail["date"])
    u = tail[tail["usable"].fillna(False)].copy()

    panel = pd.read_pickle(_out(PANEL_NAME))
    panel["date"] = pd.to_datetime(panel["date"])

    # MA28's external-financing leg flags the TOP DECILE WITHIN EACH DATE, so `build_flags` is
    # handed EVERY panel ticker and the restriction to our rows happens AFTERWARDS. Handing it
    # only the optionable names would compute the decile boundary on a different universe and
    # produce a flag that is not the published one - it would compute cleanly and be a costume.
    all_tickers = sorted(panel["ticker"].astype(str).unique())
    flags = build_flags(_data("backtest"), all_tickers, sorted(panel["date"].unique()))
    flags["date"] = pd.to_datetime(flags["date"])

    # C-FIDELITY, GATING: the flags must be MA28's own object, not a lookalike computed on a
    # different universe. MA28-CARD published 6,542 flagged rows at 5.7414% of the panel, and
    # MB21's C1 is why the COUNT is gated rather than a rate compared loosely - a control that
    # scores perfectly on an empty comparison has compared nothing.
    fp = panel[["date", "ticker"]].copy()
    fp["ticker"] = fp["ticker"].astype(str)
    chk = fp.merge(flags[["date", "ticker", "vetoed"]], on=["date", "ticker"], how="left")
    n_panel_flagged = int(chk["vetoed"].fillna(False).sum())
    share = n_panel_flagged / len(chk) if len(chk) else 0.0
    if n_panel_flagged != 6542:
        raise SystemExit("C-FIDELITY FAILED: %d flagged panel rows against MA28's published "
                         "6,542. These are not MA28's flags; refusing to score." % n_panel_flagged)

    j = u.merge(flags[["date", "ticker", "vetoed", "n_flags"]],
                left_on=["date", "symbol"], right_on=["date", "ticker"], how="left")
    # A name with no computable accounting flag is NOT flagged, and the count is reported.
    j["acct_flag"] = j["vetoed"].fillna(False).astype(bool)
    n_no_flag_row = int(j["vetoed"].isna().sum())

    res = {}
    for x in (PRIMARY_X,) + SECONDARY_X:
        col = "tail_%s" % x
        if col not in j.columns:
            res[str(x)] = {"available": False}
            continue
        f = j.loc[j["acct_flag"], col].dropna()
        n = j.loc[~j["acct_flag"], col].dropna()
        fm = float(f.mean()) if len(f) else None
        nm = float(n.mean()) if len(n) else None
        res[str(x)] = {
            "available": True, "n_flagged": int(len(f)), "n_unflagged": int(len(n)),
            "flagged_mean_tail_mass": fm, "unflagged_mean_tail_mass": nm,
            "ratio": (fm / nm) if (fm is not None and nm) else None,
            "is_primary": x == PRIMARY_X,
        }

    prim = res[str(PRIMARY_X)]
    ratio = prim.get("ratio")
    fires = bool(ratio is not None and ratio >= KILL_RATIO)

    payload = {
        "item": "O-1", "pass": "pre-outcome-kill",
        "register": "PREREG_o1_long_puts_accounting_flags.md",
        "status": "READ BEFORE ANY ARM - no return is touched anywhere in this file",
        "tenor": {"target_dte": TARGET_DTE, "band": list(BAND),
                  "why": "register sec 4, fixed by E-5's arithmetic before any outcome: the "
                         "excess crash COUNT peaks in quarter two, so a 45-75 DTE put would miss "
                         "the peak of the excess it is buying",
                  "tenor_range_ratio": BAND[1] / BAND[0],
                  "e4_band_for_contrast": [50, 140]},
        "thresholds": {"primary": PRIMARY_X, "secondary": list(SECONDARY_X),
                       "why_primary": "0.50 is MA28's own crash definition"},
        "kill_bar": KILL_RATIO,
        "kill_bar_provenance": "MA28's own ratio bar, reused verbatim rather than chosen here",
        "n_slices": int(len(tail)), "n_usable": int(len(u)),
        "usable_share": (len(u) / len(tail)) if len(tail) else None,
        "n_joined": int(len(j)), "n_with_no_accounting_row": n_no_flag_row,
        "fidelity": {
            "gating": True,
            "flagged_panel_rows": n_panel_flagged, "ma28_published": 6542,
            "flagged_share": share, "ma28_published_share": 0.057414,
            "note": "GATES the run. build_flags is s10_accounting_veto's ONE definition, handed "
                    "EVERY panel ticker so the external-financing decile boundary is MA28's own "
                    "and not one recomputed on the optionable subset.",
        },
        "results": res,
        "kill_statistic": ratio,
        "kill_fires": fires,
        "e4_prior": "E-4 measured the market tail flag and the accounting flag NEARLY "
                    "INDEPENDENT at Cohen's kappa 0.0624 and odds ratio 2.4257, which the "
                    "register declared IN ADVANCE as strong prior evidence this kill would not "
                    "fire. E-4's UNDERPOWERED verdict is not reopened.",
        "framing": "O11 GOVERNS and nothing here licenses a trade. R2 stands. This is the PANEL, "
                   "not the top-decile book - MB8 measured the flag nearly disjoint from that "
                   "book at 3.56% of holdings and one crash of eighty-four.",
    }
    with io.open(_out(OUT), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print()
    print("slices %d, usable %d (%.1f%%), joined %d, no accounting row %d"
          % (len(tail), len(u), 100 * len(u) / max(len(tail), 1), len(j), n_no_flag_row))
    for x, v in res.items():
        if not v.get("available"):
            continue
        tag = "  <- PRIMARY" if v.get("is_primary") else ""
        print("  x=%-5s flagged %5d mean %.6f | unflagged %6d mean %.6f | ratio %s%s"
              % (x, v["n_flagged"], v["flagged_mean_tail_mass"] or float("nan"),
                 v["n_unflagged"], v["unflagged_mean_tail_mass"] or float("nan"),
                 ("%.4f" % v["ratio"]) if v["ratio"] else "n/a", tag))
    print()
    print("KILL STATISTIC %s against a bar of %.2f -> %s"
          % (("%.4f" % ratio) if ratio else "n/a", KILL_RATIO,
             "FIRES - the arm is WITHDRAWN" if fires else "DOES NOT FIRE"))
    print("wrote", _out(OUT))
    return payload


def main(argv=None):
    ap = argparse.ArgumentParser(description="O-1 pre-outcome kill (READ BEFORE ANY ARM)")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--kill", action="store_true")
    ns = ap.parse_args(argv)
    if ns.build:
        build()
    if ns.kill:
        kill()
    if not (ns.build or ns.kill):
        ap.error("choose --build or --kill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
