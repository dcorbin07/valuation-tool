# -*- coding: utf-8 -*-
"""EODHD as a drop-in provider for the SHIPPED scorer -- one code path, two data sources.

**WHY A PROVIDER AND NOT A SECOND SCORER.** `D9`'s cross-vendor reading compared a Sharadar book
built by `score_universe_now` against a **SERVED** live composite read out of a scan JSON, i.e. two
different code paths as well as two different vendors, so a disagreement could not be attributed to
either. Routing EODHD through the same `score_universe_now` makes every construction choice --
winsorisation, the bucket split, the theme means, the composite -- **identical by construction**, so
what is left is the data. That is the `B7` discipline applied to a comparison rather than to a
formula: one definition, called twice.

**THE SEAM IS THE RAW COLUMN NAME.** `score_universe_now` reads `fundamentals_history(t)` and hands
the rows to the shipped number-computation, which reads Sharadar's raw SF1 names. So this module's
whole job is `EODHD statement field -> Sharadar raw column`, and nothing downstream knows or cares
which vendor produced the row.

**`datekey` IS THE FILING DATE, WHICH IS WHY THIS IS POSSIBLE AT ALL.** The scorer sorts and cuts on
`datekey`, and `EODHD_CENSUS.md` section 2 measured `filing_date` as real and populated (0.9875 in
the 2010s, zero negative lags over 1,040 periods). A vendor shipping only period-end dates could not
be read point-in-time here at any price.

**NO FIELD IS ASSUMED PRESENT.** `probe()` reports the non-null rate of every mapped field on the
caller's own population and names the ones that never appeared. This project has shipped **five
wired factors that were empty in every run of its history** -- an absent column contributes nothing
to a theme mean, raises no error, and the run completes normally -- so a vendor mapping that cannot
say which of its fields resolved is not a mapping, it is a guess. The caller is expected to refuse
rather than score a theme whose inputs did not arrive.

**TWO THEMES ARE DELIBERATELY NOT SERVED, AND THE REASON IS MEASURED.** `insider_history` and
`institutional_history` return empty. EODHD has no 13F feed at all, and its insider feed carries
**137,297 rows over 2009-01-01 -> 2026-10-22** against the licensed SF2 file's **5,636,964** -- about
2.4% -- while `ownerCik` is **0.0000 populated from 2023 on** (and 1.0000 in 2010-2011, which is a
correction to the census's own flat 0.0000: it probed recent rows only). A theme built on 2.4% of the
rows would not be the shipped theme under a different vendor, it would be a different theme. So the
comparison is run on the four themes that carry a `B3` bar and `insider` is **cited** from
`FIDELITY-2` exactly as `D9`'s register already treats it.
"""
import json
import os

#: `EODHD statement -> {eodhd field: sharadar raw column}`. Declared as data so `probe()` can walk
#: it; every entry is checked against a real payload before any score is read.
FIELD_MAP = {
    "Income_Statement": {
        "totalRevenue": "revenue",
        "netIncome": "netinc",
        "operatingIncome": "ebit",
        "ebitda": "ebitda",
        "grossProfit": "gp",
        "costOfRevenue": "cor",
        "sellingGeneralAdministrative": "sgna",
        "researchDevelopment": "rnd",
        "interestExpense": "intexp",
    },
    "Balance_Sheet": {
        "totalStockholderEquity": "equity",
        "totalAssets": "assets",
        "shortLongTermDebtTotal": "debt",
        "longTermDebt": "debtnc",
        "cashAndShortTermInvestments": "cashneq",
        "netReceivables": "receivables",
        "inventory": "inventory",
        "accountsPayable": "payables",
        "commonStockSharesOutstanding": "sharesbas",
    },
    "Cash_Flow": {
        "totalCashFromOperatingActivities": "ncfo",
        "capitalExpenditures": "capex",
        "freeCashFlow": "fcf",
    },
}

#: Columns the four compared themes cannot be built without. The caller refuses below a floor
#: rather than scoring a theme on whatever happened to arrive.
REQUIRED = ("revenue", "netinc", "ebit", "equity", "assets", "ncfo")


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def load_unit(root, ticker):
    """One harvested fundamentals payload, or None. Never raises on an absent name."""
    p = os.path.join(root, "fundamentals", "%s.json" % str(ticker).upper())
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        obj = json.load(fh)
    return obj.get("payload", obj) if isinstance(obj, dict) else None


def fundamentals_rows(payload, ticker=None):
    """EODHD quarterly statements -> rows carrying SHARADAR raw column names.

    One row per statement PERIOD, the three statements merged on the period key. `datekey` is the
    filing date so the shipped point-in-time cut applies unchanged; a period with no filing date is
    **dropped**, because a row whose own publication date is unknown cannot be placed in time, and
    falling back to the period end would be exactly the look-ahead this is built to avoid.
    """
    fin = (payload or {}).get("Financials") or {}
    byper = {}
    for stmt, mapping in FIELD_MAP.items():
        q = ((fin.get(stmt) or {}).get("quarterly") or {})
        for per, row in (q.items() if isinstance(q, dict) else []):
            if not isinstance(row, dict):
                continue
            key = str(row.get("date") or per)[:10]
            tgt = byper.setdefault(key, {"date": key, "datekey": None, "dimension": "ARQ"})
            fd = row.get("filing_date")
            if fd and not tgt["datekey"]:
                tgt["datekey"] = str(fd)[:10]
            for ef, sc in mapping.items():
                v = _num(row.get(ef))
                if v is not None:
                    tgt[sc] = v
    out = []
    for key in sorted(byper):
        r = byper[key]
        if not r.get("datekey"):
            continue
        if ticker:
            r["ticker"] = str(ticker).upper()
        out.append(r)
    return out


