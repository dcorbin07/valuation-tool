"""optionable_universe.py — WAS a name tradeable in options ON a given rebalance date?  [P1-S0]

Built for P1 Stage 0, the gating control of `VALQUO_OPTIONS_FRONTIER.md`. It answers one
question and deliberately nothing else: for each (rebalance date, ticker) in the equity panel,
would the option miner's own liquidity screen have admitted that name **on that day**?

--------------------------------------------------------------------------------------------
WHY IT EXISTS — THE FRONTIER'S OWN §2d CAVEAT, WHICH IT LABELLED LOAD-BEARING.

The frontier's scoping run partitioned the panel by whether a name has a chain in the cache
**today**. It said so, and called the resulting tilt "exactly the flattering direction":

    "A name with a liquid 2024 chain was, in 2009, disproportionately a future winner. That is
     a survivorship tilt in exactly the flattering direction, and it is the same class of
     defect as the non-PIT sector map."

That is the `S25` sector-map defect in a new costume — today's classification applied to a
1998 row — and this project has already recorded that it is a reason to be MORE sceptical of a
positive result, not less. So the gate cannot be run on a today-snapshot partition.

--------------------------------------------------------------------------------------------
WHAT THIS FIXES, AND THE LARGER HALF IT CANNOT — O20's OWN CORRECTION, INHERITED VERBATIM.

`options_universe.py` already records that O20's premise is two claims and only one holds:

  * THE POOL ORDER IS HINDSIGHT. Names were ranked for mining by TODAY's market cap, so a name
    that was liquid in 2016 and has since shrunk or died was never reached. **This module
    cannot touch that.** No evaluation-time filter recovers data that was never mined.
  * THE LIQUIDITY SCREEN IS NOT TODAY'S. `name_is_viable` measured the name's FIRST CACHED
    YEAR. Re-asking it per-day is what this module does.

So the partition here is an **upper bound on the repair**, and the residual selection is
stated rather than implied. A pass on this universe means "the composite sorts the names we
mined, dated honestly", never "the composite sorts optionable names".

--------------------------------------------------------------------------------------------
THE THRESHOLDS ARE NOT RE-DECLARED HERE. `pit_liquidity` and `pit_liquid_ok` are IMPORTED from
`valuation.edge.options_universe`, which imports them in turn from the miner. Re-typing a
constant is the B7 defect class and this file refuses to participate in it. If the miner's bar
moves, this partition moves with it.

TRI-STATE IS PRESERVED. `pit_liquid_ok` returns None — not False — when the day's chain cannot
answer, because an unmeasurable day is not a failed day. Collapsing the two would silently
delete names for a data reason while reporting it as a liquidity finding.

--------------------------------------------------------------------------------------------
IT NEVER READS A FORWARD RETURN. The partition is a function of (date, ticker, chain) alone.
That is what lets it be built BEFORE the register without leaking: a universe definition that
cannot see an outcome cannot be tuned to one. Pinned by test.
"""
from __future__ import annotations

import glob
import os
from typing import Optional

import numpy as np
import pandas as pd

# The O20 rule itself — imported, never re-typed. A study may import the engine.
from ..edge.options_universe import pit_liquidity, pit_liquid_ok

# A rebalance date is a trading day and the cache is daily EOD, so the chain for that very day
# is the normal case. The window tolerates a holiday or a one-off miner gap. It is CALENDAR
# days and it is small on purpose: a wide window would quietly re-introduce staleness, and the
# whole point of this module is that the answer is dated.
STALE_MAX_DAYS = 5

# Below this many quoted rows a "chain" is a fragment and `pit_liquidity` is being asked to
# measure a name from almost nothing. Reported, not silently dropped.
MIN_CHAIN_ROWS = 20


def is_populated_cache(root: Optional[str]) -> bool:
    """Does `root` hold an options cache with actual ticker directories in it?

    EXISTENCE IS NOT POPULATION, and the difference is the whole point. A git worktree carries
    its own empty `data/`, so `data/options` can exist and be empty — which every downstream
    consumer reads as "no coverage" rather than as "wrong root". That silent-empty failure is
    `options_backtest.BARS_CACHE`'s defect (session 25), where a relative path resolved to
    nothing and returned an empty bar set instead of an error.
    """
    if not root:
        return False
    opt = os.path.join(root, "options")
    if not os.path.isdir(opt):
        return False
    try:
        entries = os.listdir(opt)[:50]
    except OSError:
        return False
    return any(os.path.isdir(os.path.join(opt, d)) for d in entries)


