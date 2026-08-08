"""
ThetaData BULK loader — one call per symbol-year, cached to data/options/, 4 concurrent.

WHY THIS REPLACED THE PER-DAY PULLER. The first version called the feed once per candidate day
and once per contract. Measured on the real run that was ~9s per call and 280-640 serial calls
per name: about 51 minutes per name, ~12.7 hours for a 15-name smoke, and hopeless at full
scale. It was also effectively serial while the Standard tier allows 4 concurrent requests, and
it wrote nothing to disk, so a kill lost everything.

The fix is that `option_history_eod` accepts a DATE RANGE and `expiration="*"`, so ONE call
returns an entire year of the entire chain:

    AAPL 2019, max_dte=90  ->  203,666 deduped rows across 253 trading days in 49s, 11MB cached

That is 0.19s per trading day against ~9s before. Per name the pull drops from 280-640 calls to
22 (one EOD + one open-interest call per year), and afterwards every "chain on day D" and every
"contract's full history" is a SLICE of a cached frame rather than a network call.

WHAT IS CACHED, AND WHY IT IS SLIM. Only the columns the backtest actually uses are kept
(expiration, strike, right, date, bid, ask, volume, open_interest), downcast to float32/int32.
The full response is ~5x larger and nothing downstream reads the extra columns.

MAX_DTE IS 200, RAISED FROM 90 (audit O15). The original 90 covered what the options strategy
alone needs: the FRONT expiry (put/call ratio and ATM IV, always < ~10 DTE) and the 45-75 DTE
band the contract is picked from. What it foreclosed is U1 — the equity composite's horizon is
63 TRADING days, which is ~92 CALENDAR days, so the natural option tenor for testing the stock
signal as an options entry sat exactly at, and just past, the old ceiling. It also made
`atm_iv_180` 100% empty and put LEAPS, calendars and diagonals out of reach entirely.

The old comment claimed raising it "multiplies storage for contracts nothing reads". MEASURED,
on identical spans (March 2023): rows and bytes go up x1.19 (BKNG) to x1.30 (AAPL), and
wall-clock is UNCHANGED (x0.90-1.10). Not a multiple — beyond 90 DTE there are no weeklies,
only monthlies and quarterlies, so the added tenor is sparse, and the call is dominated by the
server-side scan rather than the payload.

DEPTH IS RECORDED PER SYMBOL-YEAR, AND UPGRADING IS OPT-IN. A cache mined at two different
ceilings is exactly this project's favourite bug: 90-DTE and 200-DTE years are indistinguishable
on disk, and a consumer reading a 150-DTE contract would silently get nothing for some names and
data for others. Every cached year now carries a `.dte` sidecar naming the ceiling that produced
it (absent = 90, which is what every pre-O15 file is), and `depth_report()` counts them.
`ensure_year` still SKIPS a shallower cached year by default, so raising this constant does not
silently trigger a re-pull of all 3,140 cached symbol-years the next time the breadth miner
runs. Only `ThetaBulk(max_dte=200, upgrade_depth=True)` — what `dte_extend.py` uses — re-pulls
to deepen.

RESUMABILITY. Each symbol-year is written atomically (temp file then replace) so a kill mid-write
cannot leave a half-file that later loads as truncated data. `ensure_year` skips anything already
on disk, so a re-run costs nothing for work already done - the failure mode that lost the first
run's progress entirely.

--------------------------------------------------------------------------------------------
WHY QUARTERLY CHUNKS, RETRY, AND AN EXPLICIT GAP RECORD (added after the first bulk run).

The first bulk attempt requested a whole year per call and had NO retry. Measured on the real
run, 11 of 30 year-pulls died with gRPC `_MultiThreadedRendezvous` errors - and because there
was no retry and no record, those years were SILENTLY ABSENT. AAPL was missing 2021, 2022 and
2023 while the run carried on as if the history were complete. A backtest that reports a
confident verdict with a third of its data missing is precisely the silent-corruption failure
this project has been bitten by four times.

Three fixes, in order of importance:

  1. GAPS ARE RECORDED, NOT SWALLOWED. A symbol-year that cannot be fetched writes a `.missing`
     marker, and `coverage_report` returns exactly which symbol-years are absent. The backtest
     REFUSES to score a symbol with an incomplete history rather than quietly under-sampling it.
  2. QUARTERLY CHUNKS. The failures are size-related: a quarter of AAPL 2022 returns in 18s
     where the full year fails outright. A year is assembled from four quarter calls, and a
     quarter that fails is retried before the year is abandoned.
  3. TIMEOUT + BACKOFF. Each call runs with a deadline so a hung stream cannot pin a worker,
     and transient failures are retried with increasing backoff. "No data" is still treated as
     an answer, not an error, so empty quarters cost nothing.

`strike_range` was tested as a way to cut payload and REJECTED: it cut rows 38% but made the
call 6x SLOWER (110s vs 18s), because the filtering happens server-side after the scan.

--------------------------------------------------------------------------------------------
TWO FURTHER BUGS, both caught by running the status tool against the live job rather than
waiting for the run to finish.

  A. "MISSING" WAS STICKY. A failed year wrote a marker that blocked every future retry, so one
     transient gRPC error removed that year permanently. AAPL 2026 was marked missing, yet
     re-requesting 2026Q1 by hand returned 83,040 rows immediately - the failure was transient
     and the marker was the real damage. Markers are now split:
        `.empty`   - the feed genuinely has no data (NoDataFoundError). COVERED, never refetched.
        `.missing` - the fetch FAILED. Counted as a gap and RETRIED on the next run.
     The distinction matters because "this ticker did not trade yet" and "the request broke"
     look identical downstream and have opposite correct responses.

  B. TICKER RENAMES BREAK THE JOIN. Options are stored under the symbol as it was AT THE TIME.
     META returns nothing before June 2022; FB returns 101,544 rows for 2019Q1 alone. Scoring
     META on 2022+ only, while treating the earlier years as gaps, would silently drop six years
     of a name we do have data for. `ALIASES` maps a current ticker to its historical symbols and
     `_fetch_span` retries an empty span under the alias, which also handles the mid-year
     boundary (FB until 2022-06-09, META after) without hard-coding the date.

     This is the same class of problem as the today-snapshot caveats already recorded for the
     P10 sector map and the P24.2 CIK map: an identifier that is correct now is not correct for
     history.

     C. AN ALIAS POINTED AT A DIFFERENT LIVE COMPANY, AND SILENTLY CACHED ITS CHAINS.
     `ALIASES["WBD"] = ["T"]` was wrong: Warner Bros Discovery is the continuation of the
     DISCOVERY share line (DISCA), not of AT&T. AT&T distributed WBD shares and went on
     trading under `T` throughout. Because the fallback fires whenever the current symbol
     returns an empty span, every WBD year before the April 2022 listing fell through to `T`
     and cached AT&T's option chains under WBD. Measured: WBD 2016-2021 were byte-identical
     to T (966,790 rows, identical keys AND identical bids) and WBD 2022 Jan-Mar likewise
     (33,964 rows) - about 1.00M rows of one company's options filed under another's.

     The generic defect is that a WRONG alias and a RIGHT alias are indistinguishable at the
     point of use: both return rows. So the mapping is no longer trusted to be hand-checked.
     A genuine predecessor STOPS trading when the successor starts, so predecessor and
     successor data must not OVERLAP in time. `alias_overlap_conflicts()` checks exactly that
     against whatever is on disk, and `WBD -> DISCA` satisfies it (DISCA 2016-2021, WBD
     2022-2025, disjoint) where `WBD -> T` fails it in four separate years.

     Provenance is also recorded now: when a fallback supplies a span, the symbol-year gets an
     `.alias` sidecar naming the symbol the rows actually came from, so "these are not this
     ticker's own rows" is a fact on disk rather than something to be re-derived.
"""
from __future__ import annotations

