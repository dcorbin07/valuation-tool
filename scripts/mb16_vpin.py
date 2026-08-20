"""MB16 pass 1 - build quote-classified VPIN and run the item's PRE-SCORING kill.

READ-ONLY. NO ARM IS SCORED HERE and no return is touched. This pass exists because MB16's kill
condition fires BEFORE any outcome: *"if quote-classified VPIN correlates above 0.90 within date
with O14's already-null signed_volume or unusual_volume, it is those features renamed and the arm
is withdrawn before any outcome is read."*

WHY QUOTE-CLASSIFIED ONLY. Andersen-Bondarenko's critique of Easley-Lopez de Prado-O'Hara's VPIN
is specific: the disputed component is the BULK VOLUME classifier, which they find inferior to a
standard tick rule. It does not reach a quote-classified construction. O14 already built and
validated the quote classifier here (Lee-Ready, median 98.54% of eligible prints classified), so
that is the only version built.

TWO CONSTANTS FIXED ON AVAILABILITY BEFORE ANY CORRELATION WAS COMPUTED (MA58's precedent, where
K=10 was fixed on availability and the K=5 sweep carries no verdict):

  * `N_BUCKETS = 50`, Easley-Lopez de Prado-O'Hara's own standard. Feasibility measured first on
    a 60-day sample: 100% of alert-days carry at least 5 contracts per bucket at n=50, median 248.
    n = 10/20/100 are computed as a SENSITIVITY and carry no verdict.
  * The correlation is taken WITHIN MONTH, not within date, and the reason is structural rather
    than convenient - see `_KILL_UNIT_NOTE`.

Everything else is O14's: the same book, the same eligibility, the same per-contract Lee-Ready
classifier imported rather than re-implemented (a second copy would be the B7 defect class), and
the comparison is against O14's OWN BANKED per-unit values in `O14_FEATURES.pkl` rather than a
re-derivation, so the two cannot drift.

    python -m scripts.mb16_vpin            # build + kill
    python -m scripts.mb16_vpin --kill-only  # re-read the dump, recompute the kill
"""
from __future__ import annotations

import io
import json
import os
import pickle
import sys
import time

import numpy as np
import pandas as pd

from valuation.edge import tickflow as TF
from valuation.edge import tickflow_signals as TS

_KILL_UNIT_NOTE = (
    "MB16 specifies the kill 'within date'. THAT CROSS-SECTION DOES NOT EXIST ON THIS BOOK and "
    "the fact is O14's own: measured here at 1,570 dates carrying a MEDIAN OF 2 NAMES, a maximum "
    "of 17, ZERO dates reaching 20 names, and 39.7% of dates carrying exactly ONE name. A "
    "within-date Spearman is undefined at n=1 and is identically +/-1 at n=2, so the registered "
    "statistic would be noise or a constant rather than a measurement. O14 hit the identical wall "
    "and sorted MONTHLY. The kill is therefore taken on the cross-section the study actually "
    "sorts on - WITHIN MONTH - and the POOLED correlation is reported beside it. Both are shown; "
    "the kill fires if EITHER exceeds the bar, which is the strictly more conservative reading."
)

N_BUCKETS = 50
SENSITIVITY_BUCKETS = (10, 20, 100)
KILL_BAR = 0.90
MIN_NAMES_FOR_RHO = 5          # a Spearman below this is not a measurement


def _data_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        cand = os.path.join(here, "data")
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return cand
        here = os.path.dirname(here)
    for cand in (os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                              "..", "..", "..", "..", "data")),):
        if os.path.isdir(os.path.join(cand, "options_universe")):
            return cand
    return os.path.join(os.getcwd(), "data")


DATA = _data_root()
TICKS = os.path.join(DATA, "options_ticks")
O14_FEATURES = os.path.join(DATA, "free_analysis", "O14_FEATURES.pkl")
DUMP = os.path.join(DATA, "free_analysis", "MB16_VPIN_UNITS.pkl")     # rule 9: store the draws
OUT = os.path.join(DATA, "free_analysis", "MB16_KILL.json")

