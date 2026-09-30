"""Resolve a company's sector through a FAIL-CLOSED chain, and say where it came from.

THE DEFECT THIS EXISTS FOR, MEASURED ON THE PUBLIC SITE 2026-09-30 ~13:45 ET. Four of four
financials came back with `company.sector == ""` from `POST /api/value`, and an empty sector
matches neither `FINANCIAL_SECTORS` nor any `FINANCIAL_INDUSTRY_HINTS`, so `classify` fell
through to the growth branch and valued a bank or insurer with the unlevered FCFF DCF its own
comment refuses for exactly these names:

    KNSL  sector ""  -> hypergrowth  FV ~$625  88 Strong Buy   (vs P/B-ROE $291, 67 Buy at 03:48)
    TRV   sector ""  -> mature       FV ~$702  89 Strong Buy
    PGR   sector ""  -> growth                 87 Strong Buy
    JPM   sector ""  -> growth                 49 Hold

The same service read KNSL as `financial` ten hours earlier, so `yfinance`'s `info` fails
INTERMITTENTLY from Render's IPs. **An intermittent fail-open is worse than a permanent one**: it
is invisible in any single local run, and the same ticker gets a different model depending on
which request happened to reach Yahoo.

WHY A CHAIN AND NOT A RETRY. Retrying the same endpoint from the same IP against the same rate
limiter buys latency, not information. Each rung here is a DIFFERENT SOURCE:

  1. **the scan** -- the latest saved snapshot already carries a sector for every scored name, it
     is on disk, and it costs no network call at all. It is first because it is both the cheapest
     and the most consistent with what the rest of the product already believes.
  2. **SEC `sic`** -- authoritative, free, no key, and the issuer's own filed classification.
     `edgar.py` already talks to SEC and already resolves the CIK.
  3. **FMP profile** -- only if a key is set; last because it is the one with a cost and the one
     the audit already recorded returning 402 on the company-screener.

AND IF EVERY RUNG FAILS THE ANSWER IS `None`, NEVER A GUESS. The caller must then carry an
UNKNOWN regime rather than a plausible one. That is the whole point: the defect was not that the
sector was missing, it was that missing read as "not a financial".

SIC 6000-6799 is Finance, Insurance and Real Estate on the SEC's own Office assignment, which is
why the range is that and not something narrower. It maps to `Financial Services`, the string
`FINANCIAL_SECTORS` already holds -- the map is to the vocabulary the engine already speaks, not
a new one, so nothing downstream has to learn a second name for the same thing.
"""
from __future__ import annotations

import logging
from typing import Optional, Tuple

_LOG = logging.getLogger(__name__)

# The SEC's own Division of Corporation Finance office range for Finance, Insurance and Real
# Estate. Quoted as a range rather than enumerated: SIC has ~90 codes in it and an enumeration
# would silently drop the ones nobody thought of.
SIC_FINANCE_LO, SIC_FINANCE_HI = 6000, 6799

SRC_SCAN = "scan"
SRC_SEC = "sec_sic"
SRC_FMP = "fmp_profile"
SRC_PRIMARY = "primary"          # the ordinary yfinance `info` path already succeeded
SRC_NONE = "unresolved"

_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# THE CENSUS. Without it the chain is invisible: a service silently living on the SEC rung
# looks exactly like one whose primary is healthy, and the difference is the whole question
# after an intermittent failure. Counts only -- no tickers, nothing a log would not already
# carry -- and it is process-local, so it describes THIS worker since its last restart and says
# so rather than implying a history it does not have.
_CENSUS: dict = {}


def reset_census() -> None:
    _CENSUS.clear()


def source_census() -> dict:
    total = sum(_CENSUS.values())
    return {
        "by_source": dict(_CENSUS),
        "n": total,
        "share": {k: round(v / total, 4) for k, v in _CENSUS.items()} if total else {},
        "scope": ("this worker process since its last restart -- Render runs more than one and "
                  "recycles them, so treat it as a sample rather than a complete history"),
    }


def _count(src: str) -> str:
    _CENSUS[src] = _CENSUS.get(src, 0) + 1
    return src