import datetime as dt
import os
import pickle
import threading
import time
from typing import Optional

def _main_repo_root() -> str:
    """The PRIMARY checkout's root, even when we are running inside a git worktree.

    `data/` is gitignored and therefore exists ONLY in the primary checkout — a worktree gets
    an empty `data/` of its own. With a RELATIVE cache root, running the miner from a worktree
    silently mined into a phantom directory next to the real 16GB cache and re-pulled
    everything, while `.env` (also gitignored, also primary-only) failed to resolve so the
    ThetaData key came back empty and every name "failed its probe". Both failures are silent.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # <repo>/valuation
    root = os.path.dirname(here)
    marker = os.path.join(root, ".git")
    if os.path.isfile(marker):          # a worktree: .git is a FILE pointing at the real gitdir
        try:
            with open(marker, encoding="utf-8") as f:
                gitdir = f.read().split("gitdir:", 1)[1].strip()
            # <primary>/.git/worktrees/<name>  ->  <primary>
            parts = gitdir.replace("\\", "/").split("/.git/worktrees/")
            if len(parts) == 2 and os.path.isdir(parts[0]):
                return os.path.normpath(parts[0])
        except (OSError, IndexError):
            pass
    return root


REPO_ROOT = _main_repo_root()
# Absolute, and anchored on the PRIMARY checkout. Never make this relative again.
CACHE_ROOT = os.path.join(REPO_ROOT, "data", "options")
MAX_DTE = 200                  # audit O15, raised from 90. See the module docstring.
LEGACY_MAX_DTE = 90            # what every symbol-year cached before O15 was pulled at. A
                               # cached year with no `.dte` sidecar is assumed to be this, which
                               # is a fact about the code's history, not a guess: MAX_DTE was 90
                               # from the first bulk run until 2026-08-05.
WORKERS = 4                  # ThetaData Standard allows 4 concurrent requests
CALL_TIMEOUT = 75              # seconds. Was 180, which let ONE pathological symbol-year burn
                               # 8 calls x 3 retries x 180s = 72 minutes, and ten such years
                               # half a day - enough to stall an unattended queue on one name.
                               # A healthy quarter returns in ~5-20s, so 75s is generous.
RETRIES = 2                    # a call that fails twice at 75s is not going to succeed
MIN_SPAN_DAYS = 20             # floor for adaptive splitting; below a month, stop halving

# --- throughput controls (added after names took ~17 min each) ------------------------------
# A name that fails once keeps its SMALLER chunk size for every remaining span, instead of
# rediscovering the failure quarter by quarter. Paying the ~150s failure cost once per name
# rather than once per quarter is the single biggest win here.
DEFAULT_CHUNK_DAYS = 30        # a MONTH, not a quarter. Measured: quarterly spans were both
                               # slower and failure-prone. AAPL is 110,416 rows in 41.4s per
                               # quarter but 34,996 in 9.0s per month (3 months = 27s), and
                               # BKNG's quarter times out at 396,240 rows / 72.8s while its
                               # month returns in 20.9s. Smaller responses are simply more
                               # efficient here, so monthly is faster AND removes the failure
                               # -discovery cost that made every large name burn ~150s.
MIN_CHUNK_DAYS = 22            # ~a month; BKNG returns 122,488 rows in 30s at this size
NAME_BUDGET_S = 900            # hard wall-clock ceiling per symbol-year; then give up
MAX_MISSING_ATTEMPTS = 2       # after this many failed runs a year is EXHAUSTED, not retried
BACKOFF = 4.0                  # seconds, multiplied by attempt number

# --- open-interest quality (audit B4, writer side) ------------------------------------------
# B4 fixed the two CONSUMERS of the -1 sentinel (`_oi_sum` masks it, the MIN_OI gate no longer
# reads it as zero). It did NOT touch this file, so the WRITER still manufactured it: when the
# separate open-interest call faulted, every row of the span got -1 and the year was cached as
# COMPLETE, indistinguishable from a year whose contracts genuinely have no OI at source.
# A symbol-year below this floor now gets an `.oi_degraded` sidecar recording the measured
# coverage and whether the OI CALL faulted, so the two causes can be told apart and the bad
# spans can be targeted for re-mine instead of being invisible.
OI_COVERAGE_FLOOR = 0.95       # pre-committed 2026-08-04, BEFORE the audit was run
CLIENT_RESET_AFTER_FAULTS = 6  # consecutive faults => the gRPC channel is dead, rebuild it
KEEP = ["expiration", "strike", "right", "date", "bid", "ask", "volume", "open_interest"]

# Current ticker -> symbols it traded under earlier. Options history is stored under the
# symbol of the day, so without this a renamed name silently loses its pre-rename history.
#
# THE ONE RULE: an alias must be a symbol the company ITSELF traded under and has since
# STOPPED using. It must never be a ticker that is still live as some other company, because
# the fallback fires on any empty span and cannot tell a correct alias from a wrong one - both
# return rows. `WBD -> T` broke this rule and cached ~1.00M rows of AT&T chains under WBD
# (docstring note C). Anything added here must satisfy `alias_overlap_conflicts()`.
#
# Every mapping below was verified against the feed on 2026-08-06 by probing a 10-day span in
# a year on each side of the rename; the predecessor's data ends where the successor's begins.
ALIASES = {
    "META": ["FB"],          # renamed 2022-06
    "GOOGL": ["GOOG"],       # NOTE: both share classes trade concurrently, so this is not a
                             # rename and the fallback never fires (GOOGL has no empty spans).
                             # Kept only because removing it is a behaviour change with no
                             # measured benefit; `alias_overlap_conflicts()` reports it.
    "RTX": ["UTX"],          # United Technologies -> Raytheon Technologies, 2020-04
    "WBD": ["DISCA"],        # CORRECTED. Was ["T"], which is a different, still-live company.
                             # Probed: DISCA 2016:700 2018:460 2021:2208 2022:0 2024:0 rows;
                             # WBD 2016:0 2018:0 2021:0 2022:6612 2024:2116. Disjoint.
    "BNY": ["BK"],           # Bank of New York Mellon, BK -> BNY. Probed 2018 BK 5,154 rows.
    "FISV": ["FI"],          # Fiserv, FISV -> FI (2023). FISV covers <=2023 and is tried
                             # FIRST, so the 2013-2021 window in which `FI` was an unrelated
                             # live ticker is never reached - the fallback only fires for
                             # spans where FISV itself is empty, i.e. 2023-08 onward.
    "MRSH": ["MMC"],         # Marsh & McLennan, MMC -> MRSH. Probed 2018 MMC 680 rows.
    "UI": ["UBNT"],          # Ubiquiti, UBNT -> UI (2019). Recovers the early years only:
                             # probed 2024 returns 0 rows under BOTH symbols, so the recent
                             # history is genuinely absent from this feed, not mis-keyed.
    "XYZ": ["SQ"],           # Block, SQ -> XYZ (2025). Probed 2018 SQ 7,388 rows.
}

_LOAD_LOCK = threading.Lock()


def _log(m):
    print(f"[theta-bulk] {m}", flush=True)


def _key_from_repo_env() -> str:
    """Read THETADATA_API_KEY from the PRIMARY checkout's .env.

    `thetadata_provider._api_key()` looks in `os.getcwd()` and its own repo root; from a
    worktree both miss, because `.env` is gitignored and primary-only. The value is never
    logged.
    """
    p = os.path.join(REPO_ROOT, ".env")
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip().startswith("THETADATA_API_KEY") and "=" in line:
                    return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def year_path(symbol: str, year: int, root: str = CACHE_ROOT) -> str:
    return os.path.join(root, symbol.upper(), f"{symbol.upper()}-{year}.pkl")


def oi_coverage(df) -> float:
    """Fraction of rows whose open interest is KNOWN. -1 is the feed's unknown sentinel."""
    if df is None or len(df) == 0 or "open_interest" not in df.columns:
        return 0.0
    return float((df["open_interest"] >= 0).mean())


