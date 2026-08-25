"""IBES announcement dates as a SECOND, independent source for the `I-4` earnings-date spine.

WHY THIS EXISTS
---------------
`I-4` rests on Sharadar EVENTS code 22, an 8-K item. **29 of the options book's 186 names carry
ZERO code-22 coverage and every one is a foreign private issuer** filing 20-F/6-K rather than
8-K, so the hole is not random -- it is exactly the non-US ADRs. Every event-conditioned study
inherits it, honestly (they count the unknowns) but silently in the sense that the universe
shrinks without the shrinkage being the finding.

IBES actuals carry `anndats` -- the announcement date -- for US-listed issuers including ADRs,
which is the population code 22 misses.

THE THREE TRAPS, ALL MEASURED RATHER THAN ANTICIPATED
-----------------------------------------------------
**1. `oftic` IS A LEASE, NOT AN IDENTITY.** Matching our tickers to IBES's official-ticker column
reaches 29 of 29 missing names, which reads as a perfect repair. It is contaminated: `SPOT`
carries PANAMSAT CORP 1996-2004 beside SPOTIFY TECH; `RIO` carries ROYAL INTL OPTIC and VALE
beside RIO TINTO; `ARM` carries ARMSTRONG RUB, ARM FINL GROUP and ARVINMERITOR beside ARM
HOLDINGS. **Measured across the 29, 17.7% of the rows `oftic` offers belong to a different
company.** This is `S3-I5`'s ticker reuse in a third table, and the clean number is the tell --
`MA31`'s failure mode, where a lookup computes cleanly and answers a different question.

**2. ESCAPING REUSE NEEDS A DATE, NOT A DIFFERENT COLUMN.** The first CUSIP-based fix collected
every cusip CRSP had ever associated with a ticker and re-imported the same contamination through
another door (it returned MORE rows for TTE, SONY and BHP than the naive route did, and the extra
rows were other companies). The identifier must be resolved AS OF a date.

**3. IBES MASKS CUSIP CHARACTERS WITH `X`, AND AN EXACT MATCH FAILS SILENTLY.** IBES writes
`0636711X` where CRSP writes `06367110`. An 8-character equality test returns ZERO rows for such
a name, which is indistinguishable from "IBES does not cover it" -- and it hit BMO, CNQ and TD,
i.e. more of the very population this module exists to recover. Masking affects **1.64% of rows**
and appears in positions 6 and 8 (827 and 563 distinct cusips). The rule here treats `X` as a
wildcard **positionally**, so `0028931X` matches `00289310` while `00108281` still does NOT match
`00108282` -- two genuinely different companies that share a 7-character prefix. Truncating to 7
characters would have merged them; 328 such prefixes exist.

FENCE
-----
Raw IBES rows never leave `D:\\wrds`. This module emits DATES and counts. The dates are treated as
licensed content: they inform internal joins and are not rendered publicly.
"""
from __future__ import annotations

import collections
import datetime as dt
import glob
import os
from typing import Dict, Iterable, Optional

#: Where the chunked IBES pull lives. Never inside the checkout.
DEFAULT_ACT_DIR = r"D:\wrds\ibes_act_epsus"

#: IBES `measure` for earnings per share. Other measures (sales, cash flow) announce on the same
#: day but are separate rows; keeping them would multiply-count a single announcement.
MEASURE_EPS = "EPS"

#: `pdicity` values that represent a REPORTING EVENT we want on the spine. QTR is the quarterly
#: announcement. ANN is the annual figure, which for most issuers is announced on the SAME day as
#: Q4 and would double-count -- but for a semiannual or annual-only filer it is the only event
#: there is, so it is kept and de-duplicated by DATE rather than dropped by type.
PERIODICITIES = ("QTR", "ANN", "SAN")


