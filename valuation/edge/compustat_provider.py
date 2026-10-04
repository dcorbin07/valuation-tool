"""OOS1 -- a Compustat/CRSP provider for the SHIPPED panel builder.

WHY A PROVIDER AND NOT A SECOND BUILDER
    The pre-1999 holdout needs the SAME theme columns the Sharadar panel carries.
    Re-implementing their formulas against Compustat field names would create a second
    definition of the composite -- `B7`'s defect, which this project has paid for repeatedly --
    and it would make the vendor-translation gate UNINTERPRETABLE: a low rank correlation could
    be a vendor difference OR my arithmetic, with no way to tell which.

    So this implements `HistoricalDataProvider`'s interface and nothing else. It maps
    `comp.fundq` and `crsp.dsf` onto the field names the shipped builder reads via `_f(sf1, ...)`,
    and `build_fundamental_panel` computes every signal with the shipped formulas.
    **The only surface that can be wrong here is the field mapping, and Gate B measures exactly
    that.**

THE AVAILABILITY RULE -- THE ONE THING `co_ifndq` COULD NOT SUPPLY
    A fundamental becomes usable on `rdq`, the earnings announcement date. `MC12` measured that
    `co_ifndq` carries NO availability date (only `datadate`) and is ~100% restated, which is why
    `fundq` had to be pulled. Measured on the server: `rdq` is non-null on **835,478 of
    1,234,665** rows in 1972-2008 -- **67.67%** -- BELOW the charter's 70% rule, so a fallback is
    mandatory and is DECLARED HERE rather than chosen after seeing a result: where `rdq` is null
    the row becomes usable at `datadate + FALLBACK_LAG_DAYS`, and **every row carries
    `datekey_source`, so the two populations can never be mixed silently.** That is OOS1's K3
    branch and this is its answer.

UNITS -- THE FAILURE THAT WOULD NOT RAISE
    Compustat quarterly items are in **MILLIONS**; the Sharadar fields the builder reads are in
    **UNITS**. Every mapped level is multiplied by 1e6. Getting this wrong raises nothing: every
    RATIO stays correct and only the LEVELS are 1e6 out, so `size` and the EV ratios would be
    quietly wrong and nothing else would move. Pinned by test.

THE YEAR-TO-DATE TRAP
    `oancfy`, `capxy`, `sstky`, `prstkcy`, `dvy` are **year-to-date**, not quarterly. Q1 is the
    YTD value; Q2-Q4 need `YTD_t - YTD_{t-1}` within the SAME fiscal year, because the counter
    resets at the year boundary. Using the raw figure inflates Q4 by roughly 4x and corrupts
    `fcf`, `fcf_margin`, `accruals` and `neg_issuance`. Converted here, pinned by test.

WHAT IS DELIBERATELY EMPTY, AND WHY THAT IS CORRECT RATHER THAN MISSING
    `insider_history`, `institutional_history` and `grades_history` return **empty lists**.
    Form 4 is not machine-readable before 2003 and 13F coverage on this account starts ~2009, so
    the charter already froze the holdout model at **FIVE themes**. An empty list makes those
    themes absent, which `composite_from_frame` handles by renormalising over the present-weight
    mass -- the shipped convention. **Returning a fabricated neutral value instead would be
    worse: it would look like coverage.**
"""
from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

RAW = r"D:\wrds"

#: Where `rdq` is absent, a fundamental becomes usable this many days after `datadate`.
#: One quarter -- the conventional choice -- DECLARED here rather than tuned later.
FALLBACK_LAG_DAYS = 90

#: Compustat millions -> units.
MM = 1e6

#: CRSP `shrout` is in THOUSANDS.
SHROUT = 1e3

#: The CRSP universe French's factors are built on: ordinary common shares on NYSE/AMEX/Nasdaq.
#: NOT a refinement -- without it the market return carries ADRs, REITs and closed-end funds and
#: Gate A would disagree with French for a reason that is not a defect in this build.
SHRCD_OK = (10, 11)
EXCHCD_OK = (1, 2, 3)

#: `fundq` field -> the Sharadar field name the builder reads. LEVELS in millions; the derived
#: fields (gp, ebitmargin, fcf, debt, ...) are computed in `_sf1_row`.
DIRECT_MM = {
    "atq": "assets",
    "cheq": "cashneq",
    "cogsq": "cor",
    "oiadpq": "ebit",
    "oibdpq": "ebitda",
    "piq": "ebt",
    "ceqq": "equity",
    "xintq": "intexp",
    "icaptq": "invcap",
    "niq": "netinc",
    "ibcomq": "netinccmn",
    "revtq": "revenue",
    "xrdq": "rnd",
    "xsgaq": "sgna",
    "txtq": "taxexp",
}

