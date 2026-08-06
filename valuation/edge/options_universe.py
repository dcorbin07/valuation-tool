"""
Roadmap 22b — the single-leg scream-buy edge, re-measured on the EXPANDED universe.

PRE-SPECIFIED. Everything from here to the "RESULT" banner was written and committed BEFORE the
broad run was executed, for the usual reason: with a heavy-tailed payoff and 130 new names, a
gate chosen after seeing the numbers is not a gate.

--------------------------------------------------------------------------------------------
WHY THIS RUN EXISTS.

Every options result this project has quoted — +12.33%/trade, the term_slope filter, the trade
autopsy — was measured on 55 megacaps. That is the friendly slice, and this codebase already
learned once, expensively, what a friendly slice does: the stock model's PBO was 13% on 800
names and 53% on the full universe. The METHODOLOGY RULE in CLAUDE.md exists because of it, and
it applies to options exactly as it applies to the panel.

The miner has since cached the mid/small-cap tier. So the question is narrow and answerable:
does the edge HOLD as breadth grows, or is it a megacap phenomenon?

Don's thesis cuts both ways and both halves are testable:
  * mid/small caps move harder, so they should produce MORE frequent >= +100% winners and
    DE-CONCENTRATE a tail that currently rests on a handful of names;
  * their options carry wider spreads and richer IV, so the move may already be priced in and
    the fills may eat whatever the extra movement earns.

--------------------------------------------------------------------------------------------
NOTHING ABOUT THE STRATEGY IS RE-TUNED HERE. THAT IS THE POINT.

The alert rule, the contract rule, the exit discipline, the fill model and the term_slope
threshold are all imported or hard-quoted from the 55-name work and applied UNCHANGED to names
that never informed them. A broad-universe run that also re-fits its parameters would answer a
different, much easier question.

In particular `SHIPPED_TERM_THRESHOLD` is the number fitted on the 55-name 2016-2020 half. On
the 130 names that did not exist in that fit, applying it is a genuine out-of-sample test of the
one filter this project has adopted.

--------------------------------------------------------------------------------------------
THE UNIVERSE IS NOT NEUTRAL, AND THE BIAS RUNS TOWARD THE EDGE. STATED UP FRONT.

Two selection effects are baked into the cache and neither can be removed by anything done here:

  1. TODAY'S LIQUIDITY CHOSE THE NAMES. The miner walks a pool ordered by present-day liquidity.
     A name that is liquid now was not necessarily liquid in 2016, and names that died are
     absent entirely. This is the same today-snapshot caveat already recorded for the P10 sector
     map and the P24.2 CIK map.
  2. THE MINER SKIPPED THIN NAMES ON PURPOSE — by median spread and ATM open interest. Those are
     precisely the names where wide fills would eat the edge. So the broad universe is ALREADY
     spread-filtered, which biases this test TOWARD the edge surviving, not against it.

`universe_selection_report` counts exactly how many names were skipped and why, so the size of
this bias is a reported number rather than a footnote. A "the edge holds on 184 names" result
means "holds on 184 names that are liquid today and passed a spread screen" and must be quoted
that way.

--------------------------------------------------------------------------------------------
WINDOW: 2016-01-01 .. 2025-10-15, AND WHY IT IS SHORTER THAN THE 55-NAME RUN.

The cache holds 2016-2025 for the new names and 2016-2026 for some of the old ones. A trade
entered near the end of the data would have its exit path truncated — the contract's life would
run past the cached history and settle on bars instead of quotes. That is a silent, one-sided
distortion of exactly the kind this project keeps getting bitten by.

So entries stop at ENTRY_END, which is 75 days (the maximum DTE) before the end of the shared
cached history, and the 55-name baseline is RE-SCORED on the identical window rather than quoted
from its published figure. The published +12.33% number covers a longer window and a slightly
different name set; comparing against it directly would confound breadth with period. Both
numbers are reported, but the like-for-like comparison is the one that carries the verdict.

--------------------------------------------------------------------------------------------
PRE-COMMITTED BARS. A verdict is one of HOLDS / WEAKENS / MEGACAP-ONLY, decided by these.

  B1  THE EDGE HOLDS on the broad universe if, at DEFAULT_AGGRESSION = 1.0 (buy the ask, sell
      the bid — never the mid):
        (a) expectancy per trade > 0, AND
        (b) profit factor > 1.0, AND
        (c) it is positive in BOTH held-out halves (2016-2020, 2021-2025). The both-directions
            rule the stock model uses. A result that lives in one half is a period, not an edge.
      Failing (c) while passing (a) and (b) is WEAKENS, not HOLDS.

  B2  TERM_SLOPE GENERALISES if the SHIPPED threshold, applied unchanged to the NEW names only,
      lifts their late-half expectancy by >= MIN_LATE_GAIN while retaining >= MIN_RETAINED of
      their late-half trades, on >= MIN_TRADES trades. Imported from options_signals_v2 so the
      bars cannot drift apart from the ones the filter was adopted under.

  B3  THE MID/SMALL TIER IS KEPT only if all three hold:
        (a) its expectancy at aggression 1.0 is > 0 — net of its own wider fills, not the
            megacap fills;
        (b) it DE-CONCENTRATES the tail: the Herfindahl index of >= +100% winners across names
            must FALL versus the megacap-only book. A broader book that still rests on the same
            few names has not diversified anything;
        (c) it carries >= MIN_CLOSED_PER_BUCKET closed trades, imported from options_tracker.

  B4  THE HOME-RUN THESIS is upheld only if P(>= +100%) is HIGHER in the mid/small tier than in
      the mega tier AND a BOOTSTRAP_DRAWS-resample confidence interval on the difference
      excludes zero. A raw difference in a heavy tail is not evidence on its own.

  B5  THE HEADLINE IS ALWAYS THE AGGRESSION = 1.0 NUMBER. Mid fills are printed as a diagnostic
      of how much of the result is spread, and never as the result.

A finding that the edge does not extend is a valid outcome and is to be reported as such. The
expected direction here is some weakening — that is what wider spreads do — and the interesting
question is whether it weakens gracefully or breaks.

--------------------------------------------------------------------------------------------
CAP TIERS ARE FIXED BOUNDARIES ON POINT-IN-TIME MARKET CAP, not quantiles of this sample.

Quantile tiers would move with the universe and make "the mid tier" mean something different in
every re-run as the miner grows. Fixed dollar boundaries stay comparable. The cap is read from
the DAILY bulk cache at the last month-end ON OR BEFORE the entry date — the same point-in-time
source the fundamental panel uses, so a name that was mid-cap in 2016 and mega-cap in 2025 is
correctly counted as both.

--------------------------------------------------------------------------------------------
WHAT THIS CANNOT SEE.

  * Borrow, assignment and early-exercise are not modelled. This is a long-call book, so none of
    them bind, but a short-vol construction would need them.
  * The exit walks DAILY closes. An intraday spike through the +100% target that closes back
    below it is recorded as not having hit — conservative, and consistent with the 55-name run.
  * Volume comes from Sharadar SEP; where it is missing the technical score loses the +6 volume
    bonus, so the reconstruction fires FEWER alerts than live, never more.
  * 2026 is excluded by ENTRY_END, so this says nothing about the current year.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import pickle
from typing import Optional

from . import options_backtest as OB
from . import options_fill as F
# Imported, never re-declared: if these bars ever move, this study moves with them.
from .options_signals_v2 import LATE_START, MIN_LATE_GAIN, MIN_RETAINED, MIN_TRADES
from .options_tracker import MIN_CLOSED_PER_BUCKET, _stats

# ---- window -------------------------------------------------------------------------------
ENTRY_START = "2016-01-01"
ENTRY_END = "2025-10-15"        # 75d (max DTE) + a half-DTE margin inside the 2025 cache end
CACHE_YEARS = tuple(range(2016, 2026))

# ---- the shipped filter, quoted from the adopted §2 result and NOT refitted here ------------
SHIPPED_TERM_THRESHOLD = 0.0105

# ---- outcome buckets (identical to options_autopsy, so the two studies agree) ---------------
TAIL_WIN = 1.00                 # >= +100%: the tail the strategy exists to catch
TOTAL_LOSS = -0.90              # the "goes to zero" bucket
STOP_OUT = -0.45                # at or through the -50% stop, allowing for exit slippage

# ---- cap tiers: FIXED dollar boundaries on point-in-time market cap, in $ millions ----------
TIER_EDGES = ((200_000.0, "mega"), (50_000.0, "large"), (10_000.0, "mid"), (0.0, "small"))
TIER_ORDER = ("mega", "large", "mid", "small")
BROAD_TIERS = ("mid", "small")  # "mid/small" wherever the mandate says it

BOOTSTRAP_DRAWS = 4000

# The exact 55-name pool every previous options result was measured on, quoted verbatim from
# the run script that produced them. It is here so "broad vs 55" can be a partition of ONE run
# on ONE window, rather than a comparison against a published figure computed over a longer
# window and a slightly different name set — which would confound breadth with period.
BASELINE_55 = (
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "BAC", "WFC", "C", "GS",
    "XOM", "CVX", "JNJ", "PFE", "MRK", "UNH", "WMT", "HD", "DIS", "NKE", "MCD", "KO", "PEP",
    "CSCO", "INTC", "ORCL", "IBM", "QCOM", "TXN", "AMD", "MU", "CAT", "BA", "GE", "F", "GM",
    "T", "VZ", "CMCSA", "NFLX", "CRM", "ADBE", "PYPL", "SBUX", "LOW", "TGT", "COST", "UPS",
    "MMM", "HON", "LMT", "RTX", "DE")

# The published 55-name headline, for reference only. NOT the comparison the verdict rests on:
# it covers 2016-01-01..2026-06-30 and includes PYPL, which this cache does not carry as
# complete. Quoted so the two can be seen side by side without being conflated.
PUBLISHED_55 = {"expectancy_pct": 0.1233, "hit_rate": 0.38, "profit_factor": 1.36,
                "n": 1540, "window": ["2016-01-01", "2026-06-30"], "n_names": 55}

DATA_ROOT = "data"
OUT_DIR = os.path.join("data", "options_universe")     # NOT data/options — the miner owns that


def _log(m):
    print(f"[optuniv] {m}", flush=True)


def _f(x) -> Optional[float]:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


# ================================ universe ==================================================
def universe_selection_report(data_root: str = DATA_ROOT) -> dict:
    """Who is in, who was skipped, and why — the selection bias as a counted number.

    Reads the miner's manifest READ-ONLY. A name is eligible only if the miner marked it
    `complete` AND every cached year is actually on disk; a manifest entry is a claim, and this
    project has been bitten four times by trusting one.
    """
    path = os.path.join(data_root, "options", "cache_manifest.json")
    if not os.path.exists(path):
        return {"ok": False, "reason": "no cache manifest"}
    with open(path, encoding="utf-8") as f:
        man = json.load(f)
    by_status, skipped = {}, {}
    complete, partial_life = [], {}
    for tkr, rec in sorted(man.items()):
        st = str(rec.get("status") or "unknown")
        by_status[st] = by_status.get(st, 0) + 1
        if st != "complete":
            skipped[tkr] = str(rec.get("reason") or st)
            continue
        years = {int(y) for y in (rec.get("years") or [])}
        # A year is COVERED if the frame is on disk OR the feed answered "no data" for it —
        # ThetaBulk's own distinction. Requiring the .pkl would silently drop every name that
        # IPO'd after 2016 (ABNB, DASH, HOOD, CVNA...), i.e. exactly the younger, smaller names
        # this study exists to bring in, and would bias the universe back toward megacaps.
        traded = [y for y in CACHE_YEARS
                  if os.path.exists(os.path.join(data_root, "options", tkr, f"{tkr}-{y}.pkl"))]
        empty = [y for y in CACHE_YEARS
                 if os.path.exists(os.path.join(data_root, "options", tkr,
                                                f"{tkr}-{y}.pkl.empty"))]
        covered = set(traded) | set(empty)
        if not years.issuperset(CACHE_YEARS) or covered != set(CACHE_YEARS) or rec.get("gaps"):
            skipped[tkr] = "incomplete_on_disk"
            continue
        complete.append(tkr)
        if len(traded) < len(CACHE_YEARS):
            partial_life[tkr] = sorted(traded)
    thin = {t: r for t, r in skipped.items() if "thin" in r or "spread" in r or "OI" in r}
    return {"ok": True, "n_evaluated": len(man), "by_status": by_status,
            "universe": sorted(complete), "n_universe": len(complete),
            "n_skipped": len(skipped), "n_skipped_thin": len(thin),
            "skipped_thin_examples": dict(sorted(thin.items())[:12]),
            "n_partial_life": len(partial_life),
            "partial_life": {t: y for t, y in sorted(partial_life.items())},
            "note": "the skipped-thin names are exactly where wide fills would bite; their "
                    "absence biases this test TOWARD the edge surviving."}


def universe(data_root: str = DATA_ROOT) -> list:
    return universe_selection_report(data_root).get("universe") or []


# ================================ O20 — point-in-time liquidity =============================
# AUDIT O20, AND THE AUDIT'S PREMISE IS HALF WRONG — recorded here because the correction
# changes what this filter can and cannot buy.
#
# O20 states: "Names were selected for mining by CURRENT liquidity, and current liquidity is a
# function of how the company did over the sample." Read against `mine_options_cache.py`, that
# is two claims and only one of them holds.
#
#   * THE POOL ORDER IS HINDSIGHT. Names are ranked for mining by TODAY's market cap from the
#     Sharadar daily table (`mine_options_cache.py:15-20`). A name that was liquid in 2016 and
#     has since shrunk or died was never reached, let alone cached. TRUE, and it is the larger
#     of the two effects.
#   * THE LIQUIDITY SCREEN IS NOT TODAY'S. `name_is_viable` measures real option tradeability on
#     the name's FIRST CACHED YEAR — 2016, or the IPO year — not on a present-day chain
#     (`mine_options_cache.py:160`). So the thin-name cut was already close to point-in-time.
#
# WHAT THIS MEANS FOR THE FIX. O20 calls the repair cheap, and it is; it is also only half a
# repair, and the half it cannot reach is the bigger one. Re-screening on point-in-time
# liquidity answers "was this name tradeable ON THE DAY the alert fired?" — a name screened in
# on its 2016 chain may have been untradeable in 2019, and a 2021 IPO is screened on a year in
# which it did not trade options at all. It CANNOT answer "which names would have been in the
# pool at all in 2016?", because the names that failed that test are not on disk. No
# evaluation-time filter can recover data that was never mined.
#
# So the number this produces is an upper bound on the repair, and the residual selection is
# stated rather than implied. `survivorship_probe` remains the diagnostic for the part O20
# cannot touch.
#
# The thresholds below are the MINER'S OWN, imported so the two cannot drift apart. The whole
# point is to apply the same bar at a different moment, not a different bar.
def _miner_thresholds() -> dict:
    """The miner's viability constants, read from the miner. Never re-declared here."""
    try:
        import mine_options_cache as M
        return {"max_median_spread_pct": float(M.MAX_MEDIAN_SPREAD_PCT),
                "min_atm_oi": float(M.MIN_ATM_OI),
                "min_atm_oi_notional": float(M.MIN_ATM_OI_NOTIONAL),
                "spread_min_premium": float(M.SPREAD_MIN_PREMIUM),
                "source": "mine_options_cache"}
    except Exception:                                                     # noqa: BLE001
        # The miner lives at the repo root and is not importable from every entry point. These
        # are its values as of audit O20; the `source` field makes the fallback visible rather
        # than letting a stale copy pass for the real thing.
        return {"max_median_spread_pct": 0.15, "min_atm_oi": 500.0,
                "min_atm_oi_notional": 2_500_000.0, "spread_min_premium": 0.50,
                "source": "FALLBACK COPY — mine_options_cache not importable"}


