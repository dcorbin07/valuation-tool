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
#
# KEPT FOR ITS CALLERS AND NO LONGER THE WHOLE MAP. Item 41 extended `sector_from_sic` from this
# one range to the full SIC space -- see `SIC_RANGES` below and the measurement that licensed it.
SIC_FINANCE_LO, SIC_FINANCE_HI = 6000, 6799

#: ITEM 41 -- THE FULL SIC MAP, AND WHY IT EXISTS.
#:
#: This function used to map ONLY 6000-6799 and return `None` for everything else, with a stated
#: reason: *"inventing a mapping for them would trade a known-missing sector for a
#: plausible-but-wrong one."* That caution was HALF right, and the half it got wrong was
#: expensive. Measured on the 2026-10-07 scan -- the day Yahoo refused the runner outright, so
#: every name needed this chain -- **460 names were UNRESOLVED on every source**, each getting
#: `regime UNKNOWN` and **its valuation withheld**, while the SEC rung rescued only the 143 that
#: happened to be financials.
#:
#: WHAT THE MEASUREMENT SHOWED (scripts/sic_map_report.py, 2026-10-08, 459 of 460 names carrying
#: a filed SIC, 0 without a CIK, 0 fetch failures):
#:
#:   * the map resolves **413 of 460 (89.8%)** of that population;
#:   * where the product ALREADY has an opinion it **agrees on 134 of 138 (97.1%)**, so the
#:     taxonomy cost is **2.9%** -- against the **11.37%** `S25` measured for its GICS crosswalk
#:     onto these same eleven strings;
#:   * the four disagreements are genuine taxonomy differences, not map errors: GHC (a
#:     conglomerate), NSIT (files as a catalogue retailer, operates as an IT reseller), RDDT
#:     (files as software, is classed as media), SSL (files as refining, is classed as chemicals).
#:
#: THE CAUTION IS HONOURED WHERE IT ACTUALLY BITES. SIC's MANUFACTURING, EXTRACTIVE and UTILITY
#: codes map cleanly; its SERVICE codes do not, and the rule for refusing one is stated rather
#: than applied by taste -- **a code is mapped only where ONE sector is at least two thirds of
#: its observed members.** 7389 "Business Services NEC" holds MA, PYPL, GPN (payments), UBER,
#: DASH, ETSY, MELI (consumer), AKAM (technology) and CBZ, MMS (industrials): four sectors in
#: one code, so it stays `None`.
#:
#: AND `None` IS A NAMED STATE, NEVER A DEFAULT. `SECTOR_TARGET_MARGIN.get(sector, 0.12)` fails
#: OPEN in the middle of a 0.100-0.270 range, so returning a guess is a VOTE for a margin rather
#: than an absence of one -- `S25`'s finding, and the reason an unmapped code must refuse.

#: Exact 4-digit overrides, applied BEFORE the ranges: each is a cell where SIC's own division
#: boundary cuts across this vocabulary.
SIC_EXACT = {
    # pharma and biotech sit inside SIC's CHEMICALS division
    "2833": "Healthcare", "2834": "Healthcare", "2835": "Healthcare", "2836": "Healthcare",
    # refining and oilfield machinery sit outside SIC's extraction range
    "2911": "Energy", "3533": "Energy",
    # semiconductor EQUIPMENT is filed as "special industry machinery" (ASML, LRCX, ACMR)
    "3559": "Technology",
    # laboratory analytical instruments are diagnostics (WAT, BIO, TXG), not industrial
    "3826": "Healthcare",
    # household audio/video is a consumer product, not electronics
    "3651": "Consumer Cyclical",
    # drug stores and medical wholesale are healthcare in this vocabulary
    "5912": "Healthcare", "5047": "Healthcare",
    # contract research: ICLR and IQV file here
    "8731": "Healthcare",
    # newspapers, periodicals and books are media
    "2711": "Communication Services", "2721": "Communication Services",
    "2731": "Communication Services",
}

#: Codes whose observed membership spans too many sectors to carry one. NAMED, with the split,
#: so a later reader can disagree with the evidence rather than with a blank.
SIC_AMBIGUOUS = {
    "7370",   # GOOGL, META, PINS, MTCH (Communication Services) vs APP, ZM, BSP (Technology)
    "7389",   # MA, PYPL, GPN | UBER, DASH, ETSY, MELI | AKAM | CBZ, MMS -- four sectors
    "7320",   # consumer credit reporting vs collection services
    "3690",   # AMPX, ENS, EOSE -- batteries and storage straddle Industrials and Technology
    "3827",   # optical instruments: defence (Industrials) and semiconductor (Technology)
    "3829",   # "measuring and controlling devices, NEC" -- NEC by its own name
    "5000", "5090", "5099", "5199",   # wholesale "NEC" buckets, mixed by construction
    "6770",   # blank checks and SPACs -- not a business sector at all
    "9995",   # "non-classifiable establishments" -- the SEC's own refusal to classify
}