class MaskedCusip:
    """CUSIP comparison that honours IBES's `X` mask, and nothing looser.

    Deliberately NOT a prefix match. A 7-character prefix rule would treat `00108281`
    (BOS BETTER ONLINE) and `00108282` (TECHNOPRISES) as the same security -- 328 prefixes in
    this file are shared by more than one distinct cusip. Position-wise wildcarding accepts a
    masked character and refuses a differing one.
    """

    @staticmethod
    def matches(ibes: str, crsp: str) -> bool:
        if not ibes or not crsp:
            return False
        a, b = str(ibes).upper().strip(), str(crsp).upper().strip()
        if len(a) != len(b):
            return False
        return all(x == y or x == "X" for x, y in zip(a, b))

    @staticmethod
    def key(ibes: str) -> str:
        """A bucket key that a masked and an unmasked cusip share, for cheap candidate lookup.

        Masked positions are replaced by `.` so the key is the same for `0028931X` and
        `00289310` only after both are normalised -- so the key is built from the UNMASKED
        positions and used to fetch CANDIDATES, with `matches` making the actual decision.
        """
        s = str(ibes).upper().strip()
        return "".join(c if c != "X" else "." for c in s)


def _iter_chunks(act_dir: str = ""):
    d = act_dir or DEFAULT_ACT_DIR
    if not os.path.isdir(d):
        raise FileNotFoundError(
            f"{d} is absent. IBES actuals live on D: and are never mirrored into the checkout; "
            f"run `python -m scripts.wrds_pull --product ibes_act_epsus` first.")
    files = sorted(glob.glob(os.path.join(d, "*.pkl")))
    if not files:
        raise FileNotFoundError(f"{d} exists but holds no chunk files -- existence is not "
                                f"population, and an empty read here would report zero coverage "
                                f"for every name.")
    import pandas as pd
    for f in files:
        yield pd.read_pickle(f, compression="gzip")


def load_announcements(act_dir: str = "", measures=(MEASURE_EPS,)) -> "object":
    """Every EPS announcement row, as a frame carrying cusip, cname, pdicity and `anndats`."""
    import pandas as pd
    keep = ["ticker", "oftic", "cusip", "cname", "measure", "pdicity", "anndats", "anntims"]
    out = []
    for d in _iter_chunks(act_dir):
        sub = d[keep]
        sub = sub[sub["measure"].isin(measures)]
        out.append(sub)
    df = pd.concat(out, ignore_index=True)
    for c in ("ticker", "oftic", "cusip", "cname"):
        df[c] = df[c].astype("string").str.upper().str.strip()
    return df


def dates_by_cusip(df, cusips: Iterable[str],
                   periodicities=PERIODICITIES) -> Dict[str, list]:
    """{cusip8 as given: [ISO date, ...]} for the supplied CRSP cusips, honouring the X mask."""
    want = [str(c).upper().strip() for c in cusips if c]
    sub = df[df["pdicity"].isin(list(periodicities))]
    buckets = collections.defaultdict(list)
    for cu, an in zip(sub["cusip"].tolist(), sub["anndats"].tolist()):
        if cu is None or an is None:
            continue
        buckets[str(cu)].append(str(an)[:10])
    out = {}
    for c in want:
        hits = []
        for icu, ds in buckets.items():
            if MaskedCusip.matches(icu, c):
                hits.extend(ds)
        if hits:
            out[c] = sorted(set(hits))
    return out


def dates_by_intervals(df, intervals: Dict[str, list],
                       periodicities=PERIODICITIES) -> Dict[str, list]:
    """{ticker: [ISO date, ...]} where a date counts only if it falls INSIDE the window during
    which that cusip was this ticker's identity.

    `intervals` is `{ticker: [(cusip8, from, to), ...]}`. This is the only construction in this
    module that is safe against BOTH ticker reuse and cusip continuation -- see
    `scripts/w3b_ibes_spine._crsp_intervals`, which measured what each of the two naive
    alternatives costs.
    """
    sub = df[df["pdicity"].isin(list(periodicities))]
    rows = list(zip(sub["cusip"].tolist(), sub["anndats"].tolist()))
    buckets = collections.defaultdict(list)
    for cu, an in rows:
        if cu is None or an is None:
            continue
        buckets[str(cu)].append(str(an)[:10])

    out: Dict[str, list] = {}
    for t, ivs in intervals.items():
        hits = []
        for c8, lo, hi in ivs:
            for icu, ds in buckets.items():
                if not MaskedCusip.matches(icu, c8):
                    continue
                hits.extend(d for d in ds if lo <= d <= hi)
        if hits:
            out[t] = sorted(set(hits))
    return out


def _as_date(v) -> Optional[dt.date]:
    if v is None:
        return None
    if isinstance(v, dt.date):
        return v
    s = str(v)[:10]
    try:
        return dt.date.fromisoformat(s)
    except ValueError:
        return None