def dropped_for_no_filing_date(payload):
    """How many statement periods this payload loses to an absent filing date.

    Reported rather than silently differenced: the drop is the price of reading the vendor
    point-in-time, and a reader comparing row counts across vendors needs to see it.
    """
    fin = (payload or {}).get("Financials") or {}
    keys, kept = set(), set()
    for stmt in FIELD_MAP:
        q = ((fin.get(stmt) or {}).get("quarterly") or {})
        for per, row in (q.items() if isinstance(q, dict) else []):
            if not isinstance(row, dict):
                continue
            k = str(row.get("date") or per)[:10]
            keys.add(k)
            if row.get("filing_date"):
                kept.add(k)
    return {"periods": len(keys), "with_filing_date": len(kept),
            "dropped": len(keys) - len(kept)}


def probe(root, tickers):
    """Per-field non-null rate ON THE CALLER'S OWN POPULATION, plus the fields never seen.

    Returns the counts as well as the rates: a rate without its denominator is the figure this
    record has mis-applied across populations more than once.
    """
    cols = sorted({c for m in FIELD_MAP.values() for c in m.values()})
    seen = {c: 0 for c in cols}
    rows = names = 0
    periods = kept = 0
    for t in tickers:
        pay = load_unit(root, t)
        if pay is None:
            continue
        names += 1
        d = dropped_for_no_filing_date(pay)
        periods += d["periods"]
        kept += d["with_filing_date"]
        rr = fundamentals_rows(pay, t)
        rows += len(rr)
        for r in rr:
            for c in cols:
                if r.get(c) is not None:
                    seen[c] += 1
    return {"names_with_a_payload": names, "rows": rows,
            "statement_periods": periods, "periods_with_filing_date": kept,
            "periods_dropped_no_filing_date": periods - kept,
            "field_non_null": {c: (seen[c] / rows if rows else None) for c in cols},
            "field_non_null_counts": seen,
            "never_seen": sorted([c for c in cols if seen[c] == 0]),
            "required_missing": sorted([c for c in REQUIRED if seen[c] == 0])}


def capex_sign(root, tickers, limit=400):
    """MEASURE the capex sign convention; never assume it.

    `_KEEP`'s own comment records the Sharadar trap: capex is stored as a **negative** outflow and
    the identity is `fcf = ncfo + capex`. A vendor using the opposite sign would silently invert
    every free-cash-flow number built from it, so the convention is read off the data and reported.
    """
    neg = pos = 0
    for t in tickers:
        pay = load_unit(root, t)
        if pay is None:
            continue
        for r in fundamentals_rows(pay, t):
            v = r.get("capex")
            if v is None or v == 0:
                continue
            if v < 0:
                neg += 1
            else:
                pos += 1
        if neg + pos >= limit:
            break
    n = neg + pos
    return {"n": n, "negative": neg, "positive": pos,
            "share_negative": (neg / n if n else None),
            "matches_sharadar_convention": (neg > pos) if n else None}


class EodhdProvider:
    """The methods `score_universe_now` calls, backed by the EODHD freeze.

    `price_history` DELEGATES to the project's existing provider. That is the brief's own
    instruction ("EODHD fundamentals and the project's existing prices") and it is also the right
    experiment: holding prices fixed means the two books differ only through fundamentals-derived
    inputs, so a `momentum` or `size` disagreement is attributable rather than confounded with a
    second price vendor.
    """

    def __init__(self, freeze_root, price_delegate):
        self.root = freeze_root
        self._px = price_delegate
        self._cache = {}

    def ready(self):
        d = os.path.join(self.root, "fundamentals")
        if not os.path.isdir(d):
            return False, "no fundamentals directory under %s" % self.root
        n = len([f for f in os.listdir(d) if f.endswith(".json")])
        return (n > 0), "%d fundamentals units" % n

    def universe(self, limit=None):
        d = os.path.join(self.root, "fundamentals")
        if not os.path.isdir(d):
            return []
        names = sorted(f[:-5].upper() for f in os.listdir(d) if f.endswith(".json"))
        return names if limit is None else names[:limit]

    def price_history(self, ticker, days=None):
        return self._px.price_history(ticker, days=days)

    def fundamentals_history(self, ticker):
        t = str(ticker).upper()
        if t not in self._cache:
            self._cache[t] = fundamentals_rows(load_unit(self.root, t), t)
        return self._cache[t]

    def insider_history(self, ticker):
        return []

    def institutional_history(self, ticker):
        return []

    def delisted_map(self):
        return {}
