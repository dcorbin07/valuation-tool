# -*- coding: utf-8 -*-
"""`INSIDER-CLUSTER` — the event construction: clustered OPPORTUNISTIC insider buying.

Don's ruling, `DECISIONS.md` 2026-10-13: *"clustered insider buying tested in SHARES (F-15's
options form is dead on arithmetic)"*. The scout's `a8c1a75` computed why the call cannot work —
it needs 4.85% of premium at IV 0.30 against a published drift near 1.64% over 60 days, short by
3.0× — and recommended the stock side, where this project's own measured equity cost (`B11`, 33.4
bps one way) leaves 1.64% netting +0.97%.

**THE CLUSTER IS DEFINED FROM THE LITERATURE, IN THIS MODULE, BEFORE ANY OUTCOME IS READ.** No
forward return is computed anywhere in this file; the arm computes those, so the kill pass can run
and be read in its own invocation without having seen an outcome (`O10`'s process defect).

THE DEFINITION, STATED ONCE
--------------------------------------------------------------------------------------------
1. **Every row is classified ROUTINE / OPPORTUNISTIC by `insider_routine.classify`**, which is
   Cohen-Malloy-Pomorski's published three-consecutive-year rule and is **called, never
   re-implemented** (`B7`). It is classified on the **FULL file**, not on the purchase subset:
   CMP classify an insider's habit from *any* trade, and `MB20` measured that establishing the
   pattern from a truncated history **under-counts routine** (36.76% against the full-history
   37.95%) because adding rows can only ADD routine labels.
2. **An open-market purchase is `transactioncode == "P"`.** A row whose code is **MISSING is
   COUNTED AND SKIPPED** and is never read as "not a purchase" — `MB20`'s correction, and the
   scout re-measured the share at 28.52% on the `data/backtest` export. **Measured here on the
   freeze's own raw file it is 29.42% of 11,570,121 rows**, and that difference is itself a
   finding (see `scripts/insider_cluster_census.py`).
3. **A CLUSTER EVENT is `k` or more DISTINCT `ownername` filing an opportunistic open-market
   purchase in the same ticker inside a `WINDOW_DAYS` calendar window**, dated at the **LAST**
   filing in the window — the first date on which the whole cluster is public. `k = 2` primary,
   `k = 3` sensitivity.
4. **THE EVENT IS DATED ON `filingdate`, NOT `transactiondate`.** A trade is not public
   information until it is filed, and a signal dated on the trade date would read as if the market
   could see a Form 4 before it existed. The ROUTINE habit, by contrast, is measured in
   `transactiondate` months, because the habit is a property of when the insider TRADES —
   `insider_routine`'s own rule, unchanged.
5. **ONE EVENT PER CLUSTER.** After an event fires for a ticker, the next requires a window whose
   last filing is strictly after the previous event date, so a long run of filings cannot re-fire
   the same cluster many times. Without this a single busy quarter at one name would dominate the
   event count and the cluster-robust SE would be absorbing a structure the design created.

WHAT IS GENUINELY NEW HERE, AND WHAT IS NOT — stated so the result is not over-read
--------------------------------------------------------------------------------------------
**NOT NEW:** that the `insider` THEME is weak (IC *t* **-0.24** on the published panel); that
re-filtering the theme's rows cannot move the blend (`MB20`: the filter moved the score on 54.83%
of scored cells and the composite's per-date rank correlation between arms was **0.9774**, top-25
overlap 22.65 of 25, and it ADOPTED NOTHING); and that dip × insider open-market buying was
**NULL** (`V6-B` arm 3, +1.147pp/yr full sample with a late half of **+0.011pp**).

**NEW:** none of those tested a **standalone event signal**. `MB20` re-scored a theme that sits at
1/7 weight; `V6-B` conditioned on a dip first; the theme's IC is a cross-sectional rank statistic
on a quarterly panel, which `SEARCH_DOCTRINE` §1.4 measures as the weakest space this project has
(80%-power MDE 0.4274-0.5071 SD, *"a merely good new signal is invisible there BY
CONSTRUCTION"*). **This is event time on the daily series, where the same document measures the
MDE an order of magnitude smaller.** So a null here is a different null, and a pass here would not
contradict any of the three.
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd

from . import dipcall as D
from . import insider_routine as IR

# ------------------------------------------------------------------ THE DEFINITION (register §2)
#: Distinct opportunistic purchasers required. PRIMARY, and the sensitivity is declared beside it
#: so neither can be reached for after seeing which passes.
K_PRIMARY = 2
K_SENSITIVITY = 3

#: The calendar window the filings must fall inside. 30 days is one filing month — Form 4 is due
#: within two business days of the trade, so a 30-day window on FILING dates groups insiders who
#: acted inside roughly the same month, which is the unit Cohen-Malloy-Pomorski's monthly
#: portfolios are formed on.
WINDOW_DAYS = 30

PURCHASE_CODE = "P"

#: Named states, never folded into each other. `S10`'s failure mode is a data-availability screen
#: wearing a behavioural screen's name.
CODE_MISSING = "CODE_MISSING"


def sf2_zip(root: Optional[str] = None) -> str:
    """The FREEZE's own raw SF2, and NOT `data/backtest/insiders.csv`.

    **The charter's reason, now measured on the insider file itself.**
    `sharadar_freeze._fresh_universe` ranks the TICKERS snapshot by TODAY's `scalemarketcap` and
    keeps the top 3,000, so `data/backtest` is *the names that are biggest in 2026* — selection on
    a present-day property. On the insider file that costs **11,570,121 raw rows against the
    6,688,777 the scout measured on the export, and 682,435 open-market purchase rows against
    163,653 — 4.17×.** Using the export would have scored the cluster signal on a universe
    selected by its own future size.
    """
    r = root or D.data_root()
    p = os.path.join(r, "backtest_freeze_2026-10", "raw", "SHARADAR_SF2_2026-10-04.zip")
    if not os.path.isfile(p):
        raise SystemExit("REFUSING: no raw SF2 at %s" % p)
    return p


def load_sf2(root: Optional[str] = None, chunksize: int = 2_000_000) -> pd.DataFrame:
    """`ticker`, `ownername`, `filingdate`, `transactiondate`, `transactioncode` — all rows.

    Every row is loaded because the ROUTINE habit is established from the whole history (rule 1).
    Filtering to purchases first would under-count routine and so OVER-count opportunistic, which
    is the flattering direction for this register's own hypothesis.
    """
    import io
    import zipfile
    cols = ["ticker", "ownername", "filingdate", "transactiondate", "transactioncode"]
    z = zipfile.ZipFile(sf2_zip(root))
    name = z.namelist()[0]
    out = []
    with z.open(name) as f:
        for ch in pd.read_csv(io.TextIOWrapper(f, encoding="utf-8"), usecols=cols,
                              chunksize=chunksize, low_memory=False):
            out.append(ch)
    df = pd.concat(out, ignore_index=True)
    for c in ("ticker", "ownername", "filingdate", "transactiondate", "transactioncode"):
        df[c] = df[c].astype("string")
    return df


def code_census(df: pd.DataFrame) -> dict:
    """What the code column can and cannot say. COUNTED, never assumed."""
    c = df["transactioncode"]
    n = len(df)
    miss = int(c.isna().sum())
    return {
        "rows": n,
        "code_missing": miss,
        "code_missing_share": (miss / n) if n else float("nan"),
        "purchase_rows": int((c == PURCHASE_CODE).sum()),
        "SKIP_RULE": ("a row with no transactioncode is COUNTED AND SKIPPED and is never read as "
                      "'not a purchase' -- MB20's correction"),
    }


def label_rows(df: pd.DataFrame) -> pd.Series:
    """ROUTINE / OPPORTUNISTIC / UNCLASSIFIABLE, from the shipped classifier."""
    return IR.classify(df, ticker_col="ticker", owner_col="ownername",
                       date_col="transactiondate")


def prior_year_presence(df: pd.DataFrame) -> np.ndarray:
    """Was the `(ticker, owner)` pair OBSERVABLE in each of the two prior calendar years?

    **THIS IS THE STRICT OPPORTUNISTIC CONDITION AND IT IS NOT A REFINEMENT, IT IS THE DIFFERENCE
    BETWEEN A BEHAVIOURAL SCREEN AND A DATA-AVAILABILITY ONE.** `insider_routine.classify` labels
    a pair ROUTINE only when it traded in the same month in each of the two prior years, so a pair
    with no prior years at all is OPPORTUNISTIC **by default** — it is not that the insider broke a
    habit, it is that no habit could have been observed.

    Measured before any outcome existed (`scripts/insider_cluster_census2.py`): **only 34.32% of
    the 589,322 opportunistic open-market purchase rows have both prior years present**, so
    **65.68% of the label is "no history to be routine with"**. On `data/backtest`'s narrower,
    older population `MB20` measured the routine share of classifiable rows at **60.47%**; on the
    freeze's full file it is **33.86%**, and that gap is exactly what a wider and younger universe
    produces. Leaving it unmeasured would have made the arm `S10`'s failure mode — a screen wearing
    another screen's name — which is this project's most repeated defect.

    Computed as a mask ALONGSIDE the shipped classifier rather than by editing it (`B7`).
    """
    tk = df["ticker"].astype("string")
    ow = df["ownername"].astype("string")
    td = pd.to_datetime(df["transactiondate"], errors="coerce")
    ok = (tk.notna() & ow.notna() & td.notna()).to_numpy(dtype=bool)
    y = td.dt.year
    seen = set(zip(tk[ok].tolist(), ow[ok].tolist(),
                   y[ok].astype("int64").tolist()))
    t_l, o_l, y_l = tk.to_numpy(), ow.to_numpy(), y.to_numpy()
    out = np.zeros(len(df), dtype=bool)
    for i in np.flatnonzero(ok):
        yy = int(y_l[i])
        out[i] = ((t_l[i], o_l[i], yy - 1) in seen) and ((t_l[i], o_l[i], yy - 2) in seen)
    return out


def opportunistic_purchases(df: pd.DataFrame, labels: pd.Series,
                            strict: bool = True) -> pd.DataFrame:
    """The rows a cluster may be built from: OPPORTUNISTIC, code present and equal to `P`.

    `strict=True` additionally requires `prior_year_presence` — the register's PRIMARY, for the
    reason that function documents. `strict=False` is the declared SENSITIVITY and is the broad
    label `MB20`'s classifier returns on its own. **The default is the strict form so a caller
    that forgets the argument gets the conservative one** — `O-1`'s lesson that a guard whose
    default is off is a guard a new caller silently loses.

    Returns `ticker`, `ownername`, `filingdate` only — nothing an outcome could be read from.
    """
    code = df["transactioncode"]
    # `.fillna(False)` IS THE SKIP, AND IT IS EXPLICIT BECAUSE PANDAS REFUSED TO GUESS.
    # Under the `string` dtype a missing code is `pd.NA`, so `code == "P"` is a NULLABLE boolean
    # and `.to_numpy(dtype=bool)` RAISES rather than coercing -- which is the correct refusal and
    # is the `blank-code counter` family one level up: `MA-final-batch` recorded a check that read
    # **0** blank codes on a column holding 1,544,490 of them, because `NA` compares False against
    # every literal and nothing raised. Here the fill is the register's rule rather than a
    # convenience: a row with no code is NOT a purchase-or-not, it is UNKNOWN, it is counted by
    # `code_census` and it is excluded from the event set. Writing it out means a future reader
    # cannot mistake the coercion for an assumption that a blank is a sale.
    is_buy = (code == PURCHASE_CODE).fillna(False).to_numpy(dtype=bool)
    keep = (labels.to_numpy() == IR.OPPORTUNISTIC) & is_buy
    if strict:
        keep = keep & prior_year_presence(df)
    out = df.loc[keep, ["ticker", "ownername", "filingdate"]].copy()
    out = out.dropna(subset=["ticker", "ownername", "filingdate"])
    out["filingdate"] = out["filingdate"].astype(str).str.slice(0, 10)
    return out.sort_values(["ticker", "filingdate"]).reset_index(drop=True)


def cluster_events(buys: pd.DataFrame, k: int = K_PRIMARY,
                   window_days: int = WINDOW_DAYS) -> pd.DataFrame:
    """`ticker`, `date`, `n_insiders`, `window_lo` — one row per cluster event (rules 3 and 5).

    Dated at the LAST filing in the window. A fresh event requires its last filing to be strictly
    after the previous event's date for that ticker, so one cluster fires once.
    """
    if not len(buys):
        return pd.DataFrame(columns=["ticker", "date", "n_insiders", "window_lo"])
    rows = []
    w = pd.Timedelta(days=int(window_days))
    for tk, g in buys.groupby("ticker", sort=True):
        d = pd.to_datetime(g["filingdate"], errors="coerce")
        ow = g["ownername"].astype(str).to_numpy()
        ok = d.notna().to_numpy()
        d = d[ok].to_numpy()
        ow = ow[ok]
        if len(d) < k:
            continue
        order = np.argsort(d, kind="stable")
        d, ow = d[order], ow[order]
        last_fired = None
        for j in range(len(d)):
            lo = d[j] - w
            sel = (d <= d[j]) & (d >= lo)
            names = set(ow[sel])
            if len(names) < k:
                continue
            # A COOLDOWN OF THE WHOLE WINDOW, AND THE FIRST CUT OF THIS LINE WAS A REAL DEFECT
            # CAUGHT BEFORE ANY OUTCOME. It read `d[j] <= last_fired`, which only suppresses a
            # repeat on the SAME day -- so the very next filing re-fired the same cluster, and
            # ISCA came back with 29 insiders on 2008-01-04, 01-07 AND 01-08, one cluster counted
            # about twenty times. The register's rule 5 states the intent correctly (*"a busy
            # quarter at one name cannot re-fire the same cluster"*), so the CODE was wrong
            # against the REGISTER rather than the other way round, which is the only direction
            # in which this is a fix rather than a change of hypothesis.
            #
            # Requiring the next event to sit more than one window after the last means the
            # fired windows cannot overlap, so each cluster contributes exactly once. The
            # correction REDUCES the event count and therefore reduces power -- the direction
            # that makes the design harder, discovered before any outcome existed.
            if last_fired is not None and d[j] <= last_fired + w:
                continue
            rows.append({"ticker": tk, "date": str(pd.Timestamp(d[j]).date()),
                         "n_insiders": len(names),
                         "window_lo": str(pd.Timestamp(lo).date())})
            last_fired = d[j]
    # AN EMPTY RESULT MUST BE AN EMPTY FRAME WITH THE RIGHT COLUMNS, NOT AN EXCEPTION.
    # The guard at the top catches an empty INPUT; this catches an input that simply produced no
    # cluster -- `pd.DataFrame([]).sort_values(["date", ...])` raises `KeyError`, because an empty
    # frame has no columns to sort on. On the real file it never fires (there are always events),
    # so it is LATENT, and a defect neutralised by a coincidence in the data is not handled: the
    # three construction tests that found it are exactly the k=1-insider, out-of-window and
    # strict-excludes-everything cases a caller will eventually hit.
    if not rows:
        return pd.DataFrame(columns=["ticker", "date", "n_insiders", "window_lo"])
    return pd.DataFrame(rows).sort_values(["date", "ticker"]).reset_index(drop=True)
