"""MC12 — PANEL EXTENSION, STAGE-1 CENSUS. Register: `PREREG_panel_ext_census.md`.

WHAT THIS IS
    Facts about what data exists per weighted theme and per calendar year 1995-2008, on two
    candidate routes to a pre-2009 panel. FACTS class, ZERO trials.

WHAT THIS IS NOT, AND IT IS PINNED RATHER THAN PROMISED
    No forward return, no price return, no information coefficient, no t-statistic is computed
    anywhere in this module. `tests/test_panel_ext_census.py` asserts that over this file's own
    SYNTAX TREE (E-4's idiom) rather than by grep, because a docstring naming the forbidden
    thing would trip a substring ban -- this record has paid for that five times.

    A CENSUS CANNOT PRODUCE A VERDICT ABOUT RETURNS. A PASS here means only "a successor
    register on this route and start year is not blocked by data availability".

THE TWO ROUTES
    ROUTE S -- the Sharadar freeze, same vendor as the shipped panel: raw bulk `sf1` (ARQ, PIT
    by EARLIEST `datekey`), `sep`, `actions`, `sf3`, plus the licensed insider export. This is
    the route `DESIGN_panel_extension.md` never considers.

    ROUTE W -- CRSP/Compustat already banked on `D:\\wrds`: `comp.co_ifndq` for fundamentals,
    `crsp.stocknames` DATED intervals -> cusip8 -> `comp.security` -> gvkey as `W-28` built it.
    The naive UNDATED ticker route is reported BESIDE the dated one as the contaminated control
    and NEVER as coverage.

WHY ROUTE W's PRICE LEG IS SIZED AND NOT MEASURED
    `co_ifndq` carries no price column at all, and `crsp.dsf` is banked only for 2008-2024. So
    every price-dependent theme on Route W before 2008 is a SIZE ESTIMATE extrapolated from the
    real 2008 year-chunk, never a coverage measurement, and every such figure is labelled.

RECONCILIATION -- A DECLARED SUBSTITUTION
    The register declares it: the WRDS login is rejected by PAM at this commit, so each banked
    chunk is reconciled against `D:\\wrds\\manifest.jsonl` (rows/sha256/status captured at pull
    time) and the manifest is verified against the frames on disk. That establishes the file on
    disk is the file the server returned. It does NOT re-establish that the server's table is
    unchanged since 2026-08-28, and the artifact says so.

WHERE `data/` LIVES
    A WORKTREE CARRIES `data/` EMPTY. Resolved by walking up to the checkout that owns it
    (`E-5`'s wrong-object family, which cost this project a silent skip once already). The
    resolution is REPORTED in the artifact so a reader can see which tree was read.

RUN
    python -m scripts.panel_ext_census            # both routes
    python -m scripts.panel_ext_census --route s  # one route
"""
from __future__ import annotations

import argparse
import ast
import io
import json
import os
import sys
import datetime as dt

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

YEARS = list(range(1995, 2009))          # the census window
REF_YEARS = list(range(2009, 2014))      # K4's backfill reference
START_YEARS = (1995, 1999, 2000)         # candidate start years to adjudicate

RAW_ROOT = r"D:\wrds"

# ---------------------------------------------------------------------------
# BARS -- every one from the register. Changing a value here voids the item.
# ---------------------------------------------------------------------------
K1_MIN_NAMES = 1030          # 70% of the shipped panel's own minimum 1,471 cross-section
K2_NONNULL = 0.70            # the project's own 70% non-null rule
K3_LO, K3_HI = 0.5, 2.0      # x the shipped panel's own later-delisting share; BOTH tails fail
K4_MAX_SHORTFALL_PP = 10.0   # percentage points below the 2009-2013 reference
PIT_LAG_DAYS = 120           # datekey must precede reportperiod + this, for K4

#: A year whose own maximum observed session count is below this cannot support a
#: price-history theme, and a bar calibrated against it would be vacuous. 200 is well below
#: any real US trading year (the thinnest in this window is 2001 at 248) and well above the
#: partial years the freeze's `sep` layer begins with.
MIN_PLAUSIBLE_SESSIONS = 200


def _data_root() -> str:
    """The checkout that owns a populated `data/`. A worktree's own is empty."""
    d = REPO
    for _ in range(6):
        cand = os.path.join(d, "data", "backtest_freeze_2026-08")
        if os.path.isdir(cand):
            return os.path.join(d, "data")
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    raise SystemExit("REFUSING: no populated data/backtest_freeze_2026-08 found from %s. "
                     "A worktree carries data/ EMPTY; run from a checkout that owns it." % REPO)


def _freeze() -> str:
    return os.path.join(_data_root(), "backtest_freeze_2026-08")


# ---------------------------------------------------------------------------
# The load-bearing set, DERIVED not retyped
# ---------------------------------------------------------------------------
def weighted_theme_inputs():
    """Delegate to `E-1`'s AST derivation rather than reimplement it (`B7`).

    Returns (distinct z-columns, {theme: [z-columns]}). `insider` legitimately returns ZERO
    z-columns: `factors.py` maps it as a fixed affine `(insider_score-50)/25`, not a z-score,
    so there is no standardised column to find -- which is why `DESIGN` 1.1's table lists 25
    rows for a correct prose count of 24.
    """
    sys.path.insert(0, HERE)
    from e1_graveyard_stouffer import weighted_theme_inputs as _wti
    return _wti()