def cached_dte(symbol: str, year: int, root: str = CACHE_ROOT) -> int:
    """The DTE ceiling a cached symbol-year was pulled at, or 0 if it is not cached (audit O15).

    A missing `.dte` sidecar beside an existing pickle means LEGACY_MAX_DTE: every file written
    before O15 was pulled at 90, so this is recorded history rather than an assumption. Without
    this, a cache mined at two ceilings is indistinguishable on disk and a consumer asking for a
    150-DTE contract gets data for some names and silence for others, with nothing to show why.
    """
    path = year_path(symbol, year, root)
    if not os.path.exists(path):
        return 0
    try:
        with open(path + ".dte", encoding="utf-8") as f:
            return int(f.read().strip().split()[0])
    except (OSError, ValueError, IndexError):
        return LEGACY_MAX_DTE


def depth_report(root: str = CACHE_ROOT) -> dict:
    """How many cached symbol-years sit at each DTE ceiling, and which names are fully deep.

    The point is that a PARTIAL deepening stays visible. After O15 only the most liquid ~100
    names are at 200; everything else is still 90, and any claim about term structure has to
    say which set it is talking about.
    """
    by_depth, by_name = {}, {}
    if not os.path.isdir(root):
        return {"by_depth": {}, "names_fully_deep": [], "names_mixed": [], "max_dte": MAX_DTE}
    for sym in sorted(os.listdir(root)):
        d = os.path.join(root, sym)
        if not os.path.isdir(d):
            continue
        depths = []
        for fn in sorted(os.listdir(d)):
            if not (fn.endswith(".pkl") and "-" in fn):
                continue
            try:
                yr = int(fn.rsplit("-", 1)[1][:-4])
            except ValueError:
                continue
            dep = cached_dte(sym, yr, root)
            depths.append(dep)
            by_depth[dep] = by_depth.get(dep, 0) + 1
        if depths:
            by_name[sym] = depths
    deep = sorted(s for s, ds in by_name.items() if ds and min(ds) >= MAX_DTE)
    mixed = sorted(s for s, ds in by_name.items() if ds and min(ds) < MAX_DTE <= max(ds))
    return {"by_depth": {str(k): v for k, v in sorted(by_depth.items())},
            "names_fully_deep": deep, "names_mixed": mixed,
            "n_names": len(by_name), "max_dte": MAX_DTE}


def _cached_years(symbol: str, root: str = CACHE_ROOT) -> set:
    """Years for which `symbol` has a NON-EMPTY cached frame."""
    d = os.path.join(root, symbol.upper())
    if not os.path.isdir(d):
        return set()
    out = set()
    for fn in os.listdir(d):
        if fn.endswith(".pkl") and "-" in fn:
            try:
                out.add(int(fn.rsplit("-", 1)[1][:-4]))
            except ValueError:
                pass
    return out


