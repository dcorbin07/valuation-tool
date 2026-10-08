# -*- coding: utf-8 -*-
"""The DATED panel-ticker -> IBES-ticker link, as an INSTRUMENT.

`STAGE1-BATCH1`'s A9 handed this forward: its size-costume kill needs a dated IBES link, and
**`MB15`'s rule is that the instrument is validated BEFORE any hypothesis reads it** -- a census
that probes the names in a brief measures the brief. So this module builds the link and **computes
no outcome statistic of any kind**: no forward return is read, no signal is scored, no arm exists.
Pinned by test.

**NO WRDS CONNECTION IS NEEDED OR MADE.** `ibes_id`, `ibes_statsum_epsus` (51 chunks) and the
actuals are already on `D:\\wrds` from the 2026-08-24 pull, and `crsp_stocknames` with them. The
one-attempt-per-session rule (`DECISIONS.md` 2026-10-04) is therefore not engaged at all, which is
the safest outcome available to this item.

**WHY DATED IS THE WHOLE POINT.** `W-3b` measured an UNDATED ticker join contaminating at **17.7%**
and `W-28` measured an undated `gvkey` route assigning one company's dates to a DIFFERENT company
on **54 names** -- while clearing a 90% coverage bar the dated route could not. `S25` recorded the
same hazard from the other side: `comp.security` carries **no date columns**, so temporal reuse --
a ticker that was company A in 2009 and is company B today -- **is not observable on that route at
all**. `ibes_id` carries `sdates`, so here it is.

**TWO ROUTES, AND THEIR AGREEMENT IS THE VALIDATION.**

* **Route A, direct:** panel `ticker` -> IBES `oftic`, dated by spans built from consecutive
  `sdates`.
* **Route B, via CRSP:** panel `ticker` -> CRSP `ticker` dated by `namedt`/`nameenddt` -> `ncusip`
  -> IBES `cusip`, dated on both legs.

Neither is the other's control by assumption; the agreement is MEASURED, and a disagreement is
reported rather than resolved by preferring one. That is `W-28`'s discipline (it validated its
naive leg against an independently measured census before trusting the dated one).

**THE LOOK-AHEAD REFUSAL IS THE PROPERTY THIS MODULE EXISTS FOR.** A date PREDATING a ticker's
first span returns `NOT_COVERED` and **never the first span**. Returning it would read as coverage,
produce a plausible IBES ticker, and be undetectable downstream -- the exact defect being removed,
re-introduced by the thing removing it. `S25` pinned this with a positive control so the guard
cannot pass by refusing everything, and so does this.
"""
from __future__ import annotations

import os

import pandas as pd

#: resolution states. A refusal is a RECORD, never a crash and never a silent None -- `S25`'s
#: `UNMAPPED` lesson, and `MB15`'s: a filter that never ran and a filter that ran and found
#: nothing must not read the same.
OK = "OK"
NOT_COVERED = "NOT_COVERED"           # no span contains the date (incl. BEFORE the first)
AMBIGUOUS = "AMBIGUOUS"               # >1 IBES ticker claims this ticker-date
UNMAPPED = "UNMAPPED"                 # the ticker is not in the identifier table at all
STATES = (OK, NOT_COVERED, AMBIGUOUS, UNMAPPED)

#: `D:\wrds` and never the repo: licensed rows never land inside the checkout, where a stray
#: `git add -A` reaches (the rule `wrds_pull` already enforces).
RAW = os.environ.get("VALQUO_WRDS_RAW", "D:\\wrds")


def _read(path):
    """The pull writes gzip-compressed pickles; pandas does not always sniff that from a `.pkl`
    name, and the bare read raises `UnpicklingError: invalid load key, '\\x1f'` -- the gzip magic
    byte. Both forms are tried so a future pull writing uncompressed still loads."""
    try:
        return pd.read_pickle(path, compression="gzip")
    except Exception:                                   # noqa: BLE001
        return pd.read_pickle(path)


def ibes_id(path=None):
    p = path or os.path.join(RAW, "ibes_id", "ibes_id_all.pkl")
    if not os.path.exists(p):
        raise FileNotFoundError(
            "no ibes_id at %s. This module reads the 2026-08-24 pull and makes NO WRDS "
            "connection; if the pull is gone, re-pulling it is a separate item under the "
            "one-attempt-per-session rule." % p)
    return _read(p)