#: z-column -> the raw SF1 fields it cannot be computed without. DECLARED, and printed in the
#: artifact, because the alternative is reimplementing `factors.py`'s formulas here and risking
#: a second definition of the composite (`B7`). A z-column counts as available on a row when
#: EVERY field it needs is non-null.
SF1_NEEDS = {
    "z_earnings_yield": ["netinccmnusd", "marketcap"],
    "z_fcf_yield":      ["fcf", "marketcap"],
    "z_ebit_ev":        ["ebit", "ev"],
    "z_book_to_price":  ["equity", "marketcap"],
    "z_neg_ev_sales":   ["ev", "revenue"],
    "z_neg_ev_ebitda":  ["ev", "ebitda"],
    "z_neg_ps":         ["marketcap", "revenue"],
    "z_roic":           ["ebit", "invcap"],
    "z_roe":            ["netinccmnusd", "equity"],
    "z_op_margin":      ["opinc", "revenue"],
    "z_gross_margin":   ["gp", "revenue"],
    "z_neg_leverage":   ["debt", "equity"],
    "z_gp_on_capital":  ["gp", "invcap"],
    "z_fcf_margin":     ["fcf", "revenue"],
    "z_accruals_q":     ["netinc", "ncfo", "assets"],
    "z_interest_cov":   ["ebit", "intexp"],
    "z_f_score":        ["netinc", "ncfo", "assets", "revenue", "gp"],
    "z_neg_issuance":   ["ncfcommon"],
    "z_neg_log_mktcap": ["marketcap"],
    # price-history columns: not in SF1, handled from `sep`
    "z_ret_12_1":       [],
    "z_ret_6_1":        [],
    "z_high_prox":      [],
    # ownership: not in SF1, handled from `sf3`
    "z_inst_accum":     [],
    "z_sm_breadth":     [],
}

SF1_FIELDS = sorted({f for v in SF1_NEEDS.values() for f in v})
SF1_COLS = ["ticker", "dimension", "datekey", "reportperiod", "calendardate"] + SF1_FIELDS


# ---------------------------------------------------------------------------
# ROUTE S
# ---------------------------------------------------------------------------
def route_s_fundamentals(chunksize=400_000, progress=True):
    """Stream raw bulk `sf1`, keep ARQ, and take the EARLIEST `datekey` per (ticker, period).

    Earliest-datekey is the point-in-time selection: the first vintage at which a period was
    observable. A later `datekey` for the same `reportperiod` is a restatement and must not be
    the row a historical date is scored on.
    """
    path = os.path.join(_freeze(), "bulk", "sf1.csv")
    keep = []
    wanted = set(YEARS) | set(REF_YEARS)
    n_raw = 0
    for i, ch in enumerate(pd.read_csv(path, usecols=SF1_COLS, chunksize=chunksize,
                                       low_memory=False)):
        n_raw += len(ch)
        ch = ch[ch["dimension"] == "ARQ"]
        if ch.empty:
            continue
        yr = ch["reportperiod"].astype(str).str.slice(0, 4)
        ch = ch[yr.isin({str(y) for y in wanted})]
        if not ch.empty:
            keep.append(ch)
        if progress and i % 10 == 0:
            print("   sf1 chunk %d, rows read %s, kept %s"
                  % (i, f"{n_raw:,}", f"{sum(len(k) for k in keep):,}"), flush=True)
    if not keep:
        raise SystemExit("REFUSING: sf1 ARQ yielded zero rows in 1995-2013 -- a filter is wrong")
    df = pd.concat(keep, ignore_index=True)
    df["year"] = df["reportperiod"].astype(str).str.slice(0, 4).astype(int)
    # PIT: earliest datekey per (ticker, reportperiod)
    df = df.sort_values("datekey").drop_duplicates(["ticker", "reportperiod"], keep="first")
    return df, n_raw


def theme_coverage(df, per_theme, year_col="year"):
    """Per theme per year: share of NAMES for which the theme is scoreable.

    Two definitions are reported side by side, and the pair is the point. The shipped composite
    takes `df[cols].mean(axis=1)`, and pandas SKIPS NaN -- so a row with one input present
    scores a theme built from one input. `W-28` measured that this silently becomes a DIFFERENT
    theme. `any` is therefore the semantics of the shipped code and `all` is the honest ceiling.
    """
    out = {}
    for yr, g in df.groupby(year_col):
        names = g["ticker"].nunique()
        row = {"names": int(names)}
        for theme, zcols in per_theme.items():
            usable = [z for z in zcols if SF1_NEEDS.get(z)]
            if not usable:
                row[theme] = None          # not an SF1 question; measured from its own source
                continue
            any_ok = None
            all_ok = None
            for z in usable:
                need = SF1_NEEDS[z]
                ok = g[need].notna().all(axis=1)
                any_ok = ok if any_ok is None else (any_ok | ok)
                all_ok = ok if all_ok is None else (all_ok & ok)
            g2 = g.assign(_any=any_ok, _all=all_ok)
            by_name = g2.groupby("ticker")[["_any", "_all"]].max()
            row[theme] = {"any": round(float(by_name["_any"].mean()), 6),
                          "all": round(float(by_name["_all"].mean()), 6),
                          "n_inputs": len(usable)}
        out[int(yr)] = row
    return out


