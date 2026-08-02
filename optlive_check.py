"""Did the term_slope threshold transfer from synthetic IV to a real broker surface?

THE QUESTION. `TERM_SLOPE_THRESHOLD` = 0.0105 was fitted on IV solved from the MID by bisection
on ThetaData history. Live, Tradier serves its own smoothed surface. The threshold is about one
vol point - small enough that the estimator can decide the answer - so a constant fitted on one
series is not automatically valid on the other. Nothing offline can settle it; this can.

WHAT IT MEASURES, on the same 55 names the backtest ran:

  1. `slope_bs`      - ATM IV solved from the mid on the REAL chain, i.e. the fitted estimator
                       applied to live quotes. This is the apples-to-apples comparison.
  2. `slope_broker`  - ATM IV read from Tradier's published greeks. This is the cheap path the
                       whole-universe scan uses, and the one the gate actually consumed.

against the 1,540 backtested alert rows in `optbt_signals.pkl`, which carry `term_slope` at
100% coverage.

TWO LIMITS THAT ARE STATED RATHER THAN HIDDEN, because they bound what this can conclude:

  * ONE DAY VS TEN YEARS. The backtest distribution spans 2016-2025; this is a single snapshot.
    A shifted median could be a broken estimator or could be what the market looks like today.
    The distribution SHAPE and SCALE are the informative parts, not the exact centre.
  * ALERT DAYS VS ALL DAYS. The backtest rows are days a scream-buy actually fired - high
    momentum days. This samples every name unconditionally. Term structure on a breakout day
    need not match a random Tuesday, so a modest centre shift is expected even if the estimator
    transferred perfectly.

Run:  python optlive_check.py [--limit N]
"""
import sys
import os
import json
import time
import pickle
import datetime as dt
import statistics as st
import warnings

warnings.filterwarnings("ignore")
BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from valuation.config import CONFIG                                    # noqa: E402
from valuation.intraday.providers import TradierProvider, atm_iv_from_chain   # noqa: E402
from valuation.intraday import term_filter as TF                       # noqa: E402
from valuation.edge import options_live as L                           # noqa: E402

ROOT = r"C:\Users\donni\Downloads\valuation-tool"
OPTROOT = os.path.join(ROOT, "data", "options")
REF_PKL = os.path.join(OPTROOT, "optbt_signals.pkl")
OUT_JSON = os.path.join(OPTROOT, "LIVE_TERM_CHECK.json")

POOL = ["AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "BAC", "WFC", "C", "GS",
        "XOM", "CVX", "JNJ", "PFE", "MRK", "UNH", "WMT", "HD", "DIS", "NKE", "MCD", "KO", "PEP",
        "CSCO", "INTC", "ORCL", "IBM", "QCOM", "TXN", "AMD", "MU", "CAT", "BA", "GE", "F", "GM",
        "T", "VZ", "CMCSA", "NFLX", "CRM", "ADBE", "PYPL", "SBUX", "LOW", "TGT", "COST", "UPS",
        "MMM", "HON", "LMT", "RTX", "DE"]


def describe(vals, label):
    v = sorted(x for x in vals if x is not None and x == x)
    if not v:
        return {"label": label, "n": 0}
    q = st.quantiles(v, n=10) if len(v) >= 10 else []
    return {"label": label, "n": len(v),
            "median": round(st.median(v), 5),
            "mean": round(sum(v) / len(v), 5),
            "stdev": round(st.pstdev(v), 5) if len(v) > 1 else None,
            "p10": round(q[0], 5) if q else None,
            "p90": round(q[-1], 5) if q else None,
            "min": round(v[0], 5), "max": round(v[-1], 5),
            "pct_above_threshold": round(
                sum(1 for x in v if x >= TF.TERM_SLOPE_THRESHOLD) / len(v), 4)}