#: Year-to-date flows, converted to a quarterly flow by `_ytd_to_quarterly`.
YTD = ("oancfy", "capxy", "dvy", "sstky", "prstkcy")


def _num(v):
    """A real number, or None. NaN counts as ABSENT -- the builder's own `_f` convention."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _ytd_to_quarterly(df: pd.DataFrame) -> pd.DataFrame:
    """`YTD_t - YTD_{t-1}` within a fiscal year; Q1 is the YTD value itself.

    Sorted by (gvkey, fyearq, fqtr) and differenced WITHIN (gvkey, fyearq), so the subtraction
    never crosses a year boundary where the YTD counter resets to zero.
    """
    out = df.sort_values(["gvkey", "fyearq", "fqtr"]).copy()
    for c in YTD:
        if c not in out.columns:
            continue
        prev = out.groupby(["gvkey", "fyearq"], sort=False)[c].shift(1)
        # Where no prior quarter of the same fiscal year exists, the YTD value IS the flow.
        out[c + "_q"] = np.where(prev.isna(), out[c], out[c] - prev)
    return out


class CompustatCrspProvider:
    """Serves the shipped builder from `comp.fundq` + `crsp.dsf`, both banked on `D:\\wrds`.

    Loaded once into memory and served per-ticker, because the builder's loop calls
    `price_history(t)` and `fundamentals_history(t)` once per name.

    The provider's "ticker" is the **permno as a string**, not an exchange ticker. A ticker is
    reused across companies over 50 years -- `S25` recorded that temporal reuse is unobservable
    on the undated route -- while a permno is permanent by construction. `self.ticker_of` maps
    permno -> the last ticker seen, for reporting only; nothing joins on it.
    """

    def __init__(self, raw: str = RAW, year_lo: int = 1971, year_hi: int = 2024,
                 usd_only: bool = True, permnos: Optional[set] = None):
        self.raw, self.year_lo, self.year_hi = raw, year_lo, year_hi
        self.usd_only = usd_only
        self.permnos = set(permnos) if permnos else None
        self.notes: Dict[str, object] = {}
        self._px: Optional[pd.DataFrame] = None
        self._sf1: Optional[Dict[str, List[dict]]] = None
        self._link: Optional[pd.DataFrame] = None
        self._series: Dict[str, Tuple[List[str], List[float]]] = {}
        self.ticker_of: Dict[str, str] = {}

    # ------------------------------------------------------------------ loaders
    def _chunks(self, product: str, permno_filter: bool = False) -> List[pd.DataFrame]:
        """Year chunks in `[year_lo, year_hi]`, optionally filtered DURING the load.

        The filter is applied per chunk rather than after `concat` for a measured reason: 16 years
        of `crsp_dsf` is ~32M rows, which materialises to roughly 2 GB before any filter could
        run. Filtering as each chunk lands keeps only the names asked for and makes the Gate B
        build possible on this machine at all.
        """
        parts = []
        for p in sorted(glob.glob(os.path.join(self.raw, product, product + "_*.pkl"))):
            y = os.path.basename(p)[-8:-4]
            if not y.isdigit() or not (self.year_lo <= int(y) <= self.year_hi):
                continue
            d = pd.read_pickle(p, compression="gzip")
            if permno_filter and self.permnos and "permno" in d.columns:
                d = d[d["permno"].isin(self.permnos)]
            if len(d):
                parts.append(d)
        return parts

    def link(self) -> pd.DataFrame:
        """permno <-> dated historical cusip, with the share-code/exchange universe attached.

        `ncusip` is the cusip AS OF the interval; `cusip` is today's. Linking on today's cusip
        attributes a company's modern identity to its historical rows, which is `W-28`'s measured
        misattribution on 54 names. CCM is DENIED on this account, so this dated route is the one
        available.
        """
        if self._link is not None:
            return self._link
        p = os.path.join(self.raw, "crsp_stocknames", "crsp_stocknames_all.pkl")
        sn = pd.read_pickle(p, compression="gzip").copy()
        sn["namedt"] = pd.to_datetime(sn["namedt"], errors="coerce")
        sn["nameenddt"] = pd.to_datetime(sn["nameenddt"], errors="coerce").fillna(
            pd.Timestamp("2100-01-01"))
        sn["cusip8"] = sn["ncusip"].astype(str).str.upper().str.strip().str.slice(0, 8)
        sn = sn[sn["cusip8"].str.len() == 8]
        for c in ("shrcd", "exchcd"):
            sn[c] = pd.to_numeric(sn.get(c), errors="coerce")
        self._link = sn[["permno", "cusip8", "namedt", "nameenddt", "ticker",
                         "shrcd", "exchcd"]].dropna(subset=["permno", "namedt"])
        return self._link

    def prices(self) -> pd.DataFrame:
        """Daily CRSP prices with market cap, filtered to the common-stock universe."""
        if self._px is not None:
            return self._px
        parts = self._chunks("crsp_dsf", permno_filter=True)
        if not parts:
            raise SystemExit("REFUSING: no crsp_dsf chunks in %s for %d-%d -- pull unfinished?"
                             % (self.raw, self.year_lo, self.year_hi))
        d = pd.concat(parts, ignore_index=True)
        d["date"] = pd.to_datetime(d["date"], errors="coerce")
        d = d.dropna(subset=["date", "permno"])
        # CRSP marks a bid/ask AVERAGE with a NEGATIVE price: the sign is a quote-type flag, not
        # a value. Taking it at face value makes a price negative and every ratio built on it
        # flip sign, silently.
        d["px"] = pd.to_numeric(d["prc"], errors="coerce").abs()
        d["shrout"] = pd.to_numeric(d["shrout"], errors="coerce")
        d["ret"] = pd.to_numeric(d["ret"], errors="coerce")
        d["mktcap"] = d["px"] * d["shrout"] * SHROUT
        if self.permnos:
            d = d[d["permno"].isin(self.permnos)]
        # Dated universe filter via the name history.
        lk = self.link()[["permno", "namedt", "nameenddt", "shrcd", "exchcd", "ticker"]]
        d = d.merge(lk, on="permno", how="left")
        d = d[(d["date"] >= d["namedt"]) & (d["date"] <= d["nameenddt"])]
        self.notes["dsf_rows_all"] = int(len(d))
        d = d[d["shrcd"].isin(SHRCD_OK) & d["exchcd"].isin(EXCHCD_OK)]
        self.notes["dsf_rows_universe"] = int(len(d))
        self.notes["dsf_permnos"] = int(d["permno"].nunique())
        self.notes["dsf_span"] = [str(d["date"].min().date()), str(d["date"].max().date())]
        for pn, tk in d.groupby("permno")["ticker"].last().items():
            self.ticker_of[str(int(pn))] = str(tk)
        self._px = d.sort_values(["permno", "date"])
        return self._px

    def _sf1_row(self, r: dict) -> dict:
        """One Compustat quarter mapped onto the Sharadar field names the builder reads.

        `roe`/`roic`/`assetturnover`/`beta` are deliberately ABSENT: `fundamental_panel.DERIVE`
        marks all four as derived, so the builder computes them from the line items. Supplying a
        vendor value would mean the holdout arm and the training arm used different definitions
        of the same signal -- a `B7` split inside the very comparison meant to detect one.
        """
        g = lambda k: _num(r.get(k))                                     # noqa: E731
        out: dict = {"datekey": r["datekey"], "date": r["datadate"],
                     "datekey_source": r["datekey_source"]}
        for src, dst in DIRECT_MM.items():
            v = g(src)
            out[dst] = None if v is None else v * MM
        # `equity` falls back to total stockholders' equity where common equity is absent.
        if out.get("equity") is None:
            v = g("seqq")
            out["equity"] = None if v is None else v * MM
        rev, cor = out.get("revenue"), out.get("cor")
        # `gpq` is ~0% non-null on this pull, so gross profit is REVENUE - COST OF REVENUE.
        gp = g("gpq")
        out["gp"] = (gp * MM) if gp is not None else (
            (rev - cor) if (rev is not None and cor is not None) else None)
        out["grossmargin"] = (out["gp"] / rev) if (out["gp"] is not None and rev) else None
        out["ebitmargin"] = (out["ebit"] / rev) if (out["ebit"] is not None and rev) else None
        dltt, dlc = g("dlttq"), g("dlcq")
        out["debt"] = None if (dltt is None and dlc is None) else \
            ((dltt or 0.0) + (dlc or 0.0)) * MM
        ncfo, capx = g("oancfy_q"), g("capxy_q")
        out["ncfo"] = None if ncfo is None else ncfo * MM
        out["fcf"] = None if (ncfo is None or capx is None) else (ncfo - capx) * MM
        # USD-only, so the builder's currency translation is the identity. `P7` measured that
        # getting this wrong computed `book_to_price` 892 against a true 0.589.
        out["fxusd"] = 1.0
        out["netinccmnusd"] = out.get("netinccmn")
        out["sharefactor"] = 1.0
        sh = g("cshoq")
        out["sharesbas"] = None if sh is None else sh * MM
        sstk, prstkc = g("sstky_q"), g("prstkcy_q")
        out["sstk"] = None if sstk is None else sstk * MM
        out["prstkc"] = None if prstkc is None else prstkc * MM
        return out

    def fundamentals(self) -> Dict[str, List[dict]]:
        """permno(str) -> the ticker's quarters, sorted by availability date."""
        if self._sf1 is not None:
            return self._sf1
        parts = self._chunks("comp_fundq")
        if not parts:
            raise SystemExit("REFUSING: no comp_fundq chunks in %s for %d-%d"
                             % (self.raw, self.year_lo, self.year_hi))
        f = pd.concat(parts, ignore_index=True)
        # THE STANDARD COMPUSTAT FILTER, declared. Omitting it double-counts every firm that
        # appears under more than one (indfmt, datafmt, consol, popsrc) combination.
        for col, val in (("indfmt", "INDL"), ("datafmt", "STD"),
                         ("consol", "C"), ("popsrc", "D")):
            if col in f.columns:
                f = f[f[col] == val]
        if self.usd_only and "curcdq" in f.columns:
            n0 = len(f)
            f = f[f["curcdq"] == "USD"]
            self.notes["fundq_rows_dropped_non_usd"] = int(n0 - len(f))
        f["datadate"] = pd.to_datetime(f["datadate"], errors="coerce")
        f["rdq"] = pd.to_datetime(f.get("rdq"), errors="coerce")
        f = f.dropna(subset=["datadate", "gvkey"])
        f = _ytd_to_quarterly(f)

        fb = f["datadate"] + pd.Timedelta(days=FALLBACK_LAG_DAYS)
        f["datekey_ts"] = f["rdq"].where(f["rdq"].notna(), fb)
        f["datekey_source"] = np.where(f["rdq"].notna(), "rdq",
                                       "datadate_plus_%dd" % FALLBACK_LAG_DAYS)
        # An `rdq` BEFORE its own period end is a vendor error, not an early filing, and taking
        # it would be a look-ahead of up to a quarter on those rows.
        bad = f["rdq"].notna() & (f["rdq"] < f["datadate"])
        self.notes["fundq_rows_rdq_before_datadate"] = int(bad.sum())
        f.loc[bad, "datekey_ts"] = fb[bad]
        f.loc[bad, "datekey_source"] = "rdq_before_datadate"
        self.notes["fundq_rows"] = int(len(f))
        self.notes["fundq_rdq_share"] = round(float((f["datekey_source"] == "rdq").mean()), 6)

        f["cusip8"] = f["cusip"].astype(str).str.upper().str.strip().str.slice(0, 8)
        lk = self.link()
        m = f.merge(lk[["permno", "cusip8", "namedt", "nameenddt", "shrcd", "exchcd"]],
                    on="cusip8", how="inner")
        m = m[(m["datadate"] >= m["namedt"]) & (m["datadate"] <= m["nameenddt"])]
        m = m[m["shrcd"].isin(SHRCD_OK) & m["exchcd"].isin(EXCHCD_OK)]
        if self.permnos:
            m = m[m["permno"].isin(self.permnos)]
        self.notes["fundq_rows_linked"] = int(len(m))
        self.notes["fundq_permnos_linked"] = int(m["permno"].nunique())
        self.notes["fundq_link_rate_rows"] = round(float(len(m)) / max(1, len(f)), 6)

        m["datekey"] = m["datekey_ts"].dt.strftime("%Y-%m-%d")
        m["datadate_s"] = m["datadate"].dt.strftime("%Y-%m-%d")
        cols = (list(DIRECT_MM) + ["seqq", "gpq", "dlttq", "dlcq", "cshoq", "fyearq", "fqtr"]
                + [c + "_q" for c in YTD])
        cols = [c for c in cols if c in m.columns]
        out: Dict[str, List[dict]] = {}
        for pn, grp in m.sort_values("datekey_ts").groupby("permno", sort=False):
            rows = []
            for rec in grp[cols + ["datekey", "datadate_s", "datekey_source"]].to_dict("records"):
                rec["datadate"] = rec.pop("datadate_s")
                rows.append(self._sf1_row(rec))
            out[str(int(pn))] = rows
        self._sf1 = out
        return out

    # --------------------------------------------- HistoricalDataProvider surface
    def universe(self, limit=None):
        """Permnos (as strings) carrying both a price series and a linked fundamental."""
        px, sf1 = self.prices(), self.fundamentals()
        have = sorted(set(px["permno"].astype(int).astype(str)) & set(sf1))
        self.notes["universe_n"] = len(have)
        if limit is not None and limit < len(have):
            # Largest by terminal market cap, so a subset is a SMOKE TEST of the big end rather
            # than an arbitrary alphabetical slice -- `B12`'s measured defect.
            last = px.groupby("permno")["mktcap"].last()
            idx = [int(h) for h in have]
            have = [str(int(p)) for p in
                    last.loc[idx].sort_values(ascending=False).index[:limit]]
        return have

    def market_index(self):
        """A value-weighted CRSP market index level, from `dsf` itself.

        WHY IT EXISTS: `build_fundamental_panel` needs a benchmark series, and the shipped default
        is the ticker `SPY`, which this provider cannot resolve because it keys on **permno**.
        SPY also does not exist before 1993, and the holdout starts in 1972.

        WHAT IT IS NOT: **no gate statistic reads it.** Gate A computes its own market return
        directly from `dsf` and compares that to French; Gate B compares COMPOSITES, and the
        benchmark reaches only `bench_ret`, which no theme uses. So this is a build-internal
        series whose only job is to let the builder run.

        WHAT THE REAL OOS1 BENCHMARK SHOULD BE, recorded so this stand-in is not mistaken for it:
        the charter specifies **S&P 500 total return** before SPY. `crsp_a_stock.dsi` carries
        `vwretd` and `sprtrn` and is a small table -- **it is NOT banked and is the one further
        pull OOS1 needs.** Using this index as the holdout benchmark would be a deviation.
        """
        px = self.prices()
        d = px[["date", "permno", "ret", "mktcap"]].dropna(subset=["ret"]).copy()
        d = d.sort_values(["permno", "date"])
        # Weight by the PRIOR day's cap. Weighting by the same day's cap is a look-ahead that
        # mechanically overweights whatever rose that day.
        d["w"] = d.groupby("permno", sort=False)["mktcap"].shift(1)
        d = d[(d["w"] > 0) & d["w"].notna()]
        num = (d["ret"] * d["w"]).groupby(d["date"]).sum()
        den = d["w"].groupby(d["date"]).sum()
        r = (num / den).sort_index()
        lvl = (1.0 + r).cumprod() * 100.0
        return [x.strftime("%Y-%m-%d") for x in lvl.index], [float(v) for v in lvl.values]

    def price_history(self, ticker, days=None):
        """(dates, adjusted closes) for one permno, oldest first.

        CRSP's `prc` is AS-TRADED. The builder's momentum and high-proximity columns need a
        SPLIT-ADJUSTED series, so the price is divided by `cfacpr`. `V6`'s `C5` measured both
        sides of this: on a raw series a 2-for-1 split reads as a -50% drawdown, and since
        companies split AFTER they rise, a raw basis flags the strongest names in the universe.
        """
        if ticker in self._series:
            d, c = self._series[ticker]
        elif not str(ticker).isdigit():
            # Any non-permno key is the benchmark. The builder's default is "SPY"; this provider
            # keys on permno, so a non-numeric key can only be the benchmark request.
            d, c = self.market_index()
            self._series[ticker] = (d, c)
        else:
            px = self.prices()
            g = px[px["permno"] == int(ticker)]
            if g.empty:
                return [], []
            cf = pd.to_numeric(g.get("cfacpr"), errors="coerce").replace(0.0, np.nan)
            adj = g["px"] / cf.fillna(1.0)
            ok = adj.notna()
            d = [x.strftime("%Y-%m-%d") for x in g.loc[ok, "date"]]
            c = [float(x) for x in adj[ok]]
            self._series[ticker] = (d, c)
        if days:
            return d[-int(days):], c[-int(days):]
        return d, c

    def fundamentals_history(self, ticker):
        return self.fundamentals().get(str(ticker), [])

    def fundamentals_pit(self, ticker, as_of):
        """The most recent quarter STRICTLY AVAILABLE before `as_of`."""
        key = str(as_of)[:10]
        rows = [r for r in self.fundamentals_history(ticker) if r["datekey"] < key]
        return rows[-1] if rows else {}

    # The five-theme holdout model carries none of these. Empty is CORRECT, not missing --
    # see the module docstring.
    def insider_history(self, ticker):
        return []

    def institutional_history(self, ticker):
        return []

    def grades_history(self, ticker):
        return []

    def delisted_map(self):
        return {}