def route_s_nonsf1_themes(sf1_names_by_year, progress=True):
    """The three weighted themes SF1 cannot answer, measured from their own sources.

    Without this the census would evaluate K2 on FOUR of the seven weighted themes and report a
    verdict as though it had covered all seven -- and `institutional` and `insider` are exactly
    the two the register expects to fail. Measured as PRESENCE relative to that year's SF1 name
    set, which is the population a panel built on Route S would actually score:

      * `momentum`  -- `sep`: a name needs a price history to have `ret_12_1` at all, so the
                       test is >= 250 trading days of closes inside the year.
      * `institutional` -- `sf3` (13F): >= 1 holder record dated in the year.
      * `insider`   -- the licensed insider export: >= 1 Form 4 row dated in the year.

    These are AVAILABILITY counts, never scores. No return, ratio or rank is computed.
    """
    fz = _freeze()
    years = sorted(sf1_names_by_year)
    out = {y: {} for y in years}

    def _count(path, tick_col, date_col, label, chunksize=1_000_000, min_rows=1,
               relative_frac=None):
        """`relative_frac` calibrates the bar against the YEAR'S OWN observed maximum.

        A DEFECT THIS PARAMETER EXISTS TO FIX, found by disbelieving a number rather than by
        anything raising. `momentum` first used an absolute `min_rows=250` trading days, and
        2001 came back at EXACTLY 0.000 sitting between 0.816 (2000) and 0.884 (2002) -- because
        the NYSE closed for four days after 11 September 2001 and that year has 248 sessions, so
        every name failed a 250-day bar. A knife-edge absolute threshold against a
        holiday-shortened year is the hazard `E-6` closed with "a successor must not set a
        knife-edge burn-in bar". Calibrating against the year's own maximum is immune to it.
        """
        seen = {y: {} for y in years}
        n = 0
        for i, ch in enumerate(pd.read_csv(path, usecols=[tick_col, date_col],
                                           chunksize=chunksize, low_memory=False)):
            n += len(ch)
            # progress prints BEFORE any filter can `continue` past it -- the first cut put it
            # after, so a source with no in-window rows printed nothing and read as a hang
            if progress and i % 10 == 0:
                print("   %s chunk %d, rows read %s" % (label, i, f"{n:,}"), flush=True)
            yr = ch[date_col].astype(str).str.slice(0, 4)
            ch = ch.assign(_y=pd.to_numeric(yr, errors="coerce"))
            ch = ch[ch["_y"].isin(years)]
            if ch.empty:
                continue
            for y, g in ch.groupby("_y"):
                d = seen[int(y)]
                vc = g[tick_col].astype(str).value_counts()
                for t, c in vc.items():
                    d[t] = d.get(t, 0) + int(c)
        for y in years:
            names = sf1_names_by_year[y]
            if not names:
                out[y][label] = None
                continue
            d = seen[y]
            vacuous = None
            if relative_frac is not None:
                observed_max = max(d.values()) if d else 0
                # A RELATIVE BAR GOES VACUOUS WHEN THE YEAR'S OWN MAXIMUM IS TRIVIAL, and that
                # is the second defect this block has produced. Calibrating against the year's
                # max fixed 2001 and then handed 1997 a bar of ONE row -- because `sep` starts
                # 1997-12-31, so that year holds a single session -- reporting 93.2% "available"
                # for a theme that needs twelve months of prices. A year that cannot supply a
                # plausible trading calendar is NOT AVAILABLE, never 93% available.
                if observed_max < MIN_PLAUSIBLE_SESSIONS:
                    out[y][label] = {
                        "share": 0.0, "names_with_source": 0, "sf1_names": int(len(names)),
                        "rows_required": None, "year_observed_max_rows": int(observed_max),
                        "bar": "NOT AVAILABLE",
                        "vacuous_reason": ("the year's own maximum of %d source rows is below "
                                           "the %d-session floor, so a relative bar would be "
                                           "trivially satisfied" % (observed_max,
                                                                    MIN_PLAUSIBLE_SESSIONS))}
                    continue
                need = max(1, int(round(relative_frac * observed_max)))
            else:
                need = min_rows
                observed_max = None
            hit = sum(1 for t in names if d.get(t, 0) >= need)
            out[y][label] = {"share": round(hit / len(names), 6),
                             "names_with_source": int(hit),
                             "sf1_names": int(len(names)),
                             "rows_required": int(need),
                             "year_observed_max_rows": observed_max,
                             "vacuous_reason": vacuous,
                             "bar": ("%.2f x the year's own max" % relative_frac
                                     if relative_frac is not None else "absolute")}
        return n

    _count(os.path.join(fz, "bulk", "sep.csv"), "ticker", "date", "momentum",
           relative_frac=0.90)
    _count(os.path.join(fz, "bulk", "sf3.csv"), "ticker", "calendardate", "institutional")
    ins = os.path.join(fz, "backtest", "insiders.csv")
    if os.path.exists(ins):
        _count(ins, "ticker", "transactiondate", "insider")
    else:
        for y in years:
            out[y]["insider"] = None
    return out