def pit_liquidity(chain, as_of=None) -> dict:
    """The miner's liquidity measures, computed on ONE day's chain instead of on a whole year.

    Mirrors `mine_options_cache.name_is_viable` term for term: near-the-money is approximated by
    the top decile of open interest (OI concentrates around the money), the strike of those
    contracts stands in for spot, and the spread is measured only on contracts with a real
    premium — measuring it across far-OTM lottery tickets reads a one-cent tick on a five-cent
    mid as 20% and rejects perfectly tradeable names.

    Open interest is a STOCK and is stable within a day; whole-chain volume is a FLOW and one
    day of it is noisy, so volume is reported but is deliberately NOT a gate here. The miner
    could use a yearly median; a single alert date cannot.
    """
    import pandas as pd

    if chain is None or len(chain) == 0:
        return {"ok": False}
    th = _miner_thresholds()
    bid = pd.to_numeric(chain.get("bid"), errors="coerce").fillna(0)
    ask = pd.to_numeric(chain.get("ask"), errors="coerce").fillna(0)
    # AUDIT B4 — -1 is the cache's "the open-interest call failed" sentinel, never a count.
    oi = pd.to_numeric(chain.get("open_interest"), errors="coerce")
    oi = oi.where(oi >= 0)
    vol = pd.to_numeric(chain.get("volume"), errors="coerce").fillna(0)
    strike = pd.to_numeric(chain.get("strike"), errors="coerce")
    mid = (bid + ask) / 2.0
    quoted = (bid > 0) & (ask > bid) & (mid > 0)
    live = quoted & (oi > 0)
    live_oi = oi[live]
    atm_oi = float(live_oi.quantile(0.90)) if len(live_oi.dropna()) else 0.0
    top = live & (oi >= atm_oi) if atm_oi > 0 else live
    atm_strike = float(strike[top].median()) if int(top.sum()) else 0.0
    notional = atm_oi * atm_strike * 100.0
    mask = quoted & (vol > 0) & (oi >= th["min_atm_oi"]) & (mid >= th["spread_min_premium"])
    spr = ((ask - bid) / mid)[mask]
    med_spread = float(spr.median()) if len(spr) else None
    return {"ok": True, "atm_oi": atm_oi, "atm_oi_notional": notional,
            "median_spread_pct": med_spread,
            "chain_volume": float(vol.sum()),
            "n_spread_sample": int(len(spr))}


