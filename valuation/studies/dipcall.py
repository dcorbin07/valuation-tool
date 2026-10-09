"""DIP-CALL — the event construction, shared by the kill pass and the arm.

Register: `PREREG_dipcall.md`, committed ALONE at `c5e0b31` (markdown only, zero `.py`), a strict
git ancestor of every commit that computes an outcome. Trials booked at `a984ec9` (equity 274 ->
278) BEFORE this file existed.

**EVERY CONSTANT BELOW IS FROM THE REGISTER.** Changing one after a measurement voids the item
(`MA28`'s rule). `W-28`'s rule binds too: a bar may be RAISED and never LOWERED after it is
watched.

WHAT THIS MODULE MAY AND MAY NOT READ. It builds the event set from PRE-EVENT information only:
the return that DEFINES the event, and a volatility scale taken strictly before it (`shift(1)`).
It computes no forward return and no abnormal return — those live in `scripts/dipcall_arm.py`, so
the kill pass can be run and read in its own invocation without ever having seen an outcome
(`O10`'s process defect: a gating control and its outcomes must not run in one pass).

THREE EXECUTOR IMPLEMENTATION DECISIONS, MADE BEFORE ANY OUTCOME EXISTS AND RECORDED HERE BECAUSE
THE REGISTER FIXES THE RULE AND NOT THE MECHANICS:

1. **THE WHOLE HORIZON MUST LIE INSIDE THE BUILD YEARS.** An event on 2019-12-20 with a
   21-session horizon would read half-0 prices in 2020 — the `2020-2026 x half 0` cell, which
   `RESEARCH_CHARTER.md` §4's budget allocates to nothing. So an event qualifies for horizon `h`
   only if session `t + h` is still inside the build quadrant. The arms therefore have slightly
   different event sets per horizon, which is correct rather than untidy.

2. **THE DESIGN EFFECT IN THE KILL PASS IS MEASURED ON THE EVENT-DAY z, NOT ON AN OUTCOME.** A
   design effect is a within-cluster correlation OF SOMETHING, and the only quantity a
   pre-outcome pass may read is the event day itself. That is also the census's own stated worry
   — *"a market-wide drop creates thousands of simultaneous events that share one shock"* — so it
   is the right variable for the question the kill asks. The outcome-side design effect is
   reported by the arm pass, and the INFERENCE does not depend on either: `A2` makes the standard
   errors cluster-robust, which absorbs within-cluster correlation directly instead of applying a
   haircut. Stated so nobody later reads the kill's figure as the SE's provenance.

3. **THE PRE-OUTCOME HORIZON DISPERSION IS THE TRAILING DAILY SD SCALED BY sqrt(h), AND IT IS AN
   UPPER BOUND ON POWER.** `A10` requires the 63-session SD be measured rather than anchored at
   20pp, and a pre-outcome pass cannot measure a realised forward dispersion. Volatility is
   clustered, so post-event dispersion EXCEEDS the trailing estimate — which means this estimate
   UNDERSTATES the required n and so OVERSTATES power. That is the unsafe direction and is
   labelled, not hidden: the MDE that travels with the verdict comes from the arm's own REALISED
   SD (`MB8`: never borrow an se), and the kill pass's table is explicitly a bound.
"""
import hashlib
import os
from typing import Optional

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ REGISTER CONSTANTS (§2a, §7)
K_PRIMARY = 2.5
K_SENSITIVITY = (2.0, 3.0)
VOL_WIN = 60
MIN_VOL_OBS = 40
TIER_FLOOR = 10e9

BUILD_LO, BUILD_HI = "2009-01-01", "2019-12-31"
HALF_BOUNDARY = "2015-01-01"                 # §2d, boundary EMBARGOED

HORIZONS_PRIMARY = (5, 21)                   # §1, co-primary
HORIZONS_SENSITIVITY = (63, 126)             # §1, NO VERDICT

# ------------------------------------------------------------------- REGISTER BARS (§2f, §2g)
MIN_EVENTS_PER_CELL = 1500                   # kill 1 — may be RAISED, never lowered (W-28)
EARNINGS_COVERAGE_FLOOR = 0.70               # kill 2
VOL_RHO_BAR = 0.30                           # kill 4, the draft's registered form
VOL_QUINTILE_RATIO_BAR = 3.0                 # kill 4, A3's added discriminating form
ECONOMIC_FLOOR_PP = 0.67                     # A4 — 2 x B11's measured 33.4bps one-way
PERMUTATION_DRAWS = 500                      # A2 leg 3
BH_Q = 0.10                                  # §7
BH_K = 10                                    # §7 — fixed, never shrunk
CONTRACT_MIN_POSITIONS = 50                  # charter §5 Stage 1b

NEWS_SESSION_WINDOW = (0, 1)                 # A1 — i - j in {0, 1}, in SESSIONS not calendar days

NEWS = "news"
NO_NEWS = "no_news"
UNKNOWN = "unknown"

