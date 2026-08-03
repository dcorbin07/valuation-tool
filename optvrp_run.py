"""A3 — generate the put-credit-spread (VRP) arm's trades on the cached ThetaData history.

Same shape as `optbt_run.py`: incremental, resumable, banks per name, so a stop at any point
still yields a usable verdict from the names that completed.

The STRATEGY lives in valuation/edge/options_vrp.py (ported from the options-bot); this file is
only the walk: which days are candidates, in what order, and where the result is banked.
"""
import sys, os, datetime as dt, json, warnings, time, pickle

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
_ENV = r"C:\Users\donni\Downloads\valuation-tool\.env"
if os.path.exists(_ENV):
    for line in open(_ENV, encoding="utf-8", errors="replace"):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import pandas as pd

from valuation.edge import blackscholes as BS
from valuation.edge import options_backtest as OB
from valuation.edge import options_vrp as V
from valuation.edge.theta_bulk import ThetaBulk

ROOT = r"C:\Users\donni\Downloads\valuation-tool"
OPTROOT = os.path.join(ROOT, "data", "options")
IV_SERIES = os.path.join(OPTROOT, "atm_iv_series.pkl")
# The PRE-REGISTERED SENSITIVITY, not a second headline. `options_vrp` commits to the bot's 10%
# short-leg bid-ask gate as the primary and to the project's own 25% quote-sanity bar as the one
# alternative worth measuring, so that "the tight gate starved the sample" is a number rather
# than a suspicion. Set VRP_BID_ASK_PCT to run it; it banks to its own file.
BID_ASK = float(os.environ.get("VRP_BID_ASK_PCT") or V.MAX_BID_ASK_PCT)
# Fill aggression. 1.0 (the default, and the ONLY headline) is the full touch on both legs both
# ways. `options_fill` already declares lower values a DIAGNOSTIC — "provided ONLY to show how
# much of a result is spread assumption; it is never the headline number" — and a credit spread
# is in practice worked as one net-credit limit order rather than two market orders, so how much
# fill quality the arm needs is a decision-relevant sensitivity. It is NOT a second verdict: a
# result that exists only at better-than-touch fills is reported as "does not survive the
# spread", exactly as the single-leg arm's mandate requires.
AGGRESSION = float(os.environ.get("VRP_AGGRESSION") or 1.0)
_TAG = "" if abs(BID_ASK - V.MAX_BID_ASK_PCT) < 1e-9 else "_ba%02d" % round(BID_ASK * 100)
if abs(AGGRESSION - 1.0) > 1e-9:
    _TAG += "_ag%02d" % round(AGGRESSION * 100)
OUT = os.path.join(OPTROOT, "optvrp_state%s.pkl" % _TAG)
LOCK = OUT + ".lock"
START, END = "2016-01-01", "2025-12-31"
YEARS = list(range(2016, 2026))
TODAY = dt.date.today()
REQUIRED_YEARS = [y for y in YEARS if y < TODAY.year]

# Same 55-name pool the single-leg arm ran on, so the two arms are comparable by construction.
POOL = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "BAC", "WFC", "C", "GS",
        "XOM", "CVX", "JNJ", "PFE", "MRK", "UNH", "WMT", "HD", "DIS", "NKE", "MCD", "KO", "PEP",
        "CSCO", "INTC", "ORCL", "IBM", "QCOM", "TXN", "AMD", "MU", "CAT", "BA", "GE", "F", "GM",
        "T", "VZ", "CMCSA", "NFLX", "CRM", "ADBE", "PYPL", "SBUX", "LOW", "TGT", "COST", "UPS",
        "MMM", "HON", "LMT", "RTX", "DE"]

# Moneyness band the 20-delta put lives in. Solving IV across the whole ladder to find it was
# the dominant cost of the single-leg run; a 20-delta 35-DTE put on these names sits roughly
# 3-15% out of the money, and the band is wide enough to hold it in every vol regime here.
MNY_LO, MNY_HI = 0.70, 1.02

if os.path.exists(LOCK):
    try:
        _pid = int(open(LOCK).read().strip())
        import subprocess
        _alive = str(_pid) in subprocess.run(["tasklist", "/FI", "PID eq %d" % _pid],
                                             capture_output=True, text=True).stdout
    except Exception:
        _alive = False
    if _alive:
        raise SystemExit("another VRP run is active (pid %d)" % _pid)
os.makedirs(os.path.dirname(LOCK), exist_ok=True)
open(LOCK, "w").write(str(os.getpid()))

prov = ThetaBulk(root=OPTROOT)
print("status:", prov.status(), flush=True)

# ---- ATM IV series (A2) — the real IV-rank input -------------------------------------------
if not os.path.exists(IV_SERIES):
    raise SystemExit("missing %s — A2's daily ATM-IV series is required for the IV-rank filter"
                     % IV_SERIES)
with open(IV_SERIES, "rb") as f:
    IVS = pickle.load(f)
print(f"atm_iv_series: {len(IVS)} names", flush=True)