T0 = time.time()


def _log(m):
    print("[%6.1fs] %s" % (time.time() - T0, m), flush=True)


# ---------------------------------------------------------------------------------------------
def vpin(sides, sizes, n_buckets: int = N_BUCKETS):
    """Quote-classified VPIN over one alert-day's classified prints, in TIME order.

    Volume is cut into `n_buckets` equal-volume buckets and a print STRADDLING a boundary is
    split across it, which is the standard construction; assigning whole prints to buckets would
    make the bucket sizes unequal and the imbalance denominator wrong.

    Returns None when there is not enough classified volume to fill the buckets, never 0.0 - a
    fabricated zero would read as "perfectly balanced flow" rather than "not measurable".
    """
    s = np.asarray(sides, dtype=np.float64)
    z = np.asarray(sizes, dtype=np.float64)
    ok = np.isfinite(s) & np.isfinite(z) & (s != 0) & (z > 0)
    if not ok.any():
        return None
    s, z = s[ok], z[ok]
    total = float(z.sum())
    if total <= 0 or n_buckets < 2 or total < n_buckets:
        return None

    v = total / float(n_buckets)
    edges = np.arange(1, n_buckets, dtype=np.float64) * v      # interior boundaries
    cum = np.cumsum(z)
    start = cum - z                                            # each print spans [start, cum)

    # signed and unsigned volume accumulated per bucket, splitting straddling prints exactly
    buy = np.where(s > 0, z, 0.0)
    sell = np.where(s < 0, z, 0.0)
    bounds = np.r_[0.0, edges, total]
    b_buy = np.zeros(n_buckets)
    b_sell = np.zeros(n_buckets)
    for k in range(n_buckets):
        lo, hi = bounds[k], bounds[k + 1]
        overlap = np.clip(np.minimum(cum, hi) - np.maximum(start, lo), 0.0, None)
        frac = np.divide(overlap, z, out=np.zeros_like(z), where=z > 0)
        b_buy[k] = float((buy * frac).sum())
        b_sell[k] = float((sell * frac).sum())

    imb = np.abs(b_buy - b_sell) / v
    return float(imb.mean())