# A11 — ACTIONS rows that make an end-of-series a TERMINAL value rather than an administrative
# censor. `E-5` measured the cost of conflating them: 591 rows whose ticker stops trading inside
# the window silently deleted 16 crashes, 5 of them flagged.
TERMINAL_ACTIONS = ("delisted", "bankruptcyliquidation", "regulatorydelisting",
                    "voluntarydelisting", "acquisitionby", "mergerto")


# ------------------------------------------------------------------------------- paths (E-5)
def data_root(required: bool = True) -> Optional[str]:
    """The PRIMARY populated data root, never the worktree's empty one.

    `E-5`'s wrong-object family: a worktree carries `data/` EMPTY (here it carries no `data/` at
    all), so a path resolved against the repo root silently reads nothing and the caller gets a
    clean, plausible zero.

    **`required=True` RAISES, AND THAT DEFAULT IS LOAD-BEARING — A SCRIPT THAT CANNOT FIND ITS
    DATA MUST REFUSE RATHER THAN READ NOTHING.** `required=False` is for CALLERS THAT MUST ASK
    WITHOUT COMMITTING, and it exists because the raising form broke this item's own suite in CI:
    `data/` is gitignored, so on a runner there is no populated root at all and four
    data-dependent tests ABORTED instead of skipping loudly. A test must be able to ask "is the
    data here?" and get an answer rather than an exception; a script must not. Those are
    different needs and this is the one parameter that separates them.
    """
    d = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "data", "free_analysis")):
            return os.path.join(d, "data")
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    if required:
        raise SystemExit("REFUSING: no populated data root found")
    return None


def have_data() -> bool:
    """True when a populated data root exists. For LOUD SKIPS, never for a silent pass."""
    return data_root(required=False) is not None


def prices_dir() -> str:
    return os.path.join(data_root(), "full2009", "backtest", "prices")


def panel_path() -> str:
    return os.path.join(data_root(), "free_analysis", "UNIVERSE_BIAS_PANEL_full.pkl")


def events_csv() -> str:
    return os.path.join(data_root(), "bulk", "events.csv")


def actions_csv() -> str:
    return os.path.join(data_root(), "bulk", "actions.csv")


def out_path(name: str) -> str:
    return os.path.join(data_root(), "free_analysis", name)


# ------------------------------------------------------------------------- the X1 ticker split
def stable_key_half(ticker) -> int:
    """`X1`'s published split, `sha1(ticker) % 2`, no seed.

    One definition, and it is pinned two ways by `tests/test_dipcall.py`: against `X1`'s own
    `scripts/r4_x1_accounting_universe.stable_key_half`, and against the census's measured 3,545
    half-0 names. `MA5`'s lesson is that a second copy of one definition is how a bar freezes;
    here the duplication already existed (the census and `r4` each carry one), so this adds a
    THIRD and the test is what stops them diverging. Reported as a bug in the handoff.
    """
    return int(hashlib.sha1(str(ticker).encode("utf-8")).hexdigest(), 16) % 2


# ------------------------------------------------------------------------- A12 point-in-time tier
def tier_schedule(panel: Optional[pd.DataFrame] = None) -> dict:
    """{ticker: [(panel_date, market_cap), ...]} ascending, for ticker half 0 only.

    A12. The census's 459 names are *"ever `market_cap >= $10B` on a build-quadrant date"*, which
    counts a name's 2009 events because it reached $10B in 2019 — selection on a FUTURE property,
    and the draft's own §6 forbids it. Tier membership here is the most recent PRIOR quarterly
    observation, so a name joins the tier when it is measured to be in it and not before.
    """
    d = panel if panel is not None else pd.read_pickle(panel_path())
    d = d[["date", "ticker", "market_cap"]].copy()
    d["date"] = d["date"].astype(str)
    d["ticker"] = d["ticker"].astype(str)
    d = d[d["ticker"].map(stable_key_half) == 0]
    d["cap"] = pd.to_numeric(d["market_cap"], errors="coerce")
    d = d.dropna(subset=["cap"]).sort_values(["ticker", "date"])
    out = {}
    for t, g in d.groupby("ticker", sort=False):
        out[t] = list(zip(g["date"].tolist(), g["cap"].tolist()))
    return out


def _tier_flags(dates, schedule_for_name) -> np.ndarray:
    """Point-in-time `cap >= TIER_FLOOR` at each session date, from the most recent PRIOR panel
    observation. A session before the name's first panel date is NOT in the tier — unknown is
    never read as eligible."""
    if not schedule_for_name:
        return np.zeros(len(dates), dtype=bool)
    pd_dates = np.array([x[0] for x in schedule_for_name])
    caps = np.array([x[1] for x in schedule_for_name], dtype=float)
    # `side="right"` so a panel observation ON the session date counts as known at that date:
    # the panel date IS the observation date, and B26's precedent makes a same-day filing usable.
    idx = np.searchsorted(pd_dates, np.asarray(dates, dtype=object), side="right") - 1
    ok = idx >= 0
    flags = np.zeros(len(dates), dtype=bool)
    flags[ok] = caps[idx[ok]] >= TIER_FLOOR
    return flags