def _data_root(explicit: Optional[str] = None) -> str:
    """The options cache lives with the licensed export, which a git worktree does not carry."""
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.environ.get("VALQUO_DATA_ROOT"),
        os.path.abspath(os.path.join(here, "..", "..", "data")),
        r"C:\Users\donni\Downloads\valuation-tool\data",
    ]
    for c in cands:
        if is_populated_cache(c):
            return c
    raise FileNotFoundError(
        "optionable_universe: no populated options cache found. Tried: %r. A git worktree "
        "carries an empty data/ — pass data_root or set VALQUO_DATA_ROOT." % (cands,))


def chain_year_path(root: str, ticker: str, year: int) -> str:
    return os.path.join(root, "options", ticker, "%s-%d.pkl" % (ticker, year))


def cached_years(root: str, ticker: str) -> list:
    out = []
    for f in glob.glob(os.path.join(root, "options", ticker, "*.pkl")):
        b = os.path.basename(f)[:-4]
        if "-" in b:
            try:
                out.append(int(b.rsplit("-", 1)[1]))
            except ValueError:
                pass
    return sorted(out)


def _as_of_slice(chain: pd.DataFrame, when: pd.Timestamp, stale_max: int = STALE_MAX_DAYS):
    """The most recent chain-day at or before `when`, within the staleness window.

    ON-OR-BEFORE, not strictly-before, and the distinction is deliberate. "Does this name have
    a tradeable option chain today" is CONTEMPORANEOUS information — you observe it at the
    close of the rebalance date, alongside every price the panel already uses. It is not a
    forecast of anything. Contrast `join_pit`, which is strictly-before because it joins a
    PREDICTIVE feature; that rule is about not seeing the future, and a chain's existence today
    is not the future. `staleness_days` is returned so the choice is auditable rather than
    buried, and a caller wanting the stricter rule can filter on it.
    """
    if chain is None or len(chain) == 0 or "date" not in chain.columns:
        return None, None
    d = pd.to_datetime(chain["date"], errors="coerce")
    lo = when - pd.Timedelta(days=int(stale_max))
    m = (d <= when) & (d >= lo)
    if not bool(m.any()):
        return None, None
    day = d[m].max()
    return chain[d == day], int((when - day).days)


def date_ticker_partition(dates, tickers, data_root: Optional[str] = None,
                          stale_max: int = STALE_MAX_DAYS, progress=None) -> pd.DataFrame:
    """One row per (date, ticker) for which the cache holds ANY chain in the window.

    Columns: date, ticker, staleness_days, n_chain_rows, pit_liquid (True/False/None),
    median_spread_pct, atm_oi, atm_oi_notional.

    A (date, ticker) absent from the output has no point-in-time chain at all — that is the
    `has_chain = False` case, represented by absence rather than by a row of NaNs so that a
    caller cannot accidentally treat "no chain" as "chain that failed the screen".
    """
    root = _data_root(data_root)
    dates = [pd.Timestamp(x) for x in sorted(pd.to_datetime(pd.Index(dates)).unique())]
    by_year = {}
    for d in dates:
        by_year.setdefault(d.year, []).append(d)

    rows = []
    tickers = sorted(set(tickers))
    for i, t in enumerate(tickers):
        years = set(cached_years(root, t))
        if not years:
            continue
        for yr, ds in by_year.items():
            # A January rebalance can legitimately be served by the previous year's file if the
            # new year's has not started; try the year itself first, then fall back.
            for src in (yr, yr - 1):
                if src not in years:
                    continue
                p = chain_year_path(root, t, src)
                try:
                    ch = pd.read_pickle(p)
                except Exception:                                          # noqa: BLE001
                    continue
                got = False
                for d in ds:
                    sl, stale = _as_of_slice(ch, d, stale_max)
                    if sl is None or len(sl) == 0:
                        continue
                    got = True
                    st = pit_liquidity(sl, d)
                    rows.append({
                        "date": d, "ticker": t, "staleness_days": stale,
                        "n_chain_rows": int(len(sl)),
                        "pit_liquid": pit_liquid_ok(st),
                        "median_spread_pct": st.get("median_spread_pct"),
                        "atm_oi": st.get("atm_oi"),
                        "atm_oi_notional": st.get("atm_oi_notional"),
                    })
                del ch
                if got:
                    break
        if progress and (i + 1) % 50 == 0:
            progress(i + 1, len(tickers))
    if not rows:
        return pd.DataFrame(columns=["date", "ticker", "staleness_days", "n_chain_rows",
                                     "pit_liquid", "median_spread_pct", "atm_oi",
                                     "atm_oi_notional"])
    out = pd.DataFrame(rows)
    # Duplicate (date,ticker) would double-count a name in a decile. Cannot happen by
    # construction (one row per pair) but asserted, because a silent duplicate would inflate
    # the optionable universe and read as coverage.
    dup = int(out.duplicated(["date", "ticker"]).sum())
    if dup:
        raise AssertionError("optionable_universe: %d duplicate (date,ticker) rows" % dup)
    return out.sort_values(["date", "ticker"]).reset_index(drop=True)