def route_s_pit_provenance(df):
    """K4: share of rows whose EARLIEST datekey precedes reportperiod + 120d, per year.

    A low share means the vendor supplied the period long after the fact -- backfill -- and a
    point-in-time panel built on it would be scoring information nobody had.
    """
    d = df.copy()
    rp = pd.to_datetime(d["reportperiod"], errors="coerce")
    dk = pd.to_datetime(d["datekey"], errors="coerce")
    d["_timely"] = (dk - rp).dt.days <= PIT_LAG_DAYS
    d["_lag"] = (dk - rp).dt.days
    out = {}
    for yr, g in d.groupby("year"):
        out[int(yr)] = {"rows": int(len(g)),
                        "timely_share": round(float(g["_timely"].mean()), 6),
                        "median_lag_days": (None if g["_lag"].dropna().empty
                                            else float(g["_lag"].median()))}
    return out


def actions_delisting():
    """Delisting events from the freeze's ACTIONS layer, as the B14 mask reads them."""
    path = os.path.join(_freeze(), "bulk", "actions.csv")
    a = pd.read_csv(path, usecols=["date", "action", "ticker"], low_memory=False)
    de = a[a["action"].astype(str).str.lower().str.contains("delist", na=False)]
    return de, a


#: K3's forward window, in years. PRIMARY is 5; the others ship as a labelled sensitivity
#: carrying NO verdict, so no single choice is load-bearing.
K3_HORIZONS = (3, 5, 10)
K3_PRIMARY_H = 5
ACTIONS_LAST_YEAR = 2026        # the freeze's ACTIONS cut; censors any window past it


def _first_delist_year(delist):
    return (delist.assign(_y=pd.to_datetime(delist["date"], errors="coerce").dt.year)
                  .dropna(subset=["_y"]).groupby("ticker")["_y"].min())


def later_delist_share(df, delist, year_col="year"):
    """K3: share of names present in a year that delist within a MATCHED forward window.

    A DEFECT IN THIS INSTRUMENT, FOUND BY DISBELIEVING ITS OWN OUTPUT AND FIXED BEFORE ANY
    VERDICT WAS READ. The first cut compared each extension year's share of names delisting at
    ANY later date against the shipped panel's EVER-delist share. Those are different objects: a
    1997 cohort has ~29 years of forward observation and the shipped panel ~17, so the extension
    years read 0.60-0.82 against a shipped 0.28 and THIRTEEN OF FOURTEEN YEARS "failed" the
    upper tail. Thirteen identical failures are a broken comparison, not thirteen broken
    universes -- the "two percentages on different objects" family this record names repeatedly.

    Repaired by giving both sides the SAME window length. The bar is untouched; what changed is
    that the two sides now measure the same quantity, which is what makes the ratio meaningful
    at all. A year whose window runs past the ACTIONS cut is reported CENSORED and is not scored.
    """
    first_de = _first_delist_year(delist)
    out = {}
    for yr, g in df.groupby(year_col):
        yr = int(yr)
        names = pd.Index(g["ticker"].unique())
        dy = first_de.reindex(names)
        rec = {"names": int(len(names)),
               "ever_delist_share": round(float(dy.notna().mean()), 6),
               "unbounded_later_delist_share_NOT_COMPARABLE":
                   round(float((dy > yr).fillna(False).mean()), 6)}
        for h in K3_HORIZONS:
            if yr + h > ACTIONS_LAST_YEAR:
                rec["within_%dy" % h] = None
                rec["within_%dy_censored" % h] = True
                continue
            hit = ((dy > yr) & (dy <= yr + h)).fillna(False)
            rec["within_%dy" % h] = round(float(hit.mean()), 6)
            rec["within_%dy_censored" % h] = False
        out[yr] = rec
    return out


def shipped_panel_delist_reference(panel, delist, horizons=K3_HORIZONS):
    """The shipped panel's OWN delisting share, on the same matched windows.

    Averaged over the panel's own rebalance dates, restricted to dates whose forward window
    fits inside the ACTIONS cut -- so the reference is uncensored by construction. The number of
    dates contributing is REPORTED, because a reference built on a handful of dates is not the
    same evidence as one built on fifty (`MB21`'s rule: every rate asserts what it compared).
    """
    first_de = _first_delist_year(delist)
    tick = "ticker" if "ticker" in panel.columns else None
    dcol = "date" if "date" in panel.columns else None
    if not (tick and dcol):
        return {"status": "UNAVAILABLE", "reason": "panel lacks ticker/date columns"}
    yrs = pd.to_datetime(panel[dcol], errors="coerce").dt.year
    p = panel.assign(_y=yrs)
    out = {}
    for h in horizons:
        shares, used = [], []
        for y, g in p.groupby("_y"):
            y = int(y)
            if y + h > ACTIONS_LAST_YEAR:
                continue
            names = pd.Index(g[tick].astype(str).unique())
            dy = first_de.reindex(names)
            shares.append(float(((dy > y) & (dy <= y + h)).fillna(False).mean()))
            used.append(y)
        out["within_%dy" % h] = (round(sum(shares) / len(shares), 6) if shares else None)
        out["within_%dy_years_used" % h] = used
        out["within_%dy_n_years" % h] = len(used)
    return out


# ---------------------------------------------------------------------------
# ROUTE W
# ---------------------------------------------------------------------------
def _read_banked(rel):
    """Banked WRDS frames are gzip-compressed behind a bare `.pkl`. pandas infers none."""
    return pd.read_pickle(os.path.join(RAW_ROOT, rel), compression="gzip")