def _sides_for(d):
    """O14's classification, per contract in time order - imported, never re-implemented."""
    price = d["price"].to_numpy(np.float64)
    bid = d["bid"].to_numpy(np.float64)
    ask = d["ask"].to_numpy(np.float64)
    right = d["right"].astype(str).to_numpy()
    strike = d["strike"].to_numpy(np.float64)
    expiry = d["expiration"].astype(str).to_numpy()
    cid = np.array(["%s|%s|%s" % (e, k, r) for e, k, r in zip(expiry, strike, right)])
    ts = pd.to_datetime(d["trade_timestamp"], utc=True, errors="coerce")
    tms = (ts.astype("int64") // 10 ** 6).to_numpy(np.float64)

    sides = np.zeros(len(d), dtype=np.int8)
    _u, codes = np.unique(cid, return_inverse=True)
    order = np.lexsort((tms, codes))
    gc = codes[order]
    bounds = np.flatnonzero(np.r_[True, gc[1:] != gc[:-1], True])
    for gi in range(bounds.size - 1):
        idx = order[bounds[gi]:bounds[gi + 1]]
        if idx.size:
            sides[idx] = TS.classify_side(price[idx], bid[idx], ask[idx])
    return sides, tms, d["size"].to_numpy(np.float64)


def unit(tkr, day):
    p = os.path.join(TICKS, tkr, "%s-%s.pkl" % (tkr, day))
    if not os.path.exists(p):
        return None
    try:
        with open(p, "rb") as f:
            d = pickle.load(f)["rows"]
    except Exception:                                                  # noqa: BLE001
        return None
    if not isinstance(d, pd.DataFrame) or not len(d):
        return None
    elig = np.isin(d["condition"].to_numpy(), np.asarray(TF.SINGLE_LEG_CODES))
    if not elig.any():
        return None
    d = d.loc[elig]
    if len(d) < 20:
        return None

    sides, tms, size = _sides_for(d)
    order = np.argsort(tms, kind="stable")          # VPIN is a TIME-ordered construction
    s_t, z_t = sides[order], size[order]

    out = {"ticker": tkr, "date": day, "month": day[:7],
           "n_prints": int(len(d)), "n_classified": int((sides != 0).sum()),
           "classified_rate": float((sides != 0).sum()) / max(len(d), 1),
           # the instrument check: O14's own statistic, recomputed on the same prints
           "signed_volume_recomputed": TS.signed_volume(sides, size),
           "vpin": vpin(s_t, z_t, N_BUCKETS)}
    for nb in SENSITIVITY_BUCKETS:
        out["vpin_n%d" % nb] = vpin(s_t, z_t, nb)
    return out


# ---------------------------------------------------------------------------------------------
def build():
    recs = pickle.load(open(O14_FEATURES, "rb"))["recs"]
    _log("O14 banked units: %d" % len(recs))
    out, missing = [], []
    for i, r in enumerate(recs, 1):
        u = unit(r["ticker"], r["date"])
        if u is None:
            missing.append((r["ticker"], r["date"]))
            continue
        u["o14_signed_volume"] = r.get("signed_volume")
        u["o14_unusual_volume"] = r.get("unusual_volume")
        u["o14_classified_rate"] = r.get("classified_rate")
        out.append(u)
        if i % 250 == 0:
            _log("  %d/%d  built %d  missing %d" % (i, len(recs), len(out), len(missing)))
    pickle.dump({"units": out, "missing": missing}, open(DUMP, "wb"))
    _log("wrote %s (%d units)" % (DUMP, len(out)))
    return out, missing


def _spearman(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3:
        return None
    x, y = a[m], b[m]
    if np.unique(x).size < 2 or np.unique(y).size < 2:
        return None
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def kill(units):
    df = pd.DataFrame(units)
    res = {}
    targets = {"signed_volume": "o14_signed_volume",
               "unusual_volume": "o14_unusual_volume",
               # NOT the registered comparison - see the note emitted with it
               "abs_signed_volume": "_abs_signed"}
    df["_abs_signed"] = df["o14_signed_volume"].abs()

    for label, col in targets.items():
        pooled = _spearman(df["vpin"], df[col])
        per_month, sizes = [], []
        for _m, g in df.groupby("month"):
            gg = g[np.isfinite(g["vpin"]) & np.isfinite(g[col])]
            if len(gg) < MIN_NAMES_FOR_RHO:
                continue
            r = _spearman(gg["vpin"], gg[col])
            if r is not None:
                per_month.append(r)
                sizes.append(len(gg))
        pm = np.array(per_month, dtype=np.float64)
        res[label] = {
            "pooled_spearman": pooled,
            "mean_within_month_spearman": float(pm.mean()) if pm.size else None,
            "median_within_month_spearman": float(np.median(pm)) if pm.size else None,
            "months_used": int(pm.size),
            "median_names_per_month": float(np.median(sizes)) if sizes else None,
            "max_abs": float(max(abs(pooled or 0.0),
                                 abs(float(pm.mean()) if pm.size else 0.0))),
        }
    return res


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--kill-only" in argv:
        blob = pickle.load(open(DUMP, "rb"))
        units, missing = blob["units"], blob["missing"]
        _log("re-read %d units from the dump" % len(units))
    else:
        units, missing = build()

    df = pd.DataFrame(units)
    # ---- gating instrument control, read BEFORE the kill (MB15's lesson) ----------------------
    rate_med = float(df["classified_rate"].median())
    sv_new = df["signed_volume_recomputed"].to_numpy(np.float64)
    sv_o14 = df["o14_signed_volume"].to_numpy(np.float64)
    m = np.isfinite(sv_new) & np.isfinite(sv_o14)
    max_dev = float(np.max(np.abs(sv_new[m] - sv_o14[m]))) if m.any() else None
    ctrl = {
        "lee_ready_classified_rate_median": rate_med,
        "o14_published_rate_median": 0.9854035696220825,
        "rate_reproduces": abs(rate_med - 0.9854035696220825) < 1e-9,
        "signed_volume_max_abs_deviation_vs_o14": max_dev,
        "signed_volume_reproduces_exactly": (max_dev is not None and max_dev == 0.0),
        "n_compared": int(m.sum()),
        "note": "If the classifier does not reproduce O14's banked values EXACTLY then VPIN is "
                "not being built on O14's instrument and no comparison against O14's features "
                "means anything. This is read before the kill, never after.",
    }
    _log("CONTROL classified-rate median %.16f (O14 %.16f) reproduces=%s"
         % (rate_med, 0.9854035696220825, ctrl["rate_reproduces"]))
    _log("CONTROL signed_volume max |dev| vs O14 banked: %r on %d units"
         % (max_dev, ctrl["n_compared"]))

    per_date = df.groupby("date").size()
    xsec = {
        "n_dates": int(per_date.size),
        "median_names_per_date": float(per_date.median()),
        "max_names_per_date": int(per_date.max()),
        "dates_with_20_or_more": int((per_date >= 20).sum()),
        "dates_with_exactly_one": int((per_date == 1).sum()),
        "within_date_is_computable": bool((per_date >= MIN_NAMES_FOR_RHO).sum() > 0.5 * per_date.size),
        "note": _KILL_UNIT_NOTE,
    }

    res = kill(units)
    registered = max(res["signed_volume"]["max_abs"], res["unusual_volume"]["max_abs"])
    fires = registered > KILL_BAR

    payload = {
        "item": "MB16",
        "pass": "instrument-and-kill",
        "status": "READ-ONLY - no arm scored, no return touched",
        "conditioning": "ALERT DAYS ONLY - the tick cache is exactly the alert days and nothing "
                        "else, so every figure here is conditioned on them and none generalises "
                        "to the tape.",
        "vpin_version": "QUOTE-CLASSIFIED (Lee-Ready). The Bulk Volume classifier that "
                        "Andersen-Bondarenko dispute is deliberately NOT built.",
        "n_buckets_primary": N_BUCKETS,
        "n_buckets_fixed_on": "availability, before any correlation - 100% of sampled alert-days "
                              "carry >=5 contracts per bucket at n=50, median 248",
        "sensitivity_buckets": list(SENSITIVITY_BUCKETS),
        "kill_bar": KILL_BAR,
        "n_units": int(len(df)),
        "n_missing": len(missing),
        "gating_control": ctrl,
        "cross_section": xsec,
        "correlations": res,
        "registered_kill_statistic": registered,
        "kill_fires": bool(fires),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print()
    print("CROSS-SECTION: %d dates, median %.1f names, max %d, dates>=20: %d"
          % (xsec["n_dates"], xsec["median_names_per_date"], xsec["max_names_per_date"],
             xsec["dates_with_20_or_more"]))
    print()
    for label, v in res.items():
        tag = "  (NOT the registered comparison)" if label == "abs_signed_volume" else ""
        print("%-20s pooled %+.4f   within-month mean %s   months %d%s"
              % (label, v["pooled_spearman"] or float("nan"),
                 ("%+.4f" % v["mean_within_month_spearman"])
                 if v["mean_within_month_spearman"] is not None else "   n/a",
                 v["months_used"], tag))
    print()
    print("REGISTERED KILL STATISTIC = %.4f against a bar of %.2f -> %s"
          % (registered, KILL_BAR, "FIRES" if fires else "DOES NOT FIRE"))
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