def spans(ids, key="oftic", us_only=False):
    """Dated spans from consecutive `sdates`, **grouped by the IBES `ticker`**.

    `ibes_id` carries a START date per row and NO end date, exactly like `comp.co_hgic` in `S25`.
    A row's span therefore runs to the day before **that IBES TICKER's** next `sdates`, and the
    last row's span is left OPEN -- `None` rather than a far-future sentinel, because a sentinel
    reads as coverage and this is the one place the distinction matters.

    **A DEFECT IN THE FIRST CUT, AND THE FIX IS ALSO THE FINDING.** It grouped by `key` and took
    `shift(-1)` within it. But an exchange ticker is **NOT a unique key in IBES, even at a single
    date**: measured on the real table, `oftic == 'ABT'` is claimed by SIX different IBES tickers
    -- `ABT` (Abbott Labs), `@APL` (Apollo Batteries), `ABT1` (Absolute Software), `@Q69` (Ambit
    Properties), `@82M` (Aqua Bio Tech) -- because companies on different exchanges share one. So
    grouping by `oftic` INTERLEAVED all six: Abbott's span ended the day Apollo Batteries appeared
    in 1993 and a 2009 date landed inside another company's span. Caught by disbelieving an
    agreement rate of 0.742 whose examples returned `@39I` for Abbott.

    Grouped by `ticker`, resolving BY `oftic` is then honestly `AMBIGUOUS` wherever more than one
    company holds that exchange ticker at the date -- a measured property of the identifier rather
    than a defect to hide, and exactly what would silently poison a join on ticker.

    `us_only` filters to `usfirm == 1`, IBES's own US-firm flag. **It DEFAULTS TO FALSE** so the
    ambiguity is reported before it is narrowed away, and the runner reports both readings.

    Rows with no `sdates` are DROPPED AND COUNTED, never dated to the epoch.
    """
    cols = [key, "ticker", "sdates"] + (["usfirm"] if "usfirm" in ids.columns else [])
    d = ids[cols].copy()
    d = d.rename(columns={"ticker": "ibes_ticker"})
    dropped_no_date = int(d["sdates"].isna().sum())
    dropped_no_key = int(d[key].isna().sum())
    dropped_non_us = 0
    if us_only and "usfirm" in d.columns:
        before = len(d)
        d = d[pd.to_numeric(d["usfirm"], errors="coerce") == 1]
        dropped_non_us = before - len(d)
    d = d.dropna(subset=[key, "sdates"])
    d[key] = d[key].astype(str).str.strip().str.upper()
    d["sdates"] = pd.to_datetime(d["sdates"], errors="coerce")
    d = d.dropna(subset=["sdates"])
    d = d.sort_values(["ibes_ticker", "sdates", key]).drop_duplicates(
        ["ibes_ticker", "sdates", key])
    # THE SPAN BELONGS TO THE IBES TICKER, not to the key: it ends the day before THIS TICKER's
    # next record, whoever else happens to claim the same exchange ticker in between.
    d["next_start"] = d.groupby("ibes_ticker")["sdates"].shift(-1)
    d["end"] = d["next_start"] - pd.Timedelta(days=1)
    d = d.drop(columns=["next_start"])
    return d, {"dropped_no_sdates": dropped_no_date, "dropped_no_%s" % key: dropped_no_key,
               "dropped_non_us": dropped_non_us, "us_only": bool(us_only),
               "spans": int(len(d)), "keys": int(d[key].nunique()),
               "ibes_tickers": int(d["ibes_ticker"].nunique()),
               "grouped_by": "ibes_ticker -- NOT by %s, because an exchange ticker is not a "
                             "unique key in IBES even at one date" % key}


def resolve(span_table, key_value, as_of, key="oftic"):
    """The ONE resolution function. Returns `(ibes_ticker_or_None, state)`.

    **A date before the first span returns `NOT_COVERED` and NEVER the first span.** That is the
    property this module exists for; `S25` recorded that returning the first span would read as
    coverage, produce a plausible identifier and be undetectable downstream.
    """
    k = str(key_value).strip().upper()
    g = span_table[span_table[key] == k]
    if g.empty:
        return None, UNMAPPED
    t = pd.Timestamp(as_of)
    hit = g[(g["sdates"] <= t) & (g["end"].isna() | (g["end"] >= t))]
    if hit.empty:
        return None, NOT_COVERED
    names = sorted(set(hit["ibes_ticker"].astype(str)))
    if len(names) > 1:
        return None, AMBIGUOUS
    return names[0], OK


def crsp_names(path=None):
    p = path or os.path.join(RAW, "crsp_stocknames", "crsp_stocknames_all.pkl")
    if not os.path.exists(p):
        return None
    return _read(p)