# ---- earnings (Sharadar EVENTS code 22; PARTIAL coverage, see options_vrp header) -----------
try:
    from valuation.edge import bulk as BULK
    EVENTS = BULK.prepare_events(os.path.join(ROOT, "data", "bulk", "events.csv"),
                                 cache_dir=os.path.join(ROOT, "data", "bulk", "prepared"))
except Exception as e:                                                   # noqa: BLE001
    print(f"events unavailable ({type(e).__name__}) — earnings filter INERT", flush=True)
    EVENTS = {}

# ---- bars (as-traded closes for option maths) ----------------------------------------------
bars_by, liq = {}, []
for t in POOL:
    b = OB.load_bars(t)
    if not b:
        continue
    bars_by[t] = b
    dv = [b["close"][i] * b["volume"][i] for i, d in enumerate(b["date"])
          if "2015-01-01" <= d < "2016-01-01"]
    if len(dv) > 100:
        liq.append((t, sum(dv) / len(dv)))
liq.sort(key=lambda x: -x[1])
UNI = [t for t, _ in liq if t in IVS]
print(f"universe {len(UNI)} names with bars + IV series", flush=True)

state = {"trades": [], "mirror": [], "done": [], "funnel": {}, "gaps": {},
         "config": {"width": V.SPREAD_WIDTH, "delta": V.TARGET_SHORT_DELTA,
                    "dte": [V.MIN_DTE, V.MAX_DTE], "iv_rank_min": V.IV_RANK_MIN,
                    "bid_ask_pct": BID_ASK, "aggression": AGGRESSION,
                    "is_headline": (abs(BID_ASK - V.MAX_BID_ASK_PCT) < 1e-9
                                    and abs(AGGRESSION - 1.0) < 1e-9)}}
if os.path.exists(OUT):
    try:
        with open(OUT, "rb") as f:
            prev = pickle.load(f)
        if isinstance(prev, dict) and "done" in prev:
            state = prev
            print(f"resumed: {len(state['done'])} names, {len(state['trades'])} trades",
                  flush=True)
    except Exception:
        pass


def bank():
    tmp = OUT + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(state, f, protocol=5)
    os.replace(tmp, OUT)


def note(key):
    state["funnel"][key] = state["funnel"].get(key, 0) + 1


def covered_years_for(t):
    from valuation.edge.theta_bulk import year_path
    ys = set(prov.cached_years(t))
    for y in YEARS:
        if os.path.exists(year_path(t, y, OPTROOT) + ".empty"):
            ys.add(y)
    return ys


def price_index(bars):
    """date -> as-traded close, plus a sorted date list for as-of lookups."""
    px = bars.get("raw_close") or bars["close"]
    return {d: px[i] for i, d in enumerate(bars["date"])}, list(bars["date"])


def settle_price(px_by, dates, expiry):
    """Last as-traded close on or before expiration (the ladder is never split-adjusted)."""
    iso = expiry.isoformat()
    best = None
    for d in dates:
        if d <= iso:
            best = d
        else:
            break
    return px_by.get(best) if best else None


def hist_by_day(t, expiry, strike, entry_date):
    """{date: row-dict} for one contract's life. One slice per leg per trade, not per day."""
    h = prov.contract_history(t, expiry, strike, "P", entry_date, expiry)
    if h is None or len(h) == 0:
        return {}
    return {r["date"]: {"bid": r["bid"], "ask": r["ask"],
                        "volume": r["volume"], "open_interest": r["open_interest"]}
            for _, r in h.iterrows()}