# ------------------------------------------------------------------------------ price series
def read_prices(ticker: str) -> Optional[pd.DataFrame]:
    """Ascending `date`/`close`, split- AND dividend-adjusted (§2a; the panel's `close` is
    `closeadj`). RAW close is required for any STRIKE and is step 2's problem, never step 1's."""
    p = os.path.join(prices_dir(), "%s.csv" % ticker)
    if not os.path.isfile(p):
        return None
    try:
        s = pd.read_csv(p, usecols=["date", "close"])
    except (ValueError, OSError):
        return None
    s["date"] = s["date"].astype(str)
    s["close"] = pd.to_numeric(s["close"], errors="coerce")
    s = s.dropna(subset=["close"])
    s = s[s["close"] > 0].sort_values("date").reset_index(drop=True)
    return s if len(s) else None


def name_frame(ticker: str, schedule_for_name, k: float = K_PRIMARY) -> Optional[pd.DataFrame]:
    """One name's PRE-OUTCOME event frame. No forward return is computed here.

    Columns: date, session_idx (the name's own trading-session index, which is what A1's news
    window is measured in), close, ret, vol (trailing, STRICTLY prior), z, event, tier,
    n_sessions_total.
    """
    s = read_prices(ticker)
    if s is None or len(s) < VOL_WIN + 10:
        return None
    # The session index is over the name's FULL series, so a window that reaches outside the
    # build quadrant is detectable rather than silently truncated.
    s["session_idx"] = np.arange(len(s), dtype=np.int64)
    s["ret"] = s["close"].pct_change()
    # STRICTLY PRIOR: shift(1) so the event day is not inside its own scale.
    s["vol"] = s["ret"].rolling(VOL_WIN, min_periods=MIN_VOL_OBS).std().shift(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        s["z"] = s["ret"] / s["vol"]
    s["scoreable"] = s["z"].notna() & s["vol"].gt(0)
    s["event"] = s["scoreable"] & s["z"].le(-float(k))
    s["tier"] = _tier_flags(s["date"].tolist(), schedule_for_name)
    s["ticker"] = ticker
    return s


# --------------------------------------------------------------------------- A1 the news split
def news_class(spine, ticker: str, session_idx_of_event, announce_session_idx) -> str:
    """NEWS iff an announcement falls at session `j` with `i - j` in {0, 1} (A1).

    Earnings are released after the close or before the open, so the reaction is the announcement
    session or the one immediately after it. Measured in SESSIONS, never calendar days: a
    Friday-after-the-close announcement reacts on Monday, three calendar days later and ONE
    session later.
    """
    if announce_session_idx is None:
        return UNKNOWN
    lo, hi = NEWS_SESSION_WINDOW
    for j in announce_session_idx:
        d = int(session_idx_of_event) - int(j)
        if lo <= d <= hi:
            return NEWS
    return NO_NEWS


def announce_sessions(spine, ticker: str, date_to_idx: dict) -> Optional[list]:
    """The name's code-22 announcement dates mapped into its own session index.

    `None` for a name with NO coverage anywhere — A1b's third state, which is counted and
    excluded by name and is NEVER read as "no news". `O6`/`O7` measured 29 of 186 names as
    foreign private issuers with ZERO earnings dates, so a filter reading "no date" as "no
    announcement" fails OPEN on a non-random tenth of the book.

    An announcement on a NON-trading date (a holiday, or a date outside this name's price file)
    is mapped forward to the next session the name actually trades, because that is the session
    the reaction can appear on. An announcement after the name's last price is dropped.
    """
    ds = spine.dates_or_unknown(ticker)
    if ds is None:
        return None
    keys = sorted(date_to_idx)
    if not keys:
        return []
    arr = np.array(keys, dtype=object)
    out = []
    for d in ds:
        d = str(d)[:10]
        pos = int(np.searchsorted(arr, d, side="left"))
        if pos < len(arr):
            out.append(int(date_to_idx[arr[pos]]))
    return sorted(set(out))


# ------------------------------------------------------------------------ halves and the embargo
def half_of(date: str) -> str:
    return "early" if str(date) < HALF_BOUNDARY else "late"


def horizon_ok(frame_len: int, session_idx: int, h: int, last_build_idx: int) -> bool:
    """Implementation decision 1: the WHOLE horizon must lie inside the build years."""
    end = int(session_idx) + int(h)
    return end <= int(last_build_idx) and end < int(frame_len)


def crosses_boundary(dates, session_idx: int, h: int) -> bool:
    """§2d. An event whose horizon window crosses 2015-01-01 is dropped from BOTH halves and
    counted — the boundary is embargoed rather than assigned to whichever half the event day
    happens to fall in."""
    i = int(session_idx)
    j = min(i + int(h), len(dates) - 1)
    return str(dates[i]) < HALF_BOUNDARY <= str(dates[j])
