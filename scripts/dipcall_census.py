"""DIP-CALL feasibility census. ZERO TRIALS, and NO FORWARD RETURN IS TOUCHED.

It counts how many volatility-relative drop events exist on the build quadrant's tier, and -- the
number that actually decides the program's power -- HOW CLUSTERED they are in time. A market-wide
drop creates thousands of simultaneous events that share one shock, so the raw count overstates
the independent evidence. `SELRULE` measured exactly this shape: 16 co-moving countries were worth
2-4 independent draws, and quoting 16 would have understated the true alpha 7.5-fold.

A census is a fact about what data exists (the `S25`/`MB15`/`MB3` class) and under `MB1-SEL` can
only ever BLOCK a design, never produce a finding. **No forward return is read anywhere in this
file**: the event-day return is used to DEFINE the event and nothing after the event day is loaded.
"""
import glob
import io
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def _data_root():
    """The PRIMARY populated data root, never the worktree's empty one (`E-5`)."""
    d = REPO
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "data", "free_analysis")):
            return os.path.join(d, "data")
        nxt = os.path.dirname(d)
        if nxt == d:
            break
        d = nxt
    raise SystemExit("REFUSING: no populated data root found")


DATA = _data_root()
PRICES = os.path.join(DATA, "full2009", "backtest", "prices")
PANEL = os.path.join(DATA, "free_analysis", "UNIVERSE_BIAS_PANEL_full.pkl")
OUT = os.path.join(DATA, "free_analysis", "DIPCALL_CENSUS.json")

LO, HI = "2009-01-01", "2019-12-31"      # the BUILD quadrant's years
VOL_WIN = 60                              # trailing sessions for the volatility scale
MIN_VOL_OBS = 40
KS = (2.0, 2.5, 3.0)
TIER = 10e9


def stable_key_half(t):
    import hashlib
    return int(hashlib.sha1(str(t).encode()).hexdigest(), 16) % 2


def tier_names():
    """Names in the $10B tier on at least one build-quadrant date, ticker half 0."""
    d = pd.read_pickle(PANEL)
    d = d[["date", "ticker", "market_cap"]].copy()
    d["yr"] = d["date"].astype(str).str.slice(0, 4).astype(int)
    d = d[(d["yr"] >= 2009) & (d["yr"] <= 2019)]
    d = d[d["ticker"].map(stable_key_half) == 0]
    cap = pd.to_numeric(d["market_cap"], errors="coerce")
    tier = d[cap >= TIER]
    return sorted(set(tier["ticker"].astype(str))), sorted(set(d["ticker"].astype(str)))


def main():
    tier, half = tier_names()
    print("build-quadrant half-0 names: %d ; ever in the $10B tier: %d" % (len(half), len(tier)))

    rows, per_name = [], 0
    for i, t in enumerate(tier):
        p = os.path.join(PRICES, "%s.csv" % t)
        if not os.path.isfile(p):
            continue
        s = pd.read_csv(p)
        s["date"] = s["date"].astype(str)
        s = s[(s["date"] >= LO) & (s["date"] <= HI)].sort_values("date")
        if len(s) < VOL_WIN + 10:
            continue
        c = pd.to_numeric(s["close"], errors="coerce")
        r = c.pct_change()
        # Trailing volatility, STRICTLY prior: shift(1) so the event day is not in its own scale.
        vol = r.rolling(VOL_WIN, min_periods=MIN_VOL_OBS).std().shift(1)
        z = r / vol
        ok = z.notna() & vol.gt(0)
        per_name += int(ok.sum())
        ev = pd.DataFrame({"date": s["date"].values, "z": z.values, "ok": ok.values})
        ev = ev[ev["ok"]]
        ev["ticker"] = t
        rows.append(ev[["date", "ticker", "z"]])
        if i and i % 150 == 0:
            print("  %d/%d names, %s scoreable name-days so far"
                  % (i, len(tier), "{:,}".format(per_name)))

    if not rows:
        raise SystemExit("REFUSING: no price files matched the tier")
    ev = pd.concat(rows, ignore_index=True)
    art = {"item": "DIP-CALL feasibility census", "trials": 0,
           "forward_return_touched": False,
           "build_quadrant": [LO, HI], "vol_window": VOL_WIN,
           "names_half0": len(half), "names_ever_tier": len(tier),
           "names_with_prices": int(ev["ticker"].nunique()),
           "scoreable_name_days": int(len(ev)),
           "sessions": int(ev["date"].nunique()), "by_k": {}}
    print("\nscoreable name-days %s over %d sessions, %d names"
          % ("{:,}".format(len(ev)), ev["date"].nunique(), ev["ticker"].nunique()))

    print("\n%-6s %10s %8s %10s %10s %10s" %
          ("k", "events", "rate", "top1day%", "top10day%", "eff-n est"))
    for k in KS:
        e = ev[ev["z"] <= -k]
        n = len(e)
        if not n:
            continue
        by_day = e.groupby("date").size().sort_values(ascending=False)
        top1 = float(by_day.iloc[0]) / n
        top10 = float(by_day.iloc[:10].sum()) / n
        # A deliberately crude effective-n: treat each event DAY as one cluster and apply the
        # standard design-effect haircut n_eff = n / (1 + (m_bar - 1) * rho) at rho = 1, i.e.
        # events on the same day share their shock entirely. That is the PESSIMISTIC end and is
        # reported as a BRACKET with the raw count, never as the number.
        m_bar = n / len(by_day)
        eff_full = len(by_day)                      # rho = 1
        art["by_k"]["%.1f" % k] = {
            "events": n,
            "event_rate_per_name_day": round(n / len(ev), 6),
            "distinct_event_days": int(len(by_day)),
            "mean_events_per_event_day": round(m_bar, 3),
            "share_on_worst_single_day": round(top1, 4),
            "share_on_worst_10_days": round(top10, 4),
            "eff_n_rho1_lower_bracket": int(eff_full),
            "eff_n_raw_upper_bracket": n,
        }
        print("%-6.1f %10s %8.4f %10.4f %10.4f %10s" %
              (k, "{:,}".format(n), n / len(ev), top1, top10, "{:,}".format(eff_full)))

    with io.open(OUT, "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