#: Whole ranges left unmapped. A range rather than exact codes because SIC fills a division
#: densely and the ambiguity belongs to the DIVISION.
SIC_AMBIGUOUS_RANGES = (
    # WATER TRANSPORT spans THREE sectors on the real population: crude tankers (FRO, INSW, DHT,
    # LPG) read Energy, cruise (VIK) reads Consumer Cyclical, dry bulk and inland barge (MATX,
    # KEX) read Industrials. A hull is not a sector. Measured: mapping it to Industrials
    # produced 3 of the 9 disagreements in the first validation pass.
    (4400, 4499),
    # PATENT OWNERS (6794, Dolby) and MINERAL ROYALTY TRADERS (6795, Triple Flag) are FILED as
    # finance and operate as neither. SIC is literal about the filing and the sector is about
    # the business; here they are different questions.
    (6794, 6795),
)

#: `(lo, hi, sector)`, inclusive, FIRST match wins -- so narrower ranges precede wider ones.
#: Every sector string is checked against the engine's own keys at import (see below), so a typo
#: fails loudly instead of resolving a name to a sector the engine has no margin for.
SIC_RANGES = (
    # --- extractive -------------------------------------------------------------------------
    (1000, 1099, "Basic Materials"),        # metal mining -- AEM, AG, AU, HBM
    (1200, 1299, "Energy"),                 # coal
    (1300, 1399, "Energy"),                 # oil and gas extraction, drilling, field services
    (1400, 1499, "Basic Materials"),        # nonmetallic minerals
    # --- construction -----------------------------------------------------------------------
    (1520, 1599, "Consumer Cyclical"),      # homebuilders -- KBH, MTH, GRBK: a consumer durable
    (1600, 1799, "Industrials"),            # heavy and specialty trades -- KBR, STRL, AGX
    # --- food, drink, tobacco ---------------------------------------------------------------
    (2000, 2099, "Consumer Defensive"),     # food and beverages -- KO, PEP, ADM, BG
    (2100, 2199, "Consumer Defensive"),     # tobacco
    # --- textiles and apparel ---------------------------------------------------------------
    (2200, 2399, "Consumer Cyclical"),      # LULU, RL, VFC, KTB, FIGS
    # --- wood, paper, furniture -------------------------------------------------------------
    (2400, 2699, "Basic Materials"),
    # --- chemicals (pharma already diverted above) ------------------------------------------
    (2800, 2899, "Basic Materials"),        # DOW, LYB, ALB, EMN, WLK
    # --- petroleum, rubber, leather ---------------------------------------------------------
    (2900, 2999, "Energy"),                 # refining and petroleum products
    (3000, 3099, "Consumer Cyclical"),      # rubber and plastics footwear -- NKE, DECK, ONON
    (3100, 3199, "Consumer Cyclical"),      # leather
    # --- stone, clay, glass, metals ---------------------------------------------------------
    (3200, 3299, "Basic Materials"),
    (3300, 3399, "Basic Materials"),        # primary metals -- STLD, CMC, AA, MT
    (3400, 3499, "Industrials"),            # fabricated metal -- ACA, VMI, BALL, CCK
    # --- machinery and computers ------------------------------------------------------------
    (3500, 3569, "Industrials"),            # industrial machinery -- FLS, GGG, ITT, NDSN
    (3570, 3579, "Technology"),             # computers and storage -- AAPL, DELL, STX, NTAP
    (3580, 3599, "Industrials"),
    # --- electrical and electronics ---------------------------------------------------------
    (3600, 3639, "Industrials"),            # electrical industrial apparatus, appliances
    (3640, 3650, "Industrials"),            # lighting
    (3660, 3679, "Technology"),             # comms equipment, semis, PCBs, components
    (3680, 3689, "Technology"),
    # --- transport equipment ----------------------------------------------------------------
    (3700, 3716, "Consumer Cyclical"),      # motor vehicles and parts -- ALV, LEA, DAN, ALSN
    (3720, 3799, "Industrials"),            # aerospace, ships, rail
    # --- instruments (3826/3827/3829 handled above) -----------------------------------------
    (3800, 3825, "Technology"),             # measuring and testing -- KEYS, TER, COHU, CGNX
    (3830, 3859, "Healthcare"),             # surgical, medical, dental, ophthalmic
    (3860, 3999, "Consumer Cyclical"),      # photographic, jewellery, toys, misc manufacturing
    # --- transport and utilities ------------------------------------------------------------
    (4000, 4099, "Industrials"),            # rail
    (4100, 4299, "Industrials"),            # transit and trucking
    (4500, 4599, "Industrials"),            # air transport -- UAL, ALGT, CPA
    (4600, 4619, "Energy"),                 # pipelines other than natural gas
    (4700, 4799, "Industrials"),            # transportation services
    (4800, 4899, "Communication Services"),  # telephone, broadcasting, cable -- T, VZ, BCE
    (4900, 4911, "Utilities"),              # electric
    (4920, 4925, "Energy"),                 # natural gas transmission -- AM, DTM, WES, KGS
    (4930, 4999, "Utilities"),              # combination, water, sanitary
    # --- trade ------------------------------------------------------------------------------
    (5010, 5088, "Industrials"),            # industrial and electronic wholesale -- ARW, GWW
    (5100, 5159, "Consumer Defensive"),     # grocery and farm-product wholesale
    (5160, 5198, "Basic Materials"),        # chemicals wholesale
    (5200, 5399, "Consumer Cyclical"),      # building supply, general merchandise
    (5400, 5499, "Consumer Defensive"),     # grocery stores -- ACI, SFM, TBBB
    (5500, 5599, "Consumer Cyclical"),      # auto dealers -- LAD, GPI, AAP
    (5600, 5899, "Consumer Cyclical"),      # apparel, furniture, electronics, eating places
    (5900, 5911, "Consumer Cyclical"),
    (5920, 5999, "Consumer Cyclical"),      # misc retail -- AMZN files 5961
    # --- finance, insurance, real estate ----------------------------------------------------
    (6000, 6499, "Financial Services"),
    # REAL ESTATE AND REITs ARE NOT "FINANCIAL SERVICES", and the old range said they were.
    # `classify.py` turns the sector into a REGIME, so a REIT reading `Financial Services` was
    # valued by the bank method (justified P/B from ROE) instead of taking the REIT branch that
    # REFUSES the FCFF lens -- and item 38's group labels the two differently on the page.
    (6500, 6599, "Real Estate"),
    (6798, 6798, "Real Estate"),            # REITs
    # SPLIT AROUND 6770 (blank checks and SPACs), which `SIC_AMBIGUOUS` refuses. The refusal
    # already wins -- it is checked first -- but a range that COVERS a code the map is supposed
    # to refuse makes the two layers contradict each other on paper, and the next reader
    # removing the "redundant" set entry would silently start calling shell companies
    # Financial Services. Found by the guard asserting the layers agree, not by reading.
    (6600, 6769, "Financial Services"),
    (6771, 6793, "Financial Services"),
    (6796, 6797, "Financial Services"),
    (6799, 6799, "Financial Services"),
    # --- services ---------------------------------------------------------------------------
    (7000, 7099, "Consumer Cyclical"),      # hotels -- LVS, MGM, PK, PENN
    (7200, 7299, "Consumer Cyclical"),      # personal services
    (7372, 7373, "Technology"),             # prepackaged software -- ADBE, ADSK, CHKP
    (7374, 7379, "Technology"),             # data processing and computer services
    (7600, 7699, "Consumer Cyclical"),      # repair services
    (7800, 7899, "Communication Services"),  # motion pictures and entertainment
    (7900, 7999, "Consumer Cyclical"),      # amusement and recreation -- DKNG, MTN, MSGE
    (8000, 8099, "Healthcare"),             # health services -- labs, hospitals, home health
    (8100, 8199, "Industrials"),            # legal services
    (8200, 8299, "Consumer Cyclical"),      # educational services -- EDU, LOPE, TAL
    (8300, 8399, "Industrials"),            # social services
    (8400, 8499, "Communication Services"),  # museums and cultural institutions
    (8600, 8699, "Industrials"),            # membership organisations
    (8700, 8730, "Industrials"),            # engineering, accounting, management
    (8732, 8799, "Industrials"),
)