def crsp_spans(names):
    """CRSP's own dated ticker spans, which already carry BOTH ends."""
    d = names[["ticker", "ncusip", "namedt", "nameenddt", "permno"]].copy()
    d = d.dropna(subset=["ticker", "ncusip", "namedt"])
    d["ticker"] = d["ticker"].astype(str).str.strip().str.upper()
    d["ncusip"] = d["ncusip"].astype(str).str.strip().str.upper()
    d["namedt"] = pd.to_datetime(d["namedt"], errors="coerce")
    d["nameenddt"] = pd.to_datetime(d["nameenddt"], errors="coerce")
    return d.dropna(subset=["namedt"])


def resolve_via_crsp(crsp, cusip_spans, ticker, as_of):
    """Route B: panel ticker -> CRSP dated ncusip -> IBES dated cusip.

    IBES `cusip` is the 8-character form and CRSP's `ncusip` is too, so they are compared at 8
    characters with no truncation of either -- a length mismatch silently matching nothing is the
    shape `E-6` hit when a merge matched ZERO rows in silence.
    """
    t = pd.Timestamp(as_of)
    k = str(ticker).strip().upper()
    g = crsp[(crsp["ticker"] == k) & (crsp["namedt"] <= t)
             & (crsp["nameenddt"].isna() | (crsp["nameenddt"] >= t))]
    if g.empty:
        return None, (UNMAPPED if (crsp["ticker"] == k).sum() == 0 else NOT_COVERED)
    cus = sorted(set(g["ncusip"].astype(str).str[:8]))
    if len(cus) > 1:
        return None, AMBIGUOUS
    return resolve(cusip_spans, cus[0], as_of, key="cusip")


def resolve_many(span_table, cells, key="oftic", key_col="ticker", date_col="date"):
    """Vectorised interval join: every (key, date) cell resolved in one pass.

    **THE SCALAR `resolve` REMAINS THE DEFINITION OF THE RULE.** This is a second implementation
    for scale, and `scripts/ibes_link_validate` REQUIRES it to agree with the scalar on a sample
    before reading anything off it -- `B7`'s rule that a second implementation is proved to match
    rather than assumed to. The per-cell loop it replaces was a full table scan per cell and
    would not have finished.

    Returns a frame with `resolved` and `state`, one row per input cell, in input order.
    """
    c = cells[[key_col, date_col]].copy()
    c.columns = ["_k", "_d"]
    c["_k"] = c["_k"].astype(str).str.strip().str.upper()
    c["_d"] = pd.to_datetime(c["_d"])
    c["_row"] = range(len(c))

    s = span_table.rename(columns={key: "_k"})[["_k", "ibes_ticker", "sdates", "end"]]
    # an OPEN span (no end) must match every later date, so a sentinel is used ONLY inside the
    # comparison and never stored -- `spans()` keeps `end` as NaT deliberately.
    far = pd.Timestamp("2262-04-10")
    m = c.merge(s, on="_k", how="left")
    end = m["end"].fillna(far)
    hit = m["sdates"].notna() & (m["sdates"] <= m["_d"]) & (end >= m["_d"])

    known = set(s["_k"].unique())
    out = pd.DataFrame({"_row": c["_row"].values, "_k": c["_k"].values,
                        "_d": c["_d"].values})
    good = m[hit]
    # a cell with >1 DISTINCT ibes_ticker in force is AMBIGUOUS
    g = good.groupby("_row")["ibes_ticker"].agg(["nunique", "first"])
    out = out.merge(g, left_on="_row", right_index=True, how="left")
    def _state(r):
        if r["_k"] not in known:
            return UNMAPPED
        if r["nunique"] != r["nunique"] or r["nunique"] == 0:      # NaN -> no span in force
            return NOT_COVERED
        return AMBIGUOUS if r["nunique"] > 1 else OK
    out["state"] = out.apply(_state, axis=1)
    out["resolved"] = out.apply(
        lambda r: (r["first"] if r["state"] == OK else None), axis=1)
    return out[["_k", "_d", "resolved", "state"]].rename(
        columns={"_k": key_col, "_d": date_col})