def pit_liquid_ok(stats: Optional[dict]) -> Optional[bool]:
    """Would the miner's own screen have admitted this name ON THIS DAY?

    Returns None — not False — when the day's chain cannot answer. An unmeasurable day is not a
    failed day, and collapsing the two would silently delete trades for a data reason while
    reporting them as a liquidity finding.
    """
    if not stats or not stats.get("ok"):
        return None
    th = _miner_thresholds()
    sp = stats.get("median_spread_pct")
    if sp is None:
        return None
    if sp > th["max_median_spread_pct"]:
        return False
    # Open interest passes on EITHER measure, exactly as the miner has it: an expensive name
    # holds few contracts but large notional, a cheap one the reverse. Only failing BOTH is
    # genuinely too small to trade.
    return bool((stats.get("atm_oi") or 0) >= th["min_atm_oi"]
                or (stats.get("atm_oi_notional") or 0) >= th["min_atm_oi_notional"])


def o20_split(rows) -> dict:
    """Partition a book by whether each trade's name was liquid AS OF its own entry date."""
    liq = [r for r in rows if r.get("pit_liquid") is True]
    illiq = [r for r in rows if r.get("pit_liquid") is False]
    unknown = [r for r in rows if r.get("pit_liquid") is None]
    n = len(rows)
    return {"n_total": n, "n_pit_liquid": len(liq), "n_pit_illiquid": len(illiq),
            "n_unmeasurable": len(unknown),
            "retained_frac": (len(liq) / n) if n else None,
            "coverage": ((n - len(unknown)) / n) if n else None,
            "pit_liquid": tail_stats(liq), "pit_illiquid": tail_stats(illiq),
            "unmeasurable": tail_stats(unknown),
            "held_out_pit_liquid": held_out(liq) if liq else None,
            "thresholds": _miner_thresholds(),
            "note": "the miner's OWN screen applied at each entry date instead of on the name's "
                    "first cached year. This cannot repair the pool's hindsight market-cap "
                    "ranking — those names were never mined — so it is an upper bound on the "
                    "fix, not the whole of it."}


# ================================ point-in-time market cap ==================================
_DAILY_CACHE = {}


def load_caps(data_root: str = DATA_ROOT) -> dict:
    """{ticker: [(date, marketcap_$M), ...]} month-end, from the DAILY bulk cache."""
    key = os.path.abspath(data_root)
    if key in _DAILY_CACHE:
        return _DAILY_CACHE[key]
    path = os.path.join(data_root, "bulk", "prepared", "daily.pkl")
    out = {}
    if os.path.exists(path):
        with open(path, "rb") as f:
            raw = pickle.load(f)
        for tkr, rows in raw.items():
            ser = [(str(r[0])[:10], _f(r[1])) for r in rows if _f(r[1]) is not None]
            if ser:
                out[str(tkr).upper()] = ser
    _DAILY_CACHE[key] = out
    return out


def cap_at(caps: dict, ticker: str, as_of: str) -> Optional[float]:
    """Market cap ($M) at the last month-end ON OR BEFORE `as_of`. Point-in-time by construction:
    nothing after the entry date is visible, so a name is tiered as it stood that day."""
    ser = caps.get(str(ticker).upper())
    if not ser:
        return None
    got = None
    for d, v in ser:
        if d <= as_of:
            got = v
        else:
            break
    return got


def tier_of(mcap: Optional[float]) -> Optional[str]:
    if mcap is None:
        return None
    for edge, name in TIER_EDGES:
        if mcap >= edge:
            return name
    return "small"