def _engine_sector_keys() -> set:
    """The engine's OWN sector vocabulary, IMPORTED and never retyped (`S25`/`MA5`'s rule).

    `SECTOR_TARGET_MARGIN` and `comps.SECTOR_MULTIPLES` are keyed on exactly these strings, so a
    map emitting anything else would resolve a name to a sector the engine has no margin for --
    and `.get(sector, 0.12)` fails OPEN, so the symptom would be a silent default rather than an
    error.
    """
    from ..engine.assumptions import SECTOR_TARGET_MARGIN
    return set(SECTOR_TARGET_MARGIN)


def _check_map_against_the_engine() -> None:
    """Every sector this map can emit must be a key the engine already speaks.

    AT IMPORT, so a typo is a startup failure rather than a name quietly valued against the
    middle of the margin range. Degrades to a no-op if the engine cannot be imported, because a
    data module must not refuse to load because of a layering accident.
    """
    try:
        keys = _engine_sector_keys()
    except Exception:                                                   # noqa: BLE001
        return
    emitted = set(SIC_EXACT.values()) | {sec for _lo, _hi, sec in SIC_RANGES}
    bad = sorted(emitted - keys)
    if bad:
        raise RuntimeError(
            "sector_resolve's SIC map emits %r, which is not in the engine's own sector "
            "vocabulary %r" % (bad, sorted(keys)))