def alias_overlap_conflicts(aliases: dict = None, root: str = CACHE_ROOT) -> dict:
    """Aliases whose predecessor traded CONCURRENTLY with the successor. Empty dict = clean.

    A rename is a handover: the old symbol stops the moment the new one starts, so the two
    must never both have data for the same year. A ticker that overlaps its "successor" is
    therefore not a predecessor at all - it is a different, still-live company, and every
    empty span of the successor will be silently filled with ITS chains.

    That is not hypothetical. `WBD -> T` overlapped in 2022, 2023, 2024 and 2025 and had
    already written ~1.00M rows of AT&T's options into WBD's cache, byte-identical to T's own
    frames, before this check existed. Overlap is what distinguishes that case from the four
    correct mappings, so it is the thing worth testing.

    Judged on CACHED data only - it is an audit of what is on disk, not a network call - so a
    pair with nothing cached simply returns no evidence rather than a false clean bill.
    """
    aliases = ALIASES if aliases is None else aliases
    out = {}
    for cur, older in aliases.items():
        cur_years = _cached_years(cur, root)
        for old in older:
            shared = sorted(cur_years & _cached_years(old, root))
            if shared:
                out[f"{cur}<-{old}"] = shared
    return out


def reused_ticker_suspects(root: str = CACHE_ROOT) -> dict:
    """Cache directories that may hold MORE THAN ONE COMPANY. Empty dict = clean.

    `alias_overlap_conflicts()` above cannot see this class, because no alias is involved. The
    miner asks the feed for a ticker in every year and the feed answers for whoever HELD that
    ticker at the time, so a symbol that changed hands comes back as one continuous-looking
    history made of two companies.

    `COR` is the live example. CoreSite Realty held it until American Tower acquired the company
    in 2021-12; Cencora took it in 2023-08 on renaming from AmerisourceBergen. The cache holds
    CoreSite for 2016-2021 and Cencora for 2023-2025 in one directory, and the median strike
    steps 130 -> 165 across the join, which is the two underlyings' price levels, not a move.

    THE SIGNATURE IS THE INTERIOR HOLE, and it is worth being precise about why: a listed
    company does not stop having options for a year and then resume, but a ticker between owners
    has nothing to answer with. So an uncached year with cached years on BOTH sides is the
    cheap, specific marker of a handover. It reads filenames only -- no pickles, no network --
    so it is free enough to run on every status call.

    A MID-HISTORY `.empty` COUNTS AS A HOLE, and getting this backwards would have missed the
    one name the function exists for. Elsewhere `.empty` means "the feed genuinely has nothing,
    so the year is COVERED rather than a gap" -- true for LEADING years (pre-IPO, pre-rename)
    and TRAILING ones (delisted). In the interior it means the opposite: COR-2022 is `.empty`
    precisely BECAUSE the ticker belonged to nobody that year, which is the handover itself.

    This is a SCREEN, NOT A VERDICT. A hole can also be an ordinary outage (the May-2022 source
    defect put one in every name it touched until the retry pass filled them), so a hit means
    "establish which company this is before using the name", not "this data is wrong". The
    reverse error is the expensive one: a blended two-company series is invisible downstream,
    because both halves are well-formed and coverage looks complete.
    """
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, name)):
            continue
        yrs = sorted(_cached_years(name, root))
        if len(yrs) < 2:
            continue
        hole = [y for y in range(yrs[0], yrs[-1] + 1) if y not in yrs]
        if hole:
            out[name] = {"cached": yrs, "hole": hole,
                         "empty_marked": [y for y in hole
                                          if os.path.exists(year_path(name, y, root) + ".empty")]}
    return out


def collapsed_year_suspects(root: str = CACHE_ROOT, ratio: float = 0.2) -> dict:
    """Years that hold FAR less data than both neighbours. Empty dict = clean.

    The companion to `reused_ticker_suspects()`, for the handover that leaves NO hole. When a
    ticker changes hands mid-year the feed answers for the new holder, so the year is neither
    empty nor missing -- it is present, well-formed, and wrong. Nothing above catches that.

    `META` is the live example, and it is a top-ten name. Facebook renamed to Meta in 2022-06,
    so `ALIASES["META"] = ["FB"]` supplies 2016-2020 correctly. But through the back half of
    2021 the `META` ticker belonged to a ~$15 company, and the feed answered with ITS chains:
    META-2021 holds 9,398 rows over 2021-07-08..12-31 at strikes 8-22, between years of 247,139
    and 171,788 rows at strikes 130-350. Facebook's actual 2021 was never fetched, because the
    alias fallback only fires on an EMPTY span and this span was not empty.

    THAT IS THE STRUCTURAL POINT, and it is why a third screen exists rather than a wider alias
    table: an alias can only rescue a year the current symbol has NOTHING for. Against a reused
    ticker the current symbol always has something, so no alias mapping can ever fix this class.

    Measured on FILE SIZE, not row counts, so it costs a stat() per file and never unpickles:
    META-2021 is 0.44MB between 11.62MB and 8.08MB, a 26x collapse that no threshold worth
    arguing about would miss. A SCREEN, NOT A VERDICT -- a genuinely thin year (a name that
    briefly lost liquidity) looks the same from here and has to be told apart by looking.
    """
    out = {}
    if not os.path.isdir(root):
        return out
    for name in sorted(os.listdir(root)):
        if not os.path.isdir(os.path.join(root, name)):
            continue
        size = {}
        for y in _cached_years(name, root):
            try:
                size[y] = os.path.getsize(year_path(name, y, root))
            except OSError:
                continue
        for y in sorted(size):
            prev, nxt = size.get(y - 1), size.get(y + 1)
            if prev and nxt and size[y] < ratio * prev and size[y] < ratio * nxt:
                out.setdefault(name, []).append(
                    {"year": y, "mb": round(size[y] / 1e6, 2),
                     "prev_mb": round(prev / 1e6, 2), "next_mb": round(nxt / 1e6, 2)})
    return out