def crsp_cusip_many(crsp, cells, key_col="ticker", date_col="date"):
    """Route B's FIRST leg, vectorised: panel ticker -> CRSP dated ncusip (8 chars)."""
    c = cells[[key_col, date_col]].copy()
    c.columns = ["_k", "_d"]
    c["_k"] = c["_k"].astype(str).str.strip().str.upper()
    c["_d"] = pd.to_datetime(c["_d"])
    c["_row"] = range(len(c))
    s = crsp[["ticker", "ncusip", "namedt", "nameenddt"]].rename(columns={"ticker": "_k"})
    far = pd.Timestamp("2262-04-10")
    m = c.merge(s, on="_k", how="left")
    end = m["nameenddt"].fillna(far)
    hit = m["namedt"].notna() & (m["namedt"] <= m["_d"]) & (end >= m["_d"])
    good = m[hit].copy()
    good["cus8"] = good["ncusip"].astype(str).str[:8]
    g = good.groupby("_row")["cus8"].agg(["nunique", "first"])
    known = set(s["_k"].unique())
    out = pd.DataFrame({"_row": c["_row"].values, "_k": c["_k"].values, "_d": c["_d"].values})
    out = out.merge(g, left_on="_row", right_index=True, how="left")
    def _state(r):
        if r["_k"] not in known:
            return UNMAPPED
        if r["nunique"] != r["nunique"] or r["nunique"] == 0:
            return NOT_COVERED
        return AMBIGUOUS if r["nunique"] > 1 else OK
    out["state"] = out.apply(_state, axis=1)
    out["cusip"] = out.apply(lambda r: (r["first"] if r["state"] == OK else None), axis=1)
    return out[["_k", "_d", "cusip", "state"]].rename(
        columns={"_k": key_col, "_d": date_col})


def resolve_route_b(cusip_spans, crsp_spans_table, cells):
    """Route B: panel ticker -> CRSP cusip (DATED) -> IBES ticker (DATED).

    Returns a frame with `ticker`, `date`, `resolved`, `state` -- one row per input cell, in the
    input's order.

    **ONE IMPLEMENTATION, TWO CALLERS (`B7`).** `IBES-LINK`'s validator produced this join and
    `STAGE1-BATCH2`'s `K0` needs it on a different population (the $10B tier). A second copy of a
    three-step dated join is how two numbers for one question come about -- and the version that
    carries the defect is usually the newer one.

    **LEG-1 REFUSALS MAP THROUGH RATHER THAN BECOMING `UNMAPPED`.** A name CRSP cannot place at a
    date is `NOT_COVERED` or `AMBIGUOUS` for a reason, and collapsing those into one bucket would
    lose the distinction between *"no cusip at this date"* and *"a cusip that IBES does not
    know"*. That distinction is the whole point of a dated route.

    **A CORRECTION CARRIED FORWARD FROM THE VALIDATOR, kept because it is the kind of thing that
    silently returns the wrong shape:** leg 1's output already carries a `ticker` column (the
    PANEL ticker), so renaming `cusip` -> `ticker` produces a DUPLICATE and the slice comes back
    with three columns. The leg-2 input is built EXPLICITLY instead.
    """
    import pandas as pd

    cl = cells[["ticker", "date"]].copy()
    if crsp_spans_table is None:
        return pd.DataFrame({"ticker": cl["ticker"].values, "date": cl["date"].values,
                             "resolved": None, "state": "ROUTE_ABSENT"})

    leg1 = crsp_cusip_many(crsp_spans_table, cl)
    ok1 = leg1[leg1["state"] == OK]
    leg2_in = pd.DataFrame({"ticker": ok1["cusip"].values, "date": ok1["date"].values})
    leg2 = resolve_many(cusip_spans, leg2_in, key="cusip")

    key1 = {(t, pd.Timestamp(d)): st for t, d, st
            in leg1[["ticker", "date", "state"]].itertuples(index=False)}
    got2 = {(t, pd.Timestamp(d)): (v, st) for t, d, v, st
            in leg2[["ticker", "date", "resolved", "state"]].itertuples(index=False)}
    cus = {(t, pd.Timestamp(d)): c for t, d, c
           in ok1[["ticker", "date", "cusip"]].itertuples(index=False)}

    vals, states = [], []
    for t, d in zip(cl["ticker"].values, cl["date"].values):
        kk = (t, pd.Timestamp(d))
        st1 = key1.get(kk, UNMAPPED)
        if st1 != OK:
            vals.append(None)
            states.append(st1)
            continue
        c = cus.get(kk)
        v, st2 = got2.get((c, pd.Timestamp(d)), (None, UNMAPPED))
        vals.append(v)
        states.append(st2)
    return pd.DataFrame({"ticker": cl["ticker"].values, "date": cl["date"].values,
                         "resolved": vals, "state": states})
