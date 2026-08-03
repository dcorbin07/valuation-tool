"""
Unattended ThetaData cache expansion — 55 megacaps -> the full liquid optionable universe.

Pure data-pull. No research, no gates, no verdicts. Resumable: every symbol-year is written
atomically and skipped if present, so a kill costs at most the year in flight.

--------------------------------------------------------------------------------------------
UNIVERSE RANKING, AND WHY IT IS NOT DONE ON OPTIONS LIQUIDITY DIRECTLY.

Ranking by actual options liquidity would need a chain pull per symbol across 15,669 optionable
names - hours of work before the first useful byte is cached. ThetaData's all-symbol flat file
would answer it in one call but requires a PROFESSIONAL subscription (this account is Standard;
verified, it returns PERMISSION_DENIED).

So names are ranked by MARKET CAP from the local Sharadar daily table - instant, offline, and a
strong proxy: the options liquidity ranking and the market-cap ranking agree closely at the top,
which is the part that matters when pulling top-down. The proxy is then CORRECTED BY REALITY:
after a name's first year is cached, its actual option liquidity is measured, and names whose
chains are too thin to trade are abandoned before their remaining years are pulled. That way a
bad proxy costs one year, not ten.

--------------------------------------------------------------------------------------------
THE CACHE FILTER IS DELIBERATELY LOOSER THAN THE BACKTEST'S ENTRY FILTER. This is the one thing
in this file that could silently corrupt every future result, so it is spelled out.

`options_fill` screens ENTRIES at OI>=100, volume>=10, spread<=25%. It deliberately does NOT
re-apply that at exit, because you must be able to exit a contract you already own even after it
goes illiquid - otherwise the backtest gets to abandon its losers, which is survivorship bias
wearing a different hat.

If this miner filtered the CACHE at the entry thresholds, those exit quotes would be deleted
from disk and the backtest could never see them. Every future run would then quietly inherit the
bias the entry/exit asymmetry exists to prevent.

So the cache filter removes only rows that carry NO information at all:
  * no two-sided quote AND no open interest AND no volume - a dead contract nothing can be
    learned from; and
  * quotes wider than CACHE_MAX_SPREAD_PCT, which are placeholders rather than markets.
Everything a trade could ever need to exit is retained.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPO = r"C:\Users\donni\Downloads\valuation-tool"
OPTROOT = os.path.join(REPO, "data", "options")

# Load .env from the REPO explicitly. The provider's fallback searches the CWD and the package
# parent, neither of which is the main checkout when this runs from a worktree - so the key was
# invisible and the miner exited immediately with "no THETADATA_API_KEY".
try:
    for _line in open(os.path.join(REPO, ".env"), encoding="utf-8", errors="replace"):
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
except OSError:
    pass


MANIFEST = os.path.join(OPTROOT, "cache_manifest.json")
PROGRESS = os.path.join(OPTROOT, "MINING_PROGRESS.txt")

YEARS = list(range(2016, 2026))          # ten complete years; 2026 is in progress and excluded
TARGET_NAMES = 1000

# Cache-level filter. LOOSER than options_fill's entry screen on purpose - see the header.
CACHE_MAX_SPREAD_PCT = 3.0               # 300%: only placeholder quotes, not real markets

# Name-level viability, judged on the FIRST cached year rather than assumed from market cap.
# Thresholds are the PERMISSIVE end of the specified ranges (OI 500-1000, volume 100-500,
# spread 10-15%) on purpose: the point of extending past the megacaps is to reach the
# high-IV mid/small movers retail trades heavily, and the tight end of each range would start
# excluding exactly those. The cut is aimed at untradeable micro-caps, not at volatility.
MIN_ATM_OI = 500                 # contract-count floor, used only for the spread population
# Open interest is measured in DOLLARS, not contracts. A contract controls 100 x share price, so
# an absolute contract floor systematically penalises high-priced stocks: DE was rejected at 492
# contracts - eight short of 500 - while trading 5,964 contracts/day at a 9.7% spread, and LRCX
# at 240 contracts while trading 11,686/day. Neither is remotely illiquid; they are simply
# expensive, so the same dollar exposure needs fewer contracts. $2.5M is 500 contracts on a $50
# stock, i.e. the brief's intent expressed at a price-neutral scale.
MIN_ATM_OI_NOTIONAL = 2_500_000
MIN_DAILY_OPTION_VOLUME = 100    # median total contracts traded across the chain per day
MAX_MEDIAN_SPREAD_PCT = 0.15     # THE key cut - spread is what kills a long-premium edge
SPREAD_MIN_PREMIUM = 0.50        # measure spread only on contracts with a REAL premium
MIN_DAYS_WITH_CHAIN = 100        # of ~252; below this the name is not continuously live

# Unattended runs must not fill the disk. ~199MB/name at megacap scale (mid/small caps are far
# smaller), so 1,000 names projects to well under the free space - but a guard costs nothing and
# a full C: drive during an overnight job is expensive.
MIN_FREE_GB = 40
RETRY_ROUNDS = 2         # bounded re-attempts for names that came in partial


def log(msg):
    line = f"[mine] {msg}"
    print(line, flush=True)
    try:
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def ranked_universe(limit: int = TARGET_NAMES) -> list:
    """Optionable names, biggest first. Market cap is the proxy; reality corrects it later."""
    import pandas as pd

    from valuation.edge.theta_bulk import ThetaBulk

    d = pd.read_csv(os.path.join(REPO, "data", "bulk", "daily.csv"),
                    usecols=["ticker", "date", "marketcap"])
    d = d[d["date"] >= "2024-01-01"]
    last = d.sort_values("date").groupby("ticker").tail(1)
    last = last[last["marketcap"] > 0].sort_values("marketcap", ascending=False)

    tb = ThetaBulk(root=OPTROOT)
    optionable = set()
    try:
        syms = tb._cli().option_list_symbols()
        col = "symbol" if "symbol" in syms.columns else syms.columns[0]
        optionable = {str(x).upper() for x in syms[col]}
        log(f"optionable symbols from ThetaData: {len(optionable):,}")
    except Exception as e:                                           # noqa: BLE001
        log(f"could not list optionable symbols ({type(e).__name__}); ranking on market cap only")

    out = []
    for t in last["ticker"]:
        t = str(t).upper()
        if optionable and t not in optionable:
            continue
        out.append(t)
        if len(out) >= limit:
            break
    return out


def slim_filter(df):
    """Drop only information-free rows. Returns (kept_frame, n_dropped)."""
    import pandas as pd

    if df is None or len(df) == 0:
        return df, 0
    n0 = len(df)
    bid = pd.to_numeric(df["bid"], errors="coerce").fillna(0)
    ask = pd.to_numeric(df["ask"], errors="coerce").fillna(0)
    oi = pd.to_numeric(df["open_interest"], errors="coerce").fillna(-1)
    vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    dead = (bid <= 0) & (ask <= 0) & (oi <= 0) & (vol <= 0)
    mid = (bid + ask) / 2.0
    absurd = (mid > 0) & (((ask - bid) / mid) > CACHE_MAX_SPREAD_PCT)
    keep = ~(dead | absurd)
    return df[keep].reset_index(drop=True), int(n0 - int(keep.sum()))


def name_is_viable(tb, sym: str, year: int) -> tuple:
    """Measure a name's REAL option tradeability from one cached year. (viable, stats).

    Near-the-money is approximated by the HIGHEST-OI contracts rather than by distance from spot:
    open interest concentrates around the money, and using it avoids needing a per-name spot
    series just to screen. Spread is measured only on contracts that actually trade, because the
    spread on a contract nobody touches is not the spread you would pay.
    """
    import pandas as pd

    df = tb._year_frame(sym, year)
    if df is None or len(df) == 0:
        return False, {"reason": "no data"}
    days = int(df["date"].nunique())
    bid = pd.to_numeric(df["bid"], errors="coerce").fillna(0)
    ask = pd.to_numeric(df["ask"], errors="coerce").fillna(0)
    oi = pd.to_numeric(df["open_interest"], errors="coerce").fillna(-1)
    vol = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    mid = (bid + ask) / 2.0

    quoted = (bid > 0) & (ask > bid) & (mid > 0)
    # daily option volume across the whole chain
    dv = df.assign(_v=vol).groupby("date")["_v"].sum()
    daily_volume = float(dv.median()) if len(dv) else 0.0
    # near-ATM open interest: the top decile by OI, which is where the money sits
    live = quoted & (oi > 0)
    live_oi = oi[live]
    atm_oi = float(live_oi.quantile(0.90)) if len(live_oi) else 0.0
    # Price proxy: the strike of those most-held contracts, since OI concentrates near the money.
    # This avoids needing a per-name spot series purely to screen.
    strike = pd.to_numeric(df["strike"], errors="coerce")
    top = live & (oi >= atm_oi) if atm_oi > 0 else live
    atm_strike = float(strike[top].median()) if int(top.sum()) else 0.0
    atm_notional = atm_oi * atm_strike * 100.0

    # Spread on contracts we would ACTUALLY trade. Measuring it across every quoted contract
    # includes far-OTM lottery tickets where a one-cent tick on a five-cent mid reads as 20%,
    # which is not the spread a 35-delta 45-75 DTE call pays. That mis-measurement rejected
    # RKLB at 18.2% - a name with 8,198 contracts/day and 1,821 ATM OI, and one the brief names
    # explicitly as the kind of high-IV mover worth having. On real premium it is 8.7%.
    tradeable_mask = quoted & (vol > 0) & (oi >= MIN_ATM_OI) & (mid >= SPREAD_MIN_PREMIUM)
    spr = ((ask - bid) / mid)[tradeable_mask]
    median_spread = float(spr.median()) if len(spr) else 1.0

    stats = {"days_with_chain": days,
             "daily_option_volume": round(daily_volume, 0),
             "atm_oi": round(atm_oi, 0),
             "atm_strike": round(atm_strike, 2),
             "atm_oi_notional_m": round(atm_notional / 1e6, 1),
             "median_spread_pct": round(median_spread, 4),
             "rows": int(len(df))}
    fails = []
    if days < MIN_DAYS_WITH_CHAIN:
        fails.append(f"{days}d chain")
    if daily_volume < MIN_DAILY_OPTION_VOLUME:
        fails.append(f"vol {daily_volume:.0f}/day")
    # Open interest passes on EITHER measure. Liquidity has two faces: an expensive name holds
    # few contracts but large notional (DE: 492 contracts, $19.2M), a cheap one holds many
    # contracts but small notional (RKLB: 1,821 contracts, $1.3M). Requiring contracts alone
    # rejected DE; requiring notional alone rejected RKLB - and the brief names RKLB explicitly
    # as a name that should pass. Only a name failing BOTH is genuinely too small to trade
    # (SPCX: 8 contracts, $0.0M). Spread remains the primary cut, as the brief specifies.
    if atm_oi < MIN_ATM_OI and atm_notional < MIN_ATM_OI_NOTIONAL:
        fails.append(f"atm OI {atm_oi:.0f} contracts / ${atm_notional/1e6:.1f}M")
    if median_spread > MAX_MEDIAN_SPREAD_PCT:
        fails.append(f"spread {median_spread:.0%}")
    stats["reason"] = "ok" if not fails else "thin: " + ", ".join(fails)
    return (not fails), stats


def main():
    import shutil

    from valuation.edge.theta_bulk import ThetaBulk, year_path

    os.makedirs(OPTROOT, exist_ok=True)
    tb = ThetaBulk(root=OPTROOT)
    if not tb.status()["available"]:
        log(f"ThetaData unavailable: {tb.status()['reason']}")
        return

    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            manifest = json.load(open(MANIFEST, encoding="utf-8"))
        except (OSError, ValueError):
            manifest = {}

    uni = ranked_universe(TARGET_NAMES)
    log(f"target universe: {len(uni)} names (market-cap ranked, optionable); free disk {shutil.disk_usage(chr(67)+chr(58)+chr(47)).free/1e9:.0f}GB")

    t0 = time.time()
    for i, sym in enumerate(uni, 1):
        import shutil
        free_gb = shutil.disk_usage("C:/").free / 1e9
        if free_gb < MIN_FREE_GB:
            log(f"STOPPING: only {free_gb:.0f}GB free (floor {MIN_FREE_GB}GB). "
                f"Cache is intact and the run resumes where it left off.")
            break

        rec = manifest.get(sym, {})
        if rec.get("status") in ("complete", "skipped_thin"):
            continue

        # Probe year: cache one year, then let REAL liquidity decide whether to continue.
        probe = 2024 if 2024 in YEARS else YEARS[-1]
        tb.ensure_year(sym, probe)
        viable, stats = name_is_viable(tb, sym, probe)
        if not viable:
            manifest[sym] = {"status": "skipped_thin", **stats}
            log(f"[{i}/{len(uni)}] {sym}: SKIP - {stats['reason']}")
            _save(manifest)
            continue

        # 4-concurrent across this name's years. Sequential years would be ~18 min/name
        # (~133 hours for the universe); concurrency brings it to ~5 min/name.
        tb.prefetch([sym], YEARS)
        got, gaps = [], []
        for y in YEARS:
            pth = year_path(sym, y, OPTROOT)
            (got if (os.path.exists(pth) or os.path.exists(pth + ".empty")) else gaps).append(y)

        # Shrink what was just written: drop information-free rows only.
        dropped_total = 0
        for y in got:
            pth = year_path(sym, y, OPTROOT)
            if not os.path.exists(pth):
                continue
            try:
                import pickle
                with open(pth, "rb") as f:
                    df = pickle.load(f)
                kept, dropped = slim_filter(df)
                if dropped:
                    tmp = pth + ".tmp"
                    with open(tmp, "wb") as f:
                        pickle.dump(kept, f, protocol=5)
                    os.replace(tmp, pth)
                    dropped_total += dropped
            except Exception:                                        # noqa: BLE001
                pass

        manifest[sym] = {"status": "complete" if not gaps else "partial",
                         "years": got, "gaps": gaps, "rows_dropped": dropped_total, **stats}
        done = sum(1 for v in manifest.values() if v.get("status") in ("complete", "partial"))
        log(f"[{i}/{len(uni)}] {sym}: {len(got)} years"
            + (f", GAPS {gaps}" if gaps else "")
            + f" | {done} of {len(uni)} names cached | {(time.time()-t0)/60:.0f}m")
        _save(manifest)

    _save(manifest)

    # RETRY PASS over names that came in partial. Gaps here are transient gRPC failures far more
    # often than genuinely absent data, and the main loop walks the universe exactly once, so
    # without this a name keeps a gap for good. Bounded rounds so a permanently-dead year cannot
    # spin forever.
    for rnd in range(1, RETRY_ROUNDS + 1):
        partial = [k for k, v in manifest.items() if v.get("status") == "partial"]
        if not partial:
            break
        log(f"retry round {rnd}/{RETRY_ROUNDS}: {len(partial)} partial names "
            f"({', '.join(partial[:8])}{' ...' if len(partial) > 8 else ''})")
        for sym in partial:
            gaps = manifest[sym].get("gaps") or []
            if not gaps:
                manifest[sym]["status"] = "complete"
                continue
            for y in list(gaps):
                pth = year_path(sym, y, OPTROOT)
                # Clear the failure marker so the year is actually re-attempted.
                try:
                    if os.path.exists(pth + ".missing"):
                        os.remove(pth + ".missing")
                except OSError:
                    pass
                tb.ensure_year(sym, y)
            still = [y for y in gaps
                     if not (os.path.exists(year_path(sym, y, OPTROOT))
                             or os.path.exists(year_path(sym, y, OPTROOT) + ".empty"))]
            manifest[sym]["gaps"] = still
            manifest[sym]["status"] = "complete" if not still else "partial"
            log(f"  {sym}: {len(gaps) - len(still)} of {len(gaps)} gap years recovered"
                + (f"; still missing {still}" if still else ""))
            _save(manifest)

    _save(manifest)
    done = sum(1 for v in manifest.values() if v.get("status") in ("complete", "partial"))
    partial = [k for k, v in manifest.items() if v.get("status") == "partial"]
    thin = [k for k, v in manifest.items() if v.get("status") == "skipped_thin"]
    log(f"FINISHED: {done} of {len(uni)} names cached; {len(partial)} partial"
        + (f" ({', '.join(partial)})" if partial else "")
        + f"; {len(thin)} skipped as too illiquid")


def _save(manifest):
    try:
        tmp = MANIFEST + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=1, sort_keys=True)
        os.replace(tmp, MANIFEST)
    except OSError:
        pass


if __name__ == "__main__":
    main()
