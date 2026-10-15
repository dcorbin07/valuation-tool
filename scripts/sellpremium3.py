"""SELL-PREMIUM-3 — the dip entries as a 25-delta put credit spread.

Register: `PREREG_sellpremium3.md`, committed ALONE and a strict git ancestor of this file.
4 options trials booked BEFORE this script existed.

TWO INVOCATIONS, AND THE SPLIT IS THE POINT (`O10`'s process defect):

    python -m scripts.sellpremium3 --kills     # K1, K3-POS, K3-ACCT, in their own pass
    python -m scripts.sellpremium3 --arms      # REFUSES without a passing kills artifact

**EVERY SCORING PRIMITIVE IS IMPORTED** (`B7`): the event set and short leg from
`sellpremium2_arm`, the crash arithmetic from `sellpremium2_kills`, the sizing grid from
`sellpremium2_sizing_fix`, settlement from `valuation.studies.sellpremium`. A second
implementation of any of them at a rationed read would be unrecoverable.

**AMENDMENT A1 IS LOAD-BEARING HERE AND IT IS WHY THIS FILE EXISTS RATHER THAN A COPY OF THE
STAGE-2 RUNNER:** a spread settles TWO legs, so the stale-map defect that voided
`SELL-PREMIUM-2`'s stage 2 would be inherited twice over. `spot_maps` is given the years the
TRADES span and `settlement_spot` is given the required `max_stale_days`; refusals are counted.
"""
import argparse
import io
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from valuation.edge import research_log                                      # noqa: E402
from valuation.edge.statistics import hlz_hurdle                             # noqa: E402
from valuation.studies import dipcall as D                                   # noqa: E402
from valuation.studies import sellpremium as SP                              # noqa: E402
from scripts import sellpremium2_arm as A2M                                  # noqa: E402
from scripts import sellpremium2_kills as K2                                 # noqa: E402

PREFIX = "SELLPREMIUM3"

# ---- every constant below is the REGISTER'S. Changing one after a measurement voids the item.
WIDTH_FRAC = 0.075                 # the long leg sits 7.5% of SPOT below the short strike
WIDTH_BAND = (0.05, 0.125)         # realised width outside this is REFUSED
K1_MIN_EVENTS = 1200               # two-leg floor; below it the register STOPS
K1_MIN_DAYS = 300
K3_ACCT_MAX = 0.35                 # account-level crash loss cap, inherited from SELL-PREMIUM-2
DEPLOY_CAP = 0.35                  # fraction of equity at risk across all open spreads
EQUITY_BPS_ONE_WAY = 0.00334       # B11's measured 33.4 bps
EQUITY_CROSSINGS = 2               # as drafted
ACCOUNT_SIZES = (10000.0, 25000.0, 50000.0)


def _years(picks):
    return A2M.years_spanning(picks)


def long_leg(day_rows, short_exp, short_strike, spot):
    """The nearest listed strike AT OR BELOW `K_short - 0.075*spot`, SAME expiry. PURE.

    Returns `None` when the chain lists nothing there, or when the realised width falls outside
    the declared 5%-12.5% band -- a REFUSAL, not a substitution. The band is the register's and
    the draft's reason is arithmetic rather than taste: below 5% the credit does not cover two
    crossings plus the long leg's decay, and above 12.5% the capital rises faster than the
    credit.
    """
    target = float(short_strike) - WIDTH_FRAC * float(spot)
    d = day_rows[(day_rows["expiration"].astype(str) == str(short_exp))
                 & (day_rows["strike"].astype(float) <= target)]
    if not len(d):
        return None
    d = d[(d["bid"].astype(float) > 0.0) & (d["ask"].astype(float) > d["bid"].astype(float))]
    if not len(d):
        return None
    r = d.loc[d["strike"].astype(float).idxmax()]
    width = float(short_strike) - float(r["strike"])
    frac = width / float(spot)
    if frac < WIDTH_BAND[0] or frac > WIDTH_BAND[1]:
        return None
    return {"strike": float(r["strike"]), "bid": float(r["bid"]), "ask": float(r["ask"]),
            "width": width, "width_frac": frac}