_check_map_against_the_engine()

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

    `None` MEANS UNMAPPED AND IS A NAMED STATE, never a default. See `SIC_RANGES` above for the
    measurement that licensed the map and for the rule that decides which codes refuse.

    A STRING IS ACCEPTED because `submissions` serves `"sic": "6331"` as one -- an int-only map
    would decline every real answer and the SEC rung would be dead code that looks alive.
    """
    s = str(sic or "").strip()
    if not s:
        return None
    if s.isdigit():
        s = s.zfill(4)
    if s in SIC_AMBIGUOUS:
        return None
    if s in SIC_EXACT:
        return SIC_EXACT[s]
    try:
        code = int(s)
    except (TypeError, ValueError):
        return None
    for lo, hi in SIC_AMBIGUOUS_RANGES:
        if lo <= code <= hi:
            return None
    for lo, hi, sector in SIC_RANGES:
        if lo <= code <= hi:
            return sector
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


#: ITEM 41 -- SEC FAIR ACCESS, AND A CACHE, BOTH OF WHICH THE RUNG NOW NEEDS BECAUSE IT WORKS.
#:
#: While the map covered one sector in eleven this rung answered for ~10% of the names that
#: reached it; now it answers for ~90%, so its call volume is real. The SEC asks for a declared
#: User-Agent and a request ceiling, and `edgar._headers` already supplies the first.
#:
#: 0.13s IS THE PROJECT'S OWN SEC PACING, not a new number -- `scripts/live_theme_sources.py`
#: fixes `SEC_MIN_INTERVAL_S = 0.13` for exactly this service. Reusing it rather than inventing
#: a second interval is `MA5`'s rule: two constants for one rate limit drift, and the one that
#: drifts upward is the one that gets us blocked.
SEC_MIN_INTERVAL_S = 0.13

#: ticker -> resolved sector or None. PROCESS-LOCAL and never persisted, like `_CENSUS` above.
#:
#: IT IS NOT AN OPTIMISATION FOR A SINGLE SCAN -- it is one because the scan values some names
#: TWICE. The hot pass values its DCF set and then item 35's dip precompute re-values every
#: qualifying name through `value_ticker`, so ~230 of them reach this chain a second time.
#:
#: A `None` IS CACHED TOO, and that is deliberate: a name SEC cannot classify is not a name
#: worth asking about again in the same process, and re-asking would spend the fair-access
#: budget on a question already answered.
_SEC_CACHE: dict = {}


def _sec_wait() -> None:
    """Hold the SEC's minimum interval. Module-level clock, so every caller shares one budget."""
    import time
    last = _SEC_CACHE.get("__last__", 0.0)
    gap = time.monotonic() - last
    if 0 <= gap < SEC_MIN_INTERVAL_S:
        time.sleep(SEC_MIN_INTERVAL_S - gap)
    _SEC_CACHE["__last__"] = time.monotonic()


def _from_sec(ticker: str, cfg) -> Optional[str]:
    """The issuer's own filed SIC, via SEC submissions. Free, no key, authoritative.

    FOR A VALUATION DATED TODAY, TODAY'S CLASSIFICATION *IS* THE POINT-IN-TIME ONE, which is
    what makes this rung legitimate here where `S25` had to build a dated map for a HISTORICAL
    panel. The same filing read against a 2009 row would be look-ahead; read against a quote
    from this morning it is simply the current fact.
    """
    key = (ticker or "").strip().upper()
    if key in _SEC_CACHE:
        return _SEC_CACHE[key]
    out = None
    try:
        import requests
        from . import edgar
        cik = edgar.resolve_cik(ticker, cfg)
        if not cik:
            # NOT an error and not cached as a failure of SEC's: a ticker with no CIK is not an
            # SEC filer under that symbol (a foreign issuer, a fund), which the census counts.
            _SEC_CACHE[key] = None
            return None
        _sec_wait()
        r = requests.get(_SUBMISSIONS_URL.format(cik=cik),
                         headers=edgar._headers(cfg), timeout=15)
        r.raise_for_status()
        out = sector_from_sic((r.json() or {}).get("sic"))
    except Exception as e:                                              # noqa: BLE001
        _LOG.warning("sector: the SEC rung failed for %s (%s)", ticker, type(e).__name__)
        # A TRANSPORT FAILURE IS NOT CACHED. Caching it would turn one timeout into a
        # process-long refusal for that name, which is the opposite of what a retryable error
        # deserves -- and `None` from the map (a real answer) must stay distinguishable from
        # `None` from a dropped connection.
        return None
    _SEC_CACHE[key] = out
    return out


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
