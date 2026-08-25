"""O-1 pass 2 - THE ARM. Long puts on accounting-flagged names, against matched unflagged rows.

`PREREG_o1_long_puts_accounting_flags.md` (ALONE and BLIND at `c82c15b`; the options trial booked
at `5423515` BEFORE any runner existed).

IT REFUSES WITHOUT A PASSING KILL ARTIFACT. `scripts/o1_kill.py` runs in its OWN pass and is read
first - `O10`'s process defect, not repeated. The refusal is mutation-tested.

NOTHING IS RE-IMPLEMENTED. `pick_contract` and `simulate_trade` are the SHIPPED engine's, IMPORTED
and unmodified; both already take `right` and `dte_range` as real parameters, so a put at this
register's declared tenor needs no second copy of either. `build_flags` is `s10_accounting_veto`'s
ONE definition. The chain provider is `evown_build.FreezeChains`, whose key carries the RIGHT -
`EVOWN` learned that the hard way and this book is the one where it would bite hardest, since a
strike/expiry pair here names a put whose call twin is the cheap one.

THE MEDIAN IS BANNED ON A RETURN and the ban is pinned by AST in the suite, scoped to returns
because a tenor's median is an ordinary descriptive (`EVOWN`'s narrowing, inherited).

    python -m scripts.o1_arm --build     # simulate the put book (slow, checkpointed)
    python -m scripts.o1_arm --score     # match, bootstrap, and record the verdict
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from valuation.edge import chain_store as cs                          # noqa: E402
from valuation.edge import options_backtest as OB                     # noqa: E402
from valuation.edge import power_gate as pg                           # noqa: E402
from valuation.edge import research_log as rl                         # noqa: E402
from valuation.edge import statistics as st                           # noqa: E402
from valuation.edge.options_fill import CONTRACT_MULTIPLIER           # noqa: E402
from s10_accounting_veto import build_flags                           # noqa: E402
from evown_build import FreezeChains                                  # noqa: E402
import o1_kill as K                                                   # noqa: E402

# ---- the register's declared constants. None is chosen here. ---------------------------------
RIGHT = "P"                       # sec 5: LONG PUT. The whole O-series book is 100% calls.
DTE_BAND = (150, 210)             # sec 4, fixed by E-5's arithmetic before any outcome
SECONDARY_BAND = (330, 400)       # sec 4, declared secondary, NO verdict power
DRAWS = 2000                      # sec 5
SEED = 20260824                   # sec 5
RHO = 0.6743                      # O18's measured toll - AN EXTRAPOLATION, labelled everywhere
FLOOR_TRADES = 3600               # sec 6, DERIVED FROM POWER and not from n
FLOOR_PER_HALF = 1200             # sec 6
PRIOR_EFFECT_SD = 0.07            # sec 6, the register's own prior effect size

BOOK = "O1_PUT_BOOK.pkl"
OUT = "O1_ARM.json"


class HarvestChains(FreezeChains):
    """`FreezeChains` over the HARVEST freeze, which pickles a different payload shape.

    `EVOWN` read the EOD freeze, which pickles a bare DataFrame, so its loader collects frames
    with `isinstance(f, pd.DataFrame)`. The harvest pickles a dict carrying `rows` plus its own
    `max_dte` provenance, so that test is False for every file and the loader collects NOTHING -
    it does not raise, `by_date` is simply None and every date reads `no_chain_on_date`. Caught by
    the smoke test picking ZERO contracts on a name whose chain is demonstrably there.

    Only the LOADING is overridden. `chain_on`, `index_contracts` and `contract_history` are
    INHERITED unmodified, which is the point: `index_contracts` carries the right-in-the-key fix
    `EVOWN` paid three build passes for, and this book is the one where it would bite hardest,
    since every contract here is a put whose call twin at the same strike is the cheap one.
    """

    def __init__(self, opt_root, tk):
        frames = []
        d = os.path.join(opt_root, tk)
        if os.path.isdir(d):
            for f in sorted(os.listdir(d)):
                if not f.endswith(".pkl"):
                    continue
                try:
                    fr = K.chain_frame(os.path.join(d, f))
                except Exception:                                      # noqa: BLE001
                    continue
                if isinstance(fr, pd.DataFrame) and len(fr):
                    frames.append(fr)
        if not frames:
            self.by_date, self._all, self.by_contract = None, None, {}
            return
        a = pd.concat(frames, ignore_index=True)
        a["date"] = a["date"].astype(str).str[:10]
        a["expiration"] = a["expiration"].astype(str).str[:10]
        self._all = a
        self.by_date = {dd: g for dd, g in a.groupby("date", observed=True)}
        self.by_contract = {}


def require_kill() -> dict:
    """REFUSE unless the kill ran and did not fire.

    THREE STATES, NOT TWO, and the distinction is `E-1`'s: a hard-coded refusal cannot tell
    ABSENT from FAILING, and a reader who is told "the kill did not pass" when the truth is
    "the kill was never run" has been told the wrong thing. The arm is never executed to prove
    this gate works - `E-1` proved a refusal by removing it and thereby RAN a withdrawn arm.
    """
    p = K._out(K.OUT)
    if not os.path.isfile(p):
        raise SystemExit(
            "REFUSING: no kill artifact at %s. The pre-outcome kill has NOT BEEN RUN. "
            "Run `python -m scripts.o1_kill --kill` first; O10's process defect is that a "
            "gating control and the outcomes it gates ran in one pass." % p)
    with io.open(p, encoding="utf-8") as fh:
        art = json.load(fh)
    if art.get("kill_fires"):
        raise SystemExit(
            "REFUSING: the kill FIRED at %r against a bar of %r. The register withdraws the arm "
            "before any outcome is read; the market already prices the flag."
            % (art.get("kill_statistic"), art.get("kill_bar")))
    if art.get("kill_statistic") is None:
        raise SystemExit(
            "REFUSING: the kill artifact exists but carries NO statistic. That is a FAILED kill, "
            "not a passing one, and the two must not read alike.")
    return art


def cap_quintiles(panel: pd.DataFrame) -> pd.DataFrame:
    """Within-date market-cap quintile. Within DATE because a cap tier is a cross-sectional
    fact and a pooled quintile over 17 years would sort largely on the calendar."""
    p = panel[["date", "ticker", "market_cap"]].copy()
    p["ticker"] = p["ticker"].astype(str)

    def q(s):
        if s.notna().sum() < 5:
            return pd.Series(np.nan, index=s.index)
        return pd.qcut(s.rank(method="first"), 5, labels=False)

    p["cap_q"] = p.groupby("date")["market_cap"].transform(q)
    return p


def build(band=DTE_BAND, out_name=BOOK) -> pd.DataFrame:
    require_kill()

    panel = pd.read_pickle(K._out(K.PANEL_NAME))
    panel["date"] = pd.to_datetime(panel["date"])
    panel["_t"] = panel["ticker"].astype(str)

    chains, prov = cs.resolve_harvest()
    if not prov.get("pinned"):
        raise SystemExit("O-1 reads the PINNED freeze only")
    print("chains: %s  manifest %s"
          % (chains, str(prov.get("manifest_sha256"))[:16]), flush=True)

    # U1-SPLIT, AND OMITTING THIS WAS A DEFECT OF MINE. Option strikes are AS-TRADED and never
    # adjusted for splits while `raw_close` crosses one, so a contract whose life spans a split
    # settles a pre-split strike against a post-split underlying. `simulate_trade`'s `splits`
    # argument defaults to None - "the historical behaviour exactly" - so a caller that forgets
    # it silently gets NO guard. Measured on this book: MNST entered 2016-10-18 with a 135 strike
    # and split 3-for-1 on 2016-11-10, and the settle branch booked intrinsic of 135 minus ~45
    # for a fake +1453%. Caught by disbelieving one return, not by anything raising - and it is
    # the same defect `U1-SPLIT` found on GE's 1-for-8 reverse split, in a new costume.
    splits = OB.load_splits(K._data())

    bars_dir = K._bars_dir()
    bar_syms = {f[:-4] for f in os.listdir(bars_dir) if f.endswith(".pkl")}
    fz = {d for d in os.listdir(chains) if os.path.isdir(os.path.join(chains, d))}
    names = sorted(fz & set(panel["_t"]) & bar_syms)

    have = {}
    for t, d in zip(panel["_t"], panel["date"]):
        have.setdefault(t, []).append(pd.Timestamp(d))

    rows = []
    ckpt = K._out(out_name + ".partial")
    done = set()
    if os.path.exists(ckpt):
        prev = pd.read_pickle(ckpt)
        rows = prev.to_dict("records")
        done = set(prev["ticker"].astype(str))
        print("resuming: %d rows, %d names done" % (len(rows), len(done)), flush=True)

    for i, tk in enumerate(names, 1):
        if tk in done:
            continue
        rc = K.raw_close_series(bars_dir, tk)
        if rc is None:
            continue
        # THE SHIPPED LOADER, not a hand-built dict, and this is a DEFECT OF MINE repaired.
        # `simulate_trade`'s settle branch does `ds <= expiry.isoformat()` and `window_ending`
        # does `d <= as_of`, so the engine consistently expects `bars["date"]` to hold ISO
        # STRINGS - which is what the canonical cache stores. My first cut handed it
        # `datetime.date` objects, which raised `TypeError` on 26 of 2,688 trades. Those 26 are
        # NOT a random 1%: they are exactly the trades that reached the SETTLE branch, and for a
        # long put that is where a deep-ITM expiry pays, so the dropout ran AGAINST the
        # hypothesis. Using the shipped loader removes the hand-built object entirely (`B7`).
        bars = OB.load_bars(tk, cache_dir=bars_dir)
        if not bars or not bars.get("raw_close"):
            continue
        fc = HarvestChains(chains, tk)
        if fc.by_date is None:
            continue

        picks = []
        for d in sorted(have.get(tk, [])):
            key = d.date().isoformat()
            day = fc.chain_on(key)
            if day is None or not len(day):
                rows.append({"ticker": tk, "date": d, "traded": False,
                             "reason": "no_chain_on_date"})
                continue
            if d not in rc.index:
                rows.append({"ticker": tk, "date": d, "traded": False, "reason": "no_raw_close"})
                continue
            spot = float(rc.loc[d])
            best = OB.pick_contract(day, spot, d.date(), right=RIGHT, dte_range=band)
            if best is None:
                rows.append({"ticker": tk, "date": d, "traded": False,
                             "reason": "no_contract_in_band"})
                continue
            picks.append((d, best, spot))

        if picks:
            fc.index_contracts([(float(b["strike"]), str(b["expiration"])[:10], RIGHT)
                                for _, b, _ in picks])
        for d, best, spot in picks:
            try:
                tr = OB.simulate_trade(fc, tk, best, d.date(), bars, splits=splits)
            except Exception as e:                                     # noqa: BLE001
                rows.append({"ticker": tk, "date": d, "traded": False,
                             "reason": "sim_error:%s" % type(e).__name__})
                continue
            # A REFUSED TRADE IS A DICT AND A DICT IS TRUTHY, which is a defect of my own:
            # `simulate_trade` signals refusal as {"ok": False, "reason": ...} rather than by
            # returning None, so `if not tr` lets it straight through and the row lands marked
            # `traded: True` with no premium, no return and its REASON THROWN AWAY. The scoring
            # was never wrong - those rows carry a null return and are filtered - but a book that
            # says it traded something it refused is wrong about its own history, and the reason
            # is exactly the diagnosis `RUN_RULES` rule 9 exists to keep.
            if not tr or not tr.get("ok"):
                rows.append({"ticker": tk, "date": d, "traded": False,
                             "reason": (tr.get("reason") if tr else None) or "no_trade"})
                continue
            ef = tr.get("entry_fill")
            rows.append({
                "ticker": tk, "date": d, "traded": True, "reason": None,
                "strike": float(best["strike"]), "expiration": str(best["expiration"])[:10],
                "right": RIGHT, "spot": spot,
                "delta": (float(best["delta"]) if best.get("delta") is not None else None),
                "dte": int((pd.Timestamp(str(best["expiration"])[:10]) - d).days),
                "entry_premium": (float(ef) if ef is not None else None),
                "net_pnl": tr.get("net_pnl"),
                # THE MULTIPLIER, and leaving it out is EVOWN's pass-2 defect exactly.
                # `simulate_trade` returns `net_pnl` in DOLLARS while `entry_fill` is the
                # PER-SHARE premium, so the naive ratio reads a hundredfold high: AAPL 2018-01-16
                # came back at +102.461 rather than +1.0246. The engine's own constants prove the
                # correction rather than my arithmetic asserting it - that trade exits at
                # "target" and TARGET_PCT is 1.00, and the stop cases land at -0.53 against a
                # STOP_PCT of -0.50. Caught by disbelieving the numbers, not by anything raising.
                "ret": (float(tr["net_pnl"]) / (float(ef) * CONTRACT_MULTIPLIER)
                        if (ef and tr.get("net_pnl") is not None) else None),
                "exit_date": tr.get("exit_date"), "held_days": tr.get("held_days"),
                "exit_reason": tr.get("exit_reason"),
                "entry_bid": best.get("bid"), "entry_ask": best.get("ask"),
            })

        if i % 20 == 0:
            pd.DataFrame(rows).to_pickle(ckpt)
            print("  ... %d/%d names, %d rows, %d traded (checkpointed)"
                  % (i, len(names), len(rows),
                     int(pd.DataFrame(rows)["traded"].fillna(False).sum())), flush=True)

    book = pd.DataFrame(rows)
    book.to_pickle(K._out(out_name))       # RULE 9: the draws land before anything is summarised
    if os.path.exists(ckpt):
        os.remove(ckpt)
    print("wrote %s  rows %d  traded %d"
          % (out_name, len(book), int(book["traded"].fillna(False).sum())), flush=True)
    return book


def _boot_gap(d: pd.DataFrame, rng, draws: int):
    """Paired name-year cluster bootstrap - R3's own unit. Resamples CELLS, so a name-year's
    flagged and unflagged legs travel together and the pairing is preserved."""
    cells = d["cell"].unique()
    idx = {c: g.index.to_numpy() for c, g in d.groupby("cell")}
    out = []
    for _ in range(draws):
        pick = rng.choice(cells, size=len(cells), replace=True)
        s = d.loc[np.concatenate([idx[c] for c in pick])]
        f = s.loc[s["flag"], "ret"]
        n = s.loc[~s["flag"], "ret"]
        if len(f) < 5 or len(n) < 5:
            continue
        out.append(float(f.mean()) - float(n.mean()))
    return np.array(out)


def score() -> dict:
    art = require_kill()
    book = pd.read_pickle(K._out(BOOK))
    book["date"] = pd.to_datetime(book["date"])
    t = book[book["traded"].fillna(False) & book["ret"].notna()].copy()

    panel = pd.read_pickle(K._out(K.PANEL_NAME))
    panel["date"] = pd.to_datetime(panel["date"])
    caps = cap_quintiles(panel)
    flags = build_flags(K._data("backtest"),
                        sorted(panel["ticker"].astype(str).unique()),
                        sorted(panel["date"].unique()))
    flags["date"] = pd.to_datetime(flags["date"])

    # C-FIDELITY, GATING - MA28-CARD published 6,542 flagged panel rows at 5.7414%.
    fp = panel[["date", "ticker"]].copy()
    fp["ticker"] = fp["ticker"].astype(str)
    chk = fp.merge(flags[["date", "ticker", "vetoed"]], on=["date", "ticker"], how="left")
    n_panel_flagged = int(chk["vetoed"].fillna(False).sum())
    if n_panel_flagged != 6542:
        raise SystemExit("C-FIDELITY FAILED: %d flagged panel rows against MA28's 6,542"
                         % n_panel_flagged)

    t = t.merge(flags[["date", "ticker", "vetoed"]], on=["date", "ticker"], how="left")
    t = t.merge(caps[["date", "ticker", "cap_q"]], on=["date", "ticker"], how="left")
    t["flag"] = t["vetoed"].fillna(False).astype(bool)
    t["yr"] = t["date"].dt.year
    t["name_year"] = t["ticker"].astype(str) + "|" + t["yr"].astype(str)

    # COSTS. The verdict is taken on the FULL QUOTED SPREAD, the conservative side. The rho leg
    # is reported beside it and is AN EXTRAPOLATION: O18 measured rho on 35-delta ~60-DTE CALLS
    # and this book is PUTS at 150-210 DTE.
    mid = (t["entry_bid"].astype(float) + t["entry_ask"].astype(float)) / 2.0
    half = (t["entry_ask"].astype(float) - t["entry_bid"].astype(float)) / 2.0
    prem_rho = mid + RHO * half
    t["ret_rho"] = np.where(prem_rho > 0,
                            t["net_pnl"].astype(float)
                            / (prem_rho.replace(0, np.nan) * CONTRACT_MULTIPLIER), np.nan)

    N = rl.detail()["by_domain"]["options"]
    crit = st.hlz_hurdle(N)
    rng = np.random.default_rng(SEED)

    arms = {}
    for label, keycols in (("primary_name_year", ["name_year"]),
                           ("secondary_year_x_capq", ["yr", "cap_q"])):
        d = t.dropna(subset=keycols).copy()
        d["cell"] = d[keycols].astype(str).agg("|".join, axis=1)
        g = d.groupby("cell")["flag"].agg(["sum", "count"])
        keep = g[(g["sum"] > 0) & (g["sum"] < g["count"])].index
        dropped_flagged = int(d.loc[d["flag"] & ~d["cell"].isin(keep)].shape[0])
        d = d[d["cell"].isin(keep)].copy().reset_index(drop=True)

        f = d.loc[d["flag"], "ret"]
        n = d.loc[~d["flag"], "ret"]
        if len(f) < 5 or len(n) < 5:
            arms[label] = {"scoreable": False, "n_flagged": int(len(f)),
                           "n_unflagged": int(len(n)),
                           "dropped_flagged_unmatched": dropped_flagged}
            continue
        gap = float(f.mean()) - float(n.mean())
        boot = _boot_gap(d, rng, DRAWS)
        lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
        se = float(boot.std(ddof=1))
        sd_pooled = float(pd.concat([f, n]).std(ddof=1))
        n_eff = int(len(f))

        fr = d.loc[d["flag"], "ret_rho"].dropna()
        nr = d.loc[~d["flag"], "ret_rho"].dropna()
        gap_rho = (float(fr.mean()) - float(nr.mean())) if (len(fr) > 4 and len(nr) > 4) else None

        early = d[d["yr"] <= d["yr"].median()]
        late = d[d["yr"] > d["yr"].median()]

        def half_gap(x):
            a, b = x.loc[x["flag"], "ret"], x.loc[~x["flag"], "ret"]
            if len(a) < 5 or len(b) < 5:
                return None
            return float(a.mean()) - float(b.mean())

        mde80 = float(pg.mde_at_power(n_eff, n_trials=N)) * sd_pooled
        mde50 = float(pg.mde_at_power(n_eff, n_trials=N, z_power=0.0)) * sd_pooled
        power_vs_prior = float(pg.power_at(PRIOR_EFFECT_SD * sd_pooled, se, n_trials=N))

        under = (n_eff + int(len(n))) < FLOOR_TRADES
        arms[label] = {
            "scoreable": True,
            "matched_on": keycols, "n_cells": int(d["cell"].nunique()),
            "n_flagged": n_eff, "n_unflagged": int(len(n)),
            "n_matched_total": int(len(d)),
            "dropped_flagged_unmatched": dropped_flagged,
            "flagged_mean_ret": float(f.mean()), "unflagged_mean_ret": float(n.mean()),
            "gap": gap, "ci95": [lo, hi], "bootstrap_se": se, "n_draws": int(len(boot)),
            "gap_at_rho_EXTRAPOLATION": gap_rho,
            "early_gap": half_gap(early), "late_gap": half_gap(late),
            "sd_pooled": sd_pooled,
            "mde_80_power": mde80, "mde_50_power": mde50,
            "observed_over_mde80": (abs(gap) / mde80) if mde80 else None,
            "power_against_register_prior": power_vs_prior,
            "floor_trades": FLOOR_TRADES, "floor_per_half": FLOOR_PER_HALF,
            "below_floor": bool(under),
            "verdict": ("UNDERPOWERED" if under else
                        ("SEPARATES" if (lo > 0 or hi < 0) else "NULL")),
        }

    prim = arms.get("primary_name_year", {})
    payload = {
        "item": "O-1", "pass": "arm",
        "register": "PREREG_o1_long_puts_accounting_flags.md",
        "kill": {"statistic": art.get("kill_statistic"), "bar": art.get("kill_bar"),
                 "fired": art.get("kill_fires"),
                 "read_in_its_own_pass_before_this_ran": True},
        "instrument": {
            "right": RIGHT, "dte_band": list(DTE_BAND),
            "selection": "valuation.edge.options_backtest.pick_contract, IMPORTED, right='P'",
            "exit": "valuation.edge.options_backtest.simulate_trade, IMPORTED and unmodified",
            "flags": "s10_accounting_veto.build_flags, the ONE definition",
            "chains": "evown_build.FreezeChains, key carries the RIGHT",
        },
        "options_N": N, "crit": crit,
        "fidelity": {"gating": True, "flagged_panel_rows": n_panel_flagged,
                     "ma28_published": 6542},
        "book": {"rows": int(len(book)), "traded": int(book["traded"].fillna(False).sum()),
                 "scoreable": int(len(t))},
        "arms": arms,
        "verdict": prim.get("verdict"),
        "costs": {"verdict_basis": "FULL QUOTED SPREAD - the conservative side",
                  "rho": RHO,
                  "rho_is_an_extrapolation": "O18 measured rho on 35-delta ~60-DTE CALLS; this "
                                             "book is PUTS at 150-210 DTE"},
        "framing": "O11 GOVERNS and nothing here licenses a trade. R2 stands. ADOPTS NOTHING.",
    }
    with io.open(K._out(OUT), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, default=str)

    print()
    for k, v in arms.items():
        if not v.get("scoreable"):
            print("%s: NOT SCOREABLE (flagged %d, unflagged %d)"
                  % (k, v.get("n_flagged"), v.get("n_unflagged")))
            continue
        print("%s: flagged %d vs unflagged %d over %d cells (%d flagged dropped unmatched)"
              % (k, v["n_flagged"], v["n_unflagged"], v["n_cells"],
                 v["dropped_flagged_unmatched"]))
        print("   gap %+.4f  CI95 [%+.4f, %+.4f]   early %s  late %s"
              % (v["gap"], v["ci95"][0], v["ci95"][1],
                 ("%+.4f" % v["early_gap"]) if v["early_gap"] is not None else "n/a",
                 ("%+.4f" % v["late_gap"]) if v["late_gap"] is not None else "n/a"))
        print("   MDE80 %.4f  MDE50 %.4f  observed/MDE80 %.3fx  power vs register prior %.4f"
              % (v["mde_80_power"], v["mde_50_power"], v["observed_over_mde80"],
                 v["power_against_register_prior"]))
        print("   VERDICT %s   (floor %d matched trades; this book has %d)"
              % (v["verdict"], FLOOR_TRADES, v["n_matched_total"]))
    print("wrote %s" % K._out(OUT))
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.build:
        build()
    if a.score:
        score()
    if not (a.build or a.score):
        ap.error("pass --build or --score")


if __name__ == "__main__":
    main()