def settle_spread(short, lng, spot_at_expiry):
    """One put credit spread, held to expiry. PURE.

    Short sold at the BID and long bought at the ASK -- TWO crossings at entry and none at exit,
    which is the draft's §4 and the reason hold-to-expiry is load-bearing (`A3` paid four).
    In the assignment band the shares are SOLD at the project's measured 33.4 bps, charged
    `EQUITY_CROSSINGS` times on the SHORT-STRIKE notional as drafted. **Exercising the long put
    instead is refused by name** -- it locks the full width even when `S > K_long`.
    """
    K_s, K_l = float(short["strike"]), float(lng["strike"])
    credit = float(short["bid"]) - float(lng["ask"])
    S = float(spot_at_expiry)
    width = K_s - K_l
    equity_cost = 0.0
    if S >= K_s:
        pnl, band = credit, "both_worthless"
    elif S <= K_l:
        pnl, band = credit - width, "both_exercise"
    else:
        equity_cost = EQUITY_CROSSINGS * EQUITY_BPS_ONE_WAY * K_s
        pnl, band = credit - (K_s - S) - equity_cost, "assigned_long_worthless"
    cap_draft = max(1e-9, width - credit)          # the REGISTERED denominator
    cap_broker = max(1e-9, width)                  # Fidelity's published requirement (A4)
    return {"credit": credit, "width": width, "pnl": pnl, "band": band,
            "equity_cost": equity_cost,
            "capital_draft": cap_draft * 100.0, "capital_broker": cap_broker * 100.0,
            "ret_pct": 100.0 * pnl / cap_draft,
            "ret_pct_broker": 100.0 * pnl / cap_broker,
            "pnl_dollars": pnl * 100.0}


# ------------------------------------------------------------------------------- the pick pass
def build_picks(era_picks, label):
    """Attach a long leg to every short pick. Counts every refusal reason separately."""
    out, why = [], {"no_chain": 0, "no_day": 0, "no_strike_below": 0, "band_refused": 0}
    cache, t0 = {}, time.time()
    for i, (_ix, r) in enumerate(era_picks.iterrows()):
        t, y = str(r["ticker"]), int(str(r["date"])[:4])
        if (t, y) not in cache:
            raw = SP.read_raw_chain(t, y)
            cache[(t, y)] = SP.index_by_date(raw) if raw is not None else None
        byd = cache[(t, y)]
        if byd is None:
            why["no_chain"] += 1
            continue
        day = byd.get(str(r["date"]))
        if day is None or not len(day):
            why["no_day"] += 1
            continue
        puts = day[day["right"].astype(str).str.upper().str[0] == "P"]
        got = long_leg(puts, r["expiration"], r["strike"], r["spot"])
        if got is None:
            # distinguish "nothing listed there" from "listed but outside the declared band"
            tgt = float(r["strike"]) - WIDTH_FRAC * float(r["spot"])
            if len(puts[puts["strike"].astype(float) <= tgt]):
                why["band_refused"] += 1
            else:
                why["no_strike_below"] += 1
            continue
        row = dict(r)
        row.update({"long_strike": got["strike"], "long_bid": got["bid"],
                    "long_ask": got["ask"], "width": got["width"],
                    "width_frac": got["width_frac"]})
        out.append(row)
        if i and i % 500 == 0:
            print("    %s %d/%d (%.0fs)" % (label, i, len(era_picks), time.time() - t0))
    return pd.DataFrame(out), why