class ThetaBulk:
    """Year-chunked option history. Degrades to a no-op with no API key."""

    def __init__(self, api_key: Optional[str] = None, root: str = CACHE_ROOT,
                 max_dte: int = MAX_DTE, max_years_in_memory: int = 6,
                 upgrade_depth: bool = False):
        from .thetadata_provider import _api_key

        self.root = root
        self.max_dte = max_dte
        # OFF by default on purpose (audit O15). Raising MAX_DTE 90 -> 200 would otherwise make
        # every one of the 3,140 already-cached symbol-years look stale, and the next ordinary
        # breadth-mining run would silently re-pull the entire 17GB cache. Deepening is a
        # deliberate job (`dte_extend.py`), not a side effect of a constant changing.
        self.upgrade_depth = upgrade_depth
        self._key = api_key if api_key is not None else (_api_key() or _key_from_repo_env())
        self._client = None
        self._faults = 0               # consecutive faults; resets the channel when sustained
        self._tl = threading.local()   # per-thread OI-call fault count for the span in flight
        self._err = None if self._key else "no THETADATA_API_KEY"
        self._mem = {}
        self._mem_order = []
        self._max_mem = max_years_in_memory
        self._client_lock = threading.Lock()
        self._chunk_days = {}          # symbol -> span size that actually works
        self._budget_start = {}        # symbol -> wall-clock start for its pull

    def status(self) -> dict:
        return {"available": bool(self._key), "reason": self._err, "root": self.root,
                "max_dte": self.max_dte, "upgrade_depth": self.upgrade_depth,
                "workers": WORKERS}

    def needs_pull(self, symbol: str, year: int) -> bool:
        """Does this symbol-year still need fetching? The ONE place that decides.

        `prefetch` used to make this call itself with a bare `os.path.exists`, which meant any
        rule added to `ensure_year` was bypassed by the bulk path — a deep re-mine would have
        skipped every name and reported success having done nothing.
        """
        path = year_path(symbol, year, self.root)
        if os.path.exists(path + ".exhausted"):
            # Checked FIRST, and for a cached year too: a year that repeatedly fails to deepen
            # would otherwise be re-queued on every run forever, since the shallow frame on disk
            # keeps it looking eligible.
            return False
        if os.path.exists(path):
            return self.upgrade_depth and cached_dte(symbol, year, self.root) < self.max_dte
        return not os.path.exists(path + ".empty")

    def _cli(self):
        # One client, guarded: the gRPC client is shared across the 4 worker threads.
        with self._client_lock:
            if self._client is None:
                if not self._key:
                    return None
                try:
                    import thetadata as td
                    self._client = td.ThetaClient(api_key=self._key, dataframe_type="pandas")
                except Exception as e:                                   # noqa: BLE001
                    self._err = f"{type(e).__name__}: {e}"
                    return None
            return self._client

    # ---------------- fetching ----------------
    def _call_with_timeout(self, fn, **kw):
        """Run a feed call with a deadline and backoff. None means 'no data' or gave up.

        THE DEADLINE IS ENFORCED BY ABANDONING THE CALL, NOT BY WAITING FOR IT.

        This used to read `with ThreadPoolExecutor(max_workers=1) as one: ...
        result(timeout=CALL_TIMEOUT)`. The `with` block's `__exit__` calls
        `shutdown(wait=True)`, so on timeout the code logged "timeout after 75s" and then
        **blocked until the runaway call finished anyway**. The deadline controlled when a
        message was printed and nothing else; `CALL_TIMEOUT` had never once bounded a call.

        Measured cost of that: **TXRH took 39,526s — 11 hours — for nine year-files, and still
        lost 2023 and 2025**, while GRAB did the same work 200s later in 200s. TXRH is not a
        slow name: a 30-day span returns 4,020 rows in 3.7s when probed directly. The hours
        were a transient hang the miner had no way to escape, because `_fetch_year`'s
        `NAME_BUDGET_S` is only checked BETWEEN spans and could not fire while blocked inside
        one.

        The subtler damage: a hung call never returns, so it never became a fault, so
        `_note_fault` never counted it and the dead-channel detector never fired through an
        11-hour stall. A hang is now counted as a fault.

        TWO CORRECTIONS TO THAT ACCOUNT, both from re-reading the logs on 2026-08-07 rather
        than from reasoning:

        * "the detector was bypassed" OVERSTATED IT. It was blind to HANGS specifically, not
          broken in general — on ordinary gRPC errors it worked and demonstrably fired, twice
          ("6 consecutive faults: rebuilding the client", `BREADTH_RUN2.log`). Only the hang
          path was invisible to it.
        * "the run reported 0 faults" WAS READ OUT OF THE WRONG FILE. `MINING_PROGRESS.txt`
          carries only `[mine]` lines and has never contained a single `[theta-bulk]` line, so
          it could not have shown a fault whatever the detector did. The faults were in
          `BREADTH_RUN*.log` all along: 81 give-ups, 18 chunk halvings, 3 timeouts, 2 client
          rebuilds, 2 budget exhaustions. **A statistic quoted from a stream that does not
          carry it is not evidence, and this one was quoted repeatedly.**

        FAULT COUNTING IS DELIBERATELY ASYMMETRIC. A hang counts once per ABANDONED ATTEMPT
        plus once when the retries run out; an error counts once, only when it gives up. So a
        fully-hung call contributes 3 faults where a failing one contributes 1, and
        CLIENT_RESET_AFTER_FAULTS is reached after ~2 hung calls against 6 failing ones. That
        is intended — a hang is the stronger evidence that the channel is dead, and it is the
        failure that costs hours rather than seconds — but it was measured, not designed, so it
        is written down here rather than left to be rediscovered.

        The abandoned worker is a DAEMON thread, so a call that never returns cannot pin the
        interpreter at exit the way an executor thread would.
        """
        for attempt in range(1, RETRIES + 1):
            box = {}

            def _run(_box=box):
                try:
                    _box["v"] = fn(**kw)
                except BaseException as e:                               # noqa: BLE001
                    _box["e"] = e

            th = threading.Thread(target=_run, daemon=True,
                                  name=f"theta-call-{kw.get('symbol', '?')}")
            th.start()
            th.join(CALL_TIMEOUT)
            if th.is_alive():
                _log(f"timeout after {CALL_TIMEOUT}s (attempt {attempt}/{RETRIES}); "
                     f"ABANDONING the call")
                self._note_fault()          # a hang is a channel symptom, not a free pass
                if attempt < RETRIES:
                    time.sleep(BACKOFF * attempt)
                continue
            if "e" in box:
                e = box["e"]
                # "No data" is an ANSWER (an empty quarter), not a fault worth retrying.
                if type(e).__name__ == "NoDataFoundError" or "No data found" in str(e):
                    return None
                if attempt == RETRIES:
                    _log(f"gave up after {RETRIES}: {type(e).__name__}")
                    self._note_fault()
                    return "FAILED"
                time.sleep(BACKOFF * attempt)
                continue
            return box["v"]
        self._note_fault()
        return "FAILED"

    def _note_fault(self):
        """A run of consecutive faults means the gRPC channel itself died; rebuild it.

        Measured: one unattended run pulled 318 names, then EVERY call from queue position 371
        to 826 failed with `_MultiThreadedRendezvous` — 455 names burned. A fresh process
        immediately pulled AAPL in 6.8s, so the feed was fine and the CHANNEL was dead. Nothing
        in the loop ever reset the client, so the miner could not recover from it in-process.
        """
        self._faults += 1
        if self._faults >= CLIENT_RESET_AFTER_FAULTS:
            with self._client_lock:
                self._client = None
            self._faults = 0
            _log(f"{CLIENT_RESET_AFTER_FAULTS} consecutive faults: rebuilding the client")

    def _note_ok(self):
        self._faults = 0

    def _fetch_span_once(self, symbol: str, start: dt.date, end: dt.date):
        """One EOD + one open-interest call for a span. Returns (frame_or_None, failed_bool)."""
        import pandas as pd

        cli = self._cli()
        if cli is None:
            return None, True
        tried = [symbol.upper()] + [a for a in ALIASES.get(symbol.upper(), [])]
        eod = None
        for sym in tried:
            # NOTE the ordering is load-bearing: the CURRENT symbol is always tried first, so a
            # fallback can only ever fill a span the name itself has no data for. That is what
            # keeps `FISV -> FI` safe across the years in which `FI` was an unrelated live
            # ticker. It is NOT enough on its own - see `alias_overlap_conflicts()`.
            eod = self._call_with_timeout(cli.option_history_eod, start_date=start, end_date=end,
                                          symbol=sym, expiration="*", max_dte=self.max_dte)
            if isinstance(eod, str):        # "FAILED" - a fault, not an absence; stop here
                return None, True
            if eod is not None and len(eod):
                symbol_used = sym
                break
        else:
            symbol_used = None
        if eod is None or len(eod) == 0:
            return None, False              # genuinely empty span, not a failure
        if symbol_used and symbol_used != symbol.upper():
            # An ALIAS supplied this span. Record it so the substitution is auditable on disk
            # instead of being invisible the way the AT&T-under-WBD rows were.
            try:
                self._tl.alias_used.add(symbol_used)
            except AttributeError:
                self._tl.alias_used = {symbol_used}
        eod = eod.copy()
        eod["date"] = pd.to_datetime(eod["created"]).dt.date
        eod = (eod.sort_values("created")
                  .drop_duplicates(subset=["date", "expiration", "strike", "right"],
                                   keep="last"))
        self._note_ok()                 # the EOD call returned, so the channel is alive
        oi = self._call_with_timeout(cli.option_history_open_interest, start_date=start,
                                     end_date=end, symbol=symbol_used or symbol.upper(),
                                     expiration="*", max_dte=self.max_dte)
        if isinstance(oi, str):
            # THE OI CALL FAULTED. Every row of this span is about to get the -1 unknown
            # sentinel. Record it so `ensure_year` can tell "the call broke" (retryable) from
            # "these contracts have no OI at source" (not retryable) instead of caching both
            # as an identical, complete-looking year.
            self._tl.oi_faults = getattr(self._tl, "oi_faults", 0) + 1
        if oi is not None and not isinstance(oi, str) and len(oi):
            oi = oi.copy()
            oi["date"] = pd.to_datetime(oi["timestamp"]).dt.date
            oi = (oi.sort_values("timestamp")
                    .drop_duplicates(subset=["date", "expiration", "strike", "right"],
                                     keep="last"))
            eod = eod.merge(oi[["date", "expiration", "strike", "right", "open_interest"]],
                            on=["date", "expiration", "strike", "right"], how="left")
        if "open_interest" not in eod.columns:
            eod["open_interest"] = None
        slim = eod[[c for c in KEEP if c in eod.columns]].copy()
        slim["expiration"] = pd.to_datetime(slim["expiration"]).dt.date
        for c in ("bid", "ask", "strike"):
            slim[c] = pd.to_numeric(slim[c], errors="coerce").astype("float32")
        slim["volume"] = pd.to_numeric(slim["volume"], errors="coerce").fillna(0).astype("int32")
        slim["open_interest"] = (pd.to_numeric(slim["open_interest"], errors="coerce")
                                 .fillna(-1).astype("int32"))
        slim["right"] = slim["right"].astype(str).str[0].str.upper()
        return slim.reset_index(drop=True), False


    def _fetch_span(self, symbol: str, start: dt.date, end: dt.date, depth: int = 0):
        """Fetch a span, HALVING it on failure until it succeeds or hits MIN_SPAN_DAYS.

        Response size, not flakiness, is what makes these calls fail. Measured: a quarter of
        BKNG is 396,240 rows and takes 72.8s against a 75s deadline, because it is the
        highest-priced US stock and carries an enormous strike ladder; the same quarter of AAPL
        is 110,416 rows in 41.4s. So BKNG failed whenever the connection was under any load,
        and it failed the SAME way every run - which is why BKNG and NOW each came back missing
        exactly four consecutive years rather than random ones.

        A longer deadline is the wrong fix: it makes a slow name slower without making a large
        response smaller. Halving the span halves the rows (BKNG one month: 122,488 rows in
        30.0s), and it adapts automatically to whatever a name's chain size demands rather than
        needing a per-name tuning table.
        """
        import pandas as pd

        df, failed = self._fetch_span_once(symbol, start, end)
        if not failed:
            return df, False
        span_days = (end - start).days
        if span_days <= MIN_SPAN_DAYS:
            return df, True
        mid = start + dt.timedelta(days=span_days // 2)
        _log(f"{symbol} {start}..{end} failed; splitting ({span_days}d -> 2x{span_days//2}d)")
        a, fa = self._fetch_span(symbol, start, mid, depth + 1)
        b, fb = self._fetch_span(symbol, mid + dt.timedelta(days=1), end, depth + 1)
        parts = [x for x in (a, b) if x is not None and len(x)]
        if not parts:
            return None, (fa or fb)
        return pd.concat(parts, ignore_index=True), (fa or fb)

    def _fetch_year(self, symbol: str, year: int):
        """A year assembled from adaptive chunks. Returns (frame_or_None, any_chunk_failed).

        Two behaviours matter for throughput:

        * THE CHUNK SIZE IS REMEMBERED PER NAME. Response size, not flakiness, is what fails:
          a quarter of BKNG is 396,240 rows and takes 72.8s against a 75s deadline, while the
          same quarter of AAPL is 110,416 rows in 41.4s. Rediscovering that quarter by quarter
          cost ~150s of dead time four times over; now the first failure halves the chunk for
          the REST of the name.
        * THERE IS A WALL-CLOCK BUDGET. Past NAME_BUDGET_S the name is abandoned with whatever
          it has. One pathological symbol must never consume a whole unattended run.
        """
        import pandas as pd

        today = dt.date.today()
        t_start = time.time()
        chunk = self._chunk_days.get(symbol.upper(), DEFAULT_CHUNK_DAYS)
        parts, failed = [], False
        self._tl.oi_faults = 0         # counts OI-call faults across this year's spans
        self._tl.alias_used = set()    # which symbols actually supplied this year's rows

        cur = dt.date(year, 1, 1)
        year_end = min(dt.date(year, 12, 31), today)
        while cur <= year_end:
            if time.time() - t_start > NAME_BUDGET_S:
                _log(f"{symbol} {year}: budget {NAME_BUDGET_S}s exhausted; abandoning the rest")
                failed = True
                break
            span_end = min(cur + dt.timedelta(days=chunk - 1), year_end)
            df, fail = self._fetch_span_once(symbol, cur, span_end)
            if fail and chunk > MIN_CHUNK_DAYS:
                # Halve for this span AND every later one - the name has told us its size.
                chunk = max(MIN_CHUNK_DAYS, chunk // 2)
                self._chunk_days[symbol.upper()] = chunk
                _log(f"{symbol}: chunk -> {chunk}d for the rest of this name")
                continue                      # retry the same start at the smaller size
            if fail:
                failed = True
            if df is not None and len(df):
                parts.append(df)
            cur = span_end + dt.timedelta(days=1)

        if not parts:
            return None, failed
        out = pd.concat(parts, ignore_index=True)
        out = out.drop_duplicates(subset=["date", "expiration", "strike", "right"], keep="last")
        out["right"] = out["right"].astype("category")
        return out.reset_index(drop=True), failed

    def ensure_year(self, symbol: str, year: int) -> bool:
        """Pull + cache one symbol-year unless already on disk. Atomic write; resumable."""
        path = year_path(symbol, year, self.root)
        if os.path.exists(path):
            if not (self.upgrade_depth
                    and cached_dte(symbol, year, self.root) < self.max_dte):
                return True         # cached, and deep enough for what was asked for
            # Deepening: keep the shallow frame until the deeper pull has proven itself. A bad
            # network day must never be able to trade good 90-DTE data for nothing.
            _log(f"{symbol} {year}: deepening "
                 f"{cached_dte(symbol, year, self.root)} -> {self.max_dte} DTE")
        if os.path.exists(path + ".empty"):
            return True          # genuinely no data (pre-IPO / pre-rename): covered, not a gap
        if os.path.exists(path + ".exhausted"):
            # Tried MAX_MISSING_ATTEMPTS times across runs and never succeeded. Retrying it
            # again is the blackhole that made every run spend ~17 minutes on the same name.
            return False
        df, failed = self._fetch_year(symbol, year)
        if df is None or len(df) == 0:
            # Distinguish "the feed has nothing" from "the request broke". A silently-absent
            # year is how the first run nearly reported a verdict on a third of its data gone.
            marker = ".missing" if failed else ".empty"
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                attempts = 0
                if failed and os.path.exists(path + ".missing"):
                    try:
                        attempts = int(open(path + ".missing").read().split()[0])
                    except (OSError, ValueError, IndexError):
                        attempts = 1
                attempts += 1
                if failed and attempts >= MAX_MISSING_ATTEMPTS:
                    # Give up permanently rather than re-burning the budget every run.
                    with open(path + ".exhausted", "w", encoding="utf-8") as f:
                        f.write(f"{attempts} failed attempts, last "
                                f"{dt.date.today().isoformat()}\n")
                    try:
                        os.remove(path + ".missing")
                    except OSError:
                        pass
                    _log(f"{symbol} {year}: EXHAUSTED after {attempts} attempts; will not retry")
                else:
                    with open(path + marker, "w", encoding="utf-8") as f:
                        f.write(f"{attempts} {'fetch failed' if failed else 'no data'} "
                                f"{dt.date.today().isoformat()}\n")
            except OSError:
                pass
            return not failed
        if failed:
            # Partial year: do NOT cache it as if complete.
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path + ".missing", "w", encoding="utf-8") as f:
                    f.write(f"partial (a quarter failed) {dt.date.today().isoformat()}\n")
            except OSError:
                pass
            return False
        # OPEN-INTEREST QUALITY GATE (audit B4, writer side). Record the measured coverage and
        # whether the OI call itself faulted, so a degraded year is visible on disk instead of
        # looking identical to a clean one. The frame is still cached either way -- the EOD data
        # is expensive and valid; it is the OI column that is unknown.
        cov = oi_coverage(df)
        oi_faults = int(getattr(self._tl, "oi_faults", 0))
        deg = path + ".oi_degraded"
        if cov < OI_COVERAGE_FLOOR:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(deg, "w", encoding="utf-8") as f:
                    f.write(f"coverage {cov:.6f} floor {OI_COVERAGE_FLOOR} "
                            f"oi_call_faults {oi_faults} {dt.date.today().isoformat()}\n")
            except OSError:
                pass
            _log(f"{symbol} {year}: OI coverage {cov:.1%} < {OI_COVERAGE_FLOOR:.0%} "
                 f"({oi_faults} OI-call faults)")
        elif os.path.exists(deg):
            try:
                os.remove(deg)          # recovered on re-mine
            except OSError:
                pass
        # DEEPENING MUST NOT LOSE ROWS (audit O15). A 200-DTE pull of a span is a strict
        # SUPERSET of the 90-DTE pull of that same span, so a deeper frame with FEWER rows means
        # the pull was partial in some way the failure flags did not catch. Keep the shallow
        # frame in that case: it is real, expensive data and the deeper one is not proven.
        if os.path.exists(path):
            old = self._year_frame(symbol, year)
            if old is not None and len(old) > len(df):
                _log(f"{symbol} {year}: deeper pull returned {len(df):,} rows < cached "
                     f"{len(old):,}; KEEPING the shallow frame")
                return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + f".tmp{os.getpid()}"
        try:
            with open(tmp, "wb") as f:
                pickle.dump(df, f, protocol=5)
            os.replace(tmp, path)                 # atomic: a kill cannot leave a partial file
            with open(path + ".dte", "w", encoding="utf-8") as f:
                f.write(f"{self.max_dte} pulled {dt.date.today().isoformat()}\n")
            # PROVENANCE. If any span of this year came from an alias, say so on disk. Without
            # this the AT&T-under-WBD rows were indistinguishable from WBD's own.
            used = sorted(getattr(self._tl, "alias_used", ()) or ())
            if used:
                with open(path + ".alias", "w", encoding="utf-8") as f:
                    f.write(f"{','.join(used)} supplied rows for {symbol.upper()} {year} "
                            f"{dt.date.today().isoformat()}\n")
            # A SUCCEEDED YEAR MUST NOT KEEP ITS FAILURE MARKER. `.oi_degraded` above is
            # already cleared on recovery; `.missing`/`.empty` were not, so a year that failed
            # once and succeeded later kept a marker contradicting the pickle beside it. Five
            # names (CMG, DHI, FNV, MCD, RKLB) carried a `.missing` for 2022 while holding a
            # complete 2022 frame, which made the May-2022 damage look ~5x worse than it was.
            #
            # It is not only cosmetic: `ensure_year` reads the attempt count out of `.missing`,
            # so a stale one means the NEXT genuine failure starts partway to
            # MAX_MISSING_ATTEMPTS and can be retired to `.exhausted` early -- a year given up
            # on for failures it already recovered from.
            for stale in (path + ".missing", path + ".empty"):
                if os.path.exists(stale):
                    try:
                        os.remove(stale)
                    except OSError:
                        pass
            with _LOAD_LOCK:
                self._mem.pop((symbol.upper(), year), None)  # in-memory copy is now stale
        except OSError as e:
            _log(f"write failed {path}: {e}")
            try:
                os.remove(tmp)
            except OSError:
                pass
            return False
        return True

    def prefetch(self, symbols, years, workers: int = WORKERS) -> dict:
        """Bulk pull with the tier's 4 concurrent requests. Skips anything already cached."""
        from concurrent.futures import ThreadPoolExecutor, as_completed

        jobs = [(s, y) for s in symbols for y in years if self.needs_pull(s, y)]
        got = miss = 0
        t0 = time.time()
        if not jobs:
            return {"fetched": 0, "missing": 0, "already_cached": len(symbols) * len(years),
                    "seconds": 0.0}
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(self.ensure_year, s, y): (s, y) for s, y in jobs}
            for i, fu in enumerate(as_completed(futs), 1):
                s, y = futs[fu]
                try:
                    ok = fu.result()
                except Exception as e:                                   # noqa: BLE001
                    _log(f"{s} {y}: {type(e).__name__} {str(e)[:90]}")
                    ok = False
                got += 1 if ok else 0
                miss += 0 if ok else 1
                if i % 10 == 0 or i == len(jobs):
                    _log(f"{i}/{len(jobs)} year-files ({got} ok, {miss} empty) "
                         f"{time.time()-t0:.0f}s")
        return {"fetched": got, "missing": miss,
                "already_cached": len(symbols) * len(years) - len(jobs),
                "seconds": round(time.time() - t0, 1)}

    # ---------------- reading (no network) ----------------
    def _year_frame(self, symbol: str, year: int):
        key = (symbol.upper(), year)
        with _LOAD_LOCK:
            if key in self._mem:
                return self._mem[key]
        path = year_path(symbol, year, self.root)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "rb") as f:
                df = pickle.load(f)
        except (OSError, pickle.UnpicklingError):
            return None
        with _LOAD_LOCK:
            self._mem[key] = df
            self._mem_order.append(key)
            while len(self._mem_order) > self._max_mem:
                old = self._mem_order.pop(0)
                self._mem.pop(old, None)
        return df

    def chain_on(self, symbol: str, date):
        """The chain as of one date - a SLICE of the cached year, not a network call."""
        import pandas as pd

        d = date if isinstance(date, dt.date) else dt.date.fromisoformat(str(date)[:10])
        df = self._year_frame(symbol, d.year)
        if df is None:
            return pd.DataFrame()
        out = df[df["date"] == d]
        return out.reset_index(drop=True)

    def contract_history(self, symbol, expiration, strike, right, start, end):
        """One contract's daily life across the entry->expiry window. Spans year boundaries."""
        import pandas as pd

        s = start if isinstance(start, dt.date) else dt.date.fromisoformat(str(start)[:10])
        e = end if isinstance(end, dt.date) else dt.date.fromisoformat(str(end)[:10])
        exp = expiration if isinstance(expiration, dt.date) else \
            dt.date.fromisoformat(str(expiration)[:10])
        frames = []
        for yr in range(s.year, e.year + 1):
            df = self._year_frame(symbol, yr)
            if df is None:
                continue
            m = df[(df["expiration"] == exp)
                   & (df["strike"].astype(float).round(3) == round(float(strike), 3))
                   & (df["right"].astype(str).str[0] == str(right)[0].upper())
                   & (df["date"] >= s) & (df["date"] <= e)]
            if len(m):
                frames.append(m)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames).sort_values("date").reset_index(drop=True)

    def coverage_report(self, symbols, years) -> dict:
        """Exactly which symbol-years are present vs missing. The backtest must consult this
        before scoring: a symbol with gaps is under-sampled, not merely smaller."""
        complete, gaps = {}, {}
        for s_ in symbols:
            have = set(self.cached_years(s_))
            # A year the feed genuinely has no data for (pre-IPO, pre-rename) is COVERED.
            for y in years:
                if os.path.exists(year_path(s_, y, self.root) + ".empty"):
                    have.add(y)
            miss = [y for y in years if y not in have]
            complete[s_] = sorted(have & set(years))
            if miss:
                gaps[s_] = miss
        return {"complete": complete, "gaps": gaps,
                "fully_covered": [s_ for s_ in symbols if s_ not in gaps],
                "n_fully_covered": len([s_ for s_ in symbols if s_ not in gaps])}

    def cached_years(self, symbol: str) -> list:
        d = os.path.join(self.root, symbol.upper())
        if not os.path.isdir(d):
            return []
        out = []
        for fn in os.listdir(d):
            if fn.endswith(".pkl") and "-" in fn:
                try:
                    out.append(int(fn.rsplit("-", 1)[1][:-4]))
                except ValueError:
                    pass
        return sorted(out)


# ---------------------------------------------------------------------------------------
# Standalone entry point so the pull is NOT driven by an agent session:
#     python -m valuation.edge.theta_bulk
# It delegates to the miner, which owns the ranked universe and the liquidity screen.
if __name__ == "__main__":
    import runpy
    import sys

    _here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, _here)
    runpy.run_path(os.path.join(_here, "mine_options_cache.py"), run_name="__main__")