def coverage_report(part: pd.DataFrame, panel_dates, panel_counts=None) -> dict:
    """Coverage FIRST, per the COVERAGE RULE — before any return is looked at.

    `panel_counts` maps date -> names in the panel that date, so the share is of the real
    cross-section rather than of whatever the partition happens to contain.
    """
    dates = [pd.Timestamp(x) for x in sorted(pd.to_datetime(pd.Index(panel_dates)).unique())]
    per = []
    for d in dates:
        s = part[part["date"] == d] if len(part) else part
        n_chain = int(len(s))
        n_liq = int((s["pit_liquid"] == True).sum()) if n_chain else 0        # noqa: E712
        n_unk = int(s["pit_liquid"].isna().sum()) if n_chain else 0
        tot = int(panel_counts.get(d, 0)) if panel_counts else None
        per.append({"date": str(d)[:10], "panel_names": tot, "has_chain": n_chain,
                    "pit_liquid": n_liq, "unmeasurable": n_unk,
                    "share_liquid": (round(n_liq / tot, 4) if tot else None)})
    covered = [r for r in per if r["has_chain"] > 0]
    liq = [r for r in per if r["pit_liquid"] > 0]
    return {
        "n_panel_dates": len(dates),
        "n_dates_any_chain": len(covered),
        "n_dates_pit_liquid": len(liq),
        "n_dates_zero_chain": len(dates) - len(covered),
        "first_covered": covered[0]["date"] if covered else None,
        "last_covered": covered[-1]["date"] if covered else None,
        "median_pit_liquid_per_covered_date": (
            float(np.median([r["pit_liquid"] for r in liq])) if liq else 0.0),
        "median_has_chain_per_covered_date": (
            float(np.median([r["has_chain"] for r in covered])) if covered else 0.0),
        "staleness_days_max": (int(part["staleness_days"].max()) if len(part) else None),
        "staleness_days_nonzero_share": (
            round(float((part["staleness_days"] > 0).mean()), 4) if len(part) else None),
        "n_rows": int(len(part)),
        "n_unmeasurable": int(part["pit_liquid"].isna().sum()) if len(part) else 0,
        "per_date": per,
    }


def restrict(panel: pd.DataFrame, part: pd.DataFrame, mode: str = "pit_liquid") -> pd.DataFrame:
    """The panel restricted to the optionable universe.

    `mode`:
      * "pit_liquid"  — PRIMARY. The miner's own screen passes on the day. This is the universe
                        P1 would actually have to trade, which is why it is primary.
      * "has_chain"   — SENSITIVITY. Any point-in-time chain at all, screen ignored.

    An `unmeasurable` day (pit_liquid is None) is EXCLUDED from "pit_liquid" and INCLUDED in
    "has_chain". Neither choice is neutral, so both universes are reported and the primary is
    named in the register before either is scored.
    """
    if mode not in ("pit_liquid", "has_chain"):
        raise ValueError("restrict: mode must be pit_liquid or has_chain, got %r" % (mode,))
    if not len(part):
        return panel.iloc[0:0].copy()
    sel = part if mode == "has_chain" else part[part["pit_liquid"] == True]   # noqa: E712
    keys = set(zip(pd.to_datetime(sel["date"]), sel["ticker"]))
    d = pd.to_datetime(panel["date"])
    mask = [(a, b) in keys for a, b in zip(d, panel["ticker"])]
    return panel[np.asarray(mask, dtype=bool)].copy()
