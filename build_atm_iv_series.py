"""A2: daily ATM-IV series per name across ALL trading days, from the cached ThetaData.

iv_rank asks "is vol rich or cheap FOR THIS NAME", which needs a trailing distribution. Phase 3b
computed IV only on alert days (~28 per name), so the 60-observation minimum was never met and
coverage was 0% - the signal was untestable, not rejected. This builds the full series once and
caches it, after which iv_rank is a lookup.
"""
import sys, os, pickle, datetime as dt, warnings, time
warnings.filterwarnings("ignore")
sys.path.insert(0, r"C:\Users\donni\Downloads\valuation-tool\.claude\worktrees\p5-coverage-and-derived-inputs")
for line in open(r"C:\Users\donni\Downloads\valuation-tool\.env", encoding="utf-8", errors="replace"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())

import pandas as pd
from valuation.edge import options_backtest as OB, blackscholes as BS
from valuation.edge.theta_bulk import ThetaBulk

OPTROOT = r"C:\Users\donni\Downloads\valuation-tool\data\options"
OUT = os.path.join(OPTROOT, "atm_iv_series.pkl")
prov = ThetaBulk(root=OPTROOT)

state = pickle.load(open(OUT, "rb")) if os.path.exists(OUT) else {}
names = sorted({d for d in os.listdir(OPTROOT) if os.path.isdir(os.path.join(OPTROOT, d))})
print(f"names with cached chains: {len(names)}", flush=True)

t0 = time.time()
for ni, tk in enumerate(names, 1):
    if tk in state:
        continue
    bars = OB.load_bars(tk)
    if not bars:
        state[tk] = {}
        continue
    years = prov.cached_years(tk)
    series = {}
    for yr in years:
        df = prov._year_frame(tk, yr)
        if df is None or len(df) == 0:
            continue
        # index the year once, then walk its trading days
        for day, chunk in df.groupby("date"):
            try:
                i = bars["date"].index(day.isoformat())
            except ValueError:
                continue
            und = bars["raw_close"][i]
            if not und or und <= 0:
                continue
            exps = sorted({e for e in chunk["expiration"] if e > day})
            if not exps:
                continue
            # the ~60-DTE expiry: the band we actually trade, and best-conditioned for IV
            target = min(exps, key=lambda e: abs((e - day).days - 60))
            sub = chunk[(chunk["expiration"] == target)
                        & (chunk["right"].astype(str).str[0] == "C")].copy()
            if len(sub) == 0:
                continue
            sub["_d"] = (sub["strike"].astype(float) - und).abs()
            r_free = BS.risk_free_rate(day)
            T = (target - day).days / 365.0
            iv = None
            for _, row in sub.sort_values("_d").head(4).iterrows():
                try:
                    mid = (float(row["bid"]) + float(row["ask"])) / 2.0
                except (TypeError, ValueError):
                    continue
                v = BS.implied_vol(mid, und, float(row["strike"]), T, r_free, "C")
                if v:
                    iv = float(v)
                    break
            if iv:
                series[day.isoformat()] = iv
    state[tk] = series
    print(f"[{ni}/{len(names)}] {tk}: {len(series)} daily IVs  ({time.time()-t0:.0f}s)", flush=True)
    with open(OUT + ".tmp", "wb") as f:
        pickle.dump(state, f, protocol=5)
    os.replace(OUT + ".tmp", OUT)

tot = sum(len(v) for v in state.values())
print(f"\nDONE {len(state)} names, {tot:,} daily ATM-IV observations", flush=True)
per = [len(v) for v in state.values() if v]
if per:
    print(f"per name: min {min(per)}  median {sorted(per)[len(per)//2]}  max {max(per)}", flush=True)