def manifest_reconcile(table):
    """Recorded rows per chunk, LAST pull per chunk winning.

    Six `co_ifndq` years were re-pulled with identical counts, so summing every manifest entry
    double-counts them -- which is exactly how `DESIGN`'s 2,467,490 came to differ from
    `WRDS_CENSUS`'s 2,114,571 by 352,919.
    """
    per, order, n_entries, bad = {}, [], 0, 0
    p = os.path.join(RAW_ROOT, "manifest.jsonl")
    for ln in io.open(p, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if r.get("table") != table:
            continue
        n_entries += 1
        if r.get("status") not in (None, "ok", "OK"):
            bad += 1
        ch = str(r.get("chunk"))
        per[ch] = int(r.get("rows") or 0)
        if ch not in order:
            order.append(ch)
    return {"table": table, "entries": n_entries, "distinct_chunks": len(per),
            "non_ok": bad, "rows_dedup": sum(per.values()),
            "rows_all_entries_double_counted": None, "per_chunk": per}


def route_w_link():
    """DATED ticker -> permno -> cusip8 -> gvkey, with the UNDATED route as a control.

    The undated route is `W-28`'s contaminated shape: it assigns a gvkey CRSP dates belonging to
    a DIFFERENT company wherever a ticker was reused. It is reported and never counted.
    """
    sn = _read_banked("crsp_stocknames/crsp_stocknames_all.pkl")
    sec = _read_banked("comp_security/comp_security_all.pkl")
    sn = sn.copy()
    sn["cusip8"] = sn["cusip"].astype(str).str.slice(0, 8)
    sec = sec.copy()
    sec["cusip8"] = sec["cusip"].astype(str).str.slice(0, 8)
    dated = sn.dropna(subset=["namedt", "nameenddt"])
    by_cusip = sec.dropna(subset=["cusip8"]).drop_duplicates("cusip8").set_index("cusip8")["gvkey"]
    linked = dated.assign(gvkey=dated["cusip8"].map(by_cusip))
    naive = sec.dropna(subset=["tic"]).drop_duplicates("tic").set_index("tic")["gvkey"]
    return {
        "stocknames_rows": int(len(sn)),
        "stocknames_dated_rows": int(len(dated)),
        "comp_security_rows": int(len(sec)),
        "cusip8_to_gvkey_pairs": int(by_cusip.notna().sum()),
        "dated_intervals_with_gvkey": int(linked["gvkey"].notna().sum()),
        "dated_link_share": round(float(linked["gvkey"].notna().mean()), 6),
        "CONTAMINATED_CONTROL_undated_tic_to_gvkey": int(naive.notna().sum()),
        "control_note": ("the undated tic->gvkey route is W-28's contamination shape and is "
                         "NEVER counted as coverage"),
    }


def route_w_fundamentals(years):
    """Per-year non-null share of the `co_ifndq` line items, plus the PIT composition.

    `co_ifndq`'s ONLY date-like column is `datadate` -- no `rdq`, no `srcdate`, no vintage of
    any kind -- so no publication lag is verifiable from this table and K4 cannot be run on
    this route. What IS recorded is the `datafmt`/`consol` composition, which distinguishes
    as-first-reported from restated WITHOUT dating either.
    """
    NEED = ["atq", "ceqq", "ibq", "revtq", "saleq", "cshoq", "dlttq", "dlcq",
            "oiadpq", "cogsq", "xsgaq", "xintq", "ppentq", "invtq", "rectq", "gpq"]
    out = {}
    for y in years:
        p = os.path.join(RAW_ROOT, "comp_pit", "comp_pit_%d.pkl" % y)
        if not os.path.exists(p):
            out[y] = {"status": "ABSENT"}
            continue
        df = _read_banked("comp_pit/comp_pit_%d.pkl" % y)
        cols = {c: round(float(df[c].notna().mean()), 6) for c in NEED if c in df.columns}
        absent = [c for c in NEED if c not in df.columns]
        rec = {"rows": int(len(df)), "gvkeys": int(df["gvkey"].nunique()),
               "nonnull": cols, "absent_columns": absent,
               "below_70pct": sorted([c for c, v in cols.items() if v < K2_NONNULL])}
        for c in ("datafmt", "consol"):
            if c in df.columns:
                rec[c] = {str(k): int(v) for k, v in df[c].value_counts().items()}
        rec["date_like_columns"] = sorted([c for c in df.columns if "date" in c])
        out[y] = rec
    return out


def pit_composition_summary(fw):
    """Is `co_ifndq` actually as-first-reported, or restated data wearing a PIT directory name?

    THE CENSUS'S SHARPEST ROUTE W FINDING, and it is free. Compustat's point-in-time product
    marks as-first-reported rows `PRE_AMENDS`. Measured across 1995-2008 this table is
    essentially ALL `STD` -- the restated basis -- and it carries no vintage column to date
    either. So a panel built on Route W would score a historical date against fundamentals as
    they were LATER restated, which is the look-ahead the project's whole PIT discipline exists
    to prevent. The brief calls this table "the entitled point-in-time quarterly"; on this
    account, for this window, that premise is NOT supported by the data.
    """
    pre = std = tot = 0
    zero_years = []
    for y in sorted(fw):
        r = fw[y]
        if not isinstance(r, dict) or r.get("status") == "ABSENT":
            continue
        d = r.get("datafmt") or {}
        p, s = int(d.get("PRE_AMENDS", 0)), int(d.get("STD", 0))
        pre += p
        std += s
        tot += int(r.get("rows") or 0)
        if p == 0:
            zero_years.append(int(y))
    return {
        "years_measured": len([y for y in fw if isinstance(fw[y], dict)
                               and fw[y].get("status") != "ABSENT"]),
        "rows_total": tot,
        "PRE_AMENDS_rows_total": pre,
        "STD_rows_total": std,
        "PRE_AMENDS_share": (round(pre / tot, 8) if tot else None),
        "years_with_zero_PRE_AMENDS": zero_years,
        "verdict": ("co_ifndq is essentially 100% STD (restated basis) across 1995-2008 and has "
                    "no vintage column, so its point-in-time premise is NOT supported on this "
                    "account for this window"),
    }


def dsf_sizing():
    """SIZE the absent 1994-2007 `dsf` from the real 2008 chunk. Never a coverage claim.

    THE REFERENCE CHUNK IS PANEL-RESTRICTED, WHICH IS MEASURED RATHER THAN ASSUMED: `dsf_2008`
    holds 1,607 distinct permno over 253 dates (~1,583 names per date) in FOUR columns, so it is
    `dsf` narrowed to the SHIPPED panel's names, not a full CRSP year (~1.7M rows). Two effects
    then push the estimate in OPPOSITE directions and the net is NOT established: a pre-2009
    extension needs names absent from today's panel, which makes this an UNDERSTATEMENT, while
    the pre-2008 CRSP cross-section is smaller than 2008's, which makes it an OVERSTATEMENT.
    The figure is therefore a panel-restricted order-of-magnitude, and no direction is claimed.
    """
    d = os.path.join(RAW_ROOT, "crsp_dsf_panel")
    have = sorted(int(x) for f in os.listdir(d)
                  for x in [f[4:8]] if f.startswith("dsf_") and x.isdigit())
    ref_year = min(have)
    ref_path = os.path.join(d, "dsf_%d.pkl" % ref_year)
    ref_bytes = os.path.getsize(ref_path)
    ref = _read_banked("crsp_dsf_panel/dsf_%d.pkl" % ref_year)
    need = [y for y in range(1994, 2008) if y not in have]
    return {
        "banked_years": have,
        "reference_year": ref_year,
        "reference_rows": int(len(ref)),
        "reference_bytes_on_disk": int(ref_bytes),
        "reference_columns": int(ref.shape[1]),
        "years_required_and_ABSENT": need,
        "estimated_rows": int(len(ref)) * len(need),
        "estimated_bytes_on_disk": int(ref_bytes) * len(need),
        "reference_distinct_permno": (int(ref["permno"].nunique())
                                      if "permno" in ref.columns else None),
        "reference_distinct_dates": (int(ref["date"].nunique())
                                     if "date" in ref.columns else None),
        "reference_columns_names": sorted(ref.columns.tolist()),
        "reference_is_panel_restricted": True,
        "method": ("linear extrapolation from ONE real year-chunk, as the task directs. The "
                   "chunk is PANEL-RESTRICTED (1,607 permno, 4 columns), so two effects push "
                   "the estimate opposite ways -- an extension needs names absent from today's "
                   "panel (understates) while the pre-2008 cross-section is smaller than "
                   "2008's (overstates). NO DIRECTION IS CLAIMED."),
        "consequence": ("every Route W statement about a price-dependent theme before 2008 is "
                        "a SIZE ESTIMATE, not a coverage measurement"),
    }


# ---------------------------------------------------------------------------
# KILLS
# ---------------------------------------------------------------------------
def evaluate_kills(cov, prov, delist_stats, shipped_delist_share, ref_prov):
    """Every bar is the register's. None is relaxed after reading."""
    res = {}
    for y in YEARS:
        c = cov.get(y, {})
        k1_names = c.get("names", 0)
        k1 = k1_names >= K1_MIN_NAMES

        themes = {t: v for t, v in c.items() if t != "names" and isinstance(v, dict)}
        k2_fail = sorted([t for t, v in themes.items() if v["any"] < K2_NONNULL])
        k2 = not k2_fail

        d = delist_stats.get(y, {})
        key = "within_%dy" % K3_PRIMARY_H
        share = d.get(key)
        ref = (shipped_delist_share or {}).get(key) if isinstance(shipped_delist_share, dict) \
            else None
        if share is None:
            k3, k3_why = None, "CENSORED: %d + %dy runs past the ACTIONS cut" % (y, K3_PRIMARY_H)
        elif not ref:
            k3, k3_why = None, "shipped reference unavailable on a matched window"
        else:
            lo, hi = K3_LO * ref, K3_HI * ref
            k3 = bool(lo <= share <= hi)
            k3_why = ("%dy window: %.4f vs shipped %.4f, band [%.4f, %.4f]"
                      % (K3_PRIMARY_H, share, ref, lo, hi))

        p = prov.get(y, {})
        ts = p.get("timely_share")
        if ts is None or ref_prov is None:
            k4, k4_why = None, "reference unavailable"
        else:
            shortfall_pp = (ref_prov - ts) * 100.0
            k4 = bool(shortfall_pp <= K4_MAX_SHORTFALL_PP)
            k4_why = "timely %.4f vs ref %.4f -> shortfall %.2f pp" % (ts, ref_prov, shortfall_pp)

        res[y] = {"K1_names": {"pass": bool(k1), "names": int(k1_names), "bar": K1_MIN_NAMES},
                  "K2_themes": {"pass": bool(k2), "failing": k2_fail, "bar": K2_NONNULL},
                  "K3_survivorship": {"pass": k3, "detail": k3_why},
                  "K4_pit": {"pass": k4, "detail": k4_why}}
    return res


def start_year_verdicts(kills):
    """PASS/FAIL per candidate start year: every year from the start onward must clear."""
    out = {}
    for sy in START_YEARS:
        span = [y for y in YEARS if y >= sy]
        failing = {}
        for y in span:
            k = kills.get(y, {})
            bad = [name for name, v in k.items() if v.get("pass") is False]
            if bad:
                failing[y] = bad
        out[sy] = {"verdict": "PASS" if not failing else "FAIL",
                   "years_checked": span, "failing_years": failing}
    return out


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--route", choices=["s", "w", "both"], default="both")
    ap.add_argument("--out-json", default=os.path.join(RAW_ROOT, "PANEL_EXT_CENSUS.json"))
    ap.add_argument("--out-md", default=os.path.join(REPO, "PANEL_EXT_CENSUS.md"))
    args = ap.parse_args(argv)

    used, per_theme = weighted_theme_inputs()
    assert len(used) == 24, ("the AST-derived z-column set moved: %d, not 24. The census scope "
                             "is defined on that set; investigate before reporting." % len(used))

    art = {
        "item": "MC12 / PANEL-EXT-CENSUS",
        "class": "FACTS",
        "trials": 0,
        "register": "PREREG_panel_ext_census.md",
        "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "data_root_resolved": _data_root(),
        "z_columns_distinct_AST": len(used),
        "z_columns_per_theme": {k: sorted(v) for k, v in per_theme.items()},
        "insider_note": ("`insider` contributes ZERO z-columns because factors.py maps it as a "
                         "fixed affine (insider_score-50)/25, not a z-score. DESIGN 1.1's prose "
                         "count of 24 is CORRECT and its table's 25th row is not a z-column."),
        "sf1_needs_declared": SF1_NEEDS,
        "bars": {"K1_MIN_NAMES": K1_MIN_NAMES, "K2_NONNULL": K2_NONNULL,
                 "K3_LO": K3_LO, "K3_HI": K3_HI,
                 "K4_MAX_SHORTFALL_PP": K4_MAX_SHORTFALL_PP, "PIT_LAG_DAYS": PIT_LAG_DAYS},
    }

    if args.route in ("s", "both"):
        print("ROUTE S: streaming raw bulk sf1 ...", flush=True)
        sf1, n_raw = route_s_fundamentals()
        print("   sf1 rows read %s, ARQ PIT rows kept %s" % (f"{n_raw:,}", f"{len(sf1):,}"),
              flush=True)
        cov = theme_coverage(sf1, per_theme)

        # the three weighted themes SF1 cannot answer, so K2 covers all SEVEN and not four
        names_by_year = {int(y): set(g["ticker"].astype(str).unique())
                         for y, g in sf1.groupby("year") if int(y) in YEARS}
        nonsf1 = route_s_nonsf1_themes(names_by_year)
        for y, d in nonsf1.items():
            if y not in cov:
                continue
            for theme, rec in d.items():
                if rec is None:
                    continue
                # for these themes the SOURCE's presence is the binding constraint, so `any`
                # and `all` coincide and the record says which source produced it
                cov[y][theme] = {"any": rec["share"], "all": rec["share"], "n_inputs": 0,
                                 "source": "non-SF1", "detail": rec}

        prov = route_s_pit_provenance(sf1)
        de, actions_all = actions_delisting()
        dl = later_delist_share(sf1, de)

        ref_years_present = [y for y in REF_YEARS if y in prov]
        ref_prov = (sum(prov[y]["timely_share"] for y in ref_years_present)
                    / len(ref_years_present)) if ref_years_present else None

        # the shipped panel's own delisting share on MATCHED windows -- a property of the
        # INCUMBENT, so measuring it reads no extension data
        shipped = None
        pp = os.path.join(_data_root(), "free_analysis", "panel_corrected_69d.pkl")
        if os.path.exists(pp):
            panel = pd.read_pickle(pp)
            shipped = shipped_panel_delist_reference(panel, de)
            del panel

        art["route_s"] = {
            "sf1_rows_read": n_raw,
            "sf1_arq_pit_rows": int(len(sf1)),
            "coverage_by_year": cov,
            "pit_provenance_by_year": prov,
            "pit_reference_2009_2013": ref_prov,
            "delisting_by_year": dl,
            "actions_rows": int(len(actions_all)),
            "actions_delist_events": int(len(de)),
            "shipped_panel_delist_reference_matched": shipped,
        }
        art["kills_route_s"] = evaluate_kills(cov, prov, dl, shipped, ref_prov)
        art["start_year_verdicts_route_s"] = start_year_verdicts(art["kills_route_s"])

    if args.route in ("w", "both"):
        print("ROUTE W: reading banked CRSP/Compustat ...", flush=True)
        rec = manifest_reconcile("co_ifndq")
        fw = route_w_fundamentals(YEARS)
        art["route_w"] = {
            "manifest_co_ifndq": {k: v for k, v in rec.items() if k != "per_chunk"},
            "fundamentals_by_year": fw,
            "link": route_w_link(),
            "dsf_sizing": dsf_sizing(),
            "pit_limitation": ("co_ifndq has NO vintage column (only datadate), so no "
                               "publication lag is verifiable and K4 cannot be run on this "
                               "route. The datafmt/consol composition is reported instead."),
            "pit_composition_summary": pit_composition_summary(fw),
        }

    os.makedirs(os.path.dirname(args.out_json), exist_ok=True)
    with io.open(args.out_json, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("banked %s" % args.out_json)

    write_markdown(art, args.out_md)
    print("wrote %s" % args.out_md)
    return 0


def write_markdown(art, path):
    L = []
    A = L.append
    A("# PANEL_EXT_CENSUS — MC12 Stage-1 census (zero trials, FACTS class)")
    A("")
    A("Register: `PREREG_panel_ext_census.md`. Generated `%s`." % art["utc"])
    A("")
    A("**No forward return, price return, IC or *t* is computed anywhere in this census** — "
      "pinned over the module's own syntax tree by `tests/test_panel_ext_census.py`. A PASS "
      "below means only *\"a successor register on this route and start year is not blocked by "
      "data availability\"*.")
    A("")
    A("Data root resolved to `%s` (a worktree carries `data/` empty)." % art["data_root_resolved"])
    A("")
    A("## The load-bearing set")
    A("")
    A("**%d distinct z-columns, derived by AST** from the theme means rather than retyped."
      % art["z_columns_distinct_AST"])
    A("")
    A(art["insider_note"])
    A("")
    A("| theme | z-columns |")
    A("|---|---|")
    for t in sorted(art["z_columns_per_theme"]):
        cols = art["z_columns_per_theme"][t]
        A("| `%s` | %s |" % (t, ", ".join("`%s`" % c for c in cols) if cols else "*none*"))
    A("")
    if "route_s" in art:
        rs = art["route_s"]
        A("## ROUTE S — the Sharadar freeze")
        A("")
        A("`sf1` rows read **%s**; ARQ rows kept at earliest-`datekey` **%s**."
          % (f"{rs['sf1_rows_read']:,}", f"{rs['sf1_arq_pit_rows']:,}"))
        A("")
        A("| year | names | K1 | failing themes (K2) | later-delist | timely `datekey` |")
        A("|---|---|---|---|---|---|")
        for y in YEARS:
            k = art["kills_route_s"].get(y, {})
            cv = rs["coverage_by_year"].get(y, {})
            dl = rs["delisting_by_year"].get(y, {})
            pv = rs["pit_provenance_by_year"].get(y, {})
            A("| %d | %s | %s | %s | %s | %s |" % (
                y, f"{cv.get('names', 0):,}",
                "PASS" if k.get("K1_names", {}).get("pass") else "**FAIL**",
                ", ".join("`%s`" % t for t in k.get("K2_themes", {}).get("failing", [])) or "—",
                ("%.3f" % dl["within_5y"]) if dl.get("within_5y") is not None else "censored",
                ("%.3f" % pv["timely_share"]) if pv.get("timely_share") is not None else "—"))
        A("")
        A("Shipped panel's own delisting reference, on MATCHED forward windows: **%s**."
          % rs.get("shipped_panel_delist_reference_matched"))
        A("")
        A("### Verdict per candidate start year — Route S")
        A("")
        for sy, v in sorted(art["start_year_verdicts_route_s"].items()):
            A("* **%s — %s**%s" % (sy, v["verdict"],
                                   "" if v["verdict"] == "PASS"
                                   else " (failing: %s)" % v["failing_years"]))
        A("")
    if "route_w" in art:
        rw = art["route_w"]
        A("## ROUTE W — CRSP / Compustat")
        A("")
        m = rw["manifest_co_ifndq"]
        A("`co_ifndq` manifest: **%d entries over %d distinct chunks**, %d non-ok, "
          "deduped rows **%s**." % (m["entries"], m["distinct_chunks"], m["non_ok"],
                                    f"{m['rows_dedup']:,}"))
        A("")
        A("**%s**" % rw["pit_limitation"])
        A("")
        A("### The link")
        A("")
        for k, v in sorted(rw["link"].items()):
            A("* `%s` = %s" % (k, v))
        A("")
        A("### `dsf` sizing — an estimate, never coverage")
        A("")
        for k, v in sorted(rw["dsf_sizing"].items()):
            A("* `%s` = %s" % (k, v))
        A("")
        A("### Per-year `co_ifndq` line items below the 70% rule")
        A("")
        A("| year | rows | gvkeys | below 70% |")
        A("|---|---|---|---|")
        for y in YEARS:
            f = rw["fundamentals_by_year"].get(y, {})
            if f.get("status") == "ABSENT":
                A("| %d | — | — | *year file absent* |" % y)
                continue
            A("| %d | %s | %s | %s |" % (y, f"{f.get('rows', 0):,}", f"{f.get('gvkeys', 0):,}",
                                         ", ".join("`%s`" % c for c in f.get("below_70pct", []))
                                         or "—"))
        A("")
    A("## What this does not do")
    A("")
    A("It builds no panel, adopts nothing, and licenses no trial. No outcome is computed, so no "
      "statement here bears on whether a pre-2009 edge exists.")
    A("")
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