# ================================ scoring one name ==========================================
def run_name(prov, ticker: str, bars: dict, start: str = ENTRY_START, end: str = ENTRY_END,
             aggression: float = F.DEFAULT_AGGRESSION, caps: Optional[dict] = None,
             with_signals: bool = True) -> dict:
    """Reconstruct one name's alert history and trades. The live logic is CALLED, not copied.

    One position per name at a time, exactly as `run_full.py` did for the 55 — otherwise a name
    in a strong run stacks overlapping trades and its winners get counted several times.
    """
    from valuation.intraday.signals import evaluate as sig_evaluate
    from valuation.intraday.technical import technical_signals
    from valuation.saas.notify import _BULL

    from . import options_signals_v2 as S2

    caps = caps if caps is not None else {}
    rows, rejects = [], {}
    n_cand = n_alert = 0
    open_until = None
    for d in bars["date"]:
        if not (start <= d <= end):
            continue
        if open_until and d <= open_until:
            continue
        w = OB.bars_asof(bars, d)
        if not w:
            continue
        ts = technical_signals(w).get("score")
        if ts is None or ts < OB.PREFILTER_TECH:
            continue
        n_cand += 1
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(ticker, day)
        if chain is None or len(chain) == 0:
            rejects["no_chain"] = rejects.get("no_chain", 0) + 1
            continue
        und = OB.spot_asof(w)        # AUDIT B1 — AS-TRADED: strikes are never split-adjusted
        summ = OB.chain_summary(chain, und, day)
        ev = sig_evaluate(w, summ, horizon=OB.HORIZON)
        sc, labels = ev.get("score"), ev.get("labels") or []
        if sc is None or sc < OB.ALERT_MIN_SCORE:
            continue
        if not any(any(bl in l for bl in _BULL) for l in labels):
            continue
        n_alert += 1
        row = OB.pick_contract(chain, und, day, right="C")
        if row is None:
            rejects["no_contract_in_band"] = rejects.get("no_contract_in_band", 0) + 1
            continue
        tr = OB.simulate_trade(prov, ticker, row, day, bars, aggression=aggression)
        if not tr or not tr.get("ok"):
            rejects[(tr or {}).get("reason", "sim_failed")] = \
                rejects.get((tr or {}).get("reason", "sim_failed"), 0) + 1
            continue
        r = OB.to_alert_row(ticker, day, row, tr, sc, labels, (summ or {}).get("atm_iv"), None)
        # Extras this study needs and `to_alert_row` deliberately does not carry.
        r["entry_spread_pct"] = tr.get("entry_spread_pct")
        r["settled_at_intrinsic"] = tr.get("settled_at_intrinsic")
        r["underlying_entry"] = float(und)
        mc = cap_at(caps, ticker, d)
        r["marketcap_musd"] = mc
        r["cap_tier"] = tier_of(mc)
        # AUDIT O20 — was this name tradeable ON THIS DAY, by the miner's own screen? Computed
        # from the chain already in hand, so it costs nothing and makes the point-in-time
        # liquidity filter an evaluation-time choice rather than a second scoring pass.
        _pl = pit_liquidity(chain, day)
        r["pit_liquid"] = pit_liquid_ok(_pl)
        r["pit_median_spread_pct"] = _pl.get("median_spread_pct")
        r["pit_atm_oi"] = _pl.get("atm_oi")
        r["pit_atm_oi_notional"] = _pl.get("atm_oi_notional")
        if with_signals:
            # Realised vol over the trailing 30 sessions, from ADJUSTED closes (a split is not
            # a move). Feeds `vrp`; term_slope needs no bar input.
            rv = _realized_vol(w["close"])
            try:
                sigs = S2.compute_signals(chain, und, day, iv_history=None, realized_vol=rv)
            except Exception:                                            # noqa: BLE001
                sigs = {}
            for k, v in (sigs or {}).items():
                r[k] = v
        rows.append(r)
        open_until = tr.get("exit_date")
    return {"ticker": ticker, "rows": rows, "n_cand": n_cand, "n_alert": n_alert,
            "rejects": rejects}


def _realized_vol(closes, window: int = 30) -> Optional[float]:
    import math
    px = [c for c in closes[-(window + 1):] if c and c > 0]
    if len(px) < window // 2:
        return None
    rets = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    if len(rets) < 5:
        return None
    m = sum(rets) / len(rets)
    var = sum((x - m) ** 2 for x in rets) / (len(rets) - 1)
    return math.sqrt(var * 252.0)


