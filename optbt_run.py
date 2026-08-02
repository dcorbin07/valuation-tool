"""Full-universe scream-buy backtest: incremental, resumable, banks results per name.

Structured so a stop at ANY point still yields a usable verdict from completed names, rather
than the all-or-nothing prefetch-then-compute shape that lost everything when killed.
"""
import sys, os, datetime as dt, json, warnings, time, pickle
warnings.filterwarnings("ignore")
BASE = r"C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs"
sys.path.insert(0, BASE)
for line in open(r"C:\Users\donni\Downloads\valuation-tool\.env", encoding="utf-8", errors="replace"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

from valuation.edge import options_backtest as OB
from valuation.edge.theta_bulk import ThetaBulk
from valuation.intraday.technical import technical_signals
from valuation.intraday.signals import evaluate
from valuation.saas.notify import _BULL

OPTROOT = r"C:\Users\donni\Downloads\valuation-tool\data\options"
OUT = r"C:\Users\donni\.claude\jobs\7819c8eb\tmp\optbt_trades.pkl"
# 2026 IS EXCLUDED ENTIRELY, not merely un-required. It failed on every single name and every
# retry (while 2016-2025 fetched cleanly for all of them), so requesting it only burned ~90s
# per name in futile retries. Ten complete years is the sample; the year in progress is not
# part of it. The per-trade expiry guard below then naturally drops late-2025 alerts whose
# contract would expire in the uncovered year, rather than settling them at intrinsic.
START, END = "2016-01-01", "2025-12-31"
YEARS = list(range(2016, 2026))

# ONLY PAST YEARS ARE REQUIRED. 2026 is the year in progress, and requiring it excluded every
# single name (5/5 skipped, 0 scored) even though 2016-2025 - ten complete years - fetched
# cleanly for all of them. The current year is fetched best-effort and used if present.
TODAY = dt.date.today()
REQUIRED_YEARS = [y for y in YEARS if y < TODAY.year]

POOL = ["AAPL","MSFT","AMZN","GOOGL","META","NVDA","TSLA","JPM","BAC","WFC","C","GS","XOM",
        "CVX","JNJ","PFE","MRK","UNH","WMT","HD","DIS","NKE","MCD","KO","PEP","CSCO","INTC",
        "ORCL","IBM","QCOM","TXN","AMD","MU","CAT","BA","GE","F","GM","T","VZ","CMCSA","NFLX",
        "CRM","ADBE","PYPL","SBUX","LOW","TGT","COST","UPS","MMM","HON","LMT","RTX","DE"]

prov = ThetaBulk(root=OPTROOT)
print("status:", prov.status(), flush=True)

# ---- universe ordered by 2015 liquidity (PIT: not chosen on later performance) -------------
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
UNI = [t for t, _ in liq]
print(f"universe {len(UNI)} names, most liquid first: {UNI[:10]}...", flush=True)

# ---- resume any previous partial result ----------------------------------------------------
state = {"trades": [], "done": [], "cand": 0, "alerts": 0, "rejects": {}, "gaps": {}}
if os.path.exists(OUT):
    try:
        with open(OUT, "rb") as f:
            prev = pickle.load(f)
        if isinstance(prev, dict) and "done" in prev:
            state = prev
            print(f"resumed: {len(state['done'])} names, {len(state['trades'])} trades", flush=True)
    except Exception:
        pass


def bank():
    tmp = OUT + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(state, f, protocol=5)
    os.replace(tmp, OUT)


def covered_years_for(t):
    """Years actually on disk for this name (a .empty year counts: the feed has nothing)."""
    import os as _os
    from valuation.edge.theta_bulk import year_path
    ys = set(prov.cached_years(t))
    for y in YEARS:
        if _os.path.exists(year_path(t, y, OPTROOT) + ".empty"):
            ys.add(y)
    return ys


def run_name(t):
    b = bars_by[t]
    covered = covered_years_for(t)
    n_c = n_a = 0
    out = []
    open_until = None            # one position per name at a time, as a live book would hold
    for d in b["date"]:
        if not (START <= d <= END):
            continue
        if open_until and d <= open_until:
            continue
        w = OB.bars_asof(b, d)
        if not w:
            continue
        ts = technical_signals(w).get("score")
        if ts is None or ts < OB.PREFILTER_TECH:
            continue
        n_c += 1
        day = dt.date.fromisoformat(d)
        chain = prov.chain_on(t, day)
        if chain is None or len(chain) == 0:
            continue
        und = w["close"][-1]
        summ = OB.chain_summary(chain, und, day)
        ev = evaluate(w, summ, horizon=OB.HORIZON)
        sc, labels = ev.get("score"), ev.get("labels") or []
        if sc is None or sc < OB.ALERT_MIN_SCORE:
            continue
        if not any(any(bl in l for bl in _BULL) for l in labels):
            continue
        n_a += 1
        row = OB.pick_contract(chain, und, day, right="C")
        # An alert whose contract EXPIRES in an uncovered year would bypass the quote-based
        # exit discipline and settle at intrinsic instead - a silent change of strategy for
        # those trades. Skip it rather than score a trade the data cannot support.
        if row is not None:
            import pandas as _pd
            _exp_year = _pd.Timestamp(row["expiration"]).year
            if _exp_year not in covered:
                state["rejects"]["expiry_year_uncovered"] = \
                    state["rejects"].get("expiry_year_uncovered", 0) + 1
                continue
        if row is None:
            state["rejects"]["no_contract_in_band"] = state["rejects"].get("no_contract_in_band", 0) + 1
            continue
        tr = OB.simulate_trade(prov, t, row, day, b)
        if not tr or not tr.get("ok"):
            r = (tr or {}).get("reason", "sim_failed")
            state["rejects"][r] = state["rejects"].get(r, 0) + 1
            continue
        out.append(OB.to_alert_row(t, day, row, tr, sc, labels, (summ or {}).get("atm_iv"), None))
        open_until = tr.get("exit_date")
    return out, n_c, n_a


t_all = time.time()
for i, t in enumerate(UNI, 1):
    if t in state["done"]:
        continue
    t0 = time.time()
    prov.prefetch([t], YEARS)                    # 4 concurrent across this name's years
    cov = prov.coverage_report([t], REQUIRED_YEARS)
    if cov["gaps"]:
        # Do NOT score a name with an incomplete history - that is under-sampling dressed up
        # as a smaller sample. Record it and move on.
        state["gaps"][t] = cov["gaps"][t]
        print(f"[{i}/{len(UNI)}] {t}: SKIPPED, missing years {cov['gaps'][t]}", flush=True)
        state["done"].append(t)
        bank()
        continue
    pull_s = time.time() - t0
    tr, n_c, n_a = run_name(t)
    state["trades"].extend(tr)
    state["cand"] += n_c
    state["alerts"] += n_a
    state["done"].append(t)
    bank()
    done_n = len(state["done"])
    print(f"[{i}/{len(UNI)}] {t}: cand={n_c} alerts={n_a} trades={len(tr)} "
          f"| pull {pull_s/60:.1f}m compute {(time.time()-t0-pull_s):.0f}s "
          f"| total {len(state['trades'])} trades, {(time.time()-t_all)/60/done_n:.1f} min/name",
          flush=True)
    if state["trades"] and done_n % 5 == 0:
        o = OB.expectancy_report(state["trades"])["overall"]
        print(f"    running: n={o['n_closed']} hit={o['hit_rate']} "
              f"exp={o['expectancy_pct']} pf={o['profit_factor']}", flush=True)

print(f"\nDONE names={len(state['done'])} trades={len(state['trades'])} "
      f"gaps={len(state['gaps'])} rejects={state['rejects']}", flush=True)
if state["trades"]:
    rep = OB.expectancy_report(state["trades"])
    print(json.dumps(rep, indent=1, default=str)[:3000], flush=True)
