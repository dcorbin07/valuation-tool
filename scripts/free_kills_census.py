"""FREE KILLS — the zero-trial pre-outcome census for N1-N8 and W-17, plus MC9's validation.

WHAT THIS IS
    Read-only censuses. No register is committed, no arm is scored, no trial is booked, no WRDS
    pull is made. Every number below is a COUNT, a COVERAGE SHARE, or a SIGNAL-vs-SIGNAL rank
    correlation. **No forward return is joined to anything and no outcome statistic is computed**
    -- pinned by `tests/test_free_kills_census.py` over this module's own syntax tree.

ORDER
    The handoff's order: N3, N8, N4, W-17, then N1, N2, N5, N6, N7, then MC9.

TWO TRAPS THIS FILE HANDLES EXPLICITLY
    * `data/` IS EMPTY IN A WORKTREE. Resolved by walking up to the checkout that owns it
      (`E-5`'s wrong-object family).
    * THE PANEL'S `date` IS A STRING AND `B13_ADV_PANEL`'s IS A `datetime.date`. Merging them
      without normalising matches ZERO rows IN SILENCE, which is this record's most expensive
      recurring join defect. Both sides are forced to `YYYY-MM-DD` strings.

RUN
    python -m scripts.free_kills_census
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, REPO)

PANEL = os.path.join("free_analysis", "panel_corrected_69d.pkl")

# ---- band grid for the buildability censuses. A CENSUS may report a grid; the ARM may not. ----
CEILINGS = [2e9, 5e9, 1e10]        # market cap, dollars -- "small/mid" is BELOW the served tier
FLOORS = [1e6, 5e6, 2e7]           # dollar ADV
BAND_CEILING = 5e9                 # the band used for the per-draft censuses below
BAND_FLOOR = 5e6

MIN_BOOK = 50                      # CONTRACT_MIN_POSITIONS
NONNULL_RULE = 0.70                # the project's own 70% rule
COSTUME_BAR = 0.60                 # R6's / E-1's own bar, reused verbatim
CLUSTER_WINDOW_DAYS = 90
SPINOFF_CLOSE = 100                # N8: usable events below this -> close
SPINOFF_UNDERPOWERED = 400         # N8: below this -> UNDERPOWERED by construction (DC-1 n_eff)

THEMES7 = ("value", "quality", "momentum", "insider", "capital_discipline", "size",
           "institutional")


def _data_root() -> str:
    d = REPO
    for _ in range(6):
        if os.path.isfile(os.path.join(d, "data", PANEL)):
            return os.path.join(d, "data")
        p = os.path.dirname(d)
        if p == d:
            break
        d = p
    raise SystemExit("REFUSING: no data root holding %s (a worktree carries data/ EMPTY)" % PANEL)


def _norm_date(s) -> pd.Series:
    """Both sides of every join become YYYY-MM-DD strings. See the module docstring."""
    return pd.Series(s).astype(str).str.slice(0, 10)


def _spearman(a, b) -> float:
    a = pd.Series(a).astype(float)
    b = pd.Series(b).astype(float)
    ok = a.notna() & b.notna()
    if ok.sum() < 8:
        return float("nan")
    return float(a[ok].rank().corr(b[ok].rank()))


def _mean_abs_per_date_rho(df, col_a, col_b) -> dict:
    vals = []
    for _, g in df.groupby("date"):
        r = _spearman(g[col_a], g[col_b])
        if r == r:
            vals.append(abs(r))
    if not vals:
        return {"mean_abs_rho": None, "n_dates": 0}
    return {"mean_abs_rho": round(float(np.mean(vals)), 6),
            "max_abs_rho": round(float(np.max(vals)), 6),
            "n_dates": len(vals)}


# ---------------------------------------------------------------------------
def load_panel(root):
    p = pd.read_pickle(os.path.join(root, PANEL))
    p = p.copy()
    p["date"] = _norm_date(p["date"])
    p["ticker"] = p["ticker"].astype(str).str.upper()
    return p


def load_adv(root):
    b = pd.read_pickle(os.path.join(root, "free_analysis", "B13_ADV_PANEL.pkl")).copy()
    b["date"] = _norm_date(b["date"])
    b["ticker"] = b["ticker"].astype(str).str.upper()
    return b


def banded(panel, adv, ceiling=BAND_CEILING, floor=BAND_FLOOR):
    """The small/mid band: market cap BELOW `ceiling`, dollar ADV ABOVE `floor`."""
    m = panel.merge(adv[["ticker", "date", "adv"]], on=["ticker", "date"], how="left")
    if len(m) != len(panel):
        raise SystemExit("REFUSING: the ADV merge changed the row count (%d -> %d)"
                         % (len(panel), len(m)))
    keep = (m["market_cap"] < ceiling) & (m["adv"] > floor)
    return m[keep].copy(), m


# ===========================================================================
# N3 -- the earnings-date spine inside the band
# ===========================================================================
def kill_n3(panel, band, root):
    from valuation.edge.event_spine import EventSpine
    names_panel = sorted(panel["ticker"].unique())
    names_band = sorted(band["ticker"].unique())
    csv = os.path.join(root, "backtest_freeze_2026-08", "bulk", "events.csv")

    spine = EventSpine.build(names=names_panel, csv_path=csv)
    cen_panel = spine.census(names=names_panel)
    cen_band = spine.census(names=names_band)

    def _ann_per_ticker_year(names):
        tot, pairs = 0, 0
        for t in names:
            ds = spine.by_ticker.get(t) or []
            ds = [d for d in ds if "2009" <= d[:4] <= "2026"]
            yrs = {d[:4] for d in ds}
            tot += len(ds)
            pairs += len(yrs)
        return (tot / pairs) if pairs else None

    out = {
        "panel_names": len(names_panel),
        "band_names": len(names_band),
        "panel_states": dict(cen_panel.get("states", {})),
        "band_states": dict(cen_band.get("states", {})),
        "panel_fail_closed": len(cen_panel.get("fail_closed", [])),
        "band_fail_closed": len(cen_band.get("fail_closed", [])),
        "band_fail_closed_share": (len(cen_band.get("fail_closed", [])) / len(names_band)
                                   if names_band else None),
        "announcements_per_ticker_year_panel": _ann_per_ticker_year(names_panel),
        "announcements_per_ticker_year_band": _ann_per_ticker_year(names_band),
        "reference_w3b_options_universe": 2.83,
        "reference_expected": 4.0,
    }
    cov = 1.0 - (out["band_fail_closed_share"] or 0.0)
    out["band_covered_share"] = cov
    out["fired"] = bool(cov < NONNULL_RULE)
    out["bar"] = "covered share of band names >= %.2f" % NONNULL_RULE
    return out


# ===========================================================================
# N8 -- the spin-off event census
# ===========================================================================
def kill_n8(panel, band, root):
    a = pd.read_csv(os.path.join(root, "backtest_freeze_2026-08", "bulk", "actions.csv"),
                    usecols=["date", "action", "ticker"], low_memory=False)
    a["date"] = _norm_date(a["date"])
    a["ticker"] = a["ticker"].astype(str).str.upper()
    a["action"] = a["action"].astype(str)

    lo, hi = panel["date"].min(), panel["date"].max()
    names_panel = set(panel["ticker"].unique())
    names_band = set(band["ticker"].unique())

    out = {"window": [lo, hi]}
    for code in ("spinoff", "spunofffrom", "spinoffdividend"):
        ev = a[a["action"] == code]
        inw = ev[(ev["date"] >= lo) & (ev["date"] <= hi)]
        out[code] = {
            "all_history": int(len(ev)),
            "in_panel_window": int(len(inw)),
            "on_panel_names": int(inw["ticker"].isin(names_panel).sum()),
            "on_band_names": int(inw["ticker"].isin(names_band).sum()),
        }
    usable = out["spinoff"]["on_band_names"] + out["spunofffrom"]["on_band_names"]
    out["usable_child_or_parent_events_in_band"] = int(usable)
    out["bar_close"] = SPINOFF_CLOSE
    out["bar_underpowered"] = SPINOFF_UNDERPOWERED
    out["fired"] = bool(usable < SPINOFF_CLOSE)
    out["underpowered"] = bool(usable < SPINOFF_UNDERPOWERED)
    return out


# ===========================================================================
# N4 -- the insider cluster census
# ===========================================================================
def kill_n4(panel, band, root):
    from valuation.studies import insider_routine as IR
    path = os.path.join(root, "backtest_freeze_2026-08", "backtest", "insiders.csv")
    cols = ["ticker", "ownername", "transactiondate", "transactioncode"]
    rows = []
    for ch in pd.read_csv(path, usecols=cols, chunksize=1_000_000, low_memory=False):
        ch = ch[ch["transactioncode"].astype(str).str.upper() == "P"]
        if len(ch):
            rows.append(ch)
    buys = pd.concat(rows, ignore_index=True)
    buys["ticker"] = buys["ticker"].astype(str).str.upper()
    buys["transactiondate"] = _norm_date(buys["transactiondate"])

    labels = IR.classify(buys)
    cov = IR.coverage(labels)
    opp = buys[np.asarray(IR.opportunistic_mask(labels))].copy()

    dates = sorted(band["date"].unique())
    by_date = {d: set(g["ticker"]) for d, g in band.groupby("date")}
    counts, cluster_counts = [], []
    for d in dates:
        start = (pd.Timestamp(d) - pd.Timedelta(days=CLUSTER_WINDOW_DAYS)).strftime("%Y-%m-%d")
        w = opp[(opp["transactiondate"] > start) & (opp["transactiondate"] <= d)]
        w = w[w["ticker"].isin(by_date[d])]
        per = w.groupby("ticker")["ownername"].nunique()
        counts.append(int((per >= 1).sum()))
        cluster_counts.append(int((per >= 2).sum()))
    return {
        "open_market_purchase_rows": int(len(buys)),
        "routine_share_of_classifiable": cov.get("routine_share_of_classifiable"),
        "opportunistic_rows": int(len(opp)),
        "window_days": CLUSTER_WINDOW_DAYS,
        "names_with_any_opportunistic_buyer_per_date":
            {"median": float(np.median(counts)), "min": int(min(counts)), "max": int(max(counts))},
        "names_with_TWO_OR_MORE_per_date":
            {"median": float(np.median(cluster_counts)), "min": int(min(cluster_counts)),
             "max": int(max(cluster_counts))},
        "reference_v6b_allcap_no_cluster_no_floor": 106,
        "bar": "median names with >= 2 distinct opportunistic buyers >= %d" % MIN_BOOK,
        "fired": bool(np.median(cluster_counts) < MIN_BOOK),
        "fired_hard": bool(np.median(cluster_counts) < 20),
    }


# ===========================================================================
# W-17 -- K1 CLOCK, answerable from the banked census with no pull
# ===========================================================================
def kill_w17(root):
    """K1 fires if the readable membership source carries EFFECTIVE dates only.

    `WRDS_CENSUS.md` records `crsp_a_indexes.dsp500list` as **2,064 DATED MEMBERSHIP SPELLS**,
    1925-12-31 -> 2024-12-31. A membership SPELL is an effective-date interval; it carries no
    ANNOUNCEMENT date. W-17's K1 is exactly "the census returns effective dates only, with no
    announcement date -> STOP", so the kill is answerable from the record without the pull.
    """
    census = os.path.join(REPO, "WRDS_CENSUS.md")
    txt = io.open(census, encoding="utf-8", errors="replace").read()
    has = "dsp500list" in txt
    spells = "membership spells" in txt or "dated\nmembership spells" in txt
    return {
        "source": "crsp_a_indexes.dsp500list",
        "census_records_it": bool(has),
        "census_describes_membership_spells": bool(spells),
        "spells": 2064,
        "span": "1925-12-31 -> 2024-12-31",
        "banked": os.path.isdir("D:/wrds/crsp_dsp500list"),
        "k1_condition": "the census returns EFFECTIVE dates only, with no announcement date",
        "fired": bool(has and spells),
        "k2_k4_status": ("BLOCKED on the pull -- the event-count and clustering kills need the "
                         "table itself, which is ENTITLED and NOT banked, and WRDS is down"),
    }


# ===========================================================================
# N1 -- buildability and the cost arithmetic
# ===========================================================================
def kill_n1(panel, adv):
    """Buildability on the EFFECTIVE dates only.

    A DEFECT IN THIS CENSUS, CAUGHT BY DISBELIEVING AN IDENTICAL COUNT ACROSS UNRELATED
    THRESHOLDS. The first cut reported `min_eligible = 0` and "5 dates below 50" in eight of nine
    grid cells. An identical figure across thresholds that share no boundary is a common cause,
    not eight coincidences: `B13_ADV_PANEL` is built from CRSP and spans 2009-01-15 -> 2024-10-23,
    while the panel runs to 2026-01-28, so the five rebalance dates past CRSP's cut have ZERO ADV
    coverage and every band read empty on them. **That is the vendor cut masquerading as a
    coverage hole -- `W-28`'s measured defect, and the same five dates `PREREG_DRAFT_oos1` already
    declared UNVERIFIABLE by construction.** They are now EXCLUDED and LISTED, never scored.
    """
    m = panel.merge(adv[["ticker", "date", "adv"]], on=["ticker", "date"], how="left")
    cov = m.groupby("date")["adv"].apply(lambda s: float(s.notna().mean()))
    effective = sorted(cov[cov > 0].index)
    excluded = sorted(cov[cov == 0].index)
    m = m[m["date"].isin(effective)]
    grid = {}
    for c in CEILINGS:
        for f in FLOORS:
            sel = m[(m["market_cap"] < c) & (m["adv"] > f)]
            per = sel.groupby("date")["ticker"].nunique().reindex(effective, fill_value=0)
            grid["cap<%.0fB_adv>%.0fM" % (c / 1e9, f / 1e6)] = {
                "median_eligible": float(per.median()),
                "min_eligible": int(per.min()),
                "max_eligible": int(per.max()),
                "dates_below_min_book": int((per < MIN_BOOK).sum()),
                "n_dates": int(len(per)),
            }
    key = "cap<%.0fB_adv>%.0fM" % (BAND_CEILING / 1e9, BAND_FLOOR / 1e6)
    chosen = grid[key]
    return {
        "adv_coverage_of_effective_cells": round(float(m["adv"].notna().mean()), 6),
        "effective_dates": len(effective),
        "excluded_dates_zero_adv_coverage": excluded,
        "exclusion_reason": ("B13_ADV_PANEL is CRSP-built and ends 2024-10-23; these are the "
                            "panel's rebalance dates past the vendor cut. LISTED, NOT SCORED "
                            "(W-28's defect; PREREG_DRAFT_oos1 named the same five dates). "
                            "MC9's SEP-based ADV runs to 2026 and is the natural substitute, "
                            "which is a measured reason that instrument is worth having."),
        "grid": grid,
        "band_used": key,
        "bar": "median eligible >= %d" % MIN_BOOK,
        "fired": bool(chosen["median_eligible"] < MIN_BOOK),
        "note": ("the cost leg of K1 needs Don's actual Roth size, which is not in the repo; "
                 "the buildability leg is reported here and the cost leg is NOT RUN"),
    }


# ===========================================================================
# N2 -- neg_issuance coverage and dispersion in the band
# ===========================================================================
def kill_n2(band):
    col = "z_neg_issuance"
    if col not in band.columns:
        return {"status": "ABSENT", "column": col}
    per = band.groupby("date")[col].apply(lambda s: float(s.notna().mean()))
    conc = []
    for _, g in band.groupby("date"):
        v = g[col].dropna()
        if len(v) >= 20:
            conc.append(float(v.abs().nlargest(max(1, len(v) // 20)).sum() / v.abs().sum()))
    return {
        "nonnull_share_per_date": {"median": round(float(per.median()), 6),
                                   "min": round(float(per.min()), 6)},
        "top5pct_share_of_absolute_mass": (round(float(np.median(conc)), 6) if conc else None),
        "bar": "median non-null share >= %.2f" % NONNULL_RULE,
        "fired": bool(per.median() < NONNULL_RULE),
    }


# ===========================================================================
# N5 -- analyst coverage (numest) availability and the size costume
# ===========================================================================
def kill_n5(band):
    """K1 is the IBES link, and it is reported as a LINK problem rather than a coverage one.

    `numest` lives in `ibes_statsum_epsus`, which is banked and keyed on IBES `ticker` (not a
    CRSP permno and not a Sharadar ticker). The link runs through `ibes_id`, and `W-3b` and
    `W-28` both measured that an UNDATED ticker link misattributes silently. So the honest free
    kill here is whether the link is DATED and buildable, and that is established by inspection
    of what is banked rather than by a correlation.
    """
    import glob
    ss = sorted(glob.glob("D:/wrds/ibes_statsum_epsus/*.pkl"))
    idp = sorted(glob.glob("D:/wrds/ibes_id/*.pkl"))
    out = {"statsum_chunks": len(ss), "ibes_id_chunks": len(idp)}
    if not ss or not idp:
        out["status"] = "ABSENT"
        out["fired"] = True
        return out
    one = pd.read_pickle(ss[len(ss) // 2], compression="gzip")
    ids = pd.read_pickle(idp[0], compression="gzip")
    out["statsum_columns"] = sorted(one.columns.tolist())[:28]
    out["statsum_has_numest"] = bool("numest" in one.columns)
    out["ibes_id_columns"] = sorted(ids.columns.tolist())[:28]
    dated = [c for c in ids.columns if "date" in str(c).lower()]
    out["ibes_id_date_columns"] = dated
    out["link_is_dated"] = bool(dated)
    out["bar"] = "numest present AND the ibes_id link carries dates"
    out["fired"] = not (out["statsum_has_numest"] and out["link_is_dated"])
    return out


# ===========================================================================
# N6 -- industry group sizes and the momentum costume
# ===========================================================================
def kill_n6(band):
    if "sector" not in band.columns or "z_ret_12_1" not in band.columns:
        return {"status": "ABSENT"}
    sizes = []
    for _, g in band.groupby("date"):
        vc = g.groupby("sector")["ticker"].nunique()
        if len(vc):
            sizes.append(float(vc.min()))
    b = band.copy()
    b["_ind_mom"] = b.groupby(["date", "sector"])["z_ret_12_1"].transform("mean")
    rho = _mean_abs_per_date_rho(b.dropna(subset=["_ind_mom", "momentum"]),
                                 "_ind_mom", "momentum")
    return {
        "min_industry_group_size_per_date": {"median": float(np.median(sizes)),
                                             "min": float(np.min(sizes))},
        "sectors_per_date_median": float(np.median(
            [band[band["date"] == d]["sector"].nunique() for d in sorted(band["date"].unique())])),
        "momentum_costume": rho,
        "costume_bar": COSTUME_BAR,
        "fired": bool(rho.get("mean_abs_rho") is not None
                      and rho["mean_abs_rho"] > COSTUME_BAR),
        "classification_caveat": ("the panel's `sector` is TODAY's classification, not "
                                 "point-in-time -- S25 measured 11.37% disagreement. This census "
                                 "measures GROUP SIZES and the costume, NOT a point-in-time map"),
    }


# ===========================================================================
# N7 -- the 52-week-high disclosure
# ===========================================================================
def kill_n7(band, panel):
    import valuation.edge.fundamental_panel as FP
    from valuation.screener.cross_sectional import zscore
    if "z_high_prox" not in band.columns:
        return {"status": "ABSENT"}
    b = band.copy()
    comp = []
    for d, g in panel.groupby("date"):
        c = FP.composite_from_frame(g, list(THEMES7), {t: 0.125 for t in THEMES7}, zscore)
        comp.append(pd.DataFrame({"ticker": g["ticker"].values, "date": d,
                                  "_composite": np.asarray(c)}))
    cdf = pd.concat(comp, ignore_index=True)
    b = b.merge(cdf, on=["ticker", "date"], how="left")
    return {
        "vs_momentum_theme": _mean_abs_per_date_rho(
            b.dropna(subset=["z_high_prox", "momentum"]), "z_high_prox", "momentum"),
        "vs_composite": _mean_abs_per_date_rho(
            b.dropna(subset=["z_high_prox", "_composite"]), "z_high_prox", "_composite"),
        "identity_check_rho_is_1": bool(
            abs((_mean_abs_per_date_rho(b.dropna(subset=["z_high_prox", "momentum"]),
                                        "z_high_prox", "momentum").get("mean_abs_rho") or 0) - 1.0)
            < 1e-9),
        "note": ("K1 is a DISCLOSURE, not a kill: a high correlation with `momentum` is expected "
                 "and is not disqualifying. K2 is the non-identity check."),
        "fired": False,
    }


# ===========================================================================
# MC9 -- validate the $ADV instrument against the clean CRSP panel
# ===========================================================================
def validate_mc9(root):
    from valuation.edge import adv_sep as A
    crsp = load_adv(root)
    # MC9's artifact is RAW SEP BARS keyed by ticker -- {ticker: [(date, o, h, l, c, vol, adj)]} --
    # NOT a precomputed ADV. So the instrument under test is `adv_sep.adv_series`, and validating
    # it means running it rather than reading a column.
    blob = pd.read_pickle(os.path.join(root, "free_analysis", "MC9_SEP_ADV.pkl"))
    if not (isinstance(blob, dict) and "by_ticker" in blob):
        return {"status": "UNEXPECTED_SHAPE", "type": type(blob).__name__}
    ser = A.adv_series(blob["by_ticker"])
    cell = A.by_cell(ser)
    key = list(zip(crsp["ticker"], crsp["date"]))
    crsp = crsp.assign(adv_sep=[cell.get(k) for k in key])
    m = crsp
    ok = m["adv_sep"].notna() & m["adv"].notna() & (m["adv"] > 0)
    ratio = (m.loc[ok, "adv_sep"].astype(float) / m.loc[ok, "adv"].astype(float))
    banked = None
    fp = os.path.join(root, "free_analysis", "MC9_FIDELITY.json")
    if os.path.isfile(fp):
        banked = json.load(open(fp)).get("vs_crsp")
    return {
        "crsp_cells": int(len(crsp)),
        "overlapping_cells": int(ok.sum()),
        "sep_covers_crsp_cells": round(float(ok.sum() / len(crsp)), 10),
        "median_ratio": round(float(ratio.median()), 10),
        "p05": round(float(ratio.quantile(0.05)), 10),
        "p95": round(float(ratio.quantile(0.95)), 10),
        "share_more_than_25pct_apart": round(float(((ratio - 1).abs() > 0.25).mean()), 10),
        "banked_MC9_FIDELITY_vs_crsp": banked,
        "note": ("MC9 was ALREADY validated -- MC9_FIDELITY.json is a B7 fidelity record. This "
                 "is an INDEPENDENT reproduction of that comparison, not a first one."),
    }


# ===========================================================================
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default=os.path.join(REPO, "FREE_KILLS_CENSUS.json"))
    args = ap.parse_args(argv)

    root = _data_root()
    print("[fk] data root %s" % root, flush=True)
    panel = load_panel(root)
    adv = load_adv(root)
    band, merged = banded(panel, adv)
    print("[fk] panel %d rows / %d names; band %d rows / %d names"
          % (len(panel), panel["ticker"].nunique(), len(band), band["ticker"].nunique()),
          flush=True)

    art = {
        "item": "FREE KILLS (N1-N8 + W-17) and MC9 validation",
        "class": "FACTS", "trials": 0,
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "data_root": root,
        "band": {"ceiling_usd": BAND_CEILING, "floor_adv_usd": BAND_FLOOR,
                 "rows": int(len(band)), "names": int(band["ticker"].nunique())},
    }

    for name, fn in (("N3", lambda: kill_n3(panel, band, root)),
                     ("N8", lambda: kill_n8(panel, band, root)),
                     ("N4", lambda: kill_n4(panel, band, root)),
                     ("W17", lambda: kill_w17(root)),
                     ("N1", lambda: kill_n1(panel, adv)),
                     ("N2", lambda: kill_n2(band)),
                     ("N5", lambda: kill_n5(band)),
                     ("N6", lambda: kill_n6(band)),
                     ("N7", lambda: kill_n7(band, panel)),
                     ("MC9", lambda: validate_mc9(root))):
        print("[fk] %s ..." % name, flush=True)
        try:
            art[name] = fn()
        except Exception as exc:                                     # noqa: BLE001
            art[name] = {"status": "FAILED", "error": "%s: %s" % (type(exc).__name__, exc)}
            print("    FAILED: %s: %s" % (type(exc).__name__, exc), flush=True)
        f = art[name].get("fired")
        print("    fired=%s" % f, flush=True)

    with io.open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("wrote %s" % args.out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