def sector_from_sic(sic) -> Optional[str]:
    """Map a SIC code to the engine's own sector vocabulary, or None.

    ONLY the finance range is mapped, deliberately. The other SIC divisions do not correspond
    one-to-one with the sector strings `CYCLICAL_SECTORS` uses, and inventing a mapping for them
    would trade a known-missing sector for a plausible-but-wrong one -- which is the failure
    being repaired, in a new costume. A non-financial SIC returns None and the chain continues.
    """
    try:
        code = int(str(sic).strip())
    except (TypeError, ValueError):
        return None
    if SIC_FINANCE_LO <= code <= SIC_FINANCE_HI:
        return "Financial Services"
    return None


def _from_scan(ticker: str, store=None) -> Optional[str]:
    """The latest saved scan snapshot's own sector for this ticker. No network."""
    try:
        if store is None:
            from ..screener.store import Store
            store = Store()
        date = store.latest_scan_date()
        if not date:
            return None
        for row in (store.load_snapshot(date) or []):
            if (row.get("ticker") or "").upper() == ticker.upper():
                return (row.get("sector") or "").strip() or None
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("sector: the scan rung failed for %s (%s)", ticker, type(e).__name__)
    return None


def _from_sec(ticker: str, cfg) -> Optional[str]:
    """The issuer's own filed SIC, via SEC submissions. Free, no key, authoritative."""
    try:
        import requests
        from . import edgar
        cik = edgar.resolve_cik(ticker, cfg)
        if not cik:
            return None
        r = requests.get(_SUBMISSIONS_URL.format(cik=cik),
                         headers=edgar._headers(cfg), timeout=15)
        r.raise_for_status()
        return sector_from_sic((r.json() or {}).get("sic"))
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("sector: the SEC rung failed for %s (%s)", ticker, type(e).__name__)
    return None


def _from_fmp(ticker: str, cfg) -> Optional[str]:
    """FMP's profile, ONLY if a key is configured. Last because it is the one that costs."""
    key = getattr(cfg, "fmp_api_key", None) or getattr(cfg, "FMP_API_KEY", None)
    if not key:
        return None
    try:
        import requests
        r = requests.get("https://financialmodelingprep.com/api/v3/profile/%s" % ticker,
                         params={"apikey": key}, timeout=15)
        r.raise_for_status()
        rows = r.json() or []
        if isinstance(rows, list) and rows:
            return (rows[0].get("sector") or "").strip() or None
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("sector: the FMP rung failed for %s (%s)", ticker, type(e).__name__)
    return None


def resolve_sector(ticker: str, cfg, current: str = "", store=None) -> Tuple[Optional[str], str]:
    """`(sector, source)`. `(None, "unresolved")` when every rung fails -- never a guess.

    `current` is whatever the primary fetch already produced. A non-empty one short-circuits the
    whole chain: the fallbacks exist for the failure, not to second-guess a working fetch.
    """
    if (current or "").strip():
        return current.strip(), _count(SRC_PRIMARY)
    for fn, src in ((lambda: _from_scan(ticker, store), SRC_SCAN),
                    (lambda: _from_sec(ticker, cfg), SRC_SEC),
                    (lambda: _from_fmp(ticker, cfg), SRC_FMP)):
        # THE GUARD IS HERE AS WELL AS INSIDE EACH RUNG, AND THAT IS NOT BELT-AND-BRACES.
        # Each rung currently catches its own failure, so this looks redundant -- until a rung
        # raises somewhere its own `try` does not cover, or a fourth rung is added by someone
        # who does not know the convention. Then ONE flaky source takes down the two BEHIND it,
        # and a fallback chain silently becomes a single point of failure. The property "a
        # failing rung declines" belongs to the chain, not to each rung's discipline.
        try:
            got = fn()
        except Exception as e:                                          # noqa: BLE001
            _LOG.warning("sector: the %s rung RAISED for %s (%s) - continuing down the chain",
                         src, ticker, type(e).__name__)
            continue
        if got:
            _LOG.warning("sector: %s resolved from %s after the primary returned nothing",
                         ticker, src)
            return got, _count(src)
    _LOG.warning("sector: %s is UNRESOLVED on every source - the regime is UNKNOWN and the "
                 "valuation will be withheld rather than guessed", ticker)
    return None, _count(SRC_NONE)