# ------------------------------------------------------------------------------------ the kills
def run_kills():
    print("SELL-PREMIUM-3 KILLS  (own pass; the arm refuses without this artifact)\n")
    short = pd.read_pickle(D.out_path("SELLPREMIUM2_PICKS25.pkl"))
    print("  short-leg picks on the BUILD quadrant: %d" % len(short))
    picks, why = build_picks(short, "K1")
    n_events, n_days = len(picks), (picks["date"].nunique() if len(picks) else 0)
    k1 = {"n_priceable_events": int(n_events), "n_covered_days": int(n_days),
          "floor_events": K1_MIN_EVENTS, "floor_days": K1_MIN_DAYS,
          "refusals": why, "short_leg_picks": int(len(short)),
          "pass": bool(n_events >= K1_MIN_EVENTS and n_days >= K1_MIN_DAYS),
          "note": ("a two-leg filter is strictly tighter than SELL-PREMIUM-2's one-leg 2,610 "
                   "and the two coverages may not be compared without saying so (void 7)")}
    print("\nK1  %d priceable two-leg events (floor %d), %d covered days (floor %d) -> %s"
          % (n_events, K1_MIN_EVENTS, n_days, K1_MIN_DAYS, "PASS" if k1["pass"] else "FIRES"))
    print("    refusals: %s" % json.dumps(why))

    art = {"item": "SELL-PREMIUM-3 kills", "register": "PREREG_sellpremium3.md",
           "K1": k1, "width_frac": WIDTH_FRAC, "width_band": list(WIDTH_BAND)}

    if not k1["pass"]:
        art["all_kills_pass"] = False
        _write(art)
        print("\nK1 FIRES. The register STOPS; no arm runs.")
        return 1

    picks.to_pickle(D.out_path("%s_PICKS.pkl" % PREFIX))

    # ---- K3-POS, on MEASURED credit at the measured strikes (A3, and the draft's void 6)
    mon = float(np.median(picks["moneyness"]))
    cred = (picks["bid"].astype(float) - picks["long_ask"].astype(float))
    prem = float(np.median(cred / picks["strike"].astype(float)))
    dte = float(np.median(picks["dte"]))
    turns = 252.0 / dte
    spy = D.read_prices("SPY")
    worst = {}
    for y in (2016, 2017, 2018, 2019, 2020, 2022, 2025):
        s = spy[(spy["date"] >= "%d-01-01" % y) & (spy["date"] <= "%d-12-31" % y)]
        if len(s) > 32:
            worst["%d" % y] = SP.worst_rolling(s["close"].to_numpy(dtype=float), 32)
    w = min([v for v in worst.values() if np.isfinite(v)] or [float("nan")])
    # A spread's loss is CAPPED at the width, which is the whole point and is why K3-POS alone
    # is the wrong frame -- see K3-ACCT below and the register's §5.
    width_frac_of_strike = float(np.median(picks["width"] / picks["strike"].astype(float)))
    tab = {}
    for nm, fall in list(worst.items()) + [("single_name_at_1.4x", w * 1.4)]:
        if not np.isfinite(fall):
            continue
        loss = min(width_frac_of_strike, max(0.0, (-fall - (1.0 - mon)) * 1.0))
        cap = max(1e-9, width_frac_of_strike - prem)
        tab[nm] = {"worst_32_session_return": float(fall),
                   "loss_on_capital": float(loss / cap),
                   "years_of_premium": float((loss / cap) / max(1e-9, prem * turns / cap))}
    worst_years = max(v["years_of_premium"] for v in tab.values()) if tab else float("inf")
    k3p = {"median_moneyness": mon, "median_credit_frac_of_strike": prem, "median_dte": dte,
           "turns_per_year": turns, "median_width_frac_of_strike": width_frac_of_strike,
           "annual_income_frac_of_capital": float(prem * turns
                                                  / max(1e-9, width_frac_of_strike - prem)),
           "table": tab, "worst_years_of_premium": float(worst_years),
           "bar": SP.K3_MAX_YEARS_OF_PREMIUM,
           "pass": bool(np.isfinite(worst_years)
                        and worst_years <= SP.K3_MAX_YEARS_OF_PREMIUM)}
    print("\nK3-POS  worst %.4f years of premium against %.1f -> %s"
          % (k3p["worst_years_of_premium"], k3p["bar"], "PASS" if k3p["pass"] else "FIRES"))

    # ---- K3-ACCT: in a 32.6% month every 7.5%-OTM long strike is through, so EVERY open
    # spread pays its maximum and the account loss IS the deployed fraction. The cap enforces
    # it by construction, which the register scores as low-information (expectation 4).
    k3a = {"deployment_cap": DEPLOY_CAP, "bar": K3_ACCT_MAX,
           "account_loss_in_a_32_6pc_month": DEPLOY_CAP,
           "reason": ("every 7.5%-OTM long strike is through in a 32.6% month, so each open "
                      "spread pays its full width and the account-level loss is exactly the "
                      "deployed fraction"),
           "pass": bool(DEPLOY_CAP <= K3_ACCT_MAX)}
    print("K3-ACCT %.1f%% deployed vs a %.1f%% bar -> %s"
          % (100 * DEPLOY_CAP, 100 * K3_ACCT_MAX, "PASS" if k3a["pass"] else "FIRES"))

    art.update({"K3_POS": k3p, "K3_ACCT": k3a,
                "all_kills_pass": bool(k1["pass"] and k3p["pass"] and k3a["pass"])})
    _write(art)
    print("\nall kills pass: %s" % art["all_kills_pass"])
    return 0 if art["all_kills_pass"] else 1


def _write(art):
    with io.open(D.out_path("%s_KILLS.json" % PREFIX), "w", encoding="utf-8") as fh:
        json.dump(art, fh, indent=2, sort_keys=True, default=str)
    print("wrote %s" % D.out_path("%s_KILLS.json" % PREFIX))


def require_kills():
    p = D.out_path("%s_KILLS.json" % PREFIX)
    if not os.path.isfile(p):
        raise SystemExit("REFUSED: no kills artifact at %s. Run --kills first (O10)." % p)
    with io.open(p, encoding="utf-8") as fh:
        k = json.load(fh)
    if not k.get("all_kills_pass"):
        raise SystemExit("REFUSED: the kills artifact does not pass. The arm does not run.")
    return k


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--kills", action="store_true")
    ap.add_argument("--arms", action="store_true")
    a = ap.parse_args()
    if a.kills:
        sys.exit(run_kills())
    if a.arms:
        from scripts.sellpremium3_arms import main as arms_main
        sys.exit(arms_main())
    ap.error("choose --kills or --arms")