def run_name(t):
    bars = bars_by[t]
    px_by, dates = price_index(bars)
    covered = covered_years_for(t)
    ivs = IVS.get(t) or {}
    iv_index = V.build_iv_index(ivs)
    iv_pos = {d: i for i, (d, _) in enumerate(iv_index)}
    earn = set()
    if EVENTS:
        from valuation.edge.bulk import earnings_dates
        earn = set(earnings_dates(EVENTS, t))
    out, mirrors = [], []
    open_until = None

    frames = {}
    for y in YEARS:
        f = prov._year_frame(t, y)
        if f is None or len(f) == 0:
            continue
        p = f[f["right"].astype(str).str[0] == "P"]
        if len(p):
            frames[y] = dict(tuple(p.groupby("date")))

    for d in bars["date"]:
        if not (START <= d <= END):
            continue
        if open_until and d <= open_until:
            continue
        day = dt.date.fromisoformat(d)
        by_date = frames.get(day.year)
        if not by_date or day not in by_date:
            continue
        note("candidate_days")

        # 1. IV rank — the entry filter. Unknown is SKIPPED, never defaulted.
        i = iv_pos.get(d)
        rank = V.iv_rank_at(iv_index, i) if i is not None else None
        if rank is None:
            note("no_iv_rank")
            continue
        if rank < V.IV_RANK_MIN:
            note("iv_rank_below_min")
            continue
        atm_iv = ivs.get(d)

        chain = by_date[day]
        exps = sorted({e for e in chain["expiration"] if e > day})
        exp = V.pick_expiration(exps, day)
        if exp is None:
            note("no_expiration_in_window")
            continue

        # 2. Earnings between entry and expiration (partial coverage — a miss is UNKNOWN).
        if earn and any(day.isoformat() < e <= exp.isoformat() for e in earn):
            note("earnings_in_window")
            continue

        und = px_by.get(d)
        if not und or und <= 0:
            note("no_underlying")
            continue
        leg = chain[chain["expiration"] == exp]
        if len(leg) == 0:
            note("empty_expiry")
            continue
        mny = leg["strike"].astype(float) / float(und)
        near = leg[(mny >= MNY_LO) & (mny <= MNY_HI)]
        if len(near) == 0:
            note("no_strikes_in_band")
            continue
        enr = BS.enrich_chain(near, und, day)
        short_row, why = V.find_short_put(enr, max_bid_ask_pct=BID_ASK)
        if short_row is None:
            note(why or "no_short_leg")
            continue
        short_k = float(short_row["strike"])
        wing = V.find_wing(leg, short_k - V.SPREAD_WIDTH)
        if wing is None:
            note("no_wing_strike")
            continue
        long_k = float(wing["strike"])
        width = short_k - long_k
        if width <= 0:
            note("bad_width")
            continue
        credit = V.entry_credit(short_row, wing, aggression=AGGRESSION)
        if credit is None:
            note("wing_unquotable")
            continue
        if credit < V.MIN_CREDIT:
            note("credit_below_floor")
            continue
        if credit >= width:
            note("credit_exceeds_width")
            continue

        sh = hist_by_day(t, exp, short_k, day)
        lh = hist_by_day(t, exp, long_k, day)
        if not sh or not lh:
            note("no_leg_history")
            continue
        settle = settle_price(px_by, dates, exp)
        if exp.year not in covered:
            # A spread expiring in an uncovered year would bypass the quote-based exit
            # discipline entirely and settle at intrinsic — a silent change of strategy for
            # those trades. Skip rather than score one the data cannot support.
            note("expiry_year_uncovered")
            continue
        tr = V.simulate_spread(sh, lh, day, exp, short_k, long_k, credit, settle,
                               aggression=AGGRESSION)
        if not tr or not tr.get("ok"):
            note((tr or {}).get("reason", "sim_failed"))
            continue
        s_mid = (float(short_row["bid"]) + float(short_row["ask"])) / 2.0
        l_mid = (float(wing["bid"]) + float(wing["ask"])) / 2.0
        tr.update({
            "ticker": t, "short_strike": short_k, "long_strike": long_k,
            "short_delta": float(short_row["delta"]) if short_row.get("delta") is not None
            else None,
            "short_oi": int(short_row["open_interest"]),
            "dte": (exp - day).days, "expiry": exp.isoformat(),
            "iv_rank": rank, "atm_iv": atm_iv, "underlying": float(und),
            "mid_credit_ps": s_mid - l_mid,
            "earnings_known": bool(earn),
            "opt_right": "put", "strike": short_k, "score": None, "horizon": "vrp",
        })
        out.append(tr)
        note("trades")
        mir = V.simulate_mirror(sh, lh, day, exp, short_k, long_k, settle,
                                aggression=AGGRESSION)
        if mir:
            mir["ticker"] = t
            mirrors.append(mir)
        open_until = tr["exit_date"]
    return out, mirrors


t_all = time.time()
for i, t in enumerate(UNI, 1):
    if t in state["done"]:
        continue
    t0 = time.time()
    cov = prov.coverage_report([t], REQUIRED_YEARS)
    if cov["gaps"]:
        state["gaps"][t] = cov["gaps"][t]
        state["done"].append(t)
        print(f"[{i}/{len(UNI)}] {t}: SKIPPED, missing years {cov['gaps'][t]}", flush=True)
        bank()
        continue
    tr, mir = run_name(t)
    state["trades"].extend(tr)
    state["mirror"].extend(mir)
    state["done"].append(t)
    bank()
    n = len(state["done"])
    print(f"[{i}/{len(UNI)}] {t}: trades={len(tr)} mirror={len(mir)} "
          f"| {time.time()-t0:.0f}s | total {len(state['trades'])} "
          f"| {(time.time()-t_all)/60/max(n,1):.2f} min/name", flush=True)
    if state["trades"] and n % 5 == 0:
        from valuation.edge.options_tracker import _stats
        o = _stats(state["trades"])
        print(f"    running: n={o['n_closed']} hit={o['hit_rate']} "
              f"exp={o['expectancy_pct']} pf={o['profit_factor']}", flush=True)

print(f"\nDONE names={len(state['done'])} trades={len(state['trades'])} "
      f"gaps={len(state['gaps'])}", flush=True)
print("funnel:", json.dumps(state["funnel"], indent=1), flush=True)
try:
    os.remove(LOCK)
except OSError:
    pass