def spot_prices(prov, tickers):
    """One batched quote call rather than one per name."""
    out = {}
    for i in range(0, len(tickers), 25):
        chunk = tickers[i:i + 25]
        try:
            q = prov._get("markets/quotes", symbols=",".join(chunk))
            qq = ((q or {}).get("quotes") or {}).get("quote")
            if isinstance(qq, dict):
                qq = [qq]
            for r in qq or []:
                px = r.get("last") or r.get("close") or r.get("prevclose")
                if px:
                    out[r.get("symbol")] = float(px)
        except Exception as e:                                          # noqa: BLE001
            print(f"  quote fetch failed for {chunk[:3]}...: {e}", flush=True)
    return out


def by_expiry(rows):
    groups = {}
    for o in rows or []:
        e = str(o.get("expiration_date") or o.get("expiration"))[:10]
        groups.setdefault(e, []).append(o)
    return groups


def main():
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    names = POOL[:limit] if limit else POOL

    prov = TradierProvider(CONFIG)
    today = dt.date.today()
    print(f"live term-structure check | {today} ({today:%A}) | env={CONFIG.tradier_env} "
          f"| {len(names)} names", flush=True)
    if today.weekday() >= 5:
        print("  NOTE: market closed - these are the last close's quotes. Must be re-confirmed "
              "on a moving market.", flush=True)

    spots = spot_prices(prov, names)
    print(f"  spots resolved: {len(spots)}/{len(names)}", flush=True)

    per_name, failures = [], []
    for i, t in enumerate(names, 1):
        try:
            chain = prov.get_option_chain(t, L.DTE_RANGE)
        except Exception as e:                                          # noqa: BLE001
            chain = None
            failures.append({"ticker": t, "why": f"{type(e).__name__}: {e}"})
        if not chain:
            failures.append({"ticker": t, "why": "no chain"})
            print(f"  [{i}/{len(names)}] {t:6} no chain", flush=True)
            continue
        spot = spots.get(t)
        # as_of comes from the QUOTES, not the wall clock. On a stale feed the two differ and
        # the short-dated leg's solved IV is inflated by sqrt(T_true/T_assumed) - see
        # options_live.chain_as_of. Passing today here would manufacture the very failure this
        # script exists to test for.
        asof = L.resolve_as_of(chain)

        # (1) the FITTED estimator on the real chain
        bs = L.term_read(chain_rows=chain, underlying=spot)
        # (2) the broker's own surface, per expiry, the cheap scan path
        groups = by_expiry(chain)
        future = sorted(e for e in groups
                        if e and e > asof.isoformat())
        broker_slope = None
        if len(future) >= 2:
            front = future[0]
            far = min(future, key=lambda e: abs((dt.date.fromisoformat(e) - asof).days - 60))
            if far != front:
                f_iv = atm_iv_from_chain(groups[front], spot)
                m_iv = atm_iv_from_chain(groups[far], spot)
                if f_iv and m_iv:
                    broker_slope = m_iv - f_iv

        # (3) the whole live alert, on a real chain
        row = {"ticker": t, "score": 90, "labels": ["Uptrend"], "price": spot, "detail": {}}
        alert = L.build_alert(row, chain_rows=chain,
                              risk_budget=CONFIG.options_risk_per_trade)
        c = alert.get("contract") or {}
        per_name.append({
            "ticker": t, "spot": spot, "chain_rows": len(chain),
            "quote_date": asof.isoformat(), "front_dte": bs.get("front_dte"),
            "front_iv": bs.get("front_iv"), "far_iv": bs.get("far_iv"),
            "slope_bs": bs.get("term_slope"), "term_ok_bs": bs.get("term_ok"),
            "slope_broker": broker_slope,
            "term_ok_broker": (None if broker_slope is None
                               else broker_slope >= TF.TERM_SLOPE_THRESHOLD),
            "contract": ({"strike": c.get("strike"), "expiry": c.get("expiry"),
                          "dte": c.get("dte"), "delta": c.get("delta"),
                          "broker_delta": c.get("broker_delta"),
                          "delta_gap": c.get("delta_source_gap"),
                          "bid": c.get("bid"), "ask": c.get("ask"),
                          "entry_premium": c.get("entry_premium"), "iv": c.get("iv"),
                          "oi": c.get("open_interest")} if c else None),
            "confidence": (alert.get("confidence") or {}).get("level"),
            "sizing": {k: (alert.get("sizing") or {}).get(k)
                       for k in ("skip", "contracts", "dollar_risk", "reason")},
            "actionable": alert.get("actionable"),
        })
        print(f"  [{i}/{len(names)}] {t:6} bs={_f(bs.get('term_slope'))} "
              f"broker={_f(broker_slope)} contract={'y' if c else 'n'} "
              f"conf={(alert.get('confidence') or {}).get('level')}", flush=True)
        time.sleep(0.35)                       # stay well inside Tradier's rate limit

    # ---- reference: the backtested alert rows ------------------------------------------
    ref = []
    if os.path.exists(REF_PKL):
        with open(REF_PKL, "rb") as f:
            ref = [r.get("term_slope") for r in pickle.load(f)]

    out = {
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "market_open": today.weekday() < 5,
        "threshold": TF.TERM_SLOPE_THRESHOLD,
        "names_requested": len(names), "names_with_chain": len(per_name),
        "failures": failures,
        "distributions": {
            "backtest_alerts_2016_2025": describe(ref, "backtest (ThetaData, BS-from-mid)"),
            "live_bs_from_mid": describe([r["slope_bs"] for r in per_name],
                                         "live (real chain, BS-from-mid = fitted estimator)"),
            "live_broker_surface": describe([r["slope_broker"] for r in per_name],
                                            "live (Tradier published greeks)"),
        },
        "gate": {
            "backtest_retention": L.BACKTEST_TERM_RETENTION,
            "live_retention_bs": _ret([r["term_ok_bs"] for r in per_name]),
            "live_retention_broker": _ret([r["term_ok_broker"] for r in per_name]),
            "agreement_bs_vs_broker": _agree(per_name),
        },
        "per_name": per_name,
    }
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=str)

    print("\n=== term_slope: live vs backtest ===")
    for k, d in out["distributions"].items():
        if d["n"]:
            sd = "  n/a" if d["stdev"] is None else f"{d['stdev']:.4f}"
            p10 = "   n/a" if d["p10"] is None else f"{d['p10']:+.4f}"
            p90 = "   n/a" if d["p90"] is None else f"{d['p90']:+.4f}"
            print(f"  {d['label']:52} n={d['n']:5} median={d['median']:+.4f} "
                  f"mean={d['mean']:+.4f} sd={sd} p10={p10} p90={p90} "
                  f">=thr {d['pct_above_threshold']:.1%}")
    g = out["gate"]
    print(f"\n  backtest retention   {g['backtest_retention']:.1%}")
    print(f"  live retention (bs)  {g['live_retention_bs']}")
    print(f"  live retention (brk) {g['live_retention_broker']}")
    print(f"  bs vs broker agree   {g['agreement_bs_vs_broker']}")
    sized = [r for r in per_name if not r["sizing"]["skip"]]
    print(f"\n  contracts resolved   {sum(1 for r in per_name if r['contract'])}/{len(per_name)}")
    print(f"  sized (not skipped)  {len(sized)}/{len(per_name)}")
    print(f"  wrote {OUT_JSON}")


def _f(v):
    return "  none" if v is None else f"{v:+.4f}"


def _ret(flags):
    known = [f for f in flags if f is not None]
    if not known:
        return None
    return round(sum(1 for f in known if f) / len(known), 4)


def _agree(rows):
    both = [(r["term_ok_bs"], r["term_ok_broker"]) for r in rows
            if r["term_ok_bs"] is not None and r["term_ok_broker"] is not None]
    if not both:
        return None
    return {"n": len(both), "agree": round(sum(1 for a, b in both if a == b) / len(both), 4)}


if __name__ == "__main__":
    main()