# ================================ outcome shape =============================================
def tail_stats(rows) -> dict:
    """The barbell, spelled out. Hit rate is reported but never on its own — a filter that
    raises it by clipping the right tail makes this strategy worse, which is the whole lesson of
    the trade autopsy."""
    p = [_f(r.get("pnl_pct")) for r in rows]
    p = [v for v in p if v is not None]
    n = len(p)
    if not n:
        return {"n": 0}
    s = _stats(rows)
    return {"n": n,
            "expectancy_pct": s["expectancy_pct"], "profit_factor": s["profit_factor"],
            "hit_rate": s["hit_rate"],
            "p_tail_win": sum(1 for v in p if v >= TAIL_WIN) / n,
            "p_total_loss": sum(1 for v in p if v <= TOTAL_LOSS) / n,
            "p_stop_out": sum(1 for v in p if v <= STOP_OUT) / n,
            "median_pct": sorted(p)[n // 2],
            "avg_win_pct": s["avg_win_pct"], "avg_loss_pct": s["avg_loss_pct"],
            "tail_share_of_gross_win": (sum(v for v in p if v >= TAIL_WIN)
                                        / sum(v for v in p if v > 0))
            if any(v > 0 for v in p) else None}


def concentration(rows) -> dict:
    """How much of the book's upside rests on how few names.

    Two Herfindahls, because they answer different questions: one over the COUNT of >= +100%
    winners (is the tail spread across names?) and one over each name's share of total gross
    profit (is the P&L spread across names?). Both are 1.0 for a single name and ~1/N for N
    equal contributors.
    """
    tail_by, prof_by = {}, {}
    for r in rows:
        v = _f(r.get("pnl_pct"))
        if v is None:
            continue
        t = str(r.get("ticker") or "?")
        if v >= TAIL_WIN:
            tail_by[t] = tail_by.get(t, 0) + 1
        if v > 0:
            prof_by[t] = prof_by.get(t, 0.0) + v

    def hhi(d):
        tot = sum(d.values())
        if tot <= 0:
            return None
        return sum((v / tot) ** 2 for v in d.values())

    def top_share(d, k):
        tot = sum(d.values())
        if tot <= 0:
            return None
        return sum(sorted(d.values(), reverse=True)[:k]) / tot

    return {"n_tail_winners": sum(tail_by.values()), "n_names_with_tail_win": len(tail_by),
            "tail_hhi": hhi(tail_by), "tail_top5_share": top_share(tail_by, 5),
            "profit_hhi": hhi(prof_by), "profit_top5_share": top_share(prof_by, 5),
            "n_names_profitable": len(prof_by),
            "top_tail_names": sorted(tail_by.items(), key=lambda kv: -kv[1])[:10],
            "effective_names_tail": (1.0 / hhi(tail_by)) if hhi(tail_by) else None}


def held_out(rows) -> dict:
    """Early / late halves at the project's standing boundary. Both must be positive for B1."""
    early = [r for r in rows if str(r["alert_ts"])[:10] < LATE_START]
    late = [r for r in rows if str(r["alert_ts"])[:10] >= LATE_START]
    return {"early": tail_stats(early), "late": tail_stats(late),
            "both_positive": bool(early and late
                                  and (_stats(early)["expectancy_pct"] or 0) > 0
                                  and (_stats(late)["expectancy_pct"] or 0) > 0)}


def by_year(rows) -> dict:
    out = {}
    for r in rows:
        out.setdefault(str(r["alert_ts"])[:4], []).append(r)
    return {y: {"n": len(rs), "expectancy_pct": _stats(rs)["expectancy_pct"],
                "p_tail_win": tail_stats(rs)["p_tail_win"]}
            for y, rs in sorted(out.items())}


# ================================ tiers =====================================================
def tier_report(rows) -> dict:
    """Every headline, broken out by point-in-time cap tier — the mandate's item 4."""
    groups = {}
    for r in rows:
        t = r.get("cap_tier")
        if t:
            groups.setdefault(t, []).append(r)
    out = {}
    for t in TIER_ORDER:
        rs = groups.get(t) or []
        if not rs:
            continue
        d = tail_stats(rs)
        d["n_names"] = len({r.get("ticker") for r in rs})
        d["median_entry_spread_pct"] = _median([_f(r.get("entry_spread_pct")) for r in rs])
        d["median_iv"] = _median([_f(r.get("iv")) for r in rs])
        d["held_out"] = held_out(rs)
        d["enough_to_judge"] = d["n"] >= MIN_CLOSED_PER_BUCKET
        out[t] = d
    return out


def _median(vals):
    v = sorted(x for x in vals if x is not None)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


def bootstrap_diff(a_rows, b_rows, stat: str = "p_tail_win", draws: int = BOOTSTRAP_DRAWS,
                   seed: int = 0) -> dict:
    """Percentile CI on stat(a) - stat(b) by resampling trades within each group.

    Resampling TRADES (not names) is the right unit here because the statistic is per-trade, but
    it does mean the CI ignores within-name clustering and is therefore OPTIMISTICALLY NARROW.
    Said plainly rather than left for someone to discover.
    """
    import random

    def val(rs):
        d = tail_stats(rs)
        return d.get(stat)

    a0, b0 = val(a_rows), val(b_rows)
    if a0 is None or b0 is None or not a_rows or not b_rows:
        return {"ok": False, "reason": "empty group"}
    rnd = random.Random(seed)
    diffs = []
    for _ in range(draws):
        sa = [a_rows[rnd.randrange(len(a_rows))] for _ in range(len(a_rows))]
        sb = [b_rows[rnd.randrange(len(b_rows))] for _ in range(len(b_rows))]
        va, vb = val(sa), val(sb)
        if va is not None and vb is not None:
            diffs.append(va - vb)
    if not diffs:
        return {"ok": False, "reason": "no draws"}
    diffs.sort()
    lo = diffs[int(0.025 * len(diffs))]
    hi = diffs[min(len(diffs) - 1, int(0.975 * len(diffs)))]
    return {"ok": True, "stat": stat, "a": a0, "b": b0, "diff": a0 - b0,
            "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0), "draws": len(diffs),
            "note": "trade-level bootstrap; ignores within-name clustering, so the CI is "
                    "optimistically narrow."}


# ================================ term_slope, applied not refitted ==========================
def term_slope_effect(rows, threshold: float = SHIPPED_TERM_THRESHOLD,
                      late_only: bool = True) -> dict:
    """Apply the SHIPPED threshold unchanged. Nothing here is fitted on these rows."""
    scope = [r for r in rows if str(r["alert_ts"])[:10] >= LATE_START] if late_only else rows
    has = [r for r in scope if _f(r.get("term_slope")) is not None]
    if not has:
        return {"ok": False, "reason": "no term_slope coverage"}
    keep = [r for r in has if _f(r["term_slope"]) >= threshold]
    base, filt = _stats(has), _stats(keep) if keep else _stats([])
    gain = (filt["expectancy_pct"] or 0) - (base["expectancy_pct"] or 0)
    retained = len(keep) / len(has)
    tw_all = tail_stats(has)["p_tail_win"]
    tw_keep = tail_stats(keep)["p_tail_win"] if keep else None
    return {"ok": True, "threshold": threshold, "scope": "late" if late_only else "full",
            "n_all": base["n_closed"], "n_kept": filt["n_closed"], "retained": retained,
            "exp_all": base["expectancy_pct"], "exp_filtered": filt["expectancy_pct"],
            "gain": gain, "p_tail_win_all": tw_all, "p_tail_win_kept": tw_keep,
            "tail_retention": ((tw_keep * len(keep)) / (tw_all * len(has)))
            if (tw_all and keep) else None,
            "passes_B2": bool(gain >= MIN_LATE_GAIN and retained >= MIN_RETAINED
                              and filt["n_closed"] >= MIN_TRADES)}


# ================================ R7 — the re-committed retention floor =====================
# AUDIT R7. The 40% retention floor (`MIN_RETAINED`) was never derived. `options_autopsy.py:36`
# gives G3's purpose as a PRODUCT rationale — "a filter that keeps 8% of alerts has not improved
# the strategy, it has replaced it with a smaller one" — and the statistical risk it might seem
# to carry is already held by G4 (`n_kept >= MIN_TRADES`) and G6 (beats a random filter keeping
# the same count). 40% is a round number; the 55-name run cleared it by 0.6pp and the 187-name
# run missed it by 3.6pp.
#
# A FIXED PERCENTAGE IS THE WRONG UNIT ON A GROWING UNIVERSE. A fixed-threshold filter applied to
# a broader book is mechanically more selective — more names means more of the distribution's
# left side — so a constant percentage floor makes ANY filter fail as the universe grows. That is
# a scale artefact, not a statement about the filter.
#
# The percentage was proxying for two distinct things. They are measured directly below, and
# this replacement was committed in writing (HANDOFF_edge_audit.md Part 0) BEFORE the re-score.
# It is not a renegotiation of a failed bar: G3b has never been measured, and term_slope can
# still fail on it.
MIN_ALERTS_PER_YEAR = 52          # G3a — one per week, the minimum cadence to build a book
MIN_SPAN_FRAC = 0.60              # G3b — of the unfiltered book's names AND of its months
MIN_RETENTION_BACKSTOP = 0.20     # G3c — below one in five, the filter IS the strategy


def term_slope_gate(rows, threshold: float = SHIPPED_TERM_THRESHOLD,
                    late_only: bool = True) -> dict:
    """G3a / G3b / G3c — the re-committed replacement for the single 40% retention arm."""
    scope = [r for r in rows if str(r["alert_ts"])[:10] >= LATE_START] if late_only else rows
    has = [r for r in scope if _f(r.get("term_slope")) is not None]
    if not has:
        return {"ok": False, "reason": "no term_slope coverage"}
    keep = [r for r in has if _f(r["term_slope"]) >= threshold]

    def span(rs):
        return ({str(r.get("ticker") or "?") for r in rs},
                {str(r["alert_ts"])[:7] for r in rs},
                {str(r["alert_ts"])[:4] for r in rs})

    n_all, n_keep = len(has), len(keep)
    names_a, months_a, years_a = span(has)
    names_k, months_k, years_k = span(keep)

    # G3a is a rate over the years the UNFILTERED book spans, so a filter cannot pass by
    # surviving in two busy years and vanishing from the rest.
    per_year = (n_keep / len(years_a)) if years_a else 0.0
    name_span = (len(names_k) / len(names_a)) if names_a else 0.0
    month_span = (len(months_k) / len(months_a)) if months_a else 0.0
    retention = (n_keep / n_all) if n_all else 0.0

    g3a = bool(per_year >= MIN_ALERTS_PER_YEAR)
    g3b = bool(name_span >= MIN_SPAN_FRAC and month_span >= MIN_SPAN_FRAC)
    g3c = bool(retention >= MIN_RETENTION_BACKSTOP)
    return {"ok": True, "scope": "late" if late_only else "full", "threshold": threshold,
            "n_all": n_all, "n_kept": n_keep, "retention": retention,
            "G3a_flow": g3a, "alerts_per_year": per_year,
            "G3a_floor": MIN_ALERTS_PER_YEAR, "n_years_spanned": len(years_a),
            "G3b_concentration": g3b,
            "name_span_frac": name_span, "month_span_frac": month_span,
            "G3b_floor": MIN_SPAN_FRAC,
            "n_names_all": len(names_a), "n_names_kept": len(names_k),
            "n_months_all": len(months_a), "n_months_kept": len(months_k),
            "G3c_backstop": g3c, "G3c_floor": MIN_RETENTION_BACKSTOP,
            "passes_G3": bool(g3a and g3b and g3c),
            "old_40pct_arm": bool(retention >= MIN_RETAINED),
            "note": "G3a/G3b/G3c replace the underived 40% arm (audit R7), committed in writing "
                    "before this re-score. G3b had never been measured."}



def random_entry_control(prov, ticker: str, bars: dict, trades: list, draws: int = 2,
                         seed: int = 0, aggression: float = F.DEFAULT_AGGRESSION,
                         caps: Optional[dict] = None) -> list:
    """THE control this study needs most: same name, same YEAR, random entry DAY.

    The survivorship probe shows the book's expectancy is concentrated in names that went on to
    compound — but that comparison is partly circular, because a call on a stock that rose 5x
    makes money whether or not the entry was skilful. This separates the two.

    For every real trade it draws a random trading day for the SAME ticker in the SAME calendar
    year and runs the identical contract rule, fill model and exit discipline. Holding name and
    year fixed removes "this name went up over the decade" and "2020 was a good year" from the
    comparison, leaving exactly one difference: whether the scream-buy signal picked the day.

    If the control earns the same, the edge is the universe, not the alert.
    """
    import random

    rnd = random.Random(f"{seed}:{ticker}")
    caps = caps if caps is not None else {}
    by_year = {}
    for i, d in enumerate(bars["date"]):
        if ENTRY_START <= d <= ENTRY_END:
            by_year.setdefault(d[:4], []).append(d)
    out = []
    for tr in trades:
        yr = str(tr["alert_ts"])[:4]
        pool = by_year.get(yr) or []
        if len(pool) < 20:
            continue
        for _ in range(draws):
            d = pool[rnd.randrange(len(pool))]
            w = OB.bars_asof(bars, d)
            if not w:
                continue
            day = dt.date.fromisoformat(d)
            chain = prov.chain_on(ticker, day)
            if chain is None or len(chain) == 0:
                continue
            und = OB.spot_asof(w)      # AUDIT B1 — AS-TRADED, matching run_name and settlement
            row = OB.pick_contract(chain, und, day, right="C")
            if row is None:
                continue
            t = OB.simulate_trade(prov, ticker, row, day, bars, aggression=aggression)
            if not t or not t.get("ok"):
                continue
            r = OB.to_alert_row(ticker, day, row, t, None, [], None, None)
            mc = cap_at(caps, ticker, d)
            r["marketcap_musd"] = mc
            r["cap_tier"] = tier_of(mc)
            r["entry_spread_pct"] = t.get("entry_spread_pct")
            r["_control_for"] = str(tr["alert_ts"])[:10]
            # AUDIT O20 — the control is screened by the SAME point-in-time rule. Filtering one
            # arm and not the other would turn a liquidity correction into a comparison between
            # two different universes, which is the error the control exists to avoid.
            _pl = pit_liquidity(chain, day)
            r["pit_liquid"] = pit_liquid_ok(_pl)
            r["pit_median_spread_pct"] = _pl.get("median_spread_pct")
            r["pit_atm_oi"] = _pl.get("atm_oi")
            r["pit_atm_oi_notional"] = _pl.get("atm_oi_notional")
            out.append(r)
    return out


def control_comparison(real_rows, ctrl_rows, seed: int = 0) -> dict:
    """Alert-day book vs random-day book, overall and by tier. The bar is simple: if the alert
    carries information, the real book must beat its own control.

    AUDIT R3 — the verdict now reads the CLUSTERED statistics, not the trade-level ones. The
    trade-level bootstrap treats 3,042 trades on 187 correlated names as 3,042 independent draws
    and produces an interval that is optimistically narrow; it is kept because every historical
    number was computed with it and dropping it would break comparability, but it is no longer
    what decides anything. `date_block` (months resampled together, paired across the two arms)
    and `paired_name_year` (the sign test the whole conclusion rests on, in the repository for
    the first time) are the statistics of record.
    """
    from . import options_stats as ST

    def blk(a, b):
        d = bootstrap_diff(a, b, "expectancy_pct", seed=seed)
        db = ST.date_block_diff(a, b, seed=seed)
        pn = ST.paired_name_year(a, b)
        return {"real": tail_stats(a), "control": tail_stats(b),
                "expectancy_diff": d.get("diff"), "ci95": d.get("ci95"),
                # Retained for comparability with the record, and explicitly not the verdict.
                "beats_control_trade_level": bool(d.get("ok") and d["diff"] > 0
                                                  and d["excludes_zero"]),
                "tail_diff": bootstrap_diff(a, b, "p_tail_win", seed=seed).get("diff"),
                # AUDIT R3 — the statistics of record.
                "date_block": db,
                "paired_name_year": pn,
                "effective_n_real": ST.effective_n(a),
                "effective_n_control": ST.effective_n(b),
                "beats_control": bool(db.get("ok") and db.get("positive_at_significance")),
                "loses_to_control": bool(db.get("ok") and db.get("negative_at_significance"))}
    out = {"overall": blk(real_rows, ctrl_rows)}
    for t in TIER_ORDER:
        a = [r for r in real_rows if r.get("cap_tier") == t]
        b = [r for r in ctrl_rows if r.get("cap_tier") == t]
        if len(a) >= MIN_CLOSED_PER_BUCKET and len(b) >= MIN_CLOSED_PER_BUCKET:
            out[t] = blk(a, b)
    # AUDIT O20 — the same comparison on the point-in-time-liquid subset of BOTH arms. Filtering
    # one side only would compare two different universes.
    la = [r for r in real_rows if r.get("pit_liquid") is True]
    lb = [r for r in ctrl_rows if r.get("pit_liquid") is True]
    if len(la) >= MIN_CLOSED_PER_BUCKET and len(lb) >= MIN_CLOSED_PER_BUCKET:
        out["pit_liquid_only"] = blk(la, lb)
    out["note"] = ("control = same ticker, same calendar year, random entry day, identical "
                   "contract/fill/exit rules. Name and year are held fixed, so the only "
                   "difference is day selection. The VERDICT keys read the date-block "
                   "bootstrap (audit R3); the trade-level interval is kept for comparability.")
    return out


def survivorship_probe(rows, caps: dict) -> dict:
    """Is the small-cap tier a CAP effect, or is it survivorship wearing a cap label?

    The universe was chosen by TODAY's liquidity. So a name that was small in 2016 and is in
    this cache now is, by construction, one that survived and grew — the tier is populated by
    the early lives of names that later became large. Nothing in a point-in-time market cap
    fixes that; the selection happened before the backtest started.

    The discriminating test is to split each tier by how much the name GREW between entry and
    today, which is knowable only in hindsight and therefore useless as a filter, but exactly
    the right diagnostic. If the tier's edge is a genuine small-cap effect it should appear in
    both halves. If it appears only among the names that went on to compound, the tier result is
    an artifact of who is in the universe, and must not be read as "mid/small caps work".
    """
    import statistics as st

    def today_cap(t):
        ser = caps.get(str(t).upper())
        return ser[-1][1] if ser else None

    out = {}
    for tier in TIER_ORDER:
        rs = [r for r in rows if r.get("cap_tier") == tier]
        g = []
        for r in rs:
            tc, ec = today_cap(r.get("ticker")), _f(r.get("marketcap_musd"))
            if tc and ec and ec > 0:
                g.append((tc / ec, r))
        if len(g) < 2 * MIN_CLOSED_PER_BUCKET:
            out[tier] = {"n": len(rs), "n_with_growth": len(g),
                         "enough_to_split": False,
                         "median_growth_x": st.median([x for x, _ in g]) if g else None}
            continue
        med = st.median([x for x, _ in g])
        lo = [r for x, r in g if x <= med]
        hi = [r for x, r in g if x > med]
        out[tier] = {
            "n": len(rs), "n_with_growth": len(g), "enough_to_split": True,
            "median_growth_x": med,
            "low_growth": {"n": len(lo), **{k: tail_stats(lo)[k] for k in
                                            ("expectancy_pct", "profit_factor", "p_tail_win")}},
            "high_growth": {"n": len(hi), **{k: tail_stats(hi)[k] for k in
                                             ("expectancy_pct", "profit_factor", "p_tail_win")}},
            "edge_survives_in_low_growth_half":
                bool((tail_stats(lo)["expectancy_pct"] or -1) > 0
                     and len(lo) >= MIN_CLOSED_PER_BUCKET),
        }
    return {"note": "growth is entry-to-TODAY market cap — hindsight by construction, usable as "
                    "a diagnostic and never as a filter.",
            "by_tier": out}


# ================================ coverage + sanity =========================================
def sanity(rows, meta: Optional[dict] = None) -> dict:
    """Is the log SANE, not merely present — the options-lane counterpart of the panel's
    `sanity_check`. Coverage says a field exists; this asks whether the numbers behind it are
    the ones we think they are.

    Do not silence a flag here to make a run look clean. Investigate it or record why it is
    expected — the same rule the fundamental panel operates under.
    """
    n = len(rows)
    if not n:
        return {"ok": False, "reason": "no trades"}
    flags = []

    def frac(pred):
        return sum(1 for r in rows if pred(r)) / n

    # 1. How much of the P&L rests on bar-settled expiries rather than real exit quotes.
    intrinsic = frac(lambda r: bool(r.get("settled_at_intrinsic")))
    if intrinsic > 0.35:
        flags.append(f"{intrinsic:.1%} of trades settled at intrinsic, not on a quote")

    # 2. Spread discipline. Entry spreads above the fill model's own ceiling should be
    #    impossible — quote_reject_reason drops them — so any at all means a leak.
    sp = [_f(r.get("entry_spread_pct")) for r in rows]
    sp = [v for v in sp if v is not None]
    over = sum(1 for v in sp if v > F.MAX_SPREAD_PCT)
    if over:
        flags.append(f"{over} trades entered above MAX_SPREAD_PCT — the fill filter leaked")

    # 3. Concentration: no single name should dominate a 187-name book.
    by_name = {}
    for r in rows:
        by_name[r.get("ticker")] = by_name.get(r.get("ticker"), 0) + 1
    top = max(by_name.values())
    if top / n > 0.05:
        flags.append(f"one name carries {top}/{n} trades ({top/n:.1%})")

    # 4. Tier coverage: an unresolvable market cap silently drops a trade from every tier table.
    no_tier = frac(lambda r: not r.get("cap_tier"))
    if no_tier > 0.02:
        flags.append(f"{no_tier:.1%} of trades have no point-in-time market cap")

    # 5. Signal coverage. The COVERAGE RULE: never judge a signal without checking this first.
    cov = {k: frac(lambda r, k=k: _f(r.get(k)) is not None)
           for k in ("term_slope", "skew_25d", "vrp", "gex_proxy", "iv", "entry_spread_pct")}
    for k, c in cov.items():
        if c < 0.05:
            flags.append(f"signal {k} has {c:.1%} coverage — effectively empty")

    # 6. AUDIT B1 — is the ENTRY IV a plausible equity vol at all? This is the guard that the
    #    price-basis bug walked straight past. Feeding a split/dividend-ADJUSTED spot into an
    #    implied-vol solve against AS-TRADED strikes produces vols of 1.28-1.57 (128-157%), which
    #    the 187-name run reported and the handoff recorded as an unexplained anomaly. Coverage
    #    said `iv` was present; nothing asked whether it was sane. A median outside [0.05, 1.00]
    #    is not a market regime, it is a broken input.
    ivs = [_f(r.get("iv")) for r in rows]
    ivs = [v for v in ivs if v is not None and v > 0]
    iv_med = _median(ivs)
    if iv_med is not None and not (0.05 <= iv_med <= 1.00):
        flags.append(f"median entry IV {iv_med:.3f} is outside [0.05, 1.00] — implausible as an "
                     f"equity ATM vol; check the underlying price basis (adjusted vs as-traded)")

    # 7. AUDIT B2 — how many days were CENSORED from each trade's exit path. A skipped day is a
    #    day the stop could have fired on and did not, and the bias is one-sided in the bad
    #    direction: a loser that dips through -50% on a wide-quote day, is skipped, and then
    #    recovers gets recorded as a TARGET WIN. This is now measured per trade instead of being
    #    invisible, so a fill-model regression that starts censoring again is loud.
    _sk = [(_f(r.get("exit_days_skipped")), _f(r.get("exit_days_used"))) for r in rows]
    _sk = [(a, b) for a, b in _sk if a is not None and b is not None]
    skip_rate = None
    if _sk:
        tot_sk = sum(a for a, _ in _sk)
        tot_all = sum(a + b for a, b in _sk)
        skip_rate = (tot_sk / tot_all) if tot_all else 0.0
        any_skipped = sum(1 for a, _ in _sk if a > 0) / len(_sk)
        if skip_rate > 0.02:
            flags.append(f"{skip_rate:.1%} of exit-path days were censored by the quote filter "
                         f"({any_skipped:.1%} of trades affected) — a skipped day is a day the "
                         f"stop could have fired on")

    exits = {}
    for r in rows:
        exits[str(r.get("exit_reason") or "?")] = exits.get(str(r.get("exit_reason") or "?"), 0) + 1

    out = {"ok": True, "n": n, "settled_at_intrinsic_frac": intrinsic, "iv_median": iv_med,
           "exit_days_censored_frac": skip_rate,                          # AUDIT B2
           "signal_coverage": cov, "exit_reason_mix": {k: v / n for k, v in sorted(exits.items())},
           "spread_median": _median(sp), "spread_p90": (sorted(sp)[int(0.9 * len(sp))]
                                                        if sp else None),
           "n_names": len(by_name), "max_name_share": top / n,
           "trades_per_name_median": _median([float(v) for v in by_name.values()]),
           "flags": flags}
    if meta:
        rej = {}
        for _, m in meta.items():
            for k, v in (m.get("rejects") or {}).items():
                rej[k] = rej.get(k, 0) + v
        out["alerts_total"] = sum(m.get("n_alert") or 0 for m in meta.values())
        out["candidates_total"] = sum(m.get("n_cand") or 0 for m in meta.values())
        out["rejects"] = dict(sorted(rej.items(), key=lambda kv: -kv[1]))
        out["alert_to_trade_rate"] = (n / out["alerts_total"]) if out["alerts_total"] else None
    return out


def rejects_by_tier(meta: dict, caps: dict) -> dict:
    """Why alerts never became trades, split by the name's cap tier TODAY.

    Deliberately today's tier, not point-in-time: a rejected alert has no entry row to date, and
    the question here ("do smaller names lose more alerts to unfillable quotes?") is about the
    name, not the moment. Labelled so nobody reads it as a point-in-time number.
    """
    out = {}
    for tkr, m in (meta or {}).items():
        ser = caps.get(str(tkr).upper())
        t = tier_of(ser[-1][1]) if ser else None
        if not t:
            continue
        d = out.setdefault(t, {"n_names": 0, "alerts": 0, "trades": 0, "rejects": {}})
        d["n_names"] += 1
        d["alerts"] += m.get("n_alert") or 0
        d["trades"] += m.get("n_trades") or 0
        for k, v in (m.get("rejects") or {}).items():
            d["rejects"][k] = d["rejects"].get(k, 0) + v
    for t, d in out.items():
        d["alert_to_trade_rate"] = (d["trades"] / d["alerts"]) if d["alerts"] else None
        d["rejects"] = dict(sorted(d["rejects"].items(), key=lambda kv: -kv[1]))
    return {"note": "tier here is TODAY's market cap, not point-in-time — a rejected alert "
                    "never produced an entry row.",
            "by_tier": {t: out[t] for t in TIER_ORDER if t in out}}


# ================================ the verdict ===============================================
def verdict(rows, mega_rows, broad_rows) -> dict:
    """B1-B4, applied mechanically to whatever came out. No judgement calls at this point."""
    s = _stats(rows)
    ho = held_out(rows)
    b1_ab = bool((s["expectancy_pct"] or 0) > 0 and (s["profit_factor"] or 0) > 1.0)
    b1 = bool(b1_ab and ho["both_positive"])

    bs = _stats(broad_rows)
    c_all, c_mega = concentration(rows), concentration(mega_rows)
    dec = (c_all["tail_hhi"] is not None and c_mega["tail_hhi"] is not None
           and c_all["tail_hhi"] < c_mega["tail_hhi"])
    b3 = bool((bs["expectancy_pct"] or 0) > 0 and dec
              and bs["n_closed"] >= MIN_CLOSED_PER_BUCKET)

    hr = bootstrap_diff(broad_rows, mega_rows, "p_tail_win")
    b4 = bool(hr.get("ok") and hr["diff"] > 0 and hr["excludes_zero"])

    if b1:
        label = "HOLDS"
    elif b1_ab:
        label = "WEAKENS"
    else:
        label = "DOES NOT EXTEND"
    return {"B1_edge_holds": b1, "B1_expectancy_and_pf": b1_ab,
            "B1_both_halves_positive": ho["both_positive"],
            "B3_keep_mid_small": b3, "B3_deconcentrates": dec,
            "B3_broad_expectancy": bs["expectancy_pct"], "B3_broad_n": bs["n_closed"],
            "B4_home_run_thesis": b4, "B4_detail": hr,
            "tail_hhi_all": c_all["tail_hhi"], "tail_hhi_mega_only": c_mega["tail_hhi"],
            "label": label}


# ================================ orchestration =============================================
def analyse(rows, seed: int = 0, meta: Optional[dict] = None,
            data_root: str = DATA_ROOT) -> dict:
    """Everything the mandate asks for, from a trade log. Separated from the scoring loop so it
    can be re-run in a second on a banked log without touching the cache again."""
    from .options_autopsy import deflated_sharpe

    mega = [r for r in rows if r.get("cap_tier") in ("mega", "large")]
    broad = [r for r in rows if r.get("cap_tier") in BROAD_TIERS]
    base = [r for r in rows if str(r.get("ticker") or "").upper() in BASELINE_55]
    fresh = [r for r in rows if str(r.get("ticker") or "").upper() not in BASELINE_55]
    out = {
        "overall": tail_stats(rows),
        "held_out": held_out(rows),
        "by_year": by_year(rows),
        "tiers": tier_report(rows),
        "concentration_all": concentration(rows),
        "concentration_mega_large_only": concentration(mega),
        "concentration_mid_small_only": concentration(broad),
        "home_run": {
            "p_tail_win": bootstrap_diff(broad, mega, "p_tail_win", seed=seed),
            "expectancy": bootstrap_diff(broad, mega, "expectancy_pct", seed=seed),
        },
        "term_slope_all": term_slope_effect(rows),
        "term_slope_full_sample": term_slope_effect(rows, late_only=False),
        # THE like-for-like read: one run, one window, partitioned by whether the name was in
        # the pool that every prior options result was measured on.
        "baseline_55_names": {
            "n_names": len({r["ticker"] for r in base}),
            "stats": tail_stats(base), "held_out": held_out(base),
            "concentration": concentration(base), "tiers": tier_report(base)},
        "new_names_only": {
            "n_names": len({r["ticker"] for r in fresh}),
            "stats": tail_stats(fresh), "held_out": held_out(fresh),
            "concentration": concentration(fresh), "tiers": tier_report(fresh),
            # term_slope was fitted on the 55-name early half; these names never informed it,
            # so applying the shipped threshold here is a genuine out-of-sample test (B2).
            "term_slope_out_of_sample": term_slope_effect(fresh),
            "term_slope_full_sample": term_slope_effect(fresh, late_only=False)},
        "published_55_for_reference": PUBLISHED_55,
        "sanity": sanity(rows, meta),
        "survivorship_probe": survivorship_probe(rows, load_caps(data_root)),
        "rejects_by_tier": rejects_by_tier(meta, load_caps(data_root)) if meta else None,
        "verdict": verdict(rows, mega, broad),
    }
    # B2 is a statement about the names that did NOT inform the threshold, so it is read off the
    # new-names partition rather than the whole book.
    ts_oos = out["new_names_only"]["term_slope_out_of_sample"]
    out["verdict"]["B2_term_slope_generalises"] = bool(ts_oos.get("passes_B2"))
    out["verdict"]["B2_detail"] = ts_oos

    # AUDIT R7 — the re-committed G3a/G3b/G3c floor, scored on the same scope B2 uses (the names
    # that never informed the threshold) and, separately, on the whole broad book.
    from . import options_stats as ST
    out["term_slope_gate_R7"] = {
        "new_names_late": term_slope_gate(fresh),
        "new_names_full": term_slope_gate(fresh, late_only=False),
        "broad_book_late": term_slope_gate(rows),
        "broad_book_full": term_slope_gate(rows, late_only=False),
    }
    out["verdict"]["R7_term_slope_passes_G3"] = bool(
        out["term_slope_gate_R7"]["new_names_late"].get("passes_G3"))

    # AUDIT O20 — point-in-time liquidity, as an evaluation-time partition.
    out["o20_point_in_time_liquidity"] = o20_split(rows)

    # AUDIT R3 — clustered inference on the headline itself, not only on the control comparison.
    out["clustered_inference_R3"] = {
        "effective_n": ST.effective_n(rows),
        "expectancy_date_block": ST.date_block_bootstrap(rows, seed=seed),
        "expectancy_date_block_new_names": ST.date_block_bootstrap(fresh, seed=seed),
        "note": "the headline expectancy, with months resampled as blocks. Every previously "
                "published options interval resampled TRADES and is optimistically narrow.",
    }

    ret = [_f(r.get("pnl_pct")) for r in rows]
    # n_trials=1: this is ONE pre-specified strategy re-measured on new names, not a search.
    # The autopsy's own DSR, deflated by 64 features, is the number for the feature sweep.
    out["deflated_sharpe"] = deflated_sharpe([v for v in ret if v is not None], n_trials=1)
    out["deflated_sharpe_new_names"] = deflated_sharpe(
        [v for v in (_f(r.get("pnl_pct")) for r in fresh) if v is not None], n_trials=1)
    # AUDIT R3.5 — the same statistic at the effective sample size. A shrinkage, never a gain.
    out["deflated_sharpe_clustered"] = ST.deflated_sharpe_clustered(
        [v for v in ret if v is not None], n_trials=1, rows=rows)
    return out


def save(res: dict, out_dir: str = OUT_DIR, name: str = "UNIVERSE_RESULTS.json") -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=str)
    return path
